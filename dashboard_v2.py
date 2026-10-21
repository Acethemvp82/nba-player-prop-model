"""Clean NBA research dashboard. No fabricated betting probabilities or odds."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from espn_schedule import espn_games_on
from espn_history import collect_espn_history, espn_final_game_players
from pregame_baseline_board import build_pregame_baseline_board
from matchup_scoring import matchup_context, attach_matchups
from csv_export import safe_spreadsheet_cell
from slate_coverage import slate_coverage

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

def tipoff_et(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ET).strftime("%I:%M %p ET")
    except (ValueError, TypeError, AttributeError):
        return "Unknown"


def render_dashboard():
    st.set_page_config(page_title="NBA Prop Board", page_icon="🏀", layout="wide")
    st.title("NBA Player Prop Board")
    st.caption("Rebuild milestone 2 · Slate coverage + matchup context")
    st.caption("Player baselines • Opponent matchup context • Points, rebounds, assists and threes")
    with st.sidebar:
        st.header("Slate controls")
        day = st.date_input("Slate date", datetime.now(ET).date())
        lookback = st.select_slider("History window (days)", options=[7, 14, 21, 30], value=21)
        cap = st.select_slider("Completed games to retrieve", options=[10, 20, 30, 50, 75, 100], value=100)
        refresh = st.button("Build / refresh projections", type="primary", use_container_width=True)
        st.caption("Historical results are cached for one hour. No live sportsbook connection.")
    key = (day.isoformat(), lookback, cap)
    if refresh:
        schedule_for.clear()
        final_for.clear()
        history_for.clear()
    if refresh or st.session_state.get("nba_v2_attempted_key") != key:
        st.session_state["nba_v2_attempted_key"] = key
        with st.spinner("Retrieving verified completed-game statistics…"):
            try:
                st.session_state["nba_v2_history"] = history_for(*key)
                st.session_state["nba_v2_key"] = key
                st.session_state["nba_v2_loaded_at"] = datetime.now(ET).strftime("%b %d, %I:%M %p ET")
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
        st.info("History has not loaded for these settings. Use **Build / refresh projections** to retry.")
    else:
        history = st.session_state["nba_v2_history"]
        if history.get("failures") or history.get("history_truncated"):
            st.warning("Historical feed has gaps or was capped. Treat projections as incomplete research baselines.")
        with st.expander("History retrieval health"):
            st.write({"Games loaded": history.get("games_loaded", 0),
                      "Games requested": history.get("games_requested", 0),
                      "Dates checked": history.get("dates_checked", 0),
                      "Failures": len(history.get("failures", [])),
                      "Games omitted by cap": history.get("eligible_games_omitted", 0)})
            if history.get("failures"):
                st.dataframe(pd.DataFrame(history["failures"]), hide_index=True)
            st.caption("The selected window can include preseason games. These are research samples, not confirmed current-season or active-roster projections.")
        forecasts = build_pregame_baseline_board(
            history.get("observations", []), day.isoformat(), min_games=5)
        forecasts = attach_matchups(forecasts, opponents,
            matchup_context(history.get("observations", []), day.isoformat()))
        coverage, sparse = slate_coverage(history.get("observations", []),
            day.isoformat(), opponents, forecasts)
        covered = sum(r["Baseline rows"] > 0 for r in coverage)
        st.metric("Teams with baselines", f"{covered} / {len(opponents)}")
        missing = [r["Team"] for r in coverage if not r["Baseline rows"]]
        if missing:
            st.warning("No five-game baselines for: " + ", ".join(missing)
                       + ". See coverage and short-history averages below.")
        with st.expander("Slate coverage — every scheduled team"):
            if coverage:
                st.dataframe(pd.DataFrame(coverage), hide_index=True, use_container_width=True)
            st.caption("Counts are before board filters and use historical team membership. "
                       "They do not verify today's roster, starters or injury status.")
        with st.expander(f"Short-history averages — {len(sparse)} players below five appearances"):
            st.caption("Observed averages only. These players do not meet the five-game "
                       "baseline minimum and are excluded from the projection board. "
                       "Samples may include preseason; availability is unconfirmed.")
            if sparse:
                sparse_frame = pd.DataFrame(sparse)
                st.dataframe(sparse_frame, hide_index=True, use_container_width=True,
                    column_config={key: st.column_config.NumberColumn(key, format="%.1f")
                                   for key in sparse_frame.columns if key.endswith(" avg")})
                st.download_button("Download short-history averages CSV",
                    sparse_frame.map(safe_spreadsheet_cell).to_csv(index=False),
                    file_name=f"nba_short_history_{day.isoformat()}.csv", mime="text/csv")
            else:
                st.caption("No short-history player samples in the retrieved data.")
        st.caption("Last successful build: " + st.session_state.get("nba_v2_loaded_at", "Unknown"))
        st.caption(f"{len(forecasts)} eligible player-prop projections from teams on this slate. "
                   "Baseline values are not calibrated betting probabilities or matchup-adjusted forecasts.")
        if forecasts:
            frame = pd.DataFrame(forecasts)
            frame["Opponent"] = frame["opponent"]
            frame["Matchup"] = pd.to_numeric(frame["matchup_score"], errors="coerce")
            frame["Opp Games"] = frame["opponent_games"]
            frame["Opp Allowed"] = frame["opponent_allowed"]
            frame["Prop"] = frame["prop"].map(PROPS)
            frame["Projection"] = pd.to_numeric(frame["baseline"], errors="coerce").round(1)
            frame["Sample"] = frame["sample_games"]
            frame["Recent MPG"] = pd.to_numeric(frame["recent_minutes"], errors="coerce").round(1)
            frame["Readiness"] = frame["research_readiness"].map({
                "history_ready": "Established", "limited_sample": "Limited",
                "stale_history": "Stale"}).fillna("Unknown")
            frame["Player"] = frame["player"]
            frame["Team"] = frame["team"]
            filters = st.columns([2, 2, 2])
            with filters[0]:
                selected = st.multiselect(
                    "Prop categories", list(PROPS.values()),
                    default=list(PROPS.values()))
            with filters[1]:
                teams = sorted(frame["Team"].dropna().unique().tolist())
                chosen_teams = st.multiselect("Teams", teams, default=teams)
            with filters[2]:
                readiness = st.multiselect(
                    "Data readiness", ["Established", "Limited", "Stale"],
                    default=["Established", "Limited", "Stale"])
            player_search = st.text_input(
                "Find player", placeholder="Search by player name…")
            sort_choice = st.selectbox(
                "Sort research board",
                ["Most historical games", "Highest baseline within prop", "Highest matchup score", "Player name"])
            frame = frame[
                frame["Player"].str.contains(player_search, case=False, regex=False, na=False)
            ]
            frame = frame[
                frame["Prop"].isin(selected)
                & frame["Team"].isin(chosen_teams)
                & frame["Readiness"].isin(readiness)
            ].copy()
            if sort_choice == "Highest baseline within prop":
                frame = frame.sort_values(
                    ["Prop", "Projection", "Sample", "Player"],
                    ascending=[True, False, False, True]).reset_index(drop=True)
            elif sort_choice == "Highest matchup score":
                frame = frame.sort_values(["Matchup", "Sample", "Player", "Prop"],
                    ascending=[False, False, True, True], na_position="last").reset_index(drop=True)
            elif sort_choice == "Player name":
                frame = frame.sort_values(
                    ["Player", "Prop"], ascending=[True, True]).reset_index(drop=True)
            else:
                frame = frame.sort_values(
                    ["Sample", "Player", "Prop"],
                    ascending=[False, True, True]).reset_index(drop=True)
            frame.insert(0, "Row", range(1, len(frame) + 1))
            established = int((frame["Readiness"] == "Established").sum())
            limited = int((frame["Readiness"] == "Limited").sum())
            stale = int((frame["Readiness"] == "Stale").sum())
            x, y, z, w = st.columns(4)
            x.metric("Visible projections", len(frame))
            y.metric("Established", established)
            z.metric("Limited", limited)
            w.metric("Stale", stale)
            columns = ["Row", "Player", "Team", "Opponent", "Prop",
                       "Projection", "Matchup", "Opp Games", "Opp Allowed", "Sample", "Recent MPG", "Readiness"]
            st.dataframe(
                frame[columns].style.map(
                    lambda v: "background-color: #174d36; color: white" if v == "Established"
                    else "background-color: #6b491d; color: white" if v == "Limited"
                    else "background-color: #692a2a; color: white" if v == "Stale" else "",
                    subset=["Readiness"]).map(
                    lambda v: "" if pd.isna(v) else ("background-color: #174d36; color: white" if v >= 60
                    else "background-color: #692a2a; color: white" if v <= 40
                    else "background-color: #6b491d; color: white"), subset=["Matchup"]),
                use_container_width=True, hide_index=True,
                column_config={
                    "Row": st.column_config.NumberColumn("#", help="Display order only, not a betting ranking."),
                    "Projection": st.column_config.NumberColumn("Baseline", format="%.1f", help="Unadjusted historical projection."),
                    "Matchup": st.column_config.NumberColumn("Matchup / 100", format="%.1f", help="Descriptive allowance score. 50 neutral; higher means more allowed in this sample. Not a hit probability."),
                    "Opp Allowed": st.column_config.NumberColumn("Opp allowed / game", format="%.1f"),
                    "Opp Games": st.column_config.NumberColumn("Opponent sample"),
                    "Sample": st.column_config.NumberColumn("Games sampled"),
                    "Recent MPG": st.column_config.NumberColumn("Recent minutes", format="%.1f"),
                    "Readiness": st.column_config.TextColumn("History quality"),
                })
            st.download_button("Download projections CSV",
                               frame[columns].map(safe_spreadsheet_cell).to_csv(index=False),
                               file_name=f"nba_baselines_{day.isoformat()}.csv",
                               mime="text/csv")
            st.caption("Display order follows your selected sort. It is not a betting-value ranking. "
                       "Matchup colors: green ≥60, amber 40–60, red ≤40. Blank means insufficient data; not a 0 score.")
        else:
            st.warning("No eligible projections for this slate with the loaded history. "
                       "Increase the history window or game cap; do not treat missing players as zero projections.")
    render_schedule(day.isoformat())
    with st.expander("Methodology and data limitations"):
        st.write("Projections use verified completed-game statistics before the selected slate date. "
                 "A minimum of five historical games is required. ESPN roster listings alone "
                 "never count as player projections. This board does not have FanDuel lines, "
                 "or calibrated over probabilities. Matchup scores compare observed opponent allowance "
                 "against the loaded sample, require five games and eight observed players per game, "
                 "and shrink toward 50 using five prior games. They do not control for pace, position, "
                 "opponent strength or complete roster coverage, and do not change the baseline. "
                 "Historical team membership does not confirm today’s roster or availability.")


@st.fragment(run_every=60)
def render_schedule(day):
    try:
        games = schedule_for(day)
    except Exception as exc:
        st.warning(f"Schedule refresh unavailable: {exc}")
        return
    with st.expander("Today's matchups and tipoffs"):
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
