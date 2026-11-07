/* Raster-host-only wrapper. Production and Runtime link the original object. */
#include "NG2Core.h"

size_t ng2_orient_rgba_real(const uint8_t *,size_t,int32_t,int32_t,int32_t,uint8_t *,size_t);
static uint64_t calls;
void ng2_raster_spy_reset(void){calls=0;}
uint64_t ng2_raster_spy_calls(void){return calls;}
size_t ng2_orient_rgba(const uint8_t *source,size_t length,int32_t width,int32_t height,
                       int32_t orientation,uint8_t *destination,size_t destination_length){
    ++calls;
    return ng2_orient_rgba_real(source,length,width,height,orientation,destination,destination_length);
}
