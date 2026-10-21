from opponent_stats import opponent_game_totals


def row(pid, opponent="BOS", day="2026-10-18", points=20, **extra):
    return {"player_id": pid, "game_id": "123", "game_date": day,
            "team": "NYK", "opponent": opponent, "is_final": True,
            "points": points, "rebounds": 5, "assists": 3, "threes": 2,
            **extra}


def test_observed_totals_and_deduplication():
    rows = [row(1, points=20), row(2, points=10), row(1, points=20)]
    result = opponent_game_totals(rows, "2026-10-20")
    assert len(result) == 1
    assert result[0]["players_observed"] == 2
    assert result[0]["points_allowed_observed"] == 30
    assert result[0]["threes_allowed_observed"] == 4


def test_cutoff_and_nonfinal_excluded():
    rows = [row(1, day="2026-10-20"), {**row(2), "is_final": False}]
    assert opponent_game_totals(rows, "2026-10-20") == []


def test_missing_prop_is_not_zero_filled():
    rows = [row(1), {**row(2), "assists": None}]
    result = opponent_game_totals(rows, "2026-10-20")
    assert result[0]["assists_allowed_observed"] is None
    assert result[0]["points_allowed_observed"] == 40


def test_screened_opponent_averages_include_sample_counts():
    from opponent_stats import opponent_sample_summary
    games = [
        {"opponent": "BOS", "players_observed": 9,
         "points_allowed_observed": 100, "rebounds_allowed_observed": 42,
         "assists_allowed_observed": None, "threes_allowed_observed": 12},
        {"opponent": "BOS", "players_observed": 10,
         "points_allowed_observed": 110, "rebounds_allowed_observed": 44,
         "assists_allowed_observed": 22, "threes_allowed_observed": 14},
        {"opponent": "BOS", "players_observed": 3,
         "points_allowed_observed": 10, "rebounds_allowed_observed": 5,
         "assists_allowed_observed": 2, "threes_allowed_observed": 1},
    ]
    result = opponent_sample_summary(games)
    assert len(result) == 1
    assert result[0]["screened_games"] == 2
    assert result[0]["points_observed_avg"] == 105
    assert result[0]["assists_valid_games"] == 1
    assert result[0]["assists_observed_avg"] == 22


def test_opponent_averages_reject_invalid_screen():
    import pytest
    from opponent_stats import opponent_sample_summary
    with pytest.raises(ValueError):
        opponent_sample_summary([], min_players=0)


def test_duplicate_player_keeps_first_observation():
    rows = [row(1, points=17), row(1, points=99)]
    result = opponent_game_totals(rows, "2026-10-20")
    assert result[0]["players_observed"] == 1
    assert result[0]["points_allowed_observed"] == 17


def test_bad_coverage_counts_are_skipped():
    from opponent_stats import opponent_sample_summary
    games = [
        {"opponent": "BOS", "players_observed": None, "points_allowed_observed": 100},
        {"opponent": "NYK", "players_observed": True, "points_allowed_observed": 100},
        {"opponent": "MIA", "players_observed": 8, "points_allowed_observed": 90},
    ]
    result = opponent_sample_summary(games)
    assert len(result) == 1
    assert result[0]["opponent"] == "MIA"
