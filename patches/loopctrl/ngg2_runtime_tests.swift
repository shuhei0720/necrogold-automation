import Foundation

func require(_ condition: Bool, _ name: String) {
    if !condition { print("FAIL \(name)"); exit(1) }
}
let runtime = NG2Runtime.shared
var sequence = 0
func identity() -> String { sequence += 1; return String(format: "%032x", sequence) }
func call(_ method: String, _ id: String, keepalive: Bool? = nil, owner: String = "fixture-owner") -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "_necro_owner": .string(owner)]
    if method == "necro_native_start" { params["profile"] = .string("normal-1-1-v1") }
    if let keepalive { params["keepalive"] = .bool(keepalive) }
    return runtime.handle(method: method, params: params)
}
func report(_ id: String) -> [String: JSONValue] { call("necro_native_status", id).0?["report"]?.objectValue ?? [:] }
func pump(_ name: String, timeout: Double = 5, _ condition: () -> Bool) {
    let end = Date().addingTimeInterval(timeout)
    while !condition() && Date() < end { RunLoop.current.run(until: Date().addingTimeInterval(0.005)) }
    require(condition(), name)
}
func drained(_ id: String) -> Bool { report(id)["workers_drained"]?.boolValue == true }
func cancelDrain(_ id: String) {
    _ = call("necro_native_cancel", id); NG2Fake.release()
    pump("run_drained") { drained(id) }
}

// The cancellation is deliberately placed after the capture loop's outer
// condition and before its admission lock. This catches deletion at the actual
// production capture call site, not merely a helper's standalone behavior.
NG2Fake.reset(.empty)
let captureRace = identity()
NG2RuntimeTestHooks.beforeCaptureAdmission = {
    _ = call("necro_native_cancel", captureRace)
    NG2RuntimeTestHooks.beforeCaptureAdmission = nil
}
require(call("necro_native_start", captureRace).1 == nil, "capture_race_start")
pump("capture_cancel_drained") { drained(captureRace) }
require(NG2Fake.countRequests() == 0 && NG2Fake.countTouches() == 0, "cancel_between_loop_and_admission_no_capture")

NG2Fake.reset(.pause)
let ticketRace = identity()
NG2RuntimeTestHooks.beforeMainAdmission = {
    _ = call("necro_native_cancel", ticketRace)
    NG2RuntimeTestHooks.beforeMainAdmission = nil
}
require(call("necro_native_start", ticketRace).1 == nil, "ticket_race_start")
pump("main_cancel_drained") { drained(ticketRace) }
require(NG2Fake.countRequests() > 0 && NG2Fake.countTouches() == 0, "production_capture_C_ticket_main_cancel_no_synth")

// Time can advance after main was entered while its final admission lock is
// pending. The authorization must sample the clock at begin, not before it.
NG2Fake.reset(.pause)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let staleMainClock = identity()
var advancedAtAdmission = false
NG2RuntimeTestHooks.beforeMainAdmission = {
    let events = report(staleMainClock)["events"]?.arrayValue ?? []
    let deadline = events.last?.objectValue?["deadline_ns"]?.intValue ?? 0
    let current = NG2Fake.virtualClock()
    require(deadline > 0 && UInt64(deadline) >= current, "main_clock_fixture_ticket_still_valid")
    NG2Fake.advance(UInt64(deadline)-current+1)
    advancedAtAdmission = true
    NG2RuntimeTestHooks.beforeMainAdmission = nil
}
require(call("necro_native_start", staleMainClock).1 == nil, "main_clock_start")
pump("main_clock_admission_completed") {
    advancedAtAdmission && report(staleMainClock)["main_ticket_outstanding"]?.boolValue == false
}
require(NG2Fake.countTouches() == 0, "expired_during_main_admission_no_synth")
cancelDrain(staleMainClock)

