import pytest
from projection_core import core_projections


def game(i,minutes=30,points=15,team='NYK'):
    return dict(player_id='espn:1',player='Example',game_id=f'espn:{i}',game_date=f'2026-10-{i:02}',
                team=team,opponent='BOS',is_final=True,minutes=minutes,points=points,
                rebounds=6,assists=3,threes=1,position='G')


def test_minutes_rate_math_and_zero_is_valid():
    rows=[game(i) for i in range(1,6)]
    result={r['prop']:r for r in core_projections(rows,'2026-10-10')}
    assert result['points']['baseline']==15
    assert result['points']['forecast_minutes']==30
    assert result['points']['rate_per_minute']==.5
    zero=[{**r,'threes':0} for r in rows]
    assert next(r for r in core_projections(zero,'2026-10-10') if r['prop']=='threes')['baseline']==0


def test_median_minutes_resists_one_short_game_and_no_future_leakage():
    rows=[game(i,minutes=30 if i<5 else 5,points=15 if i<5 else 2.5) for i in range(1,6)]
    first=core_projections(rows,'2026-10-10')
    assert first[0]['forecast_minutes']==30 and first[0]['baseline']==15
    assert core_projections(rows+rows+[game(10,points=999)],'2026-10-10')==first


def test_conflicts_missing_metrics_and_new_team_abstain():
    rows=[game(i) for i in range(1,6)]
    assert core_projections(rows+[{**rows[-1],'points':99}],'2026-10-10')==[]
    assert core_projections(rows+[game(6,team='BOS')],'2026-10-10')==[]
    assert not any(r['prop']=='points' for r in core_projections([{**r,'points':None} for r in rows],'2026-10-10'))
    with pytest.raises(ValueError): core_projections(rows,'bad')
