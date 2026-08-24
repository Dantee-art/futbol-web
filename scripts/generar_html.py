"""
generar_html.py
Lee datos/picks_hoy.json (armado por actualizar_datos.py) y genera
index.html: el expediente completo del dia, agrupado por liga.
Si un dato puntual no vino de ESPN, se muestra como "no disponible"
en vez de inventarlo.
"""

import json
import html as html_lib
import os  # <-- Importamos os para manejar las rutas

# --- CORRECCIÓN DE RUTAS ABSOLUTAS ---
DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_RAIZ = os.path.dirname(DIRECTORIO_SCRIPT)

INPUT_PATH = os.path.join(DIRECTORIO_RAIZ, "datos", "picks_hoy.json")
OUTPUT_PATH = os.path.join(DIRECTORIO_RAIZ, "index.html")
# -------------------------------------


def esc(txt):
    return html_lib.escape(str(txt)) if txt is not None else ""


def render_top5(top5):
    if not top5:
        return '<div class="redactado">⊘ Sin picks con suficiente base estadística hoy para armar un Top 5 confiable.</div>'
    filas = []
    for i, p in enumerate(top5, start=1):
        filas.append(f'''
        <div class="top5-item">
          <span class="top5-rank">#{i}</span>
          <div class="top5-body">
            <div class="top5-liga">{esc(p["liga_nombre"])}</div>
            <div class="top5-partido">{esc(p["local"])} vs. {esc(p["visita"])}</div>
            <div class="top5-mercado">{esc(p["mercado"])}</div>
            <div class="top5-justif">{esc(p["justificacion"])}</div>
            <div class="top5-meta">Confianza {esc(p["confianza"])} · base {esc(p["n_min"])} partidos comparables</div>
          </div>
        </div>''')
    return "".join(filas)


def render_pick_seguro(pick):
    if not pick or not pick.get("disponible"):
        razon = (pick or {}).get("razon", "Sin datos suficientes.")
        return f'<div class="redactado">⊘ <b>Sin pick seguro disponible:</b> {esc(razon)}</div>'
    alternativas = pick.get("alternativas", [])
    alt_html = ""
    if alternativas:
        items = "".join(f'<li>{esc(a["mercado"])}</li>' for a in alternativas)
        alt_html = f'<div class="fundamento" style="margin-top:6px">Alternativas de respaldo: <ul style="margin-left:16px">{items}</ul></div>'
    return f'''
    <div class="pick-destacado" style="background:var(--verified-teal)">
      <span class="tag" style="color:#e8dcae">Pick más seguro · confianza {esc(pick.get("confianza",""))}</span>
      <div class="valor">{esc(pick["mercado"])}</div>
      <div class="fundamento">{esc(pick["justificacion"])}</div>
      {alt_html}
    </div>'''


def render_cuotas(pickcenter):
    if not pickcenter:
        return '<div class="redactado">⊘ <b>Sin cuota fija disponible</b> para este partido en la fuente.</div>'
    p = pickcenter[0]  # primer proveedor (suele ser el principal)
    proveedor = p.get("provider", {}).get("name", "Casa de apuestas")
    home_odds = p.get("homeTeamOdds", {})
    away_odds = p.get("awayTeamOdds", {})
    ou = p.get("overUnder")
    partes = [f'<div class="pick-destacado"><span class="tag">Cuota fija · {esc(proveedor)}</span>']
    if home_odds.get("moneyLine") is not None:
        partes.append(f'<div class="valor">Local {esc(home_odds.get("moneyLine"))} · Visitante {esc(away_odds.get("moneyLine"))}</div>')
    if ou is not None:
        partes.append(f'<div class="fundamento">Línea de goles totales: Over/Under {esc(ou)}</div>')
    partes.append("</div>")
    return "".join(partes)


def render_h2h(seasonseries):
    if not seasonseries:
        return '<div class="redactado">⊘ Sin historial H2H disponible.</div>'
    s = seasonseries[0]
    resumen = s.get("summary", "")
    eventos = s.get("events", [])[:5]
    filas = "".join(
        f'<div class="evento-ficha"><span class="evento-desc">{esc(e.get("shortDetail", e.get("date","")))} — '
        f'{esc(e.get("shortSummary", ""))}</span></div>'
        for e in eventos
    )
    return f'<p class="analisis-parrafo"><b>{esc(resumen)}</b></p>{filas}'


