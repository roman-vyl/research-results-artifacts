#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

void exits(int,int,int,double,double,double,const double*,const double*,const double*,const double*,const double*,int,int,double*,int64_t*,int64_t*);

/* Each leg has its own chronological admissions. Orders from both legs
   share equity; exits precede entries. Omit MTM between events for screening;
   shortlisted runs use the original bar-by-bar portfolio implementation. */
typedef struct {int b,x;double s,p,y;} Trade;
static double pair_net(const Trade *a,int n,const Trade *b,int m,const double *close,int *common){
    const Trade *legs[2]={a,b},*open[2]={0,0};
    int pos[2]={0,0},len[2]={n,m}; double cash=10000,qty[2]={0,0};*common=0;
    for(;;){
        int bar=2147483647;
        for(int k=0;k<2;k++){
            int next=open[k]?open[k]->x:(pos[k]<len[k]?legs[k][pos[k]].b:2147483647);
            if(next<bar)bar=next;
        }
        if(bar==2147483647)break;
        for(int k=0;k<2;k++)if(open[k]&&open[k]->x==bar){
            const Trade *t=open[k];
            cash+=qty[k]*(t->s*(t->y-t->p)-.0004*t->y);open[k]=NULL;
        }
        double eq=cash;
        for(int k=0;k<2;k++)if(open[k])eq+=qty[k]*open[k]->s*(close[bar]-open[k]->p);
        for(int k=0;k<2;k++)if(!open[k]&&pos[k]<len[k]&&legs[k][pos[k]].b==bar){
            open[k]=&legs[k][pos[k]++];qty[k]=eq*.5/(open[k]->p*1.0004);cash-=qty[k]*.0004*open[k]->p;
            if(k==1&&open[0]&&open[0]->b==bar&&open[0]->s==open[1]->s)(*common)++;
        }
    }
    return cash-10000;
}
static Trade* anchor(const double *v,int n){
    Trade *r=malloc((size_t)n*sizeof *r);for(int i=0;i<n;i++)r[i]=(Trade){v[6*i],v[6*i+1],v[6*i+2],v[6*i+3],v[6*i+4]};return r;
}
int screen(int nb,int ne,int nc,int nd,double tp,const int64_t *bars,const double *s,const double *rf,
           const int64_t *bx,const double *br,const double *hi,const double *lo,const double *cl,const double *op,
           const int64_t *arm,const double *ds,const int64_t *indices,const int64_t *offset,
           const double *av,int na,const double *bv,int nb2,double *out){
    Trade *refs[2]={anchor(av,na),anchor(bv,nb2)};
    double *r=malloc((size_t)ne*nd*sizeof *r);int64_t *x=malloc((size_t)ne*nd*sizeof *x),*hits=malloc(nd*sizeof *hits);
    Trade *list=malloc((size_t)ne*sizeof *list);
    for(int i=0;i<ne;i++){
        if(arm[i]<0)for(int k=0;k<nd;k++){r[i*nd+k]=br[i];x[i*nd+k]=bx[i];}
        else exits(nb,bars[i],arm[i],s[i],cl[bars[i]]*rf[i],tp,hi,lo,op,cl,ds,nd,0,r+i*nd,x+i*nd,hits);
    }
    for(int j=0;j<nc;j++)for(int k=0;k<nd;k++){
        int n=0,busy=-1,wins=0,active=0,above=0,fast=0;double eq=10000;
        for(int64_t u=offset[j];u<offset[j+1];u++){
            int i=indices[u],b=bars[i],ix=i*nd+k;
            if(b<=busy)continue;
            if(x[ix]<0){free(list);free(hits);free(x);free(r);free(refs[0]);free(refs[1]);return 1;}
            busy=x[ix];double p=cl[b],y=p*(1+s[i]*rf[i]*r[ix]);double ret=(s[i]*(y-p)-.0004*(y+p))/(p*1.0004);
            list[n++]=(Trade){b,busy,s[i],p,y};eq*=1+ret;wins+=ret>0;active+=arm[i]>=0;above+=r[ix]>tp+1e-8;fast+=arm[i]>=0&&busy-arm[i]<=12;
        }
        double *o=out+((size_t)j*nd+k)*10;
        o[0]=eq-10000;o[1]=n;o[2]=wins;o[3]=active;o[4]=above;o[5]=fast;
        for(int z=0;z<2;z++){int common=0;o[6+2*z]=pair_net(refs[z],z==0?na:nb2,list,n,cl,&common);o[7+2*z]=common;}
    }
    free(list);free(hits);free(x);free(r);free(refs[0]);free(refs[1]);return 0;
}
void cross_scan(const double *cl,const double *values,const int64_t *offset,int n,int split,double *out){
    Trade **legs=malloc(n*sizeof *legs);
    for(int i=0;i<n;i++)legs[i]=anchor(values+6*offset[i],offset[i+1]-offset[i]);
    for(int i=0;i<split;i++)for(int j=split;j<n;j++){
        int common=0;double *cell=out+2*((size_t)i*(n-split)+j-split);
        cell[0]=pair_net(legs[i],offset[i+1]-offset[i],legs[j],offset[j+1]-offset[j],cl,&common);
        cell[1]=common;
    }
    for(int i=0;i<n;i++)free(legs[i]);free(legs);
}
