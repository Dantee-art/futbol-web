from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class Opportunity:
    event: str
    sport: str
    market: str
    outcomes: list[dict[str, Any]]
    implied_sum: float
    profit_pct: float
    valid: bool


def _decimal(price: Any) -> float | None:
    try:
        value = float(price)
        return value if value > 1.0 else None
    except (TypeError, ValueError):
        return None


def find_arbitrage(events: list[dict[str, Any]], min_profit_pct: float = 0.10) -> list[Opportunity]:
    """Encuentra surebets binarias o multi-resultado usando la mejor cuota por outcome.

    La oportunidad es válida cuando sum(1/cuota_mejor) < 1. Para dos outcomes
    calcula la asignación óptima de banca que iguala el retorno bruto.
    """
    opportunities: list[Opportunity] = []
    for event in events:
        event_name = event.get("home_team", "") + " vs " + event.get("away_team", "")
        sport = event.get("sport_title", event.get("sport_key", ""))
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for bookmaker in event.get("bookmakers", []):
            book = bookmaker.get("title", bookmaker.get("key", ""))
            for market in bookmaker.get("markets", []):
                key = (market.get("key", ""), str(market.get("outcomes", [{}])[0].get("point", "")))
                outcomes = market.get("outcomes", [])
                # Para spreads/totals, el point identifica la misma línea.
                signature = (market.get("key", ""), tuple(sorted(str(o.get("point", "")) for o in outcomes)))
                bucket = grouped.setdefault(signature, {})
                for outcome in outcomes:
                    name = str(outcome.get("name", ""))
                    point = outcome.get("point")
                    price = _decimal(outcome.get("price"))
                    if price is None:
                        continue
                    oid = f"{name}|{point}"
                    old = bucket.get(oid)
                    if old is None or price > old["odds"]:
                        bucket[oid] = {"name": name, "point": point, "odds": price, "bookmaker": book}

        for signature, outcomes_map in grouped.items():
            outcomes = list(outcomes_map.values())
            # Solo evaluamos mercados donde todos los resultados necesarios tienen cuota.
            if len(outcomes) < 2:
                continue
            implied = sum(1.0 / o["odds"] for o in outcomes)
            profit = (1.0 / implied - 1.0) * 100.0
            if implied < 1.0 and profit >= min_profit_pct:
                opportunities.append(Opportunity(event_name, sport, signature[0], outcomes, implied, profit, True))
    return sorted(opportunities, key=lambda x: x.profit_pct, reverse=True)


def allocate_stakes(bankroll_ars: float, opportunity: Opportunity) -> list[dict[str, Any]]:
    """Distribuye ARS proporcionalmente a 1/cuota para igualar el retorno bruto."""
    if bankroll_ars <= 0 or not opportunity.valid:
        raise ValueError("La banca debe ser positiva y la oportunidad válida.")
    total_inverse = opportunity.implied_sum
    rows = []
    for outcome in opportunity.outcomes:
        stake = bankroll_ars * (1.0 / outcome["odds"]) / total_inverse
        rows.append({**outcome, "stake_ars": round(stake, 2), "gross_return_ars": round(stake * outcome["odds"], 2)})
    return rows
