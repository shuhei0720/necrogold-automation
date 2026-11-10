"""TEST066: preserve the two pause bars under short lettering and JPEG gaps.

The public C perception entrypoint is exercised with procedural HUD pixels.
Known device143 establishes the observed failure; these are not future frames.
"""
from PIL import ImageDraw
import unittest

from tests import test_native_perception as fixture
from necroprobe import gold_scan

CORE = fixture.CORE


def fragmented_icon(color=180):
    image = fixture.synthetic_floor()
    image.paste(0, (429, 6, 465, 42))
    fixture.paint_template(image, 'icon', (color, color, color))
    draw = ImageDraw.Draw(image)
    # A short label crosses the icon crop above its bars. One missing row
    # in four edge columns splits 24px bars into 12px and 11px fragments.
    draw.rectangle((429, 8, 464, 11), fill=(color, color, color))
    draw.rectangle((435, 24, 438, 24), fill=(0, 0, 0))
    return image


class NativeIcon066Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = fixture.CORE
        try:
            fixture.CORE = CORE
            fixture.NativePerceptionTests.setUpClass.__func__(cls)
        finally:
            fixture.CORE = previous

    @classmethod
    def tearDownClass(cls):
        fixture.NativePerceptionTests.tearDownClass.__func__(cls)

    analyze = fixture.NativePerceptionTests.analyze

    def test_fragmented_two_bar_icon_with_short_label_is_a_floor(self):
        out = self.analyze(fragmented_icon())
        self.assertEqual(2, out.state,
            'two observed bars with short overlay must retain the full HUD FLOOR classification')
        self.assertEqual((0, 0), (out.goods, out.restart_label))

    def test_fragmented_icon_keeps_original_intensity_boundary(self):
        for brightness in (54, 55, 84, 85, 180):
            with self.subTest(brightness=brightness):
                self.assertEqual(2 if brightness >= 55 else 0,
                                 self.analyze(fragmented_icon(brightness)).state)

    def test_missing_one_bar_white_region_and_short_glyphs_are_not_floor(self):
        for mode in ('absent', 'one_bar', 'white', 'glyph8', 'glyph9', 'glyph10', 'colored'):
            with self.subTest(mode=mode):
                image = fixture.synthetic_floor()
                image.paste(0, (429, 6, 465, 42))
                draw = ImageDraw.Draw(image)
                if mode == 'one_bar':
                    draw.rectangle((435, 12, 442, 35), fill=(180, 180, 180))
                elif mode == 'white':
                    draw.rectangle((429, 6, 464, 41), fill=(255, 255, 255))
                elif mode.startswith('glyph'):
                    height = int(mode.removeprefix('glyph'))
                    for x in (435, 452):
                        draw.rectangle((x, 12, x+7, 11+height), fill=(180, 180, 180))
                        draw.rectangle((x, 36-height, x+7, 35), fill=(180, 180, 180))
                elif mode == 'colored':
                    fixture.paint_template(image, 'icon', (255, 80, 80))
                out = self.analyze(image)
                self.assertEqual(0, out.state)
                self.assertEqual((0, 0), (out.goods, out.beat_valid))

    def test_fragmented_icon_does_not_replace_other_hud_or_menu_guards(self):
        for missing in ('footer', 'zone_one', 'floor_one'):
            with self.subTest(missing=missing):
                image = fragmented_icon()
                image.paste(0, gold_scan._TEMPLATES[missing][0])
                self.assertEqual(0, self.analyze(image).state)
        for label, expected in (('continue', 1), ('death', 0)):
            with self.subTest(label=label):
                image = fragmented_icon()
                fixture.paint_template(image, label)
                self.assertEqual(expected, self.analyze(image).state)

    def test_displaced_bars_remain_rejected_at_the_fixed_hud_location(self):
        for dx, dy in ((4, 0), (-4, 0), (0, 8), (0, -8)):
            with self.subTest(dx=dx, dy=dy):
                image = fixture.synthetic_floor()
                icon = image.crop((429, 6, 465, 42))
                image.paste(0, (429, 6, 465, 42))
                image.paste(icon, (429+dx, 6+dy))
                self.assertEqual(0, self.analyze(image).state)

    def test_original_bright_bars_and_long_opening_path_still_classify_floor(self):
        self.assertEqual(2, self.analyze(fixture.synthetic_floor()).state)
        image = fixture.synthetic_floor()
        for y in range(6, 42, 8):
            image.paste((180, 180, 180), (429, y, 441, min(y+3, 42)))
        self.assertEqual(2, self.analyze(image).state)


if __name__ == '__main__':
    unittest.main()
