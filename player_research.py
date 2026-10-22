"""Player line research: observed results and explicit minutes scenarios."""
from math import isfinite
from historical_stats import _day, _valid_game_id
from prop_probability import american_odds_break_even

PROPS = ('points', 'rebounds', 'assists', 'threes')


def player_games(observations, player_id, prop, as_of, limit=10):
    cutoff = _day(as_of)
    if cutoff is None or prop not in PROPS or type(limit) is not int or limit < 1:
        raise ValueError('Invalid date, prop or sample limit')
    candidates = []
    for row in observations:
        if not isinstance(row, dict) or str(row.get('player_id')) != str(player_id):
            continue
        day = _day(row.get('game_date'))
        value, minutes = row.get(prop), row.get('minutes')
        if (row.get('is_final') is not True or day is None or day >= cutoff
                or not _valid_game_id(row.get('game_id'))
                or type(value) not in (int, float) or not isfinite(value) or value < 0
                or type(minutes) not in (int, float) or not isfinite(minutes) or minutes <= 0):
            continue
        candidates.append({'Date': day.isoformat(), 'Game ID': str(row['game_id']),
                           'Team': row.get('team'), 'Opponent': row.get('opponent'),
                           'Minutes': minutes, 'Result': value})
    seen, output = set(), []
    for row in sorted(candidates, key=lambda r: (r['Date'], r['Game ID']), reverse=True):
        if row['Game ID'] not in seen:
            seen.add(row['Game ID'])
            output.append(row)
    return output[:limit]


def compare_line(games, line, odds=None):
    if type(line) not in (int, float) or not isfinite(line) or line < 0:
        raise ValueError('Line must be a finite nonnegative number')
    over = sum(row['Result'] > line for row in games)
    push = sum(row['Result'] == line for row in games)
    under = len(games) - over - push
    return {'sample_games': len(games), 'over': over, 'under': under, 'push': push,
            'break_even': american_odds_break_even(odds)}


def minutes_scenario(baseline, recent_minutes, expected_minutes):
    values = (baseline, recent_minutes, expected_minutes)
    if (any(type(x) not in (int, float) or not isfinite(x) for x in values)
            or baseline < 0 or recent_minutes <= 0 or not 0 <= expected_minutes <= 48):
        raise ValueError('Invalid minutes scenario')
    return round(baseline * expected_minutes / recent_minutes, 2)