// An image decoded and analyzed before cancellation is still untrusted when
// its result is committed afterwards. Such results must not reach C or export.
for revoked in ["cancel", "owner"] {
    NG2Fake.reset(.pause)
    let analysisRace = identity()
    NG2RuntimeTestHooks.beforeAnalysisCommit = {
        if revoked == "cancel" { _ = call("necro_native_cancel", analysisRace) }
        // Pause is visible before its off-lock notification is delivered.
        else { RemoteSession.shared.paused = true }
        NG2RuntimeTestHooks.beforeAnalysisCommit = nil
    }
    require(call("necro_native_start", analysisRace).1 == nil, "analysis_race_start_"+revoked)
    pump("analysis_race_drained_"+revoked) { drained(analysisRace) }
    let snapshot = report(analysisRace)
    require(snapshot["accepted_frames"]?.intValue == 0 && snapshot["analyzed_capture_count"]?.intValue == 0 &&
        snapshot["retained_image_count"]?.intValue == 0, "revoked_analysis_never_observed_or_retained_"+revoked)
    require(NG2Fake.countTouches() == 0, "revoked_analysis_no_input_"+revoked)
}

// The real foreground PID lookup performs synchronous XCTest IPC. Holding it
// must leave the public non-UI status and cancel endpoints responsive.
NG2Fake.reset(.pause)
let heldForeground = identity()
let enteredForeground = DispatchSemaphore(value: 0)
let releaseForeground = DispatchSemaphore(value: 0)
let finishedForegroundProbe = DispatchSemaphore(value: 0)
let foregroundProbeLock = NSLock()
var foregroundProbeResponsive = false
NG2RuntimeTestHooks.beforeMainAdmission = {
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        NG2Fake.lock.lock(); NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
        enteredForeground.signal()
        _ = releaseForeground.wait(timeout: .now()+2)
    }
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.beforeMainAdmission = nil
    DispatchQueue.global().async {
        let entered = enteredForeground.wait(timeout: .now()+2) == .success
        let statusDone = DispatchSemaphore(value: 0)
        let cancelDone = DispatchSemaphore(value: 0)
        DispatchQueue.global().async { _ = call("necro_native_status", heldForeground); statusDone.signal() }
        DispatchQueue.global().async { _ = call("necro_native_cancel", heldForeground); cancelDone.signal() }
        let statusImmediate = statusDone.wait(timeout: .now()+0.25) == .success
        let cancelImmediate = cancelDone.wait(timeout: .now()+0.25) == .success
        foregroundProbeLock.lock()
        foregroundProbeResponsive = entered && statusImmediate && cancelImmediate
        foregroundProbeLock.unlock()
        releaseForeground.signal()
        finishedForegroundProbe.signal()
    }
}
require(call("necro_native_start", heldForeground).1 == nil, "foreground_IPC_hold_start")
pump("foreground_IPC_hold_drained") { drained(heldForeground) }
require(finishedForegroundProbe.wait(timeout: .now()+2) == .success, "foreground_IPC_probe_finished")
foregroundProbeLock.lock(); let foregroundResponsive = foregroundProbeResponsive; foregroundProbeLock.unlock()
require(foregroundResponsive, "foreground_IPC_hold_keeps_status_cancel_nonblocking")
require(NG2Fake.countTouches() == 0, "foreground_IPC_hold_cancel_no_late_synth")

// Both slow foreground IPC itself and delay after its result invalidate the
// sampled authority, even when cancellation and owner flags remain unchanged.
for delayed in ["query", "gate"] {
    NG2Fake.reset(.pause)
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let oldAuthority = identity()
    NG2RuntimeTestHooks.beforeMainAdmission = {
        if delayed == "query" {
            NG2Fake.lock.lock()
            NG2Fake.beforeForegroundQuery = {
                NG2Fake.lock.lock(); NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
                NG2Fake.advance(1_000_000_001)
            }
            NG2Fake.lock.unlock()
        } else {
            NG2RuntimeTestHooks.afterForegroundQuery = {
                NG2Fake.advance(1_000_000_001)
                NG2RuntimeTestHooks.afterForegroundQuery = nil
            }
        }
        NG2RuntimeTestHooks.beforeMainAdmission = nil
    }
    require(call("necro_native_start", oldAuthority).1 == nil, "authority_age_start_"+delayed)
    pump("authority_age_drained_"+delayed) { drained(oldAuthority) }
    require(report(oldAuthority)["reason"]?.intValue == 7 && NG2Fake.countTouches() == 0,
        "authority_sample_over_1s_no_synth_"+delayed)
}

