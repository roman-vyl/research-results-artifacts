#include "drawdown.h"
/* Stop at the entry price is active from the bar AFTER ADX. The original
   stop wins on a conflict; TP stays live until a TD phase change. Only
   the first entry-price touch before (or on) the TD decision can alter
   an exit: after that decision the runner's stop is at least entry (D<=T). */
void sweep_be(int ne,int nd,int nh,int nb,double tp,const double *cl,const double *hi,const double *lo,const double *op,
 const int64_t *bars,const double *sg,const double *rf,const int64_t *bx,const double *br,const int64_t *td,
 const double *ds,const int64_t *protect,const int64_t *touch,const int64_t *cap,const double *anchor6,int na,double *out){
 double *gap=malloc(ne*sizeof(double)), *prev_gap=malloc(ne*sizeof(double)); Trade *prev=malloc(ne*sizeof(Trade)); Trade *anchorA=anchor(anchor6,na),*ledger=malloc(ne*sizeof *ledger);
 int64_t *xx=malloc((size_t)ne*nd*sizeof *xx),*hits=malloc(nd*sizeof *hits);
 double *rr=malloc((size_t)ne*nd*sizeof *rr);
 for(int j=0;j<ne;j++){
   if(td[j]>=0)exits(nb,bars[j],td[j],sg[j],cl[bars[j]]*rf[j],tp,hi,lo,op,cl,ds,nd,0,rr+j*nd,xx+j*nd,hits);
   else for(int k=0;k<nd;k++){rr[j*nd+k]=br[j];xx[j*nd+k]=bx[j];}
 }
 for(int k=0;k<nd;k++)for(int l=0;l<=4;l++){
 int pn=-1,common=0;double pair=0,dd=0,stressed=0;
 for(int h=0;h<nh;h++){
   int n=0,wins=0,busy=-1,armed=0,be=0,saved=0,hurt=0,neutral=0,runner=0,above=0,missed=0,samebar=0;
   double eq=10000,savedR=0,hurtR=0;
   for(int j=0;j<ne;j++){
     int b=bars[j];if(b<=busy||(l&&(cap[j]<1||cap[j]>l)))continue;
     int x=xx[j*nd+k],a=protect[h*ne+j],t=touch[h*ne+j],tr=td[j];double r=rr[j*nd+k],s=sg[j],p=cl[b];
     samebar+=a>=0&&a==tr;
     int pro=a>=0&&(tr<0||a<tr);armed+=pro;
     int cut=pro&&t>=0&&t<=x&&(tr<0||t<=tr);
     if(cut){
       int conflict=sg[j]*(sg[j]>0?lo[t]-p:hi[t]-p)<=-rf[j]*p;
       /* A first touch hitting the initial stop before TD cannot change the baseline. */
       if(conflict)cut=0;
     }
     if(cut){be++;saved+=r< -1e-8;hurt+=r>1e-8;neutral+=fabs(r)<=1e-8;
       savedR+=fmax(0,-r);hurtR+=fmax(0,r);missed+=r>tp+1e-8;x=t;r=0;
     }
     runner+=tr>=0&&!cut;above+=r>tp+1e-8;
     double ret=(r*rf[j]-.0004*(2+s*r*rf[j]))/1.0004;
     gap[n]=cut&&s*(op[x]-p)<0?op[x]:p*(1+s*r*rf[j]); eq*=1+ret;wins+=ret>0;busy=x;ledger[n++]=(Trade){b,x,s,p,p*(1+s*r*rf[j])};
   }
   if(n!=pn||memcmp(prev,ledger,n*sizeof(Trade))||memcmp(prev_gap,gap,n*sizeof(double))){
     pn=n; memcpy(prev,ledger,n*sizeof(Trade));memcpy(prev_gap,gap,n*sizeof(double));
     pair=equity_scan(anchorA,na,ledger,n,cl,&common,&dd);
     for(int i=0;i<n;i++)ledger[i].y=gap[i];
     stressed=pair_net(anchorA,na,ledger,n,cl,&common);
   }
   double *v=out+(((size_t)h*nd+k)*5+l)*19;
   v[0]=eq-10000;v[1]=pair;v[2]=wins;v[3]=n;v[4]=armed;v[5]=be;v[6]=saved;v[7]=hurt;v[8]=neutral;
   v[9]=runner;v[10]=above;v[11]=missed;v[12]=savedR;v[13]=hurtR;v[14]=common;v[15]=n+na-common;v[16]=samebar;v[17]=dd;v[18]=stressed;
 }
 }
 free(gap);free(prev_gap);free(prev);free(anchorA);free(ledger);free(xx);free(hits);free(rr);
}
