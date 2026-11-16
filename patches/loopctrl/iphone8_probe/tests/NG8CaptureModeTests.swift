import Foundation

@main
struct NG8CaptureModeTests {
    static func require(_ value: @autoclosure () -> Bool, _ label: String) {
        if !value() { print("FAIL \(label)"); exit(1) }
    }

    static let remote = NG8RequestOrigin.authenticatedRemote(tokenID: "0123abcd")
    static let local = NG8RequestOrigin.trustedInProcess
    static let capture = RPCServiceMode.iphone8CaptureOnly
    static let runtimeID = String(repeating: "a", count: 32)
    static let probeID = String(repeating: "b", count: 32)

    static func decision(_ operation: NG8PolicyOperation,
                         origin: NG8RequestOrigin = NG8CaptureModeTests.remote) -> NG8RouteDecision {
        NG8CaptureRoutePolicy.decide(mode: capture, origin: origin, operation: operation)
    }

    static func qualification() {
        #if NG8_CAPTURE_PROBE_BUILD
        require(RPCServiceMode.compiledOptIn, "dedicated_compile_condition_is_visible")
        #else
        require(!RPCServiceMode.compiledOptIn, "ordinary_compile_condition_defaults_off")
        #endif
        var normalReads = 0
        let ordinary = RPCServiceMode.select(buildOptIn: false) {
            normalReads += 1
            return "iPhone10,1"
        }
        require(ordinary == .normal && normalReads == 0,
                "normal_build_performs_zero_hardware_queries")
        let rejected: [String?] = ["iPhone12,1", "iPhone10,4", "iPhone 8", "iPhone",
                                  "iPhone10,1 ", "", nil]
        for (index, model) in rejected.enumerated() {
            require(RPCServiceMode.select(buildOptIn: true,
                readHardwareIdentifier: { model }) == .normal,
                "other_unknown_or_failed_raw_model_stays_normal_\(index)")
        }
        var qualifiedReads = 0
        let qualified = RPCServiceMode.select(buildOptIn: true) {
            qualifiedReads += 1
            return "iPhone10,1"
        }
        // Required first behavior Red. This fails by value, not by compilation.
        require(qualified == .iphone8CaptureOnly,
                "qualified_optin_raw_iphone10_1_selects_capture_only")
        require(qualifiedReads == 1, "qualified_selection_reads_raw_hardware_once")
    }

    static func metadata() {
        let baselineCaps = ["envelope_v1", "necrogold_native_v15", "legacy-cap-sentinel"]
        let baselineMethods = ["config", "screenshot", "necro_native_start", "legacy-method-sentinel"]
        let normal = NG8AdvertisedSurface.project(mode: .normal,
            normalCapabilities: baselineCaps, normalMethodNames: baselineMethods)
        require(normal.serviceMode == nil && normal.capabilities == baselineCaps
            && normal.methodNames == baselineMethods, "normal_metadata_preserves_exact_order_and_values")
        let dedicated = NG8AdvertisedSurface.project(mode: capture,
            normalCapabilities: baselineCaps, normalMethodNames: baselineMethods)
        require(dedicated.serviceMode == "iphone8-capture-only-v1", "dedicated_metadata_names_service_mode")
        require(dedicated.capabilities == ["envelope_v1", "necrogold_capture_probe_v1"],
                "dedicated_metadata_advertises_probe_without_native_g1_or_stream")
        require(dedicated.methodNames == ["config", "logs", "recent_logs",
            "necro_capture_probe_status", "necro_capture_probe_start",
            "necro_capture_probe_cancel", "necro_capture_probe_results"],
            "dedicated_metadata_advertises_only_implemented_read_and_probe_methods")
    }

