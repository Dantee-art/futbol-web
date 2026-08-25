"""Recolección de remates con separación ataque/defensa y condición."""
from datetime import date, timedelta
import requests
from config import COMPETITIONS, LAST_MATCHES, MIN_MATCHES

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

class FootballDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "FootballMonteCarlo/2.0"

    def _get(self, url, params=None):
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _find_team(self, name, league):
        end = date.today()
        for days in range(0, 370, 14):
            d = end - timedelta(days=days)
            try:
                data = self._get(f"{BASE}/{league}/scoreboard", {"dates": d.strftime('%Y%m%d'), "limit": 100})
            except requests.RequestException:
                continue
            for event in data.get("events", []):
                for c in event.get("competitions", [{}])[0].get("competitors", []):
                    team = c.get("team", {})
                    names = {str(team.get("displayName", "")).casefold(), str(team.get("shortDisplayName", "")).casefold(), str(team.get("name", "")).casefold()}
                    if name.casefold() in names:
                        return team.get("id")
        raise ValueError(f"No encontré '{name}' en {league}.")

    @staticmethod
    def _stats(summary, team_id):
        result = {"shots": None, "sot": None}
        for group in summary.get("boxscore", {}).get("players", []):
            if str(group.get("team", {}).get("id")) != str(team_id):
                continue
            for stat_group in group.get("statistics", []):
                labels = [str(x).lower().replace(" ", "") for x in stat_group.get("names", [])]
                values = stat_group.get("totals", [])
                for label, value in zip(labels, values):
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        continue
                    if label in {"shots", "totalshots", "shotstotal"}:
                        result["shots"] = (result["shots"] or 0.0) + value
                    elif label in {"shotsontarget", "sog", "shotsontargettotal"}:
                        result["sot"] = (result["sot"] or 0.0) + value
        return result

    def collect(self, team_name, competition, home):
        if competition not in COMPETITIONS:
            raise ValueError(f"Competición no permitida: {competition}")
        league = COMPETITIONS[competition][1]
        team_id = self._find_team(team_name, league)
        condition = "home" if home else "away"
        matches = []
        end = date.today()

        for days in range(0, 1100, 7):
            if len(matches) >= LAST_MATCHES:
                break
            d = end - timedelta(days=days)
            try:
                data = self._get(f"{BASE}/{league}/scoreboard", {"dates": d.strftime('%Y%m%d'), "limit": 100})
            except requests.RequestException:
                continue
            for event in data.get("events", []):
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                me = next((c for c in competitors if str(c.get("team", {}).get("id")) == str(team_id)), None)
                if not me or me.get("homeAway") != condition:
                    continue
                if event.get("status", {}).get("type", {}).get("state") != "post":
                    continue
                opponent = next((c for c in competitors if str(c.get("team", {}).get("id")) != str(team_id)), None)
                if not opponent:
                    continue
                try:
                    summary = self._get(f"{BASE}/{league}/summary", {"event": event.get("id")})
                    own = self._stats(summary, team_id)
                    opp = self._stats(summary, opponent.get("team", {}).get("id"))
                except requests.RequestException:
                    continue
                if any(x is None for x in (own["shots"], own["sot"], opp["shots"], opp["sot"])):
                    continue
                matches.append({
                    "shots_for": own["shots"], "sot_for": own["sot"],
                    "shots_against": opp["shots"], "sot_against": opp["sot"],
                    "date": d.isoformat(), "condition": condition, "event_id": event.get("id")
                })
                if len(matches) >= LAST_MATCHES:
                    break

        if len(matches) < MIN_MATCHES:
            raise ValueError(f"Solo hay {len(matches)} partidos verificables para {team_name}; se requieren al menos {MIN_MATCHES}.")
        return matches[-LAST_MATCHES:]
