"""Deterministic tests for the opt-in ESPN network probe."""
from datetime import date

from scripts.espn_live_probe import check_recent_finals


def game(event_id):
    return {"espnCompleted": True, "espnEventId": event_id}


def verified_player():
    return {"player_id": "espn:5", "player": "Example", "team": "BOS",
            "points": 20, "rebounds": 6, "assists": 4, "threes": 2,
            "source": "ESPN verified final boxscore"}


def test_probe_retries_failed_final_and_uses_next_valid_game():
    requested = []

    def schedule(day):
        return [game("100"), game("101")]

    def boxscore(event_id):
        requested.append(event_id)
        if event_id == "100":
            raise ValueError("Bad summary")
        return [verified_player()]

    result = check_recent_finals(date(2026, 10, 21), days=1,
                                 schedule_loader=schedule, boxscore_loader=boxscore)
    assert result["date"] == "2026-10-20"
    assert result["event_id"] == "101"
    assert result["players"] == 1
    assert result["completed"] == 2
    assert len(result["errors"]) == 1
    assert requested == ["100", "101"]


def test_probe_reports_schedule_failure_and_continues():
    def schedule(day):
        if day == "2026-10-20":
            raise ValueError("Schedule unavailable")
        return [game("102")]

    result = check_recent_finals(date(2026, 10, 21), days=2,
                                 schedule_loader=schedule,
                                 boxscore_loader=lambda _: [verified_player()])
    assert result["event_id"] == "102"
    assert len(result["errors"]) == 1


def test_probe_reports_missing_final_games():
    result = check_recent_finals(date(2026, 10, 21), days=2,
                                 schedule_loader=lambda _: [],
                                 boxscore_loader=lambda _: [])
    assert result["players"] == 0
    assert result["completed"] == 0


def test_probe_skips_invalid_event_ids():
    requested = []
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game(None), game("not-an-id"), game("103")],
        boxscore_loader=lambda eid: requested.append(eid) or [verified_player()],
    )
    assert requested == ["103"]
    assert result["event_id"] == "103"


def test_probe_handles_malformed_schedule_collection():
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: {"games": []},
        boxscore_loader=lambda _: [],
    )
    assert result["players"] == 0
    assert "invalid game collection" in result["errors"][0]


def test_probe_respects_boxscore_attempt_limit():
    requested = []
    result = check_recent_finals(
        date(2026, 10, 21), days=3, max_attempts=2,
        schedule_loader=lambda _: [game("101"), game("102"), game("103")],
        boxscore_loader=lambda eid: requested.append(eid) or [],
    )
    assert requested == ["101", "102"]
    assert result["completed"] == 2
    assert result["players"] == 0


def test_probe_rejects_invalid_request_budget():
    import pytest

    with pytest.raises(ValueError, match="max_attempts"):
        check_recent_finals(date(2026, 10, 21), max_attempts=0)
    with pytest.raises(ValueError, match="max_attempts"):
        check_recent_finals(date(2026, 10, 21), max_attempts=True)


def test_probe_does_not_pass_on_unverified_boxscore_rows():
    unverified = {**verified_player(), "source": "ESPN team roster (unconfirmed)"}
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player(), unverified],
    )
    assert result["players"] == 0
    assert result["completed"] == 1
    assert "Unverified or invalid" in result["errors"][0]


def test_probe_rejects_player_from_wrong_matchup():
    scheduled = {**game("101"), "homeTeam": {"teamTricode": "NYK"},
                 "awayTeam": {"teamTricode": "LAL"}}
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [scheduled],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "does not match scheduled game" in result["errors"][0]


def test_probe_rejects_duplicate_player_rows():
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player(), verified_player()],
    )
    assert result["players"] == 0
    assert "Duplicate player" in result["errors"][0]


def test_probe_accepts_valid_scheduled_matchup():
    scheduled = {**game("101"), "homeTeam": {"teamTricode": "BOS"},
                 "awayTeam": {"teamTricode": "NYK"}}
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [scheduled],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 1


