from replay import OUT, Market, source, DIST, tempfile, np, pd

def audit(m, indicators, sl, tp, tf, cut, d):
    z=m.z
    close,high,low,op=(m.m[k] for k in ("c","h","l","o"))
    a,q=list(z['sls']).index(sl),list(z['ratios']).index(tp)
    adx,plus,minus=[indicators[f"{tf}_{k}"] for k in ("adx","plus","minus")]
    records=[]; busy=-1
    for i in z['ix'][3,290]:
        start=z['bars'][i]; side=z['side'][i]
        if m.block[i] or start<=busy:continue
        base_end=z['xb'][i,a,q]
        r=z['rr'][i,a,q]; end=base_end
        mask=(adx[start+1:end]-adx[start]>=cut)&(side*(plus[start+1:end]-minus[start+1:end])>0)
        hit=np.flatnonzero(mask)
        arm=-1; gross=r; risk=z['ar'][i]*sl*close[start]
        if len(hit):
            arm=start+1+hit[0]
            gain=lambda j:side*((high if side>0 else low)[j]-close[start])/risk
            adverse=lambda j:side*((low if side>0 else high)[j]-close[start])/risk
            peak=max(0.,np.max(gain(slice(start+1,arm+1))))
            for j in range(arm+1,len(close)):
                stop=max(-1.,peak-d)
                if adverse(j)<=stop:
                    end=j;gross=-1 if adverse(j)<=-1 else stop
                    break
                peak=max(peak,gain(j))
            else:raise ValueError("open at sample end")
        rows=[sl,tp,tf,cut,d,start,end,side,arm,r,gross]
        records.append(rows);busy=end
    frame=pd.DataFrame(records,columns=['sl','tp','tf','cut','d','entry_bar','exit_bar','side','arm_bar','original_R','exit_R'])
    for col in ('entry','exit','arm'):
        frame[col+'_utc']=[str(z['time'][int(b)].astype('datetime64[ms]')) if b>=0 else '' for b in frame[col+'_bar']]
    suffix='' if tp==4.5 else f'_tp{tp:g}'
    grid=pd.read_csv(OUT/f'grid_3_290_{sl:g}{suffix}.csv.gz')
    ref=grid[(grid.tf==tf)&(grid.cut==cut)&(grid.d==d)].iloc[0]
    ar=frame.arm_bar>=0
    assert ref.n==len(frame) and ref.act==ar.sum() and ref.above==(frame.exit_R>tp+1e-8).sum()
    entry=frame.entry_bar.to_numpy();side=frame.side.to_numpy()
    fractions=z['ar'][[next(i for i in z['ix'][3,290] if z['bars'][i]==b and z['side'][i]==s) for b,s in zip(entry,side)]]*sl
    ret=frame.exit_R.to_numpy()*fractions
    net=(10000*np.prod(1+(ret-.0004*(2+side*ret))/1.0004)-10000)
    assert abs(net-ref.net)<.001
    return frame

if __name__=='__main__':
    with tempfile.TemporaryDirectory() as tmp:
        m=Market('eth',tmp);ind=source.indicators('eth',m.m)
        configs=[(4.75,4.5,5,46.5,1.75),(4.75,4.5,15,26,1.75),(5,5,15,26.75,1.5),(5,5,60,5,3),(5,5,60,1.5,3)]
        pd.concat([audit(m,ind,*c) for c in configs]).to_csv(OUT/'selected_trades.csv',index=False)
        refs=[]
        for sl,tp in [(4.75,4.5),(5,5)]:
            for d in (1.5,1.75,2,3):
                p=dict(w=3,lb=290,sl=sl,tp=tp,cap=0,t=4,d=d)
                r=m.calc(p,alloc=1);ledger,_=m.ledger(p)
                gross=ledger[:,2]*(ledger[:,4]/ledger[:,3]-1)/ledger[:,5]
                refs.append(dict(sl=sl,tp=tp,t=4,d=d,net=r['net'],wr=r['wr'],dd=-r['dd'],n=r['n'],above=int((gross>tp+1e-8).sum())))
        pd.DataFrame(refs).to_csv(OUT/'td_controls.csv',index=False)
