// TEST058 public baseline. Concatenate the existing Runtime test helpers before
// this file. This fixture uses only hooks already present in TEST057 Runtime;
// no preparation getter, new producer hook, or rewritten old source supplies Red.
// Received TEST057 cap46 left 5,017,107ns after observe; its replacement AX IPC
// consumed 11,311,875ns. We impose those two independent intervals. The original
// ticket, SAME proof, frozen deadline, real raster/beat/motion, and synth gate
// are all produced by the unchanged Runtime and Controller.
func test058PreparedContinuousDeadlinePublic() {
    test058PreparedContinuousCase("none")
    #if NG2_PREPARATION_TEST058_GREEN
    for fault in ["generation", "pid", "prefix", "cancel", "owner", "lock", "controller", "deadline_equal",
                  "too_late", "too_early", "authority_equal", "authority_plus_one", "authority_reverse", "direct_due"] {
        test058PreparedContinuousCase(fault)
    }
    test058EveryPreparationIdentityField()
    for fresh in [false, true] {
        for staleFirst in [true, false] { test058TwoReissuesPublic(fresh: fresh, staleFirst: staleFirst) }
    }
    for exit in ["cancel", "expired", "terminal"] {
        test058TwoReissuesPublic(fresh: false, staleFirst: false, retentionExit: exit)
    }
    #endif
}

