// TEST094 real filesystem/fault-boundary fixture. macOS host only; no game input.
import Foundation

func check(_ condition: Bool, _ label: String) {
    if !condition { print("FAIL " + label); exit(1) }
}
func rejects(_ label: String, _ body: () throws -> Void) {
    do { try body(); print("FAIL accepted " + label); exit(1) } catch {}
}
let root = FileManager.default.temporaryDirectory.appendingPathComponent("ngg2-spool-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root) }
let runID = String(repeating: "a", count: 32)
let owner = "host-fixture-owner"
var rgba = Data(count: NG2CycleSpool.rasterBytes)
rgba.withUnsafeMutableBytes { raw in
    let bytes = raw.bindMemory(to: UInt8.self)
    for offset in stride(from: 0, to: bytes.count, by: 4) {
        bytes[offset] = UInt8(truncatingIfNeeded: offset / 4)
        bytes[offset+1] = UInt8(truncatingIfNeeded: offset / 896)
        bytes[offset+2] = UInt8(truncatingIfNeeded: offset / 17)
        bytes[offset+3] = 255
    }
}
let png = try NG2CycleSpool.storedPNG(rgba: rgba)
check(png.count == 1_484_368, "stored PNG exact bound")
check(png.count <= 2 * 1024 * 1024, "stored PNG export bound")
try png.write(to: root.appendingPathComponent("roundtrip.png"))
// The Python runner independently decodes this PNG and checks every pixel.
try rgba.write(to: root.appendingPathComponent("roundtrip.rgba"))

let spool = try NG2CycleSpool.testCreate(rootURL: root, runID: runID, owner: owner)
try spool.reserveCheckpoint(frames: 6, metadataBytes: 32 * 1024)
NG2CycleSpoolTestHooks.writeLimit = 113
let frame = try spool.commitFrame(captureID: 17, rgba: rgba,
                                 metadata: ["capture_start_ns": 7, "completed_prefix": 0])
NG2CycleSpoolTestHooks.writeLimit = nil
check(try spool.readRGBA(frame) == rgba, "short writes produce every original byte")
check((try spool.frameMetadata(frame))["capture_start_ns"] as? Int == 7, "immutable metadata")
rejects("duplicate capture overwrite") {
    _ = try spool.commitFrame(captureID: 17, rgba: rgba, metadata: [:])
}
check(try spool.readRGBA(frame) == rgba, "duplicate preserves prior bytes")

let reopened = try NG2CycleSpool.testRecover(rootURL: root, runID: runID, owner: owner)
check(reopened.readOnly, "recovery always read only")
check(try reopened.frames().count == 1, "recovery registered set")
rejects("recovery input-write authority") {
    _ = try reopened.commitRecord(kind: "restart-intent", cycle: 1, payload: [:])
}
let changedOwner = try NG2CycleSpool.testRecover(rootURL: root, runID: runID, owner: "different-owner")
check(changedOwner.readOnly && changedOwner.storedOwnerSHA256 == reopened.storedOwnerSHA256,
      "new authenticated owner recovers original owner provenance read only")
rejects("run path traversal") {
    _ = try NG2CycleSpool.testCreate(rootURL: root, runID: "../outside", owner: owner)
}

for boundary in ["part_open", "write", "file_sync", "rename", "directory_sync"] {
    let id = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    let faulted = try NG2CycleSpool.testCreate(rootURL: root, runID: id, owner: owner)
    NG2CycleSpoolTestHooks.beforeBoundary = { $0 != boundary }
    rejects("fault " + boundary) {
        _ = try faulted.commitFrame(captureID: 1, rgba: rgba, metadata: [:])
    }
    NG2CycleSpoolTestHooks.beforeBoundary = nil
    check(faulted.readOnly, "fault permanently revokes writer " + boundary)
    rejects("postfault intent " + boundary) {
        _ = try faulted.commitRecord(kind: "restart-intent", cycle: 1, payload: [:])
    }
}

let symlinkID = String(repeating: "b", count: 32)
let directory = root.appendingPathComponent("NGG2Cycles")
try FileManager.default.createSymbolicLink(at: directory.appendingPathComponent(symlinkID), withDestinationURL: root)
rejects("symlink session create") {
    _ = try NG2CycleSpool.testCreate(rootURL: root, runID: symlinkID, owner: owner)
}
rejects("symlink session recover") {
    _ = try NG2CycleSpool.testRecover(rootURL: root, runID: symlinkID, owner: owner)
}

let recordID = String(repeating: "c", count: 32)
let records = try NG2CycleSpool.testCreate(rootURL: root, runID: recordID, owner: owner)
let intent = try records.commitRecord(kind: "restart-intent", cycle: 1, payload: ["command_id": 5])
let outcome = try records.commitRecord(kind: "restart-outcome", cycle: 1, payload: ["ack": "unknown"], previous: intent.sha256)
check(outcome.previous == intent.sha256, "intent outcome immutable chain")
check(try records.records().count == 2, "record count")
rejects("incorrect chain") {
    _ = try records.commitRecord(kind: "restart-outcome", cycle: 1, payload: [:], previous: String(repeating: "0", count: 64))
}

let overID = String(repeating: "d", count: 32)
let bounded = try NG2CycleSpool.testCreate(rootURL: root, runID: overID, owner: owner)
try bounded.reserveCheckpoint(frames: 44, metadataBytes: 32 * 1024)
rejects("frame capacity reserve") { try bounded.reserveCheckpoint(frames: 45, metadataBytes: 1) }
var invalid = rgba; invalid[3] = 0
let alpha = try NG2CycleSpool.testCreate(rootURL: root, runID: String(repeating: "e", count: 32), owner: owner)
rejects("nonopaque RGBA") { _ = try alpha.commitFrame(captureID: 1, rgba: invalid, metadata: [:]) }
rejects("wrong geometry") { _ = try NG2CycleSpool.storedPNG(rgba: Data()) }
let zero = try NG2CycleSpool.testCreate(rootURL: root, runID: String(repeating: "f", count: 32), owner: owner)
NG2CycleSpoolTestHooks.writeLimit = 0
rejects("zero-progress write") { _ = try zero.commitFrame(captureID: 1, rgba: rgba, metadata: [:]) }
NG2CycleSpoolTestHooks.writeLimit = nil
check(zero.readOnly, "zero write revokes writer")

let publicationRoot = root.appendingPathComponent("publication")
try FileManager.default.createDirectory(at: publicationRoot, withIntermediateDirectories: false,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
let publication = try NG2CycleSpool.testCreate(rootURL: publicationRoot, runID: runID, owner: owner)
check(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: publicationRoot) == [runID],
      "fresh process admission sees unpublished session")
let receipt: [String: Any] = ["export_id": String(repeating: "1", count: 32),
    "manifest_sha256": String(repeating: "2", count: 64), "archive_sha256": String(repeating: "3", count: 64)]
_ = try publication.commitRecord(kind: "published", cycle: 0, payload: receipt)
check(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: publicationRoot).isEmpty,
      "durable publication permits next session admission")
