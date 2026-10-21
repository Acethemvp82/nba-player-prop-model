from pregame_results import score_pregame_baselines


def forecast(**overrides):
    row = {"player_id": "espn:123", "slate_date": "2026-10-21",
           "prop": "points", "baseline": 21.5, "player": "Example"}
    return {**row, **overrides}


def final(**overrides):
    row = {"player_id": "espn:123", "game_date": "2026-10-21",
           "is_final": True, "points": 24}
    return {**row, **overrides}


def test_scores_verified_matching_final():
    rows = score_pregame_baselines([forecast()], [final()])
    assert len(rows) == 1
    assert rows[0]["actual"] == 24
    assert rows[0]["projection_error"] == -2.5
    assert rows[0]["absolute_error"] == 2.5


def test_rejects_wrong_date_and_unfinished_game():
    assert score_pregame_baselines([forecast()], [final(game_date="2026-10-20")]) == []
    assert score_pregame_baselines([forecast()], [final(is_final=False)]) == []


def test_rejects_ambiguous_multiple_games():
    assert score_pregame_baselines([forecast()], [final(), final()]) == []


def test_rejects_unverified_metrics_and_invalid_baseline():
    assert score_pregame_baselines([forecast()], [final(points=24.5)]) == []
    assert score_pregame_baselines([forecast(baseline=float("nan"))], [final()]) == []


def test_matches_id_without_mixing_players():
    assert score_pregame_baselines([forecast()], [final(player_id="espn:456")]) == []
