"""Pure diagnostic summaries for ESPN historical coverage on a selected slate."""

from datetime import date

PROPS = ("points", "rebounds", "assists", "threes")


def espn_history_coverage(observations, scheduled_teams):
    """Count distinct, nonconflicting verified player-games; not full roster coverage."""
    teams = sorted({team for team in scheduled_teams
                    if isinstance(team, str) and len(team) == 3
                    and team.isascii() and team.isalpha() and team.isupper()})
    grouped = {team: {} for team in teams}
    for row in observations:
        if not isinstance(row, dict) or row.get("source") != "ESPN verified final boxscore":
            continue
        team = row.get("team")
        if team not in grouped:
            continue
        player_id, game_id = row.get("player_id"), row.get("game_id")
        if not (isinstance(player_id, str) and player_id.startswith("espn:")
                and player_id[5:].isascii() and player_id[5:].isdigit()
                and isinstance(game_id, str) and game_id.startswith("espn:")
                and game_id[5:].isascii() and game_id[5:].isdigit()
                and all(type(row.get(prop)) is int and row[prop] >= 0 for prop in PROPS)):
            continue
        game_date = row.get("game_date")
        if not isinstance(game_date, str):
            continue
        try:
            parsed_date = date.fromisoformat(game_date)
        except ValueError:
            continue
        if parsed_date.isoformat() != game_date:
            continue
        key = (player_id, game_id)
        records = grouped[team]
        if key in records:
            previous = records[key]
            if previous is not None and (previous["game_date"] != game_date
                                        or any(previous[prop] != row[prop] for prop in PROPS)):
                records[key] = None
        else:
            records[key] = row
    # A player cannot appear for two teams in the same game. Exclude both
    # sides of a cross-team conflict rather than inflating slate coverage.
    ownership = {}
    conflicts = set()
    for team, records in grouped.items():
        for key, row in records.items():
            if row is None:
                continue
            previous_team = ownership.setdefault(key, team)
            if previous_team != team:
                conflicts.add(key)
    for records in grouped.values():
        for key in conflicts:
            records.pop(key, None)
    result = []
    for team, records in grouped.items():
        players = {}
        for (pid, gid), row in records.items():
            if row is not None:
                players.setdefault(pid, set()).add(gid)
        counts = [len(games) for games in players.values()]
        result.append({"Team": team, "Historical players": len(players),
                       "Player-game records": sum(counts),
                       "Players with 5+ games": sum(n >= 5 for n in counts),
                       "Players with 10+ games": sum(n >= 10 for n in counts),
                       "Status": "Partial historical sample" if players else "No verified history"})
    return result
