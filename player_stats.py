"""Normalize NBA box-score statistics; never mistake results for projections."""
from datetime import timedelta
import re

STAT_FIELDS = {
    "points": "points",
    "rebounds": "reboundsTotal",
    "assists": "assists",
    "threes": "threePointersMade",
}
_DURATION = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$")

def parse_minutes(value):
    """NBA live feeds use ISO-8601 durations such as PT28M31.00S."""
    if not isinstance(value, str):
        return None
    match = _DURATION.fullmatch(value)
    if not match or not any(part is not None for part in match.groups()):
        return None
    hours, minutes, seconds = match.groups()
    return round(int(hours or 0) * 60 + int(minutes or 0) + float(seconds or 0) / 60, 2)

def normalize_player_boxscore(player, game_id, final=False):
    """Return one game observation, never a predictive input unless final=True."""
    stats = player.get("statistics") or {}
    record = {
        "game_id": str(game_id),
        "player_id": player.get("player_id"),
        "player": player.get("player"),
        "team": player.get("team"),
        "opponent": player.get("opponent"),
        "is_final": bool(final),
        "minutes": parse_minutes(stats.get("minutes")),
    }
    for label, field in STAT_FIELDS.items():
        value = stats.get(field)
        record[label] = value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None
    return record

def completed_game_observations(games, player_loader):
    """Collect results only for completed games, ignoring live and future games."""
    records = []
    for game in games:
        if game.get("gameStatus") != 3:
            continue
        game_id = str(game.get("gameId") or "")
        if not game_id.isdigit():
            continue
        for player in player_loader(game_id):
            record = normalize_player_boxscore(player, game_id, final=True)
            if record["player_id"] is not None and record["minutes"] is not None:
                records.append(record)
    return records
