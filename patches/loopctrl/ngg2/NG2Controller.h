/* NG-G2 bounded native controller. All times are device monotonic nanoseconds.
 * One caller serializes core calls; cancellation is also checked by the Swift
 * main ticket before synth. No core pointer is shared with status/cancel RPCs. */
#ifndef NG2_CONTROLLER_H
#define NG2_CONTROLLER_H
#include "NG2Core.h"
typedef struct NG2Controller NG2Controller;
enum { NG2_ACTION_NONE=0, NG2_ACTION_RESUME=1, NG2_ACTION_PAUSE=2,
       NG2_ACTION_RESTART=3, NG2_ACTION_MOVE=4 };
enum { NG2_PHASE_SEARCH=0, NG2_PHASE_FLOOR=1, NG2_PHASE_PAUSE=2,
       NG2_PHASE_RESTART=3, NG2_PHASE_SYNC=4, NG2_PHASE_WALK=5,
       NG2_PHASE_FINISH=6, NG2_PHASE_DONE=7 };
enum { NG2_REASON_NONE=0, NG2_REASON_GOODS=1, NG2_REASON_CANCELLED=2,
       NG2_REASON_FOREGROUND=3, NG2_REASON_LOCKED=4, NG2_REASON_OWNER_PAUSED=5,
       NG2_REASON_CAPTURE=6, NG2_REASON_STALE=7, NG2_REASON_BEAT=8,
       NG2_REASON_LATE=9, NG2_REASON_MOVEMENT=10, NG2_REASON_UNKNOWN_INPUT=11,
       NG2_REASON_NO_PATH=12, NG2_REASON_PARTIAL_GOODS=13, NG2_REASON_LIMIT=14,
       NG2_REASON_SESSION=15, NG2_REASON_RESTART=16, NG2_REASON_SCREEN=17,
       NG2_REASON_GENERATION=18, NG2_REASON_HEARTBEAT=19, NG2_REASON_GEOMETRY=20 };
typedef struct {
    uint64_t id, ordinal, target_ns, not_before_ns, deadline_ns;
    uint64_t source_capture_id, source_start_ns, phase_sample_ns;
    int32_t kind, direction, x, y;
} NG2Command;
typedef struct {
    uint32_t abi_version, struct_size;
    int32_t phase, reason, terminal, goods, paused, input_state;
    int32_t inputs, moves, door_changes, terrain_changes, restarts, x, y, lead_confirmed;
    uint64_t started_ns, walk_started_ns, ended_ns, first_move_ns;
    uint64_t last_capture_id, last_capture_start_ns, last_capture_end_ns;
    uint64_t last_completed_id, current_command_id, last_ordinal, next_target_ns, lead_ns;
    uint64_t capture_count, accepted_frames, discarded_frames, beat_period_ns;
} NG2ControllerStatus;
typedef struct {
    NG2Command command;
    uint64_t begin_ns, end_ns, observed_capture_id;
    int32_t outcome, reason, motion, dx, dy;
} NG2ControllerEvent;
/* Bounded TEST045 diagnostics, separate from the existing status/event ABI. */
typedef struct {
    uint64_t command_id, source_capture_id, observed_capture_id, target_ns, deadline_ns;
    int32_t change_mask, changed_tiles, changed_protected, state_before, state_after;
    int32_t goods_before, goods_after, replan_count, replan_allowed;
} NG2ControllerSceneChange;
/* TEST051 bounded companion rows. Both queries retain first1/latest2 in the
 * same order, without changing any existing public struct layout. Cell deltas
 * are the first four distinct row-major changed coordinates: x=-11..11,
 * y=-5..4, tiles=0..6, protected=0..1. cell_count=0..4 and omitted_cells=0..226
 * count their union (sum<=230). Counters include the current allowance and
 * are bounded at continuous_count<=8 / chain_count<=2. */
enum { NG2_REVALIDATE_NONE=0, NG2_REVALIDATE_INITIAL_ALLOWED=1,
       NG2_REVALIDATE_CONTINUOUS_ALLOWED=2, NG2_REVALIDATE_INITIAL_REJECTED=3,
       NG2_REVALIDATE_STATE=4, NG2_REVALIDATE_BUDGET=5,
       NG2_REVALIDATE_TIMING=6, NG2_REVALIDATE_FLOOR=7,
       NG2_REVALIDATE_GOLD=8, NG2_REVALIDATE_PROTECTED=9,
       NG2_REVALIDATE_ROUTE=10, NG2_REVALIDATE_MOTION=11 };
typedef struct {
    int32_t x, y, tile_before, tile_after, protected_before, protected_after;
} NG2ControllerCellChange;
typedef struct {
    uint64_t command_id, source_capture_id, observed_capture_id;
    int32_t validation, continuous_count, chain_count, cell_count, omitted_cells;
    NG2ControllerCellChange cells[4];
} NG2ControllerSceneDetail;
/* TEST046 visual confirmation, separate from the status/event ABI. The latest
 * MOVE remains queryable after active becomes zero. active is always 0 or 1. */
typedef struct {
    uint64_t command_id, source_capture_id, last_capture_id, deadline_ns;
    int32_t attempts, last_motion, active;
} NG2ControllerMotionWait;
/* Defaults: 16 directions, 12 restarts, 45s walking, 180s session. */
NG2Controller *ng2_controller_create(uint64_t now);
void ng2_controller_destroy(NG2Controller *controller);
/* stable=1 only if capture saw the same completed prefix and no inflight UI
 * command at both boundaries. Scene bytes are copied before returning. */
int ng2_controller_observe(NG2Controller *, const NG2Scene *, uint64_t capture_id,
    uint64_t start_ns, uint64_t end_ns, uint64_t completed_prefix, int32_t stable);
/* Tick reserves at most one immutable ticket. 1=ticket,0=none,-1=invalid. */
int ng2_controller_tick(NG2Controller *, uint64_t now, int32_t foreground,
    int32_t locked, int32_t owner_active, NG2Command *out);
/* Called on main immediately before synth while the control caller is blocked.
 * Rechecks the original ticket/deadline and current guards. 1 permits ONE synth.
 * A late queued ticket is never silently rescheduled. */
int ng2_controller_begin(NG2Controller *, uint64_t command_id, uint64_t now,
    int32_t foreground, int32_t locked, int32_t owner_active);
/* outcome: 1=synth returned success; 0=definitely not started; -1=started unknown.
 * completed synth is still not proof of gameplay movement. Never resend. */
int ng2_controller_complete(NG2Controller *, uint64_t command_id, uint64_t now, int32_t outcome);
void ng2_controller_cancel(NG2Controller *, uint64_t now, int32_t reason);
void ng2_controller_status(const NG2Controller *, NG2ControllerStatus *out);
size_t ng2_controller_events(const NG2Controller *, NG2ControllerEvent *out, size_t capacity);
size_t ng2_controller_scene_changes(const NG2Controller *, NG2ControllerSceneChange *out, size_t capacity);
size_t ng2_controller_scene_details(const NG2Controller *, NG2ControllerSceneDetail *out, size_t capacity);
void ng2_controller_motion_wait(const NG2Controller *, NG2ControllerMotionWait *out);
const char *ng2_reason_name(int32_t reason);
#endif
