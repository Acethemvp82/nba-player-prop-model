import pytest
from nba_data import NBADataError
from espn_final_stats import parse_final_espn_boxscore


def sample(completed=True, event_id="4012"):
    return {
        "header": {"competitions": [{"id": event_id, "status": {"type": {"completed": completed}}}]},
        "boxscore": {"players": [{"team": {"abbreviation": "NY"}, "statistics": [{
            "labels": ["MIN", "3PT", "REB", "AST", "PTS"],
            "athletes": [{"athlete": {"id": "22", "displayName": "Sample Guard"},
                          "stats": ["34", "3-7", "8", "6", "24"]}]
        }]}]}
    }


def test_verified_final_stats_are_parsed_with_namespaced_ids():
    rows = parse_final_espn_boxscore(sample(), "4012")
    assert rows == [{"player_id": "espn:22", "player": "Sample Guard",
                     "team": "NYK", "points": 24, "rebounds": 8,
                     "assists": 6, "threes": 3, "source": "ESPN verified final boxscore"}]


def test_unfinished_game_rejected():
    with pytest.raises(NBADataError, match="not verified final"):
        parse_final_espn_boxscore(sample(completed=False), "4012")


def test_mismatched_game_id_rejected():
    with pytest.raises(NBADataError, match="ID mismatch"):
        parse_final_espn_boxscore(sample(event_id="4013"), "4012")


def test_malformed_statistics_never_become_zero():
    data = sample()
    data["boxscore"]["players"][0]["statistics"][0]["athletes"][0]["stats"][1] = "N/A"
    with pytest.raises(NBADataError, match="no validated"):
        parse_final_espn_boxscore(data, "4012")


def test_alternate_keys_and_multiple_competitions():
    data = sample()
    correct = data["header"]["competitions"][0]
    data["header"]["competitions"] = [
        {"id": "9999", "status": {"type": {"completed": False}}}, correct]
    section = data["boxscore"]["players"][0]["statistics"][0]
    section["keys"] = section.pop("labels")
    rows = parse_final_espn_boxscore(data, "4012")
    assert rows[0]["points"] == 24
