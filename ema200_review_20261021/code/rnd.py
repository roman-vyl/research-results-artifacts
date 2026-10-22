"""Random-cut control for run.py (same number of blocked eligible entries as V2-2 and as zone vote B, 5 draws each). Control check of three votes on areas not used for calibration (rules: ctrl3/RULES.md, fixed before this run).
Variants: none, V2-2 (v2e200/spec_v2.json linear core, theta .4726, vetoes), V2-2 trimmed (core without B1 1h, D1, A2.3, C5, V1.3),
zone vote B (v1 linear theta .75 + vetoes). Outcomes = lab sim_tp 'old' rule (as code/fullplane.py), one position, fee .0004/side, $10k compounding.
Usage: run.py <sol|eth|bch|bnb>. Writes ctrl3/<area>.csv.gz."""
import sys, json, pickle, numpy as np, pandas as pd
D = '/mnt/project-files/ema200_calib/'; R = D + 'review/'; FEE = 0.0004; CO = sys.argv[1]
sys.path.insert(0, R + 'calib')
S2 = json.load(open(D + 'v2e200/spec_v2.json')); TH2 = [v['theta'] for v in S2['variants'] if v['id'] == 2][0]
DROP = {'B1 1h', 'D1', 'A2.3', 'C5', 'V1.3'}
def candles(cf, coin, bars):
    Z = np.load(cf); t = Z[coin + '_t']; TM = np.arange(t[0], t[-1] + 1, 300000, dtype=np.int64)[:bars]
    Df = pd.DataFrame(np.c_[Z[coin + '_h'], Z[coin + '_l'], Z[coin + '_c']], index=t, columns=['h', 'l', 'c']).reindex(TM)
    C = Df.c.ffill().values; H = Df.h.fillna(pd.Series(C, index=TM)).values; L = Df.l.fillna(pd.Series(C, index=TM)).values
    return C, H, L, pd.to_datetime(TM, unit='ms', utc=True).year.values
def outcomes(C, H, L, BAR, G, AR, SLS, RT):
    n = len(BAR); NN = len(C); RRo = np.zeros((n, len(SLS), len(RT))); XB = np.zeros((n, len(SLS), len(RT)), int); OK = np.ones((n, len(SLS), len(RT)), bool)
    for i in range(n):
        b, g = BAR[i], G[i]; E = C[b]; fav = H[b:] if g > 0 else -L[b:]; adv = L[b:] if g > 0 else -H[b:]; Es = E if g > 0 else -E
        for a, k in enumerate(SLS):
            Rr = k * AR[i] * E; h_ = np.nonzero(adv[1:] <= Es - Rr)[0]; has = len(h_) > 0; nlen = (1 + int(h_[0]) + 1) if has else len(fav)
            best = np.maximum.accumulate(fav[:nlen])
            for q, rt in enumerate(RT):
                lvl = Es + rt * Rr; j = int(np.searchsorted(best, lvl, 'left'))
                if j < 1:
                    nz = np.nonzero(fav[1:nlen] >= lvl)[0]; j = 1 + int(nz[0]) if len(nz) else nlen
                sl_i = nlen - 1 if has else nlen
                if j < sl_i: RRo[i, a, q] = rt; XB[i, a, q] = b + j
                elif has: RRo[i, a, q] = -1.0; XB[i, a, q] = b + nlen - 1
                else: OK[i, a, q] = False; XB[i, a, q] = NN
    return RRo, XB, OK
def v2masks(feat):
    def hit(m, s, T): x = feat(m); return np.isfinite(x) & ((x <= T) if s == 'low' else (x >= T))
    vt = sum(hit(r['metric'], r['side'], r['thr']) for r in S2['veto']) > 0
    def blk(core):
        s = sum(hit(r['metric'], r['side'], r['thr']) * min(max(S2['r_core'][r['voter']] / 0.55, 0), 1) for r in core)
        return vt | ((s >= TH2) & (s > 0))
    return blk(S2['core']), blk([r for r in S2['core'] if r['voter'] not in DROP])
