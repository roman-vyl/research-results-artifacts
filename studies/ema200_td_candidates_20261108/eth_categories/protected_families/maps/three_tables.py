"""Format saved baseline rows and saved protected-surface metrics; no strategy replay."""
from pathlib import Path
from html import escape
import json,gzip,csv
P=Path(__file__).resolve().parent
BASE=Path.home()/'BBB_data/research/analysis/ETHUSDT.P/ema200/w8_or_sp109_no_spot_5d/runs.csv'
with BASE.open() as f:plain=[r for r in csv.DictReader(f) if r['w8_or_sp109']=='1' and not r['touch_max'] and float(r['tp_sl_ratio'])>=3.5]
labels={'wide':'Широкий стек · короткий лукбэк','narrow':'Узкий стек · длинный лукбэк','middle':'Средний стек · длинный лукбэк'}
ranges={'wide':(9,14,20,60),'narrow':(3,5,220,300),'middle':(5,8,100,200)}
coords={'wide':'11/20','narrow':'5/280','middle':'7/170'}
head=['Этап','Вход · SL / TP','T / D, R','ΔADX 5m','Сделки','Net Won, $','WR, %','Max DD, %','Защита, %','Спасено / урезано','Худший месяц, %','Худший полный год, %']
def fmt(x,n=2):return f'{x:,.{n}f}'.replace(',',' ').replace('.',',')
html=['''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ETH · три семейства: исходная → TD → Protected</title><link rel="stylesheet" href="ui.css"><main><header><a href="../index.html">← Интерактивные поверхности</a><h1>Три семейства ETH</h1><p>Одиночный счёт $10 000. Все касания, W8 OR SP109 без SPOT. Исходная строка — максимум Net Won в сохранённой сетке семейства при TP ≥ 3,5R. Для TD показаны три расстояния: 1,25R, 2R и 3R. В каждой группе расстояний выбран вариант с наибольшим минимумом Net Won при трёх порогах 5m: 8, 10 и 12. Пороговый набор — проверка чувствительности вокруг 10. Особые условия отбора: для D 1,25 триггер 1,50–2,75, для D 2 триггер 2,75–3,50, для D 3 триггер 3,50–4,50. Внутри сравнения TD и BE параметры входа и TD одинаковы.</p></header>''']
bridge = [('wide',11,20,5,4.5,3.5,2),('wide',11,20,5,4.5,3.75,2.5),('narrow',5,280,4.5,5,2.75,1.25),('middle',7,170,4.75,3.5,2.5,1.25)]
html.append('<section id="absolute"><h2>Что заработали относительно исходного лидера семейства</h2><p>Net Won одиночного счёта на каждом этапе, в долларах. Сравнение первых двух столбцов включает смену входа и SL/TP. Далее вход и SL/TP фиксированы.</p><div class="wrap"><table><tr><th>Кандидат · T / D</th><th>Исходный лидер</th><th>Кандидат без TD</th><th>Только TD</th><th>TD + BE (5m Δ10)</th><th>Δ к лидеру</th></tr>')
for g,w,lb,sl,tp,t,d in bridge:
 w0,w1,l0,l1=ranges[g]
 leader=max(float(r['net_pnl']) for r in plain if w0<=float(r['min_current_width_atr'])<=w1 and l0<=float(r['untouched_lookback'])<=l1)
 no=next(float(r['net_pnl']) for r in plain if [float(r[k]) for k in ['min_current_width_atr','untouched_lookback','sl_atr_multiplier','tp_sl_ratio']]==[w,lb,sl,tp])
 z=json.load(gzip.open(P/'data'/f'{g}_{sl:g}_{tp:g}_5.json.gz'));key=f'{t:g}/{d:g}';ix=z['fields'].index('net')
 td=z['td'][key][ix];be=next(r[1+ix] for r in reversed(z['curves'][key]) if r[0]<=10)
 html.append('<tr><td>'+f'{w}/{lb} · {t:g}/{d:g}'+'</td>'+''.join('<td>'+fmt(v,0)+'</td>' for v in [leader,no,td,be,be-leader])+'</tr>')
html.append('</table></div></section>')
for g in labels:
 w0,w1,l0,l1=ranges[g];baseline=max((r for r in plain if w0<=float(r['min_current_width_atr'])<=w1 and l0<=float(r['untouched_lookback'])<=l1),key=lambda r:float(r['net_pnl']))
 a=[['Исходная',f"{baseline['min_current_width_atr']}/{baseline['untouched_lookback']} · {baseline['sl_atr_multiplier']}/{baseline['tp_sl_ratio']}",'—','—',baseline['realised_trade_count'],fmt(float(baseline['net_pnl']),0),fmt(100*float(baseline['win_rate'])),fmt(-100*float(baseline['max_drawdown_mtm_pct'])),'—','—','—','—']]
 variants=[[],[],[]]
 for f in (P/'data').glob(g+'_*_5.json.gz'):
  _,sl,tp,_=f.name.split('_');z=json.load(gzip.open(f))
  for key,seq in z['curves'].items():
   t,d=map(float,key.split('/'));i=0 if d==1.25 and 1.5<=t<=2.75 else 1 if d==2 and 2.75<=t<=3.5 else 2 if d==3 and 3.5<=t<=4.5 else None
   if i is None:continue
   b=dict(zip(z['fields'],z['td'][key]));v=[dict(zip(z['fields'],next(r[1:] for r in reversed(seq) if r[0]<=h))) for h in [8,10,12]]
   variants[i].append((min(q['net'] for q in v),sl,tp,t,d,b,v))
 for group in variants:
  _,sl,tp,t,d,b,v=max(group,key=lambda r:r[0])
  for h,q in zip([0,8,10,12],[b,*v]):
   link=f'../index.html#g={g}&sl={sl}&tp={tp}&tf=5&t={t}&d={d}&h={h or 10}&ref=td&metric=net&low=8&high=12'
   a.append([('Чистая TD' if not h else 'TD + BE'),f'{coords[g]} · {sl}/{tp}',f'<a href="{link}">{t:g} / {d:g}</a>',h or '—',int(q['n']),fmt(q['net'],0),fmt(q['wr']),fmt(q['dd']),fmt(100*q['active']/q['n'],1) if h else '—',f"{int(q['saved'])} / {int(q['hurt'])}" if h else '—',fmt(q['mworst']),fmt(q['yworst'])])
 html.append(f'<section id="{g}"><h2>{labels[g]}</h2><p>Исходную выбирали среди ширин {w0}–{w1}, лукбэков {l0}–{l1}. TD и Protected — срез {coords[g]}.</p><div class="wrap"><table><tr>'+''.join('<th>'+s+'</th>' for s in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(s)+'</td>' for s in row)+'</tr>' for row in a)+'</table></div></section>')
(P/'three.html').write_text(''.join(html)+'</main></html>')
