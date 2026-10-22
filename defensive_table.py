"""Escaped, compact defensive matchup table with rank badges."""
from html import escape
from math import ceil
import pandas as pd
from live_sources import TEAM_NAMES

DEF_STATS={'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM','steals':'Steals','blocks':'Blocks'}


def number(value):
    return '—' if pd.isna(value) else f'{float(value):.1f}'


def defensive_table_html(frame, show_ranks=True):
    headers=['TEAM / DEFENSE','POS','OPPOSING PLAYER','LINE','L10 AVG','L5 AVG','H2H','PROJ','MIN']+list(DEF_STATS.values())
    css='''<style>
    .def-wrap{overflow:auto;max-height:730px;border:1px solid #303039;border-radius:7px;background:#0e0f13}
    .def-table{width:100%;border-collapse:collapse;white-space:nowrap;color:#ededf3;font:13px system-ui,sans-serif}
    .def-table th{position:sticky;top:0;background:#15151c;z-index:1;padding:12px 10px;border-bottom:2px solid #45434e;font-size:10px;letter-spacing:.06em;color:#bcb9c7;text-align:center}
    .def-table td{padding:10px 12px;border-bottom:1px solid #36343e;text-align:center;vertical-align:middle}
    .def-table tr:hover{background:#1b1823}.def-team{text-align:left!important;max-width:155px;white-space:normal;font-weight:600}
    .def-player{text-align:left!important;min-width:150px;border-right:1px solid #54505d;font-weight:600}
    .def-pos{background:#302337;color:#d9b1f0;border:1px solid #533c61;border-radius:4px;padding:3px 5px;font-size:10px;margin-left:6px}
    .def-rank{display:block;max-width:58px;margin:4px auto 0;border:1px solid currentColor;border-radius:5px;padding:2px 4px;font-size:10px;background:#ffffff06}
    .def-green{color:#8ade99}.def-amber{color:#eac967}.def-red{color:#e77f85}.def-muted{color:#85838e}
    .def-over{background:#19743d!important;color:#e8ffed;font-weight:700}.def-under{color:#df939b}
    </style>'''
    rows=[]
    for _,r in frame.iterrows():
        position=escape(str(r.get('Pos','—')))
        player=escape(str(r['Player']))
        defense=escape(TEAM_NAMES.get(r['Opponent'],str(r['Opponent'])))
        cells=[f'<td class="def-team">{defense}</td>',f'<td>{escape(str(r.get("Group","Unknown")))}</td>',
               f'<td class="def-player">{player}<span class="def-pos">{position}</span></td>',f'<td>{number(r["Line"])}</td>']
        for field in ['L10','L5','H2H']:
            value,line=r[field],r['Line']
            cls='def-over' if not pd.isna(value) and not pd.isna(line) and value>line else ''
            tip=f'{int(r["H2H N"])} head-to-head games in loaded window' if field=='H2H' else 'Observed average, not a hit probability'
            cells.append(f'<td class="{cls}" title="{tip}">{number(value)}</td>')
        cells += [f'<td>{number(r["Projection"])}</td>',f'<td>{number(r.get("Model Min"))}</td>']
        for label in DEF_STATS.values():
            value=r.get(label)
            rank=r.get('rank_'+label)
            teams=r.get('teams_'+label,0)
            cls='def-muted'
            if not pd.isna(rank) and teams and r.get('varies_'+label,False):
                cls='def-green' if rank<=ceil(teams/3) else 'def-amber' if rank<=ceil(2*teams/3) else 'def-red'
            badge=f'<span class="def-rank">#{int(rank)}/{int(teams)}</span>' if show_ranks and not pd.isna(rank) and teams else ''
            cells.append(f'<td class="{cls}" title="Per-game allowance to all players in this position group">{number(value)}{badge}</td>')
        rows.append('<tr>'+''.join(cells)+'</tr>')
    if not rows: rows=['<tr><td colspan="15">No players match these filters.</td></tr>']
    return css+'<div class="def-wrap"><table class="def-table"><thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
