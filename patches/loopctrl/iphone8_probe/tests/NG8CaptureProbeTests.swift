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
    var main: [Job] = [], worker: [Job] = [], coordinator: [Job] = []
    var mainReturns: [() -> Void] = [], workerReturns: [() -> Void] = [], coordinatorReturns: [() -> Void] = []
    var watches: [Watch] = []
    func enqueueMain(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        main.append(Job(body: body, returned: returned))
    }
    func enqueueWorker(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        worker.append(Job(body: body, returned: returned))
    }
    func enqueueCoordinator(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        coordinator.append(Job(body: body, returned: returned))
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
    func runCoordinator(emitReturn: Bool = true) {
        guard !coordinator.isEmpty else { return }
        let job = coordinator.removeFirst(); job.body()
        if emitReturn { job.returned() } else { coordinatorReturns.append(job.returned) }
    }
    func returnCoordinator() { if !coordinatorReturns.isEmpty { coordinatorReturns.removeFirst()() } }
    func pumpCoordinator() {
        var remaining = 64
        while !coordinator.isEmpty && remaining > 0 { runCoordinator(); remaining -= 1 }
        if !coordinator.isEmpty { print("FIXTURE_ERROR coordinator_queue_not_bounded"); exit(2) }
    }
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
    var forced: Result<NG8ProbeJPEGMetadata, NG8ProbeFailure>?
    // ImageIO metadata only. No CGImage/raster decode or re-encoding API.
    func inspect(_ data: Data) -> Result<NG8ProbeJPEGMetadata, NG8ProbeFailure> {
        inspectCount += 1
        if let forced = forced { return forced }
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
    func complete(_ bytes: Data = Fixture.jpeg) {
        scheduler.runMain(); scheduler.runWorker(); driver.deliver(.success(bytes)); driver.finishBridge()
        scheduler.pumpCoordinator()
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
    h.scheduler.pumpCoordinator()
    expect(h.status?.failure == .deadline && h.status?.draining == true && h.status?.leaseHeld == true,
           "deadline_does_not_release_unreturned_main")
    h.scheduler.runMain()
    h.scheduler.pumpCoordinator()
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
    h.scheduler.pumpCoordinator()
    expect(h.status?.failure == .cancelled && h.status?.leaseHeld == true,
           "bridge_drain_does_not_replace_worker_return")
    h.scheduler.returnWorker()
    h.scheduler.pumpCoordinator()
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
    h.scheduler.pumpCoordinator()
    expect(h.driver.requestCount == 1 && h.status?.state != .ready && h.status?.leaseHeld == true,
           "synchronous_bridge_reply_cannot_skip_worker_return")
    h.scheduler.returnWorker()
    h.scheduler.pumpCoordinator()
    expect(h.status?.state == .ready, "ready_after_real_worker_and_bridge_finish")
    h.driver.deliver(); h.driver.finishBridge()
    h.scheduler.pumpCoordinator()
    expect(h.metadata.inspectCount == 1 && h.metadata.hashCount == 1 && h.driver.requestCount == 1,
           "duplicate_candidate_cannot_reconsume_or_recapture")
}

private func cancelDuringPrepare() {
    let h = Harness()
    h.driver.beforePrepare = { _ = h.probe.cancel(Fixture.key, owner: Fixture.owner) }
    h.start(); h.scheduler.runMain(); h.scheduler.runWorker()
    h.scheduler.pumpCoordinator()
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
    h.scheduler.pumpCoordinator()
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
    h.scheduler.pumpCoordinator()
    expect(h.status?.failure == .expired && h.status?.leaseHeld == false,
           "ready_ttl_discards_raw_at_fixed_expiry")
    expect(value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
           "expired_artifact_cannot_export_or_extend_ttl")
}

// Additional pre-implementation Red cases. Setup deliberately does not assert
// generic admission first: each selector's first FAIL identifies its own
// contract rather than merely repeating qualified_start_is_accepted.
private func beginUnchecked(_ h: Harness, key: NG8ProbeKey = Fixture.key) {
    _ = h.probe.start(key, owner: Fixture.owner)
}
private func isTerminalOrConsumed(_ result: Result<NG8ProbeStatus, NG8ProbeFailure>,
                                 state: NG8ProbeState) -> Bool {
    failure(result) == .consumedID || value(result)?.state == state
}

private func idBudgetAndHistory() {
    let h = Harness()
    var generations: [UInt64] = []
    var keys: [NG8ProbeKey] = []
    for number in 1...128 {
        let key = NG8ProbeKey(runtimeID: Fixture.runtime,
                             probeID: String(format: "%032llx", UInt64(number)))
        keys.append(key)
        if let generation = value(h.probe.start(key, owner: Fixture.owner))?.generation {
            generations.append(generation)
        }
        _ = h.probe.cancel(key, owner: Fixture.owner)
        h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    }
    expect(generations == (1...128).map { UInt64($0) }, "accepted_generation_1_through_128")
    let next = NG8ProbeKey(runtimeID: Fixture.runtime, probeID: String(repeating: "d", count: 32))
    expect(failure(h.probe.start(next, owner: Fixture.owner)) == .limitReached,
           "accepted_129th_new_id_hits_fixed_limit")
    expect(keys.prefix(64).allSatisfy {
        failure(h.probe.status($0, owner: Fixture.owner)) == .consumedID
    }, "first_64_terminal_records_retired_to_tombstones")
    expect(keys.suffix(64).allSatisfy {
        value(h.probe.status($0, owner: Fixture.owner))?.state == .cancelled
    }, "last_64_terminal_records_remain_image_free_cached")
    expect(failure(h.probe.start(keys[0], owner: Fixture.owner)) == .consumedID &&
           h.driver.requestCount == 0, "retired_id_never_recaptures_or_resets_generation")
}

private func sameIDCached() {
    let h = Harness(); beginUnchecked(h); h.complete()
    let repeated = value(h.probe.start(Fixture.key, owner: Fixture.owner))
    h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    expect(repeated?.state == .ready && h.driver.requestCount == 1,
           "same_ready_id_returns_cached_without_recapture")
    expect(h.metadata.inspectCount == 1 && h.metadata.hashCount == 1,
           "same_ready_id_does_not_rehash_or_reinspect")
}

private func sameIDAfterCancel() {
    let h = Harness(); beginUnchecked(h); h.scheduler.runMain(); h.scheduler.runWorker()
    _ = h.probe.cancel(Fixture.key, owner: Fixture.owner)
    h.driver.deliver(); h.driver.finishBridge(); h.scheduler.pumpCoordinator()
    let repeated = h.probe.start(Fixture.key, owner: Fixture.owner)
    h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    expect(isTerminalOrConsumed(repeated, state: .cancelled) && h.driver.requestCount == 1,
           "cancelled_same_id_is_consumed_without_recapture")
    expect(value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
           "cancelled_same_id_cannot_restore_discarded_bytes")
}

private func sameIDAfterTTL() {
    let h = Harness(); beginUnchecked(h); h.complete()
    let ready = h.status
    let expiry = ready?.readyExpiryNs ?? h.clock.nowNs
    h.clock.nowNs = expiry; h.scheduler.fire(at: expiry); h.scheduler.pumpCoordinator()
    let repeated = h.probe.start(Fixture.key, owner: Fixture.owner)
    h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    expect(isTerminalOrConsumed(repeated, state: .expired) && h.driver.requestCount == 1,
           "expired_same_id_is_consumed_without_recapture")
    expect(ready?.readyExpiryNs == 1_000_000 + NG8ProbeLimits.artifactTTLNs &&
           h.status?.readyExpiryNs == ready?.readyExpiryNs,
           "artifact_expiry_is_fixed_from_ready_and_never_extended")
}

private func otherOwnerSameID() {
    let h = Harness(); beginUnchecked(h); h.complete()
    let foreign = NG8ProbeOwner(tokenIdentity: "synthetic-other-active-owner")
    let start = h.probe.start(Fixture.key, owner: foreign)
    let status = h.probe.status(Fixture.key, owner: foreign)
    let cancel = h.probe.cancel(Fixture.key, owner: foreign)
    let manifest = h.probe.manifest(Fixture.key, owner: foreign)
    let chunk = h.probe.chunk(Fixture.key, owner: foreign, sha256: Fixture.sha, offset: 0, limit: 64)
    h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    expect(value(start) == nil && value(status) == nil && value(cancel) == nil &&
           value(manifest) == nil && value(chunk) == nil && h.driver.requestCount == 1,
           "foreign_owner_same_id_gets_no_state_bytes_cancel_or_recapture")
    expect(h.status?.state == .ready &&
           value(h.probe.manifest(Fixture.key, owner: Fixture.owner))?.sha256 == Fixture.sha,
           "foreign_owner_cannot_destroy_authorized_owner_artifact")
}

private func busyIDNotConsumed() {
    let h = Harness(); beginUnchecked(h)
    let second = NG8ProbeKey(runtimeID: Fixture.runtime, probeID: String(repeating: "c", count: 32))
    let busy = h.probe.start(second, owner: Fixture.owner)
    expect(failure(busy) == .busyProbe, "busy_new_id_rejects_without_consuming_id")
    _ = h.probe.cancel(Fixture.key, owner: Fixture.owner)
    h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
    let accepted = value(h.probe.start(second, owner: Fixture.owner))
    expect(accepted?.generation == 2, "previously_busy_id_can_be_accepted_after_real_drain")
}

private enum OwnerBoundary { case prepare, request, commit, export }
private func ownerGate(_ state: NG8ProbeOwnerState, name: String, at boundary: OwnerBoundary) {
    let h = Harness(); beginUnchecked(h)
    switch boundary {
    case .prepare:
        h.owner.state = state
        h.scheduler.runMain(); h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
        expect(h.status?.failure == .ownerInactive && h.driver.prepareCount == 0 &&
               h.driver.requestCount == 0, "\(name)_before_prepare_refuses_owned_job")
    case .request:
        h.scheduler.runMain(); h.owner.state = state
        h.scheduler.runWorker(); h.scheduler.pumpCoordinator()
        expect(h.status?.failure == .ownerInactive && h.driver.prepareCount == 1 &&
               h.driver.requestCount == 0, "\(name)_before_request_refuses_new_capture")
    case .commit:
        h.scheduler.runMain(); h.scheduler.runWorker(); h.owner.state = state
        h.driver.deliver(); h.driver.finishBridge(); h.scheduler.pumpCoordinator()
        expect(h.status?.failure == .ownerInactive && h.driver.requestCount == 1 &&
               value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
               "\(name)_before_commit_cannot_publish_candidate")
    case .export:
        h.complete(); h.owner.state = state
        expect(value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil &&
               value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                  sha256: Fixture.sha, offset: 0, limit: 64)) == nil &&
               h.driver.requestCount == 1 && h.status != nil,
               "\(name)_before_export_returns_no_payload")
    }
}

