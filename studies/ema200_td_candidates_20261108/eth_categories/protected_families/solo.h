#include "drawdown.h"
/* A single leg uses the full account at entry, pays both fees, and is
   marked at each close at the position's liquidation value. */
static double solo(const Trade *tr,int n,const double *cl,double *dd){
 double cash=10000,peak=cash;
 if(dd)*dd=0;
 for(int i=0;i<n;i++){
  Trade t=tr[i];double qty=cash/(t.p*1.0004);
  cash-=qty*.0004*t.p;
  if(dd)mark(t.b,t.x,cash-qty*t.s*t.p,qty*(t.s-.0004),&peak,dd);
  cash+=qty*(t.s*(t.y-t.p)-.0004*t.y);
  if(dd){peak=fmax(peak,cash);*dd=fmax(*dd,1-cash/peak);}
 }
 if(dd)*dd*=100;
 return cash-10000;
}
#define equity_scan(a,n,b,m,cl,cm,dd) solo(b,m,cl,dd)
#define pair_net(a,n,b,m,cl,cm) solo(b,m,cl,NULL)
