"""One-player-per-row research board; no invented positional defense ranks."""
from player_research import player_games
from historical_stats import player_history_summaries

STATS = {'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM'}
POSITIONS = {'PG','SG','SF','PF','C','G','F','G-F','F-C'}


def build_matchup_board(observations, forecasts, opponents, slate_date, prop='points', context=None):
    if prop not in STATS: raise ValueError('Invalid selected prop')
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
        ctx = context.get((opponent,prop),{})
        record = {'player_id':pid,'Team':team,'Pos':next(iter(positions)) if len(positions)==1 else '—',
                  'Player':player.get('player'),'Opponent':opponent,
                  'Line':None,'L10':avg(recent),'L5':avg(recent[:5]),'H2H':avg(h2h),
                  'H2H N':len(h2h),'Projection':selected.get('baseline'),
                  'Matchup':selected.get('matchup_score',ctx.get('matchup_score')),
                  'Sample':selected.get('sample_games',len(sample)),
                  'Status':any_forecast.get('availability','Unknown — no current report'),
                  'Readiness':selected.get('research_readiness','below_minimum')}
        for key,label in STATS.items():
            forecast = predictions.get((pid,key),{})
            record[label] = forecast.get('baseline')
            record['score_' + label] = forecast.get('matchup_score',context.get((opponent,key),{}).get('matchup_score'))
        output.append(record)
    return sorted(output,key=lambda r:(r['Team'],r['Player'] or '',r['player_id']))
