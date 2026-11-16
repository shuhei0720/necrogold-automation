#include "NG2DeviceRaster.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define REQUIRE(c) do{if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 1;}}while(0)
int main(void){
    const size_t pixels=896u*414u,n=1334u*750u*4u;
    uint8_t *s=calloc(n,1),*r=malloc(pixels*4),*observed=malloc(pixels);
    NG2ProfileRasterValidity v;
    const NG2DeviceGeometryProfile *p=ng2_device_geometry_profile("iPhone10,1",375,667);
    REQUIRE(s&&r&&observed&&p);
    for(size_t i=3;i<n;i+=4)s[i]=255;
    /* Nonblack actual margin: every source row/column remains identifiable. */
    for(int y=714;y<750;y++)for(int x=1330;x<1334;x++){
        size_t at=((size_t)y*1334+(size_t)x)*4;
        s[at]=(uint8_t)(30*(x-1329));s[at+1]=(uint8_t)(y-700);s[at+2]=200;
    }
    REQUIRE(ng2_profile_raster8(s,n,1334,750,p,NULL,0,NG2_PROFILE_RASTER_FLOOR,
        r,pixels*4,observed,pixels,&v)==0);
    for(int y=0;y<18;y++)for(int x=0;x<4;x++){
        size_t a=((size_t)(396+y)*896+852+(size_t)x)*4;
        size_t b=((size_t)(715+2*y)*1334+1330+(size_t)x)*4;
        REQUIRE(memcmp(r+a,s+b,4)==0);
    }
    REQUIRE(v.ui_observed[1]&&v.ui_observed[2]&&v.ui_state_observed);
    REQUIRE(v.qualification_gaps==31&&!v.motion_qualified&&!v.goods_coverage_qualified&&!v.input_authorized);
    REQUIRE(!v.cell_observed[0]&&!observed[0]);
    REQUIRE(!v.cell_observed[(-5+5)*23+2+11]);
    REQUIRE(!v.cell_observed[(-4+5)*23+5+11]);
    NG2DeviceRect hidden={665,357,667,375};
    REQUIRE(ng2_profile_raster8(s,n,1334,750,p,&hidden,1,NG2_PROFILE_RASTER_FLOOR,
        r,pixels*4,observed,pixels,&v)==0);
    REQUIRE(!v.ui_observed[2]&&!v.ui_state_observed);
    REQUIRE(ng2_profile_raster8(s,n,750,1334,p,NULL,0,NG2_PROFILE_RASTER_FLOOR,
        r,pixels*4,observed,pixels,&v)==-1);
    REQUIRE(ng2_profile_raster8(s,n,1334,750,ng2_device_geometry_profile(NULL,414,896),NULL,0,
        NG2_PROFILE_RASTER_FLOOR,r,pixels*4,observed,pixels,&v)==-1);
    NG2Scene goods;NG2DeviceRect required;
    memset(&goods,0,sizeof(goods));goods.state=NG2_FLOOR;goods.goods=NG2_GOODS_VISIBLE;
    goods.tiles[(1+5)*23-2+11]=NG2_TILE_ITEM;
    goods.tiles[(1+5)*23-1+11]=NG2_TILE_ITEM;
    goods.tiles[(1+5)*23+0+11]=NG2_TILE_ITEM;
    memset(observed,1,pixels);
    REQUIRE(ng2_profile_goods_support(&goods,observed,pixels,&required)==1);
    REQUIRE(required.x0==340&&required.x1==484&&required.y0==157&&required.y1==302);
    observed[200u*896u+400u]=0;
    REQUIRE(ng2_profile_goods_support(&goods,observed,pixels,&required)==0);
    NG2DeviceGeometryProfile impulse_profile=*p;
    NG2DeviceUIMap impulse_map={"continue_g1_tuned",{1.125,.5,1.625,1},{0,0,1,1},NG2_DEVICE_UI_BICUBIC,1};
    impulse_profile.ui_maps=&impulse_map;impulse_profile.ui_map_count=1;
    s[(1334u+2u)*4u]=255;
    REQUIRE(ng2_profile_raster8(s,n,1334,750,&impulse_profile,NULL,0,NG2_PROFILE_RASTER_PAUSE,
        r,pixels*4,observed,pixels,&v)==0);
    /* Independently measured Pillow F impulse: x2 at phase .25 has .890625,
     * not the Catmull-Rom .8671875. RGB conversion truncates255*.890625. */
    REQUIRE(r[0]==227);
    impulse_map=(NG2DeviceUIMap){"continue_g1_tuned",{.135,0,3.36,.5},{0,0,3,1},NG2_DEVICE_UI_BOX,1};
    for(int x=0;x<8;x++)s[(size_t)x*4]=(uint8_t)x;
    REQUIRE(ng2_profile_raster8(s,n,1334,750,&impulse_profile,NULL,0,NG2_PROFILE_RASTER_PAUSE,
        r,pixels*4,observed,pixels,&v)==0);
    /* Proper BOX reduction of source [.27,6.72] selects source centers;
     * last output averages indices5/6 and rounds5.5 to6, not area-weight5. */
    REQUIRE(r[0]==1&&r[4]==3&&r[8]==6);
    for(uint32_t gaps=0;gaps<=4;gaps+=4){
        impulse_profile.qualification_gaps=gaps;
        REQUIRE(ng2_profile_raster8(s,n,1334,750,&impulse_profile,NULL,0,NG2_PROFILE_RASTER_PAUSE,
            r,pixels*4,observed,pixels,&v)==0);
        REQUIRE(v.qualification_gaps==gaps&&!v.input_authorized);
    }
    NG2Scene passage;NG2Decision step;
    memset(&passage,0,sizeof(passage));passage.abi_version=1;passage.struct_size=sizeof(passage);
    passage.state=NG2_FLOOR;passage.gold_state=NG2_GOLD_CLEAR;
    memset(&v,0,sizeof(v));v.version=1;v.size=sizeof(v);v.clear_scope=NG2_CLEAR_SCOPE_OBSERVED_FOV_MINUS_HUD;
    for(int y=-4;y<=0;y++){
        int at=(y+5)*23+11;passage.tiles[at]=NG2_TILE_FLOOR;v.cell_observed[at]=1;
    }
    for(int x=-1;x<=1;x+=2){int at=(-3+5)*23+x+11;passage.tiles[at]=NG2_TILE_DIRT;v.cell_observed[at]=1;}
    memset(observed,1,pixels);
    ng2_profile_restrict_scene(&passage,&v,observed);
    REQUIRE(passage.gold_state==NG2_GOLD_CLEAR);
    REQUIRE(ng2_passage_candidates(&passage)&(1u<<2));
    REQUIRE(ng2_choose_passage(&passage,0,0,0,-3,&step)>0&&step.direction==NG2_UP);
    for(int i=0;i<NG2_TILE_COUNT;i++)REQUIRE(passage.protected_cells[i]==0);
    passage.protected_cells[0]=1;ng2_profile_restrict_scene(&passage,&v,observed);
    REQUIRE(passage.protected_cells[0]==1);
    v.clear_scope=NG2_CLEAR_SCOPE_UNKNOWN;ng2_profile_restrict_scene(&passage,&v,observed);
    REQUIRE(passage.gold_state==NG2_GOLD_UNKNOWN);
    free(s);free(r);free(observed);puts("PASS real normal8 raster sampling/coverage/input fences");return 0;
}
