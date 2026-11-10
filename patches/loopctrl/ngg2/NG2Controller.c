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
#define INITIAL_PREPARATION UINT64_C(50000000)
#define INITIAL_PUBLICATION UINT64_C(100000000)
#define CONTINUOUS_PUBLICATION UINT64_C(100000000)
#define CONTINUOUS_SOURCE UINT64_C(200000000)
static const uint64_t leads[7]={150000000,75000000,225000000,300000000,375000000,450000000,25000000};
static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
enum { NG2_CONTINUOUS_NONE=0, NG2_CONTINUOUS_SAME=1, NG2_CONTINUOUS_FRESH=2 };
struct NG2Controller {
    NG2ControllerStatus s;
    NG2Scene scene,before,retune_anchor;
    NG2Scene motion_reference_scene;
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
    uint16_t visits[NG2_VISIT_COUNT];
    uint16_t motion_reference_visits[NG2_VISIT_COUNT];
    uint8_t restart_fingerprint[48];
    uint64_t seen_id,seen_start,seen_end,last_now,transition_ns,sync_ns;
    uint64_t ack_ns,command_period,next_nominal,next_deadline,next_period,last_observed_prefix;
    uint64_t motion_retry_start_ns;
    uint64_t latest_verified_ns;
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
};
static int tile_index(int x,int y){return x>=-11&&x<=11&&y>=-5&&y<=4?(y+5)*23+x+11:-1;}
static int tile(const NG2Scene *s,int x,int y){int k=tile_index(x,y);return k<0?0:s->tiles[k];}
static int protected_at(const NG2Scene *s,int x,int y){int k=tile_index(x,y);return k>=0&&s->protected_cells[k];}
static int valid_time(uint64_t t){return t<NS_LIMIT;}
static uint64_t minimum(uint64_t a,uint64_t b){return a<b?a:b;}
static uint64_t maximum(uint64_t a,uint64_t b){return a>b?a:b;}
static int valid_scene(const NG2Scene *s){
    int i;
    if(!s||s->abi_version!=NG2_ABI_VERSION||s->struct_size!=sizeof(*s)||s->state<0||s->state>2
        ||s->restart_label<0||s->restart_label>1||s->gold_state<0||s->gold_state>2
        ||s->gold_peak<0||s->gold_peak>255||s->goods<0||s->goods>2||s->beat_valid<0||s->beat_valid>1)return 0;
    for(i=0;i<NG2_TILE_COUNT;++i)if(s->tiles[i]>NG2_TILE_ITEM||s->protected_cells[i]>1)return 0;
    return 1;
}
static NG2ControllerEvent *event(NG2Controller *p){return p->event_count?&p->events[p->event_count-1]:NULL;}
static void terminal(NG2Controller *p,uint64_t now,int reason){
    p->preparation_epoch=0;
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
static void clear_model(NG2Controller *p){
    memset(&p->model,0,sizeof(p->model));p->sample_count=0;p->s.beat_period_ns=0;p->beat_failed=0;
    p->model_capture_id=0;
}
static int initial_recoverable(const NG2Controller *p){
    return !p->finish_requested&&!p->s.terminal&&!p->s.goods&&p->s.walk_started_ns
        &&!p->s.inputs&&!p->s.moves&&!p->s.lead_confirmed
        &&(p->s.input_state==0||(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE));
}
static uint64_t sync_deadline(const NG2Controller *p){
    uint64_t deadline=minimum(p->sync_ns+12*SECOND,p->s.started_ns+180*SECOND);
    if(p->s.walk_started_ns)deadline=minimum(deadline,p->s.walk_started_ns+45*SECOND);
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
    return p->initial_slot_target&&!p->s.inputs&&!p->s.moves&&!p->s.lead_confirmed;
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
static void start_floor(NG2Controller *p,const NG2Scene *scene,uint64_t end){
    if(scene->state!=NG2_FLOOR)return;
    if(scene->gold_state==NG2_GOLD_CANDIDATE){
        if(!p->s.walk_started_ns){p->s.walk_started_ns=end;p->sync_ns=end;clear_model(p);}
        p->s.phase=NG2_PHASE_SYNC;
    }else if(scene->gold_state==NG2_GOLD_CLEAR){
        memcpy(p->restart_fingerprint,scene->fingerprint,48);p->s.phase=NG2_PHASE_FLOOR;
    }
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
        ||p->s.inputs||p->s.moves||p->s.lead_confirmed||!p->initial_ticket_valid
        ||p->command.kind!=NG2_ACTION_MOVE||direction<1||direction>4
        ||!safe_floor(&p->before,direction)||!safe_floor(scene,direction)
        ||!same_gold(&p->before,scene)||!ng2_beat_model_valid(&p->model)
        ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned)
        ||!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&choice)
        ||choice.direction!=direction
        ||!ng2_motion(&p->before,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)return 0;
    return 1;
}
static int same_choice(const NG2Decision *a,const NG2Decision *b){
    return a->direction==b->direction&&a->reason==b->reason&&a->target_x==b->target_x
        &&a->target_y==b->target_y&&a->obstacle==b->obstacle;
}
/* Preserve the published initial ticket through irrelevant remote palette
 * flicker throughout its publication window. Its source/before remain frozen;
 * every accepted current image must independently prove the same safe step. */
