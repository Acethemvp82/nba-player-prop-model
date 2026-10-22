"""Clean NBA research dashboard. No fabricated betting probabilities or odds."""
from datetime import datetime, timezone
import os
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from espn_schedule import espn_games_on
from espn_history import collect_espn_history, espn_final_game_players
from projection_core import core_projections as build_pregame_baseline_board
from position_defense import positional_allowance as matchup_context
from defensive_table import defensive_table_html
from csv_export import safe_spreadsheet_cell
from slate_coverage import slate_coverage
from baseline_backtest import evaluate_baselines
from player_research import player_games, compare_line, minutes_scenario
from matchup_board import build_matchup_board, STATS
from live_sources import fetch_injuries, reported_status, fetch_event_odds, select_quote

ET = ZoneInfo("America/New_York")
PROPS = {"points": "Points", "rebounds": "Rebounds",
         "assists": "Assists", "threes": "3-Pointers"}

@st.cache_data(ttl=300, show_spinner=False)
def schedule_for(day):
    return espn_games_on(day)

@st.cache_data(ttl=3600, show_spinner=False)
def final_for(event_id, schema_version=2):
    return espn_final_game_players(event_id)

@st.cache_data(ttl=3600, show_spinner=False)
def history_for(day, days, cap, schema_version="positional-core-v1"):
    return collect_espn_history(
        day, days=days, max_games=cap,
        schedule_loader=schedule_for, boxscore_loader=final_for)

def tipoff_et(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ET).strftime("%I:%M %p ET")
    except (ValueError, TypeError, AttributeError):
        return "Unknown"


@st.cache_data(ttl=300, show_spinner=False)
def injuries_for():
    return fetch_injuries()


