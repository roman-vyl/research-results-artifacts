"""Independent barwise checks plus a full count of the published RLE grid."""
from pathlib import Path
import json,gzip,tempfile,sys
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));from build import F,Market,Review,audit,GROUPS,FIELDS
from run import THRESHOLDS
def check():
 info=json.loads((P/'overview.json').read_text());total=0
 for f in (P/'data').glob('*.gz'):
  z=json.load(gzip.open(f));total+=len(THRESHOLDS)*len(z['curves']);assert z['fields']==FIELDS
  for key,seq in z['curves'].items():
   assert key in z['td'] and seq[0][0]==.05 and all(len(row)==len(FIELDS)+1 for row in seq)
 assert total==sum(r['n'] for r in info['counts'])
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);rv=Review(m);mo=m.z['time'].astype('datetime64[ms]').astype('datetime64[M]');sel=mo[rv.sim.z['dayends']];full=(sel>mo[0])&(sel<mo[-1]);assert full.sum()==66
  for g,(w,lb,cap) in GROUPS.items():
   for sl,tp,tf,h,t,d in [(4.75,3.5,5,9.65,2.5,1.25),(5,4,60,1.5,2.75,1.75),(4.25,5,15,11,3,2)]:
    a,_,_=audit(m,rv,w,lb,sl,tp,cap,t,d,tf,h)
    r=rv.sim.run(0,ta=a,aa=1,curve=True);curve=np.array(r['curve']);mr=(100*(curve/np.r_[1.,curve[:-1]]-1))[full];yr=list(r['years'].values())
    f=P/'data'/f'{g}_{sl:g}_{tp:g}_{tf}.json.gz';z=json.load(gzip.open(f));row=dict(zip(FIELDS,next(row[1:] for row in z['curves'][f'{t:g}/{d:g}'][::-1] if row[0]<=h)))
    metrics=['net','wr','dd','msd','mpos','mworst','ysd','yworst',*['y'+y for y in r['years']]]
    np.testing.assert_allclose([row[k] for k in metrics],[r['net'],r['wr'],-r['dd'],mr.std(),100*(mr>1e-8).mean(),mr.min(),np.std(yr[1:-1]),min(yr[1:-1]),*yr],rtol=0,atol=.00001)
 print('12 independent cell checks,',total,'published combinations.')
if __name__=='__main__':check()
