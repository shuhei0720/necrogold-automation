"""TEST094 marked upper-left shadow passage: retain UNKNOWN, approach FLOOR.

The user marks TEST093 capture156 as an upward passage hypothesis. These
procedural maps preserve its visible wall/unknown/floor topology. They do not
reconstruct absent captures152-155 or reveal an unseen shop beyond the mouth.
"""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_passage_navigation072 import Scene, Decision, room, set_cell, offset, shifted
from tests.test_native_supported_mouth084 import supported
from tests.test_native_corner_vantage086 import corner

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
MOUTH = (-2, -3)
DARK = (MOUTH, (-2, -4), (-2, -2), (-1, -2))
COLUMN = tuple((-3, y) for y in range(-4, 2))
ROOM_FLOOR = tuple((x, y) for y in (-1, 0) for x in range(-2, 1))


def shadow():
    scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=1)
    for p in COLUMN + ((-1, -3),):
        set_cell(scene, *p, DIRT)
    for p in ROOM_FLOOR:
        set_cell(scene, *p, FLOOR)
    return scene


def remap(source, transform):
    result = Scene.from_buffer_copy(bytes(source))
    result.tiles[:] = bytes(230)
    result.protected_cells[:] = bytes(230)
    for y in range(-5, 5):
        for x in range(-11, 12):
            tx, ty = transform(x, y)
            if -11 <= tx <= 11 and -5 <= ty <= 4:
                i = offset(x, y)
                set_cell(result, tx, ty, source.tiles[i], source.protected_cells[i])
    return result


def profiles(method):
    def run(self):
        for name, library in self.libraries.items():
            with self.subTest(profile=name):
                self.lib = library
                method(self)
    return run


