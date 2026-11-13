"""TEST097 observed corner witnesses; no inferred floor or future game views.

TEST096 bc2396 captures28/52 and6f62db captures130/254 label fixed upper-left
passage candidates. These procedural witnesses express their shared observed
boundary geometry. The three-step vantage is not the total approach length.
"""
import ctypes as C
from itertools import combinations, product
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_passage_navigation072 as original_mouths
from tests import test_native_supported_mouth084 as supported_mouths
from tests import test_native_corner_vantage086 as original_corners
from tests import test_native_shadow_passage094 as original_shadow
from tests import test_native_split_shadow095 as original_split

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)
DIRECTIONS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
CENTRE = ((-1, -1), (0, -1), (-1, 0), (0, 0))
INSIDE = ((-2, -2), (-2, -1), (-1, -2))
ROOF = tuple((x, -3) for x in range(-1, 3))
LEFT_BOUNDARY = tuple((-3, y) for y in range(-3, 4))


class OccludedScene(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ('abi_version', 'struct_size')] + [
        (name, C.c_int32) for name in ('state', 'restart_label', 'gold_state', 'gold_peak', 'goods')] + [
        ('tiles', C.c_uint8 * 230), ('protected_cells', C.c_uint8 * 230),
        ('signature', C.c_uint8 * 23296), ('fingerprint', C.c_uint8 * 48),
        ('beat_valid', C.c_int32), ('beat_remaining', C.c_double),
        ('beat_spacing', C.c_double), ('beat_center', C.c_double)]


class OccludedDecision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
                ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def position(x, y):
    return (y + 5) * 23 + x + 11


def paint(scene, point, kind, protected=0):
    index = position(*point)
    scene.tiles[index] = kind
    scene.protected_cells[index] = protected


def upper_shadow097(roof=((-1, -3), (1, -3)), left=((-3, 0), (-3, 1))):
    scene = OccludedScene(abi_version=1, struct_size=C.sizeof(OccludedScene), state=2, gold_state=1)
    for point in CENTRE + ((-2, -1), (-1, -2)):
        paint(scene, point, FLOOR)
    for point in tuple(roof) + tuple(left) + ((-3, -4),):
        paint(scene, point, DIRT)
    return scene


def outside_elbow097():
    scene = OccludedScene(abi_version=1, struct_size=C.sizeof(OccludedScene), state=2, gold_state=1)
    for point in CENTRE + ((-2, -1), (-2, -2), (-3, -2), (-4, -3)):
        paint(scene, point, FLOOR)
    for point in ((-3, -3), (-2, -3), (-1, -3)):
        paint(scene, point, DIRT)
    return scene


def transform097(source, operation):
    result = OccludedScene.from_buffer_copy(bytes(source))
    result.tiles[:] = bytes(230)
    result.protected_cells[:] = bytes(230)
    for y in range(-5, 5):
        for x in range(-11, 12):
            target = operation(x, y)
            if -11 <= target[0] <= 11 and -5 <= target[1] <= 4:
                paint(result, target, source.tiles[position(x, y)], source.protected_cells[position(x, y)])
    return result


def both_profiles(method):
    def run(self):
        for profile, library in self.libraries.items():
            with self.subTest(profile=profile):
                self.lib = library
                method(self)
    return run


