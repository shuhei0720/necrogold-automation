"""TEST083: observe one past floor unit that first reveals one gold cell.

Procedural pixel fields carry a strict nine-pixel translation independent of
native output. They are not phone captures, live-state replays or acceptance.
"""
import ctypes as C
from copy import deepcopy
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_blocked067 import Entrance
from tests.test_native_passage_motion082 import pair as base_pair, cell, DIRS

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def pair(direction=3, pixels=9):
    before, after = base_pair(direction, pixels=pixels)
    gx, gy = {1: (-2, 3), 2: (2, -3), 3: (-3, -2), 4: (3, 2)}[direction]
    dx, dy = DIRS[direction]
    before.tiles[cell(gx + dx, gy + dy)] = 0
    after.tiles[cell(gx, gy)] = 2
    after.gold_state = 2
    return [before, after]


SHIM = r'''
static void test083_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]) {
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d) {
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test083_previous(const NG2Scene*a,const NG2Scene*b,int direction,int out[39]) {
    View v[2];Candidate c[73];NG2Motion m={0};int i=0;test083_candidates(a,b,v,c);
    #define TEST083_SAVE() do {out[i++]=m.kind;out[i++]=m.dx;out[i++]=m.dy;}while(0)
    evaluate_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    gate_detail_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    opening_detail_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    passage_detail_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    opening_gradient_motion(a,b,direction,c,&m);TEST083_SAVE();
    static_floor_gradient_motion(a,b,direction,c,&m);TEST083_SAVE();
    corner_blur_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    closed_gate_axis_motion(a,b,direction,c,&m);TEST083_SAVE();
    revealed_gate_axis_motion(a,b,direction,c,&m);TEST083_SAVE();
    sparse_gate_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    side_gate_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    terrain_blur_motion(a,b,direction,v,c,&m);TEST083_SAVE();
    corner_gradient_blur_motion(a,b,direction,v,c,&m);TEST083_SAVE();
}
void test083_stats(const NG2Scene*a,const NG2Scene*b,double scores[6],int flags[8]) {
    View v[2];Candidate c[73];int k,su,ba;test083_candidates(a,b,v,c);
    scores[0]=c[0].score;scores[1]=c[1].score-c[0].score;
    flags[0]=c[0].sx;flags[1]=c[0].sy;
    flags[2]=unique_terrain_translation(a,b,c[0].sx,c[0].sy);
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,flags+3,flags+4,flags+5);
    flags[7]=1;
    for(k=1;k<73;++k) {
        world_blur_texture(a,b,v,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(flags[3],flags[4],su,ba))flags[7]=0;
    }
    for(k=0;k<2;++k) {
        scores[2+2*k]=phase_band_intensity(v,v+1,c[0].sx,c[0].sy,k);
        scores[3+2*k]=phase_band_intensity(v,v+1,c[1].sx,c[1].sy,k);
    }
}
void test083_proof(const NG2Scene*a,const NG2Scene*b,int direction,double score,double gap,
                   int sx,int sy,int other,NG2Motion*out) {
    View v[2];Candidate c[73];int k;test083_candidates(a,b,v,c);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy) {
        Candidate swap=c[0];c[0]=c[k];c[k]=swap;break;
    }
    c[0].score=score;c[1].score=score+gap;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    if(other==3)c[72].score=INFINITY;
#if TEST083_PRESENT
    first_gold_terrain_blur_motion(a,b,direction,v,c,out);
#else
    (void)direction;(void)out;
#endif
}
int test083_geometry(const NG2Scene*a,const NG2Scene*b,int sx,int sy) {
    return unique_terrain_translation(a,b,sx,sy);
}
int test083_numeric(int support,int bad,int upper,int count,int opposite) {
    return texture_strength(support,bad,95)&&upper>=100&&support-upper>=100
        &&texture_lead(support,bad,count,opposite);
}
int test083_components(const NG2Scene*a,const NG2Scene*b,int mode,int flags[9]) {
    View v[2];Candidate c[73];NG2Motion out={0};unsigned int state=83083;
    int k,x,y,su,ba;test083_candidates(a,b,v,c);
    /* Deliberately isolate computed phase/blur arrays at this private test
     * boundary. Only the public positive has coherent raw Scene/View data. */
    if(mode==1||mode==2) {
        memset(v[0].normalized,0,N);memset(v[1].normalized,0,N);
        if(mode==2) {
            for(k=1;k<73;++k)if(c[k].sx==18&&!c[k].sy) {
                Candidate swap=c[1];c[1]=c[k];c[k]=swap;break;
            }
            c[0].score=.6;c[1].score=.8;
            for(y=24;y<76;++y)for(x=70;x<170;++x) {
                unsigned char value;if(!((x>=70&&x<80)||(x>=160&&x<170)))continue;
                state=1664525u*state+1013904223u;value=(unsigned char)(20+state%201);
                v[0].normalized[y*W+x]=value;v[1].normalized[(y+9)*W+x]=value;
            }
        }
    }
    if(mode==3)memset(v[1].blur,0,N);
    if(mode==4)for(k=0;k<N;++k)v[1].blur[k]=(unsigned char)(255-v[1].blur[k]);
    if(mode==5) {
        memset(v[1].blur,0,N);
        for(y=0;y<H;++y)for(x=0;x<W;++x) {
            int phase=y%16;unsigned char value=(unsigned char)(20+24*(phase<8?phase:16-phase));
            v[0].blur[y*W+x]=value;if(y+8<H)v[1].blur[(y+8)*W+x]=value;
        }
    }
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,flags,flags+1,flags+2);flags[4]=1;
    for(k=1;k<73;++k) {
        world_blur_texture(a,b,v,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(flags[0],flags[1],su,ba))flags[4]=0;
    }
    flags[5]=isfinite(phase_band_intensity(v,v+1,c[0].sx,c[0].sy,0))
        &&isfinite(phase_band_intensity(v,v+1,c[0].sx,c[0].sy,1));
    flags[6]=isfinite(phase_band_intensity(v,v+1,c[1].sx,c[1].sy,0))
        &&isfinite(phase_band_intensity(v,v+1,c[1].sx,c[1].sy,1));
    flags[7]=independent_phase(v,c);flags[8]=unique_terrain_translation(a,b,c[0].sx,c[0].sy);
#if TEST083_PRESENT
    first_gold_terrain_blur_motion(a,b,NG2_UP,v,c,&out);
#endif
    return out.kind;
}
'''


