"""Transparent quality checks for collected NBA historical observations.

These diagnostics do not imply that the sample is complete or predictive.
"""
from collections import Counter
from math import isfinite
from historical_stats import _day

PROPS = ("points", "rebounds", "assists", "threes")


def history_quality(observations, as_of):
    """Count eligible, rejected, and missing-value records without imputing data."""
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    counts = Counter()
    games = set()
    players = set()
    for row in observations:
        counts["rows_received"] += 1
        if not isinstance(row, dict) or row.get("is_final") is not True:
            counts["rejected_nonfinal_or_invalid"] += 1
            continue
        played = _day(row.get("game_date"))
        if played is None or played >= cutoff:
            counts["rejected_date"] += 1
            continue
        gid = str(row.get("game_id") or "")
        pid = row.get("player_id")
        minutes = row.get("minutes")
        if (not gid.isdigit() or pid is None or
                not isinstance(minutes, (int, float)) or isinstance(minutes, bool)
                or not isfinite(minutes) or minutes <= 0):
            counts["rejected_identity_or_minutes"] += 1
            continue
        counts["usable_appearances"] += 1
        games.add(gid)
        players.add(str(pid))
        for prop in PROPS:
            value = row.get(prop)
            if (not isinstance(value, (int, float)) or isinstance(value, bool)
                    or not isfinite(value) or value < 0):
                counts[prop + "_missing"] += 1
    return {
        "rows_received": counts["rows_received"],
        "usable_appearances": counts["usable_appearances"],
        "unique_games": len(games),
        "unique_players": len(players),
        "rejected_nonfinal_or_invalid": counts["rejected_nonfinal_or_invalid"],
        "rejected_date": counts["rejected_date"],
        "rejected_identity_or_minutes": counts["rejected_identity_or_minutes"],
        **{prop + "_missing": counts[prop + "_missing"] for prop in PROPS},
    }