private func chunkRanges() {
    let h = Harness(); beginUnchecked(h); h.complete()
    let last = value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                  sha256: Fixture.sha, offset: 660, limit: 65536))
    expect(last?.data == Data(Fixture.jpeg.suffix(8)) && last?.offset == 660,
           "chunk_final_short_returns_only_remaining_bytes")
    let single = value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                    sha256: Fixture.sha, offset: 667, limit: 1))
    expect(single?.data == Data(Fixture.jpeg.suffix(1)), "last_byte_limit_one_is_valid")
    for limit in [-1, 0, 65537, Int.max] {
        expect(failure(h.probe.chunk(Fixture.key, owner: Fixture.owner,
               sha256: Fixture.sha, offset: 0, limit: limit)) == .invalidRequest,
               "chunk_nonpositive_or_overlimit_rejected")
    }
    for offset in [UInt64(668), UInt64(669), UInt64.max] {
        expect(failure(h.probe.chunk(Fixture.key, owner: Fixture.owner,
               sha256: Fixture.sha, offset: offset, limit: 65536)) == .invalidRequest,
               "chunk_eof_outside_or_overflow_rejected")
    }
    expect(failure(h.probe.chunk(Fixture.key, owner: Fixture.owner,
           sha256: String(repeating: "0", count: 64), offset: 0, limit: 1)) == .invalidRequest,
           "chunk_hash_cannot_select_other_bytes")
}

