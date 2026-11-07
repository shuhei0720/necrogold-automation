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
require(!NG2TicketGuard.canReleaseLease(captureWorkerDone: false, captureOutstanding: true,
    mainOutstanding: false, legacyCaptures: 0), "timed_out_capture_holds_lease")
require(!NG2TicketGuard.canReleaseLease(captureWorkerDone: true, captureOutstanding: false,
    mainOutstanding: true, legacyCaptures: 0), "queued_main_holds_lease")
require(!NG2TicketGuard.canReleaseLease(captureWorkerDone: true, captureOutstanding: false,
    mainOutstanding: false, legacyCaptures: 1), "legacy_capture_holds_lease")
require(NG2TicketGuard.canReleaseLease(captureWorkerDone: true, captureOutstanding: false,
    mainOutstanding: false, legacyCaptures: 0), "drained_releases_lease")
require(!NG2TicketGuard.renewsHeartbeat(ownerActive: true, cancelled: false), "default_status_does_not_renew")
require(!NG2TicketGuard.renewsHeartbeat(keepalive: true, ownerActive: false, cancelled: false), "paused_owner_does_not_renew")
require(!NG2TicketGuard.renewsHeartbeat(keepalive: true, ownerActive: true, cancelled: true), "cancelled_run_does_not_renew")
require(NG2TicketGuard.renewsHeartbeat(keepalive: true, ownerActive: true, cancelled: false), "explicit_active_keepalive_renews")
print("PASS 20 pure Swift ticket/drain/heartbeat contracts; UIKit/device not executed")