// Fresh main-thread authority checks are made after a ticket has already been
// reserved, and cancel before any synth rather than planning a cleanup input.
for lost in ["foreground", "lock", "owner"] {
    NG2Fake.reset(.pause)
    let authority = identity()
    NG2RuntimeTestHooks.beforeMainAdmission = {
        if lost == "foreground" { NG2Fake.lock.lock(); NG2Fake.frontPID = 0; NG2Fake.lock.unlock() }
        else if lost == "lock" { LockStateMonitor.monitor.isLocked = true }
        else { RemoteSession.shared.paused = true }
        NG2RuntimeTestHooks.beforeMainAdmission = nil
    }
    require(call("necro_native_start", authority).1 == nil, "authority_start_"+lost)
    pump("authority_drained_"+lost) { drained(authority) }
    let reason = lost == "foreground" ? 3 : (lost == "lock" ? 4 : 5)
    require(report(authority)["reason"]?.intValue == reason && NG2Fake.countTouches() == 0,
        "final_authority_loss_no_synth_or_cleanup_"+lost)
}

NG2Fake.reset(.empty)
let queued = identity()
require(call("necro_native_start", queued).1 == nil, "queued_start")
Thread.sleep(forTimeInterval: 0.02)
require(runtime.leaseError("gesture") != nil && runtime.leaseError("device_info") != nil, "legacy_UI_receipt_blocked")
require(runtime.leaseError("necro_native_status") == nil && runtime.leaseError("necro_native_cancel") == nil, "status_cancel_nonUI_lane")
require(call("necro_native_status", queued).1 == nil, "status_answers_while_main_not_pumped")
_ = call("necro_native_cancel", queued)
pump("queued_cancel_drained") { drained(queued) }
require(NG2Fake.countActivations() == 0 && NG2Fake.countRequests() == 0, "queued_bootstrap_cancel_no_late_activation")

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let readOnly = identity()
require(call("necro_native_start", readOnly).1 == nil, "readonly_start")
Thread.sleep(forTimeInterval: 0.02)
NG2Fake.advance(6_000_000_000)
require(call("necro_native_status", readOnly).1 == nil, "readonly_status")
Thread.sleep(forTimeInterval: 0.15)
require(report(readOnly)["cancel_requested"]?.boolValue == true, "status_default_does_not_extend_watchdog")
pump("readonly_drained") { drained(readOnly) }
require(report(readOnly)["reason"]?.intValue == 19 && NG2Fake.countActivations() == 0, "heartbeat_stops_queued_bootstrap")

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let alive = identity()
require(call("necro_native_start", alive).1 == nil, "keepalive_start")
Thread.sleep(forTimeInterval: 0.02)
// Renew before expiry; advancing beyond expiry before sending the renewal
// would race the independent watchdog and legitimately allow cancellation.
NG2Fake.advance(4_000_000_000)
require(call("necro_native_status", alive, keepalive: true).1 == nil, "explicit_keepalive")
NG2Fake.advance(2_000_000_000)
Thread.sleep(forTimeInterval: 0.15)
require(report(alive)["cancel_requested"]?.boolValue == false, "active_explicit_keepalive_renews")
cancelDrain(alive)

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let hardLimit = identity()
require(call("necro_native_start", hardLimit).1 == nil, "session_limit_start")
Thread.sleep(forTimeInterval: 0.02)
NG2Fake.advance(181_000_000_000)
_ = call("necro_native_status", hardLimit, keepalive: true)
Thread.sleep(forTimeInterval: 0.15)
require(report(hardLimit)["cancel_requested"]?.boolValue == true, "hard_session_limit_despite_keepalive")
pump("hard_limit_drained") { drained(hardLimit) }
require(report(hardLimit)["reason"]?.intValue == 15 && NG2Fake.countActivations() == 0, "independent_limit_prevents_late_activation")

NG2Fake.reset(.hold)
let timeout = identity()
require(call("necro_native_start", timeout).1 == nil, "capture_timeout_start")
pump("one_capture_started") { NG2Fake.countRequests() == 1 }
pump("capture_timeout_invalidates_generation", timeout: 4) { report(timeout)["capture_timed_out"]?.boolValue == true }
require(!drained(timeout) && runtime.hasLease, "outstanding_daemon_keeps_lease")
require(call("necro_native_start", identity()).1 != nil, "new_run_refused_before_capture_drain")
require(call("necro_native_start", timeout).1 == nil && NG2Fake.countRequests() == 1, "same_run_idempotent_no_second_worker")
cancelDrain(timeout)

