"""TEST100 fixed lower-left fringe: approach observed FLOOR, retain the wall.

TEST099 actual2 capture59 is the labelled calibration source. These procedural
Scenes express its observed exterior FLOOR and opaque lower-left boundary.
They do not reveal a shop, relabel DIRT, or reconstruct future iPhone views.
"""
import ctypes as C
from itertools import product
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_passage_navigation072 as mouths072
from tests import test_native_supported_mouth084 as supported084
from tests import test_native_corner_vantage086 as corners086
from tests import test_native_shadow_passage094 as shadow094
from tests import test_native_split_shadow095 as split095
from tests import test_native_occluded_corner097 as corner097
from tests import test_native_solid_corner098 as solid098

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
MOUTH = (-3, 2)
OUTSIDE = (-4, 2)
INBOARD = (-2, 2)
VANTAGE = (-2, 1)
WALLS = ((-3, 1), MOUTH, (-3, 3), (-4, 3), (-2, 3))
FLOORS = (OUTSIDE, INBOARD, (-1, 0), (0, 0), (-1, 1), (0, 1))
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def lower_fringe100():
    scene = mouths072.Scene(abi_version=1, struct_size=C.sizeof(mouths072.Scene),
                            state=2, gold_state=1)
    for point in WALLS:
        mouths072.set_cell(scene, *point, DIRT)
    for point in FLOORS + (VANTAGE,):
        mouths072.set_cell(scene, *point, FLOOR)
    return scene


def both_profiles100(method):
    def run(self):
        for profile, library in self.libraries.items():
            with self.subTest(profile=profile):
                self.lib = library
                method(self)
    return run


