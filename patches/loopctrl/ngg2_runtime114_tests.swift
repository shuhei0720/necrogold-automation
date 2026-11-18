// TEST114 selected actual Runtime/C boundaries. All future images, clock and
// game responses are procedural. The unchanged normal Perception/Motion/Ring
// producers run; no classifier result or controller field is supplied here.
struct Runtime114Capture {
    let id, start, end, prefix: UInt64
    let stable: Bool
}

func runtime114Scene(_ rgba: Data) -> UnsafeMutablePointer<NG2Scene> {
    let scene = UnsafeMutablePointer<NG2Scene>.allocate(capacity: 1)
    scene.initialize(to: NG2Scene())
    require(rgba.withUnsafeBytes { ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress,
        rgba.count, 896*4, scene) } == 0, "test114_unchanged_normal_perception_succeeds")
    return scene
}
func runtime114Motion(_ before: Data, _ after: Data) -> NG2Motion {
    let a = runtime114Scene(before), b = runtime114Scene(after)
    defer { a.deinitialize(count: 1); a.deallocate(); b.deinitialize(count: 1); b.deallocate() }
    var motion = NG2Motion()
    require(ng2_motion(a, b, Int32(NG2_UP), &motion) == 1,
        "test114_unchanged_normal_motion_call_succeeds")
    return motion
}
func runtime114Credit(_ report: [String: JSONValue]) -> [JSONValue] {
    ["inputs", "moves", "door_changes", "terrain_changes", "restarts", "x", "y"].map { report[$0] ?? .null }
}
// Before lead calibration C deliberately numbers a direct door-opening probe
// ordinal0. This fixture begins at that observed door. It still requires the
// exact current source, full frozen timing and normal raw door observation;
// entry and the independent current-view UP use the original positive-ordinal
// qualifier. No event or production field is rewritten for either check.
func runtime114InitialOpeningTicket(_ id: String, _ snapshot: [String: JSONValue], _ ticket: [String: JSONValue]) -> Bool {
    guard snapshot["lead_confirmed"]?.intValue == 0,
          ticket["ordinal"]?.intValue == 0, ticket["direction"]?.intValue == 3,
          let command = ticket["id"]?.intValue, command > 0,
          snapshot["current_command_id"]?.intValue == command, snapshot["input_state"]?.intValue == 1,
          ticket["kind"]?.intValue == 4, ticket["outcome"]?.intValue == 0, ticket["begin_ns"]?.intValue == 0,
          let target = ticket["target_ns"]?.intValue, target == snapshot["next_target_ns"]?.intValue,
          let notBefore = ticket["not_before_ns"]?.intValue, let deadline = ticket["deadline_ns"]?.intValue,
          let lead = snapshot["lead_ns"]?.intValue, lead > 0, target >= lead,
          notBefore == target-lead, deadline >= notBefore, deadline-notBefore <= 10_000_000,
          let source = ticket["source_capture_id"]?.intValue, source > 0, source == snapshot["last_capture_id"]?.intValue,
          let start = ticket["source_start_ns"]?.intValue, start > 0, start == snapshot["last_capture_start_ns"]?.intValue,
          let end = snapshot["last_capture_end_ns"]?.intValue, end >= start,
          let phase = ticket["phase_sample_ns"]?.intValue, phase > 0, phase <= end,
          let now = snapshot["device_now_ns"]?.intValue, now >= end, now >= phase,
          now <= deadline, now-start <= 3_000_000_000, now-phase <= 3_000_000_000,
          let actual = runtime.testOriginalFrameEvidence(id, captureIDs: [UInt64(source)])?[UInt64(source)],
          actual.1["capture_start_ns"] == ticket["source_start_ns"], actual.1["stable_prefix"]?.boolValue == true,
          actual.1["completed_prefix_start"] == snapshot["last_completed_id"],
          actual.1["completed_prefix_end"] == snapshot["last_completed_id"],
          let pixels = NG2Raster.decode(actual.0) else { return false }
    let scene = runtime114Scene(pixels)
    defer { scene.deinitialize(count: 1); scene.deallocate() }
    let up = withUnsafeBytes(of: scene.pointee.tiles) { $0.load(fromByteOffset: 4*23+11, as: UInt8.self) }
    return scene.pointee.state == Int32(NG2_FLOOR) && scene.pointee.goods == Int32(NG2_GOODS_UNKNOWN) && up == UInt8(NG2_TILE_DOOR)
}
func runtime114Admission(_ id: String, _ state: [String: JSONValue]) {
    let source = state["capture_start_ns"]?.intValue ?? 0, worker = state["worker_started_ns"]?.intValue ?? 0
    let deadline = state["deadline_ns"]?.intValue ?? 0
    require(source > 0 && worker >= source && worker <= deadline && worker-source <= 150_000_000 &&
        deadline <= source+150_000_000 && deadline <= worker+100_000_000,
        "test114_actual_source150_worker100_admission_bounds")
    var row = state.filter { ["job_id", "capture_id", "capture_start_ns", "worker_started_ns", "deadline_ns", "prefix"].contains($0.key) }
    row["run_id"] = .string(id); row["source_age_at_worker_admission_ns"] = .int(worker-source)
    if let bytes = try? JSONEncoder().encode(row), let text = String(data: bytes, encoding: .utf8) {
        print("EVIDENCE TEST114 ADMISSION " + text)
    } else { require(false, "test114_actual_admission_evidence_encodes") }
}

