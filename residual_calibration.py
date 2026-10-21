"""Walk-forward residual dispersion for research-only NBA prop probabilities.

Never fit dispersion on the game being predicted or later games.
"""
from collections import defaultdict
from math import isfinite, sqrt

from historical_stats import _day, player_history_summaries
from projection_baseline import baseline_projections

PROPS = ("points", "rebounds", "assists", "threes")


def walk_forward_residuals(observations, as_of, min_training_games=5):
    """Collect out-of-sample residuals using strictly earlier game dates."""
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    if type(min_training_games) is not int or min_training_games < 1:
        raise ValueError("min_training_games must be positive")
    grouped = defaultdict(list)
    seen = set()
    for row in observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        day = _day(row.get("game_date"))
        gid, pid = str(row.get("game_id") or ""), str(row.get("player_id") or "")
        minutes = row.get("minutes")
        if (day is None or day >= cutoff or not gid.isdigit() or not pid
                or type(minutes) not in (int, float) or not isfinite(minutes)
                or minutes <= 0 or (gid, pid) in seen):
            continue
        seen.add((gid, pid))
        grouped[day].append(row)
    training = []
    residuals = {prop: [] for prop in PROPS}
    for day in sorted(grouped):
        summaries = player_history_summaries(training, as_of=day)
        predictions = {(str(p["player_id"]), p["prop"]): p["baseline"]
                       for p in baseline_projections(summaries, min_games=min_training_games)}
        for row in grouped[day]:
            for prop in PROPS:
                actual = row.get(prop)
                predicted = predictions.get((str(row["player_id"]), prop))
                if (type(actual) in (int, float) and isfinite(actual) and actual >= 0
                        and type(predicted) in (int, float) and isfinite(predicted)):
                    residuals[prop].append({"date": day.isoformat(),
                                            "error": float(actual) - float(predicted)})
        training.extend(grouped[day])
    return residuals


def residual_calibration(residuals, min_samples=30):
    """Summarize per-prop out-of-sample residuals; abstain for small samples.

    RMSE is an exploratory scale estimate, not a validated distribution.
    """
    if type(min_samples) is not int or min_samples < 2:
        raise ValueError("min_samples must be >= 2")
    result = []
    for prop in PROPS:
        values = [r["error"] for r in residuals.get(prop, [])
                  if isinstance(r, dict) and type(r.get("error")) in (int, float)
                  and isfinite(r["error"])]
        n = len(values)
        rmse = sqrt(sum(e * e for e in values) / n) if n else None
        result.append({"prop": prop, "samples": n,
                       "rmse": round(rmse, 4) if rmse is not None else None,
                       "residual_std": round(rmse, 4)
                       if n >= min_samples and rmse is not None and rmse > 0 else None,
                       "status": "research_only" if n >= min_samples and rmse is not None
                       and rmse > 0 else "insufficient_data"})
    return result
