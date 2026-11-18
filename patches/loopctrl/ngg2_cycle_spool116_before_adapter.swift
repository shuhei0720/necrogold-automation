// TEST ONLY: exposes proposed TEST116 signatures over unmodified TEST115
// Spool primitives. It deliberately adds no campaign quota, reservation gate,
// content seal or recovered input authority. Its assertion Red is the missing
// NEW storage contract, not a claim that TEST115 exposed this native mode.
import Foundation
import CryptoKit

private func beforeSpool116Hash(_ bytes: Data) -> String {
    SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
}
extension NG2CycleSpool {
    struct Reservation: Equatable {
        let tokenID: String
        let rootID: String
        let runID: String
        let index: Int
        let predecessorID: String?
        var payload: [String: Any] {
            ["schema": "ngg2-continuation-reservation-v1", "root_id": rootID,
             "run_id": runID, "index": index, "predecessor_id": predecessorID as Any? ?? NSNull(),
             "token_id": tokenID, "slot_bytes": 156 * 1024 * 1024]
        }
    }
    final class CampaignQuota {
        let rootID: String
        init(rootID: String) { self.rootID = rootID }
        func reserveNext(runID: String, index: Int, predecessorID: String?) throws -> Reservation {
            Reservation(tokenID: UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased(),
                rootID: rootID, runID: runID, index: index, predecessorID: predecessorID)
        }
    }
    static func testCreateCampaignQuota(rootURL: URL, rootID: String, owner: String) throws -> CampaignQuota {
        CampaignQuota(rootID: rootID)
    }
    static func testCreate(rootURL: URL, runID: String, owner: String, provenance: [String: Any],
                           quota: CampaignQuota, reservation: Reservation) throws -> NG2CycleSpool {
        try testCreate(rootURL: rootURL, runID: runID, owner: owner, provenance: provenance)
    }
    var controlContentSealed: Bool { false }
    func sealContinuation(rootID: String, index: Int, predecessorID: String?, clockID: String,
                          terminal: RecordRef, continuation: [String: Any], successor: Reservation?) throws -> RecordRef {
        let refs = try frames().map { ["capture_id": $0.captureID, "raw_sha256": $0.rawSHA256,
            "metadata_sha256": $0.metadataSHA256, "bytes": $0.bytes] as [String: Any] }
        let frames = try JSONSerialization.data(withJSONObject: refs, options: [.sortedKeys, .withoutEscapingSlashes])
        return try commitRecord(kind: "continuation_seal", cycle: terminal.cycle, payload: [
            "schema": "ngg2-continuation-seal-v1", "root_id": rootID, "run_id": runID,
            "index": index, "predecessor_id": predecessorID as Any? ?? NSNull(),
            "next_run_id": successor?.runID as Any? ?? NSNull(), "clock_id": clockID,
            "session_sha256": beforeSpool116Hash(try sessionBytes()!), "terminal_sha256": terminal.sha256,
            "frames_sha256": beforeSpool116Hash(frames), "controller": continuation])
    }
}
