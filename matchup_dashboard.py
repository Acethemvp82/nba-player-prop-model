"""Focused NBA matchup board matching the user's reference screenshots."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from defensive_table import interactive_table_html
from matchup_csv import read_matchup_csv
from team_identity import SHORT_NAMES

BOARD_RELEASE='clean-matchup-v4'

ET=ZoneInfo('America/New_York')
ROOT=Path(__file__).resolve().parent
PROPS={'Points':'points','Rebounds':'rebounds','Assists':'assists','3PTM':'threes'}


def filter_board(frame, search='', defenses=None, positions=None):
    result=frame.copy()
    if search: result=result[result['Player'].str.contains(search,case=False,regex=False,na=False)]
    if defenses is not None: result=result[result['Opponent'].isin(defenses)]
    if positions is not None: result=result[result['Group'].isin(positions)]
    return result


def render_imported_board():
    reference=ROOT/'data'/'reference-matchups-2026-10-29.csv'
    with st.expander('CSV source',expanded=not reference.exists()):
        upload=st.file_uploader('Upload matchup export',type=['csv'],key='matchup_upload')
        st.caption('Imports the line, recent averages, positions and all six defensive values exactly as exported. An imported file is a snapshot and does not update itself.')
    if upload:
        content=upload.getvalue();source_name=upload.name
    elif reference.exists():
        content=reference.read_bytes();source_name=reference.name
    else:
        st.info('Upload your matchup CSV to build this board.');return
    try: frame,metadata=read_matchup_csv(content)
    except ValueError as exc: st.error(str(exc));return
    # The CSV does not carry offensive team IDs. Do not guess them from names.
    metadata={**metadata,'File':source_name,'Source':'Imported matchup CSV'}
    if not upload:
        metadata['Snapshot date']='2026-10-29'
        # These three pairings are visible in the user's accompanying screenshots.
        # Apply only to that bundled reference, never to arbitrary uploaded files.
        opponents={'ATL':'CLE','CLE':'ATL','MEM':'POR','POR':'MEM','NOP':'SAC','SAC':'NOP'}
        frame['Team']=frame['Opponent'].map(opponents)
    summary=' · '.join(f'{k}: {v}' for k,v in metadata.items() if k in ('Season','Window','Snapshot date'))
    st.caption(f'Imported snapshot · {len(frame)} players · {summary}')
    st.caption('Green averages exceed the exported line. Defensive ranks: green 1–10, amber 11–20, red 21–30. TEAM is the defense; POS is the matchup position. Player badges preserve the source position.')
    components.html(interactive_table_html(frame,metadata=metadata),height=1120,scrolling=False)


@st.cache_data(ttl=300,show_spinner=False)
def live_board(day,prop,defense_season):
    # Reuse the existing verified game collectors; avoid estimates in the display.
    from dashboard_v2 import schedule_for,history_for,injuries_for
    from slate_evidence import roster_observations
    from matchup_board import build_matchup_board
    from position_defense import positional_allowance
    from live_sources import reported_status
    from datetime import timezone
    games=schedule_for(day)
    if not games: return pd.DataFrame(),games,{'message':'No NBA games scheduled for this date.'}
    history=history_for(day,21,450,'regular-roster-v2')
    opponents={}
    for game in games:
        away=game.get('awayTeam',{}).get('teamTricode');home=game.get('homeTeam',{}).get('teamTricode')
        if away and home: opponents.update({away:home,home:away})
    all_observations=history.get('observations',[])
    observations=roster_observations(history)
    year=history.get('season_year')
    selected_year=year if defense_season=='Current season' else year-1 if year else None
    defensive=[r for r in all_observations if not selected_year or r.get('season_year')==selected_year]
    context=positional_allowance(defensive,day)
    rows=build_matchup_board(observations,[],opponents,day,prop,context)
    if history.get('roster_checked'):
        members={(r['player_id'],r['team']) for r in history.get('roster',[])}
        rows=[r for r in rows if (r['player_id'],r['Team']) in members]
    now=datetime.now(timezone.utc)
    if day==datetime.now(ET).date().isoformat():
        try:
            feed=injuries_for()
            for row in rows: row['Status']=reported_status(feed,row['Player'],row['Team'],now)
        except Exception:
            pass
    for row in rows: row['Source']='Live NBA history · latest 15 team games'
    return pd.DataFrame(rows),games,{
        'failures':len(history.get('failures',[])),
        'loaded':history.get('games_loaded',0),
        'defense_season':selected_year,
        'positions':'G / F / C',
        'built_at':datetime.now(ET).strftime('%b %d, %I:%M %p ET'),
        'schedule':dict(st.session_state.get('nba_schedule_health',{})),
    }


def apply_provider_lines(frame,payloads,games,prop,now):
    from live_sources import select_quote_pair,quote_matches_game
    result=frame.copy();result['Line']=None
    for i,row in result.iterrows():
        matches=[g for g in games if {g.get(s,{}).get('teamTricode') for s in ('homeTeam','awayTeam')}=={row['Team'],row['Opponent']}]
        payload=payloads.get(tuple(sorted((row['Team'],row['Opponent']))))
        if not payload or len(matches)!=1 or not quote_matches_game(payload,matches[0]): continue
        pair=select_quote_pair(payload,row['Player'],prop,now)
        if pair: result.at[i,'Line']=pair['line']
    return result


def render_live_board():
    from dashboard_v2 import odds_key,schedule_for,history_for,final_for,injuries_for
    from live_sources import fetch_event_odds
    from datetime import timezone
    cols=st.columns([1.1,1.1,1.4,.65])
    day=cols[0].date_input('Slate date',datetime.now(ET).date(),key='clean_day').isoformat()
    label=cols[1].selectbox('Player prop',list(PROPS),key='clean_prop')
    season=cols[2].selectbox('Defensive history',['Current season','Previous season reference'],key='clean_season')
    if cols[3].button('Refresh',use_container_width=True):
        live_board.clear();schedule_for.clear();history_for.clear();final_for.clear();injuries_for.clear()
        st.session_state.pop('clean_quotes',None)
    try:
        with st.spinner('Loading the slate and completed games…'):
            frame,games,health=live_board(day,PROPS[label],season)
    except Exception as exc:
        st.error('Live NBA data could not load: '+str(exc))
        st.info('The imported CSV board remains available from the source selector above.');return
    with st.expander('Games and tipoffs'):
        from dashboard_v2 import tipoff_et
        for g in games:
            st.write(f"{g.get('awayTeam',{}).get('teamTricode','?')} @ {g.get('homeTeam',{}).get('teamTricode','?')} · {tipoff_et(g.get('gameTimeUTC'))} · {g.get('gameStatusText','Scheduled')}")
    if frame.empty:
        st.info(health.get('message') or 'No verified player history is available for this slate.');return
    if health.get('schedule') and not health['schedule'].get('fresh',True):
        st.warning(health['schedule'].get('message','Schedule is from a saved snapshot.'))
    st.caption(f"Live NBA history · updated {health.get('built_at','')} · {health.get('loaded',0)} completed games loaded. L10/L5 use the latest available regular-season appearances and may span seasons.")
    st.caption(f"Defensive groups: G / F / C from the source · latest 15 loaded games per slate team · {season.lower()}. Ranks compare qualified teams in this sample, not all 30 teams. Hover a rank for its comparison count. Use an imported export for the exact PG/SG/SF/PF/C matchups shown in your reference.")
    if health.get('failures'): st.warning('Some history could not load; missing defensive values stay blank.')
    hide=st.checkbox('Hide reported Out / Doubtful',value=True,key='clean_hide')
    if hide: frame=frame[~frame['Status'].str.casefold().isin(['out','doubtful'])]
    key=odds_key();identity=(day,PROPS[label])
    if key:
        if st.button('Load FanDuel lines',key='clean_load_lines'):
            payloads={};failures=0
            with st.spinner('Loading FanDuel lines…'):
                for g in games:
                    away=g['awayTeam']['teamTricode'];home=g['homeTeam']['teamTricode']
                    try: payloads[tuple(sorted((away,home)))]=fetch_event_odds(key,away,home,day,datetime.now(timezone.utc))
                    except ValueError: failures+=1
            st.session_state['clean_quotes']=(identity,payloads)
            if failures: st.caption(f'{failures} games have no usable upcoming FanDuel feed.')
        cached=st.session_state.get('clean_quotes')
        if cached and cached[0]==identity:
            frame=apply_provider_lines(frame,cached[1],games,PROPS[label],datetime.now(timezone.utc))
        st.caption(f"FanDuel lines: {int(frame['Line'].notna().sum())} of {len(frame)} players. Only fresh, two-sided pregame lines are shown.")
    else:
        st.caption('Live sportsbook lines are not connected. Lines stay N/A. Your imported CSV includes its exported lines.')
    meta={'Source':'Live NBA history','Slate date':day,'Player prop':label,'Window':'Latest 15 team games','Defensive history':season,'Position groups':'G/F/C'}
    components.html(interactive_table_html(frame,metadata=meta),height=1120,scrolling=False)


def render_dashboard():
    st.set_page_config(page_title='NBA Defensive Matchups',page_icon='🏀',layout='wide',initial_sidebar_state='collapsed')
    st.markdown('''<style>
    .stApp{background:#101010;color:#eee}.block-container{max-width:1700px;padding-top:2rem;padding-bottom:1rem}h1{font-size:1.45rem!important;letter-spacing:.03em;margin-bottom:.25rem!important}div[data-testid="stVerticalBlock"]{gap:.5rem}div[data-testid="stCaptionContainer"]{font-size:.75rem;color:#aaa}div[data-testid="stExpander"]{border-color:#333}iframe{border:0}section[data-testid="stSidebar"]{background:#151515}
    </style>''',unsafe_allow_html=True)
    st.title('NBA DEFENSIVE MATCHUPS')
    source=st.radio('Board source',['Live NBA','Imported matchup CSV'],horizontal=True,key='clean_source')
    if source=='Imported matchup CSV': render_imported_board()
    else: render_live_board()
    with st.sidebar:
        st.header('Board settings')
        st.caption('Live NBA uses verified completed games. Imported matchup CSV preserves your exported values and exact positions.')
        st.caption('Optional FanDuel feed: add ODDS_API_KEY in Streamlit Secrets. Never paste API keys into chat or GitHub.')
        if st.button('Open advanced research',key='open_advanced'): st.session_state['clean_advanced']=True
    if st.session_state.get('clean_advanced'):
        with st.expander('Advanced research',expanded=True):
            from dashboard_v2 import render_saved_results
            render_saved_results()
