from datetime import date
import pytest
from season_schedule import games_on

SAMPLE = [{"games": [
    {"gameId": "0022600001", "gameDateEst": "2026-10-20", "gameStatus": 3},
    {"gameId": "0022600002", "gameDateEst": "2026-10-21", "gameStatus": 1},
    {"gameId": "invalid", "gameDateEst": "2026-10-20"},
]}]

def test_schedule_filters_by_date():
    games = games_on("2026-10-20", SAMPLE)
    assert [g["gameId"] for g in games] == ["0022600001"]

def test_date_object_and_empty_slate():
    assert games_on(date(2026, 10, 21), SAMPLE)[0]["gameStatus"] == 1
    assert games_on("2026-10-22", SAMPLE) == []

def test_bad_date_is_rejected():
    with pytest.raises(ValueError):
        games_on("not-a-date", SAMPLE)


def test_parent_entry_date_used_when_game_has_no_date():
    schedule = [{"gameDate": "10/21/2026 12:00:00 AM",
                 "games": [{"gameId": "0022600003", "gameStatus": 1}]}]
    assert [g["gameId"] for g in games_on("2026-10-21", schedule)] == ["0022600003"]
    assert games_on("2026-10-20", schedule) == []
