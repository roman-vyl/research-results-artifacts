"""Owner rule 20:36: EMA200 bounce resolves within hours. Zone vote B, SL 4-6.5 x TP 4-8R, all W x LB: per cell net/WR/DD/years + median/90% hours to TP and to SL."""
import sys, json, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, '/mnt/project-files/ema200_calib/review/calib'); import zc, vote2
D = '/mnt/project-files/ema200_calib/'; FEE = 0.0004; _s = open('run.py').read(); exec(_s[_s.index('def candles'):_s.index('def v2masks')])
c = sys.argv[1]; b = zc.B[c]; X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); meta = json.load(open(D + zc.P_[c] + '/meta.json'))
BAR = b['bar'].astype(int); G = b['g'].astype(int); AR = X.ar.values.astype(float)
zB = (vote2.score('v1', c, 'linear') >= 0.75 - 1e-9) | vote2.veto(c, 'v1')
C, H, L, YR = candles(D + 'candles/candles_btc_eth_sol_5m_20261020.npz', c, meta['bars'])
SLS = (4.0, 4.25, 4.5, 4.75, 5.0, 5.5, 6.0, 6.5); RT = tuple(np.arange(3.0, 8.01, 0.5)); RRo, XB, OK = outcomes(C, H, L, BAR, G, AR, SLS, RT); RF = np.outer(AR, SLS)
if c == 'btc': OK &= XB < 684720
def job(key):
    ix = b['IX'][key]; ix = ix[~zB[ix]]; rows = []
    for a, sl in enumerate(SLS):
        for q, rt in enumerate(RT):
            busy = -1; eq = 1e4; pk = eq; dd = 0; ends = {}; hw = []; hl = []; nl = 0; gl = 0.0; gs = 0.0; tpp = []; yg = {}
            for i in ix:
                if BAR[i] <= busy: continue
                if not OK[i, a, q]: break
                rr = RRo[i, a, q]; x = rr * RF[i, a]; g = (x - FEE * (2 + G[i] * x)) / (1 + FEE); y = int(YR[XB[i, a, q]]); st = ends.get(y, (eq, eq))[0]
                eq *= 1 + g; ends[y] = (st, eq); pk = max(pk, eq); dd = min(dd, eq / pk - 1); h = (XB[i, a, q] - BAR[i]) / 12
                (hw if rr > 0 else hl).append(h); busy = XB[i, a, q]
                tpp.append(100 * rt * RF[i, a]); yg[y] = yg.get(y, 0) + g
                if G[i] > 0: gl += g
                else: gs += g
            yrs = [bb / aa - 1 for aa, bb in ends.values()]; n = len(hw) + len(hl)
            rows.append(dict(w=key[0], lb=key[1], sl=sl, ratio=rt, net=eq - 1e4, n=n, wr=len(hw) / n if n else np.nan, dd=dd, worst=min(yrs) if yrs else np.nan,
                             yup=sum(v > 0 for v in yrs), ny=len(yrs), tp_h=np.median(hw) if hw else np.nan, tp_h90=np.percentile(hw, 90) if hw else np.nan,
                             sl_h=np.median(hl) if hl else np.nan, long_g=gl, short_g=gs, tp_pct=np.median(tpp) if tpp else np.nan,
                             top_year=max(yg.values()) / sum(v for v in yg.values() if v > 0) if yg and any(v > 0 for v in yg.values()) else np.nan))
    return rows
if __name__ == '__main__':
    with mp.get_context('fork').Pool(4) as p: R = [r for rs in p.map(job, sorted(b['IX'])) for r in rs]
    pd.DataFrame(R).to_csv(f'fast2_{c}.csv.gz', index=False, compression='gzip'); print(c, len(R))
