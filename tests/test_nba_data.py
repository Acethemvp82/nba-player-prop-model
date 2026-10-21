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
    sample = {"game": {"gameId": "123", "homeTeam": {"teamTricode": "BOS", "players": [{"personId": 1, "name": "Player A"}]},
                       "awayTeam": {"teamTricode": "NYK", "players": [{"personId": 2, "name": "Player B"}]}}}
    monkeypatch.setattr(nba_data, "_get_json", lambda _: sample)
    players = nba_data.game_players("123")
    assert [(p["team"], p["opponent"]) for p in players] == [("BOS", "NYK"), ("NYK", "BOS")]

def test_rejects_invalid_game_id():
    with pytest.raises(nba_data.NBADataError):
        nba_data.game_players("../bad")


def test_wrong_game_boxscore_is_rejected(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {"game": {"gameId": "999"}})
    with pytest.raises(nba_data.NBADataError, match="mismatch"):
        nba_data.game_players("123")


def test_missing_team_object_is_safe(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {
        "game": {"gameId": "123", "homeTeam": None,
                 "awayTeam": {"teamTricode": "BOS", "players": [
                     {"personId": 1, "name": "Test", "statistics": {}}
                 ]}}})
    result = nba_data.game_players("123")
    assert len(result) == 1
    assert result[0]["opponent"] is None


def test_malformed_live_player_entries_are_skipped(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {
        "game": {"gameId": "123",
                 "homeTeam": {"teamTricode": "BOS", "players": [None, "bad", {"personId": 1, "name": "Valid"}]},
                 "awayTeam": {"teamTricode": "NYK", "players": "invalid"}}})
    players = nba_data.game_players("123")
    assert len(players) == 1
    assert players[0]["player_id"] == 1


def test_scoreboard_skips_malformed_games(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {
        "scoreboard": {"games": [None, "bad", {"gameId": "123"}]}})
    assert nba_data.scoreboard() == [{"gameId": "123"}]


def test_scoreboard_rejects_malformed_scoreboard_object(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {"scoreboard": ["invalid"]})
    with pytest.raises(nba_data.NBADataError, match="games list"):
        nba_data.scoreboard()


def test_live_players_handle_malformed_opponent_object(monkeypatch):
    monkeypatch.setattr(nba_data, "_get_json", lambda _: {
        "game": {"gameId": "123",
                 "homeTeam": {"teamTricode": "BOS", "players": [
                     {"personId": 1, "name": "Example"}]},
                 "awayTeam": ["malformed"]}})
    players = nba_data.game_players("123")
    assert len(players) == 1
    assert players[0]["opponent"] is None


def test_live_feed_rejects_boolean_and_unicode_digit_game_ids():
    for game_id in (True, "１２３"):
        with pytest.raises(nba_data.NBADataError, match="Invalid NBA game ID"):
            nba_data.game_players(game_id)
