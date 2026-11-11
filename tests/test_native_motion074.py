"""TEST074: supplemental motion evidence, using procedural fields only.

The received 073 pixels remain outside Git. These fixtures exercise the public
motion contract: a fixed central half-gradient resolves stationary lighting
change at a gold gate; strong existing detail and unique observed terrain
anchors resolve a clear-floor unit translation. They are not iPhone playback.
"""
import ctypes as C
import os
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


def lit_opening(direction=3, seed=74074):
    rng = random.Random(seed)
    pixels = bytes(rng.randrange(18, 72) for _ in range(W * H))
    pair = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                  gold_state=2) for _ in range(2)]
    for scene in pair:
        scene.tiles[:] = [1] * 230
    pair[0].signature[:] = pixels
    # A strong monotonic illumination change retains local edge ordering but
    # deliberately violates the original global intensity score. Half of a
    # fixed central difference uses the original six-gray contrast unit.
    pair[1].signature[:] = bytes(20 + 3 * value for value in pixels)
    dx, dy = DIRS[direction]
    for side in (-1, 1):
        point = (dx + side * dy, dy - side * dx)
        for scene in pair:
            scene.tiles[cell(*point)] = 2
    pair[0].tiles[cell(dx, dy)] = 5
    pair[1].tiles[cell(dx, dy)] = 1
    pair[1].goods = 1
    return pair


def clear_translation(direction=1, amount=1, pixels=None):
    pair = list(procedural_pair(direction, amount=amount, pixels=pixels))
    dx, dy = DIRS[direction]
    for scene in pair:
        scene.gold_state = 1
        scene.tiles[:] = [1] * 230
    for x, y, kind in ((-3, -1, 3), (4, 2, 3), (-3, 2, 4), (5, -2, 4)):
        pair[0].tiles[cell(x, y)] = kind
        pair[1].tiles[cell(x - dx * amount, y - dy * amount)] = kind
    return pair


