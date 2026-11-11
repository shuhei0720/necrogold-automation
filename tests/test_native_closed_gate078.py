"""TEST078: prove arrival one cell before a still-closed gold door.

All signatures, maps and numeric feature tables are procedural unit fixtures.
They test a past unit displacement and never stand in for phone acceptance,
an opening, an entrance, an ACK, or a future device response.
"""
import ctypes as C
import math
import os
from pathlib import Path
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


def pair(direction=3, amount=1, pixels=None, overlay=True):
    before, after = procedural_pair(direction, amount=amount, pixels=pixels, overlay=overlay)
    dx, dy = DIRS[direction]
    for scene in (before, after):
        scene.tiles[:] = [1] * 230
    for x, y, kind in ((2 * dx, 2 * dy, 5),
                       (2 * dx + dy, 2 * dy - dx, 2),
                       (2 * dx - dy, 2 * dy + dx, 2)):
        before.tiles[cell(x, y)] = kind
        after.tiles[cell(x - dx * amount, y - dy * amount)] = kind
    return before, after


SHIM = r'''
int test078_present(void) { return TEST078_PRESENT; }
#if TEST078_PRESENT
static int test078_scalar_mask(int x,int y) {
    return x>=40&&x<179&&y>=20&&y<85
        &&!(x>=103&&x<122&&y>=43&&y<61)
        &&!(x>=115&&x<154&&y>=38&&y<80)
        &&!(x>=101&&x<123&&y>=80);
}
/* A direct scalar specification recomputes the axis per frame and pixel.
 * It does not call the production feature builder or cached comparison. */
static int test078_scalar_feature(const NG2Scene*s,int x,int y,int out[3]) {
    int axis;out[0]=out[1]=out[2]=0;
    for(axis=1;axis<=2;++axis) {
        int i,materials=0,ox=axis==1,oy=axis==2,delta;
        for(i=0;i<3;++i) {
            int step=i==0?0:(i==1?-1:1),xx=x+step*ox,yy=y+step*oy;
            int gx=(4*xx-34)/36-11,gy=(4*yy-9)/36-5,kind;
            if(!test078_scalar_mask(xx,yy)||gx < -11||gx>11||gy < -5||gy>4) break;
            kind=s->tiles[(gy+5)*23+gx+11];
            if(!kind||kind==5||kind==6||s->protected_cells[(gy+5)*23+gx+11])break;
            materials|=kind<<(3*i);
        }
        if(i!=3)continue;
        delta=(int)s->signature[(y+oy)*W+x+ox]-s->signature[(y-oy)*W+x-ox];
        if(abs(delta)<12)continue;
        out[0]=materials;out[1]=axis;out[2]=delta>0?1:-1;return 1;
    }
    return 0;
}
static ClosedGateAxisCache *test078_cache(const NG2Scene*a,const NG2Scene*b) {
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));
    if(!c)return NULL;
    closed_gate_axis_features(a,c->before,c->indices,&c->count);
    closed_gate_axis_features(b,c->after,NULL,NULL);return c;
}
#endif
int test078_feature(const NG2Scene*s,int x,int y,int out[3]) {
    out[0]=out[1]=out[2]=0;
#if TEST078_PRESENT
    ClosedGateAxisFeature*f=(ClosedGateAxisFeature*)calloc(N,sizeof(*f));
    if(!f)return 0;
    closed_gate_axis_features(s,f,NULL,NULL);
    out[0]=f[y*W+x].materials;out[1]=f[y*W+x].axis;out[2]=f[y*W+x].sign;
    free(f);return out[0]!=0;
#else
    (void)s;(void)x;(void)y;return 0;
#endif
}
void test078_counts(const NG2Scene*a,const NG2Scene*b,int sx,int sy,int out[4]) {
    out[0]=out[1]=out[2]=out[3]=0;
#if TEST078_PRESENT
    ClosedGateAxisCache*c=test078_cache(a,b);
    if(!c)return;
    closed_gate_axis_texture(c,sx,sy,&out[0],&out[1],&out[2]);free(c);
#else
    (void)a;(void)b;(void)sx;(void)sy;
#endif
}
void test078_point(const NG2Scene*a,const NG2Scene*b,int x,int y,int out[4]) {
    out[0]=out[1]=out[2]=out[3]=0;
#if TEST078_PRESENT
    ClosedGateAxisCache*c=test078_cache(a,b);int at=y*W+x;
    if(!c)return;
    c->count=c->before[at].materials?1:0;c->indices[0]=(uint16_t)at;
    closed_gate_axis_texture(c,0,0,&out[0],&out[1],&out[2]);free(c);
#else
    (void)a;(void)b;(void)x;(void)y;
#endif
}
void test078_proof(const NG2Scene*a,const NG2Scene*b,int direction,
                   double score,double gap,int sx,int sy,NG2Motion*out) {
#if TEST078_PRESENT
    Candidate c[73];int n=1,amount,d,k;View v[2];
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    c[0].sx=c[0].sy=0;c[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(&v[0],&v[1],c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    /* Only the global phase is injected. Geometry and all73 feature
     * comparisons still run through the actual production helper. */
    c[0].score=score;c[1].score=score+gap;
    closed_gate_axis_motion(a,b,direction,c,out);
#else
    (void)a;(void)b;(void)direction;(void)score;(void)gap;(void)sx;(void)sy;(void)out;
#endif
}
int test078_parity(const NG2Scene*a,const NG2Scene*b) {
#if TEST078_PRESENT
    ClosedGateAxisCache*c=test078_cache(a,b);int amount,d,equal=1;
    if(!c)return 0;
    for(amount=0;amount<=18;++amount)for(d=1;d<=(amount?4:1);++d) {
        int sx=amount*ddx[d],sy=amount*ddy[d],x,y,support=0,bad=0,regions[2]={0};
        int cached[4];
        for(y=20;y<85;++y)for(x=40;x<179;++x) {
            int first[3],second[3];
            if(y==51||y==52||y+sy==51||y+sy==52)continue;
            if(!test078_scalar_feature(a,x,y,first)||
               !test078_scalar_feature(b,x+sx,y+sy,second))continue;
            if(first[0]!=second[0]||first[1]!=second[1])continue;
            ++support;bad+=first[2]!=second[2];++regions[y<52?0:1];
        }
        closed_gate_axis_texture(c,sx,sy,&cached[0],&cached[1],&cached[2]);
        if(support!=cached[0]||bad!=cached[1]||regions[0]!=cached[2]||regions[1]!=cached[3])equal=0;
    }
    free(c);return equal;
#else
    (void)a;(void)b;return 0;
#endif
}
int test078_single(int y,int sy,int out[4]) {
    out[0]=out[1]=out[2]=out[3]=0;
#if TEST078_PRESENT
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));int at=y*W+60;
    if(!c)return 0;
    c->count=1;c->indices[0]=(uint16_t)at;
    c->before[at].materials=c->after[at+sy*W].materials=1;
    c->before[at].axis=c->after[at+sy*W].axis=1;
    c->before[at].sign=c->after[at+sy*W].sign=1;
    closed_gate_axis_texture(c,0,sy,&out[0],&out[1],&out[2]);free(c);return 1;
#else
    (void)y;(void)sy;return 0;
#endif
}
int test078_numeric(int support,int bad,int upper,int competing,int opposite) {
#if TEST078_PRESENT
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));
    Candidate candidates[73];unsigned int state=78078;int i,n=1,amount,d,result;
    if(!c)return 0;
    candidates[0].sx=candidates[0].sy=0;candidates[0].score=0;
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];candidates[n].score=1;++n;
    }
    /* Sparse even-x features make the +1 competitor independently writable.
     * Numeric fields never enter a public Scene or device claim. */
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
#else
    (void)support;(void)bad;(void)upper;(void)competing;(void)opposite;return 0;
#endif
}
'''


