import Foundation
#if canImport(Darwin)
import Darwin
#endif

// Pure qualification and policy. Actual Kit/UI-test callsites are connected
// only by the separate overlay; this file never starts a producer or listener.
enum RPCServiceMode: String, Equatable {
    case normal
    case iphone8CaptureOnly = "iphone8-capture-only-v1"

    #if NG8_CAPTURE_PROBE_BUILD
    static let compiledOptIn = true
    #else
    static let compiledOptIn = false
    #endif

    static let currentBuildMode = select(buildOptIn: compiledOptIn,
        readHardwareIdentifier: NG8HardwareIdentifier.read)

    static func select(buildOptIn: Bool,
                       readHardwareIdentifier: () -> String?) -> RPCServiceMode {
        guard buildOptIn else { return .normal }
        return readHardwareIdentifier() == "iPhone10,1" ? .iphone8CaptureOnly : .normal
    }
}

enum NG8HardwareIdentifier {
    static func read() -> String? {
        #if os(iOS) && canImport(Darwin)
        var count = 0
        guard sysctlbyname("hw.machine", nil, &count, nil, 0) == 0,
              count > 1, count <= 256 else { return nil }
        var bytes = [UInt8](repeating: 0, count: count)
        let capacity = bytes.count
        let result = bytes.withUnsafeMutableBytes {
            sysctlbyname("hw.machine", $0.baseAddress, &count, nil, 0)
        }
        guard result == 0, count > 1, count <= capacity, bytes[count - 1] == 0,
              !bytes.prefix(count - 1).contains(0) else { return nil }
        return String(bytes: bytes.prefix(count - 1), encoding: .utf8)
        #else
        return nil
        #endif
    }
}

// Deliberately not Codable or representable by a caller string. The actual
// authenticated HTTP or trusted in-process callsite must supply this value.
enum NG8RequestOrigin: Equatable {
    case publicHTTP
    case authenticatedRemote(tokenID: String)
    case trustedInProcess
}

// Only untrusted caller fields enter the pure policy. Server-injected actor,
// peer and origin information must remain outside this dictionary.
enum NG8PolicyValue: Equatable {
    case string(String)
    case bool(Bool)
    case integer(Int)
    case null
    case unsupported
}

enum NG8LocalOperation: Equatable {
    case setPaused(Bool)
    case stop
    case restart
    case setPort(Int)
    case setRemoteAccess(Bool)
    case setNearby(Bool)
}

enum NG8PolicyOperation: Equatable {
    case http(verb: String, path: String)
    case rpc(method: String, callerParams: [String: NG8PolicyValue])
    case local(NG8LocalOperation)
}

enum NG8AllowedRoute: Equatable {
    case publicMetadata
    case encryptedRPC
    case probe
    case remoteConfigRead
    case trustedLocalConfigRead
    case logs
    case trustedLocalAuthAdmin
    case trustedLocalListenerAdmin
}

enum NG8PolicyRejection: String, Equatable {
    case notAvailable = "not_available"
    case invalidRequest = "invalid_request"
    case authenticationRequired = "authentication_required"
    case trustedLocalRequired = "trusted_local_required"
    case pairingDisabledInCaptureOnly = "pairing_disabled_in_capture_only"
}

enum NG8RouteDecision: Equatable {
    case normalDispatch
    case allow(NG8AllowedRoute)
    case reject(NG8PolicyRejection)
    case rejectHTTP(status: Int, code: NG8PolicyRejection)
}

struct NG8AdvertisedSurface: Equatable {
    let serviceMode: String?
    let capabilities: [String]
    let methodNames: [String]

    static let probeMethodNames = ["necro_capture_probe_status", "necro_capture_probe_start",
                                  "necro_capture_probe_cancel", "necro_capture_probe_results"]

    static func project(mode: RPCServiceMode, normalCapabilities: [String],
                        normalMethodNames: [String]) -> NG8AdvertisedSurface {
        if mode == .iphone8CaptureOnly {
            return NG8AdvertisedSurface(serviceMode: mode.rawValue,
                capabilities: ["envelope_v1", "necrogold_capture_probe_v1"],
                methodNames: ["config", "logs", "recent_logs"] + probeMethodNames)
        }
        return NG8AdvertisedSurface(serviceMode: nil,
            capabilities: normalCapabilities, methodNames: normalMethodNames)
    }
}

// These identify integration sites, not five distinct coordinator lifetimes.
// The actual constructor calls remain unmodified until the later overlay step.
enum NG8ServerConstructionSite: String, CaseIterable {
    case initialStart
    case urlPortChange
    case configPortChange
    case enableRemoteAccess
    case disableRemoteAccess
}

