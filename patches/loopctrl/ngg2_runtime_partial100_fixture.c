/* This HOST TU includes the exact selected old/current Controller source.
 * Only historical preconditions are seeded once before A's first observe;
 * job/source/budget/credit/rebinding and all later outputs remain production C.
 * Scene production below is procedural, not Perception or device evidence. */
#define ng2_controller_observe_at ng2_partial100_observe_real
#include "NG2Controller.c"
#undef ng2_controller_observe_at
#include "ngg2_runtime_partial100_fixture.h"
#include <pthread.h>

static pthread_mutex_t partial100_gate=PTHREAD_MUTEX_INITIALIZER;
static NG2Partial100Proof partial100_proof;
static uint64_t partial100_a_prefix;
static uint64_t partial100_hash(const uint8_t *p,size_t n){
    uint64_t h=UINT64_C(14695981039346656037);size_t i;
    for(i=0;i<n;++i){h^=p[i];h*=UINT64_C(1099511628211);}return h;
}
void ng2_partial100_reset(void){
    pthread_mutex_lock(&partial100_gate);memset(&partial100_proof,0,sizeof(partial100_proof));
    partial100_a_prefix=0;pthread_mutex_unlock(&partial100_gate);
}
void ng2_partial100_proof(NG2Partial100Proof *out){
    pthread_mutex_lock(&partial100_gate);if(out)*out=partial100_proof;pthread_mutex_unlock(&partial100_gate);
}
static void partial100_cell(NG2Scene *s,int x,int y,int kind){s->tiles[(y+5)*23+x+11]=(uint8_t)kind;}
static void partial100_cross(NG2Scene *s,int x,int y){
    int d;for(d=0;d<5;++d)s->protected_cells[(y+dy[d]+5)*23+x+dx[d]+11]=1;
}
int ng2_partial100_pixels(uint8_t *out,size_t length,int32_t marker){
    size_t i;if(!out||length!=896u*414u*4u||(marker!=11&&marker!=23&&marker!=31&&marker!=47))return 0;
    for(i=0;i<length;i+=4){out[i]=out[i+1]=out[i+2]=0;out[i+3]=255;}
    out[0]=(uint8_t)marker;out[1]=73;out[2]=119;return 1;
}
void ng2_test_pause(uint8_t *out,size_t length){(void)ng2_partial100_pixels(out,length,11);}
/* The genuine Perception object is retained for Raster orientation/fingerprint,
 * with only its analyze symbol renamed by this HOST checker. */
