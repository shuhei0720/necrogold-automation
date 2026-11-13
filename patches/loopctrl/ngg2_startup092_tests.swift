// TEST092 STARTUP HOST METHOD BEGIN.
    // Negative setup only: no controller decision, input or outcome is made.
    func test092ChangeInitialCapture(_ id: String, field: String) -> Bool {
        guard let run = lock.ng2Locked({ current }), run.id == id else { return false }
        return run.lock.ng2Locked {
            guard !run.stopped, run.cancelReason == 0 else { return false }
            if field == "prefix" { run.prefix = 1 }
            else if field == "inflight" { run.inFlight = true }
            else if field == "pid" { run.expectedPID = 0 }
            else { return false }
            return true
        }
    }
// TEST092 STARTUP HOST METHOD END.

// TEST092 STARTUP FIXTURE BEGIN.
final class Test092Clock {
    private let lock = NSLock()
    private var value: UInt64 = 1_000_000_000_000
    func now() -> UInt64 { lock.lock(); defer { lock.unlock() }; return value }
    func advance(_ ns: UInt64) { lock.lock(); value += ns; lock.unlock() }
}
final class Test092Flag {
    private let lock = NSLock()
    private var value = false
    func set() { lock.lock(); value = true; lock.unlock() }
    func get() -> Bool { lock.lock(); defer { lock.unlock() }; return value }
}
func test092Portrait(width: Int = 414, height: Int = 896, orientation: Int? = 1) -> Data {
    let bytes = Data(count: width*height*4)
    let provider = CGDataProvider(data: bytes as CFData)!
    let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
        bytesPerRow: width*4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
        bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
            CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
        decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
    let output = NSMutableData()
    let destination = CGImageDestinationCreateWithData(output, "public.tiff" as CFString, 1, nil)!
    let properties: CFDictionary? = orientation.map { [kCGImagePropertyOrientation: $0] as CFDictionary }
    CGImageDestinationAddImage(destination, image, properties)
    require(CGImageDestinationFinalize(destination), "test092_portrait_fixture_encoding")
    return output as Data
}
let test092Landscape = NG2Raster.png(test081Floor())!
func test092Configure(_ bytes: Data?, error: String? = nil) -> Test092Clock {
    NG2Fake.reset(.reply)
    let clock = Test092Clock()
    NG2RuntimeTestHooks.clock = { clock.now() }
    NG2Fake.lock.lock()
    NG2Fake.replyData = bytes; NG2Fake.replyError = error
    NG2Fake.captureTimeProvider = { clock.advance(1_000_000); return clock.now() }
    NG2Fake.lock.unlock()
    return clock
}
func test092Failure(_ id: String) -> [String: JSONValue]? { report(id)["capture_failure"]?.objectValue }
func test092Start(_ id: String) {
    diagnoseFixture(id)
    require(call("necro_native_start", id).1 == nil, "test092_public_start")
}
func test092Clean(_ id: String) {
    cancelDrain(id)
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = nil
    NG2Fake.lock.lock(); NG2Fake.beforeForegroundQuery = nil; NG2Fake.lock.unlock()
    fixtureFailureSnapshot = nil
}
// The no-input requirement ends at the first independently normal raster.
// Its controller may legitimately pause after observing that raster. Observe
// the boundary before C receives it instead of forbidding every later input.
func test092FirstNormalFence(minimumCaptureID: UInt64) -> Test092Flag {
    let seen = Test092Flag()
    NG2RuntimeTestHooks.beforeAnalysisFrameCommit = { capture, start, end, prefix, stable in
        guard !seen.get() else { return }
        require(capture >= minimumCaptureID && start < end && prefix == 0 && stable &&
            NG2Fake.countTouches() == 0 && NG2Fake.countActivations() == 1,
            "test092_portrait_wait_has_no_input_before_first_normal_raster_reaches_C")
        seen.set()
    }
    return seen
}
func test092NormalSources(_ id: String, excluding rejected: Set<Int>) -> Bool {
    let value = report(id)
    let captures = (value["captures"]?.arrayValue ?? []).compactMap { $0.objectValue?["id"]?.intValue }
    let events = (value["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
    return events.filter { ($0["begin_ns"]?.intValue ?? 0) > 0 }.allSatisfy {
        guard let source = $0["source_capture_id"]?.intValue else { return false }
        return captures.contains(source) && !rejected.contains(source)
    }
}
func test092FirstPortraitWaitsForLandscape() {
    for orientation in [Int?(1), nil] { for scale in [1, 2] {
        let portrait = test092Portrait(width: 414*scale, height: 896*scale, orientation: orientation)
        _ = test092Configure(portrait)
        let id = identity()
        let normal = test092FirstNormalFence(minimumCaptureID: 2)
        NG2RuntimeTestHooks.beforeCaptureAdmission = {
            if NG2Fake.countRequests() > 0 {
                NG2Fake.lock.lock(); NG2Fake.replyData = test092Landscape; NG2Fake.lock.unlock()
            }
        }
        test092Start(id)
        pump("test092_first_portrait_reaches_terminal_or_normal_raster") {
            (report(id)["analyzed_capture_count"]?.intValue ?? 0) > 0 || drained(id)
        }
        let raster = report(id)["raster_samples"]?.arrayValue?.first?.objectValue
        require(normal.get() && (report(id)["analyzed_capture_count"]?.intValue ?? 0) > 0 &&
            test092Failure(id) == nil && NG2Fake.countRequests() >= 2 && NG2Fake.countActivations() == 1 &&
            raster?["source_width"]?.intValue == 896 && raster?["source_height"]?.intValue == 414 &&
            raster?["orientation"]?.intValue == 1 &&
            test092NormalSources(id, excluding: [1]),
            "test092_first_portrait_waits_for_landscape_without_rotation_input_or_relaunch")
        test092Clean(id)
    } }
    print("PASS TEST092 initial portrait waits for independently normal landscape without input")
}
func test092StartupBounds() {
    let portrait = test092Portrait()
    _ = test092Configure(portrait)
    var id = identity(); test092Start(id)
    pump("test092_finite_portrait_count_drains", timeout: 30) { drained(id) }
    require(NG2Fake.countRequests() == 64 && NG2Fake.countTouches() == 0 &&
        report(id)["reason"]?.intValue == 20 && report(id)["analyzed_capture_count"]?.intValue == 0 &&
        test092Failure(id)?["capture_id"]?.intValue == 64,
        "test092_portrait_count_is_finite_and_last_original_failure_is_reported")
    test092Clean(id)
    let clock = test092Configure(portrait)
    id = identity()
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() == 1 {
            clock.advance(2_998_000_000)
        }
    }
    test092Start(id)
    pump("test092_original_deadline_equality_drains") { drained(id) }
    require(NG2Fake.countRequests() == 2 && report(id)["reason"]?.intValue == 20 &&
        test092Failure(id)?["capture_id"]?.intValue == 2 && NG2Fake.countTouches() == 0,
        "test092_original_activation_deadline_is_not_renewed")
    test092Clean(id)
    let admissionClock = test092Configure(portrait)
    id = identity()
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() == 1 { admissionClock.advance(2_999_000_000) }
    }
    test092Start(id)
    pump("test092_no_request_at_original_deadline") { drained(id) }
    require(NG2Fake.countRequests() == 1 && test092Failure(id)?["capture_id"]?.intValue == 1 &&
        report(id)["reason"]?.intValue == 20 && NG2Fake.countTouches() == 0,
        "test092_deadline_equality_does_not_admit_another_capture")
    test092Clean(id)
    print("PASS TEST092 original three second deadline and sixty four portrait limit")
}
func test092LateAdmittedNormalKeepsCaptureContract() {
    let clock = test092Configure(test092Portrait())
    let id = identity()
    let normal = test092FirstNormalFence(minimumCaptureID: 2)
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() == 1 {
            clock.advance(2_998_000_000)
            NG2Fake.lock.lock(); NG2Fake.replyData = test092Landscape; NG2Fake.lock.unlock()
        }
    }
    NG2Fake.lock.lock()
    NG2Fake.captureTimeProvider = {
        clock.advance(NG2Fake.countRequests() == 1 ? 1_000_000_000 : 1_000_000)
        return clock.now()
    }
    NG2Fake.lock.unlock()
    test092Start(id)
    pump("test092_admitted_normal_raster_finishes_after_startup_deadline") {
        (report(id)["analyzed_capture_count"]?.intValue ?? 0) > 0 || drained(id)
    }
    require(normal.get() && (report(id)["analyzed_capture_count"]?.intValue ?? 0) > 0 && test092Failure(id) == nil &&
        NG2Fake.countRequests() >= 2 && test092NormalSources(id, excluding: [1]),
        "test092_normal_reply_already_admitted_before_deadline_retains_original_capture_contract")
    test092Clean(id)
    print("PASS TEST092 already admitted normal reply retains original capture completion contract")
}
func test092OtherFailuresRemainImmediate() {
    let fixtures: [(Data?, String?, String, String)] = [
        (NG2Fake.squarePNG, nil, "metadata", "aspect"),
        (Data(), nil, "source", "encoded_empty"),
        (nil, "direct capture failed", "reply", "capture_failed"),
        (test092Portrait(orientation: 3), nil, "metadata", "aspect"),
        (test092Portrait(width: 896, height: 414, orientation: 8), nil, "metadata", "aspect")]
    for (bytes, error, stage, code) in fixtures {
        _ = test092Configure(bytes, error: error)
        let id = identity(); test092Start(id)
        pump("test092_other_failure_drains") { drained(id) }
        require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 &&
            report(id)["reason"]?.intValue == 20 && test092Failure(id)?["stage"]?.stringValue == stage &&
            test092Failure(id)?["code"]?.stringValue == code,
            "test092_other_metadata_source_reply_and_EXIF_failures_are_not_retried")
        test092Clean(id)
    }
    print("PASS TEST092 square source reply and other EXIF failures retain immediate stop")
}
func test092NormalAndAnalysisFailuresEndWait() {
    _ = test092Configure(test092Landscape)
    let portrait = test092Portrait()
    var id = identity()
    let normal = test092FirstNormalFence(minimumCaptureID: 1)
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() > 0 {
            let deadline = Date().addingTimeInterval(2)
            while (report(id)["analyzed_capture_count"]?.intValue ?? 0) == 0 && Date() < deadline {
                Thread.sleep(forTimeInterval: 0.001)
            }
            NG2Fake.lock.lock(); NG2Fake.replyData = portrait; NG2Fake.lock.unlock()
        }
    }
    test092Start(id)
    pump("test092_portrait_after_normal_raster_drains") { drained(id) }
    require(normal.get() && NG2Fake.countRequests() == 2 && report(id)["analyzed_capture_count"]?.intValue == 1 &&
        report(id)["reason"]?.intValue == 20 && test092Failure(id)?["capture_id"]?.intValue == 2 &&
        test092NormalSources(id, excluding: [2]), "test092_first_normal_raster_permanently_ends_startup_wait")
    test092Clean(id)
    _ = test092Configure(test092Landscape)
    id = identity(); NG2RuntimeTestHooks.analysisRGBA = { _ in Data() }
    test092Start(id)
    pump("test092_analysis_failure_drains") { drained(id) }
    require(NG2Fake.countRequests() == 1 && test092Failure(id)?["stage"]?.stringValue == "analysis" &&
        test092Failure(id)?["code"]?.stringValue == "invalid_rgba" && NG2Fake.countTouches() == 0,
        "test092_analysis_failure_is_never_treated_as_pending_presentation")
    test092Clean(id)
    print("PASS TEST092 normal raster permanently ends wait and analysis failure remains immediate")
}
func test092AuthorityFences() {
    for fault in ["cancel", "owner", "lock", "foreground", "generation", "stale", "deadline"] {
        let clock = test092Configure(test092Portrait())
        let id = identity(), entered = Test092Flag()
        NG2Fake.lock.lock()
        NG2Fake.beforeForegroundQuery = {
            guard NG2Fake.countRequests() > 0, !entered.get() else { return }
            entered.set()
            if fault == "cancel" { _ = call("necro_native_cancel", id) }
            else if fault == "owner" { RemoteSession.shared.paused = true }
            else if fault == "lock" { LockStateMonitor.monitor.isLocked = true }
            else if fault == "foreground" { NG2Fake.lock.lock(); NG2Fake.frontPID = 41; NG2Fake.lock.unlock() }
            else if fault == "generation" { require(runtime.testFailureGeneration(id, advance: true) != nil, "test092_advance_generation") }
            else if fault == "stale" { clock.advance(1_000_000_001) }
            else { clock.advance(3_000_000_000) }
        }
        NG2Fake.lock.unlock()
        test092Start(id)
        pump("test092_fresh_query_is_reached") { entered.get() || drained(id) }
        require(entered.get(), "test092_portrait_rechecks_actual_foreground")
        if fault == "generation" { _ = call("necro_native_cancel", id) }
        pump("test092_lost_authority_query_drains") { drained(id) }
        let reason = report(id)["reason"]?.intValue
        let expected = ["cancel": 2, "owner": 5, "lock": 4, "foreground": 3]
        require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 &&
            NG2Fake.countActivations() == 1 && (expected[fault] == nil || reason == expected[fault]),
            "test092_query_return_cannot_revive_cancel_owner_lock_foreground_or_stale_authority")
        if fault == "generation" {
            require(test092Failure(id) == nil, "test092_old_generation_failure_does_not_mutate_current_run")
        }
        RemoteSession.shared.paused = false; LockStateMonitor.monitor.isLocked = false
        test092Clean(id)
    }
    print("PASS TEST092 fresh query rejects cancellation owner lock foreground generation and stale time")
}
func test092QueuedQueryCancelRetainsLease() {
    _ = test092Configure(test092Portrait())
    let id = identity(), admitted = Test092Flag(), release = DispatchSemaphore(value: 0)
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() == 0 {
            admitted.set(); require(release.wait(timeout: .now()+5) == .success, "test092_release_first_capture")
        }
    }
    test092Start(id)
    pump("test092_bootstrap_reaches_first_capture") { admitted.get() }
    release.signal()
    let deadline = Date().addingTimeInterval(3)
    while report(id)["main_ticket_outstanding"]?.boolValue != true && Date() < deadline {
        Thread.sleep(forTimeInterval: 0.002)
    }
    require(report(id)["main_ticket_outstanding"]?.boolValue == true, "test092_portrait_query_is_queued_on_main")
    _ = call("necro_native_cancel", id)
    require(!drained(id) && call("necro_native_start", identity()).1 != nil,
        "test092_queued_query_keeps_lease_until_actual_main_return")
    pump("test092_cancelled_main_query_drains") { drained(id) }
    require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 && NG2Fake.countActivations() == 1 &&
        test092Failure(id) == nil, "test092_queued_cancel_has_no_late_query_retry_input_or_failure")
    test092Clean(id)
    print("PASS TEST092 queued foreground query cancellation retains lease until main returns")
}
func test092TimeoutStillDrainsExactCallback() {
    _ = test092Configure(test092Portrait())
    let id = identity()
    NG2RuntimeTestHooks.beforeCaptureAdmission = {
        if NG2Fake.countRequests() == 1 { NG2Fake.lock.lock(); NG2Fake.mode = .hold; NG2Fake.lock.unlock() }
    }
    test092Start(id)
    pump("test092_second_capture_timeout_is_visible", timeout: 4) { report(id)["capture_timed_out"]?.boolValue == true }
    require(!drained(id) && call("necro_native_start", identity()).1 != nil && NG2Fake.countRequests() == 2,
        "test092_timed_out_capture_retains_worker_and_lease")
    NG2Fake.release()
    pump("test092_exact_timed_out_callback_drains") { drained(id) }
    require(report(id)["reason"]?.intValue == 6 && NG2Fake.countTouches() == 0 &&
        test092Failure(id) == nil, "test092_timeout_is_not_hidden_by_startup_portrait_wait")
    test092Clean(id)
    print("PASS TEST092 timeout retains exact callback drain and original capture stop")
}
func test092StableInitialGuards() {
    for field in ["prefix", "inflight", "pid"] {
        _ = test092Configure(test092Portrait())
        let id = identity()
        NG2RuntimeTestHooks.beforeCaptureAdmission = {
            if NG2Fake.countRequests() == 0 {
                require(runtime.test092ChangeInitialCapture(id, field: field), "test092_initial_guard_setup")
                NG2RuntimeTestHooks.beforeCaptureAdmission = nil
            }
        }
        test092Start(id)
        pump("test092_invalid_initial_capture_drains") { drained(id) }
        require(NG2Fake.countRequests() == 1 && NG2Fake.countTouches() == 0 &&
            report(id)["analyzed_capture_count"]?.intValue == 0,
            "test092_changed_prefix_inflight_or_expected_pid_cannot_supply_retry_authority")
        test092Clean(id)
    }
    print("PASS TEST092 initial prefix inflight and expected PID boundaries remain strict")
}
// TEST092 STARTUP FIXTURE END.
