// TEST095 control integration uses procedural pixels and an explicit result
// override. The checker separately calls the actual Ring mode2 pixel producer;
// these callbacks prove lifecycle/wire binding, not image or phone accuracy.
func cycle095Slot(_ cx: Int32, _ sy: Int32, _ index: Int32) -> NG2RingSlot {
    var slot = NG2RingSlot()
    slot.cx = cx; slot.sy = sy; slot.slot = index
    slot.kind = UInt32(NG2_RING_GENERIC_NON_TARGET); slot.outcome = UInt32(NG2_RING_NON_TARGET)
    slot.icon_score = 0.1; slot.icon_upper_bound = 0.1
    slot.icon_box = (cx - 16, sy + 35, 32, 28)
    slot.non_target_icon_box = (cx - 18, sy + 24, 36, 67)
    return slot
}
func cycle095Negative(_ scene: UnsafePointer<NG2Scene>?, _ start: UInt64, _ end: UInt64) -> NG2RingResult {
    var value = NG2RingResult()
    ng2_fixture_cycle_result(scene, start, end, 3, &value)
    value.reason = UInt32(NG2_RING_EXPOSED_TARGET_ABSENT)
    value.certificate.policy_version = 2
    if scene == nil { value.certificate.actual_gold_cells = 1 }
    value.certificate.strip_box = (246, 114, 180, 67)
    value.rows.0.reason = UInt32(NG2_RING_EXPOSED_TARGET_ABSENT)
    value.rows.0.slots = (cycle095Slot(300, 90, 0), cycle095Slot(336, 90, 1), cycle095Slot(372, 90, 2))
    value.partial_count = 2
    value.partial.0 = cycle095Slot(264, 90, 0)
    value.partial.1 = cycle095Slot(408, 90, 0)
    value.certificate.item_boxes = (value.rows.0.slots.0.non_target_icon_box,
        value.rows.0.slots.1.non_target_icon_box, value.rows.0.slots.2.non_target_icon_box)
    value.certificate.name_boxes = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    return value
}
func cycle095GenericWire(_ value: [String: JSONValue]) -> Bool {
    let row = value["rows"]?.arrayValue?.first?.objectValue
    let slots = (row?["slots"]?.arrayValue ?? []) + (value["partial"]?.arrayValue ?? [])
    return value["policy_version"]?.stringValue == "exposed_cursering_target_only_v2" && slots.count == 5 &&
        slots.allSatisfy { slot in
            let item = slot.objectValue
            return item?["kind"]?.stringValue == "generic_non_target" && item?["non_target_id"]?.intValue == 0 &&
                item?["ignored_container_id"]?.intValue == 0 && item?["outcome"]?.stringValue == "non_target"
        }
}
func testCycle095Wire() {
    var binary = cycle095Negative(nil, 10, 20)
    do {
        let value = try NG2CycleWire.assessment(binary, mode: Int32(NG2_RING_MODE_TARGET_ONLY))
        require(cycle095GenericWire(value), "cycle095_generic_wire_and_policy2")
        var legacy = NG2RingResult()
        ng2_fixture_cycle_result(nil, 10, 20, 3, &legacy)
        let old0 = try NG2CycleWire.assessment(legacy, mode: 0)
        let old1 = try NG2CycleWire.assessment(legacy, mode: 1)
        require(try NG2CycleWire.canonical(old0) == NG2CycleWire.canonical(old1), "cycle095_legacy_mode0_mode1_wire_equal")
        require(old0["policy_version"]?.stringValue == String(cString: ng2_ring_policy_version()) &&
            old0["rows"]?.arrayValue?.first?.objectValue?["slots"]?.arrayValue?.first?.objectValue?["kind"]?.stringValue == "known_non_target",
            "cycle095_legacy_named_wire_and_policy1_preserved")
        var unknown = NG2RingResult()
        unknown.abi = 1; unknown.size = UInt32(MemoryLayout<NG2RingResult>.size)
        unknown.selected_row = -1; unknown.selected_partial = -1
        let partial = try NG2CycleWire.assessment(unknown, mode: Int32(NG2_RING_MODE_TARGET_ONLY))
        require(partial["policy_version"]?.stringValue == "exposed_cursering_target_only_v2",
            "cycle095_incomplete_result_retains_worker_policy2")
    } catch { require(false, "cycle095_generic_wire_and_policy2") }
    require(ng2_ring_negative_certificate(&binary) == 1, "cycle095_injected_certificate_independent_C_validator")
    print("PASS TEST095 policy2 generic wire and unchanged legacy mode0/1 projection")
}
func cycle095ObserveMode(_ gate: NSLock, _ modes: UnsafeMutablePointer<[Int32]>) {
    NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, _, _ in
        require(mode == Int32(NG2_RING_MODE_TARGET_ONLY), "cycle095_actual_classifier_uses_target_only_mode")
        gate.lock(); modes.pointee.append(mode); gate.unlock()
    }
}
func testCycle095Hold(_ root: URL, partial: Bool) {
    _ = resetCycleFixture(root); cycleProof(1)
    let id = identity(), gate = NSLock(), modes = UnsafeMutablePointer<[Int32]>.allocate(capacity: 1)
    modes.initialize(to: [])
    defer { NG2RuntimeCycleTestHooks.afterClassificationCall = nil; modes.deinitialize(count: 1); modes.deallocate() }
    cycle095ObserveMode(gate, modes)
    let image = cycleSearchPixels(worldX: 108, variant: 1, goods: partial ? 2 : 1)
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        return paused ? original : image
    }
    cycleStart(id)
    pump("cycle095_candidate_actual_drain", timeout: 30) { cycleDrained(id) }
    gate.lock(); let calls = modes.pointee; gate.unlock()
    let state = cycleCompanion(id)
    require(!calls.isEmpty && state["outcome"]?.stringValue == "candidate" && state["partial"]?.boolValue == partial &&
        NG2Fake.taps().count == 1 && NG2Fake.paths().isEmpty,
        "cycle095_candidate_and_partial_hold_without_restart")
    publishFixtureClaim(id)
    print(partial ? "PASS TEST095 partial candidate held after actual mode2 call" : "PASS TEST095 visible candidate held after actual mode2 call")
}
func testCycle095NegativeRestart(_ root: URL) {
    let clock = resetCycleFixture(root), id = identity(), gate = NSLock()
    var restarted = false, settle = false, settleNext = false, intentEntered = false, intentDurable = false
    let modes = UnsafeMutablePointer<[Int32]>.allocate(capacity: 1)
    modes.initialize(to: [])
    defer { NG2RuntimeCycleTestHooks.afterClassificationCall = nil; modes.deinitialize(count: 1); modes.deallocate() }
    cycle095ObserveMode(gate, modes)
    let first = cycleSearchPixels(worldX: 0, variant: 0, goods: 1)
    let next = cycleSearchPixels(worldX: 36, variant: 1, goods: 1)
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        gate.lock(); let changed = restarted; gate.unlock(); return changed ? next : first
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        gate.lock(); let changed = restarted; gate.unlock()
        if changed { ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), 1, &result) }
        else {
            result = cycle095Negative(scene, result.started_ns, NG2Runtime.now())
            require(ng2_ring_negative_certificate(&result) == 1, "cycle095_injected_certificate_independent_C_validator")
        }
    }
    NG2RuntimeCycleTestHooks.beforeIntentWrite = { _ in
        let state = cycleCompanion(id)
        gate.lock(); intentEntered = true
        intentDurable = (state["durable_ns"]?.intValue ?? 0) > 0 && state["outcome"]?.stringValue == "negative"
        gate.unlock()
        require(NG2Fake.taps().allSatisfy { $0.x == 390 && $0.y == 448 }, "cycle095_no_restart_before_durable_intent")
    }
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            gate.lock(); restarted = true; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let state = cycleCompanion(id)
        gate.lock()
        let advance = !settle && (state["pause_capture_id"]?.intValue ?? 0) > 0 && state["pending"]?.boolValue == false &&
            state["outcome"]?.stringValue == "negative" && (state["durable_ns"]?.intValue ?? 0) > 0
        if advance { settle = true }
        let advanceNext = !settleNext && (state["level_id"]?.intValue ?? 0) >= 2 &&
            state["pending"]?.boolValue == false && state["outcome"]?.stringValue == "candidate"
        if advanceNext { settleNext = true }
        gate.unlock()
        if advance || advanceNext { clock.advance(220_000_000) }
    }
    cycleStart(id)
    pump("cycle095_binary_negative_then_candidate_drained", timeout: 30) { cycleDrained(id) }
    gate.lock(); let observedIntent = intentEntered && intentDurable, calls = modes.pointee; gate.unlock()
    let taps = NG2Fake.taps(), state = cycleCompanion(id)
    // This counter includes both the negative shop and the held candidate.
    require(observedIntent && calls.count >= 2 && state["completed_shops"]?.intValue == 2 &&
        state["level_id"]?.intValue == 2 && state["outcome"]?.stringValue == "candidate" &&
        taps.filter { $0.x == 144 && $0.y == 448 }.count == 1 && taps.count == 3 && NG2Fake.paths().isEmpty,
        "cycle095_binary_negative_durable_intent_restart_then_candidate_hold")
    do {
        let spool = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: "fixture-owner")
        let records = try spool.records()
        let negative = try records.filter { $0.kind == "checkpoint" }.compactMap { record -> [String: JSONValue]? in
            guard record.payload["assessment_adopted"] as? Bool == true,
                  let raw = record.payload["assessment"] as? [String: Any] else { return nil }
            let assessment = try NG2CycleWire.decode(raw)
            return assessment["outcome"]?.stringValue == "negative" ? assessment : nil
        }
        require(negative.count == 1 && cycle095GenericWire(negative[0]) &&
            records.filter { $0.kind == "restart_intent" }.count == 1 &&
            records.filter { $0.kind == "restart_outcome" }.count == 1,
            "cycle095_policy2_wire_and_exact_intent_outcome_durably_saved")
    } catch { require(false, "cycle095_policy2_wire_and_exact_intent_outcome_durably_saved") }
    publishFixtureClaim(id)
    print("PASS TEST095 binary negative durable checkpoint and exact intent restart then candidate hold")
}

// TEST095 ENTRYPOINTS BEGIN.
let cycle095Root = FileManager.default.temporaryDirectory.appendingPathComponent("runtime-target-only095-" + UUID().uuidString)
try FileManager.default.createDirectory(at: cycle095Root, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: cycle095Root) }
NG2RuntimeCycleTestHooks.spoolRoot = cycle095Root
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
pump("cycle095_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
// TEST095 CASE CALLS BEGIN.
testCycle095Wire()
testCycle095NegativeRestart(cycle095Root)
testCycle095Hold(cycle095Root, partial: false)
testCycle095Hold(cycle095Root, partial: true)
print("PASS TEST095 production Runtime four target-only policy/wire/negative/candidate/partial callbacks; procedural pixels and injected lifecycle result")
