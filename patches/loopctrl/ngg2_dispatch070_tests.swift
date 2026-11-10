// TEST070 focused public Runtime fixture. Concatenate only the common helpers
// before "// This public request is intentionally runnable" from
// ngg2_runtime_tests.swift. The real raster, C planner, motion proof, frozen
// ticket, preparation epoch and final synth gate produce every action.
// The intervals below independently model the received dispatch boundary;
// this is synthetic queue-cost coverage, not replay of missing device frames.
func test070DeferredEvidenceDispatchPublic() {
    NG2Fake.reset(.walk)
    NG2Fake.lock.lock()
    NG2Fake.walkY = 1; NG2Fake.walkGoodsEnabled = false
    NG2Fake.remoteVariantDuringWalk = true
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let id = identity(), state = NSLock()
    diagnoseFixture(id)
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        NG2Fake.waitForCapturePermit(); NG2Fake.performBoundaryClockChange()
    }
    alignInitialFixtureMove(id)
    let observeRemainder: UInt64 = 3_181_000
    let retentionCost: UInt64 = 6_463_000, repeatedQueryCost: UInt64 = 10_256_000
    let finalCost: UInt64 = 104_000
    var oldID: UInt64 = 0, replacementID: UInt64 = 0
    var original: [String: JSONValue] = [:], replacement: [String: JSONValue] = [:]
    var originalAuthority: [UInt64]?, replacementAuthority: [UInt64]?
    var expectedObserveEnd: UInt64 = 0, actualObserveEnd: UInt64 = 0
    var armed = false, observed = false, finalEntered = false
    var retentionStart: UInt64 = 0, retentionEnd: UInt64 = 0, retentionBeforeFinal = false
    var queryingID: UInt64 = 0, repeatedQueries = 0
    var queryStart: UInt64 = 0, queryEnd: UInt64 = 0, gateEntry: UInt64 = 0
    var returned = Set<UInt64>()
    NG2RuntimeTestHooks.beforeMainAdmission = {
        let currentID = UInt64(max(0, report(id)["current_command_id"]?.intValue ?? 0))
        state.lock(); queryingID = currentID; state.unlock()
    }
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        state.lock()
        let repeatQuery = observed && queryingID == oldID+1
        if repeatQuery { repeatedQueries += 1; queryStart = NG2Fake.virtualClock() }
        state.unlock()
        if repeatQuery { NG2Fake.advance(repeatedQueryCost) }
        state.lock(); if repeatQuery { queryEnd = NG2Fake.virtualClock() }; state.unlock()
    }
    NG2Fake.lock.unlock()
    NG2RuntimeObserveTestHooks.afterObserve = {
        state.lock()
        if armed && NG2Fake.virtualClock() >= expectedObserveEnd {
            armed = false; observed = true; actualObserveEnd = NG2Fake.virtualClock()
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        }
        state.unlock()
    }
    NG2RuntimeTestHooks.beforeEvidenceRetention = { currentCommandID in
        // The baseline seam precedes its snapshot publication. Identify the
        // new C ticket by the provided scalar, never by an injected report.
        state.lock()
        let inject = observed && oldID != 0 && currentCommandID == oldID+1 && retentionStart == 0
        if inject {
            retentionStart = NG2Fake.virtualClock(); retentionBeforeFinal = !finalEntered
        }
        state.unlock()
        if inject { NG2Fake.advance(retentionCost) }
        state.lock(); if inject { retentionEnd = NG2Fake.virtualClock() }; state.unlock()
    }
    NG2RuntimeTestHooks.afterTicketReturned = { command in
        state.lock(); returned.insert(command); state.unlock()
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
        state.lock(); let first = oldID == 0
        if first { oldID = command; original = event } else { replacementID = command; replacement = event }
        state.unlock()
        if !first {
            NG2RuntimeTestHooks.beforeMainAuthority = {
                let authority = runtime.testPreparedAuthority(id, commandID: command)
                state.lock()
                finalEntered = true; gateEntry = NG2Fake.virtualClock(); replacementAuthority = authority
                state.unlock()
                NG2Fake.advance(finalCost)
            }
            // Exercise the actual due-ticket branch. Holding/releasing this
            // callback would hide diagnostic work ahead of real dispatch.
            return false
        }
        NG2Fake.holdTicket(command, callback)
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        let authority = runtime.testPreparedAuthority(id, commandID: command)
        state.lock(); originalAuthority = authority; state.unlock()
        let deadline = UInt64(event["deadline_ns"]!.intValue!)
        require(NG2Fake.changeClockAtCaptureBoundary {
            let captureStart = deadline-observeRemainder-2_000_000
            let now = NG2Fake.virtualClock()
            require(now <= captureStart, "test070_original_ticket_has_time_for_changed_capture")
            NG2Fake.advance(captureStart-now)
            NG2Fake.lock.lock()
            NG2Fake.remoteVariant = 1; NG2Fake.captureLimit = NG2Fake.requests+1
            NG2Fake.lock.unlock()
            state.lock(); expectedObserveEnd = deadline-observeRemainder; armed = true; state.unlock()
        }, "test070_changed_capture_owns_exact_clock_boundary")
        return true
    }
    require(call("necro_native_start", id).1 == nil, "test070_deferred_evidence_public_start")
    pump("test070_real_reissue_callback_and_retention_returned", timeout: 15) {
        _ = call("necro_native_status", id, keepalive: true)
        state.lock(); defer { state.unlock() }
        return replacementID != 0 && returned.contains(replacementID) && retentionEnd != 0
    }
    let after = report(id)
    state.lock()
    let old = oldID, new = replacementID, frozen = original, next = replacement
    let beforeAuthority = originalAuthority, afterAuthority = replacementAuthority
    let observeEnd = actualObserveEnd, entry = gateEntry, injected = repeatedQueries
    let retentionDuration = retentionEnd-retentionStart, prematureRetention = retentionBeforeFinal
    let repeatDuration = queryEnd-queryStart
    state.unlock()
    let events = (after["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let sent = events.first { $0["id"]?.intValue == Int(new) } ?? [:]
    let deadline = UInt64(frozen["deadline_ns"]!.intValue!)
    require(after["inputs"]?.intValue == 3 && NG2Fake.paths().count == 3 &&
        sent["outcome"]?.intValue == 2 && injected == 0 && !prematureRetention &&
        (sent["begin_ns"]?.intValue ?? Int.max) <= Int(deadline),
        "MISSING_test070_due_reissue_prepares_before_evidence_retention")
    require(after["moves"]?.intValue == 2 && observeEnd+observeRemainder == deadline &&
        retentionDuration == retentionCost && entry == observeEnd &&
        sent["begin_ns"]?.intValue == Int(entry+finalCost) && repeatDuration == 0,
        "test070_independent_queue_costs_preserve_original_observe_and_gate_clock")
    require(new == old+1 && beforeAuthority != nil && beforeAuthority == afterAuthority &&
        beforeAuthority![3] != 0 && frozen["source_capture_id"] != next["source_capture_id"] &&
        ["ordinal", "target_ns", "not_before_ns", "deadline_ns", "direction", "x", "y"].allSatisfy {
            frozen[$0] == next[$0]
        } && events.first(where: { $0["id"]?.intValue == Int(old) })?["begin_ns"]?.intValue == 0,
        "test070_real_SAME_reissue_keeps_original_epoch_sample_and_all_frozen_ticket_fields")
    let sourceIDs = [UInt64(frozen["source_capture_id"]!.intValue!), UInt64(next["source_capture_id"]!.intValue!)]
    let evidence = runtime.testOriginalFrameEvidence(id, captureIDs: sourceIDs)
    require(evidence?.count == 2 && sourceIDs.allSatisfy {
        evidence?[$0]?.1["capture_id"]?.intValue == Int($0)
    } && after["dispatch_failure"] == .null,
        "test070_deferred_retention_keeps_both_original_source_images_and_coherent_report")
    let touches = NG2Fake.countTouches()
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    NG2Fake.releaseTicket(old)
    pump("test070_stale_original_callback_returns") {
        state.lock(); defer { state.unlock() }; return returned.contains(old)
    }
    require(NG2Fake.countTouches() == touches && report(id)["dispatch_failure"] == .null,
        "test070_stale_callback_cannot_send_or_replace_dispatch_diagnostic")
    NG2RuntimeTestHooks.beforeEvidenceRetention = nil
    NG2RuntimeObserveTestHooks.afterObserve = nil
    _ = call("necro_native_cancel", id)
    NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    pump("test070_deferred_evidence_workers_drain", timeout: 15) { drained(id) }
    require(report(id)["workers_drained"]?.boolValue == true && !runtime.hasLease,
        "test070_retained_evidence_does_not_release_live_callbacks_early")
    fixtureFailureSnapshot = nil
    print("PASS TEST070 public Runtime deferred evidence dispatch and frozen preparation epoch")
}

