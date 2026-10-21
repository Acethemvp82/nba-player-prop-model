"""Score frozen pregame research baselines against verified final player-games.

No sportsbook lines, betting outcomes, or calibrated probabilities are inferred.
"""
from datetime import date
from math import isfinite

PROPS = ("points", "rebounds", "assists", "threes")


def _valid_iso_day(value):
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False



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
                or not _valid_iso_day(day)):
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
                or not _valid_iso_day(day) or prop not in PROPS or type(baseline) not in (int, float)
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
    for row in scored_rows or []:
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
                or not _valid_iso_day(day) or prop not in PROPS or type(baseline) not in (int, float)
                or not isfinite(baseline) or baseline < 0):
            continue
        keys.add((str(pid), day, prop))
    graded = set()
    for row in scored_rows or []:
        if (isinstance(row, dict) and row.get("result_status") == "verified_final"
                and isinstance(row.get("player_id"), (str, int))
                and not isinstance(row.get("player_id"), bool)
                and _valid_iso_day(row.get("slate_date"))
                and row.get("prop") in PROPS):
            graded.add((str(row["player_id"]), row["slate_date"], row["prop"]))
    count = len(keys & graded)
    return {"eligible_forecasts": len(keys), "graded_forecasts": count,
            "unmatched_forecasts": len(keys) - count,
            "grading_coverage_pct": round(100 * count / len(keys), 1) if keys else None}


def summarize_projection_errors_by_slate(scored_rows):
    """Per-date, per-prop error summary for longitudinal research exports."""
    dates = {}
    for row in scored_rows or []:
        if (not isinstance(row, dict) or row.get("result_status") != "verified_final"
                or not _valid_iso_day(row.get("slate_date"))):
            continue
        dates.setdefault(row["slate_date"], []).append(row)
    output = []
    for day in sorted(dates):
        for summary in summarize_projection_errors(dates[day]):
            output.append({"slate_date": day, **summary})
    return output





def list_unmatched_forecasts(forecasts, scored_rows):
    """Return valid, distinct frozen projections without a verified matched final."""
    graded_keys = {
        (str(row["player_id"]), row["slate_date"], row["prop"])
        for row in (scored_rows or [])
        if (isinstance(row, dict) and row.get("result_status") == "verified_final"
            and isinstance(row.get("player_id"), (str, int))
            and not isinstance(row.get("player_id"), bool)
            and _valid_iso_day(row.get("slate_date")) and row.get("prop") in PROPS)
    }
    seen = set()
    unmatched = []
    for row in forecasts or []:
        if not isinstance(row, dict):
            continue
        pid, day, prop, baseline = (
            row.get("player_id"), row.get("slate_date"),
            row.get("prop"), row.get("baseline"))
        if (not isinstance(pid, (str, int)) or isinstance(pid, bool)
                or not _valid_iso_day(day) or prop not in PROPS
                or type(baseline) not in (int, float)
                or not isfinite(baseline) or baseline < 0):
            continue
        key = (str(pid), day, prop)
        if key in seen or key in graded_keys:
            continue
        seen.add(key)
        unmatched.append({
            "slate_date": day, "player_id": str(pid),
            "player": row.get("player") if isinstance(row.get("player"), str) else "",
            "team": row.get("team") if isinstance(row.get("team"), str) else "",
            "prop": prop, "baseline": baseline,
            "result_status": "unmatched",
        })
    return sorted(unmatched, key=lambda row: (row["slate_date"], row["player_id"], row["prop"]))



def summarize_unmatched_forecasts_by_slate(forecasts, scored_rows):
    """Aggregate the same unmatched keys shown in the player-level report."""
    counts = {}
    for row in list_unmatched_forecasts(forecasts, scored_rows):
        key = (row["slate_date"], row["prop"])
        counts[key] = counts.get(key, 0) + 1
    return [
        {"slate_date": day, "prop": prop, "unmatched_forecasts": count}
        for (day, prop), count in sorted(counts.items())
    ]


def summarize_grading_by_slate(forecasts, scored_rows):
    """Coverage by slate date; unmatched rows are not counted as losses."""
    dates = sorted({
        row["slate_date"] for row in (forecasts or [])
        if isinstance(row, dict) and _valid_iso_day(row.get("slate_date"))
    })
    output = []
    for day in dates:
        day_forecasts = [
            row for row in (forecasts or [])
            if isinstance(row, dict) and row.get("slate_date") == day
        ]
        day_scored = [
            row for row in (scored_rows or [])
            if isinstance(row, dict) and row.get("slate_date") == day
        ]
        summary = projection_grading_coverage(day_forecasts, day_scored)
        if summary["eligible_forecasts"]:
            output.append({"slate_date": day, **summary})
    return output
