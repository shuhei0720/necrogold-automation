import Foundation
import CoreGraphics

// TEST058 synthetic host integration. The fixed expectations are reviewed in
// docs/tests/test058-world-cases.md; they are not real-game acceptance labels.
struct ShopWorldCase058 {
    let id: String
    let direction: Int32
    let iron: Bool
    var detour = false
    var goodsVariant: Int32 = 0
    var fault = ""
}
func shopPath058(_ direction: Int32) -> [[(point: CGPoint, t: Double)]] {
    let point: CGPoint
    switch direction {
    case 1: point = CGPoint(x: 207, y: 49)
    case 2: point = CGPoint(x: 207, y: 838)
    case 3: point = CGPoint(x: 290, y: 838)
    default: point = CGPoint(x: 124, y: 838)
    }
    return [[(point: point, t: 0), (point: point, t: 0.05)]]
}
func shopScene058(_ bytes: Data, _ label: String) -> NG2Scene {
    var scene = NG2Scene()
    require(bytes.withUnsafeBytes {
        ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, bytes.count, 896*4, &scene)
    } == 0, "shop058_real_RGBA_analysis_"+label)
    return scene
}
func shopTile058(_ scene: NG2Scene, _ x: Int32, _ y: Int32, protected: Bool = false) -> UInt8 {
    let i = Int((y+5)*23+x+11)
    if protected { return withUnsafeBytes(of: scene.protected_cells) { $0[i] } }
    return withUnsafeBytes(of: scene.tiles) { $0[i] }
}
func testShopWorldClock058() {
    let epoch: UInt64 = 10_000_000_000
    let nominal = epoch+SmallShopWorld.period-SmallShopWorld.lead
    let boundaries: [(Int64, Bool)] = [(-10_000_001,false),(-10_000_000,true),
        (0,true),(10_000_000,true),(10_000_001,false)]
    for (delta, accepted) in boundaries {
        let world = SmallShopWorld(direction: 3, iron: false, epoch: epoch)
        world.tap(x: 297, y: 448)
        let actual = world.gesture(shopPath058(3), at: UInt64(Int64(nominal)+delta))
        require(actual == accepted && world.snapshot().moves == (accepted ? 1 : 0),
            "shop058_independent_clock_inclusive_boundary_"+String(delta))
    }
    let world = SmallShopWorld(direction: 3, iron: false, epoch: epoch)
    require(!world.gesture(shopPath058(3), at: nominal), "shop058_paused_direction_rejected")
    world.tap(x: 297, y: 448)
    require(!world.gesture([[(point: CGPoint(x: 290, y: 838), t: 0)]], at: nominal),
        "shop058_malformed_path_rejected")
    require(world.gesture(shopPath058(3), at: nominal), "shop058_first_beat_consumed")
    require(!world.gesture(shopPath058(3), at: nominal+1) && world.snapshot().moves == 1 &&
        world.snapshot().operations.last?.result == "duplicate_beat", "shop058_same_beat_cannot_move_twice")
}
func testShopWorldPixels058() {
    let epoch: UInt64 = 10_000_000_000
    for direction in [Int32(3),2,4,1] {
        for iron in [false,true] {
            let label = String(direction)+(iron ? "_iron" : "_wood")
            let world = SmallShopWorld(direction: direction, iron: iron, epoch: epoch)
            let initial = shopScene058(world.rgba(at: epoch), label+"_initial")
            require(initial.state == 2 && initial.gold_state == 2 && initial.goods == 0 && initial.beat_valid == 1,
                "shop058_initial_live_HUD_gold_no_goods_"+label)
            world.tap(x: 297, y: 448)
            var before = initial
            for operation in 1...4 {
                let at = epoch+UInt64(operation)*SmallShopWorld.period-SmallShopWorld.lead
                require(world.gesture(shopPath058(direction), at: at), "shop058_pixel_world_consumes_"+label)
                var after = shopScene058(world.rgba(at: at+240_000_000), label+"_"+String(operation))
                let state = world.snapshot(), event = state.operations.last!
                if operation == 3 {
                    var motion = NG2Motion()
                    require(event.result == "door_opened" && event.before == event.after &&
                        state.moves == 2 && state.doors == 1 &&
                        ng2_motion(&before, &after, direction, &motion) == 1 && motion.kind == 3 &&
                        motion.dx == 0 && motion.dy == 0,
                        "shop058_closed_probe_has_real_pixels_without_displacement_"+label)
                } else if operation < 3 {
                    var motion = NG2Motion()
                    let vector = SmallShopWorld.vector(direction)
                    require(ng2_motion(&before, &after, direction, &motion) == 1 && motion.kind == 1 &&
                        motion.dx == vector.x && motion.dy == vector.y,
                        "shop058_world_unit_translation_real_motion_"+label)
                }
                require(after.goods == (operation == 4 ? 2 : 0), "shop058_world_occlusion_from_position_"+label)
                before = after
            }
            require(world.snapshot().player == world.gate && world.snapshot().moves == 3,
                "shop058_open_gate_requires_separate_entry_"+label)
        }
    }
    let partial = SmallShopWorld(direction: 3, iron: false, goodsVariant: 1, epoch: epoch)
    partial.tap(x: 297, y: 448)
    for operation in 1...3 {
        require(partial.gesture(shopPath058(3), at: epoch+UInt64(operation)*SmallShopWorld.period-SmallShopWorld.lead),
            "shop058_PF_pixel_world_step")
    }
    let far = shopScene058(partial.rgba(at: epoch+2_000_000_000), "PF_outside_open")
    require(far.goods == 1 && shopTile058(far, 0, -1, protected: true) == 0,
        "shop058_PF_partial_keeps_entry_unprotected")
    let adjacent = SmallShopWorld(direction: 3, iron: false, goodsVariant: 2, epoch: epoch)
    let near = shopScene058(adjacent.rgba(at: epoch), "PA_initial")
    require(near.goods == 1 && shopTile058(near, 0, -1, protected: true) == 1,
        "shop058_PA_partial_protects_next_floor")
}
func shopDiagnose058(_ run: String, _ world: SmallShopWorld, _ label: String) {
    diagnoseFixture(run)
    let previous = fixtureFailureSnapshot
    fixtureFailureSnapshot = {
        var value = previous?() ?? [:]
        let state = world.snapshot()
        value["shop_case"] = .string(label)
        value["shop_world"] = .object(["x": .int(Int(state.player.x)), "y": .int(Int(state.player.y)),
            "moves": .int(state.moves), "doors": .int(state.doors), "digs": .int(state.digs),
            "paused": .bool(state.paused), "resumes": .int(state.resumes), "pauses": .int(state.pauses),
            "operations": .array(state.operations.map { .object(["at_ns": .int(Int($0.at)),
                "direction": .int(Int($0.direction)), "result": .string($0.result), "accepted": .bool($0.accepted),
                "before_x": .int(Int($0.before.x)), "before_y": .int(Int($0.before.y)),
                "after_x": .int(Int($0.after.x)), "after_y": .int(Int($0.after.y))]) })])
        return value
    }
}
func testShopWorldCase058(_ fixture: ShopWorldCase058) {
    NG2Fake.reset(.shop)
    NG2Fake.lock.lock(); let epoch = NG2Fake.phaseBase; NG2Fake.lock.unlock()
    let world = SmallShopWorld(direction: fixture.direction, iron: fixture.iron, detour: fixture.detour,
        goodsVariant: fixture.goodsVariant, epoch: epoch)
    NG2Fake.lock.lock()
    NG2Fake.shopWorld = world
    NG2Fake.shopFailNextDirection = fixture.fault == "unknown"
    NG2Fake.lock.unlock()
    let run = identity()
    shopDiagnose058(run, world, fixture.id)
    NG2RuntimeTestHooks.clock = { NG2Fake.virtualClock() }
    NG2RuntimeTestHooks.beforeCaptureAdmission = { NG2Fake.performBoundaryClockChange() }
    alignInitialFixtureMove(run)
    var heldID: UInt64 = 0
    NG2RuntimeTestHooks.afterTicketReturned = { returned in
        NG2Fake.lock.lock(); NG2Fake.returnedTickets.insert(returned); NG2Fake.lock.unlock()
    }
    NG2RuntimeTestHooks.scheduleTicket = { commandID, callback in
        let current = report(run)
        let events = (current["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
        guard events.contains(where: { $0["id"]?.intValue == Int(commandID) && $0["kind"]?.intValue == 4 }) else { return false }
        let state = world.snapshot()
        // The next reservation follows an actual observation of the previous
        // world operation, rather than an ACK being treated as displacement.
        require(current["moves"]?.intValue == state.moves && current["door_changes"]?.intValue == state.doors &&
            current["terrain_changes"]?.intValue == state.digs && current["x"]?.intValue == Int(state.player.x) &&
            current["y"]?.intValue == Int(state.player.y),
            "shop058_previous_world_operation_confirmed_before_next_input_"+fixture.id)
        let completed = events.filter { $0["kind"]?.intValue == 4 && ($0["begin_ns"]?.intValue ?? 0) > 0 }
        if let operation = state.operations.last, let event = completed.last {
            let kind = operation.result == "moved" ? 1 : operation.result == "door_opened" ? 3 : 4
            require(event["motion"]?.intValue == kind,
                "shop058_previous_real_motion_kind_matches_world_"+fixture.id)
            if kind == 1 {
                require(event["dx"]?.intValue == Int(operation.after.x-operation.before.x) &&
                    event["dy"]?.intValue == Int(operation.after.y-operation.before.y),
                    "shop058_signed_real_unit_motion_matches_world_"+fixture.id)
            } else {
                require(operation.before == operation.after && event["dx"]?.intValue == 0 && event["dy"]?.intValue == 0,
                    "shop058_opening_does_not_credit_a_step_"+fixture.id)
            }
        }
        if fixture.fault == "cancel" {
            heldID = commandID; NG2Fake.holdTicket(commandID, callback); return true
        }
        NG2RuntimeTestHooks.beforeMainAuthority = { admitFirstFixtureMove(run, expectedID: commandID) }
        callback()
        return true
    }
    require(call("necro_native_start", run).1 == nil, "shop058_public_start_"+fixture.id)
    if fixture.fault == "cancel" {
        pump("shop058_CA_first_unsent_move_held", timeout: 20) { heldID != 0 || drained(run) }
        require(heldID != 0 && world.snapshot().operations.isEmpty, "shop058_CA_no_direction_before_cancel")
        require(call("necro_native_cancel", run).1 == nil, "shop058_CA_public_cancel")
        NG2Fake.releaseTicket(heldID)
    }
    pump("shop058_public_terminal_and_drain_"+fixture.id, timeout: 30) {
        _ = call("necro_native_status", run, keepalive: true)
        return drained(run)
    }
    let final = report(run), state = world.snapshot()
    require(state.resumes == 1 && state.operations.allSatisfy { $0.accepted },
        "shop058_independent_world_accepts_only_valid_distinct_beats_"+fixture.id)
    let expectedInputs = fixture.fault == "cancel" || fixture.goodsVariant == 2 ? 0 : fixture.fault == "unknown" ? 1 : fixture.detour ? 7 : 4
    require(state.operations.count == expectedInputs && NG2Fake.paths().count == expectedInputs &&
        final["inputs"]?.intValue == expectedInputs,
        "shop058_fixed_direction_budget_"+fixture.id)
    if fixture.fault == "cancel" {
        NG2Fake.lock.lock(); let returned = NG2Fake.returnedTickets.contains(heldID); NG2Fake.lock.unlock()
        require(returned && state.player == ShopWorldPoint(x: 0, y: 0) && state.pauses == 0 &&
            final["reason"]?.intValue == 2 && final["moves"]?.intValue == 0 &&
            final["x"]?.intValue == 0 && final["y"]?.intValue == 0,
            "shop058_CA_stale_callback_is_inert_without_cleanup")
    } else if fixture.fault == "unknown" {
        require(state.player == ShopWorldPoint(x: 0, y: -1) && state.moves == 1 && state.pauses == 0 &&
            final["moves"]?.intValue == 0 && final["reason"]?.intValue == 11 && final["input_state"]?.intValue == 4 &&
            final["x"]?.intValue == 0 && final["y"]?.intValue == 0 && final["ui_frozen"]?.boolValue == true && runtime.hasLease,
            "shop058_UN_consumed_world_input_is_not_retried_or_credited")
        let touches = NG2Fake.countTouches()
        require(call("necro_native_start", identity()).1 != nil && runtime.leaseError("gesture") != nil &&
            runtime.leaseError("screenshot") != nil && !runtime.beginStreamCapture() &&
            NG2Fake.countTouches() == touches && world.snapshot().operations.count == 1,
            "shop058_UN_no_next_run_UI_or_capture_after_unknown")
    } else {
        require(state.paused && state.pauses == 1 && final["paused"]?.intValue == 1,
            "shop058_single_holding_pause_"+fixture.id)
        let paused = shopScene058(NG2Raster.decode(world.png(at: NG2Fake.virtualClock()))!, fixture.id+"_pause")
        require(paused.state == 1, "shop058_final_pause_pixels_"+fixture.id)
        if fixture.goodsVariant == 2 {
            require(state.player == ShopWorldPoint(x: 0, y: 0) && final["reason"]?.intValue == 13 &&
                final["x"]?.intValue == 0 && final["y"]?.intValue == 0 && final["goods"]?.intValue == 0 &&
                shopScene058(world.rgba(at: NG2Fake.virtualClock()), "PA_kept").goods == 1,
                "shop058_PA_keeps_unobserved_goods_without_direction")
        } else {
            let expectedMoves = fixture.detour ? 5 : 3
            let credited = final["moves"]?.intValue ?? -1
            require(state.player == world.gate && state.moves == expectedMoves && state.doors == 1 &&
                state.digs == (fixture.detour ? 1 : 0) && final["door_changes"]?.intValue == 1 &&
                final["terrain_changes"]?.intValue == state.digs && final["goods"]?.intValue == 1 &&
                final["reason"]?.intValue == 1 && (credited == expectedMoves || credited == expectedMoves-1),
                "shop058_independent_entry_visible_goods_and_opening_counts_"+fixture.id)
            if credited == expectedMoves {
                require(final["x"]?.intValue == Int(world.gate.x) && final["y"]?.intValue == Int(world.gate.y),
                    "shop058_fully_observed_final_position_"+fixture.id)
            } else {
                let sent = (final["events"]?.arrayValue ?? []).compactMap { $0.objectValue }
                    .filter { $0["kind"]?.intValue == 4 && ($0["begin_ns"]?.intValue ?? 0) > 0 }.last!
                let reference = (final["motion_references"]?.arrayValue ?? []).compactMap { $0.objectValue }
                    .first { $0["command_id"] == sent["id"] }
                let beforeLast = state.operations.last!.before
                require(sent["outcome"]?.intValue == 2 && sent["motion"]?.intValue == 0 &&
                    final["x"]?.intValue == Int(beforeLast.x) && final["y"]?.intValue == Int(beforeLast.y) &&
                    reference?["observed_capture_id"]?.intValue == 0 && reference?["primary_motion"]?.intValue == 0 &&
                    reference?["fallback_attempted"]?.boolValue == false && reference?["selected_motion"]?.intValue == 0,
                    "shop058_only_final_goods_latched_unevaluated_ACK_may_lack_credit_"+fixture.id)
            }
            require(shopScene058(world.rgba(at: NG2Fake.virtualClock()), fixture.id+"_visible").goods == 2,
                "shop058_all_three_item_prices_visible_from_world_position_"+fixture.id)
        }
    }
    require(NG2Fake.taps().filter { $0 == CGPoint(x: 390, y: 448) }.count == state.pauses &&
        NG2Fake.countTouches() == state.operations.count+state.resumes+state.pauses,
        "shop058_no_extra_post_goods_direction_or_purchase_"+fixture.id)
    require(call("necro_native_results", run).1 == nil, "shop058_public_results_"+fixture.id)
    let worldRecord: [String: JSONValue] = [
        "case_id": .string(fixture.id), "report": .object(final),
        "world": .object(["x": .int(Int(state.player.x)), "y": .int(Int(state.player.y)),
            "moves": .int(state.moves), "doors": .int(state.doors), "digs": .int(state.digs),
            "paused": .bool(state.paused), "pauses": .int(state.pauses),
            "operations": .array(state.operations.map { operation in .object([
                "at_ns": .int(Int(operation.at)), "direction": .int(Int(operation.direction)),
                "before_x": .int(Int(operation.before.x)), "before_y": .int(Int(operation.before.y)),
                "after_x": .int(Int(operation.after.x)), "after_y": .int(Int(operation.after.y)),
                "result": .string(operation.result), "accepted": .bool(operation.accepted)]) })])]
    if let bytes = try? JSONEncoder().encode(worldRecord), let encoded = String(data: bytes, encoding: .utf8) {
        print("REPORT test058_shop " + encoded)
    } else { require(false, "shop058_actual_report_and_world_log_serializable_"+fixture.id) }
    fixtureFailureSnapshot = nil
    print("PASS shop058 case "+fixture.id+" inputs="+String(state.operations.count)+" world_moves="+String(state.moves))
}
func testShopWorld058Public() {
    testShopWorldClock058()
    testShopWorldPixels058()
    let cases: [ShopWorldCase058] = [
        .init(id: "N-W", direction: 3, iron: false), .init(id: "N-I", direction: 3, iron: true),
        .init(id: "E-W", direction: 2, iron: false), .init(id: "E-I", direction: 2, iron: true),
        .init(id: "S-W", direction: 4, iron: false), .init(id: "S-I", direction: 4, iron: true),
        .init(id: "W-W", direction: 1, iron: false), .init(id: "W-I", direction: 1, iron: true),
        .init(id: "DN", direction: 3, iron: false, detour: true),
        .init(id: "DE", direction: 2, iron: true, detour: true),
        .init(id: "DS", direction: 4, iron: false, detour: true),
        .init(id: "DW", direction: 1, iron: true, detour: true),
        .init(id: "PF", direction: 3, iron: false, goodsVariant: 1),
        .init(id: "PA", direction: 3, iron: false, goodsVariant: 2),
        .init(id: "CA", direction: 3, iron: false, fault: "cancel"),
        .init(id: "UN", direction: 3, iron: false, fault: "unknown")]
    require(cases.count == 16 && cases.last?.id == "UN", "shop058_fixed_matrix_unknown_is_last")
    for fixture in cases { testShopWorldCase058(fixture) }
    print("PASS production Runtime public API/TEST058 independent synthetic shop world16")
}
