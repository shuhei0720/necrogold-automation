#ifndef NGG2_CYCLE_RUNTIME_FIXTURE_H
#define NGG2_CYCLE_RUNTIME_FIXTURE_H
#include "ngg2/NG2Core.h"
#include "ngg2/NG2Ring.h"
/* Procedural worker proof for host control/callback tests only. This is never
 * compiled into the runner and does not assert image or device accuracy. */
void ng2_fixture_cycle_result(const NG2Scene *, uint64_t started_ns,
    uint64_t finished_ns, int outcome, NG2RingResult *);
#endif
