"""Atomic history writes, pre-tip snapshots, and market-specific paper grading."""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from live_sources import utc
from prop_probability import american_odds_break_even
from first_basket_model import MARKETS

ROOT = Path(__file__).resolve().parent / 'data' / 'first-basket'


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    # Corrupt existing files must never silently reset the ledger.
    return json.loads(path.read_text())


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def capture(path, picks, now=None, quotes=None):
    """First save per game/market wins; later builds cannot rewrite the selection."""
    now = now or datetime.now(timezone.utc)
    quotes = quotes or {}
    saved = read_json(path, [])
    keys = {(r['slate_date'], r['event_id'], r['market']) for r in saved}
    added = 0
    for row in picks:
        key = (row['slate_date'], row['event_id'], row['market'])
        tip = utc(row.get('tipoff'))
        if key in keys or not tip or tip <= now or row['market'] not in MARKETS or row.get('research_score') is None:
            continue
        quote = quotes.get(row['player_id'] + ':' + row['event_id'], {})
        odds, book, quoted = quote.get('odds'), quote.get('book'), utc(quote.get('checked_at'))
        valid = (american_odds_break_even(odds) is not None and isinstance(book, str) and bool(book.strip())
                 and quoted is not None and 0 <= (now-quoted).total_seconds() <= 1800 and quoted < tip)
        saved.append({**row, 'captured_at': now.isoformat(), 'odds': odds if valid else None,
                      'book': book if valid else None, 'quote_checked_at': quote.get('checked_at') if valid else None,
                      'quote_source': 'Manual user entry' if valid else None,
                      'paper_only': True})
        keys.add(key)
        added += 1
    write_json(path, saved)
    return added


def grade(saved, history):
    finals = {r['event_id']: r for r in history}
    output = []
    for row in saved:
        final = finals.get(row['event_id'])
        result, profit = 'Pending', None
        tip, captured = utc(row.get('tipoff')), utc(row.get('captured_at'))
        if not tip or not captured or captured >= tip:
            result = 'Invalid capture'
        elif final:
            expected = {row['team'], row['opponent']}
            if (final.get('game_date') != row['slate_date'] or set(final['teams'].values()) != expected
                    or row['market'] not in MARKETS):
                result = 'Needs review'
            elif row['player_id'] not in final['starters'].get(row['team'], []):
                # Book rules differ; do not assume loss or void for a nonstarter.
                result = 'Nonstarter — check settlement'
            else:
                won = final[row['market']] == row['player_id']
                result = 'Won' if won else 'Lost'
                odds = row.get('odds')
                if american_odds_break_even(odds) is not None:
                    profit = (odds/100 if odds > 0 else 100/-odds) if won else -1.0
        output.append({**row, 'result': result, 'profit_units': profit})
    return output
