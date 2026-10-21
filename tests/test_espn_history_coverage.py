from espn_history_coverage import espn_history_coverage


def record(team, pid, gid):
    return {"team": team, "player_id": f"espn:{pid}", "game_id": f"espn:{gid}",
            "source": "ESPN verified final boxscore",
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
