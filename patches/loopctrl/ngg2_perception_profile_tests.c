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

static unsigned scene_cases,orientation_cases,fingerprint_cases,floor_quantization_cases;
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
static void quantization_floor(uint8_t *rgba){
    opaque_black(rgba);
    paint_mask(rgba,&ng2_template_icon);paint_mask(rgba,&ng2_template_footer);
    paint_mask(rgba,&ng2_template_zone_one);paint_mask(rgba,&ng2_template_floor_one);
}
static int quantization_noise(int n,int texture){
    if(!texture||n==624)return 0;
    if(texture==2){
        /* Population variance is exactly4:620*4+9+9+1+1=625*4. */
        if(n<310)return -2;
        if(n<620)return 2;
        return n==620?-3:n==621?3:n==622?-1:1;
    }
    return n%2?-(texture==3?2:3):(texture==3?2:3);
}
static void quantization_cell(uint8_t *rgba,int tx,int ty,int r,int g,int b,int texture){
    int x,y,n=0,cx=448+36*tx,cy=207+36*ty;
    for(y=cy-12;y<cy+13;++y)for(x=cx-12;x<cx+13;++x){
        size_t at=((size_t)y*WIDTH+(size_t)x)*4;
        int noise=quantization_noise(n++,texture);
        rgba[at]=(uint8_t)(r+noise);rgba[at+1]=(uint8_t)(g+noise);
        rgba[at+2]=(uint8_t)(b+noise);rgba[at+3]=255;
    }
}
static void quantization_tile(int x,int y,int expected){
    int index=(y+5)*23+x+11;
    require(reference_scene->tiles[index]==expected&&optimized_scene->tiles[index]==expected,
            "profile_floor_quantization_known_tile");
    ++floor_quantization_cases;
}
static void floor_quantization(void){
    /* Fixed semantic expectations, not copied from either compiler output.
     * TEST056's visually confirmed floor(44,27,24) motivates the first row.
     * The remaining rows bound only bright-floor lower B by+155; dark-floor,
     * upper limits, texture and the obstacle precedence stay independent. */
    static const struct { int r,g,b,texture,expected; } cases[]={
        {44,27,24,1,NG2_TILE_FLOOR}, /* Known TEST056 floor, old formula rejects. */
        {41,25,21,1,NG2_TILE_FLOOR}, /* Exact lower equality:55*41=100*21+155. */
        {50,30,26,1,NG2_TILE_FLOOR}, /* Inside by5, not a ratio.50 extension. */
        {52,31,27,1,NG2_TILE_DIRT},  /* Outside by5:2860>2700+155. */
        {41,25,20,1,NG2_TILE_DIRT},
        {38,23,17,1,NG2_TILE_FLOOR}, /* Existing dark-band boundary. */
        {39,23,17,1,NG2_TILE_DIRT},
        {39,23,20,1,NG2_TILE_FLOOR},
        {39,23,19,1,NG2_TILE_DIRT},
        {52,31,28,1,NG2_TILE_FLOOR},
        {53,33,29,1,NG2_TILE_DIRT},
        {53,33,30,1,NG2_TILE_UNKNOWN},
        {50,34,30,1,NG2_TILE_FLOOR}, /* G upper equality. */
        {50,35,30,1,NG2_TILE_STONE},
        {40,18,22,1,NG2_TILE_FLOOR}, /* G lower equality. */
        {40,17,21,1,NG2_TILE_DIRT},  /* Only G lower fails the floor band. */
        {40,17,22,1,NG2_TILE_UNKNOWN},
        {40,24,28,1,NG2_TILE_FLOOR}, /* B upper equality. */
        {40,25,29,1,NG2_TILE_UNKNOWN},
        {50,32,26,1,NG2_TILE_FLOOR}, /* abs(G-B)=.12*R. */
        {50,33,26,1,NG2_TILE_DIRT},
        {44,27,24,2,NG2_TILE_FLOOR}, /* Population stddev exactly2. */
        {44,27,24,3,NG2_TILE_DIRT},  /* Population stddev just below2. */
        {40,25,23,0,NG2_TILE_UNKNOWN},
        {39,24,22,1,NG2_TILE_FLOOR}, /* Existing positive colour assertions. */
        {40,25,23,1,NG2_TILE_FLOOR},
        {45,30,30,1,NG2_TILE_FLOOR},
        {52,35,29,1,NG2_TILE_FLOOR},
        {50,36,30,1,NG2_TILE_STONE}, /* Existing excluded colour assertions. */
        {50,25,25,1,NG2_TILE_DIRT},  /* A blanket B/R>=.50 would accept this. */
        {45,32,29,1,NG2_TILE_STONE},
        {53,33,31,1,NG2_TILE_UNKNOWN},
        {70,70,65,1,NG2_TILE_STONE},
        {50,32,15,1,NG2_TILE_DIRT},
        {63,19,4,1,NG2_TILE_UNKNOWN}, /* Unbracketed wood is not floor/door. */
        {3,3,3,0,NG2_TILE_UNKNOWN}
    };
    uint8_t *rgba=allocate(RGBA_LENGTH);size_t k;int n,goods;
    for(k=0;k<sizeof(cases)/sizeof(cases[0]);++k){
        quantization_floor(rgba);
        quantization_cell(rgba,-1,0,cases[k].r,cases[k].g,cases[k].b,cases[k].texture);
        compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_FLOOR,NG2_GOODS_UNKNOWN);
        quantization_tile(-1,0,cases[k].expected);
    }
    /* Gold's625-pixel sample count wins before the floor median/variance.
     * At279 gold pixels the remaining346 floor pixels still determine it. */
    for(n=279;n<=280;++n){
        int i;quantization_floor(rgba);quantization_cell(rgba,-1,0,44,27,24,1);
        for(i=0;i<n;++i){size_t at=((size_t)(195+i/25)*WIDTH+(size_t)(400+i%25))*4;
            rgba[at]=199;rgba[at+1]=164;rgba[at+2]=63;}
        compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_FLOOR,NG2_GOODS_UNKNOWN);
        quantization_tile(-1,0,n==280?NG2_TILE_GOLD:NG2_TILE_FLOOR);
    }
    quantization_floor(rgba);quantization_cell(rgba,-10,-3,44,27,24,1);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_FLOOR,NG2_GOODS_UNKNOWN);
    quantization_tile(-10,-3,NG2_TILE_UNKNOWN); /* HUD overlap still excludes. */
    require(ng2_fixture_floor_rgba(rgba,RGBA_LENGTH,0,0,.25,1)==1,
            "profile_floor_quantization_goods_fixture");
    quantization_cell(rgba,-1,0,44,27,24,1);
    compare_scene(rgba,RGBA_LENGTH,STRIDE,0,NG2_FLOOR,NG2_GOODS_VISIBLE);
    quantization_tile(-1,0,NG2_TILE_FLOOR);
    for(goods=-7;goods<=-5;++goods){
        int index=3*23+goods+11;
        require(optimized_scene->tiles[index]==NG2_TILE_ITEM
                &&optimized_scene->protected_cells[index]
                &&optimized_scene->protected_cells[index-23]
                &&optimized_scene->protected_cells[index+23],
                "profile_floor_quantization_merchandise_protected");
    }
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
    scenes();floor_quantization();orientations();fingerprints();
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
           "orientation=%u/all output bytes; fingerprint=%u; floor_quantization=%u; "
           "compiler=%s; arch=%s\n",
           scene_cases,sizeof(NG2Scene),orientation_cases,fingerprint_cases,
           floor_quantization_cases,compiler,architecture);
    return 0;
}
