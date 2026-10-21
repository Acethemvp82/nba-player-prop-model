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


def test_conflicting_duplicate_game_is_excluded_from_trends():
    rows = [row("2026-10-17", "101", 10),
            row("2026-10-18", "102", 20),
            row("2026-10-18", "102", 99),
            row("2026-10-18", "102", 20)]
    trend = espn_recent_trends(rows, "2026-10-21")[("espn:12", "BOS")]
    assert trend["Sample games"] == 1
    assert trend["points L5 avg"] == 10


def test_all_conflicted_games_produce_no_trend():
    rows = [row("2026-10-18", "102", 20),
            row("2026-10-18", "102", 99)]
    assert espn_recent_trends(rows, "2026-10-21") == {}


def test_trends_reject_noncanonical_team_codes():
    invalid = [{**row("2026-10-19", "103", 20), "team": team}
               for team in ("bos", "B0S")]
    assert espn_recent_trends(invalid, "2026-10-21") == {}


def test_trends_exclude_cross_team_athlete_game_conflict():
    first = row("2026-10-19", "100", 20)
    second = {**first, "team": "NYK"}
    assert espn_recent_trends([first, second], "2026-10-21") == {}


def test_trends_cross_team_conflict_when_first_team_has_disputed_totals():
    first = row("2026-10-19", "100", 20)
    disputed = {**first, "points": 25}
    opposing = {**first, "team": "NYK", "points": 30}
    assert espn_recent_trends([first, disputed, opposing], "2026-10-21") == {}


def test_noncanonical_espn_date_is_excluded():
    invalid = {"source": "ESPN verified final boxscore", "player_id": "espn:12", "player": "Player One", "team": "BOS", "game_id": "espn:100", "game_date": "20261019", "points": 20, "rebounds": 5, "assists": 3, "threes": 2}
    assert espn_recent_trends([invalid], "2026-10-21") == {}
