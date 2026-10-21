"""As-of descriptive matchup context; scores are not betting probabilities."""
from opponent_stats import PROPS, opponent_game_totals, opponent_sample_summary


def matchup_context(observations, as_of, min_games=5):
    """Compare screened opponent allowance with the game-weighted loaded sample.

    Shrink deviations toward neutral with five prior games. A score of 50 is
    neutral; each allowance percentage point moves the score by two, bounded
    to 0–100. Missing/small samples remain unknown, never neutral by default.
    This does not adjust player forecasts: pace, position and schedule strength
    have not been controlled. The reference is the loaded sample, not the league.
    """
    if type(min_games) is not int or min_games < 1:
        raise ValueError("min_games must be a positive integer")
    summaries = opponent_sample_summary(opponent_game_totals(observations, as_of))
    output = {}
    for prop in PROPS:
        eligible = [s for s in summaries if s[prop + '_valid_games'] >= min_games
                    and s[prop + '_observed_avg'] is not None]
        total_games = sum(s[prop + '_valid_games'] for s in eligible)
        reference = (sum(s[prop + '_observed_avg'] * s[prop + '_valid_games']
                         for s in eligible) / total_games if total_games else None)
        for summary in summaries:
            games = summary[prop + '_valid_games']
            avg = summary[prop + '_observed_avg']
            known = len(eligible) >= 2 and games >= min_games and reference is not None and reference > 0
            deviation = ((avg / reference - 1) * games / (games + 5)) if known else None
            output[(summary['opponent'], prop)] = {
                'matchup_score': round(max(0, min(100, 50 + 200 * deviation)), 1) if known else None,
                'opponent_games': games, 'opponent_allowed': avg,
                'sample_reference': round(reference, 2) if reference is not None else None,
                'matchup_status': 'Available' if known else 'Insufficient sample',
            }
    return output


def attach_matchups(forecasts, opponents, context):
    """Only retain slate teams, preserving unknown matchups and baseline values."""
    return [{**row, 'opponent': opponents[row['team']],
             **context.get((opponents[row['team']], row['prop']), {
                 'matchup_score': None, 'opponent_games': 0,
                 'opponent_allowed': None, 'sample_reference': None,
                 'matchup_status': 'Insufficient sample'})}
            for row in forecasts if row.get('team') in opponents]