def render_dashboard():
    st.set_page_config(page_title="NBA Matchup Board", page_icon="🏀", layout="wide", initial_sidebar_state="collapsed")
    st.markdown("""<style>
    .block-container {max-width:1600px;padding-top:4.5rem;padding-bottom:2rem;}
    h1 {font-size:1.9rem!important;letter-spacing:-.035em;}
    [data-testid="stDataFrame"] {border:1px solid #353344;border-radius:8px;}
    [data-testid="stMetricValue"] {font-size:1.5rem;}
    div[data-testid="stVerticalBlock"] {gap:.65rem;}
    .nba-banner {padding:.8rem 1rem;border:1px solid #594369;border-radius:7px;
      background:linear-gradient(110deg,#30203f,#141825 65%);font-size:1.15rem;font-weight:700;}
    </style><div class="nba-banner">NBA DEFENSIVE MATCHUPS</div>""", unsafe_allow_html=True)
    with st.sidebar:
        st.header("Slate controls")
        day = st.date_input("Slate date", datetime.now(ET).date())
        lookback = st.select_slider("History window (days)", options=[7,14,21,30], value=21)
        cap = st.select_slider("Completed games to retrieve", options=[10,20,30,50,75,100], value=100)
        refresh = st.button("Build / refresh projections", type="primary", use_container_width=True)
        st.caption("History cached for one hour. Line feed requires a configured provider key.")
    key = (day.isoformat(),lookback,cap,"positional-core-v1")
    if refresh:
        schedule_for.clear(); final_for.clear(); history_for.clear(); injuries_for.clear()
    render_schedule(day.isoformat())
    if refresh or st.session_state.get("nba_v2_attempted_key") != key:
        st.session_state["nba_v2_attempted_key"] = key
        with st.spinner("Loading completed-game history…"):
            try:
                st.session_state["nba_v2_history"] = history_for(*key)
                st.session_state["nba_v2_key"] = key
                st.session_state["nba_v2_loaded_at"] = datetime.now(ET).strftime("%b %d, %I:%M %p ET")
            except Exception as exc:
                st.error(f"Historical data unavailable: {exc}")
    try:
        games = schedule_for(day.isoformat())
    except Exception as exc:
        games = []; st.warning(f"ESPN schedule unavailable: {exc}")
    opponents = {}
    for game in games:
        away=game.get("awayTeam",{}).get("teamTricode")
        home=game.get("homeTeam",{}).get("teamTricode")
        if away and home: opponents.update({away:home,home:away})
    ready = st.session_state.get("nba_v2_key") == key
    if not ready:
        st.info("History has not loaded for these settings. Use **Build / refresh projections** to retry.")
        return
    history = st.session_state["nba_v2_history"]
    observations = history.get("observations",[])
    context = matchup_context(observations,day.isoformat())
    forecasts = [{**r,'opponent':opponents[r['team']]} for r in
                 build_pregame_baseline_board(observations,day.isoformat(),min_games=5)
                 if r.get('team') in opponents]
    injury_feed = None
    if day == datetime.now(ET).date():
        try:
            injury_feed=injuries_for()
        except ValueError as exc:
            st.warning(str(exc))
    now=datetime.now(timezone.utc)
    forecasts=[{**r,"availability":reported_status(injury_feed,r['player'],r['team'],now)
                if injury_feed else "Unknown — no current report"} for r in forecasts]
    a,b,c,d=st.columns([1.4,1.2,2,2])
    with a:
        selected_label=st.selectbox("Selected prop",list(PROPS.values()))
    prop=next(k for k,v in PROPS.items() if v==selected_label)
    rows=build_matchup_board(observations,forecasts,opponents,day.isoformat(),prop,context)
    # Reported status also applies to players with sparse history.
    if injury_feed:
        for r in rows: r['Status']=reported_status(injury_feed,r['Player'],r['Team'],now)
    with b:
        position_options=["All"]+sorted({r['Group'] for r in rows})
        position=st.selectbox("Position group",position_options,index=position_options.index("G") if "G" in position_options else 0)
    with c:
        teams=st.multiselect("Defenses",sorted(opponents),default=sorted(opponents))
    with d:
        sort_choice=st.selectbox("Sort by",["Highest positional allowance","Highest projection","Most historical games","Player name"])
    search_col,status_col=st.columns([3,2])
    with search_col:
        search=st.text_input("Find player",placeholder="Search players…")
    with status_col:
        show_ranks=st.checkbox("Show rankings",value=True)
        hide_unavailable=st.checkbox("Hide players reported Out or Doubtful",value=True)
    covered=sum(any(f['team']==t for f in forecasts) for t in opponents)
    st.caption(f"{len(games)} games · {len(opponents)} teams · {covered} teams with minutes-based projections · "
               + st.session_state.get("nba_v2_loaded_at","Unknown build time"))
    st.caption(f"Line, L10, L5, H2H and Proj follow {selected_label}. The team column is the DEFENSE. "
               "Colored stats are per-game allowance to all Guards (G), Forwards (F), or Centers (C). "
               "Ranks compare qualified teams in this loaded sample; the denominator is shown. "
               "Broad G/F labels are not inferred PG/SG roles.")
    if history.get('failures') or history.get('history_truncated'):
        st.warning("Retrieved history is incomplete. Coverage details are below the board.")
    if rows:
        frame=pd.DataFrame(rows)
        for i,r in frame.iterrows():
            frame.at[i,'Line']=st.session_state.get('line_'+str(r['player_id'])+prop)
        frame=frame[frame['Opponent'].isin(teams) & frame['Player'].str.contains(search,case=False,regex=False,na=False)]
        if position!='All': frame=frame[frame['Group']==position]
        if hide_unavailable: frame=frame[~frame['Status'].str.casefold().isin(['out','doubtful'])]
        sorting={'Highest positional allowance':(['Matchup','Sample','Player'],[False,False,True]),
                 'Highest projection':(['Projection','Sample','Player'],[False,False,True]),
                 'Most historical games':(['Sample','Player'],[False,True]),
                 'Player name':(['Player'],[True])}
        by,asc=sorting[sort_choice]
        frame=frame.sort_values(by,ascending=asc,na_position='last').reset_index(drop=True)
        frame.insert(0,'Row',range(1,len(frame)+1))
        st.caption(f"{len(frame)} players shown · {int(frame['Def Rank'].notna().sum())} with ranked position evidence · blank projection = insufficient current-team history")
        columns=['Row','Team','Pos','Group','Player','Opponent','Line','L10','L5','H2H','H2H N',
                 'Projection','Model Min','Recent Min','Points','Rebounds','Assists','3PM','Steals','Blocks',
                 'Def Rank','Rank Teams','Defense Games','Sample','Status']
        st.html(defensive_table_html(frame,show_ranks=show_ranks))
        with st.expander("Board data and sample counts"):
            st.dataframe(frame[columns],hide_index=True,use_container_width=True)
        st.download_button('Export board CSV',frame[columns].map(safe_spreadsheet_cell).to_csv(index=False),
            file_name=f'nba_matchup_board_{day.isoformat()}.csv',mime='text/csv')
    else:
        st.info("No historical player samples for these scheduled teams yet.")
    if not forecasts:
        st.warning("No eligible projections for this slate. Short-history averages remain available below.")
    with st.expander("Player details, lines and minutes scenarios"):
        if forecasts: render_player_research(forecasts,history,day.isoformat())
        else: st.caption('Player line comparison needs a qualifying baseline.')
    with st.expander("Data coverage and model checks"):
        coverage,sparse=slate_coverage(observations,day.isoformat(),opponents,forecasts)
        if coverage: st.dataframe(pd.DataFrame(coverage),hide_index=True,use_container_width=True)
        st.caption('Historical team membership does not confirm current roster or starters. Samples may include preseason.')
        st.write({k:history.get(k) for k in ['games_loaded','games_requested','dates_checked','eligible_games_omitted']})
        if history.get('failures'): st.dataframe(pd.DataFrame(history['failures']),hide_index=True)
        if injury_feed: st.caption('Injury feed retrieved: '+injury_feed['retrieved_at'])
        if sparse:
            st.caption('Short-history averages — observed results, not forecasts')
            st.dataframe(pd.DataFrame(sparse),hide_index=True,use_container_width=True)
        render_validation(history,day.isoformat())
    with st.expander("How to read this board"):
        st.write('L10 and L5 are means of up to ten and five available games, not guaranteed full samples. '
                 'H2H is the observed average against this opponent within the loaded window; its sample is shown. '
                 'Proj uses median last-five minutes times weighted per-minute production, requiring five valid games on the current historical team. '
                 'Colored stats show observed allowance to the full position group. Rank 1 is the most allowed among qualified sample teams, not a league-wide rank unless all 30 qualify. '
                 'Position is shown only when provided by a completed-game source. '
                 'Lines are blank until entered in Player details or copied from the configured provider feed.')


