import Foundation
import ImageIO
import CryptoKit

// Isolated synthetic host contracts, not an iPhone/drain/production acceptance.
// Compile with NG8CaptureProbe.swift using -parse-as-library. The default case
// must compile and fail assertions against the unavailable TDD baseline.
private var failedAssertions = 0
private func expect(_ value: Bool, _ label: String) {
    if !value { failedAssertions += 1; print("FAIL \(label)") }
}
private func value<T>(_ result: Result<T, NG8ProbeFailure>) -> T? {
    if case .success(let item) = result { return item }; return nil
}
private func failure<T>(_ result: Result<T, NG8ProbeFailure>) -> NG8ProbeFailure? {
    if case .failure(let item) = result { return item }; return nil
}

private enum Fixture {
    // Public Pillow-generated 8x6 RGB JPEG, EXIF8. No phone image or secret.
    static let jpeg = Data(base64Encoded: "/9j/4AAQSkZJRgABAQAAAQABAAD/4QAiRXhpZgAATU0AKgAAAAgAAQESAAMAAAABAAgAAAAAAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wAARCAAGAAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDmKKKK9I4T/9k=")!
    static let sha = "6a3cb73d59969daf3ba88a768f226b345c57ea31eb9d22d22b0589ccacd6f2a9"
    static let runtime = String(repeating: "a", count: 32)
    static let key = NG8ProbeKey(runtimeID: runtime, probeID: String(repeating: "b", count: 32))
    static let owner = NG8ProbeOwner(tokenIdentity: "synthetic-authorized-owner")
}

