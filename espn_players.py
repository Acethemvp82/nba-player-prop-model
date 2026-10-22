"""ESPN game-summary player listings for schedule fallback.

ESPN athlete identifiers are namespaced and must never be used as NBA IDs.
Player listings do not establish pregame active status or validated statistics.
"""
import requests
from nba_data import NBADataError
from espn_schedule import ESPN_TO_NBA

SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"


def espn_game_players(event_id):
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
        raise NBADataError(f"ESPN player listing unavailable: {exc}") from exc
    if not isinstance(payload, dict):
        raise NBADataError("Invalid ESPN game summary")
    boxscore = payload.get("boxscore")
    groups = boxscore.get("players") if isinstance(boxscore, dict) else None
    if not isinstance(groups, list):
        raise NBADataError("ESPN summary does not provide player listings yet")
    result = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        team = group.get("team")
        code = team.get("abbreviation") if isinstance(team, dict) else None
        if not isinstance(code, str) or not code.isascii() or not code.isalpha():
            continue
        code = ESPN_TO_NBA.get(code.upper(), code.upper())
        if len(code) != 3:
            continue
        statistics = group.get("statistics")
        if not isinstance(statistics, list):
            continue
        for category in statistics:
            athletes = category.get("athletes") if isinstance(category, dict) else None
            if not isinstance(athletes, list):
                continue
            for item in athletes:
                athlete = item.get("athlete") if isinstance(item, dict) else None
                if not isinstance(athlete, dict):
                    continue
                athlete_id = athlete.get("id")
                name = athlete.get("displayName")
                if (not isinstance(athlete_id, (str, int)) or isinstance(athlete_id, bool)
                        or not str(athlete_id).isascii() or not str(athlete_id).isdigit()
                        or not isinstance(name, str) or not name.strip()):
                    continue
                key = (str(athlete_id), code)
                if key in seen:
                    continue
                seen.add(key)
                result.append({"player_id": f"espn:{athlete_id}", "player": name.strip(),
                               "team": code, "source": "ESPN game summary (unconfirmed)"})
    if not result:
        raise NBADataError("ESPN game summary has no usable player listings; pregame rosters may not be published")
    return result


ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"


def espn_team_roster(team_id, expected_team):
    """Retrieve ESPN team roster candidates, NOT confirmed active players."""
    if (not isinstance(team_id, (str, int)) or isinstance(team_id, bool)
            or not str(team_id).isascii() or not str(team_id).isdigit()):
        raise NBADataError("Invalid ESPN team ID")
    if not isinstance(expected_team, str) or len(expected_team) != 3 or not expected_team.isascii() or not expected_team.isalpha():
        raise NBADataError("Invalid expected NBA team code")
    try:
        response = requests.get(ROSTER_URL.format(team_id=team_id),
                                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                                timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise NBADataError(f"ESPN team roster unavailable: {exc}") from exc
    if not isinstance(payload, dict):
        raise NBADataError("Invalid ESPN team roster")
    team = payload.get("team")
    if isinstance(team, dict):
        actual = team.get("abbreviation")
        if isinstance(actual, str):
            actual = ESPN_TO_NBA.get(actual.upper(), actual.upper())
            if actual != expected_team:
                raise NBADataError("ESPN roster team does not match scheduled team")
    athletes = payload.get("athletes")
    if not isinstance(athletes, list):
        raise NBADataError("ESPN team roster has no athletes list")
    result = []
    seen = set()
    expanded = []
    for entry in athletes:
        if not isinstance(entry, dict):
            continue
        nested = entry.get("items")
        if isinstance(nested, list):
            expanded.extend(item for item in nested if isinstance(item, dict))
        else:
            expanded.append(entry)
    for athlete in expanded:
        profile = athlete.get("athlete") if isinstance(athlete.get("athlete"), dict) else athlete
        identifier = profile.get("id")
        name = profile.get("displayName")
        if (not isinstance(identifier, (str, int)) or isinstance(identifier, bool)
                or not str(identifier).isascii() or not str(identifier).isdigit()
                or not isinstance(name, str) or not name.strip()):
            continue
        if str(identifier) in seen:
            continue
        seen.add(str(identifier))
        result.append({"player_id": f"espn:{identifier}", "player": name.strip(),
                       "team": expected_team, "position": (profile.get("position") or {}).get("abbreviation"),
                       "source": "ESPN team roster (unconfirmed)"})
    if not result:
        raise NBADataError("ESPN team roster has no usable athletes")
    return result
