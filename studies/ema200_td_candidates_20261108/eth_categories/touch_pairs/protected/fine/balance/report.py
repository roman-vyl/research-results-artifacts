"""Render standalone tables from the saved median breakdown."""
import csv
from pathlib import Path
from html import escape

P=Path(__file__).resolve().parent

def read(name):
    with (P/(name+'.csv')).open() as f:
        return list(csv.DictReader(f))
def num(s):
    return '—' if not s else f'{float(s):,.1f}'.replace(',',' ').replace('.',',')
def money(s):
    return f'{float(s):+,.0f}'.replace(',',' ').replace('-','−')
def table(rows, key, title, planes=False):
    fields=[(key,title),('active','Защита / все'),('hit_active','BE / защиты'),('success_hit','Спасено / BE'),
            ('success_active','Спасено / защиты'),('hurt_active','Урезано / защиты'),('be_count','Выходов BE'),
            ('net_r100','Баланс R / 100 сделок'),('gain','Δ Net Won'),('gap_gain','Δ с гэпом')]
    if planes:
        fields += [('positive_planes','Плоскости в плюсе')]
    def cell(r,k):
        if k==key:return escape(r[k])
        if k=='positive_planes':return r[k]+' / '+r['planes']
        return money(r[k]) if 'gain' in k else num(r[k])
    head=''.join(f'<th>{label}</th>' for _,label in fields)
    body=''.join('<tr>'+''.join(f'<td>{cell(r,k)}</td>' for k,_ in fields)+'</tr>' for r in rows)
    return '<div class="wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'

def render():
    stats=read('summary')
    text=['''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ETH · частота и результат защиты</title><style>
    body{font:16px/1.55 system-ui,sans-serif;color:#19362f;background:#fafcfb;margin:28px auto;padding:0 20px;max-width:1250px}a{color:#07594a}h1,h2,h3{line-height:1.18}p{max-width:95ch}.wrap{overflow:auto}table{border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px;width:100%}th,td{padding:7px;text-align:right;border-bottom:1px solid #d7e2db}th{background:#eaf1ec}td:first-child,th:first-child{text-align:left}td{white-space:nowrap}</style><main>
    <a href="../index.html">← Карта ΔADX × T × D</a><h1>ETH 7/170 · частота и результат защиты</h1>
    <p><strong>На 5 мин при ΔADX 9,30–10,05 защита включается в 39,2% сделок. Из 100 активаций около 42 спасают убыточный выход и 11–12 урезают прибыльный. Медианная прибавка пары $1 334, при худшем исполнении BE $1 195. На 20 из 20 плоскостей медианная прибавка положительна.</strong></p>
    <p>Защита активируется при направленном росте ADX раньше перехода в Runner. Доли и суммы в R относятся к сделкам 7/170. Изменение Net Won относится к общему счёту со второй ногой ★3/290 и сравнивается с чистой TD при тех же настройках.</p>
    <p>«Спасено» — выход по цене входа заменил убыточный выход чистой TD. «Урезано» — он заменил прибыльный выход. Два знаменателя отвечают на разные вопросы: «спасено / защиты» учитывает все активации, «спасено / BE» — только исполненные защитные стопы. Доли в процентах. Выходы по цене входа несут комиссии.</p>
    <p>В таблицах по частоте и порогу сначала берётся медиана по всем подходящим T, D и ограничениям касаний каждой плоскости SL/TP, затем медиана по плоскостям. Плоскости равноправны. Для нулевого знаменателя доля не определена. «Плоскости в плюсе» считает плоскости с положительной медианной Δ Net Won. Баланс в R — сумма сохранённых убытков за вычетом упущенных выигрышей на 100 сделок. Денежная дельта дополнительно учитывает комиссии, повторные входы и компаундирование.</p>
    <p><a href="#freq">По доле активации</a> · <a href="#bands">По порогам ΔADX</a> · <a href="#blocks">Внутри соседних T и D</a></p><h2 id="freq">Что меняется, если защита включается чаще</h2><p>Левая граница интервала открыта, правая включена. Нулевая частота вынесена отдельно. Пустые интервалы отсутствуют.</p>''']
    for kind in ['activation','threshold']:
        if kind=='threshold':
            text.append('<h2 id="bands">Диапазоны порогов ΔADX</h2><p>В каждом диапазоне показаны все допустимые T и D. Это измеренный эффект на сетке поиска, участки выбраны по той же истории.</p>')
        for tf in [5,15,60]:
            rows=[r for r in stats if r['kind']==kind and r['tf']==str(tf)]
            rows.sort(key=lambda r:float(r['label'].split('-')[0]))
            text.append('<h3>'+str(tf)+' мин</h3>'+table(rows,'label','Частота, %' if kind=='activation' else 'Диапазон ΔADX',True))
    text.append('<h3>5 мин · частота внутри ΔADX 9,30–10,05</h3>'+table([r for r in stats if r['kind']=='band_activation' and r['tf']=='5'],'label','Частота, %',True))
    text.append('<h2 id="blocks">Медианы внутри непрерывных плато</h2><p>Здесь единица наблюдения — одна ячейка выбранного блока ΔADX × T × D. Блоки заранее взяты из предыдущего полного перебора. На 5m и 15m по 84 ячейки, на 1h по 44. Уровни и денежные результаты для каждой ячейки доступны на карте.</p>')
    blocks=read('plateaus')
    from aggregate import BLOCKS
    for row, spec in zip(blocks,BLOCKS):
        _,sl,tp,cap,tf,a,b,t,u,d,e=spec
        row['name']+=f' · SL {sl:g} TP {tp:g} · касания '+(f'≤{cap}' if cap else 'все')+f' · Δ {a:g}–{b:g} · T {t:g}–{u:g} · D {d:g}–{e:g}'
    text.append(table(blocks,'name','Плато'))
    text.append('<p><a href="planes.csv">Все медианы по каждой плоскости</a> · <a href="summary.csv">Сводные медианы, межквартильные интервалы и размеры выборок</a> · <a href="plateaus.csv">Показатели плато</a></p></main></html>')
    (P/'index.html').write_text('\n'.join(text))
if __name__=='__main__':render()
