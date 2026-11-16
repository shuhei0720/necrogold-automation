#include "NG2DeviceGeometryProfile.h"
#include <string.h>

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
    .qualification_gaps=0
};
static const NG2DeviceGeometryProfile profile8={
    .name="iphone8-geometry-candidate",.device=8,.legacy_passthrough=0,
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
        NG2_DEVICE_GAP_UI_GUARD|NG2_DEVICE_GAP_MOTION_SUPPORT|NG2_DEVICE_GAP_MENU
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
