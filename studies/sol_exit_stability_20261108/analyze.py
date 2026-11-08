from compute import *
from collections import defaultdict
import warnings
warnings.filterwarnings("ignore",category=RuntimeWarning)
from functools import lru_cache
FREQ=[0,10,20,30,40,50,60,100]
def source_refs():
 x=json.loads(Path('/tmp/sol_final_two.json').read_text());r={}
 for family,key in [('wide','wide'),('narrow','star')]:
  q=x[key];a=q['full'];ys=np.array([a['years'][str(y)]for y in (2022,2023,2024,2025)])
  r[family]=dict(net=a['net'],wr=a['wr'],dd=-a['dd'],month_sd=q['monthly']['sd'],year_worst=ys.min(),year_sd=ys.std(),params=q['params'],months=q['monthly'],years=a['years'])
 return r
def wmedian(x):return np.nanmedian(x,axis=0)
def flatten():
 refs=source_refs();pool=defaultdict(list);dist=[];counts=defaultdict(lambda:np.zeros(5,dtype='int64'))
 layer_summaries=[]
 curve_rows=[]
 for family,geos in AREAS.items():
  ref=refs[family]
  for sl,tp in LAYERS:
   for w,lb in geos:
    file=P/'data'/f'{w}_{lb}_{sl:g}_{tp:g}.npz'
    with np.load(file) as f:
     labels=f['labels'];rev=f['inverse'];keys=[k for k in f.files if k.startswith('t')]+['runner','be_only']; li=labels[:,0]>0
     for key in keys:
      native=f[key]
      istd=key.startswith('t'); mode='protected_td' if istd else key
      t=int(key[1:])/4 if istd else 0.;ds=np.arange(1.,1+native.shape[1]*.25,.25)
      x=native[rev]
      control=native[rev[0]]
      for j,d in enumerate(ds):
       for cap in range(5):
        v=x[:,j,cap].astype('float64')
        # TD is represented once, at the no-ADX control.
        for tf in ([0,5,15,60] if istd else [5,15,60]):
         ids=np.array([0]) if tf==0 else np.flatnonzero(labels[:,0]==tf)
         z=v[ids];wr=100*z[:,2]/z[:,3];act=100*z[:,4]/z[:,3] if mode!='runner' else 100*z[:,9]/z[:,3]
         name='td' if tf==0 else mode
         gain=z[:,0]-control[j,cap,0]
         good=(z[:,0]>=ref['net']*.98)&(wr>=ref['wr'])&(z[:,17]<=ref['dd'])&(z[:,19]<=ref['month_sd'])&(z[:,24]>=ref['year_worst'])
         stable=(z[:,17]<=ref['dd'])&(z[:,19]<=ref['month_sd'])&(z[:,24]>=ref['year_worst'])
         near=(z[:,0]>=ref['net']*.9)&stable
         counts[family,name]+=np.array([len(z),sum(good),sum(near),sum(stable),sum(z[:,0]>=ref['net'])])
         # A spectrum of useful comparisons, retaining full loss boundaries.
         choices=[('income',stable),('near',near),('smooth',z[:,0]>=ref['net']*.9),('all',np.ones(len(z),bool))]
         for criterion,ok in choices:
          score=-z[:,19] if criterion=='smooth' else z[:,0]
          order=np.argsort(np.where(ok,score,-np.inf))[::-1]
          # retain the most profitable or smoothest outcomes, including threshold plateaus
          taken=[]
          for k in order:
           if not ok[k]:break
           sig=tuple(z[k,[0,2,3,17,19,24,4,9]])
           if sig in taken:continue
           taken.append(sig)
           r=dict(family=family,mode=name,w=w,lb=lb,sl=sl,tp=tp,t=t,d=(0 if mode=='be_only' else d),cap=cap,tf=tf,h=labels[ids[k],1],criterion=criterion,wr=wr[k],active=act[k],gain=gain[k])
           r.update(dict(zip(FIELDS,z[k])))
           r['score']=float(score[k]);pk=(family,name,'tight' if d<=1.5 else 'wide');pool[pk].append(r)
           if len(pool[pk])>5000:
            pruned=[]
            for criterion_name in ['income','near','smooth','all']:
             bunch=[a for a in pool[pk] if a['criterion']==criterion_name]
             bunch.sort(key=lambda a:a['score'],reverse=True);seen=set()
             for candidate in bunch:
              token=tuple(candidate[k]for k in ['w','lb','sl','tp','cap'])
              if token not in seen:seen.add(token);pruned.append(candidate)
              if len(seen)>=50:break
            pool[pk]=pruned
           if len(taken)>=2:break
         # Equal weight geometry/configuration aggregates by TF and activation.
         for low,high in zip(FREQ[:-1],FREQ[1:]):
          mask=(act>low)&(act<=high)
          if not mask.any():continue
          zz=z[mask];acts=act[mask]
          be=zz[:,5];armed=zz[:,4];saved=zz[:,6];hurt=zz[:,7]
          def pct(a,b):return np.divide(100*a,b,out=np.full(len(b),np.nan),where=b>0)
          with np.errstate(all='ignore'):
           means=np.nanmean(np.column_stack([zz[:,0],wr[mask],zz[:,17],zz[:,19],zz[:,24],acts,pct(be,armed),pct(saved,be),pct(saved,armed),pct(hurt,armed),gain[mask]]),axis=0)
          curve_rows.append(dict(family=family,mode=name,tf=tf,distance='tight' if d<=1.5 else 'wide',w=w,lb=lb,sl=sl,tp=tp,freq=f'{low}–{high}',count=mask.sum(),**dict(zip(['net','wr','dd','month_sd','year_worst','active','hit_active','saved_hit','saved_active','hurt_active','gain'],means))))
    df=pd.DataFrame(curve_rows)
    if len(df):
     layer_summaries.append(df.groupby(['family','mode','tf','distance','freq','w','lb','sl','tp']).median(numeric_only=True).reset_index())
    curve_rows=[]
    print('screen',family,sl,tp,w,lb,flush=True)
 # Keep a broad candidate pool and a bounded shortlist for neighbour audit.
 chosen=[]
 for key,items in pool.items():
  f=pd.DataFrame(items).sort_values('score',ascending=False)
  groups=[]
  for crit,df in f.groupby('criterion'):
   # distinct geometry/SLTP/caps, with several alternatives per mode and distance
   groups.append(df.drop_duplicates(['w','lb','sl','tp','cap']).head(18))
  chosen.append(pd.concat(groups))
 f=pd.concat(chosen).drop_duplicates(['family','mode','w','lb','sl','tp','t','d','cap','tf','h'])
 f.to_csv(P/'pool.csv',index=False,float_format='%.7g')
 c=pd.DataFrame([dict(family=k[0],mode=k[1],n=v[0],dominates=v[1],near=v[2],stable=v[3],beats_net=v[4])for k,v in counts.items()])
 c.to_csv(P/'coverage.csv',index=False)
 # First average within each cell/SLTP; then equal-weight medians across layers.
 d=pd.concat(layer_summaries);cols=['family','mode','tf','distance','freq']
 a=d.groupby([*cols,'w','lb','sl','tp'],observed=True).mean(numeric_only=True)
 a.groupby(cols,observed=True).median(numeric_only=True).reset_index().to_csv(P/'frequency.csv',index=False,float_format='%.6f')
 (P/'references.json').write_text(json.dumps(refs,default=lambda v:v.item(),ensure_ascii=False))
 print('pool',len(f),'coverage',c.to_dict('records'),flush=True)
if __name__=='__main__':flatten()
