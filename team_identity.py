"""Team names and logo aliases without importing network clients."""
TEAM_NAMES = dict(zip(
    'ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WSH'.split(),
    ['Atlanta Hawks','Boston Celtics','Brooklyn Nets','Charlotte Hornets','Chicago Bulls','Cleveland Cavaliers','Dallas Mavericks','Denver Nuggets','Detroit Pistons','Golden State Warriors','Houston Rockets','Indiana Pacers','Los Angeles Clippers','Los Angeles Lakers','Memphis Grizzlies','Miami Heat','Milwaukee Bucks','Minnesota Timberwolves','New Orleans Pelicans','New York Knicks','Oklahoma City Thunder','Orlando Magic','Philadelphia 76ers','Phoenix Suns','Portland Trail Blazers','Sacramento Kings','San Antonio Spurs','Toronto Raptors','Utah Jazz','Washington Wizards']))
SHORT_NAMES = dict(zip(TEAM_NAMES, ['Hawks','Celtics','Nets','Hornets','Bulls','Cavaliers','Mavericks','Nuggets','Pistons','Warriors','Rockets','Pacers','Clippers','Lakers','Grizzlies','Heat','Bucks','Timberwolves','Pelicans','Knicks','Thunder','Magic','76ers','Suns','Trail Blazers','Kings','Spurs','Raptors','Jazz','Wizards']))
NAME_TEAMS = {name: code for code, name in TEAM_NAMES.items()}
NAME_TEAMS.update({name: code for code, name in SHORT_NAMES.items()})
NAME_TEAMS.update({code: code for code in TEAM_NAMES})
ESPN_LOGOS = {'NOP':'no','NYK':'ny','GSW':'gs','SAS':'sa','UTA':'utah'}
