"""Live ESPN final-boxscore smoke check; never produces betting projections.

Run: python scripts/espn_live_probe.py
"""
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from espn_history import espn_final_game_players
from espn_schedule import espn_games_on


def check_recent_finals(today=None, days=7, schedule_loader=espn_games_on,
                        boxscore_loader=espn_final_game_players, max_attempts=12):
    """Try multiple recent finals, preserving errors for troubleshooting.

    One unavailable boxscore should not mask another valid final game.
    """
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 30:
        raise ValueError("days must be between 1 and 30")
    today = today or datetime.now(timezone.utc).date()
    errors = []
    completed = 0
    for offset in range(1, days + 1):
        if completed >= max_attempts:
            break
        day = (today - timedelta(days=offset)).isoformat()
        try:
            games = schedule_loader(day)
        except Exception as exc:
            errors.append(f"{day} schedule: {type(exc).__name__}: {exc}")
            continue
        if not isinstance(games, list):
            errors.append(f"{day} schedule: invalid game collection")
            continue
        for game in games:
            if completed >= max_attempts:
                break
            if not isinstance(game, dict) or game.get("espnCompleted") is not True:
                continue
            event_id = game.get("espnEventId")
            if not (isinstance(event_id, str) and event_id.isascii()
                    and event_id.isdigit()):
                continue
            completed += 1
            try:
                players = boxscore_loader(event_id)
                if not isinstance(players, list) or not players:
                    raise ValueError("No validated player observations")
                # Cross-check the verified summary against the scoreboard matchup.
                home, away = game.get("homeTeam"), game.get("awayTeam")
                expected_teams = None
                if home is not None or away is not None:
                    if not isinstance(home, dict) or not isinstance(away, dict):
                        raise ValueError("Incomplete scheduled matchup")
                    expected_teams = {home.get("teamTricode"), away.get("teamTricode")}
                    if (len(expected_teams) != 2
                            or any(not isinstance(team, str) or len(team) != 3
                                   or not team.isascii() or not team.isalpha()
                                   or not team.isupper() for team in expected_teams)):
                        raise ValueError("Invalid scheduled matchup")
                seen_players = set()
                # A probe must never pass on a malformed or unverified row.
                for player in players:
                    if not isinstance(player, dict):
                        raise ValueError("Malformed player observation")
                    pid = player.get("player_id")
                    team = player.get("team")
                    if (player.get("source") != "ESPN verified final boxscore"
                            or not isinstance(pid, str) or not pid.startswith("espn:")
                            or not pid[5:].isascii() or not pid[5:].isdigit()
                            or not isinstance(team, str) or len(team) != 3
                            or not team.isascii() or not team.isalpha() or not team.isupper()
                            or any(type(player.get(stat)) is not int or player[stat] < 0
                                   for stat in ("points", "rebounds", "assists", "threes"))):
                        raise ValueError("Unverified or invalid player observation")
                    if expected_teams is not None and team not in expected_teams:
                        raise ValueError("Player team does not match scheduled game")
                    key = (pid, team)
                    if key in seen_players:
                        raise ValueError("Duplicate player observation")
                    seen_players.add(key)
            except Exception as exc:
                errors.append(f"{day} event={event_id}: {type(exc).__name__}: {exc}")
                continue
            return {"date": day, "event_id": event_id, "players": len(players),
                    "completed": completed, "errors": errors}
    return {"date": None, "event_id": None, "players": 0,
            "completed": completed, "errors": errors}


def main():
    result = check_recent_finals()
    for error in result["errors"]:
        print(f"WARNING: {error}", file=sys.stderr)
    if result["players"]:
        print(f"PASS ESPN final game {result['date']} event={result['event_id']}: "
              f"{result['players']} validated player rows")
        return 0
    print(f"FAIL: No verified ESPN final-game player rows; "
          f"{result['completed']} completed games attempted in seven days",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
