"""Append-only pre-tip forecasts and final-result comparisons; no betting probabilities."""
from datetime import datetime, timezone
from pathlib import Path
import json
from projection_core import core_projections
from slate_evidence import roster_observations
from projection_core import valid_number
from market_validation import stamp
from role_checks import ROLE_FIELDS


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
        saved.update({k:row.get(k) for k in ('minutes_low','minutes_high','research_readiness')+ROLE_FIELDS})
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
    results=[]; finals={}; seen=set()
    for row in records:
        if not isinstance(row, dict): continue
        eid=row.get('event_id')
        prop=row.get('prop')
        captured,tip=stamp(row.get('captured_at')),stamp(row.get('tipoff'))
        if (not isinstance(eid,str) or not eid.isascii() or not eid.isdigit()
                or prop not in ('points','rebounds','assists','threes')
                or captured is None or tip is None or captured>=tip
                or not valid_number(row.get('baseline'))
                or not valid_number(row.get('reference_last5'))): continue
        key=(eid,row.get('player_id'),prop,row.get('model_version'))
        if key in seen: continue
        seen.add(key)
        if eid not in finals:
            try: finals[eid]=final_loader(eid)
            except Exception: finals[eid]=None
        final=finals[eid]
        if not isinstance(final,list): continue
        matched=[r for r in final if isinstance(r,dict) and r.get('player_id')==row.get('player_id') and r.get('team')==row.get('team')]
        if len(matched)!=1: continue  # DNP/missing is never scored as zero.
        observation=matched[0]
        actual=observation.get(prop)
        minutes=observation.get('minutes')
        if (observation.get('is_final') is not True or not valid_number(minutes)
                or not 0<minutes<=60 or not valid_number(actual)): continue
        # Some loaders include the event identity; reject a mismatched response.
        gid=observation.get('game_id')
        if gid is not None and str(gid) not in (eid,'espn:'+eid): continue
        results.append({**row,'actual':actual,'actual_minutes':minutes,'result_status':'verified_final',
                        'absolute_error':round(abs(row['baseline']-actual),3),
                        'reference_error':round(abs(row['reference_last5']-actual),3)})
    return results


def refresh_forecast_results(records, final_loader, cached_finals=None):
    """Rebuild grades from frozen inputs, reusing only screened final boxscores.

    Legacy aggregate errors lack minutes/finality evidence and are never reused.
    Failed or empty responses remain retryable on the next scheduled run.
    """
    cache = {}
    for eid, rows in (cached_finals or {}).items():
        if (isinstance(rows, list) and rows and all(
                isinstance(r, dict) and r.get('is_final') is True
                and valid_number(r.get('minutes')) and 0 < r['minutes'] <= 60
                and all(valid_number(r.get(p)) for p in ('points','rebounds','assists','threes'))
                for r in rows)):
            cache[eid] = rows

    def load(eid):
        if eid not in cache:
            rows = final_loader(eid)
            if (isinstance(rows, list) and rows and all(
                    isinstance(r, dict) and r.get('is_final') is True
                    and valid_number(r.get('minutes')) and 0 < r['minutes'] <= 60
                    and all(valid_number(r.get(p)) for p in ('points','rebounds','assists','threes'))
                    for r in rows)):
                cache[eid] = rows
            return rows
        return cache[eid]

    return score_forecasts(records, load), cache
