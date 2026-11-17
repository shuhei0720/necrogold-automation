"""Observed top-clipped SHOP face anchored by a complete adjacent face.

Procedural pixels exercise the measured geometry; they are not phone results.
"""
import ctypes as C
import unittest

from tests import test_native_offer_coverage104 as offers
from tests.test_native_ring094 import Result


class NativeOfferGeometry105Tests(unittest.TestCase):
    setUpClass = classmethod(offers.NativeOfferCoverage104Tests.setUpClass.__func__)
    scene = staticmethod(offers.shop_scene)
    pixels = staticmethod(offers.shop_pixels)
    assess = offers.NativeOfferCoverage104Tests.assess

    def test_same_top_observed_fragment_uses_full_face_row_and_preserves_target_priority(self):
        # TEST111 mode2 uses the image and observed price glyphs, without numeric OCR.
        full = (-15, -14, 30, 29)
        fragment = (-14, -14, 29, 17)
        for faces in ((full, fragment), (fragment, full)):
            with self.subTest(faces=faces):
                status, result = self.assess(self.pixels(faces=faces))
                self.assertEqual((0, 3, 2, 9),
                    (status, result.outcome, result.coverage, result.certificate.policy_version),
                    'three observed prices/products and anchored positive face geometry authorize absence')
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
                for named, expected in ((True, 2), (False, 2)):
                    self.assertEqual(expected,
                        self.assess(self.pixels(faces=faces, target=True, target_name=named))[1].outcome)
                self.assertEqual(1, self.assess(self.pixels(faces=faces, target=True,
                    target_name=False, missing_price=1))[1].outcome)

    def test_unanchored_shifted_missing_or_subminimum_fragments_remain_unknown(self):
        full = (-15, -14, 30, 29)
        fragment = (-14, -14, 29, 17)
        for faces in ((full, None), (full, (-14, -13, 29, 17)),
                      (full, (-14, -14, 29, 15)), (full, (-14, -14, 26, 17)),
                      (full, (-15, -4, 30, 19)), (full, (-15, -10, 30, 29))):
            with self.subTest(faces=faces):
                self.assertNotEqual(3, self.assess(self.pixels(faces=faces))[1].outcome)
        # Two equal components have their own centered legacy row. This is
        # the original min16/full-pair proof, not authority for the new branch.
        status, legacy = self.assess(self.pixels(faces=(fragment, fragment)))
        self.assertEqual((0, 3), (status, legacy.outcome))

    def test_numeric_certificate_requires_same_top_anchor_and_target_absence(self):
        full = (-15, -14, 30, 29)
        status, base = self.assess(self.pixels(faces=(full, (-14, -14, 29, 17))))
        self.assertEqual((0, 3, 9), (status, base.outcome, base.certificate.policy_version))
        changes = {
            'shifted top': lambda r: r.certificate.board_boxes[1].__setitem__(1, r.certificate.board_boxes[1][1]+1),
            'two fragments': lambda r: r.certificate.board_boxes[0].__setitem__(3, 17),
            'too short': lambda r: r.certificate.board_boxes[1].__setitem__(3, 15),
            'count149': lambda r: r.certificate.board_counts.__setitem__(1, 149),
            'different width': lambda r: r.certificate.board_boxes[1].__setitem__(2, 26),
            'candidate': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
            'extra price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
        }
        for name, mutate in changes.items():
            with self.subTest(name=name):
                result = Result.from_buffer_copy(base)
                mutate(result)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))


if __name__ == '__main__':
    unittest.main()
