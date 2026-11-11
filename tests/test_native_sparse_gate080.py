"""TEST080: narrow-corridor past motion with unavailable legacy phase.

Procedural signatures/maps test native proof boundaries, not phone acceptance,
input acknowledgements, opening a door, or entering the shop.
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


def pair(direction=3, amount=1, pixels=None):
    dx, dy = DIRS[direction]
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                           gold_state=2) for _ in range(2)]
    for scene in (before, after):
        scene.tiles[:] = [1] * 230
    for x, y, kind in ((2 * dx, 2 * dy, 5),
                       (2 * dx + dy, 2 * dy - dx, 2),
                       (2 * dx - dy, 2 * dy + dx, 2),
                       (-5, -1, 3), (3, 1, 3)):
        before.tiles[cell(x, y)] = kind
        xx, yy = x - dx * amount, y - dy * amount
        if -11 <= xx <= 11 and -5 <= yy <= 4:
            after.tiles[cell(xx, yy)] = kind
    # Every before pixel in the old intensity mask is zero. That makes all73
    # old scores +INF independently of the proposed additional proof.
    rng = random.Random(80080)
    world = bytearray(W * H)
    for y in range(36, 84):
        for x in range(90, 139):
            world[y * W + x] = rng.randrange(20, 221)
    before.signature[:] = world
    shift = 9 * amount if pixels is None else pixels
    moved = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x - dx * shift, y - dy * shift
            if 0 <= xx < W and 0 <= yy < H:
                moved[int(yy) * W + int(xx)] = world[y * W + x]
    after.signature[:] = moved
    return [before, after]


SHIM = r'''
int test080_legacy_finite(const NG2Scene*a,const NG2Scene*b) {
    View v[2];int amount,d,count=0;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    count+=isfinite(intensity(&v[0],&v[1],0,0));
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d)
        count+=isfinite(intensity(&v[0],&v[1],amount*ddx[d],amount*ddy[d]));
    return count;
}
int test080_pixel(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
#if TEST080_PRESENT
    return sparse_gate_pixel(a,b,x,y,sx,sy);
#else
    (void)a;(void)b;(void)x;(void)y;(void)sx;(void)sy;return 0;
#endif
}
void test080_phase(const NG2Scene*a,const NG2Scene*b,int shifts[146],double scores[73],int counts[219]) {
    View v[2];int n=0,amount,d;view(a->signature,&v[0]);view(b->signature,&v[1]);
    for(amount=0;amount<=18;++amount)for(d=1;d<=(amount?4:1);++d) {
        int sx=amount*ddx[d],sy=amount*ddy[d];shifts[2*n]=sx;shifts[2*n+1]=sy;
#if TEST080_PRESENT
        scores[n]=sparse_gate_intensity(a,b,&v[0],&v[1],sx,sy,&counts[3*n],&counts[3*n+1]);
#else
        scores[n]=INFINITY;counts[3*n]=counts[3*n+1]=counts[3*n+2]=0;
#endif
        ++n;
    }
}
/* Independent direct scalar specification: no production mask, cached View,
 * feature helper, intensity helper or round helper is called here. */
static int test080_scalar_pixel(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
    int ox,oy;
    if(y==64||y==65||y+sy==64||y+sy==65)return 0;
    for(oy=-1;oy<=1;++oy)for(ox=-1;ox<=1;++ox) {
        int ax=x+ox,ay=y+oy,bx=ax+sx,by=ay+sy,side;
        for(side=0;side<2;++side) {
            int xx=side?bx:ax,yy=side?by:ay;
            if(xx<40||xx>=179||yy<20||yy>=85
                ||(xx>=103&&xx<122&&yy>=43&&yy<61)
                ||(xx>=115&&xx<154&&yy>=38&&yy<80)
                ||(xx>=101&&xx<123&&yy>=80))return 0;
        }
        {
            int gx=(4*ax-34)/36-11,gy=(4*ay-9)/36-5;
            int hx=(4*bx-34)/36-11,hy=(4*by-9)/36-5;
            int at=(gy+5)*23+gx+11,bt=(hy+5)*23+hx+11;
            int kind=a->tiles[at];
            if(!kind||kind!=b->tiles[bt]||kind==5||kind==6
                ||a->protected_cells[at]||b->protected_cells[bt])return 0;
        }
    }
    return 1;
}
static int test080_scalar_normalized(const NG2Scene*s,int x,int y) {
    int yy,total=0,raw=s->signature[y*W+x],result;
    if(raw<=6)return 0;
    for(yy=y-1;yy<=y+1;++yy)
        total+=(s->signature[yy*W+x-1]+s->signature[yy*W+x]+s->signature[yy*W+x+1]+1)/3;
    result=raw-(total+1)/3+128;
    return result<0?0:(result>255?255:result);
}
static double test080_scalar_phase(const NG2Scene*a,const NG2Scene*b,int sx,int sy,int out[3]) {
    uint32_t count=0,sa=0,sb=0,qa=0,qb=0,total=0;
    int x,y;double contrast,ma,mb,gain;unsigned char lut[256];
    memset(out,0,3*sizeof(*out));
    for(y=20;y<85;++y)for(x=40;x<179;++x) {
        unsigned av,bv;if(!test080_scalar_pixel(a,b,x,y,sx,sy))continue;
        av=test080_scalar_normalized(a,x,y);bv=test080_scalar_normalized(b,x+sx,y+sy);
        if(av<=6||bv<=6)continue;
        ++count;sa+=av;sb+=bv;qa+=av*av;qb+=bv*bv;++out[y<65?1:2];
    }
    out[0]=(int)count;if(count<300)return INFINITY;
    contrast=(sqrt(((double)qa-(double)sa*sa/count)/count)+sqrt(((double)qb-(double)sb*sb/count)/count))/2;
    ma=(double)sa/count;mb=(double)sb/count;
    if(!isfinite(contrast)||contrast<2.5||ma<6||mb<6)return INFINITY;
    gain=ma/mb;if(gain<.65)gain=.65;else if(gain>1.55)gain=1.55;
    for(x=0;x<256;++x) {
        volatile double product=x*gain;unsigned n=(unsigned)product;double f=product-n;
        if(f>.5||(f==.5&&(n&1u)))++n;
        lut[x]=(unsigned char)(n>255?255:n);
    }
    for(y=20;y<85;++y)for(x=40;x<179;++x) {
        int av,bv;if(!test080_scalar_pixel(a,b,x,y,sx,sy))continue;
        av=test080_scalar_normalized(a,x,y);bv=test080_scalar_normalized(b,x+sx,y+sy);
        if(av>6&&bv>6)total+=(uint32_t)abs(av-lut[bv]);
    }
    return(double)total/count/contrast;
}
int test080_scalar_parity(const NG2Scene*a,const NG2Scene*b) {
    View v[2];int amount,d;view(a->signature,&v[0]);view(b->signature,&v[1]);
    for(amount=0;amount<=18;++amount)for(d=1;d<=(amount?4:1);++d) {
        int sx=amount*ddx[d],sy=amount*ddy[d],actual[3],expected[3];double got,want;
        want=test080_scalar_phase(a,b,sx,sy,expected);
#if TEST080_PRESENT
        got=sparse_gate_intensity(a,b,&v[0],&v[1],sx,sy,actual,actual+1);
#else
        got=INFINITY;memset(actual,0,sizeof(actual));
#endif
        if(memcmp(actual,expected,sizeof(actual))||got!=want)return 0;
    }
    return 1;
}
void test080_proof(const NG2Scene*a,const NG2Scene*b,int direction,int legacy_mode,NG2Motion*out) {
    View v[2];Candidate legacy[73];int i;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    for(i=0;i<73;++i){legacy[i].score=INFINITY;legacy[i].sx=legacy[i].sy=0;}
    if(legacy_mode==1)legacy[0].score=.2;
    if(legacy_mode==2)legacy[72].score=.8;
    if(legacy_mode==3)legacy[0].score=NAN;
    if(legacy_mode==4)legacy[72].score=NAN;
    if(legacy_mode==5)legacy[0].score=-INFINITY;
    if(legacy_mode==6)legacy[72].score=-INFINITY;
#if TEST080_PRESENT
    sparse_gate_motion(a,b,direction,v,legacy,out);
#else
    (void)direction;(void)out;(void)legacy;
#endif
}
int test080_phase_numeric(double first,double second,int support,int upper,int direction,int sx,int sy,int other) {
    Candidate c[73];int i,regions[2]={upper,support-upper};
    for(i=0;i<73;++i){c[i].score=INFINITY;c[i].sx=c[i].sy=0;}
    c[0].score=first;c[0].sx=sx;c[0].sy=sy;c[1].score=second;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
#if TEST080_PRESENT
    return sparse_gate_phase_valid(c,direction,support,regions);
#else
    (void)c;(void)direction;(void)regions;return 0;
#endif
}
void test080_phase_values(int count,int first,int second,int spread,double*out,int values[3]) {
    NG2Scene a,b;View av,bv;int x,y,n=0;
    memset(&a,0,sizeof(a));memset(&b,0,sizeof(b));memset(&av,0,sizeof(av));memset(&bv,0,sizeof(bv));
    memset(a.tiles,1,CELLS);memset(b.tiles,1,CELLS);
    for(y=20;y<85&&n<count;++y)for(x=40;x<179&&n<count;++x) {
        int sign=(n&1)?1:0;if(!test080_scalar_pixel(&a,&b,x,y,0,0))continue;
        av.normalized[y*W+x]=(unsigned char)(first+sign*spread);
        bv.normalized[y*W+x]=(unsigned char)(second+sign*spread);++n;
    }
#if TEST080_PRESENT
    *out=sparse_gate_intensity(&a,&b,&av,&bv,0,0,values,values+1);
#else
    *out=INFINITY;memset(values,0,3*sizeof(*values));
#endif
}
int test080_axis_numeric(int support,int bad,int competing,int opposite) {
    ClosedGateAxisCache*c=(ClosedGateAxisCache*)calloc(1,sizeof(*c));
    Candidate candidates[73];unsigned int state=80080;int i,n=1,amount,d,result;
    if(!c)return 0;
    candidates[0].sx=candidates[0].sy=0;candidates[0].score=0;
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];candidates[n].score=1;++n;
    }
    for(i=0;i<support;++i) {
        int at,x,y;
        do {
            state=1664525u*state+1013904223u;x=42+2*(int)((state>>8)%64);
            state=1664525u*state+1013904223u;y=54+(int)((state>>8)%29);at=y*W+x;
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
#if TEST080_PRESENT
    result=sparse_gate_axis_strong(c,candidates);
#else
    (void)candidates;result=0;
#endif
    free(c);return result;
}
'''


class NativeSparseGate080Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test080-sparse-gate-')
        source = Path(os.environ.get('NECRO_TEST080_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        present = 'static void sparse_gate_motion(' in source.read_text()
        shim = Path(cls.temp.name) / 'sparse-gate-proof.c'
        shim.write_text('#define TEST080_PRESENT ' + str(int(present)) + '\n#include "' +
                        str(source) + '"\n' + SHIM)
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm',
                '-o', str(library)], check=True, capture_output=True)
            lib = C.CDLL(str(library)); ptr = C.POINTER(Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_choose.argtypes = [ptr, C.c_int, C.c_int, C.POINTER(C.c_uint16),
                C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                C.c_int, C.POINTER(Entrance)]
            lib.test080_legacy_finite.argtypes = [ptr, ptr]
            ints = C.POINTER(C.c_int); doubles = C.POINTER(C.c_double)
            lib.test080_pixel.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int]
            lib.test080_phase.argtypes = [ptr, ptr, ints, doubles, ints]
            lib.test080_scalar_parity.argtypes = [ptr, ptr]
            lib.test080_proof.argtypes = [ptr, ptr, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test080_phase_numeric.argtypes = [C.c_double, C.c_double, *([C.c_int] * 6)]
            lib.test080_phase_values.argtypes = [C.c_int, C.c_int, C.c_int, C.c_int, doubles, ints]
            lib.test080_axis_numeric.argtypes = [C.c_int] * 4
            cls.libraries[profile] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, images, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def test_public_four_direction_sparse_arrival_reaches_closed_door_without_entry(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    images = pair(direction)
                    self.assertEqual(0, lib.test080_legacy_finite(
                        C.byref(images[0]), C.byref(images[1])))
                    self.assertEqual((1, dx, dy), self.result(lib, images, direction),
                        'the procedural world moves one unit before the still-closed shop door')
                    visits = (C.c_uint16 * 1089)(); visits[16 * 33 + 16] = 1
                    visits[(16 + dy) * 33 + 16 + dx] = 1
                    entrance = Entrance(); decision = Decision()
                    self.assertEqual(1, lib.ng2_choose(C.byref(images[1]), dx, dy,
                        visits, len(visits), C.byref(entrance), C.byref(decision)))
                    self.assertEqual((direction, 5, 5),
                        (decision.direction, decision.reason, decision.obstacle))
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(images[0]),
                        C.byref(images[1]), direction, 0, 0, 1, C.byref(entrance)))
                    self.assertEqual(0, entrance.valid)

    def proof(self, lib, images, direction=3, legacy=0, initial=0):
        out = Motion(initial, 7 if initial else 0, -3 if initial else 0)
        lib.test080_proof(C.byref(images[0]), C.byref(images[1]), direction, legacy, C.byref(out))
        return out.kind, out.dx, out.dy

    def phase(self, lib, images):
        shifts = (C.c_int * 146)(); scores = (C.c_double * 73)(); counts = (C.c_int * 219)()
        lib.test080_phase(C.byref(images[0]), C.byref(images[1]), shifts, scores, counts)
        return [(shifts[2*i], shifts[2*i+1], scores[i], tuple(counts[3*i:3*i+3]))
                for i in range(73)]

    def test_scope_closed_geometry_old_anchors_and_observed_endpoints_are_required(self):
        cases = []
        for side in (0, 1):
            for field, value in (('state', 1), ('gold_state', 1), ('goods', 1)):
                images = pair(); setattr(images[side], field, value)
                cases.append((f'{side}:{field}', images))
            for label, point, kind in (('protected', (8, 3), None), ('item', (8, 3), 6),
                                       ('extra_gold', (8, 3), 2), ('origin', (0, 0), 4)):
                images = pair()
                if kind is None:
                    images[side].protected_cells[cell(*point)] = 1
                else:
                    images[side].tiles[cell(*point)] = kind
                cases.append((f'{side}:{label}', images))
        for side, point, kind, label in (
                (0, (0, -1), 0, 'unknown_next'), (0, (0, -2), 1, 'old_open'),
                (1, (0, -1), 1, 'latest_open'), (0, (-1, -2), 1, 'old_gold_missing'),
                (1, (1, -1), 1, 'latest_gold_missing'), (0, (-5, -1), 1, 'one_old_anchor'),
                (1, (-5, 0), 4, 'old_anchor_lost')):
            images = pair(); images[side].tiles[cell(*point)] = kind; cases.append((label, images))
        images = pair()
        for x, y in ((-5, -1), (3, 1)):
            images[0].tiles[cell(x, y)] = images[1].tiles[cell(x, y+1)] = 1
        for x, y in ((-2, 0), (2, -4)):
            images[0].tiles[cell(x, y)] = images[1].tiles[cell(x, y+1)] = 3
        cases.append(('two_collinear_old_anchors', images))
        images = pair(); images[0].tiles[cell(-5, -1)] = images[0].tiles[cell(3, 1)] = 1
        cases.append(('new_only_stone_cannot_anchor', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, label=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            images = pair(); images[0].tiles[cell(8, 3)] = 3
            images[1].tiles[cell(8, 4)] = 4
            self.assertEqual((1, 0, -1), self.proof(lib, images),
                'an unrelated lost old stone is never counted as a retained anchor')

    def test_only_all_positive_infinite_legacy_and_unknown_output_may_use_proof(self):
        for profile, lib in self.libraries.items():
            images = pair()
            with self.subTest(profile=profile):
                self.assertEqual((1, 0, -1), self.proof(lib, images))
                for legacy in range(1, 7):
                    self.assertEqual((0, 0, 0), self.proof(lib, images, legacy=legacy))
                for known in (1, 2, 3, 4, 5):
                    self.assertEqual((known, 7, -3), self.proof(lib, images, initial=known))

    def test_phase_uses_all_nine_actual_dependencies_and_fixed_disjoint_bands(self):
        # Diagonal-only UI intersections catch checking just center/cardinal pixels.
        bad_points = ((102, 42), (122, 42), (102, 61), (122, 61),
                      (114, 37), (100, 79), (123, 79), (40, 30), (178, 30),
                      (90, 20), (90, 84), (90, 64), (90, 65))
        for profile, lib in self.libraries.items():
            images = pair(); a, b = images
            for x, y in bad_points:
                with self.subTest(profile=profile, point=(x, y)):
                    self.assertEqual(0, lib.test080_pixel(C.byref(a), C.byref(b), x, y, 0, 0))
            self.assertEqual(1, lib.test080_pixel(C.byref(a), C.byref(b), 90, 40, 0, 0))
            for sy in (24, 25):
                self.assertEqual(0, lib.test080_pixel(C.byref(a), C.byref(b), 90, 40, 0, sy))
            # Same checks apply to all nine actual dependencies in either frame.
            for side in (0, 1):
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for bad in (0, 4, 5, 6, 'protected'):
                            images = pair(); x, y = 90 + ox, 40 + oy
                            gx, gy = (4*x-34)//36-11, (4*y-9)//36-5
                            if bad == 'protected':
                                images[side].protected_cells[cell(gx, gy)] = 1
                            else:
                                images[side].tiles[cell(gx, gy)] = bad
                            self.assertEqual(0, lib.test080_pixel(C.byref(images[0]),
                                C.byref(images[1]), 90, 40, 0, 0))

    def test_phase_all73_matches_independent_scalar_specification(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    images = pair(direction)
                    self.assertEqual(1, lib.test080_scalar_parity(C.byref(images[0]), C.byref(images[1])))
                    rows = self.phase(lib, images)
                    self.assertEqual(73, len({(r[0], r[1]) for r in rows}))
                    ranked = sorted(rows, key=lambda r: r[2]); first, second = ranked[:2]
                    self.assertEqual((-9*dx, -9*dy), first[:2])
                    self.assertEqual(0, first[2]); self.assertGreaterEqual(second[2]-first[2], .08)
                    self.assertGreaterEqual(first[3][0], 300)
                    self.assertGreaterEqual(min(first[3][1:]), 100)

    def test_phase_score_gap_support_bands_contrast_and_gain_boundaries(self):
        for profile, lib in self.libraries.items():
            def valid(first=.45, second=.53, support=300, upper=100,
                      direction=3, sx=0, sy=9, other=0):
                return lib.test080_phase_numeric(first, second, support, upper,
                                                 direction, sx, sy, other)
            with self.subTest(profile=profile):
                self.assertEqual(1, valid())
                self.assertEqual(0, valid(first=math.nextafter(.45, math.inf)))
                below = math.nextafter(.53, -math.inf)
                self.assertLess(below-.45, .08); self.assertGreaterEqual(.53-.45, .08)
                self.assertEqual(0, valid(second=below))
                for options in ({'support': 299}, {'upper': 99}, {'upper': 201},
                                {'direction': 0}, {'direction': 5}, {'sx': 1}, {'sy': 8},
                                {'first': math.inf}, {'first': -math.inf}, {'first': math.nan},
                                {'other': 1}, {'other': 2}):
                    self.assertEqual(0, valid(**options), options)
                self.assertEqual(1, valid(upper=200))
                self.assertEqual(1, valid(second=math.inf))
                for count, first, second, spread, expected_finite in (
                        (299, 100, 100, 5, False), (300, 100, 100, 4, False),
                        (300, 100, 100, 5, True), (300, 6, 100, 0, False),
                        (300, 100, 200, 10, True), (300, 200, 100, 10, True)):
                    score = C.c_double(); counts = (C.c_int * 3)()
                    lib.test080_phase_values(count, first, second, spread, C.byref(score), counts)
                    self.assertEqual(expected_finite, math.isfinite(score.value))
                    if expected_finite:
                        gain = min(1.55, max(.65, (first+spread/2)/(second+spread/2)))
                        loss = sum(abs(av-min(255, round(bv*gain))) for av, bv in
                                   ((first, second), (first+spread, second+spread)))/2
                        self.assertEqual(loss/(spread/2), score.value)

    def test_fixed_axis_strength_and_all73_competitor_lead_are_required(self):
        cases = ((299, 0, 0, 0, 0), (300, 0, 0, 0, 1),
                 (400, 20, 0, 0, 1), (400, 21, 0, 0, 0),
                 (400, 0, 299, 0, 1), (400, 0, 300, 44, 0),
                 (400, 0, 300, 45, 1), (400, 20, 300, 59, 0),
                 (400, 20, 300, 60, 1))
        for profile, lib in self.libraries.items():
            for support, bad, competing, opposite, expected in cases:
                with self.subTest(profile=profile, case=(support, bad, competing, opposite)):
                    self.assertEqual(expected, lib.test080_axis_numeric(support, bad, competing, opposite))

    def test_zero_reverse_two_cells_partial_pixels_and_known_public_results_are_distinct(self):
        for profile, lib in self.libraries.items():
            for amount, pixels in ((0, None), (-1, None), (2, None), (1, 8), (1, 10)):
                with self.subTest(profile=profile, amount=amount, pixels=pixels):
                    self.assertEqual((0, 0, 0), self.proof(lib, pair(amount=amount, pixels=pixels)))
            images = pair(pixels=8); exact = pair(pixels=9)
            images[1].signature[:] = [(a+b+1)//2 for a, b in
                                      zip(images[1].signature, exact[1].signature)]
            self.assertEqual((0, 0, 0), self.proof(lib, images),
                'an interpolated eight-and-a-half pixel phase is not a unit')
            images = list(procedural_pair(3))
            self.assertEqual((1, 0, -1), self.result(lib, images))
            images = list(procedural_pair(3, amount=0, overlay=False))
            self.assertEqual((2, 0, 0), self.result(lib, images))
            images = list(procedural_pair(3, amount=-1))
            self.assertNotEqual(1, self.result(lib, images)[0])