static int partial100_scene(int marker,NG2Scene *out){
    uint32_t noise=100100u;int i;
    memset(out,0,sizeof(*out));out->abi_version=1;out->struct_size=sizeof(*out);
    if(marker==11){out->state=NG2_PAUSE;out->restart_label=1;return 0;}
    if(marker==23){out->state=NG2_FLOOR;out->gold_state=NG2_GOLD_CLEAR;partial100_cell(out,0,0,NG2_TILE_FLOOR);return 0;}
    if(marker!=31&&marker!=47)return -1;
    out->state=NG2_FLOOR;out->gold_state=NG2_GOLD_CANDIDATE;out->gold_peak=190;out->goods=NG2_GOODS_PARTIAL;
    partial100_cell(out,0,0,NG2_TILE_FLOOR);partial100_cell(out,-1,0,NG2_TILE_FLOOR);
    partial100_cell(out,-1,-1,NG2_TILE_GOLD);partial100_cell(out,-1,1,NG2_TILE_GOLD);
    partial100_cell(out,-2,0,NG2_TILE_FLOOR);partial100_cell(out,-2,-1,NG2_TILE_DIRT);
    partial100_cell(out,-2,1,NG2_TILE_FLOOR);partial100_cell(out,8,3,NG2_TILE_STONE);
    partial100_cell(out,-5,2,NG2_TILE_ITEM);partial100_cross(out,-5,2);
    partial100_cell(out,-6,2,NG2_TILE_FLOOR);partial100_cell(out,-7,2,NG2_TILE_GOLD);
    partial100_cell(out,-8,2,NG2_TILE_FLOOR);
    if(marker==47){partial100_cell(out,-6,2,NG2_TILE_ITEM);partial100_cross(out,-6,2);
        partial100_cell(out,-7,2,NG2_TILE_ITEM);partial100_cross(out,-7,2);}
    for(i=0;i<NG2_SIGNATURE_LENGTH;++i){noise=noise*1664525u+1013904223u;out->signature[i]=(uint8_t)(20+noise%220);}
    return 0;
}
int ng2_analyze_rgba(const uint8_t *raw,size_t length,size_t stride,NG2Scene *out){
    if(!raw||!out||length!=896u*414u*4u||stride!=896u*4u)return -1;
    return partial100_scene(raw[0],out);
}
uint64_t ng2_partial100_expected_scene_hash(int32_t marker){
    NG2Scene *scene=(NG2Scene *)malloc(sizeof(*scene));uint64_t hash=0;
    if(scene){if(!partial100_scene(marker,scene))hash=partial100_hash((const uint8_t *)scene,sizeof(*scene));free(scene);}return hash;
}
int ng2_controller_observe_at(NG2Controller *p,const NG2Scene *scene,uint64_t id,
    uint64_t start,uint64_t end,uint64_t prefix,int32_t stable,uint64_t commit){
    NG2ControllerCycleStatus before,after;int result,first_a=0;
    if(!p)return ng2_partial100_observe_real(p,scene,id,start,end,prefix,stable,commit);
    ng2_controller_cycle_status(p,&before);
    if(!partial100_proof.seed_count&&scene&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_PARTIAL
        &&before.job_id==0&&stable&&prefix&&prefix==p->s.last_completed_id&&!p->s.input_state&&p->event_count){
        NG2ControllerEvent *e=&p->events[p->event_count-1];
        /* Explicit synthetic prehistory at the real RESUME prefix. This is
         * NOT evidence that Runtime performed prior walking or opened a door. */
        p->s.inputs=2;p->s.moves=1;p->s.lead_confirmed=1;p->s.door_changes=1;
        e->command.id=prefix;e->command.kind=NG2_ACTION_MOVE;e->command.direction=NG2_LEFT;
        e->outcome=2;e->motion=NG2_DOOR_OPENED;e->dx=e->dy=0;
        pthread_mutex_lock(&partial100_gate);partial100_proof.seed_count=1;
        partial100_proof.prefix=prefix;pthread_mutex_unlock(&partial100_gate);first_a=1;
    }
    result=ng2_partial100_observe_real(p,scene,id,start,end,prefix,stable,commit);
    ng2_controller_cycle_status(p,&after);
    pthread_mutex_lock(&partial100_gate);
    if(scene&&scene->state==NG2_FLOOR&&scene->goods==NG2_GOODS_UNKNOWN&&stable&&prefix
        &&prefix==p->s.last_completed_id&&!p->s.input_state&&!after.job_id)partial100_proof.ready_for_a=1;
    if(first_a){partial100_proof.a_capture=after.capture_id;partial100_a_prefix=after.prefix;}
    if(scene&&tile(scene,-7,2)==NG2_TILE_ITEM&&before.job_id==1&&before.state==NG2_CYCLE_ASSESS)
        partial100_proof.b_while_assessing=1;
    if(scene&&tile(scene,-7,2)==NG2_TILE_ITEM&&before.state==NG2_CYCLE_OBSERVE_MORE
        &&start>=before.release_after_ns&&!partial100_proof.compared_b){
        NG2ControllerCycleStatus saved;NG2ControllerStatus status_before,status_after;NG2RingResult stale;
        partial100_proof.compared_b=1;partial100_proof.b_capture=id;
        partial100_proof.job_before=before.job_id;partial100_proof.job_after=after.job_id;
        partial100_proof.capture_after=after.capture_id;partial100_proof.pending_after=after.pending;
        partial100_proof.state_after=after.state;partial100_proof.horizon_before=before.continuation_deadline_ns;
        partial100_proof.horizon_after=after.continuation_deadline_ns;
        if(after.job_id==2&&after.pending){
            saved=after;ng2_controller_status(p,&status_before);memset(&stale,0,sizeof(stale));
            stale.abi=NG2_RING_ABI;stale.size=sizeof(stale);stale.selected_row=stale.selected_partial=-1;
            stale.started_ns=stale.finished_ns=commit;
            partial100_proof.stale_worker_rejected=!ng2_controller_cycle_worker_begin(p,1,partial100_proof.a_capture,partial100_a_prefix,commit);
            partial100_proof.stale_result_rejected=!ng2_controller_cycle_assess(p,1,partial100_proof.a_capture,partial100_a_prefix,commit,&stale);
            ng2_controller_cycle_status(p,&after);ng2_controller_status(p,&status_after);
            partial100_proof.stale_result_rejected&=!memcmp(&saved,&after,sizeof(after))&&!memcmp(&status_before,&status_after,sizeof(status_after));
        }
    }
    pthread_mutex_unlock(&partial100_gate);return result;
}
int ng2_ring_assess_rgba_real(const uint8_t *,size_t,size_t,const NG2RingOptions *,NG2RingResult *);
int ng2_ring_assess_rgba(const uint8_t *raw,size_t length,size_t stride,const NG2RingOptions *options,NG2RingResult *out){
    int slot,i;
    pthread_mutex_lock(&partial100_gate);slot=partial100_proof.ring_calls++;
    if(slot<2){partial100_proof.raw_hash[slot]=partial100_hash(raw,length);partial100_proof.marker[slot]=raw[0];
        partial100_proof.mode[slot]=options?options->mode:-1;
        if(options&&options->scene){partial100_proof.scene_hash[slot]=partial100_hash((const uint8_t *)options->scene,sizeof(*options->scene));
            partial100_proof.scene_address[slot]=(uint64_t)(uintptr_t)options->scene;}
        if(options&&options->scene)for(i=0;i<NG2_TILE_COUNT;++i){
            partial100_proof.items[slot]+=options->scene->tiles[i]==NG2_TILE_ITEM;
            partial100_proof.protected_count[slot]+=options->scene->protected_cells[i]!=0;}}
    pthread_mutex_unlock(&partial100_gate);
    return ng2_ring_assess_rgba_real(raw,length,stride,options,out);
}
void ng2_partial100_result(uint64_t job,uint64_t started,uint64_t finished,NG2RingResult *out){
    memset(out,0,sizeof(*out));out->abi=NG2_RING_ABI;out->size=sizeof(*out);
    out->started_ns=started;out->finished_ns=finished;out->selected_row=out->selected_partial=-1;
    out->coverage=NG2_RING_COVERAGE_INCOMPLETE;out->partial_count=1;
    if(job==1){out->partial_safe_no_positive=1;out->partial[0].icon_score=out->partial[0].icon_upper_bound=.1;
        out->partial[0].icon_score_exact=1;}
    else{out->outcome=NG2_RING_CANDIDATE;out->selected_partial=0;out->partial[0].outcome=NG2_RING_CANDIDATE;
        out->partial[0].icon_score=out->partial[0].icon_upper_bound=.9;out->partial[0].icon_score_exact=1;}
}
