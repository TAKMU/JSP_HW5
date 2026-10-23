"""
jsp_core.py — Piezas base para la búsqueda local en JSP.

Representación: permutación con repetición de trabajos (operation-based).
  Cada trabajo j aparece m veces. La k-ésima aparición de j en la lista
  representa la k-ésima operación de j. Cualquier permutación es factible.

Instancias: se leen del archivo del equipo instances/data.txt TAL CUAL está.
  El archivo solo se abre en modo lectura; el código nunca lo modifica ni
  depende de una copia convertida a otro formato.
"""
import ast
import random
import re


class Instance:
    def __init__(self, name, n_jobs, n_machines, ops):
        self.name = name
        self.n_jobs = n_jobs
        self.n_machines = n_machines
        # ops[j][k] = (maquina, duracion) de la k-ésima operación del trabajo j
        self.ops = ops

    def __repr__(self):
        return f"Instance({self.name}, {self.n_jobs}x{self.n_machines})"


def load_instances(path):
    """
    Lee el formato del equipo (varias instancias en un archivo):

        instance abz5
        <descripción>
        10 10                                              <- n_trabajos n_maquinas
        [
        [(maquina, duracion), (maquina, duracion), ...],   <- un trabajo por renglón
        ...
        ]

    Las líneas de '+++' son separadores. Devuelve {nombre: Instance}.
    Nota: el comentario de abz7/abz8 dice "15 x 20", pero la línea de
    dimensiones dice "20 15" y los datos tienen 20 trabajos de 15 operaciones;
    se usa la línea de dimensiones.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    instances = {}
    # Cada bloque empieza con "instance <nombre>"
    for block in re.split(r"^\s*instance\s+", text, flags=re.M)[1:]:
        name = block.split()[0]
        # Primera línea que sean exactamente dos enteros: "n m"
        dims = re.search(r"^\s*(\d+)\s+(\d+)\s*$", block, flags=re.M)
        n, m = int(dims.group(1)), int(dims.group(2))
        # La lista de trabajos va del primer '[' después de "n m" a su ']' de cierre
        start = block.index("[", dims.end())
        end = block.rindex("]") + 1
        ops = ast.literal_eval(block[start:end])
        assert len(ops) == n and all(len(job) == m for job in ops), \
            f"{name}: dimensiones no coinciden con {n}x{m}"
        assert all(sorted(mc for mc, _ in job) == list(range(m)) for job in ops), \
            f"{name}: algún trabajo no visita cada máquina exactamente una vez"
        instances[name] = Instance(name, n, m, [list(job) for job in ops])
    return instances


# Nombre anterior, se conserva para no romper código que ya lo use.
load_instances_team = load_instances


def random_solution(inst, rng):
    """Permutación aleatoria: cada trabajo aparece n_machines veces."""
    perm = [j for j in range(inst.n_jobs) for _ in range(inst.n_machines)]
    rng.shuffle(perm)
    return perm


def decode(inst, perm):
    """
    Convierte una permutación en un calendario semi-activo.

    Recorre la lista de izquierda a derecha; cada operación inicia lo más
    temprano posible respetando:
      - precedencia: después de que termine la operación anterior del trabajo
      - capacidad:   después de que la máquina quede libre
    Devuelve (makespan, starts) con starts[j][k] = inicio de la op k del trabajo j.
    Costo: O(n·m), lineal en el número de operaciones.
    """
    n, m = inst.n_jobs, inst.n_machines
    next_op = [0] * n        # siguiente operación pendiente de cada trabajo
    job_ready = [0] * n      # cuándo termina la última op programada del trabajo
    mach_ready = [0] * m     # cuándo queda libre cada máquina
    starts = [[0] * m for _ in range(n)]

    for j in perm:
        k = next_op[j]
        machine, dur = inst.ops[j][k]
        s = max(job_ready[j], mach_ready[machine])
        starts[j][k] = s
        job_ready[j] = s + dur
        mach_ready[machine] = s + dur
        next_op[j] += 1

    return max(job_ready), starts


def check_schedule(inst, starts):
    """
    Verifica independientemente que un calendario cumpla todas las restricciones.
    Útil como prueba y para la defensa: demuestra que las soluciones son válidas.
    """
    n, m = inst.n_jobs, inst.n_machines
    # Precedencia dentro de cada trabajo
    for j in range(n):
        for k in range(1, m):
            prev_end = starts[j][k - 1] + inst.ops[j][k - 1][1]
            if starts[j][k] < prev_end:
                return False, f"precedencia violada en trabajo {j}, op {k}"
    # Sin traslapes en cada máquina
    by_machine = {}
    for j in range(n):
        for k in range(m):
            mach, dur = inst.ops[j][k]
            by_machine.setdefault(mach, []).append((starts[j][k], starts[j][k] + dur, j))
    for mach, ivs in by_machine.items():
        ivs.sort()
        for (s1, e1, j1), (s2, e2, j2) in zip(ivs, ivs[1:]):
            if s2 < e1:
                return False, f"traslape en máquina {mach}: trabajos {j1} y {j2}"
    return True, "ok"
