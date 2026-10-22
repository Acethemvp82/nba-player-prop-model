"""Append-only pre-tip forecasts and final-result comparisons; no betting probabilities."""
from datetime import datetime, timezone
from pathlib import Path
import json
from projection_core import core_projections
from slate_evidence import roster_observations


def capture_forecasts(history, games, day, now=None):
    now=now or datetime.now(timezone.utc)
    upcoming={}
    for game in games:
        try: tip=datetime.fromisoformat(game['gameTimeUTC'].replace('Z','+00:00'))
        except (KeyError,ValueError,TypeError,AttributeError): continue
        if tip.tzinfo is None or now>=tip or game.get('espnCompleted') is not False: continue
        if str(game.get('gameStatusText','')).casefold() not in ('scheduled','pre'): continue
        for side in ('homeTeam','awayTeam'): upcoming[game[side]['teamTricode']]=game
    records=[]
    if not history.get('roster_checked'): return records
    for row in core_projections(roster_observations(history),day):
        game=upcoming.get(row['team'])
        if not game: continue
        saved={k:row[k] for k in ('player_id','player','team','prop','baseline','reference_last5','evidence','source_season','slate_date','sample_games','forecast_minutes','current_season_games')}
        saved.update({k:row.get(k) for k in ('minutes_low','minutes_high','research_readiness')})
        records.append({**saved,'event_id':game['espnEventId'],'tipoff':game['gameTimeUTC'],
                        'captured_at':now.isoformat(),'model_version':'regular-roster-v2'})
    return records


def save_first_forecasts(records, path):
    path=Path(path); existing=json.loads(path.read_text()) if path.exists() else []
    keys={(r['event_id'],r['player_id'],r['prop']) for r in existing}
    for r in records:
        key=(r['event_id'],r['player_id'],r['prop'])
        if key not in keys: existing.append(r);keys.add(key)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(existing,indent=2,allow_nan=False)+'\n')
    return existing


def score_forecasts(records, final_loader):
    results=[]; finals={}
    for row in records:
        eid=row['event_id']
        if eid not in finals:
            try: finals[eid]=final_loader(eid)
            except Exception: finals[eid]=None
        final=finals[eid]
        if final is None: continue
        matched=[r for r in final if r.get('player_id')==row['player_id'] and r.get('team')==row['team']]
        if len(matched)!=1: continue  # DNP/missing is never scored as zero.
        actual=matched[0].get(row['prop'])
        if type(actual) not in (int,float): continue
        if datetime.fromisoformat(row['captured_at'])>=datetime.fromisoformat(row['tipoff'].replace('Z','+00:00')): continue
        results.append({**row,'actual':actual,'absolute_error':round(abs(row['baseline']-actual),3),
                        'reference_error':round(abs(row['reference_last5']-actual),3)})
    return results
