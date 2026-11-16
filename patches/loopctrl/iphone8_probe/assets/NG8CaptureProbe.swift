import Foundation

// Isolated state core. Actual qualification/authentication, read-only evidence
// inspection, queues and the new capture bridge are trusted injected adapters.
// No UI, raster decoding/re-encoding, filesystem or legacy native API is used.
enum NG8ProbeLimits {
    static let schema = "ngg2-capture-probe-v1"
    static let serviceMode = "iphone8-capture-only-v1"
    static let acceptedIDs = 128
    static let terminalHistory = 64
    static let captureDeadlineNs: UInt64 = 2_000_000_000
    static let artifactTTLNs: UInt64 = 300_000_000_000
    static let jpegBytes = 8 * 1024 * 1024
    static let manifestBytes = 64 * 1024
    static let chunkBytes = 64 * 1024
    static let chunkWireBytes = 256 * 1024
    static let maximumAxis = 4096
    static let maximumPixels = 8_000_000
}

enum NG8ProbeFailure: String, Error {
    case notAvailable = "not_available", oldEvidenceBlocked = "old_evidence_blocked"
    case trustedLocalUnavailable = "trusted_local_unavailable", runtimeMismatch = "runtime_mismatch"
    case invalidRequest = "invalid_request", ownerInactive = "owner_inactive"
    case unavailable, consumedID = "consumed_id", limitReached = "limit_reached"
    case busyProbe = "busy_probe", deadline, prepareUnavailable = "prepare_unavailable"
    case apiUnavailable = "api_unavailable", requestUnavailable = "request_unavailable"
    case requestException = "request_exception", replyException = "reply_exception"
    case captureFailed = "capture_failed", bytesInvalid = "bytes_invalid"
    case jpegInvalid = "jpeg_invalid", metadataInvalid = "metadata_invalid"
    case producerViolation = "producer_violation", cancelled, expired
}

enum NG8ProbeState: String { case accepted, preparing, capturing, ready, cancelled, failed, expired }
enum NG8ProbeOldEvidence: String { case clean, blocked }
enum NG8ProbeOwnerState { case active, paused, inactive }

// Owner is injected by the authenticated adapter; no wire parser creates it.
struct NG8ProbeOwner: Hashable { let tokenIdentity: String }
struct NG8ProbeKey: Equatable { let runtimeID: String; let probeID: String }

struct NG8ProbeTicket: Equatable {
    let key: NG8ProbeKey
    let generation: UInt64
    let cancelEpoch: UInt64
    let owner: NG8ProbeOwner
    let acceptedNs: UInt64
    let deadlineNs: UInt64
}

struct NG8ProbeStatus {
    let runtimeID: String
    let oldEvidenceGate: NG8ProbeOldEvidence
    let probeID: String?
    let generation: UInt64?
    let cancelEpoch: UInt64?
    let state: NG8ProbeState?
    let failure: NG8ProbeFailure?
    let clockID: String
    let acceptedNs: UInt64?
    let deadlineNs: UInt64?
    let requestStartNs: UInt64?
    // Wire callback_body_handoff_ns: owned getter/copy/reply-consumer handoff,
    // never proof of the daemon block's literal stack return/internal cleanup.
    let callbackEndNs: UInt64?
    let callbackReturnVerified = false
    let readyExpiryNs: UInt64?
    let draining: Bool
    let leaseHeld: Bool
}

struct NG8ProbeJPEGMetadata: Equatable {
    let width: Int
    let height: Int
    // ImageIO metadata only: missing remains nil; no orientation transform.
    let exifOrientation: Int?
}

