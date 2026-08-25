"""Motor estadístico para picks de fútbol.
No usa mercados inventados de goles por equipo.
Genera probabilidades para resultado, doble oportunidad, goles, BTTS,
tarjetas y remates. Las probabilidades de goles/resultado salen de un
modelo Poisson calibrado con GF/GC recientes de ambos equipos.
"""
import math
from dataclasses import dataclass, field
from typing import List

@dataclass
class HistorialEquipo:
    nombre: str
    partidos_evaluados: int
    goles_favor_prom: float
    goles_contra_prom: float
    tarjetas_prom: float
    remates_totales_prom: float
    remates_arco_prom: float
    partidos_ambos_anotan_pct: float
    goles_favor_lista: List[float] = field(default_factory=list)
    goles_contra_lista: List[float] = field(default_factory=list)
    tarjetas_lista: List[float] = field(default_factory=list)
    remates_totales_lista: List[float] = field(default_factory=list)

def _confianza(n):
    if n >= 15: return "Alta"
    if n >= 10: return "Media-alta"
    if n >= 7: return "Media"
    return "Baja"

def _poisson(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def _matriz_goles(lh, va, maxg=8):
    # Ataque local + defensa visitante y ataque visitante + defensa local.
    xg_l = max(0.15, 0.58 * lh.goles_favor_prom + 0.42 * va.goles_contra_prom)
    xg_v = max(0.15, 0.58 * va.goles_favor_prom + 0.42 * lh.goles_contra_prom)
    # Ajuste suave de localía, sin exagerar.
    xg_l *= 1.06
    xg_v *= 0.96
    pl = [_poisson(k, xg_l) for k in range(maxg + 1)]
    pv = [_poisson(k, xg_v) for k in range(maxg + 1)]
    return xg_l, xg_v, pl, pv

def _sum_probs(pl, pv, fn):
    return sum(pl[i] * pv[j] for i in range(len(pl)) for j in range(len(pv)) if fn(i, j))

def _empirical_total(a, b, line, over):
    if not a or not b: return None
    ok = sum((x + y > line) if over else (x + y < line) for x in a for y in b)
    return ok / (len(a) * len(b))

def _candidate(mercado, prob, familia, justificacion, n, min_prob=0.56):
    if prob is None or not 0 <= prob <= 1 or prob < min_prob: return None
    # Penalización mínima por muestras pequeñas; no modifica la probabilidad visible.
    score = prob * (0.82 + 0.18 * min(n, 20) / 20)
    return {"mercado": mercado, "probabilidad": round(prob * 100, 1), "score": round(score, 4), "confianza": _confianza(n), "familia": familia, "justificacion": justificacion}

def evaluar_mercados_candidatos(local, visitante):
    n = min(local.partidos_evaluados, visitante.partidos_evaluados)
    if n < 5: return []
    xg_l, xg_v, pl, pv = _matriz_goles(local, visitante)
    total_xg = xg_l + xg_v
    c = []

    # RESULTADO 1X2 + DOBLE OPORTUNIDAD.
    p_l = _sum_probs(pl, pv, lambda i,j: i > j)
    p_e = _sum_probs(pl, pv, lambda i,j: i == j)
    p_v = _sum_probs(pl, pv, lambda i,j: i < j)
    resultado = [(f"Gana {local.nombre}", p_l), ("Empate", p_e), (f"Gana {visitante.nombre}", p_v)]
    mejor = max(resultado, key=lambda x:x[1])
    z = _candidate(mejor[0], mejor[1], "resultado", f"Modelo de goles esperado: {xg_l:.2f} para {local.nombre} y {xg_v:.2f} para {visitante.nombre}, usando los últimos {n} partidos evaluados.", n, .50)
    if z: c.append(z)
    dc = [(f"{local.nombre} o Empate", p_l+p_e), (f"{visitante.nombre} o Empate", p_v+p_e), (f"{local.nombre} o {visitante.nombre}", p_l+p_v)]
    bestdc = max(dc, key=lambda x:x[1])
    z = _candidate(f"Doble oportunidad: {bestdc[0]}", bestdc[1], "doble", f"La suma de probabilidades 1X2 del modelo da {bestdc[1]*100:.1f}% para esta doble oportunidad.", n, .64)
    if z: c.append(z)

    # GOLES TOTALES. Solo líneas de partido, nunca "goles propios".
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        over = 1 - sum(_poisson(k, total_xg) for k in range(int(math.floor(line))+1))
        under = 1 - over
        for label,prob in ((f"Más de {line} goles",over),(f"Menos de {line} goles",under)):
            z=_candidate(label,prob,"goles",f"xG total estimado: {total_xg:.2f}. El modelo proyecta {prob*100:.1f}% para este mercado.",n,.57)
            if z:c.append(z)

    # BTTS por Poisson + tendencia histórica.
    btts_model = 1 - pl[0] - pv[0] + pl[0]*pv[0]
    btts_hist = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 200
    btts = 0.72*btts_model + 0.28*btts_hist
    label = "Ambos anotan: Sí" if btts >= .5 else "Ambos anotan: No"
    prob = btts if btts >= .5 else 1-btts
    z=_candidate(label,prob,"btts",f"Modelo BTTS {btts_model*100:.1f}% + tendencia histórica combinada {btts_hist*100:.1f}%.",n,.57)
    if z:c.append(z)

    # TARJETAS y REMATES: combinamos muestras de ambos equipos y elegimos la línea más estable.
    for familia, lista_a, lista_b, lineas, nombre in [
        ("tarjetas",local.tarjetas_lista,visitante.tarjetas_lista,(2.5,3.5,4.5,5.5,6.5),"tarjetas"),
        ("remates",local.remates_totales_lista,visitante.remates_totales_lista,(17.5,19.5,21.5,23.5,25.5,27.5),"remates totales")]:
        opciones=[]
        for line in lineas:
            po=_empirical_total(lista_a,lista_b,line,True); pu=_empirical_total(lista_a,lista_b,line,False)
            if po is not None: opciones.append((po,f"Más de {line} {nombre}",f"El historial combinado supera {line} {nombre} en {po*100:.1f}% de los escenarios.",line))
            if pu is not None: opciones.append((pu,f"Menos de {line} {nombre}",f"El historial combinado queda por debajo de {line} {nombre} en {pu*100:.1f}% de los escenarios.",line))
        if opciones:
            best=max(opciones,key=lambda x:x[0])
            z=_candidate(best[1],best[0],familia,best[2],n,.62 if familia=="tarjetas" else .60)
            if z:c.append(z)

    # Una recomendación fuerte por familia, pero conservamos 6-7 familias/mercados.
    mejores={}
    for x in c:
        if x["familia"] not in mejores or x["score"]>mejores[x["familia"]]["score"]: mejores[x["familia"]]=x
    out=sorted(mejores.values(),key=lambda x:x["score"],reverse=True)
    return out[:7]

def pick_mas_seguro(local, visitante):
    n=min(local.partidos_evaluados,visitante.partidos_evaluados)
    if n<5:
        return {"disponible":False,"razon":f"Historial insuficiente: {local.nombre} {local.partidos_evaluados}, {visitante.nombre} {visitante.partidos_evaluados}.","recomendaciones":[]}
    c=evaluar_mercados_candidatos(local,visitante)
    if not c:
        return {"disponible":False,"razon":"No hubo mercados con probabilidad estadística suficiente.","recomendaciones":[]}
    return {"disponible":True,"mercado":c[0]["mercado"],"justificacion":c[0]["justificacion"],"confianza":c[0]["confianza"],"score":c[0]["score"],"probabilidad":c[0]["probabilidad"],"n_min":n,"recomendaciones":c,"alternativas":c[1:]}

def armar_parrafo_partido(local,visitante):
    return (f"{local.nombre}: {local.goles_favor_prom:.2f} GF, {local.goles_contra_prom:.2f} GC, {local.remates_totales_prom:.1f} remates y {local.tarjetas_prom:.1f} tarjetas por partido.\n"
            f"{visitante.nombre}: {visitante.goles_favor_prom:.2f} GF, {visitante.goles_contra_prom:.2f} GC, {visitante.remates_totales_prom:.1f} remates y {visitante.tarjetas_prom:.1f} tarjetas por partido.\n"
            f"BTTS histórico: {((local.partidos_ambos_anotan_pct+visitante.partidos_ambos_anotan_pct)/2):.1f}%. Muestra usada: {min(local.partidos_evaluados,visitante.partidos_evaluados)} partidos por equipo.")
