"""TEST108 cap323: a floor mouth between independently observed boundaries.

The sparse fixture records current wall/floor/unknown observations only.
It grants a three-step inside view and never fills the disconnected mouth.
"""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
MOUTH, VANTAGE = (-3,-2), (-2,-1)
WALLS = ((-4,-3),(-3,-3),(-2,-3),(-1,-3),(-3,1),(-3,2),(-3,3))
DARK = ((-4,-2),(-2,-2),(-3,-1),(-3,0))
FLOORS = tuple((x,y) for y in (-1,0) for x in (-2,-1,0)) + ((-1,-2),)
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


def terrain(wall=DIRT):
    scene = Scene(abi_version=1,struct_size=C.sizeof(Scene),state=2,gold_state=1)
    for point in WALLS:
        paint(scene,point,wall)
    for point in FLOORS+(MOUTH,):
        paint(scene,point,FLOOR)
    return scene


def transform(source,operation):
    scene = Scene.from_buffer_copy(bytes(source))
    scene.tiles[:] = bytes(230)
    scene.protected_cells[:] = bytes(230)
    for y in range(-5,5):
        for x in range(-11,12):
            xx,yy = operation(x,y)
            if -11<=xx<=11 and -5<=yy<=4:
                paint(scene,(xx,yy),source.tiles[at(x,y)])
                scene.protected_cells[at(xx,yy)] = source.protected_cells[at(x,y)]
    return scene


SHIM = r'''
int test109_dark_side(const NG2Scene*s){
#if TEST109_DARK_SIDE_PRESENT
    Path route[CELLS];if(!passage_scene(s))return 0;path_search(s,0,1,route);
    return passage_dark_side_mouth_vantage(s,route);
#else
    (void)s;return 0;
#endif
}
'''


