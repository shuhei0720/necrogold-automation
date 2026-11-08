/* TEST050 host-only compiler parity; no implementation is copied here.
 * Compile this file in wrapper mode twice to expose the original file's static
 * probes, then in ordinary mode as the executable. The production public
 * symbols below must come from the actual strict Navigation object. */
#if defined(NG2_NAVIGATION_PROFILE_WRAPPER)
#if defined(NG2_PROFILE_REFERENCE)
#define ng2_choose ref_ng2_choose
#define ng2_motion ref_ng2_motion
#define ng2_entered_gate ref_ng2_entered_gate
#define ng2_profile_view ref_ng2_profile_view
#define ng2_profile_scores ref_ng2_profile_scores
#define ng2_profile_evaluate ref_ng2_profile_evaluate
#define ng2_profile_strong ref_ng2_profile_strong
#define ng2_profile_texture_strength ref_ng2_profile_texture_strength
#define ng2_profile_texture_lead ref_ng2_profile_texture_lead
#else
#define ng2_choose profile_unused_ng2_choose
#define ng2_motion profile_unused_ng2_motion
#define ng2_entered_gate profile_unused_ng2_entered_gate
#endif
#include "NG2Navigation.c"
void ng2_profile_view(const uint8_t *raw,uint8_t *out){
    View result;view(raw,&result);memcpy(out,&result,sizeof(result));
}
void ng2_profile_scores(const uint8_t *a,const uint8_t *b,double *out){
    View views[2];int k=1,n,d;view(a,&views[0]);view(b,&views[1]);
    out[0]=intensity(&views[0],&views[1],0,0);
    for(n=1;n<=18;++n)for(d=1;d<=4;++d)
        out[k++]=intensity(&views[0],&views[1],n*ddx[d],n*ddy[d]);
}
void ng2_profile_evaluate(const NG2Scene *a,const NG2Scene *b,int direction,
                          const double *scores,NG2Motion *out){
    View views[2];Candidate candidates[73];int k=1,n,d;
    view(a->signature,&views[0]);view(b->signature,&views[1]);
    memset(out,0,sizeof(*out));
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=scores[0];
    for(n=1;n<=18;++n)for(d=1;d<=4;++d){
        candidates[k].sx=n*ddx[d];candidates[k].sy=n*ddy[d];
        candidates[k].score=scores[k];++k;
    }
    evaluate_motion(a,b,direction,views,candidates,out);
}
int ng2_profile_texture_strength(int support,int bad,int percent){
    return texture_strength(support,bad,percent);
}
int ng2_profile_texture_lead(int support,int bad,int count,int opposite){
    return texture_lead(support,bad,count,opposite);
}
int ng2_profile_strong(const uint8_t *texture,const uint8_t *positive,
                       int expanded,int regions){
    View views[2];Candidate candidates[73];int i,k=1,n,d;
    memset(views,0,sizeof(views));
    for(i=0;i<N;++i){
        views[0].texture[i]=views[1].texture[i]=texture[i]!=0;
        views[1].positive[i]=positive[i]!=0;
    }
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=0;
    for(n=1;n<=18;++n)for(d=1;d<=4;++d){
        candidates[k].sx=n*ddx[d];candidates[k].sy=n*ddy[d];
        candidates[k].score=1;++k;
    }
    return strong_texture(&views[0],&views[1],candidates,expanded,regions);
}
#else
#include "NG2Core.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int ref_ng2_choose(const NG2Scene *,int32_t,int32_t,const uint16_t *,size_t,const NG2Entrance *,NG2Decision *);
extern int ref_ng2_motion(const NG2Scene *,const NG2Scene *,int32_t,NG2Motion *);
extern int ref_ng2_entered_gate(const NG2Scene *,const NG2Scene *,int32_t,int32_t,int32_t,int32_t,NG2Entrance *);
#define DECLARE_PROBES(prefix) \
extern void prefix##view(const uint8_t *,uint8_t *); \
extern void prefix##scores(const uint8_t *,const uint8_t *,double *); \
extern void prefix##evaluate(const NG2Scene *,const NG2Scene *,int,const double *,NG2Motion *); \
extern int prefix##strong(const uint8_t *,const uint8_t *,int,int); \
extern int prefix##texture_strength(int,int,int); \
extern int prefix##texture_lead(int,int,int,int)
DECLARE_PROBES(ng2_profile_);
DECLARE_PROBES(ref_ng2_profile_);

