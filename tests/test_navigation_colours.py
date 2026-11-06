"""TEST027: C色集計は現行Pillowの整数条件と完全一致すること。"""
import ctypes as C
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from necroprobe import navigation_stats as native,shop_navigation as nav
from test_shop_navigation import terrain,shop_image

ROOT=Path(__file__).resolve().parents[1]
N=896*414
OUT=460+N

class ColourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        p=Path(cls.tmp.name)/'colours.so'
        subprocess.run(['gcc','-O2','-fPIC','-ffreestanding','-fno-stack-protector','-fno-builtin','-shared','-nostdlib','-Wl,--build-id=none',str(ROOT/'necroprobe/navigation_stats.c'),'-o',str(p)],check=True)
        cls.lib=C.CDLL(str(p))
    def func(self):
        f=self.lib.necro_navigation_colours
        f.argtypes=[C.c_char_p,C.c_uint32,C.POINTER(C.c_ubyte),C.c_uint32];f.restype=C.c_int
        return f
    def check(self,im):
        out=(C.c_ubyte*OUT)();self.assertEqual(0,self.func()(im.tobytes(),3*N,out,OUT))
        raw=bytes(out);gold=nav._colour_mask(im.split());sign=nav._colour_mask(im.split(),True)
        actual=Image.frombytes('L',im.size,raw[460:])
        for box in nav._HUD:actual.paste(0,box)
        self.assertEqual(sign.tobytes(),actual.tobytes())
        for j in range(10):
            for i in range(23):
                box=(40+36*i,15+36*j,65+36*i,40+36*j)
                if any(nav._overlap(box,h) for h in nav._HUD):continue
                self.assertEqual(gold.crop(box).histogram()[255],int.from_bytes(raw[2*(j*23+i):2*(j*23+i)+2],'little'))
        with patch.object(native,'_native',None):expected=nav.scan(im)
        with patch.object(native,'_native',self.lib),patch.object(nav,'_colour_mask',side_effect=AssertionError('slow colour path')):
            actual=nav.scan(im)
        self.assertEqual(expected,actual)
    def test_exact_random_boundary_extremes_and_full_scene_parity(self):
        rng=random.Random(27027)
        self.check(Image.frombytes('RGB',(896,414),rng.randbytes(3*N)))
        for rgb in ((0,0,0),(255,255,255),(199,164,63),(200,190,10),(52,40,10),(57,50,8),(255,255,0),(63,19,0)):
            self.check(Image.new('RGB',(896,414),rgb))
        self.check(terrain());self.check(shop_image())
    def test_lut_saturation_and_gold_279_280_boundary(self):
        # Every r/g pair with b chosen at both upper/lower mask boundaries.
        pixels=[]
        for r in range(256):
            for g in range(256):
                for b in (g*7//100,(g*580+999)//1000,(g*240+999)//1000):
                    pixels.append((r,g,min(255,b)))
        im=Image.new('RGB',(896,414));im.putdata(pixels+[(0,0,0)]*(N-len(pixels)));self.check(im)
        for n in (279,280):
            im=Image.new('RGB',(896,414));cell=Image.new('RGB',(25,25))
            cell.putdata([(199,164,63)]*n+[(0,0,0)]*(625-n));im.paste(cell,(436,159));self.check(im)
            self.assertEqual(n==280,nav.scan(im).tiles.get((0,-1))=='gold')

    def test_actual_frames_parity(self):
        folder=os.environ.get('NECRO_TEST026_FRAMES')
        if not folder:self.skipTest('external TEST026 frames not supplied')
        paths=list(Path(folder).glob('run-*.jpg'));self.assertTrue(paths,'no TEST026 frames found')
        for p in paths:
            with self.subTest(frame=p.name),Image.open(p) as im:self.check(im.convert('RGB'))
    def test_empty_evidence_folder_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'NECRO_TEST026_FRAMES':folder}):
            with self.assertRaises(AssertionError):self.test_actual_frames_parity()

    def test_fixed_lengths_canaries_and_fallback(self):
        for raw,n,m in ((None,3*N,OUT),(b'x',1,OUT),(b'x',3*N,OUT-1),(b'x',3*N,OUT+1)):
            buf=(C.c_ubyte*OUT)(*([99]*OUT));self.assertEqual(-1,self.func()(raw,n,buf,m));self.assertEqual(bytes([99])*OUT,bytes(buf))
        guard=(C.c_ubyte*(OUT+2))(*([99]*(OUT+2)));ptr=C.cast(C.byref(guard,1),C.POINTER(C.c_ubyte))
        self.assertEqual(0,self.func()(bytes(3*N),3*N,ptr,OUT));self.assertEqual((99,99),(guard[0],guard[-1]))
        with patch.object(native,'_native',None):self.assertIsNone(native.colours(bytes(3*N)))
        with patch.object(native,'_native',self.lib):
            for bad in (None,b'',bytearray(3*N)):self.assertIsNone(native.colours(bad))
            with patch.object(native,'_invoke_colours',return_value=None):self.assertIsNone(native.colours(bytes(3*N)))

if __name__=='__main__':unittest.main()
