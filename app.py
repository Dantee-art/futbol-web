from __future__ import annotations
import argparse, json
from pathlib import Path
from arbitrage.odds_api import fetch_odds
from arbitrage.engine import find_arbitrage, allocate_stakes

SPORTS = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
    "soccer_germany_bundesliga", "soccer_france_ligue_one",
    "soccer_uefa_champs_league", "soccer_uefa_europa_league",
    "soccer_conmebol_libertadores", "soccer_brazil_campeonato",
    "soccer_argentina_primera_division",
]
OUT = Path("data/arbitrage.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--bankroll", type=float, default=100000.0)
    args = parser.parse_args()
    events = fetch_odds(SPORTS)
    opportunities = find_arbitrage(events)
    result = []
    for opp in opportunities:
        stakes = allocate_stakes(args.bankroll, opp)
        result.append({
            "event": opp.event, "sport": opp.sport, "market": opp.market,
            "implied_sum": round(opp.implied_sum, 8),
            "profit_pct": round(opp.profit_pct, 4),
            "bankroll_ars": args.bankroll,
            "stakes": stakes,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated_at": __import__('datetime').datetime.now().isoformat(), "bankroll_ars": args.bankroll, "opportunities": result}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Oportunidades encontradas: {len(result)}")

if __name__ == "__main__":
    main()
