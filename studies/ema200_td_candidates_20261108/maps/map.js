const $ = id => document.getElementById(id);
const assets = ['btc','eth','sol'];
const widths = Array.from({length:12},(_,i)=>3+i);
const lbs = Array.from({length:29},(_,i)=>20+i*10);
const distances = Array.from({length:12},(_,i)=>(i+1)/4);
const metrics = {net:'Net Won, $',wr:'Win rate, %',n:'Число сделок',dd:'Max DD, %',armed:'Активации TD',pf:'Profit factor',year:'Худший полный год, %',avg:'Net Won на сделку, $'};
const factors = [100,1000,1,1000,1,1000,1000];
const filters = [
  ['netMin','Net Won от, $'],['netMax','Net Won до, $'],['wrMin','WR от, %'],['ddMax','DD до, %'],
  ['nMin','Сделки от'],['armedMin','Активации от'],['pfMin','PF от'],['yearMin','Худший год от, %'],
  ['wMin','Ширина от'],['wMax','Ширина до'],['lbMin','Лукбэк от'],['lbMax','Лукбэк до'],
  ['tMin','T от, R'],['tMax','T до, R'],['dMin','D от, R'],['dMax','D до, R']
];
const defaults={coin:'btc',sl:4.75,tp:5,cap:0,w:9,lb:30,t:3.5,d:1.25,metric:'net',delta:0,scope:'cell',numbers:1,mode:'fixed'};
const state={};
function parseState(){
 const qs=new URLSearchParams(location.hash.slice(1)); Object.assign(state,defaults);
for(const [k,v] of Object.entries(defaults))if(qs.has(k)){
  if(typeof v==='string')state[k]=qs.get(k);else if(qs.get(k)!==''&&Number.isFinite(+qs.get(k)))state[k]=+qs.get(k);
}
if(!assets.includes(state.coin))state.coin='btc';
if(!(state.metric in metrics))state.metric='net';
if(!widths.includes(state.w))state.w=9;
if(!lbs.includes(state.lb))state.lb=30;
if(![0,1,2,3].includes(state.cap))state.cap=0;
if(state.scope!=='local')state.scope='cell';
if(state.mode!=='best')state.mode='fixed';
 for(const [id] of filters)state[id]=qs.get(id)?.trim()&&Number.isFinite(+qs.get(id))?+qs.get(id):null;
}
parseState();
const fmt=(n,d=1)=>Number.isFinite(n)?n.toLocaleString('ru-RU',{maximumFractionDigits:d}):'—';
const cash=(n)=>fmt(n,0);
const axis=n=>fmt(n,2);
const choice=(items,v)=>items.map(i=>'<option value="'+i+'"'+(i===v?' selected':'')+'>'+axis(i)+'</option>').join('');
function range(v,min,max){return (min===null||v>=min)&&(max===null||v<=max)}
function geomId(w,lb){return (w-3)*29+(lb-20)/10}
function median(xs){xs=xs.filter(Number.isFinite).sort((a,b)=>a-b);const m=xs.length>>1;return !xs.length?NaN:xs.length%2?xs[m]:(xs[m]+xs[m-1])/2}
function url(){const p=new URLSearchParams();for(const [k,v] of Object.entries(state))if(v!==null)p.set(k,String(v));history.replaceState(null,'','#'+p)}
for(const [id,title] of filters){
  const label=document.createElement('label');label.textContent=title;
  const input=document.createElement('input');input.type='number';input.step='any';input.id=id;input.placeholder='Любое';
  if(state[id]!==null)input.value=state[id];input.oninput=()=>{state[id]=input.value===''?null:input.valueAsNumber;changed()};
  label.append(input);$('filters').append(label);
}
$('metric').innerHTML=Object.entries(metrics).map(([k,v])=>'<option value="'+k+'">'+v+'</option>').join('');
for(const k of ['coin','cap','metric','delta','scope','mode'])$(k).value=state[k];$('numbers').checked=Boolean(state.numbers);

