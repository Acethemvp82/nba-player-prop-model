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
from forecast_tracking import capture_forecasts, save_first_forecasts, refresh_forecast_results

if __name__=='__main__':
    now=datetime.now(timezone.utc); day=now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    games=espn_games_on(day)
    history=collect_slate_evidence(day,games,max_games=300)
    games=espn_games_on(day)
    now=datetime.now(timezone.utc)
    schedule_path=Path('data/schedules')/(day+'.json');schedule_path.parent.mkdir(parents=True,exist_ok=True)
    schedule_path.write_text(json.dumps({'day':day,'retrieved_at':now.isoformat(),'games':games},indent=2,allow_nan=False)+'\n')
    records=capture_forecasts(history,games,day,now)
    if records: save_first_forecasts(records,Path('data/forecasts')/(day+'.json'))
    market_path=Path('data/market-ledger.json')
    if os.environ.get('NBA_CAPTURE_QUOTES','').lower()=='true':
        market,failures=capture_market_records(records,games,os.environ.get('ODDS_API_KEY',''))
        print(f'Market capture: {len(market)} records; {len(failures)} source issues')
        if market: append_market_records(market,market_path)
    else: print('Market capture disabled; no provider requests or fabricated odds')
    output=Path('data/forecast-results.json');output.parent.mkdir(parents=True,exist_ok=True)
    cache_path=Path('data/final-observations.json')
    cached=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    saved=[]
    for path in sorted(Path('data/forecasts').glob('*.json')):
        saved.extend(json.loads(path.read_text()))
    all_results,finals=refresh_forecast_results(saved,espn_final_game_players,cached)
    cache_path.write_text(json.dumps(finals,indent=2,allow_nan=False)+'\n')
    output.write_text(json.dumps({'grading_version':2,'updated_at':now.isoformat(),
        'final_events':sorted(finals),'frozen_forecasts':len(saved),'results':all_results},indent=2,allow_nan=False)+'\n')
    def final_loader(eid):
        if eid not in finals: finals[eid]=espn_final_game_players(eid)
        return finals[eid]
    if market_path.exists():
        ledger=json.loads(market_path.read_text())
        market_results_path=Path('data/market-results.json')
        combined={}
        for eid in {r['event_id'] for r in ledger}:
            try: combined[eid]=final_loader(eid)
            except Exception: pass
        graded,invalid=grade_records(ledger,combined)
        market_results_path.write_text(json.dumps({'updated_at':now.isoformat(),'invalid_records':invalid,'records':graded,'summary':summarize(graded)},indent=2)+'\n')
    print(f'{len(records)} candidate forecasts; {len(all_results)} scored forecasts. Missing/DNP finals are unscored.')
