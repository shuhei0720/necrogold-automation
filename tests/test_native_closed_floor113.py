"""TEST113: one observed floor before a closed door keeps bounded authority.

Public procedural Controller runs distinguish cheap remote floor palette
changes from independently proved STONE refresh. They are not device replay.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_closed_refresh081 as closed


class NativeClosedFloor113Tests(unittest.TestCase):
    setUpClass = classmethod(closed.NativeClosedRefresh081Tests.setUpClass.__func__)
    tearDownClass = classmethod(closed.NativeClosedRefresh081Tests.tearDownClass.__func__)

    def capped_stones(self, direction=3):
        terrain, old = self.armed(direction, distance=2)
        for point in ((2, 2), (3, 2)):
            terrain = deepcopy(terrain)
            terrain.tiles[self.rotate(*point)] = 'stone'
            self.now += 2
            self.observe_actual(self.scene(2, 2, terrain, beat=True))
            self.assertEqual(2, self.scene_details()[-1].validation)
            old = self.next_move(terrain)
        self.assertEqual(2, self.scene_details()[-1].chain_count)
        return terrain, old

    def test_remote_floor_palette_keeps_exact_unsent_ticket_without_same_reissues(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                self.fresh_engine()
                terrain, old = self.armed(direction, distance=2)
                credit, old_event = self.credit(), bytes(self.events()[-1])
                for point in ((2, 2), (3, 2), (4, 2)):
                    terrain = deepcopy(terrain)
                    terrain.tiles[self.rotate(*point)] = 'dirt'
                    self.now += 2
                    self.observe_actual(self.scene(2, 2, terrain, beat=True))
                    self.assertEqual((0, 1, old.id), (self.status().reason,
                        self.status().input_state, self.status().current_command_id),
                        'unchanged next floor and closed bracket retain the exact ticket')
                    self.assertEqual(old_event, bytes(self.events()[-1]))
                    self.assertEqual(credit, self.credit())
                self.ack(old)
                self.assertEqual((2, 1), (self.status().inputs, self.status().moves))
                self.observed_result(old, native.translated(terrain, direction))
                self.assertEqual((0, 2, 2), (self.status().reason,
                    self.status().inputs, self.status().moves))

    def test_remote_stone_refresh_retires_then_requires_independent_future_ticket(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                self.fresh_engine()
                terrain, old = self.capped_stones(direction)
                # STONE changes intentionally leave the cheap palette path.
                # The unchanged normal validator exhausts its original two
                # SAME reissues before this separate formal refresh is used.
                changed = deepcopy(terrain)
                changed.tiles[self.rotate(4, 2)] = 'stone'
                credit, epoch = self.credit(), self.status().walk_started_ns
                self.now = old.deadline_ns-8_306_930
                self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertEqual((0, 0, credit), (self.status().reason,
                    self.status().input_state, self.credit()),
                    'distance-one closed floor has the same bounded refresh as the farther approach')
                retired = bytes(self.events()[-1])
                self.assertEqual((0, 3), (self.events()[-1].begin_ns, self.events()[-1].outcome))
                self.assertEqual(bytes(old), bytes(self.events()[-1].command))
                self.reject_old_callbacks_without_mutation(old)
                independent = deepcopy(changed)
                independent.tiles[self.rotate(2, 3)] = 'stone'
                self.assertEqual(self.choice(changed), self.choice(independent))
                self.assertEqual((2, 0, 0), self.motion(changed, independent, direction))
                self.now += 4
                self.observe_actual(self.scene(2, 2, independent, beat=True))
                self.assertEqual((0, credit, epoch), (self.status().reason,
                    self.credit(), self.status().walk_started_ns))
                new = self.next_move(independent)
                self.assertGreater(new.id, old.id)
                self.assertGreater(new.target_ns, old.target_ns)
                self.assertEqual((old.ordinal, direction), (new.ordinal, new.direction))
                self.assertEqual(retired, bytes(self.events()[-2]))
                self.ack(new)
                self.observed_result(new, native.translated(independent, direction))
                self.assertEqual((0, 2, 2), (self.status().reason,
                    self.status().inputs, self.status().moves))

    def test_closed_floor_refresh_refuses_changed_local_material_route_or_protection(self):
        for fault in ('origin', 'next', 'near_origin', 'near_next', 'extra_gold',
                      'lost_gold', 'protection', 'item', 'door', 'farther_door'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, old = self.capped_stones()
                changed = deepcopy(terrain)
                changed.tiles[(4, 2)] = 'stone'
                if fault in ('origin', 'next', 'near_origin', 'near_next'):
                    point = {'origin': (0, 0), 'next': (0, -1),
                             'near_origin': (1, 1), 'near_next': (1, -2)}[fault]
                    changed.tiles[point] = 'dirt'
                elif fault == 'extra_gold': changed.tiles[(-8, 3)] = 'gold'
                elif fault == 'lost_gold': changed.tiles[(-1, -2)] = 'dirt'
                elif fault == 'protection': changed.protected.add((-8, 3))
                elif fault == 'item': changed.tiles[(-8, 3)] = 'item'
                elif fault == 'door': changed.tiles[(0, -2)] = 'floor'
                else:
                    changed.tiles[(0, -2)] = 'floor'
                    changed.tiles[(0, -3)] = 'door'
                    changed.tiles[(-1, -2)] = changed.tiles[(1, -2)] = 'floor'
                    changed.tiles[(-1, -3)] = changed.tiles[(1, -3)] = 'gold'
                credit = self.credit()
                self.now = old.deadline_ns-8_306_930
                self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertEqual((17, credit), (self.status().reason, self.credit()))
                self.assertNotEqual(4, self.tick()[1].kind)
                retired = next(row for row in self.events() if row.command.id == old.id)
                self.assertEqual((0, 3), (retired.begin_ns, retired.outcome))
                self.reject_old_callbacks_without_mutation(old)


for _name in ('setUp', 'scene', 'observe_actual', 'observe', 'tick', 'status', 'events',
              'scene_details', 'motion_wait', 'recovery', 'recovery_samples',
              'all_public_bytes', 'reject_old_callbacks_without_mutation', 'ack',
              'fit', 'next_move', 'fresh_engine', 'publish_procedural_candidate',
              'preparation_epoch', 'choice', 'motion', 'credit', 'observed_result',
              'observed_vantage', 'armed', 'drift'):
    setattr(NativeClosedFloor113Tests, _name,
            getattr(closed.NativeClosedRefresh081Tests, _name))


if __name__ == '__main__':
    unittest.main()
