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
