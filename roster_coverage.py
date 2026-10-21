"""Pure roster coverage diagnostics, independent of selected prop categories."""


def roster_coverage(players, scheduled_teams):
    """Count unique roster listings and missing scheduled teams.

    A listing is not proof of active status or a complete roster.
    """
    teams = {str(team) for team in scheduled_teams if isinstance(team, str) and team}
    def valid_id(p):
        if not isinstance(p, dict) or p.get("team") not in teams:
            return False
        player_id = p.get("player_id")
        if not isinstance(player_id, (str, int)) or isinstance(player_id, bool):
            return False
        value = str(player_id)
        if p.get("source") in ("ESPN game summary (unconfirmed)", "ESPN team roster (unconfirmed)"):
            return value.startswith("espn:") and value[5:].isascii() and value[5:].isdigit()
        return value.isascii() and value.isdigit()

    valid = [p for p in players if valid_id(p)]
    unique = {(str(p["player_id"]), p["team"]) for p in valid}
    feed = {(str(p["player_id"]), p["team"]) for p in valid
            if p.get("source") in ("NBA game feed", "ESPN game summary (unconfirmed)", "ESPN team roster (unconfirmed)")}
    represented = {team for _, team in unique}
    return {"scheduled_teams": len(teams), "represented_teams": len(represented),
            "missing_teams": sorted(teams - represented),
            "players": len(unique), "feed_players": len(feed),
            "historical_candidates": len(unique - feed)}
