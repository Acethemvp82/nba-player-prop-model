"""Daily first-basket collection and paper tracking, shared by UI and scheduler."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from espn_schedule import espn_games_on
from first_basket_data import collect_history, fetch_summary, parse_opening
from first_basket_model import build_board, top_candidates, MARKETS
from first_basket_store import ROOT, read_json, write_json, capture, grade
from live_sources import fetch_injuries


def build_slate(day, per_team=20, root=ROOT):
    archive_path = root / 'history.json'
    archive = read_json(archive_path, [])
    games = espn_games_on(day)
    evidence = collect_history(day, games, existing=archive, per_team=per_team)
    merged = {r['event_id']: r for r in archive}
    merged.update({r['event_id']: r for r in evidence['games']})
    ledger_path = root / 'picks.json'
    ledger = read_json(ledger_path, []) + read_json(root / 'priced-picks.json', [])
    now = datetime.now(timezone.utc)
    # Results are resolved even when yesterday's teams are absent from today's slate.
    for eid in {r['event_id'] for r in ledger if r['slate_date'] < day} - merged.keys():
        try:
            merged[eid] = parse_opening(fetch_summary(eid), eid)
        except Exception as exc:
            evidence['failures'].append({'event_id': eid, 'stage': 'grading', 'error': str(exc)[:180]})
    write_json(archive_path, sorted(merged.values(), key=lambda r: (r['game_date'], r['event_id'])))
    try:
        injuries = fetch_injuries() if day == now.astimezone(ZoneInfo('America/New_York')).date().isoformat() else None
        # Tuple keys cannot be written to JSON. Store reports separately from the public slate.
        injury_error = None
    except ValueError as exc:
        injuries, injury_error = None, str(exc)
    report = {**evidence, 'slate': games, 'boards': {}, 'injury_error': injury_error,
              'built_at': now.isoformat(), 'history_window': per_team}
    for market in MARKETS:
        board = build_board(games, evidence['games'], evidence['roster'], day, market, injuries, now=now)
        report['boards'][market] = board
        capture(ledger_path, top_candidates(board), now=now)
    write_json(root / 'slates' / (day + '.json'), report)
    write_json(root / 'results.json', grade(read_json(ledger_path, []), list(merged.values())))
    return report
