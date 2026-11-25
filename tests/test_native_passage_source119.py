"""TEST119: retire a refined no-gold ticket before a newly observed route.

Public C lifecycle and independently declared room/clock/signatures model the
TEST118 failure boundary. Recorded source109 remains UNKNOWN against111;
no missing phone captures or future input outcomes are reconstructed here.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_passage072 as passage
from tests import test_native_passage115 as source115
from tests import test_native_passage_navigation072 as geometry
from tests import test_native_recovery as mechanics
from tests import test_native_stationary_wait076 as stationary
from tests.test_native_motion075 import Motion
from tests.test_native_beat import NativeSample

CORE = Path(os.environ.get('NECRO119_PASSAGE_CORE', native.CORE))


class NativePassageSource119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior = native.CORE
        try:
            native.CORE = CORE
            native.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            native.CORE = prior
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(Motion)]
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(native.Scene), C.c_int32,
            C.c_int32, C.c_int32, C.c_int32, C.POINTER(geometry.Decision)]
        cls.lib.ng2_controller_recovery_status.argtypes = [C.c_void_p, C.POINTER(mechanics.RecoveryStatus)]
        cls.lib.ng2_controller_recovery_samples.argtypes = [C.c_void_p, C.c_size_t,
            C.POINTER(NativeSample), C.c_size_t]
        cls.lib.ng2_controller_recovery_samples.restype = C.c_size_t

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)
    setUp = native.NativeControllerTests.setUp
    scene = native.NativeControllerTests.scene
    tick = native.NativeControllerTests.tick
    status = native.NativeControllerTests.status
    events = native.NativeControllerTests.events
    ack = native.NativeControllerTests.ack
    motion_wait = native.NativeControllerTests.motion_wait
    preparation_epoch = native.NativeControllerTests.preparation_epoch
    fresh_engine = native.NativeControllerTests.fresh_engine
    credit = stationary.NativeStationaryWait076Tests.credit
    frame = stationary.NativeStationaryWait076Tests.frame
    observe = stationary.NativeStationaryWait076Tests.observe
    direct_motion = source115.NativePassageSource115Tests.direct_motion
    next_operation = passage.NativePassage072Tests.next_operation
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    scene_changes = native.NativeControllerTests.scene_changes
    scene_details = native.NativeControllerTests.scene_details
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes

    def choice(self, terrain):
        frame = self.frame(terrain)
        value = geometry.Decision()
        self.assertGreater(self.lib.ng2_choose_passage(C.byref(frame), self.status().x,
            self.status().y, -3, 2, C.byref(value)), 0)
        return tuple(getattr(value, field) for field, _ in value._fields_)

    def refined_route(self):
        room = passage.passage_room(mouth=(-3, 2))
        for _ in range(27):
            self.now += 100_000_000
            self.observe(room)
        first = self.next_operation(room)
        self.assertEqual((4, 1), (first.kind, first.direction))
        self.ack(first)
        before = native.translated(room, first.direction)
        # A still-obscured bottom-side floor keeps the inboard DOWN vantage.
        # The known mouth/world goal and current/next FLOOR do not change.
        before.tiles[(-1, 2)] = 'dirt'
        self.now = max(self.now, first.target_ns+80_000_002)
        self.observe(before)
        self.assertEqual((1, 1, -1, 0),
            (self.status().inputs, self.status().moves, self.status().x, self.status().y))
        self.verified_ns = self.now
        old = self.next_operation(before)
        self.assertEqual((4, 4), (old.kind, old.direction))
        refined = deepcopy(before)
        self.assertEqual('dirt', refined.tiles[(4, 2)])
        refined.tiles[(4, 2)] = 'stone'
        self.assertEqual((2, 0, 0), self.direct_motion(before, refined, old.direction))
        self.now += 2
        self.observe(refined)
        ready, new = self.tick()
        self.assertEqual((1, 4), (ready, new.kind))
        self.assertGreater(new.id, old.id)
        self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal, old.direction),
            (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal, new.direction))
        self.original_period = self.status().beat_period_ns
        self.parent_deadline = min(self.status().walk_started_ns+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,
            self.status().started_ns+180*native.SECOND)
        self.saved_credit = self.credit()
        changed = deepcopy(refined)
        changed.tiles[(-1, 2)] = 'floor'
        self.assertEqual((4, 10, 0, 2, 1), self.choice(refined))
        self.assertEqual((1, 10, -3, 2, 1), self.choice(changed))
        self.assertEqual((2, 0, 0), self.direct_motion(refined, changed, old.direction))
        return before, refined, changed, old, new

    def enter_route_wait(self):
        before, refined, changed, old, new = self.refined_route()
        self.now += 2
        self.trigger_ns = self.now
        self.wait_deadline = min(self.parent_deadline, self.now+2*self.original_period)
        count = len(self.events())
        self.observe(changed)
        self.assertEqual((0, 0, 0),
            (self.status().reason, self.status().input_state, self.status().current_command_id),
            'a definitely-unstarted refined ticket must retire into the bounded route wait')
        retired = self.events()[-1]
        self.assertEqual((new.id, 3, 0, 0),
            (retired.command.id, retired.outcome, retired.begin_ns, retired.motion))
        self.assertEqual(count, len(self.events()))
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual(0, self.preparation_epoch(new))
        revoked = self.scene_changes()[-1]
        self.assertEqual((new.id, 0), (revoked.command_id, revoked.replan_allowed))
        self.assertEqual(1, self.scene_details()[-1].continuous_count,
            'entering a data wait cannot renew the existing global reissue budget')
        self.assertEqual((new.target_ns, new.not_before_ns, new.deadline_ns),
            (retired.command.target_ns, retired.command.not_before_ns, retired.command.deadline_ns))
        self.assertEqual(0, self.tick()[0], 'one changed image is not replacement input authority')
        self.reject_old_callbacks_without_mutation(old)
        self.reject_old_callbacks_without_mutation(new)
        return changed, old, new

    def test_refined_unsent_route_change_waits_then_independent_proof_uses_new_physical_beat(self):
        changed, old, new = self.enter_route_wait()
        self.now += 90_000_000
        self.observe(changed)
        replacement = self.next_operation(changed)
        self.assertEqual((4, 1, old.ordinal),
            (replacement.kind, replacement.direction, replacement.ordinal))
        self.assertGreater(replacement.id, new.id)
        self.assertGreater(replacement.target_ns, old.target_ns)
        self.assertLess(replacement.not_before_ns, self.parent_deadline)
        self.assertLess(self.now, self.wait_deadline)
        self.assertEqual(self.saved_credit, self.credit())
        self.ack(replacement)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves), 'ACK is not movement')
        moved = native.translated(changed, replacement.direction)
        self.assertEqual((1, -1, 0), self.direct_motion(changed, moved, replacement.direction))
        self.now = max(self.now+2, replacement.target_ns+80_000_002)
        self.observe(moved)
        self.assertEqual((0, 2, 2, -2, 0),
            (self.status().reason, self.status().inputs, self.status().moves,
             self.status().x, self.status().y))

    def test_route_wait_repeated_unknown_proof_does_not_renew_W_or_credit(self):
        changed, _, _ = self.enter_route_wait()
        noisy = stationary.NativeStationaryWait076Tests.uncertain(self, changed)
        self.assertEqual((0, 0, 0), self.direct_motion(changed, noisy, 4))
        for offset in (90_000_000, 180_000_000, 270_000_000):
            self.now = self.trigger_ns+offset
            self.observe(noisy)
            self.assertEqual(0, self.status().reason)
            self.assertEqual(0, self.tick()[0])
            self.assertEqual(self.saved_credit, self.credit())
        self.now = self.wait_deadline
        self.observe(changed)
        self.assertEqual(12, self.status().reason, 'the original two-beat route wait expires')
        self.assertEqual(self.saved_credit, self.credit())
        self.assertNotEqual(4, self.tick()[1].kind)

    def test_begun_ACK_and_unknown_inputs_do_not_become_route_retries(self):
        for stage in ('begun', 'ACK', 'unknown'):
            with self.subTest(stage=stage):
                self.fresh_engine()
                _, _, changed, _, new = self.refined_route()
                self.now = new.not_before_ns
                self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1))
                if stage != 'begun':
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, new.id,
                        self.now, 1 if stage=='ACK' else -1))
                    if stage=='ACK': self.prefix=new.id
                count = len(self.events())
                self.now += 2
                self.observe(changed)
                self.assertEqual(count, len(self.events()))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                    self.now, 1, 0, 1))

    def test_wrong_prefix_or_unstable_capture_cannot_retire_or_replace_the_live_ticket(self):
        for options in ({'prefix': 99}, {'stable': 0}):
            with self.subTest(options=options):
                self.fresh_engine()
                _, _, changed, _, new = self.refined_route()
                count = len(self.events())
                self.now += 2
                self.assertEqual(0, self.observe(changed, **options))
                self.assertEqual((0, 1, new.id),
                    (self.status().reason, self.status().input_state, self.status().current_command_id))
                self.assertEqual(count, len(self.events()))
                self.assertEqual(self.saved_credit, self.credit())

    def test_wait_cancel_and_replacement_owner_guard_preserve_zero_additional_inputs(self):
        for fault in ('cancel', 'owner', 'foreground', 'locked'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                changed, _, _ = self.enter_route_wait()
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now+1, 2)
                    self.now += 2
                    self.observe(changed)
                    self.assertNotEqual(4, self.tick()[1].kind)
                else:
                    self.now += 90_000_000
                    self.observe(changed)
                    replacement = self.next_operation(changed)
                    self.assertEqual((4, 1), (replacement.kind, replacement.direction))
                    self.now = replacement.not_before_ns
                    options = {'front': 1, 'locked': 0, 'owner': 1}
                    options[{'owner': 'owner', 'foreground': 'front', 'locked': 'locked'}[fault]] = 1 if fault=='locked' else 0
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                        replacement.id, self.now, options['front'], options['locked'], options['owner']))
                self.assertEqual(self.saved_credit, self.credit())
                self.assertNotEqual(0, self.status().reason)

    def test_changed_goods_protection_next_floor_or_unproved_motion_cannot_use_wait_downgrade(self):
        for fault in ('protected', 'item', 'gold', 'partial', 'next_floor', 'unknown_motion', 'expired'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, _, changed, _, new = self.refined_route()
                if fault == 'protected': changed.protected.add((-1, 0))
                elif fault == 'item': changed.tiles[(7, 2)] = 'item'
                elif fault == 'gold':
                    changed.tiles[(7, 2)] = 'gold'; changed.gold.add((7, 2))
                elif fault == 'partial': changed.goods = 'partial'
                elif fault == 'next_floor': changed.tiles[(0, 1)] = 'dirt'
                elif fault == 'unknown_motion':
                    changed = stationary.NativeStationaryWait076Tests.uncertain(self, changed)
                self.now = new.deadline_ns+1 if fault=='expired' else self.now+2
                self.observe(changed)
                self.assertNotEqual(0, self.status().reason)
                self.assertEqual(self.saved_credit, self.credit())
                self.assertNotEqual(4, self.tick()[1].kind)


if __name__ == '__main__':
    unittest.main()