func test058PreparedContinuousCase(_ fault: String) {
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
    #if NG2_PREPARATION_TEST058_GREEN
    let ownerWatchdog = fault == "owner" ? TestOwnerWatchdogFence(id) : nil
    var originalAuthority: [UInt64]?
    var finalEntered = false
    var directDispatches: [UInt64] = []
    NG2RuntimeTestHooks.beforeDueDispatch = { command in stateLock.lock(); directDispatches.append(command); stateLock.unlock() }
    NG2RuntimeTestHooks.beforeReportEncode = { origin, _ in
        stateLock.lock(); let premature = fault == "none" && lateObservationCompleted && !finalEntered; stateLock.unlock()
        if origin == "flush" && premature {
            // Independent diagnostic cost, not an invented TEST057 substage.
            NG2Fake.advance(20_000_000)
            require(false, "test058_full_JSON_waits_until_timed_callback_has_entered_main")
        }
    }
    #endif
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
        stateLock.lock()
        let first = oldID == 0
        if first { oldID = command; original = event } else { replacementID = command }
        stateLock.unlock()
        #if NG2_PREPARATION_TEST058_GREEN
        if !first && fault == "direct_due" {
            NG2RuntimeTestHooks.beforeMainAuthority = {
                require(originalAuthority == runtime.testPreparedAuthority(id, commandID: command),
                    "test058_direct_due_uses_unchanged_original_sample_at_real_main_gate")
                stateLock.lock(); finalEntered = true; stateLock.unlock()
            }
            return false
        }
        #endif
        NG2Fake.holdTicket(command, callback)
        if first {
            NG2RuntimeTestHooks.beforeMainAuthority = nil
            #if NG2_PREPARATION_TEST058_GREEN
            originalAuthority = runtime.testPreparedAuthority(id, commandID: command)
            #endif
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
        stateLock.lock()
        // A due preparation can be executed directly in the production queue.
        // Its public event is still required even when it was never held here.
        if oldID != 0, let latest = events.last(where: {
            $0["kind"]?.intValue == 4 && $0["ordinal"] == original["ordinal"] && $0["id"]?.intValue != Int(oldID)
        }) { replacementID = UInt64(latest["id"]!.intValue!) }
        let offeredID = replacementID, alreadyReturned = returned.contains(replacementID)
        stateLock.unlock()
        guard offeredID != 0 else { return false }
        if fault == "direct_due" { return alreadyReturned }
        // Publishing the C event precedes prepare() and the actual callback
        // offer. Releasing before holdTicket would be a lost no-op release.
        NG2Fake.lock.lock(); let offered = NG2Fake.heldTickets[offeredID] != nil; NG2Fake.lock.unlock()
        return offered
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
    #if NG2_PREPARATION_TEST058_GREEN
    NG2RuntimeTestHooks.beforeMainAuthority = {
        stateLock.lock(); finalEntered = true; stateLock.unlock()
        // The control caller is synchronously stopped at this hook. Test final
        // admission separately from a timer that may legitimately revoke first.
        if fault == "owner" {
            ownerWatchdog!.park()
            NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = false; NG2Fake.lock.unlock()
        }
        if fault == "lock" { LockStateMonitor.monitor.isLocked = true }
        if fault == "controller" { runtime.testInvalidateControllerTicket(id) }
        if fault == "deadline_equal" { NG2Fake.advance(observedRemainder) }
        if fault == "too_late" { NG2Fake.advance(observedRemainder+1) }
        if fault == "too_early" {
            NG2Fake.lock.lock(); NG2Fake.fixedClock = UInt64(frozen["not_before_ns"]!.intValue!)-1; NG2Fake.lock.unlock()
        }
        if ["authority_equal", "authority_plus_one", "authority_reverse"].contains(fault), let authority = originalAuthority {
            let now = fault == "authority_reverse" ? authority[1]-1
                : authority[0]+1_000_000_000+(fault == "authority_plus_one" ? 1 : 0)
            NG2Fake.lock.lock(); NG2Fake.fixedClock = now; NG2Fake.lock.unlock()
        }
    }
    require(originalAuthority != nil && (fault == "direct_due" || originalAuthority == runtime.testPreparedAuthority(id, commandID: replacement)),
        "test058_qualified_reissue_preserves_original_sample_start_end_preparedID_and_epoch_"+fault)
    var previousContext: [UInt64]?
    if fault == "generation" { _ = runtime.testFailureGeneration(id, advance: true) }
    if fault == "pid" { previousContext = runtime.testPreparationContext(id, expectedPID: 43) }
    if fault == "prefix" { previousContext = runtime.testPreparationContext(id, prefix: 999_999) }
    if fault == "cancel" { _ = call("necro_native_cancel", id) }
    #endif
    NG2Fake.releaseTicket(replacement)
    pump("test058_replacement_callback_actually_returned") {
        stateLock.lock(); defer { stateLock.unlock() }; return returned.contains(replacement)
    }
    let after = report(id)
    let sent = (after["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["id"]?.intValue == Int(replacement) }
    if fault == "none" || fault == "deadline_equal" || fault == "direct_due" {
        require(after["inputs"]?.intValue == 3 && NG2Fake.paths().count == 3 && sent?["outcome"]?.intValue == 2 &&
            (sent?["begin_ns"]?.intValue ?? 0) >= frozen["not_before_ns"]!.intValue! &&
            (sent?["begin_ns"]?.intValue ?? Int.max) <= Int(deadline),
            "MISSING_prepared_continuous_reissue_sends_within_original_frozen_deadline")
        require(injected == 0 && starts[Int(replacement)] == nil && runtime.hasLease,
            "test058_same_logical_MOVE_reuses_original_fresh_AX_under_live_lease")
    } else {
        require(after["inputs"]?.intValue == 2 && NG2Fake.paths().count == 2 && sent?["begin_ns"]?.intValue == 0,
            "test058_final_qualified_preparation_rejects_changed_"+fault)
        let expectedCodes = ["pid": "controller_rejected", "prefix": "controller_rejected", "owner": "owner",
            "lock": "locked", "controller": "controller_rejected", "too_late": "too_late", "too_early": "too_early",
            "authority_equal": "too_late", "authority_plus_one": "authority_stale", "authority_reverse": "authority_stale"]
        if let expected = expectedCodes[fault] {
            require(after["dispatch_failure"]?.objectValue?["code"]?.stringValue == expected,
                "test058_changed_preparation_preserves_dispatch_failure_classification_"+fault)
        } else {
            require(after["dispatch_failure"] == .null, "test058_cancelled_or_old_generation_callback_is_silent_"+fault)
        }
    }
    #if NG2_PREPARATION_TEST058_GREEN
    if fault == "direct_due" {
        require(directDispatches.filter { $0 == replacement }.count == 1,
            "test058_due_prepared_ticket_runs_inline_before_any_queue_handoff")
    }
    if let previousContext { _ = runtime.testPreparationContext(id, expectedPID: pid_t(previousContext[0]), prefix: previousContext[1]) }
    NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.lock.unlock()
    LockStateMonitor.monitor.isLocked = false
    ownerWatchdog?.finish()
    #endif
    let failureBeforeOld = report(id)["dispatch_failure"]
    let touches = NG2Fake.countTouches()
    NG2Fake.releaseTicket(old)
    pump("test058_old_callback_actually_returned") {
        stateLock.lock(); defer { stateLock.unlock() }; return returned.contains(old)
    }
    require(NG2Fake.countTouches() == touches && report(id)["dispatch_failure"] == failureBeforeOld,
        "test058_retired_callback_has_no_synth_or_failure_effect")
    _ = call("necro_native_cancel", id)
    NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    pump("test058_deadline_fixture_all_workers_drained") { drained(id) }
    fixtureFailureSnapshot = nil
    #if NG2_PREPARATION_TEST058_GREEN
    NG2RuntimeTestHooks.beforeReportEncode = nil
    NG2RuntimeTestHooks.beforeDueDispatch = nil
    #endif
}

#if NG2_PREPARATION_TEST058_GREEN
// This procedural variant starts with two UNKNOWN side cells and reveals
// FLOOR with the bracketed shop. It is independent of the DIRT-ACK fixture:
// the new LEFT action is safe FLOOR, permitting a later SAME in that epoch.
func test058FreshFloorRGBA(_ source: Data, worldY: Int32, revealed: Bool, secondChange: Bool) -> Data {
    var rgba = source
    rgba.withUnsafeMutableBytes { raw in
        let bytes = raw.bindMemory(to: UInt8.self)
        for x in [-1, -2] {
            let cx = 448+36*x, cy = 207-Int(worldY)
            let color = revealed ? [26, 16, 16] : [0, 0, 0]
            for py in max(0, cy-17)..<min(414, cy+18) {
                for px in max(0, cx-17)..<min(896, cx+18) {
                    let wx = UInt32(truncatingIfNeeded: px), wy = UInt32(truncatingIfNeeded: py+Int(worldY))
                    var hash = (wx &* 0x9e3779b9) ^ (wy &* 0x85ebca6b)
                    hash ^= hash >> 16; hash = hash &* 0x7feb352d; hash ^= hash >> 15
                    let noise = Int(hash % 9)-4, at = (py*896+px)*4
                    for channel in 0..<3 { bytes[at+channel] = UInt8(max(0, min(255, color[channel]+noise))) }
                }
            }
        }
        if secondChange {
            require(ng2_fixture_remote_cell(bytes.baseAddress, bytes.count, 2) == 1,
                "test058_second_remote_cell_is_rendered_before_real_analysis")
        }
    }
    return rgba
}

func test058DeferredReportsPublic(_ id: String, sourceIDs: Set<Int>, cancelWhileHeld: Bool) {
    let before = report(id), initialAccepted = before["accepted_frames"]!.intValue!
    let initialCapture = before["last_capture_id"]!.intValue!, prefix = before["last_completed_id"]!
    require(runtime.testSaturateLiveDiagnosticPins(id), "test058_live_diagnostic_pressure_uses_real_retained_raster")
    let state = NSLock(), releaseEncode = DispatchSemaphore(value: 0)
    var committed = 0, claimed = false, finished = false
    var oldProjection: [String: JSONValue] = [:]
    NG2RuntimeObserveTestHooks.afterObserve = {
        state.lock(); committed += 1; let stop = committed == 1 || committed == 6; state.unlock()
        if stop { NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock() }
    }
    NG2RuntimeTestHooks.beforeReportEncode = { origin, _ in
        guard origin == "response", !Thread.isMainThread else { return }
        state.lock(); let hold = !claimed; if hold { claimed = true }; state.unlock()
        if hold {
            // Resume five more real captures while this old immutable response
            // waits. Holding this callback must not retain the run admission lock.
            NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
            require(releaseEncode.wait(timeout: .now()+5) == .success, "test058_old_report_encoder_released")
        }
    }
    DispatchQueue.global().async {
        while true {
            let response = report(id)
            state.lock()
            if claimed { oldProjection = response; finished = true; state.unlock(); return }
            state.unlock()
            Thread.sleep(forTimeInterval: 0.001)
        }
    }
    NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 1_000_000; NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    pump("test058_old_immutable_report_encoder_is_held") { state.lock(); defer { state.unlock() }; return claimed }
    pump("test058_six_actual_commits_run_while_old_JSON_is_held") {
        state.lock(); defer { state.unlock() }; return committed == 6
    }
    var latest = report(id)
    pump("test058_latest_typed_snapshot_is_visible_during_old_encode") {
        latest = report(id)
        return latest["accepted_frames"]?.intValue == initialAccepted+6
    }
    let newRows = (latest["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { ($0["id"]?.intValue ?? 0) > initialCapture }
    require(newRows.count == 6 && newRows.allSatisfy {
        $0["stable"]?.boolValue == true && $0["completed_prefix_start"] == prefix && $0["completed_prefix_end"] == prefix
    } && latest["pinned_image_count"]?.intValue == 20 && latest["recent_image_count"]?.intValue == 4 &&
        sourceIDs.isDisjoint(with: Set((latest["missing_capture_ids"]?.arrayValue ?? []).compactMap { $0.intValue })),
        "test058_six_commits_preserve_original_comparisons_after_recent4_and_pin20_pressure")
    if cancelWhileHeld {
        require(call("necro_native_cancel", id).1 == nil, "test058_cancel_RPC_remains_responsive_during_old_JSON_encode")
    }
    let newestCapture = UInt64(latest["last_capture_id"]!.intValue!)
    releaseEncode.signal()
    pump("test058_old_encoder_actually_returns") { state.lock(); defer { state.unlock() }; return finished }
    state.lock(); let oldCapture = oldProjection["last_capture_id"]?.intValue ?? Int.max; state.unlock()
    require(oldCapture < Int(newestCapture) && (runtime.testCachedControllerCapture(id) ?? 0) >= newestCapture,
        "test058_late_old_JSON_never_overwrites_newer_controller_snapshot_cache")
    NG2RuntimeObserveTestHooks.afterObserve = nil
    NG2RuntimeTestHooks.beforeReportEncode = nil
}

func test058TwoReissuesPublic(fresh: Bool, staleFirst: Bool, retentionExit: String? = nil) {
    NG2Fake.reset(.walk)
    NG2Fake.lock.lock()
    NG2Fake.walkY = fresh ? 2 : 1; NG2Fake.walkGoodsEnabled = false
    NG2Fake.remoteVariantDuringWalk = !fresh; NG2Fake.freshRevalidationWorld = fresh
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let id = identity(); diagnoseFixture(id)
    NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.waitForCapturePermit(); NG2Fake.performBoundaryClockChange() }
    alignInitialFixtureMove(id)
    if fresh {
        NG2RuntimeTestHooks.analysisRGBA = { raw in
            NG2Fake.lock.lock()
            let y = NG2Fake.walkY*36, reveal = NG2Fake.freshRevalidationVariant == 1, second = NG2Fake.remoteVariant == 2
            NG2Fake.lock.unlock()
            return test058FreshFloorRGBA(raw, worldY: y, revealed: reveal, secondChange: second)
        }
    }
    var recordedFamily: [[String: JSONValue]] = [], recordedAuthorities: [[UInt64]] = []
    var originalMotionDeadline: JSONValue?
    let stateLock = NSLock(); var returned = Set<UInt64>()
    NG2RuntimeTestHooks.afterTicketReturned = { command in stateLock.lock(); returned.insert(command); stateLock.unlock() }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let current = report(id)
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }), event["kind"]?.intValue == 4 else { return false }
        if (current["inputs"]?.intValue ?? 0) < 2 {
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: command) }
            callback(); return true
        }
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        NG2Fake.holdTicket(command, callback)
        guard let authority = runtime.testPreparedAuthority(id, commandID: command) else {
            require(false, "test058_two_reissues_have_live_preparation"); return true
        }
        stateLock.lock()
        recordedFamily.append(event); recordedAuthorities.append(authority)
        let familyCount = recordedFamily.count
        if originalMotionDeadline == nil { originalMotionDeadline = current["motion_wait"]?.objectValue?["deadline_ns"] }
        let sameMotionDeadline = originalMotionDeadline == current["motion_wait"]?.objectValue?["deadline_ns"]
        stateLock.unlock()
        require(sameMotionDeadline,
            "test058_two_reissues_do_not_extend_original_motion_horizon")
        NG2Fake.lock.lock()
        NG2Fake.fixedCaptureAdvance = 5_000_000
        if fresh { NG2Fake.freshRevalidationVariant = 1 }
        NG2Fake.remoteVariant = familyCount == 1 ? 1 : 2
        if familyCount == 3 { NG2Fake.captureLimit = NG2Fake.requests }
        NG2Fake.lock.unlock()
        return true
    }
    require(call("necro_native_start", id).1 == nil, "test058_two_reissues_public_start")
    pump("test058_two_qualified_reissues_created", timeout: 15) {
        _ = call("necro_native_status", id, keepalive: true)
        stateLock.lock(); defer { stateLock.unlock() }; return recordedFamily.count == 3
    }
    stateLock.lock(); let family = recordedFamily, authorities = recordedAuthorities; stateLock.unlock()
    let current = report(id), original = family[0], latest = family[2]
    let oldIDs = family.prefix(2).map { UInt64($0["id"]!.intValue!) }, latestID = UInt64(latest["id"]!.intValue!)
    let details = (current["scene_change_details"]?.arrayValue ?? []).compactMap { $0.objectValue }
    require(details.map { $0["validation"]?.intValue ?? -1 } == (fresh ? [12, 2] : [2, 2]) &&
        details.map { $0["chain_count"]?.intValue ?? -1 } == [1, 2] &&
        family.allSatisfy { event in ["ordinal", "target_ns", "not_before_ns", "deadline_ns"].allSatisfy { event[$0] == original[$0] } } &&
        authorities.allSatisfy { $0 == authorities[0] } && authorities[0][2] == UInt64(original["id"]!.intValue!) &&
        Set(family.compactMap { $0["source_capture_id"]?.intValue }).count == 3,
        "test058_same_epoch_two_updates_preserve_original_sample_and_all_frozen_boundaries")
    require(latest["direction"]?.intValue == (fresh ? 1 : 3) && latest["x"]?.intValue == (fresh ? 207 : 290) &&
        latest["y"]?.intValue == (fresh ? 49 : 838), "test058_FRESH_then_SAME_keeps_latest_action_and_coordinates")
    let sourceIDs = Set(family.compactMap { $0["source_capture_id"]?.intValue })
    let originalEvidence = retentionExit == nil ? nil : runtime.testOriginalFrameEvidence(id, captureIDs: sourceIDs.sorted().map { UInt64($0) })
    if retentionExit != nil {
        require(originalEvidence?.count == 3, "test058_original_comparison_PNG_bytes_hash_metadata_saved_before_pressure")
        test058DeferredReportsPublic(id, sourceIDs: sourceIDs, cancelWhileHeld: retentionExit == "cancel")
    }
    func release(_ command: UInt64) {
        NG2Fake.releaseTicket(command)
        pump("test058_chain_callback_actually_returned") { stateLock.lock(); defer { stateLock.unlock() }; return returned.contains(command) }
    }
    if staleFirst {
        for command in oldIDs { release(command) }
        require(runtime.hasLease && report(id)["current_command_id"]?.intValue == Int(latestID) && NG2Fake.paths().count == 2,
            "test058_two_old_returns_keep_latest_family_lease_and_ticket")
    }
    let now = NG2Fake.virtualClock(), notBefore = UInt64(latest["not_before_ns"]!.intValue!)
    NG2Fake.lock.lock(); let pending = NG2Fake.pending; NG2Fake.lock.unlock()
    require(pending == 0, "test058_chain_clock_changes_between_completed_captures")
    if now < notBefore { NG2Fake.advance(notBefore-now) }
    if retentionExit == "expired" {
        NG2RuntimeTestHooks.beforeMainAuthority = {
            let deadline = UInt64(latest["deadline_ns"]!.intValue!), at = NG2Fake.virtualClock()
            if at <= deadline { NG2Fake.advance(deadline-at+1) }
            NG2RuntimeTestHooks.beforeMainAuthority = nil
        }
    }
    release(latestID)
    let acknowledged = report(id)
    let sent = retentionExit != "cancel" && retentionExit != "expired"
    require(acknowledged["inputs"]?.intValue == (sent ? 3 : 2) && acknowledged["moves"]?.intValue == 2 &&
        NG2Fake.paths().count == (sent ? 3 : 2) && runtime.testPreparedAuthority(id, commandID: latestID) == nil,
        "test058_latest_ticket_ACK_or_revocation_ends_shared_authority")
    if retentionExit == "expired" {
        require(acknowledged["dispatch_failure"]?.objectValue?["code"]?.stringValue == "too_late",
            "test058_expired_original_ticket_is_rejected_before_natural_cleanup")
    }
    if sent {
        require(NG2Fake.paths().last?.first?.first?.point == CGPoint(x: fresh ? 207 : 290, y: fresh ? 49 : 838),
            "test058_latest_ticket_sends_latest_direction_and_coordinates")
    }
    if fresh {
        let reference = (acknowledged["motion_references"]?.arrayValue ?? []).compactMap { $0.objectValue }.last
        require(reference?["reference_eligible"]?.boolValue == false && reference?["fallback_attempted"]?.boolValue == false &&
            reference?["authority_capture_id"] == latest["source_capture_id"],
            "test058_FRESH_then_SAME_never_revives_old_motion_reference")
    }
    if retentionExit == "terminal" || retentionExit == "expired" {
        NG2Fake.lock.lock()
        NG2Fake.walkGoodsEnabled = retentionExit == "terminal"; NG2Fake.captureLimit = nil
        NG2Fake.lock.unlock()
        pump("test058_delayed_diagnostics_natural_goods_terminal_flush") {
            let terminal = report(id)
            return terminal["terminal"]?.intValue == 1 && terminal["paused"]?.intValue == 1 &&
                terminal["cancel_requested"]?.boolValue == false &&
                terminal["goods"]?.intValue == (retentionExit == "terminal" ? 1 : 0)
        }
    } else { _ = call("necro_native_cancel", id) }
    if !staleFirst {
        require(runtime.hasLease && !drained(id), "test058_new_return_waits_for_both_retired_callbacks")
        for command in oldIDs { release(command) }
    }
    NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    pump("test058_two_reissues_all_callbacks_and_capture_drained") { drained(id) }
    require(NG2Fake.paths().count == (sent ? 3 : 2), "test058_all_three_callback_returns_preserve_exact_synth_count")
    if retentionExit != nil {
        let result = call("necro_native_results", id)
        let exported = Set((result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
        let terminal = result.0?["report"]?.objectValue ?? [:]
        require(result.1 == nil && sourceIDs.isSubset(of: exported) && terminal["workers_drained"]?.boolValue == true &&
            terminal["events"] == report(id)["events"] && terminal["scene_change_details"] == report(id)["scene_change_details"],
            "test058_deferred_JSON_"+retentionExit!+"_flush_and_export_preserve_all_original_comparisons")
        for captureID in sourceIDs {
            let row = (result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["capture_id"]?.intValue == captureID }
            guard let row, let encoded = row["data_base64"]?.stringValue, let png = Data(base64Encoded: encoded),
                  let original = originalEvidence?[UInt64(captureID)] else {
                require(false, "test058_original_comparison_export_has_decodable_PNG_and_original_evidence"); return
            }
            require(png == original.0 && original.1.allSatisfy { row[$0.key] == $0.value },
                "test058_deferred_JSON_export_preserves_original_PNG_bytes_SHA_and_capture_metadata")
        }
    }
    fixtureFailureSnapshot = nil
}

func test058EveryPreparationIdentityField() {
    let expected: Set<String> = ["same_identity_shared_new_id", "reject_run", "reject_clock",
        "reject_owner", "reject_generation", "reject_pid", "reject_prefix", "reject_epoch",
        "reject_ordinal", "reject_target", "reject_not_before", "reject_deadline",
        "reject_ACK_epoch_zero", "reject_changed_C_epoch", "epoch_zero_fresh_single_id",
        "epoch_zero_reject_other_id"]
    let results = runtime.testPreparationIdentityCoverage()
    require(Set(results.keys) == expected, "test058_preparation_identity_coverage_exact_matrix")
    for name in expected.sorted() {
        require(results[name] == true, "test058_production_preparation_identity_"+name)
    }
    print("PASS TEST058 production preparation identity 11-key matrix and epoch/ID exclusions")
}
// Called by the main TEST058 wrapper.
#endif

test058PreparedContinuousDeadlinePublic()
print("PASS TEST058 prepared continuous deadline public baseline")
