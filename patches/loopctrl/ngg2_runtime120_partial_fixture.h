#ifndef NG2_RUNTIME120_PARTIAL_FIXTURE_H
#define NG2_RUNTIME120_PARTIAL_FIXTURE_H
#include "NG2Controller.h"
#include <stddef.h>
#include <stdint.h>
enum {NG2_QUEUE120_BEFORE=0,NG2_QUEUE120_EARLY=1,NG2_QUEUE120_LATE=2,
      NG2_QUEUE120_WALL=3,NG2_QUEUE120_INITIAL=4,NG2_QUEUE120_OPENED=5,
      NG2_QUEUE120_GATE=6,NG2_QUEUE120_PAUSE=7};
int ng2_fixture_queue120_rgba(uint8_t *,size_t,int32_t,int32_t,double);
typedef void (*NG2Partial120FrameCallback)(void *,uint64_t,uint64_t,uint64_t,uint64_t,
    uint64_t,uint64_t,const uint8_t *,size_t,const NG2Scene *,const NG2IrregularObservation *);
typedef struct {
    uint64_t started_ns,latest_id,prefix,ack_ns,epoch_ns,period_ns,entry_ns,return_ns;
    NG2Command command;
    NG2ControllerStatus status;
    int32_t frames,normal_units,error;
} NG2Partial120Setup;
typedef struct {
    uint64_t command_id,motion_calls,motion_ns,begin_calls,begin_accepted;
    uint64_t begin_entry_ns,begin_exit_ns,begin_motion_calls;
    uint64_t getter_calls,getter_motion_calls,getter_ns,complete_calls,complete_ns;
    uint64_t tick_calls,tick_entry_ns,tick_exit_ns;
    int32_t complete_outcome,motion_kind,motion_dx,motion_dy;
} NG2Partial120Counts;
uint64_t ng2_partial120_now(void);
void ng2_partial120_select(uint64_t);
void ng2_partial120_arm_target(void);
void ng2_partial120_counts(NG2Partial120Counts *);
double ng2_fixture_partial120_phase(const NG2Partial120Setup *,uint64_t);
NG2Controller *ng2_fixture_partial120_setup(NG2Partial120FrameCallback,void *,NG2Partial120Setup *);
#endif
