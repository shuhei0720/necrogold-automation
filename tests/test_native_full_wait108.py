"""Bounded no-input FULL observation waits, with fixed source authority.

Original236->238 has unchanged GOLD/ITEM/protection but ordinary material
jitter and normal UNKNOWN motion; its next cell is DIRT, never a MOVE proof.
The surfaces/HUD/clocks below are procedural. Future returning frames are
contract tests, not unrecorded phone acceptance. A host-only read probe checks
phase authority without adding any production ABI or mutating private state.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_full_framing101 as full
from tests.test_native_stop099 import stop_detail


PROBE = r'''
/* HOST TEST ONLY: read-only introspection, never linked to a shipped IPA. */
uint64_t ng2_test_full_wait_probe(const NG2Controller *p,int field){
    if(!p)return 0;
    switch(field){
        case 0:return (uint64_t)p->cycle_full_framing;
        case 1:return p->model_capture_id;
        case 2:return p->proof_capture_id;
        case 3:return (uint64_t)p->sample_count;
        case 4:return p->recovery_slot_target;
        case 5:return p->preparation_epoch;
        case 6:return p->model.last_ns;
        case 7:return (uint64_t)ng2_beat_model_valid(&p->model);
        default:return 0;
    }
}
'''


class NativeFullWait108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        cls.probe_directory = tempfile.TemporaryDirectory(prefix='full-wait108-')
        core = Path(cls.probe_directory.name)
        original = Path(os.environ.get('NECRO_TEST108_WAIT_CORE', str(previous)))
        for path in original.iterdir():
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, core/path.name)
        controller = core/'NG2Controller.c'
        controller.write_text(controller.read_text()+PROBE)
        try:
            native.CORE = core
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_test_full_wait_probe.argtypes = [C.c_void_p, C.c_int]
        cls.lib.ng2_test_full_wait_probe.restype = C.c_uint64

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()
        cls.probe_directory.cleanup()

    def setUp(self):
        self.f = full.NativeFullFraming101Tests(methodName='runTest')
        self.f.lib = self.lib
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def admitted(self):
        source, opening, state, moves = self.f.admitted()
        self.h, self.q = self.f.h, self.f.q
        self.assertEqual(1, self.probe(0))
        return source, opening, state, moves

    def probe(self, field):
        return self.lib.ng2_test_full_wait_probe(self.h.engine, field)

    @staticmethod
    def binding(state):
        return tuple(getattr(state, name) for name in ('job_id', 'capture_id',
            'capture_start_ns', 'prefix', 'deadline_ns', 'continuation_deadline_ns',
            'hold_started_ns', 'release_after_ns', 'level_id'))

    def observe(self, source, advance=10_000_000, **kwargs):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, source, beat=True), **kwargs)

    def assert_wait(self, state, moves):
        self.assertEqual((3, 0, 0, 0), (self.q.cycle().state, self.q.cycle().status,
            self.q.cycle().pending, self.q.cycle().completed_shops),
            'ordinary uncertainty before any reservation must remain an uncounted no-input wait')
        self.assertEqual(self.binding(state), self.binding(self.q.cycle()))
        self.assertEqual((1, 0, 0, 0, 0, 0), tuple(self.probe(i) for i in (0, 1, 2, 4, 5, 7)))
        self.assertEqual((0, moves, 0), (self.h.status().beat_period_ns,
            self.h.status().moves, self.h.status().input_state))
        self.assertEqual((0, 0), (stop_detail(self.lib, self.h.engine).valid,
            self.h.tick()[1].kind), 'a recoverable wait is not the first terminal stop')

    def new_phase(self, source, proof):
        for _ in range(20):
            if self.probe(7):
                break
            self.assertLess(self.h.now+100_000_000, self.q.cycle().continuation_deadline_ns)
            self.observe(source, 100_000_000)
        self.assertEqual(1, self.probe(7), 'only a new normal fit may issue another ticket')
        self.assertGreaterEqual(self.probe(1), proof)
        self.assertGreaterEqual(self.probe(6), self.first_fresh_start)
        self.assertEqual(2, self.probe(0))
        return self.h.next_move(source)

    def test_material_or_raw_unknown_waits_then_direct_anchor_zero_creates_a_new_current_model(self):
        for unknown in (False, True):
            with self.subTest(raw_unknown=unknown):
                source, opening, state, moves = self.admitted()
                count = self.probe(3)
                self.assertGreater(count, 0)
                bad = deepcopy(source)
                bad.tiles[(-1, 0)] = 'dirt'
                if unknown:
                    bad.signature = bytes([80])*23296
                self.assertEqual((0 if unknown else 2, 0, 0), self.h.motion(source, bad, 1))
                self.observe(bad)
                self.assert_wait(state, moves)
                self.assertEqual(count, self.probe(3), 'retained raw HUD samples are data, not old model authority')
                self.first_fresh_start = self.h.now+10_000_000-2
                self.observe(source)
                proof = self.h.number
                self.assertEqual((2, proof), (self.probe(0), self.probe(2)))
                command = self.new_phase(source, proof)
                self.assertGreater(command.id, opening.id)
                self.assertGreaterEqual(command.source_capture_id, proof)
                self.assertGreaterEqual(command.phase_sample_ns, self.first_fresh_start)
                self.assertEqual(self.binding(state), self.binding(self.q.cycle()))

    def test_invalid_stage_two_revokes_phase_preparation_and_proof_without_rebinding(self):
        source, _, state, moves = self.admitted()
        self.observe(source)
        self.assertEqual(2, self.probe(0))
        self.assertGreater(self.probe(1), 0)
        self.assertGreater(self.probe(2), 0)
        count = self.probe(3)
        bad = deepcopy(source)
        bad.tiles[(-1, 0)] = 'dirt'
        self.observe(bad)
        self.assert_wait(state, moves)
        self.assertEqual(count, self.probe(3))
        self.observe(bad)
        self.assert_wait(state, moves)

    def test_two_later_zero_frames_cannot_bridge_unknown_from_the_fixed_anchor(self):
        source, _, state, moves = self.admitted()
        a = deepcopy(source)
        rng = random.Random(108108)
        a.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
        b = deepcopy(a)
        self.assertEqual((0, 0, 0), self.h.motion(source, a, 1))
        self.assertEqual((2, 0, 0), self.h.motion(a, b, 1))
        self.observe(a)
        self.assert_wait(state, moves)
        self.observe(b)
        self.assert_wait(state, moves)
        self.assertEqual(0, self.probe(1))

    def test_known_motion_or_changed_door_permanently_refuses_later_anchor_zero(self):
        for fault in ('moved', 'tween', 'door'):
            with self.subTest(fault=fault):
                source, _, state, moves = self.admitted()
                if fault == 'door':
                    bad = deepcopy(source)
                    bad.tiles[(-2, 0)] = 'door'
                else:
                    bad = native.translated(source, 1, amount=9 if fault == 'moved' else 8)
                    self.assertEqual(1 if fault == 'moved' else 7, self.h.motion(source, bad, 1)[0])
                self.observe(bad)
                self.assertEqual(7, self.q.cycle().state)
                self.assertEqual(0, self.probe(0))
                self.observe(source)
                self.assertEqual((7, moves), (self.q.cycle().state, self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_new_goods_gold_protection_and_nonfull_scenes_never_become_wait_credit(self):
        for fault in ('item', 'gold', 'protection', 'partial', 'gold_state'):
            with self.subTest(fault=fault):
                source, _, _, moves = self.admitted()
                bad = deepcopy(source)
                if fault == 'item':
                    bad.tiles[(6, 2)] = 'item'
                    bad.protected.add((6, 2))
                elif fault == 'gold':
                    bad.tiles[(6, 2)] = 'gold'
                elif fault == 'protection':
                    bad.protected.add((6, 2))
                elif fault == 'partial':
                    bad.goods = 'partial'
                self.h.now += 10_000_000
                value = self.h.scene(2, 0 if fault == 'gold_state' else 2, bad, beat=True)
                self.h.observe_actual(value)
                self.assertEqual(7, self.q.cycle().state)
                self.observe(source)
                self.assertEqual((0, moves), (self.probe(0), self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_reserved_stage_three_does_not_gain_a_wait_or_resend(self):
        source, opening, state, moves, command = self.f.ticket()
        self.h, self.q = self.f.h, self.f.q
        self.assertEqual((3, 1), (self.probe(0), self.h.status().input_state))
        bad = deepcopy(source)
        bad.tiles[(-1, 0)] = 'dirt'
        self.observe(bad)
        self.assertEqual((7, 0, moves), (self.q.cycle().state, self.probe(0), self.h.status().moves))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
            max(self.h.now, command.not_before_ns), 1, 0, 1))
        self.observe(source)
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_wait_original_deadline_expires_with_no_further_capture_or_only_prefix_discards(self):
        for discarded in (False, True):
            with self.subTest(prefix_discard=discarded):
                source, _, state, moves = self.admitted()
                bad = deepcopy(source)
                bad.tiles[(-1, 0)] = 'dirt'
                self.observe(bad)
                self.assert_wait(state, moves)
                if discarded:
                    self.h.now = state.continuation_deadline_ns-1
                    self.assertEqual(0, self.h.observe_actual(self.h.scene(2, 2, source, beat=True),
                        prefix=self.h.prefix+1))
                self.h.now = state.continuation_deadline_ns+1
                ready, command = self.h.tick()
                self.assertEqual(7, self.q.cycle().state)
                self.assertEqual(0, self.probe(0))
                self.assertEqual((moves, state.continuation_deadline_ns),
                    (self.h.status().moves, self.q.cycle().continuation_deadline_ns))
                self.assertNotEqual(4, command.kind)


if __name__ == '__main__':
    unittest.main()
