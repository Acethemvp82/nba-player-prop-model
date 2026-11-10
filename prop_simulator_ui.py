"""Optional simulator panel; never changes board lines, rankings or hammers."""
from datetime import date
import pandas as pd
import streamlit as st
from prop_simulator import PROPS, simulation_games, simulate_prop


def render_prop_simulator(frame, feed, day):
    st.subheader('10,000-run prop simulator')
    st.caption('Research simulation · Points, rebounds, assists and threes · Separate from board rankings and 🔨 rules.')
    if 'player_id' not in frame or frame.empty:
        st.info('Verified player identities and game history are needed for the simulator.'); return
    players = frame.dropna(subset=['player_id', 'Team']).drop_duplicates(['player_id', 'Team']).sort_values('Player')
    choices = [(r['player_id'], r['Team']) for _, r in players.iterrows()]
    names = {(r['player_id'], r['Team']): f"{r['Player']} · {r['Team']} vs {r['Opponent']}" for _, r in players.iterrows()}
    if not choices:
        st.info('No verified players match the board filters.'); return
    selected = st.selectbox('Simulation player', choices, format_func=lambda p: names[p], key='prop_sim_player')
    cols = st.columns(2)
    label = cols[0].selectbox('Simulation stat', list(PROPS), key='prop_sim_stat')
    window = cols[1].selectbox('Recent games', [5, 10, 15], index=1, key='prop_sim_window')
    stat = PROPS[label]
    games = simulation_games(feed.get('observations', []), selected[0], selected[1], stat, day, window)
    st.caption(f'Slate {day} · {len(games)}/{window} available verified appearances with this team. DNPs excluded; history may cross seasons.')
    if len(games) < 5:
        st.info('At least five verified appearances with this team are needed. No simulation is produced.'); return
    if len(games) < window:
        st.warning(f'Only {len(games)} of the requested {window} games are available.')
    if (date.fromisoformat(day) - date.fromisoformat(games[0]['Date'])).days > 30:
        st.warning('The latest available appearance is over 30 days before this slate. This sample may not reflect the current role.')
    # apply_snapshot has already rejected stale, started and wrong-stat lines.
    row = players[(players['player_id'] == selected[0]) & (players['Team'] == selected[1])].iloc[0]
    snapshot_line = row.get('Line')
    available = (row.get('Line stat') == stat and isinstance(row.get('Line source'), str)
                 and pd.notna(snapshot_line))
    modes = ['Enter current line'] + (['Use verified board snapshot'] if available else [])
    mode = st.radio('Simulation line source', modes, horizontal=True, key='prop_sim_line_source')
    if mode == 'Use verified board snapshot':
        line = float(snapshot_line)
        st.caption(f"Snapshot line {line:g} · Captured {row.get('Line captured', 'Unknown')} · Confirm it against your current ticket.")
    else:
        line = st.number_input('Current line to test', min_value=0.0, value=None, step=0.5,
                               key=f'prop_sim_line_{selected[0]}_{selected[1]}_{stat}',
                               placeholder='Enter the line shown on your ticket')
        st.caption('Manually entered scenario line; this does not update the board or restart the paused FanDuel refresh.')
    request = (day, selected, stat, window, mode, line, tuple((g['Game ID'], g['Result'], g['Minutes']) for g in games))
    if st.button('Run 10,000 simulations', type='primary', disabled=line is None, key='prop_sim_run'):
        try:
            st.session_state['prop_sim_result'] = (request, simulate_prop(games, line))
        except ValueError as exc:
            st.error(str(exc)); return
    saved = st.session_state.get('prop_sim_result')
    if saved and saved[0] == request:
        result = saved[1]
        st.write(f"**{names[selected]} · {label} · Line {line:g}**")
        for col, outcome in zip(st.columns(3), ['Over', 'Under', 'Push']):
            col.metric(f'Simulated {outcome.lower()}', f"{result['percent'][outcome]:.1f}%",
                       help=f"{result['counts'][outcome]:,} of 10,000 draws")
        st.caption(f"Simulated average {result['mean']:.1f} · Middle 80% of draws: {result['p10']:g}–{result['p90']:g}. This range is not a confidence interval for the next game.")
        st.bar_chart(pd.DataFrame(result['distribution']).set_index('Total'), y='Draws')
        observed = result['historical']
        st.caption(f"Actual sample: {observed['Over']} over / {observed['Under']} under / {observed['Push']} push in {len(games)} games.")
    st.caption('Method: equally resample one past full-game total per draw. Percentages approximate this small sample’s frequencies, not validated win probabilities. No adjustments for opponent, injuries, minutes, pace or role changes; totals outside the observed sample cannot occur. Repeated runs use the same seed. More draws do not add new game evidence.')
    with st.expander('Games used in the simulation'):
        st.dataframe(pd.DataFrame(games), hide_index=True, use_container_width=True)
