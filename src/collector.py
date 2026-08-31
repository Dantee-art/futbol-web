from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.the-odds-api.com/v4"
# Competiciones de fútbol relevantes. Se valida disponibilidad contra /sports.
PREFERRED = {
    "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
    "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_uefa_champs_league",
    "soccer_uefa_europa_league", "soccer_conmebol_libertadores",
    "soccer_brazil_campeonato", "soccer_argentina_primera_division",
}
# The Odds API no documenta actualmente un mercado de remates de equipo/partido.
# Estos nombres se aceptan SOLO si el proveedor los devuelve realmente.
SHOT_MARKET_KEYS = {
    "total_shots", "shots", "team_shots", "team_total_shots",
    "shots_total", "alternate_total_shots", "alternate_team_shots",
}


def api_key() -> str:
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta el secreto ODDS_API_KEY en GitHub Actions.")
    return key


def get_sports(key: str) -> list[dict]:
    r = requests.get(f"{BASE}/sports", params={"apiKey": key}, timeout=30)
    r.raise_for_status()
    return r.json()


def get_events(key: str, sport: str) -> list[dict]:
    params = {"apiKey": key, "regions": "eu,uk", "markets": "h2h", "oddsFormat": "decimal"}
    r = requests.get(f"{BASE}/sports/{sport}/odds", params=params, timeout=30)
    if r.status_code in (401, 429):
        raise RuntimeError(f"The Odds API devolvió HTTP {r.status_code}.")
    r.raise_for_status()
    return r.json()


def get_event_markets(key: str, sport: str, event_id: str) -> dict:
    # Los mercados adicionales se consultan por evento según la documentación v4.
    params = {
        "apiKey": key,
        "regions": "eu,uk",
        "markets": "player_shots,player_shots_on_target",
        "oddsFormat": "decimal",
    }
    r = requests.get(f"{BASE}/sports/{sport}/events/{event_id}/odds", params=params, timeout=30)
    if r.status_code in (404, 422):
        return {}
    if r.status_code == 401:
        raise RuntimeError("The Odds API rechazó ODDS_API_KEY (HTTP 401).")
    if r.status_code == 429:
        raise RuntimeError("The Odds API alcanzó el límite de uso (HTTP 429).")
    r.raise_for_status()
    return r.json()


def extract_shot_lines(event: dict, detail: dict) -> list[dict]:
    rows = []
    # Nunca inventamos una línea. Solo aceptamos mercados que el proveedor entregue.
    for bookmaker in detail.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market.get("key", "")
            if key not in SHOT_MARKET_KEYS:
                continue
            for outcome in market.get("outcomes", []):
                rows.append({
                    "bookmaker": bookmaker.get("title"),
                    "market_key": key,
                    "market": market.get("key"),
                    "side": outcome.get("name"),
                    "team": outcome.get("description"),
                    "line": outcome.get("point"),
                    "odds": outcome.get("price"),
                    "updated": market.get("last_update"),
                })
    return rows


def main() -> None:
    key = api_key()
    sports = {s["key"] for s in get_sports(key) if s.get("key") in PREFERRED and s.get("active")}
    matches = []

    for sport in sorted(sports):
        for event in get_events(key, sport):
            # La API devuelve próximos/live; la interfaz filtra por fecha local.
            detail = get_event_markets(key, sport, event["id"])
            matches.append({
                "id": event["id"],
                "sport_key": sport,
                "sport_title": event.get("sport_title", sport),
                "commence_time": event.get("commence_time"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "shot_lines": extract_shot_lines(event, detail),
            })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "The Odds API",
        "note": "Solo se muestran líneas de remates que el proveedor devuelve. No se generan líneas sintéticas.",
        "matches": matches,
    }
    Path("data").mkdir(exist_ok=True)
    Path("data/remates_hoy.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
