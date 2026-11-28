// Appended to the unchanged TEST116 fixture helpers by check_cycle_spool126.py.
// Actual Swift/filesystem discovery work and object lifetimes; no game input.
// Counter code is injected into temporary copies of both measured sources.
#if canImport(Darwin)
import Darwin
#endif

func files126(_ root: URL) throws -> [String: String] {
    let enumerator = FileManager.default.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey])!
    var result: [String: String] = [:]
    for case let path as URL in enumerator {
        guard try path.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else { continue }
        try autoreleasepool {
            let bytes = try Data(contentsOf: path)
            result[String(path.path.dropFirst(root.path.count + 1))] = String(bytes.count) + ":" + hash116(bytes)
        }
    }
    return result
}

func metrics126() throws {
    let value: [String: Any] = ["metadata_loads": NG2DiscoveryMetrics126.metadataLoads,
        "live_recovered_sources": NG2DiscoveryMetrics126.liveSources,
        "peak_recovered_sources": NG2DiscoveryMetrics126.peakSources,
        "hash_scratch_bytes": NG2DiscoveryMetrics126.hashScratchBytes]
    let bytes = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    print("METRICS126 " + String(data: bytes, encoding: .utf8)!)
}

func discovery126(_ bound: String) throws {
    var expected: [String] = []
    for _ in 0..<4 {
        let pair = try autoreleasepool { try pair116() }
        expected.append(contentsOf: [pair.0, pair.1])
    }
    check116(NG2DiscoveryMetrics126.liveSources == 0, "fixture_releases_sources_before_discovery")
    let before = try files126(root116)
    NG2DiscoveryMetrics126.reset()
    let pending = try autoreleasepool { try NG2CycleSpool.testUnpublishedRunIDs(rootURL: root116) }
    check116(pending == expected.sorted(), "startup_exact_pending_eight_namespaces")
    check116(try files126(root116) == before, "startup_keeps_every_original_file_byte")
    check116(NG2DiscoveryMetrics126.liveSources == 0, "startup_releases_recovered_sources_after_scan")
    try metrics126()
    if bound == "work" {
        check116(NG2DiscoveryMetrics126.metadataLoads <= 4 * expected.count, "startup_metadata_loads_linear")
    } else {
        check116(NG2DiscoveryMetrics126.peakSources <= 4, "startup_recovered_sources_bounded")
    }
}

func hash126() throws {
    let id = id116()
    do {
        let source = try NG2CycleSpool.testCreate(rootURL: root116, runID: id, owner: owner116)
        _ = try source.commitFrame(captureID: 1, rgba: raw116, metadata: ["generation": 1])
    }
    let directory = root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    let empty = directory.appendingPathComponent(".part-" + UUID().uuidString.lowercased())
    try Data().write(to: empty)
    try FileManager.default.setAttributes([.posixPermissions: NSNumber(value: 0o600)], ofItemAtPath: empty.path)
    let before = try files126(root116)
    NG2DiscoveryMetrics126.reset()
    try autoreleasepool {
        let source = try NG2CycleSpool.testRecover(rootURL: root116, runID: id, owner: owner116)
        let artifacts = try source.artifacts()
        check116(artifacts.contains(where: { $0.name == empty.lastPathComponent && $0.bytes == 0 }),
            "snapshot_includes_empty_uncommitted_artifact")
        for ref in artifacts {
            let bytes = try Data(contentsOf: directory.appendingPathComponent(ref.name))
            check116(ref.bytes == bytes.count && ref.sha256 == hash116(bytes), "snapshot_exact_full_file_sha256")
        }
        let values = artifacts.map { ref -> [String: Any] in
            ["id": hash116(Data(ref.name.utf8)), "name": ref.name, "kind": ref.kind,
             "byte_length": ref.bytes, "sha256": ref.sha256, "input_authority": false]
        }
        let value: [String: Any] = ["run_id": id,
            "original_owner_sha256": source.originalOwnerSHA256 as Any? ?? NSNull(), "artifacts": values]
        let canonical = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
        check116(source.snapshotSHA256 == hash116(canonical), "snapshot_canonical_digest_unchanged")
    }
    check116(try files126(root116) == before, "snapshot_hash_keeps_every_original_file_byte")
    try metrics126()
    check116(NG2DiscoveryMetrics126.hashScratchBytes > 0, "artifact_hash_allocation_observed")
    check116(NG2DiscoveryMetrics126.hashScratchBytes <= 64 * 1024, "artifact_hash_scratch_64KiB")
}

