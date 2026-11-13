// TEST094 actual helper/filesystem export tests; no game operations.
import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition { print("FAIL " + message); exit(1) }
}
func awaitResult(_ work: () -> ([String: JSONValue]?, String?)) -> [String: JSONValue] {
    let limit = Date().addingTimeInterval(12)
    while Date() < limit {
        let result = work()
        if let answer = result.0 { return answer }
        check(result.1 == "pending", "unexpected export failure " + (result.1 ?? "nil"))
        RunLoop.current.run(until: Date().addingTimeInterval(0.005))
    }
    print("FAIL bounded export pending"); exit(1)
}
let root = FileManager.default.temporaryDirectory.appendingPathComponent("ngg2-export-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                                      attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root) }
let id = String(repeating: "9", count: 32), owner = "export-fixture-owner"
var rgba = Data(count: 896 * 414 * 4)
rgba.withUnsafeMutableBytes { raw in
    let p = raw.bindMemory(to: UInt8.self)
    for at in stride(from: 0, to: p.count, by: 4) {
        p[at] = UInt8(truncatingIfNeeded: at / 7); p[at+1] = 33; p[at+2] = 71; p[at+3] = 255
    }
}
let spool = try NG2CycleSpool.testCreate(rootURL: root, runID: id, owner: owner)
let frame = try spool.commitFrame(captureID: 7, rgba: rgba, metadata: ["completed_prefix": 0])
let checkpoint = try spool.commitRecord(kind: "checkpoint", cycle: 1, payload: ["outcome": "unknown"])
let status: [String: JSONValue] = ["terminal": .bool(true), "workers_drained": .bool(true),
    "native_inflight": .bool(false), "input_state": .int(0), "ui_frozen": .bool(false)]
let exporter = NG2CycleExport(spool: spool, status: status, recovered: false, owner: owner)
exporter.prepare()
let manifestPayload = awaitResult { exporter.manifest() }
let text = manifestPayload["manifest_json"]!.stringValue!
let manifestData = Data(text.utf8)
let exportID = manifestPayload["export_id"]!.stringValue!
let manifestSHA = manifestPayload["manifest_sha256"]!.stringValue!
check(NG2CycleWire.hash(manifestData) == manifestSHA, "exact manifest UTF8 hash")
let manifest = try JSONSerialization.jsonObject(with: manifestData) as! [String: Any]
check(manifest["complete"] as? Bool == true && manifest["interrupted"] as? Bool == false, "complete normal export")
let imageRows = manifest["images"] as! [[String: Any]]
let recordRows = manifest["records"] as! [[String: Any]]
check(imageRows.count == 1 && recordRows.count == 3, "all images and provenance records")
check(exporter.chunk(captureID: 999, offset: 0).1 == "invalid_cycle_export_range", "unknown capture is request-local")
check(exporter.chunk(captureID: 7, offset: Int.max).1 == "invalid_cycle_export_range", "bad offset is request-local")
check(exporter.record(sequence: 999, offset: 0).1 == "invalid_cycle_export_range", "unknown record is request-local")
check(exporter.manifest().0 == manifestPayload && exporter.failure == nil, "malformed request cannot poison export")
print("PASS exact native manifest and complete provenance inventory")

var imageBytes = Data(), offset = 0
while offset < imageRows[0]["bytes"] as! Int {
    let batch = awaitResult { exporter.batch(requests: (0..<4).map { (captureID: UInt64(7), offset: offset + $0 * 65536) }) }
    guard case .array(let chunks)? = batch["chunks"] else { check(false, "batch shape"); break }
    for value in chunks {
        guard case .object(let chunk) = value else { check(false, "chunk shape"); continue }
        check(chunk["offset"]?.intValue == imageBytes.count, "ordered exact offset")
        imageBytes.append(Data(base64Encoded: chunk["data_base64"]!.stringValue!)!)
        offset = chunk["next_offset"]!.intValue!
    }
}
check(imageBytes.count == imageRows[0]["bytes"] as! Int && NG2CycleWire.hash(imageBytes) == imageRows[0]["sha256"] as! String,
      "all PNG bytes match immutable manifest")
for row in recordRows {
    let sequence = row["sequence"] as! Int
    let chunk = awaitResult { exporter.record(sequence: sequence, offset: 0) }
    let bytes = Data(base64Encoded: chunk["data_base64"]!.stringValue!)!
    check(NG2CycleWire.hash(bytes) == row["sha256"] as! String, "exact record hash")
    if sequence == 1 { check(bytes == (try spool.recordBytes(checkpoint)), "journal bytes preserved") }
    if sequence == 513 { check(bytes == (try spool.frameEnvelopeBytes(frame)), "frame envelope bytes preserved") }
}
if let output = ProcessInfo.processInfo.environment["NG2_EXPORT_OUTPUT"] {
    try imageBytes.write(to: URL(fileURLWithPath: output + ".png"))
    try rgba.write(to: URL(fileURLWithPath: output + ".rgba"))
}
print("PASS paged immutable image and exact evidence records")

check(exporter.published(exportID: String(repeating: "0", count: 32), manifestSHA: manifestSHA,
                         archiveSHA: String(repeating: "a", count: 64)).0 == nil, "wrong export publication refused")
check(try spool.records().last?.kind == "checkpoint", "no receipt from wrong identity")
let archiveSHA = String(repeating: "a", count: 64)
var receipt: [String: JSONValue] = [:]
let receiptDeadline = Date().addingTimeInterval(12)
while Date() < receiptDeadline {
    let answer = exporter.published(exportID: exportID, manifestSHA: manifestSHA, archiveSHA: archiveSHA)
    check(answer.1 == nil, "publication succeeds")
    if answer.0?["accepted"]?.boolValue == true { receipt = answer.0!; break }
    RunLoop.current.run(until: Date().addingTimeInterval(0.005))
}
check(receipt["accepted"]?.boolValue == true && exporter.published, "durable publication completed")
check(receipt["receipt_sha256"]?.stringValue == (try spool.records().last?.sha256), "receipt binds committed file")
check(try spool.exportManifestBytes() == manifestData, "receipt does not change frozen manifest")
check(exporter.published(exportID: exportID, manifestSHA: manifestSHA,
                         archiveSHA: String(repeating: "b", count: 64)).0 == nil, "conflicting ZIP refused")
print("PASS durable publication receipt, frozen bytes and conflict rejection")

let reopened = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: "changed-owner")
let replay = NG2CycleExport(spool: reopened, status: status, recovered: true, owner: "changed-owner")
replay.prepare()
let replayManifest = awaitResult { replay.manifest() }
check(replayManifest == manifestPayload, "same immutable export after process/owner change")
let replayPNG = awaitResult { replay.chunk(captureID: 7, offset: 0) }
check(replayPNG["sha256"]?.stringValue == imageRows[0]["sha256"] as? String, "recovery uses same encoded bytes")
print("PASS read-only owner-change recovery preserves manifest and encoding")

