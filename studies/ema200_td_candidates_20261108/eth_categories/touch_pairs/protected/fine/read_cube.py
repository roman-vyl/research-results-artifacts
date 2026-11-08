from run import *
class Cube:
 def __init__(self,lb,sl,tp):
  with np.load(f'/tmp/eth_cube_{lb}_{sl:g}_{tp:g}.npz') as f:
   self.labels=f['labels'];self.rev=f['inverse']
   self.ts={int(k[1:])/4:f[k] for k in f.files if k.startswith('t')}
 def series(self,t,d,cap,tf):
  m=self.labels[:,0]==tf;x=self.ts[t];j=int(round((d-1.25)*4));f=pd.DataFrame(x[self.rev[m],j,cap],columns=METRICS);f['h']=self.labels[m,1];base=x[self.rev[0],j,cap];f['gain']=f.pair-base[1];f['dd_diff']=f.dd-base[-2];f['wr']=100*(f.wins+36)/(f.n+92);f['baseline']=base[1];f['base_dd']=base[-2];f['base_wr']=100*(base[2]+36)/(base[3]+92)
  return f
