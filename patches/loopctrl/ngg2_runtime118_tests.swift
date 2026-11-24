// TEST118 changed callback boundaries only. The captures and physical world
// are public procedural fixtures. Relative incoming capture cuts come from
// normal source refresh; this is not a recorded-game or full Runtime fault replay.
func runtime118Fake<T>(_ body: () -> T) -> T {
    NG2Fake.lock.lock(); defer { NG2Fake.lock.unlock() }; return body()
}
final class Runtime118Cost {
    var observeStart: UInt64 = 0, totalObserveCost: UInt64 = 0, totalTickCost: UInt64 = 0
    var tickCalls = 0, zeroTickCalls = 0
    var beginStart: UInt64 = 0, beginCost: UInt64 = 0, beginReturn: UInt64 = 0
    var beginCalls = 0
    func install() {
        NG2RuntimeObserveTestHooks.beforeObserve = { self.observeStart = DispatchTime.now().uptimeNanoseconds }
        NG2RuntimeObserveTestHooks.afterObserve = {
            let elapsed = DispatchTime.now().uptimeNanoseconds-self.observeStart
            require(elapsed > 0, "test118_actual_C_observe_has_measured_cost")
            self.totalObserveCost += elapsed; NG2Fake.advance(elapsed)
        }
        ng2_fixture_begin115_install(runtime118BeginReturned, Unmanaged.passUnretained(self).toOpaque())
        ng2_fixture_tick118_install(runtime118TickReturned, Unmanaged.passUnretained(self).toOpaque())
    }
    func uninstall() {
        ng2_fixture_begin115_install(nil, nil); ng2_fixture_tick118_install(nil, nil)
        NG2RuntimeObserveTestHooks.beforeObserve = nil; NG2RuntimeObserveTestHooks.afterObserve = nil
    }
}
func runtime118TickReturned(_ context: UnsafeMutableRawPointer?, _ elapsed: UInt64) {
    guard let context else { return }
    let value = Unmanaged<Runtime118Cost>.fromOpaque(context).takeUnretainedValue()
    // Darwin may quantize an empty early-return tick to exactly zero. Keep
    // that observed zero; never substitute an invented positive duration.
    value.tickCalls += 1
    if elapsed == 0 { value.zeroTickCalls += 1 }
    value.totalTickCost += elapsed; NG2Fake.advance(elapsed)
}
func runtime118TickEvidence(_ value: Runtime118Cost) {
    require(value.tickCalls > 0 && value.zeroTickCalls <= value.tickCalls && value.totalTickCost > 0,
        "test118_meaningful_case_has_measured_aggregate_tick_cost")
    runtime118Emit("TICK_COST", ["tick_calls": .int(value.tickCalls),
        "zero_duration_calls": .int(value.zeroTickCalls), "total_tick_cost_ns": .int(Int(value.totalTickCost))])
}
func runtime118BeginReturned(_ context: UnsafeMutableRawPointer?, _ id: UInt64, _ now: UInt64, _ result: Int32) {
    guard let context else { return }
    let value = Unmanaged<Runtime118Cost>.fromOpaque(context).takeUnretainedValue()
    guard value.beginStart != 0 else { return }
    require(result == 1, "test118_actual_current_C_begin_accepts_new_ID")
    value.beginCost = DispatchTime.now().uptimeNanoseconds-value.beginStart
    value.beginCalls += 1; NG2Fake.advance(value.beginCost); value.beginReturn = NG2Fake.virtualClock()
    value.beginStart = 0
}
func runtime118Emit(_ kind: String, _ value: [String: JSONValue]) {
    if let bytes = try? JSONEncoder().encode(value), let text = String(data: bytes, encoding: .utf8) {
        print("EVIDENCE TEST118 " + kind + " " + text)
    } else { require(false, "test118_typed_evidence_encodes") }
}
func testRuntime118Preinput(_ root: URL) {
    runtime112Reset(root)
    // The shared cycle reset installs a FULL-goods RGBA override. This case
    // uses the native walking renderer and must keep its real no-goods view.
    NG2RuntimeCycleTestHooks.rgba = nil
    NG2Fake.lock.lock()
    NG2Fake.walkPaused = false; NG2Fake.walkY = 0; NG2Fake.walkGoodsEnabled = false
    NG2Fake.freshRevalidationWorld = false
    NG2Fake.lock.unlock()
    let id = identity()
    let captureOffset: UInt64 = 30_000_000, captureDuration: UInt64 = 10_000_000
    let beforeNotBefore: UInt64 = 15_000_000, afterNotBefore: UInt64 = 3_610_361
    let cost = Runtime118Cost(); cost.install()
    defer { cost.uninstall() }
    var oldNotBefore: UInt64 = 0, frozenPeriod: UInt64 = 0
    let refreshGate = NSLock()
    var refreshBackendPending = false, refreshCaptureID: UInt64 = 0
    func refreshLocked<T>(_ body: () -> T) -> T {
        refreshGate.lock(); defer { refreshGate.unlock() }; return body()
    }
    var refreshStart: UInt64 = 0, refreshEnd: UInt64 = 0
    var oldSourceStart: UInt64 = 0, oldSourceEnd: UInt64 = 0, oldPrefix: UInt64 = 0
    var pixelStart: UInt64 = 0, pixelEnd: UInt64 = 0
    diagnoseFixture(id); alignInitialFixtureMove(id)
    let physicalEpoch = runtime118Fake { NG2Fake.phaseBase }
    NG2RuntimeCycleTestHooks.rgba = { original in
        let actor = runtime118Fake { (NG2Fake.walkPaused, NG2Fake.walkX) }
        if actor.0 { return original }
        let midpoint = pixelStart+(pixelEnd-pixelStart)/2
        require(pixelEnd >= pixelStart && midpoint >= physicalEpoch, "test118_fixed_physical_epoch_precedes_every_capture")
        let elapsed = midpoint-physicalEpoch
        let q = Double(519_999_999-(elapsed % 520_000_000))/520_000_000.0
        var bytes = Data(count: 896*414*4); let count = bytes.count
        bytes.withUnsafeMutableBytes {
            require(ng2_fixture_walk118_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                count, actor.1, q) == 1, "test118_normal_RGBA_fixed_corridor_world")
        }
        return bytes
    }
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
        pixelStart = NG2Fake.virtualClock()
    }
    NG2RuntimeTestHooks.afterCaptureBackendReply = { capture in
        pixelEnd = NG2Fake.virtualClock()
        refreshLocked {
            if refreshBackendPending {
                require(refreshCaptureID == 0, "test118_exact_refresh_backend_identity_frozen_once")
                refreshCaptureID = capture; refreshBackendPending = false
            }
        }
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
              event["kind"]?.intValue == 4 else { return false }
        if (snapshot["inputs"]?.intValue ?? 0) < 2 {
            NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: command) }
            callback(); return true
        }
        NG2Fake.holdTicket(command, callback)
        if oldID == 0 {
            oldID = command
            oldPrepared = runtime.testPreparedAuthority(id, commandID: command) ?? []
            guard let boundary = event["not_before_ns"]?.intValue else {
                require(false, "test118_original_ticket_has_not_before"); return true
            }
            oldNotBefore = UInt64(boundary)
            oldSourceStart = UInt64(event["source_start_ns"]?.intValue ?? 0)
            guard let oldSourceID = event["source_capture_id"]?.intValue,
                  let metadata = runtime.testOriginalFrameEvidence(id, captureIDs: [UInt64(oldSourceID)])?[UInt64(oldSourceID)]?.1,
                  let end = metadata["capture_end_ns"]?.intValue,
                  let period = snapshot["beat_period_ns"]?.intValue,
                  let prefix = snapshot["last_completed_id"]?.intValue, prefix > 0 else {
                require(false, "test118_original_queued_ticket_source_metadata_present"); return true
            }
            oldSourceEnd = UInt64(end); frozenPeriod = UInt64(period); oldPrefix = UInt64(prefix)
            require(NG2Fake.changeClockAtCaptureBoundary {
                let at = UInt64(boundary)-captureOffset, now = NG2Fake.virtualClock()
                require(now <= at && at >= oldSourceEnd &&
                    at-oldSourceStart >= frozenPeriod/10,
                    "test118_actual_independent_source_gap_before_unchanged_window")
                if now < at { NG2Fake.advance(at-now) }
                NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 0
                NG2Fake.captureTimeProvider = {
                    refreshLocked {
                        require(refreshCaptureID == 0 && !refreshBackendPending,
                            "test118_one_explicit_refresh_backend_request")
                        refreshBackendPending = true
                    }
                    let start = NG2Fake.virtualClock()
                    NG2Fake.advance(captureDuration)
                    return start+captureDuration/2
                }
                NG2Fake.captureLimit = NG2Fake.requests+1
                NG2Fake.lock.unlock()
            }, "test118_refresh_at_existing_capture_boundary")
        } else {
            newID = command; refreshCommit = NG2Fake.virtualClock()
            newPrepared = runtime.testPreparedAuthority(id, commandID: command) ?? []
            NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        }
        return true
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, start, end, prefix, stable in
        let selected = refreshLocked { refreshCaptureID }
        guard selected != 0 && capture == selected else { return }
        require(refreshStart == 0 && stable && prefix == oldPrefix &&
            start >= oldNotBefore-captureOffset && start >= oldSourceEnd &&
            start-oldSourceStart >= frozenPeriod/10 && end >= start+captureDuration,
            "test118_exact_refresh_actual_independent_capture_interval")
        refreshStart = start; refreshEnd = end
        let at = oldNotBefore-beforeNotBefore, now = NG2Fake.virtualClock()
        if now < at { NG2Fake.advance(at-now) }
        let actual = NG2Fake.virtualClock()
        require(at <= actual && actual < oldNotBefore && end <= actual,
            "test118_selected_refresh_preserves_planned_cut_and_actual_native_cost")
    }
    require(call("necro_native_start", id).1 == nil, "test118_existing_fresh_callback_public_start")
    pump("test118_two_confirmed_moves_then_new_fresh_id", timeout: 30) {
        newID != 0 || report(id)["terminal"]?.intValue == 1
    }
    let before = report(id)
    let events = (before["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    guard let old = events.first(where: { $0["id"]?.intValue == Int(oldID) }),
          let fresh = events.first(where: { $0["id"]?.intValue == Int(newID) }) else {
        require(false, "test118_real_old_and_new_fresh_events_exist"); return
    }
    require(oldID != 0 && newID > oldID && before["inputs"]?.intValue == 2 && before["moves"]?.intValue == 2 &&
        before["lead_confirmed"]?.intValue == 1 &&
        old["outcome"]?.intValue == 3 && old["begin_ns"]?.intValue == 0 &&
        ["target_ns", "not_before_ns", "deadline_ns", "ordinal"].allSatisfy({ old[$0] == fresh[$0] }) &&
        old["source_capture_id"] != fresh["source_capture_id"],
        "test118_latest_fresh_id_keeps_original_window_and_no_old_input_credit")
    let metadataIDs = [UInt64(old["source_capture_id"]!.intValue!), UInt64(fresh["source_capture_id"]!.intValue!)]
    guard let frames = runtime.testOriginalFrameEvidence(id, captureIDs: metadataIDs),
          let firstMetadata = frames[metadataIDs[0]]?.1, let lastMetadata = frames[metadataIDs[1]]?.1 else {
        require(false, "test118_both_sources_belong_to_same_actual_run"); return
    }
    guard let refreshSample = (before["captures"]?.arrayValue ?? []).compactMap({ $0.objectValue })
            .first(where: { $0["id"]?.intValue == Int(metadataIDs[1]) }),
          let observeStart = refreshSample["observe_start_ns"]?.intValue,
          let observeEnd = refreshSample["observe_end_ns"]?.intValue else {
        require(false, "test118_exact_refresh_runtime_C_entry_and_return_recorded"); return
    }
    require(refreshLocked { refreshCaptureID } == metadataIDs[1] &&
        lastMetadata["capture_start_ns"]?.intValue == Int(refreshStart) &&
        lastMetadata["capture_end_ns"]?.intValue == Int(refreshEnd) &&
        UInt64(observeStart) >= oldNotBefore-beforeNotBefore &&
        UInt64(observeStart) < UInt64(observeEnd) && UInt64(observeEnd) <= refreshCommit &&
        refreshCommit < oldNotBefore,
        "test118_only_selected_capture_owns_actual_C_cost_before_original_window")
    require([firstMetadata,lastMetadata].allSatisfy {
        $0["stable_prefix"]?.boolValue == true && $0["inflight_start"]?.boolValue == false &&
        $0["inflight_end"]?.boolValue == false &&
        $0["completed_prefix_start"] == firstMetadata["completed_prefix_start"] &&
        $0["completed_prefix_end"] == firstMetadata["completed_prefix_start"]
    } && runtime118Fake { NG2Fake.frontPID == 42 && NG2Fake.authenticatedOwnerActive &&
        NG2Fake.authorizedOwners == Set(["fixture-owner"]) },
        "test118_same_run_owner_PID_prefix_and_nonsent_generation_lease")
    require(oldPrepared.count == 4 && newPrepared == oldPrepared &&
        queries[Int(oldID)]?.count == 1 && queries[Int(newID)] == nil,
        "test118_actual_runtime_reuses_opaque_epoch_and_original_ax_sample")
    let count = NG2Fake.countTouches(), paths = NG2Fake.paths().count
    NG2RuntimeTestHooks.beforeMainAuthority = { require(false, "test118_stale_callback_never_reaches_final_gate") }
    NG2Fake.releaseTicket(oldID)
    pump("test118_actual_old_callback_returns_before_new_main") { oldReturn != 0 }
    require(NG2Fake.countTouches() == count && NG2Fake.paths().count == paths &&
        report(id)["events"] == before["events"] && report(id)["current_command_id"]?.intValue == Int(newID),
        "test118_old_return_cannot_touch_or_complete_new_reservation")
    NG2RuntimeTestHooks.beforeMainAuthority = {
        admitFirstFixtureMove(id, expectedID: newID, afterAlignment: { at in
            let actual = UInt64(fresh["not_before_ns"]!.intValue!)+afterNotBefore
            require(at <= actual, "test118_actual_begin_offset_not_rescheduled")
            if at < actual { NG2Fake.advance(actual-at) }
        })
        newMain = NG2Fake.virtualClock(); cost.beginStart = DispatchTime.now().uptimeNanoseconds
        require(oldReturn <= newMain &&
            refreshCommit >= UInt64(fresh["not_before_ns"]!.intValue!)-beforeNotBefore &&
            newMain <= UInt64(fresh["deadline_ns"]!.intValue!),
            "test118_actual_new_main_after_measured_cost_inside_unchanged_deadline")
    }
    NG2Fake.releaseTicket(newID)
    pump("test118_new_actual_ack_and_all_callbacks_drained", timeout: 30) { drained(id) }
    let final = report(id)
    let finalEvents = (final["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let sent = finalEvents.first(where: { $0["id"]?.intValue == Int(newID) }) ?? [:]
    require(final["inputs"]?.intValue == 3 && final["moves"]?.intValue == 2 &&
        sent["outcome"]?.intValue == 2 && sent["motion"]?.intValue == 0 &&
        old["begin_ns"]?.intValue == 0 && NG2Fake.paths().count == paths+1,
        "test118_one_new_gesture_no_invented_motion_or_unknown_resend")
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
    evidence["old_source_start_ns"] = .int(Int(oldSourceStart))
    evidence["old_source_end_ns"] = .int(Int(oldSourceEnd))
    evidence["frozen_period_ns"] = .int(Int(frozenPeriod))
    evidence["refresh_start_ns"] = .int(Int(refreshStart)); evidence["refresh_end_ns"] = .int(Int(refreshEnd))
    evidence["refresh_planned_analysis_cut_ns"] = .int(Int(oldNotBefore-beforeNotBefore))
    evidence["refresh_analysis_cut_ns"] = .int(observeStart)
    evidence["refresh_observe_end_ns"] = .int(observeEnd)
    evidence["begin_return_ns"] = .int(Int(cost.beginReturn))
    evidence["begin_cost_ns"] = .int(Int(cost.beginCost))
    evidence["observe_cost_ns"] = .int(Int(cost.totalObserveCost))
    evidence["tick_cost_ns"] = .int(Int(cost.totalTickCost))
    evidence["fit_phase_adjustments"] = .int(0)
    require(cost.beginCost > 0 && cost.beginReturn <= UInt64(fresh["deadline_ns"]!.intValue!) &&
        cost.beginCalls == 1 && refreshEnd-refreshStart >= captureDuration,
        "test118_real_native_elapsed_charged_before_Runtime_post_begin_gate")
    runtime118TickEvidence(cost)
    runtime118Emit("PREPARATION", evidence)
    let sources = Set([old["source_capture_id"]!.intValue!, fresh["source_capture_id"]!.intValue!])
    let result = call("necro_native_results", id)
    let exported = Set((result.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue?["capture_id"]?.intValue })
    require(result.1 == nil && sources.isSubset(of: exported), "test118_fresh_actual_export_retains_both_sources_after_drain")
    guard let payload = result.0, let exportRoot = ProcessInfo.processInfo.environment["NG2_RUNTIME112_EVIDENCE"],
          let selected = ProcessInfo.processInfo.environment["NG2_RUNTIME112_CASE"] else {
        require(false, "test118_native_results_evidence_output_is_explicit"); return
    }
    let destination = URL(fileURLWithPath: exportRoot).appendingPathComponent(selected)
        .appendingPathComponent("native-results").appendingPathComponent(id)
    do {
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true,
            attributes: [.posixPermissions: NSNumber(value: 0o700)])
        let encoded = try JSONEncoder().encode(payload)
        try encoded.write(to: destination.appendingPathComponent("native-results.json"))
        var saved = [JSONValue]()
        for sourceID in metadataIDs {
            guard let row = (payload["images"]?.arrayValue ?? []).compactMap({ $0.objectValue })
                    .first(where: { $0["capture_id"]?.intValue == Int(sourceID) }),
                  let base64 = row["data_base64"]?.stringValue, let png = Data(base64Encoded: base64),
                  let rgba = NG2Raster.decode(png), let original = frames[sourceID],
                  let originalRGBA = NG2Raster.decode(original.0) else {
                require(false, "test118_both_native_result_source_images_decode"); return
            }
            require(rgba == originalRGBA && row["sha256"]?.stringValue == NG2CycleWire.hash(png),
                "test118_exported_native_PNG_is_exact_original_RGBA")
            let stem = "capture-"+String(sourceID)
            try png.write(to: destination.appendingPathComponent(stem+".png"))
            try rgba.write(to: destination.appendingPathComponent(stem+".rgba"))
            let metadata = try JSONEncoder().encode(original.1)
            try metadata.write(to: destination.appendingPathComponent(stem+".metadata.json"))
            saved.append(.object(["capture_id": .int(Int(sourceID)), "stem": .string(stem),
                "png_sha256": .string(NG2CycleWire.hash(png)), "raw_sha256": .string(NG2CycleWire.hash(rgba)),
                "metadata_sha256": .string(NG2CycleWire.hash(metadata))]))
        }
        let receipt: [String: JSONValue] = ["schema": .string("test118-native-results-evidence-v1"),
            "scope": .string("actual_noncycle_native_results_and_original_runtime_sources_not_Spool"),
            "run_id": .string(id), "old_command_id": .int(Int(oldID)), "new_command_id": .int(Int(newID)),
            "native_results_sha256": .string(NG2CycleWire.hash(encoded)), "sources": .array(saved)]
        try JSONEncoder().encode(receipt).write(to: destination.appendingPathComponent("receipt.json"))
    } catch { require(false, "test118_actual_native_results_export_write") }
    fixtureFailureSnapshot = nil
}


func runtime118Start(_ id: String) -> ([String: JSONValue]?, JSONRPCError?) {
    runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-irregular-v1"), "_necro_owner": .string("fixture-owner"),
        "continuous_campaign": .bool(true), "initial_restart": .bool(true)])
}
func runtime118Events(_ id: String) -> [[String: JSONValue]] {
    (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
// Ordinary campaign keepalive runs on the main test pump, once per second,
// rather than serializing a status RPC before every production control tick.
final class Runtime118CampaignWatch {
    let id: String
    var lastPoll: UInt64 = 0, lastChildPoll: UInt64 = 0, child = "", childObserved = false, allDrained = false
    init(_ id: String) { self.id = id }
    func progress(_ next: String) -> Bool {
        let now = DispatchTime.now().uptimeNanoseconds
        if lastPoll == 0 || now-lastPoll >= 1_000_000_000 {
            let value = runtime116Payload(id)
            allDrained = value["terminal"]?.boolValue == true && value["workers_drained"]?.boolValue == true
            lastPoll = now
        }
        if next != child { child = next; childObserved = false; lastChildPoll = 0 }
        if !child.isEmpty && !childObserved && (lastChildPoll == 0 || now-lastChildPoll >= 100_000_000) {
            childObserved = (report(child)["last_capture_id"]?.intValue ?? 0) > 0
            lastChildPoll = now
        }
        return childObserved || allDrained
    }
    func stopped() -> Bool {
        let now = DispatchTime.now().uptimeNanoseconds
        if lastPoll == 0 || now-lastPoll >= 100_000_000 {
            let value = runtime116Payload(id, keepalive: false)
            allDrained = value["terminal"]?.boolValue == true && value["workers_drained"]?.boolValue == true
            lastPoll = now
        }
        return allDrained
    }
}
final class Runtime118UpperWorld {
    let gate = NSLock(), rootID: String, physicalEpoch: UInt64
    var x: Int32 = 2, y: Int32 = 0, opened = false
    var captureStart: UInt64 = 0, captureEnd: UInt64 = 0
    var capturePose: (Int32, Int32, Bool, Int) = (2,0,false,0), consumedPaths = 0
    var captureModels = [UInt64: [String: JSONValue]]()
    var restarts = 0, child = "", gestures = [Int](), partialJobs = 0, fullJobs = 0
    var workerStart: UInt64 = 0, normalCalls = 0, negativeCalls = 0
    var parents = [UInt64](), jobs = [UInt64](), workerDurations = [UInt64]()
    var baseParent: UInt64 = 0, allocatedParent: UInt64 = 0, allocationPeriod: UInt64 = 0
    var sourceStates = [UInt64: [String: JSONValue]]()
    init(_ id: String) { rootID = id; physicalEpoch = NG2Fake.virtualClock() }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func install() {
        NG2RuntimeTestHooks.beforeCaptureAdmission = {
            // fastGesture appends its actual path only after the ACK-model
            // sleep returns. Consume each completed physical path once, away
            // from the input boundary, and freeze this capture's own pose.
            let paths = NG2Fake.paths(), start = NG2Fake.virtualClock()
            self.locked {
                require(paths.count >= self.consumedPaths, "test118_actual_physical_path_inventory_is_monotonic")
                for path in paths.dropFirst(self.consumedPaths) {
                    require(path.count == 1 && path[0].count == 2,
                        "test118_actual_upper_path_has_one_finger_two_points")
                    let finger = path[0]
                    require(finger[0].t == 0 && finger[1].t == 0.05 && finger[0].point == finger[1].point,
                        "test118_actual_upper_path_preserves_50ms_stationary_gesture")
                    let point = finger[0].point
                    let direction = point == CGPoint(x:207,y:49) ? 1 : point == CGPoint(x:124,y:838) ? 4 : 0
                    require(direction != 0, "test118_upper_route_actual_path_is_LEFT_or_DOWN")
                    self.gestures.append(direction)
                    if !self.opened && self.x > 0 {
                        require(direction == 1 && self.y == 0, "test118_actual_observed_outside_lead_in")
                        self.x -= 1
                    } else if !self.opened {
                        require(direction == 1 && self.x == 0 && self.y == 0,
                            "test118_first_LEFT_opens_door_without_displacement")
                        self.opened = true
                    } else if direction == 1 { self.x -= 1 }
                    else { self.y += 1 }
                }
                self.consumedPaths = paths.count
                self.captureStart = start
                self.capturePose = (self.x,self.y,self.opened,self.restarts)
            }
        }
        NG2RuntimeTestHooks.afterCaptureBackendReply = { capture in
            self.locked {
                self.captureEnd = NG2Fake.virtualClock()
                if self.capturePose.3 < 2 {
                    require(self.captureModels.count < 4096, "test118_finite_root_capture_pose_inventory")
                    self.captureModels[capture] = ["x": .int(Int(self.capturePose.0)), "y": .int(Int(self.capturePose.1)),
                        "opened": .bool(self.capturePose.2), "completed_paths": .int(self.consumedPaths),
                        "admission_ns": .int(Int(self.captureStart)), "reply_ns": .int(Int(self.captureEnd))]
                }
            }
        }
        NG2RuntimeCycleTestHooks.rgba = { original in
            let paused = runtime118Fake { NG2Fake.walkPaused }
            if paused { return original }
            let pose = self.locked { (self.capturePose.0, self.capturePose.1, self.capturePose.2,
                self.captureStart, self.captureEnd, self.capturePose.3) }
            let midpoint = pose.3+(pose.4 >= pose.3 ? (pose.4-pose.3)/2 : 0)
            let elapsed = midpoint >= self.physicalEpoch ? midpoint-self.physicalEpoch : 0
            let q = Double(519_999_999-(elapsed % 520_000_000))/520_000_000.0
            var bytes = Data(count: 896*414*4); let count = bytes.count
            bytes.withUnsafeMutableBytes {
                let valid = pose.5 >= 2
                    ? ng2_fixture_floor_pixels_rgba($0.bindMemory(to: UInt8.self).baseAddress, count, 0, 0, q, 0)
                    : ng2_fixture_upper118_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                        count, pose.0, pose.1, pose.2 ? 1 : 0, q)
                require(valid == 1, "test118_same_physical_upper_world_at_actual_gesture_pose")
            }
            return bytes
        }
        NG2Fake.cycleTap = { x, y in
            require(!(x == 297 && y == 448), "test118_initial_and_successor_never_resume_old_floor")
            if x == 144 && y == 448 {
                self.locked { self.restarts += 1 }
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
            }
        }
        NG2Fake.applyShopGesture = { _ in
            // Recorded touch ACK duration is charged to the wall clock; it
            // grants no movement credit. No fixture RPC/report runs inside
            // this actual input interval. Later normal pixels prove motion.
            Thread.sleep(forTimeInterval: 0.278756083)
            return true
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { job in
            let state = cycleCompanion(self.rootID)
            runtime112RecordAdmission(self.rootID, state, label: "test118_upper_normal_wall_clock")
            let capture = UInt64(state["capture_id"]?.intValue ?? 0)
            require(state["job_id"]?.intValue == Int(job) && state["pending"]?.boolValue == true,
                "test118_actual_pending_worker_owns_same_immutable_job")
            // Runtime already analyzed this exact immutable source before
            // worker admission. Record its actual C flags now; inspect the
            // persisted original RAW/PNG after all inputs have stopped.
            let partial = state["partial"]?.boolValue == true
            require(partial || state["full_seen"]?.boolValue == true,
                "test118_actual_worker_has_partial_or_full_source_flags")
            self.locked {
                if partial { self.partialJobs += 1 } else { self.fullJobs += 1 }
                self.jobs.append(job); self.sourceStates[capture] = state
                let parent = UInt64(state["continuation_deadline_ns"]?.intValue ?? 0)
                self.parents.append(parent)
                if self.baseParent == 0 { self.baseParent = parent }
                if self.x < 0 {
                    require(self.allocatedParent > 0 && parent > 0 && parent <= self.allocatedParent,
                        "test118_each_fresh_job_parent_stays_within_one_frozen_route_cap")
                }
                self.workerStart = NG2Fake.virtualClock()
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY) && status == 0,
                "test118_actual_normal_Ring_target_worker")
            self.locked {
                self.normalCalls += 1
                if outcome == UInt32(NG2_RING_NEGATIVE) { self.negativeCalls += 1 }
                self.workerDurations.append(NG2Fake.virtualClock()-self.workerStart)
            }
        }
        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { _ in
            guard self.locked({ self.allocatedParent == 0 }) else { return }
            let state = cycleCompanion(self.rootID), snapshot = report(self.rootID)
            let parent = UInt64(state["continuation_deadline_ns"]?.intValue ?? 0)
            let period = UInt64(snapshot["beat_period_ns"]?.intValue ?? 0)
            self.locked {
                if self.allocatedParent == 0 && self.baseParent > 0 && parent > self.baseParent &&
                    self.x == 0 && self.y == 0 && self.opened {
                    require(period > 0 && parent <= self.baseParent+period,
                        "test118_initial_V2_allocation_adds_at_most_one_frozen_period")
                    self.allocatedParent = parent; self.allocationPeriod = period
                }
            }
        }
        NG2RuntimeTestHooks.beforeControlTick = nil
    }
}

// Diagnostic copies are original stopped Spool bytes, separate from normal
// synthetic exports. Preserve them before a terminal assertion can exit.
func runtime118ArchiveStoppedSpool(_ root: URL, _ id: String,
        sourceStates: [UInt64: [String: JSONValue]], snapshot: [String: JSONValue]) {
    guard let output = ProcessInfo.processInfo.environment["NG2_RUNTIME112_EVIDENCE"],
          let selected = ProcessInfo.processInfo.environment["NG2_RUNTIME112_CASE"] else {
        require(false, "test118_stopped_evidence_output_is_explicit"); return
    }
    let source = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    let destination = URL(fileURLWithPath: output).deletingLastPathComponent()
        .appendingPathComponent("stopped-runtime-evidence").appendingPathComponent(selected).appendingPathComponent(id)
    do {
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true,
            attributes: [.posixPermissions: NSNumber(value: 0o700)])
        let sources = Dictionary(uniqueKeysWithValues: sourceStates.map { (String($0.key), JSONValue.object($0.value)) })
        var diagnostic: [String: JSONValue] = ["schema": .string("test118-stopped-original-spool-v1"),
            "run_id": .string(id), "snapshot": .object(snapshot), "worker_sources": .object(sources)]
        try JSONEncoder().encode(diagnostic).write(to: destination.appendingPathComponent("diagnostic.json"))
        guard let files = FileManager.default.enumerator(at: source, includingPropertiesForKeys: nil) else {
            require(false, "test118_original_stopped_Spool_exists"); return
        }
        let byteLimit = NG2CycleSpool.maximumRawBytes + NG2CycleSpool.maximumMetadataBytes
            + NG2CycleSpool.maximumPNGBytes + NG2CycleSpool.maximumExportTemporaryBytes
        // Four files per retained frame, the store's512 sequenced records,
        // and32 bounded session/manifest/reservation/escrow control files.
        let fileLimit = 4*NG2CycleSpool.maximumFrames+512+32
        // Darwin's temporary-directory URL and enumerator may spell the
        // same /var/folders directory with /private. Normalize only this
        // known root alias, without following or admitting a symlink leaf.
        func temporaryPath(_ url: URL) -> String {
            let path = url.standardizedFileURL.path
            return path.hasPrefix("/private/var/folders/") ? String(path.dropFirst(8)) : path
        }
        let sourcePath = temporaryPath(source)
        var total = 0, count = 0
        for case let url as URL in files {
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            let kind = (attributes[.type] as? FileAttributeType)?.rawValue ?? (attributes[.type] as? String)
            if kind == FileAttributeType.typeDirectory.rawValue { continue }
            let path = temporaryPath(url)
            if kind != FileAttributeType.typeRegular.rawValue || !path.hasPrefix(sourcePath+"/") {
                diagnostic["copy_rejection"] = .object(["source": .string(source.path), "url": .string(url.path),
                    "normalized_source": .string(sourcePath), "normalized_url": .string(path),
                    "kind": .string(kind ?? "unrecognized")])
                try JSONEncoder().encode(diagnostic).write(to: destination.appendingPathComponent("diagnostic.json"))
            }
            require(kind == FileAttributeType.typeRegular.rawValue, "test118_stopped_Spool_regular_original_file")
            require(path.hasPrefix(sourcePath+"/"), "test118_stopped_Spool_original_component_containment")
            let relative = String(path.dropFirst(sourcePath.count+1))
            require(!relative.isEmpty && !relative.split(separator: "/").contains(".."), "test118_stopped_Spool_safe_relative_path")
            let bytes = try Data(contentsOf: url); total += bytes.count; count += 1
            require(count <= fileLimit && total <= byteLimit, "test118_stopped_Spool_bounded_original_copy")
            let target = destination.appendingPathComponent("spool").appendingPathComponent(relative)
            try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try bytes.write(to: target)
        }
        require(count > 0, "test118_stopped_original_Spool_copy_nonempty")
    } catch { require(false, "test118_stopped_original_Spool_write") }
}
func runtime118CheckStoppedSources(_ root: URL, _ id: String, _ sources: [UInt64: [String: JSONValue]]) {
    require(!sources.isEmpty && runtime116Drained(id), "test118_source_verification_after_all_callbacks_drain")
    let folder = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    for capture in sources.keys.sorted() {
        let state = sources[capture]!, stem = String(format: "frame-%016llx", capture)
        guard let raw = try? Data(contentsOf: folder.appendingPathComponent(stem+".rgba")),
              let encoded = try? Data(contentsOf: folder.appendingPathComponent(stem+".json")),
              let body = try? JSONDecoder().decode([String: JSONValue].self, from: encoded),
              let metadata = body["metadata"]?.objectValue else {
            require(false, "test118_original_worker_source_persisted_before_postdrain_check"); return
        }
        require(body["run_id"]?.stringValue == id && body["capture_id"]?.intValue == Int(capture) &&
            body["raw_sha256"]?.stringValue == NG2CycleWire.hash(raw) &&
            metadata["capture_start_ns"] == state["capture_start_ns"] &&
            metadata["stable_prefix"]?.boolValue == true && metadata["inflight_start"]?.boolValue == false &&
            metadata["inflight_end"]?.boolValue == false && metadata["completed_prefix_start"] == state["prefix"] &&
            metadata["completed_prefix_end"] == state["prefix"],
            "test118_actual_worker_original_RAW_metadata_prefix_and_source_time")
        let scene = runtime114Scene(raw)
        let items = withUnsafeBytes(of: scene.pointee.tiles) { $0.filter { $0 == 6 }.count }
        let partial = state["partial"]?.boolValue == true
        require(scene.pointee.state == 2 &&
            (partial && scene.pointee.goods == 1 && items == 5 || !partial && scene.pointee.goods == 2 && items == 3),
            "test118_real_Perception_partial_five_then_full_three")
        scene.deinitialize(count: 1); scene.deallocate()
        runtime111PersistedPixels(folder, capture: capture, expected: raw)
    }
}
// Upper-only read-only diagnostics. No hook supplies a clock, Scene, guard,
// lease or result. A hook marker is not the later Runtime final gate.
final class Runtime118UpperTrace {
    let id: String, capacity = 4096
    private let gate = NSLock()
    private var rows = [[Int64]?](repeating: nil, count: 4096)
    private var sequence: UInt64 = 0, active = true
    private var capture: (UInt64, UInt64, UInt64, UInt64, Bool) = (0,0,0,0,false)
    private var saved: [String: JSONValue]?
    init(_ id: String) { self.id = id }
    func mark(_ kind: Int64, _ ticket: UInt64 = 0, _ values: [Int64] = []) {
        gate.lock(); defer { gate.unlock() }
        guard active else { return }
        sequence += 1
        // Preserve uint64 bits, rather than trapping in a hot callback.
        rows[Int((sequence-1) % UInt64(capacity))] = [Int64(bitPattern: sequence),kind,
            Int64(bitPattern: DispatchTime.now().uptimeNanoseconds),Int64(bitPattern: ticket)] + values
    }
    func preparation(_ command: NG2Command) {
        let ticket = command.id // Immutable identity from this actual C return.
        NG2RuntimeTestHooks.beforeMainAdmission = { self.mark(2,ticket) }
        NG2RuntimeTestHooks.afterForegroundQuery = { self.mark(3,ticket) }
    }
    func install() {
        ng2_fixture_trace118_install(runtime118TraceTick, runtime118TraceEpoch, Unmanaged.passUnretained(self).toOpaque())
        ng2_fixture_begin115_install(runtime118TraceBegin, Unmanaged.passUnretained(self).toOpaque())
        NG2RuntimeTestHooks.scheduleTicket = { ticket, _ in
            self.mark(1,ticket)
            // ownsTicket precedes the main hook, and controlQueue synchronously
            // waits for main. No later ticket can replace this captured ID.
            NG2RuntimeTestHooks.beforeMainAuthority = {
                self.mark(4,ticket)
                let lease = runtime.testPreparedAuthority(self.id, commandID: ticket)
                self.mark(5,ticket,[lease == nil ? 0 : 1] + (lease ?? []).map { Int64(bitPattern:$0) })
            }
            return false // Preserve actual Runtime dispatch, due-inline or asyncAfter.
        }
        NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { ticket,start,end,prefix,stable in
            self.gate.lock(); self.capture = (ticket,start,end,prefix,stable); self.gate.unlock()
        }
        NG2RuntimeObserveTestHooks.beforeObserve = { self.observation(8) }
        NG2RuntimeObserveTestHooks.afterObserve = { self.observation(9) }
        NG2RuntimeTestHooks.beforeControlTick = { self.mark(10) }
    }
    func observation(_ kind: Int64) {
        gate.lock(); let value = capture; gate.unlock()
        mark(kind,value.0,[Int64(bitPattern:value.1),Int64(bitPattern:value.2),
            Int64(bitPattern:value.3),value.4 ? 1 : 0])
    }
    func progress(_ watch: Runtime118CampaignWatch, _ child: String) -> Bool {
        let now = DispatchTime.now().uptimeNanoseconds
        let predictedDue = watch.lastPoll == 0 || now-watch.lastPoll >= 1_000_000_000
        if predictedDue { mark(11) }
        let result = watch.progress(child) // Same original keepalive/cadence.
        if predictedDue { mark(12) }
        // The original watch samples its own later now: absent markers do
        // not prove that its one-second boundary was not crossed inside it.
        return result
    }
    func stop() {
        gate.lock(); let wasActive = active; active = false; gate.unlock()
        guard wasActive else { return }
        ng2_fixture_trace118_install(nil,nil,nil); ng2_fixture_begin115_install(nil,nil)
        NG2RuntimeTestHooks.scheduleTicket = nil
        NG2RuntimeTestHooks.beforeMainAdmission = nil; NG2RuntimeTestHooks.afterForegroundQuery = nil
        NG2RuntimeTestHooks.beforeMainAuthority = nil; NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
        NG2RuntimeObserveTestHooks.beforeObserve = nil; NG2RuntimeObserveTestHooks.afterObserve = nil
        NG2RuntimeTestHooks.beforeControlTick = nil
    }
    func save() -> [String: JSONValue] {
        gate.lock()
        if let saved { gate.unlock(); return saved }
        let total = sequence, stillActive = active, copy = rows.compactMap { $0 }
        gate.unlock()
        let ordered = copy.sorted { $0[0] < $1[0] }
        let body: [String: JSONValue] = ["schema": .string("test118-upper-ticket-ledger-v1"),"run_id": .string(id),
            "root_only": .bool(true),"active_at_snapshot": .bool(stillActive),"capacity": .int(capacity),
            "total_rows": .int(Int(total)),"dropped_rows": .int(max(0,Int(total)-capacity)),
            "row_prefix": .array(["sequence","kind","Dispatch_uptime_ns","immutable_ID"].map { .string($0) }),
            "unsigned_encoding": .string("uint64 bits encoded as signed int64; no hot overflow trap"),
            "kinds": .object(["1": .string("schedule_hook_return_FALSE_actual_dispatch_path_preserved_may_due_inline; no extra values"),
                "2": .string("prepare_main_hook; no extra values"),"3": .string("AX_return_hook; no extra values"),
                "4": .string("beforeMainAuthority_hook_not_final_gate; no extra values"),
                "5": .string("cached_shared_lease_present[,authority_start,end,prepared_ID,epoch]; nil_is_not_local_queued_lease_absence"),
                "6": .string("actual_C_begin_return; passed_now,result"),
                "7": .string("actual_C_tick_return; passed_now,native_elapsed,result[,ordinal,target,NB,D,source_ID,source_start,phase_sample,kind,direction,x,y]"),
                "8": .string("before_actual_C_observe; capture_start,end,prefix,stable"),
                "9": .string("after_actual_C_observe; capture_start,end,prefix,stable"),
                "10": .string("before_ControlTick_hook; no extra values"),
                "11": .string("predicted_due_progress_call_begin; no extra values; absence_does_not_prove_no_actual_poll"),
                "12": .string("predicted_due_progress_call_end; no extra values; enclosing_call_not_actual_RPC_boundary"),
                "13": .string("actual_C_preparation_epoch_return; passed_now,actual_epoch,native_elapsed")]),
            "limits": .string("Read-only diagnostic overhead is real wall time. Epoch0 permits single-ID use. Hook is not final gate; missing gate-epoch/begin cannot uniquely distinguish time/key/cancel. Dropped intervals remain unknown. Predicted-due progress markers are not exact RPC edges; their absence cannot exclude a boundary-crossing actual poll. CLOCK_MONOTONIC is duration only."),
            "rows": .array(ordered.map { .array($0.map { .int(Int($0)) }) })]
        var summary: [String: JSONValue] = ["run_id": .string(id),"rows": .int(ordered.count),
            "total_rows": .int(Int(total)),"dropped_rows": .int(max(0,Int(total)-capacity))]
        if let output = ProcessInfo.processInfo.environment["NG2_RUNTIME112_EVIDENCE"] {
            let folder = URL(fileURLWithPath:output).deletingLastPathComponent().appendingPathComponent("upper-ticket-ledger")
            do {
                try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
                let bytes = try JSONEncoder().encode(body), name = "upper-ticket-ledger/"+id+".json"
                try bytes.write(to:folder.appendingPathComponent(id+".json"),options:.atomic)
                summary["path"] = .string(name); summary["sha256"] = .string(NG2CycleWire.hash(bytes))
            } catch { summary["save_error"] = .string("diagnostic_write_failed") }
        } else { summary["save_error"] = .string("diagnostic_output_unavailable") }
        gate.lock(); saved = summary; gate.unlock()
        runtime118Emit("UPPER_LEDGER", summary)
        return summary
    }
}
func runtime118TraceTick(_ context: UnsafeMutableRawPointer?, _ now: UInt64, _ elapsed: UInt64,
        _ result: Int32, _ pointer: UnsafePointer<NG2Command>?) {
    guard let context else { return }
    let trace = Unmanaged<Runtime118UpperTrace>.fromOpaque(context).takeUnretainedValue()
    var values = [Int64(bitPattern:now),Int64(bitPattern:elapsed),Int64(result)]
    var ticket: UInt64 = 0
    if result == 1, let command = pointer?.pointee {
        ticket = command.id
        values += [command.ordinal,command.target_ns,command.not_before_ns,command.deadline_ns,
            command.source_capture_id,command.source_start_ns,command.phase_sample_ns].map { Int64(bitPattern:$0) }
        values += [command.kind,command.direction,command.x,command.y].map { Int64($0) }
        trace.preparation(command) // Copies values; no pointer retained.
    }
    trace.mark(7,ticket,values)
}
func runtime118TraceEpoch(_ context: UnsafeMutableRawPointer?, _ ticket: UInt64, _ now: UInt64,
        _ value: UInt64, _ elapsed: UInt64) {
    guard let context else { return }
    Unmanaged<Runtime118UpperTrace>.fromOpaque(context).takeUnretainedValue()
        .mark(13,ticket,[Int64(bitPattern:now),Int64(bitPattern:value),Int64(bitPattern:elapsed)])
}
func runtime118TraceBegin(_ context: UnsafeMutableRawPointer?, _ ticket: UInt64, _ now: UInt64, _ result: Int32) {
    guard let context else { return }
    Unmanaged<Runtime118UpperTrace>.fromOpaque(context).takeUnretainedValue()
        .mark(6,ticket,[Int64(bitPattern:now),Int64(result)])
}

