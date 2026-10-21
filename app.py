"""NBA Player Prop Model — live schedule and player feed preview."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from nba_data import NBADataError, scoreboard, game_players
from season_schedule import season_schedule, games_on
from history_collection import recent_player_summaries, fetch_boxscore_players
from projection_baseline import baseline_projections
from pregame_roster import candidate_players

st.set_page_config(page_title="NBA Player Prop Model", page_icon="🏀", layout="wide")
st.title("🏀 NBA Player Prop Model")
st.caption("FanDuel-focused | Master board | NBA feed preview v0.2")
st.info("NBA schedule and available game-roster data are displayed below. Pregame projections and FanDuel odds are NOT connected. This is not a ranked betting board.")

@st.cache_data(ttl=300, show_spinner=False)
def load_games():
    return scoreboard()

@st.cache_data(ttl=900, show_spinner=False)
def load_players(game_id):
    return game_players(str(game_id))

if st.button("Refresh NBA feed"):
    load_games.clear()
    load_players.clear()
    st.rerun()

st.caption("Feed checked on refresh or after cache expiry. Games update approximately every 5 minutes; player listings every 15 minutes.")
try:
    games = load_games()
except NBADataError as exc:
    st.error(f"Could not retrieve NBA games: {exc}")
    games = []

game_rows = []
for game in games:
    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    game_rows.append({
        "Game ID": str(game.get("gameId") or ""),
        "Matchup": f'{away.get("teamTricode", "?")} @ {home.get("teamTricode", "?")}',
        "Status": game.get("gameStatusText") or "Unknown",
        "Tipoff (UTC)": game.get("gameTimeUTC") or "Not available",
    })

@st.cache_data(ttl=3600, show_spinner=False)
def load_schedule():
    return season_schedule()

st.subheader("Upcoming NBA slate")
slate_date = st.date_input("Slate date", value=datetime.now(ZoneInfo("America/New_York")).date())
try:
    slate_games = games_on(slate_date, load_schedule())
except NBADataError as exc:
    st.warning(str(exc))
    slate_games = []
st.caption(f"{len(slate_games)} scheduled games for {slate_date}")
slate_rows = []
for scheduled in slate_games:
    home = scheduled.get("homeTeam") or {}
    away = scheduled.get("awayTeam") or {}
    slate_rows.append({
        "Game ID": str(scheduled.get("gameId") or ""),
        "Matchup": f'{away.get("teamTricode", "?")} @ {home.get("teamTricode", "?")}',
        "Status": scheduled.get("gameStatusText") or "Scheduled",
        "Tipoff (UTC)": scheduled.get("gameTimeUTC") or "Not available",
    })
if slate_rows:
    st.dataframe(pd.DataFrame(slate_rows).drop(columns=["Game ID"]),
                 use_container_width=True, hide_index=True)
else:
    st.info("No games listed for the selected date.")

st.subheader("Current-day NBA games")
if game_rows:
    st.dataframe(pd.DataFrame(game_rows).drop(columns=["Game ID"]), use_container_width=True, hide_index=True)
else:
    st.warning("No games returned by today's NBA scoreboard.")

st.subheader("Historical player statistics — research preview")
st.caption("Official completed-game box scores only. These are descriptive averages, not predictions or betting edges.")
@st.cache_data(ttl=86400, show_spinner=False)
def load_final_boxscore(game_id):
    return fetch_boxscore_players(game_id)

@st.cache_data(ttl=3600, show_spinner=False)
def load_historical_summary(as_of, game_limit):
    return recent_player_summaries(load_schedule(), as_of=as_of,
                                   max_games=game_limit, loader=load_final_boxscore)

history_limit = st.select_slider("Recent completed games to retrieve", options=[10, 20, 40, 80, 160, 320], value=80)
st.caption("Larger samples may require hundreds of NBA requests on first load. Verified final-game box scores are cached individually for 24 hours; aggregate summaries for one hour.")
if st.button("Load historical player averages"):
    try:
        with st.spinner("Loading completed NBA game data..."):
            historical = load_historical_summary(slate_date.isoformat(), history_limit)
        st.session_state["nba_historical_preview"] = historical
        st.session_state["nba_historical_preview_date"] = slate_date.isoformat()
        st.session_state["nba_historical_preview_limit"] = history_limit
    except (NBADataError, ValueError, TypeError, KeyError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")

historical = st.session_state.get("nba_historical_preview")
if st.session_state.get("nba_historical_preview_date") != slate_date.isoformat():
    historical = None
if historical:
    st.caption(f"Historical sample as of {st.session_state.get('nba_historical_preview_date')}: "
               f"{historical['games_loaded']} of {historical['games_requested']} requested games loaded "
               f"({historical['eligible_games']} eligible games in schedule). "
               "Season averages cover only the collected sample, not necessarily the full season.")
    if historical["summaries"]:
        st.metric("Players with completed-game observations", len(historical["summaries"]))
        st.metric("Players with 5+ sampled games", sum(item.get("games_played", 0) >= 5 for item in historical["summaries"]))
        fields = ["player", "team", "games_played", "minutes_last_5_avg",
                  "points_last_5_avg", "rebounds_last_5_avg",
                  "assists_last_5_avg", "threes_last_5_avg",
                  "points_last_10_avg", "rebounds_last_10_avg",
                  "assists_last_10_avg", "threes_last_10_avg"]
        st.dataframe(pd.DataFrame(historical["summaries"])[fields],
                     use_container_width=True, hide_index=True)
    else:
        st.warning("No usable completed-game player observations were returned.")
    if historical["failed_games"]:
        with st.expander(f"Historical box scores unavailable ({len(historical['failed_games'])})"):
            st.dataframe(pd.DataFrame(historical["failed_games"]), hide_index=True)


st.subheader("Master Player Prop Board — data preview")
categories = ["Points", "Rebounds", "Assists", "3-Pointers"]
selected = st.multiselect("Prop categories", categories, default=categories)
columns = ["Game", "Player", "Player ID", "Team", "Opponent", "Roster Source", "Last Seen", "Prop", "FanDuel Line", "Over Odds", "Projection", "Over Probability", "Edge", "Confidence"]
rows = []
failures = []
for game in slate_rows:
    if not game["Game ID"]:
        continue
    try:
        players = load_players(game["Game ID"])
    except NBADataError as exc:
        failures.append(f'{game["Matchup"]}: {exc}')
        continue
    for player in players:
        if not player.get("player"):
            continue
        for prop in selected:
            rows.append({
                "Game": game["Matchup"],
                "Player": player["player"],
                "Player ID": player.get("player_id"),
                "Team": player.get("team"),
                "Opponent": player.get("opponent"),
                "Roster Source": "NBA game feed",
                "Last Seen": None,
                "Prop": prop,
                "FanDuel Line": None,
                "Over Odds": None,
                "Projection": None,
                "Over Probability": None,
                "Edge": None,
                "Confidence": "Not calculated",
            })
history_for_slate = st.session_state.get("nba_historical_preview")
if st.session_state.get("nba_historical_preview_date") != slate_date.isoformat():
    history_for_slate = None
if history_for_slate and history_for_slate.get("summaries"):
    candidates = candidate_players(slate_games, history_for_slate["summaries"], slate_date)
    known = {(str(item["Player ID"]), item["Team"]) for item in rows}
    for candidate in candidates:
        key = (str(candidate["player_id"]), candidate["team"])
        if key in known:
            continue
        for game in slate_rows:
            teams = game["Matchup"].split(" @ ")
            if candidate["team"] not in teams:
                continue
            opponent = teams[0] if candidate["team"] == teams[1] else teams[1]
            for prop in selected:
                rows.append({"Game": game["Matchup"], "Player": candidate["player"],
                             "Player ID": candidate["player_id"], "Team": candidate["team"],
                             "Opponent": opponent, "Roster Source": "Historical candidate (unconfirmed)",
                             "Last Seen": candidate["last_seen"], "Prop": prop, "FanDuel Line": None,
                             "Over Odds": None, "Projection": None,
                             "Over Probability": None, "Edge": None,
                             "Confidence": "Historical candidate; unconfirmed"})
            known.add(key)
            break
board = pd.DataFrame(rows, columns=columns)
if not board.empty:
    st.caption(f"{board['Player'].nunique()} players from available game feeds or historical candidates. Roster Source and Last Seen show where each listing came from; availability is not verified.")
    historical_board = st.session_state.get("nba_historical_preview")
    if st.session_state.get("nba_historical_preview_date") != slate_date.isoformat():
        historical_board = None
    if historical_board and historical_board.get("summaries"):
        baseline_lookup = {(str(item["player_id"]), item["prop"]): item["baseline"]
                           for item in baseline_projections(historical_board["summaries"])}
        prop_codes = {"Points": "points", "Rebounds": "rebounds",
                      "Assists": "assists", "3-Pointers": "threes"}
        board["Historical baseline"] = [baseline_lookup.get((str(item.get("Player ID")), prop_codes[item["Prop"]]))
                                        for item in rows]
        board = board.sort_values(["Prop", "Historical baseline", "Player"], ascending=[True, False, True], na_position="last")
    if "Historical baseline" in board.columns:
        st.caption("Historical averages are ordered within each prop category, not across incomparable stats. This is not an OVER edge ranking.")
    st.dataframe(board.drop(columns=["Player ID"]), use_container_width=True, hide_index=True)
else:
    st.warning("No player listings available yet. Some box scores may not publish rosters before tipoff.")
if failures:
    with st.expander(f"NBA game feeds unavailable ({len(failures)})"):
        for failure in failures:
            st.write(failure)
st.caption("Historical baseline ordering is for research only, NOT an OVER ranking. FanDuel lines, probabilities and edges remain blank until sourced and validated.")
with st.expander("Model methodology and safeguards"):
    st.markdown("""
- Next: season and recent-game player statistics, minutes and roster coverage.
- Then: projections adjusted for role, matchup, pace and uncertainty.
- Only compute OVER probabilities after the projection model is validated.
- Only compare against timestamped, authorized sportsbook lines.
- Track outcomes, calibration and performance without look-ahead bias.
""")


st.subheader("Preliminary statistical baselines — not betting recommendations")
if historical:
    baseline_rows = baseline_projections(historical["summaries"], min_games=5)
    if baseline_rows:
        baseline_frame = pd.DataFrame(baseline_rows)
        st.caption("Blended completed-game averages only. No matchup adjustment, FanDuel lines, "
                   "validated OVER probabilities, or confidence tiers. "
                   "The sample may not cover the full season.")
        st.dataframe(baseline_frame.rename(columns={
            "player": "Player", "team": "Team", "prop": "Prop",
            "baseline": "Unadjusted baseline", "sample_games": "Valid games",
            "recent_minutes": "Last 5 avg minutes", "method": "Method"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No players have sufficient completed-game observations for baselines yet. "
                "Collect more historical games to build a reliable sample.")
