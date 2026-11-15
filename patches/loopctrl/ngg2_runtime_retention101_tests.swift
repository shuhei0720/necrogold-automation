// Appended ONLY to staged HOST Runtime files by the TEST101 checker. The same
// component seam compiles with old/new Runtime and never names the new field.
// Frames/snapshots are procedural diagnostic pressure, not C/input evidence.
#if NG2_RUNTIME_HOST_TEST
extension NG2Runtime {
    func test101Retention(_ root: URL) throws {
        let oldPriority: Set<UInt64> = Set([15,201,10,11,12,13,14,437,40,41,42] + Array(24...35))
        require101(oldPriority.count == 23, "retention101_old_priority_inventory")
        let base = Self.now() - 2_000_000
        func frame(_ id: UInt64, generation: UInt64 = 1, prefix: UInt64 = 7) -> NG2Frame {
            let analysis = NG2Analysis()
            analysis.scene.pointee.abi_version = 1
            analysis.scene.pointee.struct_size = UInt32(MemoryLayout<NG2Scene>.size)
            analysis.scene.pointee.state = 2; analysis.scene.pointee.gold_state = 1
            var raw = Data(repeating: 255, count: 896*414*4)
            raw[0] = UInt8(id & 255); raw[1] = UInt8((id >> 8) & 255); raw[2] = 101
            let start = base + id*1_000
            return NG2Frame(id: id, start: start, end: start+100, decodeEnd: start+110,
                generation: generation, analysisStart: start+120, analysisEnd: start+130,
                analysis: analysis, startPrefix: prefix, prefix: prefix, startInFlight: false,
                endInFlight: false, stable: true, rgba: raw,
                rasterTrace: NG2Raster.Trace(sourceWidth: 896, sourceHeight: 414, orientation: 1,
                    sourceNs: 0, drawNs: 0, orientNs: 0, scaleNs: 0, copyPixels: 896*414),
                encodedBytes: 0, diagnosticOrientation: 1)
        }
        func snapshot(_ status: NG2ControllerStatus, _ events: [NG2ControllerEvent],
                      _ changes: [NG2ControllerSceneChange] = [],
                      stop: NG2ControllerStopDetail = NG2ControllerStopDetail()) -> NG2ControllerSnapshot {
            NG2ControllerSnapshot(status: status, events: events, changes: changes, details: [],
                motionWait: NG2ControllerMotionWait(), motionReferences: [],
                recovery: NG2ControllerRecoveryStatus(), recoveryRecords: [],
                stopDetail: stop, handoff: NG2ControllerHandoff())
        }
        func prepare(_ profile: String = Self.cycleProfile, fault: String = "", full: Bool = false)
            -> (NG2Run, [UInt64: NG2Frame], NG2ControllerSnapshot) {
            let id = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
            let run = NG2Run(owner: "fixture-owner", id: id, now: base, profile: profile)
            var frames: [UInt64: NG2Frame] = [:]
            for id in oldPriority.union([43,200,436,500,501,502,503]) { frames[id] = frame(id) }
            if fault == "source_generation" { frames[436] = frame(436, generation: 2) }
            if fault == "observed_generation" { frames[437] = frame(437, generation: 2) }
            if fault == "source_prefix" { frames[436] = frame(436, prefix: 8) }
            if fault == "observed_prefix" { frames[437] = frame(437, prefix: 8) }
            let source = frames[436]!, observed = frames[437]!
            run.initial = frames[200]; run.found = frames[201]; run.prefix = 7
            run.images = [frames[500]!, frames[501]!, source, observed]
            let priorIDs = profile == Self.cycleProfile ? oldPriority.union(full ? [43] : []) : oldPriority.subtracting([40,41,42])
            for id in priorIDs { run.pinned[id] = frames[id] }
            var command = NG2Command()
            command.id = 22; command.ordinal = 4; command.target_ns = base+2_000_000_000
            command.not_before_ns = command.target_ns-150_000_000; command.deadline_ns = command.not_before_ns+10_000_000
            command.source_capture_id = 436; command.source_start_ns = source.start
            command.phase_sample_ns = base; command.kind = 4; command.direction = 3; command.y = -1
            var pending = NG2ControllerEvent(); pending.command = command
            var rejected = pending; rejected.outcome = 3; rejected.reason = 17
            rejected.end_ns = observed.end; rejected.observed_capture_id = observed.id
            if fault == "phase_sample" { rejected.command.phase_sample_ns += 1 }
            if fault == "begun" { rejected.begin_ns = base+1 }
            var old = NG2ControllerStatus()
            old.abi_version = 1; old.struct_size = UInt32(MemoryLayout<NG2ControllerStatus>.size)
            old.phase = 4; old.input_state = 1; old.current_command_id = 22; old.last_completed_id = 7
            old.started_ns = base; old.last_capture_id = source.id
            old.last_capture_start_ns = source.start; old.last_capture_end_ns = source.end
            var current = old
            current.input_state = 0; current.current_command_id = 0; current.reason = 17
            current.last_capture_id = observed.id; current.last_capture_start_ns = observed.start
            current.last_capture_end_ns = observed.end
            // Establish old pressure from its own immutable snapshot first.
            // Every priority raster is already present, never invented by a
            // later lookup into this fixture's dictionary.
            pressure(run,frames,snapshot(old,[pending]),full: full)
            run.images = [frames[500]!,frames[501]!,source,observed]
            run.controllerSnapshot = snapshot(old, [pending])
            let latest = snapshot(current, [rejected])
            run.references.formUnion([436,437])
            // Same owner/generation/prefix/identity guards as production; only
            // procedural diagnostic state is supplied to the private helper.
            run.lock.ng2Locked { retainInitialRejectionLocked(run, latest) }
            run.controllerSnapshot = latest
            return (run, frames, latest)
        }
        func pressure(_ run: NG2Run, _ frames: [UInt64: NG2Frame], _ previous: NG2ControllerSnapshot, full: Bool = false) {
            run.found = frames[201]; run.initial = frames[200]
            run.restartDecisionCaptureIDs = Dictionary(uniqueKeysWithValues: (0..<12).map { ($0, UInt64($0+24)) })
            run.images = [frames[500]!,frames[501]!,frames[502]!,frames[503]!]
            var last = previous.status; last.terminal = 1; last.last_capture_id = 15
            last.last_capture_start_ns = frames[15]!.start; last.last_capture_end_ns = frames[15]!.end
            var move = NG2ControllerEvent(); move.command.id = 23; move.command.kind = 4
            move.command.source_capture_id = 14; move.outcome = 3; move.reason = 17
            var a = NG2ControllerSceneChange(); a.source_capture_id = 8; a.observed_capture_id = 9
            var b = NG2ControllerSceneChange(); b.source_capture_id = 10; b.observed_capture_id = 11
            var c = NG2ControllerSceneChange(); c.source_capture_id = 12; c.observed_capture_id = 13
            var stop = NG2ControllerStopDetail(); stop.abi_version = 1
            stop.struct_size = UInt32(MemoryLayout<NG2ControllerStopDetail>.size)
            stop.valid = 1; stop.stage = 1; stop.reason = 17; stop.prefix = 7
            stop.source_capture_id = 40; stop.observed_capture_id = 41; stop.anchor_capture_id = 42
            stop.last_comparison_capture_id = full ? 43 : 0
            let next = snapshot(last, [move], [a,b,c],stop: stop); run.controllerSnapshot = next
            run.lock.ng2Locked { retainEvidenceLocked(run, next) }
        }
        func selected(_ run: NG2Run) -> Set<UInt64> {
            run.lock.ng2Locked { Set(selectedExportFrames(run).map { $0.id }) }
        }
        func register(_ run: NG2Run) {
            run.terminal = true; run.stopped = true; run.lease = false; run.captureWorkerDone = true
            lock.ng2Locked { current = run }
        }
        func unregister(_ run: NG2Run) {
            lock.ng2Locked { if current === run { current = nil } }
        }
        func status(_ run: NG2Run) -> [String: JSONValue] {
            handle(method: "necro_native_status", params: ["run_id": .string(run.id),
                "_necro_owner": .string(run.owner)]).0?["report"]?.objectValue ?? [:]
        }
        func missing(_ run: NG2Run) -> Set<Int> {
            Set((status(run)["missing_capture_ids"]?.arrayValue ?? []).compactMap { $0.intValue })
        }
        let (run, frames, previous) = prepare()
        pressure(run, frames, previous)
        let expected = oldPriority.union([436])
        require101(selected(run) == expected && run.pinned.count == 24,
                   "retention101_coherent_source_and_observed_survive_recent_eviction")
        require101(run.images.count == 4 && !run.images.contains(where: { $0.id == 436 || $0.id == 437 }),
                   "retention101_pair_is_outside_recent_four")
        register(run)
        require101(!missing(run).contains(436) && !missing(run).contains(437), "retention101_retained_pair_has_no_missing_reference")
        run.cycle!.spool = try NG2CycleSpool.testCreate(rootURL: root, runID: run.id, owner: run.owner)
        persistCycleTerminal(run)
        pump101("retention101_actual_terminal_persistence") { run.lock.ng2Locked { run.cycle!.terminalPersisted } }
        var wire: [String: JSONValue] = [:]
        pump101("retention101_public_cycle_manifest") {
            let answer = self.handle(method: "necro_native_cycle", params: ["run_id": .string(run.id),
                "mode": .string("manifest"), "_necro_owner": .string(run.owner)])
            if let error = answer.1 { require101(error.code == -32094, "retention101_only_pending_export_retries") }
            wire = answer.0?["payload"]?.objectValue ?? [:]
            return wire["manifest_json"]?.stringValue != nil
        }
        let manifest = try JSONDecoder().decode([String: JSONValue].self, from: Data(wire["manifest_json"]!.stringValue!.utf8))
        let images = (manifest["images"]?.arrayValue ?? []).compactMap { $0.objectValue }
        require101(Set(images.compactMap { $0["capture_id"]?.intValue }) == Set(expected.map { Int($0) }),
                   "retention101_all_old_priorities_and_pair_in_normal_export")
        let spool = run.cycle!.spool!
        for id in [UInt64(436),UInt64(437)] {
            let original = frames[id]!, row = images.first { $0["capture_id"]?.intValue == Int(id) }!
            let ref = try spool.frames().first { $0.captureID == id }!
            let metadata = try spool.frameMetadata(ref)
            require101(row["raw_sha256"]?.stringValue == NG2CycleWire.hash(original.rgba) &&
                ref.rawSHA256 == NG2CycleWire.hash(original.rgba) &&
                (metadata["capture_start_ns"] as? NSNumber)?.uint64Value == original.start &&
                (metadata["capture_end_ns"] as? NSNumber)?.uint64Value == original.end &&
                (metadata["generation"] as? NSNumber)?.uint64Value == original.generation &&
                (metadata["completed_prefix_start"] as? NSNumber)?.uint64Value == 7 &&
                (metadata["completed_prefix_end"] as? NSNumber)?.uint64Value == 7,
                "retention101_original_pair_hash_time_generation_prefix_preserved")
            var png = Data()
            while png.count < row["bytes"]!.intValue! {
                var chunk: [String: JSONValue] = [:]
                pump101("retention101_normal_png_chunk") {
                    let answer = self.handle(method: "necro_native_cycle", params: ["run_id": .string(run.id),
                        "mode": .string("chunk"), "_necro_owner": .string(run.owner), "export_id": wire["export_id"]!,
                        "capture_id": .int(Int(id)), "offset": .int(png.count)])
                    if let error = answer.1 { require101(error.code == -32094, "retention101_only_pending_chunk_retries") }
                    chunk = answer.0?["payload"]?.objectValue ?? [:]
                    return chunk["data_base64"]?.stringValue != nil
                }
                png.append(Data(base64Encoded: chunk["data_base64"]!.stringValue!)!)
            }
            require101(png.count == row["bytes"]?.intValue && NG2CycleWire.hash(png) == row["sha256"]?.stringValue,
                       "retention101_pair_png_bytes_match_manifest")
        }
        unregister(run)
        for viaDispatch in [true,false] {
            let (late, values, before) = prepare(); pressure(late, values, before)
            late.images = [values[43]!,values[501]!,values[502]!,values[503]!]
            let prior = late.controllerSnapshot!
            var stop = prior.stopDetail; stop.last_comparison_capture_id = 43
            let incoming = snapshot(prior.status,prior.events,prior.changes,stop: stop)
            late.controllerSnapshot = incoming
            late.lock.ng2Locked {
                if viaDispatch {
                    pinDispatchSourceLocked(late,43)
                    require101(Set(late.pinned.keys) == oldPriority.union([43]),
                               "retention101_dispatch_admits_old_source_before_priority_refresh")
                    // The later coherent snapshot now gives that source its
                    // diagnostic priority, without another eviction.
                    retainEvidenceLocked(late,incoming)
                } else { retainEvidenceLocked(late,incoming) }
            }
            require101(late.pinned.count == 24 && selected(late) == oldPriority.union([43]),
                       "retention101_late_old_priority_evicts_only_optional_in_both_pin_paths")
            register(late)
            require101(missing(late).contains(436) && !missing(late).contains(437),
                       "retention101_evicted_optional_reference_remains_truthfully_missing")
            unregister(late)
        }
        let (full, all, fullPrevious) = prepare(full: true)
        pressure(full, all, fullPrevious, full: true)
        full.images = [all[500]!,all[501]!,all[502]!,all[503]!]
        full.lock.ng2Locked { retainEvidenceLocked(full,full.controllerSnapshot!) }
        register(full)
        require101(full.pinned.count == 24 && !selected(full).contains(436) && missing(full).contains(436),
                   "retention101_full_legacy_budget_does_not_promise_optional_source")
        unregister(full)
        for fault in ["source_generation","observed_generation","source_prefix","observed_prefix","phase_sample","begun"] {
            let (bad, values, before) = prepare(fault: fault); pressure(bad,values,before)
            require101(!selected(bad).contains(436) && bad.initialRejectedCaptureID == nil,
                       "retention101_mismatched_pair_is_not_promoted_"+fault)
        }
        let (legacy, legacyFrames, legacyPrevious) = prepare(Self.evidenceProfile)
        pressure(legacy,legacyFrames,legacyPrevious)
        require101(legacy.pinned.count <= 20 && selected(legacy).contains(437) && !selected(legacy).contains(436),
                   "retention101_profile2_keeps_observed_only_and_twenty_limit")
        print("PASS TEST101 finite coherent rejection-pair retention/export; procedural diagnostic component, existing24/44 budgets")
    }
}
#endif
