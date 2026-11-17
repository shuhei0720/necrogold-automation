"""TEST105 normal procedural offer producer joined to public C cycle authority.

A full observed SIGN anchors a top-aligned shorter adjacent component. These
pixels/Scenes/clocks are procedural; they do not reconstruct phone futures.
"""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_observed_shop_controller104 as old_controller
from tests import test_native_offer_coverage104 as offers
from tests import test_native_ring_bank094 as bank


class NativeOfferController105Tests(unittest.TestCase):
    setUpClass = classmethod(old_controller.NativeObservedShopController104Tests.setUpClass.__func__)
    tearDownClass = classmethod(old_controller.NativeObservedShopController104Tests.tearDownClass.__func__)
    setUp = old_controller.NativeObservedShopController104Tests.setUp

    def normal(self, *, mirror=False, target=False, target_name=True, missing_price=None,
               closed_slot=None, mutate=None, source_mutate=None):
        if not hasattr(self, 'ring'):
            tmp = tempfile.TemporaryDirectory(prefix='offer-controller105-')
            self.addCleanup(tmp.cleanup)
            self.ring = bank.NativeRingBank094Tests.build_library(
                native.CORE/'NG2Ring.c', Path(tmp.name)/'ring.so')
        full, fragment = (-15, -14, 30, 29), (-14, -14, 29, 17)
        if closed_slot is None:
            s = offers.shop_scene()
            rgba = offers.shop_pixels(faces=(fragment, full) if mirror else (full, fragment),
                target=target, target_name=target_name, missing_price=missing_price)
        else:
            from tests import test_native_closed_offer105 as closed
            s = closed.shop_scene(container_slot=closed_slot)
            rgba = closed.shop_pixels(container_slot=closed_slot, target=target,
                target_name=target_name, missing_price=missing_price)
        status, value = offers.normal_assess(self.ring, rgba, s)
        self.assertEqual((0, 0), (status, value.status))
        if source_mutate: source_mutate(s)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(s))))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        original = cycle.Result.from_buffer_copy(bytes(value))
        original.started_ns = original.finished_ns = 0
        value.started_ns, value.finished_ns = self.h.now, self.h.now + 1
        normalized = cycle.Result.from_buffer_copy(bytes(value))
        normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(original), bytes(normalized),
            'joining preserves normal pixel evidence, except its procedural host clock')
        if mutate: mutate(value)
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
        return job, value

    def restart_after_durable_intent(self, job):
        self.assertEqual((3, 0, 4),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state),
            'the independently checked complete producer result must permit the existing negative cycle')
        self.assertEqual(0, self.q.durable())
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(
            self.h.engine, restart.id, self.h.now, 1, 0, 1), 'restart still requires durable intent')
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))
        waiting = self.q.cycle()
        self.assertEqual(job.level_id, waiting.level_id)
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id + 1, 0), (self.q.cycle().level_id, self.q.cycle().state))

    def held(self):
        self.assertNotEqual(3, self.q.cycle().outcome)
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))
        self.assertEqual(0, self.h.status().restarts)

    def test_normal_top_anchored_fragment_reaches_durable_intent_restart_ack_and_new_floor(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                self.setUp()
                job, value = self.normal(mirror=mirror)
                self.assertEqual((3, 2, 9),
                    (value.outcome, value.coverage, value.certificate.policy_version))
                self.restart_after_durable_intent(job)

    def test_normal_target_candidate_and_unobserved_price_never_restart(self):
        # TEST111 mode2 uses the image and observed price glyphs, without numeric OCR.
        for target, name, price, expected in (
                (True, True, None, 2), (True, False, None, 2),
                (True, False, 1, 1), (False, True, 1, 0)):
            with self.subTest(target=target, name=name, price=price):
                self.setUp()
                _, value = self.normal(target=target, target_name=name, missing_price=price)
                self.assertEqual(expected, value.outcome)
                self.assertEqual(int(expected in (1, 2)), self.q.cycle().candidate_latched)
                self.held()

    def test_c_independently_rejects_shifted_fragment_subminimum_and_counterfeit_absence(self):
        changes = {
            'shifted_top': lambda r: r.certificate.board_boxes[1].__setitem__(1,
                r.certificate.board_boxes[1][1] + 1),
            'two_fragments': lambda r: r.certificate.board_boxes[0].__setitem__(3, 17),
            'short': lambda r: r.certificate.board_boxes[1].__setitem__(3, 15),
            'wide_delta': lambda r: r.certificate.board_boxes[1].__setitem__(2, 26),
            'count149': lambda r: r.certificate.board_counts.__setitem__(1, 149),
            'new_price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'possible_target': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
        }
        for fault, mutate in changes.items():
            with self.subTest(fault=fault):
                self.setUp()
                _, value = self.normal(mutate=mutate)
                self.assertEqual(3, value.outcome)
                self.assertEqual((0, 3, 7),
                    (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                self.held()

    def test_normal_closed_offer_reaches_durable_intent_restart_ack_and_new_floor(self):
        for slot in range(3):
            with self.subTest(container_slot=slot):
                self.setUp()
                job, value = self.normal(closed_slot=slot)
                self.assertEqual((3, 2, 10, 2, 1),
                    (value.outcome, value.coverage, value.certificate.policy_version,
                     value.certificate.non_target_items, value.certificate.ignored_containers))
                self.assertEqual(11, value.rows[value.selected_row].slots[slot].ignored_container_id)
                self.restart_after_durable_intent(job)

    def test_closed_offer_metrics_ordinary_price_floor_and_target_absence_are_independent(self):
        # TEST111 mode2 uses the image and observed price glyphs, without numeric OCR.
        def red(value): return value.rows[value.selected_row].slots[2]
        changes = {
            'icon': lambda r: setattr(red(r), 'ignored_icon_score', .939),
            'gold_iou': lambda r: setattr(red(r), 'ignored_gold_iou', .939),
            'gold_coverage': lambda r: setattr(red(r), 'ignored_gold_coverage', .949),
            'dark_iou': lambda r: setattr(red(r), 'ignored_dark_iou', .939),
            'dark_coverage': lambda r: setattr(red(r), 'ignored_dark_coverage', .949),
            'other_chest': lambda r: setattr(red(r), 'ignored_container_id', 9),
            'bad_pose': lambda r: red(r).ignored_icon_box.__setitem__(0, 40),
            'possible_target': lambda r: setattr(red(r), 'icon_upper_bound', .8),
            'strong_word': lambda r: (setattr(red(r), 'word_present', 1),
                setattr(red(r), 'word_iou', .82), setattr(red(r), 'word_coverage', .90)),
        }
        for fault, mutate in changes.items():
            with self.subTest(fault=fault):
                self.setUp()
                _, value = self.normal(closed_slot=2, mutate=mutate)
                self.assertEqual(3, value.outcome)
                self.assertEqual((0, 3, 7),
                    (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                self.held()
        for ordinary_slot in (0, 1):
            with self.subTest(unseen_ordinary_price_floor=ordinary_slot):
                self.setUp()
                self.normal(closed_slot=2, source_mutate=lambda s:
                    offers.set_tile(s, -3 + ordinary_slot, -2, 0))
                self.assertEqual((0, 3, 7),
                    (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                self.held()
        for named, price, expected in ((True, None, 2), (False, None, 2), (False, 1, 1)):
            with self.subTest(target_named=named, missing_price=price):
                self.setUp()
                _, value = self.normal(closed_slot=2, target=True, target_name=named, missing_price=price)
                self.assertEqual(expected, value.outcome)
                self.assertEqual(1, self.q.cycle().candidate_latched)
                self.held()


if __name__ == '__main__':
    unittest.main()
