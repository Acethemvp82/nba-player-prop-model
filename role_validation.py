"""Paired walk-forward diagnostics for a minutes-only candidate, never auto-tuning."""
from collections import defaultdict
from projection_core import clean_games, core_projections, valid_number
from historical_stats import _day


def evaluate_role_scenario(observations, as_of):
    """Compare the board with current-three median minutes on identical results.

    Production per minute stays fixed. Every input precedes the result date;
    candidates require three same-team current-season appearances. These are
    reconstructed forecasts, not independently frozen market observations.
    """
    grouped=defaultdict(list)
    for row in clean_games(observations,as_of):
        if row.get('season_type')=='regular' and type(row.get('season_year')) is int:
            grouped[_day(row['game_date'])].append(row)
    cutoff=_day(as_of)
    evaluation_year=cutoff.year+(cutoff.month>=7)
    training=[];details=[]
    for day in sorted(grouped):
        if day.year+(day.month>=7)!=evaluation_year:
            training.extend(grouped[day]);continue
        predictions={(p['player_id'],p['prop']):p for p in core_projections(training,day)}
        for actual_row in grouped[day]:
            for prop in ('points','rebounds','assists','threes'):
                forecast=predictions.get((str(actual_row['player_id']),prop))
                if not forecast or forecast['team']!=actual_row['team']: continue
                current_minutes=forecast['role_recent_minutes']
                actual=actual_row.get(prop)
                if (forecast['role_current_games']<3 or not valid_number(current_minutes)
                        or not valid_number(actual) or forecast['forecast_minutes']<=0): continue
                scenario=round(forecast['baseline']*min(48.,current_minutes)/forecast['forecast_minutes'],2)
                details.append({'game_date':day.isoformat(),'game_id':str(actual_row['game_id']),
                    'player_id':forecast['player_id'],'player':forecast['player'],'team':forecast['team'],
                    'prop':prop,'evidence':forecast['evidence'],'role_status':forecast['role_status'],
                    'last_training_date':max(forecast['last_game_date'],forecast.get('role_last_game_date') or forecast['last_game_date']),
                    'role_minutes':current_minutes,'model_minutes':forecast['forecast_minutes'],
                    'baseline':forecast['baseline'],'role_scenario':scenario,
                    'reference_last5':forecast['reference_last5'],'actual':actual,
                    'model_error':round(abs(forecast['baseline']-actual),3),
                    'scenario_error':round(abs(scenario-actual),3),
                    'reference_error':round(abs(forecast['reference_last5']-actual),3)})
        training.extend(grouped[day])
    cohorts=defaultdict(list)
    for r in details: cohorts[r['evidence'],r['role_status'],r['prop']].append(r)
    summary=[]
    for (evidence,role,prop),rows in sorted(cohorts.items()):
        mean=lambda field:round(sum(r[field] for r in rows)/len(rows),3)
        summary.append({'Evidence':evidence,'Role check':role,'Prop':prop,'Scored':len(rows),
            'Games':len({r['game_id'] for r in rows}),'Dates':len({r['game_date'] for r in rows}),
            'Players':len({r['player_id'] for r in rows}),'Model MAE':mean('model_error'),
            'Role scenario MAE':mean('scenario_error'),'Last-five MAE':mean('reference_error'),
            'Scenario minus model MAE':round(sum(r['scenario_error']-r['model_error'] for r in rows)/len(rows),3)})
    return {'summary':summary,'details':details}
