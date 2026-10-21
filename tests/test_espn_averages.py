from espn_averages import espn_player_averages


def test_espn_averages_deduplicate_games_and_exclude_slate_day():
    def row(day, gid, points):
        return {"player_id": "espn:12", "player": "Player One", "team": "BOS",
                "game_date": day, "game_id": gid, "source": "ESPN verified final boxscore", "points": points,
                "rebounds": 6, "assists": 4, "threes": 2}
    rows = [row("2026-10-18", "espn:100", 20),
            row("2026-10-18", "espn:100", 20),
            row("2026-10-19", "espn:101", 30),
            row("2026-10-21", "espn:102", 90)]
    result = espn_player_averages(rows, "2026-10-21")
    assert result[0]["Sample games"] == 2
    assert result[0]["Points avg"] == 25
    assert result[0]["Threes avg"] == 2


def test_espn_averages_reject_invalid_and_unscoped_identifiers():
    assert espn_player_averages([
        {"player_id": "12", "player": "Wrong ID", "team": "BOS",
         "game_date": "2026-10-20", "game_id": "espn:1",
         "points": 10, "rebounds": 2, "assists": 1, "threes": 1},
    ], "2026-10-21") == []


def test_malformed_espn_game_ids_are_excluded():
    base = {"player_id": "espn:12", "player": "Player One", "team": "BOS",
            "game_date": "2026-10-20", "source": "ESPN verified final boxscore",
            "points": 20, "rebounds": 5, "assists": 3, "threes": 2}
    assert espn_player_averages([{**base, "game_id": "espn:invalid"}], "2026-10-21") == []
    assert espn_player_averages([{**base, "game_id": "espn:100"}], "2026-10-21")[0]["Sample games"] == 1


def test_conflicting_duplicate_games_are_excluded_from_averages():
    base = {"player_id": "espn:12", "player": "Player One", "team": "BOS",
            "source": "ESPN verified final boxscore",
            "rebounds": 6, "assists": 4, "threes": 2}
    rows = [
        {**base, "game_date": "2026-10-18", "game_id": "espn:100", "points": 20},
        {**base, "game_date": "2026-10-19", "game_id": "espn:101", "points": 30},
        {**base, "game_date": "2026-10-19", "game_id": "espn:101", "points": 99},
        {**base, "game_date": "2026-10-19", "game_id": "espn:101", "points": 30},
    ]
    result = espn_player_averages(rows, "2026-10-21")
    assert len(result) == 1
    assert result[0]["Sample games"] == 1
    assert result[0]["Points avg"] == 20


def test_all_conflicted_games_produce_no_averages():
    base = {"player_id": "espn:12", "player": "Player One", "team": "BOS",
            "source": "ESPN verified final boxscore",
            "game_date": "2026-10-19", "game_id": "espn:101",
            "rebounds": 6, "assists": 4, "threes": 2}
    assert espn_player_averages([
        {**base, "points": 30}, {**base, "points": 99}
    ], "2026-10-21") == []
