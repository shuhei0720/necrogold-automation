/* TEST120 Runtime component setup. Public procedural RGBA and lifecycle only. */
#include "ngg2_runtime120_partial_fixture.h"
#include "ngg2_runtime_scene_fixtures.h"
#include "ngg2/NG2Templates.h"
#include "runtime120_partial_pixels.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#define Q120_SIZE (896u*414u*4u)
static void pixel120(uint8_t *out,int x,int y,int r,int g,int b){
    size_t at;if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;
    out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}
int ng2_fixture_queue120_rgba(uint8_t *out,size_t length,int32_t kind,
                             int32_t candidate,double q){
    uint8_t world[1089]={0},*ui;int x,y,px=kind==NG2_QUEUE120_INITIAL?2:1;
    size_t i;int column=0,row=0;
    if(!out||length!=Q120_SIZE||kind<0||kind>7||candidate!=0
       ||!isfinite(q)||q<0||q>=1)return 0;
    (void)&ng2_template_icon;(void)&ng2_template_footer;(void)&ng2_template_zone_one;
    (void)&ng2_template_floor_one;(void)&ng2_template_death;
    if(kind==NG2_QUEUE120_PAUSE){
        const NG2Template *templates[2]={&ng2_template_continue,&ng2_template_restart};
        memset(out,0,length);for(i=3;i<length;i+=4)out[i]=255;
        for(int n=0;n<2;++n){const NG2Template *t=templates[n];
            for(y=0;y<t->h;++y)for(x=0;x<t->w;++x)
                if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1)
                    pixel120(out,t->x+x,t->y+y,180,180,180);
        }
        return 1;
    }
    for(y=-4;y<=0;++y)for(x=-5;x<=2;++x)world[(y+16)*33+x+16]=1;
    for(y=-5;y<=1;++y)world[(y+16)*33-6+16]=2;
    for(x=-6;x<=0;++x)world[17*33+x+16]=2;
    world[17*33-5+16]=4;
    world[15*33+16]=2;
    world[16*33+16]=(uint8_t)(kind==NG2_QUEUE120_INITIAL||kind==NG2_QUEUE120_GATE?7:1);
    world[11*33-6+16]=4;
    world[13*33+2+16]=(uint8_t)(kind==NG2_QUEUE120_WALL?4:1);
    world[12*33-6+16]=4;
    world[19*33+7+16]=4;
    world[13*33-8+16]=3;world[18*33+5+16]=3;world[20*33+8+16]=3;
    if(!ng2_fixture_shop_rgba(out,length,px,0,q,world,sizeof(world),16,16,1,0))return 0;
    {
        const NG2Partial120PixelRun *runs=ng2_partial120_partial;
        size_t count=sizeof(ng2_partial120_partial)/sizeof(*runs);
        for(i=0;i<count;++i)for(int j=0;j<runs[i].count;++j){
            if(column<181)pixel120(out,214-36*px+column,196+row,runs[i].r,runs[i].g,runs[i].b);
            if(++column==253){column=0;++row;}
        }
        if(kind==NG2_QUEUE120_INITIAL||kind==NG2_QUEUE120_BEFORE||kind==NG2_QUEUE120_OPENED||kind==NG2_QUEUE120_GATE)
            for(y=211;y<251;++y)for(x=286-36*px;x<322-36*px;++x)
                pixel120(out,x,y,27,17,15);
    }
    /* UI templates/HUD remain independent from world camera texture. */
    ui=(uint8_t*)malloc(length);if(!ui)return 0;
    memset(world,0,sizeof(world));
    if(!ng2_fixture_shop_rgba(ui,length,0,0,q,world,sizeof(world),16,16,1,0)){
        free(ui);return 0;
    }
    for(i=0;i<length;i+=4)if(ui[i]||ui[i+1]||ui[i+2]){
        out[i]=ui[i];out[i+1]=ui[i+1];out[i+2]=ui[i+2];out[i+3]=255;
    }
    free(ui);return 1;
}

