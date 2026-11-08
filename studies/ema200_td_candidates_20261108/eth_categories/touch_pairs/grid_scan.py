"""Screen independent ETH strategies with either reference star on shared equity."""
from pathlib import Path
import ctypes,sys,tempfile,subprocess
import numpy as np
import pandas as pd
O=Path(__file__).resolve().parent
R=Path.cwd();sys.path.insert(0,str(R/'research/w8_pair_selection_20261108'))
from pairs import Market,module
old=module('impulse',R/'research/stage2_cross_coin_review/v3_adx_impulse_grid_20261107_v1/common.py')
A=dict(w=3,lb=290,sl=4.5,tp=4.5,cap=0,t=0,d=0)
B=dict(w=7,lb=190,sl=4.5,tp=3.5,cap=0,t=0,d=0)
def screen(mode,sl_args):
 with tempfile.TemporaryDirectory() as tmp:
  market=Market('eth',tmp);z=market.z;m=market.m;ind=old.indicators('eth',m) if mode=='adx' else None
  lib=Path(tmp)/'scan.so'
  subprocess.run(['cc','-O3','-shared','-fPIC',str(O/'screen.c'),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
  fn=ctypes.CDLL(str(lib)).screen
  cells=[];seq=[];mapping={}
  for (w,lb),ii in sorted(z['ix'].items()):
   ii=ii[~market.block[ii]]
   for cap in range(5):
    jj=ii[(z['touch'][ii]>=1)&(z['touch'][ii]<=cap)] if cap else ii
    token=jj.tobytes()
    if token not in mapping:mapping[token]=len(seq);seq.append(jj)
    cells.append((w,lb,cap,mapping[token]))
  cells=np.array(cells);uid=np.unique(np.concatenate(seq))
  ix=np.searchsorted(uid,np.concatenate(seq));off=np.r_[0,np.cumsum(list(map(len,seq)))].astype('int64')
  av,bv=[np.ascontiguousarray(market.ledger(p)[0]) for p in [A,B]]
  bars=z['bars'][uid];s=z['side'][uid].astype(float)
  cl,hi,lo,op=[m[k] for k in ('c','h','l','o')]
  print(mode,len(seq),len(cells),len(bars),flush=True)
  for sl in sl_args:
   rf=z['ar'][uid]*sl
   for tp in (3.5,4.,4.5,5.):
    ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
    xx=np.where(z['ok'][uid,ai,qi],z['xb'][uid,ai,qi],-1).astype('int64');rr=z['rr'][uid,ai,qi]
    head=[bars,s,rf,xx,rr,hi,lo,cl,op]
    cuts={0:[0]} if mode=='td' else {}
    if mode=='td':cuts[1]=np.arange(1,min(tp-.5,4)+.001,.25)
    else:
     cuts={5:np.unique(np.r_[.25,np.arange(2,51,2),46.5,47.5]),15:np.unique(np.r_[.25,np.arange(1,41),26.75]),60:np.unique(np.r_[.1,np.arange(.5,16.1,.5),20,25,30])}
    rows=[];evaluated=0
    for tf,grid in cuts.items():
     plans=np.full((len(grid),len(uid)),-1,dtype=np.int64)
     if tf:
      for j,(b,end,side) in enumerate(zip(bars,xx,s)):
       seg=slice(b+1,end if end>=0 else None)
       if tf==1:score=side*((hi if side>0 else lo)[seg]-cl[b])/(rf[j]*cl[b])
       else:
        adx=ind[f'{tf}_adx'];delta=adx[seg]-adx[b]
        score=np.where(np.isfinite(delta)&(side*(ind[f'{tf}_plus'][seg]-ind[f'{tf}_minus'][seg])>0),delta,-np.inf)
       path=np.maximum.accumulate(score);loc=path.searchsorted(grid);fired=loc<len(path);plans[fired,j]=b+1+loc[fired]
     for cut,arm in zip(grid,plans):
      ds=np.arange(1.0 if tf==1 else 1.25,(min(cut,3) if tf==1 else 3)+.001,.25) if tf else np.array([0.])
      if not len(ds): continue
      out=np.empty((len(seq),len(ds),10))
      arrays=[*head,arm,ds,ix,off]  # 13 pointer arguments before anchors
      fn.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*len(arrays)+[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
      ret=fn(len(cl),len(uid),len(seq),len(ds),tp,*[x.ctypes.data for x in arrays],av.ctypes.data,len(av),bv.ctypes.data,len(bv),out.ctypes.data)
      if ret:raise ValueError('Unresolved exit')
      expanded=out[cells[:,3]];evaluated+=len(cells)*len(ds)
      keep=(tf==0)|(expanded[:,:,0]>=18000)|(expanded[:,:,6]>=21500)|(expanded[:,:,8]>=21500)
      if tf:
       # Retain each category's best per cap even when all portfolios are weak.
       for cap in range(5):
        for mask in [(cells[:,0]>=8)&(cells[:,1]<=90),(cells[:,0]<=5)&(cells[:,1]>=180)]:
         group=np.flatnonzero(mask&(cells[:,2]==cap))
         for field in (0,6,8):
          arg=np.unravel_index(expanded[group,:,field].argmax(),(len(group),len(ds)))
          keep[group[arg[0]],arg[1]]=True
      i,k=np.where(keep)
      if len(i):rows.append(np.column_stack([cells[i,:3],np.full(len(i),tf),np.full(len(i),cut),ds[k],expanded[i,k]]))
    cols='w lb cap tf t d net n wins act above fast pairA commonA pairB commonB'.split()
    f=pd.DataFrame(np.concatenate(rows),columns=cols).assign(sl=sl,tp=tp)
    f.to_pickle(f'/tmp/touchgrid_{mode}_{sl:g}_{tp:g}.pkl')
    print(sl,tp,evaluated,len(f),flush=True)
if __name__=='__main__':screen(sys.argv[1],[float(v) for v in sys.argv[2:]])
