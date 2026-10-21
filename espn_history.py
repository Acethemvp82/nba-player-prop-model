"""Bounded ESPN historical observations, isolated from NBA-CDN player IDs."""
from datetime import timedelta
import requests
from nba_data import NBADataError
from historical_stats import _day
from espn_schedule import espn_games_on
from espn_players import SUMMARY_URL
from espn_final_stats import parse_final_espn_boxscore


def espn_final_game_players(event_id):
    if (not isinstance(event_id, (str, int)) or isinstance(event_id, bool)
            or not str(event_id).isascii() or not str(event_id).isdigit()):
        raise NBADataError("Invalid ESPN event ID")
    try:
        response = requests.get(SUMMARY_URL, params={"event": str(event_id)},
                                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                                timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise NBADataError(f"ESPN historical boxscore unavailable: {exc}") from exc
    return parse_final_espn_boxscore(payload, event_id)


def collect_espn_history(as_of, days=7, max_games=30,
                         schedule_loader=espn_games_on, boxscore_loader=espn_final_game_players):
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("Invalid as-of date")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 30:
        raise ValueError("days must be between 1 and 30")
    if isinstance(max_games, bool) or not isinstance(max_games, int) or not 1 <= max_games <= 100:
        raise ValueError("max_games must be between 1 and 100")
    observations, failures = [], []
    games_requested = games_loaded = 0
    seen = set()
    for offset in range(1, days + 1):
        day = cutoff - timedelta(days=offset)
        try:
            games = schedule_loader(day.isoformat())
        except (NBADataError, ValueError, TypeError) as exc:
            failures.append({"date": day.isoformat(), "error": str(exc)})
            continue
        if not isinstance(games, list):
            failures.append({"date": day.isoformat(), "error": "Invalid schedule"})
            continue
        for game in games:
            if games_requested >= max_games:
                break
            if not isinstance(game, dict):
                continue
            eid = game.get("espnEventId")
            if not isinstance(eid, str) or not eid.isascii() or not eid.isdigit() or eid in seen:
                continue
            seen.add(eid)
            games_requested += 1
            try:
                players = boxscore_loader(eid)
                if not isinstance(players, list) or not players:
                    raise NBADataError("No validated ESPN boxscore players")
                games_loaded += 1
                for player in players:
                    observations.append({**player, "game_id": f"espn:{eid}",
                                         "game_date": day.isoformat()})
            except (NBADataError, ValueError, TypeError, KeyError) as exc:
                failures.append({"event_id": eid, "date": day.isoformat(), "error": str(exc)})
        if games_requested >= max_games:
            break
    return {"observations": observations, "games_requested": games_requested,
            "games_loaded": games_loaded, "failures": failures,
            "source": "ESPN verified final boxscores"}