private final class Clock: NG8ProbeClock {
    var nowNs: UInt64 = 1_000_000
    let clockID = "synthetic-owned-monotonic-v1"
}
private final class Watch: NG8ProbeWatch {
    let deadline: UInt64
    let fired: () -> Void
    var cancelled = false
    var delivered = false
    init(_ deadline: UInt64, _ fired: @escaping () -> Void) { self.deadline = deadline; self.fired = fired }
    func cancel() { cancelled = true }
}
private final class Scheduler: NG8ProbeScheduler {
    struct Job { let body: () -> Void; let returned: () -> Void }
    var main: [Job] = [], worker: [Job] = []
    var mainReturns: [() -> Void] = [], workerReturns: [() -> Void] = []
    var watches: [Watch] = []
    func enqueueMain(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        main.append(Job(body: body, returned: returned))
    }
    func enqueueWorker(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        worker.append(Job(body: body, returned: returned))
    }
    func watch(at deadlineNs: UInt64, fired: @escaping () -> Void) -> NG8ProbeWatch {
        let item = Watch(deadlineNs, fired); watches.append(item); return item
    }
    func runMain(emitReturn: Bool = true) {
        guard !main.isEmpty else { return }
        let job = main.removeFirst(); job.body()
        if emitReturn { job.returned() } else { mainReturns.append(job.returned) }
    }
    func runWorker(emitReturn: Bool = true) {
        guard !worker.isEmpty else { return }
        let job = worker.removeFirst(); job.body()
        if emitReturn { job.returned() } else { workerReturns.append(job.returned) }
    }
    func returnMain() { if !mainReturns.isEmpty { mainReturns.removeFirst()() } }
    func returnWorker() { if !workerReturns.isEmpty { workerReturns.removeFirst()() } }
    func fire(at now: UInt64) {
        for item in watches where !item.cancelled && !item.delivered && item.deadline <= now {
            item.delivered = true; item.fired()
        }
    }
}
private final class Driver: NG8ProbeCaptureDriver {
    var prepareCount = 0, requestCount = 0
    var beforePrepare: (() -> Void)?
    var synchronousReply = false
    var reply: ((Result<Data, NG8ProbeFailure>) -> Void)?
    var drained: (() -> Void)?
    var tickets: [NG8ProbeTicket] = []
    func prepare(_ ticket: NG8ProbeTicket) -> Result<Void, NG8ProbeFailure> {
        prepareCount += 1; beforePrepare?(); return .success(())
    }
    func request(_ ticket: NG8ProbeTicket,
                 reply: @escaping (Result<Data, NG8ProbeFailure>) -> Void,
                 drained: @escaping () -> Void) {
        requestCount += 1; tickets.append(ticket); self.reply = reply; self.drained = drained
        if synchronousReply { reply(.success(Fixture.jpeg)); drained() }
    }
    func deliver(_ result: Result<Data, NG8ProbeFailure> = .success(Fixture.jpeg)) { reply?(result) }
    func finishBridge() { drained?() }
}
private final class OwnerBox { var state: NG8ProbeOwnerState = .active }
private final class EvidenceBox { var state: NG8ProbeOldEvidence = .clean }
private final class Metadata {
    var inspectCount = 0, hashCount = 0
    // ImageIO metadata only. No CGImage/raster decode or re-encoding API.
    func inspect(_ data: Data) -> Result<NG8ProbeJPEGMetadata, NG8ProbeFailure> {
        inspectCount += 1
        guard data.count <= NG8ProbeLimits.jpegBytes,
              let source = CGImageSourceCreateWithData(data as CFData, nil),
              CGImageSourceGetCount(source) == 1,
              let type = CGImageSourceGetType(source), type as String == "public.jpeg",
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int,
              width > 0, height > 0, width <= 4096, height <= 4096,
              width * height <= 8_000_000 else { return .failure(.metadataInvalid) }
        var orientation: Int?
        if let entry = properties[kCGImagePropertyOrientation] {
            guard let number = entry as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  number.doubleValue == Double(number.intValue), (1...8).contains(number.intValue)
            else { return .failure(.metadataInvalid) }
            orientation = number.intValue
        }
        return .success(NG8ProbeJPEGMetadata(width: width, height: height, exifOrientation: orientation))
    }
    func hash(_ data: Data) -> String {
        hashCount += 1
        return SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}
private final class Harness {
    let clock: Clock
    let scheduler: Scheduler
    let driver: Driver
    let owner: OwnerBox
    let evidence: EvidenceBox
    let metadata: Metadata
    let probe: NG8CaptureProbe
    init(qualified: Bool? = true) {
        let clock = Clock(), scheduler = Scheduler(), driver = Driver()
        let owner = OwnerBox(), evidence = EvidenceBox(), metadata = Metadata()
        self.clock = clock; self.scheduler = scheduler; self.driver = driver
        self.owner = owner; self.evidence = evidence; self.metadata = metadata
        if let qualified = qualified {
            probe = NG8CaptureProbe(qualified: qualified, runtimeID: Fixture.runtime,
                clock: clock, scheduler: scheduler, driver: driver,
                ownerState: { [owner] _ in owner.state }, oldEvidenceGate: { [evidence] in evidence.state },
                inspectJPEG: metadata.inspect, sha256: metadata.hash)
        } else {
            probe = NG8CaptureProbe(runtimeID: Fixture.runtime,
                clock: clock, scheduler: scheduler, driver: driver,
                ownerState: { [owner] _ in owner.state }, oldEvidenceGate: { [evidence] in evidence.state },
                inspectJPEG: metadata.inspect, sha256: metadata.hash)
        }
    }
    func start() {
        expect(value(probe.start(Fixture.key, owner: Fixture.owner)) != nil, "qualified_start_is_accepted")
    }
    func complete() {
        scheduler.runMain(); scheduler.runWorker(); driver.deliver(); driver.finishBridge()
    }
    var status: NG8ProbeStatus? { value(probe.status(Fixture.key, owner: Fixture.owner)) }
}

private func qualifiedCapture() {
    let h = Harness()
    h.start(); h.complete()
    expect(h.driver.requestCount == 1, "qualified_new_id_one_capture")
    expect(h.status?.state == .ready && h.status?.draining == false && h.status?.leaseHeld == true,
           "qualified_capture_ready_keeps_raw_lease")
    let manifest = value(h.probe.manifest(Fixture.key, owner: Fixture.owner))
    expect(manifest?.sha256 == Fixture.sha && manifest?.byteLength == 668 &&
           manifest?.metadata == NG8ProbeJPEGMetadata(width: 8, height: 6, exifOrientation: 8),
           "original_jpeg_hash_length_and_exif8_metadata")
    let chunk = value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                   sha256: Fixture.sha, offset: 0, limit: 65536))
    expect(chunk?.data == Fixture.jpeg, "ready_chunk_exact_original_bytes")
    expect(manifest?.inputAuthorized == false && manifest?.inputGeometryVerified == false &&
           manifest?.normalizationApplied == false && manifest?.freshnessVerified == false &&
           manifest?.deviceCaptureNs == nil && !h.probe.inputAuthorized,
           "capture_never_mints_input_geometry_or_freshness")
    expect(h.metadata.inspectCount == 1 && h.metadata.hashCount == 1,
           "immutable_original_inspected_and_hashed_once")
}

