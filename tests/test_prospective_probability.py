from datetime import date,timedelta
from copy import deepcopy
import pytest
from prospective_probability import estimate_probability, valid_evidence, score_probability_records
from market_validation import make_market_record, grade_records


def archive():
    rows=[]
    for i in range(100):
        day=(date(2026,10,1)+timedelta(days=i//10)).isoformat()
        rows.append(dict(player_id=f'espn:{i%20}',event_id=str(100+i//5),prop='points',
            evidence='Current season',source_season=2027,model_version='regular-roster-v2',
            result_status='verified_final',role_status='stable',sample_games=10,
            minutes_low=28.,minutes_high=32.,actual_minutes=30.,slate_date=day,
            captured_at=day+'T18:00Z',tipoff=day+'T23:00Z',baseline=20.,actual=22 if i%2 else 18))
    return {'grading_version':2,'results':rows}


def target():
    return dict(evidence='Current season',slate_date='2026-10-22',baseline=20.,prop='points')


def test_abstains_for_prior_season_or_small_and_correlated_samples():
    assert estimate_probability(target()|{'evidence':'Prior-season reference'},18.5,archive())['status']=='current_season_required'
    a=archive();a['results']=a['results'][:99]
    assert 'over' not in estimate_probability(target(),18.5,a)
    a=archive()
    for r in a['results']:r['player_id']='espn:1'
    assert estimate_probability(target(),18.5,a)['status']=='insufficient_history'
    a=archive()
    for r in a['results']:r['role_status']='changed'
    assert estimate_probability(target(),18.5,a)['samples']==0


def test_empirical_probability_is_frozen_discrete_and_push_aware():
    evidence=estimate_probability(target(),20.5,archive())
    assert evidence['status']=='experimental' and evidence['samples']==100
    assert evidence['over']==evidence['under']==.5 and evidence['push']==0
    assert valid_evidence(evidence,'2026-10-22')
    whole=estimate_probability(target(),20,archive())
    assert whole['push']==pytest.approx(1/103) and sum(whole[k] for k in ('over','under','push'))==pytest.approx(1)
    assert not valid_evidence(evidence|{'last_training_date':'2026-10-22'},'2026-10-22')


def test_future_duplicate_conflicting_and_wrong_cohort_rows_do_not_leak():
    a=archive();baseline=estimate_probability(target(),20.5,a)
    extra=a['results'][0]|{'slate_date':'2026-10-22','tipoff':'2026-10-22T23:00Z','event_id':'999','actual':1000}
    changed=deepcopy(a);changed['results']+=a['results']+[extra]
    assert estimate_probability(target(),20.5,changed)==baseline
    a['results'].append(a['results'][0]|{'actual':999})
    assert estimate_probability(target(),20.5,a)['samples']==99
    a=archive()
    for r in a['results']:r['captured_at']=r['tipoff']
    assert estimate_probability(target(),20.5,a)['samples']==0


def test_probability_freeze_and_later_brier_score_use_captured_evidence():
    from tests.test_market_validation import F,GAME,NOW
    f=F|{'role_status':'stable'}
    record=make_market_record(f,GAME,20.5,-110,125,'manual_unverified',NOW,probability_archive=archive())
    evidence=record['probability_evidence']
    assert evidence['status']=='experimental' and evidence['over']==.5
    final={'123':[{'player_id':'espn:1','team':'NYK','points':23,'minutes':30,'is_final':True}]}
    graded=grade_records([record],final)[0]
    report=score_probability_records(graded+graded)
    assert len(report)==1 and report[0]['Scored']==1 and report[0]['Brier score']==.25
    assert score_probability_records(grade_records([record],{})[0])==[]
