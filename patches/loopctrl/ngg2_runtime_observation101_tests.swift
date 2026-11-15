// TEST101 only: finite diagnostic export and one FULL/UNKNOWN framing worker.
import Foundation
import CoreGraphics
import ImageIO

var failure101: (() -> [String: JSONValue])?
func require101(_ value: Bool, _ name: String) {
    if !value {
        if let state = failure101?(), let raw = try? JSONEncoder().encode(state), let text = String(data: raw, encoding: .utf8) {
            print("DIAGNOSTIC observation101 " + text)
        }
        print("FAIL " + name); exit(1)
    }
}
func wait101(_ timeout: Double = 30, _ condition: () -> Bool) -> Bool {
    let until = Date().addingTimeInterval(timeout)
    while !condition() && Date() < until { RunLoop.current.run(until: Date().addingTimeInterval(0.005)) }
    return condition()
}
func pump101(_ name: String, _ condition: () -> Bool) { require101(wait101(30,condition),name) }
func startup101(_ stage: String, _ answer: ([String: JSONValue]?,JSONRPCError?)) {
    if let error = answer.1 {
        let value: [String: JSONValue] = ["stage": .string(stage),"error_code": .int(error.code),
            "error_message": .string(error.message),"error_data": error.data.map { .object($0) } ?? .null]
        if let data = try? JSONEncoder().encode(value), let line = String(data: data,encoding: .utf8) { print("DIAGNOSTIC observation101_startup "+line) }
    }
}
final class Framing101Clock {
    private let lock = NSLock()
    private var value = DispatchTime.now().uptimeNanoseconds
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; value += 1_000; return value }
    func advance(_ amount: UInt64) { lock.lock(); value += amount; lock.unlock() }
    func reach(_ target: UInt64) { lock.lock(); if value < target { value = target }; lock.unlock() }
}
func framing101Proof() -> NG2Framing101Proof { var value = NG2Framing101Proof(); ng2_framing101_proof(&value); return value }
func framing101Hash(_ data: Data) -> UInt64 {
    data.reduce(UInt64(14_695_981_039_346_656_037)) { ($0 ^ UInt64($1)) &* 1_099_511_628_211 }
}
func framing101Pixels(_ marker: Int32) -> Data {
    var value = Data(count: 896*414*4); let count = value.count
    value.withUnsafeMutableBytes { require101(ng2_framing101_pixels($0.bindMemory(to: UInt8.self).baseAddress,count,marker)==1,
                                             "framing101_procedural_rgba") }
    return value
}
func testFullFraming101(_ root: URL) throws {
    let runtime = NG2Runtime.shared, clock = Framing101Clock(), gate = NSLock(), second = DispatchSemaphore(value: 0)
    let id = "00000000000000000000000000101101"
    let a = framing101Pixels(31), b = framing101Pixels(47), unknown = framing101Pixels(61)
    let pause = framing101Pixels(11), clear = framing101Pixels(23), changed = framing101Pixels(24)
    var source = 23, firstCapture = false, resumeSettled = false, pauseSettled = false, entered2 = false
    var jobs: [UInt64] = []
    NG2Fake.reset(.walk); ng2_framing101_reset()
    NG2Fake.lock.lock(); NG2Fake.walkPaused = true; NG2Fake.lock.unlock()
    func call(_ mode: String, _ extra: [String: JSONValue] = [:]) -> ([String: JSONValue]?,JSONRPCError?) {
        var params: [String: JSONValue] = ["run_id": .string(id),"mode": .string(mode),"_necro_owner": .string("fixture-owner")]
        for (k,v) in extra { params[k] = v }
        return runtime.handle(method: "necro_native_cycle",params: params)
    }
    func payload() -> [String: JSONValue] { call("status").0?["payload"]?.objectValue ?? [:] }
    func companion() -> [String: JSONValue] { payload()["cycle"]?.objectValue ?? [:] }
    func report() -> [String: JSONValue] {
        runtime.handle(method: "necro_native_status",params: ["run_id": .string(id),"_necro_owner": .string("fixture-owner")]).0?["report"]?.objectValue ?? [:]
    }
    failure101 = {
        let p = framing101Proof()
        return ["cycle": .object(payload()),"report": .object(report()),"seed_error": .int(Int(p.seed_error)),
            "fit_ok": .int(Int(p.fit_ok)),"seed_count": .int(Int(p.seed_count)),"a_capture": .int(Int(p.a_capture)),
            "static_capture": .int(Int(p.static_capture)),"move_id": .int(Int(p.move_id)),"ack_prefix": .int(Int(p.ack_prefix)),
            "unknown_seen": .int(Int(p.unknown_seen)),"job_after": .int(Int(p.job_after)),
            "old_horizon": .int(Int(p.old_horizon)),"new_horizon": .int(Int(p.new_horizon))]
    }
    NG2RuntimeTestHooks.clock = { clock.now() }
    NG2RuntimeCycleTestHooks.spoolRoot = root
    NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        gate.lock(); let advance = !firstCapture; firstCapture = true; gate.unlock()
        // The only 2.2s history setup precedes the first image/ticket, inside
        // the unchanged activation3s/no-Scene4s guards. No deadline is edited.
        if advance { clock.advance(2_200_000_000) }
    }
    NG2RuntimeCycleTestHooks.rgba = { _ in
        ng2_framing101_clock(NG2Runtime.now())
        NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
        if paused { return pause }
        let proof = framing101Proof()
        if proof.ack_prefix == 4 && proof.unknown_seen == 0 { return unknown }
        gate.lock(); let marker = source; gate.unlock()
        return marker == 23 ? clear : marker == 24 ? changed : marker == 47 ? b : a
    }
    NG2Fake.cycleTap = { x,y in
        if x == 297 && y == 448 { NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock() }
        if x == 144 && y == 448 {
            gate.lock(); source = 24; gate.unlock()
            NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock()
        }
    }
    NG2RuntimeObserveTestHooks.afterObserve = {
        let proof = framing101Proof()
        gate.lock()
        if proof.ready_for_a == 1 && source == 24 { source = 31 }
        if proof.unknown_seen == 1 && source == 31 { source = 47 }
        gate.unlock()
    }
    NG2RuntimeCycleTestHooks.beforeClassification = { job in
        gate.lock(); jobs.append(job); if job == 2 { entered2 = true }; gate.unlock()
        if job == 2 { require101(second.wait(timeout: .now()+30) == .success,"framing101_second_worker_fixture_release") }
    }
    NG2RuntimeCycleTestHooks.classificationResult = { job,_,value in
        ng2_framing101_result(job,value.started_ns,NG2Runtime.now(),&value)
    }
    NG2RuntimeTestHooks.beforeControlTick = {
        let value = report()
        let proof = framing101Proof()
        if proof.seed_count == 0 {
            let prefix = value["last_completed_id"]?.intValue ?? 0
            let input = value["input_state"]?.intValue ?? -1
            gate.lock()
            let resume = prefix == 1 && input == 0 && !resumeSettled
            let paused = prefix == 2 && input == 0 && !pauseSettled
            if resume { resumeSettled = true }; if paused { pauseSettled = true }; gate.unlock()
            if resume || paused { clock.advance(220_000_000) }
        } else if proof.ack_prefix == 4 && proof.unknown_seen == 0 {
            clock.reach(proof.target_ns+80_000_000)
        } else if proof.move_id == 0 {
            let target = UInt64(max(0,value["next_target_ns"]?.intValue ?? 0))
            let lead = UInt64(max(0,value["lead_ns"]?.intValue ?? 0))
            if target > lead+90_000_000 { clock.reach(target-lead-90_000_000) }
        }
    }
    NG2RuntimeTestHooks.beforeMainAuthority = {
        let proof = framing101Proof(), value = report()
        if proof.move_id != 0 && value["current_command_id"]?.intValue == Int(proof.move_id) {
            clock.reach(proof.not_before_ns)
            require101(clock.now() <= proof.deadline_ns,"framing101_actual_dispatch_within_original_window")
        }
    }
    pump101("framing101_normal_prepare_ready") {
        let answer = call("prepare"); startup101("prepare",answer)
        require101(answer.1 == nil,"framing101_normal_prepare_request")
        return answer.0?["payload"]?.objectValue?["ready"]?.boolValue == true
    }
    let start = runtime.handle(method: "necro_native_start",params: ["run_id": .string(id),
        "profile": .string("normal-1-1-cycle-v1"),"_necro_owner": .string("fixture-owner")])
    startup101("start",start); require101(start.1 == nil,"framing101_actual_runtime_start")
    _ = wait101 {
        let proof = framing101Proof(), state = companion()
        return proof.move_id != 0 || (state["completed_shops"]?.intValue ?? 0) > 0 ||
            (payload()["terminal"]?.boolValue == true)
    }
    let issued = framing101Proof()
    require101(issued.seed_count == 1 && issued.fit_ok == 1 && issued.seed_error == 0 && issued.prefix == 3 &&
        issued.before_inputs == 3 && issued.before_moves == 1 && issued.before_restarts == 1,
        "framing101_declared_ordered_history_and_public_fit_precondition")
    require101(issued.move_id == 4 && issued.move_ordinal > 3 && issued.move_source > issued.a_capture &&
        issued.static_capture > issued.a_capture && issued.move_source >= issued.static_capture,
        "framing101_full_unknown_mints_fresh_observational_move")
    require101(issued.completed_before == 0,"framing101_unknown_is_not_a_completed_shop")
    pump101("framing101_actual_unknown_then_moved_and_second_worker") {
        gate.lock(); let entered = entered2; gate.unlock(); return entered
    }
    let moved = framing101Proof()
    require101(moved.ack_prefix == 4 && moved.unknown_seen == 1 && moved.ack_job == 1 && moved.ack_moves == 1 &&
        moved.moved_moves == 2 && moved.job_after == 2 && moved.job2_capture == moved.moved_capture &&
        moved.new_horizon <= moved.old_horizon && moved.old_job_rejected == 1 && moved.old_ticket_rejected == 1,
        "framing101_ack_unknown_has_no_credit_only_strict_move_binds_new_job")
    gate.lock(); source = 31; gate.unlock(); second.signal()
    pump101("framing101_new_candidate_terminal_drained") { payload()["workers_drained"]?.boolValue == true }
    let final = companion(), proof = framing101Proof(), value = report()
    require101(final["job_id"]?.intValue == 2 && final["capture_id"]?.intValue == Int(moved.job2_capture) &&
        final["outcome"]?.stringValue == "candidate" && final["candidate_latched"]?.boolValue == true &&
        final["completed_shops"]?.intValue == 1 && value["input_state"]?.intValue == 0 &&
        value["inputs"]?.intValue == 4 && value["moves"]?.intValue == 2 && value["restarts"]?.intValue == 1 &&
        NG2Fake.paths().count == 1,"framing101_candidate_hold_one_new_move_no_new_restart")
    require101(proof.ring_calls == 2 && proof.marker.0 == 31 && proof.marker.1 == 47 &&
        proof.raw_hash.0 == framing101Hash(a) && proof.raw_hash.1 == framing101Hash(b) &&
        proof.mode.0 == Int32(NG2_RING_MODE_TARGET_ONLY) && proof.mode.1 == Int32(NG2_RING_MODE_TARGET_ONLY) &&
        proof.scene_hash.1 == proof.bound_scene_hash,"framing101_normal_worker_owns_latest_immutable_full_b")
    let spool = try NG2CycleSpool.testRecover(rootURL: root,runID: id,owner: "fixture-owner")
    guard let checkpoint = try spool.records().last(where: { $0.kind == "checkpoint" }) else {
        require101(false,"framing101_candidate_checkpoint_exists"); return
    }
    let envelope = try JSONDecoder().decode([String: JSONValue].self,from: spool.recordBytes(checkpoint))
    let checkpointValue = envelope["payload"]?.objectValue ?? [:]
    require101(checkpointValue["assessment_adopted"]?.boolValue == true &&
        checkpointValue["raw_sha256"]?.stringValue == NG2CycleWire.hash(b) &&
        checkpointValue["assessment"]?.objectValue?["outcome"]?.stringValue == "candidate" &&
        checkpointValue["cycle"]?.objectValue?["job_id"]?.intValue == 2,
        "framing101_durable_new_job_result_not_old_unknown")
    gate.lock(); let workerJobs = jobs; gate.unlock(); require101(workerJobs == [1,2],"framing101_exactly_two_classification_jobs")
    NG2RuntimeTestHooks.beforeCaptureAdmission = nil; NG2RuntimeTestHooks.beforeControlTick = nil
    NG2RuntimeTestHooks.beforeMainAuthority = nil; NG2RuntimeObserveTestHooks.afterObserve = nil
    failure101 = nil
    print("PASS TEST101 FULL UNKNOWN static/fresh MOVE/ACK UNKNOWN/strict MOVED/latest worker candidate; declared historical preconditions")
}

let selected101 = CommandLine.arguments.count > 1 ? CommandLine.arguments[1].split(separator: ",").map(String.init) : ["retention","framing"]
require101(!selected101.isEmpty && Set(selected101).isSubset(of: ["retention","framing"]),"observation101_selected_cases")
let root101 = FileManager.default.temporaryDirectory.appendingPathComponent("runtime-observation101-"+UUID().uuidString)
try FileManager.default.createDirectory(at: root101,withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: root101) }
NG2Fake.reset(.walk)
for name in selected101 {
    // Independent components use separate stores. A deliberately unpublished
    // diagnostic retention spool must not become framing's recovery input.
    let caseRoot = root101.appendingPathComponent(name)
    try FileManager.default.createDirectory(at: caseRoot,withIntermediateDirectories: true)
    if name == "retention" { try NG2Runtime.shared.test101Retention(caseRoot) }
    else { try testFullFraming101(caseRoot) }
}
print("PASS TEST101 retention/export and full-UNKNOWN framing components; procedural/historical fixtures, real production paths")
