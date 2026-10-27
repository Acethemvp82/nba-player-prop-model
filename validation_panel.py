"""Streamlit controls for explicit manual paper capture and prospective grading."""
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd
import streamlit as st
from market_validation import make_market_record,deduplicate,grade_records,summarize,validate_record,record_id

from prospective_probability import load_forecast_archive, score_probability_records

ROOT=Path(__file__).resolve().parent/'data'


def load_rows(path):
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,list) else []
    except (OSError,ValueError):return []


def render_paper_capture(selected,line,over_odds,games):
    with st.expander('Freeze a pregame paper record'):
        st.caption('One hypothetical unit per eligible signal. Enter BOTH prices from the same sportsbook and line. Manual quotes and timestamps are unverified; this does not place a bet.')
        under=st.number_input('Under American odds (for paper tracking)',value=None,step=1,key='paper_under_'+selected.get('slate_date','unknown')+'_'+str(selected['player_id'])+selected['prop'])
        if st.button('Freeze this line and forecast',disabled=line is None or over_odds is None or under is None):
            matches=[g for g in games if selected['team'] in [g.get(s,{}).get('teamTricode') for s in ('homeTeam','awayTeam')]]
            try:
                if len(matches)!=1:raise ValueError('No unique scheduled game for this player')
                record=make_market_record(selected,matches[0],line,over_odds,under,'manual_unverified',probability_archive=load_forecast_archive())
                saved,invalid=deduplicate(st.session_state.get('nba_paper_records',[])+[record])
                st.session_state['nba_paper_records']=saved
                st.success('Paper record frozen for this session. Download the JSON below to keep it across restarts.')
                if not record['eligible']: st.info(record['signal']+': saved as research only; no simulated bet is counted.')
            except ValueError as exc:st.error(str(exc))
        saved=st.session_state.get('nba_paper_records',[])
        if saved:
            st.download_button('Download frozen paper ledger JSON',json.dumps({'schema':'nba-paper-ledger-v1','records':saved},indent=2,allow_nan=False),
                file_name='nba-paper-ledger.json',mime='application/json')
        st.caption('First record per game/player/prop/rule/source is retained. A session is temporary: download your ledger, then import it in the report after the games.')


def render_market_validation(final_loader):
    with st.expander('Prospective paper results — lines, odds and returns'):
        st.caption('Fixed rule line-gap-role-v2: eligible current-season estimate above line → Over; below line → Under; equal → pass. Ten current-season appearances, a last-five minutes range of at most 12 and a stable observed role comparison are required. Changed or unknown roles stay research only. Legacy line-gap-v1 records retain their frozen rules. The recent-average benchmark uses the same eligibility gate and captured prices. No weights are tuned from this report.')
        canonical=load_rows(ROOT/'market-ledger.json')
        published=ROOT/'market-results.json'
        saved_results={}
        try:saved_results=json.loads(published.read_text())
        except (OSError,ValueError):pass
        st.caption(f'{len(canonical)} published provider records. Automatic quote capture requires an opt-in and a configured provider key; no missing prices are invented.')
        upload=st.file_uploader('Import a saved paper ledger JSON',type=['json'],key='nba_paper_upload')
        if upload is not None:
            try:
                if upload.size>2_000_000:raise ValueError('File exceeds 2 MB')
                payload=json.loads(upload.getvalue())
                if not isinstance(payload,dict) or payload.get('schema')!='nba-paper-ledger-v1':raise ValueError('Unknown ledger format')
                imported=payload.get('records')
                if not isinstance(imported,list) or len(imported)>5000:raise ValueError('Invalid record list')
                if any(not isinstance(r,dict) or not validate_record(r) for r in imported):raise ValueError('Invalid or modified ledger records')
                normalized=[]
                for row in imported:
                    r={**row,'source':'manual_unverified'};r['record_id']=record_id(r);normalized.append(r)
                st.session_state['nba_paper_records'],_=deduplicate(st.session_state.get('nba_paper_records',[])+normalized)
                st.caption('Imported records are treated as manual/unverified regardless of their original source label. Checksums detect changes, not authenticity.')
            except (ValueError,TypeError,UnicodeError) as exc:st.error('Import rejected: '+str(exc))
        records,invalid=deduplicate(canonical+st.session_state.get('nba_paper_records',[]))
        finals=dict(st.session_state.get('nba_paper_finals',{}))
        # Recover only previously verified actual values/minutes from the repository report.
        for row in saved_results.get('records',[]):
            if row.get('actual') is None or not row.get('actual_minutes',0)>0:continue
            eid=row['event_id'];rows=finals.setdefault(eid,[])
            match=next((r for r in rows if r['player_id']==row['player_id'] and r['team']==row['team']),None)
            if match is None:
                match={'player_id':row['player_id'],'team':row['team'],'minutes':row['actual_minutes'],'is_final':True};rows.append(match)
            match[row['prop']]=row['actual']
        if records and st.button('Grade saved entries against verified finals'):
            failures=0
            for eid in {r['event_id'] for r in records}:
                try:finals[eid]=final_loader(eid)
                except Exception:failures+=1
            st.session_state['nba_paper_finals']=finals
            if failures:st.caption(f'{failures} games lack verified finals; their entries stay unresolved.')
        graded,rejected=grade_records(records,finals)
        if invalid+rejected:st.warning(f'{invalid+rejected} invalid/conflicting records excluded.')
        if not graded:
            st.info('No frozen market records yet. Save both prices in Player details or import your ledger. Existing forecast-only records cannot establish betting returns.')
        else:
            st.dataframe(pd.DataFrame(summarize(graded)),hide_index=True,use_container_width=True)
            frame=pd.DataFrame(graded)
            st.dataframe(frame[['slate_date','player','prop','source','evidence','signal','line','over_odds','under_odds','model_side','actual','model_outcome','model_units','reference_side','reference_units']],hide_index=True,use_container_width=True)
            st.download_button('Download paper grading audit JSON',json.dumps({'records':graded,'summary':summarize(graded)},indent=2,allow_nan=False),file_name='nba-paper-results.json',mime='application/json')
        st.subheader('Prospective probability checks')
        probability_report=score_probability_records(graded)
        if probability_report:
            st.dataframe(pd.DataFrame(probability_report),hide_index=True,use_container_width=True)
        else:
            st.info('No resolved, pre-tip experimental probabilities to score yet. Estimation requires 100 current-season frozen residuals covering 20 games, 10 dates and 20 players for the selected prop. Prior-season references do not qualify.')
        st.caption('Brier scores compare frozen conditional Over estimates with later non-push results. Experimental estimates are never automatically labeled proven. Pushes and unresolved results are excluded from this probability diagnostic.')
        st.caption('Paper grading: one unit risked; win profit = price payout, loss = −1, push = 0. Win percentage excludes pushes; ROI is net units / units risked including pushes. Missing/DNP stays unresolved; research-only signals are passes. No actual wagers or sportsbook-specific settlement adjustments are assumed. Multiple props from one game are correlated; inspect Games and Dates, not just entry count. A positive sample ROI does not establish an edge.')