def test_probe_rejects_invalid_lookback_days():
    import pytest

    for days in (0, 31, True, 1.5):
        with pytest.raises(ValueError, match="days"):
            check_recent_finals(date(2026, 10, 21), days=days)


def test_probe_requires_successful_historical_collection(monkeypatch):
    import scripts.espn_live_probe as probe

    def failed_collection(*args, **kwargs):
        return {"games_loaded": 0, "observations": [],
                "failures": [{"error": "collector rejected data"}]}

    monkeypatch.setattr(probe, "collect_espn_history", failed_collection)
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "history collector rejected" in result["errors"][0]


def test_probe_requires_averages_to_include_all_verified_players(monkeypatch):
    import scripts.espn_live_probe as probe

    monkeypatch.setattr(probe, "espn_player_averages", lambda *args: [])
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "averages or recent trends" in result["errors"][0]


def test_probe_requires_trends_to_include_all_verified_players(monkeypatch):
    import scripts.espn_live_probe as probe

    monkeypatch.setattr(probe, "espn_recent_trends", lambda *args: {})
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "averages or recent trends" in result["errors"][0]


def test_probe_requires_valid_averages_and_trends(monkeypatch):
    import scripts.espn_live_probe as probe

    monkeypatch.setattr(probe, "espn_player_averages", lambda *args: [])
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "averages or recent trends" in result["errors"][0]


def test_probe_accepts_final_through_full_statistics_pipeline():
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 1
    assert result["errors"] == []


def test_probe_rejects_changed_historical_average(monkeypatch):
    import scripts.espn_live_probe as probe

    real_averages = probe.espn_player_averages

    def changed_averages(*args):
        rows = real_averages(*args)
        rows[0]["Points avg"] += 1
        return rows

    monkeypatch.setattr(probe, "espn_player_averages", changed_averages)
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "averages changed player totals" in result["errors"][0]


def test_probe_rejects_changed_recent_trend(monkeypatch):
    import scripts.espn_live_probe as probe

    real_trends = probe.espn_recent_trends

    def changed_trends(*args):
        rows = real_trends(*args)
        rows[("espn:5", "BOS")]["points L5 avg"] += 1
        return rows

    monkeypatch.setattr(probe, "espn_recent_trends", changed_trends)
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["players"] == 0
    assert "trends changed player totals" in result["errors"][0]


def test_probe_rejects_malformed_schedule_day_without_requesting_boxscore():
    requested = []
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101"), None],
        boxscore_loader=lambda eid: requested.append(eid) or [verified_player()],
    )
    assert result["players"] == 0
    assert requested == []
    assert "malformed game entry" in result["errors"][0]


def test_probe_reports_invalid_completed_event_before_valid_final():
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game(None), game("101")],
        boxscore_loader=lambda _: [verified_player()],
    )
    assert result["event_id"] == "101"
    assert "invalid ESPN event ID" in result["errors"][0]


def test_probe_rejects_cross_team_duplicate_athlete():
    second = dict(verified_player(), team="NYK")
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [verified_player(), second],
    )
    assert result["players"] == 0
    assert "opposing teams" in result["errors"][0]


def test_probe_rejects_missing_player_name():
    unnamed = dict(verified_player(), player=" ")
    result = check_recent_finals(
        date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game("101")],
        boxscore_loader=lambda _: [unnamed],
    )
    assert result["players"] == 0
    assert "invalid player observation" in result["errors"][0]


def test_probe_rejects_threes_greater_than_possible_points():
    row = dict(verified_player(), points=8, threes=3)
    result = check_recent_finals(date(2026, 10, 21), days=1,
        schedule_loader=lambda _: [game('101')],
        boxscore_loader=lambda _: [row])
    assert result['players'] == 0
    assert 'three-pointers exceed recorded points' in result['errors'][0]
