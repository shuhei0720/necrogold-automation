"""TEST090: a past floor unit may hide one old stone behind the fixed heart HUD.

The procedural fields define their displacement independently. They are not
phone images, private Controller replay, or evidence of shop arrival.
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
from tests.test_native_passage_motion082 import pair as base_pair, cell, DIRS
from tests.test_native_first_gold083 import SHIM as FIRST_GOLD_SHIM
from tests.test_native_single_gold086 import SHIM as SINGLE_GOLD_SHIM

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def pair(direction=3):
    scenes = base_pair(direction)
    dx, dy = DIRS[direction]
    for x, y in ((-4,-2), (-3,-2), (-2,-2), (2,-2), (3,-2),
                 (-4,2), (-3,2), (-2,2), (2,2)):
        scenes[0].tiles[cell(x,y)] = 4
        scenes[1].tiles[cell(x-dx,y-dy)] = 4
    # DOWN would require the old stone itself inside the lower HUD. That
    # impossible observation is deliberately a rejection case, not a positive.
    x, y = {1:(-2,3), 2:(2,3), 3:(-1,2), 4:(-1,4)}[direction]
    scenes[0].tiles[cell(x,y)] = 3
    scenes[1].tiles[cell(x-dx,y-dy)] = 0
    return scenes


REUSED_SHIM = FIRST_GOLD_SHIM.replace('first_gold_terrain_blur_motion',
                                     'hud_occluded_terrain_blur_motion')
REUSED_SHIM = REUSED_SHIM.replace(
    'return unique_terrain_translation(a,b,sx,sy);',
    '#if TEST083_PRESENT\n return unique_hud_terrain_translation(a,b,sx,sy);\n'
    '#else\n (void)a;(void)b;(void)sx;(void)sy;return 0;\n#endif')
EXTRA_SHIM = SINGLE_GOLD_SHIM.replace('int out[45]', 'int out[48]')
EXTRA_SHIM = EXTRA_SHIM.replace('out[42]=m.kind;out[43]=m.dx;out[44]=m.dy;',
    'out[42]=m.kind;out[43]=m.dx;out[44]=m.dy;\n'
    ' singleton_gold_terrain_blur_motion(a,b,d,v,c,&m);\n'
    ' out[45]=m.kind;out[46]=m.dx;out[47]=m.dy;')
EXTRA_SHIM = EXTRA_SHIM.replace('singleton_gold_terrain_blur_motion(&aa,&bb,NG2_UP,v,c,&m);',
                              'hud_occluded_terrain_blur_motion(&aa,&bb,NG2_UP,v,c,&m);')
EXTRA_SHIM += r'''
int test090_geometry_count(const NG2Scene*a,const NG2Scene*b) {
#if TEST083_PRESENT
    int amount,d,count=0;
    for(amount=0;amount<=2;++amount)for(d=1;d<=(amount?4:1);++d)
        count+=hud_terrain_translation(a,b,amount*ddx[d],amount*ddy[d]);
    return count;
#else
    (void)a;(void)b;return 0;
#endif
}
'''


class NativeHudUnit090Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test090-hud-unit-')
        directory = Path(cls.temp.name)
        for p in CORE.glob('NG2*'):
            if p.suffix in ('.c','.h'): shutil.copyfile(p,directory/p.name)
        source = Path(os.environ.get('NECRO_TEST090_BASELINE_NAVIGATION', CORE/'NG2Navigation.c'))
        shutil.copyfile(source, directory/'NG2Navigation.c')
        hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c','.h')}
        if len(hashes) != 8: raise AssertionError('eight native C/H source identities required')
        identity = os.environ.get('NECRO_TEST090_HUD_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps(dict(source_sha256=hashes,
                selected_navigation=str(source), test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
                sort_keys=True,indent=2)+'\n')
        present = 'static void hud_occluded_terrain_blur_motion(' in source.read_text()
        shim = directory/'proof.c'
        shim.write_text('#define NECROGOLD_HOST_TEST 1\n'
            +f'#define TEST083_PRESENT {int(present)}\n#include "{directory / "NG2Navigation.c"}"\n'
            +'#if defined(NECROGOLD_HOST_TEST)\n'+REUSED_SHIM+EXTRA_SHIM+'\n#endif\n')
        cls.libraries = {}
        for profile, flags in (('o0',['-O0']), ('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            path = directory/(profile+'.so')
            subprocess.run(['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                '-fPIC','-shared',str(shim),'-lm','-o',str(path)], check=True,capture_output=True)
            lib=C.CDLL(str(path));ptr=C.POINTER(Scene);ints=C.POINTER(C.c_int)
            lib.ng2_motion.argtypes=[ptr,ptr,C.c_int,C.POINTER(Motion)]
            lib.ng2_entered_gate.argtypes=[ptr,ptr,C.c_int,C.c_int,C.c_int,C.c_int,C.POINTER(Entrance)]
            lib.test086_previous.argtypes=[ptr,ptr,C.c_int,ints]
            lib.test086_stats.argtypes=[ptr,ptr,C.c_int,C.POINTER(C.c_double),ints]
            lib.test083_proof.argtypes=[ptr,ptr,C.c_int,C.c_double,C.c_double,C.c_int,C.c_int,C.c_int,C.POINTER(Motion)]
            lib.test083_geometry.argtypes=[ptr,ptr,C.c_int,C.c_int]
            lib.test090_geometry_count.argtypes=[ptr,ptr]
            lib.test083_components.argtypes=[ptr,ptr,C.c_int,ints]
            lib.test086_axis_components.argtypes=[ptr,ptr,C.c_int,ints]
            lib.test083_numeric.argtypes=[C.c_int]*5
            lib.test086_numeric.argtypes=[C.c_int]*5
            lib.test086_dependencies.argtypes=[ptr,ptr]+[C.c_int]*4
            cls.libraries[profile]=lib

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def motion(self,lib,scenes,direction=3):
        out=Motion(99,99,99)
        self.assertEqual(1,lib.ng2_motion(C.byref(scenes[0]),C.byref(scenes[1]),direction,C.byref(out)))
        return out.kind,out.dx,out.dy

    def proof(self,lib,scenes,direction=3,score=.6,gap=.2,shift=None,other=0,initial=0):
        dx,dy=DIRS[direction];sx,sy=shift if shift is not None else (-9*dx,-9*dy)
        out=Motion(initial,0,0)
        lib.test083_proof(C.byref(scenes[0]),C.byref(scenes[1]),direction,score,gap,sx,sy,other,C.byref(out))
        return out.kind,out.dx,out.dy

    def test_public_unit_retains_visible_stones_when_one_moves_into_heart_hud(self):
        for profile,lib in self.libraries.items():
            for direction in (1,2,3):
                with self.subTest(profile=profile,direction=direction):
                    scenes=pair(direction);dx,dy=DIRS[direction]
                    previous=(C.c_int*48)();scores=(C.c_double*6)();flags=(C.c_int*24)()
                    lib.test086_previous(C.byref(scenes[0]),C.byref(scenes[1]),direction,previous)
                    self.assertEqual([0]*48,list(previous),'all sixteen old stages remain independently UNKNOWN')
                    lib.test086_stats(C.byref(scenes[0]),C.byref(scenes[1]),direction,scores,flags)
                    self.assertGreater(scores[0],.45);self.assertGreaterEqual(scores[1],.08)
                    self.assertEqual((-9*dx,-9*dy),tuple(flags[:2]))
                    self.assertEqual((3,2,9),(flags[10],flags[11],flags[12]))
                    self.assertGreater(flags[13],0);self.assertEqual((1,1),(flags[8],flags[9]))
                    self.assertEqual((1,dx,dy),self.motion(lib,scenes,direction),
                        'a visible two-anchor unit must not be lost because a third anchor enters fixed HUD')
                    entered=Entrance(99,99,99,99)
                    self.assertEqual(0,lib.ng2_entered_gate(C.byref(scenes[0]),C.byref(scenes[1]),
                        direction,0,0,1,C.byref(entered)))
                    self.assertEqual((0,0,0,0),tuple(getattr(entered,k) for k,_ in entered._fields_))

    def test_exact_new_hud_occlusion_and_independent_old_terrain_are_required(self):
        for profile,lib in self.libraries.items():
            self.assertEqual((1,0,-1),self.proof(lib,pair()))
            self.assertEqual((0,0,0),self.proof(lib,pair(4),4),'the old source may not already be hidden')
            for point in ((-5,-2),(4,1)):
                for kind in (0,1,4):
                    scenes=pair();scenes[1].tiles[cell(point[0],point[1]+1)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes))
            for kind in (1,3,4):
                scenes=pair();scenes[1].tiles[cell(-1,3)]=kind
                self.assertEqual((0,0,0),self.proof(lib,scenes),'only unobserved HUD, never another material')
            for x in (-2,2):
                scenes=pair();scenes[0].tiles[cell(-1,2)]=1;scenes[1].tiles[cell(-1,3)]=1
                scenes[0].tiles[cell(x,2)]=3;scenes[1].tiles[cell(x,3)]=0
                # Replace the one dirt anchor used for this outside-HUD stone,
                # so rejection cannot come merely from an eight-dirt fixture.
                scenes[0].tiles[cell(6,2)]=4;scenes[1].tiles[cell(6,3)]=4
                self.assertEqual(9,sum(k==4 for k in scenes[0].tiles))
                self.assertEqual((0,0,0),self.proof(lib,scenes),'a stone lost outside HUD stays contradictory')
            scenes=pair();scenes[0].tiles[cell(4,1)]=1
            self.assertEqual((0,0,0),self.proof(lib,scenes))
            with self.subTest(profile=profile,unobserved_support='source_stone_in_other_hud'):
                scenes=pair();scenes[0].tiles[cell(-9,-3)]=3;scenes[1].tiles[cell(-9,-2)]=3
                self.assertEqual((0,0,0),self.proof(lib,scenes),
                                 'a stone under the fixed DIG HUD is never an observed anchor')
            with self.subTest(profile=profile,unobserved_support='dirt_count_inflated_by_other_hud'):
                scenes=pair();scenes[0].tiles[cell(-4,2)]=1;scenes[1].tiles[cell(-4,3)]=1
                scenes[0].tiles[cell(-9,-3)]=4;scenes[1].tiles[cell(-9,-2)]=4
                self.assertEqual(9,sum(k==4 for k in scenes[0].tiles))
                self.assertEqual((0,0,0),self.proof(lib,scenes),
                                 'eight visible dirt plus a HUD sample cannot become nine anchors')
            scenes=pair();scenes[0].tiles[cell(0,2)]=3;scenes[1].tiles[cell(0,3)]=0
            self.assertEqual((0,0,0),self.proof(lib,scenes),'two disappearing stones exceed the sole occlusion')
            scenes=pair();old_dirt=[i for i,k in enumerate(scenes[0].tiles) if k==4]
            scenes[1].tiles[old_dirt[0]+23]=1
            self.assertEqual((0,0,0),self.proof(lib,scenes),'eight dirt anchors are insufficient')
            scenes=pair()
            for s in scenes:s.tiles[:]=[1]*230
            for x,kind in ((-6,3),(6,3),*[(x,4) for x in (-10,-9,-8,-7,-5,-4,-3,-2,2)]):
                scenes[0].tiles[cell(x,2)]=kind;scenes[1].tiles[cell(x,3)]=kind
            scenes[0].tiles[cell(-1,2)]=3;scenes[1].tiles[cell(-1,3)]=0
            self.assertEqual(9,sum(k==4 for k in scenes[0].tiles))
            self.assertEqual((0,0,0),self.proof(lib,scenes))
            scenes=pair()
            for s in scenes:s.tiles[:]=[1]*230
            stones=((-5,-2),(6,1),(-1,2),(-2,3))
            # Keep the complete 25px samples outside every fixed HUD; the
            # old (-9,-2) sample would overlap DIG despite its map position.
            dirt=((-10,0),(-8,-2),(-7,-2),(-3,-2),(2,-2),(3,-2),(-9,2),(-8,2),(2,2))
            for kind,points in ((3,stones),(4,dirt)):
                for x,y in points:
                    scenes[0].tiles[cell(x,y)]=kind
                    for tx,ty in ((0,1),(1,0)):
                        if (x+tx,y+ty)==(-1,3):continue
                        prior=scenes[1].tiles[cell(x+tx,y+ty)]
                        self.assertIn(prior,(1,kind),'the two material translations must not contradict')
                        scenes[1].tiles[cell(x+tx,y+ty)]=kind
            scenes[1].tiles[cell(-1,3)]=0
            self.assertEqual(2,lib.test090_geometry_count(C.byref(scenes[0]),C.byref(scenes[1])),
                             'two different visible old stones may project onto the same hidden cell')
            self.assertEqual(0,lib.test083_geometry(C.byref(scenes[0]),C.byref(scenes[1]),0,9))
            self.assertEqual((0,0,0),self.proof(lib,scenes))

    def test_scope_safe_observed_endpoints_and_known_motion_results_are_preserved(self):
        for profile,lib in self.libraries.items():
            for side in (0,1):
                for field,values in (('state',(0,1,3)),('gold_state',(0,2,3)),('goods',(1,2))):
                    for value in values:
                        scenes=pair();setattr(scenes[side],field,value)
                        self.assertEqual((0,0,0),self.proof(lib,scenes))
                for kind in (2,5,6):
                    scenes=pair();scenes[side].tiles[cell(7,-3)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes))
                scenes=pair();scenes[side].protected_cells[cell(8,4)]=1
                self.assertEqual((0,0,0),self.proof(lib,scenes))
            for side,point in ((0,(0,0)),(0,(0,-1)),(1,(0,0))):
                for kind in (0,3,4):
                    scenes=pair();scenes[side].tiles[cell(*point)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes))
            for initial in range(1,8):self.assertEqual((initial,0,0),self.proof(lib,pair(),initial=initial))
            for direction,(dx,dy) in DIRS.items():
                for pixels,expected in ((0,(2,0,0)),(8,(7,0,0)),(9,(1,dx,dy)),
                                        (18,(6,2*dx,2*dy)),(-9,(6,-dx,-dy))):
                    self.assertEqual(expected,self.motion(lib,procedural_pair(direction,pixels=pixels,overlay=False),direction))

    def test_raw_unit_finite_phases_and_original_numeric_thresholds_are_unchanged(self):
        for profile,lib in self.libraries.items():
            scenes=pair()
            for score,gap,other,expected in ((.45,.2,0,0),(.450001,.2,0,1),(.6,.079999,0,0),
                    (.6,.2,0,1),(math.nan,.2,0,0),(math.inf,.2,0,0),(-math.inf,.2,0,0),
                    (.6,math.inf,0,0),(.6,.2,1,0),(.6,.2,2,0),(.6,.2,3,0)):
                self.assertEqual(expected,self.proof(lib,scenes,score=score,gap=gap,other=other)[0])
            for shift in ((0,0),(0,8),(0,-9),(0,18)):
                self.assertEqual((0,0,0),self.proof(lib,scenes,shift=shift))
            for mode in range(6):
                flags=(C.c_int*9)()
                # Mode2 keeps independent_phase true but makes the runner-up
                # band unavailable. This proof additionally requires both
                # winner and runner-up finite in both bands.
                self.assertEqual(1 if mode==0 else 0,
                    lib.test083_components(C.byref(scenes[0]),C.byref(scenes[1]),mode,flags))
                if mode==2:self.assertEqual((1,0,1),tuple(flags[5:8]))
            for args,expected in (((300,15,100,300,60),1),((299,0,100,300,60),0),
                    ((300,16,100,300,60),0),((300,15,99,300,60),0),((300,15,201,300,60),0),((300,15,100,300,59),0)):
                self.assertEqual(expected,lib.test083_numeric(*args))

    def test_independent_axis_all_competitors_and_blur_dependencies_remain_required(self):
        for profile,lib in self.libraries.items():
            scenes=pair()
            for mode in range(5):
                flags=(C.c_int*6)()
                self.assertEqual(1 if mode==0 else 0,
                    lib.test086_axis_components(C.byref(scenes[0]),C.byref(scenes[1]),mode,flags))
                self.assertEqual(1,flags[5])
                if mode==1:self.assertLess(flags[0],300)
                if mode==2:self.assertGreater(4*flags[1],flags[0])
                if mode==3:self.assertLess(flags[2],100)
                if mode==4:self.assertEqual(0,flags[4])
            for args,expected in (((300,75,100,300,120),1),((299,0,100,300,120),0),
                    ((300,76,100,300,120),0),((300,75,99,300,120),0),((300,75,201,300,120),0),((300,75,100,300,119),0)):
                self.assertEqual(expected,lib.test086_numeric(*args))
            self.assertEqual(1,lib.test086_dependencies(C.byref(scenes[0]),C.byref(scenes[1]),75,28,0,9))
            scenes[1].tiles[cell(-4,-1)]=0
            self.assertEqual(0,lib.test086_dependencies(C.byref(scenes[0]),C.byref(scenes[1]),75,28,0,9))


if __name__=='__main__':unittest.main()
