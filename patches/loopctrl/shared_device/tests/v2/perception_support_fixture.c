/* Synthetic world-support regression. No captured images or input authority. */
#include "NG2Core.h"
#include "NG2Templates.h"
#include "NG2WorldSupport.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define PIXELS (896u*414u)
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
static void rectangle(uint8_t *rgba,int x0,int y0,int x1,int y1,int r,int g,int b){
    for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
        size_t at=((size_t)y*896+(size_t)x)*4;
        rgba[at]=(uint8_t)r;rgba[at+1]=(uint8_t)g;rgba[at+2]=(uint8_t)b;
    }
}
static void support_rectangle(uint8_t *support,int x0,int y0,int x1,int y1,uint8_t value){
    for(int y=y0;y<y1;y++)memset(support+(size_t)y*896+(size_t)x0,value,(size_t)(x1-x0));
}
static void actual8_support(uint8_t *support){
    static const double hud[][4]={{0,0,86,140},{436,0,581,60},{594,8,648,78},
        {315,6,351,42},{576,291,627,336},{0,312,667,350},{308,292,360,365},
        {0,350,667,375},{0,148,87,153},{578,148,667,153},{0,220,87,225},{578,220,667,225}};
    for(int y=0;y<414;y++)for(int x=0;x<896;x++){
        double x0=x-114.5,y0=y-19.5,x1=x0+1,y1=y0+1;
        int known=x0>=0&&y0>=0&&x1<=667&&y1<=375;
        for(size_t i=0;i<sizeof(hud)/sizeof(hud[0])&&known;i++)
            if(x0<hud[i][2]&&hud[i][0]<x1&&y0<hud[i][3]&&hud[i][1]<y1)known=0;
        support[(size_t)y*896+(size_t)x]=(uint8_t)known;
    }
}
static void floor_gate(uint8_t *rgba){
    const NG2Template *templates[]={&ng2_template_icon,&ng2_template_footer,&ng2_template_zone_one,&ng2_template_floor_one};
    /* These are the same synthetic gate pixels used by existing public tests,
     * not an adapter that paints templates onto captured images. */
    memset(rgba,0,PIXELS*4);
    for(size_t i=0;i<PIXELS;i++)rgba[4*i+3]=255;
    for(size_t k=0;k<sizeof(templates)/sizeof(templates[0]);k++){
        const NG2Template *t=templates[k];
        for(int y=0;y<t->h;y++)for(int x=0;x<t->w;x++)
            if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1)
                rectangle(rgba,t->x+x,t->y+y,t->x+x+1,t->y+y+1,180,180,180);
    }
}
static int analyze(const uint8_t *rgba,const uint8_t *support,size_t length,int32_t clear_scope,NG2Scene *out){
    NG2WorldSupportScope previous=ng2_world_support_enter(support,length,clear_scope);
    int result=ng2_analyze_rgba(rgba,PIXELS*4,896u*4u,out);
    ng2_world_support_leave(previous);return result;
}
static int analyze_rgba(const uint8_t *ui,const uint8_t *world,size_t world_length,size_t stride,
    const uint8_t *support,size_t support_length,int32_t clear_scope,NG2Scene *out){
    NG2WorldSupportScope previous=ng2_world_support_enter_rgba(world,world_length,stride,support,support_length,clear_scope);
    int result=ng2_analyze_rgba(ui,PIXELS*4,896u*4u,out);
    ng2_world_support_leave(previous);return result;
}
static void black_world(uint8_t *rgba){
    memset(rgba,0,PIXELS*4);for(size_t i=0;i<PIXELS;i++)rgba[i*4+3]=255;
}
static void ui_beat(uint8_t *rgba){
    const int centers[]={122,230,338,554,662,770};
    for(size_t i=0;i<sizeof(centers)/sizeof(centers[0]);i++)
        rectangle(rgba,centers[i]-1,350,centers[i]+2,387,10,140,120);
}
static int gold_tiles(const NG2Scene *scene){
    int count=0;for(int i=0;i<NG2_TILE_COUNT;i++)count+=scene->tiles[i]==NG2_TILE_GOLD;return count;
}
int main(int argc,char **argv){
    uint8_t *rgba=(uint8_t*)malloc(PIXELS*4),*support=(uint8_t*)malloc(PIXELS),*world=(uint8_t*)malloc(PIXELS*4);
    NG2Scene *legacy=(NG2Scene*)malloc(sizeof(*legacy)),*scoped=(NG2Scene*)malloc(sizeof(*scoped)),*restored=(NG2Scene*)malloc(sizeof(*restored));
    NG2WorldSupportScope outer,inner;
    REQUIRE(rgba&&support&&world&&legacy&&scoped&&restored);
    REQUIRE(argc==1||(argc==2&&!strcmp(argv[1],"--rgba-only")));
    REQUIRE(!ng2_world_support_active());
    if(argc==1){
    floor_gate(rgba);actual8_support(support);
    /* Actual8 source649.5..665.5,8.5..59.5: observed world beyond currency648,
     * inside source667, yet fully under the legacy x>=663,y<80 exclusion. */
    rectangle(rgba,764,28,780,79,199,164,63);
    REQUIRE(analyze(rgba,NULL,0,NG2_WORLD_CLEAR_UNKNOWN,legacy)==0&&legacy->state==NG2_FLOOR);
    REQUIRE(legacy->gold_state==NG2_GOLD_CLEAR&&legacy->gold_peak==0);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==0&&scoped->state==NG2_FLOOR);
    printf("partial marker oldGold%d/peak%d scopedGold%d/peak%d\n",legacy->gold_state,legacy->gold_peak,scoped->gold_state,scoped->gold_peak);
    REQUIRE(scoped->gold_state==NG2_GOLD_CANDIDATE&&scoped->gold_peak==151&&gold_tiles(scoped)==0);
    REQUIRE(analyze(rgba,NULL,0,NG2_WORLD_CLEAR_UNKNOWN,restored)==0&&!memcmp(legacy,restored,sizeof(*legacy)));
    /* The same pixels may be copied UI/unknown; they then supply no world
     * positive and their absence does not certify a negative of the gap. */
    support_rectangle(support,764,28,780,79,0);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==0);
    REQUIRE(scoped->gold_state==NG2_GOLD_UNKNOWN&&scoped->gold_peak==0&&!gold_tiles(scoped));
    /* Gold-coloured actual health HUD is excluded from complete local scope. */
    floor_gate(rgba);memset(support,1,PIXELS);
    rectangle(rgba,600,40,640,70,199,164,63);support_rectangle(support,600,40,640,70,0);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD,scoped)==0);
    REQUIRE(scoped->gold_state==NG2_GOLD_CLEAR&&scoped->gold_peak==0&&!gold_tiles(scoped));
    /* Lower-fringe raw gold counts must not revive unknown UI as world. */
    floor_gate(rgba);memset(support,1,PIXELS);
    rectangle(rgba,400,339,425,364,199,164,63);rectangle(rgba,472,339,497,364,199,164,63);
    REQUIRE(analyze(rgba,NULL,0,NG2_WORLD_CLEAR_UNKNOWN,legacy)==0&&gold_tiles(legacy)==2);
    support_rectangle(support,400,339,425,364,0);support_rectangle(support,472,339,497,364,0);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==0);
    REQUIRE(scoped->gold_state==NG2_GOLD_UNKNOWN&&scoped->gold_peak==0&&!gold_tiles(scoped));
    /* Absence is only the explicitly complete observed local scope. */
    floor_gate(rgba);memset(support,1,PIXELS);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==0&&scoped->gold_state==NG2_GOLD_UNKNOWN);
    REQUIRE(analyze(rgba,support,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD,scoped)==0&&scoped->gold_state==NG2_GOLD_CLEAR);
    outer=ng2_world_support_enter(support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN);
    REQUIRE(ng2_world_support_active()&&ng2_world_pixel_observed(100,100));
    REQUIRE(ng2_world_roi_observed(100,100,125,125)&&!ng2_world_roi_observed(-1,100,125,125));
    support[110u*896u+110u]=0;REQUIRE(!ng2_world_roi_observed(100,100,125,125));
    inner=ng2_world_support_enter(NULL,0,NG2_WORLD_CLEAR_UNKNOWN);
    REQUIRE(!ng2_world_support_active());ng2_world_support_leave(inner);
    REQUIRE(ng2_world_support_active()&&!ng2_world_pixel_observed(110,110));
    ng2_world_support_leave(outer);REQUIRE(!ng2_world_support_active());
    outer=ng2_world_support_enter(NULL,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD);
    REQUIRE(ng2_world_support_active()&&!ng2_world_pixel_observed(100,100)&&!ng2_world_roi_observed(100,100,125,125));
    REQUIRE(ng2_world_support_clear_scope()==NG2_WORLD_CLEAR_UNKNOWN);
    ng2_world_support_leave(outer);
    outer=ng2_world_support_enter(support,PIXELS,2);
    REQUIRE(ng2_world_support_active()&&!ng2_world_pixel_observed(100,100));ng2_world_support_leave(outer);
    REQUIRE(analyze(rgba,NULL,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD,scoped)==0&&scoped->gold_state==NG2_GOLD_UNKNOWN);
    REQUIRE(!ng2_world_support_active());
    }
    /* The UI composite can contain coloured UI while the exact same-capture
     * pre-UI world is black. World evidence must not read the UI replacement. */
    floor_gate(rgba);ui_beat(rgba);black_world(world);memset(support,1,PIXELS);
    rectangle(rgba,580,100,640,140,199,164,63);
    REQUIRE(analyze(rgba,NULL,0,NG2_WORLD_CLEAR_UNKNOWN,legacy)==0&&legacy->gold_state==NG2_GOLD_CANDIDATE);
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD,scoped)==0);
    printf("UI-only fakeGold worldGold%d/peak%d\n",scoped->gold_state,scoped->gold_peak);
    REQUIRE(scoped->state==NG2_FLOOR&&scoped->gold_state==NG2_GOLD_CLEAR&&scoped->gold_peak==0&&!gold_tiles(scoped));
    for(size_t i=0;i<NG2_SIGNATURE_LENGTH;i++)REQUIRE(scoped->signature[i]==0);
    for(int i=0;i<48;i++)REQUIRE(scoped->fingerprint[i]==0);
    REQUIRE(scoped->beat_valid==1&&scoped->beat_spacing==108&&scoped->beat_center==446);
    REQUIRE(analyze(rgba,NULL,0,NG2_WORLD_CLEAR_UNKNOWN,restored)==0&&!memcmp(legacy,restored,sizeof(*legacy)));
    /* An observed world fragment survives even though UI overwrote it black. */
    floor_gate(rgba);ui_beat(rgba);black_world(world);actual8_support(support);
    rectangle(world,764,28,780,79,199,164,63);
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD,scoped)==0);
    REQUIRE(scoped->gold_state==NG2_GOLD_CANDIDATE&&scoped->gold_peak==151&&!gold_tiles(scoped));
    REQUIRE(scoped->signature[12*224+192]>0&&scoped->beat_valid==1);
    /* Material sampling likewise uses world pixels, not the fake UI stone. */
    floor_gate(rgba);black_world(world);actual8_support(support);
    rectangle(rgba,508,123,533,148,90,85,80);
    for(int y=123;y<148;y++)for(int x=508;x<533;x++){
        int r=20+5*((x+y)%3);rectangle(world,x,y,x+1,y+1,r,3*r/5,3*r/5);
    }
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==0);
    REQUIRE(scoped->tiles[3*23+13]==NG2_TILE_FLOOR);
    /* Malformed RGBA never falls back to the UI composite. */
    REQUIRE(analyze_rgba(rgba,NULL,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==-1&&scoped->state==NG2_UNKNOWN);
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4-1,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==-1&&scoped->state==NG2_UNKNOWN);
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u-4,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==-1&&scoped->state==NG2_UNKNOWN);
    world[3]=0;
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN,scoped)==-1&&scoped->state==NG2_UNKNOWN);world[3]=255;
    REQUIRE(analyze_rgba(rgba,world,PIXELS*4,896u*4u,support,PIXELS-1,NG2_WORLD_CLEAR_UNKNOWN,scoped)==-1&&scoped->state==NG2_UNKNOWN);
    outer=ng2_world_support_enter(support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN);
    REQUIRE(ng2_world_support_rgba(rgba,PIXELS*4,896u*4u)==rgba);
    inner=ng2_world_support_enter_rgba(world,PIXELS*4,896u*4u,support,PIXELS,NG2_WORLD_CLEAR_UNKNOWN);
    REQUIRE(ng2_world_support_rgba(rgba,PIXELS*4,896u*4u)==world);
    REQUIRE(ng2_world_support_rgba(rgba,(896u*4u+4)*414u,896u*4u+4)==NULL);
    ng2_world_support_leave(inner);
    REQUIRE(ng2_world_support_rgba(rgba,PIXELS*4,896u*4u)==rgba);
    ng2_world_support_leave(outer);REQUIRE(!ng2_world_support_active());
    free(restored);free(scoped);free(legacy);free(support);free(world);free(rgba);
    puts("PASS world support: partialGold151,NULLidentity,HUD/UI/fringe reject,localCLEAR,ROI,malformed,nested restore,preUI-RGBA,world-gray/material,UI-beat; input_authorized=false");
    return 0;
}
