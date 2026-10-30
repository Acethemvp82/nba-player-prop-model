"""Compact screenshot-matched table; all provider strings are escaped."""
from html import escape
from math import ceil, isfinite
from numbers import Real
from pathlib import Path
import json
import pandas as pd
from team_identity import TEAM_NAMES, SHORT_NAMES, ESPN_LOGOS

TABLE_RELEASE='fanduel-snapshots-v6'

DEF_STATS={'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM','steals':'Steals','blocks':'Blocks'}
HEADERS=['TEAM','POS','OPPOSING PLAYER','LINE','L10 AVG','L5 AVG','H2H','POINTS','REBOUNDS','ASSISTS','3PTM','STEALS','BLOCKS']


def valid(value):
    return isinstance(value,Real) and not isinstance(value,bool) and isfinite(value)


def number(value):
    return f'{float(value):.1f}' if valid(value) else 'N/A'


def logo(code):
    if not isinstance(code,str) or code not in TEAM_NAMES: return ''
    alias=ESPN_LOGOS.get(code,code.lower())
    return f'<img class="def-logo" src="https://a.espncdn.com/i/teamlogos/nba/500/{alias}.png" alt="" loading="lazy" onerror="this.hidden=true">'


def defensive_table_html(frame, show_ranks=True):
    css=Path(__file__).with_name('matchup_table.css').read_text()
    rows=[]
    for _,r in frame.iterrows():
        opponent=r.get('Opponent'); defense=SHORT_NAMES.get(opponent,str(opponent or 'Unknown'))
        position=str(r.get('Pos') or '—'); name=str(r.get('Player') or 'Unknown player')
        matchup_position=str(r.get('Group') or 'Unknown')
        new_team=r.get('New team',False)
        new_team=isinstance(new_team,(bool,Real)) and not pd.isna(new_team) and bool(new_team)
        player=f'{logo(r.get("Team"))}<span class="def-name">{escape(name)}</span><span class="def-pos">{escape(position)}</span>'
        if new_team: player+='<span class="def-new">NEW TEAM</span>'
        cells=[f'<td class="def-team" data-value="{escape(defense)}">{logo(opponent)}<span>{escape(defense)}</span></td>',
               f'<td class="def-match-pos" data-value="{escape(matchup_position)}">{escape(matchup_position)}</td>',
               f'<td class="def-player" data-value="{escape(name)}"><button type="button" class="player-button" aria-label="Details for {escape(name)}">{player}</button></td>']
        export=[defense,matchup_position,name+' '+position+(' NEW TEAM' if new_team else '')]
        for field in ['Line','L10','L5','H2H']:
            value=r.get(field); line=r.get('Line')
            cls='def-over' if field!='Line' and valid(value) and valid(line) and value>line else ''
            tooltip='Imported value; sample count not supplied' if str(r.get('Source','')).startswith('Imported') else 'Observed average, not a hit probability'
            if field=='H2H' and valid(r.get('H2H N')): tooltip=f'{int(r["H2H N"])} head-to-head games in loaded history'
            if field in ('L10','L5') and valid(r.get(field+' N')): tooltip=f'{int(r[field+" N"])} completed appearances; season/team boundaries may be crossed'
            extra=''
            if field=='Line' and valid(value) and isinstance(r.get('Line source'),str):
                tooltip=f"{r['Line source']} · Captured {r.get('Line captured','Unknown')} · {r.get('Line status','Export snapshot')}"
                extra='<small class="line-book">FD snapshot</small>'
            count=r.get('PF '+field+' over')
            if field in ('L5','L10') and isinstance(count,str):
                extra=f'<small class="line-hit" title="PropFinder historical overs at this exported line">O {escape(count)}</small>'
            cells.append(f'<td class="{cls}" data-value="{value if valid(value) else ""}" title="{escape(tooltip)}">{number(value)}{extra}</td>')
            export.append(value if valid(value) else 'N/A')
        for label in DEF_STATS.values():
            value,rank,teams=r.get(label),r.get('rank_'+label),r.get('teams_'+label)
            cls='def-muted';badge=''
            if valid(rank) and valid(teams) and teams>0:
                if r.get('varies_'+label,False):
                    cls='def-green' if rank<=ceil(teams/3) else 'def-amber' if rank<=ceil(2*teams/3) else 'def-red'
                if show_ranks:
                    badge=f'<span class="def-rank" title="Rank {int(rank)} of {int(teams)} qualified teams">#{int(rank)}</span>'
            sample=r.get('games_'+label)
            tip='Per-game defensive allowance to this position group'
            if valid(sample): tip+=f'; {int(sample)} completed games'
            omitted=r.get('omitted_'+label)
            if valid(omitted) and omitted: tip+=f'; {int(omitted)} games omitted for incomplete positions'
            cells.append(f'<td class="{cls}" data-value="{value if valid(value) else ""}" title="{escape(tip)}">{number(value)}{badge}</td>')
            export.append(number(value)+(f' #{int(rank)}' if valid(rank) else ''))
        summary={}
        for key in ('Line source','Line captured','Line stat','Line status','PF L5 over','PF L10 over','PF H2H over','Projection','Model Min','Evidence','Status','Sample','Role note','Source','L10 N','L5 N','H2H N','Latest game','Position source','History window','games_Points','games_Rebounds','games_Assists','games_3PM','games_Steals','games_Blocks'):
            value=r.get(key)
            display={'L10 N':'Last 10 sample','L5 N':'Last 5 sample','H2H N':'H2H games','games_Points':'Points allowance games','games_Rebounds':'Rebound allowance games','games_Assists':'Assist allowance games','games_3PM':'3PTM allowance games','games_Steals':'Steal allowance games','games_Blocks':'Block allowance games'}.get(key,key)
            if valid(value): summary[display]=float(value)
            elif isinstance(value,str) and value: summary[display]=value
        details=escape(json.dumps(summary),quote=True)
        values=escape(json.dumps(export,default=lambda v:float(v)),quote=True)
        rows.append(f'<tr data-summary="{details}" data-export="{values}">'+''.join(cells)+'</tr>')
    if not rows: rows=['<tr class="empty"><td colspan="13">No players match these filters.</td></tr>']
    return '<style>'+css+'</style><div class="def-wrap" role="region" aria-label="NBA defensive matchups" tabindex="0"><table class="def-table"><thead><tr>'+''.join(f'<th scope="col">{h}</th>' for h in HEADERS)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def interactive_table_html(frame, show_ranks=True, metadata=None):
    tools='''<div class="table-tools"><input id="table-search" type="search" placeholder="Find player…" aria-label="Find player"><select id="defense-filter" aria-label="Defense"><option value="">All teams</option></select><select id="position-filter" aria-label="Matchup position"><option value="">All positions</option></select><button type="button" id="export">Export to CSV <span aria-hidden="true">↗</span></button><button type="button" id="reset" title="Clear search and filters">Reset</button><span id="filter-status" role="status"></span></div><div id="player-detail" role="status" hidden></div>'''
    # Metadata is JSON data, never executable HTML or JS from the provider.
    meta=escape(json.dumps(metadata or {}),quote=True)
    return tools+f'<div id="table-metadata" data-value="{meta}" hidden></div>'+defensive_table_html(frame,show_ranks)+'<script>'+Path(__file__).with_name('matchup_table.js').read_text()+'</script>'
