"""TEST100 fresh PARTIAL jobs on procedural public-C observations.

The received223/225 pair supplies the exposure class. No original image is
embedded and no future game acceptance or classifier accuracy is asserted.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_entry097 as entry
from tests.test_native_ring094 import Result


def cross(point):
    x, y = point
    return {(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)}


class NativePartialRebind100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry.NativePartialEntry097Tests.setUpClass()
        cls.lib = entry.NativePartialEntry097Tests.lib

    @classmethod
    def tearDownClass(cls):
        entry.NativePartialEntry097Tests.tearDownClass()

    def setUp(self):
        self.p = entry.NativePartialEntry097Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q

    @staticmethod
    def safe(value):
        value.partial_safe_no_positive = value.partial_count = 1
        value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
        value.partial[0].icon_score_exact = 1

    def pending(self, direction=1, **kwargs):
        protected = cross((-5, 2))
        extra = {(-5, 2): 'item', (-6, 2): 'floor', (-7, 2): 'gold', (-8, 2): 'floor'}
        return self.p.pending(direction=direction, extra=extra, protected=protected, **kwargs)

    @staticmethod
    def exposed(source, point=(-7, 2), adjacent=True):
        value = deepcopy(source)
        value.tiles[point] = 'item'
        value.protected.update(cross(point))
        if adjacent:
            value.tiles[(-6, 2)] = 'item'
            value.protected.update(cross((-6, 2)))
        return value

    def rebind(self):
        source, retired = self.pending()
        old = self.q.cycle()
        latest = self.exposed(source)
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.q.cycle()
        self.assertEqual((old.job_id + 1, 1, 1), (fresh.job_id, fresh.pending, fresh.state),
                         'new exposed ITEM must bind a fresh PARTIAL classification job')
        self.assertEqual((self.h.number, self.h.prefix), (fresh.capture_id, fresh.prefix))
        self.assertGreater(fresh.capture_id, old.capture_id)
        self.assertLessEqual(fresh.continuation_deadline_ns, old.continuation_deadline_ns)
        self.assertEqual((0, 0, 0, 2, 1), (fresh.worker_started_ns, fresh.assessment_ns,
            fresh.candidate_latched, self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.h.tick()[0], 'unclassified newly exposed goods never authorize input')
        return source, latest, retired, old, fresh

    def test_new_exposure_gets_new_identity_and_rejects_old_worker_result(self):
        _, _, retired, old, fresh = self.rebind()
        before = (bytes(self.q.cycle()), bytes(self.h.status()))
        stale = Result(abi=1, size=C.sizeof(Result), selected_row=-1, selected_partial=-1,
                       started_ns=self.h.now, finished_ns=self.h.now + 1)
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine, old.job_id,
            old.capture_id, old.prefix, self.h.now, C.byref(stale)))
        self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine, old.job_id,
            old.capture_id, old.prefix, self.h.now))
        self.assertEqual(before, (bytes(self.q.cycle()), bytes(self.h.status())))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, retired.id, self.h.now, 1, 0, 1))
        self.assertEqual(fresh.job_id, self.q.cycle().job_id)

    def test_new_candidate_or_unsafe_unknown_is_held_without_movement_or_restart(self):
        for outcome in (0, 1, 2):
            with self.subTest(outcome=outcome):
                self.setUp()
                self.rebind()
                self.q.assess(outcome, 1)
                self.assertEqual((7, outcome, int(outcome != 0)), (self.q.cycle().state,
                    self.q.cycle().outcome, self.q.cycle().candidate_latched))
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                    self.h.status().restarts))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))

    def test_safe_new_result_uses_old_horizon_and_one_rebind_per_stationary_episode(self):
        _, latest, _, old, fresh = self.rebind()
        self.q.assess(0, 1, self.safe)
        self.assertEqual((3, old.continuation_deadline_ns), (self.q.cycle().state,
            self.q.cycle().continuation_deadline_ns))
        second = self.exposed(latest, point=(-8, 2), adjacent=False)
        self.p.observe(second)
        self.assertEqual(fresh.job_id, self.q.cycle().job_id,
                         'a bind/time refresh cannot reset the one-use stationary allowance')
        self.assertEqual(7, self.q.cycle().state)
        self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
            self.h.status().restarts))

    def test_horizon_expiry_after_new_result_cannot_restore_old_observation_credit(self):
        _, latest, _, old, _ = self.rebind()
        self.q.assess(0, 1, self.safe)
        self.h.now = old.continuation_deadline_ns + 1
        self.p.observe(latest)
        self.assertEqual(7, self.q.cycle().state)
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_reveal_requires_old_items_protection_and_remote_envelope(self):
        for fault in ('old_item', 'old_protection', 'near', 'extra_protection', 'other_material', 'no_growth'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _ = self.pending()
                old = self.q.cycle()
                latest = self.exposed(source)
                if fault == 'old_item': latest.tiles[(-5, 2)] = 'floor'
                elif fault == 'old_protection': latest.protected.discard((-5, 1))
                elif fault == 'near': latest.tiles[(-1, 0)] = 'item'; latest.protected.update(cross((-1, 0)))
                elif fault == 'extra_protection': latest.protected.add((8, 4))
                elif fault == 'other_material': latest.tiles[(8, 3)] = 'dirt'
                elif fault == 'no_growth': latest = deepcopy(source)
                self.p.observe(latest)
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                if fault != 'no_growth': self.assertEqual(7, self.q.cycle().state)

    def test_real_opening_same_prefix_strict_zero_and_original_deadline_remain_required(self):
        for fault in ('no_ack', 'wrong_ack', 'motion', 'unknown_motion', 'prefix', 'unstable', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _ = self.pending(direction=3 if fault == 'wrong_ack' else 1, opened=fault != 'no_ack',
                    opening_direction=2 if fault == 'wrong_ack' else 1)
                old = self.q.cycle()
                latest = self.exposed(source)
                if fault == 'motion': latest.signature = native.translated(source, 1).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80]) * 23296
                elif fault == 'deadline': self.h.now = old.continuation_deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                self.p.observe(latest, **({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                                         {'stable': 0} if fault == 'unstable' else {}))
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))


if __name__ == '__main__':
    unittest.main()
