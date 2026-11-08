"""Publish single-account slices, extending the existing family scan only for missing data."""
from pathlib import Path
import sys,tempfile,ctypes,subprocess,json,gzip,copy
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
from family import F,R,Market,Review,layer,rollmin
from read_cube import Cube
from verify import audit,star
FIELDS='net wr dd n active be saved hurt savedR hurtR gap above msd mpos mworst ysd yworst y2021 y2022 y2023 y2024 y2025 y2026'.split()
GROUPS={'wide':(11,20,0),'wide4':(11,20,4),'narrow':(5,280,0),'middle':(7,170,0)}
def write(name,obj):
 with (P/name).open('w') as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def lib(tmp):
 s=(F/'cube.c').read_text().replace('#include "drawdown.h"','#include "periods.h"')
 s=s.replace('int pn=-1','double cal[11]={0}; int pn=-1').replace('pair=equity_scan','periods(ledger,n,cl,cal); pair=equity_scan')
 s=s.replace(')*19;',')*30;').replace('v[18]=stressed;','v[18]=stressed;memcpy(v+19,cal,sizeof(cal));')
 src=Path(tmp)/'cube.c';src.write_text(s);path=Path(tmp)/'cube.so'
 subprocess.run(['cc','-O3','-shared','-fPIC','-I',str(P),'-I',str(P.parent),'-I',str(F),str(src),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(path)],check=True)
 cpu=ctypes.CDLL(str(path));cpu.sweep_be.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p];cpu.sweep_be.restype=None
 cpu.init_prices.argtypes=[ctypes.c_void_p,ctypes.c_int];cpu.calendar.argtypes=[ctypes.c_void_p]*3+[ctypes.c_int]
 return cpu
def vector(x):
 return np.column_stack((x[:,0],100*x[:,2]/x[:,3],x[:,17],x[:,3:8],x[:,12:14],x[:,18],x[:,10],x[:,19:]))
