from slate_coverage import slate_coverage


def observation(day, gid, team='NYK', pid='espn:1', points=10, **extra):
    return dict(game_date=day, game_id='espn:' + str(gid), player_id=pid,
                player='Example', team=team, is_final=True, minutes=30,
                points=points, rebounds=5, assists=4, threes=2, **extra)


def test_all_slate_teams_and_separate_sparse_history():
    rows = [observation('2026-10-10', g) for g in range(4)]
    teams, previews = slate_coverage(rows, '2026-10-21', {'NYK':'BOS','BOS':'NYK'}, [])
    assert len(teams) == 2
    assert teams[0]['Coverage'] == 'No player history'
    assert teams[1]['Coverage'] == 'Fewer than 5 appearances'
    assert previews[0]['Appearances'] == 4
    assert previews[0]['Points avg'] == 10
    assert 'Projection' not in previews[0]


def test_duplicates_future_nonfinal_and_nonslate_teams_excluded():
    past = observation('2026-10-10', 1)
    rows = [past, past, observation('2026-10-21', 2, points=100),
            observation('2026-10-22', 3, points=100),
            {**past, 'game_id': 'espn:4', 'is_final':False},
            observation('2026-10-10', 5, team='MIA', pid='espn:2')]
    teams, previews = slate_coverage(rows, '2026-10-21', {'NYK':'BOS'}, [])
    assert teams[0]['Players observed'] == 1
    assert previews[0]['Appearances'] == 1
    assert previews[0]['Points avg'] == 10


def test_available_players_count_distinct_ids_and_sparse_missing_stats():
    rows = [observation('2026-10-10', g) for g in range(5)]
    forecasts = [dict(team='NYK', player_id='espn:1', prop=p) for p in ('points','rebounds')]
    teams, previews = slate_coverage(rows, '2026-10-21', {'NYK':'BOS'}, forecasts)
    assert teams[0]['Players with baselines'] == 1
    assert teams[0]['Baseline rows'] == 2
    assert teams[0]['Coverage'] == 'Baselines available'
    assert previews == []
    teams, _ = slate_coverage(rows, '2026-10-21', {'NYK':'BOS'}, [])
    assert teams[0]['Coverage'] == 'Incomplete player stats'


def test_latest_team_membership_and_invalid_asof():
    import pytest
    rows = [observation('2026-10-10', 1), observation('2026-10-20', 2, team='BOS')]
    teams, previews = slate_coverage(rows, '2026-10-21', {'NYK':'BOS','BOS':'NYK'}, [])
    assert teams[0]['Players observed'] == 1
    assert teams[1]['Players observed'] == 0
    assert previews[0]['Team'] == 'BOS'
    with pytest.raises(ValueError):
        slate_coverage([], 'invalid', {}, [])
