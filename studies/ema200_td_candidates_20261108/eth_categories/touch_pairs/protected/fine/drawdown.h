#include "../../screen.c"
/* Sparse extrema table. Only intervals that can exceed the recorded drawdown
   and have an unknown peak/trough order require chronological subdivision. */
static double *low_table,*high_table;static int stride;
void init_prices(const double *cl,int n){
    stride=n;int levels=32-__builtin_clz((unsigned)n);
    low_table=malloc((size_t)n*levels*sizeof(double));high_table=malloc((size_t)n*levels*sizeof(double));
    memcpy(low_table,cl,n*sizeof(double));memcpy(high_table,cl,n*sizeof(double));
    for(int level=1;level<levels;level++){
        int half=1<<(level-1);double *lo=low_table+(size_t)n*level,*hi=high_table+(size_t)n*level;
        for(int i=0;i+2*half<=n;i++){lo[i]=fmin(lo[i-n],lo[i+half-n]);hi[i]=fmax(hi[i-n],hi[i+half-n]);}
    }
}
void release_prices(void){free(low_table);free(high_table);}
static void mark(int a,int b,double cash,double slope,double *peak,double *dd){
    if(a>=b)return;
    int lv=31-__builtin_clz((unsigned)(b-a));int end=b-(1<<lv);
    double *lo=low_table+(size_t)stride*lv,*hi=high_table+(size_t)stride*lv;
    double x=cash+slope*fmin(lo[a],lo[end]),y=cash+slope*fmax(hi[a],hi[end]);
    double bottom=fmin(x,y),top=fmax(x,y),newpeak=fmax(*peak,top);
    if(top<=*peak||b==a+1){*dd=fmax(*dd,1-bottom/newpeak);*peak=newpeak;return;}
    if(1-bottom/newpeak<=*dd){*peak=newpeak;return;}
    int mid=a+(b-a)/2;mark(a,mid,cash,slope,peak,dd);mark(mid,b,cash,slope,peak,dd);
}
static double equity_scan(const Trade *a,int n,const Trade *b,int m,const double *cl,int *common,double *dd){
    const Trade *legs[]={a,b},*open[]={NULL,NULL};int len[]={n,m},pos[]={0,0};double cash=10000,peak=cash,qty[]={0.,0.};
    *common=0;*dd=0.;
    for(;;){
        int bar=2147483647;
        for(int k=0;k<2;k++){int next=open[k]?open[k]->x:pos[k]<len[k]?legs[k][pos[k]].b:2147483647;if(next<bar)bar=next;}
        if(bar==2147483647)break;
        for(int k=0;k<2;k++)if(open[k]&&open[k]->x==bar){
            const Trade *t=open[k];cash+=qty[k]*(t->s*(t->y-t->p)-.0004*t->y);open[k]=NULL;}
        double eq=cash;
        for(int k=0;k<2;k++)if(open[k])eq+=qty[k]*open[k]->s*(cl[bar]-open[k]->p);
        for(int k=0;k<2;k++)if(!open[k]&&pos[k]<len[k]&&legs[k][pos[k]].b==bar){
            open[k]=&legs[k][pos[k]++];qty[k]=eq*.5/(open[k]->p*1.0004);cash-=qty[k]*.0004*open[k]->p;
            if(k==1&&open[0]&&open[0]->b==bar&&open[0]->s==open[1]->s)(*common)++;}
        int end=stride;double intercept=cash,slope=0;
        for(int k=0;k<2;k++){
            int next=open[k]?open[k]->x:pos[k]<len[k]?legs[k][pos[k]].b:stride;if(next<end)end=next;
            if(open[k]){intercept-=qty[k]*open[k]->s*open[k]->p;slope+=qty[k]*(open[k]->s-.0004);}}
        if(open[0]||open[1])mark(bar,end,intercept,slope,&peak,dd);
        else{peak=fmax(peak,cash);*dd=fmax(*dd,1-cash/peak);}
    }
    *dd*=100;return cash-10000;
}