final class Runtime114CurrentWorld {
    let gate = NSLock(), id: String
    let oldStartRelease = DispatchSemaphore(value: 0)
    let oldProducerRelease = DispatchSemaphore(value: 0), oldCommitRelease = DispatchSemaphore(value: 0)
    let currentProducerRelease = DispatchSemaphore(value: 0), currentCommitRelease = DispatchSemaphore(value: 0)
    var stage = 0, aligned = false, decodeID: UInt64 = 0, restarts = 0
    var oldReady = false, oldProducerParked = false, oldCommitParked = false
    var currentProducerParked = false, currentCommitParked = false, collectProofs = false, restoreClock = false
    var oldJob: UInt64 = 0, currentJob: UInt64 = 0, activeJob: UInt64 = 0
    var oldState = [String: JSONValue](), currentState = [String: JSONValue]()
    var workers = [UInt64](), kernelOutcomes = [UInt64: UInt32]()
    var rendered = [UInt64: (Int, Data)](), consumed = [UInt64: Runtime114Capture]()
    var sources = [UInt64: Data](), sourceMetadata = [UInt64: [String: JSONValue]]()
    var proofs = [Runtime114Capture](), reservations = [UInt64: [String: JSONValue]](), advanced = Set<UInt64>()
    var frozenCredit = [JSONValue](), frozenTouches = 0, frozenPaths = 0

