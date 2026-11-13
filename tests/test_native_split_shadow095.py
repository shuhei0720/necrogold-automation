"""TEST095 marked split upper-left roof: approach observed FLOOR, retain UNKNOWN.

The user labels TEST094 capture146 as a passage candidate. Only its visible
wall/unknown/floor topology supports this finite initial-world hypothesis;
these procedural scenes do not reconstruct an unseen shop or future frames.
"""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_passage_navigation072 import Scene, Decision, room, set_cell, offset, shifted
from tests.test_native_supported_mouth084 import supported
from tests.test_native_corner_vantage086 import corner
from tests.test_native_shadow_passage094 import profiles, remap, shadow

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
MOUTH = (-2, -3)
DARK = ((-2, -4), (-2, -3), (-1, -3), (-3, -2), (-2, -2), (-1, -2))
WALLS = ((-4, -3), (-3, -3), (0, -3), (1, -3), (2, -3), (-3, -1), (-3, 0))
FLOORS = tuple((x, y) for y in (-1, 0) for x in range(-2, 1)) + ((0, -2), (1, -2))
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def split_shadow(wall=DIRT):
    scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=1)
    for p in WALLS:
        set_cell(scene, *p, wall)
    for p in FLOORS:
        set_cell(scene, *p, FLOOR)
    return scene


class NativeSplitShadow095Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='split-shadow095-')
        cls.libraries = {}
        for name, flags in (('unchanged_o0', ['-O0']), ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[name] = lib = C.CDLL(str(target))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)]
            lib.ng2_passage_candidates.restype = C.c_uint32
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                                             C.c_int32, C.c_int32, C.POINTER(Decision)]
            lib.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidates(self, scene):
        before = bytes(scene)
        value = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'the candidate cannot relabel any observed or UNKNOWN cell')
        return value

    def choose(self, scene, x=0, y=0):
        before = bytes(scene)
        out = Decision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(out, field) for field, _ in out._fields_)

    @profiles
    def test_marked_split_roof_adds_only_fixed_upper_left_hypothesis(self):
        scene = split_shadow()
        self.assertEqual((UNKNOWN,) * 6, tuple(scene.tiles[offset(*p)] for p in DARK))
        self.assertEqual((DIRT,) * 7, tuple(scene.tiles[offset(*p)] for p in WALLS))
        self.assertEqual((FLOOR,) * 8, tuple(scene.tiles[offset(*p)] for p in FLOORS))
        self.assertEqual((3, (1, 10, -2, -1, FLOOR)), self.choose(scene))
        self.assertEqual(1, self.candidates(scene), 'the marked split roof has a safe three-step FLOOR vantage')
        for wall in (DIRT, STONE):
            self.assertEqual(1, self.candidates(split_shadow(wall)), 'observed wall material does not reveal an unseen passage')

    @profiles
    def test_all_six_dark_cells_remain_unknown_and_are_required(self):
        for p in DARK:
            for value in (FLOOR, GOLD, STONE, DIRT, DOOR, ITEM):
                with self.subTest(position=p, material=value):
                    scene = split_shadow(); set_cell(scene, *p, value)
                    self.assertEqual(0, self.candidates(scene) & 1)

    @profiles
    def test_both_roof_sides_and_lower_left_wall_need_observed_support(self):
        for p in WALLS:
            for value in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
                with self.subTest(position=p, material=value):
                    scene = split_shadow(); set_cell(scene, *p, value)
                    result = self.candidates(scene)
                    self.assertEqual(0, result & 1)
                    if p == (1, -3) and value == FLOOR:
                        self.assertEqual(1 << 3, result, 'the original observed two-flank mouth remains valid')
        scene = split_shadow()
        for p in WALLS:
            set_cell(scene, *p, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'black gaps without observed walls do not authorize a candidate')

    @profiles
    def test_observed_approach_floor_shortest_path_and_all_protections_are_required(self):
        for p in FLOORS:
            for value in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                with self.subTest(position=p, material=value):
                    scene = split_shadow(); set_cell(scene, *p, value)
                    self.assertEqual(0, self.candidates(scene) & 1)
        for p in set(DARK + WALLS + FLOORS + ((8, 1),)):
            scene = split_shadow(); set_cell(scene, *p, scene.tiles[offset(*p)], 1)
            self.assertEqual(0, self.candidates(scene) & 1)
        scene = split_shadow()
        set_cell(scene, -1, 0, UNKNOWN); set_cell(scene, -1, -1, UNKNOWN)
        for p in ((0, 1), (-1, 1), (-2, 1)):
            set_cell(scene, *p, FLOOR)
        self.assertEqual((5, (4, 10, -2, -1, FLOOR)), self.choose(scene))
        self.assertEqual(0, self.candidates(scene) & 1, 'a longer detour is outside the three-step hypothesis')

    @profiles
    def test_fixed_world_mouth_uses_three_actual_floor_steps_then_holds(self):
        terrain = split_shadow(); x = y = 0
        self.assertEqual(1, self.candidates(terrain))
        for step in range(3):
            scene = shifted(terrain, x, y)
            length, choice = self.choose(scene, x, y)
            self.assertEqual(3-step, length)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((10, -2-x, -1-y, FLOOR), (reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
            self.assertEqual(0, scene.protected_cells[offset(dx, dy)])
            x += dx; y += dy
        self.assertEqual((-2, -1), (x, y))
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(shifted(terrain, x, y), x, y))
        self.assertEqual((UNKNOWN,) * 6, tuple(terrain.tiles[offset(*p)] for p in DARK))

    @profiles
    def test_old_candidates_and_invalid_gold_goods_other_corners_are_preserved(self):
        self.assertEqual(1, self.candidates(shadow()))
        self.assertEqual(1 << 6, self.candidates(supported()))
        for side in range(2):
            for k in (-2, 2):
                self.assertEqual(1 << (side*5+k+2), self.candidates(corner((-3, k) if side else (k, -3))))
        mouths = tuple((k, -3) for k in range(-2, 3)) + tuple((-3, k) for k in range(-2, 3))
        for bit, mouth in enumerate(mouths):
            self.assertEqual(1 << bit, self.candidates(room((mouth,))))
        self.assertEqual(0, self.candidates(room(mouths)), 'adjacent gaps without wall flanks are not ten independent mouths')
        for transform in (lambda x,y:(-x,y), lambda x,y:(x,-y), lambda x,y:(y,x), lambda x,y:(x+1,y)):
            self.assertEqual(0, self.candidates(remap(split_shadow(), transform)) & 1)
        for field, value in (('state', 0), ('state', 1), ('abi_version', 2), ('struct_size', C.sizeof(Scene)-1),
                             ('gold_state', 0), ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = split_shadow(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene) & 1)
        scene = split_shadow(); set_cell(scene, 8, 1, GOLD)
        self.assertEqual(0, self.candidates(scene) & 1)
        scene = split_shadow(); set_cell(scene, 8, 1, ITEM)
        self.assertEqual(0, self.candidates(scene) & 1)
        scene = split_shadow(); scene.tiles[offset(8, 1)] = 7
        self.assertEqual(0, self.candidates(scene) & 1)