@st.fragment(run_every=60)
def render_schedule(day):
    try:
        games = schedule_for(day)
    except Exception as exc:
        st.warning(f"Schedule refresh unavailable: {exc}")
        return
    with st.expander("Today's matchups and tipoffs", expanded=True):
        if games:
            rows = []
            for game in games:
                away = game.get("awayTeam", {}).get("teamTricode", "?")
                home = game.get("homeTeam", {}).get("teamTricode", "?")
                rows.append({"Matchup": f"{away} @ {home}",
                             "Status": game.get("gameStatusText", "Unknown"),
                             "Tipoff (ET)": tipoff_et(game.get("gameTimeUTC", ""))})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("No schedule data for selected date.")
        st.caption("Schedule checks every minute while open; source cache lasts five minutes. Times shown in Eastern Time.")


@st.cache_data(ttl=3600, show_spinner=False)
def validation_for(observations, day, schema_version=3):
    return evaluate_baselines(observations, day, min_training_games=5,model="minutes")


def render_validation(history, day):
    st.subheader("Prediction validation — earlier games only")
    st.caption("Retrospective walk-forward check: each forecast uses at least five appearances "
               "from strictly earlier dates. Same-day results never enter training. "
               "These are reconstructed forecasts, not saved pregame predictions.")
    result = validation_for(history.get("observations", []), day, schema_version=3)
    summary = pd.DataFrame(result["summary"])
    evaluated = int(summary["evaluated"].sum())
    if not evaluated:
        st.info("Not enough earlier games to evaluate a five-game forecast yet. "
                "Zero scored forecasts means accuracy is unknown, not zero error.")
        return
    st.caption(f"{evaluated} scored player-prop forecasts across the loaded history. "
               "Four props from one appearance are four forecasts, not four independent games.")
    if history.get("history_truncated") or history.get("failures"):
        st.warning("Validation uses an incomplete retrieved sample. Missing games can change both forecasts and measured error.")
    # Older cached evaluations may lack this newly introduced summary field.
    if "different_from_last5" not in summary:
        summary["different_from_last5"] = summary["prop"].map(lambda prop: sum(
            abs(d["baseline"] - d["last5_baseline"]) > 0.005
            for d in result.get("details", []) if d.get("prop") == prop))
    if int(summary["different_from_last5"].sum()) == 0:
        st.info("The model and reference forecasts are identical in this evaluation sample. "
                "This comparison cannot yet establish an advantage for either method.")
    st.caption("Reference: " + result.get("reference", "last-five average") + ". Forecast weights are not selected by these results.")
    summary["prop"] = summary["prop"].map(PROPS)
    labels = {"prop": "Prop", "evaluated": "Scored forecasts", "players_evaluated": "Players",
              "dates_evaluated": "Dates", "coverage_pct": "Evaluated coverage %",
              "mae": "Model MAE", "last5_mae": "Reference MAE",
              "different_from_last5": "Different forecasts",
              "mae_delta_vs_last5": "Model minus reference", "mean_error": "Bias", "rmse": "RMSE",
              "first_evaluation_date": "First result", "last_evaluation_date": "Last result"}
    table = summary[list(labels)].rename(columns=labels)
    st.dataframe(table, hide_index=True, use_container_width=True,
        column_config={k: st.column_config.NumberColumn(k, format="%.3f")
            for k in ("Model MAE", "Reference MAE", "Model minus reference", "Bias", "RMSE")})
    st.caption("MAE is the average size of a miss in that prop's units; lower is better. "
               "A negative Model minus reference favors the new model. Positive bias means overprediction. "
               "Coverage includes appearances that had too little earlier history to forecast. "
               "Small, potentially preseason samples do not establish betting accuracy; no formula is auto-tuned here.")
    with st.expander("Audit scored forecasts and training dates"):
        details = pd.DataFrame(result["details"])
        choice = st.selectbox("Validation prop", list(PROPS.values()))
        details["prop"] = details["prop"].map(PROPS)
        details = details[details["prop"] == choice].sort_values(
            ["game_date", "player_id"], ascending=[False, True])
        st.dataframe(details, hide_index=True, use_container_width=True)
        st.download_button("Download scored forecast audit CSV",
            details.map(safe_spreadsheet_cell).to_csv(index=False),
            file_name=f"nba_validation_{day}.csv", mime="text/csv")


