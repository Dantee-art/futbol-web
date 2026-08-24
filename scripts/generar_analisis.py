"""
generar_analisis.py
Genera texto de análisis por partido usando SOLO datos reales de ESPN
(sin llamadas a ningún modelo de IA, sin costo, 100% plantillas condicionales).

Cada mercado se evalúa en VARIAS líneas posibles (ej. goles 0.5/1.5/2.5) y
se elige la línea más segura de esa familia usando la PROBABILIDAD EMPÍRICA
real: cuántos de los últimos partidos superaron esa línea, contando de
verdad los partidos guardados en el historial (no un promedio ni una
suposición). Esa probabilidad es la misma que después se usa para calcular
el EV+ contra la cuota que el usuario cargue en la página.
"""

import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class HistorialEquipo:
    nombre: str
    partidos_evaluados: int          # cuántos partidos reales se pudieron traer (idealmente 20)
    goles_favor_prom: float
    goles_contra_prom: float
    tarjetas_prom: float
    remates_totales_prom: float
    remates_arco_prom: float
    partidos_ambos_anotan_pct: float  # 0-100
    # Listas crudas partido por partido -- necesarias para la probabilidad empirica y el EV+
    goles_favor_lista: List[float] = field(default_factory=list)
    goles_contra_lista: List[float] = field(default_factory=list)
    tarjetas_lista: List[float] = field(default_factory=list)
    remates_totales_lista: List[float] = field(default_factory=list)


def _confianza(n_partidos: int) -> str:
    """Etiqueta de confianza según cuántos partidos reales hay detrás del promedio."""
    if n_partidos >= 15:
        return "alta"
    if n_partidos >= 8:
        return "media"
    return "baja"


def texto_tendencia_tarjetas(h: HistorialEquipo) -> str:
    conf = _confianza(h.partidos_evaluados)
    base = f"En sus últimos {h.partidos_evaluados} partidos con datos disponibles, "
    if h.tarjetas_prom >= 3.0:
        cuerpo = f"{h.nombre} promedia {h.tarjetas_prom:.1f} tarjetas por partido — una tendencia marcadamente indisciplinada."
    elif h.tarjetas_prom >= 2.0:
        cuerpo = f"{h.nombre} promedia {h.tarjetas_prom:.1f} tarjetas por partido, un nivel moderado."
    else:
        cuerpo = f"{h.nombre} promedia apenas {h.tarjetas_prom:.1f} tarjetas por partido, un equipo disciplinado."
    return base + cuerpo + f" (confianza {conf}, base: {h.partidos_evaluados} partidos reales)"


def texto_tendencia_remates(h: HistorialEquipo) -> str:
    pct_al_arco = (h.remates_arco_prom / h.remates_totales_prom * 100) if h.remates_totales_prom else 0
    return (
        f"{h.nombre} remata {h.remates_totales_prom:.1f} veces por partido, de las cuales "
        f"{h.remates_arco_prom:.1f} van al arco ({pct_al_arco:.0f}% de efectividad de puntería)."
    )


def texto_btts(local: HistorialEquipo, visitante: HistorialEquipo) -> str:
    prom = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 2
    if prom >= 60:
        return f"Ambos anotan (Sí) — promedio combinado {prom:.0f}% en los partidos recientes de ambos equipos."
    elif prom <= 35:
        return f"Ambos anotan (No) — promedio combinado {prom:.0f}%, tendencia baja de goles en ambos arcos."
    return f"Ambos anotan — {prom:.0f}% combinado, sin tendencia clara hacia sí o no."


def _sin_historial_texto(nombre: str) -> str:
    return (
        f"{nombre} no tiene partidos jugados registrados en la fuente todavía "
        f"(probable pretemporada o inicio de temporada) — no hay base real para proyectar nada de este equipo."
    )


# ---------------------------------------------------------------------------
# PROBABILIDAD EMPIRICA -- la base real de todo el sistema de picks y del EV+
# ---------------------------------------------------------------------------

def prob_over(lista, linea):
    """Fraccion de partidos, de una lista real de valores, que superaron la linea."""
    if not lista:
        return None
    return sum(1 for x in lista if x > linea) / len(lista)


