/* TEST043 device-clock controller. Synth ACK is never movement evidence.
 * Calls are serialized by the adapter; begin runs on main while that caller
 * is blocked. No callback, shared global state, HTTP model or clock is used. */
#include "NG2Controller.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
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
static const uint64_t leads[7]={150000000,75000000,225000000,300000000,375000000,450000000,25000000};
static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
enum { NG2_CONTINUOUS_NONE=0, NG2_CONTINUOUS_SAME=1, NG2_CONTINUOUS_FRESH=2 };
enum { NG2_GATE_RETRY_NONE=0, NG2_GATE_RETRY_REFIT=1, NG2_GATE_RETRY_ISSUED=2 };
enum { NG2_GATE_REFRESH_NONE=0, NG2_GATE_REFRESH_OBSERVE=1,
       NG2_GATE_REFRESH_READY=2, NG2_GATE_REFRESH_ISSUED=3 };
struct NG2Controller {
    NG2ControllerStatus s;
    NG2Scene scene,before,retune_anchor;
    NG2Scene motion_reference_scene;
    NG2Scene gate_refresh_anchor,gate_refresh_previous;
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
    uint64_t finish_ns,preparation_epoch;
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
    int initial_view_pending,initial_candidate_waiting;
    int observation_refresh_active,observation_refresh_count;
    int stationary_wait_active,stationary_wait_x,stationary_wait_y;
    int stationary_wait_inputs,stationary_wait_moves,stationary_wait_passage,stationary_wait_bit;
    uint32_t stationary_wait_pending,stationary_wait_inspected,stationary_wait_unresolved,stationary_wait_closed;
};
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
static uint64_t maximum(uint64_t a,uint64_t b){return a>b?a:b;}
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
    p->stationary_wait_active=0;p->stationary_wait_parent=0;p->stationary_wait_trigger_id=0;
}
static void terminal(NG2Controller *p,uint64_t now,int reason){
    p->preparation_epoch=0;
    clear_stationary_wait(p);
    if(!p->s.terminal){p->motion_wait.active=0;p->s.reason=reason;p->s.terminal=1;p->s.phase=NG2_PHASE_DONE;p->s.ended_ns=now;}
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
    p->preparation_epoch=0;
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
static int fresh(NG2Controller *p,uint64_t now){
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
    if(!p->finish_requested&&(p->initial_view_pending||p->initial_candidate_waiting))return 0;
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
    uint64_t deadline=minimum(p->sync_ns+12*SECOND,p->s.started_ns+180*SECOND);
    if(p->s.walk_started_ns)deadline=minimum(deadline,p->s.walk_started_ns+45*SECOND);
    if(p->stationary_wait_parent)deadline=minimum(deadline,p->stationary_wait_parent);
    else if(p->gate_refresh_state)deadline=minimum(deadline,p->gate_refresh_deadline);
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
static int passage_goods_protected(const NG2Scene *s){
    int i;
    for(i=0;i<NG2_TILE_COUNT;++i)
        if(s->tiles[i]==NG2_TILE_ITEM||(s->protected_cells[i]&&s->tiles[i]!=NG2_TILE_GOLD))return 1;
    return 0;
}
static int initial_uncertain_floor(const NG2Controller *p,const NG2Scene *scene){
    return (p->initial_view_pending||p->initial_candidate_waiting)
        &&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_UNKNOWN
        &&!passage_goods_protected(scene)&&!actual_gold(scene)&&!clear_gold_floor(scene);
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
    if(d<1||d>4||s->state!=NG2_FLOOR||s->gold_state!=NG2_GOLD_CLEAR
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
    initial_candidate_support(scene,p->initial_candidate_tiles);
}
/* A changed fingerprint proves a restart, not completion of its drawing.
 * This fixed first-floor epoch belongs to the level and is never refreshed. */
static void begin_initial_view(NG2Controller *p,const NG2Scene *scene,
    uint64_t id,uint64_t start,uint64_t end){
    p->initial_view_id=id;p->initial_view_start=start;p->initial_view_end=end;
    p->initial_view_pending=!actual_gold(scene);p->initial_candidate_waiting=0;
    p->initial_candidate_id=0;
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
    /* Session counters, all used allowances, trace history, IDs, ordinal and
     * the first walk horizon survive a proven new game level. */
    p->level_input_base=p->s.inputs;p->level_move_base=p->s.moves;
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
    p->passage_active=0;p->passage_bit=-1;p->passage_wait_kind=0;
    p->passage_pending=p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
    p->passage_wait_deadline=p->passage_wait_horizon=p->passage_release_proof_id=p->passage_anchor_id=p->passage_anchor_start=p->passage_anchor_end=0;
    p->initial_view_id=p->initial_view_start=p->initial_view_end=0;
    p->initial_candidate_id=p->initial_candidate_end=p->initial_candidate_prefix=0;
    p->initial_candidate_mask=0;p->initial_view_pending=p->initial_candidate_waiting=0;
    memset(p->initial_candidate_tiles,0,sizeof(p->initial_candidate_tiles));
    p->restart_baseline_valid=p->restart_intent=0;p->sync_ns=end;p->transition_ns=end;p->s.phase=NG2_PHASE_SEARCH;
}
static void start_floor(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t end){
    uint64_t epoch=p->initial_view_end?p->initial_view_end:end;
    if(scene->state!=NG2_FLOOR)return;
    if((scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))&&!actual_gold(scene)){
        finish(p,end,NG2_REASON_PARTIAL_GOODS);return;
    }
    if(initial_uncertain_floor(p,scene))return;
    if(actual_gold(scene)){
        p->passage_active=0;p->passage_wait_kind=0;p->restart_intent=0;
        if(!p->s.walk_started_ns)p->s.walk_started_ns=epoch;
        p->sync_ns=epoch;clear_model(p);p->s.phase=NG2_PHASE_SYNC;
    }else if(scene->gold_state==NG2_GOLD_CLEAR){
        if(!clear_gold_floor(scene)){finish(p,end,NG2_REASON_SCREEN);return;}
        if(!p->initial_candidate_id)remember_initial_candidate(p,scene,id,end,p->s.last_completed_id);
        p->passage_pending=ng2_passage_candidates(scene);
        if(p->passage_pending){
            p->passage_active=1;p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
            select_passage(p,scene);
            if(!p->s.walk_started_ns)p->s.walk_started_ns=epoch;
            p->sync_ns=epoch;clear_model(p);p->s.phase=NG2_PHASE_SYNC;
        }else {p->restart_intent=1;p->s.phase=NG2_PHASE_FLOOR;}
    }else if(scene->gold_state==NG2_GOLD_CANDIDATE)finish(p,end,NG2_REASON_SCREEN);
}
/* Initial-room evidence may be reclassified only before a physical input.
 * After movement the original world mouth must survive camera translation.
 * Unknown/disappearing support retires an unsent ticket but is not a wall. */
static int recheck_initial_view(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix){
    unsigned char support[30];uint32_t mask,missing;int bit,x,y,closed=1,independent,same;
    if(p->finish_requested||p->s.goods||level_inputs(p)||level_moves(p)||p->s.lead_confirmed
        ||p->s.x||p->s.y||p->s.input_state>1
        ||p->observe_now<start||p->observe_now-start>FRESH
        ||(!p->initial_view_pending&&!p->initial_candidate_waiting&&!p->passage_active&&!p->restart_intent))return 0;
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
    if(!clear_gold_floor(scene))return 0;
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
    same=mask==p->initial_candidate_mask;
    for(bit=0;bit<10;++bit)if((p->passage_pending|mask)&(UINT32_C(1)<<bit))
        if(memcmp(support+3*bit,p->initial_candidate_tiles+3*bit,3))same=0;
    if(!independent||!same||!closed){
        remember_initial_candidate(p,scene,id,end,prefix);return 1;
    }
    p->initial_view_pending=0;
    if(p->initial_candidate_waiting){
        p->initial_candidate_waiting=0;p->restart_baseline_valid=p->restart_pending=0;
        p->passage_pending=mask;p->passage_inspected=p->passage_unresolved=p->passage_closed=0;
        p->passage_wait_kind=0;p->passage_wait_deadline=p->passage_release_proof_id=0;
        p->restart_intent=!mask;p->passage_active=mask!=0;
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
    horizon=minimum(horizon,p->s.started_ns+180*SECOND);
    p->passage_wait_kind=kind;p->passage_wait_horizon=horizon;
    p->passage_wait_deadline=ng2_beat_model_valid(&p->model)?minimum(now+2*p->model.period_ns,horizon):0;
    p->passage_anchor=*scene;p->passage_anchor_id=id;
    p->passage_anchor_start=start;p->passage_anchor_end=end;
    p->proof_deadline=0;p->proof_reacquire=0;p->proof_capture_id=id;p->motion_wait.active=0;
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
    p->passage_pending&=~bit;
    if(inspection==1)p->passage_inspected|=bit;
    else if(inspection==2)p->passage_closed|=bit;
    else p->passage_unresolved|=bit;
    p->passage_wait_kind=0;p->passage_wait_deadline=0;
    if(select_passage(p,scene))return;
    p->passage_active=0;
    if(p->passage_unresolved){finish(p,now,NG2_REASON_NO_PATH);return;}
    /* Every fixed candidate was independently inspected or locally closed. */
    clear_slots(p);p->proof_deadline=0;p->recovery.mode=NG2_RECOVERY_NORMAL;
    p->restart_intent=1;p->s.phase=NG2_PHASE_FLOOR;
}
static void update_passage_wait(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Motion still;NG2Decision a,b;int kind=p->passage_wait_kind,x,y,d=p->command.direction;
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
    if(actual_gold(scene)&&kind!=PASSAGE_WAIT_GOLD){
        p->passage_wait_kind=PASSAGE_WAIT_GOLD;p->passage_anchor=*scene;
        p->passage_anchor_id=id;p->passage_anchor_start=start;p->passage_anchor_end=end;return;
    }
    if(start<p->passage_anchor_end||id<=p->passage_anchor_id
        ||!ng2_motion(&p->passage_anchor,scene,d,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)return;
    if(kind==PASSAGE_WAIT_GOLD){
        if(!actual_gold(scene)||!same_gold(&p->passage_anchor,scene)
            ||tile(scene,0,0)!=NG2_TILE_FLOOR)return;
        p->passage_active=0;p->passage_wait_kind=0;p->proof_capture_id=id;p->passage_release_proof_id=id;
        clear_recovery_slot(p);p->s.phase=NG2_PHASE_SYNC;return;
    }
    if(!clear_gold_floor(scene))return;
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
        p->passage_wait_kind=PASSAGE_WAIT_ROUTE;p->passage_anchor=*scene;
        p->passage_anchor_id=id;p->passage_anchor_start=start;p->passage_anchor_end=end;
    }
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
            p->passage_active=0;p->motion_reference_present=p->motion_reference_valid=0;return;
        }
        begin_passage_wait(p,scene,id,start,end,now,PASSAGE_WAIT_GOLD);return;
    }
    if(scene->goods!=NG2_GOODS_UNKNOWN){finish(p,now,NG2_REASON_PARTIAL_GOODS);return;}
    if(!clear_gold_floor(scene)){finish(p,now,NG2_REASON_SCREEN);return;}
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
static uint64_t continuous_horizon(const NG2Controller *p){
    uint64_t horizon=minimum(p->continuous_ticket.source_start_ns+FRESH,p->continuous_ticket.phase_sample_ns+FRESH);
    horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);
    return minimum(horizon,p->s.started_ns+180*SECOND);
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
/* The closed door is beyond the unchanged dig cell. Its observed GOLD pair
 * must be perpendicular to the input axis, in both source and latest frame. */
static int closed_door_two_ahead(const NG2Scene *s,int d){
    int x=2*dx[d],y=2*dy[d];
    return tile(s,x,y)==NG2_TILE_DOOR
        &&tile(s,x+dy[d],y-dx[d])==NG2_TILE_GOLD
        &&tile(s,x-dy[d],y+dx[d])==NG2_TILE_GOLD;
}
/* Keep an entrance or the same observed-floor vantage through irrelevant
 * remote flicker. Ticket/before and all bounds stay fixed;
 * do not grant safe-floor calibration, reissue or reference eligibility. */
static int quiet_gate_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision before,latest;NG2Motion motion;uint64_t aligned;int i,d=p->command.direction;
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
        ||(!entrance_step&&!interior_step&&!approach_step&&!dirt_step)
        ||(entrance_step&&(p->command_choice.target_x!=dx[d]||p->command_choice.target_y!=dy[d]))
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=scene->goods||scene->goods<NG2_GOODS_UNKNOWN||scene->goods>NG2_GOODS_PARTIAL
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||(gold_changed&&!growth&&!clipped_entry)
        ||(!clipped_entry&&memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT))
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=obstacle||tile(scene,dx[d],dy[d])!=obstacle
        ||(entrance_step&&(!gate_at(&p->before,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d])))
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH||now>continuous_horizon(p)
        ||(p->command_sync_deadline&&now>=p->command_sync_deadline)
        ||now-p->s.walk_started_ns>=45*SECOND||now-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
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
        if(clipped_entry&&i/23==0&&p->before.protected_cells[i])continue;
        if(dirt_step&&(p->before.protected_cells[i]||scene->protected_cells[i]))return 0;
        if(growth&&b==NG2_TILE_GOLD)continue;
        if((!shielded&&((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)))
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT&&a!=NG2_TILE_STONE)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE))return 0;
    }
    return choose_step(p,&p->before,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,&p->command_choice)&&same_choice(&before,&latest)
        &&ng2_motion(&p->before,scene,d,&motion)&&motion.kind==NG2_BLOCKED&&!motion.dx&&!motion.dy;
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
    budget=minimum(budget,p->s.started_ns+180*SECOND);
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
    budget=minimum(budget,p->s.started_ns+180*SECOND);
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
static int observation_refresh_scene(const NG2Controller *p,const NG2Scene *scene){
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
    return choose_step(p,a,&before)
        &&choose_step(p,scene,&latest)
        &&same_choice(&before,choice)&&same_choice(&before,&latest)
        &&(!stone_change||(closed_approach_refresh(p,scene)
            &&ng2_motion(a,scene,d,&still)&&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy));
}
/* An exhausted logical ticket need not end a stationary, known-floor walk.
 * Withdraw it first. A later independent pair and future preparation window
 * authorize a different ID; no old timing, epoch or input credit survives. */
