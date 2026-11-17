"""TEST113: uncertain initial GOLD before any MOVE ticket withdraws data only.

Procedural public C frames test a settled candidate before dispatch. No old
clock, pending input or scene authority is recreated from a recorded frame.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_passage072 as passage
from tests import test_native_view074 as view


class NativeInitialUncertain113Tests(unittest.TestCase):
    setUpClass = classmethod(view.NativeView074Tests.setUpClass.__func__)
    tearDownClass = classmethod(view.NativeView074Tests.tearDownClass.__func__)

    def settled(self, fitted=False):
        self.new_uptime()
        terrain = passage.passage_room((-3, 0))
        self.observe(terrain)
        self.now += 250_000_000
        self.observe(terrain)
        if fitted: self.fit_clear(terrain)
        self.assertEqual((0, 0, 0, 0, 0), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().input_state,
            self.status().current_command_id))
        self.assertEqual([], self.events())
        return terrain

    def uncertain(self, terrain):
        frame = self.scene(terrain, gold=0)
        frame.gold_peak = 100
        return frame

    def later(self, frame, amount=20_000_000, **kwargs):
        self.now += amount
        return self.observe(frame, **kwargs)

    def test_settled_prefirst_ticket_uncertainty_waits_for_new_pair_and_entirely_fresh_fit(self):
        for fitted in (False, True):
            with self.subTest(old_valid_fit=fitted):
                terrain = self.settled(fitted)
                epoch, started = self.status().walk_started_ns, self.status().started_ns
                if fitted: self.assertEqual(native.PERIOD, self.status().beat_period_ns)
                self.later(self.uncertain(terrain))
                self.assertEqual((0, 0, 0), (self.status().reason,
                    self.status().input_state, self.status().beat_period_ns),
                    'settled no-ticket uncertainty revokes model/data authority without fatal SCREEN')
                self.assertEqual([], self.events(), 'no nonexistent MOVE may be retired or credited')
                self.assertEqual(0, self.tick()[0])
                self.later(terrain)
                first = self.number
                self.assertEqual(0, self.tick()[0], 'one new frame grants no authority')
                self.later(terrain)
                proof = self.number
                self.assertGreater(proof, first)
                self.assertEqual(0, self.tick()[0], 'old fit cannot reappear after the independent pair')
                for _ in range(9):
                    self.later(terrain, amount=100_000_000)
                    self.assertEqual(0, self.tick()[0], 'fresh fit still requires its normal sample span')
                self.fit_clear(terrain)
                command = self.next_move(terrain)
                self.assertEqual(4, command.kind)
                self.assertGreaterEqual(command.source_capture_id, proof)
                self.assertEqual((0, 0, 0, epoch, started), (self.status().inputs,
                    self.status().moves, self.status().restarts,
                    self.status().walk_started_ns, self.status().started_ns))
                self.moved(terrain, command)
                self.assertEqual((0, 1, 1), (self.status().reason,
                    self.status().inputs, self.status().moves))

    def test_empty_changed_or_missing_retained_support_never_becomes_restart_authority(self):
        for fault in ('empty', 'changed_mask', 'support'):
            with self.subTest(fault=fault):
                terrain = self.settled()
                self.later(self.uncertain(terrain))
                self.assertEqual(0, self.status().reason)
                changed = deepcopy(terrain)
                if fault == 'empty': changed.tiles[(-3, 0)] = 'stone'
                elif fault == 'changed_mask':
                    changed = passage.passage_room((0, -3))
                else: changed.tiles[(-3, -1)] = 'stone'
                for _ in range(4):
                    self.later(changed)
                    self.assertEqual((0, 0), (self.status().reason, self.tick()[0]))
                    self.assertEqual([], self.events())
                self.now = self.status().walk_started_ns+12*native.SECOND
                self.tick()
                self.assertEqual((8, 0, 0), (self.status().reason,
                    self.status().inputs, self.status().moves))

    def test_overlapping_or_wrong_prefix_trigger_has_no_new_authority(self):
        for fault in ('overlap', 'prefix', 'unstable'):
            with self.subTest(fault=fault):
                terrain = self.settled()
                previous_end = self.status().last_capture_end_ns
                options = ({'start': previous_end-1} if fault == 'overlap' else
                           {'prefix': self.prefix+1} if fault == 'prefix' else {'stable': 0})
                self.later(self.uncertain(terrain), **options)
                self.assertEqual([], self.events())
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
                if fault == 'overlap': self.assertEqual(17, self.status().reason)
                else: self.assertEqual(0, self.status().reason)


for _name in ('setUp', 'status', 'events', 'tick', 'ack', 'fresh_engine', 'scene',
              'observe', 'fit_clear', 'next_operation', 'next_move', 'moved',
              'recovery', 'recovery_samples', 'all_public_bytes',
              'reject_old_callbacks_without_mutation', 'new_uptime'):
    setattr(NativeInitialUncertain113Tests, _name, getattr(view.NativeView074Tests, _name))


if __name__ == '__main__':
    unittest.main()
