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
