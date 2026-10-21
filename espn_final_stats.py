"""Validated ESPN final-game player stat observations (separate from NBA IDs).

This parser never treats an ESPN roster candidate as a completed-game result.
"""
from nba_data import NBADataError
from espn_schedule import ESPN_TO_NBA


def _whole(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    raw = str(value)
    return int(raw) if raw.isascii() and raw.isdigit() else None


def parse_final_espn_boxscore(payload, expected_event_id):
    """Parse ESPN boxscore statistics only for a confirmed final event."""
    if not isinstance(payload, dict):
        raise NBADataError("Invalid ESPN game summary")
    event_id = str(expected_event_id)
    if not event_id.isascii() or not event_id.isdigit():
        raise NBADataError("Invalid ESPN event ID")
    header = payload.get("header")
    competitions = header.get("competitions") if isinstance(header, dict) else None
    if not isinstance(competitions, list) or not competitions:
        raise NBADataError("ESPN game finality cannot be verified")
    competition = next((entry for entry in competitions if isinstance(entry, dict)
                        and str(entry.get("id")) == event_id), None)
    if competition is None:
        raise NBADataError("ESPN game ID mismatch")
    status = competition.get("status")
    status_type = status.get("type") if isinstance(status, dict) else None
    if not isinstance(status_type, dict) or status_type.get("completed") is not True:
        raise NBADataError("ESPN game is not verified final")
    boxscore = payload.get("boxscore")
    groups = boxscore.get("players") if isinstance(boxscore, dict) else None
    if not isinstance(groups, list):
        raise NBADataError("ESPN final game has no player boxscore")
    output = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        team = group.get("team")
        code = team.get("abbreviation") if isinstance(team, dict) else None
        if not isinstance(code, str) or not code.isascii():
            continue
        code = ESPN_TO_NBA.get(code.upper(), code.upper())
        if len(code) != 3 or not code.isalpha():
            continue
        sections = group.get("statistics")
        if not isinstance(sections, list):
            continue
        for section in sections:
            if not isinstance(section, dict):
                continue
            labels = section.get("labels") or section.get("keys")
            athletes = section.get("athletes")
            if not isinstance(labels, list) or not isinstance(athletes, list):
                continue
            indexes = {label.strip().upper(): i for i, label in enumerate(labels)
                       if isinstance(label, str)}
            if not all(key in indexes for key in ("PTS", "REB", "AST", "3PT")):
                continue
            for item in athletes:
                if not isinstance(item, dict) or item.get("didNotPlay") is True or item.get("didNotPlay") == "true":
                    continue
                athlete = item.get("athlete")
                values = item.get("stats")
                if not isinstance(athlete, dict) or not isinstance(values, list):
                    continue
                aid = _whole(athlete.get("id"))
                name = athlete.get("displayName")
                if aid is None or not isinstance(name, str) or not name.strip():
                    continue
                def read(key):
                    idx = indexes[key]
                    return _whole(values[idx]) if idx < len(values) else None
                points, rebounds, assists = (read(key) for key in ("PTS", "REB", "AST"))
                three_idx = indexes["3PT"]
                three_text = values[three_idx] if three_idx < len(values) else None
                # ESPN 3PT is made-attempted (e.g. 3-7), not a plain count.
                # Reject malformed strings and impossible made > attempted values.
                threes = None
                if isinstance(three_text, str):
                    parts = three_text.split("-")
                    if len(parts) == 2:
                        made, attempted = _whole(parts[0]), _whole(parts[1])
                        if made is not None and attempted is not None and made <= attempted:
                            threes = made
                if None in (points, rebounds, assists, threes):
                    continue
                key = (aid, code)
                if key in seen:
                    continue
                seen.add(key)
                output.append({"player_id": f"espn:{aid}", "player": name.strip(),
                               "team": code, "points": points, "rebounds": rebounds,
                               "assists": assists, "threes": threes,
                               "source": "ESPN verified final boxscore"})
    if not output:
        raise NBADataError("ESPN final boxscore has no validated player statistics")
    return output
