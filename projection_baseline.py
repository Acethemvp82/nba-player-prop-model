"""Conservative, descriptive baseline projections from completed-game observations.

These are unadjusted statistical baselines, NOT calibrated betting probabilities.
Insufficient samples or missing metrics remain unavailable.
"""
from math import isfinite

PROPS = ("points", "rebounds", "assists", "threes")

def baseline_projections(summaries, min_games=5):
    """Blend last-5, last-10 and collected-sample per-game averages.

    A player must have >= min_games appearances and >= min_games valid
    observations for the specific prop. This does not account for opponent,
    injuries, starting status, or changes in rotation.
    """
    if not isinstance(min_games, int) or isinstance(min_games, bool) or min_games < 1:
        raise ValueError("min_games must be a positive integer")
    output = []
    for row in summaries:
        if row.get("games_played", 0) < min_games:
            continue
        minutes = row.get("minutes_last_5_avg")
        if not isinstance(minutes, (int, float)) or not isfinite(minutes) or minutes <= 0:
            continue
        for prop in PROPS:
            n = row.get(f"{prop}_season_n", 0)
            if not isinstance(n, int) or n < min_games:
                continue
            season = row.get(f"{prop}_season_avg")
            last10 = row.get(f"{prop}_last_10_avg")
            last5 = row.get(f"{prop}_last_5_avg")
            if any(not isinstance(v, (int, float)) or not isfinite(v) or v < 0
                   for v in (season, last10, last5)):
                continue
            # Baseline is deliberately simple and transparent; no claimed edge.
            estimate = 0.25 * season + 0.35 * last10 + 0.40 * last5
            output.append({
                "player_id": row.get("player_id"),
                "player": row.get("player"),
                "team": row.get("team"),
                "prop": prop,
                "baseline": round(estimate, 2),
                "sample_games": n,
                "recent_minutes": minutes,
                "method": "historical blend; unadjusted",
            })
    return output
