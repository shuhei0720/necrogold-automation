"""TEST118 upper-side calibration cut through public Controller calls.

The sparse geometry follows TEST117's one-sign, lower hidden row. Textures,
public worker results and future responses are explicit procedural inputs;
original PNG/time calibration is recorded separately outside the repository.
No future phone arrival or normal pixel classifier is certified by this file.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_fade100 as opened
from tests.test_native_ring094 import Result


class NativeUpper118Tests(unittest.TestCase):
    WORKER = 6_282_750
    CALLBACK = 534_959
    SYNTH = 278_756_083
    RESPONSE = 57_862_708

    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO118_UPPER_CORE', str(previous)))
            opened.NativeOpenedFade100Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = opened.NativeOpenedFade100Tests.lib

    @classmethod
    def tearDownClass(cls):
        opened.NativeOpenedFade100Tests.tearDownClass()

    def setUp(self):
        self.mechanics = opened.NativeOpenedFade100Tests(methodName='runTest')
        self.mechanics.lib = self.lib
        self.addCleanup(self.mechanics.doCleanups)
        self.h = self.mechanics.harness()
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib = self.lib
        self.q.h = self.h

    @staticmethod
    def point(point, direction):
        x, y = point
        return (x, y) if direction == 1 else (-x, y)

    @staticmethod
    def cross(items):
        return {(x+a, y+b) for x, y in items for a, b in ((0, 0), *native.DIRS.values())
                if -11 <= x+a <= 11 and -5 <= y+b <= 4}

    def frame(self, source, delay=20_000_000):
        self.h.now += delay
        return self.h.observe_actual(self.h.scene(2, 2, source, beat=True))

    def ticket(self, source):
        # Physical phase stays fixed by scene(); no fit/candidate phase helper
        # relocates this clock into a convenient publication window.
        for _ in range(180):
            self.frame(source)
            ready, command = self.h.tick()
            if ready:
                self.assertEqual(4, command.kind, 'an unread lower row needs another observed safe step')
                return command
            self.assertFalse(self.h.status().terminal, 'stopped before the hidden lower row was framed')
        self.fail('no bounded observation MOVE')

    def ack(self, command, source):
        while self.h.now < command.not_before_ns:
            self.frame(source, min(20_000_000, command.not_before_ns-self.h.now))
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.h.now += self.SYNTH
        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, 1))
        self.h.prefix = command.id
        self.h.now += self.RESPONSE

    def pending(self, direction=1, composite=False, fault=None, hint=None):
        d = native.DIRS[direction][0]
        cells = {(x, 0): 'floor' for x in range(-6, 1)}
        cells.update({(x, 1): 'floor' for x in range(-6, -1)})
        cells.update({(-1, 0): 'door', (-1, 1): 'gold', (0, 1): 'dirt',
                      (-7, 0): 'gold', (-7, 1): 'gold', (-7, 2): 'gold',
                      (-6, 2): 'floor', (-5, 2): 'dirt', (-4, 2): 'dirt',
                      (-8, -3): 'stone', (5, 2): 'stone', (8, 3): 'stone'})
        cells.update({(x, -1): 'gold' for x in range(-7, 0)})
        initial = {(self.point(p, direction)[0]+d, self.point(p, direction)[1]): kind
                   for p, kind in cells.items()}
        initial[(0, 0)] = 'floor'
        terrain = native.textured(initial)
        self.h.fit(terrain)
        first = self.ticket(terrain)
        self.assertEqual(direction, first.direction)
        self.ack(first, terrain)
        terrain = native.translated(terrain, direction)
        self.h.observe_actual(self.h.scene(2, 2, terrain, beat=True))
        self.assertEqual((1, d, 0), (self.h.events()[-1].motion,
                                    self.h.events()[-1].dx, self.h.events()[-1].dy))
        opening = self.ticket(terrain)
        self.assertEqual(direction, opening.direction)
        self.ack(opening, terrain)
        source = deepcopy(terrain)
        source.tiles[(d, 0)] = 'floor'
        source.goods = 'partial'
        items = {self.point((x, 4), direction) for x in range(-7, -2)}
        for item in items:
            source.tiles[item] = 'item'
        source.protected = self.cross(items)
        if composite:
            source.tiles[self.point((-5, -1), direction)] = 'door'
            for x in range(-6, -1):
                source.tiles[self.point((x, 1), direction)] = 'dirt'
        if fault == 'roof':
            source.tiles[self.point((-4, -1), direction)] = 'floor'
        elif fault == 'cap':
            source.tiles[self.point((-7, 2), direction)] = 'floor'
        elif fault == 'row':
            source.tiles.pop(self.point((-7, 4), direction))
            source.protected = self.cross(items-{self.point((-7, 4), direction)})
        self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
        self.assertEqual((2, 1, 1, 3), (self.h.status().inputs, self.h.status().moves,
                                      self.h.status().door_changes, self.h.events()[-1].motion))
        parent = self.q.cycle()
        self.assertEqual((1, 1), (parent.pending, parent.partial))
        self.assess(source, hint)
        return source, parent

    def assess(self, source, hint=None):
        state = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, state.job_id, state.capture_id, state.prefix, self.h.now))
        value = Result(abi=1, size=C.sizeof(Result), outcome=0, coverage=1,
                       selected_row=-1, selected_partial=0, partial_count=1,
                       partial_safe_no_positive=1, started_ns=self.h.now)
        # A mirrored source returns the mirrored far-side probe. Selecting
        # lexical-left after a RIGHT entry would fabricate a central-HUD
        # probe that a normal source cannot use as safe evidence.
        x, y = max((p for p, kind in source.tiles.items() if kind == 'item'),
                   key=lambda p: abs(p[0]))
        slot = value.partial[0]
        slot.cx, slot.sy = 448+36*x, 207+36*y-48
        slot.icon_score = slot.icon_upper_bound = .744182904
        slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
        if hint in (1, 2):
            slot.outcome = value.outcome = hint
            value.partial_safe_no_positive = 0
        self.h.now += self.WORKER
        value.finished_ns = self.h.now
        self.h.now += self.CALLBACK
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)))
        return value

    def changed(self, source, direction):
        changed = deepcopy(source)
        changed.tiles[self.point((-5, -1), direction)] = 'gold'
        for x in range(-6, -1):
            changed.tiles[self.point((x, 1), direction)] = 'floor'
        return changed

    def test_same_opening_remote_gold_and_shielded_palette_get_data_not_motion(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.setUp()
                source, parent = self.pending(direction, composite=True)
                changed = self.changed(source, direction)
                self.assertEqual((2, 0, 0), self.h.motion(source, changed, direction))
                counters = (self.h.status().inputs, self.h.status().moves)
                self.frame(changed, 40_233_333)
                current = self.q.cycle()
                self.assertEqual((1, parent.job_id+1), (current.pending, current.job_id),
                    'the original composed static difference must select a fresh DATA job')
                self.assertEqual(parent.continuation_deadline_ns, current.continuation_deadline_ns)
                self.assertEqual(counters, (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(3, current.outcome, 'fresh DATA is not a negative certificate')

    def test_row4_one_sign_route_keeps_parent_through_all_four_safe_steps(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.setUp()
                source, base = self.pending(direction)
                # The separate five-step plan makes one initial V2 allocation.
                # This four-prefix regression checks that allocated parent;
                # the V1 tests retain their original-parent assertions.
                parent = self.q.cycle()
                self.assertEqual(base.continuation_deadline_ns+self.h.status().beat_period_ns,
                                 parent.continuation_deadline_ns)
                for index, wanted in enumerate((direction, direction, 4, 4)):
                    command = self.ticket(source)
                    self.assertEqual(wanted, command.direction)
                    old = self.h.status()
                    self.ack(command, source)
                    latest = native.translated(source, wanted)
                    # Future game response: reveal only the next observed
                    # walking floor. No UNKNOWN is made traversable before it.
                    if index < 3:
                        latest.tiles[native.DIRS[(direction, 4, 4)[index]]] = 'floor'
                    # The normal producer recomputes the cardinal halo after
                    # a row enters the finite array; old clipped bits are not
                    # transported as if they described unseen cells.
                    latest.protected = self.cross({p for p, kind in latest.tiles.items() if kind == 'item'})
                    self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
                    event = self.h.events()[-1]
                    self.assertEqual((1, *native.DIRS[wanted]), (event.motion, event.dx, event.dy))
                    self.assertEqual((old.inputs+1, old.moves+1),
                                     (self.h.status().inputs, self.h.status().moves))
                    self.assertEqual(parent.continuation_deadline_ns,
                                     self.q.cycle().continuation_deadline_ns,
                                     'V2 must retain its first frozen parent after actual MOVED')
                    self.assertLessEqual(self.h.now, parent.continuation_deadline_ns)
                    source = latest
                    self.assess(source)
                self.assertEqual(5, self.h.status().moves)
                self.assertNotEqual(3, self.q.cycle().outcome, 'four moves alone do not certify absence')

    def test_candidate_and_target_never_fund_a_row4_input(self):
        for hint in (1, 2):
            with self.subTest(hint=hint):
                self.setUp()
                source, _parent = self.pending(hint=hint)
                self.assertEqual(1, self.q.cycle().candidate_latched)
                before = (self.h.status().inputs, self.h.status().moves)
                self.frame(source)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4,
                                 'a real returned candidate/target precedes observation authority')
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(0, self.h.status().restarts)

    def test_changed_protection_or_unknown_next_floor_cannot_fund_move(self):
        for fault in ('protected', 'unknown', 'unshielded'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _parent = self.pending(composite=True)
                changed = self.changed(source, 1)
                if fault == 'protected':
                    changed.protected.add((-1, 0))
                elif fault == 'unknown':
                    changed.tiles.pop((-1, 0), None)
                else:
                    changed.tiles[(-2, 0)] = 'dirt'
                before = (self.h.status().inputs, self.h.status().moves)
                self.frame(changed, 40_233_333)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(3, self.q.cycle().outcome)
                self.assertEqual(0, self.h.status().restarts)

    def test_first_v2_snapshot_may_finish_after_data_return_if_born_after_source(self):
        source, _base = self.pending()
        parent = self.q.cycle()  # one initial V2 allocation, never renewed by this snapshot
        classified = self.q.cycle()
        release = classified.release_after_ns
        start, end = release-1_000_000, release+10_000_000
        self.h.now = end+2_000_000
        image = self.h.scene(2, 2, source, beat=True)
        image.beat_remaining = ((5*native.SECOND-(start+end)//2) % native.PERIOD)/native.PERIOD
        before = (self.h.status().inputs, self.h.status().moves)
        self.assertEqual(1, self.h.observe_actual(image, start=start, end=end))
        self.assertEqual(4, self.h.status().phase,
                         'a distinct post-source snapshot committed after the real result must retain the first preparation phase')
        self.assertEqual(0, self.h.status().reason)
        self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)

    def test_first_snapshot_before_worker_or_result_cannot_prepare(self):
        for fault in ('before_source', 'before_worker', 'before_return', 'prefix'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _parent = self.pending()
                classified = self.q.cycle()
                release = classified.release_after_ns
                start, end = release-1_000_000, release+10_000_000
                if fault == 'before_source':
                    start = classified.capture_start_ns-1
                elif fault == 'before_worker':
                    start = classified.worker_started_ns-1
                elif fault == 'before_return':
                    start, end = release-2_000_000, release-1
                self.h.now = max(self.h.now, end+2_000_000)
                image = self.h.scene(2, 2, source, beat=True)
                image.beat_remaining = ((5*native.SECOND-(start+end)//2) % native.PERIOD)/native.PERIOD
                before = (self.h.status().inputs, self.h.status().moves)
                self.h.observe_actual(image, start=start, end=end,
                                      prefix=self.h.prefix+1 if fault == 'prefix' else self.h.prefix)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(0, self.h.status().restarts)

    def test_row4_admission_allocates_one_period_once_and_funds_fifth_step(self):
        """The separate five-step plan allocates V2's extra observation only.

        V1's four-step/original-parent expectations remain in upper_entry112.
        The old V2 four-step receipt is retained outside the repository.
        """
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.setUp()
                source, base = self.pending(direction)
                allocated = self.q.cycle().continuation_deadline_ns
                initial_period = self.h.status().beat_period_ns
                for index, wanted in enumerate((direction, direction, 4, 4, 4)):
                    command = self.ticket(source)
                    self.assertEqual(wanted, command.direction)
                    self.ack(command, source)
                    latest = native.translated(source, wanted)
                    if index < 4:
                        latest.tiles[native.DIRS[(direction, 4, 4, 4)[index]]] = 'floor'
                    latest.protected = self.cross({p for p, kind in latest.tiles.items() if kind == 'item'})
                    self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
                    event = self.h.events()[-1]
                    self.assertEqual((1, *native.DIRS[wanted]), (event.motion, event.dx, event.dy))
                    self.assertEqual(allocated, self.q.cycle().continuation_deadline_ns,
                                     'later callbacks and current models cannot renew the allocation')
                    source = latest
                    self.assess(source)
                self.assertEqual(base.continuation_deadline_ns + initial_period,
                                 allocated, 'V2 allocates exactly one initially valid period')
                self.assertEqual((7, 6), (self.h.status().inputs, self.h.status().moves))
                self.frame(source)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4, 'a sixth upper observation has no authority')
                self.assertNotEqual(3, self.q.cycle().outcome, 'five moves alone are not absence')
