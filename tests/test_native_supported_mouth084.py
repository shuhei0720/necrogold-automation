"""TEST084 observed FLOOR mouth/outside with one genuinely unknown flank."""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_passage_navigation072 import Scene, Decision, room, set_cell, offset, shifted

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def supported(mouth=(-3, -1), unknown_side=1, wall=DIRT, walls=3):
    scene = room([mouth])
    side = mouth[0] == -3
    k = mouth[1] if side else mouth[0]
    unknown = k + unknown_side
    known = k - unknown_side
    supports = [known] + [j for j in range(-3, 4) if j not in (known, unknown, k)]
    for j in range(-3, 4):
        set_cell(scene, -3 if side else j, j if side else -3, UNKNOWN)
    for j in supports[:walls]:
        set_cell(scene, -3 if side else j, j if side else -3, wall)
    set_cell(scene, *mouth, FLOOR)
    return scene


def profiles(method):
    def run(self):
        for profile, library in self.libraries.items():
            with self.subTest(profile=profile):
                self.lib = library
                method(self)
    return run


class NativeSupportedMouth084Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='supported-mouth084-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.temp.name) / (profile+'.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[profile] = lib = C.CDLL(str(target))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)]
            lib.ng2_passage_candidates.restype = C.c_uint32
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                                             C.c_int32, C.c_int32, C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidates(self, scene):
        before = bytes(scene)
        result = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene))
        return result

    def choose(self, scene, x, y, mouth):
        before = bytes(scene)
        decision = Decision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *mouth, C.byref(decision))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(decision, k) for k, _ in decision._fields_)

    @profiles
    def test_observed_outside_floor_with_one_unknown_flank_selects_fixed_upper_left_mouths(self):
        source = supported()
        self.assertEqual((FLOOR, FLOOR, DIRT, UNKNOWN), tuple(source.tiles[offset(*p)]
                         for p in ((-3, -1), (-4, -1), (-3, -2), (-3, 0))))
        self.assertEqual(3, sum(source.tiles[offset(-3, k)] in (DIRT, STONE) for k in range(-3, 4)))
        self.assertEqual(1 << 6, self.candidates(source),
                         'current mouth/outside floor with a supported wall must not be discarded')
        self.assertEqual((5, (1, 10, -4, -1, FLOOR)), self.choose(source, 0, 0, (-3, -1)))
        for side in range(2):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for unknown_side in (-1, 1):
                    for wall in (DIRT, STONE):
                        with self.subTest(mouth=mouth, unknown_side=unknown_side, wall=wall):
                            scene = supported(mouth, unknown_side, wall)
                            self.assertEqual(1 << (side*5+k+2), self.candidates(scene))
                            self.assertEqual(FLOOR, self.choose(scene, 0, 0, mouth)[1][4])

    @profiles
    def test_missing_flank_needs_outside_floor_and_three_current_walls(self):
        for outside in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
            scene = supported(); set_cell(scene, -4, -1, outside)
            self.assertEqual(0, self.candidates(scene))
        for flank in (FLOOR, GOLD, DOOR, ITEM):
            scene = supported(); set_cell(scene, -3, 0, flank)
            self.assertEqual(0, self.candidates(scene))
        scene = supported(); set_cell(scene, -3, -2, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'two unobserved flanks are not wall support')
        self.assertEqual(0, self.candidates(supported(walls=2)))
        self.assertEqual(1 << 6, self.candidates(supported(walls=3)))
        for mouth in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
            scene = supported(); set_cell(scene, -3, -1, mouth)
            if mouth != UNKNOWN:
                self.assertEqual(0, self.candidates(scene))
            else:
                self.assertEqual(1 << 6, self.candidates(scene), 'the existing UNKNOWN-mouth branch remains valid')

    @profiles
    def test_only_current_safe_floor_paths_authorize_approach(self):
        terrain = supported(); mouth = (-3, -1); goal = (-4, -1)
        x = y = 0
        for _ in range(6):
            scene = shifted(terrain, x, y)
            length, decision = self.choose(scene, x, y, mouth)
            if (x, y) == goal:
                self.assertEqual((0, (0, 0, 0, 0, 0)), (length, decision))
                break
            self.assertGreater(length, 0)
            direction, reason, tx, ty, obstacle = decision
            self.assertEqual((10, goal[0]-x, goal[1]-y, FLOOR), (reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
            self.assertEqual(0, scene.protected_cells[offset(dx, dy)])
            x += dx; y += dy
        self.assertEqual(goal, (x, y))
        for position in ((0, 0), (-1, 0), (-3, -1), (-4, -1), (-4, -2)):
            scene = supported(); scene.protected_cells[offset(*position)] = 1
            self.assertEqual(0, self.candidates(scene))
        scene = supported()
        for k in range(-2, 3): set_cell(scene, -2, k, STONE)
        self.assertEqual(0, self.candidates(scene), 'the mouth needs an observed reachable inboard')

    @profiles
    def test_gold_goods_invalid_scenes_and_ordinary_right_down_exits_stay_out(self):
        for field, value in (('state', 0), ('state', 1), ('abi_version', 2),
                             ('struct_size', C.sizeof(Scene)-1), ('gold_state', 0),
                             ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = supported(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene))
        for position, kind in (((8, 1), GOLD), ((0, 0), UNKNOWN), ((0, 0), DIRT), ((8, 1), 7)):
            scene = supported(); set_cell(scene, *position, kind)
            self.assertEqual(0, self.candidates(scene))
        scene = supported(); scene.protected_cells[offset(8, 1)] = 2
        self.assertEqual(0, self.candidates(scene))
        scene = room()
        for p in ((3, 0), (4, 0), (0, 3), (0, 4)): set_cell(scene, *p, FLOOR)
        set_cell(scene, 3, 1, UNKNOWN); set_cell(scene, 1, 3, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'the new shape does not extend to ordinary right/down exits')
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))

    @profiles
    def test_old_two_wall_and_shadowed_mouth_masks_and_source_bytes_are_preserved(self):
        for mouth in ((-2, -3), (2, -3), (-3, 0), (-3, 2)):
            side = mouth[0] == -3; k = mouth[1] if side else mouth[0]
            for outside in (UNKNOWN, FLOOR):
                for kind in (FLOOR, UNKNOWN):
                    scene = room([mouth], outside=outside, mouth_kind=kind)
                    expected = 0 if kind == UNKNOWN and outside == UNKNOWN else 1 << (side*5+k+2)
                    self.assertEqual(expected, self.candidates(scene))
        scene = supported(); snapshot = deepcopy(scene)
        self.candidates(scene); self.choose(scene, 0, 0, (-3, -1))
        self.assertEqual(bytes(snapshot), bytes(scene), 'UNKNOWN flank and original evidence bytes remain untouched')
        self.assertEqual(UNKNOWN, scene.tiles[offset(-3, 0)])
