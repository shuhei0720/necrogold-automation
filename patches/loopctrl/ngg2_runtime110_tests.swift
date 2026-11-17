// TEST110 selected production Runtime callback contract. All pixels, clocks,
// classifier results and game reactions below are procedural host fixtures.
// The queue roles correspond to TEST109 249->250, not archived phone images.
func testIrregular110ProfilePreparePublic(_ root: URL) {
    _ = resetCycleFixture(root)
    let answer = runtime.handle(method: "necro_native_irregular", params: ["run_id": .string(identity()),
        "mode": .string("prepare"), "_necro_owner": .string("fixture-owner")])
    require(answer.1 == nil && answer.0?["schema"]?.stringValue == "ngg2-irregular-cycle-v1" &&
        answer.0?["profile"]?.stringValue == "normal-1-1-irregular-v1",
        "test110_new_profile_prepare_accepted_with_own_closed_envelope")
    require(NG2Fake.countTouches() == 0 && NG2Fake.countActivations() == 0,
        "test110_prepare_has_no_game_input")
    print("PASS TEST110 new profile prepare actual Runtime query")
}

func testFullData110QueueRetentionPublic(_ root: URL, candidateFirst: Bool = false) {
    let clock = resetCycleFixture(root), gate = NSLock(), release = DispatchSemaphore(value: 0)
    let id = identity(), partial = cycleSearchPixels(worldX: 0, variant: 0, goods: 2)
    let full = cycleSearchPixels(worldX: 0, variant: 0, goods: 1)
    let expectedSHA = NG2CycleWire.hash(full)
    var produceFull = false, offeredFull = false, entered = [UInt64](), latestCapture: UInt64 = 0
    var firstJob: UInt64 = 0, heldResume: UInt64 = 0, sentinelPending = false, sentinelCapture: UInt64 = 0
    NG2Fake.lock.lock(); NG2Fake.walkPaused = true; NG2Fake.lock.unlock()
    NG2Fake.cycleTap = { x, y in
        if x == 297 && y == 448 {
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.mode = .walk; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); defer { gate.unlock() }
        if sentinelPending { sentinelPending = false; return full }
        if produceFull && !offeredFull { offeredFull = true; return full }
        return partial
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, _, _, _, stable in
        gate.lock(); latestCapture = capture
        if !stable && sentinelCapture == 0 { sentinelCapture = capture }
        gate.unlock()
    }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        gate.lock(); heldResume = command; gate.unlock()
        NG2Fake.lock.lock(); NG2Fake.mode = .hold; NG2Fake.lock.unlock()
        NG2Fake.holdTicket(command, callback)
        return true
    }
    NG2RuntimeCycleTestHooks.beforeClassification = { job in
        gate.lock(); entered.append(job); let first = entered.count == 1
        if first { firstJob = job }; gate.unlock()
        if first { release.wait() }
    }
    NG2RuntimeCycleTestHooks.classificationResult = { job, scene, result in
        let started = result.started_ns
        gate.lock(); let first = job == firstJob; gate.unlock()
        if first && !candidateFirst {
            ng2_fixture_partial_unknown110(scene, started, NG2Runtime.now(), &result)
        } else { ng2_fixture_cycle_result(scene, started, NG2Runtime.now(), 1, &result) }
    }
    cycleStart(id)
    pump("test110_resume_held_with_capture_started", timeout: 20) {
        gate.lock(); let held = heldResume != 0; gate.unlock()
        NG2Fake.lock.lock(); let captureHeld = !NG2Fake.callbacks.isEmpty; NG2Fake.lock.unlock()
        return held && captureHeld
    }
    // Occupy the existing first-FULL `found` slot with a correctly rejected
    // cross-prefix image. This is a real capture/RESUME boundary, not a cache
    // mutation; the later queued FULL must therefore survive on its own ID.
    NG2RuntimeTestHooks.scheduleTicket = nil
    gate.lock(); let resume = heldResume; gate.unlock()
    NG2Fake.releaseTicket(resume)
    pump("test110_resume_actual_ack", timeout: 20) { report(id)["last_completed_id"]?.intValue == Int(resume) }
    gate.lock(); sentinelPending = true; gate.unlock()
    NG2Fake.lock.lock(); let callbacks = NG2Fake.callbacks; NG2Fake.callbacks = []; NG2Fake.lock.unlock()
    require(callbacks.count == 1, "test110_exact_one_cross_prefix_capture")
    callbacks[0](NG2Fake.pausePNG, nil)
    pump("test110_first_partial_worker_parked", timeout: 20) {
        gate.lock(); defer { gate.unlock() }; return entered.count == 1
    }
    let initial = cycleCompanion(id)
    require(initial["partial"]?.boolValue == true && initial["pending"]?.boolValue == true,
        "test110_public_partial_job_is_real_C_pending")
    gate.lock(); let rejectedSentinel = sentinelCapture; gate.unlock()
    require(rejectedSentinel != 0 && (initial["capture_id"]?.intValue ?? 0) > Int(rejectedSentinel) &&
        (report(id)["discarded_frames"]?.intValue ?? 0) > 0,
        "test110_prior_full_sentinel_is_cross_prefix_rejected_before_partial_job")
    gate.lock(); produceFull = true; gate.unlock()
    pump("test110_first_full_queued_by_actual_C", timeout: 20) {
        (cycleCompanion(id)["queued_capture_id"]?.intValue ?? 0) > 0
    }
    let queued = cycleCompanion(id)["queued_capture_id"]!.intValue!
    let queuedStart = cycleCompanion(id)["queued_capture_start_ns"]!.intValue!
    let acceptedAtQueue = report(id)["accepted_frames"]!.intValue!
    pump("test110_queued_source_older_than_recent_four", timeout: 20) {
        gate.lock(); let idsAdvanced = latestCapture >= UInt64(queued + 32); gate.unlock()
        let state = report(id)
        return idsAdvanced && (state["accepted_frames"]?.intValue ?? 0) >= acceptedAtQueue + 32 &&
            state["last_completed_id"]?.intValue == Int(resume)
    }
    require(cycleCompanion(id)["queued_capture_id"]?.intValue == queued && NG2Fake.countTouches() == 1,
        "test110_first_full_queue_not_replaced_or_resynthesized")
    require(runtime.testOriginalFrameEvidence(id, captureIDs: [UInt64(queued)]) == nil &&
        report(id)["pinned_image_count"]?.intValue == 24,
        "test110_queued_source_evicted_from_real_recent_and_pin_fallback")
    release.signal()
    if candidateFirst {
        pump("test110_candidate_precedes_queued_negative", timeout: 20) {
            cycleCompanion(id)["candidate_latched"]?.boolValue == true
        }
        gate.lock(); let workers = entered.count; gate.unlock()
        require(workers == 1 && cycleCompanion(id)["capture_id"]?.intValue == initial["capture_id"]?.intValue,
            "test110_candidate_never_starts_queued_worker")
    } else {
        pump("test110_queue_first_source_transferred_to_actual_worker", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return entered.count == 2
        }
        pump("test110_queued_result_adopted", timeout: 20) {
            cycleCompanion(id)["candidate_latched"]?.boolValue == true
        }
        let state = cycleCompanion(id)
        require(state["capture_id"]?.intValue == queued && state["capture_start_ns"]?.intValue == queuedStart &&
            state["deadline_ns"]!.intValue! <= queuedStart + 150_000_000 &&
            state["deadline_ns"]!.intValue! <= state["worker_started_ns"]!.intValue! + 100_000_000 &&
            state["continuation_deadline_ns"]!.intValue! <= queuedStart + 3_000_000_000,
            "test110_queued_worker_uses_source_bound_deadlines_without_runtime_extension")
    }
    // The earlier real RESUME keeps PAUSE ineligible during the parked worker.
    // Let its existing 200ms UI interval elapse only after classifier adoption.
    clock.advance(220_000_000)
    pump("test110_checkpoint_from_actual_worker", timeout: 30) {
        (cycleCompanion(id)["durable_ns"]?.intValue ?? 0) > 0
    }
    if !candidateFirst {
        let files = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!
        var matched = false
        for case let url as URL in files where url.lastPathComponent.contains("checkpoint") {
            guard let bytes = try? Data(contentsOf: url),
                  let envelope = try? JSONDecoder().decode([String: JSONValue].self, from: bytes),
                  let body = envelope["payload"]?.objectValue,
                  body["cycle"]?.objectValue?["capture_id"]?.intValue == queued else { continue }
            matched = body["raw_sha256"]?.stringValue == expectedSHA && body["assessment_adopted"]?.boolValue == true
        }
        require(matched, "test110_actual_queued_worker_rgba_digest_persisted")
    }
    require(NG2Fake.paths().isEmpty && NG2Fake.taps().count == 2,
        "test110_no_move_or_restart_or_unknown_resend")
    _ = call("necro_native_cancel", id)
    pump("test110_cancel_drains_actual_callbacks", timeout: 30) { cycleDrained(id) }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    publishFixtureClaim(id)
    print(candidateFirst ? "PASS TEST110 candidate veto queued worker actual callbacks" :
        "PASS TEST110 queued FULL source retained and actual worker RGBA digest persisted")
}

