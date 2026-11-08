"""Single-leg Protected benchmark for the two selected ETH geometries."""
from pathlib import Path
import copy,sys,tempfile,subprocess,ctypes,json
import numpy as np,pandas as pd
OUT=Path(__file__).resolve().parent
F=OUT.parent/'touch_pairs/protected/fine'
sys.path.insert(0,str(F))
from run import Market,old,R,layer,THRESHOLDS
from verify import Review,audit
from regions import rollmin
CASES=[(11,20,5,5,0),(11,20,5,5,4),(5,280,5,4,0)]
def compute():
 with tempfile.TemporaryDirectory() as td:
  m=Market('eth',td);rv=Review(m);cl=m.m['c']
  src=(F/'cube.c').read_text().replace('#include "drawdown.h"','#include "solo.h"')
  cop=Path(td)/'solo.c';cop.write_text(src);lib=Path(td)/'solo.so'
  subprocess.run(['cc','-O3','-shared','-fPIC','-I',str(OUT),'-I',str(F),str(cop),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
  cpu=ctypes.CDLL(str(lib));fn=cpu.sweep_be;fn.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p];fn.restype=None
  cpu.init_prices.argtypes=[ctypes.c_void_p,ctypes.c_int];cpu.init_prices(cl.ctypes.data,len(cl))
  summary=[];floors=[];baselines=[]
  for w,lb,sl,tp,cap in CASES:
   tag=f'{w}/{lb} '+('все' if not cap else '≤4')
   view=copy.copy(m);view.z=dict(m.z,ix={(7,lb):m.z['ix'][w,lb]})
   ts=np.arange(1.5,tp-.49,.25)
   b,s,rf,bx,br,ta,labels,adx,touch,capv=layer(view,rv.ind,lb,sl,tp,ts)
   labels=np.asarray(labels);_,first,rev=np.unique(np.column_stack([adx,touch]),axis=0,return_index=True,return_inverse=True)
   adx=adx[first];touch=touch[first];shape=(len(ts),8,len(rev))
   val=np.full((9,*shape),np.nan)
   cfg=dict(w=w,lb=lb,sl=sl,tp=tp,cap=cap,tf=(60 if w==11 else 5),t=(6 if w==11 else 46.5),d=(3 if w==11 else 1.5))
   live=rv.full(cfg);ctrl=rv.full(dict(cfg,w=10 if w==11 else 3,lb=20 if w==11 else 290,sl=4.75 if w==11 else 4.5,tp=5 if w==11 else 4.5,cap=0,t=0,d=0,tf=0))
   for label,v in [('front',live),('control',ctrl)]:baselines.append(dict(tag=tag,label=label,**{k:v[k] for k in ['net','wr','dd','n']}))
   for i,t in enumerate(ts):
    ds=np.arange(1.25,min(3,t)+.01,.25);out=np.empty((len(first),len(ds),5,19))
    args=[cl,m.m['h'],m.m['l'],m.m['o'],b,s,rf,bx,br,ta[i],ds,adx,touch,capv,np.zeros((0,6))]
    fn(len(b),len(ds),len(first),len(cl),tp,*[x.ctypes.data for x in args],0,out.ctypes.data)
    x=out[rev,:,cap].transpose(1,0,2)
    np.testing.assert_allclose(x[:,:,0],x[:,:,1],atol=1e-6)
    net=x[:,:,0];wr=100*x[:,:,2]/x[:,:,3];dd=x[:,:,17];freq=100*x[:,:,4]/x[:,:,3]
    vals=[net,wr,-dd,net-net[:,0,None],freq,x[:,:,5],x[:,:,18],x[:,:,6],x[:,:,7]]
    val[:,i,:len(ds)]=np.stack(vals)
   for tf in [5,15,60]:
    idx=np.where(labels[:,0]==tf)[0]
    a=val[:,:,:,idx];valid=np.isfinite(a[0]);beat=(a[0]>live['net']+.005)&(a[1]>live['wr']+1e-7)&(-a[2]<live['dd']-1e-7)
    for name,mask in [('вся сетка',valid),('защита 20–40%',valid&(a[4]>=20)&(a[4]<=40))]:
     if mask.sum():
      med=np.median(a[:,mask],axis=1);summary.append(dict(tag=tag,tf=tf,scope=name,n=mask.sum(),wins=(mask&beat).sum(),wins_allow_equal_dd=(mask&(a[0]>live['net']+.005)&(a[1]>live['wr']+1e-7)&(-a[2]<=live['dd']+1e-7)).sum(),max_net=float(a[0][mask].max()),max_net_wr_at_least=max(a[0][mask&(a[1]>=live['wr']-1e-8)],default=np.nan),**dict(zip(['net','wr','negdd','gain','active','be','gap','save','hurt'],med))))
    idx=idx[labels[idx,1]<=60];a=val[:,:,:,idx];hs=labels[idx,1]
    width=11 if tf==60 else 21
    low=np.stack([rollmin(np.nan_to_num(v,nan=-np.inf),width) for v in a])
    crit=(low[3]>.005)&(low[5]>=3)
    for typ,mask in [('positive',crit),('frequent',crit&(low[4]>=20)),('beats_front',crit&(low[0]>live['net']+.005)&(low[1]>live['wr']+1e-7)&(-low[2]<live['dd']-1e-7)),('beats_family_control',crit&(low[0]>ctrl['net']+.005)&(low[1]>ctrl['wr']+1e-7)&(-low[2]<ctrl['dd']-1e-7))]:
     if not mask.any():continue
     i,j,k=np.unravel_index(np.argmax(np.where(mask,low[6],-np.inf)),mask.shape)
     box=a[:,i:i+2,j:j+2,k:k+width].reshape(9,-1)
     row=dict(tag=tag,tf=tf,kind=typ,h0=hs[k],h1=hs[k+width-1],t0=ts[i],t1=ts[i+1],d0=1.25+.25*j,d1=1.50+.25*j,count=box.shape[1],eligible=int(mask.sum()))
     for key,v in zip(['net','wr','negdd','gain','active','be','gap','save','hurt'],box):row[key]=np.median(v);row['min_'+key]=v.min()
     floors.append(row)
   for t,d,tf,h in [(2.5,1.5,5,9.65),(2.75,1.75,60,1.5)]:
    trade,_,_=audit(m,rv,w,lb,sl,tp,cap,t,d,tf,h)
    truth=rv.sim.run(0,ta=trade,aa=1)
    near=val[:,np.where(ts==t)[0][0],int((d-1.25)*4),np.flatnonzero((labels[:,0]==tf)&(labels[:,1]==h))[0]]
    np.testing.assert_allclose([truth['net'],truth['dd'],truth['wr']],[near[0],near[2],near[1]],atol=1e-7)
   print(tag,'done',flush=True)
  for name,rows in [('blocks',floors),('distribution',summary),('baselines',baselines)]:pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
if __name__=='__main__':compute()
