from projection_baseline import baseline_projections

def test_baseline_blend_and_four_props():
    row = {"player_id": 1, "player": "Sample", "team": "NYK",
           "games_played": 10, "minutes_last_5_avg": 30}
    for prop in ("points", "rebounds", "assists", "threes"):
        row[f"{prop}_season_n"] = 10
        row[f"{prop}_season_avg"] = 10
        row[f"{prop}_last_10_avg"] = 12
        row[f"{prop}_last_5_avg"] = 15
    result = baseline_projections([row])
    assert len(result) == 4
    assert all(r["baseline"] == 12.7 for r in result)
    assert all(r["sample_games"] == 10 for r in result)

def test_insufficient_games_not_projected():
    assert baseline_projections([{"games_played": 2, "minutes_last_5_avg": 22}]) == []

def test_missing_stats_not_zero_filled():
    row = {"games_played": 10, "minutes_last_5_avg": 28,
           "points_season_n": 10, "points_season_avg": None,
           "points_last_10_avg": 12, "points_last_5_avg": 15}
    assert baseline_projections([row]) == []

def test_invalid_min_games_rejected():
    import pytest
    with pytest.raises(ValueError):
        baseline_projections([], min_games=0)
