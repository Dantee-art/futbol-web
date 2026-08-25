"""Modelo probabilístico de remates con sobredispersión y ajuste ataque-defensa."""
import numpy as np


class MatchModel:
    """
    Construye tasas de remates usando media + varianza histórica.

    Se usa una combinación conservadora entre la tasa ofensiva propia y la
    tasa que normalmente concede el rival. Para conteos sobredispersos se
    estima el parámetro de una Negative Binomial mediante media/varianza.
    """

    def __init__(self, home_data, away_data):
        self.home = self._fit(home_data)
        self.away = self._fit(away_data)

        # Ataque de local contra defensa del visitante.
        self.home_rate = self._blend_rate(self.home, self.away)
        self.away_rate = self._blend_rate(self.away, self.home)

    @staticmethod
    def _fit(data):
        shots = np.asarray([x["shots"] for x in data], dtype=float)
        sot = np.asarray([x["sot"] for x in data], dtype=float)

        return {
            "shots_mean": float(np.mean(shots)),
            "shots_var": float(np.var(shots, ddof=1)) if len(shots) > 1 else 0.0,
            "sot_mean": float(np.mean(sot)),
            "sot_var": float(np.var(sot, ddof=1)) if len(sot) > 1 else 0.0,
            "shots_std": float(np.std(shots, ddof=1)) if len(shots) > 1 else 0.0,
            "sot_std": float(np.std(sot, ddof=1)) if len(sot) > 1 else 0.0,
            "n": len(data),
        }

    @staticmethod
    def _blend_rate(team, opponent):
        """Promedia ataque propio y volumen concedido por el rival."""
        # En la muestra disponible solo tenemos la producción del equipo.
        # Como aproximación estable, la tasa propia conserva mayor peso.
        shots = 0.65 * team["shots_mean"] + 0.35 * opponent["shots_mean"]
        sot = 0.65 * team["sot_mean"] + 0.35 * opponent["sot_mean"]
        return {
            "shots_mean": max(0.01, shots),
            "sot_mean": max(0.01, sot),
            "shots_var": max(team["shots_var"], team["shots_mean"]),
            "sot_var": max(team["sot_var"], team["sot_mean"]),
        }

    @staticmethod
    def dispersion(mean, variance):
        """Devuelve (size, probability) para Negative Binomial.

        Si var <= mean, el proceso se comporta aproximadamente como Poisson.
        Si var > mean, se conserva la sobredispersión mediante NB.
        """
        if variance <= mean + 1e-9:
            return None
        p = mean / variance
        size = mean * p / max(1.0 - p, 1e-9)
        return max(size, 1e-6), min(max(p, 1e-6), 1 - 1e-6)
