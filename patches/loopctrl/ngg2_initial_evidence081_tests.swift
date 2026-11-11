// TEST081 RETENTION HOST METHOD BEGIN.
    // HOST-only bounded raster/snapshot pressure. No real C decision or
    // controller input is claimed; the production cache/pin/export is used.
    func test081SeedInitialDecision(_ id: String, source: UInt64, rgba: Data,
                                   variant: String = "valid", deferred: Bool = true) -> Bool {
        let analysis = NG2Analysis()
        let analyzed = rgba.withUnsafeBytes {
            ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, rgba.count,
                            NG2Raster.stride, analysis.scene)
        }
        guard analyzed == 0, analysis.scene.pointee.state == 2,
              analysis.scene.pointee.gold_state == 1, analysis.scene.pointee.goods == 0 else { return false }
        if variant == "state" { analysis.scene.pointee.state = 1 }
        if variant == "gold" { analysis.scene.pointee.gold_state = 2 }
        if variant == "goods" { analysis.scene.pointee.goods = 2 }
        return controlQueue.sync {
            guard let run = lock.ng2Locked({ current }), run.id == id, run.core == nil,
                  let core = ng2_controller_create(Self.now()) else { return false }
            run.core = core
            defer { NG2RuntimeEvidenceTestHooks.snapshot = nil; ng2_controller_destroy(core); run.core = nil }
            let prepared = lock.ng2Locked { run.lock.ng2Locked { () -> Bool in
                guard exportEligibleLocked(run), run.exportBuildID == nil,
                      let original = selectedExportFrames(run).first else { return false }
                let prefix: UInt64 = 299
                let frame = NG2Frame(id: source, start: original.start, end: original.end,
                    decodeEnd: original.decodeEnd, generation: variant == "generation" ? run.generation+1 : run.generation,
                    analysisStart: original.analysisStart, analysisEnd: original.analysisEnd, analysis: analysis,
                    startPrefix: prefix, prefix: variant == "prefix" ? prefix+1 : prefix,
                    startInFlight: variant == "inflight", endInFlight: false, stable: variant != "unstable",
                    rgba: rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                    diagnosticOrientation: original.diagnosticOrientation)
                run.images = variant == "missing" ? [] : [frame]
                run.references.insert(source); run.exportCache = nil
                return true
            } }
            guard prepared else { return false }
            var status = NG2ControllerStatus()
            status.input_state = 1; status.current_command_id = 300; status.last_completed_id = 299
            if variant == "reason" { status.reason = 10 }
            if variant == "goods" { status.goods = 1 }
            if variant == "terminal" { status.terminal = 1 }
            if variant == "input" { status.input_state = 3 }
            if variant == "current" { status.current_command_id = 301 }
            var event = NG2ControllerEvent(); event.command.id = 300
            event.command.kind = variant == "kind" ? 4 : 2
            event.command.source_capture_id = source
            if variant == "started" { event.begin_ns = 1 }
            if variant == "outcome" { event.outcome = 2 }
            NG2RuntimeEvidenceTestHooks.snapshot = ([event], [])
            let saved = run.lock.ng2Locked { () -> (Int32, Bool, Bool, UInt64) in
                let result = (run.cancelReason, run.stopped, run.terminal, run.prefix)
                run.cancelReason = 0; run.stopped = false; run.terminal = false; run.prefix = 299
                return result
            }
            NG2Fake.lock.lock(); let owner = NG2Fake.authenticatedOwnerActive
            if variant == "owner" { NG2Fake.authenticatedOwnerActive = false }
            NG2Fake.lock.unlock()
            cache(run, status, retainEvidence: !deferred)
            NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = owner; NG2Fake.lock.unlock()
            run.lock.ng2Locked {
                run.cancelReason = saved.0; run.stopped = saved.1; run.terminal = saved.2; run.prefix = saved.3
            }
            // Restore a terminal diagnostic snapshot. It cannot select a new
            // source and does not make the source a terminal priority frame.
            status = NG2ControllerStatus(); status.terminal = 1; status.last_capture_id = 1
            cache(run, status)
            return true
        }
    }
    func test081PressureInitialDecision(_ id: String) -> Bool {
        return controlQueue.sync {
            guard let run = lock.ng2Locked({ current }), run.id == id, run.core == nil,
                  let core = ng2_controller_create(Self.now()) else { return false }
            run.core = core
            defer { NG2RuntimeEvidenceTestHooks.snapshot = nil; ng2_controller_destroy(core); run.core = nil }
            let seeded = lock.ng2Locked { run.lock.ng2Locked { () -> Bool in
                guard exportEligibleLocked(run), run.exportBuildID == nil,
                      let original = selectedExportFrames(run).first else { return false }
                func clone(_ capture: UInt64) -> NG2Frame {
                    NG2Frame(id: capture, start: original.start, end: original.end, decodeEnd: original.decodeEnd,
                        generation: run.generation, analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                        analysis: original.analysis, startPrefix: original.startPrefix, prefix: original.prefix,
                        startInFlight: original.startInFlight, endInFlight: original.endInFlight, stable: original.stable,
                        rgba: original.rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                        diagnosticOrientation: original.diagnosticOrientation)
                }
                run.pinned = Dictionary(uniqueKeysWithValues: (Array(200...218).map { UInt64($0) }+[14]).map { ($0, clone($0)) })
                run.images = [10, 11, 12, 13].map { clone(UInt64($0)) }
                run.found = clone(201); run.references.formUnion(run.pinned.keys)
                run.analyzedFrames = max(run.analyzedFrames, 64); run.exportCache = nil
                return true
            } }
            guard seeded else { return false }
            let changes = [(UInt64(8), UInt64(9)), (10, 11), (12, 13)].map { source, observed -> NG2ControllerSceneChange in
                var value = NG2ControllerSceneChange(); value.source_capture_id = source; value.observed_capture_id = observed
                return value
            }
            let events = [UInt64(219), 14].enumerated().map { index, source -> NG2ControllerEvent in
                var event = NG2ControllerEvent(); event.command.id = UInt64(index+1)
                event.command.kind = 4; event.command.source_capture_id = source; return event
            }
            NG2RuntimeEvidenceTestHooks.snapshot = (events, changes)
            var status = NG2ControllerStatus(); cache(run, status)
            let advanced = lock.ng2Locked { run.lock.ng2Locked { () -> Bool in
                guard let original = run.images.first else { return false }
                run.images = [15, 16, 17, 18].map { capture -> NG2Frame in
                    NG2Frame(id: UInt64(capture), start: original.start, end: original.end, decodeEnd: original.decodeEnd,
                        generation: run.generation, analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                        analysis: original.analysis, startPrefix: original.startPrefix, prefix: original.prefix,
                        startInFlight: original.startInFlight, endInFlight: original.endInFlight, stable: original.stable,
                        rgba: original.rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                        diagnosticOrientation: original.diagnosticOrientation)
                }
                return true
            } }
            guard advanced else { return false }
            status.terminal = 1; status.last_capture_id = 15; cache(run, status)
            return true
        }
    }
