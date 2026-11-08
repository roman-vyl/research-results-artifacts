from pathlib import Path
import ctypes,sys,tempfile,subprocess
import numpy as np,pandas as pd
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent));from grid_scan import A,Market,old,R
H=np.unique(np.r_[.1,np.arange(.25,10.01,.25),np.arange(10.5,50.01,.5),np.arange(51.,76.),100.])
COLS='solo pair wins n protected be saved hurt neutral runner above lost_above savedR hurtR common union samebar'.split()

def prepare(m,w,lb,sl,tp,ind):
 z=m.z;c=m.m
 ids=z['ix'][w,lb];ids=ids[~m.block[ids]]
 b=z['bars'][ids];s=z['side'][ids].astype(float);rf=sl*z['ar'][ids]
 ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
 xx=z['xb'][ids,ai,qi];rr=z['rr'][ids,ai,qi]
 assert z['ok'][ids,ai,qi].all()
 ts=np.round(np.arange(1.5,min(tp-1.25,4)+.001,.25),2)
 arms=np.full((len(ts),len(b)),-1,'int64')
 labels=[(0,0)]+[(tf,h) for tf in (5,15,60) for h in H]
 adx=np.full((len(labels),len(b)),-1,'int64');touch=adx.copy()
 for j,(start,end,side) in enumerate(zip(b,xx,s)):
  seg=slice(start+1,end);p=c['c'][start]
  fav=(c['h'] if side>0 else c['l'])[seg]
  path=np.maximum.accumulate(side*(fav-p)/(p*rf[j]));ix=path.searchsorted(ts);found=ix<len(path)
  arms[found,j]=start+1+ix[found]
  # Include original exit bar in BE-touch search, but never in activation decisions.
  adv=(c['l'] if side>0 else c['h'])[start+1:end+1]
  crossed=start+1+np.flatnonzero(side*(adv-p)<=0)
  for k,tf in enumerate((5,15,60)):
   ax,plus,minus=[ind[f'{tf}_{name}'] for name in ('adx','plus','minus')]
   delta=ax[seg]-ax[start]
   rises=np.maximum.accumulate(np.where(np.isfinite(delta)&(side*(plus[seg]-minus[seg])>0),delta,-np.inf))
   loc=rises.searchsorted(H);mask=loc<len(rises);rows=1+k*len(H)+np.flatnonzero(mask)
   hits=start+1+loc[mask];adx[rows,j]=hits
   first=crossed.searchsorted(hits,side='right');has=first<len(crossed)
   touch[rows[has],j]=crossed[first[has]]
 return b,s,rf,xx,rr,ts,arms,labels,adx,touch,np.nan_to_num(z['touch'][ids],nan=-1).astype('int64')

def compute(w,lb,sls,tps):
 with tempfile.TemporaryDirectory() as tmp:
  lib=Path(tmp)/'be.so';subprocess.run(['cc','-O3','-shared','-fPIC',str(OUT/'protect.c'),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
  fn=ctypes.CDLL(str(lib)).sweep_be;fn.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p];fn.restype=None
  m=Market('eth',tmp);c=m.m;anchor=m.ledger(A)[0];ind=old.indicators('eth',c)
  for sl in sls:
   for tp in tps:
    b,s,rf,xx,rr,ts,ta,labels,adx,touch,touch_n=prepare(m,w,lb,sl,tp,ind)
    dfs=[]
    for t,td in zip(ts,ta):
     ds=np.arange(1.25,min(t,3)+.001,.25);out=np.empty((len(labels),len(ds),5,len(COLS)))
     args=[c['c'],c['h'],c['l'],c['o'],b,s,rf,xx,rr,td,ds,adx,touch,touch_n,anchor]
     fn(len(b),len(ds),len(labels),len(c['c']),tp,*[v.ctypes.data for v in args],len(anchor),out.ctypes.data)
     cap=np.arange(5);df=pd.DataFrame(out.reshape(-1,len(COLS)),columns=COLS)
     i,j,k=np.indices(out.shape[:3]).reshape(3,-1)
     ref=out[0,j,k];df['dnet']=df.pair-ref[:,1];df['delta_solo']=df.solo-ref[:,0]
     df['wrpair']=100*(df.wins+36)/(df.n+92);df['dwr']=df.wrpair-100*(ref[:,2]+36)/(ref[:,3]+92)
     df['cap']=k;df['tf']=np.asarray(labels)[i,0];df['h']=np.asarray(labels)[i,1];df['t']=t;df['d']=ds[j]
     dfs.append(df)
    data=pd.concat(dfs,ignore_index=True);data.to_pickle(f'/tmp/protected_{w}_{lb}_{sl:g}_{tp:g}.pkl',compression='gzip')
    print(w,lb,sl,tp,len(data),flush=True)
if __name__=='__main__':
 compute(7,170,[4,4.25,4.5,4.75,5],[3.5,4,4.5,5])
