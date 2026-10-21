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
