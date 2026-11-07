import Foundation

func permits(_ cancelled: Bool = false, generation: UInt64 = 1,
             current: UInt64 = 1, owner: Bool = true, foreground: Bool = true,
             locked: Bool = false, now: UInt64 = 100, earliest: UInt64 = 90,
             deadline: UInt64 = 110) -> Bool {
    NG2TicketGuard.permits(expectedGeneration: generation,
        currentGeneration: current, cancelled: cancelled, ownerActive: owner,
        foreground: foreground, locked: locked, now: now,
        notBefore: earliest, deadline: deadline)
}
func require(_ value: Bool, _ label: String) {
    if !value { print("FAIL \(label)"); exit(1) }
}
require(!permits(true), "cancelled_ticket_not_sent")
require(!permits(generation: 0, current: 0), "zero_generation_refused")
require(!permits(current: 2), "changed_generation_not_sent")
require(!permits(owner: false), "owner_pause_not_sent")
require(!permits(foreground: false), "foreground_changed_not_sent")
require(!permits(locked: true), "locked_not_sent")
require(!permits(now: 89), "early_not_sent")
require(!permits(now: 111), "late_not_sent")
require(!permits(earliest: 111), "reversed_interval_not_sent")
require(permits(now: 90), "earliest_inclusive")
require(permits(now: 110), "deadline_inclusive")
require(permits(), "valid_ticket")
print("PASS 12 pure Swift ticket contracts; UIKit/device not executed")