func runRuntime110IrregularCase(_ name: String, _ root: URL) -> Bool {
    #if NG2_IRREGULAR_TEST110_GREEN
    switch name {
    case "death_lifecycle", "death_partial_floor", "death_later_goods", "death_third_menu", "death_unknown_menu", "death_unknown_continue", "death_pin24", "death_cancel_pin24", "death_cancel_continue", "death_cancel_restart", "death_owner_checkpoint", "death_late_checkpoint", "death_storage_checkpoint", "death_recovery_lifecycle", "death_decode_park", "death_outcome_storage":
        testIrregular110DeathCallbacksPublic(root, variant: String(name.dropFirst(6))); return true
    case "invalid_companion": testIrregular110AnalysisVetoPublic(root, promptOnly: false); return true
    case "prompt_only": testIrregular110AnalysisVetoPublic(root, promptOnly: true); return true
    case "pending_candidate": testIrregular110PendingCandidatePublic(root, variant: "candidate"); return true
    case "pending_invalid": testIrregular110PendingCandidatePublic(root, variant: "invalid"); return true
    case "pending_unknown": testIrregular110PendingCandidatePublic(root, variant: "unknown"); return true
    case "pending_negative": testIrregular110PendingCandidatePublic(root, variant: "negative"); return true
    case "enemy_retention": testIrregular110EnemyRetentionPublic(root); return true
    case "recovery_unknown_profile": testIrregular110RecoveryProfileBoundaryPublic(root); return true
    default: return false
    }
    #else
    return false
    #endif
}

let root110 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime110-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root110, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root110) }
NG2RuntimeCycleTestHooks.spoolRoot = root110
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
let case110 = CommandLine.arguments.last ?? ""
if case110 == "profile" { testIrregular110ProfilePreparePublic(root110) }
else if case110 == "negative" {
    cycleFixtureProfile = "normal-1-1-irregular-v1"
    pump("test110_irregular_prepare_ready") {
        cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    testCycle094TwoShopsAndIntentCancel(root110, cancelIntent: false)
    print("PASS TEST110 new-profile normal negative durable restart and next candidate")
}
else if runRuntime110IrregularCase(case110, root110) { }
else if case110 == "prefix" {
    test058PreparedContinuousCase("prefix")
    print("PASS TEST110 existing prefix gate actual callbacks")
}
else if case110 == "retention" || case110 == "candidate" {
    pump("test110_cycle_prepare_ready") {
        cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    testFullData110QueueRetentionPublic(root110, candidateFirst: case110 == "candidate")
}
else { require(false, "test110_unknown_case_is_not_another_fixture") }
print("PASS TEST110 CASE " + case110)
