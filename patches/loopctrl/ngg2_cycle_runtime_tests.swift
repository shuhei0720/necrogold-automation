// TEST094 actual Runtime callbacks with procedural pixels, clock and classifier
// results. These tests do not assert game accuracy, device speed or ZIP bytes.
final class CycleFixtureClock {
    private let gate = NSLock()
    private var value = DispatchTime.now().uptimeNanoseconds
    func now() -> UInt64 { gate.lock(); defer { gate.unlock() }; value += 1_000; return value }
    func advance(_ amount: UInt64) { gate.lock(); value += amount; gate.unlock() }
}
func cycleCall(_ id: String, _ mode: String = "status", extra: [String: JSONValue] = [:], owner: String = "fixture-owner") -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "mode": .string(mode), "_necro_owner": .string(owner)]
    for (key, value) in extra { params[key] = value }
    return runtime.handle(method: "necro_native_cycle", params: params)
}
func cyclePayload(_ id: String) -> [String: JSONValue] { cycleCall(id).0?["payload"]?.objectValue ?? [:] }
func cycleCompanion(_ id: String) -> [String: JSONValue] { cyclePayload(id)["cycle"]?.objectValue ?? [:] }
func cycleDrained(_ id: String) -> Bool { cyclePayload(id)["workers_drained"]?.boolValue == true }
func cycleStart(_ id: String) {
    fixtureFailureSnapshot = {
        ["cycle_status": .object(cyclePayload(id)), "controller_report": .object(report(id)),
         "touch_count": .int(NG2Fake.countTouches()), "capture_requests": .int(NG2Fake.countRequests()),
         "tap_count": .int(NG2Fake.taps().count)]
    }
    let answer = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-cycle-v1"), "_necro_owner": .string("fixture-owner")])
    require(answer.1 == nil, "cycle094_start_accepted")
}
func cycleProof(_ outcome: Int32) {
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        let start = result.started_ns, end = NG2Runtime.now()
        ng2_fixture_cycle_result(scene, start, end, outcome, &result)
    }
}
func cyclePixels(worldX: Int32 = 0, goods: Bool = true) -> Data {
    var bytes = Data(count: 896 * 414 * 4)
    let count = bytes.count
    bytes.withUnsafeMutableBytes { raw in
        require(ng2_fixture_floor_pixels_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count,
            worldX, 0, 0.5, goods ? 1 : 0) == 1, "cycle094_procedural_pixels")
    }
    return bytes
}
func cycleSearchPixels(worldX: Int32, variant: Int32, goods: Int32 = 0) -> Data {
    var bytes = Data(count: 896 * 414 * 4)
    let count = bytes.count
    bytes.withUnsafeMutableBytes { raw in
        require(ng2_fixture_cycle_search_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count,
            worldX, variant, goods) == 1, "cycle094_procedural_search_pixels")
    }
    return bytes
}
func resetCycleFixture(_ root: URL) -> CycleFixtureClock {
    NG2Fake.reset(.walk)
    let clock = CycleFixtureClock()
    NG2RuntimeTestHooks.clock = { clock.now() }
    NG2RuntimeCycleTestHooks.spoolRoot = root
    NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
    NG2RuntimeCycleTestHooks.beforeClassification = nil
    NG2RuntimeCycleTestHooks.classificationResult = nil
    NG2RuntimeCycleTestHooks.beforeClassificationCommit = nil
    NG2RuntimeCycleTestHooks.beforeCheckpointWrite = nil
    NG2RuntimeCycleTestHooks.beforeIntentWrite = nil
    NG2RuntimeCycleTestHooks.beforePersistenceCommit = nil
    NG2RuntimeCycleTestHooks.afterNotification = nil
    NG2RuntimeCycleTestHooks.afterTerminalDrainPass = nil
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    let full = cyclePixels()
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        return paused ? original : full
    }
    return clock
}
func publishFixtureClaim(_ id: String, diagnostic: Bool = false, requiredCaptureIDs: Set<Int> = [],
                         checkBounds: Bool = false, expectedInputState: Int? = nil) {
    var payload: [String: JSONValue]?
    pump("cycle094_manifest_ready", timeout: 30) {
        let reply = cycleCall(id, "manifest")
        if let error = reply.1 { require(error.code == -32094, "cycle094_only_pending_is_retried") }
        payload = reply.0?["payload"]?.objectValue
        return payload != nil
    }
    guard let value = payload, let text = value["manifest_json"]?.stringValue,
          let bytes = text.data(using: .utf8), let exportID = value["export_id"]?.stringValue,
          let manifestSHA = value["manifest_sha256"]?.stringValue,
          let manifest = try? JSONDecoder().decode([String: JSONValue].self, from: bytes) else {
        require(false, "cycle094_exact_manifest_parse"); return
    }
    require(NG2CycleWire.hash(bytes) == manifestSHA && manifest["terminal"]?.boolValue == true &&
        manifest["workers_drained"]?.boolValue == true, "cycle094_frozen_manifest_identity")
    if diagnostic { require(manifest["complete"]?.boolValue == false, "cycle094_storage_fault_never_normal_certificate") }
    if let expectedInputState {
        require(manifest["input_state"]?.intValue == expectedInputState && manifest["ui_frozen"]?.boolValue == true,
            "cycle094_unknown_manifest_preserves_input_state_and_freeze")
    }
    let imageIDs = Set((manifest["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    require(requiredCaptureIDs.isSubset(of: imageIDs), "cycle094_first_last_skip_sources_survive_recent_eviction_and_shop")
    if checkBounds, let capture = imageIDs.first {
        let overflow = cycleCall(id, "batch", extra: ["export_id": .string(exportID), "capture_id": .int(capture),
            "offset": .int(Int.max), "count": .int(4)])
        let wrongType = cycleCall(id, "batch", extra: ["export_id": .string(exportID), "capture_id": .int(capture),
            "offset": .int(0), "count": .bool(true)])
        let wrongExport = cycleCall(id, "chunk", extra: ["export_id": .string(String(repeating: "f", count: 32)),
            "capture_id": .int(capture), "offset": .int(0)])
        require(overflow.0 == nil && overflow.1?.code == -32602 && wrongType.0 == nil && wrongType.1?.code == -32602,
            "cycle094_batch_intmax_and_boolean_count_rejected_before_arithmetic")
        require(wrongExport.0 == nil && wrongExport.1?.code == -32602,
            "cycle094_wrong_export_identity_rejected_before_read_without_poisoning")
    }
    // This is an explicit simulated client receipt. The separate Python
    // publisher tests verify real ZIP bytes; the native server cannot do so.
    let claim = String(repeating: "a", count: 64)
    pump("cycle094_publication_ack", timeout: 30) {
        let reply = cycleCall(id, "published", extra: ["export_id": .string(exportID),
            "manifest_sha256": .string(manifestSHA), "archive_sha256": .string(claim)])
        if let error = reply.1 { require(error.code == -32094, "cycle094_receipt_only_pending_is_retried") }
        return reply.0?["payload"]?.objectValue?["accepted"]?.boolValue == true
    }
}

func testCycle094WorkerCancelAndDrain(_ root: URL) {
    _ = resetCycleFixture(root); cycleProof(1)
    let id = identity(), signal = DispatchSemaphore(value: 0), gate = NSLock()
    var entered = false, terminalPassObserved = false, leaseAfterTerminalPass = false
    NG2RuntimeCycleTestHooks.beforeClassification = { _ in gate.lock(); entered = true; gate.unlock(); signal.wait() }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in NG2Fake.holdTicket(command, callback); return true }
    NG2RuntimeCycleTestHooks.afterTerminalDrainPass = { observedID, captureDone, captureOutstanding, mainOutstanding in
        guard observedID == id, captureDone, !captureOutstanding, !mainOutstanding,
              NG2CaptureBridge.pendingRequests == 0 else { return }
        let held = runtime.hasLease
        gate.lock(); terminalPassObserved = true; leaseAfterTerminalPass = held; gate.unlock()
    }
    cycleStart(id)
    pump("cycle094_worker_entered") { gate.lock(); defer { gate.unlock() }; return entered }
    _ = call("necro_native_cancel", id)
    pump("cycle094_cancel_terminal") { cyclePayload(id)["terminal"]?.boolValue == true }
    NG2Fake.lock.lock(); let held = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
    for command in held { NG2Fake.releaseTicket(command) }
    pump("cycle094_cancel_main_and_capture_drained") {
        let value = report(id)
        return value["main_ticket_outstanding"]?.boolValue == false && value["capture_outstanding"]?.boolValue == false
    }
    // Main/capture reporting can precede the terminal lease-release decision.
    // Observe the completed real pass while the classification worker remains
    // parked; the lease mutation must be visible before that worker is freed.
    pump("cycle094_cancel_terminal_drain_pass_observed") {
        gate.lock(); defer { gate.unlock() }; return terminalPassObserved
    }
    gate.lock(); let heldAfterPass = leaseAfterTerminalPass; gate.unlock()
    NG2RuntimeCycleTestHooks.afterTerminalDrainPass = nil
    require(heldAfterPass && !cycleDrained(id) && runtime.hasLease && NG2Fake.countTouches() == 0,
        "cycle094_cancel_holds_lease_until_worker_and_main_return")
    signal.signal()
    pump("cycle094_cancel_actual_drain", timeout: 20) { cycleDrained(id) }
    require(cycleCompanion(id)["outcome"]?.stringValue == "unknown" && NG2Fake.countTouches() == 0,
        "cycle094_late_candidate_after_cancel_inert")
    publishFixtureClaim(id)
}

func testCycle094CandidateOneShot(_ root: URL) {
    _ = resetCycleFixture(root); cycleProof(1)
    let id = identity(), gate = NSLock(); var notices = 0
    NG2RuntimeCycleTestHooks.afterNotification = { _ in gate.lock(); notices += 1; gate.unlock() }
    cycleStart(id)
    pump("cycle094_candidate_drained", timeout: 20) { cycleDrained(id) }
    for _ in 0..<8 { _ = cycleCall(id) }
    gate.lock(); let count = notices; gate.unlock()
    require(cycleCompanion(id)["outcome"]?.stringValue == "candidate" && count == 1 &&
        NG2Fake.countTouches() == 1 && NG2Fake.paths().isEmpty,
        "cycle094_candidate_real_pause_one_notice_no_purchase_or_restart")
    let blocked = runtime.handle(method: "necro_native_start", params: ["run_id": .string(identity()),
        "profile": .string("normal-1-1-cycle-v1"), "_necro_owner": .string("fixture-owner")])
    require(blocked.1?.code == -32095, "cycle094_unpublished_next_session_definitively_not_started")
    publishFixtureClaim(id, checkBounds: true)
}

func testCycle094LateAndStorageHold(_ root: URL, storage: Bool) {
    let clock = resetCycleFixture(root); cycleProof(storage ? 1 : 3)
    let id = identity()
    if storage {
        NG2RuntimeCycleTestHooks.beforeCheckpointWrite = { _ in
            var failed = false
            NG2CycleSpoolTestHooks.beforeBoundary = { boundary in
                if boundary == "file_sync" && !failed { failed = true; return false }; return true
            }
        }
    } else {
        NG2RuntimeCycleTestHooks.beforeClassificationCommit = { _ in clock.advance(151_000_000) }
    }
    cycleStart(id)
    pump("cycle094_fault_drained", timeout: 20) { cycleDrained(id) }
    let state = cycleCompanion(id)
    require(NG2Fake.taps().allSatisfy { $0.x == 390 && $0.y == 448 } && NG2Fake.paths().isEmpty,
        "cycle094_failure_never_restart_or_move")
    if storage { require(state["durable_ns"]?.intValue == 0, "cycle094_storage_failure_never_fabricates_durable") }
    else { require(state["assessment_status"]?.stringValue == "deadline", "cycle094_late_negative_never_revives_fast_authority") }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    publishFixtureClaim(id, diagnostic: storage)
}

func testCycle094TwoShopsAndIntentCancel(_ root: URL, cancelIntent: Bool) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    var level = 1, expose = true, settleAdvanced = false, nextSettleAdvanced = false, writerEntered = false
    var classifierReleased = false, pauseBeforeClassifier = false
    let classificationRelease = DispatchSemaphore(value: 0)
    let first = cyclePixels(), nextEmpty = cyclePixels(worldX: 36, goods: false), nextGoods = cyclePixels(worldX: 36)
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let current = level, visible = expose; gate.unlock()
        return current == 1 ? first : (visible ? nextGoods : nextEmpty)
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        gate.lock(); let current = level; gate.unlock()
        ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), current == 1 ? 3 : 1, &result)
    }
    if cancelIntent {
        // Exercise the CI162 ordering deliberately: the PAUSE image reaches
        // control while the classifier is still pending. Settling the UI may
        // not advance this procedural clock past the worker's adoption bound.
        NG2RuntimeCycleTestHooks.beforeClassification = { _ in classificationRelease.wait() }
    }
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); level = 2; expose = false; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id)
        gate.lock()
        let paused = (state["pause_capture_id"]?.intValue ?? 0) > 0
        let releaseClassifier = cancelIntent && !classifierReleased && paused && state["pending"]?.boolValue == true
        if releaseClassifier { classifierReleased = true; pauseBeforeClassifier = true }
        let advance = !settleAdvanced && paused && state["pending"]?.boolValue == false
            && state["assessment_status"]?.stringValue == "ok" && state["outcome"]?.stringValue == "negative"
            && (state["durable_ns"]?.intValue ?? 0) > 0
        if advance { settleAdvanced = true }
        if (state["level_id"]?.intValue ?? 0) >= 2 { expose = true }
        let advanceNext = !nextSettleAdvanced && (state["level_id"]?.intValue ?? 0) >= 2
            && state["pending"]?.boolValue == false && state["outcome"]?.stringValue == "candidate"
        if advanceNext { nextSettleAdvanced = true }
        gate.unlock()
        if releaseClassifier { classificationRelease.signal() }
        if advance { clock.advance(220_000_000) }
        if advanceNext { clock.advance(220_000_000) }
    }
    let release = DispatchSemaphore(value: 0)
    if cancelIntent {
        NG2RuntimeCycleTestHooks.beforeIntentWrite = { _ in
            gate.lock(); writerEntered = true; gate.unlock(); release.wait()
        }
    }
    cycleStart(id)
    if cancelIntent {
        pump("cycle094_exact_intent_writer_entered", timeout: 20) { gate.lock(); defer { gate.unlock() }; return writerEntered }
        gate.lock(); let observedPendingPause = pauseBeforeClassifier; gate.unlock()
        require(observedPendingPause, "cycle094_pause_before_classifier_does_not_spend_adoption_deadline")
        require(NG2Fake.taps().count == 1, "cycle094_uncommitted_intent_restart_zero")
        _ = call("necro_native_cancel", id)
        require(!cycleDrained(id), "cycle094_cancel_does_not_fake_writer_drain")
        release.signal()
    }
    pump("cycle094_session_drained", timeout: 30) { cycleDrained(id) }
    let taps = NG2Fake.taps(), restarts = taps.filter { $0.x == 144 && $0.y == 448 }.count
    if cancelIntent { require(restarts == 0, "cycle094_late_durable_intent_cannot_dispatch_after_cancel") }
    else {
        let state = cycleCompanion(id)
        require(restarts == 1 && taps.count == 3 && state["level_id"]?.intValue == 2 &&
            state["completed_shops"]?.intValue == 2 && state["outcome"]?.stringValue == "candidate",
            "cycle094_two_shops_one_session_negative_restart_actual_new_floor_and_next_hold")
    }
    if cancelIntent {
        NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert("fixture-recovery-owner"); NG2Fake.lock.unlock()
        var recovered: [String: JSONValue]?
        pump("cycle094_dangling_intent_readonly_recovery", timeout: 20) {
            recovered = cycleCall(id, owner: "fixture-recovery-owner").0?["payload"]?.objectValue
            return recovered != nil
        }
        require(recovered?["state"]?.stringValue == "stopped" && recovered?["input_state"]?.intValue == 4 &&
            recovered?["ui_frozen"]?.boolValue == true && NG2Fake.taps().count == 1,
            "cycle094_dangling_intent_recovers_unknown_frozen_without_resend")
    }
    require(NG2Fake.paths().isEmpty, "cycle094_full_visible_world_no_purchase")
    publishFixtureClaim(id)
}

