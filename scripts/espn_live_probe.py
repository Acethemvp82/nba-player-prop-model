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
                        boxscore_loader=espn_final_game_players):
    """Try multiple recent finals, preserving errors for troubleshooting.

    One unavailable boxscore should not mask another valid final game.
    """
    today = today or datetime.now(timezone.utc).date()
    errors = []
    completed = 0
    for offset in range(1, days + 1):
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
            if not isinstance(game, dict) or game.get("espnCompleted") is not True:
                continue
            event_id = game.get("espnEventId")
            if not (isinstance(event_id, str) and event_id.isascii()
                    and event_id.isdigit()):
                continue
            completed += 1
            try:
                players = boxscore_loader(event_id)
                if not players:
                    raise ValueError("No validated player observations")
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
