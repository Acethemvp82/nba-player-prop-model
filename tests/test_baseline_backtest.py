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
