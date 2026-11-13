"""TEST096: received one-step reveals need one old STONE and independent proofs.

All pixels below are procedural. This is a motion contract, not phone accuracy.
"""
import ctypes as C
import os
import math
from copy import deepcopy
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion
from tests.test_native_side_gate081 import pair as side_pair

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def pair_a(direction=1):
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                          gold_state=2) for _ in range(2)]
    before.tiles[:] = [4] * 230
    dx, dy = DIRS[direction]
    rotate = {1: lambda x, y: (x, y), 2: lambda x, y: (-x, -y),
              3: lambda x, y: (-y, x), 4: lambda x, y: (y, -x)}[direction]
    for x, y, kind in ((0, 0, 1), (-1, 0, 1), (-2, -2, 2),
                        (-1, -2, 0), (0, -2, 0), (0, -1, 3)):
        xx, yy = rotate(x, y)
        before.tiles[cell(xx, yy)] = kind
    for y in range(-5, 5):
        for x in range(-11, 12):
            xx, yy = x - dx, y - dy
            if -11 <= xx <= 11 and -5 <= yy <= 4:
                after.tiles[cell(xx, yy)] = before.tiles[cell(x, y)]
    for x, y, kind in ((0, -2, 5), (1, -2, 2)):
        xx, yy = rotate(x, y)
        after.tiles[cell(xx, yy)] = kind
    rng = random.Random(96096)
    world = bytearray([96] * (W * H))
    for ys in (range(30, 43, 3), range(60, 76, 3)):
        points = [(x, y) for y in ys for x in range(51, 91, 3)]
        rng.shuffle(points)
        for x, y in points[:60]:
            world[y * W + x] = rng.randrange(160, 224) if rng.getrandbits(1) else rng.randrange(16, 40)
    moved = bytearray([96] * (W * H))
    for y in range(H):
        for x in range(W):
            xx, yy = x - 9 * dx, y - 9 * dy
            if 0 <= xx < W and 0 <= yy < H:
                moved[yy * W + xx] = world[y * W + x]
    before.signature[:] = world
    after.signature[:] = moved
    return [before, after]


