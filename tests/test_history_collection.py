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
        {"gameId": "104", "gameStatus": 2, "gameDate": "10/20/2026 12:00:00 AM"},
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


def test_large_history_budget_remains_bounded():
    schedule = [{"games": [
        {"gameId": str(1000 + i), "gameStatus": 3, "gameDateEst": "2026-10-19"}
        for i in range(350)
    ]}]
    calls = []
    def loader(gid):
        calls.append(gid)
        return []
    result = collect_recent_history(schedule, "2026-10-20", max_games=320, loader=loader)
    assert result["games_requested"] == 320
    assert result["eligible_games"] == 350
    assert len(calls) == 320


def test_final_boxscore_rejects_missing_team_players(monkeypatch):
    import pytest
    from nba_data import NBADataError
    from history_collection import fetch_boxscore_players
    monkeypatch.setattr("history_collection._get_json", lambda _: {
        "game": {"gameId": "123", "gameStatus": 3,
                 "homeTeam": {"teamTricode": "BOS", "players": []},
                 "awayTeam": {"teamTricode": "NYK"}}})
    with pytest.raises(NBADataError, match="player lists"):
        fetch_boxscore_players("123")


def test_final_boxscore_rejects_duplicate_team_identity(monkeypatch):
    import pytest
    from nba_data import NBADataError
    from history_collection import fetch_boxscore_players
    monkeypatch.setattr("history_collection._get_json", lambda _: {
        "game": {"gameId": "123", "gameStatus": 3,
                 "homeTeam": {"teamTricode": "BOS", "players": []},
                 "awayTeam": {"teamTricode": "BOS", "players": []}}})
    with pytest.raises(NBADataError, match="team identities"):
        fetch_boxscore_players("123")


def test_duplicate_schedule_entries_count_once_even_when_budget_is_small():
    schedule = [{"games": [
        {"gameId": "100", "gameStatus": 3, "gameDateEst": "2026-10-19"},
        {"gameId": "100", "gameStatus": 3, "gameDateEst": "2026-10-19"},
        {"gameId": "101", "gameStatus": 3, "gameDateEst": "2026-10-18"},
    ]}]
    called = []
    def loader(gid):
        called.append(gid)
        return []
    result = collect_recent_history(schedule, "2026-10-20", max_games=1, loader=loader)
    assert result["eligible_games"] == 2
    assert result["games_requested"] == 1
    assert called == ["100"]


def test_missing_schedule_game_lists_are_skipped():
    schedule = [
        {"gameDate": "2026-10-19", "games": None},
        {"gameDate": "2026-10-19"},
        {"games": [{"gameId": "777", "gameStatus": 3,
                    "gameDateEst": "2026-10-19"}]},
    ]
    result = collect_recent_history(schedule, "2026-10-20", loader=lambda _: [])
    assert result["games_requested"] == 1
    assert result["eligible_games"] == 1


def test_invalid_schedule_is_rejected():
    import pytest
    from nba_data import NBADataError
    with pytest.raises(NBADataError, match="schedule"):
        collect_recent_history(None, "2026-10-20")


def test_missing_games_list_is_skipped():
    schedule = [
        {"gameDate": "2026-10-18", "games": None},
        {"gameDate": "2026-10-18", "games": "invalid"},
        {"gameDate": "2026-10-18", "games": [{"gameId": "200", "gameStatus": 3}]},
    ]
    result = collect_recent_history(schedule, "2026-10-20", loader=lambda _: [])
    assert result["games_requested"] == 1
    assert result["games_loaded"] == 1


def test_invalid_schedule_is_rejected():
    import pytest
    from nba_data import NBADataError
    with pytest.raises(NBADataError, match="schedule"):
        collect_recent_history(None, "2026-10-20")


def test_final_boxscore_skips_malformed_players_and_stats(monkeypatch):
    from history_collection import fetch_boxscore_players
    monkeypatch.setattr("history_collection._get_json", lambda _: {
        "game": {"gameId": "123", "gameStatus": 3,
                 "homeTeam": {"teamTricode": "BOS", "players": [
                     None, "invalid", {"personId": 7, "name": "Example",
                                       "statistics": "invalid"}]},
                 "awayTeam": {"teamTricode": "NYK", "players": []}}})
    players = fetch_boxscore_players("123")
    assert len(players) == 1
    assert players[0]["player_id"] == 7
    assert players[0]["statistics"] == {}


def test_stale_in_progress_schedule_status_can_load_verified_final():
    schedule = [{"games": [{"gameId": "222", "gameStatus": 2,
                             "gameDateEst": "2026-10-18"}]}]
    called = []
    def verified_loader(gid):
        called.append(gid)
        return [{"player_id": 9, "player": "Example", "team": "NYK",
                 "statistics": {"minutes": "PT20M", "points": 17}}]
    result = collect_recent_history(schedule, "2026-10-20", loader=verified_loader)
    assert called == ["222"]
    assert result["games_loaded"] == 1
    assert result["observations"][0]["points"] == 17


def test_final_boxscore_rejects_malformed_team_objects(monkeypatch):
    import pytest
    from nba_data import NBADataError
    from history_collection import fetch_boxscore_players
    monkeypatch.setattr("history_collection._get_json", lambda _: {
        "game": {"gameId": "123", "gameStatus": 3,
                 "homeTeam": ["unexpected"], "awayTeam": {"teamTricode": "NYK", "players": []}}})
    with pytest.raises(NBADataError, match="malformed team objects"):
        fetch_boxscore_players("123")


def test_history_skips_non_ascii_numeric_game_ids():
    schedule = [{"games": [
        {"gameId": "１２３", "gameStatus": 3, "gameDateEst": "2026-10-19"},
        {"gameId": "123", "gameStatus": 3, "gameDateEst": "2026-10-19"},
    ]}]
    called = []
    result = collect_recent_history(schedule, "2026-10-20",
                                    loader=lambda gid: called.append(gid) or [])
    assert called == ["123"]
    assert result["games_requested"] == 1


def test_final_boxscore_rejects_boolean_game_id():
    import pytest
    from nba_data import NBADataError
    from history_collection import fetch_boxscore_players
    with pytest.raises(NBADataError, match="Invalid NBA game ID"):
        fetch_boxscore_players(True)
