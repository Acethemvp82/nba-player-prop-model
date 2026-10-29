from pathlib import Path
import pandas as pd
import pytest
from matchup_csv import read_matchup_csv
from defensive_table import defensive_table_html, interactive_table_html

REFERENCE=Path(__file__).resolve().parents[1]/'data'/'reference-matchups-2026-10-29.csv'


def test_reference_preserves_all_values_and_position_mismatches():
    frame,meta=read_matchup_csv(REFERENCE.read_bytes())
    assert len(frame)==30 and meta=={'Season':'2026','Window':'Full Season'}
    mobley=frame[frame['Player']=='Evan Mobley'].iloc[0]
    assert (mobley['Opponent'],mobley['Line'],mobley['L10'],mobley['L5'])==('ATL',17.5,18.7,19.)
    assert (mobley['Points'],mobley['rank_Points'],mobley['Rebounds'],mobley['rank_Rebounds'])==(34.2,2,16.2,1)
    lillard=frame[frame['Player']=='Damian Lillard'].iloc[0]
    assert lillard['Group']=='PG' and lillard['Pos']=='SG'
    assert frame[frame['Player']=='Ja Morant'].iloc[0]['New team']
    jordan=frame[frame['Player']=='DeAndre Jordan'].iloc[0]
    assert pd.isna(jordan['Line'])
    # Missing source sample counts and offensive team IDs must not be fabricated.
    assert frame['H2H N'].isna().all() and frame['Team'].isna().all()


@pytest.mark.parametrize('old,new',[('35.3 #2','35.3 #31'),('35.3 #2','35.3 #2.2'),('35.3 #2','N/A #2'),('23.5,24.3','nan,24.3'),('23.5,24.3','-1,24.3')])
def test_invalid_csv_rejected(old,new):
    with pytest.raises(ValueError): read_matchup_csv(REFERENCE.read_text().replace(old,new,1))


def test_duplicate_rows_rejected():
    text=REFERENCE.read_text();row=text.splitlines()[4]
    with pytest.raises(ValueError,match='duplicate'): read_matchup_csv(text+'\n'+row)


def test_exact_column_order_and_safe_import_markup():
    frame,meta=read_matchup_csv(REFERENCE.read_bytes())
    frame.at[0,'Player']='<img src=x onerror=alert(1)>'
    html=interactive_table_html(frame,metadata=meta)
    assert '<img src=x' not in html and '&lt;img src=x' in html
    headers=['TEAM','POS','OPPOSING PLAYER','LINE','L10 AVG','L5 AVG','H2H','POINTS','REBOUNDS','ASSISTS','3PTM','STEALS','BLOCKS']
    assert [html.index('>'+h+'</th>') for h in headers]==sorted(html.index('>'+h+'</th>') for h in headers)
    assert html.count('<th scope="col">')==13
    assert 'NEW TEAM</span>' in html
    assert '>#1</span>' in html
    assert 'Rank 1 of 30 qualified teams' in html
    assert '<th scope="col">PROJ' not in html
    assert 'Imported value; sample count not supplied' in html


def test_no_green_when_missing_or_equal_line():
    frame,_=read_matchup_csv(REFERENCE.read_bytes())
    row=frame.iloc[[0]].copy();row['Line']=None
    html=defensive_table_html(row)
    assert 'class="def-over"' not in html
    row['Line']=row['L10'];row['L5']=row['L10'];row['H2H']=None
    assert 'class="def-over"' not in defensive_table_html(row)
