"""Configuración central del simulador."""
COMPETITIONS = {
    "premier_league": ("Premier League", "eng.1"),
    "la_liga": ("LaLiga", "esp.1"),
    "bundesliga": ("Bundesliga", "ger.1"),
    "serie_a": ("Serie A", "ita.1"),
    "ligue_1": ("Ligue 1", "fra.1"),
    "champions": ("UEFA Champions League", "uefa.champions"),
    "europa": ("UEFA Europa League", "uefa.europa"),
    "libertadores": ("Copa Libertadores", "conmebol.libertadores"),
    "brasileirao": ("Brasileirão", "bra.1"),
    "argentina": ("Liga Profesional Argentina", "arg.1"),
}
LAST_MATCHES = 20
MIN_MATCHES = 8
ITERATIONS = 10_000
MAX_SEASONS_BACK = 3
