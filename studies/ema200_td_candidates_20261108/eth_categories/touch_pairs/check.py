"""Independent replay and neighbourhood checks for shortlisted ETH strategies."""
import hashlib,itertools
from grid_scan import *

KEY=['w','lb','cap','sl','tp','tf','t','d']
def packed(x):return tuple(x[k] for k in KEY)
def star(x):return dict(x,tf=0)
class Review:
 def __init__(self,market):
  self.m=market
  self.ind=old.indicators('eth',market.m)
  self.cache={}
  z=market.z;months=z['time'].astype('datetime64[ms]').astype('datetime64[M]')
  self.sim=market.sims[len(months)]
  self.sim.z['dayends']=np.r_[np.flatnonzero(months[1:]!=months[:-1]),len(months)-1].astype('int64')
 def ledger(self,p):
  key=packed(p)
  if key in self.cache:return self.cache[key]
  w,lb,cap,sl,tp,tf,t,d=key
  if tf<=1:
   ledger,opened=self.m.ledger(p);assert not opened
  else:
   m=self.m;z=m.z;ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
   adx,plus,minus=[self.ind[f'{tf:g}_{k}'] for k in ('adx','plus','minus')]
   cl,hi,lo,op=[m.m[k] for k in ('c','h','l','o')]
   ds=np.array([d],float);rr=np.zeros(1);xx=np.zeros(1,'int64');aux=xx.copy()
   data=[];busy=-1
   for i in z['ix'][w,lb]:
    b=z['bars'][i];s=z['side'][i];rf=sl*z['ar'][i]
    if b<=busy or m.block[i] or (cap and not 1<=z['touch'][i]<=cap):continue
    end=z['xb'][i,ai,qi] if z['ok'][i,ai,qi] else len(cl)
    window=slice(b+1,end);hits=np.flatnonzero((adx[window]-adx[b]>=t)&(s*(plus[window]-minus[window])>0))
    r=z['rr'][i,ai,qi]
    if len(hits):
     m.lib.exits(len(cl),b,b+1+hits[0],s,rf*cl[b],tp,*[v.ctypes.data for v in (hi,lo,op,cl,ds)],1,0,*[v.ctypes.data for v in (rr,xx,aux)])
     end=xx[0];r=rr[0]
    assert 0<=end<len(cl)
    data.append((b,end,s,cl[b],cl[b]*(1+s*r*rf),rf));busy=end
   ledger=np.array(data)
  self.cache[key]=ledger
  return ledger
 def full(self,a,b=None):
  x=self.ledger(a);y=self.ledger(b) if b else np.empty((0,6))
  r=self.sim.run(0,ta=x,tb=y,aa=.5 if b else 1,ab=.5 if b else 0,curve=True)
  e=np.array(r['curve']);mr=100*(e/np.r_[1.,e[:-1]]-1)
  sx={(int(v[0]),int(v[2])) for v in x};sy={(int(v[0]),int(v[2]))for v in y}
  return dict(net=r['net'],wr=r['wr'],dd=-r['dd'],n=int(r['orders']),common=len(sx&sy),union=len(sx|sy),unique_b=len(sy-sx),sd_month=mr.std(),worst_month=mr.min(),long=r['net_long'],short=r['net_short'],**r['years'])

def category(f):
 return np.select([(f.w>=8)&(f.lb<=90),(f.w<=5)&(f.lb>=180)],['wide','narrow'],'middle')

def shortlist(f,kind):
 z=f[(f.cat==kind)&(f.tf>0)&(f.act>=1)].copy()
 # Distinct configurations per family, activity and touch setting. Select on absolute
 # PnL or a close PnL with better WR, then verify with the other leg replaced as well.
 ref='pairB' if kind=='narrow' else 'pairA'
 z['freq']=(z.act/z.n>=.1);z['bucket']=pd.cut(z.wins/z.n,[0,.30,.35,.38,.40,.43,.50,1])
 z=z.sort_values(ref,ascending=False).drop_duplicates(['w','lb','cap','tf','freq','bucket'])
 keep=z.groupby(['tf','cap','freq','bucket'],observed=True).head(2)
 return keep[KEY].drop_duplicates().to_dict('records')

def combine(m,review,f,tmp):
 groups=[shortlist(f,k) for k in ('narrow','wide','middle')]
 groups[0].append(star(A));groups[2].append(star(B))
 sets=[]
 for group in groups:
  seen=set();selected=[]
  for p in group:
   ledger=review.ledger(p);sig=hashlib.sha256(ledger.tobytes()).digest()
   if sig not in seen:seen.add(sig);selected.append(p)
  sets.append(selected)
 configs=sum(sets,[]);ls=[review.ledger(p) for p in configs];v=np.vstack(ls);offs=np.r_[0,np.cumsum(list(map(len,ls)))].astype('int64')
 split=len(sets[0]);second=len(sets[1]);n=len(ls)
 lib=Path(tmp)/'cross.so';subprocess.run(['cc','-O3','-shared','-fPIC',str(O/'screen.c'),str(R/'research/w8_td_geometry/engine_level_exits.c'),'-o',str(lib)],check=True)
 func=ctypes.CDLL(str(lib)).cross_scan;func.argtypes=[ctypes.c_void_p]*3+[ctypes.c_int]*2+[ctypes.c_void_p];func.restype=None
 out=np.empty((split,n-split,2))
 func(m.m['c'].ctypes.data,v.ctypes.data,offs.ctypes.data,n,split,out.ctypes.data)
 wins=np.array([np.sum(l[:,2]*(l[:,4]-l[:,3])>.0004*(l[:,3]+l[:,4])) for l in ls])
 a,b=np.indices(out.shape[:2]);a=a.ravel();b=b.ravel()+split;cnt=np.array(list(map(len,ls)))
 pairs=pd.DataFrame(dict(i=a,j=b,role=np.where(b<split+second,'wide','middle'),net=out[:,:,0].ravel(),common=out[:,:,1].ravel(),wr=100*(wins[a]+wins[b])/(cnt[a]+cnt[b])))
 pairs['union']=cnt[a]+cnt[b]-pairs.common
 pairs.to_pickle('/tmp/touch_pairs_cross.pkl')
 pd.DataFrame(configs).to_json('/tmp/touch_pairs_cfg.json',orient='records')
 print('shortlists',list(map(len,sets)),'crosses',len(pairs),flush=True)
 for name,z in pairs.groupby('role'):
  for v in [z, z[(z.wr>=37.71)&(z.union>=218)],z[(z.wr>=37.71)&(z.union>=218)&(z.common<=79)]]:
   if v.empty:continue
   p=v.nlargest(1,'net').iloc[0];print(name,p.to_dict(),configs[p.i],configs[p.j],flush=True)
 return pairs,configs

if __name__=='__main__':
 f=pd.concat([pd.read_pickle(p) for p in Path('/tmp').glob('touchgrid_*pkl')],ignore_index=True);f['cat']=category(f)
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);rv=Review(m);combine(m,rv,f,tmp)
