"""Validate NBA box-score player membership against a scheduled matchup.

This checks feed consistency, not whether a player is active or starting.
"""

def valid_game_player(player, matchup):
    if not isinstance(player, dict) or not isinstance(matchup, str):
        return False
    teams = matchup.split(" @ ")
    if len(teams) != 2 or not all(teams) or teams[0] == teams[1]:
        return False
    away, home = teams
    team = player.get("team")
    opponent = player.get("opponent")
    return bool(player.get("player")) and (
        (team == away and opponent == home) or
        (team == home and opponent == away)
    )
