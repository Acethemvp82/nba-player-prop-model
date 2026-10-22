"""Bounded regular-season evidence and current roster identities for a slate."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from espn_schedule import ESPN_TO_NBA
from espn_players import espn_team_roster
from espn_history import collect_espn_history, espn_final_game_players

ET=ZoneInfo('America/New_York')


def team_events(team_id, season):
    response=requests.get(f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule',
                          params={'season':season,'seasontype':2},timeout=15)
    response.raise_for_status()
    payload=response.json()
    if not isinstance(payload,dict) or not isinstance(payload.get('events'),list):
        raise ValueError('Team schedule unavailable')
    return payload['events']


def regular_event(event, as_of, expected_team, season):
    """Reject unknown season types, unfinished games and unrelated matchups."""
    try:
        if event['seasonType']['type'] != 2 or event['season']['year'] != season: return None
        c=event['competitions'][0]
        if c['status']['type']['completed'] is not True: return None
        day=datetime.fromisoformat(event['date'].replace('Z','+00:00')).astimezone(ET).date()
        if day.isoformat() >= as_of: return None
        sides={}
        for item in c['competitors']:
            code=item['team']['abbreviation'].upper()
            sides[item['homeAway']]={'teamTricode':ESPN_TO_NBA.get(code,code)}
        codes=[r['teamTricode'] for r in sides.values()]
        eid=str(event['id'])
        if len(codes)!=2 or len(set(codes))!=2 or expected_team not in codes or not eid.isascii() or not eid.isdigit(): return None
        return {'espnEventId':eid,'espnCompleted':True,'homeTeam':sides['home'],'awayTeam':sides['away'],
                'game_date':day.isoformat(),'season_year':season,'season_type':'regular'}
    except (KeyError,TypeError,ValueError,IndexError,AttributeError): return None


def collect_slate_evidence(as_of, games, max_games=100, schedule_loader=team_events,
                           roster_loader=espn_team_roster, boxscore_loader=espn_final_game_players):
    year=datetime.fromisoformat(as_of).year+(datetime.fromisoformat(as_of).month>=7)
    # ESPN's side keys are home/away.
    ids={g[side+'Team']['teamTricode']:g.get('espnTeamIds',{}).get(side)
         for g in games for side in ('home','away')}
    failures=[]; rosters=[]; selected={}
    limit=min(15,max(1,max_games//max(1,len(ids))))
    for team,tid in sorted(ids.items()):
        if not tid:
            failures.append({'team':team,'error':'Missing current roster identity'});continue
        try: rosters.extend(roster_loader(tid,team))
        except Exception as exc: failures.append({'team':team,'error':f'Roster unavailable: {exc}'})
        events=[]
        for season in (year,year-1):
            try:
                events.extend(r for e in schedule_loader(tid,season)
                              if (r:=regular_event(e,as_of,team,season)))
            except Exception as exc: failures.append({'team':team,'season':season,'error':f'Schedule unavailable: {exc}'})
        for e in sorted(events,key=lambda e:(e['game_date'],e['espnEventId']),reverse=True)[:limit]:
            selected[e['espnEventId']]=e
    def collect(e):
        cutoff=(datetime.fromisoformat(e['game_date'])+timedelta(days=1)).date().isoformat()
        result=collect_espn_history(cutoff,days=1,max_games=1,schedule_loader=lambda _: [e],boxscore_loader=boxscore_loader)
        for row in result['observations']: row.update(season_type='regular',season_year=e['season_year'])
        return result
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(collect,selected.values()))
    observations=[r for result in results for r in result['observations']]
    for result in results: failures.extend(result['failures'])
    # Conflicting current team memberships invalidate the roster identity.
    memberships={}
    for r in rosters: memberships.setdefault(r['player_id'],set()).add(r['team'])
    roster=[r for r in rosters if len(memberships[r['player_id']])==1]
    return {'observations':observations,'roster':roster,'roster_checked':True,
            'season_year':year,'season_type':'regular','games_loaded':sum(r['games_loaded'] for r in results),
            'games_requested':len(selected),'dates_checked':len({e['game_date'] for e in selected.values()}),
            'eligible_games_omitted':0,'history_truncated':False,'failures':failures,
            'season_counts':dict(Counter(r['season_year'] for r in observations)),
            'source':'ESPN regular-season team schedules and verified finals; bounded latest games per slate team'}


def roster_observations(history):
    """Keep historical team attribution; exclude players no longer on that team."""
    rows=history.get('observations',[])
    if not history.get('roster_checked'): return rows
    members={(r['player_id'],r['team']) for r in history.get('roster',[])}
    return [r for r in rows if (r['player_id'],r['team']) in members]
