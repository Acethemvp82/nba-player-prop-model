"""Historical game summaries from completed NBA player observations.

This module is descriptive, not a prediction engine. Input observations must be
ordered by game date; records with missing dates are excluded to avoid silently
mislabeling the most recent games.
"""
from collections import defaultdict
from datetime import date, datetime
from math import isfinite

PROPS = ("points", "rebounds", "assists", "threes")


def _valid_game_id(value):
    """Accept NBA numeric IDs or explicitly namespaced ESPN event IDs."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return False
    identifier = str(value)
    if identifier.isascii() and identifier.isdigit():
        return True
    if identifier.startswith("espn:"):
        suffix = identifier[5:]
        return bool(suffix) and suffix.isascii() and suffix.isdigit()
    return False



def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                pass
            for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            return None
    return None


def player_history_summaries(observations, as_of=None):
    """Summarize final games strictly before as_of (when supplied).

    Only positive-minute appearances count as games played. Missing stats do
    not become zeroes, and each prop average uses its own valid sample size.
    """
    cutoff = _day(as_of) if as_of is not None else None
    if as_of is not None and cutoff is None:
        raise ValueError("as_of must be a valid ISO date")
    groups = defaultdict(list)
    for row in observations:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        played = _day(row.get("game_date"))
        minutes = row.get("minutes")
        if played is None or (cutoff is not None and played >= cutoff):
            continue
        if not isinstance(minutes, (int, float)) or isinstance(minutes, bool) or not isfinite(minutes) or minutes <= 0:
            continue
        pid = row.get("player_id")
        if pid is None or not _valid_game_id(row.get("game_id")):
            continue
        groups[str(pid)].append((played, row))
    output = []
    for pid, games in groups.items():
        games.sort(key=lambda item: (item[0], str(item[1]["game_id"])), reverse=True)
        seen = set()
        unique = []
        for _, game in games:
            game_key = str(game["game_id"])
            if game_key not in seen:
                unique.append(game)
                seen.add(game_key)
        latest = unique[0]
        record = {"player_id": pid, "player": latest.get("player"),
                  "team": latest.get("team"), "games_played": len(unique),
                  "last_game_date": str(_day(latest["game_date"]))}
        for prop in ("minutes",) + PROPS:
            for label, sample in (("season", unique), ("last_10", unique[:10]), ("last_5", unique[:5])):
                values = [g.get(prop) for g in sample]
                valid = [float(v) for v in values if isinstance(v, (int, float))
                         and not isinstance(v, bool) and isfinite(v) and v >= 0]
                record[f"{prop}_{label}_avg"] = round(sum(valid) / len(valid), 2) if valid else None
                record[f"{prop}_{label}_n"] = len(valid)
        output.append(record)
    return sorted(output, key=lambda r: (r["player"] or "", r["player_id"]))
