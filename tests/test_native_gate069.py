"""TEST069: discard an unsent closed-door ticket and obtain independent evidence.

Procedural public-C clocks/textures test one bounded refresh. TEST068's real
130->133 pair remains UNKNOWN; no absent future game frame is reconstructed.
"""
import ctypes as C
from copy import deepcopy
import random
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_device066 as doors
from tests import test_native_blocked067 as blocked

SECOND = fixture.SECOND
CORE = mechanics.CORE


class NativeGate069Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
    tearDownClass = classmethod(doors.NativeDevice066Tests.tearDownClass.__func__)
    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    armed_door = doors.NativeDevice066Tests.armed_door
    distant_change = doors.NativeDevice066Tests.distant_change
    credit = blocked.NativeBlocked067Tests.credit

    def observed_result(self, command, terrain, offset=80_000_002):
        moves = self.status().moves
        mechanics.NativeRecoveryTests.observed_result(self, command, terrain, offset)
        if self.status().moves > moves:
            self.verified_ns = self.now

    def uncertainty(self, terrain, salt=69069):
        changed = self.distant_change(terrain)
        rng = random.Random(salt)
        changed.signature = bytes(rng.randrange(20, 100) for _ in range(23296))
        return changed

    def refresh(self, direction=1):
        terrain, old = self.armed_door(direction)
        # This fixture's last actual result was committed just before the
        # continuous ticket was published. The recorded trace exposes its
        # immutable +12s epoch for subsequent checks.
        credit = self.credit()
        changed = self.uncertainty(terrain)
        self.now += 2
        self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual((0, 0, 0, credit), (self.status().reason,
            self.status().terminal, self.status().input_state, self.credit()),
            'a never-begun closed-door action must withdraw and observe before cleanup')
        retired = bytes(self.events()[-1]); event = self.events()[-1]
        self.assertEqual((3, 17, 0, 0, 0), (event.outcome, event.reason,
            event.begin_ns, event.motion, event.observed_capture_id))
        self.assertEqual(bytes(old), bytes(event.command))
        self.assertEqual((old.id - 1, 0), (self.status().last_completed_id,
            self.status().current_command_id))
        self.assertEqual((0, 0), (self.status().beat_period_ns,
            self.motion_wait().active))
        recovery = self.recovery(); row = recovery.records[min(1, recovery.record_count - 1)]
        self.assertEqual((2, 1, old.id, 6, 3), (recovery.mode,
            recovery.post_move_reacquisitions, row.command_id, row.reason, row.clock))
        self.assertGreater(row.model.period_ns, 0)
        self.assertEqual(self.verified_ns + 12 * SECOND, row.sync_deadline_ns,
            'neither seed replacement nor fresh fitting resets verified-progress time')
        self.assertNotEqual(4, self.tick()[1].kind)
        self.reject_old_callbacks_without_mutation(old)
        return changed, old, retired, row.sync_deadline_ns, credit

    def new_ticket(self, changed, old):
        # A different, later capture must prove BLOCKED independently. The
        # original UNKNOWN image pair cannot itself authorize the replacement.
        for _ in range(18):
            self.now += 100_000_000
            self.observe_actual(self.scene(2, 2, changed, beat=True))
            self.assertNotEqual(4, self.tick()[1].kind)
            self.assertEqual(0, self.status().beat_period_ns)
        for _ in range(9):
            self.now += 100_000_000
            self.observe_actual(self.scene(2, 2, changed, beat=True))
        new = self.next_move(changed)
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertGreater(new.source_capture_id, old.source_capture_id)
        self.assertEqual((old.ordinal, old.direction), (new.ordinal, new.direction))
        self.assertGreaterEqual(new.not_before_ns - self.now, 50_000_000)
        return new

    def test_new_independent_stationary_pair_and_fresh_hud_open_then_enter(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                self.fresh_engine()
                changed, old, retired, deadline, credit = self.refresh(direction)
                new = self.new_ticket(changed, old)
                self.assertEqual(credit, self.credit())
                self.assertEqual(retired, bytes(self.events()[-2]))
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new)
                opened = deepcopy(changed); opened.tiles[fixture.DIRS[direction]] = 'floor'
                self.observed_result(new, opened)
                self.assertEqual((2, 1, 1, 3), (self.status().inputs, self.status().moves,
                    self.status().door_changes, self.events()[-1].motion))
                entry = self.next_move(opened)
                self.ack(entry)
                self.observed_result(entry, fixture.translated(opened, direction))
                self.assertEqual((3, 2, 1, 0), (self.status().inputs, self.status().moves,
                    self.status().door_changes, self.status().reason))
                self.assertEqual(retired, bytes(self.events()[1]))

    def test_unknown_pairs_cannot_authorize_and_original_sync_budget_expires(self):
        changed, old, retired, deadline, credit = self.refresh()
        for index in range(26):
            self.now += 100_000_000
            changed = self.uncertainty(changed, index)
            self.observe_actual(self.scene(2, 2, changed, beat=True))
            self.assertNotEqual(4, self.tick()[1].kind)
        self.assertEqual(credit, self.credit())
        self.assertEqual(2, len(self.events()))
        self.now = deadline
        self.assertNotEqual(4, self.tick()[1].kind)
        self.assertEqual(8, self.status().reason)
        self.assertEqual(retired, bytes(self.events()[1]))
        self.assertEqual(credit, self.credit())

    def test_stationary_proof_requires_a_hud_sample_at_least_as_new_as_the_proof(self):
        changed, old, _, _, credit = self.refresh()
        for index in range(27):
            self.now += 100_000_000
            changed = self.uncertainty(changed, 69000 + index)
            self.observe_actual(self.scene(2, 2, changed, beat=True))
            self.assertNotEqual(4, self.tick()[1].kind)
        self.assertGreater(self.status().beat_period_ns, 0)
        # A new independent stationary image without a valid HUD is good
        # geometric evidence, but its older fitted model cannot authorize it.
        self.now += 2
        self.observe_actual(self.scene(2, 2, changed, beat=False))
        self.assertNotEqual(4, self.tick()[1].kind)
        self.assertEqual(credit, self.credit())
        self.now += 100_000_000
        self.observe_actual(self.scene(2, 2, changed, beat=True))
        new = self.next_move(changed)
        self.assertGreater(new.id, old.id)
        self.assertEqual(credit, self.credit())

    def test_geometry_protection_goods_and_known_motion_drift_end_refresh(self):
        for stage in ('observing', 'fitting', 'issued'):
            for fault in ('gold', 'protected', 'local', 'door', 'item', 'partial', 'moved', 'tween'):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine()
                    changed, old, retired, _, credit = self.refresh()
                    if stage == 'issued':
                        new = self.new_ticket(changed, old)
                    elif stage == 'fitting':
                        self.now += 100_000_000
                        self.observe_actual(self.scene(2, 2, changed, beat=True))
                        self.tick()
                    drift = deepcopy(changed)
                    if fault == 'gold': drift.tiles[(8, 3)] = 'gold'
                    elif fault == 'protected': drift.protected.add((8, 3))
                    elif fault == 'local': drift.tiles[(0, 1)] = 'stone'
                    elif fault == 'door': drift.tiles[(-1, 0)] = 'floor'
                    elif fault == 'item': drift.tiles[(8, 3)] = 'item'
                    elif fault == 'partial': drift.goods = 'partial'
                    else:
                        drift = fixture.translated(changed, 1, 9 if fault == 'moved' else 8)
                        # Keep the exact immutable terrain permission while
                        # testing signature-only, known nonstationary proof.
                        drift.tiles = deepcopy(changed.tiles)
                    self.now += 2
                    self.observe_actual(self.scene(2, 2, drift, beat=True))
                    self.assertEqual(17, self.status().reason)
                    self.assertEqual(credit, self.credit())
                    self.assertEqual(retired, bytes(self.events()[1]))
                    if stage == 'issued':
                        self.assertEqual(0, self.lib.ng2_controller_begin(
                            self.engine, new.id, new.not_before_ns, 1, 0, 1))

    def test_expired_original_ticket_and_sent_unknown_never_refresh(self):
        for fault in ('deadline', 'flat', 'sent_unknown'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, old = self.armed_door()
                changed = self.uncertainty(terrain)
                if fault == 'sent_unknown':
                    self.ack(old)
                    for offset in (80_000_002, 210_000_004, 730_000_006):
                        self.now = old.target_ns + offset
                        self.observe_actual(self.scene(2, 2, changed, beat=True))
                else:
                    if fault == 'flat': changed.signature = bytes([40]) * 23296
                    self.now = old.deadline_ns - 1 if fault == 'deadline' else self.now + 2
                    self.observe_actual(self.scene(2, 2, changed, beat=True),
                        commit=old.deadline_ns + 1 if fault == 'deadline' else self.now)
                    if fault == 'deadline': self.now = old.deadline_ns + 1
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(1, self.status().moves)

    def test_refresh_uses_actual_commit_and_rejects_unstable_or_wrong_prefix(self):
        for fault in ('deadline_equal', 'deadline_late', 'unstable', 'wrong_prefix', 'begun'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, old = self.armed_door()
                changed = self.uncertainty(terrain)
                options = {}
                if fault.startswith('deadline'):
                    self.now = old.deadline_ns - 1
                    options['commit'] = old.deadline_ns + int(fault == 'deadline_late')
                else:
                    self.now += 2
                    if fault == 'unstable': options['stable'] = 0
                    elif fault == 'wrong_prefix': options['prefix'] = self.prefix - 1
                    else:
                        self.now = old.not_before_ns
                        self.assertEqual(1, self.lib.ng2_controller_begin(
                            self.engine, old.id, self.now, 1, 0, 1))
                        self.now += 2
                self.observe_actual(self.scene(2, 2, changed, beat=True), **options)
                if fault == 'deadline_equal':
                    self.assertEqual((0, 0, 1), (self.status().reason,
                        self.status().input_state, self.recovery().post_move_reacquisitions))
                    self.reject_old_callbacks_without_mutation(old)
                else:
                    self.assertEqual(0, self.recovery().post_move_reacquisitions)
                    if fault == 'deadline_late': self.assertEqual(17, self.status().reason)
                    else: self.assertEqual(old.id, self.status().current_command_id)
                self.assertEqual((1, 1, 0), (self.status().inputs,
                    self.status().moves, self.status().door_changes))

    def test_goods_and_owner_guards_preempt_the_refresh_or_new_ticket(self):
        for stage in ('observing', 'issued'):
            for fault in ('goods', 'foreground', 'locked', 'owner'):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine()
                    changed, old, _, _, credit = self.refresh()
                    if stage == 'issued': new = self.new_ticket(changed, old)
                    if fault == 'goods':
                        changed.goods = 'visible'; self.now += 2
                        self.observe_actual(self.scene(2, 2, changed, beat=True))
                    else:
                        flags = {'front': 1, 'locked': 0, 'owner': 1}
                        flags[{'foreground': 'front', 'locked': 'locked', 'owner': 'owner'}[fault]] = int(fault == 'locked')
                        self.tick(**flags)
                    if stage == 'issued':
                        self.assertEqual(0, self.lib.ng2_controller_begin(
                            self.engine, new.id, new.not_before_ns, 1, 0, 1))
                    self.assertNotEqual(4, self.tick()[1].kind)
                    self.assertEqual(credit, self.credit())
                    self.assertEqual({'goods': 1, 'foreground': 3, 'locked': 4, 'owner': 5}[fault], self.status().reason)

    def test_new_ticket_signature_failure_cannot_restart_another_refresh_episode(self):
        changed, old, retired, _, credit = self.refresh()
        new = self.new_ticket(changed, old)
        drift = self.uncertainty(changed, 69070)
        self.now += 2
        self.observe_actual(self.scene(2, 2, drift, beat=True))
        self.assertEqual(17, self.status().reason)
        self.assertEqual(credit, self.credit())
        self.assertEqual(1, self.recovery().post_move_reacquisitions)
        self.assertEqual(retired, bytes(self.events()[1]))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id, new.not_before_ns, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
