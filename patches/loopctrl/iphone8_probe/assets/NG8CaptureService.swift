import Foundation
import Dispatch
import ImageIO
import CryptoKit
import CoreFoundation
import Darwin

private final class NG8ServiceClock: NG8ProbeClock {
    let clockID = "dispatch-uptime-ns-v1"
    var nowNs: UInt64 { DispatchTime.now().uptimeNanoseconds }
}

private final class NG8ServiceWatch: NG8ProbeWatch {
    private let source: DispatchSourceTimer
    init(deadlineNs: UInt64, queue: DispatchQueue, fired: @escaping () -> Void) {
        source = DispatchSource.makeTimerSource(queue: queue)
        source.schedule(deadline: DispatchTime(uptimeNanoseconds: deadlineNs), leeway: .nanoseconds(0))
        source.setEventHandler(handler: fired)
        source.resume()
    }
    func cancel() { source.cancel() }
    deinit { source.cancel() }
}

// Drop the body closure (and its candidate Data) before reporting our owned
// job's return. This proves no literal daemon or Dispatch closure stack return.
private final class NG8ServiceOwnedJob {
    private var body: (() -> Void)?
    init(_ body: @escaping () -> Void) { self.body = body }
    func runAndDrop() {
        let operation = body
        body = nil
        operation?()
    }
}

private final class NG8ServiceScheduler: NG8ProbeScheduler {
    private let worker = DispatchQueue(label: "ng8.capture.worker", qos: .userInitiated)
    private let coordinator = DispatchQueue(label: "ng8.capture.coordinator", qos: .userInitiated)
    private let watchdog = DispatchQueue(label: "ng8.capture.watchdog", qos: .userInitiated)
    private func enqueue(_ queue: DispatchQueue, _ body: @escaping () -> Void,
                         returned: @escaping () -> Void) {
        let job = NG8ServiceOwnedJob(body)
        queue.async { job.runAndDrop(); returned() }
    }
    func enqueueMain(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        enqueue(.main, body, returned: returned)
    }
    func enqueueWorker(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        enqueue(worker, body, returned: returned)
    }
    func enqueueCoordinator(_ body: @escaping () -> Void, returned: @escaping () -> Void) {
        enqueue(coordinator, body, returned: returned)
    }
    func watch(at deadlineNs: UInt64, fired: @escaping () -> Void) -> NG8ProbeWatch {
        NG8ServiceWatch(deadlineNs: deadlineNs, queue: watchdog, fired: fired)
    }
}

private final class NG8ServiceDriver: NG8ProbeCaptureDriver {
    private let bridge: NG8CaptureService.Bridge
    init(_ bridge: NG8CaptureService.Bridge) { self.bridge = bridge }
    func prepare(_ ticket: NG8ProbeTicket) -> Result<Void, NG8ProbeFailure> {
        bridge.prepare() ? .success(()) : .failure(.prepareUnavailable)
    }
    func request(_ ticket: NG8ProbeTicket,
                 reply: @escaping (Result<Data, NG8ProbeFailure>) -> Void,
                 drained: @escaping () -> Void) {
        bridge.request({ data, code in
            if let code = code {
                // Never relay arbitrary NSError/daemon text, including a raw
                // string that happens to match an unrelated public enum case.
                let reason: NG8ProbeFailure
                switch code {
                case "api_unavailable": reason = .apiUnavailable
                case "prepare_unavailable": reason = .prepareUnavailable
                case "request_unavailable": reason = .requestUnavailable
                case "request_exception": reason = .requestException
                case "reply_exception": reason = .replyException
                case "bytes_invalid": reason = .bytesInvalid
                default: reason = .captureFailed
                }
                reply(.failure(reason))
            } else if let data = data {
                reply(.success(data))
            } else {
                reply(.failure(.captureFailed))
            }
        }, drained)
    }
}

