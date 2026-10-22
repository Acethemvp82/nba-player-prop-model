"""Frozen prospective paper records and fixed-stake grading, not proof of an edge."""
from datetime import datetime, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo
from math import isfinite
import json
from prop_signal import prop_signal

POLICY='line-gap-v1'


def stamp(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError,AttributeError): return None


def number(value):
    return type(value) in (int,float) and isfinite(value) and value>=0


def valid_odds(value):
    return type(value) in (int,float) and isfinite(value) and int(value)==value and (value<=-100 or value>=100)


def direction(estimate,line):
    return 'over' if estimate>line else 'under' if estimate<line else 'pass'


def make_market_record(forecast,game,line,over_odds,under_odds,source,now=None,quote_updated=None):
    now=now or datetime.now(timezone.utc)
    tip=stamp(game.get('gameTimeUTC'))
    if now.tzinfo is None or tip is None or now>=tip: raise ValueError('Only pre-tip entries can be frozen')
    if game.get('espnCompleted') is not False or str(game.get('gameStatusText','')).casefold() not in ('scheduled','pre'):
        raise ValueError('Game must still be scheduled')
    if source not in ('manual_unverified','provider_fanduel'): raise ValueError('Unknown quote source')
    if forecast.get('slate_date')!=tip.astimezone(ZoneInfo('America/New_York')).date().isoformat():
        raise ValueError('Forecast date does not match scheduled game')
    if forecast.get('team') not in [game.get(s,{}).get('teamTricode') for s in ('homeTeam','awayTeam')]:
        raise ValueError('Player team does not match scheduled game')
    if not str(game.get('espnEventId','')).isascii() or not str(game.get('espnEventId','')).isdigit(): raise ValueError('Invalid event ID')
    if forecast.get('prop') not in ('points','rebounds','assists','threes') or not str(forecast.get('player_id','')).startswith('espn:'):
        raise ValueError('Invalid forecast identity')
    if not all(number(v) for v in (line,forecast.get('baseline'),forecast.get('reference_last5'))): raise ValueError('Invalid estimate or line')
    if line*2!=int(line*2): raise ValueError('Use whole or half-unit lines')
    if not all(valid_odds(o) for o in (over_odds,under_odds)): raise ValueError('Enter valid American prices for both sides')
    q=stamp(quote_updated) if source=='provider_fanduel' else now
    if q is None or not -120<=(now-q).total_seconds()<=1800 or q>=tip: raise ValueError('Quote is stale, future-dated or after tip')
    label,_,reason=prop_signal({'Projection':forecast['baseline'],'Line':line,'Evidence':forecast.get('evidence'),
        'Sample':forecast.get('sample_games'),'Minutes low':forecast.get('minutes_low'),'Minutes high':forecast.get('minutes_high'),
        'Readiness':forecast.get('research_readiness'),'Status':forecast.get('availability','Unknown')})
    eligible=label in ('Above line','Below line','At line')
    row={k:forecast.get(k) for k in ('player_id','player','team','prop','baseline','reference_last5','evidence','slate_date','sample_games','forecast_minutes')}
    row.update(event_id=str(game['espnEventId']),tipoff=tip.isoformat(),captured_at=now.isoformat(),quote_updated=q.isoformat(),
        line=float(line),over_odds=int(over_odds),under_odds=int(under_odds),source=source,
        model_version='regular-roster-v2',policy_version=POLICY,eligible=eligible,signal=label,signal_reason=reason,
        model_side=direction(forecast['baseline'],line) if eligible else 'pass',
        reference_side=direction(forecast['reference_last5'],line) if eligible else 'pass',stake_units=1)
    row['record_id']=record_id(row)
    return row


def record_id(row):
    return sha256(json.dumps({k:v for k,v in row.items() if k!='record_id'},sort_keys=True,allow_nan=False).encode()).hexdigest()


