// TEST116 actual Runtime/C/Spool callbacks. Pixels, UI and clocks are procedural.
// The normal-chain case keeps the real Ring output; fault cases explicitly use
// the old synthetic result adapter to isolate lifecycle and return fences.
var runtime116PublicationEvidence = [String: JSONValue]()
func runtime116Start(_ id: String) -> ([String: JSONValue]?, JSONRPCError?) {
    runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-irregular-v1"), "continuous_campaign": .bool(true),
        "_necro_owner": .string("fixture-owner")])
}
func runtime116Status(_ id: String, keepalive: Bool = true) -> ([String: JSONValue]?, JSONRPCError?) {
    cycleCall(id, "campaign_status", extra: ["keepalive": .bool(keepalive)])
}
func runtime116Payload(_ id: String, keepalive: Bool = true) -> [String: JSONValue] {
    runtime116Status(id, keepalive: keepalive).0?["payload"]?.objectValue ?? [:]
}
func runtime116Children(_ id: String) -> [[String: JSONValue]] {
    (runtime116Payload(id, keepalive: false)["children"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
func runtime116Drained(_ id: String) -> Bool {
    let value = runtime116Payload(id, keepalive: false)
    return value["terminal"]?.boolValue == true && value["workers_drained"]?.boolValue == true
}
func runtime116Reset(_ root: URL) {
    runtime112Reset(root)
    runtime116PublicationEvidence = [:]
    NG2RuntimeContinuousTestHooks.rootDurationNS = nil
    NG2RuntimeContinuousTestHooks.failCoreCreation = false
    NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn = nil
    NG2RuntimeContinuousTestHooks.beforePersistenceCommitReturn = nil
    NG2RuntimeContinuousTestHooks.afterSealEnqueueBeforeReturn = nil
    NG2RuntimeContinuousTestHooks.beforeSealCommitReturn = nil
    NG2RuntimeContinuousTestHooks.afterCaptureThreadEnqueueBeforeReturn = nil
    NG2RuntimeContinuousTestHooks.beforeSuccessorCommit = nil
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = nil
    NG2RuntimeContinuousTestHooks.beforeBootstrapAdmission = nil
    NG2CycleSpoolTestHooks.availableBytes = 4 * 1024 * 1024 * 1024
}
func runtime116Heartbeat(_ id: String) {
    let prior = NG2RuntimeTestHooks.beforeControlTick
    NG2RuntimeTestHooks.beforeControlTick = {
        _ = runtime116Status(id)
        prior?()
    }
}
func runtime116Begin(_ id: String) {
    fixtureFailureSnapshot = {
        let value = runtime116Payload(id, keepalive: false)
        let active = value["active_run_id"]?.stringValue ?? id
        return ["campaign": .object(value), "active_report": .object(report(active)),
            "cycle": .object(cyclePayload(active)), "yield": .object(runtime112State(active)),
            "touches": .int(NG2Fake.countTouches()), "paths": .int(NG2Fake.paths().count),
            "activations": .int(NG2Fake.countActivations()), "clock": .int(Int(NG2Fake.virtualClock())),
            "publication": .object(runtime116PublicationEvidence)]
    }
    let answer = runtime116Start(id)
    require(answer.1 == nil && answer.0?["continuous_campaign"]?.boolValue == true &&
        answer.0?["yield_after_restart"] == nil,
        "test116_explicit_continuous_start_without_old_wire_yield")
}
func runtime116LiveExportBlocked(_ id: String) {
    require(cycleCall(id, "manifest").1?.code == -32094 &&
        call("necro_native_results", id).1?.code == -32094,
        "test116_live_root_and_child_heavy_export_cannot_clone_input_lease")
}
func runtime116RawHashes(_ root: URL, _ id: String) -> [String: String] {
    let folder = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    guard let files = try? FileManager.default.contentsOfDirectory(at: folder,
            includingPropertiesForKeys: [.isRegularFileKey]) else { return [:] }
    var result = [String: String]()
    for file in files where file.lastPathComponent.hasSuffix(".rgba") {
        guard let raw = try? Data(contentsOf: file) else {
            require(false, "test116_saved_original_rgba_is_readable"); return [:]
        }
        result[file.lastPathComponent] = NG2CycleWire.hash(raw)
    }
    return result
}
func runtime116Emit(_ kind: String, _ value: [String: JSONValue]) {
    guard let bytes = try? JSONEncoder().encode(value), let line = String(data: bytes, encoding: .utf8) else {
        require(false, "test116_evidence_encodes"); return
    }
    print("EVIDENCE TEST116 " + kind + " " + line)
}
struct Runtime116PreparedExport {
    let manifest: [String: JSONValue], status: [String: JSONValue], bytes: Data
    let destination: URL?
}
func runtime116PrepareSyntheticExport(_ id: String, label: String,
        rootReplyBytes: Data) -> Runtime116PreparedExport? {
    guard let manifest = cycleCall(id, "manifest").0?["payload"]?.objectValue,
          let text = manifest["manifest_json"]?.stringValue, let bytes = text.data(using: .utf8),
          let value = try? JSONDecoder().decode([String: JSONValue].self, from: bytes),
          let exportID = manifest["export_id"]?.stringValue else {
        require(false, "cycle094_exact_manifest_parse"); return nil
    }
    let status = cyclePayload(id)
    require(NG2CycleWire.hash(bytes) == manifest["manifest_sha256"]?.stringValue &&
        value["terminal"]?.boolValue == true && value["workers_drained"]?.boolValue == true &&
        status["terminal"]?.boolValue == true && status["workers_drained"]?.boolValue == true,
        "cycle094_frozen_manifest_identity")
    var records = [String: JSONValue](), seen = Set<Int>()
    for row in value["records"]?.arrayValue ?? [] {
        guard let ref = row.objectValue, let sequence = ref["sequence"]?.intValue,
              let count = ref["bytes"]?.intValue, count > 0, count <= 2*1024*1024,
              let hash = ref["sha256"]?.stringValue, seen.insert(sequence).inserted else {
            require(false, "test116_prepublication_record_inventory_is_exact_and_bounded"); return nil
        }
        var data = Data()
        while data.count < count {
            let offset = data.count
            var page: [String: JSONValue]?
            pump("test116_prepublication_record_page_ready", timeout: 30) {
                let reply = cycleCall(id, "record", extra: ["export_id": .string(exportID),
                    "sequence": .int(sequence), "offset": .int(offset)])
                if let error = reply.1 { require(error.code == -32094, "test116_record_only_pending_is_retried") }
                page = reply.0?["payload"]?.objectValue
                return page != nil
            }
            guard let page, let encoded = page["data_base64"]?.stringValue,
                  let part = Data(base64Encoded: encoded) else {
                require(false, "test116_record_page_contains_actual_bytes"); return nil
            }
            require(page["export_id"]?.stringValue == exportID && page["sequence"]?.intValue == sequence &&
                page["offset"]?.intValue == offset && page["total_bytes"]?.intValue == count &&
                page["sha256"]?.stringValue == hash && part.count == min(NG2CycleWire.chunkBytes,count-offset) &&
                page["next_offset"]?.intValue == offset+part.count &&
                page["eof"]?.boolValue == (offset+part.count == count),
                "test116_every_record_page_has_exact_child_offset_hash_and_eof")
            data.append(part)
        }
        require(data.count == count && NG2CycleWire.hash(data) == hash,
            "test116_prepublication_all_record_bytes_match_frozen_manifest")
        records[String(sequence)] = .string(data.base64EncodedString())
    }
    require(!records.isEmpty, "test116_prepublication_records_include_real_session_and_terminal_chain")
    let environment = ProcessInfo.processInfo.environment
    var destination: URL?
    if let output = environment["NG2_RUNTIME112_EVIDENCE"], !output.isEmpty,
       let selected = environment["NG2_RUNTIME112_CASE"], !selected.isEmpty {
        let folder = URL(fileURLWithPath: output).appendingPathComponent(selected)
            .appendingPathComponent(label).appendingPathComponent(id)
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true,
                attributes: [.posixPermissions: NSNumber(value: 0o700)])
            try bytes.write(to: folder.appendingPathComponent("manifest.json"), options: .atomic)
            try JSONEncoder().encode(manifest).write(to: folder.appendingPathComponent("manifest-rpc.json"), options: .atomic)
            try JSONEncoder().encode(status).write(to: folder.appendingPathComponent("runtime-status.json"), options: .atomic)
            try JSONEncoder().encode(records).write(to: folder.appendingPathComponent("records-rpc.json"), options: .atomic)
            try rootReplyBytes.write(to: folder.appendingPathComponent("root-status-rpc.json"), options: .atomic)
            destination = folder
        } catch { require(false, "test116_prepublication_verified_export_saved_before_ack") }
    }
    return Runtime116PreparedExport(manifest: manifest, status: status, bytes: bytes, destination: destination)
}
func runtime116PublishFixtureClaim(_ id: String, manifest: [String: JSONValue], retired: Bool) -> [String: JSONValue] {
    // The TEST094 frozen-manifest/ACK assertions are retained in this explicit
    // order. The original helpers remain unchanged for their historical scope.
    // Current callbacks retire heavy noncurrent exports as soon as ACK wins.
    guard let exportID = manifest["export_id"]?.stringValue,
          let manifestSHA = manifest["manifest_sha256"]?.stringValue else {
        require(false, "test116_publication_uses_prepared_exact_child_manifest"); return [:]
    }
    let claim = String(repeating: "a", count: 64) // Explicit simulated client receipt, as in TEST094.
    let request: [String: JSONValue] = ["export_id": .string(exportID),
        "manifest_sha256": .string(manifestSHA), "archive_sha256": .string(claim)]
    var attempts = 0, accepted = 0, pendingAfterAccepted = 0
    var firstAccepted: [String: JSONValue]?
    runtime116PublicationEvidence = ["run_id": .string(id), "request": .object(request)]
    pump("cycle094_publication_ack", timeout: 30) {
        let reply = cycleCall(id, "published", extra: request)
        let payload = reply.0?["payload"]?.objectValue
        attempts += 1
        if payload?["accepted"]?.boolValue == true {
            accepted += 1
            if firstAccepted == nil { firstAccepted = payload }
            require(payload == firstAccepted, "test116_repeated_publication_ack_has_identical_receipt")
        } else if firstAccepted != nil { pendingAfterAccepted += 1 }
        runtime116PublicationEvidence["attempts"] = .int(attempts)
        runtime116PublicationEvidence["accepted_replies"] = .int(accepted)
        runtime116PublicationEvidence["pending_after_accepted"] = .int(pendingAfterAccepted)
        runtime116PublicationEvidence["last_payload"] = payload.map { .object($0) } ?? .null
        runtime116PublicationEvidence["last_error_code"] = reply.1.map { .int($0.code) } ?? .null
        runtime116PublicationEvidence["last_error_message"] = reply.1.map { .string($0.message) } ?? .null
        if let error = reply.1 { require(error.code == -32094, "cycle094_receipt_only_pending_is_retried") }
        return payload?["accepted"]?.boolValue == true
    }
    require(accepted >= 2 && pendingAfterAccepted == 0 &&
        firstAccepted?["export_id"] == request["export_id"] &&
        firstAccepted?["manifest_sha256"] == request["manifest_sha256"] &&
        firstAccepted?["archive_sha256"] == request["archive_sha256"] &&
        firstAccepted?["receipt_sha256"]?.stringValue?.count == 64,
        "test116_successful_publication_is_immediately_idempotent_after_cache_retirement")
    let touches = NG2Fake.countTouches(), activations = NG2Fake.countActivations()
    if retired {
        for key in ["export_id", "manifest_sha256", "archive_sha256"] {
            var conflicting = request
            let original = request[key]!.stringValue!
            conflicting[key] = .string((original.first == "a" ? "b" : "a") + String(original.dropFirst()))
            let rejected = cycleCall(id, "published", extra: conflicting)
            require(rejected.0 == nil && rejected.1?.code == -32602,
                "test116_retired_receipt_rejects_each_different_publication_identity")
        }
    }
    for _ in 0..<2 {
        let duplicate = cycleCall(id, "published", extra: request)
        require(duplicate.1 == nil && duplicate.0?["payload"]?.objectValue == firstAccepted,
            "test116_same_child_same_publication_retransmit_preserves_ack_and_receipt")
    }
    require(NG2Fake.countTouches() == touches && NG2Fake.countActivations() == activations,
        "test116_receipt_only_retransmits_cannot_reactivate_or_issue_input")
    runtime116Emit("PUBLICATION_ACK", runtime116PublicationEvidence)
    return firstAccepted ?? [:]
}
func runtime116PreserveSyntheticExport(_ root: URL, _ id: String, label: String,
        prepared: Runtime116PreparedExport, published: [String: JSONValue]) {
    guard let destination = prepared.destination else { return }
    do {
        // All RPC content was verified and saved before ACK retired the heavy
        // object. Now preserve the actual durable publication record and Spool.
        let source = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
        try FileManager.default.copyItem(at: source, to: destination.appendingPathComponent("spool"))
        require(published["accepted"]?.boolValue == true && published["receipt_sha256"]?.stringValue?.count == 64,
            "test112_synthetic_export_actual_idempotent_publication_ack")
        try JSONEncoder().encode(published).write(to: destination.appendingPathComponent("published-rpc.json"), options: .atomic)
        var inventory = [[String: JSONValue]](), total = 0, publicationRecordMatches = 0
        let enumerator = FileManager.default.enumerator(at: destination, includingPropertiesForKeys: [.isRegularFileKey])!
        for case let file as URL in enumerator {
            guard (try file.resourceValues(forKeys: [.isRegularFileKey])).isRegularFile == true else { continue }
            let bytes = try Data(contentsOf: file), name = String(file.path.dropFirst(destination.path.count+1))
            total += bytes.count
            inventory.append(["name": .string(name), "bytes": .int(bytes.count), "sha256": .string(NG2CycleWire.hash(bytes))])
            if name.hasPrefix("spool/record-"),
               let record = try? JSONDecoder().decode([String: JSONValue].self, from: bytes),
               record["kind"]?.stringValue == "published", let payload = record["payload"]?.objectValue {
                require(NG2CycleWire.hash(bytes) == published["receipt_sha256"]?.stringValue &&
                    payload["export_id"] == published["export_id"] &&
                    payload["manifest_sha256"] == published["manifest_sha256"] &&
                    payload["archive_sha256"] == published["archive_sha256"],
                    "test116_actual_durable_publication_record_matches_retransmitted_ack_exactly")
                publicationRecordMatches += 1
            }
        }
        require(total > 0 && total <= 64*1024*1024 && inventory.count <= 256,
            "test112_synthetic_export_bounded_actual_spool_inventory")
        require(publicationRecordMatches == 1, "test116_exactly_one_original_publication_record_survives_cache_retirement")
        let receipt: [String: JSONValue] = ["schema": .string("test112-synthetic-runtime-export-v1"),
            "scope": .string("procedural host pixels and clock; actual C Runtime Spool RPC; no phone acceptance"),
            "case": .string(ProcessInfo.processInfo.environment["NG2_RUNTIME112_CASE"] ?? ""),
            "label": .string(label), "run_id": .string(id), "client_archive_receipt_is_simulated": .bool(true),
            "client_archive_sha256": .string(String(repeating: "a", count: 64)),
            "manifest_sha256": .string(NG2CycleWire.hash(prepared.bytes)),
            "publication_receipt_sha256": published["receipt_sha256"] ?? .null,
            "export_id": prepared.manifest["export_id"] ?? .null,
            "published_record_present": .bool(ir110Record(root, id, "published") != nil),
            "files": .array(inventory.sorted { ($0["name"]?.stringValue ?? "") < ($1["name"]?.stringValue ?? "") }.map { .object($0) })]
        require(receipt["published_record_present"]?.boolValue == true,
            "test112_synthetic_export_actual_publication_record_present")
        try JSONEncoder().encode(receipt).write(to: destination.appendingPathComponent("receipt.json"), options: .atomic)
    } catch { require(false, "test112_synthetic_export_copy_or_hash_failed") }
}
func runtime116ExportAll(_ root: URL, _ id: String, label: String, normal: Bool = true) {
    require(runtime116Drained(id) && !runtime.hasLease, "test116_full_campaign_actually_drained_before_export")
    let rootStatus = runtime116Status(id, keepalive: false)
    guard rootStatus.1 == nil, let rootReply = rootStatus.0,
          let rootReplyBytes = try? JSONEncoder().encode(rootReply) else {
        require(false, "test116_stopped_root_actual_rpc_is_available_for_client_crossbind"); return
    }
    let children = runtime116Children(id)
    require(!children.isEmpty && children.count <= 16, "test116_all_child_ids_retained_for_export")
    for (index, child) in children.enumerated() {
        guard let childID = child["run_id"]?.stringValue else {
            require(false, "test116_export_child_uuid_present"); return
        }
        require(child["index"]?.intValue == index &&
            child["predecessor_id"] == (index == 0 ? .null : children[index-1]["run_id"]),
            "test116_root_child_predecessor_order_is_not_reconstructed_from_latest_only")
        let saved = runtime116RawHashes(root, childID)
        runtime111Manifest(childID, required: [])
        for (name, hash) in saved {
            let folder = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(childID)
            let suffix = String(name.dropFirst("frame-".count).dropLast(".rgba".count))
            let png = folder.appendingPathComponent("png-"+suffix+".png")
            let raw = try? Data(contentsOf: folder.appendingPathComponent(name))
            let encoded = try? Data(contentsOf: png)
            require(raw.map(NG2CycleWire.hash) == hash &&
                encoded.flatMap(NG2Raster.decode).map(NG2CycleWire.hash) == hash,
                "test116_each_child_original_rgba_and_normal_png_have_exact_same_hash")
        }
        if normal { require(child["escrow_sealed"]?.boolValue == true,
            "test116_normal_child_has_durable_escrow_not_only_ram") }
        let childLabel = label+"_child"+String(index)
        guard let prepared = runtime116PrepareSyntheticExport(childID, label: childLabel, rootReplyBytes: rootReplyBytes) else { return }
        let publication = runtime116PublishFixtureClaim(childID, manifest: prepared.manifest,
            retired: index+1 < children.count)
        runtime116PreserveSyntheticExport(root, childID, label: childLabel, prepared: prepared, published: publication)
    }
}

final class Runtime116State {
    let gate = NSLock()
    var child = "", admitted = 0, rootRaw = [String: String](), uiAfterRestart = 0
    var worlds = [Runtime112UpperWorld]()
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
}
final class Runtime116Park {
    let gate = NSLock(), release = DispatchSemaphore(value: 0)
    var entered = false
    func isEntered() -> Bool { gate.lock(); defer { gate.unlock() }; return entered }
    func wait(_ name: String) {
        gate.lock(); let first = !entered; if first { entered = true }; gate.unlock()
        if first { require(release.wait(timeout: .now()+40) == .success, "test116_bounded_actual_return_park_"+name) }
    }
}
func runtime116AssertHeld(_ id: String, _ label: String) {
    let payload = runtime116Payload(id)
    require(runtime.hasLease && payload["workers_drained"]?.boolValue == false &&
        runtime116Children(id).count == 1,
        "test116_"+label+"_real_return_pending_keeps_root_lease_and_no_successor")
    runtime116LiveExportBlocked(id)
}
func runtime116InstallFaultWorld(_ id: String) -> Runtime112World {
    let world = Runtime112World(id); world.install(); runtime116Heartbeat(id)
    return world
}
func runtime116CancelAfterAdmission(_ id: String, _ state: Runtime116State) {
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, oldID, childID, index in
        require(rootID == id && oldID == id && index == 1, "test116_only_next_fresh_uuid_admitted")
        state.locked { state.child = childID; state.admitted += 1 }
        _ = call("necro_native_cancel", rootID)
    }
}

