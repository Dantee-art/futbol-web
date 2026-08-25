"""CLI del simulador Monte Carlo de remates de fútbol."""
import argparse
from src.collector import FootballDataCollector
from src.model import MatchModel
from src.simulator import MonteCarloSimulator


def main():
    parser = argparse.ArgumentParser(description="Simulador de remates de fútbol - 10.000 Monte Carlo")
    parser.add_argument("--home", help="Equipo local")
    parser.add_argument("--away", help="Equipo visitante")
    parser.add_argument("--competition", default="premier_league", help="Competición permitida")
    args = parser.parse_args()

    home = args.home or input("Equipo local: ").strip()
    away = args.away or input("Equipo visitante: ").strip()
    competition = args.competition

    try:
        collector = FootballDataCollector()
        home_data = collector.collect(home, competition, home=True)
        away_data = collector.collect(away, competition, home=False)
        model = MatchModel(home_data, away_data)
        result = MonteCarloSimulator(model).run(10_000)
        print(result.format_console(home, away, competition))
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("No se pudo construir una muestra suficiente con datos oficiales.")


if __name__ == "__main__":
    main()
