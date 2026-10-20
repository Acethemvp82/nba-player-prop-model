"""NBA Player Prop Model — live schedule and player feed preview."""
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from nba_data import NBADataError, scoreboard, game_players

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

st.subheader("Today's NBA games")
if game_rows:
    st.dataframe(pd.DataFrame(game_rows).drop(columns=["Game ID"]), use_container_width=True, hide_index=True)
else:
    st.warning("No games returned by today's NBA scoreboard.")

st.subheader("Master Player Prop Board — data preview")
categories = ["Points", "Rebounds", "Assists", "3-Pointers"]
selected = st.multiselect("Prop categories", categories, default=categories)
columns = ["Game", "Player", "Team", "Opponent", "Prop", "FanDuel Line", "Over Odds", "Projection", "Over Probability", "Edge", "Confidence"]
rows = []
failures = []
for game in game_rows:
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
                "Team": player.get("team"),
                "Opponent": player.get("opponent"),
                "Prop": prop,
                "FanDuel Line": None,
                "Over Odds": None,
                "Projection": None,
                "Over Probability": None,
                "Edge": None,
                "Confidence": "Not calculated",
            })
board = pd.DataFrame(rows, columns=columns)
if not board.empty:
    st.caption(f"{board['Player'].nunique()} unique players listed in available game feeds; not necessarily the complete active NBA roster.")
    st.dataframe(board, use_container_width=True, hide_index=True)
else:
    st.warning("No player listings available yet. Some box scores may not publish rosters before tipoff.")
if failures:
    with st.expander(f"NBA game feeds unavailable ({len(failures)})"):
        for failure in failures:
            st.write(failure)
st.caption("Blank FanDuel lines and model projections are intentional. No placeholder numbers or unverified betting probabilities are displayed.")
with st.expander("Model methodology and safeguards"):
    st.markdown("""
- Next: season and recent-game player statistics, minutes and roster coverage.
- Then: projections adjusted for role, matchup, pace and uncertainty.
- Only compute OVER probabilities after the projection model is validated.
- Only compare against timestamped, authorized sportsbook lines.
- Track outcomes, calibration and performance without look-ahead bias.
""")