    static func routesAndAuthority() {
        require(decision(.http(verb: "POST", path: "/pair"), origin: .publicHTTP)
            == .rejectHTTP(status: 403, code: .pairingDisabledInCaptureOnly),
            "pair_is_always_403_without_approval_dispatch")
        require(decision(.http(verb: "GET", path: "/schema"), origin: .publicHTTP)
            == .allow(.publicMetadata), "schema_is_image_free_public_metadata")
        require(decision(.http(verb: "POST", path: "/rpc"), origin: .publicHTTP)
            == .allow(.encryptedRPC), "rpc_route_enters_existing_envelope_authentication")
        require(decision(.rpc(method: "config", callerParams: [:])) == .allow(.remoteConfigRead),
                "authenticated_remote_config_is_minimal_read_only")
        require(decision(.rpc(method: "config", callerParams: [:]), origin: local)
            == .allow(.trustedLocalConfigRead), "trusted_local_config_keeps_existing_health_shape_lane")
        for origin in [remote, local] {
            require(decision(.rpc(method: "logs", callerParams: [:]), origin: origin) == .allow(.logs),
                    "existing_authenticated_and_local_log_reads_keep_a_read_only_lane")
        }
        let mutations: [[String: NG8PolicyValue]] = [
            ["revoke_session_id": .string("0123abcd")], ["clear_sessions": .bool(true)],
            ["listen_port": .integer(8300)], ["allow_remote_access": .bool(true)],
            ["pair_respond": .unsupported], ["pair_allow_recent": .string("old-request")]
        ]
        for (index, params) in mutations.enumerated() {
            require(decision(.rpc(method: "config", callerParams: params)) == .reject(.invalidRequest),
                    "remote_config_mutation_refused_\(index)")
        }
        for forged in ["_peer_source", "_origin", "_actor", "_necro_probe_owner"] {
            require(decision(.rpc(method: "config", callerParams: [forged: .string("trustedInProcess")]))
                == .reject(.invalidRequest), "caller_field_cannot_create_local_authority_\(forged)")
        }
        require(decision(.rpc(method: "config", callerParams: ["revoke_session_id": .string("0123abcd")]),
            origin: local) == .allow(.trustedLocalAuthAdmin), "trusted_local_revoke_is_explicit_auth_admin")
        require(decision(.rpc(method: "config", callerParams: ["clear_sessions": .bool(true)]),
            origin: local) == .allow(.trustedLocalAuthAdmin), "trusted_local_clear_sessions_is_explicit_auth_admin")
        for deniedApproval in [["pair_respond": NG8PolicyValue.unsupported],
                               ["pair_allow_recent": NG8PolicyValue.string("old-request")]] {
            require(decision(.rpc(method: "config", callerParams: deniedApproval), origin: local)
                == .reject(.invalidRequest), "local_admin_cannot_reopen_pair_approval")
        }
        require(decision(.rpc(method: "config", callerParams: ["listen_port": .integer(8300)]),
            origin: local) == .allow(.trustedLocalListenerAdmin), "local_config_port_change_uses_listener_lane")
        let badLocalRequests: [[String: NG8PolicyValue]] = [["clear_sessions": .bool(false)],
            ["revoke_session_id": .integer(1)],
            ["revoke_session_id": .string("0123abcd"), "listen_port": .integer(8300)]]
        for bad in badLocalRequests {
            require(decision(.rpc(method: "config", callerParams: bad), origin: local)
                == .reject(.invalidRequest), "local_auth_admin_schema_is_closed")
        }
        for operation in [NG8LocalOperation.setPaused(true), .setPaused(false)] {
            require(decision(.local(operation), origin: local) == .allow(.trustedLocalAuthAdmin),
                    "owner_pause_and_resume_use_local_auth_admin")
            require(decision(.local(operation)) == .reject(.trustedLocalRequired),
                    "remote_origin_cannot_invoke_local_pause")
        }
        for operation in [NG8LocalOperation.stop, .restart, .setPort(8300),
                          .setRemoteAccess(true), .setRemoteAccess(false), .setNearby(false)] {
            require(decision(.local(operation), origin: local) == .allow(.trustedLocalListenerAdmin),
                    "local_listener_management_has_its_own_lane")
            require(decision(.local(operation)) == .reject(.trustedLocalRequired),
                    "remote_origin_cannot_invoke_local_listener_management")
        }
        let probeParams: [String: NG8PolicyValue] = ["runtime_id": .string(runtimeID), "probe_id": .string(probeID)]
        require(decision(.rpc(method: "necro_capture_probe_start", callerParams: probeParams)) == .allow(.probe),
                "authenticated_owner_can_enter_probe_parser")
        require(decision(.rpc(method: "necro_capture_probe_start", callerParams: probeParams), origin: local)
            == .reject(.authenticationRequired), "local_admin_does_not_manufacture_a_probe_owner")
        require(decision(.rpc(method: "necro_capture_probe_status", callerParams: [:]), origin: .publicHTTP)
            == .reject(.authenticationRequired), "public_http_cannot_dispatch_a_probe_rpc")
        for method in ["tap", "screenshot", "device_info", "reset", "necro_native_start",
                       "necro_native_cycle", "stream_ticket", "page_update", "pair_allow_recent"] {
            require(decision(.rpc(method: method, callerParams: [:])) == .reject(.notAvailable),
                    "capture_only_refuses_legacy_producer_\(method)")
        }
        for path in ["/stream", "/remote", "/remote/", "/stream?ticket=old"] {
            require(decision(.http(verb: "GET", path: path), origin: .publicHTTP) == .reject(.notAvailable),
                    "capture_only_refuses_legacy_http_\(path)")
        }
        require(NG8CaptureRoutePolicy.decide(mode: .normal, origin: remote,
            operation: .rpc(method: "config", callerParams: ["legacy-sentinel": .bool(true)])) == .normalDispatch,
            "ordinary_mode_delegates_existing_policy_without_new_allowlist")
    }

