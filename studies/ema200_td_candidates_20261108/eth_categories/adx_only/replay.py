"""ETH narrow portfolio replay with directional ADX as the sole arming signal."""
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(Path.cwd() / "research/w8_pair_selection_20261108"))
from pairs import Market, module

ARCHIVE = Path.cwd() / "research/stage2_cross_coin_review/v3_adx_impulse_grid_20261107_v1"
source = module("archived_impulse", ARCHIVE / "common.py")
TFS = (5, 15, 60)
GRID = np.r_[.1, np.arange(.25, 100.01, .25)]
DIST = np.arange(1.25, 3.01, .25)



def replay(market, indicators, w, lb, sl, tp=4.5):
    z = market.z
    c, hi, lo, op = [market.m[k] for k in ("c", "h", "l", "o")]
    ids = z["ix"][w, lb]
    ids = ids[~market.block[ids]]
    starts, sides = z["bars"][ids], z["side"][ids]
    risks = z["ar"][ids] * sl
    ai, qi = list(z["sls"]).index(sl), list(z["ratios"]).index(tp)
    base_r = z["rr"][ids, ai, qi]
    base_exit = np.where(z["ok"][ids, ai, qi], z["xb"][ids, ai, qi], -1)
    never = len(c) + 1
    cutoff = np.datetime64("2025-01-01", "ms").astype("int64")
    sim = market.sims[len(c)]
    month = z["time"].astype("datetime64[ms]").astype("datetime64[M]")
    sim.z["dayends"] = np.r_[np.flatnonzero(month[1:] != month[:-1]), len(c)-1].astype("int64")
    exit_cache = {}
    portfolio_cache = {}

    def exits(j, arm):
        key = j, arm
        if key not in exit_cache:
            r = np.empty(len(DIST))
            x = np.empty(len(DIST), dtype=np.int64)
            dummy = np.empty_like(x)
            b = starts[j]
            market.lib.exits(len(c), b, arm, sides[j], risks[j]*c[b], tp,
                             *[v.ctypes.data for v in (hi, lo, op, c, DIST)], len(DIST), 0,
                             *[v.ctypes.data for v in (r, x, dummy)])
            exit_cache[key] = r, x
        return exit_cache[key]

    def portfolio(arms, di, verify=False):
        key = di, arms.tobytes()
        if key in portfolio_cache and not verify:
            return portfolio_cache[key]
        busy = -1
        records, indices, multiples = [], [], []
        for j, b in enumerate(starts):
            if b <= busy:
                continue
            r, end = base_r[j], base_exit[j]
            if arms[j] != never:
                rr, xx = exits(j, arms[j])
                r, end = rr[di], xx[di]
            assert end >= 0, "unresolved trade requires marking"
            records.append((b, end, sides[j], c[b], c[b]*(1+sides[j]*r*risks[j]), risks[j]))
            indices.append(j)
            multiples.append(r)
            busy = end
        ledger = np.array(records)
        if verify:
            check, opened = market.ledger(dict(w=w,lb=lb,sl=sl,tp=tp,cap=0,t=0,d=0))
            assert not opened
            np.testing.assert_allclose(ledger,check,rtol=1e-12,atol=1e-8)
        v = sim.run(0, ta=ledger, aa=1, curve=True)
        ids_used = np.array(indices)
        a = arms[ids_used]
        b = starts[ids_used]
        x = ledger[:,1].astype(int)
        r = np.array(multiples)
        active = a != never
        above = r > tp+1e-8
        after = z["time"][x] >= cutoff
        duration = (z["time"][x[active]]-z["time"][a[active]])/3600000
        curve = np.array(v["curve"])
        month_returns = 100*(curve/np.r_[1.,curve[:-1]]-1)
        stats = dict(net=v["net"], wr=v["wr"], dd=-v["dd"], n=len(ledger), act=int(active.sum()),
                     quick=int(sum(duration<=1)), above=int(above.sum()), late_above=int(sum(above & after)),
                     median_extra=float(np.median(r[above]-tp)) if above.any() else None,
                     hold=float(np.median(duration)) if len(duration) else None,
                     days7=int(sum(duration>=24*7)), sd_month=float(month_returns.std()),
                     net_long=v["net_long"], net_short=v["net_short"],
                     **{f"y{year}":value for year,value in v["years"].items()})
        portfolio_cache[key] = stats
        return stats

    rows = []
    initial = portfolio(np.full(len(ids),never),0,True)
    rows.append(dict(tf=0,cut=0,d=0,**initial))
    for tf in TFS:
        adx, plus, minus = [indicators[f"{tf}_{k}"] for k in ("adx","plus","minus")]
        bars = np.full((len(GRID),len(ids)),never,np.int64)
        for j, (b,end,side) in enumerate(zip(starts,base_exit,sides)):
            window = slice(b+1, end if end>=0 else None)
            rise = adx[window]-adx[b]
            aligned = side*(plus[window]-minus[window])>0
            path = np.maximum.accumulate(np.where(aligned & np.isfinite(rise),rise,-np.inf))
            k = path.searchsorted(GRID)
            hit = k < len(path)
            bars[hit,j] = b+1+k[hit]
        for cut,arms in zip(GRID,bars):
            for di,d in enumerate(DIST):
                metrics = portfolio(arms,di)
                if cut == GRID[-1]:
                    assert metrics["act"]==0 and metrics["net"]==initial["net"]
                rows.append(dict(tf=tf,cut=cut,d=d,**metrics))
    out = pd.DataFrame(rows).assign(w=w,lb=lb,sl=sl,tp=tp)
    suffix = "" if tp==4.5 else f"_tp{tp:g}"
    out.to_csv(OUT/f"grid_{w}_{lb}_{sl:g}{suffix}.csv.gz",index=False)


if __name__=="__main__":
    with tempfile.TemporaryDirectory() as tmp:
        market=Market("eth",tmp)
        indicators=source.indicators("eth",market.m)
        if "--initial" in sys.argv:
            for sl in (4,4.25,4.5,4.75,5):
                for tp in (4,4.5,5):
                    if (sl,tp) not in [(4.5,4.5),(4.75,4.5)]:
                        replay(market,indicators,3,290,sl,tp)
        elif "--neighbors" in sys.argv:
            sl,tp = map(float,sys.argv[-2:])
            for w in (3,4):
                for lb in (280,290,300):
                    if (w,lb)!=(3,290): replay(market,indicators,w,lb,sl,tp)
        else:
            for w,lb,sl in [(3,290,4.75),(3,290,4.5),*((w,lb,4.75) for w in (3,4) for lb in (280,290,300) if (w,lb)!=(3,290))]:
                replay(market,indicators,w,lb,sl)
