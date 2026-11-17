"""TEST110: two pause bars remain observable behind thin name strokes.

The public fixture is procedural, not a stored device crop. Original80c6/321
motivates the mechanism; its later input and game response remain unrecorded.
The fixed full-ROI proof never fills a missing bar or clips observed padding.
"""
import ctypes as C
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from PIL import ImageDraw

from necroprobe import gold_scan
from tests import test_native_controller as controller
from tests import test_native_icon084 as prior
from tests import test_native_perception as perception
from tests import test_native_recovery as mechanics


def thin_letter_icon(color=(180, 180, 180)):
    image = prior.nine_pixel_icon(color)
    draw = ImageDraw.Draw(image)
    # Thin, long letter strokes survive a vertical-only opening. The two
    # observed bars retain their wider runs independently of those strokes.
    for x in (430, 432, 445, 448, 461, 463):
        draw.line((x, 12, x, 35), fill=color)
    return image


class NativeRectIcon110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core = Path(os.environ.get('NECRO_TEST110_ICON_CORE', str(controller.CORE)))
        previous = mechanics.CORE
        try:
            mechanics.CORE = core
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_analyze_rgba.argtypes = [
            C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(controller.Scene)]
        cls.lib.ng2_analyze_rgba.restype = C.c_int
        cls.probe_temp = tempfile.TemporaryDirectory(prefix='rect-icon110-')
        cls.addClassCleanup(cls.probe_temp.cleanup)
        directory = Path(cls.probe_temp.name)
        present = 'static void ng2_icon_rect3x9(' in (core/'NG2Perception.c').read_text()
        source = directory/'probe.c'
        source.write_text('#include "'+str(core/'NG2Perception.c')+'"\n'
            '#define HAS_RECT_ICON '+str(int(present))+'\n'+r'''
/* HOST TEST ONLY: inspect the actual private opening, not shipped in IPA. */
void ng2_test_rect_icon110(const unsigned char *mask,unsigned char *out){
#if HAS_RECT_ICON
    unsigned char eroded[1296];ng2_icon_rect3x9(mask,eroded,out);
#else
    (void)mask;memset(out,0,1296);
#endif
}
''')
        target = directory/'probe.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
            '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-shared',
            str(source), '-lm', '-o', str(target)], check=True)
        cls.probe = C.CDLL(str(target))
        cls.probe.ng2_test_rect_icon110.argtypes = [
            C.POINTER(C.c_uint8), C.POINTER(C.c_uint8)]

    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
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
    analyze = prior.NativeIcon084Tests.analyze

    def test_thin_letter_strokes_keep_two_independently_observed_pause_bars(self):
        image = thin_letter_icon()
        for evidence in prior.full_icon_stages(image).values():
            self.assertLess(5*evidence[0], 4*evidence[1],
                'all retained raw/vertical paths fail before this new positive proof')
        value = self.analyze(image)
        self.assertEqual((2, 0, 0), (value.state, value.restart_label, value.goods),
            'observed two-bar rectangles with thin label strokes still show a live floor')

    def test_intensity_neutrality_and_the_fixed_full_icon_location_are_preserved(self):
        for brightness in (54, 55, 84, 85, 180):
            with self.subTest(brightness=brightness):
                self.assertEqual(2 if brightness >= 55 else 0,
                    self.analyze(thin_letter_icon((brightness,)*3)).state)
        self.assertEqual(0, self.analyze(thin_letter_icon((255, 80, 80))).state)
        for dx, dy in ((4, 0), (-4, 0), (0, 8), (0, -8)):
            with self.subTest(shift=(dx, dy)):
                image = thin_letter_icon()
                icon = image.crop((429, 6, 465, 42))
                image.paste(0, (429, 6, 465, 42))
                image.paste(icon, (429+dx, 6+dy))
                self.assertEqual(0, self.analyze(image).state)

    def test_missing_bar_thin_letters_short_glyphs_and_visible_padding_do_not_pass(self):
        for mode in ('absent', 'one_bar', 'white', 'letters', 'glyph8', 'glyph9',
                     'glyph10', 'padding3'):
            with self.subTest(mode=mode):
                image = thin_letter_icon() if mode == 'padding3' else perception.synthetic_floor()
                if mode != 'padding3':
                    image.paste(0, (429, 6, 465, 42))
                draw = ImageDraw.Draw(image)
                if mode == 'one_bar':
                    draw.rectangle((435, 12, 442, 35), fill=(180,)*3)
                elif mode == 'white':
                    draw.rectangle((429, 6, 464, 41), fill=(255,)*3)
                elif mode == 'letters':
                    for x in (430, 432, 445, 448, 461, 463):
                        draw.line((x, 12, x, 35), fill=(180,)*3)
                elif mode.startswith('glyph'):
                    height = int(mode.removeprefix('glyph'))
                    for x in (435, 452):
                        draw.rectangle((x, 12, x+7, 11+height), fill=(180,)*3)
                        draw.rectangle((x, 36-height, x+7, 35), fill=(180,)*3)
                elif mode == 'padding3':
                    draw.rectangle((429, 6, 431, 41), fill=(180,)*3)
                self.assertEqual(0, self.analyze(image).state)

    def test_footer_menu_death_and_invalid_raster_guards_still_precede_floor(self):
        for missing in ('footer', 'zone_one', 'floor_one'):
            with self.subTest(missing=missing):
                image = thin_letter_icon()
                image.paste(0, gold_scan._TEMPLATES[missing][0])
                self.assertEqual(0, self.analyze(image).state)
        for label, expected in (('continue', 1), ('death', 0)):
            with self.subTest(label=label):
                image = thin_letter_icon()
                perception.paint_template(image, label)
                self.assertEqual(expected, self.analyze(image).state)
        raw = thin_letter_icon().convert('RGBA').tobytes()
        for invalid, stride in ((raw[:-1], 3584), (raw[:-1]+b'\0', 3584), (raw, 3583)):
            value = controller.Scene()
            self.assertEqual(-1, self.lib.ng2_analyze_rgba(
                invalid, len(invalid), stride, C.byref(value)))
            self.assertEqual((0, 0, 0), (value.state, value.goods, value.beat_valid))

    def test_rectangular_opening_is_a_subset_and_does_not_clip_three_pixel_padding(self):
        rng = random.Random(110321)
        masks = []
        for index in range(24):
            mask = bytearray(rng.randrange(2) for _ in range(1296))
            x0, y0 = (index*3)%29, (index*5)%23
            for y in range(y0, y0+13):
                for x in range(x0, x0+7):
                    mask[y*36+x] = 1
            masks.append(mask)
        padding = bytearray(1296)
        for y in range(36):
            for x in range(3):
                padding[y*36+x] = 1
        masks.append(padding)
        for number, mask in enumerate(masks):
            value = (C.c_uint8*1296).from_buffer_copy(mask)
            before = bytes(value)
            result = (C.c_uint8*1296)()
            self.probe.ng2_test_rect_icon110(value, result)
            with self.subTest(mask=number):
                self.assertEqual(before, bytes(value))
                self.assertTrue(all(v in (0, 1) and (not v or mask[i])
                                    for i, v in enumerate(result)),
                    'no opening may add an unobserved pixel, including at the crop edge')
        self.assertEqual(bytes(padding), bytes(result),
            'the full3px padding stripe remains in the union; it is not erased or cropped')

    def test_input_pixels_and_opaque_stride_padding_do_not_change_the_scene(self):
        image = thin_letter_icon()
        before = image.tobytes()
        self.assertEqual(bytes(self.analyze(image)), bytes(self.analyze(image, padding=17)))
        self.assertEqual(before, image.tobytes())

    def test_public_rgba_after_ack_holds_goods_and_requires_an_observed_pause(self):
        self.fit()
        move = self.next_move()
        original_ticket = bytes(move)
        self.ack(move)
        image = prior.visible_merchandise(thin_letter_icon())
        before = image.tobytes()
        goods = self.analyze(image)
        self.assertEqual((2, 2), (goods.state, goods.goods))
        self.assertEqual(before, image.tobytes())
        self.now = max(self.now+2, move.target_ns+80_000_002)
        self.assertEqual(1, self.observe(goods, prefix=move.id))
        state = self.status()
        self.assertEqual((1, 0, 1, 1, 0, 0),
            (state.inputs, state.moves, state.goods, state.reason, state.paused, state.terminal))
        self.assertEqual(0, self.motion_wait().active)
        self.assertEqual(original_ticket, bytes(self.events()[0].command))
        ready, pause = self.tick()
        self.assertEqual((1, 2, self.number), (ready, pause.kind, pause.source_capture_id))
        self.ack(pause)
        self.assertEqual((0, 0), (self.status().paused, self.status().terminal))
        paused_image = thin_letter_icon()
        perception.paint_template(paused_image, 'continue')
        self.now += 100_000_000
        self.assertEqual(1, self.observe(self.analyze(paused_image), prefix=pause.id))
        self.assertEqual((1, 1, 1, 1, 1),
            (self.status().terminal, self.status().goods, self.status().paused,
             self.status().reason, self.status().inputs))
        self.assertEqual(0, self.tick()[0])
        self.assertEqual([4, 2], [e.command.kind for e in self.events()])


if __name__ == '__main__':
    unittest.main()