class NativeFirstGold083Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test083-first-gold-')
        source = Path(os.environ.get('NECRO_TEST083_BASELINE_NAVIGATION',
                                     CORE / 'NG2Navigation.c'))
        present = 'static void first_gold_terrain_blur_motion(' in source.read_text()
        shim = Path(cls.temp.name) / 'proof.c'
        shim.write_text(f'#define TEST083_PRESENT {int(present)}\n'
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
            lib.test083_previous.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_int)]
            lib.test083_stats.argtypes = [ptr, ptr, C.POINTER(C.c_double), C.POINTER(C.c_int)]
            lib.test083_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                                          C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test083_geometry.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test083_numeric.argtypes = [C.c_int] * 5
            lib.test083_components.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_int)]
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def motion(self, lib, scenes, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(scenes[0]), C.byref(scenes[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, scenes, direction=3, score=.6, gap=.2, shift=None,
              other=0, initial=0):
        dx, dy = DIRS[direction]
        sx, sy = shift if shift is not None else (-9 * dx, -9 * dy)
        out = Motion(initial, 0, 0)
        lib.test083_proof(C.byref(scenes[0]), C.byref(scenes[1]), direction,
                          score, gap, sx, sy, other, C.byref(out))
        return out.kind, out.dx, out.dy

    def test_public_four_direction_first_gold_unit_keeps_opening_and_entry_uncredited(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    scenes = pair(direction)
                    scores, flags, previous = (C.c_double * 6)(), (C.c_int * 8)(), (C.c_int * 39)()
                    lib.test083_previous(C.byref(scenes[0]), C.byref(scenes[1]), direction, previous)
                    self.assertEqual([0] * 39, list(previous))
                    lib.test083_stats(C.byref(scenes[0]), C.byref(scenes[1]), scores, flags)
                    self.assertGreater(scores[0], .45)
                    self.assertGreaterEqual(scores[1], .08)
                    self.assertEqual((-9 * dx, -9 * dy), tuple(flags[:2]))
                    self.assertEqual(1, flags[2])
                    self.assertGreaterEqual(flags[3], 300)
                    self.assertLessEqual(20 * flags[4], flags[3])
                    self.assertGreaterEqual(min(flags[5:7]), 100)
                    self.assertEqual(1, flags[7])
                    self.assertTrue(all(math.isfinite(value) for value in scores))
                    for band in range(2):
                        self.assertGreaterEqual(scores[3 + 2 * band] - scores[2 + 2 * band], .08)
                    self.assertEqual((1, dx, dy), self.motion(lib, scenes, direction))
                    entered = Entrance(99, 99, 99, 99)
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(scenes[0]),
                        C.byref(scenes[1]), direction, 0, 0, 1, C.byref(entered)))
                    self.assertEqual((0, 0, 0, 0), tuple(getattr(entered, k)
                        for k, _ in entered._fields_))

    def test_first_gold_requires_clear_single_candidate_unknown_projection_and_safe_floor(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('goods', (1, 2)),
                                  ('gold_state', (0, 2, 3) if side == 0 else (0, 1, 3))):
                for value in values:
                    scenes = pair()
                    setattr(scenes[side], field, value)
                    cases.append((f'{side}:{field}:{value}', scenes))
            scenes = pair()
            scenes[side].tiles[cell(8, 3)] = 6
            cases.append((f'{side}:item', scenes))
            scenes = pair()
            scenes[side].protected_cells[cell(8, 3)] = 1
            cases.append((f'{side}:protection', scenes))
            for point in ((0, 0), (0, -1)) if side == 0 else ((0, 0),):
                for kind in (0, 3, 4, 5):
                    scenes = pair()
                    scenes[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', scenes))
        for kind in (1, 2, 3, 4, 5, 6):
            scenes = pair()
            scenes[0].tiles[cell(-3, -3)] = kind
            cases.append((f'projection_known:{kind}', scenes))
        scenes = pair()
        scenes[0].tiles[cell(8, 3)] = 2
        cases.append(('old_gold', scenes))
        scenes = pair()
        scenes[1].tiles[cell(8, 3)] = 2
        cases.append(('two_new_gold', scenes))
        scenes = pair()
        scenes[1].tiles[cell(-3, -2)] = 0
        cases.append(('no_new_gold', scenes))
        scenes = deepcopy(scenes)
        scenes[1].tiles[cell(-3, -5)] = 2
        cases.append(('projection_outside_grid', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            for kind in (0, 3, 4, 5):
                scenes = pair()
                scenes[1].tiles[cell(0, -1)] = kind
                with self.subTest(profile=profile, future_next=kind):
                    self.assertEqual((1, 0, -1), self.proof(lib, scenes))

    def test_all_old_stones_noncollinear_dirt_and_unique_nine_remain_required(self):
        cases = []
        for point in ((-5, -1), (4, 2)):
            for kind in (0, 1, 4):
                scenes = pair()
                scenes[1].tiles[cell(*point)] = kind
                cases.append((f'lost_old_stone:{point}:{kind}', scenes))
        for side in (0, 1):
            scenes = pair()
            scenes[side].tiles[cell(-5, -2 if side == 0 else -1)] = 1
            cases.append((f'one_old_stone:{side}', scenes))
        scenes = pair()
        scenes[0].tiles[cell(-4, 2)] = 1
        scenes[1].tiles[cell(-4, 3)] = 1
        cases.append(('missing_old_dirt', scenes))
        scenes = deepcopy(scenes)
        scenes[0].tiles[cell(-2, -1)] = 4
        scenes[1].tiles[cell(-2, 0)] = 4
        cases.append(('collinear_dirt', scenes))
        scenes = pair()
        for x, y, kind in ((-5, -2, 3), (4, 1, 3), (-4, 2, 4)):
            scenes[1].tiles[cell(x, y)] = kind
        cases.append(('zero_and_unit_match', scenes))
        scenes = pair()
        scenes[1].tiles[cell(-5, -1)] = 0
        scenes[1].tiles[cell(8, 1)] = 3
        cases.append(('new_anchor_cannot_replace_old', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual(0, lib.test083_geometry(C.byref(scenes[0]),
                                                            C.byref(scenes[1]), 0, 9))
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            scenes = pair()
            scenes[1].tiles[cell(8, 1)] = 3
            self.assertEqual(1, lib.test083_geometry(C.byref(scenes[0]),
                                                    C.byref(scenes[1]), 0, 9))

    def test_original_raw_finite_phase_and_strong_blur_limits_are_independent(self):
        for profile, lib in self.libraries.items():
            scenes = pair()
            for label, score, gap, other, expected in (
                    ('first_float_above_gap', .6,
                     math.nextafter(.6 + .08, math.inf) - .6, 0, 1),
                    ('rounded_below_gap', .6, .08, 0, 0),
                    ('below_gap', .6, .079999, 0, 0),
                    ('high_scope_edge', .45, .2, 0, 0),
                    ('above_scope_edge', .450001, .2, 0, 1),
                    ('nan_best', math.nan, .2, 0, 0),
                    ('infinite_best', math.inf, .2, 0, 0),
                    ('negative_infinite_best', -math.inf, .2, 0, 0),
                    ('infinite_runnerup', .6, math.inf, 0, 0),
                    ('nan_other', .6, .2, 1, 0),
                    ('negative_infinite_other', .6, .2, 2, 0),
                    ('unavailable_other', .6, .2, 3, 1)):
                with self.subTest(profile=profile, raw=label):
                    self.assertEqual(expected, self.proof(lib, scenes,
                        score=score, gap=gap, other=other)[0])
            for mode in range(6):
                flags = (C.c_int * 9)()
                with self.subTest(profile=profile, component=mode):
                    self.assertEqual(1 if mode == 0 else 0,
                        lib.test083_components(C.byref(scenes[0]), C.byref(scenes[1]), mode, flags))
                    self.assertEqual(1, flags[8])
                    if mode == 1:
                        self.assertEqual(0, flags[5])
                    elif mode == 2:
                        self.assertEqual((1, 0, 1), tuple(flags[5:8]))
                    elif mode == 3:
                        self.assertEqual((1, 1, 1), tuple(flags[5:8]))
                        self.assertLess(flags[0], 300)
                    elif mode == 4:
                        self.assertGreaterEqual(flags[0], 300)
                        self.assertGreater(20 * flags[1], flags[0])
                    elif mode == 5:
                        self.assertGreaterEqual(flags[0], 300)
                        self.assertLessEqual(20 * flags[1], flags[0])
                        self.assertGreaterEqual(min(flags[2:4]), 100)
                        self.assertEqual(0, flags[4])
            for values, expected in (((300, 15, 100, 300, 60), 1),
                                     ((299, 0, 100, 300, 60), 0),
                                     ((300, 16, 100, 300, 60), 0),
                                     ((300, 15, 99, 300, 60), 0),
                                     ((300, 15, 201, 300, 60), 0),
                                     ((300, 15, 100, 300, 59), 0),
                                     ((300, 15, 100, 299, 0), 1)):
                with self.subTest(profile=profile, numeric=values):
                    self.assertEqual(expected, lib.test083_numeric(*values))

    def test_known_outputs_reverse_partial_stationary_and_two_cells_never_gain_unit_credit(self):
        for profile, lib in self.libraries.items():
            for known in range(1, 8):
                self.assertEqual((known, 0, 0), self.proof(lib, pair(), initial=known))
            for direction, (dx, dy) in DIRS.items():
                for pixels, expected in ((0, (2, 0, 0)), (8, (7, 0, 0)),
                                         (9, (1, dx, dy)), (18, (6, 2 * dx, 2 * dy)),
                                         (-9, (6, -dx, -dy))):
                    with self.subTest(profile=profile, direction=direction, old_pixels=pixels):
                        self.assertEqual(expected, self.motion(lib,
                            procedural_pair(direction, pixels=pixels, overlay=False), direction))
                for shift in ((0, 0), (-8 * dx, -8 * dy), (9 * dx, 9 * dy),
                              (-18 * dx, -18 * dy)):
                    with self.subTest(profile=profile, direction=direction, wrong_unit=shift):
                        self.assertEqual((0, 0, 0), self.proof(lib, pair(direction),
                            direction=direction, shift=shift))
                for pixels in (0, 8, -9, 18):
                    with self.subTest(profile=profile, direction=direction, new_nonunit=pixels):
                        self.assertNotEqual(1, self.motion(lib,
                            pair(direction, pixels=pixels), direction)[0])
            eight, nine = pair(pixels=8), pair(pixels=9)
            eight[1].signature[:] = bytes((a + b) // 2 for a, b in
                                           zip(eight[1].signature, nine[1].signature))
            self.assertNotEqual(1, self.motion(lib, eight)[0])


if __name__ == '__main__':
    unittest.main()
