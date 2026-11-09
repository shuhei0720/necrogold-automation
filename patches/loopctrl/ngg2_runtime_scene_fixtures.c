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

int ng2_fixture_motion_reference_rgba(uint8_t *out,size_t length,int32_t world_y,
                                       double q,int32_t goods,int32_t variant){
    uint32_t state=0;int sx,sy,c;
    if(variant<0||variant>1||(variant==1&&(world_y!=-36||goods!=0)))return 0;
    if(!ng2_fixture_floor_pixels_rgba(out,length,0,world_y,q,goods))return 0;
    if(!variant)return 1;
    for(sy=20;sy<70;++sy)for(sx=40;sx<179;++sx){
        int delta;size_t at;
        if(sx>=90&&sx<139&&sy>=36)continue;
        state=UINT32_C(1664525)*state+UINT32_C(1013904223);
        delta=(int)((state>>8)%13)-6;at=((size_t)(4*sy)*FW+(size_t)(4*sx))*4;
        for(c=0;c<3;++c){int value=(int)out[at+(size_t)c]+delta;
            out[at+(size_t)c]=(uint8_t)(value<7?7:value>255?255:value);}
    }
    return ng2_fixture_remote_cell(out,length,1);
}

int ng2_fixture_shop_rgba(uint8_t *out,size_t length,int32_t player_x,
                          int32_t player_y,double q,const uint8_t *tiles,
                          size_t tile_count,int32_t gate_x,int32_t gate_y,
                          int32_t direction,int32_t goods_variant){
    static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
    int x,y,k,open,inside,show,full,cx,cy,sign_y;
    size_t i;
    if(!out||length!=FS||!tiles||tile_count!=1089||player_x < -16||player_x>16
       ||player_y < -16||player_y>16||gate_x < -16||gate_x>16||gate_y < -16||gate_y>16
       ||!isfinite(q)||q<0||q>=1||direction<1||direction>4||goods_variant<0||goods_variant>2)return 0;
    for(i=0;i<tile_count;++i)
        if(tiles[i]!=0&&tiles[i]!=1&&tiles[i]!=2&&tiles[i]!=3&&tiles[i]!=4&&tiles[i]!=7)return 0;
    /* Texture is anchored to absolute world pixels. Camera translation does
     * not regenerate it, and unknown/out-of-map terrain remains unknown. */
    for(y=0;y<FH;++y)for(x=0;x<FW;++x){
        int wx=x+36*player_x,wy=y+36*player_y;
        int tx=floor_div(wx-448+18,36),ty=floor_div(wy-207+18,36);
        int material=tx>=-16&&tx<=16&&ty>=-16&&ty<=16?tiles[(ty+16)*33+tx+16]:0;
        uint32_t hash=(uint32_t)wx*UINT32_C(0x9e3779b9)^(uint32_t)wy*UINT32_C(0x85ebca6b);
        int noise,r=0,g=0,b=0;
        hash^=hash>>16;hash*=UINT32_C(0x7feb352d);hash^=hash>>15;
        noise=(int)(hash%9)-4;
        if(material==1){r=26;g=16;b=16;}
        else if(material==2){r=199;g=164;b=63;}
        else if(material==3){r=80;g=80;b=80;}
        else if(material==4){r=100;g=50;b=10;}
        else if(material==7){r=63;g=19;b=0;}
        if(!material)noise=0;
        pixel(out,x,y,r+noise,g+noise,b+noise);
    }
    template_mask(out,&ng2_template_icon);template_mask(out,&ng2_template_footer);
    template_mask(out,&ng2_template_zone_one);template_mask(out,&ng2_template_floor_one);
    for(k=0;k<6;++k){int distance=(int)floor((q+k)*104+.5);
        rectangle(out,446-distance,350,448-distance,387,20,180,160);
        rectangle(out,446+distance,350,448+distance,387,20,180,160);
    }
    open=tiles[(gate_y+16)*33+gate_x+16]==1;
    inside=(player_x-gate_x)*dx[direction]+(player_y-gate_y)*dy[direction]>=0;
    show=goods_variant==2||(open&&(inside||goods_variant==1));
    full=goods_variant!=2&&open&&inside;
    if(show){
        int product_x=goods_variant==2?0:gate_x+2*dx[direction];
        int product_y=goods_variant==2?-2:gate_y+2*dy[direction];
        cx=448+36*(product_x-player_x);cy=207+36*(product_y-player_y);
        sign_y=cy-48;
        /* The first density peak is at the left slot's x and sign_y. All
         * three slots stay horizontal in world coordinates for every gate. */
        rectangle(out,cx-42,sign_y-6,cx-21,sign_y+15,200,190,10);
        if(full)for(k=-1;k<=1;++k){int slot_x=cx+36*k;
            rectangle(out,slot_x-12,cy-8,slot_x+12,cy-7,56,56,56);
            rectangle(out,slot_x-11,cy+21,slot_x+7,cy+22,141,141,141);
        }
    }
    return 1;
}
