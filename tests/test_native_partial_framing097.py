"""TEST097 one observed UP framing input, public C with procedural clocks.

Source167 in received e503 has protected merchandise at the top two rows but
no Ring slot anchors. The empty assessment remains UNKNOWN and incomplete.
These modeled callbacks prove bounded input semantics, not later device frames.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_entry097 as entry


class NativePartialFraming097Tests(unittest.TestCase):
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
    def envelope(items=None):
        items = {(x, y) for x in range(-3, 2) for y in (-5, -4)} if items is None else set(items)
        protected = set(items)
        for x, y in items:
            protected.update((x + dx, y + dy) for dx, dy in native.DIRS.values())
        protected = {point for point in protected if -11 <= point[0] <= 11 and -5 <= point[1] <= 4}
        return {point: 'item' for point in items}, protected

    def pending(self, *, items=None, extra=None, protected_extra=(), remove_protected=(),
                direction=3, opened=True, opening_direction=None, outcome=0,
                mutate=None):
        cells, protected = self.envelope(items)
        cells.update(extra or {})
        protected.update(protected_extra)
        protected.difference_update(remove_protected)
        terrain, opening = self.p.pending(direction=direction, opened=opened,
            opening_direction=opening_direction, extra=cells, protected=protected,
            outcome=outcome, safe_slots=False, mutate_assessment=mutate)
        return terrain, opening

    def held(self):
        self.assertNotEqual(0, self.q.cycle().state)
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(0, self.h.status().restarts)

    def admitted(self):
        state = self.q.cycle()
        self.assertEqual((3, 0, 0, 1, 0),
                         (state.state, state.outcome, state.status, state.coverage, state.completed_shops),
                         'empty UNKNOWN needs an explicit one-input framing credit, never a completed shop')
        self.assertEqual((0, 0, 0, 0), (state.pending, state.full_seen,
                                      state.candidate_latched, self.h.status().goods))
        self.assertEqual(0, self.h.tick()[0], 'admission alone cannot dispatch or pause')
        return state

    def test_empty_unknown_keeps_result_and_waits_for_independent_up_framing(self):
        terrain, _ = self.pending()
        original = self.admitted()
        self.assertGreater(original.continuation_deadline_ns, original.deadline_ns,
                           'input horizon is separate from the classifier deadline')
        self.assertEqual(1, self.p.observe(terrain))
        current = self.q.cycle()
        self.assertEqual((0, 0, 0, 1, 0), (current.state, current.outcome, current.status,
                                         current.coverage, current.completed_shops))
        self.assertEqual((original.job_id, original.continuation_deadline_ns),
                         (current.job_id, current.continuation_deadline_ns))
        command = self.h.next_move(terrain)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.id, self.h.prefix)
        self.assertGreaterEqual(command.not_before_ns - self.h.now, 50_000_000)

    def test_framing_requires_actual_up_opening_and_correct_result_domain(self):
        for fault in ('no_open', 'wrong_direction', 'candidate', 'target', 'deadline',
                      'kernel', 'coverage', 'row', 'partial', 'safe'):
            with self.subTest(fault=fault):
                self.setUp()
                def mutate(value):
                    if fault == 'deadline': value.status = 2
                    elif fault == 'kernel': value.status = 5
                    elif fault == 'coverage': value.coverage = 0
                    elif fault == 'row': value.row_count = 1
                    elif fault == 'partial': value.partial_count = 1
                    elif fault == 'safe': value.partial_safe_no_positive = 1
                self.pending(opened=fault != 'no_open',
                             direction=1 if fault == 'wrong_direction' else 3,
                             outcome={'candidate': 1, 'target': 2}.get(fault, 0), mutate=mutate)
                self.held()

    def test_top_item_and_protection_are_positive_complete_footprint_witnesses(self):
        for fault in ('no_top_item', 'no_item', 'unprotected_item', 'low_item', 'low_protection'):
            with self.subTest(fault=fault):
                self.setUp()
                items = {(x, -4) for x in range(-3, 2)} if fault == 'no_top_item' else set() if fault == 'no_item' else None
                extra = {(-3, -3): 'item'} if fault == 'low_item' else None
                self.pending(items=items, extra=extra,
                             remove_protected={(-3, -5)} if fault == 'unprotected_item' else (),
                             protected_extra={(-3, -2)} if fault == 'low_protection' else ())
                self.held()

    def test_hypothetical_fringe_item_bounds_and_new_hud_occlusion_are_conservative(self):
        # Protection may originate from an ITEM just outside the finite grid.
        # Its own and four neighboring possible centers need the full bounds.
        for point in ((-6, -5), (4, -5)):
            with self.subTest(point=point):
                self.setUp()
                self.pending(protected_extra={point})
                self.held()

    def test_independent_frame_needs_original_item_protection_choice_and_zero(self):
        for fault in ('item', 'protection', 'choice', 'motion'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending()
                self.admitted()
                changed = deepcopy(terrain)
                if fault == 'item': changed.tiles[(-3, -5)] = 'dirt'
                elif fault == 'protection': changed.protected.remove((-3, -5))
                elif fault == 'choice': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'motion': changed.signature = native.translated(terrain, 3).signature
                self.p.observe(changed)
                self.held()

    def test_same_or_pre_release_frame_wrong_prefix_and_unstable_cannot_release_credit(self):
        for fault in ('same_id', 'pre_release', 'prefix', 'unstable'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending()
                original = self.admitted()
                h = self.h
                h.now += 10_000_000
                kwargs = {'number': original.capture_id} if fault == 'same_id' else (
                    {'start': original.release_after_ns - 1} if fault == 'pre_release' else (
                    {'prefix': h.prefix + 1} if fault == 'prefix' else {'stable': 0}))
                h.observe(h.scene(2, 2, terrain, beat=True), **kwargs)
                self.assertEqual(3, self.q.cycle().state)
                self.assertEqual(0, h.tick()[0])
                self.assertEqual((2, 1, 0), (h.status().inputs, h.status().moves, h.status().restarts))

    def test_original_horizon_cancel_and_foreground_guards_never_renew_framing(self):
        for fault in ('deadline', 'cancel', 'foreground', 'locked', 'owner'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending()
                original = self.admitted()
                if fault == 'deadline':
                    self.h.now = original.continuation_deadline_ns + 1
                    self.p.observe(terrain)
                    self.held()
                elif fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                    self.held()
                else:
                    self.p.observe(terrain)
                    command = self.h.next_move(terrain)
                    self.h.now = command.not_before_ns
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                        self.h.now, int(fault != 'foreground'), int(fault == 'locked'), int(fault != 'owner')))
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                                           self.h.status().restarts))

    def test_exactly_one_move_requires_new_assessment_and_cannot_reuse_old_ticket(self):
        terrain, opening = self.pending()
        original = self.admitted()
        self.p.observe(terrain)
        command = self.h.next_move(terrain)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id,
                                                        command.not_before_ns, 1, 0, 1))
        self.h.ack(command)
        self.assertEqual((3, 1), (self.h.status().inputs, self.h.status().moves))
        after = native.translated(terrain, 3)
        self.h.observed_result(command, after)
        current = self.q.cycle()
        self.assertEqual((original.job_id + 1, 1, 0),
                         (current.job_id, current.pending, current.completed_shops))
        self.assertEqual(0, self.h.tick()[0], 'the old empty result never grants a second MOVE')
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                                                        self.h.now, 1, 0, 1))

    def test_new_full_observation_before_framing_move_gets_new_normal_job(self):
        for reserved in (False, True):
            with self.subTest(reserved=reserved):
                self.setUp()
                terrain, _ = self.pending()
                original = self.admitted()
                command = None
                if reserved:
                    self.p.observe(terrain)
                    command = self.h.next_move(terrain)
                    frozen = bytes(command)
                full = deepcopy(terrain); full.goods = 'visible'
                self.assertEqual(1, self.p.observe(full))
                current = self.q.cycle()
                self.assertEqual((original.job_id + 1, 1, 1, 1, 0, 0, 0),
                    (current.job_id, current.state, current.pending, current.full_seen,
                     current.partial, current.completed_shops, current.status),
                    'a newly observed FULL scene must be classified instead of retaining the old empty job')
                self.assertGreater(current.capture_id, original.capture_id)
                self.assertGreater(current.deadline_ns, original.deadline_ns)
                self.assertEqual((2, 1, 0, 0, 1),
                    (self.h.status().inputs, self.h.status().moves, self.h.status().restarts,
                     self.h.status().input_state, self.h.status().goods))
                if command:
                    self.assertEqual(frozen, bytes(self.h.events()[-1].command))
                    self.assertEqual((3, 0), (self.h.events()[-1].outcome, self.h.events()[-1].begin_ns))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, command.not_before_ns, 1, 0, 1))
                before = bytes(self.h.status()), bytes(self.q.cycle())
                self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    original.job_id, original.capture_id, original.prefix, self.h.now + 2))
                stale = entry.cycle094.Result(abi=1, size=C.sizeof(entry.cycle094.Result),
                    selected_row=-1, selected_partial=-1, started_ns=self.h.now,
                    finished_ns=self.h.now + 1)
                self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    original.job_id, original.capture_id, original.prefix,
                    self.h.now + 2, C.byref(stale)))
                self.assertEqual(before, (bytes(self.h.status()), bytes(self.q.cycle())))
        for state in (0, 1):
            with self.subTest(non_floor_state=state):
                self.setUp()
                terrain, _ = self.pending()
                original = self.admitted()
                full = deepcopy(terrain); full.goods = 'visible'
                self.h.now += 10_000_000
                self.h.observe(self.h.scene(state, 2, full, beat=True))
                current = self.q.cycle()
                self.assertEqual((original.job_id, original.capture_id, 0),
                    (current.job_id, current.capture_id, current.pending),
                    'non-FLOOR goods may protect a hold, never bind a new classification source')
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                                           self.h.status().restarts))


if __name__ == '__main__':
    unittest.main()