private enum NG8ServiceJPEG {
    private static func integer(_ value: Any?, range: ClosedRange<Int>) -> Int? {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
        let value = number.doubleValue
        guard value.isFinite, value.rounded(.towardZero) == value,
              value >= Double(range.lowerBound), value <= Double(range.upperBound) else { return nil }
        return Int(value)
    }
    static func inspect(_ bytes: Data) -> Result<NG8ProbeJPEGMetadata, NG8ProbeFailure> {
        guard !bytes.isEmpty, bytes.count <= NG8ProbeLimits.jpegBytes else { return .failure(.bytesInvalid) }
        let options = [kCGImageSourceShouldCache: false, kCGImageSourceShouldCacheImmediately: false] as CFDictionary
        guard let source = CGImageSourceCreateWithData(bytes as CFData, options),
              let type = CGImageSourceGetType(source), type as String == "public.jpeg",
              CGImageSourceGetCount(source) == 1,
              CGImageSourceGetStatus(source) == .statusComplete else { return .failure(.jpegInvalid) }
        guard let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, options) as? [String: Any],
              let width = integer(properties[kCGImagePropertyPixelWidth as String], range: 1...NG8ProbeLimits.maximumAxis),
              let height = integer(properties[kCGImagePropertyPixelHeight as String], range: 1...NG8ProbeLimits.maximumAxis),
              width * height <= NG8ProbeLimits.maximumPixels else { return .failure(.metadataInvalid) }
        let orientation: Int?
        if let raw = properties[kCGImagePropertyOrientation as String] {
            guard let parsed = integer(raw, range: 1...8) else { return .failure(.metadataInvalid) }
            orientation = parsed
        } else { orientation = nil }
        // Only ImageIO container properties are inspected. No pixel decode,
        // resize, rotation, UIImage or JPEG re-encoding is performed.
        return .success(NG8ProbeJPEGMetadata(width: width, height: height, exifOrientation: orientation))
    }
    static func hash(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}

