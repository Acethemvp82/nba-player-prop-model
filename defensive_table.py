"""Escaped, compact defensive matchup table with rank badges."""
import json
from html import escape
from math import ceil
from prop_signal import prop_signal
import pandas as pd
from live_sources import TEAM_NAMES

DEF_STATS={'points':'Points','rebounds':'Rebounds','assists':'Assists','threes':'3PM','steals':'Steals','blocks':'Blocks'}


def number(value):
    return '—' if pd.isna(value) else f'{float(value):.1f}'


def defensive_table_html(frame, show_ranks=True):
    headers=['TEAM','POS','OPPOSING PLAYER','LINE','L10 AVG','L5 AVG','H2H']+list(DEF_STATS.values())
    css='''<style>
    .def-wrap{overflow:auto;max-height:730px;border:1px solid #303039;border-radius:0;background:#101010}
    .def-table{width:100%;border-collapse:collapse;white-space:nowrap;color:#ededf3;font:13px system-ui,sans-serif}
    .def-table th{position:sticky;top:0;background:#111111;z-index:1;padding:12px 10px;border-bottom:2px solid #45434e;font-size:10px;letter-spacing:.06em;color:#bcb9c7;text-align:center}
    .def-table td{padding:12px 10px;border-bottom:1px solid #36343e;text-align:center;vertical-align:middle}
    .def-table tr:hover{background:#1b1823}.def-team{text-align:left!important;max-width:155px;white-space:normal;font-weight:600}
    .def-player{position:sticky;left:0;z-index:2;background:#111111;text-align:left!important;min-width:220px;border-right:1px solid #54505d;font-weight:600}
    .def-table th:nth-child(3){position:sticky;left:0;z-index:4;min-width:220px;text-align:left}.def-logo{width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:8px}.def-pos{background:#302337;color:#d9b1f0;border:1px solid #533c61;border-radius:4px;padding:3px 5px;font-size:10px;margin-left:6px}
    .def-rank{display:block;max-width:38px;margin:4px auto 0;border:1px solid currentColor;border-radius:5px;padding:2px 4px;font-size:10px;background:#ffffff06}
    .def-green{color:#8ade99}.def-amber{color:#eac967}.def-red{color:#e77f85}.def-muted{color:#85838e}
    .def-over{background:#19743d!important;color:#e8ffed;font-weight:700}.def-under{color:#df939b}
    </style>'''
    rows=[]
    for _,r in frame.iterrows():
        position=escape(str(r.get('Pos','—')))
        player=escape(str(r['Player']))
        signal_label,signal_color,signal_reason=prop_signal(r)
        # Player signal remains available in the tap-to-open summary.
        defense=escape(TEAM_NAMES.get(r['Opponent'],str(r['Opponent'])))
        def logo(code):
            if code not in TEAM_NAMES: return ''
            espn={'NOP':'no','NYK':'ny','GSW':'gs','SAS':'sa','UTA':'utah','WSH':'wsh'}.get(code,code.lower())
            return f'<img class="def-logo" src="https://a.espncdn.com/i/teamlogos/nba/500/{espn}.png" alt="" loading="lazy">'
        player=logo(r.get('Team'))+player
        defense=logo(r['Opponent'])+defense
        cells=[f'<td class="def-team">{defense}</td>',f'<td>{escape(str(r.get("Group","Unknown")))}</td>',
               f'<td class="def-player">{player}<span class="def-pos">{position}</span></td>',f'<td>{number(r["Line"])}</td>']
        for field in ['L10','L5','H2H']:
            value,line=r[field],r['Line']
            cls='def-over' if not pd.isna(value) and not pd.isna(line) and value>line else ''
            tip=f'{int(r["H2H N"])} head-to-head games in loaded window' if field=='H2H' else 'Observed average, not a hit probability'
            cells.append(f'<td class="{cls}" title="{tip}">{number(value)}</td>')
        for label in DEF_STATS.values():
            value=r.get(label)
            rank=r.get('rank_'+label)
            teams=r.get('teams_'+label,0)
            cls='def-muted'
            if not pd.isna(rank) and teams and r.get('varies_'+label,False):
                cls='def-green' if rank<=ceil(teams/3) else 'def-amber' if rank<=ceil(2*teams/3) else 'def-red'
            badge=f'<span class="def-rank" title="Rank {int(rank)} of {int(teams)} qualified teams">#{int(rank)}</span>' if show_ranks and not pd.isna(rank) and teams else ''
            cells.append(f'<td class="{cls}" title="Per-game allowance to all players in this position group">{number(value)}{badge}</td>')
        summary={'Projection':number(r.get('Projection')), 'Model minutes':number(r.get('Model Min')), 'Evidence':str(r.get('Evidence','Unclassified history')), 'Prop signal':signal_label, 'Signal reason':signal_reason}
        rows.append('<tr data-summary="'+escape(json.dumps(summary),quote=True)+'">'+''.join(cells)+'</tr>')
    if not rows: rows=['<tr><td colspan="13">No players match these filters.</td></tr>']
    return css+'<div class="def-wrap"><table class="def-table"><thead><tr>'+''.join(f'<th>{"3PTM" if h == "3PM" else h.upper()}</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def interactive_table_html(frame, show_ranks=True):
    """Self-contained interactive table; filtering stays within the displayed rows."""
    return defensive_table_html(frame, show_ranks) + '''
    <style>
    body{margin:0;background:#0e0f13;color:#ededf3;font:13px system-ui,sans-serif}
    .table-tools{display:flex;gap:12px;align-items:center;padding:10px 4px}
    button{background:#302337;border:1px solid #77538d;border-radius:5px;color:#ededf3;padding:6px 10px;cursor:pointer}
    .def-table th button{background:none;border:0;padding:0;color:inherit;font:inherit;cursor:pointer}
    .def-team button,.position-filter{background:none;border:0;padding:0;color:inherit;font:inherit;text-align:inherit;text-decoration:underline;text-decoration-style:dotted}
    th[aria-sort]{color:#dfb4fa}.def-wrap{max-height:680px}
    </style>
    <div class="table-tools"><button id="reset">Clear table filters</button><span id="filter-status" role="status"></span></div><div id="player-detail" role="status" hidden style="padding:12px;border:1px solid #77538d;margin-bottom:10px"></div>
    <script>
    const table=document.querySelector('.def-table'),body=table.tBodies[0];
    const rows=Array.from(body.rows).filter(r=>r.cells.length===13);
    const filters={};let sorted=-1,ascending=false;
    const status=document.getElementById('filter-status');
    table.parentElement.before(document.querySelector('.table-tools'));
    table.parentElement.before(document.getElementById('player-detail'));
    for(const row of rows){const cell=row.cells[2],button=document.createElement('button');
      button.className='position-filter';button.type='button';
      while(cell.firstChild)button.append(cell.firstChild);cell.append(button);
      button.title='Show player summary';button.onclick=()=>{
        const panel=document.getElementById('player-detail');panel.replaceChildren();panel.hidden=false;
        const title=document.createElement('strong');title.textContent=cell.textContent;panel.append(title);
        for(const i of [0,3,4,5,6]){const item=document.createElement('div');
          item.textContent=table.tHead.rows[0].cells[i].textContent.replace(' ↕','')+': '+row.cells[i].textContent;panel.append(item);}
        for(const [label,value] of Object.entries(JSON.parse(row.dataset.summary||'{}'))){const item=document.createElement('div');item.textContent=label+': '+value;panel.append(item);}
        const close=document.createElement('button');close.textContent='Close summary';close.onclick=()=>panel.hidden=true;panel.append(close);
      };
    }
    function apply(){let visible=0;for(const row of rows){
      row.hidden=Object.entries(filters).some(([i,v])=>row.cells[i].textContent!==v);
      if(!row.hidden)visible++;
    }status.textContent=visible+' players'+(Object.keys(filters).length?' · '+Object.values(filters).join(' · '):' · Click a heading to sort; a defense or position to filter.');}
    for(const row of rows){for(const index of [0,1]){
      const cell=row.cells[index],value=cell.textContent,button=document.createElement('button');
      button.type='button';button.textContent=value;button.className='position-filter';
      button.title='Filter table to '+value;
      button.onclick=()=>{filters[index]=value;apply();};cell.replaceChildren(button);
    }}
    Array.from(table.tHead.rows[0].cells).forEach((cell,index)=>{
      const label=cell.textContent,button=document.createElement('button');
      button.textContent=label;button.title='Sort by '+label;button.type='button';
      button.onclick=()=>{
        ascending=sorted===index?!ascending:(index<3);sorted=index;
        for(const th of table.tHead.rows[0].cells)th.removeAttribute('aria-sort');
        cell.setAttribute('aria-sort',ascending?'ascending':'descending');
        for(const th of table.tHead.rows[0].cells){const b=th.querySelector('button');b.textContent=b.textContent.replace(/ [↑↓]$/,'');}button.textContent=label+(ascending?' ↑':' ↓');
        function value(row){const text=row.cells[index].textContent.trim();
          return (index<3)?text:(text.startsWith('—')?null:parseFloat(text));}
        rows.sort((a,b)=>{const x=value(a),y=value(b);
          if(x===null||Number.isNaN(x))return y===null||Number.isNaN(y)?0:1;
          if(y===null||Number.isNaN(y))return -1;
          return ((index<3)?x.localeCompare(y):x-y)*(ascending?1:-1);});
        for(const row of rows)body.append(row);
      };cell.replaceChildren(button);
    });
    document.getElementById('reset').onclick=()=>{for(const k of Object.keys(filters))delete filters[k];apply();};
    apply();
    </script>'''