struct NG8ProbeManifest {
    let key: NG8ProbeKey
    let generation: UInt64
    let clockID: String
    let byteLength: Int
    let sha256: String
    let metadata: NG8ProbeJPEGMetadata
    let acceptedNs: UInt64
    let deadlineNs: UInt64
    let requestStartNs: UInt64
    // Same final owned-work handoff meaning as status.callbackEndNs.
    let callbackEndNs: UInt64
    let callbackReturnVerified = false
    let readyExpiryNs: UInt64
    let sourceAPI = "XCTScreenshotRequest"
    let requestedUTI = "public.jpeg"
    let requestedQuality = 0.6
    let format = "jpeg"
    let scope = "screen"
    let inputAuthorized = false
    let inputGeometryVerified = false
    let normalizationApplied = false
    let deviceCaptureNs: UInt64? = nil
    let freshnessVerified = false
}

struct NG8ProbeChunk {
    let key: NG8ProbeKey
    let generation: UInt64
    let sha256: String
    let offset: UInt64
    let byteLength: Int
    let data: Data
}

enum NG8ProbeCommand: Equatable {
    case status(NG8ProbeKey?)
    case start(NG8ProbeKey)
    case cancel(NG8ProbeKey)
    case manifest(NG8ProbeKey)
    case chunk(NG8ProbeKey, sha256: String, offset: UInt64, limit: Int)
}

enum NG8ProbeWire {
    static func hex(_ value: String, count: Int) -> Bool {
        let bytes = value.utf8
        return bytes.count == count && bytes.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    private static func integer(_ value: Any?) -> UInt64? {
        guard let number = value as? NSNumber,
              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: number.objCType))
        else { return nil }
        let text = number.stringValue
        guard !text.isEmpty && text.utf8.allSatisfy({ (48...57).contains($0) }) else { return nil }
        return UInt64(text)
    }

    // Qualification and owner are never decoded from caller fields.
    static func decode(method: String, params: [String: Any]) -> Result<NG8ProbeCommand, NG8ProbeFailure> {
        if method == "necro_capture_probe_status" && params.isEmpty { return .success(.status(nil)) }
        guard let runtime = params["runtime_id"] as? String, hex(runtime, count: 32),
              let probe = params["probe_id"] as? String, hex(probe, count: 32)
        else { return .failure(.invalidRequest) }
        let key = NG8ProbeKey(runtimeID: runtime, probeID: probe)
        let identity: Set<String> = ["runtime_id", "probe_id"]
        switch method {
        case "necro_capture_probe_status" where Set(params.keys) == identity:
            return .success(.status(key))
        case "necro_capture_probe_start" where Set(params.keys) == identity:
            return .success(.start(key))
        case "necro_capture_probe_cancel" where Set(params.keys) == identity:
            return .success(.cancel(key))
        case "necro_capture_probe_results":
            if params["mode"] as? String == "manifest",
               Set(params.keys) == identity.union(["mode"]) { return .success(.manifest(key)) }
            guard params["mode"] as? String == "chunk",
                  Set(params.keys) == identity.union(["mode", "sha256", "offset", "limit"]),
                  let hash = params["sha256"] as? String, hex(hash, count: 64),
                  let offset = integer(params["offset"]), let limit = integer(params["limit"]),
                  limit >= 1 && limit <= UInt64(NG8ProbeLimits.chunkBytes)
            else { return .failure(.invalidRequest) }
            return .success(.chunk(key, sha256: hash, offset: offset, limit: Int(limit)))
        default: return .failure(.invalidRequest)
        }
    }
}

protocol NG8ProbeClock: AnyObject {
    // Trusted intrinsic monotonic read: no side effects, blocking, lock taking,
    // reentry or callbacks. It may be sampled while the state lock is held.
    var nowNs: UInt64 { get }
    var clockID: String { get }
}

protocol NG8ProbeWatch: AnyObject { func cancel() }

