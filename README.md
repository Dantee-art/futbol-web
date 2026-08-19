# valuebets-afa

Detector automático de value bets para Liga Profesional Argentina y Copa Libertadores.
Compara las cuotas de Bet365 y Betano contra el consenso de mercado (promedio sin vig
de todas las casas disponibles vía odds-api.io) y publica los resultados en un dashboard.

## Cómo funciona

1. `scripts/recolectar_cuotas.py` — busca las ligas argentinas en odds-api.io, trae los
   próximos partidos y las cuotas de todas las casas disponibles → `datos/cuotas.json`
2. `scripts/calcular_ev.py` — arma el consenso de mercado y calcula el EV de Bet365/Betano
   contra ese consenso → `datos/value_bets.json`
3. `.github/workflows/actualizar.yml` — corre los dos scripts cada 6 horas y commitea
   los resultados automáticamente
4. `index.html` — dashboard que lee `datos/value_bets.json` y muestra los value bets
   ordenados por EV

## Setup (todo desde GitHub, sin local)

1. Creá el repo `valuebets-afa` en GitHub (público, para que funcione GitHub Pages)
2. Subí esta estructura de carpetas y archivos tal cual
3. Andá a **Settings → Secrets and variables → Actions → New repository secret**
   - Nombre: `ODDS_API_KEY`
   - Valor: tu API key de odds-api.io
4. Andá a **Settings → Actions → General → Workflow permissions** y activá
   "Read and write permissions"
5. Andá a **Settings → Pages** y activá GitHub Pages desde la rama `main`, carpeta `/ (root)`
6. Andá a la pestaña **Actions**, elegí "Actualizar value bets" y tocá **Run workflow**
   para el primer corrido manual (así no esperás 6 horas)
7. Cuando termine, entrá a `https://<tu-usuario>.github.io/valuebets-afa/`

## ⚠️ Importante sobre el schema de odds-api.io

El schema exacto que devuelve `/events/{id}/odds` no está 100% documentado
públicamente. `calcular_ev.py` asume una estructura razonable, pero si el primer
run te da "0 partidos con datos usables" en el log de Actions:

1. Bajá `datos/cuotas.json` y mirá cómo vino un partido real
2. Ajustá la función `extraer_1x2()` en `scripts/calcular_ev.py` a la forma real
3. Pedime ayuda pegando un fragmento de ese JSON y lo arreglamos juntos

## Limitaciones conocidas

- Free tier de odds-api.io: 100 requests/hora — con pocos partidos por día alcanza sobra
- El "consenso de mercado" necesita al menos 2 casas con cuotas para ese partido;
  si un partido tiene poca cobertura de casas, no se evalúa
- Esto NO es un modelo predictivo propio (todavía) — es detección de discrepancias
  entre casas. Un +EV real requiere además que el consenso mismo sea confiable
  (partidos con pocas casas listadas pueden dar consensos poco representativos)
  
