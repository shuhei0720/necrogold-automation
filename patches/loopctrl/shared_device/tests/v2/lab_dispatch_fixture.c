#include "NG2DeviceGeometryProfile.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line%d %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
    const NG2DeviceGeometryProfile *p=ng2_device_geometry_profile("iPhone10,1",375,667);
    const NG2DeviceGeometryProfile *old=ng2_device_geometry_profile(NULL,414,896);
    NG2DeviceGeometryProfile disabled;NG2DeviceInputPoint out={-91,-92,0};
    CHECK(p&&p->qualification_gaps==31&&p->lab_input_permitted==1);
    CHECK(strstr(p->name,"experimental-lab")!=NULL);
    disabled=*p;disabled.lab_input_permitted=0;
    CHECK(!ng2_device_dispatch_point(&disabled,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    CHECK(out.x==-91&&out.y==-92); /* still no begin/synth candidate */
    /* The only changed admission is the trusted compiled spare policy. */
    CHECK(ng2_device_dispatch_point(p,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    CHECK(out.x==187.5&&out.y==40&&p->qualification_gaps==31);
    for(int direction=NG2_LEFT;direction<=NG2_DOWN;direction++){
        NG2DeviceInputPoint candidate;
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_MOVE,direction,&candidate));
        CHECK(ng2_device_dispatch_point(p,NG2_ACTION_MOVE,direction,0,0,&out));
        CHECK(out.x==candidate.x&&out.y==candidate.y);
    }
    for(int kind=NG2_ACTION_RESUME;kind<=NG2_ACTION_RESTART;kind++){
        NG2DeviceInputPoint candidate;
        CHECK(ng2_device_input_candidate(p,kind,0,&candidate));
        CHECK(ng2_device_dispatch_point(p,kind,0,0,0,&out));
        CHECK(out.x==candidate.x&&out.y==candidate.y);
    }
    CHECK(!ng2_device_geometry_profile("unknown",375,667));
    CHECK(!ng2_device_geometry_profile(NULL,375,667));
    CHECK(!ng2_device_geometry_profile("iPhone10,1",414,896));
    CHECK(!ng2_device_dispatch_point(NULL,NG2_ACTION_MOVE,NG2_LEFT,0,0,&out));
    CHECK(!ng2_device_dispatch_point(p,-1,0,0,0,&out));
    CHECK(!ng2_device_dispatch_point(p,NG2_ACTION_MOVE,99,0,0,&out));
    disabled=*p;disabled.panel_width=414;disabled.panel_height=896;
    CHECK(!ng2_device_dispatch_point(&disabled,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    disabled=*p;disabled.lab_input_permitted=2;
    CHECK(!ng2_device_dispatch_point(&disabled,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    disabled=*p;disabled.input[0].measured=0;
    CHECK(!ng2_device_dispatch_point(&disabled,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    disabled=*p;disabled.input[0].x=NAN;
    CHECK(!ng2_device_dispatch_point(&disabled,NG2_ACTION_MOVE,NG2_LEFT,207,49,&out));
    CHECK(old&&old->qualification_gaps==0&&!old->lab_input_permitted);
    CHECK(ng2_device_dispatch_point(old,99,88,-123,2147483647,&out));
    CHECK(out.x==-123&&out.y==2147483647);
    puts("PASS EXPERIMENTAL trusted8 known7points with gaps31; lab0/unknown/unmeasured reject; legacy unchanged; NOT production acceptance");return 0;
}