protocol NG8ProbeScheduler: AnyObject {
    // `returned` means the actual owned body has returned, not that it was
    // queued or its reply was delivered. Production adapters use finally/defer.
    func enqueueMain(_ body: @escaping () -> Void, returned: @escaping () -> Void)
    func enqueueWorker(_ body: @escaping () -> Void, returned: @escaping () -> Void)
    // Bridge receivers only enqueue; no inline AX/hash/metadata/wait/core lock.
    // FIFO/serial and nonblocking; never execute the body inline. This receiving
    // owned job has a separate actual-return notification.
    func enqueueCoordinator(_ body: @escaping () -> Void, returned: @escaping () -> Void)
    func watch(at deadlineNs: UInt64, fired: @escaping () -> Void) -> NG8ProbeWatch
}

protocol NG8ProbeCaptureDriver: AnyObject {
    // Called only inside the owned main job. This is descriptor prepare only.
    func prepare(_ ticket: NG8ProbeTicket) -> Result<Void, NG8ProbeFailure>
    // The trusted bridge emits each notification at most once. `reply` supplies
    // a candidate; it does not prove worker/callback drain.
    // `drained` is the final owned data/getter/copy/primary-consumer handoff
    // after send-unwind, not a post-return daemon ACK. Its receiver only enqueues;
    // receiving coordinator-job return is tracked separately. Literal callback
    // return remains unverified. Synthetic error/function return is no handoff.
    func request(_ ticket: NG8ProbeTicket,
                 reply: @escaping (Result<Data, NG8ProbeFailure>) -> Void,
                 drained: @escaping () -> Void)
}

final class NG8CaptureProbe {
    let runtimeID: String
    let qualified: Bool
    let inputAuthorized = false
    private let clock: NG8ProbeClock
    private let scheduler: NG8ProbeScheduler
    private let driver: NG8ProbeCaptureDriver
    private let ownerState: (NG8ProbeOwner) -> NG8ProbeOwnerState
    private let oldEvidenceGate: () -> NG8ProbeOldEvidence
    private let inspectJPEG: (Data) -> Result<NG8ProbeJPEGMetadata, NG8ProbeFailure>
    private let sha256: (Data) -> String
    private let lock = NSLock()
    private let clockIdentifier: String
    private typealias Effects = [() -> Void]

    private struct Artifact {
        let bytes: Data
        let metadata: NG8ProbeJPEGMetadata
        let hash: String
    }
    private struct Authorization {
        let state: NG8ProbeOwnerState
        let revision: UInt64
    }
    private final class Record {
        let ticket: NG8ProbeTicket
        let ownerRevision: UInt64
        var state = NG8ProbeState.accepted
        var failure: NG8ProbeFailure?
        var cancelEpoch: UInt64 = 0
        var cancelRecorded = false
        var mainOutstanding = true
        var workerOutstanding = false
        var bridgeOutstanding = false
        var replyOutstanding = false
        var handoffOutstanding = false
        var replyClaimed = false
        var handoffClaimed = false
        var requestNs: UInt64?
        var handoffNs: UInt64?
        var expiryNs: UInt64?
        var artifact: Artifact?
        var captureWatch: NG8ProbeWatch?
        var expiryWatch: NG8ProbeWatch?
        var archived = false
        init(_ ticket: NG8ProbeTicket, ownerRevision: UInt64) {
            self.ticket = ticket; self.ownerRevision = ownerRevision
        }
    }
    // Claimed and read only while holding the same state lock. Duplicate jobs
    // never decrement the first job's reserved outstanding flag.
    private final class Claim { var accepted = false }
    private var records: [String: Record] = [:]
    private var seen: [String: NG8ProbeOwner] = [:]
    private var history: [String] = []
    private var current: Record?
    private var producerBlocked = false
    private var ownerRevision: UInt64 = 0

    init(qualified: Bool = false,
         runtimeID: String = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
         clock: NG8ProbeClock, scheduler: NG8ProbeScheduler, driver: NG8ProbeCaptureDriver,
         ownerState: @escaping (NG8ProbeOwner) -> NG8ProbeOwnerState,
         oldEvidenceGate: @escaping () -> NG8ProbeOldEvidence,
         inspectJPEG: @escaping (Data) -> Result<NG8ProbeJPEGMetadata, NG8ProbeFailure>,
         sha256: @escaping (Data) -> String) {
        self.qualified = qualified
        self.runtimeID = runtimeID
        self.clock = clock
        self.scheduler = scheduler
        self.driver = driver
        self.ownerState = ownerState
        self.oldEvidenceGate = oldEvidenceGate
        self.inspectJPEG = inspectJPEG
        self.sha256 = sha256
        self.clockIdentifier = clock.clockID
    }

