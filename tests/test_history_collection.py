from historical_stats import _day
from history_collection import collect_recent_history, recent_player_summaries

def test_nba_date_formats():
    assert _day("10/20/2026 12:00:00 AM").isoformat() == "2026-10-20"
    assert _day("2026-10-20").isoformat() == "2026-10-20"

def test_history_excludes_today_and_future_and_reports_failures():
    schedule = [{"games": [
        {"gameId": "101", "gameStatus": 3, "gameDate": "10/18/2026 12:00:00 AM"},
        {"gameId": "102", "gameStatus": 3, "gameDate": "10/19/2026 12:00:00 AM"},
        {"gameId": "103", "gameStatus": 3, "gameDate": "10/20/2026 12:00:00 AM"},
        {"gameId": "104", "gameStatus": 2, "gameDate": "10/17/2026 12:00:00 AM"},
    ]}]
    called = []
    def loader(gid):
        called.append(gid)
        if gid == "102":
            raise ValueError("missing")
        return [{"player_id": 9, "player": "Sample", "team": "NYK",
                 "statistics": {"minutes": "PT30M", "points": 20,
                                "reboundsTotal": 6, "assists": 4,
                                "threePointersMade": 2}}]
    result = recent_player_summaries(schedule, "2026-10-20", loader=loader)
    assert called == ["102", "101"]
    assert result["games_requested"] == 2
    assert result["games_loaded"] == 1
    assert len(result["failed_games"]) == 1
    assert result["summaries"][0]["points_last_5_avg"] == 20

def test_bounded_history():
    schedule = [{"games": [{"gameId": str(i), "gameStatus": 3,
                             "gameDateEst": "2026-10-19"} for i in range(10)]}]
    result = collect_recent_history(schedule, "2026-10-20", max_games=2,
                                    loader=lambda _: [])
    assert result["games_requested"] == 2
    assert result["eligible_games"] == 10


def test_invalid_player_payload_is_reported():
    schedule = [{"games": [{"gameId": "123", "gameStatus": "3", "gameDateEst": "2026-10-19"}]}]
    result = collect_recent_history(schedule, "2026-10-20", loader=lambda _: None)
    assert result["games_requested"] == 1
    assert result["games_loaded"] == 0
    assert len(result["failed_games"]) == 1
    assert result["observations"] == []


def test_stale_schedule_status_uses_verified_boxscore_loader():
    schedule = [{"games": [{"gameId": "555", "gameStatus": 1,
                             "gameDateEst": "2026-10-18"}]}]
    called = []
    def verified_final_loader(gid):
        called.append(gid)
        return [{"player_id": 7, "player": "Test", "team": "BOS",
                 "statistics": {"minutes": "PT25M", "points": 16}}]
    result = collect_recent_history(schedule, "2026-10-20",
                                    loader=verified_final_loader)
    assert called == ["555"]
    assert result["games_loaded"] == 1
    assert result["observations"][0]["points"] == 16


def test_parent_schedule_date_is_preserved():
    schedule = [{"gameDate": "10/19/2026 12:00:00 AM",
                 "games": [{"gameId": "888", "gameStatus": 1}]}]
    result = collect_recent_history(schedule, "2026-10-20",
        loader=lambda gid: [{"player_id": 2, "player": "Sample",
                             "statistics": {"minutes": "PT20M", "points": 11}}])
    assert result["games_loaded"] == 1
    assert result["observations"][0]["game_date"] == "2026-10-19"
