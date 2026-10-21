"""Fetch verified final NBA player results for games in saved snapshots.

Uses NBA-CDN IDs only; ESPN event/athlete identifiers are not compatible.
Network errors are reported per game and never converted to losses.
"""
from history_collection import fetch_boxscore_players
from player_stats import normalize_player_boxscore
from nba_data import NBADataError
from pregame_snapshot import validate_pregame_snapshot


def collect_snapshot_finals(snapshots, loader=fetch_boxscore_players, max_games=20):
    if type(max_games) is not int or not 1 <= max_games <= 100:
        raise ValueError("max_games must be 1..100")
    ids = set()
    for row in snapshots:
        valid, _ = validate_pregame_snapshot(row)
        if valid:
            ids.add(str(row["game_id"]))
    ordered = sorted(ids)
    selected = ordered[:max_games]
    failures = []
    observations = []
    for gid in selected:
        try:
            players = loader(gid)
            if not isinstance(players, list) or not players:
                raise NBADataError("Empty final box score")
            seen = set()
            normalized = []
            for player in players:
                record = normalize_player_boxscore(player, gid, final=True)
                pid = str(record.get("player_id") or "") if record else ""
                if not pid.isascii() or not pid.isdigit() or pid in seen:
                    raise NBADataError("Invalid or duplicate player in final box score")
                seen.add(pid)
                normalized.append(record)
            observations.extend(normalized)
        except (NBADataError, ValueError, TypeError, KeyError, OSError) as exc:
            failures.append({"game_id": gid, "error": str(exc)})
    return {"final_players": observations, "games_requested": len(selected),
            "games_omitted_by_limit": max(0, len(ordered) - max_games),
            "games_loaded": len(selected) - len(failures), "failures": failures}