func testRuntime116NewMode(_ root: URL) {
    runtime116Reset(root); let id = identity()
    runtime116Begin(id)
    require(runtime116Payload(id)["root_id"]?.stringValue == id,
        "test116_root_status_binds_same_native_campaign_identity")
    runtime116LiveExportBlocked(id)
    _ = call("necro_native_cancel", id); NG2Fake.release()
    pump("test116_new_mode_cancel_returns_all_real_callbacks", timeout: 40) { runtime116Drained(id) }
    require(runtime116Children(id).count == 1 && NG2Fake.paths().isEmpty,
        "test116_admission_alone_cannot_move_or_create_a_successor")
}

func testRuntime116NormalChain(_ root: URL, checkHistory: Bool = false) {
    runtime116Reset(root)
    let id = identity(), state = Runtime116State()
    let first = Runtime112UpperWorld(id, mirrored: false, cancelPartial: false)
    state.worlds.append(first); first.install(); runtime116Heartbeat(id)
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, oldID, childID, index in
        require(rootID == id && oldID == id && index == 1 && childID != id,
            "test116_fresh_child_uuid_is_linked_only_after_old_seal")
        let originals = runtime116RawHashes(root, oldID)
        require(!originals.isEmpty && ir110Record(root, oldID, "continuation_seal") != nil,
            "test116_old_actual_raw_and_durable_continuation_seal_exist_before_child")
        let second = Runtime112UpperWorld(childID, mirrored: false, cancelPartial: false)
        state.locked { state.child = childID; state.admitted += 1; state.rootRaw = originals; state.worlds.append(second) }
        second.install(); runtime116Heartbeat(id)
        runtime116LiveExportBlocked(oldID); runtime116LiveExportBlocked(childID)
        require(cyclePayload(oldID)["notification"]?.objectValue?["state"]?.stringValue == "not_requested",
            "test116_normal_intermediate_child_does_not_notify_a_stop")
    }
    runtime116Begin(id)
    pump("test116_normal_ring_negative_real_restart_and_new_child_actual_move", timeout: 50) {
        _ = runtime116Status(id)
        let child = state.locked { state.child }
        return !child.isEmpty && (report(child)["moves"]?.intValue ?? 0) >= 1
            || runtime116Drained(id)
    }
    let child = state.locked { state.child }, current = report(state.locked { state.child })
    require(!child.isEmpty && child != id && state.locked({ state.admitted == 1 }) &&
        (current["beat_period_ns"]?.intValue ?? 0) > 0 && (current["moves"]?.intValue ?? 0) >= 1,
        "test116_successor_requires_own_actual_floor_fit_and_real_unit_not_old_phase_or_input")
    let terminal = ir110Record(root, id, "terminal")?["controller"]?.objectValue ?? [:]
    let events = (terminal["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let firstChildCapture = (current["captures"]?.arrayValue ?? []).first?.objectValue ?? [:]
    let childEvents = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let firstChildMove = childEvents.first(where: { $0["kind"]?.intValue == 4 }) ?? [:]
    let childStart = current["accepted_started_ns"]?.intValue ?? 0
    require(childStart > (terminal["started_ns"]?.intValue ?? Int.max) &&
        current["restarts"]?.intValue == 0 && firstChildCapture["completed_prefix_start"]?.intValue == 0 &&
        (firstChildMove["phase_sample_ns"]?.intValue ?? 0) >= childStart,
        "test116_child_budget_prefix_and_phase_sample_begin_fresh_after_old_epoch")
    require(events.last?["kind"]?.intValue == 3 && events.last?["outcome"]?.intValue == 2 &&
        ir110Record(root, id, "checkpoint") != nil && ir110Record(root, id, "restart_intent") != nil &&
        ir110Record(root, id, "restart_outcome") != nil && first.locked({ first.kernelCalls > 0 && first.restarts == 1 }),
        "test116_real_normal_ring_negative_durable_intent_ack_new_floor_without_recovery_pause")
    let taps = NG2Fake.taps()
    require(taps.filter({ $0 == CGPoint(x: 297, y: 448) }).count == 1 &&
        taps.filter({ $0 == CGPoint(x: 390, y: 448) }).count == 1 &&
        taps.filter({ $0 == CGPoint(x: 144, y: 448) }).count == 1 && NG2Fake.countActivations() == 1,
        "test116_next_floor_has_no_added_pause_resume_or_game_reactivation")
    require(runtime116RawHashes(root, id) == state.locked({ state.rootRaw }),
        "test116_old_raw_bytes_survive_real_successor_movement_unchanged")
    let children = runtime116Children(id)
    require(children.count == 2 && children[0]["escrow_sealed"]?.boolValue == true &&
        children[0]["escrow_sha256"]?.stringValue?.count == 64,
        "test116_child_transition_is_disk_escrow_not_host_publication")
    runtime116Emit("CHAIN", ["root_id": .string(id), "child_id": .string(child),
        "classification_override": .bool(false), "normal_kernel_calls": .int(first.locked { first.kernelCalls }),
        "restarts": .int(first.locked { first.restarts }), "child_moves": current["moves"] ?? .null,
        "child_fit_period_ns": current["beat_period_ns"] ?? .null,
        "activation_count": .int(NG2Fake.countActivations()), "pause_count": .int(1),
        "resume_count": .int(1), "raw_count": .int(state.locked { state.rootRaw.count })])
    _ = call("necro_native_cancel", id); NG2Fake.release()
    pump("test116_both_children_terminal_and_actual_drain", timeout: 50) { runtime116Drained(id) }
    runtime116ExportAll(root, id, label: checkHistory ? "history" : "normal_chain")
    if checkHistory {
        let touches = NG2Fake.countTouches(), activations = NG2Fake.countActivations()
        let legacy = identity()
        require(call("necro_native_start", legacy).1 == nil,
            "test116_new_current_identity_archives_prior_continuous_child_metadata")
        let oldAsNew = runtime116Start(child)
        let oldAsLegacy = runtime.handle(method: "necro_native_start", params: ["run_id": .string(child),
            "profile": .string("normal-1-1-irregular-v1"), "_necro_owner": .string("fixture-owner")])
        let legitimateRoot = runtime116Start(id)
        require(oldAsNew.1?.code == -32602 && oldAsLegacy.1?.code == -32602 &&
            legitimateRoot.1 == nil && legitimateRoot.0?["run_id"]?.stringValue == id &&
            legitimateRoot.0?["continuous_campaign"]?.boolValue == true,
            "test116_archived_child_mode_is_immutable_while_exact_root_start_is_idempotent")
        _ = call("necro_native_cancel", legacy)
        pump("test116_metadata_only_history_probe_legacy_drained", timeout: 20) { drained(legacy) }
        let archivedRoot = runtime116Payload(id, keepalive: false)
        require(NG2Fake.countTouches() == touches && NG2Fake.countActivations() == activations &&
            runtime116Children(id).count == 2 && archivedRoot["active_run_id"]?.stringValue == child &&
            archivedRoot["terminal"]?.boolValue == true && archivedRoot["workers_drained"]?.boolValue == true,
            "test116_rejected_history_mode_never_changes_ui_children_or_final_active_identity")
    }
}

func testRuntime116Candidate(_ root: URL, late: Bool) {
    runtime116Reset(root); let id = identity(), world = runtime116InstallFaultWorld(id)
    let previous = NG2RuntimeCycleTestHooks.classificationResult
    NG2RuntimeCycleTestHooks.classificationResult = { mode, scene, result in
        previous?(mode, scene, &result)
        ng2_fixture_cycle_result(scene, result.started_ns, NG2Runtime.now(), 1, &result)
        if late { NG2Fake.advance(101_000_001); result.status = UInt32(NG2_RING_DEADLINE) }
    }
    runtime116Begin(id)
    pump("test116_known_candidate_or_late_positive_stops_campaign", timeout: 40) { runtime116Drained(id) }
    require(world.locked({ world.restarts == 0 }) && runtime116Children(id).count == 1 &&
        NG2Fake.countActivations() == 1 && ["candidate", "target"].contains(runtime116Payload(id)["stop_reason"]?.stringValue ?? ""),
        "test116_positive_hint_even_after_worker_deadline_cannot_start_another_uuid_or_restart")
    runtime116ExportAll(root, id, label: late ? "late_hint" : "candidate")
}

func testRuntime116ReturnPark(_ root: URL, kind: String) {
    runtime116Reset(root); let id = identity(), world = runtime116InstallFaultWorld(id)
    let park = Runtime116Park(), state = Runtime116State()
    runtime116CancelAfterAdmission(id, state)
    switch kind {
    case "producer": NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn = { _ in park.wait(kind) }
    case "classification_commit": NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn = { _ in park.wait(kind) }
    case "capture_decode": NG2RuntimeTestHooks.beforeCaptureDecode = { _ in
        if world.locked({ world.stage > 0 }) { park.wait(kind) }
    }
    case "capture_control": NG2RuntimeTestHooks.beforeCaptureControlConsume = { _ in
        if world.locked({ world.stage > 0 }) { park.wait(kind) }
    }
    case "capture_thread_return": NG2RuntimeContinuousTestHooks.afterCaptureThreadEnqueueBeforeReturn = { run in
        if run == id { park.wait(kind) }
    }
    case "seal_producer": NG2RuntimeContinuousTestHooks.afterSealEnqueueBeforeReturn = { _ in park.wait(kind) }
    case "seal_commit": NG2RuntimeContinuousTestHooks.beforeSealCommitReturn = { _ in park.wait(kind) }
    default:
        let pieces = kind.split(separator: ":").map(String.init)
        require(pieces.count == 2, "test116_known_persistence_park_kind")
        if pieces[0] == "writer" {
            NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn = { run, phase in
                if run == id && phase == pieces[1] { park.wait(kind) }
            }
        } else {
            require(pieces[0] == "commit", "test116_known_persistence_commit_park_kind")
            NG2RuntimeContinuousTestHooks.beforePersistenceCommitReturn = { run, phase in
                if run == id && phase == pieces[1] { park.wait(kind) }
            }
        }
    }
    runtime116Begin(id)
    pump("test116_selected_actual_return_park_entered_"+kind, timeout: 40) { park.isEntered() || runtime116Drained(id) }
    require(park.isEntered(), "test116_expected_return_boundary_is_really_executed_"+kind)
    runtime116AssertHeld(id, kind)
    if kind == "capture_thread_return" {
        require(ir110Record(root, id, "terminal") == nil,
            "test116_capture_done_flag_and_enqueued_callback_do_not_replace_thread_return_before_terminal_record")
    }
    let paths = NG2Fake.paths().count, taps = NG2Fake.taps().count
    RunLoop.current.run(until: Date().addingTimeInterval(0.03))
    runtime116AssertHeld(id, kind)
    // A durably committed result may finish the OLD child's known PAUSE/RS.
    // Actual-return fences prohibit a successor and lease release, rather
    // than invalidating already committed old-child input authority.
    if kind.hasPrefix("seal_") || kind.hasPrefix("capture_") || kind.hasSuffix(":outcome") || kind.hasSuffix(":terminal") {
        require(NG2Fake.paths().count == paths && NG2Fake.taps().count == taps,
            "test116_post_restart_or_terminal_return_cannot_issue_later_input_"+kind)
    }
    park.release.signal()
    pump("test116_released_return_all_callbacks_settle_"+kind, timeout: 50) { runtime116Drained(id) }
    require(state.locked({ state.admitted == 1 }), "test116_only_one_successor_after_real_return_"+kind)
    runtime116ExportAll(root, id, label: kind.replacingOccurrences(of: ":", with: "_"))
}

func testRuntime116SwapCancellation(_ root: URL, after: Bool) {
    runtime116Reset(root); let id = identity(), _ = runtime116InstallFaultWorld(id), state = Runtime116State()
    var swaps = 0, countAtGate = 0
    let noticeGate = NSLock(); var notices = [String: Int]()
    NG2RuntimeCycleTestHooks.afterNotification = { child in
        noticeGate.lock(); notices[child, default: 0] += 1; noticeGate.unlock()
    }
    if after {
        NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, _, childID, index in
            require(rootID == id && index == 1, "test116_active_child_cancel_targets_only_new_uuid")
            state.locked { state.child = childID; state.admitted += 1 }
            countAtGate = NG2Fake.countTouches()
            _ = call("necro_native_cancel", childID)
        }
    } else {
        NG2RuntimeContinuousTestHooks.beforeSuccessorCommit = { rootID, oldID, childID in
            require(rootID == id && oldID == id && childID != id, "test116_cancel_gate_has_prepared_fresh_uuid")
            swaps += 1; countAtGate = NG2Fake.countTouches()
            _ = call("necro_native_cancel", rootID)
        }
        NG2RuntimeContinuousTestHooks.afterChildAdmitted = { _, _, _, _ in state.locked { state.admitted += 1 } }
    }
    runtime116Begin(id)
    pump("test116_swap_cancel_real_queues_drain", timeout: 50) { runtime116Drained(id) }
    require(NG2Fake.countTouches() == countAtGate && NG2Fake.countActivations() == 1 &&
        state.locked({ state.admitted == (after ? 1 : 0) }) && (after || swaps == 1),
        "test116_cancel_linearizes_before_or_after_exchange_without_new_child_ui")
    if !after {
        let children = runtime116Children(id)
        require(children.count == 2 && children[0]["escrow_sealed"]?.boolValue == true &&
            children[1]["state"]?.stringValue == "stopped" && children[1]["escrow_sealed"]?.boolValue == false,
            "test116_prepared_orphan_stays_indexed_as_diagnostic_not_gameplay_or_complete")
        let orphan = children[1]["run_id"]!.stringValue!
        pump("test116_prepared_diagnostic_notifies_once_after_real_drain", timeout: 10) {
            cyclePayload(orphan)["notification"]?.objectValue?["state"]?.stringValue == "requested"
        }
        noticeGate.lock(); let count = notices[orphan] ?? 0; noticeGate.unlock()
        require(count == 1, "test116_prepared_diagnostic_final_notice_is_not_suppressed_or_duplicated")
        var manifest: [String: JSONValue]?
        pump("test116_prepared_orphan_readonly_diagnostic_export", timeout: 30) {
            if let text = cycleCall(orphan, "manifest").0?["payload"]?.objectValue?["manifest_json"]?.stringValue,
               let bytes = text.data(using: .utf8) { manifest = try? JSONDecoder().decode([String: JSONValue].self, from: bytes) }
            return manifest != nil
        }
        require(manifest?["complete"]?.boolValue == false && manifest?["input_state"]?.intValue == 4,
            "test116_orphan_has_no_manufactured_terminal_or_known_input_proof")
    }
}

