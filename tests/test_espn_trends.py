from espn_trends import espn_recent_trends


def row(day, gid, pts):
    return {"source": "ESPN verified final boxscore", "player_id": "espn:12",
            "team": "BOS", "game_id": f"espn:{gid}", "game_date": day,
            "points": pts, "rebounds": 5, "assists": 3, "threes": 2}


def test_trends_use_latest_unique_completed_games():
    rows = [row("2026-10-17", "101", 10), row("2026-10-18", "102", 20),
            row("2026-10-19", "103", 30), row("2026-10-19", "103", 30),
            row("2026-10-21", "104", 100)]
    trend = espn_recent_trends(rows, "2026-10-21")[("espn:12", "BOS")]
    assert trend["Sample games"] == 3
    assert trend["Available last 5 games"] == 3
    assert trend["points L5 avg"] == 20
    assert trend["points L10 avg"] == 20


def test_unverified_and_invalid_rows_are_excluded():
    bad = row("2026-10-19", "103", 20)
    bad["source"] = "ESPN team roster (unconfirmed)"
    assert espn_recent_trends([bad], "2026-10-21") == {}
