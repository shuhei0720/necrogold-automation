// TEST099 source/record/retention callbacks. Clock/pixels/results are procedural.
// One explicit readonly POD override pressures snapshot/pin boundaries; every
// qualification/deadline case otherwise uses the actual current C getters.
func cycle099Records(_ root: URL, _ id: String) -> [(String, [String: JSONValue])] {
    do {
        let spool = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: "fixture-owner")
        return try spool.records().map { row in
            let value = try JSONDecoder().decode([String: JSONValue].self, from: spool.recordBytes(row))
            return (row.kind, value["payload"]?.objectValue ?? [:])
        }
    } catch { require(false, "cycle099_record_bytes_recover"); return [] }
}
func cycle099Terminal(_ root: URL, _ id: String) -> [String: JSONValue] {
    var value: [String: JSONValue] = [:]
    pump("cycle099_terminal_record_durable", timeout: 30) {
        value = cycle099Records(root, id).last(where: { $0.0 == "terminal" })?.1["controller"]?.objectValue ?? [:]
        return !value.isEmpty
    }
    return value
}
let cycle099StopKeys: Set<String> = ["schema", "valid", "stage", "reason", "at_ns", "source_capture_id",
    "observed_capture_id", "anchor_capture_id", "prefix", "deadline_ns", "wait_kind", "passage_bit",
    "passage_pending", "passage_unresolved", "passage_unlocalized_gold", "x", "y", "validation",
    "motion_kind", "motion_dx", "motion_dy", "last_comparison_capture_id"]
let cycle099HandoffKeys: Set<String> = ["schema", "kind", "allowed", "reason", "qualified_ns",
    "source_capture_id", "source_prefix", "pause_capture_id", "completed_prefix"]
