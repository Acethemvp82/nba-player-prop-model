from pathlib import Path
from streamlit.testing.v1 import AppTest
import dashboard_v2 as dashboard


def fixtures(monkeypatch, forecasts):
    monkeypatch.setattr(dashboard, 'schedule_for', lambda day: [
        {'awayTeam': {'teamTricode': 'NYK'}, 'homeTeam': {'teamTricode': 'BOS'},
         'gameTimeUTC': '2026-10-21T23:30:00Z', 'gameStatusText': 'Scheduled'}])
    monkeypatch.setattr(dashboard, 'history_for', lambda *args: {'observations': []})
    monkeypatch.setattr(dashboard, 'build_pregame_baseline_board', lambda *a, **k: forecasts)
    monkeypatch.setattr(dashboard, 'matchup_context', lambda *a: {
        ('BOS', 'points'): {'matchup_score': 65, 'opponent_games': 8,
                              'opponent_allowed': 112, 'sample_reference': 108,
                              'matchup_status': 'Available'}})
    for name in ('schedule_for', 'history_for'):
        getattr(dashboard, name).clear = lambda: None


def test_populated_board_filters_and_sort(monkeypatch):
    fixtures(monkeypatch, [dict(player='Test Player', player_id='espn:1', team='NYK',
        prop='points', baseline=24, sample_games=10, recent_minutes=32,
        research_readiness='history_ready')])
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    assert not at.exception
    board = at.dataframe[0].value
    assert board.iloc[0]['Matchup'] == 65
    assert board.iloc[0]['Projection'] == 24
    at.selectbox[0].select('Highest matchup score').run()
    assert not at.exception
    at.text_input[0].input('nobody').run()
    assert len(at.dataframe[0].value) == 0
    at.button[0].click().run()
    assert not at.exception


def test_empty_and_feed_failure(monkeypatch):
    fixtures(monkeypatch, [])
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    assert not at.exception
    assert any('No eligible projections' in item.value for item in at.warning)
    def fail(*args):
        raise ValueError('feed unavailable')
    fail.clear = lambda: None
    monkeypatch.setattr(dashboard, 'history_for', fail)
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    assert not at.exception
    assert any('feed unavailable' in item.value for item in at.error)


def test_tipoffs():
    assert dashboard.tipoff_et('2026-10-21T23:30:00Z') == '07:30 PM ET'
    assert dashboard.tipoff_et(None) == 'Unknown'
