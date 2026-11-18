/* TEST115 host instrumentation only. The production Controller object is
 * compiled with ng2_controller_begin renamed to the function below. This
 * wrapper returns its actual result unchanged, then lets the host advance
 * its own clock. The exact old/new Runtime sees the same original C symbol.
 * No Controller field, Scene, permission, or classifier result is supplied. */
#include "ngg2/NG2Controller.h"

typedef void (*NG2Begin115Callback)(void *,uint64_t,uint64_t,int32_t);
static NG2Begin115Callback begin115_callback;
static void *begin115_context;

int ng2_controller_begin115_actual(NG2Controller *,uint64_t,uint64_t,int32_t,int32_t,int32_t);

void ng2_fixture_begin115_install(NG2Begin115Callback callback,void *context){
    begin115_callback=callback;begin115_context=context;
}
int ng2_controller_begin(NG2Controller *controller,uint64_t id,uint64_t now,
    int32_t foreground,int32_t locked,int32_t owner){
    int result=ng2_controller_begin115_actual(controller,id,now,foreground,locked,owner);
    if(begin115_callback)begin115_callback(begin115_context,id,now,result);
    return result;
}
