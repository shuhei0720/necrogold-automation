"""TEST097 bounded PARTIAL continuation, using public C and procedural clocks.

Received 4b176->178 supplies the shielded DIRT->FLOOR difference, and
6f414->416 the remote STONE->DIRT difference. All prior responses and textures
here are procedural; these tests do not invent subsequent iPhone arrival.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle094


class NativePartialEntry097Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle094.NativeCycle094Tests.setUpClass()
        cls.lib = cycle094.NativeCycle094Tests.lib

    @classmethod
    def tearDownClass(cls):
        cycle094.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle094.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def pending(self, direction=3, side=1, initial='dirt', opened=True,
                opening_direction=None, extra=None, outcome=0, protected=(),
                safe_slots=True, mutate_assessment=None):
        h = self.h
        opening_direction = direction if opening_direction is None else opening_direction
        rotate = {1: lambda x, y: (y, -x), 2: lambda x, y: (-y, x),
                  3: lambda x, y: (x, y), 4: lambda x, y: (-x, -y)}[opening_direction]
        tiles = {(0, 0): 'floor', (0, -1): 'floor',
                 (0, -2): 'door' if opened else 'floor',
                 (-1, -2): 'gold', (1, -2): 'gold',
                 (0, -3): 'floor', (-1, -3): 'floor', (1, -3): 'floor'}
        terrain = native.textured({rotate(x, y): kind for (x, y), kind in tiles.items()})
        h.fit(terrain)
        first = h.next_move(terrain)
        self.assertEqual(opening_direction, first.direction)
        h.ack(first)
        terrain = native.translated(terrain, opening_direction)
        h.observed_result(first, terrain)
        if opened:
            opening = h.next_move(terrain)
            h.ack(opening)
            terrain = deepcopy(terrain)
            terrain.tiles[native.DIRS[opening_direction]] = 'floor'
        else:
            opening = first
        if opening_direction != direction:
            # A separately observed UP entrance must not inherit the RIGHT
            # gate's real acknowledgement. The chooser independently selects it.
            self.assertEqual(3, direction)
            terrain.tiles.update({(0, -1): 'floor', (-1, -1): 'gold', (1, -1): 'gold'})
            self.shield = (side, -2)
        else:
            self.shield = rotate(side, -2)
        terrain.tiles[self.shield] = initial
        terrain.tiles[(8, 3)] = 'stone'
        if extra:
            terrain.tiles.update(extra)
        terrain.protected.update(protected)
        terrain.goods = 'partial'
        if opened:
            h.observed_result(opening, terrain)
            self.assertEqual(3, h.events()[-1].motion)
        else:
            h.now += 2
            self.assertEqual(1, h.observe(h.scene(2, 2, terrain, beat=True)))
        self.assertEqual((1, 1, 1, 0), (h.status().moves, h.status().lead_confirmed,
                                      self.q.cycle().pending, h.status().input_state))
        self.assertEqual(int(opened), h.status().door_changes)
        def safe(value):
            if outcome == 0 and safe_slots:
                value.partial_safe_no_positive = value.partial_count = 1
                value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
                value.partial[0].icon_score_exact = 1
            if mutate_assessment:
                mutate_assessment(value)
        self.q.assess(outcome, 1, safe)
        return terrain, opening

    def observe(self, terrain, **kwargs):
        h = self.h
        h.now += 10_000_000
        value = deepcopy(terrain)
        value.tiles = {point: kind for point, kind in value.tiles.items() if kind != 'unknown'}
        return h.observe(h.scene(2, 2, value, beat=True), **kwargs)

    def continued(self, before):
        current = self.q.cycle()
        self.assertEqual((0, 0, 0, 0), (current.state, current.status,
                                      self.h.status().reason, self.h.status().terminal))
        self.assertEqual((before.job_id, before.continuation_deadline_ns, before.prefix),
                         (current.job_id, current.continuation_deadline_ns, current.prefix))
        self.assertEqual((2, 1, 1), (self.h.status().inputs, self.h.status().moves,
                                   self.h.status().door_changes))

    def rejected(self):
        self.assertNotEqual(0, self.q.cycle().state)
        self.assertEqual(0, self.h.status().restarts)
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)

    def test_acknowledged_open_entry_shielded_floor_dirt_keeps_observation_credit(self):
        for direction in (1, 2, 3, 4):
            for side in (-1, 1):
                for initial in ('dirt', 'floor'):
                    with self.subTest(direction=direction, side=side, initial=initial):
                        self.setUp()
                        terrain, _ = self.pending(direction, side, initial)
                        original = self.q.cycle()
                        changed = deepcopy(terrain)
                        changed.tiles[self.shield] = 'floor' if initial == 'dirt' else 'dirt'
                        self.observe(changed)
                        self.continued(original)

    def test_remote_stone_to_dirt_keeps_observation_credit(self):
        for point in ((-2, 4), (8, 3)):
            with self.subTest(point=point):
                self.setUp()
                terrain, _ = self.pending(extra={point: 'stone'})
                original = self.q.cycle()
                changed = deepcopy(terrain); changed.tiles[point] = 'dirt'
                self.observe(changed)
                self.continued(original)

    def test_shield_permission_requires_actual_same_direction_opening_and_unchanged_gold(self):
        for fault in ('no_open_ack', 'wrong_direction', 'gold_missing', 'gold_changed',
                      'forward_axis', 'other_near'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending(opened=fault != 'no_open_ack',
                                          opening_direction=2 if fault == 'wrong_direction' else 3)
                changed = deepcopy(terrain); changed.tiles[self.shield] = 'floor'
                if fault == 'gold_missing':
                    # A source with a different, still valid route never
                    # inherits the missing shield's GOLD support.
                    changed.tiles[(1, -1)] = 'floor'
                elif fault == 'gold_changed': changed.tiles[(1, -1)] = 'stone'
                elif fault == 'forward_axis': changed.tiles[(0, -2)] = 'dirt'
                elif fault == 'other_near': changed.tiles[(1, 0)] = 'dirt'
                self.observe(changed)
                self.rejected()

    def test_nearby_or_protected_material_and_other_stone_destinations_are_not_quiet(self):
        cases = [((1, -2), 'dirt', new, False) for new in ('unknown', 'stone', 'gold', 'door', 'item')]
        cases += [((8, 3), 'stone', new, False) for new in ('unknown', 'floor', 'gold', 'door', 'item')]
        cases += [((1, 0), 'stone', 'dirt', False), ((0, -2), 'stone', 'dirt', False),
                  ((8, 3), 'stone', 'dirt', True), ((1, -2), 'dirt', 'floor', True)]
        for point, old, new, protected in cases:
            with self.subTest(point=point, old=old, new=new, protected=protected):
                self.setUp()
                terrain, _ = self.pending(extra={point: old})
                changed = deepcopy(terrain); changed.tiles[point] = new
                if protected: changed.protected.add(point)
                self.observe(changed)
                self.rejected()

    def test_partial_relation_still_requires_same_decision_and_independent_strict_zero(self):
        for fault in ('next_floor', 'motion', 'gold', 'goods', 'protected'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending(extra={(-2, 4): 'stone'})
                changed = deepcopy(terrain); changed.tiles[(-2, 4)] = 'dirt'
                if fault == 'next_floor': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'motion': changed.signature = native.translated(terrain, 3).signature
                elif fault == 'gold': changed.tiles[(-1, -1)] = 'floor'
                elif fault == 'goods': changed.goods = 'unknown'
                elif fault == 'protected': changed.protected.add((8, 4))
                self.observe(changed)
                self.rejected()

    def test_original_prefix_continuation_horizon_and_cancel_remain_required(self):
        for fault in ('prefix', 'unstable', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending(extra={(-2, 4): 'stone'})
                changed = deepcopy(terrain); changed.tiles[(-2, 4)] = 'dirt'
                before = self.q.cycle()
                if fault == 'deadline': self.h.now = before.continuation_deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                answer = self.observe(changed, **({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                                                 {'stable': 0} if fault == 'unstable' else {}))
                if fault in ('prefix', 'unstable'):
                    self.assertEqual(0, answer)
                    self.assertEqual(bytes(before), bytes(self.q.cycle()))
                    self.assertEqual(0, self.h.tick()[0])
                else:
                    self.rejected()
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves,
                                           self.h.status().restarts))

    def test_new_ticket_keeps_its_frozen_bounds_and_completed_opening_id_does_not_revive(self):
        terrain, opening = self.pending(extra={(-2, 4): 'stone'})
        original = self.q.cycle()
        changed = deepcopy(terrain); changed.tiles[self.shield] = 'floor'
        self.observe(changed)
        self.continued(original)
        command = self.h.next_move(changed)
        frozen, horizon = bytes(command), self.q.cycle().continuation_deadline_ns
        again = deepcopy(changed); again.tiles[(-2, 4)] = 'dirt'
        self.observe(again)
        self.continued(original)
        self.assertEqual((command.id, horizon),
                         (self.h.status().current_command_id, self.q.cycle().continuation_deadline_ns))
        self.assertEqual(frozen, bytes(self.h.events()[-1].command))
        before = bytes(self.h.status()), bytes(self.q.cycle())
        for callback in (self.lib.ng2_controller_begin, self.lib.ng2_controller_complete):
            values = [self.h.engine, opening.id, self.h.now]
            values += [1, 0, 1] if callback == self.lib.ng2_controller_begin else [1]
            self.assertEqual(0, callback(*values))
        self.assertEqual(before, (bytes(self.h.status()), bytes(self.q.cycle())))
        self.h.ack(command)
        self.assertEqual((3, 1), (self.h.status().inputs, self.h.status().moves),
                         'ACK is one new input, never displacement')


if __name__ == '__main__':
    unittest.main()
