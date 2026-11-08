import Foundation
import CoreGraphics
import ImageIO

private extension NSLock {
    func fixtureLocked<T>(_ body: () -> T) -> T { lock(); defer { unlock() }; return body() }
}
// This fixture-only hook type lets the exact old Runtime compile unchanged:
// its producer has no call sites, while new HOST_TEST Runtime can expose the
// committed C boundary without adding release symbols or a production clock.
enum NG2RuntimeObserveTestHooks {
    static var beforeObserve: (() -> Void)?
    static var afterObserve: (() -> Void)?
}
enum NG2RuntimeExportTestHooks {
    static var beforeExportEncode: (() -> Void)?
    static var afterExportEncode: (() -> Void)?
    static var beforeExportReply: (() -> Void)?
    static var transformExportPNG: ((Data, UInt64) -> Data)?
}
enum NG2Fake {
    enum Mode { case empty, pause, hold, walk, reply }
    static let lock = NSLock()
    static var mode = Mode.empty
    static var requests = 0
    static var activations = 0
    static var touches = 0
    static var failTouch = false
    static var authenticatedOwnerActive = true
    static var frontPID: pid_t = 42
    static var beforeForegroundQuery: (() -> Void)?
    static var gesturePaths: [[[(point: CGPoint, t: Double)]]] = []
    static var tapPoints: [CGPoint] = []
    static var walkX: Int32 = 0
    static var walkY: Int32 = 0
    static var walkMoves = 0
    static var walkCapturesAfterMove = 0
    static var walkObservationAfter: UInt64 = 0
    static var walkGoodsEnabled = true
    static var walkPixelInset: Int32 = 0
    static var walkPaused = false
    static var phaseBase: UInt64 = 0
    static var remoteVariant: Int32 = 0
    static var remoteVariantDuringWalk = false
    static var heldTickets: [UInt64: () -> Void] = [:]
    static var returnedTickets = Set<UInt64>()
    static var unknownFrames = 0
    static var boundaryClockChange: (() -> Void)?
    static var captureDrainedRuns = Set<String>()
    static var captureLimit: Int?
    static var firstUnknownID: UInt64 = 0
    static var subtileResolvedWait = false
    static var callbacks: [(Data?, String?) -> Void] = []
    static var offset: UInt64 = 0
    // TEST051's continuing multi-beat fixture uses explicit logical capture
    // boundaries. PNG painting/encoding CPU time must not move its synthetic
    // HUD behind the timestamps supplied to the real C beat model.
    static var fixedClock: UInt64?
    static var pending = 0
    static var replyData: Data?
    static var replyError: String?
    static var captureTimeProvider: (() -> UInt64)?
    static var observeClock: UInt64 = 10
    static var observeEntries: [UInt64] = []
    static var observeExits: [UInt64] = []
    static func reset(_ next: Mode) {
        lock.fixtureLocked { mode = next; requests = 0; activations = 0; touches = 0; failTouch = false; authenticatedOwnerActive = true; frontPID = 42; callbacks = []; offset = 0; fixedClock = nil; pending = 0 }
        lock.fixtureLocked {
            replyData = nil; replyError = nil
            captureTimeProvider = nil
            observeClock = 10; observeEntries = []; observeExits = []
            beforeForegroundQuery = nil
            gesturePaths = []; tapPoints = []; walkX = 0; walkY = 0
            walkMoves = 0; walkCapturesAfterMove = 0; walkObservationAfter = 0; walkPaused = false
            walkGoodsEnabled = true; walkPixelInset = 0; captureLimit = nil; firstUnknownID = 0; subtileResolvedWait = false
            remoteVariant = 0; heldTickets = [:]; returnedTickets = []; unknownFrames = 0
            remoteVariantDuringWalk = false
            boundaryClockChange = nil
            captureDrainedRuns = []
            phaseBase = DispatchTime.now().uptimeNanoseconds
        }
        RemoteSession.shared.paused = false
        NG2RuntimeTestHooks.beforeCaptureAdmission = nil
        NG2RuntimeTestHooks.beforeMainAdmission = nil
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        NG2RuntimeTestHooks.beforeAnalysisCommit = nil
        NG2RuntimeTestHooks.afterForegroundQuery = nil
        NG2RuntimeTestHooks.beforeControlTick = nil
        NG2RuntimeTestHooks.scheduleTicket = nil
        NG2RuntimeTestHooks.afterTicketReturned = nil
        NG2RuntimeTestHooks.afterCaptureDrainProcessed = nil
        NG2RuntimeTestHooks.beforeCaptureFailureCommit = nil
        NG2RuntimeTestHooks.analysisRGBA = nil
        NG2RuntimeTestHooks.afterWatchdogCheck = nil
        LockStateMonitor.monitor.isLocked = false
        NG2RuntimeTestHooks.clock = nil
        NG2RuntimeObserveTestHooks.beforeObserve = nil
        NG2RuntimeObserveTestHooks.afterObserve = nil
        NG2RuntimeExportTestHooks.beforeExportEncode = nil
        NG2RuntimeExportTestHooks.afterExportEncode = nil
        NG2RuntimeExportTestHooks.beforeExportReply = nil
        NG2RuntimeExportTestHooks.transformExportPNG = nil
    }
    // Separate analysis, gate and actual C-entry/return phases by construction.
    // The expected start comes from the boundary hook, never a reported field.
    static func observeFixtureNow() -> UInt64 {
        lock.fixtureLocked {
            if observeClock < 50 { observeClock += 1 }
            return 1_000_000_000 + observeClock
        }
    }
    static func setObserveGateClock() { lock.fixtureLocked { observeClock = 100 } }
    static func enterObserveBoundary() {
        lock.fixtureLocked { observeClock = 200; observeEntries.append(1_000_000_000 + observeClock) }
    }
    static func leaveObserveBoundary() {
        lock.fixtureLocked { observeClock = 300; observeExits.append(1_000_000_000 + observeClock) }
    }
    static func observeBoundaries() -> ([UInt64], [UInt64]) { lock.fixtureLocked { (observeEntries, observeExits) } }
    static func countRequests() -> Int { lock.fixtureLocked { requests } }
    static func countTouches() -> Int { lock.fixtureLocked { touches } }
    static func countActivations() -> Int { lock.fixtureLocked { activations } }
    static func release() {
        let pending = lock.fixtureLocked { () -> [(Data?, String?) -> Void] in let old = callbacks; callbacks = []; return old }
        for callback in pending { callback(nil, "fixture release") }
    }
    static func paths() -> [[[(point: CGPoint, t: Double)]]] { lock.fixtureLocked { gesturePaths } }
    static func taps() -> [CGPoint] { lock.fixtureLocked { tapPoints } }
    static func holdTicket(_ id: UInt64, _ callback: @escaping () -> Void) {
        lock.fixtureLocked { heldTickets[id] = callback }
    }
    static func releaseTicket(_ id: UInt64) {
        let callback = lock.fixtureLocked { heldTickets.removeValue(forKey: id) }
        callback?()
    }
    // The production capture loop invokes beforeCaptureAdmission only after
    // the preceding raw callback, decode and publication have completed.
    // Clock jumps used by these fixtures must occur at that exact boundary.
    static func changeClockAtCaptureBoundary(_ change: @escaping () -> Void) -> Bool {
        let finished = DispatchSemaphore(value: 0)
        lock.fixtureLocked {
            precondition(boundaryClockChange == nil)
            boundaryClockChange = { change(); finished.signal() }
        }
        return finished.wait(timeout: .now()+2) == .success
    }
    static func performBoundaryClockChange() {
        let change = lock.fixtureLocked { () -> (() -> Void)? in
            let old = boundaryClockChange; boundaryClockChange = nil; return old
        }
        change?()
    }
    static func waitForCapturePermit() {
        while lock.fixtureLocked({ captureLimit.map { requests >= $0 } ?? false }) {
            Thread.sleep(forTimeInterval: 0.001)
        }
    }
    static func walkedPNG(capturedAt time: UInt64) -> Data {
        let unknown = lock.fixtureLocked { () -> Bool in
            if unknownFrames == 0 { return false }; unknownFrames -= 1; return true
        }
        if unknown { return unknownPNG }
        let state = lock.fixtureLocked { () -> (Int32, Int32, Int32, Bool, UInt64) in
            if walkMoves > 0 { walkCapturesAfterMove += 1 }
            // This known world reveals goods at the first real C ticket's
            // target+80ms, before its next beat. Eligibility uses this fake
            // request's entry clock, not the later PNG painting clock. A frame
            // count alone could beat the motion observation horizon.
            let goods = walkGoodsEnabled && walkMoves > 0 && walkObservationAfter > 0 && time >= walkObservationAfter
            return (36*walkX, 36*walkY + (walkMoves > 0 ? walkPixelInset : 0), goods ? 1 : 0, walkPaused, phaseBase)
        }
        if state.3 { return pausePNG }
        let period: UInt64 = 520_000_000
        let elapsed = time >= state.4 ? time-state.4 : 0
        let fraction = Double(period-1-(elapsed % period))/Double(period)
        var rgba = Data(count: 896*414*4)
        let count = rgba.count
        let valid = rgba.withUnsafeMutableBytes {
            ng2_fixture_floor_pixels_rgba($0.bindMemory(to: UInt8.self).baseAddress, count, state.0, state.1, fraction, state.2)
        }
        precondition(valid == 1)
        let remote = lock.fixtureLocked { (remoteVariant, remoteVariantDuringWalk) }
        if (state.0 == 0 && state.1 == 0) || remote.1 {
            let changed = rgba.withUnsafeMutableBytes {
                ng2_fixture_remote_cell($0.bindMemory(to: UInt8.self).baseAddress, count, remote.0)
            }
            precondition(changed == 1)
        }
        return NG2Raster.png(rgba)!
    }
    static func virtualClock() -> UInt64 {
        lock.fixtureLocked { fixedClock ?? (DispatchTime.now().uptimeNanoseconds + offset) }
    }
    static func advance(_ ns: UInt64) {
        lock.fixtureLocked {
            if let value = fixedClock { fixedClock = value + ns } else { offset += ns }
        }
    }
    static func useFixedCaptureClock() { lock.fixtureLocked { fixedClock = phaseBase + 1_000 } }
    static let pausePNG: Data = {
        var bytes = Data(count: 896*414*4)
        let count = bytes.count
        bytes.withUnsafeMutableBytes { ng2_test_pause($0.bindMemory(to: UInt8.self).baseAddress, count) }
        return NG2Raster.png(bytes)!
    }()
    static let unknownPNG = NG2Raster.png(Data(count: 896*414*4))!
    static let squarePNG: Data = {
        let bytes = Data(repeating: 0, count: 16)
        let provider = CGDataProvider(data: bytes as CFData)!
        let source = CGImage(width: 2, height: 2, bitsPerComponent: 8, bitsPerPixel: 32,
            bytesPerRow: 8, space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
                CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
            decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
        let output = NSMutableData()
        let destination = CGImageDestinationCreateWithData(output, "public.png" as CFString, 1, nil)!
        CGImageDestinationAddImage(destination, source, nil)
        precondition(CGImageDestinationFinalize(destination))
        return output as Data
    }()
    static let portraitTIFF: Data = {
        let bytes = Data(repeating: 0, count: 414*896*4)
        let provider = CGDataProvider(data: bytes as CFData)!
        let source = CGImage(width: 414, height: 896, bitsPerComponent: 8, bitsPerPixel: 32,
            bytesPerRow: 414*4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
                CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
            decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
        let output = NSMutableData()
        let destination = CGImageDestinationCreateWithData(output, "public.tiff" as CFString, 1, nil)!
        CGImageDestinationAddImage(destination, source, [kCGImagePropertyOrientation: 8] as CFDictionary)
        precondition(CGImageDestinationFinalize(destination))
        return output as Data
    }()
}
final class RemoteSession {
    static let shared = RemoteSession()
    private let lock = NSLock()
    private var value = false
    var paused: Bool { get { lock.fixtureLocked { value } } set { lock.fixtureLocked { value = newValue } } }
}
final class AuthManager {
    static let shared = AuthManager()
    func clientName(forTokenId owner: String) -> String? {
        NG2Fake.lock.fixtureLocked { owner == "fixture-owner" && NG2Fake.authenticatedOwnerActive ? "Fixture" : nil }
    }
}
final class LockStateMonitor {
    static let monitor = LockStateMonitor()
    static func shared() -> LockStateMonitor { monitor }
    var isLocked = false
}
enum ForegroundApp {
    static func openBundleID(_ id: String) -> Bool { NG2Fake.lock.fixtureLocked { NG2Fake.activations += 1 }; return true }
    static func processID(forBundleID id: String) -> pid_t { 42 }
    static func frontmostPID() -> pid_t {
        let hook = NG2Fake.lock.fixtureLocked { NG2Fake.beforeForegroundQuery }
        hook?()
        return NG2Fake.lock.fixtureLocked { NG2Fake.frontPID }
    }
}
final class XCUIApplication { init(bundleIdentifier: String) {} }
enum ObjCException { static func catching(_ body: () -> Void) -> String? { body(); return nil } }
final class FastActionHandler {
    init(app: XCUIApplication) {}
    private func touch() -> ([String: JSONValue]?, JSONRPCError?) {
        let failed = NG2Fake.lock.fixtureLocked { () -> Bool in NG2Fake.touches += 1; return NG2Fake.failTouch }
        return failed ? (nil, .serverError("fixture started synth failure")) : (["message": .string("fixture ACK")], nil)
    }
    func fastTap(x: Double, y: Double) -> ([String: JSONValue]?, JSONRPCError?) {
        NG2Fake.lock.fixtureLocked {
            NG2Fake.tapPoints.append(CGPoint(x: x, y: y))
            if NG2Fake.mode == .walk && x == 390 && y == 448 { NG2Fake.walkPaused = true }
        }
        return touch()
    }
    func fastGesture(_ fingers: [[(point: CGPoint, t: Double)]]) -> ([String: JSONValue]?, JSONRPCError?) {
        NG2Fake.lock.fixtureLocked {
            NG2Fake.gesturePaths.append(fingers)
            if NG2Fake.mode == .walk, let point = fingers.first?.first?.point {
                if point.x == 290 && point.y == 838 { NG2Fake.walkY -= 1 }
                else if point.x == 124 && point.y == 838 { NG2Fake.walkY += 1 }
                else if point.x == 207 && point.y == 49 { NG2Fake.walkX -= 1 }
                else if point.x == 207 && point.y == 838 { NG2Fake.walkX += 1 }
                NG2Fake.walkMoves += 1
            }
        }
        return touch()
    }
}
enum NG2CaptureBridge {
    static var pendingRequests: UInt { NG2Fake.lock.fixtureLocked { UInt(NG2Fake.pending) } }
    static func prepare() -> Bool { Thread.isMainThread }
    static func requestJPEG(_ reply: @escaping (Data?, String?) -> Void) {
        let timeProvider = NG2Fake.lock.fixtureLocked { NG2Fake.captureTimeProvider }
        let capturedAt = timeProvider?() ?? NG2Fake.virtualClock()
        let fixedCapture = NG2Fake.lock.fixtureLocked { NG2Fake.fixedClock != nil }
        let mode = NG2Fake.lock.fixtureLocked { () -> NG2Fake.Mode in
            NG2Fake.requests += 1; NG2Fake.pending += 1
            if NG2Fake.mode == .hold {
                NG2Fake.callbacks.append { data, error in
                    NG2Fake.lock.fixtureLocked { NG2Fake.pending -= 1 }
                    reply(data, error)
                }
            }
            return NG2Fake.mode
        }
        if mode == .hold { return }
        DispatchQueue.global().asyncAfter(deadline: .now()+0.005) {
            NG2Fake.lock.fixtureLocked { NG2Fake.pending -= 1 }
            if mode == .reply {
                let value = NG2Fake.lock.fixtureLocked { (NG2Fake.replyData, NG2Fake.replyError) }
                reply(value.0, value.1); return
            }
            let data: Data? = mode == .walk ? NG2Fake.walkedPNG(capturedAt: capturedAt + (fixedCapture ? 1_000_000 : 0)) : (mode == .pause ? NG2Fake.pausePNG : nil)
            if fixedCapture { NG2Fake.advance(2_000_000) }
            reply(data, "fixture capture")
        }
    }
}
