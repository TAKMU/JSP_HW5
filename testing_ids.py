

instance_1 =  [
 [(2,  1),  (0,  3),  (1,  6),  (3,  7),  (5,  3),  (4,  6)],
 [(1,  8),  (2,  5),  (4, 10),  (5, 10),  (0, 10),  (3,  4)],
 [(2,  5),  (3,  4),  (5,  8),  (0,  9),  (1,  1),  (4,  7)],
 [(1,  5),  (0,  5),  (2,  5),  (3,  3),  (4,  8),  (5,  9)], 
 [(2,  9),  (1,  3),  (4,  5),  (5,  4),  (0,  3),  (3,  1)],
 [(1,  3),  (3,  3),  (5,  9),  (0, 10),  (4,  4),  (2,  1)]
 ]

NUM_MACHINES = 6

import math
 
 
def lower_bound(instance, num_machines):
    job_sums = [sum(d for _, d in job) for job in instance]
    machine_sums = [0] * num_machines
    for job in instance:
        for machine, duration in job:
            machine_sums[machine] += duration
    bound = max(max(job_sums), max(machine_sums))

 
 
def iterative_search(instance, depth, i, machines_t, jobs_t, next_tasks,
                     prune_obj, path, prev_start, prev_job, makespan, next_bound):
    if i == depth:
        return list(path)                
 
    for j, task in enumerate(next_tasks):
        if task >= len(instance[j]):
            continue                   
 
        machine, duration = instance[j][task]
        start = max(machines_t[machine], jobs_t[j])
        end = start + duration
 
        if start < prev_start or (start == prev_start and j < prev_job):
            continue
 
        if end > prune_obj:
            next_bound[0] = min(next_bound[0], end + 10)
            continue
 
        old_machine_t = machines_t[machine]
        old_job_t = jobs_t[j]
 
        machines_t[machine] = end
        jobs_t[j] = end
        next_tasks[j] = task + 1
        path.append((j, task, machine, start, end))
 
        result = iterative_search(instance, depth, i + 1, machines_t, jobs_t,
                                  next_tasks, prune_obj, path,
                                  start, j, max(makespan, end), next_bound)
 
        path.pop()
        machines_t[machine] = old_machine_t
        jobs_t[j] = old_job_t
        next_tasks[j] = task
 
        if result is not None:
            return result
 
    return None
 
 
def start_search(instance, num_machines, verbose=False):
    depth = sum(len(job) for job in instance)
    n_jobs = len(instance)
    machines_t = [0] * num_machines
    jobs_t = [0] * n_jobs
    next_task = [0] * n_jobs
 
    bound = lower_bound(instance, num_machines)
    while True:
        if verbose:
            print("Trying bound", bound)
        next_bound = [math.inf]
        schedule = iterative_search(instance, depth, 0, machines_t, jobs_t,
                                    next_task, bound, [], -1, -1, 0, next_bound)
        if schedule is not None:
            return bound, schedule
        if next_bound[0] == math.inf:
            raise ValueError("No feasible schedule exists")
        bound = next_bound[0]
 
 
def print_schedule(schedule, num_machines):
    for m in range(num_machines):
        tasks = sorted((s, e, j, t) for j, t, mm, s, e in schedule if mm == m)
        row = ", ".join(f"J{j}.{t} [{s}-{e})" for s, e, j, t in tasks)
        print(f"Machine {m}: {row}")
 
 
if __name__ == "__main__":
 
    makespan, schedule = start_search(instance_1, NUM_MACHINES, verbose=True)
    print("Lower bound:", lower_bound(instance_1, NUM_MACHINES))
    print("Optimal makespan:", makespan)
    print_schedule(schedule, NUM_MACHINES)
 