func testCycle094SearchRestart(_ root: URL, firstGoods: Int = 0) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    var exposed = false, settled = false
    // Distinct observed terrain must satisfy the real restart fingerprint;
    // translating nearly uniform floor noise does not prove a new floor.
    let clear: [Data] = [Int32(0), 36, 72].enumerated().map { entry in
        cycleSearchPixels(worldX: entry.element, variant: Int32(entry.offset % 2))
    }
    let empty = cycleSearchPixels(worldX: 108, variant: 1)
    let goods = cycleSearchPixels(worldX: 108, variant: 1, goods: 1)
    let partial = cycleSearchPixels(worldX: 108, variant: 1, goods: 2)
    var restarts = 0
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); restarts += 1; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let count = restarts, show = exposed; gate.unlock()
        if count < 3 { return clear[count] }
        if firstGoods == 1 { return partial }
        if firstGoods == 2 { return goods }
        return show ? goods : empty
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id)
        if (state["level_id"]?.intValue ?? 0) >= 4 { gate.lock(); exposed = true; gate.unlock() }
        else { clock.advance(20_000_000) }
        gate.lock()
        let advance = !settled && (state["job_id"]?.intValue ?? 0) > 0
            && state["pending"]?.boolValue == false && state["outcome"]?.stringValue == "candidate"
        if advance { settled = true }
        gate.unlock()
        if advance { clock.advance(220_000_000) }
    }
    cycleProof(1); cycleStart(id)
    pump("cycle094_search_skip_restart_drained", timeout: 30) { cycleDrained(id) }
    let taps = NG2Fake.taps()
    require(taps.filter { $0.x == 144 && $0.y == 448 }.count == 3 && taps.count == 7 &&
        cycleCompanion(id)["level_id"]?.intValue == 4 && cycleCompanion(id)["outcome"]?.stringValue == "candidate",
        "cycle094_search_restart_does_not_require_negative_shop_certificate")
    let pauseSources = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        .filter { $0["kind"]?.intValue == 2 }.prefix(3).compactMap { $0["source_capture_id"]?.intValue }
    require(pauseSources.count == 3 && pauseSources.first != pauseSources.last,
        "cycle094_distinct_first_last_skip_source_ids")
    publishFixtureClaim(id, requiredCaptureIDs: Set(pauseSources))
}

