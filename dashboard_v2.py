"""Clean NBA research dashboard. No fabricated betting probabilities or odds."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from espn_schedule import espn_games_on
from espn_history import collect_espn_history, espn_final_game_players
from pregame_baseline_board import build_pregame_baseline_board

ET = ZoneInfo("America/New_York")
PROPS = {"points": "Points", "rebounds": "Rebounds",
         "assists": "Assists", "threes": "3-Pointers"}

@st.cache_data(ttl=300, show_spinner=False)
def schedule_for(day):
    return espn_games_on(day)

@st.cache_data(ttl=3600, show_spinner=False)
def final_for(event_id):
    return espn_final_game_players(event_id)

@st.cache_data(ttl=3600, show_spinner=False)
def history_for(day, days, cap):
    return collect_espn_history(
        day, days=days, max_games=cap,
        schedule_loader=schedule_for, boxscore_loader=final_for)

def render_dashboard():
    st.set_page_config(page_title="NBA Prop Board", page_icon="🏀", layout="wide")
    st.title("🏀 NBA Player Prop Board")
    st.caption("Pregame statistical baselines • Verified completed games • No invented odds")
    with st.sidebar:
        st.header("Slate controls")
        day = st.date_input("Slate date", datetime.now(ET).date())
        lookback = st.select_slider("History window (days)", options=[7, 14, 21, 30], value=21)
        cap = st.select_slider("Completed games to retrieve", options=[10, 20, 30, 50, 75, 100], value=50)
        refresh = st.button("Build / refresh projections", type="primary", use_container_width=True)
        st.caption("Historical results are cached for one hour. No live sportsbook connection.")
    key = (day.isoformat(), lookback, cap)
    if refresh:
        with st.spinner("Retrieving verified completed-game statistics…"):
            try:
                st.session_state["nba_v2_history"] = history_for(*key)
                st.session_state["nba_v2_key"] = key
            except Exception as exc:
                st.error(f"Historical data unavailable: {exc}")
    try:
        games = schedule_for(day.isoformat())
    except Exception as exc:
        games = []
        st.warning(f"ESPN schedule unavailable: {exc}")
    opponents = {}
    for game in games:
        away = game.get("awayTeam", {}).get("teamTricode")
        home = game.get("homeTeam", {}).get("teamTricode")
        if away and home:
            opponents[away] = home
            opponents[home] = away
    a, b, c = st.columns(3)
    a.metric("Games on slate", len(games))
    b.metric("Teams on slate", len(opponents))
    ready = st.session_state.get("nba_v2_key") == key
    c.metric("Historical data", "Loaded" if ready else "Not loaded")
    st.subheader("Master projection board")
    if not ready:
        st.info("Select **Build / refresh projections** in the sidebar to load verified player history and populate this board.")
    else:
        history = st.session_state["nba_v2_history"]
        if history.get("failures") or history.get("history_truncated"):
            st.warning("Historical feed has gaps or was capped. Treat projections as incomplete research baselines.")
        forecasts = build_pregame_baseline_board(
            history.get("observations", []), day.isoformat(), min_games=5)
        forecasts = [r for r in forecasts if r.get("team") in opponents]
        st.caption(f"{len(forecasts)} eligible player-prop projections from teams on this slate. "
                   "Baseline values are not calibrated betting probabilities or matchup-adjusted forecasts.")
        if forecasts:
            frame = pd.DataFrame(forecasts)
            frame["Opponent"] = frame["team"].map(opponents)
            frame["Prop"] = frame["prop"].map(PROPS)
            frame["Projection"] = pd.to_numeric(frame["baseline"], errors="coerce").round(1)
            frame["Sample"] = frame["sample_games"]
            frame["Readiness"] = frame["research_readiness"].map({
                "history_ready": "Established", "limited_sample": "Limited",
                "stale_history": "Stale"}).fillna("Unknown")
            frame["Player"] = frame["player"]
            frame["Team"] = frame["team"]
            selected = st.multiselect("Prop categories", list(PROPS.values()), default=list(PROPS.values()))
            frame = frame[frame["Prop"].isin(selected)]
            frame = frame.sort_values(["Sample", "Player", "Prop"],
                                      ascending=[False, True, True]).reset_index(drop=True)
            frame.insert(0, "Research Rank", range(1, len(frame) + 1))
            columns = ["Research Rank", "Player", "Team", "Opponent", "Prop",
                       "Projection", "Sample", "Readiness"]
            st.dataframe(frame[columns].style.map(
                lambda v: "background-color: #174d36; color: white" if v == "Established"
                else "background-color: #6b491d; color: white" if v == "Limited"
                else "background-color: #692a2a; color: white" if v == "Stale" else "",
                subset=["Readiness"]), use_container_width=True, hide_index=True)
            st.download_button("Download projections CSV",
                               frame[columns].to_csv(index=False),
                               file_name=f"nba_baselines_{day.isoformat()}.csv",
                               mime="text/csv")
            st.caption("Research Rank sorts by historical sample size, NOT expected betting value. "
                       "No betting tiers until matchup adjustments and calibration are validated.")
        else:
            st.warning("No eligible projections for this slate with the loaded history. "
                       "Increase the history window or game cap; do not treat missing players as zero projections.")
    with st.expander("Today's matchups and tipoffs"):
        if games:
            rows = []
            for game in games:
                away = game.get("awayTeam", {}).get("teamTricode", "?")
                home = game.get("homeTeam", {}).get("teamTricode", "?")
                rows.append({"Matchup": f"{away} @ {home}",
                             "Status": game.get("gameStatusText", "Unknown"),
                             "Tipoff (UTC)": game.get("gameTimeUTC", "")})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("No schedule data for selected date.")
    with st.expander("Methodology and data limitations"):
        st.write("Projections use verified completed-game statistics before the selected slate date. "
                 "A minimum of five historical games is required. ESPN roster listings alone "
                 "never count as player projections. This board does not have FanDuel lines, "
                 "calibrated over probabilities, or validated opponent adjustments.")
