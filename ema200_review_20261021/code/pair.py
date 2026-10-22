"""Overlap of two strategies per coin (owner 20:14): shared entries and time in market overlap, zone vote B."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/ema200_calib/review/calib'); import zc, vote2
D = '/mnt/project-files/ema200_calib/'; _s = open('run.py').read(); exec(_s[_s.index('def candles'):_s.index('def v2masks')])  # helpers: candles, outcomes
PAIRS = {'btc': [(10, 200, 7.5, 4.0), (11, 20, 7.5, 4.0), (10, 20, 7.5, 4.0)], 'eth': [(4, 300, 7.5, 4.0), (11, 20, 4.5, 5.5), (10, 20, 4.5, 7.0)],
         'sol': [(6, 290, 6.0, 4.0), (10, 30, 5.5, 6.5)]}
for c, S in PAIRS.items():
    b = zc.B[c]; X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); meta = json.load(open(D + zc.P_[c] + '/meta.json'))
    BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float)
    zB = (vote2.score('v1', c, 'linear') >= 0.75 - 1e-9) | vote2.veto(c, 'v1')
    C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', c, meta['bars'])
    SLS = sorted({s[2] for s in S}); RT = sorted({s[3] for s in S}); RRo, XB, OK = outcomes(C, H, L, BAR, G, AR, SLS, RT)
    if c == 'btc': OK &= XB < 684720
    tr = {}
    for (w, lb, sl, rt) in S:
        ix = b['IX'][(w, lb)]; ix = ix[~zB[ix]]; a = SLS.index(sl); q = RT.index(rt); busy = -1; T = []
        for i in ix:
            if BAR[i] <= busy: continue
            if not OK[i, a, q]: break
            T.append((i, BAR[i], XB[i, a, q])); busy = XB[i, a, q]
        tr[(w, lb, sl, rt)] = T
    keys = list(tr)
    for k1 in keys[:1]:
        for k2 in keys[1:]:
            A, B_ = tr[k1], tr[k2]; ea = {t[0] for t in A}; eb = {t[0] for t in B_}
            ina = np.zeros(len(C) + 2, bool); inb = np.zeros(len(C) + 2, bool)
            for _, s, e in A: ina[s:e + 1] = True
            for _, s, e in B_: inb[s:e + 1] = True
            print(c, k1, len(A), 'vs', k2, len(B_), '| shared entries', len(ea & eb), '| both in market %.0f%% of long-LB time' % (100 * (ina & inb).sum() / max(ina.sum(), 1)),
                  '| in market: long %.0f%%, short %.0f%%' % (100 * ina.mean(), 100 * inb.mean()))