def validate_record(row):
    try:
        if row['record_id']!=record_id(row) or row['policy_version']!=POLICY: return False
        captured,tip,q=(stamp(row[k]) for k in ('captured_at','tipoff','quote_updated'))
        if None in (captured,tip,q) or not captured<tip or not q<tip or not -120<=(captured-q).total_seconds()<=1800: return False
        if not all(number(row[k]) for k in ('baseline','reference_last5','line')) or row['line']*2!=int(row['line']*2): return False
        if not all(valid_odds(row[k]) for k in ('over_odds','under_odds')): return False
        if row['source'] not in ('manual_unverified','provider_fanduel') or row['stake_units']!=1 or type(row['eligible']) is not bool: return False
        if row['prop'] not in ('points','rebounds','assists','threes') or not str(row['event_id']).isdigit(): return False
        if row['eligible'] and row['signal'] not in ('Above line','Below line','At line'): return False
        for key,estimate in (('model_side','baseline'),('reference_side','reference_last5')):
            if row[key]!=(direction(row[estimate],row['line']) if row['eligible'] else 'pass'): return False
        return True
    except (KeyError,ValueError,TypeError,OverflowError): return False


def deduplicate(records):
    """One earliest captured entry per source/game/player/prop/policy. Reject conflicts."""
    unique={};conflicts=set();invalid=0
    for row in records:
        if not isinstance(row,dict) or not validate_record(row): invalid+=1;continue
        key=tuple(row[k] for k in ('source','event_id','player_id','prop','model_version','policy_version'))
        prior=unique.get(key)
        if prior and stamp(row['captured_at'])==stamp(prior['captured_at']) and row['record_id']!=prior['record_id']: conflicts.add(key)
        elif not prior or stamp(row['captured_at'])<stamp(prior['captured_at']): unique[key]=row
    return [r for k,r in unique.items() if k not in conflicts],invalid+len(conflicts)


def settle(actual,line,side,odds):
    if side=='pass': return 'pass',0.
    if actual==line: return 'push',0.
    won=(actual>line) if side=='over' else actual<line
    return ('win',round(odds/100 if odds>0 else 100/abs(odds),6)) if won else ('loss',-1.)


def grade_records(records,finals):
    """Finals are verified observations keyed by event. Absent players stay unresolved."""
    clean,invalid=deduplicate(records);graded=[]
    for row in clean:
        matches=[r for r in finals.get(row['event_id'],[]) if r.get('player_id')==row['player_id'] and r.get('team')==row['team'] and r.get('is_final') is True]
        actual=matches[0].get(row['prop']) if len(matches)==1 and number(matches[0].get('minutes')) and matches[0]['minutes']>0 else None
        result={**row,'actual':actual if number(actual) else None,
                'actual_minutes':matches[0]['minutes'] if number(actual) else None}
        for method in ('model','reference'):
            side=row[method+'_side']
            odds=row['over_odds'] if side=='over' else row['under_odds']
            outcome,units=settle(actual,row['line'],side,odds) if number(actual) else ('pass',0.) if side=='pass' else ('unresolved',None)
            result.update({method+'_outcome':outcome,method+'_units':units})
        graded.append(result)
    return graded,invalid


def summarize(graded):
    groups={}
    for row in graded:
        key=tuple(row[k] for k in ('source','model_version','policy_version','evidence','prop'))
        groups.setdefault(key,[]).append(row)
    output=[]
    for key,rows in groups.items():
        group=dict(zip(('Source','Model version','Policy','Evidence','Prop'),key))
        group.update(Entries=len(rows),Games=len({r['event_id'] for r in rows}),Dates=len({r['slate_date'] for r in rows}),Unresolved=sum(r['model_outcome']=='unresolved' for r in rows))
        for method in ('model','reference'):
            resolved=[r for r in rows if r[method+'_outcome'] in ('win','loss','push')]
            net=sum(r[method+'_units'] for r in resolved)
            wins=sum(r[method+'_outcome']=='win' for r in rows);losses=sum(r[method+'_outcome']=='loss' for r in rows)
            group[method+' win %']=round(100*wins/(wins+losses),2) if wins+losses else None
            group.update({method+' bets':len(resolved),method+' wins':sum(r[method+'_outcome']=='win' for r in rows),
                method+' losses':sum(r[method+'_outcome']=='loss' for r in rows),method+' pushes':sum(r[method+'_outcome']=='push' for r in rows),
                method+' net units':round(net,3),method+' ROI %':round(100*net/len(resolved),2) if resolved else None})
        output.append(group)
    return output
