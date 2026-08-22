"""
calcular_historial.py
A partir de los ultimos N partidos jugados de un equipo (via espn_client),
abre cada uno (keyEvents + boxscore) y calcula promedios reales.
Cada partido del historial se cachea PERMANENTE porque ya paso y no cambia.
"""

from espn_client import get_summary, partidos_jugados_recientes
from generar_analisis import HistorialEquipo


def _extraer_stats_de_partido(summary, team_id):
    """Devuelve (goles_favor, goles_contra, tarjetas, remates_totales, remates_arco, hizo_gol_rival)
    para el equipo team_id dentro de un partido ya resuelto."""
    box = summary.get("boxscore", {})
    teams_box = box.get("teams", [])

    goles_favor = goles_contra = 0
    remates_totales = remates_arco = 0
    encontrado = False

    for t in teams_box:
        stats = {s.get("name"): s.get("displayValue") for s in t.get("statistics", [])}
        es_este_equipo = str(t.get("team", {}).get("id")) == str(team_id)
        if es_este_equipo:
            encontrado = True
            remates_totales = float(stats.get("totalShots", 0) or 0)
            remates_arco = float(stats.get("shotsOnTarget", 0) or 0)

    # goles y tarjetas via keyEvents (mas confiable que boxscore para esto)
    tarjetas = 0
    for ev in summary.get("keyEvents", []):
        tipo = (ev.get("type", {}) or {}).get("text", "") or ""
        participantes = ev.get("participants", [])
        equipo_evento = str(ev.get("team", {}).get("id", ""))
        if "card" in tipo.lower() and equipo_evento == str(team_id):
            tarjetas += 1
        if tipo.lower() == "goal":
            if equipo_evento == str(team_id):
                goles_favor += 1
            elif equipo_evento:
                goles_contra += 1

    return {
        "goles_favor": goles_favor,
        "goles_contra": goles_contra,
        "tarjetas": tarjetas,
        "remates_totales": remates_totales,
        "remates_arco": remates_arco,
        "ambos_anotaron": goles_favor > 0 and goles_contra > 0,
        "encontrado": encontrado,
    }


def construir_historial(liga_slug, team_id, nombre_equipo, n=20):
    """
    Recorre los ultimos n partidos jugados del equipo y devuelve un
    HistorialEquipo con promedios reales. Si algun partido individual
    falla al pedirse, se lo salta (no rompe todo el calculo).
    """
    partidos = partidos_jugados_recientes(liga_slug, team_id, n=n)

    acumulado = []
    for p in partidos:
        event_id = p.get("id")
        if not event_id:
            continue
        try:
            summary = get_summary(liga_slug, event_id, permanent=True)
        except Exception:
            continue  # partido individual no disponible, seguimos con el resto
        stats = _extraer_stats_de_partido(summary, team_id)
        if stats["encontrado"] or stats["goles_favor"] or stats["goles_contra"]:
            acumulado.append(stats)

    n_reales = len(acumulado)
    if n_reales == 0:
        return HistorialEquipo(nombre_equipo, 0, 0, 0, 0, 0, 0, 0)

    def prom(campo):
        return sum(a[campo] for a in acumulado) / n_reales

    pct_btts = sum(1 for a in acumulado if a["ambos_anotaron"]) / n_reales * 100

    return HistorialEquipo(
        nombre=nombre_equipo,
        partidos_evaluados=n_reales,
        goles_favor_prom=round(prom("goles_favor"), 2),
        goles_contra_prom=round(prom("goles_contra"), 2),
        tarjetas_prom=round(prom("tarjetas"), 2),
        remates_totales_prom=round(prom("remates_totales"), 2),
        remates_arco_prom=round(prom("remates_arco"), 2),
        partidos_ambos_anotan_pct=round(pct_btts, 1),
    )
