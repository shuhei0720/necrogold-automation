/* Procedural TEST112 upper shop. Each stage supplies pixels to unchanged
 * Perception/Motion/Ring, never an injected Scene or forced classifier result. */
#include "ngg2_runtime_scene_fixtures.h"
#include "runtime112_upper_shop.h"
#include <math.h>

static void upper112_pixel(uint8_t *out,int x,int y,int r,int g,int b){
    size_t at;
    if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;
    out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}
static void upper112_rect(uint8_t *out,int left,int top,int right,int bottom,int r,int g,int b){
    int x,y;for(y=top;y<bottom;++y)for(x=left;x<right;++x)upper112_pixel(out,x,y,r,g,b);
}
int ng2_fixture_upper112_rgba(uint8_t *out,size_t length,int32_t stage,int32_t mirror,double q){
    static const int positions[7][2]={{1,0},{0,0},{0,0},{-1,0},{-2,0},{-2,1},{-2,2}};
    static const int cells[][3]={{-1,0,7},{-1,-1,2},{-1,1,2},
        {-7,-2,2},{-7,-1,2},{-7,0,2},{-7,1,2},{-6,-2,2},{-5,-2,2},{-4,-2,2},
        {-2,0,4},{0,1,4},{-8,-3,3},{5,2,3},{8,3,3},{1,0,1}};
    uint8_t world[1089]={0};int x,y,px,py,sign=mirror?-1:1,k,left,sy,column=0,row=0;
    size_t i;
    if(!out||length!=896u*414u*4u||stage<0||stage>6||mirror<0||mirror>1
        ||!isfinite(q)||q<0||q>=1)return 0;
    px=sign*positions[stage][0];py=positions[stage][1];
    for(y=-1;y<=4;++y)for(x=-6;x<=0;++x)world[(y+16)*33+sign*x+16]=1;
    for(i=0;i<sizeof(cells)/sizeof(*cells);++i)
        world[(cells[i][1]+16)*33+sign*cells[i][0]+16]=(uint8_t)cells[i][2];
    if(stage>=2)world[16*33-sign+16]=1; /* Actually opened door; no displacement. */
    if(stage>=3)world[16*33-2*sign+16]=1; /* Later observed positive next floor. */
    /* The unused far gate suppresses the old factory's automatic shop layer. */
    if(!ng2_fixture_shop_rgba(out,length,px,py,q,world,sizeof(world),16,16,mirror?2:1,0))return 0;
    if(stage<2)return 1;
    left=(mirror?557:267)-36*px;sy=267-36*py;
    for(i=0;i<sizeof(ng2_upper112_runs)/sizeof(*ng2_upper112_runs);++i){
        const NG2Upper112Run *run=&ng2_upper112_runs[i];int j;
        for(j=0;j<run->count;++j){
            upper112_pixel(out,left-90+column,sy-35+row,run->r,run->g,run->b);
            if(++column==253){column=0;++row;}
        }
    }
    if(stage<5)for(k=0;k<3;++k)
        upper112_rect(out,left+36*k-12,sy+69,left+36*k+13,sy+90,27,17,15);
    /* HUD is a screen overlay, not moving world terrain. Restore its existing
     * beat bars after the lower room patch at precisely the same q. */
    for(k=0;k<6;++k){int distance=(int)floor((q+k)*104+.5);
        upper112_rect(out,446-distance,350,448-distance,387,20,180,160);
        upper112_rect(out,446+distance,350,448+distance,387,20,180,160);
    }
    return 1;
}
