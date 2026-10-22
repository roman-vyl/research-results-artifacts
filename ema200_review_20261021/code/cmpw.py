"""Zone vote B vs V2-2 on wide planes (owner 19:55): halves of the plane by W and LB, all SL x TP layers, and good cells (plateaus)."""
import pandas as pd, numpy as np, json
K = ['w', 'lb', 'sl', 'ratio']; OUT = {}
for c in ('btc', 'eth', 'sol'):
    d = pd.read_csv(f'wide_{c}.csv.gz'); d['allup'] = (d.yup == d.ny) & (d.ny > 0); d['y5'] = d.yup >= 5
    p = d.pivot_table(index=K, columns='variant', values=['net', 'wr', 'dd', 'allup', 'n']); p.columns = [f'{a}_{b}' for a, b in p.columns]; p = p.reset_index()
    p['wh'] = np.where(p.w <= 8, 'W3–8', 'W9–14'); p['lh'] = np.where(p.lb <= 150, 'LB20–150', 'LB160–300')
    # good cells without filter = owner's robustness rule: net >= 5k, DD >= -35%, >= 60 trades, >= 5 profitable years
    y5 = d[d.variant == 'none'].set_index(K).y5
    p['good'] = (p.net_none >= 5000) & (p.dd_none >= -0.35) & (p.n_none >= 60) & p.set_index(K).index.map(y5).values.astype(bool)
    p['diff'] = p.net_zB - p.net_v2
    def agg(g):
        return pd.Series(dict(cells=len(g), none=g.net_none.median(), v2=g.net_v2.median(), zB=g.net_zB.median(), zB_better=100 * (g.net_zB > g.net_v2).mean(),
                              wr_v2=100 * g.wr_v2.median(), wr_zB=100 * g.wr_zB.median(), dd_v2=100 * g.dd_v2.median(), dd_zB=100 * g.dd_zB.median(),
                              up_v2=100 * g.allup_v2.mean(), up_zB=100 * g.allup_zB.mean()))
    o = dict(halves=[], good={}, grid={}, gridgood={}, bands=[])
    for (wh, lh), g in p.groupby(['wh', 'lh']):
        o['halves'].append(dict(wh=wh, lh=lh, all=agg(g).to_dict(), good=agg(g[g.good]).to_dict() if g.good.sum() else None))
    o['good'] = agg(p[p.good]).to_dict(); o['all'] = agg(p).to_dict()
    for nm, q in (('grid', p), ('gridgood', p[p.good])):
        gg = q.groupby(['sl', 'ratio']).apply(lambda g: pd.Series(dict(cells=len(g), zb_better=100 * (g.net_zB > g.net_v2).mean(), v2=g.net_v2.median(), zB=g.net_zB.median(), none=g.net_none.median())), include_groups=False).reset_index()
        o[nm] = gg.to_dict('records')
    # layer-level winners per half (median net of the half in one SL x TP layer)
    L = p.groupby(['wh', 'lh', 'sl', 'ratio']).agg(v2=('net_v2', 'median'), zB=('net_zB', 'median')).reset_index()
    o['layer_wins'] = dict(zB=int((L.zB > L.v2).sum()), v2=int((L.v2 > L.zB).sum()))
    Lg = p[p.good].groupby(['wh', 'lh', 'sl', 'ratio']).agg(v2=('net_v2', 'median'), zB=('net_zB', 'median'), n=('net_v2', 'size')).reset_index(); Lg = Lg[Lg.n >= 3]
    o['layer_wins_good'] = dict(zB=int((Lg.zB > Lg.v2).sum()), v2=int((Lg.v2 > Lg.zB).sum()))
    OUT[c] = o
    print(c, 'ALL', {k: round(v, 1) for k, v in o['all'].items()}); print(c, 'GOOD', {k: round(v, 1) for k, v in o['good'].items()}, o['layer_wins'], o['layer_wins_good'])
    for h in o['halves']: print('  ', h['wh'], h['lh'], 'all zB>v2 %.0f%% med v2 %.1fk zB %.1fk' % (h['all']['zB_better'], h['all']['v2'] / 1e3, h['all']['zB'] / 1e3),
                                '| good n=%d zB>v2 %.0f%% v2 %.1fk zB %.1fk' % ((h['good']['cells'], h['good']['zB_better'], h['good']['v2'] / 1e3, h['good']['zB'] / 1e3) if h['good'] else (0, 0, 0, 0)))
json.dump(OUT, open('cmpw.json', 'w'))
