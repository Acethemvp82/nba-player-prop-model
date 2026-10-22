"""Run in GitHub Actions; retain the first pre-tip reference and score actual finals."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import os
from market_capture import capture_market_records, append_market_records
from market_validation import grade_records, summarize
from espn_schedule import espn_games_on
from espn_history import espn_final_game_players
from slate_evidence import collect_slate_evidence
from forecast_tracking import capture_forecasts, save_first_forecasts, score_forecasts

if __name__=='__main__':
    now=datetime.now(timezone.utc); day=now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    games=espn_games_on(day)
    history=collect_slate_evidence(day,games,max_games=300)
    games=espn_games_on(day)
    now=datetime.now(timezone.utc)
    records=capture_forecasts(history,games,day,now)
    if records: save_first_forecasts(records,Path('data/forecasts')/(day+'.json'))
    market_path=Path('data/market-ledger.json')
    if os.environ.get('NBA_CAPTURE_QUOTES','').lower()=='true':
        market,failures=capture_market_records(records,games,os.environ.get('ODDS_API_KEY',''))
        print(f'Market capture: {len(market)} records; {len(failures)} source issues')
        if market: append_market_records(market,market_path)
    else: print('Market capture disabled; no provider requests or fabricated odds')
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
    if market_path.exists():
        ledger=json.loads(market_path.read_text())
        market_results_path=Path('data/market-results.json')
        old=json.loads(market_results_path.read_text()) if market_results_path.exists() else {}
        old_final={r['event_id'] for r in old.get('records',[]) if r.get('actual') is not None and r.get('actual_minutes',0)>0}
        # Reuse prior verified actuals rather than re-requesting completed games.
        market_finals={}
        for r in old.get('records',[]):
            if r.get('actual') is None or not r.get('actual_minutes',0)>0: continue
            market_finals.setdefault(r['event_id'],[]).append({'player_id':r['player_id'],'team':r['team'],r['prop']:r['actual'],'minutes':r['actual_minutes'],'is_final':True})
        # Use one combined final row per player to avoid duplicate prop rows.
        combined={}
        for eid,rows in market_finals.items():
            people={}
            for r in rows:
                identity=(r['player_id'],r['team']);people.setdefault(identity,{}).update(r)
            combined[eid]=list(people.values())
        for eid in {r['event_id'] for r in ledger}-old_final:
            try: combined[eid]=final_loader(eid)
            except Exception: pass
        graded,invalid=grade_records(ledger,combined)
        market_results_path.write_text(json.dumps({'updated_at':now.isoformat(),'invalid_records':invalid,'records':graded,'summary':summarize(graded)},indent=2)+'\n')
    print(f'{len(records)} candidate forecasts; {len(all_results)} scored forecasts. Missing/DNP finals are unscored.')
