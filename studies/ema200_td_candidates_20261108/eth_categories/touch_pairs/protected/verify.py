from sweep import *
import json
from check import Review,star

def audit(m,rv,w,lb,sl,tp,cap,t,d,tf,h):
 z=m.z;c=m.m;ii=z['ix'][w,lb];ai=list(z['sls']).index(sl);qi=list(z['ratios']).index(tp)
 busy=-1;records=[];meta=[]
 for i in ii:
  b=z['bars'][i];s=z['side'][i]
  if b<=busy or m.block[i] or (cap and not 1<=z['touch'][i]<=cap):continue
  entry=c['c'][b];rf=z['ar'][i]*sl;risk=entry*rf
  protection=run=-1;peak=0;stop=-1;price=None;reason=None
  original=z['xb'][i,ai,qi];base_r=z['rr'][i,ai,qi]
  for j in range(b+1,len(c['c'])):
   adverse=s*((c['l'] if s>0 else c['h'])[j]-entry)/risk
   if adverse<=-1 or (run<0 and j==original and base_r<0):price=-1;reason='SL';break
   if adverse<=stop:price=stop;reason='BE' if run<0 else 'TRAIL';break
   if run<0 and j==original and base_r>0:price=tp;reason='TP';break
   peak=max(peak,s*((c['h'] if s>0 else c['l'])[j]-entry)/risk)
   if peak>=t and run<0:run=j
   if run>=0:stop=max(stop,peak-d)
   elif tf and protection<0:
    ax,plus,minus=[rv.ind[f'{tf}_{k}'] for k in ('adx','plus','minus')]
    if ax[j]-ax[b]>=h and (plus[j]-minus[j])*s>0:protection=j;stop=0
  assert price is not None
  busy=j;records.append([b,j,s,entry,entry*(1+s*price*rf),rf]);meta.append([b,j,protection,run,price,reason])
 a=np.array(records);summary=rv.sim.run(0,ta=rv.ledger(star(A)),tb=a,aa=.5,ab=.5,curve=True)
 curve=np.array(summary.pop('curve'));summary['month_sd']=np.std(100*(curve/np.r_[1.,curve[:-1]]-1))
 return a,meta,summary
CASES={
 'frequent':(4.75,5,0,2.5,1.75,5,10),
 'frequent_cap4':(4.75,5,4,2.5,1.75,5,10),
 'prior_strong':(4.75,5,0,3,1.25,5,33),
 'prior_frequent':(4.75,5,0,3,1.25,5,10),
 'distance_2':(4.5,5,0,2.75,2,5,9.5),
 '15m':(5,5,0,3.75,1.75,15,21),
 '1h':(5,5,0,3.75,1.75,60,1.5),
 'native_cap4_plane':(4.5,3.5,4,2,1.5,5,9.5)}
if __name__=='__main__':
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);rv=Review(m);rows=[];neighbors=[]
  for label,pars in CASES.items():
   sl,tp,cap,t,d,tf,h=pars
   a,meta,r=audit(m,rv,7,170,*pars);pure,_,r0=audit(m,rv,7,170,sl,tp,cap,t,d,0,0)
   td=m.ledger(dict(w=7,lb=170,sl=sl,tp=tp,cap=cap,t=t,d=d))[0];np.testing.assert_allclose(pure,td,atol=1e-8,rtol=1e-12)
   f=pd.read_pickle(f'/tmp/protected_7_170_{sl:g}_{tp:g}.pkl',compression='gzip')
   x=f[(f.cap==cap)&(f.t==t)&(f.d==d)&(f.h==h)&(f.tf==tf)].iloc[0]
   assert abs(r['net']-x.pair)<.01 and abs(r['wr']-x.wrpair)<1e-6
   assert len(a)==x.n and sum(y[2]>=0 for y in meta)==x.protected and sum(y[5]=='BE' for y in meta)==x.be
   row=dict(case=label,**x.to_dict(),be_dd=-r['dd'],td_dd=-r0['dd'],month_sd=r['month_sd'],td_month_sd=r0['month_sd'],**{f'y{y}':v for y,v in r['years'].items()},**{f'dy{y}':v-r0['years'][y] for y,v in r['years'].items()})
   rows.append(row)
   if label=='frequent':
    target=json.loads(Path('/tmp/prot_native_result.json').read_bytes())
    fills=sorted(json.loads((Path.home()/'BBB_data/research/runs'/target['run_id']/'trades.json').read_bytes()),key=lambda q:q['entry_bar_index'])
    assert len(fills)==len(a)
    for v,fll in zip(a,fills):
     assert v[0]==fll['entry_bar_index'] and v[1]==fll['exit_bar_index'] and v[2]==(1 if fll['side']=='long' else -1) and abs(v[4]-float(fll['exit_price']))<1e-7 and abs(v[3]-float(fll['entry_price']))<1e-7
    assert abs(x.solo-float(target['net_pnl']))<.01
    pd.DataFrame(meta,columns=['entry_bar','exit_bar','protected_bar','runner_bar','R','exit']).to_csv(OUT/'verified_trades.csv',index=False)
   for lb in (160,170,180):
    if label not in ('frequent','distance_2','prior_strong','15m','1h'):continue
    new=audit(m,rv,7,lb,*pars)[2];same=audit(m,rv,7,lb,sl,tp,cap,t,d,0,0)[2]
    neighbors.append(dict(case=label,lb=lb,pair=new['net'],gain=new['net']-same['net'],dd=-new['dd'],td_dd=-same['dd']))
  pd.DataFrame(rows).to_csv(OUT/'cases.csv',index=False);pd.DataFrame(neighbors).to_csv(OUT/'neighbors.csv',index=False)
