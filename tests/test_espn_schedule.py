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


def test_duplicate_espn_matchups_are_not_listed_twice():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            event = {"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "NY"}},
                {"homeAway": "away", "team": {"abbreviation": "BOS"}},
            ]}]}
            return {"events": [event, event]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        games = espn_games_on("2026-10-21")
    assert len(games) == 1
    assert games[0]["homeTeam"]["teamTricode"] == "NYK"


def test_espn_fallback_reads_scores_without_fabricating_missing_scores():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "BOS"}, "score": "108"},
                {"homeAway": "away", "team": {"abbreviation": "NY"}, "score": "102"},
            ]}]}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        game = espn_games_on("2026-10-21")[0]
    assert game["homeScore"] == 108
    assert game["awayScore"] == 102


def test_espn_fallback_does_not_turn_missing_scores_into_zero():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "BOS"}},
                {"homeAway": "away", "team": {"abbreviation": "NY"}, "score": "N/A"},
            ]}]}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        game = espn_games_on("2026-10-21")[0]
    assert game["homeScore"] is None
    assert game["awayScore"] is None


def test_espn_team_ids_remain_separate_from_nba_game_ids():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"id": "401555555", "competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "NY", "id": "18"}},
                {"homeAway": "away", "team": {"abbreviation": "BOS", "id": "2"}},
            ]}]}]}
    with patch("espn_schedule.requests.get", return_value=Response()):
        game = espn_games_on("2026-10-21")[0]
    assert game["gameId"] is None
    assert game["espnEventId"] == "401555555"
    assert game["espnTeamIds"] == {"home": "18", "away": "2"}


def test_espn_team_ids_available_even_if_event_id_is_missing():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "NY", "id": "18"}},
                {"homeAway": "away", "team": {"abbreviation": "BOS", "id": "2"}},
            ]}]}]}
    with patch("espn_schedule.requests.get", return_value=Response()):
        game = espn_games_on("2026-10-21")[0]
    assert game["espnEventId"] is None
    assert game["espnTeamIds"]["home"] == "18"


def test_distinct_espn_events_with_same_matchup_are_preserved():
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            event = {"competitions": [{"competitors": [
                {"homeAway": "home", "team": {"abbreviation": "BOS"}},
                {"homeAway": "away", "team": {"abbreviation": "NY"}},
            ]}]}
            return {"events": [{**event, "id": "40101"}, {**event, "id": "40102"},
                               {**event, "id": "40101"}]}

    with patch("espn_schedule.requests.get", return_value=Response()):
        games = espn_games_on("2026-10-21")
    assert [game["espnEventId"] for game in games] == ["40101", "40102"]
