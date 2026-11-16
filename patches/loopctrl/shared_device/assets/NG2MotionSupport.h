/* Scoped observation support for the unchanged motion evidence arithmetic.
 * This API does not grant input authority or alter NG2Core/Scene ABI. */
#ifndef NG2_MOTION_SUPPORT_H
#define NG2_MOTION_SUPPORT_H
#include <stddef.h>
#include <stdint.h>
typedef struct {
    const uint8_t *pointer;
    size_t len;
    int32_t enabled;
} NG2MotionSupportScope;
/* The caller owns an immutable 224x104 signature-validity bitmap for this
 * thread's entire scope, including before/after and kernel dependencies.
 * NULL+0 is explicit legacy behavior. Any other malformed input rejects all
 * evidence. Always leave with the exact scope returned by enter, including
 * after failures and nested calls. Existing owner/ticket/ACK fences remain. */
NG2MotionSupportScope ng2_motion_support_enter(const uint8_t *signature_valid,size_t length);
void ng2_motion_support_leave(NG2MotionSupportScope previous);
#endif