func testRuntime116Bootstrap(_ root: URL, deadline: Bool) {
    runtime116Reset(root); let id = identity(), park = Runtime116Park()
    if deadline { NG2RuntimeContinuousTestHooks.rootDurationNS = 1_000_000 }
    NG2RuntimeContinuousTestHooks.beforeBootstrapAdmission = { runID, index in
        require(runID == id && index == 0, "test116_only_initial_bootstrap_selected")
        DispatchQueue.global().async {
            require(runtime.hasLease && NG2Fake.countActivations() == 0 && NG2Fake.countTouches() == 0,
                "test116_root_bootstrap_before_admission_has_no_ui_and_keeps_lease")
            if deadline {
                let bound = UInt64(runtime116Payload(id, keepalive: false)["deadline_ns"]!.intValue!)
                let now = NG2Fake.virtualClock(); if now < bound { NG2Fake.advance(bound-now) }
            } else { _ = call("necro_native_cancel", id) }
            park.release.signal()
        }
        park.wait(deadline ? "bootstrap_deadline" : "bootstrap_cancel")
    }
    runtime116Begin(id)
    pump("test116_bootstrap_cancel_or_deadline_actually_drained", timeout: 40) { runtime116Drained(id) }
    require(park.isEntered() && NG2Fake.countActivations() == 0 && NG2Fake.countTouches() == 0 &&
        runtime116Children(id).count == 1,
        "test116_root_cancel_or_deadline_while_main_parked_prevents_game_activation_and_all_ui")
}

