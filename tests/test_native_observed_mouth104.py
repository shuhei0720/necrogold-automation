"""TEST104 observed upper mouth: approach known floor, retain hidden outside.

The source label is TEST103 actual4 capture116. Independent sparse procedural
maps express its observed topology, without copying phone pixels or Scene bytes.
"""
import ast
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests import test_native_occluded_corner097 as old097

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
MOUTH, OUTSIDE, VANTAGE = (-2,-3), (-2,-4), (-1,-2)
CENTRE = ((-1,-1),(0,-1),(-1,0),(0,0))
INSIDE = ((-2,-2),(-2,-1),(-1,-2))
WALLS = ((-3,-4),(-3,-3),(-1,-3),(1,-3),(-3,1))
Scene, Decision = old097.OccludedScene, old097.OccludedDecision
position, paint = old097.position, old097.paint


def observed_mouth104():
    scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=1)
    for point in CENTRE + (VANTAGE, MOUTH):
        paint(scene, point, FLOOR)
    for point in WALLS:
        paint(scene, point, DIRT)
    return scene


SHIM = r'''
int test104_observed(const NG2Scene*s){
#if TEST104_OBSERVED_PRESENT
    Path route[CELLS];if(!passage_scene(s))return 0;path_search(s,0,1,route);
    return passage_observed_upper_vantage(s,route);
#else
    (void)s;return 0;
#endif
}
'''


