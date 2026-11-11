"""TEST079: prove a past unit when lighting first reveals a closed gold gate.

Sparse procedural points give the legacy median fewer than300 samples while
fixed-axis neighbors provide independent evidence in both camera bands. The
maps/signatures are generated here; none is a phone frame or a future replay.
"""
import ctypes as C
from copy import deepcopy
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_blocked067 import Decision, Entrance

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def pair(direction=1, amount=1, pixels=None, band=None):
    rng = random.Random(79079)
    world = bytearray([24] * (W * H))
    for index, ys in enumerate((range(30, 43, 3), range(60, 76, 3))):
        choices = [(x, y) for y in ys for x in range(51, 91, 3)]
        rng.shuffle(choices)
        for x, y in choices[:50]:
            value = rng.randrange(160, 224)
            if band is None or index == band:
                world[y * W + x] = value
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                           gold_state=2) for _ in range(2)]
    for scene in (before, after):
        scene.tiles[:] = [1] * 230
    dx, dy = DIRS[direction]
    rotate = {1: lambda x, y: (x, y), 2: lambda x, y: (-x, -y),
              3: lambda x, y: (-y, x), 4: lambda x, y: (y, -x)}[direction]
    # Canonical LEFT: singleton(-2,-2) becomes the near GOLD(-1,-2).
    # Previously UNKNOWN door and far bracket become visible only afterward.
    old = {(-2, -2): 2, (-1, -2): 0, (0, -2): 0,
           (-2, -1): 3, (0, -1): 3, (-2, 1): 3, (3, 1): 3}
    for (x, y), kind in old.items():
        xx, yy = rotate(x, y)
        before.tiles[cell(xx, yy)] = kind
        xx -= dx * amount; yy -= dy * amount
        if -11 <= xx <= 11 and -5 <= yy <= 4:
            after.tiles[cell(xx, yy)] = kind
    for x, y, kind in ((-1, -2, 5), (0, -2, 2)):
        xx, yy = rotate(x, y)
        xx -= dx * amount; yy -= dy * amount
        if -11 <= xx <= 11 and -5 <= yy <= 4:
            after.tiles[cell(xx, yy)] = kind
    # An unrelated old STONE changes classification; it is not an anchor.
    xx, yy = rotate(3, 1)
    xx -= dx * amount; yy -= dy * amount
    if -11 <= xx <= 11 and -5 <= yy <= 4:
        after.tiles[cell(xx, yy)] = 4
    before.signature[:] = world
    shift = 9 * amount if pixels is None else pixels
    moved = bytearray([24] * (W * H))
    for y in range(H):
        for x in range(W):
            xx, yy = x - dx * shift, y - dy * shift
            if 0 <= xx < W and 0 <= yy < H:
                moved[int(yy) * W + int(xx)] = world[y * W + x]
    after.signature[:] = moved
    return [before, after]


