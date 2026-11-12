"""TEST083 public Perception: current floor pixels around a bounded occlusion.

All RGBA is procedural. No item label, red-heart detector, private helper or
Controller state supplies the expected floor classification.
"""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_perception import NativeScene, synthetic_floor

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)


def offset(cell):
    return (cell[1]+5)*23+cell[0]+11


def fill(image, cell, box, colors):
    cx, cy = 448+36*cell[0], 207+36*cell[1]
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            image.putpixel((cx+x, cy+y), colors[(x+y)%len(colors)])


def frame(cell=(-2, 0), full=(49, 24, 15), upper=((29, 19, 17), (35, 23, 21)),
          lower=((29, 19, 17), (35, 23, 21)), lower_box=(-12, 13, 13, 18)):
    image = synthetic_floor()
    fill(image, cell, (-12, -12, 13, 13), (full,))
    fill(image, cell, (-12, -12, 13, 0), upper)
    fill(image, cell, lower_box, lower)
    return image


class NativeOuterFloor083Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='outer-floor083-')
        target = Path(cls.temp.name)/'perception.so'
        subprocess.run(['cc', '-std=c11', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-shared',
                        str(CORE/'NG2Perception.c'), '-lm', '-o', str(target)], check=True)
        cls.lib = C.CDLL(str(target))
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
        cls.lib.ng2_analyze_rgba.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def analyze(self, image, padding=0):
        raw = image.convert('RGBA').tobytes()
        if padding:
            raw = b''.join(raw[y*3584:(y+1)*3584]+bytes([13])*padding for y in range(414))
        scene = NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584+padding, C.byref(scene)))
        self.assertEqual((1, C.sizeof(NativeScene), 2), (scene.abi_version, scene.struct_size, scene.state))
        return scene

    def tile(self, image, cell=(-2, 0)):
        return self.analyze(image).tiles[offset(cell)]

    def test_two_disjoint_current_floor_bands_recover_occluded_floor(self):
        image = frame()
        for name, box, size in (('upper', (-12, -12, 13, 0), 300),
                                ('outer lower', (-12, 13, 13, 18), 125)):
            x0, y0, x1, y1 = box
            values = [image.getpixel((376+x, 207+y)) for y in range(y0, y1) for x in range(x0, x1)]
            self.assertEqual(size, len(values), name)
            self.assertEqual((35, 23, 21), tuple(sorted(p[c] for p in values)[size//2] for c in range(3)), name)
            self.assertGreaterEqual(size*sum(p[0]**2 for p in values)-sum(p[0] for p in values)**2,
                                    4*size*size, name+' must meet the original texture bound')
            witness = synthetic_floor()
            for at in range(625):
                witness.putpixel((364+at%25, 195+at//25), values[at%size])
            self.assertEqual(FLOOR, self.tile(witness), name+' must independently classify as original floor')
        scene = self.analyze(image)
        self.assertEqual(FLOOR, scene.tiles[offset((-2, 0))],
                         '425 observed floor pixels must not become a dirt wall under a narrow occlusion')
        self.assertEqual((0, 0), (scene.goods, sum(scene.protected_cells)),
                         'neither merchandise nor protection is the floor evidence')
        self.assertEqual(FLOOR, self.analyze(frame(), padding=16).tiles[offset((-2, 0))])

    def test_each_floor_band_needs_real_colour_and_texture(self):
        for bad in (((49, 24, 15),), ((32, 20, 18),), ((0, 0, 0), (0, 0, 0), (255, 255, 255)),
                    ((88, 52, 24), (96, 58, 28)), ((70, 58, 48), (90, 76, 64)),
                    ((63, 19, 0), (70, 22, 2))):
            for which in ('upper', 'lower'):
                with self.subTest(which=which, colors=bad):
                    self.assertEqual(DIRT, self.tile(frame(**{which: bad})))
        weak = ((9, 6, 5), (15, 9, 8))
        self.assertEqual(DIRT, self.tile(frame(upper=weak)))
        self.assertEqual(DIRT, self.tile(frame(lower=weak)))
        strong = ((10, 6, 5), (16, 9, 8))
        self.assertEqual(FLOOR, self.tile(frame(upper=strong, lower=strong)),
                         'medianR16 is current visible floor, not near-black salt')

    def test_full_colour_bounds_keep_warm_walls_out(self):
        for full in ((39, 20, 12), (52, 28, 16), (40, 18, 12), (50, 34, 16),
                     (40, 22, 11), (50, 28, 21)):
            with self.subTest(inside=full):
                self.assertEqual(FLOOR, self.tile(frame(full=full)))
        for full in ((38, 20, 12), (53, 28, 16), (40, 17, 12), (50, 35, 16),
                     (40, 22, 10), (50, 28, 22), (118, 76, 36)):
            with self.subTest(outside=full):
                self.assertEqual(DIRT, self.tile(frame(full=full)))

    def test_fixed_same_tile_bands_hud_and_invalid_alpha_are_not_bypassed(self):
        self.assertEqual(DIRT, self.tile(frame(lower_box=(-12, 18, 13, 23))),
                         'floor in the next tile does not replace the fixed y13..17 observation')
        self.assertEqual(UNKNOWN, self.tile(frame(cell=(0, 3)), (0, 3)),
                         'the original heart HUD exclusion remains authoritative')
        self.assertEqual(FLOOR, self.tile(frame(cell=(2, 3)), (2, 3)),
                         'the adjacent genuinely HUD-free tile still has both floor witnesses')
        raw = bytearray(frame().convert('RGBA').tobytes()); raw[3] = 0
        scene = NativeScene()
        self.assertEqual(-1, self.lib.ng2_analyze_rgba(bytes(raw), len(raw), 3584, C.byref(scene)))
        self.assertEqual(0, scene.state)

    def test_old_types_gate_and_merchandise_protection_take_precedence(self):
        cell = (-2, 0)
        for color, expected in (((210, 160, 20), GOLD), ((70, 58, 48), STONE),
                                ((63, 19, 0), UNKNOWN), ((0, 0, 0), UNKNOWN)):
            image = frame(full=color)
            # More than half the original full ROI retains the old material;
            # the two floor witnesses cannot override its non-DIRT type.
            self.assertEqual(expected, self.tile(image), str(color))
        image = frame()
        for side in ((-3, 0), (-1, 0)):
            fill(image, side, (-12, -12, 13, 13), ((210, 160, 20),))
        self.assertEqual(DOOR, self.tile(image), 'old gold gate conversion precedes the additional proof')
        item = (-7, -2)
        image = frame(cell=item)
        image.paste((200, 190, 10), (190, 90, 211, 111))
        scene = self.analyze(image)
        self.assertEqual(1, scene.goods)
        self.assertEqual(ITEM, scene.tiles[offset(item)])
        self.assertEqual(1, scene.protected_cells[offset(item)],
                         'a floor witness does not authorize walking onto a merchandise candidate')
