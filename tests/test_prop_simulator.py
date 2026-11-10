from copy import deepcopy
import pytest
from prop_simulator import simulation_games, simulate_prop, PROPS


def observations(n=15):
    return [{'player_id':'espn:1','game_id':f'espn:{i+1}', 'team':'BOS','opponent':'NYK',
             'is_final':True,'season_type':'regular','source':'ESPN verified final boxscore',
             'game_date':f'2026-10-{i+1:02d}','minutes':30,
             'points':i,'rebounds':i,'assists':i,'threes':i} for i in range(n)]


@pytest.mark.parametrize('stat', PROPS.values())
@pytest.mark.parametrize('window', [5,10,15])
def test_windows_and_supported_stats(stat,window):
    rows=observations();before=deepcopy(rows)
    games=simulation_games(rows,'espn:1','BOS',stat,'2026-11-01',window)
    assert len(games)==window and games[0]['Result']==14
    assert rows==before
    r=simulate_prop(games,10.5)
    assert r['runs']==10000 and sum(r['counts'].values())==10000
    assert r['counts']['Push']==0
    assert abs(r['percent']['Over']-100*sum(g['Result']>10.5 for g in games)/window)<2
    assert r==simulate_prop(games,10.5)


def test_future_nonfinal_dnp_wrong_identity_and_conflicts_excluded():
    rows=observations(10)
    rows += [dict(rows[0],points=99)]  # conflicting game is excluded completely
    rows += [dict(rows[1],game_id='espn:100',game_date='2026-11-01'),
             dict(rows[1],game_id='espn:101',is_final=False),
             dict(rows[1],game_id='espn:102',minutes=0),
             dict(rows[1],game_id='espn:103',team='LAL'),
             dict(rows[1],game_id='espn:104',player_id='espn:2'),
             dict(rows[1],game_id='espn:105',source='unverified'),
             dict(rows[1],game_id='espn:106',points=1.5),
             dict(rows[1],game_id='espn:107',season_type='preseason')]
    games=simulation_games(rows,'espn:1','BOS','points','2026-11-01',15)
    assert len(games)==9 and {g['Game ID'] for g in games}=={f'espn:{i}' for i in range(2,11)}


def test_integer_lines_keep_pushes_and_no_fake_variation():
    games=[{'Result':3}]*5
    r=simulate_prop(games,3)
    assert r['counts']=={'Over':0,'Under':0,'Push':10000}
    assert r['mean']==r['p10']==r['p90']==3
    assert simulate_prop(games,2.5)['percent']['Over']==100
    assert simulate_prop(games,3.5)['percent']['Under']==100


@pytest.mark.parametrize('line', [None,True,-.5,float('nan'),float('inf'),1.2])
def test_invalid_line_refused(line):
    with pytest.raises(ValueError): simulate_prop([{'Result':3}]*5,line)


def test_insufficient_sample_and_bad_inputs_refused():
    with pytest.raises(ValueError):simulate_prop([{'Result':3}]*4,3.5)
    with pytest.raises(ValueError):simulate_prop([{'Result':True}]*5,3.5)
    with pytest.raises(ValueError):simulation_games([], 'espn:1','BOS','steals','2026-11-01')
    with pytest.raises(ValueError):simulation_games([], 'espn:1','BOS','points','2026-11-01',30)


def test_ui_requires_line_runs_and_clears_stale_results():
    from streamlit.testing.v1 import AppTest
    code='''
import pandas as pd
from prop_simulator_ui import render_prop_simulator
from tests.test_prop_simulator import observations
frame=pd.DataFrame([{'player_id':'espn:1','Player':'Test Player','Team':'BOS','Opponent':'NYK','Line':99.5}])
render_prop_simulator(frame,{'observations':observations()},'2026-11-01')
'''
    # Import fixtures through a real test module file, independent of namespace packages.
    code=code.replace('from tests.test_prop_simulator import observations',
                      'def observations(): return '+repr(observations()))
    at=AppTest.from_string(code).run()
    assert not at.exception and at.button[0].disabled
    assert at.radio[0].options==['Enter current line']  # no stale/unverified prefill
    at.number_input[0].set_value(10.5).run()
    at.button[0].click().run()
    assert not at.exception and len(at.metric)==3
    assert any('Actual sample:' in c.value for c in at.caption)
    at.number_input[0].set_value(3.5).run()
    assert not at.exception and not at.metric
    at.selectbox(key='prop_sim_stat').set_value('Threes').run()
    assert at.number_input[0].value is None and at.button[0].disabled


def test_simulator_opens_from_board_without_changing_rankings(monkeypatch):
    from pathlib import Path
    import pandas as pd
    from streamlit.testing.v1 import AppTest
    import matchup_dashboard as dashboard
    frame=pd.DataFrame([{'player_id':'espn:1','Player':'Example','Team':'BOS','Opponent':'NYK',
                         'Status':'Unknown','Pos':'PG','Group':'PG','L10':10.,'L5':10.}])
    before=frame.copy(deep=True)
    monkeypatch.setattr(dashboard,'live_board',lambda *a:(frame,[],{'built_at':'test'}))
    monkeypatch.setattr(dashboard,'league_feed_for',lambda *a:({'observations':observations()},[]))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    at.checkbox(key='open_prop_simulator').set_value(True).run()
    assert not at.exception
    assert at.selectbox(key='prop_sim_stat').options==list(PROPS)
    at.number_input[0].set_value(10.5).run()
    at.button(key='prop_sim_run').click().run()
    assert not at.exception and len(at.metric)==3
    pd.testing.assert_frame_equal(frame,before)
