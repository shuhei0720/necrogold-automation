#include "NG2DeviceGeometryProfile.h"
#include <string.h>
#include <math.h>
#if defined(__APPLE__)
#include <sys/sysctl.h>
#endif

static const NG2DeviceHUD hud11[]={
    {"inventory",{0,0,143,140}},{"health",{663,0,896,80}},
    {"minimap",{717,315,896,414}},{"beat_heart",{405,321,485,414}},
    {"footer",{0,380,896,414}},{"pause",{429,0,465,45}},
    {"right_control",{866,45,896,290}}
};
/* NEW8 G1 measured conservative envelopes, not production RAW acceptance.
 * Dynamic instructions/notifications remain per-frame source occlusions. */
static const NG2DeviceHUD hud8[]={
    {"inventory_and_external_indicator",{0,0,86,140}},
    {"health",{436,0,581,60}},{"currency",{594,8,648,78}},
    {"pause",{315,6,351,42}},{"minimap",{576,291,627,336}},
    {"beat_band",{0,312,667,350}},{"beat_heart",{308,292,360,365}},
    {"bottom_labels",{0,350,667,375}},
    {"left_upper_control",{0,148,87,153}},{"right_upper_control",{578,148,667,153}},
    {"left_lower_control",{0,220,87,225}},{"right_lower_control",{578,220,667,225}}
};
static const NG2DeviceUIMap ui8[]={
    {"pause",{315,6,351,42},{429,6,465,42},NG2_DEVICE_UI_BILINEAR,1},
    /* Glyph dimensions are unchanged. Only real observed terminal whitespace
     * is widened; no assumption about its pixel values or per-frame validity. */
    {"footer_body",{565,357,665,375},{752,396,852,414},NG2_DEVICE_UI_BILINEAR,1},
    {"footer_guard",{665,357,667,375},{852,396,856,414},NG2_DEVICE_UI_NEAREST,1},
    {"beat",{0,311,667,350},{114.5,350,781.5,389},NG2_DEVICE_UI_BOX,0},
    {"continue_g1_tuned",{275.72088607594935,93.425,391.45325497287525,120.55678294573643},
        {384,104,512,132},NG2_DEVICE_UI_BICUBIC,1},
    /* One actual original JPEG, EXIF8. Full observed ROI, proper BOX reduction;
     * metadata/phase evidence does not clear the menu or input acceptance gap. */
    {"restart_raw_box",{251.1363728537,231.5552734659,415.3524392753,257.34481368475},
        {357,256,538,284},NG2_DEVICE_UI_BOX,1}
};
static const NG2DeviceGeometryProfile profile11={
    .name="iphone11-legacy-geometry",.device=11,.legacy_passthrough=1,
    .panel_width=414,.panel_height=896,.source_point_width=896,.source_point_height=414,
    .canonical_width=896,.canonical_height=414,
    .world_to_canonical={1,0,0,0,1,0},.portrait_to_landscape={0,1,0,-1,0,414},
    .canonical_source_fov={0,0,896,414},
    .source_hud=hud11,.source_hud_count=sizeof(hud11)/sizeof(hud11[0]),
    .ui_maps=NULL,.ui_map_count=0,
    /* Exact Controller.c reserve values; legacy dispatch remains untouched. */
    .input={{207,49,1},{207,838,1},{290,838,1},{124,838,1},
            {390,448,1},{297,448,1},{144,448,1}},
    /* Zero adds no new exception: existing qualification fences still apply. */
    .qualification_gaps=0,.lab_input_permitted=0
};
static const NG2DeviceGeometryProfile profile8={
    .name="iphone8-experimental-lab-v1",.device=8,.legacy_passthrough=0,
    .panel_width=375,.panel_height=667,.source_point_width=667,.source_point_height=375,
    .canonical_width=896,.canonical_height=414,
    .world_to_canonical={1,0,114.5,0,1,19.5},.portrait_to_landscape={0,1,0,-1,0,375},
    .canonical_source_fov={114.5,19.5,781.5,394.5},
    .source_hud=hud8,.source_hud_count=sizeof(hud8)/sizeof(hud8[0]),
    .ui_maps=ui8,.ui_map_count=sizeof(ui8)/sizeof(ui8[0]),
    /* Hub-only four-direction landmark calibration; no dungeon qualification.
     * Restart point has repeated observed Pause->new1-1/time-reset evidence.
     * Candidate facts never clear any RAW/guard/motion/menu acceptance gap. */
    .input={{187.5,40,1},{187.5,616,1},{325,187.5,1},{50,187.5,1},
            {352.5,333.5,1},{268.5,333.5,1},{130,332.5,1}},
    .qualification_gaps=NG2_DEVICE_GAP_RAW|NG2_DEVICE_GAP_FOUR_DIRECTION_ACK|
        NG2_DEVICE_GAP_UI_GUARD|NG2_DEVICE_GAP_MOTION_SUPPORT|NG2_DEVICE_GAP_MENU,
    /* User-authorized bounded spare-game experiment. This does NOT accept any
     * qualification gap or bypass the common native Controller's input gate. */
    .lab_input_permitted=1
};