private enum NG8ServiceOldEvidence {
    // The OS-provided sandbox home may itself use /var -> /private/var. Resolve
    // only that trusted prefix; Library/Application Support/NGG2Cycles remain
    // subject to no-follow descriptor traversal at every inspection.
    static func productionURL() -> URL? {
        let home = URL(fileURLWithPath: NSHomeDirectory(), isDirectory: true).standardizedFileURL
        guard let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first,
              support.isFileURL, support.standardizedFileURL.path.hasPrefix(home.path + "/") else { return nil }
        let suffix = String(support.standardizedFileURL.path.dropFirst(home.path.count + 1))
        return home.resolvingSymlinksInPath().appendingPathComponent(suffix, isDirectory: true)
            .appendingPathComponent("NGG2Cycles", isDirectory: true)
    }
    static func inspect(_ url: URL) -> NG8ProbeOldEvidence {
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.utf8.contains(0) else { return .blocked }
        let home = URL(fileURLWithPath: NSHomeDirectory(), isDirectory: true).resolvingSymlinksInPath()
        var candidateAnchor: URL?
        if url.path.hasPrefix(home.path + "/") { candidateAnchor = home }
        #if NG8_CAPTURE_SERVICE_HOST_TEST
        let temporary = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
        if candidateAnchor == nil, url.path.hasPrefix(temporary.path + "/") { candidateAnchor = temporary }
        #endif
        guard let anchor = candidateAnchor else { return .blocked }
        let relative = String(url.path.dropFirst(anchor.path.count + 1))
        let components = relative.split(separator: "/").map(String.init)
        guard !components.isEmpty, !components.contains("."), !components.contains("..") else { return .blocked }
        // Do not enumerate/open ancestors of the sandbox. The OS-supplied
        // canonical home is the trusted FD anchor; every child is no-follow.
        var descriptor = open(anchor.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { return .blocked }
        defer { close(descriptor) }
        for component in components {
            let child = openat(descriptor, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            if child < 0 { return errno == ENOENT ? .clean : .blocked }
            close(descriptor)
            descriptor = child
        }
        var info = stat()
        guard fstat(descriptor, &info) == 0, (info.st_mode & mode_t(S_IFMT)) == mode_t(S_IFDIR) else { return .blocked }
        let duplicate = dup(descriptor)
        guard duplicate >= 0 else { return .blocked }
        guard let directory = fdopendir(duplicate) else { close(duplicate); return .blocked }
        defer { closedir(directory) }
        while true {
            errno = 0
            guard let entry = readdir(directory) else { return errno == 0 ? .clean : .blocked }
            let ignored = withUnsafePointer(to: &entry.pointee.d_name) { pointer in
                pointer.withMemoryRebound(to: CChar.self, capacity: Int(MAXNAMLEN) + 1) {
                    $0[0] == 46 && ($0[1] == 0 || ($0[1] == 46 && $0[2] == 0))
                }
            }
            if !ignored { return .blocked }
        }
    }
}

// The process owner retains this service across listener restarts/rebinds.
// The ObjC bridge is injected by UITests; no Kit -> UITest dependency exists.
final class NG8CaptureService {
    typealias Reply = (Data?, String?) -> Void
    typealias Handoff = () -> Void
    struct Bridge {
        let prepare: () -> Bool
        let request: (@escaping Reply, @escaping Handoff) -> Void
    }
    typealias Completion = (Result<[String: Any], NG8ProbeFailure>) -> Void
    let runtimeID: String
    let mode: RPCServiceMode
    private let core: NG8CaptureProbe
    private let ownerState: (String) -> NG8ProbeOwnerState
    private let rpc = DispatchQueue(label: "ng8.capture.rpc", qos: .userInitiated)
    // Access only on rpc. A cached terminal start must never replace the active
    // record, or a later Stop could cancel an old ID and miss the live capture.
    private var active: (key: NG8ProbeKey, owner: NG8ProbeOwner, generation: UInt64)?
    private var listenerActive = true

    convenience init?(mode: RPCServiceMode, bridge: Bridge,
                      ownerState: @escaping (String) -> NG8ProbeOwnerState) {
        guard mode == .iphone8CaptureOnly, RPCServiceMode.currentBuildMode == .iphone8CaptureOnly,
              let spool = NG8ServiceOldEvidence.productionURL() else { return nil }
        self.init(mode: mode, bridge: bridge, ownerState: ownerState, legacySpoolURL: spool)
    }
    private init(mode: RPCServiceMode, bridge: Bridge,
                 ownerState: @escaping (String) -> NG8ProbeOwnerState, legacySpoolURL: URL) {
        let identity = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        runtimeID = identity
        self.mode = mode
        self.ownerState = ownerState
        core = NG8CaptureProbe(qualified: true, runtimeID: identity,
            clock: NG8ServiceClock(), scheduler: NG8ServiceScheduler(), driver: NG8ServiceDriver(bridge),
            ownerState: { ownerState($0.tokenIdentity) },
            oldEvidenceGate: { NG8ServiceOldEvidence.inspect(legacySpoolURL) },
            inspectJPEG: NG8ServiceJPEG.inspect, sha256: NG8ServiceJPEG.hash)
    }
    #if NG8_CAPTURE_SERVICE_HOST_TEST
    static func hostTest(mode: RPCServiceMode, bridge: Bridge,
                         ownerState: @escaping (String) -> NG8ProbeOwnerState,
                         legacySpoolURL: URL) -> NG8CaptureService? {
        guard mode == .iphone8CaptureOnly else { return nil }
        return NG8CaptureService(mode: mode, bridge: bridge, ownerState: ownerState, legacySpoolURL: legacySpoolURL)
    }
    #endif

    func handle(method: String, params: [String: Any], ownerTokenID: String,
                completion: @escaping Completion) {
        rpc.async {
            guard NG8ProbeWire.hex(ownerTokenID, count: 8), self.ownerState(ownerTokenID) != .inactive else {
                completion(.failure(.ownerInactive)); return
            }
            let owner = NG8ProbeOwner(tokenIdentity: ownerTokenID)
            let command: NG8ProbeCommand
            switch NG8ProbeWire.decode(method: method, params: params) {
            case .failure(let reason): completion(.failure(reason)); return
            case .success(let value): command = value
            }
            let result: Result<[String: Any], NG8ProbeFailure>
            switch command {
            case .status(let key): result = self.core.status(key, owner: owner).map(Self.status)
            case .cancel(let key): result = self.core.cancel(key, owner: owner).map(Self.status)
            case .start(let key):
                guard self.listenerActive else { completion(.failure(.unavailable)); return }
                let started = self.core.start(key, owner: owner)
                if case .success(let status) = started, let generation = status.generation,
                   let state = status.state, [.accepted, .preparing, .capturing, .ready].contains(state),
                   generation >= (self.active?.generation ?? 0) {
                    self.active = (key, owner, generation)
                }
                result = started.map(Self.status)
            case .manifest(let key): result = self.core.manifest(key, owner: owner).map(Self.manifest)
            case .chunk(let key, let hash, let offset, let limit):
                result = self.core.chunk(key, owner: owner, sha256: hash, offset: offset, limit: limit).map(Self.chunk)
            }
            // This queue is separate from AX/metadata/hash and the watchdog.
            // No raw exception text, paths or owner identity is serialized.
            completion(result.flatMap { value in
                let maximum: Int
                if case .chunk = command { maximum = NG8ProbeLimits.chunkWireBytes }
                else { maximum = NG8ProbeLimits.manifestBytes }
                guard JSONSerialization.isValidJSONObject(value),
                      let encoded = try? JSONSerialization.data(withJSONObject: value),
                      encoded.count <= maximum else { return .failure(.metadataInvalid) }
                return .success(value)
            })
        }
    }
    // Must be called after AuthManager's mutation and after its lock is released.
    // Do not put this fence behind pending RPC work or use it for a LAN rebind.
    func ownerChanged() { core.ownerChanged() }
    private func cancelActiveOnQueue() {
        if let active = active { _ = core.cancel(active.key, owner: active.owner) }
    }
    func cancelActive(completion: (() -> Void)? = nil) {
        rpc.async { self.cancelActiveOnQueue(); completion?() }
    }
    func setListenerActive(_ active: Bool, completion: (() -> Void)? = nil) {
        rpc.async {
            self.listenerActive = active
            if !active { self.cancelActiveOnQueue() }
            completion?()
        }
    }
    private static func optional<T>(_ value: T?) -> Any { value.map { $0 as Any } ?? NSNull() }
    private static func status(_ value: NG8ProbeStatus) -> [String: Any] {
        ["schema": NG8ProbeLimits.schema, "service_mode": NG8ProbeLimits.serviceMode,
         "runtime_id": value.runtimeID, "old_evidence_gate": value.oldEvidenceGate.rawValue,
         "probe_id": optional(value.probeID), "generation": optional(value.generation),
         "cancel_epoch": optional(value.cancelEpoch), "state": optional(value.state?.rawValue),
         "failure_code": optional(value.failure?.rawValue), "clock_id": value.clockID,
         "accepted_ns": optional(value.acceptedNs), "deadline_ns": optional(value.deadlineNs),
         "request_start_ns": optional(value.requestStartNs), "callback_body_handoff_ns": optional(value.callbackEndNs),
         "callback_return_verified": false, "ready_expiry_ns": optional(value.readyExpiryNs),
         "draining": value.draining, "lease_held": value.leaseHeld]
    }
    private static func manifest(_ value: NG8ProbeManifest) -> [String: Any] {
        ["schema": NG8ProbeLimits.schema, "service_mode": NG8ProbeLimits.serviceMode,
         "runtime_id": value.key.runtimeID, "probe_id": value.key.probeID, "generation": value.generation,
         "clock_id": value.clockID, "source_api": value.sourceAPI, "requested_uti": value.requestedUTI,
         "requested_quality": value.requestedQuality, "format": value.format, "byte_length": value.byteLength,
         "sha256": value.sha256, "source_width": value.metadata.width, "source_height": value.metadata.height,
         "exif_orientation": optional(value.metadata.exifOrientation), "accepted_ns": value.acceptedNs,
         "deadline_ns": value.deadlineNs, "request_start_ns": value.requestStartNs,
         "callback_body_handoff_ns": value.callbackEndNs, "callback_return_verified": false,
         "ready_expiry_ns": value.readyExpiryNs, "input_authorized": false, "input_geometry_verified": false,
         "normalization_applied": false, "device_capture_ns": NSNull(), "freshness_verified": false, "scope": value.scope]
    }
    private static func chunk(_ value: NG8ProbeChunk) -> [String: Any] {
        ["schema": NG8ProbeLimits.schema, "service_mode": NG8ProbeLimits.serviceMode,
         "runtime_id": value.key.runtimeID, "probe_id": value.key.probeID, "generation": value.generation,
         "sha256": value.sha256, "offset": value.offset, "byte_length": value.byteLength,
         "chunk_bytes": value.data.count, "data_base64": value.data.base64EncodedString()]
    }
}
