"""TEST082 public Perception with procedural pixels; no device replay or input."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_perception import NativeScene, synthetic_floor

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
UNKNOWN, FLOOR, GOLD, STONE, DIRT, DOOR, ITEM = range(7)


class Decision(C.Structure):
    _fields_ = [(key, C.c_int32) for key in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


def index(x, y):
    return (y+5)*23+x+11


def patch(image, pixels, cell=(-2, 0)):
    cx, cy = 448+36*cell[0], 207+36*cell[1]
    for y in range(25):
        for x in range(25):
            image.putpixel((cx-12+x, cy-12+y), pixels[y*25+x])
    return image


def texture(first, second):
    return [first if (x+y)%2 else second for y in range(25) for x in range(25)]


def bright(layout='diagonal', full=(47, 28, 24)):
    pixels = [full]*625
    if layout == 'horizontal':
        pixels[:300] = [(44, 26, 23)]*170 + [(47, 28, 24)]*130
        pixels[300:] = [(50, 29, 26)]*175 + [(47, 28, 24)]*150
        for at, value in ((0, (10, 5, 4)), (299, (100, 80, 60)),
                          (300, (100, 80, 60)), (624, (10, 5, 4))):
            pixels[at] = value
    else:
        for y in range(25):
            for x in range(25):
                if (x >= 12 and y < 12) or (x < 12 and y >= 12):
                    pixels[y*25+x] = (30, 20, 18) if (x+y)%2 else (34, 22, 20)
    return pixels


def partial(lower_nonblack=313, upper_black=300, low_r=False):
    pixels = [(0, 0, 0)]*300 + texture((36, 22, 20), (40, 24, 22))[:325]
    for at in range(300, 625-lower_nonblack):
        pixels[at] = (0, 0, 0)
    # Exactly312 pixels below this value give full median(7,3,3), a DIRT
    # label in the delivered classifier, while the observed lower half is floor.
    pixels[312] = (7, 3, 3)
    for at in range(upper_black, 300):
        pixels[at] = (7, 3, 3)
    if low_r:
        for at in range(313, 625):
            pixels[at] = (14, 8, 7) if at%2 else (10, 6, 5)
    return pixels


def stone(full=(51, 38, 27)):
    pixels = [full]*625
    for y in range(25):
        for x in range(25):
            if (x >= 12 and y < 12) or (x < 12 and y >= 12):
                pixels[y*25+x] = (53, 40, 32) if (x+y)%2 else (57, 44, 36)
    return pixels


class NativeMaterials082Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='materials082-')
        target = Path(cls.temp.name)/'public-materials.so'
        subprocess.run(['cc', '-std=c11', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-shared',
                        str(CORE/'NG2Perception.c'), str(CORE/'NG2Navigation.c'),
                        '-lm', '-o', str(target)], check=True)
        cls.lib = C.CDLL(str(target))
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
        cls.lib.ng2_passage_candidates.argtypes = [C.POINTER(NativeScene)]
        cls.lib.ng2_passage_candidates.restype = C.c_uint32
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(NativeScene), C.c_int32, C.c_int32,
                                             C.c_int32, C.c_int32, C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def analyze(self, pixels, cell=(-2, 0), image=None):
        if image is None:
            image = synthetic_floor()
        raw = patch(image, pixels, cell).convert('RGBA').tobytes()
        result = NativeScene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584, C.byref(result)))
        self.assertEqual((1, C.sizeof(NativeScene), 2), (result.abi_version, result.struct_size, result.state))
        return result

    def tile(self, pixels, cell=(-2, 0)):
        return self.analyze(pixels, cell).tiles[index(*cell)]

    def test_bright_disjoint_floor_survives_integer_boundary(self):
        for layout in ('diagonal', 'horizontal'):
            with self.subTest(layout=layout):
                self.assertEqual(FLOOR, self.tile(bright(layout)),
                                 'observed floor must survive a full-ROI integer boundary')
        # With RGB8 and R39..52 the attainable edges around the bound77 are
        # deficit75 (46,28,23) and deficit85 (48,29,24), not fractions of RGB.
        self.assertEqual(FLOOR, self.tile(bright(full=(46, 28, 23))))

    def test_partial_observed_mouth_becomes_candidate_without_unknown_entry(self):
        image = synthetic_floor()
        for y in range(-2, 3):
            for x in range(-2, 3):
                patch(image, texture((28, 18, 16), (34, 22, 20)), (x, y))
        for k in range(-3, 4):
            patch(image, texture((88, 52, 24), (96, 58, 28)), (k, -3))
            patch(image, texture((88, 52, 24), (96, 58, 28)), (-3, k))
        scene = self.analyze(partial(), (-2, -3), image)
        self.assertEqual(FLOOR, scene.tiles[index(-2, -3)], 'visible lower floor cannot become a dirt wall')
        self.assertEqual(UNKNOWN, scene.tiles[index(-2, -4)])
        self.assertEqual(1, self.lib.ng2_passage_candidates(C.byref(scene)))
        decision = Decision()
        self.assertEqual(5, self.lib.ng2_choose_passage(C.byref(scene), 0, 0, -2, -3, C.byref(decision)))
        self.assertEqual((1, 10, -2, -3, FLOOR), tuple(getattr(decision, name) for name, _ in decision._fields_))
        self.assertEqual(FLOOR, self.tile(partial(upper_black=285)), 'exact95% upper black is sufficient')

    def test_stone_disjoint_brick_texture_survives_integer_boundary(self):
        self.assertEqual(STONE, self.tile(stone()), 'observed stone brick cannot become dirt at one RGB integer')
        self.assertEqual(STONE, self.tile(stone((92, 70, 48))), 'deficit76 is inside the fixed integer bound')

    def test_bright_requires_disjoint_texture_and_bounded_colour(self):
        for full in ((48, 29, 24), (47, 28, 23), (47, 20, 24), (47, 34, 24), (53, 30, 25)):
            with self.subTest(full=full):
                self.assertEqual(DIRT, self.tile(bright(full=full)))
        # A common lower-right quarter can satisfy both overlapping halves;
        # it cannot provide two non-overlapping floor observations.
        common = [(47, 28, 24)]*625
        for y in range(12, 25):
            for x in range(12, 25):
                common[y*25+x] = (30, 20, 18) if (x+y)%2 else (34, 22, 20)
        self.assertEqual(DIRT, self.tile(common))
        for black in ('UR', 'LL'):
            pixels = bright()
            for y in range(25):
                for x in range(25):
                    if (black == 'UR' and x >= 12 and y < 12) or (black == 'LL' and x < 12 and y >= 12):
                        pixels[y*25+x] = (0, 0, 0)
            pixels[12 if black == 'UR' else 300] = (255, 255, 255)
            self.assertEqual(DIRT, self.tile(pixels), 'salt-black is not a floor witness')
        flat = bright()
        for y in range(25):
            for x in range(25):
                if (x >= 12 and y < 12) or (x < 12 and y >= 12):
                    flat[y*25+x] = (32, 20, 18)
        self.assertEqual(DIRT, self.tile(flat), 'flat colour cannot supply floor texture')

    def test_partial_requires_current_observed_floor_not_darkness_or_wall(self):
        for pixels in ([(0, 0, 0)]*625, [(4, 2, 1)]*624+[(255, 255, 255)]):
            self.assertEqual(UNKNOWN, self.tile(pixels))
        for lower in (texture((80, 48, 22), (96, 58, 26)), texture((52, 42, 34), (60, 48, 40)),
                      texture((80, 24, 8), (100, 30, 10))):
            pixels = partial(); pixels[300:] = lower[:325]
            for at in range(300, 312): pixels[at] = (0, 0, 0)
            pixels[312] = (7, 3, 3)
            self.assertNotEqual(FLOOR, self.tile(pixels), 'wall/wood pixels are not observed floor')
        self.assertNotEqual(FLOOR, self.tile(partial(low_r=True)))
        for count in (293, 292):
            pixels = [(0, 3, 3)]*142 + [(7, 0, 3)]*143 + [(7, 3, 3)]*15
            pixels += [(0, 3, 3) if at%2 else (7, 0, 3) for at in range(325-count)]
            pixels += texture((36, 22, 20), (40, 24, 22))[:count]
            self.assertEqual(FLOOR if count == 293 else DIRT, self.tile(pixels),
                             'lower half needs at least90% current nonblack observations')
        low_texture = [(0, 0, 0)]*300 + [(7, 3, 3)]*13 + [(16, 9, 8)]*312
        self.assertEqual(DIRT, self.tile(low_texture), 'a nearly flat lower patch is not floor texture')
        # More than5% nonblack in the upper half must not be treated as its
        # fixed black/floor boundary. The full median stays original DIRT.
        self.assertEqual(DIRT, self.tile(partial(upper_black=284)))

    def test_stone_requires_disjoint_witnesses_and_original_red_green_guards(self):
        for full in ((109, 80, 57), (51, 38, 26), (51, 35, 27), (40, 30, 21)):
            with self.subTest(full=full):
                self.assertNotEqual(STONE, self.tile(stone(full)))
        common = [(51, 38, 27)]*625
        for y in range(12):
            for x in range(12):
                common[y*25+x] = (53, 40, 32) if (x+y)%2 else (57, 44, 36)
        self.assertEqual(DIRT, self.tile(common))
        flat = stone()
        for y in range(25):
            for x in range(25):
                if (x >= 12 and y < 12) or (x < 12 and y >= 12): flat[y*25+x] = (55, 42, 34)
        self.assertEqual(DIRT, self.tile(flat))

    def test_old_materials_gold_gate_hud_and_invalid_alpha_remain_guarded(self):
        for pixels, expected in ((texture((28, 18, 16), (34, 22, 20)), FLOOR),
                                 (texture((88, 52, 24), (96, 58, 28)), DIRT),
                                 (texture((70, 58, 48), (90, 76, 64)), STONE),
                                 (texture((80, 24, 8), (100, 30, 10)), UNKNOWN),
                                 ([(210, 160, 20)]*625, GOLD)):
            self.assertEqual(expected, self.tile(pixels))
        image = synthetic_floor()
        for cell in ((-3, 0), (-1, 0)):
            patch(image, [(210, 160, 20)]*625, cell)
        scene = self.analyze(bright(), image=image)
        self.assertEqual(DOOR, scene.tiles[index(-2, 0)], 'existing gold gate conversion precedes extra material proofs')
        self.assertEqual(UNKNOWN, self.tile(bright(), (0, 4)), 'fixed heart HUD stays masked')
        raw = bytearray(patch(synthetic_floor(), bright()).convert('RGBA').tobytes()); raw[3] = 0
        out = NativeScene(); self.assertEqual(-1, self.lib.ng2_analyze_rgba(bytes(raw), len(raw), 3584, C.byref(out)))
        self.assertEqual(0, out.state)
