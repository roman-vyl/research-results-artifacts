"""Curves per filter on zone samples: common absolute threshold grid for 3 coins; per point: n cut, stops, stop share, saved R, random-cut mean and 5-95%."""
import json, numpy as np, zc
F = [('A1','a1s','low','V3'),('A2.1','accel','high','V3'),('B1 5m','leg_5m','high','V3'),('B1 15m','leg_15m','high','V3'),('B1 1h','leg_1h','high','V3'),
 ('B2 r14','r14','low','V3'),('B2 m14','m14','low','V3'),('C1 c11','c11','low','V3'),('C1 c12','c12','high','V3'),('C5','c5','low','V3'),('C5','c5','high','V3'),
 ('A3','a3','high','V1'),('A5','a5','high','V1'),('A6','a6','high','V1'),('C3.1','c31','high','V1'),
 ('A2.2','a22','low','R'),('A2.3','a23','high','R'),('A4','a4','high','R'),('A6','a6','low','R'),('C3.1','c31','low','R'),('C3.2','c32','low','R'),('C3.2','c32','high','R'),
 ('V1.1','v11','low','R'),('V1.1','v11','high','R'),('V1.2','v12','low','R'),('V1.2','v12','high','R'),('V1.3','v13','low','R'),('V1.3','v13','high','R'),
 ('V1.4','v14','low','R'),('V1.4','v14','high','R'),('V2.1','v21','high','R'),('V2.2','v22','low','R'),('V2.2','v22','high','R'),('V2.3','v23','high','R'),
 ('B3','b3h','low','U'),('D1','d1_1d','low','U'),('D2','d2_1d','low','U')]
rng = np.random.default_rng(7); SMP = {}
for c in zc.C:
    ids, S, R, K = zc.sample(c); SMP[c] = dict(ids=ids, S=S, R=R)
def sig(x):
    return float('%.3g' % x)
out = dict(base={c: round(100 * SMP[c]['S'].mean(), 1) for c in zc.C}, n={c: len(SMP[c]['ids']) for c in zc.C},
           meanR={c: round(float(SMP[c]['R'].mean()), 3) for c in zc.C}, cells={c: len(zc.B[c]['cells']) for c in zc.C}, F=[])
RND = {}
def rand_band(c, n):
    k = (c, n)
    if k not in RND:
        R = SMP[c]['R']; S = SMP[c]['S']
        if n == 0: RND[k] = (0, 0, 0, 0); return RND[k]
        idx = np.argsort(rng.random((400, len(R))), 1)[:, :n]; sv = -R[idx].sum(1); ss = S[idx].mean(1)
        RND[k] = (float(sv.mean()), float(np.percentile(sv, 5)), float(np.percentile(sv, 95)), float(np.percentile(ss, 95)))
    return RND[k]
for name, m, side, grp in F:
    X = {c: zc.feat(c, m)[SMP[c]['ids']] for c in zc.C}; allv = np.concatenate([x[np.isfinite(x)] for x in X.values()])
    p = (lambda q: np.percentile(allv, q))
    if side == 'low': a, b, e = p(50), p(1), allv.min(); core = np.linspace(a, b, 31); tail = np.linspace(b, e, 8)[1:]
    else: a, b, e = p(50), p(99), allv.max(); core = np.linspace(a, b, 31); tail = np.linspace(b, e, 8)[1:]
    G = sorted(set(sig(t) for t in np.r_[core, tail]), reverse=(side == 'low'))
    rec = dict(name=name, m=m, side=side, grp=grp, G=G, a={})
    for c in zc.C:
        x = X[c]; S = SMP[c]['S']; R = SMP[c]['R']; pts = []
        for t in G:
            h = np.isfinite(x) & ((x <= t) if side == 'low' else (x >= t)); n = int(h.sum())
            rm, r5, r95, s95 = rand_band(c, n)
            pts.append([n, round(float(S[h].sum()), 2), round(100 * float(S[h].mean()), 1) if n else None, round(float(-R[h].sum()), 2), round(rm, 2), round(r5, 2), round(r95, 2), round(100 * s95, 1)])
        rec['a'][c] = dict(nvalid=int(np.isfinite(x).sum()), pts=pts)
    out['F'].append(rec)
json.dump(out, open('/mnt/project-files/ema200_calib/review/calib/curves.json', 'w'))
print(out['base'], out['n'], out['meanR'], len(out['F']))