func changedSnapshot126() throws {
    // The same missing-header/receipt boundary asserted by TEST094, isolated
    // here so the selected startup checks do not execute its unrelated cases.
    let id = id116(), root = root116.appendingPathComponent("header-interrupted")
    let directory = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
        attributes: [.posixPermissions: NSNumber(value: 0o700)])
    let part = directory.appendingPathComponent(".part-" + UUID().uuidString.lowercased())
    try Data("interrupted header".utf8).write(to: part)
    try FileManager.default.setAttributes([.posixPermissions: NSNumber(value: 0o600)], ofItemAtPath: part.path)
    let source = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: owner116)
    check116(source.readOnly && source.diagnosticInterrupted && source.originalOwnerSHA256 == nil,
        "missing_header_has_no_original_owner_or_input_authority")
    check116(try source.sessionBytes() == nil, "missing_header_stays_missing")
    let ledger = try source.createRecoveryExport(owner: owner116), exportID = ledger.recoveryExportID!
    let bytes = try JSONSerialization.data(withJSONObject: ["export_id": exportID, "complete": false], options: [.sortedKeys])
    let manifest = try ledger.commitExportManifest(bytes: bytes)
    _ = try source.commitRecoveredPublication(owner: owner116, exportID: exportID,
        manifestSHA256: manifest.sha256, archiveSHA256: String(repeating: "6", count: 64))
    check116(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: root).isEmpty,
        "matching_diagnostic_publication_releases_pending")
    try Data("changed interrupted header".utf8).write(to: part)
    check116(try NG2CycleSpool.testUnpublishedRunIDs(rootURL: root) == [id],
        "changed_original_artifact_invalidates_publication_snapshot")
    check116(try source.sessionBytes() == nil, "publication_never_repairs_missing_header")
}

func hashSource126() throws -> (String,URL) {
    let id=id116()
    do {
        let source=try NG2CycleSpool.testCreate(rootURL:root116,runID:id,owner:owner116)
        _ = try source.commitFrame(captureID:1,rgba:raw116,metadata:["generation":1])
    }
    return (id,root116.appendingPathComponent("NGG2Cycles").appendingPathComponent(id)
        .appendingPathComponent("frame-0000000000000001.rgba"))
}
func hashFailure126(_ id:String,reason:String) throws {
    do {
        _ = try NG2CycleSpool.testRecover(rootURL:root116,runID:id,owner:owner116)
        check116(false,"artifact_hash_must_reject_"+reason)
    } catch NG2CycleSpool.Failure.io(let code) {
        check116(code == reason,"artifact_hash_exact_io_failure_"+reason)
    } catch NG2CycleSpool.Failure.invalid(let code) {
        check116(code == reason,"artifact_hash_exact_invalid_failure_"+reason)
    }
}
func hashFileSafety126() throws {
    for fault in ["symlink","mode","size"] {
        let (id,path)=try hashSource126()
        NG2DiscoveryMetrics126.reset()
        var mutated=false
        NG2DiscoveryMetrics126.beforeArtifactHash = { name,_ in
            guard name == path.lastPathComponent,!mutated else { return }
            mutated=true
            if fault == "symlink" {
                let target=root116.appendingPathComponent("original-"+id)
                try FileManager.default.moveItem(at:path,to:target)
                try FileManager.default.createSymbolicLink(at:path,withDestinationURL:target)
            } else if fault == "mode" {
                try FileManager.default.setAttributes([.posixPermissions:NSNumber(value:0o644)],ofItemAtPath:path.path)
            } else {
                let file=FileHandle(forWritingAtPath:path.path)!
                file.truncateFile(atOffset:UInt64(NG2CycleSpool.maximumExportTemporaryBytes+1));file.closeFile()
            }
        }
        defer { NG2DiscoveryMetrics126.beforeArtifactHash=nil }
        try hashFailure126(id,reason:fault == "symlink" ? "read-open":"read-file")
        check116(mutated,"file_safety_exercises_real_hash_open_"+fault)
    }
}
func hashReadBoundary126(_ growth:Bool) throws {
    let (id,path)=try hashSource126()
    NG2DiscoveryMetrics126.reset()
    var interrupted=false,mutated=false
    NG2DiscoveryMetrics126.beforeRead = { descriptor,_ in
        guard NG2DiscoveryMetrics126.hashDepth > 0 else { return nil }
        var value=stat()
        guard fstat(descriptor,&value) == 0,value.st_size == NG2CycleSpool.rasterBytes,!mutated else { return nil }
        if !interrupted { interrupted=true;errno=EINTR;return -1 }
        mutated=true
        let file=FileHandle(forWritingAtPath:path.path)!
        if growth { file.seekToEndOfFile();file.write(Data([0x5a])) }
        else { file.truncateFile(atOffset:UInt64(NG2CycleSpool.rasterBytes/2)) }
        file.closeFile()
        return nil
    }
    defer { NG2DiscoveryMetrics126.beforeRead=nil }
    try hashFailure126(id,reason:growth ? "read-growth":"read-short")
    check116(interrupted && mutated,"hash_retries_EINTR_then_observes_real_file_change")
}

let selected126 = CommandLine.arguments.dropFirst().first ?? "work"
switch selected126 {
case "work", "retained": try discovery126(selected126)
case "hash": try hash126()
case "116-published_quota": try publishedQuota116()
case "116-damaged_owner": try damagedOwner116()
case "116-orphan_quota": try orphanQuota116()
case "116-orphan_accounting": try orphanAccounting116()
case "116-alias_integrity": try aliasIntegrity116()
case "116-recovered_quota": try recoveredQuota116()
case "116-recovery_namespace": try recoveryNamespace116()
case "snapshot_parity": try changedSnapshot126()
case "hash_file_safety": try hashFileSafety126()
case "hash_short": try hashReadBoundary126(false)
case "hash_growth": try hashReadBoundary126(true)
default: fatalError("unknown TEST126 fixture case")
}
if !["work", "retained", "hash"].contains(selected126) { try metrics126() }
print("PASS TEST126 Spool " + selected126)
