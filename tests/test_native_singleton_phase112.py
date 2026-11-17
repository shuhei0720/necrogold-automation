"""TEST112: one old STONE and a unit lighting phase qualify only unsent zero.

Procedural fixed worlds reuse the independently specified 095/103 material and
lighting fixtures. No recorded pixels or absent future device responses supply
the expectations. Global Motion stays UNKNOWN and Controller retains ownership.
"""
import ctypes as C
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import unittest

from tests import test_native_controller as fixture
from tests import test_native_motion067 as motion067
from tests import test_native_plural_stationary103 as scalar103
from tests import test_native_plural_wait103 as wait103
from tests import test_native_clear_stationary095 as clear095
from tests import test_native_passage072 as passage

CORE = fixture.CORE
SYMBOL = 'ng2_clear_singleton_phase_stationary_zero'


def phase_pair(direction=2):
    pair = scalar103.plural_phase_pair(direction)
    for scene in pair:
        scene.tiles[scalar103.cell(4, 1)] = 1
    return pair


class NativeSingletonPhase112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='singleton-phase112-')
        directory = Path(cls.temp.name)
        cls.sources = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                       (CORE/'NG2Navigation.c', CORE/'NG2Core.h', Path(__file__))}
        present = 'int ' + SYMBOL + '(' in (CORE/'NG2Navigation.c').read_text()
        shim = directory/'proof.c'
        shim.write_text('#include "' + str(CORE/'NG2Navigation.c') + '"\n' +
            'int phase112(const NG2Scene*a,const NG2Scene*b,int d){\n' +
            ('return ' + SYMBOL + '(a,b,d);' if present else '(void)a;(void)b;(void)d;return 0;') + '\n}\n')
        cls.libraries = {}
        for name, flags in (('o0', ['-O0']), ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in cls.sources.items())
            target = directory/(name+'.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(shim), '-lm', '-o', str(target)], check=True)
            cls.libraries[name] = lib = C.CDLL(str(target))
            for symbol in ('phase112', 'ng2_clear_singleton_stationary_zero', 'ng2_clear_plural_stationary_zero'):
                getattr(lib, symbol).argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene), C.c_int]
                getattr(lib, symbol).restype = C.c_int
            lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene), C.c_int,
                                      C.POINTER(motion067.Motion)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def proof(self, lib, pair, direction=3):
        original = tuple(bytes(s) for s in pair)
        result = lib.phase112(C.byref(pair[0]), C.byref(pair[1]), direction)
        self.assertEqual(original, tuple(bytes(s) for s in pair), 'qualification is read-only')
        return result

    def test_each_lighting_phase_and_action_adds_only_read_only_zero_qualification(self):
        for name, lib in self.libraries.items():
            for phase in (1, 2, 3, 4):
                pair = phase_pair(phase)
                self.assertEqual(1, list(pair[0].tiles).count(3))
                for direction in (1, 2, 3, 4):
                    with self.subTest(build=name, phase=phase, direction=direction):
                        motion = motion067.Motion()
                        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                                         direction, C.byref(motion)))
                        self.assertEqual((0, 0, 0), (motion.kind, motion.dx, motion.dy))
                        self.assertEqual(0, lib.ng2_clear_singleton_stationary_zero(
                            C.byref(pair[0]), C.byref(pair[1]), direction))
                        self.assertEqual(0, lib.ng2_clear_plural_stationary_zero(
                            C.byref(pair[0]), C.byref(pair[1]), direction))
                        self.assertEqual(1, self.proof(lib, pair, direction),
                                         'one old landmark and the existing supported unit-phase proof are independent')

    def test_old_landmark_two_dimensional_dirt_and_near_floor_are_required(self):
        faults = ('old_stone_loss', 'new_only_stone', 'two_old_stones', 'dirt_count',
                  'collinear_dirt', 'origin', 'target', 'near_floor', 'protection',
                  'gold', 'door', 'item', 'goods', 'nonfloor', 'unknown_gold', 'abi', 'size')
        for name, lib in self.libraries.items():
            for fault in faults:
                with self.subTest(build=name, fault=fault):
                    pair = phase_pair()
                    if fault in ('old_stone_loss', 'new_only_stone'):
                        pair[1].tiles[scalar103.cell(-5, -2)] = 1
                        if fault == 'new_only_stone': pair[1].tiles[scalar103.cell(4, 1)] = 3
                    elif fault == 'two_old_stones':
                        for s in pair: s.tiles[scalar103.cell(4, 1)] = 3
                    elif fault in ('dirt_count', 'collinear_dirt'):
                        for s in pair:
                            for i, kind in enumerate(s.tiles):
                                if kind == 4: s.tiles[i] = 1
                            for x, y in (scalar103.DIRT[:8] if fault == 'dirt_count' else
                                         tuple((x, -2) for x in range(-4, 5))):
                                s.tiles[scalar103.cell(x, y)] = 4
                    elif fault == 'origin': pair[1].tiles[scalar103.cell(0, 0)] = 4
                    elif fault == 'target': pair[1].tiles[scalar103.cell(0, -1)] = 4
                    elif fault == 'near_floor': pair[1].tiles[scalar103.cell(1, -1)] = 4
                    elif fault == 'protection': pair[1].protected_cells[scalar103.cell(8, 2)] = 1
                    elif fault in ('gold', 'door', 'item'):
                        pair[1].tiles[scalar103.cell(8, 2)] = {'gold': 2, 'door': 5, 'item': 6}[fault]
                    elif fault == 'goods': pair[1].goods = 1
                    elif fault == 'nonfloor': pair[1].state = 1
                    elif fault == 'unknown_gold': pair[1].gold_state = 0
                    elif fault == 'abi': pair[1].abi_version = 0
                    else: pair[1].struct_size = 0
                    self.assertEqual(0, self.proof(lib, pair), fault)

    def test_known_zero_translated_texture_and_missing_independent_bands_do_not_qualify(self):
        for name, lib in self.libraries.items():
            for fault in ('same_frame', 'shifted', 'upper_band', 'lower_band', 'flat'):
                with self.subTest(build=name, fault=fault):
                    pair = phase_pair()
                    if fault == 'same_frame': pair[1] = deepcopy(pair[0])
                    elif fault == 'shifted':
                        source = bytes(pair[0].signature)
                        pair[1].signature[:] = bytes(source[y*224+(x+9)%224]
                            for y in range(104) for x in range(224))
                    else:
                        for s in pair:
                            values = bytearray(s.signature)
                            for y in range(104):
                                # These world/axis planes split at y52 and
                                # depend on radius-two raw neighborhoods.
                                if fault == 'flat' or (fault == 'upper_band' and y < 54) or (
                                        fault == 'lower_band' and y >= 50):
                                    values[y*224:(y+1)*224] = bytes([7])*224
                            s.signature[:] = values
                    self.assertEqual(0, self.proof(lib, pair), fault)

    def test_null_and_out_of_range_direction_are_rejected(self):
        for name, lib in self.libraries.items():
            pair = phase_pair()
            for direction in (-1, 0, 5):
                self.assertEqual(0, self.proof(lib, pair, direction), name)
            for a, b in ((None, C.byref(pair[1])), (C.byref(pair[0]), None), (None, None)):
                self.assertEqual(0, lib.phase112(a, b, 3), name)


