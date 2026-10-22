"""Observed allowance by explicit source position groups; never inferred PG/SG."""
from collections import defaultdict
from projection_core import clean_games, valid_number

METRICS=('points','rebounds','assists','threes','steals','blocks')
GROUPS={'G':'G','PG':'G','SG':'G','F':'F','SF':'F','PF':'F','C':'C'}


def position_group(position):
    return GROUPS.get(position)


def positional_allowance(observations, as_of, min_games=5, min_players=8, min_teams=3):
    """Per-game totals allowed to ALL players of a group, not individual matchups.

    Games lacking full position coverage among observed players are omitted.
    Rankings use only qualified teams in the retrieved sample. Higher allowance
    gets rank 1. Ties share the best applicable rank. No neutral score is invented.
    """
    if any(type(v) is not int or v<1 for v in (min_games,min_players,min_teams)):
        raise ValueError('Invalid positional coverage threshold')
    raw=clean_games(observations,as_of)
    # Reject an offense/game if duplicate conflicts removed any of its players.
    conflicted_groups=set()
    seen={}
    for r in observations:
        if not clean_games([r],as_of): continue
        k=(str(r.get('player_id')),str(r.get('game_id')))
        if k in seen and any(seen[k].get(f)!=r.get(f) for f in ('team','opponent','minutes','position')+METRICS):
            conflicted_groups.add((str(r.get('game_id')),r.get('team')))
            conflicted_groups.add((str(r.get('game_id')),seen[k].get('team')))
        seen.setdefault(k,r)
    games=defaultdict(list)
    for r in raw:
        if r.get('opponent') and r['opponent']!=r['team']:
            games[(str(r['game_id']),r['team'],r['opponent'])].append(r)
    samples=defaultdict(list)
    for (gid,team,opp),players in games.items():
        if (gid,team) in conflicted_groups or len(players)<min_players: continue
        if any(position_group(r.get('position')) is None for r in players): continue
        for group in ('G','F','C'):
            subset=[r for r in players if position_group(r.get('position'))==group]
            for prop in METRICS:
                if all(valid_number(r.get(prop)) for r in subset):
                    samples[opp,group,prop].append(sum(r[prop] for r in subset))
    output={}
    for (opp,group,prop),values in samples.items():
        if len(values)>=min_games:
            output[opp,group,prop]={'allowed':round(sum(values)/len(values),2),
                                   'games':len(values),'rank':None,'ranked_teams':0,'varies':False}
    for group in ('G','F','C'):
        for prop in METRICS:
            cohort=[v for (o,g,p),v in output.items() if g==group and p==prop]
            if len(cohort)<min_teams: continue
            for value in cohort:
                value['rank']=1+sum(other['allowed']>value['allowed'] for other in cohort)
                value['ranked_teams']=len(cohort)
                value['varies']=len({v['allowed'] for v in cohort})>1
    return output
