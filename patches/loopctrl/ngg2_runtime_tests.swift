import Foundation
import ImageIO

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
func admitFirstFixtureMove(_ id: String, expectedID: UInt64? = nil, afterAlignment: ((UInt64) -> Void)? = nil) {
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
        afterAlignment?(max(now, at))
    }, "fixture_move_admission_capture_boundary")
    NG2RuntimeTestHooks.beforeMainAuthority = nil
}
func alignInitialFixtureMove(_ id: String) {
    // Every caller uses the matching synthetic virtual clock (or its owned
    // motion-deadline wrapper). The real raster/perception/beat path now sees
    // the HUD at the exact fixed capture midpoint, independent of host load.
    NG2Fake.useFixedCaptureClock()
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

// This public request is intentionally runnable against the fixed TEST050
// Runtime, with no dependence on new C diagnostic symbols or producer hooks.
func testPagedResultsManifestPublicBaseline() {
    NG2Fake.reset(.empty)
    let id = identity()
    require(call("necro_native_start", id).1 == nil, "paged_manifest_fixture_public_start")
    pump("paged_manifest_fixture_public_drain") { drained(id) }
    require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0,
        "paged_manifest_fixture_actual_nil_capture_terminal_without_input")
    let result = runtime.handle(method: "necro_native_results", params: [
        "run_id": .string(id), "_necro_owner": .string("fixture-owner"), "mode": .string("manifest")])
    require(result.1 == nil && result.0?["result_mode"]?.stringValue == "manifest" &&
        result.0?["export_id"]?.stringValue?.count == 32,
        "MISSING_paged_results_manifest")
}
// TEST051 MANIFEST FIXTURE END.

// The fixed old TEST049 Runtime uses the same public API and compiled fakes.
// Analysis finishes below gate+100; only the actual committed C boundary moves
// the clock to +200, and its return moves it to +300. The old producer never
// invokes those hooks and must fail the named missing-field assertion.
func testObserveStartAtCommittedCBoundary() {
    NG2Fake.reset(.pause)
    let id = identity()
    let releaseCapture = DispatchSemaphore(value: 0)
    NG2RuntimeTestHooks.clock = { NG2Fake.observeFixtureNow() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() > 0 { releaseCapture.wait() }
    }
    NG2RuntimeTestHooks.beforeAnalysisCommit = { NG2Fake.setObserveGateClock() }
    NG2RuntimeObserveTestHooks.beforeObserve = { NG2Fake.enterObserveBoundary() }
    NG2RuntimeObserveTestHooks.afterObserve = { NG2Fake.leaveObserveBoundary() }
    // A pause image may offer RESUME. Revoke its callback before allowing it
    // to return, preserving real callback drain with no UI action or clock jump.
    NG2RuntimeTestHooks.scheduleTicket = { _, callback in
        _ = call("necro_native_cancel", id); callback(); return true
    }
    require(call("necro_native_start", id).1 == nil, "observe_start_fixture_public_start")
    pump("observe_start_fixture_actual_capture_committed") {
        report(id)["captures"]?.arrayValue?.count == 1
    }
    _ = call("necro_native_cancel", id)
    releaseCapture.signal()
    pump("observe_start_fixture_public_drain") { drained(id) }
    let result = call("necro_native_results", id)
    require(result.1 == nil, "observe_start_fixture_public_results")
    let captures = result.0?["report"]?.objectValue?["captures"]?.arrayValue ?? []
    require(captures.count == 1, "observe_start_fixture_one_committed_public_capture")
    let capture = captures[0].objectValue ?? [:]
    require(capture["observe_start_ns"] != nil, "MISSING_observe_start_ns")
    let boundaries = NG2Fake.observeBoundaries()
    require(boundaries.0 == [1_000_000_200] && boundaries.1 == [1_000_000_300],
        "observe_start_fixture_actual_C_boundaries")
    require((capture["analysis_end_ns"]?.intValue ?? Int.max) < 1_000_000_100,
        "observe_start_fixture_analysis_precedes_commit_gate")
    require(capture["observe_start_ns"]?.intValue == Int(boundaries.0[0]),
        "observe_start_actual_committed_C_entry")
    require(capture["observe_end_ns"]?.intValue == Int(boundaries.1[0]),
        "observe_end_preserves_after_C_publication_clock")
    require(NG2Fake.countTouches() == 0, "observe_start_diagnostics_do_not_send_input")
}
// TEST050 OBSERVE FIXTURE END.

// TEST047 baseline uses only the existing public API and the old nil-reply
// fake. A missing diagnostic must be an executed assertion, not a new API or
// setup failure. The standalone baseline stops at the end marker below.
func diagnosticIsNull(_ value: JSONValue?) -> Bool {
    if case .null? = value { return true }; return false
}
func nilReplyDiagnostic(_ value: [String: JSONValue]?) -> Bool {
    guard let value else { return false }
    let keys = Set(["capture_id", "stage", "code", "start_ns", "end_ns", "encoded_bytes",
        "source_width", "source_height", "orientation"])
    return Set(value.keys) == keys && value["capture_id"]?.intValue == 1 &&
        value["stage"]?.stringValue == "reply" && value["code"]?.stringValue == "other" &&
        (value["start_ns"]?.intValue ?? 0) > 0 &&
        (value["end_ns"]?.intValue ?? 0) > (value["start_ns"]?.intValue ?? 0) &&
        ["encoded_bytes", "source_width", "source_height", "orientation"].allSatisfy { diagnosticIsNull(value[$0]) }
}
NG2Fake.reset(.empty)
let nilReply = identity()
require(call("necro_native_start", nilReply).1 == nil, "capture_failure_nil_reply_fixture_start")
pump("capture_failure_nil_reply_fixture_drained") { drained(nilReply) }
let nilReplyReport = report(nilReply)
require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 &&
    nilReplyReport["reason"]?.intValue == 20, "capture_failure_nil_reply_fixture_reached_capture_guard")
let nilReplyResult = call("necro_native_results", nilReply)
require(nilReplyResult.1 == nil, "capture_failure_nil_reply_fixture_results")
require(nilReplyDiagnostic(nilReplyReport["capture_failure"]?.objectValue) &&
    nilReplyDiagnostic(nilReplyResult.0?["report"]?.objectValue?["capture_failure"]?.objectValue),
    "capture_failure_actual_nil_reply_is_reported")
// TEST047 RUNTIME FAILURE BASELINE END.

// TEST048 public baseline. The held callback must already own a fresh foreground
// sample; querying only after release spends the original ten-millisecond window.
NG2Fake.reset(.walk)
let preparedMove = identity()
diagnoseFixture(preparedMove)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(preparedMove)
var preparedMoveQueries = 0
var preparedQueryIsMove = false
var preparedMoveID: UInt64 = 0
var preparedMoveCommand: [String: JSONValue] = [:]
NG2RuntimeTestHooks.beforeMainAdmission = {
    let current = report(preparedMove)
    let currentID = current["current_command_id"]?.intValue ?? 0
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    NG2Fake.lock.lock()
    preparedQueryIsMove = events.contains(where: { $0["id"]?.intValue == currentID && $0["kind"]?.intValue == 4 })
    NG2Fake.lock.unlock()
}
NG2Fake.lock.lock()
NG2Fake.beforeForegroundQuery = {
    NG2Fake.lock.lock(); let isMove = preparedQueryIsMove
    if isMove { preparedMoveQueries += 1 }; NG2Fake.lock.unlock()
    if isMove { NG2Fake.advance(20_000_000) }
}
NG2Fake.lock.unlock()
NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(preparedMove) }
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let current = report(preparedMove)
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let event = events.first(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
    NG2Fake.lock.lock(); let queries = preparedMoveQueries; NG2Fake.lock.unlock()
    require(queries == 1, "move_foreground_prepared_before_final_callback_is_offered")
    preparedMoveID = id; preparedMoveCommand = event
    NG2Fake.holdTicket(id, callback)
    return true
}
require(call("necro_native_start", preparedMove).1 == nil, "prepared_move_public_start")
pump("prepared_move_final_callback_held", timeout: 12) { preparedMoveID != 0 }
require(runtime.hasLease && report(preparedMove)["main_ticket_outstanding"]?.boolValue == true,
    "prepared_move_pipeline_retains_lease_between_prepare_and_final")