class NativeShadowPassage094Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='shadow-passage094-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.temp.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[profile] = lib = C.CDLL(str(target))
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
        result = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'a passage hypothesis must not relabel UNKNOWN')
        return result

    def choose(self, scene, x=0, y=0):
        before = bytes(scene)
        out = Decision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(out, name) for name, _ in out._fields_)

    @profiles
    def test_marked_shadow_shape_keeps_unknown_and_adds_only_fixed_upper_left_mouth(self):
        scene = shadow()
        self.assertEqual((UNKNOWN,) * 4, tuple(scene.tiles[offset(*p)] for p in DARK))
        self.assertEqual((DIRT,) * 7, tuple(scene.tiles[offset(*p)] for p in COLUMN + ((-1, -3),)))
        self.assertEqual((FLOOR,) * 6, tuple(scene.tiles[offset(*p)] for p in ROOM_FLOOR))
        self.assertEqual((3, (1, 10, -2, -1, FLOOR)), self.choose(scene),
                         'the unchanged chooser already has a current observed FLOOR vantage')
        self.assertEqual(1, self.candidates(scene),
                         'the marked tall-wall shadow hypothesis must survive without fabricating floor or gold')

    @profiles
    def test_tall_brown_column_and_opposite_roof_wall_are_required(self):
        for p in COLUMN + ((-1, -3),):
            for kind in (UNKNOWN, FLOOR, GOLD, STONE, DOOR, ITEM):
                with self.subTest(position=p, material=kind):
                    scene = shadow(); set_cell(scene, *p, kind)
                    # A newly observed FLOOR in the left wall can satisfy
                    # an old two-flank mouth; keep that independent bit.
                    expected = 1 << (p[1]+7) if kind == FLOOR and p in ((-3, -1), (-3, 0)) else 0
                    self.assertEqual(expected, self.candidates(scene))
        scene = shadow()
        for p in COLUMN:
            set_cell(scene, *p, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'an unobserved black column is not a tall observed wall')

    @profiles
    def test_four_dark_cells_and_observed_short_floor_vantage_are_required(self):
        for p in DARK:
            for kind in (FLOOR, GOLD, STONE, DIRT, DOOR, ITEM):
                with self.subTest(position=p, material=kind):
                    scene = shadow(); set_cell(scene, *p, kind)
                    self.assertEqual(0, self.candidates(scene))
        for p in ROOM_FLOOR:
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                with self.subTest(position=p, material=kind):
                    scene = shadow(); set_cell(scene, *p, kind)
                    self.assertEqual(0, self.candidates(scene))
        scene = shadow()
        set_cell(scene, -1, 0, UNKNOWN)
        set_cell(scene, -1, -1, UNKNOWN)
        for p in ((0, 1), (-1, 1), (-2, 1)):
            set_cell(scene, *p, FLOOR)
        self.assertEqual((5, (4, 10, -2, -1, FLOOR)), self.choose(scene))
        self.assertEqual(0, self.candidates(scene), 'a five-step detour is outside this limited hypothesis')
        set_cell(scene, -2, 0, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'an isolated observed endpoint is not approach authority')

    @profiles
    def test_fixed_world_mouth_moves_only_on_observed_floor_then_holds(self):
        terrain = shadow(); x = y = steps = 0
        self.assertEqual(1, self.candidates(terrain))
        while (x, y) != (-2, -1):
            scene = shifted(terrain, x, y)
            length, choice = self.choose(scene, x, y)
            self.assertGreater(length, 0)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((10, -2-x, -1-y, FLOOR), (reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
            self.assertEqual(0, scene.protected_cells[offset(dx, dy)])
            x += dx; y += dy; steps += 1
            self.assertLessEqual(steps, 3)
        self.assertEqual(3, steps)
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(shifted(terrain, x, y), x, y),
                         'the unchanged map gives no step into the still UNKNOWN inboard')
        self.assertEqual((UNKNOWN,) * 4, tuple(terrain.tiles[offset(*p)] for p in DARK))

    @profiles
    def test_black_gaps_other_sides_goods_gold_protection_and_invalid_scenes_fail_closed(self):
        for transform in (lambda x, y: (-x, y), lambda x, y: (y, x),
                          lambda x, y: (x, -y), lambda x, y: (x+1, y)):
            scene = remap(shadow(), transform)
            self.assertEqual(0, self.candidates(scene), 'the new hypothesis belongs only to the marked fixed upper-left corner')
        scene = shadow()
        for p in COLUMN + ((-1, -3),):
            set_cell(scene, *p, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'black gaps alone do not authorize exploration')
        for p in ((0, 0), (-1, 0), (-2, -1), *DARK, *COLUMN, (-1, -3), (8, 1)):
            scene = shadow(); scene.protected_cells[offset(*p)] = 1
            self.assertEqual(0, self.candidates(scene))
        for p in ((8, 1), (-1, -1)):
            for kind in (ITEM, GOLD):
                scene = shadow(); set_cell(scene, *p, kind)
                self.assertEqual(0, self.candidates(scene))
        for field, value in (('state', 0), ('state', 1), ('abi_version', 2),
                             ('struct_size', C.sizeof(Scene)-1), ('gold_state', 0),
                             ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = shadow(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene))
        scene = shadow(); scene.protected_cells[offset(8, 1)] = 2
        self.assertEqual(0, self.candidates(scene))
        scene = shadow(); set_cell(scene, 8, 1, 7)
        self.assertEqual(0, self.candidates(scene))
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))

    @profiles
    def test_original_ten_mouths_supported_mouths_and_corner_masks_remain_unchanged(self):
        for side in range(2):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for outside in (UNKNOWN, FLOOR):
                    for kind in (FLOOR, UNKNOWN):
                        scene = room([mouth], outside=outside, mouth_kind=kind)
                        expected = 0 if kind == UNKNOWN and outside == UNKNOWN else 1 << (side*5+k+2)
                        self.assertEqual(expected, self.candidates(scene))
                self.assertEqual(1 << (side*5+k+2), self.candidates(supported(mouth)))
                self.assertEqual(1 << (side*5+k+2) if abs(k) == 2 else 0,
                                 self.candidates(corner(mouth)))
