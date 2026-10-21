"""Date-specific NBA schedule adapter with strict input validation.

The official NBA scheduleLeagueV2 feed contains a season-long game list.
No historical box scores are inferred from schedule entries.
"""
from datetime import date
from nba_data import NBADataError, _get_json
from historical_stats import _day

SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

def season_schedule():
    payload = _get_json(SCHEDULE_URL)
    dates = payload.get("leagueSchedule", {}).get("gameDates")
    if not isinstance(dates, list):
        raise NBADataError("NBA season schedule response has no gameDates list.")
    return dates

def games_on(day, schedule=None):
    """Return scheduled NBA games for an ISO date, including final games.

    Requires a season schedule covering the requested date; an absent date is
    an empty slate, not permission to silently substitute today's games.
    """
    if isinstance(day, str):
        try:
            day = date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError("day must be an ISO date") from exc
    if not isinstance(day, date):
        raise ValueError("day must be a date")
    dates = season_schedule() if schedule is None else schedule
    if not isinstance(dates, list):
        raise NBADataError("Invalid season schedule.")
    games = []
    seen_ids = set()
    for entry in dates:
        if not isinstance(entry, dict):
            continue
        entry_day = _day(entry.get("gameDate"))
        entry_games = entry.get("games")
        if not isinstance(entry_games, list):
            continue
        for game in entry_games:
            if not isinstance(game, dict):
                continue
            game_day = _day(game.get("gameDateEst") or game.get("gameDate")) or entry_day
            game_id = str(game.get("gameId") or "")
            if game_day == day and game_id.isdigit() and game_id not in seen_ids:
                games.append(game)
                seen_ids.add(game_id)
    return games
