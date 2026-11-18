// Actual Swift/filesystem with procedural evidence, space/fault hooks only.
// No Controller/UI authority or iPhone acceptance is supplied by this fixture.
import Foundation
import CryptoKit

func check116(_ condition: Bool, _ label: String) {
    if !condition { print("FAIL " + label); exit(1) }
}
func rejects116(_ label: String, _ body: () throws -> Void) {
    do { try body(); print("FAIL accepted " + label); exit(1) } catch {}
}
func hash116(_ bytes: Data) -> String {
    SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
}
let root116 = FileManager.default.temporaryDirectory.appendingPathComponent("ngg2-spool116-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root116, withIntermediateDirectories: false,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root116) }
let owner116 = "spool116-host-owner", start116: UInt64 = 1_000_000_000
let deadline116 = start116 + 2_880_000_000_000
var raw116 = Data(count: NG2CycleSpool.rasterBytes)
raw116.withUnsafeMutableBytes { raw in
    let bytes = raw.bindMemory(to: UInt8.self)
    for i in stride(from: 3, to: bytes.count, by: 4) { bytes[i] = 255 }
}
func id116() -> String { UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased() }
func provenance116(_ token: NG2CycleSpool.Reservation, clock: String) -> [String: Any] {
    ["native_profile": "normal-1-1-irregular-v1", "clock_id": clock,
     "continuous_campaign": ["schema": "ngg2-continuous-child-v1", "root_id": token.rootID,
        "index": token.index, "predecessor_id": token.predecessorID as Any? ?? NSNull(),
        "root_started_ns": start116, "root_deadline_ns": deadline116]]
}
func make116() throws -> (NG2CycleSpool.CampaignQuota, NG2CycleSpool, String) {
    NG2CycleSpoolTestHooks.availableBytes = 4 * 1024 * 1024 * 1024
    let id = id116(), clock = id116()
    let quota = try NG2CycleSpool.testCreateCampaignQuota(rootURL: root116, rootID: id, owner: owner116)
    let token = try quota.reserveNext(runID: id, index: 0, predecessorID: nil)
    let store = try NG2CycleSpool.testCreate(rootURL: root116, runID: id, owner: owner116,
        provenance: provenance116(token, clock: clock), quota: quota, reservation: token)
    return (quota, store, clock)
}
func controller116(qualified: Bool = false) -> [String: Any] {
    ["abi_version": 1, "enabled": true, "successor_floor": false, "qualified": qualified,
     "root_deadline_ns": deadline116, "qualified_ns": qualified ? start116+1 : 0,
     "parent_deadline_ns": qualified ? start116+2 : 0, "old_job_id": qualified ? 1 : 0,
     "restart_command_id": qualified ? 2 : 0, "new_floor_capture_id": qualified ? 3 : 0,
     "source_capture_id": qualified ? 4 : 0, "source_start_ns": qualified ? start116+1 : 0,
     "source_prefix": qualified ? 2 : 0]
}
func terminal116(_ store: NG2CycleSpool) throws -> NG2CycleSpool.RecordRef {
    _ = try store.commitFrame(captureID: 1, rgba: raw116, metadata: ["generation": 1])
    return try store.commitRecord(kind: "terminal", cycle: 0,
        payload: ["controller": ["terminal": 1, "input_state": 0, "current_command_id": 0]])
}
func original116(_ store: NG2CycleSpool) throws -> [String: Data] {
    let directory = root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(store.runID)
    return try Dictionary(uniqueKeysWithValues: FileManager.default.contentsOfDirectory(atPath: directory.path).map {
        ($0, try Data(contentsOf: directory.appendingPathComponent($0)))
    })
}
func unchanged116(_ store: NG2CycleSpool, _ before: [String: Data], _ label: String) throws {
    let after = try original116(store)
    check116(before.allSatisfy { after[$0.key] == $0.value }, label)
}
func quota116() throws {
    let (quota, store, _) = try make116()
    NG2CycleSpoolTestHooks.availableBytes = 400 * 1024 * 1024
    _ = try quota.reserveNext(runID: id116(), index: 1, predecessorID: store.runID)
    NG2CycleSpoolTestHooks.availableBytes = 200 * 1024 * 1024
    rejects116("campaign_write_steals_other_slot_reservation") {
        _ = try store.commitFrame(captureID: 1, rgba: raw116, metadata: [:])
    }
    check116(try store.frames().isEmpty, "quota_failure_commits_no_raw_reference")
}
func slot116() throws {
    let (quota, store, _) = try make116()
    var predecessor = store.runID
    for index in 1..<16 {
        let next = id116()
        _ = try quota.reserveNext(runID: next, index: index, predecessorID: predecessor)
        predecessor = next
    }
    rejects116("campaign_unpublished_slot17") {
        _ = try quota.reserveNext(runID: id116(), index: 16, predecessorID: predecessor)
    }
}
func seal116() throws {
    let (_, store, clock) = try make116(), terminal = try terminal116(store)
    _ = try store.sealContinuation(rootID: store.runID, index: 0, predecessorID: nil,
        clockID: clock, terminal: terminal, continuation: controller116(), successor: nil)
    rejects116("control_frame_after_continuation_seal") {
        _ = try store.commitFrame(captureID: 2, rgba: raw116, metadata: [:])
    }
    rejects116("control_record_after_continuation_seal") {
        _ = try store.commitRecord(kind: "checkpoint", cycle: 1, payload: [:])
    }
    check116(store.controlContentSealed, "sealed_content_is_separate_from_export_writer")
}
func export116() throws {
    let (_, store, clock) = try make116(), terminal = try terminal116(store)
    let before = try original116(store)
    let seal = try store.sealContinuation(rootID: store.runID, index: 0, predecessorID: nil,
        clockID: clock, terminal: terminal, continuation: controller116(), successor: nil)
    check116(seal.previous == terminal.sha256 && seal.kind == "continuation_seal", "seal_is_after_exact_terminal_chain_head")
    let payload = seal.payload
    check116(Set(payload.keys) == ["schema", "root_id", "run_id", "index", "predecessor_id", "next_run_id",
        "clock_id", "session_sha256", "terminal_sha256", "frames_sha256", "controller"], "seal_closed_11_key_contract")
    check116(payload["session_sha256"] as? String == hash116(try store.sessionBytes()!), "seal_binds_owner_clock_session_bytes")
    let refs = try store.frames().map { ["capture_id": $0.captureID, "raw_sha256": $0.rawSHA256,
        "metadata_sha256": $0.metadataSHA256, "bytes": $0.bytes] as [String: Any] }
    let encoded = try JSONSerialization.data(withJSONObject: refs, options: [.sortedKeys, .withoutEscapingSlashes])
    check116(payload["frames_sha256"] as? String == hash116(encoded), "seal_binds_all_raw_and_metadata_refs")
    let ref = try store.frames()[0], png = try NG2CycleSpool.storedPNG(rgba: raw116)
    _ = try store.commitPNG(captureID: ref.captureID, bytes: png, metadata: ["raw_sha256": ref.rawSHA256])
    let exportID = id116()
    let manifest = try JSONSerialization.data(withJSONObject: ["export_id": exportID], options: [.sortedKeys])
    let frozen = try store.commitExportManifest(exportID: exportID, bytes: manifest)
    _ = try store.commitPublication(exportID: exportID, manifestSHA256: frozen.sha256,
        archiveSHA256: String(repeating: "a", count: 64))
    try unchanged116(store, before, "all_original_control_bytes_survive_normal_export")
    let recovered = try NG2CycleSpool.testRecover(rootURL: root116, runID: store.runID, owner: owner116)
    check116(recovered.readOnly && !recovered.diagnosticInterrupted, "valid_seal_recovers_readonly_without_interruption_forgery")
    rejects116("recovered_seal_does_not_revive_writer") {
        _ = try recovered.commitFrame(captureID: 2, rgba: raw116, metadata: [:])
    }
    check116(try recovered.readRGBA(recovered.frames()[0]) == raw116, "all_recovered_original_pixels_match")
}
func fault116() throws {
    for boundary in ["part_open", "write", "file_sync", "rename", "directory_sync"] {
        let (_, store, clock) = try make116(), terminal = try terminal116(store)
        let before = try original116(store)
        NG2CycleSpoolTestHooks.beforeBoundary = { $0 != boundary }
        rejects116("seal_" + boundary) {
            _ = try store.sealContinuation(rootID: store.runID, index: 0, predecessorID: nil,
                clockID: clock, terminal: terminal, continuation: controller116(), successor: nil)
        }
        NG2CycleSpoolTestHooks.beforeBoundary = nil
        check116(store.readOnly, "failed_seal_never_revives_writer_" + boundary)
        try unchanged116(store, before, "failed_seal_preserves_all_prior_files_" + boundary)
        let recovered = try NG2CycleSpool.testRecover(rootURL: root116, runID: store.runID, owner: owner116)
        check116(recovered.readOnly, "failed_seal_recovery_is_readonly_" + boundary)
    }
}
// A stopped two-child cohort with one already converted PNG models process
// loss during export. These are real files, not restored input permissions.
func pair116() throws -> (String, String) {
    let (quota, first, firstClock) = try make116()
    let secondID=id116(), secondClock=id116()
    let next=try quota.reserveNext(runID:secondID,index:1,predecessorID:first.runID)
    _ = try first.commitRecord(kind:"continuation_reservation",cycle:0,payload:next.payload)
    let metadata:[String:Any] = ["generation":1,"stable_prefix":true,"capture_start_ns":start116+1,
        "completed_prefix_start":2,"completed_prefix_end":2,"inflight_start":false,"inflight_end":false]
    _ = try first.commitFrame(captureID:3,rgba:raw116,metadata:metadata)
    _ = try first.commitFrame(captureID:4,rgba:raw116,metadata:metadata)
    let terminal=try first.commitRecord(kind:"terminal",cycle:0,
        payload:["controller":["terminal":1,"input_state":0,"current_command_id":0]])
    _ = try first.sealContinuation(rootID:first.runID,index:0,predecessorID:nil,clockID:firstClock,
        terminal:terminal,continuation:controller116(qualified:true),successor:next)
    let png=try NG2CycleSpool.storedPNG(rgba:raw116), ref=try first.frames()[0]
    _ = try first.commitPNG(captureID:ref.captureID,bytes:png,metadata:["raw_sha256":ref.rawSHA256])
    let second=try NG2CycleSpool.testCreate(rootURL:root116,runID:secondID,owner:owner116,
        provenance:provenance116(next,clock:secondClock),quota:quota,reservation:next)
    let terminalSecond=try terminal116(second)
    var stopped=controller116(); stopped["successor_floor"] = true
    _ = try second.sealContinuation(rootID:first.runID,index:1,predecessorID:first.runID,
        clockID:secondClock,terminal:terminalSecond,continuation:stopped,successor:nil)
    return (first.runID,second.runID)
}
func alias116() throws {
    let (firstID,_) = try pair116()
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:firstID,owner:owner116)
    let original=try original116(source)
    let ledger=try source.createRecoveryExport(owner:owner116)
    let refs=try ledger.pngs()
    check116(refs.count == 1 && refs[0].captureID == 3,"sealed_original_png_readonly_alias")
    check116(try ledger.readPNG(refs[0]) == NG2CycleSpool.storedPNG(rgba:raw116),"alias_reads_exact_whole_original_png")
    try unchanged116(source,original,"readonly_alias_changes_no_original_file")
    let exportRoot=root116.appendingPathComponent("NGG2RecoveryExports")
    let physical=try FileManager.default.subpathsOfDirectory(atPath:exportRoot.path)
    check116(!physical.contains(where:{$0.hasSuffix(".png")}),"readonly_alias_does_not_copy_or_double_charge_png")
}
func recoveredQuota116() throws {
    let (_,secondID) = try pair116()
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:secondID,owner:owner116)
    NG2CycleSpoolTestHooks.availableBytes = 200 * 1024 * 1024
    rejects116("recovered_export_steals_other_slot_reservation") {
        _ = try source.createRecoveryExport(owner:owner116)
    }
    check116(source.readOnly,"recovery_quota_does_not_restore_input_or_writer")
}
let selected116 = CommandLine.arguments.dropFirst().first ?? "all"
switch selected116 {
case "quota": try quota116()
case "slot": try slot116()
case "seal": try seal116()
case "export": try export116()
case "fault": try fault116()
case "alias": try alias116()
case "recovered_quota": try recoveredQuota116()
case "all": try quota116(); try slot116(); try seal116(); try export116(); try fault116(); try alias116(); try recoveredQuota116()
default: print("FAIL unknown TEST116 Spool case"); exit(1)
}
print("PASS TEST116 Spool " + selected116)
