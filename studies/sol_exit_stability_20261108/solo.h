#include "../stage2_cross_coin_review/ema200_td_candidates_20261108/eth_categories/touch_pairs/protected/fine/drawdown.h"
static const int64_t *month_ends; static int nm; static int *year_at; static int complete0,complete1;
static double period_stats[15];
void init_periods(const int64_t *ends,int n,int *ys,int c0,int c1){month_ends=ends;nm=n;year_at=ys;complete0=c0;complete1=c1;}
static int cmpdouble(const void *a,const void *b){double x=*(double*)a,y=*(double*)b;return (x>y)-(x<y);}
static double median(double *a,int n){if(!n)return NAN;qsort(a,n,sizeof(double),cmpdouble);return n%2?a[n/2]:(a[n/2-1]+a[n/2])/2;}
static double solo(const Trade *tr,int n,const double *cl,double *dd){
 double cash=10000,peak=cash,curve[1000],side[2]={0,0};int mi=0;
 if(dd)*dd=0;
 for(int i=0;i<n;i++){
  Trade t=tr[i];
  while(mi<nm&&month_ends[mi]<t.b)curve[mi++]=cash;
  double qty=cash/(t.p*1.0004);cash-=qty*.0004*t.p;
  double intercept=cash-qty*t.s*t.p,slope=qty*(t.s-.0004);
  if(dd)mark(t.b,t.x,intercept,slope,&peak,dd);
  while(mi<nm&&month_ends[mi]<t.x){curve[mi]=intercept+slope*cl[month_ends[mi]];mi++;}
  cash+=qty*(t.s*(t.y-t.p)-.0004*t.y);side[t.s>0?0:1]+=qty*(t.s*(t.y-t.p)-.0004*(t.y+t.p));
  if(dd){peak=fmax(peak,cash);*dd=fmax(*dd,1-cash/peak);}
 }
 while(mi<nm)curve[mi++]=cash;
 if(dd){
  *dd*=100;double sum=0,squares=0,lowest=1e9,mr[1000];int pos=0,mc=complete1-complete0;
  for(int j=complete0;j<complete1;j++){double r=100*(curve[j]/(j?curve[j-1]:10000)-1);sum+=r;squares+=r*r;lowest=fmin(lowest,r);pos+=r>1e-8;mr[j-complete0]=r;}
  period_stats[0]=sqrt(fmax(0,squares/mc-pow(sum/mc,2)));period_stats[1]=100.*pos/mc;period_stats[2]=lowest;period_stats[3]=median(mr,mc);
  double annual[6]={0},gains[6]={0},previous=10000;
  for(int j=0;j<nm;j++)if(j==nm-1||year_at[j+1]!=year_at[j]){int y=year_at[j]-2021;annual[y]=100*(curve[j]/previous-1);gains[y]=curve[j]-previous;previous=curve[j];}
  sum=0;squares=0;lowest=1e9;double maxgain=-1e30,total=0;
  for(int y=1;y<5;y++){sum+=annual[y];squares+=annual[y]*annual[y];lowest=fmin(lowest,annual[y]);maxgain=fmax(maxgain,gains[y]);total+=gains[y];}
  period_stats[4]=sqrt(fmax(0,squares/4-pow(sum/4,2)));period_stats[5]=lowest;period_stats[6]=100*maxgain/total;
  for(int y=0;y<6;y++)period_stats[7+y]=annual[y];period_stats[13]=side[0];period_stats[14]=side[1];
 }
 return cash-10000;
}
#define equity_scan(a,n,b,m,cl,cm,dd) solo(b,m,cl,dd)
#define pair_net(a,n,b,m,cl,cm) solo(b,m,cl,NULL)
