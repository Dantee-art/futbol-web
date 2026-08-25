"""Modelo de remates: ataque propio + defensa rival + sobredispersión."""
import numpy as np

class MatchModel:
    def __init__(self, home_data, away_data):
        self.home = self._fit(home_data)
        self.away = self._fit(away_data)
        self.home_rate = self._match_rate(self.home, self.away)
        self.away_rate = self._match_rate(self.away, self.home)

    @staticmethod
    def _fit(data):
        def arr(key):
            return np.asarray([x[key] for x in data], dtype=float)
        sf, st = arr("shots_for"), arr("sot_for")
        sa, sta = arr("shots_against"), arr("sot_against")
        return {
            "attack_shots": float(sf.mean()), "attack_shots_var": float(sf.var(ddof=1)),
            "attack_sot": float(st.mean()), "attack_sot_var": float(st.var(ddof=1)),
            "def_shots": float(sa.mean()), "def_shots_var": float(sa.var(ddof=1)),
            "def_sot": float(sta.mean()), "def_sot_var": float(sta.var(ddof=1)),
            "n": len(data),
        }

    @staticmethod
    def _match_rate(team, opponent):
        # 60% ataque propio + 40% volumen que concede el rival.
        shots = 0.60 * team["attack_shots"] + 0.40 * opponent["def_shots"]
        sot = 0.60 * team["attack_sot"] + 0.40 * opponent["def_sot"]
        # Combina varianzas para no borrar la incertidumbre de ninguno.
        shots_var = 0.60 * team["attack_shots_var"] + 0.40 * opponent["def_shots_var"]
        sot_var = 0.60 * team["attack_sot_var"] + 0.40 * opponent["def_sot_var"]
        return {"shots_mean": max(shots, 0.05), "sot_mean": max(sot, 0.05),
                "shots_var": max(shots_var, shots), "sot_var": max(sot_var, sot)}

    @staticmethod
    def dispersion(mean, variance):
        if variance <= mean + 1e-9:
            return None
        p = mean / variance
        size = mean * p / max(1.0 - p, 1e-9)
        return max(size, 1e-6), min(max(p, 1e-6), 1 - 1e-6)
