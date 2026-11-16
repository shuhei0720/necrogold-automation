/* Standalone C99 smoke: actual profile support plus unchanged motion evidence.
 * No Python/NumPy, images, device input, or qualification claims.
 * Compile from the normal tree with NG2Navigation.c+NG2DeviceGeometryProfile.c
 * and -I LoopCtrlUITests -std=c99 -O2 -Wall -Wextra -Werror -pedantic -lm. */
#include "NG2Core.h"
#include "NG2DeviceGeometryProfile.h"
#include "NG2MotionSupport.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SW 224
#define SH 104
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
static uint32_t random_next(uint32_t *state){
    uint32_t value=*state;value^=value<<13;value^=value>>17;value^=value<<5;
    *state=value;return value;
}
static int old_mask(int x,int y){
    return x>=40&&x<179&&y>=20&&y<79&&!(x>=90&&x<139&&y>=36);
}
static void make_pair(NG2Scene *before,NG2Scene *after,const uint8_t *support,
                      int direction,int observed,uint32_t seed,int *domain_count){
    static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
    int sx=-9*dx[direction],sy=-9*dy[direction];
    memset(before,0,sizeof(*before));memset(after,0,sizeof(*after));
    before->abi_version=after->abi_version=NG2_ABI_VERSION;
    before->struct_size=after->struct_size=(uint32_t)sizeof(*before);
    before->state=after->state=NG2_FLOOR;
    before->gold_state=after->gold_state=NG2_GOLD_CLEAR;
    /* All other cells are UNKNOWN; no fabricated terrain map is needed. */
    before->tiles[126]=after->tiles[126]=NG2_TILE_FLOOR;
    memset(before->signature,50,NG2_SIGNATURE_LENGTH);
    memset(after->signature,50,NG2_SIGNATURE_LENGTH);
    *domain_count=0;
    for(int y=0;y<SH;y++)for(int x=0;x<SW;x++){
        int old=y*SW+x,latest=(y+sy)*SW+x+sx,known;
        if(!old_mask(x,y)||!old_mask(x+sx,y+sy))continue;
        known=support[old]&&support[latest];
        if((observed&&!known)||(!observed&&known))continue;
        before->signature[old]=(uint8_t)(12+random_next(&seed)%218);
        after->signature[latest]=before->signature[old];
        ++*domain_count;
    }
}
static int scoped(const NG2Scene *before,const NG2Scene *after,int direction,
                   const uint8_t *support,size_t length,NG2Motion *out){
    NG2MotionSupportScope previous=ng2_motion_support_enter(support,length);
    int result=ng2_motion(before,after,direction,out);
    ng2_motion_support_leave(previous);return result;
}
static int same_motion(NG2Motion a,NG2Motion b){
    return a.kind==b.kind&&a.dx==b.dx&&a.dy==b.dy;
}
static int direction_case(int direction,NG2Scene *before,NG2Scene *after,
                          const uint8_t *support,const uint8_t *zero){
    static const int dx[5]={0,-1,1,0,0},dy[5]={0,0,0,-1,1};
    NG2Motion baseline,restricted,restored,positive;
    int invalid_count,valid_count;
    uint32_t seed=0x9e3779b9u^(uint32_t)direction;
    make_pair(before,after,support,direction,0,seed,&invalid_count);
    REQUIRE(ng2_motion(before,after,direction,&baseline)==1);
    REQUIRE(baseline.kind==NG2_MOVED&&baseline.dx==dx[direction]&&baseline.dy==dy[direction]);
    REQUIRE(scoped(before,after,direction,support,NG2_SIGNATURE_LENGTH,&restricted)==1);
    REQUIRE(restricted.kind==NG2_MOTION_UNKNOWN&&!restricted.dx&&!restricted.dy);
    REQUIRE(ng2_motion(before,after,direction,&restored)==1&&same_motion(baseline,restored));
    REQUIRE(scoped(before,after,direction,NULL,0,&restored)==1&&same_motion(baseline,restored));
    make_pair(before,after,support,direction,1,seed,&valid_count);
    REQUIRE(scoped(before,after,direction,support,NG2_SIGNATURE_LENGTH,&positive)==1);
    REQUIRE(positive.kind==NG2_MOVED&&positive.dx==dx[direction]&&positive.dy==dy[direction]);
    REQUIRE(scoped(before,after,direction,zero,NG2_SIGNATURE_LENGTH,&restricted)==1);
    REQUIRE(restricted.kind==NG2_MOTION_UNKNOWN&&!restricted.dx&&!restricted.dy);
    REQUIRE(scoped(before,after,direction,NULL,NG2_SIGNATURE_LENGTH,&restricted)==1);
    REQUIRE(restricted.kind==NG2_MOTION_UNKNOWN&&!restricted.dx&&!restricted.dy);
    printf("direction%d seed%u invalid%d valid%d PASS\n",direction,seed,invalid_count,valid_count);
    return 0;
}
int main(void){
    const NG2DeviceGeometryProfile *profile=ng2_device_geometry_profile("iPhone10,1",375,667);
    uint8_t *support=(uint8_t*)malloc(NG2_SIGNATURE_LENGTH);
    uint8_t *zero=(uint8_t*)calloc(NG2_SIGNATURE_LENGTH,1);
    NG2Scene *before=(NG2Scene*)malloc(sizeof(*before));
    NG2Scene *after=(NG2Scene*)malloc(sizeof(*after));
    REQUIRE(profile&&profile->qualification_gaps==31&&support&&zero&&before&&after);
    REQUIRE(ng2_device_motion_signature_support(profile,support,NG2_SIGNATURE_LENGTH)==1);
    for(int direction=NG2_LEFT;direction<=NG2_DOWN;direction++)
        if(direction_case(direction,before,after,support,zero))return 1;
    free(after);free(before);free(zero);free(support);
    puts("PASS actual profile support: 4invalidUNKNOWN,4observedMOVED,zero/malformedUNKNOWN,NULLrestore; input_authorized=false");
    return 0;
}
