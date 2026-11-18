"""TEST114 same physical SHOP pair, independent numerical row proofs.

Every pixel, Scene, clock and input response here is procedural. The retained
phone inputs 164 and 250 are calibrated privately; these are not phone replays.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_goods111 as goods
from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_native_shop_coverage102 import _put, draw_faces
from tests.test_target_assessment087 import FEATURES


ROOT = Path(__file__).resolve().parents[1]


def paired_pixels(*, upper=False, **kwargs):
    """The same two components independently seed their measured row centers."""
    left, sy = (301, 225) if upper else (339, 43)
    faces = (((-15, -15, 30, 30), (-15, -15, 30, 27)) if upper
             else ((-15, -14, 30, 29), (-15, -14, 30, 27)))
    pixels = offer.shop_pixels(left=left, sy=sy, faces=faces, **kwargs)
    if upper:
        pixels = bytearray(goods.prices(pixels, left, sy))
        # An independently visible material phase starts two rows above the
        # ordinary 225 endcap. The 223 upper half has seven red-material rows;
        # the 225 upper half has only five. Both full caps remain visible.
        for side in (-48, 96):
            for y in range(sy + 34, sy + 63):
                for x in range(left + side, left + side + 25):
                    colour = (65, 30, 25) if y < sy + 41 else (30, 20, 18)
                    phase = (x + y) % 3
                    colour = (colour[0] + (5 if phase == 0 else -5 if phase == 1 else 0),
                              colour[1], colour[2])
                    _put(pixels, x, y, colour)
        pixels = bytes(pixels)
    return pixels


def paired_scene(upper=False):
    return goods.upper_scene() if upper else offer.shop_scene()


class NativePhysicalPair114Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='physical-pair114-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO114_RING_SOURCE',
            str(ROOT / 'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = bank.NativeRingBank094Tests.build_library(source, Path(cls.tmp.name) / 'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, pixels=None, scene=None, upper=False, **kwargs):
        return offer.normal_assess(self.lib,
            paired_pixels(upper=upper) if pixels is None else pixels,
            paired_scene(upper) if scene is None else scene, **kwargs)

    def test_two_row_centers_from_one_original_pair_have_one_physical_coverage(self):
        scene = paired_scene()
        before = bytes(scene)
        status, result = self.assess(scene=scene)
        self.assertEqual((0, [(339, 43), (339, 42)]),
            (status, [(row.left, row.sy) for row in result.rows[:result.row_count]]),
            'the normal observer must retain both original numerical hypotheses')
        self.assertEqual((3, 2, 9, 1, 0),
            (result.outcome, result.coverage, result.certificate.policy_version,
             result.certificate.accepted_rows, result.certificate.failure_flags),
            'one observed physical pair must receive its complete original offer proof')
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(before, bytes(scene), 'coverage cannot fill any Scene evidence')

    def test_independent_upper_proof_can_use_the_other_measured_row_of_same_pair(self):
        scene = paired_scene(True)
        before = bytes(scene)
        status, result = self.assess(upper=True, scene=scene)
        self.assertEqual((0, [(301, 225), (301, 223)]),
            (status, [(row.left, row.sy) for row in result.rows[:result.row_count]]))
        self.assertEqual((3, 2, 15, 1, 0, 225),
            (result.outcome, result.coverage, result.certificate.policy_version,
             result.certificate.accepted_rows, result.certificate.failure_flags,
             result.certificate.row[1]),
            'the incomplete 223 proof must not hide an independent complete original 225 proof')
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(before, bytes(scene))

    def test_extra_physical_component_cannot_be_collapsed_into_the_original_pair(self):
        for upper in (False, True):
            with self.subTest(upper=upper):
                status, result = self.assess(paired_pixels(upper=upper, extra_board=True), upper=upper)
                self.assertEqual(0, status)
                self.assertNotEqual(3, result.outcome,
                    'a third independently observed component is not a numerical alias')
                pixels = bytearray(paired_pixels(upper=upper))
                draw_faces(pixels, 590, 170,
                    ((-15, -14, 30, 29), (-15, -14, 30, 27)))
                self.assertNotEqual(3, self.assess(bytes(pixels), upper=upper)[1].outcome,
                    'a separate physical pair cannot collapse into the original pair')

    def test_same_pair_cannot_borrow_a_different_world_item_row_or_protection(self):
        for upper in (False, True):
            for fault in ('other_row', 'fourth_item', 'mask', 'floor'):
                scene = paired_scene(upper)
                ax, ay = (-4, 2) if upper else (-3, -3)
                if fault == 'other_row':
                    scene = offer.shop_scene(ax=ax, ay=ay - 1)
                elif fault == 'fourth_item':
                    offer.set_tile(scene, 8, 3, 6)
                elif fault == 'mask':
                    scene.protected_cells[0] = 1
                else:
                    offer.set_tile(scene, ax + 1, ay + 1, 0)
                with self.subTest(upper=upper, fault=fault):
                    self.assertNotEqual(3, self.assess(scene=scene, upper=upper)[1].outcome)

    def test_unobserved_third_sku_price_or_outer_cap_never_becomes_absence(self):
        for upper in (False, True):
            for fault in ('third_price', 'third_item', 'outer_cap'):
                pixels = bytearray(paired_pixels(upper=upper, missing_price=2))
                left, sy = (301, 225) if upper else (339, 43)
                if fault != 'third_price':
                    pixels = bytearray(paired_pixels(upper=upper))
                    x0, x1 = ((left + 54, left + 90) if fault == 'third_item'
                              else (left + 96, left + 121))
                    for y in range(sy + 24, sy + 91):
                        for x in range(x0, x1):
                            _put(pixels, x, y, (0, 0, 0))
                with self.subTest(upper=upper, fault=fault):
                    self.assertNotEqual(3, self.assess(bytes(pixels), upper=upper)[1].outcome)

    def test_target_in_original_row_or_partial_keeps_priority_over_all_aliases(self):
        for upper in (False, True):
            status, result = self.assess(paired_pixels(upper=upper, target=True,
                target_name=False), upper=upper)
            self.assertEqual((0, 2), (status, result.outcome))
            # Remove only the corresponding price: the same genuine target
            # sprite must stay held as candidate through every coverage trial.
            status, result = self.assess(paired_pixels(upper=upper, target=True,
                target_name=False, missing_price=1), upper=upper)
            self.assertEqual((0, 1), (status, result.outcome))

    def test_alias_exclusive_name_edge_is_swept_before_any_negative(self):
        # The earlier measured sy42 has a name-union top one pixel above sy43.
        # A full reference name at that edge must veto the otherwise complete row.
        pixels = bytearray(paired_pixels())
        left, top = 339 - 70, 42 - 20
        for dy, row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row, 16) >> dx & 1:
                    _put(pixels, left + dx, top + dy, (245, 245, 245))
        self.assertEqual(1, self.assess(bytes(pixels))[1].outcome,
            'the wider name union of every retained alias is a positive veto')

    def test_target_at_other_alias_full_strip_edge_cannot_be_lost(self):
        pixels = bytearray(paired_pixels())
        sprite = FEATURES['icons'][0]
        left, top = 339 - 54, 42 + 24
        for y in range(top, top + sprite['height']):
            for x in range(left, left + sprite['width']):
                _put(pixels, x, y, (27, 17, 12))
        for dx, dy, r, g, b in sprite['bright']:
            _put(pixels, left + dx, top + dy, (r, g, b))
        for dx, dy in sprite['dark']:
            _put(pixels, left + dx, top + dy, (0, 0, 0))
        self.assertIn(self.assess(bytes(pixels))[1].outcome, (1, 2),
            'the earlier alias owns this complete primary pose at its exclusive top edge')

    def test_cancel_deadline_and_legacy_modes_cannot_gain_alias_absence(self):
        for upper in (False, True):
            for kwargs, expected in (({'cancelled': True}, 1), ({'deadline': True}, 2)):
                with self.subTest(upper=upper, kwargs=kwargs):
                    status, result = self.assess(upper=upper, **kwargs)
                    self.assertEqual((expected, 0, 0),
                                     (status, result.outcome, result.coverage))
            for mode in (0, 1):
                self.assertNotEqual(3, self.assess(upper=upper, mode=mode)[1].outcome)

    def test_late_alias_cancel_and_deadline_keep_monotonic_work_and_no_absence(self):
        for upper in (False, True):
            pixels, scene = paired_pixels(upper=upper), paired_scene(upper)
            status, complete = self.assess(pixels, scene, upper=upper)
            self.assertEqual((0, 3, 2), (status, complete.outcome, complete.coverage))
            # Place the callback near the completed producer's tail, past its
            # initial scoring. Counts come from public work, not private images
            # or rewritten result timestamps. Both paths must carry prior work.
            late = complete.checks - 100
            self.assertGreater(late, 100)
            for fault, expected in (('cancel', 1), ('deadline', 2)):
                with self.subTest(upper=upper, fault=fault):
                    calls = {'now': 0, 'cancel': 0}

                    def now(_):
                        calls['now'] += 1
                        return 100 * calls['now']

                    def cancel(_):
                        calls['cancel'] += 1
                        return int(fault == 'cancel' and calls['cancel'] >= late)

                    clock, cancelled = Clock(now), Cancelled(cancel)
                    options = Options(abi=1, size=C.sizeof(Options), mode=2, fast=1,
                        scene=C.addressof(scene), now_ns=clock, cancelled=cancelled,
                        deadline_ns=100 * (late + 1) if fault == 'deadline' else 100_000_000)
                    before = bytes(scene)
                    result, buf = Result(), C.create_string_buffer(pixels)
                    code = self.lib.ng2_ring_assess_rgba(buf, len(pixels), 896 * 4,
                        C.byref(options), C.byref(result))
                    self.assertEqual((expected, expected, 0, 0, -1, -1),
                        (code, result.status, result.outcome, result.coverage,
                         result.selected_row, result.selected_partial))
                    self.assertEqual(late, result.checks,
                        'a scratch alias must preserve every prior checkpoint')
                    self.assertEqual(result.checks, calls['cancel'])
                    self.assertEqual(100 * calls['now'], result.finished_ns,
                        'the final clock cannot roll back to an earlier alias')
                    self.assertGreater(result.finished_ns, result.started_ns)
                    self.assertEqual(before, bytes(scene))

    def test_other_alias_full_strip_crossing_fixed_hud_cannot_be_collapsed(self):
        left, sy = 301, 229
        pixels = goods.prices(offer.shop_pixels(left=left, sy=sy,
            faces=((-15, -15, 30, 30), (-15, -13, 30, 30))), left, sy)
        status, result = self.assess(pixels, paired_scene(True), upper=True)
        self.assertEqual((0, [(301, 229), (301, 231)]),
            (status, [(row.left, row.sy) for row in result.rows[:result.row_count]]))
        # Row229's B ends before the fixed y321 HUD. Its measured alias231
        # extends into that HUD, despite projecting to the very same ITEM row.
        self.assertEqual(0, result.outcome,
            'each original alias strip must retain the existing bounds/HUD qualification')
        self.assertNotEqual(2, result.coverage)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_policy_filtered_physical_alias_keeps_its_complete_positive_name_union(self):
        left, sy = 301, 225
        plain = goods.prices(offer.shop_pixels(left=left, sy=sy,
            faces=((-15, -15, 30, 30), (-15, -15, 30, 27))), left, sy)
        status, control = self.assess(plain, paired_scene(True), upper=True)
        self.assertEqual((0, [(301, 225), (301, 223)]),
            (status, [(row.left, row.sy) for row in control.rows[:control.row_count]]))
        self.assertEqual((3, 2, 9, [301, 223]),
            (control.outcome, control.coverage, control.certificate.policy_version,
             list(control.certificate.row)),
            'the existing selected numeric row independently proves this plain control')
        for top in (265, 266):
            pixels = bytearray(plain)
            for dy, row in enumerate(FEATURES['word']['rows_hex']):
                for dx in range(84):
                    if int(row, 16) >> dx & 1:
                        _put(pixels, 280 + dx, top + dy, (245, 245, 245))
            with self.subTest(word_top=top):
                status, result = self.assess(bytes(pixels), paired_scene(True), upper=True)
                self.assertEqual((0, 1), (status, result.outcome),
                    'a physical alias filtered only by the selected policy still owns its positive name union')
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_policy_filtered_physical_alias_keeps_its_complete_primary_strip(self):
        left, sy = 301, 225
        plain = goods.prices(offer.shop_pixels(left=left, sy=sy,
            faces=((-15, -15, 30, 30), (-15, -15, 30, 27))), left, sy)
        for index, sprite in enumerate(FEATURES['icons']):
            pixels = bytearray(plain)
            x0, top = left - 54, sy + 91 - sprite['height']
            for y in range(top, top + sprite['height']):
                for x in range(x0, x0 + sprite['width']):
                    _put(pixels, x, y, (27, 17, 12))
            for dx, dy, r, g, b in sprite['bright']:
                _put(pixels, x0 + dx, top + dy, (r, g, b))
            for dx, dy in sprite['dark']:
                _put(pixels, x0 + dx, top + dy, (0, 0, 0))
            with self.subTest(template=index):
                status, result = self.assess(bytes(pixels), paired_scene(True), upper=True)
                self.assertEqual(0, status)
                self.assertIn(result.outcome, (1, 2),
                    'every measured physical alias owns target poses at its full strip boundary')
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_independent_policy_reuses_its_exact_completed_sweep_within_worker_budget(self):
        # Synthetic cost model, not a phone timing claim. A fixed 32658ns per
        # checkpoint places 100ms between the observed 2873-check full-domain
        # proof and its 3241-check duplicate-work version of this same fixture.
        # The complete per-alias searches remain required under this budget.
        pixels, scene = paired_pixels(upper=True), paired_scene(True)
        calls = {'now': 0}

        def now(_):
            calls['now'] += 1
            return 32658 * calls['now']

        clock, cancelled = Clock(now), Cancelled(lambda _: 0)
        options = Options(abi=1, size=C.sizeof(Options), mode=2, fast=1,
            scene=C.addressof(scene), now_ns=clock, cancelled=cancelled,
            deadline_ns=100_000_000)
        result, buf = Result(), C.create_string_buffer(pixels)
        status = self.lib.ng2_ring_assess_rgba(buf, len(pixels), 896 * 4,
            C.byref(options), C.byref(result))
        self.assertEqual((0, 0, 3, 2, 15),
            (status, result.status, result.outcome, result.coverage,
             result.certificate.policy_version),
            'repeating an already completed exact numeric sweep must not consume the original worker budget')
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertLessEqual(result.finished_ns, options.deadline_ns)
        self.assertGreater(result.finished_ns, result.started_ns)


class NativePhysicalPairAdoption114Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.tmp = tempfile.TemporaryDirectory(prefix='physical-pair-adoption114-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO114_RING_SOURCE',
            str(ROOT / 'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.ring = bank.NativeRingBank094Tests.build_library(source, Path(cls.tmp.name) / 'ring.so')

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def test_initial_full_normal_negative_still_needs_new_pause_durable_and_intent(self):
        for upper in (False, True):
            with self.subTest(upper=upper):
                self.setUp()
                scene = paired_scene(upper)
                status, value = offer.normal_assess(self.ring, paired_pixels(upper=upper), scene)
                self.assertEqual((0, 3, 2), (status, value.outcome, value.coverage),
                    'the very first FULL producer must complete; a later retry cannot stand in for it')
                self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
                job = self.q.cycle()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
                    self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
                worker = self.q.cycle()
                # A newer incompatible material/source prevents a classification
                # retry. It does not replace the immutable already complete FULL.
                ready, pause = self.h.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                latest = deepcopy(scene)
                offer.set_tile(latest, 9, 3, 2)
                self.h.now += 5_000_000
                self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(latest))))
                self.assertEqual(job.job_id, self.q.cycle().job_id)
                value.started_ns, value.finished_ns = worker.worker_started_ns, self.h.now
                self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
                self.assertEqual((3, 0, 4), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state))
                self.assertEqual(0, self.q.durable(), 'unpaused normal proof is not durable PAUSE')
                self.h.ack(pause)
                self.h.now += 210_000_000
                self.assertEqual(1, self.h.observe(self.h.scene(state=1)))
                self.assertEqual(0, self.h.tick()[0], 'durable storage still gates restart')
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.h.engine, restart.id, self.h.now, 1, 0, 1))
                self.assertEqual(1, self.q.intent(restart))


if __name__ == '__main__':
    unittest.main()
