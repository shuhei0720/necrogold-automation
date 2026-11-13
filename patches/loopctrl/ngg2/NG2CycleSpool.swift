// TEST094 private, immutable evidence store. This component never issues input.
import Foundation
import CryptoKit
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

#if NG2_RUNTIME_HOST_TEST
enum NG2CycleSpoolTestHooks {
    static var beforeBoundary: ((String) -> Bool)?
    static var writeLimit: Int?
}
#endif

final class NG2CycleSpool {
    static let width = 896, height = 414
    static let rasterBytes = width * height * 4
    static let maximumFrames = 44
    static let maximumRawBytes = 64 * 1024 * 1024
    static let maximumMetadataBytes = 2 * 1024 * 1024
    static let maximumExportTemporaryBytes = 2 * 1024 * 1024
    static let maximumPNGBytes = 88 * 1024 * 1024
    // 414 filter bytes + RGBA, 23 stored blocks, zlib wrapper and PNG chunks.
    static let storedPNGBytes = (width * 4 + 1) * height + 23 * 5 + 6 + 57

    enum Failure: Error {
        case invalid(String), io(String), limit(String), readOnly, collision
    }
    struct FrameRef {
        let captureID: UInt64
        let rawSHA256: String
        let bytes: Int
        let metadataSHA256: String
    }
    struct RecordRef {
        let sequence: Int
        let kind: String
        let cycle: UInt64
        let sha256: String
        let previous: String?
        let payload: [String: Any]
    }
    struct PNGRef {
        let captureID: UInt64
        let sha256: String
        let bytes: Int
        let metadataSHA256: String
        let metadata: [String: Any]
    }
    struct ArtifactRef {
        let id: String
        let name: String
        let role: String
        let bytes: Int
        let sha256: String
        var kind: String { role }
        var authority: Bool { false }
    }
    struct ManifestRef {
        let exportID: String
        let sha256: String
        let bytes: Int
    }
    let runID: String
    private let supportURL: URL
    private let rootName: String
    private let directoryName: String
    private var ownerSHA256: String
    var storedOwnerSHA256: String { ownerSHA256 }
    var originalOwnerSHA256: String? { ownerSHA256.isEmpty ? nil : ownerSHA256 }
    private(set) var diagnosticInterrupted = false
    private(set) var snapshotSHA256: String?
    private var directoryFD: Int32 = -1
    private let gate = NSLock()
    private var writable: Bool
    private var damaged = false
    private var registered: [UInt64: FrameRef] = [:]
    private var recordList: [RecordRef] = []
    private var registeredPNGs: [UInt64: PNGRef] = [:]
    private var pngBytes = 0
    private var artifactList: [ArtifactRef] = []
    private var artifactMap: [String: ArtifactRef] = [:]
    private var manifestRef: ManifestRef?
    private var metadataBytes = 0
    private var incompleteEntries = false
    var readOnly: Bool { gate.lock(); defer { gate.unlock() }; return !writable || damaged }

