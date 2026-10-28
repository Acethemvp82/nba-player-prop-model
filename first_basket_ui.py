"""First-basket Streamlit board. Network work happens only on an explicit refresh."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from csv_export import safe_spreadsheet_cell
from first_basket_model import build_board, top_candidates, MARKETS
from first_basket_store import ROOT, read_json, capture, grade, write_json
from first_basket_pipeline import build_slate
from live_sources import fetch_injuries, utc
from prop_probability import american_odds_break_even

ET = ZoneInfo('America/New_York')


@st.cache_data(ttl=300, show_spinner=False)
def current_injuries():
    return fetch_injuries()


def frame_for(rows):
    return pd.DataFrame([{'Rank': r['rank'], 'Player': r['player'], 'Team': r['team'],
                         'Opponent': r['opponent'], 'Research score': r['research_score'],
                         'First baskets / starts': f"{r['first_baskets']}/{r['starts']}",
                         'Last 10 starts': f"{r['last10_first_baskets']}/{r['last10_starts']}",
                         'Team opening shots / starts': f"{r['first_shots']}/{r['starts']}",
                         'Team scored first': f"{r['team_first_baskets']}/{r['team_games']}",
                         'Team tip wins': f"{r['tip_wins']}/{r['tip_games']}",
                         'Starter': r['starter_status'], 'Availability': r['status'],
                         'Readiness': r['readiness'], 'Notes': r['flags'],
                         'Seasons (end year: starts)': str(r['season_counts']),
                         'Last historical start': r['last_history_date']} for r in rows])


def render():
    st.set_page_config(page_title='NBA First Basket', page_icon='🏀', layout='wide')
    st.title('🏀 First Basket Board')
    st.caption('Daily slate · opening possessions · ranked research candidates')
    today = datetime.now(ET).date()
    controls = st.columns([1, 2, 1, 1])
    day = controls[0].date_input('Slate date', today, key='fb_day').isoformat()
    market = controls[1].selectbox('Settlement market', list(MARKETS), format_func=MARKETS.get)
    window = controls[2].selectbox('Games per team', [10, 20, 30], index=1)
    refresh = controls[3].button('Build / refresh', type='primary')
    st.caption('First field goal excludes free throws. First points includes them. Match the selection to your sportsbook’s settlement rules.')
    report_path = ROOT / 'slates' / (day + '.json')
    if refresh:
        with st.spinner('Checking the slate, rosters and completed play-by-play… first build can take several minutes.'):
            try:
                report = build_slate(day, window)
                st.session_state['fb_report:' + day] = report
                current_injuries.clear()
            except Exception as exc:
                st.error('Build failed: ' + str(exc)[:250])
    report = st.session_state.get('fb_report:' + day) or read_json(report_path, None)
    if not report:
        st.info('Choose a date and press Build / refresh to collect the first-basket evidence. No sample or invented picks are shown.')
        return
    built = utc(report.get('built_at'))
    age = (datetime.now(timezone.utc)-built).total_seconds() if built else float('inf')
    st.caption(f"Built {built.astimezone(ET).strftime('%b %d, %I:%M %p ET') if built else 'unknown'} · {report['loaded']}/{report['requested']} historical games loaded · latest {report['history_window']} games per team requested")
    if age > 3600:
        st.warning('This build is older than one hour. Refresh before using the candidate list.')
    if report['failures']:
        st.warning(f"{len(report['failures'])} source checks failed. Rankings use incomplete evidence; inspect coverage below.")
    try:
        injuries = current_injuries() if day == today.isoformat() else None
    except ValueError:
        injuries = None
        st.warning('Injury feed unavailable. Availability needs review.')
    confirmations = st.session_state.setdefault('fb_confirmations:' + day, {})
    with st.expander('Starting lineups — confirm before using picks'):
        st.caption('Initial candidates use the latest completed game’s starters. Roster membership does not confirm a starting role. Confirmations expire after one hour.')
        for game in report['slate']:
            eid = game['espnEventId']
            if not utc(game.get('gameTimeUTC')) or utc(game['gameTimeUTC']) <= datetime.now(timezone.utc):
                continue
            for side in ('away', 'home'):
                team = game[side+'Team']['teamTricode']
                options = {r['player_id']: r['player'] for r in report['roster'] if r['team'] == team}
                key = eid + ':' + team
                previous = sorted((r for r in report['games'] if team in r['teams'].values()), key=lambda r: r['game_date'], reverse=True)
                default = [p for p in previous[0]['starters'][team] if p in options] if previous else []
                with st.form('fb_lineup:' + day + ':' + key):
                    st.write(team)
                    selected = st.multiselect('Starting five', list(options), default=default, format_func=options.get)
                    source = st.text_input('Lineup source', placeholder='Official team announcement or source URL')
                    confirm = st.form_submit_button('Confirm these five starters')
                if confirm:
                    if len(selected) != 5 or not source.strip():
                        st.error('Select exactly five players and provide the lineup source.')
                    else:
                        confirmations[key] = {'player_ids': selected, 'source': source.strip(),
                                              'checked_at': datetime.now(timezone.utc).isoformat()}
    board = build_board(report['slate'], report['games'], report['roster'], day, market,
                        injuries, confirmations=confirmations)
    if age > 3600 or report['failures']:
        for row in board:
            row['readiness'] = 'Research only'
            row['flags'] += '; Build stale or source coverage incomplete'
    top = top_candidates(board)
    metrics = st.columns(3)
    metrics[0].metric('Scheduled games', len(report['slate']))
    metrics[1].metric('Ranked candidates', sum(r['rank'] is not None for r in board))
    metrics[2].metric('Ready for price review', sum(r['readiness'] == 'Ready for price review' for r in board))
    st.subheader('Top candidates · one per game')
    if top:
        for column, row in zip(st.columns(len(top)), top):
            with column:
                st.subheader(row['player'])
                st.write(f"{row['team']} vs {row['opponent']}")
                st.metric('Research score', row['research_score'])
                st.caption(f"{row['first_baskets']} first baskets in {row['starts']} starts · {row['first_shots']} team opening shots")
                st.caption(row['readiness'] + (' · ' + row['flags'] if row['flags'] else ''))
    else:
        st.info('No upcoming candidates with at least five historical same-team starts. A full top three is not forced.')
    st.caption('Research score is an ordering index, not a hit probability. It blends smoothed historical first-basket rate (60%), team opening-shot share (25%) and team first-basket rate (15%). No validated EV or guaranteed edge is claimed.')
    teams = st.multiselect('Filter teams', sorted({r['team'] for r in board}))
    shown = [r for r in board if not teams or r['team'] in teams]
    if shown:
        frame = frame_for(shown)
        st.dataframe(frame, hide_index=True, use_container_width=True)
        st.download_button('Export first-basket board', frame.map(safe_spreadsheet_cell).to_csv(index=False),
                           file_name=f'first_basket_{day}_{market}.csv', mime='text/csv')
    with st.expander('Paper tracking and sportsbook prices'):
        st.caption('Daily builds save the first top candidate per game/market before tipoff. Later builds cannot replace that pick. These are paper records, not placed bets. Automatic selections may have unconfirmed lineups.')
        quotes = {}
        with st.form('fb_prices:' + day + market):
            for row in top:
                st.write(row['player'])
                odds = st.number_input('American odds', value=None, step=1, key='fb_odds:' + row['event_id'] + row['player_id'] + market)
                book = st.text_input('Sportsbook', key='fb_book:' + row['event_id'] + row['player_id'] + market)
                if odds is not None:
                    quotes[row['player_id'] + ':' + row['event_id']] = {'odds': odds, 'book': book,
                                                                     'checked_at': datetime.now(timezone.utc).isoformat()}
            save = st.form_submit_button('Save separate priced paper card')
        if save:
            valid = [r for r in top if (q := quotes.get(r['player_id'] + ':' + r['event_id']))
                     and american_odds_break_even(q['odds']) is not None and q['book'].strip()]
            if not valid:
                st.error('Enter valid American odds and a sportsbook for at least one selection.')
            else:
                added = capture(ROOT / 'priced-picks.json', valid, quotes=quotes)
                st.success(f'{added} new paper selections saved. Existing picks are unchanged.')
        automatic = read_json(ROOT / 'picks.json', [])
        priced = read_json(ROOT / 'priced-picks.json', [])
        saved = automatic + priced
        archive = read_json(ROOT / 'history.json', [])
        results = grade(saved, archive)
        for label, records in [('Automatic research cards', automatic), ('Manually priced cards', priced)]:
            outcomes = grade(records, archive)
            settled = [r for r in outcomes if r['result'] in ('Won', 'Lost')]
            wins = sum(r['result'] == 'Won' for r in settled)
            st.write(f'{label}: {wins} wins / {len(settled)} settled selections')
            measured = [r for r in settled if r['profit_units'] is not None]
            if measured:
                profit = sum(r['profit_units'] for r in measured)
                st.caption(f'Paper profit: {profit:+.2f} units · ROI: {100*profit/len(measured):+.1f}% on {len(measured)} priced selections (one unit each). This is observed performance, not a future hit probability.')
        if results:
            st.dataframe(pd.DataFrame([{k: r.get(k) for k in ('slate_date', 'player', 'market', 'readiness', 'odds', 'book', 'result', 'profit_units')} for r in results]), hide_index=True, use_container_width=True)
            st.download_button('Download paper records', __import__('json').dumps(saved, indent=2),
                               file_name='first_basket_paper_records.json', mime='application/json')
        st.caption('Priced cards saved in this app use local storage and can be lost on a hosting restart; download a backup. Scheduled GitHub paper records persist in the repository. Nonstarter settlement requires review.')
    with st.expander('Source coverage and method'):
        st.write('Only verified final regular-season games strictly before the selected date enter the evidence. Current and previous seasons can be included; each candidate shows the season counts. Player history stays with the same team. First baskets use the selected market, not the team’s first basket.')
        st.write('Team tip wins and opponent position context are descriptive evidence. No confirmed opening play is inferred from total points, and no odds are invented. Live sportsbook first-basket prices are not connected in this version.')
        if report['failures']:
            st.dataframe(pd.DataFrame(report['failures']), hide_index=True, use_container_width=True)
        if report['slate']:
            st.dataframe(pd.DataFrame([{'Matchup': g['awayTeam']['teamTricode'] + ' @ ' + g['homeTeam']['teamTricode'], 'Tipoff': g['gameTimeUTC'], 'Status': g['gameStatusText']} for g in report['slate']]), hide_index=True, use_container_width=True)
