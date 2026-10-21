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