let interruptedID = String(repeating: "8", count: 32)
let unfinished = try NG2CycleSpool.testCreate(rootURL: root, runID: interruptedID, owner: owner)
_ = try unfinished.commitFrame(captureID: 19, rgba: rgba, metadata: ["completed_prefix": 0])
let interrupted = try NG2CycleSpool.testRecover(rootURL: root, runID: interruptedID, owner: owner)
let diagnostic = NG2CycleExport(spool: interrupted, status: status, recovered: true, owner: owner)
diagnostic.prepare()
let diagnosticPayload = awaitResult { diagnostic.manifest() }
let diagnosticData = Data(diagnosticPayload["manifest_json"]!.stringValue!.utf8)
let diagnosticObject = try JSONSerialization.jsonObject(with: diagnosticData) as! [String: Any]
check(diagnosticObject["complete"] as? Bool == false && diagnosticObject["interrupted"] as? Bool == true,
      "interrupted run cannot claim normal completion")
check(try interrupted.exportManifestBytes() == nil, "original evidence remains read only")
check((diagnosticObject["images"] as! [[String: Any]]).count == 1, "committed raw survives interrupted export")
print("PASS interrupted diagnostic export retains committed image without false completion")

// A corrupt frozen recovery sidecar must not be selected forever on retry.
let firstRecoveryID = diagnosticPayload["export_id"]!.stringValue!
let recoveryPNG = root.appendingPathComponent("NGG2RecoveryExports")
    .appendingPathComponent(interruptedID + "-" + firstRecoveryID)
    .appendingPathComponent(String(format: "png-%016llx.png", UInt64(19)))
var corrupt = try Data(contentsOf: recoveryPNG)
corrupt[100] ^= 1
try corrupt.write(to: recoveryPNG)
let retriedDiagnostic = NG2CycleExport(spool: interrupted, status: status, recovered: true, owner: owner)
retriedDiagnostic.prepare()
let retriedPayload = awaitResult { retriedDiagnostic.manifest() }
check(retriedPayload["export_id"]!.stringValue! != firstRecoveryID, "bad frozen ledger is never reused")
check(try Data(contentsOf: recoveryPNG) == corrupt, "old corrupt ledger is retained unchanged")
let retriedObject = try JSONSerialization.jsonObject(with: Data(retriedPayload["manifest_json"]!.stringValue!.utf8)) as! [String: Any]
check(retriedObject["complete"] as? Bool == false && (retriedObject["images"] as! [[String: Any]]).count == 1,
      "fresh diagnostic recovers original raw without claiming normal completion")
print("PASS corrupt recovery ledger is retained while fresh diagnostic recovers original image")

let repeatedRecovery = NG2CycleExport(spool: interrupted, status: status, recovered: true, owner: "changed-again")
repeatedRecovery.prepare()
check(awaitResult { repeatedRecovery.manifest() } == retriedPayload,
      "healthy diagnostic export ID and bytes survive retry after bad ledger rejection")
