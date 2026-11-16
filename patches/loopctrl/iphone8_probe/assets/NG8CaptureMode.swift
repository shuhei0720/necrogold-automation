import Foundation

// Initial TDD stub. No existing Kit/UI-test source calls these declarations.
// Keep qualification and policy unimplemented until the named assertion Red
// has been observed with the real macOS compiler.
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
        // Intentionally does not call the reader, including in normal builds.
        // Green will require exact raw iPhone10,1 qualification, not UIDevice's
        // family name or NearbyIdentity's marketing-name fallback.
        _ = buildOptIn
        _ = readHardwareIdentifier
        return .normal
    }
}

enum NG8HardwareIdentifier {
    static func read() -> String? {
        // Stub: the eventual Darwin hw.machine reader belongs here, with no
        // UIKit/XCTest/ObjC dependency. nil is not device qualification.
        nil
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

    static func project(mode: RPCServiceMode, normalCapabilities: [String],
                        normalMethodNames: [String]) -> NG8AdvertisedSurface {
        _ = mode
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
        _ = origin
        _ = operation
        return mode == .normal ? .normalDispatch : .reject(.notAvailable)
    }

    static func bind<Coordinator: AnyObject>(mode: RPCServiceMode,
        site: NG8ServerConstructionSite, processCoordinator: Coordinator)
        -> NG8ServerBinding<Coordinator>? {
        _ = mode
        _ = site
        _ = processCoordinator
        return nil
    }
}
