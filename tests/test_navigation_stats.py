"""TEST-018の固定格子統計。実機性能はこのホスト試験で代用しない。"""
import ctypes as C
import hashlib
from pathlib import Path
import os
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageStat
from necroprobe import shop_navigation as nav

ROOT=Path(__file__).resolve().parents[1]
RGB_LENGTH=896*414*3
OUTPUT_LENGTH=230*4

def reference(image):
    result=[]
    for j in range(-5,5):
        for i in range(-11,12):
            x,y=448+36*i,207+36*j
            stat=ImageStat.Stat(image.crop((x-12,y-12,x+13,y+13)))
            result.extend([*stat.median,int(max(stat.stddev)>=2)])
    return bytes(result)

class NavigationStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        lib=Path(cls.tmp.name)/'navigation-host.so'
        subprocess.run(['gcc','-O2','-fPIC','-ffreestanding','-fno-stack-protector','-fno-builtin',
                        '-shared','-nostdlib','-Wl,--build-id=none',str(ROOT/'necroprobe/navigation_stats.c'),
                        '-o',str(lib)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(lib));cls.func=cls.lib.necro_navigation_stats
        cls.func.argtypes=[C.c_char_p,C.c_uint32,C.POINTER(C.c_ubyte),C.c_uint32];cls.func.restype=C.c_int
    def scan(self,image):
        out=(C.c_ubyte*OUTPUT_LENGTH)()
        self.assertEqual(0,self.func(image.tobytes(),RGB_LENGTH,out,OUTPUT_LENGTH));return bytes(out)
    def test_01_exact_statistics_boundaries_and_all_channels(self):
        for color in ((0,0,0),(255,255,255),(37,23,25)):
            with self.subTest(color=color):
                im=Image.new('RGB',(896,414),color);self.assertEqual(reference(im),self.scan(im))
        rng=random.Random(18018)
        im=Image.frombytes('RGB',(896,414),rng.randbytes(RGB_LENGTH))
        self.assertEqual(reference(im),self.scan(im))
        # 625 pixels: median crosses at sample313; variance is below/equal/above4.
        cases=[([18]*312+[22]*313,22,0),([18]*313+[22]*312,18,0),
               ([18]*310+[22]*310+[17,23,19,21,20],20,1),
               ([18]*312+[22]*312+[23],22,1)]
        for values,median,spread in cases:
            for channel in range(3):
                for offset in (0,225):
                    with self.subTest(channel=channel,offset=offset,median=median,spread=spread):
                        pixels=[]
                        for v in values:
                            pixel=[200,210,220];pixel[channel]=v+offset;pixels.append(tuple(pixel))
                        im=Image.new('RGB',(896,414));cell=Image.new('RGB',(25,25));cell.putdata(pixels)
                        im.paste(cell,(40,15));actual=self.scan(im)
                        self.assertEqual(median+offset,actual[channel]);self.assertEqual(spread,actual[3])
                        self.assertEqual(reference(im),actual)
    def test_02_reject_lengths_without_writes(self):
        for raw,n,m in ((None,RGB_LENGTH,OUTPUT_LENGTH),(b'x',1,OUTPUT_LENGTH),
                        (b'x',RGB_LENGTH-1,OUTPUT_LENGTH),(b'x',0xffffffff,OUTPUT_LENGTH),
                        (b'x',RGB_LENGTH,OUTPUT_LENGTH-1),(b'x',RGB_LENGTH,OUTPUT_LENGTH+1)):
            out=(C.c_ubyte*OUTPUT_LENGTH)(*([99]*OUTPUT_LENGTH))
            self.assertEqual(-1,self.func(raw,n,out,m));self.assertEqual(bytes([99])*OUTPUT_LENGTH,bytes(out))
        self.assertEqual(-1,self.func(b'x',RGB_LENGTH,None,OUTPUT_LENGTH))
        guarded=(C.c_ubyte*(OUTPUT_LENGTH+2))(*([99]*(OUTPUT_LENGTH+2)))
        output=C.cast(C.byref(guarded,1),C.POINTER(C.c_ubyte))
        self.assertEqual(0,self.func(bytes(RGB_LENGTH),RGB_LENGTH,output,OUTPUT_LENGTH))
        self.assertEqual((99,99),(guarded[0],guarded[-1]))
    def test_03_optional_real_frames_and_full_navigation_parity(self):
        folder=os.environ.get('NECRO_STATS_FRAMES')
        if not folder:self.skipTest('external real frames not supplied')
        from necroprobe import navigation_stats
        paths=list(Path(folder).rglob('*.jpg'));self.assertGreater(len(paths),0)
        for path in paths:
            with self.subTest(frame=path.name),Image.open(path) as src:
                im=src.convert('RGB');self.assertEqual(reference(im),self.scan(im))
                with patch.object(navigation_stats,'_native',None):expected=nav.scan(im)
                with patch.object(navigation_stats,'_native',self.lib),patch.object(ImageStat,'Stat',side_effect=AssertionError('slow statistics')):
                    actual=nav.scan(im)
                self.assertEqual(expected,actual)
                self.assertEqual(nav.choose(expected),nav.choose(actual))
                self.assertEqual(nav.motion(expected,expected,'left'),nav.motion(actual,actual,'left'))
    def test_04_artifact_loader_hash_selfcheck_and_fallback(self):
        from necroprobe import navigation_stats as native
        blob=(ROOT/'necroprobe/navigation_stats_i386.so').read_bytes()
        self.assertEqual(b'\x7fELF\x01\x01',blob[:6]);self.assertEqual(3,int.from_bytes(blob[18:20],'little'))
        self.assertEqual(native._EXPECTED_SHA256,hashlib.sha256(blob).hexdigest())
        symbols=subprocess.run(['nm','-u',str(ROOT/'necroprobe/navigation_stats_i386.so')],capture_output=True,text=True,check=True)
        self.assertEqual('',symbols.stdout.strip())
        dynamic=subprocess.run(['readelf','-d',str(ROOT/'necroprobe/navigation_stats_i386.so')],capture_output=True,text=True,check=True)
        self.assertNotIn('NEEDED',dynamic.stdout)
        with patch.object(native.sys,'platform','linux'),patch.object(native.C,'sizeof',return_value=4),patch.object(native.C,'CDLL',return_value=self.lib) as loader:
            self.assertIs(self.lib,native._load())
            loader.reset_mock()
            with patch.object(Path,'read_bytes',return_value=b'corrupt'):
                self.assertIsNone(native._load());loader.assert_not_called()
            with patch.object(native.C,'CDLL',side_effect=OSError('unavailable')):
                self.assertIsNone(native._load())
            with patch.object(native,'_invoke',return_value=bytes(OUTPUT_LENGTH)):
                self.assertIsNone(native._load())
        with patch.object(native.sys,'platform','linux'),patch.object(native.C,'sizeof',return_value=8),patch.object(native.C,'CDLL') as loader:
            self.assertIsNone(native._load());loader.assert_not_called()
        with patch.object(native.sys,'platform','darwin'),patch.object(native.C,'sizeof',return_value=4),patch.object(native.C,'CDLL') as loader:
            self.assertIsNone(native._load());loader.assert_not_called()
        with patch.object(native,'_native',self.lib):
            for value in (None,'x',b'x',bytearray(RGB_LENGTH),bytes(RGB_LENGTH+1)):
                self.assertIsNone(native.scan(value))
        with patch.object(native,'_native',self.lib),patch.object(native,'ENGINE','native_i386'),patch.object(native,'_invoke',return_value=None):
            self.assertIsNone(native.scan(bytes(RGB_LENGTH)));self.assertEqual('pillow',native.ENGINE)