let layers=[], active=null, cube=null, serial=0, crossSerial=0;
const indices=new Map(), cache=new Map(), busy=new Map();
function status(text,error=false){$('status').innerText=text;$('status').classList.toggle('error',error)}
function file(asset,layer,cap){return 'data/'+asset+'/'+layer.key+'_'+cap+'.gz'}
async function fetchPlane(asset,layer,cap){
  const path=file(asset,layer,cap);
  if(cache.has(path)){const a=cache.get(path);cache.delete(path);cache.set(path,a);return a}
  if(busy.has(path))return busy.get(path);
  const job=(async()=>{
    const res=await fetch(path);if(!res.ok)throw Error(path+' · HTTP '+res.status);
    const bytes=new Uint8Array(await new Response(res.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
    const len=layer.coords.length*7*348;
    if(bytes.length!==len*4)throw Error('Неверная длина среза '+path);
    const out=new Float32Array(len);
    for(let group=0;group<len/348;group++){
      let prev=0;const scale=factors[group%7];
      for(let k=group*348;k<(group+1)*348;k++){
        prev=(prev+(bytes[k]|(bytes[k+len]<<8)|(bytes[k+2*len]<<16)|(bytes[k+3*len]<<24)))|0;
        out[k]=prev===-2147483648?NaN:prev/scale;
      }
    }
    cache.set(path,out);if(cache.size>12)cache.delete(cache.keys().next().value);
    return out;
  })();busy.set(path,job);try{return await job}finally{busy.delete(path)}
}
function read(arr,i,g,key){
  if(key==='avg'){const n=read(arr,i,g,'n');return n?read(arr,i,g,'net')/n:NaN}
  const f={net:0,wr:1,n:2,dd:3,armed:4,pf:5,year:6}[key];return arr[(i*7+f)*348+g];
}
const neighborhoods=Array.from({length:348},(_,g)=>{
  const w=widths[Math.floor(g/29)],l=lbs[g%29];
  return widths.filter(x=>Math.abs(w-x)<=1).flatMap(x=>lbs.filter(y=>Math.abs(l-y)<=10).map(y=>geomId(x,y)));
});
function viewValue(a,i,g,k,diff=false){
  const value=id=>{const v=read(a,i,id,k);return diff?(v-read(a,0,id,k))*(k==='dd'?-1:1):v};
  return state.scope==='local'?median(neighborhoods[g].map(value)):value(g);
}
function displayed(a,i,g){return viewValue(a,i,g,state.metric,Boolean(state.delta))}
function rowAllowed(a,i,g){
  const rules=[['net',state.netMin,state.netMax],['wr',state.wrMin,null],['dd',null,state.ddMax],
               ['n',state.nMin,null],['armed',state.armedMin,null],['pf',state.pfMin,null],['year',state.yearMin,null]];
  return rules.every(([key,lo,hi])=>(lo===null&&hi===null)||range(viewValue(a,i,g,key),lo,hi));
}
function geomAllowed(w,lb){return range(w,state.wMin,state.wMax)&&range(lb,state.lbMin,state.lbMax)}
function tdAllowed(t,d){return !t||range(t,state.tMin,state.tMax)&&range(d,state.dMin,state.dMax)}
function better(x,y){return state.metric==='dd'&&!state.delta?x<y:x>y}
function coord(layer,t,d){return layer.coords.findIndex(([a,b])=>a===t&&b===d)}
function make(a,i,g,key,tip,allowed=true){
  const value=displayed(a,i,g);
  return {key,value,ok:allowed&&rowAllowed(a,i,g)&&Number.isFinite(value),
    tip:tip+'\n'+metrics[state.metric]+(state.delta?' · Δ':'')+' '+fmt(value,2)+'\nЦентр · Net $'+cash(read(a,i,g,'net'))+' · WR '+fmt(read(a,i,g,'wr'))+'% · DD '+fmt(read(a,i,g,'dd'))+'% · N '+fmt(read(a,i,g,'n'),0)};
}
function bounds(grids){let lo=Infinity,hi=-Infinity;for(const grid of grids)for(const row of grid)for(const c of row)if(c?.ok){lo=Math.min(lo,c.value);hi=Math.max(hi,c.value)}
 if(!Number.isFinite(lo))return null;
 if(state.delta){const m=Math.max(Math.abs(lo),Math.abs(hi));return [-m,m]}
 return [lo,hi]}
function paint(v,scale){
  let k=scale&&scale[1]>scale[0]?(v-scale[0])/(scale[1]-scale[0]):.5;
  if(state.metric==='dd'&&!state.delta)k=1-k;
  k=Math.max(0,Math.min(1,k));const ends=k>.5?[[231,227,205],[65,131,106]]:[[152,94,64],[231,227,205]];
  const p=k>.5?2*(k-.5):2*k;return 'rgb('+ends[0].map((v,i)=>Math.round(v+(ends[1][i]-v)*p)).join(',')+')';
}
function compact(v){if(!Number.isFinite(v))return '—';if(state.metric==='net'&&Math.abs(v)>=1000)return fmt(v/1000,1)+'k';return fmt(v,['n','armed','avg','net'].includes(state.metric)?0:1)}
function heat(target,cols,ys,grid,scale,selected,corner,minsize){
  const head='<thead><tr><th>'+corner+'</th>'+cols.map(v=>'<th>'+axis(v)+'</th>').join('')+'</tr></thead>';
  const lines=grid.map((r,i)=>'<tr><th>'+axis(ys[i])+'</th>'+r.map(c=>{
    if(c?.filtered)return '<td><span class="excluded" title="Ни одна TD не прошла фильтры">—</span></td>';
    if(!c)return '<td><span class="void" title="Комбинация отсутствует"></span></td>';
    const style=c.ok?'background:'+paint(c.value,scale)+';color:#16221c':'background:#586469;color:#d6dcdb';
    return '<td><button type="button" data-key="'+c.key+'" aria-pressed="'+(c.key===selected)+'" style="'+style+'" title="'+c.tip+(c.ok?'':' · вне фильтра или метрика отсутствует')+'" aria-label="'+c.tip+'">'+(state.numbers?compact(c.value):'')+(c.caption?'<small>'+c.caption+'</small>':'')+'</button></td>';
  }).join('')+'</tr>').join('');
  target.innerHTML='<table class="heat" style="--min:'+minsize+'px">'+head+'<tbody>'+lines+'</tbody></table>';
}
function annotate(grid){let n=0,m=0;for(const r of grid)for(const v of r)if(v){m++;if(v.ok)n++}return n+' из '+m}
function validOpts(){const sls=[...new Set(layers.map(x=>x.sl))];
 if(!sls.includes(state.sl))state.sl=sls.reduce((a,b)=>Math.abs(b-state.sl)<Math.abs(a-state.sl)?b:a);
 const tps=layers.filter(x=>x.sl===state.sl).map(x=>x.tp);if(!tps.includes(state.tp))state.tp=tps.reduce((a,b)=>Math.abs(b-state.tp)<Math.abs(a-state.tp)?b:a);
 $('sl').innerHTML=choice(sls,state.sl);$('tp').innerHTML=choice(tps,state.tp);return layers.find(x=>x.sl===state.sl&&x.tp===state.tp);
}
async function load(){
  const ticket=++serial;crossSerial++;active=null;cube=null;$('compare').disabled=true;
  for(const id of ['geometry','td','selection','layers','crossStatus','scale','ginfo','tinfo'])$(id).replaceChildren();
  status('Загружается выбранный срез…');
  try{
    const asset=state.coin;
    if(!indices.has(asset)){const r=await fetch('data/'+asset+'/index.json');if(!r.ok)throw Error('Нет индекса '+asset);indices.set(asset,await r.json())}
    if(ticket!==serial)return;
    layers=indices.get(asset);const l=validOpts();
    if(coord(l,state.t,state.d)<0){
      const ts=[...new Set(l.coords.map(c=>c[0]))].filter(v=>v>0);
      state.t=ts.reduce((a,b)=>Math.abs(b-state.t)<Math.abs(a-state.t)?b:a);
      const ds=l.coords.filter(c=>c[0]===state.t).map(c=>c[1]);state.d=ds.reduce((a,b)=>Math.abs(b-state.d)<Math.abs(a-state.d)?b:a);
    }
    const a=await fetchPlane(asset,l,state.cap);if(ticket!==serial)return;
    active=l;cube=a;$('compare').disabled=false;changed();
  }catch(e){if(ticket===serial)status('Не удалось загрузить срез. '+e.message,true)}
}
function draw(){
  if(!cube)return;
  const wlist=widths.filter(w=>range(w,state.wMin,state.wMax)),llist=lbs.filter(l=>range(l,state.lbMin,state.lbMax));
  const ts=[...new Set(active.coords.slice(1).map(c=>c[0]))].filter(t=>range(t,state.tMin,state.tMax));
  const ds=distances.filter(d=>range(d,state.dMin,state.dMax));
  const i=coord(active,state.t,state.d),g=geomId(state.w,state.lb);
  const grid=wlist.map(w=>llist.map(lb=>make(cube,i,geomId(w,lb),w+':'+lb,'Ширина '+w+' · лукбэк '+lb,tdAllowed(state.t,state.d))));
  const tgrid=ds.map(d=>ts.map(t=>{const ix=coord(active,t,d);return ix<0?null:make(cube,ix,g,t+':'+d,'T '+t+'R · D '+d+'R',geomAllowed(state.w,state.lb))}));
  const scale=bounds([grid,tgrid]);
  heat($('geometry'),llist,wlist,grid,scale,state.w+':'+state.lb,'W / LB',Math.max(210,(llist.length+1)*24));
  heat($('td'),ts,ds,tgrid,scale,state.t+':'+state.d,'D / T',Math.max(210,(ts.length+1)*30));
  const tdText=state.t?'T '+axis(state.t)+'R · D '+axis(state.d)+'R':'Без TD';
  $('ginfo').textContent=tdText+' · проходит '+annotate(grid)+'. Клик выбирает геометрию.';
  $('tinfo').textContent='Ширина '+state.w+' · лукбэк '+state.lb+' · проходит '+annotate(tgrid)+'. Клик выбирает TD.';
  const reverse=state.metric==='dd'&&!state.delta;
  $('scale').innerHTML=scale?fmt(scale[reverse?1:0],2)+' <em></em> '+fmt(scale[reverse?0:1],2):'Нет подходящих значений';
  const stats=[['Net Won, $',cash(read(cube,i,g,'net'))],['Без TD, $',cash(read(cube,0,g,'net'))],['Δ Net Won, $',cash(read(cube,i,g,'net')-read(cube,0,g,'net'))],['WR',fmt(read(cube,i,g,'wr'))+'%'],['Max DD',fmt(read(cube,i,g,'dd'))+'%'],['Сделок',read(cube,i,g,'n')],['Активаций TD',read(cube,i,g,'armed')],['PF',fmt(read(cube,i,g,'pf'),2)]];
  const ns=widths.filter(w=>Math.abs(w-state.w)<=1).flatMap(w=>lbs.filter(l=>Math.abs(l-state.lb)<=10).map(l=>read(cube,i,geomId(w,l),'net')));
  stats.push(['Медиана Net 3×3, $',cash(median(ns))],['Худший полный год',fmt(read(cube,i,g,'year'))+'%']);
  $('selection').innerHTML='<h2>'+state.coin.toUpperCase()+' · ширина '+state.w+' · лукбэк '+state.lb+' · '+tdText+'</h2><div class="stats">'+stats.map(([a,b])=>'<span>'+a+'<strong>'+b+'</strong></span>').join('')+'</div>';
  const visible=rowAllowed(cube,i,g)&&geomAllowed(state.w,state.lb)&&tdAllowed(state.t,state.d);
  status(visible?'Выбрано · SL '+axis(state.sl)+' ATR · TP '+axis(state.tp)+'R':'Выбранная ячейка вне фильтров · её значения сохранены в карточке.');
}
window.addEventListener('hashchange',()=>{
 parseState();
 for(const k of ['coin','cap','metric','delta','scope','mode'])$(k).value=state[k];
 for(const [k] of filters)$(k).value=state[k]??'';
 $('numbers').checked=Boolean(state.numbers);load();
});
function changed(){crossSerial++;$('layers').replaceChildren();$('crossStatus').textContent='';draw();url()}
for(const id of ['coin','sl','tp','cap','metric','delta','scope','numbers','mode']){
 $(id).onchange=()=>{state[id]=id==='numbers'?Number($(id).checked):typeof defaults[id]==='number'?+$(id).value:$(id).value;
 if(['coin','sl','tp','cap'].includes(id))load();else changed()};
}
function setFilters(values){for(const [k,v] of Object.entries(values)){state[k]=v;$(k).value=v??''}}
$('reset').onclick=()=>{setFilters(Object.fromEntries(filters.map(([k])=>[k,null])));changed()};
$('band').onclick=()=>{setFilters({netMin:20000,netMax:22000});changed()};
$('zone').onclick=()=>{setFilters({wMin:8,wMax:9,lbMin:20,lbMax:40});state.w=9;state.lb=30;
 if(state.coin!=='btc'){state.coin='btc';$('coin').value='btc';load()}else changed()};
$('off').onclick=()=>{state.t=0;state.d=0;changed()};
for(const id of ['geometry','td'])$(id).onclick=e=>{
 const btn=e.target.closest('button[data-key]');if(!btn)return;const [x,y]=btn.dataset.key.split(':').map(Number);
 if(id==='geometry'){state.w=x;state.lb=y}else{state.t=x;state.d=y}changed();
};
async function compare(){
 if(!active)return;
 const version=++crossSerial,asset=state.coin,g=geomId(state.w,state.lb);
 $('layers').replaceChildren();$('crossStatus').textContent='Чтение срезов…';
 const outcomes=new Map();let next=0,done=0;
 async function worker(){
  while(version===crossSerial&&next<layers.length){
    const l=layers[next++],a=await fetchPlane(asset,l,state.cap);
    if(version!==crossSerial)return;
    let pick=null;
    const inspect=i=>{
      if(i<0)return;const [t,d]=l.coords[i],k=l.key+':'+t+':'+d;
      const v=make(a,i,g,k,'SL '+l.sl+' · TP '+l.tp+' · T '+t+' · D '+d,tdAllowed(t,d)&&geomAllowed(state.w,state.lb));
      if(state.mode==='fixed'||v.ok&&(!pick||better(v.value,pick.value)))pick=v;
    };
    if(state.mode==='fixed')inspect(coord(l,state.t,state.d));
    else for(let i=1;i<l.coords.length;i++)inspect(i);
    if(pick&&state.mode==='best')pick.caption=pick.key.split(':').slice(1).map(x=>axis(+x)).join(' / ');
    outcomes.set(l.key,pick??(state.mode==='best'?{filtered:true}:null));$('crossStatus').textContent=++done+' / '+layers.length+' срезов';
  }
 }
 try{await Promise.all([worker(),worker(),worker()]);if(version!==crossSerial)return;
  const sls=[...new Set(layers.map(l=>l.sl))],tps=[...new Set(layers.map(l=>l.tp))].sort((a,b)=>a-b);
  const grid=sls.map(sl=>tps.map(tp=>outcomes.get(sl+'_'+tp)||null));
  const scale=bounds([grid]);
  heat($('layers'),tps,sls,grid,scale,active.key+':'+state.t+':'+state.d,'SL / TP',450);
  $('crossStatus').textContent='Проходит '+annotate(grid)+' · шкала этой карты '+(scale?fmt(scale[0],2)+' … '+fmt(scale[1],2):'—');
 }catch(e){if(version===crossSerial)$('crossStatus').textContent='Ошибка загрузки: '+e.message}
}
$('compare').onclick=compare;
$('layers').onclick=e=>{const b=e.target.closest('button[data-key]');if(!b)return;
 const [k,t,d]=b.dataset.key.split(':'),l=layers.find(x=>x.key===k);Object.assign(state,{sl:l.sl,tp:l.tp,t:+t,d:+d});load()};
load();

const tip=document.createElement('div');tip.className='tip';tip.hidden=true;document.body.append(tip);
for(const id of ['geometry','td','layers']){
  const el=$(id);
  el.addEventListener('pointermove',e=>{
    const cell=e.target.closest('button[data-key]');if(!cell){tip.hidden=true;return}
    tip.textContent=cell.getAttribute('aria-label');tip.hidden=false;
    tip.style.left=Math.max(4,Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8))+'px';
    tip.style.top=(e.clientY+tip.offsetHeight+18>innerHeight?e.clientY-tip.offsetHeight-8:e.clientY+14)+'px';
  });
  el.addEventListener('pointerleave',()=>tip.hidden=true);el.addEventListener('click',()=>tip.hidden=true);
}
