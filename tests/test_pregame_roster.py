from pregame_roster import candidate_players

def test_recent_team_candidate_included():
    games = [{"homeTeam": {"teamTricode": "NYK"}, "awayTeam": {"teamTricode": "BOS"}}]
    summaries = [{"player_id": 12, "player": "Sample", "team": "NYK",
                  "last_game_date": "2026-10-18"}]
    result = candidate_players(games, summaries, "2026-10-21")
    assert len(result) == 1
    assert "unconfirmed" in result[0]["source"]

def test_old_and_future_observations_excluded():
    games = [{"homeTeam": {"teamTricode": "NYK"}}]
    summaries = [{"player_id": 1, "player": "Old", "team": "NYK",
                  "last_game_date": "2026-09-01"},
                 {"player_id": 2, "player": "Future", "team": "NYK",
                  "last_game_date": "2026-10-22"}]
    assert candidate_players(games, summaries, "2026-10-21") == []

def test_other_team_excluded():
    assert candidate_players([{"homeTeam": {"teamTricode": "BOS"}}],
        [{"player_id": 1, "player": "Test", "team": "NYK",
          "last_game_date": "2026-10-19"}], "2026-10-21") == []
