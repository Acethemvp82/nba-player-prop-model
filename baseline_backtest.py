"""Leakage-safe retrospective checks for unadjusted NBA statistical baselines.

Evaluates predicted per-game values against completed-game results only.
This is not an OVER probability, sportsbook backtest, or betting recommendation.
"""
from collections import defaultdict
from math import isfinite

from historical_stats import _day, _valid_game_id, player_history_summaries
from projection_baseline import baseline_projections

PROPS = ("points", "rebounds", "assists", "threes")


def evaluate_baselines(observations, as_of, min_training_games=5):
    """Walk forward by game date, training exclusively on earlier dates.

    Same-day games are evaluated together to avoid using their outcomes as
    training data for one another. Duplicate player/game observations are
    counted once. Results are descriptive MAE and signed error by prop.
    """
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    if (not isinstance(min_training_games, int) or isinstance(min_training_games, bool)
            or min_training_games < 1):
        raise ValueError("min_training_games must be a positive integer")
    by_date = defaultdict(list)
    seen = set()
    invalid_rows = 0
    future_or_cutoff_rows = 0
    duplicate_rows = 0
    for row in observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            invalid_rows += 1
            continue
        day = _day(row.get("game_date"))
        gid = str(row.get("game_id") or "")
        pid = row.get("player_id")
        minutes = row.get("minutes")
        if day is not None and day >= cutoff:
            future_or_cutoff_rows += 1
            continue
        if (day is None or not _valid_game_id(row.get("game_id")) or pid is None
                or not isinstance(minutes, (int, float)) or isinstance(minutes, bool)
                or not isfinite(minutes) or minutes <= 0):
            invalid_rows += 1
            continue
        key = (gid, str(pid))
        if key in seen:
            duplicate_rows += 1
            continue
        seen.add(key)
        by_date[day].append(row)
    training = []
    errors = defaultdict(list)
    eligible_appearances = defaultdict(int)
    player_games = defaultdict(set)
    evaluated_dates = defaultdict(set)
    squared_errors = defaultdict(list)
    benchmark_errors = defaultdict(list)
    details = []
    for day in sorted(by_date):
        summaries = player_history_summaries(training, as_of=day)
        predictions = {(str(p["player_id"]), p["prop"]): p
                       for p in baseline_projections(summaries, min_games=min_training_games)}
        summary_by_id = {str(s["player_id"]): s for s in summaries}
        for row in by_date[day]:
            for prop in PROPS:
                actual = row.get(prop)
                if (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                        and isfinite(actual) and actual >= 0):
                    eligible_appearances[prop] += 1
                forecast = predictions.get((str(row["player_id"]), prop))
                # A historical forecast for a former team would not have
                # represented this matchup on the pregame board.
                predicted = forecast["baseline"] if forecast and forecast["team"] == row.get("team") else None
                if (predicted is not None and isinstance(actual, (int, float))
                        and not isinstance(actual, bool) and isfinite(actual) and actual >= 0):
                    summary = summary_by_id[str(row["player_id"])]
                    benchmark = summary[prop + "_last_5_avg"]
                    benchmark_errors[prop].append(float(benchmark) - float(actual))
                    details.append({"game_date": day.isoformat(), "game_id": str(row["game_id"]),
                        "player_id": str(row["player_id"]), "player": row.get("player"),
                        "team": row.get("team"), "prop": prop,
                        "baseline": predicted, "last5_baseline": benchmark, "actual": actual,
                        "error": round(predicted - actual, 3),
                        "absolute_error": round(abs(predicted - actual), 3),
                        "training_games": forecast["sample_games"],
                        "last_training_date": summary["last_game_date"]})
                    errors[prop].append(float(predicted) - float(actual))
                    squared_errors[prop].append((float(predicted) - float(actual)) ** 2)
                    player_games[prop].add(str(row["player_id"]))
                    evaluated_dates[prop].add(day)
        training.extend(by_date[day])
    results = [
        {"prop": prop,
         "excluded_invalid_rows": invalid_rows,
         "excluded_on_or_after_cutoff": future_or_cutoff_rows,
         "excluded_duplicate_rows": duplicate_rows, "evaluated": len(errors[prop]),
         "players_evaluated": len(player_games[prop]),
         "eligible_appearances": eligible_appearances[prop],
         "coverage_pct": round(100 * len(errors[prop]) / eligible_appearances[prop], 1)
         if eligible_appearances[prop] else None,
         "dates_evaluated": len(evaluated_dates[prop]),
         "first_evaluation_date": min(evaluated_dates[prop]).isoformat() if evaluated_dates[prop] else None,
         "last_evaluation_date": max(evaluated_dates[prop]).isoformat() if evaluated_dates[prop] else None,
         "mae": round(sum(abs(e) for e in errors[prop]) / len(errors[prop]), 3)
         if errors[prop] else None,
         "mean_error": round(sum(errors[prop]) / len(errors[prop]), 3)
         if errors[prop] else None,
         "last5_mae": round(sum(abs(e) for e in benchmark_errors[prop]) / len(benchmark_errors[prop]), 3)
         if benchmark_errors[prop] else None,
         "mae_delta_vs_last5": round((sum(abs(e) for e in errors[prop])
                                      - sum(abs(e) for e in benchmark_errors[prop])) / len(errors[prop]), 3)
         if errors[prop] else None,
         "rmse": round((sum(squared_errors[prop]) / len(squared_errors[prop])) ** 0.5, 3)
         if squared_errors[prop] else None}
        for prop in PROPS
    ]

    return {"summary": results, "details": details}


def baseline_backtest(observations, as_of, min_training_games=5):
    """Compatibility wrapper returning per-prop walk-forward summaries."""
    return evaluate_baselines(observations, as_of, min_training_games)["summary"]
