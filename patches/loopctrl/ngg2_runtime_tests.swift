import Foundation

var fixtureFailureSnapshot: (() -> [String: JSONValue])?
func require(_ condition: Bool, _ name: String) {
    if !condition {
        if let diagnostic = fixtureFailureSnapshot?(), let bytes = try? JSONEncoder().encode(diagnostic),
            let line = String(data: bytes, encoding: .utf8) { print("DIAGNOSTIC runtime_fixture " + line) }
        print("FAIL \(name)"); exit(1)
    }
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
func diagnoseFixture(_ id: String) {
    fixtureFailureSnapshot = {
        let snapshot = report(id)
        NG2Fake.lock.lock()
        let held = NG2Fake.heldTickets.keys.sorted(), returned = NG2Fake.returnedTickets.sorted()
        let phase = NG2Fake.phaseBase, pending = NG2Fake.pending, variant = NG2Fake.remoteVariant
        let captureDrained = NG2Fake.captureDrainedRuns.contains(id)
        NG2Fake.lock.unlock()
        return ["report": .object(snapshot), "held_ticket_ids": .array(held.map { .int(Int($0)) }),
            "returned_ticket_ids": .array(returned.map { .int(Int($0)) }),
            "fake_now_ns": .int(Int(NG2Fake.virtualClock())), "phase_base_ns": .int(Int(phase)),
            "pending_captures": .int(pending), "remote_variant": .int(Int(variant)),
            "capture_drain_processed": .bool(captureDrained),
            "path_count": .int(NG2Fake.paths().count), "touch_count": .int(NG2Fake.countTouches())]
    }
}
func admitFirstFixtureMove(_ id: String, expectedID: UInt64? = nil) {
    let current = report(id)
    let currentID = current["current_command_id"]?.intValue ?? 0
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard (expectedID == nil || currentID == Int(expectedID!)),
        let command = events.first(where: { $0["id"]?.intValue == currentID && $0["kind"]?.intValue == 4 }) else {
        // A stale callback may return before this hook is reached. Never let
        // its setup clock operation leak into a later holding PAUSE.
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        return
    }
    let at = UInt64(command["not_before_ns"]!.intValue!)
    let deadline = UInt64(command["deadline_ns"]!.intValue!)
    NG2Fake.lock.lock(); NG2Fake.walkObservationAfter = UInt64(command["target_ns"]!.intValue!)+80_000_000; NG2Fake.lock.unlock()
    require(NG2Fake.changeClockAtCaptureBoundary {
        let now = NG2Fake.virtualClock()
        require(now <= deadline, "fixture_current_move_not_late_before_admission")
        if now < at { NG2Fake.advance(at-now) }
    }, "fixture_move_admission_capture_boundary")
    NG2RuntimeTestHooks.beforeMainAuthority = nil
}
func alignInitialFixtureMove(_ id: String) {
    NG2RuntimeTestHooks.beforeControlTick = {
        let current = report(id)
        guard (current["beat_period_ns"]?.intValue ?? 0) > 0 &&
            !(current["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 }) else { return }
        // Move the known world/clock together between complete captures. The
        // real planner then has about420ms until its own next dispatch point,
        // enough for a later capture boundary or a changed-frame observation.
        require(NG2Fake.changeClockAtCaptureBoundary {
            let now = NG2Fake.virtualClock()
            NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
            let period: UInt64 = 520_000_000
            let position = (now-epoch+150_000_000) % period
            NG2Fake.advance((period+100_000_000-position) % period)
        }, "fixture_initial_alignment_capture_boundary")
        NG2RuntimeTestHooks.beforeControlTick = nil
    }
}
func scheduleFirstFixtureMove(_ run: String, holdingPause: Bool = false) {
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        let current = report(run)
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let event = events.first(where: { $0["id"]?.intValue == Int(id) }) else { return false }
        if event["kind"]?.intValue == 4 && current["inputs"]?.intValue == 0 { callback(); return true }
        if holdingPause && event["kind"]?.intValue == 2 { NG2Fake.holdTicket(id, callback); return true }
        return false
    }
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
    require(snapshot["raster_samples"]?.arrayValue?.isEmpty == true && snapshot["raster_samples_dropped"]?.intValue == 0,
        "revoked_analysis_never_commits_raster_trace_"+revoked)
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
diagnoseFixture(walk)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(walk)
NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(walk) }
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let current = report(walk)
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard current["inputs"]?.intValue == 0,
        events.contains(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
    // Test real C begin/main admission without depending on a GCD timer wake
    // landing in a 10ms window while unrelated fixture analysis is queued.
    callback()
    return true
}
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
fixtureFailureSnapshot = nil

// The same procedural world is genuinely UNKNOWN at35px and MOVED at36px.
// Keep the holding PAUSE callback queued while later FLOOR images evict the
// first ambiguous observation from recent4; only cumulative event pins save it.
NG2Fake.reset(.walk)
let subtile = identity()
diagnoseFixture(subtile)
NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 1; NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = {
    NG2Fake.performBoundaryClockChange()
    let current = report(subtile), wait = report(subtile)["motion_wait"]?.objectValue ?? [:]
    if wait["active"]?.boolValue == true && wait["attempts"]?.intValue == 1 {
        require(wait["last_motion"]?.intValue == 0 && current["input_state"]?.intValue == 3 &&
            NG2Fake.paths().count == 1, "subtile_UNKNOWN_ACK_wait_has_no_followup_MOVE")
        NG2Fake.lock.lock()
        if NG2Fake.firstUnknownID == 0 { NG2Fake.firstUnknownID = UInt64(wait["last_capture_id"]!.intValue!) }
        NG2Fake.walkPixelInset = 0
        NG2Fake.lock.unlock()
        NG2RuntimeTestHooks.beforeControlTick = {
            let snapshot = report(subtile), resolved = report(subtile)["motion_wait"]?.objectValue ?? [:]
            guard snapshot["moves"]?.intValue == 1 else { return }
            require(resolved["active"]?.boolValue == false && (resolved["attempts"]?.intValue ?? 0) >= 2 &&
                resolved["last_motion"]?.intValue == 1, "subtile_original_ACK_query_resolves_after_UNKNOWN")
            NG2Fake.lock.lock(); NG2Fake.subtileResolvedWait = true; NG2Fake.lock.unlock()
            NG2RuntimeTestHooks.beforeControlTick = nil
        }
    }
    if current["moves"]?.intValue == 1 {
        NG2Fake.lock.lock(); NG2Fake.walkGoodsEnabled = true; NG2Fake.lock.unlock()
    }
}
alignInitialFixtureMove(subtile)
NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(subtile) }
scheduleFirstFixtureMove(subtile, holdingPause: true)
require(call("necro_native_start", subtile).1 == nil, "subtile_walk_start")
pump("subtile_UNKNOWN_then_MOVED_and_goods_holding_pause", timeout: 12) {
    let current = call("necro_native_status", subtile, keepalive: true).0?["report"]?.objectValue ?? [:]
    NG2Fake.lock.lock(); let held = !NG2Fake.heldTickets.isEmpty, unknownID = Int(NG2Fake.firstUnknownID); NG2Fake.lock.unlock()
    let recent = (current["captures"]?.arrayValue ?? []).suffix(4).compactMap { $0.objectValue?["id"]?.intValue }
    return held && unknownID > 0 && recent.count == 4 && !recent.contains(unknownID) && current["moves"]?.intValue == 1
}
let subtileReport = report(subtile)
NG2Fake.lock.lock()
let subtileUnknownID = Int(NG2Fake.firstUnknownID), subtileTickets = Array(NG2Fake.heldTickets.keys), subtileResolved = NG2Fake.subtileResolvedWait
NG2Fake.lock.unlock()
let subtileMove = (subtileReport["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["kind"]?.intValue == 4 }
require(subtileResolved && subtileMove?["motion"]?.intValue == 1 && subtileReport["inputs"]?.intValue == 1 && NG2Fake.paths().count == 1,
    "subtile_36px_confirms_original_ACK_without_extra_MOVE")
_ = call("necro_native_cancel", subtile)
for id in subtileTickets { NG2Fake.releaseTicket(id) }
pump("subtile_held_callback_drained") { drained(subtile) }
let subtileResult = call("necro_native_results", subtile)
let subtileExports = Set((subtileResult.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
require(subtileResult.1 == nil && subtileExports.contains(subtileUnknownID), "motion_first_UNKNOWN_frame_pinned_beyond_recent_window")
fixtureFailureSnapshot = nil

// Cross the original motion deadline during real analysis, while the image's
// request interval is still before that deadline. The next production tick
// must use its actual clock. A second tick may never repair a missed first one.
NG2Fake.reset(.walk)
let motionLate = identity()
diagnoseFixture(motionLate)
NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 1; NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange(); NG2Fake.waitForCapturePermit() }
alignInitialFixtureMove(motionLate)
NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(motionLate) }
scheduleFirstFixtureMove(motionLate, holdingPause: true)
var crossedMotionDeadline = false
var deadlineTicks = 0
NG2RuntimeTestHooks.beforeAnalysisCommit = {
    let wait = report(motionLate)["motion_wait"]?.objectValue ?? [:]
    guard !crossedMotionDeadline, wait["active"]?.boolValue == true && wait["attempts"]?.intValue == 1 else { return }
    let deadline = UInt64(wait["deadline_ns"]!.intValue!)
    require(NG2Fake.virtualClock() < deadline, "motion_deadline_fixture_analysis_starts_before_original_deadline")
    require(NG2Fake.changeClockAtCaptureBoundary {
        let now = NG2Fake.virtualClock()
        if now <= deadline { NG2Fake.advance(deadline+1-now) }
        NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
    }, "motion_deadline_fixture_crosses_at_capture_boundary")
    crossedMotionDeadline = true
    NG2RuntimeTestHooks.beforeControlTick = {
        deadlineTicks += 1
        if deadlineTicks > 1 {
            let events = (report(motionLate)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            require(events.contains(where: { $0["kind"]?.intValue == 2 }), "motion_deadline_rechecked_after_analysis_before_next_tick")
        }
    }
}
require(call("necro_native_start", motionLate).1 == nil, "motion_deadline_walk_start")
pump("motion_deadline_fresh_prefix_holding_pause", timeout: 12) {
    _ = call("necro_native_status", motionLate, keepalive: true)
    NG2Fake.lock.lock(); let held = !NG2Fake.heldTickets.isEmpty; NG2Fake.lock.unlock()
    return held
}
let lateReport = report(motionLate), lateWait = report(motionLate)["motion_wait"]?.objectValue ?? [:]
let lateEvents = (lateReport["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
let lateMove = lateEvents.first { $0["kind"]?.intValue == 4 }!
let latePause = lateEvents.first { $0["kind"]?.intValue == 2 }!
let lateSource = (lateReport["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }.first {
    $0["id"]?.intValue == latePause["source_capture_id"]?.intValue
}
require(lateReport["reason"]?.intValue == 9 && lateWait["active"]?.boolValue == false &&
    lateReport["inputs"]?.intValue == 1 && lateReport["moves"]?.intValue == 0 && NG2Fake.paths().count == 1 &&
    latePause["source_capture_id"]?.intValue != lateMove["source_capture_id"]?.intValue &&
    lateSource?["stable"]?.boolValue == true && lateSource?["completed_prefix_end"]?.intValue == lateMove["id"]?.intValue,
    "motion_deadline_rechecked_after_analysis_before_next_tick")
NG2RuntimeTestHooks.beforeAnalysisCommit = nil
NG2RuntimeTestHooks.beforeControlTick = nil
NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; let lateTickets = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
for id in lateTickets { NG2Fake.releaseTicket(id) }
pump("motion_deadline_known_ACK_fresh_cleanup_drained") { drained(motionLate) }
require(report(motionLate)["paused"]?.intValue == 1 && NG2Fake.taps().count == 1 && NG2Fake.paths().count == 1,
    "motion_deadline_cleanup_uses_new_prefix_once_without_followup_MOVE")
fixtureFailureSnapshot = nil

// A fresh matching-prefix goods frame takes priority even while its35px
// camera position has not established displacement for the known synth ACK.
NG2Fake.reset(.walk)
let ambiguousGoods = identity()
diagnoseFixture(ambiguousGoods)
NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 1; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(ambiguousGoods)
NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(ambiguousGoods) }
scheduleFirstFixtureMove(ambiguousGoods)
require(call("necro_native_start", ambiguousGoods).1 == nil, "motion_goods_priority_start")
pump("motion_goods_priority_drained", timeout: 12) {
    _ = call("necro_native_status", ambiguousGoods, keepalive: true)
    return drained(ambiguousGoods)
}
let goodsWait = report(ambiguousGoods)["motion_wait"]?.objectValue ?? [:]
require(report(ambiguousGoods)["goods"]?.intValue == 1 && report(ambiguousGoods)["paused"]?.intValue == 1 &&
    report(ambiguousGoods)["moves"]?.intValue == 0 && goodsWait["active"]?.boolValue == false &&
    goodsWait["attempts"]?.intValue == 1 && goodsWait["last_motion"]?.intValue == 0 &&
    NG2Fake.paths().count == 1 && NG2Fake.taps().count == 1,
    "motion_UNKNOWN_position_goods_priority_holds_without_followup_MOVE")
fixtureFailureSnapshot = nil

// Revoke the original queued first-move ticket using one real remote-cell
// change. Execute its actual callback before/after the replacement callback.
// All perception, same-position proof, new planning and begin calls are real.
for staleFirst in [true, false] {
    NG2Fake.reset(.walk)
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    let replan = identity()
    diagnoseFixture(replan)
    NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
    alignInitialFixtureMove(replan)
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
    NG2RuntimeTestHooks.afterCaptureDrainProcessed = { id in
        NG2Fake.lock.lock(); NG2Fake.captureDrainedRuns.insert(id); NG2Fake.lock.unlock()
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
    NG2Fake.lock.lock(); let preparedHeld = Set(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
    require(moves.count == 2 && moves.allSatisfy({ preparedHeld.contains(UInt64($0["id"]!.intValue!)) }),
        "replan_fixture_two_move_tickets_are_queued")
    require(moves[0]["outcome"]?.intValue == 3 && moves[0]["begin_ns"]?.intValue == 0,
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
    NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(replan, expectedID: newID) }
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
        pump("replan_capture_worker_drained_and_cycle_processed") {
            NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }
            return NG2Fake.captureDrainedRuns.contains(replan)
        }
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
    fixtureFailureSnapshot = nil
}

// A rejected UNKNOWN difference must retain its own frame even when later
// UNKNOWN observations evict it from the four-frame recent window. No later
// movement event can accidentally supply this reference for the pin test.
NG2Fake.reset(.walk)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let rejectedDifference = identity()
diagnoseFixture(rejectedDifference)
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(rejectedDifference)
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let movements = (report(rejectedDifference)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
    guard movements.contains(where: { $0["id"]?.intValue == Int(id) }) else { return false }
    NG2Fake.holdTicket(id, callback)
    NG2Fake.lock.lock(); NG2Fake.unknownFrames = 10; NG2Fake.lock.unlock()
    return true
}
require(call("necro_native_start", rejectedDifference).1 == nil, "rejected_difference_start")
pump("rejected_difference_terminal", timeout: 12) {
    let current = call("necro_native_status", rejectedDifference, keepalive: true).0?["report"]?.objectValue ?? [:]
    return current["terminal"]?.intValue == 1
}
let rejectedReport = report(rejectedDifference)
let rejectedChanges = rejectedReport["scene_changes"]?.arrayValue ?? []
require(rejectedChanges.count == 1 && rejectedChanges[0].objectValue?["replan_allowed"]?.boolValue == false &&
    rejectedChanges[0].objectValue?["state_after"]?.intValue == 0 && rejectedReport["inputs"]?.intValue == 0,
    "unknown_difference_rejects_replan_without_direction")
let rejected = rejectedChanges[0].objectValue!
require(rejectedReport["last_capture_id"]!.intValue! - rejected["observed_capture_id"]!.intValue! >= 5,
    "rejected_difference_fixture_exceeds_recent_window")
let lastAnalyzedIDs = (rejectedReport["captures"]?.arrayValue ?? []).suffix(4).compactMap { $0.objectValue?["id"]?.intValue }
require(lastAnalyzedIDs.count == 4 && !lastAnalyzedIDs.contains(rejected["observed_capture_id"]!.intValue!),
    "rejected_difference_fixture_evicted_from_recent_analysis_window")
NG2Fake.lock.lock(); let rejectedIDs = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
for id in rejectedIDs { NG2Fake.releaseTicket(id) }
pump("rejected_difference_drained") { drained(rejectedDifference) }
let rejectedResult = call("necro_native_results", rejectedDifference)
let rejectedExports = Set((rejectedResult.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
require(rejectedResult.1 == nil && rejectedExports.contains(rejected["source_capture_id"]!.intValue!) &&
    rejectedExports.contains(rejected["observed_capture_id"]!.intValue!), "rejected_difference_frames_pinned_beyond_recent_window")
fixtureFailureSnapshot = nil

// Public trace telemetry is committed with each actual analysis, bounded to
// first1+latest31. Hold the real RESUME callback and admit captures one at a
// time so31/32/33 are observable states rather than timer-dependent guesses.
NG2Fake.reset(.pause)
let traceRun = identity()
diagnoseFixture(traceRun)
NG2Fake.lock.lock(); NG2Fake.captureLimit = 31; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.beforeCaptureAdmission = {
    while true {
        NG2Fake.lock.lock(); let limit = NG2Fake.captureLimit, requested = NG2Fake.requests; NG2Fake.lock.unlock()
        guard let limit else { return }
        if requested < limit && (report(traceRun)["analyzed_capture_count"]?.intValue ?? 0) >= requested { return }
        Thread.sleep(forTimeInterval: 0.001)
    }
}
NG2RuntimeTestHooks.scheduleTicket = { id, callback in NG2Fake.holdTicket(id, callback); return true }
require(call("necro_native_start", traceRun).1 == nil, "raster_trace_start")
for total in [31, 32, 33] {
    NG2Fake.lock.lock(); NG2Fake.captureLimit = total; NG2Fake.lock.unlock()
    pump("raster_trace_exact_\(total)_analyses", timeout: 12) {
        let current = call("necro_native_status", traceRun, keepalive: true).0?["report"]?.objectValue ?? [:]
        return current["analyzed_capture_count"]?.intValue == total
    }
    let current = report(traceRun)
    let captures = (current["captures"]?.arrayValue ?? []).compactMap { $0.objectValue?["id"]?.intValue }
    let samples = (current["raster_samples"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let sampleIDs = samples.compactMap { $0["capture_id"]?.intValue }
    let expected = total <= 32 ? captures : Array(captures.prefix(1)) + Array(captures.suffix(31))
    require(samples.count == min(total, 32) && sampleIDs == expected && Set(sampleIDs).count == sampleIDs.count &&
        current["raster_samples_dropped"]?.intValue == max(total-32, 0), "raster_trace_first_and_latest_retention_\(total)")
    let traceKeys = Set(["capture_id", "source_width", "source_height", "orientation", "source_ns", "draw_ns", "orient_ns", "scale_ns", "copy_pixels"])
    require(samples.allSatisfy { sample in
        Set(sample.keys) == traceKeys && sample["source_width"]?.intValue == 896 && sample["source_height"]?.intValue == 414 &&
        sample["orientation"]?.intValue == 1 && ["source_ns", "draw_ns", "orient_ns", "scale_ns", "copy_pixels"].allSatisfy { (sample[$0]?.intValue ?? -1) >= 0 }
    }, "raster_trace_immutable_source_geometry_and_fixed_schema_\(total)")
}
let traceBeforeResults = report(traceRun)["raster_samples"]
_ = call("necro_native_cancel", traceRun)
NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; let traceTickets = Array(NG2Fake.heldTickets.keys); NG2Fake.lock.unlock()
for id in traceTickets { NG2Fake.releaseTicket(id) }
pump("raster_trace_cancel_callback_and_capture_drained") { drained(traceRun) }
let traceResult = call("necro_native_results", traceRun)
let traceAfterResults = traceResult.0?["report"]?.objectValue?["raster_samples"]
let traceEncoder = JSONEncoder()
traceEncoder.outputFormatting = [.sortedKeys]
require(traceResult.1 == nil && (try? traceEncoder.encode(traceBeforeResults)) == (try? traceEncoder.encode(traceAfterResults)) &&
    traceResult.0?["report"]?.objectValue?["raster_samples_dropped"]?.intValue == 1 && NG2Fake.countTouches() == 0,
    "raster_trace_public_results_preserves_retained_samples")
fixtureFailureSnapshot = nil

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
