"""TEST092: a clipped gold hint is not an absent shop.

Procedural rooms and native clocks exercise the public Controller. Neither
the missing first rejected device image nor later iPhone frames are invented.
"""
import ctypes as C
from copy import deepcopy
import random
import unittest

from tests import test_native_controller as fixture
from tests import test_native_passage072 as passage
from tests import test_native_view074 as view
from tests.test_native_blocked067 import Decision

CORE = view.CORE


def clipped_room(mouth=(0, -3)):
    terrain = passage.passage_room(mouth)
    terrain.unlocalized_gold = True
    terrain.gold_peak = 158
    return terrain


class NativeUnlocalizedPassage092Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old = view.CORE
        try:
            view.CORE = CORE
            view.NativeView074Tests.setUpClass.__func__(cls)
        finally:
            view.CORE = old
        cls.lib.ng2_passage_candidates.argtypes = [C.POINTER(fixture.Scene)]
        cls.lib.ng2_passage_candidates.restype = C.c_uint32
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
                                              C.c_int32, C.c_int32, C.POINTER(Decision)]

    tearDownClass = classmethod(view.NativeView074Tests.tearDownClass.__func__)
    setUp = view.NativeView074Tests.setUp
    status = view.NativeView074Tests.status
    events = view.NativeView074Tests.events
    tick = view.NativeView074Tests.tick
    ack = view.NativeView074Tests.ack
    fresh_engine = view.NativeView074Tests.fresh_engine
    all_public_bytes = view.NativeView074Tests.all_public_bytes
    recovery = view.NativeView074Tests.recovery
    recovery_samples = view.NativeView074Tests.recovery_samples
    reject_old_callbacks_without_mutation = view.NativeView074Tests.reject_old_callbacks_without_mutation
    observe = view.NativeView074Tests.observe
    fit_clear = view.NativeView074Tests.fit_clear
    next_operation = view.NativeView074Tests.next_operation
    next_move = view.NativeView074Tests.next_move
    resumed = view.NativeView074Tests.resumed
    after_first_floor = view.NativeView074Tests.after_first_floor
    independent = view.NativeView074Tests.independent
    new_uptime = view.NativeView074Tests.new_uptime

    def scene(self, terrain, gold=None, **kwargs):
        hinted = getattr(terrain, 'unlocalized_gold', False)
        if gold is None and hinted:
            gold = getattr(terrain, 'hint_state', 2)
        frame = passage.NativePassage072Tests.scene(self, terrain, gold=gold, **kwargs)
        if hinted:
            frame.gold_peak = getattr(terrain, 'gold_peak', 158)
        if getattr(terrain, 'origin_unknown', False):
            frame.tiles[5*23+11] = 0
        return frame

    def moved(self, terrain, command, reveal=None, hint=True):
        count = self.status().moves
        self.ack(command)
        shifted = fixture.translated(terrain, command.direction)
        shifted.unlocalized_gold = hint
        shifted.gold_peak = getattr(terrain, 'gold_peak', 158)
        if reveal:
            shifted.tiles.update(reveal)
            shifted.gold = {p for p, kind in shifted.tiles.items() if kind == 'gold'}
        self.now = max(self.now, command.target_ns+80_000_002)
        self.assertEqual(1, self.observe(shifted))
        self.assertEqual(count+1, self.status().moves)
        self.assertEqual(0, self.status().reason)
        return shifted

    def test_positive_clipped_gold_approaches_only_an_independently_supported_passage(self):
        for mouth, direction in (((0, -3), 3), ((-3, 0), 1), ((2, -3), 2)):
            with self.subTest(mouth=mouth):
                self.fresh_engine()
                terrain, _, _ = self.resumed(clipped_room(mouth))
                self.assertEqual(0, self.tick()[0], 'the first post-UI image is not a walking permission')
                self.after_first_floor(terrain)
                self.assertGreater(self.status().walk_started_ns, 0,
                    'a positive clipped gold hint and observed passage must establish a finite walk episode')
                self.fit_clear(terrain)
                command = self.next_move(terrain)
                self.assertEqual(direction, command.direction)
                frame = self.scene(terrain)
                self.assertEqual((2, 0), (frame.gold_state, sum(t == 2 for t in frame.tiles)),
                    'approaching a candidate must neither clear the hint nor fabricate a GOLD cell')
                self.assertNotEqual(0, self.lib.ng2_passage_candidates(C.byref(frame)))
                decision = Decision()
                self.assertGreater(self.lib.ng2_choose_passage(C.byref(frame), 0, 0,
                    mouth[0], mouth[1], C.byref(decision)), 0)
                self.assertEqual((direction, 10, 1),
                    (decision.direction, decision.reason, decision.obstacle))
                terrain = self.moved(terrain, command)
                self.assertEqual((1, 1, 1, 0), (self.status().inputs, self.status().moves,
                    self.status().lead_confirmed, self.status().restarts))

    def test_hint_without_a_supported_mouth_or_safe_surface_never_authorizes_input(self):
        for fault in ('no_mouth', 'low_peak', 'unknown', 'protected', 'item', 'origin', 'goods'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain = clipped_room(None if fault == 'no_mouth' else (0, -3))
                if fault == 'low_peak': terrain.gold_peak = 134
                if fault == 'unknown': terrain.hint_state = 0; terrain.gold_peak = 110
                if fault == 'protected': terrain.protected.add((8, 3))
                if fault == 'item': terrain.tiles[(8, 3)] = 'item'
                if fault == 'origin': terrain.origin_unknown = True
                if fault == 'goods': terrain.goods = 'partial'
                frame = self.scene(terrain)
                self.assertEqual(0, self.lib.ng2_passage_candidates(C.byref(frame)))
                if fault in ('protected', 'item'):
                    clear_frame = self.scene(terrain, gold=1)
                    self.assertNotEqual(0, self.lib.ng2_passage_candidates(C.byref(clear_frame)),
                        'the additional whole-scene rejection belongs only to positive unlocalized views')
                terrain, _, _ = self.resumed(terrain)
                self.after_first_floor(terrain)
                for _ in range(27):
                    self.now += 100_000_000
                    self.observe(terrain)
                    ready, command = self.tick()
                    self.assertNotIn(command.kind, (3, 4),
                        'unknown or protected positive evidence grants neither a step nor a restart')
                    if ready or self.status().reason:
                        break
                self.assertEqual((0, 0, 0), (self.status().inputs,
                    self.status().moves, self.status().restarts))

    def test_independent_pair_rejects_crossing_and_changing_hint_classification(self):
        for fault in ('prefix', 'unstable', 'overlap', 'old_id'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, _ = self.resumed(clipped_room())
                clear = deepcopy(terrain); clear.unlocalized_gold = False
                self.after_first_floor(clear)
                for index in range(26):
                    self.now += 100_000_000
                    self.observe(clear if index % 2 == 0 else terrain)
                    self.assertEqual(0, self.tick()[0],
                        'alternating positive and clear images cannot form one initial passage proof')
                self.independent(clear)
                self.independent(terrain)
                self.assertEqual(0, self.tick()[0])
                last = self.now
                self.now += 2
                kwargs = ({'prefix': self.prefix+1} if fault == 'prefix' else
                          {'stable': 0} if fault == 'unstable' else
                          {'start': last-1, 'end': self.now} if fault == 'overlap' else
                          {'number': self.number-1})
                self.observe(terrain, **kwargs)
                self.assertEqual(0, self.tick()[0],
                    'a crossing, unstable or old image cannot provide the second positive observation')
                self.independent(terrain)
                self.fit_clear(terrain)
                self.assertEqual(4, self.next_move(terrain).kind)

    def test_first_positive_hint_survives_later_clear_and_local_goal_without_restart(self):
        # The hint vetoes a negative even before its two-view movement proof.
        terrain, _, _ = self.resumed(clipped_room())
        closed = passage.passage_room(None)
        self.after_first_floor(closed); self.independent(closed)
        self.assertEqual((12, 0, 0, 0), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().restarts))
        self.assertNotEqual(3, self.tick()[1].kind)
        for final in ('positive', 'closed_clear'):
            with self.subTest(reacquired=final):
                self.fresh_engine()
                terrain = self.fit_clear(clipped_room())
                old = self.next_move(terrain)
                started = self.status().walk_started_ns
                uncertain = self.scene(terrain, gold=0)
                self.now += 1_000_000; self.observe(uncertain)
                self.assertEqual((0, 0), (self.status().reason, self.status().input_state))
                self.reject_old_callbacks_without_mutation(old)
                hidden = passage.passage_room()
                del hidden.tiles[(0, -3)]; del hidden.tiles[(0, -4)]
                self.independent(hidden); self.independent(hidden)
                self.assertEqual((0, 0), (self.tick()[0], self.status().reason),
                    'an unseen original mouth cannot end or restart the positive approach')
                final_view = terrain if final == 'positive' else passage.passage_room(None)
                self.independent(final_view)
                self.assertEqual(0, self.tick()[0])
                self.independent(final_view)
                if final == 'positive':
                    self.fit_clear(final_view)
                    following = self.next_move(final_view)
                    self.assertGreater(following.id, old.id)
                    self.assertEqual((old.ordinal, started, 0, 0, 0),
                        (following.ordinal, self.status().walk_started_ns,
                         self.status().inputs, self.status().moves, self.status().restarts))
                else:
                    self.assertEqual((12, 0, 0, 0), (self.status().reason,
                        self.status().inputs, self.status().moves, self.status().restarts))
                    self.assertNotEqual(3, self.tick()[1].kind)
        for last_hint in (True, False):
            with self.subTest(last_hint=last_hint):
                self.fresh_engine()
                terrain = self.fit_clear(clipped_room())
                for index in range(4):
                    command = self.next_move(terrain)
                    self.assertEqual(3, command.direction)
                    terrain = self.moved(terrain, command, hint=last_hint if index == 3 else True)
                self.assertEqual((0, -4), (self.status().x, self.status().y))
                self.now += 100_000_000
                self.observe(terrain)
                cleanup = self.next_operation(terrain)
                self.assertEqual((2, 12, 0), (cleanup.kind, self.status().reason, self.status().restarts),
                    'a persistent or previously seen clipped positive is not a confirmed local absence')
                self.ack(cleanup)
                self.now += 2
                self.observe(self.scene(terrain, state=1, gold=0))
                self.tick()
                self.assertEqual(0, self.status().restarts)
                self.assertFalse(any(e.command.kind == 3 for e in self.events()))

    def test_observed_gold_handoff_releases_the_local_passage_for_shop_navigation(self):
        terrain = self.fit_clear(clipped_room())
        first = self.next_move(terrain)
        terrain = self.moved(terrain, first,
            {(0, -2): 'door', (-1, -2): 'gold', (1, -2): 'gold'}, hint=False)
        following = self.next_move(terrain)
        self.assertEqual((4, 3, 0), (following.kind, following.direction, self.status().restarts))
        self.assertGreater(following.id, first.id)
        self.assertGreater(following.ordinal, first.ordinal)
        self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
        self.assertTrue(self.scene(terrain).gold_state == 2 and terrain.gold)

    def test_positive_mode_preserves_cancellation_unknown_ack_and_original_budgets(self):
        for fault in ('cancel', 'locked', 'foreground', 'unknown_ack', 'goods', 'sync', 'walk', 'session'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain = self.fit_clear(clipped_room())
                old = self.next_move(terrain)
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                elif fault in ('locked', 'foreground'):
                    self.tick(locked=int(fault == 'locked'), front=int(fault != 'foreground'))
                elif fault == 'unknown_ack':
                    self.now = old.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
                    self.now += 1
                    self.lib.ng2_controller_complete(self.engine, old.id, self.now, -1)
                elif fault == 'goods':
                    goods = self.scene(terrain); goods.goods = 2
                    self.now += 2; self.observe(goods)
                else:
                    state = self.status()
                    self.now = (state.walk_started_ns+12*fixture.SECOND if fault == 'sync' else
                                state.walk_started_ns+45*fixture.SECOND if fault == 'walk' else
                                state.started_ns+180*fixture.SECOND)
                    self.tick()
                    self.assertEqual({'sync': 8, 'walk': 14, 'session': 15}[fault], self.status().reason)
                self.now += 2
                self.observe(terrain)
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                self.assertEqual((0, 0), (self.status().moves, self.status().restarts))
                self.assertEqual(1 if fault == 'unknown_ack' else 0, self.status().inputs)
                self.reject_old_callbacks_without_mutation(old)

    def test_gold_stationary_proof_keeps_unsent_ticket_timing_and_credit(self):
        from tests.test_native_gold_stationary092 import gold_pair
        from necroprobe import shop_navigation as navigation
        source, _ = gold_pair()
        kinds = {value: key for key, value in fixture.KINDS.items()}
        tiles = {(index % 23-11, index // 23-5): kinds[int(kind)]
                 for index, kind in enumerate(source.tiles)}
        del tiles[(0, -5)]; del tiles[(-1, 0)]
        terrain = navigation.Scene(tiles, {p for p, kind in tiles.items() if kind == 'gold'},
            'unknown', set(), bytes(source.signature))
        for preparation in (100_000_000, 44_000_000):
            with self.subTest(preparation=preparation):
                public = fixture.NativeControllerTests('test_initial_slot_waits_before_publishing_a_far_first_beat')
                public.lib = self.lib; public.setUp()
                try:
                    public.fit(terrain)
                    first = public.next_move(terrain); public.ack(first)
                    shifted = fixture.translated(terrain, first.direction)
                    public.observed_result(first, shifted)
                    old = public.next_move(shifted)
                    self.assertEqual((3, 1, 1), (old.direction, public.status().moves,
                        public.status().lead_confirmed))
                    before = public.status()
                    events = tuple(bytes(e) for e in public.events())
                    changed = deepcopy(shifted); random_values = random.Random(85086)
                    changed.signature = bytes(min(255, max(0,
                        value*5//4+4+random_values.randrange(-17, 18))) for value in shifted.signature)
                    changed.tiles[(3, -3)] = changed.tiles[(3, 3)] = 'stone'
                    public.now = max(public.now+2, old.not_before_ns-preparation)
                    self.assertEqual(1, public.observe(public.scene(2, 2, changed, beat=True)))
                    self.assertEqual((0, 0), (public.tick()[0], public.status().reason))
                    self.assertEqual((1, old.id), (public.status().input_state,
                        public.status().current_command_id),
                        'strict stationary evidence keeps the original unsent permission')
                    self.assertEqual(0, public.recovery().post_move_reacquisitions)
                    self.assertEqual(events, tuple(bytes(e) for e in public.events()))
                    self.assertEqual((before.inputs, before.moves),
                        (public.status().inputs, public.status().moves))
                    public.now = old.not_before_ns
                    self.assertEqual(bytes(old), bytes(public.events()[-1].command),
                        'the original ID, source, ordinal and absolute timing remain frozen')
                    self.assertEqual(1, self.lib.ng2_controller_begin(public.engine, old.id,
                        public.now, 1, 0, 1), 'the original unsent command can begin at its original input window')
                    self.assertEqual((before.inputs, before.moves),
                        (public.status().inputs, public.status().moves),
                        'zero displacement supplies neither ACK nor movement credit')
                finally:
                    public.doCleanups()


if __name__ == '__main__':
    unittest.main()
