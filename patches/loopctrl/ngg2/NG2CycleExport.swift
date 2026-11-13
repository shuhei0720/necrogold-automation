// TEST094 immutable terminal export. This object never grants game input.
import Foundation

final class NG2CycleExport {
    private struct Image {
        let source: NG2CycleSpool
        let ref: NG2CycleSpool.PNGRef
        let rawSHA: String
    }
    private struct Record {
        let sequence: Int
        let kind: String
        let cycle: UInt64
        let bytes: Data
        var sha: String { NG2CycleWire.hash(bytes) }
    }
    private let spool: NG2CycleSpool
    private let terminalStatus: [String: JSONValue]
    private let recovered: Bool
    private let owner: String
    private let queue = DispatchQueue(label: "top.ebato.loopctrl.ngg2.cycle-export", qos: .utility)
    private let gate = NSLock()
    private var started = false
    private var working = false
    private var errorCode: String?
    private var manifestData: Data?
    private var manifestHash = ""
    private var exportID = ""
    private var images: [UInt64: Image] = [:]
    private var records: [Int: Record] = [:]
    private var publicationStore: NG2CycleSpool?
    private var requestKey: String?
    private var requestResponse: [String: JSONValue]?
    private var publicationIdentity: String?
    private var publicationResponse: [String: JSONValue]?
    private var didPublish = false

    init(spool: NG2CycleSpool, status: [String: JSONValue], recovered: Bool, owner: String) {
        self.spool = spool; terminalStatus = status; self.recovered = recovered; self.owner = owner
    }
    var identifier: String? { gate.lock(); defer { gate.unlock() }; return manifestData == nil ? nil : exportID }
    var busy: Bool { gate.lock(); defer { gate.unlock() }; return working }
    var published: Bool { gate.lock(); defer { gate.unlock() }; return didPublish }
    var failure: String? { gate.lock(); defer { gate.unlock() }; return errorCode }

