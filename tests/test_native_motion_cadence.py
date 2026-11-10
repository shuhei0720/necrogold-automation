"""TEST062/067: pace uncertain comparisons without adding input or retries.

Synthetic signatures test C scheduling boundaries. TEST061's original images
stay UNKNOWN; no unseen completion frame or device success is asserted here.
TEST066's ~60ms capture cadence rounds a quarter-beat second check past the
next input slot. TEST067 permits that second check after one tenth of the
original period. TEST070 adds bounded checks and keeps the full-period final.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_recovery as fixture_recovery

CORE = fixture_recovery.CORE
PERIOD = fixture_recovery.PERIOD


class NativeMotionCadenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = fixture_recovery.CORE
        baseline = os.environ.get('NECRO_TEST062_BASELINE_CONTROLLER')
        cls.baseline_directory = None
        try:
            fixture_recovery.CORE = CORE
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test062-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                fixture_recovery.CORE = directory
            fixture_recovery.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            fixture_recovery.CORE = previous

    @classmethod
    def tearDownClass(cls):
        fixture_recovery.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    # Borrow mechanics explicitly; do not inherit the unrelated 29-test class.
    setUp = fixture_recovery.NativeRecoveryTests.setUp
    scene = fixture_recovery.NativeRecoveryTests.scene
    observe = fixture_recovery.NativeRecoveryTests.observe
    observe_actual = fixture_recovery.NativeRecoveryTests.observe_actual
    tick = fixture_recovery.NativeRecoveryTests.tick
    status = fixture_recovery.NativeRecoveryTests.status
    events = fixture_recovery.NativeRecoveryTests.events
    motion_wait = fixture_recovery.NativeRecoveryTests.motion_wait
    recovery = fixture_recovery.NativeRecoveryTests.recovery
    ack = fixture_recovery.NativeRecoveryTests.ack
    fit = fixture_recovery.NativeRecoveryTests.fit
    next_move = fixture_recovery.NativeRecoveryTests.next_move
    fresh_engine = fixture_recovery.NativeRecoveryTests.fresh_engine

    def armed(self):
        before = self.fit()
        command = self.next_move()
        self.ack(command)
        self.before_bytes = bytes(self.events()[-1].command)
        self.frozen_deadline = self.motion_wait().deadline_ns
        self.first_start = max(self.now + 2, command.target_ns + 80_000_000)
        return before, command

    def frame(self, terrain, start, *, commit=None, prefix=None, stable=1):
        self.now = start + 2
        return self.observe_actual(self.scene(2, 2, terrain, beat=True), start=start,
                                   end=self.now, commit=commit, prefix=prefix, stable=stable)

    def uncertain(self, before, command, *, tween=False):
        frame = fixture_recovery.translated(before, command.direction, 8) if tween else deepcopy(before)
        if not tween:
            frame.signature = bytes([40]) * 23296
        self.assertEqual(1, self.frame(frame, self.first_start))
        self.assertEqual((1, 0, 3, 1), (self.motion_wait().attempts,
                         self.status().moves, self.status().input_state, self.status().inputs))
        self.assertEqual(7 if tween else 0, self.motion_wait().last_motion)
        return frame

    def assert_frozen(self, command):
        self.assertEqual(self.before_bytes, bytes(self.events()[-1].command))
        self.assertEqual(self.frozen_deadline, self.motion_wait().deadline_ns)
        self.assertEqual(command.id, self.motion_wait().command_id)
        self.assertEqual(command.source_capture_id, self.motion_wait().source_capture_id)
        self.assertEqual(1, len([event for event in self.events() if event.command.kind == 4]))

    def test_first_complete_move_is_immediate_without_cadence_delay(self):
        before, command = self.armed()
        self.frame(fixture_recovery.translated(before, command.direction), self.first_start)
        self.assertEqual((1, 1, 0, 0), (self.status().moves, self.status().inputs,
                         self.status().input_state, self.status().reason))
        self.assertEqual(1, self.motion_wait().attempts)
        self.assertEqual(0, self.recovery().post_move_reacquisitions)

    def test_adjacent_unknown_frames_do_not_exhaust_attempts_before_full_period_move(self):
        before, command = self.armed()
        uncertain = self.uncertain(before, command)
        self.frame(uncertain, self.first_start + 40_000_000)
        self.assertEqual((1, 0, 3), (self.motion_wait().attempts,
                         self.status().reason, self.status().input_state),
                         'a 40ms adjacent frame must not consume the settling retry')
        self.frame(uncertain, self.first_start + 80_000_000)
        self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                         self.status().reason, self.status().input_state),
                         'an 80ms frame may use the second check, never a third early check')
        self.frame(fixture_recovery.translated(before, command.direction), self.first_start + PERIOD // 4)
        self.assertEqual((2, 0, 3), (self.motion_wait().attempts, self.status().moves,
                         self.status().input_state))
        self.frame(fixture_recovery.translated(before, command.direction), self.first_start + PERIOD)
        self.assertEqual((3, 1, 0), (self.motion_wait().attempts, self.status().moves, self.status().reason))
        self.assert_frozen(command)

    def test_tenth_boundary_uses_capture_start_and_skips_even_a_complete_frame(self):
        before, command = self.armed()
        self.uncertain(before, command)
        after = fixture_recovery.translated(before, command.direction)
        # Its end is beyond the checkpoint; capture start still misses by 1ns.
        self.frame(after, self.first_start + PERIOD // 10 - 1)
        self.assertEqual((1, 0, 3), (self.motion_wait().attempts,
                         self.status().moves, self.status().input_state),
                         'capture end cannot backdate the scheduled comparison start')
        self.assert_frozen(command)
        self.frame(after, self.first_start + PERIOD // 10)
        self.assertEqual((2, 1, 0), (self.motion_wait().attempts, self.status().moves, self.status().reason))
        self.assert_frozen(command)

    def test_third_comparison_uses_tenth_spacing_then_confirms(self):
        before, command = self.armed()
        uncertain = self.uncertain(before, command)
        self.frame(uncertain, self.first_start + PERIOD // 10)
        self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                         self.status().reason, self.status().input_state))
        after = fixture_recovery.translated(before, command.direction)
        self.frame(after, self.first_start + 2 * (PERIOD // 10) - 1)
        self.assertEqual((2, 0, 3), (self.motion_wait().attempts,
                         self.status().moves, self.status().input_state))
        self.frame(after, self.first_start + 2 * (PERIOD // 10))
        self.assertEqual((3, 1, 0), (self.motion_wait().attempts, self.status().moves, self.status().reason))
        self.assert_frozen(command)

    def test_eight_scheduled_unknowns_stop_without_ninth_comparison_or_input(self):
        before, command = self.armed()
        uncertain = self.uncertain(before, command)
        for index in range(1, 7):
            self.frame(uncertain, self.first_start + index * (PERIOD // 10))
            self.assertEqual((index + 1, 0, 3, 1), (self.motion_wait().attempts,
                self.status().moves, self.status().input_state, self.status().inputs))
        self.frame(uncertain, self.first_start + PERIOD - 1)
        self.assertEqual((7, 0, 3), (self.motion_wait().attempts,
            self.status().moves, self.status().input_state))
        self.frame(uncertain, self.first_start + PERIOD)
        self.assertEqual((8, 0, 10, 0), (self.motion_wait().attempts, self.status().moves,
                         self.status().reason, self.motion_wait().active))
        self.frame(fixture_recovery.translated(before, command.direction), self.first_start + PERIOD + 10_000_000)
        self.assertEqual((8, 0, 1), (self.motion_wait().attempts, self.status().moves, self.status().inputs))
        self.assert_frozen(command)

    def test_visual_expiry_is_checked_before_a_retry_would_be_skipped(self):
        before, command = self.armed()
        self.first_start = self.frozen_deadline - 50_000_000
        uncertain = self.uncertain(before, command)
        self.frame(uncertain, self.frozen_deadline - 2_000_000,
                   commit=self.frozen_deadline + 1)
        self.assertEqual((9, 0, 1), (self.status().reason, self.status().moves, self.motion_wait().attempts))
        self.assertEqual(0, self.motion_wait().active)
        self.assert_frozen(command)

    def test_goods_on_a_skipped_retry_still_latch_and_never_send_another_direction(self):
        before, command = self.armed()
        uncertain = self.uncertain(before, command)
        goods = deepcopy(uncertain)
        goods.goods = 'visible'
        self.frame(goods, self.first_start + 40_000_000)
        self.assertEqual((1, 1, 0), (self.status().goods, self.status().reason, self.status().moves))
        self.assertEqual(1, self.status().inputs)
        self.assertEqual(0, self.motion_wait().active)
        self.now += 2
        ready, pause = self.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.assertEqual(1, len([event for event in self.events() if event.command.kind == 4]))

    def test_tween_and_unknown_share_the_same_settling_schedule(self):
        before, command = self.armed()
        self.uncertain(before, command, tween=True)
        after = fixture_recovery.translated(before, command.direction)
        self.frame(after, self.first_start + PERIOD // 10 - 1)
        self.assertEqual((1, 0, 3), (self.motion_wait().attempts,
                         self.status().moves, self.status().input_state))
        self.frame(after, self.first_start + PERIOD // 10)
        self.assertEqual((2, 1), (self.motion_wait().attempts, self.status().moves))
        self.assert_frozen(command)


if __name__ == '__main__':
    unittest.main()
