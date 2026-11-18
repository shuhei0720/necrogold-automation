"""Read-only shared lower-price geometry, procedural pixels not phone results."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_ring117 as ring
from tests import test_native_closed_price106 as closed

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2/NG2ShopPriceGeometry.h'


class Geometry(C.Structure):
    _fields_ = [('left', C.c_int), ('sy', C.c_int), ('lower_slot', C.c_int),
                ('boxes', (C.c_int*4)*3), ('ink', C.c_int*3)]


def replace_price(pixels, slot, top, height, digits=1):
    cx = 267+36*slot
    for y in range(222, 248):
        for x in range(cx-11, cx+12):
            closed.single._put(pixels, x, y, (27, 17, 15))
    rows = ('111', '101', '101', '101', '101', '101', '111', '111', '111', '111')
    for d in range(digits):
        for y, row in enumerate(rows[:height]):
            for x, bit in enumerate(row):
                if bit == '1':
                    closed.single._put(pixels, cx-6+4*d+x, top+y, (245, 245, 245))


class NativePriceGeometry117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='price-geometry117-')
        cls.addClassCleanup(cls.tmp.cleanup)
        directory = Path(cls.tmp.name)
        source = directory/'probe.c'
        source.write_text('#include "'+str(CORE)+'"\n'
            'int price_geometry117(const unsigned char *p,size_t n,NG2ShopPriceGeometry *o)'
            '{return ng2_shop_lower_price_geometry(p,n,896*4,o);}\n')
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-shared', '-fPIC', str(source), '-o', str(directory/'probe.so')], check=True)
        cls.lib = C.CDLL(str(directory/'probe.so'))
        cls.lib.price_geometry117.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(Geometry)]

    def geometry(self, pixels):
        buffer = C.create_string_buffer(pixels)
        before = bytes(buffer)
        result = Geometry()
        ok = self.lib.price_geometry117(buffer, len(pixels), C.byref(result))
        self.assertEqual(before, bytes(buffer), 'a shared observation never edits any input pixel')
        return ok, result

    def test_same_full_sign_and_three_independent_complete_price_glyphs(self):
        ok, result = self.geometry(ring.separate_chest_price_pixels())
        self.assertEqual((1, 267, 153, 1), (ok, result.left, result.sy, result.lower_slot))
        self.assertTrue(all(count >= 18 for count in result.ink))
        self.assertEqual([8, 8, 8], [box[3] for box in result.boxes])

    def test_price_height_baseline_missing_extra_and_body_trim_boundaries(self):
        pixels = bytearray(ring.separate_chest_price_pixels())
        whites = [(x, y) for y in range(228, 236) for x in range(328, 352)
                  if min(pixels[4*(y*896+x):4*(y*896+x)+3]) > 140]
        self.assertEqual(19, len(whites))
        for x, y in whites[:2]:
            closed.single._put(pixels, x, y, (27, 17, 15))
        self.assertEqual(0, self.geometry(bytes(pixels))[0], 'seventeen ink pixels remain an incomplete price')
        for slot, top, height, digits in ((2, 228, 6, 3), (1, 235, 10, 2),
                                         (1, 234, 8, 2), (1, 237, 8, 2), (2, 224, 8, 1)):
            pixels = bytearray(ring.separate_chest_price_pixels())
            replace_price(pixels, slot, top, height, digits)
            with self.subTest(slot=slot, top=top, height=height):
                self.assertEqual(0, self.geometry(bytes(pixels))[0])
        for identity in (9, 10, 11):
            for pose in (46, 49, 57):
                for stripe in (False, True):
                    pixels = bytearray(closed.shop_pixels(slot=1, container_id=identity,
                        pose_offset=pose, missing_price=1, price_height=8))
                    if stripe:
                        for y in range(153+pose+22, 153+pose+25):
                            for x in range(300, 307):
                                closed.single._put(pixels, x, y, (245, 245, 245))
                    with self.subTest(identity=identity, pose=pose, stripe=stripe):
                        self.assertEqual(0, self.geometry(bytes(pixels))[0],
                            'a missing real price is not replaced by a short white body ornament')
        pixels = bytearray(ring.separate_chest_price_pixels())
        for y in range(228, 236):
            for x in range(240, 244):
                closed.single._put(pixels, x, y, (245, 245, 245))
        self.assertEqual(0, self.geometry(bytes(pixels))[0], 'a fourth independent group is not three prices')

    def test_incomplete_sprite_extra_full_face_and_invalid_alpha_are_not_complete(self):
        pixels = bytearray(ring.separate_chest_price_pixels())
        for y in range(177, 219):
            for x in range(322, 357):
                closed.single._put(pixels, x, y, (27, 17, 15))
        self.assertEqual(0, self.geometry(bytes(pixels))[0])
        pixels = bytearray(ring.separate_chest_price_pixels())
        for y in range(139, 168):
            for x in range(324, 354):
                closed.single._put(pixels, x, y, (220, 210, 10))
        self.assertEqual(0, self.geometry(bytes(pixels))[0])
        pixels = bytearray(ring.separate_chest_price_pixels())
        pixels[3] = 0
        self.assertEqual(0, self.geometry(bytes(pixels))[0])


if __name__ == '__main__':
    unittest.main()