private func wireChunkRanges() {
    let valid: [String: Any] = ["runtime_id": Fixture.runtime, "probe_id": Fixture.key.probeID,
        "mode": "chunk", "sha256": Fixture.sha, "offset": 0, "limit": 65536]
    expect(value(NG8ProbeWire.decode(method: "necro_capture_probe_results", params: valid)) ==
           .chunk(Fixture.key, sha256: Fixture.sha, offset: 0, limit: 65536),
           "wire_chunk_max_count_accepts_integer_limit")
    let badOffsets: [Any] = [-1, true, 0.0, Double.nan, "0"]
    for offset in badOffsets {
        var bad = valid; bad["offset"] = offset
        expect(failure(NG8ProbeWire.decode(method: "necro_capture_probe_results", params: bad)) == .invalidRequest,
               "wire_offset_negative_boolean_fractional_or_text_rejected")
    }
    let badLimits: [Any] = [-1, 0, 65537, true, 1.0, "1"]
    for limit in badLimits {
        var bad = valid; bad["limit"] = limit
        expect(failure(NG8ProbeWire.decode(method: "necro_capture_probe_results", params: bad)) == .invalidRequest,
               "wire_limit_type_and_range_rejected")
    }
    for field in ["owner", "actor", "qualified", "generation", "cancel_epoch"] {
        var bad = valid; bad[field] = true
        expect(failure(NG8ProbeWire.decode(method: "necro_capture_probe_results", params: bad)) == .invalidRequest,
               "wire_extra_authority_or_cursor_field_rejected")
    }
}

