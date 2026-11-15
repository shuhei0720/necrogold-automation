"""Observed left mouths and independently supported dark side passages.

TEST105 actual2/62 and actual3/72 are calibration labels. The sparse maps
express current observed geometry, never future game images or hidden floor.
"""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
CENTRE = ((-1,-1),(0,-1),(-1,0),(0,0),(-2,0))
OBSERVED_WALLS = ((-4,-3),(-3,-3),(-2,-3),(-3,-1),(-3,0),(-3,1),(-3,2))
SHADOW_WALLS = ((-3,-3),(-3,-2),(-5,1),(-5,2),(-4,2),(-3,2),(-3,3))
OBSERVED_DARK = ((-4,-2),(-2,-2))
SHADOW_DARK = ((-3,-1),(-3,0),(-3,1),(-4,1))
DIRECTIONS = {1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}


class Scene(C.Structure):
    _fields_ = [('abi_version',C.c_uint32),('struct_size',C.c_uint32)] + [
        (name,C.c_int32) for name in ('state','restart_label','gold_state','gold_peak','goods')] + [
        ('tiles',C.c_uint8*230),('protected_cells',C.c_uint8*230),
        ('signature',C.c_uint8*23296),('fingerprint',C.c_uint8*48),
        ('beat_valid',C.c_int32),('beat_remaining',C.c_double),
        ('beat_spacing',C.c_double),('beat_center',C.c_double)]


class Decision(C.Structure):
    _fields_ = [(name,C.c_int32) for name in ('direction','reason','target_x','target_y','obstacle')]


def at(x,y):
    return (y+5)*23+x+11


def paint(scene,point,kind):
    scene.tiles[at(*point)] = kind


def terrain(shadow=False,kind=DIRT):
    scene = Scene(abi_version=1,struct_size=C.sizeof(Scene),state=2,gold_state=1)
    for point in CENTRE+((-2,1) if shadow else (-2,-1),):
        paint(scene,point,FLOOR)
    for point in SHADOW_WALLS if shadow else OBSERVED_WALLS:
        paint(scene,point,kind)
    if not shadow:
        paint(scene,(-3,-2),FLOOR)
    return scene


def transform(source,operation):
    scene = Scene.from_buffer_copy(bytes(source))
    scene.tiles[:] = bytes(230);scene.protected_cells[:] = bytes(230)
    for y in range(-5,5):
        for x in range(-11,12):
            xx,yy = operation(x,y)
            if -11<=xx<=11 and -5<=yy<=4:
                paint(scene,(xx,yy),source.tiles[at(x,y)])
                scene.protected_cells[at(xx,yy)] = source.protected_cells[at(x,y)]
    return scene


SHIM = r'''
int test106_left_observation(const NG2Scene*s,int shadow){
#if TEST106_LEFT_PRESENT
    Path route[CELLS];if(!passage_scene(s))return 0;path_search(s,0,1,route);
    return shadow ? passage_split_left_vantage(s,route) : passage_observed_left_vantage(s,route);
#else
    (void)s;(void)shadow;return 0;
#endif
}
'''


