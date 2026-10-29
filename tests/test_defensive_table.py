import pandas as pd
from defensive_table import defensive_table_html


def record():
    return {'Player':'<script>bad</script>','Pos':'SG','Group':'G','Opponent':'BOS','Line':10,
            'L10':12,'L5':9,'H2H':None,'H2H N':0,'Projection':11,'Model Min':30,
            'Points':45,'rank_Points':1,'teams_Points':30,'varies_Points':True,
            'Rebounds':None,'Assists':None,'3PM':None,'Steals':None,'Blocks':None}


def test_markup_escapes_names_and_shows_rank_scope_and_no_fake_missing_values():
    output=defensive_table_html(pd.DataFrame([record()]))
    assert '<script>bad</script>' not in output and '&lt;script&gt;' in output
    assert 'Rank 1 of 30 qualified teams' in output and 'def-over' in output and '45.0' in output
    assert '>—<' in output
    assert 'Rank 1 of 30 qualified teams' not in defensive_table_html(pd.DataFrame([record()]),show_ranks=False)