class NativeDarkSide109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='dark-side109-')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        for name in ('NG2Navigation.c','NG2Core.h'):
            (directory/name).write_bytes((CORE/name).read_bytes())
        present = 'static int passage_dark_side_mouth_vantage(' in (directory/'NG2Navigation.c').read_text()
        (directory/'proof.c').write_text('#define TEST109_DARK_SIDE_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        cls.libraries = {}
        commands = []
        for profile,flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            target = directory/(profile+'.so')
            command = ['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                '-fPIC','-shared',str(directory/'proof.c'),'-lm','-o',str(target)]
            result = subprocess.run(command,capture_output=True,text=True)
            commands.append({'command':command,'returncode':result.returncode,'stderr':result.stderr})
            result.check_returncode()
            cls.libraries[profile] = lib = C.CDLL(str(target))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)]
            lib.ng2_passage_candidates.restype = C.c_uint32
            lib.test109_dark_side.argtypes = [C.POINTER(Scene)]
            lib.test109_dark_side.restype = C.c_int
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene),C.c_int,C.c_int,C.c_int,C.c_int,C.POINTER(Decision)]
            lib.ng2_choose_passage.restype = C.c_int
        evidence = os.environ.get('NECRO_TEST109_DARK_SIDE_BUILD')
        if evidence:
            output = Path(evidence)
            output.mkdir(parents=True,exist_ok=True)
            for name,lib in cls.libraries.items():
                (output/(name+'.so')).write_bytes(Path(lib._name).read_bytes())
            (output/'build.json').write_text(json.dumps({'commands':commands,'source_sha256':{
                name:hashlib.sha256((CORE/name).read_bytes()).hexdigest()
                for name in ('NG2Navigation.c','NG2Core.h')}},indent=2)+'\n')

    def mask(self,lib,scene):
        before = bytes(scene)
        result = lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before,bytes(scene),'a candidate must preserve every observed and hidden cell')
        return result

    def guard(self,lib,scene):
        before = bytes(scene)
        result = lib.test109_dark_side(C.byref(scene))
        self.assertEqual(before,bytes(scene))
        return result

    def test_observed_mouth_with_roof_and_lower_boundary_adds_only_bit5(self):
        for lib in self.libraries.values():
            for wall in (DIRT,STONE):
                scene = terrain(wall)
                self.assertEqual(32,self.mask(lib,scene),'the supported dark side mouth merits an inside FLOOR view')
                self.assertEqual(1,self.guard(lib,scene))
                self.assertEqual((UNKNOWN,)*len(DARK),tuple(scene.tiles[at(*p)] for p in DARK))

    def test_every_independent_roof_and_lower_wall_is_required(self):
        for lib in self.libraries.values():
            self.assertEqual(1,self.guard(lib,terrain()))
            for point in WALLS:
                for kind in (UNKNOWN,FLOOR,GOLD,DOOR,ITEM):
                    scene = terrain();paint(scene,point,kind)
                    self.assertEqual(0,self.guard(lib,scene),(point,kind))

    def test_mouth_is_observed_floor_and_dark_surroundings_are_not_inferred(self):
        for lib in self.libraries.values():
            self.assertEqual(1,self.guard(lib,terrain()))
            for kind in (UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM):
                scene = terrain();paint(scene,MOUTH,kind)
                self.assertEqual(0,self.guard(lib,scene),kind)
            for point in DARK:
                for kind in (FLOOR,GOLD,STONE,DIRT,DOOR,ITEM):
                    scene = terrain();paint(scene,point,kind)
                    self.assertEqual(0,self.guard(lib,scene),(point,kind))

    def test_inside_observed_floors_and_short_route_are_required(self):
        for lib in self.libraries.values():
            self.assertEqual(1,self.guard(lib,terrain()))
            for point in FLOORS:
                for kind in (UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM):
                    scene = terrain();paint(scene,point,kind)
                    self.assertEqual(0,self.guard(lib,scene),(point,kind))
            scene = terrain();paint(scene,(-1,0),UNKNOWN);paint(scene,(-1,-1),UNKNOWN)
            for point in ((0,1),(-1,1),(-2,1)):
                paint(scene,point,FLOOR)
            self.assertEqual(0,self.guard(lib,scene),'a longer detour cannot gain the three-step witness')

    def test_fixed_world_chooser_uses_three_floors_then_stops_before_unknown(self):
        for lib in self.libraries.values():
            original = terrain();x=y=0
            self.assertEqual(32,self.mask(lib,original))
            for remaining in (3,2,1):
                scene = transform(original,lambda a,b:(a-x,b-y));before = bytes(scene);choice = Decision()
                self.assertEqual(remaining,lib.ng2_choose_passage(C.byref(scene),x,y,*MOUTH,C.byref(choice)))
                self.assertEqual((10,FLOOR),(choice.reason,choice.obstacle))
                self.assertEqual((VANTAGE[0]-x,VANTAGE[1]-y),(choice.target_x,choice.target_y))
                dx,dy = DIRECTIONS[choice.direction]
                self.assertEqual(FLOOR,scene.tiles[at(dx,dy)])
                self.assertEqual(before,bytes(scene));x+=dx;y+=dy
            self.assertEqual(VANTAGE,(x,y))
            scene = transform(original,lambda a,b:(a-x,b-y));choice = Decision()
            self.assertEqual(0,lib.ng2_choose_passage(C.byref(scene),x,y,*MOUTH,C.byref(choice)))
            self.assertEqual((UNKNOWN,)*len(DARK),tuple(original.tiles[at(*p)] for p in DARK))

    def test_wrong_state_goods_gold_items_and_any_protection_do_not_gain_authority(self):
        for lib in self.libraries.values():
            for field,value in (('abi_version',2),('struct_size',C.sizeof(Scene)-1),
                ('state',0),('state',1),('gold_state',0),('gold_state',2),('gold_state',3),('goods',1),('goods',2)):
                scene = terrain();setattr(scene,field,value)
                self.assertEqual(0,self.mask(lib,scene))
            for index in range(230):
                scene = terrain();scene.protected_cells[index] = 1
                self.assertEqual(0,self.guard(lib,scene),index)
            for kind in (GOLD,ITEM,7):
                scene = terrain();paint(scene,(8,1),kind)
                self.assertEqual(0,self.mask(lib,scene))
            self.assertEqual(0,lib.ng2_passage_candidates(None))

    def test_other_orientations_and_shifted_boundaries_are_not_the_same_witness(self):
        for lib in self.libraries.values():
            for operation in (lambda x,y:(-x,y),lambda x,y:(x,-y),lambda x,y:(-y,x),
                lambda x,y:(y,x),lambda x,y:(x+1,y),lambda x,y:(x,y+1)):
                self.assertEqual(0,self.guard(lib,transform(terrain(),operation)))


if __name__ == '__main__':
    unittest.main()
