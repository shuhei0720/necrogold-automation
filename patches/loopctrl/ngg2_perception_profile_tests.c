/* Host-only TEST049 compiler-profile parity. No device image is embedded.
 * The reference exports are the unchanged production file compiled with -O0;
 * the ordinary exports are that same file compiled with strict -O2. */
#include "NG2Core.h"
#include "NG2Templates.h"
#include "ngg2_runtime_scene_fixtures.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int ref_ng2_analyze_rgba(const uint8_t *,size_t,size_t,NG2Scene *);
extern int ref_ng2_fingerprint_changed(const uint8_t *,const uint8_t *);
extern size_t ref_ng2_orient_rgba(const uint8_t *,size_t,int32_t,int32_t,int32_t,
                                 uint8_t *,size_t);

#define WIDTH 896
#define HEIGHT 414
#define STRIDE ((size_t)WIDTH*4)
#define RGBA_LENGTH (STRIDE*HEIGHT)

static unsigned scene_cases,orientation_cases,fingerprint_cases;
static NG2Scene *reference_scene,*optimized_scene;

static void require(int condition,const char *name){
    if(!condition){printf("FAIL %s\n",name);exit(1);}
}
static void *allocate(size_t count){
    void *result=malloc(count);
    require(result!=NULL,"profile_fixture_allocation");
    return result;
}
static void opaque_black(uint8_t *rgba){
    size_t k;memset(rgba,0,RGBA_LENGTH);
    for(k=3;k<RGBA_LENGTH;k+=4)rgba[k]=255;
}
static void paint_mask(uint8_t *rgba,const NG2Template *mask){
    int x,y;
    for(y=0;y<mask->h;++y)for(x=0;x<mask->w;++x){
        size_t k=((size_t)(mask->y+y)*WIDTH+(size_t)(mask->x+x))*4;
        int bit=(mask->mask[y*((mask->w+7)/8)+x/8]>>(7-x%8))&1;
        rgba[k]=rgba[k+1]=rgba[k+2]=(uint8_t)(bit?180:0);
        rgba[k+3]=255;
    }
}
static void compare_scene(const uint8_t *rgba,size_t length,size_t stride,
                          int expected_return,int expected_state,int expected_goods){
    int old_result,new_result;
    memset(reference_scene,0xa5,sizeof(*reference_scene));
    memset(optimized_scene,0x5a,sizeof(*optimized_scene));
    old_result=ref_ng2_analyze_rgba(rgba,length,stride,reference_scene);
    new_result=ng2_analyze_rgba(rgba,length,stride,optimized_scene);
    require(old_result==expected_return&&new_result==expected_return,
            "strict_O2_and_unchanged_O0_scene_result");
    require(!memcmp(reference_scene,optimized_scene,sizeof(*reference_scene)),
            "strict_O2_and_unchanged_O0_entire_scene_bytes");
    require(optimized_scene->abi_version==NG2_ABI_VERSION
            &&optimized_scene->struct_size==sizeof(*optimized_scene),
            "profile_scene_ABI_is_preserved");
    require(optimized_scene->state==expected_state,"profile_known_scene_state");
    if(expected_goods>=0)require(optimized_scene->goods==expected_goods,
                                "profile_known_goods_state");
    ++scene_cases;
}
static void scenes(void){
    static const int shifts[][2]={{0,0},{-36,0},{36,0},{0,-36},{0,36},{35,0},{0,-35}};
    static const double phases[]={0,.125,.25,.499,.75,.875};
    uint8_t *rgba=allocate(RGBA_LENGTH),*padded;
    size_t phase,shift,row;int goods;
    /* Referencing all fixed templates keeps the frozen mask header warning
     * clean under both Apple Clang and GCC without changing its contents. */
    (void)&ng2_template_icon;(void)&ng2_template_footer;
    (void)&ng2_template_zone_one;(void)&ng2_template_floor_one;
    opaque_black(rgba);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_UNKNOWN,NG2_GOODS_UNKNOWN);
    paint_mask(rgba,&ng2_template_continue);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_PAUSE,NG2_GOODS_UNKNOWN);
    paint_mask(rgba,&ng2_template_restart);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_PAUSE,NG2_GOODS_UNKNOWN);
    require(optimized_scene->restart_label==1,"profile_known_restart_label");
    for(phase=0;phase<sizeof(phases)/sizeof(phases[0]);++phase){
        for(shift=0;shift<sizeof(shifts)/sizeof(shifts[0]);++shift){
            for(goods=0;goods<=1;++goods){
                require(ng2_fixture_floor_pixels_rgba(rgba,RGBA_LENGTH,shifts[shift][0],
                    shifts[shift][1],phases[phase],goods)==1,"profile_floor_fixture");
                compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_FLOOR,
                              goods?NG2_GOODS_VISIBLE:NG2_GOODS_UNKNOWN);
            }
        }
    }
    require(ng2_fixture_floor_rgba(rgba,RGBA_LENGTH,0,0,.25,0)==1,
            "profile_floor_guard_fixture");
    paint_mask(rgba,&ng2_template_death);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_UNKNOWN,NG2_GOODS_UNKNOWN);
    require(ng2_fixture_floor_rgba(rgba,RGBA_LENGTH,0,0,.25,1)==1,
            "profile_padded_fixture");
    padded=allocate((STRIDE+7)*HEIGHT);
    memset(padded,0x13,(STRIDE+7)*HEIGHT);
    for(row=0;row<HEIGHT;++row)memcpy(padded+row*(STRIDE+7),rgba+row*STRIDE,STRIDE);
    compare_scene(padded,(STRIDE+7)*HEIGHT,STRIDE+7,0,NG2_FLOOR,NG2_GOODS_VISIBLE);
    free(padded);
    compare_scene(NULL,RGBA_LENGTH,STRIDE,-1,NG2_UNKNOWN,NG2_GOODS_UNKNOWN);
    compare_scene(rgba,RGBA_LENGTH-1,STRIDE,-1,NG2_UNKNOWN,NG2_GOODS_UNKNOWN);
    rgba[3]=254;
    compare_scene(rgba,RGBA_LENGTH,STRIDE,-1,NG2_UNKNOWN,NG2_GOODS_UNKNOWN);
    free(rgba);
}
static uint64_t hash_bytes(const uint8_t *bytes,size_t length){
    uint64_t hash=UINT64_C(1469598103934665603);size_t k;
    for(k=0;k<length;++k){hash^=bytes[k];hash*=UINT64_C(1099511628211);}
    return hash;
}
static void orientation(int32_t width,int32_t height,int32_t direction){
    size_t k,pixels=(size_t)width*(size_t)height,length=pixels*4;
    uint8_t *input=allocate(length),*old=allocate(length),*current=allocate(length);
    uint64_t before;
    for(k=0;k<length;++k)input[k]=(uint8_t)((k*37+(k/4)*19+11)%251);
    before=hash_bytes(input,length);
    memset(old,0xa5,length);memset(current,0x5a,length);
    require(ref_ng2_orient_rgba(input,length,width,height,direction,old,length)==pixels
            &&ng2_orient_rgba(input,length,width,height,direction,current,length)==pixels,
            "strict_O2_and_unchanged_O0_orientation_count");
    require(!memcmp(old,current,length),"strict_O2_and_unchanged_O0_orientation_all_bytes");
    require(hash_bytes(input,length)==before,"profile_orientation_input_immutable");
    for(k=3;k<length;k+=4)require(current[k]==255,"profile_orientation_opaque_alpha");
    ++orientation_cases;free(input);free(old);free(current);
}
static void orientations(void){
    static const int32_t sizes[][2]={{1,1},{2,3},{3,5},{7,2},{828,1792}};
    size_t k;int32_t direction;
    for(k=0;k<sizeof(sizes)/sizeof(sizes[0]);++k)
        for(direction=1;direction<=8;++direction)
            orientation(sizes[k][0],sizes[k][1],direction);
}
static void fingerprints(void){
    uint8_t before[48],after[48];unsigned variant,k;
    memset(before,0,sizeof(before));
    for(variant=0;variant<128;++variant){
        for(k=0;k<48;++k)after[k]=(uint8_t)((k*variant+variant*7)%37);
        require(ref_ng2_fingerprint_changed(before,after)==ng2_fingerprint_changed(before,after),
                "strict_O2_and_unchanged_O0_fingerprint");
        ++fingerprint_cases;
    }
    require(ref_ng2_fingerprint_changed(NULL,after)==0&&ng2_fingerprint_changed(NULL,after)==0,
            "profile_null_fingerprint_is_rejected");
    ++fingerprint_cases;
}
int main(void){
    const char *compiler,*architecture;
    reference_scene=allocate(sizeof(*reference_scene));
    optimized_scene=allocate(sizeof(*optimized_scene));
    scenes();orientations();fingerprints();
    free(reference_scene);free(optimized_scene);
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
    printf("PASS strict O2 perception matches unchanged O0; Scene=%u/all %zu bytes; "
           "orientation=%u/all output bytes; fingerprint=%u; compiler=%s; arch=%s\n",
           scene_cases,sizeof(NG2Scene),orientation_cases,fingerprint_cases,compiler,architecture);
    return 0;
}
