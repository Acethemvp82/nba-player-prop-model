from datetime import datetime,timezone,timedelta
from copy import deepcopy
import pytest
from market_validation import make_market_record,grade_records,summarize,validate_record,record_id,deduplicate
from market_capture import append_market_records

NOW=datetime(2026,10,22,18,tzinfo=timezone.utc)
GAME={'espnEventId':'123','gameTimeUTC':'2026-10-22T23:00Z','gameStatusText':'Scheduled','espnCompleted':False,
      'homeTeam':{'teamTricode':'NYK'},'awayTeam':{'teamTricode':'BOS'}}
F={'player_id':'espn:1','player':'Example','team':'NYK','prop':'points','baseline':20.,'reference_last5':18.,
   'evidence':'Current season','slate_date':'2026-10-22','sample_games':10,'forecast_minutes':30.,
   'minutes_low':28.,'minutes_high':34.,'availability':'Not listed — unconfirmed','role_status':'stable'}


def record(**changes):
    return make_market_record(F|changes,GAME,18.5,-110,125,'manual_unverified',NOW)


def final(points,minutes=30):
    return {'123':[{'player_id':'espn:1','team':'NYK','points':points,'minutes':minutes,'is_final':True}]}


def test_capture_grading_prices_and_frozen_benchmark():
    r=record();assert validate_record(r)
    assert r['model_side']=='over' and r['reference_side']=='under'
    graded,bad=grade_records([r],final(21));g=graded[0]
    assert not bad and g['model_outcome']=='win' and g['model_units']==pytest.approx(100/110,abs=1e-6)
    assert g['reference_outcome']=='loss' and g['reference_units']==-1
    s=summarize(graded)[0];assert s['Games']==1 and s['Dates']==1 and s['model ROI %']==90.91
    assert s['reference ROI %']==-100
    under=record(baseline=17.,reference_last5=22.)
    g=grade_records([under],final(18))[0][0]
    assert g['model_side']=='under' and g['model_units']==1.25
    assert g['reference_units']==-1


def test_push_pass_and_missing_are_not_losses_or_zeros():
    r=make_market_record(F,GAME,20,-110,125,'manual_unverified',NOW)
    assert r['model_side']=='pass'
    g=grade_records([r],final(20))[0][0]
    assert g['model_outcome']=='pass' and g['reference_outcome']=='push'
    assert summarize([g])[0]['model ROI %'] is None
    r=record()
    assert grade_records([r],{})[0][0]['model_outcome']=='unresolved'
    assert grade_records([r],final(0,minutes=0))[0][0]['actual'] is None
    assert grade_records([r],final(0))[0][0]['model_outcome']=='loss'
    old=record(evidence='Prior-season reference')
    assert not old['eligible'] and old['model_side']=='pass'
    assert summarize(grade_records([old],final(100))[0])[0]['model bets']==0


def test_started_ambiguous_inconsistent_and_stale_quotes_rejected():
    with pytest.raises(ValueError):make_market_record(F,GAME,18.5,-110,125,'manual_unverified',NOW+timedelta(hours=5))
    with pytest.raises(ValueError):make_market_record(F,GAME|{'espnCompleted':True},18.5,-110,125,'manual_unverified',NOW)
    with pytest.raises(ValueError):make_market_record(F|{'team':'PHI'},GAME,18.5,-110,125,'manual_unverified',NOW)
    with pytest.raises(ValueError):make_market_record(F,GAME,18.25,-110,125,'manual_unverified',NOW)
    with pytest.raises(ValueError):make_market_record(F,GAME,18.5,-110,125,'provider_fanduel',NOW,(NOW-timedelta(minutes=31)).isoformat())
    for odds in (None,True,-99,float('nan'),float('inf')):
        with pytest.raises(ValueError):make_market_record(F,GAME,18.5,odds,125,'manual_unverified',NOW)


def test_first_record_duplicate_conflicts_and_tampering(tmp_path):
    r=record();changed=r|{'line':25}
    assert not validate_record(changed)
    changed=r|{'model_side':'under'};changed['record_id']=record_id(changed)
    assert not validate_record(changed)
    newer=make_market_record(F,GAME,19.5,-110,125,'manual_unverified',NOW+timedelta(minutes=1))
    assert deduplicate([newer,r,r])[0]==[r]
    conflict=make_market_record(F,GAME,19.5,-110,125,'manual_unverified',NOW)
    assert deduplicate([r,conflict])[0]==[]
    path=tmp_path/'ledger.json';append_market_records([r],path)
    assert append_market_records([newer],path)==[r]


def test_sources_props_and_rules_are_separate_cohorts():
    r=record();provider=make_market_record(F,GAME,18.5,-110,125,'provider_fanduel',NOW,NOW.isoformat())
    grades=grade_records([r,provider],final(21))[0]
    assert len(summarize(grades))==2
    unverified=deepcopy(final(21));unverified['123'][0]['is_final']=False
    assert grade_records([r],unverified)[0][0]['actual'] is None


def test_under_quote_uses_its_own_price():
    from live_sources import select_quote
    payload={'commence_time':'2026-10-22T23:00Z','bookmakers':[{'key':'fanduel','markets':[
        {'key':'player_points','last_update':NOW.isoformat(),'outcomes':[
            {'name':'Over','description':'Example','point':18.5,'price':-110},
            {'name':'Under','description':'Example','point':18.5,'price':125}]}]}]}
    assert select_quote(payload,'Example','points',NOW,'Under')['odds']==125
    assert select_quote(payload,'Example','points',NOW)['odds']==-110
    assert select_quote(payload,'Example','points',NOW,'Sideways') is None
