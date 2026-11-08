from compute import *
from regions import rollmin
def check():
 f=pd.read_csv(P/'selected.csv').drop_duplicates(['family','mode','w','lb','sl','tp','cap','tf'])
 refs=json.loads((P/'references.json').read_text());rows=[]
 for _,r in f.iterrows():
  if r['mode']!='protected_td':continue
  with np.load(P/'data'/f'{int(r.w)}_{int(r.lb)}_{r.sl:g}_{r.tp:g}.npz') as file:
   ts=sorted(int(k[1:])/4 for k in file.files if k.startswith('t'));lab=file['labels'];rev=file['inverse']
   idx=np.flatnonzero((lab[:,0]==r.tf)&(lab[:,1]<=60));h=lab[idx,1]
   vals=np.full((8,len(ts),9,len(idx)),-np.inf)
   for i,t in enumerate(ts):
    x=file[f't{round(t*4)}'][rev[idx],:,int(r.cap)].transpose(1,0,2).astype(float)
    v=[x[:,:,0],100*x[:,:,2]/x[:,:,3],-x[:,:,17],-x[:,:,19],x[:,:,24],100*x[:,:,4]/x[:,:,3],x[:,:,5],x[:,:,18]]
    vals[:,i,:len(x)]=np.stack(v)
   # h spans 1 point, and two consecutive T and D values.
   low=np.stack([rollmin(x,5) for x in vals])
   ref=refs[r.family]
   mask=(low[0]>=ref['net']*.98)&(low[1]>=ref['wr'])&(low[2]>=-ref['dd'])&(low[3]>=-ref['month_sd'])&(low[4]>=ref['year_worst'])&(low[6]>=3)
   for name,m in [('relative_stars',mask),('frequency20',mask&(low[5]>=20))]:
    if not m.any():continue
    i,j,k=np.unravel_index(np.argmax(np.where(m,low[0],-np.inf)),m.shape);x=vals[:,i:i+2,j:j+2,k:k+5].reshape(8,-1)
    v=dict(family=r.family,w=r.w,lb=r.lb,sl=r.sl,tp=r.tp,cap=r.cap,tf=r.tf,kind=name,t0=ts[i],t1=ts[i+1],d0=1+j*.25,d1=1.25+j*.25,h0=h[k],h1=h[k+4],n=x.shape[1])
    for field,samples in zip(['net','wr','negdd','negsd','year_worst','active','be','gap'],x):v[field+'_min']=samples.min();v[field+'_med']=np.median(samples);v[field+'_max']=samples.max()
    rows.append(v)
 out=pd.DataFrame(rows);out.to_csv(P/'blocks.csv',index=False,float_format='%.6f');print(out.to_string(index=False))
if __name__=='__main__':check()
