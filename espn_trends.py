"""Recent-game ESPN trends for descriptive player research, never betting projections."""
from collections import defaultdict
from datetime import date

PROPS = ("points", "rebounds", "assists", "threes")


def espn_recent_trends(observations, as_of):
    """Last-five and last-ten *available verified* games per ESPN athlete/team.

    Sample size is explicit because provider gaps can make these incomplete.
    """
    cutoff = date.fromisoformat(as_of)
    grouped = defaultdict(dict)
    for row in observations:
        if not isinstance(row, dict) or row.get("source") != "ESPN verified final boxscore":
            continue
        pid, team, game_id = row.get("player_id"), row.get("team"), row.get("game_id")
        if not (isinstance(pid, str) and pid.startswith("espn:") and pid[5:].isascii()
                and pid[5:].isdigit() and isinstance(team, str) and len(team) == 3
                and team.isascii() and team.isalpha() and team.isupper()
                and isinstance(game_id, str) and game_id.startswith("espn:")
                and game_id[5:].isascii() and game_id[5:].isdigit()):
            continue
        try:
            played = date.fromisoformat(row["game_date"])
        except (KeyError, ValueError, TypeError):
            continue
        if played >= cutoff or any(type(row.get(prop)) is not int or row[prop] < 0 for prop in PROPS):
            continue
        key = (pid, team)
        existing = grouped[key].get(game_id)
        if game_id in grouped[key]:
            if existing is None:
                continue
            # Conflicting observations cannot safely become a recent-game trend.
            if existing[0] != played or any(
                    existing[1][prop] != row[prop] for prop in PROPS):
                grouped[key][game_id] = None
            continue
        grouped[key][game_id] = (played, row)
    result = {}
    for key, games in grouped.items():
        verified = [item for item in games.values() if item is not None]
        if not verified:
            continue
        ordered = [row for _, row in sorted(verified, key=lambda item: (item[0], item[1]["game_id"]), reverse=True)]
        data = {"Sample games": len(ordered)}
        for n in (5, 10):
            sample = ordered[:n]
            data[f"Available last {n} games"] = len(sample)
            for prop in PROPS:
                data[f"{prop} L{n} avg"] = round(sum(row[prop] for row in sample) / len(sample), 2)
        result[key] = data
    return result
