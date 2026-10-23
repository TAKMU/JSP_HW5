"""
sa.py — Recocido simulado (Simulated Annealing) para JSP.

Representación: permutación con repetición de trabajos (ver jsp_core.py).

Vecindarios (para la ablación A vs B):
  - "swap":   intercambia los elementos en dos posiciones i, j.
  - "insert": saca el elemento de la posición i y lo inserta en la posición j.
Solo se consideran movimientos entre trabajos distintos: mover dos copias del
mismo trabajo deja la permutación igual (movimiento nulo).

Esquema de temperatura:
  - T0 se calibra para aceptar ~80% de los empeoramientos al inicio.
  - Enfriamiento geométrico: cada L iteraciones, T <- alpha * T.
  - Recalentamiento: si T < T_min, se vuelve a T0 partiendo de la mejor
    solución, para aprovechar todo el presupuesto de tiempo.
"""
import math
import random
import time

from jsp_core import decode, random_solution


# ---------------------------------------------------------------- vecindarios
def random_move(perm, rng, neighborhood):
    """Devuelve un vecino aleatorio (lista nueva) de perm."""
    n = len(perm)
    while True:
        i, j = rng.randrange(n), rng.randrange(n)
        if i != j and perm[i] != perm[j]:
            break
    new = perm[:]
    if neighborhood == "swap":
        new[i], new[j] = new[j], new[i]
    elif neighborhood == "insert":
        x = new.pop(i)
        new.insert(j, x)
    else:
        raise ValueError(f"vecindario desconocido: {neighborhood}")
    return new


# ------------------------------------------------------- calibración de T0
def initial_temperature(inst, perm, rng, neighborhood, accept_prob=0.8, samples=200):
    """
    T0 tal que exp(-delta_promedio / T0) = accept_prob, usando el promedio
    de los empeoramientos observados en una muestra de movimientos aleatorios.
    """
    base, _ = decode(inst, perm)
    worse = []
    for _ in range(samples):
        c, _ = decode(inst, random_move(perm, rng, neighborhood))
        if c > base:
            worse.append(c - base)
    avg = sum(worse) / len(worse) if worse else 1.0
    return -avg / math.log(accept_prob)


# --------------------------------------------------------------- algoritmo
def simulated_annealing(inst, seed=0, time_limit=60.0, neighborhood="insert",
                        alpha=0.97, t_min=0.1, iters_per_temp=None):
    """
    Ejecuta SA hasta agotar time_limit segundos.

    Devuelve un dict con:
      best_makespan, best_perm, time_to_best, iterations, accepted,
      reheats, history [(tiempo, mejor_makespan), ...]
    """
    rng = random.Random(seed)
    t_start = time.perf_counter()

    if iters_per_temp is None:
        iters_per_temp = inst.n_jobs * inst.n_machines  # L = número de operaciones

    current = random_solution(inst, rng)
    cur_cost, _ = decode(inst, current)
    best, best_cost = current[:], cur_cost
    time_to_best = 0.0
    history = [(0.0, best_cost)]

    T0 = initial_temperature(inst, current, rng, neighborhood)
    T = T0
    iterations = accepted = reheats = 0

    while True:
        elapsed = time.perf_counter() - t_start
        if elapsed >= time_limit:
            break

        for _ in range(iters_per_temp):
            cand = random_move(current, rng, neighborhood)
            cand_cost, _ = decode(inst, cand)
            delta = cand_cost - cur_cost
            iterations += 1

            # Criterio de Metropolis
            if delta <= 0 or rng.random() < math.exp(-delta / T):
                current, cur_cost = cand, cand_cost
                accepted += 1
                if cur_cost < best_cost:
                    best, best_cost = current[:], cur_cost
                    time_to_best = time.perf_counter() - t_start
                    history.append((time_to_best, best_cost))

        T *= alpha
        if T < t_min:            # sistema "congelado": recalentar desde la mejor
            T = T0
            current, cur_cost = best[:], best_cost
            reheats += 1

    return {
        "best_makespan": best_cost,
        "best_perm": best,
        "time_to_best": time_to_best,
        "iterations": iterations,
        "accepted": accepted,
        "reheats": reheats,
        "T0": T0,
        "history": history,
    }
