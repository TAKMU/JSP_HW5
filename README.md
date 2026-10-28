# Job Shop Scheduling Problem (JSSP) — Systematic & Heuristic Search Evaluation

**Authors:** Allan Miyazono, Antonio Nápoles, Alejandro Mejía  
**Course:** Foundations of Artificial Intelligence  

---

## 1. Overview and Architecture
This repository provides a modular, reproducible benchmark of three state-space search paradigms to solve the Job Shop Scheduling Problem (JSSP) minimizing makespan ($C_{\max}$):
1. **Uninformed Search:** Iterative Cost-Bounding Search (Cost-Bounded DFS / IDMS).
2. **Informed Heuristic Search:** Weighted A* ($W \in \{1.0, 3.0\}$) equipped with Job-Bound ($H_1$) and Machine-Bound Bottleneck ($H_2$) heuristics.
3. **Local Search:** Simulated Annealing comparing Pairwise Swap ($\mathcal{N}_1$) and Shift/Insertion ($\mathcal{N}_2$) neighborhoods with adaptive temperature schedules.

---



## Files

| File | Purpose |
|---|---|
| `jsp_core.py` | Instance reader, representation, decoder and validator |
| `sa.py` | Simulated annealing with swap and insert neighborhoods |
| `run_experiments.py` | Experiments and ablation; writes the results to `results/` |

## Data

## How to reproduce

Requires Python 3.8 or later; uses only the standard library.

```
python test_decode.py                                  # tests (a few seconds)
python run_experiments.py --time 5 --seeds 3           # quick test (~2 min)
python run_experiments.py                              # full experiment: 4 inst. x 2 neighborhoods x 10 seeds x 60 s
python run_experiments.py --summary-only               # rebuilds summary.csv from runs.csv
```

`--workers N` runs N processes in parallel. Since the limit is time-based, do not use more processes than physical cores.

## Results (`results/`)

- `config.json`: parameters, seeds, Python version and machine.
- `runs.csv`: one row per run (makespan, gap, whether it reached the BKS, time to best, iterations…).
- `history.csv`: convergence curve of each run.
- `summary.csv`: best, mean, standard deviation, worst, gap and success rate per instance and neighborhood.
