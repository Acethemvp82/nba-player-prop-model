from datetime import datetime,timedelta,timezone
import pandas as pd
import pytest
from hammer_candidates import apply_hammers
from defensive_table import defensive_table_html

NOW=datetime(2026,10,30,12,tzinfo=timezone.utc)


def row():
    return {'Player':'Example Player','Team':'BOS','Opponent':'ATL','Pos':'PG','Group':'PG',
            'Line':15.5,'Line source':'FanDuel via PropFinder export','Line stat':'points',
            'Line captured ISO':NOW.isoformat(),'Projected starter':True,'Status':'Available',
            'PF L10 over':'7/10 (70%)','PF L5 over':'4/5 (80%)',
            'rank_Points':10,'teams_Points':30,'games_Points':5,'varies_Points':True}


def test_qualifying_marker_is_accessible_and_explains_specific_stat_and_line():
    result=apply_hammers(pd.DataFrame([row()]),'points','Current season',NOW)
    assert bool(result.iloc[0]['Hammer'])
    assert 'OVER 15.5 Points' in result.iloc[0]['Hammer reason']
    html=defensive_table_html(result)
    assert '🔨' in html and 'OVER research candidate' in html and 'rank 10/30' in html


@pytest.mark.parametrize('change',[
    {'Line':None},{'Line':float('nan')},{'Line source':'Unknown'}, {'Line stat':'rebounds'},
    {'Line captured ISO':(NOW-timedelta(minutes=91)).isoformat()},
    {'Line captured ISO':(NOW+timedelta(minutes=3)).isoformat()},
    {'Line captured ISO':'2026-10-30T12:00:00'},
    {'Projected starter':False},{'Status':'GTD'},{'Status':'Out'}, {'Status':'Questionable'},
    {'PF L10 over':'6/10 (60%)'},{'PF L10 over':'7/8 (88%)'},
    {'PF L5 over':'3/5 (60%)'},{'PF L5 over':'4/4 (100%)'},
    {'rank_Points':11},{'rank_Points':None},{'teams_Points':19},
    {'games_Points':4},{'varies_Points':False},
])
def test_missing_weak_or_stale_evidence_does_not_earn_marker(change):
    r={**row(),**change}
    result=apply_hammers(pd.DataFrame([r]),'points','Current season',NOW)
    assert not bool(result.iloc[0]['Hammer'])
    assert '🔨' not in defensive_table_html(result)


def test_selected_stat_and_current_season_are_required():
    frame=pd.DataFrame([row()])
    assert not apply_hammers(frame,'rebounds','Current season',NOW)['Hammer'].any()
    assert not apply_hammers(frame,'points','Previous season reference',NOW)['Hammer'].any()
