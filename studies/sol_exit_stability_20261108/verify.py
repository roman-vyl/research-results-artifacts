"""Independent candle loop used to verify compressed SOL results."""
from compute import *
def audit(m,ind,w,lb,sl,tp,cap,t,d,tf,h,mode):
 z,c=m.z,m.m;ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
 records=[];meta=[];busy=-1
 for i in z['ix'][w,lb]:
  b=z['bars'][i];s=z['side'][i]
  if b<=busy or m.block[i] or(cap and not 1<=z['touch'][i]<=cap):continue
  ep=c['c'][b];rf=sl*z['ar'][i];risk=ep*rf;stop=-1.;peak=0.;arm=prot=-1;rr=None
  orig=z['xb'][i,ai,qi]
  for x in range(b+1,len(c['c'])):
   adverse=s*((c['l']if s>0 else c['h'])[x]-ep)/risk
   if adverse<=-1 or (arm<0 and x==orig and z['rr'][i,ai,qi]<0):rr=-1.;break
   if adverse<=stop:rr=stop;break
   if arm<0 and x==orig and z['rr'][i,ai,qi]>0:rr=tp;break
   peak=max(peak,s*((c['h'] if s>0 else c['l'])[x]-ep)/risk)
   impulse=False
   if tf:
    ax,di,dm=[ind[f'{tf}_{v}'] for v in ['adx','plus','minus']]
    impulse=np.isfinite(ax[x]) and ax[x]-ax[b]>=h and s*(di[x]-dm[x])>0
   if mode=='runner':
    if arm<0 and impulse:arm=x
   elif mode!='be_only' and arm<0 and peak>=t:arm=x
   if arm>=0:
    if peak>=d:stop=max(stop,peak-d)
   elif mode!='runner' and impulse and prot<0:prot=x;stop=0.
  assert rr is not None
  busy=x;records.append((b,x,s,ep,ep*(1+s*rr*rf),rf));meta.append((prot,arm,rr))
 return np.array(records),np.array(meta)
def check():
 count=0
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('sol',tmp);ind=old.indicators('sol',m.m)
  mon=m.z['time'].astype('datetime64[ms]').astype('datetime64[M]')
  sim=m.sims[len(mon)];sim.z['dayends']=np.r_[np.flatnonzero(mon[1:]!=mon[:-1]),len(mon)-1].astype('int64')
  for w,lb,sl,tp in [(8,60,5.5,4.5),(9,70,6,4.5),(3,240,6,5)]:
   file=P/'data'/f'{w}_{lb}_{sl:g}_{tp:g}.npz'
   if not file.exists():continue
   with np.load(file) as f:arr={k:f[k] for k in f.files}
   for mode,t,d,tf,h in [('td',3,1.25,0,0),('protected',3,1.25,5,10),('runner',0,2.5,15,10),('be_only',0,1,60,2)]:
    for cap in [0,2,4]:
     a,meta=audit(m,ind,w,lb,sl,tp,cap,t,d,tf,h,mode)
     r=sim.run(0,ta=a,aa=1,curve=True);curve=np.array(r['curve']);mr=100*(curve/np.r_[1.,curve[:-1]]-1)[1:-1]
     li=0 if not tf else np.where((arr['labels'][:,0]==tf)&(arr['labels'][:,1]==h))[0][0]
     k=arr['inverse'][li]
     stored=arr['be_only'][k,0,cap] if mode=='be_only' else arr['runner'][k,round((d-1)*4),cap] if mode=='runner' else arr[f't{round(t*4)}'][k,round((d-1)*4),cap]
     actual=[r['net'],r['wr'],r['dd'],mr.std(),mr.min(),*[r['years'][str(y)]for y in range(2021,2027)]]
     expected=[stored[0],100*stored[2]/stored[3],-stored[17],stored[19],stored[21],*stored[26:32]]
     np.testing.assert_allclose(actual,expected,atol=.025,rtol=2e-6,err_msg=str((w,lb,sl,tp,mode,cap)))
     count+=1
 print('Independent candle checks matched:',count,flush=True)
if __name__=='__main__':check()