NG2Fake.reset(.empty)
let paused = identity()
NG2RuntimeTestHooks.beforeCaptureAdmission = {
    RemoteSession.shared.paused = true; runtime.ownerChanged()
    NG2RuntimeTestHooks.beforeCaptureAdmission = nil
}
require(call("necro_native_start", paused).1 == nil, "owner_pause_start")
pump("owner_pause_drained") { drained(paused) }
require(NG2Fake.countRequests() == 0 && NG2Fake.countTouches() == 0, "owner_pause_between_capture_loop_and_admission")
require(call("necro_native_results", paused).1 != nil, "paused_owner_cannot_export_images")
RemoteSession.shared.paused = false

NG2Fake.reset(.empty)
require(runtime.beginStreamCapture(), "legacy_stream_admitted_before_run")
let legacy = identity()
require(call("necro_native_start", legacy).1 == nil, "legacy_drain_start")
require(!runtime.beginStreamCapture(), "new_stream_capture_suspended")
RunLoop.current.run(until: Date().addingTimeInterval(0.05))
require(NG2Fake.countRequests() == 0, "native_waits_for_preexisting_capture")
_ = call("necro_native_cancel", legacy)
runtime.endStreamCapture()
pump("legacy_capture_drained") { drained(legacy) }

// A legacy daemon wait can finish before the actual daemon request. Native
// admission must remain blocked by that actual pending callback count.
NG2Fake.reset(.empty)
NG2Fake.lock.lock(); NG2Fake.pending = 1; NG2Fake.lock.unlock()
let legacyTimeout = identity()
require(call("necro_native_start", legacyTimeout).1 != nil, "legacy_timeout_actual_request_blocks_native_run")
NG2Fake.lock.lock(); NG2Fake.pending = 0; NG2Fake.lock.unlock()
require(call("necro_native_start", legacyTimeout).1 == nil, "legacy_actual_reply_allows_new_run")
cancelDrain(legacyTimeout)

// Starting a later run releases old raw buffers, while metadata remains
// recoverable under the old owner/run identity with explicit image omissions.
let recovered = call("necro_native_results", captureRace)
require(recovered.1 == nil && recovered.0?["report"]?.objectValue?["historical_metadata_only"]?.boolValue == true,
    "old_terminal_metadata_recoverable")
require(recovered.0?["images"]?.arrayValue?.isEmpty == true && recovered.0?["retained_images"]?.intValue == 0,
    "old_run_images_explicitly_omitted")
require(call("necro_native_status", captureRace, keepalive: true).1 == nil, "old_status_read_does_not_touch_current_run")
// Run real perception, beat fitting, BFS, timed direction input, translated
// motion observation and goods holding against procedural (non-device) frames.
NG2Fake.reset(.walk)
let walk = identity()
require(call("necro_native_start", walk).1 == nil, "native_walk_start")
pump("native_walk_first_input", timeout: 12) {
    let snapshot = call("necro_native_status", walk, keepalive: true).0?["report"]?.objectValue ?? [:]
    return (snapshot["inputs"]?.intValue ?? 0) >= 1 || snapshot["workers_drained"]?.boolValue == true
}
let paths = NG2Fake.paths()
var validDirectionPath = paths.count == 1
if let fingers = paths.first, fingers.count == 1, let finger = fingers.first, finger.count == 2 {
    validDirectionPath = validDirectionPath && finger[0].point == CGPoint(x: 290, y: 838)
    validDirectionPath = validDirectionPath && finger[1].point == finger[0].point
    validDirectionPath = validDirectionPath && finger[0].t == 0 && finger[1].t == 0.05
} else { validDirectionPath = false }
require(validDirectionPath, "native_walk_uses_single_50ms_direction_gesture")
pump("native_walk_goods_hold_drained", timeout: 8) {
    _ = call("necro_native_status", walk, keepalive: true)
    return drained(walk)
}
let walked = report(walk)
require(walked["moves"]?.intValue == 1 && walked["inputs"]?.intValue == 1 &&
    walked["lead_confirmed"]?.intValue == 1 && walked["goods"]?.intValue == 1 && walked["paused"]?.intValue == 1,
    "native_walk_real_perception_fit_BFS_motion_goods_pause")
require(call("necro_native_status", walk).0?["state"]?.stringValue == "completed", "native_walk_completed")
let taps = NG2Fake.taps()
require(taps.count == 1 && taps.first == CGPoint(x: 390, y: 448) && NG2Fake.countTouches() == 2,
    "native_walk_one_direction_one_holding_pause")
