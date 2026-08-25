"""Actualizador diario de fútbol: partidos de hoy + historial + picks."""
import json, os
from datetime import datetime, timezone, date
from espn_client import get_scoreboard, get_summary
from calcular_historial import construir_historial
from generar_analisis import armar_parrafo_partido, pick_mas_seguro

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH=os.path.join(ROOT,"config","ligas.json")
OUTPUT_PATH=os.path.join(ROOT,"datos","picks_hoy.json")
HISTORIAL_N=20

def cargar_ligas():
    with open(CONFIG_PATH,encoding="utf-8") as f: raw=json.load(f)
    return [(slug,nombre) for grupo,ligas in raw.items() if not grupo.startswith("_") for slug,nombre in ligas.items()]

def procesar_partido(slug,nombre,evento):
    event_id=evento.get("id"); comp=evento.get("competitions",[{}])[0]
    cs=comp.get("competitors",[])
    local=next((c for c in cs if c.get("homeAway")=="home"),{})
    visita=next((c for c in cs if c.get("homeAway")=="away"),{})
    lid=local.get("team",{}).get("id"); vid=visita.get("team",{}).get("id")
    ln=local.get("team",{}).get("displayName","Local"); vn=visita.get("team",{}).get("displayName","Visitante")
    if not lid or not vid: return None
    try: summary=get_summary(slug,event_id,permanent=False)
    except Exception as e:
        print(f"[SIN SUMMARY] {ln} vs {vn}: {e}"); return None
    try:
        hl=construir_historial(slug,lid,ln,HISTORIAL_N)
        hv=construir_historial(slug,vid,vn,HISTORIAL_N)
    except Exception as e:
        print(f"[SIN HISTORIAL] {ln} vs {vn}: {e}"); return None
    pick=pick_mas_seguro(hl,hv)
    recs=pick.get("recomendaciones",[])
    # Regla estricta: si no hay recomendaciones reales, el partido NO aparece en la web.
    if not pick.get("disponible") or not recs or min(hl.partidos_evaluados,hv.partidos_evaluados)<5:
        print(f"[DESCARTADO] {ln} vs {vn}: sin predicción válida"); return None
    gi=summary.get("gameInfo",{})
    return {
        "event_id":event_id,"liga_slug":slug,"liga_nombre":nombre,"fecha":evento.get("date"),
        "estado":comp.get("status",{}).get("type",{}).get("description"),
        "local":{"id":lid,"nombre":ln},"visita":{"id":vid,"nombre":vn},
        "venue":gi.get("venue",{}),"cuotas":summary.get("pickcenter",[]),"h2h":summary.get("seasonseries",[]),
        "eventos_clave":summary.get("keyEvents",[]),"historial_local":vars(hl),"historial_visita":vars(hv),
        "pick_mas_seguro":pick,"recomendaciones":recs,"analisis":armar_parrafo_partido(hl,hv),
        "datos_completos":True,
    }

def main():
    fecha=date.today().strftime("%Y%m%d")
    resultado={"generado":datetime.now(timezone.utc).isoformat(),"fecha":fecha,"ligas":[],"top5_dia":[]}
    picks=[]
    for slug,nombre in cargar_ligas():
        try: eventos=get_scoreboard(slug,fecha).get("events",[])
        except Exception as e:
            print(f"[AVISO] {slug}: {e}"); continue
        partidos=[]
        for ev in eventos:
            try:
                p=procesar_partido(slug,nombre,ev)
                if not p: continue
                partidos.append(p); r=p["pick_mas_seguro"]
                picks.append({"liga_nombre":nombre,"liga_slug":slug,"local":p["local"]["nombre"],"visita":p["visita"]["nombre"],"mercado":r["mercado"],"justificacion":r["justificacion"],"confianza":r["confianza"],"score":r["score"],"probabilidad":r["probabilidad"],"n_min":r["n_min"]})
            except Exception as e: print(f"[AVISO] partido {ev.get('id')}: {e}")
        if partidos: resultado["ligas"].append({"slug":slug,"nombre":nombre,"partidos":partidos})
    picks.sort(key=lambda x:x["score"],reverse=True); resultado["top5_dia"]=picks[:5]
    os.makedirs(os.path.dirname(OUTPUT_PATH),exist_ok=True)
    with open(OUTPUT_PATH,"w",encoding="utf-8") as f: json.dump(resultado,f,ensure_ascii=False,indent=2)
    print(f"Listo: {sum(len(x['partidos']) for x in resultado['ligas'])} partidos con predicción válida; {len(picks)} picks.")

if __name__=="__main__": main()
