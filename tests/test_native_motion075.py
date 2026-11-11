"""TEST075: procedural evidence for one observed clear-floor translation.

These generated Scenes test complete L geometry, independent pixel phase and
strong blurred edges. They contain no received phone pixels and do not measure
shop reachability or iPhone beat timing.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import procedural_pair

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


def cell(x, y):
    return (y + 5) * 23 + x + 11


def corner(scene, x, y, sx=1, sy=1, kind=4):
    for point in ((x, y), (x - sx, y), (x, y - sy)):
        scene.tiles[cell(*point)] = 1
    for i in range(3):
        scene.tiles[cell(x - i * sx, y + sy)] = kind
        scene.tiles[cell(x + sx, y - i * sy)] = kind


def translation(direction=3, pixels=9, seed=75080):
    rng = random.Random(seed)
    world = bytearray([24] * (W * H))
    # Sparse, independently located bright points have little median texture,
    # but their blurred edges occupy two separated world bands. Adjacent pixel
    # phases share less support than a dense correlated random field.
    for y0, y1 in (((33, 43) if direction == 4 else (23, 34)),
                   ((68, 72) if direction == 3 else
                                            (77, 81) if direction == 4 else (69, 80))):
        for _ in range(14):
            x, y = rng.randrange(44, 174), rng.randrange(y0, y1)
            world[y * W + x] = rng.randrange(160, 200)
    pair = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                  gold_state=1) for _ in range(2)]
    for scene in pair:
        scene.tiles[:] = [1] * 230
    dx, dy = DIRS[direction]
    corner(pair[0], 4, 1)
    corner(pair[1], 4 - dx, 1 - dy)
    pair[0].signature[:] = world
    after = bytearray(W * H)
    sx, sy = -dx * pixels, -dy * pixels
    for y in range(H):
        for x in range(W):
            xx, yy = x + sx, y + sy
            if 0 <= xx < W and 0 <= yy < H:
                after[yy * W + xx] = world[y * W + x] * 5 // 4 + 4
    pair[1].signature[:] = after
    return pair


class NativeMotion075Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test075-motion-')
        cls.libraries = {}
        source = Path(os.environ.get('NECRO_TEST075_BASELINE_NAVIGATION',
                                     CORE / 'NG2Navigation.c'))
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                            '-pedantic', '-I', str(CORE), '-fPIC', '-shared',
                            str(source), '-lm', '-o', str(path)],
                           check=True, capture_output=True)
            lib = C.CDLL(str(path))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                      C.POINTER(Motion)]
            lib.ng2_motion.restype = C.c_int
            cls.libraries[name] = lib
        # Isolate the new proof from known legacy results. This harness adds
        # no production API, and contains no phone pixels.
        shim = Path(cls.temp.name) / 'proof.c'
        shim.write_text('#include "' + str(CORE / 'NG2Navigation.c') + '"\n' + r'''
int test075_corner(const NG2Scene*a,const NG2Scene*b,int sx,int sy) {
    return unique_corner_translation(a,b,sx,sy);
}
int test075_kernel(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
    return world_kernel_known(a,b,x,y,sx,sy);
}
int test075_phase_mask(int x,int y,int band) { return phase_band_mask(x,y,band); }
int test075_cache_equal(const NG2Scene*a,const NG2Scene*b) {
    StaticGradientCache *cache=(StaticGradientCache*)calloc(1,sizeof(*cache));
    int amount,d,su,ba,re[2],cs,cb,cr[2],equal=1;
    if(!cache) return 0;
    static_gradient_features(a,cache->before,cache->indices,&cache->count);
    static_gradient_features(b,cache->after,NULL,NULL);
    for(amount=0;amount<=18;++amount)for(d=1;d<=(amount?4:1);++d) {
        int sx=amount*ddx[d],sy=amount*ddy[d];
        gradient_texture(a,b,sx,sy,&su,&ba,re);
        static_gradient_texture(cache,sx,sy,&cs,&cb,cr);
        if(su!=cs || ba!=cb || re[0]!=cr[0] || re[1]!=cr[1]) equal=0;
    }
    free(cache);return equal;
}
int test075_proof(const NG2Scene*a,const NG2Scene*b,int dir,int initial,double gap,int sx,int sy) {
    View v[2]; Candidate c[73]; NG2Motion out={0}; int n=1,amount,d,k;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    c[0].sx=c[0].sy=0;c[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(&v[0],&v[1],c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
    /* Inject global phase qualification at its explicit boundary; the two
     * independent bands, geometry and all73 blur proof remain real. */
    for(k=0;k<73;++k) if(c[k].sx==sx && c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    c[0].score=0;c[1].score=gap;
    out.kind=initial;corner_blur_motion(a,b,dir,v,c,&out);return out.kind;
}
''')
        cls.proofs = {}
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (name + '-proof.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                            '-pedantic', '-I', str(CORE), '-fPIC', '-shared',
                            str(shim), '-lm', '-o', str(path)], check=True, capture_output=True)
            lib = C.CDLL(str(path))
            ptr = C.POINTER(Scene)
            lib.test075_corner.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test075_kernel.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int]
            lib.test075_phase_mask.argtypes = [C.c_int, C.c_int, C.c_int]
            lib.test075_cache_equal.argtypes = [ptr, ptr]
            lib.test075_proof.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_double,
                                         C.c_int, C.c_int]
            cls.proofs[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, pair, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def test_complete_corner_independent_phase_and_blurred_edges_prove_one_move(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual((1, dx, dy), self.result(lib,
                        translation(direction), direction))

    def proof(self, lib, pair, initial=0, gap=.08, sx=0, sy=9):
        return lib.test075_proof(C.byref(pair[0]), C.byref(pair[1]), 3,
                                 initial, gap, sx, sy)

    def geometry(self, lib, pair, sx=0, sy=9):
        return lib.test075_corner(C.byref(pair[0]), C.byref(pair[1]), sx, sy)

    def test_complete_old_corner_can_survive_other_old_corner_loss(self):
        for profile, lib in self.proofs.items():
            pair = translation()
            corner(pair[0], -4, -1, -1, -1)
            with self.subTest(profile=profile, disappearing_old_corner=True):
                self.assertEqual(1, self.geometry(lib, pair))
            corner(pair[1], -7, 1, -1, -1)
            with self.subTest(profile=profile, new_only_corner=True):
                self.assertEqual(1, self.geometry(lib, pair))

    def test_corner_requires_all_nine_cells_materials_and_unique_translation(self):
        points = [(4, 2), (3, 2), (4, 1)]
        points += [(4 - i, 3) for i in range(3)] + [(5, 2 - i) for i in range(3)]
        for profile, lib in self.proofs.items():
            for point in points:
                for kind in (0, 3 if point in points[3:] else 4):
                    pair = translation()
                    pair[1].tiles[cell(*point)] = kind
                    with self.subTest(profile=profile, point=point, kind=kind):
                        self.assertEqual(0, self.geometry(lib, pair))
            for label in ('no_old', 'no_new', 'second_translation'):
                pair = translation()
                if label in ('no_old', 'no_new'):
                    pair[0 if label == 'no_old' else 1].tiles[:] = [1] * 230
                else:
                    corner(pair[0], -4, -1, -1, -1)
                    corner(pair[1], -4, -2, -1, -1)
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.geometry(lib, pair))

    def test_new_proof_requires_clear_unprotected_item_free_observed_floor(self):
        cases = []
        for side in (0, 1):
            for field, values in (('goods', (1, 2)), ('gold_state', (0, 2, 3))):
                for value in values:
                    pair = translation()
                    setattr(pair[side], field, value)
                    cases.append((f'{side}:{field}:{value}', pair))
            for kind in (2, 6):
                pair = translation()
                pair[side].tiles[cell(8, 3)] = kind
                cases.append((f'{side}:remote:{kind}', pair))
            pair = translation()
            pair[side].protected_cells[cell(8, 3)] = 1
            cases.append((f'{side}:remote_protection', pair))
            for point in ((0, 0), (0, -1)):
                if side == 1 and point == (0, -1):
                    continue  # A future step is checked by the next Nav call.
                for kind in (0, 2, 3, 4, 5, 6):
                    pair = translation()
                    pair[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', pair))
        for profile, lib in self.proofs.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.proof(lib, pair))
            for kind in (0, 3, 4, 5):
                pair = translation()
                pair[1].tiles[cell(0, -1)] = kind
                with self.subTest(profile=profile, next_nav_checks_future=kind):
                    self.assertEqual(1, self.proof(lib, pair))

    def test_global_phase_unit_gap_boundary_and_known_results_are_preserved(self):
        for profile, lib in self.proofs.items():
            pair = translation()
            with self.subTest(profile=profile, exact_gap=True):
                self.assertEqual(1, self.proof(lib, pair, gap=.08))
                self.assertEqual(0, self.proof(lib, pair, gap=.079999))
            for sx, sy in ((0, 0), (0, 8), (0, -9), (0, 18), (9, 0)):
                with self.subTest(profile=profile, wrong_phase=(sx, sy)):
                    self.assertEqual(0, self.proof(lib, pair, sx=sx, sy=sy))
            for initial in range(1, 8):
                with self.subTest(profile=profile, known=initial):
                    self.assertEqual(initial, self.proof(lib, pair, initial=initial))

    def test_full_kernel_rejects_hidden_changed_or_ui_dependencies(self):
        offsets = [(x, y) for y in range(-2, 3) for x in range(-2, 3)
                   if abs(x) != 2 or abs(y) != 2]
        for profile, lib in self.proofs.items():
            pair = translation()
            self.assertEqual(1, lib.test075_kernel(C.byref(pair[0]), C.byref(pair[1]),
                                                  60, 30, 0, 9))
            for ox, oy in offsets:
                for side in (0, 1):
                    x, y = 60 + ox, 30 + oy + 9 * side
                    gx, gy = (4 * x - 34) // 36 - 11, (4 * y - 9) // 36 - 5
                    for kind in (0, 3, 5, 6, 'protect'):
                        changed = deepcopy(pair)
                        if kind == 'protect':
                            changed[side].protected_cells[cell(gx, gy)] = 1
                        else:
                            changed[side].tiles[cell(gx, gy)] = kind
                        with self.subTest(profile=profile, offset=(ox, oy), side=side,
                                          hidden_dependency=kind):
                            self.assertEqual(0, lib.test075_kernel(C.byref(changed[0]),
                                C.byref(changed[1]), 60, 30, 0, 9))
            for x, y in ((101, 44), (99, 80), (40, 30), (177, 30)):
                with self.subTest(profile=profile, ui_or_edge=(x, y)):
                    self.assertEqual(0, lib.test075_kernel(C.byref(pair[0]),
                        C.byref(pair[1]), x, y, 0, 0))
            # The only UI point in this 5x5 box is an unused diagonal corner.
            self.assertEqual(1, lib.test075_kernel(C.byref(pair[0]), C.byref(pair[1]),
                                                  101, 41, 0, 0))
            for x, y, band, expected in ((109, 30, 0, 1), (110, 30, 0, 0),
                                         (113, 30, 1, 0), (114, 30, 1, 1),
                                         (102, 44, 0, 0), (114, 38, 1, 0)):
                self.assertEqual(expected, lib.test075_phase_mask(x, y, band))

    def test_partial_eight_and_half_pixel_backgrounds_never_gain_unit_credit(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                low, high = translation(direction, pixels=8), translation(direction, pixels=9)
                half = deepcopy(low)
                half[1].signature[:] = bytes((a + b) // 2 for a, b in
                    zip(low[1].signature, high[1].signature))
                for label, pair in (('eight', low), ('eight_and_half', half)):
                    with self.subTest(profile=profile, direction=direction, partial=label):
                        self.assertNotEqual(1, self.result(lib, pair, direction)[0])

    def test_world_letters_cannot_move_a_static_or_partial_background(self):
        rng = random.Random(75081)
        letters = bytes(rng.randrange(20, 240) for _ in range(39 * 42))
        cases = []
        for background in (0, 8, 8.5):
            for overlay in (0, 9, 18, None, 'appear'):
                pair = translation(pixels=int(background))
                if background == 8.5:
                    nine = translation(pixels=9)
                    pair[1].signature[:] = bytes((a + b) // 2 for a, b in
                        zip(pair[1].signature, nine[1].signature))
                for y in range(38, 80):
                    for x in range(115, 154):
                        value = letters[(y - 38) * 39 + x - 115]
                        if overlay != 'appear':
                            pair[0].signature[y * W + x] = value
                        shift = 9 if overlay == 'appear' else overlay
                        if shift is not None and y + shift < H:
                            pair[1].signature[(y + shift) * W + x] = value
                cases.append((background, overlay, pair))
        for profile, lib in self.proofs.items():
            for background, overlay, pair in cases:
                with self.subTest(profile=profile, background=background, letters=overlay):
                    self.assertEqual(0, self.proof(lib, pair))

    def test_independent_bands_weak_support_and_aliases_are_required(self):
        cases = []
        for label in ('left_only', 'right_only', 'upper_only', 'lower_only', 'weak', 'alias'):
            pair = translation()
            for scene in pair:
                pixels = bytearray(scene.signature)
                for y in range(H):
                    for x in range(W):
                        if label == 'weak':
                            pixels[y * W + x] = 24
                        elif label == 'alias':
                            pixels[y * W + x] = 24 + 120 * (x % 9 == 0 and y % 9 == 0)
                        elif not (x < 110 if label == 'left_only' else
                                  x >= 114 if label == 'right_only' else
                                  y < 50 if label == 'upper_only' else y >= 54):
                            pixels[y * W + x] = 0
                scene.signature[:] = pixels
            cases.append((label, pair))
        for label, pixels in (('left_static', 0), ('left_partial', 8),
                              ('left_low_gap', 8.5)):
            pair = translation()
            left = translation(pixels=int(pixels))
            if pixels == 8.5:
                nine = translation()
                left[1].signature[:] = bytes((a + b) // 2 for a, b in
                    zip(left[1].signature, nine[1].signature))
            for y in range(H):
                for x in range(110):
                    pair[1].signature[y * W + x] = left[1].signature[y * W + x]
            cases.append((label, pair))
        for profile, lib in self.proofs.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.proof(lib, pair))

    def test_existing_primary_and_invalid_inputs_remain_unchanged(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for pixels, expected in ((0, (2, 0, 0)), (8, (7, 0, 0)),
                                         (9, (1, dx, dy)), (18, (6, 2 * dx, 2 * dy)),
                                         (-9, (6, -dx, -dy))):
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertEqual(expected, self.result(lib,
                            procedural_pair(direction, pixels=pixels, overlay=False), direction))
            for side in (0, 1):
                for field, value in (('state', 0), ('abi_version', 2), ('goods', 3),
                                     ('struct_size', C.sizeof(Scene) - 1)):
                    pair = translation()
                    setattr(pair[side], field, value)
                    out = Motion(99, 99, 99)
                    with self.subTest(profile=profile, invalid=(side, field)):
                        self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                                         3, C.byref(out)))
                        self.assertEqual((0, 0, 0), (out.kind, out.dx, out.dy))
        # The zero-only speedup must preserve all73 counts, including weak,
        # partial and newly revealed fields; it cannot adjust the proof.
        from tests.test_native_static075 import stationary_pair
        pairs = [stationary_pair(reveal=True), translation(), translation(pixels=8)]
        changed = stationary_pair()
        changed[0].tiles[cell(-3, -2)] = 0
        changed[1].protected_cells[cell(-2, 2)] = 1
        pairs.append(changed)
        for profile, lib in self.proofs.items():
            for i, pair in enumerate(pairs):
                with self.subTest(profile=profile, cached_all73_equivalence=i):
                    self.assertEqual(1, lib.test075_cache_equal(C.byref(pair[0]),
                                                               C.byref(pair[1])))


if __name__ == '__main__':
    unittest.main()