const NG2DeviceGeometryProfile *ng2_device_geometry_profile(const char *model,int32_t w,int32_t h){
    /* Known8 contradictions are FRAME-03, not a new requirement for legacy11. */
    if(model&&!strcmp(model,"iPhone10,1"))return w==375&&h==667?&profile8:NULL;
    if(w==414&&h==896)return &profile11;
    return NULL;
}
int ng2_device_input_candidate(const NG2DeviceGeometryProfile *profile,
    int32_t kind,int32_t direction,NG2DeviceInputPoint *out){
    int i=-1;
    if(!profile||!out)return 0;
    if(kind==NG2_ACTION_MOVE&&direction>=NG2_LEFT&&direction<=NG2_DOWN)i=direction-1;
    else if(kind==NG2_ACTION_PAUSE)i=4;
    else if(kind==NG2_ACTION_RESUME)i=5;
    else if(kind==NG2_ACTION_RESTART)i=6;
    if(i<0||!profile->input[i].measured)return 0;
    *out=profile->input[i];return 1;
}
int ng2_device_dispatch_point(const NG2DeviceGeometryProfile *profile,
    int32_t kind,int32_t direction,int32_t command_x,int32_t command_y,
    NG2DeviceInputPoint *out){
    NG2DeviceInputPoint candidate;
    if(!profile||!out)return 0;
    if(profile->legacy_passthrough){
        candidate.x=command_x;candidate.y=command_y;candidate.measured=1;
    }else {
        if(profile->device!=8||profile->panel_width!=375||profile->panel_height!=667
            ||(profile->qualification_gaps!=0&&profile->lab_input_permitted!=1)
            ||!ng2_device_input_candidate(profile,kind,direction,&candidate))return 0;
        if(!isfinite(candidate.x)||!isfinite(candidate.y)||candidate.x<0||candidate.y<0
            ||candidate.x>=profile->panel_width||candidate.y>=profile->panel_height)return 0;
    }
    *out=candidate;return 1;
}
int ng2_device_local_model(char *out,size_t capacity){
    if(!out||capacity<2)return 0;
    out[0]=0;
    #if defined(__APPLE__)
    size_t length=capacity;
    if(sysctlbyname("hw.machine",out,&length,NULL,0)||!length||length>capacity||out[length-1]!=0){
        out[0]=0;return 0;
    }
    return 1;
    #else
    return 0;
    #endif
}

