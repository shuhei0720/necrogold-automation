// TEST110 real filesystem + bounded logical-reservation tests. Procedural data
// only: these cases grant no controller/UI authority and assert no phone speed.
import Foundation

func check110(_ condition: Bool, _ label: String) {
    if !condition { print("FAIL " + label); exit(1) }
}
func rejects110(_ label: String, _ body: () throws -> Void) {
    do { try body(); print("FAIL accepted " + label); exit(1) } catch {}
}
let root110 = FileManager.default.temporaryDirectory.appendingPathComponent("ngg2-spool110-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root110, withIntermediateDirectories: false,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root110) }
var raw110 = Data(count: NG2CycleSpool.rasterBytes)
raw110.withUnsafeMutableBytes { raw in
    let bytes = raw.bindMemory(to: UInt8.self)
    for offset in stride(from: 3, to: bytes.count, by: 4) { bytes[offset] = 255 }
}
func make110(_ irregular: Bool = true) throws -> NG2CycleSpool {
    let id = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    return try NG2CycleSpool.testCreate(rootURL: root110, runID: id, owner: "reservation-host",
        provenance: irregular ? ["native_profile": "normal-1-1-irregular-v1"] : [:])
}
func reserve110(_ store: NG2CycleSpool, episode: UInt64 = 1, known: Set<UInt64> = [], future: Int = 0,
                pinned: Set<UInt64> = []) throws -> NG2CycleSpool.IrregularReservation {
    try store.reserveIrregular(episode: episode, prefix: 0, generation: 1,
        knownCaptureIDs: known, futureRoles: future, pinnedCaptureIDs: pinned)
}
// This primitive tests credit/identity only. Runtime separately validates and
// emits the closed native evidence payload before granting C durability.
func payload110(_ token: NG2CycleSpool.IrregularReservation) -> [String: Any] {
    ["generation": token.generation, "irregular": ["episode_id": token.episode]]
}
let kinds110 = ["irregular_checkpoint", "irregular_continue_intent", "irregular_continue_outcome",
                "irregular_restart_intent", "irregular_restart_outcome"]

func testDedup110() throws {
    let store = try make110()
    let existing = try store.commitFrame(captureID: 1, rgba: raw110, metadata: [:])
    let token = try reserve110(store, known: [1,2,3], future: 13, pinned: Set(1...8))
    var resource = try store.irregularResources(token)
    check110(resource["raw_slots"] as? Int == 15 && resource["raw_bytes"] as? Int == 15 * NG2CycleSpool.rasterBytes,
        "registered_raw_and_duplicate_role_not_reserved_twice")
    check110(resource["pin_slots"] as? Int == 13 && resource["episode_metadata_bytes"] as? Int == 220 * 1024 &&
        resource["final_metadata_bytes"] as? Int == 1080 * 1024, "early_episode_fits_original_pin24_and_exact_EF")
    _ = try store.commitFrame(captureID: 2, rgba: raw110, metadata: ["generation": 1], reservation: token)
    _ = try store.commitRecord(kind: kinds110[0], cycle: 0, payload: payload110(token), reservation: token)
    resource = try store.irregularResources(token)
    check110(resource["raw_slots"] as? Int == 14 && resource["episode_metadata_bytes"] as? Int == 184 * 1024,
        "completed_frame_record_credit_released_actual_bytes_remain_charged")
    try store.releaseIrregular(token)
    rejects110("released_token_cannot_be_replayed") { _ = try store.irregularResources(token) }
    let next = try reserve110(store, episode: 2, known: [1,2], future: 0, pinned: [1,2])
    let nextResource = try store.irregularResources(next)
    check110(nextResource["raw_slots"] as? Int == 0 && nextResource["final_metadata_bytes"] as? Int == 1080 * 1024,
        "F_pool_is_once_per_run_across_episodes")
    try store.releaseIrregular(next)
    let savedRaw = try store.readRGBA(existing), savedFrames = try store.frames()
    check110(savedRaw == raw110 && savedFrames.count == 2, "release_never_deletes_prior_raw_bytes")
    let recovered = try NG2CycleSpool.testRecover(rootURL: root110, runID: store.runID, owner: "recovered-owner")
    let recoveredFrames = try recovered.frames()
    check110(recovered.readOnly && recoveredFrames.count == 2, "recovery_keeps_bytes_without_live_reservation")
    rejects110("recovery_cannot_restore_retry_reservation") { _ = try reserve110(recovered, episode: 3) }
}
func testRawAndMetadata110() throws {
    let raw = try make110(); _ = try reserve110(raw, future: 16)
    rejects110("generic_raw_writer_cannot_take_16_reserved_slots") {
        try raw.reserveCheckpoint(frames: 29, metadataBytes: 0)
    }
    check110(raw.readOnly, "quota_failure_before_UI_holds_writer")
    let metadata = try make110(); _ = try reserve110(metadata)
    rejects110("generic_metadata_writer_cannot_take_EF") {
        _ = try metadata.commitRecord(kind: "diagnostic", cycle: 0,
            payload: ["padding": String(repeating: "a", count: 900 * 1024)])
    }
    check110((try metadata.records()).isEmpty, "metadata_failure_has_no_committed_intent")
    let pins = try make110()
    rejects110("pin24_bound_is_not_increased") { _ = try reserve110(pins, future: 16, pinned: Set(1...9)) }
    let geometry = try make110()
    rejects110("more_than16_role_bound") { _ = try reserve110(geometry, future: 17) }
    let old = try make110(false)
    let header = try JSONSerialization.jsonObject(with: old.sessionBytes()!) as! [String: Any]
    check110((header["provenance"] as? [String: Any])?["native_profile"] == nil, "old_header_bytes_have_no_new_profile_key")
    rejects110("old_profile_never_acquires_irregular_reservation") { _ = try reserve110(old) }
}
func testIdentityAndLimits110() throws {
    for changed in ["prefix", "generation", "episode"] {
        let store = try make110(), token = try reserve110(store, known: [1])
        let foreign = NG2CycleSpool.IrregularReservation(id: token.id,
            episode: changed == "episode" ? token.episode + 1 : token.episode,
            prefix: changed == "prefix" ? token.prefix + 1 : token.prefix,
            generation: changed == "generation" ? token.generation + 1 : token.generation)
        rejects110("wrong_token_" + changed) {
            _ = try store.commitFrame(captureID: 1, rgba: raw110, metadata: ["generation": 1], reservation: foreign)
        }
        check110((try store.frames()).isEmpty && store.readOnly, "foreign_token_writes_no_raw_" + changed)
    }
    let frameStore = try make110(), frameToken = try reserve110(frameStore, known: [1])
    rejects110("whole_frame_envelope_4KiB_limit") {
        _ = try frameStore.commitFrame(captureID: 1, rgba: raw110,
            metadata: ["generation": 1, "padding": String(repeating: "a", count: 4096)], reservation: frameToken)
    }
    let compact = try make110(), compactToken = try reserve110(compact)
    var payload = payload110(compactToken); payload["padding"] = String(repeating: "a", count: 32768)
    rejects110("whole_record_envelope_32KiB_limit") {
        _ = try compact.commitRecord(kind: kinds110[0], cycle: 0, payload: payload, reservation: compactToken)
    }
    let replay = try make110(), token = try reserve110(replay)
    _ = try replay.commitRecord(kind: kinds110[0], cycle: 0, payload: payload110(token), reservation: token)
    rejects110("same_compact_kind_not_replayed") {
        _ = try replay.commitRecord(kind: kinds110[0], cycle: 0, payload: payload110(token), reservation: token)
    }
    let noToken = try make110()
    rejects110("compact_record_requires_active_token") {
        _ = try noToken.commitRecord(kind: kinds110[0], cycle: 0, payload: [:])
    }
}
func testFinalPool110() throws {
    let store = try make110(), token = try reserve110(store)
    try store.releaseIrregular(token)
    _ = try store.commitRecord(kind: "diagnostic", cycle: 0,
        payload: ["padding": String(repeating: "a", count: 700 * 1024)])
    try store.reserveCheckpoint(frames: 0, metadataBytes: 512 * 1024, finalization: true)
    _ = try store.commitRecord(kind: "terminal", cycle: 0,
        payload: ["padding": String(repeating: "b", count: 400 * 1024)])
    let export = String(repeating: "1", count: 32)
    let manifest = try JSONSerialization.data(withJSONObject: ["export_id": export], options: [.sortedKeys])
    _ = try store.commitExportManifest(exportID: export, bytes: manifest)
    _ = try store.commitPublication(exportID: export,
        manifestSHA256: String(repeating: "2", count: 64), archiveSHA256: String(repeating: "3", count: 64))
    check110((try store.records()).count == 3, "reserved_terminal_manifest_receipt_fit_after_generic_writes")
}
func testPNGCredit110() throws {
    let store = try make110()
    let raw1 = try store.commitFrame(captureID: 1, rgba: raw110, metadata: [:])
    let raw2 = try store.commitFrame(captureID: 2, rgba: raw110, metadata: [:])
    let png = try NG2CycleSpool.storedPNG(rgba: raw110)
    _ = try store.commitPNG(captureID: 1, bytes: png, metadata: ["raw_sha256": raw1.rawSHA256])
    let token = try reserve110(store, known: [1,2], pinned: [1,2])
    let resources = try store.irregularResources(token)
    check110(resources["final_metadata_bytes"] as? Int == 1076 * 1024,
        "already_saved_PNG_envelope_is_not_reserved_twice")
    try store.releaseIrregular(token)
    _ = try store.commitRecord(kind: "terminal", cycle: 0, payload: [:])
    let encoded = try store.commitPNG(captureID: 2, bytes: png, metadata: ["raw_sha256": raw2.rawSHA256])
    let pngs = try store.pngs(), saved = try store.readPNG(encoded)
    check110(pngs.count == 2 && saved == png, "PNG_writer_consumes_its_reserved_F_credit")
    let export = String(repeating: "7", count: 32)
    let manifest = try JSONSerialization.data(withJSONObject: ["export_id": export], options: [.sortedKeys])
    _ = try store.commitExportManifest(exportID: export, bytes: manifest)
    _ = try store.commitPublication(exportID: export,
        manifestSHA256: String(repeating: "8", count: 64), archiveSHA256: String(repeating: "9", count: 64))
    let oversized = try make110()
    let frame = try oversized.commitFrame(captureID: 1, rgba: raw110, metadata: [:])
    let pending = try reserve110(oversized, known: [1], pinned: [1])
    try oversized.releaseIrregular(pending)
    _ = try oversized.commitRecord(kind: "terminal", cycle: 0, payload: [:])
    rejects110("whole_PNG_envelope_4KiB_limit") {
        _ = try oversized.commitPNG(captureID: 1, bytes: png,
            metadata: ["raw_sha256": frame.rawSHA256, "padding": String(repeating: "x", count: 4096)])
    }
    check110((try oversized.pngs()).isEmpty, "oversized_PNG_metadata_writes_no_PNG")
}
func testRecordSlots110(_ stealing: Bool) throws {
    let store = try make110(), token = try reserve110(store)
    for index in 0..<505 {
        _ = try store.commitRecord(kind: "diagnostic", cycle: 0, payload: ["index": index])
    }
    if stealing {
        rejects110("record512_reserved_slots_not_stolen") {
            _ = try store.commitRecord(kind: "diagnostic", cycle: 0, payload: [:])
        }
        return
    }
    for kind in kinds110 {
        _ = try store.commitRecord(kind: kind, cycle: 0, payload: payload110(token), reservation: token)
    }
    try store.releaseIrregular(token)
    _ = try store.commitRecord(kind: "terminal", cycle: 0, payload: [:])
    let export = String(repeating: "4", count: 32)
    let manifest = try JSONSerialization.data(withJSONObject: ["export_id": export], options: [.sortedKeys])
    _ = try store.commitExportManifest(exportID: export, bytes: manifest)
    _ = try store.commitPublication(exportID: export,
        manifestSHA256: String(repeating: "5", count: 64), archiveSHA256: String(repeating: "6", count: 64))
    check110((try store.records()).count == 512, "compact5_and_terminal_receipt2_have_reserved_record_slots")
}
func testSpaceRollback110() throws {
    let noSpace = try make110()
    let emptyCredits = noSpace.testIrregularCredits()
    NG2CycleSpoolTestHooks.availableBytes = 100 * 1024 * 1024
    rejects110("worstcase_disk_reservation_before_UI") { _ = try reserve110(noSpace, future: 16) }
    NG2CycleSpoolTestHooks.availableBytes = nil
    check110(noSpace.testIrregularCredits() == emptyCredits,
        "preflight_space_failure_rolls_back_unreturned_token")
    check110(noSpace.readOnly, "preflight_rollback_does_not_revive_writer")
    try noSpace.sealForRecovery()
    let diagnostic = try noSpace.createRecoveryExport(owner: "diagnostic-owner")
    _ = try diagnostic.commitRecord(kind: "terminal", cycle: 0, payload: ["input_authority": false])
    let export = diagnostic.recoveryExportID!
    let manifest = try JSONSerialization.data(withJSONObject: ["export_id": export], options: [.sortedKeys])
    _ = try diagnostic.commitExportManifest(exportID: export, bytes: manifest)
    check110((try diagnostic.exportManifest()) != nil && noSpace.readOnly,
        "failed_preflight_cannot_strand_diagnostic_terminal_manifest")
    let prior = try make110(), first = try reserve110(prior)
    try prior.releaseIrregular(first)
    let previousCredits = prior.testIrregularCredits()
    NG2CycleSpoolTestHooks.availableBytes = 100 * 1024 * 1024
    rejects110("later_episode_space_failure") { _ = try reserve110(prior, episode: 2, future: 16) }
    NG2CycleSpoolTestHooks.availableBytes = nil
    check110(prior.testIrregularCredits() == previousCredits &&
        previousCredits["final_metadata_bytes"] == 1080 * 1024 && prior.readOnly,
        "failed_later_episode_preserves_existing_F_without_new_E")
}
func testFSFailures110() throws {
    let noSpace = try make110()
    NG2CycleSpoolTestHooks.availableBytes = 100 * 1024 * 1024
    rejects110("worstcase_disk_reservation_before_UI") { _ = try reserve110(noSpace, future: 16) }
    NG2CycleSpoolTestHooks.availableBytes = nil
    let noSpaceFrames = try noSpace.frames(), noSpaceRecords = try noSpace.records()
    check110(noSpaceFrames.isEmpty && noSpaceRecords.isEmpty && noSpace.readOnly,
        "space_failure_has_no_UI_intent_or_raw_write")
    for boundary in ["part_open", "write", "file_sync", "rename", "directory_sync"] {
        let store = try make110(), token = try reserve110(store, known: [1])
        var reached = [String](), failedAt: String?
        NG2CycleSpoolTestHooks.beforeBoundary = { name in
            reached.append(name)
            return name != boundary
        }
        do {
            _ = try store.commitFrame(captureID: 1, rgba: raw110, metadata: ["generation": 1], reservation: token)
            check110(false, "accepted_reserved_write_fault_" + boundary)
        } catch NG2CycleSpool.Failure.io(let reason) {
            failedAt = reason
        } catch {
            check110(false, "wrong_error_before_reserved_FS_boundary_" + boundary)
        }
        NG2CycleSpoolTestHooks.beforeBoundary = nil
        check110(reached.last == boundary && reached.filter({ $0 == boundary }).count == 1 &&
            failedAt == "injected-" + boundary, "actual_FS_fault_reached_exact_boundary_" + boundary)
        check110(store.readOnly, "actual_FS_fault_freezes_" + boundary)
        try store.releaseIrregular(token)
        rejects110("failed_writer_cannot_create_intent_" + boundary) {
            _ = try store.commitRecord(kind: kinds110[1], cycle: 0, payload: payload110(token), reservation: token)
        }
    }
}
if CommandLine.arguments.last == "record_steal" { try testRecordSlots110(true) }
else if CommandLine.arguments.last == "space_rollback" { try testSpaceRollback110() }
else {
    try testDedup110(); try testRawAndMetadata110(); try testIdentityAndLimits110()
    try testFinalPool110(); try testPNGCredit110(); try testRecordSlots110(true); try testRecordSlots110(false)
    try testSpaceRollback110(); try testFSFailures110()
}
print("PASS TEST110 Spool actual filesystem reservation/dedup/record512/finalization/fault/recovery")
