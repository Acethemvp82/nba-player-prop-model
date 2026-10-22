from slate_evidence import regular_event, roster_observations
from projection_core import core_projections
from forecast_tracking import capture_forecasts, save_first_forecasts, score_forecasts
from datetime import datetime,timezone


def event(kind=2,year=2026):
    return {'id':'123','date':'2026-04-01T23:00Z','season':{'year':year},'seasonType':{'type':kind},
            'competitions':[{'status':{'type':{'completed':True}},'competitors':[
                {'homeAway':'home','team':{'abbreviation':'NYK'}},{'homeAway':'away','team':{'abbreviation':'BOS'}}]}]}


def rows():
    return [dict(player_id='espn:1',player='Example',game_id=f'espn:{i}',game_date=f'2026-04-{i:02}',
                team='NYK',opponent='BOS',is_final=True,minutes=30,points=15,rebounds=5,assists=4,threes=2,
                season_type='regular',season_year=2026) for i in range(1,11)]


def test_season_type_finality_date_and_matchup():
    assert regular_event(event(),'2026-10-22','NYK',2026)['season_type']=='regular'
    assert regular_event(event(1),'2026-10-22','NYK',2026) is None
    assert regular_event(event(),'2026-03-01','NYK',2026) is None
    assert regular_event(event(),'2026-10-22','PHI',2026) is None
    assert regular_event(event(),'2026-10-22','NYK',2027) is None


def test_prior_reference_never_blends_with_current_or_preseason():
    old=rows();current=[{**old[0],'game_id':'espn:50','game_date':'2026-10-21','season_year':2027,'points':90}]
    preseason=[{**old[0],'game_id':'espn:51','game_date':'2026-10-20','season_type':'preseason','points':999}]
    result=core_projections(old+current+preseason,'2026-10-22')
    p=next(r for r in result if r['prop']=='points')
    assert p['baseline']==15 and p['evidence']=='Prior-season reference' and p['current_season_games']==1
    current=[{**old[0],'game_id':f'espn:{i+50}','game_date':f'2026-10-{i+1:02}','season_year':2027,'points':20} for i in range(5)]
    p=core_projections(old+current,'2026-10-22')[0]
    assert p['baseline']==20 and p['evidence']=='Current season'


def test_roster_excludes_former_team_and_capture_is_pretip_append_only(tmp_path):
    h={'observations':rows(),'roster_checked':True,'roster':[{'player_id':'espn:1','team':'NYK'}]}
    assert len(roster_observations(h))==10
    assert roster_observations({**h,'roster':[{'player_id':'espn:1','team':'BOS'}]})==[]
    g=[{'espnEventId':'123','homeTeam':{'teamTricode':'NYK'},'awayTeam':{'teamTricode':'BOS'},
        'gameTimeUTC':'2026-10-22T23:00Z','espnCompleted':False,'gameStatusText':'Scheduled'}]
    now=datetime(2026,10,22,20,tzinfo=timezone.utc)
    captured=capture_forecasts(h,g,'2026-10-22',now)
    assert len(captured)==4
    assert capture_forecasts(h,g,'2026-10-22',datetime(2026,10,23,tzinfo=timezone.utc))==[]
    path=tmp_path/'forecasts.json';save_first_forecasts(captured,path)
    assert save_first_forecasts([{**r,'baseline':999} for r in captured],path)==captured
    scored=score_forecasts(captured,lambda _:rows()[:1]);assert len(scored)==4
    assert all(r['absolute_error']==0 for r in scored)
    assert score_forecasts(captured,lambda _:[])==[]


def test_utah_long_code_is_normalized():
    e=event();e['competitions'][0]['competitors'][1]['team']['abbreviation']='UTAH'
    assert regular_event(e,'2026-10-22','NYK',2026)['awayTeam']['teamTricode']=='UTA'
