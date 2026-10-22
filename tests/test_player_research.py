import pytest
from player_research import player_games, compare_line, minutes_scenario


def row(day, gid, value=10, **extra):
    return dict(player_id='espn:1', game_id=f'espn:{gid}', game_date=day,
                is_final=True, minutes=30, points=value, team='BOS', opponent='NYK', **extra)


def test_recent_samples_exclude_future_invalid_and_duplicates():
    old = row('2026-10-10', 1)
    rows = [old, old, row('2026-10-11',2,20), row('2026-10-21',3,100),
            {**old,'game_id':'bad'}, {**old,'game_id':'espn:4','is_final':False},
            {**old,'player_id':'espn:2'}]
    result = player_games(rows,'espn:1','points','2026-10-21')
    assert [r['Result'] for r in result] == [20,10]
    assert len(player_games(rows,'espn:1','points','2026-10-21',limit=1)) == 1


def test_line_comparison_counts_pushes_separately():
    result = compare_line([{'Result':v} for v in [9,10,11]],10,-110)
    assert (result['over'],result['under'],result['push']) == (1,1,1)
    assert result['break_even'] == pytest.approx(110/210)
    assert compare_line([],0)['sample_games'] == 0
    assert compare_line([],0,0)['break_even'] is None


def test_scenarios_are_explicit_not_probabilities():
    assert minutes_scenario(20,30,36) == 24
    assert minutes_scenario(20,30,0) == 0
    for args in [(20,0,30),(True,30,30),(20,30,49),(20,30,float('nan'))]:
        with pytest.raises(ValueError): minutes_scenario(*args)
    for line in [True,-1,float('nan'),'10']:
        with pytest.raises(ValueError): compare_line([],line)
