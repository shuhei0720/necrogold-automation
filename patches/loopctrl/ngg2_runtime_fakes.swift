import Foundation
import CoreGraphics

private extension NSLock {
    func fixtureLocked<T>(_ body: () -> T) -> T { lock(); defer { unlock() }; return body() }
}
enum NG2Fake {
    enum Mode { case empty, pause, hold }
    static let lock = NSLock()
    static var mode = Mode.empty
    static var requests = 0
    static var activations = 0
    static var touches = 0
    static var failTouch = false
    static var frontPID: pid_t = 42
    static var callbacks: [(Data?, String?) -> Void] = []
    static var offset: UInt64 = 0
    static var pending = 0
    static func reset(_ next: Mode) {
        lock.fixtureLocked { mode = next; requests = 0; activations = 0; touches = 0; failTouch = false; frontPID = 42; callbacks = []; offset = 0; pending = 0 }
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
    static func frontmostPID() -> pid_t { NG2Fake.lock.fixtureLocked { NG2Fake.frontPID } }
}
final class XCUIApplication { init(bundleIdentifier: String) {} }
enum ObjCException { static func catching(_ body: () -> Void) -> String? { body(); return nil } }
final class FastActionHandler {
    init(app: XCUIApplication) {}
    private func touch() -> ([String: JSONValue]?, JSONRPCError?) {
        let failed = NG2Fake.lock.fixtureLocked { () -> Bool in NG2Fake.touches += 1; return NG2Fake.failTouch }
        return failed ? (nil, .serverError("fixture started synth failure")) : (["message": .string("fixture ACK")], nil)
    }
    func fastTap(x: Double, y: Double) -> ([String: JSONValue]?, JSONRPCError?) { touch() }
    func fastGesture(_ fingers: [[(point: CGPoint, t: Double)]]) -> ([String: JSONValue]?, JSONRPCError?) { touch() }
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
            reply(mode == .pause ? NG2Fake.pausePNG : nil, "fixture capture")
        }
    }
}
