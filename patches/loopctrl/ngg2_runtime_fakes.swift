import Foundation
import CoreGraphics

private extension NSLock {
    func fixtureLocked<T>(_ body: () -> T) -> T { lock(); defer { unlock() }; return body() }
}
enum NG2Fake {
    enum Mode { case empty, pause, hold, walk }
    static let lock = NSLock()
    static var mode = Mode.empty
    static var requests = 0
    static var activations = 0
    static var touches = 0
    static var failTouch = false
    static var frontPID: pid_t = 42
    static var beforeForegroundQuery: (() -> Void)?
    static var gesturePaths: [[[(point: CGPoint, t: Double)]]] = []
    static var tapPoints: [CGPoint] = []
    static var walkX: Int32 = 0
    static var walkY: Int32 = 0
    static var walkMoves = 0
    static var walkCapturesAfterMove = 0
    static var walkPaused = false
    static var phaseBase: UInt64 = 0
    static var callbacks: [(Data?, String?) -> Void] = []
    static var offset: UInt64 = 0
    static var pending = 0
    static func reset(_ next: Mode) {
        lock.fixtureLocked { mode = next; requests = 0; activations = 0; touches = 0; failTouch = false; frontPID = 42; callbacks = []; offset = 0; pending = 0 }
        lock.fixtureLocked {
            beforeForegroundQuery = nil
            gesturePaths = []; tapPoints = []; walkX = 0; walkY = 0
            walkMoves = 0; walkCapturesAfterMove = 0; walkPaused = false
            phaseBase = DispatchTime.now().uptimeNanoseconds
        }
        RemoteSession.shared.paused = false
        NG2RuntimeTestHooks.beforeCaptureAdmission = nil
        NG2RuntimeTestHooks.beforeMainAdmission = nil
        NG2RuntimeTestHooks.beforeMainAuthority = nil
        NG2RuntimeTestHooks.beforeAnalysisCommit = nil
        LockStateMonitor.monitor.isLocked = false
        NG2RuntimeTestHooks.clock = nil
    }
    static func countRequests() -> Int { lock.fixtureLocked { requests } }
    static func countTouches() -> Int { lock.fixtureLocked { touches } }
    static func countActivations() -> Int { lock.fixtureLocked { activations } }
    static func release() {
        let pending = lock.fixtureLocked { () -> [(Data?, String?) -> Void] in let old = callbacks; callbacks = []; return old }
        for callback in pending { callback(nil, "fixture release") }
    }
    static func paths() -> [[[(point: CGPoint, t: Double)]]] { lock.fixtureLocked { gesturePaths } }
    static func taps() -> [CGPoint] { lock.fixtureLocked { tapPoints } }
    static func walkedPNG() -> Data {
        let state = lock.fixtureLocked { () -> (Int32, Int32, Int32, Bool, UInt64) in
            if walkMoves > 0 { walkCapturesAfterMove += 1 }
            return (walkX, walkY, walkCapturesAfterMove >= 3 ? 1 : 0, walkPaused, phaseBase)
        }
        if state.3 { return pausePNG }
        let period: UInt64 = 520_000_000
        let time = virtualClock()
        let elapsed = time >= state.4 ? time-state.4 : 0
        let fraction = Double(period-1-(elapsed % period))/Double(period)
        var rgba = Data(count: 896*414*4)
        let count = rgba.count
        let valid = rgba.withUnsafeMutableBytes {
            ng2_fixture_floor_rgba($0.bindMemory(to: UInt8.self).baseAddress, count, state.0, state.1, fraction, state.2)
        }
        precondition(valid == 1)
        return NG2Raster.png(rgba)!
    }
    static func virtualClock() -> UInt64 { lock.fixtureLocked { DispatchTime.now().uptimeNanoseconds + offset } }
    static func advance(_ ns: UInt64) { lock.fixtureLocked { offset += ns } }
    static let pausePNG: Data = {
        var bytes = Data(count: 896*414*4)
        let count = bytes.count
        bytes.withUnsafeMutableBytes { ng2_test_pause($0.bindMemory(to: UInt8.self).baseAddress, count) }
        return NG2Raster.png(bytes)!
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
    func clientName(forTokenId owner: String) -> String? { owner == "fixture-owner" ? "Fixture" : nil }
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
            let data: Data? = mode == .walk ? NG2Fake.walkedPNG() : (mode == .pause ? NG2Fake.pausePNG : nil)
            reply(data, "fixture capture")
        }
    }
}
