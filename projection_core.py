"""Minutes-first research projections from strictly earlier verified player-games."""
from collections import defaultdict
from math import isfinite
from statistics import median
from historical_stats import _day, _valid_game_id

PROPS = ('points','rebounds','assists','threes')


def valid_number(value, minimum=0):
    return type(value) in (int,float) and isfinite(value) and value >= minimum


def clean_games(observations, as_of):
    cutoff = _day(as_of)
    if cutoff is None: raise ValueError('Invalid slate date')
    unique, conflicts = {}, set()
    for row in observations:
        if not isinstance(row,dict) or row.get('is_final') is not True: continue
        day = _day(row.get('game_date'))
        minutes = row.get('minutes')
        if (day is None or day >= cutoff or not _valid_game_id(row.get('game_id'))
            or row.get('player_id') is None or not row.get('team')
            or not valid_number(minutes) or not 0 < minutes <= 60): continue
        key=(str(row['player_id']),str(row['game_id']))
        previous=unique.get(key)
        fields=('game_date','team','opponent','minutes','position')+PROPS
        if previous and any(previous.get(k) != row.get(k) for k in fields): conflicts.add(key)
        else: unique.setdefault(key,row)
    return [r for k,r in unique.items() if k not in conflicts]


def core_projections(observations, slate_date, min_games=5):
    if type(min_games) is not int or min_games < 1: raise ValueError('Invalid minimum sample')
    cutoff=_day(slate_date)
    grouped=defaultdict(list)
    for row in clean_games(observations,slate_date): grouped[str(row['player_id'])].append(row)
    output=[]
    for pid,games in grouped.items():
        games.sort(key=lambda r:(_day(r['game_date']),str(r['game_id'])),reverse=True)
        latest=games[0]
        # Do not forecast a new team using a former team's role/minutes.
        recent=[r for r in games if r['team']==latest['team']][:10]
        if len(recent)<min_games: continue
        minutes=min(48.0,float(median(r['minutes'] for r in recent[:5])))
        age=(cutoff-_day(latest['game_date'])).days
        for prop in PROPS:
            sample=[(i,r) for i,r in enumerate(recent) if valid_number(r.get(prop))]
            if len(sample)<min_games: continue
            weighted_stat=sum((0.85**i)*r[prop] for i,r in sample)
            weighted_minutes=sum((0.85**i)*r['minutes'] for i,r in sample)
            rate=weighted_stat/weighted_minutes
            output.append({'player_id':pid,'player':latest.get('player'),'team':latest['team'],
                'prop':prop,'baseline':round(minutes*rate,2),'sample_games':len(sample),
                'recent_minutes':round(sum(r['minutes'] for r in recent[:5])/len(recent[:5]),2),
                'forecast_minutes':round(minutes,2),'rate_per_minute':round(rate,5),
                'last_game_date':_day(latest['game_date']).isoformat(),'days_since_last_game':age,
                'slate_date':cutoff.isoformat(),'research_readiness':'stale_history' if age>14 else 'limited_sample' if len(sample)<10 else 'history_ready',
                'method':'median last-5 minutes x recency-weighted per-minute production',
                'projection_status':'minutes_rate_research','over_probability':None,'sportsbook_line':None,'bet_tier':None})
    return output