func testRuntime116QualifiedCancel(_ root: URL) {
    runtime116Reset(root); let id = identity(), _ = runtime116InstallFaultWorld(id)
    let park = Runtime116Park(), state = Runtime116State()
    NG2RuntimeContinuousTestHooks.afterSealEnqueueBeforeReturn = { run in if run == id { park.wait("qualified_cancel") } }
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { _, _, _, _ in state.locked { state.admitted += 1 } }
    runtime116Begin(id)
    pump("test116_qualified_old_child_seal_producer_park", timeout: 40) { park.isEntered() || runtime116Drained(id) }
    require(park.isEntered(), "test116_qualified_terminal_is_really_saved_before_cancel")
    let proof = ir110Record(root, id, "terminal")?["controller"]?.objectValue?["continuous_campaign"]?.objectValue ?? [:]
    require(proof["qualified"]?.boolValue == true, "test116_last_qualified_proof_is_unused_when_root_cancel_wins")
    runtime116AssertHeld(id, "qualified_cancel")
    let touches = NG2Fake.countTouches()
    _ = call("necro_native_cancel", id); park.release.signal()
    pump("test116_qualified_cancel_real_seal_and_callback_returns", timeout: 40) { runtime116Drained(id) }
    require(state.locked({ state.admitted == 0 }) && runtime116Children(id).count == 1 &&
        NG2Fake.countTouches() == touches && runtime116Payload(id)["stop_reason"]?.stringValue == "cancelled",
        "test116_unused_qualified_old_child_stops_without_new_uuid_or_ui")
    runtime116ExportAll(root, id, label: "qualified_cancel")
}