    final class ProcessOwner {
        let runtimeID = NG8CaptureModeTests.runtimeID
        var seen = Set([NG8CaptureModeTests.probeID])
        var generation: UInt64 = 7
        let deadline: UInt64 = 200
        let readyExpiry: UInt64 = 300
    }

    static func constructorBindings() {
        require(Set(NG8ServerConstructionSite.allCases.map { $0.rawValue }) ==
            Set(["initialStart", "urlPortChange", "configPortChange", "enableRemoteAccess", "disableRemoteAccess"]),
            "constructor_inventory_names_all_five_declared_sites")
        let owner = ProcessOwner()
        for site in NG8ServerConstructionSite.allCases {
            let rebound = NG8CaptureRoutePolicy.bind(mode: capture, site: site, processCoordinator: owner)
            require(rebound != nil, "capture_only_constructor_gets_process_binding_\(site.rawValue)")
            if let rebound {
                require(rebound.mode == capture && rebound.processCoordinator === owner,
                        "constructor_preserves_mode_and_same_coordinator_\(site.rawValue)")
                require(rebound.processCoordinator.runtimeID == runtimeID
                    && rebound.processCoordinator.seen == Set([probeID])
                    && rebound.processCoordinator.generation == 7
                    && rebound.processCoordinator.deadline == 200
                    && rebound.processCoordinator.readyExpiry == 300,
                    "constructor_does_not_reset_process_evidence_\(site.rawValue)")
            }
        }
    }

    static func main() {
        let arguments = Array(CommandLine.arguments.dropFirst())
        guard arguments.count <= 1 else {
            print("FAIL invalid_mode_test_selector")
            exit(2)
        }
        let selector = arguments.first ?? "all"
        switch selector {
        case "qualification": qualification()
        case "metadata": metadata()
        case "routes": routesAndAuthority()
        case "binding": constructorBindings()
        case "all":
            qualification()
            metadata()
            routesAndAuthority()
            constructorBindings()
        default:
            print("FAIL invalid_mode_test_selector")
            exit(2)
        }
        print("PASS NG8 mode selector \(selector); no live router, authentication, producer or device acceptance")
    }
}
