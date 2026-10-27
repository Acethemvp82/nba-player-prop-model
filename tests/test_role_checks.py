from datetime import date, timedelta
import pytest
from projection_core import core_projections
from role_checks import minutes_role
from role_validation import evaluate_role_scenario
from prop_signal import prop_signal
from market_validation import make_market_record, validate_record, record_id, grade_records


def rows(minutes,year=2027,start=date(2026,10,1),team='NYK'):
    return [dict(player_id='espn:1',player='Example',team=team,game_id=f'espn:{year}{i}',
        game_date=(start+timedelta(days=i)).isoformat(),is_final=True,season_type='regular',
        season_year=year,minutes=m,points=m*.5,rebounds=5,assists=3,threes=1) for i,m in enumerate(minutes)]


def test_sustained_shift_and_prior_season_comparison():
    current=rows([20]*3)[::-1]
    result=minutes_role(current,30,'Prior-season reference')
    assert result['role_status']=='changed' and result['role_change_minutes']==-10
    assert result['role_last_game_date']=='2026-10-03'
    assert minutes_role(current[:2],30,'Prior-season reference')['role_status']=='insufficient_current_role'
    assert minutes_role(rows([30]*3+[24]*3)[::-1],24,'Current season')['role_status']=='changed'
    assert minutes_role(rows([30]*3+[25]*3)[::-1],25,'Current season')['role_status']=='stable'
    assert minutes_role(rows([40]*3+[33]*3)[::-1],33,'Current season')['role_status']=='stable'


def test_role_checks_never_blend_or_relabel_previous_season_projection():
    old=rows([30]*10,2026,date(2026,4,1))
    current=rows([15]*3)
    projections=core_projections(old+current,'2026-10-04')
    points=next(p for p in projections if p['prop']=='points')
    assert points['baseline']==15 and points['forecast_minutes']==30
    assert points['role_recent_minutes']==15 and points['role_status']=='changed'
    assert points['evidence']=='Prior-season reference'
    assert core_projections(old+current+[current[-1]|{'game_date':'2026-10-04','game_id':'espn:99','minutes':48}], '2026-10-04')==projections


def test_role_validation_uses_identical_earlier_samples_and_keeps_formula():
    old=rows([30]*10,2026,date(2026,4,1))
    current=rows([15]*5)
    result=evaluate_role_scenario(old+current,'2026-10-06')
    points=[r for r in result['details'] if r['prop']=='points']
    assert len(points)==2 and all(r['last_training_date']<r['game_date'] for r in points)
    assert all(r['role_scenario']==7.5 and r['actual']==7.5 and r['baseline']==15 for r in points)
    assert all(r['role_status']=='changed' for r in points)
    assert evaluate_role_scenario(old+current+current,'2026-10-06')==result
    assert evaluate_role_scenario(old+[r|{'team':'BOS'} for r in current],'2026-10-06')['details']==[]


def test_new_policy_freezes_gate_and_preserves_legacy_rules():
    from tests.test_market_validation import F,GAME,NOW
    f=F|{'role_status':'changed','role_note':'Minutes down 10'}
    record=make_market_record(f,GAME,18.5,-110,125,'manual_unverified',NOW)
    assert validate_record(record) and record['policy_version']=='line-gap-role-v2'
    assert record['signal']=='Role changed' and not record['eligible'] and record['model_side']=='pass'
    changed=record|{'eligible':True,'signal':'Above line','model_side':'over','reference_side':'under'}
    changed['record_id']=record_id(changed)
    assert not validate_record(changed)
    # v1 records retain their frozen decisions; no retrospective role-gate rewrite.
    legacy=changed|{'policy_version':'line-gap-v1'}
    legacy['record_id']=record_id(legacy)
    assert validate_record(legacy)
    assert grade_records([legacy],{'123':[{'player_id':'espn:1','team':'NYK','minutes':30,'points':20,'is_final':True}]})[0][0]['model_outcome']=='win'


@pytest.mark.parametrize('status',['Conflicting reports','Day-To-Day','Suspended',''])
def test_unrecognized_injury_status_never_becomes_green(status):
    from tests.test_prop_signal import row
    assert prop_signal(row(Status=status))[0]=='Availability uncertain'
