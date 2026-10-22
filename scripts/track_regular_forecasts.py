"""Run in GitHub Actions; retain the first pre-tip reference and score actual finals."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
from espn_schedule import espn_games_on
from espn_history import espn_final_game_players
from slate_evidence import collect_slate_evidence
from forecast_tracking import capture_forecasts, save_first_forecasts, score_forecasts

if __name__=='__main__':
    now=datetime.now(timezone.utc); day=now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    games=espn_games_on(day)
    history=collect_slate_evidence(day,games,max_games=300)
    records=capture_forecasts(history,games,day,now)
    if records: save_first_forecasts(records,Path('data/forecasts')/(day+'.json'))
    output=Path('data/forecast-results.json');output.parent.mkdir(parents=True,exist_ok=True)
    previous=json.loads(output.read_text()) if output.exists() else {}
    all_results=previous.get('results',[])
    completed=set(previous.get('final_events',[]));finals={}
    def final_loader(eid):
        if eid not in finals: finals[eid]=espn_final_game_players(eid)
        return finals[eid]
    for path in sorted(Path('data/forecasts').glob('*.json')):
        saved=json.loads(path.read_text())
        pending=[r for r in saved if r['event_id'] not in completed]
        all_results.extend(score_forecasts(pending,final_loader))
    completed.update(eid for eid,rows in finals.items() if rows)
    output.write_text(json.dumps({'updated_at':now.isoformat(),'final_events':sorted(completed),'results':all_results},indent=2)+'\n')
    print(f'{len(records)} candidate forecasts; {len(all_results)} scored forecasts. Missing/DNP finals are unscored.')
