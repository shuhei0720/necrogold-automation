// TEST116 native campaign integration. Future game pixels and clocks are
// procedural; this checks the actual Runtime public RPC and callback bodies.
func runtime116Start(_ id: String) -> ([String: JSONValue]?, JSONRPCError?) {
    runtime.handle(method: "necro_native_start", params: ["run_id": .string(id),
        "profile": .string("normal-1-1-irregular-v1"), "continuous_campaign": .bool(true),
        "_necro_owner": .string("fixture-owner")])
}
func runtime116Status(_ id: String, keepalive: Bool = true) -> ([String: JSONValue]?, JSONRPCError?) {
    cycleCall(id, "campaign_status", extra: ["keepalive": .bool(keepalive)])
}
func testRuntime116NewMode(_ root: URL) {
    runtime112Reset(root)
    let id = identity()
    let answer = runtime116Start(id)
    // The pinned old Runtime compiles and returns its real -32602 rejection.
    // No missing test hook or replacement product body is used for this Red.
    require(answer.1 == nil && answer.0?["continuous_campaign"]?.boolValue == true,
        "test116_continuous_native_mode_is_admitted_without_old_pause_yield")
    let status = runtime116Status(id)
    require(status.1 == nil && status.0?["payload"]?.objectValue?["root_id"]?.stringValue == id,
        "test116_root_status_binds_same_native_campaign_identity")
    _ = call("necro_native_cancel", id)
    NG2Fake.release()
    pump("test116_root_and_all_children_cancel_drained", timeout: 30) {
        runtime116Status(id, keepalive: false).0?["payload"]?.objectValue?["workers_drained"]?.boolValue == true
    }
}

let root116 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime116-" + UUID().uuidString)
try FileManager.default.createDirectory(at: root116, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root116) }
NG2RuntimeCycleTestHooks.spoolRoot = root116
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case116 = CommandLine.arguments.last ?? ""
pump("test116_irregular_prepare_ready") {
    cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
switch case116 {
case "new_mode": testRuntime116NewMode(root116.appendingPathComponent("mode"))
default: require(false, "test116_unknown_case_is_not_another_fixture")
}
print("PASS TEST116 CASE " + case116)
