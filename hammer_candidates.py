"""Transparent research filters; these flags are not calibrated probabilities."""
import math
import re
from datetime import datetime, timedelta, timezone
from numbers import Real

LABELS={'points':'Points','rebounds':'Rebounds','assists':'Assists',
        'threes':'3PM','steals':'Steals','blocks':'Blocks'}
RULES=('OVER candidate only: FanDuel snapshot within 90 minutes; at least 7/10 L10 '
       'and 4/5 L5 overs at that line; projected starter; no reported Out, Doubtful, '
       'Questionable or GTD; current-season defense in the softest third of at least '
       '20 qualified teams, with 5+ defensive games. Research filter, not a win probability.')


def numeric(value):
    return isinstance(value,Real) and not isinstance(value,bool) and math.isfinite(value)


def full_hits(value, games, minimum):
    if not isinstance(value,str): return False
    match=re.fullmatch(r'(\d+)/(\d+) \(\d+%\)',value)
    return bool(match and int(match[2])==games and minimum<=int(match[1])<=games)


def apply_hammers(frame, stat, defense_season, now=None):
    output=frame.copy()
    output['Hammer']=False
    output['Hammer reason']=''
    if defense_season!='Current season' or stat not in LABELS: return output
    now=now or datetime.now(timezone.utc)
    label=LABELS[stat]
    for i,row in output.iterrows():
        line=row.get('Line')
        if not numeric(line) or line<0 or row.get('Line source')!='FanDuel via PropFinder export' or row.get('Line stat')!=stat:
            continue
        try:
            captured=datetime.fromisoformat(row['Line captured ISO'].replace('Z','+00:00'))
            if captured.tzinfo is None or not timedelta(minutes=-2)<=now-captured<=timedelta(minutes=90): continue
        except (KeyError,TypeError,ValueError,AttributeError): continue
        starter=row.get('Projected starter')
        if starter is None or str(starter)!='True': continue
        status=str(row.get('Status','')).casefold()
        if any(re.search(r'\b'+s+r'\b',status) for s in ['out','doubtful','questionable','gtd']): continue
        if not full_hits(row.get('PF L10 over'),10,7) or not full_hits(row.get('PF L5 over'),5,4): continue
        rank,teams,games=row.get('rank_'+label),row.get('teams_'+label),row.get('games_'+label)
        if not all(numeric(x) for x in [rank,teams,games]) or teams<20 or games<5 or rank<1 or rank>math.ceil(teams/3): continue
        if str(row.get('varies_'+label))!='True': continue
        output.at[i,'Hammer']=True
        output.at[i,'Hammer reason']=(f"OVER {line:g} {label}: {row['PF L10 over']} L10 and {row['PF L5 over']} L5; "
                                      f"defense allowance rank {int(rank)}/{int(teams)}, {int(games)} games; projected starter. "
                                      'Snapshot within 90 minutes. Research candidate, not a guarantee; verify lineup and ticket line.')
    return output
