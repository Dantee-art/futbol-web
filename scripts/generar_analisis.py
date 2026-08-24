"""
generar_analisis.py
Genera texto de análisis por partido usando SOLO datos reales de ESPN
(sin llamadas a ningún modelo de IA, sin costo, 100% plantillas condicionales).

Cada función recibe números ya calculados desde el historial real
(últimos 20 partidos, o los que ESPN tenga disponibles) y arma una
oración coherente eligiendo entre variantes de redacción según el rango
en el que cae el dato. No inventa ningún valor: si no hay historial
suficiente, la función lo dice explícitamente en vez de simular un texto.
"""

from dataclasses import dataclass


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


def texto_goles_equipo_ou(h: HistorialEquipo, linea: float = 1.5) -> str:
    """
    Mercado: goles totales QUE HACE este equipo en el partido (over/under).
    Se calcula sobre su propio promedio de goles a favor reciente —
    NO es una cuota de casa de apuestas, es un cálculo propio y se marca como tal.
    """
    diff = h.goles_favor_prom - linea
    if h.partidos_evaluados < 5:
        return f"Datos insuficientes para proyectar goles de {h.nombre} (solo {h.partidos_evaluados} partidos con historial)."
    if diff >= 0.4:
        veredicto = f"Más de {linea} goles"
        motivo = f"promedia {h.goles_favor_prom:.2f} goles propios por partido, bien por encima de la línea."
    elif diff <= -0.4:
        veredicto = f"Menos de {linea} goles"
        motivo = f"promedia apenas {h.goles_favor_prom:.2f} goles propios por partido."
    else:
        veredicto = "Sin ventaja clara"
        motivo = f"promedia {h.goles_favor_prom:.2f} goles, muy cerca de la línea — no hay valor estadístico claro."
    return f"{h.nombre} — Goles propios {veredicto}: {motivo}"


def texto_goles_rival_ou(h_rival_recibidos: HistorialEquipo, linea: float = 1.5) -> str:
    """
    Mercado: cuántos goles puede hacerle EL RIVAL a este equipo —
    se basa en el promedio de goles QUE RECIBE el equipo analizado.
    """
    diff = h_rival_recibidos.goles_contra_prom - linea
    if h_rival_recibidos.partidos_evaluados < 5:
        return f"Datos insuficientes para proyectar goles en contra de {h_rival_recibidos.nombre}."
    if diff >= 0.4:
        veredicto = f"Más de {linea} goles en contra"
        motivo = f"{h_rival_recibidos.nombre} viene recibiendo {h_rival_recibidos.goles_contra_prom:.2f} goles por partido — defensa vulnerable."
    elif diff <= -0.4:
        veredicto = f"Menos de {linea} goles en contra"
        motivo = f"{h_rival_recibidos.nombre} solo recibe {h_rival_recibidos.goles_contra_prom:.2f} goles por partido — defensa sólida."
    else:
        veredicto = "Sin ventaja clara"
        motivo = f"{h_rival_recibidos.nombre} recibe {h_rival_recibidos.goles_contra_prom:.2f} goles, cerca de la línea."
    return f"Goles del rival ante {h_rival_recibidos.nombre} — {veredicto}: {motivo}"


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


