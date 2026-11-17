// Selected TEST112 actual Runtime callbacks. These are procedural host pixels,
// a virtual clock and explicit classifier outcomes, never phone acceptance.
// The real raster, Perception, Ring call, Controller, UI, Spool and RPC paths
// execute. Legacy 110/111 helpers and assertions are compiled without edits.
#if NG2_RESTART_YIELD_TEST112_GREEN
func runtime112State(_ id: String) -> [String: JSONValue] { runtime.testRestartYieldState(id) ?? [:] }
func runtime112Handoff(_ root: URL, _ id: String) -> [String: JSONValue] {
    ir110Record(root, id, "terminal")?["controller"]?.objectValue?["handoff"]?.objectValue ?? [:]
}
func runtime112RecordAdmission(_ id: String, _ state: [String: JSONValue], label: String) {
    let source = state["capture_start_ns"]?.intValue ?? 0, worker = state["worker_started_ns"]?.intValue ?? 0
    let deadline = state["deadline_ns"]?.intValue ?? 0
    require(source > 0 && worker >= source && worker <= deadline && worker-source <= 150_000_000 &&
        deadline <= source+150_000_000 && deadline <= worker+100_000_000,
        "test112_actual_admission_source_age_within150_worker_deadline100")
    var body = state.filter { ["job_id", "capture_id", "capture_start_ns", "worker_started_ns", "deadline_ns", "prefix"].contains($0.key) }
    body["run_id"] = .string(id); body["label"] = .string(label); body["source_age_at_worker_admission_ns"] = .int(worker-source)
    if let bytes = try? JSONEncoder().encode(body), let text = String(data: bytes, encoding: .utf8) { print("EVIDENCE TEST112 ADMISSION " + text) }
    else { require(false, "test112_actual_admission_evidence_encodes") }
}
// Optional CI artifact of these synthetic runs only. It copies the actual
// durable Spool after publication; it does not synthesize native records or
// pretend the explicit fixture client receipt proves real ZIP bytes.
func runtime112PreserveSyntheticExport(_ root: URL, _ id: String, label: String) {
    let environment = ProcessInfo.processInfo.environment
    guard let output = environment["NG2_RUNTIME112_EVIDENCE"], !output.isEmpty,
          let selectedCase = environment["NG2_RUNTIME112_CASE"], !selectedCase.isEmpty else { return }
    let destination = URL(fileURLWithPath: output).appendingPathComponent(selectedCase)
        .appendingPathComponent(label).appendingPathComponent(id)
    if label == "happy_yield" || label == "upper_left_real_ring" {
        let beforeCommit = ir110Record(root, id, "restart_outcome")?["controller"]?.objectValue ?? [:]
        let terminal = ir110Record(root, id, "terminal")?["controller"]?.objectValue ?? [:]
        require(beforeCommit["x"]?.intValue != nil && beforeCommit["y"]?.intValue != nil &&
            (beforeCommit["x"]?.intValue != 0 || beforeCommit["y"]?.intValue != 0) &&
            terminal["x"]?.intValue == 0 && terminal["y"]?.intValue == 0,
            "test112_actual_outcome_precommit_coordinates_nonzero_then_terminal_new_origin_zero")
    }
    do {
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true,
            attributes: [.posixPermissions: NSNumber(value: 0o700)])
        let source = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
        try FileManager.default.copyItem(at: source, to: destination.appendingPathComponent("spool"))
        guard let manifestPayload = cycleCall(id, "manifest").0?["payload"]?.objectValue,
              let manifestText = manifestPayload["manifest_json"]?.stringValue,
              let manifestBytes = manifestText.data(using: .utf8) else {
            require(false, "test112_synthetic_export_frozen_rpc_manifest_available"); return
        }
        try manifestBytes.write(to: destination.appendingPathComponent("manifest.json"), options: .atomic)
        try JSONEncoder().encode(cyclePayload(id)).write(to: destination.appendingPathComponent("runtime-status.json"), options: .atomic)
        try JSONEncoder().encode(manifestPayload).write(to: destination.appendingPathComponent("manifest-rpc.json"), options: .atomic)
        let published = cycleCall(id, "published", extra: ["export_id": manifestPayload["export_id"]!,
            "manifest_sha256": .string(NG2CycleWire.hash(manifestBytes)),
            "archive_sha256": .string(String(repeating: "a", count: 64))]).0?["payload"]?.objectValue ?? [:]
        require(published["accepted"]?.boolValue == true && published["receipt_sha256"]?.stringValue?.count == 64,
            "test112_synthetic_export_actual_idempotent_publication_ack")
        try JSONEncoder().encode(published).write(to: destination.appendingPathComponent("published-rpc.json"), options: .atomic)
        var inventory = [[String: JSONValue]](), total = 0
        let enumerator = FileManager.default.enumerator(at: destination, includingPropertiesForKeys: [.isRegularFileKey])!
        for case let file as URL in enumerator {
            guard (try file.resourceValues(forKeys: [.isRegularFileKey])).isRegularFile == true else { continue }
            let bytes = try Data(contentsOf: file), name = String(file.path.dropFirst(destination.path.count+1))
            total += bytes.count; inventory.append(["name": .string(name), "bytes": .int(bytes.count), "sha256": .string(NG2CycleWire.hash(bytes))])
        }
        require(total > 0 && total <= 64*1024*1024 && inventory.count <= 256,
            "test112_synthetic_export_bounded_actual_spool_inventory")
        let receipt: [String: JSONValue] = ["schema": .string("test112-synthetic-runtime-export-v1"),
            "scope": .string("procedural host pixels and clock; actual C Runtime Spool RPC; no phone acceptance"),
            "case": .string(selectedCase), "label": .string(label), "run_id": .string(id),
            "client_archive_receipt_is_simulated": .bool(true), "client_archive_sha256": .string(String(repeating: "a", count: 64)),
            "manifest_sha256": .string(NG2CycleWire.hash(manifestBytes)),
            "publication_receipt_sha256": published["receipt_sha256"] ?? .null,
            "export_id": manifestPayload["export_id"] ?? .null,
            "published_record_present": .bool(ir110Record(root, id, "published") != nil),
            "files": .array(inventory.sorted { ($0["name"]?.stringValue ?? "") < ($1["name"]?.stringValue ?? "") }.map { .object($0) })]
        require(receipt["published_record_present"]?.boolValue == true, "test112_synthetic_export_actual_publication_record_present")
        try JSONEncoder().encode(receipt).write(to: destination.appendingPathComponent("receipt.json"), options: .atomic)
    } catch { require(false, "test112_synthetic_export_copy_or_hash_failed") }
}
func runtime112Start(_ id: String) {
    fixtureFailureSnapshot = {
        ["report": .object(report(id)), "cycle": .object(cyclePayload(id)),
         "restart_yield": .object(runtime112State(id)), "touches": .int(NG2Fake.countTouches()),
         "requests": .int(NG2Fake.countRequests())]
    }
    let answer = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-irregular-v1"), "yield_after_restart": .bool(true),
        "_necro_owner": .string("fixture-owner")])
    require(answer.1 == nil, "test112_optin_start_accepted")
}