def render_eventos_clave(eventos):
    if not eventos:
        return '<div class="redactado">⊘ Sin eventos registrados.</div>'
    filas = []
    for e in eventos:
        tipo = (e.get("type", {}) or {}).get("text", "")
        minuto = e.get("clock", {}).get("displayValue", "")
        texto = e.get("text", "")
        clase = "tipo-gol" if tipo.lower() == "goal" else ("tipo-roja" if "red" in tipo.lower() else "tipo-amarilla" if "card" in tipo.lower() else "")
        if clase:
            filas.append(
                f'<div class="evento-ficha"><span class="evento-min">{esc(minuto)}</span>'
                f'<span class="evento-tipo {clase}">{esc(tipo)}</span>'
                f'<span class="evento-desc">{esc(texto)}</span></div>'
            )
    return "".join(filas) if filas else '<div class="redactado">⊘ Sin goles ni tarjetas registrados.</div>'


def render_historial_box(hist, titulo):
    if hist.get("partidos_evaluados", 0) == 0:
        return f'<div class="redactado">⊘ Sin historial calculable para {esc(titulo)}.</div>'
    return f'''
    <div class="comparativa-mini">
      <div class="section-label" style="margin-top:10px">{esc(titulo)} <span class="sello">base: {hist["partidos_evaluados"]} partidos reales</span></div>
      <div class="comp-grid">
        <div class="stat-box"><div class="stat-label">Goles a favor</div><div class="stat-val">{hist["goles_favor_prom"]}</div></div>
        <div class="stat-box"><div class="stat-label">Goles en contra</div><div class="stat-val">{hist["goles_contra_prom"]}</div></div>
        <div class="stat-box"><div class="stat-label">Tarjetas/partido</div><div class="stat-val">{hist["tarjetas_prom"]}</div></div>
        <div class="stat-box"><div class="stat-label">Remates totales</div><div class="stat-val">{hist["remates_totales_prom"]}</div></div>
        <div class="stat-box"><div class="stat-label">Remates al arco</div><div class="stat-val">{hist["remates_arco_prom"]}</div></div>
        <div class="stat-box"><div class="stat-label">% Ambos anotan</div><div class="stat-val">{hist["partidos_ambos_anotan_pct"]}%</div></div>
      </div>
    </div>'''


def render_partido(p, idx_global):
    if "error" in p:
        return f'<div class="redactado">⊘ No se pudo procesar este partido (error de datos).</div>'

    venue = p.get("venue", {}).get("fullName", "Estadio no informado")
    arbitro = p.get("arbitro") or "No confirmado"
    anchor = f"partido-{idx_global}"

    return f'''
    <details class="match-card" id="{anchor}">
      <summary>
        <div>
          <div class="match-teams">{esc(p["local"]["nombre"])} vs. {esc(p["visita"]["nombre"])}</div>
          <div class="match-meta">{esc(venue)} · Árbitro: {esc(arbitro)} · {esc(p.get("estado",""))}</div>
        </div>
      </summary>
< truncated lines 145-150 >
        {render_cuotas(p.get("cuotas"))}

        <div class="section-label" style="margin-top:16px">Historial H2H <span class="sello">verificado · seasonseries</span></div>
        {render_h2h(p.get("h2h"))}

        <div class="section-label" style="margin-top:16px">Eventos del partido <span class="sello">verificado · keyEvents</span></div>
        {render_eventos_clave(p.get("eventos_clave"))}

        <div class="section-label" style="margin-top:16px">Historial calculado <span class="sello pendiente">cálculo propio, no es cuota de casa</span></div>
        {render_historial_box(p.get("historial_local", {}), p["local"]["nombre"])}
        {render_historial_box(p.get("historial_visita", {}), p["visita"]["nombre"])}

        <div class="section-label" style="margin-top:16px">Análisis <span class="sello">generado con plantillas Python · sin IA</span></div>
        <p class="analisis-parrafo">{esc(p.get("analisis","")).replace(chr(10), "<br>")}</p>
      </div>
    </details>'''


