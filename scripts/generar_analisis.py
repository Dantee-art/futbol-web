"""
Motor de predicciones estadisticas.

Reglas importantes:
- No inventa datos.
- No recomienda "goles propios de X"; los mercados de goles son del PARTIDO.
- Genera varias recomendaciones por partido, cada una con probabilidad.
- Usa historiales reales y descarta mercados sin muestra suficiente.
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


def _confianza(n: int) -> str:
    if n >= 15:
        return "alta"
    if n >= 8:
        return "media"
    return "baja"


def _prob_linea(lista, linea, over=True):
    if not lista:
        return None
    if over:
        return sum(x > linea for x in lista) / len(lista)
    return sum(x < linea for x in lista) / len(lista)


def _candidato(mercado, prob, justificacion, n, familia, minimo=0.60):
    if prob is None or prob < minimo:
        return None
    factor_muestra = min(n / 20, 1.0)
    score = prob * (0.70 + 0.30 * factor_muestra)
    return {
        "mercado": mercado,
        "probabilidad": round(prob * 100, 1),
        "score": round(score, 4),
        "confianza": _confianza(n),
        "familia": familia,
        "justificacion": justificacion,
    }


def _combinada(lista_a, lista_b, linea, over=True):
    if not lista_a or not lista_b:
        return None
    total = len(lista_a) * len(lista_b)
    if over:
        ok = sum((a + b) > linea for a in lista_a for b in lista_b)
    else:
        ok = sum((a + b) < linea for a in lista_a for b in lista_b)
    return ok / total


def evaluar_mercados_candidatos(local: HistorialEquipo, visitante: HistorialEquipo):
    """Devuelve varias recomendaciones estadisticas, no solo una."""
    n = min(local.partidos_evaluados, visitante.partidos_evaluados)
    if n < 5:
        return []

    c = []

    # 1) DOBLE OPORTUNIDAD. Se basa en diferencial goleador reciente.
    fuerza_l = local.goles_favor_prom - local.goles_contra_prom
    fuerza_v = visitante.goles_favor_prom - visitante.goles_contra_prom
    diff = fuerza_l - fuerza_v
    p_local = 1 / (1 + math.exp(-diff))
    if p_local >= 0.62:
        c.append({
            "mercado": f"Doble oportunidad: {local.nombre} o empate",
            "probabilidad": round(p_local * 100, 1),
            "score": p_local,
            "confianza": _confianza(n),
            "familia": "resultado",
            "justificacion": f"El diferencial goleador reciente favorece a {local.nombre} sobre una muestra de {n} partidos por equipo.",
        })
    elif p_local <= 0.38:
        p = 1 - p_local
        c.append({
            "mercado": f"Doble oportunidad: {visitante.nombre} o empate",
            "probabilidad": round(p * 100, 1),
            "score": p,
            "confianza": _confianza(n),
            "familia": "resultado",
            "justificacion": f"El diferencial goleador reciente favorece a {visitante.nombre} sobre una muestra de {n} partidos por equipo.",
        })

    # 2) GOLES TOTALES DEL PARTIDO. Solo mercados normales, nunca "goles propios".
    for linea in (0.5, 1.5, 2.5, 3.5, 4.5):
        p = _combinada(local.goles_favor_lista, visitante.goles_favor_lista, linea, True)
        x = _candidato(
            f"Más de {linea} goles",
            p,
            f"La combinación de los historiales goleadores supera {linea} goles en {round(p*100) if p is not None else 0}% de los escenarios históricos.",
            n, "goles"
        )
        if x: c.append(x)
        p = _combinada(local.goles_favor_lista, visitante.goles_favor_lista, linea, False)
        x = _candidato(
            f"Menos de {linea} goles",
            p,
            f"La combinación de los historiales goleadores queda por debajo de {linea} goles en {round(p*100) if p is not None else 0}% de los escenarios históricos.",
            n, "goles"
        )
        if x: c.append(x)

    # 3) AMBOS ANOTAN.
    btts = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 200
    if btts >= 0.60:
        c.append({"mercado":"Ambos anotan: Sí","probabilidad":round(btts*100,1),"score":btts,"confianza":_confianza(n),"familia":"btts","justificacion":f"Ambos equipos registran una tendencia combinada de {round(btts*100)}% de partidos con gol de ambos."})
    elif btts <= 0.40:
        p = 1 - btts
        c.append({"mercado":"Ambos anotan: No","probabilidad":round(p*100,1),"score":p,"confianza":_confianza(n),"familia":"btts","justificacion":f"La tendencia combinada indica que ambos equipos no marcan en una proporción alta de sus partidos recientes."})

    # 4) TARJETAS DEL PARTIDO.
    for linea in (2.5, 3.5, 4.5, 5.5, 6.5):
        p = _combinada(local.tarjetas_lista, visitante.tarjetas_lista, linea, True)
        x = _candidato(f"Más de {linea} tarjetas", p, f"El historial combinado supera {linea} tarjetas en {round(p*100) if p is not None else 0}% de los escenarios.", n, "tarjetas")
        if x: c.append(x)
        p = _combinada(local.tarjetas_lista, visitante.tarjetas_lista, linea, False)
        x = _candidato(f"Menos de {linea} tarjetas", p, f"El historial combinado queda por debajo de {linea} tarjetas en {round(p*100) if p is not None else 0}% de los escenarios.", n, "tarjetas")
        if x: c.append(x)

    # 5) REMATES DEL PARTIDO. Se muestra como total, no por equipo.
    for linea in (17.5, 19.5, 21.5, 23.5, 25.5, 27.5):
        p = _combinada(local.remates_totales_lista, visitante.remates_totales_lista, linea, True)
        x = _candidato(f"Más de {linea} remates totales", p, f"El historial combinado supera {linea} remates en {round(p*100) if p is not None else 0}% de los escenarios.", n, "remates")
        if x: c.append(x)
        p = _combinada(local.remates_totales_lista, visitante.remates_totales_lista, linea, False)
        x = _candidato(f"Menos de {linea} remates totales", p, f"El historial combinado queda por debajo de {linea} remates en {round(p*100) if p is not None else 0}% de los escenarios.", n, "remates")
        if x: c.append(x)

    # Una sola recomendacion por familia: evita llenar la pantalla con lineas repetidas.
    mejores = {}
    for item in c:
        familia = item["familia"]
        if familia not in mejores or item["score"] > mejores[familia]["score"]:
            mejores[familia] = item

    resultado = list(mejores.values())
    resultado.sort(key=lambda x: x["score"], reverse=True)
    return resultado


def pick_mas_seguro(local: HistorialEquipo, visitante: HistorialEquipo) -> dict:
    candidatos = evaluar_mercados_candidatos(local, visitante)
    if not candidatos:
        motivos = []
        if local.partidos_evaluados < 5:
            motivos.append(f"{local.nombre}: solo {local.partidos_evaluados} partidos con datos")
        if visitante.partidos_evaluados < 5:
            motivos.append(f"{visitante.nombre}: solo {visitante.partidos_evaluados} partidos con datos")
        razon = "; ".join(motivos) if motivos else "No hubo ningún mercado con una probabilidad suficiente."
        return {"disponible": False, "razon": razon, "recomendaciones": []}

    n = min(local.partidos_evaluados, visitante.partidos_evaluados)
    return {
        "disponible": True,
        "mercado": candidatos[0]["mercado"],
        "justificacion": candidatos[0]["justificacion"],
        "confianza": candidatos[0]["confianza"],
        "score": candidatos[0]["score"],
        "probabilidad": candidatos[0]["probabilidad"],
        "n_min": n,
        "recomendaciones": candidatos[:6],
        "alternativas": candidatos[1:6],
    }


def texto_tendencia_tarjetas(h):
    return f"{h.nombre} promedia {h.tarjetas_prom:.1f} tarjetas en sus últimos {h.partidos_evaluados} partidos."


def texto_tendencia_remates(h):
    return f"{h.nombre} promedia {h.remates_totales_prom:.1f} remates por partido, con {h.remates_arco_prom:.1f} al arco."


def texto_btts(local, visitante):
    p = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 2
    return f"Tendencia combinada de ambos anotan: {p:.0f}%."


def armar_parrafo_partido(local, visitante):
    return "\n".join([
        texto_tendencia_tarjetas(local),
        texto_tendencia_tarjetas(visitante),
        texto_tendencia_remates(local),
        texto_tendencia_remates(visitante),
        texto_btts(local, visitante),
    ])
