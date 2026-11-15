/* HOST-only component seam. Exact old/current Controller is included below.
 * The ordinary Runtime creates IDs1/2/3 by RESUME/PAUSE/RESTART first. Before
 * source A, only declared historical ACK/lead/HUD preconditions are seeded.
 * Every new framing mode/job/ticket/result and displacement is production C. */
#define ng2_controller_observe_at ng2_framing101_observe_real
#define ng2_controller_complete ng2_framing101_complete_real
#define ng2_controller_tick ng2_framing101_tick_real
#include "NG2Controller.c"
#undef ng2_controller_observe_at
#undef ng2_controller_complete
#undef ng2_controller_tick
#include "ngg2_runtime_framing101_fixture.h"
#include <pthread.h>

static pthread_mutex_t framing101_gate=PTHREAD_MUTEX_INITIALIZER;
static NG2Framing101Proof framing101_value;
static uint64_t framing101_now,framing101_epoch,framing101_a_prefix;
static uint64_t framing101_hash(const uint8_t *p,size_t n){
    uint64_t h=UINT64_C(14695981039346656037);size_t i;
    for(i=0;i<n;++i){h^=p[i];h*=UINT64_C(1099511628211);}return h;
}
void ng2_framing101_reset(void){
    pthread_mutex_lock(&framing101_gate);memset(&framing101_value,0,sizeof(framing101_value));
    framing101_now=framing101_epoch=framing101_a_prefix=0;pthread_mutex_unlock(&framing101_gate);
}
void ng2_framing101_proof(NG2Framing101Proof *out){
    pthread_mutex_lock(&framing101_gate);if(out)*out=framing101_value;pthread_mutex_unlock(&framing101_gate);
}
void ng2_framing101_clock(uint64_t now){
    pthread_mutex_lock(&framing101_gate);framing101_now=now;pthread_mutex_unlock(&framing101_gate);
}
int ng2_framing101_pixels(uint8_t *out,size_t length,int32_t marker){
    size_t i;if(!out||length!=896u*414u*4u||(marker!=11&&marker!=23&&marker!=24&&marker!=31&&marker!=47&&marker!=61))return 0;
    for(i=0;i<length;i+=4){out[i]=out[i+1]=out[i+2]=0;out[i+3]=255;}
    out[0]=(uint8_t)marker;out[1]=101;out[2]=173;return 1;
}
void ng2_test_pause(uint8_t *out,size_t length){(void)ng2_framing101_pixels(out,length,11);}
static double framing101_q(uint64_t at,uint64_t epoch){
    uint64_t period=UINT64_C(520000000),r=at>=epoch?(period-(at-epoch)%period)%period:(epoch-at)%period;
    return (double)r/(double)period;
}
static void framing101_cell(NG2Scene *s,int x,int y,int kind){
    if(x>=-11&&x<=11&&y>=-5&&y<=4)s->tiles[(y+5)*23+x+11]=(uint8_t)kind;
}
/* Synthetic Scene producer replaces only analyze_rgba in this host binary.
 * Original Perception stays linked (renamed analyze) for Raster/fingerprint. */
