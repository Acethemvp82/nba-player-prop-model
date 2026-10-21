"""Descriptive opponent box-score aggregates from verified completed games.

These are observed per-game opponent totals, not pace-adjusted defensive ratings
or calibrated player prop adjustments. No sportsbook data is used.
"""
from collections import defaultdict
from math import isfinite
from historical_stats import _day

PROPS = ("points", "rebounds", "assists", "threes")


def opponent_game_totals(observations, as_of):
    """Aggregate each game's recorded player production by opponent.

    Excludes games on/after as_of, non-final rows, invalid team/opponent pairs,
    duplicate player observations, and missing/nonfinite prop values. Returns
    totals only for props complete among observed eligible player rows; roster
    completeness itself cannot be proven from this data.
    """
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    groups = defaultdict(dict)
    for row in observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        played = _day(row.get("game_date"))
        opponent, team = row.get("opponent"), row.get("team")
        game_id, player_id = str(row.get("game_id") or ""), row.get("player_id")
        if (played is None or played >= cutoff or not game_id.isdigit()
                or not opponent or not team or opponent == team or player_id is None):
            continue
        key = (str(opponent), game_id, str(team))
        groups[key][str(player_id)] = row
    output = []
    for (opponent, game_id, team), players in groups.items():
        record = {"opponent": opponent, "game_id": game_id,
                  "offense_team": team, "players_observed": len(players)}
        for prop in PROPS:
            values = [p.get(prop) for p in players.values()]
            if all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   and isfinite(v) and v >= 0 for v in values):
                record[prop + "_allowed_observed"] = round(sum(values), 2)
            else:
                record[prop + "_allowed_observed"] = None
        output.append(record)
    return sorted(output, key=lambda r: (r["opponent"], r["game_id"], r["offense_team"]))