if CO in ('btcx', 'ethx', 'solx'):
    import zc, vote2
    c = CO[:3]; b = zc.B[c]; X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); meta = json.load(open(D + zc.P_[c] + '/meta.json'))
    BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float); feat = lambda m: zc.feat(c, m)
    zB = (vote2.score('v1', c, 'linear') >= 0.75 - 1e-9) | vote2.veto(c, 'v1')
    C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', c, meta['bars'])
    SLS, RT = (4.0, 4.25, 4.5, 4.75, 5.0, 5.5, 6.0, 6.5), (4.0, 4.5, 5.0); IX = b['IX']
    ZC = pd.read_csv(R + 'working_zones_20261021.csv'); ZC = ZC[ZC.coin == c.upper()]
    AREAS = {c + '_zone': [(int(r.min_current_width_atr), int(r.untouched_lookback), float(r.sl_atr_multiplier), float(r.tp_sl_ratio)) for r in ZC.itertuples()]}
    if c != 'sol': AREAS[c + '_hiall'] = [(w, lb, sl, rt) for (w, lb) in IX for sl in (5.5, 6.0, 6.5) for rt in RT]
elif CO == 'sol':
    import zc, vote2
    b = zc.B['sol']; X = pd.read_csv(D + zc.P_['sol'] + '/entries_e200sol.csv.gz'); meta = json.load(open(D + zc.P_['sol'] + '/meta.json'))
    BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float); feat = lambda m: zc.feat('sol', m)
    zB = (vote2.score('v1', 'sol', 'linear') >= 0.75 - 1e-9) | vote2.veto('sol', 'v1')
    C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', 'sol', meta['bars'])
    SLS, RT = (5.5, 6.0, 6.5), (4.0, 4.5, 5.0); IX = b['IX']
    P = pd.read_csv(R + 'solwide/points_sol_full.csv.gz'); P = P[P.variant == 'none']
    A = {'sol_w6': P[P.w.between(5, 7) & P.lb.between(230, 300) & P.sl.isin([6, 6.5]) & P.ratio.between(4, 5)],
         'sol_hi': P[P.sl.isin([5.5, 6, 6.5]) & P.ratio.between(4, 5) & (P.net >= 4000) & (P.dd >= -0.40)]}
    AREAS = {k: [(int(r.w), int(r.lb), float(r.sl), float(r.ratio)) for r in v.itertuples()] for k, v in A.items()}
elif CO == 'eth':
    import zc, vote2
    b = zc.B['eth']; X = pd.read_csv(D + zc.P_['eth'] + '/entries_e200eth.csv.gz'); meta = json.load(open(D + zc.P_['eth'] + '/meta.json'))
    BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float); feat = lambda m: zc.feat('eth', m)
    zB = (vote2.score('v1', 'eth', 'linear') >= 0.75 - 1e-9) | vote2.veto('eth', 'v1')
    C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', 'eth', meta['bars'])
    SLS, RT = (4.25, 4.5, 4.75, 5.0), (4.0, 4.5, 5.0)
    IDX = {(int(bb), s): i for i, (bb, s) in enumerate(zip(X.bar, X.side))}; SIG = pickle.load(open(R + 'lbext/signals_ext_eth.pkl', 'rb'))
    IX = {k: (lambda ix: ix[np.argsort(BAR[ix], kind='stable')])(np.array([IDX[(int(bb), s)] for bb, s, _ in v], int)) for k, v in SIG.items()}
    AREAS = {'eth_lb310_500': [(w, lb, sl, rt) for (w, lb) in IX for sl in SLS for rt in RT]}
