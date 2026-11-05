"""固定RGB native scanの3群。全画像の実資料比較はrepo外で別記録する。"""
import ctypes as C
import hashlib
import importlib
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from necroprobe import gold_scan


RGB_LENGTH = 896 * 414 * 3
OUTPUT_LENGTH = 49
ROOT = Path(__file__).resolve().parents[1]


class NativeScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="necro-native-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        library = Path(cls.temp.name) / "gold_scan_host.so"
        subprocess.run(["gcc", "-O2", "-fPIC", "-ffreestanding", "-fno-stack-protector",
                        "-fno-builtin", "-shared", "-nostdlib", "-Wl,--build-id=none",
                        str(ROOT / "necroprobe/gold_scan_native.c"), "-o", str(library)],
                       check=True, capture_output=True, text=True)
        cls.library = C.CDLL(str(library))
        cls.function = cls.library.necro_gold_scan
        cls.function.argtypes = [C.c_char_p, C.c_uint32, C.POINTER(C.c_ubyte), C.c_uint32]
        cls.function.restype = C.c_int
        cls.module = importlib.import_module("necroprobe.native_scan")

    def scan(self, image):
        output = (C.c_ubyte * OUTPUT_LENGTH)()
        self.assertEqual(0, self.function(image.tobytes(), RGB_LENGTH, output, OUTPUT_LENGTH))
        return output[0], list(output[1:])

    def assert_parity(self, image):
        expected = gold_scan._gold_peak(image), gold_scan._fingerprint(image.convert("L"))
        self.assertEqual(expected, self.scan(image))

    def test_01_pillow_parity_at_edges_color_and_decision_boundaries(self):
        for color in ((0, 0, 0), (255, 255, 255), (210, 170, 30)):
            with self.subTest(color=color):
                self.assert_parity(Image.new("RGB", (896, 414), color))
        # Horizontal rounding is applied before vertical rounding; these pairs
        # deliberately straddle the unchanged clear/unknown/candidate cutoffs.
        for width, height, peak in ((19, 15, 99), (15, 19, 100), (16, 24, 134), (24, 16, 135)):
            with self.subTest(peak=peak):
                image = Image.new("RGB", (896, 414))
                image.paste((210, 170, 30), (300, 100, 300 + width, 100 + height))
                self.assertEqual(peak, gold_scan._gold_peak(image))
                self.assertEqual(peak, self.scan(image)[0])
                self.assert_parity(image)
        # Each exclusion boundary and each image edge participates in a window.
        for box in ((300, 0, 335, 5), (0, 70, 6, 105), (888, 85, 895, 120),
                    (129, 40, 157, 67), (649, 66, 677, 93), (703, 301, 731, 329),
                    (391, 307, 419, 335), (471, 307, 499, 335), (300, 366, 335, 393)):
            with self.subTest(edge=box):
                image = Image.new("RGB", (896, 414))
                ImageDraw.Draw(image).rectangle(box, fill=(210, 170, 30))
                self.assert_parity(image)
        for box in ((0, 0, 143, 54), (663, 0, 896, 80), (717, 315, 896, 414),
                    (405, 321, 485, 414), (0, 380, 896, 414)):
            with self.subTest(excluded=box):
                image = Image.new("RGB", (896, 414))
                image.paste((210, 170, 30), box)
                self.assertEqual(0, self.scan(image)[0])
                self.assert_parity(image)
        for color, included in (((52, 42, 15), False), ((53, 42, 15), True),
                ((200, 137, 30), False), ((200, 138, 30), True),
                ((200, 183, 30), True), ((200, 184, 30), False),
                ((200, 150, 10), False), ((200, 150, 11), True),
                ((200, 150, 86), True), ((200, 150, 87), False)):
            with self.subTest(color_boundary=color):
                image = Image.new("RGB", (896, 414))
                image.paste(color, (300, 100, 340, 140))
                self.assertEqual(255 if included else 0, self.scan(image)[0])
                self.assert_parity(image)
        # Exercise every channel value repeatedly, rather than only one gold.
        generator = random.Random(15015)
        self.assert_parity(Image.frombytes("RGB", (896, 414), generator.randbytes(RGB_LENGTH)))
        # Exact half means must use Python's round-to-even, including grayscale.
        image = Image.new("RGB", (896, 414))
        image.paste((1, 1, 1), (224, 70, 252, 118))
        image.paste((1, 1, 1), (280, 70, 336, 118))
        image.paste((2, 2, 2), (280, 70, 308, 118))
        self.assertEqual([0, 2], self.scan(image)[1][:2])
        self.assert_parity(image)
        image = Image.new("RGB", (896, 414), (100, 100, 100))
        initial = self.scan(image)[1]
        for difference, changed in ((11, False), (12, True)):
            moved = image.copy()
            value = 100 + difference
            moved.paste((value, value, value), (224, 70, 392, 166))
            self.assert_parity(moved)
            self.assertEqual(changed, gold_scan.changed(initial, self.scan(moved)[1]))

    def test_02_invalid_buffers_never_write_and_python_rejects_bad_values(self):
        for data, length, output_length in ((None, RGB_LENGTH, 49), (b"x", 1, 49),
                (b"", 0, 49), (b"x", RGB_LENGTH - 1, 49),
                (b"x", RGB_LENGTH + 1, 49), (b"x", 0xffffffff, 49),
                (b"x", RGB_LENGTH, 0), (b"x", RGB_LENGTH, 48), (b"x", RGB_LENGTH, 50)):
            with self.subTest(length=length, output_length=output_length):
                output = (C.c_ubyte * OUTPUT_LENGTH)(*([99] * OUTPUT_LENGTH))
                self.assertEqual(-1, self.function(data, length, output, output_length))
                self.assertEqual([99] * OUTPUT_LENGTH, list(output))
        self.assertEqual(-1, self.function(b"x", RGB_LENGTH, None, OUTPUT_LENGTH))
        with patch.object(self.module, "_native", self.library), \
             patch.object(self.module, "ENGINE", "native_i386"):
            for value in (None, "x", bytearray(RGB_LENGTH), memoryview(bytes(RGB_LENGTH)),
                          b"", b"x", bytes(RGB_LENGTH - 1), bytes(RGB_LENGTH + 1)):
                with self.subTest(type=type(value).__name__):
                    self.assertIsNone(self.module.scan(value))
            self.assertEqual((0, [0] * 48), self.module.scan(bytes(RGB_LENGTH)))

    def test_03_native_selection_requires_platform_hash_and_known_outputs(self):
        native = self.module
        artifact = (ROOT / "necroprobe/gold_scan_i386.so").read_bytes()
        self.assertEqual(b"\x7fELF\x01\x01", artifact[:6])
        self.assertEqual(3, int.from_bytes(artifact[18:20], "little"))
        self.assertEqual(native._EXPECTED_SHA256, hashlib.sha256(artifact).hexdigest())
        with patch.object(native.sys, "platform", "linux"), \
             patch.object(native.C, "sizeof", return_value=4), \
             patch.object(native.C, "CDLL", return_value=self.library) as loader:
            self.assertIs(self.library, native._load())
            loader.reset_mock()
            with patch.object(Path, "read_bytes", return_value=b"corrupt"):
                self.assertIsNone(native._load())
                loader.assert_not_called()
            with patch.object(Path, "read_bytes", side_effect=OSError("missing")):
                self.assertIsNone(native._load())
            with patch.object(native, "_invoke", return_value=(0, [0] * 48)):
                self.assertIsNone(native._load())
        with patch.object(native.sys, "platform", "linux"), \
             patch.object(native.C, "sizeof", return_value=8), \
             patch.object(native.C, "CDLL") as loader:
            self.assertIsNone(native._load())
            loader.assert_not_called()
        with patch.object(native.sys, "platform", "darwin"), \
             patch.object(native.C, "sizeof", return_value=4):
            self.assertIsNone(native._load())
        with patch.object(native, "_native", None), patch.object(native, "ENGINE", "pillow"):
            self.assertIsNone(native.scan(bytes(RGB_LENGTH)))
            self.assertEqual("pillow", native.ENGINE)
        with patch.object(native, "_native", self.library), \
             patch.object(native, "ENGINE", "native_i386"), \
             patch.object(native, "_invoke", return_value=None):
            self.assertIsNone(native.scan(bytes(RGB_LENGTH)))
            self.assertEqual("pillow", native.ENGINE)


if __name__ == "__main__":
    unittest.main()