private func jpegOrientation(_ orientation: Int?) -> Data {
    var bytes = [UInt8](Fixture.jpeg)
    // Fixed public fixture's APP1 is 20..<56; big-endian SHORT value is 48..<50.
    guard bytes.count == 668, Array(bytes[20..<24]) == [255, 225, 0, 34],
          Array(bytes[48..<50]) == [0, 8] else {
        print("FIXTURE_ERROR exif_template_changed"); exit(2)
    }
    if let orientation = orientation {
        bytes[48] = UInt8((orientation >> 8) & 255); bytes[49] = UInt8(orientation & 255)
    } else { bytes.removeSubrange(20..<56) }
    return Data(bytes)
}

private func exifAllAndMissing() {
    let hashes = [
        "11043f1218e444e747b3f2d7fa131b1a1eabcb076305a43e2d8787ddf8fee128",
        "286ea3eb83e02ae71962c6d8ceb83173e6199661a5d8e841c479e8261601cab3",
        "b37642746811698a457c1e29aa628b4db8e90d957b53d15d80235c0457a4f7e5",
        "f96fc76a572efc5b7937ce052b5d349df68127e0b21af5963c4e2e15d1ed1255",
        "aed4f2b68734a6ebd3c2507a4c58c7117386eb78e578303b117c75bb785ab776",
        "309721de0f4a2366d0c0259562b67d022bb6295f6592811b132d80c3eb4c621e",
        "d46dd3a994c53d54e427461d5b3d70501c6719944ce64bda11fa49809523e342",
        Fixture.sha,
    ]
    for orientation in 1...8 {
        let bytes = jpegOrientation(orientation)
        let inspector = Metadata()
        guard value(inspector.inspect(bytes)) == NG8ProbeJPEGMetadata(width: 8, height: 6,
              exifOrientation: orientation), inspector.hash(bytes) == hashes[orientation - 1] else {
            print("FIXTURE_ERROR generated_exif_metadata"); exit(2)
        }
        let h = Harness(); beginUnchecked(h); h.complete(bytes)
        let manifest = value(h.probe.manifest(Fixture.key, owner: Fixture.owner))
        let chunk = value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                       sha256: hashes[orientation - 1], offset: 0, limit: 65536))
        expect(manifest?.metadata.exifOrientation == orientation &&
               manifest?.metadata.width == 8 && manifest?.metadata.height == 6 &&
               manifest?.sha256 == hashes[orientation - 1] && chunk?.data == bytes,
               "exif_\(orientation)_original_metadata_and_bytes")
    }
    let bytes = jpegOrientation(nil)
    let missingHash = "357c34f51b34128a9972c081849095aac56c393406834f49a8e12661ae9a33b2"
    let inspector = Metadata()
    guard value(inspector.inspect(bytes)) == NG8ProbeJPEGMetadata(width: 8, height: 6, exifOrientation: nil),
          inspector.hash(bytes) == missingHash else {
        print("FIXTURE_ERROR generated_missing_exif"); exit(2)
    }
    let h = Harness(); beginUnchecked(h); h.complete(bytes)
    let manifest = value(h.probe.manifest(Fixture.key, owner: Fixture.owner))
    let chunk = value(h.probe.chunk(Fixture.key, owner: Fixture.owner,
                                   sha256: missingHash, offset: 0, limit: 65536))
    expect(manifest != nil && manifest?.metadata.exifOrientation == nil && chunk?.data == bytes,
           "missing_exif_remains_null_without_invented_orientation")
}