private func defaultUnqualified() {
    let h = Harness(qualified: nil)
    expect(!h.probe.qualified && failure(h.probe.start(Fixture.key, owner: Fixture.owner)) == .notAvailable,
           "constructor_without_qualification_cannot_capture")
    expect(h.driver.prepareCount == 0 && h.driver.requestCount == 0 && h.scheduler.main.isEmpty,
           "unqualified_schedules_nothing")
}

private func queuedMainDeadline() {
    let h = Harness(); h.start()
    expect(h.scheduler.watches.count == 1, "watchdog_armed_before_queued_main")
    h.clock.nowNs += NG8ProbeLimits.captureDeadlineNs
    h.scheduler.fire(at: h.clock.nowNs)
    expect(h.status?.failure == .deadline && h.status?.draining == true && h.status?.leaseHeld == true,
           "deadline_does_not_release_unreturned_main")
    h.scheduler.runMain()
    expect(h.driver.prepareCount == 0 && h.driver.requestCount == 0,
           "late_main_cannot_prepare_or_request")
    expect(h.status?.failure == .deadline && h.status?.leaseHeld == false,
           "deadline_reason_survives_actual_main_return")
}

private func cancelAndDrainFence() {
    let h = Harness(); h.start(); h.scheduler.runMain(); h.scheduler.runWorker(emitReturn: false)
    expect(h.driver.requestCount == 1, "cancel_fixture_has_real_fake_request")
    let cancelled = value(h.probe.cancel(Fixture.key, owner: Fixture.owner))
    expect(cancelled?.failure == .cancelled && cancelled?.leaseHeld == true,
           "cancel_latches_before_callback_and_worker_exit")
    h.driver.deliver(); h.driver.finishBridge()
    expect(h.status?.failure == .cancelled && h.status?.leaseHeld == true,
           "bridge_drain_does_not_replace_worker_return")
    h.scheduler.returnWorker()
    expect(h.status?.failure == .cancelled && h.status?.leaseHeld == false,
           "late_success_cannot_replace_cancel_reason")
    expect(value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
           "cancelled_raw_never_exports")
    let again = value(h.probe.cancel(Fixture.key, owner: Fixture.owner))
    expect(again?.cancelEpoch == cancelled?.cancelEpoch && cancelled?.cancelEpoch != nil,
           "idempotent_cancel_advances_epoch_once")
}

private func synchronousReplyFence() {
    let h = Harness(); h.driver.synchronousReply = true; h.start(); h.scheduler.runMain()
    h.scheduler.runWorker(emitReturn: false)
    expect(h.driver.requestCount == 1 && h.status?.state != .ready && h.status?.leaseHeld == true,
           "synchronous_bridge_reply_cannot_skip_worker_return")
    h.scheduler.returnWorker()
    expect(h.status?.state == .ready, "ready_after_real_worker_and_bridge_finish")
    h.driver.deliver(); h.driver.finishBridge()
    expect(h.metadata.inspectCount == 1 && h.metadata.hashCount == 1 && h.driver.requestCount == 1,
           "duplicate_candidate_cannot_reconsume_or_recapture")
}

private func cancelDuringPrepare() {
    let h = Harness()
    h.driver.beforePrepare = { _ = h.probe.cancel(Fixture.key, owner: Fixture.owner) }
    h.start(); h.scheduler.runMain(); h.scheduler.runWorker()
    expect(h.driver.prepareCount == 1 && h.driver.requestCount == 0,
           "cancel_during_owned_prepare_prevents_request")
    expect(h.status?.failure == .cancelled && h.status?.leaseHeld == false,
           "prepare_actual_return_closes_cancelled_lease")
}

private func revokedOwnerLateReply() {
    let h = Harness(); h.start(); h.scheduler.runMain(); h.scheduler.runWorker()
    expect(h.driver.requestCount == 1, "revoke_fixture_has_one_request")
    h.owner.state = .inactive; h.probe.ownerChanged()
    h.driver.deliver(.failure(.captureFailed)); h.driver.finishBridge()
    expect(h.status?.failure == .ownerInactive && h.status?.leaseHeld == false,
           "late_callback_failure_cannot_replace_owner_reason")
    expect(value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
           sha256: Fixture.sha, offset: 0, limit: 64)) == nil, "revoked_owner_exports_nothing")
}

