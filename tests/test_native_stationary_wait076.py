"""TEST076: uncertain unsent floor observations discard authority and wait.

Public C entrypoints and procedural images prove the bounded transitions. The
later images are explicit unit fixtures, not missing TEST075 phone captures.
"""
import ctypes as C
from copy import deepcopy
import random
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_passage072 as passage
from tests import test_native_observation072 as observation
from tests import test_native_passage_unsent076 as unsent

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeStationaryWait076Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = unsent.CORE
        try:
            unsent.CORE = CORE
            unsent.NativePassageUnsent076Tests.setUpClass.__func__(cls)
        finally:
            unsent.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
                                      C.c_int32, C.POINTER(observation.Motion)]

    tearDownClass = classmethod(unsent.NativePassageUnsent076Tests.tearDownClass.__func__)
    setUp = fixture.NativeControllerTests.setUp
    scene = fixture.NativeControllerTests.scene
    tick = fixture.NativeControllerTests.tick
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    ack = fixture.NativeControllerTests.ack
    fit = fixture.NativeControllerTests.fit
    next_move = fixture.NativeControllerTests.next_move
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    motion_wait = fixture.NativeControllerTests.motion_wait
    credit = observation.NativeObservation072Tests.credit
    choice = observation.NativeObservation072Tests.choice
    observed_vantage = observation.NativeObservation072Tests.observed_vantage
    observed_result = observation.NativeObservation072Tests.observed_result
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch

    def frame(self, terrain):
        return self.scene(2, 2 if terrain.gold else 1, terrain, beat=True)

    def observe(self, terrain, **options):
        frame = terrain if isinstance(terrain, fixture.Scene) else self.frame(terrain)
        return fixture.NativeControllerTests.observe(self, frame, **options)

    def observe_actual(self, frame, **options):
        return mechanics.NativeRecoveryTests.observe_actual(self, frame, **options)

    def armed(self, mode='shop', direction=3):
        if mode == 'shop':
            terrain, command = self.observed_vantage(direction)
            self.verified_ns = self.verified_ns
        else:
            terrain = passage.passage_room()
            for _ in range(27):
                self.now += 100_000_000
                self.observe(terrain)
            first = self.next_move(terrain)
            self.ack(first)
            terrain = fixture.translated(terrain, first.direction)
            self.now = max(self.now, first.target_ns + 80_000_002)
            self.observe(terrain)
            self.assertEqual((1, 1, 1),
                (self.status().inputs, self.status().moves, self.status().lead_confirmed))
            self.verified_ns = self.now
            # The publication helper must retain the no-gold classification.
            command = passage.NativePassage072Tests.next_operation(self, terrain)
            self.assertEqual(4, command.kind)
        self.assertEqual(1, self.status().input_state)
        self.original_period = self.status().beat_period_ns
        self.parent_deadline = min(command.source_start_ns + 3 * SECOND,
            command.phase_sample_ns + 3 * SECOND, self.verified_ns + 12 * SECOND,
            self.status().walk_started_ns + 45 * SECOND,
            self.status().started_ns + 180 * SECOND)
        return terrain, command

    def uncertain(self, terrain, remote=False):
        changed = deepcopy(terrain)
        rng = random.Random(76076)
        changed.signature = bytes(rng.randrange(20, 100) for _ in range(23296))
        if remote:
            changed.tiles[(-10, 4)] = 'stone'
        return changed

    def motion(self, before, after, direction):
        a, b = self.frame(before), self.frame(after)
        out = observation.Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def start_wait(self, mode='shop', direction=3, remote=None):
        terrain, old = self.armed(mode, direction)
        changed = self.uncertain(terrain, mode == 'shop' if remote is None else remote)
        self.assertEqual((0, 0, 0), self.motion(terrain, changed, old.direction))
        self.assertEqual((2, 0, 0), self.motion(changed, changed, old.direction))
        self.saved_credit = self.credit()
        self.now = old.deadline_ns - 30_000_000
        self.trigger_commit = self.now
        self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline,
                                 self.trigger_commit + 2 * self.original_period)
        self.observe(changed)
        self.trigger_id = self.number
        self.assert_waiting(old)
        return terrain, changed, old

    def assert_waiting(self, old):
        self.assertEqual((0, 0, 4, 0, 0),
            (self.status().reason, self.status().terminal, self.status().phase,
             self.status().input_state, self.status().current_command_id),
            'UNKNOWN must discard the unsent ticket and wait without input authority')
        self.assertEqual(self.saved_credit, self.credit())
        event = next(e for e in self.events() if e.command.id == old.id)
        self.assertEqual((3, 17, 0, 0),
                         (event.outcome, event.reason, event.begin_ns, event.motion))
        self.assertEqual(bytes(old), bytes(event.command))
        self.assertEqual(0, self.preparation_epoch(old))
        self.assertEqual(0, self.motion_wait().active)
        self.assertEqual(0, self.tick()[0], 'the trigger itself must never become READY')

    def future_ticket(self, terrain):
        for _ in range(100):
            self.now += 20_000_000
            self.observe(terrain)
            ready, command = self.tick()
            self.assertEqual(0, self.status().reason)
            if ready:
                self.assertEqual(4, command.kind)
                self.assertGreaterEqual(command.not_before_ns - self.now, 50_000_000)
                return command
        self.fail('the strict anchor proof must lead to a bounded future prepared ticket')

    def test_unknown_shop_and_mask_zero_passage_retire_without_motion_credit(self):
        for mode in ('shop', 'passage'):
            directions = (1, 2, 3, 4) if mode == 'shop' else (3,)
            for direction in directions:
                with self.subTest(mode=mode, direction=direction):
                    self.fresh_engine()
                    terrain, _, old = self.start_wait(mode, direction)
                    self.reject_old_callbacks_without_mutation(old)
                    new = self.future_ticket(terrain)
                    self.assertGreater(new.id, old.id)
                    self.assertGreater(new.target_ns, old.target_ns)
                    self.assertEqual(old.direction, new.direction)
                    self.assertEqual((1, 1), (self.status().inputs, self.status().moves))

    def test_adjacent_blocked_frames_cannot_replace_the_original_anchor(self):
        for mode in ('shop', 'passage'):
            with self.subTest(mode=mode):
                self.fresh_engine()
                terrain, changed, old = self.start_wait(mode)
                for _ in range(3):
                    self.now += 100_000_000
                    self.observe(changed)
                    self.assert_waiting(old)
                self.assertEqual((0, 0, 0), self.motion(terrain, changed, old.direction))
                self.assertEqual((2, 0, 0), self.motion(changed, changed, old.direction))
                self.future_ticket(terrain)

    def test_proof_requires_independent_current_prefix_and_increasing_capture(self):
        for fault in ('prefix', 'unstable', 'id', 'overlap'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, old = self.start_wait('passage')
                self.now += 2
                options = {'prefix': self.prefix - 1} if fault == 'prefix' else (
                    {'stable': 0} if fault == 'unstable' else
                    {'number': self.trigger_id} if fault == 'id' else
                    {'start': self.trigger_end - 1})
                self.observe(terrain, **options)
                ready, command = self.tick()
                self.assertNotEqual(4, command.kind)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, old.id, old.not_before_ns, 1, 0, 1))

    def test_parent_horizon_caps_new_ticket_schedule_and_visual_authority(self):
        terrain, _, old = self.start_wait()
        new = self.future_ticket(terrain)
        self.assertLessEqual(new.deadline_ns + self.status().lead_ns + 50_000_000,
                             self.parent_deadline)
        self.assertLessEqual(self.motion_wait().deadline_ns, self.parent_deadline)
        self.assertLessEqual(self.recovery().schedule_deadline_ns, self.parent_deadline)
        self.assertEqual(self.parent_deadline, self.recovery().records[0].sync_deadline_ns)
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves))
        for mode in ('shop', 'passage'):
            for issued in (False, True):
                for extra in (0, 1):
                    with self.subTest(mode=mode, issued=issued, parent_extra=extra):
                        self.fresh_engine()
                        terrain, _, old = self.start_wait(mode)
                        if issued:
                            self.future_ticket(terrain)
                        else:
                            self.now += 100_000_000
                            self.observe(terrain)
                        # READY/ISSUED outlive W, but neither can extend P.
                        self.now = self.wait_deadline
                        self.observe(terrain)
                        self.assertEqual(0, self.status().reason)
                        self.now = self.parent_deadline + extra
                        self.observe(terrain)
                        self.assertEqual((8, 1, 1),
                            (self.status().reason, self.status().inputs, self.status().moves))
                        self.assertNotEqual(4, self.tick()[1].kind)

    def test_wait_deadline_is_fixed_and_unknown_frames_do_not_extend_it(self):
        for extra in (0, 1):
            with self.subTest(extra=extra):
                self.fresh_engine()
                terrain, changed, old = self.start_wait('passage')
                for _ in range(3):
                    self.now += 100_000_000
                    self.observe(changed)
                    self.assert_waiting(old)
                self.now = self.wait_deadline + extra
                self.observe(terrain)
                self.assertEqual((8, 1, 1),
                    (self.status().reason, self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_ready_or_issued_unknown_does_not_reopen_the_same_wait(self):
        for issued in (False, True):
            with self.subTest(issued=issued):
                self.fresh_engine()
                terrain, changed, old = self.start_wait()
                if issued:
                    self.future_ticket(terrain)
                else:
                    self.now += 100_000_000
                    self.observe(terrain)
                recoveries = self.recovery().post_move_reacquisitions
                self.now += 2
                self.observe(changed)
                self.assertEqual((17, 1, 1, recoveries),
                    (self.status().reason, self.status().inputs, self.status().moves,
                     self.recovery().post_move_reacquisitions))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, old.id, old.not_before_ns, 1, 0, 1))

    def test_unsafe_changed_scene_and_unproven_or_expired_ticket_cannot_start_wait(self):
        for fault in ('origin', 'next', 'near', 'protected', 'item', 'gold', 'route',
                      'goods', 'partial', 'nonfloor', 'expired'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, old = self.armed()
                changed = self.uncertain(terrain, True)
                if fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'near': changed.tiles[(1, 0)] = 'dirt'
                elif fault == 'protected': changed.protected.add((-10, 4))
                elif fault == 'item': changed.tiles[(-10, 4)] = 'item'
                elif fault == 'gold':
                    changed.tiles[(-8, 3)] = 'gold'; changed.gold.add((-8, 3))
                elif fault == 'route': changed.tiles[(0, -2)] = 'dirt'
                elif fault == 'goods': changed.goods = 'visible'
                elif fault == 'partial': changed.goods = 'partial'
                self.now = old.deadline_ns + 1 if fault == 'expired' else old.deadline_ns - 30_000_000
                frame = self.frame(changed)
                if fault == 'nonfloor': frame.state = 1
                self.observe(frame)
                self.assertNotEqual((0, 0, 4, 0),
                    (self.status().reason, self.status().terminal,
                     self.status().phase, self.status().input_state))
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))

    def test_goods_priority_and_unproven_new_gold_hold_without_moving(self):
        for fault in ('visible', 'partial', 'new_gold_unknown'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, changed, old = self.start_wait('passage')
                held = deepcopy(changed)
                if fault == 'new_gold_unknown':
                    held.tiles[(-1, -2)] = 'gold'; held.gold.add((-1, -2))
                else: held.goods = fault
                self.now += 100_000_000
                self.observe(held)
                self.assertEqual(1 if fault == 'visible' else 13 if fault == 'partial' else 17,
                                 self.status().reason)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)
        with self.subTest(fault='new_gold_strict'):
            self.fresh_engine()
            terrain, _, old = self.start_wait('passage')
            revealed = deepcopy(terrain)
            revealed.tiles[(-8, 3)] = 'gold'
            revealed.gold.add((-8, 3))
            self.assertEqual((2, 0, 0), self.motion(terrain, revealed, old.direction))
            self.now += 100_000_000
            self.observe(revealed)
            self.assertEqual((0, 0, 1, 1),
                (self.status().reason, self.status().input_state,
                 self.status().inputs, self.status().moves))
            self.assertEqual(0, self.tick()[0], 'new gold needs its independent handoff proof')
            self.reject_old_callbacks_without_mutation(old)
            self.now += 100_000_000
            self.observe(revealed)
            self.assertEqual(0, self.status().reason)
            new = self.future_ticket(revealed)
            self.assertGreater(new.id, old.id)
            self.assertLessEqual(self.motion_wait().deadline_ns, self.parent_deadline)
            self.assertLessEqual(self.recovery().schedule_deadline_ns, self.parent_deadline)
            self.now = self.parent_deadline
            self.tick()
            self.assertEqual((8, 1, 1),
                (self.status().reason, self.status().inputs, self.status().moves),
                'a strict new-gold handoff must inherit the original parent deadline')


if __name__ == '__main__':
    unittest.main()
