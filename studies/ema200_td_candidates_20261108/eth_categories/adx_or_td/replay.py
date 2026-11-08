"""Offline ETH 3/290 replay. Run from the Research Service repository root."""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "research/w8_pair_selection_20261108"))
from pairs import Market, module

CROSS = ROOT / "research/stage2_cross_coin_review"
old = module("adx_v3", CROSS / "v3_adx_impulse_grid_20261107_v1/common.py")
DIST = np.arange(1.75, 3.01, .25)
GRID = np.r_[.1, np.arange(.25, 100.01, .25)]
SL, TP, TRIGGER = 4.75, 4.5, 4.0


def evaluate(market):
    z, candles = market.z, market.m
    ind = old.indicators("eth", candles)
    close, high, low, opening = (candles[k] for k in ("c", "h", "l", "o"))
    ids = z["ix"][3, 290]
    ids = ids[~market.block[ids]]
    starts = z["bars"][ids]
    sides = z["side"][ids]
    risk = SL * z["ar"][ids]
    ai = list(z["sls"]).index(SL)
    qi = list(z["ratios"]).index(TP)
    ends = np.where(z["ok"][ids, ai, qi], z["xb"][ids, ai, qi], -1)
    base_r = z["rr"][ids, ai, qi]
    never = len(close) + 1
    td = np.full(len(ids), never)
    scores = {tf: [] for tf in (5, 15)}
    for j, (b, end, side) in enumerate(zip(starts, ends, sides)):
        after = slice(b + 1, end if end >= 0 else None)
        fav = (high if side > 0 else low)[after]
        hits = np.flatnonzero(side * (fav - close[b]) / (risk[j] * close[b]) >= TRIGGER)
        if len(hits):
            td[j] = b + 1 + hits[0]
        for tf, paths in scores.items():
            adx, plus, minus = (ind[f"{tf}_{k}"] for k in ("adx", "plus", "minus"))
            delta = adx[after] - adx[b]
            aligned = side * (plus[after] - minus[after]) > 0
            paths.append(np.maximum.accumulate(np.where(aligned & np.isfinite(delta), delta, -np.inf)))

    cache = {}
    def outcomes(j, arm):
        key = j, arm
        if key not in cache:
            rr = np.empty(len(DIST))
            xx = np.empty(len(DIST), np.int64)
            aux = np.empty_like(xx)
            b = starts[j]
            market.lib.exits(len(close), b, arm, sides[j], risk[j]*close[b], TP,
                             *[v.ctypes.data for v in (high, low, opening, close, DIST)],
                             len(DIST), 0, *[v.ctypes.data for v in (rr, xx, aux)])
            cache[key] = rr, xx
        return cache[key]

    sim = market.sims[len(close)]
    rows = []
    audit = []
    base_returns = {}
    above_baseline = {}
    for tf in (0, 5, 15):
        paths = scores.get(tf, [])
        if tf:
            adx_bars = np.full((len(ids),len(GRID)), never, np.int64)
            for j,path in enumerate(paths):
                offsets = path.searchsorted(GRID)
                found = offsets < len(path)
                adx_bars[j,found] = starts[j]+1+offsets[found]
        for k,cut in enumerate(GRID if tf else [0]):
            adx = adx_bars[:,k] if tf else np.full(len(ids),never)
            arms = np.minimum(adx,td)
            returns = np.broadcast_to(base_r[:,None],(len(ids),len(DIST))).copy()
            exits = np.broadcast_to(ends[:,None],returns.shape).copy()
            for j in np.flatnonzero(arms<never):
                returns[j],exits[j] = outcomes(j,arms[j])
            for di,d in enumerate(DIST):
                used = []
                busy = -1
                for j,b in enumerate(starts):
                    if b>busy:
                        assert exits[j,di]>=0
                        used.append(j)
                        busy=exits[j,di]
                used=np.array(used)
                b,x,s,r,arm=starts[used],exits[used,di],sides[used],returns[used,di],arms[used]
                ta=np.column_stack((b,x,s,close[b],close[b]*(1+s*r*risk[used]),risk[used]))
                summary=sim.run(0,ta=ta,aa=1)
                active=arm<never
                above=r>TP+1e-8
                adx_first=adx[used]<td[used]
                adx_only=adx_first & (td[used]==never)
                ties=active & (adx[used]==td[used])
                keys=set(zip(b[above],s[above]))
                if not tf:
                    above_baseline[d]=keys
                    base_returns[d]=dict(zip(zip(b,s),r))
                    reference,_=market.ledger(dict(w=3,lb=290,cap=0,sl=SL,tp=TP,t=TRIGGER,d=d))
                    np.testing.assert_allclose(ta,reference,rtol=1e-12,atol=1e-8)
                hold=(z["time"][x[active]]-z["time"][arm[active]]) / 3600000
                bonus=r[above]-TP
                if tf==5 and cut==47.5 and d in (1.75,2):
                    for pos in np.flatnonzero(adx_first):
                        j=used[pos]
                        audit.append(dict(distance=d,entry=str(z['time'][b[pos]].astype('datetime64[ms]')),
                            side='long' if s[pos]>0 else 'short',
                            activation=str(z['time'][arm[pos]].astype('datetime64[ms]')),
                            exit=str(z['time'][x[pos]].astype('datetime64[ms]')),
                            td_would_activate=bool(td[j]<never),
                            td_R=base_returns[d].get((b[pos],s[pos])), hybrid_R=r[pos],
                            delta_adx=float(ind['5_adx'][arm[pos]]-ind['5_adx'][b[pos]])))
                rows.append(dict(tf=tf,threshold=cut,d=d,n=len(b),active=int(active.sum()),
                        adx_first=int(adx_first.sum()),adx_only=int(adx_only.sum()),ties=int(ties.sum()),
                        above=int(above.sum()),fresh=len(keys-above_baseline[d]),lost=len(above_baseline[d]-keys),
                        above_adx=int((above&adx_first).sum()),above_pct=100*np.mean(above),
                        early_above=int((above&(z["time"][x]<np.datetime64('2025-01-01','ms').astype('int64'))).sum()),
                        median_extra=float(np.median(bonus)) if len(bonus) else 0,
                        extra_sum=float(bonus.sum()),quick=int((hold<=1).sum()),hold=float(np.median(hold)),
                        net=summary["net"],wr=summary["wr"],dd=-summary["dd"],
                        **{f'y{year}':v for year,v in summary['years'].items()}))
    frame=pd.DataFrame(rows)
    pd.DataFrame(audit).to_csv(OUT/"sample_trades.csv",index=False)
    frame.to_csv(OUT/"grid.csv.gz",index=False)
    for tf in (5,15):
        for d in DIST:
            a=frame[(frame.tf==tf)&(frame.d==d)].iloc[-1]
            base=frame[(frame.tf==0)&(frame.d==d)].iloc[0]
            assert a.adx_first==0 and a.net==base.net and a.above==base.above
    return frame


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        evaluate(Market("eth",tmp))
