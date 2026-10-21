from espn_history_coverage import espn_history_coverage


def record(team, pid, gid):
    return {"team": team, "player_id": f"espn:{pid}", "game_id": f"espn:{gid}",
            "source": "ESPN verified final boxscore", "game_date": "2026-10-19",
            "points": 12, "rebounds": 4, "assists": 3, "threes": 2}


def test_coverage_counts_unique_player_games_and_missing_teams():
    rows = [record("BOS", 1, n) for n in range(1, 7)]
    rows += [record("BOS", 1, 6), record("BOS", 2, 10)]
    rows += [record("NYK", 3, 11)]
    rows[-1]["source"] = "ESPN team roster (unconfirmed)"
    result = espn_history_coverage(rows, {"BOS", "NYK"})
    assert result[0]["Historical players"] == 2
    assert result[0]["Player-game records"] == 7
    assert result[0]["Players with 5+ games"] == 1
    assert result[0]["Players with 10+ games"] == 0
    assert result[1]["Status"] == "No verified history"


def test_coverage_rejects_invalid_and_conflicting_game_records():
    valid = record("BOS", 1, 100)
    invalid = {**record("BOS", 2, 101), "points": None}
    conflict = {**valid, "points": 99}
    result = espn_history_coverage(
        [valid, invalid, conflict, valid, record("BOS", 3, 102)],
        {"BOS"},
    )
    assert result[0]["Historical players"] == 1
    assert result[0]["Player-game records"] == 1


def test_coverage_rejects_invalid_scheduled_team_codes():
    assert espn_history_coverage([], {"BOS", "bad", "BOSTON"}) == [
        {"Team": "BOS", "Historical players": 0, "Player-game records": 0,
         "Players with 5+ games": 0, "Players with 10+ games": 0,
         "Status": "No verified history"}
    ]


def test_coverage_excludes_invalid_dates_and_conflicting_dates():
    valid = record("BOS", 1, 100)
    wrong_date = {**valid, "game_date": "2026-10-18"}
    malformed = {**record("BOS", 2, 101), "game_date": "not-a-date"}
    result = espn_history_coverage(
        [valid, wrong_date, malformed, record("BOS", 3, 102)], {"BOS"}
    )
    assert result[0]["Historical players"] == 1
    assert result[0]["Player-game records"] == 1


def test_coverage_excludes_athlete_assigned_to_two_teams_in_one_game():
    rows = [
        {"player_id": "espn:9", "player": "Example", "team": team,
         "game_id": "espn:101", "game_date": "2026-10-19",
         "points": 20, "rebounds": 5, "assists": 3, "threes": 2,
         "source": "ESPN verified final boxscore"}
        for team in ("BOS", "NYK")
    ]
    coverage = espn_history_coverage(rows, {"BOS", "NYK"})
    assert len(coverage) == 2
    assert all(row["Player-game records"] == 0 for row in coverage)
    assert all(row["Historical players"] == 0 for row in coverage)


def test_coverage_excludes_other_team_when_first_team_has_conflicting_duplicates():
    original = record("BOS", 7, 100)
    conflicting = {**original, "points": 19}
    other_team = record("NYK", 7, 100)
    rows = espn_history_coverage([original, conflicting, other_team], {"BOS", "NYK"})
    assert all(row["Player-game records"] == 0 for row in rows)
    assert all(row["Historical players"] == 0 for row in rows)


def test_coverage_ignores_unhashable_provider_team_values():
    malformed = [
        {**record("BOS", 1, 10), "team": ["BOS"]},
        {**record("BOS", 2, 11), "team": {"code": "BOS"}},
    ]
    result = espn_history_coverage(
        malformed + [record("BOS", 3, 12)], {"BOS", "NYK"}
    )
    by_team = {row["Team"]: row for row in result}
    assert by_team["BOS"]["Player-game records"] == 1
    assert by_team["NYK"]["Player-game records"] == 0
