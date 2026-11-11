"""TEST075: independent gradient evidence may confirm zero displacement only.

Broad procedural rectangles have strong signed edges but little median detail.
They exercise raw Scenes, not stored phone pixels or iPhone acceptance. A zero
proof cannot grant a move, opening, entrance, retry, or motion credit.
"""
import ctypes as C
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import procedural_pair

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


def cell(x, y):
    return (y + 5) * 23 + x + 11


def stationary_pair(seed=75075, reveal=False, rectangle_count=12):
    rng = random.Random(seed)
    pixels = bytearray([48] * (W * H))
    # Straight rectangle edges carry a central gradient while most pixels
    # equal their neighborhood median. Independent upper/lower placement
    # avoids treating a single long boundary as two spatial observations.
    for i in range(rectangle_count):
        x = rng.randrange(42, 170)
        y = rng.randrange(22, 58) if i % 2 == 0 else rng.randrange(68, 79)
        width, height = rng.randrange(4, 11), rng.randrange(3, 7)
        value = rng.choice((18, 90, 130, 170))
        for yy in range(y, y + height):
            for xx in range(x, x + width):
                pixels[yy * W + xx] = value
    pair = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                  gold_state=2) for _ in range(2)]
    for scene in pair:
        scene.tiles[:] = [1] * 230
        scene.tiles[cell(-2, -2)] = 2
    pair[0].signature[:] = pixels
    pair[1].signature[:] = bytes(value * 5 // 4 + 4 for value in pixels)
    if reveal:
        # Newly lit remote terrain may change while the observed origin,
        # next floor and their neighborhoods remain unchanged.
        pair[0].tiles[cell(3, 3)], pair[1].tiles[cell(3, 3)] = 3, 4
        pair[0].tiles[cell(3, 4)], pair[1].tiles[cell(3, 4)] = 4, 1
    return pair


def shifted_pixels(pair, sx, sy):
    image = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x + sx, y + sy
            if 0 <= xx < W and 0 <= yy < H:
                image[yy * W + xx] = pair[1].signature[y * W + x]
    pair[1].signature[:] = image
    return pair


class NativeStatic075Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test075-static-')
        cls.libraries = {}
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                            '-pedantic', '-I', str(CORE), '-fPIC', '-shared',
                            str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(path)],
                           check=True, capture_output=True)
            lib = C.CDLL(str(path))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                      C.POINTER(Motion)]
            lib.ng2_motion.restype = C.c_int
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, pair, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def test_same_floor_gradient_confirms_only_blocked_in_four_directions(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for seed in (75075, 75076):
                    for reveal in (False, True):
                        with self.subTest(profile=profile, direction=direction,
                                          seed=seed, reveal=reveal):
                            self.assertEqual((2, 0, 0), self.result(lib,
                                stationary_pair(seed, reveal), direction))
            pair = stationary_pair()
            for scene in pair:
                scene.protected_cells[cell(8, 4)] = 1
            with self.subTest(profile=profile, unchanged_remote_protection=True):
                self.assertEqual((2, 0, 0), self.result(lib, pair))

    def test_static_proof_requires_safe_unchanged_local_scene_and_gold_set(self):
        cases = []
        for side in (0, 1):
            for goods in (1, 2):
                pair = stationary_pair()
                pair[side].goods = goods
                cases.append((f'goods:{side}:{goods}', pair))
            for gold in (0, 1, 3):
                pair = stationary_pair()
                pair[side].gold_state = gold
                cases.append((f'gold_state:{side}:{gold}', pair))
            for point in ((0, 0), (0, -1)):
                pair = stationary_pair()
                pair[side].tiles[cell(*point)] = 0
                cases.append((f'unobserved_floor:{side}:{point}', pair))
        for label in ('missing_gold', 'new_gold', 'gold_shift', 'both_no_gold',
                      'changed_protection', 'protected_origin', 'protected_next',
                      'item', 'local_change', 'next_neighborhood_change',
                      'door_opened', 'terrain_opened'):
            pair = stationary_pair()
            if label in ('missing_gold', 'gold_shift'):
                pair[1].tiles[cell(-2, -2)] = 1
            if label in ('new_gold', 'gold_shift'):
                pair[1].tiles[cell(5, 2)] = 2
            if label == 'both_no_gold':
                for scene in pair:
                    scene.tiles[cell(-2, -2)] = 1
            elif label == 'changed_protection':
                pair[1].protected_cells[cell(8, 4)] = 1
            elif label in ('protected_origin', 'protected_next'):
                for scene in pair:
                    scene.protected_cells[cell(0, 0 if label == 'protected_origin' else -1)] = 1
            elif label == 'item':
                for scene in pair:
                    scene.tiles[cell(8, 4)] = 6
            elif label == 'local_change':
                pair[1].tiles[cell(-1, 1)] = 3
            elif label == 'next_neighborhood_change':
                pair[1].tiles[cell(1, -2)] = 4
            elif label in ('door_opened', 'terrain_opened'):
                pair[0].tiles[cell(0, -1)] = 5 if label == 'door_opened' else 4
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.result(lib, pair))

    def test_weak_single_band_aliased_or_opposite_edges_remain_unknown(self):
        cases = []
        for label in ('weak', 'sparse', 'upper_only', 'lower_only', 'repeating',
                      'opposite_edges', 'competing_edges', 'poor_intensity'):
            pair = stationary_pair(rectangle_count=(24 if label in ('upper_only', 'lower_only')
                                   else 16 if label == 'competing_edges'
                                   else 8 if label == 'sparse' else 12))
            if label == 'weak':
                rng = random.Random(75077)
                image = bytes(rng.randrange(48, 53) for _ in range(W * H))
                for scene in pair:
                    scene.signature[:] = image
            elif label in ('upper_only', 'lower_only'):
                for scene in pair:
                    image = bytearray(scene.signature)
                    for y in range(H):
                        if (y < 65) != (label == 'upper_only'):
                            image[y * W:(y + 1) * W] = bytes(W)
                    scene.signature[:] = image
            elif label == 'repeating':
                rng = random.Random(75078)
                tile = [rng.randrange(18, 72) for _ in range(81)]
                image = bytes(tile[(y % 9) * 9 + x % 9]
                              for y in range(H) for x in range(W))
                for scene in pair:
                    scene.signature[:] = image
            elif label == 'opposite_edges':
                pair[1].signature[:] = bytes(180 if value == 18 else value * 5 // 4 + 4
                                             for value in pair[0].signature)
            elif label == 'poor_intensity':
                rng = random.Random(75079)
                pair[1].signature[:] = bytes(value * 5 // 4 + 4 + rng.randrange(-6, 7)
                                             for value in pair[0].signature)
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    self.assertEqual((0, 0, 0), self.result(lib, pair))

    def test_shift_partial_and_reverse_do_not_manufacture_a_static_proof(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for pixels in (1, 4, 9, 18, -4, -9):
                    pair = shifted_pixels(stationary_pair(), -dx * pixels, -dy * pixels)
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertNotEqual(2, self.result(lib, pair, direction)[0])

    def test_existing_primary_motion_results_remain_unchanged(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for pixels, expected in ((0, (2, 0, 0)), (4, (7, 0, 0)),
                                         (9, (1, dx, dy)), (18, (6, 2 * dx, 2 * dy)),
                                         (-9, (6, -dx, -dy))):
                    pair = procedural_pair(direction, pixels=pixels, overlay=False)
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        self.assertEqual(expected, self.result(lib, pair, direction))
                pair = list(procedural_pair(direction, pixels=0, overlay=False))
                # This existing primary opening proof has a closed gold bracket.
                for scene in pair:
                    scene.tiles[:] = [1] * 230
                    for side in (-1, 1):
                        scene.tiles[cell(dx + side * dy, dy - side * dx)] = 2
                pair[0].tiles[cell(dx, dy)] = 5
                with self.subTest(profile=profile, direction=direction, opening=True):
                    self.assertEqual((3, 0, 0), self.result(lib, pair, direction))
