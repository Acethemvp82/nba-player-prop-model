"""First-basket research rankings, explicitly separate from calibrated probabilities."""
from collections import Counter
from datetime import datetime, timezone
from live_sources import utc, reported_status

MARKETS = {'first_field_goal': 'First field goal (free throws excluded)',
           'first_points': 'First points (free throws included)'}
VERSION = 'first-basket-research-v1'


def build_board(games, history, roster, day, market='first_field_goal',
                injury_feed=None, confirmations=None, now=None, min_starts=5):
    if market not in MARKETS:
        raise ValueError('Unsupported first-basket market')
    now = now or datetime.now(timezone.utc)
    confirmations = confirmations or {}
    evidence = {}
    for row in history:
        if row.get('game_date', '') >= day or row.get('season_type') != 'regular':
            continue
        eid = row['event_id']
        if eid in evidence and evidence[eid] != row:
            raise ValueError('Conflicting historical event')
        evidence[eid] = row
    members = {(r['player_id'], r['team']): r for r in roster}
    board = []
    for game in games:
        eid = game.get('espnEventId')
        tip = utc(game.get('gameTimeUTC'))
        if not tip or tip <= now or game.get('espnCompleted') is True or not eid:
            continue
        sides = [game[s+'Team']['teamTricode'] for s in ('away', 'home')]
        for team, opponent in (sides, sides[::-1]):
            team_history = sorted((r for r in evidence.values() if team in r['teams'].values()),
                                  key=lambda r: (r['game_date'], r['event_id']), reverse=True)[:30]
            if not team_history:
                continue
            confirmation = confirmations.get(eid + ':' + team, {})
            checked = utc(confirmation.get('checked_at'))
            pids = confirmation.get('player_ids', [])
            confirmed = (checked is not None and 0 <= (now-checked).total_seconds() <= 3600
                         and checked < tip and bool(confirmation.get('source', '').strip())
                         and len(pids) == 5 and len(set(pids)) == 5
                         and all((p, team) in members for p in pids))
            # Old confirmations never supply today's candidate list.
            starters = pids if confirmed else team_history[0]['starters'][team]
            for pid in starters:
                member = members.get((pid, team))
                if not member:
                    continue
                starts = [r for r in team_history if pid in r['starters'][team]][:30]
                n = len(starts)
                if not n:
                    continue
                wins = sum(r[market] == pid for r in starts)
                shots = sum(r['team_first_shot'].get(team) == pid for r in starts)
                team_wins = sum(r['players'][r[market]]['team'] == team for r in team_history)
                tips = [r for r in team_history if r.get('tip_winner')]
                tip_wins = sum(r['tip_winner'] == team for r in tips)
                # Fixed, disclosed shrinkage reduces extreme tiny-sample rankings.
                basket_rate = (wins + .5) / (n + 5)
                shot_rate = (shots + 1) / (n + 5)
                team_rate = (team_wins + 2.5) / (len(team_history) + 5)
                score = round(100 * (.60*basket_rate + .25*shot_rate + .15*team_rate), 2) if n >= min_starts else None
                status = reported_status(injury_feed, member['player'], team, now) if injury_feed else 'Unknown — no current report'
                flags = []
                if status.casefold() in ('out', 'doubtful'):
                    continue
                if n < min_starts:
                    flags.append('Fewer than five historical starts')
                if not confirmed:
                    flags.append('Starting lineup unconfirmed')
                if (datetime.fromisoformat(day).date() - datetime.fromisoformat(team_history[0]['game_date']).date()).days > 7:
                    flags.append('Latest team lineup is older than seven days')
                if status not in ('Active', 'Available', 'Not listed — unconfirmed'):
                    flags.append('Availability needs review')
                season_counts = dict(Counter(r['season_year'] for r in starts))
                team_market = 'team_' + market
                allowed = [r for r in evidence.values() if opponent in r['teams'].values()]
                allowed_position = sum(r['players'][r[market]].get('position') == member.get('position')
                                       and r['players'][r[market]]['team'] != opponent for r in allowed)
                board.append({'event_id': eid, 'tipoff': game['gameTimeUTC'], 'slate_date': day,
                              'player_id': pid, 'player': member['player'], 'team': team,
                              'opponent': opponent, 'position': member.get('position', '?'),
                              'market': market, 'research_score': score, 'starts': n, 'first_baskets': wins,
                              'last10_first_baskets': sum(r[market] == pid for r in starts[:10]),
                              'last10_starts': len(starts[:10]), 'first_shots': shots,
                              'team_first_baskets': team_wins, 'team_games': len(team_history),
                              'tip_wins': tip_wins, 'tip_games': len(tips),
                              'team_openers': sum(r.get(team_market, {}).get(team) == pid for r in starts),
                              'opponent_allowed_position': allowed_position, 'opponent_games': len(allowed),
                              'status': status, 'starter_status': 'Confirmed by user' if confirmed else 'Projected from latest final',
                              'lineup_source': confirmation.get('source') if confirmed else None,
                              'lineup_checked_at': confirmation.get('checked_at') if confirmed else None,
                              'season_counts': season_counts, 'last_history_date': starts[0]['game_date'],
                              'readiness': 'Ready for price review' if not flags else 'Research only',
                              'flags': '; '.join(flags), 'model_version': VERSION})
    board.sort(key=lambda r: (r['research_score'] is None, -(r['research_score'] or 0), -r['starts'], r['player']))
    for i, row in enumerate(board, 1):
        row['rank'] = i if row['research_score'] is not None else None
    return board


def top_candidates(board, limit=3):
    """One candidate per game. Never force a full card from missing evidence."""
    picks, seen = [], set()
    for row in board:
        if row['research_score'] is not None and row['event_id'] not in seen:
            picks.append(row)
            seen.add(row['event_id'])
            if len(picks) == limit:
                break
    return picks
