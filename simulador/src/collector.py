"""Recolección de datos de remates usando ESPN y filtrado por condición."""
from datetime import date, timedelta
import requests
from config import COMPETITIONS, LAST_MATCHES, MIN_MATCHES

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

class FootballDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "FootballMonteCarlo/1.0"

    def _get(self, url, params=None):
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _find_team(self, name, league):
        # ESPN permite buscar por scoreboard. Recorremos ventanas de fechas para
        # encontrar el ID sin asumir que el usuario conoce el identificador.
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
                    if team.get("displayName", "").casefold() == name.casefold() or team.get("shortDisplayName", "").casefold() == name.casefold():
                        return team.get("id")
        raise ValueError(f"No encontré '{name}' en {league}. Usa el nombre oficial de ESPN.")

    @staticmethod
    def _stats(summary, team_id):
        """Extrae tiros/tiros al arco tolerando diferentes nombres de ESPN."""
        found = {"shots": None, "sot": None}
        for group in summary.get("boxscore", {}).get("players", []):
            if str(group.get("team", {}).get("id")) != str(team_id):
                continue
            for stat_group in group.get("statistics", []):
                labels = [str(x).lower() for x in stat_group.get("names", [])]
                values = stat_group.get("totals", [])
                for label, value in zip(labels, values):
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        continue
                    if label in {"shots", "totalshots", "shotstotal"}:
                        found["shots"] = (found["shots"] or 0) + value
                    elif label in {"shotsontarget", "sog", "shotsontargettotal"}:
                        found["sot"] = (found["sot"] or 0) + value
        return found

    def collect(self, team_name, competition, home):
        if competition not in COMPETITIONS:
            raise ValueError(f"Competición no permitida: {competition}")
        league = COMPETITIONS[competition][1]
        team_id = self._find_team(team_name, league)
        matches = []
        end = date.today()
        # Ventana amplia: temporada actual y temporadas cercanas quedan cubiertas
        # por eventos históricos; amistosos no se solicitan ni se incluyen.
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
                if not me or me.get("homeAway") != ("home" if home else "away"):
                    continue
                if event.get("status", {}).get("type", {}).get("state") != "post":
                    continue
                # Los amistosos/preseason no forman parte de los ligas/cupos seleccionados.
                try:
                    summary = self._get(f"{BASE}/{league}/summary", {"event": event.get("id")})
                    stats = self._stats(summary, team_id)
                except requests.RequestException:
                    continue
                if stats["shots"] is None or stats["sot"] is None:
                    continue
                matches.append({"shots": stats["shots"], "sot": stats["sot"], "date": d.isoformat()})
                if len(matches) >= LAST_MATCHES:
                    break
        if len(matches) < MIN_MATCHES:
            raise ValueError(f"Solo hay {len(matches)} partidos con remates verificables para {team_name}; se requieren al menos {MIN_MATCHES}.")
        return matches[-LAST_MATCHES:]