func cycle099Projection(_ controller: [String: JSONValue]) -> ([String: JSONValue], [String: JSONValue]) {
    let stop = controller["stop_detail"]?.objectValue ?? [:], handoff = controller["handoff"]?.objectValue ?? [:]
    require(Set(stop.keys) == cycle099StopKeys && Set(handoff.keys) == cycle099HandoffKeys &&
        stop["schema"]?.stringValue == "ngg2-stop-detail-v1" &&
        handoff["schema"]?.stringValue == "ngg2-trial-handoff-v1",
        "cycle099_terminal_has_frozen_stop_and_handoff")
    return (stop, handoff)
}
func testCycle099TerminalProjection(_ root: URL) {
    _ = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil); cycleProof(1)
    let id = identity(); cycleStart(id)
    pump("cycle099_candidate_drained", timeout: 30) { cycleDrained(id) }
    let (_, handoff) = cycle099Projection(cycle099Terminal(root, id))
    require(handoff["kind"]?.stringValue == "none" && handoff["allowed"]?.boolValue == false,
        "cycle099_candidate_cannot_mint_next_start")
    require(report(id)["stop_detail"] == nil && report(id)["handoff"] == nil,
        "cycle099_legacy_http_controller_schema_unchanged")
    publishFixtureClaim(id)
    print("PASS TEST099 frozen cycle-only stop and handoff projection")
}
func testCycle099ReadonlySupport(_ root: URL) {
    _ = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil)
    let id = identity(), before = NG2Fake.countRequests(), touches = NG2Fake.countTouches()
    let answer = cycleCall(id, "trial_support")
    let value = answer.0?["payload"]?.objectValue ?? [:]
    require(answer.1 == nil && Set(value.keys) == Set(["stop_detail_schema", "handoff_schema", "maximum_run_ids", "pin_limit"]) &&
        value["stop_detail_schema"]?.stringValue == "ngg2-stop-detail-v1" &&
        value["handoff_schema"]?.stringValue == "ngg2-trial-handoff-v1" &&
        value["maximum_run_ids"]?.intValue == 128 && value["pin_limit"]?.intValue == 24,
        "cycle099_support_is_exact_readonly_version_gate")
    let extra = cycleCall(id, "trial_support", extra: ["unexpected": .bool(true)])
    let other = cycleCall(id, "trial_support", owner: "unapproved-owner")
    require(extra.0 == nil && other.0 == nil && NG2Fake.countRequests() == before &&
        NG2Fake.countTouches() == touches && !runtime.hasLease,
        "cycle099_support_cannot_start_capture_or_bypass_owner_or_closed_params")
    print("PASS TEST099 readonly trial support before new start")
}
func testCycle099FaultProjection(_ root: URL) {
    let clock = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil); cycleProof(1)
    let id = identity()
    NG2RuntimeCycleTestHooks.beforeClassificationCommit = { _ in clock.advance(151_000_000) }
    cycleStart(id)
    pump("cycle099_deadline_fault_drained", timeout: 30) { cycleDrained(id) }
    let rows = cycle099Records(root, id)
    let final = cycle099Terminal(root, id), (stop, handoff) = cycle099Projection(final)
    let checkpoint = rows.last(where: { $0.0 == "checkpoint" })?.1["controller"]?.objectValue ?? [:]
    require(stop["valid"]?.boolValue == true && (stop["at_ns"]?.intValue ?? 0) > 0 &&
        stop["reason"]?.intValue == Int(NG2_REASON_LATE) && checkpoint["stop_detail"] == final["stop_detail"] &&
        handoff["allowed"]?.boolValue == false && NG2Fake.paths().isEmpty &&
        NG2Fake.taps().allSatisfy { $0.x == 390 && $0.y == 448 },
        "cycle099_first_failure_survives_pause_and_cannot_mint_handoff")
    let ids = Set(["source_capture_id", "observed_capture_id", "anchor_capture_id", "last_comparison_capture_id"]
        .compactMap { stop[$0]?.intValue }.filter { $0 > 0 })
    publishFixtureClaim(id, requiredCaptureIDs: ids)
    print("PASS TEST099 actual deadline stop remains frozen through cleanup")
}
func testCycle099PinAndSnapshot(_ root: URL) {
    _ = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil); cycleProof(1)
    let id = identity(), gate = NSLock(), checkpoint = DispatchSemaphore(value: 0)
    var entered = false, released = false, anchor: UInt64 = 0, observed: UInt64 = 0
    NG2RuntimeCycleTestHooks.beforeCheckpointWrite = { _ in
        gate.lock(); entered = true; gate.unlock(); checkpoint.wait()
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, _, _, prefix, _ in
        gate.lock()
        if anchor == 0 && entered { anchor = capture }
        if anchor != 0 && observed == 0 && capture >= anchor + 3 { observed = capture }
        let source = anchor, comparison = observed
        let release = entered && !released && comparison != 0 && capture >= comparison + 6
        if release { released = true }
        gate.unlock()
        if source != 0 {
            var value = NG2ControllerStopDetail()
            value.abi_version = 1; value.struct_size = UInt32(MemoryLayout<NG2ControllerStopDetail>.size)
            value.stage = 2; value.wait_kind = 4; value.passage_bit = 5
            value.source_capture_id = source; value.anchor_capture_id = source
            value.prefix = prefix; value.deadline_ns = NG2Runtime.now() + 1_000_000_000
            if comparison != 0 {
                value.valid = 1; value.reason = Int32(NG2_REASON_NO_PATH); value.at_ns = 1_234_567
                value.observed_capture_id = comparison; value.last_comparison_capture_id = comparison
            }
            ng2_fixture099_stop_override(1, &value)
        }
        if release { checkpoint.signal() }
    }
    cycleStart(id)
    pump("cycle099_pin_fixture_checkpoint_entered", timeout: 20) { gate.lock(); defer { gate.unlock() }; return entered }
    pump("cycle099_pin_fixture_retired_recent_frames", timeout: 30) { gate.lock(); defer { gate.unlock() }; return released }
    pump("cycle099_pin_fixture_actual_drain", timeout: 30) { cycleDrained(id) }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    let rows = cycle099Records(root, id)
    let final = cycle099Terminal(root, id), (stop, _) = cycle099Projection(final)
    let before = rows.last(where: { $0.0 == "checkpoint" })?.1["controller"]?.objectValue?["stop_detail"]?.objectValue ?? [:]
    gate.lock(); let source = anchor, comparison = observed; gate.unlock()
    let conditions: [String: JSONValue] = ["source_nonzero": .bool(source > 0),
        "comparison_after_source": .bool(comparison > source),
        "terminal_anchor_matches_source": .bool(stop["anchor_capture_id"]?.intValue == Int(source)),
        "terminal_observed_matches_comparison": .bool(stop["observed_capture_id"]?.intValue == Int(comparison)),
        "terminal_at_matches_override": .bool(stop["at_ns"]?.intValue == 1_234_567),
        "checkpoint_valid_false": .bool(before["valid"]?.boolValue == false),
        "checkpoint_observed_zero": .bool(before["observed_capture_id"]?.intValue == 0)]
    let checkpoints: [JSONValue] = rows.filter { $0.0 == "checkpoint" }.map { row in
        .object(["job_id": row.1["cycle"]?.objectValue?["job_id"] ?? .null,
            "stop_detail": row.1["controller"]?.objectValue?["stop_detail"] ?? .null])
    }
    let diagnostic: [String: JSONValue] = ["source_capture_id": .int(Int(source)),
        "comparison_capture_id": .int(Int(comparison)), "conditions": .object(conditions),
        "checkpoints": .array(checkpoints), "terminal_stop_detail": .object(stop)]
    if let bytes = try? JSONEncoder().encode(diagnostic), let line = String(data: bytes, encoding: .utf8) {
        print("DIAGNOSTIC cycle099_pin_snapshot " + line)
    }
    require(conditions.values.allSatisfy { $0.boolValue == true },
        "cycle099_writer_owns_old_immutable_snapshot_not_later_getter")
    publishFixtureClaim(id, requiredCaptureIDs: [Int(source), Int(comparison)])
    ng2_fixture099_stop_override(0, nil)
    print("PASS TEST099 readonly POD live anchor and first failure survive recent eviction")
}
func testCycle099NegativeHandoff(_ root: URL) {
    let clock = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil)
    let id = identity(), gate = NSLock()
    var restartCount = 0, advanced: Set<Int> = []
    let images = [cycleSearchPixels(worldX: 0, variant: 0, goods: 1),
                  cycleSearchPixels(worldX: 36, variant: 1, goods: 1)]
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let index = restartCount % 2; gate.unlock(); return images[index]
    }
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); restartCount += 1; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        result = cycle095Negative(scene, result.started_ns, NG2Runtime.now())
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id), job = stateInt(cycleCompanion(id), "job_id")
        gate.lock()
        let advance = job > 0 && !advanced.contains(job) && state["pending"]?.boolValue == false &&
            (state["durable_ns"]?.intValue ?? 0) > 0 && (state["pause_capture_id"]?.intValue ?? 0) > 0
        if advance { advanced.insert(job) }
        gate.unlock(); if advance { clock.advance(220_000_000) }
    }
    cycleStart(id); pump("cycle099_negative_four_drained", timeout: 40) { cycleDrained(id) }
    let (_, handoff) = cycle099Projection(cycle099Terminal(root, id))
    require(handoff["allowed"]?.boolValue == true && handoff["kind"]?.stringValue == "negative_limit" &&
        cycleCompanion(id)["completed_shops"]?.intValue == 4 &&
        NG2Fake.taps().filter { $0.x == 144 && $0.y == 448 }.count == 3 && NG2Fake.paths().isEmpty,
        "cycle099_actual_four_negative_shops_only_mint_clean_limit")
    let next = identity()
    let denied = runtime.handle(method: "necro_native_start", params: ["run_id": .string(next),
        "profile": .string("normal-1-1-cycle-v1"), "_necro_owner": .string("fixture-owner")])
    require(denied.0 == nil, "cycle099_next_start_blocked_before_publication_ack")
    let required = Set([handoff["source_capture_id"]?.intValue, handoff["pause_capture_id"]?.intValue].compactMap { $0 })
    publishFixtureClaim(id, requiredCaptureIDs: required)
    NG2RuntimeTestHooks.beforeControlTick = nil; cycleProof(1)
    cycleStart(next); pump("cycle099_fresh_next_run_candidate_drained", timeout: 30) { cycleDrained(next) }
    require(cycleCompanion(next)["outcome"]?.stringValue == "candidate" && NG2Fake.paths().isEmpty &&
        cycle099Terminal(root, next)["moves"]?.intValue == 0,
        "cycle099_next_run_fresh_pause_resume_reclassifies_without_old_move_authority")
    let (_, nextHandoff) = cycle099Projection(cycle099Terminal(root, next))
    require(nextHandoff["allowed"]?.boolValue == false, "cycle099_new_candidate_never_continues")
    publishFixtureClaim(next)
    print("PASS TEST099 clean negative limit publishes before a fresh candidate run")
}
func stateInt(_ value: [String: JSONValue], _ key: String) -> Int { value[key]?.intValue ?? 0 }
func testCycle099ClearSearchHandoff(_ root: URL) {
    let clock = resetCycleFixture(root); ng2_fixture099_stop_override(0, nil)
    let id = identity(), gate = NSLock(); var restarts = 0
    let images = [cycleSearchPixels(worldX: 0, variant: 0), cycleSearchPixels(worldX: 36, variant: 1)]
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); restarts += 1; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let index = restarts % 2; gate.unlock(); return images[index]
    }
    NG2RuntimeTestHooks.beforeControlTick = { clock.advance(20_000_000) }
    cycleStart(id); pump("cycle099_clear_search_limit_drained", timeout: 45) { cycleDrained(id) }
    let (_, handoff) = cycle099Projection(cycle099Terminal(root, id))
    require(handoff["allowed"]?.boolValue == true && handoff["kind"]?.stringValue == "clear_search_limit" &&
        cycleCompanion(id)["job_id"]?.intValue == 0 && report(id)["restarts"]?.intValue == 12 &&
        report(id)["inputs"]?.intValue == 0 && NG2Fake.paths().isEmpty,
        "cycle099_actual_clear_search_limit_is_not_unknown_goods_or_midroute_limit")
    let required = Set([handoff["source_capture_id"]?.intValue, handoff["pause_capture_id"]?.intValue].compactMap { $0 })
    publishFixtureClaim(id, requiredCaptureIDs: required)
    print("PASS TEST099 certified clear search limit has independent readonly handoff")
}

// TEST099 ENTRYPOINTS BEGIN.
let cycle099Root = FileManager.default.temporaryDirectory.appendingPathComponent("runtime099-" + UUID().uuidString)
try FileManager.default.createDirectory(at: cycle099Root, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: cycle099Root) }
NG2RuntimeCycleTestHooks.spoolRoot = cycle099Root
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
pump("cycle099_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
// TEST099 CASE CALLS BEGIN.
testCycle099TerminalProjection(cycle099Root)
testCycle099ReadonlySupport(cycle099Root)
testCycle099FaultProjection(cycle099Root)
testCycle099PinAndSnapshot(cycle099Root)
testCycle099NegativeHandoff(cycle099Root)
testCycle099ClearSearchHandoff(cycle099Root)
testStopEvidenceRetentionPublic()
print("PASS TEST099 six cycle diagnostic/handoff callbacks and legacy20 evidence retention; procedural clock/pixels/results")
