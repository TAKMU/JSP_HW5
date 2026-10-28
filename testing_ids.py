import math
import time
import jsp_core
import pandas as pd

instance_1 = [
    [(2,  1), (0,  3), (1,  6), (3,  7), (5,  3), (4,  6)],
    [(1,  8), (2,  5), (4, 10), (5, 10), (0, 10), (3,  4)],
    [(2,  5), (3,  4), (5,  8), (0,  9), (1,  1), (4,  7)],
    [(1,  5), (0,  5), (2,  5), (3,  3), (4,  8), (5,  9)],
    [(2,  9), (1,  3), (4,  5), (5,  4), (0,  3), (3,  1)],
    [(1,  3), (3,  3), (5,  9), (0, 10), (4,  4), (2,  1)],
]
 
NUM_MACHINES = 6
 
 
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
 
 
def iterative_search(instance, depth, i, machines_t, jobs_t, next_tasks,
                     prune_obj, path, prev_start, prev_job, makespan,
                     next_bound, stats):
    """Depth-first search that never exceeds the makespan bound `prune_obj`.
 
    Returns the schedule as a list of (job, task, machine, start, end),
    or None if no schedule fits within the bound.
 
    next_bound: one-element list, collects the smallest pruned end time.
                The optimum is at least this value if the search fails.
    stats:      dict with expanded nodes and frontier sizes.
    """
    stats["expanded"] += 1
 
    if i == depth:
        return list(path)                
 
    children = []
    for j, task in enumerate(next_tasks):
        if task >= len(instance[j]):
            continue                    
 
        machine, duration = instance[j][task]
        start = max(machines_t[machine], jobs_t[j])
        end = start + duration
 
        if start < prev_start or (start == prev_start and j < prev_job):
            continue
 
        if end > prune_obj:
            next_bound[0] = min(next_bound[0], end)
            continue
 
        children.append((j, task, machine, start, end))
 
    stats["frontier"] += len(children)
    stats["max_frontier"] = max(stats["max_frontier"], stats["frontier"])
 
    for k, (j, task, machine, start, end) in enumerate(children):
        stats["frontier"] -= 1          
 
        old_machine_t = machines_t[machine]
        old_job_t = jobs_t[j]
 
        machines_t[machine] = end
        jobs_t[j] = end
        next_tasks[j] = task + 1
        path.append((j, task, machine, start, end))
 
        result = iterative_search(instance, depth, i + 1, machines_t, jobs_t,
                                  next_tasks, prune_obj, path,
                                  start, j, max(makespan, end),
                                  next_bound, stats)
 
        path.pop()
        machines_t[machine] = old_machine_t
        jobs_t[j] = old_job_t
        next_tasks[j] = task
 
        if result is not None:
            stats["frontier"] -= len(children) - k - 1
            return result
 
    return None
 
 
def run_search(instance, num_machines, bound, stats):
    """One full depth-first search with a given bound."""
    depth = sum(len(job) for job in instance)
    n_jobs = len(instance)
    next_bound = [math.inf]
    stats["frontier"] = 0
    schedule = iterative_search(instance, depth, 0,
                                [0] * num_machines, [0] * n_jobs, [0] * n_jobs,
                                bound, [], -1, -1, 0, next_bound, stats)
    return schedule, next_bound[0]
 
 
def schedule_makespan(schedule):
    return max(entry[4] for entry in schedule)
 
 
def start_search(instance_class):
    """Phase 1: raise the bound with big jumps until a schedule fits.
    Phase 2: binary search between the proven lower value and the best
             makespan found, until they meet. The result is optimal.
 
    Returns (makespan, schedule, report).
    """
    t0 = time.perf_counter()
    stats = {"expanded": 0, "frontier": 0, "max_frontier": 0}
    instance = instance_class.ops
    num_machines = instance_class.n_machines
    increment, low = lower_bound(instance, num_machines)
    searches = 0
 
    bound = low
    while True:
        schedule, min_pruned = run_search(instance, num_machines, bound, stats)
        searches += 1
        if schedule is not None:
            break
        if min_pruned == math.inf:
            raise ValueError("No feasible schedule exists")
        low = max(low, min_pruned)       
        bound = min_pruned + increment   
 
    best = schedule
    high = schedule_makespan(best)
    time_to_best = time.perf_counter() - t0

    first = True
    while low < high:
        if first:
            mid = high - 1                         
            first = False                          
        else:
            step = max(1, (high - low) // 4)       
            mid = high - step                      
        schedule, min_pruned = run_search(instance, num_machines, mid, stats)
        searches += 1
        if schedule is not None:
            best = schedule
            high = schedule_makespan(best)         
            time_to_best = time.perf_counter() - t0
        else:
            low = max(low, mid + 1, min_pruned)
 
    total_time = time.perf_counter() - t0
    report = {
        "name" : instance_class.name,
        "makespan": high,
        "time_to_best": time_to_best,
        "total_time": total_time,
        "searches": searches,
        "expanded_nodes": stats["expanded"],
        "max_frontier": stats["max_frontier"]
    }
    return report
 
 
if __name__ == "__main__":
    instances = jsp_core.load_instances("./data/data_easy.txt")
    reports = []
    for key, value in instances.items():
        print(key)
        print(value)
        report = start_search(value)
        reports.append(report)
    df = pd.DataFrame(reports)
    print(df)
    df.to_csv("./results/report_ids.csv")