SHIM = r'''
int test079_present(void) { return TEST079_PRESENT; }
static void test079_candidates(const NG2Scene*a,const NG2Scene*b,Candidate c[73]) {
    View v[2];int n=1,amount,d;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    c[0].sx=c[0].sy=0;c[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(&v[0],&v[1],c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
int test079_match(const NG2Scene*a,const NG2Scene*b,int tx,int ty) {
#if TEST079_PRESENT
    return revealed_gate_match(a,b,tx,ty);
#else
    (void)a;(void)b;(void)tx;(void)ty;return 0;
#endif
}
int test079_geometry(const NG2Scene*a,const NG2Scene*b,int sx,int sy) {
#if TEST079_PRESENT
    return unique_revealed_gate_translation(a,b,sx,sy);
#else
    (void)a;(void)b;(void)sx;(void)sy;return 0;
#endif
}
void test079_phase(const NG2Scene*a,const NG2Scene*b,double out[2],int values[5]) {
    Candidate c[73];View v[2];int bad,regions[3];
    ClosedGateAxisCache*cache=(ClosedGateAxisCache*)calloc(1,sizeof(*cache));
    test079_candidates(a,b,c);out[0]=c[0].score;out[1]=c[1].score-c[0].score;
    values[0]=c[0].sx;values[1]=c[0].sy;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    texture_match(&v[0],&v[1],c[0].sx,c[0].sy,0,&values[2],&bad,regions);
    values[3]=values[4]=0;
    if(!cache)return;
    closed_gate_axis_features(a,cache->before,cache->indices,&cache->count);
    closed_gate_axis_features(b,cache->after,NULL,NULL);
    closed_gate_axis_texture(cache,c[0].sx,c[0].sy,&values[3],&bad,NULL);
    values[4]=closed_gate_axis_strong(cache,c);free(cache);
}
void test079_proof(const NG2Scene*a,const NG2Scene*b,int direction,
                   double score,double gap,int sx,int sy,NG2Motion*out) {
#if TEST079_PRESENT
    Candidate c[73];int k;test079_candidates(a,b,c);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    /* Geometry and all73 image comparisons remain actual. This seam injects
     * only the global phase qualification at its explicit boundary. */
    c[0].score=score;c[1].score=score+gap;
    revealed_gate_axis_motion(a,b,direction,c,out);
#else
    (void)a;(void)b;(void)direction;(void)score;(void)gap;(void)sx;(void)sy;(void)out;
#endif
}
int test079_numeric(int support,int bad,int upper,int competing,int opposite) {
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));
    Candidate candidates[73];unsigned int state=79079;int i,n=1,amount,d,result;
    if(!c)return 0;
    candidates[0].sx=candidates[0].sy=0;candidates[0].score=0;
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];candidates[n].score=1;++n;
    }
    /* Numeric proof-predicate fixture, never a public Scene or phone claim. */
    for(i=0;i<support;++i) {
        int at,x,y;
        do {
            state=1664525u*state+1013904223u;x=42+2*(int)((state>>8)%64);
            state=1664525u*state+1013904223u;y=(i<upper?22:54)+(int)((state>>8)%29);
            at=y*W+x;
        } while(c->before[at].materials);
        c->indices[c->count++]=(uint16_t)at;
        c->before[at].materials=c->after[at].materials=1;
        c->before[at].axis=c->after[at].axis=1;
        c->before[at].sign=1;c->after[at].sign=i<bad?-1:1;
        if(i<competing) {
            c->after[at+1].materials=1;c->after[at+1].axis=1;
            c->after[at+1].sign=i<opposite?-1:1;
        }
    }
    result=closed_gate_axis_strong(c,candidates);free(c);return result;
}
'''


