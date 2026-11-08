"""Rank contiguous blocks of threshold × T × D by worst stressed Net Won."""
from read_cube import *
from numpy.lib.stride_tricks import sliding_window_view

def rollmin(x,width):
    z=np.minimum(x[:-1,:-1],x[1:,:-1])
    z=np.minimum(z,np.minimum(x[:-1,1:],x[1:,1:]))
    return sliding_window_view(z,width,axis=-1).min(-1)

def regions():
    out=[];total=0;results=[]
    for file in sorted(Path('/tmp').glob('eth_cube_170_*.npz')):
        sl,tp=map(float,file.stem.split('_')[-2:]);c=Cube(170,sl,tp);ts=sorted(c.ts)
        total+=sum((len(c.labels)-1)*x.shape[1]*5 for x in c.ts.values())
        for cap in range(5):
          for tf in [5,15,60]:
            idx=np.flatnonzero((c.labels[:,0]==tf)&(c.labels[:,1]<=60))
            width=11 if tf==60 else 21
            h=c.labels[idx,1];nr=len(h)
            features=['gap_pair','pair','gain','dd','wr','protected','be','saved','hurt','above','freq']
            vals=np.full((len(features),len(ts),8,nr),-np.inf)
            for ti,t in enumerate(ts):
                x=c.ts[t];v=x[c.rev[idx],:,cap].transpose(1,0,2);base=x[c.rev[0],:,cap]
                for fi,name in enumerate(features):
                    if name=='gain':vv=v[:,:,1]-base[:,1,None]
                    elif name=='wr':vv=100*(v[:,:,2]+36)/(v[:,:,3]+92)
                    elif name=='freq':vv=100*v[:,:,4]/v[:,:,3]
                    else:vv=v[:,:,METRICS.index(name)]
                    vals[fi,ti,:len(v)]= -vv if name=='dd' else vv
            worst=dict(zip(features,[rollmin(a,width) for a in vals]))
            eligible=(worst['gain']>0)&(worst['be']>=3)
            for kind,mask in [('all',eligible),('frequent',eligible&(worst['freq']>=15)),('balanced',eligible&(worst['wr']>=37.71)&(worst['dd']>=-9.24)),('wider',eligible&(worst['freq']>=15)&(np.arange(7)[None,:,None]>=2)),('balanced_frequent',eligible&(worst['freq']>=15)&(worst['wr']>=37.71)&(worst['dd']>=-9.24))]:
                if not np.any(mask):continue
                v=np.where(mask,worst['gap_pair'],-np.inf);i,j,k=np.unravel_index(v.argmax(),v.shape)
                out.append(dict(kind=kind,sl=sl,tp=tp,cap=cap,tf=tf,h0=h[k],h1=h[k+width-1],t0=ts[i],t1=ts[i+1],d0=1.25+.25*j,d1=1.5+.25*j,**{n:(-w[i,j,k] if n=='dd' else w[i,j,k]) for n,w in worst.items()}))
    f=pd.DataFrame(out).sort_values('gap_pair',ascending=False)
    f.to_csv(P/'regions.csv',index=False)
    print('total',total)
    for k in ['all','frequent','wider','balanced','balanced_frequent']:
        for tf,x in f[f.kind==k].groupby('tf'):
            print(k,tf,x.iloc[0][['sl','tp','cap','h0','h1','t0','t1','d0','d1','pair','gap_pair','wr','dd','gain','freq']].astype(float).round(2).tolist(),flush=True)
if __name__=='__main__':regions()
