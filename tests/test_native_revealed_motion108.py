"""TEST108: a confirmed unit may reveal a side gate in sparse texture.

All signatures and terrain are procedural. This checks the motion contract,
not phone accuracy; the received image pair is calibrated outside Git.
"""
import ctypes as C
from copy import deepcopy
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
W, H = 224, 104


def cell(x, y):
    return (y + 5) * 23 + x + 11


def image_domain(x, y):
    return (40 <= x < 179 and 20 <= y < 85
            and not (103 <= x < 122 and 43 <= y < 61)
            and not (115 <= x < 154 and 38 <= y < 80)
            and not (101 <= x < 123 and y >= 80))


def texture_domain(x, y):
    return y not in (51, 52) and all(
        image_domain(x + ox, y + oy)
        for oy in (-1, 0, 1) for ox in (-1, 0, 1))


def ordinary_domain(x, y):
    return (40 <= x < 179 and 20 <= y < 79
            and not (90 <= x < 139 and y >= 36))


def pair(direction=1):
    """One translated world, with two old stones and noncollinear old dirt.

    Broad straight edges supply finite intensity competition. Sparse small
    impulses carry signed texture; their central derivatives alone cannot
    reach the older structural plane's 300 votes.
    """
    dx, dy = DIRS[direction]
    rotate = {1: lambda x, y: (x, y), 2: lambda x, y: (-x, -y),
              3: lambda x, y: (-y, x), 4: lambda x, y: (y, -x)}[direction]
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene),
                           state=2, gold_state=2) for _ in range(2)]
    dirt = ((-2, -1), (0, -1), (1, -1), (-2, 0), (-2, 1), (-1, 1),
            (2, 1), (3, 1), (4, 1), (-1, 2), (3, 2), (3, 3), (4, 2))
    for x, y in dirt:
        x, y = rotate(x, y)
        before.tiles[cell(x, y)] = 4
    for x, y, kind in ((0, 0, 1), (-1, 0, 1), (-2, -2, 2),
                       (-1, -2, 0), (0, -2, 0), (1, 0, 3), (1, 1, 3)):
        x, y = rotate(x, y)
        before.tiles[cell(x, y)] = kind
    for y in range(-5, 5):
        for x in range(-11, 12):
            qx, qy = x - dx, y - dy
            if -11 <= qx <= 11 and -5 <= qy <= 4:
                after.tiles[cell(qx, qy)] = before.tiles[cell(x, y)]
    for x, y, kind in ((0, -2, 5), (1, -2, 2)):
        x, y = rotate(x, y)
        after.tiles[cell(x, y)] = kind
    rng = random.Random(108107 + direction)
    points = [(x, y) for y in range(23, 83, 3) for x in range(43, 177, 3)
              if texture_domain(x, y) and texture_domain(x - 9 * dx, y - 9 * dy)
              and not (52 <= x < 75 and 20 <= y < 43)]
    ordinary = [p for p in points if ordinary_domain(*p)
                and ordinary_domain(p[0] - 9 * dx, p[1] - 9 * dy)]
    additional = [p for p in points if p not in ordinary]
    rng.shuffle(ordinary)
    rng.shuffle(additional)
    xvalues = [rng.randrange(24, 105) for _ in range(12)]
    yvalues = [rng.randrange(24, 105) for _ in range(9)]
    world = bytearray(xvalues[x // 21] + yvalues[y // 16]
                      for y in range(H) for x in range(W))
    for x, y in ordinary[:205] + additional[:85]:
        world[y * W + x] = max(7, min(250, world[y * W + x] + rng.choice((-11, 11))))
    moved = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            qx, qy = x - 9 * dx, y - 9 * dy
            if 0 <= qx < W and 0 <= qy < H:
                moved[qy * W + qx] = world[y * W + x]
    before.signature[:] = world
    after.signature[:] = moved
    return before, after


def limited_pair(direction=3):
    """A narrow upper passage and the lower room expose different masks.

    The ordinary mask has genuinely unavailable alternate comparisons. Room
    texture remains visible in the independent fixed world domain.
    """
    before, after = pair(direction)
    dx, dy = DIRS[direction]
    rng = random.Random(710108 + direction)
    source = bytearray(before.signature)
    for y in range(H):
        for x in range(W):
            visible = (90 <= x < 115 and 20 <= y < 53) or (99 <= x < 170 and 53 <= y < 85)
            if not visible:
                source[y * W + x] = 0
            elif y < 43 or (100 <= x < 139 and 61 <= y < 79):
                source[y * W + x] = rng.randrange(16, 240)
    moved = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            qx, qy = x - 9 * dx, y - 9 * dy
            if 0 <= qx < W and 0 <= qy < H:
                moved[qy * W + qx] = source[y * W + x]
    before.signature[:] = source
    after.signature[:] = moved
    return before, after


SHIM = r'''
static void test108_candidates(const NG2Scene *a,const NG2Scene *b,Candidate raw[73]) {
    View v[2];int amount,k,n=1;
    view(a->signature,&v[0]);view(b->signature,&v[1]);
    raw[0].sx=raw[0].sy=0;raw[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(k=1;k<=4;++k){
        raw[n].sx=amount*ddx[k];raw[n].sy=amount*ddy[k];
        raw[n].score=intensity(v,v+1,raw[n].sx,raw[n].sy);++n;
    }
    qsort(raw,73,sizeof(*raw),ranked);
}
int test108_original_domain(const NG2Scene *a,const NG2Scene *b,int d,double out[2]) {
    Candidate raw[73];int k;test108_candidates(a,b,raw);
    out[0]=raw[0].score;out[1]=raw[1].score;
    for(k=0;k<73;++k)if(!isfinite(raw[k].score))return 0;
    return revealed_singleton_raw_domain(raw,d)==1
        &&unique_revealed_singleton_translation(a,b,d,raw[0].sx,raw[0].sy)
        &&unique_visible_terrain_translation(a,b,raw[0].sx,raw[0].sy);
}
int test108_finite_count(const NG2Scene *a,const NG2Scene *b) {
    Candidate raw[73];int k,count=0;test108_candidates(a,b,raw);
    for(k=0;k<73;++k)count+=isfinite(raw[k].score)!=0;
    return count;
}
int test108_world_numeric(double best,double runner,int index,double value,int sx,int sy) {
#if TEST108_WORLD_PRESENT
    Candidate c[73];int k;
    for(k=0;k<73;++k){c[k].score=runner;c[k].sx=c[k].sy=0;}
    c[0].score=best;c[0].sx=sx;c[0].sy=sy;
    if(index>=0&&index<73)c[index].score=value;
    return revealed_world_rank(c,1);
#else
    (void)best;(void)runner;(void)index;(void)value;(void)sx;(void)sy;return 0;
#endif
}
int test108_world_pixel(int x,int y) {
#if TEST108_WORLD_PRESENT
    return revealed_world_pixel(x,y);
#else
    (void)x;(void)y;return 0;
#endif
}
void test108_world_stats(const NG2Scene*a,const NG2Scene*b,int d,double out[2],int counts[2]) {
#if TEST108_WORLD_PRESENT
    View v[2];Candidate c[73];int n=1,amount,k;view(a->signature,v);view(b->signature,v+1);
#if TEST108_MASK_PRESENT
    unsigned char included[N];revealed_world_mask(included);
#endif
    c[0].sx=-9*ddx[d];c[0].sy=-9*ddy[d];
    c[n].sx=c[n].sy=0;++n;
    for(amount=1;amount<=18;++amount)for(k=1;k<=4;++k){
        int sx=amount*ddx[k],sy=amount*ddy[k];
        if(sx==c[0].sx&&sy==c[0].sy)continue;
        c[n].sx=sx;c[n].sy=sy;++n;
    }
    counts[0]=0;out[1]=INFINITY;
    for(k=0;k<73;++k){
#if TEST108_MASK_PRESENT
        c[k].score=revealed_world_intensity(v,included,c[k].sx,c[k].sy);
#else
        c[k].score=revealed_world_intensity(v,c[k].sx,c[k].sy);
#endif
        counts[0]+=isfinite(c[k].score)!=0;
        if(k&&c[k].score<out[1])out[1]=c[k].score;
    }
    out[0]=c[0].score;counts[1]=revealed_world_rank(c,d);
#else
    (void)a;(void)b;(void)d;out[0]=out[1]=INFINITY;counts[0]=counts[1]=0;
#endif
}
int test108_cached_mask_is_exact_and_bounded(void) {
#if TEST108_MASK_PRESENT
    struct {unsigned char first[16],included[N],last[16];} frame;
    int k;memset(&frame,165,sizeof(frame));revealed_world_mask(frame.included);
    for(k=0;k<16;++k)if(frame.first[k]!=165||frame.last[k]!=165)return 0;
    for(k=0;k<N;++k)
        if(frame.included[k]!=(unsigned char)revealed_world_pixel(k%W,k/W))return 0;
    return 1;
#else
    return 0;
#endif
}
int test108_texture_isolation(const NG2Scene*a,const NG2Scene*b,int d,int fault,
                              int metrics[9],NG2Motion*out) {
#if TEST108_WORLD_PRESENT && TEST108_MASK_PRESENT
    View v[2];Candidate raw[73],world[73];unsigned char included[N];
    int i,x,y,support,bad,regions[2],flipped=0,target=0;
    view(a->signature,v);view(b->signature,v+1);test108_candidates(a,b,raw);
    revealed_world_mask(included);
    revealed_dependency_texture(v,included,raw[0].sx,raw[0].sy,&support,&bad,regions);
    if(fault==1)target=(6*support+99)/100;
    for(y=20;y<85;++y)for(x=40;x<179;++x){
        int old=y*W+x,other=(y+raw[0].sy)*W+x+raw[0].sx;
        if(fault==2&&y>=52)v[0].texture[old]=0;
        if(fault!=1||flipped>=target||y==51||y==52
            ||y+raw[0].sy==51||y+raw[0].sy==52
            ||!included[old]||!included[other]
            ||!v[0].texture[old]||!v[1].texture[other])continue;
        v[1].positive[other]=(unsigned char)!v[1].positive[other];++flipped;
    }
    metrics[0]=revealed_singleton_raw_domain(raw,d);
    metrics[2]=0;
    for(i=0;i<73;++i){
        world[i]=raw[i];world[i].score=revealed_world_intensity(v,included,raw[i].sx,raw[i].sy);
        metrics[2]+=isfinite(world[i].score)!=0;
    }
    metrics[1]=revealed_world_rank(world,d);
    revealed_dependency_texture(v,included,raw[0].sx,raw[0].sy,metrics+3,metrics+4,metrics+5);
    metrics[7]=1;
    for(i=1;i<73;++i){
        int count,opposite;
        revealed_dependency_texture(v,included,raw[i].sx,raw[i].sy,&count,&opposite,NULL);
        if(count>=300&&!texture_lead(metrics[3],metrics[4],count,opposite))metrics[7]=0;
    }
    metrics[8]=unique_revealed_singleton_translation(a,b,d,raw[0].sx,raw[0].sy)
        &&unique_visible_terrain_translation(a,b,raw[0].sx,raw[0].sy);
    revealed_dependency_unit_motion(a,b,d,v,raw,out);return 1;
#else
    (void)a;(void)b;(void)d;(void)fault;(void)metrics;(void)out;return 0;
#endif
}
'''


class RevealedMotion108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='revealed-motion108-')
        root = Path(cls.directory.name)
        source = root / 'fixture.c'
        present = 'static int revealed_world_rank(' in (CORE / 'NG2Navigation.c').read_text()
        cached = 'static void revealed_world_mask(' in (CORE / 'NG2Navigation.c').read_text()
        source.write_text('#define TEST108_WORLD_PRESENT ' + str(int(present))
                          + '\n#define TEST108_MASK_PRESENT ' + str(int(cached))
                          + '\n#include "NG2Navigation.c"\n' + SHIM)
        cls.output = root / 'motion.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-Wall', '-Wextra', '-Werror', '-pedantic', '-shared', '-fPIC',
                        '-I' + str(CORE), str(source), '-lm', '-o', str(cls.output)], check=True)
        cls.native = C.CDLL(str(cls.output))
        cls.native.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                          C.POINTER(Motion)]
        cls.native.ng2_motion.restype = C.c_int
        cls.native.test108_original_domain.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                                        C.c_int, C.POINTER(C.c_double)]
        cls.native.test108_original_domain.restype = C.c_int
        cls.native.test108_finite_count.argtypes = [C.POINTER(Scene), C.POINTER(Scene)]
        cls.native.test108_finite_count.restype = C.c_int
        cls.native.test108_world_numeric.argtypes = [C.c_double, C.c_double, C.c_int,
                                                    C.c_double, C.c_int, C.c_int]
        cls.native.test108_world_numeric.restype = C.c_int
        cls.native.test108_world_pixel.argtypes = [C.c_int, C.c_int]
        cls.native.test108_world_pixel.restype = C.c_int
        cls.native.test108_world_stats.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                                  C.c_int, C.POINTER(C.c_double),
                                                  C.POINTER(C.c_int)]
        cls.native.test108_cached_mask_is_exact_and_bounded.restype = C.c_int
        cls.native.test108_texture_isolation.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                                        C.c_int, C.c_int, C.POINTER(C.c_int),
                                                        C.POINTER(Motion)]
        cls.native.test108_texture_isolation.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def motion(self, before, after, direction):
        result = Motion()
        self.assertEqual(1, self.native.ng2_motion(C.byref(before), C.byref(after),
                                                 direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def test_sparse_revealed_gate_keeps_unit_credit_in_four_directions(self):
        for direction, (dx, dy) in DIRS.items():
            with self.subTest(direction=direction):
                before, after = pair(direction)
                scores = (C.c_double * 2)()
                self.assertEqual(1, self.native.test108_original_domain(
                    C.byref(before), C.byref(after), direction, scores))
                self.assertTrue(all(math.isfinite(v) for v in scores))
                original = bytes(before), bytes(after)
                self.assertEqual((1, dx, dy), self.motion(before, after, direction))
                self.assertEqual(original, (bytes(before), bytes(after)))

    def test_missing_old_world_witnesses_cannot_supply_a_unit(self):
        for fault in ('one_stone', 'lost_stone', 'lost_gold', 'missing_new_gate',
                      'protected', 'item', 'unknown_next_floor', 'few_old_dirt',
                      'old_door', 'goods'):
            with self.subTest(fault=fault):
                before, after = pair()
                if fault == 'one_stone':
                    before.tiles[cell(1, 1)] = after.tiles[cell(2, 1)] = 4
                elif fault == 'lost_stone':
                    after.tiles[cell(2, 1)] = 0
                elif fault == 'lost_gold':
                    after.tiles[cell(-1, -2)] = 0
                elif fault == 'missing_new_gate':
                    after.tiles[cell(0, -2)] = 0
                elif fault == 'protected':
                    before.protected_cells[cell(4, 1)] = 1
                elif fault == 'item':
                    after.tiles[cell(5, 1)] = 6
                elif fault == 'unknown_next_floor':
                    before.tiles[cell(-1, 0)] = 0
                elif fault == 'few_old_dirt':
                    found = 0
                    for i, kind in enumerate(before.tiles):
                        if kind == 4:
                            found += 1
                            if found > 8:
                                before.tiles[i] = 0
                                x, y = i % 23 - 11, i // 23 - 5
                                after.tiles[cell(x + 1, y)] = 0
                elif fault == 'old_door':
                    before.tiles[cell(4, 1)] = 5
                else:
                    before.goods = after.goods = 1
                self.assertNotEqual(1, self.motion(before, after, 1)[0])

    def test_supported_world_phase_replaces_unavailable_ordinary_comparisons(self):
        for direction in (3, 4):
            with self.subTest(direction=direction):
                before, after = limited_pair(direction)
                finite = self.native.test108_finite_count(C.byref(before), C.byref(after))
                self.assertLess(finite, 73)
                self.assertGreater(finite, 1)
                scores, counts = (C.c_double * 2)(), (C.c_int * 2)()
                self.native.test108_world_stats(C.byref(before), C.byref(after),
                                                direction, scores, counts)
                self.assertEqual((73, 1), tuple(counts))
                self.assertLessEqual(scores[0], .45)
                self.assertGreaterEqual(scores[1] - scores[0], .08)
                self.assertEqual((1, *DIRS[direction]), self.motion(before, after, direction))

    def test_zero_opposite_and_tween_pixels_do_not_inherit_the_new_gate_unit(self):
        before, after = pair()
        for kind, shift in (('zero', 0), ('opposite', -9), ('tween', 4), ('double', 18)):
            with self.subTest(kind=kind):
                changed = deepcopy(after)
                signature = bytearray(W * H)
                for y in range(H):
                    for x in range(W):
                        if 0 <= x + shift < W:
                            signature[y * W + x + shift] = before.signature[y * W + x]
                changed.signature[:] = signature
                self.assertNotEqual(1, self.motion(before, changed, 1)[0])

    def test_all73_pixel_phases_reserve_the_single_expected_unit(self):
        before, after = pair()
        phases = [(0, 0)] + [(n * dx, n * dy) for n in range(1, 19)
                            for dx, dy in DIRS.values()]
        for sx, sy in phases:
            with self.subTest(shift=(sx, sy)):
                changed = deepcopy(after)
                signature = bytearray(W * H)
                for y in range(H):
                    for x in range(W):
                        qx, qy = x + sx, y + sy
                        if 0 <= qx < W and 0 <= qy < H:
                            signature[qy * W + qx] = before.signature[y * W + x]
                changed.signature[:] = signature
                result = self.motion(before, changed, 1)
                if (sx, sy) == (9, 0):
                    self.assertEqual((1, -1, 0), result)
                else:
                    self.assertNotEqual(1, result[0])

    def test_flat_repeating_noise_and_moving_text_cannot_supply_a_unit(self):
        for kind in ('flat', 'repeating', 'noise', 'moving_text'):
            with self.subTest(kind=kind):
                before, after = pair()
                if kind == 'noise':
                    rng = random.Random(108711)
                    after.signature[:] = bytes(rng.randrange(256) for _ in range(W * H))
                elif kind == 'moving_text':
                    stationary = bytearray(before.signature)
                    for y in range(62, 76):
                        for x in range(125, 144):
                            stationary[y * W + x] = 220 if x % 4 == 0 or y % 5 == 0 else 32
                    shifted_text = bytearray(stationary)
                    for y in range(62, 76):
                        for x in range(125, 144):
                            shifted_text[y * W + x + 9] = stationary[y * W + x]
                    before.signature[:] = stationary
                    after.signature[:] = shifted_text
                else:
                    signature = bytes(96 if kind == 'flat' else 48 + 80 * ((x // 3) % 2)
                                      for y in range(H) for x in range(W))
                    before.signature[:] = after.signature[:] = signature
                self.assertNotEqual(1, self.motion(before, after, 1)[0])

    def test_world_phase_needs_every_finite_margin_and_the_exact_unit(self):
        numeric = self.native.test108_world_numeric
        self.assertEqual(1, numeric(.45, .53, -1, 0, 9, 0))
        for value in (math.nan, math.inf, -math.inf, -.01):
            self.assertEqual(0, numeric(.4, .6, 0, value, 9, 0))
            self.assertEqual(0, numeric(.4, .6, 72, value, 9, 0))
        self.assertEqual(0, numeric(math.nextafter(.45, math.inf), .7, -1, 0, 9, 0))
        for k in range(1, 73):
            self.assertEqual(0, numeric(.4, .6, k, .47, 9, 0))
        for sx, sy in ((0, 0), (-9, 0), (8, 0), (18, 0), (0, 9)):
            self.assertEqual(0, numeric(.4, .6, -1, 0, sx, sy))

    def test_world_mask_closes_all_dependencies_outside_ui(self):
        valid = self.native.test108_world_pixel
        for x, y in ((40, 30), (80, 20), (102, 42), (102, 43), (110, 50),
                     (100, 79), (110, 82), (178, 40)):
            self.assertEqual(0, valid(x, y), (x, y))
        for x, y in ((41, 21), (80, 30), (130, 70), (160, 83)):
            self.assertEqual(1, valid(x, y), (x, y))

    def test_world_scores_do_not_turn_missing_flat_or_aliased_pixels_into_margin(self):
        for kind in ('missing', 'flat', 'repeating'):
            with self.subTest(kind=kind):
                before, after = pair()
                signature = bytearray(W * H)
                if kind == 'missing':
                    rng = random.Random(108710)
                    for y in range(25, 40):
                        for x in range(60, 75):
                            signature[y * W + x] = rng.randrange(20, 240)
                else:
                    signature[:] = bytes(96 if kind == 'flat' else 48 + 80 * ((x // 3) % 2)
                                         for y in range(H) for x in range(W))
                before.signature[:] = after.signature[:] = signature
                scores, counts = (C.c_double * 2)(), (C.c_int * 2)()
                self.native.test108_world_stats(C.byref(before), C.byref(after), 1, scores, counts)
                self.assertEqual(0, counts[1])
                if kind != 'repeating':
                    self.assertLess(counts[0], 73)

    def test_ui_pixel_changes_never_supply_world_dependencies(self):
        before, after = limited_pair(3)
        rng = random.Random(108108)
        for image in (before, after):
            signature = bytearray(image.signature)
            for y in range(43, 61):
                for x in range(103, 122):
                    signature[y * W + x] = rng.randrange(256)
            for y in range(80, 104):
                for x in range(101, 123):
                    signature[y * W + x] = rng.randrange(256)
            image.signature[:] = signature
        self.assertEqual((1, 0, -1), self.motion(before, after, 3))

    def test_cached_dependency_mask_matches_the_full_domain_without_overrun(self):
        self.assertEqual(1, self.native.test108_cached_mask_is_exact_and_bounded())

    def test_texture_quality_and_bands_reject_with_every_phase_still_qualified(self):
        # Isolate the texture contract: signatures and normalized views stay
        # unchanged, so a bad phase cannot hide the removed-guard regression.
        for fault in (0, 1, 2):
            with self.subTest(fault=fault):
                before, after = limited_pair(3)
                original = bytes(before), bytes(after)
                metrics, result = (C.c_int * 9)(), Motion()
                self.assertEqual(1, self.native.test108_texture_isolation(
                    C.byref(before), C.byref(after), 3, fault, metrics, C.byref(result)))
                self.assertEqual((1, 1, 73), tuple(metrics[:3]))
                self.assertEqual((1, 1), (metrics[7], metrics[8]))
                support, bad, upper, lower = metrics[3:7]
                self.assertGreaterEqual(support, 300)
                if fault == 1:
                    self.assertGreater(20 * bad, support)
                    self.assertGreaterEqual(min(upper, lower), 100)
                elif fault == 2:
                    self.assertLessEqual(20 * bad, support)
                    self.assertLess(min(upper, lower), 100)
                    self.assertGreaterEqual(max(upper, lower), 300)
                else:
                    self.assertLessEqual(20 * bad, support)
                    self.assertGreaterEqual(min(upper, lower), 100)
                expected = (1, 0, -1) if fault == 0 else (0, 0, 0)
                self.assertEqual(expected, (result.kind, result.dx, result.dy))
                self.assertEqual(original, (bytes(before), bytes(after)))


if __name__ == '__main__':
    unittest.main()
