from verify import *
from neighbors import row
def check():
 f=pd.read_csv(P/'selected.csv').drop_duplicates(['family','mode','w','lb','sl','tp','t','d','cap','tf','h'])
 records=[]
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('sol',tmp);ind=old.indicators('sol',m.m);mon=m.z['time'].astype('datetime64[ms]').astype('datetime64[M]');sim=m.sims[len(mon)]
  sim.z['dayends']=np.r_[np.flatnonzero(mon[1:]!=mon[:-1]),len(mon)-1].astype('int64')
  for _,r in f.iterrows():
   c=r.to_dict();args=[int(c[k])for k in ['w','lb']]+[c['sl'],c['tp'],int(c['cap']),c['t'],c['d']or 1,int(c['tf']),c['h'],('protected'if c['mode']=='protected_td'else c['mode'])]
   a,meta=audit(m,ind,*args)
   res=sim.run(0,ta=a,aa=1,curve=True)
   curve=np.array(res.pop('curve'));mr=100*(curve/np.r_[1.,curve[:-1]]-1)[1:-1]
   stored=row(c);actual=[res['net'],res['wr'],res['dd'],mr.std(),mr.min(),*[res['years'][str(y)]for y in range(2021,2027)]]
   target=[stored[0],100*stored[2]/stored[3],-stored[17],stored[19],stored[21],*stored[26:32]]
   np.testing.assert_allclose(actual,target,atol=.025,rtol=3e-6,err_msg=str(args))
   records.append(dict(c,net_full=res['net'],wr_full=res['wr'],dd_full=-res['dd'],checked=True))
 pd.DataFrame(records).to_csv(P/'verified_finalists.csv',index=False)
 print('All',len(records),'distinct selected configurations independently matched.',flush=True)
if __name__=='__main__':check()
