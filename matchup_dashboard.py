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

BOARD_RELEASE='fanduel-snapshots-v6'

ET=ZoneInfo('America/New_York')
ROOT=Path(__file__).resolve().parent
PROPS={'Points':'points','Rebounds':'rebounds','Assists':'assists','3PTM':'threes','Steals':'steals','Blocks':'blocks'}


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


@st.cache_data(ttl=900,show_spinner=False)
def league_feed_for(day):
    from dashboard_v2 import schedule_for
    from league_feed import load_saved_feed,collect_league_feed
    games=schedule_for(day)
    if not games: return None,games
    saved=load_saved_feed(ROOT/'data'/'league-feed.json.gz',day)
    if saved is not None: return saved,games
    try:
        import gzip
        cache=json.loads(gzip.decompress((ROOT/'data'/'league-boxscores.json.gz').read_bytes()).decode())
    except (OSError,ValueError): cache={}
    feed,_=collect_league_feed(day,games,cache=cache)
    return feed,games


@st.cache_data(ttl=900,show_spinner=False)
def live_board(day,prop,defense_season):
    from league_feed import build_data_board
    from dashboard_v2 import injuries_for
    from live_sources import reported_status
    from datetime import timezone
    feed,games=league_feed_for(day)
    if feed is None: return pd.DataFrame(),games,{'message':'No NBA games scheduled for this date.'}
    rows=build_data_board(feed,games,prop,defense_season)
    now=datetime.now(timezone.utc)
    if day==datetime.now(ET).date().isoformat():
        try:
            injuries=injuries_for()
            for row in rows: row['Status']=reported_status(injuries,row['Player'],row['Team'],now)
        except Exception: pass
    return pd.DataFrame(rows),games,{
        'failures':len(feed.get('failures',[])),'loaded':feed.get('games_loaded',0),
        'current_games':feed.get('current_games',0),
        'defense_season':feed['season_year'] if defense_season=='Current season' else feed['season_year']-1,
        'positions':'PG / SG / SF / PF / C',
        'built_at':datetime.fromisoformat(feed['updated_at']).astimezone(ET).strftime('%b %d, %I:%M %p ET'),
        'schedule':dict(st.session_state.get('nba_schedule_health',{})),
        'teams':len(feed.get('teams',{})),
        'catalog_players':len(feed.get('positions',{}).get(str(feed['season_year']),{})),
    }



@st.fragment(run_every="15m")
def render_live_board():
    from dashboard_v2 import schedule_for,history_for,final_for,injuries_for
    cols=st.columns([1.1,1.1,1.4,.65])
    day=cols[0].date_input('Slate date',datetime.now(ET).date(),key='clean_day').isoformat()
    label=cols[1].selectbox('Player stat',list(PROPS),key='clean_prop')
    season=cols[2].selectbox('Defensive history',['Current season','Previous season reference'],key='clean_season')
    if cols[3].button('Refresh',use_container_width=True):
        live_board.clear();league_feed_for.clear();schedule_for.clear();history_for.clear();final_for.clear();injuries_for.clear()
    try:
        with st.spinner('Loading league-wide stats and projected positions…'):
            frame,games,health=live_board(day,PROPS[label],season)
    except Exception as exc:
        st.error('Live NBA data could not load: '+str(exc))
        st.info('The imported CSV board remains available from the source selector above.');return
    from propfinder_lines import apply_snapshot,load_snapshot
    frame,line_health=apply_snapshot(frame,load_snapshot(ROOT/'data'/'propfinder-fanduel.json'),day,PROPS[label])
    with st.expander('Games and tipoffs'):
        from dashboard_v2 import tipoff_et
        for g in games:
            st.write(f"{g.get('awayTeam',{}).get('teamTricode','?')} @ {g.get('homeTeam',{}).get('teamTricode','?')} · {tipoff_et(g.get('gameTimeUTC'))} · {g.get('gameStatusText','Scheduled')}")
    if frame.empty:
        st.info(health.get('message') or 'No verified player history is available for this slate.');return
    if health.get('schedule') and not health['schedule'].get('fresh',True):
        st.warning(health['schedule'].get('message','Schedule is from a saved snapshot.'))
    st.caption(f"Updated {health.get('built_at','')} · {health.get('teams',30)} league teams · {health.get('current_games',0)} current-season games. Checks for updates every 15 minutes while open.")
    st.caption('PG / SG / SF / PF / C matchups from ESPN depth charts. Defensive buckets use primary positions, with explicit depth-chart slots when a primary position is missing. Lineups are projected.')
    if health.get('failures'): st.warning('Some source requests failed. Missing values stay N/A; rank tooltips show the actual comparison count.')
    st.caption(f"FanDuel lines via PropFinder · Captured {line_health.get('captured_at','not available')} · Export snapshot, not a live sportsbook feed.")
    st.caption(line_health['message'])
    st.caption('L5/L10 over counts shown beneath averages come from PropFinder at the exported line. They describe past games, not win probabilities. NBA averages retain their existing history source.')
    filter_cols=st.columns(2)
    starters=filter_cols[0].checkbox('Projected starters only',value=True,key='clean_starters')
    hide=filter_cols[1].checkbox('Hide reported Out / Doubtful',value=True,key='clean_hide')
    if starters and 'Projected starter' in frame: frame=frame[frame['Projected starter']]
    if hide: frame=frame[~frame['Status'].str.casefold().isin(['out','doubtful'])]
    st.caption(f"{len(frame)} players · {season.lower()} defensive averages. Early-season ranks can be based on few games; tap a player or hover a value for sample counts. L10/L5 can cross seasons or teams; H2H uses current- and previous-season completed meetings.")
    meta={'Source':'ESPN verified finals','Slate date':day,'Player stat':label,'Window':'Full current regular season' if season=='Current season' else 'Loaded previous-season reference',
          'Defensive history':season,'Position groups':'PG/SG/SF/PF/C','Updated':health.get('built_at',''),'Line source':'FanDuel via PropFinder export','Line captured':line_health.get('captured_at','Unavailable'),'Line refresh':'Snapshot; requires a new published export','Hit counts':'PropFinder historical overs at the exported line'}
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
        st.caption('Live NBA combines verified completed games, five-position depth charts and league-wide defensive averages. Imported CSV preserves your exported values.')
        if st.button('Open advanced research',key='open_advanced'): st.session_state['clean_advanced']=True
    if st.session_state.get('clean_advanced'):
        with st.expander('Advanced research',expanded=True):
            from dashboard_v2 import render_saved_results
            render_saved_results()
