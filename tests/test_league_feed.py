from datetime import datetime,timezone,timedelta
import json
import pytest
from league_feed import (parse_primary_positions,parse_depth_chart,five_position_allowance,
    build_data_board,clean_observations,load_saved_feed,collect_league_feed)
from team_identity import TEAM_NAMES


def observations():
    rows=[];catalog={};teams=list(TEAM_NAMES)
    for index,team in enumerate(teams):
        opponent=teams[index^1]
        for slot,pos in enumerate(('PG','SG','SF','PF','C')):
            pid=f'espn:{index*5+slot+1}';catalog[pid]=pos
            rows.append(dict(player_id=pid,player=f'{team} {pos}',team=team,opponent=opponent,
                game_id=f'espn:{index//2+100}',game_date='2026-10-21',season_year=2027,season_type='regular',
                is_final=True,minutes=40,points=index+1,rebounds=index+1,assists=index+1,
                threes=index+1,steals=index+1,blocks=index+1))
    return rows,catalog


def test_thirty_teams_five_positions_six_stats_with_explicit_one_game_samples():
    rows,catalog=observations();ctx=five_position_allowance(rows,'2026-10-29',catalog,2027)
    assert len(ctx)==30*5*6
    assert all(v['games']==1 and v['ranked_teams']==30 for v in ctx.values())
    for pos in ('PG','SG','SF','PF','C'):
        assert {v['rank'] for (team,p,key),v in ctx.items() if p==pos and key=='points'}==set(range(1,31))
    assert not five_position_allowance(rows,'2026-10-29',catalog,2027,min_games=2)


def test_unknown_positions_do_not_create_fake_zero_allowance():
    rows,catalog=observations();catalog.pop(rows[0]['player_id'])
    ctx=five_position_allowance(rows,'2026-10-29',catalog,2027)
    assert (rows[0]['opponent'],'PG','points') not in ctx
    assert all(v['ranked_teams']==29 for v in ctx.values())


def test_missing_optional_stat_keeps_other_metrics_and_never_becomes_zero():
    rows,catalog=observations();rows[0].pop('steals')
    ctx=five_position_allowance(rows,'2026-10-29',catalog,2027)
    assert (rows[0]['opponent'],'PG','steals') not in ctx
    assert (rows[0]['opponent'],'PG','points') in ctx


def test_duplicate_conflict_disqualifies_whole_team_game():
    rows,catalog=observations();duplicate={**rows[0],'blocks':99}
    ctx=five_position_allowance(rows+[duplicate],'2026-10-29',catalog,2027)
    assert not any(team==rows[0]['opponent'] for team,pos,key in ctx)
    assert len(clean_observations(rows+[duplicate],'2026-10-29'))==len(rows)-1


def test_asof_dnp_and_season_filters():
    rows,catalog=observations()
    extras=[{**rows[0],'game_id':'espn:999','points':999,'game_date':'2026-10-29'},
            {**rows[0],'game_id':'espn:998','points':999,'season_type':'preseason'},
            {**rows[0],'game_id':'espn:997','points':999,'minutes':0}]
    assert five_position_allowance(rows+extras,'2026-10-29',catalog,2027)==five_position_allowance(rows,'2026-10-29',catalog,2027)
    assert not five_position_allowance(rows,'2026-10-29',catalog,2026)


def test_primary_catalog_only_uses_explicit_positions_and_rejects_conflicts():
    assert parse_primary_positions([{'id':1,'defaultPositionId':1},{'id':2,'defaultPositionId':5},
        {'id':3,'defaultPositionId':True},{'id':True,'defaultPositionId':3}])=={'espn:1':'PG','espn:2':'C'}
    assert parse_primary_positions([{'id':1,'defaultPositionId':1},{'id':1,'defaultPositionId':2}])=={}


def chart():
    return {'team':{'abbreviation':'ATL'},'season':{'year':2027},'depthchart':[{'positions':{
        pos.lower():{'athletes':[{'id':str(i+1),'displayName':pos},{'id':'99','displayName':'Bench'}]}
        for i,pos in enumerate(('PG','SG','SF','PF','C'))}}]}


def test_depth_chart_ties_and_starters_require_source_evidence():
    roles=parse_depth_chart(chart(),'ATL',2027,{'espn:99':'SF'})
    assert sum(r['projected_starter'] for r in roles.values())==5
    assert roles['espn:99']['matchup_position']=='SF'
    assert parse_depth_chart(chart(),'ATL',2027,{})['espn:99']['matchup_position'] is None
    with pytest.raises(ValueError): parse_depth_chart(chart(),'BOS',2027,{})
    with pytest.raises(ValueError): parse_depth_chart(chart(),'ATL',2026,{})
    ambiguous=chart();ambiguous['depthchart'][0]['positions']['sg']['athletes'][0]['id']='1'
    assert not any(r['projected_starter'] for r in parse_depth_chart(ambiguous,'ATL',2027,{}).values())


def test_traded_player_trends_and_h2h_keep_former_team_results():
    rows,catalog=observations();player=rows[0];pid=player['player_id'];team=player['team'];opp=player['opponent']
    former={**player,'team':'CLE','opponent':opp,'game_id':'espn:888','game_date':'2026-04-01','season_year':2026,'points':19}
    feed={'as_of':'2026-10-29','season_year':2027,'positions':{'2027':catalog,'2026':catalog},
          'observations':rows+[former],'roster':[dict(player_id=pid,player='Traded player',team=team)],
          'roles':{team:{pid:{'matchup_position':'SG','projected_starter':True}}}}
    slate=[{'homeTeam':{'teamTricode':team},'awayTeam':{'teamTricode':opp}}]
    r=build_data_board(feed,slate)[0]
    assert r['Team']==team and r['Pos']=='PG' and r['Group']=='SG'
    assert r['L10']==10 and r['L5']==10 and r['H2H']==10 and r['H2H N']==2
    assert r['L10 N']==2 and r['Projected starter']
    assert build_data_board(feed,slate,prop='blocks')[0]['L10']==1


def test_archive_requires_same_day_and_fresh_timestamp(tmp_path):
    path=tmp_path/'feed.json';now=datetime.now(timezone.utc)
    data={'version':1,'as_of':'2026-10-29','updated_at':now.isoformat()}
    path.write_text(json.dumps(data));assert load_saved_feed(path,'2026-10-29')==data
    assert load_saved_feed(path,'2026-10-30') is None
    data['updated_at']=(now-timedelta(hours=3)).isoformat();path.write_text(json.dumps(data))
    assert load_saved_feed(path,'2026-10-29') is None


def test_collector_requests_all_teams_both_seasons_for_small_slate():
    requested=[];teams={team:str(i+1) for i,team in enumerate(TEAM_NAMES)}
    def schedules(tid,season): requested.append((tid,season));return []
    feed,cache=collect_league_feed('2026-10-29',[],team_loader=lambda:teams,primary_loader=lambda year:{},
        schedule_loader=schedules,roster_loader=lambda tid,team:[],depth_loader=lambda tid,team,*a:{'espn:999':{'matchup_position':'PG'}} if team=='ATL' else {},boxscore_loader=lambda _:[])
    assert len(requested)==60 and len({tid for tid,season in requested})==30
    assert {season for tid,season in requested}=={2026,2027}
    assert feed['teams']==teams and cache=={}
    assert feed['positions']['2027']['espn:999']=='PG'
    assert feed['position_fallbacks']=={'espn:999':'PG'}
