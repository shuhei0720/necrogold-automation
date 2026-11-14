// One HOST component callback. Historical walk/opening is a declared C seed;
// Scenes and classifier outcomes are procedural. Runtime workers are real.
import Foundation
import CoreGraphics
import ImageIO

func require(_ condition: Bool, _ name: String) {
    if !condition { print("FAIL " + name); exit(1) }
}
func pump(_ name: String, timeout: Double = 20, _ condition: () -> Bool) {
    let deadline = Date().addingTimeInterval(timeout)
    while !condition() && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.005)) }
    require(condition(), name)
}
final class Partial100Clock {
    private let lock = NSLock()
    private var value = DispatchTime.now().uptimeNanoseconds
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; value += 1_000; return value }
    func advance(_ amount: UInt64) { lock.lock(); value += amount; lock.unlock() }
}
func partial100Proof() -> NG2Partial100Proof { var value = NG2Partial100Proof(); ng2_partial100_proof(&value); return value }
func partial100Pixels(_ marker: Int32) -> Data {
    var value = Data(count: 896*414*4); let count = value.count
    value.withUnsafeMutableBytes { require(ng2_partial100_pixels($0.bindMemory(to: UInt8.self).baseAddress, count, marker) == 1,
                                           "partial100_procedural_rgba") }
    return value
}
func partial100Hash(_ data: Data) -> UInt64 {
    data.reduce(UInt64(14_695_981_039_346_656_037)) { ($0 ^ UInt64($1)) &* 1_099_511_628_211 }
}
func partial100StartupDiagnostic(_ stage: String, _ answer: ([String: JSONValue]?, JSONRPCError?)) {
    let value: [String: JSONValue] = ["stage": .string(stage),
        "error_code": answer.1.map { .int($0.code) } ?? .null,
        "error_message": answer.1.map { .string($0.message) } ?? .null,
        "error_data": answer.1?.data.map { .object($0) } ?? .null,
        "response": answer.0.map { .object($0) } ?? .null]
    if let bytes = try? JSONEncoder().encode(value), let line = String(data: bytes, encoding: .utf8) {
        print("DIAGNOSTIC partial100_startup " + line)
    }
}
let runtime = NG2Runtime.shared
let partial100Root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("ngg2-partial100-" + UUID().uuidString)
try FileManager.default.createDirectory(at: partial100Root, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: partial100Root) }
NG2Fake.reset(.walk)
NG2Fake.lock.lock(); NG2Fake.walkPaused = true; NG2Fake.lock.unlock()
ng2_partial100_reset()
let clock = Partial100Clock(), gate = NSLock(), firstB = DispatchSemaphore(value: 0), secondWorker = DispatchSemaphore(value: 0)
let a = partial100Pixels(31), b = partial100Pixels(47), pause = partial100Pixels(11), resumed = partial100Pixels(23)
var source = 23, firstBReleased = false, worker2Entered = false, advanced = false
var workerJobs: [UInt64] = []
let runID = "00000000000000000000000000100100"
func cycle() -> [String: JSONValue] {
    runtime.handle(method: "necro_native_cycle", params: ["run_id": .string(runID), "mode": .string("status"),
        "_necro_owner": .string("fixture-owner")]).0?["payload"]?.objectValue ?? [:]
}
func companion() -> [String: JSONValue] { cycle()["cycle"]?.objectValue ?? [:] }
NG2RuntimeTestHooks.clock = { clock.now() }
NG2RuntimeCycleTestHooks.spoolRoot = partial100Root
NG2RuntimeCycleTestHooks.notificationAuthorization = "authorized"
NG2RuntimeCycleTestHooks.rgba = { _ in
    NG2Fake.lock.lock(); let paused = NG2Fake.walkPaused; NG2Fake.lock.unlock()
    if paused { return pause }
    gate.lock(); let marker = source; gate.unlock(); return marker == 23 ? resumed : marker == 31 ? a : b
}
NG2Fake.cycleTap = { x, y in
    if x == 297 && y == 448 { NG2Fake.lock.lock(); NG2Fake.walkPaused = false; NG2Fake.lock.unlock() }
}
NG2RuntimeObserveTestHooks.afterObserve = {
    let proof = partial100Proof()
    gate.lock(); if proof.ready_for_a == 1 && source == 23 { source = 31 }; gate.unlock()
    gate.lock(); let release = proof.b_while_assessing == 1 && !firstBReleased
    if release { firstBReleased = true }; gate.unlock()
    if release { firstB.signal() }
}
NG2RuntimeCycleTestHooks.beforeClassification = { job in
    gate.lock(); workerJobs.append(job); if job == 2 { worker2Entered = true }; gate.unlock()
    if job == 2 { require(secondWorker.wait(timeout: .now()+20) == .success, "partial100_second_worker_fixture_release") }
}
NG2RuntimeCycleTestHooks.classificationResult = { job, _, result in
    if job == 1 {
        gate.lock(); source = 47; gate.unlock()
        // Park the classification worker, never the serialized control queue,
        // until an actual B observation has retired any prefetch of A.
        require(firstB.wait(timeout: .now()+20) == .success, "partial100_b_observed_while_old_worker_pending")
    }
    ng2_partial100_result(job, result.started_ns, NG2Runtime.now(), &result)
}
NG2RuntimeTestHooks.beforeControlTick = {
    let state = companion()
    gate.lock()
    let advance = !advanced && state["job_id"]?.intValue == 2 && state["pending"]?.boolValue == false &&
        state["outcome"]?.stringValue == "candidate"
    if advance { advanced = true }; gate.unlock()
    if advance { clock.advance(220_000_000) }
}
pump("partial100_normal_prepare_ready") {
    let answer = runtime.handle(method: "necro_native_cycle", params: ["run_id": .string(runID),
        "mode": .string("prepare"), "_necro_owner": .string("fixture-owner")])
    if answer.1 != nil {
        partial100StartupDiagnostic("prepare", answer)
        require(false, "partial100_normal_prepare_request")
    }
    return answer.0?["payload"]?.objectValue?["ready"]?.boolValue == true
}
let started = runtime.handle(method: "necro_native_start", params: ["run_id": .string(runID),
    "profile": .string("normal-1-1-cycle-v1"), "_necro_owner": .string("fixture-owner")])