class NativeClosedGate078Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test078-closed-gate-')
        source = Path(os.environ.get('NECRO_TEST078_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        present = 'static void closed_gate_axis_motion(' in source.read_text()
        shim = Path(cls.temp.name) / 'closed-gate-proof.c'
        shim.write_text('#define TEST078_PRESENT ' + str(int(present)) + '\n#include "' +
                        str(source) + '"\n' + SHIM)
        cls.libraries = {}
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm',
                '-o', str(library)], check=True, capture_output=True)
            lib = C.CDLL(str(library)); ptr = C.POINTER(Scene); ints = C.POINTER(C.c_int)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_choose.argtypes = [ptr, C.c_int, C.c_int, C.POINTER(C.c_uint16),
                C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                C.c_int, C.POINTER(Entrance)]
            lib.test078_feature.argtypes = [ptr, C.c_int, C.c_int, ints]
            lib.test078_counts.argtypes = [ptr, ptr, C.c_int, C.c_int, ints]
            lib.test078_point.argtypes = [ptr, ptr, C.c_int, C.c_int, ints]
            lib.test078_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test078_parity.argtypes = [ptr, ptr]
            lib.test078_single.argtypes = [C.c_int, C.c_int, ints]
            lib.test078_numeric.argtypes = [C.c_int] * 5
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, images, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, images, direction=3, score=.57, gap=.4, sx=None, sy=None, initial=0):
        dx, dy = DIRS[direction]
        out = Motion(initial, 7 if initial else 0, -3 if initial else 0)
        lib.test078_proof(C.byref(images[0]), C.byref(images[1]), direction, score, gap,
            -9 * dx if sx is None else sx, -9 * dy if sy is None else sy, C.byref(out))
        return out.kind, out.dx, out.dy

    def feature(self, lib, scene, x=62, y=30):
        out = (C.c_int * 3)()
        lib.test078_feature(C.byref(scene), x, y, out)
        return tuple(out)

    def point_scene(self, x=62, y=30, horizontal=12, vertical=40):
        scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=2)
        scene.tiles[:] = [1] * 230; scene.signature[:] = bytes([48]) * (W * H)
        scene.signature[y * W + x - 1] = 30
        scene.signature[y * W + x + 1] = 30 + horizontal
        scene.signature[(y - 1) * W + x] = 20
        scene.signature[(y + 1) * W + x] = 20 + vertical
        return scene

    def test_public_four_direction_arrival_returns_next_door_without_entry(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    images = pair(direction)
                    self.assertEqual((1, dx, dy), self.result(lib, images, direction))
                    visits = (C.c_uint16 * 1089)(); visits[16 * 33 + 16] = 1
                    visits[(16 + dy) * 33 + 16 + dx] = 1
                    decision = Decision(); entrance = Entrance()
                    self.assertEqual(1, lib.ng2_choose(C.byref(images[1]), dx, dy,
                        visits, len(visits), C.byref(entrance), C.byref(decision)))
                    self.assertEqual((direction, 5, dx, dy, 5),
                        tuple(getattr(decision, name) for name, _ in decision._fields_))
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(images[0]),
                        C.byref(images[1]), direction, 0, 0, 1, C.byref(entrance)))
                    self.assertEqual(0, entrance.valid)

    def test_zero_reverse_two_cells_partial_and_known_primary_stay_distinct(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(1, self.result(lib, pair(direction, amount), direction)[0])
                for pixels in (8, 8.5):
                    images = pair(direction, pixels=8)
                    if pixels == 8.5:
                        # Half-pixel procedural interpolation, not restamped geometry.
                        nine = pair(direction, pixels=9)[1].signature
                        images[1].signature[:] = bytes((a + b) // 2 for a, b in
                            zip(images[1].signature, nine))
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertNotEqual(1, self.result(lib, images, direction)[0])
                for wrong in DIRS:
                    if wrong != direction:
                        self.assertNotEqual(1, self.result(lib, pair(direction), wrong)[0])
                for amount, expected in ((0, 2), (1, 1), (2, 6)):
                    with self.subTest(profile=profile, primary=expected, direction=direction):
                        self.assertEqual(expected,
                            self.result(lib, pair(direction, amount, overlay=False), direction)[0])

    def test_scope_requires_both_unknown_candidate_unprotected_item_free_floors(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1)), ('goods', (1, 2)), ('gold_state', (0, 1, 3))):
                for value in values:
                    images = pair(); setattr(images[side], field, value)
                    cases.append((f'{side}:{field}:{value}', images))
            for point in ((0, 0), (8, 3)):
                images = pair(); images[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protected:{point}', images))
            images = pair(); images[side].tiles[cell(8, 3)] = 6
            cases.append((f'{side}:remote_item', images))
            for point in ((0, 0), (0, -1)) if side == 0 else ((0, 0),):
                for kind in (0, 2, 3, 4, 5, 6):
                    images = pair(); images[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))

    def test_exact_closed_geometry_keeps_all_gold_and_rejects_other_gate_patterns(self):
        cases = []
        for side in (0, 1):
            for label in ('missing_gold', 'extra_gold', 'open', 'wrong_normal'):
                images = pair(); distance = 2 if side == 0 else 1
                if label == 'missing_gold': images[side].tiles[cell(-1, -distance)] = 1
                elif label == 'extra_gold': images[side].tiles[cell(8, 3)] = 2
                elif label == 'open': images[side].tiles[cell(0, -distance)] = 1
                else:
                    images[side].tiles[cell(-1, -distance)] = 1
                    images[side].tiles[cell(1, -distance)] = 1
                    images[side].tiles[cell(0, -distance - 1)] = 2
                    images[side].tiles[cell(0, -distance + 1)] = 2
                cases.append((f'{side}:{label}', images))
        images = pair(); images[1].tiles[cell(-1, -1)] = 1
        images[1].tiles[cell(-2, -1)] = 2
        cases.append(('shifted_gold', images))
        images = pair()
        for x, y, kind in ((0, -2, 5), (-1, -2, 2), (1, -2, 2)):
            images[1].tiles[cell(x, y)] = kind
        cases.append(('multiple_gate_correspondences', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            images = pair()
            images[0].tiles[cell(7, 2)] = images[1].tiles[cell(7, 3)] = 2
            self.assertEqual((1, 0, -1), self.proof(lib, images),
                'additional old GOLD is allowed when it retains the exact same unit translation')

    def test_raw_phase_boundaries_and_known_results_are_not_overwritten(self):
        # The helper subtracts two scores. Around .57, the two adjacent
        # representable second scores straddle .08; the literal sum .57+.08
        # itself subtracts to .07999999999999996 and must still be rejected.
        low = (.57 + .08) - .57
        high = math.nextafter(.57 + .08, math.inf) - .57
        self.assertLess(low, .08); self.assertGreaterEqual(high, .08)
        for profile, lib in self.libraries.items():
            for score, gap, expected in ((.450001, .4, 1), (.45, .4, 0),
                (.57, high, 1), (.57, low, 0), (.57, .079999, 0), (float('nan'), .4, 0),
                (float('inf'), .4, 0), (.57, float('nan'), 0)):
                with self.subTest(profile=profile, score=score, gap=gap):
                    self.assertEqual(expected, self.proof(lib, pair(), score=score, gap=gap)[0])
            for sx, sy in ((0, 0), (0, -9), (0, 18), (0, 8), (9, 0)):
                self.assertEqual((0, 0, 0), self.proof(lib, pair(), sx=sx, sy=sy))
            for initial in range(1, 8):
                self.assertEqual((initial, 7, -3), self.proof(lib, pair(), initial=initial))

    def test_axis_is_fixed_per_frame_with_all_actual_dependencies_and_ui_checked(self):
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                self.assertEqual((73, 1, 1), self.feature(lib, self.point_scene()),
                    'horizontal is fixed before comparison even when vertical contrast is stronger')
                self.assertEqual((73, 2, 1), self.feature(lib, self.point_scene(horizontal=11)))
                self.assertEqual((73, 1, -1), self.feature(lib, self.point_scene(horizontal=-12)))
                self.assertEqual((0, 0, 0), self.feature(lib, self.point_scene(horizontal=11, vertical=11)))
                fallback = self.point_scene()
                fallback.tiles[cell(-5, -2)] = 0  # Only the unused H-positive tile.
                self.assertEqual((73, 2, 1), self.feature(lib, fallback))
            for label in ('same', 'other_axis', 'opposite', 'different_material'):
                before = self.point_scene()
                after = self.point_scene(horizontal=11 if label == 'other_axis' else
                                         -12 if label == 'opposite' else 12)
                if label == 'different_material': after.tiles[cell(-5, -2)] = 3
                out = (C.c_int * 4)()
                lib.test078_point(C.byref(before), C.byref(after), 62, 30, out)
                with self.subTest(profile=profile, fixed_frame_match=label):
                    self.assertEqual((1, int(label == 'opposite'), 1, 0)
                        if label in ('same', 'opposite') else (0, 0, 0, 0), tuple(out))
            for axis in (1, 2):
                x, y = 62, 30
                for ox, oy in ((0, 0), (-1, 0), (1, 0)) if axis == 1 else ((0, 0), (0, -1), (0, 1)):
                    for kind in (0, 5, 6, 'protect'):
                        scene = self.point_scene(horizontal=12 if axis == 1 else 0,
                                                 vertical=0 if axis == 1 else 12)
                        gx, gy = (4 * (x + ox) - 34) // 36 - 11, (4 * (y + oy) - 9) // 36 - 5
                        if kind == 'protect': scene.protected_cells[cell(gx, gy)] = 1
                        else: scene.tiles[cell(gx, gy)] = kind
                        with self.subTest(profile=profile, axis=axis, dependency=(ox, oy), kind=kind):
                            self.assertEqual((0, 0, 0), self.feature(lib, scene))
            for x, y, horizontal, vertical in ((102, 44, 12, 0), (40, 30, 12, 0),
                                              (60, 20, 0, 12), (101, 80, 12, 12)):
                with self.subTest(profile=profile, ui_dependency=(x, y)):
                    self.assertEqual((0, 0, 0), self.feature(lib,
                        self.point_scene(x, y, horizontal, vertical), x, y))

    def test_cache_equals_direct_scalar_all73_and_camera_center_bands_are_independent(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                with self.subTest(profile=profile, direction=direction):
                    images = pair(direction)
                    self.assertEqual(1, lib.test078_parity(C.byref(images[0]), C.byref(images[1])))
            images = pair(); images[1].tiles[cell(-6, -2)] = 3
            images[1].protected_cells[cell(-4, -2)] = 1
            self.assertEqual(1, lib.test078_parity(C.byref(images[0]), C.byref(images[1])))
            for y, sy, expected in ((50, 0, (1, 0, 1, 0)), (51, 0, (0, 0, 0, 0)),
                (52, 0, (0, 0, 0, 0)), (53, 0, (1, 0, 0, 1)),
                (50, 1, (0, 0, 0, 0)), (53, -1, (0, 0, 0, 0)), (49, 1, (1, 0, 1, 0))):
                out = (C.c_int * 4)(); lib.test078_single(y, sy, out)
                with self.subTest(profile=profile, y=y, sy=sy):
                    self.assertEqual(expected, tuple(out))

    def test_support_strength_two_bands_and_sufficient_competitor_lead_boundaries(self):
        cases = ((300, 0, 150, 0, 0, 1), (299, 0, 150, 0, 0, 0),
                 (300, 15, 150, 0, 0, 1), (300, 16, 150, 0, 0, 0),
                 (300, 0, 100, 0, 0, 1), (300, 0, 99, 0, 0, 0),
                 (300, 0, 200, 0, 0, 1), (300, 0, 201, 0, 0, 0),
                 (300, 0, 0, 0, 0, 0), (300, 0, 300, 0, 0, 0),
                 (300, 0, 150, 299, 0, 1), (300, 0, 150, 300, 45, 1),
                 (300, 0, 150, 300, 44, 0), (300, 0, 150, 300, 0, 0))
        for profile, lib in self.libraries.items():
            for support, bad, upper, competing, opposite, expected in cases:
                with self.subTest(profile=profile, numeric=(support, bad, upper, competing, opposite)):
                    self.assertEqual(expected,
                        lib.test078_numeric(support, bad, upper, competing, opposite))


if __name__ == '__main__':
    unittest.main()