def render_player_research(forecasts, history, day):
    st.subheader("Player line comparison")
    st.caption("Choose a player and enter the line you see at your sportsbook. "
               "Recent outcomes are historical counts, not a predicted hit probability.")
    options = {f"{r['player']} · {r['team']} · {PROPS[r['prop']]}": r for r in forecasts}
    label = st.selectbox("Player and prop", sorted(options))
    selected = options[label]
    games = player_games(history.get("observations", []), selected['player_id'], selected['prop'], day)
    st.write("Reported availability: " + selected.get("availability", "Unknown"))
    render_live_quote(selected, day)
    st.caption("Validated model hit probability: unavailable. The current evaluation sample "
               "does not establish calibrated probabilities; historical hit counts are not a substitute.")
    a, b, c = st.columns(3)
    a.metric("Baseline", f"{selected['baseline']:.1f}")
    b.metric("Model minutes", f"{selected.get('forecast_minutes',selected['recent_minutes']):.1f}")
    c.metric("Training appearances", str(selected["sample_games"]))
    cols = st.columns(2)
    with cols[0]:
        line = st.number_input("Sportsbook line (manual)", min_value=0.0, value=None, step=0.5,
                               placeholder="Enter the current line", key="line_" + str(selected["player_id"]) + selected["prop"])
    with cols[1]:
        odds = st.number_input("Over American odds (optional)", value=None, step=1,
                               placeholder="For example, -110", key="odds_" + str(selected["player_id"]) + selected["prop"])
    if line is not None:
        result = compare_line(games, line, odds)
        a, b, c = st.columns(3)
        a.metric("Historical overs", f"{result['over']} / {result['sample_games']}")
        b.metric("Historical unders", str(result['under']))
        c.metric("Historical pushes", str(result['push']))
        st.caption(f"Baseline minus entered line: {selected['baseline'] - line:+.1f}. "
                   "A projection gap alone does not establish an edge.")
        if odds is not None:
            if result['break_even'] is None:
                st.warning("American odds must be an integer of -100 or lower, or +100 or higher.")
            else:
                st.metric("Odds break-even probability", f"{100 * result['break_even']:.1f}%")
                st.caption("Break-even is calculated from your entered odds, before any vig adjustment. "
                           "It is not the model's predicted chance.")
    with st.expander("Recent completed games and minutes scenario"):
        if games:
            st.dataframe(pd.DataFrame(games), hide_index=True, use_container_width=True)
        scenario_base = selected.get("forecast_minutes", selected["recent_minutes"])
        expected = st.number_input("Scenario minutes (your assumption)", min_value=0.0,
            max_value=48.0, value=min(48.0, float(scenario_base)), step=1.0,
            key="scenario_" + str(selected['player_id']) + selected['prop'])
        scenario = minutes_scenario(selected['baseline'], scenario_base, expected)
        st.metric("Minutes-only scenario", f"{scenario:.1f}")
        st.caption("Scales the baseline in proportion to your minutes assumption. "
                   "This is a sensitivity check, not an injury-adjusted forecast; it does not change the main board.")

    if line is not None:
        record = {"recorded_at": datetime.now(ET).isoformat(), "slate_date": day,
                  "player": selected['player'], "player_id": selected['player_id'],
                  "team": selected['team'], "prop": selected['prop'],
                  "baseline": selected['baseline'], "entered_line": line,
                  "entered_over_odds": odds, "line_source": "manual user entry; not live-verified",
                  "historical_games": result['sample_games'], "historical_overs": result['over'],
                  "historical_unders": result['under'], "historical_pushes": result['push'],
                  "odds_break_even": result['break_even'], "scenario_minutes": expected,
                  "minutes_only_scenario": scenario}
        st.download_button("Download player line research CSV",
            pd.DataFrame([record]).map(safe_spreadsheet_cell).to_csv(index=False),
            file_name=f"nba_player_research_{day}.csv", mime="text/csv")


