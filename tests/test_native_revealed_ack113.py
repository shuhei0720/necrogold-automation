"""TEST113: revealed domain-two motion resolves only a real ACK in time.

Public C uses the independently qualified procedural texture from domain113.
Actual phone input acceptance and unseen response frames are not simulated.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests.test_native_revealed_domain113 import pair


class NativeRevealedAck113Tests(unittest.TestCase):
    setUpClass = classmethod(native.NativeControllerTests.setUpClass.__func__)
    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)

    def frame(self, source):
        frame = deepcopy(source)
        frame.beat_valid = 1
        frame.beat_remaining = ((5*native.SECOND-(self.now-1))%native.PERIOD)/native.PERIOD
        frame.beat_spacing, frame.beat_center = 104., 446.
        return frame

    def armed(self):
        before, after = pair(3)
        for _ in range(27):
            self.now += 100_000_000
            self.observe(self.frame(before))
        command = self.next_move()
        self.assertEqual((4, 3, 0, 0), (command.kind, command.direction,
            self.status().inputs, self.status().moves))
        return before, after, command

    def test_only_real_current_prefix_ack_gains_the_observed_unit_with_original_visual_deadline(self):
        _, after, command = self.armed()
        deadline = self.motion_wait().deadline_ns
        self.ack(command)
        self.assertEqual((1, 0, 3), (self.status().inputs,
            self.status().moves, self.status().input_state))
        self.now = max(self.now+2, command.target_ns+80_000_002)
        self.assertLess(self.now, deadline)
        self.assertEqual(0, self.observe(self.frame(after), prefix=self.prefix-1))
        self.assertEqual((0, 3), (self.status().moves, self.status().input_state))
        self.now += 2
        self.assertEqual(1, self.observe(self.frame(after)))
        self.assertEqual((0, 1, 1, 0, 1), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().input_state,
            self.status().lead_confirmed),
            'a source-bound domain-two unit resolves the existing ACK only')
        event = next(row for row in self.events() if row.command.id == command.id)
        self.assertEqual((1, 0, -1, self.number),
            (event.motion, event.dx, event.dy, event.observed_capture_id))
        self.assertEqual(deadline, self.motion_wait().deadline_ns)

    def test_expired_visual_or_unknown_synth_never_acquires_movement_or_resends(self):
        for fault in ('expired', 'unknown_synth'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, command = self.armed()
                deadline = self.motion_wait().deadline_ns
                if fault == 'expired':
                    self.ack(command)
                    self.now = deadline+1
                else:
                    self.now = max(self.now, command.not_before_ns)
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, self.now, 1, 0, 1))
                    self.now += 50_000_000
                    self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1)
                    self.prefix = command.id
                    self.now = max(self.now+2, command.target_ns+80_000_002)
                self.observe(self.frame(after))
                self.assertEqual((1, 0), (self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(1, len([row for row in self.events() if row.command.kind == 4]))


for _name in ('setUp', 'observe', 'status', 'events', 'tick', 'ack', 'next_move',
              'motion_wait', 'fresh_engine'):
    setattr(NativeRevealedAck113Tests, _name, getattr(native.NativeControllerTests, _name))


if __name__ == '__main__':
    unittest.main()
