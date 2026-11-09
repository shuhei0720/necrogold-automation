import Foundation
import CoreGraphics

// TEST061 focused public Runtime fixtures. Pixels and the finite shop world
// are synthetic. No missing TEST060 image is supplied or relabelled MOVED.
private func recovery061(_ run: String) -> [String: JSONValue] {
    report(run)["recovery"]?.objectValue ?? [:]
}
private func events061(_ run: String) -> [[String: JSONValue]] {
    (report(run)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
private func records061(_ run: String) -> [[String: JSONValue]] {
    (recovery061(run)["records"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
private func ns061(_ value: [String: JSONValue], _ key: String) -> UInt64 {
    UInt64(max(0, value[key]?.intValue ?? 0))
}
private func captureBoundary061(_ action: @escaping () -> Void) {
    require(NG2Fake.changeClockAtCaptureBoundary(action), "test061_exact_capture_boundary_available")
}
private func setClock061(_ at: UInt64) {
    captureBoundary061 {
        let now = NG2Fake.virtualClock()
        require(now <= at, "test061_clock_never_rewinds")
        NG2Fake.advance(at-now)
    }
}
private func admission061(_ run: String) {
    // A scripted image follows the preceding actual public C assessment.
    // Explicit main/commit clock changes must still reach the parked worker
    // while controlQueue waits; no fixture lock is held while waiting here.
    let previous = NG2Fake.countRequests(), limit = Date().addingTimeInterval(3)
    while previous > 0 && Date() < limit {
        NG2Fake.lock.lock(); let explicit = NG2Fake.boundaryClockChange != nil; NG2Fake.lock.unlock()
        if explicit { break }
        let value = report(run)
        if value["cancel_requested"]?.boolValue == true || value["workers_drained"]?.boolValue == true { break }
        if let capture = value["captures"]?.arrayValue?.last?.objectValue,
            (capture["id"]?.intValue ?? 0) >= previous {
            let eligible = capture["stable"]?.boolValue == true && capture["completed_prefix_end"] == value["last_completed_id"]
            if !eligible || (value["last_capture_id"]?.intValue ?? 0) >= previous { break }
        }
        Thread.sleep(forTimeInterval: 0.001)
    }
    test060_revalidationCaptureBoundary()
}
private func start061(_ run: String) {
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = { admission061(run) }
    alignInitialFixtureMove(run)
    diagnoseFixture(run)
}
private func permit061(_ count: Int? = nil) {
    NG2Fake.lock.lock(); NG2Fake.captureLimit = count; NG2Fake.lock.unlock()
}
private func finish061(_ run: String, cancel: Bool = true) -> [String: JSONValue] {
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeObserveTestHooks.afterObserve = nil
    NG2RuntimeTestHooks.analysisRGBA = nil
    NG2RuntimeTestHooks.beforeControlTick = nil
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    if cancel { _ = call("necro_native_cancel", run) }
    NG2Fake.lock.lock()
    NG2Fake.captureLimit = nil
    let held = Array(NG2Fake.heldTickets.keys)
    NG2Fake.lock.unlock()
    for id in held { NG2Fake.releaseTicket(id) }
    NG2Fake.release()
    pump("test061_actual_workers_and_callbacks_drain", timeout: 15) {
        _ = call("necro_native_status", run, keepalive: true)
        return drained(run)
    }
    require(!runtime.hasLease, "test061_lease_released_only_after_actual_drain")
    let result = call("necro_native_results", run)
    require(result.1 == nil, "test061_public_results_after_drain")
    require(result.0?["api_version"]?.stringValue == "1.98.15-ngg2",
        "test061_actual_results_envelope_requires_API15")
    let manifest = runtime.handle(method: "necro_native_results", params: [
        "run_id": .string(run), "_necro_owner": .string("fixture-owner"), "mode": .string("manifest")])
    require(manifest.1 == nil && manifest.0?["report"]?.objectValue?["recovery"] == result.0?["report"]?.objectValue?["recovery"],
        "test061_manifest_and_results_preserve_same_recovery")
    require(manifest.0?["api_version"]?.stringValue == "1.98.15-ngg2",
        "test061_actual_manifest_envelope_requires_API15")
    fixtureFailureSnapshot = nil
    return result.0?["report"]?.objectValue ?? [:]
}
private func rendered061(playerX: Int32 = 0, playerY: Int32 = 0, phaseOffset: Double = 0, goods: Int32 = 0) -> Data {
    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
    let now = NG2Fake.virtualClock(), period: UInt64 = 520_000_000
    let elapsed = now >= epoch ? now-epoch : 0
    let fraction = (Double(period-1-(elapsed % period))/Double(period)+phaseOffset).truncatingRemainder(dividingBy: 1)
    var rgba = Data(count: 896*414*4)
    let size = rgba.count
    require(rgba.withUnsafeMutableBytes {
        ng2_fixture_floor_rgba($0.bindMemory(to: UInt8.self).baseAddress, size, playerX, playerY, fraction, goods)
    } == 1, "test061_procedural_pixel_renderer")
    return rgba
}
private func pausedFinish061(_ run: String) -> [String: JSONValue] {
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeObserveTestHooks.afterObserve = nil
    NG2RuntimeTestHooks.beforeControlTick = nil
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    NG2RuntimeTestHooks.beforeMainAdmission = nil
    let inputs = report(run)["inputs"]?.intValue ?? 0, paths = NG2Fake.paths().count
    if report(run)["reason"]?.intValue == 0 {
        // Only exercise the real GOODS latch and PAUSE lifecycle after the
        // recovery proof. This synthetic display is no shop-route oracle.
        NG2RuntimeTestHooks.analysisRGBA = { bytes in
            if report(run)["goods"]?.intValue == 1 { return bytes }
            NG2Fake.lock.lock(); let x = NG2Fake.walkX, y = NG2Fake.walkY; NG2Fake.lock.unlock()
            return rendered061(playerX: x, playerY: y, goods: 1)
        }
    } else { NG2RuntimeTestHooks.analysisRGBA = nil }
    permit061()
    pump("test061_natural_stop_latches_before_releasing_unsent_callbacks", timeout: 10) {
        _ = call("necro_native_status", run, keepalive: true)
        return report(run)["goods"]?.intValue == 1 || (report(run)["reason"]?.intValue ?? 0) != 0
    }
    NG2Fake.lock.lock(); let held = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
    for id in held { NG2Fake.releaseTicket(id) }
    pump("test061_actual_final_PAUSE_terminal_and_drained", timeout: 15) {
        _ = call("necro_native_status", run, keepalive: true)
        let value = report(run)
        return value["terminal"]?.intValue == 1 && value["paused"]?.intValue == 1 && drained(run)
    }
    require(report(run)["inputs"]?.intValue == inputs && NG2Fake.paths().count == paths,
        "test061_GOODS_or_stop_never_sends_another_direction")
    return finish061(run, cancel: false)
}
private func assertRecoverySchema061(_ value: [String: JSONValue]) {
    require(Set(value.keys) == Set(["initial_reacquisitions", "post_move_reacquisitions", "episode_id", "mode",
        "schedule_deadline_ns", "visual_deadline_ns", "ack_ns", "record_count", "dropped_records", "records"]),
        "test061_recovery_closed_top_schema")
    let records = (value["records"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let total = value["record_count"]?.intValue ?? -1
    require(records.count == min(total, 2) && value["dropped_records"]?.intValue == total-records.count,
        "test061_recovery_first_latest_counts")
    for (index, record) in records.enumerated() {
        require(Set(record.keys) == Set(["sequence", "episode_id", "reason", "clock", "at_ns", "capture_id", "command_id",
            "abandoned_target_ns", "sync_deadline_ns", "model", "samples"]), "test061_recovery_closed_record_schema")
        require(record["sequence"]?.intValue == (index == 0 ? 1 : total), "test061_recovery_first_latest_sequences")
        let model = record["model"]?.objectValue ?? [:]
        require(Set(model.keys) == Set(["period_ns", "epoch_ns", "first_ns", "last_ns", "gap_ns", "prediction_span_ns",
            "sample_count", "mode", "candidate_count", "residual", "maximum", "alternate", "alias_gap",
            "half_width_max_ns", "tracking_error", "extrapolation_budget"]), "test061_recovery_all_named_model_fields")
        let samples = record["samples"]?.arrayValue ?? []
        require(samples.count <= 13, "test061_recovery_raw_sample_limit")
        for sample in samples {
            require(Set((sample.objectValue ?? [:]).keys) == Set(["start_ns", "end_ns", "midpoint_ns", "half_width_ns", "q", "spacing", "center"]),
                "test061_recovery_all_seven_sample_fields")
        }
    }
}

private func test061AcceptedRecovery() {
    NG2Fake.reset(.hold)
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    let run = identity()
    let accepted = call("necro_native_start", run)
    require(accepted.1 == nil, "test061_public_accepted_start")
    require(accepted.0?["api_version"]?.stringValue == "1.98.15-ngg2",
        "test061_actual_start_envelope_requires_API15")
    let empty = accepted.0?["report"]?.objectValue?["recovery"]?.objectValue ?? [:]
    assertRecoverySchema061(empty)
    require(empty["mode"]?.intValue == 0 && empty["record_count"]?.intValue == 0 && empty["records"]?.arrayValue?.isEmpty == true,
        "test061_accepted_response_zero_recovery")
    pump("test061_accepted_capture_outstanding") { NG2Fake.countRequests() == 1 }
    require(call("necro_native_status", run).0?["api_version"]?.stringValue == "1.98.15-ngg2",
        "test061_actual_status_envelope_requires_API15")
    require(runtime.hasLease, "test061_pending_capture_owns_lease")
    _ = finish061(run)
}

// The first callback is actually prepared and queued by Runtime. Its final
// TicketGuard rejects D+1ns before C begin; complete(outcome0) retires it.
private func test061UnsentRetirementPublic(syncLimit: Bool, rejectCapturePhase: Bool = false) {
    NG2Fake.reset(.walk)
    NG2Fake.lock.lock(); NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
    let run = identity(); start061(run)
    let state = NSLock()
    var ids: [UInt64] = [], callbacks: [UInt64: () -> Void] = [:]
    var returned = [UInt64: Int]()
    var staleAuthorityEntries = 0
    NG2RuntimeTestHooks.afterTicketReturned = { id in state.lock(); returned[id, default: 0] += 1; state.unlock() }
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        guard let event = events061(run).first(where: { $0["id"]?.intValue == Int(id) }), event["kind"]?.intValue == 4 else { return false }
        state.lock(); ids.append(id); callbacks[id] = callback; state.unlock()
        permit061(NG2Fake.countRequests())
        NG2Fake.holdTicket(id, callback)
        return true
    }
    require(call("necro_native_start", run).1 == nil, "test061_unsent_public_start")
    pump("test061_initial_real_ticket_held", timeout: 15) { state.lock(); defer { state.unlock() }; return !ids.isEmpty }
    state.lock(); let old = ids[0], oldCallback = callbacks[ids[0]]!; state.unlock()
    let original = events061(run).first { $0["id"]?.intValue == Int(old) }!
    if rejectCapturePhase {
        NG2RuntimeTestHooks.analysisRGBA = { _ in rendered061(phaseOffset: 0.25) }
        permit061(NG2Fake.countRequests()+1)
        pump("test061_actual_capture_HUD_rejection_retires_initial_ticket", timeout: 10) {
            recovery061(run)["initial_reacquisitions"]?.intValue == 1
        }
        NG2RuntimeTestHooks.analysisRGBA = nil
    } else {
        NG2RuntimeTestHooks.beforeMainAuthority = {
            setClock061(ns061(original, "deadline_ns")+1)
            NG2RuntimeTestHooks.beforeMainAuthority = nil
        }
    }
    NG2Fake.releaseTicket(old)
    pump("test061_expired_callback_actually_returns") { state.lock(); defer { state.unlock() }; return returned[old] == 1 }
    let retired = report(run), recovery = recovery061(run)
    require(retired["inputs"]?.intValue == 0 && retired["reason"]?.intValue == 0 &&
        recovery["initial_reacquisitions"]?.intValue == 1 && recovery["mode"]?.intValue == 1,
        "test061_unsent_deadline_complete0_reacquires")
    let record = records061(run).last ?? [:]
    require(record["reason"]?.intValue == (rejectCapturePhase ? 1 : 5) && record["clock"]?.intValue == (rejectCapturePhase ? 1 : 2) &&
        record["command_id"]?.intValue == Int(old) && record["abandoned_target_ns"] == original["target_ns"],
        "test061_unsent_retirement_records_actual_tick_and_frozen_old_ticket")
    require(events061(run).first(where: { $0["id"]?.intValue == Int(old) })?["outcome"]?.intValue == 3 &&
        NG2Fake.paths().isEmpty, "test061_unsent_retirement_preserves_not_sent_event")
    assertRecoverySchema061(recovery)
    require((record["samples"]?.arrayValue?.count ?? 0) >= 7 &&
        (record["model"]?.objectValue?["period_ns"]?.intValue ?? 0) > 0,
        "test061_actual_recovery_producer_retains_preclear_model_and_samples")
    let frozen = recovery["records"]
    NG2RuntimeTestHooks.beforeMainAuthority = { state.lock(); staleAuthorityEntries += 1; state.unlock() }
    oldCallback()
    pump("test061_old_callback_after_retire_returns") { state.lock(); defer { state.unlock() }; return returned[old] == 2 }
    state.lock(); let staleEntries = staleAuthorityEntries; state.unlock()
    require(staleEntries == 0, "test061_stale_callback_skips_authority")
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    require(recovery061(run)["records"] == frozen && report(run)["inputs"]?.intValue == 0,
        "test061_retired_old_callback_cannot_mutate_new_state")
    let watchdog = syncLimit ? TestOwnerWatchdogFence(run) : nil
    if syncLimit {
        _ = call("necro_native_status", run, keepalive: true)
        watchdog?.park()
    }
    if syncLimit {
        NG2RuntimeTestHooks.beforeMainAdmission = {
            let command = report(run)["current_command_id"]?.intValue ?? 0
            guard command != 0 && command != Int(old) else { return }
            // Sample the new authority only after the original sync budget
            // expires, so authority staleness cannot hide the C complete0 path.
            setClock061(ns061(record, "sync_deadline_ns"))
            NG2RuntimeTestHooks.beforeMainAdmission = nil
        }
    }
    permit061()
    pump("test061_new_HUD_refit_selects_different_ticket", timeout: 15) {
        _ = call("necro_native_status", run, keepalive: true)
        state.lock(); defer { state.unlock() }; return ids.count >= 2
    }
    state.lock(); let fresh = ids[1]; state.unlock()
    let replacement = events061(run).first { $0["id"]?.intValue == Int(fresh) }!
    require(fresh != old && ns061(replacement, "source_capture_id") > ns061(original, "source_capture_id") &&
        ns061(replacement, "target_ns") > ns061(original, "target_ns"), "test061_reacquisition_uses_new_HUD_and_new_ticket")
    let beforeStale = report(run)
    oldCallback()
    // A queue barrier is provided by the actual new callback, below. The old
    // closure has no authority to invalidate its prepared ID or lease.
    NG2RuntimeTestHooks.beforeMainAuthority = {
        if !syncLimit { admitFirstFixtureMove(run, expectedID: fresh) }
        else { NG2RuntimeTestHooks.beforeMainAuthority = nil }
    }
    NG2Fake.releaseTicket(fresh)
    pump("test061_new_callback_after_old_callback_returns") { state.lock(); defer { state.unlock() }; return returned[fresh] == 1 }
    if syncLimit {
        require(report(run)["inputs"]?.intValue == 0 && report(run)["reason"]?.intValue == 8 &&
            recovery061(run)["initial_reacquisitions"]?.intValue == 1,
            "test061_late_callback_sync12_equal_cannot_reacquire")
    } else {
        require(report(run)["inputs"]?.intValue == 1 && NG2Fake.paths().count == 1 &&
            beforeStale["current_command_id"]?.intValue == Int(fresh), "test061_old_callback_does_not_close_new_ticket_or_lease")
        let acknowledged = report(run)
        oldCallback()
        permit061()
        pump("test061_stale_callback_after_new_ACK_no_resend") {
            let value = report(run)
            return value["input_state"]?.intValue != 3 || (value["captures"]?.arrayValue?.count ?? 0) > (acknowledged["captures"]?.arrayValue?.count ?? 0)
        }
        require(report(run)["inputs"]?.intValue == 1 && NG2Fake.paths().count == 1,
            "test061_old_callback_after_new_ACK_never_resends")
    }
    watchdog?.finish()
    let finished = pausedFinish061(run)
    require(finished["recovery"]?.objectValue?["records"]?.arrayValue?.first == frozen?.arrayValue?.first,
        "test061_preclear_recovery_survives_refit_final_PAUSE_and_export")
    print("REPORT test061_recovery_unsent " + String(data: try! JSONEncoder().encode(finished), encoding: .utf8)!)
}

// One eligible35px observation remains UNKNOWN. The next36px image arrives
// after scheduleD and keeps the original before/ACK/attempt history.
private func test061LateVisualPublic(rejectPhase: Bool) {
    NG2Fake.reset(.walk)
    NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 1; NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
    let run = identity(); start061(run)
    let state = NSLock()
    var original: [String: JSONValue] = [:], unknown: [String: JSONValue] = [:]
    var assessed = false, moved = false, newID: UInt64 = 0
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        guard let event = events061(run).first(where: { $0["id"]?.intValue == Int(id) }), event["kind"]?.intValue == 4 else { return false }
        if report(run)["inputs"]?.intValue == 0 {
            state.lock(); original = event; state.unlock()
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(run, expectedID: id) }
            callback(); return true
        }
        state.lock(); newID = id; state.unlock()
        permit061(NG2Fake.countRequests()); NG2Fake.holdTicket(id, callback); return true
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, start, end, prefix, stable in
        let current = report(run), wait = current["motion_wait"]?.objectValue ?? [:]
        state.lock(); let first = original; state.unlock()
        guard stable, prefix == ns061(first, "id"), current["input_state"]?.intValue == 3,
            start >= max(ns061(first, "target_ns")+80_000_000, ns061(recovery061(run), "ack_ns")) else { return }
        state.lock(); let firstProof = !assessed; assessed = true; state.unlock()
        if firstProof {
            require(wait["attempts"]?.intValue == 0 && end < ns061(recovery061(run), "visual_deadline_ns"),
                "test061_first_UNKNOWN_assessment_keeps_original_visual_budget")
            // Retain exactly one35px assessment before rendering the full tile.
            permit061(NG2Fake.countRequests())
        }
    }
    require(call("necro_native_start", run).1 == nil, "test061_late_visual_public_start")
    pump("test061_actual_ACK_then_35px_UNKNOWN", timeout: 15) {
        let value = report(run), wait = value["motion_wait"]?.objectValue ?? [:]
        guard wait["attempts"]?.intValue == 1 else { return false }
        state.lock(); unknown = wait; state.unlock(); return true
    }
    let before = report(run), recovery = recovery061(run)
    require(before["inputs"]?.intValue == 1 && before["moves"]?.intValue == 0 &&
        unknown["last_motion"]?.intValue == 0 && NG2Fake.paths().count == 1,
        "test061_UNKNOWN_keeps_ACK_without_additional_direction")
    NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 0; NG2Fake.lock.unlock()
    if rejectPhase {
        NG2RuntimeTestHooks.analysisRGBA = { _ in rendered061(playerY: -1, phaseOffset: 0.25) }
    }
    let late = ns061(recovery, "schedule_deadline_ns")+1
    require(late+2_000_000 < ns061(recovery, "visual_deadline_ns"), "test061_late_visual_inside_frozen_visual_deadline")
    setClock061(late)
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeTestHooks.beforeControlTick = {
        if report(run)["moves"]?.intValue == 1 {
            state.lock(); moved = true; state.unlock()
            permit061(NG2Fake.countRequests())
            // Continue actual control time while captures are parked. The
            // ordinary50ms status cache must publish the following C tick;
            // a flag set before tick is not evidence that recovery completed.
            NG2Fake.advance(50_000_000)
            NG2RuntimeTestHooks.beforeControlTick = nil
        }
    }
    permit061(NG2Fake.countRequests()+1)
    pump("test061_late_actual_same_before_36px_MOVED", timeout: 10) {
        state.lock(); let proofCommitted = moved; state.unlock()
        return proofCommitted && recovery061(run)["post_move_reacquisitions"]?.intValue == 1
    }
    let proof = report(run), trace = recovery061(run)
    let event = events061(run).first { $0["id"] == original["id"] } ?? [:]
    require(proof["moves"]?.intValue == 1 && proof["inputs"]?.intValue == 1 && event["motion"]?.intValue == 1 &&
        event["source_capture_id"] == original["source_capture_id"] && event["target_ns"] == original["target_ns"] &&
        proof["motion_wait"]?.objectValue?["attempts"]?.intValue == 2,
        "test061_late_MOVED_uses_original_ACK_before_and_attempts")
    require(trace["post_move_reacquisitions"]?.intValue == 1 && NG2Fake.paths().count == 1,
        "test061_late_MOVED_reacquires_before_new_direction")
    require(newID == 0, "test061_proof_observation_never_reissues_old_next_beat")
    assertRecoverySchema061(trace)
    NG2RuntimeTestHooks.analysisRGBA = nil
    permit061()
    pump("test061_live_HUD_selects_future_prepared_new_phase", timeout: 15) {
        _ = call("necro_native_status", run, keepalive: true)
        state.lock(); defer { state.unlock() }; return newID != 0
    }
    let next = events061(run).first { $0["id"]?.intValue == Int(newID) } ?? [:]
    require(ns061(next, "target_ns") > ns061(original, "target_ns") && ns061(next, "source_capture_id") >= ns061(event, "observed_capture_id") &&
        ns061(next, "not_before_ns") >= NG2Fake.virtualClock()+50_000_000,
        "test061_new_phase_uses_adopted_live_HUD_and_50ms_preparation")
    let saved = trace["records"]
    let finished = pausedFinish061(run)
    require(finished["recovery"]?.objectValue?["records"]?.arrayValue?.first == saved?.arrayValue?.first,
        "test061_postmove_producer_survives_new_phase_PAUSE_export")
    print("REPORT test061_recovery_late " + String(data: try! JSONEncoder().encode(finished), encoding: .utf8)!)
}

private func test061ActualCommitPublic(_ branch: String, afterObserve: Bool = false) {
    let shop = branch == "door_opened" || branch == "terrain_opened"
    NG2Fake.reset(shop ? .shop : .walk)
    NG2Fake.lock.lock()
    let epoch = NG2Fake.phaseBase
    let world = shop ? SmallShopWorld(direction: 3, iron: false, detour: branch == "terrain_opened", epoch: epoch) : nil
    NG2Fake.shopWorld = world; NG2Fake.walkGoodsEnabled = false
    NG2Fake.lock.unlock()
    let run = identity(); start061(run)
    let state = NSLock()
    var armed = false, injected = false, assessedID: UInt64 = 0, deadline: UInt64 = 0
    var postObserveTicks = 0
    var beforeInputs = 0, beforeMoves = 0, beforeDoors = 0, beforeTerrain = 0
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        guard let event = events061(run).first(where: { $0["id"]?.intValue == Int(id) }), event["kind"]?.intValue == 4 else { return false }
        NG2RuntimeTestHooks.beforeMainAuthority = {
            admitFirstFixtureMove(run, expectedID: id)
            permit061(NG2Fake.countRequests())
        }
        if branch == "blocked" { NG2RuntimeTestHooks.analysisRGBA = { _ in rendered061() } }
        callback(); return true
    }
    NG2RuntimeTestHooks.afterTicketReturned = { id in
        let current = report(run)
        guard current["input_state"]?.intValue == 3 && events061(run).contains(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return }
        let expected = branch == "blocked" ? "" : branch
        let select = shop ? world?.snapshot().operations.last?.result == expected : current["inputs"]?.intValue == 1
        guard select else { permit061(); return }
        state.lock()
        armed = true; assessedID = id; deadline = ns061(recovery061(run), "visual_deadline_ns")
        beforeInputs = current["inputs"]?.intValue ?? 0; beforeMoves = current["moves"]?.intValue ?? 0
        beforeDoors = current["door_changes"]?.intValue ?? 0; beforeTerrain = current["terrain_changes"]?.intValue ?? 0
        state.unlock()
        permit061(NG2Fake.countRequests())
        // Actual capture ends D-1ms; painting/perception CPU consumes no fake time.
        setClock061(deadline-3_000_000)
        permit061(NG2Fake.countRequests()+1)
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { _, start, end, prefix, stable in
        state.lock(); let selected = armed && !injected && stable && prefix == assessedID && end+1_000_000 == deadline
        if selected { injected = true }
        state.unlock()
        guard selected else { return }
        require(start <= end && end < deadline, "test061_actual_capture_ends_before_visual_deadline_"+branch)
        if afterObserve {
            NG2RuntimeObserveTestHooks.afterObserve = { NG2Fake.advance(deadline+1-NG2Fake.virtualClock()); NG2RuntimeObserveTestHooks.afterObserve = nil }
            NG2RuntimeTestHooks.beforeControlTick = {
                state.lock(); postObserveTicks += 1; let ticks = postObserveTicks; state.unlock()
                if ticks == 2 {
                    // The first C tick runs exactly atD+1ns. Progress time
                    // only after it so its finished state reaches the normal
                    // public cache even while capture admission is parked.
                    NG2Fake.advance(50_000_000)
                    NG2RuntimeTestHooks.beforeControlTick = nil
                }
            }
        } else {
            NG2Fake.advance(deadline+1_000_000-NG2Fake.virtualClock())
        }
    }
    require(call("necro_native_start", run).1 == nil, "test061_actual_commit_public_start_"+branch)
    pump("test061_actual_commit_selected_branch_"+branch, timeout: 25) {
        _ = call("necro_native_status", run, keepalive: true)
        state.lock(); let didInject = injected; state.unlock()
        return didInject && (report(run)["reason"]?.intValue ?? 0) != 0
    }
    let current = report(run)
    state.lock(); let inputs = beforeInputs, moves = beforeMoves, doors = beforeDoors, terrain = beforeTerrain, command = assessedID; state.unlock()
    require(current["reason"]?.intValue == 9, "test061_visual_deadline_stops_with_LATE_"+branch)
    require(current["inputs"]?.intValue == inputs && NG2Fake.paths().count == inputs,
        "test061_actual_commit_and_tick_deadlines_block_next_direction_"+branch)
    if !afterObserve {
        require(current["moves"]?.intValue == moves && current["door_changes"]?.intValue == doors && current["terrain_changes"]?.intValue == terrain,
            "test061_actual_commit_after_visual_deadline_rejects_all_motion_credit_"+branch)
    } else {
        let event = events061(run).first { $0["id"]?.intValue == Int(command) } ?? [:]
        let kind = branch == "moved" ? 1 : branch == "door_opened" ? 3 : branch == "terrain_opened" ? 4 : 2
        require(event["motion"]?.intValue == kind && ns061(event, "observed_capture_id") > 0 &&
            current["moves"]?.intValue == moves+(branch == "moved" ? 1 : 0) &&
            current["door_changes"]?.intValue == doors+(branch == "door_opened" ? 1 : 0) &&
            current["terrain_changes"]?.intValue == terrain+(branch == "terrain_opened" ? 1 : 0),
            "test061_after_C_tick_proves_selected_real_motion_branch_"+branch)
        let expiry = records061(run).last ?? [:]
        require(expiry["clock"]?.intValue == 2 && ns061(expiry, "at_ns") == deadline+1,
            "test061_first_actual_tick_stops_exactly_at_visual_D_plus_one_"+branch)
        if branch == "blocked" {
            require(current["lead_ns"]?.intValue == 75_000_000,
                "test061_after_C_tick_proves_BLOCKED_retune_before_stopping")
        }
    }
    let finished = pausedFinish061(run)
    require(finished["paused"]?.intValue == 1, "test061_late_visual_uses_fresh_cleanup_PAUSE_"+branch)
}

func test061RecoveryPublic() {
    test061AcceptedRecovery()
    test061UnsentRetirementPublic(syncLimit: false)
    test061UnsentRetirementPublic(syncLimit: true)
    test061UnsentRetirementPublic(syncLimit: false, rejectCapturePhase: true)
    test061LateVisualPublic(rejectPhase: false)
    test061LateVisualPublic(rejectPhase: true)
    for branch in ["moved", "door_opened", "terrain_opened", "blocked"] {
        test061ActualCommitPublic(branch)
        test061ActualCommitPublic(branch, afterObserve: true)
    }
}

test061RecoveryPublic()
print("PASS production Runtime public API/TEST061 recovery and actual commit fixtures")
