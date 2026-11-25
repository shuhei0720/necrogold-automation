"""A delayed, original ACK unit owns one bounded current FULL exposure.

Procedural public lifecycle, not recovered private state or future iPhone
images. A normal UNKNOWN has no negative authority. New remote GOLD is DATA
only; a later input still needs the unchanged stationary proof and beat fit.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_entered112 as entered
from tests import test_native_full_framing101 as full
from tests import test_native_current_view114 as current_view
from tests import test_native_irregular110 as irregular


class NativeEnteredCurrent119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO119_ENTERED_CORE', str(previous)))
            entered.NativeEntered112Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = entered.NativeEntered112Tests.lib
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        entered.NativeEntered112Tests.tearDownClass()

    def setUp(self):
        self.fresh()

    def fresh(self, *, yield_enabled=False):
        self.e = entered.NativeEntered112Tests('runTest')
        self.e.lib = self.lib
        self.e.setUp()
        self.addCleanup(self.e.doCleanups)
        self.f = self.e.f
        if yield_enabled:
            self.f.p = current_view.current_view_fixture(self.lib)
            self.addCleanup(self.f.p.doCleanups)

    def pending(self, *, assess=True, mutate=None):
        h, _, _, _ = self.f.p.armed(reserve=False)
        self.h = self.f.h = self.f.q.h = h
        self.q = self.f.q
        late = full.NativeFullFraming101Tests.full_source()
        late.tiles[(-1, -2)] = 'floor'
        late.tiles[(1, 0)] = 'floor'
        late.tiles[(-6, -5)] = 'dirt'
        late.tiles[(7, 3)] = 'dirt'
        before = native.translated(late, 2)
        before.tiles = {point: kind for point, kind in before.tiles.items() if kind != 'item'}
        before.tiles[(0, 0)] = 'floor'
        before = native.textured(before.tiles)
        before.goods = 'unknown'
        h.now += 10_000_000
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, before, beat=True)))
        old = h.next_move(before)
        self.assertEqual(1, old.direction)
        late.signature = native.translated(before, 1).signature
        early = deepcopy(late)
        early.signature = bytes([80])*23296
        self.assertEqual((0, 0, 0), h.motion(before, early, 1))
        self.assertEqual((1, -1, 0), h.motion(before, late, 1))
        self.assertEqual(early.protected, late.protected)
        self.assertEqual(early.tiles, late.tiles,
                         'this separate entry path reveals no protected floor cell')
        h.ack(old)
        h.now = max(h.now+2, old.target_ns+100_000_000)
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, early, beat=True)))
        self.assertEqual((0, 0), (h.status().input_state, h.events()[-1].motion))
        self.before, self.early, self.late, self.old = before, early, late, old
        self.moves, self.inputs = h.status().moves, h.status().inputs
        self.visual = h.motion_wait().deadline_ns
        if assess:
            self.q.assess(0, 1, lambda value: self.unknown(value, mutate))
        self.original = self.q.cycle()
        return self.original

    @staticmethod
    def unknown(value, mutate=None):
        full.NativeFullFraming101Tests.result(value)
        if mutate:
            mutate(value)

    def frame(self, terrain=None, *, advance=70_000_000, **kwargs):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2,
            self.late if terrain is None else terrain, beat=True), **kwargs)

    def refreshed(self):
        original = self.pending()
        self.assertEqual(3, original.state)
        self.frame()
        current = self.q.cycle()
        self.assertEqual((self.moves+1, self.inputs, original.job_id+1, 1),
            (self.h.status().moves, self.h.status().inputs, current.job_id, current.pending),
            'the original known ACK unit must bind independent current DATA without another input')
        self.assertEqual((self.h.number, self.old.id), (current.capture_id, current.prefix))
        self.assertEqual(original.hold_started_ns, current.hold_started_ns)
        self.assertLessEqual(current.continuation_deadline_ns, original.continuation_deadline_ns)
        self.assertLessEqual(current.deadline_ns, current.capture_start_ns+150_000_000)
        event = next(value for value in self.h.events() if value.command.id == self.old.id)
        self.assertEqual((2, 1, -1, 0, current.capture_id),
            (event.outcome, event.motion, event.dx, event.dy, event.observed_capture_id))
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, self.old.id,
            self.h.now, 1, 0, 1))
        return original, current

    def queued_wall(self):
        original, current = self.refreshed()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            current.job_id, current.capture_id, current.prefix, self.h.now))
        wall = deepcopy(self.late)
        wall.tiles[(-6, -5)] = 'gold'
        self.assertEqual((2, 0, 0), self.h.motion(self.late, wall, 1))
        self.frame(wall, advance=10_000_000)
        queued = self.h.number
        held = self.q.cycle()
        self.assertEqual((current.job_id, current.capture_id, queued),
            (held.job_id, held.capture_id, held.queued_capture_id),
            'the first new wall remains a source lease while its original worker drains')
        return original, current, wall, queued

    def commit(self, current, *, outcome=0, mutate=None, expected=1):
        result = cycle.Result(abi=1, size=C.sizeof(cycle.Result), outcome=outcome,
            coverage=1, selected_row=-1, selected_partial=-1,
            started_ns=self.h.now-1, finished_ns=self.h.now)
        self.unknown(result, mutate)
        self.assertEqual(expected, self.lib.ng2_controller_cycle_assess(self.h.engine,
            current.job_id, current.capture_id, current.prefix, self.h.now, C.byref(result)))
        return result

    def test_original_unit_without_revealed_halo_binds_current_data_once(self):
        for yield_enabled in (False, True):
            with self.subTest(restart_yield=yield_enabled):
                self.fresh(yield_enabled=yield_enabled)
                original, current = self.refreshed()
                self.frame(advance=10_000_000)
                self.assertEqual((self.moves+1, self.inputs, current.job_id, current.capture_id),
                    (self.h.status().moves, self.h.status().inputs,
                     self.q.cycle().job_id, self.q.cycle().capture_id))
                self.assertEqual(original.hold_started_ns, self.q.cycle().hold_started_ns)
                self.assertEqual(0, self.q.cycle().queued_capture_id,
                                 'an unchanged repeated image must not spend another DATA job')

    def test_pending_remote_wall_drains_then_owns_data_and_one_fresh_observation(self):
        self.fresh(yield_enabled=True)
        original, current, wall, queued = self.queued_wall()
        self.commit(current)
        rebound = self.q.cycle()
        self.assertEqual((current.job_id+1, queued, 1),
            (rebound.job_id, rebound.capture_id, rebound.pending))
        self.assertEqual(original.hold_started_ns, rebound.hold_started_ns)
        self.assertLessEqual(rebound.continuation_deadline_ns, original.continuation_deadline_ns)
        self.q.assess(0, 1, self.unknown)
        self.assertEqual((3, 0, 0), (self.q.cycle().state,
            self.q.cycle().pending, self.q.cycle().completed_shops))
        self.frame(wall, advance=10_000_000)
        command = self.h.next_move(wall)
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.id, self.old.id)
        self.assertGreater(command.ordinal, self.old.ordinal)
        self.assertGreater(command.source_capture_id, queued)
        self.assertGreaterEqual(command.not_before_ns-self.h.now, 50_000_000)
        self.h.ack(command)
        self.h.observed_result(command, native.translated(wall, 1))
        self.q.assess(0, 1, self.unknown)
        self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.frame(wall, advance=10_000_000)
        self.assertNotEqual(4, self.h.tick()[1].kind,
            'a consumed observation cannot rearm this token from another image')
        for outcome in ('not_sent', 'unknown_input'):
            with self.subTest(outcome=outcome):
                self.fresh(yield_enabled=True)
                _, current, wall, _ = self.queued_wall()
                self.commit(current)
                self.q.assess(0, 1, self.unknown)
                self.frame(wall, advance=10_000_000)
                command = self.h.next_move(wall)
                self.h.now = command.not_before_ns
                if outcome == 'not_sent':
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 0, 0, 1))
                else:
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                    self.h.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        command.id, self.h.now, -1))
                self.frame(wall, advance=10_000_000)
                self.assertEqual(self.moves+1, self.h.status().moves)
                self.assertNotEqual(4, self.h.tick()[1].kind,
                    'publication consumes the one observation even when delivery is not confirmed')
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))

    def test_pending_candidate_and_target_win_before_queued_source(self):
        for outcome in (1, 2):
            with self.subTest(outcome=outcome):
                self.fresh()
                _, current, _, _ = self.queued_wall()
                self.commit(current, outcome=outcome)
                state = self.q.cycle()
                self.assertEqual((1, 7, current.job_id, current.capture_id, 0),
                    (state.candidate_latched, state.state, state.job_id, state.capture_id, state.pending))
                self.assertEqual((self.moves+1, self.inputs),
                    (self.h.status().moves, self.h.status().inputs))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_visual_deadline_is_original_and_inclusive(self):
        for delta in (-1, 0, 1):
            with self.subTest(delta=delta):
                self.fresh()
                old = self.pending()
                self.h.now = self.visual+delta
                self.frame(advance=0)
                self.assertEqual(self.moves+(delta <= 0), self.h.status().moves)
                self.assertEqual(old.job_id+(delta <= 0), self.q.cycle().job_id)
                self.assertLessEqual(self.q.cycle().continuation_deadline_ns,
                    old.continuation_deadline_ns)
                self.assertEqual(self.inputs, self.h.status().inputs)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_no_unit_floor_or_identity_shortcut(self):
        for fault in ('next_dirt', 'origin_dirt', 'old_origin_dirt', 'item',
                      'protection', 'gold_loss', 'nonzero', 'prefix',
                      'unstable', 'cancel', 'parent_expired', 'worker'):
            with self.subTest(fault=fault):
                self.fresh()
                old = self.pending(assess=fault != 'worker')
                latest = deepcopy(self.late)
                kwargs = {}
                if fault == 'next_dirt': latest.tiles[(-1, 0)] = 'dirt'
                elif fault == 'origin_dirt': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'old_origin_dirt': latest.tiles[(1, 0)] = 'dirt'
                elif fault == 'item': latest.tiles[(-3, -2)] = 'floor'
                elif fault == 'protection': latest.protected.add((7, 3))
                elif fault == 'gold_loss': latest.tiles[(-6, -3)] = 'dirt'
                elif fault == 'nonzero': latest.signature = native.translated(self.before, 1, amount=4).signature
                elif fault == 'prefix': kwargs['prefix'] = self.h.prefix+1
                elif fault == 'unstable': kwargs['stable'] = 0
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                elif fault == 'parent_expired': self.h.now = old.continuation_deadline_ns+1
                elif fault == 'worker':
                    self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        old.job_id, old.capture_id, old.prefix, self.h.now))
                self.frame(latest, advance=0 if fault == 'parent_expired' else 70_000_000, **kwargs)
                self.assertEqual((self.moves, self.inputs, old.job_id),
                    (self.h.status().moves, self.h.status().inputs, self.q.cycle().job_id))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_new_wall_still_needs_direct_zero_floor_and_original_bound(self):
        for fault in ('next_dirt', 'old_origin_dirt', 'protection', 'gold_loss',
                      'unknown', 'unit', 'prefix', 'parent_expired'):
            with self.subTest(fault=fault):
                self.fresh()
                _, current = self.refreshed()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    current.job_id, current.capture_id, current.prefix, self.h.now))
                wall = deepcopy(self.late)
                wall.tiles[(-6, -5)] = 'gold'
                kwargs = {}
                if fault == 'next_dirt': wall.tiles[(-1, 0)] = 'dirt'
                elif fault == 'old_origin_dirt': wall.tiles[(1, 0)] = 'dirt'
                elif fault == 'protection': wall.protected.add((7, 3))
                elif fault == 'gold_loss': wall.tiles[(-6, -3)] = 'floor'
                elif fault == 'unknown': wall.signature = bytes([80])*23296
                elif fault == 'unit': wall.signature = native.translated(self.late, 1).signature
                elif fault == 'prefix': kwargs['prefix'] = self.h.prefix+1
                else: self.h.now = current.continuation_deadline_ns+1
                self.frame(wall, advance=0 if fault == 'parent_expired' else 10_000_000, **kwargs)
                # Expiry has already ended this job; its later normal worker
                # return has no live adoption authority and is refused.
                self.commit(current, expected=0 if fault == 'parent_expired' else 1)
                self.assertEqual(current.job_id, self.q.cycle().job_id)
                self.assertFalse(self.q.cycle().pending)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_data_two_budget_cannot_be_replenished_by_new_remote_material(self):
        _, current, wall, _ = self.queued_wall()
        self.commit(current)
        second = self.q.cycle()
        self.assertEqual(current.job_id+1, second.job_id)
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            second.job_id, second.capture_id, second.prefix, self.h.now))
        third = deepcopy(wall)
        third.tiles[(7, 3)] = 'stone'
        self.frame(third, advance=10_000_000)
        self.commit(second)
        self.assertEqual((second.job_id, 0, 7),
            (self.q.cycle().job_id, self.q.cycle().pending, self.q.cycle().state))
        self.assertNotEqual(4, self.h.tick()[1].kind)


if __name__ == '__main__':
    unittest.main()