def freeze_inputs(directory):
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
                candidates = [base.with_suffix('.py'), *(base/(a.name+'.py') for a in node.names)]
            elif isinstance(node, ast.Import):
                candidates = [(ROOT/a.name.replace('.', '/')).with_suffix('.py') for a in node.names]
            pending.extend(f for f in candidates if f.is_file())
    compiler = Path(shutil.which('cc')).resolve()
    files = sorted(seen) + [directory/n for n in ('NG2Navigation.c','NG2Core.h','proof.c')] + [compiler]
    record = {'compiler': str(compiler), 'files': {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
    (directory/'before.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


class NativeObservedMouth104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        external = os.environ.get('NECRO_TEST104_NAV_EVIDENCE')
        cls.temp = None if external else tempfile.TemporaryDirectory(prefix='observed-mouth104-')
        directory = Path(external if external else cls.temp.name)
        directory.mkdir(parents=True,exist_ok=True)
        for name in ('NG2Navigation.c','NG2Core.h'):
            shutil.copyfile(CORE/name,directory/name)
        present = 'static int passage_observed_upper_vantage(' in (directory/'NG2Navigation.c').read_text()
        (directory/'proof.c').write_text('#define TEST104_OBSERVED_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        frozen = freeze_inputs(directory)
        cls.libraries, builds = {}, []
        for profile,flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in frozen['files'].items())
            target = directory/(profile+'.so')
            command = [frozen['compiler'],'-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                       '-fPIC','-shared',str(directory/'proof.c'),'-lm','-o',str(target)]
            result = subprocess.run(command,capture_output=True,text=True)
            builds.append({'command':command,'returncode':result.returncode,'stderr':result.stderr})
            (directory/'compile.json').write_text(json.dumps(builds,indent=2)+'\n')
            result.check_returncode()
            cls.libraries[profile] = lib = C.CDLL(str(target))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)]
            lib.ng2_passage_candidates.restype = C.c_uint32
            lib.test104_observed.argtypes = [C.POINTER(Scene)]
            lib.test104_observed.restype = C.c_int
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene),C.c_int,C.c_int,C.c_int,C.c_int,C.POINTER(Decision)]
            lib.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        if cls.temp:
            cls.temp.cleanup()

    def candidates(self,lib,scene,new_only=False):
        before = bytes(scene)
        result = (lib.test104_observed if new_only else lib.ng2_passage_candidates)(C.byref(scene))
        self.assertEqual(before,bytes(scene),'a hypothesis cannot relabel hidden or observed material')
        return result

    def test_observed_mouth_with_supported_walls_adds_only_upper_bit(self):
        for lib in self.libraries.values():
            for kind in (DIRT,STONE):
                scene=observed_mouth104()
                for point in WALLS:paint(scene,point,kind)
                self.assertEqual(1,self.candidates(lib,scene),'an observed floor mouth needs the same safe closer look')
                self.assertEqual((FLOOR,UNKNOWN,UNKNOWN),tuple(scene.tiles[position(*p)]for p in(MOUTH,OUTSIDE,(-2,-2))))

    def test_every_independent_wall_and_opposite_roof_support_is_required(self):
        for lib in self.libraries.values():
            for point in WALLS:
                for kind in (UNKNOWN,FLOOR,GOLD,DOOR,ITEM):
                    scene=observed_mouth104();paint(scene,point,kind)
                    self.assertEqual(0,self.candidates(lib,scene,new_only=True),(point,kind))
            scene=observed_mouth104();paint(scene,(1,-3),UNKNOWN);paint(scene,(0,-3),DIRT)
            self.assertEqual(0,self.candidates(lib,scene,new_only=True),'two near roof walls cannot replace opposite-room support')

    def test_mouth_outside_and_inside_reject_materials_without_relabelling(self):
        for lib in self.libraries.values():
            for point,kinds in ((MOUTH,(UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM)),
                                (OUTSIDE,(FLOOR,GOLD,STONE,DIRT,DOOR,ITEM))):
                for kind in kinds:
                    scene=observed_mouth104();paint(scene,point,kind)
                    self.assertEqual(0,self.candidates(lib,scene,new_only=True),(point,kind))
            for point in INSIDE:
                for kind in (GOLD,STONE,DIRT,DOOR,ITEM):
                    scene=observed_mouth104();paint(scene,point,kind)
                    self.assertEqual(0,self.candidates(lib,scene,new_only=True),(point,kind))
            for point in ((-2,-2),(-2,-1)):
                scene=observed_mouth104();paint(scene,point,FLOOR)
                self.assertEqual(1,self.candidates(lib,scene,new_only=True),'independent already observed inside floor remains floor')

    def test_observed_three_step_vantage_and_protection_are_required(self):
        for lib in self.libraries.values():
            for point in CENTRE+(VANTAGE,):
                for kind in (UNKNOWN,GOLD,STONE,DIRT,DOOR,ITEM):
                    scene=observed_mouth104();paint(scene,point,kind)
                    self.assertEqual(0,self.candidates(lib,scene,new_only=True),(point,kind))
            for point in ((0,0),(-1,0),MOUTH,OUTSIDE,(-2,-2),VANTAGE,(8,1)):
                scene=observed_mouth104();scene.protected_cells[position(*point)]=1
                self.assertEqual(0,self.candidates(lib,scene),'all protection remains independent of the candidate')
            # The endpoint is visible but isolated from the observed centre.
            scene=observed_mouth104();paint(scene,(-1,-1),UNKNOWN)
            self.assertEqual(0,self.candidates(lib,scene,new_only=True))

    def test_scene_goods_gold_abi_and_invalid_cells_reject(self):
        for lib in self.libraries.values():
            for field,value in (('state',0),('state',1),('abi_version',2),('struct_size',C.sizeof(Scene)-1),
                                ('gold_state',0),('gold_state',2),('gold_state',3),('goods',1),('goods',2)):
                scene=observed_mouth104();setattr(scene,field,value)
                self.assertEqual(0,self.candidates(lib,scene))
            for kind in (GOLD,ITEM,7):
                scene=observed_mouth104();paint(scene,(8,1),kind)
                self.assertEqual(0,self.candidates(lib,scene))
            scene=observed_mouth104();scene.protected_cells[position(8,1)]=2
            self.assertEqual(0,self.candidates(lib,scene))
            self.assertEqual(0,lib.ng2_passage_candidates(None))

    def test_fixed_mouth_chooser_walks_only_three_observed_floors_then_holds(self):
        for lib in self.libraries.values():
            terrain=observed_mouth104();x=y=0
            for remaining in (3,2,1):
                scene=old097.transform097(terrain,lambda a,b:(a-x,b-y));before=bytes(scene);choice=Decision()
                self.assertEqual(remaining,lib.ng2_choose_passage(C.byref(scene),x,y,*MOUTH,C.byref(choice)))
                self.assertEqual((10,FLOOR),(choice.reason,choice.obstacle))
                self.assertEqual((VANTAGE[0]-x,VANTAGE[1]-y),(choice.target_x,choice.target_y))
                dx,dy=old097.DIRECTIONS[choice.direction]
                self.assertEqual(FLOOR,scene.tiles[position(dx,dy)])
                self.assertEqual(before,bytes(scene));x+=dx;y+=dy
            self.assertEqual(VANTAGE,(x,y))
            scene=old097.transform097(terrain,lambda a,b:(a-x,b-y));choice=Decision()
            self.assertEqual(0,lib.ng2_choose_passage(C.byref(scene),x,y,*MOUTH,C.byref(choice)))
            self.assertEqual(UNKNOWN,terrain.tiles[position(*OUTSIDE)])
            self.assertEqual(UNKNOWN,terrain.tiles[position(-2,-2)])

    def test_old_dark_mouth_floor_rejection_and_other_sides_keep_their_meaning(self):
        for lib in self.libraries.values():
            scene=old097.upper_shadow097();paint(scene,MOUTH,FLOOR)
            self.assertEqual(0,self.candidates(lib,scene),'a floor mouth alone lacks its observed second flank')
            for op in (lambda x,y:(-x,y),lambda x,y:(x,-y),lambda x,y:(y,x),lambda x,y:(x+1,y)):
                self.assertEqual(0,self.candidates(lib,old097.transform097(observed_mouth104(),op)))


if __name__ == '__main__':
    unittest.main()
