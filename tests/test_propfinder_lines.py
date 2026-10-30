import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
import pytest
from propfinder_lines import apply_snapshot,export_snapshot,player_key
from defensive_table import defensive_table_html

NOW=datetime(2026,10,30,12,tzinfo=timezone.utc)
GAMES=[{'away':'CHA','home':'WAS','start':'2026-10-30T19:00:00-04:00'}]
CSV='Team,Player,Prop,L5 Avg,L10 Avg,L5,L10,H2H\nCHA,LaMelo Ball,o20.5 Points,18,19,(3/5),(6/10),(2/3)\n'


def snapshot(content=CSV):
    return export_snapshot(content,GAMES,NOW.isoformat(),fanduel_only=True)


def board():
    return pd.DataFrame([{'Team':'CHA','Opponent':'WAS','Player':'LaMelo Ball','Line':None,'L10':19.2,'L5':18.,'Pos':'PG','Group':'PG'}])


def test_exact_line_and_over_counts_preserve_live_averages():
    frame,health=apply_snapshot(board(),snapshot(),'2026-10-30','points',NOW)
    assert health['matched']==1
    assert frame.iloc[0]['Line']==20.5
    assert frame.iloc[0]['PF L10 over']=='6/10 (60%)'
    assert frame.iloc[0]['L10']==19.2
    html=defensive_table_html(frame)
    assert 'FD snapshot' in html and 'O 6/10 (60%)' in html
    assert 'FanDuel via PropFinder export' in html


@pytest.mark.parametrize('change',[{'Team':'WAS'},{'Opponent':'BOS'},{'Player':'Lonzo Ball'}])
def test_reject_wrong_team_opponent_or_player(change):
    frame=board()
    for key,value in change.items(): frame[key]=value
    output,health=apply_snapshot(frame,snapshot(),'2026-10-30','points',NOW)
    assert health['matched']==0 and output.iloc[0]['Line'] is None


@pytest.mark.parametrize('day,stat,now',[
    ('2026-10-29','points',NOW),('2026-10-30','rebounds',NOW),
    ('2026-10-30','points',NOW+timedelta(days=1)),
    ('2026-10-30','points',datetime(2026,10,30,23,tzinfo=timezone.utc)),
    ('2026-10-30','points',NOW-timedelta(minutes=3)),
])
def test_wrong_stat_day_stale_future_capture_and_started_games_stay_missing(day,stat,now):
    output,health=apply_snapshot(board(),snapshot(),day,stat,now)
    assert health['matched']==0 and output.iloc[0]['Line'] is None


def test_only_full_game_core_markets_and_verified_book_import():
    text=CSV+'CHA,LaMelo Ball,o5.5 Q1 Points,1,2,(3/5),(6/10),(0/0)\nCHA,LaMelo Ball,o26.5 Points + Rebounds,1,2,(3/5),(6/10),(0/0)\n'
    assert len(snapshot(text)['records'])==1
    with pytest.raises(ValueError): export_snapshot(CSV,GAMES,NOW.isoformat())
    with pytest.raises(ValueError): export_snapshot(CSV,GAMES*2,NOW.isoformat(),fanduel_only=True)


def test_conflicting_lines_and_invalid_counts_are_not_used():
    text=CSV+'CHA,LaMelo Ball,o21.5 Points,18,19,(3/5),(6/10),(2/3)\n'
    assert snapshot(text)['records']==[]
    s=snapshot(CSV.replace('(6/10)','(11/10)').replace('(3/5)','(0/0)'))
    assert s['records'][0]['l10_over'] is None and s['records'][0]['l5_over'] is None
    s=snapshot();s['records']*=2
    assert apply_snapshot(board(),s,'2026-10-30','points',NOW)[1]['matched']==0


def test_saved_export_has_unique_supported_markets_with_explicit_game_context():
    s=json.loads((Path(__file__).resolve().parents[1]/'data/propfinder-fanduel.json').read_text())
    from propfinder_lines import MARKETS,stamp,ET,finite
    assert s['version']==1 and s['bookmaker']=='FanDuel'
    assert s['records']
    assert {r['stat'] for r in s['records']}.issubset(set(MARKETS.values()))
    for r in s['records']:
        assert r['team'] != r['opponent']
        assert stamp(r['start']).astimezone(ET).date().isoformat()==r['day']
        assert finite(r['line']) and r['line']>=0
    assert player_key('Luka Dončić')==player_key('Luka Doncic')
    keys=[(r['day'],r['team'],r['opponent'],player_key(r['player']),r['stat']) for r in s['records']]
    assert len(keys)==len(set(keys))
