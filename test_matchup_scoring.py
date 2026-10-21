import pytest
from matchup_scoring import matchup_context, attach_matchups


def sample():
    return [dict(player_id=str(p), game_id='espn:' + str(g + 100 + side * 10),
                 game_date=f'2026-10-{g+1:02}', is_final=True,
                 team=team, opponent=opp, points=points, rebounds=5,
                 assists=3, threes=1)
            for side, (team, opp, points) in enumerate([('NYK', 'BOS', 10), ('BOS', 'NYK', 20)])
            for g in range(5) for p in range(8)]


def test_matchup_direction_shrinkage_and_no_future_leakage():
    rows = sample()
    ctx = matchup_context(rows, '2026-10-10')
    assert ctx['BOS', 'points']['matchup_score'] == 16.7
    assert ctx['NYK', 'points']['matchup_score'] == 83.3
    assert ctx['NYK', 'rebounds']['matchup_score'] == 50
    future = [{**r, 'game_date': '2026-10-10', 'points': 1000} for r in rows]
    assert matchup_context(rows + future + rows, '2026-10-10') == ctx


def test_small_incomplete_and_single_opponent_samples_are_unknown():
    rows = sample()
    assert matchup_context(rows[:40], '2026-10-10')['BOS', 'points']['matchup_score'] is None
    incomplete = [r for r in rows if r['player_id'] != '7']
    assert matchup_context(incomplete, '2026-10-10') == {}
    assert matchup_context(rows, '2026-10-03')['BOS', 'points']['matchup_score'] is None
    for bad in [0, True, 1.5]:
        with pytest.raises(ValueError):
            matchup_context(rows, '2026-10-10', bad)


def test_attach_preserves_forecast_and_missing_opponent():
    rows = [dict(team='NYK', prop='points', baseline=22), dict(team='MIA', prop='points', baseline=19)]
    result = attach_matchups(rows, {'NYK': 'BOS'}, {})
    assert len(result) == 1
    assert result[0]['baseline'] == 22
    assert result[0]['matchup_score'] is None
    assert rows[0] == dict(team='NYK', prop='points', baseline=22)
