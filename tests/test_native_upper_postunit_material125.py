"""A known remote palette retains the actual-unit job and direct zero.

Public fit/opening/normal H1/worker callbacks earn every owner. Scenes and
worker values are declared control components, not a missing phone replay.
"""
import ctypes as C
from copy import deepcopy
import os
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_projection124 as projection


class NativeUpperPostunitMaterial125Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = os.environ.get('NECRO124_UPPER_PROJECTION_CORE')
        selected = os.environ.get('NECRO125_POSTUNIT_STATIC_CORE')
        if selected:
            os.environ['NECRO124_UPPER_PROJECTION_CORE'] = selected
        try:
            projection.NativeUpperProjection124Tests.setUpClass()
        finally:
            if previous is None:
                os.environ.pop('NECRO124_UPPER_PROJECTION_CORE', None)
            else:
                os.environ['NECRO124_UPPER_PROJECTION_CORE'] = previous
        cls.lib = projection.NativeUpperProjection124Tests.lib

    @classmethod
    def tearDownClass(cls):
        projection.NativeUpperProjection124Tests.tearDownClass()

    def setUp(self):
        self.p = projection.NativeUpperProjection124Tests(methodName='runTest')
        self.p.lib = self.lib
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.t, self.h = self.p.t, self.p.h

    def classified_H1(self, direction=1):
        self.direction = direction
        source, world, command = self.p.actual_H1_new_projection(direction)
        self.p.safe_current(source)
        state = self.t.q.cycle()
        self.assertEqual((3, 0, 1, 0),
            (state.state, state.pending, state.partial, state.candidate_latched))
        self.assertEqual((1, 1, 1, 2, 1, 1, 0, 5), self.p.earned()[:8])
        event = self.h.events()[-1]
        self.assertEqual((command.id, state.capture_id, 2, 1, native.DIRS[direction][0], 0),
            (event.command.id, event.observed_capture_id, event.outcome,
             event.motion, event.dx, event.dy))
        self.assertEqual(command.id, state.prefix)
        self.assertEqual((1, 0, 1, 0), self.p.token()[:4])
        return source, world, state

    def point(self, point):
        x, y = point
        return (x, y) if self.direction == 1 else (-x, y)

    def known_palette(self, source):
        changed = deepcopy(source)
        for point, old, latest in (((-4, 2), 'dirt', 'floor'),
                                    ((-3, 1), 'floor', 'dirt'),
                                    ((6, 2), 'stone', 'dirt')):
            point = self.point(point)
            self.assertEqual(old, source.tiles[point])
            self.assertNotIn(point, source.protected)
            self.assertGreater(abs(point[0])+abs(point[1]), 1)
            self.assertGreater(abs(point[0]-native.DIRS[self.direction][0])+abs(point[1]), 1)
            changed.tiles[point] = latest
        self.assertEqual(source.protected, changed.protected)
        self.assertEqual({p for p, kind in source.tiles.items() if kind == 'item'},
            {p for p, kind in changed.tiles.items() if kind == 'item'})
        self.assertEqual(source.gold, changed.gold)
        self.assertEqual('floor', changed.tiles[native.DIRS[self.direction]])
        return changed

    def test_actual_H1_known_far_palette_keeps_job_and_earns_independent_current(self):
        source, world, state = self.classified_H1()
        changed = self.known_palette(source)
        before = self.p.earned()
        self.t.frame(changed)
        current = self.t.q.cycle()
        self.assertEqual((state.job_id, state.capture_id, state.prefix, 0),
            (current.job_id, current.capture_id, current.prefix, current.pending),
            'fully known remote palette must not replace the actual-unit source with a DATA rebound')
        self.assertEqual((1, 1, 2, 2), self.p.earned()[:4])
        self.assertEqual(4, self.h.status().phase)
        self.assertEqual(before[8:12], self.p.earned()[8:12])
        self.assertEqual(world, self.p.world())
        self.assertEqual((3, 2, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().input_state))

    def assert_no_move(self):
        before = self.h.status().inputs, self.h.status().moves
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))

    def test_reserved_H2_begin_revalidates_old_unit_then_only_normal_H2_rebinds(self):
        source, world, state = self.classified_H1()
        changed = self.known_palette(source)
        self.t.frame(changed)
        command = self.t.ticket(changed)
        self.assertEqual(1, command.direction)
        current = self.t.q.cycle()
        self.assertEqual((state.job_id, state.capture_id, state.prefix),
            (current.job_id, current.capture_id, current.prefix))
        self.assertGreater(command.id, state.prefix)
        before = self.h.status().moves
        self.t.ack(command, changed)
        self.assertEqual(before, self.h.status().moves)
        latest = native.translated(changed, 1)
        latest.tiles[(0, 1)] = 'floor'
        latest.protected = self.t.cross({p for p, kind in latest.tiles.items() if kind == 'item'})
        self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
        event = self.h.events()[-1]
        self.assertEqual((1, -1, 0), (event.motion, event.dx, event.dy))
        current = self.t.q.cycle()
        self.assertEqual((state.job_id+1, event.observed_capture_id, command.id, 1),
            (current.job_id, current.capture_id, current.prefix, current.pending))
        self.assertEqual(world, self.p.world())
        self.assertEqual(state.continuation_deadline_ns, current.continuation_deadline_ns)

    def test_all_six_known_palette_pairs_and_mirror_keep_the_same_job(self):
        points = {'floor': (-3, 1), 'dirt': (-4, 2), 'stone': (6, 2)}
        for direction in (1, 2):
            for old in points:
                for latest in points:
                    if old == latest:
                        continue
                    with self.subTest(direction=direction, old=old, latest=latest):
                        self.setUp()
                        source, world, state = self.classified_H1(direction)
                        changed = deepcopy(source)
                        point = self.point(points[old])
                        self.assertEqual(old, source.tiles[point])
                        changed.tiles[point] = latest
                        self.t.frame(changed)
                        current = self.t.q.cycle()
                        self.assertEqual((state.job_id, state.capture_id, state.prefix, 0),
                            (current.job_id, current.capture_id, current.prefix, current.pending))
                        self.assertEqual((1, 1, 2, 2), self.p.earned()[:4])
                        self.assertEqual(world, self.p.world())
                        self.assertEqual(state.continuation_deadline_ns, current.continuation_deadline_ns)

    def test_unknown_change_still_requires_a_new_data_job(self):
        for fault in ('known_to_unknown', 'unknown_to_stone'):
            with self.subTest(fault=fault):
                self.setUp()
                source, world, state = self.classified_H1()
                changed = deepcopy(source)
                if fault == 'known_to_unknown': changed.tiles.pop((-4, 2))
                else:
                    self.assertNotIn((6, -3), source.tiles)
                    changed.tiles[(6, -3)] = 'stone'
                self.t.frame(changed)
                current = self.t.q.cycle()
                self.assertEqual((state.job_id+1, 1), (current.job_id, current.pending))
                self.assertEqual((1, 1, 5, 2), self.p.earned()[:4])
                self.assert_no_move()
                self.assertEqual(world, self.p.world())
                self.assertEqual(state.continuation_deadline_ns, current.continuation_deadline_ns)

    def test_cross_product_wall_protection_and_unproved_motion_do_not_gain_static_rights(self):
        for fault in ('origin', 'next', 'cross', 'item', 'gold', 'protection', 'motion'):
            with self.subTest(fault=fault):
                self.setUp()
                source, world, state = self.classified_H1()
                changed = self.known_palette(source)
                if fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': changed.tiles[(-1, 0)] = 'dirt'
                elif fault == 'cross': changed.tiles[(-2, 0)] = 'dirt'
                elif fault == 'item': changed.tiles[(-4, 4)] = 'dirt'
                elif fault == 'gold': changed.tiles[(-4, -1)] = 'dirt'
                elif fault == 'protection': changed.protected.add((6, 2))
                elif fault == 'motion': changed.signature = bytes(23296)
                self.t.frame(changed)
                self.assertNotEqual(2, self.p.earned()[2])
                self.assert_no_move()
                self.assertEqual(world, self.p.world())
                self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)

    def test_started_or_unknown_new_input_never_becomes_the_previous_unit(self):
        for known in (None, 0, 1):
            with self.subTest(completion_known=known):
                self.setUp()
                source, _world, state = self.classified_H1()
                changed = self.known_palette(source)
                self.t.frame(changed)
                command = self.t.ticket(changed)
                while self.h.now < command.not_before_ns:
                    self.t.frame(changed, min(20_000_000, command.not_before_ns-self.h.now))
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                self.h.now += self.t.SYNTH
                if known is not None:
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        command.id, self.h.now, known))
                    if known:
                        self.h.prefix = command.id
                self.t.frame(changed)
                self.assertNotEqual(2, self.p.earned()[2])
                self.assertEqual(2, self.h.status().moves)
                self.assert_no_move()
                self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)

    def test_expired_parent_cannot_gain_current_or_ticket(self):
        source, _world, state = self.classified_H1()
        changed = self.known_palette(source)
        self.h.now = state.continuation_deadline_ns+1
        self.t.frame(changed)
        self.assertNotEqual(2, self.p.earned()[2])
        self.assert_no_move()
        self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)

    def test_completed_H2_then_DOWN_keep_their_own_sources_until_declared_FULL(self):
        source, world, state = self.classified_H1()
        source = self.known_palette(source)
        self.t.frame(source)
        for index, direction in enumerate((1, 4, 4, 4)):
            if index in (1, 2):
                # H2 and D1 have different completed directions; each current
                # palette still belongs to that actual unit's immutable job.
                prior = self.t.q.cycle()
                source = deepcopy(source)
                point = (7, 3-index)
                self.assertIn(source.tiles[point], ('floor', 'dirt', 'stone'))
                source.tiles[point] = 'stone' if source.tiles[point] != 'stone' else 'dirt'
                self.t.frame(source)
                current = self.t.q.cycle()
                self.assertEqual((prior.job_id, prior.capture_id, prior.prefix, 0),
                    (current.job_id, current.capture_id, current.prefix, current.pending))
                self.assertEqual((1, 1, 2, 2), self.p.earned()[:4])
            command = self.t.ticket(source)
            self.assertEqual(direction, command.direction)
            before = self.h.status().moves
            self.t.ack(command, source)
            self.assertEqual(before, self.h.status().moves)
            source = native.translated(source, direction)
            if index == 2:
                # A declared new FULL view, not a rewritten normal ITEM mask,
                # resolves potential to the three actual offer origins.
                actual = {(-3, 2), (-2, 2), (-1, 2)}
                for point, kind in list(source.tiles.items()):
                    if kind == 'item' and point not in actual:
                        source.tiles[point] = 'dirt'
                source.goods = 'visible'
            if index < 3:
                source.tiles[(0, 1)] = 'floor'
            source.protected = self.t.cross({p for p, kind in source.tiles.items() if kind == 'item'})
            self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
            event = self.h.events()[-1]
            self.assertEqual((1, *native.DIRS[direction]), (event.motion, event.dx, event.dy))
            self.p.safe_current(source)
            self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)
            self.assertEqual(world, self.p.world())
        self.assertEqual((5, 2, 3, 5), self.p.earned()[4:8])
        self.assertEqual((7, 6), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual('visible', source.goods)
        self.assertLess(self.h.now, state.continuation_deadline_ns,
            'declared public phase/response component only; not a future phone timing guarantee')


if __name__ == '__main__':
    unittest.main()
