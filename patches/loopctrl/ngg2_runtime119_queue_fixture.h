#ifndef NG2_RUNTIME119_QUEUE_FIXTURE_H
#define NG2_RUNTIME119_QUEUE_FIXTURE_H
#include "ngg2/NG2Controller.h"
#include <stddef.h>
#include <stdint.h>
enum {NG2_QUEUE119_BEFORE=0,NG2_QUEUE119_EARLY=1,NG2_QUEUE119_LATE=2,
      NG2_QUEUE119_WALL=3,NG2_QUEUE119_INITIAL=4,NG2_QUEUE119_OPENED=5,
      NG2_QUEUE119_GATE=6,NG2_QUEUE119_PAUSE=7};
int ng2_fixture_queue119_rgba(uint8_t *,size_t,int32_t,int32_t,double);
/* Actual calls use normal Perception and public Controller lifecycle only. */
typedef void (*NG2Queue119FrameCallback)(void *,uint64_t,uint64_t,uint64_t,
    uint64_t,int32_t,const uint8_t *,size_t,const NG2Scene *,const NG2IrregularObservation *);
typedef struct {
    uint64_t started_ns,latest_id,prefix,ack_ns,epoch_ns,period_ns;
    NG2Command command;
    NG2ControllerStatus status;
    NG2ControllerCycleStatus cycle;
    int32_t frames,normal_units,opened_units,error;
} NG2Queue119Setup;
NG2Controller *ng2_fixture_queue119_setup(uint64_t,NG2Queue119FrameCallback,
    void *,NG2Queue119Setup *);
/* Prepare/cache this fixture's own normal-Perception prelude before choosing
 * its recent-past time origin. No Controller state is cached or restored. */
int ng2_fixture_queue119_prepare(void);
void ng2_fixture_queue119_prepared(NG2Queue119Setup *);
double ng2_fixture_queue119_phase(const NG2Queue119Setup *,uint64_t);
#endif
