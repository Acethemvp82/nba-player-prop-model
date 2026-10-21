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
    dates_checked = 0
    games_requested = games_loaded = 0
    seen = set()
    for offset in range(1, days + 1):
        day = cutoff - timedelta(days=offset)
        dates_checked += 1
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
            # Explicitly unfinished games cannot contribute final boxscore history.
            # Unknown finality is still checked by the strict summary parser.
            if game.get("espnCompleted") is False:
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
                valid_players = [
                    player for player in players
                    if isinstance(player, dict)
                    and player.get("source") == "ESPN verified final boxscore"
                    and isinstance(player.get("player_id"), str)
                    and player["player_id"].startswith("espn:")
                    and player["player_id"][5:].isascii()
                    and player["player_id"][5:].isdigit()
                    and isinstance(player.get("player"), str)
                    and bool(player["player"].strip())
                    and isinstance(player.get("team"), str)
                    and len(player["team"]) == 3
                    and player["team"].isascii()
                    and player["team"].isalpha()
                    and player["team"].isupper()
                    and all(type(player.get(prop)) is int and player[prop] >= 0
                            for prop in ("points", "rebounds", "assists", "threes"))
                ]
                # When the scoreboard provides both teams, never attach player
                # statistics from an unrelated matchup to this game.
                home = game.get("homeTeam")
                away = game.get("awayTeam")
                expected_teams = (
                    {home["teamTricode"], away["teamTricode"]}
                    if isinstance(home, dict) and isinstance(away, dict)
                    and isinstance(home.get("teamTricode"), str)
                    and isinstance(away.get("teamTricode"), str)
                    else None
                )
                if expected_teams is not None:
                    # A verified game has two distinct teams. Incomplete schedule
                    # metadata must not silently turn into a one-team filter.
                    if len(expected_teams) != 2 or any(
                            not isinstance(team, str) or len(team) != 3
                            or not team.isascii() or not team.isalpha()
                            or not team.isupper() for team in expected_teams):
                        raise NBADataError("Invalid ESPN scheduled matchup teams")
                    valid_players = [player for player in valid_players
                                     if player["team"] in expected_teams]
                if not valid_players:
                    raise NBADataError("No validated ESPN player observations for this matchup")
                # A provider response may repeat the same athlete in multiple
                # stat sections. Count one verified player-game per ESPN ID/team.
                unique_players = {}
                for player in valid_players:
                    unique_players.setdefault((player["player_id"], player["team"]), player)
                games_loaded += 1
                for player in unique_players.values():
                    observations.append({**player, "game_id": f"espn:{eid}",
                                         "game_date": day.isoformat()})
            except (NBADataError, ValueError, TypeError, KeyError) as exc:
                failures.append({"event_id": eid, "date": day.isoformat(), "error": str(exc)})
        if games_requested >= max_games:
            break
    return {"observations": observations, "dates_checked": dates_checked,
            "games_requested": games_requested,
            "games_loaded": games_loaded, "failures": failures,
            "source": "ESPN verified final boxscores"}
