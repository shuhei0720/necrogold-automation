#include "NG2DeviceGeometryProfile.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line%d %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
    const NG2DeviceGeometryProfile *spare=ng2_device_geometry_profile("iPhone10,1",375,667);
    const NG2DeviceGeometryProfile *legacy=ng2_device_geometry_profile(NULL,414,896);
    NG2DeviceInputPoint point={-91,-92,0};int began=0,synthesized=0;
    CHECK(spare&&spare->qualification_gaps==31);
    if(ng2_device_dispatch_point(spare,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point)){
        ++began;++synthesized;
    }
    CHECK(began==0&&synthesized==0);
    CHECK(point.x==-91&&point.y==-92);
    CHECK(ng2_device_dispatch_point(legacy,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point));
    CHECK(point.x==207&&point.y==49);
    /* Legacy also preserves future/extra C commands, not a seven-point list. */
    CHECK(ng2_device_dispatch_point(legacy,99,88,-123,2147483647,&point));
    CHECK(point.x==-123&&point.y==2147483647);
    NG2DeviceGeometryProfile qualified=*spare;qualified.qualification_gaps=0;
    CHECK(ng2_device_dispatch_point(&qualified,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point));
    CHECK(point.x==187.5&&point.y==40);
    CHECK(ng2_device_dispatch_point(&qualified,NG2_ACTION_RESUME,0,297,448,&point));
    CHECK(point.x==268.5&&point.y==333.5);
    CHECK(!ng2_device_dispatch_point(&qualified,-1,0,297,448,&point));
    qualified.input[0].measured=0;
    CHECK(!ng2_device_dispatch_point(&qualified,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point));
    qualified.input[0].measured=1;
    qualified.input[0].x=375;
    CHECK(!ng2_device_dispatch_point(&qualified,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point));
    qualified.input[0].x=NAN;
    CHECK(!ng2_device_dispatch_point(&qualified,NG2_ACTION_MOVE,NG2_LEFT,207,49,&point));
    CHECK(!ng2_device_dispatch_point(NULL,4,1,207,49,&point));
    puts("PASS pre-begin geometry gaps, legacy passthrough and Double candidate");return 0;
}
