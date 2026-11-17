"""Native target-only exclusion of a positively observed closed red chest.

Sparse-feature redraws are procedural calibration fixtures, not phone runs.
"""
import ctypes as C
import json
from pathlib import Path
import unittest

from tests import test_native_offer_coverage104 as offers
from tests.test_native_ring094 import Result
from tests.test_target_assessment087 import WIDTH

ROOT = Path(__file__).resolve().parents[1]
FEATURE = json.loads((ROOT/'necroprobe/closed_container_features105.json').read_text())['entry']


def shop_scene(ax=-3, ay=-3, container_slot=2):
    scene = offers.shop_scene(ax=ax, ay=ay)
    offers.set_tile(scene, ax+container_slot, ay+1, 0)
    return scene


def shop_pixels(left=339, sy=43, container_slot=2, damage=None, target=False,
                target_name=True, missing_price=None):
    pixels = bytearray(offers.shop_pixels(left=left, sy=sy, target=target,
        target_name=target_name, missing_price=missing_price))
    cx = left+36*container_slot
    for y in range(sy+24, sy+91):
        for x in range(cx-18, cx+18):
            offers._put(pixels, x, y, (27, 17, 15))
    shape = FEATURE['container_shape'];icon = FEATURE['icons'][0]
    for y in range(33):
        gold, dark = int(shape['gold_rows_hex'][y], 16), int(shape['dark_rows_hex'][y], 16)
        for x in range(36):
            colour = (220, 160, 15) if gold>>x&1 else (12, 8, 7) if dark>>x&1 else (60, 60, 60)
            offers._put(pixels, cx-18+x, sy+49+y, colour)
    for x, y, r, g, b in icon['bright']:
        offers._put(pixels, cx-18+x, sy+49+y, (r, g, b))
    for x, y in icon['dark']:
        offers._put(pixels, cx-18+x, sy+49+y, (0, 0, 0))
    if damage == 'lid':
        for y in range(sy+51, sy+62):
            for x in range(cx-15, cx+16):
                offers._put(pixels, x, y, (60, 60, 60))
    elif damage == 'recolor':
        for y in range(sy+49, sy+82):
            for x in range(cx-18, cx+18):
                at = 4*(y*WIDTH+x)
                r, g, b = pixels[at:at+3]
                offers._put(pixels, x, y, (g, b, r))
    elif damage == 'band_shift':
        for y in range(sy+49, sy+82):
            row = bytes(pixels[4*(y*WIDTH+cx-18):4*(y*WIDTH+cx+18)])
            for x in range(36):
                r, g, b = row[4*x:4*x+3]
                if r>85 and g>45 and 2*b<g and 50*r<=100*g<=110*r:
                    offers._put(pixels, cx-18+x, y, (60, 60, 60))
                    offers._put(pixels, cx-17+x, y, (r, g, b))
    if container_slot != missing_price:
        digits = ('111', '101', '101', '101', '101', '101', '111')
        for i in range(3):
            for y, row in enumerate(digits):
                for x, bit in enumerate(row):
                    if bit == '1':offers._put(pixels, cx-6+4*i+x, sy+82+y, (245, 245, 245))
    return bytes(pixels)


class NativeClosedOffer105Tests(unittest.TestCase):
    setUpClass = classmethod(offers.NativeOfferCoverage104Tests.setUpClass.__func__)

    def assess(self, pixels=None, scene=None):
        return offers.normal_assess(self.lib, shop_pixels() if pixels is None else pixels,
            shop_scene() if scene is None else scene)

    def test_positive_closed_red_identity_alone_explains_its_unknown_lower_cell(self):
        for slot in range(3):
            with self.subTest(slot=slot):
                scene = shop_scene(container_slot=slot);before = bytes(scene)
                status, result = self.assess(shop_pixels(container_slot=slot), scene)
                self.assertEqual((0, 3, 2, 10),
                    (status, result.outcome, result.coverage, result.certificate.policy_version))
                self.assertEqual((2, 1), (result.certificate.non_target_items, result.certificate.ignored_containers))
                self.assertEqual(11, result.rows[result.selected_row].slots[slot].ignored_container_id)
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
                self.assertEqual(before, bytes(scene), 'a closed-container proof never invents FLOOR')

    def test_damaged_recolored_or_displaced_closed_structure_is_not_excluded(self):
        for damage in ('lid', 'recolor', 'band_shift'):
            with self.subTest(damage=damage):
                self.assertNotEqual(3, self.assess(shop_pixels(damage=damage))[1].outcome)
        for missing in range(3):
            self.assertNotEqual(3, self.assess(shop_pixels(missing_price=missing))[1].outcome)
        scene = shop_scene();offers.set_tile(scene, -2, -2, 0)
        self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        for kind in (2, 3, 4, 5):
            scene = shop_scene();offers.set_tile(scene, -1, -2, kind)
            self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)

    def test_target_or_candidate_has_priority_over_closed_identity(self):
        # TEST111 mode2 uses the image and observed price glyphs, without numeric OCR.
        for named, expected in ((True, 2), (False, 2)):
            self.assertEqual(expected, self.assess(shop_pixels(target=True, target_name=named))[1].outcome)
        pixels = bytearray(shop_pixels());sprite = offers.FEATURES['icons'][0]
        left, top = 411-sprite['width']//2, 92
        for x, y, r, g, b in sprite['bright']:
            offers._put(pixels, left+x, top+y, (r, g, b))
        for x, y in sprite['dark']:
            offers._put(pixels, left+x, top+y, (0, 0, 0))
        self.assertEqual(1, self.assess(bytes(pixels))[1].outcome,
            'target evidence over the closed-object body must precede its exclusion')

    def test_numeric_closed_identity_and_binary_target_domain_are_both_required(self):
        status, base = self.assess();self.assertEqual((0, 3, 10),
            (status, base.outcome, base.certificate.policy_version))
        for field, low in (('ignored_icon_score', .939999999), ('ignored_gold_iou', .939999999),
                           ('ignored_gold_coverage', .949999999), ('ignored_dark_iou', .939999999),
                           ('ignored_dark_coverage', .949999999)):
            result = Result.from_buffer_copy(base)
            setattr(result.rows[result.selected_row].slots[2], field, low)
            self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        for fault in ('id', 'pose', 'upper', 'word', 'domain', 'strip_extreme', 'pose_extreme', 'metric_nan', 'cx_extreme', 'sy_extreme'):
            result = Result.from_buffer_copy(base);slot = result.rows[result.selected_row].slots[2]
            if fault == 'id':slot.ignored_container_id = 9
            elif fault == 'pose':slot.ignored_icon_box[0] += 100
            elif fault == 'upper':slot.icon_upper_bound = .8
            elif fault == 'word':slot.word_present, slot.word_iou, slot.word_coverage = 1, .82, .90
            elif fault == 'domain':slot.non_target_icon_box[2] = 35
            elif fault == 'strip_extreme':result.certificate.strip_box[0] = (1 << 31)-1
            elif fault == 'pose_extreme':slot.ignored_icon_box[0] = (1 << 31)-1
            elif fault == 'cx_extreme':slot.cx = -(1 << 31)
            elif fault == 'sy_extreme':slot.sy = (1 << 31)-1
            else:slot.ignored_gold_iou = float('nan')
            self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))


if __name__ == '__main__':
    unittest.main()
