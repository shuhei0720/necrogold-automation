"""Bounded empty-PARTIAL framing after an acknowledged UP opening.

TEST118/a1 source233->235 changes only a remote unprotected DIRT to STONE.
The original clipped merchandise, positive corridor, next FLOOR and normal
strict zero stay fixed. Procedural scenes below test input authority; they
are not future iPhone images or a negative merchandise certificate.
"""
from copy import deepcopy
import ctypes as C
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_entry_corridor102 as corridor
from tests import test_native_observation072 as observation


class NativeEmptyCorridor119Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO119_CORRIDOR_CORE', str(previous)))
            corridor.NativeEntryCorridor102Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = corridor.NativeEntryCorridor102Tests.lib
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                      C.c_int32, C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        corridor.NativeEntryCorridor102Tests.tearDownClass()

    def setUp(self):
        self.fresh()

    def fresh(self):
        self.f = corridor.NativeEntryCorridor102Tests('runTest')
        self.f.lib = self.lib
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.h, self.q = self.f.h, self.f.q

    def pending(self, *, side=1, point=(7, 4)):
        items = {(side*x, y) for x in range(-3, 2) for y in (-5, -4)}
        terrain, opening = self.f.pending(side=side, items=items,
            extra={(side, -5): 'item', point: 'dirt'})
        original = self.f.admitted()
        self.assertEqual((0, 0, 1), (original.pending, original.outcome, original.coverage))
        return terrain, opening, original

    def test_remote_dirt_to_stone_preserves_empty_corridor_framing(self):
        for side, point in ((1, (7, 4)), (-1, (-7, 4))):
            with self.subTest(side=side):
                self.fresh()
                terrain, opening, original = self.pending(side=side, point=point)
                latest = deepcopy(terrain)
                latest.tiles[point] = 'stone'
                source = self.h.scene(2, 2, terrain, beat=True)
                current_scene = self.h.scene(2, 2, latest, beat=True)
                motion = observation.Motion()
                self.assertEqual(1, self.lib.ng2_motion(C.byref(source), C.byref(current_scene),
                                                      3, C.byref(motion)))
                self.assertEqual((2, 0, 0), (motion.kind, motion.dx, motion.dy))
                counts = (self.h.status().inputs, self.h.status().moves)
                self.assertEqual(1, self.f.p.observe(latest))
                current = self.q.cycle()
                self.assertEqual((0, 0, 0, 1, 0), (current.state, current.pending,
                    current.outcome, current.coverage, current.completed_shops),
                    'remote opaque refinement must preserve only the existing one-use observation')
                self.assertEqual((original.job_id, original.capture_id,
                    original.continuation_deadline_ns), (current.job_id,
                    current.capture_id, current.continuation_deadline_ns))
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
                command = self.h.next_move(latest)
                self.assertEqual((4, 3), (command.kind, command.direction))
                self.assertGreater(command.id, opening.id)
                self.assertGreaterEqual(command.not_before_ns-self.h.now, 50_000_000)
                self.assertEqual(0, self.h.status().restarts)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opening.id, command.not_before_ns, 1, 0, 1))

    def test_remote_refinement_never_replaces_local_floor_protection_or_zero(self):
        for fault in ('next', 'origin', 'protected', 'item', 'gold', 'unit', 'unknown'):
            with self.subTest(fault=fault):
                self.fresh()
                terrain, _, _ = self.pending()
                latest = deepcopy(terrain)
                latest.tiles[(7, 4)] = 'stone'
                if fault == 'next': latest.tiles[(0, -1)] = 'dirt'
                elif fault == 'origin': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'protected': latest.protected.add((7, 4))
                elif fault == 'item': latest.tiles[(-3, -5)] = 'dirt'
                elif fault == 'gold': latest.tiles[(1, -2)] = 'stone'
                elif fault == 'unit': latest.signature = native.translated(terrain, 3).signature
                else: latest.signature = bytes([80])*23296
                counts = (self.h.status().inputs, self.h.status().moves)
                self.f.p.observe(latest)
                self.f.held(counts)
                self.assertEqual(0, self.h.status().restarts)


if __name__ == '__main__':
    unittest.main()