static int support_overlap(NG2DeviceRect a,NG2DeviceRect b){
    return a.x0<b.x1&&b.x0<a.x1&&a.y0<b.y1&&b.y0<a.y1;
}
static int support_rect_valid(NG2DeviceRect r,double width,double height){
    return isfinite(r.x0)&&isfinite(r.y0)&&isfinite(r.x1)&&isfinite(r.y1)
        &&r.x0>=0&&r.y0>=0&&r.x0<r.x1&&r.y0<r.y1&&r.x1<=width&&r.y1<=height;
}
int ng2_device_motion_signature_support(const NG2DeviceGeometryProfile *p,uint8_t *out,size_t n){
    /* These measured8 source domains may cover moving world pixels in some
     * frames. Always excluding them is conservative across copied C anchors. */
    static const NG2DeviceRect possible8_overlays[]={
        {259,151,405,269},{156,8,511,84}
    };
    if(!out||n!=NG2_SIGNATURE_LENGTH)return 0;
    memset(out,0,n);
    if(!p||p->legacy_passthrough||p->canonical_width!=896||p->canonical_height!=414
        ||p->source_point_width<=0||p->source_point_height<=0
        ||p->source_hud_count>32||p->ui_map_count>16
        ||(p->source_hud_count&&!p->source_hud)||(p->ui_map_count&&!p->ui_maps)
        ||p->world_to_canonical.a!=1||p->world_to_canonical.b!=0
        ||p->world_to_canonical.c!=0||p->world_to_canonical.d!=1
        ||!isfinite(p->world_to_canonical.tx)||!isfinite(p->world_to_canonical.ty))return 0;
    if(!support_rect_valid(p->canonical_source_fov,896,414))return 0;
    for(size_t i=0;i<p->source_hud_count;i++)
        if(!support_rect_valid(p->source_hud[i].source_points,p->source_point_width,p->source_point_height))return 0;
    for(size_t i=0;i<p->ui_map_count;i++)
        if(!support_rect_valid(p->ui_maps[i].canonical,896,414))return 0;
    for(int y=0;y<104;y++)for(int x=0;x<224;x++){
        /* A signature sample reads canonical pixel(4x,4y); radius2 reads the
         * inclusive endpoints, hence the half-open +9 bound below. */
        NG2DeviceRect canonical={4*x-8,4*y-8,4*x+9,4*y+9};
        NG2DeviceRect source={canonical.x0-p->world_to_canonical.tx,
            canonical.y0-p->world_to_canonical.ty,canonical.x1-p->world_to_canonical.tx,
            canonical.y1-p->world_to_canonical.ty};
        int observed=canonical.x0>=0&&canonical.y0>=0&&canonical.x1<=896&&canonical.y1<=414
            &&canonical.x0>=p->canonical_source_fov.x0&&canonical.y0>=p->canonical_source_fov.y0
            &&canonical.x1<=p->canonical_source_fov.x1&&canonical.y1<=p->canonical_source_fov.y1
            &&source.x0>=0&&source.y0>=0&&source.x1<=p->source_point_width&&source.y1<=p->source_point_height;
        for(size_t i=0;i<p->source_hud_count&&observed;i++)
            observed=!support_overlap(source,p->source_hud[i].source_points);
        for(size_t i=0;i<p->ui_map_count&&observed;i++)
            observed=!support_overlap(canonical,p->ui_maps[i].canonical);
        if(p->device==8)for(size_t i=0;i<sizeof(possible8_overlays)/sizeof(possible8_overlays[0])&&observed;i++)
            observed=!support_overlap(source,possible8_overlays[i]);
        out[(size_t)y*224+(size_t)x]=(uint8_t)observed;
    }
    return 1;
}

int ng2_device_motion_intersect_world(const uint8_t *world,size_t wn,uint8_t *out,size_t n){
    if(!out||n!=NG2_SIGNATURE_LENGTH)return 0;
    if(!world||wn!=896u*414u){memset(out,0,n);return 0;}
    for(int y=0;y<104;y++)for(int x=0;x<224;x++){
        size_t at=(size_t)y*224+(size_t)x;
        if(!out[at])continue;
        int known=4*x-8>=0&&4*y-8>=0&&4*x+8<896&&4*y+8<414;
        for(int py=4*y-8;py<=4*y+8&&known;py++)
            for(int px=4*x-8;px<=4*x+8;px++)
                if(!world[(size_t)py*896+(size_t)px]){known=0;break;}
        out[at]=(uint8_t)known;
    }
    return 1;
}
