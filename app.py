"""NBA Player Prop Model — initial Streamlit foundation."""
import pandas as pd
import streamlit as st

st.set_page_config(page_title="NBA Player Prop Model", page_icon="🏀", layout="wide")
st.title("🏀 NBA Player Prop Model")
st.caption("FanDuel-focused | All-player master board | Foundation v0.1")

st.info("Foundation installed. Live NBA player data, projections, and FanDuel odds are not connected yet. No betting edges are being claimed.")
categories = ["Points", "Rebounds", "Assists", "3-Pointers"]
selected = st.multiselect("Prop categories", categories, default=categories)
st.subheader("Master Player Prop Board")
columns = ["Game", "Player", "Team", "Opponent", "Prop", "FanDuel Line", "Over Odds", "Projection", "Over Probability", "Edge", "Confidence"]
board = pd.DataFrame(columns=columns)
st.dataframe(board, use_container_width=True, hide_index=True)
st.caption("Waiting for verified player statistics, matchup inputs, and licensed or authorized FanDuel lines. Filters will activate when data is available.")
with st.expander("Model methodology and safeguards"):
    st.markdown("""
- Estimate minutes and per-minute production using recent games and season baselines.
- Adjust for opponent defense, pace, player role, and injury-related changes when reliable inputs are available.
- Model prop distributions and calculate P(actual stat > FanDuel line).
- Compare model probabilities with sportsbook break-even probabilities including odds.
- Track closing lines and realized outcomes to assess calibration.
- Never present missing or stale odds as live, or placeholder probabilities as forecasts.
""")
