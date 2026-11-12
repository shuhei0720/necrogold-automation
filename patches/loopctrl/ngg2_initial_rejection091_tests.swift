// TEST091 INITIAL REJECTION HOST METHOD BEGIN.
    // Seed two coherent HOST-only snapshots and an original raster. Actual
    // Runtime transition validation, pin pressure and public export run; no
    // controller decision, touch or game response is fabricated as acceptance.
    func test091SeedInitialRejection(_ id: String, source: UInt64 = 174,
                                     rejected: UInt64 = 175, command: UInt64 = 14,
                                     rgba: Data, variant: String = "valid",
                                     deferred: Bool = false, recovering: Bool = false) -> Bool {
        let analysis = NG2Analysis()
        let analyzed = rgba.withUnsafeBytes {
            ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, rgba.count,
                            NG2Raster.stride, analysis.scene)
        }
        guard analyzed == 0, analysis.scene.pointee.state == 2 else { return false }
        let authorityAnalysis = NG2Analysis()
        let authorityAnalyzed = rgba.withUnsafeBytes {
            ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, rgba.count,
                            NG2Raster.stride, authorityAnalysis.scene)
        }
        guard authorityAnalyzed == 0, authorityAnalysis.scene.pointee.state == 2,
              authorityAnalysis.scene.pointee.gold_state == 1, authorityAnalysis.scene.pointee.goods == 0 else { return false }
        if variant == "source_state" { authorityAnalysis.scene.pointee.state = 1 }
        if variant == "source_gold" { authorityAnalysis.scene.pointee.gold_state = 2 }
        if variant == "source_goods" { authorityAnalysis.scene.pointee.goods = 1 }
        // This transition need not have a SceneDetail/cell-change record.
        // A GOLD-state-only rejection must retain its original raster too.
        if variant == "gold_only" { analysis.scene.pointee.gold_state = 2 }
        return controlQueue.sync {
            guard let run = lock.ng2Locked({ current }), run.id == id, run.core == nil,
                  let core = ng2_controller_create(Self.now()) else { return false }
            run.core = core
            defer { NG2RuntimeEvidenceTestHooks.snapshot = nil; ng2_controller_destroy(core); run.core = nil }
            let prefix = command-1
            var authorityStart: UInt64 = 0, authorityEnd: UInt64 = 0
            let prepared = lock.ng2Locked { run.lock.ng2Locked { () -> Bool in
                guard exportEligibleLocked(run), run.exportBuildID == nil,
                      let original = selectedExportFrames(run).first else { return false }
                let start = original.end+1, end = original.end+1_000
                authorityStart = original.start; authorityEnd = original.end
                let frame = NG2Frame(id: rejected, start: start, end: end,
                    decodeEnd: end+1, generation: variant == "generation" ? run.generation+1 : run.generation,
                    analysisStart: end+2, analysisEnd: end+3, analysis: analysis,
                    startPrefix: variant == "start_prefix" ? prefix+1 : prefix,
                    prefix: variant == "prefix" ? prefix+1 : prefix,
                    startInFlight: variant == "start_inflight", endInFlight: variant == "end_inflight",
                    stable: variant != "unstable", rgba: rgba, rasterTrace: original.rasterTrace,
                    encodedBytes: original.encodedBytes, diagnosticOrientation: original.diagnosticOrientation)
                let authority = NG2Frame(id: source, start: original.start, end: original.end,
                    decodeEnd: original.decodeEnd, generation: variant == "source_generation" ? run.generation+1 : run.generation,
                    analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                    analysis: authorityAnalysis, startPrefix: variant == "source_start_prefix" ? prefix+1 : prefix,
                    prefix: variant == "source_prefix" ? prefix+1 : prefix,
                    startInFlight: variant == "source_start_inflight", endInFlight: variant == "source_end_inflight",
                    stable: variant != "source_unstable", rgba: rgba, rasterTrace: original.rasterTrace,
                    encodedBytes: original.encodedBytes, diagnosticOrientation: original.diagnosticOrientation)
                run.images = variant == "missing" ? [authority] : variant == "source_missing" ? [frame] : [authority, frame]
                // Only the explicit missing-raster fault seeds an already
                // referenced absent ID; the product must not invent its PNG.
                if variant == "missing" { run.references.insert(rejected) }
                run.exportCache = nil
                return true
            } }
            guard prepared else { return false }
            let saved = run.lock.ng2Locked { () -> (Int32, Bool, Bool, Bool, UInt64) in
                let result = (run.cancelReason, run.stopped, run.terminal, run.inFlight, run.prefix)
                run.cancelReason = 0; run.stopped = false; run.terminal = false; run.inFlight = false; run.prefix = prefix
                return result
            }
            var queued = NG2ControllerStatus()
            queued.input_state = variant == "old_input" ? 3 : 1
            queued.current_command_id = variant == "old_current" ? command+1 : command
            queued.last_completed_id = prefix; queued.inputs = 7; queued.restarts = 11
            queued.last_capture_id = variant == "capture_order" ? rejected : source
            queued.last_capture_start_ns = authorityStart; queued.last_capture_end_ns = authorityEnd
            if variant == "old_reason" { queued.reason = 17 }
            if variant == "old_lead" { queued.lead_confirmed = 1 }
            if variant == "old_x" { queued.x = 1 }
            var pending = NG2ControllerEvent(); pending.command.id = command
            pending.command.kind = variant == "old_kind" ? 2 : 4
            pending.command.source_capture_id = variant == "source_zero" ? 0 : source
            pending.command.source_start_ns = authorityStart+(variant == "old_source_start" ? 1 : 0)
            pending.command.direction = 1; pending.command.x = -1; pending.command.ordinal = 1
            if variant == "old_started" { pending.begin_ns = 1 }
            if variant == "old_outcome" { pending.outcome = 2 }
            NG2RuntimeEvidenceTestHooks.snapshot = ([pending], [])
            let previous = variant == "no_transition" ? nil : cache(run, queued, retainEvidence: false)
            var stopped = queued
            stopped.reason = recovering ? 0 : 17; stopped.input_state = 0; stopped.current_command_id = 0
            stopped.last_capture_id = variant == "capture_id" ? rejected+1 : rejected
            let frame = run.lock.ng2Locked { run.images.first { $0.id == rejected } }
            // Missing evidence still has a coherent recorded capture interval.
            stopped.last_capture_start_ns = frame?.start ?? 100
            stopped.last_capture_end_ns = frame?.end ?? 200
            if variant == "capture_start" { stopped.last_capture_start_ns += 1 }
            if variant == "capture_end" { stopped.last_capture_end_ns += 1 }
            if variant == "last_completed" { stopped.last_completed_id += 1 }
            if variant == "input_changed" { stopped.inputs += 1 }
            if variant == "moves" { stopped.moves = 1 }
            if variant == "lead" { stopped.lead_confirmed = 1 }
            if variant == "x" { stopped.x = 1 }
            if variant == "y" { stopped.y = 1 }
            if variant == "current" { stopped.current_command_id = command }
            if variant == "input" { stopped.input_state = 1 }
            if variant == "reason" { stopped.reason = 10 }
            if variant == "terminal" { stopped.terminal = 1 }
            var failed = pending
            failed.command.id = variant == "event_id" ? command+1 : command
            failed.command.kind = variant == "kind" ? 2 : 4
            failed.command.source_capture_id = variant == "source_id" ? rejected : source
            if variant == "command_ordinal" { failed.command.ordinal += 1 }
            if variant == "command_target" { failed.command.target_ns += 1 }
            if variant == "command_not_before" { failed.command.not_before_ns += 1 }
            if variant == "command_deadline" { failed.command.deadline_ns += 1 }
            if variant == "command_source_start" { failed.command.source_start_ns += 1 }
            if variant == "command_phase_sample" { failed.command.phase_sample_ns += 1 }
            if variant == "command_direction" { failed.command.direction = 2 }
            if variant == "command_x" { failed.command.x = 1 }
            if variant == "command_y" { failed.command.y = 1 }
            failed.begin_ns = variant == "started" ? 1 : 0
            failed.end_ns = frame?.end ?? 200
            failed.outcome = variant == "outcome" ? 2 : 3
            failed.reason = variant == "event_reason" ? 10 : 17
            if variant == "event_end" { failed.end_ns += 1 }
            if variant == "cancelled" { run.lock.ng2Locked { run.cancelReason = 2 } }
            if variant == "stopped" { run.lock.ng2Locked { run.stopped = true } }
            if variant == "run_inflight" { run.lock.ng2Locked { run.inFlight = true } }
            NG2Fake.lock.lock(); let owner = NG2Fake.authenticatedOwnerActive
            if variant == "owner" { NG2Fake.authenticatedOwnerActive = false }
            NG2Fake.lock.unlock()
            NG2RuntimeEvidenceTestHooks.snapshot = ([failed], [])
            cache(run, stopped, retainEvidence: !deferred)
            // An older deferred snapshot must not replace this capture's pin.
            if let previous { retainEvidence(run, previous) }
            NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = owner; NG2Fake.lock.unlock()
            run.lock.ng2Locked {
                run.cancelReason = saved.0; run.stopped = saved.1; run.terminal = saved.2
                run.inFlight = saved.3; run.prefix = saved.4
            }
            var terminal = NG2ControllerStatus(); terminal.terminal = 1; terminal.last_capture_id = 1
            cache(run, terminal)
            return true
        }
    }
