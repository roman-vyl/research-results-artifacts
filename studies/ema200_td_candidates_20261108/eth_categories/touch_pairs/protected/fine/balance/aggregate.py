"""Aggregate ETH protection outcomes from the published compressed grid."""
from pathlib import Path
import gzip
import json
import warnings

import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent
H = np.r_[np.arange(1, 1201) / 20, 65, 70, 75, 80, 90, 100]
BINS = [0, 10, 20, 30, 40, 50, 60, 100]
METRICS = ['active', 'hit_active', 'success_hit', 'success_active', 'hurt_active',
           'saved_all', 'hurt_all', 'be_count', 'net_r100', 'gain', 'gap_gain',
           'gain_positive', 'wr_change', 'dd_change']
BANDS = {5: [(5, 7), (7, 9), (9.3, 10.05), (10.5, 12), (12.05, 15)],
         15: [(9.3, 10.05), (20.4, 21.4), (25.55, 27.65)],
         60: [(.65, 1.15), (1.3, 3), (5, 10)]}
BLOCKS = [
    ('5m, ≤4', 4.5, 3.5, 4, 5, 9.30, 10.30, 2.5, 2.75, 1.25, 1.5),
    ('5m, TP 4.5', 4.5, 4.5, 0, 5, 9.1, 10.1, 2.75, 3, 1.25, 1.5),
    ('1h, умеренный T', 4.75, 4.5, 0, 60, .65, 1.15, 2.75, 3, 1.5, 1.75),
    ('1h, поздний T', 4.5, 5, 0, 60, 1.3, 1.8, 4.25, 4.5, 1.5, 1.75),
    ('15m, поздний T', 4.75, 5, 0, 15, 20.4, 21.4, 4, 4.25, 1.5, 1.75),
]


def ratios(arr, names):
    c = dict(zip(names, arr.T))
    n, activated, be = c['n'], c['protected'], c['be']
    saved, hurt = c['saved'], c['hurt']
    assert np.all((saved + hurt <= be) & (be <= activated) & (activated <= n))
    def pct(num, den):
        return np.divide(100 * num, den, out=np.full(len(den), np.nan), where=den > 0)
    gain = c['pair'] - c['td_pair']
    return np.column_stack([pct(activated,n), pct(be,activated), pct(saved,be),
        pct(saved,activated), pct(hurt,activated), pct(saved,n), pct(hurt,n),
        be, 100*(c['savedR']-c['hurtR'])/n, gain, c['gap_pair']-c['td_pair'],
        100*(gain>.005), c['wr']-c['td_wr'], c['dd']-c['td_dd']])


def stats(rows):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        med = np.nanmedian(rows, axis=0)
    # This one column is explicitly a share of improving cells.
    med[METRICS.index('gain_positive')] = rows[:,METRICS.index('gain_positive')].mean()
    return dict(cells=len(rows), cells_with_be=int((rows[:,7]>0).sum()), **dict(zip(METRICS, med)))


def run():
    planes, blocks = [], []
    for tf in [5, 15, 60]:
        for sl in [4, 4.25, 4.5, 4.75, 5]:
            for tp in [3.5, 4, 4.5, 5]:
                arrays = []
                for cap in range(5):
                    file = P.parent / 'data' / f'{sl:g}_{tp:g}_{cap}_{tf}.json.gz'
                    with gzip.open(file) as f:
                        data = json.load(f)
                    for key, seq in data['curves'].items():
                        t, d = map(float, key.split('/'))
                        seq = np.asarray(seq)
                        index = seq[:,0].searchsorted(H, side='right')-1
                        assert index.min() == 0
                        values = ratios(seq, data['fields'])[index]
                        arrays.append(values)
                        for name, *params in BLOCKS:
                            layer = params[:4]
                            h0,h1,t0,t1,d0,d1 = params[4:]
                            if layer==[sl,tp,cap,tf] and t0<=t<=t1 and d0<=d<=d1:
                                blocks.append((name,values[(H>=h0)&(H<=h1)]))
                cube = np.stack(arrays)
                flat = cube.reshape(-1,len(METRICS))
                def record(kind, label, arr):
                    if len(arr):
                        planes.append(dict(tf=tf, sl=sl, tp=tp, kind=kind, label=label, **stats(arr)))
                record('activation','0',flat[flat[:,0]==0])
                for lo, hi in zip(BINS[:-1],BINS[1:]):
                    record('activation',f'{lo}-{hi}',flat[(flat[:,0]>lo)&(flat[:,0]<=hi)])
                for lo, hi in BANDS[tf]:
                    candidate = cube[:,(H>=lo)&(H<=hi)].reshape(-1,len(METRICS))
                    record('threshold',f'{lo:g}-{hi:g}',candidate)
                    if tf==5 and lo==9.3:
                        for left,right in zip(BINS[:-1], BINS[1:]):
                            mask = (candidate[:,0]>left)&(candidate[:,0]<=right)
                            record('band_activation',f'{left}-{right}',candidate[mask])
    frame = pd.DataFrame(planes)
    assert frame[frame.kind=='activation'].cells.sum() == 21_346_200
    summary = []
    for (tf,kind,label),df in frame.groupby(['tf','kind','label'],sort=False):
        gains = df.gain
        summary.append(dict(tf=tf,kind=kind,label=label,planes=len(df),positive_planes=int((gains>.005).sum()),
            cells=df.cells.sum(),cells_with_be=df.cells_with_be.sum(),gain_q25=gains.quantile(.25),
            gain_q75=gains.quantile(.75),**df[METRICS].median().to_dict()))
    def save(df, name):
        df.to_csv(P / (name+'.csv'),index=False,float_format='%.5f')
    save(frame,'planes')
    save(pd.DataFrame(summary),'summary')
    save(pd.DataFrame([dict(name=name,**stats(np.vstack([v for n,v in blocks if n==name])))
                       for name,*_ in BLOCKS]),'plateaus')

if __name__=='__main__':
    run()
