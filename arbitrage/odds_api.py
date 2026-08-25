from __future__ import annotations
import os
import requests

BASE_URL = "https://api.the-odds-api.com/v4"
MARKETS = ["h2h", "totals", "spreads"]
REGIONS = "eu,uk,us"


def fetch_odds(sports: list[str], markets: list[str] | None = None) -> list[dict]:
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta ODDS_API_KEY. Configúrala como GitHub Actions Secret.")

    selected = markets or MARKETS
    events = []
    for sport in sports:
        params = {
            "apiKey": key,
            "regions": REGIONS,
            "markets": ",".join(selected),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        response = requests.get(
            f"{BASE_URL}/sports/{sport}/odds",
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise RuntimeError(
                "The Odds API devolvió HTTP 401: la ODDS_API_KEY configurada en "
                "GitHub Actions no es válida para The Odds API. Revisa que el "
                "secreto se llame exactamente ODDS_API_KEY y reemplázalo por una "
                "clave activa."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "The Odds API devolvió HTTP 429: se alcanzó el límite de uso/cuotas."
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("The Odds API devolvió un formato inesperado.")
        events.extend(payload)
    return events
