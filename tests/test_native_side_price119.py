"""Separate side-shop prices; procedural pixels are not phone acceptance.

TEST118's actual center price has one unrelated white pixel above it.  A
price is a positively observed glyph, independent of other item identities.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_side_shop100 as side
from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result

ROOT = Path(__file__).resolve().parents[1]
LEFT, SY = 301, 117


def builder():
    value = side.NativeSideShop100Tests(methodName='runTest')
    value.entries = bank.bank_data()['entries'][:3]
    return value


def price_pixels(lower=1, fragment=1, *, missing=None, height=7,
                 extra=None, target=False, target_name=False, positions=None):
    value = builder()
    pixels = bytearray(value.pixels(missing_shop_glyph=True,
        missing_merchant=True, target=target, target_name=target_name))
    for y in range(SY+69, SY+91):
        for x in range(LEFT-54, LEFT+126):
            at = 4*(y*896+x)
            pixels[at:at+4] = bytes((27, 17, 12, 255))
    rows = ('111', '101', '101', '101', '101', '101', '111', '111', '111', '111')
    for slot in range(3):
        if slot == missing:
            continue
        cx = LEFT+36*slot
        offset, glyph_height = positions[slot] if positions else (82 if slot == lower else 75, height)
        top = SY+offset
        for digit in range(3):
            for y, row in enumerate(rows[:glyph_height]):
                for x, bit in enumerate(row):
                    if bit == '1':
                        value.white(pixels, cx-6+4*digit+x, top+y)
    for k in range(fragment):
        value.white(pixels, LEFT+36*lower-2+k % 3, SY+69+k//3)
    if extra:
        extra(value, pixels)
    return bytes(pixels)


def ring_library(path):
    source = Path(os.environ.get('NECRO119_SIDE_RING_SOURCE',
        str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
    lib = bank.NativeRingBank094Tests.build_library(source, path)
    lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
    lib.ng2_ring_negative_certificate.restype = C.c_int
    return lib


class NativeSidePrice119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='side-price119-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = ring_library(Path(cls.tmp.name)/'ring.so')

    def assess(self, pixels=None, *, mirror=False, scene=None, **kwargs):
        scene = builder().scene(mirror=mirror) if scene is None else scene
        before = bytes(scene)
        status, value = offer.normal_assess(self.lib,
            price_pixels(**kwargs) if pixels is None else pixels, scene)
        self.assertEqual(0, status)
        self.assertEqual(before, bytes(scene), 'price observation cannot edit a Scene')
        return value

    def negative(self, **kwargs):
        value = self.assess(**kwargs)
        self.assertEqual((3, 2, 4, 3, 0), (value.outcome, value.coverage,
            value.certificate.policy_version, value.certificate.layout_version,
            value.certificate.failure_flags),
            'three owned complete price glyphs do not require another item catalog identity')
        self.assertEqual((3, 3, 3, 0, 0), (value.certificate.observed_items,
            value.certificate.observed_prices, value.certificate.non_target_items,
            value.certificate.ignored_containers, value.certificate.unmatched_prices))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        return value

    def test_complete_low_price_and_same_column_small_fragment_are_separate_evidence(self):
        for mirror in (False, True):
            for lower in range(3):
                for fragment in (0, 1, 17):
                    with self.subTest(mirror=mirror, lower=lower, fragment=fragment):
                        self.negative(mirror=mirror, lower=lower, fragment=fragment)
        for height in (8, 9):
            with self.subTest(height=height):
                self.negative(height=height)

    def test_missing_malformed_fourth_and_split_price_cannot_disappear(self):
        for slot in range(3):
            with self.subTest(missing=slot):
                self.assertNotEqual(3, self.assess(missing=slot).outcome)
        for height in (6, 10):
            with self.subTest(height=height):
                self.assertNotEqual(3, self.assess(height=height).outcome)
        extras = {
            'fourth': lambda b, p: b.white(p, LEFT+15, SY+75, 3, 6),
            'same_x_supported': lambda b, p: b.white(p, LEFT+36-2, SY+69, 6, 3),
            'split_fourth': lambda b, p: (b.white(p, LEFT+15, SY+69, 3, 3),
                                         b.white(p, LEFT+15, SY+74, 3, 3)),
            'two_lower': lambda b, p: b.white(p, LEFT-6, SY+82, 11, 7),
        }
        for name, extra in extras.items():
            with self.subTest(extra=name):
                self.assertNotEqual(3, self.assess(fragment=0, extra=extra).outcome)

    def test_multiple_lower_tops_cannot_disagree_with_the_independent_C_selector(self):
        value = self.assess(lower=0, fragment=1, positions=((83, 8), (80, 7), (82, 7)))
        self.assertNotEqual(3, value.outcome,
            'a unique last bottom is insufficient when two prices start in the lower band; '
            f'policy={value.certificate.policy_version}, layout={value.certificate.layout_version}')
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_existing_scene_support_items_caps_and_extra_board_remain_required(self):
        points = [(-6, y) for y in range(-4, 1)]+[(0, -3), (0, -1),
            (-4, -1), (-3, -1), (-2, -1), (-5, -1), (-1, -1), (0, -2)]
        for point in points:
            scene = builder().scene()
            builder().put(scene, *point, 0)
            builder().put(scene, 10, 4, 2)
            with self.subTest(missing=point):
                self.assertNotEqual(3, self.assess(scene=scene).outcome)
        def extra_board(b, pixels):
            for y in range(166, 195):
                for x in range(585, 615):
                    at = 4*(y*896+x)
                    pixels[at:at+4] = bytes((220, 210, 10, 255))
        self.assertNotEqual(3, self.assess(extra=extra_board).outcome)
        for field in ('state', 'goods', 'gold_state'):
            scene = builder().scene()
            setattr(scene, field, 0)
            with self.subTest(field=field):
                self.assertNotEqual(3, self.assess(scene=scene).outcome)

    def test_target_image_and_priceless_candidate_stay_prior_to_generic_absence(self):
        for named in (False, True):
            with self.subTest(named=named):
                value = self.assess(target=True, target_name=named, fragment=0)
                self.assertEqual(2, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        value = self.assess(target=True, missing=1, fragment=0)
        self.assertEqual(1, value.outcome)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        value = self.assess(target=True, target_name=False, fragment=1)
        self.assertEqual(1, value.outcome,
            'an uncertain image-price association remains a candidate before any absence proof')
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_typed_lower_price_geometry_and_generic_cells_are_independently_validated(self):
        original = self.negative()
        mutations = {
            'policy': lambda r: setattr(r.certificate, 'policy_version', 17),
            'layout': lambda r: setattr(r.certificate, 'layout_version', 2),
            'height6': lambda r: r.certificate.price_boxes[1].__setitem__(3, 6),
            'height10': lambda r: r.certificate.price_boxes[1].__setitem__(3, 10),
            'lower_top': lambda r: r.certificate.price_boxes[1].__setitem__(1, SY+81),
            'lower_end': lambda r: r.certificate.price_boxes[1].__setitem__(1, SY+85),
            'two_lower': lambda r: r.certificate.price_boxes[0].__setitem__(1, SY+82),
            'extra_price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'item': lambda r: setattr(r.certificate, 'observed_items', 2),
            'ignored': lambda r: setattr(r.certificate, 'ignored_containers', 1),
            'NaN': lambda r: setattr(r.partial[0], 'icon_upper_bound', float('nan')),
            'positive': lambda r: setattr(r.partial[0], 'icon_upper_bound', .80),
        }
        for name, mutate in mutations.items():
            value = Result.from_buffer_copy(original)
            mutate(value)
            with self.subTest(forgery=name):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))


class NativeSidePriceController119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='side-price-controller119-')
        cls.addClassCleanup(cls.tmp.cleanup)
        original = native.CORE
        source = os.environ.get('NECRO119_SIDE_CONTROLLER_SOURCE')
        if source:
            overlay = Path(cls.tmp.name)/'core'
            overlay.mkdir()
            for entry in original.iterdir():
                (overlay/entry.name).symlink_to(Path(source) if entry.name == 'NG2Controller.c' else entry)
            native.CORE = overlay
        try:
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = original
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.ring = ring_library(Path(cls.tmp.name)/'ring.so')

    tearDownClass = classmethod(cycle.NativeCycle094Tests.tearDownClass.__func__)

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib = self.lib
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def normal(self, *, mirror=False, scene_change=None, result_change=None):
        scene = builder().scene(mirror=mirror)
        status, value = offer.normal_assess(self.ring, price_pixels(), scene)
        self.assertEqual((0, 3, 4, 3), (status, value.outcome,
            value.certificate.policy_version, value.certificate.layout_version))
        if scene_change:
            scene_change(scene)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        if result_change:
            result_change(value)
        value.started_ns, value.finished_ns = self.h.now, self.h.now+1
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))

    def test_normal_separate_price_reaches_independent_adoption_durable_restart_and_floor(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                self.setUp()
                self.normal(mirror=mirror)
                self.assertEqual((3, 0, 4), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state),
                    'C checks side-room geometry independently of the new price observer')
                self.q.pause_observed()
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(1, self.q.intent(restart))
                self.q.next_floor(restart)
                self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))

    def test_raw_scene_and_typed_price_forgeries_do_not_gain_restart_authority(self):
        changes = {
            'wall': lambda s: (builder().put(s, -6, -3, 0), builder().put(s, 10, 4, 2)),
            'cap': lambda s: builder().put(s, -1, -1, 0),
            'item': lambda s: builder().put(s, -3, -1, 0),
            'opening': lambda s: builder().put(s, 0, -2, 0),
        }
        for name, change in changes.items():
            with self.subTest(scene=name):
                self.setUp()
                self.normal(scene_change=change)
                self.assertEqual((0, 3), (self.q.cycle().outcome, self.q.cycle().status))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
        mutations = {
            'policy': lambda r: setattr(r.certificate, 'policy_version', 17),
            'height': lambda r: r.certificate.price_boxes[1].__setitem__(3, 6),
            'range': lambda r: r.certificate.price_boxes[1].__setitem__(1, SY+85),
            'multiple_lower': lambda r: r.certificate.price_boxes[0].__setitem__(1, SY+82),
            'extra_price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'candidate': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
        }
        for name, change in mutations.items():
            with self.subTest(certificate=name):
                self.setUp()
                self.normal(result_change=change)
                self.assertEqual((0, 3), (self.q.cycle().outcome, self.q.cycle().status))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))


if __name__ == '__main__':
    unittest.main()
