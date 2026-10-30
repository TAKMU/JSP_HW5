import math
import time
import jsp_core
import csv
 
 
# Time limit settings
USE_TIME_LIMIT = True     # False: run until the optimum is proven
TIME_LIMIT = 60.0         # seconds
CHECK_EVERY = 1024        # check the clock every this many expanded nodes
import argparse

class SearchTimeout(Exception):
    """Raised inside the search when the time limit is reached."""
    pass
 
 
def check_time(stats):
    """Raises SearchTimeout if a deadline is set and has passed.
    The clock is only read every CHECK_EVERY nodes to keep it cheap."""
    if stats["deadline"] is not None and stats["expanded"] % CHECK_EVERY == 0:
        if time.perf_counter() > stats["deadline"]:
            raise SearchTimeout
 
 
def lower_bound(instance, num_machines):
    """Returns (increment, bound).
 
    bound: no schedule can finish before the longest job or busiest machine.
    increment: size of the jump used in phase 1.
    """
    job_sums = [sum(d for _, d in job) for job in instance]
    machine_sums = [0] * num_machines
    for job in instance:
        for machine, duration in job:
            machine_sums[machine] += duration
    bound = max(max(job_sums), max(machine_sums))
    if max(machine_sums) > max(job_sums):
        increment = max(machine_sums) / num_machines
    else:
        len_jobs = [len(job) for job in instance]
        increment = max(job_sums) / min(len_jobs)
    return max(1, int(increment)), bound
 
 
# ---------------------------------------------------------------------------
# Phase 1: cost-bounded depth-first search (one iteration of IDS on cost)
# ---------------------------------------------------------------------------
def iterative_search(instance, depth, i, machines_t, jobs_t, next_tasks,
                     prune_obj, prev_start, prev_job, makespan,
                     next_bound, stats):
    """Depth-first search that never exceeds the makespan bound `prune_obj`.
 
    Returns the makespan of the first complete schedule found,
    or None if no schedule fits within the bound.
 
    next_bound: one-element list, collects the smallest pruned end time.
                The optimum is at least this value if the search fails.
    stats:      dict with expanded nodes, frontier sizes and the deadline.
    """
    stats["expanded"] += 1
    check_time(stats)
 
    if i == depth:
        return makespan                  # every task placed
 
    children = []
    for j, task in enumerate(next_tasks):
        if task >= len(instance[j]):
            continue                     # job j is finished
 
        machine, duration = instance[j][task]
        start = max(machines_t[machine], jobs_t[j])
        end = start + duration
 
        # Canonical ordering: each schedule is generated only once.
        if start < prev_start or (start == prev_start and j < prev_job):
            continue
 
        # Prune before recursing; remember the smallest value that went over.
        if end > prune_obj:
            next_bound[0] = min(next_bound[0], end)
            continue
 
        children.append((j, task, machine, start, end))
 
    stats["frontier"] += len(children)
    stats["max_frontier"] = max(stats["max_frontier"], stats["frontier"])
 
    for k, (j, task, machine, start, end) in enumerate(children):
        stats["frontier"] -= 1
 
        # save
        old_machine_t = machines_t[machine]
        old_job_t = jobs_t[j]
 
        # update
        machines_t[machine] = end
        jobs_t[j] = end
        next_tasks[j] = task + 1
 
        result = iterative_search(instance, depth, i + 1, machines_t, jobs_t,
                                  next_tasks, prune_obj, start, j,
                                  max(makespan, end), next_bound, stats)
 
        # restore
        machines_t[machine] = old_machine_t
        jobs_t[j] = old_job_t
        next_tasks[j] = task
 
        if result is not None:
            stats["frontier"] -= len(children) - k - 1
            return result
 
    return None
 
 
def run_search(instance, num_machines, bound, stats):
    """One full depth-first search with a given bound.
 
    Returns (makespan or None, smallest pruned end time).
    """
    depth = sum(len(job) for job in instance)
    n_jobs = len(instance)
    next_bound = [math.inf]
    stats["frontier"] = 0
    result = iterative_search(instance, depth, 0,
                              [0] * num_machines, [0] * n_jobs, [0] * n_jobs,
                              bound, -1, -1, 0, next_bound, stats)
    return result, next_bound[0]
 
 
