"""Owner 2026-10-25 17:15: checkbox «подтяжка стопа» on the w8v7 surfaces. Scheme agreed 16:40 on BTC W9 LB30: after entry, once 1h ADX(14) has risen >= 1.75 from its
entry-bar value with DI on the trade's side (HTF value visible only after the 1h bar closes), stop = max(initial SL, best price since entry - 0.25 R); TP kept.
Semantics = btc_trail/sim2.py one(): level fills, stop wins over TP on the same bar, decision on bar N acts from N+1. Per entry and per (SL, TP) cell: rr (in R, before fees),
exit bar, ok (resolved before data end / BTC bar 684720). Base (no trail) recomputed and checked against review/full_<c>_surf.npz.
Usage: trail_out.py <c> [wide]  -> trail_<c>[wide].npz"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/ema200_calib/review/calib'); import zc
c = sys.argv[1]; WIDE = len(sys.argv) > 2; D = zc.D; b = zc.B[c]; n = b['n']; BAR = b['bar']; G = b['g'].astype(int)
NB = 684720 if c == 'btc' else None; DELTA, DIST = 1.75, 0.25
if WIDE: SLS = (5.0, 5.5, 6.0, 6.5, 7.0); RT = tuple(np.arange(4.0, 8.01, 0.5))
else: z = np.load(D + f'review/full_{c}_surf.npz'); SLS = list(z['sls']); RT = list(z['ratios'])
X = pd.read_csv(D + zc.P_[c] + f'/entries_e200{c}.csv.gz'); AR = X.ar.values.astype(float)
meta = json.load(open(D + zc.P_[c] + '/meta.json')); Z = np.load(D + 'candles/candles_btc_eth_sol_5m_20261020.npz')
t = Z[c + '_t']; TM = np.arange(t[0], t[-1] + 1, 300000, dtype=np.int64)[:meta['bars']]
Df = pd.DataFrame(np.c_[Z[c + '_h'], Z[c + '_l'], Z[c + '_c']], index=t, columns=['h', 'l', 'c']).reindex(TM)
C = Df.c.ffill().values; H = Df.h.fillna(pd.Series(C, index=TM)).values; L = Df.l.fillna(pd.Series(C, index=TM)).values; NN = len(C)
END = NB if NB else NN
def adx(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); up = h - np.r_[h[0], h[:-1]]; dn = np.r_[l[0], l[:-1]] - l
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    def wl(x):
        o = np.full(len(x), np.nan); s = x[1:n + 1].sum(); o[n] = s
        for i in range(n + 1, len(x)): s = s - s / n + x[i]; o[i] = s
        return o
    atr = wl(tr); p = 100 * wl(pdm) / atr; m = 100 * wl(mdm) / atr; dx = 100 * abs(p - m) / (p + m)
    a = np.full(len(dx), np.nan); st = 2 * n; a[st] = np.nanmean(dx[n + 1:st + 1])
    for i in range(st + 1, len(dx)): a[i] = (a[i - 1] * (n - 1) + dx[i]) / n
    return a, p, m
g = TM // (12 * 300000); first = np.r_[True, g[1:] != g[:-1]]; gi = np.cumsum(first) - 1
a_, p_, m_ = adx(pd.Series(H).groupby(gi).max().values, pd.Series(L).groupby(gi).min().values, pd.Series(C).groupby(gi).last().values)
last = np.r_[first[1:], True]; j = np.where(last, gi, gi - 1); okj = j >= 0; jj = np.clip(j, 0, None)
A = np.where(okj, a_[jj], np.nan); P = np.where(okj, p_[jj], np.nan); M = np.where(okj, m_[jj], np.nan)
sh = (n, len(SLS), len(RT)); RRb = np.zeros(sh); XBb = np.full(sh, NN); OKb = np.zeros(sh, bool); RRt = np.zeros(sh); XBt = np.full(sh, NN); OKt = np.zeros(sh, bool); TRG = np.zeros(sh, bool)
for i in range(n):
    bb, s = int(BAR[i]), int(G[i]); E = C[bb]; fav = H[bb:END] if s > 0 else -L[bb:END]; adv = L[bb:END] if s > 0 else -H[bb:END]; Es = E if s > 0 else -E
    with np.errstate(invalid='ignore'):
        di = (P[bb:END] > M[bb:END]) if s > 0 else (M[bb:END] > P[bb:END]); cond = ((A[bb:END] - A[bb]) >= DELTA) & di & np.isfinite(A[bb:END])
    jA = int(np.argmax(cond)) if cond.any() else None
    for a, k in enumerate(SLS):
        R = k * AR[i] * E; slv = Es - R; hs = np.nonzero(adv[1:] <= slv)[0]; sli = 1 + int(hs[0]) if len(hs) else None
        for q, rt in enumerate(RT):
            tp = Es + rt * R; tpi = np.nonzero(fav[1:] >= tp)[0]; tpj = 1 + int(tpi[0]) if len(tpi) else None
            if sli is None and tpj is None: continue
            end = min(x for x in (sli, tpj) if x is not None); nn = end + 1
            if sli is not None and sli <= end: RRb[i, a, q] = -1.0
            else: RRb[i, a, q] = rt
            XBb[i, a, q] = bb + end; OKb[i, a, q] = True
            stop = np.full(nn, slv)
            if jA is not None and jA + 1 < nn:
                best = np.maximum.accumulate(fav[:nn]); stop[jA + 1:] = np.maximum(slv, best[jA:nn - 1] - DIST * R); TRG[i, a, q] = True
            hit = np.nonzero(adv[1:nn] <= stop[1:])[0]; tph = np.nonzero(fav[1:nn] >= tp)[0]
            k1 = 1 + int(hit[0]) if len(hit) else nn; k2 = 1 + int(tph[0]) if len(tph) else nn
            if k1 <= k2 and k1 < nn: RRt[i, a, q] = (stop[k1] - Es) / R; XBt[i, a, q] = bb + k1
            else: RRt[i, a, q] = rt; XBt[i, a, q] = bb + k2
            OKt[i, a, q] = True
tag = c + ('wide' if WIDE else '')
if not WIDE:
    ok0 = z['ok'] & ((z['xb'] < NB) if NB else True)
    print(tag, 'parity ok', int((ok0 != OKb).sum()), 'rr', int((np.abs(z['rr'] - RRb)[ok0 & OKb] > 1e-9).sum()), 'xb', int((z['xb'] != XBb)[ok0 & OKb].sum()), 'of', int(ok0.sum()))
np.savez_compressed(D + f'review/surf/trail/trail_{tag}.npz', sls=np.array(SLS), ratios=np.array(RT), rr=RRt, xb=XBt, ok=OKt, rr0=RRb, xb0=XBb, ok0=OKb, trig=TRG)
print(tag, 'saved; triggered share', round(float(TRG[OKt].mean()), 3), 'trail exits below TP', int(((RRt < np.array(RT)[None, None, :] - 1e-9) & (RRt > -1 + 1e-9) & OKt).sum()))