func testCycle094InitialStorageRecovery(_ root: URL) {
    _ = resetCycleFixture(root)
    let id = identity(), gate = NSLock()
    var failed = false
    NG2CycleSpoolTestHooks.beforeBoundary = { boundary in
        gate.lock(); defer { gate.unlock() }
        if boundary == "file_sync" && !failed { failed = true; return false }; return true
    }
    cycleStart(id)
    pump("cycle094_initial_header_fault_readonly_recovery", timeout: 20) { cycleDrained(id) }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    require(cyclePayload(id)["terminal"]?.boolValue == true && NG2Fake.countTouches() == 0 &&
        NG2Fake.countActivations() == 0 && cycleCompanion(id)["completed_shops"]?.intValue == 0,
        "cycle094_initial_storage_failure_never_launches_or_invents_assessment")
    require(cyclePayload(id)["input_state"]?.intValue == 4 && cyclePayload(id)["ui_frozen"]?.boolValue == true,
        "cycle094_missing_terminal_recovers_unknown_without_inventing_input_zero")
    publishFixtureClaim(id, diagnostic: true)
}

func testCycle094StartedUnknownCompletion(_ root: URL) {
    _ = resetCycleFixture(root); cycleProof(0)
    let id = identity(), gate = NSLock()
    var notices = 0, noticeAfterDrain = false
    NG2RuntimeCycleTestHooks.afterNotification = { _ in
        let drained = cycleDrained(id)
        gate.lock(); notices += 1; noticeAfterDrain = drained; gate.unlock()
    }
    NG2Fake.lock.lock(); NG2Fake.failTouch = true; NG2Fake.lock.unlock()
    cycleStart(id)
    pump("cycle094_started_unknown_actual_drain", timeout: 30) { cycleDrained(id) }
    let value = cyclePayload(id)
    require(value["input_state"]?.intValue == 4 && value["ui_frozen"]?.boolValue == true &&
        value["native_inflight"]?.boolValue == false && report(id)["native_inflight"]?.boolValue == true,
        "cycle094_unknown_synth_actual_drain_projection")
    pump("cycle094_unknown_completion_requested") { gate.lock(); defer { gate.unlock() }; return notices == 1 }
    gate.lock(); let count = notices, afterDrain = noticeAfterDrain; gate.unlock()
    require(count == 1 && afterDrain && cycleCompanion(id)["outcome"]?.stringValue == "unknown" &&
        NG2Fake.countTouches() == 1 && NG2Fake.paths().isEmpty,
        "cycle094_unknown_completion_notice_once_after_all_workers_return")
    publishFixtureClaim(id, expectedInputState: 4)
    let blocked = runtime.handle(method: "necro_native_start", params: ["run_id": .string(identity()),
        "profile": .string("normal-1-1-cycle-v1"), "_necro_owner": .string("fixture-owner")])
    require(blocked.1 != nil && runtime.hasLease && NG2Fake.countTouches() == 1,
        "cycle094_publication_does_not_clear_unknown_global_poison")
}

