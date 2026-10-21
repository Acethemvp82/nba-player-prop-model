"""NBA Player Prop Model — live schedule and player feed preview."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from nba_data import NBADataError, scoreboard, game_players
from season_schedule import season_schedule, games_on
from espn_schedule import espn_games_on
from espn_players import espn_game_players, espn_team_roster
from history_collection import recent_player_summaries, fetch_boxscore_players
from projection_baseline import baseline_projections
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

st.caption("Live scoreboard and player listings update from cached NBA feeds. Schedule and historical statistics use separate caches.")
try:
    games = load_games()
except NBADataError as exc:
    st.error(f"Could not retrieve NBA games: {exc}")
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
    st.warning(f"Official NBA season schedule unavailable: {exc}")
    try:
        slate_games = load_espn_slate(slate_date.isoformat())
        st.info("Using ESPN schedule fallback. Matchups and tipoffs only: ESPN event IDs are "
                "not NBA box-score IDs, and this does not restore player or historical feeds.")
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
            st.info("Showing ESPN schedule-only fallback for today. Player box scores are not connected.")
            st.dataframe(pd.DataFrame(fallback_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No games returned by the NBA scoreboard or ESPN fallback today.")
    except NBADataError as exc:
        st.warning(f"Current-day NBA schedule unavailable from both feeds: {exc}")

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
    missing_teams = (set(matchup) - {p.get("team") for p in players}
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
    st.dataframe(board.drop(columns=["Player ID"]), use_container_width=True, hide_index=True)
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
