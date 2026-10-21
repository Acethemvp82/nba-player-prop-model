from unittest.mock import patch
import pytest
from nba_data import NBADataError
from espn_schedule import espn_games_on


def test_espn_schedule_maps_matchup_without_reusing_espn_game_id():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{
                "id": "401234567",
                "date": "2026-10-21T23:00Z",
                "competitions": [{"competitors": [
                    {"homeAway": "home", "team": {"abbreviation": "BOS"}},
                    {"homeAway": "away", "team": {"abbreviation": "NYK"}},
                ]}],
                "status": {"type": {"description": "Scheduled"}},
            }]}

    with patch("espn_schedule.requests.get", return_value=Response()) as get:
        games = espn_games_on("2026-10-21")
    assert get.call_args.kwargs["params"] == {"dates": "20261021"}
    assert games[0]["gameId"] is None
    assert games[0]["homeTeam"]["teamTricode"] == "BOS"
    assert games[0]["awayTeam"]["teamTricode"] == "NYK"


def test_espn_schedule_ignores_malformed_events():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [None, {}, {"competitions": []}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        assert espn_games_on("2026-10-21") == []


def test_espn_schedule_reports_invalid_payload():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": None}

    with patch("espn_schedule.requests.get", return_value=Response()):
        with pytest.raises(NBADataError):
            espn_games_on("2026-10-21")


def test_espn_short_team_codes_are_normalized():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "NY"}},
                {"homeAway": "away", "team": {"abbreviation": "GS"}},
            ]}]}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        games = espn_games_on("2026-10-21")
    assert len(games) == 1
    assert games[0]["homeTeam"]["teamTricode"] == "NYK"
    assert games[0]["awayTeam"]["teamTricode"] == "GSW"


def test_espn_invalid_team_abbreviations_are_excluded():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "12A"}},
                {"homeAway": "away", "team": {"abbreviation": "BOS"}},
            ]}]}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        assert espn_games_on("2026-10-21") == []
