"""TEST036: gain LUT native化の全byte一致。ホスト速度は実機速度ではない。"""
import builtins
import ctypes as C
import hashlib
import math
import os
from pathlib import Path
import random
import subprocess
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from functools import lru_cache

from PIL import Image
from necroprobe import motion_stats as native, shop_navigation as nav
import test_motion_stats as old
from test_motion_stats import reference, ROOT


GAIN_COUNT = 73
GAIN_BYTES = 73 * 8
LUT_BYTES = 73 * 256


def python_luts(gains):
    """旧実装の独立した期待値。無効候補0の行は従来のzero-filled row。"""
    return b''.join(bytes(min(255, builtins.round(value * gain)) for value in range(256))
                    if gain else bytes(256) for gain in gains)


@lru_cache(maxsize=1)
def gain_vectors():
    values = {0.0, .65, 1.0, 1.25, 1.5, 1.55}
    for value in range(1, 256):
        for integer in range(396):
            ratio = (integer + .5) / value
            if .65 <= ratio <= 1.55:
                for gain in (math.nextafter(ratio, -math.inf), ratio, math.nextafter(ratio, math.inf)):
                    if .65 <= gain <= 1.55:
                        values.add(gain)
    rng = random.Random(36036)
    gains = sorted(values) + [rng.uniform(.65, 1.55) for _ in range(GAIN_COUNT * 20)]
    gains += [0.0] * (-len(gains) % GAIN_COUNT)
    return tuple(tuple(gains[start:start + GAIN_COUNT]) for start in range(0, len(gains), GAIN_COUNT))


class MotionLutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 既存のC統計と差分だけでもビルドできる。未実装symbolでsetUpを止めない。
        old.MotionStatsTests.setUpClass.__func__(cls)
        if C.sizeof(C.c_double) != 8:
            raise AssertionError('test ABI requires binary64')
        helper = getattr(cls.lib, 'necro_motion_luts', None)
        if helper is not None:
            helper.argtypes = [C.POINTER(C.c_double), C.c_uint32,
                               C.POINTER(C.c_ubyte), C.c_uint32]
            helper.restype = C.c_int

    def helper(self):
        helper = getattr(self.lib, 'necro_motion_luts', None)
        self.assertIsNotNone(helper, 'bounded native LUT helper not implemented')
        return helper

    def fake_native(self, result=0, corrupt=False):
        calls = []
        def helper(gains, gains_length, output, output_length):
            calls.append((gains_length, output_length))
            if result:
                return result
            data = python_luts([gains[index] for index in range(GAIN_COUNT)])
            for index, value in enumerate(data):
                output[index] = value
            if corrupt:
                output[0] ^= 1
            return 0
        return SimpleNamespace(necro_motion_stats=self.stats, necro_motion_diffs=self.diffs,
                               necro_motion_luts=helper), calls

    def compare_luts(self, gains):
        self.assertEqual(GAIN_COUNT, len(gains))
        inputs = (C.c_double * GAIN_COUNT)(*gains)
        output = (C.c_ubyte * LUT_BYTES)()
        self.assertEqual(0, self.helper()(inputs, GAIN_BYTES, output, LUT_BYTES))
        self.assertEqual(python_luts(gains), bytes(output))
        return bytes(output)

    def test_invoke_uses_native_luts_without_python_round_loop(self):
        # authoritative Red: valid helper exists in spy, but v20 ignores it and calls round.
        # Build/link/symbol errors are not used as behavior Red.
        expected, _ = reference(self.raw, self.raw)
        library, calls = self.fake_native()
        with patch.object(native, '_native', library), \
                patch.object(native, 'round', side_effect=AssertionError('Python LUT loop executed'), create=True):
            actual = native.scores(self.raw, self.raw)
        self.assertEqual(expected, actual)
        self.assertEqual([(GAIN_BYTES, LUT_BYTES)], calls)

    def test_lut_failure_invalidates_whole_native_comparison(self):
        library, calls = self.fake_native(result=-1)
        with patch.object(native, '_native', library), patch.object(native, 'ENGINE', 'native_i386'):
            self.assertIsNone(native.scores(self.raw, self.raw))
            self.assertIsNone(native._native)
            self.assertEqual('pillow', native.ENGINE)
        self.assertEqual([(GAIN_BYTES, LUT_BYTES)], calls)
        # Caller recalculates all 73 candidates; no partial/native-Pillow mix.
        before, after = nav.Scene({}, set(), 'unknown', set(), self.raw), nav.Scene({}, set(), 'unknown', set(), self.raw)
        with patch.object(native, '_native', None):
            expected = nav.motion(before, after, 'left')
        library, _ = self.fake_native(result=-1)
        with patch.object(native, '_native', library), patch.object(native, 'ENGINE', 'native_i386'):
            self.assertEqual(expected, nav.motion(before, after, 'left'))
            self.assertEqual('pillow', native.ENGINE)

    def test_loader_rejects_wrong_luts_even_when_old_statistics_selfcheck_passes(self):
        good, calls = self.fake_native()
        bad, bad_calls = self.fake_native(corrupt=True)
        with patch.object(native.sys, 'platform', 'linux'), patch.object(native.C, 'sizeof', return_value=4):
            with patch.object(native.C, 'CDLL', return_value=good):
                self.assertIs(good, native._load())
                self.assertGreater(len(calls), 0)
            with patch.object(native.C, 'CDLL', return_value=bad):
                self.assertIsNone(native._load())
                self.assertGreater(len(bad_calls), 0)
            missing = SimpleNamespace(necro_motion_stats=self.stats, necro_motion_diffs=self.diffs)
            with patch.object(native.C, 'CDLL', return_value=missing):
                self.assertIsNone(native._load())

    def test_fixed_clamps_zero_sentinel_and_half_even_ties_match_all_bytes(self):
        values = [0.0, .65, math.nextafter(.65, math.inf), 1.0, 1.25, 1.5,
                  math.nextafter(1.55, -math.inf), 1.55]
        gains = [values[index % len(values)] for index in range(GAIN_COUNT)]
        result = self.compare_luts(gains)
        self.assertEqual(bytes(256), result[:256])
        # 1.5*1=1.5→2, *3=4.5→4, *5=7.5→8 (ties to even, not away).
        row = result[5 * 256:6 * 256]
        self.assertEqual([2, 4, 8], [row[index] for index in (1, 3, 5)])
        self.assertEqual(255, row[255])

    def test_every_in_range_half_boundary_and_adjacent_binary_gains(self):
        # Cover every (integer+.5)/value threshold for byte inputs, including both ULP neighbors.
        self.helper()
        self.assertGreater(len(gain_vectors()) * GAIN_COUNT, 70_000)
        for batch in gain_vectors():
            self.compare_luts(batch)

    def test_i386_x87_same_vectors_with_shipping_codegen_flags(self):
        self.helper()
        # The same production C is linked to a freestanding ELF32 syscall runner.
        # No libc/host double implementation substitutes for actual x87 instructions.
        runner_source = r'''
extern int necro_motion_luts(const double *, unsigned int, unsigned char *, unsigned int);
static double gains[73];
static unsigned char luts[73*256];
static int io(int number, int fd, void *buffer, unsigned int length) {
    int result;
    __asm__ volatile ("int $0x80" : "=a"(result) : "0"(number), "b"(fd), "c"(buffer), "d"(length) : "memory");
    return result;
}
static __attribute__((noreturn)) void finish(int code) {
    __asm__ volatile ("int $0x80" : : "a"(1), "b"(code) : "memory");
    __builtin_unreachable();
}
void __attribute__((noreturn)) _start(void) {
    for (;;) {
        unsigned int done=0;
        while (done<sizeof(gains)) {
            int count=io(3,0,((unsigned char *)gains)+done,sizeof(gains)-done);
            if (!count) finish(done ? 91 : 0);
            if (count<0) finish(92);
            done+=(unsigned int)count;
        }
        if (necro_motion_luts(gains,sizeof(gains),luts,sizeof(luts))) finish(93);
        done=0;
        while (done<sizeof(luts)) {
            int count=io(4,1,luts+done,sizeof(luts)-done);
            if (count<=0) finish(94);
            done+=(unsigned int)count;
        }
    }
}
'''
        source = Path(self.tmp.name) / 'lut-runner.c'
        binary = Path(self.tmp.name) / 'lut-runner-i386'
        source.write_text(runner_source)
        subprocess.run(['gcc', '-m32', '-march=i386', '-mno-sse', '-mno-sse2', '-O2', '-fPIC',
                        '-ffreestanding', '-fno-stack-protector', '-fno-builtin', '-nostdlib',
                        '-static', '-no-pie', '-Wl,--build-id=none', '-Wl,-e,_start',
                        str(ROOT / 'necroprobe/motion_stats.c'), str(source), '-o', str(binary)],
                       check=True, capture_output=True)
        self.assertEqual(b'\x7fELF\x01\x01', binary.read_bytes()[:6])
        data = b''.join(struct.pack('<73d', *batch) for batch in gain_vectors())
        try:
            result = subprocess.run([str(binary)], input=data, capture_output=True, timeout=30)
        except OSError as exc:
            if exc.errno == 8:
                emulator = os.environ.get('NECRO_QEMU_I386')
                if not emulator:
                    self.skipTest('host kernel cannot execute ELF32; no x87 validation established')
                result = subprocess.run([emulator, str(binary)], input=data, capture_output=True, timeout=30)
            else:
                raise
        self.assertEqual(0, result.returncode, result.stderr)
        expected = b''.join(python_luts(batch) for batch in gain_vectors())
        self.assertEqual(expected, result.stdout)

    def test_random_gain_rows_preserve_python_byte_rounding(self):
        rng = random.Random(36036)
        for _ in range(20):
            self.compare_luts([rng.uniform(.65, 1.55) for _ in range(GAIN_COUNT)])

    def test_raw_abi_rejects_lengths_nulls_and_invalid_gains_without_output_writes(self):
        helper = self.helper()
        inputs = (C.c_double * GAIN_COUNT)(*([1.0] * GAIN_COUNT))
        def untouched(gains, size, length):
            output = (C.c_ubyte * LUT_BYTES)(*([165] * LUT_BYTES))
            self.assertEqual(-1, helper(gains, size, output, length))
            self.assertEqual(bytes([165]) * LUT_BYTES, bytes(output))
        untouched(None, GAIN_BYTES, LUT_BYTES)
        self.assertEqual(-1, helper(inputs, GAIN_BYTES, None, LUT_BYTES))
        for length in (0, GAIN_BYTES - 1, GAIN_BYTES + 1, 0xffffffff):
            untouched(inputs, length, LUT_BYTES)
        for length in (0, LUT_BYTES - 1, LUT_BYTES + 1, 0xffffffff):
            untouched(inputs, GAIN_BYTES, length)
        for index in (0, GAIN_COUNT - 1):
            for gain in (-1.0, math.nextafter(0.0, -math.inf), math.nextafter(.65, -math.inf),
                         math.nextafter(1.55, math.inf), math.nan, math.inf, -math.inf):
                invalid = (C.c_double * GAIN_COUNT)(*([1.0] * GAIN_COUNT)); invalid[index] = gain
                untouched(invalid, GAIN_BYTES, LUT_BYTES)
        guarded = (C.c_ubyte * (LUT_BYTES + 2))(*([165] * (LUT_BYTES + 2)))
        output = C.cast(C.byref(guarded, 1), C.POINTER(C.c_ubyte))
        self.assertEqual(0, helper(inputs, GAIN_BYTES, output, LUT_BYTES))
        self.assertEqual((165, 165), (guarded[0], guarded[-1]))
        self.assertEqual(bytes(range(256)) * GAIN_COUNT, bytes(guarded)[1:-1])

    def test_test035_all_73_scores_match_original_pillow_on_real_pairs(self):
        folder = os.environ.get('NECRO_TEST035_FRAMES')
        if not folder:
            self.skipTest('external TEST035 frames not supplied')
        self.helper()
        expected_hashes = {
            'run-099.jpg': '3205b1e1e6c3bed2d2afe87206a2afa9d602859cb20b4d74788a0278733a5be0',
            'run-101.jpg': '51bf7ef7a79fedab7c88b82b645c416e515fec5dfcd9605c0827f2ac4017f07d',
            'run-102.jpg': 'b893e3a351c57f347d128189a13830bc90c9ffb4f172dd4db661e98cd620e18a',
            'run-103.jpg': '0a1c856c826de86d408a787eb89f444298b61980a70896ebb7c4f1c0955b1c6a',
            'run-104.jpg': '497db2abceaa1dc6e87cd8fa10171c639a91b47d10f21bf0860c9d322b2ba2e2',
            'run-105.jpg': '47f0fe7f7da0cf1102aaffb6bd271a627cf82b71efd6fbb5633a2d36e3e601bd',
            'run-106.jpg': 'dd94bdc95e4b4ff7647832007e37aca2670bc0ad85dcad32fb2cf0b72e446cc6',
        }
        scenes = {}
        for name, digest in expected_hashes.items():
            path = Path(folder) / name
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:
                self.assertEqual((896, 414), image.size)
                scenes[name] = nav.scan(image.convert('RGB'))
        for first, second, direction in [('run-101.jpg', 'run-102.jpg', 'left'),
                ('run-102.jpg', 'run-103.jpg', 'up'), ('run-103.jpg', 'run-104.jpg', 'left'),
                ('run-104.jpg', 'run-105.jpg', 'left'), ('run-099.jpg', 'run-106.jpg', 'left')]:
            before, after = scenes[first], scenes[second]
            a, b = (nav._motion_view(scene.signature)[0] for scene in (before, after))
            expected, _ = reference(a, b)
            with patch.object(native, '_native', self.lib):
                self.assertEqual(expected, native.scores(a, b))
            for count in (1, 2, 3, 4):
                with patch.object(native, '_native', None):
                    decision = nav.motion(before, after, direction, expected_steps=count)
                with patch.object(native, '_native', self.lib):
                    self.assertEqual(decision, nav.motion(before, after, direction, expected_steps=count))


if __name__ == '__main__':
    unittest.main()
