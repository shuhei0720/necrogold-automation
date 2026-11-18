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
     "root_deadline_ns": deadline116, "qualified_ns": qualified ? start116+5 : 0,
     "parent_deadline_ns": qualified ? start116+6 : 0, "old_job_id": qualified ? 1 : 0,
     "restart_command_id": qualified ? 2 : 0, "new_floor_capture_id": qualified ? 3 : 0,
     "source_capture_id": qualified ? 4 : 0, "source_start_ns": qualified ? start116+3 : 0,
     "source_prefix": qualified ? 2 : 0]
}
func terminal116(_ store: NG2CycleSpool, continuation: [String:Any]? = nil,
                 inputState: UInt64 = 0, commandID: UInt64 = 0) throws -> NG2CycleSpool.RecordRef {
    _ = try store.commitFrame(captureID: 1, rgba: raw116, metadata: ["generation": 1])
    return try store.commitRecord(kind: "terminal", cycle: 0,
        payload: ["controller": ["terminal": 1, "input_state": inputState, "current_command_id": commandID,
            "continuous_campaign":continuation ?? controller116()]])
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
    var metadata:[String:Any] = ["generation":1,"stable_prefix":true,"capture_start_ns":start116+1,
        "capture_end_ns":start116+2,"completed_prefix_start":2,"completed_prefix_end":2,
        "inflight_start":false,"inflight_end":false]
    _ = try first.commitFrame(captureID:3,rgba:raw116,metadata:metadata)
    metadata["capture_start_ns"] = start116+3; metadata["capture_end_ns"] = start116+4
    _ = try first.commitFrame(captureID:4,rgba:raw116,metadata:metadata)
    let terminal=try first.commitRecord(kind:"terminal",cycle:0,
        payload:["controller":["terminal":1,"input_state":0,"current_command_id":0,
            "continuous_campaign":controller116(qualified:true)]])
    _ = try first.sealContinuation(rootID:first.runID,index:0,predecessorID:nil,clockID:firstClock,
        terminal:terminal,continuation:controller116(qualified:true),successor:next)
    let png=try NG2CycleSpool.storedPNG(rgba:raw116), ref=try first.frames()[0]
    _ = try first.commitPNG(captureID:ref.captureID,bytes:png,metadata:["raw_sha256":ref.rawSHA256])
    let second=try NG2CycleSpool.testCreate(rootURL:root116,runID:secondID,owner:owner116,
        provenance:provenance116(next,clock:secondClock),quota:quota,reservation:next)
    var stopped=controller116(); stopped["successor_floor"] = true
    let terminalSecond=try terminal116(second,continuation:stopped)
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
func diagnosticUnknown116() throws {
    for state:UInt64 in [3,4] {
        let (_,store,clock)=try make116(), terminal=try terminal116(store,inputState:state,commandID:23)
        let before=try original116(store)
        do {
            _ = try store.sealContinuation(rootID:store.runID,index:0,predecessorID:nil,clockID:clock,
                terminal:terminal,continuation:controller116(),successor:nil)
        } catch { print("FAIL diagnostic_unknown_seal_preserves_unresolved_input"); exit(1) }
        try unchanged116(store,before,"diagnostic_seal_preserves_original_unknown_command")
        let saved=try store.records().first(where:{$0.kind == "terminal"})!
        let controller=saved.payload["controller"] as! [String:Any]
        check116((controller["input_state"] as? NSNumber)?.uint64Value == state &&
            (controller["current_command_id"] as? NSNumber)?.uint64Value == 23,"diagnostic_seal_does_not_erase_unknown")
        let recovered=try NG2CycleSpool.testRecover(rootURL:root116,runID:store.runID,owner:owner116)
        check116(recovered.readOnly && recovered.controlContentSealed,"diagnostic_seal_never_restores_authority")
    }
}
func recordIntegrity116() throws {
    for fault in ["old_record","passed_terminal","passed_controller","session"] {
        let (_,store,clock)=try make116()
        _ = try store.commitRecord(kind:"checkpoint",cycle:0,payload:["marker":"a"])
        let terminal=try terminal116(store)
        var passed=terminal, companion=controller116()
        if fault == "old_record" {
            let path=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(store.runID)
                .appendingPathComponent("record-0001-checkpoint.json")
            let text=String(data:try Data(contentsOf:path),encoding:.utf8)!
            let damaged=text.replacingOccurrences(of:"\"marker\":\"a\"",with:"\"marker\":\"b\"")
            check116(damaged != text,"record_corruption_fixture_changes_actual_bytes")
            try Data(damaged.utf8).write(to:path)
        } else if fault == "session" {
            let path=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(store.runID).appendingPathComponent("session.json")
            var header=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as! [String:Any]
            header["owner_sha256"] = String(repeating:"f",count:64)
            try JSONSerialization.data(withJSONObject:header,options:[.sortedKeys,.withoutEscapingSlashes]).write(to:path)
        } else if fault == "passed_terminal" {
            var payload=terminal.payload;payload["forged"] = true
            passed=NG2CycleSpool.RecordRef(sequence:terminal.sequence,kind:terminal.kind,cycle:terminal.cycle,
                sha256:terminal.sha256,previous:terminal.previous,payload:payload)
        } else { companion["source_prefix"] = 7 }
        let before=try original116(store)
        rejects116("seal_integrity_"+fault) {
            _ = try store.sealContinuation(rootID:store.runID,index:0,predecessorID:nil,clockID:clock,
                terminal:passed,continuation:companion,successor:nil)
        }
        try unchanged116(store,before,"failed_integrity_seal_writes_no_new_control_record_"+fault)
        check116(store.readOnly,"failed_integrity_seal_freezes_original_writer_"+fault)
    }
}
func unsealedPredecessor116() throws {
    let (quota,store,_)=try make116(), next=try quota.reserveNext(runID:id116(),index:1,predecessorID:store.runID)
    let before=try original116(store)
    rejects116("create_before_predecessor_seal") {
        _ = try NG2CycleSpool.testCreate(rootURL:root116,runID:next.runID,owner:owner116,
            provenance:provenance116(next,clock:id116()),quota:quota,reservation:next)
    }
    let path=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(next.runID)
    check116(!FileManager.default.fileExists(atPath:path.path),"reservation_creates_no_prepared_child_namespace")
    try unchanged116(store,before,"preseal_child_rejection_preserves_parent")
}
func aliasIntegrity116() throws {
    for fault in ["metadata","png","orphan"] {
        let (firstID,_) = try pair116()
        let directory=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(firstID)
        var orphan:String?
        if fault == "orphan" {
            orphan=".part-"+UUID().uuidString.lowercased()
            check116(FileManager.default.createFile(atPath:directory.appendingPathComponent(orphan!).path,
                contents:Data("uncommitted".utf8),attributes:[.posixPermissions:NSNumber(value:0o600)]),"orphan_fixture_created")
        }
        let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:firstID,owner:owner116)
        let ledger=try source.createRecoveryExport(owner:owner116), refs=try ledger.pngs()
        check116(refs.count == 1,"integrity_fixture_retains_one_verified_original_alias")
        if fault == "orphan" {
            check116(source.diagnosticInterrupted && source.readOnly,"orphan_is_diagnostic_not_new_input_authority")
            check116(try source.artifacts().contains(where:{$0.name == orphan! && $0.role == "uncommitted"}),"orphan_original_bytes_are_in_inventory")
            check116(try ledger.readPNG(refs[0]) == NG2CycleSpool.storedPNG(rgba:raw116),"orphan_never_hides_verified_committed_png")
        } else {
            let path=directory.appendingPathComponent(String(format:"png-%016llx.",refs[0].captureID)+(fault == "png" ? "png":"json"))
            if fault == "metadata" {
                var envelope=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as! [String:Any]
                var metadata=envelope["metadata"] as! [String:Any]
                metadata["raw_sha256"] = String(repeating:"0",count:64);envelope["metadata"] = metadata
                try JSONSerialization.data(withJSONObject:envelope,options:[.sortedKeys,.withoutEscapingSlashes]).write(to:path)
            } else {
                var bytes=try Data(contentsOf:path);bytes[100] ^= 1;try bytes.write(to:path)
            }
            let before=try original116(source)
            rejects116("alias_read_revalidates_original_"+fault) { _ = try ledger.readPNG(refs[0]) }
            try unchanged116(source,before,"alias_integrity_failure_changes_no_original_file_"+fault)
        }
    }
}
func publishedPair116(_ corrupt:Bool, receiptOnly:Bool = false) throws -> (String,String) {
    let (firstID,secondID)=try pair116()
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:firstID,owner:owner116)
    let ledger=try source.createRecoveryExport(owner:owner116), exportID=ledger.recoveryExportID!
    let bytes=try JSONSerialization.data(withJSONObject:["export_id":exportID],options:[.sortedKeys])
    let manifest=try ledger.commitExportManifest(exportID:exportID,bytes:bytes)
    let receipt:NG2CycleSpool.RecordRef
    let receiptDirectory:String
    if receiptOnly {
        rejects116("real_publication_rejects_unmatched_manifest_hash_before_receipt") {
            _ = try source.commitRecoveredPublication(owner:owner116,exportID:exportID,
                manifestSHA256:String(repeating:"b",count:64),archiveSHA256:String(repeating:"a",count:64))
        }
        receipt=try source.commitRecoveredPublication(owner:owner116,exportID:exportID,manifestSHA256:manifest.sha256,
            archiveSHA256:String(repeating:"a",count:64))
        let stores=try source.recoveryExports(owner:owner116)
        let store=try stores.first(where:{try $0.records().last?.sha256 == receipt.sha256})!
        receiptDirectory=firstID+"-"+store.recoveryExportID!
        let storedManifest=try store.exportManifest()
        check116(storedManifest == nil,"real_recovered_publication_is_an_immutable_receipt_only_sibling")
    } else {
        receipt=try ledger.commitPublication(exportID:exportID,manifestSHA256:manifest.sha256,archiveSHA256:String(repeating:"a",count:64))
        receiptDirectory=firstID+"-"+exportID
    }
    if corrupt {
        let path=root116.appendingPathComponent("NGG2RecoveryExports")
            .appendingPathComponent(receiptDirectory)
            .appendingPathComponent(String(format:"record-%04d-published.json",receipt.sequence))
        var value=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as! [String:Any]
        var payload=value["payload"] as! [String:Any];payload["manifest_sha256"] = String(repeating:"b",count:64)
        value["payload"] = payload
        try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys,.withoutEscapingSlashes]).write(to:path)
    }
    // Scope ends here: no source/quota/ledger process reference is returned.
    return (firstID,secondID)
}
func publishedQuota116() throws {
    for (corrupt,receiptOnly) in [(false,false),(true,false),(false,true),(true,true)] {
        let (firstID,secondID)=try publishedPair116(corrupt,receiptOnly:receiptOnly)
        let pending=try NG2CycleSpool.testUnpublishedRunIDs(rootURL:root116)
        check116(pending.contains(firstID) == corrupt,"prepare_pending_uses_same_verified_recovery_publication_as_quota")
        let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:secondID,owner:owner116)
        NG2CycleSpoolTestHooks.availableBytes = 200 * 1024 * 1024
        if corrupt {
            rejects116("unmatched_receipt_cannot_release_other_slot_reservation") { _ = try source.createRecoveryExport(owner:owner116) }
        } else {
            do { _ = try source.createRecoveryExport(owner:owner116) }
            catch { print("FAIL verified_recovered_publication_releases_unused_reservation");exit(1) }
        }
        check116(source.readOnly,"publication_accounting_does_not_restore_control")
    }
    for corrupt in [false,true] {
        let (_,store,clock)=try make116(), terminal=try terminal116(store)
        _ = try store.sealContinuation(rootID:store.runID,index:0,predecessorID:nil,clockID:clock,
            terminal:terminal,continuation:controller116(),successor:nil)
        let exportID=id116(), bytes=try JSONSerialization.data(withJSONObject:["export_id":exportID],options:[.sortedKeys])
        let manifest=try store.commitExportManifest(exportID:exportID,bytes:bytes)
        let receipt=try store.commitPublication(exportID:exportID,manifestSHA256:manifest.sha256,
            archiveSHA256:String(repeating:"a",count:64))
        if corrupt {
            let path=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(store.runID)
                .appendingPathComponent(String(format:"record-%04d-published.json",receipt.sequence))
            var value=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as! [String:Any]
            var payload=value["payload"] as! [String:Any];payload["manifest_sha256"] = String(repeating:"b",count:64)
            value["payload"] = payload
            try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys,.withoutEscapingSlashes]).write(to:path)
        }
        let pending=try NG2CycleSpool.testUnpublishedRunIDs(rootURL:root116)
        check116(pending.contains(store.runID) == corrupt,"normal_publication_manifest_binding_controls_prepare_pending")
    }
    let (_,original,clock)=try make116(), terminal=try terminal116(original)
    _ = try original.sealContinuation(rootID:original.runID,index:0,predecessorID:nil,clockID:clock,
        terminal:terminal,continuation:controller116(),successor:nil)
    let exportID=id116(), bytes=try JSONSerialization.data(withJSONObject:["export_id":exportID],options:[.sortedKeys])
    let manifest=try original.commitExportManifest(exportID:exportID,bytes:bytes)
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:original.runID,owner:owner116)
    let before=try original116(source)
    rejects116("original_manifest_recovery_rejects_wrong_identity_before_receipt") {
        _ = try source.commitRecoveredPublication(owner:owner116,exportID:id116(),manifestSHA256:manifest.sha256,
            archiveSHA256:String(repeating:"a",count:64))
    }
    let receipt=try source.commitRecoveredPublication(owner:owner116,exportID:exportID,manifestSHA256:manifest.sha256,
        archiveSHA256:String(repeating:"a",count:64))
    let repeated=try source.commitRecoveredPublication(owner:owner116,exportID:exportID,manifestSHA256:manifest.sha256,
        archiveSHA256:String(repeating:"a",count:64))
    check116(receipt.sha256 == repeated.sha256,"original_readonly_manifest_publication_is_idempotent")
    rejects116("original_manifest_recovery_rejects_conflicting_archive_receipt") {
        _ = try source.commitRecoveredPublication(owner:owner116,exportID:exportID,manifestSHA256:manifest.sha256,
            archiveSHA256:String(repeating:"c",count:64))
    }
    let pending=try NG2CycleSpool.testUnpublishedRunIDs(rootURL:root116)
    check116(!pending.contains(original.runID),"original_readonly_manifest_receipt_removes_pending_with_exact_binding")
    try unchanged116(source,before,"receipt_only_publication_never_rewrites_original_manifest_or_control_bytes")
}
func orphanAccounting116() throws {
    let (quota,source,clock)=try make116(), terminal=try terminal116(source)
    _ = try quota.reserveNext(runID:id116(),index:1,predecessorID:source.runID)
    _ = try source.sealContinuation(rootID:source.runID,index:0,predecessorID:nil,clockID:clock,
        terminal:terminal,continuation:controller116(),successor:nil)
    let png=try NG2CycleSpool.storedPNG(rgba:raw116), ref=try source.frames()[0]
    var boundaries=0
    NG2CycleSpoolTestHooks.beforeBoundary = { name in
        if name == "directory_sync" { boundaries += 1;return boundaries != 1 }
        return true
    }
    rejects116("png_rename_without_metadata") {
        _ = try source.commitPNG(captureID:ref.captureID,bytes:png,metadata:["raw_sha256":ref.rawSHA256])
    }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    let savedPNGs=try source.pngs()
    check116(source.readOnly && savedPNGs.isEmpty,"failed_png_remains_physical_but_unregistered")
    let before=try original116(source), used=before.values.reduce(0) {$0+$1.count}
    check116(before.keys.contains(where:{$0.hasSuffix(".png")}),"PNG_fault_fixture_left_real_uncommitted_original")
    NG2CycleSpoolTestHooks.availableBytes = UInt64(2 * 156 * 1024 * 1024 - used + 512 * 1024)
    try source.sealForRecovery()
    let ledger:NG2CycleSpool
    do { ledger=try source.createRecoveryExport(owner:owner116) }
    catch { print("FAIL in_process_orphan_is_charged_before_fallback");exit(1) }
    let converted=try ledger.commitPNG(captureID:ref.captureID,bytes:png,metadata:["raw_sha256":ref.rawSHA256])
    check116(try ledger.readPNG(converted) == png,"fallback_uses_remaining_slot_without_promoting_orphan_png")
    try unchanged116(source,before,"fallback_preserves_unregistered_PNG_and_all_original_control_bytes")
    let (_,partial,_) = try make116()
    NG2CycleSpoolTestHooks.beforeBoundary = { $0 != "file_sync" }
    rejects116("raw_atomic_fault_leaves_real_part") {
        _ = try partial.commitFrame(captureID:1,rgba:raw116,metadata:[:])
    }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    try partial.sealForRecovery()
    let partialBefore=try original116(partial)
    let savedParts=partialBefore.filter { $0.key.hasPrefix(".part-") }
    check116(savedParts.count == 1 && savedParts.values.first?.count == NG2CycleSpool.rasterBytes,
        "raw_fault_keeps_one_actual_1_48MiB_part")
    let recovery=try partial.createRecoveryExport(owner:owner116)
    let ledgerPath=root116.appendingPathComponent("NGG2RecoveryExports")
        .appendingPathComponent(partial.runID+"-"+recovery.recoveryExportID!)
    let filesBefore=try FileManager.default.contentsOfDirectory(atPath:ledgerPath.path).sorted()
    var pngPartOpened=false
    NG2CycleSpoolTestHooks.beforeBoundary = { name in
        if name == "part_open" { pngPartOpened=true }
        return true
    }
    rejects116("second_atomic_part_exceeds_same_slot_two_MiB") {
        _ = try recovery.commitPNG(captureID:1,bytes:png,metadata:["raw_sha256":hash116(raw116)])
    }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    check116(!pngPartOpened,"atomic_temp_cap_rejects_before_new_part_open")
    check116(try FileManager.default.contentsOfDirectory(atPath:ledgerPath.path).sorted() == filesBefore,
        "atomic_temp_failure_creates_no_second_orphan")
    try unchanged116(partial,partialBefore,"temp_quota_failure_preserves_original_raw_part_and_metadata")
    try recovery.sealForRecovery()
    _ = try recovery.artifacts()
    let artifact=try partial.artifacts().first(where:{$0.name.hasPrefix(".part-")})!
    check116(try partial.readArtifact(id:artifact.id,offset:0,length:64) == Data(raw116.prefix(64)),
        "bounded_temp_failure_keeps_original_inventory_and_bytes_readable")
    let (_,shared,sharedClock)=try make116(), sharedTerminal=try terminal116(shared)
    _ = try shared.sealContinuation(rootID:shared.runID,index:0,predecessorID:nil,clockID:sharedClock,
        terminal:sharedTerminal,continuation:controller116(),successor:nil)
    try shared.sealForRecovery()
    let first=try shared.createRecoveryExport(owner:owner116,forceFresh:true)
    let second=try shared.createRecoveryExport(owner:owner116,forceFresh:true)
    let firstEntered=DispatchSemaphore(value:0), releaseFirst=DispatchSemaphore(value:0), firstDone=DispatchSemaphore(value:0)
    let stateGate=NSLock();var blocked=false;var firstError:Error?
    NG2CycleSpoolTestHooks.beforeBoundary = { name in
        guard name == "part_open" else { return true }
        stateGate.lock();let shouldBlock = !blocked;blocked=true;stateGate.unlock()
        if shouldBlock { firstEntered.signal();releaseFirst.wait() }
        return true
    }
    DispatchQueue.global().async {
        do { _ = try first.commitPNG(captureID:1,bytes:png,metadata:["raw_sha256":hash116(raw116)]) }
        catch { stateGate.lock();firstError=error;stateGate.unlock() }
        firstDone.signal()
    }
    check116(firstEntered.wait(timeout:.now()+5) == .success,"first_writer_holds_an_active_atomic_reservation_before_part_open")
    rejects116("parallel_writer_cannot_reuse_other_active_atomic_temp") {
        _ = try second.commitPNG(captureID:1,bytes:png,metadata:["raw_sha256":hash116(raw116)])
    }
    releaseFirst.signal()
    check116(firstDone.wait(timeout:.now()+5) == .success,"first_atomic_writer_returns_after_release")
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    stateGate.lock();let completedWithoutError = firstError == nil;stateGate.unlock()
    check116(completedWithoutError,"first_reserved_atomic_completes_without_other_writer_stealing_capacity")
    let firstPNG=try first.pngs()[0]
    check116(try first.readPNG(firstPNG) == png,"parallel_temp_rejection_preserves_first_whole_png")
}
func failedPair116() throws -> (String,String) {
    let (quota,first,clock)=try make116(), child=id116()
    let next=try quota.reserveNext(runID:child,index:1,predecessorID:first.runID)
    _ = try first.commitRecord(kind:"continuation_reservation",cycle:0,payload:next.payload)
    var metadata:[String:Any] = ["generation":1,"stable_prefix":true,"capture_start_ns":start116+1,
        "capture_end_ns":start116+2,"completed_prefix_start":2,"completed_prefix_end":2,
        "inflight_start":false,"inflight_end":false]
    _ = try first.commitFrame(captureID:3,rgba:raw116,metadata:metadata)
    metadata["capture_start_ns"] = start116+3; metadata["capture_end_ns"] = start116+4
    _ = try first.commitFrame(captureID:4,rgba:raw116,metadata:metadata)
    let terminal=try first.commitRecord(kind:"terminal",cycle:0,payload:["controller":[
        "terminal":1,"input_state":0,"current_command_id":0,"continuous_campaign":controller116(qualified:true)]])
    _ = try first.sealContinuation(rootID:first.runID,index:0,predecessorID:nil,clockID:clock,
        terminal:terminal,continuation:controller116(qualified:true),successor:next)
    NG2CycleSpoolTestHooks.writeLimit = 0
    rejects116("child_session_header_write_failure") {
        _ = try NG2CycleSpool.testCreate(rootURL:root116,runID:child,owner:owner116,
            provenance:provenance116(next,clock:id116()),quota:quota,reservation:next)
    }
    NG2CycleSpoolTestHooks.writeLimit = nil
    return (first.runID,child)
}
func orphanQuota116() throws {
    let (_,child)=try failedPair116()
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:child,owner:owner116)
    check116(try source.sessionBytes() == nil,"failed_child_header_is_not_repaired_or_forged")
    check116(source.readOnly && source.diagnosticInterrupted,"failed_child_stays_readonly_diagnostic")
    NG2CycleSpoolTestHooks.availableBytes = 200 * 1024 * 1024
    rejects116("partial_child_export_steals_parent_cohort_reservation") {
        _ = try source.createRecoveryExport(owner:owner116)
    }
}
func damagedOwner116() throws {
    for damage in ["owner0","owner1","root_id","missing_header"] {
        let (first,second)=try pair116(), target=damage == "owner1" ? second:first
        let path=root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(target).appendingPathComponent("session.json")
        if damage == "missing_header" { try FileManager.default.removeItem(at:path) }
        else {
            var header=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as! [String:Any]
            if damage == "root_id" {
                var provenance=header["provenance"] as! [String:Any]
                var continuous=provenance["continuous_campaign"] as! [String:Any]
                continuous["root_id"] = id116();provenance["continuous_campaign"] = continuous;header["provenance"] = provenance
            } else { header["owner_sha256"] = String(repeating:"f",count:64) }
            try JSONSerialization.data(withJSONObject:header,options:[.sortedKeys,.withoutEscapingSlashes]).write(to:path)
        }
        let source:NG2CycleSpool
        do { source=try NG2CycleSpool.testRecover(rootURL:root116,runID:target,owner:owner116) }
        catch { print("FAIL damaged_owner_keeps_readonly_forensic_recovery");exit(1) }
        check116(source.readOnly && source.diagnosticInterrupted,"damaged_owner_is_evidence_not_authority")
        let before=try original116(source)
        NG2CycleSpoolTestHooks.availableBytes = 200 * 1024 * 1024
        rejects116("damaged_header_keeps_other_child_reservation_"+damage) {
            _ = try source.createRecoveryExport(owner:owner116)
        }
        NG2CycleSpoolTestHooks.availableBytes = 4 * 1024 * 1024 * 1024
        let ledger=try source.createRecoveryExport(owner:owner116)
        let originals=try source.pngs(), aliases=try ledger.pngs()
        check116(originals.count == (target == first ? 1:0) && aliases.count == originals.count,
            "damaged_header_keeps_independently_valid_original_png_aliases")
        if let ref=aliases.first {
            check116(try ledger.readPNG(ref) == NG2CycleSpool.storedPNG(rgba:raw116),
                "damaged_header_png_alias_rechecks_original_metadata_and_whole_png")
        }
        try unchanged116(source,before,"damaged_owner_forensic_export_repairs_no_original_header")
    }
    let (first,second)=try pair116()
    let base=root116.appendingPathComponent("NGG2Cycles")
    try FileManager.default.removeItem(at:base.appendingPathComponent(first).appendingPathComponent("session.json"))
    for name in try FileManager.default.contentsOfDirectory(atPath:base.appendingPathComponent(second).path)
        where name.hasSuffix("-continuation_seal.json") {
        try FileManager.default.removeItem(at:base.appendingPathComponent(second).appendingPathComponent(name))
    }
    let unresolved=try NG2CycleSpool.testRecover(rootURL:root116,runID:first,owner:owner116)
    let artifacts=try unresolved.artifacts()
    check116(unresolved.readOnly && unresolved.diagnosticInterrupted && artifacts.contains(where:{$0.name.hasSuffix("-continuation_reservation.json")}),
        "unresolved_missing_header_keeps_readable_original_new_mode_markers")
    rejects116("unresolved_new_mode_never_falls_back_to_standalone_export") {
        _ = try unresolved.createRecoveryExport(owner:owner116)
    }
}
func recoveryNamespace116() throws {
    let (_,store,clock)=try make116(), terminal=try terminal116(store)
    _ = try store.sealContinuation(rootID:store.runID,index:0,predecessorID:nil,clockID:clock,
        terminal:terminal,continuation:controller116(),successor:nil)
    let source=try NG2CycleSpool.testRecover(rootURL:root116,runID:store.runID,owner:owner116)
    let base=root116.appendingPathComponent("NGG2RecoveryExports")
    try FileManager.default.createDirectory(at:base,withIntermediateDirectories:false,
        attributes:[.posixPermissions:NSNumber(value:0o700)])
    for index in 0..<128 {
        try FileManager.default.createDirectory(at:base.appendingPathComponent(store.runID+"-"+String(format:"%032x",index)),
            withIntermediateDirectories:false,attributes:[.posixPermissions:NSNumber(value:0o700)])
    }
    rejects116("recovery_namespace129") { _ = try source.createRecoveryExport(owner:owner116,forceFresh:true) }
    check116(try FileManager.default.contentsOfDirectory(atPath:base.path).count == 128,"recovery_cap_checked_before_mkdir")
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
case "diagnostic_unknown": try diagnosticUnknown116()
case "record_integrity": try recordIntegrity116()
case "preseal": try unsealedPredecessor116()
case "alias_integrity": try aliasIntegrity116()
case "published_quota": try publishedQuota116()
case "orphan_accounting": try orphanAccounting116()
case "orphan_quota": try orphanQuota116()
case "damaged_owner": try damagedOwner116()
case "recovery_namespace": try recoveryNamespace116()
case "all": try quota116(); try slot116(); try seal116(); try export116(); try fault116(); try alias116(); try recoveredQuota116(); try diagnosticUnknown116(); try recordIntegrity116(); try unsealedPredecessor116(); try aliasIntegrity116(); try publishedQuota116(); try orphanAccounting116(); try orphanQuota116(); try damagedOwner116(); try recoveryNamespace116()
default: print("FAIL unknown TEST116 Spool case"); exit(1)
}
print("PASS TEST116 Spool " + selected116)
