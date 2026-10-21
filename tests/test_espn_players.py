from unittest.mock import patch
import pytest
from espn_players import espn_game_players
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
