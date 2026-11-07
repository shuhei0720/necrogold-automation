import Foundation
import CoreGraphics
#if !NG2_RUNTIME_HOST_TEST
import XCTest
import UIKit
#endif
import CryptoKit

#if NG2_RUNTIME_HOST_TEST
enum NG2RuntimeTestHooks {
    static var clock: (() -> UInt64)?
    static var beforeCaptureAdmission: (() -> Void)?
    static var beforeMainAdmission: (() -> Void)?
    static var beforeMainAuthority: (() -> Void)?
    static var beforeAnalysisCommit: (() -> Void)?
    static var afterForegroundQuery: (() -> Void)?
    static var beforeControlTick: (() -> Void)?
    static var scheduleTicket: ((UInt64, @escaping () -> Void) -> Bool)?
    static var afterTicketReturned: ((UInt64) -> Void)?
    static var afterCaptureDrainProcessed: ((String) -> Void)?
    static var beforeCaptureFailureCommit: ((String) -> Void)?
    static var analysisRGBA: ((Data) -> Data)?
    static var afterWatchdogCheck: ((String, UInt64) -> Void)?
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

private final class NG2Run {
    let lock = NSLock()
    let owner: String
    let id: String
    let clock = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
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
    var references = Set<UInt64>()
    var analyzedFrames: UInt64 = 0
    var evictedFrames: UInt64 = 0
    var initial: NG2Frame?
    var found: NG2Frame?
    var report: [String: JSONValue] = [:]
    var captures: [JSONValue] = []
    var rasterSamples: [JSONValue] = []
    var rasterSamplesDropped: UInt64 = 0
    var captureFailure: [String: JSONValue]?
    var dispatchFailure: [String: JSONValue]?
    var replacedFrames: UInt64 = 0
    var terminal = false
    var successful = false
    var uiFrozen = false
    var captureTimedOut = false
    var bootstrapUIStarted = false
    var core: OpaquePointer?
    var expectedPID: pid_t = 0
    var foreground = false
    var fast: FastActionHandler?
    var controlTimer: DispatchSourceTimer?
    var watchdog: DispatchSourceTimer?
    var lastCache: UInt64 = 0
    init(owner: String, id: String, now: UInt64) { self.owner = owner; self.id = id; heartbeat = now; acceptedStarted = now }
    func cancel(_ reason: Int32) {
        lock.ng2Locked {
            if cancelReason == 0 { cancelReason = reason; generation &+= 1 }
            stopped = true
            latest = nil
        }
    }
}

/// One bounded native run. Controller C state is used only on controlQueue, except begin()
/// on main while controlQueue synchronously waits for that exact call.
/// Status/cancel RPCs read immutable cached dictionaries and never touch C.
final class NG2Runtime {
    static let shared = NG2Runtime()
    static let methods: Set<String> = ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results"]
    static let ownerParam = "_necro_owner"
    static let profile = "normal-1-1-v1"
    private static let game = "jp.co.spike-chunsoft.necrodancerjp"
    private let lock = NSLock()
    private let controlQueue = DispatchQueue(label: "necro.native.control", qos: .userInteractive)
    private let watchdogQueue = DispatchQueue(label: "necro.native.watchdog", qos: .userInteractive)
    private var current: NG2Run?
    private var seen = Set<String>()
    // Metadata for at most 64 drained runs. Only the current run retains raw
    // rasters (at most 20 x 896x414x4 bytes plus capture/analysis handoff).
    private var history: [String: (owner: String, response: [String: JSONValue])] = [:]
    private var historyOrder: [String] = []
    private var streamCaptures = 0
    // A started input without a trustworthy ACK freezes all later UI for this
    // runner process. Worker drain does not certify the game input outcome.
    private var poisoned = false
    private init() {}
    static func now() -> UInt64 {
        #if NG2_RUNTIME_HOST_TEST
        if let clock = NG2RuntimeTestHooks.clock { return clock() }
        #endif
        return DispatchTime.now().uptimeNanoseconds
    }
    private func ownerActive(_ run: NG2Run) -> Bool {
        !RemoteSession.shared.paused && AuthManager.shared.clientName(forTokenId: run.owner) != nil
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
              id.utf8.count == 32, id.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            return failure("Invalid native request identity.", -32602)
        }
        let allowed: Set<String> = method == "necro_native_start" ? ["run_id", "profile", Self.ownerParam]
            : (method == "necro_native_status" ? ["run_id", "keepalive", Self.ownerParam] : ["run_id", Self.ownerParam])
        guard Set((params ?? [:]).keys).isSubset(of: allowed) else { return failure("Unknown native request parameter.", -32602) }
        if method == "necro_native_start" {
            guard params?["profile"]?.stringValue == Self.profile else { return failure("Unsupported native profile.", -32602) }
            guard !RemoteSession.shared.paused else { return failure("Owner paused native control.") }
            var created: NG2Run?
            let answer: ([String: JSONValue]?, JSONRPCError?) = lock.ng2Locked {
                if let old = current, old.owner == owner, old.id == id { return (response(old), nil) }
                if let archived = history[id], archived.owner == owner { return (historical(archived.response), nil) }
                if poisoned { return failure("Unknown native input freezes new runs until the runner process restarts.") }
                if current?.lock.ng2Locked({ current?.lease ?? false }) == true { return failure("Previous native run is still draining.") }
                if NG2CaptureBridge.pendingRequests != 0 { return failure("Previous daemon capture is still outstanding.") }
                if seen.contains(id) || seen.count >= 128 { return failure("Run identity was already consumed or process run limit reached.") }
                let run = NG2Run(owner: owner, id: id, now: Self.now())
                current = run; seen.insert(id); created = run
                return (response(run), nil)
            }
            if let run = created { controlQueue.async { self.start(run) } }
            return answer
        }
        guard let run = lock.ng2Locked({ current }), run.owner == owner, run.id == id else {
            guard let archived = lock.ng2Locked({ history[id] }), archived.owner == owner else { return failure("Native run unavailable for this owner.") }
            if method == "necro_native_status", let value = params?["keepalive"], value.boolValue == nil {
                return failure("keepalive must be boolean.", -32602)
            }
            var result = historical(archived.response)
            if method == "necro_native_results" {
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
        guard ownerActive(run),
              run.lock.ng2Locked({ run.terminal && !run.lease && !run.captureOutstanding && run.captureWorkerDone }) else {
            return failure("Native images require a terminal, drained run and active owner.")
        }
        let frames: [NG2Frame] = run.lock.ng2Locked {
            var selected: [NG2Frame] = []
            for frame in [run.images.last, run.found, run.initial].compactMap({ $0 })
                + run.pinned.values.sorted(by: { $0.id > $1.id }) + Array(run.images.reversed()) {
                if !selected.contains(where: { $0.id == frame.id }) { selected.append(frame) }
            }
            return Array(selected.prefix(20))
        }
        var images: [JSONValue] = []
        var totalImageBytes = 0
        var exportedIDs = Set<UInt64>()
        // Encode stop/found/initial anchors before event evidence so a byte
        // budget cannot silently give later ordinary frames their slots.
        for frame in frames {
            guard let bytes = NG2Raster.png(frame.rgba) else { return failure("Native image encoding failed.") }
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
        guard ownerActive(run) else { return failure("Owner paused native export.") }
        var result = response(run); result["images"] = .array(images)
        result["retained_images"] = .int(frames.count)
        result["exported_images"] = .int(images.count)
        run.lock.ng2Locked {
            result["omitted_image_count"] = number(run.analyzedFrames - min(run.analyzedFrames, UInt64(images.count)))
            result["omitted_capture_ids"] = .array(run.references.subtracting(exportedIDs).sorted().map { number($0) })
        }
        result["exported_capture_ids"] = .array(exportedIDs.sorted().map { number($0) })
        return (result, nil)
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
        }
    }
    #if NG2_RUNTIME_HOST_TEST
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
        run.lock.ng2Locked {
            let state = run.terminal ? (run.lease ? "draining" : (run.successful ? "completed" : "stopped")) : (run.report.isEmpty ? "accepted" : "running")
            var report = run.report
            report["schema"] = .string("ngg2-native-v1")
            if report["input_state"] == nil { report["input_state"] = .int(0) }
            if run.inFlight && report["input_state"]?.intValue != 4 { report["input_state"] = .int(2) }
            if report["terminal"] == nil { report["terminal"] = .int(run.terminal ? 1 : 0) }
            report["clock_id"] = .string(run.clock)
            report["device_now_ns"] = number(Self.now())
            report["cancel_requested"] = .bool(run.cancelReason != 0)
            report["capture_outstanding"] = .bool(run.captureOutstanding)
            report["capture_timed_out"] = .bool(run.captureTimedOut)
            report["bootstrap_ui_started"] = .bool(run.bootstrapUIStarted)
            report["accepted_started_ns"] = number(run.acceptedStarted)
            report["workers_drained"] = .bool(!run.lease)
            report["ui_frozen"] = .bool(run.uiFrozen)
            report["main_ticket_outstanding"] = .bool(run.mainOutstanding)
            report["live_completed_prefix"] = number(run.prefix)
            report["native_inflight"] = .bool(run.inFlight)
            report["capture_backend"] = .string("direct_daemon_jpeg_only")
            report["analysis_engine"] = .string("native_C_v1")
            report["capture_time_semantics"] = .string("request_call_interval_not_presentation_timestamp")
            report["input_time_semantics"] = .string("synth_call_interval_not_game_receipt_timestamp")
            report["native_capture_requests"] = number(run.captureID)
            report["latest_frames_replaced"] = number(run.replacedFrames)
            report["captures"] = .array(run.captures)
            report["raster_samples"] = .array(run.rasterSamples)
            report["raster_samples_dropped"] = number(run.rasterSamplesDropped)
            report["capture_failure"] = run.captureFailure.map { JSONValue.object($0) } ?? .null
            report["dispatch_failure"] = run.dispatchFailure.map { JSONValue.object($0) } ?? .null
            report["daemon_requests_outstanding"] = .int(Int(NG2CaptureBridge.pendingRequests))
            let retained = Set(run.pinned.keys).union(run.images.map { $0.id })
            report["analyzed_capture_count"] = number(run.analyzedFrames)
            report["evicted_capture_count"] = number(run.evictedFrames)
            report["retained_image_count"] = .int(retained.count)
            report["pinned_image_count"] = .int(run.pinned.count)
            report["recent_image_count"] = .int(run.images.count)
            report["referenced_capture_ids"] = .array(run.references.sorted().map { number($0) })
            report["missing_capture_ids"] = .array(run.references.subtracting(retained).sorted().map { number($0) })
            return ["run_id": .string(run.id), "profile": .string(Self.profile), "state": .string(state),
                "api_version": .string("1.98.14-ngg2"), "report": .object(report)]
        }
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
        guard let core = ng2_controller_create(Self.now()) else {
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
            let admission: (UInt64, UInt64, Bool, UInt64, UInt64)? = run.lock.ng2Locked {
                guard !run.stopped, run.cancelReason == 0, self.ownerActive(run) else { return nil }
                run.captureID += 1; run.captureOutstanding = true
                return (run.captureID, run.prefix, run.inFlight, run.generation, Self.now())
            }
            guard let before = admission else { return }
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
            case .success(let value): decoded = value
            case .failure(let failure):
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
            let analysisRGBA = NG2RuntimeTestHooks.analysisRGBA?(decoded.rgba) ?? decoded.rgba
            #else
            let analysisRGBA = decoded.rgba
            #endif
            let analyzed = analysisRGBA.withUnsafeBytes { ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                analysisRGBA.count, NG2Raster.stride, scene) }
            let frame = NG2Frame(id: before.0, start: start, end: captureEnd, decodeEnd: decodeEnd,
                generation: before.3, analysisStart: analysisStart, analysisEnd: Self.now(), analysis: analysis,
                startPrefix: before.1, prefix: endPrefix, startInFlight: before.2, endInFlight: endInFlight,
                stable: !before.2 && !endInFlight && before.1 == endPrefix, rgba: decoded.rgba,
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
                NG2RuntimeTestHooks.beforeAnalysisCommit?()
                #endif
                // Commit observation and image evidence at one cancellation
                // gate. Analysis runs outside this gate; stale results do not.
                let committed = run.lock.ng2Locked { () -> Bool in
                    guard run.generation == analysisGeneration, run.cancelReason == 0, !run.stopped, self.ownerActive(run) else { return false }
                    ng2_controller_observe(core, scene, frame.id, frame.start, frame.end, frame.prefix, frame.stable ? 1 : 0)
                    run.captures.append(.object(["id": number(frame.id), "start_ns": number(frame.start),
                        "end_ns": number(frame.end), "decode_end_ns": number(frame.decodeEnd),
                        "analysis_start_ns": number(frame.analysisStart), "analysis_end_ns": number(frame.analysisEnd),
                        "observe_end_ns": number(Self.now()),
                        "completed_prefix_start": number(frame.startPrefix), "completed_prefix_end": number(frame.prefix),
                        "inflight_start": .bool(frame.startInFlight), "inflight_end": .bool(frame.endInFlight),
                        "stable": .bool(frame.stable)]))
                    if run.captures.count > 256 { run.captures.removeFirst(run.captures.count - 256) }
                    let trace = frame.rasterTrace
                    run.rasterSamples.append(.object(["capture_id": number(frame.id),
                        "source_width": .int(trace.sourceWidth), "source_height": .int(trace.sourceHeight),
                        "orientation": .int(trace.orientation), "source_ns": number(trace.sourceNs),
                        "draw_ns": number(trace.drawNs), "orient_ns": number(trace.orientNs),
                        "scale_ns": number(trace.scaleNs), "copy_pixels": number(trace.copyPixels)]))
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
        if status.terminal != 0 {
            run.lock.ng2Locked { run.terminal = true; run.successful = status.goods == 1 && status.paused == 1; run.stopped = true; run.mainCommandID = 0; run.latest = nil }
            cache(run, status)
            let legacy = lock.ng2Locked { streamCaptures } + Int(NG2CaptureBridge.pendingRequests)
            let drained = run.lock.ng2Locked {
                NG2TicketGuard.canReleaseLease(captureWorkerDone: run.captureWorkerDone,
                    captureOutstanding: run.captureOutstanding, mainOutstanding: run.mainOutstanding, legacyCaptures: legacy)
            }
            if drained {
                ng2_controller_destroy(core); run.core = nil
                run.controlTimer?.cancel(); run.controlTimer = nil
                run.watchdog?.cancel(); run.watchdog = nil
                run.lock.ng2Locked { run.lease = false }
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
            var command = NG2Command()
            let ticket = ng2_controller_tick(core, Self.now(), run.foreground ? 1 : 0,
                LockStateMonitor.shared().isLocked ? 1 : 0, ownerActive(run) ? 1 : 0, &command)
            if ticket == 1 {
                let generation = run.lock.ng2Locked {
                    run.mainCommandID = command.id; run.mainCallbacks.insert(command.id); return run.generation
                }
                ng2_controller_status(core, &status); cache(run, status)
                let authority = prepare(run, command, generation: generation)
                let at = Self.now()
                let delay = command.not_before_ns > at ? Double(command.not_before_ns - at) / 1e9 : 0
                let callback = {
                    self.execute(run, command, generation: generation, authority: authority)
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
                    return
                }
                #endif
                controlQueue.asyncAfter(deadline: .now() + delay, execute: callback)
            }
        }
        if now - min(now, run.lastCache) >= 50_000_000 { ng2_controller_status(core, &status); cache(run, status) }
    }

    private struct AuthoritySample {
        var start: UInt64 = 0
        var end: UInt64 = 0
        var foreground = false
    }
    private func ownsTicket(_ run: NG2Run, _ command: NG2Command, generation: UInt64) -> Bool {
        run.lock.ng2Locked { run.mainCommandID == command.id && run.generation == generation }
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

    private func execute(_ run: NG2Run, _ command: NG2Command, generation: UInt64, authority: AuthoritySample) {
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
                }
                guard NG2TicketGuard.permits(expectedGeneration: generation, currentGeneration: run.generation,
                    cancelled: run.cancelReason != 0, ownerActive: ownerActive, foreground: foreground,
                    locked: locked, now: now, notBefore: command.not_before_ns, deadline: command.deadline_ns),
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
        run.lock.ng2Locked { if run.mainCommandID == command.id { run.mainCommandID = 0 } }
        var status = NG2ControllerStatus(); ng2_controller_status(core, &status); cache(run, status)
        cycle(run)
    }

    private func cache(_ run: NG2Run, _ s: NG2ControllerStatus) {
        guard let core = run.core else { return }
        if s.input_state == 4 {
            lock.ng2Locked { poisoned = true }
            run.lock.ng2Locked { run.uiFrozen = true }
        }
        var events = [NG2ControllerEvent](repeating: NG2ControllerEvent(), count: 64)
        let count = events.withUnsafeMutableBufferPointer { ng2_controller_events(core, $0.baseAddress, $0.count) }
        var changes = [NG2ControllerSceneChange](repeating: NG2ControllerSceneChange(), count: 3)
        let changeCount = changes.withUnsafeMutableBufferPointer { ng2_controller_scene_changes(core, $0.baseAddress, $0.count) }
        var motionWait = NG2ControllerMotionWait()
        ng2_controller_motion_wait(core, &motionWait)
        run.lock.ng2Locked {
            var required = Set<UInt64>()
            for event in events.prefix(min(count, events.count)) {
                if event.command.source_capture_id != 0 { required.insert(event.command.source_capture_id) }
                if event.observed_capture_id != 0 { required.insert(event.observed_capture_id) }
            }
            for change in changes.prefix(min(changeCount, changes.count)) {
                required.insert(change.source_capture_id); required.insert(change.observed_capture_id)
            }
            for frame in [run.initial, run.found].compactMap({ $0 }) { required.insert(frame.id) }
            if s.terminal != 0 && s.last_capture_id != 0 { required.insert(s.last_capture_id) }
            run.references.formUnion(required)
            var available = run.pinned
            for frame in run.images + [run.initial, run.found].compactMap({ $0 }) { available[frame.id] = frame }
            let anchors = Set([run.initial?.id, run.found?.id, s.terminal != 0 ? s.last_capture_id : nil].compactMap { $0 })
            for id in anchors.sorted() where run.pinned[id] == nil {
                guard let frame = available[id] else { continue }
                if run.pinned.count == 20, let evicted = run.pinned.keys.sorted().first(where: { !anchors.contains($0) }) {
                    run.pinned.removeValue(forKey: evicted); run.evictedFrames += 1
                }
                if run.pinned.count < 20 { run.pinned[id] = frame }
            }
            for id in required.sorted() where run.pinned[id] == nil {
                if run.pinned.count < 20, let frame = available[id] { run.pinned[id] = frame }
            }
        }
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
            "events": .array(encoded), "scene_changes": .array(encodedChanges),
            "motion_wait": .object(["command_id": number(motionWait.command_id),
                "source_capture_id": number(motionWait.source_capture_id), "last_capture_id": number(motionWait.last_capture_id),
                "deadline_ns": number(motionWait.deadline_ns), "attempts": integer(motionWait.attempts),
                "last_motion": integer(motionWait.last_motion), "active": .bool(motionWait.active == 1)])]
        run.lastCache = Self.now()
        run.lock.ng2Locked { run.report = report }
    }
}
