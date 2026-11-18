// TEST115 actual callback boundaries. The clock, game and future pixels are
// procedural. CLEAR-passage admission is separately checked by public-C
// tests; this first case checks its existing FRESH preparation mechanism.
func runtime115Emit(_ kind: String, _ value: [String: JSONValue]) {
    if let bytes = try? JSONEncoder().encode(value), let text = String(data: bytes, encoding: .utf8) {
        print("EVIDENCE TEST115 " + kind + " " + text)
    } else { require(false, "test115_typed_evidence_encodes") }
}
func testRuntime115Preparation(_ root: URL) {
    runtime112Reset(root)
    // The shared cycle reset installs a FULL-goods RGBA override. This case
    // uses the native walking renderer and must keep its real no-goods view.
    NG2RuntimeCycleTestHooks.rgba = nil
    NG2Fake.lock.lock()
    NG2Fake.walkPaused = false; NG2Fake.walkY = 2; NG2Fake.walkGoodsEnabled = false
    NG2Fake.freshRevalidationWorld = true
    NG2Fake.lock.unlock()
    let id = identity(), interval: UInt64 = 54_008_584
    let beforeNotBefore: UInt64 = 49_974_003, afterNotBefore: UInt64 = 4_034_581
    diagnoseFixture(id); alignInitialFixtureMove(id)
    let fence = test060_RevalidationImageFence(x: 340, y: 243, rgb: (199, 164, 63), noisy: true)
    NG2RuntimeTestHooks.analysisRGBA = { fence.inspect($0) }
    var queries = [Int: [UInt64]](), oldID: UInt64 = 0, newID: UInt64 = 0
    var refreshCommit: UInt64 = 0, oldReturn: UInt64 = 0, newMain: UInt64 = 0
    var oldPrepared = [UInt64](), newPrepared = [UInt64]()
    // Once C has published the third reservation, stop the NEXT camera
    // admission before its ordinary clock quantum. Main preparation may
    // then finish while the original ticket and its absolute window stay
    // frozen. The one explicit refresh below owns the next capture permit.
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        let current = report(id)
        if current["inputs"]?.intValue == 2 && current["moves"]?.intValue == 2 &&
            current["input_state"]?.intValue == 1 {
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        }
        test060_revalidationCaptureBoundary()
    }
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        let command = report(id)["current_command_id"]?.intValue ?? 0
        queries[command, default: []].append(NG2Fake.virtualClock())
    }
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.afterTicketReturned = { returned in
        NG2Fake.lock.lock(); NG2Fake.returnedTickets.insert(returned); NG2Fake.lock.unlock()
        if oldID == 0 && newID == 0 && report(id)["inputs"]?.intValue == 2 {
            // The earlier 82ms camera quantum can spend the whole source
            // refresh interval while main's preparation is returning. Keep
            // normal moving pixels/HUD, but observe the next known unit at
            // a 22ms cadence before freezing the published third ticket.
            NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 20_000_000; NG2Fake.lock.unlock()
        }
        if returned == oldID { oldReturn = NG2Fake.virtualClock() }
        if returned == newID && newID != 0 {
            _ = call("necro_native_cancel", id)
            NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let snapshot = report(id)
        let events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }),
              event["kind"]?.intValue == 4 else { fence.releaseForNonMove(); return false }
        if (snapshot["inputs"]?.intValue ?? 0) < 2 {
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: command) }
            callback(); return true
        }
        NG2Fake.holdTicket(command, callback); fence.arm(command)
        if oldID == 0 {
            oldID = command
            oldPrepared = runtime.testPreparedAuthority(id, commandID: command) ?? []
            guard let boundary = event["not_before_ns"]?.intValue, boundary > Int(beforeNotBefore)+2_000_000 else {
                require(false, "test115_original_fresh_ticket_has_positive_refresh_window"); return true
            }
            require(NG2Fake.changeClockAtCaptureBoundary {
                let at = UInt64(boundary)-beforeNotBefore-2_000_000, now = NG2Fake.virtualClock()
                require(now <= at, "test115_original_window_not_moved_to_fit_refresh")
                if now < at { NG2Fake.advance(at-now) }
                NG2Fake.lock.lock()
                NG2Fake.freshRevalidationVariant = 1; NG2Fake.fixedCaptureAdvance = 0
                NG2Fake.captureLimit = NG2Fake.requests+1
                NG2Fake.lock.unlock()
            }, "test115_refresh_at_existing_capture_boundary")
        } else {
            newID = command; refreshCommit = NG2Fake.virtualClock()
            newPrepared = runtime.testPreparedAuthority(id, commandID: command) ?? []
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        }
        return true
    }
    require(call("necro_native_start", id).1 == nil, "test115_existing_fresh_callback_public_start")
    pump("test115_two_confirmed_moves_then_new_fresh_id", timeout: 30) {
        newID != 0 || report(id)["terminal"]?.intValue == 1
    }
    let before = report(id)
    let events = (before["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let old = events.first(where: { $0["id"]?.intValue == Int(oldID) }),
          let fresh = events.first(where: { $0["id"]?.intValue == Int(newID) }) else {
        require(false, "test115_real_old_and_new_fresh_events_exist"); return
    }
    require(oldID != 0 && newID > oldID && before["inputs"]?.intValue == 2 && before["moves"]?.intValue == 2 &&
        old["outcome"]?.intValue == 3 && old["begin_ns"]?.intValue == 0 &&
        ["target_ns", "not_before_ns", "deadline_ns", "ordinal"].allSatisfy({ old[$0] == fresh[$0] }) &&
        old["source_capture_id"] != fresh["source_capture_id"],
        "test115_latest_fresh_id_keeps_original_window_and_no_old_input_credit")
    require(oldPrepared.count == 4 && newPrepared == oldPrepared &&
        queries[Int(oldID)]?.count == 1 && queries[Int(newID)] == nil,
        "test115_actual_runtime_reuses_opaque_epoch_and_original_ax_sample")
    let count = NG2Fake.countTouches(), paths = NG2Fake.paths().count
    NG2RuntimeTestHooks.beforeMainAuthority = { require(false, "test115_stale_callback_never_reaches_final_gate") }
    NG2Fake.releaseTicket(oldID)
    pump("test115_actual_old_callback_returns_before_new_main") { oldReturn != 0 }
    require(NG2Fake.countTouches() == count && NG2Fake.paths().count == paths &&
        report(id)["events"] == before["events"] && report(id)["current_command_id"]?.intValue == Int(newID),
        "test115_old_return_cannot_touch_or_complete_new_reservation")
    NG2RuntimeTestHooks.beforeMainAuthority = {
        admitFirstFixtureMove(id, expectedID: newID, afterAlignment: { at in
            let actual = UInt64(fresh["not_before_ns"]!.intValue!)+afterNotBefore
            require(at <= actual, "test115_actual_begin_offset_not_rescheduled")
            if at < actual { NG2Fake.advance(actual-at) }
        })
        newMain = NG2Fake.virtualClock()
        require(newMain-refreshCommit == interval && oldReturn <= newMain &&
            refreshCommit == UInt64(fresh["not_before_ns"]!.intValue!)-beforeNotBefore &&
            newMain <= UInt64(fresh["deadline_ns"]!.intValue!),
            "test115_actual_new_main_54ms_after_refresh_inside_unchanged_deadline")
    }
    NG2Fake.releaseTicket(newID)
    pump("test115_new_actual_ack_and_all_callbacks_drained", timeout: 30) { drained(id) }
    let final = report(id)
    let finalEvents = (final["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let sent = finalEvents.first(where: { $0["id"]?.intValue == Int(newID) }) ?? [:]
    require(final["inputs"]?.intValue == 3 && final["moves"]?.intValue == 2 &&
        sent["outcome"]?.intValue == 2 && sent["motion"]?.intValue == 0 &&
        old["begin_ns"]?.intValue == 0 && NG2Fake.paths().count == paths+1,
        "test115_one_new_gesture_no_invented_motion_or_unknown_resend")
    var evidence = [String: JSONValue]()
    for (prefix, event) in [("old", old), ("new", fresh)] {
        for key in ["source_capture_id", "target_ns", "not_before_ns", "deadline_ns", "ordinal"] {
            evidence[prefix+"_"+key] = event[key]
        }
    }
    evidence["old_command_id"] = .int(Int(oldID)); evidence["new_command_id"] = .int(Int(newID))
    evidence["refresh_commit_ns"] = .int(Int(refreshCommit)); evidence["old_return_ns"] = .int(Int(oldReturn))
    evidence["new_main_admission_ns"] = .int(Int(newMain))
    for (prefix, prepared) in [("old", oldPrepared), ("new", newPrepared)] {
        for (index, key) in ["query_start_ns", "query_end_ns", "prepared_command_id", "epoch"].enumerated() {
            evidence[prefix+"_"+key] = .int(Int(prepared[index]))
        }
    }
    evidence["old_begin_count"] = .int(finalEvents.filter { $0["id"]?.intValue == Int(oldID) && ($0["begin_ns"]?.intValue ?? 0) > 0 }.count)
    evidence["new_begin_count"] = .int(finalEvents.filter { $0["id"]?.intValue == Int(newID) && ($0["begin_ns"]?.intValue ?? 0) > 0 }.count)
    runtime115Emit("PREPARATION", evidence)
    let sources = Set([old["source_capture_id"]!.intValue!, fresh["source_capture_id"]!.intValue!])
    let result = call("necro_native_results", id)
    let exported = Set((result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    require(result.1 == nil && sources.isSubset(of: exported), "test115_fresh_actual_export_retains_both_sources_after_drain")
    fixtureFailureSnapshot = nil
}

func runtime115InstallPartial(_ world: Runtime114CurrentWorld) {
    world.install()
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused, epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
        if paused { return original }
        let stage = world.locked { world.stage }
        require((0...4).contains(stage), "test115_partial_renderer_has_finite_pose")
        let now = NG2Fake.virtualClock(), midpoint = now > 1_000_000 ? now-1_000_000 : now
        let elapsed = midpoint >= epoch ? midpoint-epoch : 0, period: UInt64 = 520_000_000
        let fraction = Double(period-1-(elapsed % period))/Double(period)
        var rgba = Data(count: 896*414*4); let count = rgba.count
        rgba.withUnsafeMutableBytes { raw in
            require(ng2_fixture_partial115_rgba(raw.bindMemory(to: UInt8.self).baseAddress,
                count, Int32(stage), fraction) == 1, "test115_normal_partial_pixel_renderer")
        }
        if stage >= 2 {
            world.locked {
                require(world.decodeID > 0 && world.rendered.count < 32, "test115_partial_capture_inventory_is_bounded")
                world.rendered[world.decodeID] = (stage, rgba)
            }
        }
        return rgba
    }
    // The received failure is AFTER adoption of the old normal UNKNOWN.
    // Hold its producer return, then reveal the one-pixel top refinement.
    // This does not broaden C into a pending-old-result admission policy.
    NG2RuntimeCycleTestHooks.beforeClassification = { job in
        NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 1_000; NG2Fake.lock.unlock()
        let state = cycleCompanion(world.id), capture = UInt64(state["capture_id"]?.intValue ?? 0)
        runtime114Admission(world.id, state)
        require(state["job_id"]?.intValue == Int(job), "test115_partial_real_job_owns_exact_current_source")
        guard let actual = runtime.testOriginalFrameEvidence(world.id, captureIDs: [capture])?[capture],
              let raw = NG2Raster.decode(actual.0) else {
            require(false, "test115_partial_normal_worker_original_pixels_available"); return
        }
        world.locked {
            world.activeJob = job; world.workers.append(job); world.sources[capture] = raw
            world.sourceMetadata[capture] = actual.1
            if world.oldJob == 0 { world.oldJob = job; world.oldState = state }
            else if world.currentJob == 0 { world.currentJob = job; world.currentState = state }
        }
        require(actual.1["stable_prefix"]?.boolValue == true &&
            actual.1["inflight_start"]?.boolValue == false && actual.1["inflight_end"]?.boolValue == false &&
            actual.1["completed_prefix_start"] == state["prefix"] &&
            actual.1["completed_prefix_end"] == state["prefix"] &&
            actual.1["capture_start_ns"] == state["capture_start_ns"],
            "test115_partial_source_interval_and_prefix_are_original")
    }
    NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { job in
        if world.locked({ job == world.oldJob }) {
            // This hook is ON controlQueue. Returning it is necessary for
            // the subsequent real captures to reach C.observe. The separate
            // producer return remains parked and owns the actual drain token.
            world.locked { world.stage = 3 }
        } else if world.locked({ job == world.currentJob }) {
            world.locked { world.currentCommitParked = true }
            world.park(world.currentCommitRelease, "test115_current_partial_commit")
        } else { world.locked { world.restoreClock = true } }
    }
}

func testRuntime115Partial(_ root: URL, cancel: Bool) {
    runtime112Reset(root)
    let id = identity(), world = Runtime114CurrentWorld(id)
    defer { world.releaseAll() }
    runtime115InstallPartial(world); runtime112Start(id)
    pump("test115_adopted_old_partial_then_two_current_frames", timeout: 45) {
        world.locked { world.oldReady && world.oldProducerParked }
    }
    world.locked {
        world.frozenCredit = runtime114Credit(report(id)); world.frozenTouches = NG2Fake.countTouches()
        world.frozenPaths = NG2Fake.paths().count
    }
    require(world.frozenPaths == 2 && report(id)["moves"]?.intValue == 1 &&
        report(id)["door_changes"]?.intValue == 1 && world.locked({ world.workers.count == 1 }),
        "test115_normal_first_move_then_opening_precede_old_partial")
    let queued = cycleCompanion(id), old = world.locked { world.oldState }
    require(queued["job_id"]?.intValue != old["job_id"]?.intValue &&
        queued["capture_id"]?.intValue != old["capture_id"]?.intValue &&
        queued["pending"]?.boolValue == true && queued["worker_started_ns"]?.intValue == 0 &&
        queued["prefix"] == old["prefix"] && queued["level_id"] == old["level_id"] &&
        queued["hold_started_ns"] == old["hold_started_ns"] &&
        queued["continuation_deadline_ns"] == old["continuation_deadline_ns"],
        "test115_old_partial_queues_independent_current_data_without_old_authority")
    world.requireBlocked("test115_old_partial_producer_return", workers: 1)
    world.oldProducerRelease.signal()
    pump("test115_current_partial_actual_producer_and_commit_parked", timeout: 30) {
        world.locked { world.currentProducerParked && world.currentCommitParked }
    }
    world.requireBlocked("test115_current_partial_returns", workers: 2)
    let current = world.locked { world.currentState }, anchor = UInt64(current["capture_id"]?.intValue ?? 0)
    let oldCapture = UInt64(old["capture_id"]?.intValue ?? 0), sources = world.locked { world.sources }
    require(current["job_id"] == queued["job_id"] && current["capture_id"] == queued["capture_id"] &&
        current["capture_start_ns"] == queued["capture_start_ns"] && current["prefix"] == old["prefix"] &&
        current["hold_started_ns"] == old["hold_started_ns"] &&
        current["continuation_deadline_ns"] == old["continuation_deadline_ns"] &&
        world.locked({ world.kernelOutcomes[world.oldJob] == 0 && world.kernelOutcomes[world.currentJob] == 0 }) &&
        sources[oldCapture] != nil && sources[anchor] != nil,
        "test115_current_partial_normal_unknown_keeps_own_source_and_original_parent")
    let oldScene = runtime114Scene(sources[oldCapture]!), currentScene = runtime114Scene(sources[anchor]!)
    defer { oldScene.deinitialize(count: 1); oldScene.deallocate(); currentScene.deinitialize(count: 1); currentScene.deallocate() }
    let oldItems = withUnsafeBytes(of: oldScene.pointee.tiles) { $0.filter { $0 == UInt8(NG2_TILE_ITEM) }.count }
    let currentItems = withUnsafeBytes(of: currentScene.pointee.tiles) { $0.filter { $0 == UInt8(NG2_TILE_ITEM) }.count }
    let direct = runtime114Motion(sources[oldCapture]!, sources[anchor]!)
    require(oldScene.pointee.goods == Int32(NG2_GOODS_PARTIAL) && currentScene.pointee.goods == Int32(NG2_GOODS_PARTIAL) &&
        oldItems == 10 && currentItems == 5 && direct.kind == Int32(NG2_BLOCKED) && direct.dx == 0 && direct.dy == 0,
        "test115_normal_perception_top_alias_loss_is_static_but_old_input_remains_invalid")
    world.locked { world.collectProofs = true }
    world.currentCommitRelease.signal(); world.continueCaptures(20_000_000)
    pump("test115_two_new_current_partial_direct_frames_while_producer_held", timeout: 30) {
        world.locked { world.proofs.count == 2 }
    }
    world.requireBlocked("test115_current_partial_producer_after_two_proofs", workers: 2)
    let proofs = world.locked { world.proofs }
    require(proofs.count == 2 && proofs[0].id > anchor && proofs[1].id > proofs[0].id &&
        proofs[1].start >= proofs[0].end && proofs.allSatisfy({ $0.stable && $0.prefix == UInt64(current["prefix"]?.intValue ?? Int.max) }),
        "test115_partial_proofs_are_independent_nonoverlapping_current_epoch")
    for proof in proofs {
        guard let frame = runtime.testOriginalFrameEvidence(id, captureIDs: [proof.id])?[proof.id],
              let raw = NG2Raster.decode(frame.0) else {
            require(false, "test115_partial_new_zero_original_pixels_retained"); return
        }
        let motion = runtime114Motion(sources[anchor]!, raw)
        require(motion.kind == Int32(NG2_BLOCKED) && motion.dx == 0 && motion.dy == 0,
            "test115_each_partial_proof_is_direct_zero_from_same_immutable_anchor")
    }
    if cancel {
        _ = call("necro_native_cancel", id)
        require(!cycleDrained(id) && runtime.hasLease && runtime112State(id)["drain_token_count"]?.intValue == 1,
            "test115_partial_cancel_keeps_actual_current_worker_lease")
        world.currentProducerRelease.signal(); world.continueCaptures(20_000_000)
        pump("test115_partial_cancel_all_actual_returns_drain", timeout: 40) { cycleDrained(id) }
        require(NG2Fake.countTouches() == world.frozenTouches && NG2Fake.paths().count == world.frozenPaths &&
            world.locked({ world.restarts == 0 && world.workers.count == 2 }),
            "test115_partial_canceled_epoch_never_moves_pauses_or_restarts")
    } else {
        world.currentProducerRelease.signal(); world.continueCaptures(20_000_000)
        pump("test115_one_current_partial_up_is_actually_credited", timeout: 40) {
            report(id)["moves"]?.intValue == 2 || report(id)["terminal"]?.intValue == 1
        }
        let snapshot = report(id)
        let events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        let moves = events.filter { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 }
        require(moves.count == 3 && moves.map({ $0["motion"]?.intValue ?? 0 }) == [1,3,1] &&
            moves.allSatisfy({ $0["direction"]?.intValue == 3 }) &&
            snapshot["inputs"]?.intValue == 3 && snapshot["moves"]?.intValue == 2 &&
            world.locked({ world.restarts == 0 && world.reservations.count == 3 }),
            "test115_only_first_move_opening_and_one_current_partial_up_are_real")
        pump("test115_post_up_normal_unknown_and_actual_producer_return_before_cancel", timeout: 30) {
            let cycle = cycleCompanion(id), drain = runtime112State(id)
            let normal = world.locked { () -> Bool in
                guard let job = world.workers.last, job != world.oldJob, job != world.currentJob else { return false }
                return world.kernelOutcomes[job] == UInt32(NG2_RING_UNKNOWN)
                    && cycle["job_id"]?.intValue == Int(job)
            }
            return normal && cycle["pending"]?.boolValue == false && cycle["outcome"]?.stringValue == "unknown"
                && cycle["assessment_status"]?.stringValue == "ok" && drain["drain_token_count"]?.intValue == 0
        }
        // The post-UP future renderer is still PARTIAL. It is deliberately
        // not re-labelled complete or used to claim a phone RS outcome.
        _ = call("necro_native_cancel", id); world.continueCaptures(20_000_000)
        pump("test115_partial_after_one_up_actual_returns_drain", timeout: 40) { cycleDrained(id) }
        require(world.locked({ world.restarts == 0 }) && NG2Fake.paths().count == 3,
            "test115_unobserved_complete_merchandise_never_becomes_absence_or_extra_up")
    }
    let finalSources = world.locked { world.sources }
    ir110CheckFootprint(id); runtime111Manifest(id, required: Set(finalSources.keys.map { Int($0) }))
    for (capture, raw) in finalSources { runtime111PersistedPixels(root, capture: capture, expected: raw) }
    publishFixtureClaim(id, requiredCaptureIDs: Set(finalSources.keys.map { Int($0) }))
    runtime112PreserveSyntheticExport(root, id, label: cancel ? "partial_cancel" : "partial_view")
}

// The C wrapper returns the real begin result unchanged. Its callback models
// time spent by C; it neither edits C state nor adds a call site to Runtime.
// This lets the exact before-Runtime bytes exercise the same assertion.
final class Runtime115BeginClock {
    let gate = NSLock(), run: String, variant: String
    var command: UInt64 = 0, notBefore: UInt64 = 0, deadline: UInt64 = 0, queryStart: UInt64 = 0
    var queries = [UInt64: UInt64]()
    var before: UInt64 = 0, after: UInt64 = 0, calls = 0, returned = false
    var cancelQueued = false, cancelCompleted = false
    init(_ run: String, _ variant: String) { self.run = run; self.variant = variant }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func advanceAfterBegin(_ id: UInt64, _ now: UInt64, _ result: Int32) {
        guard locked({ id == command && command != 0 }) else { return }
        require(result == 1 && Thread.isMainThread, "test115_clock_wrapper_follows_actual_successful_begin_on_main")
        let bound = locked { deadline }, query = locked { queryStart }
        let at: UInt64
        switch variant {
        case "late", "late_cancel": at = bound+1
        case "equal": at = bound
        case "authority": at = max(bound+1, query+1_000_000_001)
        default: at = bound-1
        }
        let actual = NG2Fake.virtualClock()
        require(actual == now && actual <= at, "test115_clock_advance_is_after_normal_begin_without_moving_original_ticket")
        NG2Fake.advance(at-actual)
        if variant == "owner" {
            NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = false; NG2Fake.lock.unlock()
        } else if variant == "locked" { LockStateMonitor.monitor.isLocked = true }
        locked { before = now; after = at; calls += 1 }
        if variant == "late_cancel" {
            let attempted = DispatchSemaphore(value: 0)
            locked { cancelQueued = true }
            DispatchQueue.global().async {
                attempted.signal()
                _ = call("necro_native_cancel", self.run)
                self.locked { self.cancelCompleted = true }
            }
            require(attempted.wait(timeout: .now()+2) == .success,
                "test115_cancel_request_started_while_begin_return_gate_is_owned")
        }
    }
}
func runtime115BeginClockReturned(_ context: UnsafeMutableRawPointer?, _ command: UInt64,
    _ now: UInt64, _ result: Int32) {
    guard let context else { return }
    Unmanaged<Runtime115BeginClock>.fromOpaque(context).takeUnretainedValue().advanceAfterBegin(command, now, result)
}
func runtime115SavePostBeginReport(_ value: [String: JSONValue], variant: String) -> String {
    let name = "status-post-begin-"+variant+".json"
    guard let evidence = ProcessInfo.processInfo.environment["NG2_RUNTIME115_EVIDENCE"], !evidence.isEmpty else {
        require(false, "test115_actual_post_begin_report_artifact_destination_required"); return name
    }
    let folder = URL(fileURLWithPath: evidence).deletingLastPathComponent().appendingPathComponent("status-snapshots")
    do {
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try JSONEncoder().encode(value).write(to: folder.appendingPathComponent(name), options: .atomic)
    } catch { require(false, "test115_actual_post_begin_report_persists") }
    return "status-snapshots/"+name
}
func testRuntime115PostBeginVariant(_ root: URL, variant: String) {
    runtime112Reset(root)
    NG2RuntimeCycleTestHooks.rgba = nil
    NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
    let id = identity(), state = Runtime115BeginClock(id, variant)
    diagnoseFixture(id); alignInitialFixtureMove(id)
    ng2_fixture_begin115_install(runtime115BeginClockReturned, Unmanaged.passUnretained(state).toOpaque())
    defer { ng2_fixture_begin115_install(nil, nil) }
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        let command = UInt64(report(id)["current_command_id"]?.intValue ?? 0)
        state.locked { state.queries[command] = NG2Fake.virtualClock() }
    }
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let snapshot = report(id), events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let ticket = events.first(where: { $0["id"]?.intValue == Int(command) }),
              ticket["kind"]?.intValue == 4 else { return false }
        require(state.locked({ state.command == 0 }), "test115_post_begin_fixture_never_schedules_a_second_move")
        // The first MOVE intentionally has preparation epoch0, so Runtime
        // owns a local returned authority without a reusable cached lease.
        // Observe the actual foreground query instead of inventing a cache.
        let queried = state.locked { state.queries[command] ?? 0 }
        require(queried > 0, "test115_post_begin_original_actual_authority_sample_exists")
        state.locked {
            state.command = command; state.notBefore = UInt64(ticket["not_before_ns"]!.intValue!)
            state.deadline = UInt64(ticket["deadline_ns"]!.intValue!); state.queryStart = queried
        }
        NG2Fake.holdTicket(command, callback)
        NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        return true
    }
    NG2RuntimeTestHooks.afterTicketReturned = { command in
        if state.locked({ command == state.command }) {
            state.locked { state.returned = true }
            _ = call("necro_native_cancel", id)
            NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        }
    }
    require(call("necro_native_start", id).1 == nil, "test115_post_begin_normal_start")
    pump("test115_post_begin_first_owned_floor_ticket", timeout: 30) {
        state.locked({ state.command != 0 }) || report(id)["terminal"]?.intValue == 1
    }
    let selected = state.locked { state.command }, before = report(id)
    require(selected != 0 && before["inputs"]?.intValue == 0 && before["moves"]?.intValue == 0,
        "test115_post_begin_ticket_has_no_previous_input_or_move")
    NG2RuntimeTestHooks.beforeMainAuthority = {
        admitFirstFixtureMove(id, expectedID: selected, afterAlignment: { _ in
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        })
    }
    NG2Fake.releaseTicket(selected)
    pump("test115_post_begin_actual_selected_callback_and_workers_drain", timeout: 30) {
        state.locked({ state.returned }) && drained(id)
    }
    if variant == "late_cancel" {
        pump("test115_post_begin_queued_cancel_actually_returns") { state.locked { state.cancelCompleted } }
    }
    // Restoring the fake external environment is only for reading/exporting
    // this already-drained run. It cannot grant a new command or owner epoch.
    NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.lock.unlock()
    LockStateMonitor.monitor.isLocked = false
    let result = call("necro_native_results", id)
    let snapshot = result.0?["report"]?.objectValue ?? [:]
    let events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let moves = events.filter { $0["kind"]?.intValue == 4 }
    guard let event = moves.first(where: { $0["id"]?.intValue == Int(selected) }) else {
        require(false, "test115_post_begin_actual_event_is_retained_in_results"); return
    }
    let source = event["source_capture_id"]?.intValue ?? 0
    let exported = Set((result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    let reportFile = runtime115SavePostBeginReport(snapshot, variant: variant)
    let sent = variant == "within" || variant == "equal"
    var evidence = [String: JSONValue]()
    evidence["variant"] = .string(variant); evidence["report_file"] = .string(reportFile)
    evidence["command_id"] = .int(Int(selected)); evidence["source_capture_id"] = .int(source)
    evidence["before_ns"] = .int(Int(state.locked { state.before })); evidence["after_ns"] = .int(Int(state.locked { state.after }))
    evidence["not_before_ns"] = .int(Int(state.locked { state.notBefore })); evidence["deadline_ns"] = .int(Int(state.locked { state.deadline }))
    for name in ["begin_ns", "end_ns", "outcome"] { evidence[name] = event[name] }
    evidence["inputs"] = snapshot["inputs"]; evidence["moves"] = snapshot["moves"]
    evidence["input_state"] = snapshot["input_state"]
    evidence["gesture_count"] = .int(NG2Fake.paths().count); evidence["move_event_count"] = .int(moves.count)
    evidence["begin_call_count"] = .int(state.locked { state.calls })
    evidence["cancel_queued"] = .bool(state.locked { state.cancelQueued })
    evidence["cancel_completed"] = .bool(state.locked { state.cancelCompleted })
    evidence["exported_source"] = .bool(result.1 == nil && source > 0 && exported.contains(source))
    evidence["failure_code"] = snapshot["dispatch_failure"]?.objectValue?["code"] ?? .null
    runtime115Emit("POST_BEGIN", evidence)
    // This is the first late variant and the named before-Runtime Red oracle.
    // The baseline C really granted begin, and the baseline Runtime really
    // called the late gesture; neither compiler failure nor fake output wins.
    if variant == "late" {
        require(NG2Fake.paths().isEmpty && snapshot["inputs"]?.intValue == 0 &&
            event["outcome"]?.intValue == 3 && (event["begin_ns"]?.intValue ?? 0) > 0,
            "test115_post_begin_deadline_crossing_never_calls_gesture")
    }
    require(state.locked({ state.calls == 1 && state.before >= state.notBefore && state.before <= state.deadline }) &&
        moves.count == 1 && (event["begin_ns"]?.intValue ?? 0) == Int(state.locked { state.before }) &&
        (event["end_ns"]?.intValue ?? 0) >= Int(state.locked { state.after }) &&
        snapshot["input_state"]?.intValue != 4 && snapshot["moves"]?.intValue == 0 &&
        NG2Fake.paths().count == (sent ? 1 : 0) && snapshot["inputs"]?.intValue == (sent ? 1 : 0) &&
        event["outcome"]?.intValue == (sent ? 2 : 3) && result.1 == nil && exported.contains(source),
        "test115_post_begin_real_event_credit_gesture_and_export_match_known_send_state")
    if variant == "late_cancel" {
        require(state.locked({ state.cancelQueued && state.cancelCompleted }) &&
            event["outcome"]?.intValue == 3 && snapshot["inputs"]?.intValue == 0,
            "test115_post_begin_known_no_send_settles_before_queued_cancel_can_make_unknown")
    }
    fixtureFailureSnapshot = nil
}
func testRuntime115PostBeginClock(_ root: URL) {
    for variant in ["late", "within", "equal", "late_cancel", "owner", "locked", "authority"] {
        testRuntime115PostBeginVariant(root.appendingPathComponent(variant), variant: variant)
    }
}

let root115 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime115-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root115, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root115) }
NG2RuntimeCycleTestHooks.spoolRoot = root115
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case115 = CommandLine.arguments.last ?? ""
pump("test115_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
switch case115 {
case "passage_fresh": testRuntime115Preparation(root115.appendingPathComponent("fresh"))
case "partial_view": testRuntime115Partial(root115.appendingPathComponent("view"), cancel: false)
case "partial_cancel": testRuntime115Partial(root115.appendingPathComponent("cancel"), cancel: true)
case "post_begin_clock": testRuntime115PostBeginClock(root115.appendingPathComponent("clock"))
default: require(false, "test115_unknown_case_is_not_another_fixture")
}
print("PASS TEST115 CASE " + case115)
