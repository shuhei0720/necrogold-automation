#ifndef NG2_RUNTIME_SCENE_FIXTURES_H
#define NG2_RUNTIME_SCENE_FIXTURES_H
#include <stddef.h>
#include <stdint.h>
/* Test-only procedural 896x414 opaque packed RGBA. player_x/y are integer
 * world tile positions: moving up is player_y=-1 and shifts terrain down36px.
 * q is remaining beat fraction [0,1); pixel quantization is <=0.5/104 cycles.
 * goods=1 draws a known synthetic complete three-item/price arrangement.
 * Returns1 on success,0 on invalid arguments. No device image is embedded. */
int ng2_fixture_floor_rgba(uint8_t *out,size_t length,int32_t player_x,
                          int32_t player_y,double q,int32_t goods);
/* Pixel offset variant exercises a nearly finished35px camera translation
 * before the matching36px tile translation. HUD geometry stays fixed. */
int ng2_fixture_floor_pixels_rgba(uint8_t *out,size_t length,int32_t world_x,
                                 int32_t world_y,double q,int32_t goods);
/* Change one remote observed cell without affecting the motion-signature ROI. */
int ng2_fixture_remote_cell(uint8_t *out,size_t length,int32_t variant);
/* TEST054 procedural motion-reference world. Variant1 perturbs only sparse
 * signature samples at world_y=-36 and changes remote cell(-10,1); variant0
 * is the unchanged floor generator. No original/device pixels are included. */
int ng2_fixture_motion_reference_rgba(uint8_t *out,size_t length,int32_t world_y,
                                       double q,int32_t goods,int32_t variant);
/* TEST058 finite synthetic world. The33x33 immutable tile map uses world
 * index(y+16)*33+x+16 and materials0unknown/1floor/2gold/3stone/4dirt/7wood.
 * The gate direction points toward the shop interior. Goods variants are
 * 0normal,1partial after opening,2initial adjacent partial. */
int ng2_fixture_shop_rgba(uint8_t *out,size_t length,int32_t player_x,
                          int32_t player_y,double q,const uint8_t *tiles,
                          size_t tile_count,int32_t gate_x,int32_t gate_y,
                          int32_t direction,int32_t goods_variant);
#endif
