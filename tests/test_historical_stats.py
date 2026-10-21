from historical_stats import player_history_summaries

def game(i, day, points, minutes=30, **extra):
    return {"player_id": 12, "player": "Example", "team": "BOS",
            "game_id": str(i), "game_date": day, "is_final": True,
            "minutes": minutes, "points": points, **extra}

def test_recent_windows_and_order():
    rows = [game(i, f"2026-01-{i:02d}", i) for i in range(1, 13)]
    result = player_history_summaries(rows)[0]
    assert result["games_played"] == 12
    assert result["points_last_5_avg"] == 10
    assert result["points_last_10_avg"] == 7.5
    assert result["points_season_avg"] == 6.5

def test_cutoff_prevents_future_game_leakage():
    rows = [game(1, "2026-01-01", 10), game(2, "2026-01-02", 90)]
    result = player_history_summaries(rows, as_of="2026-01-02")[0]
    assert result["points_season_avg"] == 10
    assert result["games_played"] == 1

def test_missing_stats_and_inactive_games():
    rows = [game(1, "2026-01-01", 8, assists=3),
            game(2, "2026-01-02", None, assists=None),
            game(3, "2026-01-03", 20, minutes=0),
            {**game(4, "2026-01-04", 100), "is_final": False}]
    result = player_history_summaries(rows)[0]
    assert result["games_played"] == 2
    assert result["points_season_avg"] == 8
    assert result["points_season_n"] == 1
    assert result["assists_season_n"] == 1

def test_duplicate_games_and_undated_rows():
    rows = [game(1, "2026-01-01", 10), game(1, "2026-01-01", 10),
            game(2, None, 99)]
    result = player_history_summaries(rows)[0]
    assert result["games_played"] == 1


def test_numeric_and_string_game_ids_are_same_game():
    rows = [game(123, "2026-01-01", 10),
            game("123", "2026-01-01", 10)]
    result = player_history_summaries(rows)
    assert result[0]["games_played"] == 1
    assert result[0]["points_season_avg"] == 10


def test_malformed_observation_is_ignored():
    rows = [None, "bad", game(123, "2026-01-01", 15)]
    result = player_history_summaries(rows)
    assert result[0]["games_played"] == 1


def test_date_parser_rejects_trailing_garbage_but_accepts_iso_timestamp():
    from historical_stats import _day
    from datetime import date
    assert _day("2026-10-20garbage") is None
    assert _day("2026-10-20T19:30:00Z") == date(2026, 10, 20)
    assert _day("2026-10-20T19:30:00-04:00") == date(2026, 10, 20)