// TEST094 ENTRYPOINTS BEGIN.
var pauseProbeRGBA = Data(count: 896 * 414 * 4)
let pauseProbeBytes = pauseProbeRGBA.count
pauseProbeRGBA.withUnsafeMutableBytes { ng2_test_pause($0.bindMemory(to: UInt8.self).baseAddress, pauseProbeBytes) }
var pauseProbeScene = NG2Scene()
let pauseProbeStatus = pauseProbeRGBA.withUnsafeBytes {
    ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, pauseProbeBytes, 896 * 4, &pauseProbeScene)
}
require(pauseProbeStatus == 0 && pauseProbeScene.state == 1 && pauseProbeScene.restart_label == 1,
    "cycle094_procedural_pause_has_continue_and_restart_observed_by_real_C")
let cycleRoot = FileManager.default.temporaryDirectory.appendingPathComponent("runtime-cycle094-" + UUID().uuidString)
try FileManager.default.createDirectory(at: cycleRoot, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: cycleRoot) }
NG2RuntimeCycleTestHooks.spoolRoot = cycleRoot
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
pump("cycle094_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
// TEST094 CASE CALLS BEGIN.
testCycle094WorkerCancelAndDrain(cycleRoot)
testCycle094InitialStorageRecovery(cycleRoot)
testCycle094CandidateOneShot(cycleRoot)
testCycle094LateAndStorageHold(cycleRoot, storage: false)
testCycle094LateAndStorageHold(cycleRoot, storage: true)
testCycle094TwoShopsAndIntentCancel(cycleRoot, cancelIntent: true)
testCycle094TwoShopsAndIntentCancel(cycleRoot, cancelIntent: false)
testCycle094SearchRestart(cycleRoot)
testCycle094SearchRestart(cycleRoot, firstGoods: 1)
testCycle094SearchRestart(cycleRoot, firstGoods: 2)
testCycle094StartedUnknownCompletion(cycleRoot)
print("PASS TEST094 production Runtime selected eleven cycle worker/cancel/deadline/storage/recovery/intent/two-shop/search/unknown callbacks; procedural clock/pixels/classifier")
