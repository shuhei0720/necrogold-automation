"""TEST116 late UP proof after an early FULL through public C APIs.

The earlier ACK, normal Motion, Ring pixels, clocks and later responses are
procedural. This isolates the early-FULL/late-unit boundary calibrated with
TEST115's 136->142 UNKNOWN and 136->144 MOVED; it is not phone replay. Both
GOODS_UNKNOWN and normally classified PARTIAL pre-MOVE sources are exercised;
neither is an unrecorded phone response.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_goods113 as goods
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular
from tests.test_native_motion075 import Motion


class NativeEarlyFull116Tests(goods.Goods113Base):
    @classmethod
    def setUpClass(cls):
        prior = os.environ.get('NECRO113_GOODS_CORE')
        chosen = os.environ.get('NECRO116_EARLY_CORE')
        try:
            if chosen:
                os.environ['NECRO113_GOODS_CORE'] = chosen
            super().setUpClass()
            cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
            cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
            cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
                C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64] * 4 + [C.c_int32, C.c_uint64]
            cls.lib.ng2_controller_observe_irregular_at.restype = None
        finally:
            if prior is None:
                os.environ.pop('NECRO113_GOODS_CORE', None)
            else:
                os.environ['NECRO113_GOODS_CORE'] = prior

    def setUp(self):
        self.p = current.current_view_fixture(self.lib)
        self.addCleanup(self.p.doCleanups)

    def motion(self, a, b):
        first, last = self.h.scene(2, 2, a, beat=True), self.h.scene(2, 2, b, beat=True)
        value = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(first), C.byref(last), 3, C.byref(value)))
        return value.kind, value.dx, value.dy

    def observe(self, terrain, *, advance=70_000_000, prefix=None):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, terrain, beat=True),
            start=self.h.now-2, end=self.h.now,
            prefix=self.h.prefix if prefix is None else prefix)

    def arm_partial(self):
        self.h = self.p.harness()
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib, self.q.h = self.lib, self.h
        before = native.translated(goods.NativeGoodsUpView113Tests.source(), 4)
        before.goods = 'partial'
        closed = deepcopy(before)
        closed.goods = 'unknown'
        closed.protected.clear()
        for point, kind in list(closed.tiles.items()):
            if kind == 'item': closed.tiles[point] = 'floor'
        closed.tiles[(0, -1)] = 'door'
        initial = native.translated(closed, 4)
        initial.tiles[(0, 0)] = 'floor'
        self.h.fit(initial)
        first = self.h.next_move(initial)
        self.assertEqual(3, first.direction)
        self.h.ack(first)
        closed = native.translated(initial, 3)
        self.h.observed_result(first, closed)
        opening = self.h.next_move(closed)
        self.assertEqual(3, opening.direction)
        self.h.ack(opening)
        before.signature = closed.signature
        self.h.observed_result(opening, before)
        self.assertEqual((1, 1, 3), (self.h.status().moves,
            self.h.status().door_changes, self.h.events()[-1].motion))
        normal = self.producer(before, left=375, sy=8)
        self.assertEqual((0, 0, 3, 1), (normal.outcome, normal.row_count,
            normal.partial_count, normal.partial_safe_no_positive),
            'normal PARTIAL probes, not a desired result, admit the preceding UP')
        self.commit(normal)
        command = None
        for _ in range(220):
            self.assertEqual(1, self.observe(before, advance=20_000_000))
            ready, proposed = self.h.tick()
            if ready:
                self.assertEqual((4, 3), (proposed.kind, proposed.direction))
                command = proposed
                break
            self.assertFalse(self.h.status().terminal, 'normal PARTIAL entry must remain eligible')
        self.assertIsNotNone(command, 'normal PARTIAL result must admit the bounded first UP')
        return before, command

    def pending(self, *, prepared=False, positive=False, partial_before=False):
        if partial_before:
            self.before, self.old = self.arm_partial()
        else:
            self.h, self.before, self.old, _ = self.p.armed(direction=3)
            self.q = cycle.NativeCycle094Tests(methodName='runTest')
            self.q.lib, self.q.h = self.lib, self.h
        self.h.ack(self.old)
        self.h.now = max(self.h.now+2, self.old.target_ns+100_000_000)
        self.early = goods.NativeGoodsUpView113Tests.source()
        self.early.signature = bytes(255-v for v in native.translated(self.before, 3).signature)
        self.assertEqual((0, 0, 0), self.motion(self.before, self.early))
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, self.early, beat=True)))
        self.root = self.q.cycle()
        self.original_wait = self.h.motion_wait()
        self.counts = self.h.status().inputs, self.h.status().moves
        event = next(e for e in self.h.events() if e.command.id == self.old.id)
        self.assertEqual((2, 0, 0, 0), (event.outcome, event.motion, event.dx, event.dy))
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            self.root.job_id, self.root.capture_id, self.root.prefix, self.h.now))
        self.pause = None
        if prepared:
            ready, self.pause = self.h.tick()
            self.assertEqual((1, 2), (ready, self.pause.kind))
            self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
        value = self.producer(self.early, left=375, sy=44, target=positive)
        self.assertIn(value.outcome, (1, 2) if positive else (0,))
        self.commit(value)
        self.late = deepcopy(self.early)
        self.late.signature = native.translated(self.before, 3).signature
        self.late.tiles[(-4, -1)] = 'gold'  # Newly exposed remote wall, never a walk cell.
        self.assertEqual((1, 0, -1), self.motion(self.before, self.late))
        self.assertEqual((0, 0, 0), self.motion(self.early, self.late),
            'the early FULL is not a direct stationary substitute for the old ACK source')

    def no_new_input(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))
        self.assertEqual(self.counts[0], self.h.status().inputs)
        self.assertEqual(0, self.h.status().restarts)

    def test_original_up_ack_late_unit_is_credited_once_and_starts_only_fresh_data(self):
        for partial_before, prepared in ((False,False),(False,True),(True,False),(True,True)):
            with self.subTest(partial_before=partial_before, prepared_pause=prepared):
                self.setUp()
                self.pending(prepared=prepared, partial_before=partial_before)
                self.assertEqual(1, self.observe(self.late))
                job = self.q.cycle()
                self.assertEqual((self.root.job_id+1, self.h.number, self.root.prefix, 1),
                    (job.job_id, job.capture_id, job.prefix, job.pending),
                    'later original-ACK unit needs a new DATA source, not SCREEN or old-source zero')
                self.assertEqual((self.counts[0], self.counts[1]+1),
                    (self.h.status().inputs, self.h.status().moves),
                    'late original-ACK unit contributes exactly one move and no synthesized input')
                event = next(e for e in self.h.events() if e.command.id == self.old.id)
                self.assertEqual((2, 1, 0, -1, self.h.number),
                    (event.outcome, event.motion, event.dx, event.dy, event.observed_capture_id))
                reference = next(r for r in native.NativeControllerTests.motion_references(self.h)
                    if r.command_id == self.old.id)
                self.assertEqual((self.h.number, 1, self.old.source_capture_id, 1, 0),
                    (reference.observed_capture_id, reference.primary_motion,
                     reference.selected_capture_id, reference.selected_motion, reference.fallback_attempted))
                wait = self.h.motion_wait()
                self.assertEqual((self.original_wait.deadline_ns, self.h.number, 1, 0),
                    (wait.deadline_ns, wait.last_capture_id, wait.last_motion, wait.active))
                self.assertEqual(self.old.ordinal, self.h.status().last_ordinal)
                self.immutable_parent(self.root)
                self.assertLessEqual(job.deadline_ns, self.root.continuation_deadline_ns)
                self.assertEqual(0, self.q.durable())
                self.no_new_input()
                prior = self.h.status().moves
                self.observe(self.late, advance=20_000_000)
                self.assertEqual(prior, self.h.status().moves, 'the same original ACK cannot be credited twice')
                self.assertEqual(job.job_id, self.q.cycle().job_id)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    self.old.id, max(self.h.now,self.old.not_before_ns), 1, 0, 1))

    def test_missing_original_unit_wrong_prefix_and_expired_bounds_never_add_credit(self):
        for fault in ('unknown', 'prefix', 'parent', 'visual'):
            with self.subTest(fault=fault):
                self.setUp()
                self.pending()
                if fault == 'unknown': self.late.signature = self.early.signature
                elif fault == 'parent': self.h.now = self.root.continuation_deadline_ns+1
                elif fault == 'visual': self.h.now = self.original_wait.deadline_ns+1
                prefix = self.h.prefix-1 if fault == 'prefix' else self.h.prefix
                self.observe(self.late, advance=1, prefix=prefix)
                self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))
                self.no_new_input()
                event = next(e for e in self.h.events() if e.command.id == self.old.id)
                self.assertEqual((0, 0, 0), (event.motion, event.dx, event.dy))

    def test_normal_positive_remains_latched_ahead_of_late_unit_refresh(self):
        self.pending(positive=True)
        self.assertEqual(1, self.q.cycle().candidate_latched)
        self.observe(self.late)
        self.assertEqual(1, self.q.cycle().candidate_latched)
        self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))
        self.no_new_input()

    def test_late_unit_new_normal_data_two_zeros_one_observation_then_real_negative_restart(self):
        self.pending(partial_before=True)
        self.observe(self.late)
        source = self.q.cycle()
        self.assertEqual((self.root.job_id+1, 1), (source.job_id, source.pending))
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            source.job_id, source.capture_id, source.prefix, self.h.now))
        self.commit(self.producer(self.late, left=375, sy=44))
        self.no_new_input()
        self.observe(self.late, advance=20_000_000)
        self.no_new_input()
        first = self.h.number
        self.observe(self.late, advance=20_000_000)
        second = self.h.number
        command = self.h.next_move(self.late)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreaterEqual(command.source_capture_id, second)
        self.assertGreater(second, first)
        self.assertGreater(command.ordinal, self.old.ordinal)
        self.h.ack(command)
        latest = native.translated(self.late, 3)
        self.h.observed_result(command, latest)
        self.assertEqual(self.counts[1]+2, self.h.status().moves,
            'original ACK and separate one-use observation are each credited once')
        result = self.producer(latest, left=375, sy=80)
        self.assertEqual((3, 2), (result.outcome, result.coverage))
        self.commit(result)
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))


if __name__ == '__main__':
    unittest.main()
