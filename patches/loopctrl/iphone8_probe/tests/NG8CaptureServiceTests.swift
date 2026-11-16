import Foundation

// Synthetic host boundary only. No ObjC bridge or phone API is linked.
private final class ReplyBox {
    private let lock = NSLock()
    private var stored: Result<[String: Any], NG8ProbeFailure>?
    func put(_ value: Result<[String: Any], NG8ProbeFailure>) {
        lock.lock(); stored = value; lock.unlock()
    }
    func get() -> Result<[String: Any], NG8ProbeFailure>? {
        lock.lock(); defer { lock.unlock() }; return stored
    }
}

@main
private enum NG8CaptureServiceTests {
    static func main() {
        guard Array(CommandLine.arguments.dropFirst()) == ["service_status_runtime"] else {
            print("FIXTURE_ARGUMENT_ERROR"); exit(2)
        }
        var bridgeCalls = 0
        let bridge = NG8CaptureService.Bridge(prepare: { bridgeCalls += 1; return true },
            request: { _, _ in bridgeCalls += 1 })
        let missingSpool = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("ng8-service-" + UUID().uuidString, isDirectory: true)
            .appendingPathComponent("NGG2Cycles", isDirectory: true)
        guard let service = NG8CaptureService.hostTest(mode: .iphone8CaptureOnly, bridge: bridge,
            ownerState: { _ in .active }, legacySpoolURL: missingSpool) else {
            print("FIXTURE_ERROR service_factory"); exit(2)
        }
        let box = ReplyBox()
        service.handle(method: "necro_capture_probe_status", params: [:], ownerTokenID: "0123abcd") {
            box.put($0)
        }
        let end = Date().addingTimeInterval(5)
        while box.get() == nil && Date() < end {
            _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.005))
        }
        guard let reply = box.get() else { print("FIXTURE_ERROR service_reply_timeout"); exit(2) }
        print("CASE service_status_runtime")
        let fields: Set<String> = ["schema", "service_mode", "runtime_id", "old_evidence_gate",
            "probe_id", "generation", "cancel_epoch", "state", "failure_code", "clock_id",
            "accepted_ns", "deadline_ns", "request_start_ns", "callback_body_handoff_ns",
            "callback_return_verified", "ready_expiry_ns", "draining", "lease_held"]
        let correct: Bool
        switch reply {
        case .failure: correct = false
        case .success(let result):
            correct = Set(result.keys) == fields &&
                result["schema"] as? String == "ngg2-capture-probe-v1" &&
                result["service_mode"] as? String == "iphone8-capture-only-v1" &&
                result["runtime_id"] as? String == service.runtimeID &&
                NG8ProbeWire.hex(service.runtimeID, count: 32) &&
                result["old_evidence_gate"] as? String == "clean" &&
                result["callback_return_verified"] as? Bool == false &&
                result["draining"] as? Bool == false && result["lease_held"] as? Bool == false &&
                result["probe_id"] is NSNull && bridgeCalls == 0
        }
        if !correct {
            print("FAIL service_status_runtime")
            print("ASSERTIONS_FAILED 1")
            exit(1)
        }
        print("ASSERTIONS_FAILED 0")
    }
}
