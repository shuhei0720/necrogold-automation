"""TEST092: lighting drift cannot manufacture or hide a stationary gold view.

The repeated procedural surface independently defines zero displacement.
Raw phone frames and future game replies are not synthesized by these tests.
"""
import ctypes as C
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_stationary_texture085 import stationary_pair, cell

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def gold_pair(noise=17):
    pair = stationary_pair(noise=noise)
    for scene in pair:
        scene.gold_state = 2
        for x, y in ((-1, -5), (1, -5)):
            scene.tiles[cell(x, y)] = 2
    return pair


SHIM = r'''
static void test092_gold_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test092_gold_proof(const NG2Scene*a,const NG2Scene*b,int d,int mode,int initial,NG2Motion*out){
    NG2Scene aa=*a,bb=*b;View v[2];Candidate c[73];int i;
    test092_gold_candidates(a,b,v,c);
    out->kind=initial;out->dx=out->dy=0;
    if(mode==1)c[0].score=NAN;
    if(mode==2)c[72].score=INFINITY;
    if(mode==3)c[72].score=-INFINITY;
    if(mode==4)c[0].score=.45;
    if(mode==5)c[1].score=c[0].score+.079;
    if(mode==6)c[1].score=c[0].score;
    if(mode==7){c[0].sx=9;c[0].sy=0;}
    if(mode==8){memset(v[0].blur,0,N);memset(v[1].blur,0,N);}
    if(mode==9){memset(aa.signature,0,N);memset(bb.signature,0,N);}
    if(mode==10)for(i=0;i<N;++i){int x=i%W,y=i/W;
        aa.signature[i]=bb.signature[i]=(unsigned char)(20+(37*x+53*(y%9))%211);}
    if(mode==11)for(i=0;i<N;++i)if(i/W<53){aa.signature[i]=bb.signature[i]=0;}
#if TEST092_GOLD_PRESENT
    stationary_gold_axis_motion(&aa,&bb,d,v,c,out);
#else
    (void)aa;(void)bb;(void)d;
#endif
}
'''


class NativeGoldStationary092Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test092-gold-static-')
        directory = Path(cls.temp.name)
        for source in CORE.glob('NG2*'):
            if source.suffix in ('.c', '.h'):
                shutil.copyfile(source, directory/source.name)
        source = directory/'NG2Navigation.c'
        present = 'static void stationary_gold_axis_motion(' in source.read_text()
        shim = directory/'proof.c'
        shim.write_text(f'#define TEST092_GOLD_PRESENT {int(present)}\n'
                        '#include "NG2Navigation.c"\n'+SHIM)
        cls.libraries = {}
        external = os.environ.get('NECRO_TEST092_GOLD_LIBRARY')
        if external:
            cls.libraries['external'] = C.CDLL(external)
        else:
            for profile, flags in (('o0', ['-O0']),
                                   ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
                target = directory/(profile+'.so')
                subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                                '-pedantic', '-fPIC', '-shared', str(shim), '-lm', '-o', str(target)],
                               check=True, capture_output=True)
                cls.libraries[profile] = C.CDLL(str(target))
        for lib in cls.libraries.values():
            ptr = C.POINTER(Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            if hasattr(lib, 'test092_gold_proof'):
                lib.test092_gold_proof.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, pair, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, pair, direction=3, mode=0, initial=0):
        out = Motion(99, 99, 99)
        self.assertTrue(hasattr(lib, 'test092_gold_proof'))
        lib.test092_gold_proof(C.byref(pair[0]), C.byref(pair[1]), direction, mode, initial, C.byref(out))
        return out.kind, out.dx, out.dy

    def test_lighting_drift_with_stable_gold_confirms_only_zero(self):
        for profile, lib in self.libraries.items():
            for direction in (1, 2, 3, 4):
                for noise in (16, 17):
                    with self.subTest(profile=profile, direction=direction, noise=noise):
                        self.assertEqual((2, 0, 0), self.result(lib, gold_pair(noise), direction))

    def test_complete_nonhud_old_terrain_gold_and_safe_floor_are_required(self):
        cases = []
        for side in (0, 1):
            for field, value in (('state', 0), ('gold_state', 1), ('goods', 1), ('goods', 2)):
                pair = gold_pair();setattr(pair[side], field, value);cases.append((field, pair))
            for point, kind in (((0, 0), 4), ((0, -1), 0), ((8, 3), 5), ((8, 3), 6)):
                pair = gold_pair();pair[side].tiles[cell(*point)] = kind;cases.append((str(point), pair))
            pair = gold_pair();pair[side].protected_cells[cell(8, 3)] = 1;cases.append(('protected', pair))
            pair = gold_pair();pair[side].tiles[cell(-1, -5)] = 1;cases.append(('lost-gold', pair))
        pair = gold_pair();pair[1].tiles[cell(-1, -5)] = 1;pair[1].tiles[cell(-2, -5)] = 2
        cases.append(('shifted-gold', pair))
        pair = gold_pair();pair[1].tiles[cell(8, -4)] = 2;cases.append(('new-gold', pair))
        pair = gold_pair()
        for s in pair:s.tiles[cell(8, -4)] = 2
        cases.append(('three-gold', pair))
        pair = gold_pair();pair[1].tiles[cell(-5, -2)] = 1;cases.append(('lost-stone', pair))
        pair = gold_pair()
        for s in pair:
            s.tiles[cell(4, 1)] = 1
        cases.append(('one-stone', pair))
        pair = gold_pair()
        for s in pair:
            for i, kind in enumerate(s.tiles):
                if kind == 4:s.tiles[i] = 1
        cases.append(('missing-dirt', pair))
        for profile, lib in self.libraries.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.proof(lib, pair))

    def test_raw_finite_zero_and_independent_texture_competition_are_required(self):
        for profile, lib in self.libraries.items():
            self.assertEqual((2, 0, 0), self.proof(lib, gold_pair()))
            for mode in range(1, 12):
                with self.subTest(profile=profile, mode=mode):
                    self.assertEqual((0, 0, 0), self.proof(lib, gold_pair(), mode=mode))
            for direction in (0, 5):
                self.assertEqual((0, 0, 0), self.proof(lib, gold_pair(), direction=direction))

    def test_known_motion_and_nonzero_surfaces_cannot_be_overwritten(self):
        for profile, lib in self.libraries.items():
            for initial in range(1, 8):
                with self.subTest(profile=profile, initial=initial):
                    self.assertEqual((initial, 0, 0), self.proof(lib, gold_pair(), initial=initial))
            for direction in (1, 2, 3, 4):
                for amount in (3, 9, 18):
                    pair = procedural_pair(direction, amount=amount//9, pixels=amount, overlay=False)
                    result = self.result(lib, pair, direction)
                    expected = 7 if amount == 3 else 1 if amount == 9 else 6
                    self.assertEqual(expected, result[0])


if __name__ == '__main__':
    unittest.main()
