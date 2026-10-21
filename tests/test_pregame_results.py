from pregame_results import score_pregame_baselines, summarize_projection_errors, projection_grading_coverage, summarize_projection_errors_by_slate


def forecast(**overrides):
    row = {"player_id": "espn:123", "slate_date": "2026-10-21",
           "prop": "points", "baseline": 21.5, "player": "Example"}
    return {**row, **overrides}


def final(**overrides):
    row = {"player_id": "espn:123", "game_date": "2026-10-21",
           "is_final": True, "points": 24, "minutes": 32.0}
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


def test_final_without_valid_minutes_is_not_graded():
    for minutes in (None, 0, -1, 61, float("nan"), float("inf")):
        assert score_pregame_baselines([forecast()], [final(minutes=minutes)]) == []


def test_missing_forecast_or_final_collection_returns_no_grades():
    assert score_pregame_baselines(None, [final()]) == []
    assert score_pregame_baselines([forecast()], None) == []


def test_grading_coverage_counts_unique_matched_and_unmatched_forecasts():
    forecasts = [forecast(), forecast(), forecast(player_id="espn:456")]
    scored = score_pregame_baselines(forecasts, [final()])
    assert projection_grading_coverage(forecasts, scored) == {
        "eligible_forecasts": 2, "graded_forecasts": 1,
        "unmatched_forecasts": 1, "grading_coverage_pct": 50.0}


def test_grading_coverage_empty_sample_has_no_percentage():
    assert projection_grading_coverage([], []) == {
        "eligible_forecasts": 0, "graded_forecasts": 0,
        "unmatched_forecasts": 0, "grading_coverage_pct": None}


def test_per_slate_accuracy_keeps_dates_separate():
    rows = [
        {"slate_date": "2026-10-20", "prop": "points",
         "projection_error": -3.0, "result_status": "verified_final"},
        {"slate_date": "2026-10-21", "prop": "points",
         "projection_error": 1.0, "result_status": "verified_final"},
    ]
    assert summarize_projection_errors_by_slate(rows) == [
        {"slate_date": "2026-10-20", "prop": "points",
         "graded_projections": 1, "mean_absolute_error": 3.0,
         "mean_projection_bias": -3.0},
        {"slate_date": "2026-10-21", "prop": "points",
         "graded_projections": 1, "mean_absolute_error": 1.0,
         "mean_projection_bias": 1.0},
    ]


def test_boolean_player_ids_never_grade_or_count_as_eligible():
    assert score_pregame_baselines([forecast(player_id=True)], [final(player_id=True)]) == []
    assert projection_grading_coverage([forecast(player_id=True)], [])["eligible_forecasts"] == 0


def test_invalid_slate_date_shape_cannot_be_graded():
    assert score_pregame_baselines(
        [forecast(slate_date="20261021")],
        [final(game_date="20261021")]) == []
    assert projection_grading_coverage(
        [forecast(slate_date="20261021")], [])["eligible_forecasts"] == 0


def test_impossible_calendar_date_is_not_graded_or_eligible():
    assert score_pregame_baselines(
        [forecast(slate_date="2026-02-30")],
        [final(game_date="2026-02-30")]) == []
    assert projection_grading_coverage(
        [forecast(slate_date="2026-02-30")], [])["eligible_forecasts"] == 0


def test_per_slate_accuracy_ignores_impossible_dates():
    rows = [
        {"slate_date": "2026-02-30", "prop": "points",
         "projection_error": 5.0, "result_status": "verified_final"},
        {"slate_date": "2026-02-28", "prop": "points",
         "projection_error": -2.0, "result_status": "verified_final"},
    ]
    assert summarize_projection_errors_by_slate(rows) == [
        {"slate_date": "2026-02-28", "prop": "points",
         "graded_projections": 1, "mean_absolute_error": 2.0,
         "mean_projection_bias": -2.0}
    ]


def test_coverage_does_not_count_invalid_verified_result_keys():
    rows = [
        {"player_id": True, "slate_date": "2026-10-21",
         "prop": "points", "result_status": "verified_final"},
        {"player_id": "espn:123", "slate_date": "2026-02-30",
         "prop": "points", "result_status": "verified_final"},
        {"player_id": "espn:123", "slate_date": "2026-10-21",
         "prop": "invalid", "result_status": "verified_final"},
    ]
    assert projection_grading_coverage([forecast()], rows)["graded_forecasts"] == 0


def test_missing_scored_rows_have_no_accuracy_summary():
    assert summarize_projection_errors(None) == []
    assert summarize_projection_errors_by_slate(None) == []