#define WIDTH 224
#define HEIGHT 104
#define LENGTH NG2_SIGNATURE_LENGTH
static unsigned view_cases,score_cases,motion_cases,decision_cases,entrance_cases,boundary_cases;
static const int dxs[5]={0,-1,1,0,0},dys[5]={0,0,0,-1,1};
static uint32_t random_state=43050;
static void require(int condition,const char *name){
    if(!condition){printf("FAIL %s\n",name);exit(1);}
}
static uint32_t random_word(void){
    random_state=random_state*UINT32_C(1664525)+UINT32_C(1013904223);
    return random_state;
}
static int at(int x,int y){return (y+5)*23+x+11;}
static void set_tile(NG2Scene *s,int x,int y,uint8_t kind){
    require(x>=-11&&x<=11&&y>=-5&&y<=4,"profile_fixture_tile_in_grid");
    s->tiles[at(x,y)]=kind;
}
static void scene(NG2Scene *s){
    size_t i;memset(s,0,sizeof(*s));s->abi_version=NG2_ABI_VERSION;
    s->struct_size=(uint32_t)sizeof(*s);s->state=NG2_FLOOR;
    set_tile(s,0,0,NG2_TILE_FLOOR);set_tile(s,-3,-3,NG2_TILE_GOLD);
    for(i=0;i<LENGTH;++i)s->signature[i]=(uint8_t)(20+(random_word()>>24)%80);
}
static void translate(const NG2Scene *a,NG2Scene *b,int tx,int ty,int sx,int sy){
    int x,y;*b=*a;memset(b->tiles,0,sizeof(b->tiles));
    memset(b->protected_cells,0,sizeof(b->protected_cells));memset(b->signature,0,LENGTH);
    for(y=-5;y<=4;++y)for(x=-11;x<=11;++x){
        if(x+tx>=-11&&x+tx<=11&&y+ty>=-5&&y+ty<=4){
            b->tiles[at(x+tx,y+ty)]=a->tiles[at(x,y)];
            b->protected_cells[at(x+tx,y+ty)]=a->protected_cells[at(x,y)];
        }
    }
    for(y=0;y<HEIGHT;++y)for(x=0;x<WIDTH;++x)
        if(x+sx>=0&&x+sx<WIDTH&&y+sy>=0&&y+sy<HEIGHT)
            b->signature[(y+sy)*WIDTH+x+sx]=a->signature[y*WIDTH+x];
}
static void compare_view(const NG2Scene *s){
    uint8_t old[3*LENGTH],current[3*LENGTH];NG2Scene snapshot=*s;
    memset(old,0xa5,sizeof(old));memset(current,0x5a,sizeof(current));
    ref_ng2_profile_view(s->signature,old);ng2_profile_view(s->signature,current);
    require(!memcmp(old,current,sizeof(old)),"strict_O2_and_unchanged_O0_entire_view_bytes");
    require(!memcmp(&snapshot,s,sizeof(snapshot)),"profile_view_input_immutable");++view_cases;
}
static void compare_scores(const NG2Scene *a,const NG2Scene *b){
    double old[73],current[73];NG2Scene ac=*a,bc=*b;
    memset(old,0xa5,sizeof(old));memset(current,0x5a,sizeof(current));
    ref_ng2_profile_scores(a->signature,b->signature,old);
    ng2_profile_scores(a->signature,b->signature,current);
    require(!memcmp(old,current,sizeof(old)),"strict_O2_and_unchanged_O0_all73_score_bytes");
    require(!memcmp(&ac,a,sizeof(ac))&&!memcmp(&bc,b,sizeof(bc)),"profile_score_inputs_immutable");++score_cases;
}
static NG2Motion compare_motion(const NG2Scene *a,const NG2Scene *b,int direction,
                               int expected_return,int expected_kind,const double *scores){
    NG2Motion old,current;NG2Scene ac,bc;int r1,r2;double saved[73];
    if(a)ac=*a;
    if(b)bc=*b;
    if(scores)memcpy(saved,scores,sizeof(saved));
    memset(&old,0xa5,sizeof(old));memset(&current,0x5a,sizeof(current));
    if(scores){
        ref_ng2_profile_evaluate(a,b,direction,scores,&old);
        ng2_profile_evaluate(a,b,direction,scores,&current);r1=r2=1;
    }else{
        r1=ref_ng2_motion(a,b,direction,&old);r2=ng2_motion(a,b,direction,&current);
    }
    require(r1==r2&&r2==expected_return,"strict_O2_and_unchanged_O0_motion_return");
    require(!memcmp(&old,&current,sizeof(old)),"strict_O2_and_unchanged_O0_entire_Motion_bytes");
    require(current.kind==expected_kind,"profile_known_motion_kind");
    if(expected_kind==NG2_MOVED)
        require(current.dx==dxs[direction]&&current.dy==dys[direction],"profile_known_motion_displacement");
    if(!expected_return)require(!current.kind&&!current.dx&&!current.dy,"profile_invalid_motion_output_zero");
    if(expected_kind!=NG2_MOVED&&expected_kind!=NG2_UNEXPECTED)
        require(!current.dx&&!current.dy,"profile_known_non_displacement_motion");
    require((!a||!memcmp(&ac,a,sizeof(ac)))&&(!b||!memcmp(&bc,b,sizeof(bc)))
            &&(!scores||!memcmp(saved,scores,sizeof(saved))),"profile_motion_inputs_immutable");
    ++motion_cases;return current;
}
static NG2Decision compare_decision(const NG2Scene *s,int x,int y,const uint16_t *visits,
                                    size_t count,const NG2Entrance *entrance,int expected_return,
                                    int expected_direction,int expected_reason){
    NG2Decision old,current;NG2Scene snapshot;NG2Entrance saved;
    uint16_t history[NG2_VISIT_COUNT];int r1,r2;
    if(s)snapshot=*s;
    if(visits)memcpy(history,visits,sizeof(history));
    if(entrance)saved=*entrance;
    memset(&old,0xa5,sizeof(old));memset(&current,0x5a,sizeof(current));
    r1=ref_ng2_choose(s,x,y,visits,count,entrance,&old);
    r2=ng2_choose(s,x,y,visits,count,entrance,&current);
    require(r1==r2&&r2==expected_return,"strict_O2_and_unchanged_O0_decision_return");
    require(!memcmp(&old,&current,sizeof(old)),"strict_O2_and_unchanged_O0_entire_Decision_bytes");
    require(current.direction==expected_direction&&current.reason==expected_reason,"profile_known_decision");
    if(!expected_return&&!expected_reason){
        NG2Decision zero;memset(&zero,0,sizeof(zero));
        require(!memcmp(&current,&zero,sizeof(zero)),"profile_rejected_decision_output_zero");
    }
    require((!s||!memcmp(&snapshot,s,sizeof(snapshot)))&&(!visits||!memcmp(history,visits,sizeof(history)))
            &&(!entrance||!memcmp(&saved,entrance,sizeof(saved))),"profile_decision_inputs_immutable");
    ++decision_cases;return current;
}
static NG2Entrance compare_entrance(const NG2Scene *a,const NG2Scene *b,int direction,
                                    int x,int y,int motion,int expected_return){
    NG2Entrance old,current;NG2Scene ac,bc;int r1,r2;
    if(a)ac=*a;
    if(b)bc=*b;
    memset(&old,0xa5,sizeof(old));memset(&current,0x5a,sizeof(current));
    r1=ref_ng2_entered_gate(a,b,direction,x,y,motion,&old);
    r2=ng2_entered_gate(a,b,direction,x,y,motion,&current);
    require(r1==r2&&r2==expected_return,"strict_O2_and_unchanged_O0_entrance_return");
    require(!memcmp(&old,&current,sizeof(old)),"strict_O2_and_unchanged_O0_entire_Entrance_bytes");
    if(expected_return)
        require(current.valid==1&&current.x==x+dxs[direction]&&current.y==y+dys[direction]
                &&current.direction==direction,"profile_known_entrance");
    else require(!current.valid&&!current.x&&!current.y&&!current.direction,"profile_rejected_entrance_output_zero");
    require((!a||!memcmp(&ac,a,sizeof(ac)))&&(!b||!memcmp(&bc,b,sizeof(bc))),"profile_entrance_inputs_immutable");
    ++entrance_cases;return current;
}
static void signatures_and_motion(void){
    static const int amounts[]={0,1,8,9,10,18,-9};
    NG2Scene a,b;size_t k;int direction;
    scene(&a);
    for(direction=1;direction<=4;++direction)for(k=0;k<sizeof(amounts)/sizeof(amounts[0]);++k){
        int amount=amounts[k],kind=amount==0?NG2_BLOCKED:(amount==1||amount==8?NG2_TWEEN:
                                 (amount==9?NG2_MOVED:NG2_UNEXPECTED));
        translate(&a,&b,-dxs[direction],-dys[direction],-amount*dxs[direction],-amount*dys[direction]);
        compare_view(&b);compare_scores(&a,&b);compare_motion(&a,&b,direction,1,kind,NULL);
    }
    for(k=0;k<3;++k){
        memset(a.signature,k==0?0:(k==1?6:7),LENGTH);compare_view(&a);
        compare_scores(&a,&a);compare_motion(&a,&a,NG2_UP,1,NG2_MOTION_UNKNOWN,NULL);
    }
}
static void score_boundaries(void){
    static const int kinds[]={NG2_MOVED,NG2_MOTION_UNKNOWN,NG2_MOVED,NG2_MOTION_UNKNOWN,NG2_MOTION_UNKNOWN};
    double best[5]={.45,0,.2,.2,INFINITY},runner[5]={.53,.6,.28,0,INFINITY},scores[73];
    NG2Scene a,b;int k,j;
    best[1]=nextafter(.45,1.);runner[3]=nextafter(.28,0.);
    scene(&a);translate(&a,&b,0,1,0,9);
    for(k=0;k<5;++k){
        for(j=0;j<73;++j)scores[j]=j==36?best[k]:runner[k]; /* ninth down candidate */
        compare_motion(&a,&b,NG2_UP,1,kinds[k],scores);++boundary_cases;
    }
}
static void texture_boundaries(void){
    static const int strength[][4]={{299,0,75,0},{300,75,75,1},{300,76,75,0},{300,15,95,1},{300,16,95,0}};
    static const int lead[][3]={{400,80,1},{400,79,0},{299,0,1},{300,0,0}};
    static const int region[][5]={{150,150,15,1,1},{150,149,0,1,0},{150,150,16,1,0},{99,201,0,1,0},{99,201,0,0,1}};
    uint8_t texture[LENGTH],positive[LENGTH],saved_texture[LENGTH],saved_positive[LENGTH];
    int top[150],left[201],k,j,x,y,index,found,r1,r2;
    for(k=0;k<5;++k){
        r1=ref_ng2_profile_texture_strength(strength[k][0],strength[k][1],strength[k][2]);
        r2=ng2_profile_texture_strength(strength[k][0],strength[k][1],strength[k][2]);
        require(r1==r2&&r2==strength[k][3],"profile_exact_300_75_95_texture_strength");++boundary_cases;
    }
    for(k=0;k<4;++k){
        r1=ref_ng2_profile_texture_lead(400,20,lead[k][0],lead[k][1]);
        r2=ng2_profile_texture_lead(400,20,lead[k][0],lead[k][1]);
        require(r1==r2&&r2==lead[k][2],"profile_exact_15_percentage_point_lead");++boundary_cases;
    }
    for(k=0;k<351;++k){
        do{
            x=k<150?40+(int)((random_word()>>16)%139):40+(int)((random_word()>>16)%50);
            y=k<150?20+(int)((random_word()>>16)%16):36+(int)((random_word()>>16)%43);
            index=y*WIDTH+x;found=0;
            for(j=0;j<(k<150?k:k-150);++j)if((k<150?top[j]:left[j])==index)found=1;
        }while(found);
        if(k<150)top[k]=index;else left[k-150]=index;
    }
    for(k=0;k<5;++k){
        int count=0;memset(texture,0,sizeof(texture));memset(positive,0,sizeof(positive));
        for(j=0;j<region[k][0];++j){texture[top[j]]=255;if(count++<region[k][2])positive[top[j]]=255;}
        for(j=0;j<region[k][1];++j){texture[left[j]]=255;if(count++<region[k][2])positive[left[j]]=255;}
        memcpy(saved_texture,texture,sizeof(texture));memcpy(saved_positive,positive,sizeof(positive));
        r1=ref_ng2_profile_strong(texture,positive,0,region[k][3]);
        r2=ng2_profile_strong(texture,positive,0,region[k][3]);
        require(r1==r2&&r2==region[k][4],"profile_two_independent_100_support_regions");
        require(!memcmp(texture,saved_texture,sizeof(texture))&&!memcmp(positive,saved_positive,sizeof(positive)),
                "profile_texture_inputs_immutable");++boundary_cases;
    }
}
static void decisions_and_entrances(void){
    static const int side_direction[5]={0,NG2_UP,NG2_DOWN,NG2_RIGHT,NG2_LEFT};
    NG2Scene a,b;NG2Entrance entrance;NG2Decision chosen;uint16_t visits[NG2_VISIT_COUNT]={0};int d,k;
    for(d=1;d<=4;++d){
        int dx=dxs[d],dy=dys[d],tx=-dy,ty=dx;
        scene(&a);memset(a.tiles,0,sizeof(a.tiles));
        set_tile(&a,0,0,NG2_TILE_FLOOR);set_tile(&a,dx,dy,NG2_TILE_DOOR);
        set_tile(&a,dx+tx,dy+ty,NG2_TILE_GOLD);set_tile(&a,dx-tx,dy-ty,NG2_TILE_GOLD);
        chosen=compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,1,d,5);
        require(chosen.target_x==dx&&chosen.target_y==dy&&chosen.obstacle==NG2_TILE_DOOR,"profile_known_gate_target");
        b=a;set_tile(&b,dx,dy,NG2_TILE_FLOOR);
        compare_motion(&a,&b,d,1,NG2_DOOR_OPENED,NULL);
        compare_entrance(&a,&b,d,0,0,NG2_DOOR_OPENED,0);
        set_tile(&a,dx,dy,NG2_TILE_DIRT);
        compare_motion(&a,&b,d,1,NG2_TERRAIN_OPENED,NULL);
        for(k=0;k<2;++k){
            NG2Scene *s=k?&b:&a;s->protected_cells[at(dx,dy)]=1;
            compare_motion(&a,&b,d,1,NG2_BLOCKED,NULL);s->protected_cells[at(dx,dy)]=0;
        }
        set_tile(&a,dx,dy,NG2_TILE_FLOOR);translate(&a,&b,-dx,-dy,-9*dx,-9*dy);
        set_tile(&b,0,0,NG2_TILE_FLOOR);
        compare_motion(&a,&b,d,1,NG2_MOVED,NULL);compare_entrance(&a,&b,d,3,-3,NG2_MOVED,1);
        for(k=0;k<2;++k){
            NG2Scene *s=k?&b:&a;int idx=k?at(0,0):at(dx,dy);s->protected_cells[idx]=1;
            compare_entrance(&a,&b,d,3,-3,NG2_MOVED,0);s->protected_cells[idx]=0;
        }
        compare_entrance(&a,&b,d,dx*16,dy*16,NG2_MOVED,0);
        entrance.valid=1;entrance.x=dx;entrance.y=dy;entrance.direction=d;
        compare_decision(&b,0,0,visits,NG2_VISIT_COUNT,&entrance,0,0,4);
        memset(a.tiles,0,sizeof(a.tiles));set_tile(&a,0,0,NG2_TILE_FLOOR);
        set_tile(&a,dx,dy,NG2_TILE_FLOOR);set_tile(&a,-dx,-dy,NG2_TILE_FLOOR);
        set_tile(&a,tx,ty,NG2_TILE_FLOOR);
        set_tile(&a,-dx+tx,-dy+ty,NG2_TILE_GOLD);set_tile(&a,-dx-tx,-dy-ty,NG2_TILE_GOLD);
        chosen=compare_decision(&a,2*dx,2*dy,visits,NG2_VISIT_COUNT,&entrance,1,side_direction[d],8);
        require(chosen.target_x==tx&&chosen.target_y==ty,"profile_entrance_retains_gold_and_forbids_retreat");
        set_tile(&a,dx,dy,NG2_TILE_UNKNOWN);set_tile(&a,tx,ty,NG2_TILE_UNKNOWN);
        compare_decision(&a,2*dx,2*dy,visits,NG2_VISIT_COUNT,&entrance,0,0,0);
    }
    scene(&a);memset(a.tiles,0,sizeof(a.tiles));set_tile(&a,0,0,NG2_TILE_FLOOR);
    set_tile(&a,0,-1,NG2_TILE_FLOOR);set_tile(&a,0,1,NG2_TILE_FLOOR);set_tile(&a,3,0,NG2_TILE_GOLD);
    chosen=compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,1,NG2_DOWN,8);
    require(chosen.target_x==0&&chosen.target_y==1,"profile_route_tie_uses_direction_lexical_order");
    a.protected_cells[at(0,1)]=1;compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,2);
    a.protected_cells[at(0,1)]=0;a.goods=NG2_GOODS_VISIBLE;
    compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,1);
    a.goods=NG2_GOODS_UNKNOWN;set_tile(&a,3,0,NG2_TILE_UNKNOWN);
    compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,3);
    /* A gold bracket beyond the finite grid cannot create an observed route. */
    memset(a.tiles,0,sizeof(a.tiles));set_tile(&a,0,0,NG2_TILE_FLOOR);set_tile(&a,11,4,NG2_TILE_GOLD);
    compare_decision(&a,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,0);
}
static void invalid_arguments(void){
    NG2Scene valid,bad;NG2Decision decision;
    uint16_t visits[NG2_VISIT_COUNT]={0};int k;
    scene(&valid);
    for(k=0;k<6;++k){
        bad=valid;
        switch(k){case 0:bad.abi_version=0;break;case 1:bad.struct_size=0;break;
            case 2:bad.state=NG2_UNKNOWN;break;case 3:bad.goods=3;break;
            case 4:bad.tiles[0]=7;break;default:bad.protected_cells[0]=2;break;}
        decision=compare_decision(&bad,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,0);
        require(!decision.target_x&&!decision.target_y&&!decision.obstacle,"profile_invalid_decision_output_zero");
        compare_motion(&bad,&valid,NG2_UP,0,NG2_MOTION_UNKNOWN,NULL);
        compare_motion(&valid,&bad,NG2_UP,0,NG2_MOTION_UNKNOWN,NULL);
        compare_entrance(&bad,&valid,NG2_UP,0,0,NG2_MOVED,0);
        compare_entrance(&valid,&bad,NG2_UP,0,0,NG2_MOVED,0);
    }
    compare_decision(&valid,17,0,visits,NG2_VISIT_COUNT,NULL,0,0,0);
    compare_decision(&valid,0,-17,visits,NG2_VISIT_COUNT,NULL,0,0,0);
    compare_decision(&valid,0,0,visits,NG2_VISIT_COUNT-1,NULL,0,0,0);
    compare_decision(&valid,0,0,NULL,NG2_VISIT_COUNT,NULL,0,0,0);
    compare_decision(NULL,0,0,visits,NG2_VISIT_COUNT,NULL,0,0,0);
    compare_motion(NULL,&valid,NG2_UP,0,NG2_MOTION_UNKNOWN,NULL);
    compare_motion(&valid,NULL,NG2_UP,0,NG2_MOTION_UNKNOWN,NULL);
    for(k=0;k<3;++k){int direction=k==0?0:(k==1?5:-1);
        compare_motion(&valid,&valid,direction,0,NG2_MOTION_UNKNOWN,NULL);
        compare_entrance(&valid,&valid,direction,0,0,NG2_MOVED,0);
    }
    compare_entrance(NULL,&valid,NG2_UP,0,0,NG2_MOVED,0);
    compare_entrance(&valid,NULL,NG2_UP,0,0,NG2_MOVED,0);
    compare_entrance(&valid,&valid,NG2_UP,17,0,NG2_MOVED,0);
    require(!ref_ng2_choose(NULL,0,0,visits,NG2_VISIT_COUNT,NULL,NULL)
            &&!ng2_choose(NULL,0,0,visits,NG2_VISIT_COUNT,NULL,NULL),"profile_null_decision_output");
    require(!ref_ng2_motion(NULL,NULL,NG2_UP,NULL)&&!ng2_motion(NULL,NULL,NG2_UP,NULL),"profile_null_motion_output");
    require(!ref_ng2_entered_gate(NULL,NULL,NG2_UP,0,0,NG2_MOVED,NULL)
            &&!ng2_entered_gate(NULL,NULL,NG2_UP,0,0,NG2_MOVED,NULL),"profile_null_entrance_output");
}
int main(void){
    const char *compiler,*architecture;
    signatures_and_motion();score_boundaries();texture_boundaries();decisions_and_entrances();invalid_arguments();
#if defined(__clang__)
    compiler="Clang " __clang_version__;
#elif defined(__GNUC__)
    compiler="GCC " __VERSION__;
#else
    compiler="unknown";
#endif
#if defined(__aarch64__) || defined(__arm64__)
    architecture="arm64";
#elif defined(__x86_64__)
    architecture="x86_64";
#else
    architecture="other";
#endif
    printf("PASS strict O2 Navigation matches unchanged O0; views=%u/all %u bytes; "
           "scores=%u/all 73 double bytes; Motion=%u/Decision=%u/Entrance=%u; boundaries=%u; "
           "all returns and input bytes checked; compiler=%s; arch=%s\n",
           view_cases,3u*LENGTH,score_cases,motion_cases,decision_cases,entrance_cases,boundary_cases,compiler,architecture);
    return 0;
}
#endif
