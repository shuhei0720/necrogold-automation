import Foundation
import Dispatch
import ImageIO
import CryptoKit

// Adapter TDD baseline. No bridge/queue/filesystem/capture operation is called.
// Root owns the process lifetime and supplies the UITest-only ObjC closures;
// this file must also compile without any ObjC bridge symbol in scope.
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
    private let bridge: Bridge
    private let ownerState: (String) -> NG8ProbeOwnerState
    private let legacySpoolURL: URL

    // No caller string/JSON can construct production qualification.
    convenience init?(mode: RPCServiceMode, bridge: Bridge,
                      ownerState: @escaping (String) -> NG8ProbeOwnerState) {
        guard mode == .iphone8CaptureOnly, RPCServiceMode.currentBuildMode == .iphone8CaptureOnly,
              let support = FileManager.default.urls(for: .applicationSupportDirectory,
                                                    in: .userDomainMask).first else { return nil }
        self.init(mode: mode, bridge: bridge, ownerState: ownerState,
                  legacySpoolURL: support.appendingPathComponent("NGG2Cycles", isDirectory: true))
    }

    private init(mode: RPCServiceMode, bridge: Bridge,
                 ownerState: @escaping (String) -> NG8ProbeOwnerState, legacySpoolURL: URL) {
        self.runtimeID = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        self.mode = mode
        self.bridge = bridge
        self.ownerState = ownerState
        self.legacySpoolURL = legacySpoolURL
    }

    #if NG8_CAPTURE_SERVICE_HOST_TEST
    // This factory is absent from production compiler inputs. Synthetic host
    // tests inject an isolated old-spool path; no device qualification claim.
    static func hostTest(mode: RPCServiceMode, bridge: Bridge,
                         ownerState: @escaping (String) -> NG8ProbeOwnerState,
                         legacySpoolURL: URL) -> NG8CaptureService? {
        guard mode == .iphone8CaptureOnly else { return nil }
        return NG8CaptureService(mode: mode, bridge: bridge, ownerState: ownerState,
                                 legacySpoolURL: legacySpoolURL)
    }
    #endif

    func handle(method: String, params: [String: Any], ownerTokenID: String,
                completion: @escaping Completion) {
        completion(.failure(.notAvailable))
    }

    func ownerChanged() {}
    func cancelActive(completion: (() -> Void)? = nil) { completion?() }
    func setListenerActive(_ active: Bool, completion: (() -> Void)? = nil) { completion?() }
}
