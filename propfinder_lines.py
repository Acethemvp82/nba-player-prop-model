"""FanDuel-only PropFinder export snapshots; no account credentials or scraping."""
import csv
import io
import json
import math
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
MARKETS = {'Points':'points', 'Rebounds':'rebounds', 'Assists':'assists',
           'Three Pointers':'threes', 'Steals':'steals', 'Blocks':'blocks'}


def player_key(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(name)).casefold()
                   if c.isalnum() and not unicodedata.combining(c))


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Snapshot timestamps must include a timezone')
    return result


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def counts(value, limit):
    match = re.fullmatch(r'\((\d+)/(\d+)\)', value.strip())
    if not match:
        return None
    hits, n = map(int, match.groups())
    return [hits, n] if 0 <= hits <= n <= limit and n > 0 else None


def export_snapshot(content, games, captured_at, *, fanduel_only=False):
    """Require explicit verified book context and dated slate because CSV omits both."""
    if not fanduel_only:
        raise ValueError('Verify FanDuel-only settings before importing this export')
    stamp(captured_at)
    teams = {}
    for game in games:
        start = stamp(game['start'])
        day = start.astimezone(ET).date().isoformat()
        for team, opponent in [(game['away'], game['home']), (game['home'], game['away'])]:
            if team in teams:
                raise ValueError('Ambiguous team/game mapping')
            teams[team] = {'opponent':opponent, 'day':day, 'start':game['start']}
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    required = {'Team','Player','Prop','L5','L10','L5 Avg','L10 Avg'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Expected a PropFinder research CSV')
    records = {}
    conflicts = set()
    for row in reader:
        match = re.fullmatch(r'o(\d+(?:\.\d+)?) (.+)', row['Prop'])
        if not match or match[2] not in MARKETS:
            continue  # Full-game core stats only; alternate export must stay disabled.
        team = row['Team'].strip()
        if team not in teams:
            continue
        line = float(match[1])
        if not finite(line) or line < 0 or not row['Player'].strip():
            continue
        record = {'player':row['Player'].strip(), 'team':team, **teams[team],
                  'stat':MARKETS[match[2]], 'line':line,
                  'l5_over':counts(row.get('L5',''), 5),
                  'l10_over':counts(row.get('L10',''), 10),
                  'h2h_over':counts(row.get('H2H',''), 500)}
        key = (team, player_key(record['player']), record['stat'])
        if key in records and records[key] != record:
            conflicts.add(key)
        records[key] = record
    return {'version':1, 'source':'PropFinder research export', 'bookmaker':'FanDuel',
            'captured_at':captured_at, 'refresh':'Export snapshot; refreshed when a new export is published',
            'records':[r for k,r in records.items() if k not in conflicts]}


def apply_snapshot(frame, snapshot, day, stat, now=None):
    """Fail closed on stale, ambiguous, wrong-day/opponent/stat or started games."""
    result = frame.copy()
    result['Line'] = None
    now = now or datetime.now(timezone.utc)
    health = {'matched':0, 'message':'No FanDuel snapshot is available for this slate.'}
    if not isinstance(snapshot, dict) or snapshot.get('version') != 1 or snapshot.get('bookmaker') != 'FanDuel':
        return result, health
    try:
        captured = stamp(snapshot['captured_at'])
        age = now - captured
    except (KeyError, TypeError, ValueError, AttributeError):
        return result, health
    health['captured_at'] = captured.astimezone(ET).strftime('%b %d, %I:%M %p ET')
    if not timedelta(minutes=-2) <= age <= timedelta(hours=24):
        health['message'] = 'FanDuel export has expired. Lines remain N/A until a new snapshot is published.'
        return result, health
    lookup = {}
    for r in snapshot.get('records', []):
        try:
            start = stamp(r['start'])
            if r['day'] != day or start.astimezone(ET).date().isoformat() != day or r['stat'] != stat:
                continue
            if now >= start or captured >= start or not finite(r['line']) or r['line'] < 0:
                continue
            key = (r['team'], r['opponent'], player_key(r['player']))
            lookup[key] = r if key not in lookup else None
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    for index, row in result.iterrows():
        r = lookup.get((row.get('Team'), row.get('Opponent'), player_key(row.get('Player'))))
        if not r:
            continue
        result.at[index, 'Line'] = r['line']
        result.at[index, 'Line source'] = 'FanDuel via PropFinder export'
        result.at[index, 'Line captured'] = health['captured_at']
        result.at[index, 'Line captured ISO'] = captured.isoformat()
        result.at[index, 'Line stat'] = stat
        result.at[index, 'Line status'] = 'Pregame export snapshot — confirm the current line on your betting ticket'
        for key, label, limit in [('l5_over','PF L5 over',5), ('l10_over','PF L10 over',10), ('h2h_over','PF H2H over',500)]:
            count = r.get(key)
            if isinstance(count,list) and len(count)==2 and all(type(x) is int for x in count):
                hits,n = count
                if 0 <= hits <= n <= limit and n:
                    result.at[index,label] = f'{hits}/{n} ({hits/n:.0%})'
        health['matched'] += 1
    health['message'] = f"{health['matched']} players have a FanDuel line for this stat. Missing, started or unmatched markets stay N/A."
    return result, health


def load_snapshot(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
