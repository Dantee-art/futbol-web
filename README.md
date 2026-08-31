# Mercados de remates

Panel diario de fútbol alimentado por The Odds API. La aplicación está diseñada para mostrar únicamente líneas que una casa de apuestas haya publicado y que el proveedor entregue explícitamente.

## Importante

The Odds API documenta actualmente mercados de remates de jugadores (`player_shots` y `player_shots_on_target`) para fútbol, pero no documenta un mercado general de **remates totales del partido** ni **remates totales por equipo**. Por eso el sistema no transforma `totals` de goles en remates ni inventa líneas. Si el proveedor devuelve una clave explícita de shots, se muestra; si no, aparece `No disponible`.

## Configuración

Crear el secreto de GitHub Actions:

`ODDS_API_KEY`

Nunca guardar la clave en este repositorio.

## Actualización

GitHub Actions ejecuta `python -m src.collector` cada 30 minutos y publica `data/remates_hoy.json`. La interfaz lee ese JSON y refresca la tabla cada minuto.
