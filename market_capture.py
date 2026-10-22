"""Explicitly enabled quote collection; disabled unless a provider key and opt-in exist."""
from datetime import datetime,timezone
from pathlib import Path
import json
from live_sources import fetch_event_odds,select_quote,fetch_injuries,reported_status
from market_validation import make_market_record,deduplicate


def capture_market_records(forecasts,games,key,now=None):
    clock=lambda:now if now is not None else datetime.now(timezone.utc)
    records=[];failures=[]
    if not key: return [],['Provider key absent; no market records created']
    try: injury=fetch_injuries()
    except ValueError: injury=None
    for game in games:
        home=game['homeTeam']['teamTricode'];away=game['awayTeam']['teamTricode']
        candidates=[r for r in forecasts if r['event_id']==game.get('espnEventId')]
        if not candidates: continue
        try: payload=fetch_event_odds(key,home,away,candidates[0]['slate_date'],clock())
        except ValueError as exc: failures.append(str(exc));continue
        for r in candidates:
            observed_at=clock()
            over=select_quote(payload,r['player'],r['prop'],observed_at,'Over')
            under=select_quote(payload,r['player'],r['prop'],observed_at,'Under')
            if not over or not under or over['line']!=under['line']: continue
            status=reported_status(injury,r['player'],r['team'],observed_at) if injury else 'Report stale / unavailable'
            forecast={**r,'availability':status}
            try:
                records.append(make_market_record(forecast,game,over['line'],over['odds'],under['odds'],
                    'provider_fanduel',observed_at, min(over['updated_at'],under['updated_at'])))
            except ValueError as exc: failures.append(str(exc))
    return records,failures


def append_market_records(records,path):
    path=Path(path);existing=json.loads(path.read_text()) if path.exists() else []
    # Published first records cannot be replaced by later quotes or a modified rerun.
    keys={tuple(r[k] for k in ('source','event_id','player_id','prop','model_version','policy_version')) for r in existing}
    for r in records:
        key=tuple(r[k] for k in ('source','event_id','player_id','prop','model_version','policy_version'))
        if key not in keys:existing.append(r);keys.add(key)
    clean,invalid=deduplicate(existing)
    if invalid: raise ValueError('Invalid/conflicting records in published market ledger')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean,indent=2,allow_nan=False)+'\n')
    return clean
