from unittest.mock import patch
import pytest
from espn_players import espn_game_players, espn_team_roster
from nba_data import NBADataError


def test_espn_player_ids_are_namespaced_and_not_nba_ids():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"boxscore": {"players": [{"team": {"abbreviation": "NY"},
                "statistics": [{"athletes": [
                    {"athlete": {"id": "123", "displayName": "Test Player"}},
                    {"athlete": {"id": "123", "displayName": "Test Player"}},
                ]}]}]}}
    with patch("espn_players.requests.get", return_value=Response()):
        players = espn_game_players("401234567")
    assert len(players) == 1
    assert players[0]["player_id"] == "espn:123"
    assert players[0]["team"] == "NYK"


def test_missing_espn_player_listing_is_explicit():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"boxscore": {}}
    with patch("espn_players.requests.get", return_value=Response()):
        with pytest.raises(NBADataError):
            espn_game_players("401234567")


def test_invalid_espn_event_ids_are_rejected():
    for value in (True, "１２３", "invalid", None):
        with pytest.raises(NBADataError):
            espn_game_players(value)


def test_empty_espn_athlete_groups_are_reported_unavailable():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"boxscore": {"players": [
                {"team": {"abbreviation": "BOS"},
                 "statistics": [{"athletes": []}]}
            ]}}

    with patch("espn_players.requests.get", return_value=Response()):
        with pytest.raises(NBADataError, match="no usable player listings"):
            espn_game_players("401234567")


def test_espn_team_roster_accepts_grouped_positions_and_deduplicates():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"team": {"abbreviation": "NY"}, "athletes": [
                {"position": "Guard", "items": [
                    {"id": "12", "displayName": "Sample Guard"},
                    {"id": "12", "displayName": "Sample Guard"},
                ]},
                {"position": "Forward", "items": [
                    {"id": "13", "displayName": "Sample Forward"},
                ]},
            ]}
    with patch("espn_players.requests.get", return_value=Response()):
        players = espn_team_roster("18", "NYK")
    assert [p["player_id"] for p in players] == ["espn:12", "espn:13"]
    assert all(p["source"] == "ESPN team roster (unconfirmed)" for p in players)


def test_espn_team_roster_rejects_wrong_team():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"team": {"abbreviation": "BOS"}, "athletes": [
                {"id": "12", "displayName": "Sample Player"}
            ]}
    with patch("espn_players.requests.get", return_value=Response()):
        with pytest.raises(NBADataError, match="does not match"):
            espn_team_roster("18", "NYK")


def test_espn_team_roster_accepts_flat_athlete_list():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"team": {"abbreviation": "BOS"}, "athletes": [
                {"id": "501", "displayName": "First Player"},
                {"id": "502", "displayName": "Second Player"},
            ]}
    with patch("espn_players.requests.get", return_value=Response()):
        players = espn_team_roster("2", "BOS")
    assert [p["player_id"] for p in players] == ["espn:501", "espn:502"]


def test_espn_team_roster_rejects_invalid_identifiers():
    for team_id in (True, None, "１２", "../2"):
        with pytest.raises(NBADataError, match="Invalid ESPN team ID"):
            espn_team_roster(team_id, "BOS")
