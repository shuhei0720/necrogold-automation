"""TEST106 positive remote GOLD extension before the merchandise latch.

Public procedural callbacks preserve the original unsent action's timing;
these fixtures are not unrecorded phone frames or game arrival evidence.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_opened_fade100 as old


class NativeOpenedGrowth106Tests(unittest.TestCase):
    setUpClass = classmethod(old.NativeOpenedFade100Tests.setUpClass.__func__)
    tearDownClass = classmethod(old.NativeOpenedFade100Tests.tearDownClass.__func__)
    harness = old.NativeOpenedFade100Tests.harness
    armed = old.NativeOpenedFade100Tests.armed
    observe_latest = old.NativeOpenedFade100Tests.observe_latest
    assert_no_fresh = old.NativeOpenedFade100Tests.assert_no_fresh

    @staticmethod
    def rotate(direction, point):
        x, y = point
        return {1: (x, y), 2: (-x, -y), 3: (-y, x), 4: (y, -x)}[direction]

    def source(self, direction=1, support=True, protected=False, **options):
        h, terrain, _, _ = self.armed(direction=direction, reserve=False, **options)
        cells = {(-4, -1): 'floor', (3, 0): 'dirt'}
        if support: cells[(-5, 2) if direction != 4 else (-3, 2)] = 'gold'
        terrain.tiles.update({self.rotate(direction, p): kind for p, kind in cells.items()})
        terrain.tiles.pop(self.rotate(direction, (-4, 2)), None)
        if not support:
            for point in ((-5, 2), (-3, 2), (-4, 1), (-4, 3)):
                if terrain.tiles.get(self.rotate(direction, point)) == 'gold':
                    terrain.tiles.pop(self.rotate(direction, point))
        if protected: terrain.protected.add(self.rotate(direction, (-4, 2)))
        terrain.gold = {p for p, kind in terrain.tiles.items() if kind == 'gold'}
        h.now += 2
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, terrain, beat=True)))
        ticket = h.next_move(terrain)
        self.assertEqual((direction, 5, *native.DIRS[direction], 1), h.choice(terrain))
        return h, terrain, ticket

    @staticmethod
    def revealed(source, direction=1):
        latest = deepcopy(source)
        latest.tiles.pop(NativeOpenedGrowth106Tests.rotate(direction, (-4, -1)), None)
        latest.tiles.update({NativeOpenedGrowth106Tests.rotate(direction, p): kind
            for p, kind in { (3, 0): 'floor', (-4, 2): 'gold' }.items()})
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def test_observed_wall_extension_keeps_the_unsent_opened_floor_action_and_original_window(self):
        h, source, old_ticket = self.source()
        latest = self.revealed(source)
        self.assertEqual(h.choice(source), h.choice(latest))
        self.assertEqual((2, 0, 0), h.motion(source, latest, 1))
        epoch = h.preparation_epoch(old_ticket)
        counts = h.status().inputs, h.status().moves, h.status().door_changes
        frozen = bytes(old_ticket)
        self.observe_latest(h, latest, old_ticket)
        self.assertEqual((0, 0), (h.status().reason, h.status().terminal),
            'new positive GOLD outside both walking footprints must not end this unchanged opened entry')
        retired = next(e for e in h.events() if e.command.id == old_ticket.id)
        self.assertEqual((3, 0, frozen), (retired.outcome, retired.begin_ns, bytes(retired.command)))
        new = h.next_move(latest)
        self.assertGreater(new.id, old_ticket.id)
        self.assertEqual((old_ticket.target_ns, old_ticket.not_before_ns, old_ticket.deadline_ns, old_ticket.ordinal),
            (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal))
        self.assertEqual(epoch, h.preparation_epoch(new))
        self.assertEqual(12, h.scene_details()[-1].validation)
        self.assertEqual(counts, (h.status().inputs, h.status().moves, h.status().door_changes))
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, old_ticket.id, h.now, 1, 0, 1))
        h.ack(new)
        moved = native.translated(latest, 1)
        h.observed_result(new, moved)
        self.assertEqual((counts[0]+1, counts[1]+1, counts[2]),
            (h.status().inputs, h.status().moves, h.status().door_changes))
        self.assertEqual((1, -1, 0), (h.events()[-1].motion, h.events()[-1].dx, h.events()[-1].dy))

    def test_each_input_axis_uses_observed_adjacent_gold_without_extending_the_window(self):
        for direction in (2, 3, 4):
            with self.subTest(direction=direction):
                h, source, ticket = self.source(direction=direction)
                latest = self.revealed(source, direction)
                h.revalidate(source, latest, ticket)

    def test_missing_opening_neighbor_protection_and_nonzero_motion_do_not_gain_fresh_authority(self):
        for fault in ('legacy', 'no_open', 'no_support', 'protected', 'lost_gold',
                      'near', 'moved', 'unknown_motion', 'item'):
            with self.subTest(fault=fault):
                h, source, ticket = self.source(**(
                    {'cycle_profile': False} if fault == 'legacy' else
                    {'actual_opening': False} if fault == 'no_open' else
                    {'support': False} if fault == 'no_support' else
                    {'protected': True} if fault == 'protected' else {}))
                latest = self.revealed(source)
                if fault == 'lost_gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault == 'near': latest.tiles[(0, -1)] = 'dirt'
                elif fault == 'moved': latest.signature = native.translated(source, 1).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80]) * 23296
                elif fault == 'item':
                    latest.tiles[(6, 3)] = 'item';latest.protected.add((6, 3))
                latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
                counts = h.status().inputs, h.status().moves, h.status().door_changes
                self.observe_latest(h, latest, ticket)
                self.assert_no_fresh(h, ticket, counts)

    def test_foreign_prefix_expired_window_and_cancellation_never_replace_the_old_ticket(self):
        for fault in ('prefix', 'expired', 'cancel'):
            with self.subTest(fault=fault):
                h, source, ticket = self.source()
                latest = self.revealed(source)
                counts = h.status().inputs, h.status().moves, h.status().door_changes
                n = len(h.events())
                if fault == 'prefix':
                    self.assertEqual(0, self.observe_latest(h, latest, ticket, prefix=h.prefix+1))
                    self.assertEqual((n, ticket.id), (len(h.events()), h.status().current_command_id))
                else:
                    if fault == 'expired': h.now = ticket.deadline_ns+1
                    else: self.lib.ng2_controller_cancel(h.engine, h.now, 2)
                    self.observe_latest(h, latest, ticket)
                    self.assert_no_fresh(h, ticket, counts)
                self.assertEqual(counts, (h.status().inputs, h.status().moves, h.status().door_changes))


if __name__ == '__main__':
    unittest.main()
