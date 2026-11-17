// TEST111 selected actual Runtime/C callbacks. Pixel factories, the clock,
// classifier overrides and UI responses are procedural host fixtures. Every
// worker still hashes its retained RGBA and calls the real Ring kernel first.
// This covers the unchanged Swift raw handover also used by the independently
// tested pre-MOVED data bridge; it does not replay e5bb or claim phone success.
func runtime111Advance(_ clock: CycleFixtureClock, to target: UInt64) {
    let now = clock.now()
    if now < target { clock.advance(target - now) }
}

func runtime111Manifest(_ id: String, required: Set<Int>) {
    var manifest: [String: JSONValue]?
    pump("test111_frozen_manifest_ready", timeout: 30) {
        let reply = cycleCall(id, "manifest")
        if let error = reply.1 { require(error.code == -32094, "test111_manifest_only_pending_retried") }
        if let json = reply.0?["payload"]?.objectValue?["manifest_json"]?.stringValue,
           let bytes = json.data(using: .utf8) {
            manifest = try? JSONDecoder().decode([String: JSONValue].self, from: bytes)
        }
        return manifest != nil
    }
    let images = Set((manifest?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    require(manifest?["terminal"]?.boolValue == true && manifest?["workers_drained"]?.boolValue == true &&
        required.isSubset(of: images), "test111_first_source_and_retry_png_retained_in_frozen_manifest")
}

func runtime111PersistedPixels(_ root: URL, capture: UInt64, expected: Data) {
    let rawName = String(format: "frame-%016llx.rgba", capture)
    let pngName = String(format: "png-%016llx.png", capture)
    let files = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!
    var rawMatch = false, pngMatch = false
    for case let url as URL in files {
        if url.lastPathComponent == rawName, let bytes = try? Data(contentsOf: url) {
            rawMatch = bytes == expected && NG2CycleWire.hash(bytes) == NG2CycleWire.hash(expected)
        }
        if url.lastPathComponent == pngName, let bytes = try? Data(contentsOf: url), let rgba = NG2Raster.decode(bytes) {
            pngMatch = rgba == expected && NG2CycleWire.hash(rgba) == NG2CycleWire.hash(expected)
        }
    }
    require(rawMatch && pngMatch, "test111_exact_original_rgba_and_exported_png_" + String(capture))
}

func testFreshDeadline111CallbacksPublic(_ root: URL, variant: String) {
    let clock = resetCycleFixture(root), gate = NSLock(), id = identity()
    let workerRelease = DispatchSemaphore(value: 0), commitRelease = DispatchSemaphore(value: 0)
    let captureRelease = DispatchSemaphore(value: 0)
    let original = cyclePixels()
    // A diagnostic HUD-corner byte distinguishes raw sources without changing
    // the factory's actual FULL goods, exact ITEM/protection or static plane.
    var fresh = original
    fresh[fresh.count - 4] = 17; fresh[fresh.count - 3] = 19; fresh[fresh.count - 2] = 23
    require(NG2CycleWire.hash(original) != NG2CycleWire.hash(fresh), "test111_distinct_raw_full_sources")
    var exposeFresh = false, pauseCaptures = false, captureParked = false
    var entered = [UInt64](), commits = [UInt64](), timeoutJobs = Set<UInt64>()
    var kernelCalls = 0, ticks = 0, observedFrames = 0, scheduled = [UInt64]()
    NG2RuntimeCycleTestHooks.rgba = { pixels in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return pixels }
        gate.lock(); let useFresh = exposeFresh; gate.unlock()
        return useFresh ? fresh : original
    }
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        gate.lock(); let park = pauseCaptures
        if park { captureParked = true }; gate.unlock()
        if park {
            require(captureRelease.wait(timeout: .now() + 30) == .success, "test111_capture_gate_bounded")
            gate.lock(); captureParked = false; gate.unlock()
        }
    }
    NG2RuntimeTestHooks.beforeControlTick = { gate.lock(); ticks += 1; gate.unlock() }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { _, _, _, _, _ in
        gate.lock(); observedFrames += 1; gate.unlock()
    }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        gate.lock(); scheduled.append(command); gate.unlock()
        NG2Fake.holdTicket(command, callback)
        return true
    }
    NG2RuntimeCycleTestHooks.beforeClassification = { job in
        gate.lock(); entered.append(job); let count = entered.count
        let actualCalls = kernelCalls, actualCommits = commits.count; gate.unlock()
        require(count == 1 || (actualCalls == count - 1 && actualCommits == count - 1),
            "test111_next_worker_requires_previous_actual_kernel_and_commit_callback")
        require(workerRelease.wait(timeout: .now() + 30) == .success, "test111_worker_park_bounded")
    }
    NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, _, _ in
        require(mode == Int32(NG2_RING_MODE_TARGET_ONLY), "test111_real_kernel_called_in_target_only_mode")
        gate.lock(); kernelCalls += 1; gate.unlock()
    }
    NG2RuntimeCycleTestHooks.classificationResult = { job, scene, result in
        gate.lock(); let expired = timeoutJobs.contains(job); gate.unlock()
        let began = result.started_ns
        ng2_fixture_cycle_result(scene, began, NG2Runtime.now(), expired ? 0 : 1, &result)
        if expired {
            result.status = UInt32(NG2_RING_DEADLINE)
            if variant == "late_candidate" { result.outcome = UInt32(NG2_RING_CANDIDATE) }
        }
    }
    NG2RuntimeCycleTestHooks.beforeClassificationCommit = { job in
        gate.lock(); commits.append(job); let expired = timeoutJobs.contains(job); gate.unlock()
        if expired { require(commitRelease.wait(timeout: .now() + 30) == .success, "test111_commit_callback_park_bounded") }
    }
    cycleStart(id)
    pump("test111_initial_actual_full_worker_parked", timeout: 20) {
        gate.lock(); defer { gate.unlock() }; return entered.count == 1
    }
    let rootState = cycleCompanion(id)
    let firstCapture = UInt64(rootState["capture_id"]!.intValue!), firstJob = UInt64(rootState["job_id"]!.intValue!)
    let rootHold = rootState["hold_started_ns"]!.intValue!, rootD = rootState["continuation_deadline_ns"]!.intValue!
    require(rootState["partial"]?.boolValue == false && rootState["pending"]?.boolValue == true &&
        rootState["full_seen"]?.boolValue == true && NG2Fake.countTouches() == 0,
        "test111_initial_full_has_no_prior_move_or_ui")
    var retryCapture: UInt64 = 0
    let rounds = variant == "limit" ? 3 : 1
    for round in 1...rounds {
        let active = cycleCompanion(id), job = UInt64(active["job_id"]!.intValue!)
        let sourceStart = UInt64(active["capture_start_ns"]!.intValue!)
        let workerStart = UInt64(active["worker_started_ns"]!.intValue!)
        let deadline = UInt64(active["deadline_ns"]!.intValue!)
        require(deadline <= sourceStart + 150_000_000 && deadline <= workerStart + 100_000_000,
            "test111_every_job_keeps_source150ms_and_worker100ms_bounds")
        require(active["hold_started_ns"]?.intValue == rootHold && active["continuation_deadline_ns"]?.intValue == rootD,
            "test111_every_retry_keeps_original_hold_and_root_D")
        gate.lock(); pauseCaptures = true; gate.unlock()
        pump("test111_capture_parked_before_clock_advance", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return captureParked
        }
        runtime111Advance(clock, to: sourceStart + 90_000_000)
        require(cycleCompanion(id)["job_id"]?.intValue == Int(job) && cycleCompanion(id)["pending"]?.boolValue == true,
            "test111_90ms_does_not_replace_running_worker")
        runtime111Advance(clock, to: sourceStart + 95_000_000)
        gate.lock(); exposeFresh = true; pauseCaptures = false; gate.unlock(); captureRelease.signal()
        if round < 3 {
            pump("test111_actual_C_retains_full_after95ms", timeout: 20) {
                let state = cycleCompanion(id)
                return (state["queued_capture_id"]?.intValue ?? 0) > Int(active["capture_id"]!.intValue!) &&
                    (state["queued_capture_start_ns"]?.intValue ?? 0) >= Int(sourceStart + 95_000_000)
            }
        } else {
            let accepted = report(id)["accepted_frames"]!.intValue!
            pump("test111_exhausted_retry_still_observes_fresh_full", timeout: 20) {
                (report(id)["accepted_frames"]?.intValue ?? 0) >= accepted + 2
            }
        }
        gate.lock(); pauseCaptures = true; gate.unlock()
        pump("test111_queued_pixel_source_frozen_before_expiry", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return captureParked
        }
        let queued = cycleCompanion(id)
        let queuedCapture = UInt64(queued["queued_capture_id"]?.intValue ?? 0)
        let queuedStart = queued["queued_capture_start_ns"]?.intValue ?? 0
        runtime111Advance(clock, to: max(sourceStart + 150_000_001, workerStart + 100_000_001))
        gate.lock(); let beforeTicks = ticks; gate.unlock()
        pump("test111_expiry_reaches_actual_control_ticks", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return ticks >= beforeTicks + 2
        }
        let expired = cycleCompanion(id)
        gate.lock(); let noNewUI = scheduled.isEmpty, actualWorkers = entered.count; timeoutJobs.insert(job); gate.unlock()
        require(expired["job_id"]?.intValue == Int(job) && expired["capture_id"]?.intValue == active["capture_id"]?.intValue &&
            expired["pending"]?.boolValue == true && actualWorkers == round && noNewUI && NG2Fake.countTouches() == 0,
            "test111_expired_worker_drains_before_job_change_or_ui")
        require(cyclePayload(id)["workers_drained"]?.boolValue == false,
            "test111_parked_real_worker_never_reports_drained")
        workerRelease.signal()
        pump("test111_expired_real_kernel_reaches_commit_callback", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return commits.contains(job)
        }
        // The real kernel and hash have returned; the actual C assess callback
        // remains parked. A second worker or PAUSE is still forbidden here.
        let beforeCommit = cycleCompanion(id)
        gate.lock(); let commitWorkers = entered.count, commitUI = scheduled.count, realCalls = kernelCalls; gate.unlock()
        require(beforeCommit["job_id"]?.intValue == Int(job) && beforeCommit["pending"]?.boolValue == true &&
            commitWorkers == round && realCalls == round && commitUI == 0 && NG2Fake.countTouches() == 0,
            "test111_kernel_return_alone_cannot_retire_old_callback")
        commitRelease.signal()
        if variant == "late_candidate" || round == 3 {
            pump("test111_late_hint_or_retry_limit_settled", timeout: 20) {
                cycleCompanion(id)["pending"]?.boolValue == false
            }
            let stopped = cycleCompanion(id)
            gate.lock(); let workerCount = entered.count; gate.unlock()
            require(workerCount == round && stopped["job_id"]?.intValue == Int(job) &&
                stopped["capture_id"]?.intValue == active["capture_id"]?.intValue,
                "test111_late_candidate_or_third_timeout_cannot_start_replacement")
            if variant == "late_candidate" {
                require(stopped["candidate_latched"]?.boolValue == true && stopped["outcome"]?.stringValue == "candidate" &&
                    stopped["assessment_status"]?.stringValue == "deadline",
                    "test111_late_candidate_vetoes_queued_fresh_source")
            } else {
                require(stopped["assessment_status"]?.stringValue == "deadline" && stopped["outcome"]?.stringValue == "unknown" &&
                    stopped["candidate_latched"]?.boolValue == false,
                    "test111_initial_plus_two_retries_never_certifies_unknown_as_negative")
            }
        } else {
            pump("test111_fresh_full_reaches_next_actual_worker", timeout: 20) {
                gate.lock(); defer { gate.unlock() }; return entered.count == round + 1
            }
            let retried = cycleCompanion(id)
            require(retried["job_id"]?.intValue == Int(firstJob) + round && retried["capture_id"]?.intValue == Int(queuedCapture) &&
                retried["capture_start_ns"]?.intValue == queuedStart && retried["prefix"]?.intValue == rootState["prefix"]?.intValue &&
                retried["hold_started_ns"]?.intValue == rootHold && retried["continuation_deadline_ns"]?.intValue == rootD &&
                retried["pending"]?.boolValue == true && retried["partial"]?.boolValue == false && NG2Fake.countTouches() == 0,
                "test111_new_worker_uses_exact_queued_data_identity_and_original_root_D")
            retryCapture = queuedCapture
        }
    }
    if variant == "retry" {
        workerRelease.signal()
        pump("test111_fresh_result_candidate_adopted", timeout: 20) {
            cycleCompanion(id)["candidate_latched"]?.boolValue == true
        }
        require(cycleCompanion(id)["capture_id"]?.intValue == Int(retryCapture) &&
            cycleCompanion(id)["assessment_status"]?.stringValue == "ok",
            "test111_fresh_worker_result_is_current_source_candidate")
    }
    if variant == "limit" {
        gate.lock(); let observed = observedFrames; pauseCaptures = false; gate.unlock(); captureRelease.signal()
        pump("test111_after_limit_fresh_full_still_cannot_create_job_four", timeout: 20) {
            gate.lock(); defer { gate.unlock() }; return observedFrames >= observed + 2
        }
        gate.lock(); let count = entered.count; gate.unlock()
        require(count == 3 && cycleCompanion(id)["job_id"]?.intValue == Int(firstJob) + 2 &&
            NG2Fake.countTouches() == 0, "test111_initial_and_maximum_two_retries_is_closed")
        _ = call("necro_native_cancel", id)
    } else {
        gate.lock(); pauseCaptures = false; gate.unlock(); captureRelease.signal()
    }
    NG2RuntimeTestHooks.scheduleTicket = nil
    NG2Fake.lock.lock(); let held = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
    for command in held { NG2Fake.releaseTicket(command) }
    pump("test111_terminal_actual_worker_capture_and_main_drain", timeout: 30) { cycleDrained(id) }
    require(NG2Fake.paths().isEmpty && NG2Fake.taps().allSatisfy { $0.x == 390 && $0.y == 448 },
        "test111_no_move_restart_purchase_or_unknown_resend")
    gate.lock(); let allCalls = kernelCalls, allWorkers = entered.count; gate.unlock()
    require(allCalls == allWorkers && allWorkers == (variant == "retry" ? 2 : variant == "limit" ? 3 : 1),
        "test111_each_admitted_worker_executes_real_kernel_exactly_once")
    let required: Set<Int> = variant == "retry" ? [Int(firstCapture), Int(retryCapture)] : [Int(firstCapture)]
    runtime111Manifest(id, required: required)
    runtime111PersistedPixels(root, capture: firstCapture, expected: original)
    if variant == "retry" {
        runtime111PersistedPixels(root, capture: retryCapture, expected: fresh)
        let files = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!
        var matched = false
        for case let url as URL in files where url.lastPathComponent.contains("checkpoint") {
            guard let bytes = try? Data(contentsOf: url),
                  let envelope = try? JSONDecoder().decode([String: JSONValue].self, from: bytes),
                  let body = envelope["payload"]?.objectValue,
                  body["cycle"]?.objectValue?["capture_id"]?.intValue == Int(retryCapture) else { continue }
            matched = body["raw_sha256"]?.stringValue == NG2CycleWire.hash(fresh) && body["assessment_adopted"]?.boolValue == true
        }
        require(matched, "test111_fresh_worker_exact_rgba_sha_and_adoption_persisted")
    }
    publishFixtureClaim(id, requiredCaptureIDs: required)
    NG2RuntimeCycleTestHooks.afterClassificationCall = nil
    NG2RuntimeTestHooks.beforeCaptureAdmission = nil
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    print("PASS TEST111 fresh deadline subcase " + variant)
}

let root111 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime111-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root111, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root111) }
NG2RuntimeCycleTestHooks.spoolRoot = root111
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case111 = CommandLine.arguments.last ?? ""
if case111 == "negative" {
    pump("test111_irregular_prepare_ready") {
        cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    // Exact legacy function and every existing assertion are compiled intact.
    testCycle094TwoShopsAndIntentCancel(root111, cancelIntent: false)
} else if case111 == "retention" || case111 == "candidate" {
    pump("test111_queue_prepare_ready") {
        cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    testFullData110QueueRetentionPublic(root111, candidateFirst: case111 == "candidate")
} else if case111 == "fresh_deadline" {
    pump("test111_fresh_prepare_ready") {
        cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    for variant in ["retry", "late_candidate", "limit"] {
        let subroot = root111.appendingPathComponent(variant)
        try FileManager.default.createDirectory(at: subroot, withIntermediateDirectories: true,
            attributes: [.posixPermissions: NSNumber(value: 0o700)])
        testFreshDeadline111CallbacksPublic(subroot, variant: variant)
    }
} else { require(false, "test111_unknown_case_is_not_another_fixture") }
print("PASS TEST111 CASE " + case111)
