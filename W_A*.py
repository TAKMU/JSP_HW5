import heapq
import time
#para exportar los archivos
import csv
import json
import re
import ast

class NodoJSP:
#self es decir como nodo (permitiendo crear diferentes nodos), por eso se crea el objeto
  def __init__(self, num_trabajos, num_maquinas):
    self.g = 0  # Tiempo transcurrido (donde estoy actualmente)
    # Cuántos pasos ha completado cada trabajo (empiezan en 0)
    self.operaciones_completadas = [0] * num_trabajos
    # En qué minuto queda libre cada plato para su siguiente paso
    self.t_ready = [0] * num_trabajos
    # En qué minuto queda libre cada máquina
    self.r_maquinas = [0] * num_maquinas
    # Registro de pasos: lista de tuplas (trabajo, máquina, inicio, fin)
    #recordar qué hizo, en qué máquina y a qué hora 
    self.plan_actual = []
#permite saber si ya se completo los trabajos. operaciones_completadas [0,0,0] 
  def esta_completo(self, instancia):
# checa el numero de platos (trabajos)
    for trabajo_id in range(len(instancia)):
#checa cuantos pasos tiene el plato (primera iteracion el plato 0)
      total_pasos = len(instancia[trabajo_id])
#checa si el plato ya hizo todos sus trabajos o no
      if self.operaciones_completadas[trabajo_id] < total_pasos:
        return False
    return True

  def copiar(self):
#Crea una copia independiente del nodo para generar un hijo.
    nuevo = NodoJSP(len(self.t_ready), len(self.r_maquinas))
    nuevo.g = self.g
#usa list para crear un nodo nuevo sin modificar los valores el original
    nuevo.operaciones_completadas = list(self.operaciones_completadas)
    nuevo.t_ready = list(self.t_ready)
    nuevo.r_maquinas = list(self.r_maquinas)
    nuevo.plan_actual = list(self.plan_actual)
    return nuevo


# 3. HEURÍSTICAS H1 y H2

def calcular_H1(nodo, instancia):
  #ocupa una accion (funcion)  que el nodo puede hacer
  if nodo.esta_completo(instancia):
    return 0
  #cuanto tiempo falta por trabajo
  minutos_finales_por_trabajo = []
#que operaciones le falta a un plato 
  for j in range(len(instancia)):
    paso_actual = nodo.operaciones_completadas[j]
#de la instancia toma un plato (j) y del paso actual en adeltante 
    operaciones_restantes = instancia[j][paso_actual:]
    # Suma de la duración de lo que le falta a este trabajo
    tiempo_que_falta = 0
    for idmaquina, duracion in operaciones_restantes:
        tiempo_que_falta = ( tiempo_que_falta + duracion) 

    # Terminará cuando quede libre su paso previo + el tiempo que le falta
    fin_estimado_trabajo = nodo.t_ready[j] + tiempo_que_falta
    minutos_finales_por_trabajo.append(fin_estimado_trabajo)

  # El trabajo más tardado define el Makespan estimado
  makespan_estimado = max(minutos_finales_por_trabajo)

  # La heurística h es lo que falta a partir del reloj actual g
  #cero para evitar tiempos negativos
  return max(0, makespan_estimado - nodo.g)


def calcular_H2(nodo, instancia, num_maquinas):
  if nodo.esta_completo(instancia):
    return 0

  # Partimos del valor que da H1
  valor_h1 = calcular_H1(nodo, instancia)

  minutos_finales_por_maquina = []
#busca la maquina 
  for m in range(num_maquinas):
    carga_restante_en_esta_maquina = 0
#va por plato buscando la maquina
    for j in range(len(instancia)):
      paso_actual = nodo.operaciones_completadas[j]
      operaciones_restantes = instancia[j][paso_actual:]
#suma la maquina buscada en ese plato
      for maq_id, duracion in operaciones_restantes:
        if maq_id == m:
          carga_restante_en_esta_maquina += duracion

    # Cuándo terminará la máquina = minuto en que se desocupa + trabajo acumulado
    fin_estimado_maquina = (
        nodo.r_maquinas[m] + carga_restante_en_esta_maquina
    )
    minutos_finales_por_maquina.append(fin_estimado_maquina)

  makespan_por_maquinas = max(minutos_finales_por_maquina)
  falta_por_maquinas = max(0, makespan_por_maquinas - nodo.g)

  # H2 elige el peor cuello de botella entre trabajos y máquinas
  return max(valor_h1, falta_por_maquinas)


# 4. ALGORITMO WEIGHTED A*

def weighted_a_star(
    instancia,
    tipo_heuristica="H1",
    peso_w=1.0,
    limite_tiempo_segundos=60,
):
  num_trabajos = len(instancia)
  num_maquinas = len(instancia[0])

  nodo_inicial = NodoJSP(num_trabajos, num_maquinas)

  if tipo_heuristica == "H1":
    h_inicial = calcular_H1(nodo_inicial, instancia)
  else:
    h_inicial = calcular_H2(nodo_inicial, instancia, num_maquinas)
#formula de Weighted A*
  f_inicial = nodo_inicial.g + (peso_w * h_inicial)

