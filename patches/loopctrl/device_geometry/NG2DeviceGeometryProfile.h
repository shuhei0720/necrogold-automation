/* Pure data for one normal binary's runtime geometry selection.
 * Not wired into Runtime yet. Selection never grants input authority. */
#ifndef NG2_DEVICE_GEOMETRY_PROFILE_H
#define NG2_DEVICE_GEOMETRY_PROFILE_H
#include <stddef.h>
#include <stdint.h>
#include "../ngg2/NG2Controller.h"

typedef struct { double x0,y0,x1,y1; } NG2DeviceRect;
typedef struct { double a,b,tx,c,d,ty; } NG2DeviceAffine;
typedef struct { double x,y; int32_t measured; } NG2DeviceInputPoint;
typedef struct { const char *name; NG2DeviceRect source_points; } NG2DeviceHUD;
typedef struct {
    const char *name;
    NG2DeviceRect source_points,canonical;
    /* Reference G1 ROI only; per-frame occlusions/support remain mandatory. */
    int32_t full_guard_observed;
} NG2DeviceUIMap;
enum {
    NG2_DEVICE_GAP_RAW=1u, NG2_DEVICE_GAP_FOUR_DIRECTION_ACK=2u,
    NG2_DEVICE_GAP_UI_GUARD=4u, NG2_DEVICE_GAP_MOTION_SUPPORT=8u,
    NG2_DEVICE_GAP_MENU=16u
};
typedef struct {
    /* Geometry profile is orthogonal to existing run cycle/evidence profile. */
    const char *name;
    int32_t device,legacy_passthrough;
    int32_t panel_width,panel_height,source_point_width,source_point_height;
    int32_t canonical_width,canonical_height;
    NG2DeviceAffine world_to_canonical,portrait_to_landscape;
    NG2DeviceRect canonical_source_fov;
    const NG2DeviceHUD *source_hud;
    size_t source_hud_count;
    const NG2DeviceUIMap *ui_maps;
    size_t ui_map_count;
    /* LEFT,RIGHT,UP,DOWN,PAUSE,RESUME,RESTART. Unknown point != (0,0). */
    NG2DeviceInputPoint input[7];
    uint32_t qualification_gaps;
} NG2DeviceGeometryProfile;

/* model comes from trusted local hardware identity, never RPC selection.
 * NEW8 requires the observed iPhone10,1+375x667 pair; known8+legacy dimensions
 * are mixed geometry and reject. Other legacy414x896 keeps its existing
 * geometry condition without adding a hardware-name requirement.
 * Both profiles live in one binary; no model-specific build flag exists. */
const NG2DeviceGeometryProfile *ng2_device_geometry_profile(
    const char *model,int32_t panel_width,int32_t panel_height);
/* A measured candidate point only. Caller retains all existing owner/prefix,
 * qualification/ticket/begin/ACK fences. This function authorizes nothing. */
int ng2_device_input_candidate(const NG2DeviceGeometryProfile *profile,
    int32_t kind,int32_t direction,NG2DeviceInputPoint *out);
#endif
