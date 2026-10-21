"""Bounded historical NBA box-score collection.

Collect only FINAL games with a date strictly earlier than the requested
as-of date. Never replace missing or failed box scores with fabricated stats.
"""
from nba_data import NBADataError, _get_json, BASE
from player_stats import completed_game_observations
from historical_stats import _day, player_history_summaries

def fetch_boxscore_players(game_id):
    if not str(game_id).isdigit():
        raise NBADataError("Invalid NBA game ID")
    payload = _get_json(f"{BASE}/boxscore/boxscore_{game_id}.json")
    game = payload.get("game")
    if not isinstance(game, dict) or str(game.get("gameId")) != str(game_id):
        raise NBADataError("Box score game ID mismatch")
    if str(game.get("gameStatus")) != "3":
        raise NBADataError("Box score is not final")
    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    home_code = home.get("teamTricode")
    away_code = away.get("teamTricode")
    if not home_code or not away_code or home_code == away_code:
        raise NBADataError("Final NBA box score is missing distinct team identities")
    if not isinstance(home.get("players"), list) or not isinstance(away.get("players"), list):
        raise NBADataError("Final NBA box score is missing team player lists")
    players = []
    for side, opposite in (("homeTeam", "awayTeam"), ("awayTeam", "homeTeam")):
        team = game.get(side) or {}
        other = game.get(opposite) or {}
        for p in team.get("players") or []:
            players.append({"player_id": p.get("personId"), "player": p.get("name"),
                            "team": team.get("teamTricode"),
                            "opponent": other.get("teamTricode"),
                            "statistics": p.get("statistics") or {}})
    return players

def collect_recent_history(schedule, as_of, max_games=80, loader=fetch_boxscore_players):
    """Return observations and collection diagnostics.

    Custom loaders must return players ONLY for verified final box scores.

    The game budget caps network calls; failed games are reported and omitted.
    It does not imply full-season coverage.
    """
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid date")
    if not isinstance(max_games, int) or isinstance(max_games, bool) or not 1 <= max_games <= 500:
        raise ValueError("max_games must be between 1 and 500")
    eligible = []
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        entry_day = _day(entry.get("gameDate"))
        for game in entry.get("games", []):
            if not isinstance(game, dict):
                continue
            # Static schedules can have stale statuses; finality is verified
            # against each box score by the default loader.
            if str(game.get("gameStatus")) == "2":
                continue
            played = _day(game.get("gameDateEst") or game.get("gameDate")) or entry_day
            gid = str(game.get("gameId") or "")
            if played is not None and played < cutoff and gid.isdigit():
                eligible.append((played, gid, {**game, "gameDateEst": played.isoformat()}))
    eligible.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = []
    seen = set()
    for _, gid, game in eligible:
        if gid in seen:
            continue
        seen.add(gid)
        if len(selected) < max_games:
            selected.append({**game, "gameStatus": 3})
    errors = []
    loaded = []
    def safe_loader(gid):
        try:
            players = loader(gid)
            if not isinstance(players, list):
                raise NBADataError("Box score player list is invalid")
            loaded.append(gid)
            return players
        except (NBADataError, ValueError, TypeError, KeyError) as exc:
            errors.append({"game_id": gid, "error": str(exc)})
            return []
    observations = completed_game_observations(selected, safe_loader)
    return {"observations": observations,
            "games_requested": len(selected),
            "games_loaded": len(loaded),
            "failed_games": errors,
            "eligible_games": len(seen)}

def recent_player_summaries(schedule, as_of, max_games=80, loader=fetch_boxscore_players):
    collected = collect_recent_history(schedule, as_of, max_games, loader)
    collected["summaries"] = player_history_summaries(collected["observations"], as_of=as_of)
    return collected
