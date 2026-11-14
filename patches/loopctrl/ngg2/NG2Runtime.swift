import Foundation
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
    static var beforeAnalysisFrameCommit: ((UInt64, UInt64, UInt64, UInt64, Bool) -> Void)?
    static var afterForegroundQuery: (() -> Void)?
    static var beforeControlTick: (() -> Void)?
    static var scheduleTicket: ((UInt64, @escaping () -> Void) -> Bool)?
    static var afterTicketReturned: ((UInt64) -> Void)?
    static var afterCaptureDrainProcessed: ((String) -> Void)?
    static var beforeCaptureFailureCommit: ((String) -> Void)?
    static var analysisRGBA: ((Data) -> Data)?
    static var afterWatchdogCheck: ((String, UInt64) -> Void)?
    static var beforeReportEncode: ((String, UInt64) -> Void)?
    static var beforeDueDispatch: ((UInt64) -> Void)?
    static var beforeEvidenceRetention: ((UInt64) -> Void)?
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

// This state is owned by the run gate. Expensive classification and durable
// storage use separate single workers; neither worker has input authority.
private final class NG2CycleRun {
    var companion = NG2ControllerCycleStatus()
    var spool: NG2CycleSpool?
    var classificationOutstanding = false
    var persistenceOutstanding = false
    var checkpointJob: UInt64 = 0
    var intentCommand: UInt64 = 0
    var outcomeJob: UInt64 = 0
    var terminalPersistenceStarted = false
    var terminalPersisted = false
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
    var workerBusy: Bool { classificationOutstanding || persistenceOutstanding }
    init() {
        companion.abi_version = 1; companion.struct_size = UInt32(MemoryLayout<NG2ControllerCycleStatus>.size)
        companion.level_id = 1
    }
}

private final class NG2CycleJob {
    let run: NG2Run
    let frame: NG2Frame
    let generation, level, job, prefix, deadline: UInt64
    init(_ run: NG2Run, frame: NG2Frame, state: NG2ControllerCycleStatus) {
        self.run = run; self.frame = frame; generation = frame.generation
        level = state.level_id; job = state.job_id; prefix = state.prefix; deadline = state.deadline_ns
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
    static var beforeClassificationCommit: ((UInt64) -> Void)?
    static var beforeCheckpointWrite: ((UInt64) -> Void)?
    static var beforeIntentWrite: ((UInt64) -> Void)?
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
    let clock: String
    var generation: UInt64 = 1
    var cancelReason: Int32 = 0
    var heartbeat: UInt64
    let acceptedStarted: UInt64
    var lease = true
    var captureOutstanding = false
    var captureWorkerDone = false
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
    init(owner: String, id: String, now: UInt64, profile: String = "normal-1-1-v1", clock: String? = nil) {
        self.owner = owner; self.id = id; self.profile = profile
        self.clock = clock ?? UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        cycle = profile == NG2Runtime.cycleProfile ? NG2CycleRun() : nil
        maximumExportBytes = profile == NG2Runtime.evidenceProfile ? 10 * 1024 * 1024 : 4 * 1024 * 1024
        heartbeat = now; acceptedStarted = now
    }
    func cancel(_ reason: Int32) {
        lock.ng2Locked {
            if cancelReason == 0 { cancelReason = reason; generation &+= 1 }
            stopped = true
            latest = nil
            exportCache = nil
            preparation = nil
        }
    }
}

// Copy C and Runtime projections at one short gate. Encoding never queries C
// or synchronously re-enters controlQueue, including from a main-thread hook.
private struct NG2ResponseProjection {
    let snapshot, reportSnapshot: NG2ControllerSnapshot?
    let cachedReport: [String: JSONValue]
    let generation, reportGeneration: UInt64
    let id, clock, state, profile: String
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
        retained = Set(run.pinned.keys).union(run.images.map { $0.id }); references = run.references
        pinnedCount = run.pinned.count; recentCount = run.images.count
    }
}

