(()=>{
'use strict';
const table=document.querySelector('.def-table'),body=table.tBodies[0];
const rows=Array.from(body.rows).filter(row=>row.cells.length===13);
const search=document.getElementById('table-search'),defense=document.getElementById('defense-filter'),position=document.getElementById('position-filter');
const status=document.getElementById('filter-status');
const meta=JSON.parse(document.getElementById('table-metadata').dataset.value);
let sorted=7,ascending=false;
const value=(row,index)=>row.cells[index].dataset.value;
for(const [select,index] of [[defense,0],[position,1]]){
 for(const text of [...new Set(rows.map(row=>value(row,index)))].sort()){
  const option=document.createElement('option');option.textContent=text;option.value=text;select.append(option);
 }
}
function apply(){let visible=0;for(const row of rows){
 row.hidden=!!((defense.value&&value(row,0)!==defense.value)||(position.value&&value(row,1)!==position.value)||(search.value&&!value(row,2).toLowerCase().includes(search.value.toLowerCase().trim())));
 if(!row.hidden)visible++;
}status.textContent=visible+' of '+rows.length+' players · '+(meta.Source||'Matchup board');}
search.addEventListener('input',apply);defense.addEventListener('change',apply);position.addEventListener('change',apply);
document.getElementById('reset').onclick=()=>{search.value='';defense.value='';position.value='';apply();};
function sort(index,toggle){ascending=toggle?(sorted===index?!ascending:index<3):false;sorted=index;
 rows.sort((a,b)=>{const x=value(a,index),y=value(b,index);if(x==='')return y===''?0:1;if(y==='')return -1;
 const diff=index<3?x.localeCompare(y):Number(x)-Number(y);return diff*(ascending?1:-1);});
 for(const row of rows)body.append(row);
 Array.from(table.tHead.rows[0].cells).forEach((cell,i)=>{
 cell.removeAttribute('aria-sort');const button=cell.querySelector('button');button.textContent=button.dataset.label+(i===index?(ascending?' ↑':' ↓'):'');
 if(i===index)cell.setAttribute('aria-sort',ascending?'ascending':'descending');
 });
}
Array.from(table.tHead.rows[0].cells).forEach((cell,index)=>{const button=document.createElement('button');button.type='button';button.dataset.label=cell.textContent;button.title='Sort by '+cell.textContent;button.onclick=()=>sort(index,true);cell.replaceChildren(button);});
for(const row of rows){row.querySelector('.player-button').onclick=()=>{
 const panel=document.getElementById('player-detail');panel.replaceChildren();panel.hidden=false;
 const title=document.createElement('strong');title.textContent=value(row,2);panel.append(title);
 const pairs=[['Defense',value(row,0)],['Matchup position',value(row,1)],...Array.from([3,4,5,6],i=>[table.tHead.rows[0].cells[i].querySelector('button').dataset.label,row.cells[i].textContent]),...Object.entries(JSON.parse(row.dataset.summary))];
 for(const [label,text] of pairs){const line=document.createElement('div');line.textContent=label+': '+text;panel.append(line);}
 const button=document.createElement('button');button.textContent='Close details';button.onclick=()=>panel.hidden=true;panel.append(button);
};}
function csvCell(v){let text=String(v??'');if(/^[\s]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';}
document.getElementById('export').onclick=()=>{
 const lines=[];for(const [key,v] of Object.entries(meta))lines.push([key,v].map(csvCell).join(','));lines.push('');
 lines.push(Array.from(table.tHead.rows[0].cells,c=>csvCell(c.querySelector('button').dataset.label)).join(','));
 for(const row of rows)if(!row.hidden)lines.push(JSON.parse(row.dataset.export).map(csvCell).join(','));
 const url=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='nba-defensive-matchups.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
sort(7,false);apply();
})();
