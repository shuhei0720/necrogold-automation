"""TEST084: keep the full pause-icon proof when a bar has 9px fragments.

Procedural RGBA pixels exercise public C perception and Controller APIs. They
establish the observed glyph mechanism, not the missing first device285 frame.
"""
import ctypes as C
import unittest

from PIL import ImageDraw

from necroprobe import gold_scan
from tests import test_native_controller as controller
from tests import test_native_perception as perception
from tests import test_native_recovery as mechanics

CORE = controller.CORE


def nine_pixel_icon(color=(180, 180, 180), fragment=9):
    image = perception.synthetic_floor()
    image.paste(0, (429, 6, 465, 42))
    perception.paint_template(image, 'icon', color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((429, 8, 464, 10), fill=color)
    # Four left-bar columns retain two separate observed runs. Neither is
    # long enough for the old 11px opening when fragment is8 or9.
    draw.rectangle((435, 12+fragment, 438, 35-fragment), fill=(0, 0, 0))
    return image


def full_icon_stages(image):
    """Independent full-ROI set IoU for the fixture's old/new prerequisites."""
    crop = image.convert('RGB').crop((429, 6, 465, 42))
    reference = [bool(value) for value in gold_scan._TEMPLATES['icon'][3].getdata()]
    result = {}
    for cutoff in (55, 85):
        mask = [min(pixel) >= cutoff for pixel in crop.getdata()]
        for radius in (None, 6, 5, 4):
            observed = mask
            if radius is not None:
                eroded = [all(0 <= y+dy < 36 and mask[(y+dy)*36+x]
                              for dy in range(-radius, radius+1))
                          for y in range(36) for x in range(36)]
                observed = [any(0 <= y+dy < 36 and eroded[(y+dy)*36+x]
                                for dy in range(-radius, radius+1))
                            for y in range(36) for x in range(36)]
            intersection = sum(a and b for a, b in zip(reference, observed))
            union = sum(a or b for a, b in zip(reference, observed))
            result[(radius, cutoff)] = (intersection, union)
    return result


def visible_merchandise(image):
    image = image.copy()
    image.paste((200, 190, 10), (190, 90, 211, 111))
    # Three separated items and prices in the original clear display ROI.
    # The sign's fixed first21x21 density peak is196,96.
    for x in (196, 232, 268):
        image.paste((56,)*3, (x-12, 136, x+12, 137))
        image.paste((180,)*3, (x-11, 165, x+7, 166))
    return image


class NativeIcon084Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t,
                                            C.POINTER(controller.Scene)]
        cls.lib.ng2_analyze_rgba.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)

    setUp = controller.NativeControllerTests.setUp
    scene = controller.NativeControllerTests.scene
    observe = controller.NativeControllerTests.observe
    tick = controller.NativeControllerTests.tick
    status = controller.NativeControllerTests.status
    events = controller.NativeControllerTests.events
    motion_wait = controller.NativeControllerTests.motion_wait
    ack = controller.NativeControllerTests.ack
    fit = controller.NativeControllerTests.fit
    next_move = controller.NativeControllerTests.next_move
    publish_procedural_candidate = controller.NativeControllerTests.publish_procedural_candidate

    def analyze(self, image, padding=0):
        raw = image.convert('RGBA').tobytes()
        if padding:
            raw = b''.join(raw[y*3584:(y+1)*3584] + bytes([13])*padding
                           for y in range(414))
        scene = controller.Scene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(raw, len(raw), 3584+padding,
                                                   C.byref(scene)))
        self.assertEqual((1, C.sizeof(controller.Scene)),
                         (scene.abi_version, scene.struct_size))
        return scene

    def test_nine_pixel_bar_fragments_retain_full_reference_floor(self):
        image = nine_pixel_icon()
        stages = full_icon_stages(image)
        for cutoff in (55, 85):
            self.assertEqual((354, 486), stages[(None, cutoff)])
            for radius in (6, 5):
                self.assertEqual((280, 378), stages[(radius, cutoff)])
                intersection, union = stages[(radius, cutoff)]
                self.assertLess(5*intersection, 4*union,
                                'old full-reference opening must fail before the public Red')
            self.assertEqual((352, 378), stages[(4, cutoff)])
        self.assertEqual(0, self.analyze(nine_pixel_icon(fragment=8)).state,
                         '8px runs cannot supply the new9px opening')
        out = self.analyze(image)
        self.assertEqual(2, out.state,
                         'two observed bars with9px fragments retain full-reference FLOOR proof')
        self.assertEqual((0, 0), (out.goods, out.restart_label))

    def test_nine_pixel_path_keeps_intensity_neutrality_and_fixed_roi(self):
        for brightness in (54, 55, 84, 85, 180):
            with self.subTest(brightness=brightness):
                self.assertEqual(2 if brightness >= 55 else 0,
                                 self.analyze(nine_pixel_icon((brightness,)*3)).state)
        self.assertEqual(0, self.analyze(nine_pixel_icon((255, 80, 80))).state)
        for dx, dy in ((4, 0), (-4, 0), (0, 8), (0, -8)):
            with self.subTest(dx=dx, dy=dy):
                image = nine_pixel_icon()
                icon = image.crop((429, 6, 465, 42))
                image.paste(0, (429, 6, 465, 42))
                image.paste(icon, (429+dx, 6+dy))
                self.assertEqual(0, self.analyze(image).state)

    def test_nine_pixel_path_rejects_missing_bars_white_and_short_glyphs(self):
        for mode in ('absent', 'one_bar', 'white', 'glyph8', 'glyph9', 'glyph10',
                     'colored', 'padding_noise'):
            with self.subTest(mode=mode):
                image = nine_pixel_icon() if mode == 'padding_noise' else perception.synthetic_floor()
                if mode != 'padding_noise':
                    image.paste(0, (429, 6, 465, 42))
                draw = ImageDraw.Draw(image)
                if mode == 'one_bar':
                    draw.rectangle((435, 12, 442, 35), fill=(180,)*3)
                elif mode == 'white':
                    draw.rectangle((429, 6, 464, 41), fill=(255,)*3)
                elif mode.startswith('glyph'):
                    height = int(mode.removeprefix('glyph'))
                    for x in (435, 452):
                        draw.rectangle((x, 12, x+7, 11+height), fill=(180,)*3)
                        draw.rectangle((x, 36-height, x+7, 35), fill=(180,)*3)
                elif mode == 'colored':
                    perception.paint_template(image, 'icon', (255, 80, 80))
                elif mode == 'padding_noise':
                    draw.rectangle((429, 6, 431, 41), fill=(180,)*3)
                out = self.analyze(image)
                self.assertEqual((0, 0, 0), (out.state, out.goods, out.beat_valid))

    def test_nine_pixel_path_keeps_hud_menu_and_buffer_guards(self):
        for missing in ('footer', 'zone_one', 'floor_one'):
            with self.subTest(missing=missing):
                image = nine_pixel_icon()
                image.paste(0, gold_scan._TEMPLATES[missing][0])
                self.assertEqual(0, self.analyze(image).state)
        for label, expected in (('continue', 1), ('death', 0)):
            with self.subTest(label=label):
                image = nine_pixel_icon()
                perception.paint_template(image, label)
                self.assertEqual(expected, self.analyze(image).state)
        image = nine_pixel_icon()
        self.assertEqual(bytes(self.analyze(image)), bytes(self.analyze(image, padding=17)))
        raw = image.convert('RGBA').tobytes()
        for invalid, stride in ((raw[:-1], 3584), (raw[:-1]+b'\0', 3584), (raw, 3583)):
            with self.subTest(length=len(invalid), stride=stride):
                out = controller.Scene()
                self.assertEqual(-1, self.lib.ng2_analyze_rgba(invalid, len(invalid), stride,
                                                             C.byref(out)))
                self.assertEqual(0, out.state)

    def test_public_rgba_goods_after_move_ack_latches_and_confirms_pause(self):
        self.fit()
        move = self.next_move()
        original_ticket = bytes(move)
        self.ack(move)
        self.assertEqual((1, 0, 3, 0), (self.status().inputs, self.status().moves,
                                       self.status().input_state, self.status().goods))
        image = visible_merchandise(nine_pixel_icon())
        immutable_pixels = image.tobytes()
        goods = self.analyze(image)
        self.assertEqual((2, 2), (goods.state, goods.goods),
                         'actual RGBA must supply both FLOOR and the original VISIBLE goods proof')
        self.assertEqual(immutable_pixels, image.tobytes())
        self.now = max(self.now+2, move.target_ns+80_000_002)
        self.assertEqual(1, self.observe(goods, prefix=move.id))
        state = self.status()
        self.assertEqual((1, 0, 1, 1, 0, 0),
                         (state.inputs, state.moves, state.goods, state.reason,
                          state.paused, state.terminal))
        self.assertEqual(0, self.motion_wait().active)
        self.assertEqual(original_ticket, bytes(self.events()[0].command))
        ready, pause = self.tick()
        self.assertEqual((1, 2, self.number), (ready, pause.kind, pause.source_capture_id))
        self.assertEqual(1, len([event for event in self.events() if event.command.kind == 4]))
        self.ack(pause)
        self.assertEqual((0, 0), (self.status().paused, self.status().terminal),
                         'a UI ACK alone cannot claim an observed PAUSE')
        paused_image = nine_pixel_icon()
        perception.paint_template(paused_image, 'continue')
        paused = self.analyze(paused_image)
        self.assertEqual(1, paused.state)
        self.now += 100_000_000
        self.assertEqual(1, self.observe(paused, prefix=pause.id))
        self.assertEqual((1, 1, 1, 1, 1),
                         (self.status().terminal, self.status().goods, self.status().paused,
                          self.status().reason, self.status().inputs))
        self.assertEqual(0, self.tick()[0])
        self.assertEqual([4, 2], [event.command.kind for event in self.events()])


if __name__ == '__main__':
    unittest.main()
