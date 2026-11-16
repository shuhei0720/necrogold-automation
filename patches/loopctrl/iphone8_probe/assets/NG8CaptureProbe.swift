import Foundation

// TDD baseline only. No capture, queue, filesystem or device API is invoked.
// The qualified happy path intentionally remains unavailable until an actual
// macOS assertion Red is reported. Do not wire this stub into a product build.
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
    // Future closed parser: exactly the four planned RPCs/params, including
    // strict non-Boolean integer ranges. Qualification/owner are never params.
    static func decode(method: String, params: [String: Any]) -> Result<NG8ProbeCommand, NG8ProbeFailure> {
        .failure(.notAvailable)
    }
}

protocol NG8ProbeClock: AnyObject {
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
    // This receiving owned job has a separate actual-return notification.
    func enqueueCoordinator(_ body: @escaping () -> Void, returned: @escaping () -> Void)
    func watch(at deadlineNs: UInt64, fired: @escaping () -> Void) -> NG8ProbeWatch
}

protocol NG8ProbeCaptureDriver: AnyObject {
    // Called only inside the owned main job. This is descriptor prepare only.
    func prepare(_ ticket: NG8ProbeTicket) -> Result<Void, NG8ProbeFailure>
    // `reply` supplies a candidate; it does not prove worker/callback drain.
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
    // Future state/ID/raw mutation shares one lock; external hooks run outside it.
    private let lock = NSLock()

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
    }

    func start(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        .failure(.notAvailable)
    }

    func status(_ key: NG8ProbeKey?, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        .failure(.notAvailable)
    }

    func cancel(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeStatus, NG8ProbeFailure> {
        .failure(.notAvailable)
    }

    func manifest(_ key: NG8ProbeKey, owner: NG8ProbeOwner) -> Result<NG8ProbeManifest, NG8ProbeFailure> {
        .failure(.notAvailable)
    }

    func chunk(_ key: NG8ProbeKey, owner: NG8ProbeOwner, sha256: String,
               offset: UInt64, limit: Int) -> Result<NG8ProbeChunk, NG8ProbeFailure> {
        .failure(.notAvailable)
    }

    func ownerChanged() {}
    func producerViolation() {}
}
