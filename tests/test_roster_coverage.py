from roster_coverage import roster_coverage


def test_roster_coverage_independent_of_prop_rows():
    players = [
        {"player_id": 1, "team": "NYK", "source": "NBA game feed"},
        {"player_id": 1, "team": "NYK", "source": "NBA game feed"},
        {"player_id": 2, "team": "BOS", "source": "Historical candidate"},
    ]
    result = roster_coverage(players, {"NYK", "BOS", "MIA"})
    assert result == {"scheduled_teams": 3, "represented_teams": 2,
                      "missing_teams": ["MIA"], "players": 2,
                      "feed_players": 1, "historical_candidates": 1}


def test_unscheduled_teams_do_not_inflate_coverage():
    result = roster_coverage(
        [{"player_id": 4, "team": "MIA", "source": "NBA game feed"}],
        {"NYK", "BOS"})
    assert result["represented_teams"] == 0
    assert result["missing_teams"] == ["BOS", "NYK"]


def test_duplicate_historical_candidate_does_not_override_feed():
    result = roster_coverage([
        {"player_id": 5, "team": "BOS", "source": "NBA game feed"},
        {"player_id": 5, "team": "BOS", "source": "Historical candidate"},
    ], {"BOS"})
    assert result["players"] == 1
    assert result["feed_players"] == 1
    assert result["historical_candidates"] == 0


def test_malformed_roster_entries_are_ignored():
    players = [
        None, "invalid", {"player_id": 3, "team": "BOS", "source": "NBA game feed"},
        {"player_id": None, "team": "NYK", "source": "NBA game feed"},
        {"player_id": 4, "team": "NYK", "source": "Historical candidate"},
    ]
    result = roster_coverage(players, {"BOS", "NYK"})
    assert result["players"] == 2
    assert result["feed_players"] == 1
    assert result["historical_candidates"] == 1
    assert result["missing_teams"] == []
