"""TEST101: independently supported phase bands after the first gold reveal.

The public LEFT field is procedural and coherent. Four-direction private
cases isolate computed phase/raw/blur boundaries; those cases are not public
camera captures or an end-to-end displacement replay. TEST083 retains public
four-direction regression coverage. No private device image is embedded.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_blocked067 import Entrance
from tests.test_native_first_gold083 import pair as original_pair
from tests.test_native_passage_motion082 import cell, DIRS

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def pair():
    """One coherent LEFT unit with a short independently observed left strip."""
    scenes = original_pair(1)
    for y in range(104):
        for x in range(114):
            if 70 <= x < 96 and 20 <= y < 85:
                continue
            scenes[0].signature[y * 224 + x] = 0
            xx = x + 9
            if xx < 224:
                scenes[1].signature[y * 224 + xx] = 0
    return scenes


SHIM = r'''
static void test101_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test101_previous(const NG2Scene*a,const NG2Scene*b,int d,NG2Motion*out){
    View v[2];Candidate c[73];test101_candidates(a,b,v,c);
    evaluate_motion(a,b,d,v,c,out);
    gate_detail_motion(a,b,d,v,c,out);
    opening_detail_motion(a,b,d,v,c,out);
    passage_detail_motion(a,b,d,v,c,out);
    opening_gradient_motion(a,b,d,c,out);
    static_floor_gradient_motion(a,b,d,c,out);
    corner_blur_motion(a,b,d,v,c,out);
    closed_gate_axis_motion(a,b,d,c,out);
    revealed_gate_axis_motion(a,b,d,c,out);
    sparse_gate_motion(a,b,d,v,c,out);
    side_gate_motion(a,b,d,v,c,out);
    terrain_blur_motion(a,b,d,v,c,out);
    corner_gradient_blur_motion(a,b,d,v,c,out);
    first_gold_terrain_blur_motion(a,b,d,v,c,out);
    stationary_terrain_motion(a,b,d,v,c,out);
    singleton_gold_terrain_blur_motion(a,b,d,v,c,out);
    hud_occluded_terrain_blur_motion(a,b,d,v,c,out);
    terrain_axis_unit_motion(a,b,d,v,c,out);
    opening_blur_quality_motion(a,b,d,v,c,out);
    stationary_gold_axis_motion(a,b,d,v,c,out);
    revealed_singleton_motion(a,b,d,v,c,out);
    preserved_singleton_sparse_motion(a,b,d,v,c,out);
}
static void test101_stats_inner(const NG2Scene*a,const NG2Scene*b,int d,
    const View v[2],const Candidate c[73],double scores[8],int flags[11]){
    int i,band,su,ba,regions[2];NG2Motion old={0};
    memset(flags,0,11*sizeof(*flags));scores[0]=c[0].score;scores[1]=c[1].score-c[0].score;
    for(i=0;i<73;++i)flags[0]+=isfinite(c[i].score)!=0;
    for(band=0;band<2;++band){
        double best=phase_band_intensity(v,v+1,c[0].sx,c[0].sy,band),gap=INFINITY;
        scores[2+3*band]=best;scores[3+3*band]=phase_band_intensity(v,v+1,0,0,band);
        if(!isfinite(phase_band_intensity(v,v+1,c[1].sx,c[1].sy,band)))flags[1]|=1<<band;
        for(i=1;i<73;++i){double value=phase_band_intensity(v,v+1,c[i].sx,c[i].sy,band);
            if(isfinite(value)&&value-best<gap)gap=value-best;}
        scores[4+3*band]=gap;
        for(i=1;i<=4;++i)if(isfinite(phase_band_intensity(v,v+1,9*ddx[i],9*ddy[i],band)))flags[2]|=1<<(i-1);
    }
    flags[3]=unique_terrain_translation(a,b,c[0].sx,c[0].sy);
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,&su,&ba,regions);
    flags[4]=su;flags[5]=ba;flags[6]=regions[0];flags[7]=regions[1];flags[8]=1;
    for(i=1;i<73;++i){int count,bad;
        world_blur_texture(a,b,v,c[i].sx,c[i].sy,&count,&bad,NULL);
        if(!texture_lead(su,ba,count,bad))flags[8]=0;}
    first_gold_terrain_blur_motion(a,b,d,v,c,&old);flags[9]=old.kind;flags[10]=TEST101_PRESENT;
}
void test101_stats(const NG2Scene*a,const NG2Scene*b,int d,double scores[8],int flags[11]){
    View v[2];Candidate c[73];test101_candidates(a,b,v,c);
    test101_stats_inner(a,b,d,v,c,scores,flags);
}
/* Only the public pair uses coherent Scene/View/raw candidates. These
 * controls isolate real computed planes and numeric proof boundaries. */
void test101_private(const NG2Scene*a,const NG2Scene*b,int d,int mode,
    double score,double gap,int other,int sx,int sy,NG2Motion*out,double scores[8],int flags[11]){
    View v[2];Candidate c[73];int i,x,y,dx=ddx[d],dy=ddy[d],runner=d==NG2_RIGHT?18:-18;
    test101_candidates(a,b,v,c);
    if(mode!=10)for(y=0;y<H;++y)for(x=0;x<114;++x){
        int xx=x-9*dx,yy=y-9*dy;
        int kept=x>=70&&x<(mode==3?79:91)&&y>=20&&y<85;
        if(kept)continue;
        v[0].normalized[y*W+x]=0;
        if(xx>=0&&xx<W&&yy>=0&&yy<H)v[1].normalized[yy*W+xx]=0;
    }
    if(mode==2){memset(v[0].normalized,0,N);memset(v[1].normalized,0,N);}
    if(mode==4)for(y=0;y<H;++y)for(x=114;x<W;++x){
        int xx=x-9*dx,yy=y-9*dy;
        if(x>=150&&x<171&&y>=20&&y<85)continue;
        v[0].normalized[y*W+x]=0;
        if(xx>=0&&xx<W&&yy>=0&&yy<H)v[1].normalized[yy*W+xx]=0;
    }
    if(mode==5)for(y=0;y<H;++y)for(x=0;x<W;++x){
        unsigned char value=(unsigned char)(20+(37*(x%9)+53*y)%201);
        if(v[0].normalized[y*W+x])v[0].normalized[y*W+x]=value;
        if(v[1].normalized[y*W+x])v[1].normalized[y*W+x]=value;
    }
    if(mode==6)memset(v[1].blur,0,N);
    if(mode==7)for(i=0;i<N;++i)v[1].blur[i]=(unsigned char)(255-v[1].blur[i]);
    if(mode==8)for(y=0;y<54;++y)for(x=0;x<W;++x)v[0].blur[y*W+x]=v[1].blur[y*W+x]=0;
    if(mode==9)for(y=0;y<H;++y)for(x=0;x<W;++x){
        int phase=x%9;unsigned char value=(unsigned char)(20+24*(phase<5?phase:9-phase));
        v[0].blur[y*W+x]=v[1].blur[y*W+x]=value;
    }
    for(i=0;i<73;++i)if(c[i].sx==sx&&c[i].sy==sy){Candidate z=c[0];c[0]=c[i];c[i]=z;break;}
    if(mode!=10)for(i=1;i<73;++i)if(c[i].sx==runner&&!c[i].sy){Candidate z=c[1];c[1]=c[i];c[i]=z;break;}
    c[0].score=score;for(i=1;i<73;++i)c[i].score=score+gap;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    if(other==3)c[72].score=INFINITY;
    if(other==4)c[72].score=-.001;
    test101_stats_inner(a,b,d,v,c,scores,flags);
#if TEST101_PRESENT
    first_gold_supported_phase_motion(a,b,d,v,c,out);
#else
    (void)out;
#endif
}
'''


class NativeFirstGold101Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test101-first-gold-')
        directory = Path(cls.temp.name)
        source = Path(os.environ.get('NECRO_TEST101_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        shutil.copyfile(source, directory / 'NG2Navigation.c')
        shutil.copyfile(CORE / 'NG2Core.h', directory / 'NG2Core.h')
        selected = directory / 'NG2Navigation.c'
        present = 'static void first_gold_supported_phase_motion(' in selected.read_text()
        shim = directory / 'proof.c'
        shim.write_text(f'#define TEST101_PRESENT {int(present)}\n#include "{selected}"\n' + SHIM)
        cls.libraries, commands = {}, {}
        for profile, flags in (('o0', ['-O0']), ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            output = directory / (profile + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-fPIC', '-shared', str(shim), '-lm', '-o', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            commands[profile] = command
            lib = C.CDLL(str(output)); cls.libraries[profile] = lib
            ptr, ints, doubles = C.POINTER(Scene), C.POINTER(C.c_int), C.POINTER(C.c_double)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int, C.POINTER(Entrance)]
            lib.test101_previous.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.test101_stats.argtypes = [ptr, ptr, C.c_int, doubles, ints]
            lib.test101_private.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_double, C.c_double,
                                           C.c_int, C.c_int, C.c_int, C.POINTER(Motion), doubles, ints]
        identity = os.environ.get('NECRO_TEST101_NAV_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps(dict(selected_navigation=str(source),
                navigation_sha256=hashlib.sha256(selected.read_bytes()).hexdigest(),
                core_sha256=hashlib.sha256((directory / 'NG2Core.h').read_bytes()).hexdigest(),
                test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                shim_sha256=hashlib.sha256(shim.read_bytes()).hexdigest(), commands=commands,
                scope=__doc__), indent=2)+'\n')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def motion(self, lib, scenes, direction=1):
        out = Motion()
        self.assertEqual(1, lib.ng2_motion(C.byref(scenes[0]), C.byref(scenes[1]), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def private(self, lib, scenes, direction=1, mode=1, score=.6, gap=.2,
                other=0, shift=None, known=0):
        dx, dy = DIRS[direction]
        sx, sy = shift if shift is not None else (-9*dx, -9*dy)
        out, scores, flags = Motion(known, 0, 0), (C.c_double*8)(), (C.c_int*11)()
        lib.test101_private(C.byref(scenes[0]), C.byref(scenes[1]), direction, mode,
                            score, gap, other, sx, sy, C.byref(out), scores, flags)
        return (out.kind, out.dx, out.dy), list(scores), list(flags)

    def qualifying(self, scores, flags):
        self.assertGreater(scores[0], .45); self.assertGreaterEqual(scores[1], .08)
        self.assertEqual(73, flags[0]); self.assertNotEqual(0, flags[1])
        self.assertEqual(15, flags[2]); self.assertEqual(1, flags[3])
        for best, zero, gap in (scores[2:5], scores[5:8]):
            self.assertTrue(math.isfinite(best)); self.assertTrue(math.isfinite(zero))
            self.assertGreaterEqual(gap, .08)
        self.assertGreaterEqual(flags[4], 300); self.assertLessEqual(20*flags[5], flags[4])
        self.assertGreaterEqual(min(flags[6:8]), 100); self.assertEqual(1, flags[8])
        self.assertEqual(0, flags[9])

    def test_public_left_first_reveal_uses_supported_finite_phase_proof(self):
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                scenes = pair(); scores, flags = (C.c_double*8)(), (C.c_int*11)()
                lib.test101_stats(C.byref(scenes[0]), C.byref(scenes[1]), 1, scores, flags)
                self.qualifying(list(scores), list(flags))
                old = Motion(); lib.test101_previous(C.byref(scenes[0]), C.byref(scenes[1]), 1, C.byref(old))
                self.assertEqual((0, 0, 0), (old.kind, old.dx, old.dy))
                self.assertEqual((1, -1, 0), self.motion(lib, scenes),
                                 'one unsupported band of the raw runner must not hide independently proved first-gold motion')
                entrance = Entrance()
                self.assertEqual(0, lib.ng2_entered_gate(C.byref(scenes[0]), C.byref(scenes[1]), 1, 0, 0, 1, C.byref(entrance)))

    def test_private_four_direction_computed_planes_preserve_unit_and_known_output_scope(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    scenes = original_pair(direction)
                    result, scores, flags = self.private(lib, scenes, direction)
                    self.qualifying(scores, flags)
                    self.assertEqual((1, dx, dy), result)
                    for known in range(1, 8):
                        self.assertEqual((known, 0, 0), self.private(lib, scenes, direction, known=known)[0])

    def test_first_reveal_safe_floor_unknown_source_and_no_merchandise_are_required(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('goods', (1, 2)),
                                  ('gold_state', (0, 2, 3) if side == 0 else (0, 1, 3))):
                for value in values:
                    scenes = original_pair(1); setattr(scenes[side], field, value)
                    cases.append((f'{side}:{field}:{value}', scenes))
            for kind in (0, 3, 4, 5):
                scenes = original_pair(1); scenes[side].tiles[cell(0, 0)] = kind
                cases.append((f'{side}:origin:{kind}', scenes))
            for field, value in (('tiles', 6), ('protected_cells', 1)):
                scenes = original_pair(1); getattr(scenes[side], field)[cell(8, 3)] = value
                cases.append((f'{side}:{field}', scenes))
        for kind in (0, 3, 4, 5):
            scenes = original_pair(1); scenes[0].tiles[cell(-1, 0)] = kind
            cases.append((f'next:{kind}', scenes))
        for kind in (1, 2, 3, 4, 5, 6):
            scenes = original_pair(1); scenes[0].tiles[cell(-3, 3)] = kind
            cases.append((f'known_gold_source:{kind}', scenes))
        scenes = original_pair(1); scenes[1].tiles[cell(8, 3)] = 2; cases.append(('two_gold', scenes))
        scenes = original_pair(1); scenes[0].tiles[cell(8, 3)] = 2; cases.append(('old_gold', scenes))
        scenes = original_pair(1); scenes[1].tiles[cell(-2, 3)] = 0; cases.append(('no_gold', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.private(lib, scenes)[0])

    def test_all_old_stones_and_unique_noncollinear_terrain_remain_required(self):
        cases = []
        for point in ((-4, -2), (5, 1)):
            for kind in (0, 1, 4):
                scenes = original_pair(1); scenes[1].tiles[cell(*point)] = kind
                cases.append((f'lost_stone:{point}:{kind}', scenes))
        scenes = original_pair(1); scenes[0].tiles[cell(-5, -2)] = 1; cases.append(('one_anchor', scenes))
        scenes = original_pair(1); scenes[0].tiles[cell(-4, 2)] = 1; cases.append(('no_noncollinear_dirt', scenes))
        scenes = original_pair(1)
        for x, y, kind in ((-5, -2, 3), (4, 1, 3), (-4, 2, 4)):
            scenes[1].tiles[cell(x, y)] = kind
        cases.append(('ambiguous_zero_and_unit', scenes))
        for profile, lib in self.libraries.items():
            for label, scenes in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.private(lib, scenes)[0])

    def test_raw_numeric_nonfinite_reverse_and_nonunit_boundaries_do_not_gain_credit(self):
        for profile, lib in self.libraries.items():
            scenes = original_pair(1)
            for label, score, gap, other in (('low_scope', .45, .2, 0),
                    ('low_gap', .6, .079999, 0), ('rounded_gap', .6, .08, 0),
                    ('nan', math.nan, .2, 0), ('inf', math.inf, .2, 0),
                    ('nan_other', .6, .2, 1), ('negative_inf', .6, .2, 2),
                    ('unsupported_raw', .6, .2, 3), ('negative_raw', .6, .2, 4)):
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.private(lib, scenes, score=score, gap=gap, other=other)[0])
            for shift in ((0, 0), (8, 0), (-9, 0), (18, 0), (0, 9)):
                with self.subTest(profile=profile, shift=shift):
                    self.assertEqual((0, 0, 0), self.private(lib, scenes, shift=shift)[0])

    def test_finite_zero_unit_coverage_and_real_competitor_margins_are_independent(self):
        for profile, lib in self.libraries.items():
            for mode in (2, 3, 4, 5):
                with self.subTest(profile=profile, component=mode):
                    result, scores, flags = self.private(lib, original_pair(1), mode=mode)
                    self.assertEqual((0, 0, 0), result)
                    if mode == 2:
                        self.assertFalse(math.isfinite(scores[2]))
                    elif mode == 3:
                        self.assertTrue(math.isfinite(scores[2])); self.assertFalse(math.isfinite(scores[3]))
                    elif mode == 4:
                        self.assertTrue(all(math.isfinite(scores[i]) for i in (2, 3, 5, 6)))
                        self.assertNotEqual(15, flags[2])
                    else:
                        self.assertTrue(all(math.isfinite(scores[i]) for i in (2, 3, 5, 6)))
                        self.assertLess(scores[4], .08)

    def test_world_absolute_strength_regions_and_competing_displacements_still_veto(self):
        for profile, lib in self.libraries.items():
            for mode in (6, 7, 8, 9):
                with self.subTest(profile=profile, component=mode):
                    result, scores, flags = self.private(lib, original_pair(1), mode=mode)
                    self.assertEqual((0, 0, 0), result)
                    self.assertTrue(all(math.isfinite(scores[i]) for i in (2, 3, 5, 6)))
                    if mode == 6:
                        self.assertLess(flags[4], 300)
                    elif mode == 7:
                        self.assertGreater(20*flags[5], flags[4])
                    elif mode == 8:
                        self.assertLess(min(flags[6:8]), 100)
                    else:
                        self.assertGreaterEqual(flags[4], 300)
                        self.assertLessEqual(20*flags[5], flags[4])
                        self.assertGreaterEqual(min(flags[6:8]), 100)
                        self.assertEqual(0, flags[8])

    def test_existing_motion_results_and_old_finite_runner_path_remain_separate(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual((1, dx, dy), self.motion(lib, original_pair(direction), direction))
                    result, scores, flags = self.private(lib, original_pair(direction), direction, mode=10)
                    self.assertEqual((0, 0, 0), result)
                    self.assertEqual((73, 0, 15, 1), tuple(flags[:4]))
                    self.assertEqual(1, flags[9])
                    self.assertTrue(all(math.isfinite(scores[i]) for i in (2, 3, 5, 6)))
                    for pixels, expected in ((0, (2, 0, 0)), (8, (7, 0, 0)),
                                             (-9, (6, -dx, -dy)), (18, (6, 2*dx, 2*dy))):
                        scenes = procedural_pair(direction, pixels=pixels, overlay=False)
                        self.assertEqual(expected, self.motion(lib, scenes, direction))


if __name__ == '__main__':
    unittest.main()