static int start_observation_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Motion still,texture;uint64_t budget,aligned;
    int d=p->command.direction;
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
    budget=minimum(budget,p->s.started_ns+180*SECOND);
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    if(now>=budget)return 0;
    p->gate_refresh_anchor=p->before;p->gate_refresh_choice=p->command_choice;
    if(!observation_refresh_scene(p,scene)
        ||!ng2_motion(&p->before,scene,d,&still)||still.kind!=NG2_BLOCKED||still.dx||still.dy
        ||!ng2_motion(scene,scene,d,&texture)||texture.kind!=NG2_BLOCKED||texture.dx||texture.dy)return 0;
    ++p->observation_refresh_count;p->observation_refresh_verified=p->latest_verified_ns;
    p->observation_refresh_active=1;p->gate_refresh_anchor=*scene;
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
    if(p->stationary_wait_passage){if(!clear_gold_floor(a)||!clear_gold_floor(scene))return 0;}
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
static int stationary_wait_proof(const NG2Controller *p,const NG2Scene *scene){
    NG2Motion still;
    return stationary_wait_scene(p,scene)
        &&ng2_motion(&p->gate_refresh_anchor,scene,p->gate_refresh_choice.direction,&still)
        &&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy;
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
    budget=minimum(budget,p->s.started_ns+180*SECOND);
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
    NG2Motion still;int d=p->gate_refresh_choice.direction;
    uint64_t deadline=p->gate_refresh_state==NG2_GATE_REFRESH_OBSERVE?
        p->gate_refresh_deadline:p->stationary_wait_parent;
    if(now>=deadline){finish(p,now,NG2_REASON_BEAT);return 0;}
    if(id==p->stationary_wait_trigger_id)return 1; /* Trigger is not independent proof. */
    p->gate_refresh_proof_id=0;
    if(id<p->stationary_wait_trigger_id||start<p->gate_refresh_previous_end
        ||p->s.last_completed_id!=p->gate_refresh_prefix||!stationary_wait_world(p)){
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    if(!ng2_motion(&p->gate_refresh_anchor,scene,d,&still)){
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
    if(still.kind==NG2_BLOCKED&&!still.dx&&!still.dy){
        p->gate_refresh_proof_id=id;p->proof_capture_id=id;
        if(p->gate_refresh_state!=NG2_GATE_REFRESH_ISSUED)p->gate_refresh_state=NG2_GATE_REFRESH_READY;
    }else if(p->gate_refresh_state!=NG2_GATE_REFRESH_OBSERVE||still.kind!=NG2_MOTION_UNKNOWN){
        record_stationary_failure(p,scene,id,start,NG2_REVALIDATE_MOTION);
        finish(p,now,NG2_REASON_SCREEN);return 0;
    }
    return 1;
}
static int update_gate_refresh(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t now){
    NG2Motion still,texture;int d=p->gate_refresh_choice.direction;
    if(p->stationary_wait_active)return update_stationary_wait(p,scene,id,start,end,now);
    if(now>=p->gate_refresh_deadline){finish(p,now,NG2_REASON_BEAT);return 0;}
    p->gate_refresh_proof_id=0;
    if(p->s.last_completed_id!=p->gate_refresh_prefix
        ||!(p->observation_refresh_active?observation_refresh_scene(p,scene):
            p->terrain_refresh_active?terrain_refresh_scene(p,scene):gate_refresh_scene(p,scene))
        ||start<p->gate_refresh_previous_end||now<p->gate_refresh_previous_start
        ||now-p->gate_refresh_previous_start>FRESH
        ||!ng2_motion(p->gate_refresh_state==NG2_GATE_REFRESH_ISSUED?&p->before:
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
    int direction=p->command.direction,strict=0,fresh_allowed;
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
        &&monotone_terrain(&p->before,scene);
    if(strict&&!fresh_allowed)return strict;
    /* One cached-source proof serves both policies. A second planner call
     * must never rescue a failed full Decision from the first call. */
    if(!choose_step(p,&p->before,&before)
        ||before.direction!=direction||!same_choice(&before,&p->command_choice))return NG2_REVALIDATE_ROUTE;
    if(!choose_step(p,scene,&after)
        ||after.direction<1||after.direction>4)return NG2_REVALIDATE_ROUTE;
    if(!same_continuous_action(&before,&after)&&!strict)strict=NG2_REVALIDATE_ROUTE;
    if(strict&&!fresh_allowed)return strict;
    if(!ng2_motion(&p->before,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)return NG2_REVALIDATE_MOTION;
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
        &&now<=p->s.started_ns+180*SECOND
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
static void record_change(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    int mask,int changed_tiles,int changed_protected,int allowed,int validation){
    NG2ControllerSceneChange *change;NG2ControllerSceneDetail *detail;size_t at;int k,total=0;
    if(p->scene_change_count<3)at=p->scene_change_count++;
    else {p->scene_changes[1]=p->scene_changes[2];p->scene_details[1]=p->scene_details[2];at=2;}
    change=&p->scene_changes[at];detail=&p->scene_details[at];
    memset(change,0,sizeof(*change));memset(detail,0,sizeof(*detail));
    change->command_id=p->command.id;
    change->source_capture_id=(p->replan_pending||p->continuous_pending)?p->s.last_capture_id:p->command.source_capture_id;
    change->observed_capture_id=id;change->target_ns=p->command.target_ns;
    change->deadline_ns=p->command.deadline_ns;
    change->change_mask=mask;change->changed_tiles=changed_tiles;change->changed_protected=changed_protected;
    change->state_before=p->before.state;change->state_after=scene->state;
    change->goods_before=p->before.goods;change->goods_after=scene->goods;
    change->replan_count=p->replan_count+(validation==NG2_REVALIDATE_INITIAL_ALLOWED);
    change->replan_allowed=allowed;
    detail->command_id=change->command_id;detail->source_capture_id=change->source_capture_id;
    detail->observed_capture_id=id;detail->validation=validation;
    detail->continuous_count=p->continuous_count+continuous_allowed(validation);
    detail->chain_count=p->continuous_chain_count+continuous_allowed(validation);
    for(k=0;k<NG2_TILE_COUNT;++k)if(p->before.tiles[k]!=scene->tiles[k]
        ||p->before.protected_cells[k]!=scene->protected_cells[k]){
        if(total<4){NG2ControllerCellChange *cell=&detail->cells[total];
            cell->x=k%23-11;cell->y=k/23-5;cell->tile_before=p->before.tiles[k];cell->tile_after=scene->tiles[k];
            cell->protected_before=p->before.protected_cells[k];cell->protected_after=scene->protected_cells[k];}
        ++total;
    }
    detail->cell_count=total<4?total:4;detail->omitted_cells=total-detail->cell_count;
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
    budget=minimum(budget,p->s.started_ns+180*SECOND);
    if(p->command_sync_deadline)budget=minimum(budget,p->command_sync_deadline);
    return now<budget;
}
static void resolve_move(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,uint64_t end){
    NG2Motion motion;NG2Decision decision;NG2ControllerEvent *e=event(p);NG2Entrance entered;
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
    if((motion.kind==NG2_TWEEN||motion.kind==NG2_MOTION_UNKNOWN)&&p->motion_wait.attempts<MOTION_ASSESSMENTS)return;
    end_visual_wait(p);
    if(motion.kind==NG2_MOVED){
        if(motion.dx!=dx[direction]||motion.dy!=dy[direction]){finish(p,end,NG2_REASON_MOVEMENT);return;}
        if(ng2_entered_gate(&p->before,scene,direction,p->s.x,p->s.y,motion.kind,&entered))p->entrance=entered;
        p->s.x+=motion.dx;p->s.y+=motion.dy;++p->s.moves;
        if(p->s.x < -16||p->s.x>16||p->s.y < -16||p->s.y>16){finish(p,end,NG2_REASON_LIMIT);return;}
        if(p->visits[(p->s.y+16)*33+p->s.x+16]<UINT16_MAX)++p->visits[(p->s.y+16)*33+p->s.x+16];
        p->s.lead_confirmed=1;
        p->latest_verified_ns=p->observe_now;
        if(!p->s.first_move_ns&&e)p->s.first_move_ns=e->begin_ns;
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
int ng2_controller_observe_at(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,int32_t stable,uint64_t commit){
    int pending_kind,initial_wait=0,mask=0,changed_tiles=0,changed_protected=0;
    int clipped_entry=0,quiet_gate=0;
    if(!p)return -1;
    if(p->s.terminal)return 0;
    if(!valid_time(commit)||commit<end||commit<p->last_now)return -1;
    p->observe_now=commit;
    ++p->s.capture_count;
    if(!id||!valid_time(start)||!valid_time(end)||end<=start||start<p->s.started_ns||(start<p->last_now&&p->last_now-start>FRESH)||id<=p->seen_id
        ||(p->seen_id&&(start<=p->seen_start||end<=p->seen_end))){++p->s.discarded_frames;return 0;}
    p->seen_id=id;p->seen_start=start;p->seen_end=end;
    if(!valid_scene(scene)||stable<0||stable>1){++p->s.discarded_frames;terminal(p,end,NG2_REASON_GEOMETRY);return 0;}
    p->last_now=commit;
    if((p->s.input_state==1||p->replan_pending||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE)
        mask=scene_change(&p->before,scene,&changed_tiles,&changed_protected);
    /* A current goods observation latches before prefix/phase checks. Only a
     * subsequent stable matching prefix may authorize the holding pause. */
    if(scene->goods==NG2_GOODS_VISIBLE){finish(p,end,NG2_REASON_GOODS);p->need_fresh_cleanup=1;}
    if((p->restart_intent||(p->passage_active&&!actual_gold(scene)))
        &&(scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))){
        finish(p,end,NG2_REASON_PARTIAL_GOODS);p->need_fresh_cleanup=1;
    }
    if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
        ++p->s.discarded_frames;return 0;}
    initial_wait=recheck_initial_view(p,scene,id,start,end,prefix);
    if(initial_wait)mask=0;
    if((p->passage_active||p->restart_intent)&&!p->finish_requested&&scene->state==NG2_FLOOR
        &&!initial_wait&&!actual_gold(scene)&&!clear_gold_floor(scene)
        &&!(p->s.input_state==3&&p->command.kind==NG2_ACTION_RESTART)){
        /* An uncertain floor cannot keep old skip authority. A PAUSE UI's
         * UNKNOWN gold is normal; an ACK-known RESTART keeps its own proof. */
        finish(p,end,NG2_REASON_SCREEN);mask=0;
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
    if(p->passage_active&&!p->finish_requested&&!p->stationary_wait_active){
        if((scene->goods==NG2_GOODS_PARTIAL||passage_goods_protected(scene))&&!actual_gold(scene))
            finish(p,end,NG2_REASON_PARTIAL_GOODS);
        else if(p->passage_wait_kind){update_passage_wait(p,scene,id,start,end,commit);mask=0;}
        else if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE){
            NG2Motion still;
            if(commit>p->command.deadline_ns
                &&recover_unsent_continuous_scene(p,commit,scene,start,end,prefix))mask=0;
            else if(quiet_passage_observation(p,scene,commit))mask=0;
            else if(start_stationary_wait(p,scene,id,start,end,commit))mask=0;
            else if(commit<=p->command.deadline_ns&&scene->state==NG2_FLOOR
                &&(actual_gold(scene)||(scene->gold_state==NG2_GOLD_CLEAR&&scene->goods==NG2_GOODS_UNKNOWN))
                &&ng2_motion(&p->before,scene,p->command.direction,&still)
                &&still.kind==NG2_BLOCKED&&!still.dx&&!still.dy){
                begin_passage_wait(p,scene,id,start,end,commit,
                    actual_gold(scene)?PASSAGE_WAIT_GOLD:PASSAGE_WAIT_ROUTE);mask=0;
            }else {not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);mask=0;}
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
    if((p->s.input_state==1||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE)
        validate_motion_reference(p,scene,start,end,prefix,end);
    clipped_entry=clipped_entry_top(p,scene);
    if(!p->finish_requested&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&(mask||clipped_entry))quiet_gate=quiet_gate_observation(p,scene,commit);
    /* A return to source tiles/protection still needs the cached clock and
     * direct strict-zero proof, even when no quarantined GOLD disappeared. */
    if(!p->finish_requested&&clipped_entry&&!mask&&!quiet_gate){
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);
    }
    /* Returning exactly to the source can have mask zero after an accepted
     * remote GOLD reveal. It still cannot erase that observed wall evidence. */
    if(!p->finish_requested&&p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&scene->goods==NG2_GOODS_PARTIAL&&partial_shop_floor_step(p)
        &&!gold_retained(&p->scene,scene)&&!(clipped_entry&&quiet_gate)){
        if(mask)record_change(p,scene,id,mask,changed_tiles,changed_protected,0,NG2_REVALIDATE_GOLD);
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);mask=0;
    }
    if(mask&&(quiet_initial_observation(p,scene,commit)||quiet_gate))mask=0;
    if(mask){
        NG2Decision latest;
        int validation=p->s.lead_confirmed?continuous_validation(p,scene,end,&latest):
            (can_replan(p,scene)?NG2_REVALIDATE_INITIAL_ALLOWED:NG2_REVALIDATE_INITIAL_REJECTED);
        int allowed=validation==NG2_REVALIDATE_INITIAL_ALLOWED||continuous_allowed(validation);
        record_change(p,scene,id,mask,changed_tiles,changed_protected,allowed,validation);
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
                reset_level(p,end);begin_initial_view(p,scene,id,start,end);start_floor(p,scene,id,end);
            }
        }
    }else if(!p->finish_requested){
        if(!initial_wait&&p->s.phase==NG2_PHASE_SEARCH&&scene->state==NG2_FLOOR)start_floor(p,scene,id,end);
    }
    if(!p->stationary_wait_active)update_passage_progress(p,scene,id,start,end,commit);
    if(!p->finish_requested&&p->s.walk_started_ns&&scene->state==NG2_FLOOR
        &&p->s.input_state!=3)add_sample(p,scene,id,start,end);
    if(p->beat_failed&&!p->finish_requested
        &&!(p->s.input_state==3&&p->command.kind==NG2_ACTION_MOVE)&&!p->proof_deadline)
        finish(p,commit,NG2_REASON_BEAT);
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
    horizon=minimum(p->s.last_capture_start_ns+FRESH,p->s.started_ns+180*SECOND);
    if(kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->model.last_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    if(kind==NG2_ACTION_MOVE&&p->stationary_wait_parent)horizon=minimum(horizon,p->stationary_wait_parent);
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
    deadline=minimum(deadline,p->s.started_ns+180*SECOND);
    if(kind==NG2_ACTION_MOVE){deadline=minimum(deadline,p->model.last_ns+FRESH);
        deadline=minimum(deadline,p->s.walk_started_ns+45*SECOND);}
    p->command.deadline_ns=deadline;
    if(p->command.not_before_ns>deadline||now>deadline){finish(p,now,NG2_REASON_LATE);return 0;}
    p->command.ordinal=kind==NG2_ACTION_MOVE?p->s.last_ordinal+1:0;
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
        wait_horizon=minimum(wait_horizon,p->s.started_ns+180*SECOND);
        if(p->stationary_wait_parent)wait_horizon=minimum(wait_horizon,p->stationary_wait_parent);
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
    *out=p->command;return 1;
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
    int i,passage=0;
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
            ||!clear_gold_floor(&p->before)||!clear_gold_floor(scene)
            ||!safe_step(p,&p->before,p->command.direction)||!safe_step(p,scene,p->command.direction))return 0;
        for(i=0;i<NG2_TILE_COUNT;++i)
            if(p->before.protected_cells[i]||scene->protected_cells[i]
                ||p->before.tiles[i]==NG2_TILE_ITEM||scene->tiles[i]==NG2_TILE_ITEM)return 0;
        passage=1;
    }
    if(!p->have_scene||start>now||end>now||now-start>FRESH||prefix!=p->s.last_completed_id
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||(!passage&&(p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE))
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||memcmp(p->before.tiles,scene->tiles,NG2_TILE_COUNT)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!choose_step(p,&p->before,&before)
        ||!choose_step(p,scene,&latest)
        ||!same_choice(&before,expected)||!same_choice(&before,&latest)
        ||!ng2_motion(&p->before,scene,p->command.direction,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    if(!pending)not_sent(p,now,NG2_REASON_LATE);
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
        horizon=minimum(horizon,p->s.started_ns+180*SECOND);
        if(p->stationary_wait_parent)horizon=minimum(horizon,p->stationary_wait_parent);
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
int ng2_controller_tick(NG2Controller *p,uint64_t now,int32_t front,int32_t locked,int32_t owner,NG2Command *out){
    NG2Decision choice;int guard;
    if(out)memset(out,0,sizeof(*out));
    if(!p||!out||!valid_time(now)||now<p->last_now)return -1;
    p->last_now=now;
    if(p->s.terminal)return 0;
    guard=guards(front,locked,owner);
    if(guard){ng2_controller_cancel(p,now,guard);return 0;}
    if(now-p->s.started_ns>=180*SECOND){ng2_controller_cancel(p,now,NG2_REASON_SESSION);return 0;}
    if(p->have_scene&&p->s.last_capture_end_ns>now){ng2_controller_cancel(p,now,NG2_REASON_CAPTURE);return 0;}
    if(p->s.walk_started_ns&&now-p->s.walk_started_ns>=45*SECOND)finish(p,now,NG2_REASON_LIMIT);
    if(p->stationary_wait_active&&now>=(p->gate_refresh_state==NG2_GATE_REFRESH_OBSERVE?
        p->gate_refresh_deadline:p->stationary_wait_parent))finish(p,now,NG2_REASON_BEAT);
    if(p->s.input_state==2||p->s.input_state==4)return 0;
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
        if(p->scene.goods!=NG2_GOODS_UNKNOWN){finish(p,now,NG2_REASON_PARTIAL_GOODS);return 0;}
        if(!clear_gold_floor(&p->scene)){finish(p,now,NG2_REASON_SCREEN);return 0;}
        if(p->s.restarts>=12){finish(p,now,NG2_REASON_LIMIT);return 0;}
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
    if(p->stationary_wait_active&&!stationary_wait_proof(p,&p->scene)){
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
            horizon=minimum(horizon,p->s.started_ns+180*SECOND);
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
    reason=guards(front,locked,owner);
    if(!reason&&p->command.kind==NG2_ACTION_PAUSE&&!pause_ui_ready(p,now))reason=NG2_REASON_SCREEN;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->passage_release_proof_id
        &&p->model_capture_id<p->passage_release_proof_id)reason=NG2_REASON_BEAT;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->passage_active){
        NG2Decision latest;
        if(p->initial_view_pending||p->initial_candidate_waiting
            ||p->passage_wait_kind||!choose_step(p,&p->scene,&latest)
            ||!same_choice(&latest,&p->command_choice)||!safe_step(p,&p->scene,p->command.direction))
            reason=NG2_REASON_SCREEN;
    }
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
        &&(!stationary_wait_proof(p,&p->scene)||p->model_capture_id<p->gate_refresh_proof_id))
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
    horizon=minimum(p->command.source_start_ns+FRESH,p->s.started_ns+180*SECOND);
    if(p->command.kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->command.phase_sample_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    if(!reason&&(horizon<tail||now>horizon-tail||now>=NS_LIMIT-tail))reason=NG2_REASON_STALE;
    if(!reason&&(now<p->command.not_before_ns||now>p->command.deadline_ns))reason=NG2_REASON_LATE;
    if(!reason&&(now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH))reason=NG2_REASON_STALE;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&(p->s.goods||p->finish_requested))reason=NG2_REASON_GOODS;
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
    p->preparation_epoch=0;
    if(p->command.kind==NG2_ACTION_MOVE)p->passage_release_proof_id=0;
    if(p->command.kind==NG2_ACTION_MOVE&&p->command_choice.reason==9)p->edge_sent=1;
    p->edge_validated_capture_id=0;
    p->stationary_gate_retry_waiting=NG2_GATE_RETRY_NONE;p->stationary_gate_retry_proof_id=0;
    p->gate_refresh_state=NG2_GATE_REFRESH_NONE;p->gate_refresh_proof_id=0;
    clear_stationary_wait(p);
    p->terrain_refresh_active=0;
    p->observation_refresh_active=0;
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
        if(p->s.input_state==1&&recover_unsent_continuous(p,now))return 1;
        if(p->s.input_state==1&&initial_recoverable(p)&&now>p->command.deadline_ns){
            initial_recover(p,NG2_RECOVERY_UNSENT_DEADLINE,NG2_RECOVERY_ACTUAL_TICK,now,p->s.last_capture_id);return 1;
        }
        e->outcome=3;e->end_ns=now;e->reason=NG2_REASON_CAPTURE;
        p->s.input_state=0;p->s.current_command_id=0;finish(p,now,NG2_REASON_CAPTURE);return 1;}
    if(p->s.input_state!=2||now<e->begin_ns)return 0;
    e->end_ns=now;
    if(p->command.kind==NG2_ACTION_MOVE)++p->s.inputs;
    if(outcome==-1){e->outcome=4;e->reason=NG2_REASON_UNKNOWN_INPUT;p->s.input_state=4;terminal(p,now,NG2_REASON_UNKNOWN_INPUT);return 1;}
    e->outcome=2;p->ack_ns=now;p->transition_ns=now;p->s.last_completed_id=id;p->s.input_state=3;
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
