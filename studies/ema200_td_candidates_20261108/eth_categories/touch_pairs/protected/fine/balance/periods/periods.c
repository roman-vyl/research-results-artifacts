#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
void exits(int,int,int,double,double,double,const double*,const double*,const double*,const double*,const double*,int,int,double*,int64_t*,int64_t*);
void shared(const double*,int64_t,const double*,int64_t,const double*,int64_t,const uint8_t*,double,double,int64_t,const int64_t*,int,const int64_t*,int,double*,double*);

/* Replay one T across every D, threshold and touch cap, marking the common
   account at the end of every calendar month with the original pair simulator. */
void periods(int n,int nd,int nh,int nb,int nm,int na,double tp,const double *cl,const double *hi,const double *lo,const double *op,const int64_t *bars,const double *side,const double *rf,const int64_t *base_exit,const double *base_r,const int64_t *arm,const double *ds,const int64_t *adx,const int64_t *be,const int64_t *touch,const double *anchor,const int64_t *ends,double *curves) {
 double *rr=malloc(sizeof(double)*n*nd),*ledger=malloc(sizeof(double)*6*n),*prev=malloc(sizeof(double)*6*n);
 int64_t *ex=malloc(sizeof(int64_t)*n*nd),*dummy=malloc(sizeof(int64_t)*nd);
 uint8_t *flags=calloc(n+na,1); double out[21];
 for(int j=0;j<n;j++){
    if(arm[j]>=0) exits(nb,bars[j],arm[j],side[j],cl[bars[j]]*rf[j],tp,hi,lo,op,cl,ds,nd,0,rr+j*nd,ex+j*nd,dummy);
    else for(int k=0;k<nd;k++){rr[j*nd+k]=base_r[j];ex[j*nd+k]=base_exit[j];}
 }
 for(int d=0;d<nd;d++)for(int cap=0;cap<5;cap++){
  int prev_n=-1;
  for(int h=0;h<nh;h++){
   double *result=curves+(((d*5+cap)*nh+h)*nm);int count=0,busy=-1;
   for(int j=0;j<n;j++){
    int b=bars[j];if(b<=busy||(cap&&(touch[j]<1||touch[j]>cap)))continue;
    int a=adx[h*n+j],u=be[h*n+j],x=ex[j*nd+d],t=arm[j];double s=side[j],p=cl[b],r=rr[j*nd+d];
    if(a>=0&&(t<0||a<t)&&u>=0&&u<=x&&(t<0||u<=t)&&s*(s>0?lo[u]-p:hi[u]-p)>-rf[j]*p){x=u;r=0;}
    double *row=ledger+6*count++;row[0]=b;row[1]=x;row[2]=s;row[3]=p;row[4]=p*(1+s*r*rf[j]);row[5]=rf[j];busy=x;
   }
   if(prev_n==count&&!memcmp(ledger,prev,sizeof(double)*6*count)){memcpy(result,result-nm,sizeof(double)*nm);continue;}
   shared(cl,nb,anchor,na,ledger,count,flags,.5,.5,0,NULL,0,ends,nm,result,out);
   if(out[13]!=0)abort();
   memcpy(prev,ledger,sizeof(double)*6*count);prev_n=count;
  }
 }
 free(rr);free(ledger);free(prev);free(ex);free(dummy);free(flags);
}