class NativeSingletonPhaseWait112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear095.NativeClearStationary095Tests.setUpClass.__func__(cls)
        cls.lib.ng2_clear_plural_stationary_zero.argtypes = [C.POINTER(fixture.Scene),
            C.POINTER(fixture.Scene), C.c_int32]

    tearDownClass = classmethod(clear095.NativeClearStationary095Tests.tearDownClass.__func__)

    def plural_wait(self):
        # The single old landmark remains outside the route and both HUD masks
        # after the two public, observed moves. It is never a new-only anchor.
        room = passage.passage_room(mouth=(-2, -3))
        room.tiles[(-5, -2)] = 'stone'
        with patch.object(passage, 'passage_room', return_value=room):
            terrain, second = self.armed('passage')
        self.ack(second)
        terrain = fixture.translated(terrain, second.direction)
        self.now = max(self.now, second.target_ns + 80_000_002)
        self.assertEqual(1, self.observe(terrain))
        self.assertEqual((2, 2, 1),
            (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        self.verified_ns = self.now
        before, after = deepcopy(terrain), deepcopy(terrain)
        before.signature, after.signature = wait103.room_phase_pair(self.frame(terrain))
        self.now += 10_000_000
        self.assertEqual(1, self.observe(before))
        old = passage.NativePassage072Tests.next_move(self, before)
        self.assertIn(old.direction, (1, 3))
        self.assertEqual((0, 0, 0), self.motion(before, after, old.direction), 'global Motion stays UNKNOWN')
        self.assertEqual((2, 0, 0), self.motion(after, after, old.direction))
        a, b = self.frame(before), self.frame(after)
        self.assertEqual(1, list(a.tiles).count(3))
        self.assertEqual(0, self.lib.ng2_clear_singleton_stationary_zero(C.byref(a), C.byref(b), old.direction))
        self.assertEqual(0, self.lib.ng2_clear_plural_stationary_zero(C.byref(a), C.byref(b), old.direction))
        self.parent_deadline = min(old.source_start_ns + 3 * fixture.SECOND,
            old.phase_sample_ns + 3 * fixture.SECOND, self.verified_ns + 12 * fixture.SECOND,
            self.status().walk_started_ns + 45 * fixture.SECOND,
            self.status().started_ns + 180 * fixture.SECOND)
        self.original_period = self.status().beat_period_ns
        self.saved_credit = self.credit()
        self.saved_position = (self.status().x, self.status().y)
        self.now = old.deadline_ns - 30_000_000
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now + 2 * self.original_period)
        self.assertEqual(1, self.observe(after))
        self.trigger_id = self.number
        self.assert_waiting(old)
        return before, after, old


# Reuse the existing public-operation assertions verbatim under the newly
# specified single-landmark fixture; do not inherit/discover unrelated cases.
for _name in ('setUp', 'scene', 'frame', 'observe', 'observe_actual', 'tick', 'status',
              'events', 'ack', 'fit', 'next_move', 'publish_procedural_candidate',
              'fresh_engine', 'recovery', 'recovery_samples', 'all_public_bytes',
              'reject_old_callbacks_without_mutation', 'motion_wait', 'credit',
              'choice', 'observed_vantage', 'observed_result', 'preparation_epoch',
              'armed', 'motion', 'assert_waiting', 'future_ticket', 'selected_motion'):
    setattr(NativeSingletonPhaseWait112Tests, _name,
            getattr(clear095.NativeClearStationary095Tests, _name))
NativeSingletonPhaseWait112Tests.next_operation = passage.NativePassage072Tests.next_operation

for _name in ('test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket',
              'test_plural_proof_needs_independent_stable_current_prefix_capture',
              'test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero',
              'test_original_wait_and_parent_equalities_never_renew_from_plural_proof',
              'test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait',
              'test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back'):
    setattr(NativeSingletonPhaseWait112Tests, _name, getattr(wait103.NativePluralWait103Tests, _name))


if __name__ == '__main__':
    unittest.main()
