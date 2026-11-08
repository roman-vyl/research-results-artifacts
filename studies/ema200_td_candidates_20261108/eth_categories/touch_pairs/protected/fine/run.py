"""Factorial replay with the same pre-entry filters, risk and distance in both arms."""
from pathlib import Path
import sys,tempfile,ctypes,subprocess
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent))
from sweep import Market,old,R,A,COLS

THRESHOLDS=np.r_[np.round(np.arange(.05,60.001,.05),2),65,70,75,80,90,100]

def layer(m,ind,lb,sl,tp,ts):
 z,c=m.z,m.m;ids=z['ix'][7,lb];ids=ids[~m.block[ids]]
 b=z['bars'][ids];s=z['side'][ids].astype(float);rf=z['ar'][ids]*sl
 ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
 xx=z['xb'][ids,ai,qi];rr=z['rr'][ids,ai,qi];assert z['ok'][ids,ai,qi].all()
 arms=np.full((len(ts),len(b)),-1,np.int64)
 labels=[(0,0)]+[(tf,h) for tf in (5,15,60) for h in THRESHOLDS]
 adx=np.full((len(labels),len(b)),-1,np.int64);be=adx.copy()
 for j,(start,end,side) in enumerate(zip(b,xx,s)):
  seg=slice(start+1,end);p=c['c'][start]
  fv=(c['h'] if side>0 else c['l'])[seg];path=np.maximum.accumulate(side*(fv-p)/(p*rf[j]));loc=path.searchsorted(ts);sel=loc<len(path);arms[sel,j]=start+1+loc[sel]
  adv=(c['l'] if side>0 else c['h'])[start+1:end+1]
  cross=start+1+np.flatnonzero(side*(adv-p)<=0)
  for i,tf in enumerate((5,15,60)):
   ax,di,dm=(ind[f'{tf}_{v}'] for v in ('adx','plus','minus'));delta=ax[seg]-ax[start]
   levels=np.maximum.accumulate(np.where(np.isfinite(delta)&(side*(di[seg]-dm[seg])>0),delta,-np.inf))
   pos=levels.searchsorted(THRESHOLDS);sel=pos<len(levels);rows=1+i*len(THRESHOLDS)+np.flatnonzero(sel);hit=start+1+pos[sel]
   adx[rows,j]=hit;at=cross.searchsorted(hit,side='right');valid=at<len(cross);be[rows[valid],j]=cross[at[valid]]
 return b,s,rf,xx,rr,arms,labels,adx,be,np.nan_to_num(z['touch'][ids],nan=-1).astype('int64')
METRICS=COLS+['dd','gap_pair']
def kernel(tmp):
    path=P/'cube.c'
    lib=Path(tmp)/'sweep.so';subprocess.run(['cc','-O3','-shared','-fPIC','-I',str(P),str(path),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
    cpu=ctypes.CDLL(str(lib));cpu.sweep_be.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p];cpu.sweep_be.restype=None
    cpu.init_prices.argtypes=[ctypes.c_void_p,ctypes.c_int];cpu.init_prices.restype=None
    return cpu

def run(lb=170,sls=(4,4.25,4.5,4.75,5),tps=(3.5,4,4.5,5)):
 with tempfile.TemporaryDirectory() as tmp:
  cpu=kernel(tmp);m=Market('eth',tmp);c=m.m;anchor=m.ledger(A)[0];ind=old.indicators('eth',c);cpu.init_prices(c['c'].ctypes.data,len(c['c']))
  for sl in sls:
   for tp in tps:
    ts=np.arange(1.5,tp-.5+.001,.25)
    b,s,rf,xx,rr,arms,labels,adx,be,ct=layer(m,ind,lb,sl,tp,ts)
    _,first,inverse=np.unique(np.hstack([adx,be]),axis=0,return_index=True,return_inverse=True)
    order=np.argsort(first);first=first[order];inverse=np.argsort(order)[inverse];blocks={} 
    for t,td in zip(ts,arms):
     ds=np.arange(1.25,min(t,3)+.001,.25);out=np.empty((len(first),len(ds),5,len(METRICS)));args=[c['c'],c['h'],c['l'],c['o'],b,s,rf,xx,rr,td,ds,adx[first],be[first],ct,anchor]
     cpu.sweep_be(len(b),len(ds),len(first),len(c['c']),tp,*[v.ctypes.data for v in args],len(anchor),out.ctypes.data)
     blocks[f't{int(t*4)}']=out
    np.savez_compressed(f'/tmp/eth_cube_{lb}_{sl:g}_{tp:g}.npz',labels=np.array(labels),inverse=inverse,**blocks)
    print(lb,sl,tp,len(first),flush=True)
  cpu.release_prices()
if __name__=='__main__':run() if len(sys.argv)==1 else run(int(sys.argv[1]),[float(sys.argv[2])],[float(sys.argv[3])])
