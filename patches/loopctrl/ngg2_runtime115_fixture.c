/* TEST115 procedural renderer only. No phone pixels, Scene overrides or
 * classifier outcomes are embedded. Poses advance only after real callbacks. */
#include "ngg2_runtime_scene_fixtures.h"
#include "runtime112_upper_shop.h"
#include <math.h>
#include <stdlib.h>

static void fixture115_box(uint8_t *out,int left,int top,int right,int bottom,int r,int g,int b){
    int x,y;
    for(y=top;y<bottom;++y)for(x=left;x<right;++x){
        size_t at;
        if(x<0||x>=896||y<0||y>=414)continue;
        at=((size_t)y*896u+(size_t)x)*4u;
        out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
    }
}
int ng2_fixture_passage115_rgba(uint8_t *out,size_t length,int32_t stage,double q){
    uint8_t world[1089]={0};int x,y,py;
    if(!out||length!=896u*414u*4u||stage<0||stage>3||!isfinite(q)||q<0||q>=1)return 0;
    py=stage==0?0:stage==3?-2:-1;
    for(y=-2;y<=2;++y)for(x=-2;x<=2;++x)world[(y+16)*33+x+16]=1;
    for(x=-3;x<=3;++x){
        world[13*33+x+16]=world[19*33+x+16]=4;
        world[(x+16)*33+13]=world[(x+16)*33+19]=4;
    }
    world[13*33+16]=world[12*33+16]=1;
    if(stage>=2)world[18*33+13]=3;
    return ng2_fixture_shop_rgba(out,length,0,py,q,world,sizeof(world),16,16,3,0);
}
int ng2_fixture_partial115_rgba(uint8_t *out,size_t length,int32_t stage,double q){
    uint8_t world[1089]={0};int x,y,py;
    if(!out||length!=896u*414u*4u||stage<0||stage>5||!isfinite(q)||q<0||q>=1)return 0;
    py=stage==0?1:stage>=4?-1:0;
    for(y=-5;y<=5;++y)for(x=-6;x<=6;++x)world[(y+16)*33+x+16]=1;
    world[13*33+17]=world[14*33+17]=world[15*33+17]=world[15*33+15]=2;
    world[14*33+11]=world[17*33+11]=3;
    world[15*33+16]=stage<2?7:1;
    if(stage>=3)world[11*33+17]=2;
    if(!ng2_fixture_shop_rgba(out,length,0,py,q,world,sizeof(world),16,16,3,0))return 0;
    if(stage>=2&&stage<5){
        /* At the top edge the normal merchandise producer projects two
         * rows. A one-pixel sign refinement removes only the upper alias. */
        int top=(stage==2?0:1)-36*py;
        fixture115_box(out,397,top,434,top+21,200,190,10);
    }
    if(stage==5){
        /* Optional synthetic future: the same post-UP pose reveals a
         * complete public three-SKU drawing inside the former projection.
         * This is a normal-producer oracle, not a recorded game response.
         * Keep the actual world rail and fixed PAUSE HUD unchanged. */
        uint8_t pause[36*45*4];size_t i;int column=0,row=0;
        for(y=0;y<45;++y)for(x=429;x<465;++x){
            size_t from=((size_t)y*896u+(size_t)x)*4u,to=((size_t)y*36u+(size_t)(x-429))*4u;
            for(int c=0;c<4;++c)pause[to+(size_t)c]=out[from+(size_t)c];
        }
        for(i=0;i<sizeof(ng2_upper112_runs)/sizeof(*ng2_upper112_runs);++i){
            const NG2Upper112Run *run=&ng2_upper112_runs[i];int j;
            for(j=0;j<run->count;++j){
                if(column<216)fixture115_box(out,247+column,15+row,248+column,16+row,run->r,run->g,run->b);
                if(++column==253){column=0;++row;}
            }
        }
        for(y=0;y<45;++y)for(x=429;x<465;++x){
            size_t to=((size_t)y*896u+(size_t)x)*4u,from=((size_t)y*36u+(size_t)(x-429))*4u;
            for(int c=0;c<4;++c)out[to+(size_t)c]=pause[from+(size_t)c];
        }
    }
    return 1;
}