int ng2_analyze_rgba(const uint8_t *raw,size_t length,size_t stride,NG2Scene *out){
    uint32_t noise=101101u;uint64_t at,epoch;int marker,i,x,y,moved;
    if(!raw||!out||length!=896u*414u*4u||stride!=896u*4u)return -1;
    marker=raw[0];memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
    if(marker==11){out->state=NG2_PAUSE;out->restart_label=1;return 0;}
    if(marker!=23&&marker!=24&&marker!=31&&marker!=47&&marker!=61)return -1;
    pthread_mutex_lock(&framing101_gate);at=framing101_now;epoch=framing101_epoch;pthread_mutex_unlock(&framing101_gate);
    out->state=NG2_FLOOR;out->beat_valid=1;out->beat_spacing=104;out->beat_center=446;
    out->beat_remaining=framing101_q(at,epoch);
    if(marker==23||marker==24){out->gold_state=NG2_GOLD_CLEAR;framing101_cell(out,0,0,NG2_TILE_FLOOR);
        memset(out->fingerprint,marker==23?20:80,sizeof(out->fingerprint));return 0;}
    out->gold_state=NG2_GOLD_CANDIDATE;out->gold_peak=190;out->goods=NG2_GOODS_VISIBLE;moved=marker==47;
    for(y=-4;y<=0;++y)for(x=-5;x<0;++x)framing101_cell(out,x+moved,y,NG2_TILE_FLOOR);
    for(y=-5;y<=1;++y)framing101_cell(out,-6+moved,y,NG2_TILE_GOLD);
    for(x=-6;x<=0;++x)framing101_cell(out,x+moved,1,NG2_TILE_GOLD);
    framing101_cell(out,moved,-1,NG2_TILE_GOLD);framing101_cell(out,moved,0,NG2_TILE_FLOOR);
    framing101_cell(out,-1+moved,-2,NG2_TILE_UNKNOWN);
    for(x=-4;x<=-2;++x){int d;framing101_cell(out,x+moved,-2,NG2_TILE_ITEM);
        for(d=0;d<5;++d)out->protected_cells[(-2+dy[d]+5)*23+x+moved+dx[d]+11]=1;}
    for(y=0;y<104;++y)for(x=0;x<224;++x){
        noise=noise*1664525u+1013904223u;i=y*224+x;
        if(marker==61)out->signature[i]=80;
        else if(!moved)out->signature[i]=(uint8_t)(20+noise%220);
        else if(x+9<224)out->signature[y*224+x+9]=(uint8_t)(20+noise%220);
    }
    return 0;
}
static int framing101_history(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start){
    static const uint64_t offsets[5]={0,390000000,780000000,1170000000,2080000000};
    NG2BeatSample samples[5];NG2BeatModel model;NG2ControllerEvent *opened,*latest;uint64_t first;int k;
    if(!p||p->event_count<3||p->s.last_completed_id!=3||p->s.input_state||start<2080000002u)return 1;
    opened=&p->events[p->event_count-2];latest=&p->events[p->event_count-1];
    if(opened->command.id!=2||latest->command.id!=3||opened->outcome!=2||latest->outcome!=2
        ||!opened->begin_ns||!opened->end_ns||!latest->begin_ns||!latest->end_ns
        ||opened->end_ns>latest->begin_ns||latest->end_ns>start||!opened->observed_capture_id
        ||opened->observed_capture_id>latest->command.source_capture_id)return 2;
    first=start-2080000002u;if(first<p->s.started_ns)return 3;
    for(k=0;k<5;++k){uint64_t a=first+offsets[k];
        if(!ng2_make_sample(framing101_q(a+1,framing101_epoch),104,446,a,a+2,&samples[k]))return 4;}
    if(!ng2_beat_fit(samples,5,&model)||!ng2_beat_model_valid(&model))return 5;
    /* Declared historical model, counts and ordered ACK contents only. The
     * samples are public-fit, run-contained and older than source A. No cycle
     * field, source/anchor, new target, permission, or horizon is assigned. */
    p->model=model;memcpy(p->samples,samples,sizeof(samples));p->sample_count=5;
    p->s.beat_period_ns=model.period_ns;p->model_capture_id=p->s.last_capture_id;
    p->s.walk_started_ns=p->sync_ns=first;p->latest_verified_ns=opened->end_ns;
    p->s.inputs=3;p->s.moves=1;p->s.door_changes=1;p->s.lead_confirmed=1;p->s.last_ordinal=3;
    opened->command.kind=latest->command.kind=NG2_ACTION_MOVE;
    opened->command.direction=latest->command.direction=NG2_LEFT;
    opened->command.ordinal=2;latest->command.ordinal=3;
    opened->motion=NG2_DOOR_OPENED;latest->motion=NG2_MOTION_UNKNOWN;
    opened->dx=opened->dy=latest->dx=latest->dy=0;latest->observed_capture_id=id;
    p->command=latest->command;
    (void)scene;return 0;
}
int ng2_controller_observe_at(NG2Controller *p,const NG2Scene *scene,uint64_t id,uint64_t start,
    uint64_t end,uint64_t prefix,int32_t stable,uint64_t commit){
    NG2ControllerCycleStatus before,after;int result,seed=0,error=0;
    if(!p)return ng2_framing101_observe_real(p,scene,id,start,end,prefix,stable,commit);
    pthread_mutex_lock(&framing101_gate);
    if(!framing101_epoch)framing101_epoch=p->s.started_ns+UINT64_C(5000000000);
    pthread_mutex_unlock(&framing101_gate);
    ng2_controller_cycle_status(p,&before);
    if(!framing101_value.seed_count&&!framing101_value.seed_error&&scene&&scene->goods==NG2_GOODS_VISIBLE
        &&!before.job_id&&stable&&prefix==3&&p->s.last_completed_id==3&&!p->s.input_state){
        error=framing101_history(p,scene,id,start);seed=!error;
        pthread_mutex_lock(&framing101_gate);framing101_value.seed_error=error;
        if(seed){framing101_value.seed_count=1;framing101_value.fit_ok=1;framing101_value.prefix=prefix;
            framing101_value.before_inputs=p->s.inputs;framing101_value.before_moves=p->s.moves;
            framing101_value.before_restarts=p->s.restarts;}
        pthread_mutex_unlock(&framing101_gate);
    }
    result=ng2_framing101_observe_real(p,scene,id,start,end,prefix,stable,commit);
    ng2_controller_cycle_status(p,&after);
    pthread_mutex_lock(&framing101_gate);
    if(scene&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_UNKNOWN&&stable&&prefix==3&&!p->s.input_state&&!after.job_id)
        framing101_value.ready_for_a=1;
    if(seed){framing101_value.a_capture=after.capture_id;framing101_a_prefix=after.prefix;framing101_value.old_horizon=after.continuation_deadline_ns;}
    if(before.job_id==1&&before.state==NG2_CYCLE_OBSERVE_MORE&&scene&&scene->goods==NG2_GOODS_VISIBLE
        &&id>before.capture_id&&start>=before.release_after_ns&&after.job_id==1&&!p->s.input_state)
        framing101_value.static_capture=id;
    if(framing101_value.move_id&&p->s.input_state==3&&p->command.id==framing101_value.move_id
        &&p->motion_wait.attempts&&p->motion_wait.last_motion==NG2_MOTION_UNKNOWN){
        framing101_value.unknown_seen=1;framing101_value.ack_moves=p->s.moves;framing101_value.ack_job=(int32_t)after.job_id;}
    if(after.job_id==2&&after.pending&&!framing101_value.job_after){
        NG2ControllerCycleStatus saved=after;NG2ControllerStatus a,b;NG2RingResult stale;int w,r,t;
        framing101_value.job_after=2;framing101_value.moved_capture=id;framing101_value.job2_capture=after.capture_id;
        framing101_value.moved_moves=p->s.moves;framing101_value.new_horizon=after.continuation_deadline_ns;
        framing101_value.bound_scene_hash=framing101_hash((const uint8_t *)scene,sizeof(*scene));
        ng2_controller_status(p,&a);memset(&stale,0,sizeof(stale));stale.abi=1;stale.size=sizeof(stale);
        stale.selected_row=stale.selected_partial=-1;stale.started_ns=stale.finished_ns=commit;
        w=ng2_controller_cycle_worker_begin(p,1,framing101_value.a_capture,framing101_a_prefix,commit);
        r=ng2_controller_cycle_assess(p,1,framing101_value.a_capture,framing101_a_prefix,commit,&stale);
        t=ng2_controller_begin(p,3,commit,1,0,1);
        ng2_controller_cycle_status(p,&after);ng2_controller_status(p,&b);
        framing101_value.old_job_rejected=!w&&!r&&!memcmp(&saved,&after,sizeof(after))&&!memcmp(&a,&b,sizeof(a));
        framing101_value.old_ticket_rejected=!t;
    }
    pthread_mutex_unlock(&framing101_gate);return result;
}
int ng2_controller_tick(NG2Controller *p,uint64_t now,int32_t front,int32_t locked,int32_t owner,NG2Command *out){
    int result=ng2_framing101_tick_real(p,now,front,locked,owner,out);
    if(result==1&&out&&out->kind==NG2_ACTION_MOVE){
        NG2ControllerCycleStatus cycle;ng2_controller_cycle_status(p,&cycle);
        pthread_mutex_lock(&framing101_gate);framing101_value.move_id=out->id;framing101_value.move_ordinal=out->ordinal;
        framing101_value.move_source=out->source_capture_id;framing101_value.target_ns=out->target_ns;
        framing101_value.not_before_ns=out->not_before_ns;framing101_value.deadline_ns=out->deadline_ns;
        framing101_value.lead_ns=p->s.lead_ns;framing101_value.completed_before=cycle.completed_shops;
        pthread_mutex_unlock(&framing101_gate);
    }
    return result;
}
int ng2_controller_complete(NG2Controller *p,uint64_t id,uint64_t now,int32_t outcome){
    int result=ng2_framing101_complete_real(p,id,now,outcome);
    if(p&&id==framing101_value.move_id&&outcome==2){
        pthread_mutex_lock(&framing101_gate);framing101_value.ack_prefix=p->s.last_completed_id;
        framing101_value.ack_moves=p->s.moves;framing101_value.ack_job=(int32_t)p->cycle.job_id;
        pthread_mutex_unlock(&framing101_gate);
    }
    return result;
}
int ng2_ring_assess_rgba_real(const uint8_t *,size_t,size_t,const NG2RingOptions *,NG2RingResult *);
int ng2_ring_assess_rgba(const uint8_t *raw,size_t length,size_t stride,const NG2RingOptions *options,NG2RingResult *out){
    int slot;pthread_mutex_lock(&framing101_gate);slot=framing101_value.ring_calls++;
    if(slot<2){framing101_value.marker[slot]=raw[0];framing101_value.raw_hash[slot]=framing101_hash(raw,length);
        framing101_value.mode[slot]=options?options->mode:-1;
        if(options&&options->scene)framing101_value.scene_hash[slot]=framing101_hash((const uint8_t *)options->scene,sizeof(*options->scene));}
    pthread_mutex_unlock(&framing101_gate);return ng2_ring_assess_rgba_real(raw,length,stride,options,out);
}
void ng2_framing101_result(uint64_t job,uint64_t started,uint64_t finished,NG2RingResult *out){
    int i;NG2RingRow *row;
    memset(out,0,sizeof(*out));out->abi=1;out->size=sizeof(*out);out->started_ns=started;out->finished_ns=finished;
    out->selected_row=out->selected_partial=-1;out->coverage=NG2_RING_COVERAGE_INCOMPLETE;
    if(job!=1){out->outcome=NG2_RING_CANDIDATE;return;}
    out->row_count=1;out->selected_row=0;out->partial_count=2;out->certificate.failure_flags=258;
    out->certificate.scene_state=NG2_FLOOR;out->certificate.scene_goods=NG2_GOODS_VISIBLE;
    out->certificate.row[0]=304;out->certificate.row[1]=81;
    row=&out->rows[0];row->left=304;row->sy=81;row->word_slot=-1;
    for(i=0;i<5;++i){NG2RingSlot *slot=i<3?&row->slots[i]:&out->partial[i-3];
        slot->cx=i<3?304+36*i:232+36*(i-3);slot->sy=81;slot->slot=i<3?i:0;
        slot->icon_score=slot->icon_upper_bound=.1;}
}
