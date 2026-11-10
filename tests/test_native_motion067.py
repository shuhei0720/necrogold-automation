"""TEST067: strong terrain detail may resolve one closed-gate translation.

The public Scenes below use deterministic procedural grayscale fields. A
transient high-contrast overlay covers weak terrain detail; independent strong
terrain remains in multiple regions. These are unit expectations for the raw
TEST066 observation, not recorded pixels or iPhone acceptance measurements.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


def cell(x, y):
    return (y + 5) * 23 + x + 11


def procedural_pair(direction=1, amount=1, overlay=True, weak_terrain=False, pixels=None):
    rng = random.Random(67067)
    world = bytearray(rng.randrange(48, 53) if weak_terrain else rng.randrange(12, 90)
                      for _ in range(W * H))
    # The narrow-band terrain changes by at most four gray levels. The
    # independently generated overlay disappears between the two images.
    for y in range(20, 34):
        for x in range(40, 179):
            world[y * W + x] = 50 + 4 * rng.randrange(2)
    before_pixels = bytearray(world)
    if overlay:
        for y in range(20, 34):
            for x in range(40, 179):
                before_pixels[y * W + x] = 240 if world[y * W + x] == 50 else 16
    dx, dy = DIRS[direction]
    shift = 9 * amount if pixels is None else pixels
    sx, sy = -dx * shift, -dy * shift
    after_pixels = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x + sx, y + sy
            if 0 <= xx < W and 0 <= yy < H:
                after_pixels[yy * W + xx] = world[y * W + x]
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                           gold_state=2) for _ in range(2)]
    before.signature[:] = before_pixels
    after.signature[:] = after_pixels
    for scene in (before, after):
        scene.tiles[:] = [1] * 230
    for x, y, kind in ((-3, -1, 2), (-3, 1, 2), (-3, 0, 5)):
        before.tiles[cell(x, y)] = kind
        after.tiles[cell(x - dx * amount, y - dy * amount)] = kind
    return before, after


class NativeMotion067Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.libraries = {}
        cls.compile_commands = {}
        for profile, flags in (('unchanged_o0', ['-O0']),
                               ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (profile + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-fPIC', '-shared', str(CORE / 'NG2Navigation.c'), '-lm', '-o', str(path)]
            subprocess.run(command, check=True, capture_output=True)
            cls.compile_commands[profile] = command
            lib = C.CDLL(str(path))
            lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                      C.POINTER(Motion)]
            lib.ng2_motion.restype = C.c_int
            cls.libraries[profile] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def result(self, lib, before, after, direction):
        out = Motion(99, 99, 99)
        status = lib.ng2_motion(C.byref(before), C.byref(after), direction, C.byref(out))
        self.assertIn(status, (0, 1))
        return out.kind, out.dx, out.dy

    def test_strong_gate_detail_confirms_one_move_with_transient_overlay(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction):
                    self.assertEqual((1, dx, dy), self.result(lib, *procedural_pair(direction), direction))

    def test_extra_evidence_requires_floor_unknown_goods_and_no_protection(self):
        before, after = procedural_pair()
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('goods', (1, 2)), ('gold_state', (0, 1))):
                for value in values:
                    pair = [deepcopy(before), deepcopy(after)]
                    setattr(pair[side], field, value)
                    cases.append((f'{side}:{field}:{value}', pair))
            for point in ((0, 0), (-1, 0), (8, 3)):
                pair = [deepcopy(before), deepcopy(after)]
                pair[side].protected_cells[cell(*point)] = 1
                cases.append((f'{side}:protected:{point}', pair))
            for point in ((0, 0), (-1, 0)):
                for kind in (0, 2, 3, 4, 5, 6):
                    pair = [deepcopy(before), deepcopy(after)]
                    pair[side].tiles[cell(*point)] = kind
                    cases.append((f'{side}:floor:{point}:{kind}', pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, *pair, 1))

    def test_extra_evidence_requires_exact_closed_gold_bracket(self):
        before, after = procedural_pair()
        cases = []
        for side in (0, 1):
            pair = [deepcopy(before), deepcopy(after)]
            gold = next(i for i, kind in enumerate(pair[side].tiles) if kind == 2)
            pair[side].tiles[gold] = 1
            cases.append((f'{side}:missing_gold', pair))
            pair = [deepcopy(before), deepcopy(after)]
            pair[side].tiles[cell(8, 3)] = 2
            cases.append((f'{side}:extra_gold', pair))
            pair = [deepcopy(before), deepcopy(after)]
            door = next(i for i, kind in enumerate(pair[side].tiles) if kind == 5)
            pair[side].tiles[door] = 1
            cases.append((f'{side}:open_gate', pair))
        for profile, lib in self.libraries.items():
            for name, pair in cases:
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, *pair, 1))

    def test_stationary_reverse_partial_and_two_tiles_are_not_one_move(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for amount in (0, -1, 2):
                    with self.subTest(profile=profile, direction=direction, amount=amount):
                        self.assertNotEqual(1, self.result(lib, *procedural_pair(direction, amount), direction)[0])
                before, after = procedural_pair(direction, pixels=8)
                # A partial translation is explicitly synthetic and has no
                # matching full-cell geometry; it cannot receive move credit.
                with self.subTest(profile=profile, direction=direction, partial=True):
                    self.assertNotEqual(1, self.result(lib, before, after, direction)[0])

    def test_weak_flat_and_ambiguous_repeating_texture_stays_unknown(self):
        for profile, lib in self.libraries.items():
            for name in ('weak', 'flat', 'repeating'):
                before, after = procedural_pair(weak_terrain=name == 'weak')
                if name == 'flat':
                    before.signature[:] = after.signature[:] = bytes([40]) * (W * H)
                elif name == 'repeating':
                    rng = random.Random(67068)
                    tile = [rng.randrange(12, 90) for _ in range(81)]
                    signature = bytes(tile[(y % 9) * 9 + x % 9] for y in range(H) for x in range(W))
                    before.signature[:] = after.signature[:] = signature
                with self.subTest(profile=profile, case=name):
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, 1))

    def test_existing_normal_moves_blocks_openings_and_unexpected_are_preserved(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(profile=profile, direction=direction, case='move'):
                    self.assertEqual((1, dx, dy), self.result(lib, *procedural_pair(direction, overlay=False), direction))
                before, _ = procedural_pair(direction, overlay=False)
                with self.subTest(profile=profile, direction=direction, case='stationary'):
                    self.assertEqual((2, 0, 0), self.result(lib, before, before, direction))
                with self.subTest(profile=profile, direction=direction, case='two_tiles'):
                    self.assertEqual((6, 2 * dx, 2 * dy), self.result(lib, *procedural_pair(direction, amount=2, overlay=False), direction))
                with self.subTest(profile=profile, direction=direction, case='tween'):
                    self.assertEqual((7, 0, 0), self.result(lib, *procedural_pair(direction, overlay=False, pixels=8), direction))
            for kind, expected in ((5, 3), (4, 4)):
                before, _ = procedural_pair(overlay=False)
                after = deepcopy(before)
                before.tiles[cell(-1, 0)] = kind
                after.tiles[cell(-1, 0)] = 1
                if kind == 5:
                    for scene in (before, after):
                        scene.tiles[cell(-1, -1)] = scene.tiles[cell(-1, 1)] = 2
                with self.subTest(profile=profile, case='opening', kind=kind):
                    self.assertEqual((expected, 0, 0), self.result(lib, before, after, 1))


if __name__ == '__main__':
    unittest.main()
