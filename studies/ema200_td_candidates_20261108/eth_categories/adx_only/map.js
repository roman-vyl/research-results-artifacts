const el=id=>document.getElementById(id);
const presets=[
 ['grid_3_290_5_tp5.csv.gz',15,26.75,1.5,23,31],
 ['grid_3_290_5_tp5.csv.gz',60,1.5,3,0,8],
 ['grid_3_290_5_tp5.csv.gz',60,5,3,0,10],
 ['grid_3_290_4.75.csv.gz',5,46.5,1.75,42,51],
 ['grid_3_290_4.75.csv.gz',15,26,1.75,22,30]
];
const metrics={net:'Net Won, $',delta:'Δ Net Won, $',wr:'WR, %',dd:'Max DD, %',act:'Активации',above:'Выше TP',quick:'Выход ≤1 ч',sd_month:'Разброс месяцев, %',hold:'Медиана удержания, ч'};
let state=[],cut,d,token=0;const cache=new Map();
const fmt=(x,k=2)=>x==null?'—':x.toLocaleString('ru-RU',{maximumFractionDigits:k});
function val(row,m){return m==='delta'?row.net-state[0].net:row[m]}
function draw(){
 const tf=+el('tf').value, lo=+el('lo').value,hi=+el('hi').value,m=el('metric').value;
 const subset=state.filter(x=>x.tf===tf&&x.cut>=lo&&x.cut<=hi),distances=[...new Set(subset.map(x=>x.d))];
 const finite=subset.map(x=>val(x,m)).filter(Number.isFinite);const min=Math.min(...finite),max=Math.max(...finite);
 let html='<thead><tr><th>ΔADX / D</th>'+distances.map(y=>'<th>'+fmt(y)+'R</th>').join('')+'</tr></thead><tbody>';
 const lines=new Map();for(const r of subset){if(!lines.has(r.cut))lines.set(r.cut,[]);lines.get(r.cut).push(r)}
 for(const [h,rows] of lines){html+='<tr><td>'+fmt(h)+'</td>';for(const r of rows){let v=val(r,m),s=(v-min)/(max-min||1);if(['dd','quick','sd_month'].includes(m))s=1-s;const bg=v==null?'white':'hsl('+Math.round(22+116*s)+' 43% 88%)';html+='<td data-cut="'+h+'" data-d="'+r.d+'" class="'+(cut===h&&d===r.d?'chosen':'')+'" style="background:'+bg+'">'+fmt(v,['net','delta'].includes(m)?0:2)+'</td>'}html+='</tr>'}
 el('map').innerHTML=html+'</tbody>';const r=subset.find(x=>x.cut===cut&&x.d===d)||subset[0];el('info').textContent='Строк порога: '+lines.size+'. Цвет сравнивает значения выбранной метрики в видимой области.';if(!r){el('detail').textContent='Порог вне сетки.';el('years').innerHTML='';return}cut=r.cut;d=r.d;
 const base=state[0];el('detail').textContent='ΔADX '+fmt(cut)+' · D '+fmt(d)+'R · Net Won $'+fmt(r.net,0)+' (без раннера $'+fmt(base.net,0)+') · WR '+fmt(r.wr)+'% · DD '+fmt(r.dd)+'% · активаций '+r.act+' / '+r.n+' · выше TP '+r.above+' (с 2025 года '+r.late_above+') · медиана сверх TP '+fmt(r.median_extra)+'R · выход ≤1 ч '+r.quick+' · медиана удержания '+fmt(r.hold)+' ч · от 7 суток '+r.days7;
 let keys=['y2021','y2022','y2023','y2024','y2025','y2026','net_long','net_short','sd_month'];el('years').innerHTML='<tr><th>Выход</th>'+['2021','2022','2023','2024','2025','2026','Long, $','Short, $','σ месяца, %'].map(x=>'<th>'+x+'</th>').join('')+'</tr>'+[base,r].map((x,i)=>'<tr><td>'+['Исходный','ADX'][i]+'</td>'+keys.map(k=>'<td>'+fmt(x[k],k.startsWith('net')?0:1)+'</td>').join('')+'</tr>').join('');
}
async function loadFile(){let file=el('file').value,id=++token;el('detail').textContent='Загрузка…';try{
 if(!cache.has(file)){const response=await fetch(file);if(!response.ok)throw Error('HTTP '+response.status);let buf=await response.arrayBuffer();const raw=new Uint8Array(buf);let csv=raw[0]===31&&raw[1]===139?await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(buf);
 let [header,...rows]=csv.trim().split(/\r?\n/);let names=header.split(',');cache.set(file,rows.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[names[i],v===''?null:+v]))))}
 if(id===token){state=cache.get(file);el('get').href=file;draw()}}catch(e){if(id===token)el('detail').textContent='Ошибка загрузки: '+e.message}}
function preset(i){const [f,tf,h,y,lo,hi]=presets[i];el('file').value=f;el('tf').value=tf;cut=h;d=y;el('lo').value=lo;el('hi').value=hi;loadFile()}
el('presets').onclick=e=>{if(e.target.dataset.i!=null)preset(+e.target.dataset.i)};
el('map').onclick=e=>{if(e.target.dataset.d){cut=+e.target.dataset.cut;d=+e.target.dataset.d;draw()}};
el('file').onchange=loadFile;for(const id of ['tf','metric','lo','hi'])el(id).onchange=draw;
el('all').onclick=()=>{el('lo').value=0;el('hi').value=100;draw()};
for(const [k,v] of Object.entries(metrics))el('metric').add(new Option(v,k));
fetch('files.json').then(x=>x.json()).then(files=>{for(const f of files){const [,w,lb,sl,tp]=f.replace('.csv.gz','').split('_');el('file').add(new Option(w+'/'+lb+' · SL '+sl+' · TP '+(tp?tp.slice(2):'4.5'),f))}preset(0)}).catch(()=>el('detail').textContent='Список поверхностей не загрузился.');
