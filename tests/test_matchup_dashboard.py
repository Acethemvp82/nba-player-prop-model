from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
import matchup_dashboard as dashboard
from matchup_csv import read_matchup_csv


def fixture_frame():
    frame,_=read_matchup_csv((Path(__file__).resolve().parents[1]/'data'/'reference-matchups-2026-10-29.csv').read_bytes())
    frame['Status']='Unknown'
    return frame


def test_main_live_and_imported_sources_render_without_exceptions(monkeypatch):
    frame=fixture_frame()
    monkeypatch.setattr(dashboard,'live_board',lambda *a:(frame,[],{'loaded':10,'built_at':'test','defense_season':2027}))
    import dashboard_v2
    monkeypatch.setattr(dashboard_v2,'odds_key',lambda:'')
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    assert not at.exception
    assert at.title[0].value=='NBA DEFENSIVE MATCHUPS'
    assert any('PG / SG / SF / PF / C' in c.value for c in at.caption)
    assert not any('FanDuel' in c.value or 'sportsbook lines' in c.value for c in at.caption)
    at.radio[0].set_value('Imported matchup CSV').run()
    assert not at.exception
    assert any('30 players' in c.value for c in at.caption)
    assert any('2026-10-29' in c.value for c in at.caption)
    assert not at.number_input  # no forced manual player-by-player line workbench


def test_live_outage_keeps_csv_path_available(monkeypatch):
    def fail(*a): raise ValueError('Feed unavailable')
    monkeypatch.setattr(dashboard,'live_board',fail)
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    assert not at.exception
    assert any('Feed unavailable' in e.value for e in at.error)
    at.radio[0].set_value('Imported matchup CSV').run()
    assert not at.exception and not at.error


def test_filter_literal_search_and_empty_result():
    frame=fixture_frame()
    assert dashboard.filter_board(frame,search='[').empty
    assert len(dashboard.filter_board(frame,search='mobley'))==1
    assert set(dashboard.filter_board(frame,defenses=['ATL'])['Opponent'])=={'ATL'}
    assert set(dashboard.filter_board(frame,positions=['PG'])['Group'])=={'PG'}
