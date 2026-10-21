"""Pure diagnostic summaries for ESPN historical coverage on a selected slate."""


def espn_history_coverage(observations, scheduled_teams):
    """Count distinct validated player-games; do not imply full roster coverage."""
    teams = sorted({team for team in scheduled_teams if isinstance(team, str) and team})
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
                and game_id[5:].isascii() and game_id[5:].isdigit()):
            continue
        grouped[team].setdefault(player_id, set()).add(game_id)
    result = []
    for team, players in grouped.items():
        counts = [len(games) for games in players.values()]
        result.append({"Team": team, "Historical players": len(players),
                       "Player-game records": sum(counts),
                       "Players with 5+ games": sum(n >= 5 for n in counts),
                       "Players with 10+ games": sum(n >= 10 for n in counts),
                       "Status": "Partial historical sample" if players else "No verified history"})
    return result
