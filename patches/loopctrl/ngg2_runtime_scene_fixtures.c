/* Runtime integration fixtures only. Deterministic world texture plus existing
 * small TEST013 HUD masks exercise real perception, planning, HUD and motion.
 * They are synthetic host coverage, never an unseen/device acceptance set. */
#include "ngg2_runtime_scene_fixtures.h"
#include "ngg2/NG2Templates.h"
#include <math.h>
#define FW 896
#define FH 414
#define FS ((size_t)FW*FH*4)
static int floor_div(int value,int divisor){
    int result=value/divisor;
    return value<0&&value%divisor?result-1:result;
}
static int bounded(int value){return value<0?0:value>255?255:value;}
static void pixel(uint8_t *out,int x,int y,int r,int g,int b){
    size_t k;
    if(x<0||x>=FW||y<0||y>=FH)return;
    k=((size_t)y*FW+(size_t)x)*4;
    out[k]=(uint8_t)bounded(r);out[k+1]=(uint8_t)bounded(g);
    out[k+2]=(uint8_t)bounded(b);out[k+3]=255;
}
static void rectangle(uint8_t *out,int x0,int y0,int x1,int y1,int r,int g,int b){
    int x,y;for(y=y0;y<y1;++y)for(x=x0;x<x1;++x)pixel(out,x,y,r,g,b);
}
static void template_mask(uint8_t *out,const NG2Template *t){
    int x,y;
    rectangle(out,t->x,t->y,t->x+t->w,t->y+t->h,0,0,0);
    for(y=0;y<t->h;++y)for(x=0;x<t->w;++x)
        if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1)
            pixel(out,t->x+x,t->y+y,180,180,180);
}
int ng2_fixture_floor_pixels_rgba(uint8_t *out,size_t length,int32_t world_x,
                                 int32_t world_y,double q,int32_t goods){
    int x,y,k;
    if(!out||length!=FS||world_x < -576||world_x>576||world_y < -576||world_y>576
       ||!isfinite(q)||q<0||q>=1||(goods!=0&&goods!=1))return 0;
    /* Referencing the unused menu masks keeps this shared fixed-mask header
     * warning-clean under GCC/Clang's strict unused-const diagnostics. */
    (void)&ng2_template_continue;(void)&ng2_template_restart;(void)&ng2_template_death;
    for(y=0;y<FH;++y)for(x=0;x<FW;++x){
        int wx=x+world_x,wy=y+world_y;
        int tx=floor_div(wx-448+18,36),ty=floor_div(wy-207+18,36);
        uint32_t hash=(uint32_t)wx*UINT32_C(0x9e3779b9)^(uint32_t)wy*UINT32_C(0x85ebca6b);
        int noise,r=26,g=16,b=16;
        hash^=hash>>16;hash*=UINT32_C(0x7feb352d);hash^=hash>>15;
        noise=(int)(hash%9)-4;
        if((tx==-1||tx==1)&&ty==-3){r=199;g=164;b=63;}
        else if(tx==0&&ty==-3){r=63;g=19;b=0;}
        else if((tx==-4&&ty==-2)||(tx==5&&ty==1)){r=80;g=80;b=80;}
        pixel(out,x,y,r+noise,g+noise,b+noise);
    }
    template_mask(out,&ng2_template_icon);template_mask(out,&ng2_template_footer);
    template_mask(out,&ng2_template_zone_one);template_mask(out,&ng2_template_floor_one);
    /* Symmetric two-pixel green bars. Their means are446.5+/-integer distance,
     * keeping the two-sided circular phase check independent of rounding. */
    for(k=0;k<6;++k){int distance=(int)floor((q+k)*104+.5);
        rectangle(out,446-distance,350,448-distance,387,20,180,160);
        rectangle(out,446+distance,350,448+distance,387,20,180,160);
    }
    if(goods){
        /* A21x21 sign yields the first29px-density peak at196,96. */
        rectangle(out,190,90,211,111,200,190,10);
        for(k=0;k<3;++k){int cx=196+36*k;
            rectangle(out,cx-12,136,cx+12,137,56,56,56);
            rectangle(out,cx-11,165,cx+7,166,141,141,141);
        }
    }
    return 1;
}
int ng2_fixture_floor_rgba(uint8_t *out,size_t length,int32_t player_x,
                          int32_t player_y,double q,int32_t goods){
    if(player_x < -16||player_x>16||player_y < -16||player_y>16)return 0;
    return ng2_fixture_floor_pixels_rgba(out,length,36*player_x,36*player_y,q,goods);
}
int ng2_fixture_remote_cell(uint8_t *out,size_t length,int32_t variant){
    if(!out||length!=FS||variant<0||variant>2)return 0;
    if(variant==1)rectangle(out,71,226,106,261,80,80,80);
    if(variant==2)rectangle(out,71,226,106,261,100,40,10);
    return 1;
}