func testRuntime116SuccessorExternal(_ root: URL, variant: String) {
    runtime116Reset(root); let id = identity(), _ = runtime116InstallFaultWorld(id), state = Runtime116State()
    var touches = 0, paths = 0
    var lossApplied = false
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { _, _, child, _ in state.locked { state.child = child; state.admitted += 1 } }
    NG2RuntimeContinuousTestHooks.beforeBootstrapAdmission = { _, index in
        guard index == 1 else { return }
        touches = NG2Fake.countTouches(); paths = NG2Fake.paths().count
        if variant == "locked" { LockStateMonitor.monitor.isLocked = true }
        else {
            NG2Fake.lock.lock()
            if variant == "owner" { NG2Fake.authenticatedOwnerActive = false }
            else { NG2Fake.frontPID = 99 }
            NG2Fake.lock.unlock()
        }
        state.locked { lossApplied = true }
    }
    runtime116Begin(id)
    if variant == "owner" {
        pump("test116_owner_loss_drains_known_child_while_campaign_status_stays_unauthorized", timeout: 45) {
            let observed = state.locked { (lossApplied, state.child) }
            guard observed.0 && !observed.1.isEmpty else { return false }
            let denied = runtime116Status(id, keepalive: false)
            require(denied.0 == nil && denied.1?.code == -32602,
                "test116_inactive_owner_cannot_query_authenticated_campaign_status")
            return !runtime.hasLease && drained(observed.1)
        }
        require(NG2Fake.countTouches() == touches && NG2Fake.paths().count == paths &&
            NG2Fake.countActivations() == 1,
            "test116_owner_remains_inactive_until_all_real_callbacks_drain_without_ui")
        NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.lock.unlock()
    }
    pump("test116_successor_external_guard_drains_"+variant, timeout: 45) { runtime116Drained(id) }
    require(state.locked({ state.admitted == 1 && !state.child.isEmpty }) && NG2Fake.countTouches() == touches &&
        NG2Fake.countActivations() == 1 && NG2Fake.paths().count == paths,
        "test116_successor_external_loss_never_reactivates_game_or_issues_another_input")
    let reason = runtime116Payload(id, keepalive: false)["stop_reason"]?.stringValue
    require(reason == (variant == "locked" ? "locked" : "owner"), "test116_external_loss_has_its_own_stop_reason")
    let final = runtime116Payload(id, keepalive: false)
    require(final["input_state"]?.intValue == 0 && final["native_inflight"]?.boolValue == false &&
        final["ui_frozen"]?.boolValue == false && final["workers_drained"]?.boolValue == true,
        "test116_external_loss_is_known_input_and_fully_drained_after_observation_authority_returns")
    // Restore external test state solely after actual gameplay drain.
    NG2Fake.lock.lock(); NG2Fake.authenticatedOwnerActive = true; NG2Fake.frontPID = 42; NG2Fake.lock.unlock()
    LockStateMonitor.monitor.isLocked = false
    runtime116ExportAll(root, id, label: "external_"+variant)
}

