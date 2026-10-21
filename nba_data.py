"""NBA public schedule and roster feed; no sportsbook data or projections."""
from datetime import date
import requests

BASE = "https://cdn.nba.com/static/json/liveData"
HEADERS = {"User-Agent": "NBAPropResearch/0.1 (public schedule research)"}

class NBADataError(RuntimeError):
    pass

def _get_json(url: str) -> dict:
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected JSON root")
        return data
    except (requests.RequestException, ValueError) as exc:
        raise NBADataError(f"NBA data unavailable: {exc}") from exc

def scoreboard(day: date | None = None) -> list[dict]:
    """Return games from NBA's public scoreboard. Current-day endpoint only.

    For other dates, do not silently show today's games.
    """
    if day is not None and day != date.today():
        raise NBADataError("Historical/future date-specific schedule is not connected yet.")
    payload = _get_json(f"{BASE}/scoreboard/todaysScoreboard_00.json")
    games = payload.get("scoreboard", {}).get("games")
    if not isinstance(games, list):
        raise NBADataError("NBA scoreboard response has no games list.")
    return games

def game_players(game_id: str) -> list[dict]:
    """Read players listed in the public live box score for a game."""
    if not str(game_id).isdigit():
        raise NBADataError("Invalid NBA game ID.")
    payload = _get_json(f"{BASE}/boxscore/boxscore_{game_id}.json")
    game = payload.get("game")
    if not isinstance(game, dict) or str(game.get("gameId")) != str(game_id):
        raise NBADataError("NBA box score game ID mismatch or missing game data.")
    result = []
    for side in ("homeTeam", "awayTeam"):
        team = game.get(side) or {}
        for player in team.get("players") or []:
            result.append({
                "player_id": player.get("personId"),
                "player": player.get("name"),
                "team": team.get("teamTricode"),
                "opponent": (game.get("awayTeam" if side == "homeTeam" else "homeTeam") or {}).get("teamTricode"),
                "status": player.get("status"),
                "statistics": player.get("statistics", {}),
            })
    return result
