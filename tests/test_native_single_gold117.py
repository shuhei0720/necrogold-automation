"""TEST117: caller-owned zero evidence for old GOLD1 and independent DIRT.

A fixed procedural world under changed illumination defines zero. Normal Motion
stays unchanged. This pure helper cannot grant input or displacement credit.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_plural_stationary103 import plural_phase_pair, cell

CORE = Path(os.environ.get('NECRO117_STATIONARY_CORE',
    Path(__file__).resolve().parents[1]/'patches/loopctrl/ngg2'))


def gold_dirt_pair():
    pair=plural_phase_pair()
    for scene in pair:
        scene.gold_state=2
        for i,kind in enumerate(scene.tiles):
            if kind==3:scene.tiles[i]=4
        scene.tiles[cell(-3,2)]=2
    return pair


SHIM=r'''
int test117_combined(const NG2Scene*a,const NG2Scene*b,int d,NG2Motion*out,int32_t*zero){
#if TEST117_GOLD_PRESENT
    return ng2_single_gold_dirt_motion_zero(a,b,d,out,zero);
#else
    if(!zero)return 0;
    *zero=0;return ng2_motion(a,b,d,out);
#endif
}
void test117_reset(void){test117_views=test117_raw=0;}
uint64_t test117_count(int field){return field?test117_raw:test117_views;}
'''


class NativeSingleGold117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='gold-dirt117-')
        directory=Path(cls.temp.name)
        for source in CORE.glob('NG2*'):
            if source.suffix in ('.c','.h'):shutil.copyfile(source,directory/source.name)
        source=(directory/'NG2Navigation.c').read_text()
        present='int ng2_single_gold_dirt_motion_zero(' in source
        for signature,counter in (
            ('static void view(const unsigned char raw[N],View *out) {','views'),
            ('static double intensity(const View *a,const View *b,int sx,int sy) {','raw')):
            if source.count(signature)!=1:raise AssertionError('instrumented primitive must occur once')
            source=source.replace(signature,signature+'++test117_'+counter+';')
        source='#include <stdint.h>\nstatic uint64_t test117_views,test117_raw;\n'+source
        (directory/'NG2Navigation.c').write_text(source)
        shim=directory/'proof.c'
        shim.write_text('#define TEST117_GOLD_PRESENT '+str(int(present))+'\n#include "NG2Navigation.c"\n'+SHIM)
        cls.libraries={}
        for profile,flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
            target=directory/(profile+'.so')
            subprocess.run(['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                '-shared','-fPIC',str(shim),'-lm','-o',str(target)],check=True,capture_output=True)
            cls.libraries[profile]=lib=C.CDLL(str(target));ptr=C.POINTER(Scene)
            lib.ng2_motion.argtypes=[ptr,ptr,C.c_int32,C.POINTER(Motion)]
            lib.test117_combined.argtypes=[ptr,ptr,C.c_int32,C.POINTER(Motion),C.POINTER(C.c_int32)]
            lib.test117_count.argtypes=[C.c_int];lib.test117_count.restype=C.c_uint64

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def compare(self,lib,pair,direction=4):
        saved=tuple(bytes(scene)for scene in pair)
        expected,actual,zero=Motion(),Motion(),C.c_int32(99)
        args=[C.byref(pair[0]),C.byref(pair[1]),direction]
        expected_return=lib.ng2_motion(*args,C.byref(expected))
        lib.test117_reset()
        actual_return=lib.test117_combined(*args,C.byref(actual),C.byref(zero))
        self.assertEqual((expected_return,bytes(expected)),(actual_return,bytes(actual)))
        self.assertEqual(saved,tuple(bytes(scene)for scene in pair))
        self.assertEqual((2,73) if expected_return else (0,0),
                         (lib.test117_count(0),lib.test117_count(1)))
        return (actual.kind,actual.dx,actual.dy),zero.value

    def test_old_single_gold_independent_dirt_adds_only_shared_local_zero(self):
        for profile,lib in self.libraries.items():
            for direction in (1,2,3,4):
                with self.subTest(profile=profile,direction=direction):
                    self.assertEqual(((0,0,0),1),self.compare(lib,gold_dirt_pair(),direction),
                        'a fixed GOLD1/no-STONE/independent-DIRT world needs separate zero evidence')

    def test_old_landmarks_near_floor_and_all_protection_requirements_are_conjunctive(self):
        cases=[]
        for fault in ('clear','pause','partial','old_stone','second_gold','gold_shift','gold_hud',
                      'origin','target','near','protected','door','item','lost_wall','hidden_dirt','eight_dirt'):
            pair=gold_dirt_pair()
            if fault=='clear':pair[1].gold_state=1
            elif fault=='pause':pair[1].state=1
            elif fault=='partial':pair[1].goods=1
            elif fault=='old_stone':pair[0].tiles[cell(8,-2)]=3
            elif fault=='second_gold':pair[1].tiles[cell(8,2)]=2
            elif fault=='gold_shift':
                pair[1].tiles[cell(-3,2)]=1;pair[1].tiles[cell(-4,2)]=2
            elif fault=='gold_hud':
                for scene in pair:scene.tiles[cell(-3,2)]=1;scene.tiles[cell(0,4)]=2
            elif fault=='origin':pair[1].tiles[cell(0,0)]=0
            elif fault=='target':pair[1].tiles[cell(0,1)]=0
            elif fault=='near':pair[1].tiles[cell(-1,0)]=4
            elif fault=='protected':pair[1].protected_cells[cell(8,2)]=1
            elif fault=='door':pair[1].tiles[cell(8,2)]=5
            elif fault=='item':pair[1].tiles[cell(8,2)]=6
            elif fault=='lost_wall':pair[1].tiles[cell(-5,-3)]=1
            elif fault=='hidden_dirt':
                for scene in pair:scene.tiles[cell(0,3)]=4
            else:
                dirt=[i for i,t in enumerate(pair[0].tiles)if t==4]
                for scene in pair:
                    for i in dirt[8:]:scene.tiles[i]=1
            cases.append((fault,pair))
        for profile,lib in self.libraries.items():
            for fault,pair in cases:
                with self.subTest(profile=profile,fault=fault):
                    self.assertEqual(0,self.compare(lib,pair)[1])

    def test_independent_old_dirt_footprint_rejects_a_second_translation_even_with_unique_gold(self):
        for profile,lib in self.libraries.items():
            pair=gold_dirt_pair()
            for i,kind in enumerate(pair[0].tiles):
                if kind==4:pair[1].tiles[cell(i%23-11+1,i//23-5)]=4
            with self.subTest(profile=profile):self.assertEqual(0,self.compare(lib,pair)[1])
            changed=gold_dirt_pair();changed[1].tiles[cell(4,3)]=3
            self.assertEqual(((0,0,0),1),self.compare(lib,changed),
                'remote oldDIRT toSTONE retains the old observed obstacle, never a new anchor')

    def test_known_nonzero_Motion_or_nonzero_world_never_gets_scalar_credit(self):
        for profile,lib in self.libraries.items():
            for direction in (1,2,3,4):
                pair=procedural_pair(direction,amount=1,overlay=False)
                with self.subTest(profile=profile,direction=direction):
                    motion,zero=self.compare(lib,pair,direction)
                    self.assertEqual((1, *{1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}[direction]),motion)
                    self.assertEqual(0,zero)
            pair=gold_dirt_pair()
            pair[1].signature[:]=bytes((value+79*(i%7))%256 for i,value in enumerate(pair[1].signature))
            self.assertEqual(0,self.compare(lib,pair)[1], 'metadata alone cannot prove a changed surface stationary')

    def test_invalid_API_inputs_clear_separate_output_without_changing_normal_contract(self):
        pair=gold_dirt_pair();ptrs=[C.byref(pair[0]),C.byref(pair[1])]
        for lib in self.libraries.values():
            zero=C.c_int32(99);out=Motion(99,99,99)
            self.assertEqual(0,lib.test117_combined(*ptrs,4,None,C.byref(zero)))
            self.assertEqual(0,zero.value)
            self.assertEqual(0,lib.test117_combined(*ptrs,4,C.byref(out),None))
            for direction in (0,5):
                zero.value=99
                self.assertEqual(0,lib.test117_combined(*ptrs,direction,C.byref(out),C.byref(zero)))
                self.assertEqual(0,zero.value)


if __name__=='__main__':unittest.main()
