// HOST suffix only. The original Runtime and shared fakes remain byte-identical.
#if NG2_RUNTIME_HOST_TEST
private func require120(_ value: @autoclosure () -> Bool, _ name: String) {
    if !value() { print("FAIL test120_" + name); fflush(stdout); exit(1) }
}
private func pump120(_ name: String, _ predicate: () -> Bool) {
    let until = Date().addingTimeInterval(5)
    while !predicate() && Date() < until { RunLoop.current.run(until: Date().addingTimeInterval(0.0002)) }
    require120(predicate(), name)
}
private func counts120() -> NG2Partial120Counts {
    var value = NG2Partial120Counts(); ng2_partial120_counts(&value); return value
}
private func sceneHash120(_ frame: NG2Frame) -> String {
    NG2CycleWire.hash(Data(bytes: frame.analysis.scene, count: MemoryLayout<NG2Scene>.size))
}
// Only the two AuthManager references lexically inside staged NG2Runtime use
// this nested alias. The adapter delegates to the unchanged external fake.
private final class NG2Runtime120Owner {
    static let shared = NG2Runtime120Owner()
    static var late = false, spent = false
    static var deadline: UInt64 = 0, expenseStart: UInt64 = 0, expenseEnd: UInt64 = 0
    func clientName(forTokenId owner: String) -> String? {
        let answer = AuthManager.shared.clientName(forTokenId: owner)
        if Self.late && !Self.spent && counts120().begin_accepted == 1 {
            Self.spent = true; Self.expenseStart = DispatchTime.now().uptimeNanoseconds
            let until = max(Self.deadline + 1_000_000, Self.expenseStart + 11_000_000)
            require120(until - Self.expenseStart <= 25_000_000, "bounded_real_guard_expense")
            while DispatchTime.now().uptimeNanoseconds < until {}
            Self.expenseEnd = DispatchTime.now().uptimeNanoseconds
        }
        return answer
    }
}
private final class NG2Runtime120Evidence {
    let lock = NSLock()
    var frames: [NG2Frame] = []
    var worker: [String: Any] = [:]
    var held: (() -> Void)?
    var ticket = NG2Command()
    var ticketReturned = false
    var drained = false
    var workerReturned = false, commitReturned = false
    var ringStatus: Int32 = -1, ringOutcome: UInt32 = 99
    var ringMode: Int32 = -1, ringReturn: UInt64 = 0
    var finalEvent = NG2ControllerEvent()
    var finalStatus = NG2ControllerStatus()
    var observeMotionCalls: UInt64 = 0
    var synthEntry: UInt64 = 0
    var assessmentHash = ""
    var scheduled: UInt64 = 0, mainHook: UInt64 = 0
    var firstSource: UInt64 = 0, currentSource: UInt64 = 0
    var frameRows: [[String: Any]] {
        frames.map { frame in ["id": frame.id, "start_ns": frame.start, "end_ns": frame.end,
            "analysis_start_ns": frame.analysisStart, "analysis_end_ns": frame.analysisEnd,
            "prefix": frame.prefix, "generation": frame.generation,
            "state": frame.analysis.scene.pointee.state, "goods": frame.analysis.scene.pointee.goods,
            "raw_sha256": NG2CycleWire.hash(frame.rgba), "scene_sha256": sceneHash120(frame)] }
    }
}
private func retainPartial120Setup(_ context: UnsafeMutableRawPointer?, _ id: UInt64,
    _ start: UInt64, _ end: UInt64, _ prefix: UInt64, _ analysisStart: UInt64, _ analysisEnd: UInt64,
    _ raw: UnsafePointer<UInt8>?, _ length: Int, _ scene: UnsafePointer<NG2Scene>?,
    _ irregular: UnsafePointer<NG2IrregularObservation>?) {
    guard let context, let raw, let scene, let irregular else { require120(false, "setup_frame_callback"); return }
    let evidence = Unmanaged<NG2Runtime120Evidence>.fromOpaque(context).takeUnretainedValue()
    let analysis = NG2Analysis(); analysis.scene.pointee = scene.pointee; analysis.irregular = irregular.pointee
    evidence.frames.append(NG2Frame(id: id, start: start, end: end, decodeEnd: end, generation: 1,
        analysisStart: analysisStart, analysisEnd: analysisEnd, analysis: analysis,
        startPrefix: prefix, prefix: prefix, startInFlight: false, endInFlight: false, stable: true,
        rgba: Data(bytes: raw, count: length), rasterTrace: NG2Raster.Trace(sourceWidth: 896,
            sourceHeight: 414, orientation: 1, sourceNs: 0, drawNs: 0, orientNs: 0, scaleNs: 0,
            copyPixels: 896*414), encodedBytes: 0, diagnosticOrientation: 1))
}
extension NG2Runtime {
    private typealias AuthManager = NG2Runtime120Owner
    func test120PartialBeginDispatch(_ variant: String) {
        require120(["normal", "post_guard_late"].contains(variant), "known_variant")
        NG2Fake.reset(.empty); NG2RuntimeTestHooks.clock = nil
        NG2RuntimeCycleTestHooks.classificationResult = nil; NG2RuntimeCycleTestHooks.rgba = nil
        NG2RuntimeCycleTestHooks.irregularRGBA = nil; NG2RuntimeEvidenceTestHooks.snapshot = nil
        require120(NG2Fake.offset == 0 && NG2Fake.fixedClock == nil, "real_monotonic_offset0")
        let evidence = NG2Runtime120Evidence(); var setup = NG2Partial120Setup()
        func onControl(_ name: String, _ body: @escaping () -> Void) {
            let completion = DispatchGroup(); completion.enter()
            self.controlQueue.async { body(); completion.leave() }
            // The real preparation/main callback must be able to service main.
            pump120(name) { completion.wait(timeout: .now()) == .success }
        }
        guard let core = ng2_fixture_partial120_setup(retainPartial120Setup,
            Unmanaged.passUnretained(evidence).toOpaque(), &setup) else {
            require120(false, "public_C_setup_error_" + String(setup.error)); return
        }
        require120(setup.error == 0 && setup.normal_units == 1 && setup.status.input_state == 3,
                   "public_RGBA_earned_opening_ACK")
        let run = NG2Run(owner: "fixture-owner", id: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
            now: setup.started_ns, profile: Self.irregularProfile, yieldAfterRestart: true)
        run.core = core; run.prefix = setup.prefix; run.captureID = setup.latest_id
        run.foreground = true; run.expectedPID = 42; run.captureWorkerDone = true
        run.fast = FastActionHandler(app: XCUIApplication(bundleIdentifier: "fixture-game"))
        run.images = Array(evidence.frames.suffix(4)); run.initial = evidence.frames.first
        run.analyzedFrames = UInt64(setup.frames)
        onControl("Runtime_bookkeeping") {
            self.lock.ng2Locked { self.current = run }; self.cache(run, setup.status)
            self.refreshCycleEvidence(run); self.refreshIrregularEvidence(run)
        }
        let initialInputs = setup.status.inputs, initialMoves = setup.status.moves
        ng2_partial120_arm_target()
        NG2Runtime120Owner.late = variant == "post_guard_late"
        NG2Fake.applyShopGesture = { at in evidence.synthEntry = at; return true }
        NG2RuntimeTestHooks.beforeMainAuthority = { evidence.mainHook = Self.now() }
        func query() -> (NG2ControllerStatus, NG2ControllerCycleStatus) {
            var s = NG2ControllerStatus(), c = NG2ControllerCycleStatus()
            if let core = run.core { ng2_controller_status(core, &s); ng2_controller_cycle_status(core, &c) }
            return (s, c)
        }
        func frame(_ kind: Int32) -> NG2Frame {
            let start = Self.now(); var rgba = Data(count: 896*414*4); let count = rgba.count
            let drawn = rgba.withUnsafeMutableBytes { raw in
                ng2_fixture_queue120_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count, kind, 0,
                    ng2_fixture_partial120_phase(&setup, start))
            }
            let end = Self.now(), analysisStart = Self.now(), analysis = NG2Analysis()
            let returned = rgba.withUnsafeBytes { raw in
                ng2_analyze_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count, 896*4, analysis.scene)
            }
            let companion = rgba.withUnsafeBytes { raw in
                ng2_analyze_irregular_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count, 896*4, 0, &analysis.irregular)
            }
            let analysisEnd = Self.now()
            require120(drawn == 1 && returned == 0 && companion == 0 && analysis.scene.pointee.goods == 1
                && analysis.scene.pointee.state == 2 && analysis.irregular.kind == 0, "normal_RGBA_PARTIAL")
            run.captureID += 1
            let value = NG2Frame(id: run.captureID, start: start, end: end, decodeEnd: end,
                generation: run.generation, analysisStart: analysisStart, analysisEnd: analysisEnd, analysis: analysis,
                startPrefix: run.prefix, prefix: run.prefix, startInFlight: false, endInFlight: false, stable: true,
                rgba: rgba, rasterTrace: NG2Raster.Trace(sourceWidth: 896, sourceHeight: 414, orientation: 1,
                    sourceNs: 0, drawNs: 0, orientNs: 0, scaleNs: 0, copyPixels: 896*414),
                encodedBytes: 0, diagnosticOrientation: 1)
            evidence.frames.append(value); return value
        }
        func consume(_ value: NG2Frame) {
            run.lock.ng2Locked { run.capturePipelineIDs.insert(value.id); run.latest = value }
            self.cycle(run)
            require120(run.lock.ng2Locked { run.latest == nil && !run.capturePipelineIDs.contains(value.id) },
                       "normal_Runtime_consumed_source")
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { job in
            self.controlQueue.sync {
                let c = query().1
                require120(evidence.worker.isEmpty && c.job_id == job && c.worker_started_ns > 0,
                           "one_real_partial_worker")
                evidence.worker = ["job_id": job, "capture_id": c.capture_id,
                    "capture_start_ns": c.capture_start_ns, "prefix": c.prefix, "level_id": c.level_id,
                    "worker_started_ns": c.worker_started_ns, "deadline_ns": c.deadline_ns,
                    "parent_deadline_ns": c.continuation_deadline_ns]
                let owned = run.cycle!.frames[c.capture_id]!
                evidence.worker["raw_sha256"] = NG2CycleWire.hash(owned.rgba)
                evidence.worker["scene_sha256"] = sceneHash120(owned)
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
            evidence.ringMode = mode; evidence.ringStatus = status; evidence.ringOutcome = outcome
            evidence.ringReturn = Self.now()
        }
        NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = { _ in evidence.workerReturned = true }
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { _ in evidence.commitReturned = true }
        NG2RuntimeTestHooks.scheduleTicket = { id, callback in
            require120(evidence.held == nil && evidence.ticket.id == 0, "single_future_ticket")
            let event = run.controllerSnapshot!.events.last!
            require120(event.command.id == id && event.command.kind == 4 && event.command.direction == 1,
                       "public_ordinary_PARTIAL_LEFT_ticket")
            evidence.ticket = event.command; evidence.held = callback
            evidence.scheduled = Self.now()
            NG2Runtime120Owner.deadline = event.command.deadline_ns
            require120(counts120().command_id == id && Self.now() < event.command.not_before_ns,
                       "future_command_without_clock_shift")
            return true
        }
        NG2RuntimeTestHooks.afterTicketReturned = { id in
            require120(id == evidence.ticket.id, "same_callback_return")
            let status = query().0; evidence.finalStatus = status
            evidence.finalEvent = run.controllerSnapshot!.events.first { $0.command.id == id }!
            evidence.ticketReturned = true
            run.cancel(2); if let live = run.core { ng2_controller_cancel(live, Self.now(), 2) }
        }
        // The component ends at this exact dispatch/ACK. Use public cancel
        // before the ordinary terminal-cleanup UI can reserve another input.
        NG2RuntimeTestHooks.beforeControlTick = {
            if counts120().complete_calls == 1 {
                run.cancel(2); if let live = run.core { ng2_controller_cancel(live, Self.now(), 2) }
            }
        }
        NG2RuntimeCycleTestHooks.afterTerminalDrainPass = { _, _, _, _ in
            evidence.lock.ng2Locked {
                evidence.drained = evidence.ticketReturned && !run.lease && run.core == nil
                    && !run.cycle!.workerBusy && run.mainCallbacks.isEmpty
            }
        }
        pump120("opening_response_after_real_target") { Self.now() >= setup.command.target_ns + 100_000_000 }
        onControl("first_Runtime_PARTIAL_source") {
            let source = frame(Int32(NG2_QUEUE120_EARLY)); evidence.firstSource = source.id; consume(source)
        }
        pump120("normal_Ring_adopted_and_both_returns") {
            self.controlQueue.sync {
                evidence.workerReturned && evidence.commitReturned && !run.cycle!.workerBusy
                    && run.cycle!.assessmentAdopted
            }
        }
        controlQueue.sync {
            require120(run.cycle!.assessment?["partial_safe_no_positive"]?.boolValue == true
                && evidence.ringMode == 2 && evidence.ringStatus == 0 && evidence.ringOutcome == 0,
                "normal_partial_safe_UNKNOWN_incomplete")
            evidence.assessmentHash = NG2CycleWire.hash(try! NG2CycleWire.canonical(run.cycle!.assessment!))
        }
        // Fresh independent current images earn credit/fit, never patched state.
        for _ in 0..<12 {
            if evidence.held != nil { break }
            onControl("independent_Runtime_current") { consume(frame(Int32(NG2_QUEUE120_WALL))) }
            if evidence.held == nil { RunLoop.current.run(until: Date().addingTimeInterval(0.015)) }
        }
        require120(evidence.held != nil, "public_future_reservation")
        onControl("reserved_ticket_independent_zero") {
            let before = counts120().motion_calls
            let current = frame(Int32(NG2_QUEUE120_WALL)); evidence.currentSource = current.id; consume(current)
            let after = counts120(); evidence.observeMotionCalls = after.motion_calls - before
            require120(evidence.observeMotionCalls > 0 && after.motion_kind == 2 && after.motion_dx == 0
                && after.motion_dy == 0 && query().0.last_capture_id == current.id
                && current.id > evidence.ticket.source_capture_id, "post_reservation_direct_normal_zero")
        }
        let command = evidence.ticket
        require120(command.deadline_ns - command.not_before_ns <= 10_000_000, "unchanged_10ms_window")
        pump120("real_future_not_before") { Self.now() >= command.not_before_ns }
        require120(Self.now() <= command.deadline_ns, "positive_callback_still_within_frozen_D")
        let callback = evidence.held!; evidence.held = nil; callback()
        pump120("real_callback_and_CANCEL_drain") {
            evidence.lock.ng2Locked { evidence.drained }
        }
        let measured = counts120(), event = evidence.finalEvent
        require120(measured.begin_calls == 1 && measured.begin_accepted == 1
            && measured.begin_motion_calls == 0 && measured.getter_motion_calls == 0,
            "earned_begin_hit_no_repeated_normal_Motion")
        require120(measured.complete_calls == 1 && event.command.id == command.id,
                   "single_real_Runtime_complete")
        let expected = variant == "normal" ? 1 : 0
        require120(NG2Fake.paths().count == expected && NG2Fake.tapPoints.isEmpty, "exact_synth_count")
        if variant == "normal" {
            require120(measured.complete_outcome == 1 && event.outcome == 2
                && measured.begin_exit_ns <= command.deadline_ns
                && command.not_before_ns <= evidence.synthEntry && evidence.synthEntry <= command.deadline_ns
                && evidence.finalStatus.inputs == initialInputs+1, "future_MOVE_known_ACK")
        } else {
            require120(NG2Runtime120Owner.spent && NG2Runtime120Owner.expenseStart >= measured.begin_exit_ns
                && NG2Runtime120Owner.expenseEnd > command.deadline_ns
                && measured.complete_outcome == 0 && event.outcome == 3
                && run.dispatchFailure?["code"]?.stringValue == "too_late"
                && evidence.finalStatus.inputs == initialInputs, "actual_post_guard_certain_NOT_SENT")
        }
        require120(evidence.finalStatus.moves == initialMoves && NG2Fake.offset == 0,
                   "ACK_is_not_MOVED_and_no_clock_offset")
        let observations = run.captures.filter { $0.id >= evidence.firstSource }.map { sample in
            ["id": sample.id, "observe_start_ns": sample.observeStart, "observe_end_ns": sample.observeEnd]
        }
        let result: [String: Any] = ["schema": "ngg2-runtime120-subrun-v1", "case": "partial_begin_dispatch",
            "variant": variant, "clock": "real-monotonic-offset0", "normal_perception": true,
            "normal_ring": true, "actual_runtime_dispatch": true, "scene_override_used": false,
            "result_override_used": false, "physical_game_tested": false, "capture_thread_started": false,
            "setup_component_known_ACK": true, "setup_entry_ns": setup.entry_ns, "setup_return_ns": setup.return_ns,
            "owner_started_ns": setup.started_ns, "accepted_started_ns": run.acceptedStarted,
            "original_opening_ACK": setup.command.id, "source_capture_id": evidence.firstSource,
            "current_capture_id": evidence.currentSource, "command_id": command.id,
            "command_source_capture_id": command.source_capture_id, "ordinal": command.ordinal,
            "not_before_ns": command.not_before_ns, "deadline_ns": command.deadline_ns,
            "observe_motion_calls": evidence.observeMotionCalls, "begin_calls": measured.begin_calls,
            "begin_accepted": measured.begin_accepted, "begin_motion_calls": measured.begin_motion_calls,
            "getter_calls": measured.getter_calls, "getter_motion_calls": measured.getter_motion_calls,
            "getter_cost_ns": measured.getter_ns, "begin_entry_ns": measured.begin_entry_ns,
            "tick_calls": measured.tick_calls, "tick_entry_ns": measured.tick_entry_ns,
            "tick_exit_ns": measured.tick_exit_ns, "scheduled_ns": evidence.scheduled,
            "main_hook_ns": evidence.mainHook, "observations": observations,
            "cost_accounting": "nested-real-clock-intervals-not-an-additive-total",
            "begin_exit_ns": measured.begin_exit_ns, "complete_calls": measured.complete_calls,
            "complete_ns": measured.complete_ns, "complete_outcome": measured.complete_outcome,
            "event_outcome": event.outcome, "synth_moves": NG2Fake.paths().count,
            "synth_entry_ns": evidence.synthEntry, "assessment_sha256": evidence.assessmentHash,
            "guard_expense_start_ns": NG2Runtime120Owner.expenseStart,
            "guard_expense_end_ns": NG2Runtime120Owner.expenseEnd,
            "dispatch_failure": run.dispatchFailure?["code"]?.stringValue ?? "none",
            "normal_motion_cost_ns": measured.motion_ns, "worker": evidence.worker,
            "ring_mode": evidence.ringMode, "ring_status": evidence.ringStatus, "ring_outcome": evidence.ringOutcome,
            "ring_return_ns": evidence.ringReturn, "all_real_workers_drained": !run.cycle!.workerBusy,
            "lease_released": !run.lease, "callback_returned": evidence.ticketReturned,
            "frames": evidence.frameRows]
        let encoded = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("EVIDENCE TEST120 SUBRUN " + String(data: encoded, encoding: .utf8)!)
        print("PASS TEST120 CASE partial_begin_dispatch " + variant)
        NG2RuntimeTestHooks.scheduleTicket = nil; NG2RuntimeTestHooks.afterTicketReturned = nil
        NG2RuntimeTestHooks.beforeControlTick = nil
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        NG2Fake.applyShopGesture = nil
        NG2RuntimeCycleTestHooks.beforeClassification = nil; NG2RuntimeCycleTestHooks.afterClassificationCall = nil
        NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = nil
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = nil
        NG2RuntimeCycleTestHooks.afterTerminalDrainPass = nil
        lock.ng2Locked { if current === run { current = nil } }
    }
}
#endif
