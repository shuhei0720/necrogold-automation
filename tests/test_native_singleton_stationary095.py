"""TEST095 private zero-only evidence for a previously observed singleton STONE.

Procedural surfaces establish no camera displacement under lighting noise.
No phone pixels, Scene dump, future frame or accepted input is reproduced.
The Controller owns the additional unsent/stationary-wait/UNKNOWN-only gate.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_stationary_texture085 import stationary_pair, cell, shifted_signature

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
DIRT = ((-5,-3),(-4,-3),(-3,-3),(2,-3),(3,-3),(4,-3),
        (-5,3),(-4,3),(-3,3),(2,3),(3,3),(4,3))


def singleton_pair(noise=17, geometry=None, points=17):
    surface = stationary_pair(points=points, noise=noise)
    if geometry is None:
        pair = surface
        for scene in pair:
            scene.tiles[cell(4,1)] = 1
    else:
        pair = [Scene.from_buffer_copy(bytes(scene)) for scene in geometry]
        for scene, pixels in zip(pair, surface):
            scene.signature[:] = pixels.signature
    return pair


SHIM = r'''
static void test095_singleton_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
int test095_singleton_public(const NG2Scene*a,const NG2Scene*b,int d){
#if TEST095_SINGLETON_PRESENT
    return ng2_clear_singleton_stationary_zero(a,b,d);
#else
    (void)a;(void)b;(void)d;return 0;
#endif
}
int test095_singleton_geometry(const NG2Scene*a,const NG2Scene*b,int d){
#if TEST095_SINGLETON_PRESENT
    return clear_singleton_zero_scene(a,b,d);
#else
    (void)a;(void)b;(void)d;return 0;
#endif
}
int test095_singleton_translation(const NG2Scene*a,const NG2Scene*b,int x,int y){
#if TEST095_SINGLETON_PRESENT
    return clear_singleton_translation(a,b,x,y);
#else
    (void)a;(void)b;(void)x;(void)y;return 0;
#endif
}
int test095_singleton_numeric(const NG2Scene*a,const NG2Scene*b,int d,int mode){
    View v[2];Candidate c[73];test095_singleton_candidates(a,b,v,c);
#if TEST095_SINGLETON_PRESENT
    ClearSingletonZeroEvidence e;int i;
    if(!clear_singleton_zero_scene(a,b,d)||!clear_singleton_zero_evidence(a,b,v,c,&e))return 0;
    if(mode==1)c[0].score=NAN;
    if(mode==2)c[72].score=INFINITY;
    if(mode==3)c[72].score=-INFINITY;
    if(mode==4)c[0].score=.45;
    if(mode==5)c[0].score=.449999;
    if(mode==6)c[1].score=c[0].score+.079;
    if(mode==7)c[1].score=c[0].score;
    if(mode==8){c[0].sx=9;c[0].sy=0;}
    if(mode==9)c[72].score=NAN;
    if(mode==20)e.blur_zero=.45;
    if(mode==21)e.blur_zero=.450001;
    if(mode==22)e.blur_other[71]=e.blur_zero;
    if(mode==23)e.blur_other[71]=e.blur_zero-.001;
    if(mode==24)e.blur_other[71]=INFINITY;
    if(mode==25)e.blur_other[71]=NAN;
    if(mode==26)e.blur_other[71]=-INFINITY;
    if(mode==27)e.blur_zero=INFINITY;
    if(mode==28)e.blur_zero=NAN;
    if(mode>=30){
        e.world_support=300;e.world_bad=15;e.world_regions[0]=e.world_regions[1]=100;
        e.axis_support=400;e.axis_bad=100;e.axis_regions[0]=e.axis_regions[1]=100;
        for(i=0;i<72;++i){e.axis_other_support[i]=400;e.axis_other_bad[i]=160;}
    }
    if(mode==31)e.world_bad=16;
    if(mode==32)e.world_support=299;
    if(mode==33)e.world_regions[1]=99;
    if(mode==34)e.world_regions[0]=99;
    if(mode==41)e.axis_other_bad[71]=159;
    if(mode==42)e.axis_bad=101;
    if(mode==43)e.axis_support=299;
    if(mode==44)e.axis_regions[0]=99;
    if(mode==45)e.axis_regions[1]=99;
    return clear_singleton_zero_raw(c)&&clear_singleton_zero_numeric(&e);
#else
    (void)d;(void)mode;return 0;
#endif
}
'''


class NativeSingletonStationary095Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='singleton-static095-')
        directory = Path(cls.temp.name)
        for source in CORE.glob('NG2*'):
            if source.suffix in ('.c','.h'):
                shutil.copyfile(source,directory/source.name)
        present = 'int ng2_clear_singleton_stationary_zero(' in (directory/'NG2Navigation.c').read_text()
        shim = directory/'proof.c'
        shim.write_text('#define TEST095_SINGLETON_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        cls.libraries = {}
        for name,flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            target = directory/(name+'.so')
            subprocess.run(['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic','-fPIC','-shared',str(shim),'-lm','-o',str(target)],check=True,capture_output=True)
            cls.libraries[name]=lib=C.CDLL(str(target));ptr=C.POINTER(Scene)
            for symbol in ('test095_singleton_public','test095_singleton_geometry'):
                getattr(lib,symbol).argtypes=[ptr,ptr,C.c_int];getattr(lib,symbol).restype=C.c_int
            lib.test095_singleton_numeric.argtypes=[ptr,ptr,C.c_int,C.c_int];lib.test095_singleton_numeric.restype=C.c_int
            lib.test095_singleton_translation.argtypes=[ptr,ptr,C.c_int,C.c_int];lib.test095_singleton_translation.restype=C.c_int
            lib.ng2_motion.argtypes=[ptr,ptr,C.c_int,C.POINTER(Motion)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def proof(self,lib,pair,direction=3,mode=None,geometry=False):
        before=tuple(bytes(s) for s in pair)
        args=[C.byref(pair[0]),C.byref(pair[1]),direction]
        symbol='test095_singleton_geometry' if geometry else 'test095_singleton_public'
        if mode is not None:
            symbol='test095_singleton_numeric';args.append(mode)
        result=getattr(lib,symbol)(*args)
        self.assertEqual(before,tuple(bytes(s) for s in pair),'a zero proof cannot mutate input Scenes')
        return result

    def test_single_old_stone_fixed_surface_adds_only_readonly_zero_evidence(self):
        for profile,lib in self.libraries.items():
            for noise in (16,17):
                with self.subTest(profile=profile,noise=noise):
                    pair=singleton_pair(noise=noise);out=Motion()
                    self.assertEqual(1,lib.ng2_motion(C.byref(pair[0]),C.byref(pair[1]),3,C.byref(out)))
                    self.assertEqual(0,out.kind,'the old global Motion still reports UNKNOWN')
                    self.assertEqual(1,self.proof(lib,pair),'an independently fixed singleton terrain view needs only a zero proof')
                    self.assertEqual(1,self.proof(lib,pair,mode=0))

    def test_exact_old_singleton_is_preserved_and_new_stone_cannot_replace_it(self):
        cases=[]
        for side in (0,1):
            pair=singleton_pair();pair[side].tiles[cell(-5,-2)]=1;cases.append(pair)
        pair=singleton_pair();pair[1].tiles[cell(-5,-2)]=1;pair[1].tiles[cell(-4,-2)]=3;cases.append(pair)
        pair=singleton_pair();pair[0].tiles[cell(4,1)]=3;cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair))
            pair=singleton_pair();pair[1].tiles[cell(5,1)]=3
            self.assertEqual(1,self.proof(lib,pair),'an independently revealed far STONE is not an old anchor')

    def test_common_noncollinear_dirt_support_and_unique_nine_placements_are_required(self):
        cases=[]
        pair=singleton_pair()
        for p in DIRT[8:]:pair[1].tiles[cell(*p)]=1
        cases.append(pair)
        pair=deepcopy(pair)
        for p in ((6,-3),(7,-3),(8,-3)):pair[1].tiles[cell(*p)]=4
        cases.append(pair)
        pair=singleton_pair()
        for scene in pair:
            for i,k in enumerate(scene.tiles):
                if k in (3,4):scene.tiles[i]=1
            scene.tiles[cell(-5,2)]=3
            for x in range(-4,5):scene.tiles[cell(x,2)]=4
        cases.append(pair)
        pair=singleton_pair();pair[1].tiles[cell(-4,-2)]=3
        for x,y in DIRT:pair[1].tiles[cell(x+1,y)]=4
        cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair,geometry=True))
            pair=singleton_pair()
            for p in DIRT[9:]:pair[1].tiles[cell(*p)]=1
            self.assertEqual(1,self.proof(lib,pair,geometry=True),'nine matching 2D DIRTs meet the finite geometry bound')
            pair=singleton_pair();pair[1].tiles[cell(*DIRT[0])]=1;pair[1].tiles[cell(7,-3)]=4
            self.assertEqual(1,self.proof(lib,pair,geometry=True),'new DIRT is not substituted for the lost source location')

    def test_full_source_and_projected_hud_sample_rois_are_excluded(self):
        cases=[]
        pair=singleton_pair()
        for scene in pair:scene.tiles[cell(-5,-2)]=1;scene.tiles[cell(-1,3)]=3
        cases.append(pair)
        pair=singleton_pair()
        for p in DIRT[9:]:
            for scene in pair:scene.tiles[cell(*p)]=1
        for scene in pair:scene.tiles[cell(*DIRT[0])]=1;scene.tiles[cell(-1,3)]=4
        cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair,geometry=True),'center-outside/ROI-overlap is still HUD')
            # Shifted placements must apply the same full-ROI exclusion to
            # projected anchors and DIRTs, even with nine exact matches.
            points=DIRT[:6]+((-5,2),(2,2),(-1,2))
            pair=[Scene(abi_version=1,struct_size=C.sizeof(Scene),state=2,gold_state=1) for _ in range(2)]
            for scene in pair:scene.tiles[:]=[1]*230
            pair[0].tiles[cell(-5,-2)]=3;pair[1].tiles[cell(-5,-1)]=3
            for x,y in points:pair[0].tiles[cell(x,y)]=4;pair[1].tiles[cell(x,y+1)]=4
            args=(C.byref(pair[0]),C.byref(pair[1]),0,1)
            self.assertEqual(0,lib.test095_singleton_translation(*args),'projected DIRT ROI touching the heart cannot be the ninth anchor')
            pair[0].tiles[cell(-1,2)]=1;pair[1].tiles[cell(-1,3)]=1
            pair[0].tiles[cell(3,2)]=4;pair[1].tiles[cell(3,3)]=4
            self.assertEqual(1,lib.test095_singleton_translation(*args),'nine visible projected matching DIRTs remain valid')
            pair[0].tiles[cell(-5,-2)]=1;pair[1].tiles[cell(-5,-1)]=1
            pair[0].tiles[cell(-1,2)]=3;pair[1].tiles[cell(-1,3)]=3
            self.assertEqual(0,lib.test095_singleton_translation(*args),'projected STONE full ROI touching the heart is unavailable')

    def test_near_floor_all_protection_gold_goods_invalid_scenes_and_direction_reject(self):
        cases=[]
        for side in (0,1):
            for field,value in (('state',0),('state',1),('gold_state',0),('gold_state',2),('goods',1),('goods',2),('abi_version',2),('struct_size',C.sizeof(Scene)-1)):
                pair=singleton_pair();setattr(pair[side],field,value);cases.append(pair)
            for p,k in (((0,0),4),((0,-1),0),((1,-2),4),((7,1),2),((7,1),5),((7,1),6),((7,1),7)):
                pair=singleton_pair();pair[side].tiles[cell(*p)]=k;cases.append(pair)
            pair=singleton_pair();pair[side].protected_cells[cell(7,1)]=1;cases.append(pair)
        for lib in self.libraries.values():
            for pair in cases:self.assertEqual(0,self.proof(lib,pair))
            for direction in (0,5):self.assertEqual(0,self.proof(lib,singleton_pair(),direction))

    def test_all_raw_scores_are_finite_zero_ranked_and_inside_fallback_domain(self):
        for lib in self.libraries.values():
            for mode in range(1,10):self.assertEqual(0,self.proof(lib,singleton_pair(),mode=mode))

    def test_blur_zero_absolute_bound_and_all_seventy_two_finite_competitors(self):
        for lib in self.libraries.values():
            self.assertEqual(1,self.proof(lib,singleton_pair(),mode=20))
            for mode in range(21,29):self.assertEqual(0,self.proof(lib,singleton_pair(),mode=mode))

    def test_world_axis_strength_regions_and_last_competitor_lead_boundaries(self):
        for lib in self.libraries.values():
            self.assertEqual(1,self.proof(lib,singleton_pair(),mode=30))
            for mode in (31,32,33,34,41,42,43,44,45):self.assertEqual(0,self.proof(lib,singleton_pair(),mode=mode))
            for direction in (1,2,3,4):
                pair=procedural_pair(direction,amount=1,pixels=9,overlay=False)
                self.assertEqual(0,self.proof(lib,pair,direction),'a nonzero translated surface is not this zero-only qualification')
