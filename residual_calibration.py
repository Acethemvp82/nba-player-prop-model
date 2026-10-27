"""Walk-forward residual dispersion for research-only NBA prop probabilities.

Never fit dispersion on the game being predicted or later games.
"""
from collections import defaultdict
from math import isfinite, sqrt

from historical_stats import _day

PROPS = ("points", "rebounds", "assists", "threes")


def walk_forward_residuals(observations, as_of, min_training_games=5):
    """Collect active minutes-model residuals using strictly earlier game dates.

    These diagnostics do not enable betting probabilities. Evidence labels are
    retained so prior-season references can be evaluated separately."""
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    if type(min_training_games) is not int or min_training_games < 1:
        raise ValueError("min_training_games must be positive")
    from projection_core import clean_games, core_projections
    grouped = defaultdict(list)
    for row in clean_games(observations, as_of):
        grouped[_day(row['game_date'])].append(row)
    training = []
    residuals = {prop: [] for prop in PROPS}
    for day in sorted(grouped):
        predictions = {(str(p["player_id"]), p["prop"]): p
                       for p in core_projections(training, day, min_games=min_training_games)}
        for row in grouped[day]:
            for prop in PROPS:
                actual = row.get(prop)
                forecast = predictions.get((str(row["player_id"]), prop))
                predicted = forecast['baseline'] if forecast and forecast['team'] == row.get('team') else None
                if (type(actual) in (int, float) and isfinite(actual) and actual >= 0
                        and type(predicted) in (int, float) and isfinite(predicted)):
                    residuals[prop].append({"date": day.isoformat(),
                                            "error": float(actual) - float(predicted),
                                            "player_id": str(row['player_id']),
                                            "game_id": str(row['game_id']),
                                            "evidence": forecast['evidence'],
                                            "model_version": "regular-roster-v2",
                                            "last_training_date": forecast['last_game_date']})
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
