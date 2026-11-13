// TEST096 exercises a real synchronous main/control queue handoff with a
// 275ms PAUSE call. Clock/pixels/results remain procedural, not game evidence.
func testCycle096SlowPause(_ root: URL, negative: Bool) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    let finished = DispatchSemaphore(value: 0)
    var resultReady = false, firstFinish: UInt64 = 0, firstDeadline: UInt64 = 0
    var pauseBegin: UInt64 = 0, pauseEnd: UInt64 = 0, pauseCount = 0
    var restarted = false, settle = false, settleNext = false
    let first = cycleSearchPixels(worldX: 0, variant: 0, goods: 1)
    let next = cycleSearchPixels(worldX: 36, variant: 1, goods: 1)
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let changed = restarted; gate.unlock()
        return changed ? next : first
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        gate.lock(); let changed = restarted; gate.unlock()
        clock.advance(20_000_000)
        let end = NG2Runtime.now()
        if negative && !changed { result = cycle095Negative(scene, result.started_ns, end) }
        else { ng2_fixture_cycle_result(scene, result.started_ns, end, 1, &result) }
        let deadline = cycleCompanion(id)["deadline_ns"]?.intValue ?? 0
        gate.lock()
        if !resultReady { firstFinish = result.finished_ns; firstDeadline = UInt64(max(deadline, 0)) }
        resultReady = true
        gate.unlock()
        finished.signal()
    }
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); restarted = true; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
        guard x == 390 && y == 448 else { return }
        gate.lock(); let firstPause = pauseCount == 0; pauseCount += 1
        let ready = resultReady; gate.unlock()
        guard firstPause else { return }
        // The worker never waits for PAUSE. The old queue ordering lets this
        // call start first; the fixed ordering adopts before entering it.
        if !ready { require(finished.wait(timeout: .now() + 5) == .success, "cycle096_worker_finished_inside_synchronous_pause") }
        let begin = NG2Runtime.now()
        Thread.sleep(forTimeInterval: 0.275)
        clock.advance(275_000_000)
        let end = NG2Runtime.now()
        gate.lock(); pauseBegin = begin; pauseEnd = end; gate.unlock()
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id)
        gate.lock()
        let advance = negative && !settle && state["pending"]?.boolValue == false &&
            state["outcome"]?.stringValue == "negative" && (state["pause_capture_id"]?.intValue ?? 0) > 0 &&
            (state["durable_ns"]?.intValue ?? 0) > 0
        if advance { settle = true }
        // As in TEST095, time must also pass after RESTART before C may PAUSE
        // the next shop. Advance only after that candidate was adopted.
        let advanceNext = negative && !settleNext && (state["level_id"]?.intValue ?? 0) >= 2 &&
            state["pending"]?.boolValue == false && state["assessment_status"]?.stringValue == "ok" &&
            state["outcome"]?.stringValue == "candidate"
        if advanceNext { settleNext = true }
        gate.unlock()
        if advance || advanceNext { clock.advance(220_000_000) }
    }
    cycleStart(id)
    pump("cycle096_slow_pause_drained", timeout: 30) { cycleDrained(id) }
    let state = cycleCompanion(id), taps = NG2Fake.taps()
    gate.lock()
    let observedFinish = firstFinish, deadline = firstDeadline, begin = pauseBegin, end = pauseEnd
    gate.unlock()
    require(observedFinish > 0 && deadline >= observedFinish && begin >= observedFinish && end >= begin + 275_000_000,
        "cycle096_fixture_has_on_time_result_and_synchronous_275ms_pause")
    require(state["assessment_status"]?.stringValue == "ok" && state["outcome"]?.stringValue == "candidate",
        "cycle096_pause_does_not_expire_completed_worker")
    if negative {
        require(taps.count == 3 && taps.filter { $0.x == 144 && $0.y == 448 }.count == 1 &&
            state["level_id"]?.intValue == 2 && state["completed_shops"]?.intValue == 2,
            "cycle096_slow_pause_negative_keeps_one_durable_restart")
        do {
            let records = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: "fixture-owner").records()
            require(records.filter { $0.kind == "restart_intent" }.count == 1 &&
                records.filter { $0.kind == "restart_outcome" }.count == 1,
                "cycle096_slow_pause_exact_intent_and_outcome")
        } catch { require(false, "cycle096_slow_pause_exact_intent_and_outcome") }
    } else {
        require(taps.count == 1 && taps[0].x == 390 && taps[0].y == 448 &&
            (state["assessment_ns"]?.intValue ?? Int.max) <= Int(begin) &&
            (state["assessment_ns"]?.intValue ?? Int.max) <= Int(deadline),
            "cycle096_candidate_adopted_before_pause_and_original_deadline")
    }
    require(NG2Fake.paths().isEmpty, "cycle096_slow_pause_no_purchase_or_movement")
    publishFixtureClaim(id)
    print(negative ? "PASS TEST096 on-time negative survives 275ms PAUSE and restarts once" :
          "PASS TEST096 on-time candidate adopted before synchronous 275ms PAUSE")
}