def pair_b(direction=4):
    images = side_pair(direction=direction)
    before, after = images
    dx, dy = DIRS[direction]
    keep = {3: (-1, 1), 4: (1, -1), 1: (1, 1), 2: (-1, -1)}[direction]
    for y in range(-5, 5):
        for x in range(-11, 12):
            i = cell(x, y)
            if (before.tiles[i] == 1 and (x, y) not in ((0, 0), (dx, dy))) or (before.tiles[i] == 3 and (x, y) != keep):
                before.tiles[i] = 4
                xx, yy = x - dx, y - dy
                if -11 <= xx <= 11 and -5 <= yy <= 4:
                    after.tiles[cell(xx, yy)] = 4
    after.tiles[cell(dx, dy)] = 4  # Newly lit next wall is separate from arrival.
    rng = random.Random(196096)
    phases = {(x, y): (rng.randrange(4), rng.randrange(4))
              for y in range((H + 7) // 8) for x in range((W + 7) // 8)}
    world = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            px, py = phases[x // 8, y // 8]
            world[y * W + x] = 30 + 180 * (((x + px) // 2 + (y + py) // 2) % 2) + rng.randrange(-9, 10)
    moved = bytearray(rng.randrange(20, 221) for _ in range(W * H))
    for y in range(H):
        for x in range(W):
            xx, yy = x - 9 * dx, y - 9 * dy
            gx, gy = (4 * x - 34) // 36 - 11, (4 * y - 9) // 36 - 5
            if 0 <= xx < W and 0 <= yy < H and -11 <= gx <= 11 and -5 <= gy <= 4 and before.tiles[cell(gx, gy)]:
                moved[yy * W + xx] = world[y * W + x]
    before.signature[:] = world
    after.signature[:] = moved
    return images


def dirt_support(images, points):
    before, after = deepcopy(images)
    for y in range(-5, 5):
        for x in range(-11, 12):
            if before.tiles[cell(x, y)] == 4:
                before.tiles[cell(x, y)] = 1
                if x + 1 <= 11 and after.tiles[cell(x + 1, y)] == 4:
                    after.tiles[cell(x + 1, y)] = 1
    for x, y in points:
        before.tiles[cell(x, y)] = after.tiles[cell(x + 1, y)] = 4
    return [before, after]


SHIM = r'''
void test096_stats(const NG2Scene*a,const NG2Scene*b,int d,double out[6],int vals[32]) {
    View v[2];Candidate raw[73],phase[73];StaticGradientCache*cache=calloc(1,sizeof(*cache));
    int n=1,amount,dir,s,bad,regions[2];view(a->signature,&v[0]);view(b->signature,&v[1]);
    raw[0].sx=raw[0].sy=phase[0].sx=phase[0].sy=0;raw[0].score=intensity(&v[0],&v[1],0,0);
    phase[0].score=sparse_gate_intensity(a,b,&v[0],&v[1],0,0,NULL,NULL);
    for(amount=1;amount<=18;++amount)for(dir=1;dir<=4;++dir){
        raw[n].sx=phase[n].sx=amount*ddx[dir];raw[n].sy=phase[n].sy=amount*ddy[dir];
        raw[n].score=intensity(&v[0],&v[1],raw[n].sx,raw[n].sy);
        phase[n].score=sparse_gate_intensity(a,b,&v[0],&v[1],phase[n].sx,phase[n].sy,NULL,NULL);++n;
    }
    qsort(raw,73,sizeof(*raw),ranked);qsort(phase,73,sizeof(*phase),ranked);
    out[0]=raw[0].score;out[1]=raw[1].score;out[2]=phase[0].score;out[3]=phase[1].score;
    vals[0]=raw[0].sx;vals[1]=raw[0].sy;
    sparse_gate_intensity(a,b,&v[0],&v[1],phase[0].sx,phase[0].sy,&s,regions);
    vals[2]=s;vals[3]=regions[0];vals[4]=regions[1];vals[5]=sparse_gate_phase_valid(phase,d,s,regions);
    static_gradient_features(a,cache->before,cache->indices,&cache->count);static_gradient_features(b,cache->after,NULL,NULL);
    static_gradient_texture(cache,raw[0].sx,raw[0].sy,&s,&bad,regions);
    vals[6]=s;vals[7]=bad;vals[8]=regions[0];vals[9]=regions[1];vals[10]=texture_strength(s,bad,95);
#if TEST096_PRESENT
    vals[11]=unique_revealed_singleton_translation(a,b,d,raw[0].sx,raw[0].sy);
    vals[12]=revealed_singleton_raw_domain(raw,d);
#endif
    vals[13]=0;for(n=1;n<73;++n){int count,opposite;static_gradient_texture(cache,phase[n].sx,phase[n].sy,&count,&opposite,NULL);if(!texture_lead(s,bad,count,opposite))++vals[13];}
    free(cache);
    world_blur_texture(a,b,v,raw[0].sx,raw[0].sy,&s,&bad,regions);
    vals[14]=s;vals[15]=bad;vals[16]=regions[0];vals[17]=regions[1];vals[18]=texture_strength(s,bad,95);vals[19]=0;
    for(n=1;n<73;++n){int count,opposite;world_blur_texture(a,b,v,raw[n].sx,raw[n].sy,&count,&opposite,NULL);if(!texture_lead(s,bad,count,opposite)){if(vals[19]<2){vals[26+2*vals[19]]=raw[n].sx;vals[27+2*vals[19]]=raw[n].sy;}++vals[19];}}
    {ClosedGateAxisCache*c=calloc(1,sizeof(*c));closed_gate_axis_features(a,c->before,c->indices,&c->count);closed_gate_axis_features(b,c->after,NULL,NULL);
    closed_gate_axis_texture(c,raw[0].sx,raw[0].sy,&s,&bad,regions);vals[20]=s;vals[21]=bad;vals[22]=regions[0];vals[23]=regions[1];vals[24]=texture_strength(s,bad,95);vals[25]=0;
    for(n=1;n<73;++n){int count,opposite;closed_gate_axis_texture(c,raw[n].sx,raw[n].sy,&count,&opposite,NULL);if(!texture_lead(s,bad,count,opposite))++vals[25];}free(c);}
}
int test096_geometry(const NG2Scene*a,const NG2Scene*b,int d,int sx,int sy) {
#if TEST096_PRESENT
    if(d<1||d>4)return 0;
    return unique_revealed_singleton_translation(a,b,d,sx,sy);
#else
    (void)a;(void)b;(void)d;(void)sx;(void)sy;return 0;
#endif
}
int test096_match(const NG2Scene*a,const NG2Scene*b,int d,int tx,int ty) {
#if TEST096_PRESENT
    if(d<1||d>4)return 0;
    return revealed_singleton_match(a,b,tx,ty,d);
#else
    (void)a;(void)b;(void)d;(void)tx;(void)ty;return 0;
#endif
}
int test096_rank(int d,double first,double second,int sx,int sy,int nonfinite) {
#if TEST096_PRESENT
    Candidate c[73];int n=1,amount,dir,selected=0;
    c[0].sx=c[0].sy=0;c[0].score=3;
    for(amount=1;amount<=18;++amount)for(dir=1;dir<=4;++dir){
        c[n].sx=amount*ddx[dir];c[n].sy=amount*ddy[dir];c[n].score=3;
        if(c[n].sx==sx&&c[n].sy==sy)selected=n;
        ++n;
    }
    {Candidate swap=c[0];c[0]=c[selected];c[selected]=swap;}
    c[0].score=first;c[0].sx=sx;c[0].sy=sy;c[1].score=second;
    if(nonfinite==1)c[72].score=NAN;
    if(nonfinite==2)c[72].score=-INFINITY;
    if(nonfinite==3)c[72].score=INFINITY;
    if(nonfinite==4)c[0].score=INFINITY;
    if(nonfinite==5)c[1].score=INFINITY;
    return revealed_singleton_raw_domain(c,d);
#else
    (void)d;(void)first;(void)second;(void)sx;(void)sy;(void)nonfinite;return 0;
#endif
}
void test096_proof(const NG2Scene*a,const NG2Scene*b,int d,int initial,NG2Motion*out) {
    out->kind=initial;out->dx=initial?7:0;out->dy=initial?-3:0;
#if TEST096_PRESENT
    View v[2];Candidate c[73];int n=1,amount,dir;
    view(a->signature,&v[0]);view(b->signature,&v[1]);c[0].sx=c[0].sy=0;c[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(dir=1;dir<=4;++dir){
        c[n].sx=amount*ddx[dir];c[n].sy=amount*ddy[dir];c[n].score=intensity(&v[0],&v[1],c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);revealed_singleton_motion(a,b,d,v,c,out);
#else
    (void)a;(void)b;(void)d;
#endif
}

'''


class NativeRevealedSingleton096Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test096-revealed-singleton-')
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(os.environ.get('NECRO_TEST096_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        shim = Path(cls.temp.name) / 'proof.c'
        shim.write_text('#define TEST096_PRESENT ' + str(int('static void revealed_singleton_motion(' in source.read_text())) + '\n#include "' + str(source) + '"\n' + SHIM)
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm',
                '-o', str(library)], check=True, capture_output=True)
            lib = C.CDLL(str(library))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int, C.POINTER(Motion)]
            lib.test096_stats.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int, C.POINTER(C.c_double), C.POINTER(C.c_int)]
            lib.test096_geometry.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int, C.c_int, C.c_int]
            lib.test096_match.argtypes = lib.test096_geometry.argtypes
            lib.test096_rank.argtypes = [C.c_int, C.c_double, C.c_double, C.c_int, C.c_int, C.c_int]
            lib.test096_proof.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int, C.c_int, C.POINTER(Motion)]
            cls.libraries[profile] = lib

    def proof(self, lib, images, direction=1, initial=0):
        out = Motion()
        lib.test096_proof(C.byref(images[0]), C.byref(images[1]), direction, initial, C.byref(out))
        return out.kind, out.dx, out.dy

    def geometry(self, lib, images, direction=1, sx=9, sy=0):
        return lib.test096_geometry(C.byref(images[0]), C.byref(images[1]), direction, sx, sy)

    def test_public_known_unit_reveals_side_gate_with_one_old_stone(self):
        images = pair_a()
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                out = Motion()
                self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]), 1, C.byref(out)))
                self.assertEqual((1, -1, 0), (out.kind, out.dx, out.dy),
                    'one procedural unit must not be lost when the newly lit gate has only one old stone anchor')

    def test_both_proof_domains_move_in_four_directions_without_future_floor_credit(self):
        for profile, lib in self.libraries.items():
            for maker, domain in ((pair_a, 1), (pair_b, 2)):
                for direction, (dx, dy) in DIRS.items():
                    with self.subTest(profile=profile, domain=domain, direction=direction):
                        images = maker(direction)
                        evidence, scores = (C.c_int * 32)(), (C.c_double * 6)()
                        lib.test096_stats(C.byref(images[0]), C.byref(images[1]), direction, scores, evidence)
                        self.assertEqual(domain, evidence[12])
                        self.assertEqual(1, evidence[11])
                        self.assertEqual((1, 1), (images[0].tiles[cell(dx, dy)], images[1].tiles[cell(0, 0)]))
                        self.assertEqual(4, images[1].tiles[cell(dx, dy)], 'next dirt is not part of past-step credit')
                        if domain == 1:
                            self.assertEqual((1, 1, 0), (evidence[5], evidence[10], evidence[13]))
                        else:
                            self.assertEqual((1, 0, 1, 0), (evidence[18], evidence[19], evidence[24], evidence[25]))
                        self.assertEqual((1, dx, dy), self.proof(lib, images, direction))
                        out = Motion()
                        lib.ng2_motion(C.byref(images[0]), C.byref(images[1]), direction, C.byref(out))
                        self.assertEqual((1, dx, dy), (out.kind, out.dx, out.dy))

    def test_old_single_gold_closed_bracket_and_only_unknown_new_leaf_are_required(self):
        cases = []
        for side, point, label in ((0, (-2, -2), 'old gold'), (1, (-1, -2), 'retained gold'),
                                   (1, (1, -2), 'new leaf'), (1, (0, -2), 'closed door')):
            images = pair_a(); images[side].tiles[cell(*point)] = 1; cases.append((label, images))
        for kind in (1, 2, 3, 4, 5, 6):
            images = pair_a(); images[0].tiles[cell(0, -2)] = kind; cases.append(('known new leaf '+str(kind), images))
        for kind in (1, 2, 3, 5, 6):
            images = pair_a(); images[0].tiles[cell(-1, -2)] = kind; cases.append(('known door '+str(kind), images))
        for side in (0, 1):
            images = pair_a(); images[side].tiles[cell(-5, 0)] = 2; cases.append(('extra gold '+str(side), images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, label=label):
                    self.assertEqual(0, self.geometry(lib, images))
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            images = pair_a(); images[0].tiles[cell(-1, -2)] = 4
            self.assertEqual(1, self.geometry(lib, images), 'a newly observed door may replace old dirt')
            self.assertEqual(0, self.geometry(lib, pair_a(), direction=3), 'forward and side gate axes are distinct')

    def test_old_stone_cannot_be_replaced_by_new_stone_or_near_material_changes(self):
        for profile, lib in self.libraries.items():
            for latest in (0, 4):
                images = pair_a(); images[1].tiles[cell(1, -1)] = latest
                images[1].tiles[cell(-5, 0)] = 3
                with self.subTest(profile=profile, replace=latest):
                    self.assertEqual(0, self.geometry(lib, images))
            for point in ((1, 1), (-2, 0)):
                images = pair_a(); x, y = point
                images[0].tiles[cell(x, y)] = 3; images[1].tiles[cell(x + 1, y)] = 4
                self.assertEqual(0, self.geometry(lib, images), 'an extra old stone cannot disappear near source/target/arrival')
            for latest in (0, 4):
                images = pair_a(); images[0].tiles[cell(7, 3)] = 3; images[1].tiles[cell(8, 3)] = latest
                self.assertEqual(1, self.geometry(lib, images), 'far unsupported stone is not an affirmative anchor')
                self.assertEqual((1, -1, 0), self.proof(lib, images))
            for latest in (1, 2, 5, 6):
                images = pair_a(); images[0].tiles[cell(7, 3)] = 3; images[1].tiles[cell(8, 3)] = latest
                self.assertEqual(0, self.geometry(lib, images))

    def test_nine_matched_old_dirt_and_noncollinear_old_gold_stone_support_are_required(self):
        points = [(-6, 0), (-5, 0), (-4, 0), (-3, 0), (-6, 1), (-5, 1), (-4, 1), (-3, 1), (-6, 2)]
        for profile, lib in self.libraries.items():
            self.assertEqual(1, self.geometry(lib, dirt_support(pair_a(), points)))
            self.assertEqual(0, self.geometry(lib, dirt_support(pair_a(), points[:8])))
            images = dirt_support(pair_a(), [(-6, -2), (-5, -2), (-4, -2), (-3, -2),
                                            (2, -2), (3, -2), (4, -2), (5, -2), (6, -2)])
            images[0].tiles[cell(0, -1)] = images[1].tiles[cell(1, -1)] = 1
            images[0].tiles[cell(1, -2)] = images[1].tiles[cell(2, -2)] = 3
            self.assertEqual(0, self.geometry(lib, images), 'nine dirt points on the gold/stone line are not 2D support')

    def test_every_placement_is_checked_before_a_unique_unit_is_accepted(self):
        images = pair_a()
        images[0].tiles[cell(-2, -2)] = 0
        images[0].tiles[cell(0, -2)] = 2
        for x in (-2, -1, 1, 2):
            images[0].tiles[cell(x, -2)] = 0
        images[1].tiles[cell(-1, -1)] = 3
        for profile, lib in self.libraries.items():
            self.assertEqual(1, lib.test096_match(C.byref(images[0]), C.byref(images[1]), 1, 1, 0))
            self.assertEqual(1, lib.test096_match(C.byref(images[0]), C.byref(images[1]), 1, -1, 0))
            self.assertEqual(0, self.geometry(lib, images), 'another supported placement is not hidden by the chosen anchor')
            self.assertEqual((0, 0, 0), self.proof(lib, images))
            for sx, sy in ((0, 0), (-9, 0), (18, 0), (8, 0), (0, 9)):
                self.assertEqual(0, self.geometry(lib, pair_a(), sx=sx, sy=sy))

    def test_entire_old_and_projected_witness_rois_exclude_hud(self):
        for profile, lib in self.libraries.items():
            for x, y in ((7, -4), (5, -4)):
                images = pair_a()
                images[0].tiles[cell(0, -1)] = images[1].tiles[cell(1, -1)] = 1
                images[0].tiles[cell(x, y)] = images[1].tiles[cell(x + 1, y)] = 3
                self.assertEqual(0, self.geometry(lib, images), 'a HUD sample cannot supply the sole old stone')
            points = [(-6, 0), (-5, 0), (-4, 0), (-3, 0), (-6, 1), (-5, 1), (-4, 1), (-3, 1), (5, -4)]
            self.assertEqual(0, self.geometry(lib, dirt_support(pair_a(), points)), 'projected HUD dirt is not a ninth support')

    def test_finite_runner_exact_unit_and_separate_raw_domains_reject_bad_rankings(self):
        for profile, lib in self.libraries.items():
            self.assertEqual(1, lib.test096_rank(1, .4, .6, 9, 0, 0))
            self.assertEqual(1, lib.test096_rank(1, .4, .6, 9, 0, 3), 'unsupported other shift supplies no margin vote')
            self.assertEqual(2, lib.test096_rank(1, .5, .7, 9, 0, 0))
            self.assertEqual(0, lib.test096_rank(1, .5, .7, 9, 0, 3), 'fallback B requires every raw score finite')
            for mode in (1, 2, 4, 5):
                self.assertEqual(0, lib.test096_rank(1, .4, .6, 9, 0, mode))
            for first, second in ((math.nan, .6), (-math.inf, .6), (math.inf, .6),
                                  (.4, math.inf), (.4, math.nan), (.4, .479), (-.1, .6)):
                self.assertEqual(0, lib.test096_rank(1, first, second, 9, 0, 0))
            for sx, sy in ((0, 0), (8, 0), (18, 0), (-9, 0), (0, 9)):
                self.assertEqual(0, lib.test096_rank(1, .4, .6, sx, sy, 0))
            for direction in (0, 5):
                self.assertEqual(0, lib.test096_rank(direction, .4, .6, 9, 0, 0))

    def test_independent_pixel_strength_and_both_spatial_regions_are_required(self):
        for profile, lib in self.libraries.items():
            for maker, direction in ((pair_a, 1), (pair_b, 4)):
                for top, bottom in ((0, H), (0, 52), (52, H)):
                    images = maker(direction)
                    for scene in images:
                        raw = bytearray(scene.signature)
                        raw[top * W:bottom * W] = bytes([96]) * ((bottom - top) * W)
                        scene.signature[:] = raw
                    with self.subTest(profile=profile, maker=maker.__name__, erased=(top, bottom)):
                        self.assertEqual((0, 0, 0), self.proof(lib, images, direction))
                images = maker(direction); images[1].signature[:] = images[0].signature
                self.assertEqual((0, 0, 0), self.proof(lib, images, direction), 'an unchanged camera is not a unit')

    def test_common_floor_goods_protection_direction_and_scene_bounds_fail_closed(self):
        cases = []
        for side in (0, 1):
            for field, value in (('state', 1), ('goods', 1), ('goods', 2), ('gold_state', 1),
                                 ('abi_version', 2), ('struct_size', C.sizeof(Scene) - 1)):
                images = pair_a(); setattr(images[side], field, value); cases.append((field, images))
            images = pair_a(); images[side].protected_cells[cell(-6, 1)] = 1; cases.append(('protected', images))
            images = pair_a(); images[side].tiles[cell(-6, 1)] = 6; cases.append(('item', images))
            images = pair_a(); images[side].tiles[cell(0, 0)] = 0; cases.append(('origin', images))
        images = pair_a(); images[0].tiles[cell(-1, 0)] = 0; cases.append(('unobserved sent destination', images))
        images = pair_a(); images[1].tiles[cell(-6, 1)] = 7; cases.append(('unknown material enum', images))
        for profile, lib in self.libraries.items():
            for label, images in cases:
                with self.subTest(profile=profile, label=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, images))
            for direction in (0, 2, 3, 4, 5):
                self.assertEqual((0, 0, 0), self.proof(lib, pair_a(), direction))

    def test_existing_nonunknown_motion_is_untouched_and_inputs_are_immutable(self):
        for profile, lib in self.libraries.items():
            for images, direction in ((pair_a(), 1), (pair_b(), 4)):
                before = tuple(bytes(scene) for scene in images)
                for initial in range(1, 7):
                    self.assertEqual((initial, 7, -3), self.proof(lib, images, direction, initial))
                self.assertEqual(before, tuple(bytes(scene) for scene in images))