# ---------------------------------------------------------------------------
# Phase 2: depth-first branch-and-bound (single search, no restarts)
# ---------------------------------------------------------------------------
def bnb_search(instance, depth, i, machines_t, jobs_t, next_tasks,
               bound, prev_start, prev_job, makespan, best, stats):
    """Does not stop at the first solution: it records its makespan,
    tightens bound[0] to makespan - 1, and keeps searching.
    When it finishes, best["makespan"] is optimal.
    """
    stats["expanded"] += 1
    check_time(stats)
 
    if i == depth:
        best["makespan"] = makespan
        best["time"] = time.perf_counter() - best["t0"]
        bound[0] = makespan - 1          # from now on, only strictly better
        return
 
    children = []
    for j, task in enumerate(next_tasks):
        if task >= len(instance[j]):
            continue
        machine, duration = instance[j][task]
        start = max(machines_t[machine], jobs_t[j])
        end = start + duration
        if start < prev_start or (start == prev_start and j < prev_job):
            continue
        if end > bound[0]:
            continue
        children.append((j, task, machine, start, end))
 
    stats["frontier"] += len(children)
    stats["max_frontier"] = max(stats["max_frontier"], stats["frontier"])
 
    for (j, task, machine, start, end) in children:
        stats["frontier"] -= 1
        if end > bound[0]:               # bound may have dropped since
            continue
 
        old_machine_t = machines_t[machine]
        old_job_t = jobs_t[j]
        machines_t[machine] = end
        jobs_t[j] = end
        next_tasks[j] = task + 1
 
        bnb_search(instance, depth, i + 1, machines_t, jobs_t, next_tasks,
                   bound, start, j, max(makespan, end), best, stats)
 
        machines_t[machine] = old_machine_t
        jobs_t[j] = old_job_t
        next_tasks[j] = task
 
 
# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def start_search(instance_class, use_time_limit, time_limit):
    """Phase 1: raise the bound with big jumps until a schedule fits (IDS on cost).
    Phase 2: one branch-and-bound search starting from that makespan,
             which finds the optimum and proves it.
 
    If use_time_limit is True and the limit is reached, the best makespan
    found so far is reported (possibly None) and "optimal" is False.
 
    Returns a report dict.
    """
    t0 = time.perf_counter()
    stats = {"expanded": 0, "frontier": 0, "max_frontier": 0,
             "deadline": t0 + time_limit if use_time_limit else None}
    instance = instance_class.ops
    num_machines = instance_class.n_machines
    increment, low = lower_bound(instance, num_machines)
    searches = 0
 
    high = None                          # best makespan found so far
    time_to_best = None
    timed_out = False
 
    try:
        # ---------- Phase 1: climb ----------
        bound = low
        while True:
            searches += 1
            result, min_pruned = run_search(instance, num_machines, bound, stats)
            if result is not None:
                break
            if min_pruned == math.inf:
                raise ValueError("No feasible schedule exists")
            low = max(low, min_pruned)   # optimum >= smallest pruned end
            bound = min_pruned + increment   # jump
 
        high = result
        time_to_best = time.perf_counter() - t0
 
        # ---------- Phase 2: branch-and-bound, no restarts ----------
        if low < high:
            best = {"makespan": high, "t0": t0, "time": time_to_best}
            depth = sum(len(job) for job in instance)
            n_jobs = len(instance)
            stats["frontier"] = 0
            searches += 1
            try:
                bnb_search(instance, depth, 0, [0] * num_machines,
                           [0] * n_jobs, [0] * n_jobs, [high - 1],
                           -1, -1, 0, best, stats)
            finally:
                # keep any improvement found before a timeout
                high = best["makespan"]
                time_to_best = best["time"]
            low = high                   # search finished: optimum proven
 
    except SearchTimeout:
        timed_out = True
 
    total_time = time.perf_counter() - t0
    report = {
        "name": instance_class.name,
        "makespan": high,                # None if no schedule was found in time
        "optimal": (not timed_out) and high is not None,
        "timed_out": timed_out,
        "proven_lower_bound": low,       # optimum is in [lower bound, makespan]
        "time_to_best": time_to_best,
        "total_time": total_time,
        "searches": searches,
        "expanded_nodes": stats["expanded"],
        "max_frontier": stats["max_frontier"],
    }
    return report
 
 
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='IDS',
                    description='IDS for job shop scheduling',
                    )
    parser.add_argument('--input', '-i', type=str, required=True, help='Path to the input file')
    parser.add_argument('--output', '-o', type=str, required=True, help='Path to the output file')
    parser.add_argument('--timeout', '-to', action=argparse.BooleanOptionalAction,
                    default=True, help='Use a time limit (--no-timeout to disable)')
    parser.add_argument('--time_limit', '-tl', type=float, default=60.0, help='Time limit (s) to stop program')
    parser.add_argument('--name', '-n', type=str, help='Instance name to run')
    args = parser.parse_args()
    fname = args.input
    output_file = args.output
    tout = args.timeout
    tlimit = args.time_limit
    iname = args.name
    instances = jsp_core.load_instances(fname)
    if iname is not None:
        reports = [start_search(instances[iname], use_time_limit=tout, time_limit=tlimit)]
    else:
        reports = []
        for key, value in instances.items():
            print(key)
            reports.append(start_search(value, use_time_limit=tout,
                                        time_limit=tlimit))
    names =["name", "makespan", "optimal", "timed_out", "proven_lower_bound", "time_to_best", "total_time", "searches", "expanded_nodes","max_frontier"] 
    with open(output_file, mode="w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=names)
        writer.writeheader()
        writer.writerows(reports)