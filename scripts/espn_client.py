"""
espn_client.py
Cliente minimo para la API publica de ESPN (site.api.espn.com).
Sin API key, sin costo. Cachea en disco TODO lo que ya paso (partidos
jugados no cambian), asi cada corrida diaria solo pide lo nuevo.
"""

import requests
import json
import os
import time

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; afa-picks-bot/1.0)"}
CACHE_DIR = "datos/cache"


def _cache_path(key):
    safe = key.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-")
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _get(path, cache=True, permanent=False):
    """
    Pide un endpoint de ESPN.
    - cache=True: guarda la respuesta en disco.
    - permanent=True: si ya existe en cache, NUNCA la vuelve a pedir
      (usar solo para datos de partidos ya jugados/cerrados, que no cambian).
    """
    cpath = _cache_path(path)
    if cache and permanent and os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f:
            return json.load(f)

    url = f"{BASE}/{path}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    time.sleep(0.3)  # buen ciudadano: no reventar la API con requests pegados
    return data


def get_scoreboard(liga_slug, fecha_yyyymmdd=None):
    """Partidos de una liga. Si no se pasa fecha, trae los de hoy."""
    path = f"{liga_slug}/scoreboard"
    if fecha_yyyymmdd:
        path += f"?dates={fecha_yyyymmdd}"
    return _get(path, cache=False)  # el scoreboard de HOY cambia, no se cachea


def get_summary(liga_slug, event_id, permanent=False):
    """Detalle completo de un partido: keyEvents, boxscore, gameInfo, pickcenter, seasonseries."""
    return _get(f"{liga_slug}/summary?event={event_id}", permanent=permanent)


def get_team_schedule(liga_slug, team_id):
    """Historial de partidos de un equipo en la temporada (hasta ~23 jugados)."""
    return _get(f"{liga_slug}/teams/{team_id}/schedule", cache=False)  # cambia partido a partido


def partidos_jugados_recientes(liga_slug, team_id, n=20):
    """Devuelve los ultimos N partidos YA JUGADOS de un equipo, mas nuevo primero."""
    data = get_team_schedule(liga_slug, team_id)
    eventos = data.get("events", [])
    jugados = [
        e for e in eventos
        if e.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed")
    ]
    jugados.sort(key=lambda e: e.get("date", ""), reverse=True)
    return jugados[:n]
