"""Export the W8/no-SPOT TD cube. Usage: python prepare.py RESEARCH_SERVICE [btc|eth|sol ...]."""
from pathlib import Path
import argparse
import gzip
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WIDTHS = list(range(3, 15))
LOOKBACKS = list(range(20, 301, 10))
# Fixed-point precision, after conversion to the units shown in the UI.
SCALES = [100, 1000, 1, 1000, 1, 1000, 1000]
MISSING = -2147483648


def metrics(values, fields, full_years):
    at = lambda name: values[fields.index(name)]
    annual = np.stack([at('return_'+str(y)) for y in full_years])
    valid = np.isfinite(annual)
    worst = np.where(valid.any(axis=0), np.where(valid, annual, np.inf).min(axis=0), np.nan)
    return np.stack([at('net_pnl'), 100*at('win_rate'), at('realised_trade_count'),
                     -100*at('max_drawdown_mtm_pct'), at('armed'), at('profit_factor'), 100*worst])


def export(root, coin):
    pack = root/'research/w8_td_geometry/engine_level/data'/coin
    meta = json.loads((pack/'index.json').read_text())
    assert meta['execution_model']=='research_managed_stop_level'
    fields = meta['fields']
    years = range(2021 if coin=='btc' else 2022, 2026)
    source = Path.home()/f'BBB_data/research/analysis/{coin.upper()}USDT.P/ema200/w8_or_sp109_no_spot_5d/runs.csv'
    df = pd.read_csv(source,usecols=lambda c:c in set(fields)|{'min_current_width_atr','untouched_lookback','sl_atr_multiplier','tp_sl_ratio','touch_max','w8_or_sp109'})
    df = df[df.w8_or_sp109==1].copy()
    df['touch_max']=df.touch_max.fillna(0)
    df['armed']=0
    dst=HERE/'data'/coin
    dst.mkdir(parents=True,exist_ok=True)
    layers=[]
    for sl,tp in meta['layers']:
        if tp<=3: continue
        key=f'{sl:g}_{tp:g}'
        group=df[(df.sl_atr_multiplier==sl)&(df.tp_sl_ratio==tp)]
        blocks=[[] for _ in range(4)]
        for cap,rows in enumerate(blocks):
            base=group[group.touch_max==cap].sort_values(['min_current_width_atr','untouched_lookback'])
            assert list(zip(base.min_current_width_atr,base.untouched_lookback))==[(w,lb) for w in WIDTHS for lb in LOOKBACKS]
            rows.append(metrics(base[fields].to_numpy().T,fields,years))
        coords=[[0,0]]
        for t in meta['trigger_r']:
            if t>tp-.5:continue
            with gzip.open(pack/f'{key}_{4*t:g}.gz') as f:
                src=np.frombuffer(f.read(),dtype='<f4').reshape(10,len(fields),12,348)
            keep=min(12,int(t*4))
            coords.extend([t,(di+1)/4] for di in range(keep))
            for cap,rows in enumerate(blocks):
                batch=metrics(src[5+cap,:,:keep].astype('float64'),fields,years).transpose(1,0,2)
                rows.extend(batch)
        for cap,rows in enumerate(blocks):
            # Delta along geometries, with byte lanes contiguous to compress repeated plateaus.
            raw=np.stack(rows)
            scaled=np.rint(raw*np.asarray(SCALES)[None,:,None])
            finite=np.isfinite(scaled)
            assert (abs(scaled[finite])<2147483647).all()
            ints=np.where(finite,scaled,MISSING).astype('<i4')
            diff=np.diff(ints,axis=2,prepend=np.zeros_like(ints[:,:,:1]))
            shuffled=diff.astype('<i4').view('u1').reshape(-1,4).T.copy()
            (dst/f'{key}_{cap}.gz').write_bytes(gzip.compress(shuffled.tobytes(),compresslevel=5,mtime=0))
        layers.append(dict(sl=sl,tp=tp,key=key,coords=coords))
    (dst/'index.json').write_text(json.dumps(layers,separators=(',',':')))
    print(coin,len(layers),sum((len(x['coords'])-1)*348*4 for x in layers),flush=True)


if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('root',type=Path)
    args.add_argument('coins',nargs='*')
    opt=args.parse_args()
    for c in opt.coins or ['btc','eth','sol']:export(opt.root,c)
