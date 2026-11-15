"""TEST103: fixed-world, definitely-unsent plural terrain zero qualification.

The procedural world is fixed. A smooth illumination field changes phase by
one signature pixel while independent photometric noise changes its samples.
No phone pixels or Scene dumps supply fixtures or expected values. Caller
ownership, prefix, deadlines and new-ticket authority belong to Controller.
"""
import ast
import ctypes as C
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRT = ((-5,-3),(-4,-3),(-3,-3),(2,-3),(3,-3),(4,-3),
        (-5,3),(-4,3),(-3,3),(2,3),(3,3),(4,3))


def cell(x, y):
    return (y + 5) * 23 + x + 11


def plural_phase_pair(direction=2):
    """Same discrete world, changing lighting phase; direction is illumination."""
    if direction not in (1, 2, 3, 4):
        raise ValueError('cardinal illumination phase required')
    rng = random.Random(85085)
    world = [rng.randrange(14, 35) for _ in range(W * H)]
    for lower, upper in ((23, 34), (68, 80)):
        for _ in range(17):
            y, x = rng.randrange(lower, upper), rng.randrange(44, 174)
            world[y * W + x] = rng.randrange(160, 200)
    pair = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                  gold_state=1) for _ in range(2)]
    for scene in pair:
        scene.tiles[:] = [1] * 230
        for x, y in ((-5, -2), (4, 1)):
            scene.tiles[cell(x, y)] = 3
        for x, y in DIRT:
            scene.tiles[cell(x, y)] = 4
    noise = random.Random(85086)
    axis = (lambda i: i % W) if direction in (1, 2) else (lambda i: i // W)
    sign = -1 if direction in (1, 3) else 1
    pair[0].signature[:] = bytes(max(7, min(255, round(value +
        36 * (1 + math.sin(2 * math.pi * axis(i) / 48)))))
        for i, value in enumerate(world))
    for i, value in enumerate(world):
        lit = round(value + 36 * (1 + math.sin(2 * math.pi * (axis(i) - sign) / 48)))
        pair[1].signature[i] = max(7, min(255, lit + noise.randrange(-17, 18)))
    return pair


SHIM = r'''
static void test103_plural_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
int test103_plural_public(const NG2Scene*a,const NG2Scene*b,int d){
#if TEST103_PLURAL_PRESENT
    return ng2_clear_plural_stationary_zero(a,b,d);
#else
    (void)a;(void)b;(void)d;return 0;
#endif
}
int test103_plural_scene(const NG2Scene*a,const NG2Scene*b,int d){
#if TEST103_PLURAL_PRESENT
    return clear_plural_zero_scene(a,b,d);
#else
    (void)a;(void)b;(void)d;return 0;
#endif
}
void test103_plural_stats(const NG2Scene*a,const NG2Scene*b,double out[9]){
    View v[2];Candidate c[73];ClearSingletonZeroEvidence e;int i;
    test103_plural_candidates(a,b,v,c);
    out[0]=clear_singleton_zero_raw(c);out[1]=0;out[2]=out[3]=0;
    out[4]=clear_singleton_zero_evidence(a,b,v,c,&e);out[5]=e.blur_zero;
    for(i=1;i<73;++i)if(isfinite(e.blur_other[i-1])&&e.blur_other[i-1]<=e.blur_zero){
        ++out[1];out[2]=c[i].sx;out[3]=c[i].sy;
    }
    out[6]=clear_singleton_zero_numeric(&e);out[7]=c[0].score;out[8]=c[1].score-c[0].score;
}
int test103_plural_numeric(int mode,int unit){
#if TEST103_PLURAL_PRESENT
    Candidate c[73];ClearSingletonZeroEvidence e;int i,n=1,amount,d;
    memset(&e,0,sizeof(e));memset(c,0,sizeof(c));c[0].score=.6;
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];c[n].score=.8+n*.001;++n;
    }
    e.blur_zero=.3;e.world_support=400;e.world_bad=20;e.world_regions[0]=e.world_regions[1]=100;
    e.axis_support=400;e.axis_bad=100;e.axis_regions[0]=e.axis_regions[1]=100;
    for(i=0;i<72;++i){e.blur_other[i]=.6;e.axis_other_support[i]=400;e.axis_other_bad[i]=160;}
    if(mode==1){c[72].sx=c[unit].sx;c[72].sy=c[unit].sy;c[unit].sx=18;c[unit].sy=0;unit=72;}
    e.blur_other[unit-1]=.25;
    if(mode==2)e.blur_other[unit-1]=e.blur_zero;
    if(mode==3)e.blur_other[unit-1]=.6;
    if(mode==4)e.blur_other[(unit%4)]=e.blur_zero;
    if(mode==5){c[unit].sx=2;c[unit].sy=0;}
    if(mode==6){c[unit].sx=1;c[unit].sy=1;}
    if(mode==7)e.axis_other_support[unit-1]=299;
    if(mode==8){e.axis_other_support[unit-1]=300;e.axis_other_bad[unit-1]=120;}
    if(mode==9)e.axis_other_bad[unit-1]=159;
    if(mode==10)e.blur_zero=.45;
    if(mode==11)e.blur_zero=.450001;
    if(mode==12)e.blur_zero=NAN;
    if(mode==13)e.blur_zero=INFINITY;
    if(mode==14)e.blur_other[71]=NAN;
    if(mode==15)e.blur_other[71]=INFINITY;
    if(mode==16)e.blur_other[71]=-INFINITY;
    if(mode==17)e.blur_other[unit-1]=NAN;
    if(mode==18)e.blur_other[71]=e.blur_zero-.01;
    if(mode==20)c[0].score=.45;
    if(mode==21)c[1].score=c[0].score+.079;
    if(mode==22)c[72].score=NAN;
    if(mode==23)c[72].score=INFINITY;
    if(mode==24){c[0].sx=1;c[0].sy=0;}
    if(mode==25)c[0].score=-INFINITY;
    if(mode==30)e.world_support=399;
    if(mode==31)e.world_regions[0]=99;
    if(mode==32)e.world_regions[1]=99;
    if(mode==33)e.world_bad=21;
    if(mode==34){e.world_support=299;e.world_bad=0;}
    if(mode==40)e.axis_support=399;
    if(mode==41)e.axis_regions[0]=99;
    if(mode==42)e.axis_regions[1]=99;
    if(mode==43)e.axis_bad=101;
    if(mode==44){e.axis_support=299;e.axis_bad=0;}
    if(mode==45)e.axis_other_bad[71]=159;
    return clear_singleton_zero_raw(c)&&clear_plural_zero_numeric(c,&e);
#else
    (void)mode;(void)unit;return 0;
#endif
}
'''


def freeze(directory, shim):
    """Freeze the complete named compiler and local Python helper closure first."""
    files = [directory / 'NG2Navigation.c', directory / 'NG2Core.h', shim]
    pending, seen = [Path(__file__).resolve()], set()
    while pending:
        source = pending.pop()
        if source in seen:
            continue
        seen.add(source)
        for node in ast.walk(ast.parse(source.read_text())):
            candidates = []
            if isinstance(node, ast.ImportFrom) and node.module:
                base = ROOT / node.module.replace('.', '/')
                candidates = [base.with_suffix('.py'), *(base/(alias.name+'.py') for alias in node.names)]
            elif isinstance(node, ast.Import):
                candidates = [(ROOT/alias.name.replace('.', '/')).with_suffix('.py') for alias in node.names]
            pending.extend(other for other in candidates if other.is_file())
    files.extend(sorted(seen))
    compiler = Path(shutil.which('cc')).resolve()
    files.append(compiler)
    data = {'compiler': str(compiler), 'files': {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                                              for f in files}}
    (directory / 'before.json').write_text(json.dumps(data, indent=2) + '\n')
    return data


class NativePluralStationary103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        external = os.environ.get('NECRO_TEST103_NAV_EVIDENCE')
        cls.temp = None if external else tempfile.TemporaryDirectory(prefix='plural-static103-')
        directory = Path(external if external else cls.temp.name)
        directory.mkdir(parents=True, exist_ok=True)
        for name in ('NG2Navigation.c', 'NG2Core.h'):
            shutil.copyfile(CORE/name, directory/name)
        present = 'int ng2_clear_plural_stationary_zero(' in (directory/'NG2Navigation.c').read_text()
        shim = directory/'proof.c'
        shim.write_text('#define TEST103_PLURAL_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        frozen = freeze(directory, shim)
        cls.libraries, builds = {}, []
        for name, flags in (('o0', ['-O0']), ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest() == h for f, h in frozen['files'].items())
            target = directory/(name+'.so')
            command = [frozen['compiler'], '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-fPIC', '-shared', str(shim), '-lm', '-o', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            builds.append({'command': command, 'returncode': result.returncode, 'stderr': result.stderr})
            (directory/'compile.json').write_text(json.dumps(builds, indent=2)+'\n')
            result.check_returncode()
            cls.libraries[name] = lib = C.CDLL(str(target))
            ptr = C.POINTER(Scene)
            for symbol in ('test103_plural_public', 'test103_plural_scene', 'ng2_clear_singleton_stationary_zero'):
                getattr(lib, symbol).argtypes = [ptr, ptr, C.c_int]
                getattr(lib, symbol).restype = C.c_int
            lib.test103_plural_numeric.argtypes = [C.c_int, C.c_int]
            lib.test103_plural_numeric.restype = C.c_int
            lib.test103_plural_stats.argtypes = [ptr, ptr, C.POINTER(C.c_double)]
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]

    @classmethod
    def tearDownClass(cls):
        if cls.temp:
            cls.temp.cleanup()

    def proof(self, lib, pair, direction=3, geometry=False):
        original = tuple(bytes(s) for s in pair)
        fn = lib.test103_plural_scene if geometry else lib.test103_plural_public
        result = fn(C.byref(pair[0]), C.byref(pair[1]), direction)
        self.assertEqual(original, tuple(bytes(s) for s in pair), 'zero evidence cannot mutate scenes')
        return result

    def test_fixed_world_unit_lighting_phase_adds_only_zero_qualification(self):
        for name, lib in self.libraries.items():
            pair = plural_phase_pair()
            scores = (C.c_double*9)()
            lib.test103_plural_stats(C.byref(pair[0]), C.byref(pair[1]), scores)
            self.assertEqual((1,1,1,0,1), tuple(scores[:5]), name)
            self.assertLessEqual(scores[5], .45)
            self.assertEqual(0, scores[6], 'old all72 strict blur proof rejects this lighting phase')
            motion = Motion()
            self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), 3, C.byref(motion)))
            self.assertEqual((0,0,0), (motion.kind,motion.dx,motion.dy), 'global Motion stays UNKNOWN')
            self.assertEqual(0, lib.ng2_clear_singleton_stationary_zero(C.byref(pair[0]), C.byref(pair[1]), 3))
            self.assertEqual(1, lib.ng2_motion(C.byref(pair[1]), C.byref(pair[1]), 3, C.byref(motion)))
            self.assertEqual((2,0,0), (motion.kind,motion.dx,motion.dy), 'same frame retains its old strict zero')
            for direction in (1,2,3,4):
                self.assertEqual(1, self.proof(lib, pair, direction), name)

    def test_exact_old_plural_stones_and_old_dirt_cannot_be_replaced(self):
        cases=[]
        pair=plural_phase_pair()
        for s in pair:s.tiles[cell(4,1)]=1
        cases.append(pair)
        pair=plural_phase_pair();pair[1].tiles[cell(-5,-2)]=1;cases.append(pair)
        pair=deepcopy(pair);pair[1].tiles[cell(-4,-2)]=3;cases.append(pair)
        pair=plural_phase_pair();pair[0].tiles[cell(5,1)]=3;cases.append(pair)
        pair=plural_phase_pair()
        for p in DIRT[8:]:pair[1].tiles[cell(*p)]=1
        for p in ((6,-3),(7,-3),(8,-3)):pair[1].tiles[cell(*p)]=4
        cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair,geometry=True))
            pair=plural_phase_pair();pair[1].tiles[cell(5,1)]=3
            self.assertEqual(1,self.proof(lib,pair,geometry=True),'new stone is allowed but supplies no old anchor')
            pair=plural_phase_pair()
            for p in DIRT[9:]:pair[1].tiles[cell(*p)]=1
            self.assertEqual(1,self.proof(lib,pair,geometry=True),'nine old visible matching DIRTs suffice')

    def test_noncollinear_unique_nine_placements_and_full_hud_rois(self):
        cases=[]
        pair=plural_phase_pair()
        for s in pair:
            s.tiles[:]=[1]*230
            for x in (-5,5):s.tiles[cell(x,2)]=3
            for x in range(-4,5):s.tiles[cell(x,2)]=4
        cases.append(pair)
        pair=plural_phase_pair()
        for x,y in ((-5,-2),(4,1)):pair[1].tiles[cell(x+1,y)]=3
        for x,y in DIRT:pair[1].tiles[cell(x+1,y)]=4
        cases.append(pair)
        pair=plural_phase_pair()
        for s in pair:s.tiles[cell(-1,3)]=3
        cases.append(pair)
        pair=plural_phase_pair()
        for p in DIRT[8:]:
            for s in pair:s.tiles[cell(*p)]=1
        for s in pair:s.tiles[cell(-1,3)]=4
        cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair,geometry=True))

    def test_both_scenes_near_floor_protection_gold_goods_and_invalid_reject(self):
        cases=[]
        for side in (0,1):
            for field,value in (('state',0),('state',1),('gold_state',0),('gold_state',2),('goods',1),('goods',2),('abi_version',2),('struct_size',C.sizeof(Scene)-1)):
                pair=plural_phase_pair();setattr(pair[side],field,value);cases.append(pair)
            for p,k in (((0,0),4),((0,-1),0),((1,-2),4),((7,1),2),((7,1),5),((7,1),6),((7,1),7)):
                pair=plural_phase_pair();pair[side].tiles[cell(*p)]=k;cases.append(pair)
            pair=plural_phase_pair();pair[side].protected_cells[cell(7,1)]=1;cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair,geometry=True))
            for d in (0,5):self.assertEqual(0,self.proof(lib,plural_phase_pair(),d,geometry=True))
            self.assertEqual(0,lib.test103_plural_scene(None,None,3))

    def test_exactly_one_cardinal_unit_phase_and_supported_unit_axis(self):
        for lib in self.libraries.values():
            for unit in (1,2,3,4):
                for mode in (0,1,2,8,10):self.assertEqual(1,lib.test103_plural_numeric(mode,unit),(mode,unit))
                for mode in (3,4,5,6,7,9,18):self.assertEqual(0,lib.test103_plural_numeric(mode,unit),(mode,unit))

    def test_all_blur_finite_absolute_bound_and_all_raw_competitors(self):
        for lib in self.libraries.values():
            for mode in (*range(11,18),*range(20,26)):
                self.assertEqual(0,lib.test103_plural_numeric(mode,1),mode)

    def test_world_axis_strength_regions_and_last_lead_boundaries(self):
        for lib in self.libraries.values():
            for mode in (*range(30,35),*range(40,46)):
                self.assertEqual(0,lib.test103_plural_numeric(mode,1),mode)

    def test_real_translated_procedural_world_never_qualifies_zero(self):
        for lib in self.libraries.values():
            for direction in (1,2,3,4):
                pair=procedural_pair(direction,amount=1,pixels=9,overlay=False)
                self.assertEqual(0,self.proof(lib,pair,direction))


if __name__ == '__main__':
    unittest.main()
