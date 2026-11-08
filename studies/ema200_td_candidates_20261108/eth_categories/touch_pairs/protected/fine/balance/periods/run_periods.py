from pathlib import Path
import sys,ctypes,subprocess,tempfile,json
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent
sys.path[:0]=[str(P.parent),str(P.parent.parent)]
from aggregate import BLOCKS
from read_cube import Cube,layer,Market,A,R,old

def metrics(curves, months, complete):
    prior=np.column_stack([np.ones(len(curves)),curves[:,:-1]])
    change=100*(curves/prior-1)
    yr=months.astype('datetime64[Y]').astype(int)+1970
    ends=np.r_[np.where(np.diff(yr))[0],len(yr)-1]
    ye=curves[:,ends];first=np.column_stack([np.ones(len(ye)),ye[:,:-1]])
    annual=100*(ye/first-1); dollars=(ye-first)*10000
    full=annual[:,1:-1]
    mo=change[:,complete];bins=dollars[:,1:-1]
    res=dict(m_sd=mo.std(1),m_positive=(mo>1e-8).mean(1)*100,m_worst=mo.min(1),m_median=np.median(mo,axis=1),
             y_sd=full.std(1),y_worst=full.min(1),best_share=bins.max(1)/bins.sum(1)*100)
    res.update({str(int(y)):v for y,v in zip(yr[ends],annual.T)})
    return res,change

def run():
    rows=[]; details=[]; master=[]
    with tempfile.TemporaryDirectory() as tmp:
        m=Market('eth',tmp);ind=old.indicators('eth',m.m);anchor=m.ledger(A)[0]
        times=m.z['time'].astype('datetime64[ms]');mon=times.astype('datetime64[M]')
        ends=np.r_[np.flatnonzero(mon[1:]!=mon[:-1]),len(mon)-1].astype('int64')
        months=mon[ends]
        complete=(months>mon[0])&(months<mon[-1])
        if times[0]==mon[0].astype('datetime64[ms]'):complete[0]=True
        if times[-1]+np.timedelta64(5,'m')==(mon[-1]+1).astype('datetime64[ms]'):complete[-1]=True
        subprocess.run(['cc','-O3','-shared','-fPIC',str(P/'periods.c'),str(R/'research/w8_td_geometry/engine_level_exits.c'),str(R/'research/stage2_cross_coin_review/nvs_same_coin_shared_equity_20261106_v1/shared.c'),'-o',tmp+'/periods.so'],check=True)
        fn=ctypes.CDLL(tmp+'/periods.so').periods;fn.argtypes=[ctypes.c_int]*6+[ctypes.c_double]+[ctypes.c_void_p]*17;fn.restype=None
        sim=m.sims[len(times)];sim.z['dayends']=ends
        for sl in [4,4.25,4.5,4.75,5]:
          for tp in [3.5,4,4.5,5]:
            c=Cube(170,sl,tp);ts=sorted(c.ts)
            b,s,rf,bx,br,arms,labels,adx,touch,capv=layer(m,ind,170,sl,tp,ts)
            labels=np.array(labels)
            band=(labels[:,0]==5)&(labels[:,1]>=9.3)&(labels[:,1]<=10.05)
            selected=band.copy();selected[0]=True
            matches=[]
            for name,bsl,btp,cap,tf,h0,h1,t0,t1,d0,d1 in BLOCKS:
                if (sl,tp)!=(bsl,btp):continue
                mask=(labels[:,0]==tf)&(labels[:,1]>=h0)&(labels[:,1]<=h1)
                matches.append((name,cap,t0,t1,d0,d1,mask));selected|=mask
            ix=np.flatnonzero(selected);signals=adx[ix];cross=touch[ix];tf,h=labels[ix].T;nm=len(ends)
            for i,t in enumerate(ts):
                ds=np.arange(1.25,min(t,3)+.01,.25)
                curves=np.empty((len(ds),5,len(ix),nm))
                args=[*(m.m[k] for k in ['c','h','l','o']),b,s,rf,bx,br,arms[i],ds,signals,cross,capv,anchor,ends,curves]
                fn(len(b),len(ds),len(ix),len(times),nm,len(anchor),tp,*[v.ctypes.data for v in args])
                for j,d in enumerate(ds):
                  for cap in range(5):
                    outcome=curves[j,cap];v=c.ts[t][c.rev[ix],j,cap]
                    np.testing.assert_allclose(10000*(outcome[:,-1]-1),v[:,1],rtol=0,atol=1e-6)
                    raw,ret=metrics(outcome,months,complete)
                    base=ret[0];dif=ret-base
                    freq=100*v[:,4]/v[:,3]
                    delta={k:a-a[0] for k,a in raw.items()}
                    info=pd.DataFrame(dict(sl=sl,tp=tp,t=t,d=d,cap=cap,tf=tf,h=h,freq=freq,
                         month_win=(dif[:,complete]>1e-7).mean(1)*100,month_loss=(dif[:,complete]<-1e-7).mean(1)*100,
                         **raw,**{'delta_'+k:a for k,a in delta.items()},
                         **{'td_'+k:np.repeat(a[0],len(ix)) for k,a in raw.items()}))
                    master.append(info[band[ix]])
                    for name,bc,t0,t1,d0,d1,mask in matches:
                        if cap!=bc or not (t0<=t<=t1 and d0<=d<=d1):continue
                        sel=mask[ix];rows.append(info[sel].assign(plateau=name))
                        details.append(pd.DataFrame(dict(plateau=name,month=np.tile(months.astype(str),sum(sel)),protected=ret[sel].ravel(),td=np.tile(base,sum(sel)),diff=dif[sel].ravel())))
            print('complete',sl,tp,flush=True)
        from grid_scan import B
        stars=sim.run(0,ta=anchor,tb=m.ledger(B)[0],aa=.5,ab=.5,curve=True)
        st,_=metrics(np.array(stars['curve'])[None,:],months,complete)
        (P/'dates.json').write_text(json.dumps(dict(start=str(times[0]),end=str(times[-1]),complete_months=[str(v) for v in months[complete]],stars={k:float(a[0]) for k,a in st.items()})))
    band=pd.concat(master);blocks=pd.concat(rows);periods=pd.concat(details)
    assert len(band)==94400 and len(blocks)==340
    periods.groupby(['plateau','month']).median().to_csv(P/'months.csv',float_format='%.6f')
    blocks.to_csv(P/'cells.csv.gz',index=False,float_format='%.6f')
    planes=[]
    for name,x in [('все',band),('20–30%',band[(band.freq>20)&(band.freq<=30)]),('30–40%',band[(band.freq>30)&(band.freq<=40)])]:
        plane=x.groupby(['sl','tp']).median(numeric_only=True)
        plane['cells']=x.groupby(['sl','tp']).size();plane['band']=name;planes.append(plane)
    planes=pd.concat(planes).reset_index()
    planes.to_csv(P/'planes.csv',index=False,float_format='%.6f')
    summary=planes.groupby('band').median(numeric_only=True).reset_index().rename(columns={'band':'region'})
    blocks_summary=blocks.groupby('plateau').median(numeric_only=True).reset_index().rename(columns={'plateau':'region'})
    pd.concat([summary,blocks_summary],ignore_index=True).to_csv(P/'summary.csv',index=False,float_format='%.6f')
if __name__=='__main__':run()
