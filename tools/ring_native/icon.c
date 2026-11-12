/* Fixed feature numeric kernel; no filesystem, network, or device authority. */
#include "ring.h"
#include <stdint.h>
#include <stddef.h>
#include <float.h>
#include <math.h>
#include <fenv.h>
#include "features.h"
_Static_assert(FLT_RADIX==2 && DBL_MANT_DIG==53 && sizeof(double)==8,"binary64 required");
#define WIDTH 896
#define HEIGHT 414
/* Each volatile store completes one Python binary64 operation; no FMA. */
static double add(double a,double b){volatile double r=a+b;return r;}
static double sub(double a,double b){volatile double r=a-b;return r;}
static double mul(double a,double b){volatile double r=a*b;return r;}
static double divide(double a,double b){volatile double r=a/b;return r;}
static double root(double a){volatile double r=sqrt(a);return r;}
static double max0(double a){return a>0.0?a:0.0;}
static int min_i(int a,int b){return a<b?a:b;}
static int max_i(int a,int b){return a>b?a:b;}
/* These are the exact binary64 values of the original Python literals. */
#define F37 0x1.7ae147ae147aep-2
#define F130 0x1.4cccccccccccdp+0
#define F55 0x1.199999999999ap-1
#define F45 0x1.ccccccccccccdp-2
#define F80 0x1.999999999999ap-1
#define F20 0x1.999999999999ap-3
const char *ring_feature_sha256(void){return FIXED_FEATURE_SHA256;}
/* Caller owns rgba and cancellation. Raw best is rounded by the Python caller. */
int ring_icon(const unsigned char *rgba,size_t bytes,int cx,int sy,int mode,
                int (*cancelled)(void),double *raw_best,int box[4]){
    if((mode!=0&&mode!=1)||!rgba||bytes!=(size_t)WIDTH*HEIGHT*4||!raw_best||!box||fegetround()!=FE_TONEAREST)return -1;
    double best=0.0;box[0]=cx-16;box[1]=sy+24;box[2]=33;box[3]=28;
    for(size_t s=0;s<sizeof(sprites)/sizeof(sprites[0]);s++){
        const Sprite *sp=&sprites[s];
        int count=sp->count,dark_count=sp->dark_count;
        double dc=(double)count,dd=(double)dark_count;
        for(int y=max_i(0,sy+24);y<=min_i(HEIGHT-sp->height,sy+57);y++){
            if(cancelled&&cancelled())return 1;
            for(int x=max_i(0,cx-sp->width/2-8);x<=min_i(WIDTH-sp->width,cx-sp->width/2+8);x++){
                unsigned char observed[344][3];
                int64_t dot=0,total=0,square=0,cross=0;
                for(int k=0;k<count;k++){
                    const Bright *p=&sp->bright[k];size_t at=4*((size_t)(y+p->dy)*WIDTH+x+p->dx);
                    int a=rgba[at],c=rgba[at+1],d=rgba[at+2],v=a+c+d;
                    observed[k][0]=(unsigned char)a;observed[k][1]=(unsigned char)c;observed[k][2]=(unsigned char)d;
                    dot+=(int64_t)a*p->r+(int64_t)c*p->g+(int64_t)d*p->b;
                    total+=v;square+=(int64_t)v*v;cross+=(int64_t)v*(p->r+p->g+p->b);
                }
                double norm=root(max0(mul(sub((double)square,divide((double)(total*total),dc)),sp->target_var)));
                double shape=max0(divide(sub((double)cross,divide((double)(total*sp->target_sum),dc)),norm>9.0?norm:9.0));
                double upper=mul(add(divide(mul(F55,dc),dc),mul(F45,shape)),add(F80,divide(mul(F20,dd),dd)));
                if(upper<=best)continue;
                double gain=divide((double)dot,(double)sp->energy);
                gain=gain<F37?F37:gain;gain=gain>F130?F130:gain;
                double tolerance=mul(3.0,add(13.0,mul(15.0,gain)));
                int matches=0;
                for(int k=0;k<count;k++){
                    const Bright *p=&sp->bright[k];
                    double values[3]={fabs(sub((double)observed[k][0],mul(gain,(double)p->r))),
                                      fabs(sub((double)observed[k][1],mul(gain,(double)p->g))),
                                      fabs(sub((double)observed[k][2],mul(gain,(double)p->b)))};
                    double error=0.0,correction=0.0;
                    for(int channel=0;channel<3;channel++){
                        double value=values[channel],next=add(error,value);
                        if(mode==1){
                            double delta=fabs(error)>=fabs(value)?add(sub(error,next),value):add(sub(value,next),error);
                            correction=add(correction,delta);
                        }
                        error=next;
                    }
                    if(mode==1&&correction!=0.0)error=add(error,correction);
                    matches+=error<tolerance;
                }
                int outline=0;
                for(int k=0;k<dark_count;k++){
                    const Dark *p=&sp->dark[k];size_t at=4*((size_t)(y+p->dy)*WIDTH+x+p->dx);
                    outline+=rgba[at]+rgba[at+1]+rgba[at+2]<144;
                }
                double score=mul(add(divide(mul(F55,(double)matches),dc),mul(F45,shape)),
                                 add(F80,divide(mul(F20,(double)outline),dd)));
                if(score>best){best=score;box[0]=x;box[1]=y;box[2]=sp->width;box[3]=sp->height;}
            }
        }
    }
    *raw_best=best;return 0;
}
