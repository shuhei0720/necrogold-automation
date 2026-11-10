"""TEST067: inspect the second uncertain image soon enough for the next beat.

TEST066 received timestamps motivate one-tenth-period scheduling. Procedural
public-C scenes below prove scheduling, frozen tickets and rejection guards;
missing intermediate device PNGs are not manufactured or called replay.
"""
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_motion_cadence as cadence
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE
PERIOD = mechanics.PERIOD


class NativeCadence067Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST067_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test067-cadence-baseline-')
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

    # Mechanics only; don't inherit the unrelated recovery/cadence suites.
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

    def test_second_complete_image_uses_tenth_capture_start_boundary_and_frozen_ticket(self):
        for tween in (False, True):
            with self.subTest(tween=tween):
                self.fresh_engine(); before, command = self.armed()
                self.uncertain(before, command, tween=tween)
                after = mechanics.translated(before, command.direction)
                self.frame(after, self.first_start + PERIOD // 10 - 1)
                self.assertEqual((1, 0, 3), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state))
                self.assert_frozen(command)
                self.frame(after, self.first_start + PERIOD // 10)
                self.assertEqual((2, 1, 1, 0), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs, self.status().reason),
                    'the second strict displacement proof must use the earlier captured image')
                self.assertEqual(0, self.motion_wait().active)
                self.assert_frozen(command)

    def test_second_image_with_unstable_or_wrong_prefix_never_uses_the_new_slot(self):
        for invalid in ('unstable', 'prefix'):
            with self.subTest(invalid=invalid):
                self.fresh_engine(); before, command = self.armed()
                self.uncertain(before, command)
                after = mechanics.translated(before, command.direction)
                start = self.first_start + PERIOD // 10
                last_id = self.status().last_capture_id
                self.assertEqual(0, self.frame(after, start,
                    stable=0 if invalid == 'unstable' else 1,
                    prefix=self.prefix + 1 if invalid == 'prefix' else self.prefix))
                self.assertEqual((1, 0, 3, last_id), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state, self.status().last_capture_id))
                self.assert_frozen(command)
                # Rejected-prefix captures still advance the seen capture
                # clocks. The next eligible image must have a later start.
                self.frame(after, start + 1)
                self.assertEqual((2, 1, 1), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs))
                self.assert_frozen(command)

    def test_first_image_still_requires_ack_and_target_settling_boundary(self):
        for boundary in ('ack', 'target'):
            with self.subTest(boundary=boundary):
                self.fresh_engine(); before = self.fit(); command = self.next_move()
                self.now = command.not_before_ns
                self.assertEqual(1, self.lib.ng2_controller_begin(
                    self.engine, command.id, self.now, 1, 0, 1))
                self.now += 400_000_000 if boundary == 'ack' else 1
                ack = self.now
                self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, ack, 1))
                self.prefix = command.id
                self.before_bytes = bytes(self.events()[-1].command)
                self.frozen_deadline = self.motion_wait().deadline_ns
                earliest = max(ack, command.target_ns + 80_000_000)
                after = mechanics.translated(before, command.direction)
                self.frame(after, earliest - 1)
                self.assertEqual((0, 0, 3), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state))
                self.assert_frozen(command)
                self.frame(after, earliest)
                self.assertEqual((1, 1, 1, 0), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs, self.status().reason))
                self.assert_frozen(command)

    def test_second_proof_checks_actual_commit_against_unchanged_visual_deadline(self):
        for offset in (0, 1):
            with self.subTest(commit_after_deadline=offset):
                self.fresh_engine(); before, command = self.armed()
                self.first_start = self.frozen_deadline - 70_000_000
                self.uncertain(before, command)
                after = mechanics.translated(before, command.direction)
                self.frame(after, self.first_start + PERIOD // 10,
                    commit=self.frozen_deadline + offset)
                self.assertEqual((1 if offset else 2, 0 if offset else 1,
                    9 if offset else 0, 1), (self.motion_wait().attempts,
                    self.status().moves, self.status().reason, self.status().inputs))
                self.assertEqual(0, self.motion_wait().active)
                self.assert_frozen(command)

    def test_second_unknown_allows_early_checks_and_keeps_late_final_without_input_retry(self):
        for final in ('early_moved', 'late_moved', 'unknown'):
            with self.subTest(final=final):
                self.fresh_engine(); before, command = self.armed()
                unknown = self.uncertain(before, command)
                self.frame(unknown, self.first_start + PERIOD // 10)
                self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state))
                after = mechanics.translated(before, command.direction)
                self.frame(after, self.first_start + 2 * (PERIOD // 10) - 1)
                self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                    self.status().moves, self.status().input_state))
                self.frame(after if final == 'early_moved' else unknown,
                    self.first_start + 2 * (PERIOD // 10))
                if final != 'early_moved':
                    for index in range(3, 7):
                        self.frame(unknown, self.first_start + index * (PERIOD // 10))
                        self.assertEqual((index + 1, 0, 3, 1), (self.motion_wait().attempts,
                            self.status().moves, self.status().input_state, self.status().inputs))
                    self.frame(after if final == 'late_moved' else unknown,
                        self.first_start + PERIOD - 1)
                    self.assertEqual((7, 0, 3), (self.motion_wait().attempts,
                        self.status().moves, self.status().input_state))
                    self.frame(after if final == 'late_moved' else unknown, self.first_start + PERIOD)
                attempts = 3 if final == 'early_moved' else 8
                moved = int(final != 'unknown')
                self.assertEqual((attempts, moved, 0 if moved else 10, 1),
                    (self.motion_wait().attempts, self.status().moves,
                     self.status().reason, self.status().inputs))
                self.frame(after, self.first_start + PERIOD + 10_000_000)
                self.assertEqual((attempts, moved, 1), (self.motion_wait().attempts,
                    self.status().moves, self.status().inputs))
                self.assert_frozen(command)

    def test_early_second_move_can_publish_the_original_next_beat_without_reacquiring(self):
        before, command = self.armed()
        self.uncertain(before, command)
        after = mechanics.translated(before, command.direction)
        self.frame(after, self.first_start + PERIOD // 10)
        self.assertEqual((1, 1, 0), (self.status().moves,
            self.status().inputs, self.recovery().post_move_reacquisitions))
        self.assert_frozen(command)
        self.now = command.target_ns + PERIOD - self.status().lead_ns - 100_000_000
        self.observe_actual(self.scene(2, 2, after, beat=True))
        ready, child = self.tick()
        self.assertEqual((1, 4, command.target_ns + PERIOD),
            (ready, child.kind, child.target_ns),
            'strict early proof must leave the original next beat available')
        self.assertGreater(child.id, command.id)
        self.assertEqual(0, self.recovery().post_move_reacquisitions)
        self.ack(child)
        self.frame(mechanics.translated(after, child.direction),
            max(self.now + 2, child.target_ns + 80_000_000))
        self.assertEqual((2, 2, 0), (self.status().moves,
            self.status().inputs, self.status().reason))
        self.assertEqual(bytes(command), bytes(self.events()[0].command))


if __name__ == '__main__':
    unittest.main()
