from matchup_board import build_matchup_board


def row(day,gid,points=10,opp='BOS',**extra):
    return dict(player_id='espn:1',player='Alpha',team='NYK',opponent=opp,
                game_id='espn:'+str(gid),game_date=day,is_final=True,
                minutes=30,points=points,rebounds=5,assists=4,threes=2,position='PG',**extra)


def test_one_player_row_pivots_four_props_and_preserves_zero():
    forecasts=[dict(player_id='espn:1',player='Alpha',team='NYK',prop=p,baseline=v,
        sample_games=5,matchup_score=70) for p,v in [('points',20),('rebounds',6),('assists',4),('threes',0)]]
    result=build_matchup_board([row('2026-10-10',1)],forecasts,{'NYK':'BOS'},'2026-10-21')
    assert len(result)==1
    assert result[0]['Projection']==20 and result[0]['Points'] is None
    assert build_matchup_board([row('2026-10-10',1)],forecasts,{'NYK':'BOS'},'2026-10-21',prop='threes')[0]['Projection']==0
    assert result[0]['Pos']=='PG'


def test_l10_l5_h2h_use_only_pre_slate_finals_and_deduplicate():
    observations=[row(f'2026-10-{g:02}',g,points=g,opp='BOS' if g%2 else 'MIA') for g in range(1,13)]
    observations += [observations[-1],row('2026-10-21',100,points=1000),
                     {**row('2026-10-20',99,points=1000),'is_final':False}]
    result=build_matchup_board(observations,[],{'NYK':'BOS'},'2026-10-21')[0]
    assert result['L10']==7.5 and result['L5']==10
    assert result['H2H']==6 and result['H2H N']==6
    assert result['Points'] is None and result['Projection'] is None


def test_missing_position_and_h2h_remain_unknown_not_zero():
    observations=[{**row('2026-10-10',1,opp='MIA'),'position':None}]
    r=build_matchup_board(observations,[],{'NYK':'BOS'},'2026-10-21')[0]
    assert r['Pos']=='—' and r['H2H'] is None and r['H2H N']==0
    assert r['Matchup'] is None


def test_defensive_columns_use_position_allowance_not_player_projection():
    context={('BOS','G','points'):{'allowed':45,'rank':2,'ranked_teams':10,'games':5}}
    forecasts=[dict(player_id='espn:1',player='Alpha',team='NYK',prop='points',baseline=20,sample_games=5,forecast_minutes=30)]
    result=build_matchup_board([row('2026-10-10',1)],forecasts,{'NYK':'BOS'},'2026-10-21',context=context)[0]
    assert result['Points']==45 and result['Projection']==20
    assert result['Def Rank']==2 and result['Group']=='G'
    assert result['Defense Games']==5