    func prepare() {
        gate.lock()
        guard !started else { gate.unlock(); return }
        started = true; working = true; gate.unlock()
        queue.async {
            do { try self.build() }
            catch {
                do { try self.build(forceDiagnostic: true) }
                catch { self.fail("cycle_export_integrity_or_storage") }
            }
            self.gate.lock(); self.working = false; self.gate.unlock()
        }
    }
    private func fail(_ reason: String) {
        gate.lock(); errorCode = reason; requestResponse = nil; gate.unlock()
    }
    private static func canonical(_ object: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    private func build(forceDiagnostic: Bool = false) throws {
        let status = try NG2CycleWire.object(terminalStatus)
        guard (status["terminal"] as? NSNumber)?.intValue == 1,
              (status["workers_drained"] as? Bool) == true,
              (status["native_inflight"] as? Bool) == false else {
            throw NG2CycleSpool.Failure.invalid("export-not-drained")
        }
        if forceDiagnostic { try spool.sealForRecovery() }
        let originalManifest = try spool.exportManifest()
        let recoveredExport = forceDiagnostic || (recovered && originalManifest == nil)
        let destination = recoveredExport ? try spool.createRecoveryExport(owner: owner, forceFresh: forceDiagnostic) : spool
        var imageMap: [UInt64: Image] = [:], recordMap: [Int: Record] = [:]
        var diagnostics: [[String: Any]] = []
        if forceDiagnostic { diagnostics.append(["code": "original_export_integrity_or_storage", "authority": false]) }
        if let header = try spool.sessionBytes() {
            recordMap[0] = Record(sequence: 0, kind: "session", cycle: 0, bytes: header)
        } else {
            diagnostics.append(["code": "session_header_uncommitted", "authority": false])
        }
        for ref in try spool.records() where ref.kind != "published" {
            recordMap[ref.sequence] = Record(sequence: ref.sequence, kind: ref.kind,
                cycle: ref.cycle, bytes: try spool.recordBytes(ref))
        }
        let rawFrames = try spool.frames()
        var existing = Dictionary(uniqueKeysWithValues: try destination.pngs().map { ($0.captureID, $0) })
        let frozen = try destination.exportManifest()
        for (index, ref) in rawFrames.enumerated() {
            do {
                let metadata = try spool.frameEnvelopeBytes(ref)
                recordMap[513 + index] = Record(sequence: 513 + index, kind: "frame", cycle: 0, bytes: metadata)
                let png: NG2CycleSpool.PNGRef
                if let saved = existing[ref.captureID] {
                    _ = try destination.readPNG(saved)
                    guard saved.metadata["raw_sha256"] as? String == ref.rawSHA256 else {
                        throw NG2CycleSpool.Failure.invalid("png-raw-binding")
                    }
                    png = saved
                } else {
                    guard frozen == nil else { throw NG2CycleSpool.Failure.invalid("frozen-png-missing") }
                    let rgba = try spool.readRGBA(ref)
                    let encoded: Data
                    let encoding: String
                    if !recoveredExport, let normal = NG2Raster.png(rgba), normal.count <= 2 * 1024 * 1024 {
                        encoded = normal; encoding = "imageio-png-immutable-v1"
                    } else {
                        encoded = try NG2CycleSpool.storedPNG(rgba: rgba); encoding = "stored-rgba-png-v1"
                    }
                    png = try destination.commitPNG(captureID: ref.captureID, bytes: encoded,
                        metadata: ["raw_sha256": ref.rawSHA256, "encoding": encoding])
                    existing[ref.captureID] = png
                }
                imageMap[ref.captureID] = Image(source: destination, ref: png, rawSHA: ref.rawSHA256)
            } catch {
                // A frozen manifest is never silently rewritten to omit a file.
                if frozen != nil || !(recovered || forceDiagnostic) { throw error }
                diagnostics.append(["code": "registered_frame_unrecoverable", "capture_id": ref.captureID,
                                    "authority": false])
            }
        }
        if spool.diagnosticInterrupted {
            let artifacts = try spool.artifacts()
            let rows: [[String: Any]] = artifacts.map { artifact in
                ["id": artifact.id, "name": artifact.name, "kind": artifact.kind,
                 "bytes": artifact.bytes, "sha256": artifact.sha256, "authority": false]
            }
            let inventory = try Self.canonical(["schema": "ngg2-cycle-artifacts-v1", "run_id": spool.runID,
                                                "artifacts": rows])
            guard inventory.count <= 2 * 1024 * 1024 else { throw NG2CycleSpool.Failure.limit("artifact-inventory") }
            recordMap[557] = Record(sequence: 557, kind: "artifacts", cycle: 0, bytes: inventory)
            diagnostics.append(["code": "interrupted_artifacts", "count": rows.count, "authority": false])
        }
        let data: Data
        let identity: String
        if let prior = frozen {
            data = try destination.readExportManifest(prior); identity = prior.exportID
            try verifyManifest(data, images: imageMap, records: recordMap)
        } else {
            identity = destination.recoveryExportID ?? UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
            let imageRows: [[String: Any]] = imageMap.keys.sorted().map { id in
                let image = imageMap[id]!
                return ["name": String(format: "capture-%06llu.png", id), "capture_id": id,
                    "bytes": image.ref.bytes, "sha256": image.ref.sha256, "raw_sha256": image.rawSHA,
                    "width": 896, "height": 414]
            }
            let recordRows: [[String: Any]] = recordMap.keys.sorted().map { sequence in
                let record = recordMap[sequence]!
                return ["sequence": sequence, "kind": record.kind, "cycle": record.cycle,
                        "bytes": record.bytes.count, "sha256": record.sha]
            }
            let interrupted = recoveredExport || spool.diagnosticInterrupted
            let total = imageRows.reduce(0) { $0 + ($1["bytes"] as! Int) }
                + recordRows.reduce(0) { $0 + ($1["bytes"] as! Int) }
            let object: [String: Any] = ["schema": "ngg2-cycle-manifest-v1", "run_id": spool.runID,
                "profile": NG2CycleWire.profile, "export_id": identity,
                "complete": !interrupted && diagnostics.isEmpty && imageMap.count == rawFrames.count,
                "interrupted": interrupted, "terminal": true, "workers_drained": true,
                "input_state": status["input_state"] ?? 0, "native_inflight": false,
                "ui_frozen": status["ui_frozen"] ?? true,
                "images": imageRows, "records": recordRows, "diagnostics": diagnostics,
                "total_bytes": total, "chunk_bytes": NG2CycleWire.chunkBytes]
            data = try Self.canonical(object)
            // Manifest is deliberately compact: large evidence JSON is paged.
            guard data.count <= 300 * 1024 else { throw NG2CycleSpool.Failure.limit("manifest-wire") }
            _ = try destination.commitExportManifest(exportID: identity, bytes: data)
        }
        let finalHash = NG2CycleWire.hash(data)
        let wire = try NG2CycleWire.decode(["export_id": identity, "manifest_sha256": finalHash,
                                           "manifest_json": String(decoding: data, as: UTF8.self)])
        guard try NG2CycleWire.canonical(wire).count <= 500 * 1024 else {
            throw NG2CycleSpool.Failure.limit("manifest-wire")
        }
        gate.lock()
        manifestData = data; manifestHash = finalHash; exportID = identity
        images = imageMap; records = recordMap; publicationStore = destination
        gate.unlock()
    }
    private func verifyManifest(_ data: Data, images: [UInt64: Image], records: [Int: Record]) throws {
        guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              value["schema"] as? String == "ngg2-cycle-manifest-v1",
              value["run_id"] as? String == spool.runID, value["profile"] as? String == NG2CycleWire.profile,
              let listedImages = value["images"] as? [[String: Any]],
              let listedRecords = value["records"] as? [[String: Any]],
              listedImages.count == images.count else { throw NG2CycleSpool.Failure.invalid("manifest-identity") }
        var imageIDs = Set<UInt64>(), recordIDs = Set<Int>()
        for row in listedImages {
            guard let id = (row["capture_id"] as? NSNumber)?.uint64Value, imageIDs.insert(id).inserted,
                  let image = images[id], row["sha256"] as? String == image.ref.sha256,
                  row["raw_sha256"] as? String == image.rawSHA,
                  (row["bytes"] as? NSNumber)?.intValue == image.ref.bytes else {
                throw NG2CycleSpool.Failure.invalid("manifest-image")
            }
        }
        for row in listedRecords {
            guard let sequence = (row["sequence"] as? NSNumber)?.intValue, recordIDs.insert(sequence).inserted,
                  let record = records[sequence], row["sha256"] as? String == record.sha,
                  (row["bytes"] as? NSNumber)?.intValue == record.bytes.count,
                  row["kind"] as? String == record.kind else { throw NG2CycleSpool.Failure.invalid("manifest-record") }
        }
        guard recordIDs == Set(records.keys) else { throw NG2CycleSpool.Failure.invalid("manifest-record-set") }
    }
    func manifest() -> ([String: JSONValue]?, String?) {
        gate.lock(); defer { gate.unlock() }
        if let errorCode { return (nil, errorCode) }
        guard let data = manifestData, let text = String(data: data, encoding: .utf8) else { return (nil, "pending") }
        return (["export_id": .string(exportID), "manifest_sha256": .string(manifestHash),
                 "manifest_json": .string(text)], nil)
    }
    private func request(_ key: String, work: @escaping () throws -> [String: JSONValue]) -> ([String: JSONValue]?, String?) {
        gate.lock()
        if let errorCode { gate.unlock(); return (nil, errorCode) }
        guard manifestData != nil else { gate.unlock(); return (nil, "pending") }
        if key == requestKey, let answer = requestResponse { gate.unlock(); return (answer, nil) }
        guard !working else { gate.unlock(); return (nil, "pending") }
        requestKey = key; requestResponse = nil; working = true; gate.unlock()
        queue.async {
            do {
                let answer = try work()
                let bytes = try NG2CycleWire.canonical(answer)
                guard bytes.count <= 500 * 1024 else { throw NG2CycleSpool.Failure.limit("response-wire") }
                self.gate.lock(); self.requestResponse = answer; self.gate.unlock()
            } catch { self.fail("cycle_export_read_integrity") }
            self.gate.lock(); self.working = false; self.gate.unlock()
        }
        return (nil, "pending")
    }
    private func preflight(_ valid: () -> Bool) -> String? {
        gate.lock(); defer { gate.unlock() }
        if let errorCode { return errorCode }
        guard manifestData != nil else { return "pending" }
        return valid() ? nil : "invalid_cycle_export_range"
    }
    private func imageChunk(_ captureID: UInt64, offset: Int) throws -> [String: JSONValue] {
        guard let image = images[captureID], offset >= 0, offset < image.ref.bytes,
              offset % NG2CycleWire.chunkBytes == 0 else { throw NG2CycleSpool.Failure.invalid("chunk-range") }
        let bytes = try image.source.readPNG(image.ref, offset: offset, length: NG2CycleWire.chunkBytes)
        return ["export_id": .string(exportID), "capture_id": .int(Int(captureID)), "offset": .int(offset),
            "total_bytes": .int(image.ref.bytes), "sha256": .string(image.ref.sha256),
            "data_base64": .string(bytes.base64EncodedString()), "next_offset": .int(offset + bytes.count),
            "eof": .bool(offset + bytes.count == image.ref.bytes)]
    }
    func chunk(captureID: UInt64, offset: Int) -> ([String: JSONValue]?, String?) {
        if let reason = preflight({
            guard let image = images[captureID] else { return false }
            return offset >= 0 && offset < image.ref.bytes && offset % NG2CycleWire.chunkBytes == 0
        }) { return (nil, reason) }
        return request("i:\(captureID):\(offset)") { try self.imageChunk(captureID, offset: offset) }
    }
    func batch(requests: [(captureID: UInt64, offset: Int)]) -> ([String: JSONValue]?, String?) {
        guard (1...4).contains(requests.count) else { return (nil, "invalid_cycle_batch") }
        if let reason = preflight({
            let first = requests[0]
            guard let image = images[first.captureID], first.offset >= 0,
                  first.offset < image.ref.bytes, first.offset % NG2CycleWire.chunkBytes == 0 else { return false }
            return requests.enumerated().allSatisfy { index, row in
                row.captureID == first.captureID && row.offset >= first.offset
                    && row.offset - first.offset == index * NG2CycleWire.chunkBytes
            }
        }) { return (nil, reason) }
        let key = "b:" + requests.map { "\($0.captureID):\($0.offset)" }.joined(separator: ",")
        return request(key) {
            var chunks: [JSONValue] = []
            for row in requests {
                // A bounded request may extend beyond EOF; omit only that tail.
                if let image = self.images[row.captureID], row.offset >= image.ref.bytes { break }
                chunks.append(.object(try self.imageChunk(row.captureID, offset: row.offset)))
            }
            guard !chunks.isEmpty else { throw NG2CycleSpool.Failure.invalid("batch-empty") }
            return ["export_id": .string(self.exportID), "chunks": .array(chunks)]
        }
    }
    func record(sequence: Int, offset: Int) -> ([String: JSONValue]?, String?) {
        if let reason = preflight({
            guard let record = records[sequence] else { return false }
            return offset >= 0 && offset < record.bytes.count && offset % NG2CycleWire.chunkBytes == 0
        }) { return (nil, reason) }
        return request("r:\(sequence):\(offset)") {
            guard let record = self.records[sequence], offset >= 0, offset < record.bytes.count,
                  offset % NG2CycleWire.chunkBytes == 0 else { throw NG2CycleSpool.Failure.invalid("record-range") }
            let bytes = Data(record.bytes[offset..<min(record.bytes.count, offset + NG2CycleWire.chunkBytes)])
            return ["export_id": .string(self.exportID), "sequence": .int(sequence), "offset": .int(offset),
                "total_bytes": .int(record.bytes.count), "sha256": .string(record.sha),
                "data_base64": .string(bytes.base64EncodedString()), "next_offset": .int(offset + bytes.count),
                "eof": .bool(offset + bytes.count == record.bytes.count)]
        }
    }
    func published(exportID identity: String, manifestSHA: String, archiveSHA: String) -> ([String: JSONValue]?, String?) {
        gate.lock()
        if let errorCode { gate.unlock(); return (nil, errorCode) }
        guard manifestData != nil else { gate.unlock(); return (nil, "pending") }
        guard identity == exportID, manifestSHA == manifestHash, Self.isSHA(archiveSHA) else {
            gate.unlock(); return (nil, "invalid_cycle_publication")
        }
        let publicationKey = identity + ":" + manifestSHA + ":" + archiveSHA
        if let prior = publicationIdentity, prior != publicationKey {
            gate.unlock(); return (nil, "conflicting_cycle_publication")
        }
        if let response = publicationResponse { gate.unlock(); return (response, nil) }
        let pending: [String: JSONValue] = ["accepted": .bool(false), "export_id": .string(identity),
            "manifest_sha256": .string(manifestSHA), "archive_sha256": .string(archiveSHA), "receipt_sha256": .null]
        guard !working else { gate.unlock(); return (pending, nil) }
        publicationIdentity = publicationKey; working = true
        let store = publicationStore; gate.unlock()
        queue.async {
            do {
                guard let store else { throw NG2CycleSpool.Failure.invalid("publication-store") }
                let receipt: NG2CycleSpool.RecordRef
                if let prior = try store.records().last(where: { $0.kind == "published" }) {
                    guard prior.payload["export_id"] as? String == identity,
                          prior.payload["manifest_sha256"] as? String == manifestSHA,
                          prior.payload["archive_sha256"] as? String == archiveSHA else {
                        throw NG2CycleSpool.Failure.invalid("publication-conflict")
                    }
                    receipt = prior
                } else if store.readOnly {
                    receipt = try self.spool.commitRecoveredPublication(owner: self.owner, exportID: identity,
                        manifestSHA256: manifestSHA, archiveSHA256: archiveSHA)
                } else {
                    receipt = try store.commitPublication(exportID: identity, manifestSHA256: manifestSHA, archiveSHA256: archiveSHA)
                }
                let response: [String: JSONValue] = ["accepted": .bool(true), "export_id": .string(identity),
                    "manifest_sha256": .string(manifestSHA), "archive_sha256": .string(archiveSHA),
                    "receipt_sha256": .string(receipt.sha256)]
                self.gate.lock(); self.publicationResponse = response; self.didPublish = true; self.gate.unlock()
            } catch { self.fail("cycle_publication_storage_or_identity") }
            self.gate.lock(); self.working = false; self.gate.unlock()
        }
        return (pending, nil)
    }
    private static func isSHA(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
}
