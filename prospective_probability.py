"""Experimental residual estimates and prospective scoring; never a proven badge."""
from collections import defaultdict
from datetime import date, timedelta
from math import floor, isfinite
from pathlib import Path
from zoneinfo import ZoneInfo
import json
from live_sources import utc

VERSION='empirical-residual-v1'
MIN_SAMPLES=100
MIN_GAMES=20
MIN_DATES=10
MIN_PLAYERS=20


def numeric(value):
    return type(value) in (int,float) and isfinite(value) and value>=0


def load_forecast_archive():
    try:
        value=json.loads((Path(__file__).resolve().parent/'data/forecast-results.json').read_text())
        return value if isinstance(value,dict) and value.get('grading_version')==2 else {}
    except (OSError,ValueError): return {}


def estimate_probability(forecast,line,archive):
    """Same-prop/current-season frozen residuals, strictly before this slate.

    Resampled counts are rounded to nonnegative integers. Laplace smoothing
    assigns one observation to each possible outcome (two on half lines, three
    on whole lines). This distribution assumption requires future calibration.
    """
    empty={'version':VERSION,'status':'insufficient_history','samples':0,'games':0,'dates':0,'players':0}
    if forecast.get('evidence')!='Current season': return empty | {'status':'current_season_required'}
    try: day=date.fromisoformat(forecast['slate_date'])
    except (KeyError,TypeError,ValueError):return empty | {'status':'invalid_forecast'}
    if (not numeric(line) or not numeric(forecast.get('baseline')) or not isinstance(archive,dict)
            or archive.get('grading_version')!=2 or not isinstance(archive.get('results'),list)): return empty
    season=day.year+(day.month>=7)
    unique={};conflicts=set()
    for r in archive.get('results',[]):
        if not isinstance(r,dict):continue
        tip,captured=utc(r.get('tipoff')),utc(r.get('captured_at'))
        try: result_day=date.fromisoformat(r['slate_date'])
        except (KeyError,TypeError,ValueError): continue
        if (r.get('evidence')!='Current season' or r.get('source_season')!=season
                or r.get('prop')!=forecast.get('prop') or r.get('model_version')!='regular-roster-v2'
                or r.get('result_status')!='verified_final' or r.get('role_status')!='stable'
                or not numeric(r.get('sample_games')) or r['sample_games']<10
                or not numeric(r.get('minutes_low')) or not numeric(r.get('minutes_high'))
                or not 0<=r['minutes_high']-r['minutes_low']<=12
                or r.get('research_readiness')=='stale_history'
                or not tip or not captured or captured>=tip
                or tip.astimezone(ZoneInfo('America/New_York')).date()!=result_day
                or not day-timedelta(days=90)<=result_day<day
                or not numeric(r.get('actual_minutes')) or not 0<r['actual_minutes']<=60
                or not numeric(r.get('actual')) or not numeric(r.get('baseline'))
                or not r.get('event_id') or not r.get('player_id')):continue
        key=(r['event_id'],r['player_id'],r['prop'])
        if key in unique and unique[key]!=r:conflicts.add(key)
        else:unique.setdefault(key,r)
    rows=[r for k,r in unique.items() if k not in conflicts]
    result=empty | {'samples':len(rows),'games':len({r['event_id'] for r in rows}),
        'dates':len({r['slate_date'] for r in rows}),'players':len({r['player_id'] for r in rows})}
    if (result['samples']<MIN_SAMPLES or result['games']<MIN_GAMES
            or result['dates']<MIN_DATES or result['players']<MIN_PLAYERS):return result
    counts={'over':1,'under':1,'push':1 if line==int(line) else 0}
    for r in rows:
        simulated=max(0,floor(forecast['baseline']+r['actual']-r['baseline']+.5))
        counts['over' if simulated>line else 'under' if simulated<line else 'push']+=1
    total=sum(counts.values())
    return result | {'status':'experimental','over':counts['over']/total,'under':counts['under']/total,
        'push':counts['push']/total,'last_training_date':max(r['slate_date'] for r in rows)}


def valid_evidence(evidence,slate_date):
    if not isinstance(evidence,dict) or evidence.get('version')!=VERSION:return False
    if evidence.get('status')!='experimental':
        return evidence.get('status') in ('insufficient_history','current_season_required','invalid_forecast','forecast_ineligible') and not any(k in evidence for k in ('over','under','push'))
    values=[evidence.get(k) for k in ('over','under','push')]
    try:
        return (all(numeric(v) and v<=1 for v in values) and abs(sum(values)-1)<1e-9
            and all(type(evidence.get(k)) is int and evidence[k]>=minimum for k,minimum in
                (('samples',MIN_SAMPLES),('games',MIN_GAMES),('dates',MIN_DATES),('players',MIN_PLAYERS)))
            and date.fromisoformat(evidence['last_training_date'])<date.fromisoformat(slate_date))
    except (KeyError,TypeError,ValueError):return False


def score_probability_records(graded):
    """Conditional-over Brier score on future, resolved non-push market outcomes.

    Normalize by P(over)+P(under) because pushes are excluded from binary scoring.
    Grouping preserves quote source, evidence, model, policy and method version.
    """
    from market_validation import validate_record
    groups=defaultdict(list);seen=set()
    for r in graded:
        e=r.get('probability_evidence',{})
        frozen={k:v for k,v in r.items() if k not in ('actual','actual_minutes','model_outcome','model_units','reference_outcome','reference_units')}
        if (not validate_record(frozen) or not valid_evidence(e,r['slate_date'])
                or e.get('status')!='experimental' or not numeric(r.get('actual'))
                or not numeric(r.get('actual_minutes')) or not 0<r['actual_minutes']<=60
                or r['actual']==r['line']):continue
        if r['record_id'] in seen:continue
        seen.add(r['record_id'])
        denominator=e['over']+e['under']
        if denominator<=0:continue
        key=tuple(r[k] for k in ('source','evidence','model_version','policy_version','prop'))+(e['version'],)
        groups[key].append((r,e['over']/denominator,int(r['actual']>r['line'])))
    output=[]
    for key,rows in groups.items():
        n=len(rows)
        output.append(dict(zip(('Source','Evidence','Model','Policy','Prop','Probability method'),key)) | {
            'Scored':n,'Games':len({r['event_id'] for r,_,_ in rows}),
            'Dates':len({r['slate_date'] for r,_,_ in rows}),
            'Brier score':round(sum((p-y)**2 for _,p,y in rows)/n,4),
            'Mean predicted Over':round(sum(p for _,p,_ in rows)/n,4),
            'Observed Over':round(sum(y for _,_,y in rows)/n,4),'Status':'Experimental; not validated'})
    return output