func runtime112Reset(_ root: URL) {
    _ = resetCycleFixture(root)
    NG2RuntimeCycleTestHooks.afterClassificationCall = nil
    NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = nil
    NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = nil
    NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite = nil
    NG2RuntimeTestHooks.afterCaptureBackendReply = nil
    NG2RuntimeTestHooks.beforeCaptureControlConsume = nil
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeTestHooks.beforeControlTick = nil
    NG2Fake.lock.lock(); NG2Fake.walkPaused = true; NG2Fake.lock.unlock()
    NG2Fake.useFixedCaptureClock()
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = { test060_revalidationCaptureBoundary() }
}

// The first level uses the unchanged walking fixture. Only an actual real
// direction gesture reveals its goods, and only its real MOVED observation
// allows the old negative/PAUSE/checkpoint/intent/RESTART path to complete.
final class Runtime112World {
    let gate = NSLock()
    let id: String
    let empty = cycleSearchPixels(worldX: 36, variant: 1)
    let partial = cycleSearchPixels(worldX: 36, variant: 1, goods: 2)
    let full = cycleSearchPixels(worldX: 36, variant: 1, goods: 1)
    let unknown = ir110Blank()
    var stage = 0, restarts = 0, pausesAfterRestart = 0, phaseFrames = 0
    var aligned = false, settled = false, candidateReady = false, pinPressureChecked = false
    var post = "empty", resultMode = "normal", kernelCalls = 0, workerCalls = 0
    var oldJob: UInt64 = 0, postJobs = [UInt64]()
    var postWorkerCaptures = [UInt64](), postWorkerHashes = [String]()
    var activeID: String
    init(_ id: String) { self.id = id; activeID = id }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func install() {
        NG2RuntimeCycleTestHooks.rgba = { original in
            NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
            if paused { return original }
            return self.locked {
                if self.stage == 0 { return original }
                if self.stage == 2 || self.candidateReady { return self.full }
                self.phaseFrames += 1
                switch self.post {
                case "sequence":
                    if self.phaseFrames == 1 { return self.partial }
                    if self.phaseFrames == 2 { return self.full }
                    return self.unknown
                case "first_full": return self.phaseFrames == 1 ? self.full : self.unknown
                case "full": return self.full
                case "partial": return self.partial
                case "death": return ir110Overlay(self.full, 1)
                case "late": return self.phaseFrames == 1 ? self.empty : self.partial
                default: return self.empty
                }
            }
        }
        NG2Fake.cycleTap = { x, y in
            if x == 297 && y == 448 {
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
            }
            if x == 144 && y == 448 {
                self.locked { self.restarts += 1 }
                // Stop only the next fixture admission. An already admitted
                // old-prefix capture drains normally; it cannot become the
                // first stable ACK-bound new-floor source.
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false
                NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
            }
            if x == 390 && y == 448 { self.locked { if self.stage > 0 { self.pausesAfterRestart += 1 } } }
        }
        NG2RuntimeTestHooks.afterTicketReturned = { command in
            let run = self.locked { self.activeID }
            let events = (report(run)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let restart = events.first(where: { $0["id"]?.intValue == Int(command) && $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }) else { return }
            require(NG2Fake.changeClockAtCaptureBoundary {
                let floorAt = UInt64(restart["end_ns"]!.intValue!) + 220_000_000, now = NG2Fake.virtualClock()
                if now < floorAt { NG2Fake.advance(floorAt-now) }
                self.locked { self.stage = 1; self.phaseFrames = 0 }
                NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
            }, "test112_new_floor_pixels_only_after_actual_restart_callback_return")
        }
        NG2RuntimeTestHooks.scheduleTicket = { command, callback in
            let run = self.locked { self.activeID }
            let events = (report(run)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard events.contains(where: { $0["id"]?.intValue == Int(command) && $0["kind"]?.intValue == 4 }) else { return false }
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(run, expectedID: command) }
            callback(); return true
        }
        NG2RuntimeTestHooks.beforeControlTick = {
            let run = self.locked { self.activeID }, current = report(self.locked { self.activeID })
            let checkPins = self.locked { () -> Bool in
                guard self.stage == 0, !self.pinPressureChecked, (current["accepted_frames"]?.intValue ?? 0) > 0 else { return false }
                self.pinPressureChecked = true; return true
            }
            if checkPins {
                let ordinary = runtime.testRestartYieldPinPressure(run, protectAll: false) ?? [:]
                let protected = runtime.testRestartYieldPinPressure(run, protectAll: true) ?? [:]
                require(ordinary["accepted"]?.boolValue == true && ordinary["pin_count"]?.intValue == 24 &&
                    ordinary["incoming_retained"]?.boolValue == true && ordinary["evicted"]?.intValue == 1,
                    "test112_actual_pin_allocator_full_ordinary_evicts_one_keeps_incoming")
                require(protected["accepted"]?.boolValue == false && protected["pin_count"]?.intValue == 24 &&
                    protected["protected_preserved"]?.boolValue == true && protected["incoming_retained"]?.boolValue == false &&
                    protected["evicted"]?.intValue == 0,
                    "test112_actual_pin_allocator_all_protected_holds_without_evicting")
            }
            let ready = (current["beat_period_ns"]?.intValue ?? 0) > 0 &&
                !(current["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 })
            let align = self.locked { () -> Bool in
                if self.stage != 0 || self.aligned || !ready { return false }; self.aligned = true; return true
            }
            if align {
                require(NG2Fake.changeClockAtCaptureBoundary {
                    let now = NG2Fake.virtualClock()
                    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
                    let period: UInt64 = 520_000_000, position = (now-epoch+150_000_000) % period
                    NG2Fake.advance((period+100_000_000-position) % period)
                }, "test112_actual_walking_initial_alignment")
            }
            let state = cycleCompanion(run)
            let advance = self.locked { () -> Bool in
                guard self.stage == 0, !self.settled, (state["pause_capture_id"]?.intValue ?? 0) > 0,
                      state["pending"]?.boolValue == false, state["outcome"]?.stringValue == "negative",
                      (state["durable_ns"]?.intValue ?? 0) > 0 else { return false }
                self.settled = true; return true
            }
            if advance { NG2Fake.advance(220_000_000) }
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { job in
            self.locked { self.workerCalls += 1; if self.stage == 0 { self.oldJob = job } else { self.postJobs.append(job) } }
            // Keep the existing source150ms/worker100ms contract. This only
            // stops a procedural capture loop from racing the virtual clock.
            NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 1_000; NG2Fake.lock.unlock()
            let run = self.locked { self.activeID }, state = cycleCompanion(self.locked { self.activeID })
            runtime112RecordAdmission(run, state, label: self.locked { self.stage == 0 ? "old_walk" : "retained_goods" })
            let sourceStart = state["capture_start_ns"]?.intValue ?? 0, worker = state["worker_started_ns"]?.intValue ?? 0
            let deadline = state["deadline_ns"]?.intValue ?? 0
            require(sourceStart > 0 && worker > 0 && deadline <= sourceStart + 150_000_000 && deadline <= worker + 100_000_000,
                "test112_each_actual_worker_keeps_source150_worker100")
            if self.locked({ self.stage > 0 }) {
                let capture = UInt64(state["capture_id"]?.intValue ?? 0)
                let evidence = runtime.testOriginalFrameEvidence(run, captureIDs: [capture])
                var rawHash = ""
                if let frame = evidence?[capture], let decoded = NG2Raster.decode(frame.0) { rawHash = NG2CycleWire.hash(decoded) }
                self.locked { self.postWorkerCaptures.append(capture); self.postWorkerHashes.append(rawHash) }
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, _, _ in
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY), "test112_every_worker_calls_real_target_only_kernel")
            self.locked { self.kernelCalls += 1 }
        }
        NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
            let phase = self.locked { self.stage }, behavior = self.locked { self.post }
            let late = phase > 0 && self.locked { self.resultMode == "late_candidate" }
            let outcome: Int32 = phase == 0 ? 3 : (behavior == "full" && !late ? 0 : 1)
            if late { NG2Fake.advance(101_000_001) }
            let partialUnknown = phase > 0 && behavior == "sequence" && scene.pointee.goods == Int32(NG2_GOODS_PARTIAL)
            if partialUnknown { ng2_fixture_partial_unknown110(scene, result.started_ns, NG2Runtime.now(), &result) }
            else { ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), outcome, &result) }
            if late { result.status = UInt32(NG2_RING_DEADLINE) }
            if phase > 0 && outcome == 1 && !partialUnknown {
                self.locked { self.candidateReady = true }
                NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
            }
        }
    }
}

