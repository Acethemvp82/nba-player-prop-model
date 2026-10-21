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
