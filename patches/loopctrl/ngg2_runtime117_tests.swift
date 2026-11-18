// TEST117's three real Swift Runtime/normal Perception/Ring/Spool cases.
// The shop, HUD and UI are procedural. Wall-clock computation is charged;
// there is no fitted-phase adjustment, classification clock freeze or result
// override. The separate C Scene cuts are run and labelled by the checker.
func runtime117Start(_ id: String, continuous: Bool, initial: JSONValue? = .bool(true),
        profile: String = "normal-1-1-irregular-v1", finite: Bool = false) -> ([String: JSONValue]?, JSONRPCError?) {
    var params: [String: JSONValue] = ["run_id": .string(id), "profile": .string(profile),
        "_necro_owner": .string("fixture-owner")]
    if continuous { params["continuous_campaign"] = .bool(true) }
    if finite { params["yield_after_restart"] = .bool(true) }
    if let initial { params["initial_restart"] = initial }
    return runtime.handle(method: "necro_native_start", params: params)
}
func runtime117Events(_ id: String) -> [[String: JSONValue]] {
    (report(id)["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
}
func runtime117Reset(_ root: URL) {
    runtime116Reset(root)
    // The physical epoch is fixed at reset and is never moved to a C fit.
    NG2Fake.lock.lock(); NG2Fake.fixedClock = nil; NG2Fake.offset = 0; NG2Fake.lock.unlock()
    NG2RuntimeTestHooks.beforeCaptureAdmission = nil
    NG2RuntimeTestHooks.scheduleTicket = nil
    NG2RuntimeCycleTestHooks.classificationResult = nil
}
final class Runtime117World {
    let gate = NSLock(), variant: Int32, rootID: String, physicalEpoch: UInt64
    let initialX: Int32, initialY: Int32
    var captureStart: UInt64 = 0, captureEnd: UInt64 = 0
    var restarts = 0, normalCalls = 0, negativeCalls = 0, childID = ""
    var actualStartAccepted = false
    var partialJobs = 0, fullJobs = 0
    var admissions = [[String: JSONValue]](), workerDurations = [UInt64]()
    var workerStart: UInt64 = 0, rawSources = [UInt64: Data]()
    init(_ id: String, variant: Int32, floorInitially: Bool) {
        self.rootID = id; self.variant = variant
        initialX = floorInitially ? 0 : (variant == 1 ? 2 : 0)
        initialY = floorInitially ? 0 : (variant == 0 ? 1 : 0)
        physicalEpoch = NG2Fake.virtualClock()
        NG2Fake.lock.lock(); NG2Fake.walkPaused = !floorInitially; NG2Fake.lock.unlock()
    }
    func locked<T>(_ body: () -> T) -> T { gate.lock(); defer { gate.unlock() }; return body() }
    func install() {
        NG2RuntimeTestHooks.beforeCaptureAdmission = {
            self.locked { self.captureStart = NG2Fake.virtualClock() }
        }
        NG2RuntimeTestHooks.afterCaptureBackendReply = { _ in
            self.locked { self.captureEnd = NG2Fake.virtualClock() }
        }
        NG2RuntimeCycleTestHooks.rgba = { original in
            NG2Fake.lock.lock()
            let paused = NG2Fake.walkPaused, dx = NG2Fake.walkX, dy = NG2Fake.walkY
            NG2Fake.lock.unlock()
            if paused { return original }
            let values = self.locked { (self.captureStart, self.captureEnd, self.restarts >= 2) }
            let midpoint = values.0+(values.1 >= values.0 ? (values.1-values.0)/2 : 0)
            let elapsed = midpoint >= self.physicalEpoch ? midpoint-self.physicalEpoch : 0
            let q = Double(519_999_999-(elapsed % 520_000_000))/520_000_000.0
            if values.2 {
                // The real second RESTART tap changes the physical level.
                // This future floor must be observed and ACKed before a child
                // can be admitted; child admission never causes this change.
                var bytes = Data(count: 896*414*4); let count = bytes.count
                bytes.withUnsafeMutableBytes {
                    require(ng2_fixture_floor_pixels_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                        count, 0, 0, q, 0) == 1, "test117_successor_procedural_floor")
                }
                return bytes
            }
            var bytes = Data(count: 896*414*4); let count = bytes.count
            bytes.withUnsafeMutableBytes {
                require(ng2_fixture_shop117_rgba($0.bindMemory(to: UInt8.self).baseAddress,
                    count, self.variant, self.initialX+dx, self.initialY+dy, q) == 1,
                    "test117_public_shop_factory_actual_direction_gesture_pose")
            }
            return bytes
        }
        NG2Fake.cycleTap = { x, y in
            if x == 297 && y == 448 {
                let snapshot = report(self.rootID)
                let commands = runtime117Events(self.rootID)
                let first = commands.first(where: { $0["kind"]?.intValue == 1 }) ?? [:]
                let evidence: [String: JSONValue] = [
                    "actual_start_accepted": .bool(self.locked { self.actualStartAccepted }),
                    "accepted_frames": snapshot["accepted_frames"] ?? .int(0),
                    "last_capture_id": snapshot["last_capture_id"] ?? .int(0),
                    "actual_command_kind": first["kind"] ?? .int(0),
                    "actual_source_capture_id": first["source_capture_id"] ?? .int(0),
                    "actual_source_start_ns": first["source_start_ns"] ?? .int(0),
                    "restart_count": .int(self.locked { self.restarts })]
                require(evidence["actual_start_accepted"]?.boolValue == true &&
                    (evidence["accepted_frames"]?.intValue ?? 0) > 0 &&
                    (evidence["last_capture_id"]?.intValue ?? 0) > 0 &&
                    evidence["actual_command_kind"]?.intValue == 1 &&
                    (evidence["actual_source_capture_id"]?.intValue ?? 0) > 0 &&
                    (evidence["actual_source_start_ns"]?.intValue ?? 0) > 0 &&
                    evidence["restart_count"]?.intValue == 0,
                    "test117_UI_policy_Red_requires_accepted_start_capture_and_real_RESUME")
                runtime116Emit("INITIAL_UI117", evidence)
                require(false, "test117_initial_root_never_RESUMEs_old_floor")
            }
            if x == 144 && y == 448 {
                self.locked { self.restarts += 1 }
                NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
            }
        }
        NG2Fake.applyShopGesture = { _ in
            // The existing handler updates walkX/Y from the actual gesture
            // coordinates after this return. Charge the recorded ACK duration
            // to the wall clock; neither a ticket nor a fit moves the actor.
            Thread.sleep(forTimeInterval: 0.271861834)
            return true
        }
        NG2RuntimeCycleTestHooks.beforeClassification = { _ in
            let state = cycleCompanion(self.rootID)
            runtime112RecordAdmission(self.rootID, state, label: "test117_normal_wall_clock")
            let capture = UInt64(state["capture_id"]?.intValue ?? 0)
            guard let source = runtime.testOriginalFrameEvidence(self.rootID, captureIDs: [capture])?[capture],
                  let raw = NG2Raster.decode(source.0) else {
                require(false, "test117_actual_worker_immutable_source_present"); return
            }
            let scene = UnsafeMutablePointer<NG2Scene>.allocate(capacity: 1)
            scene.initialize(to: NG2Scene()); defer { scene.deinitialize(count: 1); scene.deallocate() }
            let status = raw.withUnsafeBytes {
                ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, raw.count, 896*4, scene)
            }
            let items = withUnsafeBytes(of: scene.pointee.tiles) { $0.filter { $0 == 6 }.count }
            require(status == 0 && scene.pointee.state == 2 &&
                (scene.pointee.goods == 1 && items > 0 || scene.pointee.goods == 2 && items == 3),
                "test117_normal_Perception_partial_then_full_without_scene_injection")
            self.locked {
                if scene.pointee.goods == 1 { self.partialJobs += 1 }
                if scene.pointee.goods == 2 { self.fullJobs += 1 }
                self.rawSources[capture] = raw; self.admissions.append(state)
                self.workerStart = NG2Fake.virtualClock()
            }
        }
        NG2RuntimeCycleTestHooks.afterClassificationCall = { mode, status, outcome in
            require(mode == Int32(NG2_RING_MODE_TARGET_ONLY) && status == 0,
                "test117_actual_normal_target_worker_returns_before_unchanged_budget")
            self.locked {
                self.normalCalls += 1
                if outcome == UInt32(NG2_RING_NEGATIVE) { self.negativeCalls += 1 }
                self.workerDurations.append(NG2Fake.virtualClock()-self.workerStart)
            }
        }
        NG2RuntimeTestHooks.beforeControlTick = { _ = runtime116Status(self.rootID) }
    }
}
func runtime117CheckChain(_ root: URL, variant: Int32) {
    runtime117Reset(root); let id = identity()
    let world = Runtime117World(id, variant: variant, floorInitially: false); world.install()
    fixtureFailureSnapshot = { ["report": .object(report(id)), "cycle": .object(cyclePayload(id)),
        "campaign": .object(runtime116Payload(id, keepalive: false)),
        "restarts": .int(world.locked { world.restarts }), "calls": .int(world.locked { world.normalCalls })] }
    NG2RuntimeContinuousTestHooks.afterChildAdmitted = { rootID, old, child, index in
        require(rootID == id && old == id && child != id && index == 1,
            "test117_one_sealed_parent_admits_one_fresh_child")
        require(ir110Record(root, id, "continuation_seal") != nil,
            "test117_continuation_is_disk_seal_before_successor")
        world.locked { world.childID = child }
    }
    let start = runtime117Start(id, continuous: true)
    require(start.1 == nil && start.0?["initial_restart"]?.boolValue == true,
        "test117_initial_restart_explicit_continuous_start")
    world.locked { world.actualStartAccepted = true }
    require(runtime117Start(id, continuous: true, initial: nil).1?.code == -32602,
        "test117_root_identity_cannot_drop_initial_restart")
    pump("test117_normal_negative_persists_and_restarts_into_fresh_child", timeout: 50) {
        let child = world.locked { world.childID }
        return !child.isEmpty && (report(child)["last_capture_id"]?.intValue ?? 0) > 0 || runtime116Drained(id)
    }
    let child = world.locked { world.childID }, terminal = ir110Record(root, id, "terminal")?["controller"]?.objectValue ?? [:]
    let events = (terminal["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    let actual = world.locked { (world.restarts, world.normalCalls, world.negativeCalls, world.workerDurations) }
    require(!child.isEmpty && actual.0 == 2 && actual.1 > 0 && actual.2 > 0 &&
        actual.3.allSatisfy { $0 < 100_000_000 }, "test117_initial_RS_then_normal_negative_RS_not_stopped_after_door")
    require((terminal["inputs"]?.intValue ?? 0) > 0 && (terminal["moves"]?.intValue ?? 0) > 0 &&
        world.locked { world.partialJobs > 0 && world.fullJobs > 0 } &&
        events.contains { $0["kind"]?.intValue == 4 && $0["outcome"]?.intValue == 2 &&
            $0["motion"]?.intValue == 1 },
        "test117_actual_direction_ACK_and_MOTION_precede_full_goods_and_negative_restart")
    require(events.filter { $0["kind"]?.intValue == 1 }.isEmpty &&
        events.filter { $0["kind"]?.intValue == 3 && $0["outcome"]?.intValue == 2 }.count == 2 &&
        ir110Record(root, id, "checkpoint") != nil && ir110Record(root, id, "restart_intent") != nil &&
        ir110Record(root, id, "restart_outcome") != nil,
        "test117_normal_negative_has_checkpoint_durable_intent_ACK_and_new_floor")
    require(report(child)["restarts"]?.intValue == 0 &&
        runtime117Events(child).allSatisfy { $0["kind"]?.intValue != 3 },
        "test117_successor_floor_has_no_duplicate_initial_restart")
    let childSession = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(child).appendingPathComponent("session.json")
    let childHeader = (try? Data(contentsOf: childSession)).flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
    require((childHeader?["provenance"] as? [String: Any])?["initial_restart"] == nil,
        "test117_successor_immutable_mode_is_false_in_actual_session")
    require(NG2Fake.taps().filter { $0 == CGPoint(x: 297, y: 448) }.isEmpty,
        "test117_ROOT_and_successor_do_not_resume_old_floor")
    let evidence: [String: JSONValue] = ["scope": .string("normal_RGBA_Runtime_Ring_Spool_procedural_UI_future"),
        "root_id": .string(id), "child_id": .string(child), "variant": .int(Int(variant)),
        "physical_period_ns": .int(520_000_000), "physical_epoch_ns": .int(Int(world.physicalEpoch)),
        "initial_and_goods_restarts": .int(actual.0), "normal_calls": .int(actual.1),
        "direction_inputs": terminal["inputs"] ?? .null, "verified_moves": terminal["moves"] ?? .null,
        "partial_jobs": .int(world.locked { world.partialJobs }), "full_jobs": .int(world.locked { world.fullJobs }),
        "direction_ACK_model_ns": .int(271_861_834),
        "negative_calls": .int(actual.2), "classification_override": .bool(false),
        "wall_clock_charged": .bool(true), "fit_phase_adjustments": .int(0),
        "worker_duration_ns": .array(actual.3.map { .int(Int($0)) })]
    runtime116Emit("BOUNDARY117", evidence)
    _ = call("necro_native_cancel", id); NG2Fake.release()
    pump("test117_actual_root_and_child_drain", timeout: 40) { runtime116Drained(id) }
    runtime116ExportAll(root, id, label: variant == 0 ? "single_face_restart" : "mixed_price_partial")
}
func testRuntime117RootFloor(_ root: URL) {
    runtime117Reset(root)
    for value in [JSONValue.bool(false), .int(1), .null] {
        require(runtime117Start(identity(), continuous: false, initial: value).1?.code == -32602,
            "test117_initial_restart_rejects_false_integer_and_null")
    }
    require(runtime117Start(identity(), continuous: false, profile: "normal-1-1-v1").1?.code == -32602 && !runtime.hasLease,
        "test117_initial_restart_rejects_foreign_profile_before_lease")
    let id = identity()
    let world = Runtime117World(id, variant: 0, floorInitially: true)
    // This finite-start cut checks only initial UI policy; its later source is
    // deliberately not classified because cancellation follows actual RS.
    world.install(); NG2RuntimeCycleTestHooks.beforeClassification = nil
    NG2RuntimeCycleTestHooks.afterClassificationCall = nil
    NG2RuntimeTestHooks.beforeControlTick = nil
    diagnoseFixture(id)
    let answer = runtime117Start(id, continuous: false, finite: true)
    require(answer.1 == nil && answer.0?["initial_restart"]?.boolValue == true,
        "test117_initial_floor_finite_start_is_explicit")
    require(runtime117Start(id, continuous: false, initial: nil, finite: true).1?.code == -32602,
        "test117_current_identity_cannot_drop_initial_restart")
    pump("test117_initial_floor_actual_PAUSE_then_RS", timeout: 20) {
        world.locked { world.restarts >= 1 } && report(id)["restarts"]?.intValue == 1 || drained(id)
    }
    _ = call("necro_native_cancel", id); NG2Fake.release()
    pump("test117_initial_floor_cancel_drains", timeout: 30) { drained(id) }
    let kinds = runtime117Events(id).filter { $0["outcome"]?.intValue == 2 }.compactMap { $0["kind"]?.intValue }
    require(Array(kinds.prefix(2)) == [2,3] && !kinds.contains(1) && world.locked { world.restarts == 1 },
        "test117_initial_FLOOR_PAUSE_RS_and_RESUME_zero")
    require(runtime117Start(id, continuous: false, initial: nil, finite: true).1?.code == -32602,
        "test117_stopped_current_identity_preserves_initial_mode")
    require(cyclePayload(id)["initial_restart"] == nil && call("necro_native_status", id).0?["initial_restart"] == nil,
        "test117_initial_mode_does_not_expand_closed_query_or_status_schema")
    publishFixtureClaim(id)
    runtime112PreserveSyntheticExport(root, id, label: "root-floor-initial")

    // Replace the resident run so the first UUID is read from immutable
    // history. The auxiliary legacy-mode run is cancelled before pumping UI.
    let auxiliary = identity(), historicalTouches = NG2Fake.countTouches()
    let oldMode = runtime117Start(auxiliary, continuous: false, initial: nil, finite: true)
    require(oldMode.1 == nil && oldMode.0?["initial_restart"] == nil,
        "test117_legacy_omit_mode_still_has_no_initial_option")
    require(runtime117Start(auxiliary, continuous: false, finite: true).1?.code == -32602,
        "test117_current_false_cannot_be_changed_to_true")
    _ = call("necro_native_cancel", auxiliary)
    pump("test117_auxiliary_legacy_run_cancel_drains", timeout: 30) { drained(auxiliary) }
    require(runtime117Start(id, continuous: false, initial: nil, finite: true).1?.code == -32602 &&
        runtime117Start(id, continuous: false, initial: .bool(false), finite: true).1?.code == -32602 &&
        runtime117Start(id, continuous: true).1?.code == -32602,
        "test117_history_uuid_cannot_drop_or_change_initial_root_mode")
    let unchangedHistory = runtime117Start(id, continuous: false, finite: true)
    require(unchangedHistory.1 == nil && unchangedHistory.0?["initial_restart"]?.boolValue == true &&
        !runtime.hasLease && NG2Fake.countTouches() == historicalTouches,
        "test117_matching_history_reply_is_metadata_without_new_input")
    publishFixtureClaim(auxiliary)

    // These are explicitly procedural session metadata, not manufactured game
    // terminals. Real Spool create/recover and the production Runtime parser
    // check CFBoolean and root identity without creating a C controller.
    let recoveryTouches = NG2Fake.countTouches(), recoveryCaptures = NG2Fake.countRequests()
    var recoveryEvidence = [[String: JSONValue]]()
    func recoverMode(_ label: String, initial: Any?, continuous: Bool, fault: String? = nil,
            profile: String = "normal-1-1-irregular-v1", rejected: Bool = false) {
        let recoveredID = identity(), owner = "fixture-owner", started = NG2Fake.virtualClock()
        var provenance: [String: Any] = ["clock_id": identity(), "native_profile": profile]
        if let initial { provenance["initial_restart"] = initial }
        if !continuous { provenance["yield_after_restart"] = true }
        do {
            if continuous {
                provenance["continuous_campaign"] = ["schema": "ngg2-continuous-child-v1", "root_id": recoveredID,
                    "index": 0, "predecessor_id": NSNull(), "root_started_ns": started,
                    "root_deadline_ns": started + 2_880_000_000_000] as [String: Any]
                let quota = try NG2CycleSpool.testCreateCampaignQuota(rootURL: root, rootID: recoveredID, owner: owner)
                let reservation = try quota.reserveNext(runID: recoveredID, index: 0, predecessorID: nil)
                _ = try NG2CycleSpool.testCreate(rootURL: root, runID: recoveredID, owner: owner,
                    provenance: provenance, quota: quota, reservation: reservation)
            } else {
                _ = try NG2CycleSpool.testCreate(rootURL: root, runID: recoveredID, owner: owner, provenance: provenance)
            }
            if let fault {
                let session = root.appendingPathComponent("NGG2Cycles").appendingPathComponent(recoveredID).appendingPathComponent("session.json")
                var header = try JSONSerialization.jsonObject(with: Data(contentsOf: session)) as! [String: Any]
                var source = header["provenance"] as! [String: Any]
                var mode = source["continuous_campaign"] as! [String: Any]
                switch fault {
                case "missing-schema": mode.removeValue(forKey: "schema")
                case "extra": mode["unexpected"] = true
                case "foreign-root": mode["root_id"] = identity()
                case "index-bool": mode["index"] = true
                case "index-one": mode["index"] = 1
                case "predecessor": mode["predecessor_id"] = recoveredID
                case "start-bool": mode["root_started_ns"] = true
                case "deadline-zero": mode["root_deadline_ns"] = 0
                default: require(false, "test117_mode_fault_has_a_closed_name")
                }
                source["continuous_campaign"] = mode; header["provenance"] = source
                try JSONSerialization.data(withJSONObject: header, options: [.sortedKeys]).write(to: session, options: .atomic)
            }
        } catch { require(false, "test117_procedural_session_metadata_created"); return }
        var reply: ([String: JSONValue]?, JSONRPCError?) = (nil, nil)
        pump("test117_recover_mode_"+label, timeout: 30) {
            reply = ir110Call(recoveredID)
            return rejected ? reply.1?.code == -32096 : reply.0?["payload"]?.objectValue?["workers_drained"]?.boolValue == true
        }
        if !rejected {
            let payload = reply.0?["payload"]?.objectValue ?? [:]
            let expectedInitial = initial != nil
            let matching = runtime117Start(recoveredID, continuous: continuous,
                initial: expectedInitial ? .bool(true) : nil, finite: !continuous)
            require(matching.1 == nil && (matching.0?["initial_restart"]?.boolValue ?? false) == expectedInitial &&
                (matching.0?["continuous_campaign"]?.boolValue ?? false) == continuous &&
                payload["terminal"]?.boolValue == true && payload["workers_drained"]?.boolValue == true,
                "test117_recovered_matching_mode_is_drained_metadata")
            if expectedInitial {
                require(runtime117Start(recoveredID, continuous: continuous, initial: nil, finite: !continuous).1?.code == -32602 &&
                    runtime117Start(recoveredID, continuous: continuous, initial: .bool(false), finite: !continuous).1?.code == -32602 &&
                    runtime117Start(recoveredID, continuous: !continuous, finite: continuous).1?.code == -32602,
                    "test117_recovered_uuid_cannot_drop_or_change_initial_root_mode")
            } else {
                require(runtime117Start(recoveredID, continuous: false, finite: true).1?.code == -32602,
                    "test117_recovered_old_false_cannot_be_changed_to_true")
            }
        }
        require(!runtime.hasLease && NG2Fake.countTouches() == recoveryTouches && NG2Fake.countRequests() == recoveryCaptures,
            "test117_recovery_mode_never_restores_capture_controller_or_input")
        recoveryEvidence.append(["case": .string(label), "scope": .string("procedural_read_only_Spool_Runtime_metadata"),
            "rejected": .bool(rejected), "error": reply.1.map { .int($0.code) } ?? .null,
            "new_inputs": .int(0), "new_captures": .int(0)])
    }
    recoverMode("finite_true_CFBoolean", initial: true, continuous: false)
    recoverMode("legacy_omitted_false", initial: nil, continuous: false)
    recoverMode("continuous_true_read_only_root", initial: true, continuous: true)
    for (label, value) in [("false", false as Any), ("integer", 1 as Any), ("floating", 1.0 as Any),
            ("string", "true" as Any), ("null", NSNull() as Any)] {
        recoverMode("invalid_initial_"+label, initial: value, continuous: false, rejected: true)
    }
    recoverMode("foreign_profile", initial: true, continuous: false, profile: "normal-1-1-cycle-v1", rejected: true)
    for fault in ["missing-schema", "extra", "foreign-root", "index-bool", "index-one", "predecessor", "start-bool", "deadline-zero"] {
        recoverMode("invalid_root_"+fault, initial: true, continuous: true, fault: fault, rejected: true)
    }
    runtime116Emit("BOUNDARY117", ["scope": .string("actual_Runtime_initial_floor_finite_UI"),
        "completed_kinds": .array(kinds.map(JSONValue.int)), "restarts": .int(world.locked { world.restarts }),
        "mode_metadata_checks": .array(recoveryEvidence.map(JSONValue.object))])
}

let root117 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime117-"+UUID().uuidString)
try FileManager.default.createDirectory(at: root117, withIntermediateDirectories: true,
    attributes: [.posixPermissions: NSNumber(value: 0o700)])
defer { try? FileManager.default.removeItem(at: root117) }
NG2RuntimeCycleTestHooks.spoolRoot = root117
cycleFixtureProfile = "normal-1-1-irregular-v1"
let case117 = CommandLine.arguments.last ?? ""
pump("test117_irregular_prepare_ready") { cycleCall(identity(), "prepare").0?["payload"]?.objectValue?["ready"]?.boolValue == true }
switch case117 {
case "single_face_restart": runtime117CheckChain(root117.appendingPathComponent(case117), variant: 0)
case "mixed_price_partial": runtime117CheckChain(root117.appendingPathComponent(case117), variant: 1)
case "root_floor_restart": testRuntime117RootFloor(root117.appendingPathComponent(case117))
default: require(false, "test117_unknown_case_is_not_another_fixture")
}
print("PASS TEST117 CASE "+case117)
