"""Auditable opening possessions from ESPN final, regular-season summaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import requests

from espn_schedule import ESPN_TO_NBA
from espn_players import SUMMARY_URL, espn_team_roster
from slate_evidence import team_events, regular_event

ET = ZoneInfo('America/New_York')
SOURCE = 'ESPN final play-by-play'


def identifier(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Missing ESPN identifier')
    text = str(value)
    if not text.isascii() or not text.isdigit():
        raise ValueError('Invalid ESPN identifier')
    return text


def fetch_summary(event_id):
    event_id = identifier(event_id)
    response = requests.get(SUMMARY_URL, params={'event': event_id}, timeout=15)
    response.raise_for_status()
    return response.json()


def parse_opening(payload, event_id):
    """Fail closed on incomplete scoring sequences; do not infer scorers from text."""
    event_id = identifier(event_id)
    header = payload['header']
    competition, = [c for c in header['competitions'] if str(c.get('id')) == event_id]
    if header.get('id') != event_id or competition['status']['type'].get('completed') is not True:
        raise ValueError('Event is not a matching verified final')
    if header['season']['type'] != 2:
        raise ValueError('Only regular-season games are supported')
    start = datetime.fromisoformat(competition['date'].replace('Z', '+00:00'))
    if start.tzinfo is None:
        raise ValueError('Game time has no timezone')
    teams, sides, scores = {}, {}, {}
    for c in competition['competitors']:
        tid = identifier(c['team']['id'])
        code = c['team']['abbreviation'].upper()
        code = ESPN_TO_NBA.get(code, code)
        side = c['homeAway']
        if side not in ('home', 'away') or side in sides or len(code) != 3:
            raise ValueError('Invalid matchup')
        sides[side] = code
        teams[tid] = code
        scores[side] = int(c['score'])
    if len(teams) != 2 or len(set(sides.values())) != 2:
        raise ValueError('Incomplete matchup')
    athletes, starters = {}, {t: [] for t in teams.values()}
    for group in payload['boxscore']['players']:
        tid = identifier(group['team']['id'])
        if tid not in teams:
            raise ValueError('Boxscore team outside matchup')
        for section in group['statistics']:
            for a in section['athletes']:
                profile = a['athlete']
                pid = 'espn:' + identifier(profile['id'])
                row = {'player_id': pid, 'player': profile['displayName'], 'team': teams[tid],
                       'position': (profile.get('position') or {}).get('abbreviation', '?')}
                if pid in athletes and athletes[pid] != row:
                    raise ValueError('Conflicting player identities')
                athletes[pid] = row
                if a.get('starter') is True and pid not in starters[teams[tid]]:
                    starters[teams[tid]].append(pid)
    if any(len(pids) != 5 for pids in starters.values()):
        raise ValueError('Five actual starters per team are required')
    plays = payload.get('plays')
    if not isinstance(plays, list) or not plays:
        raise ValueError('Full play-by-play unavailable')
    plays = sorted(plays, key=lambda p: int(identifier(p['sequenceNumber'])))
    sequences = [p['sequenceNumber'] for p in plays]
    if len(set(sequences)) != len(sequences):
        raise ValueError('Duplicate play sequence')
    opening = plays[0]
    if (opening['period']['number'] != 1 or opening['clock']['displayValue'] != '12:00'
            or opening.get('homeScore') != 0 or opening.get('awayScore') != 0):
        raise ValueError('Opening sequence is missing')
    first_points = first_fg = first_shot = None
    team_shots, team_points, team_fgs = {}, {}, {}
    prior = {'home': 0, 'away': 0}
    # Later-period score corrections do not change an already settled opening
    # market. Validate the opening sequence through both teams' first FGs.
    for play in plays:
        current = {side: play[side + 'Score'] for side in ('home', 'away')}
        if any(type(v) is not int or v < 0 for v in current.values()):
            raise ValueError('Invalid score in play sequence')
        delta = {s: current[s] - prior[s] for s in current}
        if any(v < 0 for v in delta.values()):
            raise ValueError('Score correction requires review')
        scoring = sum(delta.values()) > 0
        if scoring != (play.get('scoringPlay') is True):
            raise ValueError('Missing or inconsistent scoring play')
        shot = play.get('shootingPlay') is True and play.get('pointsAttempted') in (2, 3)
        if scoring or shot:
            tid = identifier(play['team']['id'])
            if tid not in teams:
                raise ValueError('Play team outside matchup')
            team = teams[tid]
            pid = 'espn:' + identifier(play['participants'][0]['athlete']['id'])
            if pid not in athletes or athletes[pid]['team'] != team:
                raise ValueError('Shooter identity does not match play team')
            side = next(s for s in sides if sides[s] == team)
            if scoring and (delta[side] != play.get('scoreValue') or delta[side] not in (1, 2, 3)
                            or delta[next(s for s in sides if s != side)] != 0):
                raise ValueError('Score delta does not match scorer')
            if shot:
                first_shot = first_shot or pid
                team_shots.setdefault(team, pid)
            if scoring:
                first_points = first_points or pid
                team_points.setdefault(team, pid)
                if shot:
                    first_fg = first_fg or pid
                    team_fgs.setdefault(team, pid)
        prior = current
        if len(team_fgs) == 2 and len(team_shots) == 2:
            break
    final_scores = {s: plays[-1].get(s+'Score') for s in ('home', 'away')}
    if final_scores != scores or not first_points or not first_fg or len(team_fgs) != 2:
        raise ValueError('Play-by-play does not reconcile to final scores')
    tip_team = None
    if 'jump' in opening.get('type', {}).get('text', '').lower():
        tip_team = teams.get(str(opening.get('team', {}).get('id')))
    return {'event_id': event_id, 'game_date': start.astimezone(ET).date().isoformat(),
            'season_year': header['season']['year'], 'season_type': 'regular',
            'teams': sides, 'starters': starters, 'players': athletes,
            'first_points': first_points, 'first_field_goal': first_fg,
            'first_shot': first_shot, 'team_first_shot': team_shots,
            'team_first_points': team_points, 'team_first_field_goal': team_fgs,
            'tip_winner': tip_team, 'source': SOURCE,
            'retrieved_at': datetime.now(timezone.utc).isoformat()}


def collect_history(day, games, existing=(), per_team=30, summary_loader=fetch_summary,
                    schedule_loader=team_events, roster_loader=espn_team_roster):
    """Latest games per team, deduped across opponents; no same-day training data."""
    cutoff = date.fromisoformat(day)
    if type(per_team) is not int or not 1 <= per_team <= 60:
        raise ValueError('per_team must be between 1 and 60')
    year = cutoff.year + (cutoff.month >= 7)
    ids = {g[s+'Team']['teamTricode']: g.get('espnTeamIds', {}).get(s)
           for g in games for s in ('home', 'away')}
    selected, rosters, failures = {}, [], []

    def team_data(item):
        team, tid = item
        events, roster, errors = {}, [], []
        try:
            roster = roster_loader(tid, team)
        except Exception as exc:
            errors.append({'team': team, 'stage': 'roster', 'error': type(exc).__name__})
        for season in (year, year-1):
            try:
                for e in schedule_loader(tid, season):
                    row = regular_event(e, day, team, season)
                    if row:
                        events[row['espnEventId']] = row
            except Exception as exc:
                errors.append({'team': team, 'stage': 'schedule', 'error': type(exc).__name__})
        latest = sorted(events.values(), key=lambda e: (e['game_date'], e['espnEventId']), reverse=True)[:per_team]
        return roster, latest, errors

    with ThreadPoolExecutor(max_workers=4) as pool:
        for roster, events, errors in pool.map(team_data, ids.items()):
            rosters.extend(roster)
            failures.extend(errors)
            selected.update({e['espnEventId']: e for e in events})
    cached = {r['event_id']: r for r in existing if r.get('source') == SOURCE}

    def load(event):
        eid = event['espnEventId']
        try:
            row = cached.get(eid) or parse_opening(summary_loader(eid), eid)
            expected = {event[s+'Team']['teamTricode'] for s in ('home', 'away')}
            if (set(row['teams'].values()) != expected or row['game_date'] != event['game_date']
                    or row['season_year'] != event['season_year'] or row['game_date'] >= day):
                raise ValueError('Historical event does not match schedule')
            return row, None
        except Exception as exc:
            return None, {'event_id': eid, 'stage': 'play-by-play', 'error': str(exc)[:180]}

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(load, selected.values()))
    history = [r for r, _ in results if r]
    failures.extend(e for _, e in results if e)
    memberships = {}
    for r in rosters:
        memberships.setdefault(r['player_id'], set()).add(r['team'])
    roster = list({(r['player_id'], r['team']): r for r in rosters
                   if len(memberships[r['player_id']]) == 1}.values())
    return {'games': history, 'roster': roster, 'failures': failures,
            'requested': len(selected), 'loaded': len(history), 'as_of': day,
            'retrieved_at': datetime.now(timezone.utc).isoformat()}
