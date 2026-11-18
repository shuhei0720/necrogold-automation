/* TEST114 procedural current-view pixels, never recorded phone frames.
 * The host advances poses only after actual UI callbacks. A temporal floor
 * texture change is held fixed after the independent current anchor; it does
 * not modify a Scene, Motion result, Ring result, or production mask. */
#include "ngg2_runtime_scene_fixtures.h"
#include "runtime112_upper_shop.h"
#include <math.h>
#include <stdlib.h>

static void current114_pixel(uint8_t *out,int x,int y,int r,int g,int b){
    size_t at;
    if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;
    out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}
int ng2_fixture_current114_rgba(uint8_t *out,size_t length,int32_t stage,double q){
    static const int hud[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    static const int stone[][2]={{-5,-2},{5,1},{-4,3},{4,3}};
    uint8_t world[1089]={0},unknown[1089]={0},*ui;
    int x,y,py=stage<2?1:stage==4?-1:0,column=0,row=0;
    const int left=446,sy=44-36*py;
    size_t i;
    if(!out||length!=896u*414u*4u||stage<0||stage>4||!isfinite(q)||q<0||q>=1)return 0;
    for(y=-5;y<=5;++y)for(x=-6;x<=6;++x)world[(y+16)*33+x+16]=1;
    for(i=0;i<sizeof(stone)/sizeof(*stone);++i)world[(stone[i][1]+16)*33+stone[i][0]+16]=3;
    world[16*33-1+16]=world[16*33+1+16]=2;
    world[16*33+16]=stage==0?7:1;
    if(stage>=3)world[15*33-2+16]=2; /* Newly observed remote actual GOLD. */
    ui=(uint8_t *)malloc(length);if(!ui)return 0;
    if(!ng2_fixture_shop_rgba(ui,length,0,0,q,unknown,sizeof(unknown),16,16,3,0)
        ||!ng2_fixture_shop_rgba(out,length,0,py,q,world,sizeof(world),16,16,3,0)){
        free(ui);return 0;
    }
    if(stage>=3){
        /* World-anchored, deterministic temporal texture. Its RGB range is
         * still FLOOR and is disjoint from merchandise, fixed HUD and GOLD.
         * Equal current captures remain exact; a real UP translates it. */
        for(y=80;y<315;++y)for(x=143;x<663;++x){
            size_t at=((size_t)y*896+(size_t)x)*4;
            if(out[at]>=22&&out[at]<=30&&out[at+1]>=12&&out[at+1]<=20
                &&out[at+2]>=12&&out[at+2]<=20){
                uint32_t seed=(uint32_t)x*UINT32_C(0x7feb352d)
                    ^(uint32_t)(y+36*py)*UINT32_C(0x846ca68b)^UINT32_C(114100);
                int noise;
                seed^=seed>>16;seed*=UINT32_C(0x7feb352d);seed^=seed>>15;
                noise=(int)(seed%13)-6;
                current114_pixel(out,x,y,26+noise,16+noise,16+noise);
            }
        }
    }
    if(stage>=2){
        for(i=0;i<sizeof(ng2_upper112_runs)/sizeof(*ng2_upper112_runs);++i){
            const NG2Upper112Run *run=&ng2_upper112_runs[i];int j;
            for(j=0;j<run->count;++j){
                current114_pixel(out,left-90+column,sy-35+row,run->r,run->g,run->b);
                if(++column==253){column=0;++row;}
            }
        }
    }
    for(i=0;i<sizeof(hud)/sizeof(*hud);++i)
        for(y=hud[i][1];y<hud[i][3];++y)for(x=hud[i][0];x<hud[i][2];++x){
            size_t at=((size_t)y*896+(size_t)x)*4;
            current114_pixel(out,x,y,ui[at],ui[at+1],ui[at+2]);
        }
    for(i=0;i<length;i+=4)if(ui[i]||ui[i+1]||ui[i+2]){
        out[i]=ui[i];out[i+1]=ui[i+1];out[i+2]=ui[i+2];out[i+3]=255;
    }
    free(ui);return 1;
}