private func metadataFailureLatch() {
    let h = Harness(); h.metadata.forced = .failure(.metadataInvalid)
    beginUnchecked(h); h.complete()
    expect(h.status?.failure == .metadataInvalid && h.status?.leaseHeld == false &&
           value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
           "inspector_failure_latches_without_published_raw")
    h.driver.deliver(); h.driver.finishBridge(); h.scheduler.pumpCoordinator()
    expect(h.status?.failure == .metadataInvalid && h.metadata.inspectCount == 1,
           "late_duplicate_cannot_replace_inspector_failure")
}

private func invalidTypedMetadata() {
    let bad = [
        NG8ProbeJPEGMetadata(width: 8, height: 6, exifOrientation: 0),
        NG8ProbeJPEGMetadata(width: 8, height: 6, exifOrientation: 9),
        NG8ProbeJPEGMetadata(width: 0, height: 6, exifOrientation: nil),
        NG8ProbeJPEGMetadata(width: 4097, height: 6, exifOrientation: nil),
        NG8ProbeJPEGMetadata(width: 4096, height: 4096, exifOrientation: 1),
    ]
    for metadata in bad {
        let h = Harness(); h.metadata.forced = .success(metadata)
        beginUnchecked(h); h.complete()
        expect(h.status?.failure == .metadataInvalid &&
               value(h.probe.manifest(Fixture.key, owner: Fixture.owner)) == nil,
               "invalid_typed_metadata_cannot_become_ready")
    }
}

private func encodedBytesBounds() {
    for bytes in [Data(), Data(count: NG8ProbeLimits.jpegBytes + 1)] {
        let h = Harness(); beginUnchecked(h); h.complete(bytes)
        expect(h.status?.failure == .bytesInvalid && h.metadata.inspectCount == 0 &&
               h.metadata.hashCount == 0 && h.status?.leaseHeld == false,
               "empty_or_oversize_bytes_rejected_before_inspect_hash")
    }
}

