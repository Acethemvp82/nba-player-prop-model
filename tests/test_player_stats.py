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
