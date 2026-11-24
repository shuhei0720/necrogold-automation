"""Independent raw floor moments for policy17, using procedural pixels only.

The saved TEST117/1fd107 and108 upper floor medians cross the old hue test
while their raw channel sums and per-pixel hue medians agree. This fixture
uses four generic mottled colors, not phone pixels or private Controller state.
"""
import ctypes as C
from fractions import Fraction
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_offer_witness109 as old_offer
from tests import test_native_single_offer108 as single
from tests import test_native_ring114 as paired
from tests import test_native_ring117 as lower
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result

ROOT = Path(__file__).resolve().parents[1]


def mottled_floor_pixels(*, left=375, sy=43, mirror=False, side=1, fault=None, **kwargs):
    pixels = bytearray(lower.single_face_pixels(left=left, sy=sy, mirror=mirror, **kwargs))
    cx = left + (108 if side else -36)
    for i in range(625):
        rgb = ((28, 17, 16) if i < 100 else (43, 25, 22) if i < 300
               else (31, 18, 17) if i < 450 else (38, 23, 20))
        if fault == 'mixture':
            rgb = ((43, 10, 4) if i < 150 else (35, 36, 36) if i < 300
                   else (31, 18, 16) if i < 462 else (39, 22, 20))
        elif fault == 'upper_flat' and i < 300:
            rgb = (43, 25, 22)
        elif fault == 'upper_black' and i < 31:
            rgb = (0, 0, 0)
        elif fault == 'upper_bright' and 100 <= i < 112:
            rgb = (180, 180, 180)
        elif fault == 'lower_black' and 300 <= i < 333:
            rgb = (0, 0, 0)
        elif fault == 'lower_bright' and 450 <= i < 463:
            rgb = (180, 180, 180)
        elif fault == 'wrong_gain' and 100 <= i < 300:
            rgb = (50, 28, 24)
        elif fault == 'wrong_hue' and 100 <= i < 300:
            rgb = (43, 20, 22)
        offer._put(pixels, cx-12+i % 25, sy+36+i // 25, rgb)
    return bytes(pixels)


def blue_sum_boundary(pixels, *, cx=483, sy=43):
    """Independent exact arithmetic constructs the two sides of the stated3%."""
    full = [(cx-12+x, sy+36+y) for y in range(25) for x in range(25)]
    upper = full[:300]

    def rgb(point):
        x, y = point
        return pixels[4*(y*896+x):4*(y*896+x)+3]

    fr = sum(rgb(p)[0] for p in full)
    hr = sum(rgb(p)[0] for p in upper)
    fb = sum(rgb(p)[2] for p in full)
    hb = sum(rgb(p)[2] for p in upper)

    def admitted(delta):
        a, b = (fb+delta)*hr, (hb+delta)*fr
        return 100*abs(a-b) <= 3*max(a, b)

    first_outside = next(delta for delta in range(5000) if not admitted(delta))
    assert first_outside and admitted(first_outside-1)
    # Change only ratios already above both upper medians. Their rank stays
    # unchanged, so this is a channel-sum boundary, not a changed hue median.
    full_ratios = sorted(Fraction(rgb(p)[2], rgb(p)[0]) for p in full)
    upper_ratios = sorted(Fraction(rgb(p)[2], rgb(p)[0]) for p in upper)
    bound = max(full_ratios[len(full_ratios)//2], upper_ratios[len(upper_ratios)//2])
    options = []
    for x, y in upper:
        r, g, b = rgb((x, y))
        if Fraction(b, r) <= bound:
            continue
        limit = min(255, (56*65536-32769-19595*r-38470*g)//7471)
        if limit > b:
            options.append((x, y, limit-b))
    assert sum(p[2] for p in options) >= first_outside
    results = []
    for delta in (first_outside-1, first_outside):
        value = bytearray(pixels)
        remaining = delta
        for x, y, capacity in options:
            add = min(capacity, remaining)
            value[4*(y*896+x)+2] += add
            remaining -= add
            if not remaining:
                break
        assert remaining == 0
        results.append(bytes(value))
    return results


class NativeFloorMoments118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='floor-moments118-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO118_FLOOR_RING_SOURCE',
            str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = bank.NativeRingBank094Tests.build_library(source, Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, pixels=None, scene=None, *, mirror=False, **kwargs):
        if scene is None:
            scene = lower.lower_entry_scene(ax=-5 if mirror else -2, mirror=mirror)
        before = bytes(scene)
        if pixels is None:
            pixels = mottled_floor_pixels(left=267 if mirror else 375, mirror=mirror, **kwargs)
        status, value = offer.normal_assess(self.lib, pixels, scene)
        self.assertEqual(0, status)
        self.assertEqual(before, bytes(scene), 'a floor witness cannot relabel observed geometry')
        return value

    def negative(self, **kwargs):
        value = self.assess(**kwargs)
        self.assertEqual((3, 2, 17, 0), (value.outcome, value.coverage,
            value.certificate.policy_version, value.certificate.failure_flags),
            'independent visible floor hue must not fail because channel medians use different ranks')
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        self.assertTrue(all(cap.floor_full == cap.floor_upper == cap.floor_lower == 1
            for cap in value.certificate.endcaps))
        return value

    def test_mottled_floor_uses_both_raw_moments_without_moving_thresholds(self):
        for mirror in (False, True):
            for side in (0, 1):
                with self.subTest(mirror=mirror, side=side):
                    self.negative(mirror=mirror, side=side)

    def test_mean_cancelling_foreign_colors_cannot_prove_the_cap(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                value = self.assess(mirror=mirror, fault='mixture')
                self.assertNotEqual(3, value.outcome,
                    'a matching channel average cannot hide unrelated pixel hues')
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_both_halves_keep_texture_visibility_brightness_and_gain_guards(self):
        faults = ('upper_flat', 'upper_black', 'upper_bright', 'lower_black',
                  'lower_bright', 'wrong_gain', 'wrong_hue')
        for fault in faults:
            with self.subTest(fault=fault):
                value = self.assess(fault=fault)
                self.assertNotEqual(3, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_existing_three_percent_bound_is_exact_on_both_sides(self):
        inside, outside = blue_sum_boundary(mottled_floor_pixels())
        self.negative(pixels=inside)
        self.assertNotEqual(3, self.assess(pixels=outside).outcome,
            'one extra blue sum unit crossing3% must be rejected')

    def test_observed_caps_extra_items_prices_protection_and_hud_stay_required(self):
        for kind in (0, 2, 3, 4, 5, 6):
            observed = lower.lower_entry_scene()
            offer.set_tile(observed, 1, -3, kind)
            with self.subTest(cap_kind=kind):
                self.assertNotEqual(3, self.assess(scene=observed).outcome)
        for field in ('tiles', 'protected_cells'):
            observed = lower.lower_entry_scene()
            getattr(observed, field)[9*23+15] = 6 if field == 'tiles' else 1
            with self.subTest(extra=field):
                self.assertNotEqual(3, self.assess(scene=observed).outcome)
        pixels = bytearray(mottled_floor_pixels())
        for i in range(18):
            offer._put(pixels, 480+i % 6, 43+69+i // 6, (245, 245, 245))
        self.assertNotEqual(3, self.assess(pixels=bytes(pixels)).outcome)
        self.assertNotEqual(3, self.assess(missing_price=1).outcome)
        self.assertNotEqual(3, self.assess(pixels=mottled_floor_pixels(sy=-10)).outcome)

    def test_strong_target_and_old_offer_policy_results_are_preserved(self):
        for named in (False, True):
            with self.subTest(named=named):
                value = self.assess(target=True, target_name=named)
                self.assertEqual(2, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        cases = ((old_offer.witnessed_pixels(fragment=0), offer.shop_scene(), 9),
                 (old_offer.witnessed_pixels(left=304, sy=87, single_face=True, fragment=0),
                  single.shop_scene(), 11),
                 (paired.paired_pixels(upper=True), paired.paired_scene(True), 15))
        for pixels, scene, policy in cases:
            with self.subTest(policy=policy):
                value = self.assess(pixels=pixels, scene=scene)
                self.assertEqual((3, policy), (value.outcome, value.certificate.policy_version))
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))


if __name__ == '__main__':
    unittest.main()