class NativeLowerFringe100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='lower-fringe100-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.directory.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE/'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[profile] = library = C.CDLL(str(target))
            library.ng2_passage_candidates.argtypes = [C.POINTER(mouths072.Scene)]
            library.ng2_passage_candidates.restype = C.c_uint32
            library.ng2_choose_passage.argtypes = [C.POINTER(mouths072.Scene), C.c_int32, C.c_int32,
                                                  C.c_int32, C.c_int32, C.POINTER(mouths072.Decision)]
            library.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def candidates(self, source):
        before = bytes(source)
        answer = self.lib.ng2_passage_candidates(C.byref(source))
        self.assertEqual(before, bytes(source), 'a hypothesis cannot rewrite DIRT or UNKNOWN terrain')
        return answer

    def choose(self, source, x=0, y=0):
        before = bytes(source)
        out = mouths072.Decision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(source), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(source))
        return length, tuple(getattr(out, name) for name, _ in out._fields_)

    @both_profiles100
    def test_observed_lower_exterior_floor_retains_only_fixed_left_bit9(self):
        for kinds in product((DIRT, STONE), repeat=len(WALLS)):
            scene = lower_fringe100()
            for point, kind in zip(WALLS, kinds):
                mouths072.set_cell(scene, *point, kind)
            self.assertEqual(512, self.candidates(scene),
                             'an observed exterior fringe and safe inboard FLOOR merit a closer look')
            self.assertEqual((4, (1, 10, -2, 2, FLOOR)), self.choose(scene))

    @both_profiles100
    def test_every_positive_wall_and_floor_witness_is_required(self):
        for point in WALLS:
            for kind in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
                scene = lower_fringe100(); mouths072.set_cell(scene, *point, kind)
                expected = 512 if point == MOUTH and kind == FLOOR else 0
                self.assertEqual(expected, self.candidates(scene),
                                 'the unchanged legacy two-flank FLOOR mouth remains a candidate')
        for point in FLOORS + (VANTAGE,):
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                scene = lower_fringe100(); mouths072.set_cell(scene, *point, kind)
                self.assertEqual(0, self.candidates(scene))

    @both_profiles100
    def test_short_current_floor_vantage_and_disconnected_exterior_are_required(self):
        scene = lower_fringe100()
        self.assertEqual(512, self.candidates(scene))
        for point in ((-2, 0), (-3, 0), (-4, 0), (-4, 1)):
            mouths072.set_cell(scene, *point, FLOOR)
        self.assertEqual((6, (1, 10, -4, 2, FLOOR)), self.choose(scene))
        self.assertEqual(128, self.candidates(scene),
                         'the connected path retains the legacy bit7 mouth while rejecting new bit9')
        detour = lower_fringe100()
        for point in ((-1, 0), (-1, 1), (0, 1)):
            mouths072.set_cell(detour, *point, UNKNOWN)
        for point in ((1, 0), (1, 1), (1, 2), (0, 2), (-1, 2)):
            mouths072.set_cell(detour, *point, FLOOR)
        self.assertEqual((6, (2, 10, -2, 2, FLOOR)), self.choose(detour))
        self.assertEqual(0, self.candidates(detour), 'a longer observed detour does not expand the fixed witness')
        isolated = lower_fringe100()
        for point in ((-1, 0), (0, 1)):
            mouths072.set_cell(isolated, *point, UNKNOWN)
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(isolated))
        self.assertEqual(0, self.candidates(isolated), 'isolated observed endpoints supply no input route')

    @both_profiles100
    def test_state_goods_gold_item_protection_and_fixed_coordinates_keep_scope(self):
        for field, value in (('state', 0), ('state', 1), ('state', 3), ('abi_version', 2),
                             ('struct_size', C.sizeof(mouths072.Scene)-1), ('gold_state', 0),
                             ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = lower_fringe100(); setattr(scene, field, value)
            scene.gold_peak = 200
            self.assertEqual(0, self.candidates(scene))
        for kind in (GOLD, ITEM, 7):
            scene = lower_fringe100(); mouths072.set_cell(scene, 8, 1, kind)
            self.assertEqual(0, self.candidates(scene))
        for index in range(230):
            scene = lower_fringe100(); scene.protected_cells[index] = 1
            self.assertEqual(0, self.candidates(scene), 'all protection vetoes this new finite hypothesis')
        scene = lower_fringe100(); scene.protected_cells[0] = 2
        self.assertEqual(0, self.candidates(scene))
        for operation in (lambda x, y: (-x, y), lambda x, y: (x, -y),
                          lambda x, y: (y, x), lambda x, y: (x+1, y)):
            self.assertEqual(0, self.candidates(shadow094.remap(lower_fringe100(), operation)))
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))

    @both_profiles100
    def test_fixed_world_chooser_uses_four_observed_floor_steps_then_holds_at_wall(self):
        terrain = lower_fringe100(); frozen = bytes(terrain)
        x = y = 0
        for remaining in range(4, 0, -1):
            scene = mouths072.shifted(terrain, x, y)
            length, choice = self.choose(scene, x, y)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((remaining, 10, -2-x, 2-y, FLOOR), (length, reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[mouths072.offset(dx, dy)])
            self.assertEqual(0, scene.protected_cells[mouths072.offset(dx, dy)])
            x += dx; y += dy
        self.assertEqual(INBOARD, (x, y))
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(mouths072.shifted(terrain, x, y), x, y))
        self.assertEqual(DIRT, terrain.tiles[mouths072.offset(*MOUTH)])
        self.assertEqual(UNKNOWN, terrain.tiles[mouths072.offset(-4, 1)])
        self.assertEqual(frozen, bytes(terrain), 'no hidden FLOOR or future observation is fabricated')

    @both_profiles100
    def test_existing_mouth_corner_and_shadow_masks_are_preserved(self):
        for make, expected in ((shadow094.shadow, 1), (split095.split_shadow, 1),
                               (supported084.supported, 64), (corner097.upper_shadow097, 1),
                               (corner097.outside_elbow097, 32), (solid098.solid_corner098, 32)):
            scene = mouths072.Scene.from_buffer_copy(bytes(make()))
            self.assertEqual(expected, self.candidates(scene))
        for side in (0, 1):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for outside in (UNKNOWN, FLOOR):
                    for kind in (FLOOR, UNKNOWN):
                        scene = mouths072.room([mouth], outside=outside, mouth_kind=kind)
                        expected = 0 if kind == outside == UNKNOWN else 1 << (side*5+k+2)
                        self.assertEqual(expected, self.candidates(scene))
                if abs(k) == 2:
                    self.assertEqual(1 << (side*5+k+2), self.candidates(corners086.corner(mouth)))


if __name__ == '__main__':
    unittest.main()
