import Foundation
import Dispatch

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
        let failures = serviceBoundaryChecks()
        for label in failures { print("FAIL " + label) }
        print("ASSERTIONS_FAILED \(failures.count)")
        if !failures.isEmpty { exit(1) }
    }
}

// Focused real GCD/ImageIO/filesystem boundaries; synthetic bytes/bridge only.
private final class ServiceBridgeFixture {
    private let lock = NSLock()
    private var prepares = 0
    private var requests = 0
    private var correctQueues = true
    let bytes: Data
    init(_ bytes: Data) { self.bytes = bytes }
    var count: Int { lock.lock(); defer { lock.unlock() }; return prepares + requests }
    var queuesOK: Bool { lock.lock(); defer { lock.unlock() }; return correctQueues }
    var bridge: NG8CaptureService.Bridge {
        NG8CaptureService.Bridge(prepare: {
            self.lock.lock(); self.prepares += 1
            self.correctQueues = self.correctQueues && Thread.isMainThread
            self.lock.unlock(); return true
        }, request: { reply, handoff in
            self.lock.lock(); self.requests += 1
            self.correctQueues = self.correctQueues && !Thread.isMainThread
            self.lock.unlock()
            reply(self.bytes, nil)
            handoff()
        })
    }
}

private func serviceBoundaryChecks() -> [String] {
    var failures: [String] = []
    func expect(_ value: Bool, _ label: String) { if !value { failures.append(label) } }
    let manager = FileManager.default
    let directory = manager.temporaryDirectory.resolvingSymlinksInPath()
        .appendingPathComponent("ng8-service-boundary-" + UUID().uuidString, isDirectory: true)
    defer { try? manager.removeItem(at: directory) }
    do { try manager.createDirectory(at: directory, withIntermediateDirectories: false) }
    catch { return ["fixture_private_directory"] }
    let spool = directory.appendingPathComponent("NGG2Cycles", isDirectory: true)
    let bytes = Data(base64Encoded: "/9j/4AAQSkZJRgABAQAAAQABAAD/4QAiRXhpZgAATU0AKgAAAAgAAQESAAMAAAABAAgAAAAAAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wAARCAAGAAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDmKKKK9I4T/9k=")!
    let hash = "6a3cb73d59969daf3ba88a768f226b345c57ea31eb9d22d22b0589ccacd6f2a9"
    let bridge = ServiceBridgeFixture(bytes)
    guard let service = NG8CaptureService.hostTest(mode: .iphone8CaptureOnly, bridge: bridge.bridge,
        ownerState: { _ in .active }, legacySpoolURL: spool) else { return ["fixture_service_factory"] }
    let owner = "0123abcd"
    func call(_ service: NG8CaptureService, _ method: String, _ params: [String: Any] = [:])
        -> Result<[String: Any], NG8ProbeFailure>? {
        let box = ReplyBox()
        service.handle(method: method, params: params, ownerTokenID: owner) { box.put($0) }
        let end = Date().addingTimeInterval(5)
        while box.get() == nil && Date() < end {
            _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.002))
        }
        return box.get()
    }
    func dictionary(_ reply: Result<[String: Any], NG8ProbeFailure>?) -> [String: Any]? {
        if case .success(let value)? = reply { return value }; return nil
    }
    func failure(_ reply: Result<[String: Any], NG8ProbeFailure>?, _ reason: NG8ProbeFailure) -> Bool {
        if case .failure(let value)? = reply { return value == reason }; return false
    }
    func key(_ service: NG8CaptureService, _ digit: String) -> [String: Any] {
        ["runtime_id": service.runtimeID, "probe_id": String(repeating: digit, count: 32)]
    }
    func waitReady(_ service: NG8CaptureService, _ key: [String: Any]) -> [String: Any]? {
        let end = Date().addingTimeInterval(5)
        while Date() < end {
            if let value = dictionary(call(service, "necro_capture_probe_status", key)),
               let state = value["state"] as? String,
               ["ready", "failed", "cancelled", "expired"].contains(state),
               value["draining"] as? Bool == false { return value }
            _ = RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.002))
        }
        return nil
    }
    expect(NG8CaptureService.hostTest(mode: .normal, bridge: bridge.bridge,
        ownerState: { _ in .active }, legacySpoolURL: spool) == nil, "normal_mode_producer_zero")
    let identity = key(service, "a")
    var extra = identity; extra["owner"] = owner
    expect(failure(call(service, "necro_capture_probe_start", extra), .invalidRequest) && bridge.count == 0,
           "closed_params_no_producer")
    do {
        try manager.createDirectory(at: spool, withIntermediateDirectories: false)
        try Data([1]).write(to: spool.appendingPathComponent("private-entry"), options: .withoutOverwriting)
    } catch { return failures + ["fixture_spool_setup"] }
    expect(failure(call(service, "necro_capture_probe_start", identity), .oldEvidenceBlocked) && bridge.count == 0,
           "nonempty_spool_blocks_without_capture")
    do {
        try manager.removeItem(at: spool)
        try manager.createSymbolicLink(at: spool, withDestinationURL: directory)
    } catch { return failures + ["fixture_symlink_setup"] }
    expect(failure(call(service, "necro_capture_probe_start", identity), .oldEvidenceBlocked) && bridge.count == 0,
           "below_anchor_symlink_blocks_without_capture")
    do { try manager.removeItem(at: spool) } catch { return failures + ["fixture_symlink_cleanup"] }
    let stopped = DispatchSemaphore(value: 0)
    service.setListenerActive(false) { stopped.signal() }
    expect(stopped.wait(timeout: .now() + 5) == .success, "listener_stop_completion")
    expect(failure(call(service, "necro_capture_probe_start", identity), .unavailable) && bridge.count == 0,
           "stopped_start_does_not_consume_or_capture")
    service.setListenerActive(true)
    expect(dictionary(call(service, "necro_capture_probe_start", identity))?["generation"] as? UInt64 == 1,
           "same_id_after_pre_admission_rejections")
    let ready = waitReady(service, identity)
    expect(ready?["state"] as? String == "ready" && ready?["lease_held"] as? Bool == true &&
        bridge.count == 2 && bridge.queuesOK, "actual_queues_handoff_reach_ready_once")
    var manifestParams = identity; manifestParams["mode"] = "manifest"
    let manifest = dictionary(call(service, "necro_capture_probe_results", manifestParams))
    expect(manifest?.count == 27 && manifest?["sha256"] as? String == hash &&
        manifest?["byte_length"] as? Int == bytes.count && manifest?["source_width"] as? Int == 8 &&
        manifest?["source_height"] as? Int == 6 && manifest?["exif_orientation"] as? Int == 8 &&
        manifest?["input_authorized"] as? Bool == false && manifest?["input_geometry_verified"] as? Bool == false &&
        manifest?["callback_return_verified"] as? Bool == false && manifest?["normalization_applied"] as? Bool == false &&
        manifest?["freshness_verified"] as? Bool == false && manifest?["device_capture_ns"] is NSNull,
        "original_jpeg_metadata_and_false_qualification")
    var chunkParams = identity
    chunkParams.merge(["mode": "chunk", "sha256": hash, "offset": 0, "limit": 65536]) { _, new in new }
    let chunk = dictionary(call(service, "necro_capture_probe_results", chunkParams))
    expect(chunk?.count == 10 && chunk?["chunk_bytes"] as? Int == bytes.count &&
        ((chunk?["data_base64"] as? String).flatMap { Data(base64Encoded: $0) }) == bytes,
        "full_original_chunk_exact_without_reencode")
    let cancelled = dictionary(call(service, "necro_capture_probe_cancel", identity))
    expect(cancelled?["state"] as? String == "cancelled" && cancelled?["cancel_epoch"] as? UInt64 == 1 &&
        cancelled?["lease_held"] as? Bool == false && cancelled?["runtime_id"] as? String == service.runtimeID,
        "cancel_releases_artifact_without_runtime_reset")
    _ = call(service, "necro_capture_probe_start", identity)
    expect(bridge.count == 2, "cancelled_id_never_recaptures")
    let badBridge = ServiceBridgeFixture(Data([0, 1, 2]))
    guard let bad = NG8CaptureService.hostTest(mode: .iphone8CaptureOnly, bridge: badBridge.bridge,
        ownerState: { _ in .active }, legacySpoolURL: spool) else { return failures + ["fixture_bad_service"] }
    let badKey = key(bad, "b")
    _ = call(bad, "necro_capture_probe_start", badKey)
    let rejected = waitReady(bad, badKey)
    expect(rejected?["state"] as? String == "failed" && rejected?["failure_code"] as? String == "jpeg_invalid" &&
        rejected?["lease_held"] as? Bool == false &&
        failure(call(bad, "necro_capture_probe_results", badKey.merging(["mode": "manifest"]) { _, new in new }), .jpegInvalid),
        "invalid_jpeg_never_exports")
    return failures
}
