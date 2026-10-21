"""Pure roster coverage diagnostics, independent of selected prop categories."""


def roster_coverage(players, scheduled_teams):
    """Count unique roster listings and missing scheduled teams.

    A listing is not proof of active status or a complete roster.
    """
    teams = {str(team) for team in scheduled_teams if team}
    unique = {(str(p["player_id"]), str(p["team"])) for p in players
              if p.get("player_id") is not None and p.get("team") in teams}
    feed = {(str(p["player_id"]), str(p["team"])) for p in players
            if p.get("player_id") is not None and p.get("team") in teams
            and p.get("source") == "NBA game feed"}
    represented = {team for _, team in unique}
    return {"scheduled_teams": len(teams), "represented_teams": len(represented),
            "missing_teams": sorted(teams - represented),
            "players": len(unique), "feed_players": len(feed),
            "historical_candidates": len(unique - feed)}
