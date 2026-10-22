"""Owner 20:14: two strategies per coin with zone vote B: long LB (high WR, ~100 trades) and short LB (more trades). Plateau search on wide_<c>.csv.gz."""
import pandas as pd, numpy as np
K = ['w', 'lb', 'sl', 'ratio']; out = []
for c in ('btc', 'eth', 'sol'):
    d = pd.read_csv(f'wide_{c}.csv.gz'); d = d[d.variant == 'zB'].copy()
    d['good'] = (d.net >= 5000) & (d.dd >= -0.35) & (d.n >= 60) & (d.yup >= np.maximum(d.ny - 1, 5))
    G = d.set_index(K)
    for (sl, rt), g in d.groupby(['sl', 'ratio']):
        gi = g.set_index(['w', 'lb'])
        for r in g[g.good].itertuples():
            nb = [(r.w + a, r.lb + b) for a in (-1, 0, 1) for b in (-10, 0, 10) if (a, b) != (0, 0) and (r.w + a, r.lb + b) in gi.index]
            if len(nb) < 5: continue
            q = gi.loc[nb]; share = q.good.mean()
            out.append(dict(coin=c, w=r.w, lb=r.lb, sl=sl, ratio=rt, net=r.net, wr=r.wr, dd=r.dd, n=r.n, worst=r.worst, yup=r.yup, ny=r.ny,
                            nb_good=share, nb_med=q.net.median(), nb_wr=q.wr.median(), nb_dd=q.dd.median()))
P = pd.DataFrame(out); P = P[P.nb_good >= 0.75]; P.to_csv('plat.csv', index=False)
pd.set_option('display.width', 250)
for c in ('btc', 'eth', 'sol'):
    q = P[P.coin == c]
    L = q[(q.lb >= 200)].sort_values('nb_med', ascending=False); S = q[(q.lb <= 80)].sort_values('nb_med', ascending=False)
    print('=====', c, 'plateau cells', len(q), 'long', len(L), 'short', len(S))
    print('LONG by nb median'); print(L.head(6).round(3).to_string(index=False))
    print('LONG wr>=.30'); print(L[L.wr >= .30].head(5).round(3).to_string(index=False))
    print('SHORT'); print(S.head(6).round(3).to_string(index=False))
