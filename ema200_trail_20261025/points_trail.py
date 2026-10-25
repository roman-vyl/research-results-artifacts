"""Owner 2026-10-25 17:15: rows WITH stop trailing (trail_out.py: 1h ADX rise >= 1.75 from entry + DI on our side, stop 0.25 R behind best price) for every variant of the
w8v7 surfaces (none, t1-t3, v6 w8g*, v7 w8h*), same replay/stats as surf/w8vote/points_side.py (busy until exit, $10k compounding, fees, side split).
Win = trade closed above +0.01 R (a trailed exit at ~entry is not a win), as on the trail page. Usage: points_trail.py <c> [wide] [base]  ('base' = parity run on the no-trail arrays)
-> points_trail_<c>[wide][_base].csv.gz"""
import sys, json, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, '/mnt/project-files/ema200_calib/review/calib'); import zc
c = sys.argv[1]; WIDE = 'wide' in sys.argv[2:]; BASE = 'base' in sys.argv[2:]; D = zc.D; FEE = zc.FEE; b = zc.B[c]; n = b['n']; BAR = b['bar']; G = b['g']
tag = c + ('wide' if WIDE else ''); T = np.load(D + f'review/surf/trail/trail_{tag}.npz'); SLS = list(T['sls']); RT = list(T['ratios'])
RR, XB, OK = (T['rr0'], T['xb0'], T['ok0']) if BASE else (T['rr'], T['xb'], T['ok'])
NB = 684720 if c == 'btc' else None
X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); AR = X.ar.values.astype(float); RF = np.outer(AR, SLS)
Zc = np.load(D + 'candles/candles_btc_eth_sol_5m_20261020.npz'); T0 = int(Zc[c + '_t'][0]); NBR = int(XB.max()) + 2; TMS = T0 + np.arange(NBR, dtype=np.int64) * 300000
YR = pd.to_datetime(TMS, unit='ms', utc=True).year.values; CUT = int(np.searchsorted(TMS, int(pd.Timestamp('2023-07-01', tz='UTC').value // 10**6)))
tn = X.touch.values.astype(float); TB = {N: ~(np.isfinite(tn) & (tn >= 1) & (tn <= N)) for N in (1, 2, 3)}
MK = np.load(D + f'review/surf/w8vote/maskwin7_{c}.npz')['blocked']; M6 = np.load(D + f'review/surf/w8vote/maskwin6_{c}.npz')['blocked']; assert len(MK) == n
Z0 = np.zeros(n, bool)
SETS = {'none': Z0, 't1': TB[1], 't2': TB[2], 't3': TB[3], 'w8g': M6, 'w8g_t1': M6 | TB[1], 'w8g_t2': M6 | TB[2], 'w8g_t3': M6 | TB[3], 'w8h': MK, 'w8h_t1': MK | TB[1], 'w8h_t2': MK | TB[2], 'w8h_t3': MK | TB[3]}
WT = 0.0 if BASE else 0.01
def stats(tr):
    eq = 10000.0; peak = eq; dd = 0.0; ends = {}
    for x, s, xb in tr:
        y = int(YR[xb]); st = ends.get(y, (eq, eq))[0]; g = (x - FEE * (2.0 + s * x)) / (1.0 + FEE); eq *= 1.0 + g; ends[y] = (st, eq); peak = max(peak, eq); dd = min(dd, eq / peak - 1)
    return eq - 10000.0, dd, {y: round(bb / a - 1, 4) for y, (a, bb) in ends.items()}
def job(cell):
    w, lb = cell; ix = b['IX'][cell]; rows = []
    if NB: ix = ix[BAR[ix] < NB]
    for name, B in SETS.items():
        ixk = ix[~B[ix]]
        for a in range(len(SLS)):
            for q in range(len(RT)):
                busy = -1; tr = []; Rr = []; wins = 0
                for i in ixk:
                    if BAR[i] <= busy: continue
                    if not OK[i, a, q]: break
                    rr = RR[i, a, q]; rf = RF[i, a]; tr.append((rr * rf, G[i], XB[i, a, q])); Rr.append(rr - FEE * (2 + G[i] * rr * rf) / rf); wins += rr > WT; busy = XB[i, a, q]
                Rr = np.array(Rr); gs = np.array([t[1] for t in tr]); side = {}
                for k_, sg in (('long', 1), ('short', -1)):
                    tk = [t for t in tr if t[1] == sg]; side[f'net_{k_}'] = stats(tk)[0] if tk else 0.0; side[f'r_{k_}'] = float(Rr[gs == sg].sum()) if len(Rr) else 0.0; side[f'n_{k_}'] = len(tk)
                if tr:
                    net, dd, yrs = stats(tr); a_ = [x for x in tr if x[2] < CUT]; b_ = [x for x in tr if x[2] >= CUT]
                    ni = stats(a_)[0] if a_ else 0.0; no = stats(b_)[0] if b_ else 0.0; gl = -Rr[Rr < 0].sum(); gw = Rr[Rr > 0].sum()
                else: net, dd, yrs, ni, no, gl, gw = 0.0, 0.0, {}, 0.0, 0.0, 0, 0
                rows.append(dict(w=w, lb=lb, sl=SLS[a], ratio=RT[q], variant=name, signals=len(ix), kept=len(ixk), trades=len(tr), wr=wins / len(tr) if tr else np.nan,
                                 pf=gw / gl if gl > 0 else np.nan, net=net, dd=dd, netR=float(Rr.sum()) if len(Rr) else 0.0, is_net=ni, oos_net=no, years=json.dumps({str(k): v for k, v in yrs.items()}), **side))
    return rows
if __name__ == '__main__':
    with mp.get_context('fork').Pool(4) as p: R = [r for rs in p.map(job, sorted(b['IX'])) for r in rs]
    P = pd.DataFrame(R); P.to_csv(D + f'review/surf/trail/points_trail_{tag}{"_base" if BASE else ""}.csv.gz', index=False, compression='gzip'); print(tag, 'base' if BASE else 'trail', 'rows', len(P), flush=True)