def run():
 (P/'data').mkdir(exist_ok=True);blocks=[];freqs=[];counts=[];refs={}
 with tempfile.TemporaryDirectory() as tmp:
  cpu=lib(tmp);m=Market('eth',tmp);rv=Review(m);cl=m.m['c'];cpu.init_prices(cl.ctypes.data,len(cl))
  tm=m.z['time'].astype('datetime64[ms]');mo=tm.astype('datetime64[M]');ends=np.r_[np.flatnonzero(mo[1:]!=mo[:-1]),len(mo)-1].astype('int64')
  yrs=(mo[ends].astype('datetime64[Y]').astype(int)+1970).astype('int64');complete=((mo[ends]>mo[0])&(mo[ends]<mo[-1])).astype('int64')
  cpu.calendar(ends.ctypes.data,yrs.ctypes.data,complete.ctypes.data,len(ends))
  def perf(a):
   v=rv.sim.run(0,ta=a,aa=1,curve=True);curve=np.array(v['curve']);ret=100*(curve/np.r_[1,curve[:-1]]-1);mr=ret[complete.astype(bool)];ys=list(v['years'].values())
   return dict(zip(FIELDS[:4],[v['net'],v['wr'],-v['dd'],v['orders']]),msd=mr.std(),mpos=100*(mr>1e-8).mean(),mworst=mr.min(),ysd=np.std(ys[1:-1]),yworst=min(ys[1:-1]),**{'y'+k:x for k,x in v['years'].items()})
  for g,(w,lb,cap) in GROUPS.items():
   narrow=g=='narrow';middle=g=='middle'
   cfg=dict(w=w,lb=lb,sl=5,tp=4 if narrow else 5,cap=cap,tf=5 if narrow else 60,t=46.5 if narrow else 6,d=1.5 if narrow else 3)
   refcfg=dict(w=7 if middle else 3 if narrow else 10,lb=190 if middle else 290 if narrow else 20,sl=4.5 if narrow or middle else 4.75,tp=3.5 if middle else 4.5 if narrow else 5,cap=0,t=0,d=0,tf=0)
   front=audit(m,rv,w,lb,4.75,3.5,0,2.5,1.25,5,9.65)[0] if middle else rv.ledger(cfg)
   refs[g]={'family':perf(rv.ledger(refcfg)),'front':perf(front)}
  for w,lb in [(11,20),(5,280),(7,170)]:
   view=copy.copy(m);view.z=dict(m.z,ix={(7,lb):m.z['ix'][w,lb]})
   for sl in [4,4.25,4.5,4.75,5]:
    for tp in [3.5,4,4.5,5]:
     ts=np.arange(1.5,tp-.49,.25);b,sg,rf,bx,br,arms,labels,adx,touch,capv=layer(view,rv.ind,lb,sl,tp,ts);labels=np.asarray(labels)
     _,first,rev=np.unique(np.column_stack([adx,touch]),axis=0,return_index=True,return_inverse=True)
     adx=adx[first];touch=touch[first];outs={};archive=Cube(170,sl,tp) if w==7 and Path(f'/tmp/eth_cube_170_{sl:g}_{tp:g}.npz').is_file() else None
     for i,t in enumerate(ts):
      ds=np.arange(1.25,min(3,t)+.01,.25);out=np.empty((len(first),len(ds),5,30))
      args=[cl,m.m['h'],m.m['l'],m.m['o'],b,sg,rf,bx,br,arms[i],ds,adx,touch,capv,np.empty((0,6))]
      cpu.sweep_be(len(b),len(ds),len(first),len(cl),tp,*[x.ctypes.data for x in args],0,out.ctypes.data)
      # Reuse saved single-leg outcomes for middle and verify against new DD/calendar pass.
      if archive:
       other=archive.ts[t][archive.rev]
       np.testing.assert_allclose(other[:,:,0,0],out[rev,:,0,0],atol=1e-6)
       out[:,:,0,:17]=other[first,:,0,:17]
      outs[t]=out
     for g,(gw,_,cap) in GROUPS.items():
      if w!=gw:continue
      for tf in [5,15,60]:
       ids=np.flatnonzero(labels[:,0]==tf);hs=labels[ids,1]
       vals=np.full((9,len(ts),8,len(hs)),np.nan);pack={};bas={}
       for i,(t,out) in enumerate(outs.items()):
        for j in range(out.shape[1]):
         key=f'{t:g}/{1.25+j*.25:g}';xx=vector(out[rev[ids],j,cap]);base=vector(out[rev[:1],j,cap])[0];bas[key]=base.round(5).tolist()
         rnd=xx.round(5);take=np.r_[True,np.any(rnd[1:]!=rnd[:-1],axis=1)]
         pack[key]=np.column_stack([hs[take],rnd[take]]).tolist()
         vals[:,i,j]=np.stack((xx[:,0],xx[:,1],-xx[:,2],xx[:,0]-base[0],100*xx[:,4]/xx[:,3],xx[:,5],xx[:,10],xx[:,6],xx[:,7]))
       with gzip.open(P/'data'/f'{g}_{sl:g}_{tp:g}_{tf}.json.gz','wt',compresslevel=3) as f:json.dump(dict(fields=FIELDS,curves=pack,td=bas),f,separators=(',',':'))
       a=vals.reshape(9,-1);good=np.isfinite(a[0]);a=a[:,good];control=refs[g]['family'];frontperf=refs[g]['front'];counts.append(dict(group=g,tf=tf,sl=sl,tp=tp,n=int(good.sum()),aboveFamily=int(((a[0]>control['net']+.005)&(a[1]>control['wr']+1e-7)&(-a[2]<control['dd']-1e-7)).sum()),aboveFront=int(((a[0]>frontperf['net']+.005)&(a[1]>frontperf['wr']+1e-7)&(-a[2]<frontperf['dd']-1e-7)).sum()),maxNet=a[0].max()))
       for lo,hi in [(0,10),(10,20),(20,30),(30,40),(40,50),(50,101)]:
        mask=(a[4]>=lo)&(a[4]<hi)
        if mask.any():
         v=a[:,mask];be=v[5]>0
         freqs.append(dict(group=g,tf=tf,sl=sl,tp=tp,lo=lo,hi=hi,n=int(mask.sum()),activation=np.median(v[4]),gain=np.median(v[3]),positive=100*(v[3]>.005).mean(),saveShare=np.median(100*v[7,be]/v[5,be]) if be.any() else None))
       size=11 if tf==60 else 21
       low=np.stack([rollmin(np.nan_to_num(z[:,:,:1200],nan=-np.inf),size) for z in vals])
       valid=(low[3]>.005)&(low[5]>=3)
       for typ,mask in [('td',valid),('frequent',valid&(low[4]>=20)),('family',valid&(low[0]>control['net']+.005)&(low[1]>control['wr']+1e-7)&(-low[2]<control['dd']-1e-7)),('front',valid&(low[0]>frontperf['net']+.005)&(low[1]>frontperf['wr']+1e-7)&(-low[2]<frontperf['dd']-1e-7))]:
        if not mask.any():continue
        i,j,k=np.unravel_index(np.argmax(np.where(mask,low[6],-np.inf)),mask.shape);box=vals[:,i:i+2,j:j+2,k:k+size].reshape(9,-1)
        blocks.append(dict(group=g,tf=tf,sl=sl,tp=tp,kind=typ,h0=hs[k],h1=hs[k+size-1],t0=ts[i],t1=ts[i+1],d0=1.25+j*.25,d1=1.5+j*.25,net=np.median(box[0]),gain=np.median(box[3]),wr=np.median(box[1]),dd=-np.median(box[2]),active=np.median(box[4]),saved=np.median(box[7]),hurt=np.median(box[8]),floorGap=low[6,i,j,k],floorGain=low[3,i,j,k]))
    print(w,lb,sl,flush=True)
 write('overview.json',dict(refs=refs,counts=counts,blocks=blocks,freq=freqs))
if __name__=='__main__':run()
