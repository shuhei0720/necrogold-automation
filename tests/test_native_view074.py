"""TEST074: post-UI drawing proof and initial-room candidate retirement.

Procedural frames and monotonic clocks exercise the public native controller;
they do not reproduce omitted device frames or measure the iPhone fade time.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_passage072 as passage
from tests import test_native_ui073 as ui

CORE = mechanics.CORE
SECOND = fixture.SECOND
SETTLE = 200_000_000


class NativeView074Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
    setUp = fixture.NativeControllerTests.setUp
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    tick = fixture.NativeControllerTests.tick
    ack = fixture.NativeControllerTests.ack
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    scene = passage.NativePassage072Tests.scene
    observe = passage.NativePassage072Tests.observe
    fit_clear = passage.NativePassage072Tests.fit_clear
    next_operation = passage.NativePassage072Tests.next_operation
    next_move = passage.NativePassage072Tests.next_move
    moved = passage.NativePassage072Tests.moved
    new_uptime = ui.NativeUI073Tests.new_uptime

    def resumed(self, terrain=None):
        self.new_uptime()
        terrain = passage.passage_room(mouth=None) if terrain is None else terrain
        self.observe(self.scene(terrain, state=1, gold=0))
        ready, resume = self.tick()
        self.assertEqual((1, 1), (ready, resume.kind))
        self.ack(resume)
        ack_ns = self.now
        self.now += 71_289_375
        self.observe(terrain)
        self.first_start = self.now-2
        self.first_end = self.now
        return terrain, resume, ack_ns

    def after_first_floor(self, terrain, delta=0, **kwargs):
        start = self.first_start+SETTLE+delta
        self.now = max(self.now+2, start+2)
        return self.observe(terrain, start=start, end=self.now, **kwargs)

    def independent(self, terrain, **kwargs):
        self.now += 2
        return self.observe(terrain, **kwargs)

    def test_skip_uses_first_floor_start_and_a_later_independent_capture(self):
        terrain, _, ack_ns = self.resumed()
        self.now = ack_ns+SETTLE+2
        self.observe(terrain, start=ack_ns+SETTLE, end=self.now)
        self.assertEqual(0, self.tick()[0],
            '200ms since synth ACK does not prove 200ms since the first rendered FLOOR')
        self.now = self.first_start+SETTLE+1
        self.assertEqual(0, self.tick()[0], 'elapsed time cannot promote the old frame')
        self.after_first_floor(terrain, delta=-1)
        self.assertEqual(0, self.tick()[0], 'a crossing capture cannot confirm rendering')
        self.after_first_floor(terrain)
        ready, pause = self.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.assertGreaterEqual(pause.source_start_ns-self.first_start, SETTLE)
        self.assertEqual([1, 2], [e.command.kind for e in self.events()])

    def test_faded_candidate_closes_before_first_move_only_after_two_wall_frames(self):
        for wall in ('stone', 'dirt'):
            with self.subTest(wall=wall):
                terrain, _, _ = self.resumed(passage.passage_room((-3, 0)))
                started = self.status().walk_started_ns
                closed = deepcopy(terrain)
                closed.tiles[(-3, 0)] = wall
                self.after_first_floor(closed)
                self.assertEqual(0, self.tick()[0], 'one changed wall frame is not a negative decision')
                self.independent(closed)
                ready, pause = self.tick()
                self.assertEqual((1, 2), (ready, pause.kind),
                    'two certain wall observations retire the faded initial candidate')
                self.assertEqual((0, 0, 0, started),
                    (self.status().inputs, self.status().moves,
                     self.status().restarts, self.status().walk_started_ns))
                self.assertEqual([], [e for e in self.events() if e.command.kind == 4])

    def test_reserved_false_candidate_retires_and_switches_to_confirmed_new_mouth(self):
        for initial in ('passage', 'skip'):
            with self.subTest(initial=initial):
                self.fresh_engine()
                terrain = self.fit_clear(passage.passage_room((-3, 0) if initial == 'passage' else None))
                old = self.next_operation(terrain)
                self.assertEqual(4 if initial == 'passage' else 2, old.kind)
                started = self.status().walk_started_ns
                changed = passage.passage_room((0, -3))
                self.independent(changed)
                if not started:
                    started = self.now
                self.assertEqual((0, 0), (self.status().reason, self.status().input_state))
                retired = next(e for e in self.events() if e.command.id == old.id)
                self.assertEqual((3, 0), (retired.outcome, retired.begin_ns))
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(0, self.status().reason, 'a direct-floor candidate gets one valid sync origin')
                self.reject_old_callbacks_without_mutation(old)
                self.independent(changed)
                self.fit_clear(changed)
                following = self.next_move(changed)
                self.assertEqual(3, following.direction,
                    'a confirmed new upper mouth replaces the wall-obstructed left mouth before any input')
                self.assertGreater(following.id, old.id)
                self.assertEqual(started, self.status().walk_started_ns)
                self.assertEqual((0, 0, 0),
                    (self.status().inputs, self.status().moves, self.status().restarts))
                self.reject_old_callbacks_without_mutation(old)

    def test_unknown_or_inconsistent_support_cannot_discard_a_candidate(self):
        terrain, _, _ = self.resumed(passage.passage_room((-3, 0)))
        uncertain = deepcopy(terrain)
        del uncertain.tiles[(-3, 0)]
        self.after_first_floor(uncertain)
        self.independent(uncertain)
        self.assertNotEqual(2, self.tick()[1].kind,
            'an unseen mouth must never be reinterpreted as a closed wall')
        closed = deepcopy(terrain)
        closed.tiles[(-3, 0)] = 'stone'
        self.independent(closed)
        different = deepcopy(closed)
        different.tiles[(-3, -1)] = 'stone'
        self.independent(different)
        self.assertEqual(0, self.tick()[0],
            'same mask with changing mouth support is not two matching observations')
        self.independent(different)
        self.assertEqual((1, 2), (self.tick()[0], self.events()[-1].command.kind))

    def test_prefix_unstable_overlap_and_old_frames_cannot_confirm_drawing_or_wall(self):
        for fault in ('prefix', 'unstable', 'overlap', 'old_id'):
            with self.subTest(fault=fault):
                terrain, _, _ = self.resumed(passage.passage_room((-3, 0)))
                closed = deepcopy(terrain)
                closed.tiles[(-3, 0)] = 'stone'
                self.after_first_floor(closed)
                first = self.now
                self.now += 2
                if fault == 'overlap':
                    self.observe(closed, start=first-1, end=self.now)
                elif fault == 'old_id':
                    self.observe(closed, number=self.number-1)
                else:
                    self.observe(closed, prefix=0 if fault == 'prefix' else self.prefix,
                        stable=0 if fault == 'unstable' else 1)
                self.assertEqual(0, self.tick()[0])
                self.independent(closed)
                self.assertEqual((1, 2), (self.tick()[0], self.events()[-1].command.kind))

    def test_new_gold_and_goods_take_priority_over_initial_negative_or_wall_wait(self):
        for mode in ('gold', 'goods', 'partial'):
            with self.subTest(mode=mode):
                terrain, _, _ = self.resumed()
                revealed = deepcopy(terrain)
                if mode == 'gold':
                    revealed.tiles.update({(0, -1): 'floor', (-1, -1): 'gold', (1, -1): 'gold'})
                    revealed.gold = {(-1, -1), (1, -1)}
                else:
                    revealed.goods = 'visible' if mode == 'goods' else 'partial'
                self.independent(revealed)
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                if mode == 'gold':
                    self.independent(revealed)
                    self.fit_clear(revealed)
                    command = self.next_move(revealed)
                    self.assertEqual((4, 3, 0), (command.kind, command.direction, self.status().restarts))
                else:
                    self.assertEqual(1 if mode == 'goods' else 13, self.status().reason)
                    self.assertEqual(1 if mode == 'goods' else 0, self.status().goods)
                    self.assertEqual((0, 0), (self.status().inputs, self.status().restarts))

    def test_genuine_post_ui_passage_reaches_first_move_and_moved_origin_is_not_reclassified(self):
        terrain, _, _ = self.resumed(passage.passage_room())
        self.after_first_floor(terrain)
        self.fit_clear(terrain)
        first = self.next_move(terrain)
        self.assertEqual(3, first.direction)
        terrain = self.moved(terrain, first)
        self.assertEqual((1, 1, 0, -1),
            (self.status().inputs, self.status().moves, self.status().x, self.status().y))
        following = self.next_move(terrain)
        self.assertEqual(3, following.direction,
            'the fixed world mouth remains valid after its camera-local coordinate changes')

    def test_initial_wait_retains_original_sync_session_and_unknown_input_limits(self):
        for fault in ('sync', 'uncertain_sync', 'transition', 'stale', 'owner', 'cancel', 'session', 'unknown_resume'):
            with self.subTest(fault=fault):
                if fault == 'unknown_resume':
                    self.new_uptime()
                    terrain = passage.passage_room()
                    self.observe(self.scene(terrain, state=1, gold=0))
                    ready, command = self.tick()
                    self.assertEqual((1, 1), (ready, command.kind))
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    self.now += 2
                    self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1)
                    before = self.all_public_bytes()
                    self.now += SETTLE+2
                    self.observe(terrain)
                    self.assertEqual(before, self.all_public_bytes())
                    continue
                terrain, _, ack_ns = self.resumed(passage.passage_room(
                    mouth=None if fault == 'transition' else (-3, 0)))
                started = self.status().walk_started_ns
                if fault in ('sync', 'uncertain_sync'):
                    uncertain = deepcopy(terrain)
                    del uncertain.tiles[(-3, 0)]
                    for offset in range(1, 12):
                        self.now = started+offset*SECOND
                        self.observe(self.scene(uncertain, gold=0) if fault == 'uncertain_sync' else uncertain)
                        self.tick()
                        self.assertEqual(started, self.status().walk_started_ns)
                    self.now = started+12*SECOND
                    self.tick()
                    self.assertEqual(8, self.status().reason)
                elif fault == 'transition':
                    self.now += 100_000_000
                    self.observe(self.scene(terrain, gold=0))
                    self.assertEqual((0, 0), (self.tick()[0], self.status().reason))
                    self.now = ack_ns+4*SECOND
                    self.observe(self.scene(terrain, gold=0))
                    self.tick()
                    self.assertEqual(17, self.status().reason)
                elif fault == 'stale':
                    self.now = self.status().last_capture_start_ns+3*SECOND+1
                    self.tick()
                    self.assertEqual(7, self.status().reason)
                elif fault == 'session':
                    self.now = self.status().started_ns+180*SECOND
                    self.tick()
                    self.assertEqual((1, 15), (self.status().terminal, self.status().reason))
                elif fault == 'owner':
                    self.tick(owner=0)
                    self.assertEqual(5, self.status().reason)
                else:
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    self.assertEqual(2, self.status().reason)
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                self.assertEqual((0, 0), (self.status().inputs, self.status().restarts))

    def test_restart_exploration_and_goods_stay_one_bounded_native_session(self):
        passage.NativePassage072Tests.test_one_native_session_restarts_searches_enters_and_completes_only_on_goods(self)

    def test_uncertain_drawing_waits_for_gold_or_two_clear_observations_without_ending(self):
        for initial in ('clear', 'false_candidate'):
            for timing in ('before_cutoff', 'after_cutoff'):
                for gold_state in (0, 2):
                    for final in ('gold', 'clear'):
                        with self.subTest(initial=initial, timing=timing, gold_state=gold_state, final=final):
                            terrain, _, _ = self.resumed(passage.passage_room(
                                mouth=None if initial == 'clear' else (-3, 0)))
                            started = self.status().walk_started_ns
                            start = self.first_start+SETTLE+(
                                -100_000_000 if timing == 'before_cutoff' else 50_000_000)
                            self.now = max(self.now+2, start+2)
                            self.observe(self.scene(terrain, gold=gold_state), start=start, end=self.now)
                            self.assertEqual((0, 0), (self.status().reason, self.status().terminal),
                                'an initial drawing uncertainty is neither a negative nor a screen failure')
                            self.assertEqual(0, self.tick()[0])
                            self.assertEqual((0, 0), (self.status().inputs, self.status().restarts))
                            confirmed = deepcopy(terrain)
                            if final == 'gold':
                                confirmed.tiles.update({(0, -1): 'floor', (-1, -1): 'gold', (1, -1): 'gold'})
                                confirmed.gold = {(-1, -1), (1, -1)}
                                self.now += 100_000_000
                                self.observe(confirmed)
                                self.now += 100_000_000
                                self.observe(confirmed)
                                self.fit_clear(confirmed)
                                command = self.next_move(confirmed)
                                self.assertEqual((4, 3, 0),
                                    (command.kind, command.direction, self.status().restarts))
                            else:
                                if initial == 'false_candidate':
                                    confirmed.tiles[(-3, 0)] = 'stone'
                                self.now = max(self.now+2, self.first_start+SETTLE+2)
                                self.observe(confirmed)
                                self.assertEqual(0, self.tick()[0],
                                    'uncertainty must invalidate the old negative/candidate proof')
                                self.independent(confirmed)
                                ready, pause = self.tick()
                                self.assertEqual((1, 2), (ready, pause.kind))
                                self.assertEqual(started, self.status().walk_started_ns)
                            self.assertNotIn(3, [e.command.kind for e in self.events()])


if __name__ == '__main__':
    unittest.main()
