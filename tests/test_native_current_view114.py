"""TEST114 independent current FULL view through public Controller APIs.

All clocks, Scenes, raw Ring pixels and later responses are procedural. The
normal Ring producer is real; these are not unrecorded iPhone frames. Old
source invalidation never becomes a movement proof for the new source.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_goods113 as goods
from tests import test_native_irregular110 as irregular
from tests import test_native_opened_fade100 as opened
from tests.test_native_motion075 import Motion


def current_view_fixture(lib):
    # Keep the shared historical mechanics untouched. Only TEST114's local
    # constructor opts into the Runtime mode with real return-drain fences.
    class CurrentViewOpenedFixture(opened.NativeOpenedFade100Tests):
        def harness(self, cycle_profile=True):
            h = super().harness(cycle_profile)
            self.assertTrue(cycle_profile)
            self.assertEqual(1, self.lib.ng2_controller_enable_irregular(h.engine))
            if self.yield_enabled:
                self.assertEqual(1, self.lib.ng2_controller_enable_restart_yield(h.engine))
            companion = irregular.NativeIrregular110Tests(methodName='runTest')
            companion.lib, companion.h, companion.has_irregular = self.lib, h, True
            h.observe = lambda scene, **kwargs: companion.observe(scene, irregular.none(), **kwargs)
            h.observe_actual = h.observe
            self.assertEqual(1, h.observe_actual(h.scene(state=1)))
            ready, resume = h.tick()
            self.assertEqual((1, 1), (ready, resume.kind))
            h.ack(resume)
            h.now += 210_000_000
            return h

    value = CurrentViewOpenedFixture(methodName='runTest')
    value.lib, value.yield_enabled = lib, True
    return value


class NativeCurrentView114Tests(goods.Goods113Base):
    @classmethod
    def setUpClass(cls):
        previous = os.environ.get('NECRO113_GOODS_CORE')
        selected = os.environ.get('NECRO114_CURRENT_CORE')
        try:
            if selected:
                os.environ['NECRO113_GOODS_CORE'] = selected
            super().setUpClass()
            cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
            cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
            cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
                C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64] * 4 + [C.c_int32, C.c_uint64]
            cls.lib.ng2_controller_observe_irregular_at.restype = None
        finally:
            if previous is None:
                os.environ.pop('NECRO113_GOODS_CORE', None)
            else:
                os.environ['NECRO113_GOODS_CORE'] = previous

    def setUp(self):
        self.p = current_view_fixture(self.lib)
        self.addCleanup(self.p.doCleanups)

    def frame(self, terrain, *, beat=True, advance=20_000_000, age=2,
              prefix=None, stable=1):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, terrain, beat=beat),
            start=self.h.now-age, end=self.h.now,
            prefix=self.h.prefix if prefix is None else prefix, stable=stable)

    def motion(self, first, second):
        a = self.h.scene(2, 2, first)
        b = self.h.scene(2, 2, second)
        value = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), 3, C.byref(value)))
        return value.kind, value.dx, value.dy

    def old_pending(self, *, prepared=False, opening=True, current_fault=None,
                    yield_enabled=True):
        self.p.yield_enabled = yield_enabled
        self.h, terrain, old, _ = self.p.armed(direction=3, actual_opening=opening)
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib, self.q.h = self.lib, self.h
        self.h.ack(old)
        self.h.now = max(self.h.now+2, old.target_ns+100_000_000)
        self.old_source = goods.NativeGoodsUpView113Tests.source()
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, self.old_source, beat=True)))
        self.old = old
        self.root = self.q.cycle()
        self.counts = self.h.status().inputs, self.h.status().moves
        self.old_result = self.producer(self.old_source, left=375, sy=44)
        self.assertEqual((0, 1, 1), (self.old_result.outcome,
            self.old_result.coverage, self.old_result.row_count), 'real normal producer is incomplete')
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            self.root.job_id, self.root.capture_id, self.root.prefix, self.h.now))
        self.pause = None
        if prepared:
            ready, self.pause = self.h.tick()
            self.assertEqual((1, 2), (ready, self.pause.kind))
            self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
        self.current = deepcopy(self.old_source)
        self.current.tiles[(-4, -1)] = 'gold'
        rng = random.Random(114100)
        self.current.signature = bytes(rng.randrange(20, 240) for _ in self.current.signature)
        if current_fault == 'up_unknown': self.current.tiles.pop((0, -1))
        elif current_fault == 'up_protected': self.current.protected.add((0, -1))
        elif current_fault == 'extra_item':
            self.current.tiles[(7, 3)] = 'item'; self.current.protected.add((7, 3))
        self.assertEqual((0, 0, 0), self.motion(self.old_source, self.current),
                         'old source has no direct zero to current source')
        self.assertEqual(1, self.frame(self.current))
        self.current_id = self.h.number
        self.current_end = self.h.now
        self.assertEqual(self.root.job_id, self.q.cycle().job_id,
                         'inflight old worker never silently migrates its source')
        return self.current

    def queue_current(self, **kwargs):
        self.old_pending(**kwargs)
        self.commit(self.old_result)
        queued = self.q.cycle()
        self.assertEqual((self.root.job_id+1, self.current_id, self.root.prefix, 1, 0),
            (queued.job_id, queued.capture_id, queued.prefix, queued.pending, queued.worker_started_ns),
            'hard old FULL must queue one distinct immutable current DATA job, not stop or revive old UP')
        self.immutable_parent(self.root)
        self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual((0, 0, 0), (self.h.events()[-1].motion,
            self.h.events()[-1].dx, self.h.events()[-1].dy))
        return queued

    def current_result(self, *, target=False):
        value = self.producer(self.current, left=375, sy=44, target=target, unknown=not target)
        self.assertIn(value.outcome, (1, 2) if target else (0,))
        self.commit(value)
        return value

    def no_move_or_restart(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def assert_no_old_credit(self):
        old = next(e for e in self.h.events() if e.command.id == self.old.id)
        self.assertEqual((2, 0, 0, 0), (old.outcome, old.motion, old.dx, old.dy))
        self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))

    def qualified_ticket(self):
        self.queue_current()
        self.current_result()
        self.no_move_or_restart()
        self.assertEqual(1, self.frame(self.current))
        self.first_proof = self.h.number
        self.no_move_or_restart()
        self.assertEqual(1, self.frame(self.current))
        self.second_proof = self.h.number
        command = self.h.next_move(self.current)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.source_capture_id, self.current_id)
        self.assertGreaterEqual(command.source_capture_id, self.second_proof)
        self.assertGreater(command.ordinal, self.old.ordinal,
                           'old UNKNOWN ordinal must not be reused or credited')
        self.assertLessEqual(command.target_ns+50_000_000, self.root.continuation_deadline_ns)
        self.assertLessEqual(command.deadline_ns+self.h.status().lead_ns+50_000_000,
                             self.root.continuation_deadline_ns)
        self.assert_no_old_credit()
        return command

    def test_current_normal_job_two_direct_proofs_new_fit_then_one_up_and_normal_restart(self):
        command = self.qualified_ticket()
        self.h.ack(command)
        self.assertEqual(self.counts[1], self.h.status().moves)
        latest = native.translated(self.current, 3)
        self.h.observed_result(command, latest)
        self.assertEqual(self.counts[1]+1, self.h.status().moves)
        old = next(e for e in self.h.events() if e.command.id == self.old.id)
        self.assertEqual((0, 0, 0), (old.motion, old.dx, old.dy))
        value = self.producer(latest, left=375, sy=80)
        self.assertEqual((3, 2), (value.outcome, value.coverage),
                         'post-UP absence must come from a real complete normal producer')
        self.commit(value)
        self.assertEqual(0, self.q.durable(), 'unpaused image is not durable PAUSE proof')
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))

    def test_profile_without_runtime_return_drain_fences_cannot_requalify_current_view(self):
        self.old_pending(yield_enabled=False)
        self.commit(self.old_result)
        after = self.q.cycle()
        self.assertEqual((self.root.job_id, self.root.capture_id),
            (after.job_id, after.capture_id),
            'yield-disabled Runtime mode cannot gain the independently queued current-view worker')
        self.no_move_or_restart()
        self.assert_no_old_credit()

    def test_one_direct_proof_and_old_fit_cannot_authorize_current_up(self):
        self.queue_current(); self.current_result()
        self.frame(self.current)
        self.no_move_or_restart()
        for _ in range(3):
            self.frame(self.current, beat=False)
            self.no_move_or_restart()
        self.assert_no_old_credit()

    def test_current_unknown_motion_or_changed_material_is_sticky_and_cannot_migrate(self):
        for fault in ('motion', 'gold', 'item', 'protection', 'material'):
            with self.subTest(fault=fault):
                self.setUp(); queued = self.queue_current(); self.current_result()
                self.frame(self.current)
                changed = deepcopy(self.current)
                if fault == 'motion': changed.signature = bytes([80])*len(changed.signature)
                elif fault == 'gold': changed.tiles[(-4, -1)] = 'floor'
                elif fault == 'item': changed.tiles[(-2, -3)] = 'floor'
                elif fault == 'protection': changed.protected.add((8, 3))
                else: changed.tiles[(8, 3)] = 'stone'
                self.frame(changed); self.no_move_or_restart()
                self.frame(self.current); self.frame(self.current)
                self.no_move_or_restart()
                self.assertEqual(queued.job_id, self.q.cycle().job_id,
                                 'invalid current epoch cannot migrate to another DATA anchor')
                self.assert_no_old_credit()

    def test_candidate_from_old_or_new_normal_pixels_has_priority_over_view(self):
        for where in ('old', 'current'):
            with self.subTest(where=where):
                self.setUp()
                if where == 'old':
                    self.old_pending()
                    value = self.producer(self.old_source, left=375, sy=44, target=True)
                    self.assertIn(value.outcome, (1, 2)); self.commit(value)
                    job = self.root.job_id
                else:
                    self.queue_current(); self.current_result(target=True)
                    job = self.root.job_id+1
                self.assertEqual(1, self.q.cycle().candidate_latched)
                self.frame(self.current); self.frame(self.current)
                self.no_move_or_restart()
                self.assertEqual(job, self.q.cycle().job_id)
                self.assert_no_old_credit()

    def test_only_exact_unbegun_pause_can_withdraw_before_current_bind(self):
        queued = self.queue_current(prepared=True)
        retired = next(e for e in self.h.events() if e.command.id == self.pause.id)
        self.assertEqual((3, 0), (retired.outcome, retired.begin_ns))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
            self.pause.id, max(self.h.now, self.pause.not_before_ns), 1, 0, 1))
        self.assertEqual(0, self.h.status().input_state)
        self.assertEqual(queued.capture_id, self.current_id)

    def test_missing_positive_current_floor_projection_and_expired_parent_do_not_rebind(self):
        for fault in ('up_unknown', 'up_protected', 'extra_item', 'parent'):
            with self.subTest(fault=fault):
                self.setUp(); self.old_pending(current_fault=None if fault=='parent' else fault)
                if fault == 'parent': self.h.now = self.root.continuation_deadline_ns+1
                self.commit(self.old_result)
                self.assertEqual(self.root.job_id, self.q.cycle().job_id)
                self.no_move_or_restart()
                self.assert_no_old_credit()

    def test_two_pairwise_zeros_do_not_bridge_the_immutable_current_anchor(self):
        self.queue_current(); self.current_result()
        rng = random.Random(114440)
        other = bytes(rng.randrange(20, 100) for _ in self.current.signature)
        middle, later = deepcopy(self.current), deepcopy(self.current)
        middle.signature = bytes(round(a*.7+b*.3) for a, b in zip(self.current.signature, other))
        later.signature = bytes(round(a*.5+b*.5) for a, b in zip(self.current.signature, other))
        self.assertEqual((2, 0, 0), self.motion(self.current, middle))
        self.assertEqual((2, 0, 0), self.motion(middle, later))
        self.assertEqual((0, 0, 0), self.motion(self.current, later))
        job = self.q.cycle().job_id
        self.frame(middle); self.no_move_or_restart()
        self.frame(later); self.no_move_or_restart()
        self.frame(self.current); self.frame(self.current)
        self.assertEqual(job, self.q.cycle().job_id)
        self.no_move_or_restart(); self.assert_no_old_credit()

    def test_begun_acknowledged_or_unknown_pause_is_never_retired_for_current_data(self):
        for outcome in (None, 1, -1):
            with self.subTest(outcome=outcome):
                self.setUp(); self.old_pending(prepared=True)
                self.h.now = max(self.h.now, self.pause.not_before_ns)
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                    self.pause.id, self.h.now, 1, 0, 1))
                if outcome is not None:
                    self.h.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        self.pause.id, self.h.now, outcome))
                before = bytes(next(e for e in self.h.events() if e.command.id == self.pause.id))
                if outcome == -1:
                    # Unknown synth has already made the input terminal; the
                    # late worker callback must be rejected, not adopted.
                    self.old_result.started_ns = self.h.now
                    self.h.now += 10_000_000
                    self.old_result.finished_ns = self.h.now
                    self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
                        self.root.job_id, self.root.capture_id, self.root.prefix,
                        self.h.now, C.byref(self.old_result)))
                else:
                    self.commit(self.old_result)
                self.assertEqual(self.root.job_id, self.q.cycle().job_id)
                after = next(e for e in self.h.events() if e.command.id == self.pause.id)
                self.assertEqual(before, bytes(after), 'begun PAUSE ownership cannot be rewritten')
                self.no_move_or_restart()

    def test_current_geometry_and_own_normal_result_need_no_relabelled_old_history(self):
        self.queue_current(opening=False); self.current_result()
        self.frame(self.current); self.no_move_or_restart()
        self.frame(self.current)
        command = self.h.next_move(self.current)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.ordinal, self.old.ordinal)
        self.assertGreater(command.source_capture_id, self.current_id)
        self.assert_no_old_credit()

    def test_post_up_unknown_never_restores_current_epoch_or_single_view(self):
        command = self.qualified_ticket(); self.h.ack(command)
        latest = native.translated(self.current, 3)
        self.h.observed_result(command, latest)
        value = self.producer(latest, left=375, sy=80, unknown=True)
        self.assertEqual((0, 1), (value.outcome, value.coverage))
        self.commit(value)
        job = self.q.cycle().job_id
        for _ in range(4):
            self.frame(latest); self.no_move_or_restart()
        self.assertEqual(job, self.q.cycle().job_id)
        self.assertEqual((self.counts[0]+1, self.counts[1]+1),
                         (self.h.status().inputs, self.h.status().moves))

    def test_later_static_frame_after_reservation_preserves_the_frozen_current_ticket(self):
        command = self.qualified_ticket()
        frozen = bytes(command)
        self.frame(self.current)
        reserved = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((frozen, 0, 0), (bytes(reserved.command), reserved.begin_ns, reserved.outcome))
        self.h.now = max(self.h.now, command.not_before_ns)
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
            command.id, self.h.now, 1, 0, 1),
            'an independent later zero must preserve the already reserved current ticket')


if __name__ == '__main__':
    unittest.main()
