import Foundation
import CoreFoundation
import CoreGraphics
#if !NG2_RUNTIME_HOST_TEST
import XCTest
import UIKit
import UserNotifications
#endif
import CryptoKit

#if NG2_RUNTIME_HOST_TEST
enum NG2RuntimeTestHooks {
    static var clock: (() -> UInt64)?
    static var beforeCaptureAdmission: (() -> Void)?
    static var beforeMainAdmission: (() -> Void)?
    static var beforeMainAuthority: (() -> Void)?
    static var beforeAnalysisCommit: (() -> Void)?
    static var beforeCaptureDecode: ((UInt64) -> Void)?
    static var beforeAnalysisFrameCommit: ((UInt64, UInt64, UInt64, UInt64, Bool) -> Void)?
    static var afterForegroundQuery: (() -> Void)?
    static var beforeControlTick: (() -> Void)?
    static var scheduleTicket: ((UInt64, @escaping () -> Void) -> Bool)?
    static var afterTicketReturned: ((UInt64) -> Void)?
    static var afterCaptureDrainProcessed: ((String) -> Void)?
    static var beforeCaptureFailureCommit: ((String) -> Void)?
    static var analysisRGBA: ((Data) -> Data)?
    static var afterWatchdogCheck: ((String, UInt64) -> Void)?
    static var afterCaptureBackendReply: ((UInt64) -> Void)?
    static var beforeCaptureControlConsume: ((UInt64) -> Void)?
    static var beforeReportEncode: ((String, UInt64) -> Void)?
    static var beforeDueDispatch: ((UInt64) -> Void)?
    static var beforeEvidenceRetention: ((UInt64) -> Void)?
}
enum NG2RuntimeContinuousTestHooks {
    // One HOST-only oracle supplies both the Runtime bound and Spool's
    // provenance validator. Release builds keep the exact 2880s contract.
    static var rootDurationNS: UInt64? {
        get { NG2CycleSpoolTestHooks.campaignDurationNS }
        set { NG2CycleSpoolTestHooks.campaignDurationNS = newValue }
    }
    static var failCoreCreation = false
    static var afterPersistenceEnqueueBeforeReturn: ((String, String) -> Void)?
    static var beforePersistenceCommitReturn: ((String, String) -> Void)?
    static var afterSealEnqueueBeforeReturn: ((String) -> Void)?
    static var beforeSealCommitReturn: ((String) -> Void)?
    static var afterCaptureThreadEnqueueBeforeReturn: ((String) -> Void)?
    static var beforeSuccessorCommit: ((String, String, String) -> Void)?
    static var afterChildAdmitted: ((String, String, String, Int) -> Void)?
    static var beforeBootstrapAdmission: ((String, Int) -> Void)?
}
#endif

private extension NSLock {
    func ng2Locked<T>(_ body: () -> T) -> T { lock(); defer { unlock() }; return body() }
}

// NG2Scene contains a 23,296-byte imported C tuple. Keep its storage on
// the heap so an unoptimized capture-thread stack never copies that tuple
// through every Frame/Optional/closure temporary. Only the capture worker
// writes it, before publishing the immutable Frame; observe copies from const.
private final class NG2Analysis {
    let scene = UnsafeMutablePointer<NG2Scene>.allocate(capacity: 1)
    var irregular = NG2IrregularObservation()
    init() { scene.initialize(to: NG2Scene()) }
    deinit { scene.deinitialize(count: 1); scene.deallocate() }
}

private struct NG2Frame {
    let id: UInt64
    let start: UInt64
    let end: UInt64
    let decodeEnd: UInt64
    let generation: UInt64
    let analysisStart: UInt64
    let analysisEnd: UInt64
    let analysis: NG2Analysis
    let startPrefix: UInt64
    let prefix: UInt64
    let startInFlight: Bool
    let endInFlight: Bool
    let stable: Bool
    let rgba: Data
    let rasterTrace: NG2Raster.Trace
    let encodedBytes: Int
    let diagnosticOrientation: Int?
}

// One explicit finite native campaign. The cancel flag has a short separate
// gate: cancellation never waits for a gesture or a disk fsync to return.
// Child replacement and the metadata index use gate; no I/O holds that gate.
private final class NG2ContinuousCampaign {
    struct Child {
        let id: String, predecessor: String?
        let index: Int
        var state = "accepted"
        var seal: String?
        var reason: Int32 = 0
    }
    let gate = NSLock(), cancelGate = NSLock()
    let id, owner: String
    let started, deadline: UInt64
    let quota: NG2CycleSpool.CampaignQuota
    var children: [Child]
    weak var active: NG2Run?
    var next: NG2CycleSpool.Reservation?
    var heartbeat: UInt64
    var reason = "none"
    var stopped = false, lease = true, pendingIO = false
    var terminalSafety: (Int32, Bool, Bool)?
    private var cancellation: Int32 = 0
    init(id: String, owner: String, now: UInt64, quota: NG2CycleSpool.CampaignQuota) {
        self.id = id; self.owner = owner; started = now
        #if NG2_RUNTIME_HOST_TEST
        deadline = now + min(NG2RuntimeContinuousTestHooks.rootDurationNS ?? 2_880_000_000_000, 2_880_000_000_000)
        #else
        deadline = now + 2_880_000_000_000
        #endif
        heartbeat = now; self.quota = quota
        children = [Child(id: id, predecessor: nil, index: 0)]
    }
    var cancelReason: Int32 { cancelGate.ng2Locked { cancellation } }
    func requestCancel(_ reason: Int32) {
        cancelGate.ng2Locked { if cancellation == 0 { cancellation = reason } }
    }
    func permits(_ now: UInt64) -> Bool {
        now >= started && now < deadline && cancelReason == 0
    }
    func commitIfAllowed(_ now: UInt64, _ body: () -> Bool) -> Bool {
        cancelGate.ng2Locked {
            guard now >= started, now < deadline, cancellation == 0 else { return false }
            return body()
        }
    }
}

// A token is released by classificationQueue -> controlQueue serial fences,
// after both the exact producer and result callback closures have returned.
private final class NG2ClassificationDrainToken {
    let id = UUID()
    let owner, runID: String
    let generation, job, capture, prefix: UInt64
    init(_ run: NG2Run, frame: NG2Frame, job: UInt64) {
        owner = run.owner; runID = run.id
        generation = frame.generation; self.job = job; capture = frame.id; prefix = frame.prefix
    }
}

private struct NG2RestartYieldEpoch {
    let generation, restart, oldJob: UInt64
    let fingerprint: Data
}
private struct NG2ClassificationSourceEvidence {
    let frame: NG2Frame
    let generation, job, prefix: UInt64
}
private final class NG2RestartYieldRun {
    var companion = NG2ControllerRestartYieldStatus()
    var epoch: NG2RestartYieldEpoch?
    var firstFloor: NG2Frame?
    var firstPartial: NG2Frame?
    var firstFull: NG2Frame?
    // Diagnostic originals only. Never a dispatch, C-scene or motion source.
    var classificationSources: [UInt64: NG2ClassificationSourceEvidence] = [:]
    var classificationFrames: [NG2Frame] { classificationSources.values.map { $0.frame } }
    var submittedGoodsIDs = Set<UInt64>()
    var goodsFrames: [NG2Frame] {
        [firstPartial, firstFull].compactMap { $0 }.sorted { $0.id < $1.id }
    }
    var firstGoods: NG2Frame? { goodsFrames.first }
    var firstGoodsSubmitted: Bool { goodsFrames.allSatisfy { submittedGoodsIDs.contains($0.id) } }
    var capturePaused = false
    var captureControlTokens = Set<UInt64>()
    var controlReady = false
    var failed = false
}

// This state is owned by the run gate. Expensive classification and durable
// storage use separate single workers; neither worker has input authority.
private final class NG2CycleRun {
    var companion = NG2ControllerCycleStatus()
    var spool: NG2CycleSpool?
    var classificationOutstanding = false
    var classificationDrainTokens: [UUID: NG2ClassificationDrainToken] = [:]
    var persistenceOutstanding = false
    var checkpointJob: UInt64 = 0
    var intentCommand: UInt64 = 0
    var outcomeJob: UInt64 = 0
    var terminalPersistenceStarted = false
    var terminalPersisted = false
    var terminalRecord: NG2CycleSpool.RecordRef?
    var frames: [UInt64: NG2Frame] = [:]
    var assessment: [String: JSONValue]?
    var assessmentAdopted = false
    var rawSHA256: String?
    var completed: [JSONValue] = []
    var storedCaptureIDs = Set<UInt64>()
    var failure: String?
    var notificationState = "not_requested"
    var notificationRequested = false
    var published = false
    var recovered = false
    var recoveredInputState: Int32 = 0
    var exporter: NG2CycleExport?
    var workerBusy: Bool { classificationOutstanding || !classificationDrainTokens.isEmpty || persistenceOutstanding }
    init() {
        companion.abi_version = 1; companion.struct_size = UInt32(MemoryLayout<NG2ControllerCycleStatus>.size)
        companion.level_id = 1
    }
}

private struct NG2IrregularMenuFrame {
    let id, prefix: UInt64
    let left, top: Int32
}
private final class NG2IrregularRun {
    var companion = NG2ControllerIrregularStatus()
    var frames: [UInt64: NG2Frame] = [:]
    var scanRestart = false
    var reservation: NG2CycleSpool.IrregularReservation?
    var checkpointEpisode: UInt64 = 0
    var continueIntent: UInt64 = 0
    var continueOutcome: UInt64 = 0
    var restartIntent: UInt64 = 0
    var restartOutcome: UInt64 = 0
    var recoveredProjection: [String: JSONValue]?
    var resourceProjection: [String: JSONValue] = [:]
    var hint: [String: JSONValue]?
    var roles: [String: UInt64] = [:]
    var roleEpisode: UInt64 = 0
    var menuFrames: [NG2IrregularMenuFrame] = []
    var observations: [UInt64: NG2IrregularObservation] = [:]
    var archivedInitialID: UInt64 = 0
    var archivedFoundID: UInt64 = 0
    init() {
        companion.abi_version = 1
        companion.struct_size = UInt32(MemoryLayout<NG2ControllerIrregularStatus>.size)
    }
}

private final class NG2CycleJob {
    let run: NG2Run
    let frame: NG2Frame
    let generation, level, job, prefix, deadline: UInt64
    let drainToken: NG2ClassificationDrainToken?
    init(_ run: NG2Run, frame: NG2Frame, state: NG2ControllerCycleStatus) {
        self.run = run; self.frame = frame; generation = frame.generation
        level = state.level_id; job = state.job_id; prefix = state.prefix; deadline = state.deadline_ns
        drainToken = run.yieldAfterRestart ? NG2ClassificationDrainToken(run, frame: frame, job: state.job_id) : nil
    }
    var cancelled: Bool {
        run.lock.ng2Locked { run.cancelReason != 0 || run.stopped || run.generation != generation }
    }
}

#if NG2_RUNTIME_HOST_TEST
enum NG2RuntimeCycleTestHooks {
    static var spoolRoot: URL?
    static var rgba: ((Data) -> Data)?
    static var notificationAuthorization = "authorized"
    static var beforeClassification: ((UInt64) -> Void)?
    static var classificationResult: ((UInt64, UnsafePointer<NG2Scene>, inout NG2RingResult) -> Void)?
    static var afterClassificationCall: ((Int32, Int32, UInt32) -> Void)?
    static var afterClassificationEnqueueBeforeReturn: ((UInt64) -> Void)?
    static var beforeClassificationCommitReturn: ((UInt64) -> Void)?
    static var irregularRGBA: ((Data) -> Data)?
    static var afterIrregularAnalysis: ((UInt64, Data, NG2IrregularObservation) -> Void)?
    static var beforeIrregularWrite: ((String, UInt64) -> Void)?
    static var beforeIrregularPersistenceCommit: ((String, UInt64) -> Void)?
    static var beforeClassificationCommit: ((UInt64) -> Void)?
    static var beforeCheckpointWrite: ((UInt64) -> Void)?
    static var beforeIntentWrite: ((UInt64) -> Void)?
    static var beforeRestartOutcomeWrite: ((UInt64) -> Void)?
    static var beforePersistenceCommit: ((UInt64) -> Void)?
    static var afterNotification: ((String) -> Void)?
    static var afterTerminalDrainPass: ((String, Bool, Bool, Bool) -> Void)?
}
#endif

private struct AuthoritySample {
    var start: UInt64 = 0
    var end: UInt64 = 0
    var foreground = false
}

// Foreground evidence belongs to one logical dispatch pipeline, not to an
// image or direction. Only C can certify that a new ID is a qualified reissue.
private struct NG2PreparationKey: Equatable {
    let run: ObjectIdentifier
    let clock: String
    let owner: String
    let generation: UInt64
    let expectedPID: pid_t
    let prefix: UInt64
    let epoch: UInt64
    let ordinal: UInt64
    let target: UInt64
    let notBefore: UInt64
    let deadline: UInt64
    init(_ run: NG2Run, _ command: NG2Command, generation: UInt64, epoch: UInt64) {
        self.run = ObjectIdentifier(run); clock = run.clock; owner = run.owner
        self.generation = generation; expectedPID = run.expectedPID; prefix = run.prefix
        self.epoch = epoch; ordinal = command.ordinal; target = command.target_ns
        notBefore = command.not_before_ns; deadline = command.deadline_ns
    }
    #if NG2_RUNTIME_HOST_TEST
    init(testRun: ObjectIdentifier, clock: String, owner: String, generation: UInt64,
         expectedPID: pid_t, prefix: UInt64, epoch: UInt64, ordinal: UInt64,
         target: UInt64, notBefore: UInt64, deadline: UInt64) {
        run = testRun; self.clock = clock; self.owner = owner; self.generation = generation
        self.expectedPID = expectedPID; self.prefix = prefix; self.epoch = epoch
        self.ordinal = ordinal; self.target = target; self.notBefore = notBefore; self.deadline = deadline
    }
    #endif
}

private final class NG2PreparationLease {
    let key: NG2PreparationKey
    let preparedCommandID: UInt64
    let authority: AuthoritySample
    init(key: NG2PreparationKey, commandID: UInt64, authority: AuthoritySample) {
        self.key = key; preparedCommandID = commandID; self.authority = authority
    }
    func matchesIdentity(key candidate: NG2PreparationKey, commandID: UInt64,
                         currentEpoch: UInt64) -> Bool {
        guard key == candidate else { return false }
        if key.epoch == 0 { return preparedCommandID == commandID }
        return currentEpoch == key.epoch
    }
}

// Scalar diagnostics are committed with their image. Dictionary construction
// waits until a response or an untimed report flush, outside the admission lock.
private struct NG2CaptureSample {
    let id, start, end, decodeEnd, analysisStart, analysisEnd, observeStart, observeEnd: UInt64
    let startPrefix, prefix: UInt64
    let startInFlight, endInFlight, stable: Bool
    init(_ frame: NG2Frame, observeStart: UInt64, observeEnd: UInt64) {
        id = frame.id; start = frame.start; end = frame.end; decodeEnd = frame.decodeEnd
        analysisStart = frame.analysisStart; analysisEnd = frame.analysisEnd
        self.observeStart = observeStart; self.observeEnd = observeEnd
        startPrefix = frame.startPrefix; prefix = frame.prefix
        startInFlight = frame.startInFlight; endInFlight = frame.endInFlight; stable = frame.stable
    }
}

private struct NG2RasterSample {
    let id: UInt64
    let trace: NG2Raster.Trace
}

// Copy retained C recovery records and their raw samples at the same serial
// cache boundary. Report/export encoding must never query a later live model.
private struct NG2RecoveryRecord {
    let trace: NG2ControllerRecoveryTrace
    let samples: [NG2BeatSample]
}

private final class NG2ControllerSnapshot {
    let status: NG2ControllerStatus
    let events: [NG2ControllerEvent]
    let changes: [NG2ControllerSceneChange]
    let details: [NG2ControllerSceneDetail]
    let motionWait: NG2ControllerMotionWait
    let motionReferences: [NG2ControllerMotionReference]
    let recovery: NG2ControllerRecoveryStatus
    let recoveryRecords: [NG2RecoveryRecord]
    let stopDetail: NG2ControllerStopDetail
    let handoff: NG2ControllerHandoff
    init(status: NG2ControllerStatus, events: [NG2ControllerEvent], changes: [NG2ControllerSceneChange],
         details: [NG2ControllerSceneDetail], motionWait: NG2ControllerMotionWait,
         motionReferences: [NG2ControllerMotionReference], recovery: NG2ControllerRecoveryStatus,
         recoveryRecords: [NG2RecoveryRecord], stopDetail: NG2ControllerStopDetail,
         handoff: NG2ControllerHandoff) {
        self.status = status; self.events = events; self.changes = changes; self.details = details
        self.motionWait = motionWait; self.motionReferences = motionReferences
        self.recovery = recovery; self.recoveryRecords = recoveryRecords
        self.stopDetail = stopDetail; self.handoff = handoff
    }
}

private struct NG2ExportImage {
    let bytes: Data
    let hash: String
}

private final class NG2ExportCache {
    let id: String
    let generation: UInt64
    let manifest: [String: JSONValue]
    let images: [UInt64: NG2ExportImage]
    init(id: String, generation: UInt64, manifest: [String: JSONValue], images: [UInt64: NG2ExportImage]) {
        self.id = id; self.generation = generation; self.manifest = manifest; self.images = images
    }
}

private enum NG2ExportAdmission {
    case denied
    case busy
    case cached(String, UInt64, [String: JSONValue])
    case build(String, UInt64, [NG2Frame], UInt64, Set<UInt64>)
}

private final class NG2Run {
    let lock = NSLock()
    let owner: String
    let id: String
    let profile: String
    let maximumExportBytes: Int
    let yieldAfterRestart: Bool
    let continuousCampaign: Bool
    let restartYield: NG2RestartYieldRun?
    let campaign: NG2ContinuousCampaign?
    let campaignIndex: Int
    let campaignPredecessor: String?
    let campaignReservation: NG2CycleSpool.Reservation?
    let successorPID: pid_t
    var campaignPersistenceTokens: [UUID: String] = [:]
    var campaignSealStarted = false
    var campaignContinuation = NG2ControllerContinuousStatus()
    var campaignQualifiedGeneration: UInt64 = 0
    let clock: String
    var generation: UInt64 = 1
    var cancelReason: Int32 = 0
    var heartbeat: UInt64
    let acceptedStarted: UInt64
    var lease = true
    var captureOutstanding = false
    var capturePipelineIDs = Set<UInt64>()
    var irregularCapturePaused = false
    var captureWorkerDone = false
    var captureThread: Thread?
    var bootstrapOutstanding = false
    var mainCommandID: UInt64 = 0
    var mainCallbacks = Set<UInt64>()
    var mainOutstanding: Bool { bootstrapOutstanding || !mainCallbacks.isEmpty }
    var stopped = false
    var inFlight = false
    var prefix: UInt64 = 0
    var captureID: UInt64 = 0
    var latest: NG2Frame?
    var images: [NG2Frame] = []
    var pinned: [UInt64: NG2Frame] = [:]
    // Cached on controlQueue with the C snapshot. Results never query C.
    var diagnosticCaptureIDs: [UInt64] = []
    // Cycle-only readonly wait/first-failure evidence. IDs are replaced from
    // each coherent snapshot; rasters share the bounded existing pin store.
    var cycleDiagnosticCaptureIDs: [UInt64] = []
    // Profile2 uses its existing twentieth slot for one original initial
    // rejection raster. Replacements do not grow the pin/export budgets.
    var initialRejectedCaptureID: UInt64?
    // Cycle-only optional partner of that coherent rejection. Existing
    // critical/restart/dispatch evidence keeps the bounded store's priority.
    var initialRejectedSourceCaptureID: UInt64?
    var terminalCaptureID: UInt64?
    var references = Set<UInt64>()
    var analyzedFrames: UInt64 = 0
    var evictedFrames: UInt64 = 0
    var initial: NG2Frame?
    // At most one current negative PAUSE source per restart index, 0...11.
    // Only IDs are added; raw frames stay within the existing pinned store.
    var restartDecisionCaptureIDs: [Int32: UInt64] = [:]
    var found: NG2Frame?
    var report: [String: JSONValue] = [:]
    var controllerSnapshot: NG2ControllerSnapshot?
    var reportSnapshot: NG2ControllerSnapshot?
    var reportGeneration: UInt64 = 0
    var preparation: NG2PreparationLease?
    var captures: [NG2CaptureSample] = []
    var rasterSamples: [NG2RasterSample] = []
    var rasterSamplesDropped: UInt64 = 0
    var captureFailure: [String: JSONValue]?
    var dispatchFailure: [String: JSONValue]?
    var replacedFrames: UInt64 = 0
    var terminal = false
    var successful = false
    var uiFrozen = false
    var captureTimedOut = false
    var bootstrapUIStarted = false
    var startupRasterDeadline: UInt64 = 0
    var startupRasterReady = false
    var startupPortraitFailures = 0
    var core: OpaquePointer?
    var expectedPID: pid_t = 0
    var foreground = false
    var fast: FastActionHandler?
    var controlTimer: DispatchSourceTimer?
    var watchdog: DispatchSourceTimer?
    var lastCache: UInt64 = 0
    // At most one immutable profile-bounded PNG export belongs to the current run.
    // A builder retains its token until it actually returns, even if revoked.
    var exportCache: NG2ExportCache?
    var exportBuildID: String?
    let cycle: NG2CycleRun?
    let irregular: NG2IrregularRun?
    init(owner: String, id: String, now: UInt64, profile: String = "normal-1-1-v1", clock: String? = nil,
         yieldAfterRestart: Bool = false, campaign: NG2ContinuousCampaign? = nil,
         campaignIndex: Int = 0, predecessor: String? = nil,
         reservation: NG2CycleSpool.Reservation? = nil, successorPID: pid_t = 0) {
        self.owner = owner; self.id = id; self.profile = profile
        self.campaign = campaign; self.campaignIndex = campaignIndex
        continuousCampaign = campaign != nil
        campaignPredecessor = predecessor; campaignReservation = reservation; self.successorPID = successorPID
        self.yieldAfterRestart = yieldAfterRestart || campaign != nil
        restartYield = self.yieldAfterRestart ? NG2RestartYieldRun() : nil
        self.clock = clock ?? UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        cycle = NG2Runtime.isCycleProfile(profile) ? NG2CycleRun() : nil
        irregular = profile == NG2Runtime.irregularProfile ? NG2IrregularRun() : nil
        maximumExportBytes = profile == NG2Runtime.evidenceProfile ? 10 * 1024 * 1024 : 4 * 1024 * 1024
        heartbeat = now; acceptedStarted = now
    }
    func cancel(_ reason: Int32) {
        lock.ng2Locked { cancelLocked(reason) }
    }
    // Caller already owns the run gate; quota failure and cancellation share
    // one linearization point with main's synth admission.
    func cancelLocked(_ reason: Int32) {
        if cancelReason == 0 { cancelReason = reason; generation &+= 1 }
        stopped = true
        latest = nil
        exportCache = nil
        preparation = nil
    }
}

// Copy C and Runtime projections at one short gate. Encoding never queries C
// or synchronously re-enters controlQueue, including from a main-thread hook.
private struct NG2ResponseProjection {
    let snapshot, reportSnapshot: NG2ControllerSnapshot?
    let cachedReport: [String: JSONValue]
    let generation, reportGeneration: UInt64
    let id, clock, state, profile: String
    let yieldAfterRestart: Bool
    let continuousCampaign: Bool
    let inFlight, terminal, cancelled, captureOutstanding, captureTimedOut, bootstrapUIStarted: Bool
    let lease, uiFrozen, mainOutstanding: Bool
    let acceptedStarted, prefix, captureID, replacedFrames, analyzedFrames, evictedFrames: UInt64
    let captures: [NG2CaptureSample]
    let rasterSamples: [NG2RasterSample]
    let rasterSamplesDropped: UInt64
    let captureFailure, dispatchFailure: [String: JSONValue]?
    let retained, references: Set<UInt64>
    let pinnedCount, recentCount: Int
    init(_ run: NG2Run) {
        snapshot = run.controllerSnapshot; reportSnapshot = run.reportSnapshot; cachedReport = run.report
        generation = run.generation; reportGeneration = run.reportGeneration
        id = run.id; clock = run.clock; profile = run.profile
        yieldAfterRestart = run.yieldAfterRestart && run.campaign == nil
        continuousCampaign = run.campaign != nil
        state = run.terminal ? (run.lease ? "draining" : (run.successful ? "completed" : "stopped"))
            : (run.controllerSnapshot == nil && run.report.isEmpty ? "accepted" : "running")
        inFlight = run.inFlight; terminal = run.terminal; cancelled = run.cancelReason != 0
        captureOutstanding = run.captureOutstanding; captureTimedOut = run.captureTimedOut
        bootstrapUIStarted = run.bootstrapUIStarted; lease = run.lease; uiFrozen = run.uiFrozen
        mainOutstanding = run.mainOutstanding; acceptedStarted = run.acceptedStarted; prefix = run.prefix
        captureID = run.captureID; replacedFrames = run.replacedFrames
        captures = run.captures; rasterSamples = run.rasterSamples; rasterSamplesDropped = run.rasterSamplesDropped
        captureFailure = run.captureFailure; dispatchFailure = run.dispatchFailure
        analyzedFrames = run.analyzedFrames; evictedFrames = run.evictedFrames
        retained = Set(run.pinned.keys).union(run.images.map { $0.id })
            .union(run.restartYield?.classificationSources.keys.map { $0 } ?? [])
        references = run.references
        pinnedCount = run.pinned.count; recentCount = run.images.count
    }
}

// Publication retries retain only the already durable receipt. They share
// the existing 64-entry history bound and never retain a run or image data.
private struct NG2CyclePublication {
    let profile: String
    let payload: [String: JSONValue]
}
private struct NG2RunHistory {
    let owner: String
    let response: [String: JSONValue]?
    var publication: NG2CyclePublication?
}

/// One bounded native run. Controller C state is used only on controlQueue, except begin()
/// on main while controlQueue synchronously waits for that exact call.
/// Status/cancel RPCs read immutable cached dictionaries and never touch C.
final class NG2Runtime {
    static let shared = NG2Runtime()
    static let methods: Set<String> = ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results", "necro_native_cycle", "necro_native_irregular"]
    static let ownerParam = "_necro_owner"
    static let profile = "normal-1-1-v1"
    static let evidenceProfile = "normal-1-1-evidence-v2"
    static let cycleProfile = "normal-1-1-cycle-v1"
    static let irregularProfile = "normal-1-1-irregular-v1"
    static func isCycleProfile(_ profile: String) -> Bool { profile == cycleProfile || profile == irregularProfile }
    private static let cycleEvidencePinLimit = 24
    private static let game = "jp.co.spike-chunsoft.necrodancerjp"
    private let lock = NSLock()
    private let controlQueue = DispatchQueue(label: "necro.native.control", qos: .userInteractive)
    private let watchdogQueue = DispatchQueue(label: "necro.native.watchdog", qos: .userInteractive)
    private let classificationQueue = DispatchQueue(label: "necro.native.cycle.classification", qos: .userInteractive)
    private let persistenceQueue = DispatchQueue(label: "necro.native.cycle.persistence", qos: .userInitiated)
    private var cycleScanState = "pending"
    private var cycleScanStarted = false
    private var unpublishedCycles: [String] = []
    private var notificationAuthorization = "pending"
    private var notificationPreparationStarted = false
    private var recoveredCycles: [String: NG2Run] = [:]
    private var cycleRecoveryPending = Set<String>()
    private var cycleRecoveryFailures: [String: String] = [:]
    private let runtimeInstanceID = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    private var current: NG2Run?
    private var campaigns: [String: NG2ContinuousCampaign] = [:]
    private var seen = Set<String>()
    // Metadata for at most 64 drained runs. Only the current run retains raw
    // rasters (legacy20/cycle24 pins plus recent/capture/analysis handoff).
    private var history: [String: NG2RunHistory] = [:]
    private var historyOrder: [String] = []
    private var streamCaptures = 0
    // A started input without a trustworthy ACK freezes all later UI for this
    // runner process. Worker drain does not certify the game input outcome.
    private var poisoned = false
    private init() {
        // Empty legacy installations retain their immediate start path. When
        // a cycle directory exists, the asynchronous crash-recovery admission
        // check must finish before any profile can acquire new input.
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
        if let support, FileManager.default.fileExists(atPath: support.appendingPathComponent("NGG2Cycles").path) {
            beginCycleScan()
        } else { cycleScanState = "ready" }
    }
    static func now() -> UInt64 {
        #if NG2_RUNTIME_HOST_TEST
        if let clock = NG2RuntimeTestHooks.clock { return clock() }
        #endif
        return DispatchTime.now().uptimeNanoseconds
    }
    private func ownerActive(_ run: NG2Run) -> Bool {
        !RemoteSession.shared.paused && AuthManager.shared.clientName(forTokenId: run.owner) != nil
    }

