"""TEST090: observe a thin closed iron gate before treating it as open floor.

Procedural raw pixels exercise the same public analyzer and zero-motion
classifier as the app. They are derived calibration boundaries, not missing
game responses or evidence that the shop's merchandise was reached.
"""
import ctypes as C
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from PIL import ImageDraw
from tests import test_native_perception as fixture

CORE = fixture.CORE
GOLD = (160, 120, 32)
IRON = (165, 161, 135)


def index(x, y):
    return (y+5)*23+x+11


def gate_image(point=(-1, 0), *, mode='closed', colour=IRON, bracket='vertical'):
    image = fixture.synthetic_floor()
    draw = ImageDraw.Draw(image)
    # Independent fixed texture supports stationary motion. Its pixels do not
    # assert a future device frame and are not a classifier output oracle.
    rng = random.Random(9001)
    for y in range(70, 310, 4):
        for x in range(180, 710, 4):
            value = rng.randrange(50, 201)
            draw.rectangle((x, y, x+3, y+3), fill=(value,)*3)
    x, y = point; cx, cy = 448+36*x, 207+36*y
    for yy in range(cy-12, cy+13):
        for xx in range(cx-12, cx+13):
            if 0 <= xx < 896 and 0 <= yy < 414:
                value = 24+4*((xx+yy)&1)
                image.putpixel((xx, yy), (value, 3*value//5, 3*value//5))
    offsets = ((0, -1), (0, 1)) if bracket != 'horizontal' else ((-1, 0), (1, 0))
    for side, (dx, dy) in enumerate(offsets):
        if bracket == 'upper_only' and side == 1: continue
        if bracket == 'lower_only' and side == 0: continue
        ax, ay = cx+36*dx, cy+36*dy
        draw.rectangle((ax-12, ay-12, ax+12, ay+12), fill=GOLD)
    # The candidate stripe's unpainted rows are observed dark background,
    # not the unrelated neutral texture used for global motion support.
    draw.rectangle((cx-8, cy-23, cx-5, cy+1), fill=(24, 14, 14))
    if mode == 'open':
        draw.rectangle((cx-18, cy-22, cx-5, cy-12), fill=(110, 108, 92))
    elif mode != 'none':
        rows = range(3, 25)
        if mode == 'upper': rows = range(12)
        elif mode == 'lower': rows = range(12, 25)
        elif mode == 'horizontal': rows = range(10, 14)
        elif mode == 'split_bands': rows = ()
        columns = range(2) if mode == 'two_columns' else range(4)
        for column in columns:
            for row in rows:
                xx, yy = cx-8+column, cy-23+row
                if 0 <= xx < 896 and 0 <= yy < 414:
                    image.putpixel((xx, yy), colour)
        if mode == 'split_bands':
            # Three columns have enough total pixels and three have enough
            # upper pixels, but only two columns satisfy both together.
            for column, (upper, lower) in enumerate(((12, 13), (12, 13), (7, 13), (12, 7))):
                for row in list(range(upper))+list(range(12, 12+lower)):
                    image.putpixel((cx-8+column, cy-23+row), colour)
    return image


class Motion(C.Structure):
    _fields_ = [('kind', C.c_int32), ('dx', C.c_int32), ('dy', C.c_int32)]


class NativeThinGate090Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='thin-gate090-')
        output = Path(cls.directory.name)/'thin-gate.so'
        wrapper = Path(cls.directory.name)/'perception.c'
        wrapper.write_text('#include "'+str(CORE/'NG2Perception.c')+'"\n'
            'void ng2_test_thin_gate(const unsigned char *rgba, size_t stride, NG2Scene *scene) {\n'
            '    ng2_thin_gate_doors(rgba, stride, scene);\n}\n')
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                        str(wrapper), str(CORE/'NG2Navigation.c'),
                        '-lm', '-o', str(output)], check=True)
        cls.native = C.CDLL(str(output))
        cls.native.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t,
                                               C.POINTER(fixture.NativeScene)]
        cls.native.ng2_analyze_rgba.restype = C.c_int
        cls.native.ng2_motion.argtypes = [C.POINTER(fixture.NativeScene), C.POINTER(fixture.NativeScene),
                                          C.c_int32, C.POINTER(Motion)]
        cls.native.ng2_motion.restype = C.c_int
        cls.native.ng2_test_thin_gate.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(fixture.NativeScene)]

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    analyze = fixture.NativePerceptionTests.analyze

    def test_observed_thin_iron_and_open_panel_are_distinct_and_opening_has_no_step_credit(self):
        for point in ((-1, 0), (1, 0), (-4, -1)):
            with self.subTest(point=point):
                before = self.analyze(gate_image(point))
                after = self.analyze(gate_image(point, mode='open'))
                tile = index(*point)
                self.assertEqual((2, 2, 0), (before.state, before.gold_state, before.goods))
                self.assertEqual(5, before.tiles[tile],
                    'a visible vertical iron leaf between gold walls is a closed DOOR, not traversable FLOOR')
                self.assertEqual(1, after.tiles[tile], 'the rotated open panel leaves observed floor')
                if point == (-1, 0):
                    motion = Motion()
                    self.assertEqual(1, self.native.ng2_motion(C.byref(before), C.byref(after), 1, C.byref(motion)))
                    self.assertEqual((3, 0, 0), (motion.kind, motion.dx, motion.dy),
                                     'stationary opening must not add a player step')

    def test_short_broad_dim_coloured_or_unbracketed_marks_are_not_closed_gates(self):
        cases = [('open', dict(mode='open')), ('upper', dict(mode='upper')),
                 ('lower', dict(mode='lower')), ('horizontal', dict(mode='horizontal')),
                 ('split_columns', dict(mode='split_bands')),
                 ('two_columns', dict(mode='two_columns')), ('dim', dict(colour=(44, 44, 44))),
                 ('coloured', dict(colour=(165, 80, 40))),
                 ('chromatic_edge', dict(colour=(160, 150, 114))),
                 ('one_upper_gold', dict(bracket='upper_only')),
                 ('one_lower_gold', dict(bracket='lower_only')),
                 ('wrong_normal', dict(bracket='horizontal'))]
        for label, options in cases:
            with self.subTest(case=label):
                image = gate_image(**options)
                if label == 'split_columns':
                    self.assertEqual([25, 25, 20, 19],
                        [sum(image.getpixel((404+column, 184+row)) == IRON for row in range(25))
                         for column in range(4)], 'the fixture must not add omitted iron pixels')
                scene = self.analyze(image)
                self.assertEqual(2, scene.state)
                self.assertEqual(1, scene.tiles[index(-1, 0)],
                                 'isolated marks and a rotated panel are not closed iron-door evidence')
        for point in ((0, 0), (0, 4), (7, -4)):
            with self.subTest(guard=point):
                scene = self.analyze(gate_image(point))
                self.assertNotEqual(5, scene.tiles[index(*point)])

    def test_existing_state_goods_material_protection_and_entire_sampling_hud_guards_are_required(self):
        image = gate_image(); raw = image.convert('RGBA').tobytes()
        source = self.analyze(image)
        for fault in ('state', 'gold', 'partial', 'visible', 'dirt', 'stone', 'item',
                      'protected', 'protected_above', 'protected_below', 'missing_above', 'missing_below'):
            with self.subTest(fault=fault):
                scene = fixture.NativeScene.from_buffer_copy(bytes(source))
                scene.tiles[index(-1, 0)] = 1
                if fault == 'state': scene.state = 0
                elif fault == 'gold': scene.gold_state = 1
                elif fault in ('partial', 'visible'): scene.goods = 1 if fault == 'partial' else 2
                elif fault in ('dirt', 'stone', 'item'):
                    scene.tiles[index(-1, 0)] = {'dirt': 4, 'stone': 3, 'item': 6}[fault]
                elif fault.startswith('protected'):
                    y = -1 if fault.endswith('above') else 1 if fault.endswith('below') else 0
                    scene.protected_cells[index(-1, y)] = 1
                elif fault.startswith('missing'):
                    scene.tiles[index(-1, -1 if fault.endswith('above') else 1)] = 1
                before = bytes(scene)
                self.native.ng2_test_thin_gate(raw, 3584, C.byref(scene))
                self.assertEqual(before, bytes(scene), 'thin-door evidence cannot override a rejected context')
        # The stripe begins above the median sample. Reject its full ROI even
        # when the input scene hypothetically claims both bracket cells.
        image = gate_image((0, -4)); scene = fixture.NativeScene()
        scene.state = 2; scene.gold_state = 2
        scene.tiles[index(0, -4)] = 1
        scene.tiles[index(0, -5)] = scene.tiles[index(0, -3)] = 2
        before = bytes(scene)
        self.native.ng2_test_thin_gate(image.convert('RGBA').tobytes(), 3584, C.byref(scene))
        self.assertEqual(before, bytes(scene), 'a stripe intersecting the top pause-icon HUD is not gate evidence')


if __name__ == '__main__': unittest.main()
