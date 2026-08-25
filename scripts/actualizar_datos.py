"""
Actualizador diario de futbol.
Trae los partidos de hoy de todas las ligas configuradas y genera
varias recomendaciones estadisticas por partido.
"""

import json
import os
from datetime import datetime, timezone, date

from espn_client import get_scoreboard, get_summary
from calcular_historial import construir_historial
from generar_analisis import armar_parrafo_partido, pick_mas_seguro

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_RAIZ = os.path.dirname(DIRECTORIO_SCRIPT)
CONFIG_PATH = os.path.join(DIRECTORIO_RAIZ, "config", "ligas.json")
OUTPUT_PATH = os.path.join(DIRECTORIO_RAIZ, "datos", "picks_hoy.json")
HISTORIAL_N = 20


def cargar_ligas():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    slugs = []
    for grupo, ligas in raw.items():
        if grupo.startswith("_"):
            continue
        for slug, nombre in ligas.items():
            slugs.append((slug, nombre))
    return slugs


def procesar_partido(liga_slug, liga_nombre, evento):
    event_id = evento.get("id")
    comp = evento.get("competitions", [{}])[0]
    competidores = comp.get("competitors", [])
    local = next((c for c in competidores if c.get("homeAway") == "home"), {})
    visita = next((c for c in competidores if c.get("homeAway") == "away"), {})

    local_id = local.get("team", {}).get("id")
    visita_id = visita.get("team", {}).get("id")
    local_nombre = local.get("team", {}).get("displayName", "Local")
    visita_nombre = visita.get("team", {}).get("displayName", "Visitante")

    try:
        summary = get_summary(liga_slug, event_id, permanent=False)
    except Exception as e:
        print(f"[SIN DATOS] {local_nombre} vs {visita_nombre}: {e}")
        return None

    game_info = summary.get("gameInfo", {})
    pickcenter = summary.get("pickcenter", [])
    seasonseries = summary.get("seasonseries", [])
    key_events = summary.get("keyEvents", [])

    try:
        hist_local = construir_historial(liga_slug, local_id, local_nombre, n=HISTORIAL_N)
        hist_visita = construir_historial(liga_slug, visita_id, visita_nombre, n=HISTORIAL_N)
    except Exception as e:
        print(f"[SIN HISTORIAL] {local_nombre} vs {visita_nombre}: {e}")
        return None

    pick = pick_mas_seguro(hist_local, hist_visita)
    analisis_texto = armar_parrafo_partido(hist_local, hist_visita)

    # No publicamos un partido como "con prediccion" si no existe muestra suficiente.
    recomendaciones = pick.get("recomendaciones", [])

    return {
        "event_id": event_id,
        "liga_slug": liga_slug,
        "liga_nombre": liga_nombre,
        "fecha": evento.get("date"),
        "estado": comp.get("status", {}).get("type", {}).get("description"),
        "local": {"id": local_id, "nombre": local_nombre},
        "visita": {"id": visita_id, "nombre": visita_nombre},
        "venue": game_info.get("venue", {}),
        "arbitro": next((o.get("fullName") for o in game_info.get("officials", []) if o.get("position", {}).get("name") == "Referee"), None),
        "cuotas": pickcenter,
        "h2h": seasonseries,
        "eventos_clave": key_events,
        "historial_local": vars(hist_local),
        "historial_visita": vars(hist_visita),
        "pick_mas_seguro": pick,
        "recomendaciones": recomendaciones,
        "analisis": analisis_texto,
        "datos_completos": bool(hist_local.partidos_evaluados >= 5 and hist_visita.partidos_evaluados >= 5),
    }


def main():
    ligas = cargar_ligas()
    fecha_hoy = date.today().strftime("%Y%m%d")
    print(f"Buscando partidos para la fecha: {fecha_hoy}")

    resultado = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "fecha": fecha_hoy,
        "ligas": [],
        "top5_dia": [],
    }
    picks_del_dia = []

    for slug, nombre in ligas:
        try:
            scoreboard = get_scoreboard(slug, fecha_yyyymmdd=fecha_hoy)
        except Exception as e:
            print(f"[AVISO] Liga {slug} falló: {e}")
            continue

        eventos = scoreboard.get("events", [])
        if not eventos:
            continue

        partidos_procesados = []
        for ev in eventos:
            try:
                p = procesar_partido(slug, nombre, ev)
                if p is None:
                    continue
                partidos_procesados.append(p)
                pick = p.get("pick_mas_seguro") or {}
                if pick.get("disponible") and pick.get("n_min", 0) >= 5:
                    picks_del_dia.append({
                        "liga_nombre": nombre,
                        "liga_slug": slug,
                        "local": p["local"]["nombre"],
                        "visita": p["visita"]["nombre"],
                        "mercado": pick["mercado"],
                        "justificacion": pick["justificacion"],
                        "confianza": pick["confianza"],
                        "score": pick["score"],
                        "probabilidad": pick["probabilidad"],
                        "n_min": pick["n_min"],
                    })
            except Exception as e:
                print(f"[AVISO] Partido {ev.get('id')} de {slug} falló: {e}")

        if partidos_procesados:
            resultado["ligas"].append({"slug": slug, "nombre": nombre, "partidos": partidos_procesados})

    picks_del_dia.sort(key=lambda p: p["score"], reverse=True)
    resultado["top5_dia"] = picks_del_dia[:5]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    total = sum(len(l["partidos"]) for l in resultado["ligas"])
    print(f"Listo. {total} partidos guardados. {len(picks_del_dia)} tienen pick.")


if __name__ == "__main__":
    main()
