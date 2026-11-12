"""TEST084 public RGBA evidence for a visible lower floor under black shadow."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_perception import NativeScene, synthetic_floor

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
FLOOR_COLOURS = ((29, 19, 17), (35, 23, 21))


class Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
                ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def offset(cell):
    return (cell[1] + 5) * 23 + cell[0] + 11


def paint(image, cell, pixels):
    cx, cy = 448 + 36 * cell[0], 207 + 36 * cell[1]
    for at, colour in enumerate(pixels):
        image.putpixel((cx - 12 + at % 25, cy - 12 + at // 25), colour)
    return image


def texture(colours=FLOOR_COLOURS):
    return [colours[(x + y) % len(colours)] for y in range(25) for x in range(25)]


def shadow(base=(4, 2, 1), upper_black=300, lower_nonblack=293,
           colours=FLOOR_COLOURS):
    floor = texture(colours)
    upper = [base] * upper_black + floor[:300 - upper_black]
    lower = [base] * (325 - lower_nonblack) + floor[:lower_nonblack]
    return upper + lower


def room_image():
    image = synthetic_floor()
    for y in range(-2, 3):
        for x in range(-2, 3):
            paint(image, (x, y), texture())
    for x in range(-3, 4):
        paint(image, (x, -3), texture(((88, 52, 24), (96, 58, 28))))
    return image


class NativeShadowFloor084Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='shadow-floor084-')
        target = Path(cls.temp.name) / 'public.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-shared',
                        str(CORE / 'NG2Perception.c'), str(CORE / 'NG2Navigation.c'),
                        '-lm', '-o', str(target)], check=True)
        cls.lib = C.CDLL(str(target))
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
        cls.lib.ng2_passage_candidates.argtypes = [C.POINTER(NativeScene)]
        cls.lib.ng2_passage_candidates.restype = C.c_uint32
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(NativeScene), C.c_int32, C.c_int32,
                                             C.c_int32, C.c_int32, C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def analyze(self, image, padding=0):
        raw = image.convert('RGBA').tobytes()
        if padding:
            raw = b''.join(raw[y*3584:(y+1)*3584] + bytes([13])*padding for y in range(414))
        scene = NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584+padding, C.byref(scene)))
        self.assertEqual((1, C.sizeof(NativeScene), 2), (scene.abi_version, scene.struct_size, scene.state))
        return scene

    def tile(self, pixels, cell=(-2, 0)):
        return self.analyze(paint(synthetic_floor(), cell, pixels)).tiles[offset(cell)]

    def test_black_entry_partial_floor_becomes_observed_mouth(self):
        for base in ((4, 2, 1), (7, 2, 3)):
            with self.subTest(full_median=base):
                pixels = shadow(base)
                self.assertEqual(base, tuple(sorted(p[c] for p in pixels)[312] for c in range(3)))
                self.assertEqual(300, sum(p[0] < 6 or p[1] < 3 for p in pixels[:300]))
                lower = pixels[300:]
                self.assertEqual(293, sum(p[0] >= 6 and p[1] >= 3 for p in lower))
                n = len(lower)
                self.assertGreaterEqual(n*sum(p[0]**2 for p in lower)-sum(p[0] for p in lower)**2,
                                        4*n*n, 'the actual observed lower pixels meet original texture')
                self.assertEqual(FLOOR, self.tile([lower[at % n] for at in range(625)]),
                                 'the observed lower sample independently satisfies the original floor palette')
                scene = self.analyze(paint(room_image(), (-2, -3), pixels))
                self.assertEqual(FLOOR, scene.tiles[offset((-2, -3))],
                                 'current visible lower floor must survive a black full-ROI median')
                self.assertEqual(UNKNOWN, scene.tiles[offset((-2, -4))])
                self.assertEqual(1, self.lib.ng2_passage_candidates(C.byref(scene)))
                decision = Decision()
                self.assertEqual(5, self.lib.ng2_choose_passage(C.byref(scene), 0, 0, -2, -3, C.byref(decision)))
                self.assertEqual((1, 10, -2, -3, FLOOR), tuple(getattr(decision, k) for k, _ in decision._fields_))
                self.assertEqual(FLOOR, self.analyze(paint(synthetic_floor(), (-2, 0), pixels), 16).tiles[offset((-2, 0))])

    def test_black_entry_and_full_rgb_bounds_are_required(self):
        for inside, outside in (((12, 2, 3), (13, 2, 3)),
                                ((4, 12, 3), (4, 13, 3)),
                                ((4, 2, 12), (4, 2, 13))):
            with self.subTest(boundary=inside):
                self.assertEqual(FLOOR, self.tile(shadow(inside)))
                self.assertEqual(UNKNOWN, self.tile(shadow(outside)))
        # Every upper pixel is black by the original OR rule, but independent
        # channel medians are12/12/12. This is UNKNOWN for colour, not entry.
        pixels = [(12, 0, 12) if at % 2 else (0, 12, 12) for at in range(332)]
        pixels = pixels[:300] + pixels[300:] + texture()[:293]
        self.assertEqual((12, 12, 12), tuple(sorted(p[c] for p in pixels)[312] for c in range(3)))
        self.assertEqual(UNKNOWN, self.tile(pixels), 'a nonblack full median cannot use the black-entry proof')

    def test_fixed_halves_require_95percent_black_and_90percent_visible_floor(self):
        self.assertEqual(FLOOR, self.tile(shadow(upper_black=285)))
        self.assertEqual(UNKNOWN, self.tile(shadow(upper_black=284)))
        self.assertEqual(FLOOR, self.tile(shadow(lower_nonblack=293)))
        self.assertEqual(UNKNOWN, self.tile(shadow(lower_nonblack=292)))
        for pixels in ([(0, 0, 0)]*625, [(4, 2, 1)]*624+[(255, 255, 255)],
                       list(reversed(shadow()))):
            self.assertNotEqual(FLOOR, self.tile(pixels), 'salt or a different half cannot supply the fixed witness')

    def test_observed_floor_requires_original_colour_texture_and_median_r16(self):
        for colours in (((80, 48, 22), (96, 58, 26)), ((52, 42, 34), (60, 48, 40)),
                        ((80, 24, 8), (100, 30, 10)), ((0, 0, 0), (255, 255, 255))):
            with self.subTest(wall_or_salt=colours):
                self.assertEqual(UNKNOWN, self.tile(shadow(colours=colours)))
        for median, expected in ((15, UNKNOWN), (16, FLOOR)):
            colours = ((median, 9, 8),)*3 + ((median+6, 13, 12),)
            self.assertEqual(expected, self.tile(shadow((12, 2, 3), lower_nonblack=312, colours=colours)))
        self.assertEqual(FLOOR, self.tile(shadow(colours=((52, 30, 28),)*3+((58, 34, 32),))))
        self.assertEqual(UNKNOWN, self.tile(shadow(colours=((53, 30, 28),)*3+((59, 34, 32),))))
        self.assertEqual(UNKNOWN, self.tile(shadow((12, 2, 3), lower_nonblack=312, colours=((16, 9, 8),))),
                         'upper/lower contrast does not replace original lower texture')

    def test_existing_materials_gate_goods_and_hud_keep_priority(self):
        for colours, expected in ((((210, 160, 20),), GOLD), (((70, 58, 48), (90, 76, 64)), STONE),
                                  (((88, 52, 24), (96, 58, 28)), DIRT), (((80, 24, 8), (100, 30, 10)), UNKNOWN)):
            self.assertEqual(expected, self.tile(texture(colours)))
        image = paint(synthetic_floor(), (-2, 0), texture(((88, 52, 24), (96, 58, 28))))
        for neighbour in ((-3, 0), (-1, 0)):
            paint(image, neighbour, texture(((210, 160, 20),)))
        self.assertEqual(DOOR, self.analyze(image).tiles[offset((-2, 0))])
        item = (-7, -2)
        image = paint(synthetic_floor(), item, shadow())
        image.paste((200, 190, 10), (190, 90, 211, 111))
        scene = self.analyze(image)
        self.assertEqual((1, ITEM, 1), (scene.goods, scene.tiles[offset(item)], scene.protected_cells[offset(item)]))
        self.assertEqual(UNKNOWN, self.tile(shadow(), (0, 3)), 'the original HUD exclusion covers all625 pixels')
        raw = bytearray(paint(synthetic_floor(), (-2, 0), shadow()).convert('RGBA').tobytes())
        raw[3] = 0
        scene = NativeScene()
        self.assertEqual(-1, self.lib.ng2_analyze_rgba(bytes(raw), len(raw), 3584, C.byref(scene)))
        self.assertEqual(0, scene.state)
