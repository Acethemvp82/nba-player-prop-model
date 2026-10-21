"""Score frozen pregame research baselines against verified final player-games.

No sportsbook lines, betting outcomes, or calibrated probabilities are inferred.
"""
from math import isfinite

PROPS = ("points", "rebounds", "assists", "threes")


def score_pregame_baselines(forecasts, final_observations):
    """Match on player ID and slate date; never score incomplete or future games.

    Returns one row per valid matched forecast. Multiple final games for the same
    player/date are ambiguous and are excluded rather than guessed.
    """
    if forecasts is None or final_observations is None:
        return []
    finals = {}
    for row in final_observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        pid, day = row.get("player_id"), row.get("game_date")
        if (not isinstance(pid, (str, int)) or isinstance(pid, bool)
                or not isinstance(day, str)):
            continue
        key = (str(pid), day)
        finals.setdefault(key, []).append(row)

    scored = []
    seen_forecasts = set()
    for row in forecasts:
        if not isinstance(row, dict):
            continue
        pid, day, prop = row.get("player_id"), row.get("slate_date"), row.get("prop")
        baseline = row.get("baseline")
        if (not isinstance(pid, (str, int)) or isinstance(pid, bool)
                or not isinstance(day, str) or prop not in PROPS or type(baseline) not in (int, float)
                or not isfinite(baseline) or baseline < 0):
            continue
        # Only a verified final for the same player and slate date can score.
        # Reject duplicate forecast keys to avoid double-counting accuracy.
        forecast_key = (str(pid), day, prop)
        if forecast_key in seen_forecasts:
            continue
        seen_forecasts.add(forecast_key)
        candidates = finals.get((str(pid), day), [])
        if len(candidates) != 1:
            continue
        # The scoring source must be a verified player-game with valid minutes.
        minutes = candidates[0].get("minutes")
        if (type(minutes) not in (int, float) or not isfinite(minutes)
                or not 0 < minutes <= 60):
            continue
        actual = candidates[0].get(prop)
        if type(actual) is not int or actual < 0:
            continue
        # Uploaded CSVs must not turn absent player/team fields into false
        # identity matches. Require agreement whenever both names are present.
        if (isinstance(row.get("player"), str)
                and isinstance(candidates[0].get("player"), str)
                and row["player"].strip().casefold()
                != candidates[0]["player"].strip().casefold()):
            continue
        if (row.get("team") is not None and candidates[0].get("team") is not None
                and row["team"] != candidates[0]["team"]):
            continue
        if (prop == "threes" and type(candidates[0].get("points")) is int
                and actual * 3 > candidates[0]["points"]):
            continue
        error = round(float(baseline) - actual, 2)
        scored.append({**row, "actual": actual, "projection_error": error,
                       "absolute_error": round(abs(error), 2),
                       "result_status": "verified_final"})
    return scored


def summarize_projection_errors(scored_rows):
    """Per-prop descriptive accuracy from already verified matched results.

    MAE is mean absolute error; bias is mean(projection - actual).
    An empty prop is omitted rather than reported as zero error.
    """
    groups = {prop: [] for prop in PROPS}
    for row in scored_rows:
        if not isinstance(row, dict) or row.get("result_status") != "verified_final":
            continue
        prop = row.get("prop")
        error = row.get("projection_error")
        if prop in groups and type(error) in (int, float) and isfinite(error):
            groups[prop].append(float(error))
    return [
        {"prop": prop, "graded_projections": len(errors),
         "mean_absolute_error": round(sum(abs(e) for e in errors) / len(errors), 2),
         "mean_projection_bias": round(sum(errors) / len(errors), 2)}
        for prop, errors in groups.items() if errors
    ]


def projection_grading_coverage(forecasts, scored_rows):
    """Describe grading coverage without treating unmatched forecasts as misses.

    Counts unique player/date/prop keys from valid frozen forecasts. A grade
    counts only when a verified final result has been matched.
    """
    keys = set()
    for row in forecasts or []:
        if not isinstance(row, dict):
            continue
        pid, day, prop = row.get("player_id"), row.get("slate_date"), row.get("prop")
        baseline = row.get("baseline")
        if (not isinstance(pid, (str, int)) or isinstance(pid, bool)
                or not isinstance(day, str) or prop not in PROPS or type(baseline) not in (int, float)
                or not isfinite(baseline) or baseline < 0):
            continue
        keys.add((str(pid), day, prop))
    graded = set()
    for row in scored_rows or []:
        if isinstance(row, dict) and row.get("result_status") == "verified_final":
            graded.add((str(row.get("player_id")), row.get("slate_date"), row.get("prop")))
    count = len(keys & graded)
    return {"eligible_forecasts": len(keys), "graded_forecasts": count,
            "unmatched_forecasts": len(keys) - count,
            "grading_coverage_pct": round(100 * count / len(keys), 1) if keys else None}


def summarize_projection_errors_by_slate(scored_rows):
    """Per-date, per-prop error summary for longitudinal research exports."""
    dates = {}
    for row in scored_rows or []:
        if (not isinstance(row, dict) or row.get("result_status") != "verified_final"
                or not isinstance(row.get("slate_date"), str)):
            continue
        dates.setdefault(row["slate_date"], []).append(row)
    output = []
    for day in sorted(dates):
        for summary in summarize_projection_errors(dates[day]):
            output.append({"slate_date": day, **summary})
    return output
