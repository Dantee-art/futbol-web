# Sistema de Arbitraje Deportivo

Sistema de producción para detectar **surebets/arbitrajes** a partir de cuotas reales de The Odds API.

## Qué calcula

- Mejor cuota disponible por resultado y bookmaker.
- Suma de probabilidades implícitas `Σ(1/cuota)`.
- Arbitraje cuando esa suma es menor que 1.
- Margen teórico de arbitraje en porcentaje.
- Distribución óptima de una banca en pesos argentinos.
- Retorno bruto de cada pata.
- Ganancia bruta garantizada antes de comisiones, límites, redondeos, impuestos y posibles cambios de cuota.

## Seguridad de la API

La clave **NO está guardada en el repositorio**. Configura un GitHub Actions Secret llamado `ODDS_API_KEY`.

En GitHub: Settings → Secrets and variables → Actions → New repository secret.

Nunca pongas la clave en `index.html`, JavaScript, README, commits ni variables públicas del frontend.

## Actualización

GitHub Actions ejecuta el escáner cada 15 minutos y también permite ejecución manual. El resultado queda en `data/arbitrage.json`.

## Banca

El backend genera por defecto una distribución para ARS 100.000. La interfaz permite cambiar la banca y recalcula proporcionalmente cuánto apostar en cada pata.

Ejemplo conceptual:

`1/cuota_A + 1/cuota_B < 1`

Margen:

`(1 / suma - 1) × 100`

La asignación de banca se hace proporcionalmente a `1/cuota`, de forma que el retorno bruto sea aproximadamente igual en cualquiera de los resultados cubiertos.

## Importante

Un arbitraje matemático no garantiza que una casa acepte toda la apuesta. Límites, cambios de cuota, anulaciones, mercados no equivalentes, impuestos, comisiones y restricciones de cuenta pueden eliminar la rentabilidad. El sistema identifica oportunidades matemáticas; la ejecución debe verificarse manualmente en las casas correspondientes.
