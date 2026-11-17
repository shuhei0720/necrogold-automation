"""Image-primary positives with bounded price support; fixtures are procedural."""
import ctypes as C
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
import tests.test_native_ring_bank094 as bank
from tests.test_native_ring_bank094 import complete_shop, bank_data, auth_data
from tests.test_target_assessment087 import WIDTH, FEATURES


class NativeImagePrice111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='image-price111-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = bank.NativeRingBank094Tests.build_library(
            Path(os.environ.get('NECRO111_RING_SOURCE', str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c'))),
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int
        cls.entries = bank_data()['entries'][:3]

    def shop(self, **kwargs):
        return complete_shop(self.entries, auth=auth_data(), target=True,
                             target_name=False, **kwargs)

    def assess(self, pixels, mode=2):
        now = Clock(lambda _: 100)
        cancel = Cancelled(lambda _: 0)
        options = Options(abi=1, size=C.sizeof(Options), mode=mode,
                          deadline_ns=1000000000, now_ns=now, cancelled=cancel, fast=1)
        result = Result()
        buf = C.create_string_buffer(pixels)
        status = self.lib.ng2_ring_assess_rgba(buf, len(pixels), WIDTH*4,
                                              C.byref(options), C.byref(result))
        self.assertEqual(0, status)
        return result

    def test_strong_target_image_and_observed_price_needs_no_target_name(self):
        result = self.assess(self.shop())
        self.assertEqual(2, result.outcome,
                         'Latest GOODS-02 permits a strong target image with observed price support without a name')
        row = result.rows[result.selected_row]
        self.assertEqual(2, row.slots[1].outcome)
        self.assertGreaterEqual(row.slots[1].icon_score, .94)
        self.assertEqual(1, row.slots[1].icon_score_exact)
        self.assertEqual(0, row.slots[1].word_present)
        self.assertEqual((0., 0.), (row.slots[1].word_iou, row.slots[1].word_coverage))
        self.assertEqual(16, result.certificate.policy_version)
        self.assertEqual((1, 1), (result.certificate.observed_items, result.certificate.observed_prices))
        self.assertEqual(tuple(row.slots[1].icon_box), tuple(result.certificate.item_boxes[1]))
        self.assertGreater(result.certificate.price_boxes[1][2], 0)
        self.assertEqual(1, result.coverage)
        self.assertEqual(2, result.reason)
        self.assertEqual(2, row.reason)
        self.assertEqual(-1, row.word_slot)
        self.assertEqual((0, 0, 0, 0), tuple(result.certificate.name_boxes[1]))
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_same_image_without_its_price_is_retained_as_candidate(self):
        result = self.assess(self.shop(missing_price=1))
        self.assertEqual(1, result.outcome)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    @staticmethod
    def put(pixels, x, y, rgb):
        at = 4*(y*WIDTH+x)
        pixels[at:at+4] = bytes((*rgb, 255))

    def test_price_value_is_not_fixed_to_one_calibration_number(self):
        pixels = bytearray(self.shop(missing_price=1))
        digit = ('111', '101', '111', '101', '111', '101', '111')
        for offset in (0, 4):
            for dy, line in enumerate(digit):
                for dx, ink in enumerate(line):
                    if ink == '1':
                        self.put(pixels, 393+offset+dx, 198+dy, (245, 245, 245))
        self.assertEqual(2, self.assess(bytes(pixels)).outcome,
                         'Observed glyph support is independent of the displayed numeric price')

    def test_clipped_scattered_or_insufficient_own_price_keeps_candidate(self):
        for damage in ('perimeter', 'height', 'two_groups', 'insufficient'):
            with self.subTest(damage=damage):
                pixels = bytearray(self.shop(missing_price=1))
                if damage == 'perimeter':
                    points = [(390+x, 198+y) for x in range(11) for y in range(3)] + [(384, 198)]
                elif damage == 'height':
                    points = [(390+x, 191+y) for x in range(3) for y in range(10)]
                elif damage == 'two_groups':
                    points = [(386+x, 198+y) for x in range(2) for y in range(7)]
                    points += [(404+x, 198+y) for x in range(2) for y in range(7)]
                else:
                    points = [(390+x, 198+y) for y in range(3) for x in range(6)][:17]
                for x, y in points:
                    self.put(pixels, x, y, (245, 245, 245))
                result = self.assess(bytes(pixels))
                self.assertEqual(1, result.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_ambiguous_image_remains_candidate_despite_valid_price(self):
        pixels = bytearray(self.shop())
        # Remove a visible part of the procedural target rather than supplying
        # the implementation with a hand-picked score.
        for dx, dy, *_ in FEATURES['icons'][1]['bright'][:70]:
            self.put(pixels, 378+dx, 155+dy, (27, 17, 12))
        result = self.assess(bytes(pixels))
        self.assertEqual(1, result.outcome)
        score = result.rows[result.selected_row].slots[1].icon_score
        self.assertGreaterEqual(score, .80)
        self.assertLess(score, .94)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_old_name_positive_survives_missing_price(self):
        pixels = complete_shop(self.entries, auth=auth_data(), target=True,
                               target_name=True, missing_price=1)
        result = self.assess(pixels)
        self.assertEqual(2, result.outcome)
        selected = (result.rows[result.selected_row].slots[1] if result.selected_row >= 0
                    else result.partial[result.selected_partial])
        self.assertGreaterEqual(selected.word_iou, .82)

    def test_canonical_mode0_still_requires_the_target_name(self):
        self.assertEqual(1, self.assess(self.shop(), mode=0).outcome)


if __name__ == '__main__':
    unittest.main()
