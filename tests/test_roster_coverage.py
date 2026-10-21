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


def test_invalid_player_identifiers_do_not_inflate_roster_coverage():
    players = [
        {"player_id": True, "team": "BOS", "source": "NBA game feed"},
        {"player_id": "１２３", "team": "BOS", "source": "NBA game feed"},
        {"player_id": "unknown", "team": "BOS", "source": "NBA game feed"},
        {"player_id": 123, "team": "NYK", "source": "NBA game feed"},
    ]
    result = roster_coverage(players, {"BOS", "NYK"})
    assert result["players"] == 1
    assert result["missing_teams"] == ["BOS"]


def test_namespaced_espn_players_count_as_unconfirmed_feed_listings():
    result = roster_coverage([
        {"player_id": "espn:123", "team": "NYK",
         "source": "ESPN game summary (unconfirmed)"},
        {"player_id": "espn:123", "team": "NYK",
         "source": "ESPN game summary (unconfirmed)"},
        {"player_id": 77, "team": "BOS", "source": "NBA game feed"},
    ], {"NYK", "BOS"})
    assert result["represented_teams"] == 2
    assert result["players"] == 2
    assert result["feed_players"] == 2
    assert result["historical_candidates"] == 0


def test_untrusted_espn_ids_do_not_inflate_coverage():
    result = roster_coverage([
        {"player_id": "espn:１２３", "team": "NYK",
         "source": "ESPN game summary (unconfirmed)"},
        {"player_id": "espn:abc", "team": "NYK",
         "source": "ESPN game summary (unconfirmed)"},
        {"player_id": "123", "team": "NYK",
         "source": "ESPN game summary (unconfirmed)"},
    ], {"NYK"})
    assert result["players"] == 0
    assert result["missing_teams"] == ["NYK"]
