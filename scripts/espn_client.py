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
from datetime import date

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
HEADERS = {}
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


def get_team_schedule(liga_slug, team_id, season=None):
    """
    Historial de partidos de un equipo en una temporada.
    Si no se pasa season, trae la temporada actual (la que este corriendo).
    Si se pasa season (ej. 2025), intenta traer esa temporada puntual --
    sirve para completar historial cuando la actual recien arranca.
    """
    path = f"{liga_slug}/teams/{team_id}/schedule"
    if season:
        path += f"?season={season}"
    return _get(path, cache=False)  # cambia partido a partido


def _es_amistoso(evento):
    """Heuristica para descartar amistosos: mira el nombre del evento y el tipo de temporada."""
    nombre = f"{evento.get('name','')} {evento.get('shortName','')}".lower()
    if "friendly" in nombre or "amistoso" in nombre or "pre-season" in nombre or "preseason" in nombre:
        return True
    season_type = evento.get("seasonType", {}) or {}
    tipo_nombre = str(season_type.get("name", "")).lower() if isinstance(season_type, dict) else ""
    if "preseason" in tipo_nombre or "pretemporada" in tipo_nombre:
        return True
    return False


def _jugados_de(eventos):
    return [
        e for e in eventos
        if e.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed")
        and not _es_amistoso(e)
    ]


def partidos_jugados_recientes(liga_slug, team_id, n=20):
    """
    Devuelve los ultimos N partidos YA JUGADOS y de competencia (sin amistosos)
    de un equipo, mas nuevo primero. Si la temporada actual no tiene suficientes
    partidos jugados todavia (ej. arranque de temporada en Premier League),
    completa el resto con partidos de la temporada anterior. A medida que
    avanza la temporada actual, esta funcion va a ir devolviendo cada vez
    mas partidos nuevos y menos de la temporada vieja, solo, sin tocar nada.
    """
    data_actual = get_team_schedule(liga_slug, team_id)
    jugados = _jugados_de(data_actual.get("events", []))
    jugados.sort(key=lambda e: e.get("date", ""), reverse=True)

    if len(jugados) < n:
        anio_anterior = date.today().year - 1
        try:
            data_prev = get_team_schedule(liga_slug, team_id, season=anio_anterior)
            jugados_prev = _jugados_de(data_prev.get("events", []))
            jugados_prev.sort(key=lambda e: e.get("date", ""), reverse=True)
            jugados.extend(jugados_prev)
        except Exception as e:
            print(f"[AVISO] No se pudo traer temporada {anio_anterior} para team {team_id} en {liga_slug}: {e}")

    return jugados[:n]
