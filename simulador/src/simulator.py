"""Simulación Monte Carlo con Poisson/Negative Binomial."""
import numpy as np

class SimulationResult:
    def __init__(self, h_shots, a_shots, h_sot, a_sot):
        self.h_shots, self.a_shots = h_shots, a_shots
        self.h_sot, self.a_sot = h_sot, a_sot

    @staticmethod
    def _pct(values, threshold):
        return round(float(np.mean(values > threshold) * 100), 2)

    @staticmethod
    def _ranges(values):
        bins = [(0,4),(5,7),(8,10),(11,13),(14,16),(17,19),(20,999)]
        return {f"{lo}-{hi if hi < 999 else '+'}": round(float(np.mean((values >= lo) & (values <= hi))*100),2) for lo,hi in bins}

    def to_dict(self):
        total_shots = self.h_shots + self.a_shots
        total_sot = self.h_sot + self.a_sot
        return {
            "iterations": int(len(self.h_shots)),
            "expected": {
                "home_shots": round(float(np.mean(self.h_shots)),2),
                "away_shots": round(float(np.mean(self.a_shots)),2),
                "home_sot": round(float(np.mean(self.h_sot)),2),
                "away_sot": round(float(np.mean(self.a_sot)),2),
            },
            "probabilities": {
                "total_shots_over_20_5": self._pct(total_shots,20.5),
                "total_shots_over_25_5": self._pct(total_shots,25.5),
                "total_sot_over_5_5": self._pct(total_sot,5.5),
                "total_sot_over_7_5": self._pct(total_sot,7.5),
                "home_shots_over_10_5": self._pct(self.h_shots,10.5),
                "away_shots_over_10_5": self._pct(self.a_shots,10.5),
                "home_sot_over_2_5": self._pct(self.h_sot,2.5),
                "away_sot_over_2_5": self._pct(self.a_sot,2.5),
            },
            "sot_ranges": self._ranges(total_sot),
        }

    def format_console(self, home, away, competition):
        d=self.to_dict(); lines=["\n"+"="*64,"SIMULADOR MONTE CARLO — 10.000 ITERACIONES",f"{home} vs {away} | {competition}","="*64]
        e=d["expected"]; p=d["probabilities"]
        lines += [f"Remates — {home}: {e['home_shots']:.2f}",f"Remates — {away}: {e['away_shots']:.2f}",f"Al arco — {home}: {e['home_sot']:.2f}",f"Al arco — {away}: {e['away_sot']:.2f}","\nPROBABILIDADES"]
        for k,v in p.items(): lines.append(f"{k}: {v:.2f}%")
        return "\n".join(lines)

class MonteCarloSimulator:
    def __init__(self, model, seed=None): self.model=model; self.rng=np.random.default_rng(seed)

    def _negative_binomial(self, mean, variance, n):
        if variance <= mean + 1e-9: return None
        p=mean/variance; size=mean*p/max(1-p,1e-9)
        return self.rng.negative_binomial(max(size,1e-6),min(max(p,1e-6),1-1e-6),n)

    def _sample(self, fit, n):
        shots=self._negative_binomial(fit["shots_mean"],fit["shots_var"],n)
        if shots is None: shots=self.rng.poisson(max(fit["shots_mean"],.01),n)
        sot=self._negative_binomial(fit["sot_mean"],fit["sot_var"],n)
        if sot is None: sot=self.rng.poisson(max(fit["sot_mean"],.01),n)
        return shots,np.minimum(sot,shots)

    def run(self, iterations=10_000):
        hs,hst=self._sample(self.model.home_rate,iterations); aw,ast=self._sample(self.model.away_rate,iterations)
        return SimulationResult(hs,aw,hst,ast)