let movementEvents = (walked["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
require(movementEvents.count == 1 && movementEvents.first?["outcome"]?.intValue == 2 &&
    (movementEvents.first?["observed_capture_id"]?.intValue ?? 0) > 0, "native_walk_ACK_has_motion_observation")
require(walked["missing_capture_ids"]?.arrayValue?.isEmpty == true && (walked["pinned_image_count"]?.intValue ?? 0) >= 4,
    "native_walk_event_images_pinned")
let walkResult = call("necro_native_results", walk)
require(walkResult.1 == nil && (walkResult.0?["images"]?.arrayValue?.count ?? 0) >= 4 &&
    walkResult.0?["omitted_capture_ids"]?.arrayValue?.isEmpty == true, "native_walk_initial_motion_goods_stop_images_exported")

// Revoke the original queued first-move ticket using one real remote-cell
// change. Execute its actual callback before/after the replacement callback.
// All perception, same-position proof, new planning and begin calls are real.
for staleFirst in [true, false] {
    NG2Fake.reset(.walk)
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let replan = identity()
    var aligned = false
    NG2RuntimeTestHooks.beforeControlTick = {
        let current = report(replan)
        if !aligned && (current["beat_period_ns"]?.intValue ?? 0) > 0 &&
            !(current["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 }) {
            // Give the real next-target calculation nearly a full period so
            // a second image can arrive before the original 10ms deadline.
            let now = NG2Fake.virtualClock()
            NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
            let period: UInt64 = 520_000_000
            let position = (now-epoch+150_000_000) % period
            NG2Fake.advance((period+5_000_000-position) % period)
            aligned = true
            NG2RuntimeTestHooks.beforeControlTick = nil
        }
    }
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        let current = report(replan)
        let moves = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
        guard moves.contains(where: { $0["id"]?.intValue == Int(id) }),
            (current["inputs"]?.intValue ?? 0) == 0 else { return false }
        NG2Fake.holdTicket(id, callback)
        NG2Fake.lock.lock(); NG2Fake.remoteVariant = 1; NG2Fake.lock.unlock()
        return true
    }
    NG2RuntimeTestHooks.afterTicketReturned = { id in
        NG2Fake.lock.lock(); NG2Fake.returnedTickets.insert(id); NG2Fake.lock.unlock()
    }
    require(call("necro_native_start", replan).1 == nil, "replan_runtime_start")
    pump("replan_runtime_replacement_reserved", timeout: 12) {
        let current = call("necro_native_status", replan, keepalive: true).0?["report"]?.objectValue ?? [:]
        NG2Fake.lock.lock(); let held = NG2Fake.heldTickets.count; NG2Fake.lock.unlock()
        return held >= 2 || current["terminal"]?.intValue == 1
    }
    let prepared = report(replan)
    let changes = prepared["scene_changes"]?.arrayValue ?? []
    require(changes.count == 1 && changes[0].objectValue?["replan_allowed"]?.boolValue == true,
        "replan_runtime_remote_change_uses_new_observation")
    let moves = (prepared["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
    require(moves.count == 2 && moves[0]["outcome"]?.intValue == 3 && moves[0]["begin_ns"]?.intValue == 0,
        "replan_runtime_old_ticket_definitely_unsent")
    let oldID = UInt64(moves[0]["id"]!.intValue!)
    let newID = UInt64(moves[1]["id"]!.intValue!)
    require(moves[0]["target_ns"]?.intValue == moves[1]["target_ns"]?.intValue &&
        moves[0]["not_before_ns"]?.intValue == moves[1]["not_before_ns"]?.intValue &&
        moves[1]["deadline_ns"]!.intValue! <= moves[0]["deadline_ns"]!.intValue!, "replan_runtime_original_beat_and_deadline")
    var oldQueries = 0
    func releaseOld() {
        NG2Fake.lock.lock(); NG2Fake.frontPID = 0
        NG2Fake.beforeForegroundQuery = { oldQueries += 1 }; NG2Fake.lock.unlock()
        NG2Fake.releaseTicket(oldID)
        pump("replan_stale_callback_returned") {
            NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }; return NG2Fake.returnedTickets.contains(oldID)
        }
        require(oldQueries == 0, "replan_stale_callback_skips_AX_and_shared_authority")
        NG2Fake.lock.lock(); NG2Fake.frontPID = 42; NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
    }
    if staleFirst {
        releaseOld()
        let afterOld = report(replan)
        require(afterOld["current_command_id"]?.intValue == Int(newID) &&
            afterOld["input_state"]?.intValue == 1 && afterOld["main_ticket_outstanding"]?.boolValue == true &&
            afterOld["cancel_requested"]?.boolValue == false && NG2Fake.countTouches() == 0,
            "replan_old_return_does_not_release_new_ticket")
    }
    NG2RuntimeTestHooks.beforeMainAuthority = {
        let now = NG2Fake.virtualClock()
        let at = UInt64(moves[1]["not_before_ns"]!.intValue!)
        require(now <= UInt64(moves[1]["deadline_ns"]!.intValue!), "replan_fixture_replacement_not_late")
        if now < at { NG2Fake.advance(at-now) }
        NG2RuntimeTestHooks.beforeMainAuthority = nil
    }
    NG2Fake.releaseTicket(newID)
    pump("replan_replacement_only_one_input", timeout: 8) {
        let current = call("necro_native_status", replan, keepalive: true).0?["report"]?.objectValue ?? [:]
        return (current["inputs"]?.intValue ?? 0) > 0 || current["terminal"]?.intValue == 1
    }
    require(report(replan)["inputs"]?.intValue == 1 && NG2Fake.paths().count == 1,
        "replan_replacement_is_only_direction_synth")
    pump("replan_terminal_hold", timeout: 8) {
        _ = call("necro_native_status", replan, keepalive: true)
        return report(replan)["terminal"]?.intValue == 1
    }
    if !staleFirst {
        require(!drained(replan) && runtime.hasLease && call("necro_native_start", identity()).1 != nil,
            "replan_queued_stale_callback_keeps_core_and_lease")
        releaseOld()
    }
    pump("replan_all_callbacks_drained") { drained(replan) }
    let final = report(replan)
    require(final["paused"]?.intValue == 1 && final["cancel_requested"]?.boolValue == false && NG2Fake.paths().count == 1,
        "replan_stale_callback_never_cancels_or_synthesizes")
    let result = call("necro_native_results", replan)
    let exported = Set((result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    let change = changes[0].objectValue!
    require(result.1 == nil && exported.contains(change["source_capture_id"]!.intValue!) &&
        exported.contains(change["observed_capture_id"]!.intValue!), "replan_difference_source_and_after_images_pinned")
}

NG2Fake.reset(.pause)
NG2Fake.lock.lock(); NG2Fake.failTouch = true; NG2Fake.lock.unlock()
let unknown = identity()
require(call("necro_native_start", unknown).1 == nil, "unknown_start")
pump("unknown_terminal_drained") { drained(unknown) }
require(report(unknown)["input_state"]?.intValue == 4 && NG2Fake.countTouches() == 1, "started_unknown_no_retry_or_cleanup")

require(report(unknown)["ui_frozen"]?.boolValue == true && runtime.hasLease, "unknown_global_UI_freeze_survives_worker_drain")
require(runtime.leaseError("gesture") != nil && runtime.leaseError("screenshot") != nil && runtime.leaseError("device_info") != nil,
    "unknown_blocks_all_later_UI_and_capture")
require(!runtime.beginStreamCapture(), "unknown_blocks_legacy_stream_capture")
require(call("necro_native_start", identity()).1 != nil, "unknown_blocks_same_owner_new_run")
require(call("necro_native_start", identity(), owner: "other-owner").1 != nil, "unknown_blocks_other_owner_new_run")
require(call("necro_native_start", unknown).1 == nil && NG2Fake.countTouches() == 1,
    "unknown_same_run_recovery_idempotent")
for method in ["necro_native_status", "necro_native_cancel", "necro_native_results"] {
    require(runtime.leaseError(method) == nil && call(method, unknown).1 == nil,
        "unknown_keeps_recovery_lane_"+method)
    require(call(method, unknown, owner: "other-owner").1 != nil,
        "unknown_recovery_owner_bound_"+method)
}
require(NG2Fake.countTouches() == 1, "unknown_recovery_never_synthesizes")
print("PASS production Runtime public API/capture/raster/real C/main-input/watchdog/drain integration; UIKit/XCTest/daemon faked")
