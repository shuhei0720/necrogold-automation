"""Independent C adoption of the normally produced high one-face proof.

Procedural pixels and scenes exercise the trust boundary; no private phone
state or unobserved floor is restored by these tests.
"""
import ctypes as C

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_goods113 as goods
from tests import test_native_offer_coverage104 as offer
from tests import test_native_upper_single_face118 as high


class NativeUpperSingleFaceController118Tests(goods.Goods113Base):
    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib = self.lib
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def normal(self, *, mirror=False, scene_change=None, result_change=None,
               target=False, missing_price=None):
        scene = high.shop_scene(mirror=mirror)
        pixels = high.shop_pixels(mirror=mirror, target=target,
            target_name=False, **({'missing_price': missing_price} if missing_price is not None else {}))
        status, result = offer.normal_assess(self.ring, pixels, scene)
        self.assertEqual(0, status)
        self.assertEqual(1 if target and missing_price is not None else 2 if target else 3,
            result.outcome)
        if not target:
            self.assertEqual(18, result.certificate.policy_version)
        if scene_change:
            scene_change(scene)
        before = bytes(scene)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(before)))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
        if result_change:
            result_change(result)
        result.started_ns, result.finished_ns = self.h.now, self.h.now+1
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        self.assertEqual(before, bytes(scene))
        return job

    def refused(self):
        self.assertEqual((0, 3, 7), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_normal_mirrored_high_entrance_reaches_durable_restart_and_next_floor(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                self.setUp()
                self.normal(mirror=mirror)
                self.assertEqual((3, 0, 4), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state),
                    'C must independently accept the normally observed high entrance')
                self.q.pause_observed()
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(1, self.q.intent(restart))
                self.q.next_floor(restart)
                self.assertEqual((1, 0), (self.h.status().restarts,
                    self.h.status().terminal))

    def test_c_rechecks_all_fourteen_supports_opening_and_exact_three_offer_footprint(self):
        for mirror in (False, True):
            for x, y in sorted(high.boundary(mirror=mirror)):
                def change(scene, x=x, y=y):
                    offer.set_tile(scene, x, y, 0)
                    offer.set_tile(scene, 10, 4, 2)
                with self.subTest(mirror=mirror, missing=(x, y)):
                    self.setUp()
                    self.normal(mirror=mirror, scene_change=change)
                    self.refused()
            for kind in (0, 2, 3, 4, 6):
                with self.subTest(mirror=mirror, opening=kind):
                    self.setUp()
                    self.normal(mirror=mirror, scene_change=lambda scene, kind=kind:
                        offer.set_tile(scene, -5 if mirror else 1, -3, kind))
                    self.refused()
        faults = {
            'lower_floor': lambda s: offer.set_tile(s, -1, 2, 0),
            'cap': lambda s: offer.set_tile(s, 0, 1, 0),
            'extra_item': lambda s: offer.set_tile(s, 10, 3, 6),
            'extra_protection': lambda s: s.protected_cells.__setitem__(9*23+21, 1),
            'missing_protection': lambda s: s.protected_cells.__setitem__(6*23+8, 0),
        }
        for name, change in faults.items():
            with self.subTest(scene=name):
                self.setUp()
                self.normal(scene_change=change)
                self.refused()

    def test_a_typed_numeric_certificate_cannot_replace_scene_geometry_or_prices(self):
        def wrong_policy(result):
            result.certificate.policy_version = result.certificate.board_mode = 17
        mutations = {
            'other_shape_policy17': wrong_policy,
            'gold_count': lambda r: setattr(r.certificate, 'actual_gold_cells', 15),
            'layout': lambda r: setattr(r.certificate, 'layout_version', 2),
            'invented_face': lambda r: r.certificate.board_counts.__setitem__(1, 200),
            'short_face': lambda r: r.certificate.board_boxes[0].__setitem__(3, 28),
            'fourth_price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'positive_bound': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
            'nonfinite': lambda r: setattr(r.partial[0], 'icon_upper_bound', float('nan')),
        }
        for name, mutate in mutations.items():
            with self.subTest(certificate=name):
                self.setUp()
                self.normal(result_change=mutate)
                self.refused()

    def test_target_and_priceless_candidate_stay_held_before_any_negative_restart(self):
        for missing in (None, 1):
            with self.subTest(missing_price=missing):
                self.setUp()
                self.normal(target=True, missing_price=missing)
                self.assertEqual((2 if missing is None else 1, 1, 7),
                    (self.q.cycle().outcome, self.q.cycle().candidate_latched,
                     self.q.cycle().state))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
