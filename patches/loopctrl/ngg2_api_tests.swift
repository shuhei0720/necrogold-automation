import Foundation

func require(_ value: Bool, _ label: String) {
    if !value { print("FAIL \(label)"); exit(1) }
}
let methods: Set<String> = ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results"]
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
print("PASS 16 production authenticated owner projection contracts; network/auth envelope not executed")
