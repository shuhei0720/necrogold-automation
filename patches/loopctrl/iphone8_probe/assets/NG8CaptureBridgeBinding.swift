import Foundation

// Shared by the actual UITest callsite and the early Swift/ObjC-import check.
// This file adds no capture path; the service still owns qualification/tickets.
enum NG8CaptureBridgeBinding {
    static func make() -> NG8CaptureService.Bridge {
        NG8CaptureService.Bridge(prepare: { NG8CaptureBridge.prepare() },
            request: { reply, handoff in
                NG8CaptureBridge.requestJPEG(reply: reply, drained: handoff)
            })
    }
}
