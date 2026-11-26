"""V2 static observation keeps only its current safe stepping footprint.

Public C fit/ACK/normal Motion/worker lifecycle earns the route. Surfaces,
worker results and future responses are declared procedural inputs, not the
unexported ca23 history or future iPhone merchandise/arrival.
"""
import ctypes as C
from copy import deepcopy
import os
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_begin118 as counted
from tests import test_native_upper_snapshot118 as snapshot


class NativeUpperMaterial122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = os.environ.get('NECRO118_BEGIN_CORE')
        if 'NECRO122_UPPER_CORE' in os.environ:
            os.environ['NECRO118_BEGIN_CORE'] = os.environ['NECRO122_UPPER_CORE']
        try:
            counted.NativeUpperBegin118Tests.setUpClass()
        finally:
            if previous is None:
                os.environ.pop('NECRO118_BEGIN_CORE', None)
            else:
                os.environ['NECRO118_BEGIN_CORE'] = previous
        cls.lib = counted.NativeUpperBegin118Tests.lib
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        from tests import test_native_irregular110 as irregular
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation),
            *([C.c_uint64] * 4), C.c_int32, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        counted.NativeUpperBegin118Tests.tearDownClass()

    def setUp(self):
        self.p = snapshot.NativeUpperSnapshot118Tests(methodName='runTest')
        self.p.lib = self.lib
        self.p.setup_case()
        self.addCleanup(self.p.doCleanups)
        self.t, self.h = self.p.t, self.p.h

    def pending(self, direction=1, remote_door=False):
        # A separate public room model gives the exact ca23 four material
        # roles. The V2 row/roof/cap and earned opening remain the old model.
        d = native.DIRS[direction][0]
        cells = {(x, 0): 'floor' for x in range(-6, 1)}
        cells.update({(x, 1): 'floor' for x in range(-6, -1)})
        cells.update({(-2, 1): 'dirt', (-1, 0): 'door', (-1, 1): 'gold',
            (0, 1): 'dirt', (-7, 0): 'gold', (-7, 1): 'gold', (-7, 2): 'gold',
            (-6, 2): 'floor', (-5, 2): 'dirt', (-4, 2): 'dirt',
            (-8, -3): 'stone', (5, 2): 'stone', (8, 3): 'stone'})
        cells.update({(x, -1): 'gold' for x in range(-7, 0)})
        if remote_door:
            cells[(8, 3)] = 'door'
        initial = {(self.t.point(p, direction)[0] + d,
                    self.t.point(p, direction)[1]): kind for p, kind in cells.items()}
        initial[(0, 0)] = 'floor'
        terrain = native.textured(initial)
        self.h.fit(terrain)
        first = self.t.ticket(terrain)
        self.assertEqual(direction, first.direction)
        self.t.ack(first, terrain)
        terrain = native.translated(terrain, direction)
        self.h.observe_actual(self.h.scene(2, 2, terrain, beat=True))
        self.assertEqual((1, d, 0), (self.h.events()[-1].motion,
            self.h.events()[-1].dx, self.h.events()[-1].dy))
        opening = self.t.ticket(terrain)
        self.assertEqual(direction, opening.direction)
        self.t.ack(opening, terrain)
        source = deepcopy(terrain)
        source.tiles[(d, 0)] = 'floor'
        source.goods = 'partial'
        items = {self.t.point((x, 4), direction) for x in range(-7, -2)}
        for point in items:
            source.tiles[point] = 'item'
        source.protected = self.t.cross(items)
        self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
        self.assertEqual((2, 1, 1, 3), (self.h.status().inputs,
            self.h.status().moves, self.h.status().door_changes,
            self.h.events()[-1].motion))
        self.t.assess(source)
        state = self.t.q.cycle()
        self.assertEqual((3, 0, 1, 0), (state.state, state.pending,
            state.partial, state.candidate_latched))
        return source, state

    def palette(self, source, direction=1):
        latest = deepcopy(source)
        for point, kind in (((8, -2), 'floor'), ((-4, 1), 'dirt'),
                            ((-3, 1), 'dirt'), ((-2, 1), 'floor')):
            latest.tiles[self.t.point(point, direction)] = kind
        return latest

    def ready(self, direction=1):
        source, state = self.pending(direction)
        latest = self.palette(source, direction)
        self.assertEqual((2, 0, 0), self.h.motion(source, latest, direction))
        counts = self.h.status().inputs, self.h.status().moves
        self.t.frame(latest)
        current = self.t.q.cycle()
        self.assertEqual((state.job_id, state.capture_id, state.prefix, 0),
            (current.job_id, current.capture_id, current.prefix, current.pending),
            'walking-exterior palette must retain its immutable classified job')
        self.assertEqual(state.continuation_deadline_ns, current.continuation_deadline_ns)
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
        command = self.t.ticket(latest)
        self.assertEqual(direction, command.direction)
        while self.h.now < command.not_before_ns:
            self.t.frame(latest, min(20_000_000, command.not_before_ns - self.h.now))
        return source, latest, state, command

    def test_same_job_material_can_frame_all_five_steps_without_new_data_or_parent(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.setUp()
                _anchor, source, parent, command = self.ready(direction)
                for index, wanted in enumerate((direction, direction, 4, 4, 4)):
                    if index:
                        command = self.t.ticket(source)
                    self.assertEqual(wanted, command.direction)
                    before = self.h.status()
                    self.t.ack(command, source)
                    self.assertEqual(before.moves, self.h.status().moves, 'ACK is not a unit')
                    source = native.translated(source, wanted)
                    if index < 4:
                        source.tiles[native.DIRS[direction if index == 0 else 4]] = 'floor'
                    source.protected = self.t.cross({p for p, kind in source.tiles.items() if kind == 'item'})
                    self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
                    event = self.h.events()[-1]
                    self.assertEqual((1, *native.DIRS[wanted]), (event.motion, event.dx, event.dy))
                    self.assertEqual((before.inputs + 1, before.moves + 1),
                        (self.h.status().inputs, self.h.status().moves))
                    self.assertLessEqual(self.t.q.cycle().continuation_deadline_ns,
                        parent.continuation_deadline_ns)
                    self.t.assess(source)
                self.assertEqual((7, 6, 1, 0), (self.h.status().inputs,
                    self.h.status().moves, self.h.status().door_changes, self.h.status().restarts))
                self.assertNotEqual(3, self.t.q.cycle().outcome, 'procedural partial steps are not absence')

    def test_begin_reuses_only_the_current_normal_zero_and_keeps_same_command(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.setUp()
                _anchor, latest, parent, command = self.ready(direction)
                self.lib.ng2_begin118_count_reset()
                self.t.frame(latest, 1)
                self.assertGreater(self.lib.ng2_begin118_count(), 0)
                before = self.h.status().inputs, self.h.status().moves
                self.lib.ng2_begin118_count_reset()
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.lib.ng2_begin118_count())
                self.assertEqual(bytes(command), bytes(self.h.events()[-1].command))
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(parent.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)

    def test_changed_current_and_discarded_capture_cannot_borrow_the_old_fact(self):
        for fault in ('nonzero', 'discarded'):
            with self.subTest(fault=fault):
                self.setUp()
                _anchor, latest, _parent, command = self.ready()
                changed = deepcopy(latest)
                if fault == 'nonzero':
                    changed.signature = native.translated(latest, command.direction).signature
                    self.t.frame(changed, 1)
                else:
                    self.h.now += 1
                    self.h.observe_actual(self.h.scene(2, 2, changed, beat=True), stable=0)
                self.lib.ng2_begin118_count_reset()
                result = self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1)
                self.assertEqual(0 if fault == 'nonzero' else 1, result)
                if fault == 'discarded':
                    self.assertEqual(1, self.lib.ng2_begin118_count(), 'discarded seen/current mismatch needs fallback')

    def test_step_cross_special_tiles_masks_and_unproved_motion_never_gain_input(self):
        faults = ('origin', 'next', 'origin_cross', 'next_cross', 'item',
                  'protection', 'gold', 'old_door', 'new_gold', 'new_door', 'motion')
        for fault in faults:
            with self.subTest(fault=fault):
                self.setUp()
                anchor, parent = self.pending(remote_door=fault == 'old_door')
                latest = self.palette(anchor)
                if fault == 'origin': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': latest.tiles[(-1, 0)] = 'dirt'
                elif fault == 'origin_cross': latest.tiles[(0, 1)] = 'floor'
                elif fault == 'next_cross': latest.tiles[(-2, 0)] = 'dirt'
                elif fault == 'item': latest.tiles[(-5, 4)] = 'floor'
                elif fault == 'protection': latest.protected.add((8, -2))
                elif fault == 'gold': latest.tiles[(-4, -1)] = 'floor'
                elif fault == 'old_door': latest.tiles[(8, 3)] = 'floor'
                elif fault == 'new_gold': latest.tiles[(8, -2)] = 'gold'
                elif fault == 'new_door': latest.tiles[(8, -2)] = 'door'
                else: latest.signature = native.translated(anchor, 1).signature
                before = self.h.status().inputs, self.h.status().moves
                self.t.frame(latest)
                rejected = self.t.q.cycle()
                self.assertEqual((parent.job_id + 1, 1),
                    (rejected.job_id, rejected.pending),
                    'an unsafe difference must retain the old DATA bridge, not static credit')
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertLessEqual(self.t.q.cycle().continuation_deadline_ns,
                    parent.continuation_deadline_ns)
                self.assertNotEqual(3, self.t.q.cycle().outcome)

    def test_consumed_not_sent_or_unknown_command_never_rearms_the_fact(self):
        for outcome in (0, -1):
            with self.subTest(outcome=outcome):
                self.setUp()
                _anchor, latest, parent, command = self.ready()
                before = self.h.status().inputs, self.h.status().moves
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                    command.id, self.h.now + 1, outcome))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now + 1, 1, 0, 1))
                self.t.frame(latest, 2)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                self.assertEqual(before[1], self.h.status().moves)
                self.assertLessEqual(self.t.q.cycle().continuation_deadline_ns,
                    parent.continuation_deadline_ns)

    def test_before_first_unit_stone_material_keeps_the_same_static_job(self):
        for point, kind in (((5, 2), 'dirt'), ((8, -2), 'stone')):
            with self.subTest(point=point, new_material=kind):
                self.setUp()
                source, parent = self.pending()
                latest = self.palette(source)
                latest.tiles[point] = kind
                self.assertEqual((2, 0, 0), self.h.motion(source, latest, 1))
                self.t.frame(latest)
                current = self.t.q.cycle()
                self.assertEqual((parent.job_id, 0), (current.job_id, current.pending),
                    'before H1 the same safe material qualification includes STONE')
                self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves))
                self.assertLessEqual(current.continuation_deadline_ns, parent.continuation_deadline_ns)

    def test_after_first_unit_material_keeps_the_old_postunit_bridge(self):
        source, _start, _state, _result, parent = self.p.post_unit()
        before = self.t.q.cycle()
        changed = deepcopy(source)
        changed.tiles[(5, 2)] = 'dirt'
        self.assertNotIn((5, 2), source.tiles,
            'after H1 this coordinate is UNKNOWN, not the shifted original STONE')
        self.assertEqual((2, 0, 0), self.h.motion(source, changed, 1))
        self.t.frame(changed)
        current = self.t.q.cycle()
        self.assertEqual((before.job_id + 1, 1), (current.job_id, current.pending),
            'postunit snapshot and rebound qualification remain unchanged')
        self.assertEqual(parent, current.continuation_deadline_ns)

    def test_material_does_not_rearm_an_existing_geometry_rebound(self):
        source, parent = self.pending()
        exposed = deepcopy(source)
        exposed.tiles[(8, -2)] = 'gold'
        self.assertEqual((2, 0, 0), self.h.motion(source, exposed, 1))
        self.t.frame(exposed)
        rebound = self.t.q.cycle()
        self.assertEqual((parent.job_id + 1, 1), (rebound.job_id, rebound.pending),
            'a genuine new GOLD exposure retains its old one DATA rebound')
        self.t.assess(exposed)
        current = deepcopy(exposed)
        current.tiles[(-4, 1)] = 'dirt'
        self.assertEqual((2, 0, 0), self.h.motion(exposed, current, 1))
        self.t.frame(current)
        stable = self.t.q.cycle()
        self.assertEqual((rebound.job_id, rebound.capture_id, 0),
            (stable.job_id, stable.capture_id, stable.pending),
            'material static qualification neither consumes nor rearms the rebound')
        changed = deepcopy(current)
        changed.tiles[(9, -2)] = 'gold'
        self.t.frame(changed)
        final = self.t.q.cycle()
        self.assertEqual((stable.job_id, stable.capture_id, 0),
            (final.job_id, final.capture_id, final.pending), 'a second geometry rebound remains forbidden')
        self.assertLessEqual(final.continuation_deadline_ns, parent.continuation_deadline_ns)
        self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves))

    def test_original_parent_and_commit_clock_still_bound_material_observation(self):
        for offset in (-1, 0, 1):
            with self.subTest(commit_minus_parent=offset):
                self.setUp()
                source, parent = self.pending()
                latest = self.palette(source)
                self.h.now = parent.continuation_deadline_ns + offset
                self.h.observe_actual(self.h.scene(2, 2, latest, beat=True),
                    start=parent.continuation_deadline_ns - 3,
                    end=parent.continuation_deadline_ns - 1)
                current = self.t.q.cycle()
                self.assertLessEqual(current.continuation_deadline_ns,
                    parent.continuation_deadline_ns)
                self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves))
                if offset > 0:
                    self.assertEqual(9, self.h.status().reason)
                    ready, command = self.h.tick()
                    self.assertFalse(ready and command.kind == 4, 'late route may only perform normal cleanup')
                else:
                    self.assertEqual((parent.job_id, parent.capture_id, parent.prefix, 0),
                        (current.job_id, current.capture_id, current.prefix, current.pending))
