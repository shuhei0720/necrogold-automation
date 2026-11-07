import Foundation

// NG-G2 pure ticket boundary. The first CI runs this compilable baseline
// before the implementation; an assertion failure, not a compiler failure,
// is required by check_ngg2.py --red-only.
enum NG2TicketGuard {
    static func permits(expectedGeneration: UInt64, currentGeneration: UInt64,
                        cancelled: Bool, ownerActive: Bool, foreground: Bool,
                        locked: Bool, now: UInt64, notBefore: UInt64,
                        deadline: UInt64) -> Bool {
        return true
    }
}