/// One bounded native run. Controller C state is used only on controlQueue, except begin()
/// on main while controlQueue synchronously waits for that exact call.
/// Status/cancel RPCs read immutable cached dictionaries and never touch C.
final class NG2Runtime {
    static let shared = NG2Runtime()
    static let methods: Set<String> = ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results", "necro_native_cycle"]
    static let ownerParam = "_necro_owner"
    static let profile = "normal-1-1-v1"
    static let evidenceProfile = "normal-1-1-evidence-v2"
    static let cycleProfile = "normal-1-1-cycle-v1"
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
    private var seen = Set<String>()
    // Metadata for at most 64 drained runs. Only the current run retains raw
    // rasters (legacy20/cycle24 pins plus recent/capture/analysis handoff).
    private var history: [String: (owner: String, response: [String: JSONValue])] = [:]
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

    var hasLease: Bool { lock.ng2Locked { poisoned || (current?.lock.ng2Locked { current?.lease ?? false } ?? false) } }

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
        lock.ng2Locked {
            if poisoned || current?.lock.ng2Locked({ current?.lease ?? false }) == true { return false }
            streamCaptures += 1
            return true
        }
    }
    func endStreamCapture() { lock.ng2Locked { streamCaptures -= 1 } }
    private var streamsDrained: Bool { lock.ng2Locked { streamCaptures == 0 } && NG2CaptureBridge.pendingRequests == 0 }
    func ownerChanged() {
        if RemoteSession.shared.paused { lock.ng2Locked { current }?.cancel(5) }
    }

    func handle(method: String, params: [String: JSONValue]?) -> ([String: JSONValue]?, JSONRPCError?) {
        guard Self.methods.contains(method), let owner = params?[Self.ownerParam]?.stringValue,
              !owner.isEmpty, let id = params?["run_id"]?.stringValue,
              lowerHexIdentity(id) else {
            return failure("Invalid native request identity.", -32602)
        }
        if method == "necro_native_cycle" { return handleCycle(owner: owner, id: id, params: params ?? [:]) }
        var exportMode: String?
        if method == "necro_native_results", let value = params?["mode"] {
            guard let mode = value.stringValue, mode == "manifest" || mode == "chunk" else {
                return failure("Unsupported native results mode.", -32602)
            }
            exportMode = mode
        }
        let allowed: Set<String> = method == "necro_native_start" ? ["run_id", "profile", Self.ownerParam]
            : (method == "necro_native_status" ? ["run_id", "keepalive", Self.ownerParam]
               : (exportMode == "chunk" ? ["run_id", "mode", "export_id", "capture_id", "offset", Self.ownerParam]
                  : (exportMode == "manifest" ? ["run_id", "mode", Self.ownerParam] : ["run_id", Self.ownerParam])))
        guard Set((params ?? [:]).keys).isSubset(of: allowed) else { return failure("Unknown native request parameter.", -32602) }
        if method == "necro_native_start" {
            guard let profile = params?["profile"]?.stringValue,
                  profile == Self.profile || profile == Self.evidenceProfile || profile == Self.cycleProfile else {
                return failure("Unsupported native profile.", -32602)
            }
            guard !RemoteSession.shared.paused else { return failure("Owner paused native control.") }
            var created: NG2Run?
            let answer: ([String: JSONValue]?, JSONRPCError?) = lock.ng2Locked {
                if let old = current, old.owner == owner, old.id == id {
                    guard old.profile == profile else { return failure("Native run profile is immutable.", -32602) }
                    return (response(old), nil)
                }
                if let archived = history[id], archived.owner == owner {
                    guard archived.response["profile"]?.stringValue == profile else {
                        return failure("Native run profile is immutable.", -32602)
                    }
                    return (historical(archived.response), nil)
                }
                guard cycleScanState == "ready", unpublishedCycles.isEmpty else {
                    return profile == Self.cycleProfile ? cycleNotStarted("Native cycle evidence must be recovered and publication acknowledged before a new start.")
                        : failure("Native cycle evidence must be recovered and publication acknowledged before a new start.")
                }
                if profile == Self.cycleProfile && notificationAuthorization != "authorized" && notificationAuthorization != "provisional" {
                    return cycleNotStarted("Prepare native cycle notifications before starting gameplay.")
                }
                if let oldCycle = current?.cycle, !oldCycle.published {
                    return profile == Self.cycleProfile ? cycleNotStarted("Previous native cycle publication is not acknowledged.")
                        : failure("Previous native cycle publication is not acknowledged.")
                }
                if poisoned { return failure("Unknown native input freezes new runs until the runner process restarts.") }
                if current?.lock.ng2Locked({ current?.lease ?? false }) == true { return failure("Previous native run is still draining.") }
                if current?.lock.ng2Locked({ current?.exportBuildID != nil }) == true { return failure("Previous native image export is still being prepared.") }
                if NG2CaptureBridge.pendingRequests != 0 { return failure("Previous daemon capture is still outstanding.") }
                if seen.contains(id) || seen.count >= 128 { return failure("Run identity was already consumed or process run limit reached.") }
                let run = NG2Run(owner: owner, id: id, now: Self.now(), profile: profile)
                if let old = current {
                    old.lock.ng2Locked {
                        old.exportCache = nil
                        old.images.removeAll(); old.pinned.removeAll()
                        old.initial = nil; old.found = nil; old.latest = nil
                    }
                }
                current = run; seen.insert(id); created = run
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
            guard let archived = lock.ng2Locked({ history[id] }), archived.owner == owner else { return failure("Native run unavailable for this owner.") }
            if method == "necro_native_status", let value = params?["keepalive"], value.boolValue == nil {
                return failure("keepalive must be boolean.", -32602)
            }
            var result = historical(archived.response)
            if method == "necro_native_results" {
                guard archived.response["profile"]?.stringValue != Self.evidenceProfile else {
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
                if NG2TicketGuard.renewsHeartbeat(keepalive: params?["keepalive"]?.boolValue ?? false,
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
        run.profile == Self.cycleProfile ? Self.cycleEvidencePinLimit : 20
    }

    private func priorityCaptureIDs(_ run: NG2Run) -> [UInt64] {
        var ids: [UInt64] = []
        let decisions = run.restartDecisionCaptureIDs.keys.sorted().compactMap { run.restartDecisionCaptureIDs[$0] }
        let initial = decisions.isEmpty ? [run.initial?.id].compactMap({ $0 }) : []
        // Existing stop/goods/comparison evidence stays ahead of the bounded
        // per-restart set. Its initial strong frame is already in that set.
        for id in [run.terminalCaptureID, run.found?.id].compactMap({ $0 }) + initial
            + run.diagnosticCaptureIDs + [run.initialRejectedCaptureID].compactMap({ $0 }) + decisions
            + run.cycleDiagnosticCaptureIDs {
            if id != 0 && !ids.contains(id) { ids.append(id) }
        }
        return ids
    }

    private func selectedExportFrames(_ run: NG2Run) -> [NG2Frame] {
        var available = run.pinned
        for frame in run.images + [run.initial, run.found].compactMap({ $0 }) { available[frame.id] = frame }
        let priority = priorityCaptureIDs(run).compactMap { available[$0] }
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
            if state.job_id != cycle.companion.job_id && state.pending != 0 {
                cycle.assessment = nil; cycle.assessmentAdopted = false; cycle.rawSHA256 = nil
                if !cycle.classificationOutstanding { cycle.frames.removeAll() }
            }
            cycle.companion = state
            let needed = Set([state.capture_id, state.queued_capture_id, state.pause_source_capture_id,
                state.pause_capture_id, state.next_floor_capture_id].filter { $0 != 0 })
            let available = [frame, run.initial, run.found].compactMap { $0 } + run.images + Array(run.pinned.values)
            for item in available where needed.contains(item.id) { cycle.frames[item.id] = item }
        }
    }

    private func serviceCycleAssessment(_ run: NG2Run) {
        guard let cycle = run.cycle, let core = run.core else { return }
        refreshCycleEvidence(run)
        let job: NG2CycleJob? = run.lock.ng2Locked {
            let state = cycle.companion
            guard !cycle.classificationOutstanding, state.pending == 1, state.worker_started_ns == 0,
                  state.capture_id != 0, run.cancelReason == 0, !run.stopped, ownerActive(run),
                  !LockStateMonitor.shared().isLocked, let frame = cycle.frames[state.capture_id],
                  frame.generation == run.generation, frame.stable, !frame.startInFlight, !frame.endInFlight,
                  frame.startPrefix == state.prefix, frame.prefix == state.prefix,
                  frame.start == state.capture_start_ns,
                  ng2_controller_cycle_worker_begin(core, state.job_id, state.capture_id, state.prefix, Self.now()) == 1 else { return nil }
            var admitted = NG2ControllerCycleStatus(); ng2_controller_cycle_status(core, &admitted)
            cycle.companion = admitted; cycle.classificationOutstanding = true
            return NG2CycleJob(run, frame: frame, state: admitted)
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
                    self.cycle(run)
                }
            }
        }
        persistCycleCheckpoint(run)
        persistCycleOutcome(run)
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
        persistenceQueue.async {
            var success = false
            do {
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeCycleTestHooks.beforeIntentWrite?(state.job_id)
                #endif
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
                var dispatch = false
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false
                    if durable { cycle.storedCaptureIDs.insert(frame.id) }
                    guard let currentCore = run.core, run.generation == generation, run.cancelReason == 0,
                          !run.stopped, self.ownerActive(run), !LockStateMonitor.shared().isLocked else { return }
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
                _ = try spool.commitRecord(kind: "restart_outcome", cycle: UInt64(max(state.completed_shops, 0)), payload: NG2CycleWire.object(body))
                success = true
            } catch { }
            let durable = success
            self.controlQueue.async {
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
        }
    }

    private func persistCycleTerminal(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        let admission: (NG2CycleSpool, [NG2Frame], Set<UInt64>, NG2ControllerSnapshot?, NG2ControllerCycleStatus)? = run.lock.ng2Locked {
            guard !cycle.terminalPersistenceStarted, !cycle.workerBusy, let spool = cycle.spool else { return nil }
            cycle.terminalPersistenceStarted = true; cycle.persistenceOutstanding = true
            return (spool, selectedExportFrames(run), cycle.storedCaptureIDs, run.controllerSnapshot, cycle.companion)
        }
        guard let (spool, frames, stored, snapshot, state) = admission else {
            run.lock.ng2Locked { if cycle.spool == nil && !cycle.workerBusy { cycle.terminalPersisted = true } }
            return
        }
        let assessment = run.lock.ng2Locked { cycle.assessment }
        let adopted = run.lock.ng2Locked { cycle.assessmentAdopted }
        persistenceQueue.async {
            var saved = Set<UInt64>()
            var failure: String?
            do {
                let fresh = frames.filter { !stored.contains($0.id) }
                try spool.reserveCheckpoint(frames: fresh.count, metadataBytes: 256 * 1024)
                for frame in fresh {
                    _ = try spool.commitFrame(captureID: frame.id, rgba: frame.rgba, metadata: self.cycleFrameMetadata(frame)); saved.insert(frame.id)
                }
                let body: [String: JSONValue] = ["cycle": .object(NG2CycleWire.companion(state)),
                    "assessment": assessment.map { .object($0) } ?? .null, "assessment_adopted": .bool(adopted),
                    "controller": snapshot.map { .object(self.encodeCycleSnapshot($0, origin: "cycle_terminal")) } ?? .null]
                _ = try spool.commitRecord(kind: "terminal", cycle: UInt64(max(state.completed_shops, 0)), payload: NG2CycleWire.object(body))
            } catch { failure = "terminal_commit_failed" }
            self.controlQueue.async {
                run.lock.ng2Locked {
                    cycle.persistenceOutstanding = false; cycle.terminalPersisted = true
                    cycle.storedCaptureIDs.formUnion(saved)
                    if let failure { cycle.failure = failure }
                }
                self.notifyCycleIfNeeded(run); self.cycle(run)
            }
        }
    }

    private func notifyCycleIfNeeded(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        let outcome: Int32? = run.lock.ng2Locked {
            guard !cycle.recovered, !cycle.notificationRequested, ownerActive(run) else { return nil }
            let positive = run.controllerSnapshot?.status.paused == 1 && run.cancelReason == 0
                && (cycle.companion.outcome == 1 || cycle.companion.outcome == 2)
            guard positive || (run.terminal && cycleWorkersDrainedLocked(run, cycle)) else { return nil }
            cycle.notificationRequested = true; cycle.notificationState = "pending"
            return positive ? cycle.companion.outcome : -1
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
            content.body = "ゲームをポーズしました。商品を確認してください。"
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

    private func initializeCycle(_ run: NG2Run) {
        guard let cycle = run.cycle else { return }
        run.lock.ng2Locked { cycle.persistenceOutstanding = true }
        persistenceQueue.async {
            do {
                let provenance: [String: Any] = ["clock_id": run.clock, "accepted_started_ns": run.acceptedStarted,
                    "generation": run.generation, "runtime_instance_id": self.runtimeInstanceID,
                    "system_uptime_ns": UInt64(ProcessInfo.processInfo.systemUptime * 1_000_000_000)]
                let spool: NG2CycleSpool
                #if NG2_RUNTIME_HOST_TEST
                if let root = NG2RuntimeCycleTestHooks.spoolRoot {
                    spool = try NG2CycleSpool.testCreate(rootURL: root, runID: run.id, owner: run.owner, provenance: provenance)
                } else { spool = try NG2CycleSpool.create(runID: run.id, owner: run.owner, provenance: provenance) }
                #else
                spool = try NG2CycleSpool.create(runID: run.id, owner: run.owner, provenance: provenance)
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
                    if active { self.start(run) }
                    else {
                        if run.lock.ng2Locked({ run.cancelReason == 0 }) { run.cancel(15) }
                        run.lock.ng2Locked {
                            cycle.companion.state = 8; cycle.companion.status = 2
                            run.terminal = true; run.captureWorkerDone = true; run.lease = false
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
            return ["state": .string(run.terminal ? (run.lease ? "draining" : "stopped") : "running"),
                "terminal": .bool(run.terminal), "workers_drained": .bool(drained),
                "input_state": .int(Int(status?.input_state ?? cycle.recoveredInputState)), "ui_frozen": .bool(run.uiFrozen),
                "native_inflight": .bool(run.inFlight && !drained), "cycle": .object(NG2CycleWire.companion(cycle.companion)),
                "notification": .object(["authorization": .string(permission), "state": .string(cycle.notificationState)])]
        }
    }

    // Caller holds run.lock. Historical UNKNOWN remains input_state4/frozen;
    // it is distinct from an actual native callback that is still executing.
    private func cycleWorkersDrainedLocked(_ run: NG2Run, _ cycle: NG2CycleRun) -> Bool {
        !run.lease && !cycle.workerBusy && run.captureWorkerDone && !run.captureOutstanding && !run.mainOutstanding
    }

    private func beginCycleRecovery(owner: String, id: String) {
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
                if let header = try? spool.sessionBytes(),
                   let object = try? JSONSerialization.jsonObject(with: header) as? [String: Any],
                   let provenance = object["provenance"] as? [String: Any],
                   let original = provenance["clock_id"] as? String, self.lowerHexIdentity(original) { clock = original }
                let run = NG2Run(owner: owner, id: id, now: Self.now(), profile: Self.cycleProfile, clock: clock)
                let cycle = run.cycle!
                cycle.spool = spool; cycle.recovered = true; cycle.terminalPersisted = true
                cycle.companion.state = 8
                run.terminal = true; run.stopped = true; run.lease = false; run.captureWorkerDone = true
                let records = try spool.records()
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
                let unknown = records.contains { record in
                    let controller = record.payload["controller"] as? [String: Any]
                    return (controller?["input_state"] as? NSNumber)?.intValue == 4
                }
                let noTerminal = !records.contains(where: { $0.kind == "terminal" })
                if noTerminal || dangling || unknown { cycle.recoveredInputState = 4; run.uiFrozen = true }
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
            let value = NG2CycleExport(spool: spool, status: status, recovered: cycle.recovered, owner: run.owner)
            cycle.exporter = value; return value
        }
        exporter?.prepare()
    }

    private func handleCycle(owner: String, id: String, params: [String: JSONValue]) -> ([String: JSONValue]?, JSONRPCError?) {
        let mode = params["mode"]?.stringValue ?? "status"
        let base: Set<String> = ["run_id", "mode", Self.ownerParam]
        let extra: Set<String>
        switch mode {
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
        if mode == "trial_support" {
            let payload: [String: JSONValue] = ["stop_detail_schema": .string("ngg2-stop-detail-v1"),
                "handoff_schema": .string("ngg2-trial-handoff-v1"), "maximum_run_ids": .int(128),
                "pin_limit": .int(Self.cycleEvidencePinLimit)]
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload), nil)
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
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload), nil)
        }
        let existing = lock.ng2Locked { current }
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
        if mode == "status" {
            guard params["keepalive"] == nil || params["keepalive"]?.boolValue != nil else { return failure("keepalive must be boolean.", -32602) }
            run.lock.ng2Locked {
                if !cycle.recovered && NG2TicketGuard.renewsHeartbeat(keepalive: params["keepalive"]?.boolValue ?? false,
                    ownerActive: ownerActive(run), cancelled: run.cancelReason != 0) { run.heartbeat = Self.now() }
            }
            return (NG2CycleWire.envelope(runID: id, mode: mode, payload: cyclePayload(run)), nil)
        }
        guard run.lock.ng2Locked({ run.terminal && !run.lease && !cycle.workerBusy }) else {
            return failure("Cycle export requires terminal, drained workers.")
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
                    if let previous = current, previous.id == run.id {
                        previous.lock.ng2Locked { if !previous.lease { previous.cycle?.published = true } }
                    }
                    unpublishedCycles.removeAll(where: { $0 == run.id })
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
        return (NG2CycleWire.envelope(runID: id, mode: mode, payload: payload), nil)
    }

    private func isSHA256(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
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
    func testOriginalFrameEvidence(_ id: String, captureIDs: [UInt64]) -> [UInt64: (Data, [String: JSONValue])]? {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return nil }
        let frames = run.lock.ng2Locked {
            captureIDs.compactMap { captureID in run.pinned[captureID] ?? run.images.first(where: { $0.id == captureID }) }
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
        return ["run_id": .string(projection.id), "profile": .string(projection.profile), "state": .string(projection.state),
            "api_version": .string("1.98.16-ngg2"), "report": .object(report)]
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
        let createdCore = run.cycle == nil ? ng2_controller_create(Self.now()) : ng2_controller_create_cycle(run.acceptedStarted)
        guard let core = createdCore else {
            run.cancel(15); run.lock.ng2Locked { run.terminal = true; run.captureWorkerDone = true; run.lease = false }; return
        }
        run.core = core
        // This independent timer starts before the main-thread barrier and
        // activation. It invalidates a queued bootstrap even if main is stuck.
        let watchdog = DispatchSource.makeTimerSource(queue: watchdogQueue)
        watchdog.schedule(deadline: .now(), repeating: .milliseconds(100))
        watchdog.setEventHandler { [weak self, weak run] in
            guard let self, let run else { return }
            if !self.ownerActive(run) { run.cancel(5) }
            let time = Self.now()
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
            if run.lock.ng2Locked({ run.cancelReason == 0 }) && self.ownerActive(run) && !LockStateMonitor.shared().isLocked {
                // One nonblocking LaunchServices activation also launches the
                // game when needed. No Options/calibration screen is opened.
                let allowed = run.lock.ng2Locked { () -> Bool in
                    if run.cancelReason != 0 { return false }
                    run.bootstrapUIStarted = true
                    return true
                }
                if allowed { _ = ForegroundApp.openBundleID(Self.game) }
                run.expectedPID = ForegroundApp.processID(forBundleID: Self.game)
                run.foreground = run.expectedPID > 0 && ForegroundApp.frontmostPID() == run.expectedPID
                run.fast = FastActionHandler(app: XCUIApplication(bundleIdentifier: Self.game))
                if !NG2CaptureBridge.prepare() { run.cancel(6) }
            }
        }
        run.lock.ng2Locked { run.bootstrapOutstanding = false }
        let activationDeadline = Self.now() + 3_000_000_000
        run.lock.ng2Locked { run.startupRasterDeadline = activationDeadline }
        while !run.foreground && !run.lock.ng2Locked({ run.stopped }) && Self.now() < activationDeadline {
            Thread.sleep(forTimeInterval: 0.05)
            run.lock.ng2Locked { run.bootstrapOutstanding = true }
            DispatchQueue.main.sync {
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
        capture.name = "NecroGold native capture"; capture.qualityOfService = .userInteractive; capture.start()
    }

    private func capture(_ run: NG2Run) {
        // Only the final failure enters the existing closed wire record. A
        // recovered portrait is never published as a failed game raster.
        var startupPortrait: (generation: UInt64, id: UInt64, start: UInt64, end: UInt64, failure: NG2Raster.Failure)?
        defer {
            run.lock.ng2Locked { run.captureWorkerDone = true }
            controlQueue.async {
                self.cycle(run)
                #if NG2_RUNTIME_HOST_TEST
                NG2RuntimeTestHooks.afterCaptureDrainProcessed?(run.id)
                #endif
            }
        }
        while !run.lock.ng2Locked({ run.stopped }) {
            if !streamsDrained { Thread.sleep(forTimeInterval: 0.005); continue }
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
            var startupDenied = false
            let admission: (UInt64, UInt64, Bool, UInt64, UInt64)? = run.lock.ng2Locked {
                guard !run.stopped, run.cancelReason == 0, self.ownerActive(run) else { return nil }
                if let prior = startupPortrait, !run.startupRasterReady,
                   !self.startupPortraitGateLocked(run, generation: prior.generation, now: Self.now()) {
                    startupDenied = run.generation == prior.generation && run.cancelReason == 0 && !run.stopped
                    return nil
                }
                run.captureID += 1; run.captureOutstanding = true
                return (run.captureID, run.prefix, run.inFlight, run.generation, Self.now())
            }
            guard let before = admission else {
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
            let frame = NG2Frame(id: before.0, start: start, end: captureEnd, decodeEnd: decodeEnd,
                generation: before.3, analysisStart: analysisStart, analysisEnd: Self.now(), analysis: analysis,
                startPrefix: before.1, prefix: endPrefix, startInFlight: before.2, endInFlight: endInFlight,
                stable: !before.2 && !endInFlight && before.1 == endPrefix, rgba: frameRGBA,
                rasterTrace: decoded.trace, encodedBytes: raw?.count ?? 0,
                diagnosticOrientation: decoded.diagnosticOrientation)
            if analyzed != 0 {
                let trace = frame.rasterTrace
                commitCaptureFailure(run, generation: before.3, id: frame.id, start: frame.start, end: frame.end,
                    failure: .init(stage: .analysis, code: .invalidRGBA, encodedBytes: frame.encodedBytes,
                        sourceWidth: trace.sourceWidth, sourceHeight: trace.sourceHeight, orientation: frame.diagnosticOrientation))
                cancelCaptureFailure(run, generation: before.3); return
            }
            run.lock.ng2Locked {
                if run.generation == before.3 && !run.stopped {
                    if run.latest != nil { run.replacedFrames += 1 }
                    run.latest = frame
                }
            }
            controlQueue.async { self.cycle(run) }
            Thread.sleep(forTimeInterval: 0.005)
        }
    }

    // A synchronous PAUSE occupies controlQueue until main's synth returns.
    // Give this already running, bounded full-goods job its original adoption
    // window before asking C to mint that PAUSE. No command is reserved here.
    private func waitForCycleAssessmentBeforePause(_ run: NG2Run, status: NG2ControllerStatus) -> Bool {
        run.lock.ng2Locked {
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

    private func cycle(_ run: NG2Run) {
        guard let core = run.core else { return }
        let now = Self.now()
        let cancelled = run.lock.ng2Locked { run.cancelReason }
        if cancelled != 0 { ng2_controller_cancel(core, now, cancelled) }
        let frame: NG2Frame? = run.lock.ng2Locked {
            let frame = run.latest; run.latest = nil; return frame
        }
        if let frame, cancelled == 0 {
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
                    ng2_controller_observe_at(core, scene, frame.id, frame.start, frame.end, frame.prefix, frame.stable ? 1 : 0, observeStart)
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
                    if run.initial == nil { run.initial = frame }
                    if scene.pointee.goods == 2 && run.found == nil { run.found = frame }
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
                } else {
                    // A generation-only replacement discards this old frame;
                    // it must not cancel or mutate the current generation.
                    let reason = run.lock.ng2Locked { run.cancelReason != 0 ? run.cancelReason : (self.ownerActive(run) ? Int32(0) : Int32(5)) }
                    if reason != 0 {
                        run.cancel(reason)
                        ng2_controller_cancel(core, Self.now(), reason)
                    }
                }
        }
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status)
        serviceCycleAssessment(run)
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
                NG2TicketGuard.canReleaseLease(captureWorkerDone: run.captureWorkerDone,
                    captureOutstanding: run.captureOutstanding, mainOutstanding: run.mainOutstanding, legacyCaptures: legacy)
                    && !(run.cycle?.workerBusy ?? false) && (run.cycle == nil || run.cycle!.terminalPersisted)
            }
            if drained {
                ng2_controller_destroy(core); run.core = nil
                run.controlTimer?.cancel(); run.controlTimer = nil
                run.watchdog?.cancel(); run.watchdog = nil
                run.lock.ng2Locked { run.lease = false }
                notifyCycleIfNeeded(run)
                var snapshot = response(run)
                let retained = run.lock.ng2Locked { Set(run.pinned.keys).union(run.images.map { $0.id }).count }
                snapshot["retained_images"] = .int(retained)
                snapshot["omitted_image_count"] = .int(retained)
                snapshot["exported_images"] = .int(0)
                lock.ng2Locked {
                    history[run.id] = (owner: run.owner, response: snapshot)
                    historyOrder.append(run.id)
                    if historyOrder.count > 64 { history.removeValue(forKey: historyOrder.removeFirst()) }
                }
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
            if !waitForCycleAssessmentBeforePause(run, status: status) {
                var command = NG2Command()
                let ticket = ng2_controller_tick(core, Self.now(), run.foreground ? 1 : 0,
                    LockStateMonitor.shared().isLocked ? 1 : 0, ownerActive(run) ? 1 : 0, &command)
                if ticket == 1 {
                    if run.cycle != nil && command.kind == 3 {
                        refreshCycleEvidence(run)
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
                let lostReason: Int32 = !ownerActive ? 5 : (locked ? 4 : (!foreground ? 3 : (!authorityFresh ? 7 : 0)))
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
                run.inFlight = true
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
                if run.mainCommandID == command.id && outcome == 1 { run.prefix = command.id; run.inFlight = false }
                // A started failure remains inflight: never certify a later
                // frame prefix or issue an automatic cleanup tap from it.
            }
        }
        guard run.lock.ng2Locked({ run.mainCommandID == command.id && (run.generation == generation || run.cancelReason != 0) }) else { return }
        let cancelled = run.lock.ng2Locked { run.cancelReason }
        if outcome == 0 && cancelled != 0 { ng2_controller_cancel(core, Self.now(), cancelled) }
        ng2_controller_complete(core, command.id, Self.now(), outcome)
        run.lock.ng2Locked {
            if run.mainCommandID == command.id { run.mainCommandID = 0; run.preparation = nil }
        }
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
        guard (run.profile == Self.evidenceProfile || run.profile == Self.cycleProfile), run.cancelReason == 0, !run.stopped,
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
        // Reserve the one existing slot even when the rest of pin work is
        // deferred until after dispatch. The previous snapshot is not reused.
        pinDispatchSourceLocked(run, frame.id)
    }

    // Call under run.lock, before a dispatch snapshot can defer pin work.
    // A replacement within one level cannot add an unbounded evidence slot.
    private func retainRestartDecisionLocked(_ run: NG2Run, _ snapshot: NG2ControllerSnapshot) {
        let status = snapshot.status
        guard (run.profile == Self.evidenceProfile || run.profile == Self.cycleProfile), run.cancelReason == 0, !run.stopped,
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
    private func pinDispatchSourceLocked(_ run: NG2Run, _ source: UInt64) {
        guard source != 0 else { return }
        run.references.insert(source)
        guard run.pinned[source] == nil,
              let frame = (run.images + [run.initial, run.found].compactMap({ $0 }))
                .first(where: { $0.id == source }) else { return }
        let protected = Set(priorityCaptureIDs(run) + [source])
        let limit = evidencePinLimit(run)
        if run.pinned.count == limit, let evicted = run.pinned.keys.sorted().first(where: { !protected.contains($0) }) {
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
            if run.profile == Self.cycleProfile {
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
                if run.pinned.count == limit, let evicted = run.pinned.keys.sorted().first(where: { !protected.contains($0) }) {
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
        let kinds = ["none", "negative_limit", "clear_search_limit"]
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
