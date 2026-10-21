"""Pure roster coverage diagnostics, independent of selected prop categories."""


def roster_coverage(players, scheduled_teams):
    """Count unique roster listings and missing scheduled teams.

    A listing is not proof of active status or a complete roster.
    """
    teams = {str(team) for team in scheduled_teams if isinstance(team, str) and team}
    valid = [p for p in players if isinstance(p, dict)
             and p.get("player_id") is not None and p.get("team") in teams]
    unique = {(str(p["player_id"]), p["team"]) for p in valid}
    feed = {(str(p["player_id"]), p["team"]) for p in valid
            if p.get("source") == "NBA game feed"}
    represented = {team for _, team in unique}
    return {"scheduled_teams": len(teams), "represented_teams": len(represented),
            "missing_teams": sorted(teams - represented),
            "players": len(unique), "feed_players": len(feed),
            "historical_candidates": len(unique - feed)}
