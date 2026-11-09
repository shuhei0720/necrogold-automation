// TEST058 public baseline. Concatenate the existing Runtime test helpers before
// this file. This fixture uses only hooks already present in TEST057 Runtime;
// no preparation getter, new producer hook, or rewritten old source supplies Red.
// Received TEST057 cap46 left 5,017,107ns after observe; its replacement AX IPC
// consumed 11,311,875ns. We impose those two independent intervals. The original
// ticket, SAME proof, frozen deadline, real raster/beat/motion, and synth gate
// are all produced by the unchanged Runtime and Controller.
func test058PreparedContinuousDeadlinePublic() {
    NG2Fake.reset(.walk)
    NG2Fake.lock.lock()
    NG2Fake.walkY = 1; NG2Fake.walkGoodsEnabled = false
    NG2Fake.remoteVariantDuringWalk = true
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let id = identity()
    diagnoseFixture(id)
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        NG2Fake.waitForCapturePermit()
        NG2Fake.performBoundaryClockChange()
    }
    alignInitialFixtureMove(id)
    let observedRemainder: UInt64 = 5_017_107
    let replacementQueryCost: UInt64 = 11_311_875
    let stateLock = NSLock()
    var oldID: UInt64 = 0, replacementID: UInt64 = 0
    var original: [String: JSONValue] = [:]
    var armedObservation = false, lateObservationCompleted = false
    var actualObserveEnd: UInt64 = 0
    var queryingID = 0
    var queryStarts: [Int: UInt64] = [:], queryEnds: [Int: UInt64] = [:]
    var injectedQueries = 0
    var returned = Set<UInt64>()
    NG2RuntimeTestHooks.beforeMainAdmission = {
        let command = report(id)["current_command_id"]?.intValue ?? 0
        stateLock.lock(); queryingID = command; stateLock.unlock()
    }
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        stateLock.lock()
        let command = queryingID, inject = lateObservationCompleted
        queryStarts[command] = NG2Fake.virtualClock()
        if inject { injectedQueries += 1 }
        stateLock.unlock()
        if inject { NG2Fake.advance(replacementQueryCost) }
        stateLock.lock(); queryEnds[command] = NG2Fake.virtualClock(); stateLock.unlock()
    }
    NG2Fake.lock.unlock()
    NG2RuntimeObserveTestHooks.afterObserve = {
        stateLock.lock()
        if armedObservation {
            armedObservation = false; lateObservationCompleted = true
            actualObserveEnd = NG2Fake.virtualClock()
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        }
        stateLock.unlock()
    }
    NG2RuntimeTestHooks.afterTicketReturned = { command in
        stateLock.lock(); returned.insert(command); stateLock.unlock()
    }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let current = report(id)
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }),
              event["kind"]?.intValue == 4 else { return false }
        if (current["inputs"]?.intValue ?? 0) < 2 {
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: command) }
            callback(); return true
        }
        NG2Fake.holdTicket(command, callback)
        stateLock.lock()
        let first = oldID == 0
        if first { oldID = command; original = event } else { replacementID = command }
        stateLock.unlock()
        if first {
            NG2RuntimeTestHooks.beforeMainAuthority = nil
            let deadline = UInt64(event["deadline_ns"]!.intValue!)
            require(NG2Fake.changeClockAtCaptureBoundary {
                let captureStart = deadline-observedRemainder-2_000_000
                let now = NG2Fake.virtualClock()
                require(now <= captureStart, "test058_original_ticket_has_time_for_received_remainder")
                NG2Fake.advance(captureStart-now)
                NG2Fake.lock.lock(); NG2Fake.remoteVariant = 1; NG2Fake.lock.unlock()
                stateLock.lock(); armedObservation = true; stateLock.unlock()
            }, "test058_changed_capture_owns_clock_boundary")
        }
        return true
    }
    require(call("necro_native_start", id).1 == nil, "test058_deadline_public_start")
    pump("test058_real_continuous_SAME_replacement_created", timeout: 15) {
        let current = call("necro_native_status", id, keepalive: true).0?["report"]?.objectValue ?? [:]
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        stateLock.lock(); defer { stateLock.unlock() }
        // A due preparation can be executed directly in the production queue.
        // Its public event is still required even when it was never held here.
        if oldID != 0, let latest = events.last(where: {
            $0["kind"]?.intValue == 4 && $0["ordinal"] == original["ordinal"] && $0["id"]?.intValue != Int(oldID)
        }) { replacementID = UInt64(latest["id"]!.intValue!) }
        return replacementID != 0
    }
    let before = report(id)
    stateLock.lock()
    let old = oldID, replacement = replacementID, frozen = original
    let observedEnd = actualObserveEnd, starts = queryStarts, ends = queryEnds, injected = injectedQueries
    stateLock.unlock()
    let deadline = UInt64(frozen["deadline_ns"]!.intValue!)
    let moves = (before["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
    let replacementEvent = moves.first { $0["id"]?.intValue == Int(replacement) } ?? [:]
    let details = (before["scene_change_details"]?.arrayValue ?? []).compactMap { $0.objectValue }
    require([2, 3].contains(before["inputs"]?.intValue ?? -1) && before["moves"]?.intValue == 2 &&
        frozen["outcome"]?.intValue == 0 && moves.first(where: { $0["id"]?.intValue == Int(old) })?["begin_ns"]?.intValue == 0 &&
        details.last?["validation"]?.intValue == 2 &&
        ["ordinal", "target_ns", "not_before_ns", "deadline_ns", "direction", "x", "y"].allSatisfy { frozen[$0] == replacementEvent[$0] } &&
        frozen["source_capture_id"] != replacementEvent["source_capture_id"],
        "test058_real_two_MOVED_then_definitely_unsent_SAME_same_frozen_ticket")
    require(observedEnd+observedRemainder == deadline && starts[Int(old)] != nil &&
        (injected == 0 || (injected == 1 && ends[Int(replacement)]!-starts[Int(replacement)]! == replacementQueryCost)),
        "test058_received_observe_remainder_and_independent_AX_cost_are_exact")
    print("EVIDENCE test058 observe_remaining_ns=\(deadline-observedEnd) replacement_AX_ns=\(injected == 0 ? 0 : replacementQueryCost) old_id=\(old) replacement_id=\(replacement)")
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    NG2Fake.releaseTicket(replacement)
    pump("test058_replacement_callback_actually_returned") {
        stateLock.lock(); defer { stateLock.unlock() }; return returned.contains(replacement)
    }
    let after = report(id)
    let sent = (after["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["id"]?.intValue == Int(replacement) }
    require(after["inputs"]?.intValue == 3 && NG2Fake.paths().count == 3 && sent?["outcome"]?.intValue == 2 &&
        (sent?["begin_ns"]?.intValue ?? 0) >= frozen["not_before_ns"]!.intValue! &&
        (sent?["begin_ns"]?.intValue ?? Int.max) <= Int(deadline),
        "MISSING_prepared_continuous_reissue_sends_within_original_frozen_deadline")
    require(injected == 0 && starts[Int(replacement)] == nil && runtime.hasLease,
        "test058_same_logical_MOVE_reuses_original_fresh_AX_under_live_lease")
    let touches = NG2Fake.countTouches()
    NG2Fake.releaseTicket(old)
    pump("test058_old_callback_actually_returned") {
        stateLock.lock(); defer { stateLock.unlock() }; return returned.contains(old)
    }
    require(NG2Fake.countTouches() == touches && report(id)["dispatch_failure"] == .null,
        "test058_retired_callback_has_no_synth_or_failure_effect")
    _ = call("necro_native_cancel", id)
    NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    pump("test058_deadline_fixture_all_workers_drained") { drained(id) }
    fixtureFailureSnapshot = nil
    print("PASS TEST058 prepared continuous deadline public baseline")
}

test058PreparedContinuousDeadlinePublic()
