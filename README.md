# Job Shop Scheduling Problem (JSSP) — Systematic & Heuristic Search Evaluation

**Authors:** Allan Miyazono, Antonio Nápoles, Alejandro Mejía  
**Course:** Foundations of Artificial Intelligence  

---

## 1. Overview and Architecture
This repository provides a modular, reproducible benchmark of three state-space search paradigms to solve the Job Shop Scheduling Problem (JSSP) minimizing makespan ($C_{\max}$):
1. **Uninformed Search:** Iterative Cost-Bounding Search (Cost-Bounded DFS / IDMS).
2. **Informed Heuristic Search:** Weighted A* ($W \in \{1.0, 3.0, 5.0\}$) equipped with Job-Bound ($H_1$) and Combined Job-and-Machine Bound ($H_2$) heuristics.
3. **Local Search:** Simulated Annealing comparing Pairwise Swap ($\mathcal{N}_1$) and Shift/Insertion ($\mathcal{N}_2$) neighborhoods with adaptive temperature schedules.

---



## Files

| File | Purpose |
|---|---|
| `jsp_core.py` | Instance reader, representation, decoder and validator |
| `sa.py` | Simulated annealing with swap and insert neighborhoods |
| `run_experiments.py` | Experiments and ablation; writes the results to `results/` |
| `W_A*.py` | Weighted A* implementation with H1/H2 heuristics and automatic CSV/JSON logging |

## Data
### Weighted A* Instances

The `instances/` directory contains the input datasets used by Weighted A*:

- `benchmarkA*.txt`: standard benchmark instances.
- `data_easy.txt`: generated JSSP instances.
  
Each instance is declared using the keyword `instance`, followed by its identifier and a nested Python list of jobs. Each operation is represented by a pair `(machine_id, processing_time)`. Machine identifiers are zero-based.
The Weighted A* experiments evaluate 22 instances in total: 20 generated instances and 2 standard benchmarks.

## How to reproduce

Requires Python 3.8 or later; uses only the standard library.

```
python test_decode.py                                  # tests (a few seconds)
python run_experiments.py --time 5 --seeds 3           # quick test (~2 min)
python run_experiments.py                              # full experiment: 4 inst. x 2 neighborhoods x 10 seeds x 60 s
python run_experiments.py --summary-only               # rebuilds summary.csv from runs.csv
```

`--workers N` runs N processes in parallel. Since the limit is time-based, do not use more processes than physical cores.


### Weighted A* — Heuristic Search
Run the following command from the repository root:
```bash
python3 'W_A*.py'
```
The script automatically reads the JSSP instances from `instances/` and evaluates the H1 and H2 heuristics using weights $W \in \{1.0, 3.0, 5.0\}$.
Each instance and configuration has a 60-second time limit. The experiments measure makespan, execution time, expanded nodes, maximum frontier size, and execution status.
The script automatically generates the following logs:

- `results/resultados_weighted_a_star.csv`
- `results/resultados_weighted_a_star.json`
  
These files are generated automatically when the script finishes and can be used to reproduce the experimental comparisons.

## Results (`results/`)

- `config.json`: parameters, seeds, Python version and machine.
- `runs.csv`: one row per run (makespan, gap, whether it reached the BKS, time to best, iterations…).
- `history.csv`: convergence curve of each run.
- `summary.csv`: best, mean, standard deviation, worst, gap and success rate per instance and neighborhood.

### Weighted A* Results
- `resultados_weighted_a_star.csv`: automatically generated experimental records for H1 and H2 with weights 1.0, 3.0, and 5.0.
- `resultados_weighted_a_star.json`: JSON version of the same experimental records.
Both files contain the instance identifier, heuristic, weight, makespan, execution time, expanded nodes, maximum frontier size, and execution status (`FEASIBLE`, `TIMEOUT`, or `NO_SOLUTION`).
