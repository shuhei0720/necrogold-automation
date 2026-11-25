"""TEST120: public-C DATA route owners and the one-floor closed approach.

All maps/signatures/HUD clocks and successor images are procedural. Normal
ACK/MOVED earns position/visits; no opaque Controller state is injected. The
phone's three raw cuts are calibrated separately outside Git and missing
predecessors/successors are not reconstructed by these semantic lifecycles.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import unittest

from tests import test_native_controller as native
from tests import test_native_passage072 as passage
from tests import test_native_passage_navigation072 as geometry
from tests import test_native_stationary_wait076 as stationary
from tests import test_native_observation072 as observation
from tests import test_native_recovery as mechanics
from tests import test_native_irregular110 as irregular
from tests.test_native_beat import NativeSample

CORE = Path(os.environ.get('NECRO120_ROUTE_CORE', native.CORE))


class NativeRouteObservation120Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = CORE
            native.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(observation.Motion)]
        cls.lib.ng2_choose.argtypes = [C.POINTER(native.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(native.Scene), C.c_int32,
            C.c_int32, C.c_int32, C.c_int32, C.POINTER(geometry.Decision)]
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_observe_irregular_at.restype = None
        cls.lib.ng2_controller_recovery_status.argtypes = [C.c_void_p, C.POINTER(mechanics.RecoveryStatus)]
        cls.lib.ng2_controller_recovery_samples.argtypes = [C.c_void_p, C.c_size_t,
            C.POINTER(NativeSample), C.c_size_t]
        cls.lib.ng2_controller_recovery_samples.restype = C.c_size_t

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)
    for _method in ('setUp', 'scene', 'tick', 'status', 'events', 'ack', 'fit',
        'next_move', 'motion_wait', 'preparation_epoch', 'fresh_engine',
        'publish_procedural_candidate', 'scene_changes', 'scene_details'):
        locals()[_method] = getattr(native.NativeControllerTests, _method)
    credit = observation.NativeObservation072Tests.credit
    shop_choice = observation.NativeObservation072Tests.choice
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples

    def setUp(self):
        self.now = native.SECOND+100_000_000
        self.number = self.prefix = 0
        self.engine = self.lib.ng2_controller_create_cycle(native.SECOND)
        self.assertTrue(self.engine)
        self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
        self.assertEqual(1, self.lib.ng2_controller_enable_irregular(self.engine))
        self.assertEqual(1, self.lib.ng2_controller_enable_restart_yield(self.engine))
        self.observe(self.scene())
        ready, resume = self.tick()
        self.assertEqual((1, 1), (ready, resume.kind))
        self.ack(resume)
        self.now += 210_000_000

    def fresh_engine(self):
        self.doCleanups()
        self.setUp()

    def frame(self, terrain):
        return self.scene(2, 2 if terrain.gold else 1, terrain, beat=True)

    def observe(self, terrain, **kwargs):
        frame = terrain if isinstance(terrain, native.Scene) else self.frame(terrain)
        self.number += 1
        number = kwargs.get('number', self.number)
        self.lib.ng2_controller_observe_irregular_at(self.engine, C.byref(frame),
            C.byref(irregular.none()), number,
            kwargs.get('start', self.now-2), kwargs.get('end', self.now),
            kwargs.get('prefix', self.prefix), kwargs.get('stable', 1), self.now)
        result = int(self.status().last_capture_id == number)
        if result:
            self._last_fixture_scene = native.Scene.from_buffer_copy(bytes(frame))
        return result

    def direct_motion(self, a, b, direction):
        before, after = self.frame(a), self.frame(b)
        result = observation.Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after),
            direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def passage_choice(self, terrain):
        result = geometry.Decision()
        frame = self.frame(terrain)
        self.assertGreater(self.lib.ng2_choose_passage(C.byref(frame),
            self.status().x, self.status().y, -3, 2, C.byref(result)), 0)
        return tuple(getattr(result, key) for key, _ in result._fields_)

    def earn_left(self, before_tiles):
        initial = native.textured({**{(x-1, y): kind for (x, y), kind
            in before_tiles.items()}, (0, 0): 'floor'})
        self.fit(initial)
        first = self.next_move(initial)
        self.assertEqual(1, first.direction)
        self.ack(first)
        before = native.translated(initial, first.direction)
        self.assertEqual(before_tiles, before.tiles)
        self.now = max(self.now+2, first.target_ns+80_000_002)
        self.observe(before)
        self.assertEqual((0, 1, 1, -1, 0), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().x, self.status().y))
        self.verified_ns = self.now
        return before, self.next_move(before)

    def owned_wait(self, qualify=True):
        terrain = passage.passage_room(mouth=(-3, 2))
        for _ in range(27):
            self.now += 100_000_000
            self.observe(terrain)
        for expected in (1, 1, 4):
            move = passage.NativePassage072Tests.next_operation(self, terrain)
            self.assertEqual((4, expected), (move.kind, move.direction))
            self.ack(move)
            terrain = native.translated(terrain, move.direction)
            self.now = max(self.now+2, move.target_ns+80_000_002)
            self.observe(terrain)
        self.assertEqual((0, 3, 3, -2, 1), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().x, self.status().y))
        old = passage.NativePassage072Tests.next_operation(self, terrain)
        self.assertEqual((4, 4, 10, -2, 1, 1), (old.kind, *self.passage_choice(terrain)))
        self.original_period = self.status().beat_period_ns
        self.parent = min(old.source_start_ns+3*native.SECOND,
            old.phase_sample_ns+3*native.SECOND, self.now+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,
            self.status().started_ns+180*native.SECOND)
        self.saved_credit = self.credit()
        rng = random.Random(120)
        noise = bytes(rng.randrange(20, 100) for _ in terrain.signature)
        trigger = deepcopy(terrain)
        trigger.signature = noise
        self.assertEqual((0, 0, 0), self.direct_motion(terrain, trigger, 4))
        self.now = old.deadline_ns-30_000_000
        self.wait_end = min(self.parent, self.now+2*self.original_period)
        self.observe(trigger)
        self.assertEqual((0, 0, 0), (self.status().reason,
            self.status().input_state, self.status().current_command_id))
        prior = deepcopy(terrain)
        prior.tiles[(6, -1)] = 'floor'
        prior.signature = bytes(round(.95*a+.05*b)
            for a, b in zip(terrain.signature, noise))
        self.assertEqual((2, 0, 0), self.direct_motion(terrain, prior, 4))
        self.now += 50_000_000
        if qualify:
            self.observe(prior)
            self.assertEqual(0, self.status().reason)
        changed = deepcopy(prior)
        del changed.tiles[(-2, 1)]
        changed.signature = bytes(round(.65*a+.35*b)
            for a, b in zip(terrain.signature, noise))
        self.assertEqual((0, 0, 0), self.direct_motion(terrain, changed, 4))
        self.assertEqual((2, 0, 0), self.direct_motion(prior, changed, 4))
        self.assertEqual((4, 10, -1, 1, 1), self.passage_choice(changed))
        return terrain, prior, changed, old

    def enter_stationary_handoff(self):
        before, prior, changed, old = self.owned_wait()
        self.now += 50_000_000
        self.observe(changed)
        self.assertEqual((0, 0, 0), (self.status().reason,
            self.status().input_state, self.status().current_command_id),
            'an owned zero current may hand DATA to the newly observed route')
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual(0, self.preparation_epoch(old))
        self.assertEqual(0, self.tick()[0], 'a DATA handoff is not independent proof')
        self.reject_old_callbacks_without_mutation(old)
        return before, prior, changed, old

    def future_ticket(self, terrain):
        for _ in range(40):
            self.now += 20_000_000
            self.observe(terrain)
            ready, move = self.tick()
            self.assertEqual(0, self.status().reason)
            if ready:
                self.assertEqual(4, move.kind)
                self.assertGreaterEqual(move.not_before_ns-self.now, 50_000_000)
                self.assertLess(move.deadline_ns, self.wait_end)
                return move
        self.fail('independent proof and normal fit must reach a future prepared new ID')

    def test_stationary_target_change_retires_old_unknown_source_until_independent_new_anchor(self):
        _, _, changed, old = self.enter_stationary_handoff()
        new = self.future_ticket(changed)
        self.assertEqual((old.ordinal, 4), (new.ordinal, new.direction))
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertEqual(self.saved_credit, self.credit())
        self.ack(new)
        self.assertEqual(3, self.status().moves, 'ACK alone cannot earn displacement')
        moved = native.translated(changed, new.direction)
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.observe(moved)
        self.assertEqual((0, 4, 4, -2, 2), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().x, self.status().y))

    def vantage_route(self):
        tiles = {(x, y): 'floor' for x in range(-1, 6) for y in range(-2, 3)}
        tiles.update({(x, -3): 'dirt' for x in range(-2, 7)})
        tiles.update({(0, -3): 'floor', (0, -4): 'floor', (-1, -5): 'gold',
            (1, -5): 'gold', (-1, -4): 'dirt', (1, -4): 'dirt',
            (0, 2): 'dirt', (6, 2): 'stone'})
        before, old = self.earn_left(tiles)
        self.assertEqual((3, 8, 0, -4, 1), self.shop_choice(before))
        after = deepcopy(before)
        after.tiles.update({(0, -3): 'dirt', (0, 2): 'floor',
            (11, 1): 'floor', (6, 2): 'dirt'})
        self.assertEqual((1, 8, -1, -2, 1), self.shop_choice(after))
        self.assertEqual((2, 0, 0), self.direct_motion(before, after, old.direction))
        self.original_period = self.status().beat_period_ns
        self.parent = min(old.source_start_ns+3*native.SECOND,
            old.phase_sample_ns+3*native.SECOND, self.verified_ns+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,
            self.status().started_ns+180*native.SECOND)
        return before, after, old

    def enter_vantage_route(self):
        before, after, old = self.vantage_route()
        self.saved_credit = self.credit()
        self.now += 2
        self.wait_end = min(self.parent, self.now+2*self.original_period)
        self.observe(after)
        self.assertEqual((0, 0, 0), (self.status().reason,
            self.status().input_state, self.status().current_command_id),
            'a definitely-unsent GOLD vantage may retire into a fixed DATA route wait')
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual(0, self.tick()[0])
        self.assertEqual(0, self.preparation_epoch(old))
        self.reject_old_callbacks_without_mutation(old)
        return before, after, old

    def test_gold_vantage_orthogonal_route_waits_for_independent_proof_and_future_id(self):
        _, after, old = self.enter_vantage_route()
        new = self.future_ticket(after)
        self.assertEqual((old.ordinal, 1), (new.ordinal, new.direction))
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertEqual(self.saved_credit, self.credit())
        self.ack(new)
        self.assertEqual(1, self.status().moves)
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.observe(native.translated(after, new.direction))
        self.assertEqual((0, 2, 2, -2, 0), (self.status().reason,
            self.status().inputs, self.status().moves, self.status().x, self.status().y))

    def near_route(self):
        tiles = {(0, 0): 'floor', (0, -1): 'floor', (1, 0): 'floor',
            (-1, -2): 'gold', (1, -2): 'dirt', (0, 1): 'dirt',
            (1, 2): 'dirt', (7, 3): 'dirt', (5, 4): 'dirt'}
        before, old = self.earn_left(tiles)
        self.assertEqual((3, 8, 0, -1, 1), self.shop_choice(before))
        after = deepcopy(before)
        after.tiles.update({(0, -2): 'door', (1, -2): 'gold',
            (0, 1): 'stone', (1, 2): 'stone', (7, 3): 'stone', (5, 4): 'floor'})
        after.gold.add((1, -2))
        self.assertEqual((3, 7, 0, -1, 1), self.shop_choice(after))
        self.assertEqual((2, 0, 0), self.direct_motion(before, after, 3))
        return before, after, old

    def test_near_closed_bracket_uses_fresh_id_with_original_physical_beat(self):
        _, after, old = self.near_route()
        epoch, wait, credit = self.preparation_epoch(old), self.motion_wait().deadline_ns, self.credit()
        self.assertNotEqual(0, epoch)
        self.now += 2
        self.observe(after)
        self.assertEqual(0, self.status().reason,
            'a closed door two cells ahead must retain the observed one-floor approach')
        self.assertEqual(12, self.scene_details()[-1].validation)
        ready, new = self.tick()
        self.assertEqual((1, 4, 3), (ready, new.kind, new.direction))
        self.assertGreater(new.id, old.id)
        for key in ('target_ns', 'not_before_ns', 'deadline_ns', 'ordinal'):
            self.assertEqual(getattr(old, key), getattr(new, key), key)
        self.assertEqual(epoch, self.preparation_epoch(new))
        self.assertEqual(wait, self.motion_wait().deadline_ns)
        self.assertEqual(credit, self.credit())
        self.reject_old_callbacks_without_mutation(old)

    def test_stationary_handoff_rejects_missing_current_zero_and_unsafe_route(self):
        for fault in ('no_prior', 'unknown_current', 'next_unknown', 'protected', 'extra_reveal'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, _, changed, old = self.owned_wait(qualify=fault!='no_prior')
                if fault == 'unknown_current':
                    changed.signature = bytes([80])*23296
                elif fault == 'next_unknown':
                    del changed.tiles[(0, 1)]
                elif fault == 'protected':
                    changed.protected.add((-1, 1))
                elif fault == 'extra_reveal':
                    changed.tiles[(8, 4)] = 'floor'
                self.now += 50_000_000
                self.observe(changed)
                self.assertNotEqual(0, self.status().reason)
                self.assertEqual(self.saved_credit, self.credit())
                self.assertEqual(0, self.preparation_epoch(old))
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_vantage_recipe_rejects_unrelated_material_and_protection_changes(self):
        for fault in ('stone_unknown', 'extra_opening', 'protected', 'lost_gold',
                      'next_unknown', 'unknown_motion'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, old = self.vantage_route()
                credit = self.credit()
                if fault == 'stone_unknown':
                    del after.tiles[(6, 2)]
                elif fault == 'extra_opening':
                    after.tiles[(1, -3)] = 'floor'
                elif fault == 'protected':
                    after.protected.add((-1, -2))
                elif fault == 'lost_gold':
                    after.tiles[(-1, -5)] = 'dirt'
                    after.gold.remove((-1, -5))
                elif fault == 'next_unknown':
                    del after.tiles[(-1, 0)]
                else:
                    after.signature = bytes([80])*23296
                self.now += 2
                self.observe(after)
                self.assertNotEqual(0, self.status().reason)
                self.assertEqual(credit, self.credit())
                self.assertEqual(0, self.preparation_epoch(old))
                self.assertNotEqual(4, self.tick()[1].kind)

    def route_wait(self, kind):
        if kind == 'stationary':
            _, _, anchor, old = self.enter_stationary_handoff()
        else:
            _, anchor, old = self.enter_vantage_route()
        return anchor, old

    def test_route_wait_requires_independent_current_prefix_and_strict_zero(self):
        for kind in ('stationary', 'vantage'):
            for fault in ('same_id', 'overlap', 'wrong_prefix', 'unstable', 'unknown', 'moving', 'no_current_fit'):
                with self.subTest(kind=kind, fault=fault):
                    self.fresh_engine()
                    anchor, _ = self.route_wait(kind)
                    anchor_id, anchor_end = self.status().last_capture_id, self.now
                    credit = self.credit()
                    current = deepcopy(anchor)
                    kwargs = {}
                    if fault == 'same_id': kwargs['number'] = anchor_id
                    elif fault == 'overlap': kwargs['start'] = anchor_end-1
                    elif fault == 'wrong_prefix': kwargs['prefix'] = self.prefix+7
                    elif fault == 'unstable': kwargs['stable'] = 0
                    elif fault == 'unknown': current.signature = bytes([80])*23296
                    elif fault == 'moving': current = native.translated(anchor, 4 if kind=='stationary' else 1)
                    else:
                        current = self.frame(anchor)
                        current.beat_valid = 0
                    self.now += 20_000_000
                    self.observe(current, **kwargs)
                    self.assertEqual(credit, self.credit())
                    self.assertNotEqual(4, self.tick()[1].kind,
                        'an invalid or ambiguous successor cannot authorize a route MOVE')

    def test_route_wait_never_renews_original_W_or_parent(self):
        for kind in ('stationary', 'vantage'):
            with self.subTest(kind=kind):
                self.fresh_engine()
                anchor, old = self.route_wait(kind)
                credit = self.credit()
                unclear = deepcopy(anchor)
                unclear.signature = bytes([80])*23296
                for _ in range(3):
                    self.now += 90_000_000
                    self.observe(unclear)
                    self.assertEqual(0, self.tick()[0])
                    self.assertEqual(credit, self.credit())
                self.now = self.wait_end
                self.observe(anchor)
                self.assertEqual(8, self.status().reason,
                    'the old W equality expires even after repeated new observations')
                self.assertEqual(credit, self.credit())
                self.assertEqual(0, self.preparation_epoch(old))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertLessEqual(self.wait_end, self.parent)
        # Input and its later visual proof have separate horizons. The new
        # current's fresh three seconds cannot replace the original parent
        # once true begin has consumed the private DATA route context.
        for kind in ('stationary', 'vantage'):
            for boundary in ('before', 'equal', 'after', 'commit_after'):
                with self.subTest(kind=kind, boundary=boundary):
                    self.fresh_engine()
                    anchor, _ = self.route_wait(kind)
                    new = self.future_ticket(anchor)
                    moves = self.status().moves
                    self.assertGreater(new.source_start_ns+3*native.SECOND, self.parent)
                    with self.subTest(stage='frozen_visual_and_schedule'):
                        self.assertLessEqual(self.motion_wait().deadline_ns, self.parent,
                            'publication must inherit old P into visual authority')
                        self.assertLessEqual(self.recovery().schedule_deadline_ns, self.parent)
                        self.assertLessEqual(self.recovery().visual_deadline_ns, self.parent)
                    self.ack(new)
                    shifted = native.translated(anchor, new.direction)
                    self.assertEqual((1, *native.DIRS[new.direction]),
                        self.direct_motion(anchor, shifted, new.direction))
                    offset = {'before': -1, 'equal': 0, 'after': 1, 'commit_after': 1}[boundary]
                    self.now = self.parent+offset
                    kwargs = {'start': self.parent-3, 'end': self.parent-1} if boundary=='commit_after' else {}
                    self.observe(shifted, **kwargs)
                    expected = moves+int(boundary in ('before', 'equal'))
                    self.assertEqual(expected, self.status().moves,
                        'late capture or actual commit cannot earn MOVED past old P')
                    if boundary in ('after', 'commit_after'):
                        self.assertNotEqual(0, self.status().reason)
                        self.assertNotEqual(4, self.tick()[1].kind)

    def test_started_or_consumed_ticket_cannot_rearm_route_wait(self):
        for stage in ('begun', 'ACK', 'unknown', 'replacement_not_sent', 'cancel', 'goods',
                      'foreground', 'locked', 'owner'):
            with self.subTest(stage=stage):
                self.fresh_engine()
                if stage in ('begun', 'ACK', 'unknown'):
                    _, anchor, old = self.vantage_route()
                    self.now = old.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id,
                        self.now, 1, 0, 1))
                    if stage != 'begun':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine,
                            old.id, self.now, 1 if stage=='ACK' else -1))
                        if stage == 'ACK': self.prefix = old.id
                else:
                    anchor, old = self.route_wait('vantage')
                    if stage == 'replacement_not_sent':
                        new = self.future_ticket(anchor)
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine,
                            new.id, self.now, 0))
                    elif stage == 'cancel':
                        self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    elif stage in ('foreground', 'locked', 'owner'):
                        new = self.future_ticket(anchor)
                        self.now = new.not_before_ns
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                            new.id, self.now, int(stage!='foreground'), int(stage=='locked'),
                            int(stage!='owner')))
                    else:
                        anchor = deepcopy(anchor)
                        anchor.goods = 'visible'
                self.now += 2
                self.observe(anchor)
                ready, current = self.tick()
                self.assertFalse(ready and current.kind==4 and current.direction==1
                    and current.id!=old.id, 'started/spent DATA cannot rearm a new LEFT')
                if stage == 'unknown': self.assertEqual(4, self.status().input_state)
                self.assertEqual(1, self.status().moves)

    def test_near_closed_fresh_rejects_unsafe_bracket_palette_and_motion(self):
        for fault in ('missing_door', 'missing_bracket', 'lost_gold', 'unsafe_next',
                      'near_palette', 'extra_palette', 'protected', 'unknown', 'moving', 'expired', 'commit_expired'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                before, after, old = self.near_route()
                credit = self.credit()
                if fault == 'missing_door': del after.tiles[(0, -2)]
                elif fault == 'missing_bracket':
                    after.tiles[(1, -2)] = 'stone'; after.gold.remove((1, -2))
                elif fault == 'lost_gold':
                    after.tiles[(-1, -2)] = 'dirt'; after.gold.remove((-1, -2))
                elif fault == 'unsafe_next': after.tiles[(0, -1)] = 'dirt'
                elif fault == 'near_palette':
                    after.tiles[(5, 4)] = 'dirt'; after.tiles[(0, 1)] = 'floor'
                elif fault == 'extra_palette': after.tiles[(7, 3)] = 'floor'
                elif fault == 'protected': after.protected.add((0, -1))
                elif fault == 'unknown': after.signature = bytes([80])*23296
                elif fault == 'moving': after.signature = native.translated(before, 3).signature
                self.now = old.deadline_ns+1 if fault in ('expired', 'commit_expired') else self.now+2
                kwargs = {'start': old.deadline_ns-3, 'end': old.deadline_ns-1} if fault=='commit_expired' else {}
                self.observe(after, **kwargs)
                if self.scene_details():
                    self.assertNotEqual(12, self.scene_details()[-1].validation)
                self.assertEqual(credit, self.credit())
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    max(self.now, old.not_before_ns), 1, 0, 1))
                self.assertFalse(any(e.begin_ns and e.command.id>old.id and e.command.kind==4
                    for e in self.events()))


if __name__ == '__main__':
    unittest.main()
