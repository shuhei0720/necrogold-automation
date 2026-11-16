#include "NG2WorldSupport.h"
#include <string.h>
#define WORLD_WIDTH 896
#define WORLD_HEIGHT 414
#define WORLD_PIXELS ((size_t)WORLD_WIDTH*WORLD_HEIGHT)
static __thread NG2WorldSupportScope ng2_world_support;
static int context_valid(void){
    return ng2_world_support.pointer&&ng2_world_support.len==WORLD_PIXELS
        &&(!ng2_world_support.has_rgba||ng2_world_support.rgba_valid)
        &&(ng2_world_support.clear_scope==NG2_WORLD_CLEAR_UNKNOWN
            ||ng2_world_support.clear_scope==NG2_WORLD_CLEAR_OBSERVED_FOV_MINUS_HUD);
}
NG2WorldSupportScope ng2_world_support_enter(const uint8_t *world_observed,size_t length,int32_t clear_scope){
    NG2WorldSupportScope previous=ng2_world_support;
    ng2_world_support.pointer=world_observed;
    ng2_world_support.len=length;
    ng2_world_support.enabled=world_observed!=NULL||length!=0;
    ng2_world_support.clear_scope=clear_scope;
    ng2_world_support.world_rgba=NULL;ng2_world_support.rgba_len=ng2_world_support.rgba_stride=0;
    ng2_world_support.has_rgba=ng2_world_support.rgba_valid=0;
    return previous;
}
NG2WorldSupportScope ng2_world_support_enter_rgba(const uint8_t *world_rgba,size_t rgba_length,size_t stride,
    const uint8_t *world_observed,size_t observed_length,int32_t clear_scope){
    NG2WorldSupportScope previous=ng2_world_support_enter(world_observed,observed_length,clear_scope);
    ng2_world_support.enabled=ng2_world_support.has_rgba=1;
    ng2_world_support.world_rgba=world_rgba;
    ng2_world_support.rgba_len=rgba_length;ng2_world_support.rgba_stride=stride;
    if(world_rgba&&stride>=WORLD_WIDTH*4u&&stride<=7680u&&rgba_length==stride*WORLD_HEIGHT){
        ng2_world_support.rgba_valid=1;
        for(int y=0;y<WORLD_HEIGHT&&ng2_world_support.rgba_valid;y++)for(int x=0;x<WORLD_WIDTH;x++)
            if(world_rgba[(size_t)y*stride+(size_t)x*4+3]!=255){ng2_world_support.rgba_valid=0;break;}
    }
    return previous;
}
void ng2_world_support_leave(NG2WorldSupportScope previous){ng2_world_support=previous;}
int ng2_world_support_active(void){return ng2_world_support.enabled!=0;}
int ng2_world_pixel_observed(int32_t x,int32_t y){
    if(!ng2_world_support.enabled)return 1;
    return context_valid()&&x>=0&&x<WORLD_WIDTH&&y>=0&&y<WORLD_HEIGHT
        &&ng2_world_support.pointer[(size_t)y*WORLD_WIDTH+(size_t)x]!=0;
}
int ng2_world_roi_observed(int32_t x0,int32_t y0,int32_t x1,int32_t y1){
    if(!ng2_world_support.enabled)return 1;
    if(!context_valid()||x0<0||y0<0||x1<=x0||y1<=y0||x1>WORLD_WIDTH||y1>WORLD_HEIGHT)return 0;
    for(int32_t y=y0;y<y1;y++)
        if(memchr(ng2_world_support.pointer+(size_t)y*WORLD_WIDTH+(size_t)x0,0,(size_t)(x1-x0)))return 0;
    return 1;
}
int32_t ng2_world_support_clear_scope(void){
    return ng2_world_support.enabled&&context_valid()?ng2_world_support.clear_scope:NG2_WORLD_CLEAR_UNKNOWN;
}
const uint8_t *ng2_world_support_rgba(const uint8_t *fallback,size_t length,size_t stride){
    if(!ng2_world_support.enabled||!ng2_world_support.has_rgba)return fallback;
    return context_valid()&&ng2_world_support.rgba_len==length&&ng2_world_support.rgba_stride==stride
        ?ng2_world_support.world_rgba:NULL;
}
