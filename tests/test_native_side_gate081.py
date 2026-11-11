"""TEST081: one past unit aligns a newly visible side-facing closed gate.

Maps and independent grayscale fields below are procedural. They test native
motion proof boundaries, not phone acceptance, an ACK, opening, or entry.
"""
import ctypes as C
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


def rotate(direction, x, y):
    return {3: (x, y), 4: (-x, -y), 1: (y, -x), 2: (-y, x)}[direction]


def pair(direction=3, side=-1, projection=4, amount=1, pixels=None, noise=True):
    dx, dy = DIRS[direction]
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                           gold_state=2) for _ in range(2)]
    # A six-column known strip supplies both independent bands. Unobserved
    # terrain elsewhere may flicker independently; it supplies no known vote.
    for y in range(-5, 5):
        for x in range(-8, -2):
            before.tiles[cell(x, y)] = 1
    old = ((0, 0, 1), (-2 * side, -2, 2), (-2 * side, -1, projection),
           (-2 * side, 0, 0), (-1, 1, 3), (0, 1, 3), (3, 2, 3), (3, 3, 3))
    for x, y, kind in old:
        xx, yy = rotate(direction, x, y)
        before.tiles[cell(xx, yy)] = kind
    before.tiles[cell(dx, dy)] = 1
    for y in range(-5, 5):
        for x in range(-11, 12):
            xx, yy = x - dx * amount, y - dy * amount
            if -11 <= xx <= 11 and -5 <= yy <= 4:
                after.tiles[cell(xx, yy)] = before.tiles[cell(x, y)]
    # UP canonical: new door(+/-2,0) is orthogonal to the movement axis;
    # old singleton(+/-2,-2) becomes its first GOLD leaf(+/-2,-1).
    for x, y, kind in ((-2 * side, 0, 5), (-2 * side, 1, 2)):
        xx, yy = rotate(direction, x, y)
        after.tiles[cell(xx, yy)] = kind
    for x, y in ((3, 2), (3, 3)):
        xx, yy = rotate(direction, x, y)
        xx -= dx * amount; yy -= dy * amount
        if -11 <= xx <= 11 and -5 <= yy <= 4:
            after.tiles[cell(xx, yy)] = 4
    rng = random.Random(81081)
    world = bytearray(rng.randrange(20, 221) for _ in range(W * H))
    flicker = random.Random(181081)
    moved = bytearray(W * H)
    shift = 9 * amount if pixels is None else pixels
    for y in range(H):
        for x in range(W):
            xx, yy = x - dx * shift, y - dy * shift
            if not (0 <= xx < W and 0 <= yy < H):
                continue
            gx, gy = (4 * x - 34) // 36 - 11, (4 * y - 9) // 36 - 5
            known = -11 <= gx <= 11 and -5 <= gy <= 4 and before.tiles[cell(gx, gy)]
            moved[yy * W + xx] = world[y * W + x] if known or not noise else flicker.randrange(20, 221)
    before.signature[:] = world
    after.signature[:] = moved
    return [before, after]


