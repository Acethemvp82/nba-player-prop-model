import pytest
from history_quality import history_quality


def observation(pid=1, **changes):
    row = {"game_id": "123", "game_date": "2026-10-18", "is_final": True,
           "player_id": pid, "minutes": 30, "points": 20,
           "rebounds": 5, "assists": 4, "threes": 2}
    row.update(changes)
    return row


def test_history_quality_counts_missing_values_and_coverage():
    rows = [observation(), observation(2, assists=None),
            observation(3, game_id="124", points=float("nan")),
            observation(4, game_date="2026-10-20"),
            observation(5, is_final=False),
            observation(6, minutes=0), None]
    result = history_quality(rows, "2026-10-20")
    assert result["rows_received"] == 7
    assert result["usable_appearances"] == 3
    assert result["unique_games"] == 2
    assert result["unique_players"] == 3
    assert result["assists_missing"] == 1
    assert result["points_missing"] == 1
    assert result["rejected_date"] == 1
    assert result["rejected_nonfinal_or_invalid"] == 2
    assert result["rejected_identity_or_minutes"] == 1


def test_history_quality_rejects_bad_cutoff():
    with pytest.raises(ValueError):
        history_quality([], "not-a-date")


def test_duplicate_appearances_are_reported_not_double_counted():
    rows = [observation(1, points=20),
            observation(1, points=40),
            observation(2, points=10)]
    result = history_quality(rows, "2026-10-20")
    assert result["rows_received"] == 3
    assert result["usable_appearances"] == 2
    assert result["duplicate_appearances"] == 1
    assert result["unique_players"] == 2
    assert result["unique_games"] == 1
