from __future__ import annotations
import os
import requests

BASE_URL = "https://api.the-odds-api.com/v4"
MARKETS = ["h2h", "totals", "spreads"]
REGIONS = "eu,uk,us"


def fetch_odds(sports: list[str], markets: list[str] | None = None) -> list[dict]:
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        raise RuntimeError("Falta ODDS_API_KEY. Configúrala como GitHub Actions Secret.")
    selected = markets or MARKETS
    events = []
    for sport in sports:
        params = {"apiKey": key, "regions": REGIONS, "markets": ",".join(selected), "oddsFormat": "decimal", "dateFormat": "iso"}
        response = requests.get(f"{BASE_URL}/sports/{sport}/odds", params=params, timeout=30)
        if response.status_code == 401:
            raise RuntimeError("The Odds API rechazó la clave API.")
        response.raise_for_status()
        events.extend(response.json())
    return events