private func handoffOwnedJobFence() {
    let h = Harness(); beginUnchecked(h); h.scheduler.runMain(); h.scheduler.runWorker()
    h.driver.deliver(); h.driver.finishBridge()
    expect(!h.scheduler.coordinator.isEmpty && h.metadata.inspectCount == 0 && h.metadata.hashCount == 0,
           "handoff_receivers_only_enqueue_owned_work")
    var remaining = 64
    while !h.scheduler.coordinator.isEmpty && remaining > 0 {
        h.scheduler.runCoordinator(emitReturn: false); remaining -= 1
    }
    expect(h.status?.state != .ready && h.status?.draining == true && h.status?.leaseHeld == true,
           "handoff_coordinator_actual_return_still_required")
    while !h.scheduler.coordinatorReturns.isEmpty { h.scheduler.returnCoordinator() }
    h.scheduler.pumpCoordinator()
    let manifest = value(h.probe.manifest(Fixture.key, owner: Fixture.owner))
    expect(h.status?.state == .ready && h.status?.draining == false &&
           h.status?.callbackReturnVerified == false && manifest?.callbackReturnVerified == false,
           "owned_handoff_never_claims_literal_callback_return")
}

private func staleGenerationCallback() {
    let h = Harness(); beginUnchecked(h); h.scheduler.runMain(); h.scheduler.runWorker()
    let staleReply = h.driver.reply, staleHandoff = h.driver.drained
    _ = h.probe.cancel(Fixture.key, owner: Fixture.owner)
    h.driver.deliver(.failure(.captureFailed)); h.driver.finishBridge(); h.scheduler.pumpCoordinator()
    let next = NG8ProbeKey(runtimeID: Fixture.runtime, probeID: String(repeating: "c", count: 32))
    _ = h.probe.start(next, owner: Fixture.owner); h.scheduler.runMain(); h.scheduler.runWorker()
    staleReply?(.success(Fixture.jpeg)); staleHandoff?(); h.scheduler.pumpCoordinator()
    expect(value(h.probe.status(next, owner: Fixture.owner))?.state == .capturing &&
           h.driver.requestCount == 2 && h.metadata.inspectCount == 0,
           "retired_generation_callbacks_cannot_commit_into_new_probe")
    h.driver.deliver(); h.driver.finishBridge(); h.scheduler.pumpCoordinator()
    expect(value(h.probe.manifest(next, owner: Fixture.owner))?.generation == 2,
           "new_generation_commits_only_its_own_candidate")
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
            ("id_budget_history", idBudgetAndHistory), ("same_id_cached", sameIDCached),
            ("same_id_cancelled", sameIDAfterCancel), ("same_id_expired", sameIDAfterTTL),
            ("other_owner_same_id", otherOwnerSameID), ("busy_id_not_consumed", busyIDNotConsumed),
            ("owner_pause_prepare", { ownerGate(.paused, name: "pause", at: .prepare) }),
            ("owner_revoke_prepare", { ownerGate(.inactive, name: "revoke", at: .prepare) }),
            ("owner_pause_request", { ownerGate(.paused, name: "pause", at: .request) }),
            ("owner_revoke_request", { ownerGate(.inactive, name: "revoke", at: .request) }),
            ("owner_pause_commit", { ownerGate(.paused, name: "pause", at: .commit) }),
            ("owner_revoke_commit", { ownerGate(.inactive, name: "revoke", at: .commit) }),
            ("owner_pause_export", { ownerGate(.paused, name: "pause", at: .export) }),
            ("owner_revoke_export", { ownerGate(.inactive, name: "revoke", at: .export) }),
            ("chunk_ranges", chunkRanges), ("wire_chunk_ranges", wireChunkRanges),
            ("exif_all_missing", exifAllAndMissing), ("metadata_failure", metadataFailureLatch),
            ("typed_metadata_invalid", invalidTypedMetadata), ("encoded_bytes_bounds", encodedBytesBounds),
            ("handoff_owned_job", handoffOwnedJobFence), ("stale_generation", staleGenerationCallback),
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
