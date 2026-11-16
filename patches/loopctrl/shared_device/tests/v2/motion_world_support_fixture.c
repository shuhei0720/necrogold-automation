/* Actual coverage must reach every C reference through a monotonic run mask. */
#define main ng2_static_profile_fixture_main
#include "motion_profile_fixture.c"
#undef main
int main(void){
    const NG2DeviceGeometryProfile *p=ng2_device_geometry_profile("iPhone10,1",375,667);
    uint8_t *fixed=malloc(NG2_SIGNATURE_LENGTH),*dynamic=malloc(NG2_SIGNATURE_LENGTH);
    uint8_t *coverage=malloc(896u*414u),*reappeared=malloc(896u*414u);
    NG2Scene *before=malloc(sizeof(*before)),*after=malloc(sizeof(*after));
    NG2Motion old,restricted;int count;
    REQUIRE(p&&fixed&&dynamic&&coverage&&reappeared&&before&&after);
    REQUIRE(ng2_device_motion_signature_support(p,fixed,NG2_SIGNATURE_LENGTH));
    memcpy(dynamic,fixed,NG2_SIGNATURE_LENGTH);memset(coverage,1,896u*414u);
    memset(reappeared,1,896u*414u);
    for(int y=60;y<340;y++)for(int x=160;x<700;x++)coverage[y*896+x]=0;
    /* Build expected support directly from the ACTUAL mask, independent of
     * production erosion. This test has one unknown region in an old C anchor. */
    for(int y=0;y<104;y++)for(int x=0;x<224;x++)if(dynamic[y*224+x]){
        for(int py=4*y-8;py<=4*y+8&&dynamic[y*224+x];py++)
            for(int px=4*x-8;px<=4*x+8;px++)if(!coverage[py*896+px]){dynamic[y*224+x]=0;break;}
    }
    make_pair(before,after,dynamic,NG2_LEFT,0,2654435768u,&count);
    REQUIRE(scoped(before,after,NG2_LEFT,fixed,NG2_SIGNATURE_LENGTH,&old)==1);
    REQUIRE(old.kind==NG2_MOVED&&old.dx==-1&&old.dy==0);
#ifndef NG2_DYNAMIC_SUPPORT_BASELINE_RED
    REQUIRE(ng2_device_motion_intersect_world(coverage,896u*414u,fixed,NG2_SIGNATURE_LENGTH));
#endif
    REQUIRE(scoped(before,after,NG2_LEFT,fixed,NG2_SIGNATURE_LENGTH,&restricted)==1);
    REQUIRE(restricted.kind==NG2_MOTION_UNKNOWN&&!restricted.dx&&!restricted.dy);
#ifndef NG2_DYNAMIC_SUPPORT_BASELINE_RED
    REQUIRE(memcmp(fixed,dynamic,NG2_SIGNATURE_LENGTH)==0);
    REQUIRE(ng2_device_motion_intersect_world(reappeared,896u*414u,fixed,NG2_SIGNATURE_LENGTH));
    REQUIRE(memcmp(fixed,dynamic,NG2_SIGNATURE_LENGTH)==0); /* no widening on eviction/reappearance */
    REQUIRE(!ng2_device_motion_intersect_world(NULL,0,fixed,NG2_SIGNATURE_LENGTH));
    for(int i=0;i<NG2_SIGNATURE_LENGTH;i++)REQUIRE(fixed[i]==0);
#endif
    free(after);free(before);free(reappeared);free(coverage);free(dynamic);free(fixed);
    puts("PASS actual per-frame coverage intersection rejects dynamic-only motion and never widens; input_authorized=false");return 0;
}
