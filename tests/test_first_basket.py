from copy import deepcopy
from datetime import datetime, timezone
import pytest
from first_basket_data import parse_opening, collect_history
from first_basket_model import build_board, top_candidates
from first_basket_store import capture, grade, read_json

NOW = datetime(2026, 10, 28, 18, tzinfo=timezone.utc)


def payload(free_throw=False):
    players = []
    competitors = []
    for tid, team, side in [('1', 'BOS', 'home'), ('2', 'NY', 'away')]:
        competitors.append({'team': {'id': tid, 'abbreviation': team}, 'homeAway': side,
                            'score': '3' if side == 'home' and free_throw else '2'})
        players.append({'team': {'id': tid}, 'statistics': [{'athletes': [
            {'athlete': {'id': tid+str(i), 'displayName': team+str(i), 'position': {'abbreviation': 'G'}}, 'starter': True}
            for i in range(5)]}]})

    def play(seq, home, away, pid=None, tid=None, points=0, attempted=0, clock='11:45'):
        return {'sequenceNumber': str(seq), 'period': {'number': 1}, 'clock': {'displayValue': clock},
                'homeScore': home, 'awayScore': away, 'scoringPlay': points > 0,
                'scoreValue': points, 'shootingPlay': attempted > 0, 'pointsAttempted': attempted,
                'team': {'id': tid}, 'participants': [{'athlete': {'id': pid}}], 'type': {'text': 'Shot'}}
    opening = play(1, 0, 0, clock='12:00', tid='1')
    opening['type']['text'] = 'Jumpball'
    plays = [opening]
    if free_throw:
        plays.append(play(2, 1, 0, '10', '1', 1, 1))
    plays.extend([play(3, 1 if free_throw else 0, 2, '20', '2', 2, 2),
                  play(4, 3 if free_throw else 2, 2, '11', '1', 2, 2)])
    return {'header': {'id': '100', 'season': {'type': 2, 'year': 2027}, 'competitions': [
        {'id': '100', 'status': {'type': {'completed': True}}, 'date': '2026-10-27T23:00:00Z', 'competitors': competitors}]},
        'boxscore': {'players': players}, 'plays': plays}


def sample_history(n=10):
    base = parse_opening(payload(), '100')
    return [{**deepcopy(base), 'event_id': str(100+i), 'game_date': f'2026-10-{27-i:02d}'} for i in range(n)]


def slate(eid='200'):
    return [{'espnEventId': eid, 'gameTimeUTC': '2026-10-28T23:00:00Z', 'espnCompleted': False,
             'awayTeam': {'teamTricode': 'NYK'}, 'homeTeam': {'teamTricode': 'BOS'},
             'espnTeamIds': {'home': '1', 'away': '2'}, 'gameStatusText': 'Scheduled'}]


def roster():
    return list(parse_opening(payload(), '100')['players'].values())


def test_free_throw_and_first_field_goal_have_different_winners():
    result = parse_opening(payload(True), '100')
    assert result['first_points'] == 'espn:10'
    assert result['first_field_goal'] == result['first_shot'] == 'espn:20'
    assert result['team_first_shot']['BOS'] == 'espn:11'
    assert result['tip_winner'] == 'BOS'


@pytest.mark.parametrize('change', ['live', 'preseason', 'wrong_id', 'partial', 'wrong_shooter', 'score_gap', 'duplicate', 'not_five', 'final_score'])
def test_parser_rejects_unverifiable_openings(change):
    p = payload()
    if change == 'live': p['header']['competitions'][0]['status']['type']['completed'] = False
    if change == 'preseason': p['header']['season']['type'] = 1
    if change == 'wrong_id': p['header']['id'] = '999'
    if change == 'partial': p['plays'].pop(0)
    if change == 'wrong_shooter': p['plays'][1]['participants'][0]['athlete']['id'] = '10'
    if change == 'score_gap': p['plays'][1]['awayScore'] = 3
    if change == 'duplicate': p['plays'].append(p['plays'][0])
    if change == 'not_five': p['boxscore']['players'][0]['statistics'][0]['athletes'].pop()
    if change == 'final_score': p['header']['competitions'][0]['competitors'][0]['score'] = '9'
    with pytest.raises(ValueError): parse_opening(p, '100')


def test_reordered_plays_use_sequence_numbers():
    p = payload()
    p['plays'].reverse()
    assert parse_opening(p, '100')['first_field_goal'] == 'espn:20'


def test_no_today_leakage_and_no_duplicates():
    history = sample_history()
    expected = build_board(slate(), history, roster(), '2026-10-28', now=NOW)
    same_day = {**deepcopy(history[0]), 'event_id': '999', 'game_date': '2026-10-28'}
    actual = build_board(slate(), history+[history[0], same_day], roster(), '2026-10-28', now=NOW)
    assert actual == expected
    assert actual[0]['player_id'] == 'espn:20'
    assert actual[0]['readiness'] == 'Research only'
    assert len(top_candidates(actual)) == 1


def test_insufficient_history_does_not_force_picks_or_rank():
    board = build_board(slate(), sample_history(4), roster(), '2026-10-28', now=NOW)
    assert board and all(r['rank'] is None for r in board)
    assert top_candidates(board) == []


