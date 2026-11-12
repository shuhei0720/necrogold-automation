"""TEST086 corner passage hypotheses approach observed FLOOR, keeping UNKNOWN.

TEST085 run 10554662 capture 93 labels an observed left mouth/outside and two
walls, with a genuinely UNKNOWN inboard. These public Scene maps preserve that
topology; later views are procedural and are not missing device responses.
"""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_passage_navigation072 import Scene, Decision, room, set_cell, offset, shifted

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def geometry(mouth):
    side = mouth[0] == -3
    k = mouth[1] if side else mouth[0]
    dx, dy = (-1, 0) if side else (0, -1)
    inboard = mouth[0]-dx, mouth[1]-dy
    outside = mouth[0]+dx, mouth[1]+dy
    step = -1 if k > 0 else 1
    endpoint = (inboard[0], inboard[1]+step) if side else (inboard[0]+step, inboard[1])
    flanks = ((mouth[0]+dy, mouth[1]-dx), (mouth[0]-dy, mouth[1]+dx))
    return side, k, inboard, outside, endpoint, flanks


def corner(mouth=(-3, -2), wall=DIRT):
    scene = room([mouth])
    side, _, inboard, _, _, _ = geometry(mouth)
    for j in range(-3, 4):
        if (-3, j) != mouth and side:
            set_cell(scene, -3, j, wall)
        elif (j, -3) != mouth and not side:
            set_cell(scene, j, -3, wall)
    set_cell(scene, *inboard, UNKNOWN)
    return scene


def profiles(method):
    def run(self):
        for name, library in self.libraries.items():
            with self.subTest(profile=name):
                self.lib = library
                method(self)
    return run


