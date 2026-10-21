"""Offline tests for bounded ESPN history retrieval and final-only observations."""
from nba_data import NBADataError
from espn_history import collect_espn_history


def game(event_id):
    return {"espnEventId": event_id}


def player():
    return {"player_id": "espn:9", "player": "Example", "team": "BOS",
            "points": 22, "rebounds": 7, "assists": 4, "threes": 2,
            "minutes": 30.0, "is_final": True,
            "source": "ESPN verified final boxscore"}


def test_history_excludes_slate_day_and_caps_requests():
    checked = []
    def schedule(day):
        checked.append(day)
        return [game("100"), game("101")]
    fetched = []
    def boxscore(event_id):
        fetched.append(event_id)
        return [player()]
    result = collect_espn_history("2026-10-21", days=3, max_games=1,
                                  schedule_loader=schedule, boxscore_loader=boxscore)
    assert checked == ["2026-10-20", "2026-10-19", "2026-10-18"]
    assert fetched == ["100"]
    assert result["games_loaded"] == 1
    assert result["dates_checked"] == 3
    assert result["request_limit_reached"] is True
    assert result["eligible_games_omitted"] == 1
    assert result["history_truncated"] is True
    assert result["observations"][0]["game_date"] == "2026-10-20"
    assert result["observations"][0]["game_id"] == "espn:100"


def test_history_reports_failed_boxscore_without_inventing_zero_stats():
    result = collect_espn_history("2026-10-21", days=1, max_games=2,
                                  schedule_loader=lambda _: [game("100"), game("101")],
                                  boxscore_loader=lambda eid: (_ for _ in ()).throw(
                                      NBADataError("not final")) if eid == "100" else [player()])
    assert result["games_requested"] == 2
    assert result["games_loaded"] == 1
    assert len(result["failures"]) == 1
    assert len(result["observations"]) == 1


def test_history_deduplicates_events_across_dates():
    result = collect_espn_history("2026-10-21", days=3, max_games=5,
                                  schedule_loader=lambda _: [game("100")],
                                  boxscore_loader=lambda _: [player()])
    assert result["games_requested"] == 1
    assert len(result["observations"]) == 1


def test_nonfinite_minutes_never_enter_verified_history():
    for minutes in (float("nan"), float("inf"), float("-inf")):
        bad = {**player(), "minutes": minutes}
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=1,
            schedule_loader=lambda _: [game("100")],
            boxscore_loader=lambda _: [bad])
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1


def test_unverified_player_rows_do_not_count_as_loaded_games():
    bad = player()
    bad["source"] = "ESPN team roster (unconfirmed)"
    result = collect_espn_history("2026-10-21", days=1, max_games=1,
                                  schedule_loader=lambda _: [game("100")],
                                  boxscore_loader=lambda _: [bad])
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1


def test_explicitly_unfinished_games_do_not_consume_boxscore_budget():
    fetched = []
    def fetch(eid):
        fetched.append(eid)
        return [player()]
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [
            {"espnEventId": "100", "espnCompleted": False},
            {"espnEventId": "101", "espnCompleted": True}],
        boxscore_loader=fetch)
    assert fetched == ["101"]
    assert result["games_requested"] == 1
    assert result["games_loaded"] == 1


def test_unknown_finality_still_requires_verified_boxscore():
    fetched = []
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [{"espnEventId": "100", "espnCompleted": None}],
        boxscore_loader=lambda eid: fetched.append(eid) or [player()])
    assert fetched == ["100"]
    assert result["games_loaded"] == 1


def test_missing_player_name_or_invalid_team_never_loads():
    for changes in ({"player": ""}, {"team": "XX"}, {"team": "bos"},
                    {"player": None}, {"team": None}):
        bad = {**player(), **changes}
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=1,
            schedule_loader=lambda _: [game("100")],
            boxscore_loader=lambda _: [bad])
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1


def test_repeated_athlete_rows_count_as_one_player_game():
    first = player()
    duplicate = {**first}
    second = {**first, "player_id": "espn:10", "player": "Other"}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [game("100")],
        boxscore_loader=lambda _: [first, duplicate, second])
    assert result["games_loaded"] == 1
    assert len(result["observations"]) == 2
    assert {item["player_id"] for item in result["observations"]} == {"espn:9", "espn:10"}


def test_history_rejects_game_with_players_from_unrelated_teams():
    matchup = {"espnEventId": "100",
               "homeTeam": {"teamTricode": "BOS"},
               "awayTeam": {"teamTricode": "NYK"}}
    unrelated = {**player(), "team": "MIA"}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [matchup],
        boxscore_loader=lambda _: [player(), unrelated])
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "outside scheduled matchup" in result["failures"][0]["error"]


def test_history_rejects_game_when_no_players_match_scheduled_teams():
    matchup = {"espnEventId": "100",
               "homeTeam": {"teamTricode": "BOS"},
               "awayTeam": {"teamTricode": "NYK"}}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [matchup],
        boxscore_loader=lambda _: [{**player(), "team": "MIA"}])
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1


