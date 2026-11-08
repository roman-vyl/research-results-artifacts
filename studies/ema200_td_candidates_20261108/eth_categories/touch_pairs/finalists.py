from check import *
import json

def spec(w,lb,cap,sl,tp,tf,t,d):return dict(zip(KEY,[w,lb,cap,sl,tp,tf,t,d]))
def plain(p):return dict(p,tf=0,t=0,d=0)
cases={
 'stars':(star(A),star(B)),
 'TD frequent':(star(A),spec(7,170,0,4.5,5,1,3.25,1.5)),
 'TD more profit':(star(A),spec(7,170,0,4.75,5,1,3,1.25)),
 'TD broad distance':(star(A),spec(7,170,0,4.75,4.5,1,2.75,1.75)),
 'ADX all':(star(A),spec(7,170,0,4.5,3.5,15,23,2.75)),
 'ADX four':(star(A),spec(7,170,4,4.5,3.5,15,23,2.75)),
 'two ADX':(spec(5,290,2,4.75,4.5,5,36,1.75),spec(7,170,0,4.5,3.5,15,23,2.75)),
 'strict equal net':(spec(5,280,0,5,4,5,46.5,1.5),spec(9,30,0,4.75,4.5,5,32,3)),
 'strict geometry':(spec(5,280,4,5,4,5,46.5,1.5),spec(11,20,0,5,5,60,6,3)),
}
def evaluate():
 f=pd.concat([pd.read_pickle(p) for p in Path('/tmp').glob('touchgrid_*pkl')],ignore_index=True)
 f=f.drop_duplicates(KEY).set_index(KEY)
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);review=Review(m);result={};neighbor_rows=[];touch_rows=[]
  for label,(a,b) in cases.items():
   print(label,flush=True)
   pair=review.full(a,b);no=review.full(plain(a),plain(b))
   sa,sb=review.full(a),review.full(b)
   leg=[]
   for p in (a,b):
    row=f.loc[packed(p)]
    leg.append(dict(net=row.net,wr=100*row.wins/row.n,n=row.n,act=row.act,above=row.above,fast=row.fast))
   if a==star(A):
    s=f.loc[packed(b)];assert abs(pair['net']-s.pairA)<.01 and pair['common']==s.commonA
   result[label]=dict(a=a,b=b,pair=pair,base=no,legs=leg,sa=sa,sb=sb)
   if label=='stars':continue
   # Change each setting on the second leg, retaining the first configuration.
   ts=[b['t']+i*(.25 if b['tf']==1 else 1) for i in (-1,0,1)]
   for t,d in itertools.product(ts,[b['d']-.25,b['d'],b['d']+.25]):
    if not 1<=d<=3 or (b['tf']==1 and d>t):continue
    x=dict(b,t=t,d=d);r=review.full(a,x);neighbor_rows.append(dict(label=label,axis='T,D',value1=t,value2=d,**r))
   for w,lb in itertools.product([b['w']-1,b['w'],b['w']+1],[b['lb']-10,b['lb'],b['lb']+10]):
    if not (3<=w<=14 and 20<=lb<=300):continue
    r=review.full(a,dict(b,w=w,lb=lb));neighbor_rows.append(dict(label=label,axis='w,lb',value1=w,value2=lb,**r))
   for cap in range(5):
    x=dict(b,cap=cap);r=review.full(a,x);no_cap=review.full(a,plain(x))
    touch_rows.append(dict(label=label,cap=cap,net_no_runner=no_cap['net'],**r))
  (O/'comparison.json').write_text(json.dumps(result,indent=1,default=lambda v:v.item()))
  pd.DataFrame(neighbor_rows).to_csv(O/'neighbors.csv',index=False)
  pd.DataFrame(touch_rows).to_csv(O/'touches.csv',index=False)

if __name__=='__main__':evaluate()