if started.1 != nil { partial100StartupDiagnostic("start", started) }
require(started.1 == nil, "partial100_actual_runtime_start")
pump("partial100_old_worker_reached_observe_more_and_compared_b") { partial100Proof().compared_b == 1 }
let bound = partial100Proof()
require(bound.seed_count == 1 && bound.prefix > 0 && bound.a_capture > 0 && bound.job_before == 1,
        "partial100_declared_precondition_and_actual_job1")
require(bound.job_after == 2 && bound.pending_after == 1 && bound.state_after == Int32(NG2_CYCLE_HOLD) &&
        bound.capture_after == bound.b_capture && bound.b_capture > bound.a_capture,
        "partial100_latest_item_exposure_binds_job2_before_new_worker")
require(bound.stale_worker_rejected == 1 && bound.stale_result_rejected == 1 && bound.horizon_after <= bound.horizon_before,
        "partial100_old_job_cannot_adopt_or_extend_horizon")
pump("partial100_ordinary_second_worker_entered") { gate.lock(); defer { gate.unlock() }; return worker2Entered }
// Change the live producer after job2 admission: its worker must still own B.
gate.lock(); source = 31; gate.unlock(); secondWorker.signal()
pump("partial100_candidate_terminal_drained") { cycle()["workers_drained"]?.boolValue == true }
let final = companion(), proof = partial100Proof()
require(final["job_id"]?.intValue == 2 && final["capture_id"]?.intValue == Int(bound.b_capture) &&
        final["outcome"]?.stringValue == "candidate" && final["candidate_latched"]?.boolValue == true &&
        final["pending"]?.boolValue == false, "partial100_new_candidate_is_held")
require(proof.ring_calls == 2 && proof.marker.0 == 31 && proof.marker.1 == 47 &&
        proof.raw_hash.0 == partial100Hash(a) && proof.raw_hash.1 == partial100Hash(b) &&
        proof.mode.0 == Int32(NG2_RING_MODE_TARGET_ONLY) && proof.mode.1 == Int32(NG2_RING_MODE_TARGET_ONLY) &&
        proof.items.0 == 1 && proof.items.1 == 3 && proof.protected_count.0 == 5 && proof.protected_count.1 == 11 &&
        proof.scene_hash.0 == ng2_partial100_expected_scene_hash(31) &&
        proof.scene_hash.1 == ng2_partial100_expected_scene_hash(47),
        "partial100_actual_classifier_receives_immutable_b_rgba_and_scene_tuple")
let report = runtime.handle(method: "necro_native_status", params: ["run_id": .string(runID),
    "_necro_owner": .string("fixture-owner")]).0?["report"]?.objectValue ?? [:]
require(report["input_state"]?.intValue == 0 && report["inputs"]?.intValue == 2 && report["moves"]?.intValue == 1 &&
        report["restarts"]?.intValue == 0 && NG2Fake.paths().isEmpty &&
        NG2Fake.taps().allSatisfy { ($0.x == 297 || $0.x == 390) && $0.y == 448 },
        "partial100_no_new_direction_or_restart_after_declared_history_seed")
gate.lock(); let jobs = workerJobs; gate.unlock()
require(jobs == [1,2], "partial100_only_fresh_job2_runs_after_old_job1")
do {
    let spool = try NG2CycleSpool.testRecover(rootURL: partial100Root, runID: runID, owner: "fixture-owner")
    guard let row = try spool.records().last(where: { $0.kind == "checkpoint" }) else {
        require(false, "partial100_new_candidate_checkpoint_exists"); exit(1)
    }
    let envelope = try JSONDecoder().decode([String: JSONValue].self, from: spool.recordBytes(row))
    let payload = envelope["payload"]?.objectValue ?? [:], state = payload["cycle"]?.objectValue ?? [:]
    require(payload["assessment_adopted"]?.boolValue == true && payload["raw_sha256"]?.stringValue == NG2CycleWire.hash(b) &&
            payload["assessment"]?.objectValue?["outcome"]?.stringValue == "candidate" &&
            state["job_id"]?.intValue == 2 && state["capture_id"]?.intValue == Int(bound.b_capture),
            "partial100_durable_assessment_owns_job2_b_not_old_safe_result")
} catch { require(false, "partial100_durable_checkpoint_read") }
print("DIAGNOSTIC partial100 " + "a_capture=\(bound.a_capture) b_capture=\(bound.b_capture) prefix=\(bound.prefix) raw_a=\(proof.raw_hash.0) raw_b=\(proof.raw_hash.1)")
print("PASS TEST100 one partial rebind Runtime callback; declared historical seed, procedural Scenes/RGBA/results, real workers")