    private func update<T>(_ body: (inout Effects) -> T) -> T {
        lock.lock()
        var effects: Effects = []
        let result = body(&effects)
        lock.unlock()
        // Queues/watch cancellation and all injected work are outside the lock.
        for effect in effects { effect() }
        return result
    }

    private func authorization(_ owner: NG8ProbeOwner) -> Authorization {
        let revision: UInt64 = update { _ in ownerRevision }
        // Auth reads remain outside the core lock. A concurrent ownerChanged
        // invalidates this sample before admission/commit, even for a new ID.
        return Authorization(state: ownerState(owner), revision: revision)
    }

    private func identityFailure(_ key: NG8ProbeKey) -> NG8ProbeFailure? {
        if !NG8ProbeWire.hex(key.runtimeID, count: 32) || !NG8ProbeWire.hex(key.probeID, count: 32) {
            return .invalidRequest
        }
        return key.runtimeID == runtimeID ? nil : .runtimeMismatch
    }

    private func draining(_ record: Record) -> Bool {
        record.mainOutstanding || record.workerOutstanding || record.bridgeOutstanding ||
            record.replyOutstanding || record.handoffOutstanding
    }

    private func lease(_ record: Record) -> Bool { record.artifact != nil || draining(record) }

    private func snapshot(_ record: Record?, gate: NG8ProbeOldEvidence = .clean) -> NG8ProbeStatus {
        NG8ProbeStatus(runtimeID: runtimeID, oldEvidenceGate: gate,
            probeID: record?.ticket.key.probeID, generation: record?.ticket.generation,
            cancelEpoch: record?.cancelEpoch, state: record?.state, failure: record?.failure,
            clockID: clockIdentifier, acceptedNs: record?.ticket.acceptedNs,
            deadlineNs: record?.ticket.deadlineNs, requestStartNs: record?.requestNs,
            callbackEndNs: record?.handoffNs, readyExpiryNs: record?.expiryNs,
            draining: record.map { draining($0) } ?? false, leaseHeld: record.map { lease($0) } ?? false)
    }

