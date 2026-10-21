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
