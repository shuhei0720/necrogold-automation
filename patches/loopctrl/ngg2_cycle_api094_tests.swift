import Foundation

func require(_ value: Bool, _ label: String) {
    if !value { print("FAIL \(label)"); exit(1) }
}
let methods: Set<String> = ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results", "necro_native_cycle"]
require(NG2AuthenticatedOwner.methods == methods, "native_method_allowlist")
for method in methods {
    let result = NG2AuthenticatedOwner.inject(method: method,
        params: ["run_id": .string(String(repeating: "a", count: 32)),
                 "_necro_owner": .string("forged"), "_actor": .object(["tok": .string("forged")])],
        owner: "authenticated-owner")!
    require(result["_necro_owner"]?.stringValue == "authenticated-owner", "authenticated_owner_\(method)")
    require(result["_actor"] == nil, "caller_actor_removed_\(method)")
    require(result["run_id"]?.stringValue == String(repeating: "a", count: 32), "run_id_preserved_\(method)")
}
let ordinary = NG2AuthenticatedOwner.inject(method: "gesture",
    params: ["_necro_owner": .string("forged"), "x": .int(10)], owner: "authenticated-owner")!
require(ordinary["_necro_owner"] == nil && ordinary["x"]?.intValue == 10, "ordinary_owner_private_param_removed")
require(NG2AuthenticatedOwner.inject(method: "logs", params: nil, owner: "owner") == nil, "nil_params_preserved")
let keepalive = NG2AuthenticatedOwner.inject(method: "necro_native_status",
    params: ["keepalive": .bool(true)], owner: "owner")!
require(keepalive["keepalive"]?.boolValue == true, "explicit_keepalive_preserved")
print("PASS TEST094 old16 projection checks plus new cycle owner checks; network/auth envelope not executed")

// The previous sixteen assertions are preserved above. Only their exact
// method allowlist intentionally gains the new, separately versioned RPC.
for mode in ["prepare", "status", "manifest", "chunk", "batch", "record", "published"] {
    let projected = NG2AuthenticatedOwner.inject(method: "necro_native_cycle",
        params: ["mode": .string(mode), "_necro_owner": .string("forged"),
                 "_actor": .object(["tok": .string("forged")])], owner: "cycle-owner")!
    require(projected["_necro_owner"]?.stringValue == "cycle-owner", "cycle_authenticated_owner_" + mode)
    require(projected["_actor"] == nil, "cycle_caller_actor_removed_" + mode)
    require(projected["mode"]?.stringValue == mode, "cycle_mode_preserved_" + mode)
}
let empty = NG2AuthenticatedOwner.inject(method: "necro_native_cycle", params: nil, owner: "cycle-owner")!
require(empty == ["_necro_owner": .string("cycle-owner")], "cycle_nil_params_owner_only")
let unknown = NG2AuthenticatedOwner.inject(method: "necro_native_cycle_extra",
    params: ["_necro_owner": .string("forged")], owner: "cycle-owner")!
require(unknown["_necro_owner"] == nil, "unknown_method_cannot_gain_cycle_owner")

require(RPCMethodRegistry.serverVersion == "1.98.16-ngg2", "legacy_server_version_preserved")
require(RPCMethodRegistry.protocolVersion == 1, "legacy_envelope_protocol_preserved")
let caps = RPCMethodRegistry.capabilityTags
for index in 1...15 { require(caps.filter { $0 == "necrogold_native_v\(index)" }.count == 1, "legacy_capability_\(index)") }
require(caps.filter { $0 == "necrogold_native_cycle_v1" }.count == 1, "independent_cycle_capability_once")
let nativeMethods = RPCMethodRegistry.methods.filter { $0.name.hasPrefix("necro_native_") }
require(nativeMethods.count == 5 && Set(nativeMethods.map { $0.name }) == methods, "exact_public_native_method_set")
let cycle = nativeMethods.first { $0.name == "necro_native_cycle" }!
let expectedParams: Set<String> = ["run_id", "mode", "request_authorization", "keepalive", "export_id", "capture_id",
    "sequence", "offset", "count", "manifest_sha256", "archive_sha256"]
require(cycle.params.count == expectedParams.count && Set(cycle.params.map { $0.name }) == expectedParams,
        "cycle_public_parameter_registry_closed")
require(cycle.params.filter { $0.required }.map { $0.name } == ["run_id"], "cycle_only_run_identity_required")
let types = Dictionary(uniqueKeysWithValues: cycle.params.map { ($0.name, $0.type) })
for name in ["capture_id", "sequence", "offset", "count"] { require(types[name] == "integer", "cycle_integer_" + name) }
for name in ["request_authorization", "keepalive"] { require(types[name] == "boolean", "cycle_boolean_" + name) }
let schema = RPCMethodRegistry.generateSchemaDocument()
require(schema["server_version"] as? String == RPCMethodRegistry.serverVersion, "actual_schema_version")
require(schema["protocol_version"] as? Int == 1, "actual_schema_protocol")
require(schema["capability_tags"] as? [String] == caps, "actual_schema_capability_projection")
let methodSchema = RPCMethodRegistry.generateJSONSchema()
require(methodSchema.filter { $0["name"] as? String == "necro_native_cycle" }.count == 1, "actual_schema_cycle_method_once")
print("PASS TEST094 actual owner projection and native cycle schema; no network, UI or phone acceptance")
