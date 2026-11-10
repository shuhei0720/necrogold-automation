"""TEST072 side-passage navigation through observed FLOOR only.

The twelve annotated user screenshots label upper/left room exits, including
upper-left, upper-right and lower-left families. No screenshot files are
available locally: these maps and every later view are explicitly procedural,
not reconstructions of missing device captures or gold-shop positives.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(1, 7)
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
        ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def offset(x, y):
    return (y + 5) * 23 + x + 11


def set_cell(scene, x, y, kind, protected=0):
    scene.tiles[offset(x, y)] = kind
    scene.protected_cells[offset(x, y)] = protected


def room(mouths=(), outside=FLOOR, mouth_kind=FLOOR):
    result = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2, gold_state=1)
    for y in range(-2, 3):
        for x in range(-2, 3):
            set_cell(result, x, y, FLOOR)
    for k in range(-3, 4):
        for x, y in ((k, -3), (k, 3), (-3, k), (3, k)):
            set_cell(result, x, y, DIRT)
    for x, y in mouths:
        dx, dy = (-1, 0) if x == -3 else (0, -1)
        set_cell(result, x, y, mouth_kind)
        set_cell(result, x + dx, y + dy, outside)
    return result


def shifted(scene, x, y):
    result = deepcopy(scene)
    result.tiles[:] = bytes(230)
    result.protected_cells[:] = bytes(230)
    for old_y in range(-5, 5):
        for old_x in range(-11, 12):
            local_x, local_y = old_x - x, old_y - y
            if -11 <= local_x <= 11 and -5 <= local_y <= 4:
                index = offset(old_x, old_y)
                set_cell(result, local_x, local_y, scene.tiles[index],
                    scene.protected_cells[index])
    return result


def profiles(method):
    def run(self):
        for name, library in self.libraries.items():
            with self.subTest(profile=name):
                self.lib = library
                method(self)
    return run


class NativePassageNavigation072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test072-passage-nav-')
        cls.libraries = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-shared', '-fPIC', '-I' + str(CORE),
                str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(library)], check=True)
            cls.libraries[profile] = lib = C.CDLL(str(library))
            lib.ng2_passage_candidates.argtypes = [C.POINTER(Scene)]
            lib.ng2_passage_candidates.restype = C.c_uint32
            lib.ng2_choose_passage.argtypes = [C.POINTER(Scene), C.c_int32,
                C.c_int32, C.c_int32, C.c_int32, C.POINTER(Decision)]
            lib.ng2_choose_passage.restype = C.c_int
            lib.ng2_choose.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                C.POINTER(C.c_uint16), C.c_size_t, C.c_void_p, C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidates(self, scene):
        before = bytes(scene)
        result = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(before, bytes(scene))
        return result

    def choose(self, scene, x, y, mouth_x, mouth_y):
        choice = Decision(99, 99, 99, 99, 99)
        before = bytes(scene)
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y,
            mouth_x, mouth_y, C.byref(choice))
        self.assertEqual(before, bytes(scene))
        return length, tuple(getattr(choice, name) for name, _ in choice._fields_)

    @profiles
    def test_candidate_bits_cover_annotated_families_and_multiple_mouths(self):
        for side in range(2):
            for k in range(-2, 3):
                mouth = (k, -3) if not side else (-3, k)
                for outside in (0, FLOOR):
                    with self.subTest(mouth=mouth, outside=outside):
                        self.assertEqual(1 << (side * 5 + k + 2),
                            self.candidates(room([mouth], outside=outside)),
                            'a wall-bounded FLOOR mouth merits approach even before the outside is visible')
        self.assertEqual((1 << 0) | (1 << 4) | (1 << 9),
            self.candidates(room([(-2, -3), (2, -3), (-3, 2)])))
        self.assertEqual(0, self.candidates(room()))

    @profiles
    def test_fixed_world_mouth_reaches_one_outside_with_real_floor_steps(self):
        for mouth in [(-2, -3), (2, -3), (-3, 2), (0, -3), (-3, 0)]:
            with self.subTest(mouth=mouth):
                terrain = room([mouth])
                goal = (mouth[0] - (mouth[0] == -3),
                    mouth[1] - (mouth[1] == -3))
                x = y = steps = 0
                while (x, y) != goal:
                    scene = shifted(terrain, x, y)
                    length, choice = self.choose(scene, x, y, *mouth)
                    self.assertGreater(length, 0,
                        'an observed side passage needs an actual FLOOR route, not a no-gold rejection')
                    direction, reason, tx, ty, obstacle = choice
                    self.assertEqual((10, FLOOR), (reason, obstacle))
                    self.assertEqual((goal[0] - x, goal[1] - y), (tx, ty))
                    self.assertEqual(abs(tx) + abs(ty), length)
                    dx, dy = DIRS[direction]
                    self.assertEqual(FLOOR, scene.tiles[offset(dx, dy)])
                    x += dx; y += dy; steps += 1
                    self.assertLessEqual(steps, 6)
                self.assertEqual((0, (0, 0, 0, 0, 0)),
                    self.choose(shifted(terrain, x, y), x, y, *mouth))

    @profiles
    def test_shadowed_mouth_requires_outside_floor_and_wall_line_support(self):
        mouth = (-2, -3)
        scene = room([mouth], mouth_kind=0)
        self.assertEqual(1, self.candidates(scene))
        set_cell(scene, -3, -3, 0)
        self.assertEqual(1, self.candidates(scene), 'one post plus a supported wall line may reveal a shadowed mouth')
        for x in (-1, 0, 1, 2):
            set_cell(scene, x, -3, 0)
        self.assertEqual(0, self.candidates(scene), 'outside FLOOR alone is not a supported side passage')
        scene = room([mouth], mouth_kind=0, outside=0)
        self.assertEqual(0, self.candidates(scene), 'black-only gaps never authorize exploration')
        for kind in (DIRT, STONE, DOOR, ITEM, GOLD):
            with self.subTest(outside=kind):
                scene = room([mouth], mouth_kind=0, outside=kind)
                self.assertEqual(0, self.candidates(scene))

    @profiles
    def test_unknown_outside_uses_a_monotone_observed_vantage_then_new_view(self):
        mouth = (2, -3)
        terrain = room([mouth], outside=0)
        length, choice = self.choose(terrain, 0, 0, *mouth)
        self.assertEqual((5, (2, 10, 2, -3, FLOOR)), (length, choice))
        x, y = mouth
        scene = shifted(terrain, x, y)
        self.assertEqual((0, (0, 0, 0, 0, 0)), self.choose(scene, x, y, *mouth))
        set_cell(terrain, 2, -4, FLOOR)
        self.assertEqual((1, (3, 10, 0, -1, FLOOR)),
            self.choose(shifted(terrain, x, y), x, y, *mouth))

    @profiles
    def test_invalid_start_gold_goods_ordinary_exits_and_protection_do_not_explore(self):
        source = room([(-2, -3)])
        mutations = [('state', 0), ('state', 1), ('abi_version', 2),
            ('struct_size', C.sizeof(Scene) - 1), ('gold_state', 0),
            ('gold_state', 2), ('gold_state', 3), ('goods', 1), ('goods', 2)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                scene = deepcopy(source); setattr(scene, field, value)
                self.assertEqual(0, self.candidates(scene))
                self.assertEqual(0, self.choose(scene, 0, 0, -2, -3)[0])
        for x, y in ((0, 0), (-1, 0), (0, -1), (-2, -2), (-2, -3), (-2, -4)):
            with self.subTest(protected=(x, y)):
                scene = deepcopy(source); scene.protected_cells[offset(x, y)] = 1
                self.assertEqual(0, self.candidates(scene))
        for kind in (DIRT, STONE, DOOR, ITEM, GOLD):
            with self.subTest(mouth_kind=kind):
                self.assertEqual(0, self.candidates(room([(-2, -3)], mouth_kind=kind)))
        scene = room(); set_cell(scene, 3, 0, FLOOR); set_cell(scene, 4, 0, FLOOR)
        set_cell(scene, 0, 3, FLOOR); set_cell(scene, 0, 4, FLOOR)
        self.assertEqual(0, self.candidates(scene), 'ordinary right/down progression exits are outside this local pattern')
        scene = deepcopy(source); set_cell(scene, 8, 1, GOLD)
        self.assertEqual(0, self.candidates(scene), 'real gold takes precedence even with an inconsistent CLEAR label')
        self.assertEqual(0, self.choose(scene, 0, 0, -2, -3)[0])

    @profiles
    def test_chooser_rejects_unsafe_steps_invalid_world_targets_and_unreachable_floor(self):
        for kind in (0, DIRT, STONE, DOOR, ITEM, GOLD):
            with self.subTest(next=kind):
                scene = room([(-3, 0)])
                for x, y in ((-1, 0), (0, -1), (0, 1), (1, 0)):
                    set_cell(scene, x, y, kind)
                self.assertEqual((0, (0, 0, 0, 0, 0)),
                    self.choose(scene, 0, 0, -3, 0))
        scene = room([(-3, 0)])
        for target in ((3, 0), (0, 3), (-3, -3), (-3, 3), (3, -3), (0, 0)):
            with self.subTest(target=target):
                self.assertEqual(0, self.choose(scene, 0, 0, *target)[0])
        for x, y in ((-17, 0), (17, 0), (0, -17), (0, 17)):
            with self.subTest(position=(x, y)):
                self.assertEqual(0, self.choose(scene, x, y, -3, 0)[0])
        for protected in ((0, 0), (-1, 0), (0, -1)):
            with self.subTest(protected=protected):
                altered = deepcopy(scene)
                altered.protected_cells[offset(*protected)] = 1
                self.assertEqual(0, self.choose(altered, 0, 0, -3, 0)[0])
        scene = room([(-2, -3)])
        for x, y in ((-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2)):
            set_cell(scene, x, y, STONE)
        self.assertEqual(0, self.candidates(scene), 'disconnected observed outside FLOOR is not an approach route')

    @profiles
    def test_fixed_second_mouth_remains_reachable_across_the_initial_room(self):
        first, second = (-2, -3), (-3, 2)
        terrain = room([first, second])
        self.assertEqual((1 << 0) | (1 << 9), self.candidates(terrain))
        x, y = -2, -4
        scene = shifted(terrain, x, y)
        length, choice = self.choose(scene, x, y, *second)
        self.assertGreater(length, 0)
        self.assertEqual((4, 10, 0, 4, FLOOR), choice)
        self.assertEqual(4, length, 'off-screen fixed mouth still uses only reachable current FLOOR toward it')

    @profiles
    def test_shop_chooser_stays_separate_and_null_outputs_fail_closed(self):
        scene = room([(-2, -3)])
        visits = (C.c_uint16 * 1089)(); visits[16 * 33 + 16] = 1
        choice = Decision()
        self.assertEqual(0, self.lib.ng2_choose(C.byref(scene), 0, 0,
            visits, len(visits), None, C.byref(choice)))
        self.assertEqual(3, choice.reason, 'the ordinary shop chooser still requires real gold')
        self.assertEqual(0, self.lib.ng2_passage_candidates(None))
        self.assertEqual(0, self.lib.ng2_choose_passage(C.byref(scene), 0, 0, -2, -3, None))
        self.assertEqual(0, self.lib.ng2_choose_passage(None, 0, 0, -2, -3, C.byref(choice)))
        self.assertEqual(bytes(Decision()), bytes(choice))
