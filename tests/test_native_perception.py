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
    """All 98 required images; missing private evidence is a local failure."""
    sets = (("test043-fixtures.json", "NECRO_TEST043_FIXTURE_ROOT", 66),
            ("test046-fixtures.json", "NECRO_TEST046_FIXTURE_ROOT", 8),
            ("test047-fixtures.json", "NECRO_TEST047_FIXTURE_ROOT", 5),
            ("test049-fixtures.json", "NECRO_TEST049_FIXTURE_ROOT", 8),
            ("test050-fixtures.json", "NECRO_TEST050_FIXTURE_ROOT", 11))
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
