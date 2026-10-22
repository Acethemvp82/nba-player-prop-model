from position_defense import positional_allowance,position_group


def sample():
    return [dict(player_id=f'espn:{p}',game_id=f'espn:{100*t+g}',game_date=f'2026-10-{g:02}',
        team='NYK',opponent=opp,is_final=True,minutes=20,position=('G' if p<3 else 'F' if p<6 else 'C'),
        points=10+t*5,rebounds=4,assists=2,threes=1,steals=1,blocks=0)
        for t,opp in enumerate(['BOS','MIA','LAL']) for g in range(1,6) for p in range(8)]


def test_positions_are_explicit_and_ranks_direction_and_scope():
    result=positional_allowance(sample(),'2026-10-10')
    assert result['BOS','G','points']['allowed']==30
    assert result['LAL','G','points']['allowed']==60
    assert result['LAL','G','points']['rank']==1
    assert result['BOS','G','points']['rank']==3
    assert result['BOS','G','rebounds']['rank']==1
    assert result['BOS','G','points']['ranked_teams']==3
    assert position_group('PG')=='G' and position_group('G-F') is None


def test_partial_positions_samples_and_conflicting_games_abstain():
    rows=sample()
    incomplete=[{**r,'position':None} if r['player_id']=='espn:0' else r for r in rows]
    assert positional_allowance(incomplete,'2026-10-10')=={}
    assert positional_allowance(rows,'2026-10-03')=={}
    conflicted=rows+[{**rows[0],'points':99}]
    assert ('BOS','G','points') not in positional_allowance(conflicted,'2026-10-10')
    limited=positional_allowance([r for r in rows if r['opponent']=='BOS'],'2026-10-10')
    assert limited['BOS','G','points']['rank'] is None


def test_duplicate_and_future_rows_do_not_change_totals():
    rows=sample()
    assert positional_allowance(rows,'2026-10-10')==positional_allowance(rows+rows+[
        {**r,'game_date':'2026-10-10','game_id':'espn:999'} for r in rows[:8]],'2026-10-10')