class NativeOccludedCorner097Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='occluded-corner097-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            target = Path(cls.directory.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(target)], check=True)
            cls.libraries[profile] = library = C.CDLL(str(target))
            library.ng2_passage_candidates.argtypes = [C.POINTER(OccludedScene)]
            library.ng2_passage_candidates.restype = C.c_uint32
            library.ng2_choose_passage.argtypes = [C.POINTER(OccludedScene), C.c_int32, C.c_int32,
                                                  C.c_int32, C.c_int32, C.POINTER(OccludedDecision)]
            library.ng2_choose_passage.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def candidates(self, source):
        scene = OccludedScene.from_buffer_copy(bytes(source))
        before = bytes(scene)
        mask = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene), 'candidate detection cannot relabel observed or UNKNOWN cells')
        return mask

    def choose(self, scene, x, y, mouth):
        before = bytes(scene)
        decision = OccludedDecision(99, 99, 99, 99, 99)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *mouth, C.byref(decision))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(decision, name) for name, _ in decision._fields_)

    @both_profiles
    def test_upper_shadow_retains_floor_or_unknown_inside_and_mixed_opaque_wall_support(self):
        for roof in combinations(ROOF, 2):
            for left in combinations(LEFT_BOUNDARY, 2):
                scene = upper_shadow097(roof, left)
                expected = 1 if any(point[0] >= 1 for point in roof) else 0
                # Floor already visible inboard is useful evidence, not a
                # reason to insist on the exact four dark cells of TEST094.
                for inside in product((UNKNOWN, FLOOR), repeat=3):
                    if inside[1:] == (UNKNOWN, UNKNOWN):
                        continue
                    for point, kind in zip(INSIDE, inside):
                        paint(scene, point, kind)
                    for point in tuple(roof)[::2] + tuple(left)[::2] + ((-3, -4),):
                        paint(scene, point, STONE)
                    self.assertEqual(expected, self.candidates(scene),
                                     'bit0 needs roof support extending into the opposite room half')
                    self.assertEqual((UNKNOWN, UNKNOWN), tuple(scene.tiles[position(*p)] for p in ((-2, -3), (-2, -4))))

    @both_profiles
    def test_left_elbow_uses_diagonal_outside_floor_without_inventing_direct_outside_floor(self):
        for kinds in product((DIRT, STONE), repeat=3):
            scene = outside_elbow097()
            for point, kind in zip(((-3, -3), (-2, -3), (-1, -3)), kinds):
                paint(scene, point, kind)
            self.assertEqual((FLOOR, UNKNOWN, FLOOR, UNKNOWN), tuple(scene.tiles[position(*p)] for p in
                             ((-3, -2), (-4, -2), (-4, -3), (-3, -1))))
            self.assertEqual(32, self.candidates(scene), 'the diagonal outside observation must retain the fixed left bit5')

    @both_profiles
    def test_upper_requires_independent_outer_roof_and_left_boundary_positive_walls(self):
        self.assertEqual(1, self.candidates(upper_shadow097()))
        for kind in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
            scene = upper_shadow097(); paint(scene, (-3, -4), kind)
            self.assertEqual(0, self.candidates(scene) & 1)
        for group in (ROOF, LEFT_BOUNDARY):
            for survivor in (None, *group):
                scene = upper_shadow097()
                for point in group:
                    paint(scene, point, DIRT if point == survivor else UNKNOWN)
                self.assertEqual(0, self.candidates(scene) & 1, 'a single boundary wall is not a supported portal')
        scene = upper_shadow097(roof=((-1, -3), (0, -3)))
        self.assertEqual(0, self.candidates(scene) & 1,
                         'two near roof cells do not prove the observed opposite-room boundary')

    @both_profiles
    def test_upper_dark_portal_and_inside_materials_do_not_authorize_walls_doors_or_hidden_floor(self):
        self.assertEqual(1, self.candidates(upper_shadow097()))
        for point in ((-2, -3), (-2, -4)):
            for kind in (FLOOR, GOLD, STONE, DIRT, DOOR, ITEM):
                scene = upper_shadow097(); paint(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 1)
        for point in INSIDE:
            for kind in (GOLD, STONE, DIRT, DOOR, ITEM):
                scene = upper_shadow097(); paint(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 1)
        scene = upper_shadow097()
        paint(scene, (-2, -1), UNKNOWN); paint(scene, (-1, -2), UNKNOWN)
        self.assertEqual(0, self.candidates(scene) & 1, 'neither short floor vantage is observed')

    @both_profiles
    def test_elbow_requires_each_observed_turn_wall_floor_and_unknown_direct_outside(self):
        self.assertEqual(32, self.candidates(outside_elbow097()))
        for point in ((-3, -2), (-4, -3), (-2, -2)):
            for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                scene = outside_elbow097(); paint(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 32)
        for point in ((-3, -3), (-2, -3), (-1, -3)):
            for kind in (UNKNOWN, FLOOR, GOLD, DOOR, ITEM):
                scene = outside_elbow097(); paint(scene, point, kind)
                self.assertEqual(0, self.candidates(scene) & 32)
        for kind in (FLOOR, GOLD, STONE, DIRT, DOOR, ITEM):
            scene = outside_elbow097(); paint(scene, (-4, -2), kind)
            self.assertEqual(0, self.candidates(scene) & 32)
        for kind in (FLOOR, GOLD, DOOR, ITEM):
            scene = outside_elbow097(); paint(scene, (-3, -1), kind)
            self.assertEqual(0, self.candidates(scene) & 32)
        for kind in (DIRT, STONE):
            scene = outside_elbow097(); paint(scene, (-3, -1), kind)
            self.assertEqual(32, self.candidates(scene), 'the unchanged original two-flank observed mouth remains valid')

    @both_profiles
    def test_fixed_world_chooser_advances_only_existing_floor_and_holds_before_unknown(self):
        for terrain, mouth, steps in ((upper_shadow097(), (-2, -3), 3),
                                      (outside_elbow097(), (-3, -2), 5)):
            if mouth == (-2, -3):
                paint(terrain, (-2, -2), FLOOR)
                steps = 4
            x = y = 0
            for remaining in range(steps, 0, -1):
                scene = transform097(terrain, lambda a, b: (a-x, b-y))
                length, choice = self.choose(scene, x, y, mouth)
                direction, reason, _, _, obstacle = choice
                self.assertEqual(remaining, length)
                self.assertEqual((10, FLOOR), (reason, obstacle))
                dx, dy = DIRECTIONS[direction]
                self.assertEqual(FLOOR, scene.tiles[position(dx, dy)])
                self.assertEqual(0, scene.protected_cells[position(dx, dy)])
                x += dx; y += dy
            scene = transform097(terrain, lambda a, b: (a-x, b-y))
            self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(scene, x, y, mouth))
            outside = (mouth[0], mouth[1]-1) if mouth[1] == -3 else (mouth[0]-1, mouth[1])
            self.assertEqual(UNKNOWN, terrain.tiles[position(*outside)])

    @both_profiles
    def test_scene_central_floor_goods_gold_all_protection_and_abi_guards_are_preserved(self):
        for make in (upper_shadow097, outside_elbow097):
            self.assertEqual(1 if make is upper_shadow097 else 32, self.candidates(make()))
            for point in CENTRE:
                for kind in (UNKNOWN, GOLD, STONE, DIRT, DOOR, ITEM):
                    scene = make(); paint(scene, point, kind)
                    self.assertEqual(0, self.candidates(scene))
            for point in ((8, 1), (0, 0), (-2, -1), (-1, -2), (-3, -4), (-4, -3)):
                scene = make(); scene.protected_cells[position(*point)] = 1
                self.assertEqual(0, self.candidates(scene))
            for kind in (GOLD, ITEM, 7):
                scene = make(); paint(scene, (8, 1), kind)
                self.assertEqual(0, self.candidates(scene))
            for field, value in (('state', 0), ('state', 1), ('abi_version', 2),
                                 ('struct_size', C.sizeof(OccludedScene)-1), ('gold_state', 0),
                                 ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)):
                scene = make(); setattr(scene, field, value)
                self.assertEqual(0, self.candidates(scene))
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))

    @both_profiles
    def test_old_mouths_shadows_corners_and_unrelated_sides_keep_original_masks(self):
        self.assertEqual(1, self.candidates(original_shadow.shadow()))
        self.assertEqual(1, self.candidates(original_split.split_shadow()))
        self.assertEqual(64, self.candidates(supported_mouths.supported()))
        for side in range(2):
            for k in range(-2, 3):
                mouth = (-3, k) if side else (k, -3)
                for outside in (UNKNOWN, FLOOR):
                    for kind in (FLOOR, UNKNOWN):
                        scene = original_mouths.room([mouth], outside=outside, mouth_kind=kind)
                        expected = 0 if kind == UNKNOWN and outside == UNKNOWN else 1 << (side*5+k+2)
                        self.assertEqual(expected, self.candidates(scene))
                if abs(k) == 2:
                    self.assertEqual(1 << (side*5+k+2), self.candidates(original_corners.corner(mouth)))
        for make in (upper_shadow097, outside_elbow097):
            for operation in (lambda x, y: (-x, y), lambda x, y: (x, -y),
                              lambda x, y: (y, x), lambda x, y: (x+1, y)):
                self.assertEqual(0, self.candidates(transform097(make(), operation)), 'the new witness is fixed to the marked corner')


if __name__ == '__main__':
    unittest.main()