SHIM = r'''
static void test081_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]) {
    int n=1,amount,d;view(a->signature,&v[0]);view(b->signature,&v[1]);
    c[0].sx=c[0].sy=0;c[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(&v[0],&v[1],c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test081_stats(const NG2Scene*a,const NG2Scene*b,int direction,double out[4],int values[12]) {
    View v[2];Candidate c[73],p[73];int amount,d,n=1;
    ClosedGateAxisCache*cache=(ClosedGateAxisCache*)calloc(1,sizeof(*cache));
    test081_candidates(a,b,v,c);
    p[0].sx=p[0].sy=0;p[0].score=sparse_gate_intensity(a,b,&v[0],&v[1],0,0,NULL,NULL);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        p[n].sx=amount*ddx[d];p[n].sy=amount*ddy[d];
        p[n].score=sparse_gate_intensity(a,b,&v[0],&v[1],p[n].sx,p[n].sy,NULL,NULL);++n;
    }
    qsort(p,73,sizeof(*p),ranked);out[0]=c[0].score;out[1]=c[1].score-c[0].score;
    out[2]=p[0].score;out[3]=p[1].score-p[0].score;
    values[0]=c[0].sx;values[1]=c[0].sy;values[2]=p[0].sx;values[3]=p[0].sy;
    sparse_gate_intensity(a,b,&v[0],&v[1],p[0].sx,p[0].sy,values+4,values+5);
    if(!cache)return;
    closed_gate_axis_features(a,cache->before,cache->indices,&cache->count);
    closed_gate_axis_features(b,cache->after,NULL,NULL);
    closed_gate_axis_texture(cache,-9*ddx[direction],-9*ddy[direction],values+7,values+8,values+9);
    values[11]=closed_gate_axis_strong(cache,c);free(cache);
}

int test081_match(const NG2Scene*a,const NG2Scene*b,int tx,int ty,int direction) {
#if TEST081_PRESENT
    return side_gate_match(a,b,tx,ty,direction);
#else
    (void)a;(void)b;(void)tx;(void)ty;(void)direction;return 0;
#endif
}
int test081_geometry(const NG2Scene*a,const NG2Scene*b,int direction,int sx,int sy) {
#if TEST081_PRESENT
    return unique_side_gate_translation(a,b,direction,sx,sy);
#else
    (void)a;(void)b;(void)direction;(void)sx;(void)sy;return 0;
#endif
}
void test081_proof(const NG2Scene*a,const NG2Scene*b,int direction,double score,
                   double gap,int sx,int sy,int other,NG2Motion*out) {
    View v[2];Candidate c[73];int k;test081_candidates(a,b,v,c);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    /* Only the old global phase boundary is injected. Geometry, all73
     * known-material phase scores and actual fixed-axis features still run. */
    c[0].score=score;c[1].score=score+gap;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    if(other==3)c[72].score=INFINITY;
#if TEST081_PRESENT
    side_gate_motion(a,b,direction,v,c,out);
#else
    (void)direction;(void)out;
#endif
}
int test081_pixel(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
    return sparse_gate_pixel(a,b,x,y,sx,sy);
}
int test081_phase_numeric(double first,double second,int support,int upper,int direction,int sx,int sy,int other) {
    Candidate c[73];int i,regions[2]={upper,support-upper};
    for(i=0;i<73;++i){c[i].score=INFINITY;c[i].sx=c[i].sy=0;}
    c[0].score=first;c[0].sx=sx;c[0].sy=sy;c[1].score=second;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    return sparse_gate_phase_valid(c,direction,support,regions);
}
int test081_numeric(int support,int bad,int upper,int competing,int opposite) {
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));
    Candidate candidates[73];unsigned int state=81081;int i,n=1,amount,d,result;
    if(!c)return 0;
    candidates[0].sx=candidates[0].sy=0;candidates[0].score=0;
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];candidates[n].score=1;++n;
    }
    /* Independent numeric predicate fixture; it never enters public Scenes. */
    for(i=0;i<support;++i) {
        int at,x,y;
        do {
            state=1664525u*state+1013904223u;x=42+2*(int)((state>>8)%64);
            state=1664525u*state+1013904223u;y=(i<upper?22:54)+(int)((state>>8)%29);
            at=y*W+x;
        }while(c->before[at].materials);
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
void test081_feature(const NG2Scene*s,int x,int y,int out[3]) {
    ClosedGateAxisFeature*f=(ClosedGateAxisFeature*)calloc(N,sizeof(*f));
    out[0]=out[1]=out[2]=0;if(!f)return;
    closed_gate_axis_features(s,f,NULL,NULL);
    out[0]=f[y*W+x].materials;out[1]=f[y*W+x].axis;out[2]=f[y*W+x].sign;free(f);
}
'''