    // Must be called under lock. Tombstones retain owner binding independently
    // of the last 64 terminal records, so foreign callers cannot read them.
    private func lookup(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<Record, NG8ProbeFailure> {
        guard let acceptedOwner = seen[key.probeID] else { return .failure(.unavailable) }
        guard acceptedOwner == owner else { return .failure(.unavailable) }
        guard let record = records[key.probeID] else { return .failure(.consumedID) }
        return .success(record)
    }

    private func matching(_ ticket: NG8ProbeTicket) -> Record? {
        guard let record = records[ticket.key.probeID], record.ticket == ticket else { return nil }
        return record
    }

    private func stopCaptureWatch(_ record: Record, effects: inout Effects) {
        if let watch = record.captureWatch { effects.append { watch.cancel() }; record.captureWatch = nil }
    }

    private func archive(_ record: Record) {
        guard !record.archived else { return }
        record.archived = true
        history.append(record.ticket.key.probeID)
        while history.count > NG8ProbeLimits.terminalHistory {
            let retired = history.removeFirst()
            if let item = records[retired], !lease(item) { records.removeValue(forKey: retired) }
        }
    }

    private func fail(_ record: Record, _ reason: NG8ProbeFailure, effects: inout Effects) {
        guard record.failure == nil else { return }
        record.failure = reason
        record.state = reason == .cancelled ? .cancelled : (reason == .expired ? .expired : .failed)
        record.artifact = nil
        stopCaptureWatch(record, effects: &effects)
        if let watch = record.expiryWatch { effects.append { watch.cancel() }; record.expiryWatch = nil }
        archive(record)
    }

    @discardableResult
    private func refresh(_ record: Record, now: UInt64, auth: Authorization,
                         effects: inout Effects) -> Bool {
        guard record.failure == nil else { return false }
        if producerBlocked { fail(record, .producerViolation, effects: &effects); return false }
        if auth.state != .active || auth.revision != ownerRevision || record.ownerRevision != ownerRevision {
            fail(record, .ownerInactive, effects: &effects); return false
        }
        if record.state == .ready {
            if let expiry = record.expiryNs, now >= expiry {
                fail(record, .expired, effects: &effects); return false
            }
        } else if now < record.ticket.acceptedNs || now >= record.ticket.deadlineNs {
            fail(record, .deadline, effects: &effects); return false
        }
        return record.cancelEpoch == record.ticket.cancelEpoch
    }

    private func finish(_ record: Record, now: UInt64, auth: Authorization,
                        effects: inout Effects) {
        guard refresh(record, now: now, auth: auth, effects: &effects),
              record.state != .ready, !draining(record), record.artifact != nil,
              let request = record.requestNs, let handoff = record.handoffNs else { return }
        guard request >= record.ticket.acceptedNs, handoff >= request, handoff <= now else {
            fail(record, .metadataInvalid, effects: &effects); return
        }
        let expiry = now.addingReportingOverflow(NG8ProbeLimits.artifactTTLNs)
        guard !expiry.overflow else { fail(record, .metadataInvalid, effects: &effects); return }
        record.state = .ready
        record.expiryNs = expiry.partialValue
        stopCaptureWatch(record, effects: &effects)
        let ticket = record.ticket, deadline = expiry.partialValue
        effects.append { self.armWatch(ticket, deadline: deadline, expiry: true) }
    }

    private func armWatch(_ ticket: NG8ProbeTicket, deadline: UInt64, expiry: Bool) {
        let watch = scheduler.watch(at: deadline) { self.watchFired(ticket, expiry: expiry) }
        update { effects in
            guard let record = matching(ticket), record.failure == nil,
                  (expiry ? record.state == .ready : record.state != .ready) else {
                effects.append { watch.cancel() }; return
            }
            if expiry { record.expiryWatch = watch } else { record.captureWatch = watch }
        }
    }

    private func watchFired(_ ticket: NG8ProbeTicket, expiry: Bool) {
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard let record = matching(ticket), record.failure == nil else { return }
            // A late acquisition watchdog must never invalidate ready bytes.
            if expiry {
                guard record.state == .ready, let end = record.expiryNs, now >= end else { return }
            } else {
                guard record.state != .ready, now >= ticket.deadlineNs else { return }
            }
            refresh(record, now: now, auth: auth, effects: &effects)
        }
    }

