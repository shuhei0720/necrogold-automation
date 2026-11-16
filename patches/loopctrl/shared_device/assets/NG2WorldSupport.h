/* Scoped geometry-only world observation support. No input authority and no
 * changes to NG2Core/Scene ABI. UI-template validity is a separate contract. */
#ifndef NG2_WORLD_SUPPORT_H
#define NG2_WORLD_SUPPORT_H
#include <stddef.h>
#include <stdint.h>
enum {
    NG2_WORLD_CLEAR_UNKNOWN=0,
    NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD=1
};
typedef struct {
    const uint8_t *pointer;
    size_t len;
    int32_t enabled,clear_scope;
    const uint8_t *world_rgba;
    size_t rgba_len,rgba_stride;
    int32_t has_rgba,rgba_valid;
} NG2WorldSupportScope;
/* Immutable896x414 pixel support must belong to this exact world raster.
 * NULL+0 preserves legacy behavior. Any other malformed context stays enabled
 * and rejects all evidence. Caller must restore the returned scope on every
 * path and keep Data storage alive until leave, including nested scopes.
 * CLEAR scope1 certifies only the complete observed local FOV minus known HUD;
 * extra unknown occlusions/overwritten world require scope0. */
NG2WorldSupportScope ng2_world_support_enter(const uint8_t *world_observed,size_t length,int32_t clear_scope);
/* Same-capture pre-UI world plane. Enter validates opaque canonical RGBA8;
 * storage is borrowed and immutable through leave. Invalid RGBA remains an
 * enabled reject-all context. The public C analysis stride/length must match. */
NG2WorldSupportScope ng2_world_support_enter_rgba(const uint8_t *world_rgba,size_t rgba_length,size_t stride,
    const uint8_t *world_observed,size_t observed_length,int32_t clear_scope);
void ng2_world_support_leave(NG2WorldSupportScope previous);
int ng2_world_support_active(void);
int ng2_world_pixel_observed(int32_t x,int32_t y);
int ng2_world_roi_observed(int32_t x0,int32_t y0,int32_t x1,int32_t y1);
int32_t ng2_world_support_clear_scope(void);
/* Legacy/mask-only scopes return fallback. Enabled RGBA scopes return the
 * validated pre-UI plane or NULL, never fallback on malformed source data. */
const uint8_t *ng2_world_support_rgba(const uint8_t *fallback,size_t length,size_t stride);
#endif
