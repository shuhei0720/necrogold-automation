/* TEST119 Runtime component setup. Public procedural RGBA and lifecycle only. */
#include "ngg2_runtime119_queue_fixture.h"
#include "ngg2_runtime_scene_fixtures.h"
#include "ngg2/NG2Templates.h"
#include "runtime119_queue_pixels.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define Q119_SIZE (896u*414u*4u)
static void pixel119(uint8_t *out,int x,int y,int r,int g,int b){
    size_t at;if(x<0||x>=896||y<0||y>=414)return;
    at=((size_t)y*896+(size_t)x)*4;
    out[at]=(uint8_t)r;out[at+1]=(uint8_t)g;out[at+2]=(uint8_t)b;out[at+3]=255;
}
int ng2_fixture_queue119_rgba(uint8_t *out,size_t length,int32_t kind,
                             int32_t candidate,double q){
    uint8_t world[1089]={0},*ui;int x,y,px=kind==NG2_QUEUE119_INITIAL?2:
        (kind==NG2_QUEUE119_BEFORE||kind==NG2_QUEUE119_OPENED||kind==NG2_QUEUE119_GATE?1:0);
    size_t i;int column=0,row=0;
    if(!out||length!=Q119_SIZE||kind<0||kind>7||(candidate!=0&&candidate!=1)
       ||!isfinite(q)||q<0||q>=1)return 0;
    (void)&ng2_template_icon;(void)&ng2_template_footer;(void)&ng2_template_zone_one;
    (void)&ng2_template_floor_one;(void)&ng2_template_death;
    if(kind==NG2_QUEUE119_PAUSE){
        const NG2Template *templates[2]={&ng2_template_continue,&ng2_template_restart};
        memset(out,0,length);for(i=3;i<length;i+=4)out[i]=255;
        for(int n=0;n<2;++n){const NG2Template *t=templates[n];
            for(y=0;y<t->h;++y)for(x=0;x<t->w;++x)
                if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1)
                    pixel119(out,t->x+x,t->y+y,180,180,180);
        }
        return 1;
    }
    for(y=-4;y<=0;++y)for(x=-5;x<=2;++x)world[(y+16)*33+x+16]=1;
    for(y=-5;y<=1;++y)world[(y+16)*33-6+16]=2;
    for(x=-6;x<=0;++x)world[17*33+x+16]=2;
    world[17*33-5+16]=4;
    world[15*33+16]=2;
    world[16*33+16]=(uint8_t)(kind==NG2_QUEUE119_INITIAL||kind==NG2_QUEUE119_GATE?7:1);
    world[11*33-6+16]=(uint8_t)(kind==NG2_QUEUE119_WALL?2:4);
    world[12*33-6+16]=4;
    world[19*33+7+16]=4;
    world[13*33-8+16]=3;world[18*33+5+16]=3;world[20*33+8+16]=3;
    if(!ng2_fixture_shop_rgba(out,length,px,0,q,world,sizeof(world),16,16,1,0))return 0;
    {
        int target=candidate&&(kind==NG2_QUEUE119_LATE||kind==NG2_QUEUE119_WALL);
        const NG2Queue119PixelRun *runs=target?ng2_queue119_candidate:ng2_queue119_normal;
        size_t count=target?sizeof(ng2_queue119_candidate)/sizeof(*runs):
            sizeof(ng2_queue119_normal)/sizeof(*runs);
        for(i=0;i<count;++i)for(int j=0;j<runs[i].count;++j){
            pixel119(out,214-36*px+column,52+row,runs[i].r,runs[i].g,runs[i].b);
            if(++column==253){column=0;++row;}
        }
        /* A positively drawn upper floor replaces the right wall segment.
         * Completing one remote GOLD cell cannot supply that whole wall. */
        for(y=52;y<151;++y)for(x=430-36*px;x<467-36*px;++x){
            int noise=(x+36*px+3*y)%7-3;
            pixel119(out,x,y,26+noise,16+noise,16+noise);
        }
        if(kind==NG2_QUEUE119_INITIAL||kind==NG2_QUEUE119_BEFORE||kind==NG2_QUEUE119_OPENED||kind==NG2_QUEUE119_GATE)
            for(y=67;y<107;++y)for(x=286-36*px;x<322-36*px;++x)
                pixel119(out,x,y,27,17,15);
    }
    if(kind==NG2_QUEUE119_EARLY){
        /* Deliberately ambiguous camera texture. This edits RGBA samples,
         * never a computed Scene/signature. Three fixed dark cap sample
         * boxes remain unchanged so their absent floor stays UNKNOWN. */
        for(y=80;y<316;y+=4)for(x=144;x<852;x+=4)
            if(!((x>=364&&x<=388&&y>=87&&y<=111)
                ||(x>=400&&x<=424&&y>=87&&y<=111)
                ||(x>=436&&x<=460&&y>=123&&y<=147)))pixel119(out,x,y,80,80,80);
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

typedef struct {
    NG2Controller *core;NG2Queue119Setup *out;NG2Queue119FrameCallback callback;
    void *context;uint8_t *rgba;uint64_t now;int cache_mode,cache_index;
} Q119Prelude;
typedef struct {uint8_t *rgba;NG2Scene scene;NG2IrregularObservation irregular;int kind;} Q119Cache;
static Q119Cache cache119[64];
static int cache119_count,cache119_ready;
static NG2Queue119Setup prepared119;
double ng2_fixture_queue119_phase(const NG2Queue119Setup *s,uint64_t now){
    uint64_t phase;
    if(!s||s->period_ns!=UINT64_C(520000000))return 0;
    phase=now<=s->epoch_ns?(s->epoch_ns-now)%s->period_ns:
        (s->period_ns-(now-s->epoch_ns)%s->period_ns)%s->period_ns;
    return (double)phase/(double)s->period_ns;
}
static int observe119(Q119Prelude *p,int kind){
    NG2Scene scene;NG2IrregularObservation irregular;uint64_t start=p->now-2;
    const uint8_t *rgba=p->rgba;
    if(p->cache_mode==2){
        if(p->cache_index>=cache119_count||cache119[p->cache_index].kind!=kind)return 0;
        const Q119Cache *c=&cache119[p->cache_index++];rgba=c->rgba;scene=c->scene;irregular=c->irregular;
    }else{
        if(!ng2_fixture_queue119_rgba(p->rgba,Q119_SIZE,kind,0,
           ng2_fixture_queue119_phase(p->out,p->now-1))
           ||ng2_analyze_rgba(p->rgba,Q119_SIZE,896u*4u,&scene)
           ||ng2_analyze_irregular_rgba(p->rgba,Q119_SIZE,896u*4u,0,&irregular)
           ||(kind==NG2_QUEUE119_PAUSE?scene.state!=NG2_PAUSE:
               scene.state!=NG2_FLOOR||!scene.beat_valid))return 0;
        if(p->cache_mode==1){
            if(cache119_count>=64)return 0;
            Q119Cache *c=&cache119[cache119_count++];c->kind=kind;c->scene=scene;c->irregular=irregular;
            c->rgba=(uint8_t*)malloc(Q119_SIZE);if(!c->rgba)return 0;
            memcpy(c->rgba,p->rgba,Q119_SIZE);
        }
    }
    ++p->out->latest_id;++p->out->frames;
    ng2_controller_observe_irregular_at(p->core,&scene,&irregular,p->out->latest_id,start,p->now,
        p->out->prefix,1,p->now);
    NG2ControllerStatus status;ng2_controller_status(p->core,&status);
    if(status.last_capture_id!=p->out->latest_id)return 0;
    if(p->callback)p->callback(p->context,p->out->latest_id,start,p->now,
        p->out->prefix,kind,rgba,Q119_SIZE,&scene,&irregular);
    return 1;
}
static int next119(Q119Prelude *p,int kind,NG2Command *command){
    for(int attempt=0;attempt<5;++attempt){
        NG2ControllerStatus s;
        if(ng2_controller_tick(p->core,p->now,1,0,1,command)==1)
            return command->kind==NG2_ACTION_MOVE&&command->direction==NG2_LEFT;
        ng2_controller_status(p->core,&s);
        if(s.reason||s.terminal||!s.next_target_ns)return 0;
        uint64_t publication=s.next_target_ns-s.lead_ns-UINT64_C(100000000);
        if(p->now<publication)p->now=publication;
        else ++p->now;
        if(!observe119(p,kind))return 0;
    }
    return 0;
}
static int ack119(Q119Prelude *p,const NG2Command *command){
    if(p->now<command->not_before_ns)p->now=command->not_before_ns;
    if(!ng2_controller_begin(p->core,command->id,p->now,1,0,1))return 0;
    p->now+=UINT64_C(50000000);
    if(!ng2_controller_complete(p->core,command->id,p->now,1))return 0;
    p->out->prefix=command->id;p->out->ack_ns=p->now;return 1;
}
static NG2Controller *prelude119(uint64_t started,NG2Queue119FrameCallback callback,
                                void *context,NG2Queue119Setup *out,int cache_mode){
    Q119Prelude p={0};NG2Command command={0};
    memset(out,0,sizeof(*out));out->started_ns=started;
    out->epoch_ns=started+UINT64_C(4000000000);out->period_ns=UINT64_C(520000000);
    p.core=ng2_controller_create_cycle(started);p.out=out;p.callback=callback;p.context=context;
    p.now=started+UINT64_C(100000000);p.rgba=(uint8_t*)malloc(Q119_SIZE);p.cache_mode=cache_mode;
    if(!p.core||!p.rgba){out->error=1;goto failed;}
    if(!ng2_controller_enable_irregular(p.core)||!ng2_controller_enable_restart_yield(p.core)){
        out->error=2;goto failed;}
    if(!observe119(&p,NG2_QUEUE119_PAUSE)
       ||ng2_controller_tick(p.core,p.now,1,0,1,&command)!=1
       ||command.kind!=NG2_ACTION_RESUME||!ack119(&p,&command)){
        out->error=13;goto failed;}
    for(int n=0;n<27;++n){p.now+=UINT64_C(100000000);
        if(!observe119(&p,NG2_QUEUE119_INITIAL)){out->error=3;goto failed;}}
    if(!next119(&p,NG2_QUEUE119_INITIAL,&command)||!ack119(&p,&command)){
        out->error=4;goto failed;}
    if(p.now<command.target_ns+UINT64_C(100000000))p.now=command.target_ns+UINT64_C(100000000);
    if(!observe119(&p,NG2_QUEUE119_GATE)){out->error=5;goto failed;}
    ng2_controller_status(p.core,&out->status);
    if(out->status.moves!=1||out->status.door_changes){out->error=6;goto failed;}
    ++out->normal_units;
    if(!next119(&p,NG2_QUEUE119_GATE,&command)||!ack119(&p,&command)){
        out->error=7;goto failed;}
    if(p.now<command.target_ns+UINT64_C(100000000))p.now=command.target_ns+UINT64_C(100000000);
    if(!observe119(&p,NG2_QUEUE119_OPENED)){out->error=8;goto failed;}
    ng2_controller_status(p.core,&out->status);
    if(out->status.moves!=1||out->status.door_changes!=1){out->error=9;goto failed;}
    ++out->opened_units;
    if(!next119(&p,NG2_QUEUE119_BEFORE,&command)||!ack119(&p,&command)){
        out->error=10;goto failed;}
    out->command=command;
    ng2_controller_status(p.core,&out->status);ng2_controller_cycle_status(p.core,&out->cycle);
    if(out->status.input_state!=3||out->status.moves!=1||out->status.inputs!=3
       ||out->cycle.pending||out->cycle.capture_id){out->error=11;goto failed;}
    free(p.rgba);return p.core;
failed:
    if(p.core){ng2_controller_status(p.core,&out->status);
        ng2_controller_cycle_status(p.core,&out->cycle);out->command=command;}
    free(p.rgba);if(p.core)ng2_controller_destroy(p.core);return NULL;
}
NG2Controller *ng2_fixture_queue119_setup(uint64_t now,NG2Queue119FrameCallback callback,
                                         void *context,NG2Queue119Setup *out){
    if(!out)return NULL;
    if(!cache119_ready){memset(out,0,sizeof(*out));out->error=14;return NULL;}
    uint64_t duration=prepared119.command.target_ns-prepared119.started_ns;
    if(now<=duration+UINT64_C(100000000)){memset(out,0,sizeof(*out));out->error=12;return NULL;}
    return prelude119(now-duration-UINT64_C(100000000),callback,context,out,2);
}
int ng2_fixture_queue119_prepare(void){
    if(cache119_ready)return 1;
    for(int n=0;n<cache119_count;++n){free(cache119[n].rgba);cache119[n].rgba=NULL;}
    cache119_count=0;
    NG2Controller *core=prelude119(UINT64_C(1000000000),NULL,NULL,&prepared119,1);
    if(!core)return -prepared119.error;
    ng2_controller_destroy(core);cache119_ready=1;return 1;
}
void ng2_fixture_queue119_prepared(NG2Queue119Setup *out){if(out)*out=prepared119;}
