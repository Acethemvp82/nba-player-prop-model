from matchup_validation import valid_game_player


def test_valid_away_and_home_players():
    assert valid_game_player({"player": "Away", "team": "NYK", "opponent": "BOS"}, "NYK @ BOS")
    assert valid_game_player({"player": "Home", "team": "BOS", "opponent": "NYK"}, "NYK @ BOS")


def test_wrong_opponent_or_team_is_rejected():
    assert not valid_game_player({"player": "Wrong", "team": "NYK", "opponent": "MIA"}, "NYK @ BOS")
    assert not valid_game_player({"player": "Wrong", "team": "MIA", "opponent": "NYK"}, "NYK @ BOS")


def test_missing_name_or_invalid_matchup_is_rejected():
    assert not valid_game_player({"team": "NYK", "opponent": "BOS"}, "NYK @ BOS")
    assert not valid_game_player({"player": "Sample", "team": "NYK", "opponent": "BOS"}, "NYK")
    assert not valid_game_player({"player": "Sample", "team": "NYK", "opponent": "BOS"}, "NYK @ NYK")
    assert not valid_game_player(None, "NYK @ BOS")
