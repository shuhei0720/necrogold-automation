"""TEST-020: exact native motion parity; host timing is not iPhone timing."""
import ctypes as C
import hashlib
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageStat
from necroprobe import motion_stats as native
from necroprobe import shop_navigation as nav

ROOT = Path(__file__).resolve().parents[1]
LENGTH = 224 * 104
CANDIDATES = [(0, 0)] + [(amount * dx, amount * dy) for amount in range(1, 19)
                         for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))]


def reference(before, after):
    """Independent copy of the original Pillow scoring, including crop bounds."""
    old, new = (Image.frombytes('L', (224, 104), raw) for raw in (before, after))
    valid = Image.new('L', (224, 104))
    valid.paste(255, (40, 20, 179, 79))
    valid.paste(0, (90, 36, 139, 79))
    active_old = ImageChops.darker(old.point([255 if v > 6 else 0 for v in range(256)]), valid)
    active_new = ImageChops.darker(new.point([255 if v > 6 else 0 for v in range(256)]), valid)
    scores, stats = [], []
    for sx, sy in CANDIDATES:
        box = (max(0, -sx), max(0, -sy), min(224, 224 - sx), min(104, 104 - sy))
        other = (box[0] + sx, box[1] + sy, box[2] + sx, box[3] + sy)
        a, b = old.crop(box), new.crop(other)
        mask = ImageChops.darker(active_old.crop(box), active_new.crop(other))
        sa, sb = ImageStat.Stat(a, mask), ImageStat.Stat(b, mask)
        count = mask.histogram()[255]
        stats.extend((count, sa.sum[0], sb.sum[0], sa.sum2[0], sb.sum2[0]))
        score = float('inf')
        if count >= 300:
            contrast = (sa.stddev[0] + sb.stddev[0]) / 2
            if contrast >= 2.5 and min(sa.mean[0], sb.mean[0]) >= 6:
                gain = max(.65, min(1.55, sa.mean[0] / sb.mean[0]))
                b = b.point([min(255, round(v * gain)) for v in range(256)])
                score = ImageStat.Stat(ImageChops.difference(a, b), mask).mean[0] / contrast
        scores.append((score, sx, sy))
    return scores, stats


def signature(image):
    raw = image.convert('L').tobytes()
    return b''.join(raw[y * 896:(y + 1) * 896:4] for y in range(0, 414, 4))


def shifted(raw, sx, sy):
    image = Image.new('L', (224, 104))
    image.paste(Image.frombytes('L', (224, 104), raw), (sx, sy))
    return image.tobytes()


def scene(raw):
    return nav.Scene({}, set(), 'unknown', set(), raw)


class MotionStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        lib = Path(cls.tmp.name) / 'motion-host.so'
        subprocess.run(['gcc', '-O2', '-fPIC', '-ffreestanding', '-fno-stack-protector',
                        '-fno-builtin', '-shared', '-nostdlib', '-Wl,--build-id=none',
                        str(ROOT / 'necroprobe/motion_stats.c'), '-o', str(lib)],
                       check=True, capture_output=True)
        cls.lib = C.CDLL(str(lib))
        args = [C.c_char_p, C.c_uint32, C.c_char_p, C.c_uint32]
        output = [C.POINTER(C.c_uint32), C.c_uint32]
        cls.stats = cls.lib.necro_motion_stats
        cls.stats.argtypes, cls.stats.restype = args + output, C.c_int
        cls.diffs = cls.lib.necro_motion_diffs
        cls.diffs.argtypes, cls.diffs.restype = args + [C.c_char_p, C.c_uint32] + output, C.c_int
        rng = random.Random(20020)
        cls.raw = bytes(rng.randrange(7, 256) for _ in range(LENGTH))

    def compare(self, before, after):
        expected, statistics = reference(before, after)
        self.assertEqual(statistics, list(native._statistics(self.lib, before, after)))
        with patch.object(native, '_native', self.lib):
            actual = native.scores(before, after)
        self.assertEqual(expected, actual)  # exact floats, all73 in original order
        self.assertEqual(CANDIDATES, [(sx, sy) for _, sx, sy in actual])
        return actual

    def test_01_all_scores_four_directions_tween_two_tiles_reverse_and_blocked(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            for amount, expected in ((0, 'blocked'), (9, 'moved'), (8, 'tween'),
                                     (1, 'tween'), (18, 'unexpected'), (-9, 'unexpected')):
                with self.subTest(direction=direction, amount=amount):
                    after = shifted(self.raw, -amount * dx, -amount * dy)
                    self.compare(self.raw, after)
                    with patch.object(native, '_native', self.lib):
                        self.assertEqual(expected, nav.motion(scene(self.raw), scene(after), direction))
        # The public scorer executes both native passes without Pillow statistics.
        with patch.object(native, '_native', self.lib), patch.object(
                ImageStat, 'Stat', side_effect=AssertionError('Pillow fallback executed')):
            self.assertEqual(0.0, native.scores(self.raw, self.raw)[0][0])
            self.assertEqual('blocked', nav.motion(scene(self.raw), scene(self.raw), 'left'))
            self.assertEqual('moved', nav.motion(scene(self.raw), scene(shifted(self.raw, 9, 0)), 'left'))

    def test_02_mask_count_contrast_darkness_gain_and_unrelated_negative(self):
        rng = random.Random(20021)
        cases = [(self.raw, bytes(LENGTH)), (bytes([6]) * LENGTH, self.raw),
                 (bytes([7]) * LENGTH, bytes([7]) * LENGTH),
                 (self.raw, rng.randbytes(LENGTH))]
        # Broad intensity ratios cover both gain clamps and Python half-even round.
        for low, high in ((8, 80), (20, 30), (75, 50), (150, 75), (7, 11)):
            first = bytes(low + i % 8 for i in range(LENGTH))
            second = bytes(high + i % 8 for i in range(LENGTH))
            cases.append((first, second))
        # Exact gain1.5 includes half-even LUT ties, without saturation.
        cases.append((bytes(3 * (7 + i % 64) for i in range(LENGTH)),
                      bytes(2 * (7 + i % 64) for i in range(LENGTH))))
        # Each active sample is >6; a value6 must not increase the count to300.
        positions = [y * 224 + x for y in range(20, 36) for x in range(40, 179)]
        for count in (299, 300, 301):
            data = bytearray(LENGTH)
            for i, position in enumerate(positions[:count]):
                data[position] = 20 + i % 17
            data[positions[count]] = 6
            cases.append((bytes(data), bytes(data)))
        # Exact stddev2.5 and just-below variants exercise the strict boundary.
        for values in ((20, 25), (20, 24)):
            data = bytearray(LENGTH)
            for i, position in enumerate(positions[:300]):
                data[position] = values[i % 2]
            cases.append((bytes(data), bytes(data)))
        for i, (before, after) in enumerate(cases):
            with self.subTest(case=i):
                self.compare(before, after)
                if i < 4:
                    with patch.object(native, '_native', self.lib):
                        self.assertEqual('unknown', nav.motion(scene(before), scene(after), 'left'))
        self.assertTrue(math.isfinite(self.compare(*cases[-2])[0][0]))
        self.assertTrue(math.isinf(self.compare(*cases[-1])[0][0]))
        # Inactive areas including outer edges and the player cutout cannot vote.
        before, after = bytearray(self.raw), bytearray(self.raw)
        for y in range(104):
            for x in range(224):
                if not (40 <= x < 179 and 20 <= y < 79 and not (90 <= x < 139 and y >= 36)):
                    after[y * 224 + x] = 255 - before[y * 224 + x]
        actual = self.compare(bytes(before), bytes(after))
        self.assertEqual(0.0, actual[0][0])

    def test_03_raw_abi_null_lengths_and_output_sentinels(self):
        raw, luts = bytes([20]) * LENGTH, bytes(range(256)) * 73
        for function, count, prefix in ((self.stats, 365, [raw, LENGTH, raw, LENGTH]),
                                         (self.diffs, 73, [raw, LENGTH, raw, LENGTH, luts, 73 * 256])):
            length = count * 4
            for index in range(0, len(prefix), 2):
                for replacement in (None,):
                    args = list(prefix); args[index] = replacement
                    out = (C.c_uint32 * count)(*([0xA5A5A5A5] * count))
                    self.assertEqual(-1, function(*args, out, length))
                    self.assertEqual([0xA5A5A5A5] * count, list(out))
            for index in range(1, len(prefix), 2):
                for bad_length in (0, prefix[index] - 1, prefix[index] + 1, 0xFFFFFFFF):
                    args = list(prefix); args[index] = bad_length
                    out = (C.c_uint32 * count)(*([0xA5A5A5A5] * count))
                    self.assertEqual(-1, function(*args, out, length))
                    self.assertEqual([0xA5A5A5A5] * count, list(out))
            for bad_length in (0, length - 1, length + 1, 0xFFFFFFFF):
                out = (C.c_uint32 * count)(*([0xA5A5A5A5] * count))
                self.assertEqual(-1, function(*prefix, out, bad_length))
                self.assertEqual([0xA5A5A5A5] * count, list(out))
            self.assertEqual(-1, function(*prefix, None, length))
            guard = (C.c_uint32 * (count + 2))(*([0xA5A5A5A5] * (count + 2)))
            output = C.cast(C.byref(guard, 4), C.POINTER(C.c_uint32))
            self.assertEqual(0, function(*prefix, output, length))
            self.assertEqual((0xA5A5A5A5, 0xA5A5A5A5), (guard[0], guard[-1]))

    def test_04_elf32_hash_imports_loader_selfcheck_and_full_fallback(self):
        artifact = ROOT / 'necroprobe/motion_stats_i386.so'
        blob = artifact.read_bytes()
        self.assertEqual(b'\x7fELF\x01\x01', blob[:6])
        self.assertEqual(3, int.from_bytes(blob[18:20], 'little'))
        self.assertEqual(native._EXPECTED_SHA256, hashlib.sha256(blob).hexdigest())
        symbols = subprocess.run(['nm', '-u', str(artifact)], capture_output=True, text=True, check=True)
        self.assertEqual('', symbols.stdout.strip())
        dynamic = subprocess.run(['readelf', '-d', str(artifact)], capture_output=True, text=True, check=True)
        self.assertNotIn('NEEDED', dynamic.stdout)
        with patch.object(native.sys, 'platform', 'linux'), patch.object(native.C, 'sizeof', return_value=4), \
                patch.object(native.C, 'CDLL', return_value=self.lib) as loader:
            self.assertIs(self.lib, native._load())
            loader.reset_mock()
            with patch.object(Path, 'read_bytes', return_value=b'corrupt'):
                self.assertIsNone(native._load()); loader.assert_not_called()
            with patch.object(native.C, 'CDLL', side_effect=OSError('unavailable')):
                self.assertIsNone(native._load())
            with patch.object(native.C, 'CDLL', return_value=object()):
                self.assertIsNone(native._load())
            for name, value in (('_statistics', None), ('_differences', None),
                                ('_statistics', (C.c_uint32 * 365)()),
                                ('_differences', (C.c_uint32 * 73)())):
                with patch.object(native, name, return_value=value):
                    self.assertIsNone(native._load())
        for platform, width in (('linux', 8), ('darwin', 4)):
            with patch.object(native.sys, 'platform', platform), patch.object(native.C, 'sizeof', return_value=width), \
                    patch.object(native.C, 'CDLL') as loader:
                self.assertIsNone(native._load()); loader.assert_not_called()
        with patch.object(native, '_native', self.lib):
            for invalid in (None, 'x', b'x', bytearray(LENGTH), bytes(LENGTH + 1)):
                self.assertIsNone(native.scores(invalid, self.raw))
                self.assertIsNone(native.scores(self.raw, invalid))
            self.assertIs(self.lib, native._native)
        for failure in ('_statistics', '_differences'):
            with patch.object(native, '_native', self.lib), patch.object(native, 'ENGINE', 'native_i386'), \
                    patch.object(native, failure, return_value=None):
                self.assertIsNone(native.scores(self.raw, self.raw))
                self.assertIsNone(native._native)
                self.assertEqual('pillow', native.ENGINE)
        with patch.object(native, '_native', None):
            self.assertIsNone(native.scores(self.raw, self.raw))
        with patch.object(native, '_native', self.lib), patch.object(native, 'ENGINE', 'native_i386'), \
                patch.object(native, '_invoke', side_effect=ValueError('bad native statistics')):
            self.assertIsNone(native.scores(self.raw, self.raw))
            self.assertEqual('pillow', native.ENGINE)

    def test_05_optional_real_frames_and_legacy_fixture_pairs(self):
        folder, legacy = os.environ.get('NECRO_MOTION_FRAMES'), os.environ.get('NECRO_NAV_FIXTURES')
        if not folder and not legacy:
            self.skipTest('external real frames not supplied')
        pairs = []
        if folder:
            paths = sorted(p for p in Path(folder).rglob('*') if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
            self.assertGreater(len(paths), 0)
            frames = []
            for path in paths:
                with Image.open(path) as image:
                    if image.size == (896, 414):
                        frames.append((path.name, signature(image)))
            self.assertGreater(len(frames), 0)
            pairs.extend((name, raw, raw, None) for name, raw in frames)
            pairs.extend((f'{a[0]}->{b[0]}', a[1], b[1], None) for a, b in zip(frames, frames[1:]))
        if legacy:
            frames = {}
            for number in (119, 121, 124):
                with Image.open(Path(legacy) / f'floor-{number:03}.jpg') as image:
                    frames[number] = signature(image)
            pairs.extend((f'119->{number}', frames[119], frames[number], expected)
                         for number, expected in ((121, 'tween'), (124, 'moved')))
        for name, before, after, expected in pairs:
            with self.subTest(pair=name):
                self.compare(before, after)
                for direction in nav.DIRECTIONS:
                    with patch.object(native, '_native', None):
                        reference_decision = nav.motion(scene(before), scene(after), direction)
                    with patch.object(native, '_native', self.lib):
                        self.assertEqual(reference_decision, nav.motion(scene(before), scene(after), direction))
                if expected:
                    with patch.object(native, '_native', self.lib):
                        self.assertEqual(expected, nav.motion(scene(before), scene(after), 'left'))


if __name__ == '__main__':
    unittest.main()