class NativeSideGate081Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test081-side-gate-')
        source = Path(os.environ.get('NECRO_TEST081_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        shim = Path(cls.temp.name) / 'side-gate-proof.c'
        present = 'static void side_gate_motion(' in source.read_text()
        shim.write_text('#define TEST081_PRESENT ' + str(int(present)) + '\n#include "' + str(source) + '"\n' + SHIM)
        cls.libraries = {}
        cls.compile_commands = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm', '-o', str(library)]
            subprocess.run(command, check=True, capture_output=True)
            cls.compile_commands[profile] = command
            lib = C.CDLL(str(library)); ptr = C.POINTER(Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_choose.argtypes = [ptr, C.c_int, C.c_int, C.POINTER(C.c_uint16),
                C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                C.c_int, C.POINTER(Entrance)]
            lib.test081_stats.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_double), C.POINTER(C.c_int)]
            ints = C.POINTER(C.c_int)
            lib.test081_match.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int]
            lib.test081_geometry.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int]
            lib.test081_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test081_pixel.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int]
            lib.test081_phase_numeric.argtypes = [C.c_double, C.c_double, *([C.c_int] * 6)]
            lib.test081_numeric.argtypes = [C.c_int] * 5
            lib.test081_feature.argtypes = [ptr, C.c_int, C.c_int, ints]
            cls.libraries[profile] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, images, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def stats(self, lib, images, direction=3):
        values = (C.c_double * 4)(); counts = (C.c_int * 12)()
        lib.test081_stats(C.byref(images[0]), C.byref(images[1]), direction, values, counts)
        return tuple(values), tuple(counts)

    def proof(self, lib, images, direction=3, score=.6, gap=.4,
              sx=None, sy=None, other=0, initial=0):
        dx, dy = DIRS[direction]
        out = Motion(initial, 7 if initial else 0, -3 if initial else 0)
        lib.test081_proof(C.byref(images[0]), C.byref(images[1]), direction, score, gap,
            -9 * dx if sx is None else sx, -9 * dy if sy is None else sy, other, C.byref(out))
        return out.kind, out.dx, out.dy

    def geometry(self, lib, images, direction=3, sx=None, sy=None):
        dx, dy = DIRS[direction]
        return lib.test081_geometry(C.byref(images[0]), C.byref(images[1]), direction,
            -9 * dx if sx is None else sx, -9 * dy if sy is None else sy)

    def matches(self, lib, images, direction=3):
        shifts = [(0, 0)] + [(amount * dx, amount * dy)
            for amount in (1, 2) for dx, dy in DIRS.values()]
        return [shift for shift in shifts if lib.test081_match(
            C.byref(images[0]), C.byref(images[1]), *shift, direction)]

    def feature(self, lib, scene, x=62, y=30):
        out = (C.c_int * 3)(); lib.test081_feature(C.byref(scene), x, y, out)
        return tuple(out)

    def point_scene(self, horizontal=12, vertical=40):
        scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=2)
        scene.tiles[:] = [1] * 230; scene.signature[:] = bytes([48]) * (W * H)
        scene.signature[30 * W + 61] = 30
        scene.signature[30 * W + 63] = 30 + horizontal
        scene.signature[29 * W + 62] = 20
        scene.signature[31 * W + 62] = 20 + vertical
        return scene

    def test_public_four_direction_side_gate_unit_keeps_next_navigation_unentered(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for side in (-1, 1):
                    with self.subTest(profile=profile, direction=direction, side=side):
                        images = pair(direction, side)
                        values, counts = self.stats(lib, images, direction)
                        self.assertGreater(values[0], .45)
                        self.assertGreaterEqual(values[1], .08)
                        self.assertLessEqual(values[2], .45)
                        self.assertGreaterEqual(values[3], .08)
                        self.assertEqual((-9 * dx, -9 * dy) * 2, counts[:4])
                        self.assertGreaterEqual(counts[4], 300)
                        self.assertGreaterEqual(min(counts[5:7]), 100)
                        self.assertEqual(1, counts[11])
                        self.assertEqual((1, dx, dy), self.result(lib, images, direction))
                        entrance = Entrance()
                        self.assertEqual(0, lib.ng2_entered_gate(C.byref(images[0]),
                            C.byref(images[1]), direction, 0, 0, 1, C.byref(entrance)))
                        self.assertEqual(0, entrance.valid)
                        visits = (C.c_uint16 * 1089)(); visits[16 * 33 + 16] = 1
                        visits[(16 + dy) * 33 + 16 + dx] = 1
                        decision = Decision()
                        self.assertEqual(1, lib.ng2_choose(C.byref(images[1]), dx, dy,
                            visits, len(visits), C.byref(entrance), C.byref(decision)))
                        # The side gate has no observed floor route in this
                        # sparse map. The unchanged planner explores the sole
                        # reachable unvisited floor, the previous origin.
                        following = {1: 2, 2: 1, 3: 4, 4: 3}[direction]
                        self.assertEqual((following, 8, -dx, -dy, 1),
                            tuple(getattr(decision, name) for name, _ in decision._fields_))
                        self.assertEqual(1, images[1].tiles[cell(*DIRS[decision.direction])])

    def test_new_gate_requires_unknown_or_dirt_projections_and_orthogonal_two_cell_geometry(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for side in (-1, 1):
                    dx, dy = DIRS[direction]
                    for projection in (0, 4):
                        images = pair(direction, side, projection)
                        with self.subTest(profile=profile, direction=direction, side=side, projection=projection):
                            self.assertEqual([(-dx, -dy)], self.matches(lib, images, direction))
                            self.assertEqual(1, self.geometry(lib, images, direction))
                            self.assertEqual((1, dx, dy), self.proof(lib, images, direction))
                    for canonical, kinds in (((-2 * side, -1), (1, 2, 3, 5, 6)),
                                              ((-2 * side, 0), (1, 2, 3, 4, 5, 6))):
                        for kind in kinds:
                            images = pair(direction, side)
                            images[0].tiles[cell(*rotate(direction, *canonical))] = kind
                            with self.subTest(profile=profile, direction=direction, side=side, old_projection=canonical, kind=kind):
                                self.assertEqual(0, self.geometry(lib, images, direction))
                    for scene in (0, 1):
                        images = pair(direction, side); images[scene].tiles[cell(8, 3)] = 2
                        self.assertEqual(0, self.geometry(lib, images, direction))
                    images = pair(direction, side)
                    images[1].tiles[cell(*rotate(direction, -2 * side, 0))] = 1
                    self.assertEqual(0, self.geometry(lib, images, direction))
            for cx, cy, normal in ((1, 0, 2), (3, 0, 2), (0, -2, 4), (1, 1, 2)):
                images = pair()
                for scene in images:
                    for i, kind in enumerate(scene.tiles):
                        if kind in (2, 5): scene.tiles[i] = 0
                # Construct a complete but out-of-scope bracket. Canonical UP
                # translates oldnear by +y; current gate must be x=+/-2,y=0.
                near = (cx, cy - 1) if normal == 2 else (cx - 1, cy)
                far = (cx, cy + 1) if normal == 2 else (cx + 1, cy)
                images[0].tiles[cell(near[0], near[1] - 1)] = 2
                images[0].tiles[cell(cx, cy - 1)] = 4
                images[0].tiles[cell(far[0], far[1] - 1)] = 0
                images[1].tiles[cell(cx, cy)] = 5
                images[1].tiles[cell(*near)] = images[1].tiles[cell(*far)] = 2
                with self.subTest(profile=profile, gate=(cx, cy, normal)):
                    self.assertEqual(0, self.geometry(lib, images))

    def test_old_noncollinear_stones_and_all_nine_translations_reject_different_pair_ambiguity(self):
        for profile, lib in self.libraries.items():
            for label in ('no_old_stones', 'one_old_stone', 'new_stones_only', 'collinear'):
                images = pair()
                if label in ('no_old_stones', 'new_stones_only'):
                    for i, kind in enumerate(images[0].tiles):
                        if kind == 3: images[0].tiles[i] = 1
                elif label == 'one_old_stone':
                    images[1].tiles[cell(-1, 2)] = 4
                else:
                    for scene in images:
                        for i, kind in enumerate(scene.tiles):
                            if kind == 3: scene.tiles[i] = 1
                    for point in ((2, 2), (2, 3)):
                        images[0].tiles[cell(*point)] = 3
                        images[1].tiles[cell(point[0], point[1] + 1)] = 3
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, self.geometry(lib, images))
            ordinary = pair()
            self.assertEqual([(0, 1)], self.matches(lib, ordinary))
            self.assertEqual(4, sum(kind == 3 for kind in ordinary[0].tiles))
            self.assertEqual(2, sum(kind == 3 for kind in ordinary[1].tiles))
            # Old singleton at the new gate center can map to either leaf.
            # Disjoint old pairs support +y and -y independently.
            images = pair()
            for scene in images: scene.tiles[:] = [0] * 230
            images[0].tiles[cell(2, 0)] = 2
            images[0].tiles[cell(2, -1)] = 4
            images[0].tiles[cell(2, 1)] = 0
            images[1].tiles[cell(2, 0)] = 5
            images[1].tiles[cell(2, -1)] = images[1].tiles[cell(2, 1)] = 2
            for x, y in ((-4, -2), (-2, 0)):
                images[0].tiles[cell(x, y)] = 3; images[1].tiles[cell(x, y + 1)] = 3
            for x, y in ((4, 0), (6, 2)):
                images[0].tiles[cell(x, y)] = 3; images[1].tiles[cell(x, y - 1)] = 3
            with self.subTest(profile=profile, different_pair_ambiguity=True):
                self.assertEqual([(0, -1), (0, 1)], self.matches(lib, images))
                self.assertEqual(0, self.geometry(lib, images))
                self.assertEqual(0, self.geometry(lib, images, sy=-9))

    def test_scope_requires_floor_candidate_unknown_goods_no_items_protection_and_old_endpoints(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('goods', (1, 2)), ('gold_state', (0, 1, 3))):
                for value in values:
                    images = pair(); setattr(images[side], field, value)
                    cases.append((f'{side}:{field}:{value}', images))
            for point in ((0, 0), (8, 3)):
                images = pair(); images[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protect:{point}', images))
                images = pair(); images[side].tiles[cell(*point)] = 6
                cases.append((f'{side}:item:{point}', images))
            for point in ((0, 0), (0, -1)) if side == 0 else ((0, 0),):
                for kind in (0, 2, 3, 4, 5, 6):
                    images = pair(); images[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            for kind in (0, 3, 4, 5):
                images = pair(); images[1].tiles[cell(0, -1)] = kind
                self.assertEqual((1, 0, -1), self.proof(lib, images),
                    'the following planner decides the future next cell')

    def test_raw_high_finite_unit_gap_all73_and_known_primary_outputs_are_preserved(self):
        high = math.nextafter(.6 + .08, math.inf) - .6
        low = math.nextafter(.6 + .08, -math.inf) - .6
        self.assertLess(low, .08); self.assertGreaterEqual(high, .08)
        for profile, lib in self.libraries.items():
            for score, gap, expected in ((.450001, .4, 1), (.45, .4, 0), (0., .4, 0),
                (.6, high, 1), (.6, low, 0), (.6, .079999, 0), (float('nan'), .4, 0),
                (float('inf'), .4, 0), (-float('inf'), .4, 0), (.6, float('nan'), 0)):
                with self.subTest(profile=profile, score=score, gap=gap):
                    self.assertEqual(expected, self.proof(lib, pair(), score=score, gap=gap)[0])
            for sx, sy in ((0, 0), (9, 0), (0, -9), (0, 18), (0, 8)):
                self.assertEqual((0, 0, 0), self.proof(lib, pair(), sx=sx, sy=sy))
            for other, expected in ((1, 0), (2, 0), (3, 1)):
                self.assertEqual(expected, self.proof(lib, pair(), other=other)[0])
            for initial in range(1, 8):
                self.assertEqual((initial, 7, -3), self.proof(lib, pair(), initial=initial))
            for direction, displacement in DIRS.items():
                images = procedural_pair(direction, overlay=False)
                self.assertEqual((1, *displacement), self.result(lib, images, direction))

    def test_known_phase_requires_same_unit_all_dependencies_bands_finite_scores_and_exact_limits(self):
        for profile, lib in self.libraries.items():
            for label in ('reverse_pixels', 'zero_pixels', 'flat'):
                images = pair(pixels=-9 if label == 'reverse_pixels' else 0 if label == 'zero_pixels' else None)
                if label == 'flat':
                    for scene in images: scene.signature[:] = bytes([40]) * (W * H)
                with self.subTest(profile=profile, known_phase=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            for first, second, support, upper, sx, sy, other, expected in (
                (.45, .6, 300, 100, 0, 9, 0, 1), (.450001, .6, 300, 100, 0, 9, 0, 0),
                (.3, .38, 300, 100, 0, 9, 0, 1), (.3, math.nextafter(.38, 0.), 300, 100, 0, 9, 0, 0),
                (.3, .6, 299, 100, 0, 9, 0, 0), (.3, .6, 300, 99, 0, 9, 0, 0),
                (.3, .6, 300, 201, 0, 9, 0, 0), (.3, .6, 300, 200, 0, 9, 0, 1),
                (.3, .6, 300, 100, 0, -9, 0, 0), (.3, .6, 300, 100, 0, 0, 0, 0),
                (.3, .6, 300, 100, 0, 9, 1, 0), (.3, .6, 300, 100, 0, 9, 2, 0),
                (float('nan'), .6, 300, 100, 0, 9, 0, 0),
                (float('inf'), float('inf'), 300, 100, 0, 9, 0, 0)):
                with self.subTest(profile=profile, phase=(first, second, support, upper, sx, sy, other)):
                    self.assertEqual(expected, lib.test081_phase_numeric(first, second, support, upper, 3, sx, sy, other))
            # Test each dependency on both sides at a scalar pixel inside the
            # known strip, keeping the source and translated kernels separate.
            for side in (0, 1):
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        for kind in (0, 5, 6, 'protect', 3):
                            images = pair()
                            x, y, sx, sy = 62, 40, 0, 9
                            self.assertEqual(1, lib.test081_pixel(C.byref(images[0]), C.byref(images[1]), x, y, sx, sy))
                            xx, yy = x + ox, y + oy + (sy if side else 0)
                            at = cell((4 * xx - 34) // 36 - 11, (4 * yy - 9) // 36 - 5)
                            if kind == 'protect': images[side].protected_cells[at] = 1
                            else: images[side].tiles[at] = kind
                            with self.subTest(profile=profile, dependency=(side, ox, oy), kind=kind):
                                self.assertEqual(0, lib.test081_pixel(C.byref(images[0]), C.byref(images[1]), x, y, sx, sy))
            images = pair()
            for x, y, sx, sy in ((62, 64, 0, 0), (62, 65, 0, 0), (62, 55, 0, 9),
                (62, 56, 0, 9), (40, 40, 0, 9), (103, 44, 0, 9), (115, 62, 0, 9)):
                self.assertEqual(0, lib.test081_pixel(C.byref(images[0]), C.byref(images[1]), x, y, sx, sy))

    def test_fixed_axis_strong_52_bands_95_percent_and_all73_15pp_competitor_rules(self):
        for profile, lib in self.libraries.items():
            self.assertEqual((73, 1, 1), self.feature(lib, self.point_scene()))
            self.assertEqual((73, 2, 1), self.feature(lib, self.point_scene(horizontal=11)))
            self.assertEqual((73, 1, -1), self.feature(lib, self.point_scene(horizontal=-12)))
            self.assertEqual((0, 0, 0), self.feature(lib, self.point_scene(horizontal=11, vertical=11)))
            for support, bad, upper, competing, opposite, expected in (
                (300, 0, 150, 0, 0, 1), (299, 0, 150, 0, 0, 0),
                (300, 15, 150, 0, 0, 1), (300, 16, 150, 0, 0, 0),
                (300, 0, 99, 0, 0, 0), (300, 0, 100, 0, 0, 1),
                (300, 0, 201, 0, 0, 0), (300, 0, 200, 0, 0, 1),
                (300, 0, 150, 299, 0, 1), (300, 0, 150, 300, 45, 1),
                (300, 0, 150, 300, 44, 0), (300, 0, 150, 300, 0, 0)):
                with self.subTest(profile=profile, numeric=(support, bad, upper, competing, opposite)):
                    self.assertEqual(expected, lib.test081_numeric(support, bad, upper, competing, opposite))
            for label in ('upper_only', 'lower_only', 'inverted'):
                images = pair()
                for side, scene in enumerate(images):
                    signature = bytearray(scene.signature)
                    for y in range(H):
                        for x in range(W):
                            if label == 'inverted':
                                if side: signature[y * W + x] = 255 - signature[y * W + x]
                            elif (y - (9 if side else 0) < 52) == (label == 'lower_only'):
                                signature[y * W + x] = 40
                    scene.signature[:] = signature
                with self.subTest(profile=profile, axis=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))

    def test_stationary_reverse_two_cells_eight_and_half_pixels_never_receive_unit_credit(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(1, self.result(lib, pair(direction, amount=amount), direction)[0])
                for pixels in (8, 8.5):
                    images = pair(direction, pixels=8)
                    if pixels == 8.5:
                        nine = pair(direction)[1].signature
                        images[1].signature[:] = bytes((a + b) // 2 for a, b in zip(images[1].signature, nine))
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertNotEqual(1, self.result(lib, images, direction)[0])
                for wrong in DIRS:
                    if wrong != direction:
                        self.assertNotEqual(1, self.result(lib, pair(direction), wrong)[0])


if __name__ == '__main__':
    unittest.main()
