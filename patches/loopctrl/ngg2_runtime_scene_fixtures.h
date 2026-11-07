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
#endif
