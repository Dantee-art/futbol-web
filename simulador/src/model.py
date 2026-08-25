"""Modelo probabilístico de remates."""
import numpy as np

class MatchModel:
    def __init__(self, home_data, away_data):
        self.home = self._fit(home_data)
        self.away = self._fit(away_data)

    @staticmethod
    def _fit(data):
        shots = np.array([x["shots"] for x in data], dtype=float)
        sot = np.array([x["sot"] for x in data], dtype=float)
        # Media suavizada: evita que un partido extremo domine la tasa.
        return {
            "shots_mean": float(np.mean(shots)),
            "shots_std": float(np.std(shots, ddof=1)) if len(shots) > 1 else 0.0,
            "sot_mean": float(np.mean(sot)),
            "sot_std": float(np.std(sot, ddof=1)) if len(sot) > 1 else 0.0,
            "n": len(data),
        }
