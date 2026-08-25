"""Genera simulaciones para los partidos publicados en picks_hoy.json."""
import json
from pathlib import Path
from src.collector import FootballDataCollector
from src.model import MatchModel
from src.simulator import MonteCarloSimulator

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"datos"/"picks_hoy.json"
OUTPUT=ROOT/"datos"/"simulaciones_hoy.json"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)
    raw=json.loads(INPUT.read_text(encoding="utf-8"))
    collector=FootballDataCollector(); output={"generated_at":None,"matches":[]}
    for league in raw.get("ligas",[]):
        competition=league.get("slug") or league.get("codigo")
        for match in league.get("partidos",[]):
            home=match.get("local") or match.get("home") or {}
            away=match.get("visita") or match.get("away") or {}
            home_name=home.get("nombre") if isinstance(home,dict) else home
            away_name=away.get("nombre") if isinstance(away,dict) else away
            if not home_name or not away_name or competition not in __import__('config').COMPETITIONS: continue
            try:
                hd=collector.collect(home_name,competition,True); ad=collector.collect(away_name,competition,False)
                result=MonteCarloSimulator(MatchModel(hd,ad)).run(10000).to_dict()
                output["matches"].append({"league":league.get("nombre"),"competition":competition,"home":home_name,"away":away_name,"data":result})
            except Exception as exc:
                print(f"SKIP {home_name} vs {away_name}: {exc}")
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Generadas {len(output['matches'])} simulaciones.")

if __name__=="__main__": main()