func testCycle096HungWorkerDeadline(_ root: URL) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    let release = DispatchSemaphore(value: 0)
    var entered = false
    cycleProof(1)
    NG2RuntimeCycleTestHooks.beforeClassification = { _ in
        gate.lock(); entered = true; gate.unlock(); release.wait()
    }
    cycleStart(id)
    pump("cycle096_hung_worker_entered") { gate.lock(); defer { gate.unlock() }; return entered }
    let deadline = cycleCompanion(id)["deadline_ns"]?.intValue ?? 0
    let before = NG2Runtime.now()
    require(deadline > 0, "cycle096_original_worker_deadline_available")
    clock.advance(UInt64(max(deadline - Int(before), 0)) + 1)
    pump("cycle096_hung_worker_original_deadline_paused", timeout: 20) {
        let state = cycleCompanion(id)
        return state["assessment_status"]?.stringValue == "deadline" && (state["pause_capture_id"]?.intValue ?? 0) > 0
    }
    require(!cycleDrained(id) && runtime.hasLease && NG2Fake.taps().count == 1 && NG2Fake.paths().isEmpty,
        "cycle096_hung_worker_does_not_hold_pause_forever_or_fake_drain")
    release.signal()
    pump("cycle096_hung_worker_late_result_drained", timeout: 20) { cycleDrained(id) }
    require(cycleCompanion(id)["assessment_status"]?.stringValue == "deadline" &&
        cycleCompanion(id)["outcome"]?.stringValue == "unknown" && NG2Fake.taps().count == 1,
        "cycle096_late_candidate_cannot_restore_expired_authority")
    publishFixtureClaim(id)
    print("PASS TEST096 hung worker bypasses wait after original deadline and late result stays inert")
}

func testCycle096IntentCancel(_ root: URL) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    let release = DispatchSemaphore(value: 0)
    var entered = false, settled = false
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        result = cycle095Negative(scene, result.started_ns, NG2Runtime.now())
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id)
        gate.lock()
        let advance = !settled && state["pending"]?.boolValue == false && state["outcome"]?.stringValue == "negative" &&
            (state["pause_capture_id"]?.intValue ?? 0) > 0 && (state["durable_ns"]?.intValue ?? 0) > 0
        if advance { settled = true }
        gate.unlock()
        if advance { clock.advance(220_000_000) }
    }
    NG2RuntimeCycleTestHooks.beforeIntentWrite = { _ in gate.lock(); entered = true; gate.unlock(); release.wait() }
    cycleStart(id)
    pump("cycle096_exact_intent_writer_entered", timeout: 20) { gate.lock(); defer { gate.unlock() }; return entered }
    require(NG2Fake.taps().count == 1, "cycle094_uncommitted_intent_restart_zero")
    _ = call("necro_native_cancel", id)
    require(!cycleDrained(id), "cycle094_cancel_does_not_fake_writer_drain")
    release.signal()
    pump("cycle096_intent_cancel_actual_drain", timeout: 30) { cycleDrained(id) }
    require(NG2Fake.taps().filter { $0.x == 144 && $0.y == 448 }.isEmpty,
        "cycle094_late_durable_intent_cannot_dispatch_after_cancel")
    NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert("fixture-recovery-owner"); NG2Fake.lock.unlock()
    var recovered: [String: JSONValue]?
    pump("cycle096_dangling_intent_readonly_recovery", timeout: 20) {
        recovered = cycleCall(id, owner: "fixture-recovery-owner").0?["payload"]?.objectValue
        return recovered != nil
    }
    require(recovered?["state"]?.stringValue == "stopped" && recovered?["input_state"]?.intValue == 4 &&
        recovered?["ui_frozen"]?.boolValue == true && NG2Fake.taps().count == 1,
        "cycle094_dangling_intent_recovers_unknown_frozen_without_resend")
    require(NG2Fake.paths().isEmpty, "cycle094_full_visible_world_no_purchase")
    publishFixtureClaim(id)
    print("PASS TEST096 durable intent cancellation keeps zero restart and frozen dangling recovery")
}

// TEST096 ENTRYPOINTS BEGIN.
let cycle096Root = FileManager.default.temporaryDirectory.appendingPathComponent("runtime-pause096-" + UUID().uuidString)
try FileManager.default.createDirectory(at: cycle096Root, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: cycle096Root) }
NG2RuntimeCycleTestHooks.spoolRoot = cycle096Root
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
pump("cycle096_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
// TEST096 CASE CALLS BEGIN.
testCycle096SlowPause(cycle096Root, negative: false)
testCycle096SlowPause(cycle096Root, negative: true)
testCycle096HungWorkerDeadline(cycle096Root)
testCycle096IntentCancel(cycle096Root)
testCycle094WorkerCancelAndDrain(cycle096Root)
testCycle095Wire()
testCycle095NegativeRestart(cycle096Root)
testCycle095Hold(cycle096Root, partial: false)
testCycle095Hold(cycle096Root, partial: true)
test058EveryPreparationIdentityField()
test058PreparedContinuousCase("prefix")
test058PreparedContinuousCase("cancel")
print("PASS TEST096 bounded PAUSE ordering four new cases, worker cancellation, four target-only and three legacy callbacks; procedural clock/pixels/classifier")
