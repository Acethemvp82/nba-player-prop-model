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
                        sides[item["homeAway"]] = code
        if len(sides) != 2 or sides["home"] == sides["away"]:
            continue
        games.append({
            "gameId": None,  # ESPN IDs are not compatible with NBA boxscore URLs.
            "homeTeam": {"teamTricode": sides["home"]},
            "awayTeam": {"teamTricode": sides["away"]},
            "gameTimeUTC": event.get("date"),
            "gameStatusText": (event.get("status") or {}).get("type", {}).get("description")
            if isinstance(event.get("status"), dict) and isinstance(event["status"].get("type"), dict)
            else "Unknown",
            "source": "ESPN schedule fallback",
        })
    return games
