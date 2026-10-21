"""NBA Player Prop Model — live schedule and player feed preview."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st
from nba_data import NBADataError, scoreboard, game_players
from season_schedule import season_schedule, games_on
from espn_schedule import espn_games_on
from espn_players import espn_game_players, espn_team_roster
from espn_history import collect_espn_history, espn_final_game_players
from espn_averages import espn_player_averages
from espn_trends import espn_recent_trends
from espn_history_coverage import espn_history_coverage
from espn_board_quality import history_sample_status
from espn_history_health import espn_history_health
from csv_export import safe_spreadsheet_cell
from history_collection import recent_player_summaries, fetch_boxscore_players
from projection_baseline import baseline_projections
from pregame_results import score_pregame_baselines, summarize_projection_errors, projection_grading_coverage, summarize_projection_errors_by_slate, summarize_grading_by_slate, summarize_unmatched_forecasts_by_slate, list_unmatched_forecasts, summarize_unmatched_by_player
from pregame_roster import candidate_players
from matchup_validation import valid_game_player
from opponent_stats import opponent_game_totals, opponent_sample_summary
from roster_coverage import roster_coverage
from team_source_coverage import team_source_coverage
from history_quality import history_quality
from baseline_backtest import baseline_backtest

st.set_page_config(page_title="NBA Player Prop Model", page_icon="🏀", layout="wide")
st.title("🏀 NBA Player Prop Model")
st.caption("FanDuel-focused | Master board | NBA feed preview v0.2")
st.info("NBA schedule and available game-roster data are displayed below. Pregame projections and FanDuel odds are NOT connected. This is not a ranked betting board.")

@st.cache_data(ttl=300, show_spinner=False)
def load_games():
    return scoreboard()

@st.cache_data(ttl=300, show_spinner=False)
def load_espn_slate(day):
    return espn_games_on(day)

@st.cache_data(ttl=3600, show_spinner=False)
def load_espn_team_roster(team_id, code):
    return espn_team_roster(team_id, code)

@st.cache_data(ttl=900, show_spinner=False)
def load_espn_players(event_id):
    return espn_game_players(event_id)

@st.cache_data(ttl=900, show_spinner=False)
def load_players(game_id):
    return game_players(str(game_id))

st.caption("Live game information uses available NBA or ESPN feeds. "
           "Player statistics and projections have separate data requirements.")
try:
    games = load_games()
except NBADataError as exc:
    st.info("Official NBA live scoreboard is currently unavailable. "
            "The current-day section will use ESPN schedule and scores when available.")
    games = []

game_rows = []
for game in games:
    home = game.get("homeTeam")
    away = game.get("awayTeam")
    home = home if isinstance(home, dict) else {}
    away = away if isinstance(away, dict) else {}
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
    st.caption("Official NBA season schedule is unavailable; checking ESPN schedule fallback.")
    try:
        slate_games = load_espn_slate(slate_date.isoformat())
        st.info("Using ESPN schedule fallback for matchups, scores and tipoffs. "
                "ESPN event IDs are not NBA box-score IDs; historical player data "
                "must be loaded separately.")
    except NBADataError as backup_exc:
        st.error(str(backup_exc))
        slate_games = []
st.caption(f"{len(slate_games)} scheduled games for {slate_date}")
slate_rows = []
for scheduled in slate_games:
    home = scheduled.get("homeTeam")
    away = scheduled.get("awayTeam")
    home = home if isinstance(home, dict) else {}
    away = away if isinstance(away, dict) else {}
    slate_rows.append({
        "Game ID": str(scheduled.get("gameId") or ""),
        "ESPN Event ID": scheduled.get("espnEventId"),
        "ESPN Team IDs": scheduled.get("espnTeamIds") or {},
        "Matchup": f'{away.get("teamTricode", "?")} @ {home.get("teamTricode", "?")}',
        "Status": scheduled.get("gameStatusText") or "Scheduled",
        "Score": (f'{away["teamTricode"]} {scheduled["awayScore"]} - '
                  f'{home["teamTricode"]} {scheduled["homeScore"]}')
                 if isinstance(scheduled.get("awayScore"), int)
                 and isinstance(scheduled.get("homeScore"), int) else None,
        "Tipoff (UTC)": scheduled.get("gameTimeUTC") or "Not available",
    })
# Attach ESPN identifiers to NBA-scheduled matchups for independent player-feed fallback.
# Match only exact away/home tricodes; never substitute ESPN IDs for NBA IDs.
if slate_rows and any(row["Game ID"] for row in slate_rows):
    try:
        espn_matches = {}
        for event in load_espn_slate(slate_date.isoformat()):
            away = event["awayTeam"]["teamTricode"]
            home = event["homeTeam"]["teamTricode"]
            espn_matches[f"{away} @ {home}"] = event
        for row in slate_rows:
            match = espn_matches.get(row["Matchup"])
            if match:
                row["ESPN Event ID"] = match.get("espnEventId")
                row["ESPN Team IDs"] = match.get("espnTeamIds") or {}
    except NBADataError:
        pass

if slate_rows:
    st.dataframe(pd.DataFrame(slate_rows).drop(columns=["Game ID", "ESPN Event ID", "ESPN Team IDs"]),
                 use_container_width=True, hide_index=True)
else:
    st.info("No games listed for the selected date.")

st.subheader("Current-day NBA games")
if game_rows:
    st.dataframe(pd.DataFrame(game_rows).drop(columns=["Game ID"]), use_container_width=True, hide_index=True)
else:
    try:
        today_local = datetime.now(ZoneInfo("America/New_York")).date()
        fallback_today = load_espn_slate(today_local.isoformat())
        if fallback_today:
            fallback_rows = []
            for game in fallback_today:
                home = game["homeTeam"]["teamTricode"]
                away = game["awayTeam"]["teamTricode"]
                score = (f'{away} {game["awayScore"]} - {home} {game["homeScore"]}'
                         if isinstance(game.get("awayScore"), int)
                         and isinstance(game.get("homeScore"), int) else None)
                fallback_rows.append({"Matchup": f"{away} @ {home}",
                                      "Status": game["gameStatusText"],
                                      "Score": score,
                                      "Tipoff (UTC)": game["gameTimeUTC"]})
            st.info("Showing ESPN game schedule and scores for today. "
                    "Player statistics require the separate ESPN historical feed.")
            st.dataframe(pd.DataFrame(fallback_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No games returned by the NBA scoreboard or ESPN fallback today.")
    except NBADataError as exc:
        st.warning(f"Current-day NBA schedule unavailable from both feeds: {exc}")

st.subheader("ESPN completed-game statistics — experimental")
st.caption("Separate ESPN player IDs and verified final-game boxscores. "
           "These observations are descriptive and are not yet used in projections.")
@st.cache_data(ttl=3600, show_spinner=False)
def load_espn_history_schedule(day):
    return espn_games_on(day)


@st.cache_data(ttl=3600, show_spinner=False)
def load_espn_history_final(event_id):
    return espn_final_game_players(event_id)


@st.cache_data(ttl=3600, show_spinner=False)
def load_espn_history(as_of, days, max_games):
    return collect_espn_history(
        as_of, days=days, max_games=max_games,
        schedule_loader=load_espn_history_schedule,
        boxscore_loader=load_espn_history_final,
    )

history_days = st.select_slider("ESPN history lookback (days)", options=[3, 7, 14, 21, 30], value=14)
espn_game_budget = st.select_slider("ESPN historical game request limit", options=[5, 10, 20, 30, 50, 75, 100], value=50)
st.caption("Research history: defaults to 14 days / up to 50 verified final games. Larger samples make five-game player baselines more attainable but may load more slowly. ESPN request limit is shared across the entire slate, not per player.")
refresh_espn_history = st.button(
    "Refresh ESPN history from source",
    help="Clear cached ESPN historical schedules, final boxscores, and assembled samples "
         "before loading the selected slate again.",
)
load_espn_history_clicked = st.button("Load ESPN completed-game stats")
if load_espn_history_clicked or refresh_espn_history:
    # Clear stale samples before starting a new request, including failed ones.
    st.session_state.pop("espn_history_preview", None)
    st.session_state.pop("espn_history_parameters", None)
    st.session_state.pop("espn_history_error", None)
    st.session_state.pop("espn_history_error_parameters", None)
    st.session_state.pop("espn_history_loaded_at_utc", None)
    st.session_state.pop("espn_history_refresh_type", None)
    try:
        with st.spinner("Checking completed ESPN boxscores..."):
            if refresh_espn_history:
                load_espn_history.clear()
                load_espn_history_schedule.clear()
                load_espn_history_final.clear()
            espn_history = load_espn_history(slate_date.isoformat(), history_days, espn_game_budget)
    except (NBADataError, ValueError, TypeError, KeyError, OSError, requests.RequestException) as exc:
        st.session_state["espn_history_error"] = str(exc)
        st.session_state["espn_history_error_parameters"] = (
            slate_date.isoformat(), history_days, espn_game_budget)
    else:
        st.session_state["espn_history_preview"] = espn_history
        st.session_state["espn_history_parameters"] = (slate_date.isoformat(), history_days, espn_game_budget)
        st.session_state["espn_history_loaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        st.session_state["espn_history_refresh_type"] = (
            "Source refresh requested" if refresh_espn_history else "Standard load (cache eligible)"
        )
if (st.session_state.get("espn_history_error")
        and st.session_state.get("espn_history_error_parameters") == (
            slate_date.isoformat(), history_days, espn_game_budget)):
    st.error("ESPN history could not be loaded: "
             + st.session_state["espn_history_error"]
             + ". Previous historical values have been cleared.")
if st.session_state.get("espn_history_parameters") == (slate_date.isoformat(), history_days, espn_game_budget):
    espn_history = st.session_state.get("espn_history_preview")
    if espn_history:
        if st.session_state.get("espn_history_loaded_at_utc"):
            st.caption(
                "ESPN history last loaded: "
                + st.session_state["espn_history_loaded_at_utc"]
                + " UTC. Mode: "
                + st.session_state.get("espn_history_refresh_type", "Unknown")
                + ". Standard loads may reuse cached data; a source refresh clears "
                  "the historical caches before requesting the sample."
            )
        st.caption(f"Verified ESPN final games: {espn_history['games_loaded']} of "
                   f"{espn_history['games_requested']} requested across "
                   f"{espn_history.get('dates_checked', '?')} schedule dates checked; "
                   f"{len(espn_history['observations'])} player-game observations.")
        with st.expander("ESPN retrieval health"):
            st.caption("Final-game success covers only requested boxscores. Schedule coverage "
                       "measures checked dates, and a reached request limit means the "
                       "historical sample may exclude additional games.")
            health_export = pd.DataFrame([{
                "Slate date": slate_date.isoformat(),
                "History lookback days": history_days,
                "Historical game request limit": espn_game_budget,
                **espn_history_health(espn_history),
            }])
            st.dataframe(health_export, use_container_width=True, hide_index=True)
            health_export = health_export.copy()
            for column in health_export.select_dtypes(include=["object", "string"]).columns:
                health_export[column] = health_export[column].map(safe_spreadsheet_cell)
            st.download_button(
                "Download ESPN retrieval health CSV",
                data=health_export.to_csv(index=False).encode("utf-8"),
                file_name=f"espn_history_health_{slate_date.isoformat()}.csv",
                mime="text/csv",
                key="download_espn_history_health",
            )
            if espn_history["failures"]:
                st.caption("Failed schedule dates and boxscore validations are excluded "
                           "from verified historical statistics.")
                failure_rows = [
                    {
                        "Slate date": slate_date.isoformat(),
                        "History lookback days": history_days,
                        "Historical game request limit": espn_game_budget,
                        "Date": failure.get("date", "Unknown"),
                        "Stage": "Boxscore" if "event_id" in failure else "Schedule",
                        "ESPN Event ID": failure.get("event_id", ""),
                        "Reason": str(failure.get("error", "Unknown error"))[:240],
                    }
                    for failure in espn_history["failures"]
                ]
                st.dataframe(pd.DataFrame(failure_rows), use_container_width=True,
                             hide_index=True)
                failure_export = pd.DataFrame(failure_rows)
                for column in failure_export.select_dtypes(include=["object", "string"]).columns:
                    failure_export[column] = failure_export[column].map(safe_spreadsheet_cell)
                st.download_button(
                    "Download ESPN retrieval failures CSV",
                    data=failure_export.to_csv(index=False).encode("utf-8"),
                    file_name=f"espn_history_failures_{slate_date.isoformat()}.csv",
                    mime="text/csv",
                    key="download_espn_history_failures",
                )
        if any("event_id" not in failure for failure in espn_history["failures"]):
            st.warning(
                "One or more ESPN schedule dates failed to load. Even when every requested "
                "boxscore succeeded, historical averages may omit entire game dates."
            )
        if espn_history["games_loaded"] < espn_history["games_requested"]:
            st.warning("ESPN historical sample is incomplete. Do not interpret these averages "
                       "as full-season or last-N-game statistics.")
        omitted_games = espn_history.get("eligible_games_omitted", 0)
        if omitted_games:
            st.warning(
                f"ESPN history skipped {omitted_games} eligible scheduled game(s) "
                "because of the request limit. Increase the game-request limit "
                "for broader coverage; these averages are not full-season statistics."
            )
        elif espn_history.get("request_limit_reached", False):
            st.info("The ESPN request limit was reached, but no additional eligible "
                    "games were found in the scanned dates. This does not guarantee "
                    "complete historical coverage.")
        if espn_history["games_loaded"] > 0 and espn_history["games_loaded"] < 10:
            st.caption("Small verified sample: fewer than 10 completed games loaded "
                       "across the entire requested lookback. Individual player "
                       "averages may be based on even fewer games.")
        if espn_history["failures"]:
            st.warning(f"{len(espn_history['failures'])} schedule or boxscore requests failed validation.")
            with st.expander("ESPN historical data errors"):
                st.dataframe(pd.DataFrame(espn_history["failures"]), use_container_width=True, hide_index=True)
        if not espn_history["observations"]:
            st.warning("No verified ESPN player-game statistics were retrieved. "
                       "Historical averages and L5/L10 trends will remain unavailable; "
                       "this does not mean players recorded zero stats.")
        if espn_history["observations"]:
            scheduled_espn_teams = {
                str(game[side]["teamTricode"])
                for game in slate_games for side in ("homeTeam", "awayTeam")
                if isinstance(game.get(side), dict) and game[side].get("teamTricode")
            }
            if scheduled_espn_teams:
                with st.expander("Historical sample coverage for today's teams"):
                    st.caption("Counts are distinct ESPN player-game records in the selected "
                               "lookback, not verified active players or complete season samples.")
                    st.dataframe(pd.DataFrame(espn_history_coverage(
                        espn_history["observations"], scheduled_espn_teams)),
                        use_container_width=True, hide_index=True)
            averages = espn_player_averages(espn_history["observations"], slate_date.isoformat())
            if averages:
                st.caption("ESPN historical averages: descriptive only, based on the limited "
                           "verified sample below. Not calibrated betting projections.")
                st.dataframe(pd.DataFrame(averages).drop(columns=["Player ID"]),
                             use_container_width=True, hide_index=True)
            # ESPN observations remain in their own athlete-ID namespace.
            # Forecasts are date-frozen and never use games on the slate date.
            from pregame_baseline_board import build_pregame_baseline_board
            espn_forecasts = build_pregame_baseline_board(
                espn_history["observations"], slate_date.isoformat(), min_games=5
            )
            if espn_forecasts:
                st.subheader("ESPN pregame baseline projections — research")
                st.caption(f"Eligible player-prop baselines: {len(espn_forecasts)} across "
                           f"{len({row['player_id'] for row in espn_forecasts})} unique players.")
                if espn_history.get("history_truncated"):
                    st.warning("Historical request limit omitted eligible games. These "
                               "baselines may not reflect each player's full recent sample.")
                if espn_history.get("failures"):
                    st.warning("Some ESPN schedule or final-boxscore requests failed. "
                               "Review ESPN retrieval health before relying on these baselines.")
                st.caption("Automatically generated from verified ESPN final-game samples "
                           "strictly before the slate date. These are unadjusted statistical "
                           "forecasts, not FanDuel lines or betting probabilities. "
                           "The selected lookback may omit player games.")
                forecast_frame = pd.DataFrame(espn_forecasts)
                display_fields = ["player", "team", "prop", "baseline",
                                  "sample_games", "history_coverage", "research_readiness", "recent_minutes",
                                  "last_game_date", "days_since_last_game", "slate_date"]
                st.dataframe(forecast_frame[
                    [col for col in display_fields if col in forecast_frame.columns]
                ], use_container_width=True, hide_index=True)
                forecast_export = forecast_frame.copy()
                for column in forecast_export.select_dtypes(include=["object", "string"]).columns:
                    forecast_export[column] = forecast_export[column].map(safe_spreadsheet_cell)
                st.download_button(
                    "Download ESPN research baselines CSV",
                    data=forecast_export.to_csv(index=False),
                    file_name=f"espn_research_baselines_{slate_date.isoformat()}.csv",
                    mime="text/csv",
                    help="Date-frozen, unadjusted research projections only; no sportsbook lines or calibrated probabilities.",
                )
            else:
                st.info("No ESPN players meet the five-game minimum for automatic "
                        "pregame baseline projections in this historical sample.")
                st.caption("To improve coverage, increase the ESPN history lookback and "
                           "historical game request limit above, then reload completed-game "
                           "stats. A new season or sparse completed-game history may still "
                           "leave players ineligible.")
                if espn_history.get("history_truncated"):
                    st.warning("The historical request cap omitted eligible games; "
                               "increase the limit to collect a broader player sample.")
                if espn_history.get("failures"):
                    st.warning("Some historical requests failed. Review ESPN retrieval "
                               "health for missing dates or boxscores.")
            with st.expander("Grade saved research baselines against loaded verified finals"):
                st.caption("Upload a previously saved ESPN research baselines CSV. "
                           "Only matching verified final player-games already present "
                           "in the loaded ESPN history sample can be graded; "
                           "unmatched forecasts remain ungraded.")
                uploaded_baselines = st.file_uploader(
                    "Saved ESPN research baselines CSV",
                    type=["csv"], key="espn_baseline_results_upload")
                if uploaded_baselines is not None:
                    try:
                        saved = pd.read_csv(uploaded_baselines, dtype={"player_id": str, "slate_date": str})
                        required = {"player_id", "slate_date", "prop", "baseline"}
                        if not required.issubset(saved.columns):
                            st.error("CSV missing required fields: " +
                                     ", ".join(sorted(required - set(saved.columns))))
                        else:
                            graded = score_pregame_baselines(
                                saved.to_dict("records"), espn_history["observations"])
                            coverage = projection_grading_coverage(
                                saved.to_dict("records"), graded)
                            st.caption(
                                f"Grading coverage: {coverage['graded_forecasts']} of "
                                f"{coverage['eligible_forecasts']} eligible forecasts "
                                f"({coverage['grading_coverage_pct']}%). "
                                f"Unmatched: {coverage['unmatched_forecasts']}."
                                if coverage["grading_coverage_pct"] is not None
                                else "No eligible forecasts found in the uploaded CSV."
                            )
                            if coverage["unmatched_forecasts"]:
                                with st.expander("Unmatched projections by slate and prop"):
                                    st.caption("These projections are ungraded, not recorded as misses.")
                                    missing_breakdown = pd.DataFrame(
                                        summarize_unmatched_forecasts_by_slate(
                                            saved.to_dict("records"), graded))
                                    st.dataframe(missing_breakdown,
                                                 use_container_width=True, hide_index=True)
                                    st.download_button(
                                        "Download unmatched breakdown CSV",
                                        data=missing_breakdown.to_csv(index=False),
                                        file_name=f"nba_unmatched_projections_{slate_date.isoformat()}.csv",
                                        mime="text/csv",
                                    )
                            if coverage["unmatched_forecasts"]:
                                with st.expander("Individual unmatched player projections"):
                                    unmatched_players = pd.DataFrame(
                                        list_unmatched_forecasts(saved.to_dict("records"), graded))
                                    st.caption("Ungraded projections only; missing finals are not losses.")
                                    st.dataframe(unmatched_players,
                                                 use_container_width=True, hide_index=True)
                                    st.download_button(
                                        "Download unmatched player projections CSV",
                                        data=unmatched_players.to_csv(index=False),
                                        file_name=f"nba_unmatched_players_{slate_date.isoformat()}.csv",
                                        mime="text/csv",
                                    )
                            if coverage["unmatched_forecasts"]:
                                with st.expander("Unmatched forecast counts by player"):
                                    player_coverage = pd.DataFrame(
                                        summarize_unmatched_by_player(saved.to_dict("records"), graded))
                                    st.caption("Players with the most ungraded saved projections appear first.")
                                    st.dataframe(player_coverage,
                                                 use_container_width=True, hide_index=True)
                                    st.download_button(
                                        "Download unmatched counts by player CSV",
                                        data=player_coverage.to_csv(index=False),
                                        file_name=f"nba_unmatched_by_player_{slate_date.isoformat()}.csv",
                                        mime="text/csv",
                                    )
                            if coverage["unmatched_forecasts"]:
                                st.info(
                                    f"{coverage['unmatched_forecasts']} eligible projections "
                                    "have no verified final match in the loaded history. "
                                    "To grade more, select an as-of date after those games "
                                    "and reload ESPN completed-game history."
                                )
                            if coverage["eligible_forecasts"]:
                                st.progress(coverage["graded_forecasts"] /
                                            coverage["eligible_forecasts"],
                                            text="Verified results coverage")
                            with st.expander("Grading coverage by slate date"):
                                st.caption("Unmatched forecasts indicate missing verified finals, "
                                           "not automatically incorrect predictions.")
                                slate_coverage = pd.DataFrame(
                                    summarize_grading_by_slate(saved.to_dict("records"), graded))
                                st.dataframe(slate_coverage,
                                             use_container_width=True, hide_index=True)
                                st.download_button(
                                    "Download per-slate grading coverage CSV",
                                    data=slate_coverage.to_csv(index=False),
                                    file_name=f"nba_slate_grading_coverage_{slate_date.isoformat()}.csv",
                                    mime="text/csv",
                                )
                            if graded:
                                st.dataframe(pd.DataFrame(graded)[
                                    ["player", "team", "slate_date", "prop", "baseline",
                                     "actual", "projection_error", "absolute_error"]
                                ], use_container_width=True, hide_index=True)
                                prop_accuracy = pd.DataFrame(summarize_projection_errors(graded))
                                st.dataframe(prop_accuracy,
                                             use_container_width=True, hide_index=True)
                                st.download_button(
                                    "Download overall prop accuracy CSV",
                                    data=prop_accuracy.to_csv(index=False),
                                    file_name=f"nba_prop_accuracy_{slate_date.isoformat()}.csv",
                                    mime="text/csv",
                                    help="Per-prop MAE and bias from matched verified final results only.",
                                )
                                with st.expander("Accuracy by slate date"):
                                    st.caption("Per-slate errors use only verified matched finals. "
                                               "Low sample counts may be unstable.")
                                    slate_accuracy = pd.DataFrame(
                                        summarize_projection_errors_by_slate(graded))
                                    st.dataframe(slate_accuracy,
                                                 use_container_width=True, hide_index=True)
                                    st.download_button(
                                        "Download per-slate accuracy CSV",
                                        data=slate_accuracy.to_csv(index=False),
                                        file_name=f"nba_per_slate_projection_accuracy_{slate_date.isoformat()}.csv",
                                        mime="text/csv",
                                        help="Verified matched forecasts only; includes sample counts, MAE, and bias.",
                                    )
                                graded_export = pd.DataFrame(graded).copy()
                                for column in graded_export.select_dtypes(include=["object", "string"]).columns:
                                    graded_export[column] = graded_export[column].map(safe_spreadsheet_cell)
                                st.download_button(
                                    "Download verified projection results CSV",
                                    data=graded_export.to_csv(index=False),
                                    file_name=f"nba_verified_projection_results_{slate_date.isoformat()}.csv",
                                    mime="text/csv",
                                    help="Exports only matched verified finals and their projection errors.",
                                )
                                st.caption(f"Graded {len(graded)} of {len(saved)} saved prop rows. "
                                           "MAE and bias describe this matched sample only.")
                            else:
                                st.info("No verified matching final player-games in the "
                                        "currently loaded history sample. Select a later "
                                        "as-of slate date and load the relevant finals.")
                    except (ValueError, TypeError, KeyError, UnicodeError, pd.errors.ParserError) as exc:
                        st.error(f"Could not grade the uploaded research CSV: {exc}")
            trends = espn_recent_trends(espn_history["observations"], slate_date.isoformat())
            if trends:
                st.caption("ESPN L5/L10: averages use up to 5 or 10 verified games available "
                           "in this limited lookback. They are not guaranteed complete "
                           "last-5 or last-10 NBA game samples.")
                with st.expander("ESPN recent player trends (verified sample)"):
                    names = {
                        (row["player_id"], row["team"]): row["player"]
                        for row in espn_history["observations"]
                        if isinstance(row, dict) and all(
                            key in row for key in ("player_id", "team", "player"))
                    }
                    trend_rows = [
                        {"Player": names.get(key, key[0]), "Team": key[1], **values}
                        for key, values in sorted(trends.items())
                    ]
                    st.dataframe(pd.DataFrame(trend_rows),
                                 use_container_width=True, hide_index=True)
            with st.expander("Individual verified ESPN player-game observations"):
                observation_frame = pd.DataFrame(espn_history["observations"])
                st.dataframe(observation_frame, use_container_width=True, hide_index=True)
                # The raw verified sample is useful for auditing individual
                # averages. It is not a full-season archive or a betting feed.
                export_observations = observation_frame.copy()
                for column in export_observations.select_dtypes(include=["object", "str"]).columns:
                    export_observations[column] = export_observations[column].map(safe_spreadsheet_cell)
                export_observations.insert(0, "Research Status", "VERIFIED SAMPLE — NOT COMPLETE HISTORY")
                st.download_button(
                    "Download verified ESPN player-game sample (CSV)",
                    data=export_observations.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"espn_verified_sample_{slate_date.isoformat()}.csv",
                    mime="text/csv",
                    help="Includes only validated final-game observations actually retrieved "
                         "within the selected lookback and game-request limit.",
                )

st.subheader("Historical player statistics — research preview")
st.caption("Official completed-game box scores only. These are descriptive averages, not predictions or betting edges.")
@st.cache_data(ttl=86400, show_spinner=False)
def load_final_boxscore(game_id):
    return fetch_boxscore_players(game_id)

@st.cache_data(ttl=3600, show_spinner=False)
def load_historical_summary(as_of, game_limit):
    return recent_player_summaries(load_schedule(), as_of=as_of,
                                   max_games=game_limit, loader=load_final_boxscore)

@st.cache_data(ttl=3600, show_spinner=False)
def load_baseline_backtest(observations, as_of):
    return baseline_backtest(observations, as_of)

if st.button("Refresh NBA feeds and cached history"):
    load_games.clear()
    load_espn_slate.clear()
    load_espn_players.clear()
    load_espn_team_roster.clear()
    load_espn_history.clear()
    load_espn_history_schedule.clear()
    load_espn_history_final.clear()
    st.session_state.pop('espn_history_preview', None)
    st.session_state.pop('espn_history_parameters', None)
    load_players.clear()
    load_schedule.clear()
    load_final_boxscore.clear()
    load_historical_summary.clear()
    load_baseline_backtest.clear()
    st.session_state.pop("nba_historical_preview", None)
    st.session_state.pop("nba_historical_preview_date", None)
    st.session_state.pop("nba_historical_preview_limit", None)
    st.rerun()

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
        st.info("Historical box scores still require access to the official NBA CDN. "
                "The ESPN schedule fallback does not supply verified NBA game IDs "
                "or historical player observations.")

historical = st.session_state.get("nba_historical_preview")
if (st.session_state.get("nba_historical_preview_date") != slate_date.isoformat() or
        st.session_state.get("nba_historical_preview_limit") != history_limit):
    historical = None
if historical:
    st.caption(f"Historical sample as of {st.session_state.get('nba_historical_preview_date')}: "
               f"{historical['games_loaded']} of {historical['games_requested']} requested games loaded "
               f"({historical['eligible_games']} eligible games in schedule). "
               "Season averages cover only the collected sample, not necessarily the full season.")
    if historical["games_loaded"] < historical["games_requested"]:
        st.warning("Historical sample is incomplete: some requested final box scores were unavailable. "
                   "Baselines and backtests may be biased toward successfully loaded games.")
    quality = history_quality(historical.get("observations", []), slate_date)
    with st.expander("Historical sample quality"):
        st.caption("Counts describe only the collected box scores. They do not prove full-season coverage or predict outcomes.")
        st.dataframe(pd.DataFrame([quality]), use_container_width=True, hide_index=True)
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


st.subheader("Walk-forward baseline accuracy — historical research")
if historical and historical.get("observations"):
    backtest_rows = load_baseline_backtest(historical["observations"], slate_date.isoformat())
    st.caption("Evaluates unadjusted baseline predictions using only prior-day observations. "
               "MAE is average absolute error; RMSE emphasizes larger misses; signed error is prediction minus actual. "
               "Coverage uses all eligible appearances, including early games before sufficient training history exists. Invalid, duplicate, and on-or-after-cutoff observations are counted separately. "
               "This is NOT sportsbook profitability or calibrated OVER probability.")
    if any(item["evaluated"] for item in backtest_rows):
        st.dataframe(pd.DataFrame(backtest_rows), use_container_width=True, hide_index=True)
        st.caption("Players evaluated counts distinct player IDs; evaluated counts individual game predictions. Dates evaluated and the first/last dates show the tested time span. Small samples are not reliable evidence of predictive accuracy.")
    else:
        st.info("Not enough prior player appearances to calculate a walk-forward accuracy sample.")
else:
    st.caption("Load historical player averages to inspect retrospective baseline accuracy.")

st.subheader("Opponent production allowed — historical research")
if historical and historical.get("observations"):
    opponent_rows = opponent_game_totals(historical["observations"], slate_date)
    if opponent_rows:
        st.caption("Observed player totals from collected final box scores, not verified complete-team defensive totals. No matchup adjustment is applied.")
        opponent_averages = opponent_sample_summary(opponent_rows)
        if opponent_averages:
            st.caption("Screened historical opponent averages (at least 8 observed players per game). Sample sizes are shown; these are not calibrated defensive ratings.")
            st.dataframe(pd.DataFrame(opponent_averages), use_container_width=True, hide_index=True)
        else:
            st.warning("No opponent games passed the minimum player-coverage screen.")
        with st.expander("Individual opponent game observations"):
            st.dataframe(pd.DataFrame(opponent_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No valid opponent observations in the selected historical sample.")
else:
    st.caption("Load historical player averages to inspect descriptive opponent totals.")

st.subheader("Master Player Prop Board — data preview")
categories = ["Points", "Rebounds", "Assists", "3-Pointers"]
selected = st.multiselect("Prop categories", categories, default=categories)
columns = ["Game", "Player", "Player ID", "Team", "Opponent", "Roster Source", "Last Seen", "Prop", "FanDuel Line", "Over Odds", "Projection", "Over Probability", "Edge", "Confidence"]
rows = []
roster_listings = []
failures = []
for game in slate_rows:
    source = "NBA game feed"
    players = []
    if game["Game ID"]:
        try:
            players = load_players(game["Game ID"])
        except NBADataError as exc:
            failures.append(f'{game["Matchup"]}: NBA player feed unavailable ({exc}); trying ESPN fallback')
    # A pregame NBA boxscore can list only one team. Supplement missing
    # teams without replacing valid NBA athletes or mixing ID namespaces.
    matchup = game["Matchup"].split(" @ ")
    missing_teams = (set(matchup) - {p.get("team") for p in players
                                      if isinstance(p, dict) and
                                      (p.get("source") != "NBA game feed" or
                                       valid_game_player(p, game["Matchup"]))}
                     if len(matchup) == 2 else set())
    if missing_teams and (game.get("ESPN Event ID") or game.get("ESPN Team IDs")):
        fallback_players = []
        if game.get("ESPN Event ID"):
            try:
                fallback_players = load_espn_players(game["ESPN Event ID"])
            except NBADataError:
                pass
        for side, team_code in (("away", matchup[0]), ("home", matchup[1])):
            if team_code not in missing_teams:
                continue
            team_id = (game.get("ESPN Team IDs") or {}).get(side)
            if team_id:
                try:
                    fallback_players.extend(load_espn_team_roster(team_id, team_code))
                except NBADataError as roster_exc:
                    failures.append(f'{team_code}: {roster_exc}')
        players.extend(p for p in fallback_players if p.get("team") in missing_teams)
    if not players:
        failures.append(f'{game["Matchup"]}: No player listings available from connected providers')
    # Deduplicate across game-summary and team-roster sources by namespaced ID.
    # Prefer game-summary records when the same athlete appears twice.
    deduped = {}
    for player in players:
        key = (str(player.get("player_id")), player.get("team"))
        if key not in deduped:
            deduped[key] = player
    players = list(deduped.values())
    for player in players:
        if player.get("source", source) == "NBA game feed":
            if not valid_game_player(player, game["Matchup"]):
                continue
        else:
            teams = game["Matchup"].split(" @ ")
            if len(teams) != 2 or player.get("team") not in teams:
                continue
            player["opponent"] = teams[0] if player["team"] == teams[1] else teams[1]
        player_source = player.get("source", source)
        roster_listings.append({"player_id": player.get("player_id"), "team": player.get("team"), "source": player_source})
        for prop in selected:
            rows.append({
                "Game": game["Matchup"],
                "Player": player["player"],
                "Player ID": player.get("player_id"),
                "Team": player.get("team"),
                "Opponent": player.get("opponent"),
                "Roster Source": player_source,
                "Last Seen": None,
                "Prop": prop,
                "FanDuel Line": None,
                "Over Odds": None,
                "Projection": None,
                "Over Probability": None,
                "Edge": None,
                "Confidence": "Unconfirmed ESPN listing" if player_source != "NBA game feed" else "Not calculated",
            })
history_for_slate = st.session_state.get("nba_historical_preview")
if (st.session_state.get("nba_historical_preview_date") != slate_date.isoformat() or
        st.session_state.get("nba_historical_preview_limit") != history_limit):
    history_for_slate = None
if history_for_slate and history_for_slate.get("summaries"):
    candidates = candidate_players(slate_games, history_for_slate["summaries"], slate_date)
    known = {(str(item["player_id"]), item["team"]) for item in roster_listings}
    for candidate in candidates:
        key = (str(candidate["player_id"]), candidate["team"])
        if key in known:
            continue
        for game in slate_rows:
            teams = game["Matchup"].split(" @ ")
            if candidate["team"] not in teams:
                continue
            opponent = teams[0] if candidate["team"] == teams[1] else teams[1]
            roster_listings.append({"player_id": candidate["player_id"], "team": candidate["team"], "source": "Historical candidate"})
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
# Data-quality diagnostics: expose incomplete roster coverage instead of
# presenting a partial slate as if every team were represented.
slate_teams = {str(game[side]["teamTricode"])
               for game in slate_games for side in ("homeTeam", "awayTeam")
               if isinstance(game.get(side), dict) and game[side].get("teamTricode")}
coverage = roster_coverage(roster_listings, slate_teams)
if not selected:
    st.info("Select at least one prop category to populate the master board.")
if coverage["missing_teams"]:
    st.warning("No players available for scheduled teams: " + ", ".join(coverage["missing_teams"]) +
               ". The master board is incomplete; do not interpret missing players as inactive.")
elif slate_teams:
    st.caption("Every scheduled team has at least one listed player. This does NOT verify full rosters.")
if roster_listings:
    st.caption(f"Roster coverage: {coverage['represented_teams']}/{coverage['scheduled_teams']} scheduled teams; "
               f"{coverage['players']} unique player/team listings "
               f"({coverage['feed_players']} from NBA feeds or ESPN listings (ESPN unconfirmed), "
               f"{coverage['historical_candidates']} historical candidates).")
if slate_teams:
    with st.expander("Team-by-team roster coverage and data sources"):
        st.caption("These are unique candidate listings, not confirmed active players. "
                   "Zero listings may indicate a provider outage or an unpublished roster.")
        st.dataframe(pd.DataFrame(team_source_coverage(roster_listings, slate_teams)),
                     use_container_width=True, hide_index=True)
board = pd.DataFrame(rows, columns=columns)
if not board.empty:
    # Join ESPN descriptive stats by exact namespaced athlete ID and team.
    # Never treat them as model projections or merge ESPN IDs with NBA IDs.
    espn_history_board = st.session_state.get("espn_history_preview")
    if st.session_state.get("espn_history_parameters") != (
            slate_date.isoformat(), history_days, espn_game_budget):
        espn_history_board = None
    if espn_history_board and espn_history_board.get("observations"):
        averages = espn_player_averages(espn_history_board["observations"], slate_date.isoformat())
        average_lookup = {(item["Player ID"], item["Team"]): item for item in averages}
        board["ESPN Latest Verified Game"] = [
            average_lookup.get((str(row["Player ID"]), row["Team"]), {}).get(
                "Latest verified game")
            for _, row in board.iterrows()
        ]
        board["ESPN Days Since Sample"] = [
            (slate_date - date.fromisoformat(played)).days if played else None
            for played in board["ESPN Latest Verified Game"]
        ]
        prop_avg = {"Points": "Points avg", "Rebounds": "Rebounds avg",
                    "Assists": "Assists avg", "3-Pointers": "Threes avg"}
        board["ESPN Sample Games"] = [
            average_lookup.get((str(row["Player ID"]), row["Team"]), {}).get("Sample games")
            for _, row in board.iterrows()
        ]
        board["ESPN Historical Avg"] = [
            average_lookup.get((str(row["Player ID"]), row["Team"]), {}).get(prop_avg[row["Prop"]])
            for _, row in board.iterrows()
        ]
        trends = espn_recent_trends(espn_history_board["observations"], slate_date.isoformat())
        prop_key = {"Points": "points", "Rebounds": "rebounds",
                    "Assists": "assists", "3-Pointers": "threes"}
        for n in (5, 10):
            board[f"ESPN L{n} Avg"] = [
                trends.get((str(row["Player ID"]), row["Team"]), {}).get(
                    f"{prop_key[row['Prop']]} L{n} avg")
                for _, row in board.iterrows()
            ]
            board[f"ESPN L{n} Games"] = [
                trends.get((str(row["Player ID"]), row["Team"]), {}).get(
                    f"Available last {n} games")
                for _, row in board.iterrows()
            ]
        board["ESPN History Status"] = [
            history_sample_status(row["ESPN Sample Games"],
                                  row["ESPN L5 Games"], row["ESPN L10 Games"])
            for _, row in board.iterrows()
        ]
        st.caption("ESPN History Status describes verified sample size only; "
                   "it is not a betting tier or confidence prediction.")
        st.caption("ESPN historical and L5/L10 averages use available verified pre-slate games (sample counts shown), not a "
                   "betting projection. ESPN Latest Verified Game and ESPN Days Since Sample "
                   "describe the age of the most recent sampled observation, not proof "
                   "of full-season coverage. Missing values indicate unavailable matched history.")
        # Make missing ESPN history visible by prop; a roster listing alone
        # does not establish any verified completed-game observations.
        espn_coverage = board.groupby("Prop", sort=False).agg(
            listed=("Player", "size"),
            with_history=("ESPN Historical Avg", lambda values: int(values.notna().sum())),
            with_five_games=("ESPN L5 Games", lambda values: int((values >= 5).sum())),
            with_ten_games=("ESPN L10 Games", lambda values: int((values >= 10).sum())),
        ).reset_index()
        espn_coverage["History coverage %"] = (
            100 * espn_coverage["with_history"] / espn_coverage["listed"]
        ).round(1)
        with st.expander("ESPN historical coverage by prop"):
            st.caption("Counts refer to listed player-prop rows with matching ESPN IDs and "
                       "verified final-game history, not confirmed active players.")
            st.dataframe(espn_coverage.rename(columns={
                "listed": "Listed player-props",
                "with_history": "With verified history",
                "with_five_games": "At least 5 games",
                "with_ten_games": "At least 10 games",
            }), use_container_width=True, hide_index=True)
            sample_age = pd.to_numeric(board["ESPN Days Since Sample"], errors="coerce")
            st.caption("Sample freshness across listed player-prop rows. Missing observations "
                       "are counted separately rather than treated as recent or zero.")
            st.dataframe(pd.DataFrame([{
                "Listed player-props": len(board),
                "Sample within 7 days": int(sample_age.between(0, 7).sum()),
                "Sample within 14 days": int(sample_age.between(0, 14).sum()),
                "Sample within 30 days": int(sample_age.between(0, 30).sum()),
                "Older than 30 days": int(sample_age.gt(30).sum()),
                "No verified sample": int(sample_age.isna().sum()),
            }]), use_container_width=True, hide_index=True)
        if board["ESPN Historical Avg"].isna().any():
            st.warning("Some player-prop rows have no verified matching ESPN history. "
                       "Blank averages are unavailable data, not zero performance.")

    st.caption(f"{board['Player'].nunique()} players from available game feeds or historical candidates. Roster Source and Last Seen show where each listing came from; availability is not verified.")
    historical_board = st.session_state.get("nba_historical_preview")
    if (st.session_state.get("nba_historical_preview_date") != slate_date.isoformat() or
        st.session_state.get("nba_historical_preview_limit") != history_limit):
        historical_board = None
    if historical_board and historical_board.get("summaries"):
        baseline_lookup = {(str(item["player_id"]), item["team"], item["prop"]): item["baseline"]
                           for item in baseline_projections(historical_board["summaries"])}
        prop_codes = {"Points": "points", "Rebounds": "rebounds",
                      "Assists": "assists", "3-Pointers": "threes"}
        board["Historical baseline"] = [baseline_lookup.get((str(item.get("Player ID")), item.get("Team"), prop_codes[item["Prop"]]))
                                        for item in rows]
        usable = board.groupby("Prop", sort=False)["Historical baseline"].agg(
            listed="size", baselines=lambda values: int(values.notna().sum()))
        usable["Coverage %"] = (100 * usable["baselines"] / usable["listed"]).round(1)
        st.caption("Baseline availability by prop (listed players are not confirmed active; "
                   "historical baselines require a matching current team):")
        st.dataframe(usable.reset_index().rename(columns={
            "Prop": "Prop", "listed": "Listed players", "baselines": "Usable baselines"
        }), use_container_width=True, hide_index=True)
        if board["Historical baseline"].isna().any():
            st.warning("Some listed players lack a matching-team historical baseline or sufficient "
                       "valid observations. Missing baselines are not zero projections.")
        board = board.sort_values(["Prop", "Historical baseline", "Player"], ascending=[True, False, True], na_position="last")
    if "Historical baseline" in board.columns:
        st.caption("Historical averages are ordered within each prop category, not across incomparable stats. This is not an OVER edge ranking.")
    # Research-only filtering: do not infer missing samples as zero or alter
    # projections, betting probabilities, or the underlying player ranking.
    visible_board = board
    if "ESPN Sample Games" in board.columns:
        min_verified_games = st.select_slider(
            "Minimum verified ESPN games (research view)",
            options=[0, 1, 3, 5, 10],
            value=0,
            help="0 shows every listed player. Higher values hide rows without enough "
                 "matching verified ESPN final-game observations.",
        )
        if min_verified_games:
            visible_board = board.loc[
                pd.to_numeric(board["ESPN Sample Games"], errors="coerce")
                .fillna(0).ge(min_verified_games)
            ]
            st.caption(
                f"Showing {len(visible_board)} of {len(board)} player-prop rows with "
                f"at least {min_verified_games} verified ESPN games. "
                "This is a sample-size filter, not a betting recommendation."
            )
            if visible_board.empty:
                st.warning("No player-prop rows meet the selected historical sample minimum. "
                           "Reduce the filter to view more players.")
    if "ESPN Days Since Sample" in board.columns:
        max_sample_age = st.select_slider(
            "Maximum ESPN sample age (research view)",
            options=["Any age", "7 days", "14 days", "30 days"],
            value="Any age",
            help="Optional research-only filter based on the latest verified sampled game. "
                 "Players without a matching sample are hidden when an age limit is selected.",
        )
        if max_sample_age != "Any age":
            max_days = int(max_sample_age.split()[0])
            sample_age = pd.to_numeric(
                visible_board["ESPN Days Since Sample"], errors="coerce"
            )
            visible_board = visible_board.loc[sample_age.between(0, max_days)]
            st.caption(
                f"Showing {len(visible_board)} of {len(board)} player-prop rows "
                f"with a verified ESPN sample no older than {max_days} days. "
                "Any minimum-game filter also applies. This does not alter projections."
            )
            if visible_board.empty:
                st.warning("No player-prop rows meet the selected sample-age and "
                           "sample-size filters. Widen either filter to see more players.")
    st.dataframe(visible_board.drop(columns=["Player ID"]), use_container_width=True, hide_index=True)
    # Export only the currently visible research rows, preserving missing
    # betting fields as blanks rather than inventing lines or probabilities.
    if not visible_board.empty:
        export_board = visible_board.copy()
        for column in export_board.select_dtypes(include=["object", "str"]).columns:
            export_board[column] = export_board[column].map(safe_spreadsheet_cell)
        export_board.insert(0, "Research Status", "UNCONFIRMED — NOT A BETTING BOARD")
        st.download_button(
            "Download filtered NBA research board (CSV)",
            data=export_board.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"nba_research_board_{slate_date.isoformat()}.csv",
            mime="text/csv",
            help="Exports current filters and available source data. Empty odds, "
                 "projections and probabilities remain empty.",
        )
else:
    if selected:
        st.warning("No player listings available yet. Some box scores may not publish rosters before tipoff.")
    else:
        st.caption("Master board hidden because no prop categories are selected.")
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


st.divider()
st.subheader("Capture a pregame prediction — manual research")
st.caption("This form records a supplied research probability and line; it does not generate "
           "a model forecast or fetch sportsbook odds. Saved files are local to this app "
           "instance and may disappear on redeployment.")
with st.expander("Save a pre-tipoff NBA prediction"):
    with st.form("capture_pregame_form"):
        capture_game = st.text_input("NBA game ID (numeric)", key="capture_game_id")
        capture_player = st.text_input("NBA player ID (numeric)", key="capture_player_id")
        capture_prop = st.selectbox("Prop", ["points", "rebounds", "assists", "threes"],
                                    key="capture_prop")
        capture_line = st.number_input("Prop line", min_value=0.0, value=20.5,
                                       step=0.5, key="capture_line")
        capture_probability = st.number_input("Research OVER probability (0–1)",
                                               min_value=0.0, max_value=1.0,
                                               value=0.5, step=0.01,
                                               key="capture_probability")
        capture_tipoff = st.text_input("Tipoff timestamp (ISO 8601 with timezone)",
                                       placeholder="2026-10-22T23:30:00Z",
                                       key="capture_tipoff")
        capture_source = st.text_input("Line/probability source",
                                       value="manual research", key="capture_source")
        capture_submit = st.form_submit_button("Save pregame prediction")
    if capture_submit:
        try:
            from pregame_capture import capture_pregame_prediction
            capture_result = capture_pregame_prediction({
                "game_id": capture_game.strip(), "player_id": capture_player.strip(),
                "prop": capture_prop, "line": float(capture_line),
                "over_probability": float(capture_probability),
                "tipoff_at": capture_tipoff.strip(), "source": capture_source.strip(),
            }, "pregame_snapshots")
            if capture_result["created"]:
                st.success("Pregame prediction saved with server capture time.")
            else:
                st.info("This game/player/prop/line already has a saved prediction; "
                        "the original was preserved.")
        except (ValueError, TypeError, OSError) as exc:
            st.error(f"Could not save pregame prediction: {exc}")
    from snapshot_storage import load_snapshots
    saved_capture_data = load_snapshots("pregame_snapshots")
    st.caption(f"Locally saved predictions: {len(saved_capture_data['snapshots'])}; "
               f"invalid files: {len(saved_capture_data['invalid_files'])}.")
    if saved_capture_data["snapshots"]:
        import json
        st.download_button(
            "Export locally saved predictions (JSON)",
            data=json.dumps(saved_capture_data["snapshots"], indent=2),
            file_name="nba_pregame_snapshots.json",
            mime="application/json", key="capture_export_json"
        )

st.subheader("Pregame prediction tracking — research preview")
st.caption("Upload previously captured pre-tipoff prediction snapshots and verified final NBA player "
           "statistics as JSON arrays, or refresh final NBA box scores for uploaded snapshots. "
           "Predictions are not captured automatically and uploaded timestamps are not independently "
           "authenticated. ESPN IDs cannot be matched to NBA IDs.")
with st.expander("Evaluate saved predictions against final box scores"):
    snapshot_upload = st.file_uploader(
        "Pregame snapshot JSON (array)", type=["json"], key="tracker_snapshots"
    )
    finals_upload = st.file_uploader(
        "Final NBA player statistics JSON (array)", type=["json"], key="tracker_finals"
    )
    minimum_tracked_samples = st.number_input(
        "Minimum observations for probability accuracy", min_value=2,
        max_value=10000, value=30, step=1, key="tracker_min_samples"
    )
    # A new upload invalidates previously displayed results and fetch diagnostics.
    tracker_file_signature = (
        snapshot_upload.getvalue() if snapshot_upload is not None else None,
        finals_upload.getvalue() if finals_upload is not None else None,
        int(minimum_tracked_samples),
    )
    if st.session_state.get("tracker_file_signature") != tracker_file_signature:
        st.session_state["tracker_file_signature"] = tracker_file_signature
        st.session_state.pop("tracker_report", None)
        st.session_state.pop("tracker_collection_audit", None)
        st.session_state.pop("tracker_collection_failures", None)
    from snapshot_storage import load_snapshots
    local_tracker_data = load_snapshots("pregame_snapshots")
    st.caption(f"Local prediction records ready to evaluate: "
               f"{len(local_tracker_data['snapshots'])}")
    if not local_tracker_data["snapshots"]:
        st.info("Capture a pregame prediction above to enable local result tracking.")
    if local_tracker_data["snapshots"]:
        st.caption("Locally stored snapshots are not durable across all hosting restarts. "
                   "Export your JSON backup after capturing predictions.")
    if local_tracker_data["invalid_files"]:
        st.warning(f"{len(local_tracker_data['invalid_files'])} local snapshot file(s) "
                   "failed validation and will not be scored.")
    backup_upload = st.file_uploader(
        "Restore exported local prediction backup (JSON)",
        type=["json"], key="tracker_restore_backup"
    )
    if st.button("Restore backup without overwriting predictions",
                 key="tracker_restore_button", disabled=backup_upload is None):
        try:
            import json
            from snapshot_backup import restore_snapshot_backup
            restored = restore_snapshot_backup(
                json.loads(backup_upload.getvalue()), "pregame_snapshots"
            )
            st.success(f"Restored {restored['imported']} predictions; "
                       f"{restored['already_present']} already existed.")
            st.warning("Imported capture timestamps cannot be independently verified. "
                       "Do not treat restored records as authenticated pregame evidence.")
            st.session_state.pop("tracker_report", None)
        except (ValueError, TypeError, OSError, UnicodeError) as exc:
            st.error(f"Backup restore failed: {exc}")
    if st.button("Evaluate locally saved predictions", key="tracker_evaluate_local",
                 disabled=not bool(local_tracker_data["snapshots"])):
        try:
            from automatic_tracking import refresh_saved_tracking
            with st.spinner("Fetching final NBA box scores for saved predictions..."):
                local_report = refresh_saved_tracking(
                    "pregame_snapshots", max_games=20,
                    min_samples=int(minimum_tracked_samples)
                )
            st.session_state["tracker_report"] = local_report
            collection = local_report["collection_audit"]
            st.session_state["tracker_collection_audit"] = {
                "Games requested": collection["games_requested"],
                "Games loaded": collection["games_loaded"],
                "Games omitted by limit": collection["games_omitted_by_limit"],
                "Failed games": len(collection["failures"]),
                "Invalid stored files": local_report["storage_audit"]["invalid_files"],
            }
            st.session_state["tracker_collection_failures"] = collection["failures"]
        except (ValueError, TypeError, KeyError, OSError, requests.RequestException) as exc:
            st.session_state.pop("tracker_report", None)
            st.session_state.pop("tracker_collection_audit", None)
            st.session_state.pop("tracker_collection_failures", None)
            st.error(f"Could not evaluate locally saved predictions: {exc}")
    if st.button("Fetch NBA finals for uploaded predictions", key="tracker_fetch_finals"):
        if snapshot_upload is None:
            st.warning("Upload pregame snapshots first.")
        else:
            try:
                import json
                from snapshot_final_collection import collect_snapshot_finals
                from tracking_pipeline import evaluate_tracked_slate

                from snapshot_batch import validate_snapshot_batch
                snapshot_rows = validate_snapshot_batch(json.loads(snapshot_upload.getvalue()))
                if not isinstance(snapshot_rows, list) or len(snapshot_rows) > 100000:
                    raise ValueError("Snapshots must be a JSON array of at most 100,000 records.")
                if not all(isinstance(row, dict) for row in snapshot_rows):
                    raise ValueError("Each snapshot must be a JSON object.")
                with st.spinner("Checking NBA final box scores..."):
                    fetched = collect_snapshot_finals(snapshot_rows, max_games=20)
                report = evaluate_tracked_slate(
                    snapshot_rows, fetched["final_players"],
                    min_samples=int(minimum_tracked_samples)
                )
                st.session_state["tracker_report"] = report
                st.session_state["tracker_collection_audit"] = {
                    "Games requested": fetched["games_requested"],
                    "Games loaded": fetched["games_loaded"],
                    "Games omitted by limit": fetched["games_omitted_by_limit"],
                    "Failed games": len(fetched["failures"]),
                }
                st.session_state["tracker_collection_failures"] = fetched["failures"]
            except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError,
                    OSError, requests.RequestException) as exc:
                st.session_state.pop("tracker_report", None)
                st.session_state.pop("tracker_collection_audit", None)
                st.session_state.pop("tracker_collection_failures", None)
                st.error(f"Could not fetch final results: {exc}")
    if st.button("Evaluate uploaded predictions", key="tracker_evaluate"):
        if snapshot_upload is None or finals_upload is None:
            st.warning("Upload both JSON files before evaluating.")
        else:
            try:
                import json
                from tracking_pipeline import evaluate_tracked_slate
                from pregame_snapshot import validate_pregame_snapshot

                from snapshot_batch import validate_snapshot_batch
                snapshot_rows = validate_snapshot_batch(json.loads(snapshot_upload.getvalue()))
                final_rows = json.loads(finals_upload.getvalue())
                if not isinstance(snapshot_rows, list) or not isinstance(final_rows, list):
                    raise ValueError("Both files must contain JSON arrays.")
                if len(snapshot_rows) > 100000 or len(final_rows) > 100000:
                    raise ValueError("Files exceed the 100,000-row evaluation limit.")
                if any(not isinstance(r, dict) for r in final_rows):
                    raise ValueError("Final statistics must contain JSON objects.")
                if any(not str(r.get("game_id") or "").isascii()
                       or not str(r.get("game_id") or "").isdigit()
                       or not str(r.get("player_id") or "").isascii()
                       or not str(r.get("player_id") or "").isdigit()
                       for r in final_rows):
                    raise ValueError("Final statistics require numeric NBA game/player IDs, not ESPN IDs.")
                result = evaluate_tracked_slate(
                    snapshot_rows, final_rows, min_samples=int(minimum_tracked_samples)
                )
                st.session_state["tracker_report"] = result
                st.session_state.pop("tracker_collection_audit", None)
                st.session_state.pop("tracker_collection_failures", None)
            except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
                st.session_state.pop("tracker_report", None)
                st.error(f"Could not evaluate uploaded tracking data: {exc}")
    if st.session_state.get("tracker_collection_audit"):
        st.dataframe(pd.DataFrame([st.session_state["tracker_collection_audit"]]),
                     use_container_width=True, hide_index=True)
        if st.session_state.get("tracker_collection_failures"):
            with st.expander("Final box-score retrieval failures"):
                st.dataframe(pd.DataFrame(st.session_state["tracker_collection_failures"]),
                             use_container_width=True, hide_index=True)
    report = st.session_state.get("tracker_report")
    if report:
        st.caption("Research-only diagnostics. Missing final results are not losses; "
                   "pushes are excluded from probability scoring.")
        st.dataframe(pd.DataFrame([report["audit"]]), hide_index=True,
                     use_container_width=True)
        summary = [{k: v for k, v in item.items() if k not in ("buckets", "exclusions")}
                   for item in report["calibration"]]
        st.dataframe(pd.DataFrame(summary), hide_index=True, use_container_width=True)
        if report["scored"]:
            scored_export = pd.DataFrame(report["scored"])
            st.dataframe(scored_export, hide_index=True, use_container_width=True)
            safe_export = scored_export.copy()
            for column in safe_export.select_dtypes(include=["object", "string"]).columns:
                safe_export[column] = safe_export[column].map(safe_spreadsheet_cell)
            st.download_button(
                "Download tracked results CSV",
                safe_export.to_csv(index=False).encode("utf-8"),
                file_name="nba_tracked_results.csv", mime="text/csv",
                key="tracker_download_results"
            )
