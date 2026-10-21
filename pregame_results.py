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
    finals = {}
    for row in final_observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        pid, day = row.get("player_id"), row.get("game_date")
        if not isinstance(pid, (str, int)) or not isinstance(day, str):
            continue
        key = (str(pid), day)
        finals.setdefault(key, []).append(row)

    scored = []
    for row in forecasts:
        if not isinstance(row, dict):
            continue
        pid, day, prop = row.get("player_id"), row.get("slate_date"), row.get("prop")
        baseline = row.get("baseline")
        if (not isinstance(pid, (str, int)) or not isinstance(day, str)
                or prop not in PROPS or type(baseline) not in (int, float)
                or not isfinite(baseline) or baseline < 0):
            continue
        candidates = finals.get((str(pid), day), [])
        if len(candidates) != 1:
            continue
        actual = candidates[0].get(prop)
        if type(actual) is not int or actual < 0:
            continue
        if (prop == "threes" and type(candidates[0].get("points")) is int
                and actual * 3 > candidates[0]["points"]):
            continue
        error = round(float(baseline) - actual, 2)
        scored.append({**row, "actual": actual, "projection_error": error,
                       "absolute_error": round(abs(error), 2),
                       "result_status": "verified_final"})
    return scored