else:
    CFG = {'bch': (D + 'bch200_20261021/work/bch', 'e200bch', D + 'bch200_20261021/work/alt_bch.npz'),
           'bnb': (D + 'runs_20261020/bnb200_20261020/work/bnb', 'e200bnb', D + 'entries/alt_bnb.npz')}[CO]
    WD, ENT, ALT = CFG; meta = json.load(open(WD + '/meta.json'))
    X = pd.read_csv(f'{WD}/entries_{ENT}.csv.gz'); BAR = X.bar.values.astype(int); G = np.where(X.side.values == 'long', 1, -1); AR = X.ar.values.astype(float)
    v = np.load(WD + '/values.npz', allow_pickle=True); al = np.load(ALT, allow_pickle=True)
    V = {k: v[k].astype(float) for k in v.files if k not in ('bar', 'side')}; V.update({k: al[k].astype(float) for k in al.files if k not in ('bar', 'side', 'elig')})
    elig = al['elig'].astype(bool); feat = lambda m: np.where(elig, V[m], np.nan)
    P2 = json.load(open(R + 'calib/pick2.json')); VT = json.load(open(R + 'calib/vetos.json'))
    FAM = lambda m, s: ('V1' + s) if m in ('v11', 'v12', 'v13', 'v14') else ('B1' if m.startswith('leg_') else m + s)
    def hit(m, s, T): x = feat(m); return np.isfinite(x) & ((x <= T) if s == 'low' else (x >= T))
    fam = {}
    for r in P2:
        if r['set'] != 'ALL': continue
        w = min(max(r['r'], 0) / 0.55, 1)
        if w <= 0: continue
        f = FAM(r['m'], r['side']); fam[f] = np.maximum(fam.get(f, 0), np.where(hit(r['m'], r['side'], r['T']), w, 0))
    zB = (sum(fam.values()) >= 0.75 - 1e-9) | (sum(hit(r['m'], r['side'], r['T']) for r in VT if r['set'] == 'ALL') > 0)
    C, H, L, YR = candles(D + 'candles/candles_bnb_bch.npz', CO, meta['bars'])
    SLS, RT = (4.0, 4.5, 5.0), (4.0, 4.5, 5.0)
    IDX = {(int(bb), s): i for i, (bb, s) in enumerate(zip(X.bar, X.side))}; SIG = pickle.load(open(WD + '/signals.pkl', 'rb'))
    IX = {k: (lambda ix: ix[np.argsort(BAR[ix], kind='stable')])(np.array([IDX[(int(bb), s)] for bb, s, _ in v], int)) for k, v in SIG.items()}
    AREAS = {CO + '200': [(w, lb, sl, rt) for (w, lb) in IX for sl in SLS for rt in RT]}
n = len(BAR); v2, v2t = v2masks(feat)
EL = np.nonzero(np.isfinite(feat('a5')))[0]; rng = np.random.default_rng(11); M = {}
for nm, m in (('v2', v2), ('zB', zB)):
    for j in range(5): M[f'rnd_{nm}_{j}'] = np.isin(np.arange(n), rng.choice(EL, int(m.sum()), replace=False))
print(CO, 'entries', n, {k: int(m.sum()) for k, m in M.items()}, flush=True)
RRo, XB, OK = outcomes(C, H, L, BAR, G, AR, SLS, RT); RF = np.outer(AR, SLS)
if CO == 'btcx': OK &= XB < 684720  # BTC live surface history ends 2026-09-28 (as review/surf/points.py)
def run(ix, a, q):
    busy = -1; eq = 10000.; pk = eq; dd = 0.; ends = {}; nt = 0; w = 0
    for i in ix:
        if BAR[i] <= busy: continue
        if not OK[i, a, q]: break
        x = RRo[i, a, q] * RF[i, a]; g = (x - FEE * (2 + G[i] * x)) / (1 + FEE); y = int(YR[XB[i, a, q]]); st = ends.get(y, (eq, eq))[0]
        eq *= 1 + g; ends[y] = (st, eq); pk = max(pk, eq); dd = min(dd, eq / pk - 1); nt += 1; w += RRo[i, a, q] > 0; busy = XB[i, a, q]
    yrs = [bb / aa - 1 for aa, bb in ends.values()]
    return dict(net=eq - 10000, n=nt, wr=w / nt if nt else np.nan, dd=dd, worst=min(yrs) if yrs else np.nan, yup=sum(y > 0 for y in yrs), ny=len(yrs))
for area, cells in AREAS.items():
    rows = []
    for (w, lb, sl, rt) in cells:
        ix = IX[(w, lb)]; a = SLS.index(sl); q = RT.index(rt)
        for k, m in M.items(): rows.append(dict(area=area, w=w, lb=lb, sl=sl, ratio=rt, variant=k, **run(ix[~m[ix]], a, q)))
    pd.DataFrame(rows).to_csv(R + f'ctrl3/rnd_{area}.csv.gz', index=False, compression='gzip'); print(area, len(cells), flush=True)
