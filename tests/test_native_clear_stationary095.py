"""TEST095: private clear-singleton zero proof only rearms an unsent passage.

Procedural textures share085's sparse noisy surface; observed phone imagery is
not embedded or treated as a future response. Public Controller operations retain
independent captures, fixed world/prefix, old-ID retirement and original horizons.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest

from tests import test_native_controller as fixture
from tests import test_native_stationary_wait076 as stationary
from tests import test_native_passage072 as passage
from tests import test_native_singleton_stationary095 as singleton095

CORE = fixture.CORE


class NativeClearStationary095Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = stationary.CORE
        try:
            stationary.CORE = CORE
            stationary.NativeStationaryWait076Tests.setUpClass.__func__(cls)
        finally:
            stationary.CORE = previous
        cls.lib.ng2_clear_singleton_stationary_zero.argtypes = [C.POINTER(fixture.Scene),
            C.POINTER(fixture.Scene), C.c_int32]
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p

    tearDownClass = classmethod(stationary.NativeStationaryWait076Tests.tearDownClass.__func__)

    def singleton_wait(self):
        room = passage.passage_room(mouth=(-2, -3))
        room.tiles[(2, 2)] = 'stone'
        with patch.object(passage, 'passage_room', return_value=room):
            terrain, second = self.armed('passage')
        self.assertIn(second.direction, (1, 3))
        self.ack(second)
        terrain = fixture.translated(terrain, second.direction)
        self.now = max(self.now, second.target_ns + 80_000_002)
        self.observe(terrain)
        self.assertEqual((2, 2, 1), (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        self.verified_ns = self.now
        before, after = deepcopy(terrain), deepcopy(terrain)
        pixels = singleton095.singleton_pair(points=34)
        before.signature = bytes(pixels[0].signature)
        after.signature = bytes(pixels[1].signature)
        self.now += 10_000_000
        self.assertEqual(1, self.observe(before))
        old = passage.NativePassage072Tests.next_move(self, before)
        self.assertIn(old.direction, (1, 3))
        self.assertEqual((0, 0, 0), self.motion(before, after, old.direction),
                         'the existing public motion result remains UNKNOWN')
        self.assertEqual((2, 0, 0), self.motion(after, after, old.direction))
        a, b = self.frame(before), self.frame(after)
        self.assertEqual(1, self.lib.ng2_clear_singleton_stationary_zero(C.byref(a), C.byref(b), old.direction),
                         'the independent scalar proof qualifies before testing Controller adoption')
        self.parent_deadline = min(old.source_start_ns + 3 * fixture.SECOND,
            old.phase_sample_ns + 3 * fixture.SECOND, self.verified_ns + 12 * fixture.SECOND,
            self.status().walk_started_ns + 45 * fixture.SECOND,
            self.status().started_ns + 180 * fixture.SECOND)
        self.original_period = self.status().beat_period_ns
        self.saved_credit = self.credit()
        self.now = old.deadline_ns - 30_000_000
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now + 2 * self.original_period)
        self.observe(after)
        self.trigger_id = self.number
        self.assert_waiting(old)
        return before, after, old

    def test_independent_clear_singleton_zero_rearms_only_a_new_future_ticket(self):
        for cycle in (False, True):
            with self.subTest(cycle=cycle):
                self.fresh_engine()
                if cycle:
                    self.engine = self.lib.ng2_controller_create_cycle(fixture.SECOND)
                    self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
                before, after, old = self.singleton_wait()
                self.now += 20_000_000
                self.assertEqual(1, self.observe(after))
                new = self.future_ticket(after)
                self.assertGreater(new.id, old.id)
                self.assertGreater(new.target_ns, old.target_ns)
                self.assertEqual(old.direction, new.direction)
                self.assertLessEqual(self.motion_wait().deadline_ns, self.parent_deadline)
                self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new)
                self.assertEqual((3, 2), (self.status().inputs, self.status().moves),
                                 'new synth ACK is not displacement or gate entry')

    def test_zero_proof_needs_independent_stable_current_prefix_capture(self):
        for fault in ('prefix', 'unstable', 'id', 'overlap'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, old = self.singleton_wait()
                self.now += 20_000_000
                options = {'prefix': self.prefix - 1} if fault == 'prefix' else (
                    {'stable': 0} if fault == 'unstable' else
                    {'number': self.trigger_id} if fault == 'id' else
                    {'start': self.trigger_end - 1})
                self.observe(after, **options)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    old.not_before_ns, 1, 0, 1))

    def test_original_wait_and_parent_equalities_cannot_be_renewed_by_zero_proof(self):
        for issued in (False, True):
            for extra in (0, 1):
                with self.subTest(issued=issued, extra=extra):
                    self.fresh_engine()
                    _, after, _ = self.singleton_wait()
                    if issued:
                        new = self.future_ticket(after)
                        self.assertLessEqual(new.deadline_ns + self.status().lead_ns + 50_000_000,
                                             self.parent_deadline)
                    self.now = (self.parent_deadline if issued else self.wait_deadline) + extra
                    self.observe(after)
                    self.assertEqual((8, 2, 2),
                        (self.status().reason, self.status().inputs, self.status().moves))
                    self.assertNotEqual(4, self.tick()[1].kind)

    def test_cancel_or_started_unknown_cannot_reuse_the_zero_wait(self):
        for fault in ('cancel_wait', 'cancel_issued', 'unknown_sent'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, old = self.singleton_wait()
                new = self.future_ticket(after) if fault != 'cancel_wait' else None
                if fault == 'unknown_sent':
                    self.now = max(self.now, new.not_before_ns)
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1))
                    self.now += 1
                    self.lib.ng2_controller_complete(self.engine, new.id, self.now, -1)
                    self.assertEqual(4, self.status().input_state)
                else:
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                self.now += 10_000_000
                self.observe(after)
                self.assertEqual((3 if fault == 'unknown_sent' else 2, 2),
                                 (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    old.not_before_ns, 1, 0, 1))
                if new:
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                        new.not_before_ns, 1, 0, 1))
                self.assertNotEqual(4, self.tick()[1].kind)

    def selected_motion(self):
        original = self.lib
        fixture.NativeControllerTests.motion_selection_wrapper(self)
        # The existing test-only result selector preserves actual C matching
        # unless one assessment is explicitly armed. Copy every already bound
        # public declaration so the new profile uses identical pointer ABIs.
        for name, symbol in tuple(original.__dict__.items()):
            if name.startswith('ng2_') and hasattr(symbol, 'argtypes'):
                selected = getattr(self.lib, name)
                selected.argtypes, selected.restype = symbol.argtypes, symbol.restype

    def test_known_motion_or_failed_decode_cannot_fall_back_at_observation_or_begin(self):
        self.selected_motion()
        for stage in ('observe', 'begin'):
            for result, kind, dx, dy in ((1, 1, 0, -1), (1, 3, 0, 0), (1, 4, 1, 0), (0, 0, 0, 0)):
                with self.subTest(stage=stage, result=result, kind=kind):
                    self.lib.test_motion_reset()
                    self.fresh_engine()
                    _, after, old = self.singleton_wait()
                    new = self.future_ticket(after) if stage == 'begin' else None
                    self.lib.test_motion_once(1, result, kind, dx, dy)
                    if stage == 'observe':
                        self.now += 20_000_000
                        self.observe(after)
                    else:
                        self.now = max(self.now, new.not_before_ns)
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1))
                    self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                    self.assertEqual(0, self.preparation_epoch(old))
                    self.assertNotEqual(4, self.tick()[1].kind)

    def test_actual_gold_unknown_uses_the_original_strict_handoff_only(self):
        before, after, old = self.singleton_wait()
        revealed = deepcopy(after)
        revealed.tiles[(-8, 3)] = 'gold'
        revealed.gold.add((-8, 3))
        self.assertEqual((0, 0, 0), self.motion(before, revealed, old.direction))
        self.now += 20_000_000
        self.observe(revealed)
        self.assertEqual((17, 2, 2),
                         (self.status().reason, self.status().inputs, self.status().moves))
        self.assertNotEqual(4, self.tick()[1].kind)


for _name in ('setUp', 'scene', 'frame', 'observe', 'observe_actual', 'tick', 'status',
              'events', 'ack', 'fit', 'next_move', 'publish_procedural_candidate',
              'fresh_engine', 'recovery', 'recovery_samples', 'all_public_bytes',
              'reject_old_callbacks_without_mutation', 'motion_wait', 'credit',
              'choice', 'observed_vantage', 'observed_result', 'preparation_epoch',
              'armed', 'motion', 'assert_waiting', 'future_ticket'):
    setattr(NativeClearStationary095Tests, _name, getattr(stationary.NativeStationaryWait076Tests, _name))

NativeClearStationary095Tests.next_operation = passage.NativePassage072Tests.next_operation

if __name__ == '__main__':
    unittest.main()
