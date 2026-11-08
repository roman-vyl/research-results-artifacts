from compute import *
from functools import lru_cache
import warnings
warnings.filterwarnings('ignore',category=RuntimeWarning)
@lru_cache(maxsize=40)
def get(w,lb,sl,tp,key):
 with np.load(P/'data'/f'{w}_{lb}_{sl:g}_{tp:g}.npz') as f:
  return f['labels'],f['inverse'],f[key]
def row(c,t=None,d=None,h=None,w=None,lb=None):
 t=c['t'] if t is None else t;d=c['d'] if d is None else d;h=c['h'] if h is None else h
 key=f't{round(t*4)}'if c['mode'] in ('td','protected_td') else c['mode']
 try:lab,rev,a=get(int(c['w']if w is None else w),int(c['lb']if lb is None else lb),c['sl'],c['tp'],key)
 except (KeyError,FileNotFoundError):return None
 tf=0 if c['mode']=='td' else c['tf']
 ii=np.flatnonzero((lab[:,0]==tf)&(lab[:,1]==h))
 j=0 if c['mode']=='be_only' else round((d-1)*4)
 if not len(ii) or j<0 or j>=a.shape[1]:return None
 return a[rev[ii[0]],j,int(c['cap'])].astype('float64')
FEATURES=['solo','wins','n','dd','month_sd','month_positive','month_worst','year_sd','year_worst','net_long','net_short']
def stats(arr,prefix):
 x=np.array(arr);out={}
 for field in FEATURES:
  val=100*x[:,2]/x[:,3]if field=='wins'else x[:,FIELDS.index(field)]
  for kind,f in [('min',np.nanmin),('med',np.nanmedian),('max',np.nanmax)]:out[f'{prefix}_{field}_{kind}']=f(val)
 out[prefix+'_count']=len(x)
 return out
def main():
 pool=pd.read_csv(P/'pool.csv');out=[]
 for _,r in pool.iterrows():
  if r['mode']!='td' and (r['protected']if r['mode']!='runner'else r['runner'])<1:continue
  c=r.to_dict();geo=[]
  for w,lb in AREAS[c['family']]:
   if abs(w-c['w'])<=1 and abs(lb-c['lb'])<=10:
    v=row(c,w=w,lb=lb)
    if v is not None:geo.append(v)
  local=[]
  ts=[c['t']+x for x in (-.25,0,.25)] if c['mode'] in ('td','protected_td') else [0]
  ds=[c['d']+x for x in (-.25,0,.25)] if c['mode']!='be_only'else [0]
  hs=[c['h']+x for x in (-.25,0,.25)] if c['mode']!='td' else [0]
  for t in ts:
   for d in ds:
    for h in hs:
     if d<1 and c['mode']!='be_only':continue
     if t and d>t:continue
     v=row(c,t=t,d=d,h=h)
     if v is not None:local.append(v)
  c.update(stats(geo,'geo'));c.update(stats(local,'exit'))
  out.append(c)
 df=pd.DataFrame(out);df.to_csv(P/'neighborhoods.csv',index=False,float_format='%.7g')
 refs=json.loads((P/'references.json').read_text());selected=[]
 for (family,mode),g in df.groupby(['family','mode']):
  ref=refs[family]
  valid=(g.geo_year_worst_min>0)&(g.geo_dd_med<=ref['dd'])&(g.geo_month_sd_med<=ref['month_sd'])&(g.geo_year_worst_med>=ref['year_worst'])&(g.exit_year_worst_min>0)
  for distance,dist in [('tight',g.d<=1.5),('wide',g.d>=2)]:
   for style,mask in [('income',g.solo>=ref['net']*.98),('balanced',g.solo>=ref['net']*.9),('smooth',g.solo>=ref['net']*.9)]:
    x=g[valid&dist&mask]
    if x.empty:continue
    ix=x.geo_month_sd_med.idxmin()if style=='smooth'else x.geo_solo_med.idxmax()
    s=g.loc[ix].to_dict();s.update(style=style,distance=distance);selected.append(s)
 for (family,mode),g in df.groupby(['family','mode']):
  ref=refs[family]
  valid=(g.year_sd<=ref['year_sd'])&(g.month_sd<=ref['month_sd'])&(g.dd<=ref['dd'])&(g.geo_year_sd_med<=ref['year_sd'])&(g.geo_month_sd_med<=ref['month_sd'])&(g.geo_dd_med<=ref['dd'])&(g.geo_year_worst_min>0)&(g.exit_year_worst_min>0)
  for distance,dist in [('tight',g.d<=1.5),('wide',g.d>=2)]:
   x=g[valid&dist]
   if len(x):
    ix=x.geo_solo_med.idxmax();s=g.loc[ix].to_dict();s.update(style='calendar',distance=distance);selected.append(s)
 pd.DataFrame(selected).to_csv(P/'selected.csv',index=False,float_format='%.7g')
 print('audited',len(df),'selected',len(selected),flush=True)
 print(pd.DataFrame(selected)[['family','mode','distance','style','w','lb','sl','tp','cap','t','d','tf','h','solo','wr','dd','month_sd','year_worst','geo_solo_med','geo_year_worst_min']].to_string(index=False),flush=True)
if __name__=='__main__':main()