def test_removed_roster_players_and_started_games_are_excluded():
    members = [r for r in roster() if r['player_id'] != 'espn:20']
    assert all(r['player_id'] != 'espn:20' for r in build_board(slate(), sample_history(), members, '2026-10-28', now=NOW))
    assert build_board(slate(), sample_history(), roster(), '2026-10-28', now=datetime(2026, 10, 29, tzinfo=timezone.utc)) == []


def test_out_and_questionable_flags_and_lineup_expiration():
    feed = {'feed_timestamp': NOW.isoformat(), 'reports': {('NYK', 'ny0'): {'status': 'Out'}}}
    assert all(r['player_id'] != 'espn:20' for r in build_board(slate(), sample_history(), roster(), '2026-10-28', injury_feed=feed, now=NOW))
    confirmations = {'200:BOS': {'player_ids': ['espn:1'+str(i) for i in range(5)], 'source': 'Team', 'checked_at': NOW.isoformat()}}
    board = build_board(slate(), sample_history(), roster(), '2026-10-28', injury_feed={'feed_timestamp': NOW.isoformat(), 'reports': {}}, confirmations=confirmations, now=NOW)
    assert next(r for r in board if r['team'] == 'BOS')['readiness'] == 'Ready for price review'
    board = build_board(slate(), sample_history(), roster(), '2026-10-28', confirmations=confirmations, now=datetime(2026,10,28,20,tzinfo=timezone.utc))
    assert all(r['starter_status'] != 'Confirmed by user' for r in board)


def test_pretip_capture_cannot_be_replaced_or_created_late(tmp_path):
    board = build_board(slate(), sample_history(), roster(), '2026-10-28', now=NOW)
    path = tmp_path/'picks.json'
    assert capture(path, top_candidates(board), now=NOW) == 1
    assert capture(path, board[::-1], now=NOW) == 0
    assert read_json(path, [])[0]['player_id'] == 'espn:20'
    assert capture(tmp_path/'late.json', board, now=datetime(2026,10,29,tzinfo=timezone.utc)) == 0


def test_market_specific_grading_roi_and_nonstarter(tmp_path):
    board = build_board(slate('100'), sample_history(), roster(), '2026-10-28', now=NOW)
    pick = top_candidates(board)[0]
    quotes = {'espn:20:100': {'odds': 650, 'book': 'Test book', 'checked_at': NOW.isoformat()}}
    path = tmp_path/'picks.json'
    capture(path, [pick], now=NOW, quotes=quotes)
    final = parse_opening(payload(True), '100')
    final['game_date'] = '2026-10-28'
    saved = read_json(path, [])
    result = grade(saved, [final])[0]
    assert result['result'] == 'Won' and result['profit_units'] == 6.5
    result = grade([{**saved[0], 'market': 'first_points'}], [final])[0]
    assert result['result'] == 'Lost' and result['profit_units'] == -1
    final['starters']['NYK'].remove('espn:20')
    assert grade(saved, [final])[0]['result'] == 'Nonstarter — check settlement'


def test_corrupt_ledger_is_not_reset(tmp_path):
    path = tmp_path/'broken.json'
    path.write_text('{broken')
    with pytest.raises(ValueError): read_json(path, [])


def test_collect_history_reports_missing_provider_data():
    def fail(*args): raise ValueError('offline')
    result = collect_history('2026-10-28', slate(), schedule_loader=fail, roster_loader=fail)
    assert result['games'] == result['roster'] == []
    assert len(result['failures']) == 6


def test_ui_shows_no_invented_picks_when_no_report(monkeypatch, tmp_path):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    import first_basket_ui as ui
    monkeypatch.setattr(ui, 'ROOT', tmp_path)
    at = AppTest.from_file(str(Path(ui.__file__).with_name('first_basket_app.py'))).run()
    assert not at.exception
    assert any('No sample or invented picks' in m.value for m in at.info)


def test_ui_renders_research_board_and_empty_filter(monkeypatch, tmp_path):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from first_basket_store import write_json
    import first_basket_ui as ui
    monkeypatch.setattr(ui, 'ROOT', tmp_path)
    monkeypatch.setattr(ui, 'current_injuries', lambda: {'feed_timestamp': datetime.now(timezone.utc).isoformat(), 'reports': {}})
    day = datetime.now(ui.ET).date().isoformat()
    games = slate()
    games[0]['gameTimeUTC'] = day + 'T23:00:00Z'
    history = sample_history()
    write_json(tmp_path/'slates'/(day+'.json'), {'slate': games, 'games': history, 'roster': roster(),
               'as_of': day, 'built_at': datetime.now(timezone.utc).isoformat(), 'failures': [],
               'loaded': 10, 'requested': 10, 'history_window': 10})
    at = AppTest.from_file(str(Path(ui.__file__).with_name('first_basket_app.py'))).run()
    assert not at.exception
    assert any('First baskets / starts' in d.value.columns for d in at.dataframe)
    next(m for m in at.multiselect if m.label == 'Filter teams').select('BOS').run()
    assert not at.exception
    board = next(d.value for d in at.dataframe if 'First baskets / starts' in d.value.columns)
    assert set(board['Team']) == {'BOS'}
