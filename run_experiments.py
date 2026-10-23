"""
run_experiments.py — Ablación de vecindarios (swap vs insert) del recocido simulado.

Lee las instancias de instances/data.txt TAL CUAL (el archivo del equipo, sin
modificar) y corre simulated_annealing para cada instancia x vecindario x semilla.
Cada solución se verifica con check_schedule antes de guardarse.

Archivos que genera en results/:
  config.json   parámetros, versión de Python y equipo
  runs.csv      una fila por corrida (se escribe en cuanto termina cada corrida)
  history.csv   curvas de convergencia (tiempo, mejor makespan) de cada corrida
  summary.csv   resumen por instancia y vecindario, con tasa de éxito

Uso (desde esta carpeta):
  python run_experiments.py                              # todo: 10 semillas x 60 s
  python run_experiments.py --time 5 --seeds 3           # prueba rápida
  python run_experiments.py --instances abz5 abz6 --workers 7
  python run_experiments.py --summary-only               # rehace summary.csv desde runs.csv
"""
import argparse
import csv
import datetime
import inspect
import json
import os
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from jsp_core import load_instances, decode, check_schedule
from sa import simulated_annealing

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "instances", "data.txt")

# Valores de referencia de la literatura.
#   bks = mejor solución conocida (cota superior), lb = cota inferior.
#   Si bks == lb, el óptimo está demostrado.
# Fuente: tabla de instancias de jsp-instance-utils
#   https://jsp-instance-utils.readthedocs.io/en/latest/instances-table.html
#   (abz5/abz6: Applegate & Cook 1991; abz7/abz8 BKS: Henning 2002).
REFERENCE = {
    "abz5": {"bks": 1234, "lb": 1234},
    "abz6": {"bks": 943, "lb": 943},
    "abz7": {"bks": 656, "lb": 656},
    "abz8": {"bks": 665, "lb": 648},   # abierto: óptimo no demostrado
}

RUN_FIELDS = ["instance", "n_jobs", "n_machines", "neighborhood", "seed", "time_limit",
              "best_makespan", "bks", "gap_pct", "reached_bks", "time_to_best",
              "iterations", "accepted", "reheats", "T0"]


def gap(cmax, name):
    """Porcentaje por encima de la mejor solución conocida."""
    ref = REFERENCE.get(name)
    return 100.0 * (cmax - ref["bks"]) / ref["bks"] if ref else float("nan")


def run_one(task):
    """Una corrida: (instancia, vecindario, semilla, tiempo). Se ejecuta en otro proceso."""
    inst, neighborhood, seed, time_limit = task
    r = simulated_annealing(inst, seed=seed, time_limit=time_limit, neighborhood=neighborhood)
    cmax, starts = decode(inst, r["best_perm"])
    ok, msg = check_schedule(inst, starts)
    if not ok or cmax != r["best_makespan"]:
        raise RuntimeError(f"{inst.name} {neighborhood} seed={seed}: solución inválida ({msg})")
    return inst, neighborhood, seed, time_limit, r


