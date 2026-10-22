"""Zone calibration lib (review thread, owner 2026-10-21 16:10 'возьми на себя калибровку').
Zones = review/working_zones_20261021.csv (no-filter cells, TP>=4R, net>=4k, DD/years ok). Outcomes = review/full_<c>_zone.npz
(SL 4.25,4.5,4.75,5 x TP 4,4.5,5 for all 348 W x LB cells). Sample = all unique entries taken in zone cell-layers (no filter),
label = share of those cell-layers where the entry hit its stop, R = mean net R there."""
import pickle, numpy as np, pandas as pd
D = '/mnt/project-files/ema200_calib/'; C = ('btc', 'eth', 'sol'); FEE = 0.0004
P_ = {'btc': 'btc_recheck/work/btc', 'eth': 'runs_20261020/eth200_20261020/work/eth', 'sol': 'v6/sol_work/sol'}
YEARS = list(range(2020, 2027))
ZC = pd.read_csv(D + 'review/working_zones_20261021.csv')
B = {}
for c in C:
    z = np.load(D + f'review/full_{c}_zone.npz'); X = pd.read_csv(D + P_[c] + f'/entries_e200{c}.csv.gz')
    pk = pickle.load(open(D + f'fullplane/out/{c}_full.pkl', 'rb')); assert len(pk['elig']) == len(X)
    IDX = {(int(b), s): i for i, (b, s) in enumerate(zip(X.bar, X.side))}
    SIG = pickle.load(open(D + P_[c] + '/signals.pkl', 'rb')); IX = {}
    for (w, lb), sig in SIG.items():
        ix = np.array([IDX[(int(b), s)] for b, s, _ in sig], int); IX[(w, lb)] = ix[np.argsort(z['bar'][ix], kind='stable')]
    sls = list(z['sls']); tps = list(z['ratios'])
    zc = ZC[ZC.coin == c.upper()]
    cells = [(int(r.min_current_width_atr), int(r.untouched_lookback), sls.index(r.sl_atr_multiplier), tps.index(r.tp_sl_ratio)) for r in zc.itertuples()]
    allc = [(w, lb, a, q) for (w, lb) in IX for a in range(len(sls)) for q in range(len(tps))]
    B[c] = dict(rr=z['rr'], xb=z['xb'], ok=z['ok'], bar=z['bar'], g=z['side'].astype(float), rf=np.outer(X.ar.values, sls),
                IX=IX, sls=sls, tps=tps, cells=cells, allc=allc, V=pk['V'], elig=pk['elig'], YR=pk['YR'], n=len(X))
def take(c, cell, bl):
    b = B[c]; w, lb, a, q = cell; busy = -1; out = []
    for i in b['IX'][(w, lb)]:
        if bl is not None and bl[i]: continue
        if b['bar'][i] <= busy: continue
        if not b['ok'][i, a, q]: break
        out.append(i); busy = b['xb'][i, a, q]
    return np.array(out, int)
def rn(c, t, a, q):
    b = B[c]; rr = b['rr'][t, a, q]; rf = b['rf'][t, a]; g = b['g'][t]; return rr - FEE * (2 + g * rr * rf) / rf, rr, rf, g
def metrics(c, cell, bl=None):
    b = B[c]; w, lb, a, q = cell; t = take(c, cell, bl)
    if not len(t): return dict(n=0, wr=0, R=0, net=0, dd=0, yup=0, ys=[0] * len(YEARS))
    R, rr, rf, g = rn(c, t, a, q); x = rr * rf; ge = (x - FEE * (2 + g * x)) / (1 + FEE)
    e = 10000 * np.cumprod(1 + ge); pk = np.maximum.accumulate(np.r_[10000, e])[1:]
    yr = b['YR'][b['bar'][t]]; ys = [float(R[yr == y].sum()) for y in YEARS]
    return dict(n=len(t), wr=100 * float((rr > 0).mean()), R=float(R.sum()), net=float(e[-1] - 10000), dd=float(100 * min(0, (e / pk - 1).min())),
                yup=sum(v > 0 for v in ys), ys=ys)
def sample(c, cells=None):
    b = B[c]; cells = b['cells'] if cells is None else cells; k = np.zeros(b['n']); s = np.zeros(b['n']); r = np.zeros(b['n'])
    for cell in cells:
        t = take(c, cell, None); R, rr, _, _ = rn(c, t, cell[2], cell[3]); np.add.at(k, t, 1); np.add.at(s, t, rr < 0); np.add.at(r, t, R)
    ids = np.nonzero(k)[0]; return ids, s[ids] / k[ids], r[ids] / k[ids], k[ids]
def feat(c, m):
    b = B[c]; return np.where(b['elig'], b['V'][m], np.nan)
