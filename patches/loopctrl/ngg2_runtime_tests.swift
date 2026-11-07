import Foundation

func require(_ condition: Bool, _ name: String) {
    if !condition { print("FAIL \(name)"); exit(1) }
}
let runtime = NG2Runtime.shared
var sequence = 0
func identity() -> String { sequence += 1; return String(format: "%032x", sequence) }
func call(_ method: String, _ id: String, keepalive: Bool? = nil) -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "_necro_owner": .string("fixture-owner")]
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
NG2Fake.advance(6_000_000_000)
require(call("necro_native_status", alive, keepalive: true).1 == nil, "explicit_keepalive")
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

NG2Fake.reset(.pause)
NG2Fake.lock.lock(); NG2Fake.failTouch = true; NG2Fake.lock.unlock()
let unknown = identity()
require(call("necro_native_start", unknown).1 == nil, "unknown_start")
pump("unknown_terminal_drained") { drained(unknown) }
require(report(unknown)["input_state"]?.intValue == 4 && NG2Fake.countTouches() == 1, "started_unknown_no_retry_or_cleanup")

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
let recovered = call("necro_native_results", unknown)
require(recovered.1 == nil && recovered.0?["report"]?.objectValue?["historical_metadata_only"]?.boolValue == true,
    "old_terminal_metadata_recoverable")
require(recovered.0?["images"]?.arrayValue?.isEmpty == true && recovered.0?["retained_images"]?.intValue == 0,
    "old_run_images_explicitly_omitted")
require(call("necro_native_status", unknown, keepalive: true).1 == nil, "old_status_read_does_not_touch_current_run")
print("PASS production Runtime public API/capture/raster/real C/main-input/watchdog/drain integration; UIKit/XCTest/daemon faked")
