"""TEST068: actual lower-edge gold evidence is not an invented map cell.

Public procedural HUD and color patches exercise the C perception entrypoint.
The known TEST067 first run supplies the edge-row failure; these images are
independent fixtures, not fabricated game responses after an unobserved step.
"""
import unittest
from PIL import ImageDraw

from tests import test_native_perception as fixture

CORE = fixture.CORE
GOLD = (160, 120, 32)
EDGE_DOWN = 3


def tile_index(x, y):
    return (y + 5) * 23 + x + 11


def patch(image, x, y, count=625, color=GOLD):
    cx, cy = 448 + 36*x, 207 + 36*y
    # Exactly count independent pixels inside the existing 25x25 sample.
    for n in range(count):
        image.putpixel((cx-12+n % 25, cy-12+n // 25), color)


def bracket(row=5, center=0, left=625, right=625):
    image = fixture.synthetic_floor()
    patch(image, center-1, row, left)
    patch(image, center+1, row, right)
    return image


class NativeFringe068Tests(unittest.TestCase):
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

    def test_unique_outside_bracket_is_explicit_hint_without_in_grid_gold(self):
        for center in (-4, 0, 4):
            with self.subTest(center=center):
                out = self.analyze(bracket(center=center))
                self.assertEqual((2, EDGE_DOWN, 0), (out.state, out.gold_state, out.goods))
                self.assertEqual(0, sum(kind == 2 for kind in out.tiles),
                                 'row5 is outside the array and must never be shifted to row4')
                self.assertEqual(0, sum(out.protected_cells))
                self.assertEqual(230, len(out.tiles))

    def test_both_raw_gold_samples_retain_the_original_280_pixel_boundary(self):
        for left, right in ((279, 280), (280, 279), (280, 280), (281, 280), (280, 281)):
            with self.subTest(left=left, right=right):
                out = self.analyze(bracket(left=left, right=right))
                self.assertEqual(left >= 280 and right >= 280, out.gold_state == EDGE_DOWN)
                self.assertEqual(0, sum(kind == 2 for kind in out.tiles))

    def test_masked_in_grid_pair_restores_only_the_real_two_coordinates(self):
        for row in (3, 4):
            with self.subTest(row=row):
                out = self.analyze(bracket(row=row))
                gold = [(i % 23-11, i // 23-5) for i, kind in enumerate(out.tiles) if kind == 2]
                self.assertEqual((2, 2, 0), (out.state, out.gold_state, out.goods))
                self.assertEqual([(-1, row), (1, row)], gold)
                self.assertEqual(0, out.tiles[tile_index(0, row)],
                                 'a concealed bracket center is still unobserved, not a FLOOR')
                self.assertEqual(0, sum(out.protected_cells))

    def test_one_side_solid_gold_and_multiple_pairs_supply_no_edge_authority(self):
        images = []
        one = fixture.synthetic_floor(); patch(one, -1, 5); images.append(('one', one))
        solid = bracket(); patch(solid, 0, 5); images.append(('solid', solid))
        multiple = bracket(); patch(multiple, 3, 5); patch(multiple, 5, 5)
        images.append(('multiple_columns', multiple))
        rows = bracket(); patch(rows, -1, 4); patch(rows, 1, 4)
        images.append(('multiple_rows', rows))
        for name, image in images:
            with self.subTest(name=name):
                out = self.analyze(image)
                self.assertNotEqual(EDGE_DOWN, out.gold_state)
                self.assertEqual(0, sum(kind == 2 for kind in out.tiles))

    def test_heart_arrow_or_short_bottom_bars_alone_are_not_a_gold_bracket(self):
        for element in ('red_heart', 'yellow_heart', 'arrow', 'bars'):
            with self.subTest(element=element):
                image = fixture.synthetic_floor(); draw = ImageDraw.Draw(image)
                if element.endswith('heart'):
                    color = (200, 40, 20) if element == 'red_heart' else GOLD
                    draw.polygon([(427, 352), (437, 343), (447, 350), (458, 343),
                                  (469, 352), (469, 368), (448, 386), (427, 368)], fill=color)
                elif element == 'arrow':
                    draw.polygon([(755, 345), (775, 345), (775, 339), (789, 354),
                                  (775, 369), (775, 361), (755, 361)], fill=GOLD)
                else:
                    for x in (390, 426, 462, 498, 534):
                        draw.rectangle((x, 350, x+3, 385), fill=GOLD)
                out = self.analyze(image)
                self.assertNotEqual(EDGE_DOWN, out.gold_state)
                self.assertEqual(0, sum(kind == 2 for kind in out.tiles))

    def test_partial_visible_goods_and_existing_gold_keep_their_original_authority(self):
        for visible in (False, True):
            with self.subTest(visible=visible):
                image = bracket(); image.paste((200, 190, 10), (190, 90, 211, 111))
                if visible:
                    for x in (196, 232, 268):
                        image.paste((56,)*3, (x-12, 136, x+12, 137))
                        image.paste((141,)*3, (x-11, 165, x+7, 166))
                out = self.analyze(image)
                self.assertEqual(2 if visible else 1, out.goods)
                self.assertTrue(any(out.protected_cells))
                self.assertNotEqual(EDGE_DOWN, out.gold_state)
        # An already observed gold cell remains authoritative; this helper
        # must not replace a normal candidate with a boundary-only hint.
        image = bracket(); patch(image, -4, 0)
        out = self.analyze(image)
        self.assertEqual(2, out.gold_state)
        self.assertEqual([(-4, 0)], [(i % 23-11, i // 23-5)
                         for i, kind in enumerate(out.tiles) if kind == 2])


if __name__ == '__main__':
    unittest.main()
