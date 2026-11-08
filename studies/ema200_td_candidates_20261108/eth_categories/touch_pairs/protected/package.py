from pathlib import Path
import pandas as pd,numpy as np,json
P=Path(__file__).resolve().parent;out=P/'data';out.mkdir(exist_ok=True)
parts=[];ns=0;layers=[]
for fn in sorted(Path('/tmp').glob('protected_7_170_*pkl')):
 sl,tp=map(float,fn.stem.split('_')[-2:]);layer=f'{sl:g}_{tp:g}'
 f=pd.read_pickle(fn,compression='gzip');f['freq']=100*f.protected/f.n
 f['eventrate']=100*(f.protected+f.samebar)/f.n
 f['bes']=100*f.be/f.n;f['save_rate']=100*f.saved/f.n;f['harm_rate']=100*f.hurt/f.n
 f['profit']=(f.dnet>.005).astype(float)
 z=f[f.tf!=0];ns+=len(z)
 u=z.groupby(['tf','h']).agg(cells=('pair','size'),freq=('freq','sum'),eventrate=('eventrate','sum'),be=('bes','sum'),save=('save_rate','sum'),harm=('harm_rate','sum'),profits=('profit','sum'),delta=('dnet','sum')).reset_index()
 parts.append(u)
 layers.append(layer)
 f=f.drop(columns=['wins','neutral'])
 f.to_csv(out/(layer+'.csv.gz'),index=False,float_format='%.4f')
g=pd.concat(parts).groupby(['tf','h'],as_index=False).sum()
for col in ['freq','eventrate','be','save','harm','delta','profits']:g[col]/=g.cells
g.to_csv(P/'frequency.csv',index=False,float_format='%.5f')
(P/'layers.json').write_text(json.dumps(layers));print('combos',ns)
print(g[g.h.isin([1.5,5,10,20,33])].round(2).to_string(index=False))
