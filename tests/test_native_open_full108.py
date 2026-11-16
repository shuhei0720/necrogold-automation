"""One observed entry step directly after an acknowledged opening.

TEST107/7186 opened LEFT but never entered. Original157/158 were independently
strict-zero and their Ring result was UNKNOWN/incomplete, not a negative.
These public-C fixtures use procedural texture/clocks and a three-offer
footprint; later movement and candidate responses are not missing phone frames.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_fade100 as opened
from tests import test_native_full_framing101 as full


class NativeOpenFull108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            frozen = os.environ.get('NECRO_TEST108_CONTROLLER_CORE')
            if frozen:
                native.CORE = Path(frozen)
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.p = opened.NativeOpenedFade100Tests(methodName='runTest')
        self.p.lib = self.lib
        self.addCleanup(self.p.doCleanups)

    @staticmethod
    def result(value, direction=1):
        left, sy = (267, 189) if direction == 1 else (447, 81)
        value.row_count = 1
        value.selected_row = 0
        value.partial_count = 2
        value.coverage = 1
        value.certificate.layout_version = 1
        value.certificate.policy_version = value.certificate.board_mode = 10
        value.certificate.failure_flags = 128
        value.certificate.scene_state = value.certificate.scene_goods = 2
        value.certificate.row[:] = (left, sy)
        row = value.rows[0]
        row.left, row.sy, row.word_slot = left, sy, -1
        for i, slot in enumerate(list(row.slots) + list(value.partial)[:2]):
            slot.cx = left + 36*i if i < 3 else left-36 + 144*(i-3)
            slot.sy, slot.slot = sy, i if i < 3 else 0
            slot.icon_score = slot.icon_upper_bound = .1

    @staticmethod
    def rotate(direction, point):
        x, y = point
        return (x, y) if direction == 1 else (-x, -y)

    def pending(self, direction=1, fault=None, mutate=None):
        h = self.p.harness()
        self.h = self.q.h = h
        tiles = {(x, y): 'floor' for x in range(-6, 1) for y in range(-2, 3)}
        tiles.update({(-1, 0): 'door', (-1, -1): 'gold', (-1, 1): 'gold',
                      (-7, -2): 'gold', (-7, -1): 'gold', (-7, 0): 'gold',
                      (-7, 1): 'gold', (-7, 2): 'gold',
                      (-8, -2): 'stone', (5, 2): 'stone', (8, 3): 'stone'})
        dx, dy = native.DIRS[direction]
        initial = {tuple(a+b for a, b in zip(self.rotate(direction, p), (dx, dy))): kind
                   for p, kind in tiles.items()}
        initial[(0, 0)] = 'floor'
        terrain = native.textured(initial)
        h.fit(terrain)
        first = h.next_move(terrain)
        self.assertEqual(direction, first.direction)
        h.ack(first)
        terrain = native.translated(terrain, direction)
        h.observed_result(first, terrain)
        opening = h.next_move(terrain)
        self.assertEqual(direction, opening.direction)
        h.ack(opening)
        source = deepcopy(terrain)
        source.tiles[(dx, dy)] = 'floor'
        source.goods = 'visible'
        source.protected.clear()
        items = [(-5, 1), (-4, 1), (-3, 1)] if direction == 1 else [(0, -2), (1, -2), (2, -2)]
        for x, y in items:
            source.tiles[(x, y)] = 'item'
            source.protected.update((x+a, y+b) for a, b in ((0, 0), *native.DIRS.values()))
        if fault == 'missing_bracket':
            source.tiles.pop(self.rotate(direction, (-1, -1)), None)
        elif fault == 'unknown_next':
            source.tiles.pop((dx, dy), None)
        elif fault == 'blocked_next':
            source.tiles[(dx, dy)] = 'stone'
        elif fault == 'protected_next':
            source.protected.add((dx, dy))
        elif fault == 'remote_protection':
            source.protected.add((8, -4))
        elif fault == 'no_open':
            # Keep the sent input known ACK but remove its positive opening
            # evidence. An unchanged closed gate must never mint entry credit.
            source.tiles[(dx, dy)] = 'door'
        h.observed_result(opening, source)
        if not fault:
            event = h.events()[-1]
            self.assertEqual((2, 3, 0, 0),
                (event.outcome, event.motion, event.dx, event.dy),
                'the source is the actual acknowledged opening, with no entry MOVE yet')
        moves = h.status().moves
        before = self.q.cycle()
        if fault and (h.status().reason or h.status().input_state):
            return source, opening, before, moves
        def build(value):
            self.result(value, direction)
            if mutate:
                mutate(value)
        if before.pending:
            self.q.assess(0, 1, build)
        elif not fault:
            self.fail('a valid opened FULL source must produce a normal classifier job')
        return source, opening, before, moves

    def admitted(self, **kwargs):
        source, opening, before, moves = self.pending(**kwargs)
        state = self.q.cycle()
        self.assertEqual((3, 0, 1, 0, 0), (state.state, state.partial, state.full_seen,
            state.completed_shops, state.candidate_latched),
            'a direct opening with FULL UNKNOWN must admit only the existing bounded observation wait')
        self.assertEqual(before.continuation_deadline_ns, state.continuation_deadline_ns)
        self.assertEqual(0, self.h.tick()[0], 'classification alone is not another input authority')
        return source, opening, state, moves

    def ticket(self, **kwargs):
        source, opening, state, moves = self.admitted(**kwargs)
        self.h.now += 10_000_000
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, source, beat=True)))
        command = self.h.next_move(source)
        self.assertEqual((4, opening.direction), (command.kind, command.direction))
        self.assertGreater(command.id, opening.id)
        self.assertGreater(command.source_capture_id, state.capture_id)
        self.assertLessEqual(self.h.motion_wait().deadline_ns, state.continuation_deadline_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id,
            self.h.now, 1, 0, 1), 'the old opening input is not replayed')
        return source, opening, state, moves, command

    def moved(self):
        source, opening, state, moves, command = self.ticket()
        self.h.ack(command)
        self.assertEqual((moves, state.job_id, 0), (self.h.status().moves,
            self.q.cycle().job_id, self.q.cycle().pending))
        latest = native.translated(source, command.direction)
        latest.goods = 'visible'
        self.h.observed_result(command, latest)
        self.assertEqual((moves+1, state.job_id+1, 1), (self.h.status().moves,
            self.q.cycle().job_id, self.q.cycle().pending))
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, state.continuation_deadline_ns)
        return latest, opening, state, moves, command

    def test_direct_opening_full_unknown_waits_for_independent_zero_then_enters_once(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.ticket(direction=direction)

    def test_new_candidate_after_actual_entry_is_held_without_restarting(self):
        _, opening, old, moves, command = self.moved()
        self.q.assess(1, 1)
        self.assertEqual((1, 1, 1), (self.q.cycle().outcome,
            self.q.cycle().candidate_latched, self.q.cycle().completed_shops))
        self.assertEqual(moves+1, self.h.status().moves)
        self.assertNotEqual(3, self.h.tick()[1].kind)
        self.assertGreater(command.id, opening.id)
        stale = cycle.Result(abi=1, size=C.sizeof(cycle.Result), selected_row=-1,
            selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now)
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
            old.job_id, old.capture_id, old.prefix, self.h.now, C.byref(stale)))

    def test_a_second_unknown_does_not_restore_the_one_step_credit(self):
        self.moved()
        self.q.assess(0, 1, self.result)
        self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_old_unknown_entry_history_does_not_borrow_the_direct_opening_geometry(self):
        legacy = full.NativeFullFraming101Tests(methodName='runTest')
        legacy.lib = self.lib
        legacy.setUp()
        self.addCleanup(legacy.doCleanups)
        source = full.NativeFullFraming101Tests.full_source()
        source.tiles[(0, -1)] = source.tiles[(0, 1)] = 'stone'
        source.tiles[(-1, -1)] = source.tiles[(-1, 1)] = 'gold'
        legacy.full_source = lambda: deepcopy(source)
        _, old, state, moves = legacy.pending()
        latest = legacy.h.events()[-1]
        self.assertEqual((old.id, 2, 0, 0, 0), (latest.command.id,
            latest.outcome, latest.motion, latest.dx, latest.dy),
            'this is the old entry ACK with visual UNKNOWN, not a direct opening response')
        self.assertEqual((7, 1), (state.state, state.completed_shops),
            'new next-door geometry belongs only to the bound direct-opening history')
        self.assertEqual(moves, legacy.h.status().moves)
        self.assertNotEqual(4, legacy.h.tick()[1].kind)

    def test_opening_bracket_positive_floor_and_exact_projection_are_required(self):
        for fault in ('no_open', 'missing_bracket', 'unknown_next', 'blocked_next',
                      'protected_next', 'remote_protection'):
            with self.subTest(fault=fault):
                self.pending(fault=fault)
                self.assertNotEqual(3, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_target_candidate_upper_bound_and_strong_word_precede_new_entry(self):
        faults = {
            'candidate': lambda v: setattr(v, 'outcome', 1),
            'target': lambda v: setattr(v, 'outcome', 2),
            'upper': lambda v: setattr(v.rows[0].slots[1], 'icon_upper_bound', .8),
            'word': lambda v: (setattr(v.rows[0].slots[1], 'word_present', 1),
                setattr(v.rows[0].slots[1], 'word_iou', .82),
                setattr(v.rows[0].slots[1], 'word_coverage', .90)),
            'hud': lambda v: setattr(v.partial[0], 'cx', 150),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.pending(mutate=mutate)
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_source_prefix_deadline_cancel_and_unknown_input_do_not_gain_new_authority(self):
        for fault in ('prefix', 'unstable', 'deadline', 'cancel', 'input_unknown'):
            with self.subTest(fault=fault):
                source, opening, state, moves = self.admitted()
                if fault == 'input_unknown':
                    self.h.now += 10_000_000
                    self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
                    command = self.h.next_move(source)
                    self.h.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                    self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now+1, -1)
                    self.h.now += 10_000_000
                    self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
                    self.assertEqual((4, moves), (self.h.status().input_state, self.h.status().moves))
                    self.assertNotEqual(4, self.h.tick()[1].kind)
                    continue
                self.h.now = state.continuation_deadline_ns+1 if fault == 'deadline' else self.h.now+10_000_000
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                self.h.observe_actual(self.h.scene(2, 2, source, beat=True),
                    **({'prefix': self.h.prefix+1} if fault == 'prefix' else
                       {'stable': 0} if fault == 'unstable' else {}))
                self.assertEqual(moves, self.h.status().moves)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opening.id, self.h.now, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
