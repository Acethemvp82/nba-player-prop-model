"""Descriptive ESPN player averages, with explicit sample sizes and no projections."""
from collections import defaultdict
from datetime import date

PROPS = ("points", "rebounds", "assists", "threes")


def espn_player_averages(observations, as_of):
    """Summarize verified pre-slate ESPN boxscores only.

    Does not mix ESPN IDs with NBA IDs or infer missing observations as zeros.
    """
    cutoff = date.fromisoformat(as_of)
    grouped = defaultdict(list)
    for row in observations:
        if not isinstance(row, dict):
            continue
        pid, team, name, played = (row.get(k) for k in ("player_id", "team", "player", "game_date"))
        if not (isinstance(pid, str) and pid.startswith("espn:") and
                pid[5:].isascii() and pid[5:].isdigit() and
                isinstance(team, str) and len(team) == 3 and
                isinstance(name, str) and name.strip() and isinstance(played, str)):
            continue
        try:
            day = date.fromisoformat(played)
        except ValueError:
            continue
        if day >= cutoff:
            continue
        if row.get("source") != "ESPN verified final boxscore":
            continue
        if any(isinstance(row.get(prop), bool) or
               not isinstance(row.get(prop), int) or row[prop] < 0 for prop in PROPS):
            continue
        grouped[(pid, team)].append((day, row))
    result = []
    for (pid, team), games in grouped.items():
        games.sort(key=lambda entry: entry[0], reverse=True)
        unique = {}
        for day, row in games:
            game_id = row.get("game_id")
            if isinstance(game_id, str) and game_id.startswith("espn:"):
                unique.setdefault(game_id, row)
        if not unique:
            continue
        rows = list(unique.values())
        result.append({"Player": rows[0]["player"].strip(), "Player ID": pid, "Team": team,
                       "Sample games": len(rows),
                       **{f"{prop.title()} avg": round(sum(r[prop] for r in rows) / len(rows), 2)
                          for prop in PROPS}})
    return sorted(result, key=lambda row: (row["Team"], row["Player"]))