    func start(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        guard qualified, NG8ProbeWire.hex(runtimeID, count: 32), !clockIdentifier.isEmpty,
              clockIdentifier.utf8.count <= 128 else { return .failure(.notAvailable) }
        if let reason = identityFailure(key) { return .failure(reason) }
        let gate = oldEvidenceGate(), auth = authorization(owner)
        guard auth.state == .active && !owner.tokenIdentity.isEmpty else { return .failure(.ownerInactive) }
        return update { effects in
            let now = clock.nowNs
            guard auth.revision == ownerRevision else { return .failure(.ownerInactive) }
            let deadline = now.addingReportingOverflow(NG8ProbeLimits.captureDeadlineNs)
            guard !deadline.overflow else { return .failure(.invalidRequest) }
            if seen[key.probeID] != nil {
                switch lookup(key, owner: owner) {
                case .failure(let reason): return .failure(reason)
                case .success(let record):
                    refresh(record, now: now, auth: auth, effects: &effects)
                    return .success(snapshot(record, gate: gate))
                }
            }
            guard !producerBlocked else { return .failure(.producerViolation) }
            guard gate == .clean else { return .failure(.oldEvidenceBlocked) }
            guard current.map({ !lease($0) }) ?? true else { return .failure(.busyProbe) }
            guard seen.count < NG8ProbeLimits.acceptedIDs else { return .failure(.limitReached) }
            let ticket = NG8ProbeTicket(key: key, generation: UInt64(seen.count + 1), cancelEpoch: 0,
                owner: owner, acceptedNs: now, deadlineNs: deadline.partialValue)
            let record = Record(ticket, ownerRevision: ownerRevision)
            seen[key.probeID] = owner; records[key.probeID] = record; current = record
            // Reserve main ownership before any external scheduler can reenter.
            effects.append { self.armWatch(ticket, deadline: ticket.deadlineNs, expiry: false) }
            effects.append {
                self.scheduler.enqueueMain({ self.prepare(ticket) }, returned: { self.mainReturned(ticket) })
            }
            return .success(snapshot(record, gate: gate))
        }
    }

    func status(_ key: NG8ProbeKey?, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        guard qualified else { return .failure(.notAvailable) }
        let gate = oldEvidenceGate()
        guard let key = key else { return .success(snapshot(nil, gate: gate)) }
        if let reason = identityFailure(key) { return .failure(reason) }
        let auth = authorization(owner)
        return update { effects in
            let now = clock.nowNs
            switch lookup(key, owner: owner) {
            case .failure(let reason): return .failure(reason)
            case .success(let record):
                refresh(record, now: now, auth: auth, effects: &effects)
                return .success(snapshot(record, gate: gate))
            }
        }
    }

    func cancel(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        guard qualified else { return .failure(.notAvailable) }
        if let reason = identityFailure(key) { return .failure(reason) }
        let auth = authorization(owner)
        return update { effects in
            let now = clock.nowNs
            switch lookup(key, owner: owner) {
            case .failure(let reason): return .failure(reason)
            case .success(let record):
                refresh(record, now: now, auth: auth, effects: &effects)
                if !record.cancelRecorded {
                    record.cancelRecorded = true
                    record.cancelEpoch += 1
                }
                fail(record, .cancelled, effects: &effects)
                return .success(snapshot(record))
            }
        }
    }

    private func prepare(_ ticket: NG8ProbeTicket) {
        let auth = authorization(ticket.owner)
        let admitted = update { effects -> Bool in
            let now = clock.nowNs
            guard let record = matching(ticket),
                  refresh(record, now: now, auth: auth, effects: &effects) else { return false }
            record.state = .preparing
            return true
        }
        guard admitted else { return }
        let result = driver.prepare(ticket)
        let nextAuth = authorization(ticket.owner)
        update { effects in
            let after = clock.nowNs
            guard let record = matching(ticket),
                  refresh(record, now: after, auth: nextAuth, effects: &effects) else { return }
            switch result {
            case .failure(let reason): fail(record, reason, effects: &effects)
            case .success:
                record.workerOutstanding = true
                effects.append {
                    self.scheduler.enqueueWorker({ self.request(ticket) }, returned: { self.workerReturned(ticket) })
                }
            }
        }
    }