def test_history_rejects_identical_or_malformed_matchup_teams():
    for away_code in ("BOS", "XX", "nyk", None):
        matchup = {"espnEventId": "100",
                   "homeTeam": {"teamTricode": "BOS"},
                   "awayTeam": {"teamTricode": away_code}}
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=1,
            schedule_loader=lambda _: [matchup],
            boxscore_loader=lambda _: [player()])
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1


def test_history_rejects_partially_missing_matchup_metadata():
    for matchup in (
        {"homeTeam": {"teamTricode": "BOS"}},
        {"awayTeam": {"teamTricode": "NYK"}},
        {"homeTeam": {"teamTricode": "BOS"}, "awayTeam": {}},
        {"homeTeam": None, "awayTeam": {"teamTricode": "NYK"}},
    ):
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=1,
            schedule_loader=lambda _: [{"espnEventId": "100", **matchup}],
            boxscore_loader=lambda _: [player()])
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1


def test_conflicting_duplicate_athlete_stats_reject_entire_game():
    original = player()
    conflicting = {**original, "points": original["points"] + 1}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [game("100")],
        boxscore_loader=lambda _: [original, conflicting])
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "Conflicting ESPN stats" in result["failures"][0]["error"]


def test_same_espn_athlete_cannot_play_for_both_teams_in_one_game():
    matchup = {"espnEventId": "100",
               "homeTeam": {"teamTricode": "BOS"},
               "awayTeam": {"teamTricode": "NYK"}}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [matchup],
        boxscore_loader=lambda _: [player(), {**player(), "team": "NYK"}])
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "both teams" in result["failures"][0]["error"]


def test_history_rejects_mixed_verified_and_unverified_player_rows():
    invalid = {**player(), "player_id": "espn:10",
               "source": "ESPN team roster (unconfirmed)"}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [game("100")],
        boxscore_loader=lambda _: [player(), invalid],
    )
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "unverified player rows" in result["failures"][0]["error"]


def test_history_rejects_entire_game_with_unrelated_team_player():
    scheduled = {**game("100"), "homeTeam": {"teamTricode": "BOS"},
                 "awayTeam": {"teamTricode": "NYK"}}
    unrelated = {**player(), "player_id": "espn:10", "team": "LAL"}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [scheduled],
        boxscore_loader=lambda _: [player(), unrelated],
    )
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "outside scheduled matchup" in result["failures"][0]["error"]


def test_history_continues_after_network_boxscore_failure():
    import requests

    result = collect_espn_history(
        "2026-10-21", days=1, max_games=2,
        schedule_loader=lambda _: [game("100"), game("101")],
        boxscore_loader=lambda eid: (_ for _ in ()).throw(
            requests.Timeout("ESPN timeout")) if eid == "100" else [player()],
    )
    assert result["games_requested"] == 2
    assert result["games_loaded"] == 1
    assert len(result["observations"]) == 1
    assert len(result["failures"]) == 1
    assert "timeout" in result["failures"][0]["error"]


def test_history_continues_after_network_schedule_failure():
    import requests

    def schedule(day):
        if day == "2026-10-20":
            raise requests.ConnectionError("ESPN unavailable")
        return [game("101")]

    result = collect_espn_history(
        "2026-10-21", days=2, max_games=2,
        schedule_loader=schedule,
        boxscore_loader=lambda _: [player()],
    )
    assert result["dates_checked"] == 2
    assert result["games_loaded"] == 1
    assert len(result["failures"]) == 1


def test_malformed_scoreboard_day_is_reported_without_partial_collection():
    fetched = []
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=3,
        schedule_loader=lambda _: [game("100"), None, game("101")],
        boxscore_loader=lambda event_id: fetched.append(event_id) or [player()],
    )
    assert fetched == []
    assert result["games_requested"] == 0
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "Malformed schedule" in result["failures"][0]["error"]


def test_empty_espn_scoreboard_day_is_valid_off_day():
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=3,
        schedule_loader=lambda _: [],
        boxscore_loader=lambda _: (_ for _ in ()).throw(AssertionError("no games")),
    )
    assert result["dates_checked"] == 1
    assert result["games_requested"] == 0
    assert result["failures"] == []


def test_invalid_schedule_event_id_reports_missing_history():
    for invalid_id in (None, "", "bad", "12a", 100, True):
        fetched = []
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=3,
            schedule_loader=lambda _, invalid_id=invalid_id: [
                game("100"), game(invalid_id)],
            boxscore_loader=lambda eid: fetched.append(eid) or [player()],
        )
        assert fetched == []
        assert result["games_requested"] == 0
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1
        assert "Invalid schedule event ID" in result["failures"][0]["error"]


