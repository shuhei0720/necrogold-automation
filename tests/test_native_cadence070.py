"""TEST070: bounded visual rechecks leave a known corridor's next beat available.

Public-C procedural scenes verify clocks and strict motion classifications.
The received TEST069 frames motivate checking sooner; no absent device frame
is supplied or asserted to have completed a movement.
"""
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_recovery as mechanics
from tests import test_native_motion_cadence as cadence

CORE = mechanics.CORE
PERIOD = mechanics.PERIOD


class NativeCadence070Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST070_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test070-cadence-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    publish_procedural_candidate = mechanics.NativeRecoveryTests.publish_procedural_candidate
    armed = cadence.NativeMotionCadenceTests.armed
    frame = cadence.NativeMotionCadenceTests.frame
    uncertain = cadence.NativeMotionCadenceTests.uncertain
    assert_frozen = cadence.NativeMotionCadenceTests.assert_frozen

    def seven_uncertain(self, tween=False):
        before, command = self.armed()
        unknown = self.uncertain(before, command, tween=tween)
        for index in range(1, 7):
            self.frame(unknown, self.first_start + index * (PERIOD // 10))
            self.assertEqual((index + 1, 0, 3, 0), (self.motion_wait().attempts,
                self.status().moves, self.status().input_state, self.status().reason))
            self.assert_frozen(command)
        return before, unknown, command

    def test_third_strict_move_uses_earlier_image_and_preserves_original_next_beat(self):
        for tween in (False, True):
            with self.subTest(tween=tween):
                self.fresh_engine(); before, command = self.armed()
                unknown = self.uncertain(before, command, tween=tween)
                self.frame(unknown, self.first_start + PERIOD // 10)
                after = mechanics.translated(before, command.direction)
                self.frame(after, self.first_start + 2 * (PERIOD // 10) - 1)
                self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state))
                self.frame(after, self.first_start + 2 * (PERIOD // 10))
                self.assertEqual((3, 1, 1, 0), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs, self.status().reason),
                    'a third independent strict proof must not wait an extra full beat')
                self.assert_frozen(command)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.now = command.target_ns + PERIOD - self.status().lead_ns - 100_000_000
                self.observe_actual(self.scene(2, 2, after, beat=True))
                ready, child = self.tick()
                self.assertEqual((1, 4, command.target_ns + PERIOD),
                    (ready, child.kind, child.target_ns))
                self.assertGreater(child.id, command.id)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual(bytes(command), bytes(self.events()[0].command))

    def test_each_recheck_uses_last_actual_capture_start_for_minimum_spacing(self):
        before, command = self.armed(); unknown = self.uncertain(before, command)
        self.frame(unknown, self.first_start + 60_000_000)
        after = mechanics.translated(before, command.direction)
        self.frame(after, self.first_start + 60_000_000 + PERIOD // 10 - 1)
        self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
            self.status().moves, self.status().input_state))
        self.frame(after, self.first_start + 60_000_000 + PERIOD // 10)
        self.assertEqual((3, 1, 0), (self.motion_wait().attempts,
            self.status().moves, self.status().reason))
        self.assert_frozen(command)

    def test_finite_cap_reserves_the_old_one_period_final_opportunity(self):
        for tween in (False, True):
            with self.subTest(tween=tween):
                self.fresh_engine(); before, unknown, command = self.seven_uncertain(tween)
                self.frame(unknown, self.first_start + PERIOD - 1)
                self.assertEqual((7, 0, 3, 0), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state, self.status().reason),
                    'earlier probes must never exhaust the late visual opportunity')
                self.frame(unknown, self.first_start + PERIOD)
                self.assertEqual((8, 0, 0, 10), (self.motion_wait().attempts,
                    self.status().moves, self.motion_wait().active, self.status().reason))
                self.frame(mechanics.translated(before, command.direction),
                    self.first_start + PERIOD + PERIOD // 10)
                self.assertEqual((8, 0, 1), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs))
                self.assert_frozen(command)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(bytes(command), bytes(self.events()[0].command))

    def test_eighth_late_strict_move_can_still_confirm_under_original_visual_deadline(self):
        before, _, command = self.seven_uncertain()
        self.frame(mechanics.translated(before, command.direction), self.first_start + PERIOD)
        self.assertEqual((8, 1, 1, 0), (self.motion_wait().attempts,
            self.status().moves, self.status().inputs, self.status().reason))
        self.assertEqual(0, self.motion_wait().active)
        self.assert_frozen(command)

    def test_fourth_proof_checks_original_visual_deadline_at_actual_commit(self):
        for late in (0, 1):
            with self.subTest(late=late):
                self.fresh_engine(); before, command = self.armed()
                self.first_start = self.frozen_deadline - 230_000_000
                unknown = self.uncertain(before, command)
                for index in (1, 2):
                    self.frame(unknown, self.first_start + index * (PERIOD // 10))
                self.frame(mechanics.translated(before, command.direction),
                    self.first_start + 3 * (PERIOD // 10), commit=self.frozen_deadline + late)
                self.assertEqual((3 if late else 4, 0 if late else 1, 9 if late else 0, 1),
                    (self.motion_wait().attempts, self.status().moves,
                     self.status().reason, self.status().inputs))
                self.assertEqual(0, self.motion_wait().active)
                self.assert_frozen(command)

    def test_goods_latch_on_unstable_or_too_early_recheck_without_motion_credit(self):
        for invalid in ('spacing', 'unstable', 'prefix'):
            with self.subTest(invalid=invalid):
                self.fresh_engine(); before, command = self.armed()
                unknown = self.uncertain(before, command)
                self.frame(unknown, self.first_start + PERIOD // 10)
                goods = deepcopy(unknown); goods.goods = 'visible'
                self.frame(goods, self.first_start + PERIOD // 10 + 10_000_000,
                    stable=int(invalid != 'unstable'),
                    prefix=self.prefix + 1 if invalid == 'prefix' else self.prefix)
                self.assertEqual((1, 1, 0, 1), (self.status().goods,
                    self.status().reason, self.status().moves, self.status().inputs))
                self.assertEqual(2, self.motion_wait().attempts)
                self.assertEqual(0, self.motion_wait().active)
                self.assertEqual(1, len([e for e in self.events() if e.command.kind == 4]))
                self.assert_frozen(command)

    def test_unstable_prefix_and_owner_guards_preempt_additional_assessments(self):
        for invalid in ('unstable', 'prefix', 'owner'):
            with self.subTest(invalid=invalid):
                self.fresh_engine(); before, command = self.armed()
                unknown = self.uncertain(before, command)
                self.frame(unknown, self.first_start + PERIOD // 10)
                after = mechanics.translated(before, command.direction)
                if invalid == 'owner':
                    self.tick(owner=0)
                    self.assertNotEqual(4, self.tick()[1].kind)
                    self.assertEqual(5, self.status().reason)
                else:
                    start = self.first_start + 2 * (PERIOD // 10)
                    self.assertEqual(0, self.frame(after, start,
                        stable=int(invalid != 'unstable'),
                        prefix=self.prefix + 1 if invalid == 'prefix' else self.prefix))
                    self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                        self.status().moves, self.status().input_state))
                    self.frame(after, start + 1)
                    self.assertEqual((3, 1), (self.motion_wait().attempts, self.status().moves))
                self.assertEqual(1, self.status().inputs)
                self.assert_frozen(command)

    def test_unknown_synth_never_uses_any_visual_recheck_or_another_input(self):
        before = self.fit(); command = self.next_move()
        self.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
        self.now += 1
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1))
        for index in range(9):
            self.frame(mechanics.translated(before, command.direction),
                command.target_ns + 80_000_000 + index * (PERIOD // 10))
            self.assertNotEqual(4, self.tick()[1].kind)
        self.assertEqual((4, 0, 0, 1), (self.status().input_state,
            self.motion_wait().attempts, self.status().moves, self.status().inputs))


if __name__ == '__main__':
    unittest.main()