func runtime112RequireBlocked(_ world: Runtime112World, _ label: String, workers: Int? = nil) {
    let id = world.locked { world.activeID }, state = runtime112State(world.locked { world.activeID })
    require((state["unique_retained_frame_count"]?.intValue ?? Int.max) <= 44 &&
        (runtime.testIrregularRetentionIDs(id)?["pinned"]?.count ?? Int.max) <= 24,
        "test112_" + label + "_raw_unique44_pin24_bounds")
    require(world.locked { world.pausesAfterRestart == 0 } && cyclePayload(id)["terminal"]?.boolValue != true,
        "test112_" + label + "_no_pause_terminal_or_handoff")
    if let root = NG2RuntimeCycleTestHooks.spoolRoot {
        require(!ir110Records(root, id).contains { $0["kind"]?.stringValue == "terminal" },
            "test112_" + label + "_actual_terminal_record_not_written")
    }
    if let workers { require(world.locked { world.postJobs.count == workers }, "test112_" + label + "_no_replacement_job") }
    let next = runtime.handle(method: "necro_native_start", params: ["run_id": .string(identity()),
        "profile": .string("normal-1-1-irregular-v1"), "yield_after_restart": .bool(true),
        "_necro_owner": .string("fixture-owner")])
    require(next.1 != nil && runtime.hasLease && state["control_ready"]?.boolValue != true,
        "test112_" + label + "_next_start_zero")
}

func runtime112FinishCandidate(_ root: URL, _ world: Runtime112World, required: Set<Int>) {
    let id = world.locked { world.activeID }
    pump("test112_actual_late_candidate_latched", timeout: 30) { cycleCompanion(id)["candidate_latched"]?.boolValue == true }
    pump("test112_candidate_capture_worker_main_actual_drain", timeout: 30) { cycleDrained(id) }
    require(runtime112Handoff(root, id)["allowed"]?.boolValue == false && world.locked { world.restarts == 1 },
        "test112_candidate_vetoes_restarted_budget_and_second_restart")
    require(world.locked { world.kernelCalls == world.workerCalls }, "test112_each_admitted_worker_has_real_kernel")
    runtime111Manifest(id, required: required)
    publishFixtureClaim(id, requiredCaptureIDs: required)
}

func runtime112AssertNormalChain(_ root: URL, _ world: Runtime112World) {
    let id = world.id, rows = ir110Records(root, id)
    let kinds = rows.compactMap { $0["kind"]?.stringValue }
    guard let checkpoint = rows.first(where: { $0["kind"]?.stringValue == "checkpoint" })?["payload"]?.objectValue,
          let intent = rows.first(where: { $0["kind"]?.stringValue == "restart_intent" })?["payload"]?.objectValue,
          let outcome = rows.first(where: { $0["kind"]?.stringValue == "restart_outcome" })?["payload"]?.objectValue else {
        require(false, "test112_actual_checkpoint_intent_outcome_chain_present"); return
    }
    let old = checkpoint["cycle"]?.objectValue ?? [:], rs = intent["cycle"]?.objectValue ?? [:]
    let next = outcome["cycle"]?.objectValue ?? [:]
    require(kinds.filter { $0 == "restart_intent" }.count == 1 && kinds.filter { $0 == "restart_outcome" }.count == 1 &&
        old["outcome"]?.stringValue == "negative" && checkpoint["assessment_adopted"]?.boolValue == true &&
        old["job_id"]?.intValue == rs["job_id"]?.intValue && rs["job_id"]?.intValue == next["job_id"]?.intValue &&
        (next["next_floor_capture_id"]?.intValue ?? 0) > 0 && next["outcome_ns"]?.intValue == 0 &&
        (runtime112State(id)["epoch_restart_id"]?.intValue ?? 0) > 0,
        "test112_actual_old_negative_same_job_durable_restart_new_floor_chain")
    let events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let restart = events.first(where: { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }) else {
        require(false, "test112_actual_restart_ack_present"); return
    }
    let command = restart["id"]?.intValue ?? 0
    require(events.contains { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 &&
            $0["motion"]?.intValue == 1 && ($0["id"]?.intValue ?? 0) < command } &&
        !NG2Fake.paths().isEmpty && (report(id)["inputs"]?.intValue ?? 0) > 0 &&
        events.filter { ($0["id"]?.intValue ?? 0) > command }.allSatisfy { $0["kind"]?.intValue == 2 },
        "test112_real_direction_before_restart_and_no_direction_resume_restart_after_new_floor")
}

