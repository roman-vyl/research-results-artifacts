#include <math.h>
#include <stdint.h>
/* Runner TP cancellation takes effect after the decision bar. Native
   initial_r_trailing_stop starts updates only after MFE reaches D. */
void exits(int n,int start,int arm,double s,double risk,double tp,const double *hi,const double *lo,const double *op,const double *cl,const double *ds,int nd,int mode,double *ret,int64_t *exitbar,int64_t *dummy){
 double entry=s*cl[start],initial=entry-risk,peak=entry;
 for(int b=start+1;b<=arm;b++)peak=fmax(peak,s>0?hi[b]:-lo[b]);
 for(int k=0;k<nd;k++){
  double best=peak,stop=best-entry>=ds[k]*risk?fmax(initial,best-ds[k]*risk):initial;
  ret[k]=0;exitbar[k]=-1;dummy[k]=-1;
  for(int b=arm+1;b<n;b++){
   double adverse=s>0?lo[b]:-hi[b];
   if(adverse<=stop){ret[k]=adverse<=initial?-1:(stop-entry)/risk;exitbar[k]=b;break;}
   best=fmax(best,s>0?hi[b]:-lo[b]);
   if(best-entry>=ds[k]*risk)stop=fmax(stop,best-ds[k]*risk);
  }
 }
}
