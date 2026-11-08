from verify import *
with tempfile.TemporaryDirectory() as tmp:
 m=Market('eth',tmp);rv=Review(m);out=[]
 for label,pars in CASES.items():
  ledger,events,s=audit(m,rv,7,170,*pars)
  adj=ledger.copy();gaps=outside=0;gross=[]
  for i,(b,x,p,td,r,reason) in enumerate(events):
   if reason!='BE':continue
   side=ledger[i,2];entry=ledger[i,3];op=m.m['o'][x]
   if side*(op-entry)<0:
    gaps+=1;adj[i,4]=op
    gross.append(side*(op-entry)/(entry*ledger[i,5]))
   outside+=not (m.m['l'][x]<=entry<=m.m['h'][x])
  sim=rv.sim.run(0,ta=rv.ledger(star(A)),tb=adj,aa=.5,ab=.5,curve=True)
  out.append(dict(case=label,gaps=gaps,outside=outside,open_fill_pair=sim['net'],open_fill_dd=-sim['dd'],open_fill_wr=sim['wr']))
 pd.DataFrame(out).to_csv(OUT/'open_sensitivity.csv',index=False)