    private func lowerHexIdentity(_ value: String) -> Bool {
        value.utf8.count == 32 && value.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) })
    }

    var hasLease: Bool {
        let values = lock.ng2Locked { (poisoned, current, Array(campaigns.values)) }
        return values.0 || values.1?.lock.ng2Locked({ values.1?.lease ?? false }) == true
            || values.2.contains { root in root.gate.ng2Locked { root.lease } }
    }

    func leaseError(_ method: String) -> JSONRPCError? {
        guard hasLease, !Self.methods.contains(method),
              !["logs", "recent_logs", "is_locked", "stream_ack", "control"].contains(method) else { return nil }
        let message = lock.ng2Locked { poisoned ? "Unknown native input freezes UI until the runner process restarts." : "Native run owns the UI until its workers drain." }
        return JSONRPCError(code: -32004, message: message,
            data: ["outcome": .string("not_sent"), "retry_safe": .bool(false)])
    }

    /// Every legacy stream capture takes this short admission lease. An already
    /// running frame drains before native capture starts; new ones are suspended.
    func beginStreamCapture() -> Bool {
        if hasLease { return false }
        return lock.ng2Locked {
            if poisoned || current?.lock.ng2Locked({ current?.lease ?? false }) == true { return false }
            streamCaptures += 1
            return true
        }
    }
    func endStreamCapture() { lock.ng2Locked { streamCaptures -= 1 } }
    private var streamsDrained: Bool { lock.ng2Locked { streamCaptures == 0 } && NG2CaptureBridge.pendingRequests == 0 }
    func ownerChanged() {
        if RemoteSession.shared.paused {
            let run = lock.ng2Locked { current }
            if let root = run?.campaign { cancelCampaign(root, reason: 5) }
            else { run?.cancel(5) }
        }
    }

    private func campaignReply(_ root: NG2ContinuousCampaign) -> [String: JSONValue] {
        let state = root.gate.ng2Locked { root.stopped ? (root.lease ? "draining" : "stopped") : "running" }
        return ["run_id": .string(root.id), "profile": .string(Self.irregularProfile),
            "state": .string(state), "api_version": .string("1.98.16-ngg2"),
            "report": .object([:]), "continuous_campaign": .bool(true)]
    }
    private func campaignOwnsExports(_ owner: String) -> Bool {
        let roots = lock.ng2Locked { campaigns.values.filter { $0.owner == owner } }
        return roots.contains { root in root.gate.ng2Locked { root.lease } }
    }
    private func cancelCampaign(_ root: NG2ContinuousCampaign, reason: Int32) {
        root.requestCancel(reason)
        // Never wait for the old run gate or an executing synchronous synth.
        controlQueue.async {
            let run = root.gate.ng2Locked { root.active }
            root.gate.ng2Locked {
                root.stopped = true
                if root.reason == "none" { root.reason = reason == 2 ? "cancelled" : reason == 4 ? "locked" : "owner" }
            }
            run?.cancel(reason)
            if let run, let core = run.core {
                ng2_controller_cancel(core, Self.now(), reason); self.cycle(run)
            } else if let run { self.finishContinuousTerminal(run) }
        }
    }
    private func campaignPayload(_ root: NG2ContinuousCampaign, keepalive: Bool) -> [String: JSONValue] {
        let snapshot = root.gate.ng2Locked { () -> (NG2Run?, [NG2ContinuousCampaign.Child], Bool, Bool, String) in
            let active = root.active
            if keepalive, root.permits(Self.now()), !root.stopped,
               let active, ownerActive(active), !LockStateMonitor.shared().isLocked {
                root.heartbeat = Self.now()
                active.lock.ng2Locked {
                    if NG2TicketGuard.renewsHeartbeat(keepalive: true, ownerActive: ownerActive(active), cancelled: active.cancelReason != 0) {
                        active.heartbeat = root.heartbeat
                    }
                }
            }
            return (active, root.children, root.stopped, root.lease, root.reason)
        }
        let liveState = snapshot.0?.lock.ng2Locked { () -> (Int32, Bool, Bool) in
            (snapshot.0!.controllerSnapshot?.status.input_state ?? snapshot.0!.cycle?.recoveredInputState ?? 0,
             snapshot.0!.inFlight, snapshot.0!.uiFrozen)
        } ?? (0, false, false)
        let state = snapshot.2 ? root.gate.ng2Locked({ root.terminalSafety ?? liveState }) : liveState
        let rows: [JSONValue] = snapshot.1.map { row in
            .object(["index": .int(row.index), "run_id": .string(row.id),
                "predecessor_id": row.predecessor.map { .string($0) } ?? .null,
                "state": .string(row.state), "escrow_sealed": .bool(row.seal != nil),
                "escrow_sha256": row.seal.map { .string($0) } ?? .null,
                "terminal_reason": .int(Int(row.reason))])
        }
        return ["schema": .string("ngg2-continuous-campaign-v1"), "root_id": .string(root.id),
            "state": .string(snapshot.2 ? (snapshot.3 ? "draining" : "stopped") : "running"),
            "active_run_id": .string(snapshot.1.last?.id ?? root.id), "terminal": .bool(snapshot.2),
            "workers_drained": .bool(!snapshot.3), "input_state": .int(Int(state.0)),
            "native_inflight": .bool(state.1), "ui_frozen": .bool(state.2),
            "stop_reason": .string(snapshot.4), "child_limit": .int(16),
            "deadline_ns": number(root.deadline), "children": .array(rows)]
    }

    func handle(method: String, params: [String: JSONValue]?) -> ([String: JSONValue]?, JSONRPCError?) {
        guard Self.methods.contains(method), let owner = params?[Self.ownerParam]?.stringValue,
              !owner.isEmpty, let id = params?["run_id"]?.stringValue,
              lowerHexIdentity(id) else {
            return failure("Invalid native request identity.", -32602)
        }
        if method == "necro_native_cycle" || method == "necro_native_irregular" {
            return handleCycle(owner: owner, id: id, params: params ?? [:],
                spec: method == "necro_native_irregular" ? .irregular : .standard)
        }
        if method == "necro_native_results", campaignOwnsExports(owner) {
            return failure("Native campaign evidence is deferred until gameplay drains.", -32094)
        }
        if method == "necro_native_cancel", let root = lock.ng2Locked({ campaigns[id] }), root.owner == owner {
            guard Set((params ?? [:]).keys) == ["run_id", Self.ownerParam] else { return failure("Invalid campaign cancellation.", -32602) }
            cancelCampaign(root, reason: 2)
            return (["run_id": .string(root.id), "profile": .string(Self.irregularProfile),
                "state": .string("draining"), "api_version": .string("1.98.16-ngg2"),
                "report": .object([:]), "continuous_campaign": .bool(true)], nil)
        }
        if method == "necro_native_cancel", let active = lock.ng2Locked({ current }),
           active.id == id, active.owner == owner, let root = active.campaign {
            guard Set((params ?? [:]).keys) == ["run_id", Self.ownerParam] else { return failure("Invalid child cancellation.", -32602) }
            cancelCampaign(root, reason: 2)
            return (["run_id": .string(id), "profile": .string(Self.irregularProfile),
                "state": .string("draining"), "api_version": .string("1.98.16-ngg2"),
                "report": .object([:]), "continuous_campaign": .bool(true)], nil)
        }
        var exportMode: String?
        if method == "necro_native_results", let value = params?["mode"] {
            guard let mode = value.stringValue, mode == "manifest" || mode == "chunk" else {
                return failure("Unsupported native results mode.", -32602)
            }
            exportMode = mode
        }
        let allowed: Set<String> = method == "necro_native_start" ? ["run_id", "profile", "yield_after_restart", "continuous_campaign", Self.ownerParam]
            : (method == "necro_native_status" ? ["run_id", "keepalive", Self.ownerParam]
               : (exportMode == "chunk" ? ["run_id", "mode", "export_id", "capture_id", "offset", Self.ownerParam]
                  : (exportMode == "manifest" ? ["run_id", "mode", Self.ownerParam] : ["run_id", Self.ownerParam])))
        guard Set((params ?? [:]).keys).isSubset(of: allowed) else { return failure("Unknown native request parameter.", -32602) }
        if method == "necro_native_start" {
            guard let profile = params?["profile"]?.stringValue,
                  profile == Self.profile || profile == Self.evidenceProfile || Self.isCycleProfile(profile) else {
                return failure("Unsupported native profile.", -32602)
            }
            let yieldAfterRestart: Bool
            if let value = params?["yield_after_restart"] {
                guard profile == Self.irregularProfile, value.boolValue == true else {
                    return failure("yield_after_restart is true-only and requires the irregular profile.", -32602)
                }
                yieldAfterRestart = true
            } else { yieldAfterRestart = false }
            let continuous = params?["continuous_campaign"] != nil
            if continuous && (params?["continuous_campaign"]?.boolValue != true || profile != Self.irregularProfile || yieldAfterRestart) {
                return failure("continuous_campaign is true-only and excludes restart yield.", -32602)
            }
            if let root = lock.ng2Locked({ campaigns[id] }) {
                guard root.owner == owner, continuous, profile == Self.irregularProfile else {
                    return failure("Native campaign mode is immutable.", -32602)
                }
                return (campaignReply(root), nil)
            }
            if let archived = lock.ng2Locked({ history[id] }), archived.owner == owner,
               continuous || archived.response?["continuous_campaign"]?.boolValue == true {
                // Only the original root can be retried through campaigns.
                // An archived child cannot become a different input root or
                // be projected as a legacy-mode start under the same UUID.
                return failure("Native campaign mode and root identity are immutable.", -32602)
            }
            guard !RemoteSession.shared.paused else {
                return continuous ? cycleNotStarted("Owner paused native control before campaign admission.") : failure("Owner paused native control.")
            }
            var campaign: NG2ContinuousCampaign?
            var reservation: NG2CycleSpool.Reservation?
            if continuous {
                do {
                    let quota: NG2CycleSpool.CampaignQuota
                    #if NG2_RUNTIME_HOST_TEST
                    if let root = NG2RuntimeCycleTestHooks.spoolRoot {
                        quota = try NG2CycleSpool.testCreateCampaignQuota(rootURL: root, rootID: id, owner: owner)
                    } else { quota = try NG2CycleSpool.createCampaignQuota(rootID: id, owner: owner) }
                    #else
                    quota = try NG2CycleSpool.createCampaignQuota(rootID: id, owner: owner)
                    #endif
                    campaign = NG2ContinuousCampaign(id: id, owner: owner, now: Self.now(), quota: quota)
                    reservation = try quota.reserveNext(runID: id, index: 0, predecessorID: nil)
                } catch { return cycleNotStarted("Campaign storage quota is unavailable.") }
            }
            var created: NG2Run?
            let answer: ([String: JSONValue]?, JSONRPCError?) = lock.ng2Locked {
                if let old = current, old.owner == owner, old.id == id {
                    guard old.profile == profile else { return failure("Native run profile is immutable.", -32602) }
                    guard old.campaign == nil && !continuous && old.yieldAfterRestart == yieldAfterRestart else {
                        return failure("Native restart yield option is immutable.", -32602)
                    }
                    return (response(old), nil)
                }
                if let recovered = recoveredCycles[id], recovered.owner == owner,
                   recovered.yieldAfterRestart || yieldAfterRestart {
                    guard recovered.profile == profile && recovered.yieldAfterRestart == yieldAfterRestart else {
                        return failure("Native run profile and restart yield option are immutable.", -32602)
                    }
                    return (response(recovered), nil)
                }
                if let archived = history[id], archived.owner == owner {
                    guard let response = archived.response,
                        response["profile"]?.stringValue == profile &&
                        (response["yield_after_restart"]?.boolValue ?? false) == yieldAfterRestart else {
                        return failure("Native run profile is immutable.", -32602)
                    }
                    return (historical(response), nil)
                }
                guard cycleScanState == "ready", unpublishedCycles.isEmpty else {
                    return Self.isCycleProfile(profile) ? cycleNotStarted("Native cycle evidence must be recovered and publication acknowledged before a new start.")
                        : failure("Native cycle evidence must be recovered and publication acknowledged before a new start.")
                }
                if Self.isCycleProfile(profile) && notificationAuthorization != "authorized" && notificationAuthorization != "provisional" {
                    return cycleNotStarted("Prepare native cycle notifications before starting gameplay.")
                }
                if let oldCycle = current?.cycle, !oldCycle.published {
                    return Self.isCycleProfile(profile) ? cycleNotStarted("Previous native cycle publication is not acknowledged.")
                        : failure("Previous native cycle publication is not acknowledged.")
                }
                if poisoned {
                    return continuous ? cycleNotStarted("Unknown native input prevents campaign admission.")
                        : failure("Unknown native input freezes new runs until the runner process restarts.")
                }
                if current?.lock.ng2Locked({ current?.lease ?? false }) == true {
                    return continuous ? cycleNotStarted("Previous native run is still draining before campaign admission.")
                        : failure("Previous native run is still draining.")
                }
                if campaigns.values.contains(where: { root in root.gate.ng2Locked { root.lease } }) {
                    return continuous ? cycleNotStarted("Previous native campaign is still draining.")
                        : failure("Previous native campaign is still draining.")
                }
                if current?.lock.ng2Locked({ current?.exportBuildID != nil }) == true {
                    return continuous ? cycleNotStarted("Previous native export prevents campaign admission.")
                        : failure("Previous native image export is still being prepared.")
                }
                if NG2CaptureBridge.pendingRequests != 0 {
                    return continuous ? cycleNotStarted("Previous capture prevents campaign admission.")
                        : failure("Previous daemon capture is still outstanding.")
                }
                if seen.contains(id) || seen.count >= 128 {
                    return continuous ? cycleNotStarted("Run identity or process limit prevents campaign admission.")
                        : failure("Run identity was already consumed or process run limit reached.")
                }
                let run = NG2Run(owner: owner, id: id, now: campaign?.started ?? Self.now(), profile: profile,
                    yieldAfterRestart: yieldAfterRestart, campaign: campaign, reservation: reservation)
                if let old = current {
                    old.lock.ng2Locked {
                        old.exportCache = nil
                        old.images.removeAll(); old.pinned.removeAll()
                        old.initial = nil; old.found = nil; old.latest = nil
                        old.restartYield?.classificationSources.removeAll()
                    }
                }
                current = run; seen.insert(id); created = run
                if let campaign { campaign.active = run; campaigns[id] = campaign }
                return (response(run), nil)
            }
            if let run = created {
                if run.cycle != nil { initializeCycle(run) }
                else { controlQueue.async { self.start(run) } }
            }
            return answer
        }
        guard let run = lock.ng2Locked({ current }), run.owner == owner, run.id == id else {
            if exportMode != nil { return failure("Paged native images require the current run.") }
            guard let archived = lock.ng2Locked({ history[id] }), archived.owner == owner,
                  let snapshot = archived.response else { return failure("Native run unavailable for this owner.") }
            if method == "necro_native_status", let value = params?["keepalive"], value.boolValue == nil {
                return failure("keepalive must be boolean.", -32602)
            }
            var result = historical(snapshot)
            if method == "necro_native_results" {
                guard snapshot["profile"]?.stringValue != Self.evidenceProfile else {
                    return failure("Evidence profile requires paged image export.")
                }
                guard !RemoteSession.shared.paused else { return failure("Owner paused native export.") }
                result["images"] = .array([])
                result["exported_images"] = .int(0)
            }
            return (result, nil)
        }
        if method == "necro_native_status" {
            if let value = params?["keepalive"], value.boolValue == nil { return failure("keepalive must be boolean.", -32602) }
            let active = ownerActive(run)
            run.lock.ng2Locked {
                if run.campaign == nil && NG2TicketGuard.renewsHeartbeat(keepalive: params?["keepalive"]?.boolValue ?? false,
                    ownerActive: active, cancelled: run.cancelReason != 0) { run.heartbeat = Self.now() }
            }
            return (response(run), nil)
        }
        if method == "necro_native_cancel" { run.cancel(2); return (response(run), nil) }
        if run.cycle != nil { return failure("Cycle profile requires the dedicated cycle query.") }
        if exportMode == "manifest" { return exportManifest(run) }
        if exportMode == "chunk" { return exportChunk(run, params ?? [:]) }
        guard run.profile != Self.evidenceProfile else { return failure("Evidence profile requires paged image export.") }
        guard ownerActive(run),
              run.lock.ng2Locked({ run.terminal && !run.lease && !run.captureOutstanding && run.captureWorkerDone }) else {
            return failure("Native images require a terminal, drained run and active owner.")
        }
        let legacyAdmission: ([NG2Frame], NG2ExportCache?, UInt64, String?)? = lock.ng2Locked {
            run.lock.ng2Locked {
                guard exportEligibleLocked(run), run.exportBuildID == nil else { return nil }
                let cache = run.exportCache?.generation == run.generation ? run.exportCache : nil
                let token = UUID().uuidString
                run.exportBuildID = token
                return (selectedExportFrames(run), cache, run.generation, token)
            }
        }
        guard let (frames, cached, generation, token) = legacyAdmission else { return failure("Native image export is unavailable or being prepared.") }
        defer { if let token { run.lock.ng2Locked { if run.exportBuildID == token { run.exportBuildID = nil } } } }
        var images: [JSONValue] = []
        var totalImageBytes = 0
        var exportedIDs = Set<UInt64>()
        // Encode stop/found/initial anchors before event evidence so a byte
        // budget cannot silently give later ordinary frames their slots.
        for frame in frames {
            let encoded: Data?
            if let cached { encoded = cached.images[frame.id]?.bytes; if encoded == nil { continue } }
            else { encoded = exportPNG(frame) }
            guard let bytes = encoded else { return failure("Native image encoding failed.") }
            if bytes.count > 512 * 1024 || totalImageBytes + bytes.count > 4 * 1024 * 1024 { continue }
            totalImageBytes += bytes.count
            exportedIDs.insert(frame.id)
            let hash = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
            images.append(.object(["name": .string(String(format: "capture-%06llu.png", frame.id)),
                "format": .string("png"), "data_base64": .string(bytes.base64EncodedString()),
                "pixel_width": .int(896), "pixel_height": .int(414), "sha256": .string(hash),
                "capture_id": number(frame.id), "capture_start_ns": number(frame.start),
                "capture_end_ns": number(frame.end), "completed_prefix": number(frame.prefix),
                "decode_end_ns": number(frame.decodeEnd), "completed_prefix_start": number(frame.startPrefix),
                "completed_prefix_end": number(frame.prefix), "inflight_start": .bool(frame.startInFlight),
                "inflight_end": .bool(frame.endInFlight),
                "stable_prefix": .bool(frame.stable)]))
        }
        var result = response(run); result["images"] = .array(images)
        result["retained_images"] = .int(frames.count)
        result["exported_images"] = .int(images.count)
        run.lock.ng2Locked {
            result["omitted_image_count"] = number(run.analyzedFrames - min(run.analyzedFrames, UInt64(images.count)))
            result["omitted_capture_ids"] = .array(run.references.subtracting(exportedIDs).sorted().map { number($0) })
        }
        result["exported_capture_ids"] = .array(exportedIDs.sorted().map { number($0) })
        let valid = lock.ng2Locked { run.lock.ng2Locked { exportEligibleLocked(run, generation: generation) } }
        guard valid else { return failure("Native export identity or owner changed.") }
        return (result, nil)
    }

    private func exportPNG(_ frame: NG2Frame) -> Data? {
        guard let bytes = NG2Raster.png(frame.rgba) else { return nil }
        #if NG2_RUNTIME_HOST_TEST
        if let transform = NG2RuntimeExportTestHooks.transformExportPNG { return transform(bytes, frame.id) }
        #endif
        return bytes
    }

    // Call only while holding Runtime.lock, then run.lock, in that order.
    // A started/unknown input may still be diagnosed after worker drain; this
    // read-only gate does not certify its outcome or release the UI poison.
    private func exportEligibleLocked(_ run: NG2Run, generation: UInt64? = nil) -> Bool {
        let allowed = current === run && ownerActive(run) && run.terminal && !run.lease
            && !run.captureOutstanding && run.captureWorkerDone && !run.mainOutstanding
        if !allowed { run.exportCache = nil }
        if let cache = run.exportCache, cache.generation != run.generation { run.exportCache = nil }
        // A late response from an older generation must not erase a newer
        // generation's already authenticated export cache.
        return allowed && (generation == nil || generation == run.generation)
    }

    private func evidencePinLimit(_ run: NG2Run) -> Int {
        Self.isCycleProfile(run.profile) ? Self.cycleEvidencePinLimit : 20
    }

    private func priorityCaptureIDs(_ run: NG2Run, includingInitialSource: Bool = true) -> [UInt64] {
        var ids: [UInt64] = []
        if let irregular = run.irregular {
            let state = irregular.companion
            let hint = state.stage == 0 && state.proof_capture_id != 0
                ? [state.before_capture_id, state.proof_capture_id, state.live_baseline_capture_id]
                : [state.live_baseline_capture_id]
            let needed = irregularOwnsInput(state)
                ? irregular.roles.keys.sorted().compactMap { irregular.roles[$0] } : hint
            for id in needed where id != 0 && !ids.contains(id)
                && !(run.cycle?.storedCaptureIDs.contains(id) ?? false) { ids.append(id) }
        }
        let decisions = run.restartDecisionCaptureIDs.keys.sorted().compactMap { run.restartDecisionCaptureIDs[$0] }
        let initial = decisions.isEmpty ? [run.initial?.id].compactMap({ $0 }) : []
        // Existing stop/goods/comparison evidence stays ahead of the bounded
        // per-restart set. Its initial strong frame is already in that set.
        for id in [run.terminalCaptureID, run.found?.id].compactMap({ $0 }) + initial
            + run.diagnosticCaptureIDs + [run.initialRejectedCaptureID].compactMap({ $0 }) + decisions
            + run.cycleDiagnosticCaptureIDs {
            if id != 0 && !ids.contains(id) { ids.append(id) }
        }
        if includingInitialSource, Self.isCycleProfile(run.profile),
           let source = run.initialRejectedSourceCaptureID, source != 0, !ids.contains(source) { ids.append(source) }
        if let boundary = run.restartYield {
            for id in [boundary.firstFloor?.id, boundary.firstPartial?.id, boundary.firstFull?.id].compactMap({ $0 }) where !ids.contains(id) {
                ids.insert(id, at: 0)
            }
            for id in boundary.classificationSources.keys.sorted() where !ids.contains(id)
                && !(run.cycle?.storedCaptureIDs.contains(id) ?? false) { ids.append(id) }
        }
        return ids
    }

    private func selectedExportFrames(_ run: NG2Run) -> [NG2Frame] {
        var available = run.pinned
        let cycleFrames = run.irregular == nil ? [] : (run.cycle.map { Array($0.frames.values) } ?? [])
        for frame in (run.irregular.map { Array($0.frames.values) } ?? []) + cycleFrames
            + run.images + [run.initial, run.found, run.restartYield?.firstFloor,
                run.restartYield?.firstPartial, run.restartYield?.firstFull].compactMap({ $0 }) { available[frame.id] = frame }
        var needed = priorityCaptureIDs(run)
        if run.irregular != nil, let cycle = run.cycle {
            for id in [cycle.companion.capture_id, cycle.companion.queued_capture_id,
                       cycle.companion.pause_source_capture_id, cycle.companion.pause_capture_id,
                       cycle.companion.next_floor_capture_id].filter({ $0 != 0 }) where !needed.contains(id) {
                needed.insert(id, at: 0)
            }
        }
        let priority = needed.compactMap { available[$0] }
        var frames: [NG2Frame] = []
        for frame in priority + [run.images.last].compactMap({ $0 })
            + run.pinned.values.sorted(by: { $0.id > $1.id }) + Array(run.images.reversed()) {
            if !frames.contains(where: { $0.id == frame.id }) { frames.append(frame) }
        }
        return Array(frames.prefix(evidencePinLimit(run)))
    }

    private func imageMetadata(_ frame: NG2Frame, hash: String, length: Int) -> [String: JSONValue] {
        ["name": .string(String(format: "capture-%06llu.png", frame.id)), "format": .string("png"),
         "pixel_width": .int(896), "pixel_height": .int(414), "sha256": .string(hash), "byte_length": .int(length),
         "capture_id": number(frame.id), "capture_start_ns": number(frame.start), "capture_end_ns": number(frame.end),
         "completed_prefix": number(frame.prefix), "decode_end_ns": number(frame.decodeEnd),
         "completed_prefix_start": number(frame.startPrefix), "completed_prefix_end": number(frame.prefix),
         "inflight_start": .bool(frame.startInFlight), "inflight_end": .bool(frame.endInFlight),
         "stable_prefix": .bool(frame.stable)]
    }

    private func cachedManifest(_ run: NG2Run, id: String, generation: UInt64,
                                manifest: [String: JSONValue]) -> ([String: JSONValue]?, JSONRPCError?) {
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeExportTestHooks.beforeExportReply?()
        #endif
        return lock.ng2Locked {
            run.lock.ng2Locked {
                guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == id else {
                    return failure("Native export identity or owner changed.")
                }
                return (manifest, nil)
            }
        }
    }

    private func exportManifest(_ run: NG2Run) -> ([String: JSONValue]?, JSONRPCError?) {
        let admission: NG2ExportAdmission = lock.ng2Locked {
            run.lock.ng2Locked {
                guard exportEligibleLocked(run) else { return .denied }
                if let cache = run.exportCache, cache.generation == run.generation {
                    return .cached(cache.id, cache.generation, cache.manifest)
                }
                guard run.exportBuildID == nil else { return .busy }
                let token = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
                run.exportBuildID = token
                return .build(token, run.generation, selectedExportFrames(run), run.analyzedFrames, run.references)
            }
        }
        switch admission {
        case .denied: return failure("Native images require a terminal, drained current run and active owner.")
        case .busy: return failure("Native image export is already being prepared.")
        case .cached(let id, let generation, let manifest): return cachedManifest(run, id: id, generation: generation, manifest: manifest)
        case .build(let token, let generation, let frames, let analyzedCount, let references):
            defer { run.lock.ng2Locked { if run.exportBuildID == token { run.exportBuildID = nil } } }
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeExportTestHooks.beforeExportEncode?()
            #endif
            let admitted = lock.ng2Locked { run.lock.ng2Locked { exportEligibleLocked(run, generation: generation) && run.exportBuildID == token } }
            guard admitted else { return failure("Native export identity or owner changed.") }
            var images: [UInt64: NG2ExportImage] = [:]
            var metadata: [JSONValue] = []
            var total = 0
            // PNG and SHA work happens outside both locks. The immutable run
            // profile bounds this export; v1 shares its order/budget with legacy.
            for frame in frames {
                guard let bytes = exportPNG(frame) else { return failure("Native image encoding failed.") }
                if bytes.count > 512 * 1024 || total + bytes.count > run.maximumExportBytes { continue }
                total += bytes.count
                let hash = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
                let row = imageMetadata(frame, hash: hash, length: bytes.count)
                images[frame.id] = NG2ExportImage(bytes: bytes, hash: hash)
                metadata.append(.object(row))
            }
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeExportTestHooks.afterExportEncode?()
            #endif
            let exported = Set(images.keys)
            var manifest = response(run)
            manifest["result_mode"] = .string("manifest")
            manifest["export_id"] = .string(token)
            manifest["chunk_bytes"] = .int(64 * 1024)
            manifest["total_bytes"] = .int(total)
            manifest["images"] = .array(metadata)
            manifest["retained_images"] = .int(frames.count)
            manifest["exported_images"] = .int(images.count)
            manifest["exported_capture_ids"] = .array(exported.sorted().map { number($0) })
            manifest["omitted_capture_ids"] = .array(references.subtracting(exported).sorted().map { number($0) })
            manifest["omitted_image_count"] = number(analyzedCount - min(analyzedCount, UInt64(images.count)))
            let installed = lock.ng2Locked {
                run.lock.ng2Locked { () -> Bool in
                    guard exportEligibleLocked(run, generation: generation), run.exportBuildID == token else { return false }
                    run.exportCache = NG2ExportCache(id: token, generation: generation, manifest: manifest, images: images)
                    return true
                }
            }
            guard installed else { return failure("Native export identity or owner changed.") }
            // Only run.exportCache retains the PNG collection after install.
            // Cached metadata replies never carry a hidden 4 MiB cache retain
            // across a concurrent replacement of the current run.
            images.removeAll(keepingCapacity: false)
            return cachedManifest(run, id: token, generation: generation, manifest: manifest)
        }
    }

    private func exportChunk(_ run: NG2Run, _ params: [String: JSONValue]) -> ([String: JSONValue]?, JSONRPCError?) {
        guard let exportID = params["export_id"]?.stringValue, lowerHexIdentity(exportID),
              case .int(let captureID)? = params["capture_id"], captureID > 0,
              case .int(let offset)? = params["offset"], offset >= 0 else {
            return failure("Invalid native image chunk identity or offset.", -32602)
        }
        let selection: (UInt64, Int, String, Data)? = lock.ng2Locked {
            run.lock.ng2Locked {
                guard exportEligibleLocked(run), let cache = run.exportCache, cache.generation == run.generation,
                      cache.id == exportID, let image = cache.images[UInt64(captureID)], offset < image.bytes.count else { return nil }
                let count = min(64 * 1024, image.bytes.count - offset)
                // Force a bounded independent copy, rather than a Data slice
                // that could keep the full PNG/cache alive after a new run.
                let bytes = image.bytes.withUnsafeBytes { raw -> Data in
                    Data(bytes: raw.baseAddress!.advanced(by: offset), count: count)
                }
                return (cache.generation, image.bytes.count, image.hash, bytes)
            }
        }
        guard let (generation, length, hash, bytes) = selection else { return failure("Native image export or chunk is unavailable.") }
        let result: [String: JSONValue] = ["run_id": .string(run.id), "result_mode": .string("chunk"),
            "export_id": .string(exportID), "capture_id": .int(captureID), "offset": .int(offset),
            "byte_length": .int(length), "sha256": .string(hash),
            "data_base64": .string(bytes.base64EncodedString()), "chunk_bytes": .int(bytes.count)]
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeExportTestHooks.beforeExportReply?()
        #endif
        return lock.ng2Locked {
            run.lock.ng2Locked {
                guard exportEligibleLocked(run, generation: generation), run.exportCache?.id == exportID else {
                    return failure("Native export identity or owner changed.")
                }
                return (result, nil)
            }
        }
    }

    private func refreshCycleEvidence(_ run: NG2Run, frame: NG2Frame? = nil) {
        guard let cycle = run.cycle, let core = run.core else { return }
        var state = NG2ControllerCycleStatus(); ng2_controller_cycle_status(core, &state)
        run.lock.ng2Locked {
            let retained = cycle.frames
            if state.job_id != cycle.companion.job_id && state.pending != 0 {
                cycle.assessment = nil; cycle.assessmentAdopted = false; cycle.rawSHA256 = nil
                if !cycle.classificationOutstanding { cycle.frames.removeAll() }
            }
            cycle.companion = state
            let needed = Set([state.capture_id, state.queued_capture_id, state.pause_source_capture_id,
                state.pause_capture_id, state.next_floor_capture_id].filter { $0 != 0 })
            let available = [frame, run.initial, run.found].compactMap { $0 } + run.images + Array(run.pinned.values) + Array(retained.values)
                + (run.irregular.map { Array($0.frames.values) } ?? [])
                + [run.restartYield?.firstFloor, run.restartYield?.firstPartial, run.restartYield?.firstFull].compactMap { $0 }
            cycle.frames = cycle.frames.filter { needed.contains($0.key) }
            for item in available where needed.contains(item.id) { cycle.frames[item.id] = item }
        }
    }

    private func restartFingerprint(_ frame: NG2Frame) -> Data {
        var fingerprint = frame.analysis.scene.pointee.fingerprint
        return withUnsafeBytes(of: &fingerprint) { Data($0) }
    }

    // Main's successful RESTART reply installs this before publishing its ACK
    // prefix. The capture worker can therefore protect the very first stable
    // new-floor raster even when controlQueue has not consumed latest yet.
    private func armRestartYieldLocked(_ run: NG2Run, command: NG2Command, generation: UInt64) {
        guard let boundary = run.restartYield, let cycle = run.cycle,
              run.generation == generation, run.cancelReason == 0, ownerActive(run),
              cycle.companion.state == 6, cycle.companion.restart_command_id == command.id,
              (run.controllerSnapshot?.status.inputs ?? 0) > 0,
              cycle.companion.outcome == Int32(NG2_RING_NEGATIVE), cycle.companion.durable_ns != 0,
              cycle.companion.intent_ns != 0 else { return }
        guard let source = cycle.frames[cycle.companion.capture_id], source.generation == generation,
              source.stable, cycle.assessmentAdopted else { boundary.failed = true; return }
        boundary.epoch = NG2RestartYieldEpoch(generation: generation, restart: command.id,
            oldJob: cycle.companion.job_id, fingerprint: restartFingerprint(source))
        boundary.firstFloor = nil; boundary.firstPartial = nil; boundary.firstFull = nil; boundary.submittedGoodsIDs.removeAll()
        boundary.capturePaused = false; boundary.controlReady = false
    }

    private func restartYieldRetainedIDsLocked(_ run: NG2Run, adding id: UInt64? = nil) -> Set<UInt64> {
        var ids = Set(run.pinned.keys).union(run.images.map { $0.id })
        ids.formUnion(run.restartYield?.classificationSources.keys.map { $0 } ?? [])
        ids.formUnion(run.cycle?.storedCaptureIDs ?? [])
        ids.formUnion(run.capturePipelineIDs)
        ids.formUnion(run.restartYield?.captureControlTokens ?? [])
        ids.formUnion(run.cycle?.classificationDrainTokens.values.map { $0.capture } ?? [])
        ids.formUnion(run.cycle?.frames.keys.map { $0 } ?? [])
        ids.formUnion(run.irregular?.frames.keys.map { $0 } ?? [])
        ids.formUnion([run.initial?.id, run.found?.id, run.latest?.id,
            run.restartYield?.firstFloor?.id, run.restartYield?.firstPartial?.id,
            run.restartYield?.firstFull?.id, id].compactMap { $0 })
        return ids
    }

    private func restartYieldRawBudgetFitsLocked(_ run: NG2Run, adding id: UInt64? = nil) -> Bool {
        let count = restartYieldRetainedIDsLocked(run, adding: id).count
        return count <= NG2CycleSpool.maximumFrames
            && count * NG2CycleSpool.rasterBytes <= NG2CycleSpool.maximumRawBytes
    }

    // Reserve only inside the existing pin budget. Ordinary diagnostic pins
    // may yield their slot; all protected sources stay immutable and retained.
    private func reserveRestartYieldPinLocked(_ run: NG2Run, frame: NG2Frame, protected: Set<UInt64>) -> Bool {
        if run.pinned[frame.id] != nil { return true }
        let limit = evidencePinLimit(run)
        if run.pinned.count == limit, let victim = pinVictimLocked(run, incoming: frame.id, protected: protected) {
            run.pinned.removeValue(forKey: victim); run.evictedFrames += 1
        }
        guard run.pinned.count < limit else { return false }
        run.pinned[frame.id] = frame
        return true
    }

    // Caller holds run.lock. These three aliases share the existing bounded pin
    // store; they never displace protected evidence to manufacture a boundary.
    private func retainRestartYieldCaptureLocked(_ run: NG2Run, frame: NG2Frame) {
        guard let boundary = run.restartYield else { return }
        guard restartYieldRawBudgetFitsLocked(run, adding: frame.id) else {
            boundary.failed = true; return
        }
        guard let epoch = boundary.epoch, !boundary.failed,
              run.generation == epoch.generation, frame.generation == epoch.generation,
              run.cancelReason == 0, ownerActive(run), frame.stable,
              !frame.startInFlight, !frame.endInFlight, frame.startPrefix == epoch.restart,
              frame.prefix == epoch.restart, frame.analysis.scene.pointee.state == Int32(NG2_FLOOR) else { return }
        let fingerprint = restartFingerprint(frame)
        let changed = epoch.fingerprint.withUnsafeBytes { old in
            fingerprint.withUnsafeBytes { current in
                ng2_fingerprint_changed(old.bindMemory(to: UInt8.self).baseAddress,
                    current.bindMemory(to: UInt8.self).baseAddress) == 1
            }
        }
        guard changed else { return }
        let needsFloor = boundary.firstFloor == nil
        let goods = frame.analysis.scene.pointee.goods
        let needsPartial = boundary.firstPartial == nil && goods == Int32(NG2_GOODS_PARTIAL)
        let needsFull = boundary.firstFull == nil && goods == Int32(NG2_GOODS_VISIBLE)
        guard needsFloor || needsPartial || needsFull else { return }
        let protected = Set(priorityCaptureIDs(run) + [frame.id])
        guard reserveRestartYieldPinLocked(run, frame: frame, protected: protected) else {
            boundary.failed = true; return
        }
        run.references.insert(frame.id)
        if needsFloor { boundary.firstFloor = frame }
        if needsPartial { boundary.firstPartial = frame }
        if needsFull { boundary.firstFull = frame }
    }

    // Only controlQueue calls C. Raw slots are immutable and were protected
    // before latest replacement. The DATA API consumes their original source;
    // it does not reinstall an old image as the current UI or motion scene.
    private func serviceRestartYield(_ run: NG2Run) {
        guard let boundary = run.restartYield, let cycle = run.cycle, let core = run.core else { return }
        var state = NG2ControllerRestartYieldStatus()
        ng2_controller_restart_yield_status(core, Self.now(), &state)
        run.lock.ng2Locked { boundary.companion = state }
        guard run.lock.ng2Locked({ run.cancelReason == 0 && !run.stopped && !boundary.failed && ownerActive(run) }),
              !LockStateMonitor.shared().isLocked else { return }
        if state.invalid != 0 {
            run.lock.ng2Locked { boundary.controlReady = false; boundary.capturePaused = false }
            return
        }
        guard state.pending == 1 else { return }
        if let root = run.campaign, !root.permits(Self.now()) { run.cancel(root.cancelReason == 0 ? 15 : root.cancelReason); return }
        let missingFloor = run.lock.ng2Locked { boundary.firstFloor == nil }
        if missingFloor { run.cancel(17); ng2_controller_cancel(core, Self.now(), 17); return }
        let goods: NG2Frame? = run.lock.ng2Locked {
            guard !boundary.firstGoodsSubmitted, !cycle.classificationOutstanding,
                  cycle.classificationDrainTokens.isEmpty, !cycle.persistenceOutstanding,
                  !run.mainOutstanding else { return nil }
            return boundary.goodsFrames.first { !boundary.submittedGoodsIDs.contains($0.id) }
        }
        if let goods {
            let admitted = run.lock.ng2Locked { () -> Bool in
                guard let epoch = boundary.epoch, epoch.generation == run.generation,
                      goods.generation == run.generation, epoch.restart == state.restart_command_id,
                      goods.prefix == state.prefix, state.old_job_id == epoch.oldJob,
                      run.cancelReason == 0, ownerActive(run), !run.stopped else { return false }
                return ng2_controller_restart_yield_goods(core, UnsafePointer(goods.analysis.scene),
                    goods.id, goods.start, goods.end, goods.prefix, Self.now()) == 1
            }
            if !admitted { run.lock.ng2Locked { boundary.failed = true }; run.cancel(17); ng2_controller_cancel(core, Self.now(), 17); return }
            run.lock.ng2Locked { boundary.submittedGoodsIDs.insert(goods.id) }
            refreshCycleEvidence(run, frame: goods)
            ng2_controller_restart_yield_status(core, Self.now(), &state)
            run.lock.ng2Locked { boundary.companion = state }
        }
        if state.permitted == 1 { return }
        let ready = run.lock.ng2Locked { () -> Bool in
            guard state.ready == 1, boundary.firstGoods == nil || boundary.firstGoodsSubmitted,
                  cycle.classificationDrainTokens.isEmpty, !cycle.classificationOutstanding,
                  !cycle.persistenceOutstanding, run.campaignPersistenceTokens.isEmpty else { return false }
            boundary.capturePaused = true
            return true
        }
        guard ready else {
            run.lock.ng2Locked { boundary.controlReady = false; boundary.capturePaused = false }
            return
        }
        let permit = run.lock.ng2Locked { () -> Bool in
            guard let epoch = boundary.epoch, epoch.generation == run.generation,
                  run.cancelReason == 0, !run.stopped, ownerActive(run), !LockStateMonitor.shared().isLocked,
                  !run.captureOutstanding, run.capturePipelineIDs.isEmpty, run.latest == nil,
                  boundary.captureControlTokens.isEmpty, !run.inFlight, !run.mainOutstanding, NG2CaptureBridge.pendingRequests == 0,
                  cycle.classificationDrainTokens.isEmpty, !cycle.classificationOutstanding,
                  !cycle.persistenceOutstanding, boundary.firstGoods == nil || boundary.firstGoodsSubmitted,
                  ng2_controller_restart_yield_ready(core, Self.now()) == 1,
                  let source = (run.images + Array(run.pinned.values)).first(where: { $0.id == state.source_capture_id }),
                  source.generation == run.generation, source.stable, !source.startInFlight, !source.endInFlight,
                  source.start == state.source_start_ns, source.startPrefix == epoch.restart,
                  source.prefix == epoch.restart, state.source_prefix == epoch.restart,
                  source.analysis.scene.pointee.state == Int32(NG2_FLOOR) else { return false }
            pinDispatchSourceLocked(run, source.id)
            guard run.pinned[source.id] != nil else { boundary.failed = true; return false }
            return ng2_controller_restart_yield_permit(core, source.id, source.start, source.prefix, Self.now()) == 1
        }
        run.lock.ng2Locked {
            boundary.controlReady = permit
            // A stale UI source can be reacquired only under C's original
            // parent bound. Immutable unprocessed goods never take this path:
            // their source-bound DATA admission already fails closed above.
            if !permit { boundary.capturePaused = false }
        }
        if permit, let root = run.campaign {
            let linked = root.gate.ng2Locked { root.next?.predecessorID == run.id && root.active === run && !root.stopped }
            if linked {
                run.lock.ng2Locked {
                    guard run.cancelReason == 0, root.permits(Self.now()), run.campaignPersistenceTokens.isEmpty,
                          ng2_controller_continuous_finish(core, state.source_capture_id,
                            state.source_start_ns, state.source_prefix, Self.now()) == 1 else { return }
                    ng2_controller_continuous_status(core, &run.campaignContinuation)
                    run.campaignQualifiedGeneration = run.generation
                }
            }
        }
        if run.lock.ng2Locked({ boundary.failed }) { run.cancel(17); ng2_controller_cancel(core, Self.now(), 17) }
    }

    private func beginCampaignPersistence(_ run: NG2Run, kind: String) -> UUID? {
        guard run.campaign != nil else { return nil }
        let token = UUID(); run.lock.ng2Locked { run.campaignPersistenceTokens[token] = kind }; return token
    }
    private func continuousCompanion(_ value: NG2ControllerContinuousStatus) -> [String: JSONValue] {
        ["abi_version": .int(1), "enabled": .bool(value.enabled == 1),
         "successor_floor": .bool(value.successor_floor == 1), "qualified": .bool(value.qualified == 1),
         "root_deadline_ns": number(value.root_deadline_ns), "qualified_ns": number(value.qualified_ns),
         "parent_deadline_ns": number(value.parent_deadline_ns), "old_job_id": number(value.old_job_id),
         "restart_command_id": number(value.restart_command_id), "new_floor_capture_id": number(value.new_floor_capture_id),
         "source_capture_id": number(value.source_capture_id), "source_start_ns": number(value.source_start_ns),
         "source_prefix": number(value.source_prefix)]
    }
    // Called only after all actual run callbacks and its terminal writer have
    // returned. The root keeps the UI lease while immutable files are sealed.
    private func finishContinuousTerminal(_ run: NG2Run) {
        guard let root = run.campaign, let cycle = run.cycle else { return }
        guard !root.gate.ng2Locked({ root.pendingIO }) else { return }
        let admission = run.lock.ng2Locked { () -> (NG2CycleSpool, NG2CycleSpool.RecordRef)? in
            guard run.terminal, !run.lease, run.campaignPersistenceTokens.isEmpty,
                  !cycle.workerBusy, !run.campaignSealStarted else { return nil }
            run.campaignSealStarted = true
            guard let spool = cycle.spool, let terminal = cycle.terminalRecord else { return nil }
            return (spool, terminal)
        }
        guard let (spool, terminal) = admission else {
            if run.lock.ng2Locked({ run.campaignSealStarted && cycle.terminalRecord == nil }) {
                stopContinuous(root, run: run, reason: "storage")
            }
            return
        }
        let next = root.gate.ng2Locked { () -> NG2CycleSpool.Reservation? in
            root.pendingIO = true
            if !root.stopped, root.active === run, root.permits(Self.now()), run.campaignContinuation.qualified == 1 {
                return root.next
            }
            return nil
        }
        let proof = continuousCompanion(run.campaignContinuation)
        persistenceQueue.async {
            var sealed: NG2CycleSpool.RecordRef?
            do {
                sealed = try spool.sealContinuation(rootID: root.id, index: run.campaignIndex,
                    predecessorID: run.campaignPredecessor, clockID: run.clock,
                    terminal: terminal, continuation: try NG2CycleWire.object(proof), successor: next)
            } catch { }
            self.controlQueue.async {
                if let sealed {
                    root.gate.ng2Locked {
                        root.children[run.campaignIndex].seal = sealed.sha256
                        root.children[run.campaignIndex].state = "stopped"
                        root.children[run.campaignIndex].reason = run.controllerSnapshot?.status.reason ?? 0
                    }
                }
                // Both the real seal writer and this result callback must
                // return before any next UUID acquires a gameplay core.
                self.persistenceQueue.async {
                    self.controlQueue.async {
                        guard sealed != nil else { self.stopContinuous(root, run: run, reason: "storage"); return }
                        self.advanceContinuous(root, from: run, reservation: next)
                    }
                }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeContinuousTestHooks.beforeSealCommitReturn?(run.id)
                #endif
            }
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeContinuousTestHooks.afterSealEnqueueBeforeReturn?(run.id)
            #endif
        }
    }
    private func stopContinuous(_ root: NG2ContinuousCampaign, run: NG2Run, reason: String) {
        let safety = run.lock.ng2Locked {
            (run.controllerSnapshot?.status.input_state ?? run.cycle?.recoveredInputState ?? 0,
             run.inFlight, run.uiFrozen)
        }
        root.gate.ng2Locked {
            root.stopped = true; root.pendingIO = false; root.lease = false
            root.terminalSafety = safety
            if root.reason == "none" { root.reason = reason }
            if run.campaignIndex < root.children.count {
                root.children[run.campaignIndex].state = "stopped"
                if let status = run.controllerSnapshot?.status { root.children[run.campaignIndex].reason = status.reason }
            }
        }
        notifyCycleIfNeeded(run)
    }
    private func continuousStopReason(_ root: NG2ContinuousCampaign, run: NG2Run, now: UInt64) -> String {
        let prior = root.gate.ng2Locked { (root.reason, root.heartbeat) }
        if prior.0 != "none" { return prior.0 }
        let lost = run.lock.ng2Locked { run.cancelReason }
        if root.cancelReason == 2 || lost == 2 { return "cancelled" }
        if root.cancelReason == 4 || lost == 4 || LockStateMonitor.shared().isLocked { return "locked" }
        if root.cancelReason == 3 || root.cancelReason == 5 || [3, 5, 19].contains(lost) || !ownerActive(run)
            || (now >= prior.1 && now - prior.1 >= 5_000_000_000) { return "owner" }
        if now >= root.deadline || lost == 15 { return "session" }
        if run.cycle?.companion.outcome == 2 { return "target" }
        if run.cycle?.companion.outcome == 1 { return "candidate" }
        return run.controllerSnapshot?.status.reason == 14 ? "native_limit" : "unknown"
    }
    private func continuousBootstrapLoss(_ run: NG2Run) -> Int32 {
        guard let root = run.campaign else { return 0 }
        let now = Self.now()
        if root.cancelReason != 0 { return root.cancelReason }
        if !root.permits(now) { return 15 }
        if !ownerActive(run) { return 5 }
        if LockStateMonitor.shared().isLocked { return 4 }
        return 0
    }
    private func advanceContinuous(_ root: NG2ContinuousCampaign, from old: NG2Run,
                                   reservation: NG2CycleSpool.Reservation?) {
        let now = Self.now()
        let canPrepare = root.gate.ng2Locked {
            !root.stopped && root.active === old && root.permits(now)
                && now >= root.heartbeat && now - root.heartbeat < 5_000_000_000
                && reservation?.predecessorID == old.id && root.next == reservation
        }
        let unchanged = old.lock.ng2Locked { old.cancelReason == 0 && old.generation == old.campaignQualifiedGeneration }
        guard canPrepare, unchanged, let reservation, ownerActive(old), !LockStateMonitor.shared().isLocked,
              old.campaignContinuation.qualified == 1 else {
            stopContinuous(root, run: old, reason: continuousStopReason(root, run: old, now: now)); return
        }
        // RAM ownership can retire only after its independently sealed disk
        // originals exist. Old callbacks have all returned; no source crosses.
        old.lock.ng2Locked {
            old.images.removeAll(); old.pinned.removeAll(); old.initial = nil; old.found = nil; old.latest = nil
            old.restartYield?.classificationSources.removeAll(); old.restartYield?.firstFloor = nil
            old.restartYield?.firstPartial = nil; old.restartYield?.firstFull = nil
            old.cycle?.frames.removeAll(); old.irregular?.frames.removeAll(); old.exportCache = nil
        }
        lock.ng2Locked { recoveredCycles[old.id] = old }
        let child = NG2Run(owner: root.owner, id: reservation.runID, now: now, profile: Self.irregularProfile,
            campaign: root, campaignIndex: reservation.index, predecessor: old.id,
            reservation: reservation, successorPID: old.expectedPID)
        initializeCycle(child, continuationFrom: old)
    }
    private func commitContinuousChild(_ child: NG2Run, replacing old: NG2Run) {
        guard let root = child.campaign else { return }
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeContinuousTestHooks.beforeSuccessorCommit?(root.id, old.id, child.id)
        #endif
        let committed = root.gate.ng2Locked {
            root.commitIfAllowed(Self.now()) {
                guard !root.stopped, root.active === old, root.next == child.campaignReservation,
                      root.children.count == child.campaignIndex, ownerActive(old),
                      !LockStateMonitor.shared().isLocked,
                      Self.now() >= root.heartbeat, Self.now() - root.heartbeat < 5_000_000_000 else { return false }
                guard old.lock.ng2Locked({ old.cancelReason == 0 && old.generation == old.campaignQualifiedGeneration }) else { return false }
                root.children.append(.init(id: child.id, predecessor: old.id, index: child.campaignIndex))
                root.active = child; root.next = nil; root.pendingIO = false
                child.heartbeat = root.heartbeat; return true
            }
        }
        guard committed else {
            abortPreparedChild(child, predecessor: old,
                reason: continuousStopReason(root, run: old, now: Self.now())); return
        }
        lock.ng2Locked { current = child; seen.insert(child.id) }
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeContinuousTestHooks.afterChildAdmitted?(root.id, old.id, child.id, child.campaignIndex)
        #endif
        start(child)
    }
    private func abortPreparedChild(_ child: NG2Run, predecessor: NG2Run?, reason: String) {
        guard let root = child.campaign else { return }
        child.cancel(root.cancelReason == 0 ? 6 : root.cancelReason)
        child.lock.ng2Locked {
            child.terminal = true; child.captureWorkerDone = true; child.lease = false
            child.cycle?.persistenceOutstanding = false
            // A partial initialization has no durable terminal proof. Do not
            // manufacture known-input evidence from a missing disk record.
            child.cycle?.recoveredInputState = 4; child.cycle?.recovered = true; child.uiFrozen = true
        }
        root.gate.ng2Locked {
            if root.children.count == child.campaignIndex {
                root.children.append(.init(id: child.id, predecessor: child.campaignPredecessor, index: child.campaignIndex))
            }
            root.active = child
            root.children[child.campaignIndex].state = "stopped"
            root.children[child.campaignIndex].reason = root.cancelReason == 0 ? 6 : root.cancelReason
        }
        lock.ng2Locked { recoveredCycles[child.id] = child; seen.insert(child.id) }
        stopContinuous(root, run: child, reason: reason)
    }
    private func finishCampaignPersistence(_ run: NG2Run, _ token: UUID?) {
        guard let token else { return }
        #if NG2_RUNTIME_HOST_TEST
        let kind = run.lock.ng2Locked { run.campaignPersistenceTokens[token] ?? "" }
        NG2RuntimeContinuousTestHooks.beforePersistenceCommitReturn?(run.id, kind)
        #endif
        // The serial writer and its control commit closure both return before
        // this following pair of closures can release the actual lease.
        persistenceQueue.async {
            self.controlQueue.async {
                run.lock.ng2Locked { run.campaignPersistenceTokens.removeValue(forKey: token) }
                self.cycle(run)
            }
        }
    }

    private func serviceCycleAssessment(_ run: NG2Run) {
        guard let cycle = run.cycle, let core = run.core else { return }
        refreshCycleEvidence(run)
        refreshIrregularEvidence(run)
        if let irregular = run.irregular, irregularOwnsInput(irregular.companion) { return }
        let job: NG2CycleJob? = run.lock.ng2Locked {
            let state = cycle.companion
            guard !cycle.classificationOutstanding, cycle.classificationDrainTokens.isEmpty, state.pending == 1, state.worker_started_ns == 0,
                  state.capture_id != 0, run.cancelReason == 0, !run.stopped, ownerActive(run),
                  !LockStateMonitor.shared().isLocked, let frame = cycle.frames[state.capture_id],
                  frame.generation == run.generation, frame.stable, !frame.startInFlight, !frame.endInFlight,
                  frame.startPrefix == state.prefix, frame.prefix == state.prefix,
                  frame.start == state.capture_start_ns else { return nil }
            if let boundary = run.restartYield,
               (boundary.failed || !restartYieldRawBudgetFitsLocked(run, adding: frame.id)) {
                boundary.failed = true; run.cancelLocked(17)
                ng2_controller_cancel(core, Self.now(), 17); return nil
            }
            if let prior = run.restartYield?.classificationSources[frame.id],
               prior.generation != frame.generation || prior.job != state.job_id || prior.prefix != state.prefix {
                run.restartYield?.failed = true; run.cancelLocked(17)
                ng2_controller_cancel(core, Self.now(), 17); return nil
            }
            guard ng2_controller_cycle_worker_begin(core, state.job_id, state.capture_id, state.prefix, Self.now()) == 1 else { return nil }
            var admitted = NG2ControllerCycleStatus(); ng2_controller_cycle_status(core, &admitted)
            cycle.companion = admitted; cycle.classificationOutstanding = true
            if let boundary = run.restartYield {
                boundary.classificationSources[frame.id] = NG2ClassificationSourceEvidence(frame: frame,
                    generation: frame.generation, job: admitted.job_id, prefix: admitted.prefix)
                run.references.insert(frame.id)
                // Best-effort pin placement; the strong history remains even
                // when all24 pins belong to other mandatory evidence.
                _ = reserveRestartYieldPinLocked(run, frame: frame,
                    protected: Set(priorityCaptureIDs(run) + [frame.id]))
            }
            let job = NG2CycleJob(run, frame: frame, state: admitted)
            if let token = job.drainToken { cycle.classificationDrainTokens[token.id] = token }
            return job
        }
        if let job {
            classificationQueue.async {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeClassification?(job.job)
                #endif
                let digest = NG2CycleWire.hash(job.frame.rgba)
                var options = NG2RingOptions()
                options.abi = 1; options.size = UInt32(MemoryLayout<NG2RingOptions>.size)
                options.mode = Int32(NG2_RING_MODE_TARGET_ONLY); options.fast = 1; options.deadline_ns = job.deadline
                options.scene = UnsafePointer(job.frame.analysis.scene)
                options.context = Unmanaged.passUnretained(job).toOpaque()
                options.now_ns = { _ in NG2Runtime.now() }
                options.cancelled = { context in
                    guard let context else { return 1 }
                    return Unmanaged<NG2CycleJob>.fromOpaque(context).takeUnretainedValue().cancelled ? 1 : 0
                }
                var result = NG2RingResult()
                var returned = job.frame.rgba.withUnsafeBytes { raw in
                    ng2_ring_assess_rgba(raw.bindMemory(to: UInt8.self).baseAddress, raw.count, 896 * 4, &options, &result)
                }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.afterClassificationCall?(options.mode, returned, result.outcome)
                if let fixture = NG2RuntimeCycleTestHooks.classificationResult {
                    fixture(job.job, UnsafePointer(job.frame.analysis.scene), &result)
                    returned = Int32(result.status)
                }
                #endif
                let encoded = try? NG2CycleWire.assessment(result, mode: options.mode)
                self.controlQueue.async {
                    defer {
                        #if NG2_RUNTIME_HOST_TEST
                        NG2RuntimeCycleTestHooks.beforeClassificationCommitReturn?(job.job)
                        #endif
                        if let token = job.drainToken {
                            // A result may have cleared its logical flag while
                            // its producer is still returning. Both serial
                            // closures must return before this token can clear.
                            self.classificationQueue.async {
                                self.controlQueue.async {
                                    run.lock.ng2Locked {
                                        if cycle.classificationDrainTokens[token.id] === token {
                                            cycle.classificationDrainTokens.removeValue(forKey: token.id)
                                        }
                                    }
                                    self.cycle(run)
                                }
                            }
                        }
                    }
                    #if NG2_RUNTIME_HOST_TEST
                    NG2RuntimeCycleTestHooks.beforeClassificationCommit?(job.job)
                    #endif
                    run.lock.ng2Locked {
                        defer { cycle.classificationOutstanding = false }
                        guard let currentCore = run.core, run.generation == job.generation, run.cancelReason == 0,
                              self.ownerActive(run), !LockStateMonitor.shared().isLocked else { return }
                        var current = NG2ControllerCycleStatus(); ng2_controller_cycle_status(currentCore, &current)
                        guard current.level_id == job.level, current.job_id == job.job,
                              current.capture_id == job.frame.id, current.prefix == job.prefix,
                              current.capture_start_ns == job.frame.start else { return }
                        cycle.assessment = encoded; cycle.assessmentAdopted = false; cycle.rawSHA256 = digest
                        if let irregular = run.irregular {
                            var state = NG2ControllerIrregularStatus()
                            ng2_controller_irregular_status(currentCore, &state)
                            if state.episode_id != 0 && self.irregularOwnsInput(state) {
                                if returned != Int32(result.status) || encoded == nil {
                                    irregular.hint = nil
                                    _ = ng2_controller_irregular_ring_settled(currentCore, state.episode_id,
                                        job.job, job.frame.id, job.prefix, nil, Self.now())
                                } else {
                                    irregular.hint = ["job_id": NG2CycleWire.number(job.job),
                                        "capture_id": NG2CycleWire.number(job.frame.id), "prefix": NG2CycleWire.number(job.prefix),
                                        "status": .string(NG2CycleWire.assessmentStatus(result.status)),
                                        "outcome": .string(NG2CycleWire.outcome(result.outcome))]
                                    _ = ng2_controller_irregular_ring_settled(currentCore, state.episode_id,
                                        job.job, job.frame.id, job.prefix, &result, Self.now())
                                }
                                return
                            }
                        }
                        // A same-job late report may remain diagnostic evidence;
                        // it cannot reopen a terminal or restore input authority.
                        guard !run.stopped else { return }
                        if returned != Int32(result.status) || encoded == nil {
                            _ = ng2_controller_cycle_fail(currentCore, job.job, Self.now(), 6)
                        } else {
                            let committed = ng2_controller_cycle_assess(currentCore, job.job, job.frame.id, job.prefix, Self.now(), &result)
                            if committed == 1 {
                                var adopted = NG2ControllerCycleStatus(); ng2_controller_cycle_status(currentCore, &adopted)
                                cycle.assessmentAdopted = adopted.status == Int32(result.status)
                                    && adopted.outcome == Int32(result.outcome) && Self.now() <= job.deadline
                            }
                        }
                    }
                    self.refreshCycleEvidence(run)
                    self.refreshIrregularEvidence(run)
                    self.cycle(run)
                }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.afterClassificationEnqueueBeforeReturn?(job.job)
                #endif
            }
        }
        persistCycleCheckpoint(run)
        persistCycleOutcome(run)
    }

    private func irregularOwnsInput(_ state: NG2ControllerIrregularStatus) -> Bool {
        state.stage != 0 && !(state.stage == 8 && state.outcome_ns != 0)
    }

    // The first enemy zero may precede its partner by a whole period. These
    // exact C IDs retain original pixels independently of recent4/pin24.
    private func refreshIrregularEvidence(_ run: NG2Run, frame: NG2Frame? = nil) {
        guard let irregular = run.irregular, let core = run.core else { return }
        var state = NG2ControllerIrregularStatus()
        guard ng2_controller_irregular_status(core, &state) == 1,
              (try? NG2CycleWire.irregular(state)) != nil else {
            run.cancel(17); ng2_controller_cancel(core, Self.now(), 17); return
        }
        let completed = state.stage == 8 && state.outcome_ns != 0
        if completed { refreshCycleEvidence(run, frame: frame) }
        run.lock.ng2Locked {
            if completed || state.stage == 0 {
                if completed {
                    let oldRoles = Set(irregular.roles.values)
                    let normal = Set(run.cycle?.frames.keys.map { $0 } ?? [])
                    run.pinned = run.pinned.filter {
                        !oldRoles.contains($0.key) || !(run.cycle?.storedCaptureIDs.contains($0.key) ?? false) || normal.contains($0.key)
                    }
                }
                irregular.roles.removeAll(); irregular.menuFrames.removeAll(); irregular.observations.removeAll()
                irregular.roleEpisode = 0
            } else if state.episode_id != 0 && state.episode_id != irregular.roleEpisode {
                irregular.roles.removeAll(); irregular.menuFrames.removeAll(); irregular.hint = nil
                irregular.roleEpisode = state.episode_id
                irregular.continueIntent = 0; irregular.continueOutcome = 0
                irregular.restartIntent = 0; irregular.restartOutcome = 0
                if state.live_baseline_capture_id != 0 { irregular.roles["last_live_baseline"] = state.live_baseline_capture_id }
                if state.before_capture_id != 0 { irregular.roles["before"] = state.before_capture_id }
                if state.trigger_capture_id != 0 { irregular.roles["trigger"] = state.trigger_capture_id }
                if state.kind == 1 {
                    irregular.roles["zero1"] = state.proof_capture_id
                    irregular.roles["zero2"] = state.trigger_capture_id
                }
                if let cycle = run.cycle {
                    if cycle.companion.capture_id != 0 { irregular.roles["ring_source"] = cycle.companion.capture_id }
                    if cycle.companion.queued_capture_id != 0 { irregular.roles["queued_source"] = cycle.companion.queued_capture_id }
                }
            }
            irregular.companion = state
            run.irregularCapturePaused = state.stage == 1 || state.stage == 2
            irregular.scanRestart = (state.stage == 5 || state.stage == 6) && state.continue_command_id != 0 && !run.inFlight
            if irregularOwnsInput(state) {
                if state.continue_capture_id != 0 { irregular.roles["continue_outcome"] = state.continue_capture_id }
                if state.pause_capture_id != 0 { irregular.roles["pause_ack"] = state.pause_capture_id }
                if state.next_floor_capture_id != 0 { irregular.roles["new_floor"] = state.next_floor_capture_id }
            }
            if let frame, state.episode_id != 0, irregular.restartIntent == 0, (state.stage == 5 || state.stage == 6),
               frame.generation == run.generation, frame.stable, !frame.startInFlight, !frame.endInFlight,
               frame.prefix == state.prefix, frame.analysis.irregular.kind == 2,
               frame.analysis.irregular.matches == 1 {
                if let previous = irregular.menuFrames.last {
                    let b = frame.analysis.irregular
                    if previous.prefix != frame.prefix || abs(previous.left - b.left) > 2 || abs(previous.top - b.top) > 2 {
                        irregular.menuFrames.removeAll()
                    }
                }
                if irregular.menuFrames.last?.id != frame.id {
                    irregular.menuFrames.append(NG2IrregularMenuFrame(id: frame.id, prefix: frame.prefix,
                        left: frame.analysis.irregular.left, top: frame.analysis.irregular.top))
                }
                if irregular.menuFrames.count > 2 { irregular.menuFrames.removeFirst() }
                if let first = irregular.menuFrames.first { irregular.roles["menu1"] = first.id }
                if irregular.menuFrames.count == 2 { irregular.roles["menu2"] = irregular.menuFrames[1].id }
            }
            let hints: [UInt64] = state.stage == 0 && state.proof_capture_id != 0
                ? [state.before_capture_id, state.live_baseline_capture_id, state.proof_capture_id]
                : [state.live_baseline_capture_id]
            let needed = Set((irregularOwnsInput(state) ? Array(irregular.roles.values) : hints).filter { $0 != 0 })
            let available = Array(irregular.frames.values) + (run.cycle.map { Array($0.frames.values) } ?? [])
                + run.images + Array(run.pinned.values) + [run.initial, run.found, frame].compactMap { $0 }
            for value in available where needed.contains(value.id) && value.stable {
                irregular.observations[value.id] = value.analysis.irregular
            }
            irregular.observations = irregular.observations.filter { needed.contains($0.key) }
            let durable = run.cycle?.storedCaptureIDs ?? []
            let rawNeeded = needed.subtracting(durable)
            irregular.frames = irregular.frames.filter { rawNeeded.contains($0.key) }
            for value in available where rawNeeded.contains(value.id) { irregular.frames[value.id] = value }
        }
    }

    private func irregularDrainedLocked(_ run: NG2Run, _ cycle: NG2CycleRun) -> Bool {
        !cycle.classificationOutstanding && cycle.classificationDrainTokens.isEmpty && !cycle.persistenceOutstanding && !run.mainOutstanding
            && !run.inFlight && !run.captureOutstanding && run.capturePipelineIDs.isEmpty && run.latest == nil
            && (run.restartYield?.captureControlTokens.isEmpty ?? true) && NG2CaptureBridge.pendingRequests == 0
    }

    private func releaseIrregularReservation(_ run: NG2Run, allowDrainedPoison: Bool = false) {
        guard let cycle = run.cycle, let irregular = run.irregular else { return }
        let value: (NG2CycleSpool, NG2CycleSpool.IrregularReservation)? = run.lock.ng2Locked {
            guard !cycle.workerBusy, !run.mainOutstanding,
                  !run.inFlight || (allowDrainedPoison && run.terminal && captureReturnedLocked(run) && !run.captureOutstanding),
                  let spool = cycle.spool, let token = irregular.reservation else { return nil }
            return (spool, token)
        }
        if let (spool, token) = value {
            do {
                try spool.releaseIrregular(token)
                run.lock.ng2Locked { if irregular.reservation == token { irregular.reservation = nil } }
            } catch {
                if let core = run.core {
                    _ = ng2_controller_irregular_storage_failed(core, irregular.companion.episode_id, Self.now())
                }
            }
        }
    }

    private func serviceIrregularPersistence(_ run: NG2Run) {
        guard let irregular = run.irregular, let cycle = run.cycle else { return }
        refreshIrregularEvidence(run)
        let state = run.lock.ng2Locked { irregular.companion }
        if state.stage == 9 || state.outcome_ns != 0 {
            releaseIrregularReservation(run); return
        }
        if state.stage == 2 && state.durable_ns == 0 && irregular.checkpointEpisode != state.episode_id {
            persistIrregularRecord(run, kind: "irregular_checkpoint", command: nil)
        } else if state.stage == 5 && state.continue_capture_id != 0 && state.continue_outcome_ns == 0
                    && irregular.continueOutcome != state.continue_command_id {
            persistIrregularRecord(run, kind: "irregular_continue_outcome", command: nil)
        } else if state.stage == 8 && state.next_floor_capture_id != 0 && state.outcome_ns == 0
                    && irregular.restartOutcome != state.episode_id {
            persistIrregularRecord(run, kind: "irregular_restart_outcome", command: nil)
        }
        _ = cycle
    }

    private func persistIrregularIntent(_ run: NG2Run, command: NG2Command) {
        guard let irregular = run.irregular else { return }
        if command.kind == 5 && irregular.continueIntent != command.id {
            persistIrregularRecord(run, kind: "irregular_continue_intent", command: command)
        } else if command.kind == 3 && irregular.restartIntent != command.id {
            persistIrregularRecord(run, kind: "irregular_restart_intent", command: command)
        }
    }

    private func irregularACK(_ event: NG2ControllerEvent?) -> JSONValue {
        guard let event else { return .null }
        return .object(["command_id": NG2CycleWire.number(event.command.id), "kind": .int(Int(event.command.kind)),
            "started_ns": NG2CycleWire.number(event.begin_ns), "completed_ns": NG2CycleWire.number(event.end_ns),
            "outcome": .string(event.outcome == 2 ? "acked" : "unknown")])
    }

    private func persistIrregularRecord(_ run: NG2Run, kind: String, command: NG2Command?) {
        guard let irregular = run.irregular, let cycle = run.cycle, let core = run.core else { return }
        refreshIrregularEvidence(run)
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status)
        _ = cache(run, status, retainEvidence: false)
        let admission: (NG2CycleSpool, NG2ControllerIrregularStatus, [String: UInt64], [UInt64: NG2Frame],
                        NG2ControllerSnapshot?, [UInt64: NG2Frame], [UInt64: NG2IrregularObservation], UInt64, NG2CycleSpool.IrregularReservation?, [String: JSONValue]?)? = run.lock.ng2Locked {
            let state = irregular.companion
            guard state.episode_id != 0, !cycle.persistenceOutstanding, !cycle.classificationOutstanding,
                  !run.mainOutstanding, !run.inFlight, run.cancelReason == 0, !run.stopped,
                  ownerActive(run), !LockStateMonitor.shared().isLocked, Self.now() <= state.parent_deadline_ns,
                  let spool = cycle.spool else { return nil }
            if kind == "irregular_checkpoint" {
                guard state.stage == 2, state.durable_ns == 0, irregularDrainedLocked(run, cycle) else { return nil }
                irregular.checkpointEpisode = state.episode_id
            } else if kind == "irregular_continue_intent" || kind == "irregular_restart_intent" {
                guard let command, status.input_state == 1, status.current_command_id == command.id,
                      command.source_capture_id != 0, command.id != 0, state.durable_ns != 0,
                      let source = (Array(irregular.frames.values) + run.images + Array(run.pinned.values))
                        .first(where: { $0.id == command.source_capture_id }),
                      source.generation == run.generation, source.stable, !source.startInFlight, !source.endInFlight,
                      source.start == command.source_start_ns,
                      source.startPrefix == state.prefix, source.prefix == state.prefix else { return nil }
                irregular.frames[source.id] = source
                if command.kind == 5 {
                    guard state.stage == 4, state.continue_command_id == command.id else { return nil }
                    irregular.roles["fresh_death"] = source.id; irregular.continueIntent = command.id
                } else {
                    guard state.stage == 6, state.restart_command_id == command.id else { return nil }
                    irregular.roles["restart_source"] = source.id; irregular.restartIntent = command.id
                }
            } else if kind == "irregular_continue_outcome" {
                guard state.stage == 5, state.continue_capture_id != 0, state.continue_outcome_ns == 0,
                      state.continue_intent_ns != 0 else { return nil }
                irregular.continueOutcome = state.continue_command_id
            } else {
                guard state.stage == 8, state.next_floor_capture_id != 0, state.outcome_ns == 0,
                      state.restart_intent_ns != 0 else { return nil }
                irregular.restartOutcome = state.episode_id
            }
            cycle.persistenceOutstanding = true
            var historical = run.pinned
            for value in run.restartYield?.classificationFrames ?? [] { historical[value.id] = value }
            for value in [run.initial, run.found].compactMap({ $0 }) { historical[value.id] = value }
            return (spool, state, irregular.roles, irregular.frames, run.controllerSnapshot,
                historical, irregular.observations, run.generation, irregular.reservation, irregular.hint)
        }
        guard let (spool, state, roles, frames, snapshot, historicalPins, certificates, generation, previousToken, hint) = admission else { return }
        let completedShops = run.lock.ng2Locked { max(0, cycle.companion.completed_shops) }
        persistenceQueue.async {
            var success = false, token = previousToken, authorityFailed = false
            var savedIDs = Set<UInt64>()
            do {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeIrregularWrite?(kind, state.episode_id)
                #endif
                guard roles.count <= 16, !roles.values.contains(0) else { throw NG2CycleSpool.Failure.invalid("irregular-roles") }
                let ids = Set(roles.values)
                var stored = Dictionary(uniqueKeysWithValues: try spool.frames().map { ($0.captureID, $0) })
                if kind == "irregular_checkpoint" {
                    // Preserve every historical pin before making its memory slot
                    // available to the finite future UI roles. No UI is yet allowed.
                    let transfer = historicalPins.values.filter { stored[$0.id] == nil }
                    try spool.reserveCheckpoint(frames: transfer.count, metadataBytes: transfer.count * 4096)
                    for frame in transfer {
                        stored[frame.id] = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba,
                            metadata: self.cycleFrameMetadata(frame))
                        savedIDs.insert(frame.id)
                    }
                    let pins: Set<UInt64>? = run.lock.ng2Locked {
                        guard run.generation == generation, run.cancelReason == 0, !run.stopped,
                              self.ownerActive(run), !LockStateMonitor.shared().isLocked,
                              irregular.companion.episode_id == state.episode_id,
                              irregular.companion.prefix == state.prefix,
                              irregular.companion.parent_deadline_ns == state.parent_deadline_ns,
                              irregular.companion.stage == 2, !run.mainOutstanding, !run.inFlight,
                              !run.captureOutstanding, run.capturePipelineIDs.isEmpty, run.latest == nil,
                              NG2CaptureBridge.pendingRequests == 0,
                              Self.now() <= state.parent_deadline_ns else { return nil }
                        // All removed IDs are durable. Active role originals stay.
                        run.pinned = run.pinned.filter { ids.contains($0.key) || stored[$0.key] == nil }
                        if let initial = run.initial, stored[initial.id] != nil {
                            irregular.archivedInitialID = initial.id; run.initial = nil
                        }
                        if let found = run.found, stored[found.id] != nil {
                            irregular.archivedFoundID = found.id; run.found = nil
                        }
                        return Set(run.pinned.keys)
                    }
                    guard let pins else {
                        authorityFailed = true
                        throw NG2CycleSpool.Failure.invalid("irregular-authority-changed")
                    }
                    token = try spool.reserveIrregular(episode: state.episode_id, prefix: state.prefix,
                        generation: generation, knownCaptureIDs: ids, futureRoles: 16 - roles.count, pinnedCaptureIDs: pins)
                }
                guard let reservation = token else { throw NG2CycleSpool.Failure.invalid("irregular-no-reservation") }
                for id in ids.sorted() where stored[id] == nil {
                    guard let frame = frames[id], frame.generation == generation, frame.stable,
                          !frame.startInFlight, !frame.endInFlight else { throw NG2CycleSpool.Failure.invalid("irregular-source-missing") }
                    stored[id] = try spool.commitFrame(captureID: id, rgba: frame.rgba,
                        metadata: self.cycleFrameMetadata(frame), reservation: reservation)
                    savedIDs.insert(id)
                }
                var frameRows = [JSONValue]()
                for role in roles.keys.sorted() {
                    let id = roles[role]!
                    guard let ref = stored[id] else { throw NG2CycleSpool.Failure.invalid("irregular-source-unregistered") }
                    let metadata = try spool.frameMetadata(ref)
                    guard let start = metadata["capture_start_ns"] as? NSNumber,
                          let end = metadata["capture_end_ns"] as? NSNumber,
                          let prefix = metadata["completed_prefix_end"] as? NSNumber,
                          let sourceGeneration = metadata["generation"] as? NSNumber else {
                        throw NG2CycleSpool.Failure.invalid("irregular-source-metadata")
                    }
                    frameRows.append(.object(["role": .string(role), "capture_id": NG2CycleWire.number(id),
                        "start_ns": NG2CycleWire.number(start.uint64Value), "end_ns": NG2CycleWire.number(end.uint64Value),
                        "prefix": NG2CycleWire.number(prefix.uint64Value), "generation": NG2CycleWire.number(sourceGeneration.uint64Value),
                        "rgba_sha256": .string(ref.rawSHA256)]))
                }
                let events = snapshot?.events ?? []
                let checkpointMove = kind == "irregular_checkpoint" && state.kind == 1
                    ? events.last(where: { $0.command.kind == 4 && $0.command.id == state.prefix && $0.outcome == 2 }) : nil
                if kind == "irregular_checkpoint" && state.kind == 1 && checkpointMove == nil {
                    throw NG2CycleSpool.Failure.invalid("irregular-move-ack-missing")
                }
                let actionID = kind == "irregular_continue_outcome" ? state.continue_command_id
                    : (kind == "irregular_restart_outcome" ? state.restart_command_id : 0)
                let outcomeEvent = actionID == 0 ? nil : events.last(where: { $0.command.id == actionID && $0.outcome == 2 })
                if actionID != 0 && outcomeEvent == nil { throw NG2CycleSpool.Failure.invalid("irregular-ui-ack-missing") }
                let recordedCommand = command ?? checkpointMove?.command ?? outcomeEvent?.command
                var proofs = [JSONValue](), observations = [JSONValue]()
                var observationIDs = Set<UInt64>()
                if kind == "irregular_checkpoint" && state.kind == 1 {
                    for id in [state.proof_capture_id, state.trigger_capture_id] {
                        guard let observed = certificates[id], let ref = stored[id] else {
                            throw NG2CycleSpool.Failure.invalid("irregular-proof-missing")
                        }
                        let metadata = try spool.frameMetadata(ref)
                        guard let start = metadata["capture_start_ns"] as? NSNumber,
                              let end = metadata["capture_end_ns"] as? NSNumber else {
                            throw NG2CycleSpool.Failure.invalid("irregular-proof-metadata")
                        }
                        let certificate = try NG2CycleWire.irregularObservation(observed)
                        proofs.append(.object(["capture_id": NG2CycleWire.number(id), "start_ns": NG2CycleWire.number(start.uint64Value),
                            "end_ns": NG2CycleWire.number(end.uint64Value), "normal_motion": .string("blocked"),
                            "dx": .int(0), "dy": .int(0), "enemy": .object(certificate)]))
                        observationIDs.insert(id)
                    }
                }
                if kind == "irregular_checkpoint" && state.kind == 2 { observationIDs.insert(state.trigger_capture_id) }
                if kind == "irregular_continue_intent", let source = roles["fresh_death"] { observationIDs.insert(source) }
                if kind == "irregular_continue_outcome" { observationIDs.insert(state.continue_capture_id) }
                if kind == "irregular_restart_intent" {
                    for role in ["menu1", "menu2", "restart_source"] {
                        if let id = roles[role] { observationIDs.insert(id) }
                    }
                }
                if kind == "irregular_restart_outcome" { observationIDs.insert(state.next_floor_capture_id) }
                guard observationIDs.count <= 5 else { throw NG2CycleSpool.Failure.invalid("irregular-observation-bound") }
                for id in observationIDs.sorted() {
                    guard let observed = certificates[id] ?? frames[id]?.analysis.irregular else {
                        throw NG2CycleSpool.Failure.invalid("irregular-observation-missing")
                    }
                    observations.append(.object(["capture_id": NG2CycleWire.number(id),
                        "value": .object(try NG2CycleWire.irregularObservation(observed))]))
                }
                let resources = try NG2CycleWire.decode(spool.irregularResources(reservation))
                let payload: [String: JSONValue] = ["irregular": .object(try NG2CycleWire.irregular(state)),
                    "generation": NG2CycleWire.number(generation), "resources": .object(resources), "frames": .array(frameRows),
                    "observations": .array(observations), "command": recordedCommand.map { .object(self.cycleCommand($0)) } ?? .null,
                    "ack": self.irregularACK(checkpointMove ?? outcomeEvent), "proofs": .array(proofs),
                    "assessment_hint": hint.map { .object($0) } ?? .null]
                _ = try spool.commitRecord(kind: kind, cycle: UInt64(completedShops),
                    payload: NG2CycleWire.object(payload), reservation: reservation)
                success = true
            } catch { }
            let durable = success, reserved = token, lostAuthority = authorityFailed, committedIDs = savedIDs
            self.controlQueue.async {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeIrregularPersistenceCommit?(kind, state.episode_id)
                #endif
                var shouldDispatch = false, completedRestart = false
                var committedStatus: NG2ControllerStatus?
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false
                    if let reserved { irregular.reservation = reserved }
                    cycle.storedCaptureIDs.formUnion(committedIDs)
                    guard let currentCore = run.core, run.generation == generation, run.cancelReason == 0,
                          !run.stopped, self.ownerActive(run), !LockStateMonitor.shared().isLocked else { return }
                    if !durable {
                        cycle.failure = lostAuthority ? "irregular_authority_changed" : "irregular_storage_commit_failed"
                        if !lostAuthority {
                            _ = ng2_controller_irregular_storage_failed(currentCore, state.episode_id, Self.now())
                        }
                        return
                    }
                    if kind == "irregular_checkpoint" {
                        _ = ng2_controller_irregular_durable(currentCore, state.episode_id, state.trigger_capture_id, state.prefix, Self.now())
                    } else if let command {
                        shouldDispatch = ng2_controller_irregular_intent_commit(currentCore, state.episode_id,
                            command.id, command.source_capture_id, state.prefix, Self.now()) == 1
                    } else {
                        let action: Int32 = kind == "irregular_continue_outcome" ? 5 : 3
                        let commandID = action == 5 ? state.continue_command_id : state.restart_command_id
                        let captureID = action == 5 ? state.continue_capture_id : state.next_floor_capture_id
                        let committed = ng2_controller_irregular_outcome_commit(currentCore, state.episode_id,
                            action, commandID, captureID, state.prefix, Self.now())
                        completedRestart = action == 3 && committed == 1
                    }
                    var latest = NG2ControllerStatus()
                    ng2_controller_status(currentCore, &latest)
                    committedStatus = latest
                }
                if let committedStatus { self.cache(run, committedStatus, retainEvidence: false) }
                self.refreshCycleEvidence(run)
                self.refreshIrregularEvidence(run)
                if completedRestart { self.releaseIrregularReservation(run) }
                if shouldDispatch, let command, let currentCore = run.core {
                    _ = self.dispatchReserved(run, command: command, core: currentCore)
                }
                self.cycle(run)
            }
        }
    }

    private func cycleCommand(_ value: NG2Command) -> [String: JSONValue] {
        ["id": NG2CycleWire.number(value.id), "ordinal": NG2CycleWire.number(value.ordinal),
         "target_ns": NG2CycleWire.number(value.target_ns), "not_before_ns": NG2CycleWire.number(value.not_before_ns),
         "deadline_ns": NG2CycleWire.number(value.deadline_ns), "source_capture_id": NG2CycleWire.number(value.source_capture_id),
         "source_start_ns": NG2CycleWire.number(value.source_start_ns), "phase_sample_ns": NG2CycleWire.number(value.phase_sample_ns),
         "kind": .int(Int(value.kind)), "direction": .int(Int(value.direction)), "x": .int(Int(value.x)), "y": .int(Int(value.y))]
    }

    private func persistCycleIntent(_ run: NG2Run, command: NG2Command) {
        guard let cycle = run.cycle, let core = run.core else { return }
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status)
        _ = cache(run, status, retainEvidence: false)
        refreshCycleEvidence(run)
        let admission: (NG2CycleSpool, NG2Frame, NG2ControllerCycleStatus, UInt64, Bool)? = run.lock.ng2Locked {
            guard !cycle.persistenceOutstanding, cycle.intentCommand != command.id, run.cancelReason == 0, !run.stopped,
                  cycle.companion.durable_ns != 0, let spool = cycle.spool,
                  let frame = (run.images + Array(run.pinned.values) + Array(cycle.frames.values)).first(where: { $0.id == command.source_capture_id }),
                  frame.generation == run.generation, frame.stable, !frame.startInFlight, !frame.endInFlight,
                  frame.startPrefix == run.prefix, frame.prefix == run.prefix,
                  frame.analysis.scene.pointee.state == 1, frame.analysis.scene.pointee.restart_label == 1 else { return nil }
            cycle.intentCommand = command.id; cycle.persistenceOutstanding = true; cycle.frames[frame.id] = frame
            return (spool, frame, cycle.companion, run.generation, cycle.storedCaptureIDs.contains(frame.id))
        }
        guard let (spool, frame, state, generation, stored) = admission else {
            _ = ng2_controller_cycle_storage_failed(core, cycle.companion.job_id, Self.now()); return
        }
        let persistenceToken = beginCampaignPersistence(run, kind: "intent")
        persistenceQueue.async {
            var success = false
            var campaignFailure: String?
            do {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeIntentWrite?(state.job_id)
                #endif
                if let root = run.campaign, root.gate.ng2Locked({ root.next == nil }) {
                    let nextID = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
                    let namespaceCount = self.lock.ng2Locked { self.seen.count }
                    guard namespaceCount < 128, root.permits(Self.now()) else {
                        campaignFailure = "run_limit"; throw NG2CycleSpool.Failure.limit("campaign-identities")
                    }
                    let reservation: NG2CycleSpool.Reservation
                    do { reservation = try root.quota.reserveNext(runID: nextID, index: run.campaignIndex + 1, predecessorID: run.id) }
                    catch { campaignFailure = "escrow_quota"; throw error }
                    _ = try spool.commitRecord(kind: "continuation_reservation", cycle: UInt64(max(state.completed_shops, 0)), payload: reservation.payload)
                    self.lock.ng2Locked { self.seen.insert(reservation.runID) }
                    root.gate.ng2Locked { if root.next == nil { root.next = reservation } }
                }
                if !stored {
                    try spool.reserveCheckpoint(frames: 2, metadataBytes: 64 * 1024)
                    _ = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba, metadata: self.cycleFrameMetadata(frame))
                }
                let body: [String: JSONValue] = ["cycle": .object(NG2CycleWire.companion(state)),
                    "command": .object(self.cycleCommand(command)), "generation": NG2CycleWire.number(generation),
                    "source_prefix": NG2CycleWire.number(frame.prefix), "source_raw_sha256": .string(NG2CycleWire.hash(frame.rgba))]
                _ = try spool.commitRecord(kind: "restart_intent", cycle: UInt64(max(state.completed_shops, 0)), payload: NG2CycleWire.object(body))
                success = true
            } catch { }
            let durable = success
            self.controlQueue.async {
                defer { self.finishCampaignPersistence(run, persistenceToken) }
                var dispatch = false
                if let campaignFailure, let root = run.campaign {
                    root.gate.ng2Locked { root.reason = campaignFailure; root.stopped = true }
                    root.requestCancel(14); run.cancel(14)
                }
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false
                    if durable { cycle.storedCaptureIDs.insert(frame.id) }
                    guard let currentCore = run.core, run.generation == generation, run.cancelReason == 0,
                          !run.stopped, self.ownerActive(run), !LockStateMonitor.shared().isLocked,
                          run.campaign?.permits(Self.now()) ?? true else { return }
                    if durable {
                        dispatch = ng2_controller_cycle_intent_commit(currentCore, state.job_id, command.id, frame.id, frame.prefix, Self.now()) == 1
                    } else {
                        cycle.failure = "restart_intent_commit_failed"
                        _ = ng2_controller_cycle_storage_failed(currentCore, state.job_id, Self.now())
                    }
                }
                self.refreshCycleEvidence(run)
                if dispatch, let currentCore = run.core { _ = self.dispatchReserved(run, command: command, core: currentCore) }
                else { self.cycle(run) }
            }
            #if NG2_RUNTIME_HOST_TEST
            if run.campaign != nil { NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn?(run.id, "intent") }
            #endif
        }
    }

    private func persistCycleOutcome(_ run: NG2Run) {
        guard let cycle = run.cycle, let core = run.core else { return }
        var state = NG2ControllerCycleStatus(); ng2_controller_cycle_status(core, &state)
        let admission: (NG2CycleSpool, NG2Frame, UInt64, Bool, NG2ControllerSnapshot?)? = run.lock.ng2Locked {
            guard state.next_floor_capture_id != 0, state.outcome_ns == 0,
                  cycle.outcomeJob != state.job_id, !cycle.persistenceOutstanding,
                  run.cancelReason == 0, !run.stopped, let spool = cycle.spool,
                  let frame = cycle.frames[state.next_floor_capture_id], frame.stable,
                  !frame.startInFlight, !frame.endInFlight, frame.generation == run.generation else { return nil }
            cycle.outcomeJob = state.job_id; cycle.persistenceOutstanding = true
            return (spool, frame, run.generation, cycle.storedCaptureIDs.contains(frame.id), run.controllerSnapshot)
        }
        guard let (spool, frame, generation, stored, snapshot) = admission else { return }
        let persistenceToken = beginCampaignPersistence(run, kind: "outcome")
        persistenceQueue.async {
            var success = false
            do {
                if !stored {
                    try spool.reserveCheckpoint(frames: 1, metadataBytes: 128 * 1024)
                    _ = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba, metadata: self.cycleFrameMetadata(frame))
                }
                let body: [String: JSONValue] = ["cycle": .object(NG2CycleWire.companion(state)),
                    "generation": NG2CycleWire.number(generation), "floor_capture_id": NG2CycleWire.number(frame.id),
                    "floor_prefix": NG2CycleWire.number(frame.prefix), "floor_raw_sha256": .string(NG2CycleWire.hash(frame.rgba)),
                    "controller": snapshot.map { .object(self.encodeSnapshot($0, origin: "cycle_restart_outcome")) } ?? .null]
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeRestartOutcomeWrite?(state.job_id)
                #endif
                _ = try spool.commitRecord(kind: "restart_outcome", cycle: UInt64(max(state.completed_shops, 0)), payload: NG2CycleWire.object(body))
                success = true
            } catch { }
            let durable = success
            self.controlQueue.async {
                defer { self.finishCampaignPersistence(run, persistenceToken) }
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false
                    if durable { cycle.storedCaptureIDs.insert(frame.id) }
                    guard let currentCore = run.core, run.generation == generation, run.cancelReason == 0,
                          !run.stopped, self.ownerActive(run) else { return }
                    if durable {
                        if ng2_controller_cycle_outcome_commit(currentCore, state.job_id, frame.id, frame.prefix, Self.now()) == 1 {
                            cycle.completed.append(.object(NG2CycleWire.companion(state)))
                            cycle.frames.removeAll(); cycle.assessment = nil; cycle.assessmentAdopted = false; cycle.rawSHA256 = nil
                        }
                    } else {
                        cycle.failure = "restart_outcome_commit_failed"
                        _ = ng2_controller_cycle_storage_failed(currentCore, state.job_id, Self.now())
                    }
                }
                self.refreshCycleEvidence(run); self.cycle(run)
            }
            #if NG2_RUNTIME_HOST_TEST
            if run.campaign != nil { NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn?(run.id, "outcome") }
            #endif
        }
    }

    private func cycleFrameMetadata(_ frame: NG2Frame) -> [String: Any] {
        ["capture_id": frame.id, "capture_start_ns": frame.start, "capture_end_ns": frame.end,
         "decode_end_ns": frame.decodeEnd, "generation": frame.generation,
         "completed_prefix_start": frame.startPrefix, "completed_prefix_end": frame.prefix,
         "inflight_start": frame.startInFlight, "inflight_end": frame.endInFlight,
         "stable_prefix": frame.stable, "pixel_width": 896, "pixel_height": 414,
         "analysis_start_ns": frame.analysisStart, "analysis_end_ns": frame.analysisEnd]
    }

    private func persistCycleCheckpoint(_ run: NG2Run) {
        guard let cycle = run.cycle, let core = run.core else { return }
        var state = NG2ControllerCycleStatus(); ng2_controller_cycle_status(core, &state)
        let admission: (NG2CycleSpool, [NG2Frame], Set<UInt64>, NG2ControllerSnapshot?, [String: JSONValue]?, String?, UInt64)? = run.lock.ng2Locked {
            guard state.job_id != 0, state.pending == 0, state.assessment_ns != 0, state.pause_capture_id != 0,
                  state.durable_ns == 0, cycle.checkpointJob != state.job_id, !cycle.persistenceOutstanding,
                  run.cancelReason == 0, !run.stopped, let spool = cycle.spool else { return nil }
            cycle.checkpointJob = state.job_id; cycle.persistenceOutstanding = true
            let ids = Set([state.capture_id, state.pause_source_capture_id, state.pause_capture_id].filter { $0 != 0 })
            let frames = ids.compactMap { cycle.frames[$0] }
            return (spool, frames, ids, run.controllerSnapshot, cycle.assessment, cycle.rawSHA256, run.generation)
        }
        guard let (spool, frames, ids, snapshot, assessment, rawSHA, generation) = admission else { return }
        let previousStored = run.lock.ng2Locked { cycle.storedCaptureIDs }
        let adopted = run.lock.ng2Locked { cycle.assessmentAdopted }
        let persistenceToken = beginCampaignPersistence(run, kind: "checkpoint")
        persistenceQueue.async {
            var success = false
            do {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeCheckpointWrite?(state.job_id)
                #endif
                guard frames.count == ids.count, frames.count <= 6 else { throw NG2CycleSpool.Failure.invalid("checkpoint-frames") }
                let fresh = frames.filter { !previousStored.contains($0.id) }
                try spool.reserveCheckpoint(frames: fresh.count + 3, metadataBytes: 128 * 1024)
                for frame in fresh { _ = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba, metadata: self.cycleFrameMetadata(frame)) }
                var payload: [String: JSONValue] = ["run_id": .string(run.id), "clock_id": .string(run.clock),
                    "generation": NG2CycleWire.number(generation), "cycle": .object(NG2CycleWire.companion(state)),
                    "assessment": assessment.map { .object($0) } ?? .null,
                    "assessment_adopted": .bool(adopted),
                    "raw_sha256": rawSHA.map { .string($0) } ?? .null,
                    "capture_ids": .array(ids.sorted().map { NG2CycleWire.number($0) })]
                payload["controller"] = snapshot.map { .object(self.encodeCycleSnapshot($0, origin: "cycle_checkpoint")) } ?? .null
                _ = try spool.commitRecord(kind: "checkpoint", cycle: UInt64(state.completed_shops), payload: NG2CycleWire.object(payload))
                success = true
            } catch { }
            let durable = success
            self.controlQueue.async {
                defer { self.finishCampaignPersistence(run, persistenceToken) }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforePersistenceCommit?(state.job_id)
                #endif
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false
                    if durable { cycle.storedCaptureIDs.formUnion(ids) }
                    guard let currentCore = run.core, run.generation == generation, run.cancelReason == 0,
                          !run.stopped, self.ownerActive(run) else { return }
                    if durable { _ = ng2_controller_cycle_durable(currentCore, state.job_id, state.capture_id, state.prefix, Self.now()) }
                    else {
                        cycle.failure = "checkpoint_commit_failed"
                        _ = ng2_controller_cycle_storage_failed(currentCore, state.job_id, Self.now())
                    }
                }
                self.refreshCycleEvidence(run); self.notifyCycleIfNeeded(run); self.cycle(run)
            }
            #if NG2_RUNTIME_HOST_TEST
            if run.campaign != nil { NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn?(run.id, "checkpoint") }
            #endif
        }
    }

    private func persistCycleTerminal(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        if run.irregular != nil {
            let drained = run.lock.ng2Locked {
                !cycle.workerBusy && captureReturnedLocked(run) && !run.captureOutstanding
                    && run.capturePipelineIDs.isEmpty && !run.mainOutstanding
            }
            guard drained else { return }
            // Logical UNKNOWN remains poisoned; only its actual callbacks have
            // returned. Releasing unused credits grants no input permission.
            releaseIrregularReservation(run, allowDrainedPoison: true)
        }
        let admission: (NG2CycleSpool, [NG2Frame], Set<UInt64>, NG2ControllerSnapshot?, NG2ControllerCycleStatus)? = run.lock.ng2Locked {
            guard !cycle.terminalPersistenceStarted, !cycle.workerBusy,
                  (run.restartYield?.captureControlTokens.isEmpty ?? true), let spool = cycle.spool else { return nil }
            cycle.terminalPersistenceStarted = true; cycle.persistenceOutstanding = true
            var selected = selectedExportFrames(run)
            if let boundary = run.restartYield {
                // Dedicated cycle export emits every durable Spool frame.
                // Keep selected24/pin24; history is a deduplicated raw44 union.
                var originals = Dictionary(uniqueKeysWithValues: selected.map { ($0.id, $0) })
                for frame in boundary.classificationFrames { originals[frame.id] = frame }
                selected = originals.values.sorted { $0.id < $1.id }
            }
            if let irregular = run.irregular, irregular.checkpointEpisode != 0,
               irregular.companion.outcome_ns == 0 {
                var required = Set(irregular.roles.values)
                if let boundary = run.restartYield {
                    required.formUnion([boundary.firstFloor?.id, boundary.firstPartial?.id,
                        boundary.firstFull?.id].compactMap { $0 })
                    required.formUnion(boundary.classificationSources.keys)
                }
                required.formUnion([irregular.companion.before_capture_id, irregular.companion.proof_capture_id,
                    irregular.companion.trigger_capture_id, irregular.companion.live_baseline_capture_id,
                    cycle.companion.capture_id, cycle.companion.queued_capture_id,
                    cycle.companion.pause_source_capture_id, cycle.companion.pause_capture_id].filter { $0 != 0 })
                if let terminal = run.images.last { required.insert(terminal.id) }
                // The reserved terminal role is one new raster; incidental
                // animation captures are not extra unreserved episode roles.
                selected = selected.filter { required.contains($0.id) || cycle.storedCaptureIDs.contains($0.id) }
            }
            return (spool, selected, cycle.storedCaptureIDs, run.controllerSnapshot, cycle.companion)
        }
        guard let (spool, frames, stored, snapshot, state) = admission else {
            run.lock.ng2Locked { if cycle.spool == nil && !cycle.workerBusy { cycle.terminalPersisted = true } }
            return
        }
        let assessment = run.lock.ng2Locked { cycle.assessment }
        let adopted = run.lock.ng2Locked { cycle.assessmentAdopted }
        let irregularProjection: [String: JSONValue]? = run.lock.ng2Locked {
            guard let irregular = run.irregular else { return nil }
            return irregular.recoveredProjection ?? (try? NG2CycleWire.irregular(irregular.companion))
        }
        let persistenceToken = beginCampaignPersistence(run, kind: "terminal")
        persistenceQueue.async {
            var saved = Set<UInt64>()
            var failure: String?
            var terminalRecord: NG2CycleSpool.RecordRef?
            do {
                let fresh = frames.filter { !stored.contains($0.id) }
                try spool.reserveCheckpoint(frames: fresh.count, metadataBytes: 256 * 1024, finalization: run.irregular != nil)
                for frame in fresh {
                    _ = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba, metadata: self.cycleFrameMetadata(frame)); saved.insert(frame.id)
                }
                var body: [String: JSONValue] = ["cycle": .object(NG2CycleWire.companion(state)),
                    "assessment": assessment.map { .object($0) } ?? .null, "assessment_adopted": .bool(adopted),
                    "controller": snapshot.map { .object(self.encodeCycleSnapshot($0, origin: "cycle_terminal")) } ?? .null]
                if run.irregular != nil {
                    guard let irregularProjection else { throw NG2CycleSpool.Failure.invalid("irregular-terminal-status") }
                    body["irregular"] = .object(irregularProjection)
                }
                if run.campaign != nil, var controller = body["controller"]?.objectValue {
                    controller["continuous_campaign"] = .object(self.continuousCompanion(run.campaignContinuation))
                    body["controller"] = .object(controller)
                }
                terminalRecord = try spool.commitRecord(kind: "terminal", cycle: UInt64(max(state.completed_shops, 0)), payload: NG2CycleWire.object(body))
            } catch { failure = "terminal_commit_failed" }
            self.controlQueue.async {
                defer { self.finishCampaignPersistence(run, persistenceToken) }
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false; cycle.terminalPersisted = true
                    cycle.terminalRecord = terminalRecord
                    cycle.storedCaptureIDs.formUnion(saved)
                    if let failure { cycle.failure = failure }
                }
                self.notifyCycleIfNeeded(run); self.cycle(run)
            }
            #if NG2_RUNTIME_HOST_TEST
            if run.campaign != nil { NG2RuntimeContinuousTestHooks.afterPersistenceEnqueueBeforeReturn?(run.id, "terminal") }
            #endif
        }
    }

    private func notifyCycleIfNeeded(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        if let root = run.campaign, run.campaignContinuation.qualified == 1,
           root.permits(Self.now()), root.gate.ng2Locked({ !root.stopped }) { return }
        let outcome: Int32? = run.lock.ng2Locked {
            let preparedDiagnostic = run.campaign != nil && cycle.terminalRecord == nil
            guard (!cycle.recovered || preparedDiagnostic), !cycle.notificationRequested, ownerActive(run) else { return nil }
            let positive = run.controllerSnapshot?.status.paused == 1 && run.cancelReason == 0
                && (cycle.companion.outcome == 1 || cycle.companion.outcome == 2)
            let hintHeld = run.irregular?.companion.stage == 9 && run.irregular?.companion.held_reason == 4
            guard positive || (run.terminal && cycleWorkersDrainedLocked(run, cycle)) else { return nil }
            cycle.notificationRequested = true; cycle.notificationState = "pending"
            return positive ? cycle.companion.outcome : (hintHeld ? 3 : -1)
        }
        guard let outcome else { return }
        #if NG2_RUNTIME_HOST_TEST
        run.lock.ng2Locked { cycle.notificationState = "requested" }
        NG2RuntimeCycleTestHooks.afterNotification?(run.id)
        #else
        let content = UNMutableNotificationContent()
        if outcome < 0 {
            content.title = "自動操作を停止しました"
            content.body = "iSHで保存を確認してください。"
        } else {
            content.title = outcome == 2 ? "のろいのゆびわを確認" : "のろいのゆびわの候補を保持"
            content.body = outcome == 3 ? "未採用の解析結果に候補があるため停止しました。iSHで記録を確認してください。"
                : "ゲームをポーズしました。商品を確認してください。"
        }
        content.sound = .default
        let request = UNNotificationRequest(identifier: "necro-cycle-" + run.id, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { error in
            run.lock.ng2Locked { cycle.notificationState = error == nil ? "requested" : "failed" }
        }
        #endif
    }

    private func beginCycleScan() {
        let start = lock.ng2Locked { () -> Bool in
            guard !cycleScanStarted else { return false }
            cycleScanStarted = true; cycleScanState = "pending"; return true
        }
        guard start else { return }
        persistenceQueue.async {
            do {
                let pending: [String]
                #if NG2_RUNTIME_HOST_TEST
                if let root = NG2RuntimeCycleTestHooks.spoolRoot { pending = try NG2CycleSpool.testUnpublishedRunIDs(rootURL: root) }
                else { pending = try NG2CycleSpool.unpublishedRunIDs() }
                #else
                pending = try NG2CycleSpool.unpublishedRunIDs()
                #endif
                self.lock.ng2Locked { self.unpublishedCycles = pending; self.cycleScanState = "ready" }
            } catch { self.lock.ng2Locked { self.cycleScanState = "failed" } }
        }
    }

    private func prepareCycleNotifications(request: Bool) {
        #if NG2_RUNTIME_HOST_TEST
        lock.ng2Locked { notificationAuthorization = NG2RuntimeCycleTestHooks.notificationAuthorization }
        #else
        let start = lock.ng2Locked { () -> Bool in
            guard !notificationPreparationStarted else { return false }
            notificationPreparationStarted = true; return true
        }
        guard start else { return }
        let center = UNUserNotificationCenter.current()
        center.getNotificationSettings { settings in
            let state: String
            switch settings.authorizationStatus {
            case .authorized: state = "authorized"
            case .provisional, .ephemeral: state = "provisional"
            case .denied: state = "denied"
            case .notDetermined: state = "not_determined"
            @unknown default: state = "unavailable"
            }
            self.lock.ng2Locked { self.notificationAuthorization = state; self.notificationPreparationStarted = false }
            guard request && state == "not_determined" else { return }
            DispatchQueue.main.async {
                guard let bundle = Bundle.main.bundleIdentifier else { return }
                let runnerPID = ForegroundApp.processID(forBundleID: bundle)
                guard runnerPID > 0 && ForegroundApp.frontmostPID() == runnerPID else { return }
                let admitted = self.lock.ng2Locked { () -> Bool in
                    guard !self.notificationPreparationStarted else { return false }
                    self.notificationPreparationStarted = true; self.notificationAuthorization = "pending"; return true
                }
                guard admitted else { return }
                center.requestAuthorization(options: [.alert, .sound]) { granted, error in
                    self.lock.ng2Locked {
                        self.notificationAuthorization = error == nil ? (granted ? "authorized" : "denied") : "unavailable"
                        self.notificationPreparationStarted = false
                    }
                }
            }
        }
        #endif
    }

    private func initializeCycle(_ run: NG2Run, continuationFrom predecessor: NG2Run? = nil) {
        guard let cycle = run.cycle else { return }
        if let root = run.campaign { root.gate.ng2Locked { root.pendingIO = true } }
        run.lock.ng2Locked { cycle.persistenceOutstanding = true }
        persistenceQueue.async {
            do {
                var provenance: [String: Any] = ["clock_id": run.clock, "accepted_started_ns": run.acceptedStarted,
                    "generation": run.generation, "runtime_instance_id": self.runtimeInstanceID,
                    "system_uptime_ns": UInt64(ProcessInfo.processInfo.systemUptime * 1_000_000_000)]
                if run.irregular != nil { provenance["native_profile"] = run.profile }
                if run.yieldAfterRestart && run.campaign == nil { provenance["yield_after_restart"] = true }
                if let root = run.campaign {
                    provenance["continuous_campaign"] = ["schema": "ngg2-continuous-child-v1",
                        "root_id": root.id, "index": run.campaignIndex,
                        "predecessor_id": run.campaignPredecessor as Any? ?? NSNull(),
                        "root_started_ns": root.started, "root_deadline_ns": root.deadline]
                }
                let spool: NG2CycleSpool
                #if NG2_RUNTIME_HOST_TEST
                if let root = NG2RuntimeCycleTestHooks.spoolRoot {
                    spool = try NG2CycleSpool.testCreate(rootURL: root, runID: run.id, owner: run.owner, provenance: provenance,
                        quota: run.campaign?.quota, reservation: run.campaignReservation)
                } else { spool = try NG2CycleSpool.create(runID: run.id, owner: run.owner, provenance: provenance,
                    quota: run.campaign?.quota, reservation: run.campaignReservation) }
                #else
                spool = try NG2CycleSpool.create(runID: run.id, owner: run.owner, provenance: provenance,
                    quota: run.campaign?.quota, reservation: run.campaignReservation)
                #endif
                try spool.reserveCheckpoint(frames: 6, metadataBytes: 256 * 1024)
                self.controlQueue.async {
                    let active = run.lock.ng2Locked { () -> Bool in
                        cycle.spool = spool; cycle.persistenceOutstanding = false
                        let now = Self.now()
                        return run.cancelReason == 0 && !run.stopped && self.ownerActive(run)
                            && now >= run.acceptedStarted && now - run.acceptedStarted < 180_000_000_000
                    }
                    self.lock.ng2Locked { if !self.unpublishedCycles.contains(run.id) { self.unpublishedCycles.append(run.id) } }
                    if active, let predecessor {
                        self.persistenceQueue.async {
                            self.controlQueue.async { self.commitContinuousChild(run, replacing: predecessor) }
                        }
                    } else if active, let root = run.campaign {
                        self.persistenceQueue.async {
                            self.controlQueue.async {
                                root.gate.ng2Locked { root.pendingIO = false }
                                if root.permits(Self.now()), run.lock.ng2Locked({ run.cancelReason == 0 }) {
                                    self.start(run)
                                } else { self.abortPreparedChild(run, predecessor: nil, reason: "cancelled") }
                            }
                        }
                    } else if active { self.start(run) }
                    else {
                        if run.lock.ng2Locked({ run.cancelReason == 0 }) { run.cancel(15) }
                        run.lock.ng2Locked {
                            cycle.companion.state = 8; cycle.companion.status = 2
                            run.terminal = true; run.captureWorkerDone = true; run.lease = false
                        }
                        if let root = run.campaign {
                            self.persistenceQueue.async {
                                self.controlQueue.async {
                                    self.abortPreparedChild(run, predecessor: predecessor,
                                        reason: root.cancelReason == 2 ? "cancelled" : "storage")
                                }
                            }
                        }
                    }
                }
            } catch {
                self.controlQueue.async {
                    run.cancel(6)
                    run.lock.ng2Locked {
                        cycle.persistenceOutstanding = false; cycle.failure = "spool_initialization_failed"
                        cycle.companion.state = 8; cycle.companion.status = 3
                        run.terminal = true; run.captureWorkerDone = true; run.lease = false
                    }
                    if run.campaign != nil {
                        self.persistenceQueue.async {
                            self.controlQueue.async { self.abortPreparedChild(run, predecessor: predecessor, reason: "storage") }
                        }
                    }
                    self.lock.ng2Locked { if !self.unpublishedCycles.contains(run.id) { self.unpublishedCycles.append(run.id) } }
                }
            }
        }
    }

    private func cyclePayload(_ run: NG2Run) -> [String: JSONValue] {
        let permission = lock.ng2Locked { notificationAuthorization }
        return run.lock.ng2Locked {
            let status = run.controllerSnapshot?.status
            let cycle = run.cycle!
            let drained = cycleWorkersDrainedLocked(run, cycle)
            var payload: [String: JSONValue] = ["state": .string(run.terminal ? (run.lease ? "draining" : "stopped") : "running"),
                "terminal": .bool(run.terminal), "workers_drained": .bool(drained),
                "input_state": .int(Int(status?.input_state ?? cycle.recoveredInputState)), "ui_frozen": .bool(run.uiFrozen),
                "native_inflight": .bool(run.inFlight && !drained), "cycle": .object(NG2CycleWire.companion(cycle.companion)),
                "notification": .object(["authorization": .string(permission), "state": .string(cycle.notificationState)])]
            if let irregular = run.irregular {
                payload["irregular"] = .object(irregular.recoveredProjection
                    ?? (try? NG2CycleWire.irregular(irregular.companion)) ?? [:])
            }
            return payload
        }
    }

    // Caller holds run.lock. Historical UNKNOWN remains input_state4/frozen;
    // it is distinct from an actual native callback that is still executing.
    private func cycleWorkersDrainedLocked(_ run: NG2Run, _ cycle: NG2CycleRun) -> Bool {
        !run.lease && !cycle.workerBusy && captureReturnedLocked(run) && !run.captureOutstanding && !run.mainOutstanding
            && (run.restartYield?.captureControlTokens.isEmpty ?? true)
    }
    // The worker's defer can enqueue a control callback before Thread.main
    // actually returns. Only continuous mode owns a retained worker handle;
    // its terminal timer polls completion and retires that handle afterward.
    private func captureReturnedLocked(_ run: NG2Run) -> Bool {
        guard run.captureWorkerDone else { return false }
        guard run.campaign != nil, let worker = run.captureThread else { return true }
        guard worker.isFinished else { return false }
        run.captureThread = nil
        return true
    }

    private func beginCycleRecovery(owner: String, id: String, placeholder: NG2Run? = nil) {
        let admitted = lock.ng2Locked { () -> Bool in
            guard !cycleRecoveryPending.contains(id), recoveredCycles.count < 16 else { return false }
            cycleRecoveryPending.insert(id); return true
        }
        guard admitted else { return }
        persistenceQueue.async {
            defer { self.lock.ng2Locked { self.cycleRecoveryPending.remove(id) } }
            do {
                let spool: NG2CycleSpool
                #if NG2_RUNTIME_HOST_TEST
                if let root = NG2RuntimeCycleTestHooks.spoolRoot { spool = try NG2CycleSpool.testRecover(rootURL: root, runID: id, owner: owner) }
                else { spool = try NG2CycleSpool.recover(runID: id, owner: owner) }
                #else
                spool = try NG2CycleSpool.recover(runID: id, owner: owner)
                #endif
                var clock: String?
                var recoveredProfile = placeholder?.campaign != nil ? Self.irregularProfile : Self.cycleProfile
                var recoveredYield = false
                if let header = try? spool.sessionBytes(),
                   let object = try? JSONSerialization.jsonObject(with: header) as? [String: Any],
                   let provenance = object["provenance"] as? [String: Any] {
                    if let storedProfile = provenance["native_profile"] {
                        guard let name = storedProfile as? String,
                              NG2CycleWire.ProtocolSpec.forProfile(name) != nil else {
                            throw NG2CycleSpool.Failure.invalid("recovery-native-profile")
                        }
                        recoveredProfile = name
                    }
                    if let value = provenance["yield_after_restart"] {
                        guard recoveredProfile == Self.irregularProfile,
                              let bool = value as? NSNumber, CFGetTypeID(bool) == CFBooleanGetTypeID(), bool.boolValue else {
                            throw NG2CycleSpool.Failure.invalid("recovery-restart-yield")
                        }
                        recoveredYield = true
                    }
                    if let original = provenance["clock_id"] as? String, self.lowerHexIdentity(original) { clock = original }
                }
                let run = NG2Run(owner: owner, id: id, now: Self.now(), profile: recoveredProfile, clock: clock, yieldAfterRestart: recoveredYield)
                let cycle = run.cycle!
                cycle.spool = spool; cycle.recovered = true; cycle.terminalPersisted = true
                cycle.companion.state = 8
                run.terminal = true; run.stopped = true; run.lease = false; run.captureWorkerDone = true
                let records = try spool.records()
                guard run.irregular != nil || !records.contains(where: { $0.kind.hasPrefix("irregular_") }) else {
                    throw NG2CycleSpool.Failure.invalid("recovery-record-profile")
                }
                let intents = records.filter { $0.kind == "restart_intent" }
                let outcomes = records.filter { $0.kind == "restart_outcome" }
                let dangling = intents.contains { intent in
                    guard let command = intent.payload["command"] as? [String: Any],
                          let commandID = command["id"] as? NSNumber else { return true }
                    return !outcomes.contains { outcome in
                        guard outcome.sequence > intent.sequence,
                              let source = outcome.payload["cycle"] as? [String: Any],
                              let completed = source["restart_command_id"] as? NSNumber else { return false }
                        return completed.uint64Value == commandID.uint64Value
                    }
                }
                var unknown = records.contains { record in
                    let controller = record.payload["controller"] as? [String: Any]
                    return (controller?["input_state"] as? NSNumber)?.intValue == 4
                }
                var irregularDangling = false
                if let irregular = run.irregular {
                    // Recovery is read-only. Numeric identity must not accept
                    // booleans, floating point truncation or a foreign episode.
                    func u(_ value: Any?) -> UInt64? {
                        guard let number = value as? NSNumber,
                              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: number.objCType)),
                              number.int64Value >= 0, number.uint64Value < UInt64(Int64.max) else { return nil }
                        return number.uint64Value
                    }
                    for (intentKind, outcomeKind, action, captureKey, commandKey, captureRole) in [
                        ("irregular_continue_intent", "irregular_continue_outcome", UInt64(5), "continue_capture_id", "continue_command_id", "continue_outcome"),
                        ("irregular_restart_intent", "irregular_restart_outcome", UInt64(3), "next_floor_capture_id", "restart_command_id", "new_floor")
                    ] {
                        for intent in records where intent.kind == intentKind {
                            guard let command = intent.payload["command"] as? [String: Any],
                                  let commandID = u(command["id"]), commandID > 0, u(command["kind"]) == action,
                                  let original = intent.payload["irregular"] as? [String: Any],
                                  let episode = u(original["episode_id"]), episode > 0,
                                  u(original[commandKey]) == commandID,
                                  let generation = u(intent.payload["generation"]) else {
                                irregularDangling = true; continue
                            }
                            let complete = records.contains { outcome in
                                guard outcome.kind == outcomeKind, outcome.sequence > intent.sequence,
                                      u(outcome.payload["generation"]) == generation,
                                      let state = outcome.payload["irregular"] as? [String: Any],
                                      u(state["episode_id"]) == episode, u(state["prefix"]) == commandID,
                                      u(state[commandKey]) == commandID,
                                      let capture = u(state[captureKey]), capture > 0,
                                      let frames = outcome.payload["frames"] as? [[String: Any]],
                                      frames.contains(where: { $0["role"] as? String == captureRole
                                          && u($0["capture_id"]) == capture && u($0["prefix"]) == commandID
                                          && u($0["generation"]) == generation }),
                                      let savedCommand = outcome.payload["command"] as? [String: Any],
                                      u(savedCommand["id"]) == commandID, u(savedCommand["kind"]) == action,
                                      let ack = outcome.payload["ack"] as? [String: Any],
                                      u(ack["command_id"]) == commandID, u(ack["kind"]) == action,
                                      ack["outcome"] as? String == "acked",
                                      let started = u(ack["started_ns"]), started > 0,
                                      let ended = u(ack["completed_ns"]), ended >= started else { return false }
                                return true
                            }
                            if !complete { irregularDangling = true }
                        }
                    }
                    unknown = unknown || records.contains { record in
                        if let ack = record.payload["ack"] as? [String: Any], ack["outcome"] as? String == "unknown" { return true }
                        if let state = record.payload["irregular"] as? [String: Any],
                           state["held_reason"] as? String == "unknown_input" { return true }
                        let controller = record.payload["controller"] as? [String: Any]
                        let events = controller?["events"] as? [[String: Any]] ?? []
                        return events.contains { u($0["outcome"]) == 4 }
                    }
                    if let raw = records.last(where: { $0.payload["irregular"] != nil })?.payload["irregular"] as? [String: Any] {
                        let reference = try NG2CycleWire.irregular(irregular.companion)
                        let numeric = reference.keys.filter { !["enabled", "kind", "stage", "held_reason"].contains($0) }
                        let value = try NG2CycleWire.decode(raw)
                        guard Set(value.keys) == Set(reference.keys),
                              let enabled = value["enabled"], case .bool = enabled,
                              u(raw["abi_version"]) == 1, numeric.allSatisfy({ u(raw[$0]) != nil }),
                              ["none", "stalled", "death"].contains(raw["kind"] as? String ?? ""),
                              ["idle", "quiesce", "checkpoint", "pause", "death_continue", "wait_menu", "restart_ready", "wait_restart", "outcome", "held"].contains(raw["stage"] as? String ?? ""),
                              ["none", "menu_unrecognized", "deadline", "storage", "candidate", "unknown_input", "invalid_ui", "classification", "baseline_unavailable", "limit", "control_invalid"].contains(raw["held_reason"] as? String ?? "") else {
                            throw NG2CycleSpool.Failure.invalid("recovery-irregular-status")
                        }
                        irregular.recoveredProjection = value
                    }
                }
                let noTerminal = !records.contains(where: { $0.kind == "terminal" })
                if noTerminal || dangling || irregularDangling || unknown { cycle.recoveredInputState = 4; run.uiFrozen = true }
                if let payload = records.last(where: { $0.payload["cycle"] != nil })?.payload,
                   let value = payload["cycle"] as? [String: Any] {
                    func n(_ key: String) -> UInt64 { (value[key] as? NSNumber)?.uint64Value ?? 0 }
                    cycle.companion.level_id = n("level_id"); cycle.companion.job_id = n("job_id")
                    cycle.companion.capture_id = n("capture_id"); cycle.companion.prefix = n("prefix")
                    cycle.companion.completed_shops = Int32(n("completed_shops"))
                    cycle.companion.outcome = Int32(["unknown", "candidate", "target", "negative"].firstIndex(of: value["outcome"] as? String ?? "unknown") ?? 0)
                    cycle.companion.coverage = Int32(["unknown", "incomplete", "complete"].firstIndex(of: value["coverage"] as? String ?? "unknown") ?? 0)
                }
                self.lock.ng2Locked { self.recoveredCycles[id] = run }
                if let root = placeholder?.campaign {
                    root.gate.ng2Locked { if root.active?.id == id { root.active = run } }
                }
            } catch {
                self.lock.ng2Locked { self.cycleRecoveryFailures[id] = "evidence_storage_unavailable" }
            }
        }
    }

    private func beginCycleExport(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        let status = cyclePayload(run)
        let exporter: NG2CycleExport? = run.lock.ng2Locked {
            guard run.terminal, !run.lease, !cycle.workerBusy, cycle.exporter == nil, let spool = cycle.spool else { return nil }
            let value = NG2CycleExport(spool: spool, status: status, recovered: cycle.recovered, owner: run.owner,
                spec: NG2CycleWire.ProtocolSpec.forProfile(run.profile)!)
            cycle.exporter = value; return value
        }
        exporter?.prepare()
    }

    private func handleCycle(owner: String, id: String, params: [String: JSONValue], spec: NG2CycleWire.ProtocolSpec = .standard) -> ([String: JSONValue]?, JSONRPCError?) {
        let mode = params["mode"]?.stringValue ?? "status"
        let base: Set<String> = ["run_id", "mode", Self.ownerParam]
        let extra: Set<String>
        switch mode {
        case "campaign_status": extra = ["keepalive"]
        case "trial_support": extra = []
        case "prepare": extra = ["request_authorization"]
        case "status": extra = ["keepalive"]
        case "manifest": extra = []
        case "chunk": extra = ["export_id", "capture_id", "offset"]
        case "record": extra = ["export_id", "sequence", "offset"]
        case "batch": extra = ["export_id", "capture_id", "offset", "count"]
        case "published": extra = ["export_id", "manifest_sha256", "archive_sha256"]
        default: return failure("Unsupported cycle query mode.", -32602)
        }
        guard Set(params.keys).isSubset(of: base.union(extra)),
              AuthManager.shared.clientName(forTokenId: owner) != nil, !RemoteSession.shared.paused else {
            return failure("Invalid or inactive cycle request.", -32602)
        }
        if mode == "campaign_status" {
            guard spec.profile == Self.irregularProfile,
                  let keepalive = params["keepalive"]?.boolValue,
                  let root = lock.ng2Locked({ campaigns[id] }), root.owner == owner else {
                return failure("Native campaign identity is unavailable; recover unpublished evidence.", -32097)
            }
            return (NG2CycleWire.envelope(runID: id, mode: mode,
                payload: campaignPayload(root, keepalive: keepalive), spec: spec), nil)
        }
        if mode == "trial_support" {
            let payload: [String: JSONValue] = ["stop_detail_schema": .string("ngg2-stop-detail-v1"),
                "handoff_schema": .string("ngg2-trial-handoff-v1"), "maximum_run_ids": .int(128),
                "pin_limit": .int(Self.cycleEvidencePinLimit)]
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload, spec: spec), nil)
        }
        if mode == "prepare" {
            guard params["request_authorization"] == nil || params["request_authorization"]?.boolValue != nil else {
                return failure("request_authorization must be boolean.", -32602)
            }
            beginCycleScan(); prepareCycleNotifications(request: params["request_authorization"]?.boolValue ?? false)
            let payload: [String: JSONValue] = lock.ng2Locked {
                let permitted = notificationAuthorization == "authorized" || notificationAuthorization == "provisional"
                let reason = cycleScanState == "failed" ? "recovery_scan_failed" : (cycleScanState != "ready" ? "recovery_scan_pending"
                    : (!unpublishedCycles.isEmpty ? "unpublished_cycle" : (permitted ? "none" : "need_open_loopctrl_notifications")))
                return ["ready": .bool(permitted && cycleScanState == "ready" && unpublishedCycles.isEmpty),
                    "notification_authorization": .string(notificationAuthorization), "recovery_scan": .string(cycleScanState),
                    "unpublished_run_ids": .array(unpublishedCycles.sorted().map { .string($0) }), "reason": .string(reason)]
            }
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload, spec: spec), nil)
        }
        if mode != "status", campaignOwnsExports(owner) {
            return failure("Native campaign evidence is deferred until all gameplay callbacks drain.", -32094)
        }
        let existing = lock.ng2Locked { current }
        let resident = (existing?.id == id && existing?.owner == owner && existing?.cycle != nil)
            || lock.ng2Locked({ recoveredCycles[id]?.owner == owner })
        if mode == "published", !resident, let saved = lock.ng2Locked({ history[id] }), saved.owner == owner,
           let receipt = saved.publication {
            guard receipt.profile == spec.profile,
                  let exportID = params["export_id"]?.stringValue, lowerHexIdentity(exportID),
                  let manifestSHA = params["manifest_sha256"]?.stringValue, isSHA256(manifestSHA),
                  let archiveSHA = params["archive_sha256"]?.stringValue, isSHA256(archiveSHA),
                  receipt.payload["export_id"]?.stringValue == exportID,
                  receipt.payload["manifest_sha256"]?.stringValue == manifestSHA,
                  receipt.payload["archive_sha256"]?.stringValue == archiveSHA else {
                return failure("Cycle publication conflicts with its durable receipt.", -32602)
            }
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: receipt.payload, spec: spec), nil)
        }
        let run: NG2Run?
        if let existing, existing.id == id, existing.owner == owner, existing.cycle != nil,
           existing.lock.ng2Locked({ existing.cycle!.spool != nil || !existing.terminal || existing.lease }) { run = existing }
        else { run = lock.ng2Locked { recoveredCycles[id] }.flatMap { $0.owner == owner ? $0 : nil } }
        guard let run, let cycle = run.cycle else {
            if let existing, existing.id == id, existing.cycle != nil, existing.lock.ng2Locked({ existing.lease }) {
                existing.cancel(5); return failure("Previous cycle workers must drain before read-only recovery.")
            }
            if let reason = lock.ng2Locked({ cycleRecoveryFailures[id] }) { return failure(reason, -32096) }
            beginCycleRecovery(owner: owner, id: id)
            return failure("Native cycle read-only recovery is pending.", -32094)
        }
        guard run.profile == spec.profile else { return failure("Cycle query profile differs from immutable session.", -32602) }
        if mode == "status" {
            guard params["keepalive"] == nil || params["keepalive"]?.boolValue != nil else { return failure("keepalive must be boolean.", -32602) }
            run.lock.ng2Locked {
                if !cycle.recovered && run.campaign == nil && NG2TicketGuard.renewsHeartbeat(keepalive: params["keepalive"]?.boolValue ?? false,
                    ownerActive: ownerActive(run), cancelled: run.cancelReason != 0) { run.heartbeat = Self.now() }
            }
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: cyclePayload(run), spec: spec), nil)
        }
        if let root = run.campaign, root.gate.ng2Locked({ root.lease }) {
            return failure("Native campaign evidence is deferred until all gameplay callbacks drain.", -32094)
        }
        guard run.lock.ng2Locked({ run.terminal && !run.lease && !cycle.workerBusy }) else {
            return failure("Cycle export requires terminal, drained workers.")
        }
        guard run.lock.ng2Locked({ cycle.spool != nil }) else {
            if let reason = lock.ng2Locked({ cycleRecoveryFailures[id] }) { return failure(reason, -32096) }
            lock.ng2Locked { recoveredCycles.removeValue(forKey: id) }
            beginCycleRecovery(owner: owner, id: id, placeholder: run)
            return failure("Native partial initialization evidence recovery is pending.", -32094)
        }
        let exporter: NG2CycleExport? = run.lock.ng2Locked { cycle.exporter }
        guard let exporter else {
            beginCycleExport(run)
            return failure("Native cycle export is being prepared.", -32094)
        }
        let answer: ([String: JSONValue]?, String?)
        if mode == "manifest" { answer = exporter.manifest() }
        else if mode == "published" {
            guard let exportID = params["export_id"]?.stringValue, lowerHexIdentity(exportID),
                  let manifestSHA = params["manifest_sha256"]?.stringValue, isSHA256(manifestSHA),
                  let archiveSHA = params["archive_sha256"]?.stringValue, isSHA256(archiveSHA) else {
                return failure("Invalid cycle publication identity.", -32602)
            }
            answer = exporter.published(exportID: exportID, manifestSHA: manifestSHA, archiveSHA: archiveSHA)
            if answer.0?["accepted"]?.boolValue == true {
                run.lock.ng2Locked { cycle.published = true }
                lock.ng2Locked {
                    let retained = history[run.id].flatMap { $0.owner == run.owner ? $0 : nil }
                    var entry = retained ?? NG2RunHistory(owner: run.owner, response: nil, publication: nil)
                    entry.publication = NG2CyclePublication(profile: run.profile, payload: answer.0!)
                    rememberHistoryLocked(run.id, entry)
                    if let previous = current, previous.id == run.id {
                        previous.lock.ng2Locked { if !previous.lease { previous.cycle?.published = true } }
                    }
                    unpublishedCycles.removeAll(where: { $0 == run.id })
                    if (run.campaign != nil || cycle.recovered) && current !== run { recoveredCycles.removeValue(forKey: run.id) }
                }
            }
        } else {
            guard let exportID = params["export_id"]?.stringValue, lowerHexIdentity(exportID),
                  case .int(let offset)? = params["offset"], offset >= 0, offset < 2 * 1024 * 1024 else {
                return failure("Invalid cycle export identity or offset.", -32602)
            }
            guard let currentExport = exporter.identifier else { return failure("Native cycle export is pending.", -32094) }
            guard currentExport == exportID else { return failure("Cycle export identity changed.", -32602) }
            if mode == "record" {
                guard case .int(let sequence)? = params["sequence"], sequence >= 0 else { return failure("Invalid cycle record sequence.", -32602) }
                answer = exporter.record(sequence: sequence, offset: offset)
            } else {
                guard case .int(let capture)? = params["capture_id"], capture > 0 else { return failure("Invalid cycle capture identity.", -32602) }
                if mode == "batch" {
                    guard case .int(let count)? = params["count"], (1...4).contains(count) else { return failure("Invalid cycle batch count.", -32602) }
                    answer = exporter.batch(requests: (0..<count).map { (captureID: UInt64(capture), offset: offset + $0 * NG2CycleWire.chunkBytes) })
                } else { answer = exporter.chunk(captureID: UInt64(capture), offset: offset) }
            }
            guard answer.0?["export_id"]?.stringValue == exportID || answer.0 == nil else {
                return failure("Cycle export identity changed.")
            }
        }
        guard let payload = answer.0 else {
            let pending = answer.1 == "pending"
            return failure(answer.1 ?? "Native cycle export is pending.", pending ? -32094 : -32004)
        }
        return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload, spec: spec), nil)
    }

    private func isSHA256(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    // Caller owns the Runtime metadata gate. Receipt-only entries have no
    // generic run projection, so recovery metadata cannot grant start/UI.
    private func rememberHistoryLocked(_ id: String, _ entry: NG2RunHistory) {
        history[id] = entry
        if !historyOrder.contains(id) { historyOrder.append(id) }
        if historyOrder.count > 64 { history.removeValue(forKey: historyOrder.removeFirst()) }
    }

    private func cycleNotStarted(_ message: String) -> ([String: JSONValue]?, JSONRPCError?) {
        (nil, JSONRPCError(code: -32095, message: message,
            data: ["outcome": .string("definitive_not_started"), "retry_safe": .bool(true)]))
    }

    private func failure(_ message: String, _ code: Int = -32004) -> ([String: JSONValue]?, JSONRPCError?) {
        (nil, JSONRPCError(code: code, message: message, data: ["outcome": .string("not_sent"), "retry_safe": .bool(false)]))
    }
    private func number(_ value: UInt64) -> JSONValue { .int(Int(min(value, UInt64(Int64.max)))) }
    private func integer(_ value: Int32) -> JSONValue { .int(Int(value)) }
    private func failureInteger(_ value: Int?, signed: Bool) -> JSONValue {
        guard let value else { return .null }
        guard signed ? (Int(Int32.min)...Int(Int32.max)).contains(value) : value >= 0 else { return .null }
        return .int(value)
    }
    private func replyFailure(_ error: String?) -> NG2Raster.FailureCode {
        switch error {
        case "direct capture API unavailable": return .apiUnavailable
        case "direct capture session unavailable": return .sessionUnavailable
        case "direct capture display unprepared": return .displayUnprepared
        case "direct capture request unavailable": return .requestUnavailable
        case "direct capture failed": return .captureFailed
        case "direct capture bytes invalid": return .bytesInvalid
        case "direct capture reply exception": return .replyException
        case "direct capture request exception": return .requestException
        case nil: return .missingData
        default: return .other
        }
    }
    @discardableResult
    private func commitCaptureFailure(_ run: NG2Run, generation failureGeneration: UInt64,
                                      id: UInt64, start: UInt64, end: UInt64,
                                      failure: NG2Raster.Failure) -> Bool {
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeTestHooks.beforeCaptureFailureCommit?(run.id)
        #endif
        return run.lock.ng2Locked {
            guard run.generation == failureGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }
            guard run.captureFailure == nil else { return false }
            run.captureFailure = ["capture_id": number(id), "stage": .string(failure.stage.rawValue),
                "code": .string(failure.code.rawValue), "start_ns": number(start), "end_ns": number(end),
                "encoded_bytes": failureInteger(failure.encodedBytes, signed: false),
                "source_width": failureInteger(failure.sourceWidth, signed: true),
                "source_height": failureInteger(failure.sourceHeight, signed: true),
                "orientation": failureInteger(failure.orientation, signed: true)]
            return true
        }
    }
    private func cancelCaptureFailure(_ run: NG2Run, generation: UInt64) {
        run.lock.ng2Locked {
            guard run.generation == generation, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return }
            run.cancelReason = 20; run.generation &+= 1; run.stopped = true; run.latest = nil
            run.preparation = nil
        }
    }
    // The original activation deadline bounds new requests after a portrait,
    // never an extension or input authority. Called only under run.lock.
    private func startupPortraitGateLocked(_ run: NG2Run, generation: UInt64, now: UInt64) -> Bool {
        guard run.generation == generation, run.cancelReason == 0, !run.stopped else { return false }
        let lost: Int32 = !ownerActive(run) ? 5 : (LockStateMonitor.shared().isLocked ? 4 : 0)
        if lost != 0 {
            run.cancelReason = lost; run.generation &+= 1; run.stopped = true
            run.latest = nil; run.preparation = nil
            return false
        }
        return now >= run.acceptedStarted && !run.startupRasterReady && run.startupRasterDeadline > now && run.startupPortraitFailures < 64
            && run.bootstrapUIStarted && run.prefix == 0 && !run.inFlight
            && run.initial == nil && run.latest == nil && run.analyzedFrames == 0 && run.captures.isEmpty
            && run.mainCommandID == 0 && run.mainCallbacks.isEmpty && run.expectedPID > 0
            && !run.captureOutstanding && run.captureFailure == nil
    }
    private func waitForStartupPortrait(_ run: NG2Run, generation: UInt64,
        startPrefix: UInt64, endPrefix: UInt64, startInFlight: Bool, endInFlight: Bool,
        failure: NG2Raster.Failure) -> Bool {
        guard failure.stage == .metadata, failure.code == .aspect,
              failure.orientation == nil || failure.orientation == 1,
              let width = failure.sourceWidth, let height = failure.sourceHeight,
              width > 0, height > width, height <= 4096, width*height <= 8_000_000,
              width*NG2Raster.width == height*NG2Raster.height,
              startPrefix == 0, endPrefix == 0, !startInFlight, !endInFlight else { return false }
        let expected: pid_t? = run.lock.ng2Locked {
            guard !run.bootstrapOutstanding,
                  self.startupPortraitGateLocked(run, generation: generation, now: Self.now()) else { return nil }
            // This queued callback owns the main lease until it really returns,
            // including when cancellation wins before main gets to execute it.
            run.bootstrapOutstanding = true
            return run.expectedPID
        }
        guard let expected else { return false }
        var retry = false
        DispatchQueue.main.sync {
            guard run.lock.ng2Locked({
                self.startupPortraitGateLocked(run, generation: generation, now: Self.now())
                    && run.expectedPID == expected
            }) else { return }
            let queryStart = Self.now()
            let foreground = ForegroundApp.frontmostPID() == expected
            let queryEnd = Self.now()
            retry = run.lock.ng2Locked {
                let now = Self.now()
                guard self.startupPortraitGateLocked(run, generation: generation, now: now),
                      run.expectedPID == expected else { return false }
                if !foreground {
                    run.cancelReason = 3; run.generation &+= 1; run.stopped = true
                    run.latest = nil; run.preparation = nil
                    return false
                }
                guard NG2TicketGuard.authoritySampleIsFresh(start: queryStart, end: queryEnd, now: now) else { return false }
                run.startupPortraitFailures += 1
                return run.startupPortraitFailures < 64
            }
        }
        run.lock.ng2Locked { run.bootstrapOutstanding = false }
        return retry
    }
    #if NG2_RUNTIME_HOST_TEST
    // Read-only oracle for heartbeat routing; it grants no clock, source or
    // input authority and uses the same root -> active-run lock order.
    func testContinuousHeartbeats(_ rootID: String) -> [UInt64]? {
        guard let root = lock.ng2Locked({ campaigns[rootID] }) else { return nil }
        return root.gate.ng2Locked {
            guard let active = root.active else { return nil }
            return active.lock.ng2Locked { [root.heartbeat, active.heartbeat, root.deadline] }
        }
    }
    // TEST056 HOST METHOD BEGIN.
    // Configure retained rasters and a diagnostic snapshot only after actual
    // workers drain. A temporary core makes the unchanged cache query path
    // executable; its empty diagnostics are replaced by the fixture snapshot.
    // No priority IDs, pin replacement, or export selection are injected.
    func testSeedStopEvidence(_ id: String, pinnedIDs: [UInt64]?, recentIDs: [UInt64],
                              initialID: UInt64, foundID: UInt64 = 0, terminalID: UInt64,
                              changes: [NG2ControllerSceneChange], moveSources: [UInt64]) -> Bool {
        guard recentIDs.count <= 4, changes.count <= 3, moveSources.count <= 64,
              pinnedIDs == nil || (pinnedIDs!.count <= 20 && Set(pinnedIDs!).count == pinnedIDs!.count) else { return false }
        return controlQueue.sync {
            guard let run = lock.ng2Locked({ current }), run.id == id, run.core == nil else { return false }
            let prepared = lock.ng2Locked {
                run.lock.ng2Locked { () -> Bool in
                    guard exportEligibleLocked(run), run.exportBuildID == nil,
                          let original = selectedExportFrames(run).first else { return false }
                    func clone(_ id: UInt64) -> NG2Frame {
                        NG2Frame(id: id, start: original.start, end: original.end, decodeEnd: original.decodeEnd,
                            generation: original.generation, analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                            analysis: original.analysis, startPrefix: original.startPrefix, prefix: original.prefix,
                            startInFlight: original.startInFlight, endInFlight: original.endInFlight, stable: original.stable,
                            rgba: original.rgba, rasterTrace: original.rasterTrace, encodedBytes: original.encodedBytes,
                            diagnosticOrientation: original.diagnosticOrientation)
                    }
                    if let ids = pinnedIDs { run.pinned = Dictionary(uniqueKeysWithValues: ids.map { ($0, clone($0)) }) }
                    run.images = recentIDs.map(clone)
                    run.initial = initialID == 0 ? nil : clone(initialID)
                    run.found = foundID == 0 ? nil : clone(foundID)
                    let configured = Set(run.pinned.keys).union(recentIDs).union([initialID, foundID].filter { $0 != 0 })
                    run.references.formUnion(configured); run.analyzedFrames = max(64, UInt64(run.references.count))
                    run.exportCache = nil
                    return true
                }
            }
            guard prepared, let core = ng2_controller_create(Self.now()) else { return false }
            run.core = core
            defer { NG2RuntimeEvidenceTestHooks.snapshot = nil; ng2_controller_destroy(core); run.core = nil }
            var status = NG2ControllerStatus(); status.terminal = terminalID == 0 ? 0 : 1; status.last_capture_id = terminalID
            let events = moveSources.enumerated().map { index, source -> NG2ControllerEvent in
                var event = NG2ControllerEvent(); event.command.id = UInt64(index+1)
                event.command.kind = 4; event.command.source_capture_id = source
                return event
            }
            NG2RuntimeEvidenceTestHooks.snapshot = (events, changes)
            cache(run, status)
            return true
        }
    }
    // TEST056 HOST METHOD END.
    static var testFrameStride: Int { MemoryLayout<NG2Frame>.stride }
    // Public export tests clone an actual retained raster only after drain.
    // No controller state, input outcome, or production cache is injected.
    func testSeedExportFrames(_ id: String, count: Int) -> Bool {
        guard (1...24).contains(count) else { return false }
        return lock.ng2Locked {
            guard let run = current, run.id == id else { return false }
            return run.lock.ng2Locked {
                guard exportEligibleLocked(run), run.exportBuildID == nil,
                      let frame = selectedExportFrames(run).first else { return false }
                let frames = (0..<count).map { index in
                    NG2Frame(id: UInt64(100 + index), start: frame.start, end: frame.end, decodeEnd: frame.decodeEnd,
                        generation: frame.generation, analysisStart: frame.analysisStart, analysisEnd: frame.analysisEnd,
                        analysis: frame.analysis, startPrefix: frame.startPrefix, prefix: frame.prefix,
                        startInFlight: frame.startInFlight, endInFlight: frame.endInFlight, stable: frame.stable,
                        rgba: frame.rgba, rasterTrace: frame.rasterTrace, encodedBytes: frame.encodedBytes,
                        diagnosticOrientation: frame.diagnosticOrientation)
                }
                run.images = Array(frames.suffix(4)); run.pinned = Dictionary(uniqueKeysWithValues: frames.prefix(20).map { ($0.id, $0) })
                run.initial = frames.first; run.found = nil; run.references = Set(frames.map { $0.id })
                run.analyzedFrames = UInt64(count); run.exportCache = nil
                return true
            }
        }
    }
    func testExportStorageObserver(_ id: String) -> (() -> [Int])? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return { [weak run] in
            guard let run else { return [0, 0, 0, 0, 0, 0] }
            return run.lock.ng2Locked {
                [run.exportCache?.images.values.reduce(0, { $0 + $1.bytes.count }) ?? 0,
                 run.images.count, run.pinned.count, run.initial == nil ? 0 : 1,
                 run.found == nil ? 0 : 1, run.latest == nil ? 0 : 1]
            }
        }
    }
    // Test setup may change only the generation or submit competing failures.
    // Storage still goes through the exact production commit gate, and tests
    // observe only the public status/results projection.
    func testFailureGeneration(_ id: String, advance: Bool = false) -> UInt64? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return run.lock.ng2Locked {
            if advance { run.generation &+= 1 }
            return run.generation
        }
    }
    func testPreparedAuthority(_ id: String, commandID: UInt64) -> [UInt64]? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return run.lock.ng2Locked {
            guard run.mainCommandID == commandID, let lease = run.preparation else { return nil }
            return [lease.authority.start, lease.authority.end, lease.preparedCommandID, lease.key.epoch]
        }
    }
    func testPreparationIdentityCoverage() -> [String: Bool] {
        let first = NG2Run(owner: "fixture-key-owner", id: "fixture-key-run", now: 1_000)
        let other = NG2Run(owner: "fixture-key-owner", id: "fixture-key-other", now: 1_000)
        let base = NG2PreparationKey(testRun: ObjectIdentifier(first), clock: "fixture-clock",
            owner: "fixture-key-owner", generation: 2, expectedPID: 42, prefix: 7,
            epoch: 10, ordinal: 2, target: 300, notBefore: 150, deadline: 160)
        let lease = NG2PreparationLease(key: base, commandID: 10,
            authority: AuthoritySample(start: 100, end: 101, foreground: true))
        let names = ["run", "clock", "owner", "generation", "pid", "prefix", "epoch",
                     "ordinal", "target", "not_before", "deadline"]
        var results: [String: Bool] = [:]
        results["same_identity_shared_new_id"] = lease.matchesIdentity(
            key: base, commandID: 11, currentEpoch: 10)
        for name in names {
            let changed = NG2PreparationKey(
                testRun: name == "run" ? ObjectIdentifier(other) : base.run,
                clock: name == "clock" ? "fixture-other-clock" : base.clock,
                owner: name == "owner" ? "fixture-other-owner" : base.owner,
                generation: name == "generation" ? base.generation+1 : base.generation,
                expectedPID: name == "pid" ? base.expectedPID+1 : base.expectedPID,
                prefix: name == "prefix" ? base.prefix+1 : base.prefix,
                epoch: name == "epoch" ? base.epoch+1 : base.epoch,
                ordinal: name == "ordinal" ? base.ordinal+1 : base.ordinal,
                target: name == "target" ? base.target+1 : base.target,
                notBefore: name == "not_before" ? base.notBefore+1 : base.notBefore,
                deadline: name == "deadline" ? base.deadline+1 : base.deadline)
            results["reject_"+name] = !lease.matchesIdentity(
                key: changed, commandID: 11, currentEpoch: 10)
        }
        results["reject_ACK_epoch_zero"] = !lease.matchesIdentity(
            key: base, commandID: 11, currentEpoch: 0)
        results["reject_changed_C_epoch"] = !lease.matchesIdentity(
            key: base, commandID: 11, currentEpoch: 12)
        let zero = NG2PreparationKey(testRun: base.run, clock: base.clock, owner: base.owner,
            generation: base.generation, expectedPID: base.expectedPID, prefix: base.prefix,
            epoch: 0, ordinal: base.ordinal, target: base.target,
            notBefore: base.notBefore, deadline: base.deadline)
        let single = NG2PreparationLease(key: zero, commandID: 10, authority: lease.authority)
        results["epoch_zero_fresh_single_id"] = single.matchesIdentity(
            key: zero, commandID: 10, currentEpoch: 0)
        results["epoch_zero_reject_other_id"] = !single.matchesIdentity(
            key: zero, commandID: 11, currentEpoch: 0)
        return results
    }
    @discardableResult
    func testPreparationContext(_ id: String, expectedPID: pid_t? = nil, prefix: UInt64? = nil) -> [UInt64]? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return run.lock.ng2Locked {
            let previous = [UInt64(max(0, run.expectedPID)), run.prefix]
            if let expectedPID { run.expectedPID = expectedPID }
            if let prefix { run.prefix = prefix }
            return previous
        }
    }
    func testCachedControllerCapture(_ id: String) -> UInt64? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return run.lock.ng2Locked { run.reportSnapshot?.status.last_capture_id }
    }
    func testIrregularRetentionIDs(_ id: String) -> [String: [UInt64]]? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        return run.lock.ng2Locked {
            ["pinned": run.pinned.keys.sorted(), "irregular": run.irregular?.frames.keys.sorted() ?? [],
             "cycle": run.cycle?.frames.keys.sorted() ?? [], "recent": run.images.map { $0.id },
             "initial_found": [run.initial?.id, run.found?.id].compactMap { $0 },
             "capture_pipeline": run.capturePipelineIDs.sorted()]
        }
    }
    // Combined callback/resource coverage. These are ordinary diagnostic
    // aliases of one real raster, never C observations or input permission.
    func testRestartYieldSaturatePins112(_ id: String) -> Bool {
        guard let run = lock.ng2Locked({ current }), run.id == id, run.yieldAfterRestart else { return false }
        return run.lock.ng2Locked {
            guard !run.terminal, let source = run.images.last else { return false }
            var capture: UInt64 = 1_000_000
            while run.pinned.count < evidencePinLimit(run) {
                if run.pinned[capture] == nil {
                    run.pinned[capture] = NG2Frame(id: capture, start: source.start, end: source.end,
                        decodeEnd: source.decodeEnd, generation: source.generation,
                        analysisStart: source.analysisStart, analysisEnd: source.analysisEnd, analysis: source.analysis,
                        startPrefix: source.startPrefix, prefix: source.prefix, startInFlight: source.startInFlight,
                        endInFlight: source.endInFlight, stable: source.stable, rgba: source.rgba,
                        rasterTrace: source.rasterTrace, encodedBytes: source.encodedBytes,
                        diagnosticOrientation: source.diagnosticOrientation)
                }
                capture += 1
            }
            return run.pinned.count == 24
        }
    }
    // Resource allocator coverage only. Synthetic diagnostic IDs share one
    // real immutable raster; no C scene, source permission or frame is injected.
    func testRestartYieldPinPressure(_ id: String, protectAll: Bool) -> [String: JSONValue]? {
        guard let run = lock.ng2Locked({ current }), run.id == id, run.yieldAfterRestart else { return nil }
        return run.lock.ng2Locked {
            guard let source = run.images.last else { return nil }
            let original = run.pinned, evicted = run.evictedFrames
            defer { run.pinned = original; run.evictedFrames = evicted }
            run.pinned.removeAll()
            for index in 0..<evidencePinLimit(run) {
                let capture = UInt64(1_000_000 + index)
                run.pinned[capture] = NG2Frame(id: capture, start: source.start, end: source.end,
                    decodeEnd: source.decodeEnd, generation: source.generation,
                    analysisStart: source.analysisStart, analysisEnd: source.analysisEnd, analysis: source.analysis,
                    startPrefix: source.startPrefix, prefix: source.prefix, startInFlight: source.startInFlight,
                    endInFlight: source.endInFlight, stable: source.stable, rgba: source.rgba,
                    rasterTrace: source.rasterTrace, encodedBytes: source.encodedBytes,
                    diagnosticOrientation: source.diagnosticOrientation)
            }
            let before = Set(run.pinned.keys)
            let protected = protectAll ? before.union([source.id]) : Set([source.id])
            let accepted = reserveRestartYieldPinLocked(run, frame: source, protected: protected)
            return ["accepted": .bool(accepted), "pin_count": .int(run.pinned.count),
                    "protected_preserved": .bool(protected.subtracting([source.id]).isSubset(of: Set(run.pinned.keys))),
                    "incoming_retained": .bool(run.pinned[source.id] != nil),
                    "evicted": number(run.evictedFrames - evicted)]
        }
    }
    func testRestartYieldState(_ id: String) -> [String: JSONValue]? {
        guard let run = lock.ng2Locked({ current }), run.id == id, let boundary = run.restartYield else { return nil }
        return run.lock.ng2Locked {
            ["basis_pending": .bool(boundary.companion.pending == 1), "C_ready": .bool(boundary.companion.ready == 1),
             "C_invalid": .bool(boundary.companion.invalid != 0),
             "first_floor_capture_id": number(boundary.firstFloor?.id ?? 0),
             "first_goods_capture_id": number(boundary.firstGoods?.id ?? 0),
             "first_partial_capture_id": number(boundary.firstPartial?.id ?? 0),
             "first_full_capture_id": number(boundary.firstFull?.id ?? 0),
             "submitted_goods_ids": .array(boundary.submittedGoodsIDs.sorted().map { number($0) }),
             "first_goods_raw_sha256": boundary.firstGoods.map { .string(NG2CycleWire.hash($0.rgba)) } ?? .null,
             "first_goods_submitted": .bool(boundary.firstGoods != nil && boundary.firstGoodsSubmitted),
             "drain_token_count": .int(run.cycle?.classificationDrainTokens.count ?? 0),
             "capture_paused": .bool(boundary.capturePaused), "control_ready": .bool(boundary.controlReady),
             "capture_control_token_count": .int(boundary.captureControlTokens.count),
             "unique_retained_frame_count": .int(restartYieldRetainedIDsLocked(run).count),
             "classification_source_ids": .array(boundary.classificationSources.keys.sorted().map { number($0) }),
             "epoch_restart_id": number(boundary.epoch?.restart ?? 0)]
        }
    }
    func testOriginalFrameEvidence(_ id: String, captureIDs: [UInt64]) -> [UInt64: (Data, [String: JSONValue])]? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        let frames = run.lock.ng2Locked {
            captureIDs.compactMap { captureID in run.pinned[captureID] ?? run.images.first(where: { $0.id == captureID })
                ?? run.restartYield?.classificationSources[captureID]?.frame }
        }
        guard frames.count == captureIDs.count else { return nil }
        var evidence: [UInt64: (Data, [String: JSONValue])] = [:]
        for frame in frames {
            guard let png = NG2Raster.png(frame.rgba) else { return nil }
            let hash = SHA256.hash(data: png).map { String(format: "%02x", $0) }.joined()
            var metadata = imageMetadata(frame, hash: hash, length: png.count)
            metadata.removeValue(forKey: "byte_length")
            evidence[frame.id] = (png, metadata)
        }
        return evidence
    }
    func testSaturateLiveDiagnosticPins(_ id: String) -> Bool {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return false }
        return run.lock.ng2Locked {
            guard !run.terminal, let original = run.images.last else { return false }
            var captureID: UInt64 = 1_000_000
            while run.pinned.count < 20 {
                if run.pinned[captureID] == nil {
                    run.pinned[captureID] = NG2Frame(id: captureID, start: original.start, end: original.end,
                        decodeEnd: original.decodeEnd, generation: original.generation,
                        analysisStart: original.analysisStart, analysisEnd: original.analysisEnd,
                        analysis: original.analysis, startPrefix: original.startPrefix, prefix: original.prefix,
                        startInFlight: original.startInFlight, endInFlight: original.endInFlight,
                        stable: original.stable, rgba: original.rgba, rasterTrace: original.rasterTrace,
                        encodedBytes: original.encodedBytes, diagnosticOrientation: original.diagnosticOrientation)
                }
                captureID += 1
            }
            return true
        }
    }
    @discardableResult
    func testCommitFailure(_ id: String, generation: UInt64, captureID: UInt64,
                           start: UInt64, end: UInt64, failure: NG2Raster.Failure) -> Bool {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return false }
        return commitCaptureFailure(run, generation: generation, id: captureID, start: start, end: end, failure: failure)
    }
    func testInvalidateControllerTicket(_ id: String) {
        guard let run = lock.ng2Locked({ current }), run.id == id, let core = run.core else { return }
        // Called from final main hook while controlQueue waits for that call.
        ng2_controller_cancel(core, Self.now(), 1)
    }
    func testRecordDispatchFailure(_ id: String, generation: UInt64, command: NG2Command,
                                   start: UInt64, end: UInt64, entry: UInt64, now: UInt64, code: String) {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return }
        run.lock.ng2Locked {
            recordDispatchFailure(run, command, generation: generation,
                authority: AuthoritySample(start: start, end: end, foreground: true), entry: entry, now: now, code: code)
        }
    }
    #endif
    private func response(_ run: NG2Run) -> [String: JSONValue] {
        let projection = run.lock.ng2Locked { NG2ResponseProjection(run) }
        var report = controllerReport(run, projection: projection)
        if report.isEmpty {
            report["events"] = .array([])
            report["motion_references"] = .array([])
            // Accepted response defaults belong only to this response copy.
            report["recovery"] = encodeRecovery(NG2ControllerRecoveryStatus(), records: [])
        }
        report["schema"] = .string("ngg2-native-v1")
        if report["input_state"] == nil { report["input_state"] = .int(0) }
        if projection.inFlight && report["input_state"]?.intValue != 4 { report["input_state"] = .int(2) }
        if report["terminal"] == nil { report["terminal"] = .int(projection.terminal ? 1 : 0) }
        report["clock_id"] = .string(projection.clock)
        report["device_now_ns"] = number(Self.now())
        report["cancel_requested"] = .bool(projection.cancelled)
        report["capture_outstanding"] = .bool(projection.captureOutstanding)
        report["capture_timed_out"] = .bool(projection.captureTimedOut)
        report["bootstrap_ui_started"] = .bool(projection.bootstrapUIStarted)
        report["accepted_started_ns"] = number(projection.acceptedStarted)
        report["workers_drained"] = .bool(!projection.lease)
        report["ui_frozen"] = .bool(projection.uiFrozen)
        report["main_ticket_outstanding"] = .bool(projection.mainOutstanding)
        report["live_completed_prefix"] = number(projection.prefix)
        report["native_inflight"] = .bool(projection.inFlight)
        report["capture_backend"] = .string("direct_daemon_jpeg_only")
        report["analysis_engine"] = .string("native_C_v1")
        report["capture_time_semantics"] = .string("request_call_interval_not_presentation_timestamp")
        report["input_time_semantics"] = .string("synth_call_interval_not_game_receipt_timestamp")
        report["native_capture_requests"] = number(projection.captureID)
        report["latest_frames_replaced"] = number(projection.replacedFrames)
        report["captures"] = .array(projection.captures.map { sample in
            .object(["id": number(sample.id), "start_ns": number(sample.start), "end_ns": number(sample.end),
                "decode_end_ns": number(sample.decodeEnd), "analysis_start_ns": number(sample.analysisStart),
                "analysis_end_ns": number(sample.analysisEnd), "observe_start_ns": number(sample.observeStart),
                "observe_end_ns": number(sample.observeEnd), "completed_prefix_start": number(sample.startPrefix),
                "completed_prefix_end": number(sample.prefix), "inflight_start": .bool(sample.startInFlight),
                "inflight_end": .bool(sample.endInFlight), "stable": .bool(sample.stable)])
        })
        report["raster_samples"] = .array(projection.rasterSamples.map { sample in
            let trace = sample.trace
            return .object(["capture_id": number(sample.id), "source_width": .int(trace.sourceWidth),
                "source_height": .int(trace.sourceHeight), "orientation": .int(trace.orientation),
                "source_ns": number(trace.sourceNs), "draw_ns": number(trace.drawNs),
                "orient_ns": number(trace.orientNs), "scale_ns": number(trace.scaleNs), "copy_pixels": number(trace.copyPixels)])
        })
        report["raster_samples_dropped"] = number(projection.rasterSamplesDropped)
        report["capture_failure"] = projection.captureFailure.map { JSONValue.object($0) } ?? .null
        report["dispatch_failure"] = projection.dispatchFailure.map { JSONValue.object($0) } ?? .null
        report["daemon_requests_outstanding"] = .int(Int(NG2CaptureBridge.pendingRequests))
        report["analyzed_capture_count"] = number(projection.analyzedFrames)
        report["evicted_capture_count"] = number(projection.evictedFrames)
        report["retained_image_count"] = .int(projection.retained.count)
        report["pinned_image_count"] = .int(projection.pinnedCount)
        report["recent_image_count"] = .int(projection.recentCount)
        report["referenced_capture_ids"] = .array(projection.references.sorted().map { number($0) })
        report["missing_capture_ids"] = .array(projection.references.subtracting(projection.retained).sorted().map { number($0) })
        var result: [String: JSONValue] = ["run_id": .string(projection.id), "profile": .string(projection.profile), "state": .string(projection.state),
            "api_version": .string("1.98.16-ngg2"), "report": .object(report)]
        if projection.yieldAfterRestart { result["yield_after_restart"] = .bool(true) }
        if projection.continuousCampaign { result["continuous_campaign"] = .bool(true) }
        return result
    }

    private func historical(_ snapshot: [String: JSONValue]) -> [String: JSONValue] {
        var result = snapshot
        var report = result["report"]?.objectValue ?? [:]
        report["device_now_ns"] = number(Self.now())
        report["historical_metadata_only"] = .bool(true)
        report["retained_image_count"] = .int(0)
        report["pinned_image_count"] = .int(0)
        report["recent_image_count"] = .int(0)
        report["missing_capture_ids"] = report["referenced_capture_ids"] ?? .array([])
        result["report"] = .object(report)
        result["retained_images"] = .int(0)
        result["exported_images"] = .int(0)
        result["omitted_image_count"] = report["analyzed_capture_count"] ?? .int(0)
        result["omitted_capture_ids"] = report["referenced_capture_ids"] ?? .array([])
        return result
    }

    private func start(_ run: NG2Run) {
        if let root = run.campaign, !root.permits(Self.now()) { run.cancel(root.cancelReason == 0 ? 15 : root.cancelReason) }
        let createdCore: OpaquePointer?
        #if NG2_RUNTIME_HOST_TEST
        if run.campaign != nil && NG2RuntimeContinuousTestHooks.failCoreCreation { createdCore = nil }
        else { createdCore = run.cycle == nil ? ng2_controller_create(Self.now()) : ng2_controller_create_cycle(run.acceptedStarted) }
        #else
        createdCore = run.cycle == nil ? ng2_controller_create(Self.now()) : ng2_controller_create_cycle(run.acceptedStarted)
        #endif
        guard let core = createdCore else {
            if run.campaign != nil {
                abortPreparedChild(run, predecessor: nil, reason: "storage"); return
            }
            run.cancel(15); run.lock.ng2Locked { run.terminal = true; run.captureWorkerDone = true; run.lease = false }
            return
        }
        run.core = core
        if run.irregular != nil && ng2_controller_enable_irregular(core) != 1 {
            run.cancel(17)
            run.lock.ng2Locked { run.captureWorkerDone = true }
            ng2_controller_cancel(core, Self.now(), 17); self.cycle(run); return
        }
        let enabled = run.campaign.map { ng2_controller_enable_continuous(core,
            run.campaignIndex == 0 ? 0 : 1, $0.deadline) }
            ?? (run.yieldAfterRestart ? ng2_controller_enable_restart_yield(core) : 1)
        if enabled != 1 {
            run.cancel(17)
            run.lock.ng2Locked { run.captureWorkerDone = true }
            ng2_controller_cancel(core, Self.now(), 17); self.cycle(run); return
        }
        // This independent timer starts before the main-thread barrier and
        // activation. It invalidates a queued bootstrap even if main is stuck.
        let watchdog = DispatchSource.makeTimerSource(queue: watchdogQueue)
        watchdog.schedule(deadline: .now(), repeating: .milliseconds(100))
        watchdog.setEventHandler { [weak self, weak run] in
            guard let self, let run else { return }
            if !self.ownerActive(run) { run.cancel(5) }
            let time = Self.now()
            if let root = run.campaign, !root.permits(time) { run.cancel(root.cancelReason == 0 ? 15 : root.cancelReason) }
            if time >= run.acceptedStarted && time - run.acceptedStarted >= 180_000_000_000 { run.cancel(15) }
            let stale = run.lock.ng2Locked { time > run.heartbeat && time - run.heartbeat > 5_000_000_000 }
            if stale { run.cancel(19) }
            self.controlQueue.async { self.cycle(run) }
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.afterWatchdogCheck?(run.id, time)
            #endif
        }
        run.watchdog = watchdog; watchdog.resume()
        // Barrier behind any UI call already executing when start was accepted.
        // Queued legacy calls are independently refused at their execution site.
        run.lock.ng2Locked { run.bootstrapOutstanding = true }
        DispatchQueue.main.sync {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeContinuousTestHooks.beforeBootstrapAdmission?(run.id, run.campaignIndex)
            #endif
            let lost = self.continuousBootstrapLoss(run)
            if lost != 0 { run.cancel(lost); return }
            if run.lock.ng2Locked({ run.cancelReason == 0 }) && self.ownerActive(run) && !LockStateMonitor.shared().isLocked
                && (run.campaign?.permits(Self.now()) ?? true) {
                // One nonblocking LaunchServices activation also launches the
                // game when needed. No Options/calibration screen is opened.
                let allowed = run.lock.ng2Locked { () -> Bool in
                    if run.cancelReason != 0 || !(run.campaign?.permits(Self.now()) ?? true) { return false }
                    let lost = self.continuousBootstrapLoss(run)
                    if lost != 0 { run.cancelLocked(lost); return false }
                    run.bootstrapUIStarted = true
                    return true
                }
                if run.campaign != nil && !allowed { return }
                if allowed && run.campaignIndex == 0 { _ = ForegroundApp.openBundleID(Self.game) }
                let observedPID = ForegroundApp.processID(forBundleID: Self.game)
                run.expectedPID = run.campaignIndex > 0 ? run.successorPID : observedPID
                run.foreground = run.expectedPID > 0 && ForegroundApp.frontmostPID() == run.expectedPID
                    && observedPID == run.expectedPID
                if run.campaignIndex > 0 && !run.foreground { run.cancel(3); return }
                run.fast = FastActionHandler(app: XCUIApplication(bundleIdentifier: Self.game))
                if !NG2CaptureBridge.prepare() { run.cancel(6) }
            }
        }
        run.lock.ng2Locked { run.bootstrapOutstanding = false }
        let activationDeadline = Self.now() + 3_000_000_000
        run.lock.ng2Locked { run.startupRasterDeadline = activationDeadline }
        while !run.foreground && !run.lock.ng2Locked({ run.stopped }) && Self.now() < activationDeadline {
            let lost = continuousBootstrapLoss(run)
            if lost != 0 { run.cancel(lost); break }
            Thread.sleep(forTimeInterval: 0.05)
            run.lock.ng2Locked { run.bootstrapOutstanding = true }
            DispatchQueue.main.sync {
                let lost = self.continuousBootstrapLoss(run)
                if lost != 0 { run.cancel(lost); return }
                guard run.lock.ng2Locked({ run.cancelReason == 0 }), self.ownerActive(run),
                      !LockStateMonitor.shared().isLocked else { return }
                run.expectedPID = ForegroundApp.processID(forBundleID: Self.game)
                run.foreground = run.expectedPID > 0 && ForegroundApp.frontmostPID() == run.expectedPID
            }
            run.lock.ng2Locked { run.bootstrapOutstanding = false }
        }
        if !run.foreground { run.cancel(3) }
        let timer = DispatchSource.makeTimerSource(queue: controlQueue)
        timer.schedule(deadline: .now(), repeating: .milliseconds(5), leeway: .milliseconds(1))
        timer.setEventHandler { [weak self, weak run] in if let self, let run { self.cycle(run) } }
        run.controlTimer = timer; timer.resume()
        let capture = Thread { [weak self, weak run] in if let self, let run { self.capture(run) } }
        if run.campaign != nil { run.lock.ng2Locked { run.captureThread = capture } }
        capture.name = "NecroGold native capture"; capture.qualityOfService = .userInteractive; capture.start()
    }

    private func capture(_ run: NG2Run) {
        // Only the final failure enters the existing closed wire record. A
        // recovered portrait is never published as a failed game raster.
        var startupPortrait: (generation: UInt64, id: UInt64, start: UInt64, end: UInt64, failure: NG2Raster.Failure)?
        defer {
            run.lock.ng2Locked { run.captureWorkerDone = true; run.capturePipelineIDs.removeAll() }
            controlQueue.async {
                self.cycle(run)
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeTestHooks.afterCaptureDrainProcessed?(run.id)
                #endif
            }
            #if NG2_RUNTIME_HOST_TEST
            if run.campaign != nil { NG2RuntimeContinuousTestHooks.afterCaptureThreadEnqueueBeforeReturn?(run.id) }
            #endif
        }
        while !run.lock.ng2Locked({ run.stopped }) {
            // Return tokens have the same four-entry bound as recent frames;
            // a parked control callback cannot accumulate raw queue closures.
            if !streamsDrained || run.lock.ng2Locked({ run.irregularCapturePaused || (run.restartYield?.capturePaused ?? false)
                || (run.restartYield?.captureControlTokens.count ?? 0) >= 4 }) {
                Thread.sleep(forTimeInterval: 0.005); continue
            }
            let finished = DispatchSemaphore(value: 0)
            let replyLock = NSLock()
            var answered = false
            var raw: Data?
            var captureError: String?
            var captureEnd: UInt64 = 0
            var endPrefix: UInt64 = 0
            var endInFlight = true
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeCaptureAdmission?()
            #endif
            var startupDenied = false, pausedAdmission = false, rawQuotaDenied = false
            let admission: (UInt64, UInt64, Bool, UInt64, UInt64)? = run.lock.ng2Locked {
                guard !run.stopped, run.cancelReason == 0, self.ownerActive(run) else { return nil }
                if run.irregularCapturePaused || (run.restartYield?.capturePaused ?? false)
                    || (run.restartYield?.captureControlTokens.count ?? 0) >= 4 { pausedAdmission = true; return nil }
                if let boundary = run.restartYield,
                   !self.restartYieldRawBudgetFitsLocked(run, adding: run.captureID + 1) {
                    boundary.failed = true; run.cancelLocked(17); rawQuotaDenied = true; return nil
                }
                if let prior = startupPortrait, !run.startupRasterReady,
                   !self.startupPortraitGateLocked(run, generation: prior.generation, now: Self.now()) {
                    startupDenied = run.generation == prior.generation && run.cancelReason == 0 && !run.stopped
                    return nil
                }
                run.captureID += 1; run.captureOutstanding = true
                if run.irregular != nil { run.capturePipelineIDs.insert(run.captureID) }
                return (run.captureID, run.prefix, run.inFlight, run.generation, Self.now())
            }
            guard let before = admission else {
                if rawQuotaDenied {
                    self.controlQueue.async { self.cycle(run) }
                    return
                }
                if pausedAdmission { Thread.sleep(forTimeInterval: 0.005); continue }
                if startupDenied, let prior = startupPortrait {
                    commitCaptureFailure(run, generation: prior.generation, id: prior.id,
                        start: prior.start, end: prior.end, failure: prior.failure)
                    cancelCaptureFailure(run, generation: prior.generation)
                }
                return
            }
            let start = before.4
            NG2CaptureBridge.requestJPEG { data, error in
                let first = replyLock.ng2Locked { () -> Bool in
                    if answered { return false }; answered = true; return true
                }
                guard first else { return }
                captureEnd = Self.now()
                run.lock.ng2Locked {
                    endPrefix = run.prefix; endInFlight = run.inFlight
                    run.captureOutstanding = false
                    if run.generation == before.3 && !run.stopped { raw = data; captureError = error }
                }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeTestHooks.afterCaptureBackendReply?(before.0)
                #endif
                finished.signal()
            }
            if finished.wait(timeout: .now() + 2) != .success {
                run.lock.ng2Locked { run.captureTimedOut = true }
                run.cancel(6)
                // The daemon has no cancellation acknowledgement. Keep its one
                // worker and UI lease until this exact outstanding reply drains.
                finished.wait()
                return
            }
            if run.lock.ng2Locked({ run.stopped || run.generation != before.3 }) { return }
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeCaptureDecode?(before.0)
            #endif
            let decoding: NG2Raster.DecodeResult
            if captureEnd <= start {
                decoding = .failure(.init(stage: .interval, code: .invalidInterval, encodedBytes: raw?.count))
            } else if let raw {
                decoding = NG2Raster.decodeDetailed(raw)
            } else {
                decoding = .failure(.init(stage: .reply, code: replyFailure(captureError)))
            }
            let decoded: NG2Raster.ProfiledResult
            switch decoding {
            case .success(let value):
                decoded = value
                run.lock.ng2Locked {
                    if run.generation == before.3 && run.cancelReason == 0 && !run.stopped && self.ownerActive(run) {
                        run.startupRasterReady = true
                    }
                }
            case .failure(let failure):
                if waitForStartupPortrait(run, generation: before.3, startPrefix: before.1,
                    endPrefix: endPrefix, startInFlight: before.2, endInFlight: endInFlight, failure: failure) {
                    startupPortrait = (before.3, before.0, start, captureEnd, failure)
                    run.lock.ng2Locked { run.capturePipelineIDs.remove(before.0) }
                    Thread.sleep(forTimeInterval: 0.05)
                    continue
                }
                commitCaptureFailure(run, generation: before.3, id: before.0, start: start, end: captureEnd, failure: failure)
                cancelCaptureFailure(run, generation: before.3); return
            }
            let decodeEnd = Self.now()
            let analysis = NG2Analysis()
            let scene = analysis.scene
            let analysisStart = Self.now()
            // Pure image scanning belongs to the existing capture worker. It
            // never touches the controller or blocks its timed ticket queue.
            #if NG2_RUNTIME_HOST_TEST
            let frameRGBA = NG2RuntimeCycleTestHooks.rgba?(decoded.rgba) ?? decoded.rgba
            let analysisRGBA = NG2RuntimeTestHooks.analysisRGBA?(decoded.rgba) ?? frameRGBA
            #else
            let frameRGBA = decoded.rgba
            let analysisRGBA = decoded.rgba
            #endif
            let analyzed = analysisRGBA.withUnsafeBytes { ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                analysisRGBA.count, NG2Raster.stride, scene) }
            var irregularAnalyzed: Int32 = 0
            if run.irregular != nil {
                let flags: UInt32 = run.lock.ng2Locked { run.irregular!.scanRestart ? 1 : 0 }
                #if NG2_RUNTIME_HOST_TEST
                let companionRGBA = NG2RuntimeCycleTestHooks.irregularRGBA?(frameRGBA) ?? frameRGBA
                #else
                let companionRGBA = frameRGBA
                #endif
                irregularAnalyzed = companionRGBA.withUnsafeBytes {
                    ng2_analyze_irregular_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                        companionRGBA.count, NG2Raster.stride, flags, &analysis.irregular)
                }
            }
            let frame = NG2Frame(id: before.0, start: start, end: captureEnd, decodeEnd: decodeEnd,
                generation: before.3, analysisStart: analysisStart, analysisEnd: Self.now(), analysis: analysis,
                startPrefix: before.1, prefix: endPrefix, startInFlight: before.2, endInFlight: endInFlight,
                stable: !before.2 && !endInFlight && before.1 == endPrefix, rgba: frameRGBA,
                rasterTrace: decoded.trace, encodedBytes: raw?.count ?? 0,
                diagnosticOrientation: decoded.diagnosticOrientation)
            #if NG2_RUNTIME_HOST_TEST
            if run.irregular != nil && analyzed == 0 && irregularAnalyzed == 0 {
                NG2RuntimeCycleTestHooks.afterIrregularAnalysis?(frame.id, frame.rgba, analysis.irregular)
            }
            #endif
            if analyzed != 0 || irregularAnalyzed != 0 {
                if analyzed == 0 && irregularAnalyzed != 0 {
                    // The normal raster is valid diagnostic evidence. A failed
                    // companion is never supplied to C as an inspected NONE.
                    run.lock.ng2Locked {
                        if run.generation == before.3 && run.cancelReason == 0 && !run.stopped && self.ownerActive(run) {
                            if run.initial == nil && (run.irregular?.archivedInitialID ?? 0) == 0 { run.initial = frame }
                            run.images.append(frame)
                            if run.images.count > 4 { run.images.removeFirst() }
                            run.terminalCaptureID = frame.id
                        }
                    }
                }
                let trace = frame.rasterTrace
                commitCaptureFailure(run, generation: before.3, id: frame.id, start: frame.start, end: frame.end,
                    failure: .init(stage: .analysis, code: .invalidRGBA, encodedBytes: frame.encodedBytes,
                        sourceWidth: trace.sourceWidth, sourceHeight: trace.sourceHeight, orientation: frame.diagnosticOrientation))
                cancelCaptureFailure(run, generation: before.3); return
            }
            run.lock.ng2Locked {
                if run.generation == before.3 && !run.stopped {
                    self.retainRestartYieldCaptureLocked(run, frame: frame)
                    run.restartYield?.captureControlTokens.insert(frame.id)
                    if let previous = run.latest {
                        run.replacedFrames += 1; run.capturePipelineIDs.remove(previous.id)
                    }
                    run.latest = frame
                } else {
                    run.capturePipelineIDs.remove(frame.id)
                }
            }
            if run.lock.ng2Locked({ run.restartYield?.failed ?? false }) { run.cancel(17) }
            let publishedID = frame.id
            controlQueue.async {
                self.cycle(run)
                if run.yieldAfterRestart {
                    // This serial item follows the actual frame-consumption
                    // callback return, including a frame replaced in latest.
                    self.controlQueue.async {
                        run.lock.ng2Locked { run.restartYield?.captureControlTokens.remove(publishedID) }
                        self.cycle(run)
                    }
                }
            }
            Thread.sleep(forTimeInterval: 0.005)
        }
    }

    // A synchronous PAUSE occupies controlQueue until main's synth returns.
    // Give this already running, bounded full-goods job its original adoption
    // window before asking C to mint that PAUSE. No command is reserved here.
    private func waitForCycleAssessmentBeforePause(_ run: NG2Run, status: NG2ControllerStatus) -> Bool {
        run.lock.ng2Locked {
            if run.yieldAfterRestart && !(run.cycle?.classificationDrainTokens.isEmpty ?? true) { return true }
            guard let cycle = run.cycle, cycle.classificationOutstanding,
                  cycle.companion.pending == 1, cycle.companion.state == Int32(NG2_CYCLE_ASSESS),
                  cycle.companion.full_seen == 1, cycle.companion.worker_started_ns != 0,
                  cycle.companion.capture_id != 0, run.mainCommandID == 0, !run.bootstrapOutstanding,
                  run.cancelReason == 0, !run.stopped, run.foreground, self.ownerActive(run),
                  !LockStateMonitor.shared().isLocked, status.input_state == 0,
                  status.current_command_id == 0, status.terminal == 0, status.goods == 1,
                  status.paused == 0, status.phase == Int32(NG2_PHASE_FINISH),
                  status.last_completed_id == cycle.companion.prefix,
                  let frame = cycle.frames[cycle.companion.capture_id],
                  frame.generation == run.generation, frame.start == cycle.companion.capture_start_ns,
                  frame.startPrefix == cycle.companion.prefix, frame.prefix == cycle.companion.prefix,
                  frame.stable, !frame.startInFlight, !frame.endInFlight else { return false }
            let now = Self.now()
            guard now >= cycle.companion.worker_started_ns, now >= status.started_ns,
                  now - status.started_ns < 180_000_000_000,
                  status.last_capture_end_ns <= now, now <= cycle.companion.deadline_ns else { return false }
            if status.walk_started_ns != 0 &&
                (now < status.walk_started_ns || now - status.walk_started_ns >= 45_000_000_000) { return false }
            return true
        }
    }

    private func waitForIrregularPostCheckpointUI(_ run: NG2Run, status: NG2ControllerStatus) -> Bool {
        run.lock.ng2Locked {
            guard let irregular = run.irregular else { return false }
            let state = irregular.companion
            guard (state.stage == 3 || state.stage == 4), state.durable_ns != 0 else { return false }
            return status.last_capture_id == 0 || status.last_capture_start_ns < state.durable_ns
                || status.last_completed_id != state.prefix
        }
    }

    private func cycle(_ run: NG2Run) {
        guard let core = run.core else { return }
        let now = Self.now()
        if let root = run.campaign {
            if root.cancelReason != 0 { run.cancel(root.cancelReason) }
            else if !root.permits(now) { run.cancel(15) }
        }
        let cancelled = run.lock.ng2Locked { run.cancelReason }
        if cancelled != 0 { ng2_controller_cancel(core, now, cancelled) }
        let frame: NG2Frame? = run.lock.ng2Locked {
            let frame = run.latest; run.latest = nil; return frame
        }
        if let frame, cancelled == 0 {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeCaptureControlConsume?(frame.id)
            #endif
            let analysisGeneration = frame.generation
            let scene = frame.analysis.scene
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeTestHooks.beforeAnalysisFrameCommit?(frame.id, frame.start, frame.end, frame.prefix, frame.stable)
                NG2RuntimeTestHooks.beforeAnalysisCommit?()
                #endif
                // Commit observation and image evidence at one cancellation
                // gate. Analysis runs outside this gate; stale results do not.
                let committed = run.lock.ng2Locked { () -> Bool in
                    guard run.generation == analysisGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }
                    #if NG2_RUNTIME_HOST_TEST
                    NG2RuntimeObserveTestHooks.beforeObserve?()
                    #endif
                    let observeStart = Self.now()
                    if run.irregular != nil {
                        ng2_controller_observe_irregular_at(core, scene, &frame.analysis.irregular,
                            frame.id, frame.start, frame.end, frame.prefix, frame.stable ? 1 : 0, observeStart)
                    } else {
                        ng2_controller_observe_at(core, scene, frame.id, frame.start, frame.end,
                            frame.prefix, frame.stable ? 1 : 0, observeStart)
                    }
                    #if NG2_RUNTIME_HOST_TEST
                    NG2RuntimeObserveTestHooks.afterObserve?()
                    #endif
                    run.captures.append(NG2CaptureSample(frame, observeStart: observeStart, observeEnd: Self.now()))
                    if run.captures.count > 256 { run.captures.removeFirst(run.captures.count - 256) }
                    run.rasterSamples.append(NG2RasterSample(id: frame.id, trace: frame.rasterTrace))
                    if run.rasterSamples.count > 32 {
                        run.rasterSamples.remove(at: 1)
                        run.rasterSamplesDropped += 1
                    }
                    if run.initial == nil && (run.irregular?.archivedInitialID ?? 0) == 0 { run.initial = frame }
                    if scene.pointee.goods == 2 && run.found == nil && (run.irregular?.archivedFoundID ?? 0) == 0 { run.found = frame }
                    run.analyzedFrames += 1
                    run.images.append(frame)
                    if run.images.count > 4 {
                        let removed = run.images.removeFirst()
                        if run.pinned[removed.id] == nil { run.evictedFrames += 1 }
                    }
                    return true
                }
                if committed {
                    var observedStatus = NG2ControllerStatus(); ng2_controller_status(core, &observedStatus)
                    cache(run, observedStatus)
                    refreshCycleEvidence(run, frame: frame)
                    refreshIrregularEvidence(run, frame: frame)
                } else {
                    // A generation-only replacement discards this old frame;
                    // it must not cancel or mutate the current generation.
                    let reason = run.lock.ng2Locked { run.cancelReason != 0 ? run.cancelReason : (self.ownerActive(run) ? Int32(0) : Int32(5)) }
                    if reason != 0 {
                        run.cancel(reason)
                        ng2_controller_cancel(core, Self.now(), reason)
                    }
                }
                run.lock.ng2Locked { run.capturePipelineIDs.remove(frame.id) }
        }
        serviceRestartYield(run)
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status)
        serviceCycleAssessment(run)
        serviceIrregularPersistence(run)
        if status.terminal != 0 {
            run.lock.ng2Locked {
                run.terminal = true
                run.successful = run.cycle == nil ? (status.goods == 1 && status.paused == 1)
                    : (status.paused == 1 && (run.cycle!.companion.outcome == 1 || run.cycle!.companion.outcome == 2))
                run.stopped = true; run.mainCommandID = 0; run.latest = nil; run.preparation = nil
            }
            cache(run, status)
            flushReport(run)
            persistCycleTerminal(run)
            let legacy = lock.ng2Locked { streamCaptures } + Int(NG2CaptureBridge.pendingRequests)
            let drained = run.lock.ng2Locked {
                NG2TicketGuard.canReleaseLease(captureWorkerDone: captureReturnedLocked(run),
                    captureOutstanding: run.captureOutstanding, mainOutstanding: run.mainOutstanding, legacyCaptures: legacy)
                    && !(run.cycle?.workerBusy ?? false) && (run.cycle == nil || run.cycle!.terminalPersisted)
                    && (run.restartYield?.captureControlTokens.isEmpty ?? true)
                    && run.campaignPersistenceTokens.isEmpty
            }
            if drained {
                ng2_controller_destroy(core); run.core = nil
                run.controlTimer?.cancel(); run.controlTimer = nil
                run.watchdog?.cancel(); run.watchdog = nil
                run.lock.ng2Locked { run.lease = false }
                notifyCycleIfNeeded(run)
                var snapshot = response(run)
                let retained = run.lock.ng2Locked {
                    Set(run.pinned.keys).union(run.images.map { $0.id })
                        .union(run.restartYield?.classificationSources.keys.map { $0 } ?? []).count
                }
                snapshot["retained_images"] = .int(retained)
                snapshot["omitted_image_count"] = .int(retained)
                snapshot["exported_images"] = .int(0)
                lock.ng2Locked {
                    rememberHistoryLocked(run.id, NG2RunHistory(owner: run.owner, response: snapshot,
                        publication: history[run.id]?.publication))
                }
                finishContinuousTerminal(run)
            }
            #if NG2_RUNTIME_HOST_TEST
            let workerState = run.lock.ng2Locked {
                (run.captureWorkerDone, run.captureOutstanding, run.mainOutstanding)
            }
            NG2RuntimeCycleTestHooks.afterTerminalDrainPass?(run.id, workerState.0, workerState.1, workerState.2)
            #endif
            return
        }
        // The live ticket and its actual queued callback have separate lives.
        // A revoked callback retains the core/lease but cannot own a later one.
        run.lock.ng2Locked {
            if run.mainCommandID != 0 && run.mainCommandID != status.current_command_id { run.mainCommandID = 0 }
        }
        if run.lock.ng2Locked({ run.mainCommandID == 0 && !run.bootstrapOutstanding }) {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeControlTick?()
            #endif
            if !waitForCycleAssessmentBeforePause(run, status: status)
                && !waitForIrregularPostCheckpointUI(run, status: status) {
                var command = NG2Command()
                let ticket = ng2_controller_tick(core, Self.now(), run.foreground ? 1 : 0,
                    LockStateMonitor.shared().isLocked ? 1 : 0, ownerActive(run) ? 1 : 0, &command)
                if ticket == 1 {
                    if run.cycle != nil && command.kind == 3 {
                        refreshCycleEvidence(run)
                    }
                    if let irregular = run.irregular, command.kind == 2, irregularOwnsInput(irregular.companion) {
                        let retained = run.lock.ng2Locked { () -> Bool in
                            guard let source = (run.images + Array(irregular.frames.values))
                                .first(where: { $0.id == command.source_capture_id }),
                                  source.generation == run.generation, source.stable,
                                  !source.startInFlight, !source.endInFlight,
                                  source.start == command.source_start_ns,
                                  source.prefix == irregular.companion.prefix,
                                  source.startPrefix == source.prefix else { return false }
                            irregular.roles["live_pause_source"] = source.id
                            irregular.frames[source.id] = source
                            irregular.observations[source.id] = source.analysis.irregular
                            return true
                        }
                        if !retained {
                            _ = ng2_controller_irregular_storage_failed(core, irregular.companion.episode_id, Self.now())
                            refreshIrregularEvidence(run); self.cycle(run); return
                        }
                    }
                    if run.irregular != nil && (command.kind == 3 || command.kind == 5) {
                        refreshIrregularEvidence(run)
                        if irregularOwnsInput(run.irregular!.companion) {
                            persistIrregularIntent(run, command: command); return
                        }
                    }
                    if let cycle = run.cycle, command.kind == 3, cycle.companion.state == 6,
                       cycle.companion.restart_command_id == command.id {
                        persistCycleIntent(run, command: command); return
                    }
                    if dispatchReserved(run, command: command, core: core) { return }
                }
            }
        }
        if now - min(now, run.lastCache) >= 50_000_000 { ng2_controller_status(core, &status); cache(run, status) }
        if run.lock.ng2Locked({ run.mainCommandID == 0 }) { flushReport(run) }
    }

    // Shared dispatch keeps the unchanged old-profile callback gates. Only the
    // cycle RESTART caller waits for its exact durable intent before entering.
    private func dispatchReserved(_ run: NG2Run, command: NG2Command, core: OpaquePointer) -> Bool {
        var status = NG2ControllerStatus()
        let generation = run.lock.ng2Locked {
            run.mainCommandID = command.id; run.mainCallbacks.insert(command.id); return run.generation
        }
        ng2_controller_status(core, &status)
        let dispatchSnapshot = cache(run, status, retainEvidence: false)
        let preparation = preparePipeline(run, command, generation: generation)
        let authority = preparation.authority
        let at = Self.now()
        let delay = command.not_before_ns > at ? Double(command.not_before_ns - at) / 1e9 : 0
        let callback = {
            self.execute(run, command, generation: generation, authority: authority, preparation: preparation)
            // This following queue item executes only after the exact
            // callback has returned; its earlier AX preparation also returned.
            self.controlQueue.async {
                run.lock.ng2Locked { run.mainCallbacks.remove(command.id) }
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeTestHooks.afterTicketReturned?(command.id)
                #endif
                self.cycle(run)
            }
        }
        #if NG2_RUNTIME_HOST_TEST
        if NG2RuntimeTestHooks.scheduleTicket?(command.id, { self.controlQueue.async(execute: callback) }) == true {
            if let dispatchSnapshot { retainEvidence(run, dispatchSnapshot) }
            return true
        }
        #endif
        // A due prepared ticket must reach main before diagnostic work
        // or another queued capture cycle spends its frozen window.
        if delay == 0 {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeDueDispatch?(command.id)
            #endif
            callback(); return true
        }
        controlQueue.asyncAfter(deadline: .now() + delay, execute: callback)
        if let dispatchSnapshot { retainEvidence(run, dispatchSnapshot) }
        return false
    }

    private func ownsTicket(_ run: NG2Run, _ command: NG2Command, generation: UInt64) -> Bool {
        run.lock.ng2Locked { run.mainCommandID == command.id && run.generation == generation }
    }
    private func preparePipeline(_ run: NG2Run, _ command: NG2Command, generation: UInt64) -> NG2PreparationLease {
        let epoch = run.core.map { ng2_controller_preparation_epoch($0, command.id, Self.now()) } ?? 0
        let reusable = run.lock.ng2Locked { () -> NG2PreparationLease? in
            guard run.mainCommandID == command.id, run.generation == generation,
                  run.cancelReason == 0, !run.stopped, !run.inFlight, self.ownerActive(run),
                  run.expectedPID > 0, !LockStateMonitor.shared().isLocked,
                  epoch != 0, let lease = run.preparation,
                  lease.matchesIdentity(key: NG2PreparationKey(run, command, generation: generation, epoch: epoch),
                      commandID: command.id, currentEpoch: epoch),
                  lease.authority.foreground,
                  NG2TicketGuard.authoritySampleIsFresh(start: lease.authority.start,
                      end: lease.authority.end, now: Self.now()) else {
                run.preparation = nil; return nil
            }
            return lease
        }
        if let reusable { return reusable }
        let queriedKey = run.lock.ng2Locked {
            NG2PreparationKey(run, command, generation: generation, epoch: epoch)
        }
        let authority = prepare(run, command, generation: generation)
        let at = Self.now()
        let currentEpoch = run.core.map { ng2_controller_preparation_epoch($0, command.id, at) } ?? 0
        return run.lock.ng2Locked {
            let lease = NG2PreparationLease(key: queriedKey, commandID: command.id, authority: authority)
            if currentEpoch != 0 && currentEpoch == epoch && run.mainCommandID == command.id
                && run.generation == generation && run.cancelReason == 0 && !run.stopped
                && !run.inFlight && self.ownerActive(run) && run.expectedPID > 0 && authority.foreground
                && queriedKey == NG2PreparationKey(run, command, generation: generation, epoch: currentEpoch)
                && NG2TicketGuard.authoritySampleIsFresh(start: authority.start, end: authority.end, now: at) {
                run.preparation = lease
            }
            return lease
        }
    }
    // Runs under the final gate while controlQueue is synchronously stopped.
    // Epoch zero certifies no sharing, while the newly queried single-ID path
    // still supports the initial step, retune, and non-MOVE commands.
    private func preparationMatches(_ lease: NG2PreparationLease, run: NG2Run,
                                    command: NG2Command, generation: UInt64, now: UInt64) -> Bool {
        let candidate = NG2PreparationKey(run, command, generation: generation, epoch: lease.key.epoch)
        let currentEpoch: UInt64
        if lease.key.epoch == 0 { currentEpoch = 0 }
        else {
            guard let core = run.core else { return false }
            currentEpoch = ng2_controller_preparation_epoch(core, command.id, now)
        }
        return lease.matchesIdentity(key: candidate, commandID: command.id, currentEpoch: currentEpoch)
    }
    private func prepare(_ run: NG2Run, _ command: NG2Command, generation: UInt64) -> AuthoritySample {
        var sample = AuthoritySample()
        guard ownsTicket(run, command, generation: generation) else { return sample }
        // The pipeline token remains held until the delayed callback returns.
        // main.sync proves the preparation really returned before that handoff.
        DispatchQueue.main.sync {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeMainAdmission?()
            #endif
            guard self.ownsTicket(run, command, generation: generation),
                  run.lock.ng2Locked({ run.cancelReason == 0 && !run.stopped }), self.ownerActive(run),
                  !LockStateMonitor.shared().isLocked else { return }
            // Foreground AX IPC must remain outside the status/cancel lock.
            let authorityQueryStart = Self.now()
            let foreground = run.expectedPID > 0 && ForegroundApp.frontmostPID() == run.expectedPID
            let authorityQueryEnd = Self.now()
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.afterForegroundQuery?()
            #endif
            sample = AuthoritySample(start: authorityQueryStart, end: authorityQueryEnd, foreground: foreground)
        }
        return sample
    }
    // Called under run.lock only for a still-live command/generation. No raw
    // AX response or arbitrary exception text enters this fixed first record.
    private func recordDispatchFailure(_ run: NG2Run, _ command: NG2Command, generation: UInt64,
                                       authority: AuthoritySample, entry: UInt64, now: UInt64, code: String) {
        guard run.mainCommandID == command.id, run.generation == generation, run.cancelReason == 0 else { return }
        guard command.kind == 4, run.dispatchFailure == nil else { return }
        run.dispatchFailure = ["command_id": number(command.id),
            "not_before_ns": number(command.not_before_ns), "deadline_ns": number(command.deadline_ns),
            "query_start_ns": authority.start == 0 ? .null : number(authority.start),
            "query_end_ns": authority.end == 0 ? .null : number(authority.end),
            "main_entry_ns": entry == 0 ? .null : number(entry), "gate_ns": number(now), "code": .string(code)]
    }

    private func execute(_ run: NG2Run, _ command: NG2Command, generation: UInt64, authority: AuthoritySample,
                         preparation: NG2PreparationLease? = nil) {
        guard let core = run.core else { return }
        guard ownsTicket(run, command, generation: generation) else { return }
        var outcome: Int32 = 0
        var postBeginNoSend = false
        DispatchQueue.main.sync {
            let mainEntry = Self.now()
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeMainAuthority?()
            #endif
            guard self.ownsTicket(run, command, generation: generation) else { return }
            let foreground = authority.foreground
            let locked = LockStateMonitor.shared().isLocked
            let permitted = run.lock.ng2Locked { () -> Bool in
                guard run.mainCommandID == command.id else { return false }
                let ownerActive = self.ownerActive(run)
                let now = Self.now()
                let authorityFresh = NG2TicketGuard.authoritySampleIsFresh(
                    start: authority.start, end: authority.end, now: now)
                // The gate rechecks cancellation/generation/owner and time
                // immediately before the C begin linearization point.
                let campaignLost: Int32 = run.campaign.map { root in
                    root.cancelReason != 0 ? root.cancelReason : (!root.permits(now) ? 15 : 0)
                } ?? 0
                let lostReason: Int32 = campaignLost != 0 ? campaignLost : (!ownerActive ? 5 : (locked ? 4 : (!foreground ? 3 : (!authorityFresh ? 7 : 0))))
                if run.generation == generation && run.cancelReason == 0 && lostReason != 0 {
                    let code = !ownerActive ? "owner" : (locked ? "locked" : (!foreground ? "foreground" : "authority_stale"))
                    recordDispatchFailure(run, command, generation: generation, authority: authority, entry: mainEntry, now: now, code: code)
                    run.cancelReason = lostReason; run.generation &+= 1
                    run.stopped = true; run.latest = nil
                    run.preparation = nil
                }
                guard NG2TicketGuard.permits(expectedGeneration: generation, currentGeneration: run.generation,
                    cancelled: run.cancelReason != 0, ownerActive: ownerActive, foreground: foreground,
                    locked: locked, now: now, notBefore: command.not_before_ns, deadline: command.deadline_ns),
                    preparation.map({ self.preparationMatches($0, run: run, command: command,
                        generation: generation, now: now) }) ?? true,
                    ng2_controller_begin(core, command.id, now, foreground ? 1 : 0, locked ? 1 : 0, ownerActive ? 1 : 0) == 1 else {
                    let code = now < command.not_before_ns ? "too_early" : (now > command.deadline_ns ? "too_late" : "controller_rejected")
                    recordDispatchFailure(run, command, generation: generation, authority: authority, entry: mainEntry, now: now, code: code)
                    return false
                }
                if command.kind == 4 || run.campaign != nil {
                    // C may spend the remaining input window on pixel proofs.
                    // Read live external guards first, then the actual clock,
                    // while this same run gate still owns the begun command.
                    let sendOwner = self.ownerActive(run)
                    let sendLocked = LockStateMonitor.shared().isLocked
                    let sendNow = Self.now()
                    let sendAuthorityFresh = NG2TicketGuard.authoritySampleIsFresh(
                        start: authority.start, end: authority.end, now: sendNow)
                    guard NG2TicketGuard.permits(expectedGeneration: generation, currentGeneration: run.generation,
                        cancelled: run.cancelReason != 0, ownerActive: sendOwner, foreground: foreground,
                        locked: sendLocked, now: sendNow, notBefore: command.not_before_ns, deadline: command.deadline_ns),
                        sendAuthorityFresh, run.campaign?.permits(sendNow) ?? true else {
                        let campaignLost: Int32 = run.campaign.map { root in
                            root.cancelReason != 0 ? root.cancelReason : (!root.permits(sendNow) ? 15 : 0)
                        } ?? 0
                        let lost: Int32 = campaignLost != 0 ? campaignLost : (!sendOwner ? 5 : (sendLocked ? 4 : (!sendAuthorityFresh ? 7 : 0)))
                        let code = !sendOwner ? "owner" : (sendLocked ? "locked" : (!sendAuthorityFresh ? "authority_stale" :
                            (sendNow < command.not_before_ns ? "too_early" : (sendNow > command.deadline_ns ? "too_late" : "controller_rejected"))))
                        recordDispatchFailure(run, command, generation: generation, authority: authority,
                            entry: mainEntry, now: sendNow, code: code)
                        // No physical synth began. Settle state2 as certainly
                        // not sent BEFORE releasing the gate to cancellation.
                        ng2_controller_complete(core, command.id, sendNow, 0)
                        postBeginNoSend = true
                        if run.generation == generation && run.cancelReason == 0 && lost != 0 {
                            run.cancelReason = lost; run.generation &+= 1
                            run.stopped = true; run.latest = nil; run.preparation = nil
                        }
                        return false
                    }
                    // begin consumed its C preparation epoch; its earlier
                    // identity check remains owned by this same locked gate.
                }
                run.inFlight = true
                if command.kind == 3 { run.irregular?.scanRestart = false }
                return true
            }
            guard permitted else { return }
            // begin() is the cancellation linearization point. After it, this
            // one synth is started/unknown until the synchronous call returns.
            outcome = -1
            var result: ([String: JSONValue]?, JSONRPCError?) = (nil, .internalError)
            let raised = ObjCException.catching {
                if command.kind == 4 {
                    let point = CGPoint(x: Int(command.x), y: Int(command.y))
                    result = run.fast?.fastGesture([[(point: point, t: 0.0), (point: point, t: 0.05)]]) ?? (nil, .internalError)
                } else { result = run.fast?.fastTap(x: Double(command.x), y: Double(command.y)) ?? (nil, .internalError) }
            }
            if raised == nil && result.1 == nil { outcome = 1 }
            run.lock.ng2Locked {
                if run.mainCommandID == command.id && outcome == 1 {
                    if command.kind == 3 { self.armRestartYieldLocked(run, command: command, generation: generation) }
                    run.prefix = command.id; run.inFlight = false
                }
                // A started failure remains inflight: never certify a later
                // frame prefix or issue an automatic cleanup tap from it.
            }
        }
        guard run.lock.ng2Locked({ run.mainCommandID == command.id && (run.generation == generation || run.cancelReason != 0) }) else { return }
        let cancelled = run.lock.ng2Locked { run.cancelReason }
        if outcome == 0 && cancelled != 0 { ng2_controller_cancel(core, Self.now(), cancelled) }
        if !postBeginNoSend { ng2_controller_complete(core, command.id, Self.now(), outcome) }
        run.lock.ng2Locked {
            if command.kind == 2 { run.restartYield?.capturePaused = false }
            if run.mainCommandID == command.id { run.mainCommandID = 0; run.preparation = nil }
        }
        if run.lock.ng2Locked({ run.restartYield?.failed ?? false }) { run.cancel(17) }
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status); cache(run, status)
        flushReport(run)
        cycle(run)
    }

    @discardableResult
    private func cache(_ run: NG2Run, _ s: NG2ControllerStatus,
                       retainEvidence: Bool = true) -> NG2ControllerSnapshot? {
        guard let core = run.core else { return nil }
        if s.input_state == 4 {
            lock.ng2Locked { poisoned = true }
            run.lock.ng2Locked { run.uiFrozen = true }
        }
        var events = [NG2ControllerEvent](repeating: NG2ControllerEvent(), count: 64)
        var count = events.withUnsafeMutableBufferPointer { ng2_controller_events(core, $0.baseAddress, $0.count) }
        var changes = [NG2ControllerSceneChange](repeating: NG2ControllerSceneChange(), count: 3)
        var changeCount = changes.withUnsafeMutableBufferPointer { ng2_controller_scene_changes(core, $0.baseAddress, $0.count) }
        var details = [NG2ControllerSceneDetail](repeating: NG2ControllerSceneDetail(), count: 3)
        let detailCount = details.withUnsafeMutableBufferPointer { ng2_controller_scene_details(core, $0.baseAddress, $0.count) }
        var motionWait = NG2ControllerMotionWait()
        ng2_controller_motion_wait(core, &motionWait)
        var motionReferences = [NG2ControllerMotionReference](repeating: NG2ControllerMotionReference(), count: 16)
        let motionReferenceCount = motionReferences.withUnsafeMutableBufferPointer {
            ng2_controller_motion_references(core, $0.baseAddress, $0.count)
        }
        var recovery = NG2ControllerRecoveryStatus()
        ng2_controller_recovery_status(core, &recovery)
        let retainedRecoveryCount = Int(min(recovery.record_count, 2))
        let traces = [recovery.records.0, recovery.records.1]
        let recoveryRecords: [NG2RecoveryRecord] = (0..<retainedRecoveryCount).map { index in
            var samples = [NG2BeatSample](repeating: NG2BeatSample(), count: 13)
            let count = samples.withUnsafeMutableBufferPointer {
                ng2_controller_recovery_samples(core, index, $0.baseAddress, $0.count)
            }
            return NG2RecoveryRecord(trace: traces[index], samples: Array(samples.prefix(min(count, samples.count))))
        }
        var stopDetail = NG2ControllerStopDetail(), handoff = NG2ControllerHandoff()
        if run.campaign != nil {
            var value = NG2ControllerContinuousStatus(); ng2_controller_continuous_status(core, &value)
            run.lock.ng2Locked { run.campaignContinuation = value }
        }
        ng2_controller_stop_detail(core, &stopDetail)
        ng2_controller_handoff(core, &handoff)
        // TEST056 HOST SNAPSHOT BEGIN.
        #if NG2_RUNTIME_HOST_TEST
        if let fixture = NG2RuntimeEvidenceTestHooks.snapshot {
            events = fixture.events; count = events.count
            changes = fixture.changes; changeCount = changes.count
        }
        #endif
        // TEST056 HOST SNAPSHOT END.
        let snapshot = NG2ControllerSnapshot(status: s,
            events: Array(events.prefix(min(count, events.count))),
            changes: Array(changes.prefix(min(changeCount, changes.count))),
            details: Array(details.prefix(min(detailCount, details.count))), motionWait: motionWait,
            motionReferences: Array(motionReferences.prefix(min(motionReferenceCount, motionReferences.count))),
            recovery: recovery, recoveryRecords: recoveryRecords, stopDetail: stopDetail, handoff: handoff)
        if retainEvidence {
            #if NG2_RUNTIME_HOST_TEST
            NG2RuntimeTestHooks.beforeEvidenceRetention?(s.current_command_id)
            #endif
        }
        run.lock.ng2Locked {
            retainInitialRejectionLocked(run, snapshot)
            retainRestartDecisionLocked(run, snapshot)
            // A dispatch snapshot still publishes the full coherent C state.
            // Reserve its raw authority before deferring diagnostic pin work.
            if !retainEvidence, let source = snapshot.events.last(where: {
                $0.command.id == s.current_command_id
            })?.command.source_capture_id {
                pinDispatchSourceLocked(run, source)
            }
            run.controllerSnapshot = snapshot
            if retainEvidence { retainEvidenceLocked(run, snapshot) }
        }
        run.lastCache = Self.now()
        return snapshot
    }

    // Cache only a coherent certainly-unsent transition while both original
    // rasters are still available. This is diagnostic retention, never input
    // authority, movement credit, recovery permission or a synthesized frame.
    private func retainInitialRejectionLocked(_ run: NG2Run, _ snapshot: NG2ControllerSnapshot) {
        let status = snapshot.status
        guard (run.profile == Self.evidenceProfile || Self.isCycleProfile(run.profile)), run.cancelReason == 0, !run.stopped,
              !run.terminal, !run.inFlight, ownerActive(run),
              let previous = run.controllerSnapshot else { return }
        let old = previous.status
        guard old.input_state == 1, old.current_command_id != 0, old.reason == 0,
              old.terminal == 0, old.goods == 0, old.lead_confirmed == 0, old.x == 0, old.y == 0,
              status.input_state == 0, status.current_command_id == 0,
              status.reason == 0 || status.reason == 17,
              status.terminal == 0, status.goods == 0, status.lead_confirmed == 0,
              status.x == 0, status.y == 0, status.inputs == old.inputs, status.moves == old.moves,
              run.prefix == old.last_completed_id, status.last_completed_id == old.last_completed_id,
              let pending = previous.events.last(where: { $0.command.id == old.current_command_id }),
              pending.command.kind == 4, pending.begin_ns == 0, pending.outcome == 0,
              let rejected = snapshot.events.last(where: { $0.command.id == old.current_command_id }),
              rejected.begin_ns == 0, rejected.outcome == 3, rejected.reason == 17,
              rejected.end_ns == status.last_capture_end_ns else { return }
        let a = pending.command, b = rejected.command
        guard a.id == b.id, a.ordinal == b.ordinal, a.target_ns == b.target_ns,
              a.not_before_ns == b.not_before_ns, a.deadline_ns == b.deadline_ns,
              a.source_capture_id == b.source_capture_id, a.source_start_ns == b.source_start_ns,
              a.phase_sample_ns == b.phase_sample_ns, a.kind == b.kind,
              a.direction == b.direction, a.x == b.x, a.y == b.y,
              a.source_capture_id != 0, status.last_capture_id > a.source_capture_id,
              status.last_capture_id > old.last_capture_id else { return }
        let available = run.images + Array(run.pinned.values) + [run.initial, run.found].compactMap({ $0 })
        guard let source = available.first(where: { $0.id == a.source_capture_id }),
              let frame = available.first(where: { $0.id == status.last_capture_id }),
              source.generation == run.generation, frame.generation == run.generation,
              source.stable, frame.stable,
              !source.startInFlight, !source.endInFlight, !frame.startInFlight, !frame.endInFlight,
              source.startPrefix == run.prefix, source.prefix == run.prefix,
              frame.startPrefix == run.prefix, frame.prefix == run.prefix,
              source.start == a.source_start_ns, frame.start >= source.start,
              frame.start == status.last_capture_start_ns, frame.end == status.last_capture_end_ns,
              source.analysis.scene.pointee.state == 2,
              source.analysis.scene.pointee.gold_state == 1,
              source.analysis.scene.pointee.goods == 0 else { return }
        run.initialRejectedCaptureID = frame.id
        run.references.insert(frame.id)
        if Self.isCycleProfile(run.profile) {
            run.initialRejectedSourceCaptureID = source.id
            run.references.insert(source.id)
        }
        // Reserve the one existing slot even when the rest of pin work is
        // deferred until after dispatch. The previous snapshot is not reused.
        pinDispatchSourceLocked(run, frame.id)
        if Self.isCycleProfile(run.profile) { pinDispatchSourceLocked(run, source.id) }
    }

    // Call under run.lock, before a dispatch snapshot can defer pin work.
    // A replacement within one level cannot add an unbounded evidence slot.
    private func retainRestartDecisionLocked(_ run: NG2Run, _ snapshot: NG2ControllerSnapshot) {
        let status = snapshot.status
        guard (run.profile == Self.evidenceProfile || Self.isCycleProfile(run.profile)), run.cancelReason == 0, !run.stopped,
              !run.terminal, !run.inFlight, ownerActive(run),
              status.restarts >= 0, status.restarts < 12, status.input_state == 1,
              status.reason == 0, status.goods == 0, status.terminal == 0,
              status.current_command_id != 0, run.prefix == status.last_completed_id,
              let event = snapshot.events.last(where: { $0.command.id == status.current_command_id }),
              event.command.kind == 2, event.begin_ns == 0, event.outcome == 0,
              event.command.source_capture_id != 0 else { return }
        let source = event.command.source_capture_id
        guard let frame = run.pinned[source] ?? (run.images + [run.initial, run.found].compactMap({ $0 }))
                .first(where: { $0.id == source }),
              frame.generation == run.generation, frame.stable,
              !frame.startInFlight, !frame.endInFlight,
              frame.startPrefix == run.prefix, frame.prefix == run.prefix else { return }
        let scene = frame.analysis.scene
        guard scene.pointee.state == 2, scene.pointee.gold_state == 1, scene.pointee.goods == 0 else { return }
        run.restartDecisionCaptureIDs[status.restarts] = source
        run.initial = frame
        run.references.insert(source)
    }

    // Call under run.lock. The source is already in recent/pinned immutable
    // frames; this reserves its existing slot before AX preparation can wait.
    private func pinVictimLocked(_ run: NG2Run, incoming: UInt64, protected: Set<UInt64>) -> UInt64? {
        if let ordinary = run.pinned.keys.sorted().first(where: { !protected.contains($0) }) { return ordinary }
        guard Self.isCycleProfile(run.profile), let optional = run.initialRejectedSourceCaptureID,
              optional != incoming, run.pinned[optional] != nil,
              !priorityCaptureIDs(run, includingInitialSource: false).contains(optional) else { return nil }
        return optional
    }

    private func pinDispatchSourceLocked(_ run: NG2Run, _ source: UInt64) {
        guard source != 0 else { return }
        run.references.insert(source)
        guard run.pinned[source] == nil,
              let frame = (run.images + [run.initial, run.found].compactMap({ $0 }))
                .first(where: { $0.id == source }) else { return }
        let protected = Set(priorityCaptureIDs(run) + [source])
        let limit = evidencePinLimit(run)
        if run.pinned.count == limit, let evicted = pinVictimLocked(run, incoming: source, protected: protected) {
            run.pinned.removeValue(forKey: evicted); run.evictedFrames += 1
        }
        if run.pinned.count < limit { run.pinned[source] = frame }
    }

    private func retainEvidence(_ run: NG2Run, _ snapshot: NG2ControllerSnapshot) {
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeTestHooks.beforeEvidenceRetention?(snapshot.status.current_command_id)
        #endif
        run.lock.ng2Locked {
            // execute() may already have published the ACK/newest state.
            // Its retention is authoritative; an older snapshot cannot reset it.
            guard run.controllerSnapshot === snapshot else { return }
            retainEvidenceLocked(run, snapshot)
        }
    }

    // Call under run.lock. Every value comes from the same immutable C snapshot.
    private func retainEvidenceLocked(_ run: NG2Run, _ snapshot: NG2ControllerSnapshot) {
            let s = snapshot.status, events = snapshot.events, changes = snapshot.changes
            if let irregular = run.irregular, irregularOwnsInput(irregular.companion) {
                run.terminalCaptureID = s.terminal != 0 && s.last_capture_id != 0 ? s.last_capture_id : nil
                return // Exact episode roles retain pixels; historical pins cannot steal future credits.
            }
            let motionReferences = snapshot.motionReferences
            var required = Set<UInt64>()
            var diagnosticIDs: [UInt64] = []
            // C retains first1/latest2 in chronological order. Only the latest
            // two comparisons precede cumulative evidence, newest first.
            for change in changes.suffix(2).reversed() {
                for id in [change.source_capture_id, change.observed_capture_id] where id != 0 {
                    if !diagnosticIDs.contains(id) { diagnosticIDs.append(id) }
                }
            }
            if let source = events.last(where: { $0.command.kind == 4 })?.command.source_capture_id,
               source != 0 && !diagnosticIDs.contains(source) { diagnosticIDs.append(source) }
            run.diagnosticCaptureIDs = diagnosticIDs
            if Self.isCycleProfile(run.profile) {
                let stop = snapshot.stopDetail, handoff = snapshot.handoff
                var cycleIDs: [UInt64] = []
                for id in [stop.source_capture_id, stop.observed_capture_id, stop.anchor_capture_id,
                           stop.last_comparison_capture_id, handoff.source_capture_id, handoff.pause_capture_id]
                    where id != 0 && !cycleIDs.contains(id) { cycleIDs.append(id) }
                run.cycleDiagnosticCaptureIDs = cycleIDs
                required.formUnion(cycleIDs)
            }
            run.terminalCaptureID = s.terminal != 0 && s.last_capture_id != 0 ? s.last_capture_id : nil
            for event in events {
                if event.command.source_capture_id != 0 { required.insert(event.command.source_capture_id) }
                if event.observed_capture_id != 0 { required.insert(event.observed_capture_id) }
            }
            for change in changes {
                required.insert(change.source_capture_id); required.insert(change.observed_capture_id)
            }
            for reference in motionReferences {
                for id in [reference.authority_capture_id, reference.reference_capture_id,
                           reference.observed_capture_id, reference.selected_capture_id] where id != 0 {
                    required.insert(id)
                }
            }
            for frame in [run.initial, run.found].compactMap({ $0 }) { required.insert(frame.id) }
            if s.terminal != 0 && s.last_capture_id != 0 { required.insert(s.last_capture_id) }
            run.references.formUnion(required)
            var available = run.pinned
            for frame in run.images + [run.initial, run.found].compactMap({ $0 }) { available[frame.id] = frame }
            let priority = priorityCaptureIDs(run)
            let protected = Set(priority)
            let limit = evidencePinLimit(run)
            for id in priority where run.pinned[id] == nil {
                guard let frame = available[id] else { continue }
                if run.pinned.count == limit, let evicted = pinVictimLocked(run, incoming: id, protected: protected) {
                    run.pinned.removeValue(forKey: evicted); run.evictedFrames += 1
                }
                if run.pinned.count < limit { run.pinned[id] = frame }
            }
            for id in required.sorted() where run.pinned[id] == nil {
                if run.pinned.count < limit, let frame = available[id] { run.pinned[id] = frame }
            }
    }

    private func controllerReport(_ run: NG2Run, projection: NG2ResponseProjection, origin: String = "response") -> [String: JSONValue] {
        guard let snapshot = projection.snapshot else { return projection.cachedReport }
        if snapshot === projection.reportSnapshot && projection.generation == projection.reportGeneration {
            return projection.cachedReport
        }
        let report = encodeSnapshot(snapshot, origin: origin)
        // A slow status encoder cannot replace a later C snapshot or a new
        // generation's report. Its own coherent response may still be returned.
        run.lock.ng2Locked {
            if run.controllerSnapshot === snapshot && run.generation == projection.generation {
                run.report = report; run.reportSnapshot = snapshot; run.reportGeneration = projection.generation
            }
        }
        return report
    }

    private func flushReport(_ run: NG2Run) {
        let projection = run.lock.ng2Locked { NG2ResponseProjection(run) }
        _ = controllerReport(run, projection: projection, origin: "flush")
    }

    // Only durable cycle records receive the separate readonly proof schemas.
    // HTTP/controller reports retain their existing closed shape. No live C
    // getter is queried by an asynchronous writer or response encoder.
    private func encodeCycleSnapshot(_ snapshot: NG2ControllerSnapshot, origin: String) -> [String: JSONValue] {
        var result = encodeSnapshot(snapshot, origin: origin)
        let stop = snapshot.stopDetail, handoff = snapshot.handoff
        let stages = ["none", "generic", "passage_wait", "cycle_observe", "cycle_credit"]
        let kinds = ["none", "negative_limit", "clear_search_limit", "restarted_budget"]
        let stage = Int(stop.stage), kind = Int(handoff.kind)
        result["stop_detail"] = .object(["schema": .string("ngg2-stop-detail-v1"), "valid": .bool(stop.valid == 1),
            "stage": .string(stages.indices.contains(stage) ? stages[stage] : "none"), "reason": integer(stop.reason),
            "at_ns": number(stop.at_ns), "source_capture_id": number(stop.source_capture_id),
            "observed_capture_id": number(stop.observed_capture_id), "anchor_capture_id": number(stop.anchor_capture_id),
            "prefix": number(stop.prefix), "deadline_ns": number(stop.deadline_ns), "wait_kind": integer(stop.wait_kind),
            "passage_bit": integer(stop.passage_bit), "passage_pending": number(UInt64(stop.passage_pending)),
            "passage_unresolved": number(UInt64(stop.passage_unresolved)),
            "passage_unlocalized_gold": .bool(stop.passage_unlocalized_gold == 1), "x": integer(stop.x), "y": integer(stop.y),
            "validation": integer(stop.validation), "motion_kind": integer(stop.motion_kind),
            "motion_dx": integer(stop.motion_dx), "motion_dy": integer(stop.motion_dy),
            "last_comparison_capture_id": number(stop.last_comparison_capture_id)])
        result["handoff"] = .object(["schema": .string("ngg2-trial-handoff-v1"),
            "kind": .string(kinds.indices.contains(kind) ? kinds[kind] : "none"), "allowed": .bool(handoff.allowed == 1),
            "reason": integer(handoff.reason), "qualified_ns": number(handoff.qualified_ns),
            "source_capture_id": number(handoff.source_capture_id), "source_prefix": number(handoff.source_prefix),
            "pause_capture_id": number(handoff.pause_capture_id), "completed_prefix": number(handoff.completed_prefix)])
        return result
    }

    private func encodeSnapshot(_ snapshot: NG2ControllerSnapshot, origin: String) -> [String: JSONValue] {
        #if NG2_RUNTIME_HOST_TEST
        NG2RuntimeTestHooks.beforeReportEncode?(origin, snapshot.status.last_capture_id)
        #endif
        let s = snapshot.status
        let events = snapshot.events, changes = snapshot.changes, details = snapshot.details
        let motionWait = snapshot.motionWait, motionReferences = snapshot.motionReferences
        let count = events.count, changeCount = changes.count, detailCount = details.count
        let motionReferenceCount = motionReferences.count
        let encoded = events.prefix(min(count, events.count)).map { event -> JSONValue in
            let c = event.command
            return .object(["id": number(c.id), "ordinal": number(c.ordinal), "kind": integer(c.kind),
                "direction": integer(c.direction), "x": integer(c.x), "y": integer(c.y),
                "target_ns": number(c.target_ns), "not_before_ns": number(c.not_before_ns), "deadline_ns": number(c.deadline_ns),
                "source_capture_id": number(c.source_capture_id), "source_start_ns": number(c.source_start_ns),
                "phase_sample_ns": number(c.phase_sample_ns), "begin_ns": number(event.begin_ns),
                "end_ns": number(event.end_ns), "observed_capture_id": number(event.observed_capture_id),
                "outcome": integer(event.outcome), "reason": integer(event.reason), "motion": integer(event.motion),
                "dx": integer(event.dx), "dy": integer(event.dy)])
        }
        let encodedChanges = changes.prefix(min(changeCount, changes.count)).map { c -> JSONValue in
            .object(["command_id": number(c.command_id), "source_capture_id": number(c.source_capture_id),
                "observed_capture_id": number(c.observed_capture_id), "target_ns": number(c.target_ns),
                "deadline_ns": number(c.deadline_ns), "change_mask": integer(c.change_mask),
                "changed_tiles": integer(c.changed_tiles), "changed_protected": integer(c.changed_protected),
                "state_before": integer(c.state_before), "state_after": integer(c.state_after),
                "goods_before": integer(c.goods_before), "goods_after": integer(c.goods_after),
                "replan_count": integer(c.replan_count), "replan_allowed": .bool(c.replan_allowed == 1)])
        }
        let encodedDetails = details.prefix(min(detailCount, details.count)).map { item -> JSONValue in
            var detail = item
            let cellCount = min(4, max(0, Int(detail.cell_count)))
            let cells: [JSONValue] = withUnsafePointer(to: &detail.cells) { pointer in
                pointer.withMemoryRebound(to: NG2ControllerCellChange.self, capacity: 4) { rows in
                    (0..<cellCount).map { index in
                        let cell = rows[index]
                        return .object(["x": integer(cell.x), "y": integer(cell.y),
                            "tile_before": integer(cell.tile_before), "tile_after": integer(cell.tile_after),
                            "protected_before": integer(cell.protected_before), "protected_after": integer(cell.protected_after)])
                    }
                }
            }
            return .object(["command_id": number(detail.command_id), "source_capture_id": number(detail.source_capture_id),
                "observed_capture_id": number(detail.observed_capture_id), "validation": integer(detail.validation),
                "continuous_count": integer(detail.continuous_count), "chain_count": integer(detail.chain_count),
                "cell_count": integer(detail.cell_count), "omitted_cells": integer(detail.omitted_cells), "cells": .array(cells)])
        }
        let encodedMotionReferences = motionReferences.prefix(min(motionReferenceCount, motionReferences.count)).map { reference -> JSONValue in
            .object(["command_id": number(reference.command_id), "authority_capture_id": number(reference.authority_capture_id),
                "reference_capture_id": number(reference.reference_capture_id), "reference_start_ns": number(reference.reference_start_ns),
                "reference_prefix": number(reference.reference_prefix), "observed_capture_id": number(reference.observed_capture_id),
                "reference_eligible": .bool(reference.reference_eligible == 1), "primary_motion": integer(reference.primary_motion),
                "fallback_attempted": .bool(reference.fallback_attempted == 1), "fallback_motion": integer(reference.fallback_motion),
                "selected_capture_id": number(reference.selected_capture_id), "selected_motion": integer(reference.selected_motion)])
        }
        let report: [String: JSONValue] = ["abi_version": .int(Int(s.abi_version)), "struct_size": .int(Int(s.struct_size)),
            "phase": integer(s.phase), "reason": integer(s.reason), "reason_name": .string(String(cString: ng2_reason_name(s.reason))),
            "terminal": integer(s.terminal), "goods": integer(s.goods), "paused": integer(s.paused), "input_state": integer(s.input_state),
            "inputs": integer(s.inputs), "moves": integer(s.moves), "door_changes": integer(s.door_changes),
            "terrain_changes": integer(s.terrain_changes), "restarts": integer(s.restarts), "x": integer(s.x), "y": integer(s.y),
            "lead_confirmed": integer(s.lead_confirmed), "started_ns": number(s.started_ns), "walk_started_ns": number(s.walk_started_ns),
            "ended_ns": number(s.ended_ns), "first_move_ns": number(s.first_move_ns), "last_capture_id": number(s.last_capture_id),
            "last_capture_start_ns": number(s.last_capture_start_ns), "last_capture_end_ns": number(s.last_capture_end_ns),
            "last_completed_id": number(s.last_completed_id), "current_command_id": number(s.current_command_id),
            "last_ordinal": number(s.last_ordinal), "next_target_ns": number(s.next_target_ns), "lead_ns": number(s.lead_ns),
            "capture_count": number(s.capture_count), "accepted_frames": number(s.accepted_frames),
            "discarded_frames": number(s.discarded_frames), "beat_period_ns": number(s.beat_period_ns),
            "events": .array(encoded), "scene_changes": .array(encodedChanges), "scene_change_details": .array(encodedDetails),
            "motion_references": .array(encodedMotionReferences),
            "recovery": encodeRecovery(snapshot.recovery, records: snapshot.recoveryRecords),
            "motion_wait": .object(["command_id": number(motionWait.command_id),
                "source_capture_id": number(motionWait.source_capture_id), "last_capture_id": number(motionWait.last_capture_id),
                "deadline_ns": number(motionWait.deadline_ns), "attempts": integer(motionWait.attempts),
                "last_motion": integer(motionWait.last_motion), "active": .bool(motionWait.active == 1)])]
        return report
    }

    private func encodeRecovery(_ recovery: NG2ControllerRecoveryStatus, records: [NG2RecoveryRecord]) -> JSONValue {
        let encodedRecords = records.map { record -> JSONValue in
            let r = record.trace, model = r.model
            let samples = record.samples.map { sample -> JSONValue in
                .object(["start_ns": number(sample.start_ns), "end_ns": number(sample.end_ns),
                    "midpoint_ns": number(sample.midpoint_ns), "half_width_ns": .double(sample.half_width_ns),
                    "spacing": .double(sample.spacing), "center": .double(sample.center), "q": .double(sample.q)])
            }
            return .object(["sequence": number(r.sequence), "episode_id": number(r.episode_id),
                "reason": integer(r.reason), "clock": integer(r.clock), "at_ns": number(r.at_ns),
                "capture_id": number(r.capture_id), "command_id": number(r.command_id),
                "abandoned_target_ns": number(r.abandoned_target_ns), "sync_deadline_ns": number(r.sync_deadline_ns),
                "model": .object(["period_ns": number(model.period_ns), "epoch_ns": number(model.epoch_ns),
                    "first_ns": number(model.first_ns), "last_ns": number(model.last_ns),
                    "gap_ns": number(model.gap_ns), "prediction_span_ns": number(model.prediction_span_ns),
                    "sample_count": integer(model.sample_count), "mode": integer(model.mode),
                    "candidate_count": integer(model.candidate_count), "residual": .double(model.residual),
                    "maximum": .double(model.maximum), "alternate": .double(model.alternate),
                    "alias_gap": .double(model.alias_gap), "half_width_max_ns": .double(model.half_width_max_ns),
                    "tracking_error": .double(model.tracking_error), "extrapolation_budget": .double(model.extrapolation_budget)]),
                "samples": .array(samples)])
        }
        return .object(["initial_reacquisitions": number(recovery.initial_reacquisitions),
            "post_move_reacquisitions": number(recovery.post_move_reacquisitions),
            "episode_id": number(recovery.episode_id), "mode": integer(recovery.mode),
            "schedule_deadline_ns": number(recovery.schedule_deadline_ns),
            "visual_deadline_ns": number(recovery.visual_deadline_ns), "ack_ns": number(recovery.ack_ns),
            "record_count": number(recovery.record_count), "dropped_records": number(recovery.dropped_records),
            "records": .array(encodedRecords)])
    }
}