def prob_over_combinado(lista_a, lista_b, linea):
    """
    Probabilidad de que la SUMA de un valor de lista_a + un valor de lista_b
    supere la linea, asumiendo independencia entre ambos equipos (aproximacion
    razonable dado que son partidos contra rivales distintos). Se calcula
    contando TODAS las combinaciones posibles entre ambas listas -- con ~20
    partidos por lado son ~400 combinaciones, trivial en tiempo de computo.
    """
    if not lista_a or not lista_b:
        return None
    total = len(lista_a) * len(lista_b)
    cuenta = sum(1 for a in lista_a for b in lista_b if (a + b) > linea)
    return cuenta / total


def _mejor_linea_individual(lista, lineas, factor_confianza, nombre_mercado_fn, justif_fn):
    """
    Prueba varias lineas sobre una lista individual (un solo equipo) y
    devuelve solo la mas segura de esa familia (mayor distancia del 50/50).
    """
    candidatos = []
    n = len(lista)
    if n == 0:
        return None
    for linea in lineas:
        p = prob_over(lista, linea)
        if p is None or abs(p - 0.5) <= 0.15:
            continue
        lado = "Más" if p > 0.5 else "Menos"
        prob_mostrada = p if p > 0.5 else 1 - p
        candidatos.append({
            "mercado": nombre_mercado_fn(lado, linea),
            "score": abs(p - 0.5) * 2 * factor_confianza,
            "probabilidad": round(prob_mostrada * 100, 1),
            "justificacion": justif_fn(lado, linea, round(prob_mostrada * 100), n),
        })
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos[0]


def _mejor_linea_combinada(lista_a, lista_b, lineas, factor_confianza, nombre_mercado_fn, justif_fn):
    """Misma idea que _mejor_linea_individual pero para el total de AMBOS equipos juntos."""
    candidatos = []
    if not lista_a or not lista_b:
        return None
    n = min(len(lista_a), len(lista_b))
    for linea in lineas:
        p = prob_over_combinado(lista_a, lista_b, linea)
        if p is None or abs(p - 0.5) <= 0.15:
            continue
        lado = "Más" if p > 0.5 else "Menos"
        prob_mostrada = p if p > 0.5 else 1 - p
        candidatos.append({
            "mercado": nombre_mercado_fn(lado, linea),
            "score": abs(p - 0.5) * 2 * factor_confianza,
            "probabilidad": round(prob_mostrada * 100, 1),
            "justificacion": justif_fn(lado, linea, round(prob_mostrada * 100), n),
        })
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos[0]