    private func mainReturned(_ ticket: NG8ProbeTicket) {
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard let record = matching(ticket), record.mainOutstanding else { return }
            record.mainOutstanding = false
            finish(record, now: now, auth: auth, effects: &effects)
        }
    }

    private func request(_ ticket: NG8ProbeTicket) {
        let auth = authorization(ticket.owner)
        let admitted = update { effects -> Bool in
            let now = clock.nowNs
            guard let record = matching(ticket),
                  refresh(record, now: now, auth: auth, effects: &effects) else { return false }
            record.state = .capturing; record.requestNs = now
            // Install both receive-job tickets before a synchronous bridge reply.
            record.bridgeOutstanding = true
            record.replyOutstanding = true; record.handoffOutstanding = true
            return true
        }
        guard admitted else { return }
        driver.request(ticket, reply: { result in
            // Callback receiver: enqueue only, no state lock/inspection/hash.
            let claim = Claim()
            self.scheduler.enqueueCoordinator({
                self.receiveReply(ticket, result: result, claim: claim)
            }, returned: { self.receiveReturned(ticket, claim: claim, handoff: false) })
        }, drained: {
            let handoffNs = self.clock.nowNs
            let claim = Claim()
            self.scheduler.enqueueCoordinator({
                self.receiveHandoff(ticket, at: handoffNs, claim: claim)
            }, returned: { self.receiveReturned(ticket, claim: claim, handoff: true) })
        })
    }

    private func workerReturned(_ ticket: NG8ProbeTicket) {
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard let record = matching(ticket), record.workerOutstanding else { return }
            record.workerOutstanding = false
            finish(record, now: now, auth: auth, effects: &effects)
        }
    }

    private func receiveReply(_ ticket: NG8ProbeTicket, result: Result<Data, NG8ProbeFailure>, claim: Claim) {
        let auth = authorization(ticket.owner)
        let admitted = update { effects -> Bool in
            let now = clock.nowNs
            guard let record = matching(ticket), !record.replyClaimed else { return false }
            record.replyClaimed = true; claim.accepted = true
            return refresh(record, now: now, auth: auth, effects: &effects)
        }
        guard admitted else { return }
        let bytes: Data
        switch result {
        case .failure(let reason):
            completeInspection(ticket, result: .failure(reason)); return
        case .success(let candidate):
            guard !candidate.isEmpty && candidate.count <= NG8ProbeLimits.jpegBytes else {
                completeInspection(ticket, result: .failure(.bytesInvalid)); return
            }
            bytes = candidate
        }
        // These potentially expensive injected operations never hold the lock.
        let metadata: NG8ProbeJPEGMetadata
        switch inspectJPEG(bytes) {
        case .failure(let reason): completeInspection(ticket, result: .failure(reason)); return
        case .success(let candidate):
            guard candidate.width > 0, candidate.height > 0,
                  candidate.width <= NG8ProbeLimits.maximumAxis, candidate.height <= NG8ProbeLimits.maximumAxis,
                  candidate.width * candidate.height <= NG8ProbeLimits.maximumPixels,
                  candidate.exifOrientation.map({ (1...8).contains($0) }) ?? true else {
                completeInspection(ticket, result: .failure(.metadataInvalid)); return
            }
            metadata = candidate
        }
        let nextAuth = authorization(ticket.owner)
        let stillActive = update { effects -> Bool in
            let afterInspect = clock.nowNs
            guard let record = matching(ticket) else { return false }
            return refresh(record, now: afterInspect, auth: nextAuth, effects: &effects)
        }
        guard stillActive else { return }
        let hash = sha256(bytes)
        guard NG8ProbeWire.hex(hash, count: 64) else {
            completeInspection(ticket, result: .failure(.bytesInvalid)); return
        }
        completeInspection(ticket, result: .success(Artifact(bytes: bytes, metadata: metadata, hash: hash)))
    }

    private func completeInspection(_ ticket: NG8ProbeTicket, result: Result<Artifact, NG8ProbeFailure>) {
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard let record = matching(ticket),
                  refresh(record, now: now, auth: auth, effects: &effects) else { return }
            switch result {
            case .failure(let reason): fail(record, reason, effects: &effects)
            case .success(let artifact): record.artifact = artifact
            }
            // Publication still waits for this job's actual returned callback.
        }
    }

    private func receiveHandoff(_ ticket: NG8ProbeTicket, at timestamp: UInt64, claim: Claim) {
        update { _ in
            guard let record = matching(ticket), !record.handoffClaimed else { return }
            record.handoffClaimed = true; claim.accepted = true
            record.handoffNs = timestamp
        }
    }

    private func receiveReturned(_ ticket: NG8ProbeTicket, claim: Claim, handoff: Bool) {
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard claim.accepted, let record = matching(ticket) else { return }
            claim.accepted = false
            if handoff {
                record.handoffOutstanding = false; record.bridgeOutstanding = false
            } else { record.replyOutstanding = false }
            finish(record, now: now, auth: auth, effects: &effects)
        }
    }

    func manifest(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeManifest, NG8ProbeFailure> {
        guard qualified else { return .failure(.notAvailable) }
        if let reason = identityFailure(key) { return .failure(reason) }
        let auth = authorization(owner)
        return update { effects in
            let now = clock.nowNs
            switch lookup(key, owner: owner) {
            case .failure(let reason): return .failure(reason)
            case .success(let record):
                guard refresh(record, now: now, auth: auth, effects: &effects) else {
                    return .failure(record.failure ?? .ownerInactive)
                }
                guard record.state == .ready, !draining(record), let artifact = record.artifact,
                      let request = record.requestNs, let handoff = record.handoffNs,
                      let expiry = record.expiryNs else { return .failure(.unavailable) }
                return .success(NG8ProbeManifest(key: key, generation: record.ticket.generation,
                    clockID: clockIdentifier, byteLength: artifact.bytes.count, sha256: artifact.hash,
                    metadata: artifact.metadata, acceptedNs: record.ticket.acceptedNs,
                    deadlineNs: record.ticket.deadlineNs, requestStartNs: request,
                    callbackEndNs: handoff, readyExpiryNs: expiry))
            }
        }
    }

    func chunk(_ key: NG8ProbeKey, owner: NG8ProbeOwner, sha256: String,
               offset: UInt64, limit: Int) -> Result<NG8ProbeChunk, NG8ProbeFailure> {
        guard qualified else { return .failure(.notAvailable) }
        if let reason = identityFailure(key) { return .failure(reason) }
        guard limit >= 1 && limit <= NG8ProbeLimits.chunkBytes,
              NG8ProbeWire.hex(sha256, count: 64) else { return .failure(.invalidRequest) }
        let end = offset.addingReportingOverflow(UInt64(limit))
        guard !end.overflow else { return .failure(.invalidRequest) }
        let auth = authorization(owner)
        return update { effects in
            let now = clock.nowNs
            switch lookup(key, owner: owner) {
            case .failure(let reason): return .failure(reason)
            case .success(let record):
                guard refresh(record, now: now, auth: auth, effects: &effects) else {
                    return .failure(record.failure ?? .ownerInactive)
                }
                guard record.state == .ready, !draining(record), let artifact = record.artifact
                else { return .failure(.unavailable) }
                let length = UInt64(artifact.bytes.count)
                guard sha256 == artifact.hash, offset < length else { return .failure(.invalidRequest) }
                let stop = min(end.partialValue, length)
                let bytes = artifact.bytes.subdata(in: Int(offset)..<Int(stop))
                return .success(NG8ProbeChunk(key: key, generation: record.ticket.generation,
                    sha256: artifact.hash, offset: offset, byteLength: artifact.bytes.count, data: bytes))
            }
        }
    }

    func ownerChanged() {
        let ticket: NG8ProbeTicket? = update { effects in
            let revision = ownerRevision.addingReportingOverflow(1)
            if revision.overflow {
                producerBlocked = true
                if let record = current { fail(record, .producerViolation, effects: &effects) }
            } else {
                ownerRevision = revision.partialValue
            }
            return current?.ticket
        }
        guard let ticket = ticket else { return }
        let auth = authorization(ticket.owner)
        update { effects in
            let now = clock.nowNs
            guard let record = matching(ticket) else { return }
            refresh(record, now: now, auth: auth, effects: &effects)
        }
    }

    func producerViolation() {
        update { effects in
            producerBlocked = true
            if let record = current { fail(record, .producerViolation, effects: &effects) }
        }
    }
}
