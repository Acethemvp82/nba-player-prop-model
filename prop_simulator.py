"""Empirical single-player Monte Carlo research, separate from board scoring."""
from datetime import date
from math import isfinite
import numpy as np
from league_feed import clean_observations

PROPS = {'Points': 'points', 'Rebounds': 'rebounds', 'Assists': 'assists', 'Threes': 'threes'}
RUNS = 10_000


def simulation_games(observations, player_id, team, stat, as_of, window=10):
    """Verified regular-season appearances before the slate, current team only."""
    date.fromisoformat(as_of)
    if stat not in PROPS.values() or type(window) is not int or window not in (5, 10, 15):
        raise ValueError('Choose points, rebounds, assists or threes and 5, 10 or 15 games')
    rows = clean_observations(observations, as_of)
    games = []
    for row in rows:
        value = row.get(stat)
        if (row.get('player_id') != player_id or row.get('team') != team
                or row.get('source') != 'ESPN verified final boxscore'
                or type(value) not in (int, float) or not isfinite(value)
                or value < 0 or value != int(value)):
            continue
        games.append({'Date': row['game_date'], 'Game ID': row['game_id'],
                      'Opponent': row['opponent'], 'Minutes': row['minutes'], 'Result': int(value)})
    return sorted(games, key=lambda r: (r['Date'], r['Game ID']), reverse=True)[:window]


def simulate_prop(games, line, seed=2026):
    """Draw 10,000 whole observed game totals with equal replacement weights.

    Resampling approximates the empirical distribution, not a calibrated future
    hit probability. No opponent, minutes or injury adjustment is inferred.
    """
    if type(line) not in (int, float) or not isfinite(line) or line < 0 or line * 2 != int(line * 2):
        raise ValueError('Enter a nonnegative whole or half-point line')
    if not 5 <= len(games) <= 15:
        raise ValueError('At least five verified appearances are required (maximum 15)')
    values = [g.get('Result') for g in games]
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError('Game results must be nonnegative integers')
    draws = np.random.default_rng(seed).choice(values, size=RUNS, replace=True)
    outcomes = {name: int(np.count_nonzero(test)) for name, test in
                [('Over', draws > line), ('Under', draws < line), ('Push', draws == line)]}
    totals, counts = np.unique(draws, return_counts=True)
    return {'runs': RUNS, 'sample': len(values), 'line': line,
            'counts': outcomes, 'percent': {k: 100 * v / RUNS for k, v in outcomes.items()},
            'mean': float(np.mean(draws)), 'p10': float(np.quantile(draws, .1)),
            'p90': float(np.quantile(draws, .9)),
            'historical': {'Over': sum(v > line for v in values),
                           'Under': sum(v < line for v in values),
                           'Push': sum(v == line for v in values)},
            'distribution': [{'Total': int(v), 'Draws': int(n)} for v, n in zip(totals, counts)]}
