/* TEST118 physical upper-side shop. Public procedural pixels only. */
#include "ngg2_runtime_scene_fixtures.h"
#include "runtime118_shop_pixels.h"
#include <math.h>
#include <stdlib.h>

static void pixel118(uint8_t *out,int x,int y,int r,int g,int b){
    size_t at;if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;
    out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}

int ng2_fixture_upper118_rgba(uint8_t *out,size_t length,int32_t px,int32_t py,
                            int32_t opened,double q){
    static const int hud[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    uint8_t world[1089]={0},unknown[1089]={0},*ui;
    int x,y,column=0,row=0;size_t i;
    if(!out||length!=896u*414u*4u||px < -3||px>2||py<0||py>3
        ||(opened!=0&&opened!=1)||!isfinite(q)||q<0||q>=1)return 0;
    for(y=-1;y<=5;++y)for(x=-6;x<=0;++x)world[(y+16)*33+x+16]=1;
    world[16*33+17]=world[16*33+18]=1; /* observed outside lead-in */
    for(x=-7;x<=-1;++x)world[15*33+x+16]=2;
    for(y=-1;y<=2;++y)world[(y+16)*33-7+16]=2;
    world[17*33-1+16]=2;
    world[16*33-1+16]=(uint8_t)(opened?1:7);
    /* Independent, static registration anchors for the real Motion matcher. */
    world[13*33-8+16]=3;world[18*33+5+16]=3;world[19*33+8+16]=3;
    ui=(uint8_t*)malloc(length);if(!ui)return 0;
    if(!ng2_fixture_shop_rgba(ui,length,0,0,q,unknown,sizeof(unknown),16,16,1,0)
        ||!ng2_fixture_shop_rgba(out,length,px,py,q,world,sizeof(world),16,16,1,0)){
        free(ui);return 0;
    }
    if(opened)for(i=0;i<sizeof(ng2_shop118_upper)/sizeof(*ng2_shop118_upper);++i){
        int j;const NG2Shop118Run *run=&ng2_shop118_upper[i];
        for(j=0;j<run->count;++j){
            pixel118(out,177-36*px+column,264-36*py+row,run->r,run->g,run->b);
            if(++column==253){column=0;++row;}
        }
    }
    /* The renderer's visibility edge is actor-relative and fixed. Movement
     * translates the same physical three offers above it; no C state chooses
     * whether a price or candidate is visible. */
    for(y=334;y<414;++y)for(x=0;x<896;++x)pixel118(out,x,y,0,0,0);
    for(i=0;i<sizeof(hud)/sizeof(*hud);++i)
        for(y=hud[i][1];y<hud[i][3];++y)for(x=hud[i][0];x<hud[i][2];++x){
            size_t at=((size_t)y*896+x)*4;
            pixel118(out,x,y,ui[at],ui[at+1],ui[at+2]);
        }
    for(i=0;i<length;i+=4)if(ui[i]||ui[i+1]||ui[i+2]){
        out[i]=ui[i];out[i+1]=ui[i+1];out[i+2]=ui[i+2];out[i+3]=255;
    }
    free(ui);return 1;
}

/* Independent approach corridor. It contains no shop glyph or candidate
 * item. Each actual LEFT gesture shifts this same world by exactly one tile. */
int ng2_fixture_walk118_rgba(uint8_t *out,size_t length,int32_t px,double q){
    uint8_t world[1089]={0};int x,y;
    if(px>0||px < -3)return 0;
    for(y=-2;y<=2;++y)for(x=-7;x<=2;++x)world[(y+16)*33+x+16]=1;
    for(y=-2;y<=2;++y)world[(y+16)*33-8+16]=2;
    world[14*33-7+16]=3;world[18*33+3+16]=3;
    return ng2_fixture_shop_rgba(out,length,px,0,q,world,sizeof(world),16,16,1,0);
}

#ifdef NG2_RUNTIME118_TIMING_BRIDGE
/* HOST only: return the actual tick result unchanged, then charge its measured
 * native computation to the procedural clock before Swift sees the ticket.
 * A clock-quantized zero for an empty tick remains zero in the host ledger. */
#include "ngg2/NG2Controller.h"
#include <time.h>
typedef void (*NG2Tick118Callback)(void *,uint64_t);
static NG2Tick118Callback tick118_callback;
static void *tick118_context;
/* DATA only: one exact observation request. Neither a Controller pointer nor
 * a pointer to either stack snapshot survives this synchronous wrapper. */
typedef void (*NG2Data118SnapshotCallback)(void *,uint64_t,uint64_t,uint64_t,uint64_t,
    uint64_t,int32_t,const NG2ControllerStatus *,const NG2ControllerCycleStatus *);
static NG2Data118SnapshotCallback data118_callback;
static void *data118_context;
static uint64_t data118_request[5],data118_expected[9];
static int data118_armed,data118_consumed;
void ng2_fixture_data118_install(NG2Data118SnapshotCallback callback,void *context){
    data118_callback=callback;data118_context=context;
    data118_armed=0;data118_consumed=0;
}
int ng2_fixture_data118_request(uint64_t id,uint64_t start,uint64_t end,uint64_t prefix,
    uint64_t root_started,const uint64_t *expected,size_t count){
    size_t i;
    if(!data118_callback||data118_armed||!id||!start||start>=end||!root_started||!expected||count!=9)return 0;
    for(i=0;i<9;++i)if(!expected[i])return 0;
    data118_request[0]=id;data118_request[1]=start;data118_request[2]=end;
    data118_request[3]=prefix;data118_request[4]=root_started;
    for(i=0;i<9;++i)data118_expected[i]=expected[i];
    data118_armed=1;return 1;
}
void ng2_controller_observe_irregular_at118_actual(NG2Controller *,const NG2Scene *,
    const NG2IrregularObservation *,uint64_t,uint64_t,uint64_t,uint64_t,int32_t,uint64_t);
void ng2_controller_observe_irregular_at(NG2Controller *p,const NG2Scene *scene,
    const NG2IrregularObservation *observation,uint64_t id,uint64_t start,uint64_t end,
    uint64_t prefix,int32_t stable,uint64_t commit){
    ng2_controller_observe_irregular_at118_actual(p,scene,observation,id,start,end,prefix,stable,commit);
    if(!data118_callback||!data118_armed||data118_consumed||id<data118_request[0])return;
    NG2ControllerStatus status={0};NG2ControllerCycleStatus cycle={0};
    uint64_t actual[9];size_t i;int32_t matching;
    NG2Data118SnapshotCallback callback;
    data118_consumed=1;
    ng2_controller_status(p,&status);ng2_controller_cycle_status(p,&cycle);
    actual[0]=cycle.job_id;actual[1]=cycle.capture_id;actual[2]=cycle.capture_start_ns;
    actual[3]=cycle.prefix;actual[4]=cycle.level_id;actual[5]=cycle.worker_started_ns;
    actual[6]=cycle.deadline_ns;actual[7]=cycle.hold_started_ns;actual[8]=cycle.continuation_deadline_ns;
    matching=id==data118_request[0]&&start==data118_request[1]&&end==data118_request[2]
        &&prefix==data118_request[3]&&stable==1&&status.started_ns==data118_request[4]
        &&status.last_capture_id==id&&status.last_capture_start_ns==start
        &&status.last_capture_end_ns==end&&cycle.pending==1;
    for(i=0;i<9;++i)if(actual[i]!=data118_expected[i])matching=0;
    callback=data118_callback;
    /* POD copy only. The original Swift afterObserve charges this wrapper's
     * whole actual duration before the original beforeControlTick release. */
    callback(data118_context,id,start,end,prefix,commit,matching,&status,&cycle);
}
/* Upper-only read-only diagnostics. The original callbacks below keep their
 * existing clock-charging behavior; these extra callbacks never change it. */
typedef void (*NG2Trace118TickCallback)(void *,uint64_t,uint64_t,int32_t,const NG2Command *);
typedef void (*NG2Trace118EpochCallback)(void *,uint64_t,uint64_t,uint64_t,uint64_t);
static NG2Trace118TickCallback trace118_tick;
static NG2Trace118EpochCallback trace118_epoch;
static void *trace118_context;
void ng2_fixture_trace118_install(NG2Trace118TickCallback tick,NG2Trace118EpochCallback epoch,void *context){
    trace118_tick=tick;trace118_epoch=epoch;trace118_context=context;
}
uint64_t ng2_controller_preparation_epoch118_actual(const NG2Controller *,uint64_t,uint64_t);
uint64_t ng2_controller_preparation_epoch(const NG2Controller *p,uint64_t id,uint64_t now){
    struct timespec start,end;uint64_t value,elapsed;
    NG2Trace118EpochCallback callback=trace118_epoch;void *context=trace118_context;
    if(!callback)return ng2_controller_preparation_epoch118_actual(p,id,now);
    clock_gettime(CLOCK_MONOTONIC,&start);
    value=ng2_controller_preparation_epoch118_actual(p,id,now);
    clock_gettime(CLOCK_MONOTONIC,&end);
    elapsed=(uint64_t)(end.tv_sec-start.tv_sec)*UINT64_C(1000000000)
        +(uint64_t)end.tv_nsec-(uint64_t)start.tv_nsec;
    callback(context,id,now,value,elapsed);
    return value;
}
int ng2_controller_tick118_actual(NG2Controller *,uint64_t,int32_t,int32_t,int32_t,NG2Command *);
void ng2_fixture_tick118_install(NG2Tick118Callback cb,void *context){
    tick118_callback=cb;tick118_context=context;
}
int ng2_controller_tick(NG2Controller *p,uint64_t now,int32_t foreground,
    int32_t locked,int32_t owner,NG2Command *out){
    struct timespec start,end;uint64_t elapsed;int result;
    clock_gettime(CLOCK_MONOTONIC,&start);
    result=ng2_controller_tick118_actual(p,now,foreground,locked,owner,out);
    clock_gettime(CLOCK_MONOTONIC,&end);
    elapsed=(uint64_t)(end.tv_sec-start.tv_sec)*UINT64_C(1000000000)
        +(uint64_t)end.tv_nsec-(uint64_t)start.tv_nsec;
    if(tick118_callback)tick118_callback(tick118_context,elapsed);
    if(trace118_tick)trace118_tick(trace118_context,now,elapsed,result,result==1?out:NULL);
    return result;
}
#endif

/* A temporal material change in a distant, observed, unprotected FLOOR.
 * Merchandise, wall support, HUD, physical actor and all other cells stay
 * byte-identical. The Runtime chooses the camera boundary, not a result. */
int ng2_fixture_palette118(uint8_t *out,size_t length){
    int x,y;if(!out||length!=896u*414u*4u)return 0;
    for(y=225;y<261;++y)for(x=538;x<574;++x){
        unsigned value=(unsigned)x*17u+(unsigned)y*13u;
        int noise=(int)(value%9u)-4;
        pixel118(out,x,y,100+noise,50+noise,10+noise);
    }
    return 1;
}