struct NG8ServerBinding<Coordinator: AnyObject> {
    let mode: RPCServiceMode
    let processCoordinator: Coordinator
}

enum NG8CaptureRoutePolicy {
    static func decide(mode: RPCServiceMode, origin: NG8RequestOrigin,
                       operation: NG8PolicyOperation) -> NG8RouteDecision {
        guard mode == .iphone8CaptureOnly else { return .normalDispatch }
        switch operation {
        case .http(let verb, let path):
            if verb == "POST", path == "/pair" {
                return .rejectHTTP(status: 403, code: .pairingDisabledInCaptureOnly)
            }
            if verb == "GET", path == "/schema" || path == "/whoami" {
                return .allow(.publicMetadata)
            }
            if verb == "POST", path == "/rpc" { return .allow(.encryptedRPC) }
            return .reject(.notAvailable)
        case .rpc(let method, let params):
            if NG8AdvertisedSurface.probeMethodNames.contains(method) {
                // This grants entry to the core's closed command parser only.
                // The authenticated adapter and core still validate the owner,
                // params, pause, runtime, generation and capture admission.
                return authenticated(origin) ? .allow(.probe) : .reject(.authenticationRequired)
            }
            if method == "config" { return config(origin: origin, params: params) }
            if method == "logs" || method == "recent_logs" {
                guard authenticated(origin) || origin == .trustedInProcess else {
                    return .reject(.authenticationRequired)
                }
                guard logParamsValid(params) else { return .reject(.invalidRequest) }
                return .allow(.logs)
            }
            return .reject(.notAvailable)
        case .local(let operation):
            guard origin == .trustedInProcess else { return .reject(.trustedLocalRequired) }
            switch operation {
            case .setPaused: return .allow(.trustedLocalAuthAdmin)
            case .setPort(let port):
                return validPort(port) ? .allow(.trustedLocalListenerAdmin) : .reject(.invalidRequest)
            case .stop, .restart, .setRemoteAccess, .setNearby:
                return .allow(.trustedLocalListenerAdmin)
            }
        }
    }

    static func bind<Coordinator: AnyObject>(mode: RPCServiceMode,
        site: NG8ServerConstructionSite, processCoordinator: Coordinator)
        -> NG8ServerBinding<Coordinator>? {
        guard mode == .iphone8CaptureOnly else { return nil }
        _ = site
        return NG8ServerBinding(mode: mode, processCoordinator: processCoordinator)
    }

    private static func authenticated(_ origin: NG8RequestOrigin) -> Bool {
        guard case .authenticatedRemote(let tokenID) = origin else { return false }
        return tokenID.utf8.count == 8 && tokenID.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    private static func config(origin: NG8RequestOrigin,
                               params: [String: NG8PolicyValue]) -> NG8RouteDecision {
        if authenticated(origin) {
            return params.isEmpty ? .allow(.remoteConfigRead) : .reject(.invalidRequest)
        }
        guard origin == .trustedInProcess else { return .reject(.authenticationRequired) }
        if params.isEmpty { return .allow(.trustedLocalConfigRead) }
        guard params.count == 1, let (key, value) = params.first else { return .reject(.invalidRequest) }
        switch (key, value) {
        case ("revoke_session_id", .string(let tokenID)):
            return authenticated(.authenticatedRemote(tokenID: tokenID))
                ? .allow(.trustedLocalAuthAdmin) : .reject(.invalidRequest)
        case ("clear_sessions", .bool(true)):
            return .allow(.trustedLocalAuthAdmin)
        case ("listen_port", .integer(let port)):
            return validPort(port) ? .allow(.trustedLocalListenerAdmin) : .reject(.invalidRequest)
        case ("stop_server", .bool(true)), ("allow_remote_access", .bool), ("nearby_discovery", .bool):
            return .allow(.trustedLocalListenerAdmin)
        default:
            return .reject(.invalidRequest)
        }
    }

    private static func validPort(_ value: Int) -> Bool {
        // The real listener adapter additionally enforces ServerPort.allowed.
        (1...65535).contains(value)
    }

    private static func logParamsValid(_ params: [String: NG8PolicyValue]) -> Bool {
        guard Set(params.keys).isSubset(of: ["text", "max_elements"]) else { return false }
        if let text = params["text"] {
            guard case .string = text else { return false }
        }
        if let count = params["max_elements"] {
            guard case .integer(let value) = count, (1...500).contains(value) else { return false }
        }
        return true
    }
}
