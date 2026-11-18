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
    static var availableBytes: UInt64?
    static var campaignDurationNS: UInt64?
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

    // Storage reservations are never input authority. Recovery instances may
    // charge evidence/export bytes but cannot reserve or create another child.
    struct Reservation: Equatable {
        let tokenID: String
        let rootID: String
        let runID: String
        let index: Int
        let predecessorID: String?
        var payload: [String: Any] {
            ["schema": "ngg2-continuation-reservation-v1", "root_id": rootID,
             "run_id": runID, "index": index, "predecessor_id": predecessorID as Any? ?? NSNull(),
             "token_id": tokenID, "slot_bytes": CampaignQuota.slotBytes]
        }
    }
    fileprivate struct CampaignUsage {
        var raw: Int = 0
        var metadata: Int = 0
        var png: Int = 0
        var temporary: Int = 0
        var total: Int { raw + metadata + png + temporary }
    }
    final class CampaignQuota {
        static let slotBytes = 156 * 1024 * 1024
        static let maximumSlots = 16
        static let maximumBytes = maximumSlots * slotBytes
        private final class Slot {
            let token: Reservation
            var state = 0 // reserved/creating/created/sealed/published/failed
            var writers: [String: CampaignUsage] = [:]
            init(_ token: Reservation) { self.token = token }
            var usage: CampaignUsage {
                writers.values.reduce(CampaignUsage()) { a, b in
                    CampaignUsage(raw: a.raw+b.raw, metadata: a.metadata+b.metadata, png: a.png+b.png, temporary:a.temporary+b.temporary)
                }
            }
        }
        let rootID: String
        fileprivate let rootURL: URL
        private let ownerSHA256: String
        private let storageOnly: Bool
        private let gate = NSLock()
        private var slots: [String: Slot] = [:]
        private var order: [String] = []
        private var rootTimes: (UInt64, UInt64)?
        private var clocks: Set<String> = []
        fileprivate init(rootURL: URL, rootID: String, owner: String, storageOnly: Bool = false) throws {
            guard NG2CycleSpool.isHex(rootID, count: 32), !owner.isEmpty, owner.utf8.count <= 4096 else {
                throw Failure.invalid("campaign-identity")
            }
            self.rootURL = rootURL; self.rootID = rootID; self.storageOnly = storageOnly
            ownerSHA256 = NG2CycleSpool.sha(Data(owner.utf8))
            let fd = open(rootURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw Failure.io("campaign-support") }; defer { close(fd) }
            try NG2CycleSpool.validateSupport(fd)
        }
        func reserveNext(runID: String, index: Int, predecessorID: String?) throws -> Reservation {
            gate.lock(); defer { gate.unlock() }
            guard !storageOnly, NG2CycleSpool.isHex(runID, count: 32), index == order.count,
                  index < 128, slots[runID] == nil,
                  (index == 0 ? runID == rootID && predecessorID == nil : predecessorID == order.last) else {
                throw Failure.invalid("campaign-reservation-identity")
            }
            guard slots.values.filter({ $0.state != 4 }).count < Self.maximumSlots else {
                throw Failure.limit("escrow-quota")
            }
            let names = try NG2CycleSpool.namespaceIDs(rootURL: rootURL)
            let notCreated = order.filter { !names.contains($0) }.count
            guard !names.contains(runID), names.count + notCreated < 128 else {
                throw Failure.limit("campaign-namespace")
            }
            try available(required: remaining() + Self.slotBytes)
            let token = Reservation(tokenID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                rootID: rootID, runID: runID, index: index, predecessorID: predecessorID)
            slots[runID] = Slot(token); order.append(runID)
            return token
        }
        fileprivate func begin(_ token: Reservation, owner: String, provenance: [String: Any]) throws {
            gate.lock(); defer { gate.unlock() }
            guard !storageOnly, ownerSHA256 == NG2CycleSpool.sha(Data(owner.utf8)),
                  let slot = slots[token.runID], slot.token == token, slot.state == 0,
                  let identity = NG2CycleSpool.continuousIdentity(provenance),
                  identity.root == token.rootID, identity.index == token.index,
                  identity.predecessor == token.predecessorID,
                  let clock = provenance["clock_id"] as? String, NG2CycleSpool.isHex(clock, count: 32),
                  !clocks.contains(clock), provenance["native_profile"] as? String == "normal-1-1-irregular-v1" else {
                throw Failure.invalid("campaign-create-token")
            }
            if token.index > 0 {
                guard let predecessor=token.predecessorID,slots[predecessor]?.state == 3 else {
                    throw Failure.invalid("campaign-predecessor-not-sealed")
                }
            }
            if let times = rootTimes {
                guard times.0 == identity.started, times.1 == identity.deadline else {
                    throw Failure.invalid("campaign-root-time")
                }
            } else {
                guard token.index == 0 else { throw Failure.invalid("campaign-root-first") }
                rootTimes = (identity.started, identity.deadline)
            }
            try available(required: remaining())
            clocks.insert(clock); slot.state = 1
        }
        fileprivate func failed(_ token: Reservation) {
            gate.lock(); defer { gate.unlock() }
            if let slot = slots[token.runID], slot.token == token, slot.state == 1 { slot.state = 5 }
        }
        fileprivate func created(_ token: Reservation, writer: String, usage: CampaignUsage) throws {
            gate.lock(); defer { gate.unlock() }
            guard let slot = slots[token.runID], slot.token == token, slot.state == 1 else {
                throw Failure.invalid("campaign-create-state")
            }
            try validate(slot: slot, writer: writer, usage: usage)
            slot.writers[writer] = usage; slot.state = 2
        }
        fileprivate func check(runID: String, writer: String, usage: CampaignUsage) throws {
            gate.lock(); defer { gate.unlock() }
            guard let slot = slots[runID], slot.state != 0 else { throw Failure.invalid("campaign-slot") }
            try validate(slot: slot, writer: writer, usage: usage)
            let additional=slot.state == 4 ? max(0,usage.total-(slot.writers[writer]?.total ?? 0))
                + NG2CycleSpool.maximumExportTemporaryBytes : 0
            try available(required: remaining()+additional)
        }
        fileprivate func charge(runID: String, writer: String, usage: CampaignUsage) throws {
            gate.lock(); defer { gate.unlock() }
            guard let slot = slots[runID] else { throw Failure.invalid("campaign-slot") }
            try validate(slot: slot, writer: writer, usage: usage); slot.writers[writer] = usage
        }
        fileprivate func seal(runID: String) throws {
            gate.lock(); defer { gate.unlock() }
            guard let slot = slots[runID], slot.state == 2 else { throw Failure.invalid("campaign-seal-state") }
            slot.state = 3
        }
        fileprivate func published(runID: String) {
            gate.lock(); defer { gate.unlock() }; slots[runID]?.state = 4
        }
        fileprivate func contains(_ token: Reservation) -> Bool {
            gate.lock(); defer { gate.unlock() }
            return slots[token.runID]?.token == token && slots[token.runID]?.state == 0 && !storageOnly
        }
        // Reconstructed counters are evidence capacity only. They cannot mint
        // a live token or reopen a child, including after a process restart.
        fileprivate func restore(runID:String, identity:(root:String,index:Int,predecessor:String?,started:UInt64,deadline:UInt64),
                                 writer:String, usage:CampaignUsage, published:Bool) throws {
            gate.lock(); defer { gate.unlock() }
            guard storageOnly,identity.root == rootID,identity.index < 128 else { throw Failure.invalid("campaign-recovery") }
            if let times=rootTimes {
                guard times.0 == identity.started && times.1 == identity.deadline else { throw Failure.invalid("campaign-recovery-time") }
            } else { rootTimes=(identity.started,identity.deadline) }
            let slot:Slot
            if let existing=slots[runID] { slot=existing }
            else {
                guard slots.count < 128,(published || slots.values.filter({$0.state != 4}).count < 16),
                      !slots.values.contains(where:{$0.token.index == identity.index}) else {
                    throw Failure.limit("escrow-quota")
                }
                let token=Reservation(tokenID:UUID().uuidString.replacingOccurrences(of:"-",with:"").lowercased(),
                    rootID:rootID,runID:runID,index:identity.index,predecessorID:identity.predecessor)
                slot=Slot(token);slot.state=published ? 4 : 3;slots[runID]=slot;order.append(runID)
            }
            try validate(slot:slot,writer:writer,usage:usage);slot.writers[writer]=usage
        }
        private func validate(slot: Slot, writer: String, usage: CampaignUsage) throws {
            var all = slot.writers; all[writer] = usage
            let total = all.values.reduce(CampaignUsage()) { a, b in
                CampaignUsage(raw: a.raw+b.raw, metadata: a.metadata+b.metadata, png: a.png+b.png, temporary:a.temporary+b.temporary)
            }
            guard total.raw >= 0, total.raw <= NG2CycleSpool.maximumRawBytes,
                  total.metadata >= 0, total.metadata <= NG2CycleSpool.maximumMetadataBytes,
                  total.png >= 0, total.png <= NG2CycleSpool.maximumPNGBytes,
                  total.temporary >= 0,total.temporary <= NG2CycleSpool.maximumExportTemporaryBytes,
                  total.total <= Self.slotBytes else {
                throw Failure.limit("campaign-slot-bytes")
            }
        }
        private func remaining() -> Int {
            slots.values.filter { $0.state != 4 }.reduce(0) { $0 + Self.slotBytes - $1.usage.total }
        }
        private func available(required: Int) throws {
            guard required >= 0, required <= Self.maximumBytes else { throw Failure.limit("escrow-quota") }
            let fd = open(rootURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw Failure.io("campaign-support") }; defer { close(fd) }
            try NG2CycleSpool.validateSupport(fd)
            guard try NG2CycleSpool.availableBytes(fd) >= UInt64(required) else { throw Failure.limit("escrow-quota") }
        }
    }
    private final class WeakCampaignQuota {
        weak var value:CampaignQuota?
        init(_ value:CampaignQuota) { self.value=value }
    }
    private static let recoveredQuotaGate=NSLock()
    private static var recoveredQuotas:[String:WeakCampaignQuota]=[:]
    enum Failure: Error {
        case invalid(String), io(String), limit(String), readOnly, collision
    }
    // A run-local reservation is never reconstructed from a recovery journal.
    struct IrregularReservation: Equatable {
        let id: String
        let episode, prefix, generation: UInt64
    }
    private struct IrregularBudget {
        let token: IrregularReservation
        var knownCaptureIDs: Set<UInt64>
        var futureRoles: Int
        var records: Set<String>
        let pinSlots: Int
        var rawSlots: Int { knownCaptureIDs.count + futureRoles }
        var metadata: Int { rawSlots * 4096 + records.count * 32768 }
    }
    private struct FinalBudget {
        var terminal = true, manifest = true, receipt = true
        var pngSlots: Int
        var metadata: Int {
            (terminal ? 512 * 1024 : 0) + pngSlots * 4096
                + (manifest ? 384 * 1024 : 0) + (receipt ? 8 * 1024 : 0)
        }
        var records: Int { (terminal ? 1 : 0) + (receipt ? 1 : 0) }
    }
    private static let irregularKinds: Set<String> = ["irregular_checkpoint", "irregular_continue_intent",
        "irregular_continue_outcome", "irregular_restart_intent", "irregular_restart_outcome"]
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
    private var nativeProfile: String?
    private var irregularBudget: IrregularBudget?
    private var finalBudget: FinalBudget?
    private var lastReservedEpisode: UInt64 = 0
    private var campaignQuota: CampaignQuota?
    private var campaignReservation: Reservation?
    private var continuousProvenance: [String: Any]?
    private var committedSessionSHA256: String?
    private var inheritedPNGSource:NG2CycleSpool?
    private var inheritedPNGs:[UInt64:PNGRef]=[:]
    private var inheritedRawSHA256:[UInt64:String]=[:]
    private var contentSealed = false
    private var continuationSealCredit = false
    var controlContentSealed: Bool { gate.lock(); defer { gate.unlock() }; return contentSealed }
    private var campaignWriter: String { rootName + "/" + directoryName }
    private var campaignUsage: CampaignUsage {
        CampaignUsage(raw: registered.count * Self.rasterBytes, metadata: metadataBytes, png: pngBytes)
    }
    private var reservedRawSlots: Int { irregularBudget?.rawSlots ?? 0 }
    private var reservedMetadata: Int { (irregularBudget?.metadata ?? 0) + (finalBudget?.metadata ?? 0) + (continuationSealCredit ? 8 * 1024 : 0) }
    private var reservedRecords: Int { (irregularBudget?.records.count ?? 0) + (finalBudget?.records ?? 0) + (continuationSealCredit ? 1 : 0) }
    var readOnly: Bool { gate.lock(); defer { gate.unlock() }; return !writable || damaged }

    private init(rootURL: URL, runID: String, owner: String, recover: Bool, verifyRasters: Bool = true,
                 rootName: String = "NGG2Cycles", directoryName: String? = nil,
                 provenance: [String: Any] = [:], quota: CampaignQuota? = nil, reservation: Reservation? = nil,
                 exportQuota:CampaignQuota? = nil, attachCampaignRecovery:Bool = true) throws {
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
        nativeProfile = provenance["native_profile"] as? String
        campaignQuota = exportQuota
        if !recover && (quota != nil || reservation != nil || provenance["continuous_campaign"] != nil) {
            guard let quota, let reservation, reservation.runID == runID,
                  quota.rootURL.standardizedFileURL == rootURL.standardizedFileURL else { throw Failure.invalid("campaign-create") }
            try quota.begin(reservation, owner: owner, provenance: provenance)
            campaignQuota = quota; campaignReservation = reservation
            continuousProvenance = provenance; continuationSealCredit = true
        }
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
                if campaignQuota != nil { try checkSpace(raw: 0, metadata: bytes.count) }
                try atomic(bytes, name: "session.json")
                metadataBytes = bytes.count
                committedSessionSHA256 = Self.sha(bytes)
                if let quota = campaignQuota, let reservation = campaignReservation {
                    try quota.created(reservation, writer: campaignWriter, usage: campaignUsage)
                } else if let quota=campaignQuota {
                    try quota.charge(runID:runID,writer:campaignWriter,usage:campaignUsage)
                }
            }
            if recover && attachCampaignRecovery && rootName == "NGG2Cycles" && continuousProvenance != nil {
                try restoreCampaignAccounting()
            } else if recover,let quota=campaignQuota {
                try quota.charge(runID:runID,writer:campaignWriter,usage:try storedUsage())
            }
        } catch {
            if let quota = campaignQuota, let token = campaignReservation { quota.failed(token) }
            close(directoryFD)
            directoryFD = -1
            throw error
        }
    }
    deinit { if directoryFD >= 0 { close(directoryFD) } }

    static func createCampaignQuota(rootID: String, owner: String) throws -> CampaignQuota {
        try CampaignQuota(rootURL: applicationSupport(), rootID: rootID, owner: owner)
    }
    static func create(runID: String, owner: String, provenance: [String: Any] = [:],
                       quota: CampaignQuota? = nil, reservation: Reservation? = nil) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: applicationSupport(), runID: runID, owner: owner, recover: false,
                         provenance: provenance, quota: quota, reservation: reservation)
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
            let spool = try NG2CycleSpool(rootURL: rootURL, runID: id, owner: "read-only-scan", recover: true, verifyRasters: false,attachCampaignRecovery:false)
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
    static func testCreateCampaignQuota(rootURL: URL, rootID: String, owner: String) throws -> CampaignQuota {
        try CampaignQuota(rootURL: rootURL, rootID: rootID, owner: owner)
    }
    static func testCreate(rootURL: URL, runID: String, owner: String, provenance: [String: Any] = [:],
                           quota: CampaignQuota? = nil, reservation: Reservation? = nil) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: rootURL, runID: runID, owner: owner, recover: false,
                         provenance: provenance, quota: quota, reservation: reservation)
    }
    static func testRecover(rootURL: URL, runID: String, owner: String) throws -> NG2CycleSpool {
        try NG2CycleSpool(rootURL: rootURL, runID: runID, owner: owner, recover: true)
    }
    static func testUnpublishedRunIDs(rootURL: URL) throws -> [String] {
        try unpublished(rootURL: rootURL)
    }
    func testIrregularCredits() -> [String: Int] {
        gate.lock(); defer { gate.unlock() }
        return ["episode_raw_slots": reservedRawSlots, "episode_metadata_bytes": irregularBudget?.metadata ?? 0,
            "final_metadata_bytes": finalBudget?.metadata ?? 0, "record_slots": reservedRecords]
    }
    #endif

    // The single writer calls this before a checkpoint. Finalization may
    // count its own terminal-record credit; no other writer can spend it.
    func reserveCheckpoint(frames: Int, metadataBytes requested: Int, finalization: Bool = false) throws {
        try writing {
            let terminalCredit = finalization && finalBudget?.terminal == true ? 512 * 1024 : 0
            guard frames >= 0, frames <= Self.maximumFrames - registered.count - reservedRawSlots,
                  requested >= 0, requested <= Self.maximumMetadataBytes - metadataBytes - reservedMetadata + terminalCredit,
                  (registered.count + frames + reservedRawSlots) * Self.rasterBytes <= Self.maximumRawBytes else {
                throw Failure.limit("checkpoint")
            }
            try checkSpace(raw: frames * Self.rasterBytes, metadata: requested)
        }
    }
    func reserveIrregular(episode: UInt64, prefix: UInt64, generation: UInt64,
                          knownCaptureIDs: Set<UInt64>, futureRoles: Int,
                          pinnedCaptureIDs: Set<UInt64>) throws -> IrregularReservation {
        try writing {
            guard nativeProfile == "normal-1-1-irregular-v1", irregularBudget == nil, manifestRef == nil,
                  episode > lastReservedEpisode, episode < UInt64(Int64.max), generation > 0,
                  generation < UInt64(Int64.max), prefix < UInt64(Int64.max),
                  futureRoles >= 0, knownCaptureIDs.count <= 16,
                  futureRoles <= 16 - knownCaptureIDs.count, pinnedCaptureIDs.count <= 24,
                  (knownCaptureIDs.union(pinnedCaptureIDs)).allSatisfy({ $0 > 0 && $0 < UInt64(Int64.max) }),
                  !recordList.contains(where: { $0.kind == "terminal" || $0.kind == "published" }) else {
                throw Failure.invalid("irregular-reservation")
            }
            let missing = knownCaptureIDs.subtracting(registered.keys)
            let pins = knownCaptureIDs.subtracting(pinnedCaptureIDs).count + futureRoles
            let token = IrregularReservation(id: UUID().uuidString.lowercased(), episode: episode,
                prefix: prefix, generation: generation)
            let budget = IrregularBudget(token: token, knownCaptureIDs: missing, futureRoles: futureRoles,
                records: Self.irregularKinds, pinSlots: pins)
            let final = finalBudget ?? FinalBudget(pngSlots: Self.maximumFrames - registeredPNGs.count)
            guard registered.count + budget.rawSlots <= Self.maximumFrames,
                  (registered.count + budget.rawSlots) * Self.rasterBytes <= Self.maximumRawBytes,
                  pinnedCaptureIDs.count + pins <= 24,
                  metadataBytes + budget.metadata + final.metadata <= Self.maximumMetadataBytes,
                  recordList.count + budget.records.count + final.records <= 512 else {
                throw Failure.limit("irregular-reservation")
            }
            let previousFinal = finalBudget
            irregularBudget = budget; finalBudget = final
            do { try checkSpace(raw: 0, metadata: 0) }
            catch {
                // No token escaped: roll back only this attempted reservation.
                // The enclosing writer still freezes after the space failure.
                irregularBudget = nil; finalBudget = previousFinal
                throw error
            }
            lastReservedEpisode = episode
            return token
        }
    }
    func irregularResources(_ token: IrregularReservation) throws -> [String: Any] {
        gate.lock(); defer { gate.unlock() }
        guard let budget = irregularBudget, budget.token == token else { throw Failure.invalid("irregular-token") }
        return ["raw_slots": budget.rawSlots, "raw_bytes": budget.rawSlots * Self.rasterBytes,
            "pin_slots": budget.pinSlots, "episode_metadata_bytes": budget.metadata,
            "final_metadata_bytes": finalBudget?.metadata ?? 0]
    }
    // Runtime calls this only after its actual persistence callback drains.
    // Written bytes stay charged; only unused episode credit is released.
    func releaseIrregular(_ token: IrregularReservation) throws {
        gate.lock(); defer { gate.unlock() }
        guard irregularBudget?.token == token else { throw Failure.invalid("irregular-token") }
        irregularBudget = nil
    }
    func commitFrame(captureID: UInt64, rgba: Data, metadata: [String: Any],
                     reservation: IrregularReservation? = nil) throws -> FrameRef {
        try writing {
            guard manifestRef == nil, captureID > 0, captureID < UInt64(Int64.max), registered[captureID] == nil else {
                throw Failure.collision
            }
            try Self.validateRGBA(rgba)
            let rawHash = Self.sha(rgba)
            let envelope: [String: Any] = ["schema": "ngg2-cycle-frame-v1", "run_id": runID,
                "capture_id": captureID, "raw_sha256": rawHash, "raw_bytes": rgba.count,
                "metadata": metadata]
            let encoded = try Self.canonical(envelope)
            if let reservation {
                guard Self.unsigned(metadata["generation"]) == reservation.generation else {
                    throw Failure.invalid("irregular-frame-generation")
                }
            }
            try consumeFrameCredit(captureID, bytes: encoded.count, reservation: reservation)
            guard registered.count + 1 + reservedRawSlots <= Self.maximumFrames,
                  (registered.count + 1 + reservedRawSlots) * Self.rasterBytes <= Self.maximumRawBytes else {
                throw Failure.limit("rasters")
            }
            try checkMetadata(encoded.count)
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
    func commitRecord(kind: String, cycle: UInt64, payload: [String: Any], previous: String? = nil,
                      reservation: IrregularReservation? = nil) throws -> RecordRef {
        try writing(export: kind == "published") {
            guard kind != "continuation_seal" || campaignQuota == nil else { throw Failure.invalid("seal-method-required") }
            if kind == "continuation_reservation", continuousProvenance != nil {
                guard let quota = campaignQuota, let token = Self.reservationValue(payload), quota.contains(token),
                      let provenance = continuousProvenance, let current = Self.continuousIdentity(provenance),
                      token.rootID == current.root, token.index == current.index+1,
                      token.predecessorID == runID else { throw Failure.invalid("continuation-reservation") }
            }
            return try appendRecord(kind: kind, cycle: cycle, payload: payload, previous: previous, reservation: reservation)
        }
    }
    // Called only while the single writer gate is held, including the terminal
    // content seal, so its exact prior chain and raster set cannot race a write.
    private func appendRecord(kind: String, cycle: UInt64, payload: [String: Any], previous: String? = nil,
                              reservation: IrregularReservation? = nil) throws -> RecordRef {
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
        try consumeRecordCredit(kind, bytes: encoded.count, payload: payload, reservation: reservation)
        guard recordList.count + 1 + reservedRecords <= 512 else { throw Failure.limit("records") }
        try checkMetadata(encoded.count)
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
    // Runtime calls only after terminal plus the actual capture/producer/main
    // and persistence callback return drains. This seals evidence, not input.
    func sealContinuation(rootID: String, index: Int, predecessorID: String?, clockID: String,
                          terminal: RecordRef, continuation: [String: Any], successor: Reservation?) throws -> RecordRef {
        try writing {
            guard let quota = campaignQuota, let provenance = continuousProvenance,
                  let identity = Self.continuousIdentity(provenance), !contentSealed,
                  continuationSealCredit, irregularBudget == nil, manifestRef == nil,
                  identity.root == rootID, identity.index == index, identity.predecessor == predecessorID,
                  provenance["clock_id"] as? String == clockID,
                  terminal.kind == "terminal", let savedTerminal=recordList.last,
                  savedTerminal.sequence == terminal.sequence,savedTerminal.cycle == terminal.cycle,
                  savedTerminal.kind == terminal.kind,savedTerminal.sha256 == terminal.sha256,
                  savedTerminal.previous == terminal.previous,
                  (try Self.canonical(savedTerminal.payload)) == (try Self.canonical(terminal.payload)),
                  Self.validControllerSeal(continuation, identity: identity),
                  let status = savedTerminal.payload["controller"] as? [String: Any],
                  Self.validTerminalSeal(status,continuation:continuation),
                  let savedContinuation=status["continuous_campaign"] as? [String:Any],
                  (try Self.canonical(savedContinuation)) == (try Self.canonical(continuation)) else {
                throw Failure.invalid("continuation-seal-state")
            }
            if let next = successor {
                guard Self.strictBool(continuation["qualified"]) == true, quota.contains(next),
                      next.rootID == rootID, next.index == index+1, next.predecessorID == runID,
                      recordList.contains(where: { $0.kind == "continuation_reservation"
                        && Self.reservationValue($0.payload) == next }) else {
                    throw Failure.invalid("continuation-successor")
                }
            }
            let session = try read("session.json", maximum: Self.maximumMetadataBytes)
            guard let header=Self.validSessionHeader(session,runID:runID),
                  Self.sha(session) == committedSessionSHA256,
                  header["owner_sha256"] as? String == ownerSHA256,
                  let savedProvenance=header["provenance"] as? [String:Any],
                  (try Self.canonical(savedProvenance)) == (try Self.canonical(provenance)),
                  Self.sha(try read(recordName(terminal.sequence,terminal.kind),maximum:Self.maximumMetadataBytes)) == terminal.sha256 else {
                throw Failure.invalid("continuation-terminal-hash")
            }
            try validateRecordsForSeal()
            // Each atomic commit already fsynced its file and directory. Check
            // its exact bytes again under the writer gate before joining all
            // references into the final durable chain. One raster at a time.
            for id in registered.keys.sorted() {
                let ref = registered[id]!
                let raw = try read(frameName(id,suffix:"rgba"),maximum:Self.rasterBytes)
                try Self.validateRGBA(raw)
                guard Self.sha(raw) == ref.rawSHA256,
                      Self.sha(try read(frameName(id,suffix:"json"),maximum:Self.maximumMetadataBytes)) == ref.metadataSHA256 else {
                    throw Failure.invalid("continuation-frame-hash")
                }
            }
            let payload: [String: Any] = ["schema":"ngg2-continuation-seal-v1", "root_id":rootID,
                "run_id":runID, "index":index, "predecessor_id":predecessorID as Any? ?? NSNull(),
                "next_run_id":successor?.runID as Any? ?? NSNull(), "clock_id":clockID,
                "session_sha256":Self.sha(session), "terminal_sha256":terminal.sha256,
                "frames_sha256":try frameReferencesSHA(), "controller":continuation]
            guard try validContinuationSeal(payload, prior:terminal),
                  (try Self.canonical(payload)).count <= 7 * 1024 else { throw Failure.invalid("continuation-seal-payload") }
            continuationSealCredit = false
            let seal = try appendRecord(kind:"continuation_seal",cycle:terminal.cycle,payload:payload)
            try quota.seal(runID:runID)
            contentSealed = true
            return seal
        }
    }
    private func validateRecordsForSeal() throws {
        var previous:String?
        for ref in recordList {
            let bytes=try read(recordName(ref.sequence,ref.kind),maximum:Self.maximumMetadataBytes)
            guard Self.sha(bytes) == ref.sha256,ref.previous == previous,
                  let value=try JSONSerialization.jsonObject(with:bytes) as? [String:Any],
                  Set(value.keys) == ["schema","run_id","sequence","kind","cycle","previous","payload"],
                  value["schema"] as? String == "ngg2-cycle-record-v1",value["run_id"] as? String == runID,
                  Self.unsigned(value["sequence"]) == UInt64(ref.sequence),value["kind"] as? String == ref.kind,
                  Self.unsigned(value["cycle"]) == ref.cycle,
                  (value["previous"] as? String) == previous,
                  (previous == nil ? value["previous"] is NSNull : value["previous"] is String),
                  let payload=value["payload"] as? [String:Any],
                  (try Self.canonical(payload)) == (try Self.canonical(ref.payload)),
                  (try Self.canonical(value)) == bytes else { throw Failure.invalid("continuation-record-chain") }
            previous=ref.sha256
        }
    }
    private func frameReferencesSHA() throws -> String {
        let values: [[String: Any]] = registered.keys.sorted().map { id in
            let ref = registered[id]!
            return ["capture_id":ref.captureID, "raw_sha256":ref.rawSHA256,
                "metadata_sha256":ref.metadataSHA256, "bytes":ref.bytes]
        }
        return Self.sha(try JSONSerialization.data(withJSONObject:values,options:[.sortedKeys,.withoutEscapingSlashes]))
    }
    private static func strictBool(_ value: Any?) -> Bool? {
        guard let number = value as? NSNumber, String(cString:number.objCType) == "c",
              number.intValue == 0 || number.intValue == 1 else { return nil }
        return number.boolValue
    }
    private static func validTerminalSeal(_ status:[String:Any],continuation:[String:Any]) -> Bool {
        guard unsigned(status["terminal"]) == 1,let input=unsigned(status["input_state"]),
              let command=unsigned(status["current_command_id"]),command < UInt64(Int64.max) else { return false }
        if strictBool(continuation["qualified"]) == true { return input == 0 && command == 0 }
        // Evidence-only final seals preserve a known ACK waiting for visual
        // proof or an UNKNOWN synth. Real return-drain is Runtime's fence;
        // neither logical state3/4 nor its command is erased to mimic it.
        return (input == 0 && command == 0) || input == 3 || input == 4
    }
    private static func validControllerSeal(_ value:[String:Any],
        identity:(root:String,index:Int,predecessor:String?,started:UInt64,deadline:UInt64)) -> Bool {
        let numbers:Set<String> = ["abi_version","root_deadline_ns","qualified_ns","parent_deadline_ns",
            "old_job_id","restart_command_id","new_floor_capture_id","source_capture_id","source_start_ns","source_prefix"]
        guard Set(value.keys) == numbers.union(["enabled","successor_floor","qualified"]),
              numbers.allSatisfy({ unsigned(value[$0]).map({ $0 < UInt64(Int64.max) }) == true }),
              unsigned(value["abi_version"]) == 1, strictBool(value["enabled"]) == true,
              strictBool(value["successor_floor"]) == (identity.index > 0),
              let qualified = strictBool(value["qualified"]), unsigned(value["root_deadline_ns"]) == identity.deadline else { return false }
        if qualified {
            guard let at=unsigned(value["qualified_ns"]), let parent=unsigned(value["parent_deadline_ns"]),
                  let start=unsigned(value["source_start_ns"]), at >= identity.started, parent >= at,
                  parent <= identity.deadline, start > 0, start <= at,
                  ["old_job_id","restart_command_id","new_floor_capture_id","source_capture_id","source_prefix"]
                    .allSatisfy({ (unsigned(value[$0]) ?? 0) > 0 }),
                  unsigned(value["source_prefix"]) == unsigned(value["restart_command_id"]) else { return false }
        }
        return true
    }
    private func validContinuationSeal(_ value:[String:Any], prior:RecordRef?) throws -> Bool {
        guard Set(value.keys) == ["schema","root_id","run_id","index","predecessor_id","next_run_id",
                "clock_id","session_sha256","terminal_sha256","frames_sha256","controller"],
              value["schema"] as? String == "ngg2-continuation-seal-v1",value["run_id"] as? String == runID,
              let provenance=continuousProvenance,let identity=Self.continuousIdentity(provenance),
              value["root_id"] as? String == identity.root,Self.unsigned(value["index"]) == UInt64(identity.index),
              (identity.index == 0 ? value["predecessor_id"] is NSNull : value["predecessor_id"] as? String == identity.predecessor),
              let clock=value["clock_id"] as? String,Self.isHex(clock,count:32),provenance["clock_id"] as? String == clock,
              let controller=value["controller"] as? [String:Any],Self.validControllerSeal(controller,identity:identity),
              prior?.kind == "terminal",value["terminal_sha256"] as? String == prior?.sha256,
              let priorController=prior?.payload["controller"] as? [String:Any],
              Self.validTerminalSeal(priorController,continuation:controller),
              let priorContinuation=priorController["continuous_campaign"] as? [String:Any],
              (try Self.canonical(priorContinuation)) == (try Self.canonical(controller)),
              value["session_sha256"] as? String == Self.sha(try read("session.json",maximum:Self.maximumMetadataBytes)),
              value["frames_sha256"] as? String == (try frameReferencesSHA()) else { return false }
        if !(value["next_run_id"] is NSNull) {
            guard let next=value["next_run_id"] as? String,Self.isHex(next,count:32),next != runID,
                  Self.strictBool(controller["qualified"]) == true,
                  recordList.contains(where:{ ref in
                    guard ref.kind == "continuation_reservation",let token=Self.reservationValue(ref.payload) else { return false }
                    return token.rootID == identity.root && token.runID == next && token.index == identity.index+1
                        && token.predecessorID == runID
                  }) else { return false }
        }
        if Self.strictBool(controller["qualified"]) == true {
            guard let source=Self.unsigned(controller["source_capture_id"]),let ref=registered[source],
                  let floor=Self.unsigned(controller["new_floor_capture_id"]),registered[floor] != nil,
                  let envelope=try JSONSerialization.jsonObject(with:read(frameName(source,suffix:"json"),maximum:Self.maximumMetadataBytes)) as? [String:Any],
                  Self.sha(try read(frameName(source,suffix:"json"),maximum:Self.maximumMetadataBytes)) == ref.metadataSHA256,
                  let metadata=envelope["metadata"] as? [String:Any],Self.strictBool(metadata["stable_prefix"]) == true,
                  Self.strictBool(metadata["inflight_start"]) == false,Self.strictBool(metadata["inflight_end"]) == false,
                  let captureStart=Self.unsigned(metadata["capture_start_ns"]),
                  let captureEnd=Self.unsigned(metadata["capture_end_ns"]),captureEnd >= captureStart,
                  let qualifiedAt=Self.unsigned(controller["qualified_ns"]),captureEnd <= qualifiedAt,
                  Self.unsigned(metadata["capture_start_ns"]) == Self.unsigned(controller["source_start_ns"]),
                  Self.unsigned(metadata["completed_prefix_start"]) == Self.unsigned(controller["source_prefix"]),
                  Self.unsigned(metadata["completed_prefix_end"]) == Self.unsigned(controller["source_prefix"]) else { return false }
        }
        return true
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
        try writing(export: true) {
            guard Self.isHex(exportID, count: 32), manifestRef == nil, !bytes.isEmpty,
                  bytes.count <= Self.maximumMetadataBytes - metadataBytes,
                  (try? JSONSerialization.jsonObject(with: bytes)) is [String: Any] else {
                throw Failure.invalid("export-manifest")
            }
            if var final = finalBudget {
                guard final.manifest, bytes.count <= 384 * 1024, irregularBudget == nil else {
                    throw Failure.limit("irregular-manifest")
                }
                final.manifest = false; final.pngSlots = 0; finalBudget = final
            }
            try checkMetadata(bytes.count)
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
        try writing(export: true) {
            guard manifestRef == nil, captureID > 0, captureID < UInt64(Int64.max), registeredPNGs[captureID] == nil,
                  inheritedPNGs[captureID] == nil,
                  registered[captureID] != nil || rootName == "NGG2RecoveryExports",
                  registeredPNGs.count + inheritedPNGs.keys.filter({registeredPNGs[$0] == nil}).count < Self.maximumFrames else { throw Failure.invalid("png-identity") }
            try Self.validatePNG(bytes)
            guard bytes.count <= Self.maximumPNGBytes - pngBytes else { throw Failure.limit("png-total") }
            let digest = Self.sha(bytes)
            let value: [String: Any] = ["schema": "ngg2-cycle-png-v1", "run_id": runID,
                "capture_id": captureID, "png_sha256": digest, "png_bytes": bytes.count, "metadata": metadata]
            let encoded = try Self.canonical(value)
            if var final = finalBudget {
                guard final.pngSlots > 0, encoded.count <= 4096, irregularBudget == nil else {
                    throw Failure.limit("irregular-png-metadata")
                }
                final.pngSlots -= 1; finalBudget = final
            }
            try checkMetadata(encoded.count)
            if campaignQuota != nil { try checkSpace(raw: 0, metadata: encoded.count, png: bytes.count) }
            else { try checkSpace(raw: finalBudget == nil ? bytes.count : 0, metadata: encoded.count) }
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
        var refs=inheritedPNGs
        for (id,ref) in registeredPNGs { refs[id]=ref }
        return refs.keys.sorted().compactMap { refs[$0] }
    }
    func readPNG(_ ref: PNGRef, offset: Int = 0, length: Int? = nil) throws -> Data {
        gate.lock()
        if registeredPNGs[ref.captureID] == nil,let source=inheritedPNGSource,let alias=inheritedPNGs[ref.captureID] {
            let valid=alias.sha256 == ref.sha256 && alias.metadataSHA256 == ref.metadataSHA256 && alias.bytes == ref.bytes
            gate.unlock()
            guard valid else { throw Failure.invalid("inherited-png-reference") }
            // Never hold a ledger gate while entering its immutable source;
            // publication uses the opposite ownership direction.
            return try source.readPNG(alias,offset:offset,length:length)
        }
        defer { gate.unlock() }
        guard let owned=registeredPNGs[ref.captureID],owned.sha256 == ref.sha256 else { throw Failure.invalid("png-reference") }
        if campaignQuota != nil || continuousProvenance != nil {
            guard owned.metadataSHA256 == ref.metadataSHA256,owned.bytes == ref.bytes,
                  (try Self.canonical(owned.metadata)) == (try Self.canonical(ref.metadata)) else { throw Failure.invalid("png-reference") }
            try validateCampaignPNG(owned)
        }
        let bytes = try read(pngName(ref.captureID, suffix: "png"), maximum: Self.maximumExportTemporaryBytes)
        try Self.validatePNG(bytes)
        guard bytes.count == ref.bytes, Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("png-sha") }
        if length == nil { return bytes }
        guard offset >= 0, offset < bytes.count, let count = length, count > 0, count <= 64 * 1024 else {
            throw Failure.invalid("png-range")
        }
        return Data(bytes[offset..<min(bytes.count, offset + count)])
    }
    private func validateCampaignPNG(_ ref:PNGRef) throws {
        let envelope=try read(pngName(ref.captureID,suffix:"json"),maximum:Self.maximumMetadataBytes)
        guard Self.sha(envelope) == ref.metadataSHA256,
              let value=try JSONSerialization.jsonObject(with:envelope) as? [String:Any],
              (try Self.canonical(value)) == envelope,
              let metadata=value["metadata"] as? [String:Any],
              metadata["raw_sha256"] as? String == (registered[ref.captureID]?.rawSHA256 ?? inheritedRawSHA256[ref.captureID]),
              let expected=metadata["raw_sha256"] as? String,Self.isHex(expected,count:64),
              value["png_sha256"] as? String == ref.sha256,Self.unsigned(value["png_bytes"]) == UInt64(ref.bytes) else {
            throw Failure.invalid("png-source-binding")
        }
    }
    // Caller owns this original source gate. A new or read-only recovered
    // sibling may use these fixed references; no pathname is supplied by RPC.
    private func attachInheritedPNGs(to ledger:NG2CycleSpool) throws {
        guard campaignQuota != nil else { return }
        ledger.inheritedPNGSource=self
        ledger.inheritedRawSHA256=Dictionary(uniqueKeysWithValues:registered.values.map {($0.captureID,$0.rawSHA256)})
        var inherited:[UInt64:PNGRef]=[:]
        for id in registeredPNGs.keys.sorted() {
            let ref=registeredPNGs[id]!
            do {
                try validateCampaignPNG(ref)
                let bytes=try read(pngName(id,suffix:"png"),maximum:Self.maximumExportTemporaryBytes)
                try Self.validatePNG(bytes)
                guard bytes.count == ref.bytes,Self.sha(bytes) == ref.sha256 else { throw Failure.invalid("png-sha") }
                inherited[id]=ref
            } catch {
                // Original bytes stay untouched; the diagnostic inventory
                // exposes the bad metadata/PNG. A new valid conversion may
                // use remaining quota, but this file is never called valid.
                diagnosticInterrupted=true
            }
        }
        ledger.inheritedPNGs=inherited
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
        try refreshCampaignUsage()
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
        try refreshCampaignUsage()
        let exportID = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let ledger = try NG2CycleSpool(rootURL: supportURL, runID: runID, owner: owner, recover: false,
            rootName: "NGG2RecoveryExports", directoryName: runID + "-" + exportID,exportQuota:campaignQuota)
        try attachInheritedPNGs(to:ledger)
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
    private func verifiedRecoveryPublication() throws -> Bool {
        gate.lock();defer { gate.unlock() }
        let path=supportURL.appendingPathComponent("NGG2RecoveryExports").path
        var value=stat()
        if lstat(path,&value) != 0 && errno == ENOENT { return false }
        if snapshotSHA256 == nil { try buildSnapshot() }
        for ledger in try matchingRecoveryExports(owner:"storage-only-publication") {
            guard !ledger.diagnosticInterrupted,let receipt=ledger.recordList.last,receipt.kind == "published",
                  let manifest=ledger.manifestRef,
                  receipt.payload["export_id"] as? String == manifest.exportID,
                  receipt.payload["manifest_sha256"] as? String == manifest.sha256,
                  Self.validReceipt(receipt.payload) else { continue }
            let bytes=try ledger.readExportManifest(manifest)
            if bytes.count == manifest.bytes && Self.sha(bytes) == manifest.sha256 { return true }
        }
        return false
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
                verifyRasters: true, rootName: "NGG2RecoveryExports", directoryName: name,exportQuota:campaignQuota)
            try attachInheritedPNGs(to:ledger)
            if !ledger.diagnosticInterrupted,
               ledger.recordList.first?.kind == "recovery_source",
               ledger.recordList.first?.payload["snapshot_sha256"] as? String == snapshotSHA256 { ledgers.append(ledger) }
        }
        return ledgers
    }
    var recoveryExportID: String? {
        rootName == "NGG2RecoveryExports" ? String(directoryName.suffix(32)) : nil
    }

    private func writing<T>(export: Bool = false, _ body: () throws -> T) throws -> T {
        gate.lock(); defer { gate.unlock() }
        guard writable && !damaged && (!contentSealed || export) else { throw Failure.readOnly }
        do {
            let result = try body()
            if let quota = campaignQuota {
                try quota.charge(runID: runID, writer: campaignWriter, usage: campaignUsage)
                if recordList.last?.kind == "published" { quota.published(runID: runID) }
            }
            return result
        } catch { damaged = true; writable = false; diagnosticInterrupted = true; incompleteEntries = true; throw error }
    }
    private func checkMetadata(_ bytes: Int) throws {
        guard bytes >= 0, bytes <= Self.maximumMetadataBytes - metadataBytes - reservedMetadata else {
            throw Failure.limit("metadata")
        }
    }
    private func consumeFrameCredit(_ captureID: UInt64, bytes: Int,
                                    reservation: IrregularReservation?) throws {
        guard let reservation else {
            guard irregularBudget?.knownCaptureIDs.contains(captureID) != true else {
                throw Failure.invalid("irregular-frame-token")
            }
            return
        }
        guard var budget = irregularBudget, budget.token == reservation, bytes <= 4096 else {
            throw Failure.invalid("irregular-frame-token")
        }
        if budget.knownCaptureIDs.remove(captureID) == nil {
            guard budget.futureRoles > 0 else { throw Failure.limit("irregular-frame-credit") }
            budget.futureRoles -= 1
        }
        irregularBudget = budget
    }
    private func consumeRecordCredit(_ kind: String, bytes: Int, payload: [String: Any],
                                     reservation: IrregularReservation?) throws {
        if let reservation {
            guard var budget = irregularBudget, budget.token == reservation,
                  Self.irregularKinds.contains(kind), budget.records.contains(kind), bytes <= 32768,
                  Self.unsigned(payload["generation"]) == reservation.generation,
                  let status = payload["irregular"] as? [String: Any],
                  Self.unsigned(status["episode_id"]) == reservation.episode else {
                throw Failure.invalid("irregular-record-token")
            }
            budget.records.remove(kind); irregularBudget = budget
        } else if kind.hasPrefix("irregular_") {
            throw Failure.invalid("irregular-record-token")
        } else if var final = finalBudget {
            if kind == "terminal" {
                guard final.terminal, bytes <= 512 * 1024, irregularBudget == nil else {
                    throw Failure.limit("irregular-terminal")
                }
                final.terminal = false
            } else if kind == "published" {
                guard final.receipt, !final.terminal, !final.manifest, manifestRef != nil,
                      bytes <= 8 * 1024, irregularBudget == nil else {
                    throw Failure.limit("irregular-receipt")
                }
                final.receipt = false
            }
            finalBudget = final
        }
    }
    private static func availableBytes(_ descriptor: Int32) throws -> UInt64 {
        #if canImport(Darwin)
        var value = statfs()
        guard fstatfs(descriptor, &value) == 0 else { throw Failure.io("space") }
        let measured = UInt64(value.f_bavail) * UInt64(value.f_bsize)
        #else
        var value = statvfs()
        guard fstatvfs(descriptor, &value) == 0 else { throw Failure.io("space") }
        let measured = UInt64(value.f_bavail) * UInt64(value.f_frsize)
        #endif
        #if NG2_RUNTIME_HOST_TEST
        return NG2CycleSpoolTestHooks.availableBytes ?? measured
        #else
        return measured
        #endif
    }
    private static func namespaceIDs(rootURL: URL,rootName:String = "NGG2Cycles") throws -> Set<String> {
        let support = open(rootURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard support >= 0 else { throw Failure.io("support") }; defer { close(support) }
        try validateSupport(support)
        guard rootName == "NGG2Cycles" || rootName == "NGG2RecoveryExports" else { throw Failure.invalid("namespace") }
        let fd = openat(support, rootName, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        if fd < 0 && errno == ENOENT { return [] }
        guard fd >= 0 else { throw Failure.io("root") }; defer { close(fd) }
        try validateDirectory(fd)
        let duplicate = dup(fd)
        guard duplicate >= 0, let directory = fdopendir(duplicate) else {
            if duplicate >= 0 { close(duplicate) }; throw Failure.io("enumerate")
        }
        defer { closedir(directory) }; rewinddir(directory)
        var names: Set<String> = []
        while true {
            errno = 0
            guard let entry = readdir(directory) else {
                if errno != 0 { throw Failure.io("enumerate-read") }; break
            }
            let name = withUnsafePointer(to: &entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: 256) { String(cString: $0) }
            }
            if name == "." || name == ".." { continue }
            let valid=rootName == "NGG2Cycles" ? isHex(name,count:32) :
                (name.count == 65 && name[name.index(name.startIndex,offsetBy:32)] == "-"
                    && isHex(String(name.prefix(32)),count:32) && isHex(String(name.suffix(32)),count:32))
            guard valid,names.count < 128 else { throw Failure.invalid("session-entry") }
            let child = openat(fd, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard child >= 0 else { throw Failure.invalid("session-entry") }
            do { try validateDirectory(child); close(child) } catch { close(child); throw error }
            names.insert(name)
        }
        return names
    }
    private static func continuousIdentity(_ provenance: [String: Any]) ->
        (root: String, index: Int, predecessor: String?, started: UInt64, deadline: UInt64)? {
        #if NG2_RUNTIME_HOST_TEST
        let duration=min(NG2CycleSpoolTestHooks.campaignDurationNS ?? 2_880_000_000_000,2_880_000_000_000)
        #else
        let duration:UInt64 = 2_880_000_000_000
        #endif
        guard duration > 0,let value = provenance["continuous_campaign"] as? [String: Any],
              Set(value.keys) == ["schema", "root_id", "index", "predecessor_id", "root_started_ns", "root_deadline_ns"],
              value["schema"] as? String == "ngg2-continuous-child-v1",
              let root = value["root_id"] as? String, isHex(root, count: 32),
              let index = unsigned(value["index"]), index < 128,
              let started = unsigned(value["root_started_ns"]), started > 0,
              started < UInt64(Int64.max) - duration,
              let deadline = unsigned(value["root_deadline_ns"]), deadline == started + duration else { return nil }
        let predecessor = value["predecessor_id"] as? String
        guard (index == 0 ? value["predecessor_id"] is NSNull : predecessor.map({ isHex($0,count:32) }) == true) else { return nil }
        return (root, Int(index), predecessor, started, deadline)
    }
    private static func reservationValue(_ value: [String: Any]) -> Reservation? {
        guard Set(value.keys) == ["schema", "root_id", "run_id", "index", "predecessor_id", "token_id", "slot_bytes"],
              value["schema"] as? String == "ngg2-continuation-reservation-v1",
              let root = value["root_id"] as? String, isHex(root,count:32),
              let run = value["run_id"] as? String, isHex(run,count:32),
              let token = value["token_id"] as? String, isHex(token,count:32),
              let index = unsigned(value["index"]), index < 128,
              unsigned(value["slot_bytes"]) == UInt64(CampaignQuota.slotBytes) else { return nil }
        let predecessor = value["predecessor_id"] as? String
        guard (index == 0 ? value["predecessor_id"] is NSNull : predecessor.map({ isHex($0,count:32) }) == true) else { return nil }
        return Reservation(tokenID:token,rootID:root,runID:run,index:Int(index),predecessorID:predecessor)
    }
    private func refreshCampaignUsage() throws {
        guard let quota=campaignQuota else { return }
        try quota.charge(runID:runID,writer:campaignWriter,usage:try storedUsage())
        if rootName == "NGG2Cycles" {
            for name in try Self.namespaceIDs(rootURL:supportURL,rootName:"NGG2RecoveryExports").sorted()
                where name.hasPrefix(runID+"-") {
                let ledger=try NG2CycleSpool(rootURL:supportURL,runID:runID,owner:"storage-only-failed-ledger",
                    recover:true,verifyRasters:false,rootName:"NGG2RecoveryExports",directoryName:name,
                    attachCampaignRecovery:false)
                try quota.charge(runID:runID,writer:ledger.campaignWriter,usage:try ledger.storedUsage())
            }
        }
    }
    private func storedUsage() throws -> CampaignUsage {
        try artifactEntries(hashes:false).reduce(CampaignUsage()) { current,ref in
            var value=current
            switch ref.role {
            case "raw":value.raw += ref.bytes
            case "png":value.png += ref.bytes
            case "uncommitted":value.temporary += ref.bytes
            default:value.metadata += ref.bytes
            }
            return value
        }
    }
    private func restoreCampaignAccounting() throws {
        guard let provenance=continuousProvenance,let identity=Self.continuousIdentity(provenance) else { return }
        let key=supportURL.standardizedFileURL.path + "/" + identity.root
        Self.recoveredQuotaGate.lock();defer { Self.recoveredQuotaGate.unlock() }
        if let cached=Self.recoveredQuotas[key]?.value { campaignQuota=cached;return }
        let quota=try CampaignQuota(rootURL:supportURL,rootID:identity.root,owner:"storage-only-recovery",storageOnly:true)
        var cohort:[String:NG2CycleSpool]=[:]
        for id in try Self.namespaceIDs(rootURL:supportURL).sorted() {
            let source=try NG2CycleSpool(rootURL:supportURL,runID:id,owner:"storage-only-scan",recover:true,
                verifyRasters:false,attachCampaignRecovery:false)
            guard let p=source.continuousProvenance,let child=Self.continuousIdentity(p),child.root == identity.root else { continue }
            guard source.ownerSHA256 == ownerSHA256 else { throw Failure.invalid("campaign-recovery-owner") }
            try quota.restore(runID:id,identity:child,writer:source.campaignWriter,usage:try source.storedUsage(),
                published:source.recordList.last?.kind == "published")
            cohort[id]=source
        }
        guard cohort[runID] != nil else { throw Failure.invalid("campaign-recovery-source") }
        for name in try Self.namespaceIDs(rootURL:supportURL,rootName:"NGG2RecoveryExports").sorted() {
            let id=String(name.prefix(32))
            guard cohort[id] != nil else { continue }
            let ledger=try NG2CycleSpool(rootURL:supportURL,runID:id,owner:"storage-only-ledger-scan",recover:true,
                verifyRasters:false,rootName:"NGG2RecoveryExports",directoryName:name,attachCampaignRecovery:false)
            try quota.charge(runID:id,writer:ledger.campaignWriter,usage:try ledger.storedUsage())
        }
        for source in cohort.values where source.recordList.last?.kind != "published" {
            if try source.verifiedRecoveryPublication() { quota.published(runID:source.runID) }
        }
        campaignQuota=quota;Self.recoveredQuotas[key]=WeakCampaignQuota(quota)
    }
    private func checkSpace(raw: Int, metadata requested: Int, png: Int = 0) throws {
        if let quota = campaignQuota {
            try quota.check(runID: runID, writer: campaignWriter,
                usage: CampaignUsage(raw: registered.count * Self.rasterBytes + raw,
                    metadata: metadataBytes + requested, png: pngBytes + png))
            return
        }

        #if canImport(Darwin)
        var value = statfs()
        guard fstatfs(directoryFD, &value) == 0 else { throw Failure.io("space") }
        let measuredAvailable = UInt64(value.f_bavail) * UInt64(value.f_bsize)
        #else
        var value = statvfs()
        guard fstatvfs(directoryFD, &value) == 0 else { throw Failure.io("space") }
        let measuredAvailable = UInt64(value.f_bavail) * UInt64(value.f_frsize)
        #endif
        #if NG2_RUNTIME_HOST_TEST
        let available = NG2CycleSpoolTestHooks.availableBytes ?? measuredAvailable
        #else
        let available = measuredAvailable
        #endif
        let futureRaw = reservedRawSlots * Self.rasterBytes
        let futurePNG = finalBudget?.manifest == true ? Self.maximumPNGBytes - pngBytes : 0
        let reserve = UInt64(raw + futureRaw + futurePNG
                             + max(requested, Self.maximumMetadataBytes - metadataBytes)
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
        committedSessionSHA256 = Self.sha(headerBytes)
        nativeProfile = (header["provenance"] as? [String: Any])?["native_profile"] as? String
        if let provenance=header["provenance"] as? [String:Any],provenance["continuous_campaign"] != nil {
            guard Self.continuousIdentity(provenance) != nil else { throw Failure.invalid("continuous-provenance") }
            continuousProvenance = provenance
        }
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
                if contentSealed && kind != "published" { throw Failure.invalid("sealed-control-record") }
                if kind == "continuation_reservation", continuousProvenance != nil {
                    guard let token=Self.reservationValue(payload),let provenance=continuousProvenance,
                          let identity=Self.continuousIdentity(provenance),token.rootID == identity.root,
                          token.index == identity.index+1,token.predecessorID == runID else {
                        throw Failure.invalid("continuation-reservation")
                    }
                }
                if kind == "continuation_seal", continuousProvenance != nil {
                    guard try validContinuationSeal(payload,prior:recordList.last) else { throw Failure.invalid("continuation-seal") }
                    contentSealed = true
                }
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
        if let provenance=value["provenance"] as? [String:Any],provenance["continuous_campaign"] != nil,
            continuousIdentity(provenance) == nil { return nil }
        if let provenance=value["provenance"] as? [String:Any],let identity=continuousIdentity(provenance),
            (identity.index == 0 ? identity.root != runID : identity.predecessor == runID) { return nil }
        return value
    }
    private static func regular(_ value: stat) -> Bool { value.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG) }
    private static func directory(_ value: stat) -> Bool { value.st_mode & mode_t(S_IFMT) == mode_t(S_IFDIR) }
    // Match the original OS-provided Application Support boundary. Its
    // enclosing app container is private; only our own child namespaces must
    // have mode0700. Do not reject an existing system-created support mode.
    private static func validateSupport(_ descriptor: Int32) throws {
        var value = stat()
        guard fstat(descriptor,&value) == 0,directory(value),value.st_uid == getuid() else {
            throw Failure.invalid("support")
        }
    }
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
            committedSessionSHA256=Self.sha(bytes)
            if let provenance=header["provenance"] as? [String:Any],Self.continuousIdentity(provenance) != nil {
                continuousProvenance=provenance
            }
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
        if continuousProvenance != nil {
            for name in names.sorted() where name.hasPrefix("png-") && name.hasSuffix(".json") {
                guard let bytes=try? read(name,maximum:Self.maximumMetadataBytes),
                      let value=(try? JSONSerialization.jsonObject(with:bytes)) as? [String:Any],
                      Set(value.keys) == ["schema","run_id","capture_id","png_sha256","png_bytes","metadata"],
                      value["schema"] as? String == "ngg2-cycle-png-v1",value["run_id"] as? String == runID,
                      let id=Self.unsigned(value["capture_id"]),let raw=registered[id],
                      let digest=value["png_sha256"] as? String,Self.isHex(digest,count:64),
                      let size=Self.unsigned(value["png_bytes"]),size > 0,size <= UInt64(Self.maximumExportTemporaryBytes),
                      let metadata=value["metadata"] as? [String:Any],metadata["raw_sha256"] as? String == raw.rawSHA256,
                      (try? Self.canonical(value)) == bytes,name == pngName(id,suffix:"json"),
                      names.contains(pngName(id,suffix:"png")),registeredPNGs.count < Self.maximumFrames,
                      Int(size) <= Self.maximumPNGBytes-pngBytes else { continue }
                if verifyRasters {
                    guard let png=try? read(pngName(id,suffix:"png"),maximum:Self.maximumExportTemporaryBytes),
                          (try? Self.validatePNG(png)) != nil,png.count == Int(size),Self.sha(png) == digest else { continue }
                }
                registeredPNGs[id]=PNGRef(captureID:id,sha256:digest,bytes:Int(size),
                    metadataSHA256:Self.sha(bytes),metadata:metadata)
                pngBytes += Int(size)
            }
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
            if kind == "continuation_seal",continuousProvenance != nil,
                (try? validContinuationSeal(payload,prior:recordList.last)) == true { contentSealed=true }
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
