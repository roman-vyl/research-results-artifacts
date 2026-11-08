"""SOL full cross of managed exits within supplied geometric regions."""
from pathlib import Path
import sys,tempfile,ctypes,subprocess,gzip,json,copy
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;R=Path.cwd()
F=R/'research/stage2_cross_coin_review/ema200_td_candidates_20261108/eth_categories/touch_pairs/protected/fine'
sys.path.insert(0,str(F))
from run import Market,old,layer
H=np.r_[np.arange(.25,60.01,.25),65,70,75,80,90,100]
AREAS={'wide':[(w,lb) for w in (8,9,10) for lb in (50,60,70,80,90)],
       'narrow':[(w,lb) for w in (3,4,5) for lb in (220,230,240,250,260,270,280,290)]}
LAYERS=[(sl,tp) for sl in (5.5,6.,6.5) for tp in (4.5,5.,6.)]
BASE_FIELDS='solo net wins n protected be saved hurt neutral runner above lost_above savedR hurtR common union samebar dd gap_net'.split()
PERIODS='month_sd month_positive month_worst month_median year_sd year_worst best_year_share y2021 y2022 y2023 y2024 y2025 y2026 net_long net_short'.split()
FIELDS=BASE_FIELDS+PERIODS+['quick','days7','hold_median']
N=len(FIELDS)
def build(tmp):
 src=(F/'cube.c').read_text().replace('#include "drawdown.h"','#include "solo.h"')
 src=src.replace('runner=0,above=0,','runner=0,quick=0,days7=0,above=0,').replace('double eq=10000,savedR=0,hurtR=0;','double eq=10000,savedR=0,hurtR=0,holds[5000];int hn=0;')
 src=src.replace('runner+=tr>=0&&!cut;','runner+=tr>=0&&!cut;if(tr>=0&&!cut){holds[hn++]=(x-tr)/12.;quick+=x-tr<=12;days7+=x-tr>=2016;}')
 src=src.replace(')*19;',f')*{N};')
 src=src.replace('v[18]=stressed;','v[18]=stressed;memcpy(v+19,period_stats,sizeof(period_stats));v[34]=quick;v[35]=days7;v[36]=median(holds,hn);')
 path=Path(tmp)/'kernel.c';path.write_text(src);lib=Path(tmp)/'kernel.so'
 subprocess.run(['cc','-O3','-shared','-fPIC','-I',str(P),str(path),str(P/'native_exits.c'),'-o',str(lib)],check=True)
 cpu=ctypes.CDLL(str(lib));cpu.sweep_be.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p]
 cpu.init_prices.argtypes=[ctypes.c_void_p,ctypes.c_int];cpu.init_periods.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
 return cpu
def prep(m,ind,w,lb,sl,tp,ts):
 view=copy.copy(m);view.z=dict(m.z,ix={(7,lb):m.z['ix'][w,lb]})
 import run
 oldh=run.THRESHOLDS;run.THRESHOLDS=H
 try:return layer(view,ind,lb,sl,tp,ts)
 finally:run.THRESHOLDS=oldh
def calc():
 data=P/'data';data.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as tmp:
  cpu=build(tmp);m=Market('sol',tmp);ind=old.indicators('sol',m.m);cl=m.m['c']
  mon=m.z['time'].astype('datetime64[ms]').astype('datetime64[M]');ends=np.r_[np.flatnonzero(mon[1:]!=mon[:-1]),len(mon)-1].astype('int64');years=(mon[ends].astype('datetime64[Y]').astype(int)+1970).astype('int32')
  cpu.init_prices(cl.ctypes.data,len(cl));cpu.init_periods(ends.ctypes.data,len(ends),years.ctypes.data,1,len(ends)-1)
  total=0
  for family,geometry in AREAS.items():
   for sl,tp in LAYERS:
    ts=np.arange(1.,tp-.49,.25)
    for w,lb in geometry:
     target=data/f'{w}_{lb}_{sl:g}_{tp:g}.npz'
     if target.exists():continue
     b,s,rf,bx,br,arms,labels,adx,be,capv=prep(m,ind,w,lb,sl,tp,ts)
     labels=np.array(labels)
     _,first,rev=np.unique(np.column_stack([adx,be]),axis=0,return_index=True,return_inverse=True);adx=adx[first];be=be[first]
     blocks={};empty=np.zeros((0,6));disabled=np.full((1,len(b)),-1,np.int64)
     def sweep(plans,prot,touch,ds):
      out=np.empty((len(prot),len(ds),5,N))
      args=[cl,m.m['h'],m.m['l'],m.m['o'],b,s,rf,bx,br,plans,ds,prot,touch,capv,empty]
      cpu.sweep_be(len(b),len(ds),len(prot),len(cl),tp,*[v.ctypes.data for v in args],0,out.ctypes.data)
      assert np.isfinite(out[...,0]).all() and np.allclose(out[...,0],out[...,1],atol=1e-5)
      return out
     # Full ΔADX × T × D, including the pure TD control at label 0.
     for ti,t in enumerate(ts):
      ds=np.arange(1.,min(3.,t)+.01,.25)
      blocks[f't{round(t*4)}']=sweep(arms[ti],adx,be,ds).astype('float32')
     ds=np.arange(1.,3.01,.25)
     # ADX-triggered Runner, all D, every unique impulse event.
     runner=[]
     for a in adx:
      runner.append(sweep(a,disabled,disabled,ds)[0].astype('float32'))
     blocks['runner']=np.stack(runner)
     # BE-only with original SL/TP retained.
     blocks['be_only']=sweep(np.full(len(b),-1,np.int64),adx,be,np.array([1.])).astype('float32')
     np.savez_compressed(target,labels=labels,inverse=rev,first=first,**blocks)
     total+=sum(x.shape[0]*x.shape[1]*5 for x in blocks.values())
    print(family,sl,tp,'finished',flush=True)
  cpu.release_prices()
 (P/'design.json').write_text(json.dumps(dict(areas=AREAS,layers=LAYERS,thresholds=H.tolist(),fields=FIELDS,tf=[5,15,60],caps=[0,1,2,3,4],stop_policy='effective next bar; initial stop wins conflict; native MFE >= D before first runner update',months='2021-11..2026-09',years=[2022,2023,2024,2025]),ensure_ascii=False))
if __name__=='__main__':calc()