#
  contador = 0
  frontera = []
  heapq.heappush(frontera, (f_inicial, contador, nodo_inicial))

  nodos_expandidos = 0
  maximo_tamano_frontera = 1
  tiempo_inicio = time.time()

  while len(frontera) > 0:
    if time.time() - tiempo_inicio > limite_tiempo_segundos:
      return None, "TIMEOUT", nodos_expandidos, maximo_tamano_frontera

    if len(frontera) > maximo_tamano_frontera:
      maximo_tamano_frontera = len(frontera)

    # Sacamos el nodo con menor f(n)
    f_actual, _, nodo_actual = heapq.heappop(frontera)
    nodos_expandidos += 1

    # ¿Llegamos a la meta?
    if nodo_actual.esta_completo(instancia):
      tiempo_total = round(time.time() - tiempo_inicio, 4)
      return (
          nodo_actual,
          tiempo_total,
          nodos_expandidos,
          maximo_tamano_frontera,
      )

    # GENERACIÓN DE SUCESORES (Probar qué plato programar a continuación)
    for trabajo_id in range(num_trabajos):
      paso = nodo_actual.operaciones_completadas[trabajo_id]
      # Si este plato aún tiene operaciones pendientes por programar
      if paso < len(instancia[trabajo_id]):
        maquina_id, duracion = instancia[trabajo_id][paso]
        # REGLA CLAVE: La operación solo puede empezar cuando AMBOS estén libres
        inicio = max(
            nodo_actual.t_ready[trabajo_id], nodo_actual.r_maquinas[maquina_id]
        )
        fin = inicio + duracion

        # Creamos el nuevo nodo hijo aplicando esta decisión
        hijo = nodo_actual.copiar()
        hijo.operaciones_completadas[trabajo_id] += 1
        hijo.t_ready[trabajo_id] = fin
        hijo.r_maquinas[maquina_id] = fin
        hijo.g = max(nodo_actual.g, fin)
        hijo.plan_actual.append((trabajo_id, maquina_id, inicio, fin))

        # Calculamos h para el hijo
        if tipo_heuristica == "H1":
          h_hijo = calcular_H1(hijo, instancia)
        else:
          h_hijo = calcular_H2(hijo, instancia, num_maquinas)

        # f(n) = g(n) + W * h(n)
        f_hijo = hijo.g + (peso_w * h_hijo)

        contador += 1
        heapq.heappush(frontera, (f_hijo, contador, hijo))

  return None, "NO_SOLUTION", nodos_expandidos, maximo_tamano_frontera

# 5. PARSER Y EXPERIMENTACIÓN CON EXPORTACIÓN AUTOMÁTICA (CSV / JSON)

def parse_instances(file_content_or_path):
    """Extrae las instancias de los archivos .txt usando su formato estándar."""
    try:
        with open(file_content_or_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = file_content_or_path

    pattern = re.compile(
        r'instance\s+([\w\d_]+).*?(\[\s*\[.*?\]\s*\])',
        re.DOTALL
    )
    instancias = {}
    for match in pattern.finditer(content):
        nombre = match.group(1).strip()
        lista_str = match.group(2).strip()
        try:
            instancias[nombre] = ast.literal_eval(lista_str)
        except Exception as e:
            print(f"Error parseando {nombre}: {e}")
    return instancias

# Lista de archivos a evaluar con su respectiva etiqueta
archivos_benchmark = [
   ("benchmarkA*.txt", "estandar"),
    ("data_easy.txt", "generada")
]

configuraciones = [
    ("H1", 1.0),
    ("H1", 3.0),
    ("H2", 1.0),
    ("H2", 3.0),
]
TIEMPO_LIMITE = 60.0
registros = []

print("=" * 105)
print(f"{'Archivo':<12} | {'Instancia':<15} | {'Config':<12} | {'Makespan':<10} | {'Tiempo (s)':<12} | {'Nodos Exp.':<12} | {'Status':<10}")
print("=" * 105)

for ruta, etiqueta in archivos_benchmark:
    instancias_dict = parse_instances(ruta)
    if not instancias_dict:
        print(f"Aviso: No se encontraron instancias o no existe el archivo '{ruta}'.")
        continue

    for nombre_instancia, matriz in instancias_dict.items():
        for heur, peso in configuraciones:
            config_nombre = f"{heur} (W={peso})"
            nodo_sol, t_calc, n_exp, max_front = weighted_a_star(
                instancia=matriz,
                tipo_heuristica=heur,
                peso_w=peso,
                limite_tiempo_segundos= TIEMPO_LIMITE
            )

            status = "TIMEOUT" if t_calc == "TIMEOUT" else ("feasible" if nodo_sol else "NO_SOLUTION")
            makespan_val = nodo_sol.g if nodo_sol else None
            tiempo_val = t_calc if status != "TIMEOUT" else f">{TIEMPO_LIMITE}"

            # Guardar en memoria para exportar
            registros.append({
                "archivo_origen": ruta,
                "conjunto": etiqueta,
                "instancia": nombre_instancia,
                "heuristica": heur,
                "peso_w": peso,
                "configuracion": config_nombre,
                "makespan": makespan_val,
                "tiempo_segundos": tiempo_val,
                "nodos_expandidos": n_exp,
                "max_frontera": max_front,
                "status": status
            })

            makespan_str = str(makespan_val) if makespan_val is not None else "—"
            print(f"{etiqueta:<12} | {nombre_instancia:<15} | {config_nombre:<12} | {makespan_str:<10} | {str(tiempo_val):<12} | {n_exp:<12} | {status:<10}")

print("-" * 105)

# Guardar logs automáticos en CSV
csv_file = "resultados_weighted_a_star.csv"
campos = ["archivo_origen", "conjunto", "instancia", "heuristica", "peso_w", "configuracion", "makespan", "tiempo_segundos", "nodos_expandidos", "max_frontera", "status"]
with open(csv_file, mode="w", newline="", encoding="utf-8") as f_csv:
    writer = csv.DictWriter(f_csv, fieldnames=campos)
    writer.writeheader()
    writer.writerows(registros)
print(f"Archivo CSV generado: {csv_file}")

# Guardar logs automáticos en JSON
json_file = "resultados_weighted_a_star.json"
with open(json_file, mode="w", encoding="utf-8") as f_json:
    json.dump(registros, f_json, indent=4)
print(f"Archivo JSON generado: {json_file}")