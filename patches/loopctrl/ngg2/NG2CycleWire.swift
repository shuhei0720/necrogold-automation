// TEST094 closed read-only projection. No method here grants input authority.
import Foundation
import CryptoKit

enum NG2CycleWire {
    static let schema = "ngg2-cycle-v1"
    static let profile = "normal-1-1-cycle-v1"
    static let chunkBytes = 64 * 1024
    enum Failure: Error { case invalidAssessment, invalidJSON }
    // Locally selected immutable protocol identity. Reply data never selects it.
    struct ProtocolSpec: Equatable {
        let profile, schema, method: String
        static let standard = ProtocolSpec(profile: NG2CycleWire.profile, schema: NG2CycleWire.schema,
            method: "necro_native_cycle")
        static let irregular = ProtocolSpec(profile: "normal-1-1-irregular-v1",
            schema: "ngg2-irregular-cycle-v1", method: "necro_native_irregular")
        static func forProfile(_ profile: String) -> ProtocolSpec? {
            profile == standard.profile ? standard : (profile == irregular.profile ? irregular : nil)
        }
    }

    static func number(_ value: UInt64) -> JSONValue { .int(Int(min(value, UInt64(Int64.max)))) }
    static func integer(_ value: Int32) -> JSONValue { .int(Int(value)) }
    static func hash(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    static func envelope(runID: String, mode: String, payload: [String: JSONValue],
                         spec: ProtocolSpec = .standard) -> [String: JSONValue] {
        ["schema": .string(spec.schema), "run_id": .string(runID), "profile": .string(spec.profile),
         "mode": .string(mode), "payload": .object(payload)]
    }
    static func canonical(_ object: [String: JSONValue]) throws -> Data {
        let encoded = try JSONEncoder().encode(object)
        guard let value = try JSONSerialization.jsonObject(with: encoded) as? [String: Any],
              JSONSerialization.isValidJSONObject(value) else { throw Failure.invalidJSON }
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    static func object(_ object: [String: JSONValue]) throws -> [String: Any] {
        guard let value = try JSONSerialization.jsonObject(with: canonical(object)) as? [String: Any] else {
            throw Failure.invalidJSON
        }
        return value
    }
    static func decode(_ object: [String: Any]) throws -> [String: JSONValue] {
        let bytes = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
        return try JSONDecoder().decode([String: JSONValue].self, from: bytes)
    }
    private static func ints<T>(_ tuple: T, count: Int) -> [JSONValue] {
        withUnsafeBytes(of: tuple) { raw in
            Array(raw.bindMemory(to: Int32.self).prefix(count)).map { .int(Int($0)) }
        }
    }
    private static func boxes<T>(_ tuple: T, count: Int) -> JSONValue {
        let values = ints(tuple, count: count * 4)
        return .array((0..<count).map { .array(Array(values[($0 * 4)..<($0 * 4 + 4)])) })
    }
    private static func doubles<T>(_ tuple: T, count: Int) throws -> [JSONValue] {
        try withUnsafeBytes(of: tuple) { raw in
            try Array(raw.bindMemory(to: Double.self).prefix(count)).map { value in
                guard value.isFinite else { throw Failure.invalidAssessment }
                return .double(value)
            }
        }
    }
    static func outcome(_ value: UInt32) -> String {
        value <= 3 ? ["unknown", "candidate", "target", "negative"][Int(value)] : "unknown"
    }
    static func assessmentStatus(_ value: UInt32) -> String {
        value <= 5 ? ["ok", "cancelled", "deadline", "invalid", "allocation", "kernel"][Int(value)] : "invalid"
    }
    static func coverage(_ value: UInt32) -> String {
        value <= 2 ? ["unknown", "incomplete", "complete"][Int(value)] : "unknown"
    }
    static func companion(_ value: NG2ControllerCycleStatus) -> [String: JSONValue] {
        let names = ["search", "hold", "assess", "observe_more", "negative_pause", "negative_persist", "negative_restart", "held", "done"]
        return ["abi_version": .int(Int(value.abi_version)),
            "state": .string(names[min(max(Int(value.state), 0), 8)]),
            "outcome": .string(outcome(UInt32(max(value.outcome, 0)))),
            "assessment_status": .string(assessmentStatus(UInt32(max(value.status, 0)))),
            "coverage": .string(coverage(UInt32(max(value.coverage, 0)))),
            "partial": .bool(value.partial != 0), "pending": .bool(value.pending != 0),
            "completed_shops": .int(Int(value.completed_shops)), "candidate_latched": .bool(value.candidate_latched != 0),
            "full_seen": .bool(value.full_seen != 0), "level_id": number(value.level_id), "job_id": number(value.job_id),
            "capture_id": number(value.capture_id), "capture_start_ns": number(value.capture_start_ns),
            "prefix": number(value.prefix), "deadline_ns": number(value.deadline_ns),
            "hold_started_ns": number(value.hold_started_ns), "worker_started_ns": number(value.worker_started_ns),
            "assessment_ns": number(value.assessment_ns), "durable_ns": number(value.durable_ns),
            "pause_source_capture_id": number(value.pause_source_capture_id), "pause_capture_id": number(value.pause_capture_id),
            "restart_command_id": number(value.restart_command_id), "next_floor_capture_id": number(value.next_floor_capture_id),
            "intent_ns": number(value.intent_ns), "outcome_ns": number(value.outcome_ns),
            "release_after_ns": number(value.release_after_ns), "continuation_deadline_ns": number(value.continuation_deadline_ns),
            "queued_capture_id": number(value.queued_capture_id), "queued_capture_start_ns": number(value.queued_capture_start_ns),
            "queued_prefix": number(value.queued_prefix)]
    }
    static func irregular(_ value: NG2ControllerIrregularStatus) throws -> [String: JSONValue] {
        let kinds = ["none", "stalled", "death"]
        let stages = ["idle", "quiesce", "checkpoint", "pause", "death_continue", "wait_menu",
                      "restart_ready", "wait_restart", "outcome", "held"]
        let reasons = ["none", "menu_unrecognized", "deadline", "storage", "candidate", "unknown_input",
                       "invalid_ui", "classification", "baseline_unavailable", "limit", "control_invalid"]
        let clocks = [value.episode_id, value.trigger_capture_id, value.before_capture_id,
            value.live_baseline_capture_id, value.prefix, value.trigger_ns, value.parent_deadline_ns,
            value.proof_capture_id, value.continue_command_id, value.continue_capture_id,
            value.pause_capture_id, value.restart_command_id, value.next_floor_capture_id,
            value.durable_ns, value.continue_intent_ns, value.continue_outcome_ns,
            value.restart_intent_ns, value.outcome_ns]
        guard value.abi_version == 1, value.struct_size == UInt32(MemoryLayout<NG2ControllerIrregularStatus>.size),
              value.enabled == 0 || value.enabled == 1, (0...2).contains(value.kind),
              (0...9).contains(value.stage), (0...10).contains(value.held_reason),
              value.episodes >= 0, clocks.allSatisfy({ $0 < UInt64(Int64.max) }) else {
            throw Failure.invalidJSON
        }
        let names = ["episode_id", "trigger_capture_id", "before_capture_id", "live_baseline_capture_id", "prefix",
            "trigger_ns", "parent_deadline_ns", "proof_capture_id", "continue_command_id", "continue_capture_id",
            "pause_capture_id", "restart_command_id", "next_floor_capture_id", "durable_ns", "continue_intent_ns",
            "continue_outcome_ns", "restart_intent_ns", "outcome_ns"]
        var answer: [String: JSONValue] = ["abi_version": .int(1), "enabled": .bool(value.enabled == 1),
            "kind": .string(kinds[Int(value.kind)]), "stage": .string(stages[Int(value.stage)]),
            "held_reason": .string(reasons[Int(value.held_reason)]), "episodes": .int(Int(value.episodes))]
        for (name, clock) in zip(names, clocks) { answer[name] = number(clock) }
        return answer
    }
    static func irregularObservation(_ value: NG2IrregularObservation) throws -> [String: JSONValue] {
        guard value.abi_version == 1, value.struct_size == UInt32(MemoryLayout<NG2IrregularObservation>.size),
              (0...3).contains(value.kind), (0...2).contains(value.matches), value.enemy_mask <= 15 else {
            throw Failure.invalidJSON
        }
        var answer: [String: JSONValue] = ["abi_version": .int(1), "struct_size": .int(Int(value.struct_size)),
            "kind": integer(value.kind), "glyph_intersection": integer(value.glyph_intersection),
            "glyph_union": integer(value.glyph_union), "hud_mask": integer(value.hud_mask),
            "empty_hearts": integer(value.empty_hearts), "matches": integer(value.matches),
            "left": integer(value.left), "top": integer(value.top), "width": integer(value.width),
            "height": integer(value.height), "enemy_mask": .int(Int(value.enemy_mask))]
        let hearts: [(String, [JSONValue])] = [("heart_inter", ints(value.heart_inter, count: 3)),
            ("heart_union", ints(value.heart_union, count: 3)), ("heart_red", ints(value.heart_red, count: 3)),
            ("heart_dark", ints(value.heart_dark, count: 3)), ("heart_bright", ints(value.heart_bright, count: 3))]
        let enemies: [(String, [JSONValue])] = [("enemy_matches", ints(value.enemy_matches, count: 4)),
            ("enemy_inter", ints(value.enemy_inter, count: 4)), ("enemy_union", ints(value.enemy_union, count: 4)),
            ("enemy_left", ints(value.enemy_left, count: 4)), ("enemy_top", ints(value.enemy_top, count: 4)),
            ("enemy_body_luma", ints(value.enemy_body_luma, count: 4)),
            ("enemy_body_saturation", ints(value.enemy_body_saturation, count: 4)),
            ("enemy_red_outside", ints(value.enemy_red_outside, count: 4)),
            ("enemy_heart_count", ints(value.enemy_heart_count, count: 4)),
            ("enemy_width", ints(value.enemy_width, count: 4)), ("enemy_height", ints(value.enemy_height, count: 4))]
        for (name, array) in hearts + enemies { answer[name] = .array(array) }
        return answer
    }
    private static func slot(_ value: NG2RingSlot, targetOnly: Bool) throws -> JSONValue {
        let scores = [value.icon_score, value.icon_upper_bound, value.word_iou, value.word_coverage,
                      value.non_target_icon_score, value.non_target_name_iou, value.non_target_name_coverage,
                      value.ignored_icon_score, value.ignored_gold_iou, value.ignored_gold_coverage,
                      value.ignored_dark_iou, value.ignored_dark_coverage]
        guard scores.allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 1.000001 }),
              value.outcome <= 4, value.kind <= (targetOnly ? 3 : 2), value.non_target_conflict <= 1, value.icon_score_exact <= 1,
              value.word_present == 0 || value.word_present == 1 else { throw Failure.invalidAssessment }
        return .object(["cx": integer(value.cx), "sy": integer(value.sy), "slot": integer(value.slot),
            "word_present": .bool(value.word_present == 1), "icon_score": .double(value.icon_score),
            "icon_score_exact": .bool(value.icon_score_exact == 1), "icon_upper_bound": .double(value.icon_upper_bound),
            "word_iou": .double(value.word_iou), "word_coverage": .double(value.word_coverage),
            "icon_box": .array(ints(value.icon_box, count: 4)), "word_box": .array(ints(value.word_box, count: 4)),
            "outcome": .string(["unknown", "candidate", "target", "non_target", "ignored_container"][Int(value.outcome)]),
            "non_target_id": .int(Int(value.non_target_id)),
            "non_target_icon_score": .double(value.non_target_icon_score),
            "non_target_name_iou": .double(value.non_target_name_iou),
            "non_target_name_coverage": .double(value.non_target_name_coverage),
            "non_target_icon_box": .array(ints(value.non_target_icon_box, count: 4)),
            "non_target_name_box": .array(ints(value.non_target_name_box, count: 4)),
            "non_target_conflict": .bool(value.non_target_conflict == 1),
            "kind": .string(["unknown", "known_non_target", "ignored_closed_container", "generic_non_target"][Int(value.kind)]),
            "ignored_container_id": .int(Int(value.ignored_container_id)),
            "ignored_icon_score": .double(value.ignored_icon_score),
            "ignored_gold_iou": .double(value.ignored_gold_iou),
            "ignored_gold_coverage": .double(value.ignored_gold_coverage),
            "ignored_dark_iou": .double(value.ignored_dark_iou),
            "ignored_dark_coverage": .double(value.ignored_dark_coverage),
            "ignored_icon_box": .array(ints(value.ignored_icon_box, count: 4))])
    }
    private static func endcap(_ value: NG2RingEndcap) -> JSONValue {
        .object(["box": .array(ints(value.box, count: 4)), "r": integer(value.r), "g": integer(value.g),
            "b": integer(value.b), "spread": integer(value.spread), "black_count": integer(value.black_count),
            "count": integer(value.count), "bright_count": integer(value.bright_count),
            "price_ink_count": integer(value.price_ink_count), "floor_full": integer(value.floor_full),
            "floor_upper": integer(value.floor_upper), "floor_lower": integer(value.floor_lower)])
    }
    private static func certificate(_ value: NG2RingCoverage) throws -> JSONValue {
        guard value.merchant_score.isFinite, value.merchant_coverage.isFinite else { throw Failure.invalidAssessment }
        return .object(["layout_version": .int(Int(value.layout_version)),
            "accepted_rows": integer(value.accepted_rows), "observed_items": integer(value.observed_items),
            "observed_prices": integer(value.observed_prices), "unmatched_items": integer(value.unmatched_items),
            "unmatched_prices": integer(value.unmatched_prices), "scene_state": integer(value.scene_state),
            "scene_goods": integer(value.scene_goods), "actual_gold_cells": integer(value.actual_gold_cells),
            "row": .array(ints(value.row, count: 2)), "strip_box": .array(ints(value.strip_box, count: 4)),
            "merchant_box": .array(ints(value.merchant_box, count: 4)), "sign_boxes": boxes(value.sign_boxes, count: 2),
            "merchant_score": .double(value.merchant_score), "merchant_coverage": .double(value.merchant_coverage),
            "sign_iou": .array(try doubles(value.sign_iou, count: 2)),
            "sign_coverage": .array(try doubles(value.sign_coverage, count: 2)),
            "endcaps": .array([endcap(value.endcaps.0), endcap(value.endcaps.1)]),
            "item_boxes": boxes(value.item_boxes, count: 3), "name_boxes": boxes(value.name_boxes, count: 3),
            "price_boxes": boxes(value.price_boxes, count: 3),
            "policy_version": .int(Int(value.policy_version)), "failure_flags": .int(Int(value.failure_flags)),
            "board_mode": .int(Int(value.board_mode)),
            "row_index": integer(value.row_index), "non_target_items": integer(value.non_target_items),
            "ignored_containers": integer(value.ignored_containers), "unmatched_boards": integer(value.unmatched_boards),
            "board_boxes": boxes(value.board_boxes, count: 2), "board_counts": .array(ints(value.board_counts, count: 2)),
            "board_edge_counts": boxes(value.board_edge_counts, count: 2),
            "board_corner_counts": boxes(value.board_corner_counts, count: 2),
            "board_exterior_count": .array(ints(value.board_exterior_count, count: 2))])
    }
    static func assessment(_ original: NG2RingResult, mode: Int32 = 0) throws -> [String: JSONValue] {
        let targetOnly = mode == Int32(NG2_RING_MODE_TARGET_ONLY)
        var value = original
        guard value.abi == 1, Int(value.size) == MemoryLayout<NG2RingResult>.size,
              value.status <= 5, value.outcome <= 3, value.coverage <= 2,
              (0...4).contains(Int(value.row_count)), (0...12).contains(Int(value.partial_count)),
              value.selected_row >= -1, value.selected_row < max(1, value.row_count),
              value.selected_partial >= -1, value.selected_partial < max(1, value.partial_count),
              value.partial_safe_no_positive <= 1, value.finished_ns >= value.started_ns,
              value.finished_ns < UInt64(Int64.max), value.checks < UInt64(Int64.max) else {
            throw Failure.invalidAssessment
        }
        let rowCount = Int(value.row_count), partialCount = Int(value.partial_count)
        let rows: [JSONValue] = try withUnsafePointer(to: &value.rows) { pointer in
            try pointer.withMemoryRebound(to: NG2RingRow.self, capacity: 4) { rows in
                try (0..<rowCount).map { index in
                    let row = rows[index]
                    guard row.outcome <= 3 else { throw Failure.invalidAssessment }
                    return .object(["left": integer(row.left), "sy": integer(row.sy),
                        "word_slot": integer(row.word_slot), "outcome": .string(outcome(row.outcome)),
                        "reason": .int(Int(row.reason)),
                        "slots": .array(try [slot(row.slots.0, targetOnly: targetOnly), slot(row.slots.1, targetOnly: targetOnly),
                                              slot(row.slots.2, targetOnly: targetOnly)])])
                }
            }
        }
        let partial: [JSONValue] = try withUnsafePointer(to: &value.partial) { pointer in
            try pointer.withMemoryRebound(to: NG2RingSlot.self, capacity: 12) { items in
                try (0..<partialCount).map { try slot(items[$0], targetOnly: targetOnly) }
            }
        }
        return ["status": .string(assessmentStatus(value.status)), "outcome": .string(outcome(value.outcome)),
            "coverage": .string(coverage(value.coverage)), "reason": .int(Int(value.reason)),
            "row_count": integer(value.row_count), "selected_row": integer(value.selected_row),
            "partial_count": integer(value.partial_count), "selected_partial": integer(value.selected_partial),
            "partial_safe_no_positive": .bool(value.partial_safe_no_positive == 1),
            "started_ns": number(value.started_ns), "finished_ns": number(value.finished_ns),
            "checks": number(value.checks), "rows": .array(rows), "partial": .array(partial),
            "certificate": try certificate(value.certificate),
            "classifier_version": .string(String(cString: ng2_ring_classifier_version())),
            "feature_sha256": .string(String(cString: ng2_ring_feature_sha256())),
            "bank_sha256": .string(String(cString: ng2_ring_bank_sha256())),
            "coverage_sha256": .string(String(cString: ng2_ring_coverage_sha256())),
            "coverage_version": .string(String(cString: ng2_ring_coverage_version())),
            "policy_version": .string(targetOnly ? String(cString: ng2_ring_target_only_policy_version())
                                                : String(cString: ng2_ring_policy_version()))]
    }
}
