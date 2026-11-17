"""Positive price support and local floor lighting in fully observed offers.

TEST108 source275 has an eleven-pixel non-price fragment and a textured floor
half whose median changes from (35,20,18) to (40,23,20). These procedural
fixtures exercise those observations without embedding phone pixels. The
Controller chain below is a simulated contract, not an iPhone replay.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests import test_native_single_offer108 as single
from tests.test_native_ring094 import Result

ROOT = Path(__file__).resolve().parents[1]


def put(pixels, x, y, rgb):
    at = 4 * (y * 896 + x)
    pixels[at:at + 4] = bytes((*rgb, 255))


def witnessed_pixels(*, left=339, sy=43, lighting=True, fragment=11,
                     upper=(40, 23, 20), half_black=0, half_bright=0,
                     flat=False, single_face=False, **kwargs):
    pixels = bytearray(single.shop_pixels(left, sy, **kwargs) if single_face
                       else offer.shop_pixels(left, sy, **kwargs))
    if lighting:
        # 200 low + 225 middle + 200 high pixels give the independent full,
        # upper and lower medians used in the received source's diagnostics.
        for i in range(625):
            x, y = left - 48 + i % 25, sy + 36 + i // 25
            if i < 300:
                rgb = upper if flat or i < 200 else (35, 20, 18)
            else:
                rgb = (28, 17, 16) if i < 500 else (35, 20, 18)
            if i < half_black:
                rgb = (0, 0, 0)
            elif i < half_black + half_bright:
                rgb = (180, 180, 180)
            put(pixels, x, y, rgb)
    # Kept apart from the real price's x support. It belongs to the already
    # swept offer cell, and cannot form the existing >=18-ink price witness.
    for i in range(fragment):
        put(pixels, left - 16 + i % 3, sy + 69 + i // 3, (245, 245, 245))
    return bytes(pixels)


class NativeOfferWitness109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='offer-witness109-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO109_RING_SOURCE',
            str(ROOT / 'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = bank.NativeRingBank094Tests.build_library(source, Path(cls.tmp.name) / 'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, pixels=None, scene=None, **kwargs):
        return offer.normal_assess(self.lib,
            witnessed_pixels() if pixels is None else pixels,
            offer.shop_scene() if scene is None else scene, **kwargs)

    def negative(self, pixels=None, scene=None):
        status, value = self.assess(pixels, scene)
        self.assertEqual((0, 3, 2, 9, 0),
            (status, value.outcome, value.coverage,
             value.certificate.policy_version, value.certificate.failure_flags),
            'a fully observed target-free offer row needs a supported negative, not a false fourth price')
        self.assertEqual((3, 3, 0), (value.certificate.observed_items,
            value.certificate.observed_prices, value.certificate.unmatched_prices))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        return value

    def test_small_non_price_fragment_does_not_count_as_a_fourth_price(self):
        for count in (1, 11, 17):
            with self.subTest(ink=count):
                self.negative(witnessed_pixels(lighting=False, fragment=count))

    def test_same_hue_textured_half_uses_the_independent_observed_full_floor(self):
        value = self.negative(witnessed_pixels(fragment=0))
        cap = value.certificate.endcaps[0]
        self.assertEqual((35, 20, 18, 1, 1, 1),
            (cap.r, cap.g, cap.b, cap.floor_full, cap.floor_upper, cap.floor_lower))

    def test_both_independent_causes_are_fixed_in_one_normal_producer_result(self):
        scene = offer.shop_scene()
        before = bytes(scene)
        self.negative(scene=scene)
        self.assertEqual(before, bytes(scene), 'a floor witness cannot fill or relabel Scene cells')

    def test_supported_extra_price_missing_price_and_fourth_item_remain_incomplete(self):
        for pixels in (witnessed_pixels(fragment=18),
                       witnessed_pixels(missing_price=1),
                       witnessed_pixels(extra_object=True)):
            self.assertNotEqual(3, self.assess(pixels)[1].outcome)
        scene = offer.shop_scene()
        offer.set_tile(scene, 8, 3, 6)
        self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)

    def test_half_hue_gain_texture_visibility_and_bright_bounds_are_independent(self):
        faults = ({'upper': (41, 23, 20)},  # blue/r cross product just outside 3%.
                  {'upper': (40, 24, 20)},  # green/r alone exceeds 3%.
                  {'upper': (40, 23, 19)},
                  {'upper': (45, 26, 23)},  # same hue, gain above 5/4.
                  {'flat': True},
                  {'half_black': 31},     # full <10%, upper >10% black.
                  {'half_bright': 12})    # full <24, upper >= its scaled bound.
        for kwargs in faults:
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(3, self.assess(witnessed_pixels(**kwargs))[1].outcome)

    def test_observed_caps_all_three_lower_floors_and_exact_projection_are_required(self):
        for x, y in ((-4, -3), (0, -3), (-3, -2), (-2, -2), (-1, -2)):
            for kind in (0, 4):
                scene = offer.shop_scene()
                offer.set_tile(scene, x, y, kind)
                with self.subTest(cell=(x, y), kind=kind):
                    self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        scene = offer.shop_scene()
        scene.protected_cells[2 * 23 + 8] = 0
        self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)

    def test_target_candidate_and_missing_visibility_are_never_negative(self):
        for target_name, expected in ((True, 2), (False, 1)):
            with self.subTest(target_name=target_name):
                self.assertEqual(expected, self.assess(
                    witnessed_pixels(target=True, target_name=target_name))[1].outcome)
        self.assertNotEqual(3, self.assess(witnessed_pixels(missing_wall=True))[1].outcome)

    def test_single_offer_uses_same_local_witness_without_extending_legacy_modes(self):
        status, value = self.assess(
            witnessed_pixels(left=304, sy=87, single_face=True), single.shop_scene())
        self.assertEqual((0, 3, 11), (status, value.outcome, value.certificate.policy_version))
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.assertNotEqual(3, self.assess(mode=mode)[1].outcome)

    def test_existing_numeric_certificate_rejects_missing_positive_evidence(self):
        base = self.negative()
        changes = (
            lambda v: setattr(v.certificate.endcaps[0], 'floor_upper', 0),
            lambda v: setattr(v.certificate.endcaps[0], 'black_count', 63),
            lambda v: setattr(v.certificate.endcaps[0], 'bright_count', 24),
            lambda v: setattr(v.certificate.endcaps[0], 'r', 255),
            lambda v: setattr(v.certificate, 'observed_prices', 4),
            lambda v: setattr(v.certificate, 'unmatched_prices', 1),
            lambda v: setattr(v.partial[0], 'icon_upper_bound', .8),
        )
        for i, change in enumerate(changes):
            value = Result.from_buffer_copy(base)
            change(value)
            with self.subTest(mutation=i):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))


class NativeOfferWitnessController109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.tmp = tempfile.TemporaryDirectory(prefix='offer-witness-controller109-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            ROOT / 'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name) / 'ring.so')

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def normal(self, *, scene_change=None, result_change=None, **kwargs):
        scene = offer.shop_scene()
        status, value = offer.normal_assess(self.ring, witnessed_pixels(**kwargs), scene)
        self.assertEqual((0, 0), (status, value.status))
        if scene_change:
            scene_change(scene)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
        if result_change:
            result_change(value)
        value.started_ns, value.finished_ns = self.h.now, self.h.now + 1
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
        return job, value

    def test_normal_negative_requires_pause_durable_intent_restart_ack_and_new_floor(self):
        job, value = self.normal()
        self.assertEqual((3, 2, 9), (value.outcome, value.coverage, value.certificate.policy_version))
        self.assertEqual((3, 0, 4), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))
        waiting = self.q.cycle()
        self.assertEqual(job.level_id, waiting.level_id)
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(
            self.h.engine, waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id + 1, 0), (self.q.cycle().level_id, self.q.cycle().state))

    def test_controller_independently_rejects_removed_floor_and_forged_cap_price_or_target(self):
        changes = (
            ('scene', lambda s: offer.set_tile(s, -3, -2, 0)),
            ('scene', lambda s: offer.set_tile(s, -4, -3, 4)),
            ('scene', lambda s: offer.set_tile(s, 8, 3, 6)),
            ('result', lambda v: setattr(v.certificate.endcaps[0], 'floor_upper', 0)),
            ('result', lambda v: setattr(v.certificate.endcaps[0], 'black_count', 63)),
            ('result', lambda v: setattr(v.certificate, 'observed_prices', 4)),
            ('result', lambda v: setattr(v.partial[1], 'icon_upper_bound', .8)),
        )
        for i, (kind, change) in enumerate(changes):
            with self.subTest(mutation=i):
                self.setUp()
                self.normal(**{kind + '_change': change})
                self.assertEqual((0, 3, 7), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))

    def test_target_candidate_and_incomplete_price_keep_restart_closed(self):
        for kwargs in ({'target': True}, {'target': True, 'target_name': False}, {'missing_price': 1}):
            with self.subTest(kwargs=kwargs):
                self.setUp()
                _, value = self.normal(**kwargs)
                self.assertNotEqual(3, value.outcome)
                self.assertNotEqual(3, self.q.cycle().outcome)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