let afterPublication = try NG2CycleSpool.testRecover(rootURL: publicationRoot, runID: runID, owner: "new-owner")
let publicationRecords = try afterPublication.records()
check(afterPublication.readOnly && publicationRecords.last?.kind == "published",
      "process restart observes receipt without input resume")

let pngRoot = root.appendingPathComponent("png-ledger")
try FileManager.default.createDirectory(at: pngRoot, withIntermediateDirectories: false,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
let encodedStore = try NG2CycleSpool.testCreate(rootURL: pngRoot, runID: runID, owner: owner,
    provenance: ["clock_id": String(repeating: "4", count: 32), "generation": 1])
let originalFrame = try encodedStore.commitFrame(captureID: 17, rgba: rgba, metadata: ["prefix": 0])
let encodedRef = try encodedStore.commitPNG(captureID: 17, bytes: png, metadata: ["raw_sha256": originalFrame.rawSHA256])
check(try encodedStore.readPNG(encodedRef) == png, "encoded PNG immutable exact bytes")
check(try encodedStore.readPNG(encodedRef, offset: 0, length: 64 * 1024) == Data(png.prefix(64 * 1024)),
      "PNG bounded chunk")
let manifestBytes = try JSONSerialization.data(withJSONObject: ["export_id": String(repeating: "5", count: 32),
    "fixture": "exact manifest bytes"], options: [.sortedKeys])
let encodedManifest = try encodedStore.commitExportManifest(bytes: manifestBytes)
check(try encodedStore.readExportManifest(encodedManifest) == manifestBytes, "manifest byte exact persistence")
let originalEnvelope = try encodedStore.frameEnvelopeBytes(originalFrame)
let originalHeader = try encodedStore.sessionBytes()
check(!originalEnvelope.isEmpty && originalHeader != nil, "original header frame envelopes")
let originalRecord = try records.records()[0]
check(!((try records.recordBytes(originalRecord)).isEmpty), "record exact bytes")

let encodedRecovered = try NG2CycleSpool.testRecover(rootURL: pngRoot, runID: runID, owner: "new-owner")
let recoveredPNGs = try encodedRecovered.pngs()
check(recoveredPNGs.count == 1, "one recovered PNG")
let recoveredPNG = try encodedRecovered.readPNG(recoveredPNGs[0])
check(recoveredPNG == png,
      "process restart reads committed encoded bytes")
let recoveryLedger = try encodedRecovered.createRecoveryExport(owner: "new-owner")
let recoveryID = recoveryLedger.recoveryExportID!
_ = try recoveryLedger.commitPNG(captureID: 17, bytes: png, metadata: ["original_capture_id": 17])
check(try recoveryLedger.frames().isEmpty, "recovery PNG binds original without raw duplication")
let recoveryManifest = try JSONSerialization.data(withJSONObject: ["export_id": recoveryID, "complete": false], options: [.sortedKeys])
let recoveryManifestRef = try recoveryLedger.commitExportManifest(bytes: recoveryManifest)
let reusedLedger = try encodedRecovered.createRecoveryExport(owner: "new-owner")
check(reusedLedger.recoveryExportID == recoveryID && reusedLedger.readOnly, "frozen recovery ledger identity reused")
_ = try encodedRecovered.commitRecoveredPublication(owner: "new-owner", exportID: recoveryID,
    manifestSHA256: recoveryManifestRef.sha256, archiveSHA256: String(repeating: "6", count: 64))
check(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: pngRoot).isEmpty,
      "sibling publication receipt releases explicit next start gate")

