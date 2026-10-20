from player_stats import parse_minutes, normalize_player_boxscore, completed_game_observations

def test_minutes_parsing():
    assert parse_minutes("PT28M30.00S") == 28.5
    assert parse_minutes("PT1H2M") == 62
    assert parse_minutes("invalid") is None
    assert parse_minutes(None) is None

def test_boxscore_normalization():
    player = {"player_id": 7, "player": "Test", "team": "BOS", "opponent": "NYK",
              "statistics": {"minutes": "PT20M", "points": 18, "reboundsTotal": 9,
                             "assists": 4, "threePointersMade": 3}}
    result = normalize_player_boxscore(player, "123", final=True)
    assert (result["points"], result["rebounds"], result["assists"], result["threes"]) == (18, 9, 4, 3)
    assert result["minutes"] == 20
    assert result["is_final"] is True

def test_only_completed_games_are_used():
    games = [{"gameId": "1", "gameStatus": 2}, {"gameId": "2", "gameStatus": 3}]
    def load(game_id):
        assert game_id == "2"
        return [{"player_id": 1, "player": "Test", "statistics": {"minutes": "PT12M", "points": 10}}]
    results = completed_game_observations(games, load)
    assert len(results) == 1
    assert results[0]["game_id"] == "2"

def test_invalid_stats_not_treated_as_zero():
    result = normalize_player_boxscore({"statistics": {"points": None, "assists": -1}}, "1")
    assert result["points"] is None
    assert result["assists"] is None

def test_completed_games_include_official_game_date():
    games = [{"gameId": "123", "gameStatus": 3, "gameDateEst": "2026-10-19"}]
    def load(_):
        return [{"player_id": 1, "player": "Example",
                 "statistics": {"minutes": "PT22M", "points": 12}}]
    result = completed_game_observations(games, load)
    assert result[0]["game_date"] == "2026-10-19"
    from historical_stats import player_history_summaries
    summary = player_history_summaries(result, as_of="2026-10-20")
    assert summary[0]["points_last_5_avg"] == 12

def test_missing_game_date_does_not_fabricate_history():
    games = [{"gameId": "123", "gameStatus": 3}]
    def load(_):
        return [{"player_id": 1, "statistics": {"minutes": "PT12M", "points": 7}}]
    result = completed_game_observations(games, load)
    from historical_stats import player_history_summaries
    assert player_history_summaries(result) == []
