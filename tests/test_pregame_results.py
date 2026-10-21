from pregame_results import score_pregame_baselines, summarize_projection_errors


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


def test_impossible_final_threes_are_not_scored():
    rows = score_pregame_baselines(
        [forecast(prop="threes", baseline=2.0)],
        [final(points=5, threes=3)])
    assert rows == []


def test_duplicate_forecasts_count_once():
    rows = score_pregame_baselines([forecast(), forecast()], [final()])
    assert len(rows) == 1
    assert rows[0]["absolute_error"] == 2.5


def test_mismatched_teams_are_not_scored():
    assert score_pregame_baselines(
        [forecast(team="BOS")], [final(team="NYK")]) == []
    assert len(score_pregame_baselines(
        [forecast(team="BOS")], [final(team="BOS")])) == 1


def test_projection_accuracy_summary_by_prop():
    scored = [
        {"prop": "points", "projection_error": -2.0, "result_status": "verified_final"},
        {"prop": "points", "projection_error": 4.0, "result_status": "verified_final"},
        {"prop": "assists", "projection_error": -1.0, "result_status": "verified_final"},
        {"prop": "threes", "projection_error": 50.0, "result_status": "pending"},
    ]
    summary = summarize_projection_errors(scored)
    assert summary == [
        {"prop": "points", "graded_projections": 2,
         "mean_absolute_error": 3.0, "mean_projection_bias": 1.0},
        {"prop": "assists", "graded_projections": 1,
         "mean_absolute_error": 1.0, "mean_projection_bias": -1.0},
    ]


def test_empty_accuracy_summary_has_no_fake_zeroes():
    assert summarize_projection_errors([]) == []


def test_mismatched_player_names_are_not_scored():
    assert score_pregame_baselines(
        [forecast(player="Expected Athlete")],
        [final(player="Different Athlete")]) == []
    assert len(score_pregame_baselines(
        [forecast(player="Expected Athlete")],
        [final(player=" expected athlete ") ])) == 1