class NativeMotion074Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test074-motion-')
        cls.libraries = {}
        source = Path(os.environ.get('NECRO_TEST074_BASELINE_NAVIGATION',
                                     CORE / 'NG2Navigation.c'))
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (name + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                            '-pedantic', '-I', str(CORE), '-fPIC', '-shared',
                            str(source), '-lm', '-o', str(path)],
                           check=True, capture_output=True)
            lib = C.CDLL(str(path))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                      C.POINTER(Motion)]
            lib.ng2_motion.restype = C.c_int
            cls.libraries[name] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, pair, direction):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def test_stationary_lighting_opening_has_gradient_evidence_in_four_directions(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for seed in (74074, 74075):
                    with self.subTest(profile=profile, direction=direction, seed=seed):
                        self.assertEqual((3, 0, 0), self.result(lib,
                            lit_opening(direction, seed), direction))

    def test_clear_floor_detail_and_unique_terrain_prove_one_move(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual((1, dx, dy), self.result(lib,
                        clear_translation(direction), direction))

    def test_gradient_opening_requires_the_same_bracket_and_safe_endpoints(self):
        cases = []
        for side in (0, 1):
            for point in ((0, 0), (0, -1)):
                pair = lit_opening()
                pair[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protected:{point}', pair))
            for point in ((-1, -1), (1, -1)):
                pair = lit_opening()
                pair[side].tiles[cell(*point)] = 1
                cases.append((f'{side}:missing_bracket:{point}', pair))
            for point, valid in (((0, 0), 1), ((0, -1), 5 if side == 0 else 1)):
                for kind in range(7):
                    if kind == valid:
                        continue
                    pair = lit_opening()
                    pair[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:endpoint:{point}:{kind}', pair))
            for gold in (0, 1, 3):
                pair = lit_opening()
                pair[side].gold_state = gold
                cases.append((f'{side}:gold:{gold}', pair))
        pair = lit_opening()
        pair[0].tiles[cell(7, 1)] = 2
        cases.append(('other_original_gold_disappeared', pair))
        for goods in ((0, 2), (1, 0), (2, 1), (2, 2)):
            pair = lit_opening()
            pair[0].goods, pair[1].goods = goods
            cases.append((f'goods:{goods}', pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, pair, 3))
            for goods in ((0, 0), (0, 1), (1, 1)):
                pair = lit_opening()
                pair[0].goods, pair[1].goods = goods
                with self.subTest(profile=profile, allowed_goods=goods):
                    self.assertEqual((3, 0, 0), self.result(lib, pair, 3))
            # Newly exposed remote merchandise is excluded from the evidence
            # surface and is not a license to discard the partial shop.
            pair = lit_opening()
            pair[1].tiles[cell(6, -3)] = 6
            pair[1].protected_cells[cell(6, -3)] = 1
            pair[1].tiles[cell(5, -3)] = 2
            self.assertEqual((3, 0, 0), self.result(lib, pair, 3))

    def test_gradient_uses_common_known_terrain_and_two_independent_bands(self):
        cases = []
        for label in ('unknown', 'item', 'protected', 'upper_only', 'lower_only', 'sparse'):
            pair = lit_opening()
            if label in ('unknown', 'item', 'protected'):
                for scene in pair:
                    for i in range(230):
                        if i in (cell(0, 0), cell(0, -1), cell(-1, -1), cell(1, -1)):
                            continue
                        if label == 'protected':
                            scene.protected_cells[i] = 1
                        else:
                            scene.tiles[i] = 0 if label == 'unknown' else 6
            else:
                for scene in pair:
                    image = bytearray(scene.signature)
                    for y in range(H):
                        for x in range(W):
                            keep = (y < 65 if label == 'upper_only' else
                                    y >= 65 if label == 'lower_only' else
                                    70 <= x < 78 and 50 <= y < 80)
                            if not keep:
                                image[y * W + x] = 0
                    scene.signature[:] = image
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, pair, 3))

    def test_gradient_rejects_opposite_sign_axis_disagreement_and_ambiguous_texture(self):
        cases = []
        for label in ('opposite', 'different_axis', 'weak', 'repeating', 'ui_only'):
            pair = lit_opening()
            if label == 'opposite':
                pair[1].signature[:] = bytes(245 - 3 * value for value in pair[0].signature)
            elif label == 'different_axis':
                # Both fields have strong local contrast, but horizontal and
                # vertical gradients cannot support one another's signs.
                rng = random.Random(74076)
                stripe = [rng.randrange(18, 72) for _ in range(W)]
                pair[0].signature[:] = bytes(stripe[x] for y in range(H) for x in range(W))
                pair[1].signature[:] = bytes(20 + 3 * stripe[y] for y in range(H) for x in range(W))
            elif label == 'weak':
                rng = random.Random(74077)
                pixels = bytes(rng.randrange(48, 53) for _ in range(W * H))
                pair[0].signature[:] = pixels
                pair[1].signature[:] = bytes(20 + 3 * value for value in pixels)
            elif label == 'repeating':
                rng = random.Random(74078)
                tile = [rng.randrange(18, 72) for _ in range(81)]
                pixels = bytes(tile[y % 9 * 9 + x % 9] for y in range(H) for x in range(W))
                pair[0].signature[:] = pixels
                pair[1].signature[:] = bytes(20 + 3 * value for value in pixels)
            else:
                for scene in pair:
                    pixels = bytearray(scene.signature)
                    for y in range(20, 85):
                        for x in range(40, 179):
                            if not (103 <= x < 122 and 43 <= y < 61 or
                                    101 <= x < 123 and y >= 80):
                                pixels[y * W + x] = 0
                    scene.signature[:] = pixels
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, pair, 3))

    def test_passage_move_requires_all_stones_and_a_noncollinear_dirt_anchor(self):
        cases = []
        for label in ('no_stones', 'one_stone', 'stone_mismatch', 'ambiguous_stones',
                      'no_dirt', 'collinear_dirt', 'unobserved_dirt'):
            pair = clear_translation()
            if label in ('no_stones', 'one_stone'):
                for scene in pair:
                    stones = [i for i, tile in enumerate(scene.tiles) if tile == 3]
                    for index in stones if label == 'no_stones' else stones[1:]:
                        scene.tiles[index] = 1
            elif label == 'stone_mismatch':
                pair[1].tiles[cell(-2, -1)] = 4
            elif label == 'ambiguous_stones':
                # The old stone set and non-collinear dirt can now match
                # both +1 and -1. Extra newly exposed stone alone is allowed;
                # two complete translations cannot authorize this one.
                for x, y, kind in ((-3, -1, 3), (4, 2, 3), (-3, 2, 4), (5, -2, 4)):
                    pair[1].tiles[cell(x - 1, y)] = kind
            elif label == 'no_dirt':
                for scene in pair:
                    for i, tile in enumerate(scene.tiles):
                        if tile == 4:
                            scene.tiles[i] = 1
            elif label == 'collinear_dirt':
                for scene in pair:
                    scene.tiles[:] = [1] * 230
                for x, kind in ((-4, 3), (-2, 3), (-3, 4)):
                    pair[0].tiles[cell(x, 2)] = kind
                    pair[1].tiles[cell(x + 1, 2)] = kind
            else:
                for i, tile in enumerate(pair[1].tiles):
                    if tile == 4:
                        pair[1].tiles[i] = 0
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, pair, 1))

    def test_passage_move_requires_clear_unprotected_floor_and_no_goods(self):
        cases = []
        for side in (0, 1):
            for field, values in (('goods', (1, 2)), ('gold_state', (0, 2, 3))):
                for value in values:
                    pair = clear_translation()
                    setattr(pair[side], field, value)
                    cases.append((f'{side}:{field}:{value}', pair))
            for point in ((0, 0), (-1, 0), (7, 3)):
                pair = clear_translation()
                pair[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protected:{point}', pair))
            for point in ((0, 0), (-1, 0)):
                if side == 1 and point == (-1, 0):
                    continue  # A future step is checked by the next Nav call.
                for kind in (0, 2, 3, 4, 5, 6):
                    pair = clear_translation()
                    pair[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:floor:{point}:{kind}', pair))
            for kind in (2, 6):
                pair = clear_translation()
                pair[side].tiles[cell(7, 3)] = kind
                cases.append((f'{side}:remote:{kind}', pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, pair, 1))

    def test_arrival_proof_does_not_authorize_or_require_a_future_step(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for next_kind in (0, 3, 4, 5):
                    pair = clear_translation(direction)
                    pair[1].tiles[cell(dx, dy)] = next_kind
                    with self.subTest(profile=profile, direction=direction, future=next_kind):
                        self.assertEqual((1, dx, dy), self.result(lib, pair, direction))
            pair = clear_translation()
            pair[1].tiles[cell(7, -3)] = 3
            self.assertEqual((1, -1, 0), self.result(lib, pair, 1))

    def test_reverse_partial_two_cells_and_wrong_direction_never_receive_one_move(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(1, self.result(lib,
                            clear_translation(direction, amount), direction)[0])
                for partial in (1, 8):
                    with self.subTest(profile=profile, direction=direction, partial=partial):
                        self.assertNotEqual(1, self.result(lib,
                            clear_translation(direction, pixels=partial), direction)[0])
                for wrong in DIRS:
                    if wrong != direction:
                        with self.subTest(profile=profile, direction=direction, wrong=wrong):
                            self.assertNotEqual(1, self.result(lib,
                                clear_translation(direction), wrong)[0])
                            self.assertNotEqual(3, self.result(lib,
                                lit_opening(direction), wrong)[0])

    def test_unit_move_detail_rejects_weak_one_region_and_repeated_fields(self):
        cases = []
        for label in ('weak', 'upper_only', 'left_only', 'repeating'):
            pair = clear_translation()
            if label == 'weak':
                rng = random.Random(74079)
                pixels = bytes(rng.randrange(48, 53) for _ in range(W * H))
                pair[0].signature[:] = pair[1].signature[:] = pixels
            elif label == 'repeating':
                rng = random.Random(74080)
                texture = [rng.randrange(15, 90) for _ in range(81)]
                pixels = bytes(texture[y % 9 * 9 + x % 9] for y in range(H) for x in range(W))
                pair[0].signature[:] = pair[1].signature[:] = pixels
            else:
                for scene in pair:
                    pixels = bytearray(scene.signature)
                    for y in range(H):
                        for x in range(W):
                            if not (y < 36 if label == 'upper_only' else x < 90):
                                pixels[y * W + x] = 0
                    scene.signature[:] = pixels
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertNotEqual(1, self.result(lib, pair, 1)[0])

    def test_original_primary_classification_and_invalid_abi_remain_unchanged(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    pair = list(procedural_pair(direction, overlay=False))
                    self.assertEqual((1, dx, dy), self.result(lib, pair, direction))
            for fixture in (lit_opening, clear_translation):
                for side in (0, 1):
                    for field, value in (('state', 0), ('abi_version', 2),
                                         ('struct_size', C.sizeof(Scene) - 1), ('goods', 3)):
                        pair = fixture()
                        setattr(pair[side], field, value)
                        out = Motion(99, 99, 99)
                        with self.subTest(profile=profile, fixture=fixture.__name__,
                                          side=side, field=field):
                            self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                                                             1, C.byref(out)))
                            self.assertEqual((0, 0, 0), (out.kind, out.dx, out.dy))


if __name__ == '__main__':
    unittest.main()
