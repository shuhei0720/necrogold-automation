"""TEST072: independent strong terrain detail proves a stationary opening.

These grayscale fields are deterministic procedural evidence, not copies of
the received 318 run. A sparse central passage contains stable terrain below
the character and a transient weak-detail overlay. The old ordinary motion
mask has too little matching texture; the dedicated opening proof must use
two separate terrain bands while retaining all 73 displacement alternatives.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


class Entrance(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('valid', 'x', 'y', 'direction')]


class Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def cell(x, y):
    return (y + 5) * 23 + x + 11


def sparse_opening(direction=3, seed=72072):
    rng = random.Random(seed)
    terrain = bytearray(W * H)
    # Stable, independently generated terrain appears in both near and lower
    # parts of the passage. The character itself is outside these patches.
    for y in range(50, 85):
        for x in range(91, 103):
            terrain[y * W + x] = rng.randrange(15, 100)
    for y in range(35, 50):
        for x in range(91, 103):
            terrain[y * W + x] = 50 + 4 * rng.randrange(2)
    for y in range(55, 75):
        for x in range(145, 165):
            terrain[y * W + x] = rng.randrange(45, 56)
    before_pixels = bytearray(terrain)
    for y in range(35, 50):
        for x in range(91, 103):
            before_pixels[y * W + x] = 240 if terrain[y * W + x] == 50 else 16
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                           gold_state=2) for _ in range(2)]
    before.signature[:] = before_pixels
    after.signature[:] = terrain
    dx, dy = DIRS[direction]
    for scene in (before, after):
        scene.tiles[cell(0, 0)] = 1
        for side in (-1, 1):
            scene.tiles[cell(dx + side * dy, dy - side * dx)] = 2
    before.tiles[cell(dx, dy)] = 5
    after.tiles[cell(dx, dy)] = 1
    after.goods = 1
    return before, after


class NativeDoor072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test072-door-')
        cls.libraries = {}
        cls.compile_commands = {}
        source = Path(os.environ.get('NECRO_TEST072_BASELINE_NAVIGATION',
                                     CORE / 'NG2Navigation.c'))
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (name + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-I', str(CORE), '-fPIC', '-shared', str(source), '-lm', '-o', str(path)]
            subprocess.run(command, check=True, capture_output=True)
            cls.compile_commands[name] = command
            lib = C.CDLL(str(path))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                      C.POINTER(Motion)]
            lib.ng2_motion.restype = C.c_int
            lib.ng2_choose.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                                      C.POINTER(C.c_uint16), C.c_size_t,
                                      C.POINTER(Entrance), C.POINTER(Decision)]
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, before, after, direction):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(before), C.byref(after), direction,
                                         C.byref(out)))
        return out.kind, out.dx, out.dy

    def test_sparse_opening_uses_strong_independent_terrain_in_four_directions(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for seed in (72072, 72073, 72074):
                    before, after = sparse_opening(direction, seed)
                    # New light may expose more gold and merchandise; this
                    # does not imply a unit step through the opened entrance.
                    after.tiles[cell(5, -4)] = 2
                    after.tiles[cell(5, -3)] = 6
                    after.protected_cells[cell(5, -3)] = 1
                    with self.subTest(profile=profile, direction=direction, seed=seed):
                        self.assertEqual((3, 0, 0), self.result(lib, before, after, direction))

    def test_protected_gold_walls_allow_the_observed_interior_floor(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                              gold_state=2, goods=1)
                scene.tiles[cell(0, 0)] = 1
                for step in (1, 2):
                    scene.tiles[cell(step * dx, step * dy)] = 1
                for side in (-1, 1):
                    point = (side * dy, -side * dx)
                    scene.tiles[cell(*point)] = 2
                    scene.protected_cells[cell(*point)] = 1
                visits = (C.c_uint16 * 1089)()
                visits[16 * 33 + 16] = 1
                choice = Decision()
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual(1, lib.ng2_choose(C.byref(scene), 0, 0, visits,
                        len(visits), C.byref(Entrance(1, 0, 0, direction)), C.byref(choice)))
                    self.assertEqual((direction, 8, 1),
                                     (choice.direction, choice.reason, choice.obstacle))

    def test_opening_requires_a_preserved_bracket_and_unprotected_endpoints(self):
        before, after = sparse_opening()
        cases = []
        for side in (0, 1):
            for point in ((0, 0), (0, -1)):
                pair = [deepcopy(before), deepcopy(after)]
                pair[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protected:{point}', pair))
            for point in ((-1, -1), (1, -1)):
                for kind in (0, 1, 3, 4, 5, 6):
                    pair = [deepcopy(before), deepcopy(after)]
                    pair[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:bracket:{point}:{kind}', pair))
            for kind in (0, 2, 3, 4, 5, 6):
                pair = [deepcopy(before), deepcopy(after)]
                pair[side].tiles[cell(0, 0)] = kind
                cases.append((f'{side}:origin:{kind}', pair))
            for kind in (0, 1, 2, 3, 4, 5, 6):
                if kind == (5 if side == 0 else 1):
                    continue
                pair = [deepcopy(before), deepcopy(after)]
                pair[side].tiles[cell(0, -1)] = kind
                cases.append((f'{side}:gate:{kind}', pair))
            for state in (0, 1, 3):
                pair = [deepcopy(before), deepcopy(after)]
                pair[side].gold_state = state
                cases.append((f'{side}:gold_state:{state}', pair))
        # The local bracket alone cannot erase other previously observed gold.
        pair = [deepcopy(before), deepcopy(after)]
        pair[0].tiles[cell(6, 2)] = 2
        cases.append(('old_remote_gold_disappeared', pair))
        for goods in ((0, 2), (1, 0), (2, 1), (2, 2)):
            pair = [deepcopy(before), deepcopy(after)]
            pair[0].goods, pair[1].goods = goods
            cases.append((f'goods:{goods}', pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, *pair, 3))
            for direction in (1, 2, 4):
                with self.subTest(profile=profile, wrong_direction=direction):
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, direction))
            for original_goods, latest_goods in ((0, 0), (0, 1), (1, 1)):
                pair = [deepcopy(before), deepcopy(after)]
                pair[0].goods, pair[1].goods = original_goods, latest_goods
                with self.subTest(profile=profile, goods=(original_goods, latest_goods)):
                    self.assertEqual((3, 0, 0), self.result(lib, *pair, 3))

    def test_invalid_scenes_are_rejected_before_the_supplemental_proof(self):
        for profile, lib in self.libraries.items():
            for side in (0, 1):
                for field, values in (('state', (0, 1, 3)), ('abi_version', (0, 2)),
                                      ('struct_size', (0, C.sizeof(Scene) - 1)),
                                      ('goods', (-1, 3))):
                    for value in values:
                        pair = list(sparse_opening())
                        setattr(pair[side], field, value)
                        out = Motion(99, 99, 99)
                        with self.subTest(profile=profile, side=side, field=field, value=value):
                            self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                                             3, C.byref(out)))
                            self.assertEqual((0, 0, 0), (out.kind, out.dx, out.dy))

    def test_weak_repeating_one_band_and_ui_only_pixels_do_not_prove_an_opening(self):
        cases = []
        for name in ('flat', 'weak', 'repeating', 'upper_only', 'lower_only', 'ui_only'):
            pair = list(sparse_opening())
            if name in ('flat', 'weak', 'repeating', 'ui_only'):
                rng = random.Random(72075)
                if name == 'flat':
                    pixels = bytes([40]) * (W * H)
                elif name == 'weak':
                    pixels = bytes(rng.randrange(48, 53) for _ in range(W * H))
                elif name == 'repeating':
                    tile = [rng.randrange(15, 100) for _ in range(81)]
                    pixels = bytes(tile[(y % 9) * 9 + x % 9] for y in range(H) for x in range(W))
                else:
                    pixels = bytes(rng.randrange(15, 100) if y < 20 or y >= 85 else 0
                                   for y in range(H) for _ in range(W))
                pair[0].signature[:] = pair[1].signature[:] = pixels
            else:
                rng = random.Random(72076)
                first, second = [bytearray(scene.signature) for scene in pair]
                if name == 'lower_only':
                    for y in range(50, 65):
                        for x in range(91, 103):
                            first[y * W + x] = second[y * W + x] = 0
                    for y in range(65, 85):
                        for x in range(90, 115):
                            first[y * W + x] = second[y * W + x] = rng.randrange(15, 100)
                else:
                    for y in range(65, 85):
                        for x in range(91, 103):
                            first[y * W + x] = second[y * W + x] = 0
                pair[0].signature[:] = first
                pair[1].signature[:] = second
            cases.append((name, pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, *pair, 3))

    def test_nonzero_and_existing_primary_motion_results_are_not_reclassified(self):
        from tests.test_native_motion067 import procedural_pair
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction, motion='moved'):
                    self.assertEqual((1, dx, dy), self.result(lib, *procedural_pair(direction), direction))
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(3, self.result(lib, *procedural_pair(direction, amount), direction)[0])
                for pixels in (1, 8):
                    with self.subTest(profile=profile, direction=direction, partial=pixels):
                        self.assertNotEqual(3, self.result(lib,
                            *procedural_pair(direction, pixels=pixels), direction)[0])
            before, after = sparse_opening()
            rng = random.Random(72077)
            pixels = bytes(rng.randrange(15, 100) for _ in range(W * H))
            before.signature[:] = after.signature[:] = pixels
            with self.subTest(profile=profile, primary='door_opened'):
                self.assertEqual((3, 0, 0), self.result(lib, before, after, 3))
            after.tiles[cell(0, -1)] = 5
            with self.subTest(profile=profile, primary='blocked'):
                self.assertEqual((2, 0, 0), self.result(lib, before, after, 3))

    def test_gold_wall_exception_never_allows_protected_floor_or_other_cells(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                scene = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                              gold_state=2, goods=1)
                for step in (0, 1, 2):
                    scene.tiles[cell(step * dx, step * dy)] = 1
                for side in (-1, 1):
                    point = (side * dy, -side * dx)
                    scene.tiles[cell(*point)] = 2
                    scene.protected_cells[cell(*point)] = 1
                visits = (C.c_uint16 * 1089)()
                visits[16 * 33 + 16] = 1
                entrance = Entrance(1, 0, 0, direction)
                for point in ((0, 0), (dx, dy)):
                    changed = deepcopy(scene)
                    changed.protected_cells[cell(*point)] = 1
                    choice = Decision()
                    with self.subTest(profile=profile, direction=direction, protected=point):
                        self.assertEqual(0, lib.ng2_choose(C.byref(changed), 0, 0, visits,
                            len(visits), C.byref(entrance), C.byref(choice)))
                        self.assertEqual(2, choice.reason)
                for kind in (0, 1, 3, 4, 5, 6):
                    changed = deepcopy(scene)
                    changed.tiles[cell(dy, -dx)] = kind
                    choice = Decision()
                    with self.subTest(profile=profile, direction=direction, protected_kind=kind):
                        self.assertEqual(0, lib.ng2_choose(C.byref(changed), 0, 0, visits,
                            len(visits), C.byref(entrance), C.byref(choice)))
                        self.assertEqual(2, choice.reason)
                changed = deepcopy(scene)
                changed.protected_cells[cell(2 * dx, 2 * dy)] = 1
                choice = Decision()
                with self.subTest(profile=profile, direction=direction, far_floor=True):
                    self.assertEqual(1, lib.ng2_choose(C.byref(changed), 0, 0, visits,
                        len(visits), C.byref(entrance), C.byref(choice)))
                    self.assertNotEqual((2 * dx, 2 * dy), (choice.target_x, choice.target_y))


if __name__ == '__main__':
    unittest.main()
