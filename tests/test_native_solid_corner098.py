"""A visible exterior fringe around an opaque upper-left corner merits a peek.

TEST097 actual2 capture135 is the labelled calibration source. These procedural
Scenes exercise the visible topology and input-free planner; they do not imply
an unseen shop, authorize digging, or reconstruct future iPhone responses.
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

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
WALLS = ((-3, -3), (-2, -3), (-1, -3), (-3, -2), (-3, -1))
CENTRE = ((-1, -1), (0, -1), (-1, 0), (0, 0))
INNER = ((-2, -2), (-2, -1))
MOUTH = (-3, -2)
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class SolidScene098(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32),
                ('state', C.c_int32), ('restart_label', C.c_int32), ('gold_state', C.c_int32),
                ('gold_peak', C.c_int32), ('goods', C.c_int32),
                ('tiles', C.c_uint8 * 230), ('protected_cells', C.c_uint8 * 230),
                ('signature', C.c_uint8 * 23296), ('fingerprint', C.c_uint8 * 48),
                ('beat_valid', C.c_int32), ('beat_remaining', C.c_double),
                ('beat_spacing', C.c_double), ('beat_center', C.c_double)]


class SolidDecision098(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def position098(x, y):
    return (y + 5) * 23 + x + 11


def paint098(scene, point, kind, protection=0):
    index = position098(*point)
    scene.tiles[index] = kind
    scene.protected_cells[index] = protection


def solid_corner098():
    scene = SolidScene098(abi_version=1, struct_size=C.sizeof(SolidScene098), state=2, gold_state=1)
    for point in CENTRE + INNER + ((-4, -3),):
        paint098(scene, point, FLOOR)
    for point in WALLS:
        paint098(scene, point, DIRT)
    return scene


def transform098(source, operation):
    result = SolidScene098.from_buffer_copy(bytes(source))
    result.tiles[:] = bytes(230)
    result.protected_cells[:] = bytes(230)
    for y in range(-5, 5):
        for x in range(-11, 12):
            target = operation(x, y)
            if -11 <= target[0] <= 11 and -5 <= target[1] <= 4:
                at = position098(x, y)
                paint098(result, target, source.tiles[at], source.protected_cells[at])
    return result


def both_profiles098(method):
    def run(self):
        for profile, library in self.libraries.items():
            with self.subTest(profile=profile):
                self.lib = library
                method(self)
    return run


class NativeSolidCorner098Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='solid-corner098-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.directory.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE/'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[profile] = library = C.CDLL(str(target))
            library.ng2_passage_candidates.argtypes = [C.POINTER(SolidScene098)]
            library.ng2_passage_candidates.restype = C.c_uint32
            library.ng2_choose_passage.argtypes = [C.POINTER(SolidScene098), C.c_int32, C.c_int32,
                                                  C.c_int32, C.c_int32, C.POINTER(SolidDecision098)]
            library.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def candidates(self, source):
        scene = SolidScene098.from_buffer_copy(bytes(source))
        before = bytes(scene)
        answer = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'hypotheses cannot relabel visible or UNKNOWN terrain')
        return answer

    def choose(self, source, x=0, y=0):
        scene = SolidScene098.from_buffer_copy(bytes(source))
        before = bytes(scene)
        out = SolidDecision098(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(out))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(out, name) for name, _ in SolidDecision098._fields_)

    @both_profiles098
    def test_solid_corner_exterior_floor_adds_only_fixed_left_upper_hypothesis(self):
        for kinds in product((DIRT, STONE), repeat=len(WALLS)):
            scene = solid_corner098()
            for point, kind in zip(WALLS, kinds):
                paint098(scene, point, kind)
            self.assertEqual(32, self.candidates(scene),
                             'opaque corner plus visible exterior fringe needs a closer observed-FLOOR view')
            self.assertEqual(UNKNOWN, scene.tiles[position098(-4, -2)])
            self.assertEqual((4, (1, 10, -2, -2, FLOOR)), self.choose(scene))

    @both_profiles098
    def test_each_positive_corner_wall_exterior_and_hidden_front_is_required(self):
        self.assertEqual(32, self.candidates(solid_corner098()))
        for point in WALLS:
            for kind in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
                scene = solid_corner098(); paint098(scene, point, kind)
                if point == MOUTH and kind == FLOOR:
                    self.assertEqual(32, self.candidates(scene), 'the older normal two-flank FLOOR mouth stays valid')
                else:
                    self.assertEqual(0, self.candidates(scene) & 32)
        for point in ((-4, -3), (-2, -2)):
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                scene = solid_corner098(); paint098(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 32)
        for kind in (FLOOR, GOLD, STONE, DIRT, DOOR, ITEM):
            scene = solid_corner098(); paint098(scene, (-4, -2), kind)
            self.assertEqual(0, self.candidates(scene) & 32)

    @both_profiles098
    def test_short_existing_floor_vantage_and_all_protections_are_required(self):
        self.assertEqual(32, self.candidates(solid_corner098()))
        for point in CENTRE:
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                scene = solid_corner098(); paint098(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 32)
        scene = solid_corner098(); paint098(scene, (-2, -1), UNKNOWN)
        self.assertEqual(0, self.candidates(scene) & 32, 'no short observed floor vantage')
        scene = solid_corner098(); paint098(scene, (-2, -1), UNKNOWN); paint098(scene, (-1, -2), FLOOR)
        self.assertEqual(32, self.candidates(scene), 'the existing alternate upper three-step vantage is valid')
        for point in WALLS + CENTRE + INNER + ((-4, -3), (-4, -2), (8, 1)):
            scene = solid_corner098(); scene.protected_cells[position098(*point)] = 1
            self.assertEqual(0, self.candidates(scene) & 32)
        detour = solid_corner098()
        for point in ((-1, 0), (-1, -1)):
            paint098(detour, point, UNKNOWN)
        for point in ((0, 1), (-1, 1), (-2, 1), (-2, 0)):
            paint098(detour, point, FLOOR)
        self.assertGreater(self.choose(detour)[0], 4)
        self.assertEqual(0, self.candidates(detour) & 32, 'a longer detour does not expand the local witness')

    @both_profiles098
    def test_fixed_mouth_approach_uses_four_floor_steps_and_holds_at_solid_corner(self):
        terrain = solid_corner098(); frozen = bytes(terrain)
        self.assertEqual(32, self.candidates(terrain))
        x = y = 0
        for remaining in range(4, 0, -1):
            scene = transform098(terrain, lambda a, b: (a-x, b-y))
            length, choice = self.choose(scene, x, y)
            direction, reason, tx, ty, obstacle = choice
            self.assertEqual((remaining, 10, -2-x, -2-y, FLOOR), (length, reason, tx, ty, obstacle))
            dx, dy = DIRECTIONS[direction]
            self.assertEqual(FLOOR, scene.tiles[position098(dx, dy)])
            self.assertEqual(0, scene.protected_cells[position098(dx, dy)])
            x += dx; y += dy
        self.assertEqual((-2, -2), (x, y))
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(transform098(terrain, lambda a, b: (a-x, b-y)), x, y))
        self.assertEqual(frozen, bytes(terrain), 'the wall remains opaque; no future visibility or hidden gold is invented')

    @both_profiles098
    def test_state_goods_gold_item_and_noncanonical_orientations_keep_old_scope(self):
        self.assertEqual(32, self.candidates(solid_corner098()))
        for field, value in (('state', 0), ('state', 1), ('abi_version', 2),
                             ('struct_size', C.sizeof(SolidScene098)-1), ('gold_state', 0),
                             ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = solid_corner098(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene))
        for kind in (GOLD, ITEM, 7):
            scene = solid_corner098(); paint098(scene, (8, 1), kind)
            self.assertEqual(0, self.candidates(scene))
        for operation in (lambda x, y: (-x, y), lambda x, y: (x, -y),
                          lambda x, y: (y, x), lambda x, y: (x+1, y)):
            self.assertEqual(0, self.candidates(transform098(solid_corner098(), operation)))
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))

    @both_profiles098
    def test_old_candidate_shapes_and_masks_are_unchanged(self):
        for make, expected in ((shadow094.shadow, 1), (split095.split_shadow, 1),
                               (supported084.supported, 64), (corner097.upper_shadow097, 1),
                               (corner097.outside_elbow097, 32)):
            self.assertEqual(expected, self.candidates(make()))
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