def test_valid_schedule_event_ids_still_load():
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=2,
        schedule_loader=lambda _: [game("100"), game("101")],
        boxscore_loader=lambda _: [player()],
    )
    assert result["games_loaded"] == 2
    assert result["failures"] == []


def test_duplicate_schedule_event_ids_reject_entire_date():
    fetched = []
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=3,
        schedule_loader=lambda _: [game("100"), game("101"), game("100")],
        boxscore_loader=lambda eid: fetched.append(eid) or [player()],
    )
    assert fetched == []
    assert result["games_requested"] == 0
    assert result["games_loaded"] == 0
    assert result["observations"] == []
    assert len(result["failures"]) == 1
    assert "Duplicate schedule event ID" in result["failures"][0]["error"]


def test_repeated_event_on_different_dates_still_counts_once():
    result = collect_espn_history(
        "2026-10-21", days=2, max_games=5,
        schedule_loader=lambda _: [game("100")],
        boxscore_loader=lambda _: [player()],
    )
    assert result["games_requested"] == 1
    assert result["games_loaded"] == 1
    assert result["failures"] == []


def test_invalid_scoreboard_matchup_rejects_entire_date():
    for bad_game in (
        {"espnEventId": "101", "homeTeam": {"teamTricode": "BOS"}},
        {"espnEventId": "101", "homeTeam": {"teamTricode": "BOS"},
         "awayTeam": {"teamTricode": "BOS"}},
        {"espnEventId": "101", "homeTeam": {"teamTricode": "bos"},
         "awayTeam": {"teamTricode": "NYK"}},
    ):
        fetched = []
        result = collect_espn_history(
            "2026-10-21", days=1, max_games=3,
            schedule_loader=lambda _, bad_game=bad_game: [game("100"), bad_game],
            boxscore_loader=lambda eid: fetched.append(eid) or [player()],
        )
        assert fetched == []
        assert result["games_requested"] == 0
        assert result["games_loaded"] == 0
        assert result["observations"] == []
        assert len(result["failures"]) == 1
        assert "schedule matchup" in result["failures"][0]["error"]


def test_valid_scoreboard_matchup_still_loads():
    scheduled = {"espnEventId": "100",
                 "homeTeam": {"teamTricode": "BOS"},
                 "awayTeam": {"teamTricode": "NYK"}}
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [scheduled],
        boxscore_loader=lambda _: [player()],
    )
    assert result["games_loaded"] == 1
    assert result["failures"] == []


def test_request_budget_counts_distinct_omitted_games_across_all_dates():
    fixtures = {
        "2026-10-20": [game("100"), game("101")],
        "2026-10-19": [game("101"), game("102")],
        "2026-10-18": [game("103"), game("104")],
    }
    fetched = []
    result = collect_espn_history(
        "2026-10-21", days=3, max_games=2,
        schedule_loader=lambda day: fixtures[day],
        boxscore_loader=lambda eid: fetched.append(eid) or [player()],
    )
    assert fetched == ["100", "101"]
    assert result["dates_checked"] == 3
    assert result["games_requested"] == 2
    assert result["eligible_games_omitted"] == 3
    assert result["request_limit_reached"] is True
    assert result["failures"] == []


def test_exact_request_cap_without_other_games_is_not_truncated():
    result = collect_espn_history(
        "2026-10-21", days=2, max_games=2,
        schedule_loader=lambda day: [game("100"), game("101")]
        if day == "2026-10-20" else [],
        boxscore_loader=lambda _: [player()],
    )
    assert result["dates_checked"] == 2
    assert result["games_requested"] == 2
    assert result["request_limit_reached"] is True
    assert result["eligible_games_omitted"] == 0
    assert result["history_truncated"] is False


def test_unfinished_games_do_not_count_as_omitted():
    result = collect_espn_history(
        "2026-10-21", days=1, max_games=1,
        schedule_loader=lambda _: [
            game("100"),
            {"espnEventId": "101", "espnCompleted": False},
        ],
        boxscore_loader=lambda _: [player()],
    )
    assert result["games_requested"] == 1
    assert result["eligible_games_omitted"] == 0
    assert result["history_truncated"] is False


def test_schedule_failure_after_cap_is_still_reported():
    checked = []
    def schedule(day):
        checked.append(day)
        if day == "2026-10-19":
            raise OSError("scoreboard unavailable")
        return [game("100")] if day == "2026-10-20" else []
    result = collect_espn_history(
        "2026-10-21", days=3, max_games=1,
        schedule_loader=schedule,
        boxscore_loader=lambda _: [player()],
    )
    assert checked == ["2026-10-20", "2026-10-19", "2026-10-18"]
    assert result["dates_checked"] == 3
    assert result["games_requested"] == 1
    assert result["eligible_games_omitted"] == 0
    assert result["history_truncated"] is False
    assert len(result["failures"]) == 1
    assert result["failures"][0]["date"] == "2026-10-19"
