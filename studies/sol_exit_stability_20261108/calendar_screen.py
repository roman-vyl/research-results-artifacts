"""Second view of the same saved cube, explicitly requiring lower annual dispersion."""
from compute import *
from collections import defaultdict
def run():
 refs=json.loads((P/'references.json').read_text());groups=defaultdict(list)
 for family,geos in AREAS.items():
  r=refs[family]
  for sl,tp in LAYERS:
   for w,lb in geos:
    with np.load(P/'data'/f'{w}_{lb}_{sl:g}_{tp:g}.npz') as f:
     lab=f['labels'];rev=f['inverse'];idx=np.flatnonzero(lab[:,0]>0)
     for key in [k for k in f.files if k.startswith('t')]+['runner','be_only']:
      a=f[key];t=int(key[1:])/4 if key.startswith('t')else 0
      for mode,ids in ([('td',np.array([0])),('protected_td',idx)]if key.startswith('t')else [(key,idx)]):
       x=a[rev[ids]].astype('float64')
       wr=100*x[:,:,:,2]/x[:,:,:,3]
       mask=(x[:,:,:,17]<=r['dd'])&(x[:,:,:,19]<=r['month_sd'])&(x[:,:,:,23]<=r['year_sd'])&(x[:,:,:,24]>=r['year_worst'])
       if mode!='td':mask &= x[:,:,:,9 if mode=='runner'else 4]>0
       ds=1+np.arange(x.shape[1])*.25
       for band,di in [('tight',np.flatnonzero(ds<=1.5)),('wide',np.flatnonzero(ds>=2))]:
        if not len(di):continue
        valid=mask[:,di];values=x[:,:,:,0][:,di]
        for style,ok,score in [('calendar_income',valid,values),('calendar_smooth',valid&(values>=r['net']*.9),-x[:,:,:,19][:,di])]:
         if not ok.any():continue
         i,j,cap=np.unravel_index(np.argmax(np.where(ok,score,-np.inf)),ok.shape);d=0 if mode=='be_only'else ds[di[j]]
         row=dict(family=family,mode=mode,w=w,lb=lb,sl=sl,tp=tp,t=t,d=d,cap=cap,tf=int(lab[ids[i],0]),h=lab[ids[i],1],criterion=style,wr=wr[i,di[j],cap],active=100*x[i,di[j],cap,9 if mode=='runner'else 4]/x[i,di[j],cap,3],gain=x[i,di[j],cap,0]-a[rev[0],di[j],cap,0],score=score[i,j,cap])
         row.update(dict(zip(FIELDS,x[i,di[j],cap])))
         groups[family,mode,band,style].append(row)
  print('Calendar screening',family,flush=True)
 out=[]
 for key,rows in groups.items():
  s=pd.DataFrame(rows).sort_values('score',ascending=False)
  out.append(s.head(24))
 old=pd.read_csv(P/'pool.csv');new=pd.concat([old,*out]).drop_duplicates(['family','mode','w','lb','sl','tp','t','d','cap','tf','h'])
 new.to_csv(P/'pool.csv',index=False,float_format='%.7g');print('Pool',len(new),flush=True)
if __name__=='__main__':run()