func testRestartYield112Happy(_ root: URL, secondUUID: Bool = true) {
    runtime112Reset(root); let id = identity(), world = Runtime112World(id); world.install(); runtime112Start(id)
    pump("test112_walk_negative_restart_new_floor_yield_actual_drain", timeout: 40) { cycleDrained(id) }
    let handoff = runtime112Handoff(root, id), state = runtime112State(id)
    require(Set(handoff.keys) == ["schema", "kind", "allowed", "reason", "qualified_ns", "source_capture_id", "source_prefix", "pause_capture_id", "completed_prefix"] &&
        handoff["kind"]?.stringValue == "restarted_budget" && handoff["allowed"]?.boolValue == true &&
        world.locked { world.restarts == 1 && world.pausesAfterRestart == 1 } &&
        (state["first_floor_capture_id"]?.intValue ?? 0) > 0 && state["control_ready"]?.boolValue == true,
        "test112_real_walk_negative_restart_fresh_floor_pause_handoff3")
    runtime112AssertNormalChain(root, world)
    let blocked = runtime.handle(method: "necro_native_start", params: ["run_id": .string(identity()),
        "profile": .string("normal-1-1-irregular-v1"), "yield_after_restart": .bool(true),
        "_necro_owner": .string("fixture-owner")])
    require(blocked.1?.code == -32095, "test112_unpublished_old_run_prevents_new_uuid")
    publishFixtureClaim(id, requiredCaptureIDs: [state["first_floor_capture_id"]!.intValue!])
    runtime112PreserveSyntheticExport(root, id, label: "happy_yield")
    guard secondUUID else { return }
    let next = identity(), beforeTaps = NG2Fake.taps().count, beforeMoves = NG2Fake.paths().count
    world.locked { world.activeID = next; world.stage = 2; world.candidateReady = true }
    runtime112Start(next)
    pump("test112_published_next_uuid_same_floor_fresh_resume_candidate_drain", timeout: 30) { cycleDrained(next) }
    let taps = Array(NG2Fake.taps().dropFirst(beforeTaps)), current = report(next)
    require(taps.first == CGPoint(x: 297, y: 448) && taps.filter { $0.x == 144 }.isEmpty &&
        NG2Fake.paths().count == beforeMoves && world.locked { world.restarts == 1 } &&
        cycleCompanion(next)["candidate_latched"]?.boolValue == true,
        "test112_new_uuid_same_current_floor_fresh_pause_resume_no_inherited_restart_or_move")
    let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let captures = (current["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let source = captures.first { $0["id"]?.intValue == events.first?["source_capture_id"]?.intValue }
    require(events.first?["kind"]?.intValue == 1 && (events.first?["source_capture_id"]?.intValue ?? 0) > 0 &&
        source?["completed_prefix_start"]?.intValue == 0 && source?["completed_prefix_end"]?.intValue == 0 &&
        source?["stable"]?.boolValue == true,
        "test112_new_uuid_resume_uses_its_own_fresh_prefix_zero_pause")
    publishFixtureClaim(next)
}

func testRestartYield112FirstSources(_ root: URL, firstFull: Bool, variant: String) {
    let cancelWriter = variant != "candidate", deathBeforeCancel = variant == "death_cancel"
    runtime112Reset(root); let id = identity(), world = Runtime112World(id), release = DispatchSemaphore(value: 0)
    let controlRelease = DispatchSemaphore(value: 0), writerGate = NSLock()
    var writerParked = false, controlParked = false
    world.post = "sequence"; world.install()
    if firstFull { world.post = "first_full" }
    NG2RuntimeTestHooks.beforeCaptureControlConsume = { capture in
        guard world.locked({ world.stage == 1 }), runtime112State(id)["first_floor_capture_id"]?.intValue == Int(capture) else { return }
        writerGate.lock(); let first = !controlParked; controlParked = true; writerGate.unlock()
        if first { require(controlRelease.wait(timeout: .now() + 30) == .success, "test112_first_floor_control_callback_park_bounded") }
    }
    NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite = { _ in
        writerGate.lock(); writerParked = true; writerGate.unlock()
        require(release.wait(timeout: .now() + 30) == .success, "test112_old_restart_outcome_writer_park_bounded")
    }
    runtime112Start(id)
    pump("test112_first_floor_actual_control_callback_parked", timeout: 30) { writerGate.lock(); defer { writerGate.unlock() }; return controlParked }
    pump("test112_later_unknown_replaces_latest_before_first_floor_control_returns", timeout: 20) {
        world.locked { world.phaseFrames >= 4 } && (report(id)["latest_frames_replaced"]?.intValue ?? 0) > 0
    }
    let first = runtime112State(id)
    require(first["basis_pending"]?.boolValue == false &&
        (first["first_full_capture_id"]?.intValue ?? 0) > 0 &&
        (firstFull || (first["first_partial_capture_id"]?.intValue ?? 0) > 0),
        "test112_immutable_original_partial_full_slots_before_latest_replacement_and_outcome")
    controlRelease.signal(); NG2RuntimeTestHooks.beforeCaptureControlConsume = nil
    pump("test112_restart_outcome_writer_parked", timeout: 30) { writerGate.lock(); defer { writerGate.unlock() }; return writerParked }
    pump("test112_first_partial_full_slots_survive_later_unknown", timeout: 20) {
        let state = runtime112State(id), count = world.locked { world.phaseFrames }
        return (state["first_full_capture_id"]?.intValue ?? 0) > 0 &&
            (firstFull || (state["first_partial_capture_id"]?.intValue ?? 0) > 0) && count >= 32
    }
    let saved = runtime112State(id), floor = saved["first_floor_capture_id"]!.intValue!
    let partial = saved["first_partial_capture_id"]?.intValue ?? 0, full = saved["first_full_capture_id"]!.intValue!
    NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
    require(saved["basis_pending"]?.boolValue == false && saved["first_goods_submitted"]?.boolValue == false &&
        saved["epoch_restart_id"]?.intValue == report(id)["last_completed_id"]?.intValue &&
        world.locked { world.postJobs.isEmpty }, "test112_capture_slots_arm_at_actual_ack_before_old_outcome_durable")
    ir110CheckFootprint(id); runtime112RequireBlocked(world, "raw_slots_before_outcome", workers: 0)
    let required = Set([floor, full, partial].filter { $0 > 0 })
    let evidence = runtime.testOriginalFrameEvidence(id, captureIDs: required.map { UInt64($0) })
    require(evidence?.count == required.count && saved["first_goods_raw_sha256"]?.stringValue == NG2CycleWire.hash(firstFull ? world.full : world.partial),
        "test112_first_original_goods_hash_not_unknown_replacement")
    if deathBeforeCancel {
        world.locked { world.post = "death" }
        NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        pump("test112_actual_death_before_boundary_data_classification", timeout: 20) { ir110State(id)["kind"]?.stringValue == "death" }
        require(world.locked { world.postJobs.isEmpty } && runtime112State(id)["basis_pending"]?.boolValue == false,
            "test112_actual_death_has_no_uncommitted_budget_data_or_pause_permission")
    }
    if cancelWriter { _ = call("necro_native_cancel", id) }
    release.signal(); NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite = nil
    if cancelWriter {
        NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        pump("test112_cancel_with_uncommitted_old_outcome_and_raw_slots_drains", timeout: 30) { cycleDrained(id) }
        require(world.locked { world.postJobs.isEmpty && world.pausesAfterRestart == 0 && world.restarts == 1 } &&
            runtime112Handoff(root, id)["allowed"]?.boolValue == false,
            "test112_cancel_keeps_original_slots_but_no_data_job_pause_or_handoff")
        if deathBeforeCancel {
            let irregular = ir110Record(root, id, "terminal")?["irregular"]?.objectValue ?? [:]
            require(irregular["kind"]?.stringValue == "death" && runtime112State(id)["first_goods_submitted"]?.boolValue == false,
                "test112_death_unsubmitted_partial_full_are_retained_unassessed_never_normal_handoff")
            print("EVIDENCE TEST112 DEATH_UNASSESSED skipped/death run=" + id + " partial=" + String(partial) + " full=" + String(full))
        }
        runtime111Manifest(id, required: required); publishFixtureClaim(id, requiredCaptureIDs: required)
        if partial > 0 { runtime111PersistedPixels(root, capture: UInt64(partial), expected: world.partial) }
        runtime111PersistedPixels(root, capture: UInt64(full), expected: world.full)
        return
    }
    runtime112FinishCandidate(root, world, required: required)
    let submitted = Set((runtime112State(id)["submitted_goods_ids"]?.arrayValue ?? []).compactMap { $0.intValue })
    require(submitted.contains(firstFull ? full : partial) && world.locked { world.postWorkerCaptures.first == UInt64(firstFull ? full : partial) },
        "test112_first_serial_real_data_worker_uses_first_retained_goods_id")
    if !firstFull {
        require(partial < full && submitted.contains(full) &&
            world.locked { world.postWorkerCaptures == [UInt64(partial), UInt64(full)] &&
                world.postWorkerHashes == [NG2CycleWire.hash(world.partial), NG2CycleWire.hash(world.full)] },
            "test112_first_partial_unknown_then_first_full_positive_serial_real_callbacks")
    }
    if partial > 0 { runtime111PersistedPixels(root, capture: UInt64(partial), expected: world.partial) }
    runtime111PersistedPixels(root, capture: UInt64(full), expected: world.full)
    if !firstFull { runtime112PreserveSyntheticExport(root, id, label: "first_partial_candidate") }
}

func testRestartYield112ReturnFence(_ root: URL, producer: Bool, variant: String) {
    runtime112Reset(root); let id = identity(), world = Runtime112World(id), release = DispatchSemaphore(value: 0)
    let parkGate = NSLock(); var parked = false, parkedJob: UInt64 = 0
    world.post = "full"; world.resultMode = variant; world.install()
    let park: (UInt64) -> Void = { job in
        guard world.locked({ world.stage == 1 }) else { return }
        let first = world.locked { world.postJobs.first == job }
        guard first else { return }
        parkGate.lock(); parked = true; parkedJob = job; parkGate.unlock()
        require(release.wait(timeout: .now() + 30) == .success, "test112_actual_return_fence_park_bounded")
    }
    if producer { NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = park }
    else { NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = park }
    runtime112Start(id)
    pump("test112_actual_post_restart_return_closure_parked", timeout: 30) { parkGate.lock(); defer { parkGate.unlock() }; return parked }
    if producer {
        pump("test112_enqueue_producer_park_allows_logical_commit", timeout: 20) {
            cycleCompanion(id)["pending"]?.boolValue == false &&
                (variant == "late_candidate" || runtime112State(id)["C_ready"]?.boolValue == true)
        }
    }
    let snapshot = runtime112State(id)
    parkGate.lock(); let job = parkedJob; parkGate.unlock()
    require(snapshot["drain_token_count"]?.intValue == 1 && cycleCompanion(id)["pending"]?.boolValue == false &&
        cycleCompanion(id)["job_id"]?.intValue == Int(job) && cyclePayload(id)["workers_drained"]?.boolValue == false,
        "test112_logical_false_is_not_actual_" + (producer ? "producer" : "commit") + "_return")
    runtime112RequireBlocked(world, producer ? "producer_return" : "commit_return", workers: 1)
    if variant == "late_candidate" {
        require(cycleCompanion(id)["candidate_latched"]?.boolValue == true && runtime112State(id)["C_invalid"]?.boolValue == true,
            "test112_late_positive_hint_vetoes_even_before_actual_callback_returns")
    }
    if variant == "cancel" {
        _ = call("necro_native_cancel", id)
        require(!cycleDrained(id) && runtime.hasLease && world.locked { world.pausesAfterRestart == 0 },
            "test112_cancel_after_logical_clear_keeps_actual_return_lease_and_input_zero")
    }
    release.signal()
    NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = nil
    NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = nil
    if variant == "cancel" {
        pump("test112_cancel_old_return_tokens_actual_drain", timeout: 30) { cycleDrained(id) }
        require(runtime112Handoff(root, id)["allowed"]?.boolValue == false &&
            world.locked { world.pausesAfterRestart == 0 && world.restarts == 1 } &&
            runtime112State(id)["drain_token_count"]?.intValue == 0,
            "test112_canceled_return_cannot_pause_mint_handoff_or_reopen_epoch")
        publishFixtureClaim(id); return
    }
    if variant == "late_candidate" {
        runtime112FinishCandidate(root, world, required: [runtime112State(id)["first_full_capture_id"]!.intValue!]); return
    }
    pump("test112_both_actual_returns_allow_one_yield_pause", timeout: 30) { cycleDrained(id) }
    require(runtime112Handoff(root, id)["kind"]?.stringValue == "restarted_budget" &&
        runtime112Handoff(root, id)["allowed"]?.boolValue == true &&
        runtime112State(id)["drain_token_count"]?.intValue == 0 && world.locked { world.pausesAfterRestart == 1 },
        "test112_return_fences_release_then_real_pause_handoff_only_once")
    runtime112AssertNormalChain(root, world); publishFixtureClaim(id)
}
func testRestartYield112CaptureDrain(_ root: URL, boundary: String) {
    runtime112Reset(root); let id = identity(), world = Runtime112World(id)
    let writerRelease = DispatchSemaphore(value: 0), frameRelease = DispatchSemaphore(value: 0), gate = NSLock()
    let writerReady = DispatchSemaphore(value: 0)
    var writer = false, frame = false, admissionWaited = false, parkedID: UInt64 = 0
    let staleEmpty = boundary == "stale_empty"
    world.post = staleEmpty ? "empty" : "late"; world.install()
    NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite = { _ in
        gate.lock(); writer = true; gate.unlock(); writerReady.signal()
        require(writerRelease.wait(timeout: .now() + 30) == .success, "test112_capture_drain_outcome_writer_bounded")
    }
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        test060_revalidationCaptureBoundary()
        let afterFloor = world.locked { world.stage == 1 && world.phaseFrames >= 1 }
        gate.lock(); let wait = afterFloor && !admissionWaited
        if wait { admissionWaited = true }; gate.unlock()
        if wait { require(writerReady.wait(timeout: .now() + 30) == .success, "test112_first_goods_capture_waits_for_actual_outcome_writer_park") }
    }
    let park: (UInt64) -> Void = { capture in
        guard world.locked({ world.stage == 1 && world.phaseFrames >= 1 }) else { return }
        gate.lock(); let should = writer && !frame
        if should { frame = true; parkedID = capture }; gate.unlock()
        if should { require(frameRelease.wait(timeout: .now() + 30) == .success, "test112_actual_capture_pipeline_boundary_park_bounded") }
    }
    switch boundary {
    case "capture", "stale_empty": NG2RuntimeTestHooks.afterCaptureBackendReply = park
    case "decode": NG2RuntimeTestHooks.beforeCaptureDecode = park
    case "analysis": NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, _, _, _, _ in park(capture) }
    case "control": NG2RuntimeTestHooks.beforeCaptureControlConsume = park
    default: require(false, "test112_unknown_pipeline_boundary")
    }
    runtime112Start(id)
    pump("test112_actual_" + boundary + "_pipeline_parked_after_new_floor", timeout: 30) { gate.lock(); defer { gate.unlock() }; return frame }
    writerRelease.signal(); NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite = nil
    // Analysis/control hooks run on the serial control queue: their real
    // callback itself blocks C service, which is a stronger precondition than
    // observing a stale ready projection from another queue.
    if boundary == "capture" || boundary == "decode" || staleEmpty {
        pump("test112_C_ready_while_" + boundary + "_lease_alive", timeout: 20) { runtime112State(id)["C_ready"]?.boolValue == true }
    }
    gate.lock(); let capture = parkedID; gate.unlock()
    let leases = runtime.testIrregularRetentionIDs(id)?["capture_pipeline"] ?? []
    require(leases.contains(capture) || (runtime112State(id)["capture_control_token_count"]?.intValue ?? 0) > 0,
        "test112_" + boundary + "_actual_pipeline_lease_retained")
    if staleEmpty {
        // FRESH is3s and the immutable restart parent is4s. This admitted
        // empty frame may expire, but cannot renew the old UI source. The
        // Runtime must unpause bounded capture, then use a genuinely fresh
        // frame inside the same original parent; no goods deadline changes.
        NG2Fake.advance(3_100_000_000)
        pump("test112_expired_ui_source_reopens_only_capture_within_parent", timeout: 20) {
            runtime112State(id)["C_ready"]?.boolValue == false && runtime112State(id)["capture_paused"]?.boolValue == false
        }
        runtime112RequireBlocked(world, "stale_empty_source")
        frameRelease.signal(); NG2RuntimeTestHooks.afterCaptureBackendReply = nil
        pump("test112_fresh_empty_source_reacquired_then_yield_drains", timeout: 30) { cycleDrained(id) }
        let handoff = runtime112Handoff(root, id)
        require(handoff["kind"]?.stringValue == "restarted_budget" && handoff["allowed"]?.boolValue == true &&
            (handoff["source_capture_id"]?.intValue ?? 0) > Int(capture) &&
            world.locked { world.postJobs.isEmpty && world.pausesAfterRestart == 1 && world.restarts == 1 },
            "test112_stale_ui_never_reused_fresh_same_parent_floor_allows_one_pause")
        runtime112AssertNormalChain(root, world); publishFixtureClaim(id); return
    }
    runtime112RequireBlocked(world, "capture_" + boundary)
    frameRelease.signal()
    NG2RuntimeTestHooks.afterCaptureBackendReply = nil; NG2RuntimeTestHooks.beforeCaptureDecode = nil
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil; NG2RuntimeTestHooks.beforeCaptureControlConsume = nil
    runtime112FinishCandidate(root, world, required: [Int(capture)])
    require(world.locked { world.postWorkerCaptures.contains(capture) }, "test112_" + boundary + "_late_first_goods_actual_worker_veto")
}

