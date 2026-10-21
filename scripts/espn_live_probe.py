"""Live ESPN final-boxscore smoke check; never produces betting projections.

Run: python scripts/espn_live_probe.py
"""
from datetime import datetime, timedelta, timezone
import sys

from espn_history import espn_final_game_players
from espn_schedule import espn_games_on


def main():
    # Check several recent dates: off-days should not cause false failures.
    for offset in range(1, 8):
        day = (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
        games = espn_games_on(day)
        for game in games:
            if game.get("espnCompleted") is not True:
                continue
            event_id = game.get("espnEventId")
            if not event_id:
                continue
            players = espn_final_game_players(event_id)
            if not players:
                raise RuntimeError("Final ESPN game produced no player observations")
            print(f"PASS ESPN final game {day} event={event_id}: "
                  f"{len(players)} validated player rows")
            return 0
    print("FAIL: No completed ESPN NBA games found in the previous seven days",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
