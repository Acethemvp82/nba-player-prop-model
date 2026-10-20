"""Offline validation of NBA public-data adapter."""
import pytest
import nba_data

def test_scoreboard_parses(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {"scoreboard": {"games": [{"gameId": "001"}]}})
    assert nba_data.scoreboard()[0]["gameId"] == "001"

def test_scoreboard_rejects_bad_payload(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {"scoreboard": {}})
    with pytest.raises(nba_data.NBADataError):
        nba_data.scoreboard()

def test_game_players_maps_opponents(monkeypatch):
    sample = {"game": {"homeTeam": {"teamTricode": "BOS", "players": [{"personId": 1, "name": "Player A"}]},
                       "awayTeam": {"teamTricode": "NYK", "players": [{"personId": 2, "name": "Player B"}]}}}
    monkeypatch.setattr(nba_data, "_get_json", lambda _: sample)
    players = nba_data.game_players("123")
    assert [(p["team"], p["opponent"]) for p in players] == [("BOS", "NYK"), ("NYK", "BOS")]

def test_rejects_invalid_game_id():
    with pytest.raises(nba_data.NBADataError):
        nba_data.game_players("../bad")
