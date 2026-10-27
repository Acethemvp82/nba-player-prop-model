from datetime import datetime, timezone
import pytest
from forecast_tracking import score_forecasts, refresh_forecast_results
from residual_calibration import walk_forward_residuals
from projection_core import core_projections


F = dict(event_id='123', player_id='espn:1', team='NYK', prop='points',
         baseline=15., reference_last5=14., model_version='regular-roster-v2',
         captured_at='2026-10-22T18:00:00Z', tipoff='2026-10-22T23:00:00Z')
R = dict(player_id='espn:1', team='NYK', points=0, rebounds=2, assists=1,
         threes=0, minutes=30, is_final=True)


@pytest.mark.parametrize('changes', [
    {'is_final': False}, {'is_final': None}, {'minutes': 0}, {'minutes': None},
    {'minutes': True}, {'minutes': 61}, {'points': True}, {'points': -1},
    {'points': float('nan')}, {'points': float('inf')}, {'game_id': 'espn:999'},
])
def test_invalid_final_or_dnp_does_not_score(changes):
    assert score_forecasts([F], lambda _: [R | changes]) == []


def test_zero_in_played_final_is_valid_and_duplicate_is_not_double_counted():
    scored=score_forecasts([F, F], lambda _: [R])
    assert len(scored)==1
    assert scored[0]['actual']==0 and scored[0]['actual_minutes']==30
    assert scored[0]['result_status']=='verified_final'
    assert score_forecasts([F], lambda _: [R,R])==[]


@pytest.mark.parametrize('changes', [
    {'captured_at': 'bad'}, {'captured_at': '2026-10-22T18:00:00'},
    {'captured_at': '2026-10-22T23:00:00Z'}, {'tipoff': None},
    {'baseline': float('nan')}, {'reference_last5': True}, {'event_id': 'bad'},
])
def test_bad_frozen_forecast_is_skipped_without_request(changes):
    def fail(_): raise AssertionError('Invalid records must not fetch finals')
    assert score_forecasts([F | changes], fail)==[]


def test_rebuild_reuses_verified_finals_and_retries_missing_events():
    calls=[]
    def load(eid): calls.append(eid); return [R] if eid=='123' else []
    pending=F | {'event_id':'456'}
    grades, cache=refresh_forecast_results([F,pending],load)
    assert len(grades)==1 and list(cache)==['123']
    calls.clear()
    again,cache=refresh_forecast_results([F,pending],load,cache)
    assert again==grades and calls==['456']
    # A malformed cache cannot bypass validation or suppress a retry.
    calls.clear()
    refresh_forecast_results([F],load,{'123':[R | {'minutes':0}]})
    assert calls==['123']


def history():
    return [dict(player_id='espn:1',team='NYK',player='Example',
        game_id=f'espn:{i}',game_date=f'2026-10-{i:02}',is_final=True,
        season_type='regular',season_year=2027,minutes=30,
        points=10+i,rebounds=4,assists=2,threes=1) for i in range(1,8)]


def test_residuals_match_active_model_and_support_espn_event_ids():
    rows=history()
    result=walk_forward_residuals(rows,'2026-10-08')['points']
    assert len(result)==2
    for r in result:
        forecast=next(p for p in core_projections(rows,r['date']) if p['prop']=='points')
        actual=next(o for o in rows if o['game_date']==r['date'])['points']
        assert r['error']==actual-forecast['baseline']
        assert r['last_training_date']<r['date']
        assert r['model_version']=='regular-roster-v2'
        assert r['evidence']=='Current season'
    # Future data and duplicate input must not change earlier diagnostics.
    assert walk_forward_residuals(rows+rows+[rows[-1] | {'game_date':'2026-10-08','game_id':'espn:99','points':999}], '2026-10-08')['points']==result


def test_residuals_exclude_preseason_conflicts_and_first_game_after_trade():
    rows=history()
    changed=rows[:5]+[rows[5] | {'team':'BOS'}]
    assert walk_forward_residuals(changed,'2026-10-08')['points']==[]
    assert walk_forward_residuals([r | {'season_type':'preseason'} for r in rows],'2026-10-08')['points']==[]
    conflict=rows+[rows[0] | {'points':999}]
    assert len(walk_forward_residuals(conflict,'2026-10-08')['points'])==1


def test_saved_results_panel_reports_coverage_and_rejects_legacy(tmp_path, monkeypatch):
    import json
    import dashboard_v2 as dashboard
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(dashboard,'__file__',str(tmp_path/'dashboard_v2.py'))
    data=tmp_path/'data'; data.mkdir()
    row=score_forecasts([F], lambda _:[R])[0] | {
        'slate_date':'2026-10-22','evidence':'Current season','player':'Example'}
    path=data/'forecast-results.json'
    path.write_text(json.dumps({'grading_version':2,'results':[row]}))
    at=AppTest.from_string('from dashboard_v2 import render_saved_results\nrender_saved_results()').run()
    assert not at.exception
    summary=at.dataframe[0].value
    assert summary.iloc[0]['Games']==summary.iloc[0]['Dates']==summary.iloc[0]['Players']==1
    assert summary.iloc[0]['MAE_difference']==1
    path.write_text(json.dumps({'results':[row]}))
    at.run()
    assert not at.exception and not at.dataframe
    assert any('await revalidation' in info.value for info in at.info)
