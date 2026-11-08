'use strict';
const $=id=>document.getElementById(id);
const families={wide:'Широкий 11/20',wide4:'Широкий 11/20 · ≤4',narrow:'Узкий 5/280',middle:'Средний 7/170'};
const names={net:'Net Won, $',wr:'WR, %',dd:'Max DD, %',per:'Net / сделку, $',n:'Сделок',freq:'Защита / все, %',hit:'BE / активации, %',success:'Спасено / выходы BE, %',saved:'Спасено сделок',hurt:'Урезано выигрышей',balanceR:'Баланс BE, R / 100 сделок',above:'Выходов выше TP',msd:'Разброс месяца, п.п.',mpos:'Плюсовых месяцев, %',mworst:'Худший месяц, %',ysd:'Разброс года, п.п.',yworst:'Худший полный год, %',gap:'Net при гэпах, $'};
const rates=['freq','hit','success','saved','hurt','balanceR','above','gap'];
const SL=[4,4.25,4.5,4.75,5],TP=[3.5,4,4.5,5];
const H=[...Array.from({length:1200},(_,i)=>(i+1)/20),65,70,75,80,90,100];
const initial={g:'middle',sl:4.75,tp:3.5,tf:5,h:9.65,t:2.5,d:1.25,metric:'net',ref:'td',min:'',max:'',low:8,high:12,kind:'frequent',blockTF:'all'};
let s={...initial},ov,version=0,activeBlocks=[];
const cache=new Map();
const fmt=(v,d=1)=>v==null||!Number.isFinite(v)?'—':v.toLocaleString('ru-RU',{minimumFractionDigits:0,maximumFractionDigits:d});
const select=(id,options)=>{$(id).replaceChildren(...options.map(([k,v])=>new Option(v,k)));$(id).value=s[id]};
const opts=(a)=>a.map(x=>[x,fmt(x,2)]);
const parseHash=()=>{s={...initial};for(const [k,val] of new URLSearchParams(location.hash.slice(1))){if(!(k in s))continue;const x=typeof initial[k]==='number'?Number(val):val;if(typeof x==='number'&&!Number.isFinite(x))continue;s[k]=x}if(!families[s.g])s.g='middle';if(!SL.includes(s.sl))s.sl=4.75;if(!TP.includes(s.tp))s.tp=3.5;if(![5,15,60].includes(s.tf))s.tf=5;if(!names[s.metric])s.metric='net';if(!['td','family','front','abs'].includes(s.ref))s.ref='td'};
function normalize(){
 const tMax=s.tp-.5;s.t=Math.max(1.5,Math.min(tMax,Math.round(s.t*4)/4));s.d=Math.max(1.25,Math.min(3,s.t,Math.round(s.d*4)/4));
 s.h=H.reduce((a,b)=>Math.abs(b-s.h)<Math.abs(a-s.h)?b:a);s.low=Math.max(.05,Math.min(100,s.low));s.high=Math.max(s.low,Math.min(100,s.high));
}
const ticks=(start,end)=>Array.from({length:1+Math.round((end-start)*4)},(_,i)=>start+i/4);
function controls(){
 $('groups').innerHTML=Object.entries(families).map(([k,label])=>'<button data-g="'+k+'" class="'+(k===s.g?'on':'')+'">'+label+'</button>').join('');
 select('sl',opts(SL));select('tp',opts(TP));select('tf',[[5,'5m'],[15,'15m'],[60,'1h']]);select('metric',Object.entries(names));
 select('t',opts(ticks(1.5,s.tp-.5)));select('d',opts(ticks(1.25,Math.min(s.t,3))));
 for(const k of ['t','d'])$(k+'Buttons').innerHTML=Array.from($(k).options,o=>'<button data-param="'+k+'" data-v="'+o.value+'" aria-pressed="'+o.selected+'" class="'+(o.selected?'on':'')+'">'+o.textContent+'</button>').join('');
 for(const k of ['ref','min','max','low','high','h','kind','blockTF'])$(k).value=s[k];
 $('ref').disabled=rates.includes(s.metric);
}
async function load(sl,tp,g=s.g,tf=s.tf){
 const key=[g,sl,tp,tf].join('_');
 if(!cache.has(key))cache.set(key,(async()=>{
 const r=await fetch('maps/data/'+key+'.json.gz');if(!r.ok)throw Error(r.status+' '+key);
 const b=await r.arrayBuffer();const v=new Uint8Array(b)[0]===31?await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).json():JSON.parse(new TextDecoder().decode(b));
 return v;})().catch(e=>{cache.delete(key);throw e}));
 return cache.get(key)
}
function lookup(dat,t,d,h){
 const key=t+'/'+d, seq=dat.curves[key];if(!seq)return null;
 let lo=0,hi=seq.length;while(hi-lo>1){const m=(lo+hi)>>1;if(seq[m][0]<=h)lo=m;else hi=m}
 const row={},base={};dat.fields.forEach((k,i)=>{row[k]=seq[lo][i+1];base[k]=dat.td[key][i]});
 return {row,base};
}
function value(row,k){
 if(!row)return null;
 if(k==='per')return row.net/row.n;
 if(k==='freq')return 100*row.active/row.n;
 if(k==='hit')return row.active?100*row.be/row.active:null;
 if(k==='success')return row.be?100*row.saved/row.be:null;
 if(k==='balanceR')return 100*(row.savedR-row.hurtR)/row.n;
 return row[k]??null;
}
function reference(cell){return s.ref==='td'?cell.base:ov.refs[s.g][s.ref]}
function shown(cell){
 if(!cell)return {v:null};
 const v=value(cell.row,s.metric),f=value(cell.row,'freq'),filtered=(s.min!==''&&f<+s.min)||(s.max!==''&&f>+s.max);
 const delta=s.ref!=='abs'&&!rates.includes(s.metric);
 return {v:v==null?null:delta?v-value(reference(cell),s.metric):v,filtered};
}
function heat(id,axis,ys,xs,make,attrs){
 const values=ys.map(y=>xs.map(x=>shown(make(y,x))));
 let lo=Infinity,hi=-Infinity;for(const row of values)for(const a of row)if(a.v!=null&&!a.filtered){lo=Math.min(lo,a.v);hi=Math.max(hi,a.v)}
 const delta=s.ref!=='abs'&&!rates.includes(s.metric),sign=['dd','msd','ysd','hurt'].includes(s.metric)?-1:1;
 const precision=['net','per','gap'].includes(s.metric)?0:2;
 $(id).innerHTML='<table><thead><tr><th>'+axis+'</th>'+xs.map(x=>'<th>'+fmt(x,2)+'</th>').join('')+'</tr></thead><tbody>'+values.map((cells,i)=>'<tr><th>'+fmt(ys[i],2)+'</th>'+cells.map((c,j)=>{
  if(c.v==null)return '<td class="missing">—</td>';
  let f=delta?c.v*sign/Math.max(Math.abs(lo),Math.abs(hi),.001):((c.v-lo)/(hi-lo||1)*2-1)*sign;
  const bg=c.filtered?'#333c3e':(delta&&Math.abs(c.v)<.005?'#2e4144':'hsl('+(f>=0?145:10)+' '+(22+Math.abs(f)*20)+'% '+(20+Math.abs(f)*12)+'%)');
  const [a,match]=attrs(ys[i],xs[j]);
  return '<td data-action="'+a+'" class="'+(match?'chosen':'')+'" style="background:'+bg+'">'+fmt(c.v,precision)+'</td>'}).join('')+'</tr>').join('')+'</tbody></table>'
}
function table(id,head,rows){
 $(id).innerHTML='<table><thead><tr>'+head.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+rows.map((r,i)=>'<tr '+(id==='blocks'?'data-block="'+i+'"':id==='hits'?'data-hit="'+i+'"':'')+'>'+r.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
}
const refText={family:{wide:'Исходная 10/20',wide4:'Исходная 10/20 без лимита',narrow:'★ 3/290',middle:'★ 7/190'},front:{wide:'Фронт · ADX 1h Δ6',wide4:'Фронт · ADX 1h Δ6 · ≤4',narrow:'Фронт · ADX 5m Δ46,5',middle:'Фронт · Protected Δ9,65 + TD'}};
function inspect(cell){
 const r=cell.row,cmp=[['Protected + TD',r],['Та же TD без защиты',cell.base],[refText.family[s.g],ov.refs[s.g].family],[refText.front[s.g],ov.refs[s.g].front]];
 table('comparison',['Одиночный счёт','Net Won, $','WR, %','Max DD, %','Сделок','Худший месяц, %','Разброс месяца','Худший полный год, %','Разброс года'],cmp.map(([n,q])=>[n,...['net','wr','dd','n','mworst','msd','yworst','ysd'].map(k=>fmt(q[k],k==='net'?0:2))]));
 $('status').textContent='ΔADX '+fmt(s.h,2)+' · T '+fmt(s.t,2)+'R · D '+fmt(s.d,2)+'R. Защита '+r.active+' / '+r.n+' ('+fmt(value(r,'freq'))+'%). Выход по BE '+r.be+'; спасено '+r.saved+' ('+fmt(r.savedR,2)+'R), урезано '+r.hurt+' ('+fmt(r.hurtR,2)+'R). Выше TP '+r.above+'.';
 table('years',['Доходность, %','2021*','2022','2023','2024','2025','2026*'],cmp.map(([n,q])=>[n,...[2021,2022,2023,2024,2025,2026].map(y=>fmt(q['y'+y],2))]));
}
function panels(){
 const f=ov.freq.filter(x=>x.group===s.g&&x.sl===s.sl&&x.tp===s.tp&&x.tf===s.tf);
 table('bands',['Активации, %','Ячеек','Медиана активаций, %','Спасено / BE, %','Медиана Δ Net, $','Ячеек в плюсе, %'],f.map(q=>[q.lo+'–'+Math.min(100,q.hi),fmt(q.n,0),fmt(q.activation),fmt(q.saveShare),fmt(q.gain,0),fmt(q.positive)]));
 activeBlocks=ov.blocks.filter(x=>x.group===s.g&&x.kind===s.kind&&(s.blockTF!=='selected'||x.tf===s.tf)).sort((a,b)=>b.floorGap-a.floorGap);
 if(!activeBlocks.length){$('blocks').textContent='Блоков, удовлетворяющих этому условию, нет.';return;}
 table('blocks',['TF','SL / TP','ΔADX','T, R','D, R','Защита, %','Спасено / урезано','Net, $','Δ к TD, $','WR, %','DD, %','Минимум Δ к TD, $'],activeBlocks.map(b=>[b.tf+'m',b.sl+' / '+b.tp,fmt(b.h0,2)+'–'+fmt(b.h1,2),fmt(b.t0,2)+'–'+fmt(b.t1,2),fmt(b.d0,2)+'–'+fmt(b.d1,2),fmt(b.active),fmt(b.saved)+' / '+fmt(b.hurt),fmt(b.net,0),fmt(b.gain,0),fmt(b.wr,2),fmt(b.dd,2),fmt(b.floorGain,0)]));
}
async function draw(){
 normalize();controls();history.replaceState(null,'','#'+new URLSearchParams(s));const id=++version;const f=s.tf,g=s.g;try{
 $('status').textContent='Загрузка среза…';const dat=await load(s.sl,s.tp);if(id!==version)return;
 inspect(lookup(dat,s.t,s.d,s.h));panels();
 const ts=ticks(1.5,s.tp-.5),ds=ticks(1.25,Math.min(3,s.tp-.5));heat('tdmap','T / D',ts,ds,(t,d)=>lookup(dat,t,d,s.h),(t,d)=>['td:'+t+':'+d,t===s.t&&d===s.d]);
 heat('hmap','ΔADX / T',H.filter(h=>h>=s.low&&h<=s.high),ts,(h,t)=>lookup(dat,t,s.d,h),(h,t)=>['ht:'+h+':'+t,h===s.h&&t===s.t]);
 $('legend').textContent=s.ref!=='abs'&&!rates.includes(s.metric)?'Зелёный — улучшение выбранной метрики к ориентиру, красный — ухудшение. Для DD и разброса улучшение означает снижение. Серый — за границами фильтра; прочерк — сочетание недопустимо или доля не определена.':'Цвет показывает значения внутри каждой карты. Серый — за границами фильтра; прочерк — нет сочетания или доля не определена.';
 $('plane').textContent='Загрузка срезов…';const grid=await Promise.all(SL.map(sl=>Promise.all(TP.map(tp=>load(sl,tp)))));if(id!==version||f!==s.tf||g!==s.g)return;
 heat('plane','SL / TP',SL,TP,(sl,tp)=>lookup(grid[SL.indexOf(sl)][TP.indexOf(tp)],s.t,s.d,s.h),(sl,tp)=>['plane:'+sl+':'+tp,sl===s.sl&&tp===s.tp]);
 }catch(e){if(id===version)$('status').textContent='Ошибка загрузки данных: '+e.message}
}
function pickBlock(b){Object.assign(s,{sl:b.sl,tp:b.tp,tf:b.tf,h:Math.round((b.h0+b.h1)*10)/20,t:b.t0,d:b.d0,low:Math.max(.05,b.h0-1),high:b.h1+1})}
$('groups').onclick=e=>{const g=e.target.dataset.g;if(!g)return;searchId++;$('hits').innerHTML='';$('found').textContent='';s.g=g;const b=ov.blocks.filter(b=>b.group===g&&b.kind==='frequent').sort((a,b)=>b.floorGap-a.floorGap)[0];if(b)pickBlock(b);draw()};
$('blocks').onclick=e=>{const tr=e.target.closest('tr[data-block]');if(tr){pickBlock(activeBlocks[+tr.dataset.block]);draw();$('comparison').scrollIntoView({block:'center'})}};
for(const k of ['tdmap','plane','hmap'])$(k).onclick=e=>{const td=e.target.closest('[data-action]');if(!td)return;const [type,a,b]=td.dataset.action.split(':');if(type==='td'){s.t=+a;s.d=+b}else if(type==='plane'){s.sl=+a;s.tp=+b}else{s.h=+a;s.t=+b}draw()};
for(const k of ['sl','tp','tf','t','d','h','low','high','min','max','ref','metric','kind','blockTF'])$(k).onchange=()=>{s[k]=typeof initial[k]==='number'?+$(k).value:$(k).value;draw()};
$('clear').onclick=()=>{s.min='';s.max='';draw()};$('all').onclick=()=>{s.low=.05;s.high=100;draw()};
window.onhashchange=()=>{parseHash();draw()};
(async()=>{try{const res=await fetch('maps/overview.json');if(!res.ok)throw Error(res.status);ov=await res.json();const band=await (await fetch('maps/band.json')).json();table('bandinfo',['Стратегия','Защита / все, %','Спасено / BE, %','Спасено / все, %','Урезано / все, %','Медиана Δ Net, $','Плоскостей в плюсе'],Object.entries(band).map(([g,r])=>[families[g],fmt(r.active),fmt(r.success),fmt(r.saved),fmt(r.hurt),fmt(r.gain,0),r.positive+' / '+r.planes]));parseHash();await draw()}catch(e){$('status').textContent=e.message}})();
let searchId=0,foundRows=[];
const hPos=new Map(H.map((v,i)=>[v,i]));
async function search(){
 const run=++searchId,g=s.g;const lower=id=>$(id).value===''?-Infinity:+$(id).value,upper=id=>$(id).value===''?Infinity:+$(id).value;
 const netFloor=lower('netFloor'),wrFloor=lower('wrFloor'),ddLimit=upper('ddLimit'),amin=lower('min'),amax=upper('max');
 const mode=$('rank').value;let top=[],count=0,ranges=0;
 $('found').textContent='Поиск…';$('hits').innerHTML='';
 for(const tf of [5,15,60]){
  const layers=await Promise.all(SL.flatMap(sl=>TP.map(async tp=>[sl,tp,await load(sl,tp,g,tf)])));
  if(run!==searchId||s.g!==g)return;
  for(const [sl,tp,v] of layers)for(const [key,seq] of Object.entries(v.curves)){
   const [t,d]=key.split('/').map(Number),I=v.fields.reduce((m,k,i)=>(m[k]=i+1,m),{}),base=v.td[key][I.net-1];
   for(let i=0;i<seq.length;i++){
    const x=seq[i],net=x[I.net],wr=x[I.wr],dd=x[I.dd],activation=100*x[I.active]/x[I.n];
    if(net<netFloor||wr<wrFloor||dd>ddLimit||activation<amin||activation>amax)continue;
    const score=({net,gain:net-base,gap:x[I.gap],sd:-x[I.msd],floor:x[I.yworst]})[mode];
    const start=hPos.get(x[0]),end=i+1===seq.length?H.length-1:hPos.get(seq[i+1][0])-1;
    count+=end-start+1;ranges++;
    if(top.length===50&&score<=top[49].score)continue;
    const row={sl,tp,t,d,tf,h0:H[start],h1:H[end],score,net,wr,dd,active:activation,gain:net-base,msd:x[I.msd],yworst:x[I.yworst]};
    top.push(row);top.sort((a,b)=>b.score-a.score);if(top.length>50)top.pop();
   }
  }
 }
 if(run!==searchId||s.g!==g)return;foundRows=top;
 $('found').textContent='Подходят '+fmt(count,0)+' ячеек, '+fmt(ranges,0)+' диапазонов. Показано '+top.length+'.';
 table('hits',['TF','SL / TP','T / D','Диапазон ΔADX','Net, $','Δ к TD, $','WR, %','DD, %','Защита, %','Разброс месяца','Худший год, %'],top.map(b=>[b.tf+'m',b.sl+' / '+b.tp,b.t+' / '+b.d,fmt(b.h0,2)+'–'+fmt(b.h1,2),fmt(b.net,0),fmt(b.gain,0),fmt(b.wr,2),fmt(b.dd,2),fmt(b.active),fmt(b.msd,2),fmt(b.yworst,2)]));
}
$('find').onclick=()=>search().catch(e=>{$('found').textContent=e.message});
$('hits').onclick=e=>{const tr=e.target.closest('tr[data-hit]');if(!tr)return;const b=foundRows[+tr.dataset.hit];Object.assign(s,{sl:b.sl,tp:b.tp,tf:b.tf,t:b.t,d:b.d,h:b.h0,low:Math.max(.05,b.h0-1),high:Math.min(100,b.h0+1)});draw();$('comparison').scrollIntoView({block:'center'})};

for(const k of ['t','d'])$(k+'Buttons').onclick=e=>{if(e.target.dataset.param===k){s[k]=+e.target.dataset.v;draw()}};
