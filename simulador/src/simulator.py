"""Simulación Monte Carlo y resumen de probabilidades."""
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
        bins = [(0,4),(5,7),(8,10),(11,13),(14,16),(17,19),(20,99)]
        return {f"{lo}-{hi if hi < 99 else '+'}": round(float(np.mean((values >= lo) & (values <= hi)) * 100), 2) for lo,hi in bins}

    def format_console(self, home, away, competition):
        total_sot = self.h_sot + self.a_sot
        total_shots = self.h_shots + self.a_shots
        lines = [
            "\n" + "="*64,
            "SIMULADOR MONTE CARLO — 10.000 ITERACIONES",
            f"{home} vs {away} | {competition}",
            "="*64,
            f"Remates totales esperados — {home}: {np.mean(self.h_shots):.2f}",
            f"Remates totales esperados — {away}: {np.mean(self.a_shots):.2f}",
            f"Remates al arco esperados — {home}: {np.mean(self.h_sot):.2f}",
            f"Remates al arco esperados — {away}: {np.mean(self.a_sot):.2f}",
            "\nPROBABILIDADES",
            f"Total remates > 20.5: {self._pct(total_shots,20.5):.2f}%",
            f"Total remates > 25.5: {self._pct(total_shots,25.5):.2f}%",
            f"Total remates al arco > 5.5: {self._pct(total_sot,5.5):.2f}%",
            f"Total remates al arco > 7.5: {self._pct(total_sot,7.5):.2f}%",
            f"{home} remates > 10.5: {self._pct(self.h_shots,10.5):.2f}%",
            f"{away} remates > 10.5: {self._pct(self.a_shots,10.5):.2f}%",
            f"{home} remates al arco > 2.5: {self._pct(self.h_sot,2.5):.2f}%",
            f"{away} remates al arco > 2.5: {self._pct(self.a_sot,2.5):.2f}%",
            "\nRANGOS — TOTAL REMATES AL ARCO",
        ]
        lines += [f"  {k}: {v:.2f}%" for k,v in self._ranges(total_sot).items()]
        return "\n".join(lines)

class MonteCarloSimulator:
    def __init__(self, model, seed=None):
        self.model = model
        self.rng = np.random.default_rng(seed)

    def _sample(self, fit, n):
        # Poisson model para el conteo; la desviación histórica se usa para
        # un factor multiplicativo que incorpora variabilidad real de la muestra.
        base = self.rng.poisson(max(fit["shots_mean"], 0.01), n)
        sot = self.rng.poisson(max(fit["sot_mean"], 0.01), n)
        sot = np.minimum(sot, base)
        return base, sot

    def run(self, iterations=10_000):
        hs, hst = self._sample(self.model.home, iterations)
        aw, ast = self._sample(self.model.away, iterations)
        return SimulationResult(hs, aw, hst, ast)