NG2Fake.releaseTicket(preparedMoveID)
pump("prepared_move_single_synth", timeout: 5) { (report(preparedMove)["inputs"]?.intValue ?? 0) == 1 || drained(preparedMove) }
let preparedEvent = (report(preparedMove)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    .first { $0["id"]?.intValue == Int(preparedMoveID) }
require(preparedEvent != nil && ["target_ns", "not_before_ns", "deadline_ns"].allSatisfy {
    preparedEvent?[$0]?.intValue == preparedMoveCommand[$0]?.intValue
}, "prepared_move_preserves_original_target_and_dispatch_window")
NG2Fake.lock.lock(); let preparedQueriesAtSend = preparedMoveQueries; NG2Fake.lock.unlock()
require(preparedQueriesAtSend == 1 && NG2Fake.paths().count == 1 &&
    NG2Fake.paths().first?.first?.last?.t == 0.05, "prepared_move_final_has_no_AX_and_one_50ms_gesture")
cancelDrain(preparedMove)
fixtureFailureSnapshot = nil
// TEST048 RUNTIME DISPATCH BASELINE END.

// TEST050 full-suite invocation; the baseline executes this fixture alone.
testObserveStartAtCommittedCBoundary()

require(NG2Runtime.testFrameStride < 512, "published_Frame_keeps_large_C_scene_off_value_stack")

// Generation alone can revoke a still-owned final callback. No cancellation,
// owner loss or old command ID may mask this final admission requirement.
NG2Fake.reset(.walk)
let finalGeneration = identity()
diagnoseFixture(finalGeneration)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(finalGeneration)
var generationTicket: UInt64 = 0
let generationReturnLock = NSLock()
var generationReturned = false
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let events = (report(finalGeneration)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard events.contains(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
    generationTicket = id; NG2Fake.holdTicket(id, callback); return true
}
NG2RuntimeTestHooks.afterTicketReturned = { id in
    if id == generationTicket { generationReturnLock.lock(); generationReturned = true; generationReturnLock.unlock() }
}
NG2RuntimeTestHooks.beforeMainAuthority = {
    admitFirstFixtureMove(finalGeneration)
    _ = runtime.testFailureGeneration(finalGeneration, advance: true)
}
require(call("necro_native_start", finalGeneration).1 == nil, "final_generation_revocation_public_start")
pump("final_generation_live_ticket_reserved", timeout: 12) { generationTicket != 0 }
NG2Fake.releaseTicket(generationTicket)
pump("final_generation_callback_actually_returned") {
    generationReturnLock.lock(); defer { generationReturnLock.unlock() }; return generationReturned
}
require(NG2Fake.paths().isEmpty && report(finalGeneration)["cancel_requested"]?.boolValue == false &&
    diagnosticIsNull(report(finalGeneration)["dispatch_failure"]), "final_generation_only_revocation_prevents_synth")
cancelDrain(finalGeneration)
fixtureFailureSnapshot = nil

// Holding the real pure-perception call must leave the reserved control ticket
// runnable. The fixed gate clock removes GCD wake-up jitter from this contract.
NG2Fake.reset(.walk)
let scanningMove = identity()
diagnoseFixture(scanningMove)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(scanningMove)
let scanningLock = NSLock()
let scanningRelease = DispatchSemaphore(value: 0)
var scanningHeld = false
var scanningMoveID: UInt64 = 0
var scanningNotBefore: UInt64 = 0
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let events = (report(scanningMove)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let move = events.first(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
    scanningLock.lock(); scanningMoveID = id; scanningNotBefore = UInt64(move["not_before_ns"]!.intValue!); scanningLock.unlock()
    NG2RuntimeTestHooks.analysisRGBA = { rgba in
        scanningLock.lock(); let first = !scanningHeld; scanningHeld = true; scanningLock.unlock()
        if first { _ = scanningRelease.wait(timeout: .now()+5) }
        return rgba
    }
    NG2Fake.holdTicket(id, callback)
    return true
}
require(call("necro_native_start", scanningMove).1 == nil, "pure_analysis_hold_public_start")
pump("pure_analysis_worker_reaches_hold", timeout: 12) {
    scanningLock.lock(); defer { scanningLock.unlock() }; return scanningHeld && scanningMoveID != 0
}
scanningLock.lock(); let scanningAt = scanningNotBefore, scanningID = scanningMoveID; scanningLock.unlock()
NG2RuntimeTestHooks.clock = { scanningAt }
NG2Fake.releaseTicket(scanningID)
let scanProgressDeadline = Date().addingTimeInterval(2)
while NG2Fake.paths().isEmpty && Date() < scanProgressDeadline { RunLoop.current.run(until: Date().addingTimeInterval(0.005)) }
require(NG2Fake.paths().count == 1, "pure_analysis_hold_does_not_block_final_MOVE")
require(runtime.hasLease && report(scanningMove)["workers_drained"]?.boolValue == false,
    "pure_analysis_worker_keeps_lease_until_actual_return")
let scanningCurrent = NG2Fake.virtualClock()
if scanningCurrent < scanningAt { NG2Fake.advance(scanningAt-scanningCurrent) }
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
_ = call("necro_native_cancel", scanningMove)
NG2RuntimeTestHooks.analysisRGBA = nil
scanningRelease.signal()
pump("pure_analysis_cancelled_worker_drained") { drained(scanningMove) }
require(NG2Fake.paths().count == 1 && report(scanningMove)["missing_capture_ids"]?.arrayValue?.isEmpty == true,
    "pure_analysis_cancel_keeps_one_synth_and_pinned_references")
fixtureFailureSnapshot = nil

// This wait deliberately never pumps main: queued bootstrap work must stay
// queued while the independent watchdog and public status lane are exercised.
func waitWithoutMain(_ name: String, timeout: Double = 3, _ condition: () -> Bool) {
    let deadline = Date().addingTimeInterval(timeout)
    while !condition() && Date() < deadline { Thread.sleep(forTimeInterval: 0.005) }
    require(condition(), name)
}
final class WatchdogObservation {
    private let lock = NSLock()
    private var last: UInt64?
    func record(_ time: UInt64) { lock.lock(); last = time; lock.unlock() }
    func latest() -> UInt64? { lock.lock(); defer { lock.unlock() }; return last }
}
func observeWatchdog(_ id: String) -> WatchdogObservation {
    let observation = WatchdogObservation()
    NG2RuntimeTestHooks.afterWatchdogCheck = { checkedID, time in
        if checkedID == id { observation.record(time) }
    }
    return observation
}

func captureFailureRecord(_ id: String) -> [String: JSONValue]? { report(id)["capture_failure"]?.objectValue }
func failureRoundtrip(_ id: String) -> Bool {
    guard let expected = captureFailureRecord(id),
          let result = call("necro_native_results", id).0?["report"]?.objectValue?["capture_failure"]?.objectValue else { return false }
    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
    guard let first = try? encoder.encode(expected), let second = try? encoder.encode(result) else { return false }
    return first == second
}
func captureFailureFixture(_ data: Data?, _ error: String?, stage: String, code: String) -> [String: JSONValue] {
    NG2Fake.reset(.reply)
    NG2Fake.lock.lock(); NG2Fake.replyData = data; NG2Fake.replyError = error; NG2Fake.lock.unlock()
    let id = identity()
    require(call("necro_native_start", id).1 == nil, "capture_failure_fixture_start_"+code)
    pump("capture_failure_fixture_drained_"+code) { drained(id) }
    let snapshot = report(id), value = captureFailureRecord(id)
    require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 && snapshot["reason"]?.intValue == 20 &&
        snapshot["analyzed_capture_count"]?.intValue == 0 && snapshot["raster_samples"]?.arrayValue?.isEmpty == true,
        "capture_failure_without_retry_input_or_success_trace_"+code)
    require(value?["capture_id"]?.intValue == 1 && value?["stage"]?.stringValue == stage &&
        value?["code"]?.stringValue == code && failureRoundtrip(id), "capture_failure_public_stage_code_"+code)
    return value!
}
let bridgeFailures: [(String?, String)] = [
    (nil, "missing_data"), ("direct capture API unavailable", "api_unavailable"),
    ("direct capture session unavailable", "session_unavailable"),
    ("direct capture display unprepared", "display_unprepared"),
    ("direct capture request unavailable", "request_unavailable"),
    ("direct capture failed", "capture_failed"), ("direct capture bytes invalid", "bytes_invalid"),
    ("direct capture reply exception", "reply_exception"),
    ("direct capture request exception", "request_exception"),
    ("PRIVATE-UNEXPECTED-CAPTURE-ERROR", "other")]
for (error, code) in bridgeFailures {
    let value = captureFailureFixture(nil, error, stage: "reply", code: code)
    require(["encoded_bytes", "source_width", "source_height", "orientation"].allSatisfy { diagnosticIsNull(value[$0]) },
        "capture_failure_reply_unobserved_metadata_stays_null_"+code)
    let encoded = String(data: try! JSONEncoder().encode(value), encoding: .utf8)!
    require(!encoded.contains("PRIVATE") && !encoded.contains("direct capture"), "capture_failure_never_saves_bridge_text_"+code)
}
for (bytes, code) in [(Data(), "encoded_empty"), (Data(count: 8*1024*1024+1), "encoded_limit")] {
    let value = captureFailureFixture(bytes, nil, stage: "source", code: code)
    require(value["encoded_bytes"]?.intValue == bytes.count && diagnosticIsNull(value["source_width"]) &&
        diagnosticIsNull(value["source_height"]) && diagnosticIsNull(value["orientation"]),
        "capture_failure_source_bytes_and_unknown_metadata_"+code)
}
// ImageIO can accept a provisional source for incomplete bytes. Observe its
// actual factory boundary before choosing the expected production failure.
let incompleteBytes = Data([1, 2, 3])
let incompleteSource = CGImageSourceCreateWithData(incompleteBytes as CFData, nil)
let incompleteCode: String
if let source = incompleteSource {
    if CGImageSourceGetCount(source) != 1 { incompleteCode = "image_count" }
    else {
        require(CGImageSourceCreateImageAtIndex(source, 0, nil) == nil, "capture_failure_incomplete_bytes_fixture_has_no_image")
        incompleteCode = "image_create"
    }
} else { incompleteCode = "source_open" }
let incompleteFailure = captureFailureFixture(incompleteBytes, nil, stage: "source", code: incompleteCode)
require(incompleteFailure["encoded_bytes"]?.intValue == incompleteBytes.count,
    "capture_failure_incomplete_source_keeps_actual_encoded_size")
let invalidAspect = captureFailureFixture(NG2Fake.squarePNG, nil, stage: "metadata", code: "aspect")
require(invalidAspect["encoded_bytes"]?.intValue == NG2Fake.squarePNG.count &&
    invalidAspect["source_width"]?.intValue == 2 && invalidAspect["source_height"]?.intValue == 2 &&
    diagnosticIsNull(invalidAspect["orientation"]), "capture_failure_invalid_aspect_preserves_source_metadata")

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { 1_000_000_000_000 }
let invalidInterval = identity()
require(call("necro_native_start", invalidInterval).1 == nil, "capture_failure_interval_start")
pump("capture_failure_interval_drained") { drained(invalidInterval) }
let intervalFailure = captureFailureRecord(invalidInterval)
require(intervalFailure?["stage"]?.stringValue == "interval" && intervalFailure?["code"]?.stringValue == "invalid_interval" &&
    intervalFailure?["start_ns"]?.intValue == 1_000_000_000_000 && intervalFailure?["end_ns"]?.intValue == 1_000_000_000_000 &&
    diagnosticIsNull(intervalFailure?["encoded_bytes"]) && failureRoundtrip(invalidInterval),
    "capture_failure_equal_interval_is_preserved_without_retry")

NG2Fake.reset(.pause)
let invalidAnalysis = identity()
diagnoseFixture(invalidAnalysis)
let untaggedSource = CGImageSourceCreateWithData(NG2Fake.pausePNG as CFData, nil)!
let untaggedProperties = CGImageSourceCopyPropertiesAtIndex(untaggedSource, 0, nil) as! [CFString: Any]
require(CGImageSourceGetCount(untaggedSource) == 1 && untaggedProperties[kCGImagePropertyOrientation] == nil,
    "capture_failure_PNG_fixture_has_no_EXIF_orientation")
NG2RuntimeTestHooks.analysisRGBA = { _ in Data() }
require(call("necro_native_start", invalidAnalysis).1 == nil, "capture_failure_analysis_start")
pump("capture_failure_analysis_drained") { drained(invalidAnalysis) }
let analysisFailure = captureFailureRecord(invalidAnalysis)
require(analysisFailure?["stage"]?.stringValue == "analysis" && analysisFailure?["code"]?.stringValue == "invalid_rgba" &&
    analysisFailure?["capture_id"]?.intValue == 1 && analysisFailure?["encoded_bytes"]?.intValue == NG2Fake.pausePNG.count &&
    analysisFailure?["source_width"]?.intValue == 896 && analysisFailure?["source_height"]?.intValue == 414 &&
    diagnosticIsNull(analysisFailure?["orientation"]) && failureRoundtrip(invalidAnalysis) && NG2Fake.countTouches() == 0,
    "capture_failure_real_C_analysis_rejection_is_reported")

NG2Fake.reset(.reply)
let portraitBytes = NG2Fake.portraitTIFF
let portraitSource = CGImageSourceCreateWithData(portraitBytes as CFData, nil)!
let portraitProperties = CGImageSourceCopyPropertiesAtIndex(portraitSource, 0, nil) as! [CFString: Any]
require(CGImageSourceGetCount(portraitSource) == 1 &&
    (portraitProperties[kCGImagePropertyPixelWidth] as? NSNumber)?.intValue == 414 &&
    (portraitProperties[kCGImagePropertyPixelHeight] as? NSNumber)?.intValue == 896 &&
    (portraitProperties[kCGImagePropertyOrientation] as? NSNumber)?.intValue == 8,
    "capture_failure_EXIF8_fixture_serializes_real_orientation")
NG2Fake.lock.lock(); NG2Fake.replyData = portraitBytes; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.analysisRGBA = { _ in Data() }
let orientedAnalysis = identity()
diagnoseFixture(orientedAnalysis)
require(call("necro_native_start", orientedAnalysis).1 == nil, "capture_failure_EXIF8_analysis_start")
pump("capture_failure_EXIF8_analysis_drained") { drained(orientedAnalysis) }
let orientedFailure = captureFailureRecord(orientedAnalysis)
require(orientedFailure?["stage"]?.stringValue == "analysis" && orientedFailure?["code"]?.stringValue == "invalid_rgba" &&
    orientedFailure?["encoded_bytes"]?.intValue == portraitBytes.count &&
    orientedFailure?["source_width"]?.intValue == 414 && orientedFailure?["source_height"]?.intValue == 896 &&
    orientedFailure?["orientation"]?.intValue == 8 && failureRoundtrip(orientedAnalysis) && NG2Fake.countTouches() == 0,
    "capture_failure_analysis_preserves_observed_EXIF8")
fixtureFailureSnapshot = nil

// Change only the generation after decoding failed and before its production
// commit. Cancellation and owner checks remain true at that exact boundary.
NG2Fake.reset(.reply)
let oldFailureGeneration = identity()
NG2Fake.lock.lock(); NG2Fake.replyError = "direct capture failed"; NG2Fake.lock.unlock()
var generationChangedWhileActive = false
NG2RuntimeTestHooks.beforeCaptureFailureCommit = { id in
    require(id == oldFailureGeneration, "capture_failure_generation_fixture_identity")
    let old = runtime.testFailureGeneration(id)!
    let current = runtime.testFailureGeneration(id, advance: true)!
    generationChangedWhileActive = current == old+1 && report(id)["cancel_requested"]?.boolValue == false && !RemoteSession.shared.paused
    NG2RuntimeTestHooks.beforeCaptureFailureCommit = nil
}
require(call("necro_native_start", oldFailureGeneration).1 == nil, "capture_failure_generation_start")
pump("capture_failure_generation_drained") { drained(oldFailureGeneration) }
require(generationChangedWhileActive, "capture_failure_generation_fixture_changes_only_generation")
require(diagnosticIsNull(report(oldFailureGeneration)["capture_failure"]) &&
    diagnosticIsNull(call("necro_native_results", oldFailureGeneration).0?["report"]?.objectValue?["capture_failure"]),
    "capture_failure_generation_only_revocation_does_not_publish")

for revoked in ["cancel", "owner"] {
    NG2Fake.reset(.reply)
    NG2Fake.lock.lock(); NG2Fake.replyError = "direct capture failed"; NG2Fake.lock.unlock()
    let id = identity()
    NG2RuntimeTestHooks.beforeCaptureFailureCommit = { expected in
        require(expected == id, "capture_failure_revocation_fixture_identity_"+revoked)
        if revoked == "cancel" { _ = call("necro_native_cancel", id) }
        else { RemoteSession.shared.paused = true }
        NG2RuntimeTestHooks.beforeCaptureFailureCommit = nil
    }
    require(call("necro_native_start", id).1 == nil, "capture_failure_revocation_start_"+revoked)
    pump("capture_failure_revocation_drained_"+revoked) { drained(id) }
    require(diagnosticIsNull(report(id)["capture_failure"]) && NG2Fake.countTouches() == 0,
        "capture_failure_revoked_commit_never_publishes_"+revoked)
    RemoteSession.shared.paused = false
    require(diagnosticIsNull(call("necro_native_results", id).0?["report"]?.objectValue?["capture_failure"]),
        "capture_failure_revoked_results_stay_null_"+revoked)
}

// Competing failures exercise the real first-only gate while a daemon request
// is held. Setup submits A and B; only public status/results determine success.
NG2Fake.reset(.hold)
let firstFailure = identity()
require(call("necro_native_start", firstFailure).1 == nil, "capture_failure_first_start")
pump("capture_failure_first_request_held") { NG2Fake.countRequests() == 1 }
let firstGeneration = runtime.testFailureGeneration(firstFailure)!
let failureA = NG2Raster.Failure(stage: .metadata, code: .orientation, encodedBytes: 4,
    sourceWidth: 0, sourceHeight: -1, orientation: 9)
let failureB = NG2Raster.Failure(stage: .source, code: .sourceOpen, encodedBytes: 3)
require(runtime.testCommitFailure(firstFailure, generation: firstGeneration, captureID: 11, start: 10, end: 9, failure: failureA),
    "capture_failure_first_A_fixture_committed")
let secondAccepted = runtime.testCommitFailure(firstFailure, generation: firstGeneration, captureID: 12, start: 20, end: 21, failure: failureB)
let firstRecord = captureFailureRecord(firstFailure)
require(!secondAccepted && firstRecord?["capture_id"]?.intValue == 11 && firstRecord?["code"]?.stringValue == "orientation" &&
    firstRecord?["source_width"]?.intValue == 0 && firstRecord?["source_height"]?.intValue == -1 && firstRecord?["orientation"]?.intValue == 9,
    "capture_failure_first_record_is_immutable")
let nextFailureGeneration = runtime.testFailureGeneration(firstFailure, advance: true)!
let staleAccepted = runtime.testCommitFailure(firstFailure, generation: firstGeneration, captureID: 13, start: 30, end: 31, failure: failureB)
let laterAccepted = runtime.testCommitFailure(firstFailure, generation: nextFailureGeneration, captureID: 14, start: 40, end: 41, failure: failureB)
require(!staleAccepted && !laterAccepted && captureFailureRecord(firstFailure)?["capture_id"]?.intValue == 11,
    "capture_failure_later_generations_do_not_replace_first_record")
cancelDrain(firstFailure)
require(failureRoundtrip(firstFailure), "capture_failure_first_record_survives_drain_and_results")

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
NG2RuntimeTestHooks.beforeMainAuthority = {
    let events = report(staleMainClock)["events"]?.arrayValue ?? []
    let deadline = events.last?.objectValue?["deadline_ns"]?.intValue ?? 0
    let current = NG2Fake.virtualClock()
    require(deadline > 0 && UInt64(deadline) >= current, "main_clock_fixture_ticket_still_valid")
    NG2Fake.advance(UInt64(deadline)-current+1)
    advancedAtAdmission = true
    NG2RuntimeTestHooks.beforeMainAuthority = nil
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
    NG2RuntimeObserveTestHooks.beforeObserve = { NG2Fake.enterObserveBoundary() }
    NG2RuntimeObserveTestHooks.afterObserve = { NG2Fake.leaveObserveBoundary() }
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
    let boundaries = NG2Fake.observeBoundaries()
    require(snapshot["captures"]?.arrayValue?.isEmpty == true && boundaries.0.isEmpty && boundaries.1.isEmpty,
        "revoked_analysis_never_publishes_capture_or_observe_start_"+revoked)
    RemoteSession.shared.paused = false
    require(call("necro_native_results", analysisRace).0?["report"]?.objectValue?["captures"]?.arrayValue?.isEmpty == true,
        "revoked_analysis_public_results_have_no_observe_start_"+revoked)
}

// A generation replacement alone revokes the analyzed frame. Keep the next
// capture outside admission until the actual cycle has rejected this one;
// cancellation used for drain happens only after observing that rejection.
NG2Fake.reset(.pause)
let observeGenerationRace = identity()
let releaseGenerationCapture = DispatchSemaphore(value: 0)
var observeGenerationRevoked = false
var observeGenerationProcessed = false
NG2RuntimeTestHooks.beforeCaptureAdmission = {
    if NG2Fake.countRequests() > 0 { releaseGenerationCapture.wait() }
}
NG2RuntimeTestHooks.beforeAnalysisCommit = {
    _ = runtime.testFailureGeneration(observeGenerationRace, advance: true)
    NG2Fake.lock.lock(); observeGenerationRevoked = true; NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.beforeAnalysisCommit = nil
}
NG2RuntimeTestHooks.beforeControlTick = {
    NG2Fake.lock.lock()
    if observeGenerationRevoked { observeGenerationProcessed = true }
    NG2Fake.lock.unlock()
}
NG2RuntimeObserveTestHooks.beforeObserve = { NG2Fake.enterObserveBoundary() }
NG2RuntimeObserveTestHooks.afterObserve = { NG2Fake.leaveObserveBoundary() }
require(call("necro_native_start", observeGenerationRace).1 == nil, "observe_start_generation_fixture_start")
pump("observe_start_generation_actual_cycle_processed") {
    NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }; return observeGenerationProcessed
}
let observeGenerationSnapshot = report(observeGenerationRace)
let observeGenerationBoundaries = NG2Fake.observeBoundaries()
require(observeGenerationSnapshot["cancel_requested"]?.boolValue == false &&
    observeGenerationSnapshot["accepted_frames"]?.intValue == 0 &&
    observeGenerationSnapshot["analyzed_capture_count"]?.intValue == 0 &&
    observeGenerationSnapshot["retained_image_count"]?.intValue == 0 &&
    observeGenerationSnapshot["captures"]?.arrayValue?.isEmpty == true &&
    observeGenerationBoundaries.0.isEmpty && observeGenerationBoundaries.1.isEmpty,
    "generation_only_revoked_analysis_never_publishes_capture_or_observe_start")
_ = call("necro_native_cancel", observeGenerationRace)
releaseGenerationCapture.signal()
pump("observe_start_generation_public_drain") { drained(observeGenerationRace) }
require(call("necro_native_results", observeGenerationRace).0?["report"]?.objectValue?["captures"]?.arrayValue?.isEmpty == true &&
    NG2Fake.countTouches() == 0, "generation_only_revoked_public_results_have_no_observe_start_or_input")

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
waitWithoutMain("queued_bootstrap_fixture_reached_main_barrier") { report(queued)["main_ticket_outstanding"]?.boolValue == true }
require(runtime.leaseError("gesture") != nil && runtime.leaseError("device_info") != nil, "legacy_UI_receipt_blocked")
require(runtime.leaseError("necro_native_status") == nil && runtime.leaseError("necro_native_cancel") == nil, "status_cancel_nonUI_lane")
require(call("necro_native_status", queued).1 == nil, "status_answers_while_main_not_pumped")
_ = call("necro_native_cancel", queued)
pump("queued_cancel_drained") { drained(queued) }
require(NG2Fake.countActivations() == 0 && NG2Fake.countRequests() == 0, "queued_bootstrap_cancel_no_late_activation")

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let readOnly = identity()
let readOnlyWatchdog = observeWatchdog(readOnly)
require(call("necro_native_start", readOnly).1 == nil, "readonly_start")
waitWithoutMain("readonly_watchdog_fixture_started") { readOnlyWatchdog.latest() != nil }
NG2Fake.advance(6_000_000_000)
require(call("necro_native_status", readOnly).1 == nil, "readonly_status")
waitWithoutMain("readonly_watchdog_cancel_observed_without_main") { report(readOnly)["cancel_requested"]?.boolValue == true }
require(report(readOnly)["cancel_requested"]?.boolValue == true, "status_default_does_not_extend_watchdog")
pump("readonly_drained") { drained(readOnly) }
require(report(readOnly)["reason"]?.intValue == 19 && NG2Fake.countActivations() == 0, "heartbeat_stops_queued_bootstrap")

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let alive = identity()
let aliveWatchdog = observeWatchdog(alive)
require(call("necro_native_start", alive).1 == nil, "keepalive_start")
waitWithoutMain("keepalive_watchdog_fixture_started") { aliveWatchdog.latest() != nil }
// Establish the heartbeat origin after startup scheduling has completed.
require(call("necro_native_status", alive, keepalive: true).1 == nil, "keepalive_fixture_heartbeat_origin")
// Renew before expiry; advancing beyond expiry before sending the renewal
// would race the independent watchdog and legitimately allow cancellation.
NG2Fake.advance(4_000_000_000)
require(call("necro_native_status", alive, keepalive: true).1 == nil, "explicit_keepalive")
NG2Fake.advance(2_000_000_000)
let aliveCheckAfter = NG2Fake.virtualClock()
waitWithoutMain("active_keepalive_watchdog_checked_after_advance") {
    aliveWatchdog.latest().map { $0 >= aliveCheckAfter } ?? false
}
require(report(alive)["cancel_requested"]?.boolValue == false, "active_explicit_keepalive_renews")
cancelDrain(alive)

NG2Fake.reset(.empty)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
let hardLimit = identity()
let hardLimitWatchdog = observeWatchdog(hardLimit)
require(call("necro_native_start", hardLimit).1 == nil, "session_limit_start")
waitWithoutMain("hard_limit_watchdog_fixture_started") { hardLimitWatchdog.latest() != nil }
NG2Fake.advance(181_000_000_000)
_ = call("necro_native_status", hardLimit, keepalive: true)
waitWithoutMain("hard_limit_watchdog_cancel_observed_without_main") { report(hardLimit)["cancel_requested"]?.boolValue == true }
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
    let pendingWait = report(subtile)["motion_wait"]?.objectValue ?? [:]
    NG2Fake.lock.lock(); let explicitBoundary = NG2Fake.boundaryClockChange != nil; NG2Fake.lock.unlock()
    if pendingWait["active"]?.boolValue == true && !explicitBoundary {
        // Each scripted 35px/36px transition depends on the previous public
        // C assessment. Do not let the producer render three 35px frames
        // while its first UNKNOWN is still being cached on controlQueue.
        let previousRequest = NG2Fake.countRequests()
        let end = Date().addingTimeInterval(2)
        func previousAssessmentPublished() -> Bool {
            let snapshot = report(subtile)
            guard let capture = snapshot["captures"]?.arrayValue?.last?.objectValue,
                (capture["id"]?.intValue ?? 0) >= previousRequest else { return false }
            // Capture rows are appended before the C status/cache projection.
            // An eligible stable matching-prefix frame must also reach that
            // latter snapshot. Stable captures from before the ACK can still
            // have an old prefix and be legitimately discarded by C.
            let eligible = capture["stable"]?.boolValue == true &&
                capture["completed_prefix_end"] == snapshot["last_completed_id"]
            return !eligible ||
                (snapshot["last_capture_id"]?.intValue ?? 0) >= previousRequest
        }
        var committed = previousAssessmentPublished()
        while !committed && Date() < end {
            Thread.sleep(forTimeInterval: 0.001)
            committed = previousAssessmentPublished()
        }
        require(committed, "subtile_previous_assessment_is_public_before_rendering_followup")
    }
    NG2Fake.performBoundaryClockChange()
    let current = report(subtile), wait = report(subtile)["motion_wait"]?.objectValue ?? [:]
    if wait["active"]?.boolValue == true && wait["attempts"]?.intValue == 1 {
        require(wait["last_motion"]?.intValue == 0 && current["input_state"]?.intValue == 3 &&
            NG2Fake.paths().count == 1, "subtile_UNKNOWN_ACK_wait_has_no_followup_MOVE")
        NG2Fake.lock.lock()
        if NG2Fake.firstUnknownID == 0 { NG2Fake.firstUnknownID = UInt64(wait["last_capture_id"]!.intValue!) }
        NG2Fake.walkPixelInset = 0
        // Reveal goods in the very same full36px frame. Enabling them only
        // after moves1 was published could lose the next dispatch race.
        NG2Fake.walkGoodsEnabled = true
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

// Cross the original motion deadline before committing an analyzed image,
// while its request and analysis end remain before it. The next production tick
// must use its actual clock. A second tick may never repair a missed first one.
NG2Fake.reset(.walk)
let motionLate = identity()
diagnoseFixture(motionLate)
NG2Fake.lock.lock(); NG2Fake.walkPixelInset = 1; NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
// Host scheduling and PNG/analysis cost do not advance this fixture's clock
// after the admitted MOVE. Keep every real capture interval positive, advance
// to an eligible post-ACK phase, then cross only at the explicit boundary below.
let motionFixtureClockLock = NSLock()
var motionFixtureClock: UInt64?
var motionFixtureLastClock: UInt64 = 0
func motionFixtureNow() -> UInt64 {
    motionFixtureClockLock.lock(); defer { motionFixtureClockLock.unlock() }
    let value = max(motionFixtureClock ?? NG2Fake.virtualClock(), motionFixtureLastClock+1)
    motionFixtureLastClock = value
    if motionFixtureClock != nil { motionFixtureClock = value+1 }
    return value
}
NG2RuntimeTestHooks.clock = { motionFixtureNow() }
NG2Fake.lock.lock(); NG2Fake.captureTimeProvider = { motionFixtureNow() }; NG2Fake.lock.unlock()
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange(); NG2Fake.waitForCapturePermit() }
alignInitialFixtureMove(motionLate)
NG2RuntimeTestHooks.beforeMainAuthority = {
    admitFirstFixtureMove(motionLate, afterAlignment: { aligned in
        motionFixtureClockLock.lock()
        motionFixtureClock = max(aligned, motionFixtureLastClock+1)
        motionFixtureClockLock.unlock()
    })
}
NG2RuntimeTestHooks.afterTicketReturned = { id in
    let snapshot = report(motionLate)
    let events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let move = events.first(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return }
    let eligible = UInt64(move["target_ns"]!.intValue!)+80_000_001
    let deadline = UInt64(snapshot["motion_wait"]!.objectValue!["deadline_ns"]!.intValue!)
    require(snapshot["input_state"]?.intValue == 3 && eligible < deadline,
        "motion_deadline_fixture_actual_ACK_has_original_observation_window")
    motionFixtureClockLock.lock()
    motionFixtureClock = max(eligible, motionFixtureLastClock+1)
    motionFixtureClockLock.unlock()
    NG2RuntimeTestHooks.afterTicketReturned = nil
}
scheduleFirstFixtureMove(motionLate, holdingPause: true)
var crossedMotionDeadline = false
var deadlineTicks = 0
NG2RuntimeTestHooks.beforeAnalysisCommit = {
    let wait = report(motionLate)["motion_wait"]?.objectValue ?? [:]
    guard !crossedMotionDeadline, wait["active"]?.boolValue == true && wait["attempts"]?.intValue == 1 else { return }
    let deadline = UInt64(wait["deadline_ns"]!.intValue!)
    require(motionFixtureNow() < deadline, "motion_deadline_fixture_analysis_starts_before_original_deadline")
    require(NG2Fake.changeClockAtCaptureBoundary {
        let now = NG2Fake.virtualClock()
        if now <= deadline { NG2Fake.advance(deadline+1-now) }
        motionFixtureClockLock.lock(); motionFixtureClock = deadline+1; motionFixtureClockLock.unlock()
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
    lateSource?["stable"]?.boolValue == true && lateSource?["completed_prefix_end"]?.intValue == lateMove["id"]?.intValue &&
    (lateSource?["end_ns"]?.intValue ?? Int.max) <= (lateWait["deadline_ns"]?.intValue ?? 0) &&
    (lateSource?["analysis_end_ns"]?.intValue ?? Int.max) < (lateWait["deadline_ns"]?.intValue ?? 0),
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
        var staleFinalHooks = 0
        NG2RuntimeTestHooks.beforeMainAuthority = { staleFinalHooks += 1 }
        NG2Fake.releaseTicket(oldID)
        pump("replan_stale_callback_returned") {
            NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }; return NG2Fake.returnedTickets.contains(oldID)
        }
        require(oldQueries == 0, "replan_stale_callback_skips_AX_and_shared_authority")
        require(staleFinalHooks == 0, "replan_stale_callback_skips_final_authority_hook")
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        require(diagnosticIsNull(report(replan)["dispatch_failure"]), "stale_ticket_does_not_publish_dispatch_failure")
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

// Each code is induced at the public walk path, never by a client-side
// fabricated report. Clock changes occur between complete raw captures.
func sameDispatchFailure(_ a: [String: JSONValue]?, _ b: [String: JSONValue]?) -> Bool {
    guard let a, let b else { return false }
    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
    return (try? encoder.encode(a)) == (try? encoder.encode(b))
}
let dispatchFailureKeys = Set(["command_id", "not_before_ns", "deadline_ns", "query_start_ns", "query_end_ns",
    "main_entry_ns", "gate_ns", "code"])
for failureCode in ["foreground", "locked", "owner", "authority_stale", "too_early", "too_late", "controller_rejected"] {
    NG2Fake.reset(.walk)
    let failedMove = identity()
    diagnoseFixture(failedMove)
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
    alignInitialFixtureMove(failedMove)
    var failedCommand: [String: JSONValue] = [:]
    var finalGateVisited = false
    var externalQueryEntry: UInt64 = 0, externalQueryExit: UInt64 = 0
    var externalFinalEntry: UInt64 = 0, externalFinalExit: UInt64 = 0
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        let entered = NG2Fake.virtualClock()
        let current = report(failedMove)
        let currentID = current["current_command_id"]?.intValue ?? 0
        let commands = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard commands.contains(where: { $0["id"]?.intValue == currentID && $0["kind"]?.intValue == 4 }) else { return }
        if failureCode == "foreground" {
            NG2Fake.lock.lock(); NG2Fake.frontPID = 0; NG2Fake.lock.unlock()
            // Give this observed AX interval distinct endpoints on the fixed
            // clock so swapping query_start with query_end remains detectable.
            NG2Fake.advance(1_000)
        }
        if failureCode == "authority_stale" { NG2Fake.advance(1_000_000_001) }
        externalQueryEntry = entered; externalQueryExit = NG2Fake.virtualClock()
    }
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.scheduleTicket = { id, callback in
        let commands = (report(failedMove)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let command = commands.first(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
        require(diagnosticIsNull(report(failedMove)["dispatch_failure"]), "dispatch_failure_null_before_first_rejection_"+failureCode)
        failedCommand = command
        callback(); return true
    }
    NG2RuntimeTestHooks.beforeMainAuthority = {
        let entered = NG2Fake.virtualClock()
        let current = report(failedMove)
        let currentID = current["current_command_id"]?.intValue ?? 0
        let commands = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let command = commands.first(where: { $0["id"]?.intValue == currentID && $0["kind"]?.intValue == 4 }) else { return }
        finalGateVisited = true
        if failureCode == "too_early" {
            require(NG2Fake.virtualClock() < UInt64(command["not_before_ns"]!.intValue!), "dispatch_early_fixture_precedes_original_notBefore")
            NG2RuntimeTestHooks.beforeMainAuthority = nil
        } else if failureCode == "authority_stale" {
            NG2RuntimeTestHooks.beforeMainAuthority = nil
        } else {
            admitFirstFixtureMove(failedMove)
            if failureCode == "locked" { LockStateMonitor.monitor.isLocked = true }
            if failureCode == "owner" { RemoteSession.shared.paused = true }
            if failureCode == "too_late" {
                let deadline = UInt64(command["deadline_ns"]!.intValue!)
                require(NG2Fake.changeClockAtCaptureBoundary {
                    let now = NG2Fake.virtualClock()
                    if now <= deadline { NG2Fake.advance(deadline-now+1) }
                }, "dispatch_late_fixture_capture_boundary")
            }
            if failureCode == "controller_rejected" {
                runtime.testInvalidateControllerTicket(failedMove)
            }
        }
        externalFinalEntry = entered; externalFinalExit = NG2Fake.virtualClock()
    }
    require(call("necro_native_start", failedMove).1 == nil, "dispatch_failure_public_start_"+failureCode)
    pump("dispatch_failure_committed_"+failureCode, timeout: 12) {
        _ = call("necro_native_status", failedMove, keepalive: true)
        return report(failedMove)["dispatch_failure"]?.objectValue != nil || drained(failedMove)
    }
    let firstFailure = report(failedMove)["dispatch_failure"]?.objectValue
    if failureCode == "foreground" {
        require(externalQueryExit > externalQueryEntry, "dispatch_foreground_fixture_has_positive_query_interval")
    }
    require(finalGateVisited && firstFailure?["code"]?.stringValue == failureCode && Set(firstFailure?.keys.map { $0 } ?? []) == dispatchFailureKeys &&
        firstFailure?["command_id"]?.intValue == failedCommand["id"]?.intValue &&
        ["not_before_ns", "deadline_ns"].allSatisfy { firstFailure?[$0]?.intValue == failedCommand[$0]?.intValue } &&
        (firstFailure?["query_start_ns"]?.intValue ?? 0) > 0 &&
        UInt64(firstFailure?["query_start_ns"]?.intValue ?? 0) <= externalQueryEntry &&
        externalQueryEntry <= externalQueryExit &&
        externalQueryExit <= UInt64(firstFailure?["query_end_ns"]?.intValue ?? 0) &&
        (firstFailure?["query_end_ns"]?.intValue ?? 0) <= (firstFailure?["main_entry_ns"]?.intValue ?? 0) &&
        UInt64(firstFailure?["main_entry_ns"]?.intValue ?? 0) <= externalFinalEntry &&
        externalFinalEntry <= externalFinalExit && externalFinalExit <= UInt64(firstFailure?["gate_ns"]?.intValue ?? 0),
        "dispatch_failure_actual_producer_exact_schema_and_reason_"+failureCode)
    require(NG2Fake.paths().isEmpty && report(failedMove)["inputs"]?.intValue == 0,
        "dispatch_failure_actual_producer_sends_no_direction_"+failureCode)
    // Restore public authority solely to let an explicit cancellation drain.
    NG2Fake.lock.lock(); NG2Fake.frontPID = 42; NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
    RemoteSession.shared.paused = false; LockStateMonitor.monitor.isLocked = false
    NG2RuntimeTestHooks.beforeMainAuthority = nil
    cancelDrain(failedMove)
    let saved = call("necro_native_results", failedMove)
    require(saved.1 == nil && sameDispatchFailure(firstFailure, report(failedMove)["dispatch_failure"]?.objectValue) &&
        sameDispatchFailure(firstFailure, saved.0?["report"]?.objectValue?["dispatch_failure"]?.objectValue),
        "dispatch_failure_first_record_survives_drain_and_results_"+failureCode)
    fixtureFailureSnapshot = nil
}

// Competing records use the real production storage function. Only setup is
// HOST_TEST: the actual command comes from the public reserved-MOVE event.
NG2Fake.reset(.walk)
let competingDispatch = identity()
diagnoseFixture(competingDispatch)
NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
alignInitialFixtureMove(competingDispatch)
var competingCommand: [String: JSONValue]?
var competingTicket = NG2Command()
var immutableDispatch: [String: JSONValue]?
NG2RuntimeTestHooks.scheduleTicket = { id, callback in
    let commands = (report(competingDispatch)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let command = commands.first(where: { $0["id"]?.intValue == Int(id) && $0["kind"]?.intValue == 4 }) else { return false }
    NG2Fake.holdTicket(id, callback)
    competingTicket.id = id; competingTicket.kind = 4
    competingTicket.not_before_ns = UInt64(command["not_before_ns"]!.intValue!)
    competingTicket.deadline_ns = UInt64(command["deadline_ns"]!.intValue!)
    // Keep these generation-only setup operations inside this exact control
    // callback, so a timer cannot commit an unrelated old frame between them.
    let originalDispatchGeneration = runtime.testFailureGeneration(competingDispatch)!
    let nextDispatchGeneration = runtime.testFailureGeneration(competingDispatch, advance: true)!
    let competingAt = competingTicket.not_before_ns-1
    func submit(_ ticket: NG2Command, generation: UInt64, code: String) {
        runtime.testRecordDispatchFailure(competingDispatch, generation: generation, command: ticket,
            start: competingAt-2, end: competingAt-1, entry: competingAt, now: competingAt, code: code)
    }
    submit(competingTicket, generation: originalDispatchGeneration, code: "too_late")
    require(diagnosticIsNull(report(competingDispatch)["dispatch_failure"]), "dispatch_failure_stale_generation_does_not_publish")
    var staleDispatchTicket = competingTicket; staleDispatchTicket.id += 1
    submit(staleDispatchTicket, generation: nextDispatchGeneration, code: "too_late")
    require(diagnosticIsNull(report(competingDispatch)["dispatch_failure"]), "dispatch_failure_stale_command_does_not_publish")
    submit(competingTicket, generation: nextDispatchGeneration, code: "too_early")
    immutableDispatch = report(competingDispatch)["dispatch_failure"]?.objectValue
    require(immutableDispatch?["code"]?.stringValue == "too_early", "dispatch_failure_first_record_public_storage")
    submit(competingTicket, generation: nextDispatchGeneration, code: "too_late")
    require(sameDispatchFailure(immutableDispatch, report(competingDispatch)["dispatch_failure"]?.objectValue),
        "dispatch_failure_first_record_is_immutable")
    competingCommand = command
    return true
}
require(call("necro_native_start", competingDispatch).1 == nil, "dispatch_competing_record_start")
pump("dispatch_competing_actual_MOVE_reserved", timeout: 12) { competingCommand != nil }
require(runtime.hasLease && report(competingDispatch)["main_ticket_outstanding"]?.boolValue == true && NG2Fake.paths().isEmpty,
    "dispatch_generation_revocation_retains_queued_callback_lease")
_ = call("necro_native_cancel", competingDispatch)
NG2Fake.releaseTicket(competingTicket.id)
pump("dispatch_competing_callback_drained") { drained(competingDispatch) }
let competingResults = call("necro_native_results", competingDispatch)
require(competingResults.1 == nil && sameDispatchFailure(immutableDispatch,
    competingResults.0?["report"]?.objectValue?["dispatch_failure"]?.objectValue),
    "dispatch_failure_immutable_first_record_survives_public_results")
fixtureFailureSnapshot = nil



// TEST051 PUBLIC FIXTURES BEGIN.
var test051CompletedRunID: String?
func pagedCall(_ id: String, mode: JSONValue = .string("manifest"),
               extra: [String: JSONValue] = [:], owner: String = "fixture-owner") -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "_necro_owner": .string(owner), "mode": mode]
    for (key, value) in extra { params[key] = value }
    return runtime.handle(method: "necro_native_results", params: params)
}
func publicExportFixture(_ noisyRows: Int = 0) -> String {
    NG2Fake.reset(.reply)
    var rgba = Data(count: 896*414*4)
    let length = rgba.count
    rgba.withUnsafeMutableBytes { raw in
        let bytes = raw.bindMemory(to: UInt8.self)
        ng2_test_pause(bytes.baseAddress, length)
        // Keep the complete PAUSE template (y104..132) intact. Noise below it
        // changes only the encoded payload size, not control classification.
        var random: UInt32 = 0x12345678
        if noisyRows > 0 {
            for y in 200..<min(414, 200+noisyRows) {
                for x in 0..<896 {
                    let at = (y*896+x)*4
                    for channel in 0..<3 {
                        random ^= random << 13; random ^= random >> 17; random ^= random << 5
                        bytes[at+channel] = UInt8(truncatingIfNeeded: random)
                    }
                }
            }
        }
    }
    let png = NG2Raster.png(rgba)!
    NG2Fake.lock.lock(); NG2Fake.replyData = png; NG2Fake.replyError = nil; NG2Fake.lock.unlock()
    let id = identity()
    NG2RuntimeTestHooks.scheduleTicket = { _, callback in
        _ = call("necro_native_cancel", id); callback(); return true
    }
    require(call("necro_native_start", id).1 == nil, "paged_fixture_public_start")
    pump("paged_fixture_public_capture_and_drain") { drained(id) }
    NG2RuntimeTestHooks.scheduleTicket = nil
    require(NG2Fake.countTouches() == 0 && (report(id)["retained_image_count"]?.intValue ?? 0) > 0,
        "paged_fixture_real_committed_image_without_input")
    return id
}
func testContinuousRevalidationCallbacksPublic() {
    for staleFirst in [true, false] {
        NG2Fake.reset(.walk)
        NG2Fake.lock.lock()
        // The same known world starts one tile farther from the shop, leaving
        // the third step on FLOOR after two real, confirmed UP movements.
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
        NG2RuntimeTestHooks.afterTicketReturned = { returned in
            NG2Fake.lock.lock(); NG2Fake.returnedTickets.insert(returned); NG2Fake.lock.unlock()
        }
        NG2RuntimeTestHooks.afterCaptureDrainProcessed = { run in
            NG2Fake.lock.lock(); NG2Fake.captureDrainedRuns.insert(run); NG2Fake.lock.unlock()
        }
        NG2RuntimeTestHooks.scheduleTicket = { commandID, callback in
            let current = report(id)
            let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let event = events.first(where: { $0["id"]?.intValue == Int(commandID) }),
                event["kind"]?.intValue == 4 else { return false }
            if (current["inputs"]?.intValue ?? 0) < 2 {
                NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: commandID) }
                callback(); return true
            }
            NG2Fake.holdTicket(commandID, callback)
            NG2Fake.lock.lock()
            NG2Fake.remoteVariant = 1
            if NG2Fake.heldTickets.count >= 2 { NG2Fake.captureLimit = NG2Fake.requests }
            NG2Fake.lock.unlock()
            return true
        }
        require(call("necro_native_start", id).1 == nil, "continuous_revalidation_public_start")
        pump("continuous_revalidation_two_MOVED_then_replacement", timeout: 15) {
            let current = call("necro_native_status", id, keepalive: true).0?["report"]?.objectValue ?? [:]
            NG2Fake.lock.lock(); let count = NG2Fake.heldTickets.count; NG2Fake.lock.unlock()
            return count >= 2 || current["terminal"]?.intValue == 1
        }
        let current = report(id)
        let moves = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
        require(current["inputs"]?.intValue == 2 && current["moves"]?.intValue == 2 && moves.count == 4,
            "continuous_revalidation_follows_two_actual_confirmed_moves")
        require((current["captures"]?.arrayValue ?? []).allSatisfy {
            guard let capture = $0.objectValue, let start = capture["start_ns"]?.intValue,
                let end = capture["end_ns"]?.intValue else { return false }
            return end-start == 2_000_000
        } && abs((current["beat_period_ns"]?.intValue ?? 0)-520_000_000) < 5_000_000,
            "continuous_fixture_HUD_and_capture_midpoint_share_fixed_clock")
        let old = moves[2], replacement = moves[3]
        let oldID = UInt64(old["id"]!.intValue!), newID = UInt64(replacement["id"]!.intValue!)
        require(old["outcome"]?.intValue == 3 && old["begin_ns"]?.intValue == 0,
            "continuous_revalidation_old_reservation_definitely_unsent")
        require(["target_ns", "not_before_ns", "deadline_ns", "ordinal", "direction", "x", "y"].allSatisfy {
            old[$0] == replacement[$0]
        } && old["source_capture_id"] != replacement["source_capture_id"],
            "continuous_revalidation_same_step_and_original_window")
        let changes = (current["scene_changes"]?.arrayValue ?? []).compactMap { $0.objectValue }
        let details = (current["scene_change_details"]?.arrayValue ?? []).compactMap { $0.objectValue }
        require(changes.count == 1 && changes[0]["command_id"]?.intValue == Int(oldID) &&
            changes[0]["deadline_ns"] == old["deadline_ns"] && changes[0]["replan_allowed"]?.boolValue == true,
            "continuous_revalidation_current_ticket_deadline_diagnostic")
        require(details.count == 1 && details[0]["command_id"]?.intValue == Int(oldID) &&
            details[0]["validation"]?.intValue == 2 && details[0]["continuous_count"]?.intValue == 1 &&
            details[0]["chain_count"]?.intValue == 1 &&
            details[0]["cells"]?.arrayValue?.count == 1 && details[0]["omitted_cells"]?.intValue == 0,
            "continuous_revalidation_actual_detail_producer")
        require(pagedCall(id).1 != nil, "continuous_live_callbacks_deny_manifest")
        func releaseOld() {
            var finalEntries = 0, queries = 0
            let touches = NG2Fake.countTouches()
            NG2RuntimeTestHooks.beforeMainAuthority = { finalEntries += 1 }
            NG2Fake.lock.lock(); NG2Fake.frontPID = 0; NG2Fake.beforeForegroundQuery = { queries += 1 }; NG2Fake.lock.unlock()
            NG2Fake.releaseTicket(oldID)
            pump("continuous_stale_callback_actually_returned") {
                NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }
                return NG2Fake.returnedTickets.contains(oldID)
            }
            require(finalEntries == 0 && queries == 0 && NG2Fake.countTouches() == touches,
                "continuous_old_command_skips_authority_and_touches")
            require(report(id)["dispatch_failure"] == .null, "continuous_old_command_does_not_publish_failure")
            NG2RuntimeTestHooks.beforeMainAuthority = nil
            NG2Fake.lock.lock(); NG2Fake.frontPID = 42; NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
        }
        if staleFirst {
            releaseOld()
            let after = report(id)
            require(after["current_command_id"]?.intValue == Int(newID) && after["input_state"]?.intValue == 1 &&
                after["main_ticket_outstanding"]?.boolValue == true && !drained(id) && NG2Fake.paths().count == 2,
                "continuous_old_return_keeps_public_replacement_reservation")
        }
        NG2RuntimeTestHooks.beforeMainAuthority = {
            admitFirstFixtureMove(id, expectedID: newID) { _ in
                NG2Fake.lock.lock(); NG2Fake.walkGoodsEnabled = true; NG2Fake.lock.unlock()
            }
        }
        NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        NG2Fake.releaseTicket(newID)
        if staleFirst {
            pump("continuous_replacement_callback_actually_returned") {
                NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }
                return NG2Fake.returnedTickets.contains(newID)
            }
            // The public C reservation alone cannot expose Swift callback
            // ownership. Its actual callback must retain authority to send B.
            require(report(id)["inputs"]?.intValue == 3 && NG2Fake.paths().count == 3,
                "continuous_old_return_keeps_replacement_ownership")
        }
        pump("continuous_replacement_third_input_and_terminal", timeout: 10) {
            _ = call("necro_native_status", id, keepalive: true)
            return report(id)["terminal"]?.intValue == 1
        }
        let terminal = report(id)
        let finalMoves = (terminal["events"]?.arrayValue ?? []).compactMap { $0.objectValue }.filter { $0["kind"]?.intValue == 4 }
        let sent = finalMoves.first { $0["id"]?.intValue == Int(newID) }!
        require(terminal["inputs"]?.intValue == 3 && NG2Fake.paths().count == 3 &&
            (sent["begin_ns"]?.intValue ?? 0) >= old["not_before_ns"]!.intValue! &&
            (sent["begin_ns"]?.intValue ?? Int.max) <= old["deadline_ns"]!.intValue!,
            "continuous_replacement_sends_at_most_once_in_original_window")
        if !staleFirst {
            pump("continuous_capture_worker_returned_before_stale_callback") {
                NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }
                return NG2Fake.captureDrainedRuns.contains(id)
            }
            require(!drained(id) && runtime.hasLease && pagedCall(id).1 != nil &&
                call("necro_native_start", identity()).1 != nil,
                "continuous_stale_callback_retains_lease_and_blocks_manifest")
            releaseOld()
        }
        pump("continuous_all_actual_callbacks_drained") { drained(id) }
        require(report(id)["paused"]?.intValue == 1 && report(id)["cancel_requested"]?.boolValue == false &&
            NG2Fake.paths().count == 3 && pagedCall(id).1 == nil,
            "continuous_safe_terminal_export_after_every_callback_returns")
        test051CompletedRunID = id
        fixtureFailureSnapshot = nil
    }
}
func testPagedResultsPublic() {
    // Start from the successful continuous fixture, whose cancellation reason
    // is still zero. Public cancel advances this terminal run's generation.
    let generationRun = test051CompletedRunID!
    require(report(generationRun)["cancel_requested"]?.boolValue == false,
        "paged_generation_fixture_completed_without_prior_cancel")
    let oldGenerationManifest = pagedCall(generationRun).0!
    let oldGenerationImage = oldGenerationManifest["images"]!.arrayValue!.first!.objectValue!
    let oldGenerationChunk: [String: JSONValue] = ["export_id": oldGenerationManifest["export_id"]!,
        "capture_id": oldGenerationImage["capture_id"]!, "offset": .int(0)]
    var freshGenerationManifest: [String: JSONValue]?
    NG2RuntimeExportTestHooks.beforeExportReply = {
        NG2RuntimeExportTestHooks.beforeExportReply = nil
        require(call("necro_native_cancel", generationRun).1 == nil, "paged_generation_public_terminal_cancel")
        freshGenerationManifest = pagedCall(generationRun).0
        require(freshGenerationManifest?["export_id"] != oldGenerationManifest["export_id"],
            "paged_generation_nested_manifest_has_fresh_identity")
    }
    require(pagedCall(generationRun, mode: .string("chunk"), extra: oldGenerationChunk).1 != nil,
        "paged_old_generation_reply_is_rejected")
    let freshGenerationImage = freshGenerationManifest!["images"]!.arrayValue!.first!.objectValue!
    let freshGenerationChunk: [String: JSONValue] = ["export_id": freshGenerationManifest!["export_id"]!,
        "capture_id": freshGenerationImage["capture_id"]!, "offset": .int(0)]
    require(pagedCall(generationRun, mode: .string("chunk"), extra: freshGenerationChunk).1 == nil &&
        pagedCall(generationRun).0 == freshGenerationManifest,
        "paged_late_old_generation_reply_preserves_new_export_cache")
    testPagedResultsManifestPublicBaseline()
    let id = publicExportFixture(50)
    let first = pagedCall(id)
    require(first.1 == nil, "paged_manifest_actual_producer_succeeds")
    let manifest = first.0!
    require(manifest["result_mode"]?.stringValue == "manifest" &&
        manifest["run_id"]?.stringValue == id && manifest["export_id"]?.stringValue?.count == 32 &&
        manifest["chunk_bytes"]?.intValue == 65_536,
        "paged_manifest_closed_identity_and_fixed_chunk_size")
    let imageEntries = (manifest["images"]?.arrayValue ?? []).compactMap { $0.objectValue }
    require(!imageEntries.isEmpty && imageEntries.count <= 20 &&
        imageEntries.allSatisfy { $0["data_base64"] == nil && ($0["byte_length"]?.intValue ?? 0) > 0 &&
            ($0["byte_length"]?.intValue ?? Int.max) <= 512*1024 },
        "paged_manifest_metadata_only_and_per_image_limit")
    let total = imageEntries.reduce(0) { $0+($1["byte_length"]?.intValue ?? 0) }
    require(manifest["total_bytes"]?.intValue == total && total <= 4*1024*1024 &&
        manifest["exported_images"]?.intValue == imageEntries.count,
        "paged_manifest_total_cache_budget")
    require(pagedCall(id).0 == manifest, "paged_cached_manifest_is_immutable_including_report")
    let legacy = call("necro_native_results", id)
    require(legacy.1 == nil && legacy.0?["result_mode"] == nil &&
        legacy.0?["images"]?.arrayValue?.count == imageEntries.count,
        "paged_cache_preserves_default_legacy_response")
    let exportID = manifest["export_id"]!.stringValue!
    for entry in imageEntries {
        let captureID = entry["capture_id"]!.intValue!, length = entry["byte_length"]!.intValue!
        require(length > 65_536, "paged_fixture_has_real_multiple_chunk_PNG")
        var all = Data(), offset = 0
        while offset < length {
            let params: [String: JSONValue] = ["export_id": .string(exportID), "capture_id": .int(captureID), "offset": .int(offset)]
            let reply = pagedCall(id, mode: .string("chunk"), extra: params)
            require(reply.1 == nil, "paged_chunk_actual_producer_succeeds")
            let chunk = reply.0!
            require(Set(chunk.keys) == Set(["run_id", "result_mode", "export_id", "capture_id", "offset", "byte_length", "data_base64", "sha256", "chunk_bytes"]) &&
                chunk["run_id"]?.stringValue == id && chunk["result_mode"]?.stringValue == "chunk" &&
                chunk["export_id"]?.stringValue == exportID && chunk["capture_id"]?.intValue == captureID &&
                chunk["offset"]?.intValue == offset && chunk["byte_length"]?.intValue == length && chunk["sha256"] == entry["sha256"],
                "paged_chunk_identity_offset_and_digest_bound")
            let bytes = Data(base64Encoded: chunk["data_base64"]!.stringValue!)!
            require(bytes.count == min(65_536, length-offset) && chunk["chunk_bytes"]?.intValue == bytes.count,
                "paged_chunk_exact_boundary_or_final_remainder")
            require(pagedCall(id, mode: .string("chunk"), extra: params).0 == chunk,
                "paged_same_offset_retry_returns_identical_immutable_bytes")
            all.append(bytes); offset += bytes.count
        }
        let original = (legacy.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["capture_id"]?.intValue == captureID }!
        require(all == Data(base64Encoded: original["data_base64"]!.stringValue!),
            "paged_reassembled_bytes_match_legacy_real_PNG")
        require(all.count == length && all.starts(with: [137,80,78,71,13,10,26,10]) &&
            entry["pixel_width"]?.intValue == 896 && entry["pixel_height"]?.intValue == 414,
            "paged_reassembled_PNG_length_and_dimensions")
    }
    let entry = imageEntries[0], captureID = entry["capture_id"]!.intValue!, length = entry["byte_length"]!.intValue!
    let valid: [String: JSONValue] = ["export_id": .string(exportID), "capture_id": .int(captureID), "offset": .int(0)]
    for (key, bad) in [("offset", JSONValue.int(-1)), ("offset", .int(length)), ("offset", .double(0)),
        ("offset", .bool(false)), ("capture_id", .double(Double(captureID))), ("capture_id", .bool(true)),
        ("capture_id", .int(0)), ("capture_id", .int(999_999)), ("export_id", .string(String(repeating: "f", count: 32))),
        ("export_id", .string(exportID.uppercased())), ("unexpected", .int(0))] {
        var params = valid; params[key] = bad
        // An all-numeric random id uppercases to itself; use guaranteed
        // noncanonical letters rather than assuming UUID happens to have one.
        if key == "export_id", bad == .string(exportID.uppercased()), exportID.uppercased() == exportID { continue }
        require(pagedCall(id, mode: .string("chunk"), extra: params).1 != nil,
            "paged_rejects_typed_identity_or_offset_"+key)
    }
    for badMode in [JSONValue.null, .bool(true), .int(0), .string("other")] {
        require(pagedCall(id, mode: badMode).1 != nil, "paged_rejects_unknown_or_nonstrict_mode")
    }
    require(pagedCall(id, mode: .string("chunk"), extra: ["export_id": .string(exportID)]).1 != nil &&
        pagedCall(id, extra: ["offset": .int(0)]).1 != nil,
        "paged_rejects_missing_chunk_fields_and_manifest_extras")
    require(pagedCall(id, owner: "other-owner").1 != nil &&
        pagedCall(id, mode: .string("chunk"), extra: valid, owner: "other-owner").1 != nil,
        "paged_manifest_and_chunk_authenticated_owner_bound")
    RemoteSession.shared.paused = true
    require(pagedCall(id).1 != nil && pagedCall(id, mode: .string("chunk"), extra: valid).1 != nil,
        "paged_cached_calls_recheck_paused_owner")
    RemoteSession.shared.paused = false
    require(pagedCall(id, mode: .string("chunk"), extra: valid).1 != nil,
        "paged_invalidated_cache_cannot_reuse_export_id")
    let rebuilt = pagedCall(id)
    require(rebuilt.1 == nil && rebuilt.0?["export_id"] != .string(exportID),
        "paged_owner_reactivation_builds_fresh_export_identity")

    for stage in ["before", "after"] {
        let guarded = publicExportFixture()
        if stage == "before" {
            NG2RuntimeExportTestHooks.beforeExportEncode = { RemoteSession.shared.paused = true }
        } else {
            NG2RuntimeExportTestHooks.afterExportEncode = { RemoteSession.shared.paused = true }
        }
        require(pagedCall(guarded).1 != nil, "paged_owner_revoked_"+stage+"_encoding_denies_export")
        NG2RuntimeExportTestHooks.beforeExportEncode = nil; NG2RuntimeExportTestHooks.afterExportEncode = nil
        RemoteSession.shared.paused = false
        require(pagedCall(guarded).1 == nil, "paged_failed_build_releases_budget_and_allows_fresh_export")
    }
    let competing = publicExportFixture()
    var parallelDenied = false, newRunDenied = false
    NG2RuntimeExportTestHooks.beforeExportEncode = {
        NG2RuntimeExportTestHooks.beforeExportEncode = nil
        parallelDenied = pagedCall(competing).1 != nil
        newRunDenied = call("necro_native_start", identity()).1 != nil
    }
    require(pagedCall(competing).1 == nil && parallelDenied && newRunDenied,
        "paged_parallel_build_and_new_run_do_not_amplify_cache")

    for mode in ["manifest", "chunk"] {
        let guarded = publicExportFixture(50)
        let cached = pagedCall(guarded).0!
        let item = cached["images"]!.arrayValue!.first!.objectValue!
        let chunkParams: [String: JSONValue] = ["export_id": cached["export_id"]!, "capture_id": item["capture_id"]!, "offset": .int(0)]
        NG2RuntimeExportTestHooks.beforeExportReply = {
            NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = false; NG2Fake.lock.unlock()
        }
        require(pagedCall(guarded, mode: .string(mode), extra: mode == "chunk" ? chunkParams : [:]).1 != nil,
            "paged_cached_"+mode+"_reply_rechecks_auth_owner")
        NG2RuntimeExportTestHooks.beforeExportReply = nil
        NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.lock.unlock()
        require(pagedCall(guarded, mode: .string("chunk"), extra: chunkParams).1 != nil,
            "paged_auth_revocation_discards_cached_bytes")
    }
    for mode in ["manifest", "chunk"] {
        let guarded = publicExportFixture(50)
        let cached = pagedCall(guarded).0!
        let item = cached["images"]!.arrayValue!.first!.objectValue!
        let chunkParams: [String: JSONValue] = ["export_id": cached["export_id"]!, "capture_id": item["capture_id"]!, "offset": .int(0)]
        let newer = identity()
        var acceptedNew = false
        let previousStorage = runtime.testExportStorageObserver(guarded)!
        require(previousStorage()[0] > 0 && previousStorage().dropFirst().contains(where: { $0 > 0 }),
            "paged_storage_observer_sees_actual_raw_and_encoded_evidence")
        NG2RuntimeExportTestHooks.beforeExportReply = {
            NG2RuntimeExportTestHooks.beforeExportReply = nil
            NG2Fake.lock.lock(); NG2Fake.mode = .empty; NG2Fake.lock.unlock()
            acceptedNew = call("necro_native_start", newer).1 == nil
            require(previousStorage() == [0, 0, 0, 0, 0, 0],
                "paged_replacement_retires_previous_raw_and_encoded_storage")
        }
        require(pagedCall(guarded, mode: .string(mode), extra: mode == "chunk" ? chunkParams : [:]).1 != nil && acceptedNew,
            "paged_cached_"+mode+"_reply_rechecks_current_run")
        pump("paged_replacement_run_drained") { drained(newer) }
        require(pagedCall(guarded).1 != nil && pagedCall(guarded, mode: .string("chunk"), extra: chunkParams).1 != nil &&
            call("necro_native_results", guarded).1 == nil,
            "paged_historical_run_stays_legacy_metadata_only")
    }
    // The HOST-only seam seeds bounded clones of a real committed frame;
    // the shared production encoder/budget/hash/cache path remains public.
    // Padding happens after real PNG encoding and cannot allocate a cache
    // entry until the same production per-image/aggregate tests accept it.
    for (length, expectedCount) in [(512*1024, 8), (512*1024-1, 8), (512*1024+1, 0), (128*1024, 20)] {
        let budgeted = publicExportFixture()
        require(runtime.testSeedExportFrames(budgeted, count: 20), "paged_budget_fixture_seed_is_terminal_and_bounded")
        NG2RuntimeExportTestHooks.transformExportPNG = { png, _ in
            require(png.count < length, "paged_budget_padding_starts_with_real_PNG")
            var padded = png; padded.append(Data(repeating: 0, count: length-png.count)); return padded
        }
        let bounded = pagedCall(budgeted)
        require(bounded.1 == nil && bounded.0?["retained_images"]?.intValue == 20 &&
            bounded.0?["exported_images"]?.intValue == expectedCount &&
            bounded.0?["total_bytes"]?.intValue == expectedCount*length &&
            bounded.0?["omitted_image_count"]?.intValue == 20-expectedCount &&
            bounded.0?["omitted_capture_ids"]?.arrayValue?.count == 20-expectedCount,
            "paged_exact_per_image_aggregate_and_image_count_budget_"+String(length))
        let defaultResult = call("necro_native_results", budgeted)
        require(defaultResult.1 == nil && defaultResult.0?["exported_images"] == bounded.0?["exported_images"] &&
            defaultResult.0?["exported_capture_ids"] == bounded.0?["exported_capture_ids"] &&
            defaultResult.0?["omitted_capture_ids"] == bounded.0?["omitted_capture_ids"],
            "paged_budget_selection_and_omission_equal_legacy")
        NG2RuntimeExportTestHooks.transformExportPNG = nil
    }
    let selection = publicExportFixture()
    require(!runtime.testSeedExportFrames(selection, count: 0) && !runtime.testSeedExportFrames(selection, count: 25) &&
        runtime.testSeedExportFrames(selection, count: 24), "paged_seed_obeys_existing_20_pinned_plus_4_recent_bound")
    NG2RuntimeExportTestHooks.transformExportPNG = { png, _ in
        var padded = png; padded.append(Data(repeating: 0, count: 128*1024-png.count)); return padded
    }
    let selected = pagedCall(selection)
    require(selected.1 == nil && selected.0?["retained_images"]?.intValue == 20 &&
        selected.0?["exported_images"]?.intValue == 20 && selected.0?["omitted_image_count"]?.intValue == 4 &&
        selected.0?["omitted_capture_ids"]?.arrayValue?.count == 4 && selected.0?["total_bytes"]?.intValue == 20*128*1024,
        "paged_24_retained_frames_select_only_original_20_image_budget")
    let selectedLegacy = call("necro_native_results", selection)
    require(selectedLegacy.1 == nil && selectedLegacy.0?["exported_capture_ids"] == selected.0?["exported_capture_ids"] &&
        selectedLegacy.0?["omitted_capture_ids"] == selected.0?["omitted_capture_ids"],
        "paged_24_frame_selection_matches_existing_legacy_priority")
    NG2RuntimeExportTestHooks.transformExportPNG = nil
    let oversized = publicExportFixture(214)
    let oversizedManifest = pagedCall(oversized)
    require(oversizedManifest.1 == nil && oversizedManifest.0?["exported_images"]?.intValue == 0 &&
        oversizedManifest.0?["total_bytes"]?.intValue == 0 &&
        (oversizedManifest.0?["omitted_image_count"]?.intValue ?? 0) > 0,
        "paged_oversized_real_PNG_omitted_within_original_export_budget")
}
// TEST051 PUBLIC FIXTURES END.
testContinuousRevalidationCallbacksPublic()
testPagedResultsPublic()

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
