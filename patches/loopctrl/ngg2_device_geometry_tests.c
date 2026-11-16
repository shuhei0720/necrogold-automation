#include "device_geometry/NG2DeviceGeometryProfile.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char **argv){
    const NG2DeviceGeometryProfile *p;
    NG2DeviceInputPoint point={-9,-9,0};
    CHECK(argc==2);
    if(!strcmp(argv[1],"identity")){
        CHECK(ng2_device_geometry_profile("unknown",375,667)==NULL);
        CHECK(ng2_device_geometry_profile("iPhone12,1",375,667)==NULL);
        CHECK(ng2_device_geometry_profile("iPhone10,1",667,375)==NULL);
        CHECK(ng2_device_geometry_profile(NULL,375,667)==NULL);
        CHECK(ng2_device_geometry_profile("iPhone10,1",375,667)->device==8);
        CHECK(ng2_device_geometry_profile("iPhone10,4",375,667)==NULL);
        /* No new model-name fence is added to the existing11 geometry path. */
        CHECK(ng2_device_geometry_profile("unknown",414,896)->legacy_passthrough);
        CHECK(ng2_device_geometry_profile(NULL,414,896)->legacy_passthrough);
    }else if(!strcmp(argv[1],"mixed")){
        /* Root's explicit FRAME-03 boundary: known8 cannot borrow11 shape. */
        CHECK(ng2_device_geometry_profile("iPhone10,1",414,896)==NULL);
    }else if(!strcmp(argv[1],"legacy")){
        static const double expected[7][2]={{207,49},{207,838},{290,838},{124,838},{390,448},{297,448},{144,448}};
        p=ng2_device_geometry_profile("iPhone12,1",414,896);CHECK(p&&p->legacy_passthrough);
        CHECK(p->canonical_width==896&&p->canonical_height==414&&p->source_hud_count==7);
        CHECK(p->world_to_canonical.a==1&&p->world_to_canonical.d==1);
        CHECK(p->world_to_canonical.tx==0&&p->world_to_canonical.ty==0);
        for(int i=0;i<7;++i){CHECK(p->input[i].x==expected[i][0]);CHECK(p->input[i].y==expected[i][1]);}
        CHECK(p->source_hud[5].source_points.x0==429&&p->source_hud[5].source_points.y1==45);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_RESTART,0,&point)&&point.x==144&&point.y==448);
    }else if(!strcmp(argv[1],"observed-facts")){
        p=ng2_device_geometry_profile("iPhone10,1",375,667);CHECK(p);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_MOVE,NG2_UP,&point));
        CHECK(point.x==325&&point.y==187.5);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_MOVE,NG2_RIGHT,&point));
        CHECK(point.x==187.5&&point.y==616);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_RESTART,0,&point));
        CHECK(point.x==130&&point.y==332.5);
        CHECK(p->qualification_gaps==31);
    }else if(!strcmp(argv[1],"spare")){
        p=ng2_device_geometry_profile("iPhone10,1",375,667);CHECK(p&&!p->legacy_passthrough);
        CHECK(p->qualification_gaps==31&&(p->qualification_gaps&NG2_DEVICE_GAP_RAW));
        CHECK(p->world_to_canonical.tx==114.5&&p->world_to_canonical.ty==19.5);
        CHECK(p->source_hud_count==12&&p->ui_map_count==4&&!p->ui_maps[1].full_guard_observed);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_MOVE,NG2_LEFT,&point));
        CHECK(point.x==187.5&&point.y==40);
        CHECK(p->portrait_to_landscape.b*point.y+p->portrait_to_landscape.tx==40);
        CHECK(p->portrait_to_landscape.c*point.x+p->portrait_to_landscape.ty==187.5);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_MOVE,NG2_DOWN,&point)&&point.x==50&&point.y==187.5);
        CHECK(ng2_device_input_candidate(p,NG2_ACTION_PAUSE,0,&point)&&point.x==352.5&&point.y==333.5);
        CHECK(!ng2_device_input_candidate(p,NG2_ACTION_MOVE,NG2_DIR_NONE,&point));
        CHECK(!ng2_device_input_candidate(p,NG2_ACTION_RESUME,0,&point));
    }else return 1;
    puts("PASS pure runtime profile fixture");return 0;
}
