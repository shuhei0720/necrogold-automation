"""One local FULL/UNKNOWN observation MOVE through public Controller APIs.

The latest old MOVE is known-synth ACK with uncredited visual UNKNOWN, as in
received217. Procedural later Scenes prove state transitions, not phone arrival.
"""
import ctypes as C
from copy import deepcopy
import random
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_fade100 as opened
from tests import test_native_structural_cycle096 as structural


class NativeFullFraming101Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
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
    def full_source():
        tiles = {(x, y): 'floor' for x in range(-5, 0) for y in range(-4, 1)}
        for y in range(-5, 2): tiles[(-6, y)] = 'gold'
        for x in range(-6, 1): tiles[(x, 1)] = 'gold'
        tiles[(0, -1)] = 'gold'
        tiles[(0, 0)] = 'floor'
        items = {(-4, -2), (-3, -2), (-2, -2)}
        for point in items: tiles[point] = 'item'
        tiles.pop((-1, -2), None)  # The occluded cap stays UNKNOWN.
        value = native.textured(tiles)
        value.goods = 'visible'
        value.protected = set(items)
        for x, y in items:
            value.protected.update((x + dx, y + dy) for dx, dy in native.DIRS.values())
        rng = random.Random(101101)
        value.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
        return value

    @staticmethod
    def result(value):
        value.row_count = 1
        value.selected_row = 0
        value.partial_count = 2
        value.coverage = 1
        value.certificate.failure_flags = 258
        value.certificate.scene_state, value.certificate.scene_goods = 2, 2
        value.certificate.row[:] = (304, 81)
        row = value.rows[0]
        row.left, row.sy, row.word_slot = 304, 81, -1
        for i, slot in enumerate(list(row.slots) + list(value.partial)[:2]):
            slot.cx = 304 + 36 * i if i < 3 else 232 + 36 * (i - 3)
            slot.sy, slot.slot = 81, i if i < 3 else 0
            slot.icon_score = slot.icon_upper_bound = .1

    def pending(self, *, opening=True, old_direction=1, mutate=None):
        h, terrain, old, _ = self.p.armed(direction=old_direction, actual_opening=opening)
        self.h = self.q.h = h
        before = h.status()
        h.ack(old)
        source = self.full_source()
        h.now = max(h.now + 2, old.target_ns + 100_000_000)
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, source, beat=True)))
        event = next(e for e in h.events() if e.command.id == old.id)
        self.assertEqual((2, 0, 0, 0), (event.outcome, event.motion, event.dx, event.dy),
                         'known ACK/full exposure closes visual UNKNOWN without old displacement credit')
        self.assertEqual(before.moves, h.status().moves)
        def build(value):
            self.result(value)
            if mutate: mutate(value)
        self.q.assess(0, 1, build)
        return source, old, self.q.cycle(), before.moves

    def admitted(self, **kwargs):
        source, old, state, moves = self.pending(**kwargs)
        self.assertEqual((3, 0, 1, 0, 0), (state.state, state.partial, state.full_seen,
            state.completed_shops, state.candidate_latched),
            'FULL UNKNOWN needs a distinct uncounted observation wait before any later input')
        self.assertEqual(0, self.h.tick()[0], 'assessment alone never authorizes framing input')
        return source, old, state, moves

    def ticket(self, **kwargs):
        source, old, state, moves = self.admitted(**kwargs)
        self.h.now += 10_000_000
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, source, beat=True)))
        command = self.h.next_move(source)
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.id, old.id)
        self.assertGreater(command.ordinal, old.ordinal)
        self.assertGreater(command.source_capture_id, state.capture_id)
        self.assertLessEqual(self.h.motion_wait().deadline_ns, state.continuation_deadline_ns)
        return source, old, state, moves, command

    def moved(self, partial=False, reveal_cap=False):
        source, old, state, moves, command = self.ticket()
        self.h.ack(command)
        self.assertEqual((moves, state.job_id, 0), (self.h.status().moves,
            self.q.cycle().job_id, self.q.cycle().pending), 'ACK alone gives no displacement/new classifier job')
        latest = native.translated(source, command.direction)
        if reveal_cap: latest.tiles[(0, -2)] = 'floor'
        latest.goods = 'partial' if partial else 'visible'
        self.h.observed_result(command, latest)
        self.assertEqual((moves + 1, state.job_id + 1, 1), (self.h.status().moves,
            self.q.cycle().job_id, self.q.cycle().pending))
        self.assertEqual(self.h.number, self.q.cycle().capture_id)
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, state.continuation_deadline_ns)
        return source, latest, old, state, moves, command

    def test_full_unknown_later_static_fresh_ticket_actual_moved_then_new_candidate(self):
        _, _, old, state, moves, command = self.moved()
        stale = cycle.Result(abi=1, size=C.sizeof(cycle.Result), selected_row=-1, selected_partial=-1,
                             started_ns=self.h.now, finished_ns=self.h.now)
        frozen = bytes(self.q.cycle()), bytes(self.h.status())
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine, state.job_id,
            state.capture_id, state.prefix, self.h.now, C.byref(stale)))
        self.assertEqual(frozen, (bytes(self.q.cycle()), bytes(self.h.status())))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, old.id, self.h.now, 1, 0, 1))
        self.q.assess(1, 1)
        self.assertEqual((1, 1, 1), (self.q.cycle().outcome, self.q.cycle().candidate_latched,
            self.q.cycle().completed_shops))
        self.assertEqual(moves + 1, self.h.status().moves)
        self.assertNotEqual(old.id, command.id)

    def test_fresh_partial_after_local_move_is_classified_truthfully_but_never_navigates(self):
        self.moved(partial=True)
        def safe(value):
            value.partial_count = value.partial_safe_no_positive = 1
            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
        self.q.assess(0, 1, safe)
        self.assertEqual((1, 0, 7, 1), (self.q.cycle().partial, self.q.cycle().full_seen,
            self.q.cycle().state, self.q.cycle().completed_shops))
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_second_unknown_in_same_level_does_not_restore_framing(self):
        self.moved()
        self.q.assess(0, 1, self.result)
        self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_new_full_negative_counts_once_and_uses_only_its_new_durable_source(self):
        _, latest, _, old, _, _ = self.moved(reveal_cap=True)
        scene = self.h.scene(2, 2, latest, beat=True)
        def complete(value):
            structural.NativeStructuralCycle096Tests.certificate(value, scene, 340, 87)
            value.certificate.policy_version = value.certificate.board_mode = 5
        self.q.assess(3, 2, complete)
        self.assertEqual((3, 0, 1), (self.q.cycle().outcome, self.q.cycle().status,
                                   self.q.cycle().completed_shops))
        self.assertGreater(self.q.cycle().capture_id, old.capture_id)
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0], 'new normal result still needs durable publication')
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
            restart.not_before_ns, 1, 0, 1), 'new negative still needs the normal intent commit')

    def test_new_move_visual_unknown_keeps_bounded_wait_without_full_shortcut_or_resend(self):
        source, _, state, moves, command = self.ticket()
        self.h.ack(command)
        latest = deepcopy(source); latest.signature = bytes([80]) * 23296
        self.h.now = max(self.h.now + 2, command.target_ns + 100_000_000)
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, latest, beat=True)))
        self.assertEqual((3, moves, state.job_id, 0), (self.h.status().input_state,
            self.h.status().moves, self.q.cycle().job_id, self.q.cycle().pending))
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.h.now = self.h.motion_wait().deadline_ns + 1
        self.h.tick()
        self.assertEqual((moves, state.job_id), (self.h.status().moves, self.q.cycle().job_id))
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_candidate_target_upper_bound_or_strong_word_is_held_before_observation_input(self):
        faults = {
            'candidate': lambda v: setattr(v, 'outcome', 1),
            'target': lambda v: setattr(v, 'outcome', 2),
            'upper': lambda v: setattr(v.rows[0].slots[1], 'icon_upper_bound', .8),
            'strong_word': lambda v: (setattr(v.partial[0], 'word_present', 1),
                setattr(v.partial[0], 'word_iou', 1), setattr(v.partial[0], 'word_coverage', 1)),
        }
        for name, mutate in faults.items():
            with self.subTest(fault=name):
                self.setUp()
                self.pending(mutate=mutate)
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_real_opening_axis_known_floor_protection_and_safe_potential_roi_are_required(self):
        for fault in ('no_open', 'wrong_axis', 'unknown_next', 'protected_next', 'unexplained_protection', 'hud_partial'):
            with self.subTest(fault=fault):
                self.setUp()
                original = self.full_source
                def source():
                    value = original()
                    if fault == 'unknown_next': value.tiles.pop((-1, 0), None)
                    elif fault == 'protected_next': value.protected.add((-1, 0))
                    elif fault == 'unexplained_protection': value.protected.add((8, 4))
                    return value
                self.full_source = source
                terrain, _, state, _ = self.pending(opening=fault != 'no_open', old_direction=2 if fault == 'wrong_axis' else 1,
                    mutate=(lambda v: setattr(v.partial[0], 'cx', 150)) if fault == 'hud_partial' else None)
                self.full_source = original
                parent, hold, first_job = (state.continuation_deadline_ns,
                    state.hold_started_ns, state.job_id)
                fields = ('inputs', 'moves', 'door_changes', 'terrain_changes',
                          'restarts', 'x', 'y', 'lead_confirmed', 'lead_ns',
                          'walk_started_ns', 'started_ns')
                def credit():
                    current = self.h.status()
                    return tuple(getattr(current, field) for field in fields)
                saved_credit = credit()
                saved_events = b''.join(bytes(event) for event in self.h.events())
                # Reclassification is data only. It never substitutes for the
                # rejected opening/axis/floor/ROI permission to MOVE.
                for retry in range(2):
                    state = self.q.cycle()
                    if state.state == 7:
                        break
                    self.assertNotIn(fault, ('protected_next', 'unexplained_protection'))
                    self.assertEqual((3, 0), (state.state, state.pending))
                    self.assertEqual((parent, hold), (state.continuation_deadline_ns,
                        state.hold_started_ns))
                    self.assertEqual((saved_credit, saved_events, 0), (credit(),
                        b''.join(bytes(event) for event in self.h.events()),
                        self.h.status().input_state))
                    ready, command = self.h.tick()
                    self.assertEqual((0, 0), (ready, command.kind))
                    self.h.now += 10_000_000
                    self.assertLess(self.h.now, parent)
                    self.assertEqual(1, self.h.observe_actual(
                        self.h.scene(2, 2, terrain, beat=True)))
                    current = self.q.cycle()
                    self.assertEqual((1, first_job + retry + 1),
                        (current.pending, current.job_id))
                    self.assertGreater(current.capture_id, state.capture_id)
                    self.assertEqual((parent, hold), (current.continuation_deadline_ns,
                        current.hold_started_ns))
                    self.assertLessEqual(current.deadline_ns,
                        min(parent, current.capture_start_ns + 150_000_000))
                    def unknown(value):
                        self.result(value)
                        if fault == 'hud_partial': value.partial[0].cx = 150
                    self.q.assess(0, 1, unknown)
                    self.assertEqual((saved_credit, saved_events, 0), (credit(),
                        b''.join(bytes(event) for event in self.h.events()),
                        self.h.status().input_state))
                self.assertEqual(7, self.q.cycle().state)
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_later_static_requires_immutable_goods_materials_protection_and_zero(self):
        for fault in ('item', 'material', 'protection', 'motion', 'unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _, _, _ = self.admitted()
                latest = deepcopy(source)
                if fault == 'item': latest.tiles[(-3, -2)] = 'floor'
                elif fault == 'material': latest.tiles[(-2, 0)] = 'dirt'
                elif fault == 'protection': latest.protected.discard((-4, -2))
                elif fault == 'motion': latest.signature = native.translated(source, 1).signature
                elif fault == 'unknown': latest.signature = bytes([80]) * 23296
                self.h.now += 10_000_000
                self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move(self):
        for fault in ('deadline', 'prefix', 'unstable', 'cancel', 'input_unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                if fault == 'input_unknown':
                    source, _, state, moves, command = self.ticket()
                    self.h.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                    self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now + 1, -1)
                    self.h.now += 10_000_000
                    self.h.observe_actual(self.h.scene(2, 2, native.translated(source, 1), beat=True))
                    self.assertEqual((4, moves, state.job_id), (self.h.status().input_state,
                        self.h.status().moves, self.q.cycle().job_id))
                    self.assertNotEqual(4, self.h.tick()[1].kind)
                    continue
                source, _, state, _ = self.admitted()
                if fault == 'deadline': self.h.now = state.continuation_deadline_ns + 1
                else: self.h.now += 10_000_000
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                self.h.observe_actual(self.h.scene(2, 2, source, beat=True),
                    **({'prefix': self.h.prefix + 1} if fault == 'prefix' else {'stable': 0} if fault == 'unstable' else {}))
                self.assertNotEqual(4, self.h.tick()[1].kind)


if __name__ == '__main__':
    unittest.main()
