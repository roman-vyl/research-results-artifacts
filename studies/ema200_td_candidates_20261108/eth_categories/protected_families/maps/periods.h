#include "solo.h"
// Calendar cut-offs use the same close and estimated exit fee as MTM DD.
static const int64_t *ends,*years,*complete;
static int months;
void calendar(const int64_t *m,const int64_t *y,const int64_t *full,int len){
 ends=m;years=y;complete=full;months=len;
}
static void periods(const Trade *tr,int n,const double *cl,double *out){
 double cash=10000,prev=cash,yr_start=cash,m_sum=0,m_s2=0,m_worst=100,y_sum=0,y_s2=0,y_min=1000;
 int j=0,nm=0,win=0,ny=0,year0=years[0];
 for(int k=0;k<months;k++){
  int b=ends[k];
  while(j<n&&tr[j].x<=b){
   Trade t=tr[j++];double q=cash/(t.p*1.0004);
   cash+=q*(t.s*(t.y-t.p)-.0004*(t.p+t.y));
  }
  double eq=cash;
  if(j<n&&tr[j].b<=b){
   Trade t=tr[j];double q=cash/(t.p*1.0004);
   eq+=q*(t.s*(cl[b]-t.p)-.0004*(t.p+cl[b]));
  }
  double mr=100*(eq/prev-1);prev=eq;
  if(complete[k]){nm++;m_sum+=mr;m_s2+=mr*mr;win+=mr>1e-8;m_worst=fmin(m_worst,mr);}
  if(k==months-1||years[k+1]!=years[k]){
   double yr=100*(eq/yr_start-1);yr_start=eq;out[5+years[k]-year0]=yr;
   if(years[k]>year0&&years[k]<years[months-1]){ny++;y_sum+=yr;y_s2+=yr*yr;y_min=fmin(yr,y_min);}
  }
 }
 out[0]=sqrt(fmax(0,m_s2/nm-pow(m_sum/nm,2)));out[1]=100.*win/nm;out[2]=m_worst;
 out[3]=sqrt(fmax(0,y_s2/ny-pow(y_sum/ny,2)));out[4]=y_min;
}
