"""Historical roster fallback for NBA pregame slate previews.

These are *candidate* players seen in prior completed games, not confirmed
active rosters or starters. Team membership may have changed.
"""
from historical_stats import _day

def candidate_players(games, summaries, as_of, max_age_days=30):
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("Invalid slate date")
    if not isinstance(max_age_days, int) or max_age_days < 1:
        raise ValueError("Invalid maximum history age")
    teams = set()
    for game in games:
        for side in ("homeTeam", "awayTeam"):
            team = game.get(side) or {}
            code = team.get("teamTricode")
            if code:
                teams.add(code)
    latest_by_player = {}
    for row in summaries:
        team = row.get("team")
        last_day = _day(row.get("last_game_date"))
        if team not in teams or last_day is None:
            continue
        age = (cutoff - last_day).days
        if not 0 < age <= max_age_days:
            continue
        if not row.get("player_id") or not row.get("player"):
            continue
        candidate = {"player_id": row["player_id"], "player": row["player"],
                     "team": team, "last_seen": last_day.isoformat(),
                     "source": "historical candidate; availability unconfirmed"}
        key = str(row["player_id"])
        prior = latest_by_player.get(key)
        if prior is None or candidate["last_seen"] > prior["last_seen"]:
            latest_by_player[key] = candidate
    return sorted(latest_by_player.values(), key=lambda item: (item["team"], item["player"]))
