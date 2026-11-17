"""TEST113: near FLOOR/DIRT palette changes retain only owned unsent zero.

Procedural fixed terrain and lighting exercise read-only scalar evidence and
public Controller ownership. Recorded phone PNGs remain outside these tests.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_motion067 as motion
from tests import test_native_plural_stationary103 as scalar
from tests import test_native_plural_wait103 as wait
from tests import test_native_clear_stationary095 as clear
from tests import test_native_passage072 as passage

CORE = native.CORE
SYMBOL = 'ng2_clear_plural_palette_stationary_zero'


def palette_pair(phase=2):
    pair = scalar.plural_phase_pair(phase)
    pair[1].tiles[scalar.cell(1, 1)] = 4
    return pair


class NativePaletteZero113Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='palette113-')
        directory = Path(cls.temp.name)
        shim = directory/'proof.c'
        present = 'int '+SYMBOL+'(' in (CORE/'NG2Navigation.c').read_text()
        shim.write_text('#include "'+str(CORE/'NG2Navigation.c')+'"\n'
            'int palette113(const NG2Scene*a,const NG2Scene*b,int d){'+
            ('return '+SYMBOL+'(a,b,d);' if present else
             '(void)a;(void)b;(void)d;return 0;')+'}\n')
        cls.libraries = {}
        for name, flags in (('o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = directory/(name+'.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-shared', '-fPIC', str(shim), '-lm', '-o', str(target)], check=True)
            cls.libraries[name] = lib = C.CDLL(str(target))
            for symbol in ('palette113', 'ng2_clear_plural_stationary_zero'):
                getattr(lib, symbol).argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene), C.c_int]
            lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                      C.c_int, C.POINTER(motion.Motion)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def proof(self, lib, pair, direction=3):
        saved = tuple(bytes(s) for s in pair)
        result = lib.palette113(C.byref(pair[0]), C.byref(pair[1]), direction)
        self.assertEqual(saved, tuple(bytes(s) for s in pair))
        return result

    def test_near_palette_phase_adds_zero_without_changing_global_motion_or_old_helper(self):
        for name, lib in self.libraries.items():
            for phase in (1, 2, 3, 4):
                for direction in (1, 2, 3, 4):
                    with self.subTest(build=name, phase=phase, direction=direction):
                        pair = palette_pair(phase)
                        observed = motion.Motion()
                        lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), direction, C.byref(observed))
                        self.assertEqual((0, 0, 0), (observed.kind, observed.dx, observed.dy))
                        self.assertEqual(0, lib.ng2_clear_plural_stationary_zero(
                            C.byref(pair[0]), C.byref(pair[1]), direction))
                        self.assertEqual(1, self.proof(lib, pair, direction),
                                         'independent zero evidence survives only a near floor palette change')

    def test_local_unknown_stone_origin_next_landmark_or_protection_never_qualifies(self):
        for lib in self.libraries.values():
            for fault in ('unknown', 'stone', 'origin', 'next', 'lost_old_stone',
                          'protection', 'item', 'door', 'gold', 'goods', 'flat', 'shifted'):
                with self.subTest(fault=fault):
                    pair = palette_pair()
                    if fault in ('unknown', 'stone'):
                        pair[1].tiles[scalar.cell(1, 1)] = 0 if fault == 'unknown' else 3
                    elif fault in ('origin', 'next'):
                        pair[1].tiles[scalar.cell(0, 0 if fault == 'origin' else -1)] = 4
                    elif fault == 'lost_old_stone':
                        pair[1].tiles[scalar.cell(-5, -2)] = 1
                    elif fault == 'protection': pair[1].protected_cells[scalar.cell(7, 2)] = 1
                    elif fault in ('item', 'door', 'gold'):
                        pair[1].tiles[scalar.cell(7, 2)] = {'item': 6, 'door': 5, 'gold': 2}[fault]
                    elif fault == 'goods': pair[1].goods = 1
                    elif fault == 'flat':
                        for scene in pair: scene.signature[:] = bytes([40])*23296
                    else:
                        source = bytes(pair[0].signature)
                        pair[1].signature[:] = bytes(source[y*224+(x+9)%224]
                            for y in range(104) for x in range(224))
                    self.assertEqual(0, self.proof(lib, pair))


class NativePaletteWait113Tests(unittest.TestCase):
    setUpClass = classmethod(wait.NativePluralWait103Tests.setUpClass.__func__)
    tearDownClass = classmethod(wait.NativePluralWait103Tests.tearDownClass.__func__)

    def test_ready_wait_survives_palette_then_uses_only_new_future_ticket_and_real_ack(self):
        before, after, old = wait.NativePluralWait103Tests.plural_wait(self)
        self.now += 20_000_000
        self.assertEqual(1, self.observe(after))
        changed = deepcopy(after)
        self.assertEqual('floor', changed.tiles[(1, 1)])
        changed.tiles[(1, 1)] = 'dirt'
        self.assertEqual((0, 0, 0), self.motion(before, changed, old.direction))
        self.now += 20_000_000
        self.assertEqual(1, self.observe(changed))
        self.assertEqual(0, self.status().reason,
                         'READY must re-prove fixed source zero through the qualified palette')
        new = self.future_ticket(changed)
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertGreater(new.source_capture_id, self.trigger_id)
        self.assertLessEqual(new.deadline_ns+self.status().lead_ns+50_000_000, self.parent_deadline)
        self.assertEqual(self.saved_credit, self.credit())
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new)
        self.assertEqual((3, 2), (self.status().inputs, self.status().moves))
        moved = native.translated(changed, new.direction)
        self.assertEqual((1, *native.DIRS[new.direction]), self.motion(changed, moved, new.direction))
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.observe(moved)
        self.assertEqual((0, 3, 3), (self.status().reason, self.status().inputs, self.status().moves))


for _name in ('setUp', 'scene', 'frame', 'observe', 'observe_actual', 'tick', 'status',
              'events', 'ack', 'fit', 'next_move', 'publish_procedural_candidate',
              'fresh_engine', 'recovery', 'recovery_samples', 'all_public_bytes',
              'reject_old_callbacks_without_mutation', 'motion_wait', 'credit',
              'choice', 'observed_vantage', 'observed_result', 'preparation_epoch',
              'armed', 'motion', 'assert_waiting', 'future_ticket', 'selected_motion'):
    setattr(NativePaletteWait113Tests, _name, getattr(clear.NativeClearStationary095Tests, _name))
NativePaletteWait113Tests.next_operation = passage.NativePassage072Tests.next_operation


if __name__ == '__main__':
    unittest.main()
