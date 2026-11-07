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
    uint16_t visits[NG2_VISIT_COUNT];
    uint8_t restart_fingerprint[48];
    uint64_t seen_id,seen_start,seen_end,last_now,transition_ns,sync_ns;
    uint64_t ack_ns,command_period,next_nominal,next_deadline,next_period;
    uint64_t finish_ns;
    size_t sample_count,event_count;
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
    if(!p->s.terminal){p->s.reason=reason;p->s.terminal=1;p->s.phase=NG2_PHASE_DONE;p->s.ended_ns=now;}
}
static void not_sent(NG2Controller *p,uint64_t now,int reason){
    NG2ControllerEvent *e=event(p);
    if(p->s.input_state==1){if(e){e->outcome=3;e->reason=reason;e->end_ns=now;}
        p->s.input_state=0;p->s.current_command_id=0;}
}
static void finish(NG2Controller *p,uint64_t now,int reason){
    if(p->s.terminal)return;
    if(!p->finish_requested){p->finish_requested=1;p->finish_ns=now;p->s.reason=reason;}
    if(reason==NG2_REASON_GOODS){p->s.reason=reason;p->s.goods=1;}
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
        }else if(p->s.lead_confirmed){p->beat_failed=1;return;}
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
    if(!ng2_motion(&p->before,scene,direction,&motion)){motion.kind=NG2_MOTION_UNKNOWN;motion.dx=motion.dy=0;}
    if(motion.kind==NG2_TWEEN)return;
    p->s.input_state=0;p->s.current_command_id=0;
    if(e){e->observed_capture_id=id;e->motion=motion.kind;e->dx=motion.dx;e->dy=motion.dy;}
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
    int pending_kind;
    if(!p)return -1;
    if(p->s.terminal)return 0;
    ++p->s.capture_count;
    if(!id||!valid_time(start)||!valid_time(end)||end<=start||start<p->s.started_ns||(start<p->last_now&&p->last_now-start>FRESH)||id<=p->seen_id
        ||(p->seen_id&&(start<=p->seen_start||end<=p->seen_end))){++p->s.discarded_frames;return 0;}
    p->seen_id=id;p->seen_start=start;p->seen_end=end;
    if(!valid_scene(scene)||stable<0||stable>1){++p->s.discarded_frames;terminal(p,end,NG2_REASON_GEOMETRY);return 0;}
    /* A current goods observation latches before prefix/phase checks. Only a
     * subsequent stable matching prefix may authorize the holding pause. */
    if(scene->goods==NG2_GOODS_VISIBLE){finish(p,end,NG2_REASON_GOODS);p->need_fresh_cleanup=1;}
    if(!stable||prefix!=p->s.last_completed_id||p->s.input_state==2||p->s.input_state==4){
        ++p->s.discarded_frames;return 0;}
    if(p->s.input_state==1&&p->command.kind==NG2_ACTION_MOVE
        &&(scene->state!=p->before.state||scene->goods!=p->before.goods
           ||memcmp(scene->tiles,p->before.tiles,sizeof(scene->tiles))
           ||memcmp(scene->protected_cells,p->before.protected_cells,sizeof(scene->protected_cells)))){
        not_sent(p,end,NG2_REASON_SCREEN);finish(p,end,NG2_REASON_SCREEN);
    }
    p->scene=*scene;p->have_scene=1;p->need_fresh_cleanup=0;
    p->s.paused=scene->state==NG2_PAUSE;
    p->s.last_capture_id=id;p->s.last_capture_start_ns=start;p->s.last_capture_end_ns=end;++p->s.accepted_frames;
    if(!p->s.goods)p->s.goods=scene->goods==NG2_GOODS_VISIBLE;
    if(p->s.input_state==3){
        pending_kind=p->command.kind;
        if(pending_kind==NG2_ACTION_MOVE){
            if(scene->state!=NG2_FLOOR){p->s.input_state=0;p->s.current_command_id=0;finish(p,end,NG2_REASON_SCREEN);}
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
    tail=kind==NG2_ACTION_MOVE?p->s.lead_ns+50000000:50000000;
    horizon=minimum(p->s.last_capture_start_ns+FRESH,p->s.started_ns+180*SECOND);
    if(kind==NG2_ACTION_MOVE){horizon=minimum(horizon,p->model.last_ns+FRESH);
        horizon=minimum(horizon,p->s.walk_started_ns+45*SECOND);}
    /* Preserve the original target-plus-50ms and actual-send-plus-lead-plus-
     * 50ms contract. Tighten the main ticket; never spend a 10ms allowance
     * beyond image, phase, walk, or session validity. */
    if(horizon<tail||p->command.not_before_ns>horizon-tail){finish(p,now,NG2_REASON_STALE);return 0;}
    deadline=kind==NG2_ACTION_MOVE?p->command.not_before_ns+10000000:now+SECOND;
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
    p->before=p->scene;p->command_period=p->model.period_ns;
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
        if(p->command.kind==NG2_ACTION_MOVE&&p->s.lead_confirmed&&now>p->command.target_ns+p->command_period-p->s.lead_ns+10000000){
            terminal(p,now,NG2_REASON_LATE);return 0;}
        if(now>=p->ack_ns&&now-p->ack_ns>=timeout){terminal(p,now,p->command.kind==NG2_ACTION_RESTART?NG2_REASON_RESTART:NG2_REASON_CAPTURE);}
        return 0;
    }
    if(p->finish_requested){
        if(p->have_scene&&p->scene.state==NG2_PAUSE&&fresh(p,now)){p->s.paused=1;terminal(p,now,p->s.reason);return 0;}
        if(!p->final_pause_attempted&&!p->need_fresh_cleanup&&fresh(p,now)&&p->scene.state==NG2_FLOOR){
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
    if(p->s.lead_confirmed){
        if(!p->s.next_target_ns||now>p->next_deadline){finish(p,now,NG2_REASON_LATE);return 0;}
    }else p->s.next_target_ns=ng2_next_target(&p->model,now,p->s.lead_ns);
    if(!p->s.next_target_ns){finish(p,now,NG2_REASON_BEAT);return 0;}
    p->s.phase=NG2_PHASE_WALK;
    return reserve(p,now,NG2_ACTION_MOVE,choice.direction,p->s.next_target_ns,out);
}
int ng2_controller_begin(NG2Controller *p,uint64_t id,uint64_t now,int32_t front,int32_t locked,int32_t owner){
    int reason;NG2ControllerEvent *e;uint64_t tail,horizon;
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
const char *ng2_reason_name(int32_t reason){
    static const char *const names[]={"none","goods","cancelled","foreground","locked","owner_paused","capture",
        "stale","beat","late","movement","unknown_input","no_path","partial_goods",
        "limit","session","restart","screen","generation","heartbeat","geometry"};
    return reason>=0&&reason<=NG2_REASON_GEOMETRY?names[reason]:"unknown";
}
