"""TEST095 PARTIAL continuation boundaries on procedural clocks and Scenes.

Remote DIRT differences are taken from received TEST094 pairs214/217 and142/144.
Textures, all prior control responses and future input acceptance are procedural;
this verifies the control relation, not future iPhone arrival or classifier accuracy.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle094


class NativePartialContinuation095Tests(unittest.TestCase):
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

    def pending(self, source_cell=(-5, 1), source_kind='dirt', outcome=0, source_cells=()):
        h, q = self.h, self.q
        terrain, retired = h.continuous_walk(moves=1, direction=1)
        terrain.goods = 'partial'
        terrain.tiles[source_cell] = source_kind
        for point in source_cells:
            terrain.tiles[point] = 'dirt'
        terrain.tiles = {point: kind for point, kind in terrain.tiles.items() if kind != 'unknown'}
        h.now += 2
        self.assertEqual(1, h.observe(h.scene(state=2, gold=2, terrain=terrain, beat=True)))
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, retired.id, retired.not_before_ns, 1, 0, 1))
        self.assertEqual(0, h.tick()[0])
        def safe(value):
            if outcome == 0:
                value.partial_safe_no_positive = value.partial_count = 1
                value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
                value.partial[0].icon_score_exact = 1
        q.assess(outcome, 1, safe)
        return terrain, retired

    def observe(self, terrain, **kwargs):
        self.h.now += 10_000_000
        value = deepcopy(terrain)
        value.tiles = {point: kind for point, kind in value.tiles.items() if kind != 'unknown'}
        return self.h.observe(self.h.scene(state=2, gold=2, terrain=value, beat=True), **kwargs)

    def test_remote_dirt_clearance_in_first_post_assessment_frame_keeps_new_observation_credit(self):
        # Received first continuation142->144 loses only remote DIRT(8,1).
        # The other row comes from214->217's two distant DIRT->FLOOR changes.
        for changes in ({(8, 1): 'unknown'}, {(-5, 1): 'floor', (-4, 1): 'floor'}):
            with self.subTest(changes=changes):
                self.setUp()
                terrain, retired = self.pending(next(iter(changes)), source_cells=changes)
                for point in changes:
                    # The second derived cell must also be part of the frozen
                    # source. Build it in a fresh run rather than edit the copy.
                    if point not in terrain.tiles or terrain.tiles[point] != 'dirt':
                        self.fail('fixture source DIRT support is missing')
                original = self.q.cycle()
                changed = deepcopy(terrain); changed.tiles.update(changes)
                self.assertEqual(1, self.observe(changed))
                current = self.q.cycle()
                self.assertEqual((0, 0, 0), (current.state, current.status, self.h.status().reason),
                                 'remote DIRT observation must not turn a completed no-positive PARTIAL result into KERNEL')
                self.assertEqual((original.job_id, original.continuation_deadline_ns),
                                 (current.job_id, current.continuation_deadline_ns))
                self.assertEqual((1, 1), (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, retired.id,
                    retired.not_before_ns, 1, 0, 1), 'retired pre-classification ticket never revives')

    def test_remote_dirt_clearance_after_new_ticket_keeps_its_frozen_qualified_input(self):
        for point, latest in (((-5, 1), 'floor'), ((8, 1), 'unknown')):
            with self.subTest(point=point, latest=latest):
                self.setUp()
                terrain, retired = self.pending(point)
                self.assertEqual(1, self.observe(terrain))
                self.assertEqual(0, self.q.cycle().state)
                new = self.h.next_move(terrain)
                frozen = bytes(new); deadline = self.q.cycle().continuation_deadline_ns
                changed = deepcopy(terrain); changed.tiles[point] = latest
                self.assertEqual(1, self.observe(changed))
                self.assertEqual((0, 0), (self.q.cycle().state, self.q.cycle().status))
                self.assertEqual((new.id, deadline),
                                 (self.h.status().current_command_id, self.q.cycle().continuation_deadline_ns))
                self.assertEqual(frozen, bytes(self.h.events()[-1].command), 'new ticket fields remain immutable')
                self.assertNotEqual(retired.id, new.id)
                self.h.ack(new)
                self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves),
                                 'synth ACK admits one input but is not displacement')

    def test_only_remote_unprotected_dirt_to_floor_or_unknown_is_admitted(self):
        cases = [((x, y), 'dirt', 'unknown', False)
                 for x, y in ((0, 1), (1, 1), (-1, 1), (-2, 1), (-2, 0))]
        cases += [((8, 1), old, new, False) for old, new in
                  (('stone', 'unknown'), ('gold', 'floor'), ('door', 'floor'),
                   ('item', 'unknown'), ('floor', 'unknown'), ('unknown', 'floor'),
                   ('dirt', 'stone'), ('dirt', 'door'), ('dirt', 'gold'), ('dirt', 'item'))]
        cases += [((8, 1), 'dirt', 'unknown', True)]
        for point, old, new, protected in cases:
            with self.subTest(point=point, old=old, new=new, protected=protected):
                self.setUp()
                terrain, _ = self.pending(point, old)
                changed = deepcopy(terrain); changed.tiles[point] = new
                if protected:
                    changed.protected.add(point)
                self.assertEqual(1, self.observe(changed))
                self.assertEqual((7, 0), (self.q.cycle().state, self.q.cycle().outcome))
                self.assertEqual((1, 1), (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_remote_change_requires_strict_zero_prefix_stability_and_original_deadline(self):
        for fault in ('motion', 'prefix', 'unstable', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, _ = self.pending((8, 1))
                changed = deepcopy(terrain); changed.tiles[(8, 1)] = 'unknown'
                before = self.q.cycle()
                if fault == 'motion':
                    changed.signature = native.translated(terrain, 1).signature
                if fault == 'deadline':
                    self.h.now = before.continuation_deadline_ns + 1
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 1)
                answer = self.observe(changed, **({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                                                 {'stable': 0} if fault == 'unstable' else {}))
                if fault in ('prefix', 'unstable'):
                    self.assertEqual(0, answer)
                    self.assertEqual(bytes(before), bytes(self.q.cycle()), 'unqualified images cannot change continuation')
                else:
                    self.assertNotEqual(0, self.q.cycle().state)
                self.assertEqual((1, 1), (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_remote_change_cannot_clear_candidate_or_started_unknown(self):
        self.pending((8, 1), outcome=1)
        self.assertEqual((1, 1, 7), (self.q.cycle().outcome, self.q.cycle().candidate_latched, self.q.cycle().state))
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.setUp()
        terrain, _ = self.pending((8, 1))
        self.assertEqual(1, self.observe(terrain))
        command = self.h.next_move(terrain)
        self.h.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.h.prefix = command.id
        self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now + 1, -1)
        changed = deepcopy(terrain); changed.tiles[(8, 1)] = 'unknown'
        self.observe(changed)
        self.assertEqual(4, self.h.status().input_state)
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
