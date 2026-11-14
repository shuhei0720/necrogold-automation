#include "ngg2_runtime099_fixture.h"
#include <pthread.h>
#include <string.h>

/* Only the host object renames the public getter to this alias. Production
 * builds never compile this source or the symbol-renaming compiler option. */
void ng2_controller_stop_detail_real(const NG2Controller *, NG2ControllerStopDetail *);
static pthread_mutex_t fixture099_gate = PTHREAD_MUTEX_INITIALIZER;
static int fixture099_override_enabled;
static NG2ControllerStopDetail fixture099_override;

void ng2_fixture099_stop_override(int32_t enabled, const NG2ControllerStopDetail *value) {
    pthread_mutex_lock(&fixture099_gate);
    fixture099_override_enabled = enabled && value;
    if(value)fixture099_override=*value;
    else memset(&fixture099_override,0,sizeof(fixture099_override));
    pthread_mutex_unlock(&fixture099_gate);
}
void ng2_controller_stop_detail(const NG2Controller *controller, NG2ControllerStopDetail *out) {
    ng2_controller_stop_detail_real(controller,out);
    pthread_mutex_lock(&fixture099_gate);
    if(out&&fixture099_override_enabled)*out=fixture099_override;
    pthread_mutex_unlock(&fixture099_gate);
}