class NativeRevealedGate079Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test079-revealed-gate-')
        source = Path(os.environ.get('NECRO_TEST079_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        present = 'static void revealed_gate_axis_motion(' in source.read_text()
        shim = Path(cls.temp.name) / 'revealed-gate-proof.c'
        shim.write_text('#define TEST079_PRESENT ' + str(int(present)) + '\n#include "' +
                        str(source) + '"\n' + SHIM)
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm',
                '-o', str(library)], check=True, capture_output=True)
            lib = C.CDLL(str(library)); ptr = C.POINTER(Scene); ints = C.POINTER(C.c_int)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_choose.argtypes = [ptr, C.c_int, C.c_int, C.POINTER(C.c_uint16),
                C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                C.c_int, C.POINTER(Entrance)]
            lib.test079_match.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test079_geometry.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test079_phase.argtypes = [ptr, ptr, C.POINTER(C.c_double), ints]
            lib.test079_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test079_numeric.argtypes = [C.c_int] * 5
            cls.libraries[profile] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, images, direction=1):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, images, direction=1, score=.4, gap=.4,
              sx=None, sy=None, initial=0):
        dx, dy = DIRS[direction]
        out = Motion(initial, 7 if initial else 0, -3 if initial else 0)
        lib.test079_proof(C.byref(images[0]), C.byref(images[1]), direction, score, gap,
            -9 * dx if sx is None else sx, -9 * dy if sy is None else sy, C.byref(out))
        return out.kind, out.dx, out.dy

    def geometry(self, lib, images, sx=9, sy=0):
        return lib.test079_geometry(C.byref(images[0]), C.byref(images[1]), sx, sy)

    def test_public_four_direction_reveal_is_a_unit_then_nav_approaches_without_entry(self):
        following = {1: 3, 2: 4, 3: 2, 4: 1}
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    images = pair(direction)
                    phase = (C.c_double * 2)(); evidence = (C.c_int * 5)()
                    lib.test079_phase(C.byref(images[0]), C.byref(images[1]), phase, evidence)
                    self.assertEqual((-9 * dx, -9 * dy), tuple(evidence[:2]))
                    self.assertLessEqual(phase[0], .45); self.assertGreaterEqual(phase[1], .08)
                    self.assertLess(evidence[2], 300)
                    self.assertGreaterEqual(evidence[3], 300); self.assertEqual(1, evidence[4])
                    self.assertEqual((1, dx, dy), self.result(lib, images, direction),
                        'the procedural world moves once; a newly visible gate is not an opening')
                    visits = (C.c_uint16 * 1089)(); visits[16 * 33 + 16] = 1
                    visits[(16 + dy) * 33 + 16 + dx] = 1
                    entrance = Entrance(); decision = Decision()
                    self.assertEqual(1, lib.ng2_choose(C.byref(images[1]), dx, dy,
                        visits, len(visits), C.byref(entrance), C.byref(decision)))
                    self.assertEqual((following[direction], 7, 1),
                        (decision.direction, decision.reason, decision.obstacle))
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(images[0]),
                        C.byref(images[1]), direction, 0, 0, 1, C.byref(entrance)))
                    self.assertEqual(0, entrance.valid)

    def test_revealed_gate_requires_old_singleton_exact_pair_and_unknown_projections(self):
        cases = []
        for side, point, label in ((0, (-2, -2), 'old_gold'), (1, (-1, -2), 'retained_gold'),
                                   (1, (1, -2), 'new_gold'), (1, (0, -2), 'door')):
            images = pair(); images[side].tiles[cell(*point)] = 1
            cases.append((label, images))
        for side in (0, 1):
            images = pair(); images[side].tiles[cell(8, 3)] = 2
            cases.append((f'extra_gold:{side}', images))
        for point in ((-1, -2), (0, -2)):
            for kind in (1, 2, 3, 4, 5, 6):
                images = pair(); images[0].tiles[cell(*point)] = kind
                cases.append((f'known_projection:{point}:{kind}', images))
        images = pair(); images[1].tiles[cell(0, -2)] = 4
        cases.append(('dirt_instead_of_closed_door', images))
        images = pair(); images[1].tiles[cell(1, -2)] = 1
        images[1].tiles[cell(1, -3)] = 2
        cases.append(('two_gold_but_not_the_door_bracket', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.geometry(lib, images))
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            images = pair(); images[1].tiles[cell(8, 3)] = 5
            self.assertEqual(1, self.geometry(lib, images),
                'an ordinary unbracketed door is not a second gold gate')

    def test_only_old_noncollinear_stone_anchors_count_and_other_losses_are_not_evidence(self):
        cases = []
        images = pair()
        for x, y in ((-1, -1), (1, -1), (-1, 1)):
            images[1].tiles[cell(x, y)] = 4
        cases.append(('old_stones_all_lost', images))
        images = pair()
        for i, kind in enumerate(images[0].tiles):
            if kind == 3: images[0].tiles[i] = 1
        cases.append(('new_stones_only', images))
        images = pair(); images[1].tiles[cell(1, -1)] = 4
        cases.append(('remaining_two_collinear_with_gold', images))
        images = pair()
        images[1].tiles[cell(1, -1)] = images[1].tiles[cell(-1, 1)] = 4
        cases.append(('one_old_anchor', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.geometry(lib, images))
            images = pair()
            self.assertEqual(1, self.geometry(lib, images))
            images[1].tiles[cell(-1, -1)] = 4
            self.assertEqual(1, self.geometry(lib, images),
                'another complete noncollinear old pair survives; changed points are not anchors')

    def test_all_nine_translations_include_different_anchor_pair_ambiguity(self):
        images = pair()
        for scene in images: scene.tiles[:] = [1] * 230
        images[0].tiles[cell(0, -2)] = 2
        for point in ((-1, -2), (1, -2), (-2, -2), (2, -2)):
            images[0].tiles[cell(*point)] = 0
        for point in ((-4, -1), (-2, 1), (2, 1), (4, 3)):
            images[0].tiles[cell(*point)] = 3
        for point in ((-5, -1), (-3, 1), (3, 1), (5, 3)):
            images[1].tiles[cell(*point)] = 3
        images[1].tiles[cell(-1, -2)] = images[1].tiles[cell(1, -2)] = 2
        images[1].tiles[cell(0, -2)] = 5
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                self.assertEqual(1, lib.test079_match(C.byref(images[0]), C.byref(images[1]), -1, 0))
                self.assertEqual(1, lib.test079_match(C.byref(images[0]), C.byref(images[1]), 1, 0))
                self.assertEqual(0, self.geometry(lib, images, -9, 0))
                self.assertEqual(0, self.geometry(lib, images, 9, 0))
                self.assertEqual((0, 0, 0), self.proof(lib, images))
                ordinary = pair()
                shifts = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
                          (-2, 0), (2, 0), (0, -2), (0, 2)]
                fits = [shift for shift in shifts if lib.test079_match(
                    C.byref(ordinary[0]), C.byref(ordinary[1]), *shift)]
                self.assertEqual([(1, 0)], fits)

    def test_scope_requires_unknown_candidate_unprotected_item_free_observed_endpoints(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1)), ('goods', (1, 2)), ('gold_state', (0, 1, 3))):
                for value in values:
                    images = pair(); setattr(images[side], field, value)
                    cases.append((f'{side}:{field}:{value}', images))
            for point in ((0, 0), (8, 3)):
                images = pair(); images[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protect:{point}', images))
            images = pair(); images[side].tiles[cell(8, 3)] = 6
            cases.append((f'{side}:item', images))
            for point in ((0, 0), (-1, 0)) if side == 0 else ((0, 0),):
                for kind in (0, 2, 3, 4, 5, 6):
                    images = pair(); images[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            for kind in (0, 3, 4, 5):
                images = pair(); images[1].tiles[cell(-1, 0)] = kind
                self.assertEqual((1, -1, 0), self.proof(lib, images),
                    'future next terrain is judged by the following Nav call')

    def test_raw_normal_side_unit_gap_and_known_output_boundaries(self):
        # Around .4, the literal second score already lies above .08 when
        # subtracted. Its immediately lower double is below the boundary.
        high = (.4 + .08) - .4
        low = math.nextafter(.4 + .08, -math.inf) - .4
        self.assertLess(low, .08); self.assertGreaterEqual(high, .08)
        for profile, lib in self.libraries.items():
            for score, gap, expected in ((0., .4, 1), (.45, .4, 1), (.450001, .4, 0),
                (.4, high, 1), (.4, low, 0), (float('nan'), .4, 0),
                (float('inf'), .4, 0), (.4, float('nan'), 0)):
                with self.subTest(profile=profile, score=score, gap=gap):
                    self.assertEqual(expected, self.proof(lib, pair(), score=score, gap=gap)[0])
            for sx, sy in ((0, 0), (-9, 0), (18, 0), (8, 0), (0, 9)):
                self.assertEqual((0, 0, 0), self.proof(lib, pair(), sx=sx, sy=sy))
            for initial in range(1, 8):
                self.assertEqual((initial, 7, -3), self.proof(lib, pair(), initial=initial))

    def test_stationary_reverse_two_cells_and_partial_pixels_never_become_a_unit(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(1, self.result(lib, pair(direction, amount), direction)[0])
                for pixels in (8, 8.5):
                    images = pair(direction, pixels=8)
                    if pixels == 8.5:
                        nine = pair(direction)[1].signature
                        images[1].signature[:] = bytes((a + b) // 2 for a, b in
                            zip(images[1].signature, nine))
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertNotEqual(1, self.result(lib, images, direction)[0])
                for wrong in DIRS:
                    if wrong != direction:
                        self.assertNotEqual(1, self.result(lib, pair(direction), wrong)[0])
                dense = procedural_pair(direction, overlay=False)
                self.assertEqual((1, *DIRS[direction]), self.result(lib, dense, direction))

    def test_shared_fixed_axis_strength_bands_and_all73_competitor_rules_remain_required(self):
        for profile, lib in self.libraries.items():
            for label in ('flat', 'upper_only', 'lower_only', 'opposite'):
                images = pair(band=0 if label == 'upper_only' else 1 if label == 'lower_only' else None)
                if label == 'flat':
                    for scene in images: scene.signature[:] = bytes([40]) * (W * H)
                elif label == 'opposite':
                    images[1].signature[:] = bytes(255 - value for value in images[1].signature)
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            for support, bad, upper, competing, opposite, expected in (
                (300, 0, 150, 0, 0, 1), (299, 0, 150, 0, 0, 0),
                (300, 15, 150, 0, 0, 1), (300, 16, 150, 0, 0, 0),
                (300, 0, 99, 0, 0, 0), (300, 0, 100, 0, 0, 1),
                (300, 0, 201, 0, 0, 0), (300, 0, 200, 0, 0, 1),
                (300, 0, 150, 299, 0, 1), (300, 0, 150, 300, 45, 1),
                (300, 0, 150, 300, 44, 0), (300, 0, 150, 300, 0, 0)):
                with self.subTest(profile=profile, numeric=(support, bad, upper, competing, opposite)):
                    self.assertEqual(expected,
                        lib.test079_numeric(support, bad, upper, competing, opposite))


if __name__ == '__main__':
    unittest.main()