    init(_ id: String) { self.id = id }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func releaseAll() {
        oldStartRelease.signal(); oldProducerRelease.signal(); oldCommitRelease.signal()
        currentProducerRelease.signal(); currentCommitRelease.signal()
        NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    }
    func freezeCaptures() {
        NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
    }
    func continueCaptures(_ advance: UInt64) {
        NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = advance; NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
    }
    func park(_ semaphore: DispatchSemaphore, _ label: String) {
        require(semaphore.wait(timeout: .now()+30) == .success, "test114_" + label + "_actual_return_park_bounded")
    }
    func requireBlocked(_ label: String, workers expected: Int) {
        let state = runtime112State(id), snapshot = report(id)
        require(state["drain_token_count"]?.intValue == 1 && !cycleDrained(id) && runtime.hasLease &&
            cyclePayload(id)["workers_drained"]?.boolValue == false &&
            locked { workers.count == expected } && NG2Fake.countTouches() == frozenTouches &&
            NG2Fake.paths().count == frozenPaths && runtime114Credit(snapshot) == frozenCredit,
            "test114_" + label + "_actual_token_blocks_new_worker_and_every_ui")
    }
    func install() {
        NG2RuntimeCycleTestHooks.classificationResult = nil
        NG2RuntimeTestHooks.beforeCaptureDecode = { capture in self.locked { self.decodeID = capture } }
        NG2RuntimeCycleTestHooks.rgba = { original in
            NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused, epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
            if paused { return original }
            let phase = self.locked { self.stage }
            if phase > 4 { return cycleSearchPixels(worldX: 108, variant: 1) }
            let now = NG2Fake.virtualClock(), midpoint = now > 1_000_000 ? now-1_000_000 : now
            let elapsed = midpoint >= epoch ? midpoint-epoch : 0, period: UInt64 = 520_000_000
            let fraction = Double(period-1-(elapsed % period))/Double(period)
            var rgba = Data(count: 896*414*4); let count = rgba.count
            rgba.withUnsafeMutableBytes { raw in
                require(ng2_fixture_current114_rgba(raw.bindMemory(to: UInt8.self).baseAddress,
                    count, Int32(phase), fraction) == 1, "test114_procedural_current_rgba_factory")
            }
            if phase >= 2 {
                self.locked {
                    require(self.decodeID > 0 && self.rendered.count < 32, "test114_bounded_actual_capture_pixel_inventory")
                    self.rendered[self.decodeID] = (phase, rgba)
                }
            }
            return rgba
        }
        NG2Fake.cycleTap = { x, y in
            if x == 297 && y == 448 { NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock() }
            if x == 144 && y == 448 {
                self.locked { self.restarts += 1 }
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
            }
        }
        NG2RuntimeTestHooks.scheduleTicket = { command, callback in
            let snapshot = report(self.id)
            let events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }), event["kind"]?.intValue == 4 else { return false }
            let phase = self.locked { self.stage }
            let pending = runtime112UpperPendingTicket(snapshot, event) ||
                (phase == 0 && runtime114InitialOpeningTicket(self.id, snapshot, event))
            require(pending && event["direction"]?.intValue == 3,
                "test114_owned_new_up_ticket_keeps_real_source_phase_and_frozen_window")
            require(phase == 0 || phase == 1 || phase == 3, "test114_no_ui_in_old_or_unclassified_current_world")
            if phase == 3 {
                let basis = self.locked { (self.currentState, self.proofs, self.reservations.values.compactMap { $0["ordinal"]?.intValue }.max() ?? 0) }
                let last = basis.1.last
                require(basis.1.count == 2 && runtime112State(self.id)["drain_token_count"]?.intValue == 0 &&
                    cycleCompanion(self.id)["pending"]?.boolValue == false &&
                    event["source_capture_id"]?.intValue == snapshot["last_capture_id"]?.intValue &&
                    (event["source_capture_id"]?.intValue ?? 0) >= Int(last?.id ?? UInt64.max) &&
                    (event["phase_sample_ns"]?.intValue ?? 0) >= Int(last?.start ?? UInt64.max) &&
                    (event["ordinal"]?.intValue ?? 0) > basis.2 &&
                    cycleCompanion(self.id)["hold_started_ns"] == self.oldState["hold_started_ns"] &&
                    cycleCompanion(self.id)["continuation_deadline_ns"] == self.oldState["continuation_deadline_ns"] &&
                    (event["target_ns"]?.intValue ?? Int.max) <= (self.oldState["continuation_deadline_ns"]?.intValue ?? 0)-50_000_000,
                    "test114_new_current_up_requires_two_direct_new_proofs_fresh_phase_original_parent_and_new_ordinal")
                require(runtime114Credit(snapshot) == self.frozenCredit,
                    "test114_data_and_direct_zeros_never_credit_the_old_move")
            }
            self.locked {
                require(self.reservations[command] == nil, "test114_ticket_id_is_never_reused")
                self.reservations[command] = event
            }
            NG2RuntimeTestHooks.beforeMainAuthority = {
                admitFirstFixtureMove(self.id, expectedID: command, afterAlignment: { _ in self.freezeCaptures() })
            }
            callback(); return true
        }
        NG2RuntimeTestHooks.afterTicketReturned = { command in
            let events = (report(self.id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }),
                  event["outcome"]?.intValue == 2, let kind = event["kind"]?.intValue,
                  kind == 3 || kind == 4 else { return }
            guard self.locked({ self.advanced.insert(command).inserted }) else { return }
            require(NG2Fake.changeClockAtCaptureBoundary {
                if kind == 4 {
                    let at = UInt64(event["target_ns"]!.intValue!)+80_000_000, now = NG2Fake.virtualClock()
                    if now < at { NG2Fake.advance(at-now) }
                    self.locked {
                        if self.stage == 0 { self.stage = 1 }
                        else if self.stage == 1 { self.stage = 2 }
                        else { require(self.stage == 3, "test114_current_up_pose_has_one_owner"); self.stage = 4 }
                    }
                } else {
                    let at = UInt64(event["end_ns"]!.intValue!)+220_000_000, now = NG2Fake.virtualClock()
                    if now < at { NG2Fake.advance(at-now) }
                    self.locked { self.stage = 5 }
                }
                self.continueCaptures(20_000_000)
            }, "test114_world_pose_changes_only_after_actual_ack_at_capture_boundary")
        }
        NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, start, end, prefix, stable in
            guard self.locked({ self.rendered[capture] != nil }) else { return }
            self.locked { self.consumed[capture] = Runtime114Capture(id: capture, start: start, end: end, prefix: prefix, stable: stable) }
        }
        NG2RuntimeTestHooks.beforeControlTick = {
            _ = cycleCall(self.id, extra: ["keepalive": .bool(true)])
            let snapshot = report(self.id), cycle = cycleCompanion(self.id)
            let align = self.locked { () -> Bool in
                guard self.stage == 0, !self.aligned, (snapshot["beat_period_ns"]?.intValue ?? 0) > 0,
                    !(snapshot["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 }) else { return false }
                self.aligned = true; return true
            }
            if align {
                require(NG2Fake.changeClockAtCaptureBoundary {
                    let now = NG2Fake.virtualClock()
                    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
                    let period: UInt64 = 520_000_000, position = (now-epoch+150_000_000) % period
                    NG2Fake.advance((period+100_000_000-position) % period)
                }, "test114_initial_fit_uses_actual_procedural_hud_phase")
            }
            let last = UInt64(snapshot["last_capture_id"]?.intValue ?? 0)
            let stopOld = self.locked { () -> Bool in
                guard self.oldJob != 0, self.currentJob == 0, !self.oldReady else { return false }
                let ready = self.consumed.values.filter { $0.id <= last && self.rendered[$0.id]?.0 == 3 && $0.stable }
                guard ready.count >= 2 else { return false }
                self.oldReady = true; return true
            }
            if stopOld { self.freezeCaptures() }
            let stopProofs = self.locked { () -> Bool in
                guard self.collectProofs, self.proofs.count < 2,
                    let frame = self.consumed[last], self.rendered[last]?.0 == 3,
                    last > UInt64(self.currentState["capture_id"]?.intValue ?? Int.max), frame.stable,
                    !self.proofs.contains(where: { $0.id == last }) else { return false }
                self.proofs.append(frame)
                return self.proofs.count == 2
            }
            if stopProofs { self.freezeCaptures() }
            let restore = self.locked { () -> Bool in
                guard self.restoreClock, runtime112State(self.id)["drain_token_count"]?.intValue == 0 else { return false }
                self.restoreClock = false; return true
            }
            if restore { self.continueCaptures(20_000_000) }
            if cycle["outcome"]?.stringValue == "negative", (cycle["pause_capture_id"]?.intValue ?? 0) > 0,
                (cycle["durable_ns"]?.intValue ?? 0) > 0, self.locked({ self.stage == 4 }) {
                let now = NG2Fake.virtualClock(), at = UInt64(cycle["durable_ns"]!.intValue!)+220_000_000
                if now < at { NG2Fake.advance(at-now) }
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { job in
            NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 1_000; NG2Fake.lock.unlock()
            let state = cycleCompanion(self.id), capture = UInt64(state["capture_id"]?.intValue ?? 0)
            runtime114Admission(self.id, state)
            require(state["job_id"]?.intValue == Int(job), "test114_actual_job_callback_matches_public_c_source")
            guard let actual = runtime.testOriginalFrameEvidence(self.id, captureIDs: [capture])?[capture],
                  let raw = NG2Raster.decode(actual.0) else {
                require(false, "test114_actual_worker_original_raw_source_available"); return
            }
            let first = self.locked { () -> Bool in
                self.activeJob = job; self.workers.append(job); self.sources[capture] = raw; self.sourceMetadata[capture] = actual.1
                if self.oldJob == 0 { self.oldJob = job; self.oldState = state; self.stage = 3; return true }
                if self.currentJob == 0 { self.currentJob = job; self.currentState = state }
                return false
            }
            require(actual.1["stable_prefix"]?.boolValue == true && actual.1["inflight_start"]?.boolValue == false &&
                actual.1["inflight_end"]?.boolValue == false && actual.1["completed_prefix_start"] == state["prefix"] &&
                actual.1["completed_prefix_end"] == state["prefix"] && actual.1["capture_start_ns"] == state["capture_start_ns"],
                "test114_original_rgba_capture_interval_prefix_and_lease_are_exact")
            if first { self.park(self.oldStartRelease, "old_normal_worker") }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY) && status == 0,
                "test114_actual_unmodified_normal_target_only_producer")
            self.locked { self.kernelOutcomes[self.activeJob] = outcome }
        }
        NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = { job in
            if self.locked({ job == self.oldJob }) {
                self.locked { self.oldProducerParked = true }; self.park(self.oldProducerRelease, "old_producer")
            } else if self.locked({ job == self.currentJob }) {
                self.locked { self.currentProducerParked = true }; self.park(self.currentProducerRelease, "current_producer")
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { job in
            if self.locked({ job == self.oldJob }) {
                self.locked { self.oldCommitParked = true }; self.park(self.oldCommitRelease, "old_commit")
            } else if self.locked({ job == self.currentJob }) {
                self.locked { self.currentCommitParked = true }; self.park(self.currentCommitRelease, "current_commit")
            } else { self.locked { self.restoreClock = true } }
        }
    }
}

func testRuntime114Current(_ root: URL, cancel: Bool) {
    runtime112Reset(root)
    let id = identity(), world = Runtime114CurrentWorld(id)
    defer { world.releaseAll() }
    world.install(); runtime112Start(id)
    pump("test114_actual_old_full_worker_has_two_new_current_captures", timeout: 45) { world.locked { world.oldReady } }
    world.locked {
        world.frozenCredit = runtime114Credit(report(id)); world.frozenTouches = NG2Fake.countTouches(); world.frozenPaths = NG2Fake.paths().count
    }
    require(world.frozenPaths == 2 && world.locked({ world.stage == 3 && world.workers.count == 1 }),
        "test114_actual_open_door_then_enter_precedes_old_full_worker")
    world.oldStartRelease.signal()
    pump("test114_old_actual_producer_and_commit_returns_both_parked", timeout: 30) {
        world.locked { world.oldProducerParked && world.oldCommitParked }
    }
    let queued = cycleCompanion(id), old = world.locked { world.oldState }
    require(queued["job_id"]?.intValue != old["job_id"]?.intValue && queued["capture_id"]?.intValue != old["capture_id"]?.intValue &&
        queued["pending"]?.boolValue == true && queued["worker_started_ns"]?.intValue == 0 &&
        queued["prefix"] == old["prefix"] && queued["level_id"] == old["level_id"] &&
        queued["hold_started_ns"] == old["hold_started_ns"] &&
        queued["continuation_deadline_ns"] == old["continuation_deadline_ns"],
        "test114_old_unknown_queues_independent_current_data_without_old_authority")
    world.requireBlocked("both_old_returns", workers: 1)
    world.oldProducerRelease.signal()
    pump("test114_old_producer_release_does_not_drain_while_old_commit_still_held") {
        world.locked { world.oldCommitParked } && runtime112State(id)["drain_token_count"]?.intValue == 1
    }
    world.requireBlocked("old_commit_still_held_after_producer_release", workers: 1)
    world.oldCommitRelease.signal()
    pump("test114_current_actual_producer_and_commit_returns_both_parked", timeout: 30) {
        world.locked { world.currentProducerParked && world.currentCommitParked }
    }
    world.requireBlocked("both_current_returns", workers: 2)
    let current = world.locked { world.currentState }, anchorID = UInt64(current["capture_id"]?.intValue ?? 0)
    let oldID = UInt64(old["capture_id"]?.intValue ?? 0), raw = world.locked { world.sources }
    require(current["job_id"] == queued["job_id"] && current["capture_id"] == queued["capture_id"] &&
        current["capture_start_ns"] == queued["capture_start_ns"] && current["prefix"] == old["prefix"] &&
        current["hold_started_ns"] == old["hold_started_ns"] && current["continuation_deadline_ns"] == old["continuation_deadline_ns"] &&
        world.locked({ world.kernelOutcomes[world.oldJob] == 0 && world.kernelOutcomes[world.currentJob] == 0 }) &&
        oldID != anchorID && raw[oldID] != nil && raw[anchorID] != nil &&
        runtime114Motion(raw[oldID]!, raw[anchorID]!).kind == Int32(NG2_MOTION_UNKNOWN),
        "test114_actual_current_worker_uses_new_immutable_source_old_motion_stays_unknown")
    world.locked { world.collectProofs = true }
    world.currentCommitRelease.signal(); world.continueCaptures(20_000_000)
    pump("test114_two_actual_post_result_current_frames_commit_while_producer_return_is_held", timeout: 30) {
        world.locked { world.proofs.count == 2 }
    }
    world.requireBlocked("current_producer_held_after_commit_and_two_proofs", workers: 2)
    let proofs = world.locked { world.proofs }, metadata = world.locked { world.sourceMetadata[anchorID] ?? [:] }
    require(proofs.count == 2 && proofs[0].id > anchorID && proofs[1].id > proofs[0].id &&
        proofs[0].start >= UInt64(metadata["capture_end_ns"]?.intValue ?? Int.max) &&
        proofs[1].start >= proofs[0].end && proofs.allSatisfy({ $0.stable && $0.prefix == UInt64(current["prefix"]?.intValue ?? Int.max) }),
        "test114_two_new_nonoverlapping_frames_share_exact_current_epoch_prefix")
    for proof in proofs {
        guard let actual = runtime.testOriginalFrameEvidence(id, captureIDs: [proof.id])?[proof.id], let pixels = NG2Raster.decode(actual.0) else {
            require(false, "test114_actual_direct_proof_raw_is_retained"); return
        }
        let motion = runtime114Motion(raw[anchorID]!, pixels)
        require(motion.kind == Int32(NG2_BLOCKED) && motion.dx == 0 && motion.dy == 0,
            "test114_each_new_frame_is_direct_normal_zero_from_immutable_anchor")
    }
    if cancel {
        _ = call("necro_native_cancel", id)
        require(!cycleDrained(id) && runtime.hasLease && runtime112State(id)["drain_token_count"]?.intValue == 1,
            "test114_cancel_keeps_core_raw_epoch_and_actual_current_return_lease")
        world.currentProducerRelease.signal(); world.continueCaptures(20_000_000)
        pump("test114_cancel_actual_current_worker_and_capture_return_drain", timeout: 40) { cycleDrained(id) }
        require(NG2Fake.countTouches() == world.frozenTouches && NG2Fake.paths().count == world.frozenPaths &&
            world.locked({ world.restarts == 0 && world.workers.count == 2 }) &&
            runtime112Handoff(root, id)["allowed"]?.boolValue == false,
            "test114_canceled_current_epoch_cannot_dispatch_up_pause_restart_or_handoff")
    } else {
        world.currentProducerRelease.signal(); world.continueCaptures(20_000_000)
        pump("test114_actual_current_new_up_normal_negative_durable_restart_and_yield", timeout: 45) { cycleDrained(id) }
        let events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        let moves = events.filter { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 }
        let reservations = world.locked { world.reservations }
        require(moves.count == 3 && moves.map({ $0["direction"]?.intValue ?? 0 }) == [3,3,3] &&
            moves.map({ $0["motion"]?.intValue ?? 0 }) == [3,1,1] && reservations.count == 3 &&
            moves.allSatisfy({ event in
                guard let command = event["id"]?.intValue, let reserved = reservations[UInt64(command)] else { return false }
                return runtime112UpperAcknowledgedTicket(event, reserved)
            }), "test114_only_owned_actual_open_enter_and_one_current_view_up_are_credited")
        let checkpoint = ir110Record(root, id, "checkpoint") ?? [:], assessment = checkpoint["assessment"]?.objectValue ?? [:]
        require(assessment["outcome"]?.stringValue == "negative" && assessment["coverage"]?.stringValue == "complete" &&
            checkpoint["assessment_adopted"]?.boolValue == true && world.locked({ world.restarts == 1 && world.workers.count >= 3 }) &&
            runtime112Handoff(root, id)["kind"]?.stringValue == "restarted_budget" && runtime112Handoff(root, id)["allowed"]?.boolValue == true,
            "test114_fresh_post_up_normal_complete_negative_precedes_saved_pause_restart_handoff")
        let finalRaw = world.locked { world.sources }
        let checkpointState = checkpoint["cycle"]?.objectValue ?? [:]
        let negativeSource = UInt64(checkpointState["capture_id"]?.intValue ?? 0)
        let negativeJob = UInt64(checkpointState["job_id"]?.intValue ?? 0)
        require(negativeSource > anchorID && !proofs.contains(where: { $0.id == negativeSource }) &&
            finalRaw[negativeSource] != nil && checkpoint["raw_sha256"]?.stringValue == NG2CycleWire.hash(finalRaw[negativeSource]!) &&
            world.locked({ world.kernelOutcomes[negativeJob] == UInt32(NG2_RING_NEGATIVE) }),
            "test114_post_up_classification_has_its_own_new_raw_source")
    }
    let sources = world.locked { world.sources }
    ir110CheckFootprint(id); runtime111Manifest(id, required: Set(sources.keys.map { Int($0) }))
    for (capture, bytes) in sources { runtime111PersistedPixels(root, capture: capture, expected: bytes) }
    publishFixtureClaim(id, requiredCaptureIDs: Set(sources.keys.map { Int($0) }))
    runtime112PreserveSyntheticExport(root, id, label: cancel ? "current_cancel" : "current_view")
}

let root114 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime114-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root114, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root114) }
NG2RuntimeCycleTestHooks.spoolRoot = root114
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case114 = CommandLine.arguments.last ?? ""
pump("test114_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
switch case114 {
case "current_view": testRuntime114Current(root114.appendingPathComponent("view"), cancel: false)
case "current_cancel": testRuntime114Current(root114.appendingPathComponent("cancel"), cancel: true)
default: require(false, "test114_unknown_case_is_not_another_fixture")
}
print("PASS TEST114 CASE " + case114)
