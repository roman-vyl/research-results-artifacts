from read_cube import *
from verify import audit, Review, star
SAMPLES=[
 ('reference5',4.75,5,0,5,10,2.5,1.75),
 ('later5',4.75,5,0,5,10,3.,1.75),
 ('plateau5',4.5,4.5,0,5,9.75,2.75,1.5),
 ('touch4',4.5,3.5,4,5,9.75,2.75,1.5),
 ('wider5',4.5,3.5,0,5,9.75,2.75,2.),
 ('early1h',4.75,4.5,0,60,.9,3,1.75),
 ('late1h',4.5,5,0,60,1.5,4.25,1.75),
 ('ref1h',5,5,0,60,1.5,3.75,1.75),
 ('ref1h_later',5,5,0,60,1.5,4.,1.75),
 ('ref15',4.75,5,0,15,21,4,1.5)]
def check():
 rows=[];random=np.random.default_rng(187)
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);rv=Review(m);samples=list(SAMPLES)
  for sl in (4,4.25,4.5,4.75,5):
   for tp in (3.5,4,4.5,5):
    t=random.choice(np.arange(1.5,tp-.45,.25));d=random.choice(np.arange(1.25,min(t,3)+.01,.25))
    samples.append(('check',sl,tp,random.integers(5),int(random.choice([5,15,60])),float(random.choice(THRESHOLDS[:600])),float(t),float(d)))
  for label,sl,tp,cap,tf,h,t,d in samples:
   c=Cube(170,sl,tp)
   cut=c.series(t,d,cap,tf).query('h == @h').iloc[0]
   for lb in [170] if label=='check' else [160,170,180]:
    a,meta,r=audit(m,rv,7,lb,sl,tp,cap,t,d,tf,h)
    pure,_,base=audit(m,rv,7,lb,sl,tp,cap,t,d,0,0)
    if lb==170:
     assert abs(cut.pair-r['net'])<1e-5 and abs(cut.dd+r['dd'])<1e-7 and abs(cut.gain-(r['net']-base['net']))<1e-5
     assert sum(e[2]>=0 for e in meta)==cut.protected and sum(e[-1]=='BE' for e in meta)==cut.be
     stress=a.copy()
     for i,(_,x,_,_,_,reason) in enumerate(meta):
      if reason=='BE' and a[i,2]*(m.m['o'][x]-a[i,3])<0:stress[i,4]=m.m['o'][x]
     alt=rv.sim.run(0,ta=rv.ledger(star(A)),tb=stress,aa=.5,ab=.5)
     assert abs(alt['net']-cut.gap_pair)<1e-5
    if label=='check':continue
    rows.append(dict(label=label,sl=sl,tp=tp,t=t,d=d,lb=lb,cap=cap,tf=tf,h=h,pair=r['net'],wr=r['wr'],dd=-r['dd'],gain=r['net']-base['net'],base=base['net'],month_sd=r['month_sd'],base_sd=base['month_sd'],**{f'y{k}':v for k,v in r['years'].items()},**{f'dy{k}':v-base['years'][k] for k,v in r['years'].items()}))
 pd.DataFrame(rows).to_csv(P/'verified.csv',index=False)
 print('30 controls matched',flush=True)
if __name__=='__main__':check()
