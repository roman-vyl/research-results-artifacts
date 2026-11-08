from finalists import *
def keys(x):return {(r[0],r[2]) for r in x}
with tempfile.TemporaryDirectory() as tmp:
 m=Market('eth',tmp);z=m.z;rv=Review(m);base=keys(rv.ledger(star(A)))|keys(rv.ledger(star(B)));rows=[];first_neighbors=[]
 for label,(a,b) in cases.items():
  keys_new=keys(rv.ledger(a))|keys(rv.ledger(b));row=dict(label=label,new_entries=len(keys_new-base),removed_entries=len(base-keys_new))
  for name,p,other in [('a',a,b),('b',b,a)]:
   if not p['tf']:continue
   s0=rv.full(plain(p));row[name+'_solo_no']=s0['net']
   rr=rv.full(plain(p),other);row[name+'_pair_if_off']=rr['net']
   if p['tf']>1:
    ai=list(z['sls']).index(p['sl']);qi=list(z['ratios']).index(p['tp'])
    mapping={(z['bars'][i],z['side'][i]):i for i in z['ix'][p['w'],p['lb']]}
    act={}
    for begin,end,side,entry,exit_px,rf in rv.ledger(p):
     i=mapping[begin,side];b0=int(begin);e0=z['xb'][i,ai,qi];window=slice(b0+1,e0);tf=p['tf'];adx=rv.ind[f'{tf}_adx']
     hit=np.flatnonzero((adx[window]-adx[b0]>=p['t'])&(side*(rv.ind[f'{tf}_plus'][window]-rv.ind[f'{tf}_minus'][window])>0))
     if len(hit):
      year=str(z['time'][b0+1+hit[0]].astype('datetime64[ms]'))[:4];act[year]=act.get(year,0)+1
    row[name+'_activations_by_year']=act
  if label=='two ADX':
   for k in (34,36,38):
    for d in (1.5,1.75,2):
     r=rv.full(dict(a,t=k,d=d),b);first_neighbors.append(dict(label=label,t=k,d=d,**r))
  rows.append(row)
 (O/'attribution.json').write_text(json.dumps(rows,indent=1))
 pd.DataFrame(first_neighbors).to_csv(O/'first_leg_neighbors.csv',index=False)