    private init(rootURL: URL, runID: String, owner: String, recover: Bool, verifyRasters: Bool = true,
                 rootName: String = "NGG2Cycles", directoryName: String? = nil,
                 provenance: [String: Any] = [:]) throws {
        guard Self.isHex(runID, count: 32), !owner.isEmpty, owner.utf8.count <= 4096 else {
            throw Failure.invalid("identity")
        }
        let checkedName = directoryName ?? runID
        guard rootName == "NGG2Cycles" || rootName == "NGG2RecoveryExports",
              checkedName == runID || (checkedName.hasPrefix(runID + "-")
                && checkedName.count == 65 && Self.isHex(String(checkedName.suffix(32)), count: 32)) else {
            throw Failure.invalid("directory-identity")
        }
        self.runID = runID
        supportURL = rootURL
        self.rootName = rootName
        self.directoryName = checkedName
        ownerSHA256 = Self.sha(Data(owner.utf8))
        writable = !recover
        let support = open(rootURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard support >= 0 else { throw Failure.io("support") }
        defer { close(support) }
        var supportStat = stat()
        guard fstat(support, &supportStat) == 0, Self.directory(supportStat), supportStat.st_uid == getuid() else {
            throw Failure.invalid("support")
        }
        if !recover {
            let created = mkdirat(support, rootName, 0o700)
            if created != 0 && errno != EEXIST { throw Failure.io("root-create") }
            if created == 0 && fsync(support) != 0 { throw Failure.io("support-sync") }
        }
        let root = openat(support, rootName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard root >= 0 else { throw Failure.io("root") }
        defer { close(root) }
        try Self.validateDirectory(root)
        if !recover {
            guard mkdirat(root, self.directoryName, 0o700) == 0 else {
                if errno == EEXIST { throw Failure.collision }
                throw Failure.io("session-create")
            }
            guard fsync(root) == 0 else { throw Failure.io("root-sync") }
        }
        directoryFD = openat(root, self.directoryName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directoryFD >= 0 else { throw Failure.io("session") }
        do {
            try Self.validateDirectory(directoryFD)
            if recover {
                do { try loadRegistered(verifyRasters: verifyRasters) }
                catch {
                    diagnosticInterrupted = true; incompleteEntries = true
                    registered.removeAll(); registeredPNGs.removeAll(); recordList.removeAll()
                    pngBytes = 0; metadataBytes = 0; ownerSHA256 = ""; manifestRef = nil
                    try loadInterrupted(verifyRasters: verifyRasters)
                }
                if incompleteEntries { diagnosticInterrupted = true }
                if verifyRasters { try buildSnapshot() }
            }
            else {
                let header: [String: Any] = ["schema": "ngg2-cycle-spool-v1", "run_id": runID,
                    "owner_sha256": ownerSHA256, "raster_bytes": Self.rasterBytes,
                    "maximum_frames": Self.maximumFrames, "provenance": provenance]
                let bytes = try Self.canonical(header)
                try atomic(bytes, name: "session.json")
                metadataBytes = bytes.count
            }
        } catch {
            close(directoryFD)
            directoryFD = -1
            throw error
        }
    }
    deinit { if directoryFD >= 0 { close(directoryFD) } }

    static func create(runID: String, owner: String, provenance: [String: Any] = [:]) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: applicationSupport(), runID: runID, owner: owner, recover: false, provenance: provenance)
    }
    static func recover(runID: String, owner: String) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: applicationSupport(), runID: runID, owner: owner, recover: true)
    }
    static func unpublishedRunIDs() throws -> [String] {
        try unpublished(rootURL: applicationSupport())
    }
    private static func unpublished(rootURL: URL) throws -> [String] {
        let support = open(rootURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard support >= 0 else { throw Failure.io("support") }
        defer { close(support) }
        let root = openat(support, "NGG2Cycles", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if root < 0 && errno == ENOENT { return [] }
        guard root >= 0 else { throw Failure.io("root") }
        defer { close(root) }
        try validateDirectory(root)
        let duplicate = dup(root)
        guard duplicate >= 0, let directory = fdopendir(duplicate) else {
            if duplicate >= 0 { close(duplicate) }; throw Failure.io("enumerate")
        }
        defer { closedir(directory) }
        rewinddir(directory)
        var ids: [String] = []
        while true {
            errno = 0
            guard let entry = readdir(directory) else {
                if errno != 0 { throw Failure.io("enumerate-read") }
                break
            }
            let name = withUnsafePointer(to: &entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: 256) { String(cString: $0) }
            }
            if name == "." || name == ".." { continue }
            guard isHex(name, count: 32), ids.count < 128 else { throw Failure.invalid("session-entry") }
            let descriptor = openat(root, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard descriptor >= 0 else { throw Failure.invalid("session-entry") }
            do { try validateDirectory(descriptor); close(descriptor) } catch { close(descriptor); throw error }
            ids.append(name)
        }
        var pending: [String] = []
        for id in ids.sorted() {
            let spool = try NG2CycleSpool(rootURL: rootURL, runID: id, owner: "read-only-scan", recover: true, verifyRasters: false)
            if !spool.diagnosticInterrupted && spool.recordList.last?.kind == "published" { continue }
            if try spool.hasRecoveryPublication() { continue }
            pending.append(id)
        }
        return pending
    }
    private static func applicationSupport() throws -> URL {
        guard let url = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            throw Failure.io("support-unavailable")
        }
        // This fixed, OS-provided container path is never accepted from RPC.
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: NSNumber(value: 0o700)])
        return url.resolvingSymlinksInPath()
    }
    #if NG2_RUNTIME_HOST_TEST
    static func testCreate(rootURL: URL, runID: String, owner: String, provenance: [String: Any] = [:]) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: rootURL, runID: runID, owner: owner, recover: false, provenance: provenance)
    }
    static func testRecover(rootURL: URL, runID: String, owner: String) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: rootURL, runID: runID, owner: owner, recover: true)
    }
    static func testUnpublishedRunIDs(rootURL: URL) throws -> [String] {
        try unpublished(rootURL: rootURL)
    }
    #endif

    // The single writer calls this before a checkpoint. Reserving never grants
    // input authority, and the actual writes recheck every bound and free byte.
    func reserveCheckpoint(frames: Int, metadataBytes requested: Int) throws {
        try writing {
            guard frames >= 0, frames <= Self.maximumFrames - registered.count,
                  requested >= 0, requested <= Self.maximumMetadataBytes - metadataBytes,
                  (registered.count + frames) * Self.rasterBytes <= Self.maximumRawBytes else {
                throw Failure.limit("checkpoint")
            }
            try checkSpace(raw: frames * Self.rasterBytes, metadata: requested)
        }
    }
    func commitFrame(captureID: UInt64, rgba: Data, metadata: [String: Any]) throws -> FrameRef {
        try writing {
            guard manifestRef == nil, captureID > 0, captureID < UInt64(Int64.max), registered[captureID] == nil else {
                throw Failure.collision
            }
            try Self.validateRGBA(rgba)
            guard registered.count < Self.maximumFrames,
                  (registered.count + 1) * Self.rasterBytes <= Self.maximumRawBytes else {
                throw Failure.limit("rasters")
            }
            let rawHash = Self.sha(rgba)
            let envelope: [String: Any] = ["schema": "ngg2-cycle-frame-v1", "run_id": runID,
                "capture_id": captureID, "raw_sha256": rawHash, "raw_bytes": rgba.count,
                "metadata": metadata]
            let encoded = try Self.canonical(envelope)
            guard encoded.count <= Self.maximumMetadataBytes - metadataBytes else { throw Failure.limit("metadata") }
            try checkSpace(raw: rgba.count, metadata: encoded.count)
            // Raw may survive an interrupted metadata commit. It is never in
            // the registered set until its matching metadata is durable.
            try atomic(rgba, name: frameName(captureID, suffix: "rgba"))
            try atomic(encoded, name: frameName(captureID, suffix: "json"))
            let ref = FrameRef(captureID: captureID, rawSHA256: rawHash, bytes: rgba.count,
                               metadataSHA256: Self.sha(encoded))
            registered[captureID] = ref; metadataBytes += encoded.count
            return ref
        }
    }
    func commitRecord(kind: String, cycle: UInt64, payload: [String: Any], previous: String? = nil) throws -> RecordRef {
        try writing {
            guard Self.validKind(kind), cycle < UInt64(Int64.max), recordList.count < 512,
                  recordList.last?.kind != "published", manifestRef == nil || kind == "published" else {
                throw Failure.invalid("record")
            }
            if kind == "published" && !Self.validReceipt(payload) { throw Failure.invalid("publication-receipt") }
            let prior = recordList.last?.sha256
            guard previous == nil || previous == prior else { throw Failure.invalid("record-chain") }
            let envelope: [String: Any] = ["schema": "ngg2-cycle-record-v1", "run_id": runID,
                "sequence": recordList.count + 1, "kind": kind, "cycle": cycle,
                "previous": prior as Any? ?? NSNull(), "payload": payload]
            let encoded = try Self.canonical(envelope)
            guard encoded.count <= Self.maximumMetadataBytes - metadataBytes else { throw Failure.limit("metadata") }
            try checkSpace(raw: 0, metadata: encoded.count)
            let sequence = recordList.count + 1
            if kind == "published" {
                // A failed directory sync after the receipt rename must not
                // turn a failed publication into new-session authority.
                try atomic(Data("pending".utf8), name: ".publication-pending")
            }
            try atomic(encoded, name: recordName(sequence, kind))
            if kind == "published" {
                guard unlinkat(directoryFD, ".publication-pending", 0) == 0, fsync(directoryFD) == 0 else {
                    throw Failure.io("publication-sync")
                }
            }
            let record = RecordRef(sequence: sequence, kind: kind, cycle: cycle,
                sha256: Self.sha(encoded), previous: prior,
                payload: (try JSONSerialization.jsonObject(with: encoded) as! [String: Any])["payload"] as! [String: Any])
            recordList.append(record); metadataBytes += encoded.count
            return record
        }
    }
    func frames() throws -> [FrameRef] {
        gate.lock(); defer { gate.unlock() }
        return registered.keys.sorted().compactMap { registered[$0] }
    }
    func records() throws -> [RecordRef] {
        gate.lock(); defer { gate.unlock() }; return recordList
    }
    func sessionBytes() throws -> Data? {
        gate.lock(); defer { gate.unlock() }
        var value = stat()
        if fstatat(directoryFD, "session.json", &value, AT_SYMLINK_NOFOLLOW) != 0 && errno == ENOENT { return nil }
        let bytes = try read("session.json", maximum: Self.maximumMetadataBytes)
        // Invalid header bytes remain in the diagnostic artifact inventory;
        // they must not be promoted to a certified session record.
        guard Self.validSessionHeader(bytes, runID: runID) != nil else { return nil }
        return bytes
    }
    func frameEnvelopeBytes(_ ref: FrameRef) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard registered[ref.captureID]?.metadataSHA256 == ref.metadataSHA256 else { throw Failure.invalid("frame-reference") }
        let bytes = try read(frameName(ref.captureID, suffix: "json"), maximum: Self.maximumMetadataBytes)
        guard Self.sha(bytes) == ref.metadataSHA256 else { throw Failure.invalid("frame-metadata-sha") }
        return bytes
    }
    func recordBytes(_ ref: RecordRef) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard recordList.contains(where: { $0.sequence == ref.sequence && $0.sha256 == ref.sha256 }) else {
            throw Failure.invalid("record-reference")
        }
        let bytes = try read(recordName(ref.sequence, ref.kind), maximum: Self.maximumMetadataBytes)
        guard Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("record-sha") }
        return bytes
    }
    func readRecord(sequence: Int, offset: Int, length: Int) throws -> Data {
        let rows = try records()
        guard let ref = rows.first(where: { $0.sequence == sequence }), offset >= 0,
              length > 0, length <= 64 * 1024 else { throw Failure.invalid("record-range") }
        let bytes = try recordBytes(ref)
        guard offset < bytes.count else { throw Failure.invalid("record-range") }
        return Data(bytes[offset..<min(bytes.count, offset + length)])
    }
    func commitExportManifest(exportID: String, bytes: Data) throws -> ManifestRef {
        try writing {
            guard Self.isHex(exportID, count: 32), manifestRef == nil, !bytes.isEmpty,
                  bytes.count <= Self.maximumMetadataBytes - metadataBytes,
                  (try? JSONSerialization.jsonObject(with: bytes)) is [String: Any] else {
                throw Failure.invalid("export-manifest")
            }
            try checkSpace(raw: 0, metadata: bytes.count)
            try atomic(bytes, name: "export-" + exportID + ".json")
            let ref = ManifestRef(exportID: exportID, sha256: Self.sha(bytes), bytes: bytes.count)
            manifestRef = ref; metadataBytes += bytes.count
            return ref
        }
    }
    func commitExportManifest(bytes: Data) throws -> ManifestRef {
        guard let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
              let exportID = value["export_id"] as? String else { throw Failure.invalid("export-manifest") }
        return try commitExportManifest(exportID: exportID, bytes: bytes)
    }
    func exportManifest() throws -> ManifestRef? {
        gate.lock(); defer { gate.unlock() }; return manifestRef
    }
    func readExportManifest(_ ref: ManifestRef) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard manifestRef?.exportID == ref.exportID, manifestRef?.sha256 == ref.sha256 else {
            throw Failure.invalid("manifest-reference")
        }
        let bytes = try read("export-" + ref.exportID + ".json", maximum: Self.maximumMetadataBytes)
        guard bytes.count == ref.bytes, Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("manifest-sha") }
        return bytes
    }
    func exportManifestBytes() throws -> Data? {
        guard let ref = try exportManifest() else { return nil }
        return try readExportManifest(ref)
    }
    @discardableResult
    func commitPublication(exportID: String, manifestSHA256: String, archiveSHA256: String) throws -> RecordRef {
        if let last = try records().last, last.kind == "published" {
            guard last.payload["export_id"] as? String == exportID,
                  last.payload["manifest_sha256"] as? String == manifestSHA256,
                  last.payload["archive_sha256"] as? String == archiveSHA256 else { throw Failure.invalid("publication-conflict") }
            return last
        }
        return try commitRecord(kind: "published", cycle: 0, payload: ["export_id": exportID,
            "manifest_sha256": manifestSHA256, "archive_sha256": archiveSHA256])
    }
    func frameMetadata(_ ref: FrameRef) throws -> [String: Any] {
        gate.lock(); defer { gate.unlock() }
        guard registered[ref.captureID]?.metadataSHA256 == ref.metadataSHA256 else { throw Failure.invalid("frame-reference") }
        let bytes = try read(frameName(ref.captureID, suffix: "json"), maximum: Self.maximumMetadataBytes)
        guard Self.sha(bytes) == ref.metadataSHA256,
              let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
              let metadata = value["metadata"] as? [String: Any] else { throw Failure.invalid("frame-metadata") }
        return metadata
    }
    func readRGBA(_ ref: FrameRef) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard registered[ref.captureID]?.rawSHA256 == ref.rawSHA256, ref.bytes == Self.rasterBytes else {
            throw Failure.invalid("frame-reference")
        }
        let bytes = try read(frameName(ref.captureID, suffix: "rgba"), maximum: Self.rasterBytes)
        try Self.validateRGBA(bytes)
        guard Self.sha(bytes) == ref.rawSHA256 else { throw Failure.invalid("raster-sha") }
        return bytes
    }

    func commitPNG(captureID: UInt64, bytes: Data, metadata: [String: Any]) throws -> PNGRef {
        try writing {
            guard manifestRef == nil, captureID > 0, captureID < UInt64(Int64.max), registeredPNGs[captureID] == nil,
                  registered[captureID] != nil || rootName == "NGG2RecoveryExports",
                  registeredPNGs.count < Self.maximumFrames else { throw Failure.invalid("png-identity") }
            try Self.validatePNG(bytes)
            guard bytes.count <= Self.maximumPNGBytes - pngBytes else { throw Failure.limit("png-total") }
            let digest = Self.sha(bytes)
            let value: [String: Any] = ["schema": "ngg2-cycle-png-v1", "run_id": runID,
                "capture_id": captureID, "png_sha256": digest, "png_bytes": bytes.count, "metadata": metadata]
            let encoded = try Self.canonical(value)
            guard encoded.count <= Self.maximumMetadataBytes - metadataBytes else { throw Failure.limit("metadata") }
            try checkSpace(raw: bytes.count, metadata: encoded.count)
            try atomic(bytes, name: pngName(captureID, suffix: "png"))
            try atomic(encoded, name: pngName(captureID, suffix: "json"))
            let committed = try JSONSerialization.jsonObject(with: encoded) as! [String: Any]
            let ref = PNGRef(captureID: captureID, sha256: digest, bytes: bytes.count,
                             metadataSHA256: Self.sha(encoded), metadata: committed["metadata"] as! [String: Any])
            registeredPNGs[captureID] = ref; pngBytes += bytes.count; metadataBytes += encoded.count
            return ref
        }
    }
    func pngs() throws -> [PNGRef] {
        gate.lock(); defer { gate.unlock() }
        return registeredPNGs.keys.sorted().compactMap { registeredPNGs[$0] }
    }
    func readPNG(_ ref: PNGRef, offset: Int = 0, length: Int? = nil) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard registeredPNGs[ref.captureID]?.sha256 == ref.sha256 else { throw Failure.invalid("png-reference") }
        let bytes = try read(pngName(ref.captureID, suffix: "png"), maximum: Self.maximumExportTemporaryBytes)
        try Self.validatePNG(bytes)
        guard bytes.count == ref.bytes, Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("png-sha") }
        if length == nil { return bytes }
        guard offset >= 0, offset < bytes.count, let count = length, count > 0, count <= 64 * 1024 else {
            throw Failure.invalid("png-range")
        }
        return Data(bytes[offset..<min(bytes.count, offset + count)])
    }
    func artifacts() throws -> [ArtifactRef] {
        gate.lock(); defer { gate.unlock() }
        guard !writable else { throw Failure.invalid("live-snapshot") }
        if snapshotSHA256 == nil { try buildSnapshot() }
        return artifactList
    }
    func readArtifact(id: String, offset: Int, length: Int) throws -> Data {
        gate.lock(); defer { gate.unlock() }
        guard !writable, let ref = artifactMap[id], offset >= 0, length > 0, length <= 64 * 1024,
              offset < ref.bytes || (ref.bytes == 0 && offset == 0) else { throw Failure.invalid("artifact-range") }
        let bytes = try read(ref.name, maximum: Self.maximumExportTemporaryBytes, allowEmpty: true)
        guard bytes.count == ref.bytes, Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("artifact-sha") }
        return Data(bytes[offset..<min(bytes.count, offset + length)])
    }
    // Runtime must first prove terminal + every writer/capture/main drain.
    // This one-way seal grants diagnostic read authority, never game input.
    func sealForRecovery() throws {
        gate.lock(); defer { gate.unlock() }
        writable = false; diagnosticInterrupted = true
        if snapshotSHA256 == nil { try buildSnapshot() }
    }
    // A new sibling ledger is used for every explicit recovery export. Failed
    // attempts remain untouched; they cannot strand the original session.
    func createRecoveryExport(owner: String, forceFresh: Bool = false) throws -> NG2CycleSpool {
        gate.lock(); defer { gate.unlock() }
        guard !writable else { throw Failure.invalid("live-recovery") }
        if snapshotSHA256 == nil { try buildSnapshot() }
        if !forceFresh, let existing = try matchingRecoveryExports(owner: owner).last(where: {
            !$0.diagnosticInterrupted && $0.manifestRef != nil
        }) { return existing }
        return try newRecoveryExport(owner: owner)
    }
    private func newRecoveryExport(owner: String) throws -> NG2CycleSpool {
        let exportID = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let ledger = try NG2CycleSpool(rootURL: supportURL, runID: runID, owner: owner, recover: false,
            rootName: "NGG2RecoveryExports", directoryName: runID + "-" + exportID)
        let provenance: [String: Any] = ["snapshot_sha256": snapshotSHA256!,
            "original_owner_sha256": originalOwnerSHA256 as Any? ?? NSNull(),
            "interrupted": diagnosticInterrupted, "input_authority": false,
            "artifacts": artifactList.map { Self.artifactValue($0) }]
        _ = try ledger.commitRecord(kind: "recovery_source", cycle: 0, payload: provenance)
        return ledger
    }
    func recoveryExports(owner: String) throws -> [NG2CycleSpool] {
        gate.lock(); defer { gate.unlock() }
        guard !writable else { throw Failure.invalid("live-recovery") }
        if snapshotSHA256 == nil { try buildSnapshot() }
        return try matchingRecoveryExports(owner: owner)
    }
    func recoveryReceipt(exportID: String, manifestSHA256: String, archiveSHA256: String? = nil) throws -> RecordRef? {
        gate.lock(); defer { gate.unlock() }
        guard !writable else { throw Failure.invalid("live-recovery") }
        if snapshotSHA256 == nil { try buildSnapshot() }
        for ledger in try matchingRecoveryExports(owner: "read-only-receipt") {
            if let receipt = ledger.recordList.last, receipt.kind == "published",
               receipt.payload["export_id"] as? String == exportID,
               receipt.payload["manifest_sha256"] as? String == manifestSHA256,
               archiveSHA256 == nil || receipt.payload["archive_sha256"] as? String == archiveSHA256 { return receipt }
        }
        return nil
    }
    @discardableResult
    func commitRecoveredPublication(owner: String, exportID: String, manifestSHA256: String, archiveSHA256: String) throws -> RecordRef {
        gate.lock(); defer { gate.unlock() }
        guard !writable else { throw Failure.invalid("live-recovery") }
        if snapshotSHA256 == nil { try buildSnapshot() }
        for ledger in try matchingRecoveryExports(owner: owner) {
            if let receipt = ledger.recordList.last, receipt.kind == "published",
               receipt.payload["export_id"] as? String == exportID,
               receipt.payload["manifest_sha256"] as? String == manifestSHA256 {
                guard receipt.payload["archive_sha256"] as? String == archiveSHA256 else { throw Failure.invalid("publication-conflict") }
                return receipt
            }
        }
        let ledger = try newRecoveryExport(owner: owner)
        return try ledger.commitPublication(exportID: exportID, manifestSHA256: manifestSHA256, archiveSHA256: archiveSHA256)
    }
    private func hasRecoveryPublication() throws -> Bool {
        gate.lock(); defer { gate.unlock() }
        // Check namespace existence before hashing a potentially large source.
        let path = supportURL.appendingPathComponent("NGG2RecoveryExports").path
        var value = stat()
        if lstat(path, &value) != 0 && errno == ENOENT { return false }
        if snapshotSHA256 == nil { try buildSnapshot() }
        return try matchingRecoveryExports(owner: "read-only-scan").contains(where: {
            !$0.diagnosticInterrupted && $0.recordList.last?.kind == "published"
        })
    }
    private func matchingRecoveryExports(owner: String) throws -> [NG2CycleSpool] {
        let support = open(supportURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard support >= 0 else { throw Failure.io("support") }; defer { close(support) }
        let root = openat(support, "NGG2RecoveryExports", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if root < 0 && errno == ENOENT { return [] }
        guard root >= 0 else { throw Failure.io("recovery-root") }; defer { close(root) }
        try Self.validateDirectory(root)
        let duplicate = dup(root)
        guard duplicate >= 0, let directory = fdopendir(duplicate) else {
            if duplicate >= 0 { close(duplicate) }; throw Failure.io("recovery-enumerate")
        }
        defer { closedir(directory) }; rewinddir(directory)
        var names: [String] = []
        while true {
            errno = 0
            guard let entry = readdir(directory) else {
                if errno != 0 { throw Failure.io("recovery-enumerate") }; break
            }
            let name = withUnsafePointer(to: &entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: 256) { String(cString: $0) }
            }
            if name == "." || name == ".." { continue }
            guard name.count == 65, name[name.index(name.startIndex, offsetBy: 32)] == "-",
                  Self.isHex(String(name.prefix(32)), count: 32), Self.isHex(String(name.suffix(32)), count: 32),
                  names.count < 128 else { throw Failure.invalid("recovery-entry") }
            let descriptor = openat(root, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard descriptor >= 0 else { throw Failure.invalid("recovery-entry") }
            do { try Self.validateDirectory(descriptor); close(descriptor) } catch { close(descriptor); throw error }
            names.append(name)
        }
        var ledgers: [NG2CycleSpool] = []
        for name in names.sorted() where name.hasPrefix(runID + "-") {
            let ledger = try NG2CycleSpool(rootURL: supportURL, runID: runID, owner: owner, recover: true,
                verifyRasters: true, rootName: "NGG2RecoveryExports", directoryName: name)
            if !ledger.diagnosticInterrupted,
               ledger.recordList.first?.kind == "recovery_source",
               ledger.recordList.first?.payload["snapshot_sha256"] as? String == snapshotSHA256 { ledgers.append(ledger) }
        }
        return ledgers
    }
    var recoveryExportID: String? {
        rootName == "NGG2RecoveryExports" ? String(directoryName.suffix(32)) : nil
    }

    private func writing<T>(_ body: () throws -> T) throws -> T {
        gate.lock(); defer { gate.unlock() }
        guard writable && !damaged else { throw Failure.readOnly }
        do { return try body() } catch { damaged = true; writable = false; diagnosticInterrupted = true; incompleteEntries = true; throw error }
    }
    private func checkSpace(raw: Int, metadata requested: Int) throws {
        #if canImport(Darwin)
        var value = statfs()
        guard fstatfs(directoryFD, &value) == 0 else { throw Failure.io("space") }
        let available = UInt64(value.f_bavail) * UInt64(value.f_bsize)
        #else
        var value = statvfs()
        guard fstatvfs(directoryFD, &value) == 0 else { throw Failure.io("space") }
        let available = UInt64(value.f_bavail) * UInt64(value.f_frsize)
        #endif
        let reserve = UInt64(raw + max(requested, Self.maximumMetadataBytes - metadataBytes)
                             + Self.maximumExportTemporaryBytes)
        guard available >= reserve else { throw Failure.limit("space") }
    }
    private func boundary(_ name: String) throws {
        #if NG2_RUNTIME_HOST_TEST
        if NG2CycleSpoolTestHooks.beforeBoundary?(name) == false { throw Failure.io("injected-" + name) }
        #endif
    }
    private func atomic(_ bytes: Data, name: String) throws {
        let part = ".part-" + UUID().uuidString.lowercased()
        try boundary("part_open")
        let descriptor = openat(directoryFD, part, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard descriptor >= 0 else { throw Failure.io("part-open") }
        defer { close(descriptor) }
        var value = stat()
        guard fstat(descriptor, &value) == 0, Self.regular(value), value.st_nlink == 1,
              value.st_uid == getuid(), value.st_mode & 0o077 == 0 else { throw Failure.invalid("part") }
        try bytes.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { throw Failure.invalid("empty-write") }
            var offset = 0
            while offset < raw.count {
                try boundary("write")
                var length = raw.count - offset
                #if NG2_RUNTIME_HOST_TEST
                if let limit = NG2CycleSpoolTestHooks.writeLimit { length = min(length, max(0, limit)) }
                #endif
                let written = write(descriptor, base.advanced(by: offset), length)
                if written < 0 && errno == EINTR { continue }
                guard written > 0 else { throw Failure.io("write") }
                offset += written
            }
        }
        try boundary("file_sync")
        guard fsync(descriptor) == 0 else { throw Failure.io("file-sync") }
        try boundary("rename")
        #if canImport(Darwin)
        guard renameatx_np(directoryFD, part, directoryFD, name, UInt32(RENAME_EXCL)) == 0 else {
            if errno == EEXIST { throw Failure.collision }
            throw Failure.io("rename")
        }
        #else
        // Host portability: link creates an exclusive final name, then retire
        // the part. iOS uses the atomic no-replace rename above.
        guard linkat(directoryFD, part, directoryFD, name, 0) == 0 else { throw Failure.io("rename") }
        guard unlinkat(directoryFD, part, 0) == 0 else { throw Failure.io("part-unlink") }
        #endif
        try boundary("directory_sync")
        guard fsync(directoryFD) == 0 else { throw Failure.io("directory-sync") }
    }
    private func read(_ name: String, maximum: Int, allowEmpty: Bool = false) throws -> Data {
        let descriptor = openat(directoryFD, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { throw Failure.io("read-open") }
        defer { close(descriptor) }
        var value = stat()
        guard fstat(descriptor, &value) == 0, Self.regular(value), value.st_nlink == 1,
              value.st_uid == getuid(), value.st_mode & 0o077 == 0,
              (value.st_size > 0 || (allowEmpty && value.st_size == 0)), value.st_size <= maximum else { throw Failure.invalid("read-file") }
        var bytes = Data(count: Int(value.st_size))
        try bytes.withUnsafeMutableBytes { raw in
            var offset = 0
            while offset < raw.count {
                let count = Self.readBytes(descriptor, raw.baseAddress!.advanced(by: offset), raw.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw Failure.io("read-short") }
                offset += count
            }
        }
        var tail: UInt8 = 0
        guard Self.readBytes(descriptor, &tail, 1) == 0 else { throw Failure.invalid("read-growth") }
        return bytes
    }
    private func loadRegistered(verifyRasters: Bool) throws {
        let headerBytes = try read("session.json", maximum: Self.maximumMetadataBytes)
        guard let header = try JSONSerialization.jsonObject(with: headerBytes) as? [String: Any],
              Set(header.keys) == ["schema", "run_id", "owner_sha256", "raster_bytes", "maximum_frames", "provenance"],
              header["schema"] as? String == "ngg2-cycle-spool-v1", header["run_id"] as? String == runID,
              Self.unsigned(header["raster_bytes"]) == UInt64(Self.rasterBytes),
              Self.unsigned(header["maximum_frames"]) == UInt64(Self.maximumFrames),
              header["provenance"] is [String: Any],
              let originalOwner = header["owner_sha256"] as? String, Self.isHex(originalOwner, count: 64),
              try Self.canonical(header) == headerBytes else { throw Failure.invalid("session-header") }
        // Recovery is read only. Runtime authenticates the current same-device
        // owner; the original owner digest remains evidence provenance.
        ownerSHA256 = originalOwner
        metadataBytes = headerBytes.count
        let names = try entryNames()
        for name in names.sorted() {
            var entry = stat()
            guard fstatat(directoryFD, name, &entry, AT_SYMLINK_NOFOLLOW) == 0,
                  Self.regular(entry), entry.st_uid == getuid(), entry.st_nlink == 1,
                  entry.st_mode & 0o077 == 0 else { throw Failure.invalid("directory-file") }
            if name == "session.json" { continue }
            if name.hasPrefix(".part-") || name == ".publication-pending" { incompleteEntries = true; continue }
            if name.hasSuffix(".rgba") {
                guard name.hasPrefix("frame-"), name.count == 27,
                      Self.isHex(String(name.dropFirst(6).prefix(16)), count: 16),
                      entry.st_size == Self.rasterBytes else { throw Failure.invalid("orphan-raster") }
                if !names.contains(String(name.dropLast(4)) + "json") { incompleteEntries = true }
                continue
            }
            if name.hasPrefix("png-"), name.hasSuffix(".png") {
                guard name.count == 24, Self.isHex(String(name.dropFirst(4).prefix(16)), count: 16),
                      entry.st_size > 0, entry.st_size <= Self.maximumExportTemporaryBytes else { throw Failure.invalid("png-file") }
                if !names.contains(String(name.dropLast(3)) + "json") { incompleteEntries = true }
                continue
            }
            if name.hasPrefix("frame-"), name.hasSuffix(".json") {
                let bytes = try read(name, maximum: Self.maximumMetadataBytes)
                guard let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
                      Set(value.keys) == ["schema", "run_id", "capture_id", "raw_sha256", "raw_bytes", "metadata"],
                      value["schema"] as? String == "ngg2-cycle-frame-v1", value["run_id"] as? String == runID,
                      let id = Self.unsigned(value["capture_id"]),
                      let rawHash = value["raw_sha256"] as? String, Self.isHex(rawHash, count: 64),
                      Self.unsigned(value["raw_bytes"]) == UInt64(Self.rasterBytes),
                      value["metadata"] is [String: Any], try Self.canonical(value) == bytes else { throw Failure.invalid("frame-metadata") }
                guard id > 0, id < UInt64(Int64.max), name == frameName(id, suffix: "json"),
                      names.contains(frameName(id, suffix: "rgba")),
                      registered[id] == nil, registered.count < Self.maximumFrames else { throw Failure.invalid("frame-identity") }
                if verifyRasters {
                    let raw = try read(frameName(id, suffix: "rgba"), maximum: Self.rasterBytes)
                    try Self.validateRGBA(raw)
                    guard Self.sha(raw) == rawHash else { throw Failure.invalid("raster-sha") }
                }
                registered[id] = FrameRef(captureID: id, rawSHA256: rawHash, bytes: Self.rasterBytes,
                                           metadataSHA256: Self.sha(bytes))
                metadataBytes += bytes.count
            } else if name.hasPrefix("png-"), name.hasSuffix(".json") {
                let bytes = try read(name, maximum: Self.maximumMetadataBytes)
                guard let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
                      Set(value.keys) == ["schema", "run_id", "capture_id", "png_sha256", "png_bytes", "metadata"],
                      value["schema"] as? String == "ngg2-cycle-png-v1", value["run_id"] as? String == runID,
                      let id = Self.unsigned(value["capture_id"]), id > 0, id < UInt64(Int64.max),
                      let digest = value["png_sha256"] as? String, Self.isHex(digest, count: 64),
                      let size = Self.unsigned(value["png_bytes"]), size > 0, size <= UInt64(Self.maximumExportTemporaryBytes),
                      let metadata = value["metadata"] as? [String: Any], try Self.canonical(value) == bytes,
                      name == pngName(id, suffix: "json"), names.contains(pngName(id, suffix: "png")),
                      registeredPNGs[id] == nil, registeredPNGs.count < Self.maximumFrames,
                      Int(size) <= Self.maximumPNGBytes - pngBytes else { throw Failure.invalid("png-metadata") }
                if verifyRasters {
                    let png = try read(pngName(id, suffix: "png"), maximum: Self.maximumExportTemporaryBytes)
                    try Self.validatePNG(png)
                    guard png.count == Int(size), Self.sha(png) == digest else { throw Failure.invalid("png-sha") }
                }
                registeredPNGs[id] = PNGRef(captureID: id, sha256: digest, bytes: Int(size),
                                           metadataSHA256: Self.sha(bytes), metadata: metadata)
                pngBytes += Int(size); metadataBytes += bytes.count
            } else if name.hasPrefix("export-"), name.hasSuffix(".json") {
                let id = String(name.dropFirst(7).dropLast(5))
                let bytes = try read(name, maximum: Self.maximumMetadataBytes)
                guard Self.isHex(id, count: 32), manifestRef == nil,
                      (try? JSONSerialization.jsonObject(with: bytes)) is [String: Any] else { throw Failure.invalid("export-manifest") }
                manifestRef = ManifestRef(exportID: id, sha256: Self.sha(bytes), bytes: bytes.count)
                metadataBytes += bytes.count
            } else if name.hasPrefix("record-"), name.hasSuffix(".json") {
                let bytes = try read(name, maximum: Self.maximumMetadataBytes)
                guard let value = try JSONSerialization.jsonObject(with: bytes) as? [String: Any],
                      Set(value.keys) == ["schema", "run_id", "sequence", "kind", "cycle", "previous", "payload"],
                      value["schema"] as? String == "ngg2-cycle-record-v1", value["run_id"] as? String == runID,
                      let encodedSequence = Self.unsigned(value["sequence"]), encodedSequence == UInt64(recordList.count + 1),
                      let kind = value["kind"] as? String, Self.validKind(kind),
                      let cycle = Self.unsigned(value["cycle"]), cycle < UInt64(Int64.max),
                      let payload = value["payload"] as? [String: Any],
                      (value["previous"] as? String) == recordList.last?.sha256,
                      (recordList.isEmpty ? value["previous"] is NSNull : value["previous"] is String),
                      name == recordName(Int(encodedSequence), kind), try Self.canonical(value) == bytes,
                      recordList.last?.kind != "published",
                      kind != "published" || Self.validReceipt(payload) else { throw Failure.invalid("record-chain") }
                recordList.append(RecordRef(sequence: Int(encodedSequence), kind: kind, cycle: cycle,
                    sha256: Self.sha(bytes), previous: value["previous"] as? String, payload: payload))
                metadataBytes += bytes.count
            } else { throw Failure.invalid("directory-entry") }
            guard metadataBytes <= Self.maximumMetadataBytes else { throw Failure.limit("metadata") }
        }
    }
    private func frameName(_ id: UInt64, suffix: String) -> String {
        String(format: "frame-%016llx.", id) + suffix
    }
    private func pngName(_ id: UInt64, suffix: String) -> String {
        String(format: "png-%016llx.", id) + suffix
    }
    private func recordName(_ sequence: Int, _ kind: String) -> String {
        String(format: "record-%04d-", sequence) + kind + ".json"
    }
    private static func sha(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
    private static func readBytes(_ descriptor: Int32, _ buffer: UnsafeMutableRawPointer, _ count: Int) -> Int {
        #if canImport(Darwin)
        return Darwin.read(descriptor, buffer, count)
        #else
        return Glibc.read(descriptor, buffer, count)
        #endif
    }
    private static func canonical(_ value: [String: Any]) throws -> Data {
        guard JSONSerialization.isValidJSONObject(value) else { throw Failure.invalid("json") }
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    private static func isHex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    private static func unsigned(_ value: Any?) -> UInt64? {
        guard let number = value as? NSNumber,
              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: number.objCType)),
              number.int64Value >= 0 else { return nil }
        return number.uint64Value
    }
    private static func validKind(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 32 && value.utf8.allSatisfy { (97...122).contains($0) || $0 == 45 || $0 == 95 }
    }
    private static func validReceipt(_ payload: [String: Any]) -> Bool {
        guard Set(payload.keys) == ["export_id", "manifest_sha256", "archive_sha256"],
              let exportID = payload["export_id"] as? String, isHex(exportID, count: 32),
              let manifest = payload["manifest_sha256"] as? String, isHex(manifest, count: 64),
              let archive = payload["archive_sha256"] as? String, isHex(archive, count: 64) else { return false }
        return true
    }
    private static func validSessionHeader(_ bytes: Data, runID: String) -> [String: Any]? {
        guard let value = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: Any],
              Set(value.keys) == ["schema", "run_id", "owner_sha256", "raster_bytes", "maximum_frames", "provenance"],
              value["schema"] as? String == "ngg2-cycle-spool-v1", value["run_id"] as? String == runID,
              let owner = value["owner_sha256"] as? String, isHex(owner, count: 64),
              unsigned(value["raster_bytes"]) == UInt64(rasterBytes),
              unsigned(value["maximum_frames"]) == UInt64(maximumFrames),
              value["provenance"] is [String: Any], (try? canonical(value)) == bytes else { return nil }
        return value
    }
    private static func regular(_ value: stat) -> Bool { value.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG) }
    private static func directory(_ value: stat) -> Bool { value.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR) }
    private static func validateDirectory(_ descriptor: Int32) throws {
        var value = stat()
        guard fstat(descriptor, &value) == 0, directory(value), value.st_uid == getuid(),
              value.st_mode & 0o077 == 0 else { throw Failure.invalid("directory") }
    }
    private static func validateRGBA(_ rgba: Data) throws {
        guard rgba.count == rasterBytes else { throw Failure.invalid("raster-size") }
        let opaque = rgba.withUnsafeBytes { raw -> Bool in
            let bytes = raw.bindMemory(to: UInt8.self)
            for index in stride(from: 3, to: bytes.count, by: 4) { if bytes[index] != 255 { return false } }
            return true
        }
        guard opaque else { throw Failure.invalid("raster-alpha") }
    }
    private static func validatePNG(_ png: Data) throws {
        guard png.count >= 45, png.count <= maximumExportTemporaryBytes,
              Array(png.prefix(8)) == [137, 80, 78, 71, 13, 10, 26, 10] else { throw Failure.invalid("png-header") }
        let valid = png.withUnsafeBytes { raw -> Bool in
            let p = raw.bindMemory(to: UInt8.self)
            func u32(_ i: Int) -> UInt32 {
                UInt32(p[i]) << 24 | UInt32(p[i+1]) << 16 | UInt32(p[i+2]) << 8 | UInt32(p[i+3])
            }
            return u32(8) == 13 && p[12] == 73 && p[13] == 72 && p[14] == 68 && p[15] == 82
                && u32(16) == UInt32(width) && u32(20) == UInt32(height) && p[24] == 8
                && (p[25] == 2 || p[25] == 6) && p[26] == 0 && p[27] == 0 && p[28] == 0
        }
        guard valid else { throw Failure.invalid("png-geometry") }
    }

    private func entryNames() throws -> [String] {
        let duplicate = dup(directoryFD)
        guard duplicate >= 0, let directory = fdopendir(duplicate) else {
            if duplicate >= 0 { close(duplicate) }; throw Failure.io("enumerate")
        }
        defer { closedir(directory) }; rewinddir(directory)
        var names: [String] = []
        while true {
            errno = 0
            guard let entry = readdir(directory) else {
                if errno != 0 { throw Failure.io("enumerate-read") }; break
            }
            let name = withUnsafePointer(to: &entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: 256) { String(cString: $0) }
            }
            if name != "." && name != ".." { names.append(name) }
            guard names.count <= 1024 else { throw Failure.limit("directory-entries") }
        }
        return names.sorted()
    }
    private static func validArtifactName(_ name: String) -> Bool {
        if name == "session.json" || name == ".publication-pending" { return true }
        if name.hasPrefix(".part-") {
            let token = String(name.dropFirst(6))
            return token.count == 36 && token == token.lowercased() && UUID(uuidString: token) != nil
        }
        if name.hasPrefix("frame-") {
            return ["json", "rgba"].contains(String(name.suffix(4))) && name.count == 27
                && name[name.index(name.startIndex, offsetBy: 22)] == "."
                && isHex(String(name.dropFirst(6).prefix(16)), count: 16)
        }
        if name.hasPrefix("png-") {
            let suffix = name.hasSuffix(".png") ? 4 : (name.hasSuffix(".json") ? 5 : 0)
            return suffix > 0 && name.count == 20 + suffix && isHex(String(name.dropFirst(4).prefix(16)), count: 16)
        }
        if name.hasPrefix("export-") {
            return name.count == 44 && name.hasSuffix(".json") && isHex(String(name.dropFirst(7).prefix(32)), count: 32)
        }
        if name.hasPrefix("record-"), name.hasSuffix(".json"), name.count >= 18 {
            let body = String(name.dropFirst(7).dropLast(5))
            let fields = body.split(separator: "-", maxSplits: 1)
            return fields.count == 2 && fields[0].count == 4 && Int(fields[0]) != nil && validKind(String(fields[1]))
        }
        return false
    }
    private func artifactEntries(hashes: Bool) throws -> [ArtifactRef] {
        var result: [ArtifactRef] = []
        var rawTotal = 0, pngTotal = 0, metadataTotal = 0, pendingTotal = 0
        for name in try entryNames() {
            var value = stat()
            guard Self.validArtifactName(name), fstatat(directoryFD, name, &value, AT_SYMLINK_NOFOLLOW) == 0,
                  Self.regular(value), value.st_uid == getuid(), value.st_nlink == 1,
                  value.st_mode & 0o077 == 0, value.st_size >= 0,
                  value.st_size <= Self.maximumExportTemporaryBytes else { throw Failure.invalid("diagnostic-artifact") }
            let count = Int(value.st_size)
            let role: String
            if name.hasSuffix(".rgba") { rawTotal += count; role = "raw" }
            else if name.hasSuffix(".png") { pngTotal += count; role = "png" }
            else if name.hasPrefix(".part-") || name == ".publication-pending" { pendingTotal += count; role = "uncommitted" }
            else { metadataTotal += count; role = "metadata" }
            guard rawTotal <= Self.maximumRawBytes, pngTotal <= Self.maximumPNGBytes,
                  metadataTotal <= Self.maximumMetadataBytes, pendingTotal <= Self.maximumExportTemporaryBytes else {
                throw Failure.limit("diagnostic-total")
            }
            let digest: String
            if hashes { digest = Self.sha(try read(name, maximum: Self.maximumExportTemporaryBytes, allowEmpty: true)) }
            else { digest = "" }
            result.append(ArtifactRef(id: Self.sha(Data(name.utf8)), name: name, role: role, bytes: count, sha256: digest))
        }
        return result
    }
    private static func artifactValue(_ ref: ArtifactRef) -> [String: Any] {
        ["id": ref.id, "name": ref.name, "kind": ref.kind, "byte_length": ref.bytes,
         "sha256": ref.sha256, "input_authority": false]
    }
    private func buildSnapshot() throws {
        artifactList = try artifactEntries(hashes: true)
        artifactMap = Dictionary(uniqueKeysWithValues: artifactList.map { ($0.id, $0) })
        let value: [String: Any] = ["run_id": runID, "original_owner_sha256": originalOwnerSHA256 as Any? ?? NSNull(),
                                  "artifacts": artifactList.map { Self.artifactValue($0) }]
        snapshotSHA256 = Self.sha(try Self.canonical(value))
    }
    private func loadInterrupted(verifyRasters: Bool) throws {
        let entries = try artifactEntries(hashes: false)
        let names = Set(entries.map { $0.name })
        if names.contains("session.json"), let bytes = try? read("session.json", maximum: Self.maximumMetadataBytes),
           let header = Self.validSessionHeader(bytes, runID: runID),
           let owner = header["owner_sha256"] as? String {
            ownerSHA256 = owner
        }
        for name in names.sorted() where name.hasPrefix("frame-") && name.hasSuffix(".json") {
            guard let bytes = try? read(name, maximum: Self.maximumMetadataBytes),
                  let value = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: Any],
                  Set(value.keys) == ["schema", "run_id", "capture_id", "raw_sha256", "raw_bytes", "metadata"],
                  value["schema"] as? String == "ngg2-cycle-frame-v1", value["run_id"] as? String == runID,
                  let id = Self.unsigned(value["capture_id"]), id > 0, id < UInt64(Int64.max),
                  let digest = value["raw_sha256"] as? String, Self.isHex(digest, count: 64),
                  Self.unsigned(value["raw_bytes"]) == UInt64(Self.rasterBytes), (try? Self.canonical(value)) == bytes,
                  value["metadata"] is [String: Any],
                  name == frameName(id, suffix: "json"), names.contains(frameName(id, suffix: "rgba")),
                  registered.count < Self.maximumFrames else { continue }
            if verifyRasters {
                guard let raw = try? read(frameName(id, suffix: "rgba"), maximum: Self.rasterBytes),
                      (try? Self.validateRGBA(raw)) != nil, Self.sha(raw) == digest else { continue }
            }
            registered[id] = FrameRef(captureID: id, rawSHA256: digest, bytes: Self.rasterBytes,
                                       metadataSHA256: Self.sha(bytes))
        }
        for name in names.sorted() where name.hasPrefix("record-") && name.hasSuffix(".json") {
            guard let bytes = try? read(name, maximum: Self.maximumMetadataBytes),
                  let value = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: Any],
                  Set(value.keys) == ["schema", "run_id", "sequence", "kind", "cycle", "previous", "payload"],
                  value["schema"] as? String == "ngg2-cycle-record-v1", value["run_id"] as? String == runID,
                  let sequence = Self.unsigned(value["sequence"]), sequence == UInt64(recordList.count + 1),
                  let kind = value["kind"] as? String, Self.validKind(kind),
                  let cycle = Self.unsigned(value["cycle"]), cycle < UInt64(Int64.max),
                  let payload = value["payload"] as? [String: Any],
                  (value["previous"] as? String) == recordList.last?.sha256,
                  (recordList.isEmpty ? value["previous"] is NSNull : value["previous"] is String),
                  name == recordName(Int(sequence), kind), (try? Self.canonical(value)) == bytes else { break }
            recordList.append(RecordRef(sequence: Int(sequence), kind: kind, cycle: cycle,
                sha256: Self.sha(bytes), previous: value["previous"] as? String, payload: payload))
        }
        if verifyRasters { try buildSnapshot() }
    }

    static func storedPNG(rgba: Data) throws -> Data {
        try validateRGBA(rgba)
        var png = Data([137, 80, 78, 71, 13, 10, 26, 10])
        png.reserveCapacity(storedPNGBytes)
        var header = Data(); append32(UInt32(width), to: &header); append32(UInt32(height), to: &header)
        header.append(contentsOf: [8, 6, 0, 0, 0])
        chunk("IHDR", payload: header, to: &png)
        let filteredBytes = (width * 4 + 1) * height
        let blockCount = (filteredBytes + 65_534) / 65_535
        append32(UInt32(filteredBytes + blockCount * 5 + 6), to: &png)
        let checksumStart = png.count
        png.append(contentsOf: [73, 68, 65, 84, 0x78, 0x01])
        var offset = 0
        var a: UInt32 = 1, b: UInt32 = 0
        // Stream directly into the one PNG allocation. No second filtered or
        // DEFLATE raster is retained beside the immutable caller-owned RGBA.
        rgba.withUnsafeBytes { raw in
            let pixels = raw.bindMemory(to: UInt8.self)
            while offset < filteredBytes {
                let length = min(65_535, filteredBytes - offset)
                png.append(offset + length == filteredBytes ? 1 : 0)
                png.append(UInt8(truncatingIfNeeded: length))
                png.append(UInt8(truncatingIfNeeded: length >> 8))
                png.append(UInt8(truncatingIfNeeded: ~length))
                png.append(UInt8(truncatingIfNeeded: (~length) >> 8))
                var remaining = length
                while remaining > 0 {
                    let position = offset % (width * 4 + 1)
                    if position == 0 {
                        png.append(0); b += a
                        if b >= 65_521 { b -= 65_521 }
                        offset += 1; remaining -= 1
                    } else {
                        let count = min(remaining, width * 4 + 1 - position)
                        let start = (offset / (width * 4 + 1)) * width * 4 + position - 1
                        png.append(pixels.baseAddress!.advanced(by: start), count: count)
                        // A run is at most3584 bytes, below Adler's5552-byte
                        // uint32 overflow bound. Reduce once per bounded run.
                        for index in start..<(start + count) {
                            a += UInt32(pixels[index]); b += a
                        }
                        a %= 65_521; b %= 65_521
                        offset += count; remaining -= count
                    }
                }
            }
        }
        append32((b << 16) | a, to: &png)
        let checksumEnd = png.count
        let checksum = crc32(png, start: checksumStart, end: checksumEnd)
        append32(checksum, to: &png)
        chunk("IEND", payload: Data(), to: &png)
        guard png.count == storedPNGBytes, png.count <= maximumExportTemporaryBytes else {
            throw Failure.limit("stored-png")
        }
        return png
    }
    private static func append32(_ value: UInt32, to bytes: inout Data) {
        bytes.append(contentsOf: [UInt8(truncatingIfNeeded: value >> 24), UInt8(truncatingIfNeeded: value >> 16),
                                  UInt8(truncatingIfNeeded: value >> 8), UInt8(truncatingIfNeeded: value)])
    }
    private static func chunk(_ name: String, payload: Data, to png: inout Data) {
        append32(UInt32(payload.count), to: &png)
        let start = png.count
        let type = Data(name.utf8); png.append(type); png.append(payload)
        let checksum = crc32(png, start: start, end: png.count)
        append32(checksum, to: &png)
    }
    private static func crc32(_ bytes: Data, start: Int, end: Int) -> UInt32 {
        var crc: UInt32 = 0xffff_ffff
        bytes.withUnsafeBytes { raw in
            let buffer = raw.bindMemory(to: UInt8.self)
            for index in start..<end {
                crc = (crc >> 8) ^ crcTable[Int((crc ^ UInt32(buffer[index])) & 255)]
            }
        }
        return crc ^ 0xffff_ffff
    }
    private static let crcTable: [UInt32] = (0..<256).map { value in
        var crc = UInt32(value)
        for _ in 0..<8 { crc = (crc >> 1) ^ ((crc & 1) == 1 ? 0xedb8_8320 : 0) }
        return crc
    }
}