private func oldEvidenceAndRuntime() {
    let h = Harness(); h.evidence.state = .blocked
    expect(failure(h.probe.start(Fixture.key, owner: Fixture.owner)) == .oldEvidenceBlocked,
           "old_spool_presence_blocks_without_recovery")
    expect(h.driver.prepareCount == 0 && h.driver.requestCount == 0, "old_spool_capture_zero")
    h.evidence.state = .clean
    let oldRuntime = NG8ProbeKey(runtimeID: String(repeating: "c", count: 32), probeID: Fixture.key.probeID)
    expect(failure(h.probe.start(oldRuntime, owner: Fixture.owner)) == .runtimeMismatch,
           "old_runtime_cannot_create_new_capture")
}

private func closedParams() {
    let valid: [String: Any] = ["runtime_id": Fixture.runtime, "probe_id": Fixture.key.probeID]
    expect(value(NG8ProbeWire.decode(method: "necro_capture_probe_start", params: valid)) == .start(Fixture.key),
           "closed_start_schema_accepts_only_valid_identity")
    var actor = valid; actor["_necro_probe_owner"] = "caller-forgery"
    var qualified = valid; qualified["qualified"] = true
    var booleanRange = valid
    booleanRange.merge(["mode": "chunk", "sha256": Fixture.sha, "offset": 0, "limit": true]) { _, new in new }
    for bad in [actor, qualified] {
        expect(failure(NG8ProbeWire.decode(method: "necro_capture_probe_start", params: bad)) == .invalidRequest,
               "wire_cannot_supply_owner_or_qualification")
    }
    expect(failure(NG8ProbeWire.decode(method: "necro_capture_probe_results", params: booleanRange)) == .invalidRequest,
           "boolean_chunk_limit_is_not_integer")
}

private func ttlAndChunkBounds() {
    let h = Harness(); h.start(); h.complete()
    expect(h.status?.state == .ready, "ttl_fixture_has_ready_original")
    expect(failure(h.probe.chunk(Fixture.key, owner: Fixture.owner,
           sha256: String(repeating: "0", count: 64), offset: 0, limit: 64)) == .invalidRequest,
           "wrong_hash_never_selects_different_artifact")
    expect(failure(h.probe.chunk(Fixture.key, owner: Fixture.owner,
           sha256: Fixture.sha, offset: UInt64.max, limit: 65536)) == .invalidRequest,
           "chunk_offset_overflow_rejected")
    let expiry = h.status?.readyExpiryNs ?? h.clock.nowNs
    h.clock.nowNs = expiry; h.scheduler.fire(at: expiry)
    expect(h.status?.failure == .expired && h.status?.leaseHeld == false,
           "ready_ttl_discards_raw_at_fixed_expiry")
    expect(value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
           "expired_artifact_cannot_export_or_extend_ttl")
}

@main
private enum NG8CaptureProbeHostTests {
    static func main() {
        let cases: [(String, () -> Void)] = [
            ("qualified_capture", qualifiedCapture), ("default_unqualified", defaultUnqualified),
            ("queued_main_deadline", queuedMainDeadline), ("cancel_drain_fence", cancelAndDrainFence),
            ("synchronous_reply_fence", synchronousReplyFence), ("prepare_cancel", cancelDuringPrepare),
            ("revoked_owner", revokedOwnerLateReply), ("old_evidence_runtime", oldEvidenceAndRuntime),
            ("closed_params", closedParams), ("ttl_chunk_bounds", ttlAndChunkBounds),
        ]
        let args = Array(CommandLine.arguments.dropFirst())
        let selected = args.isEmpty ? ["qualified_capture"] : (args == ["all"] ? cases.map { $0.0 } : args)
        guard selected.allSatisfy({ name in cases.contains { $0.0 == name } }) else {
            print("FIXTURE_ARGUMENT_ERROR"); exit(2)
        }
        for (name, body) in cases where selected.contains(name) {
            print("CASE \(name)"); body()
        }
        print("ASSERTIONS_FAILED \(failedAssertions)")
        exit(failedAssertions == 0 ? 0 : 1)
    }
}
