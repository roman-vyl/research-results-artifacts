"""Owner 20:29: are SL7.5 cells a local EMA200 bounce or a medium-term trend bet? Trade duration, TP distance in %, long vs short, per year. Zone vote B."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/ema200_calib/review/calib'); import zc, vote2
D = '/mnt/project-files/ema200_calib/'; FEE = 0.0004; _s = open('run.py').read(); exec(_s[_s.index('def candles'):_s.index('def v2masks')])
CELLS = {'btc': [(11, 20, 7.5, 4.0), (11, 20, 4.5, 4.5), (10, 200, 7.5, 4.0), (10, 40, 4.5, 4.5)], 'eth': [(4, 300, 7.5, 4.0), (3, 290, 4.5, 4.5), (11, 20, 4.5, 5.5), (11, 40, 4.5, 4.5)],
         'sol': [(6, 290, 6.0, 4.0), (10, 30, 5.5, 6.5), (10, 100, 5.0, 4.5)]}
for c, S in CELLS.items():
    b = zc.B[c]; X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); meta = json.load(open(D + zc.P_[c] + '/meta.json'))
    BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float)
    zB = (vote2.score('v1', c, 'linear') >= 0.75 - 1e-9) | vote2.veto(c, 'v1')
    C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', c, meta['bars'])
    SLS = sorted({s[2] for s in S}); RT = sorted({s[3] for s in S}); RRo, XB, OK = outcomes(C, H, L, BAR, G, AR, SLS, RT); RF = np.outer(AR, SLS)
    if c == 'btc': OK &= XB < 684720
    for (w, lb, sl, rt) in S:
        ix = b['IX'][(w, lb)]; ix = ix[~zB[ix]]; a = SLS.index(sl); q = RT.index(rt); busy = -1; T = []
        for i in ix:
            if BAR[i] <= busy: continue
            if not OK[i, a, q]: break
            rr = RRo[i, a, q]; x = rr * RF[i, a]; g = (x - FEE * (2 + G[i] * x)) / (1 + FEE)
            T.append(dict(side=G[i], win=rr > 0, days=(XB[i, a, q] - BAR[i]) * 5 / 1440, risk=100 * RF[i, a], g=g, yr=int(YR[XB[i, a, q]]))); busy = XB[i, a, q]
        t = pd.DataFrame(T); W = t[t.win]; Lo = t[~t.win]
        lg = t[t.side > 0]; sh = t[t.side < 0]
        print(f"{c} W{w} LB{lb} SL{sl} TP{rt}R | n {len(t)} WR {100*t.win.mean():.0f}% | стоп {t.risk.median():.2f}% тейк {t.risk.median()*rt:.1f}% | дни: тейк медиана {W.days.median():.1f} (90% {W.days.quantile(.9):.1f}), стоп {Lo.days.median():.1f} | лонг n{len(lg)} WR{100*lg.win.mean():.0f}% sum{100*lg.g.sum():+.0f}% · шорт n{len(sh)} WR{100*sh.win.mean():.0f}% sum{100*sh.g.sum():+.0f}%")
