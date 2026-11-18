"""TEST115 reuse local motion work without changing any recognition result.

Deterministic counters belong only to the compiled test copy. No timer limit,
phone image, global production cache or replacement Motion supplies authority.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_controller as native
from tests.test_native_motion075 import Motion
from tests.test_native_passage115 import candidate_pair, CELL

CORE = Path(os.environ.get('NECRO115_SHARED_CORE', native.CORE))


class NativeSharedPassageZero115Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='shared115-')
        source = (CORE/'NG2Navigation.c').read_text()
        combined = 'int ng2_unlocalized_passage_motion_zero(' in source
        # Count execution, not the occurrence of source strings. The two
        # counters never exist in the product translation unit.
        for signature, counter in (('static void view(const unsigned char raw[N],View *out) {', 'views'),
                                   ('static double intensity(const View *a,const View *b,int sx,int sy) {', 'raw')):
            if source.count(signature) != 1:
                raise AssertionError('the exact instrumented primitive must exist once')
            source = source.replace(signature, signature+'++test115_'+counter+';')
        source = '#include <stdint.h>\nstatic uint64_t test115_views,test115_raw;\n'+source
        source += '\nvoid test115_reset(void){test115_views=test115_raw=0;}\n'
        source += 'uint64_t test115_count(int field){return field?test115_raw:test115_views;}\n'
        source += '''int test115_combined(const NG2Scene*a,const NG2Scene*b,int32_t d,NG2Motion*out,int32_t*zero){
            if(!zero)return 0;
        ''' + ('''return ng2_unlocalized_passage_motion_zero(a,b,d,out,zero);
        }\n''' if combined else '''int result;*zero=0;
            result=ng2_motion(a,b,d,out);
            if(result&&out->kind==NG2_MOTION_UNKNOWN&&!out->dx&&!out->dy)
                *zero=ng2_unlocalized_passage_stationary_zero(a,b,d);
            return result;
        }\n''')
        path = Path(cls.temp.name)/'instrumented.c'; path.write_text(source)
        target = Path(cls.temp.name)/'instrumented.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
            '-Wall', '-Wextra', '-Werror', '-pedantic', '-shared', '-fPIC', '-I'+str(CORE),
            str(path), '-lm', '-o', str(target)], check=True)
        cls.lib = lib = C.CDLL(str(target))
        pointer = C.POINTER(native.Scene)
        lib.ng2_motion.argtypes = [pointer, pointer, C.c_int32, C.POINTER(Motion)]
        lib.ng2_unlocalized_passage_stationary_zero.argtypes = [pointer, pointer, C.c_int32]
        lib.test115_combined.argtypes = [pointer, pointer, C.c_int32, C.POINTER(Motion), C.POINTER(C.c_int32)]
        lib.test115_count.argtypes = [C.c_int]; lib.test115_count.restype = C.c_uint64

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def compare(self, pair, direction=3):
        first, second = (C.byref(scene) for scene in pair)
        saved = tuple(bytes(scene) for scene in pair)
        expected, actual, zero = Motion(), Motion(), C.c_int32(99)
        self.lib.test115_reset()
        old_return = self.lib.ng2_motion(first, second, direction, C.byref(expected))
        old_zero = (self.lib.ng2_unlocalized_passage_stationary_zero(first, second, direction)
            if old_return and expected.kind == 0 and expected.dx == expected.dy == 0 else 0)
        separate = self.lib.test115_count(0), self.lib.test115_count(1)
        self.lib.test115_reset()
        new_return = self.lib.test115_combined(first, second, direction, C.byref(actual), C.byref(zero))
        shared = self.lib.test115_count(0), self.lib.test115_count(1)
        self.assertEqual((old_return, bytes(expected), old_zero), (new_return, bytes(actual), zero.value))
        self.assertEqual(saved, tuple(bytes(scene) for scene in pair))
        return separate, shared, expected

    def test_unknown_positive_reuses_two_views_and_all_original_raw_candidates(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                separate, shared, observed = self.compare(candidate_pair(), direction)
                self.assertEqual((0, 0, 0), (observed.kind, observed.dx, observed.dy))
                self.assertEqual((4, 146), separate)
                self.assertEqual((2, 73), shared,
                    'the same normal Motion and strict scalar proof need one local view/raw-candidate build')

    def test_invalid_layout_and_known_motion_keep_normal_precedence_and_full_result(self):
        for fault in ('clear', 'gold', 'item', 'protected', 'origin', 'abi', 'state', 'translated'):
            for direction in (1, 2, 3, 4):
                with self.subTest(fault=fault, direction=direction):
                    pair = candidate_pair()
                    if fault == 'clear': pair[1].gold_state = 1
                    elif fault == 'gold': pair[1].tiles[CELL(7, 2)] = 2
                    elif fault == 'item': pair[1].tiles[CELL(7, 2)] = 6
                    elif fault == 'protected': pair[1].protected_cells[CELL(7, 2)] = 1
                    elif fault == 'origin': pair[1].tiles[CELL(0, 0)] = 0
                    elif fault == 'abi': pair[1].abi_version = 2
                    elif fault == 'state': pair[1].state = 1
                    else:
                        source = pair[0]; translated = deepcopy(source)
                        translated.tiles[:] = bytes(230)
                        dx, dy = native.DIRS[direction]
                        for y in range(-5, 5):
                            for x in range(-11, 12):
                                tx, ty = x-dx, y-dy
                                if -11 <= tx <= 11 and -5 <= ty <= 4:
                                    translated.tiles[CELL(tx, ty)] = source.tiles[CELL(x, y)]
                        image = native.Image.frombytes('L', (224, 104), bytes(source.signature))
                        shifted = native.Image.new('L', image.size); shifted.paste(image, (-9*dx, -9*dy))
                        translated.signature[:] = shifted.tobytes(); pair[1] = translated
                    self.compare(pair, direction)
        for direction in (0, 5, -1): self.compare(candidate_pair(), direction)
        first, second = candidate_pair(); result = Motion(7, 7, 7); zero = C.c_int32(99)
        self.assertEqual(0, self.lib.test115_combined(C.byref(first), C.byref(second), 1, None, C.byref(zero)))
        self.assertEqual(0, zero.value)
        self.assertEqual(0, self.lib.test115_combined(C.byref(first), C.byref(second), 1, C.byref(result), None))
        self.assertEqual((7, 7, 7), (result.kind, result.dx, result.dy))


if __name__ == '__main__':
    unittest.main()