// TEST081 RETENTION HOST METHOD END.

// TEST081 RETENTION FIXTURE BEGIN.
import CryptoKit
func test081Floor() -> Data {
    var rgba = Data(count: 896*414*4), tiles = [UInt8](repeating: 1, count: 33*33)
    tiles[6*33+26] = 4
    let size = rgba.count
    let valid = tiles.withUnsafeBufferPointer { map in rgba.withUnsafeMutableBytes { raw in
        ng2_fixture_shop_rgba(raw.bindMemory(to: UInt8.self).baseAddress, size, 0, 0, 0.3,
            map.baseAddress, map.count, 10, -10, 3, 0)
    } }
    require(valid == 1, "test081_floor_procedural_pixels")
    return rgba
}
func test081IDs(_ value: JSONValue?) -> Set<Int> { Set((value?.arrayValue ?? []).compactMap { $0.intValue }) }
func test081Seed(_ id: String, _ source: UInt64 = 24, variant: String = "valid", deferred: Bool = true) {
    require(runtime.test081SeedInitialDecision(id, source: source, rgba: test081Floor(), variant: variant, deferred: deferred),
        "test081_seed_actual_retention_snapshot")
}
func test081Pressure(_ id: String) {
    require(runtime.test081PressureInitialDecision(id), "test081_seed_saturated_real_cache_pressure")
}
func test081InitialDecisionSurvivesPressure() {
    let id = publicExportFixture(); test081Seed(id); test081Pressure(id)
    let manifest = pagedCall(id)
    require(manifest.1 == nil && test081IDs(manifest.0?["exported_capture_ids"]).contains(24),
        "test081_initial_decision_source_survives_pressure")
    require(NG2Fake.countTouches() == 0 && report(id)["pinned_image_count"]?.intValue == 20,
        "test081_diagnostic_pressure_never_sends_input_or_adds_pin_slot")
    print("PASS TEST081 initial decision source survives pressure")
}
func test081InitialDecisionFirstOnlyAndMetadata() {
    let id = publicExportFixture(); test081Seed(id); test081Seed(id, 25); test081Pressure(id)
    let manifest = pagedCall(id), legacy = call("necro_native_results", id)
    require(manifest.1 == nil && legacy.1 == nil, "test081_both_public_export_producers")
    let ids = test081IDs(manifest.0?["exported_capture_ids"])
    require(ids.contains(24) && !ids.contains(25), "test081_first_valid_negative_source_is_not_replaced")
    let row = (manifest.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["capture_id"]?.intValue == 24 }!
    let full = (legacy.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["capture_id"]?.intValue == 24 }!
    let bytes = NG2Raster.png(test081Floor())!, sha = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    require(row["sha256"]?.stringValue == sha && Data(base64Encoded: full["data_base64"]!.stringValue!) == bytes &&
        row["completed_prefix_start"]?.intValue == 299 && row["completed_prefix_end"]?.intValue == 299 &&
        row["stable_prefix"]?.boolValue == true && row["inflight_start"]?.boolValue == false &&
        row["inflight_end"]?.boolValue == false, "test081_source_PNG_hash_and_original_prefix_are_preserved")
    print("PASS TEST081 first source and original PNG metadata")
}
func test081InitialDecisionInvalidEvidence() {
    for fault in ["state", "gold", "goods", "generation", "prefix", "inflight", "unstable", "missing", "reason", "terminal", "input", "current", "kind", "started", "outcome", "owner"] {
        let id = publicExportFixture(); test081Seed(id, variant: fault); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(24),
            "test081_invalid_source_not_promoted_"+fault)
        require(NG2Fake.countTouches() == 0, "test081_invalid_evidence_has_no_input_"+fault)
    }
    print("PASS TEST081 invalid source and command evidence rejected")
}
func test081InitialDecisionBothCachePaths() {
    for deferred in [false, true] {
        let id = publicExportFixture(); test081Seed(id, deferred: deferred); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && test081IDs(manifest.0?["exported_capture_ids"]).contains(24),
            "test081_both_cache_paths_preserve_initial_source_"+String(deferred))
    }
    print("PASS TEST081 immediate and deferred cache paths")
}
func test081InitialDecisionBudgetsAndPriority() {
    let id = publicExportFixture(); test081Seed(id); test081Pressure(id)
    NG2RuntimeExportTestHooks.transformExportPNG = { png, _ in
        require(png.count <= 512*1024, "test081_real_PNG_within_per_image_limit")
        var padded = png; padded.append(Data(repeating: 0, count: 512*1024-png.count)); return padded
    }
    defer { NG2RuntimeExportTestHooks.transformExportPNG = nil }
    let manifest = pagedCall(id), legacy = call("necro_native_results", id)
    let expected: Set<Int> = [15, 201, 24, 10, 11, 12, 13, 14]
    require(manifest.1 == nil && legacy.1 == nil && test081IDs(manifest.0?["exported_capture_ids"]) == expected &&
        manifest.0?["exported_capture_ids"] == legacy.0?["exported_capture_ids"] &&
        manifest.0?["retained_images"]?.intValue == 20 && manifest.0?["total_bytes"]?.intValue == 4*1024*1024 &&
        report(id)["pinned_image_count"]?.intValue == 20, "test081_original_eight_priorities_and_exact_4MiB_20_pin_bounds")
    print("PASS TEST081 original priority and image budgets")
}
func test081InitialDecisionOwnershipAndMissing() {
    let id = publicExportFixture(); test081Seed(id); test081Pressure(id)
    require(pagedCall(id, owner: "other-owner").1 != nil && call("necro_native_results", id, owner: "other-owner").1 != nil,
        "test081_public_export_owner_fence")
    let manifest = pagedCall(id)
    require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(1) &&
        test081IDs(manifest.0?["omitted_capture_ids"]).contains(1), "test081_old_bootstrap_image_is_honestly_omitted")
    require(NG2Fake.countTouches() == 0 && report(id)["workers_drained"]?.boolValue == true,
        "test081_preservation_does_not_claim_or_issue_game_progress")
    print("PASS TEST081 owner and honest missing evidence")
}
// TEST081 RETENTION FIXTURE END.
