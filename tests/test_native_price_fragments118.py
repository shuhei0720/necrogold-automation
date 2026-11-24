"""TEST117's new lower-entry policy retains the existing price-ink rule.

The received 1fd source106 has three exposed products and a one/two-pixel
white fragment beside their prices. Source107/108 additionally fail an
independent endcap witness; these procedural cases do not relax that proof
or replay the phone's Controller state.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests import test_native_ring117 as lower
from tests.test_native_ring094 import Result

ROOT = Path(__file__).resolve().parents[1]


def fragmented_prices_pixels(fragment, *, mirror=False, **kwargs):
    left = 267 if mirror else 375
    pixels = bytearray(lower.single_face_pixels(left=left, mirror=mirror, **kwargs))
    # The source's x=left+17 fragment lies between independently observed
    # price groups. It is inside the full target sweep, but outside every
    # actual price's owned 23-pixel window.
    for i in range(fragment):
        offer._put(pixels, left+16+i % 3, 43+69+i // 3, (245, 245, 245))
    return bytes(pixels)


class NativePriceFragments118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='price-fragments118-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO118_RING_SOURCE',
            str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = bank.NativeRingBank094Tests.build_library(source,
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, fragment, *, mirror=False, **kwargs):
        scene = lower.lower_entry_scene(ax=-5 if mirror else -2, mirror=mirror)
        before = bytes(scene)
        status, result = offer.normal_assess(self.lib,
            fragmented_prices_pixels(fragment, mirror=mirror, **kwargs), scene)
        self.assertEqual(0, status)
        self.assertEqual(before, bytes(scene), 'price grouping cannot relabel observed geometry')
        return result

    def test_lower_entry_uses_existing_eighteen_ink_rule_for_small_nonprice_fragments(self):
        for mirror in (False, True):
            for fragment in (1, 2, 17):
                with self.subTest(mirror=mirror, fragment=fragment):
                    value = self.assess(fragment, mirror=mirror)
                    self.assertEqual((3, 2, 17, 0), (value.outcome, value.coverage,
                        value.certificate.policy_version, value.certificate.failure_flags),
                        'a sub-18-ink fragment cannot invent a fourth supported price under policy17')
                    self.assertEqual((3, 0), (value.certificate.observed_prices,
                        value.certificate.unmatched_prices))
                    self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_independent_fourth_price_at_eighteen_ink_still_rejects_absence(self):
        for fragment in (18, 24):
            with self.subTest(fragment=fragment):
                value = self.assess(fragment)
                self.assertEqual((17, 4, 1), (value.certificate.policy_version,
                    value.certificate.observed_prices, value.certificate.unmatched_prices))
                self.assertEqual(64, value.certificate.failure_flags & 64)
                self.assertNotEqual(3, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_small_fragment_cannot_replace_missing_price_or_cap_visibility(self):
        for fault in ({'missing_price': 1}, {'missing_wall': True}):
            with self.subTest(fault=fault):
                value = self.assess(17, **fault)
                self.assertNotEqual(3, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_target_image_and_own_price_stay_prior_to_nonprice_fragment(self):
        for target_name in (False, True):
            with self.subTest(target_name=target_name):
                value = self.assess(2, target=True, target_name=target_name)
                self.assertEqual(2, value.outcome,
                    'the strong target image and its own price retain target priority with or without a name')
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))


if __name__ == '__main__':
    unittest.main()
