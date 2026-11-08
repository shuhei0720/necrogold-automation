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
#define INITIAL_PREPARATION UINT64_C(50000000)
#define INITIAL_PUBLICATION UINT64_C(100000000)
static const uint64_t leads[7]={150000000,75000000,225000000,300000000,375000000,450000000,25000000};
static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
struct NG2Controller {
    NG2ControllerStatus s;
    NG2Scene scene,before,retune_anchor;
    NG2Entrance entrance;
    NG2BeatModel model;
    NG2BeatSample samples[13];
    NG2ControllerEvent events[EVENT_CAP];
    NG2Command command;
    NG2Command initial_ticket;
    NG2Command continuous_ticket;
    NG2Decision command_choice;
    NG2ControllerSceneChange scene_changes[3];
    NG2ControllerSceneDetail scene_details[3];
    NG2ControllerMotionWait motion_wait;
    uint16_t visits[NG2_VISIT_COUNT];
    uint8_t restart_fingerprint[48];
    uint64_t seen_id,seen_start,seen_end,last_now,transition_ns,sync_ns;
    uint64_t ack_ns,command_period,next_nominal,next_deadline,next_period,last_observed_prefix;
    uint64_t finish_ns;
    size_t sample_count,event_count;
    size_t scene_change_count;
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
static int corrected(NG2Controller *p,uint64_t nominal,uint64_t period,uint64_t *out){
    uint64_t target=closest(&p->model,nominal),delta=target>=nominal?target-nominal:nominal-target;
    if((double)delta>.08*(double)period)return 0;
    *out=target;return 1;
}
/* A slot plans only one initial physical beat. It grants no scene/input
 * authority and is never selected again after a late or invalid observation. */
static int initial_slot_active(const NG2Controller *p){
    return p->initial_slot_target&&!p->s.inputs&&!p->s.moves&&!p->s.lead_confirmed;
}
static void add_sample(NG2Controller *p,const NG2Scene *scene,uint64_t start,uint64_t end){
    NG2BeatSample sample;NG2BeatModel updated;size_t i,drop;
    uint64_t previous=p->model.last_ns;
    if(!scene->beat_valid||!ng2_make_sample(scene->beat_remaining,scene->beat_spacing,scene->beat_center,start,end,&sample))return;
    if(p->sample_count&&sample.midpoint_ns<=p->samples[p->sample_count-1].midpoint_ns)return;
    while(p->sample_count&&sample.midpoint_ns-p->samples[0].midpoint_ns>20*SECOND){
        memmove(p->samples,p->samples+1,(--p->sample_count)*sizeof(sample));}
    p->samples[p->sample_count++]=sample;
    if(p->sample_count>12){uint64_t density=UINT64_MAX;drop=0;
        for(i=1;i+1<p->sample_count;++i)if(p->samples[i].midpoint_ns!=previous){
            uint64_t width=p->samples[i+1].midpoint_ns-p->samples[i-1].midpoint_ns;
            if(width<density){density=width;drop=i;}}
        /* First and latest survive thinning; previous model.last survives too. */
        if(!drop){p->beat_failed=1;return;}
        memmove(p->samples+drop,p->samples+drop+1,(p->sample_count-drop-1)*sizeof(sample));--p->sample_count;
    }
    if(ng2_beat_model_valid(&p->model)){
        if(ng2_beat_track(&p->model,p->samples,p->sample_count,&updated)){
            p->model=updated;p->s.beat_period_ns=updated.period_ns;
        }else if(p->s.lead_confirmed||initial_slot_active(p)){p->beat_failed=1;return;}
        else memset(&p->model,0,sizeof(p->model));
    }
    if(!ng2_beat_model_valid(&p->model)&&p->sample_count>=4
        &&sample.midpoint_ns-p->samples[0].midpoint_ns>=2*SECOND
        &&ng2_beat_fit(p->samples,p->sample_count,&updated)){
        p->model=updated;p->s.beat_period_ns=updated.period_ns;
    }
    if(p->s.lead_confirmed&&ng2_beat_model_valid(&p->model)){
        uint64_t target;
        if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE){
            if(!corrected(p,p->command.target_ns,p->command_period,&target))p->beat_failed=1;
        }else if(p->next_nominal){
            if(!corrected(p,p->next_nominal,p->next_period,&target))p->beat_failed=1;
            else p->s.next_target_ns=target;
        }
    }
    if(initial_slot_active(p)){
        uint64_t aligned;
        if(!ng2_beat_model_valid(&p->model)
            ||!corrected(p,p->initial_slot_target,p->initial_slot_period,&aligned))p->beat_failed=1;
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
static int same_continuous_action(const NG2Decision *a,const NG2Decision *b){
    if(a->direction!=b->direction||a->reason!=b->reason||a->obstacle!=b->obstacle)return 0;
    /* Reason 8 is observed_floor_vantage. Its remote target may change while
     * the planner still authorizes the same single step onto observed floor. */
    return (a->reason==8&&a->obstacle==NG2_TILE_FLOOR)
        ||(a->target_x==b->target_x&&a->target_y==b->target_y);
}
/* Only a definitely-unsent ticket may be replaced. Unlike initial lead
 * calibration, continuous revalidation proves the cached source decision,
 * the current action and protected set, without searching for another beat. */
static int continuous_validation(NG2Controller *p,const NG2Scene *scene,uint64_t end){
    NG2Decision before,after;NG2Motion motion;uint64_t aligned;
    int direction=p->command.direction;
    if(p->s.input_state!=1||p->replan_pending||p->continuous_pending||p->finish_requested
        ||!p->s.lead_confirmed||!p->s.moves||p->s.phase!=NG2_PHASE_WALK||!p->continuous_ticket_valid
        ||p->command.kind!=NG2_ACTION_MOVE||direction<1||direction>4)return NG2_REVALIDATE_STATE;
    if(p->continuous_chain_count>=2||p->continuous_count>=8)return NG2_REVALIDATE_BUDGET;
    if(end>p->continuous_ticket.deadline_ns||!ng2_beat_model_valid(&p->model)||p->beat_failed
        ||end<p->command.phase_sample_ns||end-p->command.phase_sample_ns>FRESH
        ||end<p->command.source_start_ns||end-p->command.source_start_ns>FRESH
        ||end-p->s.walk_started_ns>=45*SECOND||end-p->s.started_ns>=180*SECOND
        ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned))return NG2_REVALIDATE_TIMING;
    if(p->before.state!=NG2_FLOOR||scene->state!=NG2_FLOOR
        ||p->before.goods!=NG2_GOODS_UNKNOWN||scene->goods!=NG2_GOODS_UNKNOWN
        ||!safe_floor(&p->before,direction)||!safe_floor(scene,direction))return NG2_REVALIDATE_FLOOR;
    if(p->before.gold_state!=NG2_GOLD_CANDIDATE||scene->gold_state!=NG2_GOLD_CANDIDATE
        ||!same_gold(&p->before,scene))return NG2_REVALIDATE_GOLD;
    if(memcmp(p->before.protected_cells,scene->protected_cells,NG2_TILE_COUNT))return NG2_REVALIDATE_PROTECTED;
    if(!ng2_choose(&p->before,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&before)
        ||!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&after)
        ||before.direction!=direction||!same_choice(&before,&p->command_choice)
        ||!same_continuous_action(&before,&after))return NG2_REVALIDATE_ROUTE;
    if(!ng2_motion(&p->before,scene,direction,&motion)||motion.kind!=NG2_BLOCKED
        ||motion.dx||motion.dy)return NG2_REVALIDATE_MOTION;
    return NG2_REVALIDATE_CONTINUOUS_ALLOWED;
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
    detail->continuous_count=p->continuous_count+(validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED);
    detail->chain_count=p->continuous_chain_count+(validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED);
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
    uint64_t earliest=maximum(p->ack_ns,p->command.target_ns+80000000);
    int direction=p->command.direction;
    if(start<earliest)return;
    if(end>p->motion_wait.deadline_ns){
        end_visual_wait(p);
        finish(p,end,NG2_REASON_LATE);return;
    }
    if(!ng2_motion(&p->before,scene,direction,&motion)){motion.kind=NG2_MOTION_UNKNOWN;motion.dx=motion.dy=0;}
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
        if(!p->s.first_move_ns&&e)p->s.first_move_ns=e->begin_ns;
    }else if(motion.kind==NG2_DOOR_OPENED||motion.kind==NG2_TERRAIN_OPENED){
        if(motion.kind==NG2_DOOR_OPENED)++p->s.door_changes;else ++p->s.terrain_changes;
        /* An opening is a verified terrain change, never the displacement
         * proof required to calibrate native lead or begin continuous beats. */
        if(!p->s.lead_confirmed){p->s.next_target_ns=0;p->next_nominal=0;p->s.phase=NG2_PHASE_SYNC;return;}
    }else if(motion.kind==NG2_BLOCKED&&!p->s.lead_confirmed){
        if(!safe_floor(&p->before,direction)||!safe_floor(scene,direction)||!same_gold(&p->before,scene)
            ||!ng2_choose(scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&decision)
            ||decision.direction!=direction||p->lead_index>=6){finish(p,end,NG2_REASON_MOVEMENT);return;}
        if(!p->have_anchor){p->retune_anchor=p->before;p->retune_direction=direction;p->have_anchor=1;}
        ++p->lead_index;p->s.lead_ns=leads[p->lead_index];p->s.next_target_ns=0;p->next_nominal=0;
        p->s.phase=NG2_PHASE_SYNC;return;
    }else {finish(p,end,NG2_REASON_MOVEMENT);return;}
    p->s.last_ordinal=p->command.ordinal;
    if(p->command.target_ns>=NS_LIMIT-p->command_period){
        p->s.next_target_ns=0;p->next_nominal=0;finish(p,end,NG2_REASON_SESSION);return;
    }
    p->next_nominal=p->command.target_ns+p->command_period;p->next_period=p->command_period;
    p->next_deadline=p->next_nominal-p->s.lead_ns+10000000;
    p->s.next_target_ns=p->next_nominal;
    if(ng2_beat_model_valid(&p->model)){
        uint64_t target;if(corrected(p,p->next_nominal,p->next_period,&target))p->s.next_target_ns=target;
        else p->beat_failed=1;
    }
    p->s.phase=NG2_PHASE_WALK;
}
int ng2_controller_observe(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,int32_t stable){
    int pending_kind,mask=0,changed_tiles=0,changed_protected=0;
    if(!p)return -1;
    if(p->s.terminal)return 0;
    ++p->s.capture_count;
    if(!id||!valid_time(start)||!valid_time(end)||end<=start||start<p->s.started_ns||(start<p->last_now&&p->last_now-start>FRESH)||id<=p->seen_id
        ||(p->seen_id&&(start<=p->seen_start||end<=p->seen_end))){++p->s.discarded_frames;return 0;}
    p->seen_id=id;p->seen_start=start;p->seen_end=end;
    if(!valid_scene(scene)||stable<0||stable>1){++p->s.discarded_frames;terminal(p,end,NG2_REASON_GEOMETRY);return 0;}
    if((p->s.input_state==1||p->replan_pending||p->continuous_pending)&&p->command.kind==NG2_ACTION_MOVE)
        mask=scene_change(&p->before,scene,&changed_tiles,&changed_protected);
    /* A current goods observation latches before prefix/phase checks. Only a
     * subsequent stable matching prefix may authorize the holding pause. */
    if(scene->goods==NG2_GOODS_VISIBLE){finish(p,end,NG2_REASON_GOODS);p->need_fresh_cleanup=1;}
    if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
        ++p->s.discarded_frames;return 0;}
    if(mask){
        int validation=p->s.lead_confirmed?continuous_validation(p,scene,end):
            (can_replan(p,scene)?NG2_REVALIDATE_INITIAL_ALLOWED:NG2_REVALIDATE_INITIAL_REJECTED);
        int allowed=validation==NG2_REVALIDATE_INITIAL_ALLOWED||validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED;
        record_change(p,scene,id,mask,changed_tiles,changed_protected,allowed,validation);
        not_sent(p,end,NG2_REASON_SCREEN);
        if(validation==NG2_REVALIDATE_INITIAL_ALLOWED){++p->replan_count;p->replan_pending=1;p->before=*scene;}
        else if(validation==NG2_REVALIDATE_CONTINUOUS_ALLOWED){
            ++p->continuous_count;++p->continuous_chain_count;p->continuous_pending=1;p->before=*scene;
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
            else {add_sample(p,scene,start,end);resolve_move(p,scene,id,start,end);}
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
        &&p->s.input_state!=3)add_sample(p,scene,start,end);
    if(p->beat_failed&&!p->finish_requested)finish(p,end,NG2_REASON_BEAT);
    return 1;
}
static int reserve(NG2Controller *p,uint64_t now,int kind,int direction,uint64_t target,NG2Command *out){
    NG2ControllerEvent *e;uint64_t deadline,horizon,tail;
    if(p->event_count>=EVENT_CAP){terminal(p,now,NG2_REASON_LIMIT);return 0;}
    memset(&p->command,0,sizeof(p->command));
    p->command.id=(uint64_t)p->event_count+1;p->command.kind=kind;p->command.direction=direction;
    p->command.source_capture_id=p->s.last_capture_id;p->command.source_start_ns=p->s.last_capture_start_ns;
    p->command.phase_sample_ns=kind==NG2_ACTION_MOVE?p->model.last_ns:0;
    p->command.target_ns=target;p->command.not_before_ns=kind==NG2_ACTION_MOVE?target-p->s.lead_ns:now;
    if(kind==NG2_ACTION_MOVE&&initial_slot_active(p)){
        p->command.target_ns=p->initial_slot_target;p->command.not_before_ns=p->initial_slot_not_before;
    }
    tail=kind==NG2_ACTION_MOVE?p->s.lead_ns+50000000:50000000;
    horizon=minimum(p->s.last_capture_start_ns+FRESH,p->s.started_ns+180*SECOND);
    if(kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->model.last_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    /* Preserve the original target-plus-50ms and actual-send-plus-lead-plus-
     * 50ms contract. Tighten the main ticket; never spend a 10ms allowance
     * beyond image, phase, walk, or session validity. */
    if(horizon<tail||p->command.not_before_ns>horizon-tail){finish(p,now,NG2_REASON_STALE);return 0;}
    deadline=kind==NG2_ACTION_MOVE?p->command.not_before_ns+10000000:now+SECOND;
    if(kind==NG2_ACTION_MOVE&&initial_slot_active(p))deadline=minimum(deadline,p->initial_slot_deadline);
    if(kind==NG2_ACTION_MOVE&&p->replan_pending)deadline=minimum(deadline,p->initial_ticket.deadline_ns);
    if(kind==NG2_ACTION_MOVE&&p->continuous_pending)deadline=minimum(deadline,p->continuous_ticket.deadline_ns);
    if(kind==NG2_ACTION_MOVE&&p->s.lead_confirmed)deadline=minimum(deadline,p->next_deadline);
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
    p->before=p->scene;p->command_period=kind==NG2_ACTION_MOVE&&initial_slot_active(p)?p->initial_slot_period:p->model.period_ns;
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
        p->command.direction=p->continuous_ticket.direction;
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
        memset(&p->motion_wait,0,sizeof(p->motion_wait));
        p->motion_wait.command_id=p->command.id;p->motion_wait.source_capture_id=p->command.source_capture_id;
        p->motion_wait.deadline_ns=minimum(next-p->s.lead_ns+10000000,wait_horizon);
        if(initial_slot_active(p))p->motion_wait.deadline_ns=minimum(p->motion_wait.deadline_ns,p->initial_slot_motion_deadline);
        if(p->continuous_pending){p->motion_wait.deadline_ns=p->continuous_motion_deadline;p->continuous_pending=0;}
        else if(p->s.lead_confirmed){p->continuous_ticket=p->command;p->continuous_period=p->command_period;
            p->continuous_motion_deadline=p->motion_wait.deadline_ns;p->continuous_ticket_valid=1;p->continuous_chain_count=0;}
    }
    p->s.input_state=1;p->s.current_command_id=p->command.id;
    e=&p->events[p->event_count++];memset(e,0,sizeof(*e));e->command=p->command;
    *out=p->command;return 1;
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
    if(p->s.input_state==1){
        if(now>p->command.deadline_ns){not_sent(p,now,NG2_REASON_LATE);finish(p,now,NG2_REASON_LATE);}
        else return 0;
    }
    if(p->s.input_state==3){
        uint64_t timeout=p->command.kind==NG2_ACTION_PAUSE&&p->finish_requested?FRESH:TRANSITION;
        if(p->command.kind==NG2_ACTION_MOVE&&now>p->motion_wait.deadline_ns){
            end_visual_wait(p);finish(p,now,NG2_REASON_LATE);
        }else{
            if(now>=p->ack_ns&&now-p->ack_ns>=timeout){terminal(p,now,p->command.kind==NG2_ACTION_RESTART?NG2_REASON_RESTART:NG2_REASON_CAPTURE);}
            return 0;
        }
    }
    if(!p->finish_requested&&initial_slot_active(p)){
        uint64_t aligned;
        if(p->beat_failed||!ng2_beat_model_valid(&p->model)||now<p->model.last_ns
            ||now-p->model.last_ns>FRESH
            ||!corrected(p,p->initial_slot_target,p->initial_slot_period,&aligned)){
            finish(p,now,NG2_REASON_BEAT);return 0;
        }
        if(!p->initial_ticket_valid&&now>p->initial_slot_not_before-INITIAL_PREPARATION){
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
        p->replan_pending=0;finish(p,now,reason);return 0;
    }
    if(p->continuous_pending&&(!ng2_beat_model_valid(&p->model)||now>p->continuous_ticket.deadline_ns)){
        int reason=now>p->continuous_ticket.deadline_ns?NG2_REASON_LATE:NG2_REASON_BEAT;
        p->continuous_pending=0;finish(p,now,reason);return 0;
    }
    if(!ng2_beat_model_valid(&p->model)){
        if(now-p->sync_ns>=12*SECOND)finish(p,now,NG2_REASON_BEAT);
        return 0;
    }
    if(now<p->model.last_ns||now-p->model.last_ns>FRESH){finish(p,now,NG2_REASON_BEAT);return 0;}
    if(p->s.inputs>=16){finish(p,now,NG2_REASON_LIMIT);return 0;}
    if(!ng2_choose(&p->scene,p->s.x,p->s.y,p->visits,NG2_VISIT_COUNT,&p->entrance,&choice)){
        finish(p,now,choice.reason==2?NG2_REASON_PARTIAL_GOODS:NG2_REASON_NO_PATH);return 0;}
    if(p->have_anchor&&!p->s.lead_confirmed&&(!same_gold(&p->retune_anchor,&p->scene)||choice.direction!=p->retune_direction
        ||!safe_floor(&p->scene,choice.direction))){finish(p,now,NG2_REASON_MOVEMENT);return 0;}
    if(p->replan_pending){
        uint64_t aligned;
        if(p->s.inputs||p->s.moves||p->s.lead_confirmed||choice.direction!=p->initial_ticket.direction
            ||!safe_floor(&p->scene,choice.direction)||now>p->initial_ticket.deadline_ns
            ||!corrected(p,p->initial_ticket.target_ns,p->initial_period,&aligned)){
            p->replan_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        p->s.next_target_ns=p->initial_ticket.target_ns;
    }else if(p->continuous_pending){
        uint64_t aligned;
        if(!same_continuous_action(&choice,&p->command_choice)||!safe_floor(&p->scene,choice.direction)
            ||!corrected(p,p->continuous_ticket.target_ns,p->continuous_period,&aligned)){
            p->continuous_pending=0;finish(p,now,NG2_REASON_SCREEN);return 0;
        }
        p->s.next_target_ns=p->continuous_ticket.target_ns;
    }else if(p->s.lead_confirmed){
        if(!p->s.next_target_ns||now>p->next_deadline){finish(p,now,NG2_REASON_LATE);return 0;}
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
    if(!reason&&now-p->s.started_ns>=180*SECOND)reason=NG2_REASON_SESSION;
    if(!reason&&p->command.kind==NG2_ACTION_MOVE&&(p->s.inputs>=16||now-p->s.walk_started_ns>=45*SECOND))reason=NG2_REASON_LIMIT;
    if(reason){not_sent(p,now,reason);if(reason==NG2_REASON_FOREGROUND||reason==NG2_REASON_LOCKED||reason==NG2_REASON_OWNER_PAUSED)terminal(p,now,reason);
        else {finish(p,now,reason);}
        return 0;}
    p->last_now=maximum(p->last_now,now);p->s.input_state=2;e=event(p);e->begin_ns=now;e->outcome=1;
    return 1;
}
int ng2_controller_complete(NG2Controller *p,uint64_t id,uint64_t now,int32_t outcome){
    NG2ControllerEvent *e;
    if(!p||!valid_time(now)||id!=p->command.id||outcome < -1||outcome>1||p->s.terminal)return 0;
    e=event(p);
    p->last_now=maximum(p->last_now,now);
    if(outcome==0&&(p->s.input_state==1||p->s.input_state==2)){
        e->outcome=3;e->end_ns=now;e->reason=NG2_REASON_CAPTURE;
        p->s.input_state=0;p->s.current_command_id=0;finish(p,now,NG2_REASON_CAPTURE);return 1;}
    if(p->s.input_state!=2||now<e->begin_ns)return 0;
    e->end_ns=now;
    if(p->command.kind==NG2_ACTION_MOVE)++p->s.inputs;
    if(outcome==-1){e->outcome=4;e->reason=NG2_REASON_UNKNOWN_INPUT;p->s.input_state=4;terminal(p,now,NG2_REASON_UNKNOWN_INPUT);return 1;}
    e->outcome=2;p->ack_ns=now;p->transition_ns=now;p->s.last_completed_id=id;p->s.input_state=3;
    if(p->command.kind==NG2_ACTION_MOVE)p->motion_wait.active=1;
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
const char *ng2_reason_name(int32_t reason){
    static const char *const names[]={"none","goods","cancelled","foreground","locked","owner_paused","capture",
        "stale","beat","late","movement","unknown_input","no_path","partial_goods",
        "limit","session","restart","screen","generation","heartbeat","geometry"};
    return reason>=0&&reason<=NG2_REASON_GEOMETRY?names[reason]:"unknown";
}
