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


@pytest.mark.parametrize("bad_value", ["4-3", "3-7-2", "-7", "3-x", "N/A", "3"])
def test_invalid_three_point_made_attempted_values_rejected(bad_value):
    data = sample()
    data["boxscore"]["players"][0]["statistics"][0]["athletes"][0]["stats"][1] = bad_value
    with pytest.raises(NBADataError, match="no validated"):
        parse_final_espn_boxscore(data, "4012")


def test_did_not_play_entries_are_excluded():
    data = sample()
    data["boxscore"]["players"][0]["statistics"][0]["athletes"][0]["didNotPlay"] = True
    with pytest.raises(NBADataError, match="no validated"):
        parse_final_espn_boxscore(data, "4012")


def test_malformed_statistics_sections_are_skipped():
    data = sample()
    data["boxscore"]["players"].insert(0, {
        "team": {"abbreviation": "BOS"}, "statistics": None})
    rows = parse_final_espn_boxscore(data, "4012")
    assert len(rows) == 1
    assert rows[0]["player_id"] == "espn:22"


def test_stat_labels_allow_surrounding_whitespace():
    data = sample()
    data["boxscore"]["players"][0]["statistics"][0]["labels"] = [
        "MIN", " 3pt ", "reb ", " Ast", " pts "]
    rows = parse_final_espn_boxscore(data, "4012")
    assert rows[0]["points"] == 24
    assert rows[0]["threes"] == 3


def test_conflicting_duplicate_final_boxscore_rows_are_rejected():
    data = sample()
    section = data["boxscore"]["players"][0]["statistics"][0]
    original = section["athletes"][0]
    section["athletes"].append({
        "athlete": dict(original["athlete"]),
        "stats": ["34", "3-7", "8", "6", "25"]})
    with pytest.raises(NBADataError, match="Conflicting ESPN final stats"):
        parse_final_espn_boxscore(data, "4012")


def test_identical_duplicate_final_boxscore_rows_are_counted_once():
    data = sample()
    section = data["boxscore"]["players"][0]["statistics"][0]
    section["athletes"].append({
        "athlete": dict(section["athletes"][0]["athlete"]),
        "stats": list(section["athletes"][0]["stats"])})
    rows = parse_final_espn_boxscore(data, "4012")
    assert len(rows) == 1
    assert rows[0]["points"] == 24


def test_same_athlete_on_two_teams_rejects_final_boxscore():
    data = sample()
    data["boxscore"]["players"].append({
        "team": {"abbreviation": "BOS"},
        "statistics": [{
            "labels": ["MIN", "3PT", "REB", "AST", "PTS"],
            "athletes": [{"athlete": {"id": "22", "displayName": "Sample Guard"},
                          "stats": ["34", "3-7", "8", "6", "24"]}]
        }]})
    with pytest.raises(NBADataError, match="both teams"):
        parse_final_espn_boxscore(data, "4012")


def test_duplicate_required_stat_headings_do_not_produce_observations():
    for heading in ("PTS", "REB", "AST", "3PT"):
        data = sample()
        section = data["boxscore"]["players"][0]["statistics"][0]
        section["labels"].append(" " + heading.lower() + " ")
        section["athletes"][0]["stats"].append("1")
        with pytest.raises(NBADataError, match="no validated"):
            parse_final_espn_boxscore(data, "4012")


@pytest.mark.parametrize("event_id", [True, False, None, 40.12, [], {}])
def test_invalid_expected_event_id_types_are_rejected(event_id):
    with pytest.raises(NBADataError, match="Invalid ESPN event ID"):
        parse_final_espn_boxscore(sample(), event_id)
