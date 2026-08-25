# Simulador de Partidos de Fútbol — Monte Carlo

Módulo independiente dentro de `futbol-web` para estimar remates totales y remates al arco mediante **10.000 simulaciones Monte Carlo**.

## Datos

Usa partidos oficiales de las competiciones configuradas. Los amistosos no se consultan. Los datos se separan estrictamente por condición: el equipo local se analiza con sus partidos como local y el visitante con sus partidos como visitante. Se buscan hasta 20 partidos verificables y se amplía la ventana histórica cuando la temporada actual no alcanza.

Competiciones habilitadas: Premier League, LaLiga, Bundesliga, Serie A, Ligue 1, Champions League, Europa League, Libertadores, Brasileirão y Liga Profesional Argentina.

## Instalación

```bash
cd simulador
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Ejemplo

```bash
python main.py --home "Liverpool" --away "Arsenal" --competition premier_league
```

El programa muestra medias esperadas, remates al arco, probabilidades Over de distintas líneas y distribución de rangos.

## Nota estadística

La simulación usa Poisson como modelo base para conteos. Los últimos 20 partidos forman la muestra; la desviación estándar queda disponible en el ajuste para futuras extensiones de sobredispersión. Las probabilidades son estimaciones del modelo, no garantías de resultados.
