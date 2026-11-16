/* Data for one normal binary's runtime geometry selection and pre-begin gate.
 * Selection alone never grants input authority; NEW8 gaps remain open. */
#ifndef NG2_DEVICE_GEOMETRY_PROFILE_H
#define NG2_DEVICE_GEOMETRY_PROFILE_H
#include <stddef.h>
#include <stdint.h>
#include "NG2Controller.h"

typedef struct { double x0,y0,x1,y1; } NG2DeviceRect;
typedef struct { double a,b,tx,c,d,ty; } NG2DeviceAffine;
typedef struct { double x,y; int32_t measured; } NG2DeviceInputPoint;
typedef struct { const char *name; NG2DeviceRect source_points; } NG2DeviceHUD;
/* Sampling policy for this inactive candidate type, separate from Core ABI. */
enum {
    NG2_DEVICE_UI_NEAREST=0, NG2_DEVICE_UI_BILINEAR=1,
    NG2_DEVICE_UI_BICUBIC=2, NG2_DEVICE_UI_BOX=3
};
typedef struct {
    const char *name;
    NG2DeviceRect source_points,canonical;
    int32_t resampler;
    /* Reference G1 ROI only; per-frame exact support/occlusions are mandatory. */
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
    /* Explicit compiled spare-device EXPERIMENTAL admission, independent of
     * NOT-ACCEPTED qualification metadata. Never supplied by RPC/client data.
     * Resolves only measured points; all Controller/ticket/owner fences remain. */
    int32_t lab_input_permitted;
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
/* Geometry-only pre-begin resolution. Legacy passthrough retains arbitrary
 * command coordinates; NEW8 additionally requires every qualification gap
 * closed unless its explicit compiled EXPERIMENTAL lab policy admits it.
 * Returning a point does not replace owner/ticket/begin authority. */
int ng2_device_dispatch_point(const NG2DeviceGeometryProfile *profile,
    int32_t kind,int32_t direction,int32_t command_x,int32_t command_y,
    NG2DeviceInputPoint *out);
/* Trusted local machine identity; no RPC or settings override. */
int ng2_device_local_model(char *out,size_t capacity);
/* Immutable geometry-only kernel support at signature resolution (224x104).
 * Includes fixed FOV/HUD, UI-copy destinations and conservative known overlay
 * exclusions. Radius2 signature pixels cover blur/gradient dependencies.
 * Does not inspect image colours or qualify an input/phase/motion result. */
int ng2_device_motion_signature_support(const NG2DeviceGeometryProfile *profile,
    uint8_t *signature_support,size_t length);
/* Monotonically intersect a run mask with one committed frame's ACTUAL
 * canonical world coverage. The fixed radius2 raw dependency never widens. */
int ng2_device_motion_intersect_world(const uint8_t *world_observed,size_t world_length,
    uint8_t *signature_support,size_t signature_length);
#endif
