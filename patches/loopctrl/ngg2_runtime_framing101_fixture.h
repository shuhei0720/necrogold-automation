#ifndef NGG2_RUNTIME_FRAMING101_FIXTURE_H
#define NGG2_RUNTIME_FRAMING101_FIXTURE_H
#include "NG2Controller.h"
#include "NG2Ring.h"
/* HOST telemetry only. Historical fields are declared component preconditions;
 * no mode/job/new ticket/horizon or motion result is supplied by this API. */
typedef struct {
    uint64_t prefix,a_capture,static_capture,move_id,move_ordinal,move_source;
    uint64_t target_ns,not_before_ns,deadline_ns,lead_ns,ack_prefix,moved_capture,job2_capture;
    uint64_t old_horizon,new_horizon,bound_scene_hash,raw_hash[2],scene_hash[2];
    int32_t ready_for_a,seed_count,fit_ok,seed_error,ring_calls,marker[2],mode[2];
    int32_t before_inputs,before_moves,before_restarts,ack_moves,ack_job,unknown_seen;
    int32_t moved_moves,job_after,old_job_rejected,old_ticket_rejected,completed_before;
} NG2Framing101Proof;
void ng2_framing101_reset(void);
void ng2_framing101_proof(NG2Framing101Proof *);
void ng2_framing101_clock(uint64_t now);
int ng2_framing101_pixels(uint8_t *,size_t,int32_t marker);
void ng2_framing101_result(uint64_t job,uint64_t started,uint64_t finished,NG2RingResult *);
void ng2_test_pause(uint8_t *,size_t);
#endif
