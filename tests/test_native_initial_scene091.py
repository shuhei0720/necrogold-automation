"""TEST091: withdraw a certainly-unsent first step before observing afresh.

Procedural scenes test control state and finite clocks. Missing device capture
175 is not reconstructed, and later device frames are not used as its cause.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_view074 as view
from tests import test_native_passage072 as passage


class NativeInitialScene091Tests(unittest.TestCase):
    setUpClass = classmethod(view.NativeView074Tests.setUpClass.__func__)
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
    scene = view.NativeView074Tests.scene
    observe = view.NativeView074Tests.observe
    fit_clear = view.NativeView074Tests.fit_clear
    next_operation = view.NativeView074Tests.next_operation
    next_move = view.NativeView074Tests.next_move

    def initial(self):
        terrain = self.fit_clear(passage.passage_room((-3, 0)))
        command = self.next_move(terrain)
        self.assertEqual((4, 1, 0, 0, 0), (command.kind, command.direction,
            self.status().inputs, self.status().moves, self.status().lead_confirmed))
        return terrain, command

    def newer(self, terrain, **kwargs):
        self.now += 1_000_000
        return self.observe(terrain, **kwargs)

    def uncertain(self, terrain):
        return self.scene(terrain, gold=0)

    def withdrawn(self, old, started):
        state = self.status()
        self.assertEqual((0, 0, 0, 4, 0, 0, 0, started), (state.reason,
            state.terminal, state.input_state, state.phase, state.inputs,
            state.moves, state.lead_confirmed, state.walk_started_ns),
            'a certainly-unsent initial scene rejection must withdraw authority and wait')
        event = next(e for e in self.events() if e.command.id == old.id)
        self.assertEqual((3, 17, 0, 0, bytes(old)), (event.outcome, event.reason,
            event.begin_ns, event.observed_capture_id, bytes(event.command)))
        self.reject_old_callbacks_without_mutation(old)
        self.assertEqual(0, self.tick()[0])

    def test_unknown_gold_withdraws_and_requires_two_new_clear_frames(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
        self.newer(terrain)
        self.assertEqual((0, 0), (self.tick()[0], self.status().reason),
            'one new clear observation cannot reuse the old candidate proof')
        self.newer(terrain)
        self.fit_clear(terrain)
        new = self.next_move(terrain)
        self.assertEqual((4, 1, old.ordinal), (new.kind, new.direction, new.ordinal))
        self.assertGreater(new.id, old.id); self.assertGreater(new.source_capture_id, old.source_capture_id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertEqual(started, self.status().walk_started_ns)
        self.reject_old_callbacks_without_mutation(old)

    def test_signature_only_uncertainty_retires_before_new_source(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        changed = deepcopy(terrain); changed.signature = bytes([40])*23296
        self.newer(changed); self.withdrawn(old, started)
        self.newer(terrain); self.assertEqual(0, self.tick()[0])
        self.newer(terrain); self.fit_clear(terrain)
        new = self.next_move(terrain)
        self.assertGreater(new.source_capture_id, old.source_capture_id)
        self.assertEqual((0, 0), (self.status().moves, self.status().inputs))

    def test_new_actual_gold_also_needs_two_independent_frames(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
        gold = deepcopy(terrain)
        gold.tiles.update({(-1, -1): 'gold', (1, -1): 'gold', (0, -1): 'floor'})
        gold.gold = {(-1, -1), (1, -1)}
        self.newer(gold); self.fit_clear_one_frame_forbidden(gold)
        self.newer(gold); self.fit_clear(gold)
        self.assertEqual(4, self.next_move(gold).kind)

    def fit_clear_one_frame_forbidden(self, terrain):
        self.assertEqual(0, self.tick()[0])
        self.assertEqual((0, 0, 0), (self.status().inputs, self.status().moves, self.status().reason))
        # Time alone cannot bless the first new GOLD observation.
        self.now += 500_000_000
        self.assertEqual(0, self.tick()[0])

    def test_changed_gold_cannot_combine_two_different_views_into_authority(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
        first, second = deepcopy(terrain), deepcopy(terrain)
        first.tiles[(-4, -1)] = 'gold'; first.gold = {(-4, -1)}
        second.tiles[(-4, 1)] = 'gold'; second.gold = {(-4, 1)}
        for n in range(30):
            self.now += 100_000_000
            self.observe(first if n % 2 else second)
            self.assertNotEqual(4, self.tick()[1].kind,
                'two gold classifications with different walls are not one stable candidate')
        self.assertEqual((0, 0, 0, started), (self.status().reason, self.status().inputs,
            self.status().moves, self.status().walk_started_ns))

    def test_hidden_old_mouth_is_not_a_negative_even_after_two_new_frames(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
        hidden = deepcopy(terrain)
        del hidden.tiles[(-3, 0)]; del hidden.tiles[(-4, 0)]
        self.newer(hidden); self.newer(hidden)
        self.assertEqual((0, 0), (self.tick()[0], self.status().reason),
            'two unknown mouth observations cannot discard an existing candidate')
        wall = deepcopy(hidden); wall.tiles[(-3, 0)] = 'dirt'
        self.newer(wall); self.assertEqual(0, self.tick()[0])
        self.newer(wall)
        self.assertEqual((1, 2), (lambda result: (result[0], result[1].kind))(self.tick()))

    def test_recovery_allowance_is_two_and_initial_deadline_never_restarts(self):
        terrain, old = self.initial(); started = self.status().walk_started_ns
        for attempt in range(2):
            self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
            self.newer(terrain); self.newer(terrain); self.fit_clear(terrain)
            old = self.next_move(terrain)
            self.assertEqual(4, old.kind)
        self.newer(self.uncertain(terrain))
        self.assertEqual(17, self.status().reason, 'initial scene recovery shares the existing two-replan allowance')
        self.assertEqual((0, 0, started), (self.status().inputs, self.status().moves,
            self.status().walk_started_ns))

    def test_cancel_started_unknown_ack_and_goods_cannot_reacquire(self):
        for fault in ('cancel', 'started', 'unknown_ack', 'goods'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, old = self.initial()
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                elif fault in ('started', 'unknown_ack'):
                    self.now = old.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
                    if fault == 'unknown_ack':
                        self.now += 1
                        self.lib.ng2_controller_complete(self.engine, old.id, self.now, -1)
                frame = self.uncertain(terrain)
                if fault == 'goods': frame.goods = 2
                self.newer(frame)
                self.assertEqual(0, self.recovery().initial_reacquisitions)
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_crossing_stale_and_original_sync_limit_do_not_supply_new_proof(self):
        for fault in ('prefix', 'unstable', 'stale', 'sync', 'walk', 'session'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, old = self.initial(); started = self.status().walk_started_ns
                self.newer(self.uncertain(terrain)); self.withdrawn(old, started)
                if fault in ('sync', 'walk', 'session'):
                    self.now = (started+12*fixture.SECOND if fault == 'sync' else
                        started+45*fixture.SECOND if fault == 'walk' else
                        self.status().started_ns+180*fixture.SECOND)
                    self.assertEqual(0, self.tick()[0])
                    self.assertEqual({'sync': 8, 'walk': 14, 'session': 15}[fault], self.status().reason)
                    continue
                kwargs = {'prefix': self.prefix+1} if fault == 'prefix' else {'stable': 0} if fault == 'unstable' else {
                    'start': self.now-3*fixture.SECOND-1, 'end': self.now+1}
                self.newer(terrain, **kwargs)
                self.newer(terrain)
                self.assertEqual(0, self.tick()[0])
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))


if __name__ == '__main__':
    unittest.main()
