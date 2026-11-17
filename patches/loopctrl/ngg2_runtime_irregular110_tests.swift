#if NG2_IRREGULAR_TEST110_GREEN
// TEST110 production Runtime callbacks with procedural pixels, clocks, game
// reactions and classifier results. No phone accuracy/speed acceptance.
func ir110Locked<T>(_ gate: NSLock, _ body: () -> T) -> T {
    gate.lock(); defer { gate.unlock() }; return body()
}
func ir110Call(_ id: String, _ mode: String = "status", extra: [String: JSONValue] = [:],
               owner: String = "fixture-owner") -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "mode": .string(mode), "_necro_owner": .string(owner)]
    for (key, value) in extra { params[key] = value }
    return runtime.handle(method: "necro_native_irregular", params: params)
}
func ir110Payload(_ id: String, owner: String = "fixture-owner") -> [String: JSONValue] {
    ir110Call(id, owner: owner).0?["payload"]?.objectValue ?? [:]
}
func ir110State(_ id: String) -> [String: JSONValue] { ir110Payload(id)["irregular"]?.objectValue ?? [:] }
func ir110Cycle(_ id: String) -> [String: JSONValue] { ir110Payload(id)["cycle"]?.objectValue ?? [:] }
func ir110Start(_ id: String) {
    fixtureFailureSnapshot = {
        ["irregular_status": .object(ir110Payload(id)), "controller": .object(report(id)),
         "touches": .int(NG2Fake.countTouches()), "requests": .int(NG2Fake.countRequests())]
    }
    let answer = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-irregular-v1"), "_necro_owner": .string("fixture-owner")])
    require(answer.1 == nil, "irregular110_public_start_accepted")
    pump("irregular110_actual_production_core_enabled", timeout: 20) {
        ir110State(id)["enabled"]?.boolValue == true
    }
}
func ir110Reset(_ root: URL) -> CycleFixtureClock {
    let clock = resetCycleFixture(root)
    NG2RuntimeCycleTestHooks.irregularRGBA = nil
    NG2RuntimeCycleTestHooks.afterIrregularAnalysis = nil
    NG2RuntimeCycleTestHooks.beforeIrregularWrite = nil
    NG2RuntimeCycleTestHooks.beforeIrregularPersistenceCommit = nil
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2RuntimeTestHooks.beforeCaptureDecode = nil
    NG2CycleSpoolTestHooks.writeLimit = nil
    NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.waitForCapturePermit() }
    pump("irregular110_prepare_ready", timeout: 20) {
        ir110Call(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    return clock
}
func ir110Overlay(_ original: Data, _ mode: Int32, direction: Int32 = 0, hearts: Int32 = 0) -> Data {
    var bytes = original
    let count = bytes.count
    bytes.withUnsafeMutableBytes {
        require(ng2_fixture_irregular110($0.bindMemory(to: UInt8.self).baseAddress, count,
            mode, direction, hearts) == 1, "irregular110_procedural_overlay")
    }
    return bytes
}
func ir110Blank() -> Data {
    var bytes = Data(count: 896 * 414 * 4)
    bytes.withUnsafeMutableBytes { raw in
        let p = raw.bindMemory(to: UInt8.self)
        for i in stride(from: 3, to: p.count, by: 4) { p[i] = 255 }
    }
    return bytes
}
func ir110Records(_ root: URL, _ id: String) -> [[String: JSONValue]] {
    let directory = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    let urls = (try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)) ?? []
    return urls.filter { $0.lastPathComponent.hasPrefix("record-") && $0.pathExtension == "json" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }.compactMap { url in
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? JSONDecoder().decode([String: JSONValue].self, from: data)
        }
}
func ir110Record(_ root: URL, _ id: String, _ kind: String) -> [String: JSONValue]? {
    ir110Records(root, id).last { $0["kind"]?.stringValue == kind }?["payload"]?.objectValue
}
func ir110FrameRows(_ payload: [String: JSONValue]) -> [[String: JSONValue]] {
    (payload["frames"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
func ir110CheckFootprint(_ id: String) {
    guard let ids = runtime.testIrregularRetentionIDs(id) else {
        require(false, "irregular110_retention_snapshot_available"); return
    }
    let pinned = Set(ids["pinned"] ?? []), recent = Set(ids["recent"] ?? [])
    let all = pinned.union(ids["irregular"] ?? []).union(ids["cycle"] ?? []).union(ids["initial_found"] ?? [])
    require(pinned.count <= 24 && recent.count <= 4 && all.subtracting(recent).count <= 25,
        "irregular110_immutable_pin_union_stays_within_24_plus_one_handoff")
}
func ir110Publish(_ id: String, required: Set<Int> = [], diagnostic: Bool = false,
                  owner: String = "fixture-owner", frozen: Bool = false) {
    var value: [String: JSONValue]?
    pump("irregular110_manifest_ready", timeout: 40) {
        let answer = ir110Call(id, "manifest", owner: owner)
        if let error = answer.1 { require(error.code == -32094, "irregular110_only_pending_is_polled") }
        value = answer.0?["payload"]?.objectValue
        return value != nil
    }
    guard let value, let text = value["manifest_json"]?.stringValue,
          let bytes = text.data(using: .utf8), let manifestSHA = value["manifest_sha256"]?.stringValue,
          let exportID = value["export_id"]?.stringValue,
          let manifest = try? JSONDecoder().decode([String: JSONValue].self, from: bytes) else {
        require(false, "irregular110_manifest_exact_bytes"); return
    }
    let imageRows = (manifest["images"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let images = Set(imageRows.compactMap { $0["capture_id"]?.intValue })
    guard let evidenceRoot = NG2RuntimeCycleTestHooks.spoolRoot else {
        require(false, "irregular110_actual_evidence_root_available"); return
    }
    var requiredImages = required, boundHashes = [Int: String]()
    for record in ir110Records(evidenceRoot, id) where record["kind"]?.stringValue?.hasPrefix("irregular_") == true {
        for frame in ir110FrameRows(record["payload"]?.objectValue ?? [:]) {
            guard let capture = frame["capture_id"]?.intValue, capture > 0,
                  let hash = frame["rgba_sha256"]?.stringValue, hash.count == 64 else {
                require(false, "irregular110_record_frame_has_closed_capture_and_original_hash"); return
            }
            require(boundHashes[capture] == nil || boundHashes[capture] == hash,
                "irregular110_repeated_record_role_keeps_original_rgba_binding")
            requiredImages.insert(capture); boundHashes[capture] = hash
        }
    }
    require(NG2CycleWire.hash(bytes) == manifestSHA && manifest["profile"]?.stringValue == "normal-1-1-irregular-v1" &&
        manifest["terminal"]?.boolValue == true && manifest["workers_drained"]?.boolValue == true && requiredImages.isSubset(of: images),
        "irregular110_true_profile_hash_and_all_record_referenced_original_images")
    for (capture, hash) in boundHashes {
        let image = imageRows.first { $0["capture_id"]?.intValue == capture }
        require(image?["raw_sha256"]?.stringValue == hash,
            "irregular110_every_record_original_rgba_hash_bound_to_manifest_png_before_publication")
    }
    if diagnostic { require(manifest["complete"]?.boolValue == false, "irregular110_fault_is_diagnostic_export") }
    if frozen { require(manifest["input_state"]?.intValue == 4 && manifest["ui_frozen"]?.boolValue == true,
        "irregular110_unknown_input_remains_frozen_in_export") }
    pump("irregular110_publication_ack", timeout: 30) {
        ir110Call(id, "published", extra: ["export_id": .string(exportID), "manifest_sha256": .string(manifestSHA),
            "archive_sha256": .string(String(repeating: "b", count: 64))], owner: owner)
            .0?["payload"]?.objectValue?["accepted"]?.boolValue == true
    }
}
func ir110ReleaseCaptures() {
    NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
}

// A finite fake UI: live -> strong game over -> only Quick Restart -> a
// different first 1-1 floor. The production Runtime decides every action.
func testIrregular110DeathCallbacksPublic(_ root: URL, variant: String = "lifecycle") {
    let clock = ir110Reset(root), id = identity(), gate = NSLock()
    let live = cyclePixels(goods: false)
    let next = variant == "partial_floor" ? cycleSearchPixels(worldX: 36, variant: 0, goods: 2)
        : cyclePixels(worldX: 36, goods: true)
    let nextEmpty = cyclePixels(worldX: 36, goods: false)
    let laterGoods = variant == "later_goods"
    let dead = ir110Overlay(live, 1), menu = ir110Overlay(live, 3), unknown = ir110Blank()
    var phase = 0, baseline = false, newFloor: UInt64 = 0, classifierCalls = 0
    var postPhase = 0, goodsSource: UInt64 = 0, freezeTail = false, tailFrozen = false, lastTail: UInt64 = 0
    var history = [UInt64](), rawHashes = [UInt64: String](), parentDeadline = 0
    var parked = false, parkAccepted = 0, firstMenuAfterPark: UInt64 = 0
    let writerRelease = DispatchSemaphore(value: 0)
    let saturated = variant == "pin24" || variant == "cancel_pin24"
    let checkpointFault = variant == "storage_checkpoint", outcomeFault = variant == "outcome_storage"
    let heldCheckpoint = variant == "cancel_pin24" || variant == "owner_checkpoint" || variant == "late_checkpoint"
    var storageFaultObserved = false, terminalOwnerDrain = false, checkpointWrites = 0
    let decodePark = variant == "decode_park"
    let triggerRelease = DispatchSemaphore(value: 0), decodeRelease = DispatchSemaphore(value: 0)
    var deathCaptureIDs = Set<UInt64>(), triggerParked = false, decodeParked = false
    var triggerCapture: UInt64 = 0
    let cancelKind = variant == "cancel_continue" ? "irregular_continue_intent" :
        (variant == "cancel_restart" ? "irregular_restart_intent" : "")
    let unknownMenu = variant == "unknown_menu", unknownSynth = variant == "unknown_continue"
    NG2Fake.lock.lock(); NG2Fake.walkPaused = true; NG2Fake.lock.unlock()
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return original }
        return ir110Locked(gate) {
            switch phase {
            case 0: return live
            case 1: return dead
            case 2: return unknownMenu ? unknown : menu
            default:
                if laterGoods {
                    if postPhase == 0 { return nextEmpty }
                    if postPhase == 2 { return unknown }
                }
                return next
            }
        }
    }
    NG2RuntimeCycleTestHooks.afterIrregularAnalysis = { capture, bytes, observation in
        ir110Locked(gate) {
            rawHashes[capture] = NG2CycleWire.hash(bytes)
            if observation.kind == 1 { deathCaptureIDs.insert(capture) }
        }
    }
    if decodePark {
        NG2RuntimeTestHooks.beforeCaptureDecode = { capture in
            let shouldPark = ir110Locked(gate) { () -> Bool in
                guard triggerParked && !decodeParked && capture != triggerCapture else { return false }
                decodeParked = true; return true
            }
            if shouldPark { decodeRelease.wait() }
        }
    }
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, start, _, prefix, stable in
        guard stable && prefix != 0 else { return }
        let shouldPark = ir110Locked(gate) { () -> Bool in
            guard decodePark && !triggerParked && deathCaptureIDs.contains(capture) else { return false }
            triggerParked = true; triggerCapture = capture; return true
        }
        if shouldPark { triggerRelease.wait() }
        let restartACK = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            .last { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }
        let afterRestartACK = restartACK?["id"]?.intValue == Int(prefix) &&
            (restartACK?["end_ns"]?.intValue ?? Int.max) <= Int(start)
        ir110Locked(gate) {
            if phase == 0 && !baseline { baseline = true; if !saturated { phase = 1 } }
            if phase == 3 && afterRestartACK {
                if newFloor == 0 {
                    newFloor = capture
                    if laterGoods { postPhase = 1 }
                    else {
                        goodsSource = capture
                        NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
                    }
                } else if laterGoods && postPhase == 1 {
                    goodsSource = capture; postPhase = 2
                } else if laterGoods && postPhase == 2 && freezeTail {
                    lastTail = capture; tailFrozen = true
                    NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
                }
            }
            if parked && phase == 2 { firstMenuAfterPark = capture }
        }
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        ir110Locked(gate) { classifierCalls += 1 }
        ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), 1, &result)
    }
    NG2Fake.cycleTap = { x, y in
        if x == 297 && y == 448 {
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        } else if x == 90 && y == 447 {
            ir110Locked(gate) { phase = 2 }
            if unknownSynth { NG2Fake.lock.lock(); NG2Fake.failTouch = true; NG2Fake.lock.unlock() }
        } else if x == 144 && y == 448 {
            ir110Locked(gate) { phase = 3 }
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeCycleTestHooks.beforeIrregularWrite = { kind, _ in
        if kind == "irregular_checkpoint" { ir110Locked(gate) { checkpointWrites += 1 } }
        let shouldPark = (variant == "third_menu" && kind == "irregular_restart_intent") ||
            (heldCheckpoint && kind == "irregular_checkpoint") ||
            (laterGoods && kind == "irregular_restart_outcome") || kind == cancelKind
        if (checkpointFault && kind == "irregular_checkpoint") || (outcomeFault && kind == "irregular_restart_outcome") {
            NG2CycleSpoolTestHooks.beforeBoundary = { boundary in
                guard boundary == "file_sync" else { return true }
                if outcomeFault {
                    // Let the actual first-floor raw and metadata finish. The
                    // next file sync is the outcome record, not its image.
                    let capture = ir110Locked(gate) { newFloor }
                    let metadata = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
                        .appendingPathComponent(String(format: "frame-%016llx.json", capture))
                    guard capture != 0 && FileManager.default.fileExists(atPath: metadata.path) else { return true }
                }
                return ir110Locked(gate) {
                    if !storageFaultObserved { storageFaultObserved = true; return false }
                    return true
                }
            }
        }
        guard shouldPark else { return }
        ir110Locked(gate) { parked = true; parkAccepted = report(id)["accepted_frames"]?.intValue ?? 0 }
        writerRelease.wait()
    }
    if variant == "owner_checkpoint" {
        NG2RuntimeCycleTestHooks.afterTerminalDrainPass = { observed, captureDone, captureOutstanding, mainOutstanding in
            if observed == id && captureDone && !captureOutstanding && !mainOutstanding && !runtime.hasLease {
                ir110Locked(gate) { terminalOwnerDrain = true }
            }
        }
    }
    ir110Start(id)
    if decodePark {
        pump("irregular110_trigger_control_and_next_actual_decode_parked", timeout: 30) {
            ir110Locked(gate) { triggerParked && decodeParked }
        }
        triggerRelease.signal()
        pump("irregular110_checkpoint_waits_for_real_decode_pipeline_lease", timeout: 30) {
            ir110State(id)["stage"]?.stringValue == "checkpoint"
        }
        require(NG2CaptureBridge.pendingRequests == 0 &&
            !(runtime.testIrregularRetentionIDs(id)?["capture_pipeline"] ?? []).isEmpty &&
            ir110Locked(gate) { checkpointWrites } == 0 && NG2Fake.countTouches() == 1 && ir110State(id)["durable_ns"]?.intValue == 0,
            "irregular110_jpeg_reply_drain_does_not_finish_decode_or_allow_persistence_ui")
        decodeRelease.signal()
        pump("irregular110_checkpoint_writer_begins_only_after_actual_decode_analysis_handoff", timeout: 30) {
            ir110Locked(gate) { checkpointWrites } == 1
        }
    }
    if saturated {
        pump("irregular110_real_24_history_pins", timeout: 30) {
            ir110Locked(gate) { baseline } && report(id)["pinned_image_count"]?.intValue == 24 &&
                (report(id)["accepted_frames"]?.intValue ?? 0) >= 32
        }
        history = runtime.testIrregularRetentionIDs(id)?["pinned"] ?? []
        require(history.count == 24, "irregular110_history_pressure_is_actual_pin24")
        ir110Locked(gate) { phase = 1 }
    }
    if checkpointFault {
        pump("irregular110_storage_failure_before_first_continue", timeout: 40) {
            ir110Payload(id)["workers_drained"]?.boolValue == true
        }
        let observed = ir110Locked(gate) { storageFaultObserved }
        require(observed && ir110State(id)["held_reason"]?.stringValue == "storage" &&
            NG2Fake.countTouches() == 1 && NG2Fake.paths().isEmpty &&
            (ir110State(id)["durable_ns"]?.intValue ?? 0) == 0 &&
            ir110Record(root, id, "irregular_continue_intent") == nil,
            "irregular110_actual_fsync_failure_never_grants_continue_or_durability")
        NG2CycleSpoolTestHooks.beforeBoundary = nil
        ir110Publish(id, diagnostic: true)
        print("PASS TEST110 actual checkpoint fsync failure holds before destructive input")
        return
    }
    if laterGoods {
        pump("irregular110_outcome_writer_parked_before_normal_goods_admission", timeout: 30) { ir110Locked(gate) { parked } }
        pump("irregular110_later_full_is_data_only_queued_hint", timeout: 30) {
            let wanted = ir110Locked(gate) { goodsSource }
            return wanted != 0 && ir110Cycle(id)["queued_capture_id"]?.intValue == Int(wanted) &&
                ir110Cycle(id)["pending"]?.boolValue == false
        }
        let atGoods = report(id)["accepted_frames"]!.intValue!
        let capturedGoods = ir110Locked(gate) { goodsSource }
        let firstObserved = ir110Locked(gate) { newFloor }
        pump("irregular110_later_goods_survives_25_accepted_unknown_tail", timeout: 40) {
            (report(id)["accepted_frames"]?.intValue ?? 0) >= atGoods + 25
        }
        require(ir110Cycle(id)["queued_capture_id"]?.intValue == Int(capturedGoods) &&
            ir110State(id)["next_floor_capture_id"]?.intValue == Int(firstObserved) &&
            ir110State(id)["outcome_ns"]?.intValue == 0 && ir110Locked(gate) { classifierCalls } == 0,
            "irregular110_original_floor_and_later_goods_are_distinct_uncredited_sources")
        ir110Locked(gate) { freezeTail = true }
        pump("irregular110_unknown_tail_capture_stopped", timeout: 20) { ir110Locked(gate) { tailFrozen } }
        ir110CheckFootprint(id)
        writerRelease.signal()
    }
    if variant == "third_menu" || heldCheckpoint || !cancelKind.isEmpty {
        pump("irregular110_selected_writer_parked", timeout: 30) { ir110Locked(gate) { parked } }
        if variant == "third_menu" {
            let before = ir110Locked(gate) { parkAccepted }
            pump("irregular110_third_menu_committed_during_intent", timeout: 30) {
                (report(id)["accepted_frames"]?.intValue ?? 0) >= before + 3 &&
                    ir110Locked(gate) { firstMenuAfterPark != 0 }
            }
            require(NG2Fake.taps().count == 2 && ir110State(id)["stage"]?.stringValue == "restart_ready",
                "irregular110_intent_writer_has_not_started_restart")
            writerRelease.signal()
        } else {
            let touches = NG2Fake.countTouches()
            require(touches == (variant == "cancel_restart" ? 2 : 1), "irregular110_no_uncommitted_ui_before_cancel")
            if variant == "owner_checkpoint" {
                NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = false; NG2Fake.lock.unlock()
            } else if variant == "late_checkpoint" {
                parentDeadline = ir110State(id)["parent_deadline_ns"]!.intValue!
                clock.advance(4_100_000_000)
            } else {
                _ = call("necro_native_cancel", id)
                require(ir110Payload(id)["workers_drained"]?.boolValue == false,
                    "irregular110_cancel_does_not_fake_writer_drain")
            }
            writerRelease.signal()
            ir110ReleaseCaptures()
            if variant == "owner_checkpoint" {
                pump("irregular110_owner_lost_actual_drain", timeout: 40) { ir110Locked(gate) { terminalOwnerDrain } }
                NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.lock.unlock()
            }
            pump("irregular110_cancelled_writer_actual_drain", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
            if variant == "late_checkpoint" {
                require(ir110State(id)["parent_deadline_ns"]?.intValue == parentDeadline &&
                    ir110State(id)["held_reason"]?.stringValue == "deadline",
                    "irregular110_late_archive_cannot_refresh_parent_or_authorize_ui")
            }
            require(NG2Fake.countTouches() == touches && NG2Fake.paths().isEmpty,
                "irregular110_cancelled_durable_callback_cannot_start_ui")
            if variant == "cancel_pin24" {
                ir110CheckFootprint(id)
                for capture in history {
                    let path = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
                        .appendingPathComponent(String(format: "frame-%016llx.rgba", capture))
                    let bytes = try? Data(contentsOf: path)
                    let expected = ir110Locked(gate) { rawHashes[capture] }
                    require(expected != nil && bytes != nil && bytes.map { NG2CycleWire.hash($0) } == expected,
                        "irregular110_cancelled_history_original_raw_hash_preserved")
                }
            }
            let recovery = "fixture-recovery-owner"
            NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert(recovery); NG2Fake.lock.unlock()
            if !cancelKind.isEmpty {
                var value = [String: JSONValue]()
                pump("irregular110_dangling_intent_readonly_recovery", timeout: 30) {
                    value = ir110Payload(id, owner: recovery)
                    return value["workers_drained"]?.boolValue == true
                }
                require(value["input_state"]?.intValue == 4 && value["ui_frozen"]?.boolValue == true &&
                    NG2Fake.countTouches() == touches,
                    "irregular110_each_dangling_action_recovers_frozen_without_resend")
                let old = runtime.handle(method: "necro_native_cycle", params: ["run_id": .string(id),
                    "mode": .string("status"), "_necro_owner": .string(recovery)])
                require(old.0 == nil && old.1?.code == -32602, "irregular110_old_query_rejects_new_spool")
                ir110Publish(id, diagnostic: true, owner: recovery, frozen: true)
            } else { ir110Publish(id, required: Set(history.map { Int($0) })) }
            print("PASS TEST110 irregular cancelled writer and immutable history/recovery callbacks " + variant)
            return
        }
    }
    if outcomeFault {
        pump("irregular110_actual_restart_outcome_record_fsync_fault_reached", timeout: 40) {
            ir110Locked(gate) { storageFaultObserved }
        }
        ir110ReleaseCaptures()
        pump("irregular110_actual_restart_outcome_fsync_failure_drains", timeout: 40) {
            ir110Payload(id)["workers_drained"]?.boolValue == true
        }
        let first = ir110Locked(gate) { newFloor }, current = report(id), state = ir110State(id)
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        require(ir110Locked(gate) { storageFaultObserved } && first != 0 &&
            state["held_reason"]?.stringValue == "storage" && state["outcome_ns"]?.intValue == 0 &&
            current["restarts"]?.intValue == 0 && ir110Cycle(id)["level_id"]?.intValue == 1 &&
            ir110Cycle(id)["completed_shops"]?.intValue == 0 && ir110Locked(gate) { classifierCalls } == 0 &&
            events.filter { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }.count == 1 &&
            NG2Fake.countTouches() == 3 && NG2Fake.paths().isEmpty &&
            ir110Record(root, id, "irregular_restart_outcome") == nil,
            "irregular110_real_restart_ack_without_outcome_fsync_grants_no_level_restart_shop_or_goods_worker")
        NG2CycleSpoolTestHooks.beforeBoundary = nil
        ir110ReleaseCaptures()
        pump("irregular110_outcome_failure_terminal_record_committed", timeout: 30) {
            ir110Record(root, id, "terminal") != nil
        }
        let rawPath = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
            .appendingPathComponent(String(format: "frame-%016llx.rgba", first))
        let raw = try? Data(contentsOf: rawPath)
        require(raw != nil && raw.map { NG2CycleWire.hash($0) } == NG2CycleWire.hash(next),
            "irregular110_outcome_record_failure_preserves_actual_first_goods_original_raw")
        let recovery = "fixture-outcome-storage-recovery-owner", touches = NG2Fake.countTouches()
        NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert(recovery); NG2Fake.lock.unlock()
        var recovered = [String: JSONValue]()
        pump("irregular110_outcome_failure_same_uuid_readonly_recovery", timeout: 30) {
            recovered = ir110Payload(id, owner: recovery)
            return recovered["workers_drained"]?.boolValue == true
        }
        require(recovered["input_state"]?.intValue == 4 && recovered["ui_frozen"]?.boolValue == true &&
            recovered["irregular"]?.objectValue?["outcome_ns"]?.intValue == 0 &&
            recovered["cycle"]?.objectValue?["completed_shops"]?.intValue == 0 && NG2Fake.countTouches() == touches,
            "irregular110_outcome_failure_recovers_same_uuid_frozen_without_retry_or_shop_credit")
        ir110Publish(id, required: [Int(first)], diagnostic: true, owner: recovery, frozen: true)
        print("PASS TEST110 actual post-restart outcome fsync failure preserves first goods and frozen recovery")
        return
    }
    if unknownSynth {
        pump("irregular110_started_unknown_continue_drains", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
        let value = ir110Payload(id), events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        require(value["input_state"]?.intValue == 4 && value["ui_frozen"]?.boolValue == true &&
            events.filter { $0["kind"]?.intValue == 5 && $0["outcome"]?.intValue == 4 }.count == 1 &&
            events.allSatisfy { $0["kind"]?.intValue != 3 && $0["kind"]?.intValue != 4 } && NG2Fake.taps().count == 2,
            "irregular110_kind5_started_unknown_never_resends_or_restarts")
        ir110Publish(id, frozen: true)
        let nextStart = runtime.handle(method: "necro_native_start", params: ["run_id": .string(identity()),
            "profile": .string("normal-1-1-irregular-v1"), "_necro_owner": .string("fixture-owner")])
        require(nextStart.1 != nil && NG2Fake.taps().count == 2, "irregular110_unknown_poison_blocks_other_uuid")
        print("PASS TEST110 irregular kind5 UNKNOWN actual callback freeze")
        return
    }
    if unknownMenu {
        pump("irregular110_unknown_menu_continue_outcome_durable", timeout: 30) {
            (ir110State(id)["continue_outcome_ns"]?.intValue ?? 0) > 0
        }
        parentDeadline = ir110State(id)["parent_deadline_ns"]!.intValue!
        clock.advance(4_100_000_000)
        pump("irregular110_unknown_menu_held_drained", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
        require(ir110State(id)["held_reason"]?.stringValue == "menu_unrecognized" &&
            ir110State(id)["parent_deadline_ns"]?.intValue == parentDeadline && NG2Fake.taps().count == 2 &&
            (report(id)["events"]?.arrayValue ?? []).allSatisfy { $0.objectValue?["kind"]?.intValue != 3 },
            "irregular110_unknown_menu_has_no_blind_restart_or_deadline_refresh")
        ir110Publish(id)
        print("PASS TEST110 irregular unknown result menu held within original parent")
        return
    }
    pump("irregular110_first_new_floor_normal_candidate_before_next_capture", timeout: 40) {
        ir110Cycle(id)["outcome"]?.stringValue == "candidate" &&
            (ir110State(id)["outcome_ns"]?.intValue ?? 0) > 0
    }
    let first = ir110Locked(gate) { newFloor }, expectedGoods = ir110Locked(gate) { goodsSource }
    let expectedLast = ir110Locked(gate) { laterGoods ? lastTail : newFloor }
    require(first != 0 && expectedGoods != 0 && report(id)["last_capture_id"]?.intValue == Int(expectedLast) &&
        ir110Cycle(id)["capture_id"]?.intValue == Int(expectedGoods) &&
        ir110Cycle(id)["completed_shops"]?.intValue == 1 && ir110Locked(gate) { classifierCalls } == 1,
        "irregular110_same_first_floor_worker_adopted_after_outcome_before_any_new_capture")
    let current = report(id), events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    require(current["restarts"]?.intValue == 1 && current["inputs"]?.intValue == 0 && current["moves"]?.intValue == 0 &&
        (current["motion_references"]?.arrayValue ?? []).isEmpty &&
        events.filter { $0["kind"]?.intValue == 5 && $0["outcome"]?.intValue == 2 }.count == 1 &&
        events.filter { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }.count == 1,
        "irregular110_continue_and_restart_ack_truthful_without_move_credit")
    let records = ir110Records(root, id), kinds = records.compactMap { $0["kind"]?.stringValue }
    let ordered = ["irregular_checkpoint", "irregular_continue_intent", "irregular_continue_outcome",
                   "irregular_restart_intent", "irregular_restart_outcome"]
    require(kinds.filter { $0.hasPrefix("irregular_") } == ordered,
        "irregular110_each_actual_fsync_record_has_its_own_kind_and_order")
    for kind in ordered {
        require(ir110Record(root, id, kind)?["irregular"]?.objectValue?["episode_id"]?.intValue == 1,
            "irregular110_records_bound_to_one_episode")
    }
    let continueIntent = ir110Record(root, id, "irregular_continue_intent")!
    require((continueIntent["command"]?.objectValue?["source_start_ns"]?.intValue ?? 0) >=
        (continueIntent["irregular"]?.objectValue?["durable_ns"]?.intValue ?? Int.max),
        "irregular110_first_continue_uses_capture_started_after_checkpoint_durable")
    let last = ir110Record(root, id, "irregular_restart_outcome")!
    let row = ir110FrameRows(last).first { $0["role"]?.stringValue == "new_floor" }
    require(row?["capture_id"]?.intValue == Int(first) && row?["rgba_sha256"]?.stringValue == NG2CycleWire.hash(laterGoods ? nextEmpty : next),
        "irregular110_immutable_first_floor_actual_rgba_hash_saved")
    ir110CheckFootprint(id)
    if laterGoods { ir110Locked(gate) { postPhase = 3 } }
    ir110ReleaseCaptures(); clock.advance(220_000_000)
    pump("irregular110_candidate_pause_terminal_actual_drain", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
    if laterGoods {
        let final = report(id)
        let pauses = (final["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
            .filter { $0["kind"]?.intValue == 2 && $0["outcome"]?.intValue == 2 }
        let pause = pauses.last
        let observed = (final["captures"]?.arrayValue ?? []).compactMap { $0.objectValue }
            .first { $0["id"]?.intValue == pause?["observed_capture_id"]?.intValue }
        require(pauses.count == 1 && (pause?["observed_capture_id"]?.intValue ?? 0) > 0 &&
            (observed?["start_ns"]?.intValue ?? 0) >= (pause?["end_ns"]?.intValue ?? Int.max) &&
            observed?["completed_prefix_start"]?.intValue == pause?["id"]?.intValue &&
            observed?["completed_prefix_end"]?.intValue == pause?["id"]?.intValue &&
            observed?["inflight_start"]?.boolValue == false && observed?["inflight_end"]?.boolValue == false &&
            observed?["stable"]?.boolValue == true && final["paused"]?.intValue == 1,
            "irregular110_later_goods_normal_pause_requires_one_ack_and_fresh_same_prefix_observation")
        require(ir110Record(root, id, "checkpoint")?["raw_sha256"]?.stringValue == NG2CycleWire.hash(next),
            "irregular110_later_goods_actual_worker_rgba_digest_survives_unknown_tail")
    }
    if saturated {
        for capture in history {
            let path = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
                .appendingPathComponent(String(format: "frame-%016llx.rgba", capture))
            let bytes = try? Data(contentsOf: path)
            let expected = ir110Locked(gate) { rawHashes[capture] }
            require(expected != nil && bytes != nil && bytes.map { NG2CycleWire.hash($0) } == expected,
                "irregular110_trim_preserves_every_durable_history_raw_hash")
        }
    }
    if variant == "recovery_lifecycle" {
        let recovery = "fixture-completed-recovery-owner", before = ir110State(id), touches = NG2Fake.countTouches()
        NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert(recovery); NG2Fake.lock.unlock()
        var recovered = [String: JSONValue]()
        pump("irregular110_completed_kind5_readonly_recovery", timeout: 30) {
            recovered = ir110Payload(id, owner: recovery)
            return recovered["workers_drained"]?.boolValue == true
        }
        let recoveredState = recovered["irregular"]?.objectValue ?? [:]
        require(recovered["input_state"]?.intValue == 0 && recovered["ui_frozen"]?.boolValue == false &&
            recovered["cycle"]?.objectValue?["completed_shops"]?.intValue == 1 &&
            ["prefix", "continue_command_id", "continue_capture_id", "restart_command_id", "next_floor_capture_id"].allSatisfy {
                recoveredState[$0]?.intValue == before[$0]?.intValue
            } && NG2Fake.countTouches() == touches && NG2Fake.paths().isEmpty,
            "irregular110_completed_continue_and_restart_recover_known_without_move_or_retry")
        let old = runtime.handle(method: "necro_native_cycle", params: ["run_id": .string(id),
            "mode": .string("status"), "_necro_owner": .string(recovery)])
        require(old.0 == nil && old.1?.code == -32602, "irregular110_completed_kind5_old_profile_stays_closed")
        ir110Publish(id, required: [Int(first)], owner: recovery)
    } else { ir110Publish(id, required: Set(history.map { Int($0) }).union([Int(first)])) }
    print("PASS TEST110 irregular death/continue/menu/restart/first-floor actual callbacks " + variant)
}

func testIrregular110AnalysisVetoPublic(_ root: URL, promptOnly: Bool) {
    _ = ir110Reset(root)
    let id = identity(), source = promptOnly ? ir110Overlay(cyclePixels(goods: false), 2) : cyclePixels(goods: false)
    if promptOnly {
        var scene = NG2Scene(), companion = NG2IrregularObservation()
        let normal = source.withUnsafeBytes { ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, source.count, 896 * 4, &scene) }
        let separate = source.withUnsafeBytes { ng2_analyze_irregular_rgba($0.bindMemory(to: UInt8.self).baseAddress, source.count, 896 * 4, 0, &companion) }
        require(normal == 0 && scene.state == 2 && separate == 0 && companion.kind == 0 && companion.matches == 1,
            "irregular110_prompt_only_is_actual_old_floor_with_positive_new_veto")
    } else { NG2RuntimeCycleTestHooks.irregularRGBA = { _ in Data() } }
    NG2RuntimeCycleTestHooks.rgba = { _ in source }
    ir110Start(id)
    pump("irregular110_unchecked_companion_never_authorizes_ui", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
    require(NG2Fake.countTouches() == 0 && NG2Fake.paths().isEmpty && report(id)["inputs"]?.intValue == 0,
        "irregular110_analysis_or_death_present_veto_has_zero_game_input")
    if promptOnly { require(ir110State(id)["held_reason"]?.stringValue == "invalid_ui", "irregular110_prompt_only_held") }
    else { require(report(id)["capture_failure"]?.objectValue?["stage"]?.stringValue == "analysis",
        "irregular110_actual_companion_failure_is_analysis_failure") }
    ir110Publish(id)
    print(promptOnly ? "PASS TEST110 positive death-present NONE veto actual callbacks" :
        "PASS TEST110 actual companion analysis failure never becomes unchecked NONE")
}

func testIrregular110PendingCandidatePublic(_ root: URL, variant: String = "candidate") {
    let clock = ir110Reset(root), id = identity(), gate = NSLock(), release = DispatchSemaphore(value: 0)
    let checkpointRelease = DispatchSemaphore(value: 0)
    let live = cyclePixels(), dead = ir110Overlay(cyclePixels(goods: false), 1)
    let menu = ir110Overlay(live, 3), next = cyclePixels(worldX: 36, goods: false)
    let allowRetry = variant == "unknown" || variant == "negative"
    var deadVisible = false, workerEntered = false, checkpointWrites = 0, classifierCalls = 0, uiPhase = 0
    NG2RuntimeCycleTestHooks.rgba = { _ in
        ir110Locked(gate) {
            if uiPhase == 1 { return menu }
            if uiPhase == 2 { return next }
            return deadVisible ? dead : live
        }
    }
    NG2RuntimeCycleTestHooks.beforeClassification = { _ in
        let first = ir110Locked(gate) { () -> Bool in
            classifierCalls += 1
            if !workerEntered { workerEntered = true; return true }
            return false
        }
        if first { release.wait() }
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        if variant == "invalid" {
            ng2_fixture_partial_unknown110(scene, result.started_ns, NG2Runtime.now(), &result)
            result.rows.0.slots.0.icon_score = Double.nan
        } else if variant == "unknown" {
            ng2_fixture_partial_unknown110(scene, result.started_ns, NG2Runtime.now(), &result)
        } else {
            ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), variant == "negative" ? 3 : 2, &result)
        }
    }
    NG2RuntimeCycleTestHooks.beforeIrregularWrite = { kind, _ in
        if kind == "irregular_checkpoint" {
            ir110Locked(gate) { checkpointWrites += 1 }
            if allowRetry { checkpointRelease.wait() }
        }
    }
    NG2Fake.cycleTap = { x, y in
        if x == 90 && y == 447 { ir110Locked(gate) { uiPhase = 1 } }
        else if x == 144 && y == 448 {
            ir110Locked(gate) { uiPhase = 2 }
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    ir110Start(id)
    pump("irregular110_pending_actual_worker_entered", timeout: 20) { ir110Locked(gate) { workerEntered } }
    ir110Locked(gate) { deadVisible = true }
    pump("irregular110_death_quiesces_pending_worker", timeout: 20) { ir110State(id)["stage"]?.stringValue == "quiesce" }
    require(ir110Locked(gate) { checkpointWrites } == 0 && NG2Fake.countTouches() == 0,
        "irregular110_pending_worker_drains_before_checkpoint_or_ui")
    release.signal()
    if allowRetry {
        pump("irregular110_ok_nonpositive_worker_reaches_real_checkpoint_writer", timeout: 30) {
            ir110Locked(gate) { checkpointWrites } == 1
        }
        let cycle = ir110Cycle(id)
        require(ir110State(id)["stage"]?.stringValue == "checkpoint" &&
            cycle["completed_shops"]?.intValue == 0 && cycle["outcome"]?.stringValue == "unknown" &&
            cycle["candidate_latched"]?.boolValue == false && NG2Fake.countTouches() == 0 &&
            ir110Record(root, id, "irregular_checkpoint") == nil && ir110Record(root, id, "checkpoint") == nil,
            "irregular110_ok_unknown_or_negative_quiesce_grants_no_shop_negative_credit_or_unsaved_ui")
        checkpointRelease.signal()
        pump("irregular110_ok_nonpositive_worker_actual_retry_outcome_durable", timeout: 40) {
            (ir110State(id)["outcome_ns"]?.intValue ?? 0) > 0
        }
        let current = report(id), events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        let checkpoint = ir110Record(root, id, "irregular_checkpoint")
        let hint = checkpoint?["assessment_hint"]?.objectValue
        require(current["restarts"]?.intValue == 1 && ir110Cycle(id)["level_id"]?.intValue == 2 &&
            ir110Cycle(id)["completed_shops"]?.intValue == 0 && ir110Cycle(id)["candidate_latched"]?.boolValue == false &&
            ir110Locked(gate) { classifierCalls } == 1 && NG2Fake.countTouches() == 2 && NG2Fake.paths().isEmpty &&
            hint?["status"]?.stringValue == "ok" && hint?["outcome"]?.stringValue == variant &&
            events.filter { $0["kind"]?.intValue == 5 && $0["outcome"]?.intValue == 2 }.count == 1 &&
            events.filter { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }.count == 1 &&
            ir110Record(root, id, "checkpoint") == nil && ir110Record(root, id, "restart_intent") == nil,
            "irregular110_ok_nonpositive_pending_result_retries_once_without_normal_negative_credit")
        _ = call("necro_native_cancel", id)
        pump("irregular110_ok_nonpositive_retry_actual_terminal_drain", timeout: 30) {
            ir110Payload(id)["workers_drained"]?.boolValue == true
        }
        ir110Publish(id)
        print("PASS TEST110 pending OK " + variant + " actual quiesce/checkpoint/retry with zero shop credit")
        return
    }
    pump("irregular110_pending_positive_held_and_drained", timeout: 40) { ir110Payload(id)["workers_drained"]?.boolValue == true }
    require(ir110State(id)["held_reason"]?.stringValue == (variant == "invalid" ? "classification" : "candidate") && ir110Cycle(id)["completed_shops"]?.intValue == 0 &&
        NG2Fake.countTouches() == 0 && ir110Locked(gate) { checkpointWrites } == 0,
        "irregular110_pending_positive_wins_without_negative_shop_credit_or_retry")
    clock.advance(1)
    ir110Publish(id)
    print(variant == "invalid" ? "PASS TEST110 invalid encoded worker result cannot release quiesce" :
        "PASS TEST110 pending positive worker actual drain and conservative hold")
}

// The immutable-session fault is injected only after the actual run has
// drained. Recovery must reject an unknown explicit profile before any UI.
func testIrregular110RecoveryProfileBoundaryPublic(_ root: URL) {
    _ = ir110Reset(root)
    let id = identity(), unknown = ir110Blank()
    NG2RuntimeCycleTestHooks.rgba = { _ in unknown }
    ir110Start(id)
    _ = call("necro_native_cancel", id)
    pump("irregular110_profile_fault_run_actually_drained", timeout: 30) {
        ir110Payload(id)["workers_drained"]?.boolValue == true
    }
    let session = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id).appendingPathComponent("session.json")
    guard let original = try? Data(contentsOf: session),
          var header = (try? JSONSerialization.jsonObject(with: original)) as? [String: Any],
          var provenance = header["provenance"] as? [String: Any] else {
        require(false, "irregular110_actual_session_profile_available"); return
    }
    provenance["native_profile"] = "normal-1-1-unknown-irregular-v1"
    header["provenance"] = provenance
    do { try JSONSerialization.data(withJSONObject: header, options: [.sortedKeys]).write(to: session, options: [.atomic]) }
    catch { require(false, "irregular110_session_profile_fault_injected") }
    let recovery = "fixture-invalid-profile-owner"
    NG2Fake.lock.lock(); NG2Fake.authorizedOwners.insert(recovery); NG2Fake.lock.unlock()
    pump("irregular110_unknown_explicit_profile_recovery_rejected", timeout: 30) {
        ir110Call(id, owner: recovery).1?.code == -32096
    }
    require(NG2Fake.countTouches() == 0 && NG2Fake.paths().isEmpty,
        "irregular110_unknown_profile_never_falls_back_or_sends_input")
    do { try original.write(to: session, options: [.atomic]) }
    catch { require(false, "irregular110_original_session_restored_for_fixture_publication") }
    ir110Publish(id)
    print("PASS TEST110 unknown explicit recovery profile rejected without input")
}

// One real procedural MOVE calibrates lead. The independent world then keeps
// the second LEFT destination occupied; synth still returns its real ACK.
func testIrregular110EnemyRetentionPublic(_ root: URL) {
    _ = ir110Reset(root)
    NG2Fake.reset(.shop)
    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
    let world = SmallShopWorld(direction: 1, iron: false, epoch: epoch)
    NG2Fake.lock.lock(); NG2Fake.shopWorld = world; NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        NG2Fake.waitForCapturePermit(); NG2Fake.performBoundaryClockChange()
    }
    let id = identity(), gate = NSLock(), next = cyclePixels(worldX: 36)
    var enemy = false, nextVisible = false, firstProof: UInt64 = 0, firstAccepted = 0
    var rawHashes = [UInt64: String](), restartTouches = 0
    alignInitialFixtureMove(id)
    NG2RuntimeCycleTestHooks.rgba = { original in
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        let state = ir110Locked(gate) { (enemy, nextVisible) }
        if state.1 { return paused ? original : next }
        if world.snapshot().paused { return original }
        return state.0 ? ir110Overlay(original, 4, direction: 1, hearts: 1) : original
    }
    NG2RuntimeCycleTestHooks.afterIrregularAnalysis = { capture, bytes, _ in
        ir110Locked(gate) { rawHashes[capture] = NG2CycleWire.hash(bytes) }
    }
    NG2Fake.applyShopGesture = { _ in
        if world.snapshot().moves == 0 { return true }
        ir110Locked(gate) { enemy = true }
        // The old period remains520ms. More than25 actual captures fit
        // between its two eligible strict comparisons without extra attempts.
        NG2Fake.lock.lock(); NG2Fake.fixedCaptureAdvance = 10_000_000; NG2Fake.lock.unlock()
        return false
    }
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard events.contains(where: { $0["id"]?.intValue == Int(command) && $0["kind"]?.intValue == 4 }) else { return false }
        NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(id, expectedID: command) }
        callback(); return true
    }
    NG2RuntimeCycleTestHooks.classificationResult = { _, scene, result in
        ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), 1, &result)
    }
    NG2Fake.cycleTap = { x, y in
        if x == 144 && y == 448 {
            ir110Locked(gate) { nextVisible = true; enemy = false; restartTouches += 1 }
            NG2Fake.lock.lock(); NG2Fake.mode = .walk; NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    ir110Start(id)
    pump("irregular110_first_enemy_zero_is_actual_idle_hint", timeout: 40) {
        _ = ir110Call(id, extra: ["keepalive": .bool(true)])
        let value = ir110State(id)
        return value["stage"]?.stringValue == "idle" && value["episode_id"]?.intValue == 0 &&
            (value["proof_capture_id"]?.intValue ?? 0) > 0
    }
    firstProof = UInt64(ir110State(id)["proof_capture_id"]!.intValue!)
    firstAccepted = report(id)["accepted_frames"]!.intValue!
    let originalDeadline = report(id)["motion_wait"]?.objectValue?["deadline_ns"]?.intValue
    let originalPeriod = report(id)["beat_period_ns"]?.intValue
    require((originalDeadline ?? 0) > 0 && (originalPeriod ?? 0) > 0 &&
        report(id)["motion_wait"]?.objectValue?["active"]?.boolValue == true,
        "irregular110_first_zero_keeps_original_live_motion_deadline_and_period")
    pump("irregular110_first_zero_survives_25_accepted_images", timeout: 40) {
        _ = ir110Call(id, extra: ["keepalive": .bool(true)])
        return (report(id)["accepted_frames"]?.intValue ?? 0) >= firstAccepted + 25
    }
    require(ir110State(id)["episode_id"]?.intValue == 0 &&
        ir110State(id)["proof_capture_id"]?.intValue == Int(firstProof) && NG2Fake.paths().count == 2 &&
        report(id)["moves"]?.intValue == 1 && report(id)["motion_wait"]?.objectValue?["deadline_ns"]?.intValue == originalDeadline,
        "irregular110_first_zero_hint_has_no_ui_credit_or_extended_original_motion_bound")
    ir110CheckFootprint(id)
    pump("irregular110_enemy_retry_candidate_actual_drain", timeout: 60) {
        _ = ir110Call(id, extra: ["keepalive": .bool(true)])
        return ir110Payload(id)["workers_drained"]?.boolValue == true
    }
    require(ir110Locked(gate) { restartTouches } == 1 && NG2Fake.paths().count == 2 &&
        report(id)["moves"]?.intValue == 1 && report(id)["inputs"]?.intValue == 2 &&
        ir110Cycle(id)["outcome"]?.stringValue == "candidate",
        "irregular110_enemy_restart_never_resends_move_or_credits_blockage")
    guard let checkpoint = ir110Record(root, id, "irregular_checkpoint"),
          let zero1 = ir110FrameRows(checkpoint).first(where: { $0["role"]?.stringValue == "zero1" }),
          let zero2 = ir110FrameRows(checkpoint).first(where: { $0["role"]?.stringValue == "zero2" }) else {
        require(false, "irregular110_both_original_enemy_proofs_saved"); return
    }
    let events = (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let pause = events.first { $0["kind"]?.intValue == 2 && $0["outcome"]?.intValue == 2 }
    let restartIntent = ir110Record(root, id, "irregular_restart_intent")
    require((pause?["source_start_ns"]?.intValue ?? 0) >=
        (restartIntent?["irregular"]?.objectValue?["durable_ns"]?.intValue ?? Int.max),
        "irregular110_first_pause_uses_capture_started_after_checkpoint_durable")
    let expected = ir110Locked(gate) { rawHashes[firstProof] }
    let rawPath = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
        .appendingPathComponent(String(format: "frame-%016llx.rgba", firstProof))
    let raw = try? Data(contentsOf: rawPath)
    require(expected != nil && raw != nil && zero1["capture_id"]?.intValue == Int(firstProof) && zero1["rgba_sha256"]?.stringValue == expected &&
        raw.map { NG2CycleWire.hash($0) } == expected &&
        (zero2["capture_id"]?.intValue ?? 0) > Int(firstProof) &&
        (zero2["start_ns"]?.intValue ?? 0) - (zero1["start_ns"]?.intValue ?? Int.max) >= (originalPeriod ?? Int.max) &&
        (zero2["end_ns"]?.intValue ?? Int.max) <= (originalDeadline ?? 0) &&
        (checkpoint["proofs"]?.arrayValue ?? []).count == 2 &&
        checkpoint["command"]?.objectValue?["kind"]?.intValue == 4 &&
        checkpoint["ack"]?.objectValue?["outcome"]?.stringValue == "acked",
        "irregular110_saved_first_zero_is_original_actual_rgba_after_long_period_wait")
    ir110Publish(id, required: [Int(firstProof), zero2["capture_id"]!.intValue!])
    print("PASS TEST110 actual first enemy zero retained across25accepted captures and durable retry")
}
#endif
