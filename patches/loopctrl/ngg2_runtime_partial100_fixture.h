#ifndef NGG2_RUNTIME_PARTIAL100_FIXTURE_H
#define NGG2_RUNTIME_PARTIAL100_FIXTURE_H
#include "NG2Controller.h"
#include "NG2Ring.h"
/* HOST component precondition/telemetry only; never an app source or ABI. */
typedef struct {
    uint64_t a_capture,b_capture,prefix,job_before,job_after,capture_after;
    uint64_t horizon_before,horizon_after,raw_hash[2],scene_hash[2],scene_address[2];
    int32_t seed_count,ready_for_a,b_while_assessing,compared_b,pending_after,state_after;
    int32_t stale_worker_rejected,stale_result_rejected,ring_calls;
    int32_t marker[2],mode[2],items[2],protected_count[2];
} NG2Partial100Proof;
void ng2_partial100_reset(void);
void ng2_partial100_proof(NG2Partial100Proof *);
int ng2_partial100_pixels(uint8_t *,size_t,int32_t marker);
uint64_t ng2_partial100_expected_scene_hash(int32_t marker);
void ng2_partial100_result(uint64_t job,uint64_t started,uint64_t finished,NG2RingResult *);
void ng2_test_pause(uint8_t *,size_t);
#endif