def odds_key():
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("ODDS_API_KEY", "")
        except (FileNotFoundError, KeyError):
            pass
    return key


def render_live_quote(selected, day):
    with st.expander("FanDuel line feed"):
        key = odds_key()
        if not key:
            st.info("Live lines need a provider key. Add ODDS_API_KEY to Streamlit Secrets "
                    "for The Odds API (the-odds-api.com). Do not put keys in GitHub or chat. "
                    "Manual line entry remains available below.")
            return
        st.caption("Fetches four prop markets for this matchup only. Each provider request "
                   "can consume plan credits; no automatic polling or paid signup occurs.")
        identity = (day, selected['team'], selected['opponent'])
        if st.button("Fetch current FanDuel lines for this matchup"):
            try:
                st.session_state['nba_live_quote'] = (identity,
                    fetch_event_odds(key, selected['team'], selected['opponent'], day,
                                     datetime.now(timezone.utc)))
            except ValueError as exc:
                st.error(str(exc))
                st.session_state.pop('nba_live_quote', None)
        cached = st.session_state.get('nba_live_quote')
        if cached and cached[0] == identity:
            quote = select_quote(cached[1], selected['player'], selected['prop'], datetime.now(timezone.utc))
            if quote:
                st.write(f"FanDuel Over {quote['line']} at {quote['odds']:+d}; provider updated {quote['updated_at']}")
                st.caption("Quotes older than 30 minutes and started events are rejected. "
                           "Confirm the current offer in your sportsbook.")
                if st.button("Copy fetched quote into comparison"):
                    st.session_state['line_' + str(selected['player_id']) + selected['prop']] = float(quote['line'])
                    st.session_state['odds_' + str(selected['player_id']) + selected['prop']] = int(quote['odds'])
            else:
                st.info("No unique fresh FanDuel over quote for this player and prop. "
                        "The market may be unavailable, stale, ambiguous or already started.")
