#ifndef NGG2_RUNTIME099_FIXTURE_H
#define NGG2_RUNTIME099_FIXTURE_H
#include "NG2Controller.h"
/* Read-only diagnostic POD override for Runtime snapshot/pin integration.
 * Actual C getter semantics are checked separately by public C units. */
void ng2_fixture099_stop_override(int32_t enabled, const NG2ControllerStopDetail *);
#endif
