"""TEST043 known-image C/Pillow parity; this is not an unseen evaluation."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from unittest.mock import patch
from PIL import Image
from necroprobe import beat_sync, gold_scan, navigation_stats, native_scan, shop_navigation

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "patches/loopctrl/ngg2"
MANIFEST = ROOT / "tests/test043-fixtures.json"
KINDS = {"floor": 1, "gold": 2, "stone": 3, "dirt": 4, "door": 5, "item": 6}


def required_fixtures():
    """Required TEST043 mode: every fixed image must exist and hash-match."""
    root = Path(os.environ.get("NECRO_TEST043_FIXTURE_ROOT", "/workspace/analysis-evidence"))
    manifest = json.loads(MANIFEST.read_text())
    if manifest["count"] != len(manifest["images"]) or manifest["count"] < 20:
        raise AssertionError("TEST043 fixture manifest requires at least20 images")
    if len({entry["sha256"] for entry in manifest["images"]}) != manifest["count"]:
        raise AssertionError("TEST043 fixture manifest must contain unique images")
    for entry in manifest["images"]:
        path = root / entry["path"]
        if not path.is_file():
            raise AssertionError(f"missing required TEST043 fixture: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise AssertionError(f"TEST043 fixture hash mismatch: {path}")
        yield path


def required_profile_fixtures():
    """All 203 required image paths; missing private evidence is a local failure."""
    sets = (("test043-fixtures.json", "NECRO_TEST043_FIXTURE_ROOT", 66),
            ("test046-fixtures.json", "NECRO_TEST046_FIXTURE_ROOT", 8),
            ("test047-fixtures.json", "NECRO_TEST047_FIXTURE_ROOT", 5),
            ("test049-fixtures.json", "NECRO_TEST049_FIXTURE_ROOT", 8),
            ("test050-fixtures.json", "NECRO_TEST050_FIXTURE_ROOT", 11),
            ("test052-fixtures.json", "NECRO_TEST052_FIXTURE_ROOT", 9),
            ("test053-fixtures.json", "NECRO_TEST053_FIXTURE_ROOT", 17),
            ("test054-fixtures.json", "NECRO_TEST054_FIXTURE_ROOT", 17),
            ("test055-fixtures.json", "NECRO_TEST055_FIXTURE_ROOT", 11),
            ("test057-fixtures.json", "NECRO_TEST057_FIXTURE_ROOT", 18),
            ("test058-fixtures.json", "NECRO_TEST058_FIXTURE_ROOT", 7),
            ("test059-fixtures.json", "NECRO_TEST059_FIXTURE_ROOT", 12),
            ("test060-fixtures.json", "NECRO_TEST060_FIXTURE_ROOT", 14))
    for filename, variable, count in sets:
        manifest = json.loads((ROOT / "tests" / filename).read_text())
        if type(manifest["count"]) is not int or manifest["count"] != count \
                or len(manifest["images"]) != count \
                or len({entry["path"] for entry in manifest["images"]}) != count:
            raise AssertionError(f"invalid required profile manifest: {filename}")
        root = Path(os.environ.get(variable, "/workspace/analysis-evidence"))
        for entry in manifest["images"]:
            relative = Path(entry["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise AssertionError(f"invalid profile fixture path: {relative}")
            path = root / relative
            if not path.is_file():
                raise AssertionError(f"missing required profile fixture: {path}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise AssertionError(f"profile fixture hash mismatch: {path}")
            yield filename, entry, path


def synthetic_floor():
    image = Image.new("RGB", (896,414))
    for name in ("icon", "footer", "zone_one", "floor_one"):
        box, _, _, mask = gold_scan._TEMPLATES[name]
        image.paste(Image.new("RGB", mask.size, (180,180,180)), box[:2], mask)
    return image


def paint_template(image, name, color=(200,200,200)):
    box, _, _, mask = gold_scan._TEMPLATES[name]
    image.paste(Image.new("RGB", mask.size, color), box[:2], mask)

class NativeScene(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ("abi_version", "struct_size")] + [
        (name, C.c_int32) for name in ("state", "restart_label", "gold_state", "gold_peak", "goods")] + [
        ("tiles", C.c_uint8 * 230), ("protected_cells", C.c_uint8 * 230),
        ("signature", C.c_uint8 * 23296), ("fingerprint", C.c_uint8 * 48),
        ("beat_valid", C.c_int32), ("beat_remaining", C.c_double),
        ("beat_spacing", C.c_double), ("beat_center", C.c_double)]

class NativePerceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="ngg2-perception-")
        output = Path(cls.directory.name) / "perception.so"
        subprocess.run(["cc", "-std=c99", "-O2", "-fno-fast-math", "-ffp-contract=off",
                        "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared",
                        str(CORE / "NG2Perception.c"), "-lm", "-o", str(output)], check=True)
        cls.native = C.CDLL(str(output))
        cls.native.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
        cls.native.ng2_analyze_rgba.restype = C.c_int
        cls.native.ng2_fingerprint_changed.argtypes = [C.c_void_p, C.c_void_p]
        cls.native.ng2_fingerprint_changed.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def analyze(self, image, padding=0):
        raw = image.convert("RGBA").tobytes()
        if padding:
            raw = b"".join(raw[y*3584:(y+1)*3584] + bytes([13])*padding for y in range(414))
        out = NativeScene()
        self.assertEqual(self.native.ng2_analyze_rgba(raw, len(raw), 896*4+padding, C.byref(out)), 0)
        self.assertEqual(out.abi_version, 1)
        self.assertEqual(out.struct_size, C.sizeof(NativeScene))
        return out

    def test_known_floor_public_entry(self):
        path = next(p for p in required_fixtures() if "test042" in str(p) and p.name == "run-101.jpg")
        with Image.open(path) as source:
            image = source.convert("RGB")
        self.assertEqual(gold_scan.analyze_image(image)["state"], "floor")
        self.assertEqual(self.analyze(image).state, 2)

    def assert_reference(self, image, padding=0):
        out = self.analyze(image, padding)
        # Force independent Pillow paths rather than the old native artifacts.
        with patch.object(native_scan, "_native", None), patch.object(navigation_stats, "_native", None):
            basic = gold_scan.analyze_image(image)
            self.assertEqual(out.state, {"unknown": 0, "pause": 1, "floor": 2}[basic["state"]])
            self.assertEqual(out.restart_label, basic["restart_label"])
            self.assertEqual(out.gold_state, {"unknown": 0, "clear": 1, "candidate": 2}[basic["gold"]])
            self.assertEqual(out.gold_peak, basic["gold_peak"])
            self.assertEqual(bytes(out.fingerprint), bytes(basic["fingerprint"] or [0]*48))
            if out.state != 2:
                self.assertEqual(bytes(out.tiles), bytes(230))
                self.assertEqual(out.goods, 0)
                self.assertEqual(out.beat_valid, 0)
                return out
            scene = shop_navigation.scan(image)
            expected_tiles = bytes(KINDS.get(scene.tiles.get((i, j)), 0)
                                   for j in range(-5, 5) for i in range(-11, 12))
            self.assertEqual(bytes(out.tiles), expected_tiles)
            self.assertEqual(bytes(out.protected_cells), bytes((i,j) in scene.protected
                             for j in range(-5, 5) for i in range(-11, 12)))
            self.assertEqual(out.goods, {"unknown": 0, "partial": 1, "visible": 2}[scene.goods])
            self.assertEqual(bytes(out.signature), scene.signature)
            feature = beat_sync.extract(image)
            self.assertEqual(out.beat_valid, feature is not None)
            if feature:
                for value, key in ((out.beat_remaining, "remaining"), (out.beat_spacing, "spacing_px"),
                                   (out.beat_center, "center_px")):
                    self.assertAlmostEqual(value, feature[key], places=13)
        return out

    def test_required_known_image_parity(self):
        count = 0
        for path in required_fixtures():
            with self.subTest(path=path.name, run=path.parent.name):
                with Image.open(path) as source:
                    image = source.convert("RGB")
                self.assert_reference(image)
                count += 1
        self.assertGreaterEqual(count, 20)

    def test_required_test046_capture_replay(self):
        """All five received startup frames are mandatory known-image replays."""
        root = Path(os.environ.get("NECRO_TEST047_FIXTURE_ROOT", "/workspace/analysis-evidence"))
        manifest = json.loads((ROOT / "tests/test047-fixtures.json").read_text())
        self.assertEqual(("ngg2-test047-fixtures-v1", 5), (manifest["schema"], manifest["count"]))
        self.assertEqual("3e1c2ec0205c118d55e83d3f69b5305bfd95af4ae22ce40e15886506e2379162",
                         manifest["source_zip_sha256"])
        self.assertEqual(5, len(manifest["images"]))
        self.assertEqual(5, len({entry["path"] for entry in manifest["images"]}))
        states = []
        for entry in manifest["images"]:
            path = root / entry["path"]
            with self.subTest(path=entry["path"]):
                self.assertIs(type(entry["state"]), int)
                self.assertIn(entry["state"], (0, 1))
                self.assertTrue(path.is_file(), f"missing required TEST047 fixture: {path}")
                self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(),
                                 f"TEST047 fixture hash mismatch: {path}")
                with Image.open(path) as source:
                    image = source.convert("RGB")
                self.assertEqual((896, 414), image.size)
                self.assertEqual(entry["state"], self.assert_reference(image).state)
                states.append(entry["state"])
        self.assertEqual((2, 3), (states.count(0), states.count(1)))

    def test_required_test048_strict_optimization_parity(self):
        """87 mandatory known images: unchanged O0 and strict O2 agree byte-for-byte."""
        sets = (("test043-fixtures.json", "NECRO_TEST043_FIXTURE_ROOT", 66),
                ("test046-fixtures.json", "NECRO_TEST046_FIXTURE_ROOT", 8),
                ("test047-fixtures.json", "NECRO_TEST047_FIXTURE_ROOT", 5),
                ("test049-fixtures.json", "NECRO_TEST049_FIXTURE_ROOT", 8))
        self.assertEqual(23864, C.sizeof(NativeScene))
        with tempfile.TemporaryDirectory(prefix="ngg2-strict-profile-") as directory:
            directory = Path(directory)
            reference_path = directory / "unchanged-o0.so"
            # The reference retains the original O0 profile. Strict FP switches
            # belong only to the new optimized side, never the reference.
            subprocess.run(["cc", "-std=c99", "-O0", "-fPIC", "-shared",
                            str(CORE / "NG2Perception.c"), "-lm", "-o", str(reference_path)], check=True)
            reference = C.CDLL(str(reference_path))
            reference.ng2_analyze_rgba.argtypes = self.native.ng2_analyze_rgba.argtypes
            reference.ng2_analyze_rgba.restype = C.c_int
            test048 = {}
            count = 0
            for manifest_name, variable, expected_count in sets:
                manifest = json.loads((ROOT / "tests" / manifest_name).read_text())
                self.assertEqual(expected_count, manifest["count"])
                self.assertEqual(expected_count, len(manifest["images"]))
                self.assertEqual(expected_count, len({entry["path"] for entry in manifest["images"]}))
                if manifest_name == "test049-fixtures.json":
                    self.assertEqual("ngg2-test049-fixtures-v1", manifest["schema"])
                    self.assertEqual("17222871b89b8c81cfc171bafd433201eb1ba28df02ef3b5e006936f13704c07",
                                     manifest["source_zip_sha256"])
                fixture_root = Path(os.environ.get(variable, "/workspace/analysis-evidence"))
                for entry in manifest["images"]:
                    relative = Path(entry["path"])
                    self.assertFalse(relative.is_absolute())
                    self.assertNotIn("..", relative.parts)
                    path = fixture_root / relative
                    with self.subTest(manifest=manifest_name, path=entry["path"]):
                        self.assertTrue(path.is_file(), f"missing required strict-profile fixture: {path}")
                        self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(),
                                         f"strict-profile fixture hash mismatch: {path}")
                        with Image.open(path) as source:
                            image = source.convert("RGB")
                        self.assertEqual((896, 414), image.size)
                        rgba = image.convert("RGBA").tobytes()
                        old = NativeScene()
                        self.assertEqual(0, reference.ng2_analyze_rgba(rgba, len(rgba), 3584, C.byref(old)))
                        optimized = self.assert_reference(image)
                        self.assertEqual(bytes(old), bytes(optimized), "full Scene bytes changed under strict O2")
                        if "state" in entry:
                            self.assertEqual(entry["state"], optimized.state)
                        if manifest_name == "test049-fixtures.json":
                            test048[int(path.stem.split("-")[1])] = (optimized, image)
                        count += 1
            self.assertEqual(87, count)

            # Reuse the established navigation harness for the five actual
            # TEST048 pairs. Input scenes originate in the strict O2 detector.
            from test_native_navigation import NativeNavigationTests, Scene, Motion, MOTIONS
            from necroprobe import motion_stats
            NativeNavigationTests.setUpClass()
            try:
                lib = NativeNavigationTests.lib
                for before_id, after_id, kind in ((5, 12, "blocked"), (5, 16, "moved"),
                                                  (12, 16, "moved"), (12, 17, "moved"),
                                                  (16, 17, "blocked")):
                    before, before_image = test048[before_id]
                    after, after_image = test048[after_id]
                    a, b = Scene.from_buffer_copy(bytes(before)), Scene.from_buffer_copy(bytes(after))
                    result = Motion()
                    self.assertEqual(1, lib.ng2_motion(C.byref(a), C.byref(b), 1, C.byref(result)))
                    self.assertEqual(MOTIONS[kind], result.kind)
                    self.assertEqual((-1, 0) if kind == "moved" else (0, 0), (result.dx, result.dy))
                    with patch.object(native_scan, "_native", None), patch.object(navigation_stats, "_native", None), \
                            patch.object(motion_stats, "_native", None):
                        pillow_before = shop_navigation.scan(before_image)
                        pillow_after = shop_navigation.scan(after_image)
                        self.assertEqual(kind, shop_navigation.motion(pillow_before, pillow_after, "left"))
                        old_view = shop_navigation._motion_view(pillow_before.signature)[0]
                        new_view = shop_navigation._motion_view(pillow_after.signature)[0]
                        expected_scores = shop_navigation._pillow_motion_scores(old_view, new_view)
                    values = (C.c_double * 73)()
                    lib.ng2_test_scores(bytes(before.signature), bytes(after.signature), values)
                    for actual, (expected, _, _) in zip(values, expected_scores):
                        self.assertAlmostEqual(expected, actual, places=12)
            finally:
                NativeNavigationTests.tearDownClass()

    def test_floor_quantization_integer_band_boundaries(self):
        """SHOP-02: preserve observed dark floor without admitting warm walls.

        Fixed RGB8 medians represent the reviewed TEST056 floor colours and
        exact integer boundaries, rather than a second copy of the classifier.
        The white challenge overlay is not required for the positive evidence.
        """
        cases = (
            ("observed_floor_44_27_24", (44, 27, 24), 1),
            ("new_lower_equal", (41, 25, 21), 1),
            ("new_lower_inside_by_five", (50, 30, 26), 1),
            ("new_lower_outside_by_five", (52, 31, 27), 4),
            ("new_lower_outside_blue_unit", (41, 25, 20), 4),
            ("unchanged_dark_red38", (38, 23, 17), 1),
            ("bright_red39", (39, 24, 20), 1),
            ("bright_red52", (52, 31, 28), 1),
            ("excluded_red53", (53, 33, 29), 4),
            ("green_lower_equal", (40, 18, 21), 1),
            ("green_lower_outside", (40, 17, 21), 4),
            ("green_upper_equal", (50, 34, 29), 1),
            ("green_upper_outside", (50, 35, 29), 3),
            ("blue_upper_equal", (40, 26, 28), 1),
            ("blue_upper_outside", (40, 26, 29), 0),
            ("green_blue_difference_equal", (50, 32, 26), 1),
            ("green_blue_difference_outside", (50, 33, 26), 4),
            ("warm_dirt_stays_blocked", (50, 25, 25), 4),
            ("brown_dirt_stays_blocked", (50, 32, 15), 4),
            ("stone_stays_blocked", (50, 36, 30), 3),
            ("unbracketed_wood_stays_unknown", (63, 19, 0), 0),
            ("unknown_stays_unknown", (5, 3, 3), 0),
        )
        for name, color, expected in cases:
            with self.subTest(boundary=name, rgb=color):
                image = synthetic_floor()
                values = [tuple(max(0, min(255, channel +
                          (0 if i == 624 else -3 if i % 2 else 3)))
                          for channel in color) for i in range(625)]
                cell = Image.new("RGB", (25, 25)); cell.putdata(values)
                image.paste(cell, (400, 195))  # relative(-1,0), outside HUD
                result = self.assert_reference(image)
                self.assertEqual(expected, result.tiles[5*23+10], name)
                self.assertEqual(0, sum(result.protected_cells))
        image = synthetic_floor()
        image.paste((41, 25, 21), (400, 195, 425, 220))
        self.assertNotEqual(1, self.assert_reference(image).tiles[5*23+10],
                            "flat colour must not become floor")
        image = synthetic_floor()
        image.paste((41, 25, 21), (112, 87, 137, 112))
        self.assertEqual(0, self.assert_reference(image).tiles[2*23+2],
                         "HUD overlap must remain unknown")
        image = synthetic_floor()
        cell = Image.new("RGB", (25, 25))
        cell.putdata([(199, 164, 63) if i < 280 else
                      tuple(c + (-3 if i % 2 else 3) for c in (41, 25, 21))
                      for i in range(625)])
        image.paste(cell, (400, 195))
        self.assertEqual(2, self.assert_reference(image).tiles[5*23+10],
                         "280 gold pixels must precede dark-floor evidence")

    def test_required_test056_original_floor_labels_and_strict_parity(self):
        """18 known originals; AI visual floor labels, not a successful new run."""
        manifest = json.loads((ROOT / "tests/test057-fixtures.json").read_text())
        self.assertEqual(("ngg2-test057-fixtures-v1", 18, 39),
                         (manifest["schema"], manifest["count"], manifest["visual_floor_label_count"]))
        self.assertEqual("c0d1735b978ee61e124d6721326fdcb5a6bae8a67fe87145efc23a3fb27c815c",
                         manifest["source_zip_sha256"])
        self.assertEqual([{"run_id": "414c5fcf2f444e56bd079559f2fcf51c",
                           "sha256": "ff829d73b15a98d17615e663b8a6d41c8e953747af0b4739da89bcd6f67d6b19"}],
                         manifest["source_reports"])
        fixtures = list(required_profile_fixtures())
        self.assertEqual(203, len(fixtures))
        self.assertEqual(203, len({str(path) for _, _, path in fixtures}))
        with tempfile.TemporaryDirectory(prefix="ngg2-test057-profile-") as directory:
            library_path = Path(directory) / "reference-o0.so"
            subprocess.run(["cc", "-std=c99", "-O0", "-fPIC", "-shared",
                            str(CORE / "NG2Perception.c"), "-lm", "-o", str(library_path)], check=True)
            reference = C.CDLL(str(library_path))
            reference.ng2_analyze_rgba.argtypes = self.native.ng2_analyze_rgba.argtypes
            reference.ng2_analyze_rgba.restype = C.c_int
            images, label_count = {}, 0
            for filename, entry, path in fixtures:
                with self.subTest(manifest=filename, image=path.name):
                    with Image.open(path) as source:
                        self.assertEqual((896, 414), source.size)
                        image = source.convert("RGB")
                    raw = image.convert("RGBA").tobytes()
                    old = NativeScene()
                    self.assertEqual(0, reference.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(old)))
                    current = self.assert_reference(image)
                    self.assertEqual(bytes(old), bytes(current), "all Scene bytes O0/strictO2")
                    if filename != "test057-fixtures.json":
                        continue
                    self.assertEqual(entry["bytes"], path.stat().st_size)
                    self.assertEqual((entry["state"], entry["goods"]), (current.state, current.goods))
                    for x, y in entry["reviewed_floor_cells"]:
                        self.assertEqual(1, current.tiles[(y+5)*23+x+11],
                                         f"native-size reviewed floor {entry['capture_id']}:{x},{y}")
                        label_count += 1
                    self.assertEqual(entry["reviewed_gold_cells"],
                                     [[i%23-11, i//23-5] for i,k in enumerate(current.tiles) if k == 2])
                    self.assertEqual(0, sum(current.protected_cells))
                    self.assertNotIn(5, current.tiles, "no observed door bracket in received056")
                    images[entry["capture_id"]] = current
            self.assertEqual(39, label_count)
            self.assertEqual(18, len(images))
            self.assertEqual(bytes(images[103].tiles), bytes(images[104].tiles))
            self.assertEqual(bytes(images[104].tiles), bytes(images[105].tiles))
            # Calibration removes the latest comparison churn. The remaining
            # off-route difference is recorded, never relabelled as full replay.
            self.assertEqual([(0, 2, 4, 1)],
                             [(i%23-11, i//23-5, a, b) for i, (a,b) in
                              enumerate(zip(images[91].tiles, images[93].tiles)) if a != b])

    def test_required_test057_original_partial_checkpoint_and_strict_parity(self):
        """Seven known originals; incomplete export and AI labels remain explicit."""
        manifest = json.loads((ROOT / "tests/test058-fixtures.json").read_text())
        self.assertEqual(("ngg2-test058-fixtures-v1", 7, [896, 414]),
                         (manifest["schema"], manifest["count"], manifest["dimensions"]))
        self.assertEqual("f49e35e4ae1a3491c1af7e0fe4e0e0acbbc990b60ff0e3cc262cd904f3f197c1",
                         manifest["source_zip_sha256"])
        self.assertEqual([{"run_id": "68c64427d18544738b986d7331b3dcfa",
                           "sha256": "300fbffdde636669f72470b623f140146dad2bbd097449531a6fe5bcb81c0966"}],
                         manifest["source_reports"])
        ids = [1, 37, 38, 44, 45, 46, 53]
        self.assertEqual({"resolved": False,
                          "reported_exported_capture_ids": [1, 2, 6, 37, 38, 44, 45, 46, 51, 52, 53],
                          "complete_png_capture_ids": ids, "not_available_as_complete_png": [2, 6, 51, 52]},
                         manifest["collection_scope"])
        self.assertEqual({"source_width": 828, "source_height": 1792, "orientation": 8,
                          "decoded_width": 896, "decoded_height": 414}, manifest["source_capture_geometry"])
        self.assertEqual({"1": "pause_in_transient_inset", "37": "floor", "38": "floor",
                          "44": "floor", "45": "floor", "46": "floor", "53": "pause"},
                         manifest["ai_visual_state_by_capture"])
        self.assertEqual(dict.fromkeys(map(str, ids), "unobserved"), manifest["ai_visual_goods_by_capture"])
        states = {1: 0, 37: 2, 38: 2, 44: 2, 45: 2, 46: 2, 53: 1}
        prefixes = {1: 0, 37: 1, 38: 1, 44: 3, 45: 3, 46: 3, 53: 6}
        with tempfile.TemporaryDirectory(prefix="ngg2-test058-perception-") as directory:
            library_path = Path(directory) / "reference-o0.so"
            subprocess.run(["cc", "-std=c99", "-O0", "-fPIC", "-shared",
                            str(CORE / "NG2Perception.c"), "-lm", "-o", str(library_path)], check=True)
            reference = C.CDLL(str(library_path))
            reference.ng2_analyze_rgba.argtypes = self.native.ng2_analyze_rgba.argtypes
            reference.ng2_analyze_rgba.restype = C.c_int
            scenes = {}
            for filename, entry, path in required_profile_fixtures():
                if filename != "test058-fixtures.json":
                    continue
                with self.subTest(capture=entry["capture_id"]):
                    cid = entry["capture_id"]
                    self.assertEqual((entry["bytes"], entry["sha256"]),
                                     (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
                    with Image.open(path) as source:
                        self.assertEqual((896, 414), source.size)
                        image = source.convert("RGB")
                    raw = image.convert("RGBA").tobytes()
                    baseline = NativeScene()
                    self.assertEqual(0, reference.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(baseline)))
                    current = self.assert_reference(image)
                    self.assertEqual(bytes(baseline), bytes(current), "all Scene bytes O0/strictO2")
                    self.assertEqual((states[cid], 0), (entry["state"], entry["goods"]))
                    self.assertEqual((entry["state"], entry["goods"]), (current.state, current.goods))
                    self.assertTrue(entry["stable"])
                    self.assertEqual(prefixes[cid], entry["completed_prefix"])
                    self.assertEqual(manifest["reviewed_gold_cells_by_capture"][str(cid)],
                                     [[i%23-11, i//23-5] for i, k in enumerate(current.tiles) if k == 2])
                    self.assertEqual(0, sum(current.protected_cells))
                    self.assertNotIn(5, current.tiles, "top door remains hidden by the pause HUD")
                    scenes[cid] = current
            self.assertEqual(set(ids), set(scenes))
            # Initial visual pause is not a recognized PAUSE; terminal53 is.
            self.assertEqual((0, 1), (scenes[1].state, scenes[53].state))
            for cid in (44, 45, 46):
                self.assertEqual(0, scenes[cid].tiles[11], "door cell(0,-5) overlaps HUD")
                for y in range(-4, 0):
                    self.assertEqual(1, scenes[cid].tiles[(y+5)*23+11], "observed upper corridor")

    def test_required_test058_original_complete_capture_and_strict_parity(self):
        """Twelve known originals; complete export is not goods acceptance."""
        manifest = json.loads((ROOT / "tests/test059-fixtures.json").read_text())
        self.assertEqual(("ngg2-test059-fixtures-v1", 12, [896, 414]),
                         (manifest["schema"], manifest["count"], manifest["dimensions"]))
        self.assertEqual("5a10c1c76237e15133843d13231206157b43f1e66cc42873b2de9cbf8c70c369",
                         manifest["source_zip_sha256"])
        self.assertEqual([{"run_id": "ff55bc0398a64132a4efde046fd8dffe",
                           "sha256": "d7e09206f382e6c80794859c63f7c06f36b0ed32aecd41bb1214b393e9041533"}],
                         manifest["source_reports"])
        ids = [1, 2, 7, 39, 40, 46, 47, 53, 54, 59, 60, 61]
        self.assertEqual({"resolved": True, "reported_exported_capture_ids": ids,
                          "complete_png_capture_ids": ids, "not_available_as_complete_png": [],
                          "unstable_prefix_capture_ids": [59, 60]}, manifest["collection_scope"])
        self.assertEqual({"source_width": 828, "source_height": 1792, "orientation": 8,
                          "decoded_width": 896, "decoded_height": 414}, manifest["source_capture_geometry"])
        floor_ids = [7, 39, 40, 46, 47, 53, 54]
        self.assertEqual(floor_ids, manifest["floor_capture_ids"])
        self.assertEqual({str(cid): ("pause_in_transient_inset" if cid == 1 else
                                    "floor" if cid in floor_ids else "pause") for cid in ids},
                         manifest["ai_visual_state_by_capture"])
        self.assertEqual(dict.fromkeys(map(str, ids), "unobserved"), manifest["ai_visual_goods_by_capture"])
        states = {1: 0, 2: 1, 7: 2, 39: 2, 40: 2, 46: 2, 47: 2, 53: 2, 54: 2, 59: 1, 60: 1, 61: 1}
        prefixes = {1: 0, 2: 0, 7: 1, 39: 1, 40: 1, 46: 3, 47: 3, 53: 4, 54: 4, 59: 4, 60: 5, 61: 5}
        gold = {str(cid): ([[-5, 2]] if cid in (7, 39, 40) else [[-4, 2]] if cid in (46, 47)
                          else [[-3, 2]] if cid in (53, 54) else []) for cid in ids}
        self.assertEqual(gold, manifest["reviewed_gold_cells_by_capture"])
        with tempfile.TemporaryDirectory(prefix="ngg2-test059-perception-") as directory:
            library_path = Path(directory) / "reference-o0.so"
            subprocess.run(["cc", "-std=c99", "-O0", "-fPIC", "-shared",
                            str(CORE / "NG2Perception.c"), "-lm", "-o", str(library_path)], check=True)
            reference = C.CDLL(str(library_path))
            reference.ng2_analyze_rgba.argtypes = self.native.ng2_analyze_rgba.argtypes
            reference.ng2_analyze_rgba.restype = C.c_int
            scenes, original_hashes = {}, {}
            for filename, entry, path in required_profile_fixtures():
                if filename != "test059-fixtures.json":
                    continue
                with self.subTest(capture=entry["capture_id"]):
                    cid = entry["capture_id"]
                    self.assertEqual((entry["bytes"], entry["sha256"]),
                                     (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
                    with Image.open(path) as source:
                        self.assertEqual((896, 414), source.size)
                        image = source.convert("RGB")
                    raw = image.convert("RGBA").tobytes()
                    unchanged = NativeScene()
                    self.assertEqual(0, reference.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(unchanged)))
                    analyzed = self.assert_reference(image)
                    self.assertEqual(bytes(unchanged), bytes(analyzed), "entire Scene bytes O0/strictO2")
                    self.assertEqual((states[cid], 0), (entry["state"], entry["goods"]))
                    self.assertEqual((entry["state"], entry["goods"]), (analyzed.state, analyzed.goods))
                    self.assertEqual(cid not in (59, 60), entry["stable"])
                    self.assertEqual(prefixes[cid], entry["completed_prefix"])
                    self.assertEqual(gold[str(cid)],
                                     [[i % 23-11, i // 23-5] for i, kind in enumerate(analyzed.tiles) if kind == 2])
                    self.assertEqual(0, sum(analyzed.protected_cells))
                    self.assertNotIn(5, analyzed.tiles, "no observed gold bracket in received058")
                    if analyzed.state != 2:
                        self.assertEqual(bytes(230), bytes(analyzed.protected_cells))
                        self.assertEqual(bytes(23296), bytes(analyzed.signature))
                        self.assertEqual((0, 0, 0), (analyzed.beat_remaining, analyzed.beat_spacing, analyzed.beat_center))
                    scenes[cid] = analyzed; original_hashes[cid] = entry["sha256"]
            self.assertEqual(set(ids), set(scenes))
            self.assertEqual((0, 1, 1), (scenes[1].state, scenes[2].state, scenes[61].state))
            self.assertEqual(1, len({original_hashes[cid] for cid in (59, 60, 61)}))
            # The wall is not relabelled FLOOR to make a third LEFT safe.
            # The next DOWN cell is independently observed FLOOR in both frames.
            for cid in (53, 54):
                self.assertEqual(4, scenes[cid].tiles[5 * 23+10])
                self.assertEqual(1, scenes[cid].tiles[6 * 23+11])

    def test_required_test059_original_partial_capture_and_strict_parity(self):
        """14 known originals; an unfinalized export stays incomplete."""
        manifest = json.loads((ROOT / "tests/test060-fixtures.json").read_text())
        self.assertEqual(("ngg2-test060-fixtures-v1", 14, [896, 414]),
                         (manifest["schema"], manifest["count"], manifest["dimensions"]))
        self.assertEqual("900b06ffcaecb973a3c97a9b794702ac031cdc5f40437558ee19844e434dce0b",
                         manifest["source_zip_sha256"])
        self.assertEqual([{"run_id": "d411b59e938c40719be2c40ab4c77939",
                           "sha256": "9079fe8f191308fb2cfccb3fffa7dbbb8fe9903c91bad92663cc60fa9504eecd"},
                          {"run_id": "897534256fce4a81942f3f8b46a6a9f3",
                           "sha256": "a25060827d62c612e038a147801d9afefcf27fe11a38d5c5ebc0476582ff7b16"}],
                         manifest["source_reports"])
        ids = [1, 2, 6, 30, 32, 38, 39, 40, 46, 47, 48, 54, 55, 61]
        floor_ids = [6, 30, 32, 38, 39, 40, 46, 47, 48, 54, 55]
        scope = manifest["collection_scope"]
        self.assertFalse(scope["resolved"])
        self.assertEqual("host_deadline", scope["stop_reason"])
        self.assertEqual((2, 16, 14, 46), tuple(scope[key] for key in
            ("native_run_count", "export_manifest_count", "completed_local_metadata_count", "journal_capture_row_count")))
        self.assertEqual(ids, scope["complete_png_capture_ids"])
        self.assertEqual([1, 2, 6, 30, 32, 38, 39, 40, 46, 47, 48, 54, 55, 59, 60, 61],
                         scope["reported_exported_capture_ids"])
        self.assertEqual([59, 60], scope["not_available_as_complete_png"])
        self.assertEqual([59, 60], scope["unfinalized_export_capture_ids"])
        self.assertEqual([60], scope["part_only_capture_ids"])
        self.assertEqual(ids, scope["referenced_capture_ids"])
        self.assertEqual([], scope["reported_missing_reference_capture_ids"])
        self.assertEqual([], scope["missing_referenced_complete_png_ids"])
        self.assertEqual([4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                          21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 37, 45, 52, 53, 59, 60],
                         scope["unavailable_original_capture_ids_for_full_replay"])
        self.assertEqual({"source_width": 828, "source_height": 1792, "orientation": 8,
                          "decoded_width": 896, "decoded_height": 414}, manifest["source_capture_geometry"])
        self.assertEqual(floor_ids, manifest["floor_capture_ids"])
        self.assertEqual({str(cid): ("pause_in_transient_inset" if cid == 1 else
                                    "floor" if cid in floor_ids else "pause") for cid in ids},
                         manifest["ai_visual_state_by_capture"])
        self.assertEqual(dict.fromkeys(map(str, ids), "unobserved"), manifest["ai_visual_goods_by_capture"])
        prefixes = {1: 0, 2: 0, 6: 1, 30: 1, 32: 1, 38: 3, 39: 3, 40: 3,
                    46: 4, 47: 4, 48: 4, 54: 6, 55: 6, 61: 8}
        gold = {str(cid): ([[-1, -5], [1, -5]] if cid in (6, 30, 32) else
                          [[-1, -4], [1, -4]] if cid in (38, 39, 40) else
                          [[-1, -3], [1, -3]] if cid in (46, 47, 48) else
                          [[-1, -2], [1, -2]] if cid in (54, 55) else []) for cid in ids}
        self.assertEqual(gold, manifest["reviewed_gold_cells_by_capture"])
        with tempfile.TemporaryDirectory(prefix="ngg2-test060-perception-") as directory:
            library_path = Path(directory) / "reference-o0.so"
            subprocess.run(["cc", "-std=c99", "-O0", "-fPIC", "-shared",
                            str(CORE / "NG2Perception.c"), "-lm", "-o", str(library_path)], check=True)
            reference = C.CDLL(str(library_path))
            reference.ng2_analyze_rgba.argtypes = self.native.ng2_analyze_rgba.argtypes
            reference.ng2_analyze_rgba.restype = C.c_int
            scenes = {}
            for filename, entry, path in required_profile_fixtures():
                if filename != "test060-fixtures.json":
                    continue
                with self.subTest(capture=entry["capture_id"]):
                    cid = entry["capture_id"]
                    self.assertEqual((entry["bytes"], entry["sha256"]),
                                     (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()))
                    with Image.open(path) as source:
                        self.assertEqual((896, 414), source.size)
                        image = source.convert("RGB")
                    raw = image.convert("RGBA").tobytes()
                    unchanged = NativeScene()
                    self.assertEqual(0, reference.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(unchanged)))
                    analyzed = self.assert_reference(image)
                    self.assertEqual(bytes(unchanged), bytes(analyzed), "entire Scene bytes O0/strictO2")
                    self.assertEqual((2 if cid in floor_ids else 0 if cid == 1 else 1, 0),
                                     (entry["state"], entry["goods"]))
                    self.assertEqual((entry["state"], entry["goods"]), (analyzed.state, analyzed.goods))
                    self.assertTrue(entry["stable"])
                    self.assertEqual(prefixes[cid], entry["completed_prefix"])
                    self.assertEqual(gold[str(cid)],
                                     [[i % 23-11, i // 23-5] for i, kind in enumerate(analyzed.tiles) if kind == 2])
                    self.assertEqual(0, sum(analyzed.protected_cells))
                    if analyzed.state != 2:
                        self.assertEqual(bytes(230), bytes(analyzed.protected_cells))
                        self.assertEqual(bytes(23296), bytes(analyzed.signature))
                        self.assertEqual((0, 0, 0), (analyzed.beat_remaining, analyzed.beat_spacing, analyzed.beat_center))
                    scenes[cid] = analyzed
            self.assertEqual(set(ids), set(scenes))
            self.assertEqual((0, 1, 1), (scenes[1].state, scenes[2].state, scenes[61].state))
            for cid in (54, 55):
                self.assertEqual(1, scenes[cid].tiles[4 * 23+11], "latest adjacent upper FLOOR")
                self.assertEqual(5, scenes[cid].tiles[3 * 23+11], "closed door remains two cells above")
            changed = [[i % 23-11, i // 23-5, a, b] for i, (a, b) in
                       enumerate(zip(scenes[54].tiles, scenes[55].tiles)) if a != b]
            self.assertEqual([[8, 2, 1, 4], [10, 2, 1, 4]], changed)
            self.assertEqual(changed, manifest["latest_scene_change"]["changed_tiles"])

    def test_fixture_check_fails_on_missing(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, NECRO_TEST043_FIXTURE_ROOT=directory):
            with self.assertRaisesRegex(AssertionError, "missing required TEST043 fixture"):
                list(required_fixtures())

    def test_padding_ignored(self):
        path = next(p for p in required_fixtures() if "test042" in str(p) and p.name == "run-101.jpg")
        with Image.open(path) as source:
            image = source.convert("RGB")
        first = self.analyze(image)
        for padding in (1, 7, 4096):
            with self.subTest(padding=padding):
                self.assertEqual(bytes(first), bytes(self.analyze(image, padding)))

    def test_invalid_input_clears_output(self):
        raw = Image.new("RGBA", (896,414), (0,0,0,255)).tobytes()
        variants = [(None,len(raw),3584), (raw,len(raw)-1,3584), (raw,len(raw)+1,3584),
                    (raw,len(raw),0), (raw,len(raw),3583), (raw,len(raw),7681),
                    (raw,len(raw),2**63), (raw[:3]+b"\xfe"+raw[4:],len(raw),3584),
                    (raw[:-1]+b"\x00",len(raw),3584)]
        for data,length,stride in variants:
            with self.subTest(length=length, stride=stride):
                out = NativeScene()
                C.memset(C.byref(out), 0xaa, C.sizeof(out))
                self.assertEqual(self.native.ng2_analyze_rgba(data,length,stride,C.byref(out)), -1)
                self.assertEqual(out.abi_version, 1)
                self.assertEqual(out.struct_size, C.sizeof(out))
                expected = NativeScene(abi_version=1, struct_size=C.sizeof(out))
                self.assertEqual(bytes(out), bytes(expected))
        self.assertEqual(self.native.ng2_analyze_rgba(raw,len(raw),3584,None), -1)

    def test_fingerprint_thresholds(self):
        a = bytes(48)
        for indices, delta in ((range(6),12), ((0,1,2,8,9,10),11),
                               ((0,1,2,8,9,10),12), ((0,1,2,8,9,10),13),
                               ((0,1,8,9,16,17),12)):
            b = bytes(delta if i in indices else 0 for i in range(48))
            self.assertEqual(bool(self.native.ng2_fingerprint_changed(a,b)),gold_scan.changed(list(a),list(b)))
        self.assertEqual(self.native.ng2_fingerprint_changed(None,a), 0)

    def test_synthetic_state_neutral_and_vertical_guards(self):
        base = synthetic_floor()
        self.assertEqual(self.assert_reference(base).state, 2)
        for name in ("continue", "restart", "death"):
            with self.subTest(template=name):
                image = base.copy()
                if name == "restart":
                    paint_template(image, "continue")
                paint_template(image, name)
                self.assertEqual(self.assert_reference(image).state, 0 if name == "death" else 1)
        for name in ("icon", "footer", "zone_one", "floor_one"):
            with self.subTest(missing=name):
                image = base.copy()
                box = gold_scan._TEMPLATES[name][0]
                image.paste(0,box)
                self.assertEqual(self.assert_reference(image).state, 0)
            with self.subTest(coloured=name):
                image = base.copy()
                image.paste(0,box)
                paint_template(image,name,(255,80,80))
                self.assertEqual(self.assert_reference(image).state, 0)
        for cutoff in (54,55,84,85):
            with self.subTest(icon_cutoff=cutoff):
                image = base.copy()
                image.paste(0,gold_scan._TEMPLATES["icon"][0])
                paint_template(image,"icon",(cutoff,)*3)
                self.assertEqual(self.assert_reference(image).state, 2 if cutoff>=55 else 0)
        image = base.copy()
        # Short neutral lettering makes raw IoU fail; the 13px opening retains
        # the two observed vertical bars without filling a missing pixel.
        for y in range(6,42,8):
            image.paste((180,180,180),(429,y,441,min(y+3,42)))
        self.assert_reference(image)
        for image in (Image.new("RGB",(896,414)),Image.new("RGB",(896,414),(255,255,255))):
            self.assertEqual(self.assert_reference(image).state,0)

    def test_synthetic_tile_integer_thresholds(self):
        values = [-2]*310 + [2]*310 + [-3,3,-1,1,0]
        colors = ((38,22,24),(39,22,24),(52,30,34),(53,30,34),(41,29,22),
                  (63,19,0),(35,8,0),(140,40,20),(141,40,20),(6,3,3),(5,3,3))
        for color in colors:
            with self.subTest(color=color):
                image = synthetic_floor()
                for n,delta in enumerate(values):
                    image.putpixel((256+n%25,123+n//25),tuple(max(0,min(255,c+delta)) for c in color))
                self.assert_reference(image)
        for count in (279,280,281):
            with self.subTest(gold_pixels=count):
                image=synthetic_floor()
                image.paste((20,12,12),(256,123,281,148))
                for n in range(count):
                    image.putpixel((256+n%25,123+n//25),(199,164,63))
                scene=self.assert_reference(image)
                self.assertEqual(scene.tiles[3*23+6]==2,count>=280)

    def test_grayscale_and_fingerprint_ties_even(self):
        for lower in (10,11):
            image=synthetic_floor()
            image.paste((lower,)*3,(224,70,280,118))
            image.paste((lower+1,)*3,(224,70,252,118))
            scene=self.assert_reference(image)
            self.assertEqual(scene.fingerprint[0],round(lower+.5))
        image=synthetic_floor()
        for y in range(70,118):
            for x in range(224,280):
                image.putpixel((x,y),((x*17)%256,(y*19)%256,((x+y)*23)%256))
        self.assert_reference(image)

    def test_gold_peak_thresholds_edges_and_colour_inequalities(self):
        for width,height,peak in ((19,15,99),(15,19,100),(16,24,134),(24,16,135)):
            with self.subTest(peak=peak):
                image=synthetic_floor()
                image.paste((210,170,30),(300,100,300+width,100+height))
                scene=self.assert_reference(image)
                self.assertEqual(scene.gold_peak,peak)
                self.assertEqual(scene.gold_state,1 if peak<100 else 2 if peak>=135 else 0)
        for box in ((300,0,335,5),(100,0,145,50),(650,0,700,50),(390,310,440,350),
                    (700,300,750,350),(300,365,335,400)):
            with self.subTest(box=box):
                image=synthetic_floor()
                image.paste((210,170,30),box)
                self.assert_reference(image)
        for color in ((52,42,15),(53,42,15),(200,137,30),(200,138,30),
                      (200,183,30),(200,184,30),(200,160,11),(200,160,12),
                      (200,160,92),(200,160,93)):
            with self.subTest(color=color):
                image=synthetic_floor()
                image.paste(color,(300,100,340,140))
                self.assert_reference(image)

    def test_synthetic_hud_thresholds_and_symmetry(self):
        for color,height in (((20,180,160),18),((20,180,160),17),((40,75,66),18),
                             ((40,76,66),18),((40,76,65),18),((0,255,255),37)):
            for width in (1,2,10,11):
                with self.subTest(color=color,height=height,width=width):
                    image=synthetic_floor()
                    for x in (42,146,250,354,538,642,746,850):
                        image.paste(color,(x,350,x+width,350+height))
                    out=self.assert_reference(image)
                    if color==(20,180,160) and height==18 and width==2:
                        self.assertEqual(out.beat_valid,1)
                        self.assertEqual(out.beat_spacing,104)
                        self.assertEqual(out.beat_center,446.5)
        image=synthetic_floor()
        for x in (42,146,250,354,538,642,758,862):
            image.paste((20,180,160),(x,350,x+2,368))
        self.assertEqual(self.assert_reference(image).beat_valid,0)

    def test_synthetic_goods_unknown_partial_and_exact_counts(self):
        image=synthetic_floor()
        self.assertEqual(self.assert_reference(image).goods,0)
        for color,expected in (((57,50,1),0),((58,51,1),1),((200,190,10),1)):
            with self.subTest(sign=color):
                image=synthetic_floor()
                image.paste(color,(190,90,211,111))
                self.assertEqual(self.assert_reference(image).goods,expected)
        for price_pixels in (17,18,19):
            for item_pixels in (23,24,25):
                for price_color in ((140,)*3,(141,)*3,(141,180,141),(141,181,141)):
                    with self.subTest(price_pixels=price_pixels,item_pixels=item_pixels,color=price_color):
                        image=synthetic_floor()
                        image.paste((200,190,10),(190,90,211,111))
                        # This21x21 sign gives the fixed first density peak196,96.
                        for x in (196,232,268):
                            image.paste((56,)*3,(x-12,136,x-12+item_pixels,137))
                            image.paste(price_color,(x-11,165,x-11+price_pixels,166))
                        scene=self.assert_reference(image)
                        expected=(price_pixels>=18 and item_pixels>=24 and min(price_color)>140
                                  and max(price_color)-min(price_color)<40)
                        self.assertEqual(scene.goods,2 if expected else 1)
                        self.assertTrue(any(scene.protected_cells))

    def test_sanitized_real_images_and_buffer_boundaries(self):
        harness = r'''
#include "NG2Core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    const size_t packed=896u*4u*414u, padded=7680u*414u;
    unsigned char *raw=(unsigned char*)malloc(padded);
    NG2Scene *out=(NG2Scene*)malloc(sizeof(*out));
    int count=0,y;
    if(!raw||!out)return 20;
    while(fread(raw,1,packed,stdin)==packed){
        if(ng2_analyze_rgba(raw,packed,3584,out))return 21;
        if(ng2_analyze_rgba(raw,packed-1,3584,out)!=-1||out->state)return 22;
        raw[packed-1]=0;
        if(ng2_analyze_rgba(raw,packed,3584,out)!=-1||out->state)return 23;
        raw[packed-1]=255;
        for(y=413;y>=0;--y){
            memmove(raw+(size_t)y*7680,raw+(size_t)y*3584,3584);
            memset(raw+(size_t)y*7680+3584,17,4096);
        }
        if(ng2_analyze_rgba(raw,padded,7680,out))return 24;
        ++count;
    }
    if(ng2_analyze_rgba(NULL,packed,3584,out)!=-1)return 25;
    if(ng2_analyze_rgba(raw,packed,3584,NULL)!=-1)return 26;
    free(out);free(raw);printf("%d\n",count);return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="ngg2-sanitized-") as directory:
            directory=Path(directory)
            source=directory/"harness.c"
            source.write_text(harness)
            executable=directory/"harness"
            subprocess.run(["cc","-std=c99","-O1","-g","-Wall","-Wextra","-Werror",
                            "-fsanitize=address,undefined","-fno-omit-frame-pointer","-no-pie",
                            "-I",str(CORE),str(source),str(CORE/"NG2Perception.c"),"-lm","-o",str(executable)],check=True)
            data=directory/"fixtures.rgba"
            count=0
            with data.open("wb") as stream:
                for path in required_fixtures():
                    with Image.open(path) as image:
                        stream.write(image.convert("RGBA").tobytes())
                    count+=1
            with data.open("rb") as stream:
                result=subprocess.run([str(executable)],stdin=stream,capture_output=True,text=True,
                                      # This managed host uses ptrace, unsupported by
                                      # LeakSanitizer. Address/UB checks remain active.
                                      env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0:halt_on_error=1",
                                           "UBSAN_OPTIONS":"halt_on_error=1:print_stacktrace=1"},check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),str(count))

if __name__ == "__main__":
    if sys.argv[1:] == ["--check-fixtures"]:
        print(f"TEST043 required known fixtures: {len(list(required_fixtures()))}")
    else:
        unittest.main()
