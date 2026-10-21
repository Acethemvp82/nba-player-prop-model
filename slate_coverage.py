"""Slate coverage and sparse-history previews from strictly pre-slate finals."""
from collections import defaultdict
from historical_stats import player_history_summaries

PROPS = ('points', 'rebounds', 'assists', 'threes')


def slate_coverage(observations, slate_date, opponents, forecasts):
    """Account for every slate team without treating historical players as active.

    Players with 1–4 appearances receive descriptive averages in a separate
    preview, never forecast rows. Coverage means historical sample coverage,
    not completeness of today's roster.
    """
    summaries = player_history_summaries(observations, as_of=slate_date)
    by_team = defaultdict(list)
    for row in summaries:
        if row['team'] in opponents:
            by_team[row['team']].append(row)
    by_forecast = defaultdict(list)
    for row in forecasts:
        if row.get('team') in opponents:
            by_forecast[row['team']].append(row)
    teams, previews = [], []
    for team, opponent in sorted(opponents.items()):
        history = by_team[team]
        available = by_forecast[team]
        teams.append({'Team': team, 'Opponent': opponent,
            'Players observed': len(history),
            'Players with baselines': len({str(r['player_id']) for r in available}),
            'Baseline rows': len(available),
            'Most appearances': max((r['games_played'] for r in history), default=0),
            'Coverage': ('Baselines available' if available else
                         'Fewer than 5 appearances' if history and all(r['games_played'] < 5 for r in history)
                         else 'Incomplete player stats' if history else 'No player history')})
        for row in history:
            if row['games_played'] >= 5:
                continue
            preview = {'Player': row['player'], 'Team': team, 'Opponent': opponent,
                'Appearances': row['games_played'], 'Last seen': row['last_game_date'],
                'Minutes avg': row['minutes_season_avg']}
            for prop in PROPS:
                preview[prop.title() + ' avg'] = row[prop + '_season_avg']
            previews.append(preview)
    return teams, sorted(previews, key=lambda r: (r['Team'], r['Player'] or ''))
