import argparse
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = "./instances/data_generated.txt"

CONFIG = {
    "easy":   {"count": 10, "jobs": 3,  "machines": 3,  "min_time": 1, "max_time": 5},
    "medium": {"count": 8,  "jobs": 4,  "machines": 4,  "min_time": 1, "max_time": 10},
    "hard":   {"count": 2,  "jobs": 6, "machines": 6, "min_time": 1, "max_time": 20},
}

SEPARATOR = " +++++++++++++++++++++++++++++"


def generate_instance(jobs_count, machines_count, min_time, max_time, rng):
    """Cada trabajo visita todas las máquinas una vez, en orden aleatorio."""
    instance = []

    for _ in range(jobs_count):
        machine_order = list(range(machines_count))
        rng.shuffle(machine_order)

        job = [
            (machine, rng.randint(min_time, max_time))
            for machine in machine_order
        ]
        instance.append(job)

    return instance


def write_team_file(output_path, seed):
    """Escribe todas las instancias de CONFIG en un solo archivo, formato del equipo."""
    rng = random.Random(seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [""]
    summary = []

    for category, cfg in CONFIG.items():
        for index in range(1, cfg["count"] + 1):
            name = f"{category}_{index:02d}"
            instance = generate_instance(
                cfg["jobs"],
                cfg["machines"],
                cfg["min_time"],
                cfg["max_time"],
                rng,
            )

            lines += [
                SEPARATOR,
                f" instance {name}",
                SEPARATOR,
                f" Generada aleatoriamente ({category}, semilla {seed}), "
                f"duraciones de {cfg['min_time']} a {cfg['max_time']}",
                f" {cfg['jobs']} {cfg['machines']}",
                " [",
            ]
            for k, job in enumerate(instance):
                comma = "," if k < len(instance) - 1 else ""
                lines.append(f" {job!r}{comma}")
            lines.append(" ]")

            summary.append(f"  {name}: {cfg['jobs']} trabajos x {cfg['machines']} máquinas, "
                           f"duraciones {cfg['min_time']}-{cfg['max_time']}")

    lines.append(SEPARATOR)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=42, help="semilla (misma semilla = mismas instancias)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="archivo de salida")
    a = p.parse_args()

    summary = write_team_file(a.out, a.seed)
    print(f"Se generaron {len(summary)} instancias (semilla {a.seed}):")
    print("\n".join(summary))
    print(f"\nGuardado en: {Path(a.out).resolve()}")


if __name__ == "__main__":
    main()
