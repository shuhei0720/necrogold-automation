#include "NG2DeviceRaster.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
    const size_t pixels=896u*414u,source_pixels=1334u*750u;
    const NG2DeviceGeometryProfile *base=ng2_device_geometry_profile("iPhone10,1",375,667);
    NG2DeviceGeometryProfile p;
    /* This synthetic map changes only geometry data: a fully observed real
     * source ROI is copied into an independently fully observed world cell. */
    const NG2DeviceUIMap map={"test_floor_ui",{450,100,475,125},{580,120,605,145},NG2_DEVICE_UI_BOX,1};
    NG2ProfileRasterValidity validity;
    uint8_t *source=(uint8_t*)malloc(source_pixels*4),*rgba=(uint8_t*)malloc(pixels*4),*observed=(uint8_t*)malloc(pixels);
    if(!base||!source||!rgba||!observed)return 2;
    p=*base;p.ui_maps=&map;p.ui_map_count=1;
    for(size_t i=0;i<source_pixels;i++){source[i*4]=source[i*4+1]=source[i*4+2]=50;source[i*4+3]=255;}
    if(ng2_profile_raster8(source,source_pixels*4,1334,750,&p,NULL,0,NG2_PROFILE_RASTER_FLOOR,rgba,pixels*4,observed,pixels,&validity))return 2;
    printf("ui_observed=%u world_observed_at_copy=%u cell_observed=%u\n",validity.ui_observed[0],observed[135u*896u+592u],validity.cell_observed[3*23+15]);
    REQUIRE(validity.ui_observed[0]==1);
    REQUIRE(observed[135u*896u+592u]==0);
    REQUIRE(validity.cell_observed[3*23+15]==0);
    REQUIRE(validity.clear_scope==NG2_CLEAR_SCOPE_UNKNOWN);
    uint8_t *original_world=malloc(pixels);REQUIRE(original_world);
    p=*base;p.ui_map_count=0;
    REQUIRE(!ng2_profile_raster8(source,source_pixels*4,1334,750,&p,NULL,0,NG2_PROFILE_RASTER_FLOOR,rgba,pixels*4,original_world,pixels,&validity));
    p=*base;
    REQUIRE(!ng2_profile_raster8(source,source_pixels*4,1334,750,&p,NULL,0,NG2_PROFILE_RASTER_FLOOR,rgba,pixels*4,observed,pixels,&validity));
    size_t lost=0;
    for(size_t i=0;i<pixels;i++)if(original_world[i]&&!observed[i])lost++;
    printf("actual_profile_UI_world_pixels_lost=%zu clear_scope=%d\n",lost,validity.clear_scope);
    REQUIRE(lost>0&&validity.clear_scope==NG2_CLEAR_SCOPE_UNKNOWN);
    free(original_world);free(observed);free(rgba);free(source);
    puts("PASS UI observed independently; overwritten world/cell UNKNOWN and incomplete CLEAR denied; input_authorized=false");return 0;
}