func testRuntime118Upper(_ root: URL) {
    runtime116Reset(root)
    NG2Fake.lock.lock(); NG2Fake.fixedClock = nil; NG2Fake.offset = 0; NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.scheduleTicket = nil
    NG2RuntimeCycleTestHooks.classificationResult = nil
    let id = identity()
    let actual = Runtime118UpperWorld(id), watch = Runtime118CampaignWatch(id), trace = Runtime118UpperTrace(id)
    actual.install(); trace.install()
    defer { trace.stop() }
    fixtureFailureSnapshot = {
        _ = trace.save() // Failure/post-route serialization only, never a hot marker.
        return ["report": .object(report(id)), "cycle": .object(cyclePayload(id)),
        "campaign": .object(runtime116Payload(id, keepalive: false)),
        "directions": .array(actual.locked { actual.gestures.map { .int($0) } }),
        "pose": .array(actual.locked { [.int(Int(actual.x)), .int(Int(actual.y))] }),
        "capture_models": .object(actual.locked { Dictionary(uniqueKeysWithValues:
            actual.captureModels.map { (String($0.key), JSONValue.object($0.value)) }) })] }
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, old, child, index in
        trace.stop() // This callback precedes start(child); root IDs never mix with child IDs.
        require(rootID == id && old == id && child != id && index == 1 &&
            ir110Record(root, id, "continuation_seal") != nil,
            "test118_original_parent_disk_seal_precedes_actual_fresh_child")
        actual.locked { actual.child = child }
    }
    require(runtime118Start(id).1 == nil, "test118_upper_actual_initial_RS_continuous_start")
    pump("test118_normal_upper_all_goods_negative_RS_then_child", timeout: 60) {
        let child = actual.locked { actual.child }
        return trace.progress(watch,child)
    }
    trace.stop(); _ = trace.save()
    let terminal = ir110Record(root, id, "terminal")?["controller"]?.objectValue ?? [:]
    let events = (terminal["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let acknowledged = events.filter { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 }
    let moved = acknowledged.filter { $0["motion"]?.intValue == 1 }
    let child = actual.locked { actual.child }
    let stoppedSnapshot = fixtureFailureSnapshot?() ?? [:]
    _ = call("necro_native_cancel", id); NG2Fake.release()
    watch.lastPoll = 0
    pump("test118_upper_root_and_child_drained", timeout: 40) { watch.stopped() }
    let originalStates = actual.locked { actual.sourceStates }
    runtime118ArchiveStoppedSpool(root,id,sourceStates:originalStates,snapshot:stoppedSnapshot)
    // The normal export API creates PNGs. Drained alone promises only RAW;
    // preserve that original stopped Spool above before asking for export.
    runtime111Manifest(id, required: Set(originalStates.keys.map { Int($0) }))
    runtime118CheckStoppedSources(root,id,originalStates)
    let captured = (stoppedSnapshot["report"]?.objectValue?["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let models = actual.locked { actual.captureModels }
    // A successful goods RS captures the successor floor on the old root
    // before child admission. That later RS prefix is a different physical
    // world; prove every eligible route-prefix capture and every directional
    // source below, rather than treating the bootstrap floor as this shop.
    let lastRoutePrefix = acknowledged.compactMap { $0["id"]?.intValue }.max() ?? 0
    let eligible = captured.filter { $0["stable"]?.boolValue == true &&
        $0["inflight_start"]?.boolValue == false && $0["inflight_end"]?.boolValue == false &&
        ($0["completed_prefix_end"]?.intValue ?? Int.max) <= lastRoutePrefix }
    require(!eligible.isEmpty, "test118_actual_noninflight_capture_pose_evidence_exists")
    for capture in eligible {
        let captureID = UInt64(capture["id"]?.intValue ?? 0), start = capture["start_ns"]?.intValue ?? 0
        guard let model = models[captureID] else {
            require(false, "test118_actual_eligible_capture_has_own_frozen_pose"); return
        }
        let completed = acknowledged.filter { ($0["end_ns"]?.intValue ?? Int.max) <= start }
        var x = 2, y = 0, opened = false
        for event in completed {
            let direction = event["direction"]?.intValue ?? 0
            if !opened && x > 0 { require(direction == 1, "test118_actual_prefix_lead_is_LEFT"); x -= 1 }
            else if !opened { require(direction == 1 && x == 0, "test118_actual_prefix_opens_LEFT"); opened = true }
            else if direction == 1 { x -= 1 }
            else { require(direction == 4, "test118_actual_prefix_inner_DOWN"); y += 1 }
        }
        require(model["completed_paths"]?.intValue == completed.count && model["x"]?.intValue == x &&
            model["y"]?.intValue == y && model["opened"]?.boolValue == opened &&
            capture["completed_prefix_start"] == capture["completed_prefix_end"] &&
            (model["admission_ns"]?.intValue ?? Int.max) <= start &&
            (model["reply_ns"]?.intValue ?? 0) >= (capture["end_ns"]?.intValue ?? Int.max),
            "test118_each_eligible_original_capture_pose_matches_actual_completed_gesture_prefix")
    }
    let eligibleIDs = Set(eligible.compactMap { $0["id"]?.intValue })
    require(acknowledged.allSatisfy { event in
        guard case let .int(source)? = event["source_capture_id"],
              case let .int(observed)? = event["observed_capture_id"],
              source > 0, observed >= 0 else { return false }
        return eligibleIDs.contains(source) && (observed == 0 || eligibleIDs.contains(observed))
    }, "test118_inflight_original_frames_never_authorize_route_input_or_motion_credit")
    require(!child.isEmpty && actual.locked { actual.restarts == 2 && actual.negativeCalls > 0 &&
        actual.partialJobs > 0 && actual.fullJobs > 0 && actual.gestures == [1,1,1,1,1,4,4,4] } &&
        actual.locked { actual.consumedPaths } == NG2Fake.paths().count &&
        moved.count == 7 && acknowledged.count == 8 &&
        acknowledged.map { $0["direction"]?.intValue ?? 0 } == actual.locked { actual.gestures } &&
        acknowledged.map { $0["motion"]?.intValue ?? 0 } == [1,1,3,1,1,1,1,1],
        "test118_open_then_actual_HHDDD_five_MOTION_then_normal_negative_restart")
    require(actual.locked { actual.workerDurations.allSatisfy { $0 > 0 && $0 < 100_000_000 } &&
        actual.baseParent > 0 && actual.allocatedParent >= actual.baseParent } &&
        terminal["moves"]?.intValue == 7 && terminal["door_changes"]?.intValue == 1,
        "test118_real_ACK_is_not_MOTION_credit_and_worker_cost_is_charged")
    require(ir110Record(root, id, "checkpoint") != nil && ir110Record(root, id, "restart_intent") != nil &&
        ir110Record(root, id, "restart_outcome") != nil &&
        runtime118Events(child).allSatisfy { $0["kind"]?.intValue != 3 },
        "test118_normal_negative_durable_checkpoint_intent_ACK_then_successor_without_duplicate_RS")
    runtime118Emit("UPPER", ["root_id": .string(id), "child_id": .string(child),
        "scope": .string("procedural_RGBA_actual_Runtime_Ring_Spool_wall_clock_future"),
        "gesture_directions": .array(actual.locked { actual.gestures.map { .int($0) } }),
        "verified_moves": .int(moved.count), "initial_and_goods_restarts": .int(actual.locked { actual.restarts }),
        "normal_calls": .int(actual.locked { actual.normalCalls }),
        "negative_calls": .int(actual.locked { actual.negativeCalls }),
        "classification_override": .bool(false), "fit_phase_adjustments": .int(0),
        "physical_period_ns": .int(520_000_000), "physical_epoch_ns": .int(Int(actual.physicalEpoch)),
        "wall_clock_charged": .bool(true), "ACK_model_ns": .int(278_756_083),
        "base_parent_ns": .int(Int(actual.locked { actual.baseParent })),
        "allocated_parent_ns": .int(Int(actual.locked { actual.allocatedParent })),
        "allocation_period_ns": .int(Int(actual.locked { actual.allocationPeriod })),
        "parent_history_ns": .array(actual.locked { actual.parents.map { .int(Int($0)) } })])
    runtime116ExportAll(root, id, label: "upper_side_hhddd")
}

// Normal FULL source -> one current DATA job -> only a far FLOOR changes
// while that immutable worker is pending. All ordering below is procedural;
// it is not the iPhone's unrecorded job1/job2 history.
func runtime118CheckPaletteSources(_ root: URL, _ id: String, current: [String: JSONValue],
        palette: UInt64, expected: Data?) {
    let sourceID = UInt64(current["capture_id"]?.intValue ?? 0)
    let folder = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    func original(_ capture: UInt64) -> (Data,[String: JSONValue])? {
        let stem = String(format:"frame-%016llx",capture)
        guard let raw = try? Data(contentsOf: folder.appendingPathComponent(stem+".rgba")),
              let encoded = try? Data(contentsOf: folder.appendingPathComponent(stem+".json")),
              let body = try? JSONDecoder().decode([String: JSONValue].self, from: encoded),
              let metadata = body["metadata"]?.objectValue else { return nil }
        require(body["run_id"]?.stringValue == id && body["capture_id"]?.intValue == Int(capture) &&
            body["raw_sha256"]?.stringValue == NG2CycleWire.hash(raw),
            "test118_palette_pair_original_raw_identity_and_hash")
        return (raw,metadata)
    }
    guard sourceID > 0 && palette > sourceID, let source = original(sourceID), let later = original(palette),
          let expected else { require(false,"test118_palette_pair_immutable_original_pixels_available"); return }
    require(later.0 == expected, "test118_actual_palette_render_equals_original_Spool_RGBA")
    let proofStart = DispatchTime.now().uptimeNanoseconds
    let a = runtime114Scene(source.0), b = runtime114Scene(later.0)
    defer { a.deinitialize(count:1); a.deallocate(); b.deinitialize(count:1); b.deallocate() }
    let first = withUnsafeBytes(of:a.pointee.tiles) { Array($0) }
    let second = withUnsafeBytes(of:b.pointee.tiles) { Array($0) }
    let oldMask = withUnsafeBytes(of:a.pointee.protected_cells) { Array($0) }
    let newMask = withUnsafeBytes(of:b.pointee.protected_cells) { Array($0) }
    let changed = first.indices.filter { first[$0] != second[$0] }
    let far = 6*23+14 // relative (3,1), outside both local3x3 neighborhoods.
    require(a.pointee.goods == 2 && b.pointee.goods == 2 && changed == [far] &&
        first[far] == 1 && second[far] == 4 && oldMask == newMask && oldMask[far] == 0 &&
        (later.1["capture_start_ns"]?.intValue ?? 0) >= (source.1["capture_end_ns"]?.intValue ?? Int.max) &&
        later.1["stable_prefix"]?.boolValue == true && later.1["inflight_start"]?.boolValue == false &&
        later.1["inflight_end"]?.boolValue == false && later.1["completed_prefix_start"] == current["prefix"] &&
        later.1["completed_prefix_end"] == current["prefix"],
        "test118_normal_Perception_exactly_one_far_FLOOR_to_DIRT_no_item_mask_or_local_change")
    require(DispatchTime.now().uptimeNanoseconds > proofStart,"test118_palette_guard_measurement_has_real_cost")
    runtime111PersistedPixels(folder,capture:sourceID,expected:source.0)
    runtime111PersistedPixels(folder,capture:palette,expected:later.0)
}
// DATA-only cache: the C callback copies POD values and never releases a worker
// or advances time. The original afterObserve cost hook runs before release.
final class Runtime118DataSnapshot {
    static let keys = ["job_id","capture_id","capture_start_ns","prefix","level_id",
        "worker_started_ns","deadline_ns","hold_started_ns","continuation_deadline_ns"]
    let id: String
    let lock = NSLock()
    var armed = false, accepted = false, responded = false, matching = false, emitted = false
    var requestID: UInt64 = 0, requestStart: UInt64 = 0, requestEnd: UInt64 = 0, requestPrefix: UInt64 = 0
    var rootStarted: UInt64 = 0, actualID: UInt64 = 0, actualStart: UInt64 = 0, actualEnd: UInt64 = 0
    var actualPrefix: UInt64 = 0, commit: UInt64 = 0, charged: UInt64 = 0
    var status = NG2ControllerStatus(), cycle = NG2ControllerCycleStatus()
    init(_ id: String) { self.id = id }
    func install() { ng2_fixture_data118_install(runtime118DataSnapshotReturned, Unmanaged.passUnretained(self).toOpaque()) }
    func uninstall() { ng2_fixture_data118_install(nil, nil) }
    func arm(_ capture: UInt64, _ start: UInt64, _ end: UInt64, _ prefix: UInt64,
             rootStarted: UInt64, expected: [String: JSONValue]) {
        lock.lock()
        guard !armed else { lock.unlock(); return }
        armed = true; requestID = capture; requestStart = start; requestEnd = end
        requestPrefix = prefix; self.rootStarted = rootStarted
        lock.unlock()
        let values = Self.keys.map { UInt64(max(0, expected[$0]?.intValue ?? 0)) }
        let result = values.withUnsafeBufferPointer {
            ng2_fixture_data118_request(capture,start,end,prefix,rootStarted,$0.baseAddress,$0.count)
        }
        lock.lock(); accepted = result == 1; lock.unlock()
    }
    func copy(_ capture: UInt64, _ start: UInt64, _ end: UInt64, _ prefix: UInt64, _ commit: UInt64,
              _ match: Int32, _ status: NG2ControllerStatus, _ cycle: NG2ControllerCycleStatus) {
        lock.lock(); defer { lock.unlock() }
        actualID = capture; actualStart = start; actualEnd = end; actualPrefix = prefix; self.commit = commit
        self.status = status; self.cycle = cycle; matching = match == 1; responded = true
    }
    func afterChargedObserve(_ capture: UInt64, _ now: UInt64) {
        lock.lock(); defer { lock.unlock() }
        if responded && requestID == capture && actualID == capture && charged == 0 { charged = now }
    }
    func snapshot() -> (NG2ControllerStatus, NG2ControllerCycleStatus, Bool) {
        lock.lock(); defer { lock.unlock() }
        return (status,cycle,accepted && responded && matching && charged > 0)
    }
    // Cold failure/postdrain diagnostics only. Its presence is never a pass.
    func emitOnce() {
        lock.lock()
        guard !emitted else { lock.unlock(); return }; emitted = true
        let value: [String: JSONValue] = ["root_id": .string(id), "root_started_ns": .int(Int(rootStarted)),
            "request_capture_id": .int(Int(requestID)), "request_start_ns": .int(Int(requestStart)),
            "request_end_ns": .int(Int(requestEnd)), "request_prefix": .int(Int(requestPrefix)),
            "actual_capture_id": .int(Int(actualID)), "actual_start_ns": .int(Int(actualStart)),
            "actual_end_ns": .int(Int(actualEnd)), "actual_prefix": .int(Int(actualPrefix)),
            "observe_commit_ns": .int(Int(commit)), "status_started_ns": .int(Int(status.started_ns)),
            "last_capture_id": .int(Int(status.last_capture_id)),
            "last_capture_start_ns": .int(Int(status.last_capture_start_ns)),
            "last_capture_end_ns": .int(Int(status.last_capture_end_ns)),
            "job_id": .int(Int(cycle.job_id)), "capture_id": .int(Int(cycle.capture_id)),
            "capture_start_ns": .int(Int(cycle.capture_start_ns)), "prefix": .int(Int(cycle.prefix)),
            "level_id": .int(Int(cycle.level_id)), "worker_started_ns": .int(Int(cycle.worker_started_ns)),
            "deadline_ns": .int(Int(cycle.deadline_ns)), "hold_started_ns": .int(Int(cycle.hold_started_ns)),
            "continuation_deadline_ns": .int(Int(cycle.continuation_deadline_ns)),
            "pending": .bool(cycle.pending == 1), "request_accepted": .bool(accepted),
            "responded": .bool(responded), "matching": .bool(matching),
            "after_observe_charged_ns": .int(Int(charged))]
        lock.unlock(); runtime118Emit("CURRENT_SNAPSHOT", value)
    }
}
func runtime118DataSnapshotReturned(_ context: UnsafeMutableRawPointer?, _ capture: UInt64, _ start: UInt64,
    _ end: UInt64, _ prefix: UInt64, _ commit: UInt64, _ matching: Int32,
    _ status: UnsafePointer<NG2ControllerStatus>?, _ cycle: UnsafePointer<NG2ControllerCycleStatus>?) {
    guard let context, let status, let cycle else { return }
    Unmanaged<Runtime118DataSnapshot>.fromOpaque(context).takeUnretainedValue()
        .copy(capture,start,end,prefix,commit,matching,status.pointee,cycle.pointee)
}

func testRuntime118Palette(_ root: URL) {
    runtime116Reset(root)
    let id = identity()
    let actual = Runtime114CurrentWorld(id), cost = Runtime118Cost(), watch = Runtime118CampaignWatch(id)
    let dataSnapshot = Runtime118DataSnapshot(id)
    let paletteRelease = DispatchSemaphore(value: 0), oldObservationRelease = DispatchSemaphore(value: 0)
    let gate = NSLock()
    var paletteRequested = false, palette = false, paletteReleased = false
    var paletteIDs = Set<UInt64>(), paletteID: UInt64 = 0, currentBefore = [String: JSONValue]()
    var child = "", initialReturned = false, workerEntry: UInt64 = 0, ringStarted: UInt64 = 0
    var observedPaletteID: UInt64 = 0, committingID: UInt64 = 0
    var lastHeartbeat: UInt64 = 0, oldObservationID: UInt64 = 0
    var rootStarted: UInt64 = 0
    var oldOrder = [String: JSONValue]()
    var sourceStates = [UInt64: [String: JSONValue]]()
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    actual.install(); cost.install(); dataSnapshot.install()
    defer { paletteRelease.signal(); oldObservationRelease.signal(); actual.releaseAll(); cost.uninstall(); dataSnapshot.uninstall() }
    // Reuse the exact public 114 physical world and ordinary producers. Its
    // stage2 is FULL/UNKNOWN; after the independent material view, stage3 is
    // FULL/normal NEGATIVE under the corrected policy17 producer.
    let originalPixels = NG2RuntimeCycleTestHooks.rgba
    NG2RuntimeCycleTestHooks.rgba = { original in
        var bytes = originalPixels?(original) ?? original
        if locked({ palette }) && actual.locked({ actual.stage == 3 }) {
            let count = bytes.count
            bytes.withUnsafeMutableBytes {
                require(ng2_fixture_palette118($0.bindMemory(to: UInt8.self).baseAddress, count) == 1,
                    "test118_only_declared_far_material_changes_in_RGBA")
            }
            let capture = actual.locked { actual.decodeID }
            locked { paletteIDs.insert(capture) }
            actual.locked { actual.rendered[capture] = (3, bytes) }
        }
        return bytes
    }
    let originalCapture = NG2RuntimeTestHooks.beforeCaptureAdmission
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        originalCapture?()
        locked { if paletteRequested { palette = true } }
    }
    let originalAfter = NG2RuntimeTestHooks.afterTicketReturned
    NG2RuntimeTestHooks.afterTicketReturned = { command in
        // Reuse the existing report response for the root's immutable start.
        let snapshot = report(id)
        let event = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            .first { $0["id"]?.intValue == Int(command) } ?? [:]
        if event["kind"]?.intValue == 3 && !locked({ initialReturned }) {
            locked { initialReturned = true; rootStarted = UInt64(max(0, snapshot["started_ns"]?.intValue ?? 0)) }; return
        }
        originalAfter?(command)
    }
    NG2Fake.cycleTap = { x, y in
        require(!(x == 297 && y == 448), "test118_current_DATA_root_never_RESUMEs_old_floor")
        if x == 144 && y == 448 {
            actual.locked { actual.restarts += 1 }
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        }
    }
    // One real stage3 C observation must precede the old normal Ring call.
    // This is only a procedural ordering fence inside its original 100ms
    // worker: the old UNKNOWN result then returns normally, without a result
    // override or any producer/commit parking. The current worker separately
    // waits for this case's one far material observation.
    NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = nil
    NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = nil
    NG2RuntimeCycleTestHooks.beforeClassification = { job in
        let entered = DispatchTime.now().uptimeNanoseconds
        let state = cycleCompanion(id), capture = UInt64(state["capture_id"]?.intValue ?? 0)
        runtime112RecordAdmission(id, state, label: "test118_current_FULL_palette")
        require(state["job_id"]?.intValue == Int(job) && state["pending"]?.boolValue == true,
            "test118_current_DATA_actual_immutable_pending_job")
        locked { sourceStates[capture] = state }
        let first = actual.locked { () -> Bool in
            actual.activeJob = job; actual.workers.append(job)
            guard let raw = actual.rendered[capture]?.1 else {
                require(false, "test118_current_DATA_actual_rendered_source_available"); return false
            }
            // Retaining immutable Data is a COW reference, not a PNG roundtrip.
            actual.sources[capture] = raw
            if actual.oldJob == 0 { actual.oldJob = job; actual.oldState = state; actual.stage = 3; return true }
            require(actual.currentJob == 0, "test118_exactly_one_current_FULL_DATA_worker")
            actual.currentJob = job; actual.currentState = state; return false
        }
        NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 20_000_000; NG2Fake.lock.unlock()
        if first {
            let deadline = UInt64(state["deadline_ns"]?.intValue ?? 0), now = NG2Fake.virtualClock()
            require(deadline > now && oldObservationRelease.wait(
                timeout: .now() + .nanoseconds(Int(deadline-now))) == .success,
                "test118_old_worker_waits_for_one_actual_new_source_C_observation_within_original_deadline")
            let current = cycleCompanion(id), proof = locked { oldOrder }
            require(["job_id","capture_id","capture_start_ns","prefix","level_id","worker_started_ns",
                "deadline_ns","hold_started_ns","continuation_deadline_ns"].allSatisfy { current[$0] == state[$0] } &&
                current["pending"]?.boolValue == true && current["candidate_latched"]?.boolValue == false &&
                proof["proof_count"]?.intValue == 1 && (proof["new_capture_id"]?.intValue ?? 0) > Int(capture) &&
                proof["prefix"] == state["prefix"] &&
                (proof["old_source_end_ns"]?.intValue ?? Int.max) <= (proof["new_start_ns"]?.intValue ?? 0) &&
                (proof["new_start_ns"]?.intValue ?? 0) < (proof["new_end_ns"]?.intValue ?? 0) &&
                (proof["new_end_ns"]?.intValue ?? Int.max) <= (proof["observe_return_ns"]?.intValue ?? 0),
                "test118_one_new_observation_preserves_exact_pending_old_source_worker_prefix_and_parent")
        } else {
            let old = actual.locked { actual.oldState }
            require(state["job_id"] != old["job_id"] && state["capture_id"] != old["capture_id"] &&
                state["prefix"] == old["prefix"] && state["level_id"] == old["level_id"] &&
                state["hold_started_ns"] == old["hold_started_ns"] &&
                state["continuation_deadline_ns"] == old["continuation_deadline_ns"],
                "test118_real_current_DATA_job_keeps_original_parent_prefix_and_level")
            locked { currentBefore = state; paletteRequested = true; workerEntry = NG2Fake.virtualClock() }
            actual.continueCaptures(20_000_000)
            require(paletteRelease.wait(timeout: .now()+10) == .success,
                "test118_current_worker_waits_for_actual_far_material_observation")
        }
        let elapsed = DispatchTime.now().uptimeNanoseconds-entered
        // Capture and C wrappers already advanced logical time; charge at
        // least the whole actual hook elapsed without counting it twice.
        let logical = UInt64(state["worker_started_ns"]?.intValue ?? 0)
        let now = NG2Fake.virtualClock()
        if now < logical+elapsed { NG2Fake.advance(logical+elapsed-now) }
        require(NG2Fake.virtualClock() <= UInt64(state["deadline_ns"]?.intValue ?? 0),
            "test118_procedural_order_fence_does_not_extend_worker_deadline")
        if first { locked {
            oldOrder["release_ns"] = .int(Int(NG2Fake.virtualClock()))
            oldOrder["fence_elapsed_ns"] = .int(Int(elapsed))
        } }
        locked { ringStarted = DispatchTime.now().uptimeNanoseconds }
    }
    let originalRingReturn = NG2RuntimeCycleTestHooks.afterClassificationCall
    NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
        let elapsed = DispatchTime.now().uptimeNanoseconds-locked { ringStarted }
        require(elapsed > 0 && elapsed < 100_000_000, "test118_normal_Ring_computation_measured_within_worker_bound")
        NG2Fake.advance(elapsed)
        if actual.locked({ actual.activeJob == actual.oldJob }) {
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY) && status == 0 && outcome == UInt32(NG2_RING_UNKNOWN),
                "test118_old_normal_UNKNOWN_returns_without_result_override_or_post_producer_parking")
        }
        originalRingReturn?(mode, status, outcome)
    }
    let originalFrameCommit = NG2RuntimeTestHooks.beforeAnalysisFrameCommit
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture,start,end,prefix,stable in
        originalFrameCommit?(capture,start,end,prefix,stable)
        locked { committingID = capture }
        let request = locked { (paletteIDs.contains(capture),currentBefore,rootStarted) }
        if request.0 { dataSnapshot.arm(capture,start,end,prefix,rootStarted:request.2,expected:request.1) }
    }
    let originalObserveReturn = NG2RuntimeObserveTestHooks.afterObserve
    NG2RuntimeObserveTestHooks.afterObserve = {
        originalObserveReturn?()
        // This callback holds the actual run lock: record only the ID whose
        // real C observe just returned. No report, decode or classifier here.
        let capture = locked { committingID }
        dataSnapshot.afterChargedObserve(capture,NG2Fake.virtualClock())
        locked { if paletteIDs.contains(capture) { observedPaletteID = capture } }
        let proof = actual.locked { () -> [String: JSONValue]? in
            let old = actual.oldState, sourceID = UInt64(old["capture_id"]?.intValue ?? 0)
            guard actual.oldJob > 0, actual.currentJob == 0, actual.rendered[capture]?.0 == 3,
                let source = actual.consumed[sourceID], let fresh = actual.consumed[capture],
                capture > sourceID, source.stable, fresh.stable, source.prefix == fresh.prefix,
                fresh.prefix == UInt64(old["prefix"]?.intValue ?? Int.max),
                source.start == UInt64(old["capture_start_ns"]?.intValue ?? 0),
                source.end <= fresh.start, fresh.start < fresh.end else { return nil }
            return ["old_job_id": old["job_id"] ?? .null, "old_source_id": .int(Int(sourceID)),
                "old_source_end_ns": .int(Int(source.end)), "new_capture_id": .int(Int(capture)),
                "new_start_ns": .int(Int(fresh.start)), "new_end_ns": .int(Int(fresh.end)),
                "prefix": old["prefix"] ?? .null, "observe_return_ns": .int(Int(NG2Fake.virtualClock())),
                "worker_started_ns": old["worker_started_ns"] ?? .null,
                "deadline_ns": old["deadline_ns"] ?? .null, "proof_count": .int(1)]
        }
        if let proof, locked({ () -> Bool in
            guard oldObservationID == 0 else { return false }
            oldObservationID = capture; oldOrder = proof; return true
        }) {
            // This hook follows the real C return. stable is the Runtime's
            // exact !inflightStart && !inflightEnd && equal-prefix predicate.
            // No PNG, secondary Perception or report builder runs under it.
            actual.freezeCaptures(); oldObservationRelease.signal()
        }
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let now = NG2Fake.virtualClock()
        if locked({ lastHeartbeat == 0 || now-lastHeartbeat >= 1_000_000_000 }) {
            _ = runtime116Status(id)
            locked { lastHeartbeat = now }
        }
        if actual.locked({ actual.stage == 0 && !actual.aligned }) {
            let snapshot = report(id)
            let align = actual.locked { () -> Bool in
                guard actual.stage == 0, !actual.aligned, (snapshot["beat_period_ns"]?.intValue ?? 0) > 0,
                    !(snapshot["events"]?.arrayValue ?? []).contains(where: { $0.objectValue?["kind"]?.intValue == 4 }) else { return false }
                actual.aligned = true; return true
            }
            if align {
                require(NG2Fake.changeClockAtCaptureBoundary {
                    let now = NG2Fake.virtualClock()
                    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
                    let period: UInt64 = 520_000_000, position = (now-epoch+150_000_000) % period
                    NG2Fake.advance((period+100_000_000-position) % period)
                }, "test114_initial_fit_uses_actual_procedural_hud_phase")
            }
        }
        let observed = locked { observedPaletteID }
        if observed > 0 && locked({ !paletteReleased }) {
            let snapshot = dataSnapshot.snapshot(), last = snapshot.0.last_capture_id
            let state = NG2CycleWire.companion(snapshot.1), before = locked { currentBefore }
            require(snapshot.2 && last == observed && !before.isEmpty && ["job_id","capture_id","capture_start_ns","prefix","level_id",
                "worker_started_ns","deadline_ns","hold_started_ns","continuation_deadline_ns"].allSatisfy {
                    state[$0] == before[$0]
                } && state["pending"]?.boolValue == true,
                "test118_only_DATA_relation_preserves_pending_source_worker_deadline_and_parent")
            locked { paletteID = last; paletteReleased = true }
            actual.freezeCaptures(); paletteRelease.signal()
        }
        if actual.locked({ actual.kernelOutcomes[actual.currentJob] == UInt32(NG2_RING_NEGATIVE) }) {
            actual.continueCaptures(20_000_000)
        }
    }
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, old, next, index in
        require(rootID == id && old == id && next != id && index == 1 &&
            ir110Record(root, id, "continuation_seal") != nil,
            "test118_current_DATA_durable_seal_precedes_actual_child")
        locked { child = next }
    }
    fixtureFailureSnapshot = { dataSnapshot.emitOnce(); return ["report": .object(report(id)), "cycle": .object(cyclePayload(id)),
        "campaign": .object(runtime116Payload(id, keepalive: false)),
        "stage": .int(actual.locked { actual.stage }), "palette_capture": .int(Int(locked { paletteID }))] }
    require(runtime118Start(id).1 == nil, "test118_current_DATA_initial_RS_continuous_start")
    pump("test118_normal_current_FULL_negative_palette_then_RS_child", timeout: 60) {
        let next = locked { child }
        return watch.progress(next)
    }
    let terminal = ir110Record(root, id, "terminal")?["controller"]?.objectValue ?? [:]
    let events = (terminal["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let directions = events.filter { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 }
    let pair = actual.locked { (actual.oldState,actual.currentState,actual.kernelOutcomes[actual.oldJob],actual.kernelOutcomes[actual.currentJob]) }
    let stoppedSnapshot = fixtureFailureSnapshot?() ?? [:]
    _ = call("necro_native_cancel", id); actual.releaseAll(); NG2Fake.release()
    watch.lastPoll = 0
    pump("test118_current_DATA_root_child_all_callbacks_drained", timeout: 40) { watch.stopped() }
    let originalStates = locked { sourceStates }, actualPaletteID = locked { paletteID }
    runtime118ArchiveStoppedSpool(root,id,sourceStates:originalStates,snapshot:stoppedSnapshot)
    runtime111Manifest(id,required:Set(originalStates.keys.map { Int($0) } + (actualPaletteID > 0 ? [Int(actualPaletteID)] : []) +
        (locked { oldObservationID } > 0 ? [Int(locked { oldObservationID })] : [])))
    runtime118CheckStoppedSources(root,id,originalStates)
    for (capture,raw) in actual.locked({ actual.sources }) {
        runtime111PersistedPixels(root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id),capture:capture,expected:raw)
    }
    require(!pair.1.isEmpty && (pair.1["job_id"]?.intValue ?? 0) > (pair.0["job_id"]?.intValue ?? Int.max) &&
        (pair.1["capture_id"]?.intValue ?? 0) >= Int(locked { oldObservationID }) && locked { oldObservationID > 0 },
        "test118_current_DATA_worker_exists_after_one_actual_new_source_observation")
    runtime118CheckPaletteSources(root,id,current:pair.1,palette:actualPaletteID,
        expected:actual.locked { actual.rendered[actualPaletteID]?.1 })
    require(!locked({ child.isEmpty }) && locked { paletteID > 0 && paletteReleased && workerEntry > 0 } &&
        pair.2 == 0 && pair.3 == UInt32(NG2_RING_NEGATIVE) &&
        actual.locked { actual.workers.count == 2 && actual.restarts == 2 } &&
        directions.count == 2 && directions.map { $0["motion"]?.intValue ?? 0 } == [3,1],
        "test118_current_normal_negative_has_no_extra_observation_UP_and_restarts")
    require(ir110Record(root,id,"checkpoint") != nil && ir110Record(root,id,"restart_intent") != nil &&
        ir110Record(root,id,"restart_outcome") != nil,
        "test118_current_DATA_negative_reaches_actual_durable_restart_records")
    runtime118Emit("DATA_ORDER", locked { oldOrder })
    runtime118TickEvidence(cost)
    runtime118Emit("CURRENT_DATA", ["root_id": .string(id), "child_id": .string(locked { child }),
        "old_source": pair.0["capture_id"] ?? .null, "current_source": pair.1["capture_id"] ?? .null,
        "palette_capture": .int(Int(locked { paletteID })), "normal_current_outcome": .int(Int(pair.3 ?? 0)),
        "directional_inputs": .int(directions.count), "extra_observation_inputs": .int(0),
        "classification_override": .bool(false), "observe_tick_Ring_cost_charged": .bool(true),
        "scope": .string("procedural_current_FULL_normal_Ring_palette_DATA_actual_Runtime_Spool")])
    runtime116ExportAll(root,id,label:"full_data_palette")
}

let root118 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime118-"+UUID().uuidString)
try FileManager.default.createDirectory(at: root118, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root118) }
NG2RuntimeCycleTestHooks.spoolRoot = root118
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case118 = CommandLine.arguments.last ?? ""
pump("test118_irregular_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
switch case118 {
case "preinput_refresh": testRuntime118Preinput(root118.appendingPathComponent(case118))
case "upper_side_hhddd": testRuntime118Upper(root118.appendingPathComponent(case118))
case "full_data_palette": testRuntime118Palette(root118.appendingPathComponent(case118))
default: require(false, "test118_unknown_case_is_not_another_fixture")
}
print("PASS TEST118 CASE "+case118)
