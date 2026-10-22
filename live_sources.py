"""Public injury reporting and an optional authenticated FanDuel odds adapter."""
from datetime import datetime, timezone
from math import isfinite
import re
import unicodedata
import requests
from espn_schedule import ESPN_TO_NBA
from prop_probability import american_odds_break_even

INJURIES_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'
ODDS_ROOT = 'https://api.the-odds-api.com/v4/sports/basketball_nba'
MARKETS = {'points':'player_points','rebounds':'player_rebounds','assists':'player_assists','threes':'player_threes'}
TEAM_NAMES = dict(zip(
    'ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WSH'.split(),
    ['Atlanta Hawks','Boston Celtics','Brooklyn Nets','Charlotte Hornets','Chicago Bulls','Cleveland Cavaliers','Dallas Mavericks','Denver Nuggets','Detroit Pistons','Golden State Warriors','Houston Rockets','Indiana Pacers','Los Angeles Clippers','Los Angeles Lakers','Memphis Grizzlies','Miami Heat','Milwaukee Bucks','Minnesota Timberwolves','New Orleans Pelicans','New York Knicks','Oklahoma City Thunder','Orlando Magic','Philadelphia 76ers','Phoenix Suns','Portland Trail Blazers','Sacramento Kings','San Antonio Spurs','Toronto Raptors','Utah Jazz','Washington Wizards']))
NAME_TEAMS = {v:k for k,v in TEAM_NAMES.items()}
NAME_TEAMS['LA Clippers'] = 'LAC'


def normalized_name(value):
    if not isinstance(value, str): return ''
    value = unicodedata.normalize('NFKD', value)
    return re.sub(r'[^a-z0-9]', '', value.encode('ascii','ignore').decode().lower())


def utc(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError, AttributeError): return None


def parse_injuries(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('injuries'),list):
        raise ValueError('Invalid injury feed')
    output = {}
    for group in payload['injuries']:
        if not isinstance(group,dict): continue
        for injury in group.get('injuries',[]):
            if not isinstance(injury,dict): continue
            athlete = injury.get('athlete') or {}
            team = athlete.get('team') or {}
            code = ESPN_TO_NBA.get(team.get('abbreviation'),team.get('abbreviation'))
            name = normalized_name(athlete.get('displayName'))
            status = injury.get('status')
            if code not in TEAM_NAMES or not name or not isinstance(status,str): continue
            key = (code,name)
            record = {'status':status, 'reported_at':injury.get('date'),
                      'source':'ESPN injury report'}
            if key in output and output[key] != record:
                record = {'status':'Conflicting reports', 'reported_at':None, 'source':'ESPN injury report'}
            output[key] = record
    return output


def fetch_injuries():
    try:
        response = requests.get(INJURIES_URL, timeout=12)
        response.raise_for_status()
        payload = response.json()
        return {'reports':parse_injuries(payload), 'feed_timestamp':payload.get('timestamp'),
                'retrieved_at':datetime.now(timezone.utc).isoformat()}
    except (requests.RequestException, ValueError, TypeError):
        raise ValueError('Injury source unavailable; status remains unknown') from None


def reported_status(feed, player, team, now):
    stamp = utc(feed.get('feed_timestamp'))
    if stamp is None or not -120 <= (now - stamp).total_seconds() <= 3600:
        return 'Report stale / unavailable'
    return feed.get('reports',{}).get((team,normalized_name(player)),{}).get('status','Not listed — unconfirmed')


def _odds_get(path, key, params=None):
    if not isinstance(key,str) or not key.strip(): raise ValueError('ODDS_API_KEY is not configured')
    try:
        response = requests.get(ODDS_ROOT + path, params={'apiKey':key, **(params or {})}, timeout=12)
        if response.status_code != 200:
            raise ValueError(f'Odds provider returned HTTP {response.status_code}; check key, access and quota')
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        # Never expose exception URLs: the provider key is a query parameter.
        if isinstance(exc,ValueError) and str(exc).startswith('Odds provider returned HTTP'):
            raise ValueError(str(exc)) from None
        raise ValueError('Odds source unavailable or response invalid') from None


def fetch_event_odds(key, team, opponent, slate_date, now):
    from zoneinfo import ZoneInfo
    events = _odds_get('/events',key)
    if not isinstance(events,list): raise ValueError('Invalid odds event list')
    matches = []
    for event in events:
        if not isinstance(event,dict): continue
        start = utc(event.get('commence_time'))
        sides = {NAME_TEAMS.get(event.get('home_team')), NAME_TEAMS.get(event.get('away_team'))}
        if start and start > now and start.astimezone(ZoneInfo('America/New_York')).date().isoformat() == slate_date and sides == {team,opponent}:
            if isinstance(event.get('id'),str) and re.fullmatch(r'[a-zA-Z0-9_-]+',event['id']): matches.append(event)
    if len(matches) != 1: raise ValueError('No unique upcoming sportsbook event for this matchup and date')
    event = matches[0]
    payload = _odds_get('/events/' + event['id'] + '/odds',key,
        {'bookmakers':'fanduel','markets':','.join(MARKETS.values()),'oddsFormat':'american'})
    if not isinstance(payload,dict) or payload.get('id') != event['id']:
        raise ValueError('Odds response does not match requested event')
    return payload


def select_quote(payload, player, prop, now):
    if prop not in MARKETS: return None
    start = utc(payload.get('commence_time'))
    if not start or start <= now: return None
    quotes = []
    for book in payload.get('bookmakers',[]):
        if not isinstance(book,dict) or book.get('key') != 'fanduel': continue
        for market in book.get('markets',[]):
            if not isinstance(market,dict) or market.get('key') != MARKETS[prop]: continue
            stamp = market.get('last_update') or book.get('last_update')
            parsed = utc(stamp)
            if not parsed or not -120 <= (now-parsed).total_seconds() <= 1800: continue
            for outcome in market.get('outcomes',[]):
                if not isinstance(outcome,dict) or outcome.get('name') != 'Over': continue
                line, odds = outcome.get('point'), outcome.get('price')
                if (normalized_name(outcome.get('description')) == normalized_name(player)
                    and type(line) in (int,float) and isfinite(line) and line >= 0
                    and american_odds_break_even(odds) is not None):
                    quotes.append({'line':line,'odds':odds,'updated_at':stamp,'book':'FanDuel'})
    unique = {(q['line'],q['odds'],q['updated_at']):q for q in quotes}
    return next(iter(unique.values())) if len(unique) == 1 else None
