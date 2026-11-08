from pathlib import Path
import json,pandas as pd
P=Path(__file__).resolve().parent
s=pd.read_csv(P/'summary.csv').set_index('region')
s=s.loc[['все','20–30%','30–40%','5m, ≤4','5m, TP 4.5','1h, умеренный T','1h, поздний T','15m, поздний T']]
cfg=json.loads((P/'dates.json').read_text());stars=cfg['stars']
def num(v):return f'{v:.2f}'.replace('.',',')
def table(head,rows):
    return '<div class="wrap"><table><tr>'+''.join('<th>'+h+'</th>' for h in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table></div>'
metrics={'y_sd':'Разброс годовых','y_worst':'Худший год','best_share':'Доля лучшего года в прибыли','m_sd':'Разброс месячных','m_positive':'Плюсовых месяцев','m_worst':'Худший месяц'}
def pair(r,k):return num(r['td_'+k])+' → '+num(r[k])
html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ETH · распределение прибыли во времени</title><style>body{font:16px/1.55 system-ui,sans-serif;max-width:1250px;margin:25px auto;padding:0 18px;color:#183829}h1,h2{line-height:1.18}a{color:#135741}.wrap{overflow:auto}table{border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums;width:100%}td,th{padding:6px 8px;text-align:right;border-bottom:1px solid #dce5df}th{background:#eff5ef}th:first-child,td:first-child{text-align:left}td{white-space:nowrap}p{max-width:95ch}</style><main><a href="../index.html">← Частота и результат защиты</a><h1>ETH · распределение прибыли по годам и месяцам</h1><p>У пары ETH звездочка 3/290 и 7/170, общий счёт с долей 50% на ногу. В диапазоне 5m ΔADX 9,30–10,05 проверены 94 400 сочетаний. Для всех трёх строк этого диапазона медианы считаются сначала внутри каждой плоскости SL/TP, затем по 20 плоскостям. Для ранее выбранных блоков берётся медиана по ячейкам самого блока. Соседние ячейки используют общую историю.</p>
<h2>Медианы · чистая TD → TD с защитой</h2><p>Годы 2022–2025 полные; месяцы с апреля 2021 по сентябрь 2026 полные (66). Доходности, доли и стандартные отклонения выражены в процентах. Разброс — стандартное отклонение доходностей. Доля лучшего года — его долларовая прибыль от суммарной прибыли четырёх полных лет. На границах периодов учтена стоимость открытых позиций с комиссией выхода.</p>'''
html+=table(['Диапазон / плато',*metrics.values()], [[label,*[pair(r,k) for k in metrics]] for label,r in s.iterrows()]+[['Две звёздочки без TD',*[num(stars[k]) for k in metrics]]])
html+='<h2>Изменение доходности по календарным годам</h2><p>Медиана попарной разницы в процентных пунктах. Крайние годы частичные.</p>'
years=range(2021,2027)
html+=table(['Диапазон / плато',*map(str,years)],[[label,*[num(r[f'delta_{y}']) for y in years]] for label,r in s.iterrows()])
html+='<h2>Месяцы двух плато 5m</h2><p>Медианная доходность пары по всем ячейкам плато, проценты. Только полные месяцы. Полная разбивка по пяти плато доступна в CSV.</p>'
m=pd.read_csv(P/'months.csv');m=m[m.month.isin(cfg['complete_months'])];series=[m[m.plateau==n].set_index('month') for n in ['5m, ≤4','5m, TP 4.5']]
html+=table(['Месяц','TP 3,5 · TD → защита','TP 4,5 · TD → защита'],[[mon,*[num(df.loc[mon,'td'])+' → '+num(df.loc[mon,'protected']) for df in series]] for mon in cfg['complete_months']])
html+='<p><a href="planes.csv">20 плоскостей</a> · <a href="months.csv">Доходность каждого месяца на пяти плато</a> · <a href="cells.csv.gz">340 ячеек плато</a></p></main></html>'
(P/'index.html').write_text(html)
