#ifndef NGG2_CYCLE_RUNTIME_FIXTURE_H
#define NGG2_CYCLE_RUNTIME_FIXTURE_H
#include "ngg2/NG2Core.h"
#include "ngg2/NG2Ring.h"
/* Procedural worker proof for host control/callback tests only. This is never
 * compiled into the runner and does not assert image or device accuracy. */
void ng2_fixture_cycle_result(const NG2Scene *, uint64_t started_ns,
    uint64_t finished_ns, int outcome, NG2RingResult *);
/* Same procedural RGBA source for Swift callbacks and the C preflight.
 * variant0 is the original world; variant1 changes six observed peripheral
 * floor patches to textured STONE, without editing Scene/fingerprint output.
 * goods0=CLEAR, goods1=VISIBLE, goods2=PARTIAL; no device pixels are embedded. */
int ng2_fixture_cycle_search_rgba(uint8_t *out, size_t length, int32_t world_x,
    int32_t variant, int32_t goods);
#endif