let headerRoot = root.appendingPathComponent("header-interrupted")
let interruptedDirectory = headerRoot.appendingPathComponent("NGG2Cycles").appendingPathComponent(runID)
try FileManager.default.createDirectory(at: interruptedDirectory, withIntermediateDirectories: true,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
let interruptedPart = interruptedDirectory.appendingPathComponent(".part-" + UUID().uuidString.lowercased())
try Data("interrupted header".utf8).write(to: interruptedPart)
try FileManager.default.setAttributes([.posixPermissions: NSNumber(value: 0o600)], ofItemAtPath: interruptedPart.path)
let interrupted = try NG2CycleSpool.testRecover(rootURL: headerRoot, runID: runID, owner: "new-owner")
check(interrupted.readOnly && interrupted.diagnosticInterrupted && interrupted.originalOwnerSHA256 == nil,
      "missing header recovery cannot claim original owner or input authority")
check(try interrupted.sessionBytes() == nil, "missing header remains missing")
let interruptedArtifacts = try interrupted.artifacts()
check(interruptedArtifacts.count == 1 && !interruptedArtifacts[0].authority, "uncommitted artifact authority zero")
let interruptedLedger = try interrupted.createRecoveryExport(owner: "new-owner")
let interruptedID = interruptedLedger.recoveryExportID!
let interruptedManifest = try JSONSerialization.data(withJSONObject: ["export_id": interruptedID, "complete": false], options: [.sortedKeys])
let interruptedManifestRef = try interruptedLedger.commitExportManifest(bytes: interruptedManifest)
_ = try interrupted.commitRecoveredPublication(owner: "new-owner", exportID: interruptedID,
    manifestSHA256: interruptedManifestRef.sha256, archiveSHA256: String(repeating: "7", count: 64))
check(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: headerRoot).isEmpty,
      "header interruption diagnostic publication avoids permanent start deadlock")
try Data("changed interrupted header".utf8).write(to: interruptedPart)
check(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: headerRoot) == [runID],
      "receipt cannot authorize changed original artifact snapshot")
print("PASS cycle_spool094 real-filesystem fault boundaries and PNG; no iPhone claim")
if let destination = ProcessInfo.processInfo.environment["NG2_SPOOL_PNG_OUTPUT"] {
    try png.write(to: URL(fileURLWithPath: destination + ".png"))
    try rgba.write(to: URL(fileURLWithPath: destination + ".rgba"))
}
