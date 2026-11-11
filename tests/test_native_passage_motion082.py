"""TEST082: an observed no-gold unit from old terrain and independent blur.

Procedural maps and grayscale fields test native proof boundaries. They do not
replay an iPhone, supply an ACK, authorize another step, or prove shop arrival.
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
from tests.test_native_blocked067 import Entrance

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def pair(direction=3, pixels=9, points=17):
    rng = random.Random(82082)
    world = bytearray(rng.randrange(14, 35) for _ in range(W * H))
    # Sparse world points supply blurred edges. Independent high-frequency
    # compression-like noise defeats the old detail plane, while the already
    # defined 21-dependency blur and two phase bands retain their evidence.
    bands = (((33, 43) if direction == 4 else (23, 34)),
             ((68, 72) if direction == 3 else
              (77, 81) if direction == 4 else (69, 80)))
    for lower, upper in bands:
        for _ in range(points):
            x, y = rng.randrange(44, 174), rng.randrange(lower, upper)
            world[y * W + x] = rng.randrange(160, 200)
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene),
                           state=2, gold_state=1) for _ in range(2)]
    before.tiles[:] = [1] * 230
    after.tiles[:] = [1] * 230
    dx, dy = DIRS[direction]
    # Every old STONE survives, with a non-collinear old DIRT anchor. This
    # observed shape contains no complete L and no gold/door bracket.
    for x, y, kind in ((-5, -2, 3), (4, 1, 3), (-4, 2, 4)):
        before.tiles[cell(x, y)] = kind
        after.tiles[cell(x - dx, y - dy)] = kind
    noise = random.Random(82083)
    moved = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x - dx * pixels, y - dy * pixels
            if 0 <= xx < W and 0 <= yy < H:
                moved[yy * W + xx] = min(255, max(0,
                    world[y * W + x] * 5 // 4 + 4 + noise.randrange(-17, 18)))
    before.signature[:] = world
    after.signature[:] = moved
    return [before, after]


def corner_pair(pixels=9):
    scenes = pair(pixels=pixels, points=20)
    for scene in scenes:
        scene.tiles[:] = [1] * 230
    for scene, x, y in ((scenes[0], 4, 1), (scenes[1], 4, 2)):
        for point in ((x, y), (x - 1, y), (x, y - 1)):
            scene.tiles[cell(*point)] = 1
        for i in range(3):
            scene.tiles[cell(x - i, y + 1)] = 4
            scene.tiles[cell(x + 1, y - i)] = 4
    return scenes


SHIM = r'''
static void test082_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]) {
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test082_stats(const NG2Scene*a,const NG2Scene*b,int direction,double out[6],int flags[12]) {
    View v[2];Candidate c[73];int k,su,ba,re[2];test082_candidates(a,b,v,c);
    out[0]=c[0].score;out[1]=c[1].score-c[0].score;
    flags[0]=c[0].sx;flags[1]=c[0].sy;
    flags[2]=unique_terrain_translation(a,b,c[0].sx,c[0].sy);
    flags[3]=unique_corner_translation(a,b,c[0].sx,c[0].sy);
    flags[4]=independent_phase(v,c);
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,&su,&ba,re);
    flags[5]=su;flags[6]=ba;flags[7]=re[0];flags[8]=re[1];flags[9]=1;
    for(k=1;k<73;++k) {int count,bad;
        world_blur_texture(a,b,v,c[k].sx,c[k].sy,&count,&bad,NULL);
        if(!texture_lead(su,ba,count,bad))flags[9]=0;
    }
    for(k=0;k<2;++k) {
        out[2+2*k]=phase_band_intensity(v,v+1,c[0].sx,c[0].sy,k);
        out[3+2*k]=phase_band_intensity(v,v+1,c[1].sx,c[1].sy,k);
    }
    flags[10]=direction;flags[11]=0;
}
void test082_proof(const NG2Scene*a,const NG2Scene*b,int direction,double score,double gap,
                   int sx,int sy,int other,NG2Motion*out) {
    View v[2];Candidate c[73];int k;test082_candidates(a,b,v,c);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    c[0].score=score;c[1].score=score+gap;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    if(other==3)c[72].score=INFINITY;
#if TEST082_PRESENT
    terrain_blur_motion(a,b,direction,v,c,out);
#else
    (void)direction;(void)out;
#endif
}
int test082_geometry(const NG2Scene*a,const NG2Scene*b,int sx,int sy) {
    return unique_terrain_translation(a,b,sx,sy);
}
int test082_kernel(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
    return world_kernel_known(a,b,x,y,sx,sy);
}
int test082_numeric(int support,int bad,int upper,int competing,int opposite) {
    return texture_strength(support,bad,95)&&upper>=100&&support-upper>=100
        &&texture_lead(support,bad,competing,opposite);
}
int test082_phase_isolation(const NG2Scene*a,const NG2Scene*b,int mode,double scores[5]) {
    View v[2];Candidate c[73];NG2Motion out={0};unsigned int state=82082;
    int x,y,k;test082_candidates(a,b,v,c);
    /* Isolate finite-band qualification at the computed View boundary.
     * Geometry and the original blur arrays remain real. This is neither
     * a manufactured phone image nor a public-path acceptance fixture. */
    for(k=1;k<73;++k)if(c[k].sx==18&&!c[k].sy) {
        Candidate swap=c[1];c[1]=c[k];c[k]=swap;break;
    }
    c[0].score=.6;c[1].score=.8;
    memset(v[0].normalized,0,N);memset(v[1].normalized,0,N);
    if(mode==2)for(y=24;y<76;++y)for(x=70;x<170;++x) {
        unsigned char value;if(!((x>=70&&x<80)||(x>=160&&x<170)))continue;
        state=1664525u*state+1013904223u;value=(unsigned char)(20+state%201);
        v[0].normalized[y*W+x]=value;v[1].normalized[(y+9)*W+x]=value;
    }
    for(k=0;k<2;++k) {
        scores[2*k]=phase_band_intensity(v,v+1,c[0].sx,c[0].sy,k);
        scores[2*k+1]=phase_band_intensity(v,v+1,c[1].sx,c[1].sy,k);
    }
    scores[4]=independent_phase(v,c);
#if TEST082_PRESENT
    terrain_blur_motion(a,b,NG2_UP,v,c,&out);
#endif
    return out.kind;
}
void test082_corner_stats(const NG2Scene*a,const NG2Scene*b,double scores[6],int flags[14]) {
    View v[2];Candidate c[73];int k,su,ba;test082_candidates(a,b,v,c);
    scores[0]=c[0].score;scores[1]=c[1].score-c[0].score;
    flags[0]=unique_corner_translation(a,b,c[0].sx,c[0].sy);
    flags[1]=unique_terrain_translation(a,b,c[0].sx,c[0].sy);
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,flags+2,flags+3,flags+4);
    flags[6]=1;
    for(k=1;k<73;++k) {
        world_blur_texture(a,b,v,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(flags[2],flags[3],su,ba))flags[6]=0;
    }
    gradient_texture(a,b,c[0].sx,c[0].sy,flags+7,flags+8,flags+9);
    flags[11]=1;
    for(k=1;k<73;++k) {
        gradient_texture(a,b,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(flags[7],flags[8],su,ba))flags[11]=0;
    }
    for(k=0;k<2;++k) {
        scores[2+2*k]=phase_band_intensity(v,v+1,c[0].sx,c[0].sy,k);
        scores[3+2*k]=phase_band_intensity(v,v+1,c[1].sx,c[1].sy,k);
    }
    flags[12]=c[0].sx;flags[13]=c[0].sy;
}
int test082_corner_proof(const NG2Scene*a,const NG2Scene*b,int mode,int flags[12]) {
    View v[2];Candidate c[73];NG2Scene aa=*a,bb=*b;NG2Motion out={0};
    unsigned int state=82082;int x,y,k,su,ba;test082_candidates(a,b,v,c);
    /* These component failures keep the other computed plane unchanged.
     * Only the public positive uses a coherent Scene/View pipeline. */
    if(mode==1)memset(v[1].blur,0,N);
    if(mode==2)for(k=0;k<N;++k) {
        state=1664525u*state+1013904223u;bb.signature[k]=(unsigned char)(20+state%201);
    }
    if(mode==3) {
        memset(bb.signature,0,N);
        for(y=0;y<H;++y)for(x=0;x<W;++x) {
            int phase=y%16;unsigned char value=(unsigned char)(20+24*(phase<8?phase:16-phase));
            aa.signature[y*W+x]=value;if(y+8<H)bb.signature[(y+8)*W+x]=value;
        }
    }
    if(mode==4||mode==5) {
        memset(v[0].normalized,0,N);memset(v[1].normalized,0,N);
        if(mode==5) {
            for(k=1;k<73;++k)if(c[k].sx==18&&!c[k].sy) {
                Candidate swap=c[1];c[1]=c[k];c[k]=swap;break;
            }
            for(y=24;y<76;++y)for(x=70;x<170;++x) {
                unsigned char value;if(!((x>=70&&x<80)||(x>=160&&x<170)))continue;
                state=1664525u*state+1013904223u;value=(unsigned char)(20+state%201);
                v[0].normalized[y*W+x]=value;v[1].normalized[(y+9)*W+x]=value;
            }
        }
    }
    if(mode==6)c[0].score=.45;
    if(mode==7)c[1].score=INFINITY;
    if(mode==8)c[72].score=NAN;
    if(mode==9)c[72].score=-INFINITY;
    world_blur_texture(&aa,&bb,v,c[0].sx,c[0].sy,flags,flags+1,flags+2);
    gradient_texture(&aa,&bb,c[0].sx,c[0].sy,flags+4,flags+5,flags+6);flags[8]=1;
    for(k=1;k<73;++k) {
        gradient_texture(&aa,&bb,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(flags[4],flags[5],su,ba))flags[8]=0;
    }
    flags[9]=isfinite(phase_band_intensity(v,v+1,c[0].sx,c[0].sy,0))
        &&isfinite(phase_band_intensity(v,v+1,c[0].sx,c[0].sy,1));
    flags[10]=isfinite(phase_band_intensity(v,v+1,c[1].sx,c[1].sy,0))
        &&isfinite(phase_band_intensity(v,v+1,c[1].sx,c[1].sy,1));
    flags[11]=independent_phase(v,c);
#if TEST082_CORNER_PRESENT
    corner_gradient_blur_motion(&aa,&bb,NG2_UP,v,c,&out);
#endif
    return out.kind;
}
int test082_corner_numeric(int blur,int blur_bad,int blur_upper,int sharp,int sharp_bad,
                           int sharp_upper,int competing,int opposite) {
    return texture_strength(blur,blur_bad,95)&&blur_upper>=100&&blur-blur_upper>=100
        &&texture_strength(sharp,sharp_bad,75)&&sharp_upper>=100&&sharp-sharp_upper>=100
        &&texture_lead(sharp,sharp_bad,competing,opposite);
}
'''


class NativePassageMotion082Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test082-passage-motion-')
        source = Path(os.environ.get('NECRO_TEST082_BASELINE_NAVIGATION',
                                     CORE / 'NG2Navigation.c'))
        present = 'static void terrain_blur_motion(' in source.read_text()
        corner_present = 'static void corner_gradient_blur_motion(' in source.read_text()
        shim = Path(cls.temp.name) / 'proof.c'
        shim.write_text(f'#define TEST082_PRESENT {int(present)}\n'
                        f'#define TEST082_CORNER_PRESENT {int(corner_present)}\n'
                        f'#include "{source}"\n' + SHIM)
        cls.libraries = {}
        for name, flags in (('o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            output = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                            '-pedantic', '-I', str(CORE), '-fPIC', '-shared',
                            str(shim), '-lm', '-o', str(output)],
                           check=True, capture_output=True)
            lib = C.CDLL(str(output))
            ptr = C.POINTER(Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                                             C.c_int, C.POINTER(Entrance)]
            lib.test082_stats.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_double),
                                          C.POINTER(C.c_int)]
            lib.test082_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                                          C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test082_geometry.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test082_kernel.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int]
            lib.test082_numeric.argtypes = [C.c_int] * 5
            lib.test082_phase_isolation.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_double)]
            lib.test082_corner_stats.argtypes = [ptr, ptr, C.POINTER(C.c_double), C.POINTER(C.c_int)]
            lib.test082_corner_proof.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_int)]
            lib.test082_corner_numeric.argtypes = [C.c_int] * 8
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def motion(self, lib, scenes, direction=3):
        result = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(scenes[0]), C.byref(scenes[1]),
                                         direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def proof(self, lib, scenes, direction=3, score=.6, gap=.2, shift=None,
              other=0, initial=0):
        dx, dy = DIRS[direction]
        sx, sy = shift if shift is not None else (-9 * dx, -9 * dy)
        result = Motion(initial, 0, 0)
        lib.test082_proof(C.byref(scenes[0]), C.byref(scenes[1]), direction,
                          score, gap, sx, sy, other, C.byref(result))
        return result.kind, result.dx, result.dy

    def test_public_four_direction_terrain_blur_unit_keeps_next_navigation_unentered(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    scenes = pair(direction)
                    scores, flags = (C.c_double * 6)(), (C.c_int * 12)()
                    lib.test082_stats(C.byref(scenes[0]), C.byref(scenes[1]),
                                      direction, scores, flags)
                    self.assertGreater(scores[0], .45)
                    self.assertGreaterEqual(scores[1], .08)
                    self.assertEqual((-9 * dx, -9 * dy), tuple(flags[:2]))
                    self.assertEqual((1, 0, 1), tuple(flags[2:5]))
                    self.assertGreaterEqual(flags[5], 300)
                    self.assertLessEqual(20 * flags[6], flags[5])
                    self.assertGreaterEqual(min(flags[7:9]), 100)
                    self.assertEqual(1, flags[9])
                    self.assertTrue(all(math.isfinite(value) for value in scores))
                    for band in range(2):
                        self.assertGreaterEqual(scores[3 + 2 * band] - scores[2 + 2 * band], .08)
                    self.assertEqual((1, dx, dy), self.motion(lib, scenes, direction))
                    entered = Entrance(99, 99, 99, 99)
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(scenes[0]),
                        C.byref(scenes[1]), direction, 0, 0, 1, C.byref(entered)))
                    self.assertEqual((0, 0, 0, 0), tuple(getattr(entered, k)
                        for k, _ in entered._fields_))

    def test_scope_requires_clear_floor_no_gold_items_protection_and_old_endpoints(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('gold_state', (0, 2, 3)),
                                  ('goods', (1, 2))):
                for value in values:
                    scenes = pair()
                    setattr(scenes[side], field, value)
                    cases.append((f'{side}:{field}:{value}', scenes))
            for kind in (2, 6):
                scenes = pair()
                scenes[side].tiles[cell(8, 3)] = kind
                cases.append((f'{side}:remote:{kind}', scenes))
            scenes = pair()
            scenes[side].protected_cells[cell(8, 3)] = 1
            cases.append((f'{side}:protection', scenes))
            for point in ((0, 0), (0, -1)) if side == 0 else ((0, 0),):
                for kind in (0, 3, 4, 5):
                    scenes = pair()
                    scenes[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            for kind in (0, 3, 4, 5):
                scenes = pair()
                scenes[1].tiles[cell(0, -1)] = kind
                with self.subTest(profile=profile, future_next=kind):
                    self.assertEqual((1, 0, -1), self.proof(lib, scenes))

    def test_all_old_terrain_and_unique_nine_reject_lost_changed_or_ambiguous_anchors(self):
        cases = []
        for point in ((-5, -1), (4, 2)):
            for kind in (0, 1, 4):
                scenes = pair()
                scenes[1].tiles[cell(*point)] = kind
                cases.append((f'lost_old:{point}:{kind}', scenes))
        for side in (0, 1):
            scenes = pair()
            scenes[side].tiles[cell(-5, -2 if side == 0 else -1)] = 1
            cases.append((f'one_old_stone:{side}', scenes))
        scenes = pair()
        scenes[0].tiles[cell(-4, 2)] = 1
        scenes[1].tiles[cell(-4, 3)] = 1
        cases.append(('no_old_dirt', scenes))
        scenes = deepcopy(scenes)
        scenes[0].tiles[cell(-2, -1)] = 4
        scenes[1].tiles[cell(-2, 0)] = 4
        cases.append(('collinear_dirt', scenes))
        scenes = pair()
        for x, y, kind in ((-5, -2, 3), (4, 1, 3), (-4, 2, 4)):
            scenes[1].tiles[cell(x, y)] = kind
        cases.append(('zero_and_unit_both_match', scenes))
        scenes = pair()
        scenes[1].tiles[cell(-5, -1)] = 0
        scenes[1].tiles[cell(8, 1)] = 3
        cases.append(('new_stone_cannot_replace_old', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, lib.test082_geometry(C.byref(scenes[0]),
                                                            C.byref(scenes[1]), 0, 9))
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            scenes = pair()
            scenes[1].tiles[cell(8, 1)] = 3
            self.assertEqual(1, lib.test082_geometry(C.byref(scenes[0]),
                                                    C.byref(scenes[1]), 0, 9))

    def test_raw_and_both_independent_phase_require_finite_same_unit_and_original_gap(self):
        for profile, lib in self.libraries.items():
            scenes = pair()
            for label, score, gap, other, expected in (
                    # At score .6 the decimal sum .6+.08 rounds so its
                    # actual double difference is below .08. Test the first
                    # representable qualifying difference without a tolerance.
                    ('first_float_above_gap', .6,
                     math.nextafter(.6 + .08, math.inf) - .6, 0, 1),
                    ('rounded_below_gap', .6, .08, 0, 0),
                    ('below_gap', .6, .079999, 0, 0),
                    ('high_scope_edge', .45, .2, 0, 0),
                    ('above_scope_edge', .450001, .2, 0, 1),
                    ('nan_best', math.nan, .2, 0, 0),
                    ('positive_inf_best', math.inf, .2, 0, 0),
                    ('negative_inf_best', -math.inf, .2, 0, 0),
                    ('inf_runnerup', .6, math.inf, 0, 0),
                    ('nan_elsewhere', .6, .2, 1, 0),
                    ('negative_inf_elsewhere', .6, .2, 2, 0),
                    ('unavailable_other_raw', .6, .2, 3, 1)):
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(expected, self.proof(lib, scenes, score=score,
                                                         gap=gap, other=other)[0])
            for mode in (1, 2):
                scores = (C.c_double * 5)()
                with self.subTest(profile=profile, isolated_phase=mode):
                    self.assertEqual(0, lib.test082_phase_isolation(C.byref(scenes[0]),
                        C.byref(scenes[1]), mode, scores))
                    if mode == 1:
                        self.assertTrue(math.isinf(scores[0]))
                        self.assertEqual(0, scores[4])
                    else:
                        self.assertTrue(math.isfinite(scores[0]) and math.isfinite(scores[2]))
                        self.assertTrue(math.isinf(scores[1]) and math.isinf(scores[3]))
                        # The old band helper accepts unavailable competitors;
                        # the new branch additionally requires a finite runner-up.
                        self.assertEqual(1, scores[4])

    def test_blur_actual_dependencies_fixed52_support95_bands_and_all73_15pp(self):
        for profile, lib in self.libraries.items():
            scenes = pair()
            self.assertEqual(1, lib.test082_kernel(C.byref(scenes[0]),
                                                  C.byref(scenes[1]), 70, 35, 0, 9))
            for oy in range(-2, 3):
                for ox in range(-2, 3):
                    if abs(ox) == 2 and abs(oy) == 2:
                        continue
                    for side in (0, 1):
                        changed = deepcopy(scenes)
                        gx = (4 * (70 + ox) - 34) // 36 - 11
                        gy = (4 * (35 + oy + 9 * side) - 9) // 36 - 5
                        changed[side].tiles[cell(gx, gy)] = 0
                        with self.subTest(profile=profile, dependency=(side, ox, oy)):
                            self.assertEqual(0, lib.test082_kernel(C.byref(changed[0]),
                                C.byref(changed[1]), 70, 35, 0, 9))
            for x, y in ((40, 35), (110, 50), (110, 81)):
                self.assertEqual(0, lib.test082_kernel(C.byref(scenes[0]),
                                                      C.byref(scenes[1]), x, y, 0, 9))
            for values, expected in (((300, 15, 100, 300, 60), 1),
                                     ((299, 0, 100, 300, 60), 0),
                                     ((300, 16, 100, 300, 60), 0),
                                     ((300, 15, 99, 300, 60), 0),
                                     ((300, 15, 201, 300, 60), 0),
                                     ((300, 15, 100, 300, 59), 0),
                                     ((300, 15, 100, 299, 0), 1)):
                with self.subTest(profile=profile, numeric=values):
                    self.assertEqual(expected, lib.test082_numeric(*values))

    def test_known_primary_and_legacy_results_zero_tween_reverse_and_two_cells_are_preserved(self):
        for profile, lib in self.libraries.items():
            for known in range(1, 8):
                with self.subTest(profile=profile, known=known):
                    self.assertEqual((known, 0, 0), self.proof(lib, pair(), initial=known))
            for direction, (dx, dy) in DIRS.items():
                for pixels, expected in ((0, (2, 0, 0)), (8, (7, 0, 0)),
                                         (9, (1, dx, dy)), (18, (6, 2 * dx, 2 * dy)),
                                         (-9, (6, -dx, -dy))):
                    with self.subTest(profile=profile, direction=direction, old_pixels=pixels):
                        self.assertEqual(expected, self.motion(lib,
                            procedural_pair(direction, pixels=pixels, overlay=False), direction))
                for shift in ((0, 0), (18 * dx, 18 * dy), (9 * dx, 9 * dy),
                              (-8 * dx, -8 * dy)):
                    with self.subTest(profile=profile, direction=direction, wrong_shift=shift):
                        self.assertEqual((0, 0, 0), self.proof(lib, pair(direction),
                                                            direction=direction, shift=shift))
            eight, nine = pair(pixels=8), pair(pixels=9)
            eight[1].signature[:] = bytes((a + b) // 2 for a, b in
                                           zip(eight[1].signature, nine[1].signature))
            self.assertNotEqual(1, self.motion(lib, eight)[0])

    def test_public_unique_corner_uses_blur_quality_and_separate_sharp_discrimination(self):
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                scenes = corner_pair()
                scores, flags = (C.c_double * 6)(), (C.c_int * 14)()
                lib.test082_corner_stats(C.byref(scenes[0]), C.byref(scenes[1]), scores, flags)
                self.assertGreater(scores[0], .45)
                self.assertGreaterEqual(scores[1], .08)
                self.assertEqual((1, 0), tuple(flags[:2]))
                self.assertEqual((0, 9), tuple(flags[12:14]))
                self.assertGreaterEqual(flags[2], 300)
                self.assertLessEqual(20 * flags[3], flags[2])
                self.assertGreaterEqual(min(flags[4:6]), 100)
                self.assertEqual(0, flags[6])  # The unchanged075 blur lead fails.
                self.assertGreaterEqual(flags[7], 300)
                self.assertLessEqual(4 * flags[8], flags[7])
                self.assertGreaterEqual(min(flags[9:11]), 100)
                self.assertEqual(1, flags[11])
                self.assertTrue(all(math.isfinite(value) for value in scores))
                for band in range(2):
                    self.assertGreaterEqual(scores[3 + 2 * band] - scores[2 + 2 * band], .08)
                self.assertEqual((1, 0, -1), self.motion(lib, scenes))

    def test_corner_planes_keep_scope_quality_phase_and_all73_discrimination_separate(self):
        for profile, lib in self.libraries.items():
            scenes = corner_pair()
            for mode in range(10):
                flags = (C.c_int * 12)()
                with self.subTest(profile=profile, component=mode):
                    self.assertEqual(1 if mode == 0 else 0,
                        lib.test082_corner_proof(C.byref(scenes[0]), C.byref(scenes[1]), mode, flags))
                    if mode == 1:
                        self.assertLess(flags[0], 300)
                        self.assertGreaterEqual(flags[4], 300)
                        self.assertLessEqual(4 * flags[5], flags[4])
                        self.assertEqual(1, flags[8])
                    elif mode in (2, 3):
                        self.assertGreaterEqual(flags[0], 300)
                        self.assertLessEqual(20 * flags[1], flags[0])
                        self.assertGreaterEqual(min(flags[2:4]), 100)
                        self.assertGreaterEqual(flags[4], 300)
                        if mode == 2:
                            self.assertGreater(4 * flags[5], flags[4])
                        else:
                            self.assertLessEqual(4 * flags[5], flags[4])
                            self.assertGreaterEqual(min(flags[6:8]), 100)
                            self.assertEqual(0, flags[8])
                    elif mode == 4:
                        self.assertEqual(0, flags[9])
                    elif mode == 5:
                        self.assertEqual((1, 0, 1), tuple(flags[9:12]))
            for values, expected in (
                    ((300, 15, 100, 300, 75, 100, 300, 120), 1),
                    ((300, 16, 100, 300, 15, 100, 300, 120), 0),
                    ((300, 15, 100, 300, 76, 100, 300, 120), 0),
                    ((299, 0, 100, 300, 75, 100, 300, 120), 0),
                    ((300, 15, 100, 299, 0, 100, 300, 120), 0),
                    ((300, 15, 99, 300, 75, 100, 300, 120), 0),
                    ((300, 15, 100, 300, 75, 99, 300, 120), 0),
                    ((300, 15, 100, 300, 75, 100, 300, 119), 0)):
                with self.subTest(profile=profile, separate_numeric=values):
                    self.assertEqual(expected, lib.test082_corner_numeric(*values))
            for side in (0, 1):
                for field, value in (('state', 1), ('goods', 1), ('goods', 2), ('gold_state', 2)):
                    changed = corner_pair()
                    setattr(changed[side], field, value)
                    flags = (C.c_int * 12)()
                    with self.subTest(profile=profile, scope=(side, field, value)):
                        self.assertEqual(0, lib.test082_corner_proof(C.byref(changed[0]),
                            C.byref(changed[1]), 0, flags))
                for kind in (2, 6):
                    changed = corner_pair()
                    changed[side].tiles[cell(8, 3)] = kind
                    flags = (C.c_int * 12)()
                    self.assertEqual(0, lib.test082_corner_proof(C.byref(changed[0]),
                        C.byref(changed[1]), 0, flags))
                changed = corner_pair()
                changed[side].protected_cells[cell(8, 3)] = 1
                flags = (C.c_int * 12)()
                self.assertEqual(0, lib.test082_corner_proof(C.byref(changed[0]),
                    C.byref(changed[1]), 0, flags))
            points = [(4, 2), (3, 2), (4, 1)]
            points += [(4 - i, 3) for i in range(3)] + [(5, 2 - i) for i in range(3)]
            for point in points:
                changed = corner_pair()
                changed[1].tiles[cell(*point)] = 0
                flags = (C.c_int * 12)()
                with self.subTest(profile=profile, lost_corner=point):
                    self.assertEqual(0, lib.test082_corner_proof(C.byref(changed[0]),
                        C.byref(changed[1]), 0, flags))
            for pixels in (0, 8, 18, -9):
                with self.subTest(profile=profile, nonunit_pixels=pixels):
                    self.assertNotEqual(1, self.motion(lib, corner_pair(pixels=pixels))[0])
            eight, nine = corner_pair(pixels=8), corner_pair(pixels=9)
            eight[1].signature[:] = bytes((a + b) // 2 for a, b in
                                           zip(eight[1].signature, nine[1].signature))
            self.assertNotEqual(1, self.motion(lib, eight)[0])


if __name__ == '__main__':
    unittest.main()
