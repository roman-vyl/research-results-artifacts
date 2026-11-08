"""Paired plane medians on the earlier 5m threshold band."""
from pathlib import Path
import gzip,json
import numpy as np
P=Path(__file__).resolve().parent
def main():
 result={}
 for group in ('wide','wide4','narrow','middle'):
  planes=[]
  for file in sorted((P/'data').glob(group+'_*.json.gz')):
   if not file.name.endswith('_5.json.gz'):continue
   layer=json.load(gzip.open(file));names=['h',*layer['fields']];sets=[]
   for k,seq in layer['curves'].items():
    a=np.array(seq);ix=a[:,0].searchsorted(np.arange(186,202)/20,side='right')-1
    v=dict(zip(names,a[ix].T));sets.append(np.column_stack([v['net']-layer['td'][k][0],100*v['active']/v['n'],np.divide(100*v['saved'],v['be'],out=np.full(16,np.nan),where=v['be']>0),100*v['saved']/v['n'],100*v['hurt']/v['n']]))
   a=np.vstack(sets);planes.append(np.nanmedian(a,axis=0))
  a=np.array(planes);med=np.nanmedian(a,axis=0)
  result[group]=dict(zip(['gain','active','success','saved','hurt'],med));result[group]['positive']=int((a[:,0]>.005).sum());result[group]['planes']=len(a)
 (P/'band.json').write_text(json.dumps(result));print(result)
if __name__=='__main__':main()
