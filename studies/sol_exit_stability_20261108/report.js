const el=id=>document.getElementById(id), fmt=(v,n=2)=>v==null?'—':Number(v).toLocaleString('ru-RU',{maximumFractionDigits:n});
const names={td:'TD',runner:'ADX Runner',protected_td:'Protected + TD',be_only:'Безубыток'};
let data,shown=[];
function tbl(ids,rows){return '<thead><tr>'+ids.map(v=>'<th>'+v+'</th>').join('')+'</tr></thead><tbody>'+rows.map((v,i)=>'<tr data-i="'+i+'">'+v.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody>'}
function box(ids,rows){return '<div class="wrap"><table>'+tbl(ids,rows)+'</table></div>'}
function summary(r){const yr=Object.values(r.years).slice(1,-1);return 'Net $'+fmt(r.net,0)+' · WR '+fmt(r.wr)+'% · DD '+fmt(r.dd)+'% · месячный разброс '+fmt(r.month_sd)+' п.п. · годовой разброс '+fmt(r.year_sd)+' п.п. · худший полный год '+fmt(r.year_worst)+'%'}
function draw(){
 const family=el('family').value,ref=data.refs[family],mode=el('mode').value,distance=el('distance').value,style=el('style').value;
 el('reference').textContent='Ориентир '+(family==='wide'?'9/70 · SL6 TP4,5 · TD4/1,25':'★3/240 · SL6 TP5 · без управления')+' · '+summary(ref);
 shown=(el('view').value==='selected'?data.selected:data.candidates).filter(r=>r.family===family&&(!style||r.style===style)&&(!mode||r.mode===mode)&&(!distance||(distance==='tight'?r.d<=1.5:r.d>=2)));
 const keys=new Set();shown=shown.sort((a,b)=>b.geo_solo_med-a.geo_solo_med).filter(r=>{const k=[r.mode,r.w,r.lb,r.sl,r.tp,r.cap,r.t,r.d,r.tf,r.h].join('_');if(keys.has(k))return false;keys.add(k);return true});
 el('candidates').innerHTML=tbl(['Механика','Стек/LB','SL/TP','Касания','TF · ΔADX','T/D','Net $','WR %','DD %','Разброс месяца','Разброс года','Худший год','Активаций %','Медиана соседей $'],shown.map(r=>[names[r.mode],r.w+'/'+r.lb,r.sl+'/'+r.tp,r.cap?'≤'+r.cap:'все',r.tf?r.tf+'m · '+fmt(r.h):'—',r.t+'/'+r.d,'<span class="'+(r.solo>=ref.net?'up':'down')+'">'+fmt(r.solo,0)+'</span>',fmt(r.wr),fmt(r.dd),fmt(r.month_sd),fmt(r.year_sd),fmt(r.year_worst),fmt(r.active,1),fmt(r.geo_solo_med,0)]));
 let freq=data.frequency.filter(r=>r.family===family&&(!mode||r.mode===mode)&&(!distance||r.distance===distance));
 el('frequencies').innerHTML=tbl(['Механика','TF','D','Активаций %','Net $','Δ Net $','WR %','DD %','Разброс месяца','Худший год','BE / активации %','Спасено / BE %','Спасено / активации %','Урезано / активации %'],freq.map(r=>[names[r.mode],r.tf,r.distance,r.freq,fmt(r.net,0),fmt(r.gain,0),fmt(r.wr),fmt(r.dd),fmt(r.month_sd),fmt(r.year_worst),fmt(r.hit_active),fmt(r.saved_hit),fmt(r.saved_active),fmt(r.hurt_active)]));
 scatter(ref);if(shown.length)detail(0);else el('detail').textContent='В этом срезе выбранных компромиссов нет. Расширенный список сохраняет альтернативы с их полной ценой по риску и прибыли.';
}
function scatter(ref){
 const key=el('scattermetric').value, xs=shown.map(r=>r.solo).concat(ref.net),ys=shown.map(r=>r[key]).concat(ref[key]);
 const xmin=0,xmax=Math.max(...xs)*1.08,ymin=0,ymax=Math.max(...ys)*1.12;
 const x=v=>60+900*(v-xmin)/(xmax-xmin||1),y=v=>310-270*(v-ymin)/(ymax-ymin||1);
 let s='<rect width="1000" height="350" fill="#fff"/>';
 for(let i=0;i<=5;i++){const xx=x(xmax*i/5),yy=y(ymax*i/5);s+='<path d="M'+xx+',30 V310 M60,'+yy+' H960" stroke="#e1e8df"/><text x="'+xx+'" y="338" text-anchor="middle" font-size="12">'+fmt(xmax*i/5,0)+'</text><text x="50" y="'+(yy+4)+'" text-anchor="end" font-size="12">'+fmt(ymax*i/5,1)+'</text>';}
 const colors={td:'#c17b27',runner:'#715cac',protected_td:'#227658',be_only:'#3b83b9'};
 shown.forEach((r,i)=>{s+='<circle data-i="'+i+'" cx="'+x(r.solo)+'" cy="'+y(r[key])+'" r="6" fill="'+colors[r.mode]+'" opacity=".8" style="cursor:pointer"><title>'+names[r.mode]+' '+r.w+'/'+r.lb+' $'+fmt(r.solo,0)+' · '+fmt(r[key])+'</title></circle>';});
 const a=x(ref.net),b=y(ref[key]);s+='<path d="M'+(a-8)+','+b+' h16 M'+a+','+(b-8)+' v16" stroke="#222" stroke-width="3"/><text x="'+(a+11)+'" y="'+(b-8)+'" font-size="12">Ориентир</text>';el('scatter').innerHTML=s;
}
function detail(i){const r=shown[i];if(!r)return;
 const row=(title,stem)=>[title,fmt(r[stem+'_min']),fmt(r[stem+'_med']),fmt(r[stem+'_max'])];
 let html='<h2>'+names[r.mode]+' · '+r.w+'/'+r.lb+' · SL '+r.sl+' · TP '+r.tp+' · '+(r.cap?'≤'+r.cap:'все касания')+'</h2><p>ΔADX '+fmt(r.h)+' на '+r.tf+'m · T '+r.t+'R · D '+r.d+'R · '+fmt(r.n,0)+' сделок. Прибыль long $'+fmt(r.net_long,0)+', short $'+fmt(r.net_short,0)+'.</p>';
 html+='<p>Protected '+fmt(r.protected,0)+' · Runner '+fmt(r.runner,0)+' · исполнений BE '+fmt(r.be,0)+' · сохранено убыточных '+fmt(r.saved,0)+' · урезано прибыльных '+fmt(r.hurt,0)+' · выше исходного TP '+fmt(r.above,0)+'. После Runner: медиана '+fmt(r.hold_median)+' ч, выход за час '+fmt(r.quick,0)+', дольше недели '+fmt(r.days7,0)+'.</p>';
 html+=box(['Год','2021*','2022','2023','2024','2025','2026*'],[['Доходность %',...[2021,2022,2023,2024,2025,2026].map(y=>fmt(r['y'+y]))]]);
 html+='<h3>Геометрия · '+r.geo_count+' соседей</h3>'+box(['Показатель','Мин','Медиана','Макс'],[row('Net $','geo_solo'),row('WR %','geo_wins'),row('DD %','geo_dd'),row('Разброс месяца','geo_month_sd'),row('Разброс года','geo_year_sd'),row('Худший полный год','geo_year_worst')]);
 html+='<h3>Выходы · '+r.exit_count+' соседних сочетаний T/D/ADX</h3>'+box(['Показатель','Мин','Медиана','Макс'],[row('Net $','exit_solo'),row('WR %','exit_wins'),row('DD %','exit_dd'),row('Разброс месяца','exit_month_sd'),row('Разброс года','exit_year_sd'),row('Худший полный год','exit_year_worst')]);
 el('detail').innerHTML=html;
}
el('scatter').onclick=e=>{if(e.target.dataset.i!=null)detail(+e.target.dataset.i)};el('scattermetric').onchange=draw;
el('candidates').onclick=e=>{const row=e.target.closest('tr[data-i]');if(row)detail(+row.dataset.i)};
for(const k of ['family','view','mode','distance','style'])el(k).onchange=draw;
fetch('report.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(x=>{data=x;draw()}).catch(e=>el('reference').textContent='Ошибка загрузки '+e.message);
