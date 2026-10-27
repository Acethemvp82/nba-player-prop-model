from streamlit.testing.v1 import AppTest


def test_manual_freeze_and_prospective_grading_flow():
    code='''
import streamlit as st
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from validation_panel import render_paper_capture,render_market_validation
now=datetime.now(timezone.utc)
tip=now+timedelta(hours=2)
f={'player_id':'espn:1','player':'Example','team':'NYK','prop':'points','baseline':20.,'reference_last5':18.,
'evidence':'Current season','slate_date':tip.astimezone(ZoneInfo('America/New_York')).date().isoformat(),
'sample_games':10,'forecast_minutes':30.,'minutes_low':28.,'minutes_high':34.,'availability':'Not listed — unconfirmed','role_status':'stable'}
g={'espnEventId':'123','gameTimeUTC':tip.isoformat(),'gameStatusText':'Scheduled','espnCompleted':False,
'homeTeam':{'teamTricode':'NYK'},'awayTeam':{'teamTricode':'BOS'}}
render_paper_capture(f,18.5,-110,[g])
render_market_validation(lambda eid:[{'player_id':'espn:1','team':'NYK','points':21,'minutes':30,'is_final':True}])
'''
    at=AppTest.from_string(code).run();assert not at.exception
    assert next(b for b in at.button if b.label=='Freeze this line and forecast').disabled
    at.number_input[0].set_value(125).run()
    next(b for b in at.button if b.label=='Freeze this line and forecast').click().run()
    assert not at.exception and len(at.session_state['nba_paper_records'])==1
    next(b for b in at.button if b.label=='Grade saved entries against verified finals').click().run()
    assert not at.exception
    summary=next(d.value for d in at.dataframe if 'model ROI %' in d.value.columns)
    manual=summary[summary['Source']=='manual_unverified'].iloc[0]
    assert manual['model wins']==1 and manual['model ROI %']==90.91
    assert manual['reference losses']==1
