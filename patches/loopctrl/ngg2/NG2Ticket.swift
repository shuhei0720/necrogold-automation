import Foundation

// NG-G2 pure ticket boundary. Baseline assertion Red was observed in
// Actions run42332613748 before this implementation.
enum NG2TicketGuard {
    static func permits(expectedGeneration: UInt64, currentGeneration: UInt64,
                        cancelled: Bool, ownerActive: Bool, foreground: Bool,
                        locked: Bool, now: UInt64, notBefore: UInt64,
                        deadline: UInt64) -> Bool {
        return expectedGeneration != 0 && expectedGeneration == currentGeneration
            && !cancelled && ownerActive && foreground && !locked
            && notBefore <= deadline && now >= notBefore && now <= deadline
    }
    static func canReleaseLease(captureWorkerDone: Bool, captureOutstanding: Bool,
                                mainOutstanding: Bool, legacyCaptures: Int) -> Bool {
        captureWorkerDone && !captureOutstanding && !mainOutstanding && legacyCaptures == 0
    }
    static func renewsHeartbeat(keepalive: Bool = false, ownerActive: Bool, cancelled: Bool) -> Bool {
        keepalive && ownerActive && !cancelled
    }
}