def write_config(path, args, data_path, names):
    """Guarda todo lo necesario para reproducir los experimentos."""
    sa_defaults = {k: v.default for k, v in inspect.signature(simulated_annealing).parameters.items()
                   if v.default is not inspect.Parameter.empty and k not in ("seed", "time_limit", "neighborhood")}
    config = {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "command": " ".join([os.path.basename(sys.argv[0])] + sys.argv[1:]),
        "data_file": os.path.relpath(data_path, HERE),
        "instances": names,
        "neighborhoods": args.neighborhoods,
        "seeds": list(range(args.seeds)),
        "time_limit_s": args.time,
        "workers": args.workers,
        "sa_parameters": sa_defaults,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "reference_values": REFERENCE,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def summarize(runs_path, summary_path):
    """Lee runs.csv y escribe summary.csv (también imprime la tabla)."""
    with open(runs_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups = {}
    for r in rows:
        groups.setdefault((r["instance"], r["neighborhood"]), []).append(r)

    fields = ["instance", "neighborhood", "runs", "best", "mean", "std", "worst", "bks", "lb",
              "optimal_known", "gap_best_pct", "gap_mean_pct", "success_rate_pct", "mean_time_to_best"]
    print(f"\n{'instancia':9} {'vecindario':10} {'n':>3} {'mejor':>6} {'media':>8} {'desv':>6} {'peor':>6} "
          f"{'BKS':>5} {'gap_mejor':>9} {'gap_media':>9} {'éxito':>6}")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for (name, nb), rs in sorted(groups.items()):
            c = [int(r["best_makespan"]) for r in rs]
            mean = statistics.mean(c)
            std = statistics.stdev(c) if len(c) > 1 else 0.0
            ttb = statistics.mean(float(r["time_to_best"]) for r in rs)
            ref = REFERENCE.get(name, {})
            succ = 100.0 * sum(r["reached_bks"] == "True" for r in rs) / len(rs)
            w.writerow({"instance": name, "neighborhood": nb, "runs": len(c), "best": min(c),
                        "mean": f"{mean:.2f}", "std": f"{std:.2f}", "worst": max(c),
                        "bks": ref.get("bks", ""), "lb": ref.get("lb", ""),
                        "optimal_known": ref.get("bks") == ref.get("lb") if ref else "",
                        "gap_best_pct": f"{gap(min(c), name):.2f}", "gap_mean_pct": f"{gap(mean, name):.2f}",
                        "success_rate_pct": f"{succ:.1f}", "mean_time_to_best": f"{ttb:.2f}"})
            print(f"{name:9} {nb:10} {len(c):3} {min(c):6} {mean:8.1f} {std:6.1f} {max(c):6} "
                  f"{ref.get('bks', '-'):>5} {gap(min(c), name):8.2f}% {gap(mean, name):8.2f}% {succ:5.0f}%")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=DEFAULT_DATA, help="archivo de instancias (por defecto instances/data.txt)")
    p.add_argument("--instances", nargs="*", help="nombres (por defecto: todas las del archivo)")
    p.add_argument("--neighborhoods", nargs="*", default=["swap", "insert"])
    p.add_argument("--seeds", type=int, default=10, help="número de semillas (0..N-1)")
    p.add_argument("--time", type=float, default=60.0, help="segundos por corrida (máximo 60 según la tarea)")
    p.add_argument("--workers", type=int, default=7,
                   help="procesos en paralelo; no uses más que núcleos físicos (el límite es por tiempo)")
    p.add_argument("--out", default=os.path.join(HERE, "results"))
    p.add_argument("--summary-only", action="store_true", help="solo rehace summary.csv a partir de runs.csv")
    a = p.parse_args()

    runs_path = os.path.join(a.out, "runs.csv")
    summary_path = os.path.join(a.out, "summary.csv")
    if a.summary_only:
        summarize(runs_path, summary_path)
        return

    if a.seeds < 1:
        p.error("--seeds debe ser al menos 1")
    if a.time > 60:
        print("AVISO: la tarea permite máximo 60 s por instancia y algoritmo.\n")
    cpus = os.cpu_count() or 1
    if a.workers > cpus:
        print(f"AVISO: --workers={a.workers} pero esta computadora reporta {cpus} núcleos lógicos. "
              f"Con límite por tiempo, los procesos compiten por CPU y los resultados serían injustos.\n")

    insts = load_instances(a.data)
    names = a.instances or list(insts)
    missing = [n for n in names if n not in insts]
    if missing:
        p.error(f"instancias no encontradas: {missing}. Disponibles: {list(insts)}")

    print(f"Datos: {os.path.relpath(a.data, HERE)}")
    tasks = [(insts[n], nb, s, a.time) for n in names for nb in a.neighborhoods for s in range(a.seeds)]
    est = len(tasks) * a.time / a.workers / 60
    print(f"{len(tasks)} corridas x {a.time:g} s con {a.workers} proceso(s) -> ~{est:.1f} min\n")

    os.makedirs(a.out, exist_ok=True)
    write_config(os.path.join(a.out, "config.json"), a, a.data, names)

    t0 = time.perf_counter()
    with open(runs_path, "w", newline="", encoding="utf-8") as f_runs, \
         open(os.path.join(a.out, "history.csv"), "w", newline="", encoding="utf-8") as f_hist, \
         ProcessPoolExecutor(max_workers=a.workers) as pool:
        w_runs = csv.DictWriter(f_runs, fieldnames=RUN_FIELDS)
        w_runs.writeheader()
        w_hist = csv.writer(f_hist)
        w_hist.writerow(["instance", "neighborhood", "seed", "time", "best_makespan"])

        futures = [pool.submit(run_one, t) for t in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            inst, nb, seed, tl, r = fut.result()
            ref = REFERENCE.get(inst.name)
            w_runs.writerow({
                "instance": inst.name, "n_jobs": inst.n_jobs, "n_machines": inst.n_machines,
                "neighborhood": nb, "seed": seed, "time_limit": tl,
                "best_makespan": r["best_makespan"], "bks": ref["bks"] if ref else "",
                "gap_pct": f"{gap(r['best_makespan'], inst.name):.2f}",
                "reached_bks": bool(ref) and r["best_makespan"] <= ref["bks"],
                "time_to_best": f"{r['time_to_best']:.3f}", "iterations": r["iterations"],
                "accepted": r["accepted"], "reheats": r["reheats"], "T0": f"{r['T0']:.2f}",
            })
            for t, c in r["history"]:
                w_hist.writerow([inst.name, nb, seed, f"{t:.3f}", c])
            f_runs.flush()
            f_hist.flush()
            print(f"[{i:3}/{len(tasks)}] {inst.name:5} {nb:6} seed={seed:2}  Cmax={r['best_makespan']:5}  "
                  f"gap={gap(r['best_makespan'], inst.name):5.1f}%  t_best={r['time_to_best']:5.1f}s")

    summarize(runs_path, summary_path)
    print(f"\nListo en {(time.perf_counter() - t0) / 60:.1f} min. Resultados en: {a.out}")


if __name__ == "__main__":
    main()
