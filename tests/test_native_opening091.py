"""TEST091: independent zero-motion evidence for a known opening door.

These procedural signatures are not received iPhone pixels. A narrow L of
terrain has a fixed high-frequency illumination change which disappears in
the independent blur. Opening is zero credit; the following entry is separate.
"""
import ctypes as C
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion074 import Motion, lit_opening


CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def sparse_opening(direction=3, seed=91093):
    pair = lit_opening(direction, 91091)
    for frame in pair:
        frame.tiles[:] = [0] * 230
        for y in range(5):
            for x in range(-1, 6 if y >= 1 else 2):
                frame.tiles[cell(x, y)] = 1 if x == 0 or y >= 2 else 4
    dx, dy = DIRS[direction]
    for side in (-1, 1):
        for frame in pair:
            frame.tiles[cell(dx + side * dy, dy - side * dx)] = 2
    pair[0].tiles[cell(dx, dy)] = 5
    pair[1].tiles[cell(dx, dy)] = 1
    for frame in pair:
        frame.tiles[cell(0, 0)] = 1
    rng = random.Random(seed)
    pair[0].signature[:] = bytes(
        rng.randrange(40, 111) if (
            (98 <= i % W < 125 and 37 <= i // W < 90)
            or (125 <= i % W < 161 and 55 <= i // W < 96)) else 0
        for i in range(W * H))
    # Three adjacent samples sum to zero. This isolates blur quality from
    # the legacy 95% unblurred detail/gradient evidence without real pixels.
    pair[1].signature[:] = bytes(
        value + 30 * ((i % W + i // W) % 3 - 1) if value else 0
        for i, value in enumerate(pair[0].signature))
    return pair


class NativeOpening091Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test091-opening-')
        cls.libraries = {}
        external = os.environ.get('NECRO_TEST091_OPENING_LIBRARY')
        if external:
            cls.libraries['external'] = C.CDLL(external)
        else:
            shim = Path(cls.temp.name) / 'proof.c'
            shim.write_text('#include "' + str(CORE / 'NG2Navigation.c') + '"\n' + r'''
int test091_opening(const NG2Scene*a,const NG2Scene*b,int d,int initial,int mode) {
    View v[2];Candidate c[73];NG2Motion out={0};int n=1,amount,k;
    view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(k=1;k<=4;++k) {
        c[n].sx=amount*ddx[k];c[n].sy=amount*ddy[k];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
    if(mode==1)c[0].score=NAN;
    if(mode==2)c[1].score=INFINITY;
    if(mode==3){c[0].score=0;c[1].score=.079;}
    if(mode==4){c[0].score=0;c[1].score=.08;}
    if(mode==5)c[0].sx=1;
    if(mode==6)c[72].score=NAN;
    if(mode==7)c[72].score=-INFINITY;
    if(mode==8)c[72].score=INFINITY;
    if(mode==9){c[0].score=0;c[1].score=0;}
    if(mode==10){c[0].score=.2;c[1].score=.1;}
    out.kind=initial;
    opening_blur_quality_motion(a,b,d,v,c,&out);
    return out.kind;
}
double test091_opening_blur(const NG2Scene*a,const NG2Scene*b) {
    View v[2];unsigned char included[N];
    view(a->signature,v);view(b->signature,v+1);stationary_blur_mask(included);
    return stationary_blur_phase(v,v+1,0,0,included);
}
''')
            for profile, flags in (
                    ('unchanged_o0', ['-O0']),
                    ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
                library = Path(cls.temp.name) / (profile + '.so')
                subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra',
                                '-Werror', '-pedantic', '-I', str(CORE),
                                '-fPIC', '-shared', str(shim), '-lm', '-o',
                                str(library)], check=True, capture_output=True)
                cls.libraries[profile] = C.CDLL(str(library))
        for library in cls.libraries.values():
            library.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                          C.c_int32, C.POINTER(Motion)]
            library.ng2_motion.restype = C.c_int
            if hasattr(library, 'test091_opening'):
                library.test091_opening.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                                    C.c_int, C.c_int, C.c_int]
                library.test091_opening_blur.argtypes = [C.POINTER(Scene), C.POINTER(Scene)]
                library.test091_opening_blur.restype = C.c_double

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, library, pair, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, library.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                             direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, library, pair, direction=3, initial=0, mode=0):
        self.assertTrue(hasattr(library, 'test091_opening'))
        return library.test091_opening(C.byref(pair[0]), C.byref(pair[1]),
                                       direction, initial, mode)

    def test_independently_blurred_static_opening_is_zero_credit(self):
        for profile, library in self.libraries.items():
            for direction in DIRS:
                for seed in (91093, 91094):
                    with self.subTest(profile=profile, direction=direction, seed=seed):
                        self.assertEqual((3, 0, 0), self.result(
                            library, sparse_opening(direction, seed), direction))

    def test_new_proof_requires_complete_safe_opening_geometry(self):
        cases = []
        for side in (0, 1):
            for point in ((0, 0), (0, -1)):
                pair = sparse_opening()
                pair[side].protected_cells[cell(*point)] = 1
                cases.append((f'protected:{side}:{point}', pair))
            for point in ((-1, -1), (1, -1)):
                pair = sparse_opening()
                pair[side].tiles[cell(*point)] = 1
                cases.append((f'bracket:{side}:{point}', pair))
            for field, value in (('state', 0), ('gold_state', 1)):
                pair = sparse_opening()
                setattr(pair[side], field, value)
                cases.append((f'{field}:{side}', pair))
        for side, point, kind in ((0, (0, 0), 4), (1, (0, 0), 4),
                                  (0, (0, -1), 1), (1, (0, -1), 5)):
            pair = sparse_opening()
            pair[side].tiles[cell(*point)] = kind
            cases.append((f'endpoint:{side}:{point}', pair))
        pair = sparse_opening()
        pair[0].tiles[cell(5, 0)] = 2
        cases.append(('observed_old_gold_disappeared', pair))
        for goods in ((1, 0), (0, 2), (1, 2), (2, 2)):
            pair = sparse_opening()
            pair[0].goods, pair[1].goods = goods
            cases.append((f'goods:{goods}', pair))
        for profile, library in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual(0, self.proof(library, pair))
            for goods in ((0, 0), (0, 1), (1, 1)):
                pair = sparse_opening()
                pair[0].goods, pair[1].goods = goods
                with self.subTest(profile=profile, allowed_goods=goods):
                    self.assertEqual(3, self.proof(library, pair))

    def test_raw_winner_runner_and_all_candidate_validity_are_required(self):
        for profile, library in self.libraries.items():
            for mode in (1, 2, 3, 5, 6, 7, 9, 10):
                with self.subTest(profile=profile, rejected_mode=mode):
                    self.assertEqual(0, self.proof(library, sparse_opening(), mode=mode))
            for mode in (0, 4, 8):
                with self.subTest(profile=profile, accepted_mode=mode):
                    self.assertEqual(3, self.proof(library, sparse_opening(), mode=mode))

    def test_blur_is_independent_absolute_quality_and_does_not_override_known(self):
        pair = sparse_opening()
        pair[1].signature[:] = bytes(
            30 + 3 * value // 2 + 30 * ((i % W + i // W) % 3 - 1)
            if value else 0 for i, value in enumerate(pair[0].signature))
        for profile, library in self.libraries.items():
            with self.subTest(profile=profile):
                quality = library.test091_opening_blur(C.byref(pair[0]), C.byref(pair[1]))
                self.assertGreater(quality, .45)
                self.assertEqual(0, self.proof(library, pair))
                # An independent new-proof refusal must not revoke an older
                # opening proof or replace any existing motion classification.
                self.assertEqual((3, 0, 0), self.result(library, pair))
                for initial in range(1, 7):
                    self.assertEqual(initial, self.proof(
                        library, sparse_opening(), initial=initial))

    def test_real_unit_pixels_are_never_recast_as_zero_opening(self):
        for profile, library in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                pair = sparse_opening(direction)
                old = bytes(pair[1].signature)
                shifted = bytearray(W * H)
                for y in range(H):
                    for x in range(W):
                        xx, yy = x - 9 * dx, y - 9 * dy
                        if 0 <= xx < W and 0 <= yy < H:
                            shifted[yy * W + xx] = old[y * W + x]
                pair[1].signature[:] = shifted
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual(0, self.proof(library, pair, direction))


if __name__ == '__main__':
    unittest.main()
