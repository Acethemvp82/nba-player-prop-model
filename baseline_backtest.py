"""Leakage-safe retrospective checks for unadjusted NBA statistical baselines.

Evaluates predicted per-game values against completed-game results only.
This is not an OVER probability, sportsbook backtest, or betting recommendation.
"""
from collections import defaultdict
from datetime import timedelta
from math import isfinite

from historical_stats import _day, player_history_summaries
from projection_baseline import baseline_projections

PROPS = ("points", "rebounds", "assists", "threes")


def baseline_backtest(observations, as_of, min_training_games=5):
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
    for row in observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        day = _day(row.get("game_date"))
        gid = str(row.get("game_id") or "")
        pid = row.get("player_id")
        minutes = row.get("minutes")
        if (day is None or day >= cutoff or not gid.isdigit() or pid is None
                or not isinstance(minutes, (int, float)) or isinstance(minutes, bool)
                or not isfinite(minutes) or minutes <= 0):
            continue
        key = (gid, str(pid))
        if key in seen:
            continue
        seen.add(key)
        by_date[day].append(row)
    training = []
    errors = defaultdict(list)
    for day in sorted(by_date):
        summaries = player_history_summaries(training, as_of=day)
        predictions = {(str(p["player_id"]), p["prop"]): p["baseline"]
                       for p in baseline_projections(summaries, min_games=min_training_games)}
        for row in by_date[day]:
            for prop in PROPS:
                actual = row.get(prop)
                predicted = predictions.get((str(row["player_id"]), prop))
                if (predicted is not None and isinstance(actual, (int, float))
                        and not isinstance(actual, bool) and isfinite(actual) and actual >= 0):
                    errors[prop].append(float(predicted) - float(actual))
        training.extend(by_date[day])
    return [
        {"prop": prop, "evaluated": len(errors[prop]),
         "mae": round(sum(abs(e) for e in errors[prop]) / len(errors[prop]), 3)
         if errors[prop] else None,
         "mean_error": round(sum(errors[prop]) / len(errors[prop]), 3)
         if errors[prop] else None}
        for prop in PROPS
    ]
