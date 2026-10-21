from baseline_backtest import baseline_backtest


def game(day, points, game_id=None):
    return {"game_id": game_id or str(day), "game_date": f"2026-10-{day:02d}",
            "is_final": True, "player_id": 10, "player": "Example",
            "team": "BOS", "minutes": 30, "points": points,
            "rebounds": 6, "assists": 4, "threes": 2}


def test_walk_forward_uses_only_prior_days():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.append(game(6, 20))
    results = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-07")}
    assert results["points"]["evaluated"] == 1
    assert results["points"]["mae"] == 10
    assert results["points"]["mean_error"] == -10
    assert results["rebounds"]["mae"] == 0


def test_same_day_results_do_not_leak_into_training():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.extend([game(6, 20, "600"), game(6, 30, "601")])
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-07")}
    assert result["points"]["evaluated"] == 2
    assert result["points"]["mae"] == 15


def test_cutoff_and_duplicate_games():
    rows = [game(i, 10) for i in range(1, 6)]
    rows += [game(6, 20), game(6, 99), game(7, 100)]
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-07")}
    assert result["points"]["evaluated"] == 1
    assert result["points"]["mae"] == 10


def test_insufficient_training_returns_no_accuracy_claim():
    result = baseline_backtest([game(1, 10)], "2026-10-03")
    assert all(r["evaluated"] == 0 and r["mae"] is None for r in result)


def test_player_coverage_is_distinct_from_evaluated_appearances():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.extend([game(6, 12), game(7, 14)])
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-08")}
    assert result["points"]["evaluated"] == 2
    assert result["points"]["players_evaluated"] == 1


def test_backtest_reports_evaluation_date_span():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.extend([game(6, 12), game(7, 14)])
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-08")}
    assert result["points"]["dates_evaluated"] == 2
    assert result["points"]["first_evaluation_date"] == "2026-10-06"
    assert result["points"]["last_evaluation_date"] == "2026-10-07"


def test_backtest_empty_sample_has_no_date_range():
    result = baseline_backtest([], "2026-10-08")
    assert all(r["dates_evaluated"] == 0 and r["first_evaluation_date"] is None
               and r["last_evaluation_date"] is None for r in result)


def test_backtest_coverage_counts_unpredicted_eligible_appearances():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.append(game(6, 20))
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-07")}
    assert result["points"]["eligible_appearances"] == 6
    assert result["points"]["evaluated"] == 1
    assert result["points"]["coverage_pct"] == 16.7


def test_empty_backtest_has_no_coverage_percentage():
    result = baseline_backtest([], "2026-10-07")
    assert all(r["eligible_appearances"] == 0 and r["coverage_pct"] is None
               for r in result)


def test_backtest_reports_excluded_rows():
    rows = [game(i, 10) for i in range(1, 6)]
    rows += [game(6, 20), game(6, 90), None,
             {**game(7, 10), "is_final": False}]
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-08")}
    assert result["points"]["excluded_duplicate_rows"] == 1
    assert result["points"]["excluded_invalid_rows"] == 2
    assert result["points"]["evaluated"] == 1


def test_rmse_emphasizes_large_misses():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.extend([game(6, 10), game(7, 20)])
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-08")}
    assert result["points"]["rmse"] is not None
    assert result["points"]["rmse"] >= result["points"]["mae"]
    assert result["rebounds"]["rmse"] == 0


def test_rmse_unavailable_when_no_predictions():
    result = baseline_backtest([], "2026-10-08")
    assert all(r["rmse"] is None for r in result)


def test_cutoff_exclusions_are_not_reported_as_invalid():
    rows = [game(i, 10) for i in range(1, 6)]
    rows.extend([game(6, 20), game(7, 30)])
    result = {r["prop"]: r for r in baseline_backtest(rows, "2026-10-07")}
    assert result["points"]["excluded_on_or_after_cutoff"] == 1
    assert result["points"]["excluded_invalid_rows"] == 0
    assert result["points"]["evaluated"] == 1


def test_espn_ids_receive_real_walk_forward_evaluation():
    from baseline_backtest import evaluate_baselines
    rows = [{**game(i, 10 if i < 6 else 20), 'game_id': f'espn:{i}'} for i in range(1, 7)]
    result = evaluate_baselines(rows, '2026-10-07')
    points = next(r for r in result['summary'] if r['prop'] == 'points')
    assert points['evaluated'] == 1
    assert points['mae'] == points['last5_mae'] == 10
    assert points['mae_delta_vs_last5'] == 0
    assert all(d['last_training_date'] < d['game_date'] for d in result['details'])
    assert result['details'][0]['training_games'] == 5


def test_benchmark_uses_identical_evaluation_games_without_same_day_training():
    from baseline_backtest import evaluate_baselines
    rows = [game(i, 10 if i <= 5 else 20) for i in range(1, 9)]
    result = evaluate_baselines(rows, '2026-10-09')
    details = [d for d in result['details'] if d['prop'] == 'points']
    summary = next(r for r in result['summary'] if r['prop'] == 'points')
    assert summary['evaluated'] == len(details) == 3
    assert summary['last5_mae'] == round(sum(abs(d['last5_baseline'] - d['actual']) for d in details) / 3, 3)
    changed = evaluate_baselines(rows + [game(9, 1000)], '2026-10-09')
    assert changed['details'] == result['details']
    assert summary['mae_delta_vs_last5'] == round(summary['mae'] - summary['last5_mae'], 3)


def test_changed_teams_are_not_scored_as_existing_team_forecasts():
    from baseline_backtest import evaluate_baselines
    rows = [game(i, 10) for i in range(1, 6)]
    rows.append({**game(6, 20), 'team':'NYK'})
    result = evaluate_baselines(rows, '2026-10-07')
    assert result['details'] == []
    assert all(r['evaluated'] == 0 and r['last5_mae'] is None for r in result['summary'])


def test_malformed_namespaced_game_ids_are_excluded():
    rows = [{**game(i, 10), 'game_id':'espn:bad'} for i in range(1, 7)]
    result = baseline_backtest(rows, '2026-10-07')
    assert all(r['evaluated'] == 0 and r['excluded_invalid_rows'] == 6 for r in result)
