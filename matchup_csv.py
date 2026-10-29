"""Read exported matchup values without recalculating or inventing player data."""
import csv
import io
import math
import re
import pandas as pd
from team_identity import NAME_TEAMS

DEF_STATS = {'POINTS':'Points','REBOUNDS':'Rebounds','ASSISTS':'Assists','3PTM':'3PM','STEALS':'Steals','BLOCKS':'Blocks'}
COLUMNS = ['TEAM','POS','OPPOSING PLAYER','LINE','L10 AVG','L5 AVG','H2H',*DEF_STATS]
POSITIONS = {'PG','SG','SF','PF','C','G','F','G-F','F-C','Unknown'}

def numeric(value, label):
    value = value.strip()
    if value.upper() in ('','N/A','NA','NULL','NONE','—','-'): return None
    try: number = float(value)
    except ValueError: raise ValueError(f'{label}: expected a number, got {value!r}') from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{label}: value must be a finite nonnegative number')
    return number

def read_matchup_csv(content):
    if isinstance(content,bytes):
        try: content=content.decode('utf-8-sig')
        except UnicodeDecodeError: raise ValueError('Please use a UTF-8 CSV export.') from None
    lines=list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
    start=next((i for i,row in enumerate(lines) if [v.strip().upper() for v in row]==COLUMNS),None)
    if start is None: raise ValueError('CSV needs TEAM, POS, OPPOSING PLAYER, LINE, L10 AVG, L5 AVG, H2H and all six defensive stat columns.')
    metadata={row[0].strip():row[1].strip() for row in lines[:start] if len(row)==2}
    output=[]; seen=set()
    for index,values in enumerate(lines[start+1:],start+2):
        if not any(v.strip() for v in values): continue
        if len(values)!=len(COLUMNS): raise ValueError(f'CSV row {index}: wrong number of columns')
        raw=dict(zip(COLUMNS,(v.strip() for v in values)))
        opponent=NAME_TEAMS.get(raw['TEAM'])
        if not opponent: raise ValueError(f'CSV row {index}: unknown defense {raw["TEAM"]!r}')
        if raw['POS'] not in POSITIONS: raise ValueError(f'CSV row {index}: unknown matchup position')
        match=re.fullmatch(r'(.+?)\s+(PG|SG|SF|PF|C|G|F|G-F|F-C)(?:\s+(NEW TEAM))?',raw['OPPOSING PLAYER'])
        name,position,new_team=match.groups() if match else (raw['OPPOSING PLAYER'],'—',None)
        if not name: raise ValueError(f'CSV row {index}: missing player name')
        key=(opponent,raw['POS'],name.casefold())
        if key in seen: raise ValueError(f'CSV row {index}: duplicate player matchup')
        seen.add(key)
        row={'Player':name,'Pos':position,'Group':raw['POS'],'Opponent':opponent,'Team':None,
             'New team':bool(new_team),'Source':'Imported matchup CSV','H2H N':None}
        for source,target in [('LINE','Line'),('L10 AVG','L10'),('L5 AVG','L5'),('H2H','H2H')]:
            row[target]=numeric(raw[source],f'CSV row {index}, {source}')
        for source,target in DEF_STATS.items():
            parts=raw[source].split('#')
            if len(parts)>2: raise ValueError(f'CSV row {index}: invalid {source} rank')
            row[target]=numeric(parts[0],f'CSV row {index}, {source}')
            rank=None
            if len(parts)==2:
                rank=numeric(parts[1],f'CSV row {index}, {source} rank')
                if rank is None or rank!=int(rank) or not 1<=rank<=30 or row[target] is None:
                    raise ValueError(f'CSV row {index}: {source} rank must be 1–30 with an allowance value')
                rank=int(rank)
            row['rank_'+target]=rank
            row['teams_'+target]=30 if rank is not None else 0
            row['varies_'+target]=rank is not None
        output.append(row)
    if not output: raise ValueError('CSV contains no matchup rows.')
    return pd.DataFrame(output),metadata
