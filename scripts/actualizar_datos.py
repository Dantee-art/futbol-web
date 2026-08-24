"""
actualizar_datos.py
Orquestador diario. Recorre todas las ligas de config/ligas.json,
trae los partidos de HOY de cada una, y para cada partido arma el
paquete completo: gameInfo, cuotas, H2H, keyEvents, boxscore, y el
historial calculado de cada equipo (via calcular_historial.py).

Corre una vez al dia via GitHub Actions. Guarda todo en
datos/picks_hoy.json, que despues lee generar_html.py.
"""

import json
import os
from datetime import datetime, timezone, date

from espn_client import get_scoreboard, get_summary
from calcular_historial import construir_historial
from generar_analisis import armar_parrafo_partido, pick_mas_seguro

# --- RUTAS ABSOLUTAS ---
DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_RAIZ = os.path.dirname(DIRECTORIO_SCRIPT)

CONFIG_PATH = os.path.join(DIRECTORIO_RAIZ, "config", "ligas.json")
OUTPUT_PATH = os.path.join(DIRECTORIO_RAIZ, "datos", "picks_hoy.json")
# -----------------------

HISTORIAL_N = 20  # partidos hacia atras por equipo


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
        return {"error": str(e), "event_id": event_id}

    game_info = summary.get("gameInfo", {})
    pickcenter = summary.get("pickcenter", [])
    seasonseries = summary.get("seasonseries", [])
    key_events = summary.get("keyEvents", [])

    # Historial real de cada equipo
    hist_local = construir_historial(liga_slug, local_id, local_nombre, n=HISTORIAL_N)
    hist_visita = construir_historial(liga_slug, visita_id, visita_nombre, n=HISTORIAL_N)

    analisis_texto = armar_parrafo_partido(hist_local, hist_visita)
    pick = pick_mas_seguro(hist_local, hist_visita)

    return {
        "event_id": event_id,
        "liga_slug": liga_slug,
        "liga_nombre": liga_nombre,
        "fecha": evento.get("date"),
        "estado": comp.get("status", {}).get("type", {}).get("description"),
        "local": {"id": local_id, "nombre": local_nombre},
        "visita": {"id": visita_id, "nombre": visita_nombre},
        "venue": game_info.get("venue", {}),
        "arbitro": next(
            (o.get("fullName") for o in game_info.get("officials", []) if o.get("position", {}).get("name") == "Referee"),
            None,
        ),
        "cuotas": pickcenter,
        "h2h": seasonseries,
        "eventos_clave": key_events,
        "historial_local": vars(hist_local),
        "historial_visita": vars(hist_visita),
        "pick_mas_seguro": pick,
        "analisis": analisis_texto,
    }


def main():
    ligas = cargar_ligas()

    # OBTENEMOS LA FECHA DE HOY EXPLÍCITA (YYYYMMDD)
    fecha_hoy = date.today().strftime("%Y%m%d")
    print(f"Buscando partidos para la fecha: {fecha_hoy}")

    resultado = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "ligas": [],
        "top5_dia": [],
    }

    picks_del_dia = []  # aca vamos juntando el mejor pick de cada partido, de todas las ligas

    for slug, nombre in ligas:
        try:
            # PASAMOS LA FECHA EXPLÍCITA A LA API DE ESPN
            scoreboard = get_scoreboard(slug, fecha_yyyymmdd=fecha_hoy)
        except Exception as e:
            print(f"[AVISO] Liga {slug} falló al traer scoreboard: {e}")
            continue

        eventos = scoreboard.get("events", [])
        if not eventos:
            continue  # esta liga no juega hoy, seguimos con la próxima

        partidos_procesados = []
        for idx_liga, ev in enumerate(eventos):
            print(f"Procesando {slug}: {ev.get('shortName', ev.get('id'))}")
            try:
                p = procesar_partido(slug, nombre, ev)
                partidos_procesados.append(p)
                pick = p.get("pick_mas_seguro") or {}
                if pick.get("disponible") and pick.get("n_min", 0) >= 10:
                    picks_del_dia.append({
                        "liga_nombre": nombre,
                        "liga_slug": slug,
                        "local": p["local"]["nombre"],
                        "visita": p["visita"]["nombre"],
                        "mercado": pick["mercado"],
                        "justificacion": pick["justificacion"],
                        "confianza": pick["confianza"],
                        "score": pick["score"],
                        "n_min": pick["n_min"],
                    })
            except Exception as e:
                print(f"[AVISO] Partido {ev.get('id')} de {slug} falló: {e}")

        if partidos_procesados:
            resultado["ligas"].append({
                "slug": slug,
                "nombre": nombre,
                "partidos": partidos_procesados,
            })

    picks_del_dia.sort(key=lambda p: p["score"], reverse=True)
    resultado["top5_dia"] = picks_del_dia[:5]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Listo. {sum(len(l['partidos']) for l in resultado['ligas'])} partidos guardados en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