func testRestartYield112InitialGate(_ root: URL) {
    runtime112Reset(root); let id = identity()
    NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
    NG2RuntimeCycleTestHooks.rgba = { original in original }
    runtime112Start(id)
    pump("test112_optin_initial_floor_held_and_actual_drain", timeout: 20) { cycleDrained(id) }
    require(NG2Fake.countTouches() == 0 && NG2Fake.paths().isEmpty,
        "test112_optin_every_new_uuid_requires_fresh_pause_no_floor_direct_input")
    require(runtime112Handoff(root, id)["allowed"]?.boolValue == false,
        "test112_initial_floor_terminal_does_not_mint_restart_handoff")
    publishFixtureClaim(id)
}

// This world advances only after an actual public UI callback. The factory
// renders every pixel; it never writes a Scene or patches Controller state.
final class Runtime112UpperWorld {
    let gate = NSLock()
    let id: String, mirrored: Bool, cancelPartial: Bool
    let workerRelease = DispatchSemaphore(value: 0)
    var stage = 0, aligned = false, workerParked = false, restarts = 0, pressureAdded = false, pressureObserved = false
    var advanced = Set<UInt64>(), rawSources = [UInt64: Data](), kernelCalls = 0, workers = 0
    var restoreClock = false
    init(_ id: String, mirrored: Bool, cancelPartial: Bool) {
        self.id = id; self.mirrored = mirrored; self.cancelPartial = cancelPartial
    }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func install() {
        NG2RuntimeCycleTestHooks.rgba = { original in
            NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused, epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
            if paused { return original }
            let phase = self.locked { self.stage }
            if phase > 6 { return cycleSearchPixels(worldX: 108, variant: 1) }
            let now = NG2Fake.virtualClock(), midpoint = now > 1_000_000 ? now - 1_000_000 : now
            let elapsed = midpoint >= epoch ? midpoint-epoch : 0, period: UInt64 = 520_000_000
            let fraction = Double(period-1-(elapsed % period))/Double(period)
            var bytes = Data(count: 896*414*4); let count = bytes.count
            bytes.withUnsafeMutableBytes { pixels in
                require(ng2_fixture_upper112_rgba(pixels.bindMemory(to: UInt8.self).baseAddress, count,
                    Int32(phase), self.mirrored ? 1 : 0, fraction) == 1,
                    "test112_upper_actual_procedural_rgba_factory")
            }
            return bytes
        }
        NG2Fake.cycleTap = { x, y in
            if x == 297 && y == 448 { NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock() }
            if x == 144 && y == 448 {
                self.locked { self.restarts += 1 }
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
            }
        }
        NG2RuntimeTestHooks.scheduleTicket = { command, callback in
            let events = (report(self.id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }), event["kind"]?.intValue == 4 else { return false }
            let phase = self.locked { self.stage }, horizontal = self.mirrored ? 2 : 1
            require(phase < 6 && event["direction"]?.intValue == (phase < 4 ? horizontal : 4),
                "test112_upper_actual_planner_h_h_h_h_down_down_sequence")
            NG2RuntimeTestHooks.beforeMainAuthority = {
                admitFirstFixtureMove(self.id, expectedID: command, afterAlignment: { _ in
                    NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
                })
            }
            callback(); return true
        }
        NG2RuntimeTestHooks.afterTicketReturned = { command in
            let events = (report(self.id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }),
                  event["outcome"]?.intValue == 2, let kind = event["kind"]?.intValue,
                  kind == 3 || kind == 4 else { return }
            let first = self.locked { self.advanced.insert(command).inserted }
            guard first else { return }
            require(NG2Fake.changeClockAtCaptureBoundary {
                if kind == 4, let target = event["target_ns"]?.intValue {
                    let end = UInt64(target) + 80_000_000, now = NG2Fake.virtualClock()
                    if now < end { NG2Fake.advance(end-now) }
                    self.locked { self.stage += 1 }
                } else {
                    let floorAt = UInt64(event["end_ns"]!.intValue!) + 220_000_000, now = NG2Fake.virtualClock()
                    if now < floorAt { NG2Fake.advance(floorAt-now) }
                    self.locked { self.stage = 7 }
                }
                NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
            }, "test112_upper_new_actual_world_pose_after_ack_at_capture_boundary")
        }
        NG2RuntimeTestHooks.beforeControlTick = {
            let current = report(self.id), cycle = cycleCompanion(self.id), state = runtime112State(self.id)
            let realFit = (current["beat_period_ns"]?.intValue ?? 0) > 0
            let align = self.locked { () -> Bool in
                guard self.stage == 0, !self.aligned, realFit,
                      !(current["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 }) else { return false }
                self.aligned = true; return true
            }
            if align {
                require(NG2Fake.changeClockAtCaptureBoundary {
                    let now = NG2Fake.virtualClock()
                    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
                    let period: UInt64 = 520_000_000, position = (now-epoch+150_000_000) % period
                    NG2Fake.advance((period+100_000_000-position) % period)
                }, "test112_upper_initial_real_hud_fit_alignment")
            }
            let restore = self.locked { () -> Bool in
                guard self.restoreClock, cycle["pending"]?.boolValue == false,
                      state["drain_token_count"]?.intValue == 0 else { return false }
                self.restoreClock = false; return true
            }
            if restore { NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 80_000_000; NG2Fake.lock.unlock() }
            if cycle["outcome"]?.stringValue == "negative", (cycle["pause_capture_id"]?.intValue ?? 0) > 0,
               (cycle["durable_ns"]?.intValue ?? 0) > 0, self.locked({ self.stage == 6 }) {
                let now = NG2Fake.virtualClock(), durable = UInt64(cycle["durable_ns"]!.intValue!)
                if now < durable + 220_000_000 { NG2Fake.advance(durable + 220_000_000-now) }
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { _ in
            NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 1_000; NG2Fake.lock.unlock()
            let state = cycleCompanion(self.id), capture = UInt64(state["capture_id"]?.intValue ?? 0)
            runtime112RecordAdmission(self.id, state, label: "upper_normal_ring")
            let original = runtime.testOriginalFrameEvidence(self.id, captureIDs: [capture])
            guard let originalFrame = original?[capture], let pixels = NG2Raster.decode(originalFrame.0) else {
                require(false, "test112_upper_actual_worker_original_raw_source_available"); return
            }
            self.locked { self.workers += 1; self.rawSources[capture] = pixels }
            let addPressure = self.locked { () -> Bool in
                guard !self.pressureAdded, state["partial"]?.boolValue == true else { return false }
                self.pressureAdded = true; return true
            }
            if addPressure {
                require(runtime.testRestartYieldSaturatePins112(self.id), "test112_upper_live_ordinary_pin_pressure_admitted")
                require(runtime.testIrregularRetentionIDs(self.id)?["pinned"]?.count == 24,
                    "test112_upper_first_actual_partial_worker_under_live24_pins")
                self.locked { self.pressureObserved = true }
            }
            let source = state["capture_start_ns"]?.intValue ?? 0, worker = state["worker_started_ns"]?.intValue ?? 0
            let deadline = state["deadline_ns"]?.intValue ?? 0
            require(source > 0 && worker > 0 && deadline <= source + 150_000_000 && deadline <= worker + 100_000_000,
                "test112_upper_each_real_job_keeps_source150_worker100")
            if self.cancelPartial && state["partial"]?.boolValue == true {
                let first = self.locked { () -> Bool in if self.workerParked { return false }; self.workerParked = true; return true }
                if first { require(self.workerRelease.wait(timeout: .now() + 30) == .success, "test112_upper_first_actual_worker_cancel_park_bounded") }
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, _, _ in
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY), "test112_upper_real_normal_target_only_kernel")
            self.locked { self.kernelCalls += 1 }
        }
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { _ in self.locked { self.restoreClock = true } }
        // In particular there is no classificationResult override here.
        NG2RuntimeCycleTestHooks.classificationResult = nil
    }
}

func testRuntime112UpperEntry(_ root: URL, mirrored: Bool, cancelPartial: Bool) {
    runtime112Reset(root); let id = identity(), world = Runtime112UpperWorld(id, mirrored: mirrored, cancelPartial: cancelPartial)
    world.install(); runtime112Start(id)
    if cancelPartial {
        pump("test112_upper_first_partial_actual_worker_parked", timeout: 30) { world.locked { world.workerParked } }
        let sources = world.locked { world.rawSources }
        require(!sources.isEmpty && world.locked { world.stage == 2 && world.pressureObserved } && NG2Fake.paths().count == 2 &&
            runtime.testIrregularRetentionIDs(id)?["pinned"]?.count == 24,
            "test112_upper_opened_door_raw_first_partial_is_actual_two_input_source")
        _ = call("necro_native_cancel", id)
        require(!cycleDrained(id) && runtime.hasLease, "test112_upper_cancel_keeps_actual_worker_and_raw_source_lease")
        world.workerRelease.signal()
        NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        pump("test112_upper_canceled_raw_source_worker_actual_drain", timeout: 30) { cycleDrained(id) }
        require(NG2Fake.paths().count == 2 && world.locked { world.restarts == 0 } &&
            runtime112Handoff(root, id)["allowed"]?.boolValue == false,
            "test112_upper_cancel_no_further_entry_down_restart_or_handoff")
        ir110CheckFootprint(id); runtime111Manifest(id, required: Set(sources.keys.map { Int($0) }))
        for (capture, pixels) in sources { runtime111PersistedPixels(root, capture: capture, expected: pixels) }
        publishFixtureClaim(id, requiredCaptureIDs: Set(sources.keys.map { Int($0) })); return
    }
    pump("test112_upper_actual_entry_down_all_goods_negative_restart_yield_drain", timeout: 45) { cycleDrained(id) }
    let events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let directions = events.filter { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 }
    require(directions.map { $0["direction"]?.intValue ?? 0 } == [mirrored ? 2 : 1, mirrored ? 2 : 1, mirrored ? 2 : 1, mirrored ? 2 : 1, 4, 4] &&
        directions.map { $0["motion"]?.intValue ?? 0 } == [1, 3, 1, 1, 1, 1] &&
        world.locked { world.restarts == 1 && world.kernelCalls == world.workers && world.pressureObserved },
        "test112_upper_real_opening_then_each_moved_h_h_down_down_and_one_restart")
    let targets = directions.suffix(4).map { $0["target_ns"]?.intValue ?? 0 }
    require(targets.count == 4 && zip(targets, targets.dropFirst()).allSatisfy { $0.1-$0.0 == 520_000_000 },
        "test112_upper_each_continuation_real_ticket_is_the_next_beat")
    let checkpoint = ir110Record(root, id, "checkpoint") ?? [:], assessment = checkpoint["assessment"]?.objectValue ?? [:]
    require(assessment["outcome"]?.stringValue == "negative" && assessment["coverage"]?.stringValue == "complete" &&
        checkpoint["assessment_adopted"]?.boolValue == true &&
        runtime112Handoff(root, id)["kind"]?.stringValue == "restarted_budget" &&
        runtime112Handoff(root, id)["allowed"]?.boolValue == true,
        "test112_upper_normal_real_classifier_all_offers_negative_saved_restart_yield")
    let sources = world.locked { world.rawSources }
    require(sources.count >= 5 && (runtime112State(id)["unique_retained_frame_count"]?.intValue ?? Int.max) <= 44,
        "test112_upper_every_actual_job_raw_source_keeps_bounded_identity")
    ir110CheckFootprint(id); runtime111Manifest(id, required: Set(sources.keys.map { Int($0) }))
    for (capture, pixels) in sources { runtime111PersistedPixels(root, capture: capture, expected: pixels) }
    publishFixtureClaim(id, requiredCaptureIDs: Set(sources.keys.map { Int($0) }))
    if !mirrored { runtime112PreserveSyntheticExport(root, id, label: "upper_left_real_ring") }
}
#endif

let root112 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime112-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root112, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root112) }
NG2RuntimeCycleTestHooks.spoolRoot = root112
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case112 = CommandLine.arguments.last ?? ""
pump("test112_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
#if NG2_RESTART_YIELD_TEST112_GREEN
switch case112 {
case "legacy": testCycle094TwoShopsAndIntentCancel(root112, cancelIntent: false)
case "yield":
    testRestartYield112InitialGate(root112.appendingPathComponent("initial"))
    testRestartYield112Happy(root112.appendingPathComponent("walking"))
case "first_partial", "first_full":
    for variant in ["candidate", "cancel", "death_cancel"] {
        testRestartYield112FirstSources(root112.appendingPathComponent(variant),
            firstFull: case112 == "first_full", variant: variant)
    }
case "producer_return", "commit_return":
    for variant in ["normal", "late_candidate", "cancel"] {
        testRestartYield112ReturnFence(root112.appendingPathComponent(variant), producer: case112 == "producer_return", variant: variant)
    }
case "capture_drain":
    for boundary in ["capture", "decode", "analysis", "control", "stale_empty"] {
        testRestartYield112CaptureDrain(root112.appendingPathComponent(boundary), boundary: boundary)
    }
case "upper_entry":
    for variant in ["left", "right", "cancel"] {
        testRuntime112UpperEntry(root112.appendingPathComponent(variant), mirrored: variant == "right", cancelPartial: variant == "cancel")
    }
default: require(false, "test112_unknown_case_is_not_another_fixture")
}
print("PASS TEST112 CASE " + case112)
#else
require(case112 == "optin_red", "test112_red_case_explicit")
_ = resetCycleFixture(root112)
let redID112 = identity()
let redReply112 = runtime.handle(method: "necro_native_start", params: ["run_id": .string(redID112),
    "profile": .string("normal-1-1-irregular-v1"), "yield_after_restart": .bool(true),
    "_necro_owner": .string("fixture-owner")])
require(redReply112.1 == nil, "test112_optin_start_accepted")
require(false, "test112_baseline_unexpectedly_accepted_optin")
#endif
