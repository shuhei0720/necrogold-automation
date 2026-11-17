// TEST113 selects the unchanged upper-shop fixture and the real public
// terminal/draining response. Pixels, clock and UI remain procedural.
func runtime113SaveStatus(_ phase: String, _ value: [String: JSONValue]) {
    guard let directory = ProcessInfo.processInfo.environment["NG2_RUNTIME113_STATUS_DIR"],
          !directory.isEmpty else {
        require(false, "test113_status_artifact_directory_required"); return
    }
    do {
        let root = URL(fileURLWithPath: directory)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true,
            attributes: [.posixPermissions: NSNumber(value: 0o700)])
        let data = try JSONEncoder().encode(value)
        try data.write(to: root.appendingPathComponent("status-" + phase + ".json"), options: .atomic)
        print("EVIDENCE TEST113 STATUS " + phase + " " + NG2CycleWire.hash(data))
    } catch { require(false, "test113_actual_public_status_artifact_saved") }
}

func testRuntime113TerminalStatus(_ root: URL) {
    runtime112Reset(root)
    let id = identity(), world = Runtime112World(id)
    let gate = NSLock(), writerRelease = DispatchSemaphore(value: 0)
    var writerParked = false
    world.install()
    // The real terminal persistence worker holds its actual file-sync lease.
    // This does not alter a status/result, controller clock, or game response.
    NG2CycleSpoolTestHooks.beforeBoundary = { boundary in
        guard boundary == "file_sync", cyclePayload(id)["terminal"]?.boolValue == true else { return true }
        gate.lock()
        let first = !writerParked
        if first { writerParked = true }
        gate.unlock()
        if first {
            require(writerRelease.wait(timeout: .now() + 30) == .success,
                "test113_actual_terminal_writer_park_is_bounded")
        }
        return true
    }
    defer { NG2CycleSpoolTestHooks.beforeBoundary = nil; writerRelease.signal() }
    runtime112Start(id)
    pump("test113_real_terminal_file_sync_lease_parked", timeout: 45) {
        gate.lock(); defer { gate.unlock() }; return writerParked
    }
    let draining = cycleCall(id)
    let during = draining.0?["payload"]?.objectValue ?? [:]
    require(draining.1 == nil && during["state"]?.stringValue == "draining" &&
        during["terminal"]?.boolValue == true && during["workers_drained"]?.boolValue == false &&
        runtime.hasLease && !cycleDrained(id),
        "test113_public_terminal_draining_is_real_pending_persistence_not_a_final_collection")
    runtime113SaveStatus("draining", draining.0 ?? [:])
    let before = NG2Fake.countTouches()
    let denied = runtime.handle(method: "necro_native_start", params: [
        "run_id": .string(identity()), "profile": .string("normal-1-1-irregular-v1"),
        "yield_after_restart": .bool(true), "_necro_owner": .string("fixture-owner")])
    require(denied.1 != nil && NG2Fake.countTouches() == before,
        "test113_draining_cannot_start_another_uuid_or_emit_ui")
    require(cycleCall(id, "manifest").1 != nil,
        "test113_draining_cannot_export_before_actual_writer_return")
    writerRelease.signal()
    pump("test113_terminal_writer_returns_before_public_stopped", timeout: 45) { cycleDrained(id) }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    let stopped = cycleCall(id), final = stopped.0?["payload"]?.objectValue ?? [:]
    require(stopped.1 == nil && final["state"]?.stringValue == "stopped" &&
        final["terminal"]?.boolValue == true && final["workers_drained"]?.boolValue == true &&
        final["input_state"]?.intValue == 0 && final["native_inflight"]?.boolValue == false &&
        final["ui_frozen"]?.boolValue == false,
        "test113_public_stopped_requires_actual_drain_and_known_input")
    runtime113SaveStatus("stopped", stopped.0 ?? [:])
    require(runtime112Handoff(root, id)["kind"]?.stringValue == "restarted_budget" &&
        runtime112Handoff(root, id)["allowed"]?.boolValue == true &&
        world.locked { world.restarts == 1 && world.pausesAfterRestart == 1 },
        "test113_normal_native_restart_and_new_floor_pause_remain_qualified")
    runtime112AssertNormalChain(root, world)
    let firstFloor = runtime112State(id)["first_floor_capture_id"]?.intValue ?? 0
    require(firstFloor > 0, "test113_original_new_floor_is_retained")
    runtime111Manifest(id, required: [firstFloor])
    publishFixtureClaim(id, requiredCaptureIDs: [firstFloor])
    runtime112PreserveSyntheticExport(root, id, label: "happy_yield")
    let next = identity(), beforeTaps = NG2Fake.taps().count, beforeMoves = NG2Fake.paths().count
    world.locked { world.activeID = next; world.stage = 2; world.candidateReady = true }
    runtime112Start(next)
    pump("test113_published_next_uuid_same_floor_fresh_resume_candidate", timeout: 30) { cycleDrained(next) }
    let taps = Array(NG2Fake.taps().dropFirst(beforeTaps)), current = report(next)
    require(taps.first == CGPoint(x: 297, y: 448) && taps.filter { $0.x == 144 }.isEmpty &&
        NG2Fake.paths().count == beforeMoves && world.locked { world.restarts == 1 } &&
        cycleCompanion(next)["candidate_latched"]?.boolValue == true,
        "test113_only_published_run_allows_fresh_same_floor_resume_and_keeps_candidate")
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let captures = (current["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let source = captures.first { $0["id"]?.intValue == events.first?["source_capture_id"]?.intValue }
    require(events.first?["kind"]?.intValue == 1 && source?["completed_prefix_start"]?.intValue == 0 &&
        source?["completed_prefix_end"]?.intValue == 0 && source?["stable"]?.boolValue == true,
        "test113_second_uuid_uses_its_own_fresh_prefix_zero_pause")
    publishFixtureClaim(next)
}

let root113 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime113-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root113, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root113) }
NG2RuntimeCycleTestHooks.spoolRoot = root113
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case113 = CommandLine.arguments.last ?? ""
pump("test113_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
switch case113 {
case "terminal_status": testRuntime113TerminalStatus(root113.appendingPathComponent("terminal"))
case "upper_entry":
    for variant in ["left", "right", "cancel"] {
        testRuntime112UpperEntry(root113.appendingPathComponent(variant),
            mirrored: variant == "right", cancelPartial: variant == "cancel")
    }
default: require(false, "test113_unknown_case_is_not_another_fixture")
}
print("PASS TEST113 CASE " + case113)
