"""One-player-per-row research board; no invented positional defense ranks."""
from player_research import player_games
from historical_stats import player_history_summaries
from position_defense import position_group

STATS = {'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM','steals':'Steals','blocks':'Blocks'}
POSITIONS = {'PG','SG','SF','PF','C','G','F','G-F','F-C'}


def build_matchup_board(observations, forecasts, opponents, slate_date, prop='points', context=None):
    if prop not in ('points','rebounds','assists','threes'): raise ValueError('Invalid selected prop')
    context = context or {}
    summaries = player_history_summaries(observations, as_of=slate_date)
    players = {str(s['player_id']):s for s in summaries if s.get('team') in opponents}
    predictions = {}
    for row in forecasts:
        if row.get('team') not in opponents: continue
        pid = str(row['player_id'])
        players.setdefault(pid, {'player_id':pid,'player':row.get('player'),'team':row['team']})
        predictions[pid,row['prop']] = row
    output = []
    for pid, player in players.items():
        team = player['team']
        opponent = opponents[team]
        sample = player_games(observations,pid,prop,slate_date,limit=10000)
        recent = sample[:10]
        h2h = [r for r in sample if r.get('Opponent') == opponent]
        selected = predictions.get((pid,prop),{})
        any_forecast = next((r for (p,_),r in predictions.items() if p == pid),{})
        latest_gid = sample[0]['Game ID'] if sample else None
        positions = {r.get('position') for r in observations if isinstance(r,dict)
                     and str(r.get('player_id')) == pid and str(r.get('game_id')) == latest_gid
                     and r.get('position') in POSITIONS}
        def avg(rows): return round(sum(r['Result'] for r in rows)/len(rows),1) if rows else None
        pos=next(iter(positions)) if len(positions)==1 else '—'
        group=position_group(pos)
        ctx = context.get((opponent,group,prop),{})
        record = {'player_id':pid,'Team':team,'Pos':pos,'Group':group or 'Unknown',
                  'Player':player.get('player'),'Opponent':opponent,
                  'Line':None,'L10':avg(recent),'L5':avg(recent[:5]),'H2H':avg(h2h),
                  'H2H N':len(h2h),'Projection':selected.get('baseline'),
                  'Matchup':ctx.get('allowed'), 'Def Rank':ctx.get('rank'),
                  'Rank Teams':ctx.get('ranked_teams',0), 'Defense Games':ctx.get('games',0),
                  'Model Min':selected.get('forecast_minutes'), 'Recent Min':selected.get('recent_minutes'),
                  'Sample':selected.get('sample_games',len(sample)),
                  'Status':any_forecast.get('availability','Unknown — no current report'),
                  'Evidence':selected.get('evidence','Insufficient history'),
                  'Current GP':selected.get('current_season_games',0),
                  'Minutes note':selected.get('minutes_note','Role unconfirmed'),
                  'Role status':selected.get('role_status','insufficient_current_role'),
                  'Role note':selected.get('role_note','Current role unconfirmed'),
                  'Current Min':selected.get('role_recent_minutes'),
                  'Minutes low':selected.get('minutes_low'), 'Minutes high':selected.get('minutes_high'),
                  'Readiness':selected.get('research_readiness','below_minimum')}
        for key,label in STATS.items():
            defense=context.get((opponent,group,key),{})
            record[label]=defense.get('allowed')
            record['varies_'+label]=defense.get('varies',False)
            record['rank_'+label]=defense.get('rank')
            record['teams_'+label]=defense.get('ranked_teams',0)
            record['score_'+label]=None
        output.append(record)
    return sorted(output,key=lambda r:(r['Team'],r['Player'] or '',r['player_id']))