func testRuntime116MainReturn(_ root: URL) {
    runtime116Reset(root); let id = identity(), _ = runtime116InstallFaultWorld(id), park = Runtime116Park()
    let previous = NG2RuntimeTestHooks.scheduleTicket
    var selected = false
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let handled = previous?(command, callback) ?? false
        if handled && !selected {
            selected = true
            let before = NG2RuntimeTestHooks.beforeMainAuthority
            NG2RuntimeTestHooks.beforeMainAuthority = {
                before?()
                DispatchQueue.global().async {
                    runtime116AssertHeld(id, "main")
                    require(NG2Fake.paths().isEmpty, "test116_main_callback_before_begin_has_no_physical_direction")
                    _ = call("necro_native_cancel", id)
                    park.release.signal()
                }
                park.wait("main")
            }
        }
        return handled
    }
    runtime116Begin(id)
    pump("test116_main_return_cancel_fully_drained", timeout: 40) { runtime116Drained(id) }
    require(park.isEntered() && NG2Fake.paths().isEmpty && runtime116Children(id).count == 1,
        "test116_main_return_then_sticky_cancel_cannot_issue_move_or_successor")
}

func testRuntime116RootClock(_ root: URL, variant: String) {
    runtime116Reset(root)
    NG2RuntimeContinuousTestHooks.rootDurationNS = 6_000_000_000
    NG2RuntimeCycleTestHooks.rgba = nil
    NG2Fake.lock.lock(); NG2Fake.walkGoodsEnabled = false; NG2Fake.lock.unlock()
    NG2Fake.cycleTap = { x, y in
        if x == 297 && y == 448 { NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock() }
    }
    let id = identity(), actualVariant = variant == "ticket_before" ? "within" : variant
    let state = Runtime115BeginClock(id, actualVariant)
    alignInitialFixtureMove(id)
    ng2_fixture_begin115_install(runtime115BeginClockReturned, Unmanaged.passUnretained(state).toOpaque())
    defer { ng2_fixture_begin115_install(nil, nil) }
    var rootBound: UInt64 = 0, ticketBound: UInt64 = 0, beforeInputs = 0
    NG2Fake.lock.lock()
    NG2Fake.beforeForegroundQuery = {
        let command = UInt64(report(id)["current_command_id"]?.intValue ?? 0)
        state.locked { state.queries[command] = NG2Fake.virtualClock() }
    }
    NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.scheduleTicket = { command, callback in
        let snapshot = report(id), events = (snapshot["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard let event = events.first(where: { $0["id"]?.intValue == Int(command) }), event["kind"]?.intValue == 4 else { return false }
        rootBound = UInt64(runtime116Payload(id)["deadline_ns"]!.intValue!)
        ticketBound = UInt64(event["deadline_ns"]!.intValue!)
        beforeInputs = snapshot["inputs"]?.intValue ?? -1
        require(state.locked({ state.command == 0 }) && ticketBound <= rootBound &&
            UInt64(event["not_before_ns"]!.intValue!) <= ticketBound,
            "test116_frozen_command_respects_same_absolute_root_deadline")
        state.locked {
            state.command = command; state.notBefore = UInt64(event["not_before_ns"]!.intValue!)
            state.deadline = variant == "ticket_before" ? ticketBound : rootBound
            state.queryStart = state.queries[command] ?? 0
        }
        NG2Fake.holdTicket(command, callback)
        NG2Fake.lock.lock(); NG2Fake.captureLimit = NG2Fake.requests; NG2Fake.lock.unlock()
        return true
    }
    NG2RuntimeTestHooks.afterTicketReturned = { command in
        if state.locked({ state.command == command }) {
            state.locked { state.returned = true }
            if variant == "ticket_before" { _ = call("necro_native_cancel", id) }
            NG2Fake.lock.lock(); NG2Fake.captureLimit = nil; NG2Fake.lock.unlock()
        }
    }
    runtime116Begin(id)
    pump("test116_root_clock_has_real_fresh_move_reservation", timeout: 30) {
        state.locked({ state.command != 0 }) || runtime116Drained(id)
    }
    let command = state.locked { state.command }
    require(command != 0, "test116_root_clock_reaches_actual_begin_boundary")
    NG2RuntimeTestHooks.beforeMainAuthority = {
        _ = runtime116Status(id)
        admitFirstFixtureMove(id, expectedID: command)
    }
    NG2Fake.releaseTicket(command)
    pump("test116_post_begin_root_clock_actual_return_and_terminal", timeout: 40) { runtime116Drained(id) }
    let final = report(id), events = (final["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let event = events.first(where: { $0["id"]?.intValue == Int(command) }) ?? [:]
    let sent = variant == "ticket_before"
    require(state.locked({ state.calls == 1 && state.before >= state.notBefore }) &&
        state.locked({ state.before <= ticketBound && state.after >= state.before }) &&
        NG2Fake.paths().count == (sent ? 1 : 0) && final["inputs"]?.intValue == beforeInputs+(sent ? 1 : 0) &&
        event["outcome"]?.intValue == (sent ? 2 : 3) && final["input_state"]?.intValue != 4,
        "test116_actual_clock_after_successful_c_begin_keeps_frozen_minimum_bound_and_known_send_state")
    runtime116Emit("ROOT_CLOCK", ["variant": .string(variant), "root_id": .string(id),
        "root_deadline_ns": .int(Int(rootBound)), "ticket_deadline_ns": .int(Int(ticketBound)),
        "before_ns": .int(Int(state.locked { state.before })), "after_ns": .int(Int(state.locked { state.after })),
        "begin_calls": .int(state.locked { state.calls }), "gesture_count": .int(NG2Fake.paths().count),
        "input_state": final["input_state"] ?? .null, "root_is_not_claimed_the_only_earlier_bound": .bool(true)])
}

func testRuntime116Heartbeat(_ root: URL) {
    runtime116Reset(root); let id = identity(), park = Runtime116Park()
    NG2RuntimeContinuousTestHooks.beforeBootstrapAdmission = { runID, index in
        require(runID == id && index == 0, "test116_heartbeat_checks_first_unactivated_child")
        DispatchQueue.global().async {
            guard let before = runtime.testContinuousHeartbeats(id), before.count == 3 else {
                require(false, "test116_heartbeat_readonly_root_and_active_child_snapshot"); return
            }
            NG2Fake.advance(1_000_000)
            _ = call("necro_native_status", id, keepalive: true)
            _ = cycleCall(id, extra: ["keepalive": .bool(true)])
            require(runtime.testContinuousHeartbeats(id) == before,
                "test116_direct_native_or_irregular_child_status_never_renews_root_or_child")
            let refreshedAt = NG2Fake.virtualClock()
            _ = runtime116Status(id)
            let refreshed = runtime.testContinuousHeartbeats(id) ?? []
            require(refreshed == [refreshedAt, refreshedAt, before[2]] && refreshedAt > before[0],
                "test116_only_root_keepalive_renews_exact_active_child_without_extending_absolute_deadline")
            NG2Fake.advance(5_000_000_001)
            _ = call("necro_native_status", id, keepalive: true)
            _ = cycleCall(id, extra: ["keepalive": .bool(true)])
            require(runtime.testContinuousHeartbeats(id) == refreshed,
                "test116_expired_root_cannot_be_kept_alive_by_direct_child_calls")
            let until = Date().addingTimeInterval(3)
            while report(id)["cancel_requested"]?.boolValue != true && Date() < until {
                Thread.sleep(forTimeInterval: 0.01)
            }
            require(report(id)["cancel_requested"]?.boolValue == true && runtime.hasLease &&
                NG2Fake.countActivations() == 0 && NG2Fake.countTouches() == 0,
                "test116_real_watchdog_expires_heartbeat_but_keeps_parked_main_lease_and_ui_zero")
            park.release.signal()
        }
        park.wait("heartbeat")
    }
    runtime116Begin(id)
    pump("test116_root_heartbeat_expiry_releases_only_after_main_return", timeout: 40) { runtime116Drained(id) }
    require(park.isEntered() && NG2Fake.countActivations() == 0 && NG2Fake.countTouches() == 0 &&
        runtime116Children(id).count == 1,
        "test116_expired_root_has_no_hidden_child_authority_or_ui_activation")
}

func testRuntime116NilCore(_ root: URL) {
    runtime116Reset(root); let id = identity(), noticeGate = NSLock()
    var notices = 0
    NG2RuntimeContinuousTestHooks.failCoreCreation = true
    NG2RuntimeCycleTestHooks.afterNotification = { run in
        if run == id { noticeGate.lock(); notices += 1; noticeGate.unlock() }
    }
    runtime116Begin(id)
    pump("test116_failed_core_creation_finitely_releases_root_after_real_initialization_return", timeout: 40) {
        runtime116Drained(id)
    }
    let payload = runtime116Payload(id, keepalive: false), children = runtime116Children(id)
    require(!runtime.hasLease && NG2Fake.countTouches() == 0 && NG2Fake.countActivations() == 0 &&
        payload["input_state"]?.intValue == 4 && payload["ui_frozen"]?.boolValue == true &&
        children.count == 1 && children[0]["escrow_sealed"]?.boolValue == false &&
        ir110Record(root, id, "terminal") == nil,
        "test116_nil_core_has_no_ui_or_fabricated_native_terminal_and_keeps_diagnostic_uncertainty")
    var manifest: [String: JSONValue]?
    pump("test116_failed_core_has_readonly_diagnostic_manifest", timeout: 20) {
        if let text = cycleCall(id, "manifest").0?["payload"]?.objectValue?["manifest_json"]?.stringValue,
           let bytes = text.data(using: .utf8) { manifest = try? JSONDecoder().decode([String: JSONValue].self, from: bytes) }
        return manifest != nil
    }
    require(manifest?["complete"]?.boolValue == false && manifest?["input_state"]?.intValue == 4 &&
        manifest?["interrupted"]?.boolValue == true,
        "test116_nil_core_archive_cannot_claim_complete_native_execution")
    pump("test116_failed_core_final_diagnostic_notifies_after_drain", timeout: 10) {
        cyclePayload(id)["notification"]?.objectValue?["state"]?.stringValue == "requested"
    }
    noticeGate.lock(); let count = notices; noticeGate.unlock()
    require(count == 1, "test116_failed_core_diagnostic_notifies_exactly_once")
}

let root116 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime116-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root116, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root116) }
NG2RuntimeCycleTestHooks.spoolRoot = root116
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case116 = CommandLine.arguments.last ?? ""
pump("test116_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
switch case116 {
case "new_mode": testRuntime116NewMode(root116.appendingPathComponent("mode"))
case "normal_chain": testRuntime116NormalChain(root116.appendingPathComponent("normal"))
case "history_mode": testRuntime116NormalChain(root116.appendingPathComponent("history"), checkHistory: true)
case "nil_core": testRuntime116NilCore(root116.appendingPathComponent("nil_core"))
case "candidate": testRuntime116Candidate(root116.appendingPathComponent("candidate"), late: false)
case "late_hint": testRuntime116Candidate(root116.appendingPathComponent("late"), late: true)
case "cancel_before_swap": testRuntime116SwapCancellation(root116.appendingPathComponent("before"), after: false)
case "cancel_after_swap": testRuntime116SwapCancellation(root116.appendingPathComponent("after"), after: true)
case "bootstrap_cancel": testRuntime116Bootstrap(root116.appendingPathComponent("boot_cancel"), deadline: false)
case "bootstrap_deadline": testRuntime116Bootstrap(root116.appendingPathComponent("boot_deadline"), deadline: true)
case "qualified_cancel": testRuntime116QualifiedCancel(root116.appendingPathComponent("qualified_cancel"))
case "successor_owner", "successor_locked", "successor_foreground":
    testRuntime116SuccessorExternal(root116.appendingPathComponent(case116), variant: String(case116.dropFirst("successor_".count)))
case "main_return": testRuntime116MainReturn(root116.appendingPathComponent("main"))
case "heartbeat": testRuntime116Heartbeat(root116.appendingPathComponent("heartbeat"))
case "post_begin_clock": testRuntime115PostBeginClock(root116.appendingPathComponent("retained_clock115"))
case "root_clock_before", "root_clock_equal", "root_clock_late", "root_clock_ticket_before":
    testRuntime116RootClock(root116.appendingPathComponent(case116), variant: String(case116.dropFirst("root_clock_".count)))
case "producer", "classification_commit", "capture_decode", "capture_control", "capture_thread_return", "seal_producer", "seal_commit",
     "writer:checkpoint", "commit:checkpoint", "writer:intent", "commit:intent", "writer:outcome", "commit:outcome", "writer:terminal", "commit:terminal":
    testRuntime116ReturnPark(root116.appendingPathComponent(case116.replacingOccurrences(of: ":", with: "_")), kind: case116)
default: require(false, "test116_unknown_case_is_not_another_fixture")
}
print("PASS TEST116 CASE " + case116)