def evaluar_mercados_candidatos(local: HistorialEquipo, visitante: HistorialEquipo):
    """
    Calcula un puntaje de "fuerza estadistica" para cada mercado posible
    (magnitud del desvio respecto a una linea neutral, multiplicado por
    la confianza segun cuantos partidos reales hay detras). Devuelve una
    lista de candidatos ordenada de mas a menos fuerte.
    Cada candidato: {"mercado": str, "score": float, "justificacion": str, "confianza": str}
    """
    candidatos = []

    ambos_con_historial = local.partidos_evaluados >= 5 and visitante.partidos_evaluados >= 5
    if not ambos_con_historial:
        return candidatos  # sin historial de alguno de los dos, no se puede comparar nada

    n_min = min(local.partidos_evaluados, visitante.partidos_evaluados)
    factor_confianza = min(n_min / 20, 1.0)

    # --- 1) Doble oportunidad, segun diferencial de forma (goles a favor - en contra) ---
    fuerza_local = local.goles_favor_prom - local.goles_contra_prom
    fuerza_visita = visitante.goles_favor_prom - visitante.goles_contra_prom
    diff_fuerza = fuerza_local - fuerza_visita
    score_do = abs(diff_fuerza) * factor_confianza
    if diff_fuerza > 0.25:
        candidatos.append({
            "mercado": f"Doble oportunidad: {local.nombre} o empate",
            "score": score_do,
            "justificacion": (
                f"{local.nombre} tiene mejor diferencial de gol reciente ({fuerza_local:+.2f} por partido) "
                f"que {visitante.nombre} ({fuerza_visita:+.2f}), sobre {n_min} partidos comparables."
            ),
        })
    elif diff_fuerza < -0.25:
        candidatos.append({
            "mercado": f"Doble oportunidad: {visitante.nombre} o empate",
            "score": score_do,
            "justificacion": (
                f"{visitante.nombre} tiene mejor diferencial de gol reciente ({fuerza_visita:+.2f} por partido) "
                f"que {local.nombre} ({fuerza_local:+.2f}), sobre {n_min} partidos comparables."
            ),
        })

    # --- 2) Goles totales del partido, over/under 2.5 ---
    total_esperado = (
        (local.goles_favor_prom + visitante.goles_contra_prom) / 2
        + (visitante.goles_favor_prom + local.goles_contra_prom) / 2
    )
    linea_goles = 2.5
    diff_goles = total_esperado - linea_goles
    score_goles = abs(diff_goles) * factor_confianza
    if abs(diff_goles) > 0.3:
        veredicto = "Más" if diff_goles > 0 else "Menos"
        candidatos.append({
            "mercado": f"Goles totales del partido: {veredicto} de {linea_goles}",
            "score": score_goles,
            "justificacion": (
                f"Combinando el ataque de {local.nombre} ({local.goles_favor_prom:.2f} GF/partido) con la defensa de "
                f"{visitante.nombre} ({visitante.goles_contra_prom:.2f} GC/partido), y viceversa, "
                f"el proyectado es {total_esperado:.2f} goles totales."
            ),
        })

    # --- 3) Remates totales del partido (linea de referencia propia, no de casa: 23.5) ---
    linea_remates_partido = 23.5
    total_remates = local.remates_totales_prom + visitante.remates_totales_prom
    diff_remates = total_remates - linea_remates_partido
    score_remates = (abs(diff_remates) / linea_remates_partido) * factor_confianza
    if abs(diff_remates) > 2:
        veredicto = "Más" if diff_remates > 0 else "Menos"
        candidatos.append({
            "mercado": f"Remates totales del partido: {veredicto} de {linea_remates_partido}",
            "score": score_remates,
            "justificacion": (
                f"{local.nombre} remata {local.remates_totales_prom:.1f}/partido y {visitante.nombre} "
                f"{visitante.remates_totales_prom:.1f}/partido — suman {total_remates:.1f}, "
                f"lejos de la línea de referencia ({linea_remates_partido})."
            ),
        })

    # --- 4) Remates de un equipo puntual, el que este mas lejos de una linea de referencia propia (11.5) ---
    linea_remates_equipo = 11.5
    for eq in (local, visitante):
        diff_eq = eq.remates_totales_prom - linea_remates_equipo
        score_eq = (abs(diff_eq) / linea_remates_equipo) * factor_confianza
        if abs(diff_eq) > 2:
            veredicto = "Más" if diff_eq > 0 else "Menos"
            candidatos.append({
                "mercado": f"Remates totales de {eq.nombre}: {veredicto} de {linea_remates_equipo}",
                "score": score_eq,
                "justificacion": (
                    f"{eq.nombre} promedia {eq.remates_totales_prom:.1f} remates totales por partido "
                    f"en sus últimos {eq.partidos_evaluados} encuentros, lejos de la línea de referencia."
                ),
            })

    # --- 5) Ambos anotan ---
    prom_btts = (local.partidos_ambos_anotan_pct + visitante.partidos_ambos_anotan_pct) / 2
    score_btts = (abs(prom_btts - 50) / 50) * factor_confianza
    if abs(prom_btts - 50) > 12:
        veredicto = "Sí" if prom_btts > 50 else "No"
        candidatos.append({
            "mercado": f"Ambos anotan: {veredicto}",
            "score": score_btts,
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
            "razon": "Ningún mercado mostró un desvío lo bastante grande respecto a su línea de referencia como para recomendarlo con confianza — partido parejo en los números.",
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
        "n_min": n_min,
        "alternativas": alternativas,
    }


def armar_parrafo_partido(local: HistorialEquipo, visitante: HistorialEquipo) -> str:
    """Junta todas las oraciones en un párrafo legible para el reporte."""
    partes = [
        texto_tendencia_tarjetas(local),
        texto_tendencia_tarjetas(visitante),
        texto_tendencia_remates(local),
        texto_tendencia_remates(visitante),
        texto_goles_equipo_ou(local),
        texto_goles_rival_ou(local),
        texto_goles_equipo_ou(visitante),
        texto_goles_rival_ou(visitante),
        texto_btts(local, visitante),
    ]
    return "\n".join(partes)


if __name__ == "__main__":
    # Ejemplo con datos ficticios SOLO para probar que el módulo corre.
    # En producción, HistorialEquipo se llena con datos reales de espn_client.py
    racing = HistorialEquipo("Racing Club", 14, 1.6, 1.1, 2.4, 12.3, 4.1, 58)
    belgrano = HistorialEquipo("Belgrano", 11, 1.2, 1.4, 2.9, 10.1, 3.2, 45)
    print(armar_parrafo_partido(racing, belgrano))
