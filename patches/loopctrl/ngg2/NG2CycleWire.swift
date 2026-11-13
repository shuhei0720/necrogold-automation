// TEST094 closed read-only projection. No method here grants input authority.
import Foundation
import CryptoKit

enum NG2CycleWire {
    static let schema = "ngg2-cycle-v1"
    static let profile = "normal-1-1-cycle-v1"
    static let chunkBytes = 64 * 1024
    enum Failure: Error { case invalidAssessment, invalidJSON }

    static func number(_ value: UInt64) -> JSONValue { .int(Int(min(value, UInt64(Int64.max)))) }
    static func integer(_ value: Int32) -> JSONValue { .int(Int(value)) }
    static func hash(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
    static func envelope(runID: String, mode: String, payload: [String: JSONValue]) -> [String: JSONValue] {
        ["schema": .string(schema), "run_id": .string(runID), "profile": .string(profile),
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
    private static func slot(_ value: NG2RingSlot) throws -> JSONValue {
        let scores = [value.icon_score, value.icon_upper_bound, value.word_iou, value.word_coverage,
                      value.non_target_icon_score, value.non_target_name_iou, value.non_target_name_coverage,
                      value.ignored_icon_score, value.ignored_gold_iou, value.ignored_gold_coverage,
                      value.ignored_dark_iou, value.ignored_dark_coverage]
        guard scores.allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 1.000001 }),
              value.outcome <= 4, value.kind <= 2, value.non_target_conflict <= 1, value.icon_score_exact <= 1,
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
            "kind": .string(["unknown", "known_non_target", "ignored_closed_container"][Int(value.kind)]),
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
    static func assessment(_ original: NG2RingResult) throws -> [String: JSONValue] {
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
                        "slots": .array(try [slot(row.slots.0), slot(row.slots.1), slot(row.slots.2)])])
                }
            }
        }
        let partial: [JSONValue] = try withUnsafePointer(to: &value.partial) { pointer in
            try pointer.withMemoryRebound(to: NG2RingSlot.self, capacity: 12) { items in
                try (0..<partialCount).map { try slot(items[$0]) }
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
            "policy_version": .string(String(cString: ng2_ring_policy_version()))]
    }
}