uint64_t ng2_partial120_now(void){
#ifdef __APPLE__
    static mach_timebase_info_data_t scale;
    if(!scale.denom)mach_timebase_info(&scale);
    return (uint64_t)(((__uint128_t)mach_absolute_time()*scale.numer)/scale.denom);
#else
    struct timespec value;clock_gettime(CLOCK_MONOTONIC,&value);
    return (uint64_t)value.tv_sec*UINT64_C(1000000000)+(uint64_t)value.tv_nsec;
#endif
}
static NG2Partial120Counts counts120;
static int target120;
void ng2_partial120_select(uint64_t command){memset(&counts120,0,sizeof(counts120));counts120.command_id=command;}
void ng2_partial120_arm_target(void){ng2_partial120_select(0);target120=1;}
void ng2_partial120_counts(NG2Partial120Counts *out){if(out)*out=counts120;}
/* Compile-time call routing only: every real computation runs once. */
int ng2_runtime120_motion(const NG2Scene *a,const NG2Scene *b,int32_t d,NG2Motion *out){
    uint64_t start=ng2_partial120_now();++counts120.motion_calls;
    int answer=ng2_motion(a,b,d,out);counts120.motion_ns+=ng2_partial120_now()-start;
    counts120.motion_kind=out->kind;counts120.motion_dx=out->dx;counts120.motion_dy=out->dy;return answer;
}
extern int ng2_runtime120_real_tick(NG2Controller *,uint64_t,int32_t,int32_t,int32_t,NG2Command *);
extern int ng2_runtime120_real_begin(NG2Controller *,uint64_t,uint64_t,int32_t,int32_t,int32_t);
extern int ng2_runtime120_real_complete(NG2Controller *,uint64_t,uint64_t,int32_t);
extern uint64_t ng2_runtime120_real_epoch(const NG2Controller *,uint64_t,uint64_t);
int ng2_controller_tick(NG2Controller *p,uint64_t now,int32_t front,int32_t locked,int32_t owner,NG2Command *out){
    uint64_t start=ng2_partial120_now();
    int answer=ng2_runtime120_real_tick(p,now,front,locked,owner,out);
    if(target120&&answer==1&&out->kind==NG2_ACTION_MOVE&&!counts120.command_id){ng2_partial120_select(out->id);target120=0;}
    if(answer==1&&out->id==counts120.command_id){++counts120.tick_calls;
        counts120.tick_entry_ns=start;counts120.tick_exit_ns=ng2_partial120_now();}
    return answer;
}
int ng2_controller_begin(NG2Controller *p,uint64_t id,uint64_t now,int32_t front,int32_t locked,int32_t owner){
    uint64_t start=ng2_partial120_now(),before=counts120.motion_calls;
    int answer=ng2_runtime120_real_begin(p,id,now,front,locked,owner);
    if(id==counts120.command_id){++counts120.begin_calls;counts120.begin_accepted+=answer==1;
        counts120.begin_entry_ns=start;counts120.begin_exit_ns=ng2_partial120_now();
        counts120.begin_motion_calls+=counts120.motion_calls-before;}
    return answer;
}
uint64_t ng2_controller_preparation_epoch(const NG2Controller *p,uint64_t id,uint64_t now){
    uint64_t start=ng2_partial120_now(),before=counts120.motion_calls;
    uint64_t answer=ng2_runtime120_real_epoch(p,id,now);
    if(id==counts120.command_id){++counts120.getter_calls;counts120.getter_motion_calls+=counts120.motion_calls-before;
        counts120.getter_ns+=ng2_partial120_now()-start;}
    return answer;
}
int ng2_controller_complete(NG2Controller *p,uint64_t id,uint64_t now,int32_t outcome){
    int answer=ng2_runtime120_real_complete(p,id,now,outcome);
    if(id==counts120.command_id){++counts120.complete_calls;counts120.complete_ns=now;counts120.complete_outcome=outcome;}
    return answer;
}
double ng2_fixture_partial120_phase(const NG2Partial120Setup *s,uint64_t now){
    uint64_t phase=now<=s->epoch_ns?(s->epoch_ns-now)%s->period_ns:
        (s->period_ns-(now-s->epoch_ns)%s->period_ns)%s->period_ns;
    return (double)phase/(double)s->period_ns;
}
static void wait120(uint64_t until){
    uint64_t now;
    while((now=ng2_partial120_now())<until){
        uint64_t remaining=until-now;
        if(remaining>UINT64_C(1500000)){struct timespec delay={0,1000000};nanosleep(&delay,NULL);}
    }
}
typedef struct {NG2Controller *core;NG2Partial120Setup *out;NG2Partial120FrameCallback callback;void *context;uint8_t *rgba;} Prelude120;
static int observe120(Prelude120 *p,int kind){
    NG2Scene scene;NG2IrregularObservation irregular;uint64_t start=ng2_partial120_now();
    if(!ng2_fixture_queue120_rgba(p->rgba,Q120_SIZE,kind,0,ng2_fixture_partial120_phase(p->out,start)))return 0;
    uint64_t end=ng2_partial120_now(),analysis=ng2_partial120_now();
    if(ng2_analyze_rgba(p->rgba,Q120_SIZE,896u*4u,&scene)
       ||ng2_analyze_irregular_rgba(p->rgba,Q120_SIZE,896u*4u,0,&irregular))return 0;
    uint64_t returned=ng2_partial120_now();++p->out->latest_id;++p->out->frames;
    ng2_controller_observe_irregular_at(p->core,&scene,&irregular,p->out->latest_id,start,end,p->out->prefix,1,returned);
    NG2ControllerStatus status;ng2_controller_status(p->core,&status);
    if(p->callback)p->callback(p->context,p->out->latest_id,start,end,p->out->prefix,analysis,returned,
        p->rgba,Q120_SIZE,&scene,&irregular);
    return status.last_capture_id==p->out->latest_id;
}
static int ticket120(Prelude120 *p,int kind,NG2Command *command){
    for(int n=0;n<6;++n){
        if(ng2_controller_tick(p->core,ng2_partial120_now(),1,0,1,command)==1)
            return command->kind==NG2_ACTION_MOVE&&command->direction==NG2_LEFT;
        NG2ControllerStatus status;ng2_controller_status(p->core,&status);
        if(status.reason||status.terminal||!status.next_target_ns)return 0;
        uint64_t publication=status.next_target_ns-status.lead_ns-UINT64_C(100000000);
        if(publication>ng2_partial120_now())wait120(publication);
        if(!observe120(p,kind))return 0;
    }
    return 0;
}
static int ack120(Prelude120 *p,const NG2Command *command){
    wait120(command->not_before_ns);uint64_t entry=ng2_partial120_now();
    if(!ng2_controller_begin(p->core,command->id,entry,1,0,1))return 0;
    wait120(entry+UINT64_C(50000000));uint64_t returned=ng2_partial120_now();
    if(!ng2_controller_complete(p->core,command->id,returned,1))return 0;
    p->out->prefix=command->id;p->out->ack_ns=returned;return 1;
}
NG2Controller *ng2_fixture_partial120_setup(NG2Partial120FrameCallback callback,void *context,NG2Partial120Setup *out){
    if(!out)return NULL;
    memset(out,0,sizeof(*out));out->entry_ns=out->started_ns=ng2_partial120_now();
    out->epoch_ns=out->started_ns+UINT64_C(4000000000);out->period_ns=UINT64_C(520000000);
    Prelude120 p={ng2_controller_create_cycle(out->started_ns),out,callback,context,NULL};NG2Command command={0};
    p.rgba=(uint8_t*)malloc(Q120_SIZE);
    if(!p.core||!p.rgba){out->error=1;goto failed;}
    if(!ng2_controller_enable_irregular(p.core)||!ng2_controller_enable_restart_yield(p.core)){out->error=2;goto failed;}
    if(!observe120(&p,NG2_QUEUE120_PAUSE)||ng2_controller_tick(p.core,ng2_partial120_now(),1,0,1,&command)!=1
       ||command.kind!=NG2_ACTION_RESUME||!ack120(&p,&command)){out->error=3;goto failed;}
    for(int n=0;n<27;++n){wait120(ng2_partial120_now()+UINT64_C(100000000));
        if(!observe120(&p,NG2_QUEUE120_INITIAL)){out->error=4;goto failed;}}
    if(!ticket120(&p,NG2_QUEUE120_INITIAL,&command)||!ack120(&p,&command)){out->error=5;goto failed;}
    wait120(command.target_ns+UINT64_C(100000000));
    if(!observe120(&p,NG2_QUEUE120_GATE)){out->error=6;goto failed;}
    ng2_controller_status(p.core,&out->status);
    if(out->status.moves!=1||out->status.door_changes){out->error=7;goto failed;}
    ++out->normal_units;
    if(!ticket120(&p,NG2_QUEUE120_GATE,&command)||!ack120(&p,&command)){out->error=8;goto failed;}
    out->command=command;ng2_controller_status(p.core,&out->status);out->return_ns=ng2_partial120_now();
    free(p.rgba);return p.core;
failed:
    if(p.core){ng2_controller_status(p.core,&out->status);ng2_controller_destroy(p.core);}
    out->command=command;out->return_ns=ng2_partial120_now();free(p.rgba);return NULL;
}