def evaluar_mercados_candidatos(local: HistorialEquipo, visitante: HistorialEquipo):
    """
    Evalua TODOS los mercados posibles (menos corners, que no existen en la
    fuente), cada uno en varias lineas, y devuelve la lista de "mejor linea
    de cada familia" ordenada de mas a menos segura. Cada candidato trae
    "probabilidad" (0-100) lista para usarse en el calculo de EV+.
    """
    candidatos = []

    if local.partidos_evaluados < 5 or visitante.partidos_evaluados < 5:
        return candidatos

    n_min = min(local.partidos_evaluados, visitante.partidos_evaluados)
    factor_combinado = min(n_min / 20, 1.0)
    factor_local = min(local.partidos_evaluados / 20, 1.0)
    factor_visita = min(visitante.partidos_evaluados / 20, 1.0)

    # --- Doble oportunidad: diferencial de gol pasado por una logistica para dar una probabilidad ---
    fuerza_local = local.goles_favor_prom - local.goles_contra_prom
    fuerza_visita = visitante.goles_favor_prom - visitante.goles_contra_prom
    diff_fuerza = fuerza_local - fuerza_visita
    prob_local_no_pierde = 1 / (1 + math.exp(-diff_fuerza))
    if abs(prob_local_no_pierde - 0.5) > 0.12:
        if prob_local_no_pierde > 0.5:
            favorito, rival = local, visitante
            prob_mostrada = prob_local_no_pierde
        else:
            favorito, rival = visitante, local
            prob_mostrada = 1 - prob_local_no_pierde
        candidatos.append({
            "mercado": f"Doble oportunidad: {favorito.nombre} o empate",
            "score": abs(prob_local_no_pierde - 0.5) * 2 * factor_combinado,
            "probabilidad": round(prob_mostrada * 100, 1),
            "justificacion": (
                f"{favorito.nombre} tiene mejor diferencial de gol reciente que {rival.nombre}, "
                f"sobre {n_min} partidos comparables (probabilidad estimada {round(prob_mostrada*100)}%)."
            ),
        })

    # --- Goles propios de cada equipo (0.5 / 1.5 / 2.5) ---
    for eq in (local, visitante):
        factor = factor_local if eq is local else factor_visita
        c = _mejor_linea_individual(
            eq.goles_favor_lista, [0.5, 1.5, 2.5], factor,
            lambda lado, linea, e=eq: f"Goles propios de {e.nombre}: {lado} de {linea}",
            lambda lado, linea, pct, n, e=eq: f"{e.nombre} tuvo {lado.lower()} de {linea} goles propios en {pct}% de sus últimos {n} partidos.",
        )
        if c:
            candidatos.append(c)

    # --- Goles recibidos por cada equipo (0.5 / 1.5 / 2.5) ---
    for eq in (local, visitante):
        factor = factor_local if eq is local else factor_visita
        c = _mejor_linea_individual(
            eq.goles_contra_lista, [0.5, 1.5, 2.5], factor,
            lambda lado, linea, e=eq: f"Goles recibidos por {e.nombre}: {lado} de {linea}",
            lambda lado, linea, pct, n, e=eq: f"{e.nombre} recibió {lado.lower()} de {linea} goles en {pct}% de sus últimos {n} partidos.",
        )
        if c:
            candidatos.append(c)

    # --- Goles totales del partido (combinado, 1.5 / 2.5 / 3.5 / 4.5) ---
    c = _mejor_linea_combinada(
        local.goles_favor_lista, visitante.goles_favor_lista, [1.5, 2.5, 3.5, 4.5], factor_combinado,
        lambda lado, linea: f"Goles totales del partido: {lado} de {linea}",
        lambda lado, linea, pct, n: f"Combinando el historial goleador de ambos equipos, {pct}% de las combinaciones posibles dan {lado.lower()} de {linea} goles totales.",
    )
    if c:
        candidatos.append(c)

    # --- Tarjetas totales de cada equipo (1.5 / 2.5 / 3.5) ---
    for eq in (local, visitante):
        factor = factor_local if eq is local else factor_visita
        c = _mejor_linea_individual(
            eq.tarjetas_lista, [1.5, 2.5, 3.5], factor,
            lambda lado, linea, e=eq: f"Tarjetas de {e.nombre}: {lado} de {linea}",
            lambda lado, linea, pct, n, e=eq: f"{e.nombre} tuvo {lado.lower()} de {linea} tarjetas en {pct}% de sus últimos {n} partidos.",
        )
        if c:
            candidatos.append(c)

    # --- Tarjetas totales del partido (combinado, 2.5 / 3.5 / 4.5 / 5.5 / 6.5) ---
    c = _mejor_linea_combinada(
        local.tarjetas_lista, visitante.tarjetas_lista, [2.5, 3.5, 4.5, 5.5, 6.5], factor_combinado,
        lambda lado, linea: f"Tarjetas totales del partido: {lado} de {linea}",
        lambda lado, linea, pct, n: f"Combinando el historial de tarjetas de ambos equipos, {pct}% de las combinaciones posibles dan {lado.lower()} de {linea} tarjetas totales.",
    )
    if c:
        candidatos.append(c)

    # --- Remates totales de cada equipo (8.5 / 10.5 / 12.5 / 14.5) ---
    for eq in (local, visitante):
        factor = factor_local if eq is local else factor_visita
        c = _mejor_linea_individual(
            eq.remates_totales_lista, [8.5, 10.5, 12.5, 14.5], factor,
            lambda lado, linea, e=eq: f"Remates totales de {e.nombre}: {lado} de {linea}",
            lambda lado, linea, pct, n, e=eq: f"{e.nombre} tuvo {lado.lower()} de {linea} remates en {pct}% de sus últimos {n} partidos.",
        )
        if c:
            candidatos.append(c)

    # --- Remates totales del partido (combinado, 19.5 / 21.5 / 23.5 / 25.5 / 27.5) ---
    c = _mejor_linea_combinada(
        local.remates_totales_lista, visitante.remates_totales_lista, [19.5, 21.5, 23.5, 25.5, 27.5], factor_combinado,
        lambda lado, linea: f"Remates totales del partido: {lado} de {linea}",
        lambda lado, linea, pct, n: f"Combinando el historial de remates de ambos equipos, {pct}% de las combinaciones posibles dan {lado.lower()} de {linea} remates totales.",
    )
    if c:
        candidatos.append(c)

    # --- Ambos anotan ---
    prom_btts = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 2
    prob_btts = prom_btts / 100
    if abs(prob_btts - 0.5) > 0.12:
        veredicto = "Sí" if prob_btts > 0.5 else "No"
        prob_mostrada = prob_btts if prob_btts > 0.5 else 1 - prob_btts
        candidatos.append({
            "mercado": f"Ambos anotan: {veredicto}",
            "score": abs(prob_btts - 0.5) * 2 * factor_combinado,
            "probabilidad": round(prob_mostrada * 100, 1),
            "justificacion": (
                f"Promedio combinado de {prom_btts:.0f}% de partidos con ambos equipos anotando, "
                f"entre {local.nombre} y {visitante.nombre}."
            ),
        })

    for c in candidatos:
        c["confianza"] = _confianza(n_min)

    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos


