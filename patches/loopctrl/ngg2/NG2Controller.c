/* TEST043 device-clock controller. Synth ACK is never movement evidence.
 * Calls are serialized by the adapter; begin runs on main while that caller
 * is blocked. No callback, shared global state, HTTP model or clock is used. */
#include "NG2Controller.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
/* Private zero-only recognition; no public Core ABI or motion result changes. */
int ng2_clear_singleton_stationary_zero(const NG2Scene *a,const NG2Scene *b,int32_t direction);
int ng2_clear_singleton_phase_stationary_zero(const NG2Scene *a,const NG2Scene *b,int32_t direction);
int ng2_clear_plural_palette_stationary_zero(const NG2Scene *a,const NG2Scene *b,int32_t direction);
int ng2_unlocalized_passage_motion_zero(const NG2Scene *a,const NG2Scene *b,int32_t direction,NG2Motion *out,int32_t *zero);
#define NS_LIMIT (UINT64_C(1)<<63)
#define SECOND UINT64_C(1000000000)
#define FRESH (3*SECOND)
#define TRANSITION (4*SECOND)
#define EVENT_CAP 64
#define MOTION_REFERENCE_CAP 16
#define MOTION_ASSESSMENTS 8
#define UI_SETTLE_NS UINT64_C(200000000)
#define INITIAL_PREPARATION UINT64_C(50000000)
#define INITIAL_PUBLICATION UINT64_C(100000000)
#define CONTINUOUS_PUBLICATION UINT64_C(100000000)
#define CONTINUOUS_SOURCE UINT64_C(200000000)
#define CYCLE_CAPTURE_BUDGET UINT64_C(150000000)
#define CYCLE_WORKER_BUDGET UINT64_C(100000000)
static const uint64_t leads[7]={150000000,75000000,225000000,300000000,375000000,450000000,25000000};
static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
enum { NG2_CONTINUOUS_NONE=0, NG2_CONTINUOUS_SAME=1, NG2_CONTINUOUS_FRESH=2 };
enum { NG2_GATE_RETRY_NONE=0, NG2_GATE_RETRY_REFIT=1, NG2_GATE_RETRY_ISSUED=2 };
enum { NG2_GATE_REFRESH_NONE=0, NG2_GATE_REFRESH_OBSERVE=1,
       NG2_GATE_REFRESH_READY=2, NG2_GATE_REFRESH_ISSUED=3 };
enum { NG2_OBSERVATION_REFRESH_SIDE_OPENING=2,
       NG2_OBSERVATION_REFRESH_VANTAGE_REPLAN=3 };
/* Private entry-only observation episode. Public ABI and old one-shot
 * authorities remain unchanged. Started inputs are never refunded. */
typedef struct {
    int active,stage,inputs,moves,valid,side;
    uint64_t parent,level,opening,job,capture,prefix,issued,last_move,moved_capture,ordinal;
    int parent_box[4],current_box[4];
    NG2Scene reference;
    NG2Decision choice;
} NG2EntryEpisode;
/* A separate DOWN-only observation whose frozen search union determines
 * its finite step count. Parent/count survive jobs; route guards are intact. */
typedef struct {
    int active,stage,inputs,moves,steps,valid;
    uint64_t parent,level,issued,ordinal;
    int box[4],parent_box[4];
    NG2ControllerStopDetail bridge_stop;
} NG2LowerObservation;
/* A direct normal-zero fact owns one exact immutable anchor/current pair.
 * It saves no command or clock authority and never chains through a third
 * image. Full copies also cover signatures, HUD fields and every mask byte. */
typedef struct {
    int valid,direction,horizontal,down,inputs,rebound;
    uint64_t owner,level,opening,job,anchor_id,anchor_start,anchor_end,anchor_prefix;
    uint64_t current_id,current_start,current_end,current_prefix;
    NG2Scene anchor,current;
} NG2UpperStaticProof;
/* A bounded horizontal entry followed by individually observed DOWN steps.
 * V1 retains four starts/base parent. V2 allocates one extra observed step
 * and one frozen period only at its first admission; neither can renew. */
typedef struct {
    int active,stage,valid,direction,inputs,horizontal,down,rebound,x,y,variant,row,steps;
    uint64_t parent,hold,sync,level,opening,job,capture,prefix,issued,ordinal;
    uint64_t base_parent,allocated_parent,allocation_period;
    uint64_t anchor_end;
    int first_inputs,first_horizontal,first_down;
    uint64_t first_owner,first_level,first_job,first_capture,first_start,first_end,first_prefix;
    uint64_t first_opening,first_worker,first_assessment,first_proof;
    NG2UpperStaticProof static_proof;
    NG2Scene world;
} NG2UpperObservation;
/* One composed PARTIAL data refinement belongs to the original level and
 * opening. A job latch cannot recreate this spent authority. */
typedef struct {
    int used;
    uint64_t owner_start,level,opening,job,capture,prefix,parent,hold,sync;
} NG2UpperPartialRefresh;
/* Opt-in boundary after a real, durably recorded negative restart. Old
 * counters and the new floor remain intact; this state grants only PAUSE. */
typedef struct {
    NG2ControllerRestartYieldStatus s;
    NG2ControllerCycleStatus prior;
    uint8_t fingerprint[48],first_fingerprint[48];
    uint64_t first_start,first_end,ack,pause,permit_capture,permit_start;
    uint64_t last_goods_id;
    int required,done,submitted,current_kind,inputs,moves,restarts;
} NG2RestartYield;
/* One definitely-unsent passage source refinement shares the original beat.
 * Its first world and image stay immutable; this is never motion evidence. */
typedef struct {
    int active,refreshed,x,y,inputs,moves,bit,unlocalized;
    uint32_t pending,inspected,unresolved,closed;
    uint64_t prefix,period,schedule,visual,sync;
    NG2Scene anchor;
    NG2Command ticket;
    NG2Decision choice;
    NG2Entrance entrance;
    uint16_t visits[NG2_VISIT_COUNT];
} NG2PassageSource;
typedef struct {
    int active;
    uint64_t owner_start,trigger,source_command,source_id,source_start,prefix,W,P;
    uint64_t id,start,end,qualified;
    NG2Scene scene;
} NG2StationarySupport;
typedef struct {
    int valid;
    uint64_t owner_start,trigger,source_command,source_id,source_start,prefix,W,P;
    uint64_t capture_id,start,end,support_id,support_start,support_end,support_qualified;
    NG2Scene scene;
} NG2StationaryQualification;
/* Explicit root-only UI initialization. It never certifies a changed world,
 * a negative shop or the finite restart-yield boundary. */
enum { NG2_INITIAL_SOURCE=1, NG2_INITIAL_VETO=2, NG2_INITIAL_PAUSE=3,
       NG2_INITIAL_RESTART=4, NG2_INITIAL_FLOOR=5, NG2_INITIAL_DONE=6,
       NG2_INITIAL_HELD=7 };
typedef struct {
    int configured,stage;
    uint64_t parent,source,source_start,source_end,source_prefix;
    uint64_t veto_capture,veto_prefix,veto_job,pause,restart,ack;
} NG2InitialRestart;
struct NG2Controller {
    NG2PassageSource passage_source;
    NG2ControllerStatus s;
    NG2Scene scene,before,retune_anchor,initial_scene_previous;
    NG2Scene motion_reference_scene;
    NG2Scene gate_refresh_anchor,gate_refresh_previous;
    NG2StationarySupport stationary_support;
    NG2StationaryQualification stationary_qualification;
    NG2Decision gate_refresh_choice;
    NG2Entrance entrance;
    NG2BeatModel model;
    NG2BeatSample samples[13];
    NG2ControllerEvent events[EVENT_CAP];
    NG2Command command;
    NG2Command initial_ticket;
    NG2Command continuous_ticket;
    NG2Decision command_choice,continuous_pending_choice;
    NG2ControllerSceneChange scene_changes[3];
    NG2ControllerSceneDetail scene_details[3];
    NG2ControllerMotionWait motion_wait;
    NG2ControllerRecoveryStatus recovery;
    NG2BeatSample recovery_samples[2][13];
    NG2ControllerMotionReference motion_references[MOTION_REFERENCE_CAP];
    NG2Command motion_reference_ticket;
    NG2Decision motion_reference_choice;
    NG2Entrance motion_reference_entrance;
    NG2Entrance stationary_wait_entrance;
    uint16_t visits[NG2_VISIT_COUNT];
    uint16_t motion_reference_visits[NG2_VISIT_COUNT];
    uint16_t stationary_wait_visits[NG2_VISIT_COUNT];
    uint8_t restart_fingerprint[48];
    uint64_t seen_id,seen_start,seen_end,last_now,transition_ns,sync_ns;
    uint64_t ack_ns,command_period,next_nominal,next_deadline,next_period,last_observed_prefix;
    uint64_t motion_retry_start_ns,motion_retry_last_ns;
    uint64_t stationary_gate_retry_proof_id;
    uint64_t edge_validated_capture_id;
    uint64_t latest_verified_ns;
    uint64_t gate_refresh_deadline,gate_refresh_prefix,gate_refresh_proof_id;
    uint64_t gate_refresh_previous_start,gate_refresh_previous_end;
    uint64_t stationary_wait_parent,stationary_wait_trigger_id;
    uint64_t observation_refresh_verified;
    uint64_t next_update_deadline;
    uint64_t schedule_deadline,continuous_schedule_deadline,initial_visual_deadline;
    uint64_t initial_slot_visual_deadline,proof_deadline,proof_capture_id,model_capture_id;
    uint64_t recovery_slot_target,recovery_slot_not_before,recovery_slot_period;
    uint64_t recovery_slot_deadline,recovery_slot_schedule,recovery_slot_visual;
    uint64_t observe_now;
    uint64_t command_sync_deadline;
    int proof_reacquire,visual_phase_failed;
    uint64_t finish_ns,preparation_epoch,preinput_refresh_epoch;
    size_t sample_count,event_count;
    size_t scene_change_count;
    size_t motion_reference_count;
    uint64_t motion_reference_prefix,motion_reference_period,motion_reference_deadline;
    int motion_reference_present,motion_reference_valid,motion_reference_reissued;
    int motion_reference_x,motion_reference_y,motion_reference_moves,motion_reference_inputs;
    uint64_t initial_period;
    uint64_t initial_slot_target,initial_slot_not_before,initial_slot_period;
    uint64_t initial_slot_deadline,initial_slot_motion_deadline;
    uint64_t continuous_period,continuous_motion_deadline;
    int initial_ticket_valid,replan_pending,replan_count;
    int continuous_ticket_valid,continuous_pending,continuous_chain_count,continuous_count;
    int have_scene,finish_requested,final_pause_attempted,need_fresh_cleanup;
    int restart_pending,lead_index,retune_direction,have_anchor,beat_failed;
    int stationary_gate_retry_used;
    int stationary_gate_recovery_pending;
    int stationary_gate_retry_waiting;
    int edge_sent;
    int gate_refresh_state,gate_refresh_used;
    int terrain_refresh_active,terrain_refresh_used;
    int level_input_base,level_move_base;
    uint32_t passage_pending,passage_inspected,passage_unresolved,passage_closed;
    int passage_active,passage_bit,passage_wait_kind,restart_baseline_valid,restart_intent;
    uint64_t passage_wait_deadline,passage_wait_horizon,passage_release_proof_id,passage_anchor_id,passage_anchor_start,passage_anchor_end;
    NG2Scene passage_anchor;
    uint64_t initial_view_id,initial_view_start,initial_view_end;
    uint64_t initial_candidate_id,initial_candidate_end,initial_candidate_prefix;
    uint32_t initial_candidate_mask;
    unsigned char initial_candidate_tiles[30];
    int initial_view_pending,initial_candidate_waiting,initial_scene_reacquiring;
    int passage_unlocalized_gold,initial_candidate_unlocalized;
    int passage_initial_reanchor;
    uint64_t opened_entry_parent,opened_entry_recovery_ns;
    int observation_refresh_active,observation_refresh_count;
    int stationary_wait_active,stationary_wait_x,stationary_wait_y;
    int stationary_wait_inputs,stationary_wait_moves,stationary_wait_passage,stationary_wait_bit;
    uint32_t stationary_wait_pending,stationary_wait_inspected,stationary_wait_unresolved,stationary_wait_closed;
    /* New-profile state is appended; no old public layout or latch changes. */
    int cycle_enabled,cycle_pause_attempted,cycle_storage_error,cycle_partial_credit;
    int cycle_queued_valid,cycle_choice_valid,cycle_framing_credit,cycle_rejection_recorded;
    int cycle_search_restart,cycle_restart_unproved;
    /* One new exposure may be classified while the observer stays still.
     * Only verified displacement or a proven new level restores this bound. */
    int cycle_partial_rebind_used;
    /* Only an adopted, nonempty normal PARTIAL UNKNOWN may retire stale
     * material evidence for a fresh data job. This grants no MOVE credit. */
    int cycle_refresh_safe;
    /* One local observation after a FULL UNKNOWN does not restore world
     * localization. Spent survives verified movement until a proven level. */
    int cycle_full_framing,cycle_full_spent;
    uint64_t cycle_full_old_ordinal;
    NG2Decision cycle_full_choice;
    /* Classification may advance while this one-use movement source stays
     * fixed. Neither a data job nor its queued successor renews its parent. */
    int cycle_full_source_valid,cycle_full_data_active,cycle_full_data_blocked;
    uint64_t cycle_full_source_id,cycle_full_source_start,cycle_full_source_prefix,cycle_full_parent;
    NG2Scene cycle_full_source;
    /* At most two fresh data jobs after an initial FULL deadline. The first
     * source and root clocks remain immutable; this state grants no MOVE. */
    int cycle_retry_only,cycle_retry_waiting,cycle_retry_used,cycle_retry_blocked,cycle_late_worker,cycle_assessing;
    int cycle_retry_data;
    uint64_t cycle_retry_parent,cycle_retry_hold,cycle_retry_prefix,cycle_retry_level;
    NG2Scene cycle_retry_source;
    /* Cache the owned prior UP source before a prepared PAUSE can replace
     * before/command. Late credit requires that original ACK's normal unit,
     * never a comparison from the early FULL or an ambiguous synth. */
    int cycle_up_history;
    uint64_t cycle_up_capture,cycle_up_job,cycle_up_level,cycle_up_period;
    NG2Command cycle_up_command;
    NG2Scene cycle_up_before;
    /* A hard-invalid old FULL may fund one independent current DATA job.
     * Its new anchor never migrates; old invalidation and MOVE credit remain. */
    int cycle_current_used,cycle_current_active,cycle_current_invalid,cycle_current_proofs;
    /* Current origin:0 FULL/UP,1 clipped PARTIAL/UP,2 latest FULL/DATA only.
     * Only origin1 retains the original potential projection for routes. */
    int cycle_current_partial;
    uint8_t cycle_current_potential[NG2_TILE_COUNT];
    uint64_t cycle_current_id,cycle_current_start,cycle_current_end,cycle_current_prefix;
    uint64_t cycle_current_level,cycle_current_job,cycle_current_proof_id,cycle_current_proof_end;
    uint64_t cycle_current_parent,cycle_current_sync,cycle_current_ordinal;
    NG2Scene cycle_current_source;
    NG2ControllerIrregularStatus irregular;
    NG2IrregularObservation irregular_observation,irregular_first_enemy,irregular_menu;
    NG2Scene irregular_live,irregular_move_before,irregular_floor,irregular_goods;
    uint64_t irregular_observation_id,irregular_live_id,irregular_first_id;
    uint64_t irregular_first_start,irregular_first_end,irregular_first_command;
    uint64_t irregular_menu_id,irregular_menu_end,irregular_trigger_prefix;
    uint64_t irregular_ring_job,irregular_ring_capture,irregular_ring_prefix,irregular_ring_deadline;
    uint64_t irregular_death_wait_capture;
    uint64_t irregular_floor_start,irregular_floor_end,irregular_floor_prefix;
    uint64_t irregular_goods_id,irregular_goods_start,irregular_goods_end,irregular_goods_prefix;
    uint8_t irregular_baseline[48];
    int irregular_observation_valid,irregular_call,irregular_lead_before;
    int irregular_ring_pending,irregular_menu_ready,irregular_death_wait,irregular_restart_ui;
    NG2EntryEpisode entry;
    NG2LowerObservation lower;
    NG2UpperObservation upper;
    NG2UpperPartialRefresh upper_partial_refresh;
    uint64_t cycle_credit_prefix,cycle_consumed_prefix,cycle_sync_deadline;
    NG2ControllerCycleStatus cycle;
    NG2Scene cycle_anchor,cycle_queued_scene;
    uint64_t cycle_move_data_end;
    NG2Decision cycle_choice;
    NG2ControllerStopDetail first_stop;
    NG2ControllerHandoff handoff;
    NG2Motion diagnostic_motion;
    int diagnostic_validation,handoff_fault,handoff_pause_bound;
    uint64_t diagnostic_capture_id,diagnostic_observed_id;
    uint64_t handoff_initial_ns,handoff_initial_source,handoff_initial_prefix;
    uint64_t handoff_pause_command,last_level_restart_id,last_level_restart_capture;
    uint64_t last_level_restart_prefix;
    int last_level_restart_count;
    NG2RestartYield restart_yield;
    NG2ControllerContinuousStatus campaign;
    NG2InitialRestart initial_restart;
};
static int restart_yield_basis(const NG2Controller *,uint64_t);
static int restart_yield_ui_source(const NG2Controller *,uint64_t,uint64_t,uint64_t,int);
static void restart_yield_invalidate(NG2Controller *p){
    if(p->restart_yield.s.pending){p->restart_yield.s.invalid=1;p->restart_yield.s.permitted=0;}
}
static void live_stop_detail(const NG2Controller *p,NG2ControllerStopDetail *out){
    memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
    out->passage_bit=p->passage_bit;out->wait_kind=p->passage_wait_kind;
    out->passage_pending=p->passage_pending;out->passage_unresolved=p->passage_unresolved;
    out->passage_unlocalized_gold=p->passage_unlocalized_gold;
    out->x=p->s.x;out->y=p->s.y;out->prefix=p->s.last_completed_id;
    out->source_capture_id=p->command.source_capture_id;
    out->observed_capture_id=p->diagnostic_observed_id?p->diagnostic_observed_id:p->s.last_capture_id;
    out->last_comparison_capture_id=p->diagnostic_capture_id;out->validation=p->diagnostic_validation;
    out->motion_kind=p->diagnostic_motion.kind;out->motion_dx=p->diagnostic_motion.dx;out->motion_dy=p->diagnostic_motion.dy;
    out->deadline_ns=p->command.deadline_ns;
    if(p->cycle_partial_credit||p->cycle_full_framing||p->cycle_full_data_active||(p->entry.active&&p->entry.stage<6)||(p->lower.active&&p->lower.stage<6)||(p->upper.active&&p->upper.stage<6)||p->cycle.state==NG2_CYCLE_OBSERVE_MORE){
        out->stage=(p->cycle_partial_credit||p->cycle_full_framing>=2||(p->entry.active&&p->entry.stage>=2&&p->entry.stage<=4)||(p->lower.active&&p->lower.stage>=2&&p->lower.stage<=4)||(p->upper.active&&p->upper.stage>=2&&p->upper.stage<=4))?NG2_STOP_CYCLE_CREDIT:NG2_STOP_CYCLE_OBSERVE;
        out->source_capture_id=out->anchor_capture_id=p->cycle.capture_id;
        if(p->cycle_full_source_valid)out->anchor_capture_id=p->cycle_full_source_id;
        out->deadline_ns=p->upper.active?p->upper.parent:p->entry.active?p->entry.parent:p->cycle.continuation_deadline_ns;
    }else if(p->passage_wait_kind){
        out->stage=NG2_STOP_PASSAGE_WAIT;out->anchor_capture_id=p->passage_anchor_id;
        out->deadline_ns=p->passage_wait_deadline?p->passage_wait_deadline:p->passage_wait_horizon;
    }
}
static void freeze_stop_detail(NG2Controller *p,uint64_t now,int reason,const NG2ControllerStopDetail *basis){
    if(p->first_stop.valid)return;
    if(basis)p->first_stop=*basis;else live_stop_detail(p,&p->first_stop);
    p->first_stop.valid=1;p->first_stop.reason=reason;p->first_stop.at_ns=now;
    if(!p->first_stop.stage)p->first_stop.stage=NG2_STOP_GENERIC;
}
static void diagnostic_comparison(NG2Controller *p,uint64_t id,int validation,const NG2Motion *motion){
    if(p->first_stop.valid)return;
    p->diagnostic_capture_id=id;p->diagnostic_validation=validation;
    if(motion)p->diagnostic_motion=*motion;else memset(&p->diagnostic_motion,0,sizeof(p->diagnostic_motion));
}
void ng2_controller_stop_detail(const NG2Controller *p,NG2ControllerStopDetail *out){
    if(!out)return;
    if(!p){memset(out,0,sizeof(*out));return;}
    if(p->first_stop.valid)*out=p->first_stop;else live_stop_detail(p,out);
}
static int cycle_holding(const NG2Controller *p){
    return p->cycle_enabled&&p->cycle.state!=NG2_CYCLE_SEARCH&&p->cycle.state!=NG2_CYCLE_DONE;
}
static int tile_index(int x,int y){return x>=-11&&x<=11&&y>=-5&&y<=4?(y+5)*23+x+11:-1;}
static int tile(const NG2Scene *s,int x,int y){int k=tile_index(x,y);return k<0?0:s->tiles[k];}
static int protected_at(const NG2Scene *s,int x,int y){int k=tile_index(x,y);return k>=0&&s->protected_cells[k];}
/* A goods mask may overlap an impassable wall. It never licenses an ITEM,
 * unknown cell or walking surface; both observations must retain this GOLD. */
static int protected_route_cell(const NG2Scene *a,const NG2Scene *b,int x,int y){
    return protected_at(b,x,y)&&(tile(a,x,y)!=NG2_TILE_GOLD||tile(b,x,y)!=NG2_TILE_GOLD);
}
static int valid_time(uint64_t t){return t<NS_LIMIT;}
static uint64_t minimum(uint64_t a,uint64_t b){return a<b?a:b;}
static int initial_restart_active(const NG2Controller *p){
    return p->initial_restart.configured&&p->initial_restart.stage>=NG2_INITIAL_SOURCE
        &&p->initial_restart.stage<NG2_INITIAL_DONE;
}
static uint64_t maximum(uint64_t a,uint64_t b){return a>b?a:b;}
/* A campaign can only shorten an original child session; no counter or
 * elapsed budget is reset inside this controller. */
static uint64_t session_bound(const NG2Controller *p){
    uint64_t bound=p->s.started_ns+180*SECOND;
    return p->campaign.enabled?minimum(bound,p->campaign.root_deadline_ns):bound;
}
static int campaign_expired(const NG2Controller *p,uint64_t now){
    return p->campaign.enabled&&now>=p->campaign.root_deadline_ns;
}
static int valid_scene(const NG2Scene *s){
    int i;
    if(!s||s->abi_version!=NG2_ABI_VERSION||s->struct_size!=sizeof(*s)||s->state<0||s->state>2
        ||s->restart_label<0||s->restart_label>1||s->gold_state<0||s->gold_state>NG2_GOLD_EDGE_DOWN
        ||s->gold_peak<0||s->gold_peak>255||s->goods<0||s->goods>2||s->beat_valid<0||s->beat_valid>1)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(s->tiles[i]>NG2_TILE_ITEM||s->protected_cells[i]>1)return 0;
    return 1;
}
static NG2ControllerEvent *event(NG2Controller *p){return p->event_count?&p->events[p->event_count-1]:NULL;}
static void clear_stationary_wait(NG2Controller *p){
    memset(&p->stationary_qualification,0,sizeof(p->stationary_qualification));
    memset(&p->stationary_support,0,sizeof(p->stationary_support));
    p->stationary_wait_active=0;p->stationary_wait_parent=0;p->stationary_wait_trigger_id=0;
}
static void terminal(NG2Controller *p,uint64_t now,int reason){
    if(reason!=NG2_REASON_LIMIT||p->handoff.kind!=NG2_HANDOFF_RESTARTED_BUDGET)restart_yield_invalidate(p);
    if(!p->s.terminal){
        freeze_stop_detail(p,now,reason,NULL);
        if(reason!=NG2_REASON_LIMIT||!p->handoff.kind)p->handoff_fault=1;
    }
    p->preparation_epoch=0;
    p->cycle_framing_credit=0;
    p->opened_entry_parent=p->opened_entry_recovery_ns=0;
    p->passage_unlocalized_gold=p->initial_candidate_unlocalized=0;p->passage_initial_reanchor=0;
    clear_stationary_wait(p);
    if(!p->s.terminal){p->motion_wait.active=0;p->s.reason=reason;p->s.terminal=1;p->s.phase=NG2_PHASE_DONE;p->s.ended_ns=now;
        if(p->cycle_enabled){p->cycle.state=NG2_CYCLE_DONE;p->cycle.pending=0;p->cycle_partial_credit=0;}}
}
static void not_sent(NG2Controller *p,uint64_t now,int reason){
    NG2ControllerEvent *e=event(p);
    if(p->s.input_state==1){if(e){e->outcome=3;e->reason=reason;e->end_ns=now;}
        p->s.input_state=0;p->s.current_command_id=0;}
}
/* Only the ACK-known visual confirmation is consumed here. Started or
 * unknown synth states must never be converted into cleanup permission. */
static void end_visual_wait(NG2Controller *p){
    p->motion_wait.active=0;p->s.input_state=0;p->s.current_command_id=0;
}
static void finish(NG2Controller *p,uint64_t now,int reason){
    if(reason!=NG2_REASON_LIMIT||p->handoff.kind!=NG2_HANDOFF_RESTARTED_BUDGET)restart_yield_invalidate(p);
    if(!p->s.terminal&&(reason!=NG2_REASON_LIMIT||!p->handoff.kind))p->handoff_fault=1;
    if(!p->s.terminal&&!p->finish_requested){
        freeze_stop_detail(p,now,reason,NULL);
    }
    p->preparation_epoch=0;
    p->cycle_framing_credit=0;
    p->opened_entry_parent=p->opened_entry_recovery_ns=0;
    p->passage_unlocalized_gold=p->initial_candidate_unlocalized=0;p->passage_initial_reanchor=0;
    clear_stationary_wait(p);
    p->edge_validated_capture_id=0;
    p->stationary_gate_retry_waiting=NG2_GATE_RETRY_NONE;p->stationary_gate_retry_proof_id=0;
    p->gate_refresh_state=NG2_GATE_REFRESH_NONE;p->gate_refresh_proof_id=0;
    p->terrain_refresh_active=0;
    p->observation_refresh_active=0;p->passage_release_proof_id=0;
    if(p->s.terminal)return;
    if(!p->finish_requested){p->finish_requested=1;p->finish_ns=now;p->s.reason=reason;}
    if(reason==NG2_REASON_GOODS){p->s.reason=reason;p->s.goods=1;}
    if(p->command.kind==NG2_ACTION_MOVE)p->motion_wait.active=0;
    /* Goods latch before matching-prefix admission. Preserve a known ACK just
     * long enough to credit real motion in that same eligible frame, then
     * close even UNKNOWN/TWEEN without postponing the holding pause. */
    if(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE&&reason!=NG2_REASON_GOODS)end_visual_wait(p);
    if(p->s.input_state==1)not_sent(p,now,p->s.reason);
    p->s.phase=NG2_PHASE_FINISH;
}
static int guards(int front,int locked,int owner){
    return owner!=1?NG2_REASON_OWNER_PAUSED:locked!=0?NG2_REASON_LOCKED:front!=1?NG2_REASON_FOREGROUND:0;
}
static int fresh(const NG2Controller *p,uint64_t now){
    return p->have_scene&&p->s.last_capture_start_ns<=now&&p->s.last_capture_end_ns<=now
        &&now-p->s.last_capture_start_ns<=FRESH;
}
/* A synth ACK is not proof that the game can accept its next UI action.
 * Require a current floor captured after the proposed UI settling interval.
 * Subtraction keeps both elapsed checks valid near the native clock limit. */
static int pause_ui_ready(const NG2Controller *p,uint64_t now){
    size_t i;
    if(!p->have_scene||p->scene.state!=NG2_FLOOR
        ||p->last_observed_prefix!=p->s.last_completed_id)return 0;
    if(!p->finish_requested&&!cycle_holding(p)&&(p->initial_view_pending||p->initial_candidate_waiting))return 0;
    for(i=p->event_count;i>0;--i){
        const NG2ControllerEvent *e=&p->events[i-1];
        if(e->outcome==2&&(e->command.kind==NG2_ACTION_RESUME||e->command.kind==NG2_ACTION_RESTART)){
            return now>=e->end_ns&&now-e->end_ns>=UI_SETTLE_NS
                &&p->s.last_capture_start_ns>=e->end_ns
                &&p->s.last_capture_start_ns-e->end_ns>=UI_SETTLE_NS;
        }
    }
    return 1; /* Already on the floor, without a preceding UI transition. */
}
static void clear_model(NG2Controller *p){
    p->stationary_qualification.valid=0;
    memset(&p->model,0,sizeof(p->model));p->sample_count=0;p->s.beat_period_ns=0;p->beat_failed=0;
    p->model_capture_id=0;
}
static int level_inputs(const NG2Controller *p){return p->s.inputs-p->level_input_base;}
static int level_moves(const NG2Controller *p){return p->s.moves-p->level_move_base;}
static int initial_recoverable(const NG2Controller *p){
    return !p->finish_requested&&!p->s.terminal&&!p->s.goods&&p->s.walk_started_ns
        &&!level_inputs(p)&&!level_moves(p)&&!p->s.lead_confirmed
        &&(p->s.input_state==0||(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE));
}
static uint64_t sync_deadline(const NG2Controller *p){
    uint64_t deadline=minimum(p->sync_ns+12*SECOND,session_bound(p));
    if(p->s.walk_started_ns)deadline=minimum(deadline,p->s.walk_started_ns+45*SECOND);
    if(p->stationary_wait_parent)deadline=minimum(deadline,p->stationary_wait_parent);
    else if(p->gate_refresh_state)deadline=minimum(deadline,p->gate_refresh_deadline);
    if(p->opened_entry_parent)deadline=minimum(deadline,p->opened_entry_parent);
    if(p->entry.active&&p->entry.parent)deadline=minimum(deadline,p->entry.parent);
    if(p->upper.active&&p->upper.parent)deadline=minimum(deadline,p->upper.parent);
    return deadline;
}
static void recovery_record(NG2Controller *p,int reason,int clock,uint64_t at,uint64_t capture){
    NG2ControllerRecoveryTrace *row;size_t slot=p->recovery.record_count?1:0;
    row=&p->recovery.records[slot];memset(row,0,sizeof(*row));
    row->sequence=++p->recovery.record_count;row->episode_id=p->recovery.episode_id;
    row->reason=reason;row->clock=clock;row->at_ns=at;row->capture_id=capture;
    row->command_id=p->command.id;
    row->abandoned_target_ns=p->recovery_slot_target?p->recovery_slot_target:
        p->initial_slot_target?p->initial_slot_target:p->s.next_target_ns;
    if(!row->abandoned_target_ns)row->abandoned_target_ns=p->command.target_ns;
    row->sync_deadline_ns=sync_deadline(p);row->model=p->model;
    row->sample_count=(int32_t)p->sample_count;
    memcpy(p->recovery_samples[slot],p->samples,p->sample_count*sizeof(p->samples[0]));
    p->recovery.dropped_records=p->recovery.record_count>2?p->recovery.record_count-2:0;
}
static void clear_recovery_slot(NG2Controller *p){
    p->recovery_slot_target=p->recovery_slot_not_before=p->recovery_slot_period=0;
    p->recovery_slot_deadline=p->recovery_slot_schedule=p->recovery_slot_visual=0;
}
static void clear_slots(NG2Controller *p){
    p->stationary_qualification.valid=0;
    p->initial_slot_target=p->initial_slot_not_before=p->initial_slot_period=0;
    p->initial_slot_deadline=p->initial_slot_motion_deadline=p->initial_slot_visual_deadline=0;
    p->initial_ticket_valid=p->replan_pending=0;memset(&p->initial_ticket,0,sizeof(p->initial_ticket));
    p->initial_period=p->initial_visual_deadline=0;
    p->continuous_ticket_valid=p->continuous_pending=p->continuous_chain_count=0;
    p->continuous_period=p->continuous_motion_deadline=p->continuous_schedule_deadline=0;
    memset(&p->continuous_ticket,0,sizeof(p->continuous_ticket));
    p->next_nominal=p->next_deadline=p->next_period=p->next_update_deadline=0;p->s.next_target_ns=0;
    p->motion_reference_present=p->motion_reference_valid=p->motion_reference_reissued=0;
    p->preparation_epoch=0;clear_recovery_slot(p);
}
static int initial_recover(NG2Controller *p,int reason,int clock,uint64_t now,uint64_t capture){
    uint64_t gate_now=clock==NG2_RECOVERY_CAPTURE_END?maximum(now,p->observe_now):now;
    if(!initial_recoverable(p))return 0;
    if(gate_now>=sync_deadline(p)){
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,gate_now==now?clock:NG2_RECOVERY_ACTUAL_COMMIT,gate_now,capture);
        finish(p,gate_now,NG2_REASON_BEAT);return 1;
    }
    if(p->recovery.mode!=NG2_RECOVERY_INITIAL){
        ++p->recovery.episode_id;++p->recovery.initial_reacquisitions;
        p->recovery.mode=NG2_RECOVERY_INITIAL;
    }
    recovery_record(p,reason,clock,now,capture);
    not_sent(p,now,reason==NG2_RECOVERY_UNSENT_DEADLINE||reason==NG2_RECOVERY_PREPARATION?
        NG2_REASON_LATE:NG2_REASON_BEAT);
    clear_slots(p);clear_model(p);memset(&p->command,0,sizeof(p->command));
    p->s.current_command_id=0;p->s.input_state=0;p->s.phase=NG2_PHASE_SYNC;
    return 1;
}
static void phase_failure(NG2Controller *p,int reason,uint64_t at,uint64_t capture){
    if(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE){
        if(!p->visual_phase_failed)recovery_record(p,NG2_RECOVERY_VISUAL_PHASE,NG2_RECOVERY_CAPTURE_END,at,capture);
        p->visual_phase_failed=p->beat_failed=1;return;
    }
    if(initial_recover(p,reason,NG2_RECOVERY_CAPTURE_END,at,capture))return;
    if(p->recovery.mode==NG2_RECOVERY_POST_MOVE){
        recovery_record(p,reason,NG2_RECOVERY_CAPTURE_END,at,capture);
        clear_recovery_slot(p);clear_model(p);p->s.next_target_ns=0;return;
    }
    p->beat_failed=1;
}
static int same_gold(const NG2Scene *a,const NG2Scene *b){
    int i;for(i=0;i<NG2_TILE_COUNT;++i)if((a->tiles[i]==NG2_TILE_GOLD)!=(b->tiles[i]==NG2_TILE_GOLD))return 0;
    return 1;
}
static int gate_at(const NG2Scene *s,int x,int y){
    return (tile(s,x-1,y)==NG2_TILE_GOLD&&tile(s,x+1,y)==NG2_TILE_GOLD)
        ||(tile(s,x,y-1)==NG2_TILE_GOLD&&tile(s,x,y+1)==NG2_TILE_GOLD);
}
static int safe_floor(const NG2Scene *s,int direction){
    int d,x=dx[direction],y=dy[direction],gold=0;
    if(s->state!=NG2_FLOOR||s->goods!=NG2_GOODS_UNKNOWN||tile(s,0,0)!=NG2_TILE_FLOOR
        ||tile(s,x,y)!=NG2_TILE_FLOOR||gate_at(s,x,y))return 0;
    for(d=0;d<NG2_TILE_COUNT;++d)gold+=s->tiles[d]==NG2_TILE_GOLD;
    if(!gold)return 0;
    for(d=0;d<5;++d)if(protected_at(s,dx[d],dy[d])||protected_at(s,x+dx[d],y+dy[d]))return 0;
    return 1;
}
/* A passage is an observed no-gold route, never a synthetic GOLD cell. */
static void passage_mouth(int bit,int *x,int *y){
    if(bit<5){*x=bit-2;*y=-3;}else{*x=-3;*y=bit-7;}
}
static void passage_goal(const NG2Controller *p,int *x,int *y){
    passage_mouth(p->passage_bit,x,y);
    if(p->passage_bit<5)--*y;else --*x;
}
static int has_gold_tiles(const NG2Scene *s){
    int i;for(i=0;i<NG2_TILE_COUNT;++i)if(s->tiles[i]==NG2_TILE_GOLD)return 1;
    return 0;
}
static int actual_gold(const NG2Scene *s){
    return s->state==NG2_FLOOR&&(s->gold_state==NG2_GOLD_EDGE_DOWN
        ||(s->gold_state==NG2_GOLD_CANDIDATE&&has_gold_tiles(s)));
}
static int clear_gold_floor(const NG2Scene *s){
    return s->state==NG2_FLOOR&&s->gold_state==NG2_GOLD_CLEAR
        &&s->goods==NG2_GOODS_UNKNOWN&&!has_gold_tiles(s);
}
/* This qualifies a current clear source only after this controller observed
 * an actual RESTART into the current level. It never creates skip authority. */
static int clear_handoff_scene(const NG2Scene *scene){
    int i;
    if(!clear_gold_floor(scene)||tile(scene,0,0)!=NG2_TILE_FLOOR||ng2_passage_candidates(scene))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(scene->protected_cells[i]||scene->tiles[i]==NG2_TILE_ITEM)return 0;
    return 1;
}
static int handoff_original_bounds(const NG2Controller *p,uint64_t now){
    return now<session_bound(p)
        &&(!p->s.walk_started_ns||now<p->s.walk_started_ns+45*SECOND);
}
/* Qualification can only be revoked here. A later clear frame never restores
 * a B marker contradicted before or after its cleanup PAUSE was published. */
static void revoke_clear_handoff(NG2Controller *p,const NG2Scene *accepted,uint64_t now){
    if(p->handoff.kind==NG2_HANDOFF_CLEAR_SEARCH_LIMIT&&!p->s.terminal
        &&(!handoff_original_bounds(p,now)
            ||(accepted&&accepted->state==NG2_FLOOR&&!clear_handoff_scene(accepted))))p->handoff_fault=1;
}
static int clear_handoff_source(NG2Controller *p,uint64_t now){
    if(!p->cycle_enabled||p->handoff_fault||p->cycle.state!=NG2_CYCLE_SEARCH
        ||p->cycle.pending||p->cycle.candidate_latched||p->cycle_storage_error||p->cycle_restart_unproved
        ||p->s.input_state||p->s.x||p->s.y||p->s.lead_confirmed||level_inputs(p)||level_moves(p)
        ||p->s.restarts<12||!p->restart_intent||p->restart_pending
        ||p->initial_view_pending||p->initial_candidate_waiting||p->initial_scene_reacquiring
        ||p->passage_active||p->passage_pending||p->passage_wait_kind||p->passage_unresolved
        ||p->passage_unlocalized_gold||p->initial_candidate_unlocalized||p->passage_inspected||p->passage_closed
        ||p->stationary_wait_active||p->gate_refresh_state||p->replan_pending||p->continuous_pending
        ||!p->last_level_restart_id||!p->last_level_restart_capture
        ||p->last_level_restart_count!=p->s.restarts
        ||p->last_level_restart_prefix!=p->s.last_completed_id
        ||p->last_level_restart_id!=p->s.last_completed_id
        ||p->s.last_capture_id<p->last_level_restart_capture
        ||p->last_observed_prefix!=p->s.last_completed_id||!fresh(p,now)
        ||!handoff_original_bounds(p,now)||!clear_handoff_scene(&p->scene))return 0;
    /* A completed earlier negative can remain in SEARCH. It is never enough
     * alone: the new-level/current-source proof above is still mandatory. */
    if(p->cycle.job_id&&(p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_NEGATIVE
        ||p->cycle.coverage!=NG2_RING_COVERAGE_COMPLETE||!p->cycle.durable_ns
        ||!p->cycle.outcome_ns||p->cycle.partial))return 0;
    return 1;
}
static void remember_level_restart(NG2Controller *p,uint64_t command,uint64_t capture,uint64_t prefix){
    p->last_level_restart_id=command;p->last_level_restart_capture=capture;
    p->last_level_restart_prefix=prefix;p->last_level_restart_count=p->s.restarts;
}
static void mint_clear_handoff(NG2Controller *p,uint64_t now){
    NG2ControllerStopDetail basis;
    if(p->handoff.kind||!clear_handoff_source(p,now))return;
    p->handoff.kind=NG2_HANDOFF_CLEAR_SEARCH_LIMIT;p->handoff.reason=NG2_REASON_LIMIT;
    p->handoff_initial_ns=now;p->handoff_initial_source=p->s.last_capture_id;
    p->handoff_initial_prefix=p->s.last_completed_id;
    live_stop_detail(p,&basis);basis.source_capture_id=p->s.last_capture_id;
    basis.observed_capture_id=p->s.last_capture_id;basis.validation=NG2_REVALIDATE_BUDGET;
    freeze_stop_detail(p,now,NG2_REASON_LIMIT,&basis);
}
static void bind_clear_handoff_pause(NG2Controller *p,uint64_t now){
    if(p->handoff.kind!=NG2_HANDOFF_CLEAR_SEARCH_LIMIT||p->handoff_pause_bound||p->handoff_fault)return;
    if(!clear_handoff_source(p,now)){p->handoff_fault=1;return;}
    p->handoff_pause_bound=1;p->handoff_pause_command=p->command.id;
    p->handoff.qualified_ns=now;p->handoff.source_capture_id=p->command.source_capture_id;
    p->handoff.source_prefix=p->s.last_completed_id;p->handoff.completed_prefix=p->command.id;
}
static void mint_negative_handoff(NG2Controller *p,uint64_t now){
    if(!p->cycle_enabled||p->handoff.kind||p->handoff_fault||p->cycle_storage_error
        ||p->cycle_restart_unproved||p->cycle.pending||p->cycle.candidate_latched
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_NEGATIVE
        ||p->cycle.coverage!=NG2_RING_COVERAGE_COMPLETE||p->cycle.partial
        ||!p->cycle.durable_ns||!p->cycle.pause_capture_id||p->s.input_state)return;
    p->handoff.kind=NG2_HANDOFF_NEGATIVE_LIMIT;p->handoff.reason=NG2_REASON_LIMIT;
    p->handoff.qualified_ns=now;p->handoff.source_capture_id=p->cycle.capture_id;
    p->handoff.source_prefix=p->cycle.prefix;p->handoff.pause_capture_id=p->cycle.pause_capture_id;
    p->handoff.completed_prefix=p->s.last_completed_id;
    p->handoff_pause_command=p->s.last_completed_id;p->handoff_pause_bound=1;
}
void ng2_controller_handoff(const NG2Controller *p,NG2ControllerHandoff *out){
    size_t i;const NG2ControllerEvent *pause=NULL;
    if(!out)return;
    if(!p){memset(out,0,sizeof(*out));return;}
    *out=p->handoff;out->abi_version=1;out->struct_size=sizeof(*out);out->allowed=0;
    if(!p->handoff.kind||p->handoff_fault||!p->handoff_pause_bound||!p->s.terminal
        ||p->s.reason!=NG2_REASON_LIMIT||p->s.input_state||!p->s.paused
        ||p->scene.state!=NG2_PAUSE||p->last_observed_prefix!=p->s.last_completed_id
        ||p->s.last_completed_id!=p->handoff_pause_command)return;
    for(i=p->event_count;i>0;--i)if(p->events[i-1].command.id==p->handoff_pause_command){pause=&p->events[i-1];break;}
    if(!pause||pause->command.kind!=NG2_ACTION_PAUSE||pause->outcome!=2
        ||!pause->begin_ns||pause->end_ns<pause->begin_ns||!pause->observed_capture_id
        ||p->s.last_capture_start_ns<pause->end_ns)return;
    if(p->handoff.kind==NG2_HANDOFF_RESTARTED_BUDGET){
        const NG2RestartYield *y=&p->restart_yield;
        if(!restart_yield_basis(p,p->s.ended_ns)||p->cycle.pending||p->cycle.candidate_latched
            ||(y->required&~y->done)||y->pause!=pause->command.id
            ||y->permit_capture!=pause->command.source_capture_id
            ||y->permit_start!=pause->command.source_start_ns
            ||p->handoff.source_capture_id!=y->permit_capture
            ||p->handoff.source_prefix!=y->s.restart_command_id)return;
    }
    out->pause_capture_id=pause->observed_capture_id;out->completed_prefix=pause->command.id;
    out->allowed=1;
}
static int passage_goods_protected(const NG2Scene *s){
    int i;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(s->tiles[i]==NG2_TILE_ITEM||(s->protected_cells[i]&&s->tiles[i]!=NG2_TILE_GOLD))return 1;
    return 0;
}
/* A clipped positive reaction has no map-cell location. It may support an
 * already observed passage, but it is never CLEAR or permission to restart. */
static int unlocalized_gold_floor(const NG2Scene *s){
    return s->state==NG2_FLOOR&&s->gold_state==NG2_GOLD_CANDIDATE&&s->gold_peak>=135
        &&s->goods==NG2_GOODS_UNKNOWN&&!has_gold_tiles(s)&&tile(s,0,0)==NG2_TILE_FLOOR
        &&!passage_goods_protected(s);
}
static int passage_floor(const NG2Scene *s){
    return clear_gold_floor(s)||unlocalized_gold_floor(s);
}
/* The normal producer's indeterminate reaction band is observation data,
 * never new-input or no-shop authority. It may accompany a known ACK while
 * the unchanged motion comparator finishes assessing that existing input. */
static int uncertain_passage_floor(const NG2Scene *s){
    int i;
    if(s->state!=NG2_FLOOR||s->goods!=NG2_GOODS_UNKNOWN
        ||s->gold_state!=NG2_GOLD_UNKNOWN||s->gold_peak<100||s->gold_peak>=135
        ||tile(s,0,0)!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(s->tiles[i]==NG2_TILE_GOLD||s->tiles[i]==NG2_TILE_ITEM||s->protected_cells[i])return 0;
    return 1;
}
static int initial_uncertain_floor(const NG2Controller *p,const NG2Scene *scene){
    return (p->initial_view_pending||p->initial_candidate_waiting)
        &&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_UNKNOWN
        &&!passage_goods_protected(scene)&&!actual_gold(scene)&&!clear_gold_floor(scene)
        &&!(unlocalized_gold_floor(scene)&&ng2_passage_candidates(scene));
}
static int choose_step(const NG2Controller *p,const NG2Scene *s,NG2Decision *out){
    int x,y;
    if(p->passage_active){
        if(p->passage_bit<0||p->passage_bit>=10){memset(out,0,sizeof(*out));return 0;}
        passage_mouth(p->passage_bit,&x,&y);
        return ng2_choose_passage(s,p->s.x,p->s.y,x,y,out)>0;
    }
    return ng2_choose(s,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,out);
}
static int safe_step(const NG2Controller *p,const NG2Scene *s,int d){
    NG2Decision out;int i;
    if(!p->passage_active)return safe_floor(s,d);
    if(d<1||d>4||!passage_floor(s)
        ||s->goods!=NG2_GOODS_UNKNOWN||tile(s,0,0)!=NG2_TILE_FLOOR
        ||tile(s,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!choose_step(p,s,&out)||out.direction!=d||out.reason!=10||out.obstacle!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<5;++i)
        if(protected_at(s,dx[i],dy[i])||protected_at(s,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    return 1;
}
static int select_passage(NG2Controller *p,const NG2Scene *s){
    int i,best=-1,length=0;
    for(i=0;i<10;++i)if(p->passage_pending&(1u<<i)){
        NG2Decision out;int x,y,n;
        passage_mouth(i,&x,&y);n=ng2_choose_passage(s,p->s.x,p->s.y,x,y,&out);
        if(n>0&&(best<0||n<length)){best=i;length=n;}
    }
    if(best<0)for(i=0;i<10;++i)if(p->passage_pending&(1u<<i)){best=i;break;}
    p->passage_bit=best;return best>=0;
}
static void initial_candidate_support(const NG2Scene *scene,unsigned char out[30]){
    int bit,x,y;
    for(bit=0;bit<10;++bit){
        passage_mouth(bit,&x,&y);
        out[3*bit]=(unsigned char)tile(scene,x,y);
        out[3*bit+1]=(unsigned char)tile(scene,x+(bit<5?-1:0),y+(bit<5?0:-1));
        out[3*bit+2]=(unsigned char)tile(scene,x+(bit<5?1:0),y+(bit<5?0:1));
    }
}
static void remember_initial_candidate(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t end,uint64_t prefix){
    p->initial_candidate_id=id;p->initial_candidate_end=end;p->initial_candidate_prefix=prefix;
    p->initial_candidate_mask=ng2_passage_candidates(scene);
    p->initial_candidate_unlocalized=unlocalized_gold_floor(scene);
    initial_candidate_support(scene,p->initial_candidate_tiles);
}
/* A changed fingerprint proves a restart, not completion of its drawing.
 * This fixed first-floor epoch belongs to the level and is never refreshed. */
static void begin_initial_view(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end){
    p->initial_view_id=id;p->initial_view_start=start;p->initial_view_end=end;
    p->initial_view_pending=!actual_gold(scene);p->initial_candidate_waiting=0;
    p->initial_candidate_id=0;p->initial_candidate_unlocalized=0;
    p->sync_ns=end;
}
/* Closest epoch on the same physical beat; no next-beat search is allowed. */
static uint64_t closest(const NG2BeatModel *m,uint64_t target){
    uint64_t forward=m->epoch_ns>=target?(m->epoch_ns-target)%m->period_ns
        :(m->period_ns-(target-m->epoch_ns)%m->period_ns)%m->period_ns;
    return forward<=m->period_ns/2?target+forward:target-(m->period_ns-forward);
}
static int corrected(const NG2Controller *p,uint64_t nominal,uint64_t period,uint64_t *out){
    uint64_t target=closest(&p->model,nominal),delta=target>=nominal?target-nominal:nominal-target;
    if((double)delta>.08*(double)period)return 0;
    *out=target;return 1;
}
/* A slot plans only one initial physical beat. It grants no scene/input
 * authority and is never selected again after a late or invalid observation. */
static int initial_slot_active(const NG2Controller *p){
    return p->initial_slot_target&&!level_inputs(p)&&!level_moves(p)&&!p->s.lead_confirmed;
}
/* A confirmed parent's next ordinal has no command yet. Track one physical
 * beat from that immutable nominal/period, pairing its current target/window.
 * Once reserved (including a pending reissue), only the ticket's guards apply. */
static int update_next_slot_candidate(NG2Controller *p){
    uint64_t target,not_before;
    if(p->s.input_state!=0||p->replan_pending||p->continuous_pending||p->beat_failed
        ||!p->next_nominal||!valid_time(p->next_nominal)||!p->next_period
        ||!ng2_beat_model_valid(&p->model)
        ||!corrected(p,p->next_nominal,p->next_period,&target)
        ||!valid_time(target)||target<p->s.lead_ns)return 0;
    not_before=target-p->s.lead_ns;
    if(not_before>=NS_LIMIT-10000000)return 0;
    p->s.next_target_ns=target;
    p->next_deadline=not_before+10000000;
    return 1;
}
static int unreserved_next_slot(const NG2Controller *p){
    return !p->finish_requested&&p->s.lead_confirmed&&p->s.moves>0&&p->s.input_state==0
        &&!p->proof_deadline&&p->recovery.mode!=NG2_RECOVERY_POST_MOVE
        &&!p->replan_pending&&!p->continuous_pending&&p->next_nominal&&p->next_period;
}
static int next_slot_expired(const NG2Controller *p,uint64_t now){
    uint64_t deadline=p->next_deadline;
    if(!unreserved_next_slot(p))return 0;
    if(p->next_update_deadline)deadline=minimum(deadline,p->next_update_deadline);
    return now>deadline;
}
static void add_sample(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t end){
    NG2BeatSample sample;NG2BeatModel updated;size_t i,drop;
    uint64_t previous=p->model.last_ns;
    if(p->visual_phase_failed&&p->s.input_state==3)return;
    if(next_slot_expired(p,maximum(end,p->last_now))){finish(p,maximum(end,p->last_now),NG2_REASON_LATE);return;}
    if(!scene->beat_valid||!ng2_make_sample(scene->beat_remaining,scene->beat_spacing,scene->beat_center,start,end,&sample))return;
    if(p->sample_count&&sample.midpoint_ns<=p->samples[p->sample_count-1].midpoint_ns)return;
    /* Observe has no analysis/commit clock. Keep every pre-update deadline
     * until tick supplies that clock, so delayed commits cannot revive a slot. */
    if(unreserved_next_slot(p)&&(!p->next_update_deadline||p->next_deadline<p->next_update_deadline))
        p->next_update_deadline=p->next_deadline;
    while(p->sample_count&&sample.midpoint_ns-p->samples[0].midpoint_ns>20*SECOND){
        memmove(p->samples,p->samples+1,(--p->sample_count)*sizeof(sample));}
    p->samples[p->sample_count++]=sample;
    if(p->sample_count>12){uint64_t density=UINT64_MAX;drop=0;
        for(i=1;i+1<p->sample_count;++i)if(p->samples[i].midpoint_ns!=previous){
            uint64_t width=p->samples[i+1].midpoint_ns-p->samples[i-1].midpoint_ns;
            if(width<density){density=width;drop=i;}}
        /* First and latest survive thinning; previous model.last survives too. */
        if(!drop){phase_failure(p,NG2_RECOVERY_TRACK,end,id);return;}
        memmove(p->samples+drop,p->samples+drop+1,(p->sample_count-drop-1)*sizeof(sample));--p->sample_count;
    }
    if(ng2_beat_model_valid(&p->model)){
        if(ng2_beat_track(&p->model,p->samples,p->sample_count,&updated)){
            p->model=updated;p->s.beat_period_ns=updated.period_ns;p->model_capture_id=id;
        }else {phase_failure(p,NG2_RECOVERY_TRACK,end,id);return;}
    }
    if(!ng2_beat_model_valid(&p->model)&&p->sample_count>=4
        &&sample.midpoint_ns-p->samples[0].midpoint_ns>=2*SECOND
        &&ng2_beat_fit(p->samples,p->sample_count,&updated)){
        p->model=updated;p->s.beat_period_ns=updated.period_ns;p->model_capture_id=id;
    }
    if(p->s.lead_confirmed&&ng2_beat_model_valid(&p->model)){
        uint64_t target;
        if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE){
            if(!corrected(p,p->command.target_ns,p->command_period,&target))
                phase_failure(p,NG2_RECOVERY_ALIGNMENT,end,id);
        }else if(p->next_nominal){
            if(p->s.input_state==0&&!p->replan_pending&&!p->continuous_pending){
                if(!update_next_slot_candidate(p))phase_failure(p,NG2_RECOVERY_ALIGNMENT,end,id);
            }else if(!corrected(p,p->next_nominal,p->next_period,&target))
                phase_failure(p,NG2_RECOVERY_ALIGNMENT,end,id);
        }
    }
    if(initial_slot_active(p)){
        uint64_t aligned;
        if(!ng2_beat_model_valid(&p->model)
            ||!corrected(p,p->initial_slot_target,p->initial_slot_period,&aligned))
            phase_failure(p,NG2_RECOVERY_ALIGNMENT,end,id);
    }
}
static void reset_level(NG2Controller *p,uint64_t end){
    memset(&p->upper_partial_refresh,0,sizeof(p->upper_partial_refresh));
    p->cycle_retry_only=p->cycle_retry_waiting=p->cycle_retry_used=p->cycle_retry_blocked=p->cycle_late_worker=0;
    p->cycle_retry_data=p->cycle_up_history=0;
    p->cycle_current_used=p->cycle_current_active=p->cycle_current_invalid=p->cycle_current_proofs=0;
    p->cycle_current_partial=0;memset(p->cycle_current_potential,0,NG2_TILE_COUNT);
    /* Session counters, all used allowances, trace history, IDs, ordinal and
     * the first walk horizon survive a proven new game level. */
    p->level_input_base=p->s.inputs;p->level_move_base=p->s.moves;
    p->cycle_partial_rebind_used=p->cycle_full_framing=p->cycle_full_spent=0;
    p->cycle_full_source_valid=p->cycle_full_data_active=p->cycle_full_data_blocked=0;
    memset(&p->entry,0,sizeof(p->entry));
    memset(&p->lower,0,sizeof(p->lower));
    memset(&p->upper,0,sizeof(p->upper));
    p->last_level_restart_id=p->last_level_restart_capture=p->last_level_restart_prefix=0;
    p->last_level_restart_count=0;
    if(!p->first_stop.valid){
        p->diagnostic_capture_id=0;p->diagnostic_validation=0;
        memset(&p->diagnostic_motion,0,sizeof(p->diagnostic_motion));
    }
    p->s.x=p->s.y=0;p->s.lead_confirmed=0;p->s.lead_ns=leads[0];p->lead_index=0;
    memset(p->visits,0,sizeof(p->visits));p->visits[16*33+16]=1;
    memset(&p->entrance,0,sizeof(p->entrance));
    clear_slots(p);clear_model(p);memset(&p->command,0,sizeof(p->command));
    p->s.current_command_id=0;p->s.input_state=0;
    p->proof_deadline=p->proof_capture_id=p->latest_verified_ns=0;
    p->proof_reacquire=p->visual_phase_failed=0;p->command_sync_deadline=0;
    p->have_anchor=p->retune_direction=0;memset(&p->retune_anchor,0,sizeof(p->retune_anchor));
    p->gate_refresh_state=NG2_GATE_REFRESH_NONE;p->gate_refresh_proof_id=0;
    clear_stationary_wait(p);
    p->terrain_refresh_active=p->observation_refresh_active=0;
    p->stationary_gate_retry_waiting=NG2_GATE_RETRY_NONE;p->stationary_gate_retry_proof_id=0;
    p->stationary_gate_recovery_pending=0;p->edge_validated_capture_id=0;
    p->schedule_deadline=p->continuous_schedule_deadline=0;
    p->motion_retry_start_ns=p->motion_retry_last_ns=0;memset(&p->motion_wait,0,sizeof(p->motion_wait));
    p->recovery.mode=NG2_RECOVERY_NORMAL;
    p->recovery.schedule_deadline_ns=p->recovery.visual_deadline_ns=p->recovery.ack_ns=0;
    p->passage_active=0;p->passage_bit=-1;p->passage_wait_kind=0;p->passage_initial_reanchor=0;
    p->passage_unlocalized_gold=p->initial_candidate_unlocalized=0;
    p->opened_entry_parent=p->opened_entry_recovery_ns=0;
    p->passage_pending=p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
    p->passage_wait_deadline=p->passage_wait_horizon=p->passage_release_proof_id=p->passage_anchor_id=p->passage_anchor_start=p->passage_anchor_end=0;
    p->initial_view_id=p->initial_view_start=p->initial_view_end=0;
    p->initial_candidate_id=p->initial_candidate_end=p->initial_candidate_prefix=0;
    p->initial_candidate_mask=0;p->initial_view_pending=p->initial_candidate_waiting=0;
    p->initial_scene_reacquiring=0;memset(&p->initial_scene_previous,0,sizeof(p->initial_scene_previous));
    memset(p->initial_candidate_tiles,0,sizeof(p->initial_candidate_tiles));
    p->restart_baseline_valid=p->restart_intent=0;p->sync_ns=end;p->transition_ns=end;p->s.phase=NG2_PHASE_SEARCH;
}
static void start_floor(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t end){
    uint64_t epoch=p->initial_view_end?p->initial_view_end:end;
    if(scene->state!=NG2_FLOOR)return;
    if(unlocalized_gold_floor(scene))p->passage_unlocalized_gold=1;
    if((scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))&&!actual_gold(scene)){
        finish(p,end,NG2_REASON_PARTIAL_GOODS);return;
    }
    if(initial_uncertain_floor(p,scene))return;
    if(actual_gold(scene)){
        p->passage_unlocalized_gold=0;
        p->passage_active=0;p->passage_wait_kind=0;p->restart_intent=0;
        if(!p->s.walk_started_ns)p->s.walk_started_ns=epoch;
        p->sync_ns=epoch;clear_model(p);p->s.phase=NG2_PHASE_SYNC;
    }else if(scene->gold_state==NG2_GOLD_CLEAR||unlocalized_gold_floor(scene)){
        if(!passage_floor(scene)){finish(p,end,NG2_REASON_SCREEN);return;}
        if(!p->initial_candidate_id)remember_initial_candidate(p,scene,id,end,p->s.last_completed_id);
        p->passage_pending=ng2_passage_candidates(scene);
        if(p->passage_pending){
            if(unlocalized_gold_floor(scene))p->passage_unlocalized_gold=1;
            p->passage_active=1;p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
            select_passage(p,scene);
            if(!p->s.walk_started_ns)p->s.walk_started_ns=epoch;
            p->sync_ns=epoch;clear_model(p);p->s.phase=NG2_PHASE_SYNC;
        }else if(clear_gold_floor(scene)){p->restart_intent=1;p->s.phase=NG2_PHASE_FLOOR;}
        else finish(p,end,NG2_REASON_NO_PATH);
    }else if(scene->gold_state==NG2_GOLD_CANDIDATE)finish(p,end,NG2_REASON_SCREEN);
}
/* Initial-room evidence may be reclassified only before a physical input.
 * After movement the original world mouth must survive camera translation.
 * Unknown/disappearing support retires an unsent ticket but is not a wall. */
/* This path retires input authority, never proves displacement from the old
 * source. A new pair must independently support a new source and initial slot.
 * It shares the existing two-replan allowance and the original sync epoch. */
static int start_initial_scene_reacquisition(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    const NG2ControllerEvent *e=event(p);
    if(!initial_recoverable(p)||p->replan_count>=2||!p->passage_active||p->passage_wait_kind
        ||p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||!p->command.id
        ||p->s.current_command_id!=p->command.id||!e||memcmp(&e->command,&p->command,sizeof(p->command))
        ||e->begin_ns||e->outcome||p->s.x||p->s.y||p->entrance.valid
        ||!p->initial_ticket_valid||p->replan_pending||p->continuous_pending
        ||p->initial_scene_reacquiring||p->initial_view_pending||p->initial_candidate_waiting
        ||!passage_floor(&p->before)||p->command_choice.reason!=10
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_UNKNOWN||passage_goods_protected(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||id<=p->command.source_capture_id
        ||prefix!=p->s.last_completed_id||start<p->command.source_start_ns
        ||now<end||now<start||now-start>FRESH)return 0;
    if(now>=sync_deadline(p)){finish(p,now,NG2_REASON_BEAT);return 1;}
    if(p->recovery.mode!=NG2_RECOVERY_INITIAL){
        ++p->recovery.episode_id;++p->recovery.initial_reacquisitions;
        p->recovery.mode=NG2_RECOVERY_INITIAL;
    }
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    ++p->replan_count;
    not_sent(p,end,NG2_REASON_SCREEN);clear_slots(p);clear_model(p);
    memset(&p->command,0,sizeof(p->command));p->motion_wait.active=0;
    p->initial_scene_reacquiring=1;p->initial_candidate_waiting=1;p->initial_candidate_id=0;
    p->passage_release_proof_id=0;p->s.phase=NG2_PHASE_SYNC;
    return 1;
}
/* A settled passage can fade before there is any MOVE/slot to retire. Freeze
 * its known candidate as data, revoke the old fit, and use only a new pair.
 * Mode two cannot turn missing candidate support into a negative restart. */
static int start_prefirst_scene_reacquisition(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Decision choice;unsigned char support[30],source_support[30];int bit;
    if(!initial_recoverable(p)||p->s.phase!=NG2_PHASE_SYNC||p->replan_count>=2
        ||!p->passage_active||!p->passage_pending||p->passage_bit<0||p->passage_bit>=10
        ||!(p->passage_pending&(UINT32_C(1)<<p->passage_bit))||p->passage_wait_kind
        ||p->s.x||p->s.y||p->entrance.valid||p->s.input_state||p->s.current_command_id||p->command.id
        ||p->initial_ticket_valid||p->replan_pending||p->continuous_ticket_valid||p->continuous_pending
        ||p->initial_slot_target||p->recovery_slot_target||p->motion_wait.active
        ||p->initial_scene_reacquiring||p->initial_view_pending||p->initial_candidate_waiting
        ||p->restart_pending||p->restart_intent||!p->have_scene||!p->initial_candidate_id
        ||p->initial_candidate_mask!=p->passage_pending
        ||!passage_floor(&p->scene)||!choose_step(p,&p->scene,&choice)||choice.reason!=10
        ||choice.obstacle!=NG2_TILE_FLOOR||!uncertain_passage_floor(scene)
        ||id<=p->s.last_capture_id||start<p->s.last_capture_end_ns
        ||prefix!=p->s.last_completed_id||now<end||now<start||now-start>FRESH)return 0;
    initial_candidate_support(&p->scene,source_support);initial_candidate_support(scene,support);
    for(bit=0;bit<10;++bit)if((p->passage_pending&(UINT32_C(1)<<bit))
        &&memcmp(support+3*bit,source_support+3*bit,3))return 0;
    if(now>=sync_deadline(p)){finish(p,now,NG2_REASON_BEAT);return 1;}
    if(p->recovery.mode!=NG2_RECOVERY_INITIAL){
        ++p->recovery.episode_id;++p->recovery.initial_reacquisitions;
        p->recovery.mode=NG2_RECOVERY_INITIAL;
    }
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    ++p->replan_count;
    p->passage_anchor=p->scene;p->passage_anchor_id=p->s.last_capture_id;
    p->passage_anchor_start=p->s.last_capture_start_ns;p->passage_anchor_end=p->s.last_capture_end_ns;
    clear_slots(p);clear_model(p);
    p->initial_scene_reacquiring=2;p->initial_candidate_waiting=1;p->initial_candidate_id=0;
    p->proof_capture_id=p->proof_deadline=p->passage_release_proof_id=0;
    return 1;
}
static int retained_prefirst_candidate(const NG2Controller *p,const NG2Scene *scene,
    uint32_t mask,const unsigned char support[30]){
    unsigned char frozen[30];NG2Decision before,after;int bit;
    if(!mask||mask!=p->passage_pending||p->passage_bit<0||p->passage_bit>=10)return 0;
    initial_candidate_support(&p->passage_anchor,frozen);
    for(bit=0;bit<10;++bit)if((mask&(UINT32_C(1)<<bit))
        &&memcmp(support+3*bit,frozen+3*bit,3))return 0;
    return choose_step(p,&p->passage_anchor,&before)&&choose_step(p,scene,&after)
        &&before.direction==after.direction&&before.reason==after.reason
        &&before.target_x==after.target_x&&before.target_y==after.target_y&&before.obstacle==after.obstacle;
}
static int recheck_initial_scene(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix){
    NG2Decision before,after;NG2Motion still;unsigned char support[30];uint32_t mask;
    int bit,x,y,d=0,same,actual=actual_gold(scene),prefirst=p->initial_scene_reacquiring==2;
    if(p->observe_now>=sync_deadline(p)){finish(p,p->observe_now,NG2_REASON_BEAT);return 1;}
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_UNKNOWN||passage_goods_protected(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||(!actual&&!passage_floor(scene))){
        p->initial_candidate_id=0;return 1;
    }
    mask=ng2_passage_candidates(scene);initial_candidate_support(scene,support);
    if(p->initial_scene_reacquiring==2&&!actual
        &&!retained_prefirst_candidate(p,scene,mask,support)){
        p->initial_candidate_id=0;return 1;
    }
    if(unlocalized_gold_floor(scene)&&!mask){p->initial_candidate_id=0;return 1;}
    same=p->initial_candidate_id&&id>p->initial_candidate_id&&start>=p->initial_candidate_end
        &&prefix==p->initial_candidate_prefix
        &&actual==actual_gold(&p->initial_scene_previous)
        &&unlocalized_gold_floor(scene)==p->initial_candidate_unlocalized
        &&same_gold(&p->initial_scene_previous,scene)
        &&mask==p->initial_candidate_mask;
    for(bit=0;same&&bit<10;++bit){
        if(((p->passage_pending|mask)&(UINT32_C(1)<<bit))
            &&memcmp(support+3*bit,p->initial_candidate_tiles+3*bit,3))same=0;
        if(!actual&&(p->passage_pending&~mask&(UINT32_C(1)<<bit))){
            passage_mouth(bit,&x,&y);
            if(tile(scene,x,y)!=NG2_TILE_DIRT&&tile(scene,x,y)!=NG2_TILE_STONE)same=0;
        }
    }
    if(same&&actual){
        same=ng2_choose(&p->initial_scene_previous,0,0,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
            &&ng2_choose(scene,0,0,p->visits,NG2_VISIT_COUNT,&p->entrance,&after)
            &&before.direction==after.direction&&before.reason==after.reason
            &&before.target_x==after.target_x&&before.target_y==after.target_y&&before.obstacle==after.obstacle;
        if(same)d=after.direction;
    }else if(same&&mask){
        for(bit=0;bit<10;++bit)if(mask&(UINT32_C(1)<<bit))break;
        passage_mouth(bit,&x,&y);
        same=ng2_choose_passage(&p->initial_scene_previous,0,0,x,y,&before)
            &&ng2_choose_passage(scene,0,0,x,y,&after)
            &&before.direction==after.direction&&before.reason==after.reason
            &&before.target_x==after.target_x&&before.target_y==after.target_y&&before.obstacle==after.obstacle;
        if(same)d=after.direction;
    }
    /* Even a no-candidate pair must be stationary before it can license a
     * restart. The fixed direction is proof-only, never an input command. */
    if(same){
        if(!d)d=NG2_LEFT;
        same=ng2_motion(&p->initial_scene_previous,scene,d,&still)
            &&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
    }
    remember_initial_candidate(p,scene,id,end,prefix);p->initial_scene_previous=*scene;
    if(!same)return 1;
    if(p->passage_unlocalized_gold&&!actual&&!mask){finish(p,end,NG2_REASON_NO_PATH);return 1;}
    if(prefirst)clear_model(p); /* The new proof begins its own raw fit span. */
    p->initial_scene_reacquiring=0;p->initial_view_pending=p->initial_candidate_waiting=0;
    p->restart_baseline_valid=p->restart_pending=0;
    p->passage_pending=mask;p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
    p->passage_wait_kind=0;p->passage_wait_deadline=p->passage_release_proof_id=0;
    p->restart_intent=!actual&&!mask;p->passage_active=!actual&&mask!=0;
    if(actual)p->passage_unlocalized_gold=0;
    else if(mask&&unlocalized_gold_floor(scene))p->passage_unlocalized_gold=1;
    if(p->passage_active)select_passage(p,scene);else p->passage_bit=-1;
    if(actual||mask){p->s.phase=NG2_PHASE_SYNC;p->passage_release_proof_id=id;}
    else p->s.phase=NG2_PHASE_FLOOR;
    return 1;
}
static int recheck_initial_view(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix){
    unsigned char support[30];uint32_t mask,missing;int bit,x,y,closed=1,independent,same;
    if(p->finish_requested||p->s.goods||level_inputs(p)||level_moves(p)||p->s.lead_confirmed
        ||p->s.x||p->s.y||p->s.input_state>1
        ||p->observe_now<start||p->observe_now-start>FRESH
        ||(!p->initial_view_pending&&!p->initial_candidate_waiting&&!p->passage_active&&!p->restart_intent))return 0;
    if(p->initial_scene_reacquiring)return recheck_initial_scene(p,scene,id,start,end,prefix);
    if(actual_gold(scene)){
        p->initial_view_pending=p->initial_candidate_waiting=0;return 0;
    }
    if(initial_uncertain_floor(p,scene)){
        /* A fade can make gold classification uncertain after the first
         * FLOOR. Freeze authority, not its original finite clock budget. */
        not_sent(p,end,NG2_REASON_SCREEN);clear_slots(p);
        p->initial_candidate_waiting=1;p->initial_candidate_id=0;
        p->passage_wait_kind=0;p->passage_release_proof_id=0;
        return 1;
    }
    if(!passage_floor(scene))return 0;
    mask=ng2_passage_candidates(scene);initial_candidate_support(scene,support);
    if(!p->initial_view_pending&&!p->initial_candidate_waiting&&mask==p->passage_pending)return 0;
    if(mask&&!p->s.walk_started_ns){
        p->s.walk_started_ns=end;
        if(!p->initial_view_end)p->sync_ns=end;
    }
    if(mask!=p->passage_pending||p->initial_candidate_waiting){
        not_sent(p,end,NG2_REASON_SCREEN);clear_slots(p);p->initial_candidate_waiting=1;
    }
    if(p->initial_view_pending&&(id<=p->initial_view_id||start<p->initial_view_end
        ||start<p->initial_view_start||start-p->initial_view_start<UI_SETTLE_NS)){
        return 1;
    }
    missing=p->passage_pending&~mask;
    for(bit=0;bit<10;++bit)if(missing&(UINT32_C(1)<<bit)){
        passage_mouth(bit,&x,&y);
        if(tile(scene,x,y)!=NG2_TILE_DIRT&&tile(scene,x,y)!=NG2_TILE_STONE)closed=0;
    }
    independent=p->initial_candidate_id&&id>p->initial_candidate_id
        &&start>=p->initial_candidate_end&&prefix==p->initial_candidate_prefix;
    same=mask==p->initial_candidate_mask
        &&unlocalized_gold_floor(scene)==p->initial_candidate_unlocalized;
    for(bit=0;bit<10;++bit)if((p->passage_pending|mask)&(UINT32_C(1)<<bit))
        if(memcmp(support+3*bit,p->initial_candidate_tiles+3*bit,3))same=0;
    if(!independent||!same||!closed){
        remember_initial_candidate(p,scene,id,end,prefix);return 1;
    }
    p->initial_view_pending=0;
    if(p->initial_candidate_waiting){
        if(p->passage_unlocalized_gold&&!mask){finish(p,end,NG2_REASON_NO_PATH);return 1;}
        p->initial_candidate_waiting=0;p->restart_baseline_valid=p->restart_pending=0;
        p->passage_pending=mask;p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
        p->passage_wait_kind=0;p->passage_wait_deadline=p->passage_release_proof_id=0;
        p->restart_intent=!mask;p->passage_active=mask!=0;
        if(mask&&unlocalized_gold_floor(scene))p->passage_unlocalized_gold=1;
        if(mask){
            select_passage(p,scene);
            if(!p->s.walk_started_ns)p->s.walk_started_ns=p->initial_view_end?p->initial_view_end:end;
            p->s.phase=NG2_PHASE_SYNC;
            p->passage_release_proof_id=id;
        }else {p->passage_bit=-1;p->s.phase=NG2_PHASE_FLOOR;}
    }
    remember_initial_candidate(p,scene,id,end,prefix);return 1;
}
static int scene_change(const NG2Scene *before,const NG2Scene *after,int *tiles,int *protected_cells){
    int i,mask=(before->state!=after->state?1:0)|(before->goods!=after->goods?2:0);
    *tiles=0;*protected_cells=0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        *tiles+=before->tiles[i]!=after->tiles[i];
        *protected_cells+=before->protected_cells[i]!=after->protected_cells[i];
    }
    return mask|(*tiles?4:0)|(*protected_cells?8:0);
}
static int can_replan(NG2Controller *p,const NG2Scene *scene){
    NG2Decision choice;NG2Motion motion;uint64_t aligned;
    int direction=p->command.direction;
    if(p->s.input_state!=1||p->replan_pending||p->finish_requested||p->replan_count>=2
        ||level_inputs(p)||level_moves(p)||p->s.lead_confirmed||!p->initial_ticket_valid
        ||p->command.kind!=NG2_ACTION_MOVE||direction<1||direction>4
        ||!safe_step(p,&p->before,direction)||!safe_step(p,scene,direction)
        ||!same_gold(&p->before,scene)||!ng2_beat_model_valid(&p->model)
        ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned)
        ||!choose_step(p,scene,&choice)
        ||choice.direction!=direction
        ||!ng2_motion(&p->before,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)return 0;
    return 1;
}
static int same_choice(const NG2Decision *a,const NG2Decision *b){
    return a->direction==b->direction&&a->reason==b->reason&&a->target_x==b->target_x
        &&a->target_y==b->target_y&&a->obstacle==b->obstacle;
}
/* Waiting for new terrain is separate from any sent input. The fixed local
 * candidate and the original budgets survive; no old ticket is resurrected. */
enum { PASSAGE_WAIT_GOAL=1,PASSAGE_WAIT_BLOCKED=2,PASSAGE_WAIT_GOLD=3,PASSAGE_WAIT_ROUTE=4 };
static void post_move_recover(NG2Controller *p,uint64_t now,int reason);
static int recover_unsent_continuous_scene(NG2Controller *p,uint64_t now,
    const NG2Scene *scene,uint64_t start,uint64_t end,uint64_t prefix);
static int irregular_blocked(NG2Controller *,const NG2Scene *,uint64_t,uint64_t,uint64_t,const NG2Motion *);
static int irregular_observe(NG2Controller *,const NG2Scene *,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t);
static int irregular_tick(NG2Controller *,uint64_t,NG2Command *);
static int irregular_begin(NG2Controller *,uint64_t,uint64_t,int,int,int);
static void irregular_hold(NG2Controller *,uint64_t,int);
static void irregular_clear_first(NG2Controller *);
static int reserve(NG2Controller *,uint64_t,int,int,uint64_t,NG2Command *);
static const NG2ControllerEvent *passage_move_ack(const NG2Controller *p){
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    if(!p->passage_active||p->passage_bit<0||p->passage_bit>=10
        ||!(p->passage_pending&(1u<<p->passage_bit))||p->finish_requested||p->s.goods
        ||p->command.kind!=NG2_ACTION_MOVE||p->command.direction<1||p->command.direction>4
        ||p->command_choice.reason!=10||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||!passage_floor(&p->before)||!p->command.id||p->s.last_completed_id!=p->command.id
        ||!e||e->command.id!=p->command.id||e->outcome!=2||!e->begin_ns
        ||e->end_ns<e->begin_ns||e->end_ns!=p->ack_ns
        ||p->motion_wait.command_id!=p->command.id
        ||p->motion_wait.source_capture_id!=p->command.source_capture_id)return NULL;
    return e;
}
static int passage_ack_visual(const NG2Controller *p,const NG2Scene *scene,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    return p->s.input_state==3&&p->s.current_command_id==p->command.id
        &&p->motion_wait.active&&!p->passage_wait_kind&&passage_move_ack(p)
        &&prefix==p->s.last_completed_id&&start>=p->ack_ns&&end>=start&&now>=end
        &&now<=p->motion_wait.deadline_ns&&uncertain_passage_floor(scene);
}
/* A ROUTE wait whose immutable anchor is the actual unit's uncertain view is
 * distinct from ordinary route waits, whose anchors already qualify input.
 * The ACK event and original visual bound remain its only parent authority. */
static int passage_moved_uncertain_wait(const NG2Controller *p){
    const NG2ControllerEvent *e=passage_move_ack(p);int d=p->command.direction;
    return p->passage_wait_kind==PASSAGE_WAIT_ROUTE&&!p->s.input_state
        &&!p->s.current_command_id&&!p->motion_wait.active
        &&uncertain_passage_floor(&p->passage_anchor)&&e&&e->motion==NG2_MOVED
        &&e->dx==dx[d]&&e->dy==dy[d]&&e->observed_capture_id==p->passage_anchor_id
        &&p->motion_wait.last_capture_id==p->passage_anchor_id
        &&p->motion_wait.last_motion==NG2_MOVED
        &&p->passage_anchor_start>=e->end_ns&&p->passage_wait_horizon
        &&p->passage_wait_horizon<=p->motion_wait.deadline_ns;
}
static int quiet_passage_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision a,b;NG2Motion still;int i,d=p->command.direction;
    if(!p->passage_active||p->passage_wait_kind||p->s.input_state!=1
        ||p->command.kind!=NG2_ACTION_MOVE||p->finish_requested||p->s.goods
        ||d<1||d>4||now>p->command.deadline_ns
        ||!safe_step(p,&p->before,d)||!safe_step(p,scene,d)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!choose_step(p,&p->before,&a)||!choose_step(p,scene,&b)
        ||!same_choice(&a,&p->command_choice)||!same_choice(&a,&b))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=p->before.tiles[i],latest=scene->tiles[i];
        if(old==latest)continue;
        if(old==NG2_TILE_GOLD||latest==NG2_TILE_GOLD||old==NG2_TILE_ITEM||latest==NG2_TILE_ITEM
            ||old==NG2_TILE_DOOR||latest==NG2_TILE_DOOR)return 0;
    }
    return ng2_motion(&p->before,scene,d,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
static int passage_source_world(const NG2Controller *p,uint64_t now){
    const NG2PassageSource *s=&p->passage_source;const NG2Command *t=&s->ticket;
    uint64_t aligned;
    return s->active&&p->passage_active&&!p->passage_wait_kind
        &&!p->stationary_wait_active&&!p->finish_requested&&!p->s.terminal&&!p->s.goods
        &&p->s.phase==NG2_PHASE_WALK&&p->s.lead_confirmed&&p->s.moves>0
        &&p->s.x==s->x&&p->s.y==s->y&&p->s.inputs==s->inputs&&p->s.moves==s->moves
        &&p->s.last_completed_id==s->prefix&&p->last_observed_prefix==s->prefix
        &&p->passage_bit==s->bit&&p->passage_pending==s->pending
        &&p->passage_inspected==s->inspected&&p->passage_unresolved==s->unresolved
        &&p->passage_closed==s->closed&&p->passage_unlocalized_gold==s->unlocalized
        &&!memcmp(p->visits,s->visits,sizeof(s->visits))
        &&!memcmp(&p->entrance,&s->entrance,sizeof(s->entrance))
        &&p->command.kind==NG2_ACTION_MOVE&&p->command.direction==t->direction
        &&p->command.ordinal==t->ordinal&&p->command.target_ns==t->target_ns
        &&p->command.not_before_ns==t->not_before_ns&&p->command.deadline_ns==t->deadline_ns
        &&p->command_period==s->period&&p->schedule_deadline==s->schedule
        &&p->motion_wait.deadline_ns==s->visual&&p->command_sync_deadline==s->sync
        &&now>=t->source_start_ns&&now-t->source_start_ns<=FRESH
        &&now>=t->phase_sample_ns&&now-t->phase_sample_ns<=FRESH
        &&now<=t->deadline_ns&&now<=s->schedule&&now<=s->visual
        &&(!s->sync||now<s->sync)&&ng2_beat_model_valid(&p->model)&&!p->beat_failed
        &&now>=p->model.last_ns&&now-p->model.last_ns<=FRESH
        &&corrected(p,t->target_ns,s->period,&aligned);
}
static int passage_source_proof(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    const NG2PassageSource *s=&p->passage_source;NG2Decision original,latest;NG2Motion zero;
    int i,d=s->ticket.direction;
    if(!passage_source_world(p,now)||d<1||d>4
        ||!clear_gold_floor(&s->anchor)||!clear_gold_floor(scene)
        ||!safe_step(p,&s->anchor,d)||!safe_step(p,scene,d)
        ||memcmp(s->anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!choose_step(p,&s->anchor,&original)||!same_choice(&original,&s->choice)
        ||!same_choice(&original,&p->command_choice)||!choose_step(p,scene,&latest)
        ||!same_choice(&original,&latest))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(s->anchor.protected_cells[i]||s->anchor.tiles[i]==NG2_TILE_GOLD||scene->tiles[i]==NG2_TILE_GOLD
            ||s->anchor.tiles[i]==NG2_TILE_DOOR||scene->tiles[i]==NG2_TILE_DOOR
            ||s->anchor.tiles[i]==NG2_TILE_ITEM||scene->tiles[i]==NG2_TILE_ITEM)return 0;
    return ng2_motion(&s->anchor,scene,d,&zero)&&zero.kind==NG2_BLOCKED&&!zero.dx&&!zero.dy;
}
static void create_passage_source(NG2Controller *p){
    NG2PassageSource *s=&p->passage_source;
    memset(s,0,sizeof(*s));
    if(!p->passage_active||p->passage_wait_kind||p->stationary_wait_active
        ||!p->s.lead_confirmed||!p->s.moves||p->command.kind!=NG2_ACTION_MOVE
        ||p->command_choice.reason!=10||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||!clear_gold_floor(&p->scene)||p->passage_unlocalized_gold)return;
    s->active=1;s->anchor=p->scene;s->ticket=p->command;s->choice=p->command_choice;
    s->prefix=p->s.last_completed_id;s->period=p->command_period;
    s->schedule=p->schedule_deadline;s->visual=p->motion_wait.deadline_ns;s->sync=p->command_sync_deadline;
    s->x=p->s.x;s->y=p->s.y;s->inputs=p->s.inputs;s->moves=p->s.moves;
    s->bit=p->passage_bit;s->pending=p->passage_pending;s->inspected=p->passage_inspected;
    s->unresolved=p->passage_unresolved;s->closed=p->passage_closed;s->unlocalized=p->passage_unlocalized_gold;
    s->entrance=p->entrance;memcpy(s->visits,p->visits,sizeof(s->visits));
}
static int passage_source_refinable(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    const NG2PassageSource *s=&p->passage_source;const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    int i,changed=0,d=p->command.direction;
    if(!s->active||s->refreshed||p->s.input_state!=1||p->s.current_command_id!=p->command.id
        ||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->replan_pending||p->continuous_pending||p->continuous_chain_count>=2||p->continuous_count>=8
        ||!passage_source_proof(p,scene,now))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(s->anchor.tiles[i]!=scene->tiles[i]){
        int x=i%23-11,y=i/23-5;
        if(s->anchor.tiles[i]!=NG2_TILE_DIRT||scene->tiles[i]!=NG2_TILE_STONE
            ||(abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))return 0;
        ++changed;
    }
    return changed>0;
}
static void begin_passage_wait(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now,int kind){
    uint64_t horizon,old_sync=p->command_sync_deadline;
    /* A first gold observation can revoke an unstarted no-gold PAUSE before
     * any walking episode exists. Establish its epoch once, never restart it. */
    if(!p->s.walk_started_ns){p->s.walk_started_ns=end;p->sync_ns=end;}
    horizon=sync_deadline(p);
    if(p->s.input_state==1)not_sent(p,end,NG2_REASON_SCREEN);
    if(p->s.lead_confirmed)post_move_recover(p,now,NG2_RECOVERY_VISUAL_SCHEDULE);
    else {clear_slots(p);p->s.phase=NG2_PHASE_SYNC;}
    if(old_sync)horizon=minimum(horizon,old_sync);
    horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
    horizon=minimum(horizon,session_bound(p));
    p->passage_wait_kind=kind;p->passage_wait_horizon=horizon;p->passage_initial_reanchor=0;
    p->passage_wait_deadline=ng2_beat_model_valid(&p->model)?minimum(now+2*p->model.period_ns,horizon):0;
    p->passage_anchor=*scene;p->passage_anchor_id=id;
    p->passage_anchor_start=start;p->passage_anchor_end=end;
    diagnostic_comparison(p,0,NG2_REVALIDATE_NONE,NULL);
    p->proof_deadline=0;p->proof_reacquire=0;p->proof_capture_id=id;p->motion_wait.active=0;
}
static int begin_uncertain_moved_passage_wait(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end,uint64_t now){
    const NG2ControllerEvent *e=passage_move_ack(p);size_t samples=p->sample_count;
    uint64_t parent=p->motion_wait.deadline_ns;int d=p->command.direction;
    if(!e||p->s.input_state||p->s.current_command_id||!p->s.lead_confirmed
        ||p->latest_verified_ns!=now||!uncertain_passage_floor(scene)
        ||e->motion!=NG2_MOVED||e->dx!=dx[d]||e->dy!=dy[d]||e->observed_capture_id!=id
        ||p->motion_wait.last_capture_id!=id||p->motion_wait.last_motion!=NG2_MOVED
        ||start<e->end_ns||now>=parent)return 0;
    begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_ROUTE);
    p->passage_wait_horizon=minimum(p->passage_wait_horizon,parent);
    p->passage_wait_deadline=p->passage_wait_deadline?
        minimum(p->passage_wait_deadline,p->passage_wait_horizon):p->passage_wait_horizon;
    /* Keep only same-level, previously admitted HUD observations as data.
     * A fresh positive route must supply a new normal fit before a new slot. */
    clear_slots(p);clear_model(p);p->sample_count=samples;
    p->proof_capture_id=p->proof_deadline=p->passage_release_proof_id=0;
    p->proof_reacquire=0;p->s.phase=NG2_PHASE_SYNC;
    return 1;
}
/* An initial fade is not a stationary source. Retire only its old route/slot
 * authority, then keep a data anchor until two current views independently
 * agree. No clock, input count, displacement or beat-model evidence is reset. */
static int initial_gold_data_scene(const NG2Scene *scene){
    int i;
    if(!actual_gold(scene)||scene->goods!=NG2_GOODS_UNKNOWN||tile(scene,0,0)!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(scene->protected_cells[i]||scene->tiles[i]==NG2_TILE_ITEM)return 0;
    return 1;
}
static int reanchor_initial_gold(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now,int can_start){
    if(p->passage_initial_reanchor<0||(!p->passage_initial_reanchor&&!can_start)
        ||!initial_recoverable(p)||p->s.input_state||p->s.current_command_id||p->s.x||p->s.y
        ||p->entrance.valid||!p->passage_active||p->passage_wait_kind!=PASSAGE_WAIT_GOLD
        ||p->restart_pending||p->restart_intent||p->initial_view_pending||p->initial_candidate_waiting
        ||p->initial_scene_reacquiring||(!p->passage_initial_reanchor&&p->replan_count>=2)
        ||!p->passage_wait_deadline||now>=p->passage_wait_deadline||now>=p->passage_wait_horizon
        ||now>=sync_deadline(p)||id<=p->passage_anchor_id||start<p->passage_anchor_end
        ||now<end||now<start||now-start>FRESH
        ||!initial_gold_data_scene(&p->passage_anchor)||!initial_gold_data_scene(scene))return 0;
    if(!p->passage_initial_reanchor){
        if(p->recovery.mode!=NG2_RECOVERY_INITIAL){
            ++p->recovery.episode_id;++p->recovery.initial_reacquisitions;
            p->recovery.mode=NG2_RECOVERY_INITIAL;
        }
        /* Preserve the discarded fade source as a recovery reference. */
        recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,p->passage_anchor_id);
        ++p->replan_count;p->passage_initial_reanchor=1;
        clear_slots(p);memset(&p->command,0,sizeof(p->command));
        p->proof_capture_id=p->proof_deadline=p->passage_release_proof_id=0;
        p->passage_pending=p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
        p->passage_bit=-1;p->initial_candidate_id=0;p->initial_candidate_mask=0;
        p->s.phase=NG2_PHASE_SYNC;
    }
    p->passage_anchor=*scene;p->passage_anchor_id=id;
    p->passage_anchor_start=start;p->passage_anchor_end=end;
    return 1;
}
/* A closed mouth is a local route rejection, not an inspection beyond it.
 * Only a verified arrival at the fixed world's inboard neighbour may use two
 * independent, strictly stationary views of the same observed wall. */
static int closed_passage_mouth(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->passage_anchor;NG2Decision choice;
    int mx,my,d,x,y,wall,i,arrival=0;
    size_t j;
    if(!p->passage_active||p->passage_bit<0||p->passage_bit>=10
        ||p->passage_wait_kind!=PASSAGE_WAIT_BLOCKED||p->s.input_state
        ||p->finish_requested||p->s.goods||!p->s.lead_confirmed||!level_moves(p)
        ||!clear_gold_floor(a)||!clear_gold_floor(scene)
        ||tile(a,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR)return 0;
    passage_mouth(p->passage_bit,&mx,&my);d=p->passage_bit<5?NG2_UP:NG2_LEFT;
    if(p->s.x!=mx-dx[d]||p->s.y!=my-dy[d])return 0;
    for(j=p->event_count;j>0;--j){
        const NG2ControllerEvent *e=&p->events[j-1];
        if(e->command.id==p->s.last_completed_id){
            arrival=e->command.kind==NG2_ACTION_MOVE&&e->outcome==2&&e->begin_ns
                &&e->motion==NG2_MOVED&&e->command.direction>=1&&e->command.direction<=4
                &&e->dx==dx[e->command.direction]&&e->dy==dy[e->command.direction]
                &&e->observed_capture_id
                &&e->observed_capture_id<=p->passage_anchor_id
                &&p->passage_anchor_start>=e->end_ns;
            break;
        }
    }
    if(!arrival)return 0;
    x=mx-p->s.x;y=my-p->s.y;wall=tile(a,x,y);
    if((wall!=NG2_TILE_DIRT&&wall!=NG2_TILE_STONE)||tile(scene,x,y)!=wall)return 0;
    for(i=-1;i<=1;i+=2){
        int sx=x+i*dy[d],sy=y-i*dx[d],old=tile(a,sx,sy);
        if((old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)||tile(scene,sx,sy)!=old)return 0;
    }
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||a->tiles[i]==NG2_TILE_ITEM||scene->tiles[i]==NG2_TILE_ITEM)return 0;
    return !choose_step(p,a,&choice)&&!choose_step(p,scene,&choice);
}
static void passage_next_candidate(NG2Controller *p,const NG2Scene *scene,uint64_t now,int inspection){
    uint32_t bit=1u<<p->passage_bit;
    NG2ControllerStopDetail previous;
    live_stop_detail(p,&previous);
    if(p->passage_unlocalized_gold)inspection=0;
    p->passage_pending&=~bit;
    if(inspection==1)p->passage_inspected|=bit;
    else if(inspection==2)p->passage_closed|=bit;
    else p->passage_unresolved|=bit;
    p->passage_wait_kind=0;p->passage_wait_deadline=0;
    if(select_passage(p,scene))return;
    p->passage_active=0;
    if(p->passage_unresolved||p->passage_unlocalized_gold){
        previous.passage_unresolved=p->passage_unresolved;
        freeze_stop_detail(p,now,NG2_REASON_NO_PATH,&previous);
        finish(p,now,NG2_REASON_NO_PATH);return;
    }
    /* Every fixed candidate was independently inspected or locally closed. */
    clear_slots(p);p->proof_deadline=0;p->recovery.mode=NG2_RECOVERY_NORMAL;
    p->restart_intent=1;p->s.phase=NG2_PHASE_FLOOR;
}
static void update_passage_wait(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Motion still={0};NG2Decision a,b;int kind=p->passage_wait_kind,x,y,d=p->command.direction,motion_ok;
    if(!kind||p->finish_requested)return;
    if(scene->state!=NG2_FLOOR){finish(p,now,NG2_REASON_SCREEN);return;}
    if((scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))&&!actual_gold(scene)){
        finish(p,now,NG2_REASON_PARTIAL_GOODS);return;
    }
    if(now>=p->passage_wait_horizon){finish(p,now,NG2_REASON_BEAT);return;}
    if(!p->passage_wait_deadline&&ng2_beat_model_valid(&p->model))
        p->passage_wait_deadline=minimum(now+2*p->model.period_ns,p->passage_wait_horizon);
    if(d<1||d>4)d=NG2_UP;
    if(p->passage_wait_deadline&&now>=p->passage_wait_deadline){
        if(kind==PASSAGE_WAIT_GOAL||kind==PASSAGE_WAIT_BLOCKED)passage_next_candidate(p,scene,now,0);
        else finish(p,now,NG2_REASON_NO_PATH);
        return;
    }
    if(passage_moved_uncertain_wait(p)){
        int i;
        /* Never replace this anchor or turn UNKNOWN into CLEAR. A later
         * independent positive route must be strictly still against the
         * actual displacement image, within that input's original bound. */
        if(start<p->passage_anchor_end||id<=p->passage_anchor_id){
            diagnostic_comparison(p,id,NG2_REVALIDATE_STATE,NULL);return;
        }
        if(!ng2_motion(&p->passage_anchor,scene,d,&still)
            ||still.kind!=NG2_BLOCKED||still.dx||still.dy){
            diagnostic_comparison(p,id,NG2_REVALIDATE_MOTION,&still);return;
        }
        if(scene->goods!=NG2_GOODS_UNKNOWN||passage_goods_protected(scene)
            ||tile(scene,0,0)!=NG2_TILE_FLOOR){
            diagnostic_comparison(p,id,NG2_REVALIDATE_STATE,&still);return;
        }
        for(i=0;i<NG2_TILE_COUNT;++i)if(scene->protected_cells[i]){
            diagnostic_comparison(p,id,NG2_REVALIDATE_STATE,&still);return;
        }
        if(clear_gold_floor(scene)){
            if(!choose_step(p,scene,&b)||!safe_step(p,scene,b.direction)){
                diagnostic_comparison(p,id,NG2_REVALIDATE_ROUTE,&still);return;
            }
        }else if(actual_gold(scene)){
            if(!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&b)
                ||!safe_floor(scene,b.direction)){
                diagnostic_comparison(p,id,NG2_REVALIDATE_ROUTE,&still);return;
            }
            p->passage_active=0;p->passage_unlocalized_gold=0;
        }else {diagnostic_comparison(p,id,NG2_REVALIDATE_GOLD,&still);return;}
        diagnostic_comparison(p,id,NG2_REVALIDATE_NONE,&still);
        p->passage_wait_kind=0;p->proof_capture_id=id;p->passage_release_proof_id=id;
        p->proof_deadline=p->passage_wait_horizon;p->proof_reacquire=0;
        p->s.phase=NG2_PHASE_SYNC;return;
    }
    if(actual_gold(scene)&&kind!=PASSAGE_WAIT_GOLD){
        p->passage_wait_kind=PASSAGE_WAIT_GOLD;p->passage_anchor=*scene;
        p->passage_anchor_id=id;p->passage_anchor_start=start;p->passage_anchor_end=end;return;
    }
    if(start<p->passage_anchor_end||id<=p->passage_anchor_id){
        diagnostic_comparison(p,id,NG2_REVALIDATE_STATE,NULL);return;
    }
    if(kind==PASSAGE_WAIT_GOLD&&p->passage_initial_reanchor<0)return;
    motion_ok=ng2_motion(&p->passage_anchor,scene,d,&still);
    if(!motion_ok||still.kind!=NG2_BLOCKED||still.dx||still.dy){
        diagnostic_comparison(p,id,NG2_REVALIDATE_MOTION,&still);
        if(kind==PASSAGE_WAIT_GOLD&&motion_ok&&(still.kind==NG2_MOVED||still.dx||still.dy)
            &&(p->passage_initial_reanchor||(initial_recoverable(p)&&!p->s.input_state
                &&!p->s.x&&!p->s.y&&!p->entrance.valid)))p->passage_initial_reanchor=-1;
        if(motion_ok&&still.kind==NG2_MOTION_UNKNOWN&&!still.dx&&!still.dy)
            reanchor_initial_gold(p,scene,id,start,end,now,1);
        return;
    }
    diagnostic_comparison(p,id,NG2_REVALIDATE_NONE,&still);
    if(kind==PASSAGE_WAIT_GOLD){
        if(p->passage_initial_reanchor){
            if(p->passage_initial_reanchor<0||!initial_recoverable(p)||p->s.input_state
                ||p->s.current_command_id||p->s.x||p->s.y||p->entrance.valid
                ||!initial_gold_data_scene(scene))return;
            if(!same_gold(&p->passage_anchor,scene)
                ||!ng2_choose(&p->passage_anchor,0,0,p->visits,NG2_VISIT_COUNT,&p->entrance,&a)
                ||!ng2_choose(scene,0,0,p->visits,NG2_VISIT_COUNT,&p->entrance,&b)||!same_choice(&a,&b)){
                reanchor_initial_gold(p,scene,id,start,end,now,0);return;
            }
        }
        if(!actual_gold(scene)||!same_gold(&p->passage_anchor,scene)
            ||tile(scene,0,0)!=NG2_TILE_FLOOR){
            diagnostic_comparison(p,id,NG2_REVALIDATE_GOLD,&still);return;
        }
        p->passage_active=0;p->passage_wait_kind=0;p->proof_capture_id=id;p->passage_release_proof_id=id;
        p->passage_unlocalized_gold=0;p->passage_initial_reanchor=0;
        clear_recovery_slot(p);p->s.phase=NG2_PHASE_SYNC;return;
    }
    if(!passage_floor(scene))return;
    if(kind==PASSAGE_WAIT_BLOCKED&&closed_passage_mouth(p,scene)){
        passage_next_candidate(p,scene,now,2);p->proof_capture_id=id;return;
    }
    passage_goal(p,&x,&y);
    if(kind==PASSAGE_WAIT_GOAL&&p->s.x==x&&p->s.y==y){
        passage_next_candidate(p,scene,now,1);p->proof_capture_id=id;return;
    }
    if(choose_step(p,scene,&b)&&safe_step(p,scene,b.direction)){
        if(kind==PASSAGE_WAIT_ROUTE&&choose_step(p,&p->passage_anchor,&a)&&same_choice(&a,&b)
            &&!memcmp(p->passage_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT)){
            p->passage_wait_kind=0;p->proof_capture_id=id;p->passage_release_proof_id=id;return;
        }
        diagnostic_comparison(p,id,NG2_REVALIDATE_ROUTE,&still);
        p->passage_wait_kind=PASSAGE_WAIT_ROUTE;p->passage_anchor=*scene;
        p->passage_anchor_id=id;p->passage_anchor_start=start;p->passage_anchor_end=end;
    }else diagnostic_comparison(p,id,NG2_REVALIDATE_ROUTE,&still);
}
static void update_passage_progress(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Decision next;int x,y;
    if(!p->passage_active||p->finish_requested||p->s.input_state||p->passage_wait_kind
        ||p->initial_view_pending||p->initial_candidate_waiting)return;
    if(actual_gold(scene)){
        /* A same-frame verified MOVED proof already establishes the new pose.
         * Otherwise wait for independent evidence before changing authority. */
        if(p->latest_verified_ns==now&&level_moves(p)>0){
            p->passage_unlocalized_gold=0;
            p->passage_active=0;p->motion_reference_present=p->motion_reference_valid=0;return;
        }
        begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_GOLD);return;
    }
    if(scene->goods!=NG2_GOODS_UNKNOWN){finish(p,now,NG2_REASON_PARTIAL_GOODS);return;}
    if(!passage_floor(scene)){
        if(!begin_uncertain_moved_passage_wait(p,scene,id,start,end,now))finish(p,now,NG2_REASON_SCREEN);
        return;
    }
    passage_goal(p,&x,&y);
    if(p->s.x==x&&p->s.y==y)begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_GOAL);
    else if(!choose_step(p,scene,&next))begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_BLOCKED);
}

/* A fringe is evidence of a shop below the lattice, not a hidden map cell.
 * Only the already observed next FLOOR may supply this single first step. */
static int edge_floor(const NG2Scene *s){
    int i;
    if(s->state!=NG2_FLOOR||s->goods!=NG2_GOODS_UNKNOWN||s->gold_state!=NG2_GOLD_EDGE_DOWN
        ||tile(s,0,0)!=NG2_TILE_FLOOR||tile(s,0,1)!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(s->tiles[i]==NG2_TILE_GOLD||s->protected_cells[i])return 0;
    return 1;
}
static int quiet_edge_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision before,latest;NG2Motion still;uint64_t aligned;int i;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->command.direction!=NG2_DOWN
        ||p->finish_requested||p->s.goods||p->edge_sent||level_inputs(p)||level_moves(p)||p->s.lead_confirmed
        ||p->s.x||p->s.y||p->entrance.valid||p->replan_pending||!p->initial_ticket_valid
        ||p->command_choice.reason!=9||!edge_floor(&p->before)||!edge_floor(scene)
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->initial_ticket.deadline_ns||now>=sync_deadline(p)
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH
        ||now-p->s.walk_started_ns>=45*SECOND||now-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a==b)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x)<=1&&abs(y-1)<=1)
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT&&a!=NG2_TILE_STONE)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE))return 0;
    }
    return choose_step(p,&p->before,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,&p->command_choice)&&same_choice(&before,&latest)
        &&ng2_motion(&p->before,scene,NG2_DOWN,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
/* Preserve the published initial ticket through irrelevant remote palette
 * flicker throughout its publication window. Its source/before remain frozen;
 * every accepted current image must independently prove the same safe step. */
static int quiet_initial_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision before,latest;NG2Motion motion;uint64_t aligned;int i,d=p->command.direction;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->finish_requested
        ||p->replan_pending||level_inputs(p)||level_moves(p)||p->s.lead_confirmed
        ||!p->initial_ticket_valid||d<1||d>4||p->beat_failed
        ||p->command.not_before_ns<INITIAL_PUBLICATION
        ||now<p->command.not_before_ns-INITIAL_PUBLICATION||now>p->command.deadline_ns
        ||!safe_step(p,&p->before,d)||!safe_step(p,scene,d)
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!same_gold(&p->before,scene)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!ng2_beat_model_valid(&p->model)
        ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a==b)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT))return 0;
    }
    return choose_step(p,&p->before,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,&p->command_choice)&&same_choice(&before,&latest)
        &&ng2_motion(&p->before,scene,d,&motion)&&motion.kind==NG2_BLOCKED&&!motion.dx&&!motion.dy;
}
static int same_continuous_action(const NG2Decision *a,const NG2Decision *b){
    if(a->direction!=b->direction||a->reason!=b->reason||a->obstacle!=b->obstacle)return 0;
    /* Reason 8 is observed_floor_vantage. Its remote target may change while
     * the planner still authorizes the same single step onto observed floor. */
    return (a->reason==8&&a->obstacle==NG2_TILE_FLOOR)
        ||(a->target_x==b->target_x&&a->target_y==b->target_y);
}
/* New observations may identify unknown cells or restrict known traversal.
 * Never erase a known blocker/item or manufacture a door without its bracket. */
static int monotone_terrain(const NG2Scene *before,const NG2Scene *after){
    int i,changed=0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=before->tiles[i],b=after->tiles[i];
        if(before->protected_cells[i]!=after->protected_cells[i])return 0;
        if(a==b)continue;
        ++changed;
        if(a==NG2_TILE_UNKNOWN){if(b<NG2_TILE_FLOOR||b>NG2_TILE_DOOR)return 0;}
        else if(a==NG2_TILE_FLOOR){if(b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE&&b!=NG2_TILE_GOLD&&b!=NG2_TILE_DOOR)return 0;}
        else if(a==NG2_TILE_DIRT){if(b!=NG2_TILE_STONE&&b!=NG2_TILE_GOLD&&b!=NG2_TILE_DOOR)return 0;}
        else return 0;
        if(b==NG2_TILE_DOOR&&!gate_at(after,i%23-11,i/23-5))return 0;
    }
    return changed!=0;
}
/* A closed bracket may become readable while the same two-cell floor approach
 * stays stationary. Only remote DIRT/FLOOR palette disagreement extends the
 * ordinary monotone relation; it never clears a nearby traversal obstacle. */
static int revealed_approach_terrain(const NG2Scene *before,const NG2Scene *after,int d){
    int gx=3*dx[d],gy=3*dy[d],sx=dy[d],sy=-dx[d],leaf_x,leaf_y;
    int i,old_gold=0,new_gold=0,palette=0;
    if(tile(before,gx,gy)!=NG2_TILE_DIRT||tile(after,gx,gy)!=NG2_TILE_DOOR
        ||tile(before,2*dx[d],2*dy[d])!=NG2_TILE_FLOOR
        ||tile(after,2*dx[d],2*dy[d])!=NG2_TILE_FLOOR
        ||tile(after,gx+sx,gy+sy)!=NG2_TILE_GOLD
        ||tile(after,gx-sx,gy-sy)!=NG2_TILE_GOLD)return 0;
    if(tile(before,gx+sx,gy+sy)==NG2_TILE_GOLD
        &&tile(before,gx-sx,gy-sy)==NG2_TILE_DIRT){leaf_x=gx-sx;leaf_y=gy-sy;}
    else if(tile(before,gx-sx,gy-sy)==NG2_TILE_GOLD
        &&tile(before,gx+sx,gy+sy)==NG2_TILE_DIRT){leaf_x=gx+sx;leaf_y=gy+sy;}
    else return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=before->tiles[i],b=after->tiles[i],x=i%23-11,y=i/23-5;
        old_gold+=a==NG2_TILE_GOLD;new_gold+=b==NG2_TILE_GOLD;
        if(before->protected_cells[i]!=after->protected_cells[i])return 0;
        if(a==b)continue;
        if(before->protected_cells[i]||after->protected_cells[i])return 0;
        if(x==gx&&y==gy&&a==NG2_TILE_DIRT&&b==NG2_TILE_DOOR)continue;
        if(x==leaf_x&&y==leaf_y&&a==NG2_TILE_DIRT&&b==NG2_TILE_GOLD)continue;
        if(a==NG2_TILE_DIRT&&b==NG2_TILE_FLOOR){
            if(abs(x)+abs(y)<6||(abs(x)<=1&&abs(y)<=1)
                ||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))return 0;
            ++palette;continue;
        }
        /* Preserve the ordinary monotone alternatives for every other cell.
         * In particular, known GOLD/STONE/DOOR/ITEM can never disappear. */
        if(a==NG2_TILE_UNKNOWN){if(b<NG2_TILE_FLOOR||b>NG2_TILE_DOOR)return 0;}
        else if(a==NG2_TILE_FLOOR){if(b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE&&b!=NG2_TILE_GOLD&&b!=NG2_TILE_DOOR)return 0;}
        else if(a==NG2_TILE_DIRT){if(b!=NG2_TILE_STONE&&b!=NG2_TILE_GOLD&&b!=NG2_TILE_DOOR)return 0;}
        else return 0;
        if(b==NG2_TILE_DOOR&&!gate_at(after,x,y))return 0;
    }
    return old_gold==1&&new_gold==2&&palette>0;
}
static uint64_t continuous_horizon(const NG2Controller *p){
    uint64_t horizon=minimum(p->continuous_ticket.source_start_ns+FRESH,p->continuous_ticket.phase_sample_ns+FRESH);
    horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
    if(p->opened_entry_parent)horizon=minimum(horizon,p->opened_entry_parent);
    return minimum(horizon,session_bound(p));
}
static int last_ack_opened_gate(const NG2Controller *p,int direction){
    size_t i;
    if(p->entrance.valid||!p->s.door_changes)return 0;
    for(i=p->event_count;i>0;--i){
        const NG2ControllerEvent *e=&p->events[i-1];
        if(e->command.id==p->s.last_completed_id)
            return e->command.kind==NG2_ACTION_MOVE&&e->command.direction==direction
                &&e->outcome==2&&e->motion==NG2_DOOR_OPENED&&!e->dx&&!e->dy;
    }
    return 0;
}
static int gold_retained(const NG2Scene *a,const NG2Scene *b){
    int i;for(i=0;i<NG2_TILE_COUNT;++i)
        if(a->tiles[i]==NG2_TILE_GOLD&&b->tiles[i]!=NG2_TILE_GOLD)return 0;
    return 1;
}
/* Newly lit wall evidence cannot change a walking surface, nearby bracket,
 * protected material or an already observed GOLD cell. Check both the frozen
 * source and the last accepted image without replacing the source ticket. */
static int distant_gold_growth(const NG2Scene *a,const NG2Scene *b,int d){
    int i;if(d<1||d>4||!gold_retained(a,b))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=b->tiles[i],x=i%23-11,y=i/23-5;
        if(old==latest)continue;
        if(a->protected_cells[i]||b->protected_cells[i])return 0;
        if(latest==NG2_TILE_GOLD
            &&((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_DIRT)
                ||(abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)))return 0;
    }
    return 1;
}
static int partial_shop_floor_step(const NG2Controller *p){
    int d=p->command.direction;
    return d>=1&&d<=4&&p->before.goods==NG2_GOODS_PARTIAL
        &&p->command_choice.obstacle==NG2_TILE_FLOOR
        &&((p->entrance.valid==1&&p->command_choice.reason==8)
            ||(p->command_choice.reason==5&&p->command_choice.target_x==dx[d]
                &&p->command_choice.target_y==dy[d]&&last_ack_opened_gate(p,d)));
}
/* A clipped top row may relabel already protected products before the first
 * UP entrance. The frozen source remains the protection superset; neither a
 * new protected point nor a changed cell outside that envelope is quiet. */
static int clipped_entry_top(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->before;
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    int i,envelope=0;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->command.direction!=3
        ||p->s.current_command_id!=p->command.id||!e||e->command.id!=p->command.id
        ||e->begin_ns||e->outcome||p->entrance.valid||!p->s.lead_confirmed||!level_moves(p)
        ||!p->continuous_ticket_valid||p->command_choice.reason!=5
        ||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||p->command_choice.target_x||p->command_choice.target_y!=-1
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_PARTIAL||scene->goods!=NG2_GOODS_PARTIAL
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!last_ack_opened_gate(p,3))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],edge=i/23==0&&a->protected_cells[i];
        if(scene->protected_cells[i]&&!a->protected_cells[i])return 0;
        if(!edge){
            if(old!=latest||a->protected_cells[i]!=scene->protected_cells[i]
                ||(p->scene.tiles[i]==NG2_TILE_GOLD&&latest!=NG2_TILE_GOLD))return 0;
            continue;
        }
        envelope=1;
        if(old==latest&&a->protected_cells[i]==scene->protected_cells[i])continue;
        if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT
                &&old!=NG2_TILE_GOLD&&old!=NG2_TILE_ITEM)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_DIRT
                &&latest!=NG2_TILE_GOLD&&latest!=NG2_TILE_ITEM))return 0;
    }
    return envelope;
}
/* This relation grants no input. A complete cached-source Decision and a
 * strict independent zero proof must still authorize a separate FRESH ID. */
static int opened_entry_floor(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->before;
    int d=p->command.direction,i;
    if(d<1||d>4||p->command.kind!=NG2_ACTION_MOVE||p->entrance.valid
        ||!p->s.lead_confirmed||!level_moves(p)||!last_ack_opened_gate(p,d)
        ||p->command_choice.reason!=5||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||p->command_choice.target_x!=dx[d]||p->command_choice.target_y!=dy[d]
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||a->goods!=scene->goods||scene->goods<NG2_GOODS_UNKNOWN||scene->goods>NG2_GOODS_PARTIAL
        ||tile(a,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(a,dx[d],dy[d])!=NG2_TILE_FLOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!gate_at(a,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d]))return 0;
    for(i=0;i<5;++i)
        if(protected_route_cell(a,scene,dx[i],dy[i])
            ||protected_route_cell(a,scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    return 1;
}
static int opened_entry_relation(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->before;
    int d=p->command.direction,i,x,y,left=12,right=-12,items=0,inner=0,remote_wall=0,clipped;
    if(!opened_entry_floor(p,scene))return 0;
    clipped=a->goods==NG2_GOODS_PARTIAL;
    if(clipped){
        if(d!=NG2_UP)return 0;
        for(x=-11;x<=11;++x)if(tile(a,x,-5)==NG2_TILE_ITEM||tile(scene,x,-5)==NG2_TILE_ITEM){
            if(x<left)left=x;
            if(x>right)right=x;
            ++items;
        }
        if(items<3||right-left+1!=items)return 0;
        for(x=left;x<=right;++x)
            if(!protected_at(a,x,-5)||!protected_at(scene,x,-5))return 0;
    }
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],envelope;
        x=i%23-11;y=i/23-5;
        /* ng2_protect projects each observed ITEM to its center and four
         * neighbors. Only its top-row horizontal margin may fluctuate. */
        envelope=clipped&&y==-5&&x>=left-1&&x<=right+1
            &&(a->protected_cells[i]||scene->protected_cells[i]);
        if(envelope){
            if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT
                    &&old!=NG2_TILE_GOLD&&old!=NG2_TILE_ITEM)
                ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_DIRT
                    &&latest!=NG2_TILE_GOLD&&latest!=NG2_TILE_ITEM))return 0;
            continue;
        }
        if(a->protected_cells[i]!=scene->protected_cells[i]
            ||(p->scene.tiles[i]==NG2_TILE_GOLD&&latest!=NG2_TILE_GOLD))return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||scene->protected_cells[i])return 0;
        /* A bracketed door outside the origin can resolve to solid GOLD.
         * A diagonal neighbor of the destination may close as well: neither
         * actual FLOOR nor its cardinal stepping cross changes. The caller
         * still needs the complete same Decision and direct strict zero.
         * No door or traversable surface is added; old profiles keep their
         * original rule. */
        if(p->cycle_enabled&&old==NG2_TILE_DOOR&&latest==NG2_TILE_GOLD
            &&(abs(x)>1||abs(y)>1)
            &&((abs(x-dx[d])>1||abs(y-dy[d])>1)
                ||(abs(x-dx[d])==1&&abs(y-dy[d])==1))
            &&gate_at(a,x,y)&&gate_at(scene,x,y)){remote_wall=1;continue;}
        /* Before the goods latch, a newly lit continuation of an observed
         * GOLD wall is also positive remote evidence. Neither MOVE footprint
         * nor old wall/protection changes; the caller still needs the full
         * unchanged choice and independent strict zero for a FRESH ticket. */
        if(p->cycle_enabled&&!clipped&&!passage_goods_protected(a)
            &&!passage_goods_protected(scene)&&latest==NG2_TILE_GOLD
            &&(old==NG2_TILE_UNKNOWN||old==NG2_TILE_DIRT)
            &&(abs(x)>1||abs(y)>1)&&(abs(x-dx[d])>1||abs(y-dy[d])>1)){
            int j,neighbor=0;
            for(j=1;j<=4;++j)
                neighbor|=tile(a,x+dx[j],y+dy[j])==NG2_TILE_GOLD
                    &&tile(scene,x+dx[j],y+dy[j])==NG2_TILE_GOLD;
            if(neighbor){remote_wall=1;continue;}
        }
        if(!clipped&&x==2*dx[d]&&y==2*dy[d]&&old==NG2_TILE_DIRT&&latest==NG2_TILE_FLOOR){
            inner=1;continue;
        }
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_DIRT&&latest!=NG2_TILE_STONE))return 0;
    }
    return clipped||inner||remote_wall||p->opened_entry_parent;
}
/* The closed door is beyond the unchanged dig cell. Its observed GOLD pair
 * must be perpendicular to the input axis, in both source and latest frame. */
static int closed_door_two_ahead(const NG2Scene *s,int d){
    int x=2*dx[d],y=2*dy[d];
    return tile(s,x,y)==NG2_TILE_DOOR
        &&tile(s,x+dy[d],y-dx[d])==NG2_TILE_GOLD
        &&tile(s,x-dy[d],y+dx[d])==NG2_TILE_GOLD;
}
/* Exactly one already observed FLOOR leads to the same closed bracket. This
 * is a route qualification, not door-open or entry credit. */
static int closed_floor_one_ahead(const NG2Scene *a,const NG2Scene *b,const NG2Decision *choice){
    int i,gold_a=0,gold_b=0,d=choice->direction;
    if(d<1||d>4||choice->reason!=7||choice->obstacle!=NG2_TILE_FLOOR
        ||choice->target_x!=dx[d]||choice->target_y!=dy[d]
        ||a->goods!=NG2_GOODS_UNKNOWN||b->goods!=NG2_GOODS_UNKNOWN
        ||!closed_door_two_ahead(a,d)||!closed_door_two_ahead(b,d))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        if(a->protected_cells[i]||b->protected_cells[i]
            ||a->tiles[i]==NG2_TILE_ITEM||b->tiles[i]==NG2_TILE_ITEM)return 0;
        gold_a+=a->tiles[i]==NG2_TILE_GOLD;gold_b+=b->tiles[i]==NG2_TILE_GOLD;
    }
    return gold_a==2&&gold_b==2;
}
/* Keep an entrance or the same observed-floor vantage through irrelevant
 * remote flicker. Ticket/before and all bounds stay fixed;
 * do not grant safe-floor calibration, reissue or reference eligibility. */
static int quiet_gate_scene(const NG2Controller *p,const NG2Scene *scene,NG2Decision *out){
    NG2Decision before,latest;NG2Motion motion;int i,d=p->command.direction;
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    int obstacle=p->command_choice.obstacle;
    int entrance_step=p->command_choice.reason==5
        &&(obstacle==NG2_TILE_FLOOR||obstacle==NG2_TILE_DOOR);
    int interior_step=p->entrance.valid==1&&p->before.goods==NG2_GOODS_PARTIAL
        &&scene->goods==NG2_GOODS_PARTIAL&&p->command_choice.reason==8&&obstacle==NG2_TILE_FLOOR;
    int approach_step=p->entrance.valid==0&&p->before.goods==NG2_GOODS_UNKNOWN
        &&scene->goods==NG2_GOODS_UNKNOWN&&p->command_choice.reason==8&&obstacle==NG2_TILE_FLOOR;
    int dirt_step=d>=1&&d<=4&&!p->entrance.valid&&p->before.goods==NG2_GOODS_UNKNOWN
        &&scene->goods==NG2_GOODS_UNKNOWN&&p->command_choice.reason==6&&obstacle==NG2_TILE_DIRT
        &&p->command_choice.target_x==dx[d]&&p->command_choice.target_y==dy[d]
        &&p->s.current_command_id==p->command.id&&e&&e->command.id==p->command.id&&!e->begin_ns&&!e->outcome
        &&closed_door_two_ahead(&p->before,d)&&closed_door_two_ahead(scene,d);
    int closed_floor_step=!p->passage_active&&!p->entrance.valid
        &&p->s.current_command_id==p->command.id&&e&&e->command.id==p->command.id&&!e->begin_ns&&!e->outcome
        &&closed_floor_one_ahead(&p->before,scene,&p->command_choice);
    int opened_entry=entrance_step&&obstacle==NG2_TILE_FLOOR
        &&p->before.goods==NG2_GOODS_PARTIAL&&scene->goods==NG2_GOODS_PARTIAL
        &&last_ack_opened_gate(p,d);
    int gold_changed=!same_gold(&p->before,scene);
    int growth=gold_changed&&(opened_entry||interior_step)
        &&distant_gold_growth(&p->before,scene,d)&&distant_gold_growth(&p->scene,scene,d);
    int clipped_entry=clipped_entry_top(p,scene);
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->finish_requested||p->s.goods
        ||p->replan_pending||p->continuous_pending||!p->s.lead_confirmed||!p->s.moves
        ||p->s.phase!=NG2_PHASE_WALK||!p->continuous_ticket_valid||d<1||d>4
        ||(!entrance_step&&!interior_step&&!approach_step&&!dirt_step&&!closed_floor_step)
        ||(entrance_step&&(p->command_choice.target_x!=dx[d]||p->command_choice.target_y!=dy[d]))
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=scene->goods||scene->goods<NG2_GOODS_UNKNOWN||scene->goods>NG2_GOODS_PARTIAL
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||(gold_changed&&!growth&&!clipped_entry)
        ||(!clipped_entry&&memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT))
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=obstacle||tile(scene,dx[d],dy[d])!=obstacle
        ||(entrance_step&&(!gate_at(&p->before,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d]))))return 0;
    for(i=0;i<5;++i)
        if(protected_route_cell(&p->before,scene,dx[i],dy[i])
            ||protected_route_cell(&p->before,scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        int shielded=opened_entry&&x*dx[d]+y*dy[d]==2&&abs(x*dy[d]-y*dx[d])==1
            &&((a==NG2_TILE_FLOOR&&b==NG2_TILE_DIRT)||(a==NG2_TILE_DIRT&&b==NG2_TILE_FLOOR))
            &&tile(&p->before,x-dx[d],y-dy[d])==NG2_TILE_GOLD
            &&tile(scene,x-dx[d],y-dy[d])==NG2_TILE_GOLD
            &&!protected_at(&p->before,x,y)&&!protected_at(scene,x,y);
        if(a==b)continue;
        /* A new STONE classification uses the separate independent refresh,
         * never this cheap same-ticket palette qualification. */
        if(closed_floor_step&&((a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT)))return 0;
        if(clipped_entry&&i/23==0&&p->before.protected_cells[i])continue;
        if(dirt_step&&(p->before.protected_cells[i]||scene->protected_cells[i]))return 0;
        if(growth&&b==NG2_TILE_GOLD)continue;
        if((!shielded&&((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)))
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT&&a!=NG2_TILE_STONE)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE))return 0;
    }
    if(!choose_step(p,&p->before,&before)||!choose_step(p,scene,&latest)
        ||!same_choice(&before,&p->command_choice)||!same_choice(&before,&latest)
        ||!ng2_motion(&p->before,scene,d,&motion)||motion.kind!=NG2_BLOCKED||motion.dx||motion.dy)return 0;
    if(out)*out=latest;
    return 1;
}
static int quiet_gate_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    uint64_t aligned;
    if(p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH||now>continuous_horizon(p)
        ||(p->command_sync_deadline&&now>=p->command_sync_deadline)
        ||now-p->s.walk_started_ns>=45*SECOND||now-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    return quiet_gate_scene(p,scene,NULL);
}
/* Only the live, unstarted observed-floor approach may reuse this scene
 * proof after its input window expires. Its caller retires the old ticket;
 * this predicate grants neither an expired send nor a new timing budget. */
static int unsent_quiet_approach_scene(const NG2Controller *p,const NG2Scene *scene,NG2Decision *out){
    int i;
    if(p->passage_active||p->entrance.valid||p->replan_pending||p->continuous_pending
        ||p->command_choice.reason!=8||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(p->before.tiles[i]!=scene->tiles[i]
            &&(p->before.protected_cells[i]||scene->protected_cells[i]))return 0;
    return quiet_gate_scene(p,scene,out);
}
static int continuous_allowed(int validation){
    return validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED||validation==NG2_REVALIDATE_FRESH_ALLOWED;
}
/* Retiring an unsent door ticket grants no replacement input. Keep its
 * original geometric permission fixed while independent later captures and
 * a fresh HUD fit establish a new, bounded action. */
static int gate_refresh_scene(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->gate_refresh_anchor;
    const NG2Decision *choice=&p->gate_refresh_choice;
    NG2Decision before,latest;int i,d=choice->direction;
    if(d<1||d>4||p->entrance.valid||choice->reason!=5||choice->obstacle!=NG2_TILE_DOOR
        ||choice->target_x!=dx[d]||choice->target_y!=dy[d]
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||tile(a,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(a,dx[d],dy[d])!=NG2_TILE_DOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_DOOR
        ||!gate_at(a,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d])
        ||!same_gold(a,scene)||memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    for(i=0;i<5;++i)
        if(protected_at(scene,dx[i],dy[i])||protected_at(scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],now=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(old==now)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)
            ||(now!=NG2_TILE_UNKNOWN&&now!=NG2_TILE_FLOOR&&now!=NG2_TILE_DIRT&&now!=NG2_TILE_STONE))return 0;
    }
    return choose_step(p,a,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,choice)&&same_choice(&before,&latest);
}
static int terrain_refresh_scene(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->gate_refresh_anchor;
    const NG2Decision *choice=&p->gate_refresh_choice;
    NG2Decision before,latest;int i,d=choice->direction;
    if(d<1||d>4||choice->reason!=7||choice->obstacle!=NG2_TILE_FLOOR
        ||choice->target_x!=dx[d]||choice->target_y!=dy[d]
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||tile(a,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(a,dx[d],dy[d])!=NG2_TILE_FLOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!same_gold(a,scene)||memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    for(i=0;i<5;++i)
        if(protected_at(scene,dx[i],dy[i])||protected_at(scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],now=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(old==now)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)
            ||(now!=NG2_TILE_UNKNOWN&&now!=NG2_TILE_FLOOR&&now!=NG2_TILE_DIRT&&now!=NG2_TILE_STONE))return 0;
    }
    return choose_step(p,a,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,choice)&&same_choice(&before,&latest);
}
static int start_gate_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Motion unresolved,texture;uint64_t budget,aligned;
    if(p->gate_refresh_used||p->gate_refresh_state||p->stationary_gate_retry_waiting
        ||p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||!p->command.id
        ||p->s.current_command_id!=p->command.id||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->finish_requested||p->s.terminal||p->s.goods||!p->s.lead_confirmed||!p->s.moves
        ||p->s.inputs>=16||!p->latest_verified_ns||!p->continuous_ticket_valid
        ||p->replan_pending||p->continuous_pending||p->proof_deadline||p->s.phase!=NG2_PHASE_WALK
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    budget=minimum(p->latest_verified_ns+12*SECOND,p->s.walk_started_ns+45*SECOND);
    budget=minimum(budget,session_bound(p));
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget)return 0;
    p->gate_refresh_anchor=p->before;p->gate_refresh_choice=p->command_choice;
    if(!gate_refresh_scene(p,scene)
        ||!ng2_motion(&p->before,scene,p->command.direction,&unresolved)
        ||unresolved.kind!=NG2_MOTION_UNKNOWN
        ||!ng2_motion(scene,scene,p->command.direction,&texture)
        ||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy)return 0;
    p->gate_refresh_used=1;p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;
    p->gate_refresh_deadline=budget;p->gate_refresh_prefix=p->s.last_completed_id;
    p->gate_refresh_previous=*scene;p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
    p->gate_refresh_proof_id=0;
    p->sync_ns=p->latest_verified_ns;
    ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;
    p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    not_sent(p,end,NG2_REASON_SCREEN);
    clear_slots(p);clear_model(p);p->motion_wait.active=0;p->visual_phase_failed=0;
    p->s.phase=NG2_PHASE_SYNC;
    return 1;
}
/* This apparent opening happened before begin, so it is not input success.
 * Withdraw the dig ticket and observe the newly visible floor independently;
 * the old model may remain useful, but neither the old ID nor credit survives. */
static int start_terrain_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Decision before,latest;NG2Motion opening,texture;
    uint64_t budget,aligned;int i,d=p->command.direction;
    if(p->terrain_refresh_used||p->gate_refresh_state||p->stationary_gate_retry_waiting
        ||p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||d<1||d>4||!p->command.id
        ||p->s.current_command_id!=p->command.id||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->finish_requested||p->s.terminal||p->s.goods||!p->s.lead_confirmed||!p->s.moves
        ||p->s.inputs>=16||!p->latest_verified_ns||!p->continuous_ticket_valid
        ||p->replan_pending||p->continuous_pending||p->proof_deadline||p->s.phase!=NG2_PHASE_WALK
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned)
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=NG2_TILE_DIRT||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!same_gold(&p->before,scene)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    budget=minimum(p->latest_verified_ns+12*SECOND,p->s.walk_started_ns+45*SECOND);
    budget=minimum(budget,session_bound(p));
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget)return 0;
    for(i=0;i<5;++i)
        if(protected_at(scene,dx[i],dy[i])||protected_at(scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a==b||(x==dx[d]&&y==dy[d]))continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT&&a!=NG2_TILE_STONE)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE))return 0;
    }
    if(!choose_step(p,&p->before,&before)
        ||!same_choice(&before,&p->command_choice)||before.direction!=d||before.reason!=6
        ||before.target_x!=dx[d]||before.target_y!=dy[d]||before.obstacle!=NG2_TILE_DIRT
        ||!choose_step(p,scene,&latest)
        ||latest.direction!=d||latest.reason!=7||latest.target_x!=dx[d]||latest.target_y!=dy[d]
        ||latest.obstacle!=NG2_TILE_FLOOR
        ||!ng2_motion(&p->before,scene,d,&opening)||opening.kind!=NG2_TERRAIN_OPENED||opening.dx||opening.dy
        ||!ng2_motion(scene,scene,d,&texture)||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy)return 0;
    p->terrain_refresh_used=1;p->terrain_refresh_active=1;
    p->gate_refresh_anchor=*scene;p->gate_refresh_choice=latest;
    p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;p->gate_refresh_proof_id=0;
    p->gate_refresh_deadline=budget;p->gate_refresh_prefix=p->s.last_completed_id;
    p->gate_refresh_previous=*scene;p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
    p->sync_ns=p->latest_verified_ns;
    ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    not_sent(p,end,NG2_REASON_SCREEN);
    clear_slots(p);p->motion_wait.active=0;p->visual_phase_failed=0;p->s.phase=NG2_PHASE_SYNC;
    p->proof_capture_id=id;
    return 1;
}
/* Only this closed, two-cell floor approach extends observation refresh to
 * remote STONE palette changes. All nearby material and the gold bracket
 * remain the fixed formal permission, not a transitive motion reference. */
static int closed_approach_refresh(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->gate_refresh_anchor;
    const NG2Decision *choice=&p->gate_refresh_choice;
    int i,gold=0,d=choice->direction,x,y;
    if(d<1||d>4||p->entrance.valid||!p->s.lead_confirmed||!level_moves(p)
        ||choice->reason!=7||choice->obstacle!=NG2_TILE_FLOOR
        ||choice->target_x!=2*dx[d]||choice->target_y!=2*dy[d]
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN)return 0;
    x=3*dx[d];y=3*dy[d];
    if(tile(a,x,y)!=NG2_TILE_DOOR||tile(scene,x,y)!=NG2_TILE_DOOR
        ||tile(a,x+dy[d],y-dx[d])!=NG2_TILE_GOLD
        ||tile(a,x-dy[d],y+dx[d])!=NG2_TILE_GOLD
        ||tile(scene,x+dy[d],y-dx[d])!=NG2_TILE_GOLD
        ||tile(scene,x-dy[d],y+dx[d])!=NG2_TILE_GOLD)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        x=i%23-11;y=i/23-5;
        gold+=a->tiles[i]==NG2_TILE_GOLD;
        if(((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))
            &&(a->tiles[i]!=scene->tiles[i]||a->protected_cells[i]!=scene->protected_cells[i]))return 0;
    }
    return gold==2;
}
/* The distance-one form remains a separate formal scope. Nearby material
 * and the complete old/new Decision are still checked before a fresh pair. */
static int closed_floor_refresh(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->gate_refresh_anchor;int i,d=p->gate_refresh_choice.direction;
    if(p->passage_active||p->entrance.valid||!p->s.lead_confirmed||!level_moves(p)
        ||!closed_floor_one_ahead(a,scene,&p->gate_refresh_choice))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5;
        if(((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))
            &&(a->tiles[i]!=scene->tiles[i]||a->protected_cells[i]!=scene->protected_cells[i]))return 0;
    }
    return 1;
}
static int observation_refresh_scene(const NG2Controller *p,const NG2Scene *scene,
    NG2Decision *changed_choice){
    const NG2Scene *a=&p->gate_refresh_anchor;
    const NG2Decision *choice=&p->gate_refresh_choice;
    NG2Decision before,latest;NG2Motion still;int i,stone_change=0,d=choice->direction;
    if(d<1||d>4||choice->obstacle!=NG2_TILE_FLOOR
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR||a->goods!=scene->goods
        ||scene->goods<NG2_GOODS_UNKNOWN||scene->goods>NG2_GOODS_PARTIAL
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||tile(a,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(a,dx[d],dy[d])!=NG2_TILE_FLOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!same_gold(a,scene)||memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    for(i=0;i<5;++i)
        if(protected_route_cell(a,scene,dx[i],dy[i])
            ||protected_route_cell(a,scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],now=scene->tiles[i];
        if(old==now)continue;
        if(a->protected_cells[i]||scene->protected_cells[i])return 0;
        if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT)
            ||(now!=NG2_TILE_UNKNOWN&&now!=NG2_TILE_FLOOR&&now!=NG2_TILE_DIRT)){
            if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)
                ||(now!=NG2_TILE_UNKNOWN&&now!=NG2_TILE_FLOOR&&now!=NG2_TILE_DIRT&&now!=NG2_TILE_STONE))return 0;
            stone_change=1;
        }
    }
    if(p->observation_refresh_active==NG2_OBSERVATION_REFRESH_VANTAGE_REPLAN
        &&memcmp(a->tiles,scene->tiles,NG2_TILE_COUNT))return 0;
    if((p->observation_refresh_active==NG2_OBSERVATION_REFRESH_SIDE_OPENING
            ||p->observation_refresh_active==NG2_OBSERVATION_REFRESH_VANTAGE_REPLAN)
        &&(!ng2_motion(a,scene,d,&still)||still.kind!=NG2_BLOCKED||still.dx||still.dy))return 0;
    if(!choose_step(p,a,&before)||!choose_step(p,scene,&latest)||!same_choice(&before,choice))return 0;
    if(!same_choice(&before,&latest)){
        /* A failed cached-source proof never supplies a replacement choice.
         * Both real chooser results are evaluated once, without rescue. */
        if(changed_choice)*changed_choice=latest;
        return 0;
    }
    return !stone_change||((closed_approach_refresh(p,scene)||closed_floor_refresh(p,scene))
        &&ng2_motion(a,scene,d,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy);
}
/* A single newly lit side floor can shorten a known-gold approach before
 * begin. This is a new observation route, never a dig or movement credit. */
static int side_opening_floor(const NG2Controller *p,const NG2Scene *scene,
    const NG2Decision *latest){
    const NG2Scene *a=&p->before;const NG2Decision *old=&p->command_choice;
    int d=old->direction,n=latest->direction;
    if(p->passage_active||p->entrance.valid||d<1||d>4||n<1||n>4
        ||d!=p->command.direction||dx[d]*dx[n]+dy[d]*dy[n]
        ||old->reason!=8||latest->reason!=8
        ||old->obstacle!=NG2_TILE_FLOOR||latest->obstacle!=NG2_TILE_FLOOR
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||!actual_gold(a)||!same_gold(a,scene)
        ||!safe_floor(a,d)||!safe_floor(scene,d)||!safe_floor(scene,n)
        ||tile(a,dx[n],dy[n])!=NG2_TILE_DIRT||tile(scene,dx[n],dy[n])!=NG2_TILE_FLOOR)return 0;
    return 1;
}
static int side_opening_refresh_scene(const NG2Controller *p,const NG2Scene *scene,
    const NG2Decision *latest){
    const NG2Scene *a=&p->before;int i,changed=0,n=latest->direction;
    if(!side_opening_floor(p,scene,latest))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||a->tiles[i]==NG2_TILE_ITEM||scene->tiles[i]==NG2_TILE_ITEM)return 0;
        if(a->tiles[i]==scene->tiles[i])continue;
        if(i!=tile_index(dx[n],dy[n]))return 0;
        ++changed;
    }
    return changed==1;
}
/* One side floor may become visible together with one remote DIRT restriction.
 * This is a separate observation permission, never a broad monotone rule or
 * a MOVE credit. The fixed latest anchor needs an independent exact reproof. */
static int composite_side_opening_refresh_scene(const NG2Controller *p,const NG2Scene *scene,
    const NG2Decision *latest){
    const NG2Scene *a=&p->before;int i,opened=0,restricted=0,d=p->command.direction,n=latest->direction;
    if(p->cycle_full_framing||p->entry.active||p->lower.active
        ||!side_opening_floor(p,scene,latest))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5,old=a->tiles[i],now=scene->tiles[i];
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||old==NG2_TILE_ITEM||now==NG2_TILE_ITEM)return 0;
        if(old==now)continue;
        if(x==dx[n]&&y==dy[n]&&old==NG2_TILE_DIRT&&now==NG2_TILE_FLOOR){++opened;continue;}
        if(old!=NG2_TILE_DIRT||now!=NG2_TILE_STONE
            ||(abs(x)<=1&&abs(y)<=1)
            ||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(abs(x-dx[n])<=1&&abs(y-dy[n])<=1))return 0;
        ++restricted;
    }
    return opened==1&&restricted==1;
}
/* A different observed-floor vantage can become shorter without changing the
 * already observed next step. Only the discarded route may lose one remote
 * STONE observation; the new step's entire local material remains fixed. */
static int vantage_replan_refresh_scene(const NG2Controller *p,const NG2Scene *scene,
    const NG2Decision *latest){
    const NG2Scene *a=&p->before;const NG2Decision *old=&p->command_choice;
    int i,stone_loss=0,opened=0,d=old->direction,n=latest->direction;
    /* latest is supplied only after observation_refresh_scene's one normal
     * old-choice calculation matched the complete cached permission. A failed
     * source calculation leaves it zero and must never be retried here. */
    if(p->passage_active||p->entrance.valid||p->cycle_full_framing||p->entry.active||p->lower.active
        ||d<1||d>4||n<1||n>4||d!=p->command.direction||dx[d]*dx[n]+dy[d]*dy[n]
        ||old->reason!=8||latest->reason!=8
        ||old->obstacle!=NG2_TILE_FLOOR||latest->obstacle!=NG2_TILE_FLOOR
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||!actual_gold(a)||!same_gold(a,scene)
        ||!safe_floor(a,d)||!safe_floor(scene,d)||!safe_floor(a,n)||!safe_floor(scene,n)
        ||tile(a,latest->target_x,latest->target_y)!=NG2_TILE_FLOOR
        ||tile(scene,latest->target_x,latest->target_y)!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5,before=a->tiles[i],after=scene->tiles[i];
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||before==NG2_TILE_ITEM||after==NG2_TILE_ITEM)return 0;
        if(before==after)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[n])<=1&&abs(y-dy[n])<=1)
            ||(x==latest->target_x&&y==latest->target_y))return 0;
        if(before==NG2_TILE_STONE&&after==NG2_TILE_UNKNOWN){++stone_loss;continue;}
        if((before!=NG2_TILE_UNKNOWN&&before!=NG2_TILE_FLOOR&&before!=NG2_TILE_DIRT)
            ||(after!=NG2_TILE_UNKNOWN&&after!=NG2_TILE_FLOOR&&after!=NG2_TILE_DIRT))return 0;
        if(before==NG2_TILE_DIRT&&after==NG2_TILE_FLOOR&&x*dx[n]+y*dy[n]>1)++opened;
    }
    return stone_loss==1&&opened>0;
}
/* An exhausted logical ticket need not end a stationary, known-floor walk.
 * Withdraw it first. A later independent pair and future preparation window
 * authorize a different ID; no old timing, epoch or input credit survives. */
static int start_observation_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Motion still,texture;NG2Decision latest={0};uint64_t budget,aligned;
    int d=p->command.direction,mode=1;
    if(p->observation_refresh_count>=8||p->observation_refresh_verified==p->latest_verified_ns
        ||p->gate_refresh_state||p->stationary_gate_retry_waiting
        ||p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||d<1||d>4||!p->command.id
        ||p->s.current_command_id!=p->command.id||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->finish_requested||p->s.terminal||p->s.goods||!p->s.lead_confirmed||!p->s.moves
        ||p->s.inputs>=16||!p->latest_verified_ns||!p->continuous_ticket_valid
        ||p->replan_pending||p->continuous_pending||p->proof_deadline||p->s.phase!=NG2_PHASE_WALK
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    budget=minimum(p->latest_verified_ns+12*SECOND,p->s.walk_started_ns+45*SECOND);
    budget=minimum(budget,session_bound(p));
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget)return 0;
    p->gate_refresh_anchor=p->before;p->gate_refresh_choice=p->command_choice;
    if(!observation_refresh_scene(p,scene,&latest)){
        if(side_opening_refresh_scene(p,scene,&latest))mode=NG2_OBSERVATION_REFRESH_SIDE_OPENING;
        else if(composite_side_opening_refresh_scene(p,scene,&latest)
            ||vantage_replan_refresh_scene(p,scene,&latest))mode=NG2_OBSERVATION_REFRESH_VANTAGE_REPLAN;
        else return 0;
    }
    if(!ng2_motion(&p->before,scene,d,&still)||still.kind!=NG2_BLOCKED||still.dx||still.dy
        ||!ng2_motion(scene,scene,d,&texture)||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy)return 0;
    ++p->observation_refresh_count;p->observation_refresh_verified=p->latest_verified_ns;
    p->observation_refresh_active=mode;
    p->gate_refresh_anchor=*scene;if(mode!=1)p->gate_refresh_choice=latest;
    p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;p->gate_refresh_proof_id=0;
    p->gate_refresh_deadline=budget;p->gate_refresh_prefix=p->s.last_completed_id;
    p->gate_refresh_previous=*scene;p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
    p->sync_ns=p->latest_verified_ns;
    ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    not_sent(p,end,NG2_REASON_SCREEN);
    clear_slots(p);p->motion_wait.active=0;p->visual_phase_failed=0;p->s.phase=NG2_PHASE_SYNC;
    p->proof_capture_id=id;
    return 1;
}
/* UNKNOWN never becomes a motion result here. Retire the unsent permission,
 * keep its original world/Scene fixed, and wait for direct strict evidence. */
static int stationary_wait_world(const NG2Controller *p){
    return p->s.x==p->stationary_wait_x&&p->s.y==p->stationary_wait_y
        &&p->s.inputs==p->stationary_wait_inputs&&p->s.moves==p->stationary_wait_moves
        &&!memcmp(p->visits,p->stationary_wait_visits,sizeof(p->visits))
        &&!memcmp(&p->entrance,&p->stationary_wait_entrance,sizeof(p->entrance))
        &&p->passage_active==p->stationary_wait_passage&&p->passage_bit==p->stationary_wait_bit
        &&!p->passage_wait_kind&&p->passage_pending==p->stationary_wait_pending
        &&p->passage_inspected==p->stationary_wait_inspected
        &&p->passage_unresolved==p->stationary_wait_unresolved
        &&p->passage_closed==p->stationary_wait_closed;
}
static int stationary_wait_scene(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->gate_refresh_anchor;const NG2Decision *choice=&p->gate_refresh_choice;
    NG2Decision before,latest;int i,d=choice->direction;
    if(!stationary_wait_world(p)||d<1||d>4||choice->obstacle!=NG2_TILE_FLOOR
        ||choice->reason!=(p->stationary_wait_passage?10:8)
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||!safe_step(p,a,d)||!safe_step(p,scene,d)
        ||!same_gold(a,scene)||memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    if(p->stationary_wait_passage){if(!passage_floor(a)||!passage_floor(scene))return 0;}
    else if(a->gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!has_gold_tiles(a))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest_tile=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(old==latest_tile)continue;
        if(a->protected_cells[i]||(!p->stationary_wait_passage
                &&((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)))
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_STONE)
            ||(latest_tile!=NG2_TILE_UNKNOWN&&latest_tile!=NG2_TILE_FLOOR
                &&latest_tile!=NG2_TILE_DIRT&&latest_tile!=NG2_TILE_STONE))return 0;
    }
    return choose_step(p,a,&before)&&choose_step(p,scene,&latest)
        &&same_choice(&before,choice)&&same_choice(&before,&latest);
}
/* Observation, publication and begin share the same definitely-unsent owner.
 * Scalar evidence never rewrites normal Motion or grants displacement credit. */
static int stationary_source_owner(const NG2Controller *p){
    const NG2StationarySupport *s=&p->stationary_support;size_t i;int source=0;
    if(!p->stationary_wait_active||s->owner_start!=p->s.started_ns||s->trigger!=p->stationary_wait_trigger_id
        ||s->prefix!=p->gate_refresh_prefix||s->prefix!=p->s.last_completed_id
        ||s->W!=p->gate_refresh_deadline||s->P!=p->stationary_wait_parent)return 0;
    for(i=0;i<p->event_count;++i){
        const NG2ControllerEvent *e=&p->events[i];
        if(e->command.id==s->source_command&&e->command.kind==NG2_ACTION_MOVE
            &&e->command.source_capture_id==s->source_id&&e->command.source_start_ns==s->source_start
            &&!e->begin_ns&&e->outcome==3){source=1;break;}
    }
    return source;
}
static int stationary_support_zero(const NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end){
    const NG2StationarySupport *s=&p->stationary_support;
    return s->active&&stationary_source_owner(p)&&id>s->id&&start>=s->end
        &&end>start&&end>=s->start&&end-s->start<=FRESH
        &&ng2_single_gold_dirt_support_zero(&p->gate_refresh_anchor,&s->scene,scene,
        p->gate_refresh_choice.direction);
}
static int stationary_current_owner(const NG2Controller *p){
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    return stationary_source_owner(p)&&!p->finish_requested&&!p->s.terminal&&!p->s.goods&&!p->cycle.candidate_latched
        &&(p->gate_refresh_state==NG2_GATE_REFRESH_READY||p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED)
        &&p->last_observed_prefix==p->gate_refresh_prefix
        &&e&&e->command.id==p->command.id&&e->command.kind==NG2_ACTION_MOVE&&!e->begin_ns
        &&((p->s.input_state==0&&!p->s.current_command_id&&e->outcome==3)
            ||(p->s.input_state==1&&p->s.current_command_id==p->command.id&&!e->outcome));
}
static int stationary_wait_zero(const NG2Controller *p,const NG2Scene *scene,const NG2Motion *still,
    int32_t scoped_zero,uint64_t id,uint64_t start,uint64_t end){
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    if(still->kind==NG2_BLOCKED&&!still->dx&&!still->dy)return 1;
    if(still->kind!=NG2_MOTION_UNKNOWN||still->dx||still->dy
        ||!p->stationary_wait_active
        ||p->finish_requested||p->s.terminal||p->s.goods
        ||(p->s.input_state!=0&&p->s.input_state!=1)
        ||(p->gate_refresh_state!=NG2_GATE_REFRESH_OBSERVE
            &&p->gate_refresh_state!=NG2_GATE_REFRESH_READY
            &&p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED)
        ||p->s.last_completed_id!=p->gate_refresh_prefix
        ||p->last_observed_prefix!=p->gate_refresh_prefix
        ||!e||e->command.id!=p->command.id||e->command.kind!=NG2_ACTION_MOVE||e->begin_ns
        ||(p->s.input_state==0&&(p->s.current_command_id||e->outcome!=3))
        ||(p->s.input_state==1&&(p->s.current_command_id!=p->command.id||e->outcome))
        ||!stationary_wait_scene(p,scene))return 0;
    if(!p->stationary_wait_passage)return scoped_zero||stationary_support_zero(p,scene,id,start,end);
    return ng2_clear_singleton_stationary_zero(&p->gate_refresh_anchor,scene,
        p->gate_refresh_choice.direction)
        ||ng2_clear_plural_stationary_zero(&p->gate_refresh_anchor,scene,
            p->gate_refresh_choice.direction)
        ||ng2_clear_singleton_phase_stationary_zero(&p->gate_refresh_anchor,scene,
            p->gate_refresh_choice.direction)
        ||ng2_clear_plural_palette_stationary_zero(&p->gate_refresh_anchor,scene,
            p->gate_refresh_choice.direction)
        ||scoped_zero;
}
static int unlocalized_stationary_wait(const NG2Controller *p){
    return p->stationary_wait_active&&p->stationary_wait_passage
        &&unlocalized_gold_floor(&p->gate_refresh_anchor);
}
static uint64_t stationary_wait_limit(const NG2Controller *p){
    return p->gate_refresh_state==NG2_GATE_REFRESH_OBSERVE?
        minimum(p->gate_refresh_deadline,p->stationary_wait_parent):p->stationary_wait_parent;
}
/* Lost current proof withdraws an already-owned wait's permission, not its
 * fixed anchor or clocks. An issued replacement may retire only before begin. */
static int stationary_wait_observe(NG2Controller *p,const NG2Scene *scene,
    const NG2Motion *still,uint64_t id,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);
    if(!p->stationary_wait_active||still->kind!=NG2_MOTION_UNKNOWN||still->dx||still->dy
        ||!stationary_wait_scene(p,scene)
        ||!e||e->command.kind!=NG2_ACTION_MOVE||e->command.id!=p->command.id||e->begin_ns)return 0;
    if(p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED){
        if(p->s.input_state!=1||p->s.current_command_id!=p->command.id||e->outcome)return 0;
        not_sent(p,end,NG2_REASON_SCREEN);p->preparation_epoch=0;p->motion_wait.active=0;
    }else if((p->gate_refresh_state!=NG2_GATE_REFRESH_OBSERVE&&p->gate_refresh_state!=NG2_GATE_REFRESH_READY)
        ||p->s.input_state||p->s.current_command_id||e->outcome!=3)return 0;
    /* READY/ISSUED retained P only while direct proof stayed valid. Losing
     * it cannot reopen OBSERVE at or beyond its original two-beat W. */
    if(now>=p->gate_refresh_deadline){finish(p,now,NG2_REASON_BEAT);return 1;}
    p->stationary_qualification.valid=0;
    p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;p->gate_refresh_proof_id=0;
    p->proof_capture_id=id;clear_recovery_slot(p);p->s.next_target_ns=0;
    p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->s.phase=NG2_PHASE_SYNC;
    return 1;
}
static int stationary_wait_compare(const NG2Controller *p,const NG2Scene *scene,
    NG2Motion *still,int32_t *zero){
    *zero=0;
    if(unlocalized_stationary_wait(p))
        return ng2_unlocalized_passage_motion_zero(&p->gate_refresh_anchor,scene,
            p->gate_refresh_choice.direction,still,zero);
    if(!p->stationary_wait_passage)
        return ng2_single_gold_dirt_motion_zero(&p->gate_refresh_anchor,scene,
            p->gate_refresh_choice.direction,still,zero);
    return ng2_motion(&p->gate_refresh_anchor,scene,p->gate_refresh_choice.direction,still);
}
/* Observe has already proved these exact C-owned bytes. This capability
 * caches no matcher/model result; every live owner/window/phase gate remains. */
static int stationary_wait_proof(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    const NG2StationaryQualification *q=&p->stationary_qualification;
    const NG2StationarySupport *s=&p->stationary_support;
    return q->valid&&stationary_current_owner(p)&&stationary_wait_scene(p,scene)
        &&q->owner_start==p->s.started_ns&&q->trigger==p->stationary_wait_trigger_id
        &&q->source_command==s->source_command&&q->source_id==s->source_id&&q->source_start==s->source_start
        &&q->prefix==p->gate_refresh_prefix&&q->prefix==p->last_observed_prefix
        &&q->W==p->gate_refresh_deadline&&q->P==p->stationary_wait_parent
        &&q->capture_id==p->gate_refresh_proof_id&&q->capture_id==p->s.last_capture_id
        &&q->start==p->s.last_capture_start_ns&&q->end==p->s.last_capture_end_ns
        &&q->support_id==(s->active?s->id:0)&&q->support_start==(s->active?s->start:0)
        &&q->support_end==(s->active?s->end:0)&&q->support_qualified==(s->active?s->qualified:0)
        &&p->model_capture_id>=q->capture_id&&fresh(p,now)&&now<stationary_wait_limit(p)
        &&!memcmp(scene,&p->scene,sizeof(*scene))&&!memcmp(&q->scene,&p->scene,sizeof(*scene));
}
static void stationary_qualify_current(NG2Controller *p,uint64_t id,uint64_t start,uint64_t end,uint64_t prefix){
    NG2StationaryQualification *q=&p->stationary_qualification;
    const NG2StationarySupport *s=&p->stationary_support;
    q->valid=0;
    if(!stationary_current_owner(p)||!stationary_wait_scene(p,&p->scene)||!ng2_beat_model_valid(&p->model)
        ||!p->gate_refresh_proof_id||p->gate_refresh_proof_id!=id
        ||p->s.last_capture_id!=id||p->s.last_capture_start_ns!=start||p->s.last_capture_end_ns!=end
        ||p->last_observed_prefix!=prefix||prefix!=p->gate_refresh_prefix)return;
    q->owner_start=p->s.started_ns;q->trigger=p->stationary_wait_trigger_id;
    q->source_command=s->source_command;q->source_id=s->source_id;q->source_start=s->source_start;
    q->prefix=prefix;q->W=p->gate_refresh_deadline;q->P=p->stationary_wait_parent;
    q->capture_id=id;q->start=start;q->end=end;q->support_id=s->active?s->id:0;
    q->support_start=s->active?s->start:0;q->support_end=s->active?s->end:0;
    q->support_qualified=s->active?s->qualified:0;
    memcpy(&q->scene,&p->scene,sizeof(q->scene));q->valid=1;
}
static void record_change(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    int mask,int changed_tiles,int changed_protected,int allowed,int validation);
static int start_stationary_wait(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Motion unresolved,texture;uint64_t budget,aligned;
    int d=p->command.direction,mask,tiles,protected_cells;
    if(p->observation_refresh_count>=8||p->observation_refresh_verified==p->latest_verified_ns
        ||p->gate_refresh_state||p->stationary_gate_retry_waiting||p->passage_wait_kind
        ||p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||d<1||d>4||!p->command.id
        ||p->s.current_command_id!=p->command.id||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->finish_requested||p->s.terminal||p->s.goods||!p->s.lead_confirmed||!p->s.moves
        ||p->s.inputs>=16||!p->latest_verified_ns||!p->continuous_ticket_valid
        ||p->replan_pending||p->continuous_pending||p->proof_deadline||p->s.phase!=NG2_PHASE_WALK
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now<p->command.phase_sample_ns
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    budget=minimum(p->command.source_start_ns+FRESH,p->command.phase_sample_ns+FRESH);
    budget=minimum(budget,p->latest_verified_ns+12*SECOND);
    budget=minimum(budget,p->s.walk_started_ns+45*SECOND);
    budget=minimum(budget,session_bound(p));
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget)return 0;
    p->gate_refresh_anchor=p->before;p->gate_refresh_choice=p->command_choice;
    p->stationary_wait_x=p->s.x;p->stationary_wait_y=p->s.y;
    p->stationary_wait_inputs=p->s.inputs;p->stationary_wait_moves=p->s.moves;
    p->stationary_wait_entrance=p->entrance;
    memcpy(p->stationary_wait_visits,p->visits,sizeof(p->visits));
    p->stationary_wait_passage=p->passage_active;p->stationary_wait_bit=p->passage_bit;
    p->stationary_wait_pending=p->passage_pending;p->stationary_wait_inspected=p->passage_inspected;
    p->stationary_wait_unresolved=p->passage_unresolved;p->stationary_wait_closed=p->passage_closed;
    if(!stationary_wait_scene(p,scene)||!ng2_motion(&p->before,scene,d,&unresolved)
        ||unresolved.kind!=NG2_MOTION_UNKNOWN||!ng2_motion(scene,scene,d,&texture)
        ||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy)return 0;
    mask=scene_change(&p->before,scene,&tiles,&protected_cells);
    if(mask&&p->passage_active)record_change(p,scene,id,mask,tiles,protected_cells,0,NG2_REVALIDATE_MOTION);
    ++p->observation_refresh_count;p->observation_refresh_verified=p->latest_verified_ns;
    p->stationary_wait_active=1;p->stationary_wait_parent=budget;p->stationary_wait_trigger_id=id;
    p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;p->gate_refresh_proof_id=0;
    p->gate_refresh_deadline=minimum(budget,now+2*p->command_period);
    p->gate_refresh_prefix=p->s.last_completed_id;
    memset(&p->stationary_support,0,sizeof(p->stationary_support));
    p->stationary_support.owner_start=p->s.started_ns;p->stationary_support.trigger=id;
    p->stationary_support.source_command=p->command.id;
    p->stationary_support.source_id=p->command.source_capture_id;
    p->stationary_support.source_start=p->command.source_start_ns;
    p->stationary_support.prefix=p->gate_refresh_prefix;
    p->stationary_support.W=p->gate_refresh_deadline;p->stationary_support.P=budget;
    p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
    p->sync_ns=p->latest_verified_ns;
    ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,now,id);
    not_sent(p,end,NG2_REASON_SCREEN);clear_slots(p);
    p->motion_wait.active=0;p->visual_phase_failed=0;p->s.phase=NG2_PHASE_SYNC;p->proof_capture_id=id;
    return 1;
}
/* The retired unsent source still equals this fixed anchor before issuance.
 * Only a real Scene difference can use the existing nonzero-mask journal. */
static void record_stationary_failure(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,int validation){
    const NG2ControllerEvent *e=event(p);int mask,tiles,protected_cells;
    if(!p->stationary_wait_active||p->finish_requested||p->s.input_state
        ||(p->gate_refresh_state!=NG2_GATE_REFRESH_OBSERVE&&p->gate_refresh_state!=NG2_GATE_REFRESH_READY)
        ||p->command.kind!=NG2_ACTION_MOVE||!p->command.source_capture_id
        ||!e||e->command.id!=p->command.id||e->begin_ns||e->outcome!=3
        ||p->replan_pending||p->continuous_pending
        ||memcmp(&p->before,&p->gate_refresh_anchor,sizeof(p->before))
        ||id<=p->stationary_wait_trigger_id||start<p->gate_refresh_previous_end
        ||p->s.last_completed_id!=p->gate_refresh_prefix||!stationary_wait_world(p))return;
    mask=scene_change(&p->before,scene,&tiles,&protected_cells);
    if(mask)record_change(p,scene,id,mask,tiles,protected_cells,0,validation);
}
static int update_stationary_wait(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Motion still;int32_t zero;
    uint64_t deadline=stationary_wait_limit(p);
    if(now>=deadline){finish(p,now,NG2_REASON_BEAT);return 0;}
    if(id==p->stationary_wait_trigger_id)return 1; /* Trigger is not independent proof. */
    p->gate_refresh_proof_id=0;
    if(id<p->stationary_wait_trigger_id||start<p->gate_refresh_previous_end
        ||p->s.last_completed_id!=p->gate_refresh_prefix||!stationary_wait_world(p)){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(!stationary_wait_compare(p,scene,&still,&zero)){
        record_stationary_failure(p,scene,id,start,NG2_REVALIDATE_MOTION);
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(p->stationary_wait_passage&&actual_gold(scene)){
        if(still.kind!=NG2_BLOCKED||still.dx||still.dy){
            record_stationary_failure(p,scene,id,start,NG2_REVALIDATE_MOTION);
            finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        /* Retain P through the existing independent gold handoff. */
        p->stationary_wait_active=0;p->gate_refresh_state=NG2_GATE_REFRESH_NONE;
        begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_GOLD);return 1;
    }
    if(!stationary_wait_scene(p,scene)){
        record_stationary_failure(p,scene,id,start,NG2_REVALIDATE_ROUTE);
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(!p->stationary_wait_passage&&!p->stationary_support.active&&now<p->gate_refresh_deadline
        &&((still.kind==NG2_BLOCKED&&!still.dx&&!still.dy)
            ||(still.kind==NG2_MOTION_UNKNOWN&&!still.dx&&!still.dy&&zero))
        &&(zero||ng2_single_gold_dirt_support_zero(&p->gate_refresh_anchor,scene,scene,
            p->gate_refresh_choice.direction))){
        p->stationary_support.active=1;p->stationary_support.scene=*scene;
        p->stationary_support.id=id;p->stationary_support.start=start;p->stationary_support.end=end;
        p->stationary_support.qualified=now;
    }
    if(stationary_wait_zero(p,scene,&still,zero,id,start,end)){
        p->gate_refresh_proof_id=id;p->proof_capture_id=id;
        if(p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED)p->gate_refresh_state=NG2_GATE_REFRESH_READY;
    }else if(stationary_wait_observe(p,scene,&still,id,end,now)){
        /* A later independent direct-anchor proof and current fit may retry
         * publication within the same original two-beat observation bound. */
    }else if(p->gate_refresh_state!=NG2_GATE_REFRESH_OBSERVE||still.kind!=NG2_MOTION_UNKNOWN){
        record_stationary_failure(p,scene,id,start,NG2_REVALIDATE_MOTION);
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    return 1;
}
static int update_gate_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Motion still,texture;int d=p->gate_refresh_choice.direction;
    int opened=p->opened_entry_parent&&p->observation_refresh_active
        &&p->gate_refresh_choice.reason==5&&p->gate_refresh_choice.obstacle==NG2_TILE_FLOOR;
    if(p->stationary_wait_active)return update_stationary_wait(p,scene,id,start,end,now);
    if(now>=p->gate_refresh_deadline){finish(p,now,NG2_REASON_BEAT);return 0;}
    p->gate_refresh_proof_id=0;
    if(opened&&p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED
        &&start<p->opened_entry_recovery_ns)return 1;
    if(p->s.last_completed_id!=p->gate_refresh_prefix
        ||(opened&&(memcmp(p->gate_refresh_anchor.tiles,scene->tiles,NG2_TILE_COUNT)
            ||memcmp(p->gate_refresh_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT)))
        ||!(p->observation_refresh_active?observation_refresh_scene(p,scene,NULL):
            p->terrain_refresh_active?terrain_refresh_scene(p,scene):gate_refresh_scene(p,scene))
        ||start<p->gate_refresh_previous_end||now<p->gate_refresh_previous_start
        ||now-p->gate_refresh_previous_start>FRESH
        ||!ng2_motion(opened?&p->gate_refresh_anchor:p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED?&p->before:
            &p->gate_refresh_previous,scene,d,&still)){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(still.kind==NG2_BLOCKED&&!still.dx&&!still.dy){
        p->gate_refresh_proof_id=id;
        if(p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED)p->gate_refresh_state=NG2_GATE_REFRESH_READY;
    }else if(p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED||still.kind!=NG2_MOTION_UNKNOWN
        ||!ng2_motion(scene,scene,d,&texture)||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }else p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;
    if(p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED){
        p->gate_refresh_previous=*scene;p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
    }
    return 1;
}
/* Only a definitely-unsent ticket may be replaced. Unlike initial lead
 * calibration, continuous revalidation proves the cached source decision,
 * the current action and protected set, without searching for another beat. */
static int continuous_validation(NG2Controller *p,const NG2Scene *scene,uint64_t end,NG2Decision *latest){
    NG2Decision before,after;NG2Motion motion;uint64_t aligned;
    int direction=p->command.direction,strict=0,fresh_allowed,revealed=0,opened=0;
    if(p->s.input_state!=1||p->replan_pending||p->continuous_pending||p->finish_requested
        ||!p->s.lead_confirmed||!p->s.moves||p->s.phase!=NG2_PHASE_WALK||!p->continuous_ticket_valid
        ||p->command.kind!=NG2_ACTION_MOVE||direction<1||direction>4)return NG2_REVALIDATE_STATE;
    if(p->continuous_chain_count>=2||p->continuous_count>=8)return NG2_REVALIDATE_BUDGET;
    if(end>p->continuous_ticket.deadline_ns||!ng2_beat_model_valid(&p->model)||p->beat_failed
        ||end<p->continuous_ticket.phase_sample_ns||end-p->continuous_ticket.phase_sample_ns>FRESH
        ||end<p->continuous_ticket.source_start_ns||end-p->continuous_ticket.source_start_ns>FRESH
        ||end<p->model.last_ns||end-p->model.last_ns>FRESH||end>continuous_horizon(p)
        ||end-p->s.walk_started_ns>=45*SECOND||end-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return NG2_REVALIDATE_TIMING;
    if(p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||!safe_step(p,&p->before,direction)||!safe_step(p,scene,direction))strict=NG2_REVALIDATE_FLOOR;
    if(p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!same_gold(&p->before,scene)){if(!strict)strict=NG2_REVALIDATE_GOLD;}
    if(memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)){
        if(!strict)strict=NG2_REVALIDATE_PROTECTED;}
    fresh_allowed=p->before.state==NG2_FLOOR&&scene->state==NG2_FLOOR
        &&p->before.goods==NG2_GOODS_UNKNOWN&&scene->goods==NG2_GOODS_UNKNOWN
        &&p->before.gold_state==NG2_GOLD_CANDIDATE&&scene->gold_state==NG2_GOLD_CANDIDATE
        &&tile(&p->before,0,0)==NG2_TILE_FLOOR&&tile(scene,0,0)==NG2_TILE_FLOOR
        &&(monotone_terrain(&p->before,scene)
            ||(strict==NG2_REVALIDATE_GOLD
                &&(revealed=revealed_approach_terrain(&p->before,scene,direction))));
    if(strict)opened=opened_entry_relation(p,scene);
    if(opened)fresh_allowed=1;
    if(strict&&!fresh_allowed)return strict;
    /* One cached-source proof serves both policies. A second planner call
     * must never rescue a failed full Decision from the first call. */
    if(!choose_step(p,&p->before,&before)
        ||before.direction!=direction||!same_choice(&before,&p->command_choice))return NG2_REVALIDATE_ROUTE;
    if(!choose_step(p,scene,&after)
        ||after.direction<1||after.direction>4)return NG2_REVALIDATE_ROUTE;
    if(opened&&!same_choice(&before,&after))return NG2_REVALIDATE_ROUTE;
    if(revealed&&(before.reason!=8||after.reason!=7||before.direction!=after.direction
        ||before.obstacle!=NG2_TILE_FLOOR||after.obstacle!=NG2_TILE_FLOOR
        ||before.target_x!=2*dx[direction]||before.target_y!=2*dy[direction]
        ||before.target_x!=after.target_x||before.target_y!=after.target_y))return NG2_REVALIDATE_ROUTE;
    if(!same_continuous_action(&before,&after)&&!strict)strict=NG2_REVALIDATE_ROUTE;
    if(strict&&!fresh_allowed)return strict;
    if(!ng2_motion(&p->before,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)return NG2_REVALIDATE_MOTION;
    if(opened&&!p->opened_entry_parent)
        p->opened_entry_parent=minimum(p->continuous_motion_deadline,
            minimum(continuous_horizon(p),sync_deadline(p)));
    *latest=after;
    if(strict)return NG2_REVALIDATE_FRESH_ALLOWED;
    return NG2_REVALIDATE_CONTINUOUS_ALLOWED;
}
/* Optional recognition evidence never supplies input authority. Its original
 * Scene, logical ticket and absolute horizons survive a qualified reissue. */
static int reference_same_move(const NG2Controller *p,int acknowledged){
    const NG2Command *a=&p->motion_reference_ticket,*b=&p->command;
    return p->motion_reference_present&&p->s.lead_confirmed&&p->s.moves>0
        &&b->kind==NG2_ACTION_MOVE&&a->ordinal==b->ordinal&&a->direction==b->direction
        &&a->target_ns==b->target_ns&&a->not_before_ns==b->not_before_ns&&a->deadline_ns==b->deadline_ns
        &&p->command_period==p->motion_reference_period
        &&p->schedule_deadline==p->motion_reference_deadline
        &&p->s.last_completed_id==(acknowledged?b->id:p->motion_reference_prefix)
        &&p->s.inputs==p->motion_reference_inputs+acknowledged&&p->s.moves==p->motion_reference_moves
        &&p->s.x==p->motion_reference_x&&p->s.y==p->motion_reference_y
        &&!memcmp(p->visits,p->motion_reference_visits,sizeof(p->visits))
        &&!memcmp(&p->entrance,&p->motion_reference_entrance,sizeof(p->entrance));
}
static int reference_time_valid(NG2Controller *p,uint64_t now,int acknowledged){
    const NG2Command *ticket=&p->motion_reference_ticket;uint64_t aligned;
    return reference_same_move(p,acknowledged)&&ng2_beat_model_valid(&p->model)&&!p->beat_failed
        &&now>=ticket->source_start_ns&&now-ticket->source_start_ns<=FRESH
        &&now>=ticket->phase_sample_ns&&now-ticket->phase_sample_ns<=FRESH
        &&now>=p->model.last_ns&&now-p->model.last_ns<=FRESH
        &&now<=p->motion_reference_deadline&&now<=p->s.walk_started_ns+45*SECOND
        &&now<=session_bound(p)
        &&(acknowledged||now<=ticket->deadline_ns)
        &&corrected(p,ticket->target_ns,p->motion_reference_period,&aligned);
}
static void validate_motion_reference(NG2Controller *p,const NG2Scene *scene,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Decision original,latest;NG2Motion motion;int direction=p->motion_reference_ticket.direction;
    if(!p->motion_reference_present||!p->motion_reference_valid)return;
    if((p->s.input_state!=1&&!p->continuous_pending)||p->finish_requested||p->s.phase!=NG2_PHASE_WALK
        ||prefix!=p->motion_reference_prefix||start>now||end>now||start>end||now-start>FRESH
        ||!reference_time_valid(p,now,0)||direction<1||direction>4
        ||p->motion_reference_scene.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->motion_reference_scene.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||p->motion_reference_scene.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!safe_step(p,&p->motion_reference_scene,direction)||!safe_step(p,scene,direction)
        ||!same_gold(&p->motion_reference_scene,scene)
        ||memcmp(p->motion_reference_scene.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!choose_step(p,&p->motion_reference_scene,&original)
        ||!same_choice(&original,&p->motion_reference_choice)||!same_choice(&original,&p->command_choice)
        ||!choose_step(p,scene,&latest)
        ||!same_choice(&original,&latest)
        ||!ng2_motion(&p->motion_reference_scene,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)p->motion_reference_valid=0;
}
/* An optional newer primary source may replace one definitely-unsent ID.
 * P/10 coalesces pre-input captures; only ordinary strict-zero Motion proves
 * the unchanged position. The frozen logical source, not a reissued source,
 * supplies that spacing origin. Exhausted budgets leave the old ID intact. */
static int preinput_same_source(const NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,uint64_t now,
    int zero_proven,NG2Decision *latest){
    NG2Decision before,after;NG2Motion zero;const NG2ControllerEvent *e;
    uint64_t epoch;int i,d=p->command.direction;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||d<1||d>4
        ||p->event_count>=EVENT_CAP||p->continuous_chain_count>=2||p->continuous_count>=8
        ||p->finish_requested||p->s.terminal||p->replan_pending||p->continuous_pending
        ||p->stationary_wait_active||p->passage_wait_kind||p->gate_refresh_state
        ||p->terrain_refresh_active||p->observation_refresh_active||p->entry.active
        ||p->lower.active||p->upper.active||p->cycle_partial_credit||p->cycle_full_framing
        ||p->stationary_gate_retry_waiting||p->command_choice.reason==9
        ||p->command_choice.obstacle!=NG2_TILE_FLOOR||now>=p->command.not_before_ns
        ||prefix!=p->s.last_completed_id||p->last_observed_prefix!=prefix
        ||id<=p->command.source_capture_id||start< p->s.last_capture_end_ns
        ||end<=start||now<end||start<p->continuous_ticket.source_start_ns
        ||!p->continuous_period
        ||start-p->continuous_ticket.source_start_ns<p->continuous_period/10)return 0;
    epoch=ng2_controller_preparation_epoch(p,p->command.id,now);
    if(!epoch||p->preinput_refresh_epoch==epoch)return 0;
    e=p->event_count?&p->events[p->event_count-1]:NULL;
    if(!e||e->command.id!=p->command.id||e->begin_ns||e->outcome
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||(p->before.gold_state!=NG2_GOLD_CLEAR&&p->before.gold_state!=NG2_GOLD_CANDIDATE)
        ||p->before.gold_state!=scene->gold_state||!same_gold(&p->before,scene)
        ||!safe_step(p,&p->before,d)||!safe_step(p,scene,d)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||(p->passage_active?!passage_source_world(p,now):!reference_same_move(p,0)))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a==NG2_TILE_ITEM||b==NG2_TILE_ITEM)return 0;
        if(a==b)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_STONE&&a!=NG2_TILE_DIRT)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_STONE&&b!=NG2_TILE_DIRT))return 0;
    }
    if(!choose_step(p,&p->before,&before)||!same_choice(&before,&p->command_choice)
        ||!choose_step(p,scene,&after)||!same_choice(&before,&after))return 0;
    if(!zero_proven&&(!ng2_motion(&p->before,scene,d,&zero)
        ||zero.kind!=NG2_BLOCKED||zero.dx||zero.dy))return 0;
    *latest=after;return 1;
}
static void create_motion_reference(NG2Controller *p){
    NG2Decision choice;int direction=p->command.direction;
    p->motion_reference_present=p->motion_reference_valid=p->motion_reference_reissued=0;
    if(p->passage_active||!p->s.lead_confirmed||!p->s.moves||direction<1||direction>4||p->scene.gold_state!=NG2_GOLD_CANDIDATE
        ||!safe_step(p,&p->scene,direction)
        ||!choose_step(p,&p->scene,&choice)
        ||!same_choice(&choice,&p->command_choice))return;
    p->motion_reference_scene=p->scene;p->motion_reference_ticket=p->command;p->motion_reference_choice=choice;
    p->motion_reference_entrance=p->entrance;memcpy(p->motion_reference_visits,p->visits,sizeof(p->visits));
    p->motion_reference_prefix=p->s.last_completed_id;p->motion_reference_period=p->command_period;
    p->motion_reference_deadline=p->schedule_deadline;
    p->motion_reference_x=p->s.x;p->motion_reference_y=p->s.y;
    p->motion_reference_moves=p->s.moves;p->motion_reference_inputs=p->s.inputs;
    p->motion_reference_present=p->motion_reference_valid=1;
}
static int motion_reference_eligible(NG2Controller *p,uint64_t now){
    if(!p->motion_reference_present||!p->motion_reference_valid||!p->motion_reference_reissued)return 0;
    if(!reference_time_valid(p,now,1)){p->motion_reference_valid=0;return 0;}
    return 1;
}
static NG2ControllerMotionReference *motion_reference_row(NG2Controller *p){
    NG2ControllerMotionReference *row=p->motion_reference_count?&p->motion_references[p->motion_reference_count-1]:NULL;
    return row&&row->command_id==p->command.id?row:NULL;
}
static void record_change_basis(NG2Controller *p,const NG2Scene *source,uint64_t source_id,
    uint64_t command_id,const NG2Scene *scene,uint64_t id,int mask,int changed_tiles,
    int changed_protected,int allowed,int validation,int cycle){
    NG2ControllerSceneChange *change;NG2ControllerSceneDetail *detail;size_t at;int k,total=0;
    if(p->scene_change_count<3)at=p->scene_change_count++;
    else {p->scene_changes[1]=p->scene_changes[2];p->scene_details[1]=p->scene_details[2];at=2;}
    change=&p->scene_changes[at];detail=&p->scene_details[at];
    memset(change,0,sizeof(*change));memset(detail,0,sizeof(*detail));
    change->command_id=command_id;
    change->source_capture_id=source_id;
    change->observed_capture_id=id;change->target_ns=p->command.target_ns;
    change->deadline_ns=p->command.deadline_ns;
    change->change_mask=mask;change->changed_tiles=changed_tiles;change->changed_protected=changed_protected;
    change->state_before=source->state;change->state_after=scene->state;
    change->goods_before=source->goods;change->goods_after=scene->goods;
    change->replan_count=cycle?0:p->replan_count+(validation==NG2_REVALIDATE_INITIAL_ALLOWED);
    change->replan_allowed=allowed;
    detail->command_id=change->command_id;detail->source_capture_id=change->source_capture_id;
    detail->observed_capture_id=id;detail->validation=validation;
    detail->continuous_count=cycle?0:p->continuous_count+continuous_allowed(validation);
    detail->chain_count=cycle?0:p->continuous_chain_count+continuous_allowed(validation);
    for(k=0;k<NG2_TILE_COUNT;++k)if(source->tiles[k]!=scene->tiles[k]
        ||source->protected_cells[k]!=scene->protected_cells[k]){
        if(total<4){NG2ControllerCellChange *cell=&detail->cells[total];
            cell->x=k%23-11;cell->y=k/23-5;cell->tile_before=source->tiles[k];cell->tile_after=scene->tiles[k];
            cell->protected_before=source->protected_cells[k];cell->protected_after=scene->protected_cells[k];}
        ++total;
    }
    detail->cell_count=total<4?total:4;detail->omitted_cells=total-detail->cell_count;
}
static void record_change(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    int mask,int changed_tiles,int changed_protected,int allowed,int validation){
    uint64_t source=(p->replan_pending||p->continuous_pending)?p->s.last_capture_id:p->command.source_capture_id;
    record_change_basis(p,&p->before,source,p->command.id,scene,id,mask,changed_tiles,
        changed_protected,allowed,validation,0);
}
/* Same-ACK state3 cannot replace before. Journal the rejected state without
 * claiming a motion assessment or changing the existing SCREEN stop. */
static void record_ack_nonfloor_failure(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    const NG2ControllerEvent *e=event(p);int mask,tiles,protected_cells;
    if(p->s.input_state!=3||p->command.kind!=NG2_ACTION_MOVE||!p->command.id
        ||!p->command.source_capture_id||p->finish_requested||p->s.terminal||p->s.goods
        ||p->replan_pending||p->continuous_pending
        ||p->s.current_command_id!=p->command.id||p->s.last_completed_id!=p->command.id
        ||p->last_observed_prefix!=p->command.id
        ||!e||memcmp(&e->command,&p->command,sizeof(p->command))||e->outcome!=2
        ||!e->begin_ns||!e->end_ns||e->begin_ns>e->end_ns||e->end_ns!=p->ack_ns
        ||!p->motion_wait.active||p->motion_wait.command_id!=p->command.id
        ||p->motion_wait.source_capture_id!=p->command.source_capture_id
        ||p->before.state!=NG2_FLOOR||scene->state==NG2_FLOOR
        ||id<=p->command.source_capture_id||start<p->ack_ns
        ||start<p->command.source_start_ns||end<=start||now<end
        ||now>p->motion_wait.deadline_ns)return;
    mask=scene_change(&p->before,scene,&tiles,&protected_cells);
    if(mask)record_change(p,scene,id,mask,tiles,protected_cells,0,NG2_REVALIDATE_STATE);
}
NG2Controller *ng2_controller_create(uint64_t now){
    NG2Controller *p;
    if(!valid_time(now)||now>NS_LIMIT-180*SECOND-1)return NULL;
    p=(NG2Controller*)calloc(1,sizeof(*p));
    if(p){p->s.abi_version=NG2_ABI_VERSION;p->s.struct_size=sizeof(p->s);p->s.started_ns=now;
        p->last_now=now;p->transition_ns=now;p->s.lead_ns=leads[0];p->visits[16*33+16]=1;}
    return p;
}
NG2Controller *ng2_controller_create_cycle(uint64_t now){
    NG2Controller *p=ng2_controller_create(now);
    if(p){p->cycle_enabled=1;p->cycle.abi_version=1;p->cycle.struct_size=sizeof(p->cycle);
        p->cycle.level_id=1;p->cycle.state=NG2_CYCLE_SEARCH;}
    return p;
}
void ng2_controller_cycle_status(const NG2Controller *p,NG2ControllerCycleStatus *out){
    if(out){if(p&&p->cycle_enabled)*out=p->cycle;else memset(out,0,sizeof(*out));}
}
void ng2_controller_destroy(NG2Controller *p){free(p);}
/* This is a new, bounded attempt after an ACK-known stationary input, never
 * replay of an unknown input or displacement credit for a missed beat. Only
 * the same observed FLOOR entrance may request a fresh model once per run. */
static int stationary_gate_scene(const NG2Controller *p,const NG2Scene *scene){
    NG2Decision before,latest;NG2Motion still;
    int i,d=p->command.direction;
    if(d<1||d>4||p->entrance.valid
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!gate_at(&p->before,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d])
        ||memcmp(p->before.tiles,scene->tiles,sizeof(scene->tiles)))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(p->before.protected_cells[i]||scene->protected_cells[i])return 0;
    if(!choose_step(p,&p->before,&before)
        ||!choose_step(p,scene,&latest)
        ||!same_choice(&before,&p->command_choice)||!same_choice(&before,&latest)
        ||before.direction!=d||before.reason!=5||before.target_x!=dx[d]
        ||before.target_y!=dy[d]||before.obstacle!=NG2_TILE_FLOOR)return 0;
    return ng2_motion(&p->before,scene,d,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
static int stationary_gate_proof(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    const NG2ControllerEvent *e;uint64_t budget;
    if(p->finish_requested||p->s.terminal||p->s.goods
        ||!p->s.lead_confirmed||p->s.moves<=0||!p->latest_verified_ns||p->s.inputs>=16
        ||p->command.kind!=NG2_ACTION_MOVE||p->s.last_completed_id!=p->command.id
        ||!stationary_gate_scene(p,scene))return 0;
    e=p->event_count?&p->events[p->event_count-1]:NULL;
    if(!e||e->outcome!=2||e->motion!=NG2_BLOCKED||e->dx||e->dy)return 0;
    budget=minimum(p->latest_verified_ns+12*SECOND,p->s.walk_started_ns+45*SECOND);
    budget=minimum(budget,session_bound(p));
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    return now<budget;
}
static int credit_unit_move(NG2Controller *p,const NG2Scene *before,const NG2Scene *scene,
    int direction,const NG2Motion *motion,const NG2ControllerEvent *e,uint64_t end){
    NG2Entrance entered;
    if(motion->kind!=NG2_MOVED||motion->dx!=dx[direction]||motion->dy!=dy[direction]){
        finish(p,end,NG2_REASON_MOVEMENT);return 0;
    }
    p->opened_entry_parent=p->opened_entry_recovery_ns=0;
    if(ng2_entered_gate(before,scene,direction,p->s.x,p->s.y,motion->kind,&entered))p->entrance=entered;
    p->s.x+=motion->dx;p->s.y+=motion->dy;++p->s.moves;
    p->cycle_partial_rebind_used=0;
    if(p->s.x < -16||p->s.x>16||p->s.y < -16||p->s.y>16){finish(p,end,NG2_REASON_LIMIT);return 0;}
    if(p->visits[(p->s.y+16)*33+p->s.x+16]<UINT16_MAX)++p->visits[(p->s.y+16)*33+p->s.x+16];
    p->s.lead_confirmed=1;p->latest_verified_ns=p->observe_now;
    if(!p->s.first_move_ns&&e)p->s.first_move_ns=e->begin_ns;
    return 1;
}
static void resolve_move(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t end){
    NG2Motion motion;NG2Decision decision;NG2ControllerEvent *e=event(p);
    NG2ControllerMotionReference *reference=motion_reference_row(p);
    uint64_t earliest=maximum(p->ack_ns,p->command.target_ns+80000000);
    int direction=p->command.direction;
    if(start<earliest)return;
    if(end>p->motion_wait.deadline_ns||p->observe_now>p->motion_wait.deadline_ns){
        recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,end>p->motion_wait.deadline_ns?
            NG2_RECOVERY_CAPTURE_END:NG2_RECOVERY_ACTUAL_COMMIT,
            end>p->motion_wait.deadline_ns?end:p->observe_now,id);
        end_visual_wait(p);
        finish(p,end,NG2_REASON_LATE);return;
    }
    /* Inspect fresh visual proof often enough to preserve the next beat.
     * Reserve the last bounded comparison for the original full-period
     * opportunity; early UNKNOWN/TWEEN can never consume that final chance. */
    if(p->motion_wait.attempts){
        if(start<p->motion_retry_last_ns||start-p->motion_retry_last_ns<p->command_period/10)return;
        if(p->motion_wait.attempts==MOTION_ASSESSMENTS-1
            &&(start<p->motion_retry_start_ns||start-p->motion_retry_start_ns<p->command_period))return;
    }
    if(!ng2_motion(&p->before,scene,direction,&motion)){motion.kind=NG2_MOTION_UNKNOWN;motion.dx=motion.dy=0;}
    if(reference){
        NG2Motion fallback;int eligible=motion_reference_eligible(p,p->observe_now);
        reference->observed_capture_id=id;reference->reference_eligible=eligible;
        reference->primary_motion=motion.kind;reference->fallback_attempted=0;reference->fallback_motion=0;
        reference->selected_capture_id=p->command.source_capture_id;reference->selected_motion=motion.kind;
        if(motion.kind==NG2_MOTION_UNKNOWN&&eligible){
            reference->fallback_attempted=1;
            if(!ng2_motion(&p->motion_reference_scene,scene,direction,&fallback)){
                fallback.kind=NG2_MOTION_UNKNOWN;fallback.dx=fallback.dy=0;
            }
            reference->fallback_motion=fallback.kind;
            if(fallback.kind==NG2_MOVED&&fallback.dx==dx[direction]&&fallback.dy==dy[direction]){
                motion=fallback;reference->selected_capture_id=p->motion_reference_ticket.source_capture_id;
                reference->selected_motion=motion.kind;
            }
        }
    }
    if(!p->motion_wait.attempts)p->motion_retry_start_ns=start;
    p->motion_retry_last_ns=start;
    ++p->motion_wait.attempts;p->motion_wait.last_capture_id=id;p->motion_wait.last_motion=motion.kind;
    if(e){e->observed_capture_id=id;e->motion=motion.kind;e->dx=motion.dx;e->dy=motion.dy;}
    if(irregular_blocked(p,scene,id,start,end,&motion))return;
    if((motion.kind==NG2_TWEEN||motion.kind==NG2_MOTION_UNKNOWN)&&p->motion_wait.attempts<MOTION_ASSESSMENTS)return;
    irregular_clear_first(p);
    end_visual_wait(p);
    if(motion.kind==NG2_MOVED){
        if(!credit_unit_move(p,&p->before,scene,direction,&motion,e,end))return;
    }else if(motion.kind==NG2_DOOR_OPENED||motion.kind==NG2_TERRAIN_OPENED){
        if(motion.kind==NG2_DOOR_OPENED)++p->s.door_changes;else ++p->s.terrain_changes;
        p->latest_verified_ns=p->observe_now;
        /* An opening is a verified terrain change, never the displacement
         * proof required to calibrate native lead or begin continuous beats. */
        if(!p->s.lead_confirmed){
            p->proof_deadline=p->motion_wait.deadline_ns;p->proof_capture_id=id;p->proof_reacquire=1;
            p->s.next_target_ns=0;p->next_nominal=0;p->s.phase=NG2_PHASE_SYNC;return;
        }
    }else if(motion.kind==NG2_BLOCKED&&!p->s.lead_confirmed){
        if(!safe_step(p,&p->before,direction)||!safe_step(p,scene,direction)||!same_gold(&p->before,scene)
            ||!choose_step(p,scene,&decision)
            ||decision.direction!=direction||p->lead_index>=6){finish(p,end,NG2_REASON_MOVEMENT);return;}
        if(!p->have_anchor){p->retune_anchor=p->before;p->retune_direction=direction;p->have_anchor=1;}
        ++p->lead_index;p->s.lead_ns=leads[p->lead_index];p->s.next_target_ns=0;p->next_nominal=0;
        p->proof_deadline=p->motion_wait.deadline_ns;p->proof_capture_id=id;p->proof_reacquire=1;
        p->s.phase=NG2_PHASE_SYNC;return;
    }else if(motion.kind==NG2_BLOCKED&&!p->stationary_gate_retry_used
        &&stationary_gate_proof(p,scene,p->observe_now)){
        ++p->stationary_gate_retry_used;
        if(p->recovery.mode!=NG2_RECOVERY_POST_MOVE){
            ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;
            p->recovery.mode=NG2_RECOVERY_POST_MOVE;
            p->sync_ns=p->latest_verified_ns;
        }
        recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_COMMIT,p->observe_now,id);
        p->proof_deadline=p->motion_wait.deadline_ns;p->proof_capture_id=id;p->proof_reacquire=0;
        clear_slots(p);clear_model(p);p->visual_phase_failed=0;
        p->stationary_gate_recovery_pending=1;
        p->stationary_gate_retry_waiting=NG2_GATE_RETRY_REFIT;
        p->s.phase=NG2_PHASE_SYNC;return;
    }else {finish(p,end,NG2_REASON_MOVEMENT);return;}
    p->s.last_ordinal=p->command.ordinal;
    if(p->command_period>=NS_LIMIT||p->command.target_ns>=NS_LIMIT-p->command_period){
        p->s.next_target_ns=0;p->next_nominal=0;finish(p,end,NG2_REASON_SESSION);return;
    }
    /* Captures can finish before the parent bound and commit after it. The
     * first actual tick must confirm that horizon before issuing a child. */
    p->proof_deadline=p->motion_wait.deadline_ns;p->proof_capture_id=id;p->proof_reacquire=0;
    p->next_update_deadline=p->schedule_deadline;
    p->next_nominal=p->command.target_ns+p->command_period;p->next_period=p->command_period;
    if(!update_next_slot_candidate(p))p->beat_failed=1;
    p->s.phase=NG2_PHASE_WALK;
}
/* Cycle evidence never becomes a UI source. Only observe() installs current
 * stable-prefix authority; the worker/writer methods below consume identities. */
static void cycle_failure(NG2Controller *p,uint64_t now,int status,int reason){
    restart_yield_invalidate(p);
    if(p->cycle_current_active){p->cycle_current_invalid=1;p->cycle_current_active=0;}
    if(p->cycle.pending&&p->cycle.state==NG2_CYCLE_ASSESS&&!p->cycle_assessing)p->cycle_late_worker=1;
    freeze_stop_detail(p,now,reason,NULL);p->handoff_fault=1;
    if(p->entry.active){p->entry.stage=6;p->entry.valid=0;}
    if(p->lower.active)p->lower.stage=6;
    if(p->upper.active){p->upper.stage=6;p->upper.valid=0;}
    if(p->s.input_state==1&&(p->command.kind==NG2_ACTION_MOVE||p->command.kind==NG2_ACTION_RESTART))
        not_sent(p,now,reason);
    p->cycle_partial_credit=p->cycle_framing_credit=p->cycle_full_framing=p->cycle_refresh_safe=0;p->cycle.pending=0;p->cycle.status=status;
    p->cycle_full_source_valid=p->cycle_full_data_active=p->cycle_full_data_blocked=0;
    p->cycle_retry_waiting=0;
    if(!p->cycle.candidate_latched)p->cycle.outcome=NG2_RING_UNKNOWN;
    p->cycle.state=NG2_CYCLE_HELD;p->cycle.assessment_ns=now;
    p->s.reason=reason;p->preparation_epoch=0;
}
static int cycle_current(const NG2Controller *p,uint64_t job,uint64_t now){
    return p&&cycle_holding(p)&&!p->s.terminal&&!p->finish_requested&&job
        &&job==p->cycle.job_id&&valid_time(now)&&now>=p->last_now;
}
static int cycle_box(const int32_t box[4]){
    static const int hud[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    size_t i;
    if(box[0]<0||box[1]<0||box[2]<=0||box[3]<=0||box[2]>896||box[3]>414
        ||box[0]>896-box[2]||box[1]>414-box[3])return 0;
    for(i=0;i<sizeof(hud)/sizeof(hud[0]);++i)
        if(box[0]<hud[i][2]&&hud[i][0]<box[0]+box[2]&&box[1]<hud[i][3]&&hud[i][1]<box[1]+box[3])return 0;
    return 1;
}
static int cycle_contains(const int32_t outer[4],const int32_t inner[4]){
    return inner[0]>=outer[0]&&inner[1]>=outer[1]
        &&inner[0]+inner[2]<=outer[0]+outer[2]&&inner[1]+inner[3]<=outer[1]+outer[3];
}
static int cycle_overlap(const int32_t a[4],const int32_t b[4]){
    return a[0]<b[0]+b[2]&&b[0]<a[0]+a[2]&&a[1]<b[1]+b[3]&&b[1]<a[1]+a[3];
}
static int cycle_score(double score,double lower){return isfinite(score)&&score>=lower&&score<=1.000001;}
static int cycle_endcap_floor(const NG2RingEndcap *sample){
    int r=sample->r,g=sample->g,b=sample->b;
    if(r<6||r>52||g<3||g>255||b<0||b>255||sample->spread!=1)return 0;
    return (r<=38&&44*r<=100*b&&100*b<=90*r&&40*r<=100*g&&100*g<=90*r
        &&abs(g-b)<=fmax(2,.18*r))||(r>38&&55*r<=100*b+155&&100*b<=70*r
        &&45*r<=100*g&&100*g<=68*r&&abs(g-b)<=fmax(2,.12*r));
}
static int cycle_no_candidate(const NG2RingSlot *slot){
    if(slot->outcome==NG2_RING_TARGET||slot->outcome==NG2_RING_CANDIDATE||slot->icon_score_exact>1
        ||slot->word_present<0||slot->word_present>1||!cycle_score(slot->icon_score,0.0)
        ||!cycle_score(slot->icon_upper_bound,0.0)
        ||(slot->word_present&&(!cycle_score(slot->word_iou,0.0)||!cycle_score(slot->word_coverage,0.0))))return 0;
    return slot->icon_score_exact?slot->icon_score<.80:slot->icon_upper_bound<.80;
}
/* Policy2 certifies the finite target-template domain, without assigning an
 * identity to the other products. The five equal cells partition primary
 * template centres; their conservative maxima are not exact sprite matches. */
static int cycle_binary_no_positive(const NG2RingSlot *slot){
    return slot->outcome<=NG2_RING_IGNORED_CONTAINER&&cycle_no_candidate(slot)&&cycle_score(slot->word_iou,0.0)
        &&cycle_score(slot->word_coverage,0.0)
        &&!(slot->word_iou>=.82&&slot->word_coverage>=.90);
}
static int cycle_zero_box(const int32_t box[4]){
    return !box[0]&&!box[1]&&!box[2]&&!box[3];
}
static int cycle_binary_cell(const NG2RingSlot *slot,int cx,int sy,int index,const int32_t strip[4]){
    const int32_t *domain=slot->non_target_icon_box,*pose=slot->icon_box;
    if(slot->cx!=cx||slot->sy!=sy||slot->slot!=index||slot->kind!=NG2_RING_GENERIC_NON_TARGET
        ||slot->outcome!=NG2_RING_NON_TARGET||slot->non_target_id||slot->ignored_container_id
        ||slot->non_target_conflict||slot->icon_score_exact
        ||slot->icon_score!=slot->icon_upper_bound||!cycle_binary_no_positive(slot)
        ||slot->non_target_icon_score!=0.0||slot->non_target_name_iou!=0.0
        ||slot->non_target_name_coverage!=0.0||slot->ignored_icon_score!=0.0
        ||slot->ignored_gold_iou!=0.0||slot->ignored_gold_coverage!=0.0
        ||slot->ignored_dark_iou!=0.0||slot->ignored_dark_coverage!=0.0
        ||!cycle_zero_box(slot->non_target_name_box)||!cycle_zero_box(slot->ignored_icon_box)
        ||domain[0]!=cx-18||domain[1]!=sy+24||domain[2]!=36||domain[3]!=67
        ||!cycle_box(domain)||!cycle_contains(strip,domain)
        ||!((pose[2]==32&&pose[3]==28)||(pose[2]==33&&pose[3]==28)
            ||(pose[2]==34&&pose[3]==29))
        ||!cycle_box(pose)||!cycle_contains(strip,pose)
        ||pose[0]+pose[2]/2<cx-18||pose[0]+pose[2]/2>=cx+18)return 0;
    if(slot->word_present){if(!cycle_box(slot->word_box))return 0;}
    else if(slot->word_iou!=0.0||slot->word_coverage!=0.0||!cycle_zero_box(slot->word_box))return 0;
    return 1;
}
static int cycle_binary_witness(const NG2RingResult *result,const NG2RingRow *row){
    const NG2RingCoverage *w=&result->certificate;int i,j,shop=0;
    if(w->non_target_items!=3||w->ignored_containers||result->partial_count!=2
        ||w->strip_box[3]!=67)return 0;
    for(i=0;i<2;++i){
        if(!cycle_score(w->sign_iou[i],0.0)||!cycle_score(w->sign_coverage[i],0.0))return 0;
        if(w->sign_iou[i]>=.94&&w->sign_coverage[i]>=.95&&cycle_box(w->sign_boxes[i]))shop=1;
    }
    if(!shop)return 0;
    for(i=0;i<result->row_count;++i)for(j=0;j<3;++j)
        if(!cycle_binary_no_positive(&result->rows[i].slots[j]))return 0;
    for(i=0;i<3;++i){
        const NG2RingSlot *slot=&row->slots[i];const int32_t *price=w->price_boxes[i];
        if(!cycle_binary_cell(slot,row->left+36*i,row->sy,i,w->strip_box)
            ||memcmp(w->item_boxes[i],slot->non_target_icon_box,sizeof(w->item_boxes[i]))
            ||!cycle_zero_box(w->name_boxes[i])||!cycle_box(price)
            ||price[0]<slot->cx-11||price[0]+price[2]>slot->cx+12
            ||price[1]<row->sy+69||price[1]+price[3]>row->sy+89)return 0;
        for(j=0;j<i;++j)if(!memcmp(price,w->price_boxes[j],sizeof(w->price_boxes[i])))return 0;
    }
    return cycle_binary_cell(&result->partial[0],row->left-36,row->sy,0,w->strip_box)
        &&cycle_binary_cell(&result->partial[1],row->left+108,row->sy,0,w->strip_box);
}
/* Policy3 uses an observed lower gold structure, not glyph or merchant
 * identity. Recompute it from the immutable source Scene; the worker's numeric
 * gold count alone is never authority. The unseen top/corner remains unknown. */
static int cycle_structural_cell(int pixel,int origin,int *cell){
    int delta=pixel-origin,value=delta/36,remainder=delta%36;
    if(remainder==18||remainder==-18)return 0;
    if(remainder>18)++value;else if(remainder<-18)--value;
    *cell=value;return 1;
}
static int cycle_structural_shape(const NG2Scene *scene,int ax,int ay,int mirror){
    int x,y,solid=ax+(mirror?4:-2),opening=ax+(mirror?-2:4);
    for(y=ay-1;y<=ay+3;++y)if(tile(scene,solid,y)!=NG2_TILE_GOLD)return 0;
    for(x=ax+(mirror?-1:-2);x<=ax+(mirror?4:3);++x)
        if(tile(scene,x,ay+3)!=NG2_TILE_GOLD)return 0;
    if(tile(scene,opening,ay)!=NG2_TILE_GOLD||tile(scene,opening,ay+2)!=NG2_TILE_GOLD)return 0;
    x=tile(scene,opening,ay+1);
    return x==NG2_TILE_FLOOR||x==NG2_TILE_DOOR;
}
static int cycle_structural_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x;
    if(scene->abi_version!=NG2_ABI_VERSION||scene->struct_size!=sizeof(*scene)
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-1 < -5||ay+3>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    /* Goods projection can legitimately protect both FLOOR endcaps. */
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    return cycle_structural_shape(scene,ax,ay,0)||cycle_structural_shape(scene,ax,ay,1);
}
/* Policy4 observes the same three offer cells below a five-cell solid side
 * and a separate two-cell doorway. It does not infer an unseen bottom wall. */
static int cycle_side_shop_shape(const NG2Scene *scene,int ax,int ay,int mirror){
    int y,solid=ax+(mirror?4:-2),opening=ax+(mirror?-2:4),middle;
    for(y=ay-3;y<=ay+1;++y)if(tile(scene,solid,y)!=NG2_TILE_GOLD)return 0;
    if(tile(scene,opening,ay-2)!=NG2_TILE_GOLD||tile(scene,opening,ay)!=NG2_TILE_GOLD)return 0;
    middle=tile(scene,opening,ay-1);return middle==NG2_TILE_FLOOR||middle==NG2_TILE_DOOR;
}
static int cycle_side_shop_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x;
    if(scene->abi_version!=NG2_ABI_VERSION||scene->struct_size!=sizeof(*scene)
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-3 < -5||ay+1>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    return cycle_side_shop_shape(scene,ax,ay,0)||cycle_side_shop_shape(scene,ax,ay,1);
}
/* Policy5 has a lower side opening two cells below the offers. Every
 * required wall and both FLOOR caps are observed in this frozen source. */
static int cycle_lower_shop_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x,y,mirror;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-1 < -5||ay+3>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(mirror=0;mirror<2;++mirror){
        int solid=ax+(mirror?4:-2),gate=ax+(mirror?-2:4),ok=1,opening=tile(scene,gate,ay+2);
        for(y=ay-1;y<=ay+3;++y)ok&=tile(scene,solid,y)==NG2_TILE_GOLD;
        for(x=ax-2;x<=ax+4;++x)ok&=tile(scene,x,ay+3)==NG2_TILE_GOLD;
        if(ok&&tile(scene,gate,ay+1)==NG2_TILE_GOLD
            &&(opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR))return 1;
    }
    return 0;
}
/* The lower rail is fully observed, including at most one interior DOOR.
 * Its extra solid-side GOLD replaces the lost rail support without filling
 * the DOOR or accepting a mere total gold count. */
static int cycle_closed_shop_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x,y,mirror;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-1 < -5||ay+3>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(mirror=0;mirror<2;++mirror){
        int solid=ax+(mirror?4:-2),gate=ax+(mirror?-2:4),ok=1,doors=0;
        int first=ax-2+mirror,last=ax+3+mirror,opening=tile(scene,gate,ay+1);
        for(y=ay-1;y<=ay+3;++y)ok&=tile(scene,solid,y)==NG2_TILE_GOLD;
        for(x=first;x<=last;++x){
            int value=tile(scene,x,ay+3);
            if(value==NG2_TILE_DOOR){
                ++doors;
                if(x==first||x==last||tile(scene,x-1,ay+3)!=NG2_TILE_GOLD
                    ||tile(scene,x+1,ay+3)!=NG2_TILE_GOLD)ok=0;
            }else if(value!=NG2_TILE_GOLD)ok=0;
        }
        if(doors>1||(doors&&(ay-2 < -5||tile(scene,solid,ay-2)!=NG2_TILE_GOLD)))ok=0;
        if(ok&&tile(scene,gate,ay)==NG2_TILE_GOLD&&tile(scene,gate,ay+2)==NG2_TILE_GOLD
            &&(opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR))return 1;
    }
    return 0;
}
static int cycle_closed_shop_faces(const NG2RingCoverage *w,const NG2RingRow *row){
    const int32_t *a=w->board_boxes[0],*b=w->board_boxes[1];int anchor;
    if(a[2]!=b[2]||abs(a[1]+a[3]-row->sy-15)>2||abs(b[1]+b[3]-row->sy-15)>2
        ||abs(a[1]+a[3]-b[1]-b[3])>2)return 0;
    for(anchor=0;anchor<2;++anchor){
        const int32_t *full=w->board_boxes[anchor],*part=w->board_boxes[1-anchor];
        if(abs(full[1]+full[3]/2-row->sy)<=2&&part[3]<=full[3]&&part[1]>=full[1])return 1;
    }
    return 0;
}
/* Policy7 has one observed full left SIGN and a separately authenticated
 * merchant. Its same-row entrance never supplies an unseen right face. */
static int cycle_single_sign_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x,y,opening;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-2 < -5||ay+2>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(y=ay-2;y<=ay+2;++y)if(tile(scene,ax-2,y)!=NG2_TILE_GOLD)return 0;
    opening=tile(scene,ax+4,ay);
    return tile(scene,ax+4,ay-1)==NG2_TILE_GOLD&&tile(scene,ax+4,ay+1)==NG2_TILE_GOLD
        &&(opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR);
}
static int cycle_single_sign_merchant(const NG2RingCoverage *w,const NG2RingRow *row){
    const int32_t *box=w->merchant_box;
    return cycle_box(box)&&box[2]==36&&box[3]==36
        &&box[0]>=row->left+15&&box[0]<=row->left+21
        &&box[1]>=row->sy-39&&box[1]<=row->sy-33
        &&cycle_score(w->merchant_score,.94)&&cycle_score(w->merchant_coverage,.95);
}
/* Policy8 positively observes a vertical lower entrance beneath the offers.
 * Ten fixed GOLD cells and both intervening FLOOR cells are independent of
 * the other structural policies' twelve-cell enclosures. */
static int cycle_bottom_shop_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x,y,opening;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-2 < -5||ay+3>4)return 0;
    for(x=ax;x<=ax+2;++x)if(tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(y=ay-2;y<=ay+1;++y)
        if(tile(scene,ax-2,y)!=NG2_TILE_GOLD||tile(scene,ax+4,y)!=NG2_TILE_GOLD)return 0;
    if(tile(scene,ax,ay+3)!=NG2_TILE_GOLD||tile(scene,ax+2,ay+3)!=NG2_TILE_GOLD
        ||tile(scene,ax+1,ay+1)!=NG2_TILE_FLOOR||tile(scene,ax+1,ay+2)!=NG2_TILE_FLOOR)return 0;
    opening=tile(scene,ax+1,ay+3);return opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR;
}
/* Policy9 authenticates the observed offer band independently of its outer
 * wall shape. Every ITEM and protected cell must belong to these three
 * offers; unseen or extra merchandise cannot inherit this certificate. */
static int cycle_observed_shop_scene(const NG2Scene *scene,const NG2RingRow *row,int red_slot){
    int ax,ay,x,i,d;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay < -5||ay+1>4)return 0;
    for(x=ax;x<=ax+2;++x)
        if(tile(scene,x,ay)!=NG2_TILE_ITEM
            ||tile(scene,x,ay+1)!=(x-ax==red_slot?NG2_TILE_UNKNOWN:NG2_TILE_FLOOR))return 0;
    if(tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int cx=i%23-11,cy=i/23-5,item=cy==ay&&cx>=ax&&cx<=ax+2,protect=0;
        if((scene->tiles[i]==NG2_TILE_ITEM)!=item)return 0;
        for(d=0;d<5;++d)
            protect|=cy+dy[d]==ay&&cx+dx[d]>=ax&&cx+dx[d]<=ax+2;
        if(scene->protected_cells[i]!=protect)return 0;
    }
    return 1;
}
/* Policy15 positively observes the higher side opening, its complete roof
 * and solid wall. Exact offer projection and lower price floors are checked
 * independently of the producer's numeric fourteen-GOLD certificate. */
static int cycle_upper_side_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,x,y,mirror;
    if(!cycle_observed_shop_scene(scene,row,-1)||row->left<197||row->left>537
        ||row->sy<21||row->sy>323
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ax-2 < -11||ax+4>11||ay-5 < -5||ay+2>4)return 0;
    for(mirror=0;mirror<2;++mirror){
        int solid=ax+(mirror?4:-2),gate=ax+(mirror?-2:4),valid=1,opening=tile(scene,gate,ay-2);
        for(y=ay-5;y<=ay+2;++y)valid&=tile(scene,solid,y)==NG2_TILE_GOLD;
        for(x=0;x<5;++x)valid&=tile(scene,solid+(mirror?-x:x),ay-5)==NG2_TILE_GOLD;
        if(valid&&tile(scene,gate,ay-3)==NG2_TILE_GOLD&&tile(scene,gate,ay-1)==NG2_TILE_GOLD
            &&(opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR))return 1;
    }
    return 0;
}
/* Policy18 is the separately observed row-one offer band after entering a
 * high side gate. Recompute its fourteen distinct roof/side/post supports;
 * the worker's numeric count cannot supply a wall or a hidden lower floor. */
static int cycle_upper_high_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,mirror,x,y;
    if(!cycle_observed_shop_scene(scene,row,-1)
        ||!cycle_structural_cell(row->left,448,&ax)
        ||!cycle_structural_cell(row->sy+48,207,&ay)||ay!=1)return 0;
    for(mirror=0;mirror<2;++mirror){
        int solid=mirror?ax+4:ax-2,gate=mirror?ax-2:ax+4,valid=1;
        int opening=tile(scene,gate,ay-4);
        for(y=ay-5;y<=ay+1;++y)valid&=tile(scene,solid,y)==NG2_TILE_GOLD;
        for(x=ax-2;x<=ax+4;++x)valid&=tile(scene,x,ay-5)==NG2_TILE_GOLD;
        if(valid&&tile(scene,gate,ay-3)==NG2_TILE_GOLD
            &&(opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR))return 1;
    }
    return 0;
}
/* Policy11 recomputes the observed fourteen-cell offset-entry boundary.
 * Numeric counts and the worker's one-face certificate cannot supply walls
 * or floor missing from this immutable source Scene. */
static int cycle_single_offer_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,mirror,x,y;
    if(!cycle_observed_shop_scene(scene,row,-1)
        ||!cycle_structural_cell(row->left,448,&ax)||!cycle_structural_cell(row->sy+48,207,&ay)
        ||ay-3 < -5||ay+3>4)return 0;
    for(mirror=0;mirror<2;++mirror){
        int wall=mirror?ax+4:ax-2,gate=mirror?ax-2:ax+4,valid=1;
        for(y=ay-3;y<=ay+3;++y)valid&=tile(scene,wall,y)==NG2_TILE_GOLD;
        for(x=ax-2;x<=ax+4;++x)valid&=tile(scene,x,ay+3)==NG2_TILE_GOLD;
        valid&=tile(scene,gate,ay+1)==NG2_TILE_GOLD;
        valid&=tile(scene,gate,ay+2)==NG2_TILE_FLOOR;
        if(valid)return 1;
    }
    return 0;
}
/* Policy17's lower entrance is proved again from the immutable Scene.
 * A numeric count or the missing second face cannot invent these floors. */
static int cycle_single_lower_entry_scene(const NG2Scene *scene,const NG2RingRow *row){
    int ax,ay,mirror,y,gate;
    if(!cycle_observed_shop_scene(scene,row,-1)||row->left<197||row->left>537
        ||row->sy<21||row->sy>224||!cycle_structural_cell(row->left,448,&ax)
        ||!cycle_structural_cell(row->sy+48,207,&ay)||ay-2 < -5||ay+3>4)return 0;
    for(mirror=0;mirror<2;++mirror){
        int wall=mirror?ax-2:ax+4,valid=1;
        for(y=ay-2;y<=ay+2;++y)valid&=tile(scene,wall,y)==NG2_TILE_GOLD;
        if(!valid)continue;
        for(gate=ax;gate<=ax+2;++gate)
            if(tile(scene,gate-1,ay+3)==NG2_TILE_GOLD&&tile(scene,gate+1,ay+3)==NG2_TILE_GOLD
                &&tile(scene,gate,ay+1)==NG2_TILE_FLOOR&&tile(scene,gate,ay+2)==NG2_TILE_FLOOR
                &&tile(scene,gate,ay+3)==NG2_TILE_FLOOR)return 1;
    }
    return 0;
}
/* Numeric face geometry is checked again at adoption, independently of the
 * Ring producer. Common top plus a centered full anchor explains a clipped
 * adjacent component without shifting the observed product/price row. */
static int cycle_observed_shop_faces(const NG2RingCoverage *w,const NG2RingRow *row){
    const int32_t *a=w->board_boxes[0],*b=w->board_boxes[1];
    int cy[2]={a[1]+a[3]/2,b[1]+b[3]/2},anchor;
    if(abs(cy[0]-row->sy)<=2&&abs(cy[1]-row->sy)<=2&&abs(cy[1]-cy[0])<=2)return 1;
    for(anchor=0;anchor<2;++anchor){
        const int32_t *full=w->board_boxes[anchor],*fragment=w->board_boxes[1-anchor];
        if(abs(cy[anchor]-row->sy)<=2&&fragment[1]==full[1]&&fragment[3]<full[3]
            &&abs(fragment[2]-full[2])<=2)return 1;
    }
    return 0;
}
/* A closed red container is a positive identity distinct from generic target
 * absence. The full binary domain remains mandatory after identity checking;
 * no Scene tile is copied or changed to grant lower-floor authority. */
static int cycle_strong_mask_coverage(double value,int ink){
    if(!isfinite(value)||value<0.0||value>1.0||ink<1||ink>1188)return 0;
    double count=round(value*ink);
    return count>=(95*ink)/100&&fabs(value-count/ink)<=1e-9;
}
static int cycle_closed_color_scores(const NG2RingSlot *slot){
    int gold,dark;
    switch(slot->ignored_container_id){case 9:gold=172;dark=548;break;
        case 10:gold=154;dark=484;break;case 11:gold=189;dark=505;break;default:return 0;}
    int strict=cycle_score(slot->ignored_icon_score,.94)&&cycle_score(slot->ignored_gold_iou,.94)
        &&cycle_score(slot->ignored_gold_coverage,.95)&&cycle_score(slot->ignored_dark_iou,.94)
        &&cycle_score(slot->ignored_dark_coverage,.95);
    int strong=cycle_score(slot->ignored_icon_score,.995)
        &&cycle_strong_mask_coverage(slot->ignored_gold_coverage,gold)
        &&cycle_strong_mask_coverage(slot->ignored_dark_coverage,dark);
    return (strict||strong)&&cycle_score(slot->ignored_gold_iou,0.0)&&cycle_score(slot->ignored_dark_iou,0.0)
        &&slot->ignored_gold_coverage<=1.0&&slot->ignored_dark_coverage<=1.0
        &&slot->ignored_gold_iou<=1.0&&slot->ignored_dark_iou<=1.0
        &&slot->ignored_gold_iou<=slot->ignored_gold_coverage+1e-9
        &&slot->ignored_dark_iou<=slot->ignored_dark_coverage+1e-9
        &&slot->ignored_gold_iou+1e-9>=slot->ignored_gold_coverage*gold/1188.0
        &&slot->ignored_dark_iou+1e-9>=slot->ignored_dark_coverage*dark/1188.0;
}
static int cycle_red_closed_cell(const NG2RingSlot *slot,int cx,int sy,int index,const int32_t strip[4],unsigned version){
    const int32_t *pose=slot->ignored_icon_box;NG2RingSlot generic;
    int old=slot->ignored_container_id==11&&cycle_score(slot->ignored_icon_score,.94)
        &&cycle_score(slot->ignored_gold_iou,.94)&&cycle_score(slot->ignored_gold_coverage,.95)
        &&cycle_score(slot->ignored_dark_iou,.94)&&cycle_score(slot->ignored_dark_coverage,.95);
    if(slot->kind!=2||slot->outcome!=NG2_RING_IGNORED_CONTAINER
        ||slot->non_target_id||slot->non_target_conflict
        ||!((version==1&&old)||(version==2&&cycle_closed_color_scores(slot)))
        ||!cycle_box(strip)||!cycle_box(pose)||pose[2]!=36||pose[3]!=33||!cycle_contains(strip,pose)
        ||pose[0]<cx-26||pose[0]>cx-10||pose[1]<sy+24||pose[1]>sy+57)return 0;
    generic=*slot;generic.kind=NG2_RING_GENERIC_NON_TARGET;generic.outcome=NG2_RING_NON_TARGET;
    generic.ignored_container_id=0;generic.ignored_icon_score=generic.ignored_gold_iou=generic.ignored_gold_coverage=0.0;
    generic.ignored_dark_iou=generic.ignored_dark_coverage=0.0;
    memset(generic.ignored_icon_box,0,sizeof(generic.ignored_icon_box));
    return cycle_binary_cell(&generic,cx,sy,index,strip);
}
static int cycle_structural_witness(const NG2Controller *p,const NG2RingResult *result){
    const NG2RingCoverage *w=&result->certificate;const NG2RingRow *row;int i,j,gold=0,side=w->policy_version==4,lower=w->policy_version==5,closed=w->policy_version==6,single=w->policy_version==7,bottom=w->policy_version==8,red=w->policy_version==10,lower_entry=w->policy_version==17,upper_high=w->policy_version==18,oneface=w->policy_version==11||lower_entry||upper_high,upper=w->policy_version==15,observed=w->policy_version==9||red||oneface,red_slot=-1,v2=w->layout_version==2,v3=w->layout_version==3,object=red||v2,face_count=0,lower_price=-1;
    if(p->cycle.partial||p->cycle.candidate_latched||!p->cycle.full_seen
        ||result->status!=NG2_RING_OK||result->outcome!=NG2_RING_NEGATIVE
        ||result->coverage!=NG2_RING_COVERAGE_COMPLETE||result->row_count<1||result->row_count>4
        ||result->selected_row<0||result->selected_row>=result->row_count||result->selected_partial!=-1
        ||result->partial_safe_no_positive||result->partial_count!=2
        ||(w->layout_version!=1&&!v2&&!v3)||((upper||lower_entry||upper_high)&&w->layout_version!=1)||(v3&&!single)||(w->policy_version!=3&&!side&&!lower&&!closed&&!single&&!bottom&&!observed&&!upper)||w->board_mode!=w->policy_version||w->failure_flags||w->accepted_rows!=1
        ||w->row_index!=result->selected_row||w->observed_items!=3||w->observed_prices!=3
        ||w->non_target_items!=(object?2:3)||w->ignored_containers!=(object?1:0)
        ||w->unmatched_items<0||w->unmatched_items>(180*67)/24||w->unmatched_prices||w->unmatched_boards
        ||w->scene_state!=NG2_FLOOR||w->scene_goods!=NG2_GOODS_VISIBLE
        ||(!single&&(!cycle_zero_box(w->merchant_box)||w->merchant_score!=0.0||w->merchant_coverage!=0.0)))return 0;
    row=&result->rows[result->selected_row];
    if(row->left<54||row->left>770||row->sy<0||row->sy>325
        ||row->left!=w->row[0]||row->sy!=w->row[1]
        ||!cycle_box(w->strip_box)||w->strip_box[0]!=row->left-54||w->strip_box[1]!=row->sy+24
        ||w->strip_box[2]!=180||w->strip_box[3]!=67
        ||((observed||v3)&&(w->strip_box[0]<143||w->strip_box[0]+w->strip_box[2]>663
            ||w->strip_box[1]<45||w->strip_box[1]+w->strip_box[3]>315)))return 0;
    if(v3){
        int top=414,bottom_price=0;
        if(!cycle_observed_shop_scene(&p->cycle_anchor,row,-1))return 0;
        for(i=0;i<3;++i){
            const int32_t *price=w->price_boxes[i];
            if(!cycle_box(price)||price[3]<7||price[3]>9)return 0;
            if(price[1]>=row->sy+82){
                if(lower_price>=0)return 0;
                lower_price=i;
            }else{
                if(price[1]<top)top=price[1];
                if(price[1]+price[3]>bottom_price)bottom_price=price[1]+price[3];
            }
        }
        if(lower_price<0||bottom_price-top>9
            ||w->price_boxes[lower_price][1]+w->price_boxes[lower_price][3]<=bottom_price)return 0;
    }
    if(object){
        for(j=0;j<result->row_count;++j)for(i=0;i<3;++i)if(result->rows[j].slots[i].ignored_container_id){
            if(j!=result->selected_row||red_slot>=0
                ||!cycle_red_closed_cell(&row->slots[i],row->left+36*i,row->sy,i,w->strip_box,w->layout_version))return 0;
            red_slot=i;
        }
        for(i=0;i<result->partial_count;++i)if(result->partial[i].ignored_container_id)return 0;
        if(red_slot<0)return 0;
    }
    if(!(upper_high?cycle_upper_high_scene(&p->cycle_anchor,row):lower_entry?cycle_single_lower_entry_scene(&p->cycle_anchor,row):upper?cycle_upper_side_scene(&p->cycle_anchor,row):oneface?cycle_single_offer_scene(&p->cycle_anchor,row):observed?cycle_observed_shop_scene(&p->cycle_anchor,row,red?red_slot:-1):bottom?cycle_bottom_shop_scene(&p->cycle_anchor,row):single?cycle_single_sign_scene(&p->cycle_anchor,row):side?cycle_side_shop_scene(&p->cycle_anchor,row):lower?cycle_lower_shop_scene(&p->cycle_anchor,row):closed?cycle_closed_shop_scene(&p->cycle_anchor,row):cycle_structural_scene(&p->cycle_anchor,row))
        ||(single&&!cycle_single_sign_merchant(w,row)))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)gold+=p->cycle_anchor.tiles[i]==NG2_TILE_GOLD;
    if(gold<(lower_entry?7:(upper||oneface)?14:observed?1:bottom?10:(side||single)?7:12)||w->actual_gold_cells!=gold)return 0;
    for(i=0;i<2;++i){
        const NG2RingEndcap *end=&w->endcaps[i];const int32_t *board=w->board_boxes[i];
        int32_t roi[4]={row->left+72*i-18,row->sy-20,36,40};
        int absent=(single&&i==1)||(oneface&&!w->board_counts[i]);
        if(!cycle_zero_box(w->sign_boxes[i])||w->sign_iou[i]!=0.0||w->sign_coverage[i]!=0.0
            ||(!absent&&(!cycle_box(roi)||!cycle_box(board)||!cycle_contains(roi,board)
            ||board[2]<18||board[2]>36||board[3]<16||board[3]>40
            ||w->board_counts[i]<150||w->board_counts[i]>board[2]*board[3]
            ||(oneface&&board[3]!=29)
            ||abs(board[0]+board[2]/2-row->left-72*i)>2||((oneface||(!closed&&!observed&&!upper))&&abs(board[1]+board[3]/2-row->sy)>2)))
            ||(absent&&(!cycle_zero_box(board)||w->board_counts[i]))
            ||w->board_exterior_count[i]
            ||!cycle_box(end->box)||end->box[0]!=row->left+(i?96:-48)||end->box[1]!=row->sy+36
            ||end->box[2]!=25||end->box[3]!=25||end->count!=625
            ||end->black_count<0||end->black_count>62||end->bright_count<0||end->bright_count>=24
            ||end->price_ink_count<0||end->price_ink_count>=18
            ||end->floor_full!=1||end->floor_upper!=1||end->floor_lower!=1||!cycle_endcap_floor(end))return 0;
        for(j=0;j<4;++j)if(w->board_edge_counts[i][j]||w->board_corner_counts[i][j])return 0;
        face_count+=!absent;
    }
    if(oneface&&face_count!=1)return 0;
    if(!single&&!oneface&&(abs((w->board_boxes[1][0]+w->board_boxes[1][2]/2)
        -(w->board_boxes[0][0]+w->board_boxes[0][2]/2)-72)>2
        ||(!closed&&!observed&&!upper&&abs((w->board_boxes[1][1]+w->board_boxes[1][3]/2)
        -(w->board_boxes[0][1]+w->board_boxes[0][3]/2))>2)))return 0;
    if(closed&&!cycle_closed_shop_faces(w,row))return 0;
    if((observed||upper)&&!oneface&&!cycle_observed_shop_faces(w,row))return 0;
    for(i=0;i<result->row_count;++i)for(j=0;j<3;++j)
        if(!cycle_binary_no_positive(&result->rows[i].slots[j]))return 0;
    for(i=0;i<result->partial_count;++i)if(!cycle_binary_no_positive(&result->partial[i]))return 0;
    for(i=0;i<3;++i){
        const NG2RingSlot *slot=&row->slots[i];const int32_t *price=w->price_boxes[i];
        if(!(i==red_slot?cycle_red_closed_cell(slot,row->left+36*i,row->sy,i,w->strip_box,w->layout_version):cycle_binary_cell(slot,row->left+36*i,row->sy,i,w->strip_box))
            ||memcmp(w->item_boxes[i],slot->non_target_icon_box,sizeof(w->item_boxes[i]))
            ||!cycle_zero_box(w->name_boxes[i])||!cycle_box(price)
            ||price[0]<slot->cx-11||price[0]+price[2]>slot->cx+12
            ||price[1]<row->sy+69||price[1]+price[3]>row->sy+((v2&&i==red_slot)||(v3&&i==lower_price)?91:89)
            ||(v2&&(price[3]>9||(i==red_slot&&price[1]<slot->ignored_icon_box[1]+33))))return 0;
        for(j=0;j<i;++j)if(!memcmp(price,w->price_boxes[j],sizeof(w->price_boxes[i])))return 0;
    }
    if(side||single||v2){
        int top=414,bottom=0;
        for(i=0;i<3;++i){
            if((v2&&i==red_slot)||(v3&&i==lower_price))continue;
            if(w->price_boxes[i][1]<top)top=w->price_boxes[i][1];
            if(w->price_boxes[i][1]+w->price_boxes[i][3]>bottom)bottom=w->price_boxes[i][1]+w->price_boxes[i][3];
        }
        if(bottom-top>9)return 0;
    }
    return cycle_binary_cell(&result->partial[0],row->left-36,row->sy,0,w->strip_box)
        &&cycle_binary_cell(&result->partial[1],row->left+108,row->sy,0,w->strip_box);
}
static int cycle_negative_witness(const NG2Controller *p,const NG2RingResult *result){
    const NG2RingCoverage *w=&result->certificate;const NG2RingRow *row;int i,j,gold=0,named=0,ignored=0;
    if(w->policy_version==3||w->policy_version==4||w->policy_version==5||w->policy_version==6||w->policy_version==7||w->policy_version==8||w->policy_version==9||w->policy_version==10||w->policy_version==11||w->policy_version==15||w->policy_version==17||w->policy_version==18)return cycle_structural_witness(p,result);
    if(p->cycle.partial||p->cycle.candidate_latched||!p->cycle.full_seen
        ||result->coverage!=NG2_RING_COVERAGE_COMPLETE||result->row_count<1||result->row_count>4
        ||result->selected_row<0||result->selected_row>=result->row_count||result->selected_partial!=-1
        ||result->partial_safe_no_positive||result->partial_count<0||result->partial_count>12
        ||w->layout_version!=1||(w->policy_version!=1&&w->policy_version!=2)||w->failure_flags||w->accepted_rows!=1
        ||w->row_index!=result->selected_row||w->observed_items!=3||w->observed_prices!=3
        ||(w->board_mode!=1&&w->board_mode!=2)
        ||w->unmatched_items||w->unmatched_prices||w->unmatched_boards
        ||w->scene_state!=NG2_FLOOR||w->scene_goods!=NG2_GOODS_VISIBLE
        ||p->cycle_anchor.state!=NG2_FLOOR||p->cycle_anchor.goods!=NG2_GOODS_VISIBLE)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)gold+=p->cycle_anchor.tiles[i]==NG2_TILE_GOLD;
    if(gold<1||w->actual_gold_cells!=gold||!cycle_box(w->strip_box)||!cycle_box(w->merchant_box)
        ||!cycle_score(w->merchant_score,.94)||!cycle_score(w->merchant_coverage,.95))return 0;
    if(!((cycle_score(w->sign_iou[0],.94)&&cycle_score(w->sign_coverage[0],.95))
        ||(cycle_score(w->sign_iou[1],.94)&&cycle_score(w->sign_coverage[1],.95))))return 0;
    row=&result->rows[result->selected_row];
    if(row->left<54||row->left>770||row->sy<0||row->sy>325
        ||row->left!=w->row[0]||row->sy!=w->row[1]||w->strip_box[0]!=row->left-54
        ||w->strip_box[1]!=row->sy+24||w->strip_box[2]!=180
        ||w->strip_box[3]!=((w->policy_version==2||w->ignored_containers>0)?67:65))return 0;
    for(i=0;i<2;++i){
        const NG2RingEndcap *end=&w->endcaps[i];const int32_t *board=w->board_boxes[i];
        int width=board[2],height=board[3];
        if(!cycle_box(w->board_boxes[i])||w->board_counts[i]<150
            ||w->board_boxes[i][2]<18||w->board_boxes[i][2]>48
            ||w->board_boxes[i][3]<16||w->board_boxes[i][3]>40
            ||!cycle_box(end->box)||end->box[0]!=row->left+(i?96:-48)
            ||end->box[1]!=row->sy+36||end->box[2]!=25||end->box[3]!=25||end->count!=625
            ||end->black_count<0||end->black_count>62||end->bright_count<0||end->bright_count>=24
            ||end->price_ink_count<0||end->price_ink_count>=18
            ||end->floor_full!=1||end->floor_upper!=1||end->floor_lower!=1||!cycle_endcap_floor(end))return 0;
        if(w->board_counts[i]>width*height||abs(board[0]+width/2-row->left-72*i)>2
            ||abs(board[1]+height/2-row->sy)>2||w->board_exterior_count[i])return 0;
        for(j=0;j<4;++j){
            int edge=w->board_edge_counts[i][j],corner=w->board_corner_counts[i][j];
            if(w->board_mode==1){if(edge||corner)return 0;}
            else{
                int length=j<2?width:height;
                if(edge<0||edge>length||4*edge<3*length||corner<1||corner>4)return 0;
            }
        }
    }
    if(abs((w->board_boxes[1][0]+w->board_boxes[1][2]/2)
        -(w->board_boxes[0][0]+w->board_boxes[0][2]/2)-72)>2
        ||abs((w->board_boxes[1][1]+w->board_boxes[1][3]/2)
        -(w->board_boxes[0][1]+w->board_boxes[0][3]/2))>2)return 0;
    for(i=0;i<result->row_count;++i)for(j=0;j<3;++j)
        if(!cycle_no_candidate(&result->rows[i].slots[j]))return 0;
    for(i=0;i<result->partial_count;++i)if(!cycle_no_candidate(&result->partial[i]))return 0;
    if(w->policy_version==2)return cycle_binary_witness(result,row);
    for(i=0;i<3;++i){
        const NG2RingSlot *slot=&row->slots[i];const int32_t *icon;int price_bottom=row->sy+89;
        if(slot->slot!=i||slot->cx!=row->left+36*i||slot->sy!=row->sy||slot->non_target_conflict
            ||!cycle_box(w->item_boxes[i])||!cycle_box(w->price_boxes[i]))return 0;
        if(slot->kind==1&&slot->outcome==NG2_RING_NON_TARGET&&slot->non_target_id>0&&slot->non_target_id<=8
            &&!slot->ignored_container_id&&cycle_score(slot->non_target_icon_score,.94)
            &&cycle_score(slot->non_target_name_iou,.94)&&cycle_score(slot->non_target_name_coverage,.95)
            &&cycle_box(slot->non_target_name_box)&&cycle_box(slot->non_target_icon_box)
            &&!memcmp(w->name_boxes[i],slot->non_target_name_box,sizeof(w->name_boxes[i]))){
            ++named;icon=slot->non_target_icon_box;
            for(j=0;j<i;++j)if(result->rows[result->selected_row].slots[j].kind==1
                &&!memcmp(w->name_boxes[i],w->name_boxes[j],sizeof(w->name_boxes[i])))return 0;
        }else if(slot->kind==2&&slot->outcome==NG2_RING_IGNORED_CONTAINER&&!slot->non_target_id
            &&(slot->ignored_container_id==9||slot->ignored_container_id==10)&&cycle_box(slot->ignored_icon_box)
            &&cycle_score(slot->ignored_icon_score,.94)&&cycle_score(slot->ignored_gold_iou,.94)
            &&cycle_score(slot->ignored_gold_coverage,.95)&&cycle_score(slot->ignored_dark_iou,.94)
            &&cycle_score(slot->ignored_dark_coverage,.95)){
            ++ignored;icon=slot->ignored_icon_box;price_bottom=row->sy+90;
        }else return 0;
        if(memcmp(w->item_boxes[i],icon,sizeof(w->item_boxes[i])))return 0;
        /* The 35x42 presence window is not a full-template bound: the
         * independently matched bank sprite includes its dark padding. */
        if(icon[2]>36||icon[3]>36||icon[0]<slot->cx-icon[2]/2-8||icon[0]>slot->cx-icon[2]/2+8
            ||icon[1]<slot->sy+24||icon[1]>slot->sy+57||!cycle_contains(w->strip_box,icon)
            ||w->price_boxes[i][0]<slot->cx-11
            ||w->price_boxes[i][0]+w->price_boxes[i][2]>slot->cx+12
            ||w->price_boxes[i][1]<slot->sy+69||w->price_boxes[i][1]+w->price_boxes[i][3]>price_bottom)return 0;
        for(j=0;j<i;++j)if(cycle_overlap(w->item_boxes[i],w->item_boxes[j])
            ||!memcmp(w->price_boxes[i],w->price_boxes[j],sizeof(w->price_boxes[i])))return 0;
    }
    return w->non_target_items==named&&w->ignored_containers==ignored&&named+ignored==3;
}
static void cycle_scene(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix){
    p->scene=*scene;p->have_scene=1;p->need_fresh_cleanup=0;p->last_observed_prefix=prefix;
    p->s.paused=scene->state==NG2_PAUSE;p->s.last_capture_id=id;
    p->s.last_capture_start_ns=start;p->s.last_capture_end_ns=end;++p->s.accepted_frames;
}
static int cycle_exact_item_protection(const NG2Scene *scene);
static int upper_side_variant(const NG2Scene *scene,int direction);
static int cycle_partial_choice(const NG2Controller *p,const NG2Scene *scene,NG2Decision *out){
    int i,d,clear=1;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_PARTIAL||!actual_gold(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||!choose_step(p,scene,out))return 0;
    d=out->direction;
    if(d<1||d>4||out->obstacle!=NG2_TILE_FLOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR)return 0;
    for(i=0;i<5;++i)
        if(protected_route_cell(scene,scene,dx[i],dy[i])
            ||protected_route_cell(scene,scene,dx[d]+dx[i],dy[d]+dy[i]))clear=0;
    if(clear)return 1;
    /* The canonical protection already includes the ITEM's cardinal halo.
     * After this same gate's actual opening, actual origin/destination
     * FLOORs need no second dilation. All other route guards stay intact. */
    return last_ack_opened_gate(p,d)&&out->reason==5
        &&out->target_x==dx[d]&&out->target_y==dy[d]&&cycle_exact_item_protection(scene)
        &&!protected_at(scene,0,0)&&!protected_at(scene,dx[d],dy[d]);
}
/* Bounding extrema of the existing icon/price/partial-name search union,
 * including +/-18px ITEM quantization. No slot anchor or absence is inferred. */
static void cycle_framing_bounds(int x,int y,int *left,int *right,int *bottom){
    int cx=448+36*x,cy=207+36*y;
    if(cx-78<*left)*left=cx-78;
    if(cx+78>*right)*right=cx+78;
    if(cy+59>*bottom)*bottom=cy+59;
}
static int cycle_framing_scene(const NG2Scene *scene){
    int i,d,top=0,left=896,right=0,bottom=0;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_PARTIAL
        ||scene->gold_state!=NG2_GOLD_CANDIDATE||!actual_gold(scene))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5;
        if(scene->tiles[i]==NG2_TILE_ITEM){
            if(!scene->protected_cells[i]||y> -4)return 0;
            if(y== -5)top=1;
            cycle_framing_bounds(x,y,&left,&right,&bottom);
        }
        if(scene->protected_cells[i]){
            if(y> -3)return 0;
            /* A protected edge cell may originate from an ITEM outside the
             * finite array. Include self and all four possible origins,
             * without adding any hypothetical ITEM to the observed Scene.
             * The self bound also contains the protected36x36 rectangle. */
            for(d=0;d<5;++d)cycle_framing_bounds(x+dx[d],y+dy[d],&left,&right,&bottom);
        }
    }
    /* Only old observable pixels are preserved. In this central/top domain,
     * the sole possible destination HUD is pause[429,0,465,45); its UP
     * preimage inside the old viewport was already in that same old HUD.
     * Offscreen/old-HUD potential pixels remain unknown, never complete. */
    return top&&left>=143&&right<=663&&bottom>0&&bottom+36<=315;
}
static int cycle_exact_item_protection(const NG2Scene *scene);
/* A separately observed entry corridor can expose a row-4-only projection.
 * Every rail cell and both steps are positive evidence. Old visible pixels
 * are preserved under UP; offscreen and old pause-HUD pixels stay unknown. */
static int cycle_corridor_scene(const NG2Scene *scene){
    int i,side,rail=0,left=896,right=0,bottom=0;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_PARTIAL
        ||scene->gold_state!=NG2_GOLD_CANDIDATE||!actual_gold(scene)
        ||!cycle_exact_item_protection(scene))return 0;
    for(i=0;i<3;++i)if(tile(scene,0,-i)!=NG2_TILE_FLOOR||protected_at(scene,0,-i))return 0;
    for(side=-1;side<=1;side+=2)
        if(tile(scene,side,-3)==NG2_TILE_GOLD&&tile(scene,side,-2)==NG2_TILE_GOLD
            &&tile(scene,side,-1)==NG2_TILE_GOLD&&tile(scene,-side,-1)==NG2_TILE_GOLD)rail=1;
    if(!rail)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM){
        int x=i%23-11,y=i/23-5;
        if(y> -4)return 0;
        cycle_framing_bounds(x,y,&left,&right,&bottom);
    }
    return left>=143&&right<=663&&bottom>0&&bottom+36<=315;
}
static int cycle_framing_scene_proof(const NG2Scene *scene){
    return cycle_framing_scene(scene)||cycle_corridor_scene(scene);
}
static int cycle_framing_admit(const NG2Controller *p,const NG2RingResult *result){
    const NG2Decision *choice=&p->cycle_choice;
    return p->cycle.partial&&!p->cycle.full_seen&&!p->cycle.candidate_latched
        &&!p->cycle_restart_unproved&&!p->cycle_pause_attempted&&!p->cycle_storage_error
        &&!p->s.input_state&&p->s.lead_confirmed&&level_moves(p)>0
        &&p->s.last_completed_id==p->cycle.prefix&&p->last_observed_prefix==p->cycle.prefix
        &&p->cycle_choice_valid&&choice->direction==NG2_UP&&choice->reason==5
        &&!choice->target_x&&choice->target_y== -1&&choice->obstacle==NG2_TILE_FLOOR
        &&last_ack_opened_gate(p,NG2_UP)&&cycle_framing_scene_proof(&p->cycle_anchor)
        &&result->outcome==NG2_RING_UNKNOWN&&result->coverage==NG2_RING_COVERAGE_INCOMPLETE
        &&!result->row_count&&!result->partial_count&&!result->partial_safe_no_positive
        &&result->selected_row== -1&&result->selected_partial== -1;
}
/* A current PARTIAL source owns only the old unused one-view allowance.
 * Its normal Scene is never enlarged with the old potential projection. */
static int cycle_current_partial_local(const NG2Controller *p,const NG2Scene *scene){
    int i,k;
    if(!p->cycle_current_partial||!cycle_corridor_scene(scene)
        ||!cycle_exact_item_protection(scene))return 0;
    for(i=0;i<5;++i)for(k=0;k<2;++k){
        int x=dx[i],y=dy[i]-k,index=tile_index(x,y);
        if(index<0||((scene->protected_cells[index]||p->cycle_current_potential[index])
            &&tile(scene,x,y)!=NG2_TILE_GOLD))return 0;
    }
    return 1;
}
static int cycle_current_partial_top_relation(const NG2Controller *p,const NG2Scene *scene);
/* This history deliberately distinguishes a prior actual opening from
 * the following ACK whose FULL view closed without displacement proof. */
static int cycle_full_history(const NG2Controller *p,int *direction){
    const NG2ControllerEvent *latest,*opened;
    if(p->event_count<2||!p->s.door_changes||!p->s.lead_confirmed||level_moves(p)<=0)return 0;
    latest=&p->events[p->event_count-1];opened=&p->events[p->event_count-2];
    if(latest->command.id!=p->s.last_completed_id||latest->outcome!=2||!latest->begin_ns||!latest->end_ns
        ||latest->motion!=NG2_MOTION_UNKNOWN||latest->dx||latest->dy||!latest->observed_capture_id
        ||latest->command.kind!=NG2_ACTION_MOVE
        ||(latest->command.direction!=NG2_LEFT&&latest->command.direction!=NG2_RIGHT)
        ||opened->command.id>=latest->command.id||opened->outcome!=2||!opened->begin_ns||!opened->end_ns
        ||opened->command.kind!=NG2_ACTION_MOVE||opened->command.direction!=latest->command.direction
        ||opened->motion!=NG2_DOOR_OPENED||opened->dx||opened->dy||!opened->observed_capture_id
        ||opened->end_ns>latest->begin_ns||opened->observed_capture_id>latest->command.source_capture_id
        ||latest->end_ns>p->cycle.capture_start_ns||latest->observed_capture_id!=p->cycle.capture_id)return 0;
    *direction=latest->command.direction;return 1;
}
/* A complete-looking offer row can already appear in the opening response.
 * That response is positive opening evidence, not an ACK of an unobserved
 * entry step. It admits the same one-use observation only from its own
 * current prefix/source; the later independent zero still owns the ticket. */
static int cycle_full_opening_history(const NG2Controller *p,int *direction){
    const NG2ControllerEvent *opened;
    if(!p->event_count||!p->s.door_changes||!p->s.lead_confirmed||level_moves(p)<=0)return 0;
    opened=&p->events[p->event_count-1];
    if(opened->command.id!=p->s.last_completed_id||opened->outcome!=2
        ||!opened->begin_ns||!opened->end_ns||opened->motion!=NG2_DOOR_OPENED
        ||opened->dx||opened->dy||opened->command.kind!=NG2_ACTION_MOVE
        ||(opened->command.direction!=NG2_LEFT&&opened->command.direction!=NG2_RIGHT)
        ||opened->end_ns>p->cycle.capture_start_ns
        ||!opened->observed_capture_id||opened->observed_capture_id!=p->cycle.capture_id)return 0;
    *direction=opened->command.direction;return 1;
}
/* Perception's ITEM projection is self plus the four cardinal cells. Full
 * observational movement requires the exact mask, including cells that do
 * not intersect the movement footprint. Missing masks cannot bypass the
 * older buffer proof by making its neighborhood appear empty. */
static int cycle_exact_item_protection(const NG2Scene *scene){
    int i,k,items=0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5,expected=0;
        items+=scene->tiles[i]==NG2_TILE_ITEM;
        for(k=0;k<5;++k)expected|=tile(scene,x+dx[k],y+dy[k])==NG2_TILE_ITEM;
        if(scene->protected_cells[i]!=expected)return 0;
    }
    return items>0;
}
static int cycle_full_up_local(const NG2Scene *scene){
    int i,n=0,left=12,right=-12,row=0;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE||!actual_gold(scene)
        ||!cycle_exact_item_protection(scene)||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(scene,0,-1)!=NG2_TILE_FLOOR||protected_at(scene,0,0)||protected_at(scene,0,-1)
        ||tile(scene,-1,0)!=NG2_TILE_GOLD||tile(scene,1,0)!=NG2_TILE_GOLD)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM){
        int x=i%23-11,y=i/23-5;
        if(n&&row!=y)return 0;
        row=y;++n;if(x<left)left=x;if(x>right)right=x;
    }
    return n==3&&right-left==2&&row== -3
        &&tile(scene,left-1,row)==NG2_TILE_FLOOR&&tile(scene,right+1,row)==NG2_TILE_FLOOR;
}
/* Called from the initial FULL bind while command/before still belong to the
 * old MOVE. PAUSE reservation later overwrites both, so admission never reads
 * that replacement as old movement identity. */
static void cycle_cache_up_history(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                                   uint64_t start,uint64_t prefix){
    const NG2ControllerEvent *latest=event(p),*opened;NG2Motion proof={0};int kind=0;
    p->cycle_up_history=0;
    if(!latest||!cycle_full_up_local(scene)||p->cycle_retry_only||p->cycle_full_spent
        ||p->entry.active||p->lower.active||p->upper.active||p->s.input_state
        ||!p->s.door_changes||!p->s.lead_confirmed||level_moves(p)<=0
        ||p->s.last_completed_id!=prefix||p->last_observed_prefix!=prefix
        ||p->command.id!=prefix||p->command.kind!=NG2_ACTION_MOVE||p->command.direction!=NG2_UP
        ||latest->command.id!=prefix||latest->outcome!=2||!latest->begin_ns||!latest->end_ns
        ||latest->end_ns>start||!latest->observed_capture_id||latest->observed_capture_id>id
        ||p->motion_wait.command_id!=prefix
        ||p->motion_wait.source_capture_id!=latest->command.source_capture_id)return;
    if(!ng2_motion(&p->before,scene,NG2_UP,&proof))return;
    if(latest->motion==NG2_MOVED&&!latest->dx&&latest->dy== -1
        &&proof.kind==NG2_MOVED&&!proof.dx&&proof.dy== -1)kind=2;
    if(latest->motion==NG2_MOTION_UNKNOWN&&!latest->dx&&!latest->dy
        &&latest->observed_capture_id==id&&proof.kind==NG2_MOTION_UNKNOWN&&!proof.dx&&!proof.dy
        &&p->event_count>=2){
        opened=&p->events[p->event_count-2];
        if(opened->command.id<latest->command.id&&opened->command.kind==NG2_ACTION_MOVE
            &&opened->command.direction==NG2_UP&&opened->outcome==2&&opened->begin_ns&&opened->end_ns
            &&opened->motion==NG2_DOOR_OPENED&&!opened->dx&&!opened->dy&&opened->observed_capture_id
            &&opened->end_ns<=latest->begin_ns&&opened->observed_capture_id<=latest->command.source_capture_id)kind=1;
    }
    if(!kind)return;
    p->cycle_up_history=kind;p->cycle_up_capture=id;p->cycle_up_job=p->cycle.job_id;
    p->cycle_up_level=p->cycle.level_id;p->cycle_up_command=latest->command;p->cycle_up_before=p->before;
    p->cycle_up_period=p->command_period;
}
static int cycle_full_local(const NG2Scene *scene,int d){
    int i,k,items=0;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE||!actual_gold(scene)
        ||(d!=NG2_LEFT&&d!=NG2_RIGHT)||tile(scene,0,-1)!=NG2_TILE_GOLD
        ||tile(scene,0,1)!=NG2_TILE_GOLD||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(scene,dx[d],0)!=NG2_TILE_FLOOR)return 0;
    for(k=0;k<5;++k)
        if(protected_at(scene,dx[k],dy[k])||protected_at(scene,dx[d]+dx[k],dy[k]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5,explained=0;
        if(scene->tiles[i]==NG2_TILE_ITEM){
            ++items;if(!scene->protected_cells[i])return 0;
        }
        if(scene->protected_cells[i]){
            for(k=0;k<5;++k)explained|=tile(scene,x+dx[k],y+dy[k])==NG2_TILE_ITEM;
            if(!explained)return 0;
        }
    }
    return items>0;
}
/* Separate local observation proof: the actual origin/destination are both
 * observed unprotected FLOOR. An extra dilation of the already exact goods
 * projection is not a collision footprint. General route guards are intact. */
static int cycle_full_footprint(const NG2Scene *scene,int d){
    return scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE&&actual_gold(scene)
        &&(d==NG2_LEFT||d==NG2_RIGHT)&&tile(scene,0,-1)==NG2_TILE_GOLD
        &&tile(scene,0,1)==NG2_TILE_GOLD&&tile(scene,0,0)==NG2_TILE_FLOOR
        &&tile(scene,dx[d],0)==NG2_TILE_FLOOR&&!protected_at(scene,0,0)
        &&!protected_at(scene,dx[d],0);
}
/* Before entering, the known GOLD bracket surrounds the next FLOOR rather
 * than the player's origin. Neither unknown floor nor merchandise protection
 * is replaced by this geometry witness. */
static int cycle_full_opening_footprint(const NG2Scene *scene,int d){
    return scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE&&actual_gold(scene)
        &&(d==NG2_LEFT||d==NG2_RIGHT)&&tile(scene,dx[d],-1)==NG2_TILE_GOLD
        &&tile(scene,dx[d],1)==NG2_TILE_GOLD&&tile(scene,0,0)==NG2_TILE_FLOOR
        &&tile(scene,dx[d],0)==NG2_TILE_FLOOR&&!protected_at(scene,0,0)
        &&!protected_at(scene,dx[d],0);
}
static int cycle_full_local_proof(const NG2Scene *scene,int d){
    int old=cycle_full_local(scene,d);
    if(d==NG2_UP)return cycle_full_up_local(scene);
    return cycle_exact_item_protection(scene)
        &&(old||cycle_full_footprint(scene,d)||cycle_full_opening_footprint(scene,d));
}
static int cycle_full_roi(int left,int top,int right,int bottom,int d){
    int shift=-36*dx[d];
    /* Central viewport contains no HUD below y45. Preserve every potential
     * old pixel; this bound never turns an unseen cap into observed floor. */
    return left>=143&&right<=663&&top>=45&&bottom<=315&&left<right&&top<bottom
        &&left+shift>=143&&right+shift<=663;
}
static int cycle_full_slot(const NG2RingSlot *slot,int d){
    return cycle_binary_no_positive(slot)&&slot->cx>=0&&slot->cx<896&&slot->sy>=0&&slot->sy<414
        &&cycle_full_roi(slot->cx-60,slot->sy-32,slot->cx+60,slot->sy+115,d);
}
/* Only a direct opening may retain an already clipped outer name margin.
 * The full observed icon core must be central, and every currently visible
 * potential pixel must remain there after the horizontal observation step.
 * The clipped margin remains UNKNOWN; this grants no negative certificate. */
static int cycle_full_opening_edge_slot(const NG2RingSlot *slot,int d){
    int left,right,visible_left,visible_right,shift;
    if(!cycle_binary_no_positive(slot)||slot->cx<0||slot->cx>=896||slot->sy<0||slot->sy>=414
        ||slot->sy-32<45||slot->sy+115>315||slot->cx-18<143||slot->cx+18>663
        ||slot->sy+24<45||slot->sy+66>315)return 0;
    left=slot->cx-60;right=slot->cx+60;
    if(d==NG2_LEFT){
        if(left>=143||right>663)return 0;
        visible_left=143;visible_right=right;shift=36;
    }else if(d==NG2_RIGHT){
        if(right<=663||left<143)return 0;
        visible_left=left;visible_right=663;shift=-36;
    }else return 0;
    return visible_left<visible_right&&visible_left+shift>=143&&visible_right+shift<=663;
}
static int cycle_full_up_roi(int left,int top,int right,int bottom){
    return left>=143&&right<=663&&top>=9&&bottom+36<=315&&left<right&&top<bottom;
}
static int cycle_full_up_slot(const NG2RingSlot *slot){
    return cycle_binary_no_positive(slot)&&slot->icon_upper_bound<.80
        &&cycle_full_up_roi(slot->cx-60,slot->sy-32,slot->cx+60,slot->sy+115);
}
static int cycle_full_up_admit(const NG2Controller *p,const NG2RingResult *result,NG2Decision *choice){
    const NG2RingRow *row;NG2Motion owned={0};int x,y,i,k,hud=0;
    if(!p->cycle_up_history||p->cycle_up_capture!=p->cycle.capture_id
        ||p->cycle_up_job!=p->cycle.job_id||p->cycle_up_level!=p->cycle.level_id
        ||p->cycle_up_command.id!=p->cycle.prefix||p->cycle_retry_only
        ||(p->cycle_retry_blocked&1)
        ||p->cycle_full_spent||p->cycle_full_framing||p->cycle.partial||!p->cycle.full_seen
        ||p->entry.active||p->lower.active||p->upper.active||p->cycle.candidate_latched
        ||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->s.input_state||p->finish_requested||p->s.terminal
        ||p->cycle.prefix!=p->s.last_completed_id||p->last_observed_prefix!=p->cycle.prefix
        ||!cycle_full_up_local(&p->cycle_anchor)||result->outcome!=NG2_RING_UNKNOWN
        ||result->coverage!=NG2_RING_COVERAGE_INCOMPLETE||result->row_count!=1
        ||result->partial_safe_no_positive)return 0;
    if(!ng2_motion(&p->cycle_up_before,&p->cycle_anchor,NG2_UP,&owned)
        ||owned.dx||owned.dy!=(p->cycle_up_history==2? -1:0)
        ||owned.kind!=(p->cycle_up_history==2?NG2_MOVED:NG2_MOTION_UNKNOWN))return 0;
    row=&result->rows[0];
    if(!cycle_structural_cell(row->left,448,&x)||!cycle_structural_cell(row->sy+48,207,&y)
        ||y!= -3||!cycle_full_up_roi(row->left-112,row->sy-20,row->left+184,row->sy+52))return 0;
    for(k=0;k<3;++k)
        if(tile(&p->cycle_anchor,x+k,y)!=NG2_TILE_ITEM||row->slots[k].cx!=row->left+36*k
            ||row->slots[k].sy!=row->sy||!cycle_full_up_slot(&row->slots[k]))return 0;
    for(k=0;k<2;++k){
        int left=row->left+72*k-18,right=left+36,top=row->sy-20,bottom=top+40;
        if(left<465&&429<right&&top<45&&0<bottom)hud=1;
    }
    if(!hud)return 0;
    for(k=0;k<result->partial_count;++k)if(!cycle_full_up_slot(&result->partial[k]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(p->cycle_anchor.tiles[i]==NG2_TILE_ITEM){
        int cx=448+36*(i%23-11),cy=207+36*(i/23-5);
        if(!cycle_full_up_roi(cx-78,cy-86,cx+78,cy+61))return 0;
    }
    memset(choice,0,sizeof(*choice));choice->direction=NG2_UP;choice->reason=5;
    choice->target_y= -1;choice->obstacle=NG2_TILE_FLOOR;return 1;
}
/* Current-only geometry repeats the unchanged FULL UP preservation domain.
 * No old command/cache identity is restamped into this independent proof. */
static int cycle_current_up_layout(const NG2Scene *scene,const NG2RingResult *result){
    const NG2RingRow *row;int x,y,i,k,hud=0;
    if(!cycle_full_up_local(scene)||result->status!=NG2_RING_OK
        ||result->outcome!=NG2_RING_UNKNOWN||result->coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||result->row_count!=1||result->partial_safe_no_positive)return 0;
    row=&result->rows[0];
    if(!cycle_structural_cell(row->left,448,&x)||!cycle_structural_cell(row->sy+48,207,&y)
        ||y!= -3||!cycle_full_up_roi(row->left-112,row->sy-20,row->left+184,row->sy+52))return 0;
    for(k=0;k<3;++k)
        if(tile(scene,x+k,y)!=NG2_TILE_ITEM||row->slots[k].cx!=row->left+36*k
            ||row->slots[k].sy!=row->sy||!cycle_full_up_slot(&row->slots[k]))return 0;
    for(k=0;k<2;++k){
        int left=row->left+72*k-18,right=left+36,top=row->sy-20,bottom=top+40;
        if(left<465&&429<right&&top<45&&0<bottom)hud=1;
    }
    if(!hud)return 0;
    for(k=0;k<result->partial_count;++k)if(!cycle_full_up_slot(&result->partial[k]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM){
        int cx=448+36*(i%23-11),cy=207+36*(i/23-5);
        if(!cycle_full_up_roi(cx-78,cy-86,cx+78,cy+61))return 0;
    }
    return 1;
}
static int cycle_full_admit(const NG2Controller *p,const NG2RingResult *result,NG2Decision *choice){
    int d,r,k,direct=0;
    if(cycle_full_up_admit(p,result,choice))return 1;
    if(!cycle_full_history(p,&d)){
        if(!cycle_full_opening_history(p,&d))return 0;
        direct=1;
    }
    if(p->cycle_full_spent||p->cycle_full_framing||p->cycle.partial||!p->cycle.full_seen
        ||p->cycle.candidate_latched||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->s.input_state||p->finish_requested||p->s.terminal||!p->cycle.capture_id
        ||p->cycle.prefix!=p->s.last_completed_id||p->last_observed_prefix!=p->cycle.prefix
        ||!cycle_full_local_proof(&p->cycle_anchor,d)
        ||(direct?!cycle_full_opening_footprint(&p->cycle_anchor,d):
            !(cycle_full_local(&p->cycle_anchor,d)||cycle_full_footprint(&p->cycle_anchor,d)))
        ||result->outcome!=NG2_RING_UNKNOWN||result->coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||result->row_count<1||result->partial_safe_no_positive)return 0;
    for(r=0;r<result->row_count;++r){
        const NG2RingRow *row=&result->rows[r];
        /* binary_word_veto also scans the whole row's wider name union. */
        if(row->left<112||row->left>712||row->sy<20||row->sy>299
            ||!cycle_full_roi(row->left-112,row->sy-20,row->left+184,row->sy+52,d))return 0;
        for(k=0;k<3;++k)
            if(row->slots[k].cx!=row->left+36*k||row->slots[k].sy!=row->sy
                ||!cycle_full_slot(&row->slots[k],d))return 0;
    }
    for(k=0;k<result->partial_count;++k)
        if(!cycle_full_slot(&result->partial[k],d)
            &&(!direct||!cycle_full_opening_edge_slot(&result->partial[k],d)))return 0;
    for(k=0;k<NG2_TILE_COUNT;++k)if(p->cycle_anchor.tiles[k]==NG2_TILE_ITEM){
        int cx=448+36*(k%23-11),cy=207+36*(k/23-5);
        if(!cycle_full_roi(cx-78,cy-86,cx+78,cy+61,d))return 0;
    }
    memset(choice,0,sizeof(*choice));choice->direction=d;choice->reason=5;
    choice->target_x=dx[d];choice->target_y=0;choice->obstacle=NG2_TILE_FLOOR;
    return 1;
}
static int cycle_full_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    const NG2Scene *a=p->cycle_full_source_valid?&p->cycle_full_source:&p->cycle_anchor;
    int local=p->cycle_current_partial&&p->cycle_current_active?
        (p->cycle_full_choice.direction==NG2_UP&&cycle_current_partial_local(p,scene)):
        cycle_full_local_proof(scene,p->cycle_full_choice.direction);
    if(!local
        ||((memcmp(a->tiles,scene->tiles,NG2_TILE_COUNT)
            ||memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))
            &&!cycle_current_partial_top_relation(p,scene)))return NG2_REVALIDATE_PROTECTED;
    if(!ng2_motion(a,scene,p->cycle_full_choice.direction,motion)
        ||motion->kind!=NG2_BLOCKED||motion->dx||motion->dy)return NG2_REVALIDATE_MOTION;
    return NG2_REVALIDATE_NONE;
}
/* An unreserved observation may wait for the same classified view to become
 * directly stationary again. This is not a replacement anchor or a motion
 * proof: only the unchanged cycle_full_static predicate can grant a ticket. */
static int cycle_full_waitable(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    const NG2Scene *a=p->cycle_full_source_valid?&p->cycle_full_source:&p->cycle_anchor;
    int i;
    if((p->cycle_full_framing!=1&&p->cycle_full_framing!=2)||!p->cycle_full_spent
        ||p->s.input_state||p->cycle.pending||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE
        ||p->cycle.partial||!p->cycle.full_seen||p->cycle.candidate_latched
        ||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->finish_requested||p->s.terminal||p->beat_failed
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||p->s.last_completed_id!=p->cycle.prefix||p->last_observed_prefix!=p->cycle.prefix
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
        ||scene->gold_state!=a->gold_state||!actual_gold(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||!cycle_exact_item_protection(scene))return 0;
    /* The material test in cycle_full_static may return before Motion runs.
     * Even a no-input wait therefore checks the immutable source directly. */
    if(!ng2_motion(a,scene,p->cycle_full_choice.direction,motion)
        ||(motion->kind!=NG2_MOTION_UNKNOWN&&motion->kind!=NG2_BLOCKED)
        ||motion->dx||motion->dy)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i];
        if(a->protected_cells[i]!=scene->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    return 1;
}
/* This direct relation admits data only. Every local movement cell, wall,
 * ITEM and projected protection is still owned by the original FULL source.
 * Two later zero comparisons cannot bridge an unknown original comparison. */
static int cycle_full_data_relation(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    const NG2Scene *a=&p->cycle_full_source;int i,d=p->cycle_full_choice.direction;
    if(!p->cycle_full_source_valid||!p->cycle_full_spent
        ||p->cycle_full_framing>=3||p->s.input_state||p->cycle.candidate_latched
        ||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->finish_requested||p->s.terminal||p->beat_failed
        ||p->cycle.partial||!p->cycle.full_seen
        ||p->cycle.prefix!=p->cycle_full_source_prefix
        ||p->s.last_completed_id!=p->cycle.prefix||p->last_observed_prefix!=p->cycle.prefix
        ||scene->gold_state!=a->gold_state||!cycle_full_local_proof(scene,d))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a->protected_cells[i]!=scene->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||scene->protected_cells[i]
            ||(abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    return ng2_motion(a,scene,d,motion)&&motion->kind==NG2_BLOCKED&&!motion->dx&&!motion->dy;
}
/* An early FULL owns pixels only while this already-issued observation MOVE
 * awaits its original visual proof. After the real MOVE is independently
 * confirmed, a direct zero relation may select those still-fresh pixels for
 * data. It never substitutes for the command's frozen movement source. */
static int cycle_moved_data_local(const NG2Scene *scene,int d){
    return scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE&&actual_gold(scene)
        &&(d==NG2_LEFT||d==NG2_RIGHT)&&cycle_exact_item_protection(scene)
        &&tile(scene,0,0)==NG2_TILE_FLOOR&&!protected_at(scene,0,0)
        &&tile(scene,dx[d],0)==NG2_TILE_FLOOR&&!protected_at(scene,dx[d],0);
}
static int cycle_moved_data_relation(const NG2Scene *a,const NG2Scene *scene,int d){
    NG2Motion still={0};int i;
    if(a->gold_state!=scene->gold_state||!cycle_moved_data_local(a,d)
        ||!cycle_moved_data_local(scene,d))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a->protected_cells[i]!=scene->protected_cells[i]
            ||(old==NG2_TILE_GOLD&&latest!=old)
            ||((old==NG2_TILE_ITEM)!=(latest==NG2_TILE_ITEM)))return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||(abs(x)<=1&&abs(y)<=1)
            ||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))return 0;
        /* A positively revealed remote wall is data, never walking credit. */
        if(latest==NG2_TILE_GOLD&&(old==NG2_TILE_UNKNOWN||old==NG2_TILE_DOOR))continue;
        if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    return ng2_motion(a,scene,d,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
static int cycle_opened_partial(const NG2Controller *p,int d){
    return d>=1&&d<=4&&p->cycle_choice_valid&&p->cycle_choice.direction==d&&p->cycle_choice.reason==5
        &&p->cycle_choice.obstacle==NG2_TILE_FLOOR
        &&p->cycle_choice.target_x==dx[d]&&p->cycle_choice.target_y==dy[d]
        &&last_ack_opened_gate(p,d);
}
/* Keep the frozen source and the old DIRT rule. An acknowledged opened entry
 * also retains the exact GOLD-shielded diagonal already admitted by the old
 * quiet gate path. Remote STONE may resolve to DIRT, never to unknown/floor.
 * Full choice/protection and independent strict zero remain required below. */
static int cycle_partial_quiet_cell(const NG2Controller *p,const NG2Scene *source,
                                  const NG2Scene *scene,int d,int i){
    int old=source->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
    int opened=cycle_opened_partial(p,d);
    int shielded=opened&&x*dx[d]+y*dy[d]==2&&abs(x*dy[d]-y*dx[d])==1
        &&((old==NG2_TILE_FLOOR&&latest==NG2_TILE_DIRT)
            ||(old==NG2_TILE_DIRT&&latest==NG2_TILE_FLOOR))
        &&tile(source,x-dx[d],y-dy[d])==NG2_TILE_GOLD
        &&tile(scene,x-dx[d],y-dy[d])==NG2_TILE_GOLD;
    if(old==latest)return 1;
    if(source->protected_cells[i]||scene->protected_cells[i])return 0;
    if(shielded)return 1;
    return !((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))
        &&((old==NG2_TILE_DIRT&&(latest==NG2_TILE_UNKNOWN||latest==NG2_TILE_FLOOR))
            ||(old==NG2_TILE_STONE&&latest==NG2_TILE_DIRT)
            ||(opened&&old==NG2_TILE_FLOOR&&latest==NG2_TILE_UNKNOWN));
}
static int cycle_partial_distant_dirt(const NG2Controller *p,const NG2Scene *source,
                                     const NG2Scene *scene,int d){
    int i;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(!cycle_partial_quiet_cell(p,source,scene,d,i))return 0;
    return 1;
}
/* A same-opening clipped side row may flicker between the three ordinary
 * floor palette labels outside the actual MOVE footprint. Preserve its
 * classified source instead of repeatedly discarding the upcoming input.
 * This is only a material relation: cycle_partial_comparison still requires
 * normal strict zero directly from that immutable source on every image. */
static int cycle_partial_side_palette(const NG2Controller *p,const NG2Scene *scene,int d){
    const NG2Scene *a=&p->cycle_anchor;const NG2ControllerEvent *e;
    int i,y,rail=0,items=0,left=12,right=-12,row=5;
    if((d!=NG2_LEFT&&d!=NG2_RIGHT)||!p->cycle_refresh_safe||!p->cycle.partial
        ||p->cycle.full_seen||p->cycle.pending||p->cycle.candidate_latched
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||p->cycle_framing_credit||p->cycle_full_framing||p->cycle_full_spent
        ||p->entry.active||p->lower.active||p->cycle_restart_unproved
        ||p->cycle_pause_attempted||p->cycle_storage_error||p->finish_requested||p->s.terminal
        ||!p->s.lead_confirmed||level_moves(p)<=0||p->s.input_state>1
        ||p->cycle.prefix!=p->s.last_completed_id||p->last_observed_prefix!=p->cycle.prefix
        ||!cycle_opened_partial(p,d)||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_PARTIAL||scene->goods!=NG2_GOODS_PARTIAL
        ||!cycle_exact_item_protection(a)||!cycle_exact_item_protection(scene))return 0;
    e=p->event_count?&p->events[p->event_count-1]:NULL;
    if(p->s.input_state==1&&(!e||e->begin_ns||e->outcome||p->command.kind!=NG2_ACTION_MOVE))return 0;
    /* A separate observed outside rail supports the clipped side-room
     * geometry. The later all-cell relation preserves every one of its GOLD
     * cells; an entry bracket or newly exposed ITEM alone cannot supply it. */
    for(i=-11;i<=11;++i)if(i*dx[d]>=3){
        int complete=1;
        for(y=-2;y<=1;++y)complete&=tile(a,i,y)==NG2_TILE_GOLD;
        rail|=complete;
    }
    if(!rail)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(old==NG2_TILE_ITEM){
            if(items&&row!=y)return 0;
            row=y;++items;if(x<left)left=x;if(x>right)right=x;
        }
        if(a->protected_cells[i]!=scene->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||(abs(x)<=1&&abs(y)<=1)
            ||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_DIRT))return 0;
    }
    return items>=3&&right-left+1==items;
}
enum { CYCLE_TOP_ALIAS=1,CYCLE_TOP_ITEM=2,CYCLE_TOP_DATA=4 };
/* Separate an observed top duplicate from the unchanged real row beneath it.
 * Every other cell still uses the old quiet/shielded rule. The exact ITEM
 * mask explains only its own top margins; it is not a general protection or
 * GOLD exception. New ITEM/material evidence requires a new normal job. */
static int cycle_partial_top_roles(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_anchor;
    int i,x,left=12,right=-12,items=0,roles=0;
    if(!p->cycle_refresh_safe||p->cycle_framing_credit||!cycle_opened_partial(p,NG2_UP)
        ||a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_PARTIAL||scene->goods!=NG2_GOODS_PARTIAL
        ||!cycle_exact_item_protection(a)||!cycle_exact_item_protection(scene))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],y=i/23-5;
        if((old==NG2_TILE_ITEM||next==NG2_TILE_ITEM)&&y!=-5&&y!=-4)return 0;
        if(y==-4){
            if((old==NG2_TILE_ITEM)!=(next==NG2_TILE_ITEM))return 0;
            if(old==NG2_TILE_ITEM){
                x=i%23-11;if(x<left)left=x;if(x>right)right=x;++items;
            }
        }
    }
    if(items<3||right-left+1!=items||left<=-11||right>=11)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],cx=i%23-11,cy=i/23-5;
        int top=cy==-5&&cx>=left&&cx<=right;
        int margin=cy==-5&&(cx==left-1||cx==right+1);
        if(top){
            if(!a->protected_cells[i]||!scene->protected_cells[i])return 0;
            if(old==next)continue;
            if(next==NG2_TILE_ITEM&&(old==NG2_TILE_UNKNOWN||old==NG2_TILE_FLOOR
                    ||old==NG2_TILE_DIRT||old==NG2_TILE_GOLD))roles|=CYCLE_TOP_ITEM;
            else if(old==NG2_TILE_ITEM&&(next==NG2_TILE_UNKNOWN||next==NG2_TILE_FLOOR
                    ||next==NG2_TILE_DIRT))roles|=CYCLE_TOP_ALIAS;
            else if((old==NG2_TILE_UNKNOWN||old==NG2_TILE_FLOOR||old==NG2_TILE_DIRT)
                &&(next==NG2_TILE_UNKNOWN||next==NG2_TILE_FLOOR||next==NG2_TILE_DIRT))roles|=CYCLE_TOP_DATA;
            else return 0;
        }else{
            if((old==NG2_TILE_ITEM||next==NG2_TILE_ITEM)&&cy==-5)return 0;
            if(a->protected_cells[i]!=scene->protected_cells[i]&&!margin)return 0;
            if(!cycle_partial_quiet_cell(p,a,scene,NG2_UP,i))return 0;
        }
    }
    return roles;
}
/* A clipped duplicate at the top edge may disappear while its complete,
 * protected lower projection remains. This is not the empty-framing proof:
 * every real lower product, wall and other protected cell is immutable. */
static int cycle_partial_top_alias(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_anchor;int x,i,left=12,right=-12,changed=0;
    if(cycle_partial_top_roles(p,scene)==CYCLE_TOP_ALIAS)return 1;
    if(p->cycle_framing_credit||!cycle_opened_partial(p,NG2_UP))return 0;
    for(x=-11;x<=11;++x)if(tile(a,x,-5)==NG2_TILE_ITEM){
        if(left==12)left=x;
        right=x;
    }
    if(left>right||left<=-11||right>=11)return 0;
    for(x=left;x<=right;++x){
        int old=tile(a,x,-5),next=tile(scene,x,-5);
        if(old!=NG2_TILE_ITEM||tile(a,x,-4)!=NG2_TILE_ITEM||tile(scene,x,-4)!=NG2_TILE_ITEM
            ||!protected_at(a,x,-5)||!protected_at(scene,x,-5)
            ||!protected_at(a,x,-4)||!protected_at(scene,x,-4)
            ||(next!=NG2_TILE_ITEM&&next!=NG2_TILE_UNKNOWN&&next!=NG2_TILE_FLOOR&&next!=NG2_TILE_DIRT))return 0;
        changed|=old!=next;
    }
    if(!changed)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int cx=i%23-11,cy=i/23-5,top=cy== -5&&cx>=left&&cx<=right;
        int margin=cy== -5&&(cx==left-1||cx==right+1);
        if(!top&&a->tiles[i]!=scene->tiles[i])return 0;
        if(a->protected_cells[i]!=scene->protected_cells[i]
            &&!(margin&&a->protected_cells[i]&&!scene->protected_cells[i]
                &&tile(a,cx,-4)!=NG2_TILE_ITEM&&tile(scene,cx,-4)!=NG2_TILE_ITEM))return 0;
    }
    return 1;
}
/* A static failure is never converted into a motion wait. The anchor remains
 * the classified source, including every ITEM/GOLD/protected cell. */
static int cycle_partial_static(const NG2Controller *p,const NG2Scene *scene,NG2Decision *latest){
    int i;
    if(p->cycle_framing_credit){
        if(!last_ack_opened_gate(p,NG2_UP)||!cycle_framing_scene_proof(&p->cycle_anchor)
            ||!cycle_framing_scene_proof(scene))return NG2_REVALIDATE_FLOOR;
        for(i=0;i<NG2_TILE_COUNT;++i)
            if((p->cycle_anchor.tiles[i]==NG2_TILE_ITEM)!=(scene->tiles[i]==NG2_TILE_ITEM))return NG2_REVALIDATE_PROTECTED;
    }
    if(!p->cycle_choice_valid||!cycle_partial_choice(p,scene,latest)
        ||!same_choice(&p->cycle_choice,latest))return NG2_REVALIDATE_ROUTE;
    if(cycle_partial_top_alias(p,scene))return NG2_REVALIDATE_NONE;
    if(!cycle_partial_distant_dirt(p,&p->cycle_anchor,scene,latest->direction)
        &&!cycle_partial_side_palette(p,scene,latest->direction))return NG2_REVALIDATE_ROUTE;
    if(memcmp(p->cycle_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT))return NG2_REVALIDATE_PROTECTED;
    return NG2_REVALIDATE_NONE;
}
static int cycle_partial_comparison(const NG2Controller *p,const NG2Scene *scene,int *wait,NG2Motion *motion){
    NG2Decision latest;NG2Motion still={0};int validation=cycle_partial_static(p,scene,&latest);
    if(wait)*wait=0;
    if(motion)memset(motion,0,sizeof(*motion));
    if(validation)return validation;
    if(!ng2_motion(&p->cycle_anchor,scene,latest.direction,&still))return NG2_REVALIDATE_MOTION;
    if(motion)*motion=still;
    if(still.kind==NG2_BLOCKED&&!still.dx&&!still.dy)return NG2_REVALIDATE_NONE;
    if(wait&&still.kind==NG2_MOTION_UNKNOWN&&cycle_opened_partial(p,latest.direction))*wait=1;
    return NG2_REVALIDATE_MOTION;
}
static int cycle_partial_relation(const NG2Controller *p,const NG2Scene *scene){
    return cycle_partial_comparison(p,scene,NULL,NULL)==NG2_REVALIDATE_NONE;
}
/* Record only the first independent rejected comparison per bound job. This
 * diagnostic uses the classified source, never the pre-opening MOVE source.
 * A zero change mask is meaningful when only the motion proof is missing. */
static void cycle_record_rejection(NG2Controller *p,const NG2Scene *scene,uint64_t id,int validation){
    int mask,tiles,protected_cells;
    if(p->cycle_rejection_recorded||!p->cycle.capture_id||id<=p->cycle.capture_id)return;
    mask=scene_change(&p->cycle_anchor,scene,&tiles,&protected_cells);
    if(!mask&&validation!=NG2_REVALIDATE_MOTION)return;
    record_change_basis(p,&p->cycle_anchor,p->cycle.capture_id,p->cycle.prefix,
        scene,id,mask,tiles,protected_cells,0,validation,1);
    p->cycle_rejection_recorded=1;
}
static void cycle_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t prefix){
    uint64_t horizon=start+FRESH,sync=p->sync_ns+12*SECOND;
    p->cycle.capture_id=id;p->cycle.capture_start_ns=start;p->cycle.prefix=prefix;
    if(p->initial_restart.stage==NG2_INITIAL_VETO&&!p->initial_restart.veto_job
        &&id==p->initial_restart.veto_capture&&prefix==p->initial_restart.veto_prefix)
        p->initial_restart.veto_job=p->cycle.job_id;
    p->cycle.deadline_ns=start+CYCLE_CAPTURE_BUDGET;p->cycle_anchor=*scene;
    cycle_cache_up_history(p,scene,id,start,prefix);
    diagnostic_comparison(p,0,NG2_REVALIDATE_NONE,NULL);
    p->cycle_rejection_recorded=0;
    p->cycle.partial=scene->goods==NG2_GOODS_PARTIAL;
    p->cycle_choice_valid=cycle_partial_choice(p,scene,&p->cycle_choice);
    if(p->s.lead_confirmed&&p->latest_verified_ns&&p->recovery.mode!=NG2_RECOVERY_POST_MOVE)
        sync=p->latest_verified_ns+12*SECOND;
    if(p->command_sync_deadline)sync=minimum(sync,p->command_sync_deadline);
    p->cycle_sync_deadline=minimum(sync,session_bound(p));
    horizon=minimum(horizon,p->cycle_sync_deadline);
    if(p->model.last_ns)horizon=minimum(horizon,p->model.last_ns+FRESH);
    if(p->s.walk_started_ns)horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
    if(p->motion_wait.active)horizon=minimum(horizon,p->motion_wait.deadline_ns);
    if(p->opened_entry_parent)horizon=minimum(horizon,p->opened_entry_parent);
    if(p->entry.active)horizon=minimum(horizon,p->entry.parent);
    if(p->upper.active)horizon=minimum(horizon,p->upper.parent);
    p->cycle.continuation_deadline_ns=horizon;
    if(!p->cycle.partial){memcpy(p->restart_fingerprint,scene->fingerprint,48);p->restart_baseline_valid=1;}
}
static void cycle_latch(NG2Controller *p,const NG2Scene *scene,uint64_t now){
    uint64_t level=p->cycle.level_id,job=p->cycle.job_id+1;
    int completed=p->cycle.completed_shops,sticky=p->cycle.candidate_latched;
    int search_restart=p->cycle.state==NG2_CYCLE_SEARCH&&p->command.kind==NG2_ACTION_RESTART
        &&(p->s.input_state==2||p->s.input_state==3);
    memset(&p->cycle,0,sizeof(p->cycle));p->cycle.abi_version=1;p->cycle.struct_size=sizeof(p->cycle);
    p->cycle.level_id=level;p->cycle.job_id=job;p->cycle.completed_shops=completed;
    p->cycle.candidate_latched=sticky;p->cycle.state=NG2_CYCLE_HOLD;p->cycle.pending=1;
    p->cycle.partial=scene->goods==NG2_GOODS_PARTIAL;p->cycle.full_seen=scene->goods==NG2_GOODS_VISIBLE;
    p->cycle.hold_started_ns=now;p->cycle_pause_attempted=p->cycle_storage_error=0;
    p->cycle_partial_credit=p->cycle_framing_credit=p->cycle_queued_valid=p->cycle_choice_valid=p->cycle_refresh_safe=0;
    p->cycle_rejection_recorded=0;p->cycle_full_framing=0;
    p->cycle_up_history=0;
    p->cycle_search_restart=search_restart;p->cycle_restart_unproved=0;
    not_sent(p,now,NG2_REASON_GOODS);clear_slots(p);
    clear_stationary_wait(p);p->gate_refresh_state=NG2_GATE_REFRESH_NONE;
    p->terrain_refresh_active=p->observation_refresh_active=0;
    p->passage_wait_kind=0;p->restart_intent=0;
    /* A first goods frame may also be the first visual RESTART response.
     * Keep that original baseline until the current ACK prefix is admitted. */
    if(!search_restart)p->restart_pending=p->restart_baseline_valid=0;
    p->proof_deadline=p->proof_capture_id=0;p->proof_reacquire=p->visual_phase_failed=0;
    p->s.phase=NG2_PHASE_FINISH;p->s.reason=NG2_REASON_GOODS;
    if(p->cycle.full_seen)p->s.goods=1;
}
static void cycle_full_data_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                                uint64_t start,uint64_t prefix,uint64_t now){
    uint64_t sync=p->cycle_sync_deadline;size_t samples=p->sample_count;
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,p->cycle_full_parent);
    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,p->cycle.continuation_deadline_ns);
    p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,sync);
    p->cycle_full_data_active=1;p->cycle_full_data_blocked=0;
    clear_model(p);p->sample_count=samples;
    p->proof_capture_id=p->proof_deadline=0;p->preparation_epoch=0;
    if(now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
}
/* An early FULL may have closed visual UNKNOWN before the same ACK's
 * original source can prove its real entry. This exceptional refresh is
 * data only: it consumes that original MOVED once within its old visual
 * bound, then fixes a new FULL source for the already allocated one-use
 * observation. It never calls the early FULL comparison a stationary one. */
static int cycle_full_entered_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    const NG2Scene *a=&p->cycle_full_source;NG2ControllerEvent *e=event(p);
    NG2Motion moved={0};int i,items=0,revealed=0,d=p->cycle_full_choice.direction,moves=p->s.moves;
    uint64_t hold=p->cycle.hold_started_ns;
    if((p->cycle_full_framing!=1&&p->cycle_full_framing!=2)||!p->cycle_full_spent
        ||!p->cycle_full_source_valid||p->cycle_full_data_active||p->cycle.pending
        ||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE||p->cycle.status!=NG2_RING_OK
        ||p->cycle.outcome!=NG2_RING_UNKNOWN||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||p->cycle.partial||!p->cycle.full_seen||p->cycle.candidate_latched
        ||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->s.input_state||p->s.current_command_id||p->finish_requested||p->s.terminal||p->beat_failed
        ||p->entry.active||p->lower.active||(d!=NG2_LEFT&&d!=NG2_RIGHT)
        ||p->cycle.capture_id!=p->cycle_full_source_id||p->cycle.prefix!=p->cycle_full_source_prefix
        ||prefix!=p->cycle.prefix||prefix!=p->s.last_completed_id||prefix!=p->last_observed_prefix
        ||p->command.id!=prefix||p->command.kind!=NG2_ACTION_MOVE||p->command.direction!=d
        ||p->command_choice.obstacle!=NG2_TILE_FLOOR||p->motion_wait.active
        ||p->motion_wait.command_id!=p->command.id
        ||p->motion_wait.source_capture_id!=p->command.source_capture_id
        ||p->motion_wait.attempts>=MOTION_ASSESSMENTS
        ||!e||memcmp(&e->command,&p->command,sizeof(p->command))||e->outcome!=2
        ||!e->begin_ns||!e->end_ns||e->end_ns!=p->ack_ns
        ||e->motion!=NG2_MOTION_UNKNOWN||e->dx||e->dy||e->observed_capture_id!=p->cycle_full_source_id
        ||id<=p->cycle_full_source_id||start<p->cycle.release_after_ns||end<start||now<end
        ||start<maximum(p->ack_ns,p->command.target_ns+80000000)
        ||now>p->cycle_full_parent||now>p->cycle.continuation_deadline_ns
        ||end>p->motion_wait.deadline_ns||now>p->motion_wait.deadline_ns
        ||(p->motion_wait.attempts&&(start<p->motion_retry_last_ns
            ||start-p->motion_retry_last_ns<p->command_period/10))
        ||(p->motion_wait.attempts==MOTION_ASSESSMENTS-1
            &&(start<p->motion_retry_start_ns||start-p->motion_retry_start_ns<p->command_period))
        ||p->before.state!=NG2_FLOOR||p->before.goods!=NG2_GOODS_UNKNOWN
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(&p->before,dx[d],0)!=NG2_TILE_FLOOR
        ||scene->gold_state!=a->gold_state||!cycle_full_local_proof(scene,d)
        ||tile(scene,-dx[d],0)!=NG2_TILE_FLOOR||protected_at(scene,-dx[d],0)
        ||!ng2_motion(&p->before,scene,d,&moved)||moved.kind!=NG2_MOVED||moved.dx!=dx[d]||moved.dy)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        items+=old==NG2_TILE_ITEM;
        if(a->protected_cells[i]!=scene->protected_cells[i]
            ||((old==NG2_TILE_ITEM)!=(latest==NG2_TILE_ITEM))
            ||((old==NG2_TILE_GOLD)!=(latest==NG2_TILE_GOLD)))return 0;
        if(old==latest)continue;
        /* FULL coordinates are after entry. The old ACK origin projects
         * to -direction; the proposed next observation ends at +direction.
         * No changed cell may touch any of those three local footprints. */
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y)<=1)
            ||(abs(x+dx[d])<=1&&abs(y)<=1))return 0;
        if(a->protected_cells[i]){
            if(old!=NG2_TILE_UNKNOWN||latest!=NG2_TILE_FLOOR)return 0;
            ++revealed;continue;
        }
        if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    if(items!=3||revealed!=1)return 0;
    /* Reuse the original movement accounting and primary/reference trace.
     * No input state is reopened, and all resulting old slot candidates
     * are revoked by the data bind before any caller can request a ticket. */
    resolve_move(p,scene,id,start,end);
    if(p->finish_requested||p->s.terminal||p->s.moves!=moves+1
        ||e->motion!=NG2_MOVED||e->dx!=dx[d]||e->dy)return 1;
    p->cycle_full_source=*scene;p->cycle_full_source_id=id;p->cycle_full_source_start=start;
    cycle_full_data_bind(p,scene,id,start,prefix,now);
    p->cycle.hold_started_ns=hold;
    return 1;
}
static int cycle_retry_source_qualified(const NG2Scene *scene){
    return scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE&&actual_gold(scene)
        &&cycle_exact_item_protection(scene)&&tile(scene,0,0)==NG2_TILE_FLOOR&&!protected_at(scene,0,0);
}
static int cycle_retry_basis(const NG2Controller *p,uint64_t now,int transient_unknown){
    uint64_t parent=p->cycle_retry_only?p->cycle_retry_parent:p->cycle.continuation_deadline_ns;
    return !p->restart_yield.s.pending&&p->cycle.capture_id&&!p->cycle.partial&&p->cycle.full_seen
        &&!p->cycle.candidate_latched&&!p->cycle_restart_unproved&&!p->cycle_pause_attempted
        &&!p->cycle_storage_error&&!p->cycle.durable_ns&&!p->cycle.intent_ns&&!p->cycle.pause_capture_id
        &&!p->s.input_state&&!p->finish_requested&&!p->s.terminal&&!p->entry.active&&!p->lower.active&&!p->upper.active
        &&!p->cycle_full_spent&&!p->cycle_full_framing&&!p->cycle_full_data_active
        &&p->cycle_retry_used<2&&!(p->cycle_retry_blocked&~(transient_unknown?2:0))&&parent&&now<=parent
        &&cycle_retry_source_qualified(&p->cycle_anchor)
        &&p->cycle.prefix==p->s.last_completed_id&&p->last_observed_prefix==p->cycle.prefix
        &&(!p->cycle_retry_only||(p->cycle.prefix==p->cycle_retry_prefix&&p->cycle.level_id==p->cycle_retry_level));
}
static int cycle_retry_eligible(const NG2Controller *p,uint64_t now){
    return p->cycle.pending&&cycle_retry_basis(p,now,0);
}
static int cycle_retry_relation(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=p->cycle_retry_only?&p->cycle_retry_source:&p->cycle_anchor;
    NG2Motion still={0};int i;
    if(a->state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||a->goods!=NG2_GOODS_VISIBLE||scene->goods!=NG2_GOODS_VISIBLE
        ||a->gold_state!=scene->gold_state||!actual_gold(scene)
        ||!cycle_exact_item_protection(a)||!cycle_exact_item_protection(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||protected_at(scene,0,0))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a->protected_cells[i]!=scene->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||(abs(x)<=1&&abs(y)<=1)
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    return ng2_motion(a,scene,NG2_LEFT,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
/* The near-neighborhood material refresh is DATA only. Neither this helper
 * nor its original anchor can grant MOVE or loosen pure-DEADLINE recovery. */
static int cycle_retry_data_relation(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_retry_source;NG2Motion still={0};int i;
    if(!p->cycle_retry_data||!cycle_retry_source_qualified(a)||!cycle_retry_source_qualified(scene)
        ||a->gold_state!=scene->gold_state)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i];
        if(a->protected_cells[i]!=scene->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE&&latest!=NG2_TILE_DIRT))return 0;
    }
    return ng2_motion(a,scene,NG2_LEFT,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
static void cycle_retry_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                             uint64_t start,uint64_t prefix,uint64_t now){
    uint64_t sync=p->cycle_sync_deadline;
    ++p->cycle_retry_used;p->cycle_retry_waiting=0;
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->cycle.hold_started_ns=p->cycle_retry_hold;
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,p->cycle_retry_parent);
    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,p->cycle.continuation_deadline_ns);
    p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,sync);
    p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
    clear_slots(p);clear_model(p);p->proof_capture_id=p->proof_deadline=p->preparation_epoch=0;
}
/* Called before freezing a recoverable deadline. An outstanding worker keeps
 * its exact identity until assess() returns, including any late positive hint. */
static int cycle_retry_wait(NG2Controller *p,uint64_t now,int drained){
    if(!cycle_retry_eligible(p,now))return 0;
    if(!p->cycle_retry_only){
        p->cycle_retry_only=1;p->cycle_retry_parent=p->cycle.continuation_deadline_ns;
        p->cycle_retry_hold=p->cycle.hold_started_ns;p->cycle_retry_source=p->cycle_anchor;
        p->cycle_retry_prefix=p->cycle.prefix;p->cycle_retry_level=p->cycle.level_id;
    }
    p->cycle_retry_waiting=1;
    if(!drained)return 1;
    p->cycle.pending=0;p->cycle.status=NG2_RING_DEADLINE;p->cycle.outcome=NG2_RING_UNKNOWN;
    p->cycle.assessment_ns=now;p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;
    if(p->cycle_queued_valid&&p->cycle.queued_prefix==p->cycle_retry_prefix
        &&now<=p->cycle.queued_capture_start_ns+CYCLE_CAPTURE_BUDGET){
        NG2Scene queued=p->cycle_queued_scene;
        uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,prefix=p->cycle.queued_prefix;
        cycle_retry_bind(p,&queued,id,start,prefix,now);
    }
    return 1;
}
static int cycle_result_positive_hint(const NG2RingResult *result){
    int r,k,hint=result->outcome==NG2_RING_TARGET||result->outcome==NG2_RING_CANDIDATE;
    for(r=0;r<result->row_count;++r)for(k=0;k<3;++k){
        const NG2RingSlot *s=&result->rows[r].slots[k];
        if(s->outcome>NG2_RING_IGNORED_CONTAINER||s->icon_score_exact>1||s->word_present<0||s->word_present>1
            ||!cycle_score(s->icon_score,0.0)||!cycle_score(s->icon_upper_bound,0.0)
            ||!cycle_score(s->word_iou,0.0)||!cycle_score(s->word_coverage,0.0))return -1;
        if(s->outcome==NG2_RING_TARGET||s->outcome==NG2_RING_CANDIDATE||s->icon_score>=.80
            ||s->icon_upper_bound>=.80||(s->word_iou>=.82&&s->word_coverage>=.90))hint=1;
    }
    for(k=0;k<result->partial_count;++k){
        const NG2RingSlot *s=&result->partial[k];
        if(s->outcome>NG2_RING_IGNORED_CONTAINER||s->icon_score_exact>1||s->word_present<0||s->word_present>1
            ||!cycle_score(s->icon_score,0.0)||!cycle_score(s->icon_upper_bound,0.0)
            ||!cycle_score(s->word_iou,0.0)||!cycle_score(s->word_coverage,0.0))return -1;
        if(s->outcome==NG2_RING_TARGET||s->outcome==NG2_RING_CANDIDATE||s->icon_score>=.80
            ||s->icon_upper_bound>=.80||(s->word_iou>=.82&&s->word_coverage>=.90))hint=1;
    }
    return hint;
}
static int restart_yield_basis(const NG2Controller *p,uint64_t now){
    const NG2RestartYield *y=&p->restart_yield;
    const NG2ControllerCycleStatus *old=&y->prior;
    return y->s.enabled&&y->s.pending&&!y->s.invalid&&valid_time(now)
        &&now>=y->first_end&&now<=y->s.parent_deadline_ns&&handoff_original_bounds(p,now)
        &&old->job_id==y->s.old_job_id&&old->status==NG2_RING_OK&&old->outcome==NG2_RING_NEGATIVE
        &&old->coverage==NG2_RING_COVERAGE_COMPLETE&&!old->partial&&!old->pending&&!old->candidate_latched
        &&old->durable_ns&&old->intent_ns&&old->outcome_ns&&old->pause_capture_id
        &&old->restart_command_id==y->s.restart_command_id
        &&old->next_floor_capture_id==y->s.new_floor_capture_id
        &&p->cycle.level_id==y->s.level_id&&p->s.x==0&&p->s.y==0&&!level_inputs(p)&&!level_moves(p)
        &&p->s.inputs==y->inputs&&p->s.moves==y->moves&&p->s.restarts==y->restarts
        &&p->s.inputs<=16&&p->s.restarts<=12&&!p->cycle_storage_error&&!p->cycle.candidate_latched
        &&(!p->irregular.enabled||p->irregular.stage==NG2_IRREGULAR_IDLE
            ||(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&p->irregular.outcome_ns));
}
static int restart_yield_positive_hint(const NG2RingResult *result){
    int row,hint=cycle_result_positive_hint(result);
    if(hint<0)return hint;
    for(row=0;row<result->row_count;++row){
        if(result->rows[row].outcome>NG2_RING_NEGATIVE)return -1;
        if(result->rows[row].outcome==NG2_RING_TARGET||result->rows[row].outcome==NG2_RING_CANDIDATE)hint=1;
    }
    return hint;
}
int ng2_controller_enable_restart_yield(NG2Controller *p){
    if(!p||!p->cycle_enabled||!p->irregular.enabled||p->restart_yield.s.enabled
        ||p->s.terminal||p->finish_requested||p->s.capture_count||p->have_scene||p->event_count)return 0;
    p->restart_yield.s.enabled=1;return 1;
}
int ng2_controller_enable_continuous(NG2Controller *p,int32_t successor,uint64_t deadline){
    if(!p||p->campaign.enabled||successor<0||successor>1||!valid_time(deadline)
        ||deadline<=p->s.started_ns||deadline-p->s.started_ns>2880*SECOND)return 0;
    if(ng2_controller_enable_restart_yield(p)!=1)return 0;
    p->campaign.abi_version=1;p->campaign.struct_size=sizeof(p->campaign);
    p->campaign.enabled=1;p->campaign.successor_floor=successor;
    p->campaign.root_deadline_ns=deadline;return 1;
}
int ng2_controller_enable_initial_restart(NG2Controller *p){
    if(!p||!p->cycle_enabled||!p->irregular.enabled||!p->restart_yield.s.enabled
        ||p->initial_restart.configured||(p->campaign.enabled&&p->campaign.successor_floor)
        ||p->s.terminal||p->finish_requested||p->s.capture_count||p->seen_id||p->have_scene
        ||p->event_count||p->s.input_state||p->s.inputs||p->s.moves||p->s.restarts)return 0;
    p->initial_restart.configured=1;p->initial_restart.stage=NG2_INITIAL_SOURCE;return 1;
}
void ng2_controller_continuous_status(const NG2Controller *p,NG2ControllerContinuousStatus *out){
    if(!out)return;
    memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
    if(p){*out=p->campaign;out->abi_version=1;out->struct_size=sizeof(*out);}
}
int ng2_controller_restart_yield_ready(const NG2Controller *p,uint64_t now){
    const NG2RestartYield *y;
    if(!p)return 0;
    y=&p->restart_yield;
    return restart_yield_basis(p,now)&&now>=p->last_now&&!p->s.terminal&&!p->finish_requested
        &&!p->s.input_state&&!y->pause&&!p->cycle.pending&&!p->cycle_late_worker
        &&!(y->required&~y->done)&&p->have_scene&&p->scene.state==NG2_FLOOR
        &&p->s.last_capture_start_ns<=now&&p->s.last_capture_end_ns<=now
        &&now-p->s.last_capture_start_ns<=FRESH&&p->s.last_capture_start_ns>=y->ack
        &&p->last_observed_prefix==y->s.restart_command_id
        &&p->s.last_completed_id==y->s.restart_command_id
        &&ng2_fingerprint_changed(y->fingerprint,p->scene.fingerprint)&&pause_ui_ready(p,now)
        &&restart_yield_ui_source(p,p->s.last_capture_id,p->s.last_capture_start_ns,now,0);
}
void ng2_controller_restart_yield_status(const NG2Controller *p,uint64_t now,NG2ControllerRestartYieldStatus *out){
    const NG2RestartYield *y;
    if(!out)return;
    memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
    if(!p)return;
    y=&p->restart_yield;*out=y->s;out->abi_version=1;out->struct_size=sizeof(*out);
    out->ready=ng2_controller_restart_yield_ready(p,now);
    out->goods_processed=y->current_kind&&(y->done&y->current_kind)!=0;
    out->needs_goods=y->required&~y->done;
    out->source_capture_id=p->s.last_capture_id;out->source_start_ns=p->s.last_capture_start_ns;
    out->source_prefix=p->last_observed_prefix;
    if(y->s.enabled&&!y->s.pending&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART){
        out->old_job_id=p->cycle.job_id;out->restart_command_id=p->cycle.restart_command_id;
        out->new_floor_capture_id=p->cycle.next_floor_capture_id;
        out->new_floor_start_ns=y->first_start;out->prefix=p->cycle.restart_command_id;
    }
}
int ng2_controller_restart_yield_goods(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2RestartYield *y;int kind;
    if(!p)return 0;
    y=&p->restart_yield;
    if(!restart_yield_basis(p,now)||now<p->last_now||p->s.terminal||p->finish_requested
        ||p->s.input_state||y->pause||p->cycle.pending||p->cycle_late_worker
        ||!valid_scene(scene)||scene->state!=NG2_FLOOR||scene->goods==NG2_GOODS_UNKNOWN
        ||!id||id>p->seen_id||id<=y->last_goods_id||id<=y->prior.capture_id
        ||!valid_time(start)||!valid_time(end)||end<=start||end>now||start<y->ack
        ||now-start>CYCLE_CAPTURE_BUDGET||prefix!=y->s.restart_command_id
        ||p->s.last_completed_id!=prefix||p->last_observed_prefix!=prefix
        ||!ng2_fingerprint_changed(y->fingerprint,scene->fingerprint))return 0;
    kind=scene->goods==NG2_GOODS_PARTIAL?1:2;
    if(y->submitted&kind)return 0;
    p->last_now=now;y->required|=kind;y->submitted|=kind;y->current_kind=kind;
    y->last_goods_id=id;y->s.goods_capture_id=id;y->s.goods_start_ns=start;y->s.permitted=0;
    /* Bind ordinary immutable DATA without installing this retained image as
     * the current UI scene, world position or motion reference. */
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,y->s.parent_deadline_ns);
    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,y->s.parent_deadline_ns);
    p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,y->s.parent_deadline_ns);
    return 1;
}
int ng2_controller_restart_yield_permit(NG2Controller *p,uint64_t capture,uint64_t start,uint64_t prefix,uint64_t now){
    NG2RestartYield *y;
    if(!p||!ng2_controller_restart_yield_ready(p,now)||capture!=p->s.last_capture_id
        ||start!=p->s.last_capture_start_ns||prefix!=p->last_observed_prefix)return 0;
    y=&p->restart_yield;p->last_now=now;y->s.permitted=1;
    y->permit_capture=capture;y->permit_start=start;return 1;
}
int ng2_controller_continuous_finish(NG2Controller *p,uint64_t capture,uint64_t start,uint64_t prefix,uint64_t now){
    NG2RestartYield *y;NG2ControllerContinuousStatus proof;
    if(!p||!p->campaign.enabled||campaign_expired(p,now)||p->campaign.qualified
        ||!ng2_controller_restart_yield_ready(p,now)||p->s.input_state||p->s.current_command_id)return 0;
    y=&p->restart_yield;
    if(!y->s.permitted||y->permit_capture!=capture||y->permit_start!=start
        ||capture!=p->s.last_capture_id||start!=p->s.last_capture_start_ns
        ||prefix!=p->last_observed_prefix||prefix!=y->s.restart_command_id)return 0;
    proof=p->campaign;proof.qualified=1;proof.qualified_ns=now;
    proof.parent_deadline_ns=minimum(y->s.parent_deadline_ns,session_bound(p));
    proof.old_job_id=y->s.old_job_id;proof.restart_command_id=y->s.restart_command_id;
    proof.new_floor_capture_id=y->s.new_floor_capture_id;
    proof.source_capture_id=capture;proof.source_start_ns=start;proof.source_prefix=prefix;
    p->last_now=now;terminal(p,now,NG2_REASON_LIMIT);
    p->campaign=proof;return 1;
}
static int restart_yield_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2RestartYield *y=&p->restart_yield;
    if(!y->s.pending)return 0;
    if(!y->pause)y->s.permitted=0;
    cycle_scene(p,scene,id,start,end,prefix);
    /* A positive/failure retires budget permission, but ordinary finish may
     * still have its one ACK-known holding PAUSE to observe. Closing that
     * exact command grants neither another input nor a budget handoff. */
    if(p->s.input_state==3&&p->command.kind==NG2_ACTION_PAUSE
        &&prefix==p->command.id&&start>=p->ack_ns
        &&((y->pause&&p->command.id==y->pause)
            ||(!y->pause&&y->s.invalid&&p->finish_requested))){
        if(scene->state==NG2_FLOOR&&scene->goods!=NG2_GOODS_UNKNOWN){
            y->required|=scene->goods==NG2_GOODS_PARTIAL?1:2;
            if(y->required&~y->done)restart_yield_invalidate(p);
        }
        if(scene->state==NG2_PAUSE){
            event(p)->observed_capture_id=id;end_visual_wait(p);p->cycle.pause_capture_id=id;
            if(y->pause&&restart_yield_basis(p,now)&&!(y->required&~y->done)&&!p->cycle.pending){
                p->handoff.pause_capture_id=id;terminal(p,now,NG2_REASON_LIMIT);
            }else{restart_yield_invalidate(p);terminal(p,now,p->s.reason?p->s.reason:NG2_REASON_CAPTURE);}
        }
        return 1;
    }
    if(prefix!=y->s.restart_command_id||scene->state==NG2_PAUSE)restart_yield_invalidate(p);
    if(scene->state==NG2_FLOOR&&scene->goods!=NG2_GOODS_UNKNOWN)
        y->required|=scene->goods==NG2_GOODS_PARTIAL?1:2;
    return 1;
}
static int cycle_new_item_protects(const NG2Scene *before,const NG2Scene *after,int x,int y){
    int d;
    for(d=0;d<5;++d)
        if(tile(before,x+dx[d],y+dy[d])!=NG2_TILE_ITEM
            &&tile(after,x+dx[d],y+dy[d])==NG2_TILE_ITEM)return 1;
    return 0;
}
/* Newly visible top duplicates invalidate the old partial data result. Each
 * cell is directly supported by its unchanged, protected lower projection;
 * only its explained halo may grow. This never grants old MOVE authority. */
static int cycle_top_projection_growth(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_anchor;int i,x,left=12,right=-12,items=0;
    if(p->cycle_partial_rebind_used||!cycle_opened_partial(p,NG2_UP))return 0;
    if(cycle_partial_top_roles(p,scene)&(CYCLE_TOP_ITEM|CYCLE_TOP_DATA))return 1;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],cx=i%23-11,cy=i/23-5;
        if(old!=next){
            if(cy!=-5||next!=NG2_TILE_ITEM
                ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT))return 0;
            if(cx<left)left=cx;
            if(cx>right)right=cx;
            ++items;
        }
        if(a->protected_cells[i]&&!scene->protected_cells[i])return 0;
        if(a->protected_cells[i]!=scene->protected_cells[i]
            &&!cycle_new_item_protects(a,scene,cx,cy))return 0;
    }
    if(items<3)return 0;
    for(x=left;x<=right;++x)
        if(tile(scene,x,-5)!=NG2_TILE_ITEM||!protected_at(scene,x,-5)
            ||tile(a,x,-4)!=NG2_TILE_ITEM||tile(scene,x,-4)!=NG2_TILE_ITEM
            ||!protected_at(a,x,-4)||!protected_at(scene,x,-4))return 0;
    return 1;
}
/* Newly exposed merchandise invalidates the old partial result. A strict
 * stationary proof may bind a fresh data job, never continue the old MOVE.
 * The old observation horizon and one-use allowance survive every bind. */
static int cycle_rebind_exposed_partial(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t prefix,uint64_t commit){
    const NG2Scene *a=&p->cycle_anchor;NG2Decision latest;NG2Motion still;int i,d,new_items=0;
    uint64_t horizon=p->cycle.continuation_deadline_ns;
    if(p->cycle_partial_rebind_used||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE||p->cycle.pending
        ||p->s.input_state||p->cycle_partial_credit||p->cycle_framing_credit||p->cycle.candidate_latched
        ||p->finish_requested||p->s.terminal||!p->cycle.capture_id||id<=p->cycle.capture_id
        ||prefix!=p->cycle.prefix||prefix!=p->s.last_completed_id||commit>horizon
        ||a->state!=NG2_FLOOR||a->goods!=NG2_GOODS_PARTIAL
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_PARTIAL||!p->cycle_choice_valid
        ||!cycle_partial_choice(p,scene,&latest)||!same_choice(&p->cycle_choice,&latest))return 0;
    d=latest.direction;
    if(!cycle_opened_partial(p,d))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],x=i%23-11,y=i/23-5;
        int protection=a->protected_cells[i]!=scene->protected_cells[i];
        if(old==NG2_TILE_ITEM&&next!=NG2_TILE_ITEM)return 0;
        if(a->protected_cells[i]&&!scene->protected_cells[i])return 0;
        if(old!=next){
            if(next!=NG2_TILE_ITEM||(old!=NG2_TILE_FLOOR&&old!=NG2_TILE_GOLD)
                ||!scene->protected_cells[i])return 0;
            ++new_items;
        }
        if(old!=next||protection){
            if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))return 0;
            if(protection&&!cycle_new_item_protects(a,scene,x,y))return 0;
        }
    }
    if(!new_items||!ng2_motion(a,scene,d,&still)||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    p->cycle_partial_rebind_used=1;
    cycle_latch(p,scene,commit);cycle_bind(p,scene,id,start,prefix);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,horizon);
    return 1;
}
/* A material change outside the fixed MOVE footprint retires the old
 * PARTIAL result rather than widening its static proof. The new immutable
 * source needs its own normal classification and another independent static
 * comparison. Repeated data refreshes keep the original continuation horizon;
 * they do not consume the separate one-use newly-exposed-ITEM allowance. A
 * remote goods halo may overlap a newly observed impassable GOLD wall after
 * the same opening ACK; no protected walking surface or ITEM may change. */
static int cycle_rebind_composed_upper(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    const NG2Scene *a=&p->cycle_anchor;NG2Decision latest;NG2Motion still={0};
    uint64_t parent=p->cycle.continuation_deadline_ns,hold=p->cycle.hold_started_ns,sync=p->cycle_sync_deadline;
    int i,d,new_gold=0,shielded=0;
    if(p->upper_partial_refresh.used||p->cycle_retry_used>=2||p->cycle_retry_only
        ||p->cycle_current_active||p->cycle.pending||!p->cycle_refresh_safe
        ||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE||p->cycle_partial_credit||p->cycle_framing_credit
        ||p->cycle_full_framing||p->cycle_full_spent||p->entry.active||p->lower.active||p->upper.active
        ||!p->cycle.partial||p->cycle.full_seen||p->cycle.candidate_latched||p->cycle_restart_unproved
        ||p->cycle_pause_attempted||p->cycle_storage_error||p->finish_requested||p->s.terminal||p->s.input_state
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE||!p->cycle_choice_valid
        ||!p->cycle.capture_id||id<=p->cycle.capture_id||start<=p->cycle.capture_start_ns
        ||start<p->cycle.release_after_ns||now<end||now>start+CYCLE_CAPTURE_BUDGET
        ||!parent||now>parent||prefix!=p->cycle.prefix||prefix!=p->s.last_completed_id
        ||prefix!=p->last_observed_prefix||a->state!=NG2_FLOOR||a->goods!=NG2_GOODS_PARTIAL
        ||!cycle_exact_item_protection(a)||!cycle_partial_choice(p,scene,&latest)
        ||!same_choice(&p->cycle_choice,&latest))return 0;
    d=latest.direction;
    if(!cycle_opened_partial(p,d)||upper_side_variant(scene,d)!=2)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],x=i%23-11,y=i/23-5;
        int near=(abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1);
        if(a->protected_cells[i]!=scene->protected_cells[i]||(old==NG2_TILE_GOLD&&next!=old)
            ||((old==NG2_TILE_ITEM)!=(next==NG2_TILE_ITEM)))return 0;
        if(old==next)continue;
        if(cycle_partial_quiet_cell(p,a,scene,d,i)){
            if(near)shielded=1;
            continue;
        }
        if(near||a->protected_cells[i]||next!=NG2_TILE_GOLD
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_DOOR))return 0;
        ++new_gold;
    }
    if(!new_gold||!shielded||!ng2_motion(a,scene,d,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    p->upper_partial_refresh.used=1;p->upper_partial_refresh.owner_start=p->s.started_ns;
    p->upper_partial_refresh.level=p->cycle.level_id;p->upper_partial_refresh.opening=prefix;
    p->upper_partial_refresh.job=p->cycle.job_id;p->upper_partial_refresh.capture=p->cycle.capture_id;
    p->upper_partial_refresh.prefix=prefix;p->upper_partial_refresh.parent=parent;
    p->upper_partial_refresh.hold=hold;p->upper_partial_refresh.sync=sync;
    ++p->cycle_retry_used;
    if(p->s.last_capture_id!=id)cycle_scene(p,scene,id,start,end,prefix);
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->cycle.hold_started_ns=hold;p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,sync);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,parent);
    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,p->cycle.continuation_deadline_ns);
    return 1;
}
static int cycle_rebind_changed_partial(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t commit){
    const NG2Scene *a=&p->cycle_anchor;NG2Decision latest;NG2Motion still;NG2ControllerEvent *e=event(p);
    uint64_t horizon=p->cycle.continuation_deadline_ns;int i,d,changed=0,top_growth;
    if(cycle_rebind_composed_upper(p,scene,id,start,end,prefix,commit))return 1;
    if(!p->cycle_refresh_safe||p->cycle.pending||p->cycle.candidate_latched||p->cycle.full_seen
        ||p->cycle_pause_attempted||p->cycle_storage_error||p->cycle_restart_unproved
        ||p->cycle_framing_credit||p->cycle_full_framing||p->cycle_full_spent||p->entry.active
        ||p->finish_requested||p->s.terminal||!p->cycle.capture_id||id<=p->cycle.capture_id
        ||start<p->cycle.release_after_ns||prefix!=p->cycle.prefix||prefix!=p->s.last_completed_id
        ||!horizon||commit>horizon||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||!p->cycle.partial||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||!((p->cycle.state==NG2_CYCLE_OBSERVE_MORE&&!p->cycle_partial_credit)
            ||(p->cycle.state==NG2_CYCLE_SEARCH&&p->cycle_partial_credit))
        ||(p->s.input_state!=0&&p->s.input_state!=1)
        ||(p->s.input_state==1&&(!p->cycle_partial_credit||p->command.kind!=NG2_ACTION_MOVE
            ||!e||e->begin_ns||e->outcome))
        ||a->state!=NG2_FLOOR||a->goods!=NG2_GOODS_PARTIAL
        ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_PARTIAL||!p->cycle_choice_valid
        ||!cycle_partial_choice(p,scene,&latest)||!same_choice(&p->cycle_choice,&latest))return 0;
    d=latest.direction;
    top_growth=cycle_top_projection_growth(p,scene);
    if(top_growth)changed=1;
    else for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],x=i%23-11,y=i/23-5;
        int observed_wall=next==NG2_TILE_GOLD
            &&(old==NG2_TILE_UNKNOWN||old==NG2_TILE_DOOR)&&cycle_opened_partial(p,d);
        if(a->protected_cells[i]!=scene->protected_cells[i]
            ||(old==NG2_TILE_GOLD&&next!=NG2_TILE_GOLD)
            ||((old==NG2_TILE_ITEM)!=(next==NG2_TILE_ITEM)))return 0;
        if(old==next)continue;
        if((a->protected_cells[i]&&!observed_wall)||(abs(x)<=1&&abs(y)<=1)
            ||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1))return 0;
        changed=1;
    }
    if(!changed||!ng2_motion(a,scene,d,&still)||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    if(top_growth)p->cycle_partial_rebind_used=1;
    if(p->s.last_capture_id!=id)cycle_scene(p,scene,id,start,end,prefix);
    cycle_latch(p,scene,commit);cycle_bind(p,scene,id,start,prefix);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,horizon);
    return 1;
}
static void entry_box(int box[4],int left,int top,int right,int bottom){
    if(left<box[0])box[0]=left;
    if(top<box[1])box[1]=top;
    if(right>box[2])box[2]=right;
    if(bottom>box[3])box[3]=bottom;
}
static void entry_item_box(int box[4],int x,int y){
    int cx=448+36*x,cy=207+36*y;entry_box(box,cx-78,cy-86,cx+78,cy+61);
}
static int entry_potential(const NG2Scene *scene,const NG2RingResult *result,int box[4]){
    int i,k,r;box[0]=896;box[1]=414;box[2]=box[3]=0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5;
        if(scene->tiles[i]==NG2_TILE_ITEM)entry_item_box(box,x,y);
        if(scene->protected_cells[i])for(k=0;k<5;++k)entry_item_box(box,x+dx[k],y+dy[k]);
    }
    for(r=0;r<result->row_count;++r){
        const NG2RingRow *row=&result->rows[r];
        if(row->left<0||row->left>=896||row->sy<0||row->sy>=414)return 0;
        entry_box(box,row->left-112,row->sy-20,row->left+184,row->sy+52);
        for(k=0;k<3;++k){
            const NG2RingSlot *v=&row->slots[k];
            if(v->cx<0||v->cx>=896||v->sy<0||v->sy>=414)return 0;
            entry_box(box,v->cx-60,v->sy-32,v->cx+60,v->sy+115);
        }
    }
    for(k=0;k<result->partial_count;++k){
        const NG2RingSlot *v=&result->partial[k];
        if(v->cx<0||v->cx>=896||v->sy<0||v->sy>=414)return 0;
        entry_box(box,v->cx-60,v->sy-32,v->cx+60,v->sy+115);
    }
    return box[0]<box[2]&&box[1]<box[3];
}
/* UP maps old pixels downward36px. Pause's visible preimage y0..9 was
 * already old pause HUD; offscreen/HUD possibilities stay unknown. */
static int entry_preserves(const int box[4],int shifted){
    return box[0]>=143&&box[2]<=663&&box[1]<box[3]&&box[3]+shifted+36<=315;
}
static int entry_local(const NG2Controller *p,const NG2Scene *scene){
    int side=p->entry.side,n=p->entry.moves;
    return p->entry.valid&&p->entry.level==p->cycle.level_id
        &&scene->state==NG2_FLOOR&&(scene->goods==NG2_GOODS_PARTIAL||scene->goods==NG2_GOODS_VISIBLE)
        &&actual_gold(scene)&&cycle_exact_item_protection(scene)
        &&tile(scene,0,0)==NG2_TILE_FLOOR&&!protected_at(scene,0,0)
        &&tile(scene,0,-1)==NG2_TILE_FLOOR&&!protected_at(scene,0,-1)
        &&tile(scene,side,-3+n)==NG2_TILE_GOLD&&tile(scene,side,-2+n)==NG2_TILE_GOLD
        &&tile(scene,side,-1+n)==NG2_TILE_GOLD&&tile(scene,-side,-1+n)==NG2_TILE_GOLD;
}
static int entry_identity(const NG2Controller *p){
    size_t i;
    if(!p->entry.valid||p->entry.level!=p->cycle.level_id||p->entry.inputs!=p->entry.moves
        ||p->cycle.job_id!=p->entry.job||p->cycle.capture_id!=p->entry.capture
        ||p->cycle.prefix!=p->entry.prefix||p->s.last_completed_id!=p->entry.prefix
        ||p->last_observed_prefix!=p->entry.prefix)return 0;
    if(!p->entry.inputs)return p->entry.prefix==p->entry.opening&&last_ack_opened_gate(p,NG2_UP);
    if(p->entry.prefix!=p->entry.last_move)return 0;
    for(i=0;i<p->event_count;++i){
        const NG2ControllerEvent *e=&p->events[i];
        if(e->command.id==p->entry.last_move)return e->command.kind==NG2_ACTION_MOVE
            &&e->command.direction==NG2_UP&&e->outcome==2&&e->motion==NG2_MOVED&&!e->dx&&e->dy== -1
            &&e->observed_capture_id==p->entry.moved_capture;
    }
    return 0;
}
static int entry_result_safe(const NG2RingResult *result){
    int r,k;
    if(result->outcome!=NG2_RING_UNKNOWN||result->coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||(result->partial_safe_no_positive&&!result->row_count&&!result->partial_count))return 0;
    for(r=0;r<result->row_count;++r)for(k=0;k<3;++k)
        if(!cycle_binary_no_positive(&result->rows[r].slots[k])
            ||result->rows[r].slots[k].icon_upper_bound>=.80)return 0;
    for(k=0;k<result->partial_count;++k)if(!cycle_binary_no_positive(&result->partial[k])
        ||result->partial[k].icon_upper_bound>=.80)return 0;
    return 1;
}
/* An assessment may retire only its own still-unbegun PAUSE reservation.
 * The cached MOVE history was already captured at FULL bind, before reserve
 * overwrote before/command; a retired PAUSE never supplies that history. */
static int cycle_data_prepared_pause(const NG2Controller *p){
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    return p->s.input_state==1&&e&&p->command.kind==NG2_ACTION_PAUSE
        &&e->command.id==p->command.id&&e->command.kind==NG2_ACTION_PAUSE
        &&!e->begin_ns&&!e->end_ns&&!e->outcome
        &&e->command.source_capture_id==p->command.source_capture_id
        &&p->command.source_capture_id==p->cycle.capture_id
        &&p->cycle.pause_source_capture_id==p->cycle.capture_id
        &&p->s.last_completed_id==p->cycle.prefix&&p->last_observed_prefix==p->cycle.prefix;
}
static void cycle_data_yield_pause(NG2Controller *p,uint64_t now){
    if(!cycle_data_prepared_pause(p)
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->entry.active||p->lower.active||p->upper.active||p->cycle.partial||!p->cycle.full_seen
        ||p->cycle.candidate_latched||p->cycle_restart_unproved||p->cycle_storage_error
        ||p->finish_requested||p->s.terminal||p->restart_yield.s.pending
        ||p->cycle_full_spent||p->cycle_full_framing||p->cycle_full_data_active
        ||p->cycle_retry_used>=2||(p->cycle_retry_blocked&1)
        ||now>p->cycle.continuation_deadline_ns||!cycle_retry_source_qualified(&p->cycle_anchor)
        ||(p->cycle_retry_only&&!p->cycle_retry_data))return;
    not_sent(p,now,NG2_REASON_GOODS);p->cycle_pause_attempted=0;p->cycle.pause_source_capture_id=0;
}
static int cycle_data_retry_wait(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    if(result->status!=NG2_RING_OK||!entry_result_safe(result)
        ||(!result->row_count&&!result->partial_count)||cycle_result_positive_hint(result)!=0
        ||(p->cycle_retry_only&&!p->cycle_retry_data)||!cycle_retry_basis(p,now,1))return 0;
    if(!p->cycle_retry_only){
        p->cycle_retry_only=p->cycle_retry_data=1;p->cycle_retry_parent=p->cycle.continuation_deadline_ns;
        p->cycle_retry_hold=p->cycle.hold_started_ns;p->cycle_retry_source=p->cycle_anchor;
        p->cycle_retry_prefix=p->cycle.prefix;p->cycle_retry_level=p->cycle.level_id;
    }
    /* Only a transient unclassified frame may be forgotten after an on-time
     * safe normal result. Hard classified/source invalidation is sticky. */
    p->cycle_retry_blocked&=1;p->cycle_retry_waiting=1;p->cycle.pending=0;
    p->cycle.status=NG2_RING_OK;p->cycle.outcome=NG2_RING_UNKNOWN;
    p->cycle.assessment_ns=now;p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;
    if(p->cycle_queued_valid&&p->cycle.queued_prefix==p->cycle_retry_prefix
        &&now<=p->cycle.queued_capture_start_ns+CYCLE_CAPTURE_BUDGET
        &&cycle_retry_data_relation(p,&p->cycle_queued_scene)){
        NG2Scene queued=p->cycle_queued_scene;
        uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,prefix=p->cycle.queued_prefix;
        cycle_retry_bind(p,&queued,id,start,prefix,now);
    }
    return 1;
}
/* A data-only replacement after a hard old-source rejection owns a separate
 * immutable epoch. Runtime may queue it inside the old callback, but its
 * existing drain-token fence must precede actual worker dispatch and UI. */
static void cycle_current_bind(NG2Controller *p,const NG2Scene *source,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now,int partial){
    uint64_t hold=p->cycle.hold_started_ns,parent=p->cycle.continuation_deadline_ns;
    uint64_t sync=p->cycle_sync_deadline,ordinal=0;size_t samples=p->sample_count,i;
    for(i=0;i<p->event_count;++i)if(p->events[i].command.kind==NG2_ACTION_MOVE
        &&p->events[i].command.ordinal>ordinal)ordinal=p->events[i].command.ordinal;
    /* Callers qualify the exact old definitely-unbegun ticket before any
     * identity changes. No begun MOVE or ambiguous synth reaches this bind. */
    if(p->s.input_state==1)not_sent(p,now,NG2_REASON_GOODS);
    p->cycle_current_partial=partial;
    if(partial==1)memcpy(p->cycle_current_potential,p->cycle_anchor.protected_cells,NG2_TILE_COUNT);
    else memset(p->cycle_current_potential,0,NG2_TILE_COUNT);
    ++p->cycle_retry_used;p->cycle_current_used=1;p->cycle_current_active=1;
    p->cycle_current_invalid=p->cycle_current_proofs=0;
    p->cycle_current_source=*source;p->cycle_current_id=id;p->cycle_current_start=start;
    p->cycle_current_end=end;p->cycle_current_prefix=prefix;p->cycle_current_level=p->cycle.level_id;
    p->cycle_current_parent=parent;p->cycle_current_sync=sync;p->cycle_current_ordinal=ordinal;
    p->cycle_current_proof_id=p->cycle_current_proof_end=0;
    cycle_latch(p,source,now);cycle_bind(p,source,id,start,prefix);
    p->cycle_current_job=p->cycle.job_id;p->cycle_up_history=0;
    p->cycle.hold_started_ns=hold;
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,parent);
    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,p->cycle.continuation_deadline_ns);
    p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,sync);
    clear_slots(p);clear_model(p);p->sample_count=samples;
    p->proof_capture_id=p->proof_deadline=0;p->preparation_epoch=0;
}
/* A latest FULL image may be classified without declaring its old comparison
 * zero. The exact observed offer projection protects unseen/extra goods and
 * the player's five-cell neighborhood; this predicate grants DATA only. */
static int cycle_current_data_scene(const NG2Scene *scene){
    NG2RingRow row;int i,count=0,left=12,ay=6;
    if(!cycle_retry_source_qualified(scene))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM){
        int x=i%23-11,y=i/23-5;
        if(ay!=6&&ay!=y)return 0;
        ay=y;if(x<left)left=x;++count;
    }
    if(count!=3)return 0;
    memset(&row,0,sizeof(row));row.left=448+36*left;row.sy=159+36*ay;
    return cycle_observed_shop_scene(scene,&row,-1);
}
static int cycle_current_data_pair(const NG2Scene *a,const NG2Scene *b){
    int i;
    if(!cycle_current_data_scene(a)||!cycle_current_data_scene(b)
        ||a->gold_state!=b->gold_state)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=b->tiles[i],x=i%23-11,y=i/23-5;
        if(a->protected_cells[i]!=b->protected_cells[i])return 0;
        if(old==latest)continue;
        if(a->protected_cells[i]||abs(x)+abs(y)<=1
            ||(old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_STONE&&old!=NG2_TILE_DIRT)
            ||(latest!=NG2_TILE_UNKNOWN&&latest!=NG2_TILE_FLOOR&&latest!=NG2_TILE_STONE
                &&latest!=NG2_TILE_DIRT&&latest!=NG2_TILE_GOLD))return 0;
    }
    return 1;
}
static int cycle_current_data_unissued(const NG2Controller *p){
    return p->cycle_full_spent&&p->cycle_full_framing==1&&p->cycle_full_source_valid
        &&!p->cycle_full_data_active&&(p->cycle_full_choice.direction==NG2_LEFT
            ||p->cycle_full_choice.direction==NG2_RIGHT)
        &&p->cycle_full_source_id==p->cycle.capture_id
        &&p->cycle_full_source_start==p->cycle.capture_start_ns
        &&p->cycle_full_source_prefix==p->cycle.prefix
        &&p->cycle_full_parent==p->cycle.continuation_deadline_ns
        &&!memcmp(&p->cycle_full_source,&p->cycle_anchor,sizeof(p->cycle_anchor))
        &&p->cycle.status==NG2_RING_OK&&p->cycle.outcome==NG2_RING_UNKNOWN
        &&p->cycle.coverage==NG2_RING_COVERAGE_INCOMPLETE;
}
static int cycle_current_data_start(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    NG2Scene source;int unissued=cycle_current_data_unissued(p);
    if(!p->restart_yield.s.enabled||p->cycle_current_used||p->cycle_current_active||p->cycle.pending
        ||p->cycle_retry_used>=2||p->cycle.partial||!p->cycle.full_seen
        ||(p->cycle_retry_only&&(p->cycle_retry_prefix!=p->cycle.prefix
            ||p->cycle_retry_level!=p->cycle.level_id
            ||p->cycle.continuation_deadline_ns>p->cycle_retry_parent))
        ||((p->cycle_full_spent||p->cycle_full_framing)&&!unissued)||p->cycle_full_data_active
        ||p->entry.active||p->lower.active||p->upper.active||p->restart_yield.s.pending
        ||p->cycle.candidate_latched||p->cycle_restart_unproved||p->cycle_storage_error
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->finish_requested||p->s.terminal||p->s.input_state>1
        ||(p->s.input_state==1&&!cycle_data_prepared_pause(p))
        ||(p->cycle_pause_attempted&&!cycle_data_prepared_pause(p))
        ||p->s.last_capture_id<=p->cycle.capture_id||p->seen_id!=p->s.last_capture_id
        ||p->seen_start!=p->s.last_capture_start_ns||p->seen_end!=p->s.last_capture_end_ns
        ||p->s.last_capture_start_ns<=p->cycle.capture_start_ns
        ||p->last_observed_prefix!=p->cycle.prefix||p->s.last_completed_id!=p->cycle.prefix
        ||now<p->s.last_capture_end_ns||now>p->s.last_capture_start_ns+CYCLE_CAPTURE_BUDGET
        ||!p->cycle.continuation_deadline_ns||now>=p->cycle.continuation_deadline_ns
        ||!cycle_current_data_pair(&p->cycle_anchor,&p->scene))return 0;
    if(result){
        if(!(p->cycle_retry_blocked&1)||cycle_result_positive_hint(result)!=0
            ||(result->outcome!=NG2_RING_NEGATIVE
                &&(!entry_result_safe(result)||(!result->row_count&&!result->partial_count))))return 0;
    }else if((!unissued&&(!p->cycle_retry_only||!p->cycle_retry_data||!p->cycle_retry_waiting))
        ||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE||p->cycle.status!=NG2_RING_OK
        ||p->cycle.outcome!=NG2_RING_UNKNOWN)return 0;
    source=p->scene;
    cycle_current_bind(p,&source,p->s.last_capture_id,p->s.last_capture_start_ns,
        p->s.last_capture_end_ns,p->cycle.prefix,now,2);
    /* Only the retired old source carried these flags. New mode2 has its own
     * immutable job and sticky validation, and never grants UP credit. */
    p->cycle_retry_only=p->cycle_retry_data=p->cycle_retry_waiting=p->cycle_retry_blocked=0;
    p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
    return 1;
}
static int cycle_current_start(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    uint64_t id,start,end,prefix;
    NG2Scene source;
    if(!p->restart_yield.s.enabled||p->cycle_current_used||p->cycle_current_active||!(p->cycle_retry_blocked&1)
        ||p->cycle_retry_only||p->cycle_full_spent||p->cycle_full_framing||p->cycle_full_data_active
        ||p->cycle_retry_used>=2||p->cycle.partial||!p->cycle.full_seen
        ||p->entry.active||p->lower.active||p->upper.active||p->restart_yield.s.pending
        ||p->cycle.candidate_latched||p->cycle_restart_unproved||p->cycle_storage_error
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->finish_requested||p->s.terminal||p->s.input_state>1
        ||(p->s.input_state==1&&!cycle_data_prepared_pause(p))
        ||(p->cycle_pause_attempted&&!cycle_data_prepared_pause(p))
        ||!entry_result_safe(result)||cycle_result_positive_hint(result)!=0
        ||!cycle_current_up_layout(&p->cycle_anchor,result)
        ||!cycle_full_up_local(&p->scene)||p->s.last_capture_id<=p->cycle.capture_id
        ||p->seen_id!=p->s.last_capture_id||p->seen_start!=p->s.last_capture_start_ns
        ||p->seen_end!=p->s.last_capture_end_ns
        ||p->s.last_capture_start_ns<=p->cycle.capture_start_ns
        ||p->last_observed_prefix!=p->cycle.prefix||p->s.last_completed_id!=p->cycle.prefix
        ||now<p->s.last_capture_end_ns||now>p->s.last_capture_start_ns+CYCLE_CAPTURE_BUDGET
        ||!p->cycle.continuation_deadline_ns||now>p->cycle.continuation_deadline_ns)return 0;
    source=p->scene;id=p->s.last_capture_id;start=p->s.last_capture_start_ns;
    end=p->s.last_capture_end_ns;prefix=p->cycle.prefix;
    /* Check and retire against the OLD capture before any identity changes.
     * Begun/ACK/unknown input is never reinterpreted as an unsent PAUSE. */
    cycle_current_bind(p,&source,id,start,end,prefix,now,0);
    return 1;
}
/* The original empty framing source may expose a stable lower projection
 * after its clipped top duplicate disappears. This is a new DATA source,
 * never an alias exception for the invalid old MOVE/negative identity. */
static int cycle_current_partial_transition(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_anchor;NG2Decision latest;NG2Motion still={0};
    int i,x,left=12,right=-12,items=0;
    if(!cycle_framing_scene(a)||!cycle_corridor_scene(a)||cycle_framing_scene(scene)
        ||!cycle_corridor_scene(scene)||a->gold_state!=scene->gold_state
        ||!cycle_exact_item_protection(a)||!cycle_exact_item_protection(scene)
        ||!cycle_opened_partial(p,NG2_UP)||!cycle_partial_choice(p,scene,&latest)
        ||!same_choice(&p->cycle_choice,&latest))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],y=i/23-5;
        if(old==NG2_TILE_ITEM&&y!=-5&&y!=-4)return 0;
        if(next==NG2_TILE_ITEM&&y!=-4)return 0;
        if(y==-4){
            if((old==NG2_TILE_ITEM)!=(next==NG2_TILE_ITEM))return 0;
            if(old==NG2_TILE_ITEM){x=i%23-11;if(x<left)left=x;if(x>right)right=x;++items;}
        }
    }
    if(items<3||right-left+1!=items||left<=-11||right>=11)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],x=i%23-11,y=i/23-5;
        int top=y==-5&&x>=left&&x<=right,margin=y==-5&&(x==left-1||x==right+1);
        if(top){
            if(old!=NG2_TILE_ITEM||!a->protected_cells[i]||!scene->protected_cells[i]
                ||(next!=NG2_TILE_UNKNOWN&&next!=NG2_TILE_FLOOR&&next!=NG2_TILE_DIRT&&next!=NG2_TILE_GOLD))return 0;
            if(next==NG2_TILE_GOLD&&(tile(scene,x,-3)!=NG2_TILE_GOLD
                ||tile(scene,x,-2)!=NG2_TILE_GOLD||tile(scene,x,-1)!=NG2_TILE_GOLD))return 0;
        }else{
            if(old!=next)return 0;
            if(a->protected_cells[i]!=scene->protected_cells[i]
                &&!(margin&&a->protected_cells[i]&&!scene->protected_cells[i]))return 0;
        }
    }
    /* Keep the old potential mask in both actual stepping crosses. */
    for(i=0;i<5;++i){
        if(protected_route_cell(a,scene,dx[i],dy[i])
            ||protected_route_cell(scene,a,dx[i],dy[i])
            ||protected_route_cell(a,scene,dx[i],dy[i]-1)
            ||protected_route_cell(scene,a,dx[i],dy[i]-1))return 0;
    }
    return ng2_motion(a,scene,NG2_UP,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
}
static int cycle_current_partial_start(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Scene source;const NG2ControllerEvent *e=event(p);
    int credited=p->cycle_partial_credit&&p->cycle.state==NG2_CYCLE_SEARCH;
    int unsent=credited&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&p->command.direction==NG2_UP&&p->command.source_capture_id>=p->cycle.capture_id
        &&p->s.current_command_id==p->command.id&&e
        &&!memcmp(&e->command,&p->command,sizeof(p->command))&&!e->begin_ns&&!e->outcome;
    if(!p->restart_yield.s.enabled||p->cycle_current_used||p->cycle_current_active
        ||p->cycle_retry_only||p->cycle_retry_used>=2||p->cycle_full_spent||p->cycle_full_framing
        ||p->cycle_full_data_active||p->entry.active||p->lower.active||p->upper.active
        ||!p->cycle_framing_credit||p->cycle.pending
        ||(!credited&&(p->cycle_partial_credit||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE))
        ||!p->cycle.partial||p->cycle.full_seen
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE||p->cycle.candidate_latched
        ||p->cycle_restart_unproved||p->cycle_storage_error||p->restart_yield.s.pending
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->finish_requested||p->s.terminal||p->s.input_state>1
        ||(p->s.input_state==1&&!unsent&&!cycle_data_prepared_pause(p))
        ||(p->cycle_pause_attempted&&!cycle_data_prepared_pause(p))
        ||id<=p->cycle.capture_id||start<p->cycle.release_after_ns||start<=p->cycle.capture_start_ns
        ||prefix!=p->cycle.prefix||prefix!=p->s.last_completed_id||prefix!=p->last_observed_prefix
        ||p->seen_id!=id||p->seen_start!=start||p->seen_end!=end
        ||now<end||now>start+CYCLE_CAPTURE_BUDGET||now>p->cycle.continuation_deadline_ns
        ||!cycle_current_partial_transition(p,scene))return 0;
    source=*scene;p->cycle_retry_blocked|=1; /* The old hard rejection stays retired. */
    if(p->s.last_capture_id!=id)cycle_scene(p,scene,id,start,end,prefix);
    cycle_current_bind(p,&source,id,start,end,prefix,now,1);return 1;
}
static int cycle_current_identity(const NG2Controller *p){
    return p->cycle_current_active&&!p->cycle_current_invalid
        &&p->cycle.job_id==p->cycle_current_job&&p->cycle.level_id==p->cycle_current_level
        &&p->cycle.capture_id==p->cycle_current_id&&p->cycle.prefix==p->cycle_current_prefix
        &&p->s.last_completed_id==p->cycle_current_prefix
        &&p->last_observed_prefix==p->cycle_current_prefix
        &&p->cycle.continuation_deadline_ns<=p->cycle_current_parent
        &&p->cycle_sync_deadline<=p->cycle_current_sync;
}
/* The independent current source can regain only the old top duplicates,
 * each supported by its unchanged lower ITEM and original potential mask.
 * This changes no anchor, result, DATA count or one-use observation budget.
 * Every accepted image still needs normal strict zero directly to that anchor. */
static int cycle_current_partial_top_relation(const NG2Controller *p,const NG2Scene *scene){
    const NG2Scene *a=&p->cycle_current_source;
    int i,left=12,right=-12,count=0,changed=0;
    if(!p->cycle_current_partial||!cycle_current_partial_local(p,a)
        ||!cycle_current_partial_local(p,scene))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(a->tiles[i]==NG2_TILE_ITEM){
        int x=i%23-11,y=i/23-5;
        if(y!=-4)return 0;
        if(x<left)left=x;
        if(x>right)right=x;
        ++count;
    }
    if(count<3||right-left+1!=count||left<=-11||right>=11)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],latest=scene->tiles[i],x=i%23-11,y=i/23-5;
        int top=y==-5&&x>=left&&x<=right;
        int margin=y==-5&&(x==left-1||x==right+1);
        if(scene->protected_cells[i]&&!p->cycle_current_potential[i])return 0;
        if(top){
            if((old!=NG2_TILE_UNKNOWN&&old!=NG2_TILE_FLOOR&&old!=NG2_TILE_DIRT&&old!=NG2_TILE_GOLD)
                ||(latest!=old&&latest!=NG2_TILE_ITEM)||!a->protected_cells[i]
                ||!scene->protected_cells[i]||!p->cycle_current_potential[i]
                ||tile(a,x,-4)!=NG2_TILE_ITEM||tile(scene,x,-4)!=NG2_TILE_ITEM)return 0;
            if(old==NG2_TILE_GOLD&&(tile(a,x,-3)!=NG2_TILE_GOLD
                ||tile(a,x,-2)!=NG2_TILE_GOLD||tile(a,x,-1)!=NG2_TILE_GOLD))return 0;
            changed|=old!=latest;
        }else{
            if(old!=latest)return 0;
            if(a->protected_cells[i]!=scene->protected_cells[i]
                &&!(margin&&!a->protected_cells[i]&&scene->protected_cells[i]
                    &&cycle_new_item_protects(a,scene,x,y)))return 0;
        }
    }
    return changed;
}
static int cycle_current_relation(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    const NG2Scene *a=&p->cycle_current_source;
    if(p->cycle_current_partial==2)
        return cycle_current_identity(p)&&cycle_current_data_pair(a,scene);
    return cycle_current_identity(p)&&scene->gold_state==a->gold_state
        &&(p->cycle_current_partial?cycle_current_partial_local(p,scene):cycle_full_up_local(scene))
        &&((!memcmp(a->tiles,scene->tiles,NG2_TILE_COUNT)
            &&!memcmp(a->protected_cells,scene->protected_cells,NG2_TILE_COUNT))
            ||cycle_current_partial_top_relation(p,scene))
        &&ng2_motion(a,scene,NG2_UP,motion)&&motion->kind==NG2_BLOCKED&&!motion->dx&&!motion->dy;
}
/* A pending FULL worker may keep its immutable DATA authority even when a
 * distant material label prevents the stronger observation-MOVE proof.
 * Downgrade only: no source/job/budget/clock changes, no UP qualification. */
static int cycle_current_keep_data(NG2Controller *p,const NG2Scene *scene,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    if(p->cycle_current_active!=1||p->cycle_current_partial!=0||!p->cycle.pending
        ||p->cycle_current_invalid||p->cycle_current_proofs||!p->cycle_current_used
        ||p->cycle_retry_used<1||p->cycle_retry_used>2||p->s.input_state
        ||p->cycle.state!=NG2_CYCLE_ASSESS||!p->cycle.worker_started_ns
        ||p->cycle.partial||!p->cycle.full_seen||p->cycle.candidate_latched
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->cycle_pause_attempted||p->cycle_storage_error||p->cycle_restart_unproved
        ||p->entry.active||p->lower.active||p->upper.active
        ||p->finish_requested||p->s.terminal||!cycle_current_identity(p)
        ||prefix!=p->cycle_current_prefix||prefix!=p->s.last_completed_id
        ||prefix!=p->last_observed_prefix||start<p->cycle_current_end
        ||start>end||end>now||now<p->cycle.worker_started_ns
        ||now>p->cycle.deadline_ns||now>p->cycle_current_parent
        ||now>start+CYCLE_CAPTURE_BUDGET
        ||!memcmp(p->cycle_current_source.tiles,scene->tiles,NG2_TILE_COUNT)
        ||!cycle_current_data_pair(&p->cycle_current_source,scene))return 0;
    p->cycle_current_partial=2;
    return 1;
}
static int cycle_current_partial_result(const NG2Controller *p,const NG2RingResult *result){
    const NG2Scene *s=&p->cycle_current_source;int i,x,y,box[4];
    if(!cycle_current_partial_local(p,s)||result->row_count
        ||(result->partial_count?result->partial_safe_no_positive!=1:result->partial_safe_no_positive!=0)
        ||!entry_potential(s,result,box)||!entry_preserves(box,0))return 0;
    for(i=0;i<result->partial_count;++i){
        const NG2RingSlot *v=&result->partial[i];
        if(!cycle_structural_cell(v->cx,448,&x)||!cycle_structural_cell(v->sy+48,207,&y)
            ||tile(s,x,y)!=NG2_TILE_ITEM)return 0;
    }
    return 1;
}
static int cycle_current_assess(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    size_t samples;
    if(p->cycle_current_active!=1)return 0;
    if(!cycle_current_identity(p)||now>p->cycle_current_parent){
        p->cycle_current_invalid=1;cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;
    }
    if(p->cycle_current_partial==2){
        p->cycle_current_active=0;
        if(result->outcome==NG2_RING_UNKNOWN){
            p->cycle.state=NG2_CYCLE_HELD;++p->cycle.completed_shops;return 1;
        }
        return 0;
    }
    if(result->outcome!=NG2_RING_UNKNOWN){p->cycle_current_active=0;return 0;}
    if(!entry_result_safe(result)||cycle_result_positive_hint(result)!=0
        ||(p->cycle_current_partial?!cycle_current_partial_result(p,result):
            !cycle_current_up_layout(&p->cycle_current_source,result))){
        p->cycle_current_invalid=1;cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;
    }
    p->cycle_current_active=2;p->cycle_full_spent=1;p->cycle_full_framing=1;
    memset(&p->cycle_full_choice,0,sizeof(p->cycle_full_choice));
    p->cycle_full_choice.direction=NG2_UP;p->cycle_full_choice.reason=5;
    p->cycle_full_choice.target_y= -1;p->cycle_full_choice.obstacle=NG2_TILE_FLOOR;
    p->cycle_full_old_ordinal=p->cycle_current_ordinal;
    p->cycle_full_source=p->cycle_current_source;p->cycle_full_source_valid=1;
    p->cycle_full_source_id=p->cycle_current_id;p->cycle_full_source_start=p->cycle_current_start;
    p->cycle_full_source_prefix=p->cycle_current_prefix;p->cycle_full_parent=p->cycle_current_parent;
    p->cycle_full_data_active=p->cycle_full_data_blocked=0;
    p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;
    samples=p->sample_count;clear_slots(p);clear_model(p);p->sample_count=samples;
    p->proof_capture_id=p->proof_deadline=0;return 1;
}
static int cycle_current_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Motion still={0};int safe,validation=NG2_REVALIDATE_NONE;
    if(!p->cycle_current_active)return 0;
    if(p->cycle.candidate_latched)return 1;
    if(id<=p->cycle_current_id||start<p->cycle_current_end)return 1;
    safe=prefix==p->cycle_current_prefix&&p->s.input_state<=1
        &&now<=p->cycle_current_parent&&now<=start+CYCLE_CAPTURE_BUDGET
        &&cycle_current_relation(p,scene,&still);
    if(!safe&&cycle_current_keep_data(p,scene,start,end,prefix,now))safe=1;
    if(!safe){
        validation=now>p->cycle_current_parent||now>start+CYCLE_CAPTURE_BUDGET?
            NG2_REVALIDATE_TIMING:prefix!=p->cycle_current_prefix||p->s.input_state>1?
            NG2_REVALIDATE_STATE:memcmp(p->cycle_current_source.tiles,scene->tiles,NG2_TILE_COUNT)
                ||memcmp(p->cycle_current_source.protected_cells,scene->protected_cells,NG2_TILE_COUNT)?
            NG2_REVALIDATE_PROTECTED:NG2_REVALIDATE_MOTION;
        if(!p->cycle_current_invalid){
            diagnostic_comparison(p,id,validation,&still);cycle_record_rejection(p,scene,id,validation);
        }
        p->cycle_current_invalid=1;
    }
    /* An in-flight worker retains candidate priority, even after invalidation.
     * No later image is queued as another anchor or replacement job. */
    if(p->cycle.pending)return 1;
    if(p->cycle_current_invalid){
        cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;
    }
    if(p->cycle_current_active!=2||start<p->cycle.release_after_ns
        ||(p->cycle_current_proof_id&&(id<=p->cycle_current_proof_id
            ||start<p->cycle_current_proof_end)))return 1;
    /* Freeze the independent pair at B. Later direct zero frames revalidate
     * that same anchor and may track phase; they cannot rewrite a reserved
     * framing3 ticket back to observation2 or move its proof identity. */
    if(p->cycle_current_proofs<2){
        p->cycle_current_proof_id=id;p->cycle_current_proof_end=end;
        ++p->cycle_current_proofs;p->proof_capture_id=id;
        if(p->cycle_current_proofs==2){
            p->cycle_full_framing=2;p->s.reason=NG2_REASON_NONE;p->s.phase=NG2_PHASE_SYNC;
            p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->sync_ns=p->latest_verified_ns;
            if(p->cycle_sync_deadline>=12*SECOND)
                p->sync_ns=minimum(p->sync_ns,p->cycle_sync_deadline-12*SECOND);
        }
    }
    add_sample(p,scene,id,start,end);return 1;
}
static void entry_unknown_hold(NG2Controller *p){
    p->entry.stage=6;p->entry.valid=0;p->cycle.state=NG2_CYCLE_HELD;
    p->cycle_queued_valid=0;
    p->s.reason=NG2_REASON_GOODS;++p->cycle.completed_shops;
}
static int entry_start(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    int side,box[4];
    if(p->entry.active||cycle_framing_scene(&p->cycle_anchor)||!cycle_corridor_scene(&p->cycle_anchor)
        ||!entry_potential(&p->cycle_anchor,result,box)||!entry_preserves(box,0))return 0;
    memset(&p->entry,0,sizeof(p->entry));p->entry.active=p->entry.valid=1;p->entry.stage=1;
    p->entry.parent=p->cycle.continuation_deadline_ns;p->entry.level=p->cycle.level_id;
    p->entry.opening=p->entry.prefix=p->cycle.prefix;p->entry.job=p->cycle.job_id;p->entry.capture=p->cycle.capture_id;
    p->entry.ordinal=p->s.last_ordinal;
    p->entry.reference=p->cycle_anchor;memcpy(p->entry.parent_box,box,sizeof(box));memcpy(p->entry.current_box,box,sizeof(box));
    for(side=-1;side<=1;side+=2)if(tile(&p->cycle_anchor,side,-3)==NG2_TILE_GOLD
        &&tile(&p->cycle_anchor,side,-2)==NG2_TILE_GOLD&&tile(&p->cycle_anchor,side,-1)==NG2_TILE_GOLD
        &&tile(&p->cycle_anchor,-side,-1)==NG2_TILE_GOLD){p->entry.side=side;break;}
    p->entry.choice.direction=NG2_UP;p->entry.choice.reason=5;p->entry.choice.target_y= -1;p->entry.choice.obstacle=NG2_TILE_FLOOR;
    p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
}
static void entry_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t prefix,uint64_t now,int bridge){
    NG2Motion still={0};
    if(bridge&&(!ng2_motion(&p->entry.reference,scene,NG2_UP,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy))p->entry.valid=0;
    not_sent(p,now,NG2_REASON_GOODS);clear_slots(p);
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->entry.job=p->cycle.job_id;p->entry.capture=id;p->entry.prefix=prefix;
    p->entry.stage=5;
    if(p->entry.valid)p->entry.reference=*scene;
}
static int entry_assess(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    int box[4];
    if(!p->entry.active)return 0;
    /* A validated complete negative keeps the original durable UI protocol;
     * the entry episode cannot create or withhold that separate authority. */
    if(result->outcome==NG2_RING_NEGATIVE){p->entry.stage=6;p->entry.valid=0;return 0;}
    if(!entry_result_safe(result)||now>p->entry.parent){entry_unknown_hold(p);return 1;}
    if(p->cycle_queued_valid&&result->outcome==NG2_RING_UNKNOWN){
        NG2Scene scene=p->cycle_queued_scene;uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,prefix=p->cycle.queued_prefix;
        p->cycle_queued_valid=0;entry_bind(p,&scene,id,start,prefix,now,1);return 1;
    }
    if(p->entry.inputs>=2||!entry_identity(p)
        ||!entry_local(p,&p->cycle_anchor)||!entry_potential(&p->cycle_anchor,result,box)
        ||!entry_preserves(p->entry.parent_box,36*p->entry.moves)||!entry_preserves(box,0)){
        entry_unknown_hold(p);return 1;
    }
    memcpy(p->entry.current_box,box,sizeof(box));p->entry.stage=1;
    p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
}
static int entry_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *still){
    if(!entry_identity(p)||!entry_local(p,scene)||memcmp(p->cycle_anchor.tiles,scene->tiles,NG2_TILE_COUNT)
        ||memcmp(p->cycle_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||scene->goods!=p->cycle_anchor.goods)return NG2_REVALIDATE_PROTECTED;
    if(!entry_preserves(p->entry.parent_box,36*p->entry.moves)||!entry_preserves(p->entry.current_box,0))return NG2_REVALIDATE_FLOOR;
    if(!ng2_motion(&p->cycle_anchor,scene,NG2_UP,still)||still->kind!=NG2_BLOCKED||still->dx||still->dy)return NG2_REVALIDATE_MOTION;
    return NG2_REVALIDATE_NONE;
}
static int entry_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Motion still={0};int validation;
    if(!p->entry.active||p->entry.stage>=6)return 0;
    cycle_scene(p,scene,id,start,end,prefix);
    if(p->entry.stage==5){
        /* A current normal worker owns its immutable source until adoption.
         * FULL is queued data, never permission to discard a possible target. */
        if(p->cycle.pending&&p->cycle.partial&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE){
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
            p->cycle.full_seen=1;p->s.goods=1;
        }
        return 1;
    }
    if(p->entry.stage==4){
        if(p->s.input_state==3&&p->command.id==p->entry.issued){
            NG2ControllerEvent *e=event(p);resolve_move(p,scene,id,start,end);
            if(!p->finish_requested&&p->s.input_state==0&&e&&e->motion==NG2_MOVED&&!e->dx&&e->dy== -1){
                ++p->entry.moves;p->entry.last_move=p->command.id;p->entry.moved_capture=id;p->entry.reference=*scene;
                if(scene->goods==NG2_GOODS_UNKNOWN)cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);
                else entry_bind(p,scene,id,start,prefix,now,0);
            }
        }
        return 1;
    }
    if(p->entry.inputs<2&&p->cycle.partial&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE){
        /* Qualified prefix only: the prior result was already adopted. A
         * definitely-unsent ticket may retire before this new data job. */
        entry_bind(p,scene,id,start,prefix,now,1);return 1;
    }
    if(now>p->entry.parent)validation=NG2_REVALIDATE_TIMING;
    else if(id<=p->cycle.capture_id||start<p->cycle.release_after_ns)return 1;
    else validation=entry_static(p,scene,&still);
    diagnostic_comparison(p,id,validation,&still);
    if(validation){cycle_record_rejection(p,scene,id,validation);cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;}
    if(p->entry.stage==1){
        clear_slots(p);p->entry.stage=2;p->cycle.state=NG2_CYCLE_SEARCH;
        p->s.reason=NG2_REASON_NONE;p->s.phase=NG2_PHASE_SYNC;p->proof_capture_id=id;
        p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->sync_ns=p->latest_verified_ns;
        if(p->cycle_sync_deadline>=12*SECOND)p->sync_ns=minimum(p->sync_ns,p->cycle_sync_deadline-12*SECOND);
    }
    add_sample(p,scene,id,start,end);return 1;
}
static int lower_local(const NG2Scene *scene){
    return scene->state==NG2_FLOOR&&(scene->goods==NG2_GOODS_PARTIAL||scene->goods==NG2_GOODS_VISIBLE)
        &&actual_gold(scene)&&cycle_exact_item_protection(scene)
        &&tile(scene,0,0)==NG2_TILE_FLOOR&&tile(scene,0,1)==NG2_TILE_FLOOR
        &&!protected_at(scene,0,0)&&!protected_at(scene,0,1);
}
/* Exact projection explains every protected point, so its observed ITEM
 * origins already contain that mask. Do not invent additional ITEMs from
 * the neighboring protection cells or omit any normal worker search union. */
static int lower_potential(const NG2Scene *scene,const NG2RingResult *result,int box[4]){
    int i,r,k;box[0]=896;box[1]=414;box[2]=box[3]=0;
    if(!entry_result_safe(result)||(!result->row_count&&!result->partial_count)
        ||(scene->goods==NG2_GOODS_VISIBLE&&result->partial_safe_no_positive)
        ||(scene->goods==NG2_GOODS_PARTIAL&&result->partial_safe_no_positive!=1))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM)
        entry_item_box(box,i%23-11,i/23-5);
    for(r=0;r<result->row_count;++r){
        const NG2RingRow *row=&result->rows[r];
        if(row->left<0||row->left>=896||row->sy<0||row->sy>=414)return 0;
        entry_box(box,row->left-112,row->sy-20,row->left+184,row->sy+52);
        for(k=0;k<3;++k){
            const NG2RingSlot *v=&row->slots[k];
            if(v->cx!=row->left+36*k||v->sy!=row->sy)return 0;
            entry_box(box,v->cx-60,v->sy-32,v->cx+60,v->sy+115);
        }
    }
    for(k=0;k<result->partial_count;++k){
        const NG2RingSlot *v=&result->partial[k];
        if(v->cx<0||v->cx>=896||v->sy<0||v->sy>=414)return 0;
        entry_box(box,v->cx-60,v->sy-32,v->cx+60,v->sy+115);
    }
    return box[0]<box[2]&&box[1]<box[3];
}
/* At x143..663, all viewport/HUD exclusions at y>=45 are bottom-closed.
 * Translating the whole potential union upward never loses an old visible
 * pixel. Its frozen remaining geometric distance must fit wholly centrally. */
static int lower_fits(const int box[4],int remaining){
    return remaining>=0&&box[0]>=143&&box[2]<=663&&box[0]<box[2]&&box[1]<box[3]
        &&box[1]-36*remaining>=45&&box[3]-36*remaining<=315;
}
static int lower_parent_fits(const NG2Controller *p){
    int box[4],remaining=p->lower.steps-p->lower.moves;
    if(!p->lower.valid||p->lower.moves<0||p->lower.moves>p->lower.inputs||p->lower.inputs>p->lower.steps)return 0;
    memcpy(box,p->lower.parent_box,sizeof(box));box[1]-=36*p->lower.moves;box[3]-=36*p->lower.moves;
    return lower_fits(box,remaining);
}
static int lower_history(const NG2Controller *p){
    const NG2ControllerEvent *e=p->event_count?&p->events[p->event_count-1]:NULL;
    return p->entrance.valid==1&&e&&e->command.id==p->cycle.prefix
        &&e->command.kind==NG2_ACTION_MOVE&&e->command.direction>=1&&e->command.direction<=4
        &&e->outcome==2&&e->begin_ns&&e->end_ns
        &&e->motion==NG2_MOVED&&e->dx==dx[e->command.direction]&&e->dy==dy[e->command.direction]
        &&e->observed_capture_id&&e->observed_capture_id<=p->cycle.capture_id
        &&e->end_ns<=p->cycle.capture_start_ns;
}
static void lower_hold(NG2Controller *p){
    /* Data classification is allowed after loss of the old world bridge.
     * Only a final UNKNOWN hold freezes that rejected MOVE qualification;
     * candidate or independently valid NEGATIVE never gets this fault. */
    if(!p->lower.valid&&p->lower.bridge_stop.source_capture_id)
        freeze_stop_detail(p,p->last_now,NG2_REASON_GOODS,&p->lower.bridge_stop);
    p->lower.stage=6;p->cycle.state=NG2_CYCLE_HELD;p->cycle_queued_valid=0;
    p->s.reason=NG2_REASON_GOODS;
}
static void lower_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t prefix,uint64_t now,int bridge){
    NG2Motion still={0};
    if(bridge&&(!ng2_motion(&p->cycle_anchor,scene,NG2_DOWN,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)){
        if(p->lower.valid){
            diagnostic_comparison(p,id,NG2_REVALIDATE_MOTION,&still);
            cycle_record_rejection(p,scene,id,NG2_REVALIDATE_MOTION);
            live_stop_detail(p,&p->lower.bridge_stop);
            p->lower.bridge_stop.observed_capture_id=id;
        }
        p->lower.valid=0;
    }
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,p->lower.parent);
    p->lower.stage=5;
}
static int lower_assess(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    NG2Decision ordinary;int box[4],remaining;
    if(result->outcome==NG2_RING_NEGATIVE){if(p->lower.active)p->lower.stage=6;return 0;}
    if(!p->lower.active){
        /* Keep a normally qualified DOWN on its existing partial path. The
         * local proof fills the last framing gap or the extra goods halo. */
        if(p->cycle.partial&&cycle_partial_choice(p,&p->cycle_anchor,&ordinary)
            &&ordinary.direction==NG2_DOWN)return 0;
        if(p->entry.active||p->cycle_full_spent||p->cycle_full_framing||p->cycle_restart_unproved
            ||p->cycle_pause_attempted||p->cycle_storage_error||p->s.input_state||p->finish_requested||!p->s.lead_confirmed
            ||!p->cycle.capture_id||p->cycle.prefix!=p->s.last_completed_id
            ||p->last_observed_prefix!=p->cycle.prefix||now>p->cycle.continuation_deadline_ns
            ||!lower_history(p)||!lower_local(&p->cycle_anchor)
            ||!lower_potential(&p->cycle_anchor,result,box)||box[3]<=315)return 0;
        remaining=(box[3]-315+35)/36;
        if(remaining>16-p->s.inputs||!lower_fits(box,remaining))return 0;
        memset(&p->lower,0,sizeof(p->lower));p->lower.active=p->lower.valid=1;p->lower.level=p->cycle.level_id;
        p->lower.steps=remaining;memcpy(p->lower.parent_box,box,sizeof(box));
        p->lower.parent=p->cycle.continuation_deadline_ns;p->lower.ordinal=p->s.last_ordinal;
    }else{
        if(!entry_result_safe(result)||now>p->lower.parent){lower_hold(p);return 1;}
        if(p->cycle_queued_valid){
            NG2Scene scene=p->cycle_queued_scene;uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,prefix=p->cycle.queued_prefix;
            p->cycle_queued_valid=0;lower_bind(p,&scene,id,start,prefix,now,1);return 1;
        }
        remaining=p->lower.steps-p->lower.moves;
        if(remaining<=0||p->lower.inputs!=p->lower.moves||p->lower.level!=p->cycle.level_id
            ||!lower_parent_fits(p)||!lower_local(&p->cycle_anchor)||!lower_potential(&p->cycle_anchor,result,box)
            ||!lower_fits(box,remaining)){lower_hold(p);return 1;}
    }
    memcpy(p->lower.box,box,sizeof(box));p->lower.stage=1;
    p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
}
static int lower_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *still){
    if(!lower_local(scene)||!lower_parent_fits(p)||!lower_fits(p->lower.box,p->lower.steps-p->lower.moves)
        ||p->lower.inputs!=p->lower.moves||p->lower.inputs>=p->lower.steps
        ||p->lower.level!=p->cycle.level_id
        ||p->cycle.prefix!=p->s.last_completed_id||p->last_observed_prefix!=p->cycle.prefix
        ||scene->goods!=p->cycle_anchor.goods
        ||memcmp(p->cycle_anchor.tiles,scene->tiles,NG2_TILE_COUNT)
        ||memcmp(p->cycle_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT))return NG2_REVALIDATE_PROTECTED;
    if(!ng2_motion(&p->cycle_anchor,scene,NG2_DOWN,still)
        ||still->kind!=NG2_BLOCKED||still->dx||still->dy)return NG2_REVALIDATE_MOTION;
    return NG2_REVALIDATE_NONE;
}
static int lower_far_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *still){
    const NG2Scene *a=&p->cycle_anchor;int i,changed=0;
    if(p->lower.inputs!=p->lower.moves||p->lower.inputs>=p->lower.steps
        ||p->lower.level!=p->cycle.level_id||!lower_parent_fits(p)
        ||p->cycle.prefix!=p->s.last_completed_id||p->last_observed_prefix!=p->cycle.prefix
        ||!lower_local(scene)||scene->goods!=a->goods)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int old=a->tiles[i],next=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a->protected_cells[i]!=scene->protected_cells[i]||(old==NG2_TILE_GOLD&&next!=old)
            ||((old==NG2_TILE_ITEM)!=(next==NG2_TILE_ITEM)))return 0;
        if(old==next)continue;
        if(a->protected_cells[i]||(abs(x)<=1&&y>=-1&&y<=2))return 0;
        changed=1;
    }
    return changed&&ng2_motion(a,scene,NG2_DOWN,still)&&still->kind==NG2_BLOCKED&&!still->dx&&!still->dy;
}
static int lower_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2Motion still={0};int validation;
    if(!p->lower.active||p->lower.stage>=6)return 0;
    cycle_scene(p,scene,id,start,end,prefix);
    if(p->lower.stage==5){
        if(p->cycle.pending&&p->cycle.partial&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE){
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
            p->cycle.full_seen=1;p->s.goods=1;
        }
        return 1;
    }
    if(p->lower.stage==4){
        if(p->s.input_state==3&&p->command.id==p->lower.issued){
            NG2ControllerEvent *e=event(p);
            if(scene->state==NG2_UNKNOWN&&start>=p->ack_ns&&now<=p->motion_wait.deadline_ns){
                phase_failure(p,NG2_RECOVERY_VISUAL_PHASE,end,id);clear_slots(p);return 1;
            }
            resolve_move(p,scene,id,start,end);
            if(!p->finish_requested&&p->s.input_state==0&&e&&e->motion==NG2_MOVED&&!e->dx&&e->dy==1){
                ++p->lower.moves;
                if(scene->goods==NG2_GOODS_UNKNOWN)lower_hold(p);
                else lower_bind(p,scene,id,start,prefix,now,0);
            }
        }
        return 1;
    }
    if(now>p->lower.parent)validation=NG2_REVALIDATE_TIMING;
    else if(id<=p->cycle.capture_id||start<p->cycle.release_after_ns)return 1;
    else if(p->cycle.partial&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE){
        lower_bind(p,scene,id,start,prefix,now,1);return 1;
    }else validation=lower_static(p,scene,&still);
    if(validation==NG2_REVALIDATE_PROTECTED&&lower_far_static(p,scene,&still)){
        lower_bind(p,scene,id,start,prefix,now,1);return 1;
    }
    diagnostic_comparison(p,id,validation,&still);
    if(validation){cycle_record_rejection(p,scene,id,validation);cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;}
    if(p->lower.stage==1){
        clear_slots(p);p->lower.stage=2;p->s.reason=NG2_REASON_NONE;p->s.phase=NG2_PHASE_SYNC;
        p->proof_capture_id=id;p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->sync_ns=p->latest_verified_ns;
        if(p->cycle_sync_deadline>=12*SECOND)p->sync_ns=minimum(p->sync_ns,p->cycle_sync_deadline-12*SECOND);
    }
    add_sample(p,scene,id,start,end);return 1;
}
/* This is observation authority for an originally hidden lower offer row,
 * not an absence certificate or a general route through merchandise. */
static int upper_side_variant(const NG2Scene *scene,int direction){
    int i,x,y,d,count=0,old=1,lower=1;
    if(direction!=NG2_LEFT&&direction!=NG2_RIGHT)return 0;
    d=dx[direction];
    for(i=0;i<NG2_TILE_COUNT;++i)if(scene->tiles[i]==NG2_TILE_ITEM){
        x=(i%23-11)*d;y=i/23-5;++count;
        if(y!=3||x<1||x>7)old=0;
        if(y!=4||x<3||x>7)lower=0;
    }
    if(tile(scene,d,-1)!=NG2_TILE_GOLD||tile(scene,d,1)!=NG2_TILE_GOLD)return 0;
    if(old&&count==7){
        for(y=-2;y<=1;++y)if(tile(scene,7*d,y)!=NG2_TILE_GOLD)return 0;
        for(x=4;x<=7;++x)if(tile(scene,d*x,-2)!=NG2_TILE_GOLD)return 0;
        return 1;
    }
    if(!lower||count!=5||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(scene,d,0)!=NG2_TILE_FLOOR||tile(scene,2*d,0)!=NG2_TILE_FLOOR
        ||protected_at(scene,0,0)||protected_at(scene,d,0)||protected_at(scene,2*d,0))return 0;
    for(y=-1;y<=2;++y)if(tile(scene,7*d,y)!=NG2_TILE_GOLD)return 0;
    for(x=1;x<=7;++x)if(tile(scene,d*x,-1)!=NG2_TILE_GOLD)return 0;
    return 2;
}
static int upper_potential_protected(const NG2Controller *p,int x,int y){
    if(protected_at(&p->upper.world,x,y))return 1;
    /* The finite row4 source cannot store its y5 cardinal halo. A later
     * observed mask may reveal only that direct neighbour of a known ITEM;
     * this explains protection, never a new ITEM or a walking FLOOR. */
    return p->upper.variant==2&&p->upper.row==4&&y==5
        &&tile(&p->upper.world,x,4)==NG2_TILE_ITEM;
}
static int upper_world(const NG2Controller *p,const NG2Scene *scene){
    int i,ox=p->s.x-p->upper.x,oy=p->s.y-p->upper.y;
    if(!p->upper.valid||p->upper.level!=p->cycle.level_id
        ||ox!=dx[p->upper.direction]*p->upper.horizontal||oy!=p->upper.down
        ||scene->state!=NG2_FLOOR||(scene->goods!=NG2_GOODS_PARTIAL&&scene->goods!=NG2_GOODS_VISIBLE)
        ||!actual_gold(scene)||!cycle_exact_item_protection(scene)
        ||tile(scene,0,0)!=NG2_TILE_FLOOR||protected_at(scene,0,0))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int x=i%23-11,y=i/23-5;
        if(scene->tiles[i]==NG2_TILE_ITEM&&tile(&p->upper.world,x+ox,y+oy)!=NG2_TILE_ITEM)return 0;
        if(scene->protected_cells[i]&&!upper_potential_protected(p,x+ox,y+oy))return 0;
        if(p->upper.world.tiles[i]==NG2_TILE_GOLD&&tile(scene,x-ox,y-oy)!=NG2_TILE_GOLD)return 0;
    }
    return 1;
}
static int upper_identity(const NG2Controller *p){
    return p->upper.active&&p->upper.valid&&p->upper.level==p->cycle.level_id
        &&p->upper.steps==(p->upper.variant==2?5:4)
        &&p->upper.parent==p->upper.allocated_parent
        &&p->upper.job==p->cycle.job_id&&p->upper.capture==p->cycle.capture_id
        &&p->upper.prefix==p->cycle.prefix&&p->s.last_completed_id==p->cycle.prefix
        &&p->last_observed_prefix==p->cycle.prefix
        &&p->upper.inputs==p->upper.horizontal+p->upper.down;
}
static int upper_direction(const NG2Controller *p){
    return p->upper.horizontal<2?p->upper.direction:p->upper.down<p->upper.steps-2?NG2_DOWN:0;
}
static int upper_floor(const NG2Controller *p,const NG2Scene *scene){
    int d=upper_direction(p);
    return d&&upper_world(p,scene)&&tile(scene,dx[d],dy[d])==NG2_TILE_FLOOR
        &&!protected_at(scene,dx[d],dy[d]);
}
static int upper_anchor(const NG2Controller *p,int cx,int sy,int outside){
    int x,y,ox=p->s.x-p->upper.x,oy=p->s.y-p->upper.y;
    if(cx<0||cx>=896||sy<0||sy>=414
        ||!cycle_structural_cell(cx,448,&x)||!cycle_structural_cell(sy+48,207,&y))return 0;
    x+=ox;y+=oy;
    if(tile(&p->upper.world,x,y)==NG2_TILE_ITEM)return 1;
    return outside&&y==p->upper.row&&(tile(&p->upper.world,x-1,y)==NG2_TILE_ITEM
        ||tile(&p->upper.world,x+1,y)==NG2_TILE_ITEM);
}
static int upper_slot(const NG2Controller *p,const NG2RingSlot *slot,int outside){
    return cycle_binary_no_positive(slot)&&upper_anchor(p,slot->cx,slot->sy,outside)
        &&(cycle_zero_box(slot->icon_box)||cycle_box(slot->icon_box))
        &&(slot->word_present?cycle_box(slot->word_box):cycle_zero_box(slot->word_box));
}
static int upper_result(const NG2Controller *p,const NG2RingResult *result){
    int r,k,virtual_cell;
    if(!upper_world(p,&p->cycle_anchor))return 0;
    for(r=0;r<result->row_count;++r){
        const NG2RingRow *row=&result->rows[r];
        for(k=0;k<3;++k)
            if(row->slots[k].cx!=row->left+36*k||row->slots[k].sy!=row->sy
                ||!upper_slot(p,&row->slots[k],0))return 0;
    }
    for(k=0;k<result->partial_count;++k){
        const NG2RingSlot *slot=&result->partial[k];virtual_cell=0;
        for(r=0;r<result->row_count;++r)
            if(slot->sy==result->rows[r].sy&&(slot->cx==result->rows[r].left-36
                ||slot->cx==result->rows[r].left+108))virtual_cell=1;
        if(!upper_slot(p,slot,virtual_cell))return 0;
    }
    return 1;
}
static void upper_hold(NG2Controller *p){
    p->upper.static_proof.valid=0;
    p->upper.stage=6;p->upper.valid=0;p->cycle.state=NG2_CYCLE_HELD;
    p->cycle_queued_valid=0;p->s.reason=NG2_REASON_GOODS;++p->cycle.completed_shops;
}
static int upper_budget(const NG2Controller *p,uint64_t now,uint64_t target){
    uint64_t last,period=p->model.period_ns;int remaining=p->upper.steps-p->upper.horizontal-p->upper.down;
    if(p->upper.steps<4||p->upper.steps>5||remaining<=0||remaining>p->upper.steps
        ||!ng2_beat_model_valid(&p->model)||p->beat_failed
        ||now>p->upper.parent||now<p->model.last_ns||now-p->model.last_ns>FRESH)return 0;
    if(!target)target=ng2_next_target(&p->model,now,p->s.lead_ns+INITIAL_PREPARATION);
    if(!target||target>=NS_LIMIT||period>(NS_LIMIT-target)/(uint64_t)remaining)return 0;
    last=target+(uint64_t)(remaining-1)*period;
    /* Forecast the earliest visual response, not the maximum normal DATA
     * budget. Actual input/visual checks still use this parent; a pending
     * worker separately owns its unchanged source150ms/worker100ms clocks. */
    return p->upper.parent>=80000000&&last<=p->upper.parent-80000000;
}
static int upper_admit(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    NG2Decision choice;int i,variant;uint64_t base,allocated,period=0,independent;
    if(p->upper.active||p->entry.active||p->lower.active||p->cycle_full_spent||p->cycle_full_framing
        ||!p->cycle.partial||p->cycle.full_seen||!entry_result_safe(result)
        ||result->reason>NG2_RING_EXPOSED_TARGET_ABSENT
        ||result->row_count
        ||(result->partial_count?result->partial_safe_no_positive!=1:result->partial_safe_no_positive!=0)
        ||p->cycle_restart_unproved||p->cycle_pause_attempted||p->cycle_storage_error
        ||p->s.input_state||p->finish_requested||p->s.terminal||!p->s.lead_confirmed||level_moves(p)<=0
        ||p->s.inputs>12||!p->cycle.capture_id||p->cycle.prefix!=p->s.last_completed_id
        ||p->last_observed_prefix!=p->cycle.prefix||now>p->cycle.continuation_deadline_ns
        ||!cycle_partial_choice(p,&p->cycle_anchor,&choice)
        ||(choice.direction!=NG2_LEFT&&choice.direction!=NG2_RIGHT)||choice.reason!=5
        ||choice.obstacle!=NG2_TILE_FLOOR||!last_ack_opened_gate(p,choice.direction)
        ||!cycle_exact_item_protection(&p->cycle_anchor))return 0;
    for(i=0;i<result->partial_count;++i)
        if(result->partial[i].kind>NG2_RING_GENERIC_NON_TARGET)return 0;
    variant=upper_side_variant(&p->cycle_anchor,choice.direction);
    if(!variant)return 0;
    base=allocated=p->cycle.continuation_deadline_ns;
    if(variant==2){
        /* This is a new five-step route allocation, never an old ticket's
         * rolling extension. Capture the independent bound before active
         * would make sync_deadline() include this route's own parent. */
        if(p->s.inputs>11||!ng2_beat_model_valid(&p->model)||p->beat_failed
            ||now<p->model.last_ns||now-p->model.last_ns>FRESH)return 0;
        period=p->model.period_ns;
        if(!base||!period||base>=NS_LIMIT-period)return 0;
        independent=sync_deadline(p);
        allocated=minimum(base+period,minimum(independent,p->cycle_sync_deadline));
        allocated=minimum(allocated,session_bound(p));
        if(p->s.walk_started_ns)allocated=minimum(allocated,p->s.walk_started_ns+45*SECOND);
        if(now>allocated)return 0;
    }
    memset(&p->upper,0,sizeof(p->upper));p->upper.active=p->upper.valid=1;
    p->upper.variant=variant;p->upper.row=variant==2?4:3;p->upper.steps=variant==2?5:4;
    p->upper.direction=choice.direction;p->upper.x=p->s.x;p->upper.y=p->s.y;p->upper.world=p->cycle_anchor;
    p->upper.base_parent=base;p->upper.allocated_parent=allocated;p->upper.allocation_period=period;
    p->upper.parent=allocated;p->upper.hold=p->cycle.hold_started_ns;
    p->upper.sync=p->cycle_sync_deadline;p->upper.level=p->cycle.level_id;p->upper.opening=p->cycle.prefix;
    p->upper.job=p->cycle.job_id;p->upper.capture=p->cycle.capture_id;p->upper.prefix=p->cycle.prefix;
    p->upper.ordinal=p->s.last_ordinal;
    if(variant==2&&p->s.last_capture_id==p->cycle.capture_id
        &&p->s.last_capture_start_ns==p->cycle.capture_start_ns
        &&p->s.last_capture_end_ns>=p->cycle.capture_start_ns&&p->s.last_capture_end_ns<=now){
        p->upper.first_owner=p->s.started_ns;p->upper.first_level=p->cycle.level_id;
        p->upper.first_opening=p->upper.opening;
        p->upper.first_job=p->cycle.job_id;p->upper.first_capture=p->cycle.capture_id;
        p->upper.first_start=p->cycle.capture_start_ns;p->upper.first_end=p->s.last_capture_end_ns;
        p->upper.first_prefix=p->cycle.prefix;
        p->upper.first_worker=p->cycle.worker_started_ns;p->upper.first_assessment=now;
        p->upper.anchor_end=p->s.last_capture_end_ns;
    }
    /* Initial partial probes belong to the original ITEM cells themselves.
     * No row means upper_result cannot grant its later coherent-row halo. */
    if(!upper_result(p,result)||!upper_floor(p,&p->cycle_anchor)||!upper_budget(p,now,0)){
        memset(&p->upper,0,sizeof(p->upper));return 0;
    }
    /* Publish only after every admission proof, including the complete
     * route forecast. A failed admission leaves the old cycle parent intact. */
    p->cycle.continuation_deadline_ns=allocated;
    p->upper.stage=1;p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
}
static void upper_bind(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,
                       uint64_t prefix,uint64_t now,int bridge){
    NG2Motion still={0};int seen=p->cycle.full_seen,d=upper_direction(p);uint64_t oldjob=p->upper.job;
    p->upper.static_proof.valid=0;
    if(!d)d=NG2_DOWN;
    if(!upper_world(p,scene)||(bridge&&(!ng2_motion(&p->cycle_anchor,scene,d,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)))p->upper.valid=0;
    cycle_latch(p,scene,now);cycle_bind(p,scene,id,start,prefix);
    p->upper.anchor_end=p->s.last_capture_id==id&&p->s.last_capture_start_ns==start
        &&p->s.last_capture_end_ns>=start?p->s.last_capture_end_ns:0;
    p->cycle.hold_started_ns=p->upper.hold;p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,p->upper.sync);
    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,p->upper.parent);
    p->cycle.full_seen|=seen;p->upper.job=p->cycle.job_id;p->upper.capture=id;p->upper.prefix=prefix;
    if(p->upper.variant==2){
        /* Only a genuinely new job after this route's actual unit may arm
         * another first snapshot. Material/FULL bridge1 never rearms it. */
        p->upper.first_job=0;
        if(!bridge&&p->restart_yield.s.enabled&&p->cycle.job_id>oldjob
            &&p->upper.anchor_end&&p->upper.anchor_end>=start&&p->upper.anchor_end<=now
            &&p->upper.inputs>0&&p->upper.inputs<p->upper.steps
            &&p->upper.inputs==p->upper.horizontal+p->upper.down){
            p->upper.first_owner=p->s.started_ns;p->upper.first_level=p->cycle.level_id;
            p->upper.first_opening=p->upper.opening;p->upper.first_job=p->cycle.job_id;
            p->upper.first_capture=id;p->upper.first_start=start;p->upper.first_end=p->upper.anchor_end;
            p->upper.first_prefix=prefix;p->upper.first_inputs=p->upper.inputs;
            p->upper.first_horizontal=p->upper.horizontal;p->upper.first_down=p->upper.down;
            p->upper.first_worker=p->upper.first_assessment=p->upper.first_proof=0;
        }
    }
    p->upper.stage=5;
}
static int upper_assess(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    if(!p->upper.active)return upper_admit(p,result,now);
    if(result->outcome==NG2_RING_NEGATIVE){
        if(!p->upper.valid||!upper_result(p,result)){
            cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;
        }
        p->upper.stage=6;p->upper.valid=0;return 0;
    }
    /* A queued newly FULL image still deserves a normal data job after
     * the movement cap/root expires. It can retain positives, not MOVE. */
    if(result->outcome==NG2_RING_UNKNOWN&&entry_result_safe(result)
        &&p->cycle_queued_valid&&!p->upper.rebound){
        NG2Scene scene=p->cycle_queued_scene;
        uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,prefix=p->cycle.queued_prefix;
        p->cycle_queued_valid=0;++p->upper.rebound;upper_bind(p,&scene,id,start,prefix,now,1);return 1;
    }
    if(!p->upper.valid||!entry_result_safe(result)||!upper_result(p,result)
        ||now>p->upper.parent||p->upper.inputs>=p->upper.steps){upper_hold(p);return 1;}
    if(p->upper.variant==2&&p->restart_yield.s.enabled&&p->cycle.partial&&!p->cycle.full_seen
        &&p->upper.first_inputs>0&&!p->upper.first_worker&&!p->upper.first_assessment&&!p->upper.first_proof
        &&p->upper.first_owner==p->s.started_ns&&p->upper.first_level==p->cycle.level_id
        &&p->upper.first_opening==p->upper.opening&&p->upper.first_job==p->cycle.job_id
        &&p->upper.first_capture==p->cycle.capture_id&&p->upper.first_start==p->cycle.capture_start_ns
        &&p->upper.first_end==p->upper.anchor_end&&p->upper.first_prefix==p->cycle.prefix
        &&p->cycle.worker_started_ns>=p->upper.first_end&&p->cycle.worker_started_ns<=now){
        p->upper.first_worker=p->cycle.worker_started_ns;p->upper.first_assessment=now;
    }
    p->upper.stage=1;p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
}
static int upper_static_footprint(const NG2Controller *p,const NG2Scene *scene){
    return upper_identity(p)&&upper_floor(p,scene)&&scene->goods==p->cycle_anchor.goods
        &&!memcmp(p->cycle_anchor.tiles,scene->tiles,NG2_TILE_COUNT)
        &&!memcmp(p->cycle_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT);
}
static int upper_normal_zero(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    if(!ng2_motion(&p->cycle_anchor,scene,upper_direction(p),motion)
        ||motion->kind!=NG2_BLOCKED||motion->dx||motion->dy)return NG2_REVALIDATE_MOTION;
    return NG2_REVALIDATE_NONE;
}
static int upper_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    if(!upper_static_footprint(p,scene))return NG2_REVALIDATE_PROTECTED;
    return upper_normal_zero(p,scene,motion);
}
static void upper_remember_zero(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix){
    NG2UpperStaticProof *z=&p->upper.static_proof;
    if(p->upper.variant!=2||!p->upper.anchor_end
        ||p->upper.anchor_end<p->cycle.capture_start_ns||p->upper.anchor_end>start
        ||id!=p->s.last_capture_id||start!=p->s.last_capture_start_ns||end!=p->s.last_capture_end_ns
        ||id!=p->seen_id||start!=p->seen_start||end!=p->seen_end
        ||prefix!=p->last_observed_prefix||memcmp(scene,&p->scene,sizeof(*scene)))return;
    z->valid=1;z->owner=p->s.started_ns;z->level=p->upper.level;z->opening=p->upper.opening;
    z->job=p->upper.job;z->anchor_id=p->cycle.capture_id;z->anchor_start=p->cycle.capture_start_ns;
    z->anchor_end=p->upper.anchor_end;z->anchor_prefix=p->cycle.prefix;
    z->current_id=id;z->current_start=start;z->current_end=end;z->current_prefix=prefix;
    z->direction=upper_direction(p);z->horizontal=p->upper.horizontal;z->down=p->upper.down;
    z->inputs=p->upper.inputs;z->rebound=p->upper.rebound;
    z->anchor=p->cycle_anchor;z->current=*scene;
}
static int upper_same_zero(const NG2Controller *p,const NG2Scene *scene){
    const NG2UpperStaticProof *z=&p->upper.static_proof;
    return p->upper.variant==2&&z->valid&&!p->finish_requested&&!p->s.terminal
        &&!p->cycle.pending&&!p->cycle_assessing&&!p->cycle.candidate_latched
        &&z->owner==p->s.started_ns&&z->level==p->upper.level&&z->level==p->cycle.level_id
        &&z->opening==p->upper.opening&&z->job==p->upper.job&&z->job==p->cycle.job_id
        &&z->anchor_id==p->upper.capture&&z->anchor_id==p->cycle.capture_id
        &&z->anchor_start==p->cycle.capture_start_ns&&z->anchor_end==p->upper.anchor_end
        &&z->anchor_prefix==p->upper.prefix&&z->anchor_prefix==p->cycle.prefix
        &&z->anchor_prefix==p->s.last_completed_id&&z->current_prefix==p->last_observed_prefix
        &&z->current_prefix==z->anchor_prefix&&z->current_id==p->s.last_capture_id
        &&z->current_start==p->s.last_capture_start_ns&&z->current_end==p->s.last_capture_end_ns
        &&z->current_id==p->seen_id&&z->current_start==p->seen_start&&z->current_end==p->seen_end
        &&z->direction==upper_direction(p)&&z->horizontal==p->upper.horizontal&&z->down==p->upper.down
        &&z->inputs==p->upper.inputs&&z->rebound==p->upper.rebound
        &&!memcmp(&z->anchor,&p->cycle_anchor,sizeof(z->anchor))
        &&!memcmp(&z->current,scene,sizeof(z->current));
}
static int upper_begin_static(const NG2Controller *p,const NG2Scene *scene,NG2Motion *motion){
    if(!upper_static_footprint(p,scene))return NG2_REVALIDATE_PROTECTED;
    /* This is the exact earlier normal-zero fact, not a synthetic Motion
     * result. All command, model, fresh/time and external guards remain. */
    if(upper_same_zero(p,scene))return NG2_REVALIDATE_NONE;
    return upper_normal_zero(p,scene,motion);
}
static int upper_first_snapshot(const NG2Controller *p,uint64_t id,uint64_t start,
    uint64_t end,uint64_t prefix,uint64_t now){
    const NG2UpperObservation *u=&p->upper;
    return u->variant==2&&u->stage==1&&!u->rebound&&!u->first_proof
        &&u->inputs==u->first_inputs&&u->horizontal==u->first_horizontal&&u->down==u->first_down
        &&u->first_opening==u->opening
        &&(u->first_inputs==0?(!u->first_horizontal&&!u->first_down&&u->first_prefix==u->opening):
            (p->restart_yield.s.enabled&&u->first_inputs>0&&u->first_inputs<u->steps
                &&u->first_inputs==u->first_horizontal+u->first_down))
        &&u->first_owner==p->s.started_ns&&u->first_level==u->level&&u->level==p->cycle.level_id
        &&u->first_job==u->job&&u->job==p->cycle.job_id
        &&u->first_capture==u->capture&&u->capture==p->cycle.capture_id
        &&u->first_start==p->cycle.capture_start_ns&&u->first_end>=u->first_start
        &&u->first_end<=u->first_assessment&&u->first_worker>0&&u->first_worker<=u->first_assessment
        &&prefix==u->first_prefix&&prefix==u->prefix
        &&prefix==p->cycle.prefix&&prefix==p->s.last_completed_id&&prefix==p->last_observed_prefix
        &&u->first_assessment==p->cycle.assessment_ns&&u->first_assessment==p->cycle.release_after_ns
        &&!p->cycle.pending&&!p->cycle_assessing&&!p->cycle.candidate_latched&&!p->cycle.full_seen
        &&p->cycle.partial&&p->cycle.status==NG2_RING_OK&&p->cycle.outcome==NG2_RING_UNKNOWN
        &&p->cycle.coverage==NG2_RING_COVERAGE_INCOMPLETE&&!p->s.input_state
        &&!p->finish_requested&&!p->s.terminal&&id>u->first_capture
        &&id==p->s.last_capture_id&&start==p->s.last_capture_start_ns&&end==p->s.last_capture_end_ns
        &&start>=u->first_end&&start>=u->first_worker&&end>=u->first_assessment
        &&now>=end&&now>=u->first_assessment&&now<=u->parent&&now<=start+CYCLE_CAPTURE_BUDGET;
}
static int upper_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,
                          uint64_t end,uint64_t prefix,uint64_t now){
    NG2Motion still={0};int validation,d;
    if(!p->upper.active||p->upper.stage>=6)return 0;
    p->upper.static_proof.valid=0;
    cycle_scene(p,scene,id,start,end,prefix);
    if(p->upper.stage==5){
        /* New accepted geometry can revoke the old source's MOVE/negative
         * identity while its immutable worker drains; positives stay prior. */
        if(scene->state==NG2_FLOOR&&!upper_world(p,scene))p->upper.valid=0;
        if(!p->upper.rebound&&p->cycle.pending&&p->cycle.partial
            &&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE){
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
        }
        return 1;
    }
    if(p->upper.stage==4){
        if(p->s.input_state==3&&p->command.id==p->upper.issued){
            NG2ControllerEvent *e=event(p);d=p->command.direction;
            if(scene->state==NG2_UNKNOWN&&start>=p->ack_ns&&now<=p->motion_wait.deadline_ns){
                phase_failure(p,NG2_RECOVERY_VISUAL_PHASE,end,id);clear_slots(p);return 1;
            }
            resolve_move(p,scene,id,start,end);
            if(!p->finish_requested&&p->s.input_state==0&&e&&e->motion==NG2_MOVED
                &&e->dx==dx[d]&&e->dy==dy[d]){
                if(d==p->upper.direction)++p->upper.horizontal;else if(d==NG2_DOWN)++p->upper.down;
                else {cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;}
                p->upper.rebound=0;
                if(scene->goods==NG2_GOODS_UNKNOWN)upper_hold(p);
                else upper_bind(p,scene,id,start,prefix,now,0);
            }
        }
        return 1;
    }
    if(now>p->upper.parent){cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 1;}
    if(id<=p->cycle.capture_id||(start<p->cycle.release_after_ns
        &&!upper_first_snapshot(p,id,start,end,prefix,now)))return 1;
    validation=upper_static(p,scene,&still);
    if(validation){
        int changed=memcmp(p->cycle_anchor.tiles,scene->tiles,NG2_TILE_COUNT)
            ||memcmp(p->cycle_anchor.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
            ||scene->goods!=p->cycle_anchor.goods;
        if(!p->upper.rebound&&scene->state==NG2_FLOOR
            &&(scene->goods==NG2_GOODS_PARTIAL||scene->goods==NG2_GOODS_VISIBLE)&&changed){
            if(p->s.input_state==1)not_sent(p,now,NG2_REASON_GOODS);
            clear_slots(p);++p->upper.rebound;upper_bind(p,scene,id,start,prefix,now,1);return 1;
        }
        /* No response, model or latest mask may stand in for direct zero.
         * Unchanged unsafe floor may wait, but never gains a ticket. */
        if(p->upper.stage!=3&&upper_world(p,scene))return 1;
        cycle_record_rejection(p,scene,id,validation);
        cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;
    }
    if(p->upper.stage==1){
        if(p->upper.variant==2&&!p->upper.first_proof)p->upper.first_proof=id;
        clear_slots(p);p->upper.stage=2;p->proof_capture_id=id;
        p->s.reason=NG2_REASON_NONE;p->s.phase=NG2_PHASE_SYNC;p->recovery.mode=NG2_RECOVERY_POST_MOVE;
        p->sync_ns=p->latest_verified_ns;
        if(p->upper.sync>=12*SECOND)p->sync_ns=minimum(p->sync_ns,p->upper.sync-12*SECOND);
    }
    upper_remember_zero(p,scene,id,start,end,prefix);
    add_sample(p,scene,id,start,end);return 1;
}

/* An early FULL keeps merchandise prior while its owned UP is still UNKNOWN.
 * A later normal unit of the ORIGINAL ACK may be credited once, within that
 * ACK's untouched visual bound, then funds only independent current DATA.
 * The early FULL is never called stationary or relabelled as that unit. */
static int cycle_early_full_up_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    const NG2Scene *a=&p->cycle_anchor;const NG2Command *old=&p->cycle_up_command;
    NG2ControllerEvent *e=NULL;NG2ControllerMotionReference *reference=NULL;
    NG2Motion moved={0};size_t i;
    if(!p->restart_yield.s.enabled||p->cycle_up_history!=1||p->cycle_current_used
        ||p->cycle_current_active||p->cycle_retry_only||p->cycle_retry_used>=2
        ||p->cycle_up_job!=p->cycle.job_id||p->cycle_up_level!=p->cycle.level_id
        ||p->cycle_up_capture!=p->cycle.capture_id||old->kind!=NG2_ACTION_MOVE||old->direction!=NG2_UP
        ||old->id!=prefix||p->cycle.prefix!=prefix||p->s.last_completed_id!=prefix
        ||p->last_observed_prefix!=prefix||p->cycle.partial||!p->cycle.full_seen
        ||p->cycle.pending||p->cycle.candidate_latched||p->cycle_restart_unproved||p->cycle_storage_error
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE||p->cycle.state!=NG2_CYCLE_OBSERVE_MORE
        ||!p->cycle_full_spent||(p->cycle_full_framing!=1&&p->cycle_full_framing!=2)
        ||p->cycle_full_choice.direction!=NG2_UP||p->cycle_full_data_active
        ||p->cycle.pause_capture_id||p->cycle.durable_ns||p->cycle.intent_ns
        ||p->entry.active||p->lower.active||p->upper.active||p->restart_yield.s.pending
        ||p->finish_requested||p->s.terminal||p->s.input_state>1
        ||(p->s.input_state==1&&!cycle_data_prepared_pause(p))
        ||(p->cycle_pause_attempted&&!cycle_data_prepared_pause(p))
        ||id<=p->cycle.capture_id||start<p->cycle.release_after_ns||start<=p->cycle.capture_start_ns
        ||now<end||now>start+CYCLE_CAPTURE_BUDGET||now>p->cycle.continuation_deadline_ns
        ||p->motion_wait.command_id!=old->id||p->motion_wait.source_capture_id!=old->source_capture_id
        ||p->motion_wait.active||!p->motion_wait.attempts||p->motion_wait.attempts>=MOTION_ASSESSMENTS
        ||p->motion_wait.last_motion!=NG2_MOTION_UNKNOWN||now>p->motion_wait.deadline_ns
        ||end>p->motion_wait.deadline_ns||!p->cycle_up_period
        ||start<p->motion_retry_last_ns||start-p->motion_retry_last_ns<p->cycle_up_period/10
        ||(p->motion_wait.attempts==MOTION_ASSESSMENTS-1
            &&(start<p->motion_retry_start_ns||start-p->motion_retry_start_ns<p->cycle_up_period))
        ||!cycle_full_up_local(a)||!cycle_full_up_local(scene)||a->gold_state!=scene->gold_state)return 0;
    for(i=0;i<p->event_count;++i){
        NG2ControllerEvent *row=&p->events[i];
        if(row->command.id==old->id)e=row;
        if(row->command.id>old->id&&row->begin_ns)return 0;
    }
    if(!e||memcmp(&e->command,old,sizeof(*old))||e->outcome!=2||!e->begin_ns||!e->end_ns
        ||e->end_ns!=p->ack_ns||e->motion!=NG2_MOTION_UNKNOWN||e->dx||e->dy
        ||e->observed_capture_id!=p->cycle.capture_id
        ||start<maximum(e->end_ns,old->target_ns+80000000))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(((a->tiles[i]==NG2_TILE_ITEM)!=(scene->tiles[i]==NG2_TILE_ITEM))
            ||a->protected_cells[i]!=scene->protected_cells[i]
            ||(a->tiles[i]==NG2_TILE_GOLD&&scene->tiles[i]!=NG2_TILE_GOLD))return 0;
    if(!ng2_motion(&p->cycle_up_before,scene,NG2_UP,&moved)
        ||moved.kind!=NG2_MOVED||moved.dx||moved.dy!=-1)return 0;
    /* This is evidence for the existing ACK, never a new input state. Keep
     * original event and primary trace linked to the actual later capture. */
    e->motion=moved.kind;e->dx=moved.dx;e->dy=moved.dy;e->observed_capture_id=id;
    for(i=0;i<p->motion_reference_count;++i)
        if(p->motion_references[i].command_id==old->id)reference=&p->motion_references[i];
    if(reference){
        reference->observed_capture_id=id;reference->primary_motion=moved.kind;
        reference->reference_eligible=reference->fallback_attempted=reference->fallback_motion=0;
        reference->selected_capture_id=old->source_capture_id;reference->selected_motion=moved.kind;
    }
    ++p->motion_wait.attempts;p->motion_wait.last_capture_id=id;p->motion_wait.last_motion=moved.kind;
    p->motion_retry_last_ns=start;
    irregular_clear_first(p);
    if(!credit_unit_move(p,&p->cycle_up_before,scene,NG2_UP,&moved,e,end))return 1;
    p->s.last_ordinal=old->ordinal;
    p->cycle_up_history=2;p->cycle_retry_blocked|=1;
    cycle_current_bind(p,scene,id,start,end,prefix,now,0);
    return 1;
}
static int cycle_observe_hold(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t commit){
    cycle_scene(p,scene,id,start,end,prefix);
    if(cycle_early_full_up_refresh(p,scene,id,start,end,prefix,commit))return 1;
    if(cycle_current_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(cycle_current_data_start(p,NULL,commit))return 1;
    /* Tracking an in-flight source is not retry/input admission. In
     * particular, its exact unsent PAUSE must not hide a later hard change
     * before the owning worker returns. No queued source or job is minted. */
    if(p->cycle.pending&&!p->cycle_retry_data&&!p->cycle.partial&&p->cycle.full_seen
        &&cycle_data_prepared_pause(p)){
        if(id>p->cycle.capture_id&&start>p->cycle.capture_start_ns){
            int same=prefix==p->cycle.prefix&&commit<=p->cycle.continuation_deadline_ns
                &&commit<=start+CYCLE_CAPTURE_BUDGET;
            if(same&&scene->state==NG2_UNKNOWN)p->cycle_retry_blocked|=2;
            else if(!same||!cycle_retry_relation(p,scene))p->cycle_retry_blocked|=1;
            if(p->cycle_retry_blocked){
                p->cycle_queued_valid=0;
                p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
            }
        }
        return 1;
    }
    if(p->cycle_retry_data&&(p->cycle_retry_waiting||p->cycle.pending)){
        int safe;
        if(id<=p->cycle.capture_id||start<=p->cycle.capture_start_ns)return 1;
        safe=prefix==p->cycle_retry_prefix&&p->cycle.level_id==p->cycle_retry_level
            &&commit<=p->cycle_retry_parent&&commit<=start+CYCLE_CAPTURE_BUDGET;
        if(safe&&scene->state==NG2_UNKNOWN)return 1;
        if(!safe||!cycle_retry_data_relation(p,scene)){
            p->cycle_retry_blocked|=1;p->cycle_queued_valid=0;
            p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
        }else if(!p->cycle_retry_blocked){
            if(p->cycle_retry_waiting&&!p->cycle.pending){
                cycle_retry_bind(p,scene,id,start,prefix,commit);return 1;
            }
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
        }
        if(p->cycle_retry_waiting&&!p->cycle.pending&&p->cycle_retry_blocked)
            cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);
        return 1;
    }
    if((p->cycle_retry_only&&p->cycle_retry_waiting)||cycle_retry_eligible(p,commit)
        ||(p->cycle.pending&&cycle_retry_basis(p,commit,1))){
        if(id>p->cycle.capture_id&&start>p->cycle.capture_start_ns){
            int safe=prefix==p->cycle.prefix&&commit<=p->cycle.continuation_deadline_ns
                &&commit<=start+CYCLE_CAPTURE_BUDGET&&cycle_retry_relation(p,scene);
            if(!safe){
                p->cycle_retry_blocked|=scene->state==NG2_UNKNOWN&&prefix==p->cycle.prefix
                    &&commit<=p->cycle.continuation_deadline_ns&&commit<=start+CYCLE_CAPTURE_BUDGET?2:1;
                p->cycle_queued_valid=0;
                p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
            }else if(!p->cycle_retry_blocked){
                if(p->cycle_retry_waiting&&!p->cycle.pending){
                    cycle_retry_bind(p,scene,id,start,prefix,commit);return 1;
                }
                p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
                p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
            }
        }
        if(p->cycle_retry_waiting&&!p->cycle.pending&&p->cycle_retry_blocked)
            cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);
        return 1;
    }
    if(p->cycle_full_data_active&&p->cycle.pending){
        NG2Motion still={0};
        if(commit>p->cycle.continuation_deadline_ns){
            cycle_failure(p,commit,NG2_RING_DEADLINE,NG2_REASON_LATE);return 1;
        }
        if(id<=p->cycle.capture_id||start<p->cycle.capture_start_ns)return 1;
        if(!cycle_full_data_relation(p,scene,&still)){
            /* Let the bound worker's target/candidate win before a deferred
             * invalidation. Unsafe observations never become queued input. */
            p->cycle_full_data_blocked=1;p->cycle_queued_valid=0;return 1;
        }
        if(!p->cycle_full_data_blocked&&!p->cycle_queued_valid){
            /* One bounded FIFO retains the first eligible exposure while
             * its predecessor runs. Later palette flicker cannot erase it. */
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
        }
        return 1;
    }
    if(p->cycle_full_framing){
        if(p->cycle_full_framing==4){
            if(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE){
                NG2ControllerEvent *e=event(p);uint64_t horizon=p->cycle.continuation_deadline_ns;
                uint64_t hold=p->cycle.hold_started_ns,sync=p->cycle_sync_deadline;
                resolve_move(p,scene,id,start,end);
                if(!p->finish_requested&&p->s.input_state==0&&e&&e->motion==NG2_MOVED
                    &&e->dx==dx[p->cycle_full_choice.direction]&&e->dy==dy[p->cycle_full_choice.direction]){
                    NG2Scene source=*scene;uint64_t source_id=id,source_start=start;
                    if(p->cycle_queued_valid&&p->cycle.queued_capture_id>p->command.source_capture_id
                        &&p->cycle.queued_capture_id<id&&p->cycle.queued_prefix==prefix
                        &&p->cycle.queued_capture_start_ns>=p->ack_ns&&start>p->cycle_move_data_end
                        &&commit<=p->cycle.queued_capture_start_ns+CYCLE_CAPTURE_BUDGET&&commit<=horizon
                        &&cycle_moved_data_relation(&p->cycle_queued_scene,scene,p->cycle_full_choice.direction)){
                        source=p->cycle_queued_scene;source_id=p->cycle.queued_capture_id;
                        source_start=p->cycle.queued_capture_start_ns;
                    }
                    p->cycle_full_framing=0;p->cycle_full_source_valid=p->cycle_full_data_active=0;
                    cycle_latch(p,&source,commit);cycle_bind(p,&source,source_id,source_start,prefix);
                    p->cycle.hold_started_ns=hold;p->cycle_sync_deadline=minimum(p->cycle_sync_deadline,sync);
                    p->cycle.continuation_deadline_ns=minimum(p->cycle.continuation_deadline_ns,horizon);
                    p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,p->cycle.continuation_deadline_ns);
                }else if(!p->finish_requested&&p->s.input_state==3){
                    /* Latest-only until confirmation; no immutable worker has
                     * started. Publish the existing queued ID as its pixel lease. */
                    p->cycle_queued_valid=0;
                    p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
                    if(prefix==p->command.id&&start>=p->ack_ns&&commit<=horizon
                        &&commit<=start+CYCLE_CAPTURE_BUDGET
                        &&cycle_moved_data_local(scene,p->cycle_full_choice.direction)){
                        p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;p->cycle_move_data_end=end;
                        p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
                    }
                }
            }
            return 1;
        }else{
            NG2Motion still={0};int validation=NG2_REVALIDATE_NONE;
            if(commit>p->cycle.continuation_deadline_ns)validation=NG2_REVALIDATE_TIMING;
            else if(prefix!=p->cycle.prefix||p->s.input_state>1)validation=NG2_REVALIDATE_STATE;
            else if(id>p->cycle.capture_id&&start>=p->cycle.release_after_ns)
                validation=cycle_full_static(p,scene,&still);
            else return 1;
            if((validation==NG2_REVALIDATE_PROTECTED||validation==NG2_REVALIDATE_MOTION)
                &&cycle_full_entered_refresh(p,scene,id,start,end,prefix,commit))return 1;
            if((validation==NG2_REVALIDATE_PROTECTED||validation==NG2_REVALIDATE_MOTION)
                &&cycle_full_waitable(p,scene,&still)){
                size_t samples=p->sample_count;
                diagnostic_comparison(p,id,validation,&still);
                if(validation==NG2_REVALIDATE_PROTECTED&&cycle_full_data_relation(p,scene,&still)){
                    cycle_full_data_bind(p,scene,id,start,prefix,commit);return 1;
                }
                clear_slots(p);clear_model(p);p->sample_count=samples;
                p->proof_capture_id=p->proof_deadline=0;p->cycle_full_framing=1;
                p->s.phase=NG2_PHASE_SYNC;
                return 1;
            }
            diagnostic_comparison(p,id,validation,&still);
            if(validation){cycle_record_rejection(p,scene,id,validation);
                cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;}
            if(p->cycle_full_framing==1){
                clear_slots(p);p->cycle_full_framing=2;p->proof_capture_id=id;
                p->s.reason=NG2_REASON_NONE;p->s.phase=NG2_PHASE_SYNC;
                p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->sync_ns=p->latest_verified_ns;
                if(p->cycle_sync_deadline>=12*SECOND)
                    p->sync_ns=minimum(p->sync_ns,p->cycle_sync_deadline-12*SECOND);
            }
            add_sample(p,scene,id,start,end);return 1;
        }
    }
    if(p->cycle.state==NG2_CYCLE_OBSERVE_MORE
        &&!p->s.input_state&&!p->cycle.candidate_latched&&!p->cycle_restart_unproved
        &&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_VISIBLE&&id>p->cycle.capture_id
        &&start>=p->cycle.release_after_ns&&prefix==p->cycle.prefix){
        /* A new, qualified FULL observation replaces partial evidence.
         * Normal binding revokes the old credit and starts classification of
         * this source; no old MOVE or input horizon is restored. */
        cycle_latch(p,scene,commit);cycle_bind(p,scene,id,start,prefix);return 1;
    }
    if(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE){
        if(scene->state==NG2_UNKNOWN&&start>=p->ack_ns
            &&end<=p->motion_wait.deadline_ns&&commit<=p->motion_wait.deadline_ns){
            /* A transient HUD occlusion is no movement or next-input proof.
             * Keep this known ACK's source and original visual budget. */
            phase_failure(p,NG2_RECOVERY_VISUAL_PHASE,end,id);clear_slots(p);return 1;
        }
        if(scene->state!=NG2_FLOOR){end_visual_wait(p);cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);}
        else{
            event(p)->observed_capture_id=id;resolve_move(p,scene,id,start,end);
            if(p->cycle.full_seen)end_visual_wait(p);
            if(p->s.input_state==0)clear_slots(p);
        }
    }else if(p->s.input_state==3&&start>=p->ack_ns){
        if(p->command.kind==NG2_ACTION_PAUSE&&scene->state==NG2_PAUSE){
            event(p)->observed_capture_id=id;end_visual_wait(p);p->s.paused=1;
            p->cycle.pause_capture_id=id;
        }else if(p->command.kind==NG2_ACTION_RESUME&&scene->state==NG2_FLOOR){
            event(p)->observed_capture_id=id;end_visual_wait(p);clear_model(p);
        }else if(p->command.kind==NG2_ACTION_RESTART&&scene->state==NG2_FLOOR
            &&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART&&p->cycle.intent_ns
            &&p->restart_pending&&p->restart_baseline_valid
            &&ng2_fingerprint_changed(p->restart_fingerprint,scene->fingerprint)){
            event(p)->observed_capture_id=id;end_visual_wait(p);p->restart_pending=0;
            ++p->s.restarts;p->cycle.next_floor_capture_id=id;
            if(p->restart_yield.s.enabled&&!p->restart_yield.s.invalid&&p->s.inputs>0){
                NG2RestartYield *y=&p->restart_yield;
                y->first_start=start;y->first_end=end;y->ack=p->ack_ns;
                y->s.new_floor_capture_id=id;y->s.new_floor_start_ns=start;
                y->s.restart_command_id=p->command.id;y->s.prefix=prefix;
                y->inputs=p->s.inputs;y->moves=p->s.moves;y->restarts=p->s.restarts;
                memcpy(y->first_fingerprint,scene->fingerprint,48);
                if(scene->goods!=NG2_GOODS_UNKNOWN)y->required|=scene->goods==NG2_GOODS_PARTIAL?1:2;
            }
        }else if(p->command.kind==NG2_ACTION_RESTART&&scene->state==NG2_FLOOR&&p->cycle_search_restart){
            int changed=p->restart_pending&&p->restart_baseline_valid
                &&commit-p->ack_ns<TRANSITION
                &&ng2_fingerprint_changed(p->restart_fingerprint,scene->fingerprint);
            event(p)->observed_capture_id=id;end_visual_wait(p);p->cycle_search_restart=0;
            p->restart_pending=0;
            if(changed){
                ++p->s.restarts;++p->cycle.level_id;reset_level(p,end);
            }else{
                /* Closing a known synth's UI wait is not new-level credit.
                 * Protect the visible goods, without retrying that restart. */
                p->cycle_restart_unproved=1;p->restart_baseline_valid=0;p->s.reason=NG2_REASON_RESTART;
            }
        }
    }
    if(p->finish_requested)return 1;
    if(scene->goods==NG2_GOODS_VISIBLE){
        p->cycle.full_seen=1;p->s.goods=1;
        if(p->cycle.capture_id&&p->cycle.partial&&!p->cycle_queued_valid
            &&scene->state==NG2_FLOOR&&p->s.input_state==0){
            p->cycle_queued_scene=*scene;p->cycle_queued_valid=1;
            p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
        }
    }
    if(p->cycle.pending&&!p->cycle.capture_id&&p->s.input_state==0&&scene->state==NG2_FLOOR
        &&scene->goods!=NG2_GOODS_UNKNOWN){
        if(!p->s.walk_started_ns&&actual_gold(scene)){p->s.walk_started_ns=end;p->sync_ns=end;}
        cycle_bind(p,scene,id,start,prefix);
    }
    if(p->cycle.state==NG2_CYCLE_OBSERVE_MORE&&start>=p->cycle.release_after_ns){
        NG2Motion motion;int wait=0,validation;
        if(p->s.input_state||p->cycle.full_seen||p->cycle.candidate_latched
            ||commit>p->cycle.continuation_deadline_ns
            ||(!p->s.lead_confirmed&&level_inputs(p))){
            diagnostic_comparison(p,id,commit>p->cycle.continuation_deadline_ns?
                NG2_REVALIDATE_TIMING:NG2_REVALIDATE_STATE,NULL);
            cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);
        }else if((validation=cycle_partial_comparison(p,scene,&wait,&motion))!=NG2_REVALIDATE_NONE){
            diagnostic_comparison(p,id,validation,&motion);
            cycle_record_rejection(p,scene,id,validation);
            /* Only an unproved zero with every fixed static guard intact may
             * wait. No sample, source, horizon, credit or input is refreshed. */
            if(!wait){
                if(validation==NG2_REVALIDATE_PROTECTED
                    &&cycle_current_partial_start(p,scene,id,start,end,prefix,commit))return 1;
                if(cycle_rebind_exposed_partial(p,scene,id,start,prefix,commit))return 1;
                if(cycle_rebind_changed_partial(p,scene,id,start,end,prefix,commit))return 1;
                cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);
            }
        }else{
            diagnostic_comparison(p,id,NG2_REVALIDATE_NONE,&motion);
            clear_slots(p);p->cycle_partial_credit=1;p->cycle_credit_prefix=prefix;
            p->cycle.state=NG2_CYCLE_SEARCH;p->s.reason=NG2_REASON_NONE;p->s.goods=0;
            p->s.phase=NG2_PHASE_SYNC;p->s.next_target_ns=0;
            p->proof_capture_id=id;p->proof_deadline=0;p->proof_reacquire=0;
            if(p->s.lead_confirmed){
                if(p->recovery.mode!=NG2_RECOVERY_POST_MOVE){
                    ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;
                    p->recovery.mode=NG2_RECOVERY_POST_MOVE;p->sync_ns=p->latest_verified_ns;
                }
            }
            if(p->cycle_sync_deadline>=12*SECOND)
                p->sync_ns=minimum(p->sync_ns,p->cycle_sync_deadline-12*SECOND);
            add_sample(p,scene,id,start,end);
        }
    }
    if(cycle_holding(p))p->s.phase=NG2_PHASE_FINISH;
    return 1;
}
int ng2_controller_cycle_worker_begin(NG2Controller *p,uint64_t job,uint64_t capture,uint64_t prefix,uint64_t now){
    if(p&&p->irregular.enabled&&p->irregular.stage!=NG2_IRREGULAR_IDLE
        &&!(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&p->irregular.outcome_ns))return 0;
    if(!cycle_current(p,job,now)||!p->cycle.pending||p->cycle.state!=NG2_CYCLE_HOLD
        ||!capture||capture!=p->cycle.capture_id||prefix!=p->cycle.prefix)return 0;
    p->last_now=now;
    if(now>p->cycle.deadline_ns){
        if(!cycle_retry_wait(p,now,1))cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    p->cycle.worker_started_ns=now;p->cycle.deadline_ns=minimum(p->cycle.deadline_ns,now+CYCLE_WORKER_BUDGET);
    p->cycle.state=NG2_CYCLE_ASSESS;return 1;
}
static int initial_restart_assess(NG2Controller *p,const NG2RingResult *result,uint64_t now){
    NG2InitialRestart *initial=&p->initial_restart;int hint;
    if(initial->stage!=NG2_INITIAL_VETO||!initial->veto_job
        ||initial->veto_job!=p->cycle.job_id||initial->veto_capture!=p->cycle.capture_id
        ||initial->veto_prefix!=p->cycle.prefix)return 0;
    hint=cycle_result_positive_hint(result);
    if(hint<0){initial->stage=NG2_INITIAL_HELD;
        cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;}
    if(hint){
        initial->stage=NG2_INITIAL_HELD;restart_yield_invalidate(p);
        p->cycle.candidate_latched=1;p->cycle.outcome=NG2_RING_CANDIDATE;
        p->cycle.coverage=NG2_RING_COVERAGE_INCOMPLETE;p->cycle.state=NG2_CYCLE_HELD;
        p->s.reason=NG2_REASON_GOODS;return 1;
    }
    if(!initial->parent||now>=initial->parent){
        initial->stage=NG2_INITIAL_HELD;finish(p,now,NG2_REASON_RESTART);return 1;
    }
    /* A completed clean veto permits this explicit initial layout skip.
     * It is not an adopted negative shop or its durable restart intent. */
    p->cycle.outcome=NG2_RING_UNKNOWN;p->cycle.coverage=NG2_RING_COVERAGE_INCOMPLETE;
    p->cycle.state=NG2_CYCLE_SEARCH;p->cycle_queued_valid=0;
    p->cycle_partial_credit=p->cycle_refresh_safe=0;p->s.goods=0;p->s.reason=NG2_REASON_NONE;
    initial->stage=p->scene.state==NG2_PAUSE?NG2_INITIAL_RESTART:NG2_INITIAL_PAUSE;
    return 1;
}
static int cycle_assess(NG2Controller *p,uint64_t job,uint64_t capture,uint64_t prefix,
    uint64_t now,const NG2RingResult *result){
    int late=p&&p->cycle_enabled&&p->cycle_late_worker&&job&&job==p->cycle.job_id
        &&valid_time(now)&&now>=p->last_now;
    if(p&&p->irregular.enabled&&p->irregular.stage!=NG2_IRREGULAR_IDLE
        &&!(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&p->irregular.outcome_ns))return 0;
    if((!cycle_current(p,job,now)&&!late)||!((p->cycle.pending&&p->cycle.state==NG2_CYCLE_ASSESS)||late)
        ||capture!=p->cycle.capture_id||prefix!=p->cycle.prefix)return 0;
    p->last_now=now;
    if(!result||result->abi!=NG2_RING_ABI||result->size!=sizeof(*result)
        ||result->status>NG2_RING_KERNEL||result->outcome>NG2_RING_NEGATIVE
        ||result->coverage>NG2_RING_COVERAGE_COMPLETE||result->row_count<0||result->row_count>4
        ||result->partial_count<0||result->partial_count>12||result->partial_safe_no_positive>1
        ||result->selected_row < -1||result->selected_row>=result->row_count
        ||result->selected_partial < -1||result->selected_partial>=result->partial_count
        ||result->started_ns<p->cycle.worker_started_ns
        ||result->finished_ns<result->started_ns||result->finished_ns>now){
        if(late){p->cycle_late_worker=0;return 0;}
        cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;
    }
    if(p->cycle_late_worker){
        int hint=p->restart_yield.s.pending?restart_yield_positive_hint(result):cycle_result_positive_hint(result);p->cycle_late_worker=0;
        if(hint>0){p->cycle.candidate_latched=1;p->cycle.outcome=NG2_RING_CANDIDATE;p->s.reason=NG2_REASON_GOODS;return 1;}
        return 0; /* Frozen failures can retain hints, never retry or adopt absence. */
    }
    if(now>p->cycle.deadline_ns||result->finished_ns>p->cycle.deadline_ns||result->status==NG2_RING_DEADLINE){
        int hint=p->restart_yield.s.pending?restart_yield_positive_hint(result):cycle_result_positive_hint(result);
        if(hint<0){cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);p->cycle_late_worker=0;return 1;}
        if(hint){
            cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
            p->cycle_late_worker=0;
            p->cycle.candidate_latched=1;p->cycle.outcome=NG2_RING_CANDIDATE;p->s.reason=NG2_REASON_GOODS;
            return 1;
        }
        if(result->status==NG2_RING_OK||result->status==NG2_RING_DEADLINE){
            if(cycle_retry_wait(p,now,1))return 1;
        }
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 1;
    }
    if(result->status!=NG2_RING_OK){cycle_failure(p,now,(int)result->status,NG2_REASON_CAPTURE);return 1;}
    if(result->outcome==NG2_RING_NEGATIVE&&!cycle_negative_witness(p,result)){
        cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;
    }
    p->cycle.pending=0;p->cycle_refresh_safe=0;p->cycle.status=NG2_RING_OK;p->cycle.outcome=(int)result->outcome;
    p->cycle.coverage=(int)result->coverage;p->cycle.assessment_ns=now;
    if(result->outcome==NG2_RING_TARGET||result->outcome==NG2_RING_CANDIDATE){
        restart_yield_invalidate(p);
        p->cycle.candidate_latched=1;p->cycle_queued_valid=0;
        p->cycle_current_active=0;
        p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
        if(p->entry.active)p->entry.stage=6;
        if(p->lower.active)p->lower.stage=6;
        if(p->upper.active){p->upper.stage=6;p->upper.valid=0;}
        p->s.reason=NG2_REASON_GOODS;
        p->cycle.state=NG2_CYCLE_HELD;++p->cycle.completed_shops;return 1;
    }
    if(initial_restart_assess(p,result,now))return 1;
    if(p->restart_yield.s.pending){
        NG2RestartYield *y=&p->restart_yield;int hint=restart_yield_positive_hint(result);
        if(!restart_yield_basis(p,now)||hint<0){cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;}
        if(hint){
            restart_yield_invalidate(p);p->cycle.candidate_latched=1;p->cycle.outcome=NG2_RING_CANDIDATE;
            p->cycle.state=NG2_CYCLE_HELD;p->s.reason=NG2_REASON_GOODS;return 1;
        }
        y->done|=y->current_kind;p->cycle.state=NG2_CYCLE_HELD;
        /* A clean veto does not certify this new floor absent or complete.
         * Its next run will resume and observe it independently. */
        p->cycle.outcome=NG2_RING_UNKNOWN;p->cycle.coverage=NG2_RING_COVERAGE_INCOMPLETE;
        p->cycle_queued_valid=0;return 1;
    }
    if(cycle_current_assess(p,result,now))return 1;
    if(cycle_current_start(p,result,now))return 1;
    if(cycle_current_data_start(p,result,now))return 1;
    if(result->outcome==NG2_RING_UNKNOWN&&entry_result_safe(result)
        &&(result->row_count||result->partial_count)&&cycle_result_positive_hint(result)==0)
        cycle_data_yield_pause(p,now);
    if(p->cycle_retry_only){
        if(p->cycle_retry_data&&cycle_data_retry_wait(p,result,now))return 1;
        p->cycle_retry_waiting=0;
        if(p->cycle_retry_blocked){cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;}
        if(result->outcome!=NG2_RING_NEGATIVE){
            p->cycle_queued_valid=0;p->cycle.state=NG2_CYCLE_HELD;++p->cycle.completed_shops;return 1;
        }
    }
    if(p->cycle_full_data_active){
        if(p->cycle_full_data_blocked||now>p->cycle_full_parent){
            cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_SCREEN);return 1;
        }
        if(result->outcome==NG2_RING_UNKNOWN){
            if(!entry_result_safe(result)||(!result->row_count&&!result->partial_count)){
                p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
                p->cycle_queued_valid=0;p->cycle.state=NG2_CYCLE_HELD;++p->cycle.completed_shops;return 1;
            }
            if(p->cycle_queued_valid){
                NG2Scene queued=p->cycle_queued_scene;
                uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,queued_prefix=p->cycle.queued_prefix;
                cycle_full_data_bind(p,&queued,id,start,queued_prefix,now);return 1;
            }
            /* The one original observation has not been issued. Its exact
             * return path remains available, but needs a later direct proof
             * and a new fit. This never restores a consumed actual MOVE. */
            p->cycle_full_framing=1;p->cycle.state=NG2_CYCLE_OBSERVE_MORE;
            p->cycle.release_after_ns=now;return 1;
        }
        p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
        p->cycle_queued_valid=0;
    }
    if(upper_assess(p,result,now))return 1;
    if(entry_assess(p,result,now))return 1;
    if(lower_assess(p,result,now))return 1;
    if(cycle_full_admit(p,result,&p->cycle_full_choice)){
        p->cycle_full_spent=1;p->cycle_full_framing=1;
        p->cycle_full_source=p->cycle_anchor;p->cycle_full_source_valid=1;
        p->cycle_full_source_id=p->cycle.capture_id;p->cycle_full_source_start=p->cycle.capture_start_ns;
        p->cycle_full_source_prefix=p->cycle.prefix;p->cycle_full_parent=p->cycle.continuation_deadline_ns;
        p->cycle_full_data_active=p->cycle_full_data_blocked=0;
        p->cycle_full_old_ordinal=p->cycle_full_choice.direction==NG2_UP?
            p->cycle_up_command.ordinal:event(p)->command.ordinal;
        p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
    }
    if(cycle_data_retry_wait(p,result,now))return 1;
    if(p->cycle_full_spent&&result->outcome!=NG2_RING_NEGATIVE){
        p->cycle.state=NG2_CYCLE_HELD;++p->cycle.completed_shops;return 1;
    }
    if(cycle_framing_admit(p,result)){
        if(entry_start(p,result,now))return 1;
        /* Empty remains UNKNOWN/INCOMPLETE. This separate, one-input credit
         * needs a later independent stationary frame and a new future ticket;
         * it never certifies target absence or a completed shop. */
        p->cycle_framing_credit=1;p->cycle_queued_valid=0;
        p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
        p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;return 1;
    }
    if(p->cycle.partial&&result->outcome==NG2_RING_UNKNOWN&&result->partial_safe_no_positive==1
        &&result->coverage==NG2_RING_COVERAGE_INCOMPLETE&&!p->cycle.candidate_latched&&!p->cycle_restart_unproved){
        int r,s,refresh_safe=1,observed=result->row_count>0||result->partial_count>0;
        for(r=0;r<result->row_count;++r)for(s=0;s<3;++s)observed&=cycle_no_candidate(&result->rows[r].slots[s]);
        for(s=0;s<result->partial_count;++s)observed&=cycle_no_candidate(&result->partial[s]);
        for(r=0;r<result->row_count;++r)for(s=0;s<3;++s)refresh_safe&=cycle_binary_no_positive(&result->rows[r].slots[s]);
        for(s=0;s<result->partial_count;++s)refresh_safe&=cycle_binary_no_positive(&result->partial[s]);
        if(!observed){cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_GEOMETRY);return 1;}
        if(p->cycle_queued_valid){
            uint64_t id=p->cycle.queued_capture_id,start=p->cycle.queued_capture_start_ns,old_prefix=p->cycle.queued_prefix;
            ++p->cycle.job_id;p->cycle.pending=1;p->cycle.state=NG2_CYCLE_HOLD;
            p->cycle.worker_started_ns=p->cycle.assessment_ns=0;p->cycle_queued_valid=0;
            p->cycle.queued_capture_id=p->cycle.queued_capture_start_ns=p->cycle.queued_prefix=0;
            cycle_bind(p,&p->cycle_queued_scene,id,start,old_prefix);
            if(now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        }else if(!p->cycle.full_seen&&!p->cycle_pause_attempted){
            p->cycle_refresh_safe=refresh_safe;
            p->cycle.state=NG2_CYCLE_OBSERVE_MORE;p->cycle.release_after_ns=now;
        }else p->cycle.state=NG2_CYCLE_HELD;
        return 1;
    }
    p->cycle.state=result->outcome==NG2_RING_NEGATIVE&&!p->cycle_restart_unproved?
        NG2_CYCLE_NEGATIVE_PAUSE:NG2_CYCLE_HELD;
    if(p->cycle_restart_unproved)p->s.reason=NG2_REASON_RESTART;
    ++p->cycle.completed_shops;
    return 1;
}
int ng2_controller_cycle_assess(NG2Controller *p,uint64_t job,uint64_t capture,uint64_t prefix,
    uint64_t now,const NG2RingResult *result){
    int accepted;if(!p)return 0;
    p->cycle_assessing=1;accepted=cycle_assess(p,job,capture,prefix,now,result);p->cycle_assessing=0;
    return accepted;
}
int ng2_controller_cycle_durable(NG2Controller *p,uint64_t job,uint64_t capture,uint64_t prefix,uint64_t now){
    if(!cycle_current(p,job,now)||p->cycle.pending||p->cycle.durable_ns||p->cycle_storage_error
        ||capture!=p->cycle.capture_id||prefix!=p->cycle.prefix||!p->cycle.pause_capture_id
        ||p->s.input_state||p->scene.state!=NG2_PAUSE||!fresh(p,now)
        ||p->last_observed_prefix!=p->s.last_completed_id)return 0;
    p->last_now=now;p->cycle.durable_ns=now;
    if(p->cycle.outcome==NG2_RING_NEGATIVE&&!p->cycle_restart_unproved)p->cycle.state=NG2_CYCLE_NEGATIVE_PERSIST;
    return 1;
}
int ng2_controller_cycle_intent_commit(NG2Controller *p,uint64_t job,uint64_t command,
    uint64_t source,uint64_t prefix,uint64_t now){
    if(!cycle_current(p,job,now)||p->cycle.state!=NG2_CYCLE_NEGATIVE_RESTART
        ||p->cycle.outcome!=NG2_RING_NEGATIVE||p->cycle.status!=NG2_RING_OK
        ||!p->cycle.durable_ns||p->cycle.intent_ns||p->cycle_storage_error||p->cycle_restart_unproved
        ||p->s.input_state!=1||command!=p->command.id||command!=p->cycle.restart_command_id
        ||p->command.kind!=NG2_ACTION_RESTART||source!=p->command.source_capture_id
        ||prefix!=p->s.last_completed_id||prefix!=p->last_observed_prefix
        ||p->scene.state!=NG2_PAUSE||!p->scene.restart_label||!fresh(p,now)
        ||now>p->command.deadline_ns||now-p->s.started_ns>=180*SECOND
        ||(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND))return 0;
    p->last_now=now;p->cycle.intent_ns=now;return 1;
}
static int restart_yield_first_proof(const NG2Controller *p,uint64_t capture,uint64_t prefix,uint64_t now){
    const NG2RestartYield *y=&p->restart_yield;
    return y->s.enabled&&!y->s.invalid&&p->s.inputs>0&&y->first_start&&y->first_end&&y->ack
        &&capture==y->s.new_floor_capture_id&&prefix==y->s.restart_command_id&&prefix==y->s.prefix
        &&y->first_start>=y->ack&&y->first_end<=now&&now-y->first_start<=FRESH
        &&p->s.inputs==y->inputs&&p->s.moves==y->moves&&p->s.restarts==y->restarts
        &&ng2_fingerprint_changed(p->restart_fingerprint,y->first_fingerprint);
}
int ng2_controller_cycle_outcome_commit(NG2Controller *p,uint64_t job,uint64_t capture,uint64_t prefix,uint64_t now){
    int original=p&&restart_yield_first_proof(p,capture,prefix,now);
    if(!cycle_current(p,job,now)||p->cycle.state!=NG2_CYCLE_NEGATIVE_RESTART
        ||!capture||capture!=p->cycle.next_floor_capture_id||!p->cycle.intent_ns||!p->cycle.durable_ns
        ||p->cycle_storage_error||p->cycle.outcome_ns||p->s.input_state
        ||prefix!=p->s.last_completed_id||prefix!=p->last_observed_prefix
        ||(!original&&(p->scene.state!=NG2_FLOOR||!fresh(p,now)
            ||!ng2_fingerprint_changed(p->restart_fingerprint,p->scene.fingerprint)))
        ||now-p->s.started_ns>=180*SECOND
        ||(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND))return 0;
    p->last_now=now;p->cycle.outcome_ns=now;
    if(p->restart_yield.s.enabled&&!p->restart_yield.s.invalid&&p->s.inputs>0){
        NG2RestartYield *y=&p->restart_yield;
        if(!y->first_start||!y->first_end||!y->ack||p->cycle.status!=NG2_RING_OK
            ||p->cycle.outcome!=NG2_RING_NEGATIVE||p->cycle.coverage!=NG2_RING_COVERAGE_COMPLETE
            ||p->cycle.partial||p->cycle.candidate_latched){cycle_failure(p,now,NG2_RING_INVALID,NG2_REASON_RESTART);return 0;}
        y->prior=p->cycle;memcpy(y->fingerprint,p->restart_fingerprint,48);
        y->s.pending=1;y->s.old_job_id=job;y->s.restart_command_id=p->cycle.restart_command_id;
        y->s.new_floor_capture_id=capture;y->s.new_floor_start_ns=y->first_start;
        y->s.prefix=prefix;y->s.level_id=p->cycle.level_id+1;
        y->s.parent_deadline_ns=minimum(y->first_start+TRANSITION,session_bound(p));
        if(p->s.walk_started_ns)y->s.parent_deadline_ns=minimum(y->s.parent_deadline_ns,p->s.walk_started_ns+45*SECOND);
        y->inputs=p->s.inputs;y->moves=p->s.moves;y->restarts=p->s.restarts;
        if(p->scene.goods!=NG2_GOODS_UNKNOWN)y->required|=p->scene.goods==NG2_GOODS_PARTIAL?1:2;
    }
    ++p->cycle.level_id;
    p->cycle.state=NG2_CYCLE_SEARCH;p->cycle.candidate_latched=0;
    p->cycle_pause_attempted=p->cycle_storage_error=p->cycle_partial_credit=p->cycle_framing_credit=p->cycle_queued_valid=0;
    p->s.goods=0;p->s.reason=NG2_REASON_NONE;reset_level(p,now);
    remember_level_restart(p,p->cycle.restart_command_id,capture,prefix);
    if(p->restart_yield.s.pending)return 1;
    if(p->scene.goods!=NG2_GOODS_UNKNOWN){
        cycle_latch(p,&p->scene,now);
        cycle_bind(p,&p->scene,p->s.last_capture_id,p->s.last_capture_start_ns,prefix);
    }else{
        begin_initial_view(p,&p->scene,p->s.last_capture_id,p->s.last_capture_start_ns,p->s.last_capture_end_ns);
        start_floor(p,&p->scene,p->s.last_capture_id,p->s.last_capture_end_ns);
    }
    return 1;
}
int ng2_controller_cycle_fail(NG2Controller *p,uint64_t job,uint64_t now,int32_t reason){
    if(!cycle_current(p,job,now))return 0;
    if(reason<1||reason>NG2_REASON_GEOMETRY)reason=NG2_REASON_CAPTURE;
    p->last_now=now;cycle_failure(p,now,NG2_RING_KERNEL,reason);return 1;
}
int ng2_controller_cycle_storage_failed(NG2Controller *p,uint64_t job,uint64_t now){
    if(!cycle_current(p,job,now))return 0;
    p->last_now=now;p->cycle_storage_error=1;
    if(p->cycle.next_floor_capture_id)p->cycle_pause_attempted=0;
    cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_CAPTURE);return 1;
}

/* Opt-in irregular observations are immutable, same-call companions. They
 * never replace normal Scene/Motion, and NONE grants no input authority. */
static int irregular_observation_ok(const NG2IrregularObservation *o){
    int i;
    if(!o||o->abi_version!=1||o->struct_size!=sizeof(*o)||o->kind<0||o->kind>3
        ||o->glyph_intersection<0||o->glyph_union<o->glyph_intersection||o->glyph_union>6480
        ||o->hud_mask<0||o->hud_mask>15||o->empty_hearts<0||o->empty_hearts>3
        ||o->matches<0||o->matches>2||o->left<0||o->top<0||o->width<0||o->height<0
        ||o->left>896||o->top>414||o->width>896-o->left||o->height>414-o->top
        ||o->enemy_mask>15)return 0;
    for(i=0;i<3;++i)if(o->heart_inter[i]<0||o->heart_union[i]<o->heart_inter[i]
        ||o->heart_inter[i]>382||o->heart_union[i]>625||o->heart_red[i]<0||o->heart_red[i]>306
        ||o->heart_dark[i]<0||o->heart_dark[i]>306
        ||o->heart_bright[i]<0||o->heart_bright[i]>306)return 0;
    for(i=0;i<4;++i)if(o->enemy_matches[i]<0||o->enemy_matches[i]>2
        ||o->enemy_inter[i]<0||o->enemy_union[i]<o->enemy_inter[i]||o->enemy_union[i]>5304
        ||o->enemy_left[i]<0||o->enemy_left[i]>896||o->enemy_top[i]<0||o->enemy_top[i]>414
        ||o->enemy_width[i]<0||o->enemy_width[i]>896-o->enemy_left[i]
        ||o->enemy_height[i]<0||o->enemy_height[i]>414-o->enemy_top[i]
        ||o->enemy_body_luma[i]<0||o->enemy_body_luma[i]>696
        ||o->enemy_body_saturation[i]<0||o->enemy_body_saturation[i]>696
        ||o->enemy_red_outside[i]<0||o->enemy_red_outside[i]>5304
        ||o->enemy_heart_count[i]<0||o->enemy_heart_count[i]>3)return 0;
    return 1;
}
static int irregular_death_present(const NG2IrregularObservation *o){
    return irregular_observation_ok(o)&&(o->matches==1||o->matches==2)
        &&o->left==312&&o->top==312&&o->width==270&&o->height==24
        &&o->glyph_intersection<=522&&o->glyph_union>=522&&100*o->glyph_intersection>=64*o->glyph_union
        &&(o->matches==2||100*o->glyph_intersection>=90*522);
}
static int irregular_death(const NG2IrregularObservation *o){
    int i;
    if(!irregular_death_present(o)||o->kind!=NG2_IRREGULAR_IMAGE_DEATH
        ||o->matches!=1||o->hud_mask!=15||o->empty_hearts!=3
        ||o->left!=312||o->top!=312||o->width!=270||o->height!=24
        ||o->glyph_union<522||100*o->glyph_intersection<64*o->glyph_union
        ||100*o->glyph_intersection<90*522)return 0;
    for(i=0;i<3;++i)if(o->heart_union[i]<382
        ||100*o->heart_inter[i]<90*o->heart_union[i]||100*o->heart_inter[i]<95*382
        ||o->heart_red[i]<225||o->heart_dark[i]<192||o->heart_bright[i]>48)return 0;
    return 1;
}
/* Reuse the original companion validation and death-presence test. A normal
 * Scene alone cannot contradict an unsupported or malformed UI companion. */
static int restart_yield_ui_source(const NG2Controller *p,uint64_t id,uint64_t start,uint64_t now,int same_call){
    return p->irregular.enabled&&(!same_call||p->irregular_call)&&p->irregular_observation_valid
        &&p->irregular_observation_id==id&&now>=start&&now-start<=FRESH
        &&irregular_observation_ok(&p->irregular_observation)
        &&!irregular_death_present(&p->irregular_observation)
        &&p->irregular_observation.kind!=NG2_IRREGULAR_IMAGE_DEATH
        &&p->irregular_observation.kind!=NG2_IRREGULAR_IMAGE_RESTART;
}
static int irregular_restart(const NG2IrregularObservation *o){
    return irregular_observation_ok(o)&&o->kind==NG2_IRREGULAR_IMAGE_RESTART&&o->matches==1
        &&o->left>=160&&o->left<=555&&o->top>=60&&o->top<=332
        &&o->width==181&&o->height==28&&o->glyph_intersection<=223&&o->glyph_union>=223
        &&o->glyph_union-223+o->glyph_intersection>=212
        &&o->glyph_union-223+o->glyph_intersection<=237
        &&100*o->glyph_intersection>=94*o->glyph_union&&100*o->glyph_intersection>=95*223;
}
static int irregular_enemy(const NG2IrregularObservation *o,int d){
    int j=d-1,n,cx,cy,w,h,l,t;
    if(d<1||d>4||!irregular_observation_ok(o)||o->kind!=NG2_IRREGULAR_IMAGE_ENEMY
        ||o->hud_mask!=15||!(o->enemy_mask&(1u<<j))||o->enemy_matches[j]!=1)return 0;
    n=o->enemy_heart_count[j];cx=448+36*dx[d];cy=207+36*dy[d];
    w=o->enemy_width[j];h=o->enemy_height[j];l=o->enemy_left[j];t=o->enemy_top[j];
    return n>=1&&n<=3&&w>=15+17*(n-1)&&w<=15+19*(n-1)&&h>=13&&h<=14
        &&l>=cx-68&&l+w<=cx+68&&t>=cy-43&&t+h<=cy-4
        &&abs(2*l+w-2*cx)<=12&&2*t+h-2*cy>=-64&&2*t+h-2*cy<=-24
        &&o->enemy_inter[j]<=137*n&&o->enemy_union[j]>=137*n&&o->enemy_red_outside[j]==o->enemy_union[j]-137*n
        &&o->enemy_red_outside[j]<=64&&100*o->enemy_inter[j]>=90*o->enemy_union[j]
        &&100*o->enemy_inter[j]>=93*137*n
        &&o->enemy_body_luma[j]>=48&&o->enemy_body_saturation[j]>=96;
}
static int irregular_active(const NG2Controller *p){
    return p->irregular.enabled&&p->irregular.stage!=NG2_IRREGULAR_IDLE;
}
static void irregular_clear_first(NG2Controller *p){
    p->irregular_first_id=p->irregular_first_start=p->irregular_first_end=p->irregular_first_command=0;
    if(!irregular_active(p))p->irregular.proof_capture_id=p->irregular.before_capture_id=0;
}
static void irregular_frame(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                            uint64_t start,uint64_t end,uint64_t prefix){
    p->scene=*scene;p->have_scene=1;p->last_observed_prefix=prefix;
    p->s.last_capture_id=id;p->s.last_capture_start_ns=start;p->s.last_capture_end_ns=end;
    p->s.paused=scene->state==NG2_PAUSE;++p->s.accepted_frames;p->irregular.prefix=prefix;
}
static void irregular_keep_goods(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                                  uint64_t start,uint64_t end,uint64_t prefix){
    if(p->irregular_goods_id||scene->state!=NG2_FLOOR||scene->goods==NG2_GOODS_UNKNOWN)return;
    p->irregular_goods=*scene;p->irregular_goods_id=id;p->irregular_goods_start=start;
    p->irregular_goods_end=end;p->irregular_goods_prefix=prefix;
    /* In OUTCOME this triple is only a bounded raw-image retention hint.
     * There is no normal job, pending worker, or input permission yet. */
    p->cycle.queued_capture_id=id;p->cycle.queued_capture_start_ns=start;p->cycle.queued_prefix=prefix;
    p->cycle_queued_valid=0;
}
static void irregular_hold(NG2Controller *p,uint64_t now,int held){
    if(!p->irregular.enabled)return;
    p->irregular.stage=NG2_IRREGULAR_HELD;
    if(!p->irregular.held_reason||held==NG2_IRREGULAR_CANDIDATE||held==NG2_IRREGULAR_UNKNOWN_INPUT)
        p->irregular.held_reason=held;
    p->irregular.prefix=p->s.last_completed_id;p->preparation_epoch=0;
    if(p->s.input_state==1)not_sent(p,now,NG2_REASON_SCREEN);
    clear_slots(p);clear_model(p);p->proof_capture_id=p->proof_deadline=0;
    if(p->s.input_state==3)end_visual_wait(p);
    if(!p->irregular_ring_pending&&p->s.input_state!=2&&!p->s.terminal)
        terminal(p,now,held==NG2_IRREGULAR_UNKNOWN_INPUT?NG2_REASON_UNKNOWN_INPUT:
            held==NG2_IRREGULAR_CANDIDATE?NG2_REASON_GOODS:
            held==NG2_IRREGULAR_STORAGE?NG2_REASON_CAPTURE:
            held==NG2_IRREGULAR_LIMIT?NG2_REASON_LIMIT:NG2_REASON_SCREEN);
}
static void irregular_start(NG2Controller *p,int kind,uint64_t id,uint64_t now){
    int episodes=p->irregular.episodes+1;uint64_t first=p->irregular_first_id;
    uint64_t before=p->command.kind==NG2_ACTION_MOVE?p->command.source_capture_id:p->irregular_live_id;
    uint64_t parent=minimum(now+TRANSITION,session_bound(p));
    if(p->s.walk_started_ns)parent=minimum(parent,p->s.walk_started_ns+45*SECOND);
    memset(&p->irregular,0,sizeof(p->irregular));p->irregular.abi_version=1;
    p->irregular.struct_size=sizeof(p->irregular);p->irregular.enabled=1;
    p->irregular.kind=kind;p->irregular.episodes=episodes;p->irregular.episode_id=(uint64_t)episodes;
    p->irregular.trigger_capture_id=id;p->irregular.before_capture_id=before;
    p->irregular.live_baseline_capture_id=p->irregular_live_id;
    p->irregular.proof_capture_id=kind==NG2_IRREGULAR_STALLED?first:0;
    p->irregular.prefix=p->irregular_trigger_prefix=p->s.last_completed_id;
    p->irregular.trigger_ns=now;p->irregular.parent_deadline_ns=parent;
    p->irregular_floor_start=p->irregular_floor_end=p->irregular_floor_prefix=0;
    p->irregular_goods_id=p->irregular_goods_start=p->irregular_goods_end=p->irregular_goods_prefix=0;
    p->irregular_restart_ui=0;
    memcpy(p->irregular_baseline,p->irregular_live.fingerprint,48);
    p->irregular_move_before=p->before;
    p->irregular_ring_pending=p->cycle.pending!=0;
    p->irregular_ring_job=p->cycle.job_id;p->irregular_ring_capture=p->cycle.capture_id;
    p->irregular_ring_prefix=p->cycle.prefix;p->irregular_ring_deadline=p->cycle.deadline_ns;
    p->irregular.stage=p->irregular_ring_pending?NG2_IRREGULAR_QUIESCE:NG2_IRREGULAR_CHECKPOINT;
    not_sent(p,now,NG2_REASON_SCREEN);if(p->s.input_state==3)end_visual_wait(p);
    clear_slots(p);clear_model(p);clear_stationary_wait(p);
    p->proof_capture_id=p->proof_deadline=p->preparation_epoch=0;
    p->entry.active=p->lower.active=0;p->cycle_partial_credit=p->cycle_framing_credit=0;
    p->cycle_full_framing=p->cycle_full_source_valid=p->cycle_full_data_active=0;
    p->passage_wait_kind=0;p->gate_refresh_state=0;p->terrain_refresh_active=p->observation_refresh_active=0;
    p->restart_intent=p->restart_pending=0;p->s.phase=NG2_PHASE_FINISH;
    p->cycle.state=NG2_CYCLE_HELD;
    if(p->cycle.candidate_latched)irregular_hold(p,now,NG2_IRREGULAR_CANDIDATE);
    else if(!p->irregular_live_id)irregular_hold(p,now,NG2_IRREGULAR_BASELINE_UNAVAILABLE);
    else if(p->s.restarts>=12||p->s.inputs>=16||episodes>12||now>=parent)
        irregular_hold(p,now,NG2_IRREGULAR_LIMIT);
}
static int irregular_blocked(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                             uint64_t start,uint64_t end,const NG2Motion *motion){
    const NG2ControllerEvent *e=event(p);int i,d=p->command.direction;
    uint64_t earliest=maximum(p->ack_ns,p->command.target_ns+80000000);
    if(!p->irregular.enabled||irregular_active(p))return 0;
    if(motion->kind!=NG2_BLOCKED||motion->dx||motion->dy){
        if(motion->kind==NG2_MOVED)irregular_clear_first(p);
        return 0;
    }
    if(!p->irregular_call||!p->irregular_observation_valid||p->irregular_observation_id!=id
        ||!irregular_enemy(&p->irregular_observation,d)||!p->irregular_lead_before
        ||!p->s.lead_confirmed||!p->command_period||p->s.input_state!=3
        ||!p->motion_wait.active||p->finish_requested||p->cycle.candidate_latched
        ||p->s.last_completed_id!=p->command.id||p->last_observed_prefix!=p->command.id
        ||!e||e->outcome!=2||!e->begin_ns||e->end_ns!=p->ack_ns
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||(tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR&&tile(scene,dx[d],dy[d])!=NG2_TILE_UNKNOWN)
        ||protected_at(&p->before,0,0)||protected_at(&p->before,dx[d],dy[d])
        ||protected_at(scene,0,0)||protected_at(scene,dx[d],dy[d])){
        irregular_clear_first(p);return 0;
    }
    for(i=0;i<NG2_TILE_COUNT;++i)if(p->before.protected_cells[i]!=scene->protected_cells[i]
        ||((p->before.tiles[i]==NG2_TILE_GOLD||p->before.tiles[i]==NG2_TILE_ITEM
                ||scene->tiles[i]==NG2_TILE_GOLD||scene->tiles[i]==NG2_TILE_ITEM)
            &&p->before.tiles[i]!=scene->tiles[i])){irregular_clear_first(p);return 0;}
    if(!p->irregular_first_id){
        if(p->motion_wait.attempts>=MOTION_ASSESSMENTS||start>p->motion_wait.deadline_ns
            ||p->command_period>p->motion_wait.deadline_ns-start){irregular_clear_first(p);return 0;}
        p->irregular_first_id=id;p->irregular_first_start=start;p->irregular_first_end=end;
        p->irregular_first_command=p->command.id;p->irregular_first_enemy=p->irregular_observation;
        p->irregular.proof_capture_id=id;p->irregular.before_capture_id=p->command.source_capture_id;
        p->irregular.live_baseline_capture_id=p->irregular_live_id;return 1;
    }
    if(p->irregular_first_command!=p->command.id||id<=p->irregular_first_id
        ||start<=p->irregular_first_end){irregular_clear_first(p);return 0;}
    if(start-p->irregular_first_start<p->command_period||start-earliest<p->command_period){
        if(p->motion_wait.attempts<MOTION_ASSESSMENTS)return 1;
        irregular_clear_first(p);return 0;
    }
    irregular_start(p,NG2_IRREGULAR_STALLED,id,p->observe_now);return 1;
}
int ng2_controller_enable_irregular(NG2Controller *p){
    if(!p||!p->cycle_enabled||p->irregular.enabled||p->s.capture_count||p->have_scene||p->event_count)return 0;
    p->irregular.abi_version=1;p->irregular.struct_size=sizeof(p->irregular);p->irregular.enabled=1;return 1;
}
int ng2_controller_irregular_status(const NG2Controller *p,NG2ControllerIrregularStatus *out){
    if(!p||!out)return 0;
    *out=p->irregular;out->abi_version=1;out->struct_size=sizeof(*out);return 1;
}
static int irregular_current(NG2Controller *p,uint64_t episode,uint64_t now){
    return p&&p->irregular.enabled&&episode&&episode==p->irregular.episode_id
        &&valid_time(now)&&now>=p->last_now&&!p->s.terminal;
}
int ng2_controller_irregular_ring_settled(NG2Controller *p,uint64_t episode,uint64_t job,
    uint64_t capture,uint64_t prefix,const NG2RingResult *r,uint64_t now){
    int positive;
    if(!p||!p->irregular.enabled||episode!=p->irregular.episode_id||!episode
        ||!p->irregular_ring_pending||job!=p->irregular_ring_job
        ||capture!=p->irregular_ring_capture||prefix!=p->irregular_ring_prefix
        ||p->s.terminal||p->irregular.held_reason==NG2_IRREGULAR_CONTROL_INVALID
        ||p->irregular.held_reason==NG2_IRREGULAR_UNKNOWN_INPUT
        ||!valid_time(now)||now<p->last_now)return 0;
    p->last_now=now;p->irregular_ring_pending=0;p->cycle.pending=0;
    if(!r||r->abi!=NG2_RING_ABI||r->size!=sizeof(*r)||r->status>NG2_RING_KERNEL
        ||r->outcome>NG2_RING_NEGATIVE||r->coverage>NG2_RING_COVERAGE_COMPLETE
        ||r->row_count<0||r->row_count>4||r->partial_count<0||r->partial_count>12
        ||r->selected_row < -1||r->selected_row>=r->row_count
        ||r->selected_partial < -1||r->selected_partial>=r->partial_count
        ||r->partial_safe_no_positive>1
        ||r->started_ns<p->cycle.worker_started_ns||r->finished_ns<r->started_ns||r->finished_ns>now){
        irregular_hold(p,now,NG2_IRREGULAR_CLASSIFICATION);return 1;}
    positive=r->status==NG2_RING_OK&&(r->outcome==NG2_RING_TARGET||r->outcome==NG2_RING_CANDIDATE);
    if(positive){p->cycle.candidate_latched=1;irregular_hold(p,now,NG2_IRREGULAR_CANDIDATE);return 1;}
    if(r->status!=NG2_RING_OK||now>p->irregular_ring_deadline||now>p->irregular.parent_deadline_ns){
        irregular_hold(p,now,NG2_IRREGULAR_CLASSIFICATION);return 1;}
    if(p->irregular.stage==NG2_IRREGULAR_QUIESCE)p->irregular.stage=NG2_IRREGULAR_CHECKPOINT;
    else if(p->irregular.stage==NG2_IRREGULAR_HELD)irregular_hold(p,now,p->irregular.held_reason);
    return 1;
}
int ng2_controller_irregular_durable(NG2Controller *p,uint64_t episode,uint64_t capture,
                                     uint64_t prefix,uint64_t now){
    if(!irregular_current(p,episode,now)||p->irregular.stage!=NG2_IRREGULAR_CHECKPOINT
        ||p->irregular_ring_pending||p->cycle.candidate_latched||p->irregular.durable_ns
        ||capture!=p->irregular.trigger_capture_id||prefix!=p->irregular_trigger_prefix
        ||prefix!=p->s.last_completed_id||p->s.input_state)return 0;
    p->last_now=now;
    if(now>p->irregular.parent_deadline_ns){irregular_hold(p,now,NG2_IRREGULAR_DEADLINE);return 0;}
    p->irregular.durable_ns=now;p->irregular.stage=p->irregular.kind==NG2_IRREGULAR_DEATH?
        NG2_IRREGULAR_DEATH_CONTINUE:NG2_IRREGULAR_PAUSE;return 1;
}
static int irregular_ui(const NG2Controller *p,int kind){
    const NG2IrregularObservation *o=&p->irregular_observation;
    if(!p->have_scene||p->last_observed_prefix!=p->s.last_completed_id
        ||!p->irregular_observation_valid||p->irregular_observation_id!=p->s.last_capture_id)return 0;
    if(kind==NG2_ACTION_DEATH_CONTINUE)return p->irregular_observation_valid&&irregular_death(o);
    if(p->irregular_observation_valid&&irregular_death_present(o))return 0;
    if(kind==NG2_ACTION_PAUSE)return p->scene.state==NG2_FLOOR
        &&!(p->irregular_observation_valid&&irregular_death(o));
    if(kind!=NG2_ACTION_RESTART)return 0;
    if(p->scene.state==NG2_PAUSE&&p->scene.restart_label)return 1;
    return p->irregular.kind==NG2_IRREGULAR_DEATH&&p->irregular_menu_ready
        &&p->irregular_observation_valid&&irregular_restart(o)
        &&abs(o->left-p->irregular_menu.left)<=2&&abs(o->top-p->irregular_menu.top)<=2;
}
static int irregular_restart_ticket(const NG2Controller *p){
    if(p->command.kind!=NG2_ACTION_RESTART||p->command.id!=p->irregular.restart_command_id
        ||!irregular_ui(p,NG2_ACTION_RESTART))return 0;
    /* Equal points do not make two different UI kinds interchangeable. */
    if(p->irregular_restart_ui==1)return p->scene.state==NG2_PAUSE&&p->scene.restart_label
        &&p->command.x==144&&p->command.y==448;
    return p->irregular_restart_ui==2&&p->scene.state!=NG2_PAUSE
        &&p->command.x==400-p->irregular_observation.top
        &&p->command.y==p->irregular_observation.left+91;
}
int ng2_controller_irregular_intent_commit(NG2Controller *p,uint64_t episode,uint64_t command,
    uint64_t source,uint64_t prefix,uint64_t now){
    int kind;
    if(!irregular_current(p,episode,now)||p->irregular.stage==NG2_IRREGULAR_HELD
        ||!p->irregular.durable_ns||p->irregular_ring_pending||p->cycle.candidate_latched
        ||p->s.input_state!=1||command!=p->command.id||source!=p->command.source_capture_id
        ||prefix!=p->s.last_completed_id||prefix!=p->last_observed_prefix
        ||now>p->command.deadline_ns||now>p->irregular.parent_deadline_ns||!fresh(p,now))return 0;
    kind=p->command.kind;
    if(!irregular_ui(p,kind))return 0;
    if(kind==NG2_ACTION_DEATH_CONTINUE&&p->irregular.stage==NG2_IRREGULAR_DEATH_CONTINUE
        &&command==p->irregular.continue_command_id&&!p->irregular.continue_intent_ns)
        p->irregular.continue_intent_ns=now;
    else if(kind==NG2_ACTION_RESTART&&p->irregular.stage==NG2_IRREGULAR_RESTART_READY
        &&command==p->irregular.restart_command_id&&!p->irregular.restart_intent_ns
        &&(p->irregular.kind!=NG2_IRREGULAR_DEATH||p->irregular.continue_outcome_ns)
        &&irregular_restart_ticket(p))
        p->irregular.restart_intent_ns=now;
    else return 0;
    p->last_now=now;return 1;
}
int ng2_controller_irregular_outcome_commit(NG2Controller *p,uint64_t episode,int32_t kind,
    uint64_t command,uint64_t capture,uint64_t prefix,uint64_t now){
    if(!irregular_current(p,episode,now)||p->irregular.stage==NG2_IRREGULAR_HELD
        ||p->cycle.candidate_latched||p->s.input_state||prefix!=p->s.last_completed_id
        ||prefix!=p->last_observed_prefix||now>p->irregular.parent_deadline_ns)return 0;
    if(kind==NG2_ACTION_DEATH_CONTINUE&&p->irregular.stage==NG2_IRREGULAR_WAIT_MENU
        &&command==p->irregular.continue_command_id&&capture==p->irregular.continue_capture_id
        &&capture&&p->irregular.continue_intent_ns&&!p->irregular.continue_outcome_ns){
        p->irregular.continue_outcome_ns=now;
        if(fresh(p,now)&&irregular_ui(p,NG2_ACTION_PAUSE))p->irregular.stage=NG2_IRREGULAR_PAUSE;
        else if(fresh(p,now)&&irregular_ui(p,NG2_ACTION_RESTART))p->irregular.stage=NG2_IRREGULAR_RESTART_READY;
    }else if(kind==NG2_ACTION_RESTART&&p->irregular.stage==NG2_IRREGULAR_OUTCOME
        &&command==p->irregular.restart_command_id&&capture==p->irregular.next_floor_capture_id
        &&capture&&p->irregular.restart_intent_ns&&!p->irregular.outcome_ns
        &&p->irregular_floor.state==NG2_FLOOR&&p->irregular_floor_prefix==prefix
        &&p->irregular_floor_end>p->irregular_floor_start
        &&ng2_fingerprint_changed(p->irregular_baseline,p->irregular_floor.fingerprint)){
        p->irregular.outcome_ns=now;++p->s.restarts;++p->cycle.level_id;
        reset_level(p,now);remember_level_restart(p,command,capture,prefix);
        begin_initial_view(p,&p->irregular_floor,capture,p->irregular_floor_start,p->irregular_floor_end);
        p->irregular_live=p->irregular_floor;p->irregular_live_id=capture;
        p->s.goods=0;p->cycle.state=NG2_CYCLE_SEARCH;p->cycle.pending=0;
        p->cycle_pause_attempted=p->cycle_storage_error=0;
        /* The accepted first floor is immutable evidence while the writer
         * drains. A later UNKNOWN is no permission to discard its products.
         * Binding retains the source's own clocks and normal worker bounds;
         * this never installs old pixels as current UI authority. */
        if(p->irregular_goods_id){
            cycle_latch(p,&p->irregular_goods,now);
            cycle_bind(p,&p->irregular_goods,p->irregular_goods_id,
                p->irregular_goods_start,p->irregular_goods_prefix);
        }
    }else return 0;
    p->last_now=now;return 1;
}
int ng2_controller_irregular_storage_failed(NG2Controller *p,uint64_t episode,uint64_t now){
    if(!irregular_current(p,episode,now)||!irregular_active(p)
        ||p->irregular.outcome_ns||p->irregular.stage==NG2_IRREGULAR_HELD)return 0;
    p->last_now=now;irregular_hold(p,now,NG2_IRREGULAR_STORAGE);return 1;
}
static int irregular_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
                             uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    int qualified=p->irregular_call&&p->irregular_observation_valid&&p->irregular_observation_id==id
        &&now>=start&&now-start<=FRESH;
    int death=qualified
        &&irregular_death(&p->irregular_observation);
    int death_present=qualified
        &&irregular_death_present(&p->irregular_observation);
    if(!p->irregular.enabled)return 0;
    p->irregular.prefix=prefix;
    if(!qualified){
        if(irregular_active(p)){irregular_frame(p,scene,id,start,end,prefix);return 1;}
        return 0;
    }
    if(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&p->irregular.outcome_ns){
        p->irregular.stage=NG2_IRREGULAR_IDLE;p->irregular.kind=NG2_IRREGULAR_NONE;
        p->irregular.held_reason=0;p->irregular_menu_ready=0;irregular_clear_first(p);
    }
    if(!irregular_active(p)){
        if(death&&!p->finish_requested){
            if(p->s.input_state==3&&start<p->ack_ns)return 0;
            irregular_frame(p,scene,id,start,end,prefix);
            if(p->s.input_state==1){p->irregular_death_wait=1;p->irregular_death_wait_capture=id;return 1;}
            if(p->s.input_state==2||p->s.input_state==4)return 1;
            if(p->irregular_death_wait&&id<=p->irregular_death_wait_capture)return 1;
            p->irregular_death_wait=0;irregular_start(p,NG2_IRREGULAR_DEATH,id,now);return 1;
        }
        if(death_present){irregular_frame(p,scene,id,start,end,prefix);
            irregular_hold(p,now,NG2_IRREGULAR_INVALID_UI);return 1;}
        if(p->irregular_death_wait){
            if(p->s.input_state)return 1;
            p->irregular_death_wait=0;finish(p,now,NG2_REASON_SCREEN);return 1;
        }
        if(scene->state==NG2_FLOOR&&!death_present){p->irregular_live=*scene;p->irregular_live_id=id;
            p->irregular.live_baseline_capture_id=id;}
        return 0;
    }
    irregular_frame(p,scene,id,start,end,prefix);
    if(p->cycle.candidate_latched){irregular_hold(p,now,NG2_IRREGULAR_CANDIDATE);return 1;}
    if(now>p->irregular.parent_deadline_ns){
        irregular_hold(p,now,p->irregular.stage==NG2_IRREGULAR_WAIT_MENU?
            NG2_IRREGULAR_MENU_UNRECOGNIZED:NG2_IRREGULAR_DEADLINE);return 1;}
    if(p->irregular.stage==NG2_IRREGULAR_HELD)return 1;
    if(p->irregular.stage==NG2_IRREGULAR_RESTART_READY&&p->s.input_state==1
        &&p->command.kind==NG2_ACTION_RESTART&&!irregular_restart_ticket(p)){
        irregular_hold(p,now,NG2_IRREGULAR_INVALID_UI);return 1;
    }
    if(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&!p->irregular.outcome_ns&&!death_present)
        irregular_keep_goods(p,scene,id,start,end,prefix);
    if(death&&p->irregular.kind==NG2_IRREGULAR_STALLED){
        if(p->irregular.stage==NG2_IRREGULAR_PAUSE&&p->irregular.durable_ns&&!p->s.input_state){
            /* The existing checkpoint and all original proof/D identities
             * survive. Runtime persists this fresh DEATH with its distinct
             * continue intent; no new episode or reservation is created. */
            p->irregular.kind=NG2_IRREGULAR_DEATH;
            p->irregular.stage=NG2_IRREGULAR_DEATH_CONTINUE;
        }else irregular_hold(p,now,NG2_IRREGULAR_INVALID_UI);
        return 1;
    }
    if(p->s.input_state==3&&start>=p->ack_ns){
        NG2ControllerEvent *e=event(p);
        if(p->command.kind==NG2_ACTION_DEATH_CONTINUE&&p->irregular.stage==NG2_IRREGULAR_WAIT_MENU){
            if(!p->irregular.continue_capture_id){p->irregular.continue_capture_id=id;
                e->observed_capture_id=id;end_visual_wait(p);}
        }else if(p->command.kind==NG2_ACTION_PAUSE&&p->irregular.stage==NG2_IRREGULAR_PAUSE
            &&scene->state==NG2_PAUSE&&scene->restart_label&&!death_present){
            p->irregular.pause_capture_id=id;e->observed_capture_id=id;end_visual_wait(p);
            p->s.paused=1;p->irregular.stage=NG2_IRREGULAR_RESTART_READY;
        }else if(p->command.kind==NG2_ACTION_RESTART&&p->irregular.stage==NG2_IRREGULAR_WAIT_RESTART
            &&scene->state==NG2_FLOOR&&!death_present&&p->irregular.live_baseline_capture_id
            &&ng2_fingerprint_changed(p->irregular_baseline,scene->fingerprint)){
            p->irregular.next_floor_capture_id=id;e->observed_capture_id=id;end_visual_wait(p);
            p->irregular_floor=*scene;p->irregular_floor_start=start;
            p->irregular_floor_end=end;p->irregular_floor_prefix=prefix;
            p->irregular.stage=NG2_IRREGULAR_OUTCOME;
            irregular_keep_goods(p,scene,id,start,end,prefix);return 1;
        }
    }
    if(p->irregular.stage==NG2_IRREGULAR_WAIT_MENU&&!p->s.input_state&&!death_present){
        const NG2IrregularObservation *o=&p->irregular_observation;
        if(p->irregular_observation_valid&&irregular_restart(o)){
            if(!p->irregular_menu_id){p->irregular_menu=*o;p->irregular_menu_id=id;
                p->irregular_menu_end=end;
            }else if(id>p->irregular_menu_id&&start>p->irregular_menu_end
                &&abs(o->left-p->irregular_menu.left)<=2&&abs(o->top-p->irregular_menu.top)<=2)
                p->irregular_menu_ready=1;
            else {p->irregular_menu_id=0;p->irregular_menu_ready=0;}
        }else if(scene->state!=NG2_PAUSE){p->irregular_menu_id=0;p->irregular_menu_ready=0;}
        if(p->irregular.continue_outcome_ns){
            if(scene->state==NG2_FLOOR)p->irregular.stage=NG2_IRREGULAR_PAUSE;
            else if(irregular_ui(p,NG2_ACTION_RESTART))p->irregular.stage=NG2_IRREGULAR_RESTART_READY;
        }
    }
    return 1;
}
static void initial_restart_parent(NG2Controller *p,uint64_t id,uint64_t start,
    uint64_t end,uint64_t prefix,uint64_t now){
    NG2InitialRestart *initial=&p->initial_restart;
    uint64_t fresh_end=start<NS_LIMIT-FRESH?start+FRESH:NS_LIMIT-1;
    uint64_t transition_end=now<NS_LIMIT-TRANSITION?now+TRANSITION:NS_LIMIT-1;
    if(initial->parent)return;
    initial->source=id;initial->source_start=start;initial->source_end=end;initial->source_prefix=prefix;
    initial->parent=minimum(fresh_end,minimum(transition_end,session_bound(p)));
    if(p->s.walk_started_ns)initial->parent=minimum(initial->parent,p->s.walk_started_ns+45*SECOND);
}
/* Return1 only when this explicit initialization owns the current UI frame.
 * Its first qualified FLOOR falls through to the ordinary goods/source path. */
static int initial_restart_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,uint64_t now){
    NG2InitialRestart *initial=&p->initial_restart;
    if(!initial_restart_active(p)||p->finish_requested)return 0;
    if(p->cycle.candidate_latched){initial->stage=NG2_INITIAL_HELD;return 0;}
    if(initial->parent&&now>=initial->parent){
        initial->stage=NG2_INITIAL_HELD;finish(p,now,NG2_REASON_RESTART);return 0;
    }
    if(initial->stage==NG2_INITIAL_FLOOR){
        int qualified=initial->ack&&p->s.input_state==3&&p->command.id==initial->restart
            &&p->command.kind==NG2_ACTION_RESTART&&prefix==initial->restart
            &&scene->state==NG2_FLOOR&&start>=initial->ack
            &&now>=initial->ack&&now-initial->ack<TRANSITION
            &&restart_yield_ui_source(p,id,start,now,1)&&p->irregular_observation.hud_mask==15;
        if(qualified){
            event(p)->observed_capture_id=id;end_visual_wait(p);
            reset_level(p,end);++p->s.restarts;
            /* This is UI completion, not proof of a changed old world. No
             * level increment, remember_level_restart or finite-yield token. */
            initial->stage=NG2_INITIAL_DONE;p->s.reason=NG2_REASON_NONE;
            begin_initial_view(p,scene,id,start,end);
            return 0;
        }
        if(scene->goods!=NG2_GOODS_UNKNOWN){initial->stage=NG2_INITIAL_HELD;return 0;}
        cycle_scene(p,scene,id,start,end,prefix);return 1;
    }
    if(initial->stage==NG2_INITIAL_VETO)return 0;
    if(!restart_yield_ui_source(p,id,start,now,1))return 0;
    if(scene->state!=NG2_PAUSE&&scene->state!=NG2_FLOOR)return 0;
    initial_restart_parent(p,id,start,end,prefix,now);
    if(scene->state==NG2_FLOOR&&scene->goods!=NG2_GOODS_UNKNOWN){
        initial->veto_capture=id;initial->veto_prefix=prefix;initial->veto_job=0;
        initial->stage=NG2_INITIAL_VETO;return 0;
    }
    cycle_scene(p,scene,id,start,end,prefix);
    if(p->s.input_state==3&&p->command.kind==NG2_ACTION_PAUSE
        &&p->command.id==initial->pause&&scene->state==NG2_PAUSE&&start>=p->ack_ns){
        event(p)->observed_capture_id=id;end_visual_wait(p);p->s.paused=1;p->s.phase=NG2_PHASE_PAUSE;
    }
    if(initial->stage==NG2_INITIAL_SOURCE)
        initial->stage=scene->state==NG2_FLOOR?NG2_INITIAL_PAUSE:
            scene->restart_label?NG2_INITIAL_RESTART:NG2_INITIAL_SOURCE;
    else if(initial->stage==NG2_INITIAL_PAUSE&&scene->state==NG2_PAUSE&&scene->restart_label)
        initial->stage=NG2_INITIAL_RESTART;
    return 1;
}
void ng2_controller_observe_irregular_at(NG2Controller *p,const NG2Scene *scene,
    const NG2IrregularObservation *observation,uint64_t id,uint64_t start,uint64_t end,
    uint64_t prefix,int32_t stable,uint64_t commit){
    NG2IrregularObservation previous;uint64_t previous_id;int previous_valid,accepted;
    if(!p)return;
    previous=p->irregular_observation;previous_id=p->irregular_observation_id;
    previous_valid=p->irregular_observation_valid;
    p->irregular_call=p->irregular.enabled;
    p->irregular_observation_valid=p->irregular.enabled&&irregular_observation_ok(observation);
    p->irregular_observation_id=id;
    if(p->irregular_observation_valid)p->irregular_observation=*observation;
    else memset(&p->irregular_observation,0,sizeof(p->irregular_observation));
    accepted=ng2_controller_observe_at(p,scene,id,start,end,prefix,stable,commit);
    if(accepted!=1){p->irregular_observation=previous;p->irregular_observation_id=previous_id;
        p->irregular_observation_valid=previous_valid;}
    p->irregular_call=0;
}
int ng2_controller_observe_at(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,int32_t stable,uint64_t commit){
    int pending_kind,initial_wait=0,mask=0,changed_tiles=0,changed_protected=0;
    int clipped_entry=0,quiet_gate=0,opened_refresh=0,preinput_zero=0;
    if(!p)return -1;
    if(p->s.terminal)return 0;
    if(!valid_time(commit)||commit<end||commit<p->last_now)return -1;
    p->observe_now=commit;
    ++p->s.capture_count;
    if(!id||!valid_time(start)||!valid_time(end)||end<=start||start<p->s.started_ns||(start<p->last_now&&p->last_now-start>FRESH)||id<=p->seen_id
        ||(p->seen_id&&(start<=p->seen_start||end<=p->seen_end))){++p->s.discarded_frames;return 0;}
    p->seen_id=id;p->seen_start=start;p->seen_end=end;
    p->stationary_qualification.valid=0;
    if(!valid_scene(scene)||stable<0||stable>1){
        p->diagnostic_observed_id=id;
        ++p->s.discarded_frames;terminal(p,end,NG2_REASON_GEOMETRY);return 0;
    }
    p->last_now=commit;
    if(campaign_expired(p,commit)){ng2_controller_cancel(p,commit,NG2_REASON_SESSION);return 0;}
    if(p->restart_yield.s.enabled&&!p->restart_yield.s.initial_pause_seen){
        if(!stable||prefix||p->s.input_state){++p->s.discarded_frames;return 0;}
        int required=p->campaign.enabled&&p->campaign.successor_floor?NG2_FLOOR:NG2_PAUSE;
        int initial_floor=p->initial_restart.configured&&p->initial_restart.stage==NG2_INITIAL_SOURCE
            &&!(p->campaign.enabled&&p->campaign.successor_floor)&&scene->state==NG2_FLOOR;
        if((scene->state==required||initial_floor)&&restart_yield_ui_source(p,id,start,commit,1))p->restart_yield.s.initial_pause_seen=1;
        else{
            cycle_scene(p,scene,id,start,end,prefix);
            if(scene->state!=NG2_UNKNOWN||!restart_yield_ui_source(p,id,start,commit,1))terminal(p,commit,NG2_REASON_SCREEN);
            return 1;
        }
    }
    if(p->restart_yield.s.pending){
        if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
            ++p->s.discarded_frames;return 0;
        }
        p->diagnostic_observed_id=id;
        if(!restart_yield_ui_source(p,id,start,commit,1)){
            NG2RestartYield *y=&p->restart_yield;
            int death=p->irregular_call&&p->irregular_observation_valid&&p->irregular_observation_id==id
                &&commit>=start&&commit-start<=FRESH&&irregular_death(&p->irregular_observation);
            restart_yield_invalidate(p);
            if(death&&!y->pause&&!p->finish_requested&&p->s.input_state==0){
                /* The existing irregular owner keeps its real worker drain,
                 * checkpoint and UI proof; budget continuation is retired. */
                y->s.pending=0;
                return irregular_observe(p,scene,id,start,end,prefix,commit);
            }
            cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);finish(p,commit,NG2_REASON_SCREEN);
            restart_yield_observe(p,scene,id,start,end,prefix,commit);p->need_fresh_cleanup=1;return 1;
        }
        if(irregular_observe(p,scene,id,start,end,prefix,commit)){
            restart_yield_invalidate(p);p->restart_yield.s.pending=0;return 1;
        }
        return restart_yield_observe(p,scene,id,start,end,prefix,commit);
    }
    if(p->restart_yield.s.enabled&&!p->restart_yield.s.invalid&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART
        &&p->cycle.next_floor_capture_id&&stable&&prefix==p->s.last_completed_id
        &&p->s.input_state==0&&scene->state==NG2_FLOOR&&scene->goods!=NG2_GOODS_UNKNOWN)
        p->restart_yield.required|=scene->goods==NG2_GOODS_PARTIAL?1:2;
    if(p->irregular.enabled&&stable==1&&prefix==p->s.last_completed_id
        &&p->s.input_state!=2&&p->s.input_state!=4
        &&irregular_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(stable==1&&prefix==p->s.last_completed_id&&p->s.input_state!=2&&p->s.input_state!=4
        &&initial_restart_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(p->cycle_enabled&&!p->finish_requested){
        int partial=scene->goods==NG2_GOODS_PARTIAL;
        int draining_partial=partial&&p->s.input_state==2&&prefix==p->cycle_consumed_prefix;
        if(!p->upper.active&&!p->entry.active&&!p->lower.active&&!cycle_holding(p)&&(scene->goods==NG2_GOODS_VISIBLE
            ||(partial&&!p->cycle_partial_credit&&!draining_partial)))cycle_latch(p,scene,commit);
        if(!p->upper.active&&!p->entry.active&&!p->lower.active&&cycle_holding(p)&&scene->goods==NG2_GOODS_VISIBLE){p->cycle.full_seen=1;p->s.goods=1;}
    }
    if((p->s.input_state==1||p->replan_pending||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE)
        mask=scene_change(&p->before,scene,&changed_tiles,&changed_protected);
    /* A current goods observation latches before prefix/phase checks. Only a
     * subsequent stable matching prefix may authorize the holding pause. */
    if(!p->cycle_enabled&&scene->goods==NG2_GOODS_VISIBLE){finish(p,end,NG2_REASON_GOODS);p->need_fresh_cleanup=1;}
    if(!p->cycle_enabled&&(p->restart_intent||(p->passage_active&&!actual_gold(scene)))
        &&(scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))){
        finish(p,end,NG2_REASON_PARTIAL_GOODS);p->need_fresh_cleanup=1;
    }
    if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
        ++p->s.discarded_frames;return 0;}
    p->diagnostic_observed_id=id;
    revoke_clear_handoff(p,scene,commit);
    if(!p->finish_requested&&upper_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(!p->finish_requested&&lower_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(!p->finish_requested&&entry_observe(p,scene,id,start,end,prefix,commit))return 1;
    if(cycle_holding(p)&&!p->finish_requested)
        return cycle_observe_hold(p,scene,id,start,end,prefix,commit);
    if(p->cycle_enabled&&p->cycle_partial_credit&&!p->finish_requested){
        NG2Motion motion={0};int validation;
        if(prefix!=p->cycle_credit_prefix)validation=NG2_REVALIDATE_STATE;
        else if(commit>p->cycle.continuation_deadline_ns)validation=NG2_REVALIDATE_TIMING;
        else validation=cycle_partial_comparison(p,scene,NULL,&motion);
        diagnostic_comparison(p,id,validation,&motion);
        if(validation!=NG2_REVALIDATE_NONE){
            if(validation==NG2_REVALIDATE_PROTECTED
                &&cycle_current_partial_start(p,scene,id,start,end,prefix,commit))return 1;
            if(cycle_rebind_changed_partial(p,scene,id,start,end,prefix,commit))return 1;
            cycle_failure(p,commit,NG2_RING_KERNEL,NG2_REASON_SCREEN);
            return cycle_observe_hold(p,scene,id,start,end,prefix,commit);
        }
        cycle_scene(p,scene,id,start,end,prefix);add_sample(p,scene,id,start,end);return 1;
    }
    if(!p->finish_requested&&unlocalized_gold_floor(scene))p->passage_unlocalized_gold=1;
    initial_wait=recheck_initial_view(p,scene,id,start,end,prefix);
    if(initial_wait)mask=0;
    if((p->passage_active||p->restart_intent)&&!p->finish_requested&&scene->state==NG2_FLOOR
        &&!initial_wait&&!actual_gold(scene)&&!clear_gold_floor(scene)
        &&!(p->passage_active&&unlocalized_gold_floor(scene))
        &&!passage_ack_visual(p,scene,start,end,prefix,commit)
        &&!passage_moved_uncertain_wait(p)
        &&!(p->s.input_state==3&&p->command.kind==NG2_ACTION_RESTART)){
        /* An uncertain floor cannot keep old skip authority. A PAUSE UI's
         * UNKNOWN gold is normal; an ACK-known RESTART keeps its own proof. */
        if(start_initial_scene_reacquisition(p,scene,id,start,end,prefix,commit)
            ||start_prefirst_scene_reacquisition(p,scene,id,start,end,prefix,commit))initial_wait=1;
        else finish(p,end,NG2_REASON_SCREEN);
        mask=0;
    }
    if(p->restart_intent&&!p->finish_requested&&clear_gold_floor(scene)
        &&!p->initial_view_pending&&!p->initial_candidate_waiting
        &&!level_inputs(p)&&!level_moves(p)&&!p->s.lead_confirmed&&!p->s.x&&!p->s.y
        &&ng2_passage_candidates(scene)){
        if(p->s.input_state==0||(p->s.input_state==1
            &&(p->command.kind==NG2_ACTION_PAUSE||p->command.kind==NG2_ACTION_RESTART))){
            not_sent(p,end,NG2_REASON_SCREEN);clear_slots(p);
            p->restart_intent=p->restart_baseline_valid=p->restart_pending=0;
            start_floor(p,scene,id,end);mask=0;
        }else if(p->s.input_state==3&&p->command.kind==NG2_ACTION_PAUSE)
            finish(p,end,NG2_REASON_NO_PATH);
    }
    if(p->restart_intent&&!p->finish_requested&&scene->state==NG2_FLOOR&&actual_gold(scene)
        &&!(p->s.input_state==3&&p->command.kind==NG2_ACTION_RESTART)){
        p->restart_intent=0;p->restart_baseline_valid=0;p->restart_pending=0;
        if(p->s.input_state==0||(p->s.input_state==1
            &&(p->command.kind==NG2_ACTION_PAUSE||p->command.kind==NG2_ACTION_RESTART))){
            p->passage_active=1;
            begin_passage_wait(p,scene,id,start,end,commit,PASSAGE_WAIT_GOLD);mask=0;
        }else finish(p,end,NG2_REASON_NO_PATH);
    }
    if(p->passage_source.refreshed&&!p->finish_requested
        &&(p->s.input_state==1||p->continuous_pending)
        &&!passage_source_proof(p,scene,commit)){
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,commit,NG2_REASON_SCREEN);mask=0;
    }
    if(p->passage_active&&!p->finish_requested&&!p->stationary_wait_active){
        if((scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))&&!actual_gold(scene))
            finish(p,end,NG2_REASON_PARTIAL_GOODS);
        else if(p->passage_wait_kind){update_passage_wait(p,scene,id,start,end,commit);mask=0;}
        else if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE){
            NG2Motion still;
            if(commit>p->command.deadline_ns
                &&recover_unsent_continuous_scene(p,commit,scene,start,end,prefix))mask=0;
            else if((preinput_zero=quiet_passage_observation(p,scene,commit))){
                if(passage_source_refinable(p,scene,commit)){
                    if(mask)record_change(p,scene,id,mask,changed_tiles,changed_protected,1,NG2_REVALIDATE_FRESH_ALLOWED);
                    not_sent(p,end,NG2_REASON_SCREEN);
                    ++p->continuous_count;++p->continuous_chain_count;
                    p->passage_source.refreshed=1;p->before=*scene;
                    p->continuous_pending_choice=p->command_choice;p->continuous_pending=NG2_CONTINUOUS_FRESH;
                    p->motion_reference_valid=0;
                }
                mask=0;
            }
            else if(start_stationary_wait(p,scene,id,start,end,commit))mask=0;
            else if(commit<=p->command.deadline_ns&&scene->state==NG2_FLOOR
                &&(actual_gold(scene)||passage_floor(scene))
                &&ng2_motion(&p->before,scene,p->command.direction,&still)
                &&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy){
                begin_passage_wait(p,scene,id,start,end,commit,
                    actual_gold(scene)?PASSAGE_WAIT_GOLD:PASSAGE_WAIT_ROUTE);mask=0;
            }else {
                if(!start_initial_scene_reacquisition(p,scene,id,start,end,prefix,commit)){
                    not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);
                }
                mask=0;
            }
        }
    }
    if(p->gate_refresh_state){
        update_gate_refresh(p,scene,id,start,end,commit);
        /* Every frame uses the fixed gate permission and independent proof,
         * including mask-zero drift. Generic FRESH cannot broaden this door. */
        mask=0;
    }
    if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE&&p->command_choice.reason==9){
        p->edge_validated_capture_id=0;
        if(commit>p->command.deadline_ns
            &&initial_recover(p,NG2_RECOVERY_UNSENT_DEADLINE,NG2_RECOVERY_ACTUAL_COMMIT,commit,id)){
            /* A completed observation can beat tick to an expired unsent
             * window. Retire that ID; only a new bounded fit may act again. */
        }else if(quiet_edge_observation(p,scene,commit))p->edge_validated_capture_id=id;
        else {
            not_sent(p,end,NG2_REASON_SCREEN);
            p->replan_pending=p->continuous_pending=0;finish(p,end,NG2_REASON_SCREEN);
        }
        mask=0;
    }
    /* Every accepted pre-dispatch image re-proves this sole entrance. A
     * signature-only failure must retire it even when scene_change is zero. */
    if(p->stationary_gate_retry_waiting==NG2_GATE_RETRY_ISSUED){
        p->stationary_gate_retry_proof_id=0;
        if(stationary_gate_scene(p,scene))p->stationary_gate_retry_proof_id=id;
        else {
            not_sent(p,end,NG2_REASON_SCREEN);
            p->replan_pending=p->continuous_pending=0;
            finish(p,end,NG2_REASON_SCREEN);mask=0;
        }
    }
    /* Even unchanged tiles can hide signature-only drift. Revalidate the
     * immutable original directly against every accepted pre-send image. */
    if((p->s.input_state==1||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE){
        validate_motion_reference(p,scene,start,end,prefix,end);
        /* Reuse only this call's strict zero against exactly the current
         * immutable before/source/prefix, never a different reference anchor. */
        if(p->motion_reference_present&&p->motion_reference_valid
            &&p->motion_reference_ticket.source_capture_id==p->command.source_capture_id
            &&p->motion_reference_ticket.source_start_ns==p->command.source_start_ns
            &&p->motion_reference_prefix==prefix
            &&!memcmp(&p->motion_reference_scene,&p->before,sizeof(p->before)))preinput_zero=1;
    }
    clipped_entry=clipped_entry_top(p,scene);
    if(!p->finish_requested&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&(mask||clipped_entry))quiet_gate=quiet_gate_observation(p,scene,commit);
    if(!p->finish_requested&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&opened_entry_relation(p,scene)
        &&(mask||(scene->goods==NG2_GOODS_PARTIAL&&partial_shop_floor_step(p)
            &&!gold_retained(&p->scene,scene))))opened_refresh=1;
    /* A return to source tiles/protection still needs the cached clock and
     * direct strict-zero proof, even when no quarantined GOLD disappeared. */
    if(!p->finish_requested&&clipped_entry&&!mask&&!quiet_gate&&!opened_refresh){
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);
    }
    /* Returning exactly to the source can have mask zero after an accepted
     * remote GOLD reveal. It still cannot erase that observed wall evidence. */
    if(!p->finish_requested&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&scene->goods==NG2_GOODS_PARTIAL&&partial_shop_floor_step(p)
        &&!gold_retained(&p->scene,scene)&&!(clipped_entry&&quiet_gate)&&!opened_refresh){
        if(mask)record_change(p,scene,id,mask,changed_tiles,changed_protected,0,NG2_REVALIDATE_GOLD);
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);mask=0;
    }
    if((mask&&quiet_initial_observation(p,scene,commit))||quiet_gate){mask=0;opened_refresh=0;}
    if(!mask&&!opened_refresh){
        NG2Decision latest;
        if(preinput_same_source(p,scene,id,start,end,prefix,commit,preinput_zero||quiet_gate,&latest)){
            uint64_t epoch=p->preparation_epoch;
            record_change(p,scene,id,0,changed_tiles,changed_protected,1,NG2_REVALIDATE_CONTINUOUS_ALLOWED);
            not_sent(p,commit,NG2_REASON_SCREEN);
            ++p->continuous_count;++p->continuous_chain_count;p->before=*scene;
            p->continuous_pending_choice=latest;p->continuous_pending=NG2_CONTINUOUS_SAME;
            p->preinput_refresh_epoch=epoch;
            if(p->motion_reference_present)p->motion_reference_reissued=1;
        }
    }
    if(mask||opened_refresh){
        NG2Decision latest;
        int validation=p->s.lead_confirmed?continuous_validation(p,scene,end,&latest):
            (can_replan(p,scene)?NG2_REVALIDATE_INITIAL_ALLOWED:NG2_REVALIDATE_INITIAL_REJECTED);
        int allowed=validation==NG2_REVALIDATE_INITIAL_ALLOWED||continuous_allowed(validation);
        if(mask)record_change(p,scene,id,mask,changed_tiles,changed_protected,allowed,validation);
        /* Refresh retains the old UNKNOWN in an unsent event; only a later
         * independent pair may authorize a replacement action. */
        if(allowed||(!start_gate_refresh(p,scene,id,start,end,commit)
            &&!start_terrain_refresh(p,scene,id,start,end,commit)
            &&!start_observation_refresh(p,scene,id,start,end,commit)
            &&!start_stationary_wait(p,scene,id,start,end,commit))){
            not_sent(p,end,NG2_REASON_SCREEN);
            if(validation==NG2_REVALIDATE_INITIAL_ALLOWED){++p->replan_count;p->replan_pending=1;p->before=*scene;}
            else if(continuous_allowed(validation)){
                ++p->continuous_count;++p->continuous_chain_count;p->before=*scene;
                p->continuous_pending_choice=latest;
                if(validation==NG2_REVALIDATE_FRESH_ALLOWED){
                    p->continuous_pending=NG2_CONTINUOUS_FRESH;
                    p->motion_reference_valid=0;
                }else{
                    p->continuous_pending=NG2_CONTINUOUS_SAME;
                    if(p->motion_reference_present)p->motion_reference_reissued=1;
                }
            }else {p->replan_pending=0;p->continuous_pending=0;finish(p,end,NG2_REASON_SCREEN);}
        }
    }
    p->scene=*scene;p->have_scene=1;p->need_fresh_cleanup=0;p->last_observed_prefix=prefix;
    p->s.paused=scene->state==NG2_PAUSE;
    p->s.last_capture_id=id;p->s.last_capture_start_ns=start;p->s.last_capture_end_ns=end;++p->s.accepted_frames;
    if(!p->s.goods)p->s.goods=scene->goods==NG2_GOODS_VISIBLE;
    if(p->finish_requested&&p->s.input_state==3&&p->command.kind==NG2_ACTION_RESTART
        &&scene->state==NG2_FLOOR&&start>=p->ack_ns){
        /* The ACK-known restart is not a new-level proof, but this current
         * floor may safely close its visual wait for the holding pause. */
        event(p)->observed_capture_id=id;end_visual_wait(p);
    }
    if(p->s.input_state==3){
        pending_kind=p->command.kind;
        if(pending_kind==NG2_ACTION_MOVE){
            if(scene->state!=NG2_FLOOR){
                record_ack_nonfloor_failure(p,scene,id,start,end,commit);
                p->s.input_state=0;p->s.current_command_id=0;finish(p,end,NG2_REASON_SCREEN);
            }
            else if(p->s.goods){
                event(p)->observed_capture_id=id;
                resolve_move(p,scene,id,start,end);
                end_visual_wait(p);finish(p,end,NG2_REASON_GOODS);
            }
            else {add_sample(p,scene,id,start,end);resolve_move(p,scene,id,start,end);}
        }else if(start>=p->ack_ns){
            if(pending_kind==NG2_ACTION_RESUME&&scene->state==NG2_FLOOR){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;clear_model(p);
                begin_initial_view(p,scene,id,start,end);start_floor(p,scene,id,end);
            }else if(pending_kind==NG2_ACTION_PAUSE&&scene->state==NG2_PAUSE){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;p->s.paused=1;
                if(p->finish_requested){terminal(p,end,p->s.reason);return 1;}
                p->s.phase=NG2_PHASE_PAUSE;
            }else if(pending_kind==NG2_ACTION_RESTART&&scene->state==NG2_FLOOR
                &&p->restart_pending&&p->restart_baseline_valid&&!p->finish_requested&&!p->s.goods
                &&scene->goods==NG2_GOODS_UNKNOWN
                &&ng2_fingerprint_changed(p->restart_fingerprint,scene->fingerprint)){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;p->restart_pending=0;++p->s.restarts;
                if(p->cycle_enabled)++p->cycle.level_id;
                {uint64_t restart_id=p->command.id;
                    reset_level(p,end);remember_level_restart(p,restart_id,id,prefix);}
                begin_initial_view(p,scene,id,start,end);start_floor(p,scene,id,end);
            }
        }
    }else if(!p->finish_requested){
        if(!initial_wait&&p->s.phase==NG2_PHASE_SEARCH&&scene->state==NG2_FLOOR)start_floor(p,scene,id,end);
    }
    if(irregular_active(p))return 1;
    if(!p->stationary_wait_active)update_passage_progress(p,scene,id,start,end,commit);
    if(!p->finish_requested&&p->s.walk_started_ns&&scene->state==NG2_FLOOR
        &&p->s.input_state!=3&&!passage_moved_uncertain_wait(p))add_sample(p,scene,id,start,end);
    if(p->beat_failed&&!p->finish_requested
        &&!(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE)&&!p->proof_deadline)
        finish(p,commit,NG2_REASON_BEAT);
    stationary_qualify_current(p,id,start,end,prefix);
    return 1;
}
int ng2_controller_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,int32_t stable){
    return ng2_controller_observe_at(p,scene,id,start,end,prefix,stable,p?maximum(end,p->last_now):end);
}
static int reserve(NG2Controller *p,uint64_t now,int kind,int direction,uint64_t target,NG2Command *out){
    NG2ControllerEvent *e;uint64_t deadline,horizon,tail;
    int reissuing=kind==NG2_ACTION_MOVE&&p->continuous_pending;
    uint64_t inherited_sync_deadline=reissuing?p->command_sync_deadline:0;
    if(p->restart_yield.s.pending&&kind!=NG2_ACTION_PAUSE){restart_yield_invalidate(p);return 0;}
    if(reissuing)validate_motion_reference(p,&p->scene,p->s.last_capture_start_ns,
        p->s.last_capture_end_ns,p->last_observed_prefix,now);
    if(p->event_count>=EVENT_CAP){terminal(p,now,NG2_REASON_LIMIT);return 0;}
    memset(&p->command,0,sizeof(p->command));
    p->command.id=(uint64_t)p->event_count+1;p->command.kind=kind;p->command.direction=direction;
    p->command.source_capture_id=p->s.last_capture_id;p->command.source_start_ns=p->s.last_capture_start_ns;
    p->command.phase_sample_ns=kind==NG2_ACTION_MOVE?p->model.last_ns:0;
    p->command_sync_deadline=kind==NG2_ACTION_MOVE&&p->recovery.mode==NG2_RECOVERY_POST_MOVE?
        sync_deadline(p):inherited_sync_deadline;
    p->command.target_ns=target;p->command.not_before_ns=kind==NG2_ACTION_MOVE?target-p->s.lead_ns:now;
    if(kind==NG2_ACTION_MOVE&&initial_slot_active(p)){
        p->command.target_ns=p->initial_slot_target;p->command.not_before_ns=p->initial_slot_not_before;
    }else if(kind==NG2_ACTION_MOVE&&p->recovery_slot_target){
        p->command.target_ns=p->recovery_slot_target;p->command.not_before_ns=p->recovery_slot_not_before;
    }
    tail=kind==NG2_ACTION_MOVE?p->s.lead_ns+50000000:50000000;
    horizon=minimum(p->s.last_capture_start_ns+FRESH,session_bound(p));
    if(initial_restart_active(p)&&p->initial_restart.parent
        &&(kind==NG2_ACTION_PAUSE||kind==NG2_ACTION_RESTART))
        horizon=minimum(horizon,p->initial_restart.parent);
    if(kind==NG2_ACTION_PAUSE&&p->restart_yield.s.pending&&!p->restart_yield.s.invalid)
        horizon=minimum(horizon,p->restart_yield.s.parent_deadline_ns);
    if(kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->model.last_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    if(kind==NG2_ACTION_MOVE&&p->stationary_wait_parent)horizon=minimum(horizon,p->stationary_wait_parent);
    if(kind==NG2_ACTION_MOVE&&p->opened_entry_parent)horizon=minimum(horizon,p->opened_entry_parent);
    if(kind==NG2_ACTION_MOVE&&(p->cycle_partial_credit||p->cycle_full_framing||p->entry.active||p->lower.active||p->upper.active))horizon=minimum(horizon,p->cycle.continuation_deadline_ns);
    if(reissuing)horizon=minimum(horizon,continuous_horizon(p));
    /* Preserve the original target-plus-50ms and actual-send-plus-lead-plus-
     * 50ms contract. Tighten the main ticket; never spend a 10ms allowance
     * beyond image, phase, walk, or session validity. */
    if(horizon<tail||p->command.not_before_ns>horizon-tail){finish(p,now,NG2_REASON_STALE);return 0;}
    deadline=kind==NG2_ACTION_MOVE?p->command.not_before_ns+10000000:now+SECOND;
    if(kind==NG2_ACTION_MOVE&&initial_slot_active(p))deadline=minimum(deadline,p->initial_slot_deadline);
    if(kind==NG2_ACTION_MOVE&&p->recovery_slot_target)deadline=minimum(deadline,p->recovery_slot_deadline);
    if(kind==NG2_ACTION_MOVE&&p->replan_pending)deadline=minimum(deadline,p->initial_ticket.deadline_ns);
    if(kind==NG2_ACTION_MOVE&&p->continuous_pending)deadline=minimum(deadline,p->continuous_ticket.deadline_ns);
    if(kind==NG2_ACTION_MOVE&&p->s.lead_confirmed&&p->next_deadline)deadline=minimum(deadline,p->next_deadline);
    deadline=minimum(deadline,horizon-tail);
    deadline=minimum(deadline,p->s.last_capture_start_ns+FRESH);
    deadline=minimum(deadline,session_bound(p));
    if(kind==NG2_ACTION_MOVE){deadline=minimum(deadline,p->model.last_ns+FRESH);
        deadline=minimum(deadline,p->s.walk_started_ns+45*SECOND);}
    p->command.deadline_ns=deadline;
    if(p->command.not_before_ns>deadline||now>deadline){finish(p,now,NG2_REASON_LATE);return 0;}
    p->command.ordinal=kind==NG2_ACTION_MOVE?p->s.last_ordinal+1:0;
    if(kind==NG2_ACTION_MOVE&&p->cycle_full_framing)
        p->command.ordinal=maximum(p->command.ordinal,p->cycle_full_old_ordinal+1);
    if(kind==NG2_ACTION_MOVE&&p->entry.active)
        p->command.ordinal=maximum(p->command.ordinal,p->entry.ordinal+1);
    if(kind==NG2_ACTION_MOVE&&p->lower.active)
        p->command.ordinal=maximum(p->command.ordinal,p->lower.ordinal+1);
    if(kind==NG2_ACTION_MOVE&&p->upper.active)
        p->command.ordinal=maximum(p->command.ordinal,p->upper.ordinal+1);
    if(kind==NG2_ACTION_MOVE&&!p->s.lead_confirmed
        &&tile(&p->scene,dx[direction],dy[direction])!=NG2_TILE_FLOOR)p->command.ordinal=0;
    p->command.x=kind==NG2_ACTION_RESUME?297:kind==NG2_ACTION_RESTART?144:kind==NG2_ACTION_PAUSE?390:
        direction==NG2_UP?290:direction==NG2_DOWN?124:207;
    p->command.y=kind==NG2_ACTION_MOVE?(direction==NG2_LEFT?49:838):448;
    p->before=p->scene;p->command_period=kind==NG2_ACTION_MOVE&&initial_slot_active(p)?p->initial_slot_period:
        kind==NG2_ACTION_MOVE&&p->recovery_slot_target?p->recovery_slot_period:p->model.period_ns;
    if(kind==NG2_ACTION_MOVE&&p->replan_pending){
        p->command.target_ns=p->initial_ticket.target_ns;
        p->command.not_before_ns=p->initial_ticket.not_before_ns;
        p->command.ordinal=p->initial_ticket.ordinal;
        p->command.direction=p->initial_ticket.direction;
        p->command_period=p->initial_period;p->replan_pending=0;
    }else if(kind==NG2_ACTION_MOVE&&p->continuous_pending){
        /* The source and command ID are new. Every timing field still names
         * the original reservation and its original motion-wait horizon. */
        if(p->command.deadline_ns<p->continuous_ticket.deadline_ns){
            p->continuous_pending=0;finish(p,now,NG2_REASON_STALE);return 0;
        }
        p->command.target_ns=p->continuous_ticket.target_ns;
        p->command.not_before_ns=p->continuous_ticket.not_before_ns;
        p->command.deadline_ns=p->continuous_ticket.deadline_ns;
        p->command.ordinal=p->continuous_ticket.ordinal;
        p->command.direction=direction; /* Latest action; frozen ticket supplies time only. */
        p->command_period=p->continuous_period;
    }else if(kind==NG2_ACTION_MOVE&&!p->initial_ticket_valid){
        p->initial_ticket=p->command;p->initial_period=p->command_period;p->initial_ticket_valid=1;
    }
    if(kind==NG2_ACTION_MOVE){
        uint64_t next,wait_horizon=minimum(p->command.source_start_ns+FRESH,p->command.phase_sample_ns+FRESH);
        if(p->command.target_ns>=NS_LIMIT-p->command_period){finish(p,now,NG2_REASON_SESSION);return 0;}
        next=p->command.target_ns+p->command_period;
        if(next<p->s.lead_ns||next-p->s.lead_ns>=NS_LIMIT-10000000){finish(p,now,NG2_REASON_SESSION);return 0;}
        wait_horizon=minimum(wait_horizon,p->s.walk_started_ns+45*SECOND);
        wait_horizon=minimum(wait_horizon,session_bound(p));
        if(p->stationary_wait_parent)wait_horizon=minimum(wait_horizon,p->stationary_wait_parent);
        if(p->opened_entry_parent)wait_horizon=minimum(wait_horizon,p->opened_entry_parent);
        if(p->cycle_partial_credit||p->cycle_full_framing||p->entry.active||p->lower.active||p->upper.active)wait_horizon=minimum(wait_horizon,p->cycle.continuation_deadline_ns);
        memset(&p->motion_wait,0,sizeof(p->motion_wait));p->motion_retry_start_ns=p->motion_retry_last_ns=0;
        p->motion_wait.command_id=p->command.id;p->motion_wait.source_capture_id=p->command.source_capture_id;
        p->schedule_deadline=minimum(next-p->s.lead_ns+10000000,wait_horizon);
        p->motion_wait.deadline_ns=wait_horizon;
        if(initial_slot_active(p)){
            p->schedule_deadline=minimum(p->schedule_deadline,p->initial_slot_motion_deadline);
            p->motion_wait.deadline_ns=minimum(p->motion_wait.deadline_ns,p->initial_slot_visual_deadline);
        }
        if(p->initial_visual_deadline&&!level_inputs(p))
            p->motion_wait.deadline_ns=minimum(p->motion_wait.deadline_ns,p->initial_visual_deadline);
        if(p->recovery_slot_target){
            p->schedule_deadline=minimum(p->schedule_deadline,p->recovery_slot_schedule);
            p->motion_wait.deadline_ns=minimum(p->motion_wait.deadline_ns,p->recovery_slot_visual);
        }
        if(p->continuous_pending){
            if(p->motion_wait.deadline_ns<p->continuous_motion_deadline){
                p->continuous_pending=0;finish(p,now,NG2_REASON_STALE);return 0;
            }
            p->motion_wait.deadline_ns=p->continuous_motion_deadline;p->continuous_pending=0;
            p->schedule_deadline=p->continuous_schedule_deadline;
        }
        else if(p->s.lead_confirmed){p->continuous_ticket=p->command;p->continuous_period=p->command_period;
            p->continuous_motion_deadline=p->motion_wait.deadline_ns;p->continuous_schedule_deadline=p->schedule_deadline;
            p->continuous_ticket_valid=1;p->continuous_chain_count=0;}
        if(!level_inputs(p))p->initial_visual_deadline=p->motion_wait.deadline_ns;
        p->recovery.schedule_deadline_ns=p->schedule_deadline;
        p->recovery.visual_deadline_ns=p->motion_wait.deadline_ns;p->recovery.ack_ns=0;
        p->visual_phase_failed=0;
        if(!reissuing)create_motion_reference(p);
    }
    /* A command ID is unique within this controller. Only a qualified
     * continuous reissue keeps the opaque identity of its logical MOVE. */
    if(kind==NG2_ACTION_MOVE&&p->s.lead_confirmed&&p->s.moves>0){
        if(!reissuing)p->preparation_epoch=p->command.id;
    }else p->preparation_epoch=0;
    if(kind==NG2_ACTION_PAUSE)bind_clear_handoff_pause(p,now);
    p->s.input_state=1;p->s.current_command_id=p->command.id;
    e=&p->events[p->event_count++];memset(e,0,sizeof(*e));e->command=p->command;
    if(kind==NG2_ACTION_MOVE){
        p->recovery.mode=NG2_RECOVERY_NORMAL;clear_recovery_slot(p);
        p->edge_validated_capture_id=p->command_choice.reason==9?p->s.last_capture_id:0;
        if(p->stationary_gate_retry_waiting!=NG2_GATE_RETRY_NONE){
            p->stationary_gate_retry_waiting=NG2_GATE_RETRY_ISSUED;
            p->stationary_gate_retry_proof_id=p->s.last_capture_id;
        }
        if(p->gate_refresh_state==NG2_GATE_REFRESH_READY){
            p->gate_refresh_state=NG2_GATE_REFRESH_ISSUED;
            p->gate_refresh_proof_id=p->s.last_capture_id;
        }
    }
    if(!reissuing)create_passage_source(p);
    *out=p->command;return 1;
}
static int irregular_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    int kind,ready;
    if(!p->irregular.enabled)return -2;
    if(!irregular_active(p)){
        if(p->irregular_first_id&&(now>p->motion_wait.deadline_ns||!p->motion_wait.active))
            irregular_clear_first(p);
        return p->irregular_death_wait?0:-2;
    }
    if(p->irregular.stage==NG2_IRREGULAR_OUTCOME&&p->irregular.outcome_ns)return 0;
    if(p->cycle.candidate_latched){irregular_hold(p,now,NG2_IRREGULAR_CANDIDATE);return 0;}
    if(now>p->irregular.parent_deadline_ns){irregular_hold(p,now,
        p->irregular.stage==NG2_IRREGULAR_WAIT_MENU?NG2_IRREGULAR_MENU_UNRECOGNIZED:NG2_IRREGULAR_DEADLINE);return 0;}
    if(p->irregular.stage==NG2_IRREGULAR_HELD||p->irregular_ring_pending
        ||p->irregular.stage==NG2_IRREGULAR_QUIESCE||p->irregular.stage==NG2_IRREGULAR_CHECKPOINT
        ||p->s.input_state==2||p->s.input_state==3||p->s.input_state==4)return 0;
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns)irregular_hold(p,now,NG2_IRREGULAR_DEADLINE);
        return 0;
    }
    if(!p->irregular.durable_ns||!fresh(p,now)||p->s.restarts>=12||p->s.inputs>=16)return 0;
    kind=p->irregular.stage==NG2_IRREGULAR_PAUSE?NG2_ACTION_PAUSE:
        p->irregular.stage==NG2_IRREGULAR_DEATH_CONTINUE?NG2_ACTION_DEATH_CONTINUE:
        p->irregular.stage==NG2_IRREGULAR_RESTART_READY?NG2_ACTION_RESTART:0;
    if(!kind||!irregular_ui(p,kind)||(kind==NG2_ACTION_PAUSE&&!pause_ui_ready(p,now)))return 0;
    if(kind==NG2_ACTION_DEATH_CONTINUE&&p->irregular.continue_command_id)return 0;
    if(kind==NG2_ACTION_RESTART&&(p->irregular.restart_command_id
        ||(p->irregular.kind==NG2_IRREGULAR_DEATH&&!p->irregular.continue_outcome_ns)))return 0;
    ready=reserve(p,now,kind,0,now,out);
    if(!ready){irregular_hold(p,now,NG2_IRREGULAR_CONTROL_INVALID);return 0;}
    p->command.deadline_ns=minimum(p->command.deadline_ns,p->irregular.parent_deadline_ns);
    if(kind==NG2_ACTION_DEATH_CONTINUE){
        p->command.x=90;p->command.y=447;p->irregular.continue_command_id=p->command.id;
    }else if(kind==NG2_ACTION_RESTART){
        p->irregular.restart_command_id=p->command.id;
        p->irregular_restart_ui=p->scene.state==NG2_PAUSE?1:2;
        if(p->scene.state!=NG2_PAUSE){p->command.x=400-p->irregular_observation.top;
            p->command.y=p->irregular_observation.left+91;}
    }
    event(p)->command=p->command;*out=p->command;return 1;
}
static int irregular_begin(NG2Controller *p,uint64_t id,uint64_t now,int front,int locked,int owner){
    int kind=p->command.kind,guard=guards(front,locked,owner);
    if(!irregular_active(p)||p->irregular.stage==NG2_IRREGULAR_HELD||p->s.terminal
        ||p->s.input_state!=1||id!=p->command.id)return 0;
    if(guard){ng2_controller_cancel(p,now,guard);return 0;}
    if(p->cycle.candidate_latched){irregular_hold(p,now,NG2_IRREGULAR_CANDIDATE);return 0;}
    if(now>p->irregular.parent_deadline_ns||now>p->command.deadline_ns){
        irregular_hold(p,now,NG2_IRREGULAR_DEADLINE);return 0;}
    if(!p->irregular.durable_ns||p->irregular_ring_pending||now<p->last_now
        ||now>p->irregular.parent_deadline_ns||now>p->command.deadline_ns
        ||now<p->command.not_before_ns||!fresh(p,now)||!irregular_ui(p,kind))return 0;
    if(kind==NG2_ACTION_PAUSE){
        if(p->irregular.stage!=NG2_IRREGULAR_PAUSE||!pause_ui_ready(p,now))return 0;
    }else if(kind==NG2_ACTION_DEATH_CONTINUE){
        if(p->irregular.stage!=NG2_IRREGULAR_DEATH_CONTINUE
            ||id!=p->irregular.continue_command_id||!p->irregular.continue_intent_ns
            ||p->command.x!=90||p->command.y!=447)return 0;
    }else if(kind==NG2_ACTION_RESTART){
        if(p->irregular.stage!=NG2_IRREGULAR_RESTART_READY
            ||id!=p->irregular.restart_command_id||!p->irregular.restart_intent_ns
            ||(p->irregular.kind==NG2_IRREGULAR_DEATH&&!p->irregular.continue_outcome_ns))return 0;
        if(!irregular_restart_ticket(p)){
            irregular_hold(p,now,NG2_IRREGULAR_INVALID_UI);return 0;
        }
    }else return 0;
    if(p->s.restarts>=12||p->s.inputs>=16||now-p->s.started_ns>=180*SECOND
        ||(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND)){
        irregular_hold(p,now,NG2_IRREGULAR_LIMIT);return 0;}
    p->last_now=now;p->s.input_state=2;p->preparation_epoch=0;
    event(p)->begin_ns=now;event(p)->outcome=1;return 1;
}
static void post_move_recover(NG2Controller *p,uint64_t now,int reason){
    if(p->recovery.mode!=NG2_RECOVERY_POST_MOVE){
        ++p->recovery.episode_id;++p->recovery.post_move_reacquisitions;
        p->recovery.mode=NG2_RECOVERY_POST_MOVE;
        p->sync_ns=p->latest_verified_ns?p->latest_verified_ns:now;
    }
    recovery_record(p,reason,NG2_RECOVERY_ACTUAL_TICK,now,
        reason==NG2_RECOVERY_UNSENT_DEADLINE?p->s.last_capture_id:p->proof_capture_id);
    clear_slots(p);p->s.phase=NG2_PHASE_SYNC;
    if(p->visual_phase_failed||p->beat_failed)clear_model(p);
    p->visual_phase_failed=0;
}
/* A missed callback/reissue window is not an unknown synth. Recover a live
 * unstarted MOVE or an already-not-sent SAME/FRESH pending action. Preserve
 * retired event bytes and obtain a new bounded beat from the last proof. */
static int recover_unsent_continuous_scene(NG2Controller *p,uint64_t now,
    const NG2Scene *scene,uint64_t start,uint64_t end,uint64_t prefix){
    NG2ControllerEvent *e=event(p);NG2Motion still;NG2Decision before,latest;uint64_t budget;
    int i,passage=0,partial=0;
    int pending=p->s.input_state==0&&!p->s.current_command_id&&p->continuous_ticket_valid
        &&(p->continuous_pending==NG2_CONTINUOUS_SAME||p->continuous_pending==NG2_CONTINUOUS_FRESH)
        &&e&&e->outcome==3&&e->reason==NG2_REASON_SCREEN;
    const NG2Decision *expected=pending?&p->continuous_pending_choice:&p->command_choice;
    now=maximum(now,p->last_now);
    if((!pending&&(p->s.input_state!=1||p->s.current_command_id!=p->command.id))
        ||p->command.kind!=NG2_ACTION_MOVE||!p->command.id||p->finish_requested||p->s.terminal||p->s.goods
        ||!p->s.lead_confirmed||p->s.moves<=0||!p->latest_verified_ns
        ||p->command.direction<1||p->command.direction>4
        ||!e||e->command.id!=p->command.id||e->begin_ns||(!pending&&e->outcome)
        ||now<=p->command.deadline_ns)return 0;
    p->last_now=now;
    if(now-p->s.started_ns>=180*SECOND){finish(p,now,NG2_REASON_SESSION);return 1;}
    if(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND){finish(p,now,NG2_REASON_LIMIT);return 1;}
    if(!p->command_sync_deadline)p->sync_ns=p->latest_verified_ns;
    budget=sync_deadline(p);
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget){
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);return 1;
    }
    if(p->passage_active){
        if(pending||p->passage_wait_kind||p->continuous_pending||p->continuous_chain_count
            ||expected->reason!=10||expected->obstacle!=NG2_TILE_FLOOR
            ||!passage_floor(&p->before)||!passage_floor(scene)
            ||!safe_step(p,&p->before,p->command.direction)||!safe_step(p,scene,p->command.direction))return 0;
        for(i=0;i<NG2_TILE_COUNT;++i)
            if(p->before.protected_cells[i]||scene->protected_cells[i]
                ||p->before.tiles[i]==NG2_TILE_ITEM||scene->tiles[i]==NG2_TILE_ITEM)return 0;
        passage=1;
    }
    partial=p->opened_entry_parent&&p->before.goods==NG2_GOODS_PARTIAL
        &&scene->goods==NG2_GOODS_PARTIAL&&opened_entry_floor(p,scene);
    if(!p->have_scene||start>now||end>now||now-start>FRESH||prefix!=p->s.last_completed_id
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||(!partial&&(p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN))
        ||(!passage&&(p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE))
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT))return 0;
    if(memcmp(p->before.tiles,scene->tiles,NG2_TILE_COUNT)){
        if(pending||passage||partial||!unsent_quiet_approach_scene(p,scene,&latest))return 0;
    }else if(!choose_step(p,&p->before,&before)
        ||!choose_step(p,scene,&latest)
        ||!same_choice(&before,expected)||!same_choice(&before,&latest)
        ||!ng2_motion(&p->before,scene,p->command.direction,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    if(!pending)not_sent(p,now,NG2_REASON_LATE);
    if(partial){
        /* The old event keeps its expired window. Only a subsequent capture
         * begun after retirement may prove this fixed latest authority. */
        p->opened_entry_recovery_ns=now;
        p->gate_refresh_anchor=*scene;p->gate_refresh_choice=latest;
        p->gate_refresh_state=NG2_GATE_REFRESH_OBSERVE;p->gate_refresh_proof_id=0;
        p->gate_refresh_deadline=budget;p->gate_refresh_prefix=prefix;
        p->gate_refresh_previous=*scene;p->gate_refresh_previous_start=start;p->gate_refresh_previous_end=end;
        p->observation_refresh_active=1;
    }
    if(p->command_sync_deadline)p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    post_move_recover(p,now,NG2_RECOVERY_UNSENT_DEADLINE);
    memset(&p->command,0,sizeof(p->command));p->s.current_command_id=0;
    return 1;
}
static int recover_unsent_continuous(NG2Controller *p,uint64_t now){
    return recover_unsent_continuous_scene(p,now,&p->scene,p->s.last_capture_start_ns,
        p->s.last_capture_end_ns,p->last_observed_prefix);
}
/* Select and publish one new physical beat after a verified action. This is
 * not a retry of its old issued ticket, and never bypasses preparation. */
static int prepare_recovery_slot(NG2Controller *p,uint64_t now){
    uint64_t aligned,target,next,horizon,tail=p->s.lead_ns+50000000;
    if(p->recovery.mode!=NG2_RECOVERY_POST_MOVE)return 1;
    if(now>=sync_deadline(p)){
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);return 0;
    }
    if(p->beat_failed||!ng2_beat_model_valid(&p->model))return 0;
    if(now<p->model.last_ns||now-p->model.last_ns>FRESH){
        recovery_record(p,NG2_RECOVERY_MODEL_STALE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        clear_model(p);clear_recovery_slot(p);return 0;
    }
    if(p->model_capture_id<p->proof_capture_id)return 0;
    if(p->recovery_slot_target){
        int reason=0;
        if(!corrected(p,p->recovery_slot_target,p->recovery_slot_period,&aligned))reason=NG2_RECOVERY_ALIGNMENT;
        else if(now>p->recovery_slot_not_before-INITIAL_PREPARATION)reason=NG2_RECOVERY_PREPARATION;
        if(reason){
            recovery_record(p,reason,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
            clear_recovery_slot(p);p->s.next_target_ns=0;return 0;
        }
    }else{
        target=ng2_next_target(&p->model,now,p->s.lead_ns+INITIAL_PREPARATION);
        if(!target||target>=NS_LIMIT-p->model.period_ns){finish(p,now,NG2_REASON_SESSION);return 0;}
        next=target+p->model.period_ns;
        if(next<p->s.lead_ns||next-p->s.lead_ns>=NS_LIMIT-10000000){finish(p,now,NG2_REASON_SESSION);return 0;}
        horizon=minimum(p->s.last_capture_start_ns+FRESH,p->model.last_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
        horizon=minimum(horizon,session_bound(p));
        if(p->stationary_wait_parent)horizon=minimum(horizon,p->stationary_wait_parent);
        if(p->opened_entry_parent)horizon=minimum(horizon,p->opened_entry_parent);
        if(horizon<tail||target-p->s.lead_ns>horizon-tail){finish(p,now,NG2_REASON_STALE);return 0;}
        p->recovery_slot_target=target;p->recovery_slot_not_before=target-p->s.lead_ns;
        p->recovery_slot_period=p->model.period_ns;
        p->recovery_slot_deadline=minimum(p->recovery_slot_not_before+10000000,horizon-tail);
        p->recovery_slot_schedule=minimum(next-p->s.lead_ns+10000000,horizon);
        p->recovery_slot_visual=horizon;
    }
    p->s.next_target_ns=p->recovery_slot_target;
    if(p->recovery_slot_not_before-now>INITIAL_PUBLICATION)return 0;
    if(p->s.last_capture_start_ns<p->recovery_slot_not_before
        &&p->recovery_slot_not_before-p->s.last_capture_start_ns>CONTINUOUS_SOURCE)return 0;
    return 1;
}
/* A late committed MOVED can be current yet too old to acquire the next
 * beat's source permission. Retire only that unissued candidate; the old
 * ACK/event and all new-slot freshness/preparation checks remain unchanged. */
static void recover_late_verified_source(NG2Controller *p,uint64_t now){
    const NG2ControllerEvent *e=event(p);uint64_t not_before;
    if(p->finish_requested||p->s.terminal||p->s.goods||!p->have_scene
        ||p->s.phase!=NG2_PHASE_WALK||!p->s.lead_confirmed||p->s.moves<=0
        ||p->s.input_state||p->s.current_command_id||p->replan_pending||p->continuous_pending
        ||p->proof_reacquire||p->visual_phase_failed||p->beat_failed
        ||p->stationary_wait_active||p->gate_refresh_state||p->passage_wait_kind
        ||!p->proof_deadline||p->proof_deadline!=p->motion_wait.deadline_ns
        ||now>p->proof_deadline||now>p->schedule_deadline||now>p->next_deadline
        ||(p->next_update_deadline&&now>p->next_update_deadline)
        ||!p->next_nominal||!p->next_period||!ng2_beat_model_valid(&p->model)
        ||p->scene.state!=NG2_FLOOR||p->scene.goods!=NG2_GOODS_UNKNOWN
        ||p->command.kind!=NG2_ACTION_MOVE||p->command.direction<1||p->command.direction>4
        ||!e||memcmp(&e->command,&p->command,sizeof(p->command))||e->outcome!=2
        ||!e->begin_ns||!e->end_ns||e->end_ns!=p->ack_ns||e->begin_ns>e->end_ns
        ||e->motion!=NG2_MOVED||e->dx!=dx[p->command.direction]||e->dy!=dy[p->command.direction]
        ||p->s.last_completed_id!=p->command.id||p->last_observed_prefix!=p->command.id
        ||!p->proof_capture_id||p->proof_capture_id!=p->s.last_capture_id
        ||e->observed_capture_id!=p->proof_capture_id||p->motion_wait.active
        ||p->motion_wait.command_id!=p->command.id
        ||p->motion_wait.source_capture_id!=p->command.source_capture_id
        ||p->motion_wait.last_capture_id!=p->proof_capture_id||p->motion_wait.last_motion!=NG2_MOVED
        ||!p->motion_wait.attempts||p->latest_verified_ns!=p->observe_now
        ||p->s.last_capture_start_ns<p->ack_ns||p->s.last_capture_end_ns>now
        ||now<p->latest_verified_ns||p->s.next_target_ns<p->s.lead_ns)return;
    not_before=p->s.next_target_ns-p->s.lead_ns;
    if((now<not_before&&not_before-now>CONTINUOUS_PUBLICATION)
        ||p->s.last_capture_start_ns>=not_before
        ||not_before-p->s.last_capture_start_ns<=CONTINUOUS_SOURCE)return;
    if(p->command_sync_deadline){
        if(now>=p->command_sync_deadline||sync_deadline(p)>p->command_sync_deadline)return;
        p->recovery.mode=NG2_RECOVERY_POST_MOVE; /* Preserve the existing episode's bound. */
    }
    post_move_recover(p,now,NG2_RECOVERY_VISUAL_SCHEDULE);
}
/* A last, never-issued D3 may use its still-future physical beat when the
 * ordinary50ms preparation selected a beat beyond this route's fixed cap.
 * This local proposal grants no input and never changes an issued ticket. */
typedef struct {
    uint64_t target,not_before,period,deadline,schedule,visual;
} NG2UpperLastSlot;
static int upper_last_slot(NG2Controller *p,uint64_t now,NG2UpperLastSlot *slot){
    const NG2ControllerEvent *e=event(p);
    uint64_t target,aligned,period=p->model.period_ns,not_before,horizon,tail,next,deadline;
    if(!p->upper.active||p->upper.variant!=2||!p->restart_yield.s.enabled||p->upper.stage!=2
        ||p->upper.steps!=5||p->upper.inputs!=4||p->upper.horizontal!=2||p->upper.down!=2
        ||p->finish_requested||p->s.terminal||p->s.input_state||p->s.current_command_id
        ||p->s.inputs>=16||p->event_count>=EVENT_CAP||p->restart_yield.s.pending
        ||p->cycle.pending||p->cycle_assessing||p->cycle.candidate_latched
        ||p->cycle.status!=NG2_RING_OK||p->cycle.outcome!=NG2_RING_UNKNOWN
        ||p->cycle.coverage!=NG2_RING_COVERAGE_INCOMPLETE
        ||p->recovery.mode!=NG2_RECOVERY_POST_MOVE||p->replan_pending||p->continuous_pending
        ||!p->recovery_slot_target||!p->recovery_slot_period||!p->recovery_slot_visual
        ||!fresh(p,now)||!ng2_beat_model_valid(&p->model)||p->beat_failed
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH||p->model_capture_id<p->proof_capture_id
        ||!upper_identity(p)||!upper_floor(p,&p->scene)||!upper_same_zero(p,&p->scene)
        ||upper_budget(p,now,p->recovery_slot_target))return 0;
    /* The exact latest event is the known D2 unit. Any subsequent published,
     * NOT_SENT or UNKNOWN D3 makes this identity unavailable, even if a
     * later model nudges its numeric representation of that same beat. */
    if(!e||e->command.kind!=NG2_ACTION_MOVE||e->command.direction!=NG2_DOWN
        ||e->outcome!=2||e->motion!=NG2_MOVED||e->dx||e->dy!=1||!e->begin_ns
        ||e->end_ns!=p->ack_ns||now<e->end_ns||p->s.last_capture_start_ns<e->end_ns
        ||e->command.id!=p->upper.issued||e->command.id!=p->s.last_completed_id
        ||e->command.id!=p->cycle.prefix||e->command.id!=p->upper.prefix
        ||e->command.ordinal!=p->s.last_ordinal||e->command.ordinal!=p->upper.ordinal
        ||e->observed_capture_id!=p->cycle.capture_id
        ||memcmp(&e->command,&p->command,sizeof(p->command))||!p->command_period
        ||e->command.target_ns>=NS_LIMIT-p->command_period)return 0;
    target=ng2_next_target(&p->model,now,p->s.lead_ns);
    if(!target||target>=NS_LIMIT-period||target<p->s.lead_ns
        ||!corrected(p,e->command.target_ns+p->command_period,p->command_period,&aligned)
        ||target!=aligned||target>=p->recovery_slot_target
        ||!corrected(p,p->recovery_slot_target,p->recovery_slot_period,&aligned)
        ||aligned!=target+period||!upper_budget(p,now,target))return 0;
    not_before=target-p->s.lead_ns;
    if(not_before<=now||not_before-now>=INITIAL_PREPARATION
        ||not_before-now>INITIAL_PUBLICATION||not_before>=NS_LIMIT-10000000
        ||(p->s.last_capture_start_ns<not_before
            &&not_before-p->s.last_capture_start_ns>CONTINUOUS_SOURCE)
        ||p->s.last_capture_start_ns>=NS_LIMIT-FRESH||p->model.last_ns>=NS_LIMIT-FRESH
        ||p->s.lead_ns>=NS_LIMIT-50000000)return 0;
    tail=p->s.lead_ns+50000000;
    horizon=minimum(p->recovery_slot_visual,p->s.last_capture_start_ns+FRESH);
    horizon=minimum(horizon,p->model.last_ns+FRESH);horizon=minimum(horizon,session_bound(p));
    horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
    horizon=minimum(horizon,p->cycle.continuation_deadline_ns);horizon=minimum(horizon,p->upper.parent);
    if(horizon<tail||not_before>horizon-tail)return 0;
    deadline=minimum(not_before+10000000,minimum(p->recovery_slot_deadline,horizon-tail));
    next=target+period;
    if(deadline<not_before||now>deadline||next<p->s.lead_ns
        ||next-p->s.lead_ns>=NS_LIMIT-10000000)return 0;
    slot->target=target;slot->not_before=not_before;slot->period=period;slot->deadline=deadline;
    slot->schedule=minimum(p->recovery_slot_schedule,minimum(next-p->s.lead_ns+10000000,horizon));
    slot->visual=horizon;return 1;
}
static int upper_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    int d,prepared,last=0;NG2UpperLastSlot slot={0};
    if(!p->upper.active||p->upper.stage>=6)return -2;
    /* The frozen parent bounds MOVE, not the normal worker's data budget. */
    if(p->cycle.pending){
        if(now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    if(p->upper.level!=p->cycle.level_id||now>p->upper.parent){
        if(p->s.input_state==3)end_visual_wait(p);
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 0;
    }
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns){not_sent(p,now,NG2_REASON_LATE);cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);}
        return 0;
    }
    if(p->s.input_state==3){
        if(now>p->motion_wait.deadline_ns){end_visual_wait(p);cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);}
        return 0;
    }
    if(p->upper.stage!=2)return 0;
    if(!upper_identity(p)||p->upper.inputs>=p->upper.steps||p->s.inputs>=16||!upper_floor(p,&p->scene)){
        upper_hold(p);return 0;
    }
    if(!fresh(p,now))return 0;
    prepared=prepare_recovery_slot(p,now);
    if(!p->finish_requested&&upper_last_slot(p,now,&slot)){
        p->recovery_slot_target=slot.target;p->recovery_slot_not_before=slot.not_before;
        p->recovery_slot_period=slot.period;p->recovery_slot_deadline=slot.deadline;
        p->recovery_slot_schedule=slot.schedule;p->recovery_slot_visual=slot.visual;
        p->s.next_target_ns=slot.target;prepared=last=1;
    }
    if(!prepared)return 0;
    if(!upper_budget(p,now,p->recovery_slot_target)){upper_hold(p);return 0;}
    d=upper_direction(p);memset(&p->command_choice,0,sizeof(p->command_choice));
    p->command_choice.direction=d;p->command_choice.reason=5;
    p->command_choice.target_x=dx[d];p->command_choice.target_y=dy[d];p->command_choice.obstacle=NG2_TILE_FLOOR;
    if(reserve(p,now,NG2_ACTION_MOVE,d,p->recovery_slot_target,out)==1){
        p->upper.stage=3;p->upper.issued=out->id;p->upper.ordinal=out->ordinal;return 1;
    }
    if(last){clear_recovery_slot(p);p->s.next_target_ns=0;if(!p->finish_requested)upper_hold(p);}
    return 0;
}

static int lower_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    if(!p->lower.active||p->lower.stage>=6)return -2;
    if(p->cycle.pending){
        if(now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    if(p->lower.level!=p->cycle.level_id||now>p->lower.parent){
        if(p->s.input_state==3)end_visual_wait(p);
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 0;
    }
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    if(p->s.input_state==3){
        if(now>p->motion_wait.deadline_ns){end_visual_wait(p);cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);}
        return 0;
    }
    if(p->lower.stage!=2)return 0;
    if(p->lower.inputs>=p->lower.steps||p->s.inputs>=16||!lower_parent_fits(p)){
        cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_LIMIT);return 0;
    }
    if(!fresh(p,now)||!prepare_recovery_slot(p,now))return 0;
    memset(&p->command_choice,0,sizeof(p->command_choice));p->command_choice.direction=NG2_DOWN;
    p->command_choice.reason=5;p->command_choice.target_y=1;p->command_choice.obstacle=NG2_TILE_FLOOR;
    if(reserve(p,now,NG2_ACTION_MOVE,NG2_DOWN,p->recovery_slot_target,out)==1){
        p->lower.stage=3;p->lower.issued=out->id;p->lower.ordinal=out->ordinal;return 1;
    }
    return 0;
}
static int entry_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    if(!p->entry.active||p->entry.stage>=6)return -2;
    if(p->entry.level!=p->cycle.level_id){
        if(p->s.input_state==3)end_visual_wait(p);
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 0;
    }
    /* The parent bounds observational inputs, not the current normal
     * worker's immutable data budget or its possible positive result. */
    if(p->cycle.pending){
        if(now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    if(now>p->entry.parent){
        if(p->s.input_state==3)end_visual_wait(p);
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);return 0;
    }
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        return 0;
    }
    if(p->s.input_state==3){
        if(now>p->motion_wait.deadline_ns){end_visual_wait(p);cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);}
        return 0;
    }
    if(p->entry.stage!=2)return 0;
    if(p->entry.inputs>=2||p->s.inputs>=16||!entry_identity(p)){
        cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_LIMIT);return 0;}
    if(!fresh(p,now)||!prepare_recovery_slot(p,now))return 0;
    p->command_choice=p->entry.choice;
    if(reserve(p,now,NG2_ACTION_MOVE,NG2_UP,p->recovery_slot_target,out)==1){
        p->entry.stage=3;p->entry.issued=out->id;p->entry.ordinal=out->ordinal;return 1;}
    return 0;
}
static int restart_yield_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    NG2RestartYield *y=&p->restart_yield;int result;
    if(!y->s.pending)return -2;
    if(!restart_yield_basis(p,now))restart_yield_invalidate(p);
    if(p->cycle.pending&&now>p->cycle.deadline_ns)cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
    if(y->s.invalid){finish(p,now,p->s.reason?p->s.reason:NG2_REASON_CAPTURE);return -2;}
    if(p->campaign.enabled)return 0; /* Runtime's real drain may only end DATA. */
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns){restart_yield_invalidate(p);not_sent(p,now,NG2_REASON_LATE);finish(p,now,NG2_REASON_LATE);}
        return 0;
    }
    if(p->s.input_state||!y->s.permitted||!ng2_controller_restart_yield_ready(p,now))return 0;
    if(y->permit_capture!=p->s.last_capture_id||y->permit_start!=p->s.last_capture_start_ns){y->s.permitted=0;return 0;}
    p->handoff.kind=NG2_HANDOFF_RESTARTED_BUDGET;p->handoff.reason=NG2_REASON_LIMIT;
    p->handoff.qualified_ns=now;p->handoff.source_capture_id=y->permit_capture;
    p->handoff.source_prefix=y->s.restart_command_id;
    finish(p,now,NG2_REASON_LIMIT);p->final_pause_attempted=1;
    result=reserve(p,now,NG2_ACTION_PAUSE,0,0,out);
    if(result==1){
        y->pause=out->id;p->handoff_pause_command=out->id;p->handoff_pause_bound=1;
        p->handoff.completed_prefix=out->id;p->cycle.pause_source_capture_id=out->source_capture_id;
    }else restart_yield_invalidate(p);
    return result;
}
static int cycle_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    if(p->cycle.pending&&((p->cycle.capture_id&&now>p->cycle.deadline_ns)
        ||(!p->cycle.capture_id&&now-p->cycle.hold_started_ns>=TRANSITION))){
        if(p->cycle.capture_id&&cycle_retry_wait(p,now,p->cycle.worker_started_ns==0))return 0;
        if(p->cycle.worker_started_ns&&p->cycle.state==NG2_CYCLE_ASSESS&&p->cycle.full_seen&&!p->cycle.partial
            &&!p->s.input_state&&!p->cycle_full_spent&&!p->entry.active&&!p->lower.active
            &&cycle_retry_source_qualified(&p->cycle_anchor)
            &&now<=p->cycle.continuation_deadline_ns)return 0;
        cycle_failure(p,now,p->cycle.capture_id?NG2_RING_DEADLINE:NG2_RING_KERNEL,
            p->cycle.capture_id?NG2_REASON_LATE:NG2_REASON_CAPTURE);
    }
    if(p->cycle.state==NG2_CYCLE_OBSERVE_MORE&&now>p->cycle.continuation_deadline_ns)
        cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
    if(p->cycle_current_active==1&&p->cycle.pending)return 0;
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns){
            not_sent(p,now,NG2_REASON_LATE);cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_LATE);
        }else return 0;
    }
    if(p->s.input_state==3){
        if(p->command.kind==NG2_ACTION_MOVE&&now>p->motion_wait.deadline_ns){
            end_visual_wait(p);cycle_failure(p,now,NG2_RING_DEADLINE,NG2_REASON_LATE);
        }else{
            if(now>=p->ack_ns&&now-p->ack_ns>=TRANSITION)
                terminal(p,now,p->command.kind==NG2_ACTION_RESTART?NG2_REASON_RESTART:NG2_REASON_CAPTURE);
            return 0;
        }
    }
    if(p->have_scene&&p->scene.state==NG2_PAUSE&&fresh(p,now)&&p->cycle.pause_capture_id){
        p->s.paused=1;
        if(p->cycle.outcome==NG2_RING_NEGATIVE&&p->cycle.status==NG2_RING_OK
            &&p->cycle.durable_ns&&!p->cycle_storage_error&&!p->cycle_restart_unproved){
            int result;
            if(p->cycle.completed_shops>=4||p->s.restarts>=12){
                mint_negative_handoff(p,now);terminal(p,now,NG2_REASON_LIMIT);return 0;
            }
            if(!p->scene.restart_label||now<p->ack_ns||now-p->ack_ns<UI_SETTLE_NS)return 0;
            p->restart_pending=1;result=reserve(p,now,NG2_ACTION_RESTART,0,0,out);
            if(result==1){p->cycle.restart_command_id=out->id;p->cycle.state=NG2_CYCLE_NEGATIVE_RESTART;}
            return result;
        }
        if(!p->cycle.pending&&(p->cycle.durable_ns||p->cycle_storage_error))
            terminal(p,now,p->s.reason);
        return 0;
    }
    if(p->cycle_full_framing){
        if(p->cycle_full_framing!=2)return 0;
        if(now>p->cycle.continuation_deadline_ns||p->s.inputs>=16){
            cycle_failure(p,now,NG2_RING_KERNEL,NG2_REASON_LIMIT);return 0;}
        if(!fresh(p,now)||p->last_observed_prefix!=p->cycle.prefix)return 0;
        if(!prepare_recovery_slot(p,now))return 0;
        p->command_choice=p->cycle_full_choice;
        if(reserve(p,now,NG2_ACTION_MOVE,p->cycle_full_choice.direction,p->recovery_slot_target,out)==1){
            p->cycle_full_framing=3;return 1;}
        return 0;
    }
    if(p->cycle.next_floor_capture_id&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART)return 0;
    if(p->cycle_full_data_active&&p->cycle.pending)return 0;
    if(p->cycle.state==NG2_CYCLE_OBSERVE_MORE||(p->cycle.partial&&!p->cycle.full_seen&&p->cycle.pending))return 0;
    if(!p->cycle_pause_attempted&&!p->need_fresh_cleanup&&fresh(p,now)&&p->scene.state==NG2_FLOOR
        &&p->last_observed_prefix==p->s.last_completed_id&&pause_ui_ready(p,now)){
        int result;
        p->cycle_pause_attempted=1;result=reserve(p,now,NG2_ACTION_PAUSE,0,0,out);
        if(result==1)p->cycle.pause_source_capture_id=out->source_capture_id;
        return result;
    }
    if(now>=p->cycle.hold_started_ns&&now-p->cycle.hold_started_ns>=TRANSITION)
        terminal(p,now,p->s.reason?p->s.reason:NG2_REASON_CAPTURE);
    return 0;
}
static int initial_restart_tick(NG2Controller *p,uint64_t now,NG2Command *out){
    NG2InitialRestart *initial=&p->initial_restart;int result;
    if(!initial_restart_active(p)||p->finish_requested)return -2;
    if(p->cycle.candidate_latched){initial->stage=NG2_INITIAL_HELD;return -2;}
    if(initial->parent&&now>=initial->parent){
        initial->stage=NG2_INITIAL_HELD;finish(p,now,NG2_REASON_RESTART);return -2;
    }
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns){not_sent(p,now,NG2_REASON_LATE);
            initial->stage=NG2_INITIAL_HELD;finish(p,now,NG2_REASON_LATE);}
        return 0;
    }
    if(p->s.input_state)return 0;
    if(initial->stage==NG2_INITIAL_VETO){
        if(!p->cycle.pending)return 0;
        result=cycle_tick(p,now,out);
        if(result==1){
            if(out->kind!=NG2_ACTION_PAUSE){not_sent(p,now,NG2_REASON_SCREEN);
                initial->stage=NG2_INITIAL_HELD;finish(p,now,NG2_REASON_SCREEN);memset(out,0,sizeof(*out));return 0;}
            initial->pause=out->id;
        }
        return result;
    }
    if(!p->have_scene||!fresh(p,now)||!initial->parent
        ||p->last_observed_prefix!=p->s.last_completed_id
        ||!restart_yield_ui_source(p,p->s.last_capture_id,p->s.last_capture_start_ns,now,0))return 0;
    if(initial->stage==NG2_INITIAL_PAUSE&&p->scene.state==NG2_FLOOR&&pause_ui_ready(p,now)){
        result=reserve(p,now,NG2_ACTION_PAUSE,0,0,out);
        if(result==1)initial->pause=out->id;
        return result;
    }
    if(initial->stage==NG2_INITIAL_RESTART&&p->scene.state==NG2_PAUSE&&p->scene.restart_label
        &&!p->cycle.pending&&!p->cycle_late_worker&&p->s.restarts<12
        &&(!initial->pause||(now>=p->ack_ns&&now-p->ack_ns>=UI_SETTLE_NS))){
        result=reserve(p,now,NG2_ACTION_RESTART,0,0,out);
        if(result==1){initial->restart=out->id;initial->stage=NG2_INITIAL_FLOOR;
            event(p)->reason=NG2_REASON_RESTART;}
        return result;
    }
    return 0;
}
static int initial_restart_begin_reason(NG2Controller *p,uint64_t now){
    const NG2InitialRestart *initial=&p->initial_restart;
    if(!initial_restart_active(p))return 0;
    if(!initial->parent||now>=initial->parent||!fresh(p,now)
        ||p->last_observed_prefix!=p->s.last_completed_id
        ||!restart_yield_ui_source(p,p->s.last_capture_id,p->s.last_capture_start_ns,now,0))return NG2_REASON_SCREEN;
    if(p->command.kind==NG2_ACTION_RESTART){
        uint64_t prefix=initial->pause?initial->pause:initial->source_prefix;
        if(initial->stage!=NG2_INITIAL_FLOOR||p->command.id!=initial->restart
            ||p->s.last_completed_id!=prefix||p->scene.state!=NG2_PAUSE||!p->scene.restart_label
            ||p->cycle.pending||p->cycle_late_worker||p->cycle.candidate_latched
            ||(initial->pause&&(now<p->ack_ns||now-p->ack_ns<UI_SETTLE_NS)))return NG2_REASON_SCREEN;
    }else if(p->command.kind==NG2_ACTION_PAUSE){
        if(p->command.id!=initial->pause||p->scene.state!=NG2_FLOOR
            ||p->s.last_completed_id!=initial->source_prefix)return NG2_REASON_SCREEN;
    }else return NG2_REASON_SCREEN;
    return 0;
}
int ng2_controller_tick(NG2Controller *p,uint64_t now,int32_t front,int32_t locked,int32_t owner,NG2Command *out){
    NG2Decision choice;int guard;
    if(out)memset(out,0,sizeof(*out));
    if(!p||!out||!valid_time(now)||now<p->last_now)return -1;
    p->last_now=now;
    if(p->s.terminal)return 0;
    revoke_clear_handoff(p,NULL,now);
    guard=guards(front,locked,owner);
    if(guard){ng2_controller_cancel(p,now,guard);return 0;}
    if(now-p->s.started_ns>=180*SECOND||campaign_expired(p,now)){ng2_controller_cancel(p,now,NG2_REASON_SESSION);return 0;}
    if(p->have_scene&&p->s.last_capture_end_ns>now){ng2_controller_cancel(p,now,NG2_REASON_CAPTURE);return 0;}
    if(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND)finish(p,now,NG2_REASON_LIMIT);
    if(p->restart_yield.s.enabled&&!p->restart_yield.s.initial_pause_seen){
        if(now-p->s.started_ns>=TRANSITION)terminal(p,now,NG2_REASON_SCREEN);
        return 0;
    }
    {int handled=restart_yield_tick(p,now,out);if(handled!=-2)return handled;}
    if(p->restart_yield.s.enabled&&!p->restart_yield.s.invalid&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART
        &&p->cycle.next_floor_capture_id)return 0; /* Durable outcome has no UI authority yet. */
    if(p->stationary_wait_active&&now>=stationary_wait_limit(p))finish(p,now,NG2_REASON_BEAT);
    {int handled=irregular_tick(p,now,out);if(handled!=-2)return handled;}
    if(p->s.input_state==2||p->s.input_state==4)return 0;
    {int handled=initial_restart_tick(p,now,out);if(handled!=-2)return handled;}
    if(p->upper.active&&!p->finish_requested){int handled=upper_tick(p,now,out);if(handled!= -2)return handled;}
    if(p->lower.active&&!p->finish_requested){int handled=lower_tick(p,now,out);if(handled!= -2)return handled;}
    if(p->entry.active&&!p->finish_requested){int handled=entry_tick(p,now,out);if(handled!= -2)return handled;}
    if(cycle_holding(p)&&!p->finish_requested)return cycle_tick(p,now,out);
    if(initial_recoverable(p)&&now>=sync_deadline(p)){
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);
    }
    if(!p->finish_requested&&p->recovery.mode==NG2_RECOVERY_POST_MOVE&&now>=sync_deadline(p)){
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);return 0;
    }
    if(p->s.input_state==1){
        if(p->command_sync_deadline&&now>=p->command_sync_deadline){
            recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
            finish(p,now,NG2_REASON_BEAT);return 0;
        }
        if(now>p->command.deadline_ns){
            if(initial_recover(p,NG2_RECOVERY_UNSENT_DEADLINE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id))return 0;
            if(recover_unsent_continuous(p,now))return 0;
            not_sent(p,now,NG2_REASON_LATE);finish(p,now,NG2_REASON_LATE);
        }
        else return 0;
    }
    if(p->s.input_state==0&&p->continuous_pending&&now>p->command.deadline_ns
        &&recover_unsent_continuous(p,now))return 0;
    if(p->s.input_state==3){
        uint64_t timeout=p->command.kind==NG2_ACTION_PAUSE&&p->finish_requested?FRESH:TRANSITION;
        if(p->command.kind==NG2_ACTION_MOVE&&now>p->motion_wait.deadline_ns){
            recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
            end_visual_wait(p);finish(p,now,NG2_REASON_LATE);
        }else{
            if(now>=p->ack_ns&&now-p->ack_ns>=timeout){terminal(p,now,p->command.kind==NG2_ACTION_RESTART?NG2_REASON_RESTART:NG2_REASON_CAPTURE);}
            return 0;
        }
    }
    if(p->proof_deadline&&!p->finish_requested){
        if(now>p->proof_deadline){
            recovery_record(p,NG2_RECOVERY_VISUAL_SCHEDULE,NG2_RECOVERY_ACTUAL_TICK,now,p->proof_capture_id);
            p->proof_deadline=0;finish(p,now,NG2_REASON_LATE);return 0;
        }
        /* The stationary entrance path already recorded its old model before
         * clearing it. Check the same parent horizon without recording twice. */
        if(p->stationary_gate_recovery_pending)p->stationary_gate_recovery_pending=0;
        else if(p->proof_reacquire||p->visual_phase_failed||p->beat_failed||!ng2_beat_model_valid(&p->model)
            ||now>p->schedule_deadline||!p->s.next_target_ns||now>p->next_deadline
            ||(p->next_update_deadline&&now>p->next_update_deadline))
            post_move_recover(p,now,p->visual_phase_failed||p->beat_failed?
                NG2_RECOVERY_VISUAL_PHASE:NG2_RECOVERY_VISUAL_SCHEDULE);
        else recover_late_verified_source(p,now);
        p->proof_deadline=0;p->proof_reacquire=0;
    }
    if(!p->finish_requested&&initial_slot_active(p)){
        uint64_t aligned;
        if(p->beat_failed||!ng2_beat_model_valid(&p->model)||now<p->model.last_ns
            ||now-p->model.last_ns>FRESH
            ||!corrected(p,p->initial_slot_target,p->initial_slot_period,&aligned)){
            if(initial_recover(p,NG2_RECOVERY_ALIGNMENT,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id))return 0;
            finish(p,now,NG2_REASON_BEAT);return 0;
        }
        if(!p->initial_ticket_valid&&now>p->initial_slot_not_before-INITIAL_PREPARATION){
            if(initial_recover(p,NG2_RECOVERY_PREPARATION,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id))return 0;
            finish(p,now,NG2_REASON_LATE);return 0;
        }
    }
    if(p->finish_requested){
        if(p->have_scene&&p->scene.state==NG2_PAUSE&&fresh(p,now)){p->s.paused=1;terminal(p,now,p->s.reason);return 0;}
        if(!p->final_pause_attempted&&!p->need_fresh_cleanup&&fresh(p,now)&&p->scene.state==NG2_FLOOR
            &&p->last_observed_prefix==p->s.last_completed_id&&pause_ui_ready(p,now)){
            p->final_pause_attempted=1;return reserve(p,now,NG2_ACTION_PAUSE,0,0,out);}
        if(now>=p->finish_ns&&now-p->finish_ns>=TRANSITION)terminal(p,now,p->s.reason);
        return 0;
    }
    if(!p->have_scene){if(now-p->s.started_ns>=TRANSITION)terminal(p,now,NG2_REASON_CAPTURE);return 0;}
    if(!fresh(p,now)){finish(p,now,NG2_REASON_STALE);return 0;}
    if(p->scene.state==NG2_UNKNOWN){if(now-p->transition_ns>=TRANSITION)terminal(p,now,NG2_REASON_SCREEN);return 0;}
    if(p->s.phase==NG2_PHASE_SEARCH&&p->scene.state==NG2_PAUSE)return reserve(p,now,NG2_ACTION_RESUME,0,0,out);
    if(p->s.phase==NG2_PHASE_PAUSE){
        if(p->scene.state==NG2_PAUSE&&p->scene.restart_label&&now>=p->ack_ns&&now-p->ack_ns>=UI_SETTLE_NS){
            if(p->s.restarts>=12){finish(p,now,NG2_REASON_LIMIT);return 0;}
            p->restart_pending=1;return reserve(p,now,NG2_ACTION_RESTART,0,0,out);}
        if(now>=p->ack_ns&&now-p->ack_ns>=TRANSITION)terminal(p,now,NG2_REASON_RESTART);
        return 0;
    }
    if(p->scene.state!=NG2_FLOOR){finish(p,now,NG2_REASON_SCREEN);return 0;}
    if(p->initial_view_pending||p->initial_candidate_waiting){
        if(!p->s.walk_started_ns&&now>=p->transition_ns&&now-p->transition_ns>=TRANSITION)
            finish(p,now,NG2_REASON_SCREEN);
        return 0;
    }
    if(p->s.phase==NG2_PHASE_FLOOR&&p->scene.gold_state==NG2_GOLD_CLEAR){
        if(p->passage_unlocalized_gold){finish(p,now,NG2_REASON_NO_PATH);return 0;}
        if(p->scene.goods!=NG2_GOODS_UNKNOWN){finish(p,now,NG2_REASON_PARTIAL_GOODS);return 0;}
        if(!clear_gold_floor(&p->scene)){finish(p,now,NG2_REASON_SCREEN);return 0;}
        if(p->s.restarts>=12){mint_clear_handoff(p,now);finish(p,now,NG2_REASON_LIMIT);return 0;}
        if(!pause_ui_ready(p,now))return 0;
        memcpy(p->restart_fingerprint,p->scene.fingerprint,48);p->restart_baseline_valid=1;p->restart_intent=1;
        return reserve(p,now,NG2_ACTION_PAUSE,0,0,out);
    }
    if(p->passage_wait_kind){
        if(now>=p->passage_wait_horizon){finish(p,now,NG2_REASON_BEAT);return 0;}
        if(!p->passage_wait_deadline&&ng2_beat_model_valid(&p->model))
            p->passage_wait_deadline=minimum(now+2*p->model.period_ns,p->passage_wait_horizon);
        if(p->passage_wait_deadline&&now>=p->passage_wait_deadline){
            if(p->passage_wait_kind==PASSAGE_WAIT_GOAL||p->passage_wait_kind==PASSAGE_WAIT_BLOCKED)
                passage_next_candidate(p,&p->scene,now,0);
            else finish(p,now,NG2_REASON_NO_PATH);
        }
        return 0;
    }
    if(!p->s.walk_started_ns){
        if(p->scene.gold_state==NG2_GOLD_CANDIDATE||p->scene.gold_state==NG2_GOLD_EDGE_DOWN)
            start_floor(p,&p->scene,p->s.last_capture_id,now);
        else if(now-p->transition_ns>=TRANSITION)finish(p,now,NG2_REASON_SCREEN);
        return 0;
    }
    if(p->replan_pending&&(!ng2_beat_model_valid(&p->model)||now>p->initial_ticket.deadline_ns)){
        int reason=now>p->initial_ticket.deadline_ns?NG2_REASON_LATE:NG2_REASON_BEAT;
        if(initial_recover(p,reason==NG2_REASON_LATE?NG2_RECOVERY_UNSENT_DEADLINE:NG2_RECOVERY_MODEL_STALE,
            NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id))return 0;
        p->replan_pending=0;finish(p,now,reason);return 0;
    }
    if(p->continuous_pending&&(!ng2_beat_model_valid(&p->model)||now>p->continuous_ticket.deadline_ns
        ||now>continuous_horizon(p))){
        int reason=now>p->continuous_ticket.deadline_ns?NG2_REASON_LATE:NG2_REASON_BEAT;
        p->continuous_pending=0;finish(p,now,reason);return 0;
    }
    if(p->continuous_pending&&p->passage_source.refreshed&&!passage_source_proof(p,&p->scene,now)){
        p->continuous_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(p->passage_release_proof_id&&p->model_capture_id<p->passage_release_proof_id)return 0;
    if(!ng2_beat_model_valid(&p->model)){
        if(p->recovery.mode==NG2_RECOVERY_POST_MOVE){prepare_recovery_slot(p,now);return 0;}
        if(now-p->sync_ns>=12*SECOND)finish(p,now,NG2_REASON_BEAT);
        return 0;
    }
    if(now<p->model.last_ns||now-p->model.last_ns>FRESH){
        if(initial_recover(p,NG2_RECOVERY_MODEL_STALE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id))return 0;
        if(p->recovery.mode==NG2_RECOVERY_POST_MOVE){prepare_recovery_slot(p,now);return 0;}
        finish(p,now,NG2_REASON_BEAT);return 0;
    }
    if(!prepare_recovery_slot(p,now))return 0;
    if(p->gate_refresh_state
        &&(p->gate_refresh_state==NG2_GATE_REFRESH_OBSERVE||!p->gate_refresh_proof_id
            ||p->gate_refresh_proof_id!=p->s.last_capture_id
            ||p->model_capture_id<p->gate_refresh_proof_id))return 0;
    if(p->stationary_wait_active&&!stationary_wait_proof(p,&p->scene,now)){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(p->s.inputs>=16){finish(p,now,NG2_REASON_LIMIT);return 0;}
    if(p->scene.gold_state==NG2_GOLD_EDGE_DOWN
        &&(p->edge_sent||level_inputs(p)||level_moves(p)||p->s.lead_confirmed||!edge_floor(&p->scene))){
        finish(p,now,NG2_REASON_NO_PATH);return 0;
    }
    /* Refit is not authority to choose another route. Re-prove the original
     * stationary entrance immediately before publishing its sole new ticket. */
    if((p->stationary_gate_retry_waiting==NG2_GATE_RETRY_REFIT&&!stationary_gate_proof(p,&p->scene,now))
        ||(p->stationary_gate_retry_waiting==NG2_GATE_RETRY_ISSUED&&!stationary_gate_scene(p,&p->scene))){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(!choose_step(p,&p->scene,&choice)){
        finish(p,now,choice.reason==2?NG2_REASON_PARTIAL_GOODS:NG2_REASON_NO_PATH);return 0;}
    if(p->have_anchor&&!p->s.lead_confirmed&&(!same_gold(&p->retune_anchor,&p->scene)||choice.direction!=p->retune_direction
        ||!safe_step(p,&p->scene,choice.direction))){finish(p,now,NG2_REASON_MOVEMENT);return 0;}
    if(p->recovery.mode==NG2_RECOVERY_POST_MOVE){
        p->s.next_target_ns=p->recovery_slot_target;
    }else if(p->replan_pending){
        uint64_t aligned;
        if(level_inputs(p)||level_moves(p)||p->s.lead_confirmed||choice.direction!=p->initial_ticket.direction
            ||!safe_step(p,&p->scene,choice.direction)||now>p->initial_ticket.deadline_ns
            ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned)){
            p->replan_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        p->s.next_target_ns=p->initial_ticket.target_ns;
    }else if(p->continuous_pending){
        uint64_t aligned;
        int valid_choice=p->continuous_pending==NG2_CONTINUOUS_FRESH?
            same_choice(&choice,&p->continuous_pending_choice):
            same_continuous_action(&choice,&p->command_choice)&&safe_step(p,&p->scene,choice.direction);
        if(!valid_choice
            ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned)){
            p->continuous_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        p->s.next_target_ns=p->continuous_ticket.target_ns;
    }else if(p->s.lead_confirmed){
        if(!p->s.next_target_ns||now>p->next_deadline||next_slot_expired(p,now)){finish(p,now,NG2_REASON_LATE);return 0;}
        p->next_update_deadline=0;
        if(p->s.moves>0&&p->next_nominal&&p->next_period){
            uint64_t not_before;
            if(p->s.next_target_ns<p->s.lead_ns){finish(p,now,NG2_REASON_LATE);return 0;}
            not_before=p->s.next_target_ns-p->s.lead_ns;
            /* Only this unreserved ordinal waits for a recent acquisition.
             * Issued SAME/FRESH tickets above retain their original bounds. */
            if(now<not_before&&not_before-now>CONTINUOUS_PUBLICATION)return 0;
            if(p->s.last_capture_start_ns<not_before&&not_before-p->s.last_capture_start_ns>CONTINUOUS_SOURCE)return 0;
        }
    }else if(!level_inputs(p)&&!level_moves(p)&&!p->initial_ticket_valid){
        uint64_t horizon,tail=p->s.lead_ns+50000000;
        if(!p->initial_slot_target){
            uint64_t next;
            p->s.next_target_ns=ng2_next_target(&p->model,now,p->s.lead_ns+INITIAL_PREPARATION);
            if(!p->s.next_target_ns){finish(p,now,NG2_REASON_BEAT);return 0;}
            if(p->s.next_target_ns>=NS_LIMIT-p->model.period_ns){finish(p,now,NG2_REASON_SESSION);return 0;}
            next=p->s.next_target_ns+p->model.period_ns;
            if(next<p->s.lead_ns||next-p->s.lead_ns>=NS_LIMIT-10000000){finish(p,now,NG2_REASON_SESSION);return 0;}
            horizon=minimum(p->s.last_capture_start_ns+FRESH,p->model.last_ns+FRESH);
            horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
            horizon=minimum(horizon,session_bound(p));
            if(horizon<tail||p->s.next_target_ns-p->s.lead_ns>horizon-tail){finish(p,now,NG2_REASON_STALE);return 0;}
            p->initial_slot_target=p->s.next_target_ns;
            p->initial_slot_not_before=p->initial_slot_target-p->s.lead_ns;
            p->initial_slot_period=p->model.period_ns;
            p->initial_slot_deadline=minimum(p->initial_slot_not_before+10000000,horizon-tail);
            p->initial_slot_motion_deadline=minimum(next-p->s.lead_ns+10000000,horizon);
            p->initial_slot_visual_deadline=horizon;
        }
        p->s.next_target_ns=p->initial_slot_target;
        if(now>p->initial_slot_not_before-INITIAL_PREPARATION){finish(p,now,NG2_REASON_LATE);return 0;}
        if(p->initial_slot_not_before-now>INITIAL_PUBLICATION)return 0;
    }else p->s.next_target_ns=ng2_next_target(&p->model,now,p->s.lead_ns);
    if(!p->s.next_target_ns){finish(p,now,NG2_REASON_BEAT);return 0;}
    p->s.phase=NG2_PHASE_WALK;
    p->command_choice=choice;
    return reserve(p,now,NG2_ACTION_MOVE,choice.direction,p->s.next_target_ns,out);
}
int ng2_controller_begin(NG2Controller *p,uint64_t id,uint64_t now,int32_t front,int32_t locked,int32_t owner){
    int reason;NG2ControllerEvent *e;uint64_t tail,horizon,aligned;
    if(!p||!valid_time(now)||p->s.terminal||p->s.input_state!=1||id!=p->command.id)return 0;
    if(campaign_expired(p,now)){not_sent(p,now,NG2_REASON_SESSION);terminal(p,now,NG2_REASON_SESSION);return 0;}
    if(irregular_active(p))return irregular_begin(p,id,now,front,locked,owner);
    if(p->command.kind==NG2_ACTION_DEATH_CONTINUE)return 0;
    if(p->irregular.enabled&&p->irregular_death_wait)return 0;
    revoke_clear_handoff(p,NULL,now);
    if(p->cycle_enabled&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART
        &&p->command.kind==NG2_ACTION_RESTART&&!p->cycle.intent_ns)return 0;
    reason=guards(front,locked,owner);
    if(!reason)reason=initial_restart_begin_reason(p,now);
    if(!reason&&p->restart_yield.s.pending){
        NG2RestartYield *y=&p->restart_yield;
        if(p->command.kind!=NG2_ACTION_PAUSE)reason=NG2_REASON_SCREEN;
        else if(y->pause==id&&(!restart_yield_basis(p,now)||!y->s.permitted
            ||p->command.source_capture_id!=y->permit_capture||p->command.source_start_ns!=y->permit_start
            ||p->s.last_capture_id!=y->permit_capture||p->s.last_capture_start_ns!=y->permit_start
            ||p->last_observed_prefix!=y->s.restart_command_id||p->cycle.pending||(y->required&~y->done)
            ||!restart_yield_ui_source(p,p->s.last_capture_id,p->s.last_capture_start_ns,now,0)))reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->cycle_enabled&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART
        &&p->command.kind==NG2_ACTION_RESTART
        &&(p->cycle_storage_error||!p->cycle.durable_ns||p->cycle.restart_command_id!=id
            ||p->scene.state!=NG2_PAUSE||!p->scene.restart_label
            ||p->last_observed_prefix!=p->s.last_completed_id||!fresh(p,now)))reason=NG2_REASON_SCREEN;
    if(!reason&&p->cycle_enabled&&p->cycle.state==NG2_CYCLE_NEGATIVE_RESTART
        &&p->command.kind==NG2_ACTION_RESTART&&p->s.walk_started_ns
        &&now-p->s.walk_started_ns>=45*SECOND)reason=NG2_REASON_LIMIT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->cycle_partial_credit
        &&(p->s.last_completed_id!=p->cycle_credit_prefix||now>p->cycle.continuation_deadline_ns
            ||!cycle_partial_relation(p,&p->scene)))reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->cycle_full_framing){
        NG2Motion still={0};
        if(p->cycle_full_framing!=3||p->s.last_completed_id!=p->cycle.prefix
            ||now>p->cycle.continuation_deadline_ns||cycle_full_static(p,&p->scene,&still)
            ||!same_choice(&p->command_choice,&p->cycle_full_choice))reason=NG2_REASON_SCREEN;
        if(p->cycle_current_active&&(!cycle_current_identity(p)||p->cycle_current_proofs!=2
            ||p->model_capture_id<p->cycle_current_proof_id))reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->upper.active){
        NG2Motion still={0};
        if(p->upper.stage!=3||p->upper.inputs>=p->upper.steps||p->command.id!=p->upper.issued
            ||p->command.direction!=upper_direction(p)||now>p->upper.parent
            ||!upper_budget(p,now,p->command.target_ns)||upper_begin_static(p,&p->scene,&still))reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->entry.active){
        NG2Motion still={0};
        if(p->entry.stage!=3||p->entry.inputs>=2||p->command.id!=p->entry.issued
            ||p->command.direction!=NG2_UP||now>p->entry.parent||entry_static(p,&p->scene,&still))reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->lower.active){
        NG2Motion still={0};
        if(p->lower.stage!=3||p->lower.inputs>=p->lower.steps||p->command.id!=p->lower.issued
            ||p->command.direction!=NG2_DOWN||now>p->lower.parent||lower_static(p,&p->scene,&still))reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->command.kind==NG2_ACTION_PAUSE&&!pause_ui_ready(p,now))reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->passage_release_proof_id
        &&p->model_capture_id<p->passage_release_proof_id)reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->passage_active&&!p->cycle_full_framing&&!p->entry.active&&!p->lower.active&&!p->upper.active){
        NG2Decision latest;
        if(p->initial_view_pending||p->initial_candidate_waiting
            ||p->passage_wait_kind||!choose_step(p,&p->scene,&latest)
            ||!same_choice(&latest,&p->command_choice)||!safe_step(p,&p->scene,p->command.direction))
            reason=NG2_REASON_SCREEN;
    }
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->passage_source.refreshed
        &&!passage_source_proof(p,&p->scene,now))reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->command_choice.reason==9
        &&(p->edge_sent||level_inputs(p)||level_moves(p)||p->s.lead_confirmed
           ||!p->edge_validated_capture_id||p->edge_validated_capture_id!=p->s.last_capture_id))
        reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->stationary_gate_retry_waiting==NG2_GATE_RETRY_ISSUED
        &&(!p->stationary_gate_retry_proof_id||p->stationary_gate_retry_proof_id!=p->s.last_capture_id))
        reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED
        &&(!p->gate_refresh_proof_id||p->gate_refresh_proof_id!=p->s.last_capture_id))reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->observation_refresh_active
        &&p->model_capture_id<p->gate_refresh_proof_id)reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->stationary_wait_active
        &&now>=stationary_wait_limit(p))reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->stationary_wait_active
        &&(!stationary_wait_proof(p,&p->scene,now)||p->model_capture_id<p->gate_refresh_proof_id))
        reason=NG2_REASON_SCREEN;
    if(!reason&&recover_unsent_continuous(p,now))return 0;
    if(!reason&&p->command_sync_deadline&&now>=p->command_sync_deadline){
        p->last_now=maximum(p->last_now,now);
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);return 0;
    }
    if(!reason&&initial_recoverable(p)&&now>=sync_deadline(p)){
        p->last_now=maximum(p->last_now,now);
        recovery_record(p,NG2_RECOVERY_SYNC_BUDGET,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);
        finish(p,now,NG2_REASON_BEAT);return 0;
    }
    if(!reason&&now>p->command.deadline_ns&&initial_recoverable(p)){
        p->last_now=maximum(p->last_now,now);
        initial_recover(p,NG2_RECOVERY_UNSENT_DEADLINE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);return 0;
    }
    tail=p->command.kind==NG2_ACTION_MOVE?p->s.lead_ns+50000000:50000000;
    horizon=minimum(p->command.source_start_ns+FRESH,session_bound(p));
    if(p->command.kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->command.phase_sample_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    if(p->command.kind==NG2_ACTION_MOVE&&p->opened_entry_parent)horizon=minimum(horizon,p->opened_entry_parent);
    if(p->command.kind==NG2_ACTION_MOVE&&p->cycle_full_framing)horizon=minimum(horizon,p->cycle.continuation_deadline_ns);
    if(p->command.kind==NG2_ACTION_MOVE&&p->entry.active)horizon=minimum(horizon,p->entry.parent);
    if(p->command.kind==NG2_ACTION_MOVE&&p->lower.active)horizon=minimum(horizon,p->lower.parent);
    if(p->command.kind==NG2_ACTION_MOVE&&p->upper.active)horizon=minimum(horizon,p->upper.parent);
    if(!reason&&(horizon<tail||now>horizon-tail||now>=NS_LIMIT-tail))reason=NG2_REASON_STALE;
    if(!reason&&(now<p->command.not_before_ns||now>p->command.deadline_ns))reason=NG2_REASON_LATE;
    if(!reason&&(now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH))reason=NG2_REASON_STALE;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&((p->s.goods&&p->cycle_full_framing!=3&&!(p->entry.active&&p->entry.stage==3)&&!(p->lower.active&&p->lower.stage==3)&&!(p->upper.active&&p->upper.stage==3))||p->finish_requested))reason=NG2_REASON_GOODS;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&(now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||!ng2_beat_model_valid(&p->model)||p->beat_failed))reason=NG2_REASON_BEAT;
    /* A later HUD-only observation can update the model after reissue. The
     * original target is immutable, and must still name the same live beat. */
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->replan_count>0&&level_inputs(p)==0
        &&!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned))reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&initial_slot_active(p)
        &&!corrected(p,p->initial_slot_target,p->initial_slot_period,&aligned))reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->continuous_chain_count>0
        &&!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->command_sync_deadline
        &&!corrected(p,p->command.target_ns,p->command_period,&aligned))reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->continuous_chain_count>0
        &&(continuous_horizon(p)<tail||now>continuous_horizon(p)-tail))reason=NG2_REASON_STALE;
    if(!reason&&now-p->s.started_ns>=180*SECOND)reason=NG2_REASON_SESSION;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&(p->s.inputs>=16||now-p->s.walk_started_ns>=45*SECOND))reason=NG2_REASON_LIMIT;
    if(reason){not_sent(p,now,reason);if(reason==NG2_REASON_FOREGROUND||reason==NG2_REASON_LOCKED||reason==NG2_REASON_OWNER_PAUSED)terminal(p,now,reason);
        else {finish(p,now,reason);}
        return 0;}
    if(p->command.kind==NG2_ACTION_MOVE&&p->motion_reference_valid&&!reference_time_valid(p,now,0))
        p->motion_reference_valid=0;
    if(p->command.kind==NG2_ACTION_MOVE&&p->cycle_partial_credit){
        p->cycle_partial_credit=p->cycle_framing_credit=0;p->cycle_consumed_prefix=p->s.last_completed_id;
    }
    if(p->command.kind==NG2_ACTION_MOVE&&p->cycle_full_framing==3){
        p->cycle_full_framing=4;p->cycle_current_active=0;
    }
    if(p->command.kind==NG2_ACTION_MOVE&&p->entry.active){++p->entry.inputs;p->entry.stage=4;}
    if(p->command.kind==NG2_ACTION_MOVE&&p->lower.active){++p->lower.inputs;p->lower.stage=4;}
    if(p->command.kind==NG2_ACTION_MOVE&&p->upper.active){
        p->upper.static_proof.valid=0;++p->upper.inputs;p->upper.stage=4;
    }
    p->preparation_epoch=0;
    if(p->command.kind==NG2_ACTION_MOVE){p->passage_release_proof_id=0;
        p->irregular_lead_before=p->s.lead_confirmed;irregular_clear_first(p);}
    if(p->command.kind==NG2_ACTION_MOVE&&p->command_choice.reason==9)p->edge_sent=1;
    p->edge_validated_capture_id=0;
    p->stationary_gate_retry_waiting=NG2_GATE_RETRY_NONE;p->stationary_gate_retry_proof_id=0;
    p->gate_refresh_state=NG2_GATE_REFRESH_NONE;p->gate_refresh_proof_id=0;
    clear_stationary_wait(p);
    p->terrain_refresh_active=0;
    p->observation_refresh_active=0;
    p->passage_source.active=p->passage_source.refreshed=0;
    p->last_now=maximum(p->last_now,now);p->s.input_state=2;e=event(p);e->begin_ns=now;e->outcome=1;
    return 1;
}
int ng2_controller_complete(NG2Controller *p,uint64_t id,uint64_t now,int32_t outcome){
    NG2ControllerEvent *e;
    if(!p||!valid_time(now)||id!=p->command.id||outcome < -1||outcome>1||p->s.terminal)return 0;
    /* Stale IDs AND already-completed states are inert, including clocks. */
    if(!((outcome==0&&(p->s.input_state==1||p->s.input_state==2))
        ||(outcome!=0&&p->s.input_state==2)))return 0;
    e=event(p);
    p->last_now=maximum(p->last_now,now);
    if(outcome==0&&(p->s.input_state==1||p->s.input_state==2)){
        if(p->irregular.enabled&&p->irregular_death_wait&&!irregular_active(p)){
            e->outcome=3;e->end_ns=now;e->reason=NG2_REASON_CAPTURE;
            p->s.input_state=0;p->s.current_command_id=0;clear_slots(p);clear_model(p);
            return 1;
        }
        if(irregular_active(p)){
            e->outcome=3;e->end_ns=now;e->reason=NG2_REASON_CAPTURE;
            p->s.input_state=0;p->s.current_command_id=0;
            irregular_hold(p,now,NG2_IRREGULAR_CONTROL_INVALID);return 1;
        }
        if(p->s.input_state==1&&recover_unsent_continuous(p,now))return 1;
        if(p->s.input_state==1&&initial_recoverable(p)&&now>p->command.deadline_ns){
            initial_recover(p,NG2_RECOVERY_UNSENT_DEADLINE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);return 1;
        }
        e->outcome=3;e->end_ns=now;e->reason=NG2_REASON_CAPTURE;
        p->s.input_state=0;p->s.current_command_id=0;finish(p,now,NG2_REASON_CAPTURE);return 1;}
    if(p->s.input_state!=2||now<e->begin_ns)return 0;
    e->end_ns=now;
    if(p->command.kind==NG2_ACTION_MOVE)++p->s.inputs;
    if(outcome==-1){e->outcome=4;e->reason=NG2_REASON_UNKNOWN_INPUT;p->s.input_state=4;
        if(irregular_active(p)){p->irregular.stage=NG2_IRREGULAR_HELD;p->irregular.held_reason=NG2_IRREGULAR_UNKNOWN_INPUT;}
        terminal(p,now,NG2_REASON_UNKNOWN_INPUT);return 1;}
    e->outcome=2;p->ack_ns=now;p->transition_ns=now;p->s.last_completed_id=id;p->s.input_state=3;
    if(p->initial_restart.stage==NG2_INITIAL_FLOOR&&p->initial_restart.restart==id
        &&p->command.kind==NG2_ACTION_RESTART)p->initial_restart.ack=now;
    if(p->command.kind==NG2_ACTION_MOVE){p->motion_wait.active=1;p->recovery.ack_ns=now;}
    if(p->command.kind==NG2_ACTION_MOVE&&p->motion_reference_count<MOTION_REFERENCE_CAP){
        NG2ControllerMotionReference *row=&p->motion_references[p->motion_reference_count++];
        memset(row,0,sizeof(*row));row->command_id=id;
        row->authority_capture_id=row->selected_capture_id=p->command.source_capture_id;
        if(p->motion_reference_present){
            row->reference_capture_id=p->motion_reference_ticket.source_capture_id;
            row->reference_start_ns=p->motion_reference_ticket.source_start_ns;
            row->reference_prefix=p->motion_reference_prefix;
        }
        row->reference_eligible=motion_reference_eligible(p,now);
    }
    p->s.paused=0;
    if(irregular_active(p)){
        p->irregular.prefix=id;p->s.phase=NG2_PHASE_FINISH;
        if(p->irregular.stage==NG2_IRREGULAR_HELD){
            irregular_hold(p,now,p->irregular.held_reason);return 1;
        }
        if(p->command.kind==NG2_ACTION_DEATH_CONTINUE)p->irregular.stage=NG2_IRREGULAR_WAIT_MENU;
        else if(p->command.kind==NG2_ACTION_RESTART)p->irregular.stage=NG2_IRREGULAR_WAIT_RESTART;
        return 1;
    }
    if(p->command.kind==NG2_ACTION_RESUME)p->s.phase=NG2_PHASE_FLOOR;
    else if(p->command.kind==NG2_ACTION_PAUSE)p->s.phase=p->finish_requested?NG2_PHASE_FINISH:NG2_PHASE_PAUSE;
    else if(p->command.kind==NG2_ACTION_RESTART)p->s.phase=NG2_PHASE_RESTART;
    return 1;
}
void ng2_controller_cancel(NG2Controller *p,uint64_t now,int32_t reason){
    NG2ControllerEvent *e;
    if(!p||p->s.terminal||!valid_time(now))return;
    p->last_now=maximum(p->last_now,now);
    if(reason<1||reason>NG2_REASON_GEOMETRY)reason=NG2_REASON_CANCELLED;
    if(irregular_active(p)){
        p->irregular.stage=NG2_IRREGULAR_HELD;
        p->irregular.held_reason=p->s.input_state==2?NG2_IRREGULAR_UNKNOWN_INPUT:NG2_IRREGULAR_CONTROL_INVALID;
    }
    irregular_clear_first(p);
    if(p->s.input_state==2){e=event(p);e->outcome=4;e->reason=NG2_REASON_UNKNOWN_INPUT;e->end_ns=now;
        if(p->command.kind==NG2_ACTION_MOVE)++p->s.inputs;
        p->s.input_state=4;terminal(p,now,NG2_REASON_UNKNOWN_INPUT);return;}
    not_sent(p,now,reason);terminal(p,now,reason);
}
void ng2_controller_status(const NG2Controller *p,NG2ControllerStatus *out){if(out){if(p)*out=p->s;else memset(out,0,sizeof(*out));}}
uint64_t ng2_controller_preparation_epoch(const NG2Controller *p,uint64_t id,uint64_t now){
    uint64_t horizon,tail,aligned;
    if(!p||!id||!valid_time(now)||!p->preparation_epoch||p->s.terminal||p->finish_requested
        ||p->s.input_state!=1||p->s.current_command_id!=id||p->command.id!=id
        ||p->command.kind!=NG2_ACTION_MOVE||p->s.phase!=NG2_PHASE_WALK
        ||!p->s.lead_confirmed||p->s.moves<=0||p->s.goods||!p->have_scene
        ||p->scene.state!=NG2_FLOOR||p->replan_pending||p->continuous_pending
        ||!p->continuous_ticket_valid||p->s.inputs>=16
        ||p->last_observed_prefix!=p->s.last_completed_id)return 0;
    /* Direction/coordinates may change under FRESH. These frozen fields
     * identify the logical beat; optional motion-reference eligibility does
     * not supply or revoke preparation ownership. */
    if(p->command.ordinal!=p->continuous_ticket.ordinal
        ||p->command.target_ns!=p->continuous_ticket.target_ns
        ||p->command.not_before_ns!=p->continuous_ticket.not_before_ns
        ||p->command.deadline_ns!=p->continuous_ticket.deadline_ns
        ||p->command_period!=p->continuous_period)return 0;
    if(now<p->last_now||now<p->s.started_ns||now<p->s.walk_started_ns
        ||now<p->s.last_capture_end_ns||now<p->command.source_start_ns||now<p->command.phase_sample_ns
        ||now<p->continuous_ticket.source_start_ns||now<p->continuous_ticket.phase_sample_ns
        ||now<p->model.last_ns||now>p->command.deadline_ns||now>p->continuous_motion_deadline
        ||(p->command_sync_deadline&&now>=p->command_sync_deadline)
        ||p->command.not_before_ns>p->command.deadline_ns
        ||!ng2_beat_model_valid(&p->model)||p->beat_failed
        ||now-p->model.last_ns>FRESH
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    horizon=minimum(p->command.source_start_ns+FRESH,p->command.phase_sample_ns+FRESH);
    horizon=minimum(horizon,continuous_horizon(p));tail=p->s.lead_ns+50000000;
    if(horizon<tail||now>horizon-tail)return 0;
    return p->preparation_epoch;
}
size_t ng2_controller_events(const NG2Controller *p,NG2ControllerEvent *out,size_t capacity){
    size_t n;if(!p||!out)return 0;n=p->event_count<capacity?p->event_count:capacity;memcpy(out,p->events,n*sizeof(*out));return n;
}
size_t ng2_controller_scene_changes(const NG2Controller *p,NG2ControllerSceneChange *out,size_t capacity){
    size_t n;if(!p||!out)return 0;n=p->scene_change_count<capacity?p->scene_change_count:capacity;
    memcpy(out,p->scene_changes,n*sizeof(*out));return n;
}
size_t ng2_controller_scene_details(const NG2Controller *p,NG2ControllerSceneDetail *out,size_t capacity){
    size_t n;if(!p||!out)return 0;n=p->scene_change_count<capacity?p->scene_change_count:capacity;
    memcpy(out,p->scene_details,n*sizeof(*out));return n;
}
void ng2_controller_motion_wait(const NG2Controller *p,NG2ControllerMotionWait *out){
    if(out){if(p)*out=p->motion_wait;else memset(out,0,sizeof(*out));}
}
void ng2_controller_recovery_status(const NG2Controller *p,NG2ControllerRecoveryStatus *out){
    if(out){if(p)*out=p->recovery;else memset(out,0,sizeof(*out));}
}
size_t ng2_controller_recovery_samples(const NG2Controller *p,size_t index,NG2BeatSample *out,size_t capacity){
    size_t n;
    if(!p||!out||index>=2||index>=p->recovery.record_count)return 0;
    n=(size_t)p->recovery.records[index].sample_count;if(n>capacity)n=capacity;
    memcpy(out,p->recovery_samples[index],n*sizeof(*out));return n;
}
size_t ng2_controller_motion_references(const NG2Controller *p,NG2ControllerMotionReference *out,size_t capacity){
    size_t n;if(!p||!out)return 0;n=p->motion_reference_count<capacity?p->motion_reference_count:capacity;
    memcpy(out,p->motion_references,n*sizeof(*out));return n;
}
const char *ng2_reason_name(int32_t reason){
    static const char *const names[]={"none","goods","cancelled","foreground","locked","owner_paused","capture",
        "stale","beat","late","movement","unknown_input","no_path","partial_goods",
        "limit","session","restart","screen","generation","heartbeat","geometry"};
    return reason>=0&&reason<=NG2_REASON_GEOMETRY?names[reason]:"unknown";
}
