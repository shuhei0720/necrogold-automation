"""Current floor evidence around a compact overlay above a positive GOLD rail.

The floor patches and overlay below are procedural, independently specified
pixels. TEST118/ef175..177 is calibration only; no phone pixels or item names
supply the public test's expected FLOOR or future movement.
"""
import ctypes as C
import os
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


def torch_floor_frame(fault=None, *, cell=(-2, 0), missing_rail=None):
    image = synthetic_floor().convert('RGBA')
    cx, cy = 448+36*cell[0], 207+36*cell[1]

    def fill(x, y, width, height, low, high=None, count=None):
        high = low if high is None else high
        count = width*height if count is None else count
        for k in range(width*height):
            image.putpixel((cx+x+k % width, cy+y+k//width),
                           low if k<count else high)

    # Each diagonal patch has the ordinary positive floor median and texture.
    # Other visible parts have a different lighting rank; full-channel medians
    # alone must remain DIRT in the old classifier.
    fill(-12, -12, 25, 25, (41, 24, 20))
    fill(-12, -12, 12, 12, (31, 19, 18), (74, 43, 36), 80)
    fill(0, -12, 13, 12, (38, 23, 20), (55, 31, 24), 73)
    fill(0, 0, 13, 13, (31, 18, 20), (74, 43, 36), 94)
    fill(-11, 6, 12, 7, (200, 100, 18, 255))
    for delta in (-1, 0, 1):
        px = cx+36*delta
        for y in range(cy+24, cy+49):
            for x in range(px-12, px+13):
                image.putpixel((x, y), (210, 160, 20, 255))
    if missing_rail is not None:
        px = cx+36*missing_rail
        for y in range(cy+24, cy+49):
            for x in range(px-12, px+13):
                image.putpixel((x, y), (31, 19, 18, 255))
    if fault == 'no_warm': fill(-11, 6, 12, 7, (41, 24, 20, 255))
    elif fault == 'UL_dirt': fill(-12, -12, 12, 12, (100, 58, 25), (110, 64, 28), 80)
    elif fault == 'LR_dirt': fill(0, 0, 13, 13, (100, 58, 25), (110, 64, 28), 94)
    elif fault == 'UL_flat': fill(-12, -12, 12, 12, (31, 19, 18))
    elif fault == 'LR_flat': fill(0, 0, 13, 13, (51, 28, 27))
    elif fault == 'dirt_wall':
        fill(-12, -12, 25, 25, (100, 58, 25), (110, 64, 28), 330)
        fill(-11, 6, 12, 7, (200, 100, 18, 255))
    elif fault == 'stone_wall':
        fill(-12, -12, 25, 25, (80, 65, 52), (90, 70, 58), 330)
        fill(-11, 6, 12, 7, (200, 100, 18, 255))
    elif fault == 'gold_wall': fill(-12, -12, 25, 25, (210, 160, 20))
    elif fault == 'door':
        for dx in (-36, 36): fill(dx-12, -12, 25, 25, (210, 160, 20))
    elif fault == 'stray': image.putpixel((cx+10, cy-10), (200, 100, 18, 255))
    elif fault == 'disconnected':
        fill(-11, 6, 12, 7, (41, 24, 20, 255))
        fill(-11, 6, 5, 7, (200, 100, 18, 255))
        fill(-4, 6, 5, 7, (200, 100, 18, 255))
    elif fault == 'raised_blob':
        fill(-11, 6, 12, 7, (41, 24, 20, 255))
        fill(-11, 0, 12, 7, (200, 100, 18, 255))
    elif fault == 'tiny_blob':
        fill(-11, 6, 12, 7, (41, 24, 20, 255))
        fill(-11, 8, 5, 5, (200, 100, 18, 255))
    elif fault == 'low_density':
        fill(-11, 6, 12, 7, (41, 24, 20, 255))
        for x in range(-12, 1): image.putpixel((cx+x, cy), (200, 100, 18, 255))
        for y in range(1, 13):
            image.putpixel((cx-12, cy+y), (200, 100, 18, 255))
            image.putpixel((cx, cy+y), (200, 100, 18, 255))
    return image


class NativeTorchFloor119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='torch-floor119-')
        target = Path(cls.temp.name)/'perception.so'
        source = Path(os.environ.get('NECRO119_FLOOR_SOURCE', str(CORE/'NG2Perception.c')))
        subprocess.run(['cc', '-std=c11', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-frounding-math', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-fPIC', '-shared', '-I'+str(CORE), str(source), '-lm', '-o', str(target)],
                       check=True, capture_output=True)
        cls.lib = C.CDLL(str(target))
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
        cls.lib.ng2_analyze_rgba.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def analyze(self, image, *, padding=0):
        raw = image.convert('RGBA').tobytes()
        if padding:
            raw = b''.join(raw[y*3584:(y+1)*3584]+bytes([13])*padding for y in range(414))
        scene = NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584+padding, C.byref(scene)))
        self.assertEqual((1, C.sizeof(NativeScene), 2),
                         (scene.abi_version, scene.struct_size, scene.state))
        return scene

    def tile(self, image, cell=(-2, 0)):
        return self.analyze(image).tiles[offset(cell)]

    def test_compact_overlay_and_current_positive_floor_patches_recover_floor(self):
        image = torch_floor_frame()
        cx, cy = 376, 207
        # Each patch independently produces the original FLOOR type when its
        # observed colour/texture fills the ordinary sample. UL and LR are
        # disjoint; the upper band overlaps UL and is not extra pixel coverage.
        for box in ((-12, -12, 12, 12), (0, 0, 13, 13), (-12, -12, 25, 12)):
            x, y, w, h = box
            values = [image.getpixel((cx+x+dx, cy+y+dy)) for dy in range(h) for dx in range(w)]
            witness = synthetic_floor().convert('RGBA')
            for k in range(625):
                witness.putpixel((cx-12+k % 25, cy-12+k//25), values[k % len(values)])
            self.assertEqual(FLOOR, self.tile(witness), 'each current patch is original floor evidence')
        scene = self.analyze(image)
        self.assertEqual(FLOOR, scene.tiles[offset((-2, 0))],
                         'a current floor around a compact wall overlay must not remain a dirt obstacle')
        self.assertEqual((0, 0), (scene.goods, sum(scene.protected_cells)))
        self.assertEqual(FLOOR, self.analyze(image, padding=16).tiles[offset((-2, 0))])

    def test_each_current_floor_patch_needs_colour_and_texture(self):
        for fault in ('UL_dirt', 'LR_dirt', 'UL_flat', 'LR_flat'):
            with self.subTest(fault=fault):
                self.assertEqual(DIRT, self.tile(torch_floor_frame(fault)))

    def test_overlay_needs_one_dense_component_with_exact_lower_extent(self):
        for fault in ('no_warm', 'stray', 'disconnected', 'raised_blob', 'tiny_blob', 'low_density'):
            with self.subTest(fault=fault):
                self.assertEqual(DIRT, self.tile(torch_floor_frame(fault)))

    def test_gold_rail_and_existing_nonfloor_types_remain_required(self):
        for rail in (-1, 0, 1):
            with self.subTest(missing_rail=rail):
                self.assertEqual(DIRT, self.tile(torch_floor_frame(missing_rail=rail)))
        for fault, expected in (('dirt_wall', DIRT), ('stone_wall', STONE),
                                ('gold_wall', GOLD), ('door', DOOR)):
            with self.subTest(fault=fault):
                self.assertEqual(expected, self.tile(torch_floor_frame(fault)))

    def test_hud_alpha_and_merchandise_priority_are_unchanged(self):
        self.assertEqual(UNKNOWN, self.tile(torch_floor_frame(cell=(0, 3)), (0, 3)))
        image = torch_floor_frame(cell=(-7, -2))
        image.paste((200, 190, 10), (190, 90, 211, 111))
        scene = self.analyze(image)
        self.assertEqual((1, ITEM, 1),
                         (scene.goods, scene.tiles[offset((-7, -2))],
                          scene.protected_cells[offset((-7, -2))]))
        raw = bytearray(torch_floor_frame().tobytes()); raw[3] = 0
        scene = NativeScene()
        self.assertEqual(-1, self.lib.ng2_analyze_rgba(bytes(raw), len(raw), 3584, C.byref(scene)))
        self.assertEqual(0, scene.state)


if __name__ == '__main__':
    unittest.main()
