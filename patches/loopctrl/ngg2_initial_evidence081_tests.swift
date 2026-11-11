// TEST081 RETENTION HOST METHOD BEGIN.
    // HOST-only raster/metadata pressure. It does not create C decisions or
    // game responses; actual cache, pin, eviction and public export run.
    func test081SeedDecision(_ id: String, level: Int32, source: UInt64, command: UInt64,
                             rgba: Data, variant: String = "valid", deferred: Bool = true) -> Bool {
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
            let prefix = command-1
            let prepared = lock.ng2Locked { run.lock.ng2Locked { () -> Bool in
                guard exportEligibleLocked(run), run.exportBuildID == nil,
                      let original = selectedExportFrames(run).first else { return false }
                let frame = NG2Frame(id: source, start: original.start, end: original.end,
                    decodeEnd: original.decodeEnd, generation: variant == "generation" ? run.generation+1 : run.generation,
                    analysisStart: original.analysisStart, analysisEnd: original.analysisEnd, analysis: analysis,
                    startPrefix: variant == "start_prefix" ? prefix+1 : prefix,
                    prefix: variant == "prefix" ? prefix+1 : prefix,
                    startInFlight: variant == "inflight", endInFlight: variant == "end_inflight", stable: variant != "unstable",
                    rgba: rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                    diagnosticOrientation: original.diagnosticOrientation)
                run.images = variant == "missing" ? [] : [frame]
                run.references.insert(source); run.exportCache = nil
                return true
            } }
            guard prepared else { return false }
            var status = NG2ControllerStatus()
            status.input_state = 1; status.current_command_id = command; status.last_completed_id = prefix
            status.restarts = level
            if variant == "reason" { status.reason = 10 }
            if variant == "goods" { status.goods = 1 }
            if variant == "terminal" { status.terminal = 1 }
            if variant == "input" { status.input_state = 3 }
            if variant == "current" { status.current_command_id = command+1 }
            var event = NG2ControllerEvent(); event.command.id = command
            event.command.kind = variant == "kind" ? 4 : 2
            event.command.source_capture_id = source
            if variant == "started" { event.begin_ns = 1 }
            if variant == "outcome" { event.outcome = 2 }
            NG2RuntimeEvidenceTestHooks.snapshot = ([event], [])
            let saved = run.lock.ng2Locked { () -> (Int32, Bool, Bool, UInt64) in
                let result = (run.cancelReason, run.stopped, run.terminal, run.prefix)
                run.cancelReason = variant == "cancelled" ? 2 : 0
                run.stopped = variant == "stopped"; run.terminal = false; run.prefix = prefix
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
            // A terminal snapshot cannot create a new negative judgment.
            status = NG2ControllerStatus(); status.terminal = 1; status.last_capture_id = 1
            cache(run, status)
            return true
        }
    }
    func test081PressureDecisions(_ id: String) -> Bool {
        return controlQueue.sync {
            guard let run = lock.ng2Locked({ current }), run.id == id, run.core == nil,
                  let core = ng2_controller_create(Self.now()) else { return false }
            run.core = core
            defer { NG2RuntimeEvidenceTestHooks.snapshot = nil; ng2_controller_destroy(core); run.core = nil }
            guard let original = lock.ng2Locked({ run.lock.ng2Locked { () -> NG2Frame? in
                guard exportEligibleLocked(run), run.exportBuildID == nil else { return nil }
                run.exportCache = nil
                return selectedExportFrames(run).first
            } }) else { return false }
            func clone(_ capture: UInt64) -> NG2Frame {
                if let retained = run.pinned[capture] ?? run.images.first(where: { $0.id == capture }) { return retained }
                return NG2Frame(id: capture, start: original.start, end: original.end, decodeEnd: original.decodeEnd,
                    generation: run.generation, analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                    analysis: original.analysis, startPrefix: original.startPrefix, prefix: original.prefix,
                    startInFlight: original.startInFlight, endInFlight: original.endInFlight, stable: original.stable,
                    rgba: original.rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                    diagnosticOrientation: original.diagnosticOrientation)
            }
            func move(_ source: UInt64) -> NG2ControllerEvent {
                var event = NG2ControllerEvent(); event.command.id = 600+source
                event.command.kind = 4; event.command.source_capture_id = source; return event
            }
            // Preserve the previously retained map. Fill and churn ordinary
            // evidence via real cache/pin eviction, rather than erasing pins.
            var status = NG2ControllerStatus()
            for capture in UInt64(200)...UInt64(230) {
                run.lock.ng2Locked { run.images = [clone(capture)] }
                NG2RuntimeEvidenceTestHooks.snapshot = ([move(capture)], [])
                cache(run, status)
            }
            run.lock.ng2Locked { run.images = [clone(14)]; run.found = clone(201) }
            NG2RuntimeEvidenceTestHooks.snapshot = ([move(14)], []); cache(run, status)
            run.lock.ng2Locked { run.images = [10, 11, 12, 13].map { clone(UInt64($0)) } }
            let changes = [(UInt64(8), UInt64(9)), (10, 11), (12, 13)].map { source, observed -> NG2ControllerSceneChange in
                var row = NG2ControllerSceneChange(); row.source_capture_id = source; row.observed_capture_id = observed
                return row
            }
            NG2RuntimeEvidenceTestHooks.snapshot = ([move(14)], changes); cache(run, status)
            run.lock.ng2Locked {
                run.images = [15, 16, 17, 18].map { clone(UInt64($0)) }
                run.analyzedFrames = max(run.analyzedFrames, 100)
            }
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
func test081ExportFixture(evidence: Bool = test081EvidenceProfile) -> String {
    NG2Fake.reset(.reply)
    NG2Fake.lock.lock(); NG2Fake.replyData = NG2Fake.pausePNG; NG2Fake.replyError = nil; NG2Fake.lock.unlock()
    let id = identity()
    NG2RuntimeTestHooks.scheduleTicket = { _, callback in
        _ = call("necro_native_cancel", id); callback(); return true
    }
    let result = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "_necro_owner": .string("fixture-owner"),
        "profile": .string(evidence ? "normal-1-1-evidence-v2" : "normal-1-1-v1")])
    require(result.1 == nil, "test081_actual_public_profile_start")
    pump("test081_actual_public_capture_and_drain") { drained(id) }
    NG2RuntimeTestHooks.scheduleTicket = nil
    require(NG2Fake.countTouches() == 0 && (report(id)["retained_image_count"]?.intValue ?? 0) > 0,
        "test081_actual_committed_image_without_input")
    return id
}
func test081IDs(_ value: JSONValue?) -> Set<Int> { Set((value?.arrayValue ?? []).compactMap { $0.intValue }) }
func test081Seed(_ id: String, level: Int32 = 0, source: UInt64 = 24, command: UInt64 = 300,
                 variant: String = "valid", deferred: Bool = true) {
    require(runtime.test081SeedDecision(id, level: level, source: source, command: command,
        rgba: test081Floor(), variant: variant, deferred: deferred), "test081_seed_actual_retention_snapshot")
}
func test081AllLevels(_ id: String, deferred: Bool = true) {
    for level in Int32(0)...Int32(11) {
        test081Seed(id, level: level, source: UInt64(24+level), command: UInt64(300+level), deferred: deferred)
    }
}
func test081Pressure(_ id: String) {
    require(runtime.test081PressureDecisions(id), "test081_actual_cache_eviction_pressure")
}
func test081Digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
func test081PaddedPNGs() {
    NG2RuntimeExportTestHooks.transformExportPNG = { png, _ in
        require(png.count <= 512*1024, "test081_real_PNG_within_per_image_limit")
        var padded = png; padded.append(Data(repeating: 0, count: 512*1024-png.count)); return padded
    }
}
func test081ReadAllChunks(_ id: String, _ manifest: [String: JSONValue]) {
    let exportID = manifest["export_id"]!.stringValue!
    for row in (manifest["images"]?.arrayValue ?? []).compactMap({ $0.objectValue }) {
        let capture = row["capture_id"]!.intValue!, length = row["byte_length"]!.intValue!
        var bytes = Data()
        while bytes.count < length {
            let value = pagedCall(id, mode: .string("chunk"), extra: ["export_id": .string(exportID),
                "capture_id": .int(capture), "offset": .int(bytes.count)])
            require(value.1 == nil && value.0?["offset"]?.intValue == bytes.count &&
                value.0?["byte_length"]?.intValue == length && value.0?["sha256"] == row["sha256"],
                "test081_actual_chunk_identity")
            let part = Data(base64Encoded: value.0!["data_base64"]!.stringValue!)!
            require(!part.isEmpty && part.count <= 64*1024 && bytes.count+part.count <= length,
                "test081_actual_chunk_bound")
            bytes.append(part)
        }
        require(bytes.count == length && test081Digest(bytes) == row["sha256"]!.stringValue!,
            "test081_every_selected_PNG_complete_length_and_hash")
    }
}
func test081AllRestartDecisionsSurvivePressure() {
    let id = test081ExportFixture(); test081AllLevels(id); test081Pressure(id)
    let manifest = pagedCall(id)
    require(manifest.1 == nil && Set(24...35).isSubset(of: test081IDs(manifest.0?["exported_capture_ids"])),
        "test081_all_restart_decision_sources_survive_pressure")
    require(NG2Fake.countTouches() == 0 && report(id)["pinned_image_count"]?.intValue == 20,
        "test081_diagnostic_pressure_never_sends_input_or_adds_pin_slot")
    print("PASS TEST081 all twelve restart decision sources survive pressure")
}
func test081LatestDecisionPerLevelAndMetadata() {
    let id = test081ExportFixture()
    for offset in UInt64(0)...UInt64(39) {
        test081Seed(id, source: 24+offset, command: 300+offset)
    }
    test081Seed(id, level: 1, source: 64, command: 340); test081Pressure(id)
    let manifest = pagedCall(id), ids = test081IDs(manifest.0?["exported_capture_ids"])
    require(manifest.1 == nil && ids.contains(63) && ids.contains(64) && ids.isDisjoint(with: Set(24...62)),
        "test081_latest_reissued_source_per_level_replaces_old_reservation")
    let row = (manifest.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }.first { $0["capture_id"]?.intValue == 63 }!
    let bytes = NG2Raster.png(test081Floor())!
    require(row["sha256"]?.stringValue == test081Digest(bytes) && row["completed_prefix_start"]?.intValue == 338 &&
        row["completed_prefix_end"]?.intValue == 338 && row["stable_prefix"]?.boolValue == true &&
        row["inflight_start"]?.boolValue == false && row["inflight_end"]?.boolValue == false,
        "test081_original_source_PNG_hash_and_prefix_are_preserved")
    test081ReadAllChunks(id, manifest.0!)
    print("PASS TEST081 latest per level and original source metadata")
}
func test081InvalidDecisionEvidence() {
    for fault in ["state", "gold", "goods", "generation", "start_prefix", "prefix", "inflight", "end_inflight",
                  "unstable", "missing", "reason", "terminal", "input", "current", "kind", "started", "outcome", "owner", "cancelled", "stopped"] {
        let id = test081ExportFixture(); test081Seed(id, variant: fault); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(24),
            "test081_invalid_source_not_promoted_"+fault)
        require(NG2Fake.countTouches() == 0, "test081_invalid_evidence_no_input_"+fault)
    }
    for level in [Int32(-1), 12] {
        let id = test081ExportFixture(); test081Seed(id, level: level); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(24),
            "test081_restart_index_must_be_zero_through_eleven")
    }
    print("PASS TEST081 invalid source command owner and restart bounds")
}
func test081BothDecisionCachePaths() {
    for deferred in [false, true] {
        let id = test081ExportFixture(); test081AllLevels(id, deferred: deferred); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && Set(24...35).isSubset(of: test081IDs(manifest.0?["exported_capture_ids"])),
            "test081_all_levels_in_both_cache_paths_"+String(deferred))
    }
    let overlap = test081ExportFixture()
    test081Seed(overlap, source: 12); test081Seed(overlap, level: 1, source: 14, command: 301)
    test081Pressure(overlap)
    let manifest = pagedCall(overlap)
    let selected = (manifest.0?["exported_capture_ids"]?.arrayValue ?? []).compactMap { $0.intValue }
    require(manifest.1 == nil && Set(selected).count == selected.count && Set([12, 14]).isSubset(of: Set(selected)) &&
        (report(overlap)["pinned_image_count"]?.intValue ?? 21) <= 20,
        "test081_map_and_critical_priority_overlap_uses_one_image_slot")
    print("PASS TEST081 immediate and deferred cache paths")
}
func test081ProfileBudgetsAndCompletePagedExport() {
    let id = test081ExportFixture(); test081AllLevels(id); test081Pressure(id); test081PaddedPNGs()
    defer { NG2RuntimeExportTestHooks.transformExportPNG = nil }
    let manifest = pagedCall(id)
    let critical: Set<Int> = [15, 201, 10, 11, 12, 13, 14]
    require(manifest.1 == nil && critical.union(Set(24...35)).isSubset(of: test081IDs(manifest.0?["exported_capture_ids"])) &&
        manifest.0?["profile"]?.stringValue == "normal-1-1-evidence-v2" &&
        manifest.0?["retained_images"]?.intValue == 20 && manifest.0?["exported_images"]?.intValue == 20 &&
        manifest.0?["total_bytes"]?.intValue == 10*1024*1024 && report(id)["pinned_image_count"]?.intValue == 20,
        "test081_twelve_decisions_seven_critical_and_full_20_PNG_10MiB_bound")
    require(call("necro_native_results", id).1 != nil, "test081_evidence_profile_requires_paged_export")
    test081ReadAllChunks(id, manifest.0!)
    NG2RuntimeExportTestHooks.transformExportPNG = nil
    let old = test081ExportFixture(evidence: false); test081AllLevels(old); test081Pressure(old); test081PaddedPNGs()
    let legacy = call("necro_native_results", old), oldManifest = pagedCall(old)
    require(legacy.1 == nil && oldManifest.1 == nil && oldManifest.0?["profile"]?.stringValue == "normal-1-1-v1" &&
        test081IDs(oldManifest.0?["exported_capture_ids"]) == critical.union([1]) &&
        oldManifest.0?["exported_capture_ids"] == legacy.0?["exported_capture_ids"] &&
        oldManifest.0?["total_bytes"]?.intValue == 4*1024*1024,
        "test081_legacy_profile_preserves_original_eight_priorities_and_4MiB")
    print("PASS TEST081 v2 complete paged 10MiB and v1 legacy 4MiB")
}
func test081DecisionOwnershipAndMissingEvidence() {
    let id = test081ExportFixture(); test081AllLevels(id); test081Pressure(id)
    require(pagedCall(id, owner: "other-owner").1 != nil && call("necro_native_results", id, owner: "other-owner").1 != nil,
        "test081_public_export_owner_fence")
    let mismatch = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "_necro_owner": .string("fixture-owner"), "profile": .string("normal-1-1-v1")])
    require(mismatch.1 != nil, "test081_same_run_cannot_change_immutable_profile")
    let manifest = pagedCall(id)
    require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(1) &&
        test081IDs(manifest.0?["omitted_capture_ids"]).contains(1), "test081_old_bootstrap_image_honestly_omitted")
    require(NG2Fake.countTouches() == 0 && report(id)["workers_drained"]?.boolValue == true,
        "test081_preservation_never_claims_or_issues_game_progress")
    _ = test081ExportFixture()
    let historicalMismatch = runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "_necro_owner": .string("fixture-owner"), "profile": .string("normal-1-1-v1")])
    require(historicalMismatch.1 != nil, "test081_historical_run_cannot_change_immutable_profile")
    print("PASS TEST081 immutable profile owner and honest missing evidence")
}
// TEST081 RETENTION FIXTURE END.