class NativeCornerVantage086Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='corner-vantage086-')
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
            lib.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidates(self, scene):
        before = bytes(scene)
        result = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'candidate hypotheses must not relabel UNKNOWN')
        return result

    def choose(self, scene, x, y, mouth):
        before = bytes(scene)
        choice = Decision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *mouth, C.byref(choice))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(choice, name) for name, _ in choice._fields_)

    @profiles
    def test_unknown_inboard_keeps_observed_corner_candidate_for_safe_vantage(self):
        scene = corner()
        self.assertEqual((FLOOR, FLOOR, DIRT, DIRT, UNKNOWN, FLOOR),
                         tuple(scene.tiles[offset(*p)] for p in
                               ((-3, -2), (-4, -2), (-3, -3), (-3, -1), (-2, -2), (-2, -1))))
        self.assertEqual(6, sum(scene.tiles[offset(-3, j)] in (DIRT, STONE) for j in range(-3, 4)))
        self.assertEqual((3, (1, 10, -2, -1, FLOOR)), self.choose(scene, 0, 0, (-3, -2)),
                         'the existing public chooser already reaches the observed inward vantage in three steps')
        self.assertEqual(UNKNOWN, scene.tiles[offset(-2, -2)])
        self.assertEqual(1 << 5, self.candidates(scene),
                         'observed mouth/outside and both walls merit a floor-only approach before rejecting this corner')

    @profiles
    def test_only_four_fixed_upper_left_corners_gain_the_new_hypothesis(self):
        for side in range(2):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for wall in (DIRT, STONE):
                    with self.subTest(mouth=mouth, wall=wall):
                        scene = corner(mouth, wall)
                        expected = 1 << (side*5+k+2) if abs(k) == 2 else 0
                        self.assertEqual(expected, self.candidates(scene))
        for mouth, outside, inboard in (((3, -2), (4, -2), (2, -2)),
                                         ((3, 2), (4, 2), (2, 2)),
                                         ((-2, 3), (-2, 4), (-2, 2)),
                                         ((2, 3), (2, 4), (2, 2))):
            scene = room()
            set_cell(scene, *mouth, FLOOR); set_cell(scene, *outside, FLOOR)
            set_cell(scene, *inboard, UNKNOWN)
            self.assertEqual(0, self.candidates(scene), 'ordinary right/down exits gain no exploration authority')

    @profiles
    def test_observed_mouth_outside_two_walls_and_unknown_inboard_are_all_required(self):
        for position in ((-3, -2), (-4, -2)):
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                with self.subTest(position=position, kind=kind):
                    scene = corner(); set_cell(scene, *position, kind)
                    self.assertEqual(0, self.candidates(scene))
        for kind in (GOLD, STONE, DIRT, DOOR, ITEM):
            scene = corner(); set_cell(scene, -2, -2, kind)
            self.assertEqual(0, self.candidates(scene))
        for position in ((-3, -3), (-3, -1)):
            for kind in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
                scene = corner(); set_cell(scene, *position, kind)
                self.assertEqual(0, self.candidates(scene))
        scene = corner()
        for j in (0, 1, 2, 3): set_cell(scene, -3, j, UNKNOWN)
        self.assertEqual(2, sum(scene.tiles[offset(-3, j)] in (DIRT, STONE) for j in range(-3, 4)))
        self.assertEqual(0, self.candidates(scene), 'the two flanks alone do not meet the three-wall support')
        set_cell(scene, -3, 0, STONE)
        self.assertEqual(1 << 5, self.candidates(scene))
        set_cell(scene, -2, -2, FLOOR)
        self.assertEqual(1 << 5, self.candidates(scene), 'the original reachable-inboard branch is retained')

    @profiles
    def test_vantage_requires_observed_shortest_three_step_route_and_clear_crosses(self):
        for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
            scene = corner(); set_cell(scene, -2, -1, kind)
            self.assertEqual(0, self.candidates(scene))
        scene = corner()
        for y in range(-2, 3):
            for x in range(-2, 3): set_cell(scene, x, y, UNKNOWN)
        for p in ((0, 0), (0, 1), (-1, 1), (-2, 1), (-2, 0), (-2, -1)):
            set_cell(scene, *p, FLOOR)
        self.assertEqual((5, (4, 10, -2, -1, FLOOR)), self.choose(scene, 0, 0, (-3, -2)))
        self.assertEqual(0, self.candidates(scene), 'a five-step detour is outside the fixed corner hypothesis')
        set_cell(scene, -2, 0, UNKNOWN)
        self.assertEqual(0, self.candidates(scene), 'an isolated visible endpoint is not a floor route')
        for position in ((0, 0), (-1, 0), (-3, -2), (-4, -2), (-5, -2),
                         (-2, -2), (-2, -3), (-1, -2), (-2, -1), (-2, 0)):
            scene = corner(); scene.protected_cells[offset(*position)] = 1
            self.assertEqual(0, self.candidates(scene), 'origin, route and mouth/inboard/outside crosses remain protected')
        scene = corner(); scene.protected_cells[offset(8, 1)] = 1
        self.assertEqual(1 << 5, self.candidates(scene), 'an unrelated protected cell does not grant or remove the local floor path')

    @profiles
    def test_fixed_world_mouth_approaches_only_floor_and_holds_until_a_new_observed_route(self):
        mouth = (-3, -2); terrain = corner(); x = y = steps = 0
        while (x, y) != (-2, -1):
            scene = shifted(terrain, x, y)
            length, choice = self.choose(scene, x, y, mouth)
            self.assertGreater(length, 0)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((10, -2-x, -1-y, FLOOR), (reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
            self.assertEqual(0, scene.protected_cells[offset(dx, dy)])
            x += dx; y += dy; steps += 1
            self.assertLessEqual(steps, 3)
        self.assertEqual(3, steps)
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(shifted(terrain, x, y), x, y, mouth),
                         'the UNKNOWN bridge is retained and never becomes a synthetic floor input')
        self.assertEqual(UNKNOWN, terrain.tiles[offset(-2, -2)])
        set_cell(terrain, -2, -2, FLOOR)  # Procedural later observation, not a reconstructed device frame.
        for _ in range(3):
            scene = shifted(terrain, x, y)
            length, choice = self.choose(scene, x, y, mouth)
            self.assertGreater(length, 0)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((10, -4-x, -2-y, FLOOR), (reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
            x += dx; y += dy
        self.assertEqual((-4, -2), (x, y))
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(shifted(terrain, x, y), x, y, mouth))

    @profiles
    def test_scene_guards_and_all_original_ten_mouth_branches_stay_unchanged(self):
        for field, value in (('state', 0), ('state', 1), ('abi_version', 2),
                             ('struct_size', C.sizeof(Scene)-1), ('gold_state', 0),
                             ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = corner(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene))
        for position, kind in (((8, 1), GOLD), ((0, 0), UNKNOWN), ((0, 0), DIRT), ((8, 1), 7)):
            scene = corner(); set_cell(scene, *position, kind)
            self.assertEqual(0, self.candidates(scene))
        scene = corner(); scene.protected_cells[offset(8, 1)] = 2
        self.assertEqual(0, self.candidates(scene))
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))
        for side in range(2):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for outside in (UNKNOWN, FLOOR):
                    for kind in (FLOOR, UNKNOWN):
                        scene = room([mouth], outside=outside, mouth_kind=kind)
                        expected = 0 if kind == UNKNOWN and outside == UNKNOWN else 1 << (side*5+k+2)
                        self.assertEqual(expected, self.candidates(scene), 'existing candidate branches retain their original masks')
