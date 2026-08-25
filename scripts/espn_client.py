"""
espn_client.py
Cliente ESPN sin API key.
Historial: temporada actual + temporada anterior como respaldo.
"""
import requests, json, os, time
from datetime import date

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CACHE_DIR = "datos/cache"

def _cache_path(key):
    safe = key.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-")
    return os.path.join(CACHE_DIR, f"{safe}.json")

def _get(path, cache=True, permanent=False):
    cpath = _cache_path(path)
    if cache and permanent and os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f: return json.load(f)
    r = requests.get(f"{BASE}/{path}", timeout=25)
    r.raise_for_status()
    data = r.json()
    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cpath, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)
    time.sleep(0.25)
    return data

def get_scoreboard(liga_slug, fecha_yyyymmdd=None):
    path = f"{liga_slug}/scoreboard"
    if fecha_yyyymmdd: path += f"?dates={fecha_yyyymmdd}"
    return _get(path, cache=False)

def get_summary(liga_slug, event_id, permanent=False):
    return _get(f"{liga_slug}/summary?event={event_id}", permanent=permanent)

def get_team_schedule(liga_slug, team_id, season=None):
    path = f"{liga_slug}/teams/{team_id}/schedule"
    if season: path += f"?season={season}"
    return _get(path, cache=False)

def _es_amistoso(e):
    texto = f"{e.get('name','')} {e.get('shortName','')}".lower()
    if any(x in texto for x in ("friendly", "amistoso", "pre-season", "preseason", "pretemporada")): return True
    st = e.get("seasonType", {}) or {}
    return "pre" in str(st.get("name", "")).lower()

def _jugados_de(eventos):
    return [e for e in eventos if e.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed") and not _es_amistoso(e)]

def _ordenar(eventos):
    eventos = list(eventos)
    eventos.sort(key=lambda e: e.get("date", ""), reverse=True)
    return eventos

def partidos_jugados_recientes(liga_slug, team_id, n=20):
    """Hasta N partidos oficiales: temporada actual, luego anterior y luego anterior."""
    vistos=set(); salida=[]
    temporadas=[date.today().year,date.today().year-1,date.today().year-2]
    for season in temporadas:
        try:
            data=get_team_schedule(liga_slug,team_id,season=season)
            eventos=_ordenar(_jugados_de(data.get("events",[])))
        except Exception as e:
            print(f"[AVISO] historial {liga_slug}/{team_id}/{season}: {e}"); continue
        for e in eventos:
            eid=str(e.get("id",""))
            if eid and eid not in vistos: vistos.add(eid); salida.append(e)
            if len(salida)>=n: return salida[:n]
    return salida[:n]
