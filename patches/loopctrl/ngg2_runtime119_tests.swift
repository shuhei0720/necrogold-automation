// Appended only to a staged copy of the unchanged production Runtime body.
// The setup earns a normal ACK with public C and normal Perception. All target
// observations then enter the ordinary Runtime cycle, frame retention and Ring.
#if NG2_RUNTIME_HOST_TEST
private func require119(_ condition: @autoclosure () -> Bool, _ name: String) {
    if !condition() { print("FAIL test119_" + name); fflush(stdout); exit(1) }
}
private func pump119(_ name: String, _ predicate: () -> Bool) {
    let until = Date().addingTimeInterval(3)
    while !predicate() && Date() < until {
        RunLoop.current.run(until: Date().addingTimeInterval(0.0005))
    }
    require119(predicate(), name)
}
private func sceneHash119(_ frame: NG2Frame) -> String {
    NG2CycleWire.hash(Data(bytes: frame.analysis.scene, count: MemoryLayout<NG2Scene>.size))
}
private func irregularHash119(_ frame: NG2Frame) -> String {
    withUnsafeBytes(of: frame.analysis.irregular) { NG2CycleWire.hash(Data($0)) }
}
private final class NG2Runtime119Worker {
    let frame: NG2Frame
    let admitted: NG2ControllerCycleStatus
    let index: Int
    var mode: Int32 = -1, status: Int32 = -1, outcome: UInt32 = 99
    var ringReturn: UInt64 = 0, commit: UInt64 = 0, producer: UInt64 = 0, commitReturn: UInt64 = 0
    var adopted = false, producerToken = false, commitToken = false
    init(_ frame: NG2Frame, _ state: NG2ControllerCycleStatus, index: Int) { self.frame = frame; admitted = state; self.index = index }
    func wire() -> [String: Any] {
        ["job_id": admitted.job_id, "capture_id": frame.id, "capture_start_ns": frame.start,
         "prefix": frame.prefix, "generation": frame.generation, "level_id": admitted.level_id,
         "hold_started_ns": admitted.hold_started_ns, "parent_deadline_ns": admitted.continuation_deadline_ns,
         "worker_started_ns": admitted.worker_started_ns,
         "deadline_ns": admitted.deadline_ns, "raw_sha256": NG2CycleWire.hash(frame.rgba),
         "scene_sha256": sceneHash119(frame), "irregular_sha256": irregularHash119(frame), "mode": mode, "fast": 1, "status": status, "outcome": outcome,
         "ring_return_ns": ringReturn, "commit_ns": commit, "producer_hook_ns": producer,
         "commit_return_hook_ns": commitReturn, "adopted": adopted,
         "drain_token_at_producer_return": producerToken, "drain_token_at_commit_return": commitToken]
    }
}
private final class NG2Runtime119Evidence {
    let lock = NSLock()
    var frames: [NG2Frame] = []
    var workers: [NG2Runtime119Worker] = []
    var active: NG2Runtime119Worker?
    var earlyID: UInt64 = 0, lateID: UInt64 = 0, queuedID: UInt64 = 0
    var hold: UInt64 = 0, parent: UInt64 = 0, level: UInt64 = 0
    var inputs: Int32 = 0, moves: Int32 = 0
    var earlyMoves: Int32 = -1, earlyInputState: Int32 = -1, earlyMotion: Int32 = -1
    var earlyObserved: UInt64 = 0
    var before: NG2Frame?
    var motions: [[String: Any]] = []
    var queuedImmutable = false, fences = true, sourceIdentity = true, parentPreserved = true
    var lateCredit = false, lateToken = false, queuedAdopted = false
    var candidateLatched = false, candidateSourcePreserved = false, cancelled = false
    func frameWire(_ frame: NG2Frame) -> [String: Any] {
        ["id": frame.id, "start_ns": frame.start, "end_ns": frame.end, "prefix": frame.prefix,
         "generation": frame.generation, "analysis_start_ns": frame.analysisStart,
         "analysis_end_ns": frame.analysisEnd, "raw_sha256": NG2CycleWire.hash(frame.rgba),
         "scene_sha256": sceneHash119(frame), "irregular_sha256": irregularHash119(frame),
         "irregular_kind": frame.analysis.irregular.kind, "state": frame.analysis.scene.pointee.state,
         "goods": frame.analysis.scene.pointee.goods, "gold_state": frame.analysis.scene.pointee.gold_state,
         "tiles_sha256": withUnsafeBytes(of: frame.analysis.scene.pointee.tiles) { NG2CycleWire.hash(Data($0)) },
         "protected_sha256": withUnsafeBytes(of: frame.analysis.scene.pointee.protected_cells) { NG2CycleWire.hash(Data($0)) }]
    }
}
private func retainQueue119Setup(_ context: UnsafeMutableRawPointer?, _ id: UInt64,
    _ start: UInt64, _ end: UInt64, _ prefix: UInt64, _ kind: Int32,
    _ raw: UnsafePointer<UInt8>?, _ length: Int, _ scene: UnsafePointer<NG2Scene>?,
    _ irregular: UnsafePointer<NG2IrregularObservation>?) {
    guard let context, let raw, let scene, let irregular else { require119(false, "setup_callback_valid"); return }
    let evidence = Unmanaged<NG2Runtime119Evidence>.fromOpaque(context).takeUnretainedValue()
    let analysis = NG2Analysis(); analysis.scene.pointee = scene.pointee; analysis.irregular = irregular.pointee
    let frame = NG2Frame(id: id, start: start, end: end, decodeEnd: end, generation: 1,
        analysisStart: end, analysisEnd: end, analysis: analysis, startPrefix: prefix, prefix: prefix,
        startInFlight: false, endInFlight: false, stable: true, rgba: Data(bytes: raw, count: length),
        rasterTrace: NG2Raster.Trace(sourceWidth: 896, sourceHeight: 414, orientation: 1,
            sourceNs: 0, drawNs: 0, orientNs: 0, scaleNs: 0, copyPixels: 896*414),
        encodedBytes: 0, diagnosticOrientation: 1)
    evidence.frames.append(frame)
    if kind == Int32(NG2_QUEUE119_BEFORE) { evidence.before = frame }
}
extension NG2Runtime {
    func test119EnteredCurrentQueue(_ variant: String) {
        require119(["normal", "candidate"].contains(variant), "known_variant")
        NG2Fake.reset(.empty)
        NG2RuntimeTestHooks.clock = nil
        NG2RuntimeCycleTestHooks.classificationResult = nil
        NG2RuntimeCycleTestHooks.rgba = nil
        NG2RuntimeEvidenceTestHooks.snapshot = nil
        let evidence = NG2Runtime119Evidence()
        var setup = NG2Queue119Setup()
        require119(ng2_fixture_queue119_prepare() == 1, "own_normal_Perception_setup_pixels_prepared")
        let setupEntry = Self.now()
        guard let core = ng2_fixture_queue119_setup(setupEntry, retainQueue119Setup,
            Unmanaged.passUnretained(evidence).toOpaque(), &setup) else {
            require119(false, "public_RGBA_setup_earned_ACK_error_" + String(setup.error)); return
        }
        let setupReturned = Self.now()
        evidence.before = evidence.frames.first { $0.id == setup.command.source_capture_id }
        require119(evidence.before?.start == setup.command.source_start_ns
            && evidence.before?.analysis.scene.pointee.goods == Int32(NG2_GOODS_UNKNOWN),
            "original_ACK_source_is_same_public_observed_RGBA")
        require119(setup.error == 0 && setup.normal_units >= 1 && setup.opened_units >= 1,
                   "public_normal_ACK_and_door_earned")
        require119(setup.status.last_completed_id == setup.prefix && setup.status.last_capture_id == setup.latest_id
            && setup.status.started_ns == setup.started_ns && setup.status.input_state == 3,
            "setup_same_public_status_metadata")
        require119(setup.cycle.pending == 0 && setup.cycle.candidate_latched == 0,
                   "setup_does_not_prebuild_target_token_or_result")
        let identity = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let run = NG2Run(owner: "fixture-owner", id: identity, now: setup.started_ns,
                        profile: Self.irregularProfile, yieldAfterRestart: true)
        run.core = core; run.prefix = setup.prefix; run.captureID = setup.latest_id
        run.foreground = true; run.expectedPID = 42; run.captureWorkerDone = true
        run.images = Array(evidence.frames.suffix(4)); run.initial = evidence.frames.first
        run.analyzedFrames = UInt64(setup.frames)
        evidence.inputs = setup.status.inputs; evidence.moves = setup.status.moves
        controlQueue.sync {
            self.lock.ng2Locked { self.current = run }
            self.cache(run, setup.status)
            self.refreshCycleEvidence(run)
            self.refreshIrregularEvidence(run)
            require119(run.cycle!.companion.capture_id == setup.cycle.capture_id
                && run.cycle!.companion.job_id == setup.cycle.job_id && run.acceptedStarted == setup.status.started_ns,
                "runtime_bookkeeping_derived_from_same_public_setup")
        }
        func query() -> (NG2ControllerStatus, NG2ControllerCycleStatus, NG2ControllerStopDetail) {
            var status = NG2ControllerStatus(), cycle = NG2ControllerCycleStatus(), stop = NG2ControllerStopDetail()
            if let currentCore = run.core {
                ng2_controller_status(currentCore, &status); ng2_controller_cycle_status(currentCore, &cycle)
                ng2_controller_stop_detail(currentCore, &stop)
            }
            return (status, cycle, stop)
        }
        func createFrame(_ kind: Int32) -> NG2Frame {
            let start = Self.now()
            var bytes = Data(count: 896*414*4); let count = bytes.count
            let q = ng2_fixture_queue119_phase(&setup, start)
            let drawn = bytes.withUnsafeMutableBytes { raw in
                ng2_fixture_queue119_rgba(raw.bindMemory(to: UInt8.self).baseAddress,
                    count, kind, variant == "candidate" ? 1 : 0, q)
            }
            require119(drawn == 1, "new_procedural_RGBA_factory")
            let end = Self.now(), analysisStart = Self.now(), analysis = NG2Analysis()
            let analyzed = bytes.withUnsafeBytes { raw in
                ng2_analyze_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count, 896*4, analysis.scene)
            }
            let irregularAnalyzed = bytes.withUnsafeBytes { raw in
                ng2_analyze_irregular_rgba(raw.bindMemory(to: UInt8.self).baseAddress, count, 896*4, 0, &analysis.irregular)
            }
            let analysisEnd = Self.now()
            require119(irregularAnalyzed == 0 && analysis.irregular.kind == Int32(NG2_IRREGULAR_IMAGE_NONE),
                       "new_RGBA_normal_irregular_observation_NONE")
            require119(analyzed == 0 && analysis.scene.pointee.state == Int32(NG2_FLOOR)
                && analysis.scene.pointee.goods == 2, "new_RGBA_normal_Perception_FULL")
            run.captureID += 1
            let frame = NG2Frame(id: run.captureID, start: start, end: end, decodeEnd: end, generation: run.generation,
                analysisStart: analysisStart, analysisEnd: analysisEnd, analysis: analysis,
                startPrefix: run.prefix, prefix: run.prefix, startInFlight: false, endInFlight: false, stable: true,
                rgba: bytes, rasterTrace: NG2Raster.Trace(sourceWidth: 896, sourceHeight: 414, orientation: 1,
                    sourceNs: 0, drawNs: 0, orientNs: 0, scaleNs: 0, copyPixels: 896*414),
                encodedBytes: 0, diagnosticOrientation: 1)
            evidence.lock.ng2Locked { evidence.frames.append(frame) }
            return frame
        }
        // Called on controlQueue only. The normal production consumer installs
        // the Scene, caches public status and fills cycle.frames itself.
        func consume(_ frame: NG2Frame) {
            run.lock.ng2Locked {
                require119(run.latest == nil && run.capturePipelineIDs.isEmpty, "one_normal_latest_frame")
                run.capturePipelineIDs.insert(frame.id); run.latest = frame
            }
            self.cycle(run)
            require119(run.lock.ng2Locked { run.latest == nil && !run.capturePipelineIDs.contains(frame.id) },
                       "normal_cycle_consumes_new_frame")
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { job in
            self.controlQueue.sync {
                let state = query().1
                require119(state.job_id == job && state.worker_started_ns > 0 && state.capture_id > 0,
                           "real_Runtime_worker_admission")
                guard let frame = run.lock.ng2Locked({ run.cycle!.frames[state.capture_id] }) else {
                    require119(false, "Runtime_lease_retains_original_frame"); return
                }
                require119(frame.start == state.capture_start_ns && frame.prefix == state.prefix && frame.generation == 1,
                           "immutable_lease_identity")
                let worker = NG2Runtime119Worker(frame, state, index: evidence.workers.count)
                if let previous = evidence.workers.last {
                    require119(previous.producer > 0 && previous.commitReturn > 0
                        && state.worker_started_ns >= max(previous.producer, previous.commitReturn),
                        "next_worker_after_actual_old_producer_and_commit_return")
                }
                evidence.lock.ng2Locked { evidence.workers.append(worker); evidence.active = worker }
                if frame.id == evidence.lateID {
                    let status = query().0
                    require119(status.inputs == evidence.inputs && status.moves == evidence.moves+1
                        && state.job_id > setup.cycle.job_id && state.capture_id == evidence.lateID,
                        "late_entered_original_ACK_unit_once_before_candidate")
                    let credited = run.controllerSnapshot!.events.last!
                    require119(credited.command.id == setup.command.id && credited.outcome == 2
                        && credited.motion == Int32(NG2_MOVED) && credited.dx == -1 && credited.dy == 0
                        && credited.observed_capture_id == evidence.lateID,
                        "same_original_ACK_event_owns_late_unit_credit")
                    evidence.lateCredit = true; evidence.lateToken = true
                    evidence.parentPreserved = evidence.parentPreserved && state.hold_started_ns == evidence.hold
                        && state.continuation_deadline_ns > 0 && state.continuation_deadline_ns <= evidence.parent && state.level_id == evidence.level
                        && state.prefix == setup.prefix
                    let queued = createFrame(Int32(NG2_QUEUE119_WALL)); evidence.queuedID = queued.id
                    var motion = NG2Motion()
                    ng2_motion(frame.analysis.scene, queued.analysis.scene, Int32(NG2_LEFT), &motion)
                    require119(motion.kind == Int32(NG2_BLOCKED) && motion.dx == 0 && motion.dy == 0,
                               "new_remote_GOLD_is_normal_strict_zero")
                    evidence.motions.append(["before": frame.id, "after": queued.id,
                        "direction": 1, "kind": motion.kind, "dx": motion.dx, "dy": motion.dy])
                    consume(queued)
                    let pending = query().1
                    evidence.queuedImmutable = pending.job_id == job && pending.capture_id == frame.id
                        && pending.capture_start_ns == frame.start && pending.queued_capture_id == queued.id
                        && pending.queued_capture_start_ns == queued.start && pending.queued_prefix == queued.prefix
                    require119(evidence.queuedImmutable, "pending_old_worker_keeps_immutable_source_and_queues_new_RGBA")
                }
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
            evidence.lock.ng2Locked {
                guard let worker = evidence.active else { require119(false, "real_Ring_has_active_job"); return }
                worker.mode = mode; worker.status = status; worker.outcome = outcome; worker.ringReturn = Self.now()
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassificationCommit = { job in
            evidence.lock.ng2Locked {
                require119(evidence.active?.admitted.job_id == job, "real_commit_same_job")
                evidence.active?.commit = Self.now()
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { job in
            let state = query().1
            let row = evidence.lock.ng2Locked { evidence.workers.first { $0.admitted.job_id == job }! }
            row.commitReturn = Self.now(); row.commit = row.commitReturn
            row.commitToken = run.lock.ng2Locked { run.cycle!.classificationDrainTokens.values.contains { $0.job == job } }
            row.adopted = run.lock.ng2Locked { run.cycle!.assessmentAdopted }
                || (state.job_id > job && state.capture_id == evidence.queuedID && state.pending == 1)
            require119(row.commitToken && row.adopted, "actual_C_adoption_with_real_commit_return_token")
            if row.frame.id == evidence.earlyID {
                evidence.hold = state.hold_started_ns; evidence.parent = state.continuation_deadline_ns
                evidence.level = state.level_id
                require119(row.outcome == UInt32(NG2_RING_UNKNOWN) && evidence.hold > 0 && evidence.parent > evidence.hold,
                           "early_FULL_real_Ring_UNKNOWN_and_original_parent")
            }
            let final = variant == "candidate" ? row.frame.id == evidence.lateID : row.frame.id == evidence.queuedID
            if final {
                let current = query()
                evidence.parentPreserved = evidence.parentPreserved && current.1.hold_started_ns == evidence.hold
                    && current.1.continuation_deadline_ns > 0 && current.1.continuation_deadline_ns <= evidence.parent && current.1.level_id == evidence.level
                if variant == "candidate" {
                    evidence.candidateLatched = current.1.candidate_latched == 1
                        && [UInt32(NG2_RING_CANDIDATE), UInt32(NG2_RING_TARGET)].contains(row.outcome)
                    evidence.candidateSourcePreserved = current.1.job_id == job && current.1.capture_id == evidence.lateID
                    require119(evidence.lateToken && evidence.candidateLatched && evidence.candidateSourcePreserved,
                               "pending_DATA_actual_candidate_wins_over_queued_material")
                } else {
                    evidence.queuedAdopted = row.adopted && row.frame.id == evidence.queuedID
                        && current.1.capture_id == evidence.queuedID
                    require119(evidence.queuedAdopted && current.2.anchor_capture_id == evidence.queuedID,
                               "new_classified_RGBA_owns_public_full_source_anchor")
                }
                require119(current.0.inputs == evidence.inputs && current.0.moves == evidence.moves+1,
                           "no_new_input_during_DATA_workers")
                // Public cancellation at this real return boundary prevents any
                // later UI reservation; the actual producer/control tokens drain.
                let cancelled = self.handle(method: "necro_native_cancel", params:
                    ["run_id": .string(run.id), "_necro_owner": .string(run.owner)])
                require119(cancelled.1 == nil, "public_cancel_accepted")
                evidence.cancelled = true
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = { job in
            // The commit was enqueued before this hook. FIFO sync waits for its
            // real return while this real producer closure still owns its token.
            self.controlQueue.sync {
                let row = evidence.lock.ng2Locked { evidence.workers.first { $0.admitted.job_id == job }! }
                row.producer = Self.now()
                row.producerToken = run.lock.ng2Locked {
                    run.cycle!.classificationDrainTokens.values.contains { $0.job == job }
                }
                let count = evidence.lock.ng2Locked { evidence.workers.count }
                evidence.fences = evidence.fences && row.producerToken && row.commitToken
                    && count == row.index+1
                require119(row.producerToken, "old_producer_real_return_fence_keeps_token")
            }
        }
        // This component never starts capture/backend/UI threads or timers.
        // The normal target frame consumer and both real worker queues are live.
        controlQueue.sync {
            let early = createFrame(Int32(NG2_QUEUE119_EARLY)); evidence.earlyID = early.id
            guard let before = evidence.before else { require119(false, "setup_before_RGBA_exists"); return }
            var motion = NG2Motion(); ng2_motion(before.analysis.scene, early.analysis.scene, Int32(NG2_LEFT), &motion)
            require119(motion.kind == Int32(NG2_MOTION_UNKNOWN), "early_FULL_normal_motion_ambiguous")
            evidence.motions.append(["before": before.id, "after": early.id,
                "direction": 1, "kind": motion.kind, "dx": motion.dx, "dy": motion.dy])
            consume(early)
            let earlyState = query()
            let earlyEvent = run.controllerSnapshot!.events.last!
            evidence.earlyMoves = earlyState.0.moves; evidence.earlyInputState = earlyState.0.input_state
            evidence.earlyMotion = earlyEvent.motion; evidence.earlyObserved = earlyEvent.observed_capture_id
            require119(earlyState.0.moves == evidence.moves && earlyState.0.inputs == evidence.inputs
                && earlyState.0.input_state == 0 && earlyEvent.command.id == setup.command.id
                && earlyEvent.motion == Int32(NG2_MOTION_UNKNOWN) && earlyEvent.dx == 0 && earlyEvent.dy == 0
                && earlyEvent.observed_capture_id == early.id,
                "early_FULL_closes_actual_C_ACK_UNKNOWN_without_fallback_credit")
        }
        pump119("early_real_worker_and_both_returns") {
            self.controlQueue.sync {
                evidence.workers.count == 1 && run.lock.ng2Locked { !run.cycle!.workerBusy }
            }
        }
        let lateEarliest = controlQueue.sync { () -> UInt64 in
            let early = evidence.frames.first { $0.id == evidence.earlyID }!
            let state = query().1
            return max(early.end + setup.period_ns/10, state.release_after_ns)
        }
        require119(lateEarliest <= evidence.parent, "independent_late_source_within_original_parent")
        // Keep the unchanged independent-sample interval on the real clock.
        // This elapsed wait is charged to the old visual and parent bounds.
        pump119("normal_independent_late_capture_interval") { Self.now() >= lateEarliest }
        controlQueue.sync {
            let late = createFrame(Int32(NG2_QUEUE119_LATE)); evidence.lateID = late.id
            var motion = NG2Motion(); ng2_motion(evidence.before!.analysis.scene, late.analysis.scene,
                                               Int32(NG2_LEFT), &motion)
            require119(motion.kind == Int32(NG2_MOVED) && motion.dx == -1 && motion.dy == 0,
                       "late_RGBA_normal_LEFT_unit")
            evidence.motions.append(["before": evidence.before!.id, "after": late.id,
                "direction": 1, "kind": motion.kind, "dx": motion.dx, "dy": motion.dy])
            consume(late)
        }
        pump119("public_cancel_and_actual_worker_lease_drain") {
            self.controlQueue.sync {
                run.lock.ng2Locked { !run.lease && !run.cycle!.workerBusy && run.core == nil }
            }
        }
        let committedFrames = controlQueue.sync { run.captures }
        evidence.sourceIdentity = evidence.frames.filter { $0.id >= evidence.earlyID }.allSatisfy { frame in
            committedFrames.contains { sample in sample.id == frame.id && sample.start == frame.start
                && sample.end == frame.end && sample.prefix == frame.prefix && sample.startPrefix == frame.startPrefix
                && sample.stable && !sample.startInFlight && !sample.endInFlight }
        }
        require119(evidence.sourceIdentity, "actual_Runtime_observe_committed_same_new_frame_metadata")
        NG2RuntimeCycleTestHooks.beforeClassification = nil
        NG2RuntimeCycleTestHooks.afterClassificationCall = nil
        NG2RuntimeCycleTestHooks.beforeClassificationCommit = nil
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = nil
        NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = nil
        require119(evidence.workers.count == (variant == "normal" ? 3 : 2), "exact_real_worker_count")
        let extraInputReservations = (run.controllerSnapshot?.events ?? []).filter { $0.command.id > setup.command.id }
        require119(extraInputReservations.isEmpty, "no_extra_C_input_reservation_after_setup")
        require119(NG2Fake.paths().isEmpty && NG2Fake.tapPoints.isEmpty && run.mainCallbacks.isEmpty,
                   "no_future_MOVE_RESTART_or_UI_dispatch")
        let result: [String: Any] = ["schema": "ngg2-runtime119-subrun-v1", "case": "entered_current_queue", "variant": variant,
            "clock": "real-monotonic-offset0-after-earned-setup", "normal_perception": true, "normal_ring": true,
            "runtime_profile": run.profile, "yield_after_restart": run.yieldAfterRestart,
            "normal_irregular_analysis": true,
            "actual_runtime_cycle": true, "new_frames_via_latest": true, "same_public_setup_bookkeeping": true,
            "original_parent_preserved": evidence.parentPreserved, "old_worker_return_fences": evidence.fences,
            "queued_immutable_until_result": evidence.queuedImmutable, "source_identity_bound": evidence.sourceIdentity,
            "result_override_used": false, "scene_override_used": false, "capture_thread_started": false,
            "physical_game_tested": false, "late_unit_credited_once": evidence.lateCredit,
            "late_token_before_candidate": evidence.lateToken, "new_queued_source_adopted": evidence.queuedAdopted,
            "candidate_latched": evidence.candidateLatched, "candidate_source_preserved": evidence.candidateSourcePreserved,
            "cancelled": evidence.cancelled, "all_real_workers_drained": !run.cycle!.workerBusy,
            "lease_released": !run.lease, "no_future_move_or_restart": NG2Fake.paths().isEmpty && extraInputReservations.isEmpty,
            "extra_input_reservations": extraInputReservations.count,
            "early_capture_id": evidence.earlyID, "late_capture_id": evidence.lateID, "queued_capture_id": evidence.queuedID,
            "hold_started_ns": evidence.hold, "parent_deadline_ns": evidence.parent,
            "owner_started_ns": setup.started_ns, "accepted_started_ns": run.acceptedStarted,
            "setup_entry_ns": setupEntry, "setup_return_ns": setupReturned,
            "setup_replay_actual_cost_ns": setupReturned-setupEntry,
            "setup_prefix": setup.prefix, "setup_latest_capture_id": setup.latest_id,
            "original_ack_command_id": setup.command.id, "original_ack_source_capture_id": setup.command.source_capture_id,
            "original_ack_source_start_ns": setup.command.source_start_ns, "original_ack_ns": setup.ack_ns,
            "original_ack_target_ns": setup.command.target_ns, "before_capture_id": evidence.before!.id,
            "original_inputs": evidence.inputs, "original_moves": evidence.moves,
            "early_moves": evidence.earlyMoves, "early_input_state": evidence.earlyInputState,
            "early_ack_motion": evidence.earlyMotion, "early_ack_observed_capture_id": evidence.earlyObserved,
            "setup_public_frame_count": setup.frames, "setup_normal_units": setup.normal_units,
            "setup_opened_units": setup.opened_units,
            "frames": evidence.frames.map(evidence.frameWire), "motion_proofs": evidence.motions,
            "workers": evidence.workers.map { $0.wire() }]
        let encoded = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("EVIDENCE TEST119 SUBRUN " + String(data: encoded, encoding: .utf8)!)
        print("PASS TEST119 CASE entered_current_queue " + variant)
        lock.ng2Locked { if current === run { current = nil } }
    }
}
#endif