static int quiet_initial_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision before,latest;NG2Motion motion;uint64_t aligned;int i,d=p->command.direction;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->finish_requested
        ||p->replan_pending||p->s.inputs||p->s.moves||p->s.lead_confirmed
        ||!p->initial_ticket_valid||d<1||d>4||p->beat_failed
        ||p->command.not_before_ns<INITIAL_PUBLICATION
        ||now<p->command.not_before_ns-INITIAL_PUBLICATION||now>p->command.deadline_ns
        ||!safe_floor(&p->before,d)||!safe_floor(scene,d)
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
    return ng2_choose(&p->before,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
        &&ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&latest)
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
/* An already-open entrance is a single observed-floor step, including when
 * distant merchandise is only PARTIAL. Remote palette flicker cannot alter
 * that exact action. Keep its original ticket/before and all absolute bounds;
 * do not grant safe-floor calibration, reissue or reference eligibility. */
static int quiet_gate_observation(const NG2Controller *p,const NG2Scene *scene,uint64_t now){
    NG2Decision before,latest;NG2Motion motion;uint64_t aligned;int i,d=p->command.direction;
    if(p->s.input_state!=1||p->command.kind!=NG2_ACTION_MOVE||p->finish_requested||p->s.goods
        ||p->replan_pending||p->continuous_pending||!p->s.lead_confirmed||!p->s.moves
        ||p->s.phase!=NG2_PHASE_WALK||!p->continuous_ticket_valid||d<1||d>4
        ||p->command_choice.reason!=5||p->command_choice.obstacle!=NG2_TILE_FLOOR
        ||p->command_choice.target_x!=dx[d]||p->command_choice.target_y!=dy[d]
        ||p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=scene->goods||scene->goods<NG2_GOODS_UNKNOWN||scene->goods>NG2_GOODS_PARTIAL
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!same_gold(&p->before,scene)
        ||memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(scene,0,0)!=NG2_TILE_FLOOR
        ||tile(&p->before,dx[d],dy[d])!=NG2_TILE_FLOOR||tile(scene,dx[d],dy[d])!=NG2_TILE_FLOOR
        ||!gate_at(&p->before,dx[d],dy[d])||!gate_at(scene,dx[d],dy[d])
        ||p->beat_failed||!ng2_beat_model_valid(&p->model)
        ||now>p->command.deadline_ns||now>p->continuous_ticket.deadline_ns
        ||now<p->command.source_start_ns||now-p->command.source_start_ns>FRESH
        ||now<p->command.phase_sample_ns||now-p->command.phase_sample_ns>FRESH
        ||now<p->model.last_ns||now-p->model.last_ns>FRESH||now>continuous_horizon(p)
        ||(p->command_sync_deadline&&now>=p->command_sync_deadline)
        ||now-p->s.walk_started_ns>=45*SECOND||now-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return 0;
    for(i=0;i<5;++i)
        if(protected_at(scene,dx[i],dy[i])||protected_at(scene,dx[d]+dx[i],dy[d]+dy[i]))return 0;
    for(i=0;i<NG2_TILE_COUNT;++i){
        int a=p->before.tiles[i],b=scene->tiles[i],x=i%23-11,y=i/23-5;
        if(a==b)continue;
        if((abs(x)<=1&&abs(y)<=1)||(abs(x-dx[d])<=1&&abs(y-dy[d])<=1)
            ||(a!=NG2_TILE_UNKNOWN&&a!=NG2_TILE_FLOOR&&a!=NG2_TILE_DIRT&&a!=NG2_TILE_STONE)
            ||(b!=NG2_TILE_UNKNOWN&&b!=NG2_TILE_FLOOR&&b!=NG2_TILE_DIRT&&b!=NG2_TILE_STONE))return 0;
    }
    return ng2_choose(&p->before,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
        &&ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&latest)
        &&same_choice(&before,&p->command_choice)&&same_choice(&before,&latest)
        &&ng2_motion(&p->before,scene,d,&motion)&&motion.kind==NG2_BLOCKED&&!motion.dx&&!motion.dy;
}
static int continuous_allowed(int validation){
    return validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED||validation==NG2_REVALIDATE_FRESH_ALLOWED;
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
        ||!safe_floor(&p->before,direction)||!safe_floor(scene,direction))strict=NG2_REVALIDATE_FLOOR;
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
    if(!ng2_choose(&p->before,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
        ||before.direction!=direction||!same_choice(&before,&p->command_choice))return NG2_REVALIDATE_ROUTE;
    if(!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&after)
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
        ||!safe_floor(&p->motion_reference_scene,direction)||!safe_floor(scene,direction)
        ||!same_gold(&p->motion_reference_scene,scene)
        ||memcmp(p->motion_reference_scene.protected_cells,scene->protected_cells,NG2_TILE_COUNT)
        ||!ng2_choose(&p->motion_reference_scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&original)
        ||!same_choice(&original,&p->motion_reference_choice)||!same_choice(&original,&p->command_choice)
        ||!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&latest)
        ||!same_choice(&original,&latest)
        ||!ng2_motion(&p->motion_reference_scene,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)p->motion_reference_valid=0;
}
static void create_motion_reference(NG2Controller *p){
    NG2Decision choice;int direction=p->command.direction;
    p->motion_reference_present=p->motion_reference_valid=p->motion_reference_reissued=0;
    if(!p->s.lead_confirmed||!p->s.moves||direction<1||direction>4||p->scene.gold_state!=NG2_GOLD_CANDIDATE
        ||!safe_floor(&p->scene,direction)
        ||!ng2_choose(&p->scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&choice)
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
NG2Controller *ng2_controller_create(uint64_t now){
    NG2Controller *p;
    if(!valid_time(now)||now>NS_LIMIT-180*SECOND-1)return NULL;
    p=(NG2Controller*)calloc(1,sizeof(*p));
    if(p){p->s.abi_version=NG2_ABI_VERSION;p->s.struct_size=sizeof(p->s);p->s.started_ns=now;
        p->last_now=now;p->transition_ns=now;p->s.lead_ns=leads[0];p->visits[16*33+16]=1;}
    return p;
}
void ng2_controller_destroy(NG2Controller *p){free(p);}
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
    /* Adjacent 40ms images can all show the same unfinished camera scroll.
     * Keep the first assessment immediate, then sample at a quarter and a
     * full original period without extending its immutable visual deadline. */
    if(p->motion_wait.attempts){
        uint64_t spacing=p->motion_wait.attempts==1?p->command_period/4:p->command_period;
        if(start<p->motion_retry_start_ns||start-p->motion_retry_start_ns<spacing)return;
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
    ++p->motion_wait.attempts;p->motion_wait.last_capture_id=id;p->motion_wait.last_motion=motion.kind;
    if(e){e->observed_capture_id=id;e->motion=motion.kind;e->dx=motion.dx;e->dy=motion.dy;}
    if((motion.kind==NG2_TWEEN||motion.kind==NG2_MOTION_UNKNOWN)&&p->motion_wait.attempts<3)return;
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
        if(!safe_floor(&p->before,direction)||!safe_floor(scene,direction)||!same_gold(&p->before,scene)
            ||!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&decision)
            ||decision.direction!=direction||p->lead_index>=6){finish(p,end,NG2_REASON_MOVEMENT);return;}
        if(!p->have_anchor){p->retune_anchor=p->before;p->retune_direction=direction;p->have_anchor=1;}
        ++p->lead_index;p->s.lead_ns=leads[p->lead_index];p->s.next_target_ns=0;p->next_nominal=0;
        p->proof_deadline=p->motion_wait.deadline_ns;p->proof_capture_id=id;p->proof_reacquire=1;
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
    int pending_kind,mask=0,changed_tiles=0,changed_protected=0;
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
    if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
        ++p->s.discarded_frames;return 0;}
    /* Even unchanged tiles can hide signature-only drift. Revalidate the
     * immutable original directly against every accepted pre-send image. */
    if((p->s.input_state==1||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE)
        validate_motion_reference(p,scene,start,end,prefix,end);
    if(mask&&(quiet_initial_observation(p,scene,commit)||quiet_gate_observation(p,scene,commit)))mask=0;
    if(mask){
        NG2Decision latest;
        int validation=p->s.lead_confirmed?continuous_validation(p,scene,end,&latest):
            (can_replan(p,scene)?NG2_REVALIDATE_INITIAL_ALLOWED:NG2_REVALIDATE_INITIAL_REJECTED);
        int allowed=validation==NG2_REVALIDATE_INITIAL_ALLOWED||continuous_allowed(validation);
        record_change(p,scene,id,mask,changed_tiles,changed_protected,allowed,validation);
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
    p->scene=*scene;p->have_scene=1;p->need_fresh_cleanup=0;p->last_observed_prefix=prefix;
    p->s.paused=scene->state==NG2_PAUSE;
    p->s.last_capture_id=id;p->s.last_capture_start_ns=start;p->s.last_capture_end_ns=end;++p->s.accepted_frames;
    if(!p->s.goods)p->s.goods=scene->goods==NG2_GOODS_VISIBLE;
    if(p->s.input_state==3){
        pending_kind=p->command.kind;
        if(pending_kind==NG2_ACTION_MOVE){
            if(scene->state!=NG2_FLOOR){p->s.input_state=0;p->s.current_command_id=0;finish(p,end,NG2_REASON_SCREEN);}
            else if(p->s.goods){
                event(p)->observed_capture_id=id;
                resolve_move(p,scene,id,start,end);
                end_visual_wait(p);finish(p,end,NG2_REASON_GOODS);
            }
            else {add_sample(p,scene,id,start,end);resolve_move(p,scene,id,start,end);}
        }else if(start>=p->ack_ns){
            if(pending_kind==NG2_ACTION_RESUME&&scene->state==NG2_FLOOR){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;clear_model(p);start_floor(p,scene,end);
            }else if(pending_kind==NG2_ACTION_PAUSE&&scene->state==NG2_PAUSE){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;p->s.paused=1;
                if(p->finish_requested){terminal(p,end,p->s.reason);return 1;}
                p->s.phase=NG2_PHASE_PAUSE;
            }else if(pending_kind==NG2_ACTION_RESTART&&scene->state==NG2_FLOOR
                &&ng2_fingerprint_changed(p->restart_fingerprint,scene->fingerprint)){
                event(p)->observed_capture_id=id;
                p->s.input_state=0;p->s.current_command_id=0;p->restart_pending=0;++p->s.restarts;
                clear_model(p);start_floor(p,scene,end);
            }
        }
    }else if(!p->finish_requested){
        if(p->s.phase==NG2_PHASE_SEARCH&&scene->state==NG2_FLOOR)start_floor(p,scene,end);
    }
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
        memset(&p->motion_wait,0,sizeof(p->motion_wait));p->motion_retry_start_ns=0;
        p->motion_wait.command_id=p->command.id;p->motion_wait.source_capture_id=p->command.source_capture_id;
        p->schedule_deadline=minimum(next-p->s.lead_ns+10000000,wait_horizon);
        p->motion_wait.deadline_ns=wait_horizon;
        if(initial_slot_active(p)){
            p->schedule_deadline=minimum(p->schedule_deadline,p->initial_slot_motion_deadline);
            p->motion_wait.deadline_ns=minimum(p->motion_wait.deadline_ns,p->initial_slot_visual_deadline);
        }
        if(p->initial_visual_deadline&&!p->s.inputs)
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
        if(!p->s.inputs)p->initial_visual_deadline=p->motion_wait.deadline_ns;
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
    if(kind==NG2_ACTION_MOVE){p->recovery.mode=NG2_RECOVERY_NORMAL;clear_recovery_slot(p);}
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
static int recover_unsent_continuous(NG2Controller *p,uint64_t now){
    NG2ControllerEvent *e=event(p);NG2Motion still;NG2Decision before,latest;uint64_t budget;
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
    if(!fresh(p,now)||p->last_observed_prefix!=p->s.last_completed_id
        ||p->before.state!=NG2_FLOOR||p->scene.state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||p->scene.goods!=NG2_GOODS_UNKNOWN
        ||p->before.gold_state!=NG2_GOLD_CANDIDATE||p->scene.gold_state!=NG2_GOLD_CANDIDATE
        ||tile(&p->before,0,0)!=NG2_TILE_FLOOR||tile(&p->scene,0,0)!=NG2_TILE_FLOOR
        ||memcmp(p->before.tiles,p->scene.tiles,NG2_TILE_COUNT)
        ||memcmp(p->before.protected_cells,p->scene.protected_cells,NG2_TILE_COUNT)
        ||!ng2_choose(&p->before,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
        ||!ng2_choose(&p->scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&latest)
        ||!same_choice(&before,expected)||!same_choice(&before,&latest)
        ||!ng2_motion(&p->before,&p->scene,p->command.direction,&still)
        ||still.kind!=NG2_BLOCKED||still.dx||still.dy)return 0;
    if(!pending)not_sent(p,now,NG2_REASON_LATE);
    if(p->command_sync_deadline)p->recovery.mode=NG2_RECOVERY_POST_MOVE;
    post_move_recover(p,now,NG2_RECOVERY_UNSENT_DEADLINE);
    memset(&p->command,0,sizeof(p->command));p->s.current_command_id=0;
    return 1;
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
        if(p->proof_reacquire||p->visual_phase_failed||p->beat_failed||!ng2_beat_model_valid(&p->model)
            ||now>p->schedule_deadline||!p->s.next_target_ns||now>p->next_deadline
            ||(p->next_update_deadline&&now>p->next_update_deadline))
            post_move_recover(p,now,p->visual_phase_failed||p->beat_failed?
                NG2_RECOVERY_VISUAL_PHASE:NG2_RECOVERY_VISUAL_SCHEDULE);
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
            &&p->last_observed_prefix==p->s.last_completed_id){
            p->final_pause_attempted=1;return reserve(p,now,NG2_ACTION_PAUSE,0,0,out);}
        if(now>=p->finish_ns&&now-p->finish_ns>=TRANSITION)terminal(p,now,p->s.reason);
        return 0;
    }
    if(!p->have_scene){if(now-p->s.started_ns>=TRANSITION)terminal(p,now,NG2_REASON_CAPTURE);return 0;}
    if(!fresh(p,now)){finish(p,now,NG2_REASON_STALE);return 0;}
    if(p->scene.state==NG2_UNKNOWN){if(now-p->transition_ns>=TRANSITION)terminal(p,now,NG2_REASON_SCREEN);return 0;}
    if(p->s.phase==NG2_PHASE_SEARCH&&p->scene.state==NG2_PAUSE)return reserve(p,now,NG2_ACTION_RESUME,0,0,out);
    if(p->s.phase==NG2_PHASE_PAUSE){
        if(p->scene.state==NG2_PAUSE&&p->scene.restart_label&&now>=p->ack_ns+200000000){
            if(p->s.restarts>=12){finish(p,now,NG2_REASON_LIMIT);return 0;}
            p->restart_pending=1;return reserve(p,now,NG2_ACTION_RESTART,0,0,out);}
        if(now>=p->ack_ns&&now-p->ack_ns>=TRANSITION)terminal(p,now,NG2_REASON_RESTART);
        return 0;
    }
    if(p->scene.state!=NG2_FLOOR){finish(p,now,NG2_REASON_SCREEN);return 0;}
    if(p->s.phase==NG2_PHASE_FLOOR&&p->scene.gold_state==NG2_GOLD_CLEAR){
        if(p->s.restarts>=12){finish(p,now,NG2_REASON_LIMIT);return 0;}
        return reserve(p,now,NG2_ACTION_PAUSE,0,0,out);
    }
    if(!p->s.walk_started_ns){
        if(p->scene.gold_state==NG2_GOLD_CANDIDATE)start_floor(p,&p->scene,now);
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
    if(p->s.inputs>=16){finish(p,now,NG2_REASON_LIMIT);return 0;}
    if(!ng2_choose(&p->scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&choice)){
        finish(p,now,choice.reason==2?NG2_REASON_PARTIAL_GOODS:NG2_REASON_NO_PATH);return 0;}
    if(p->have_anchor&&!p->s.lead_confirmed&&(!same_gold(&p->retune_anchor,&p->scene)||choice.direction!=p->retune_direction
        ||!safe_floor(&p->scene,choice.direction))){finish(p,now,NG2_REASON_MOVEMENT);return 0;}
    if(p->recovery.mode==NG2_RECOVERY_POST_MOVE){
        p->s.next_target_ns=p->recovery_slot_target;
    }else if(p->replan_pending){
        uint64_t aligned;
        if(p->s.inputs||p->s.moves||p->s.lead_confirmed||choice.direction!=p->initial_ticket.direction
            ||!safe_floor(&p->scene,choice.direction)||now>p->initial_ticket.deadline_ns
            ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned)){
            p->replan_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        p->s.next_target_ns=p->initial_ticket.target_ns;
    }else if(p->continuous_pending){
        uint64_t aligned;
        int valid_choice=p->continuous_pending==NG2_CONTINUOUS_FRESH?
            same_choice(&choice,&p->continuous_pending_choice):
            same_continuous_action(&choice,&p->command_choice)&&safe_floor(&p->scene,choice.direction);
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
    }else if(!p->s.inputs&&!p->s.moves&&!p->initial_ticket_valid){
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
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&p->replan_count>0&&p->s.inputs==0
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