def generar():
    with open(INPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    ligas = data.get("ligas", [])
    idx_global = 0
    indice_html = []
    cuerpo_html = []

    for liga in ligas:
        slug = liga["slug"]
        nombre = liga["nombre"]
        n_partidos = len(liga["partidos"])
        indice_html.append(f'<a href="#liga-{slug}" class="indice-item">{esc(nombre)} <span>{n_partidos}</span></a>')

        partidos_html = []
        for p in liga["partidos"]:
            idx_global += 1
            partidos_html.append(render_partido(p, idx_global))

        cuerpo_html.append(f'''
        <section class="liga-section" id="liga-{slug}">
          <div class="liga-header">
            <span class="liga-titulo">{esc(nombre)}</span>
            <span class="liga-count">{n_partidos} partido(s)</span>
          </div>
          {"".join(partidos_html)}
        </section>''')

    generado = data.get("generado", "")

    html_final = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Expediente del día — Picks</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>
<span class="folder-tab">EXPEDIENTE DIARIO · ACTUALIZADO {esc(generado)}</span>
<header>
  <h1>Picks del día</h1>
  <div class="subtitulo">Todos los datos provienen de la API pública de ESPN. Ningún número es estimado ni inventado; lo que falta se marca como no disponible.</div>
</header>
<nav class="indice">{"".join(indice_html)}</nav>
<section class="top5-section">
  <div class="section-label" style="font-size:12px">Top 5 picks del día · todas las ligas <span class="sello pendiente">ranking global, cálculo propio</span></div>
  {render_top5(data.get("top5_dia", []))}
</section>
{"".join(cuerpo_html)}
<footer>
  <b>Metodología:</b> cuotas y mercado principal desde pickcenter (ESPN). H2H desde seasonseries. Tarjetas y goles con jugador/minuto desde keyEvents. Remates por equipo desde boxscore. Promedios de historial calculados sobre los últimos {esc(data.get("historial_n","20"))} partidos jugados de cada equipo, vía teams/schedule. El "pick más seguro" es un cálculo propio que compara la fuerza estadística de varios mercados (doble oportunidad, goles totales, remates) y elige el de mayor desvío respecto a una línea de referencia — no es una recomendación de casa de apuestas. Sin córners ni remates por jugador individual: no existen en esta fuente. Sin bajas/lesiones: endpoint sin datos cargados. Análisis narrativo generado con plantillas condicionales en Python, sin IA ni costo de API.
</footer>
</body>
</html>'''

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"Generado {OUTPUT_PATH} con {idx_global} partidos en {len(ligas)} ligas.")


CSS = """
:root{
  --paper:#e9e2d0; --paper-dark:#ddd4bd; --ink:#1e1b16; --ink-soft:#4a4438;
  --pencil:#7a725f; --stamp-red:#a23324; --verified-teal:#2f5e52;
  --redact:#191510; --rule:#c7bca0;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--paper);color:var(--ink);font-family:'Source Serif 4',serif;padding-bottom:60px;}
.folder-tab{background:var(--ink);color:var(--paper);font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;padding:8px 16px;display:inline-block;border-radius:0 0 6px 0;}
header{padding:18px 20px 20px;border-bottom:3px double var(--ink);}
h1{font-family:'Special Elite',monospace;font-size:26px;margin-bottom:6px;}
.subtitulo{font-size:12.5px;color:var(--ink-soft);font-style:italic;}
.indice{display:flex;flex-wrap:wrap;gap:8px;padding:16px 20px;border-bottom:1px solid var(--rule);}
.indice-item{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--verified-teal);text-decoration:none;border:1px solid var(--verified-teal);border-radius:3px;padding:4px 8px;background:rgba(47,94,82,0.06);}
.indice-item span{color:var(--pencil);margin-left:4px;}
.liga-section{padding:18px 20px;border-bottom:2px solid var(--ink-soft);}
.liga-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;}
.liga-titulo{font-family:'Special Elite',monospace;font-size:19px;}
.liga-count{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--pencil);}
.match-card{background:var(--paper-dark);border:1px solid var(--rule);border-radius:4px;margin-bottom:12px;overflow:hidden;}
.match-card summary{padding:12px 14px;cursor:pointer;list-style:none;}
.match-card summary::-webkit-details-marker{display:none;}
.match-teams{font-family:'Special Elite',monospace;font-size:15px;}
.match-meta{font-family:'JetBrains Mono',monospace;font-size:9.5px;color:var(--pencil);margin-top:3px;}
.match-body{padding:0 14px 16px;border-top:1px dashed var(--rule);}
.section-label{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--pencil);margin-top:12px;margin-bottom:6px;display:flex;align-items:center;gap:6px;}
.sello{display:inline-flex;align-items:center;gap:4px;font-family:'JetBrains Mono',monospace;font-size:8.5px;text-transform:uppercase;color:var(--verified-teal);border:1.2px solid var(--verified-teal);border-radius:3px;padding:1px 5px;transform:rotate(-1.5deg);}
.sello.pendiente{color:var(--stamp-red);border-color:var(--stamp-red);}
.sello::before{content:"✓";font-weight:700;}
.sello.pendiente::before{content:"⊘";}
.pick-destacado{background:var(--ink);color:var(--paper);padding:12px 14px;border-radius:2px;}
.pick-destacado .tag{font-family:'JetBrains Mono',monospace;font-size:8.5px;letter-spacing:1.5px;text-transform:uppercase;color:#c9a227;display:block;margin-bottom:4px;}
.pick-destacado .valor{font-family:'Special Elite',monospace;font-size:15px;}
.pick-destacado .fundamento{font-size:11px;color:#c9c2ad;margin-top:4px;}
.redactado{background:repeating-linear-gradient(135deg,var(--redact),var(--redact) 6px,#2a2419 6px,#2a2419 7px);color:var(--paper);font-family:'JetBrains Mono',monospace;font-size:10px;padding:8px 10px;border-radius:2px;}
.evento-ficha{display:flex;gap:8px;align-items:baseline;padding:5px 0;border-bottom:1px dashed var(--rule);font-size:12.5px;}
.evento-min{font-family:'JetBrains Mono',monospace;font-weight:700;width:38px;flex-shrink:0;font-size:11px;}
.evento-tipo{font-size:8.5px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;padding:1px 5px;border-radius:2px;flex-shrink:0;}
.tipo-gol{background:var(--verified-teal);color:var(--paper);}
.tipo-amarilla{background:#c9a227;color:var(--ink);}
.tipo-roja{background:var(--stamp-red);color:var(--paper);}
.comp-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:4px;}
.stat-box{background:rgba(0,0,0,0.04);border:1px solid var(--rule);border-radius:3px;padding:6px 8px;}
.stat-label{font-size:8.5px;font-family:'JetBrains Mono',monospace;color:var(--pencil);text-transform:uppercase;}
.stat-val{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;color:var(--verified-teal);}
.analisis-parrafo{font-size:12.5px;line-height:1.6;}
footer{padding:18px 20px 30px;font-family:'JetBrains Mono',monospace;font-size:9.5px;color:var(--pencil);line-height:1.7;}
.top5-section{padding:16px 20px 20px;border-bottom:3px double var(--ink);background:rgba(47,94,82,0.05);}
.top5-item{display:flex;gap:12px;padding:12px 0;border-bottom:1px dashed var(--rule);}
.top5-item:last-child{border-bottom:none;}
.top5-rank{font-family:'Special Elite',monospace;font-size:22px;color:var(--verified-teal);width:36px;flex-shrink:0;}
.top5-liga{font-family:'JetBrains Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--pencil);}
.top5-partido{font-family:'Special Elite',monospace;font-size:14px;margin:2px 0;}
.top5-mercado{font-size:13px;font-weight:600;color:var(--verified-teal);}
.top5-justif{font-size:11.5px;color:var(--ink-soft);margin-top:2px;}
.top5-meta{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--pencil);margin-top:4px;}
"""

if __name__ == "__main__":
    generar()
