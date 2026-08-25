"""Simulación Monte Carlo con Poisson/Negative Binomial."""
import numpy as np


class SimulationResult:
    def __init__(self, h_shots, a_shots, h_sot, a_sot):
        self.h_shots, self.a_shots = h_shots, a_shots
        self.h_sot, self.a_sot = h_sot, a_sot

    @staticmethod
    def _pct(values, threshold):
        return float(np.mean(values > threshold) * 100)

    @staticmethod
    def _ranges(values):
        bins = [(0, 4), (5, 7), (8, 10), (11, 13), (14, 16), (17, 19), (20, 999)]
        return {
            f"{lo}-{hi if hi < 999 else '+'}": round(float(np.mean((values >= lo) & (values <= hi)) * 100), 2)
            for lo, hi in bins
        }

    def format_console(self, home, away, competition):
        total_sot = self.h_sot + self.a_sot
        total_shots = self.h_shots + self.a_shots
        lines = [
            "\n" + "=" * 64,
            "SIMULADOR MONTE CARLO — 10.000 ITERACIONES",
            f"{home} vs {away} | {competition}",
            "=" * 64,
            f"Remates totales esperados — {home}: {np.mean(self.h_shots):.2f}",
            f"Remates totales esperados — {away}: {np.mean(self.a_shots):.2f}",
            f"Remates al arco esperados — {home}: {np.mean(self.h_sot):.2f}",
            f"Remates al arco esperados — {away}: {np.mean(self.a_sot):.2f}",
            "\nPROBABILIDADES",
            f"Total remates > 20.5: {self._pct(total_shots, 20.5):.2f}%",
            f"Total remates > 25.5: {self._pct(total_shots, 25.5):.2f}%",
            f"Total remates al arco > 5.5: {self._pct(total_sot, 5.5):.2f}%",
            f"Total remates al arco > 7.5: {self._pct(total_sot, 7.5):.2f}%",
            f"{home} remates > 10.5: {self._pct(self.h_shots, 10.5):.2f}%",
            f"{away} remates > 10.5: {self._pct(self.a_shots, 10.5):.2f}%",
            f"{home} remates al arco > 2.5: {self._pct(self.h_sot, 2.5):.2f}%",
            f"{away} remates al arco > 2.5: {self._pct(self.a_sot, 2.5):.2f}%",
            "\nRANGOS — TOTAL REMATES AL ARCO",
        ]
        lines += [f"  {k}: {v:.2f}%" for k, v in self._ranges(total_sot).items()]
        return "\n".join(lines)


class MonteCarloSimulator:
    def __init__(self, model, seed=None):
        self.model = model
        self.rng = np.random.default_rng(seed)

    def _negative_binomial(self, mean, variance, n):
        """Muestra NB si varianza > media; devuelve None si Poisson es mejor."""
        if variance <= mean + 1e-9:
            return None
        p = mean / variance
        size = mean * p / max(1.0 - p, 1e-9)
        size = max(size, 1e-6)
        p = min(max(p, 1e-6), 1 - 1e-6)
        return self.rng.negative_binomial(size, p, n)

    def _sample(self, fit, n):
        shots = self._negative_binomial(
            fit["shots_mean"], fit["shots_var"], n
        )
        if shots is None:
            shots = self.rng.poisson(max(fit["shots_mean"], 0.01), n)

        sot = self._negative_binomial(
            fit["sot_mean"], fit["sot_var"], n
        )
        if sot is None:
            sot = self.rng.poisson(max(fit["sot_mean"], 0.01), n)

        # Un remate al arco no puede superar los remates totales.
        sot = np.minimum(sot, shots)
        return shots, sot

    def run(self, iterations=10_000):
        hs, hst = self._sample(self.model.home_rate, iterations)
        aw, ast = self._sample(self.model.away_rate, iterations)
        return SimulationResult(hs, aw, hst, ast)
