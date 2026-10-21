import pytest
from espn_history_health import espn_history_health


def test_espn_history_health_complete_collection():
    health = espn_history_health({
        "games_requested": 4, "games_loaded": 4, "dates_checked": 2,
        "failures": [], "observations": [{}, {}, {}],
    })
    assert health["Final-game success %"] == 100.0
    assert health["Verified player-game records"] == 3
    assert health["Status"] == "All requested finals loaded"


def test_espn_history_health_partial_collection():
    health = espn_history_health({
        "games_requested": 5, "games_loaded": 3, "dates_checked": 3,
        "failures": [{"error": "timeout"}], "observations": [{}],
    })
    assert health["Final-game success %"] == 60.0
    assert health["Failed final-game requests"] == 2
    assert health["Status"] == "Partial historical retrieval"


def test_espn_history_health_no_requests():
    health = espn_history_health({
        "games_requested": 0, "games_loaded": 0, "dates_checked": 7,
        "failures": [], "observations": [],
    })
    assert health["Final-game success %"] is None
    assert health["Status"] == "No final games requested"


@pytest.mark.parametrize("bad", [
    {"games_requested": 1, "games_loaded": 2, "dates_checked": 1,
     "failures": [], "observations": []},
    {"games_requested": True, "games_loaded": 0, "dates_checked": 1,
     "failures": [], "observations": []},
    {"games_requested": 1, "games_loaded": 0, "dates_checked": 1,
     "failures": "oops", "observations": []},
])
def test_espn_history_health_rejects_bad_counters(bad):
    with pytest.raises(ValueError):
        espn_history_health(bad)


def test_history_health_reports_actual_verified_date_range():
    health = espn_history_health({
        "games_requested": 3, "games_loaded": 2, "dates_checked": 5,
        "failures": [{"error": "timeout"}],
        "observations": [
            {"game_date": "2026-10-18"},
            {"game_date": "2026-10-20"},
            {"game_date": "20261019"},  # noncanonical: ignored
            {"game_date": "invalid"},
        ],
    })
    assert health["Oldest verified game"] == "2026-10-18"
    assert health["Newest verified game"] == "2026-10-20"


def test_history_health_no_verified_dates_is_explicitly_missing():
    health = espn_history_health({
        "games_requested": 0, "games_loaded": 0, "dates_checked": 1,
        "failures": [], "observations": [],
    })
    assert health["Oldest verified game"] is None
    assert health["Newest verified game"] is None


def test_health_separates_schedule_and_boxscore_failures():
    health = espn_history_health({
        "games_requested": 3, "games_loaded": 2, "dates_checked": 4,
        "failures": [
            {"date": "2026-10-19", "error": "schedule unavailable"},
            {"event_id": "123", "date": "2026-10-20", "error": "invalid final"},
        ],
        "observations": [{}],
    })
    assert health["Failed schedule dates"] == 1
    assert health["Failed boxscore validations"] == 1
    assert health["Status"] == "Partial historical retrieval"


def test_schedule_outage_without_requested_games_is_not_clean_empty_history():
    health = espn_history_health({
        "games_requested": 0, "games_loaded": 0, "dates_checked": 2,
        "failures": [{"date": "2026-10-19", "error": "network outage"}],
        "observations": [],
    })
    assert health["Status"] == "Schedule retrieval errors; no finals requested"
    assert health["Failed schedule dates"] == 1


def test_schedule_coverage_counts_unique_failed_dates():
    health = espn_history_health({
        "games_requested": 2, "games_loaded": 1, "dates_checked": 4,
        "failures": [
            {"date": "2026-10-20", "error": "scoreboard unavailable"},
            {"date": "2026-10-20", "error": "duplicate error report"},
            {"date": "2026-10-19", "event_id": "100", "error": "invalid final"},
        ],
        "observations": [{}],
    })
    assert health["Schedule dates usable"] == 3
    assert health["Schedule coverage %"] == 75.0
    assert health["Final-game success %"] == 50.0


def test_zero_scanned_days_have_no_schedule_coverage_percentage():
    health = espn_history_health({
        "games_requested": 0, "games_loaded": 0, "dates_checked": 0,
        "failures": [], "observations": [],
    })
    assert health["Schedule dates usable"] == 0
    assert health["Schedule coverage %"] is None


def test_undated_schedule_failure_does_not_claim_complete_coverage():
    health = espn_history_health({
        "games_requested": 1, "games_loaded": 1, "dates_checked": 4,
        "failures": [{"error": "scoreboard timeout"}],
        "observations": [],
    })
    assert health["Schedule dates usable"] is None
    assert health["Schedule coverage %"] is None
    assert health["Status"] == "Partial historical retrieval"


def test_dated_schedule_failure_preserves_measurable_coverage():
    health = espn_history_health({
        "games_requested": 1, "games_loaded": 1, "dates_checked": 4,
        "failures": [{"date": "2026-10-20", "error": "scoreboard timeout"}],
        "observations": [],
    })
    assert health["Schedule dates usable"] == 3
    assert health["Schedule coverage %"] == 75.0