class NativeLeftObservation106Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='left-observation106-')
        cls.addClassCleanup(cls.temp.cleanup);directory = Path(cls.temp.name)
        for name in ('NG2Navigation.c','NG2Core.h'):
            (directory/name).write_bytes((CORE/name).read_bytes())
        source = (directory/'NG2Navigation.c').read_text()
        present = 'static int passage_observed_left_vantage(' in source
        (directory/'proof.c').write_text('#define TEST106_LEFT_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        cls.libraries = {}
        for profile,flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            target = directory/(profile+'.so')
            subprocess.run(['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                '-fPIC','-shared',str(directory/'proof.c'),'-lm','-o',str(target)],check=True)
            cls.libraries[profile] = lib = C.CDLL(str(target))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)];lib.ng2_passage_candidates.restype = C.c_uint32
            lib.test106_left_observation.argtypes = [C.POINTER(Scene),C.c_int];lib.test106_left_observation.restype = C.c_int
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene),C.c_int32,C.c_int32,C.c_int32,C.c_int32,C.POINTER(Decision)]
            lib.ng2_choose_passage.restype = C.c_int

    def mask(self,lib,scene):
        before = bytes(scene);value = lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before,bytes(scene),'a candidate cannot relabel floor or unknown cells')
        return value

    def guard(self,lib,scene,shadow):
        before = bytes(scene);value = lib.test106_left_observation(C.byref(scene),int(shadow))
        self.assertEqual(before,bytes(scene));return value

    def test_observed_left_floor_mouth_with_independent_long_wall_adds_only_bit5(self):
        for lib in self.libraries.values():
            for kind in (DIRT,STONE):
                scene = terrain(kind=kind)
                self.assertEqual(32,self.mask(lib,scene),'a supported left floor mouth merits its known three-step view')
                self.assertEqual(1,self.guard(lib,scene,False))

    def test_dark_left_gap_with_pillar_and_both_boundary_ends_adds_only_bit8(self):
        for lib in self.libraries.values():
            for kind in (DIRT,STONE):
                scene = terrain(shadow=True,kind=kind)
                self.assertEqual(256,self.mask(lib,scene),'a supported dark side passage merits its known three-step view')
                self.assertEqual(1,self.guard(lib,scene,True))

    def test_each_positive_wall_floor_and_dark_gap_is_independent(self):
        for lib in self.libraries.values():
            for shadow,walls,dark in ((False,OBSERVED_WALLS,OBSERVED_DARK),(True,SHADOW_WALLS,SHADOW_DARK)):
                for point in walls:
                    for kind in (UNKNOWN,FLOOR,GOLD,DOOR,ITEM):
                        scene=terrain(shadow);paint(scene,point,kind)
                        self.assertEqual(0,self.guard(lib,scene,shadow),(shadow,point,kind))
                for point in CENTRE+((-2,1) if shadow else (-2,-1),):
                    for kind in (UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM):
                        scene=terrain(shadow);paint(scene,point,kind)
                        self.assertEqual(0,self.guard(lib,scene,shadow),(shadow,point,kind))
                for point in dark:
                    for kind in (FLOOR,GOLD,STONE,DIRT,DOOR,ITEM):
                        scene=terrain(shadow);paint(scene,point,kind)
                        self.assertEqual(0,self.guard(lib,scene,shadow),(shadow,point,kind))
                if not shadow:
                    for kind in (UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM):
                        scene=terrain();paint(scene,(-3,-2),kind)
                        self.assertEqual(0,self.guard(lib,scene,False))

    def test_fixed_world_chooser_uses_only_three_observed_floors_then_holds(self):
        for lib in self.libraries.values():
            for shadow,mouth,vantage in ((False,(-3,-2),(-2,-1)),(True,(-3,1),(-2,1))):
                original=terrain(shadow);x=y=0
                for remaining in (3,2,1):
                    scene=transform(original,lambda a,b:(a-x,b-y));before=bytes(scene);choice=Decision()
                    self.assertEqual(remaining,lib.ng2_choose_passage(C.byref(scene),x,y,*mouth,C.byref(choice)))
                    self.assertEqual((10,FLOOR),(choice.reason,choice.obstacle))
                    self.assertEqual((vantage[0]-x,vantage[1]-y),(choice.target_x,choice.target_y))
                    dx,dy=DIRECTIONS[choice.direction];self.assertEqual(FLOOR,scene.tiles[at(dx,dy)])
                    self.assertEqual(before,bytes(scene));x+=dx;y+=dy
                self.assertEqual(vantage,(x,y))
                scene=transform(original,lambda a,b:(a-x,b-y));choice=Decision()
                self.assertEqual(0,lib.ng2_choose_passage(C.byref(scene),x,y,*mouth,C.byref(choice)))
                self.assertEqual(UNKNOWN,original.tiles[at(mouth[0]-1,mouth[1])])

    def test_state_gold_goods_protection_and_other_sides_cannot_gain_authority(self):
        for lib in self.libraries.values():
            for shadow in (False,True):
                for field,value in (('abi_version',2),('struct_size',C.sizeof(Scene)-1),('state',0),('state',1),
                    ('gold_state',0),('gold_state',2),('gold_state',3),('goods',1),('goods',2)):
                    scene=terrain(shadow);setattr(scene,field,value);self.assertEqual(0,self.mask(lib,scene))
                for point in ((0,0),(-2,0),(-2,-1),(-2,1),(-3,-2),(-3,1),(8,1)):
                    scene=terrain(shadow);scene.protected_cells[at(*point)]=1;self.assertEqual(0,self.mask(lib,scene))
                for name,op in (('horizontal',lambda x,y:(-x,y)),('vertical',lambda x,y:(x,-y)),
                    ('transpose',lambda x,y:(y,x)),('shift',lambda x,y:(x+1,y))):
                    scene=transform(terrain(shadow),op)
                    # The stronger observed witness transposes into an
                    # already valid old104 upper mouth. Preserve that bit.
                    expected=1 if not shadow and name=='transpose' else 0
                    self.assertEqual(expected,self.mask(lib,scene))
                    self.assertEqual(0,self.guard(lib,scene,shadow))
                for kind in (GOLD,ITEM,7):
                    scene=terrain(shadow);paint(scene,(8,1),kind);self.assertEqual(0,self.mask(lib,scene))
                scene=terrain(shadow);scene.protected_cells[at(8,1)]=2;self.assertEqual(0,self.mask(lib,scene))
            self.assertEqual(0,lib.ng2_passage_candidates(None))


if __name__=='__main__':
    unittest.main()
