"""League-wide verified NBA data with explicit ESPN five-position labels.

Depth-chart slots describe projected roles, not confirmed starting lineups.
Fantasy primary positions classify defensive buckets; no G/F split is inferred.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import gzip
import math
import requests
from espn_schedule import ESPN_TO_NBA
from espn_history import collect_espn_history, espn_final_game_players
from slate_evidence import regular_event, team_events
from espn_players import espn_team_roster
from team_identity import TEAM_NAMES

ET=ZoneInfo('America/New_York')
VERSION=1
POSITIONS=('PG','SG','SF','PF','C')
METRICS={'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM','steals':'Steals','blocks':'Blocks'}
PRIMARY={1:'PG',2:'SG',3:'SF',4:'PF',5:'C'}


def get_json(url,params=None,headers=None):
    response=requests.get(url,params=params,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json',**(headers or {})},timeout=15)
    response.raise_for_status()
    return response.json()


def league_teams():
    payload=get_json('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams',{'limit':100})
    try: entries=payload['sports'][0]['leagues'][0]['teams']
    except (KeyError,IndexError,TypeError): raise ValueError('League team directory is unavailable') from None
    teams={}
    for entry in entries:
        team=entry.get('team',{});code=ESPN_TO_NBA.get(team.get('abbreviation'),team.get('abbreviation'));tid=str(team.get('id',''))
        if code in TEAM_NAMES and tid.isascii() and tid.isdigit(): teams[code]=tid
    if set(teams)!=set(TEAM_NAMES) or len(set(teams.values()))!=30:
        raise ValueError('League team directory did not return all 30 unique NBA teams')
    return teams


def parse_primary_positions(payload):
    if not isinstance(payload,list): raise ValueError('Invalid primary-position catalog')
    output={};conflicts=set()
    for row in payload:
        if not isinstance(row,dict): continue
        pid=row.get('id');pos=row.get('defaultPositionId')
        if isinstance(pid,bool) or not isinstance(pid,(int,str)) or not str(pid).isascii() or not str(pid).isdigit(): continue
        if type(pos) is not int or pos not in PRIMARY: continue
        key='espn:'+str(pid)
        if key in output and output[key]!=PRIMARY[pos]: conflicts.add(key)
        else: output[key]=PRIMARY[pos]
    return {key:pos for key,pos in output.items() if key not in conflicts}


def primary_positions(season):
    payload=get_json(f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/players',
        {'view':'players_wl'},{'X-Fantasy-Filter':json.dumps({'players':{'limit':5000,'offset':0}})})
    output=parse_primary_positions(payload)
    # The unfiltered endpoint silently defaults to only 50 alphabetical players.
    if len(output)<300: raise ValueError('Primary-position catalog is incomplete; five-position ranks withheld')
    return output


def parse_depth_chart(payload,expected_team,season,primary):
    if not isinstance(payload,dict): raise ValueError('Invalid depth chart')
    team=payload.get('team',{});actual=ESPN_TO_NBA.get(team.get('abbreviation'),team.get('abbreviation'))
    if actual!=expected_team or payload.get('season',{}).get('year')!=season:
        raise ValueError('Depth chart team or season does not match the requested slate')
    charts=payload.get('depthchart')
    if not isinstance(charts,list) or not charts: raise ValueError('Depth chart has no position slots')
    slots=charts[0].get('positions',{})
    if not isinstance(slots,dict): raise ValueError('Depth chart positions are missing')
    candidates=defaultdict(list);starters={}
    for slot in POSITIONS:
        athletes=slots.get(slot.lower(),{}).get('athletes',[])
        if not isinstance(athletes,list) or not athletes: continue
        for depth,athlete in enumerate(athletes,1):
            if not isinstance(athlete,dict): continue
            pid=str(athlete.get('id',''))
            if not pid.isascii() or not pid.isdigit(): continue
            pid='espn:'+pid;candidates[pid].append((depth,slot))
            if depth==1: starters[slot]=pid
    assignments={}
    for pid,choices in candidates.items():
        depth=min(d for d,_ in choices);tied=[p for d,p in choices if d==depth]
        position=tied[0] if len(tied)==1 else primary.get(pid) if primary.get(pid) in tied else None
        assignments[pid]={'matchup_position':position,'depth':depth,'positions':[p for _,p in choices],
                          'projected_starter':pid in starters.values()}
    if len(starters)!=5 or len(set(starters.values()))!=5:
        # Ambiguous slots cannot establish a five-player starting group.
        for value in assignments.values(): value['projected_starter']=False
    return assignments


def depth_chart(team_id,team,season,primary):
    payload=get_json(f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/depthcharts')
    return parse_depth_chart(payload,team,season,primary)


def collect_league_feed(as_of,slate,cache=None,team_loader=league_teams,
                        primary_loader=primary_positions,schedule_loader=team_events,
                        roster_loader=espn_team_roster,depth_loader=depth_chart,
                        boxscore_loader=espn_final_game_players):
    cutoff=datetime.fromisoformat(as_of).date()
    year=cutoff.year+(cutoff.month>=7)
    teams=team_loader();failures=[]
    if set(teams)!=set(TEAM_NAMES): raise ValueError('All 30 team identities are required for league-wide collection')
    catalogs={}
    for season in (year,year-1):
        try: catalogs[str(season)]=primary_loader(season)
        except Exception as exc:
            failures.append({'source':'primary positions','season':season,'error':str(exc)})
            catalogs[str(season)]={}
    def team_data(item):
        team,tid=item;errors=[];roster=[];roles={};events=[]
        try: roster=roster_loader(tid,team)
        except Exception as exc: errors.append({'team':team,'source':'roster','error':str(exc)})
        try: roles=depth_loader(tid,team,year,catalogs[str(year)])
        except Exception as exc: errors.append({'team':team,'source':'depth chart','error':str(exc)})
        for season in (year,year-1):
            try:
                events.extend(e for raw in schedule_loader(tid,season) if (e:=regular_event(raw,as_of,team,season)))
            except Exception as exc: errors.append({'team':team,'source':'schedule','season':season,'error':str(exc)})
        return team,roster,roles,events,errors
    with ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(team_data,sorted(teams.items())))
    roster=[];roles={};selected={}
    slate_defenses={g.get(side,{}).get('teamTricode') for g in slate for side in ('homeTeam','awayTeam')}
    for team,members,assignments,events,errors in results:
        roster.extend(members);roles[team]=assignments;failures.extend(errors)
        current=[e for e in events if e['season_year']==year]
        prior=sorted([e for e in events if e['season_year']==year-1],key=lambda e:(e['game_date'],e['espnEventId']),reverse=True)
        # Current season is complete; prior history supplies L10/L5 across season boundaries.
        for event in current+prior[:15]: selected[event['espnEventId']]=event
        # Include all prior-season games involving today's defenses, including
        # meetings a traded player had while playing for a different team.
        for event in prior:
            pair={event['homeTeam']['teamTricode'],event['awayTeam']['teamTricode']}
            if pair & slate_defenses: selected[event['espnEventId']]=event
    fallback_positions={}
    for team,assignments in roles.items():
        for pid,role in assignments.items():
            if pid not in catalogs[str(year)] and role.get('matchup_position') in POSITIONS:
                fallback_positions[pid]=role['matchup_position']
    catalogs[str(year)].update(fallback_positions)
    source_cache=cache if isinstance(cache,dict) else {}
    def collect(event):
        eid=event['espnEventId'];old=source_cache.get(eid)
        if isinstance(old,dict) and old.get('event')==event and isinstance(old.get('observations'),list) and old['observations']:
            return eid,old,[]
        next_day=(datetime.fromisoformat(event['game_date']).date()).toordinal()+1
        end=date.fromordinal(next_day).isoformat()
        result=collect_espn_history(end,days=1,max_games=1,schedule_loader=lambda _:[event],boxscore_loader=boxscore_loader)
        rows=result['observations']
        for row in rows: row.update(season_year=event['season_year'],season_type='regular')
        record={'event':event,'observations':rows}
        return eid,record,result.get('failures',[])
    records={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for eid,record,errors in pool.map(collect,selected.values()):
            if record['observations']: records[eid]=record
            failures.extend(errors)
    observations=[row for record in records.values() for row in record['observations']]
    memberships=defaultdict(set)
    for member in roster: memberships[member['player_id']].add(member['team'])
    roster=[member for member in roster if len(memberships[member['player_id']])==1]
    now=datetime.now(timezone.utc).isoformat()
    feed={'version':VERSION,'as_of':as_of,'season_year':year,'updated_at':now,
          'teams':teams,'roster':roster,'roles':roles,'positions':catalogs,'position_fallbacks':fallback_positions,'observations':observations,
          'failures':failures,'games_requested':len(selected),'games_loaded':len(records),
          'current_games':len({r['game_id'] for r in observations if r.get('season_year')==year}),
          'h2h_window':'Current regular season plus previous regular season, across teams; DNPs excluded'}
    return feed,records


def valid_number(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def clean_observations(observations,as_of):
    output={};conflicts=set()
    for r in observations:
        if not isinstance(r,dict) or r.get('is_final') is not True or r.get('season_type')!='regular': continue
        try: day=datetime.fromisoformat(r.get('game_date','')).date().isoformat()
        except (ValueError,TypeError): continue
        if day>=as_of or not str(r.get('player_id','')).startswith('espn:') or not str(r.get('game_id','')).startswith('espn:'): continue
        if r.get('team') not in TEAM_NAMES or r.get('opponent') not in TEAM_NAMES or r['team']==r['opponent']: continue
        if not valid_number(r.get('minutes')) or not 0<r['minutes']<=60: continue
        key=(r['player_id'],r['game_id'])
        if key in output and any(output[key].get(k)!=r.get(k) for k in ('team','opponent','game_date','minutes','season_year',*METRICS)):
            conflicts.add(key)
        else: output.setdefault(key,r)
    return [r for k,r in output.items() if k not in conflicts]


def five_position_allowance(observations,as_of,catalog,season_year,min_games=1):
    if type(min_games) is not int or min_games<1: raise ValueError('Minimum games must be positive')
    grouped=defaultdict(list);seen={};conflicted=set()
    for row in observations:
        if not isinstance(row,dict): continue
        key=(row.get('player_id'),row.get('game_id'))
        prior=seen.get(key)
        if prior and any(prior.get(k)!=row.get(k) for k in ('team','opponent','game_date','minutes','season_year',*METRICS)):
            for value in (row,prior): conflicted.add((value.get('game_id'),value.get('team'),value.get('opponent')))
        else: seen.setdefault(key,row)
    for row in clean_observations(observations,as_of):
        group=(row['game_id'],row['team'],row['opponent'])
        if row.get('season_year')==season_year and group not in conflicted: grouped[group].append(row)
    samples=defaultdict(list);omitted=defaultdict(int)
    for (gid,team,opponent),players in grouped.items():
        if len(players)<5 or any(catalog.get(r['player_id']) not in POSITIONS for r in players):
            omitted[opponent]+=1;continue
        for key in METRICS:
            if not all(valid_number(r.get(key)) for r in players): continue
            for pos in POSITIONS:
                samples[opponent,pos,key].append(sum(r[key] for r in players if catalog[r['player_id']]==pos))
    output={}
    for (team,pos,key),values in samples.items():
        if len(values)>=min_games:
            output[team,pos,key]={'allowed':round(sum(values)/len(values),2),'games':len(values),'rank':None,
                'ranked_teams':0,'varies':False,'omitted_games':omitted[team]}
    for pos in POSITIONS:
        for key in METRICS:
            cohort=[v for (team,p,k),v in output.items() if p==pos and k==key]
            # Never label a one-team or two-team comparison a league rank.
            if len(cohort)<3: continue
            for value in cohort:
                value['rank']=1+sum(other['allowed']>value['allowed'] for other in cohort)
                value['ranked_teams']=len(cohort);value['varies']=len({v['allowed'] for v in cohort})>1
    return output


def build_data_board(feed,slate,prop='points',defense_season='Current season'):
    if prop not in METRICS: raise ValueError('Unknown player stat')
    as_of=feed['as_of'];year=feed['season_year'];def_year=year if defense_season=='Current season' else year-1
    catalog=feed.get('positions',{}).get(str(def_year),{})
    rows=clean_observations(feed.get('observations',[]),as_of)
    context=five_position_allowance(rows,as_of,catalog,def_year)
    by_player=defaultdict(list)
    for row in rows: by_player[row['player_id']].append(row)
    opponents={}
    for game in slate:
        home=game.get('homeTeam',{}).get('teamTricode');away=game.get('awayTeam',{}).get('teamTricode')
        if home in TEAM_NAMES and away in TEAM_NAMES: opponents.update({home:away,away:home})
    current=feed.get('positions',{}).get(str(year),{})
    output=[];seen=set()
    for member in feed.get('roster',[]):
        pid,team=member.get('player_id'),member.get('team')
        if team not in opponents or (pid,team) in seen: continue
        seen.add((pid,team));opponent=opponents[team]
        games=sorted(by_player[pid],key=lambda r:(r['game_date'],r['game_id']),reverse=True)
        role=feed.get('roles',{}).get(team,{}).get(pid,{})
        primary=current.get(pid);position=role.get('matchup_position') or primary
        eligible=[r for r in games if valid_number(r.get(prop))]
        recent=eligible[:10];last5=eligible[:5];h2h=[r for r in eligible if r['opponent']==opponent]
        def avg(sample): return round(sum(r[prop] for r in sample)/len(sample),1) if sample else None
        record={'player_id':pid,'Player':member['player'],'Team':team,'Opponent':opponent,
            'Pos':primary or '—','Group':position or 'Unknown','Line':None,
            'L10':avg(recent),'L5':avg(last5),'H2H':avg(h2h),
            'L10 N':len(recent),'L5 N':len(last5),'H2H N':len(h2h),
            'Latest game':games[0]['game_date'] if games else None,
            'Projected starter':role.get('projected_starter',False),'Depth':role.get('depth'),
            'Status':'Unknown — no current report','Source':'ESPN verified finals; ESPN depth charts and primary positions',
            'Position source':'ESPN depth-chart slot (matchup) / ESPN primary position (badge)',
            'History window':feed.get('h2h_window','Loaded completed regular-season games'),
            'Position verified':position in POSITIONS,'Defense season':def_year}
        for key,label in METRICS.items():
            ctx=context.get((opponent,position,key),{})
            record[label]=ctx.get('allowed');record['rank_'+label]=ctx.get('rank')
            record['teams_'+label]=ctx.get('ranked_teams',0);record['varies_'+label]=ctx.get('varies',False)
            record['games_'+label]=ctx.get('games',0);record['omitted_'+label]=ctx.get('omitted_games',0)
        output.append(record)
    return output


def load_saved_feed(path,day):
    try:
        path=Path(path)
        feed=json.loads(gzip.decompress(path.read_bytes()).decode()) if path.suffix=='.gz' else json.loads(path.read_text())
    except (OSError,ValueError): return None
    if not isinstance(feed,dict) or feed.get('version')!=VERSION or feed.get('as_of')!=day: return None
    try: stamp=datetime.fromisoformat(feed['updated_at'].replace('Z','+00:00'))
    except (KeyError,ValueError,TypeError,AttributeError): return None
    now=datetime.now(timezone.utc)
    if stamp.tzinfo is None or not -120<=(now-stamp).total_seconds()<=7200: return None
    return feed
