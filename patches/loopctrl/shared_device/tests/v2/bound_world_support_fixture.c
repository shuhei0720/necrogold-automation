/* Synthetic plane-binding proof; no captured pixels are edited. */
#define main ng2_mask_support_fixture_main
#include "perception_support_fixture.c"
#undef main
#include "NG2DeviceRaster.h"
static void validity(NG2ProfileRasterValidity *v,const uint8_t *coverage){
    memset(v,0,sizeof(*v));v->version=1;v->size=sizeof(*v);v->qualification_gaps=31;
    v->clear_scope=NG2_CLEAR_SCOPE_OBSERVED_FOV_MINUS_HUD;
    for(int j=-5;j<5;j++)for(int i=-11;i<12;i++){
        int known=1,cx=448+36*i,cy=207+36*j;
        for(int y=cy-18;y<cy+18&&known;y++)for(int x=cx-18;x<cx+18;x++)
            if(x<0||y<0||x>=896||y>=414||!coverage[y*896+x]){known=0;break;}
        v->cell_observed[(j+5)*23+i+11]=(uint8_t)known;
    }
}
int main(void){
    uint8_t *ui=malloc(PIXELS*4),*world=malloc(PIXELS*4),*coverage=malloc(PIXELS);
    NG2Scene *scene=malloc(sizeof(*scene)),*direct=malloc(sizeof(*direct));
    NG2ProfileRasterValidity fv,wv,pv,chosen;int32_t selected;
    REQUIRE(ui&&world&&coverage&&scene&&direct);
    floor_gate(ui);memset(world,0,PIXELS*4);for(size_t i=0;i<PIXELS;i++)world[4*i+3]=255;
    actual8_support(coverage);validity(&wv,coverage);fv=wv;pv=wv;fv.ui_state_observed=1;
    /* UI-only gold never supplies world evidence. Complete real world is dark. */
    rectangle(ui,250,150,300,210,199,164,63);
    REQUIRE(ng2_profile_raster_analyze_world(ui,&fv,world,coverage,&wv,ui,&pv,scene,&selected,&chosen)==0);
    REQUIRE(scene->state==NG2_FLOOR&&scene->gold_state==NG2_GOLD_CLEAR&&scene->gold_peak==0);
    REQUIRE(chosen.ui_state_observed==1&&chosen.clear_scope==1&&selected==NG2_PROFILE_RASTER_FLOOR);
    /* Real partial gold survives an independent UI copy over those pixels. */
    rectangle(world,764,28,780,79,199,164,63);
    REQUIRE(ng2_analyze_rgba(world,PIXELS*4,896u*4u,direct)==0&&direct->state==NG2_UNKNOWN);
    REQUIRE(ng2_profile_raster_analyze_world(ui,&fv,world,coverage,&wv,ui,&pv,scene,&selected,&chosen)==0);
    REQUIRE(scene->state==NG2_FLOOR&&scene->gold_state==NG2_GOLD_CANDIDATE&&scene->gold_peak==151&&!gold_tiles(scene));
    /* Motion and published Ring/pixel proof must consume this SAME world RGBA,
     * not the self-classifying UI raster. Check every produced signature byte. */
    for(int y=0;y<414;y+=4)for(int x=0;x<896;x+=4){
        const uint8_t *p=world+((size_t)y*896+(size_t)x)*4;
        uint8_t gray=(uint8_t)((19595u*p[0]+38470u*p[1]+7471u*p[2]+32768u)>>16);
        REQUIRE(scene->signature[(y/4)*224+x/4]==gray);
    }
    wv.clear_scope=NG2_CLEAR_SCOPE_UNKNOWN;rectangle(world,764,28,780,79,0,0,0);
    REQUIRE(ng2_profile_raster_analyze_world(ui,&fv,world,coverage,&wv,ui,&pv,scene,&selected,&chosen)==0);
    REQUIRE(scene->gold_state==NG2_GOLD_UNKNOWN);
    world[3]=0;
    REQUIRE(ng2_profile_raster_analyze_world(ui,&fv,world,coverage,&wv,ui,&pv,scene,&selected,&chosen)==-1);
    free(direct);free(scene);free(coverage);free(world);free(ui);
    puts("PASS same-capture UI state/world proof split: UI-only gold0,real partial151,all signature bytes=world,unknown/alpha reject; input_authorized=false");return 0;
}