def pick_mas_seguro(local: HistorialEquipo, visitante: HistorialEquipo) -> dict:
    """
    Devuelve UN SOLO pick: el mercado con mayor fuerza estadistica entre
    los candidatos disponibles. Si no hay historial suficiente de alguno
    de los dos equipos, lo dice explicitamente en vez de forzar un pick.
    """
    if local.partidos_evaluados < 5 or visitante.partidos_evaluados < 5:
        motivo = []
        if local.partidos_evaluados < 5:
            motivo.append(_sin_historial_texto(local.nombre))
        if visitante.partidos_evaluados < 5:
            motivo.append(_sin_historial_texto(visitante.nombre))
        return {
            "disponible": False,
            "razon": " ".join(motivo),
        }

    candidatos = evaluar_mercados_candidatos(local, visitante)
    if not candidatos:
        return {
            "disponible": False,
            "razon": "Ningún mercado mostró una probabilidad lo bastante alejada del 50/50 como para recomendarlo con confianza — partido parejo en los números.",
        }

    mejor = candidatos[0]
    alternativas = candidatos[1:3]  # hasta 2 alternativas de respaldo
    n_min = min(local.partidos_evaluados, visitante.partidos_evaluados)
    return {
        "disponible": True,
        "mercado": mejor["mercado"],
        "justificacion": mejor["justificacion"],
        "confianza": mejor["confianza"],
        "score": mejor["score"],
        "probabilidad": mejor["probabilidad"],
        "n_min": n_min,
        "alternativas": alternativas,
    }


def armar_parrafo_partido(local: HistorialEquipo, visitante: HistorialEquipo) -> str:
    """Junta algunas oraciones descriptivas en un parrafo legible para el reporte."""
    partes = [
        texto_tendencia_tarjetas(local),
        texto_tendencia_tarjetas(visitante),
        texto_tendencia_remates(local),
        texto_tendencia_remates(visitante),
        texto_btts(local, visitante),
    ]
    return "\n".join(partes)


if __name__ == "__main__":
    # Ejemplo con datos ficticios SOLO para probar que el modulo corre.
    import random
    random.seed(42)
    racing_goles = [random.choice([0,1,1,2,2,3]) for _ in range(14)]
    belgrano_goles = [random.choice([0,0,1,1,2]) for _ in range(11)]
    racing = HistorialEquipo("Racing Club", 14, 1.6, 1.1, 2.4, 12.3, 4.1, 58,
                              goles_favor_lista=racing_goles, goles_contra_lista=[1]*14,
                              tarjetas_lista=[2,3,2,1,3,4,2,1,2,3,2,1,3,2],
                              remates_totales_lista=[12,14,10,13,11,15,12,9,13,12,11,14,10,13])
    belgrano = HistorialEquipo("Belgrano", 11, 1.2, 1.4, 2.9, 10.1, 3.2, 45,
                                goles_favor_lista=belgrano_goles, goles_contra_lista=[1]*11,
                                tarjetas_lista=[3,2,4,3,2,3,4,2,3,3,2],
                                remates_totales_lista=[9,11,10,8,10,11,9,10,8,9,10])
    print(armar_parrafo_partido(racing, belgrano))
    print()
    print("=== Pick mas seguro ===")
    print(pick_mas_seguro(racing, belgrano))
        
