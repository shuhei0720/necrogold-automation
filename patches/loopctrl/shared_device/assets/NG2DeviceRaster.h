#ifndef NG2_PROFILE_RASTER_H
#define NG2_PROFILE_RASTER_H
#include "NG2DeviceGeometryProfile.h"
enum { NG2_PROFILE_RASTER_FLOOR=1, NG2_PROFILE_RASTER_PAUSE=2, NG2_PROFILE_RASTER_WORLD=3 };
enum { NG2_CLEAR_SCOPE_UNKNOWN=0, NG2_CLEAR_SCOPE_OBSERVED_FOV_MINUS_HUD=1 };
typedef struct {
    uint32_t version, size, qualification_gaps;
    uint8_t cell_observed[NG2_TILE_COUNT], ui_observed[16];
    int32_t ui_state_observed, restart_ui_observed;
    /* Same immutable profile FOV, minus source/native HUD. Never world-none.
     * Declared dynamic occlusions deny CLEAR until a new unobscured frame. */
    int32_t clear_scope;
    /* Geometry diagnostics cannot qualify any of these contracts. */
    int32_t motion_qualified, goods_coverage_qualified, input_authorized;
} NG2ProfileRasterValidity;
/* Already-oriented opaque sRGB RGBA8; no JPEG/EXIF inference occurs here.
 * Copies observed pixels only. Black exclusion has world_observed=0.
 * Candidate8 only; legacy11 must retain its original decoder/analysis path. */
int ng2_profile_raster8(const uint8_t *source,size_t length,int32_t width,int32_t height,
    const NG2DeviceGeometryProfile *profile,const NG2DeviceRect *occlusions,size_t count,
    int32_t view,uint8_t *rgba,size_t rgba_length,uint8_t *world_observed,size_t observed_length,
    NG2ProfileRasterValidity *validity);
/* Public perception only, preserving its PAUSE-before-FLOOR priority.
 * selected_view/scene/validity refer to the same immutable chosen raster. */
int ng2_profile_raster_analyze(const uint8_t *floor_rgba,const uint8_t *floor_observed,const NG2ProfileRasterValidity *floor_validity,
    const uint8_t *pause_rgba,const NG2ProfileRasterValidity *pause_validity,
    NG2Scene *scene,int32_t *selected_view,NG2ProfileRasterValidity *selected_validity);
/* Additive same-capture plane binding. UI state/beat use floor_ui; FLOOR
 * world classification and returned proofs use untouched world_rgba only.
 * Existing facade signature remains available for mask-only diagnostics. */
int ng2_profile_raster_analyze_world(const uint8_t *floor_ui,const NG2ProfileRasterValidity *floor_ui_validity,
    const uint8_t *world_rgba,const uint8_t *world_observed,const NG2ProfileRasterValidity *world_validity,
    const uint8_t *pause_ui,const NG2ProfileRasterValidity *pause_validity,
    NG2Scene *scene,int32_t *selected_view,NG2ProfileRasterValidity *selected_validity);
/* Coverage-only witness for the unchanged C's existing three-item VISIBLE.
 * Does not find signs, inspect colours or reimplement merchandise thresholds. */
int ng2_profile_goods_support(const NG2Scene *scene,const uint8_t *observed,size_t length,
    NG2DeviceRect *required_canonical);
void ng2_profile_restrict_scene(NG2Scene *scene,NG2ProfileRasterValidity *validity,
    const uint8_t *observed);
#endif
