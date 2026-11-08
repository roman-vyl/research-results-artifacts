from read_cube import *
import json,gzip
def build():
 names=['pair','td_pair','wr','dd','gap_pair','protected','be','saved','hurt','savedR','hurtR','above','runner','n','solo','samebar','union','common','td_dd','td_wr','lost_above']
 h=THRESHOLDS;f=P/'data';f.mkdir(exist_ok=True)
 avg={tf:np.zeros((len(h),6)) for tf in [5,15,60]};nconf=0
 for path in sorted(Path('/tmp').glob('eth_cube_170_*.npz')):
  sl,tp=map(float,path.stem.split('_')[-2:]);c=Cube(170,sl,tp)
  for cap in range(5):
   for tf in (5,15,60):
    curves={};ids=c.rev[c.labels[:,0]==tf]
    for t,arr in c.ts.items():
     for j in range(arr.shape[1]):
      d=1.25+j*.25;v=arr[ids,j,cap];b=arr[c.rev[0],j,cap]
      wr=100*(v[:,2]+36)/(v[:,3]+92);gain=v[:,1]-b[1]
      avg[tf]+=np.column_stack((np.ones(len(h)),gain,gain>.005,100*v[:,4]/v[:,3],100*v[:,6]/v[:,3],100*v[:,7]/v[:,3]))
      nconf+=len(h)
      items=np.column_stack((v[:,1],np.full(len(h),b[1]),wr,v[:,17],v[:,18],v[:,4:8],v[:,12:14],v[:,10],v[:,9],v[:,3],v[:,0],v[:,16],v[:,15],v[:,14],np.full(len(h),b[17]),np.full(len(h),100*(b[2]+36)/(b[3]+92)),v[:,11])).round(5)
      take=np.r_[True,np.any(items[1:]!=items[:-1],axis=1)]
      curves[f'{t:g}/{d:g}']=np.column_stack((h[take],items[take])).tolist()
    data={'fields':['h',*names],'curves':curves}
    with gzip.open(f/f'{sl:g}_{tp:g}_{cap}_{tf}.json.gz','wt',compresslevel=5) as o:json.dump(data,o,separators=(',',':'))
 result=[]
 for tf,arr in avg.items():
  z=arr[:,1:]/arr[:,:1];result.extend([[tf,v,int(cnt),*r] for v,cnt,r in zip(h,arr[:,0],z)])
 pd.DataFrame(result,columns=['tf','h','count','mean_gain','share_up','mean_protected_pct','mean_save_pct','mean_hurt_pct']).to_csv(P/'frequency.csv',index=False,float_format='%.5f')
 print('points',nconf)
if __name__=='__main__':build()
