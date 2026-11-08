from sweep import *
from verify import CASES

if __name__=='__main__':
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);ind=old.indicators('eth',m.m);z=m.z
  cells=list(z['ix']);ids=np.unique(np.concatenate([z['ix'][key] for key in cells]));ids=ids[~m.block[ids]]
  z['ix'][0,0]=ids
  lib=Path(tmp)/'transfer.so';subprocess.run(['cc','-O3','-shared','-fPIC',str(OUT/'protect.c'),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
  fn=ctypes.CDLL(str(lib)).sweep_be;fn.argtypes=[ctypes.c_int]*4+[ctypes.c_double]+[ctypes.c_void_p]*15+[ctypes.c_int,ctypes.c_void_p];fn.restype=None
  aa=m.ledger(A)[0];c=m.m;cache={};results=[]
  for name in ('frequent','prior_strong','distance_2','15m','1h','native_cap4_plane'):
   sl,tp,cap,t,d,tf,h=CASES[name]
   if (sl,tp) not in cache:cache[sl,tp]=prepare(m,0,0,sl,tp,ind)
   bars,s,rf,xx,rr,ts,ta,labels,adx,touch,caps=cache[sl,tp];ri=[0,labels.index((tf,h))]
   for w,lb in cells:
    ci=z['ix'][w,lb];ix=np.searchsorted(ids,ci[~m.block[ci]])
    args=[c['c'],c['h'],c['l'],c['o'],bars[ix],s[ix],rf[ix],xx[ix],rr[ix],ta[np.where(ts==t)[0][0],ix],np.array([d],float),np.ascontiguousarray(adx[ri][:,ix]),np.ascontiguousarray(touch[ri][:,ix]),caps[ix],aa]
    out=np.empty((2,1,5,len(COLS)));fn(len(ix),1,2,len(c['c']),tp,*[v.ctypes.data for v in args],len(aa),out.ctypes.data)
    for k in range(5):
     base,hybrid=out[:,0,k]
     results.append(dict(case=name,w=w,lb=lb,cap=k,pair=hybrid[1],delta=hybrid[1]-base[1],n=hybrid[3],protected=hybrid[4],be=hybrid[5],saved=hybrid[6],hurt=hybrid[7]))
  pd.DataFrame(results).to_csv(OUT/'transfer.csv.gz',index=False)
