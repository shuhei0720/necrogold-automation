/* TEST117 finite physical shop model. No phone pixels, Scene injection or
 * classifier-result override. The map/pose/HUD exist independently of C. */
#include "ngg2_runtime_scene_fixtures.h"
#include "runtime117_shop_pixels.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static void put117(uint8_t*out,int x,int y,int r,int g,int b){
    size_t at;if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;out[at]=(uint8_t)r;
    out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}
static void cell117(uint8_t*out,int x,int y,int px,int py,int kind){
    int xx,yy,cx=448+36*(x-px),cy=207+36*(y-py);
    for(yy=cy-18;yy<cy+18;++yy)for(xx=cx-18;xx<cx+18;++xx){
        int noise=(int)(((unsigned)(xx+36*px)*17u+(unsigned)(yy+36*py)*13u)%9)-4;
        if(kind==2)put117(out,xx,yy,199+noise,164+noise,63+noise);
        else if(kind==1)put117(out,xx,yy,26+noise,16+noise,16+noise);
    }
}
static void patch117(uint8_t*out,const NG2Shop117Run*runs,size_t count,int left,int top){
    size_t i;int row=0,column=0;
    for(i=0;i<count;++i){int j;for(j=0;j<runs[i].count;++j){
        put117(out,left+column,top+row,runs[i].r,runs[i].g,runs[i].b);
        if(++column==253){column=0;++row;}
    }}
}
int ng2_fixture_shop117_rgba(uint8_t*out,size_t length,int variant,int px,int py,double q){
    uint8_t world[1089]={0},unknown[1089]={0},*ui;int x,y;size_t i;
    if(!out||length!=896u*414u*4u||variant<0||variant>1||px < -3||px>3||py < -3||py>3
        ||!isfinite(q)||q<0||q>=1)return 0;
    /* Walkable observed supports and the right lower-entrance rail. */
    for(y=-3;y<=1;++y)for(x=-8;x<=3;++x)world[(y+16)*33+x+16]=1;
    if(variant==0){
        for(y=-5;y<=-1;++y)world[(y+16)*33+2+16]=2;
        world[16*33-1+16]=world[16*33+1+16]=2;
    }else{
        for(y=-2;y<=2;++y)world[(y+16)*33-7+16]=2;
        world[15*33-1+16]=world[17*33-1+16]=2;
    }
    ui=(uint8_t*)malloc(length);if(!ui)return 0;
    if(!ng2_fixture_shop_rgba(ui,length,0,0,q,unknown,sizeof(unknown),16,16,1,0)
        ||!ng2_fixture_shop_rgba(out,length,px,py,q,world,sizeof(world),16,16,1,0)){
        free(ui);return 0;
    }
    if(variant==0)patch117(out,ng2_shop117_one_face,
        sizeof(ng2_shop117_one_face)/sizeof(*ng2_shop117_one_face),285-36*px,8-36*py);
    else patch117(out,ng2_shop117_mixed_price,
        sizeof(ng2_shop117_mixed_price)/sizeof(*ng2_shop117_mixed_price),177-36*px,118-36*py);
    /* Physical boundary is outside the three-offer strip and must survive
     * composition. It is observed terrain, never an assigned Scene value. */
    for(y=-5;y<=4;++y)for(x=-11;x<=11;++x)
        if(world[(y+16)*33+x+16]==2)cell117(out,x,y,px,py,2);
    /* The mixed-price drawing's old decorative rail crosses the actual
     * doorway. The declared physical doorway and source are observed FLOOR,
     * as in the failure cut; do not fabricate an obstruction at destination. */
    if(variant==1){cell117(out,-1,0,px,py,1);cell117(out,0,0,px,py,1);}
    /* Fixed display HUD; the physical 520ms phase comes from the caller's
     * independent world clock, not a fitted or selected Controller ticket. */
    for(i=0;i<length;i+=4)if(ui[i]||ui[i+1]||ui[i+2]){
        out[i]=ui[i];out[i+1]=ui[i+1];out[i+2]=ui[i+2];out[i+3]=255;
    }
    free(ui);return 1;
}
