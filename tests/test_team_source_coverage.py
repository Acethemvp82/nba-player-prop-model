from team_source_coverage import team_source_coverage


def test_team_coverage_shows_missing_teams_and_deduplicates_players():
    rows = [
        {"team": "NYK", "player_id": "espn:1", "source": "ESPN team roster (unconfirmed)"},
        {"team": "NYK", "player_id": "espn:1", "source": "ESPN team roster (unconfirmed)"},
        {"team": "NYK", "player_id": "espn:2", "source": "ESPN game summary (unconfirmed)"},
        {"team": "BOS", "player_id": None, "source": "NBA game feed"},
    ]
    result = team_source_coverage(rows, {"BOS", "NYK"})
    assert result[0]["Team"] == "BOS"
    assert result[0]["Listed players"] == 0
    assert result[0]["Status"] == "No listings"
    assert result[1]["Listed players"] == 2
    assert "ESPN team roster" in result[1]["Data sources"]
    assert "ESPN game summary" in result[1]["Data sources"]


def test_team_coverage_ignores_unscheduled_and_invalid_entries():
    result = team_source_coverage([
        None, {"team": "LAL", "player_id": "1", "source": "NBA game feed"},
        {"team": "BOS", "player_id": True, "source": "NBA game feed"},
    ], {"BOS"})
    assert result[0]["Listed players"] == 0