// TEST091 INITIAL REJECTION HOST METHOD END.

// TEST091 INITIAL REJECTION FIXTURE BEGIN.
let test091Critical: Set<Int> = [15, 201, 10, 11, 12, 13, 14]
let test091Decisions = Set(24...35)
let test091InvalidRejections = ["old_input", "old_current", "old_reason", "old_lead", "old_x",
    "old_kind", "old_started", "old_outcome", "no_transition", "capture_id", "capture_start", "capture_end",
    "last_completed", "input_changed", "moves", "lead", "x", "y", "current", "input", "reason", "terminal",
    "event_id", "kind", "source_id", "started", "outcome", "event_reason", "event_end", "generation",
    "start_prefix", "prefix", "start_inflight", "end_inflight", "unstable", "cancelled", "stopped",
    "run_inflight", "owner", "source_generation", "source_start_prefix", "source_prefix", "source_start_inflight",
    "source_end_inflight", "source_unstable", "source_missing", "source_state", "source_gold", "source_goods",
    "old_source_start", "source_zero", "capture_order", "command_ordinal", "command_target", "command_not_before",
    "command_deadline", "command_source_start", "command_phase_sample", "command_direction", "command_x", "command_y"]
func test091Seed(_ id: String, source: UInt64 = 174, rejected: UInt64 = 175, command: UInt64 = 14,
                 variant: String = "valid", deferred: Bool = false, recovering: Bool = false) {
    require(runtime.test091SeedInitialRejection(id, source: source, rejected: rejected, command: command,
        rgba: test081Floor(), variant: variant, deferred: deferred, recovering: recovering),
        "test091_seed_coherent_initial_rejection_snapshots")
}
func test091InitialRejectionSurvivesPressure() {
    let id = test081ExportFixture(); test081AllLevels(id); test091Seed(id); test081Pressure(id)
    let manifest = pagedCall(id)
    require(manifest.1 == nil && test081IDs(manifest.0?["exported_capture_ids"]).contains(175),
        "test091_initial_rejection_source_survives_pressure")
    require(test081IDs(manifest.0?["exported_capture_ids"]) == test091Critical.union(test091Decisions).union([175]) &&
        report(id)["pinned_image_count"]?.intValue == 20 && NG2Fake.countTouches() == 0,
        "test091_critical_seven_map_twelve_and_one_rejection_share_twenty_slots")
    print("PASS TEST091 initial rejection preserves seven critical twelve map and one spare")
}
func test091InitialRejectionMetadataAndDeferred() {
    for deferred in [false, true] { for recovering in [false, true] {
        let id = test081ExportFixture(); test081AllLevels(id)
        test091Seed(id, variant: "gold_only", deferred: deferred, recovering: recovering)
        guard let expected = runtime.testOriginalFrameEvidence(id, captureIDs: [175])?[175] else {
            require(false, "test091_original_retained_rejection_raster"); return
        }
        test081Pressure(id)
        let manifest = pagedCall(id)
        let row = (manifest.0?["images"]?.arrayValue ?? []).compactMap { $0.objectValue }
            .first { $0["capture_id"]?.intValue == 175 }
        require(manifest.1 == nil && row != nil && test081Digest(expected.0) == row?["sha256"]?.stringValue &&
            expected.1.allSatisfy { key, value in row?[key] == value } &&
            row?["completed_prefix_start"]?.intValue == 13 && row?["completed_prefix_end"]?.intValue == 13 &&
            row?["stable_prefix"]?.boolValue == true && row?["inflight_start"]?.boolValue == false &&
            row?["inflight_end"]?.boolValue == false && NG2Fake.countTouches() == 0,
            "test091_original_PNG_hash_times_prefix_and_immediate_deferred_recovery_paths")
    } }
    print("PASS TEST091 original metadata and immediate deferred terminal or recovering snapshots")
}
func test091InitialRejectionGuards() {
    for fault in test091InvalidRejections {
        let id = test081ExportFixture(); test091Seed(id, variant: fault); test081Pressure(id)
        let manifest = pagedCall(id)
        require(manifest.1 == nil && !test081IDs(manifest.0?["exported_capture_ids"]).contains(175),
            "test091_invalid_initial_rejection_not_promoted_"+fault)
        require(NG2Fake.countTouches() == 0, "test091_invalid_initial_rejection_never_sends_input_"+fault)
    }
    print("PASS TEST091 precise snapshot owner prefix ID begin0 SCREEN and zero input guards")
}
func test091InitialRejectionReplacementAndMissing() {
    let id = test081ExportFixture(); test081AllLevels(id); test091Seed(id)
    test091Seed(id, source: 180, rejected: 181, command: 15); test081Pressure(id)
    let manifest = pagedCall(id), ids = test081IDs(manifest.0?["exported_capture_ids"])
    require(manifest.1 == nil && ids == test091Critical.union(test091Decisions).union([181]) &&
        !ids.contains(175) && test081IDs(manifest.0?["omitted_capture_ids"]).contains(175),
        "test091_one_rejection_reservation_replaces_prior_slot_honestly")
    let missing = test081ExportFixture(); test091Seed(missing, variant: "missing"); test081Pressure(missing)
    let absent = pagedCall(missing)
    require(absent.1 == nil && !test081IDs(absent.0?["exported_capture_ids"]).contains(175) &&
        test081IDs(absent.0?["omitted_capture_ids"]).contains(175) && NG2Fake.countTouches() == 0,
        "test091_missing_rejection_has_no_substitute_or_synthetic_PNG")
    print("PASS TEST091 single bounded replacement and honest missing raster")
}
func test091InitialRejectionBudgetsAndOwner() {
    let id = test081ExportFixture(); test081AllLevels(id); test091Seed(id); test081Pressure(id)
    test081PaddedPNGs(); defer { NG2RuntimeExportTestHooks.transformExportPNG = nil }
    let manifest = pagedCall(id)
    require(manifest.1 == nil && manifest.0?["retained_images"]?.intValue == 20 &&
        manifest.0?["exported_images"]?.intValue == 20 && manifest.0?["total_bytes"]?.intValue == 10*1024*1024 &&
        manifest.0?["profile"]?.stringValue == "normal-1-1-evidence-v2" &&
        test081IDs(manifest.0?["exported_capture_ids"]) == test091Critical.union(test091Decisions).union([175]),
        "test091_exact_twenty_PNG_ten_MiB_with_all_existing_protected_evidence")
    require(pagedCall(id, owner: "other-owner").1 != nil && call("necro_native_results", id).1 != nil &&
        report(id)["workers_drained"]?.boolValue == true && NG2Fake.countTouches() == 0,
        "test091_same_owner_paged_only_drained_without_input")
    test081ReadAllChunks(id, manifest.0!)
    NG2RuntimeExportTestHooks.transformExportPNG = nil
    let old = test081ExportFixture(evidence: false); test081AllLevels(old); test091Seed(old); test081Pressure(old)
    test081PaddedPNGs()
    let legacy = call("necro_native_results", old), oldManifest = pagedCall(old)
    require(legacy.1 == nil && oldManifest.1 == nil && oldManifest.0?["profile"]?.stringValue == "normal-1-1-v1" &&
        test081IDs(oldManifest.0?["exported_capture_ids"]) == test091Critical.union([1]) &&
        oldManifest.0?["exported_capture_ids"] == legacy.0?["exported_capture_ids"] &&
        oldManifest.0?["total_bytes"]?.intValue == 4*1024*1024 && NG2Fake.countTouches() == 0,
        "test091_original_legacy_eight_priorities_and_four_MiB_are_unchanged")
    print("PASS TEST091 full paged 10MiB owner fence and unchanged legacy 4MiB")
}
// TEST091 INITIAL REJECTION FIXTURE END.
