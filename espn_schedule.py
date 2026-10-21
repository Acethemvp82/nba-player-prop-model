"""Independent NBA schedule fallback using ESPN's public scoreboard feed.

ESPN event IDs are NOT NBA game IDs and must never be sent to NBA box-score
endpoints. This adapter supplies date-specific matchup visibility only.
"""
import requests
from nba_data import NBADataError
from historical_stats import _day

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
# ESPN occasionally uses two-letter team abbreviations; NBA feeds use tricodes.
ESPN_TO_NBA = {"NY": "NYK", "GS": "GSW", "SA": "SAS", "NO": "NOP"}


def espn_games_on(day):
    parsed = _day(day)
    if parsed is None:
        raise ValueError("day must be a valid date")
    try:
        response = requests.get(ESPN_URL, params={"dates": parsed.strftime("%Y%m%d")},
                                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                                timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise NBADataError(f"Backup NBA schedule unavailable: {exc}") from exc
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        raise NBADataError("Backup NBA schedule has no events list")
    games = []
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        competitions = event.get("competitions")
        if not isinstance(competitions, list) or not competitions or not isinstance(competitions[0], dict):
            continue
        competitors = competitions[0].get("competitors")
        if not isinstance(competitors, list):
            continue
        sides = {}
        scores = {}
        team_ids = {}
        for item in competitors:
            if not isinstance(item, dict) or item.get("homeAway") not in ("home", "away"):
                continue
            team = item.get("team")
            if isinstance(team, dict):
                abbreviation = team.get("abbreviation")
                if (isinstance(abbreviation, str) and abbreviation.isascii()
                        and abbreviation.isalpha()):
                    code = abbreviation.upper()
                    code = ESPN_TO_NBA.get(code, code)
                    if len(code) == 3:
                        side = item["homeAway"]
                        sides[side] = code
                        identifier = team.get("id")
                        if isinstance(identifier, (str, int)) and not isinstance(identifier, bool) and str(identifier).isascii() and str(identifier).isdigit():
                            team_ids[side] = str(identifier)
                        score = item.get("score")
                        if isinstance(score, (str, int)) and not isinstance(score, bool):
                            value = str(score)
                            if value.isascii() and value.isdigit():
                                scores[side] = int(value)
        if len(sides) != 2 or sides["home"] == sides["away"]:
            continue
        matchup = (sides["away"], sides["home"])
        # Ignore an event whose competitors do not agree on the game sides.
        if len(competitors) != 2 or len(sides) != 2:
            continue
        event_id = str(event.get("id") or "")
        valid_event_id = event_id if event_id.isascii() and event_id.isdigit() else None
        # ESPN event IDs identify games; a repeated matchup may be a separate game.
        dedup_key = ("event", valid_event_id) if valid_event_id else ("matchup", matchup)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        games.append({
            "gameId": None,  # ESPN IDs are not compatible with NBA boxscore URLs.
            "espnEventId": valid_event_id,
            "homeTeam": {"teamTricode": sides["home"]},
            "awayTeam": {"teamTricode": sides["away"]},
            "espnTeamIds": team_ids,
            "gameTimeUTC": event.get("date"),
            "homeScore": scores.get("home"),
            "awayScore": scores.get("away"),
            "espnCompleted": (event["status"]["type"]["completed"]
                              if isinstance(event.get("status"), dict)
                              and isinstance(event["status"].get("type"), dict)
                              and isinstance(event["status"]["type"].get("completed"), bool)
                              else None),
            "gameStatusText": (event.get("status") or {}).get("type", {}).get("description")
            if isinstance(event.get("status"), dict) and isinstance(event["status"].get("type"), dict)
            else "Unknown",
            "source": "ESPN schedule fallback",
        })
    return games
