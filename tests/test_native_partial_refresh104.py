"""TEST104 fresh PARTIAL classification after a changed static observation.

Public C callbacks, procedural Scenes/results and clocks establish ownership.
No phone Scene is embedded and no modeled later image proves device arrival.
The normal typed worker path is distinct from actual Ring pixel accuracy.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_observation072 as observation
from tests import test_native_partial_entry097 as entry
from tests.test_native_ring094 import Result


class NativePartialRefresh104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry.NativePartialEntry097Tests.setUpClass()
        cls.lib = entry.NativePartialEntry097Tests.lib
        cls.lib.ng2_choose.argtypes = [C.POINTER(native.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                      C.c_int32, C.POINTER(observation.Motion)]
        cls.lib.ng2_entered_gate.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.POINTER(observation.Entrance)]

    @classmethod
    def tearDownClass(cls):
        entry.NativePartialEntry097Tests.tearDownClass()

    def setUp(self):
        self.fresh()

    def fresh(self):
        self.p = entry.NativePartialEntry097Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q
        self.entrance = None

    @staticmethod
    def safe(value):
        value.partial_safe_no_positive = value.partial_count = 1
        slot = value.partial[0]
        slot.icon_score = slot.icon_upper_bound = .1
        slot.icon_score_exact = 1

    def pending(self, *, extra=None, protected=()):
        cells = {(8, 3): 'floor'}
        cells.update(extra or {})
        source, opened = self.p.pending(direction=1, extra=cells, protected=protected)
        self.assertEqual((3, 0, 0, 2, 1, 1),
            (self.q.cycle().state, self.q.cycle().pending, self.q.cycle().status,
             self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        return source, opened

    def choice(self, terrain, entrance=None):
        # The public helper reconstructs world visits from actual MOVED
        # events. Immediately after opening, no entered-gate MOVE occurred.
        return observation.NativeObservation072Tests.choice(self.h, terrain, entrance or self.entrance)

    def motion(self, before, after, direction):
        return observation.NativeObservation072Tests.motion(self.h, before, after, direction)

    def counts(self):
        value = self.h.status()
        return value.inputs, value.moves, value.x, value.y

    def no_move(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4),
                         'neither an unclassified source nor UNKNOWN can restart or move')

    @staticmethod
    def changed(source, point=(8, 3), material='dirt'):
        latest = deepcopy(source)
        latest.tiles[point] = material
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def refresh(self, source, *, point=(8, 3), material='dirt'):
        old, counts = self.q.cycle(), self.counts()
        frozen = dict(source.tiles), set(source.gold), set(source.protected), source.signature
        latest = self.changed(source, point, material)
        self.assertNotEqual(source.tiles.get(point), latest.tiles.get(point),
                            'a refresh fixture must actually change the frozen material')
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((2, 0, 0), self.motion(source, latest, self.choice(source)[0]))
        self.assertEqual(1, self.p.observe(latest))
        self.assertEqual(frozen, (source.tiles, source.gold, source.protected, source.signature),
                         'the earlier procedural source remains immutable')
        return latest, old, self.assert_fresh(old, counts)

    @staticmethod
    def cross(point):
        x, y = point
        return {(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)}

    def exposed_source(self):
        return self.pending(extra={(-5, 2): 'item', (-6, 2): 'floor',
                                   (-7, 2): 'gold', (-8, 2): 'floor', (9, 3): 'floor'},
                            protected=self.cross((-5, 2)))

    def expose(self, source, *, point=(-7, 2), adjacent=True):
        latest = deepcopy(source)
        latest.tiles[point] = 'item'
        latest.protected.update(self.cross(point))
        if adjacent:
            latest.tiles[(-6, 2)] = 'item'
            latest.protected.update(self.cross((-6, 2)))
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def assert_fresh(self, old, counts):
        current = self.q.cycle()
        self.assertEqual((old.job_id + 1, 1, 1, 1, 0),
            (current.job_id, current.pending, current.state, current.partial, current.full_seen),
            'a changed static PARTIAL must retire old continuation and bind a fresh normal data job')
        self.assertEqual((self.h.number, self.h.prefix), (current.capture_id, current.prefix))
        self.assertGreater(current.capture_id, old.capture_id)
        self.assertLessEqual(current.continuation_deadline_ns, old.continuation_deadline_ns)
        self.assertEqual((0, 0, 0),
            (current.worker_started_ns, current.assessment_ns, current.candidate_latched))
        self.assertEqual(counts,
            (self.h.status().inputs, self.h.status().moves, self.h.status().x, self.h.status().y))
        self.assertEqual(0, self.h.tick()[0], 'unclassified changed pixels carry no MOVE authority')
        return current

    def test_new_far_gold_and_material_refresh_withdraw_credit_and_reserved_ticket(self):
        for stage, material in (('observe', 'gold'), ('credit', 'dirt'), ('reserved', 'dirt')):
            with self.subTest(stage=stage, material=material):
                self.fresh()
                source, opened = self.pending()
                ticket = None
                if stage != 'observe':
                    self.assertEqual(1, self.p.observe(source))
                    self.assertEqual((0, 0), (self.q.cycle().state, self.h.status().input_state))
                    if stage == 'reserved':
                        ticket = self.h.next_move(source)
                        self.assertEqual((4, 1, 0),
                            (ticket.kind, self.h.status().input_state, self.h.events()[-1].begin_ns))
                counts = self.counts()
                latest, old, fresh = self.refresh(source, material=material)
                self.assertEqual((0, 0), (self.h.status().input_state, self.h.status().current_command_id))
                if ticket:
                    retired = next(e for e in self.h.events() if e.command.id == ticket.id)
                    self.assertEqual((0, 3, bytes(ticket)),
                        (retired.begin_ns, retired.outcome, bytes(retired.command)))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        ticket.id, max(self.h.now, ticket.not_before_ns), 1, 0, 1))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opened.id, self.h.now, 1, 0, 1))
                self.q.assess(0, 1, self.safe)
                self.assertEqual((fresh.job_id, 3, 0), (self.q.cycle().job_id,
                    self.q.cycle().state, self.q.cycle().completed_shops))
                self.no_move()
                self.assertEqual(1, self.p.observe(latest))
                new = self.h.next_move(latest)
                self.assertGreater(new.id, ticket.id if ticket else opened.id)
                self.assertGreater(new.source_capture_id, fresh.capture_id)
                self.assertLessEqual(new.deadline_ns, old.continuation_deadline_ns)
                self.assertEqual(counts, self.counts())

    def test_new_candidate_target_or_unsafe_unknown_holds_and_pending_source_never_refreshes(self):
        for outcome in (0, 1, 2):
            with self.subTest(outcome=outcome):
                self.fresh()
                source, _ = self.pending()
                latest, old, fresh = self.refresh(source)
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    fresh.job_id, fresh.capture_id, fresh.prefix, self.h.now))
                snapshot = bytes(self.q.cycle())
                wrong = Result(abi=1, size=C.sizeof(Result), selected_row=-1, selected_partial=-1,
                    started_ns=self.h.now, finished_ns=self.h.now + 1)
                for job, capture, prefix in ((old.job_id, old.capture_id, old.prefix),
                                            (fresh.job_id, old.capture_id, fresh.prefix),
                                            (fresh.job_id, fresh.capture_id, fresh.prefix + 1)):
                    self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
                        job, capture, prefix, self.h.now, C.byref(wrong)))
                    self.assertEqual(snapshot, bytes(self.q.cycle()))
                self.assertEqual(1, self.p.observe(self.changed(latest, material='floor')))
                self.assertEqual((fresh.job_id, fresh.capture_id, 1),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending),
                    'a pending worker owns its immutable source even when another changed frame arrives')
                result = Result(abi=1, size=C.sizeof(Result), outcome=outcome, coverage=1,
                    selected_row=-1, selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now + 1)
                self.h.now += 2
                self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    fresh.job_id, fresh.capture_id, fresh.prefix, self.h.now, C.byref(result)))
                self.assertEqual((7, outcome, int(outcome != 0)),
                    (self.q.cycle().state, self.q.cycle().outcome, self.q.cycle().candidate_latched))
                self.no_move()
                self.assertEqual((2, 1, 0),
                    (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))
        for fault in ('upper_bound', 'strong_word'):
            with self.subTest(unsafe_safe_partial=fault):
                self.fresh()
                def unsafe(value):
                    self.safe(value)
                    slot = value.partial[0]
                    if fault == 'upper_bound':
                        slot.icon_score_exact = 0
                        slot.icon_upper_bound = .8
                    else:
                        slot.word_present = 1
                        slot.word_iou, slot.word_coverage = .82, .90
                source, _ = self.p.pending(direction=1, extra={(8, 3): 'floor'},
                                            mutate_assessment=unsafe)
                old, counts = self.q.cycle(), self.counts()
                self.assertEqual(1, self.p.observe(self.changed(source)))
                self.assertEqual((old.job_id, old.capture_id),
                    (self.q.cycle().job_id, self.q.cycle().capture_id),
                    'safe flag alone cannot give a new job to possible icon or strong target text')
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_refresh_rejects_lost_gold_item_protection_near_material_and_nonzero_motion(self):
        for fault in ('gold', 'item', 'protection', 'origin', 'target', 'near', 'new_item',
                      'motion', 'unknown_motion', 'full', 'pause'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.pending(extra={(-5, 2): 'item'}, protected=self.cross((-5, 2)))
                old, counts = self.q.cycle(), self.counts()
                latest = self.changed(source)
                if fault == 'gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault == 'item': latest.tiles[(-5, 2)] = 'floor'
                elif fault == 'protection': latest.protected.discard((-5, 1))
                elif fault == 'origin': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'target': latest.tiles[(-1, 0)] = 'dirt'
                elif fault == 'near': latest.tiles[(0, 1)] = 'dirt'
                elif fault == 'new_item': latest.tiles[(8, 3)] = 'item'
                elif fault == 'motion': latest.signature = native.translated(source, 1).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80]) * 23296
                elif fault == 'full': latest.goods = 'visible'
                latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
                self.h.now += 10_000_000
                self.h.observe(self.h.scene(1 if fault == 'pause' else 2, 2, latest, beat=True))
                if fault != 'full':
                    self.assertEqual(old.job_id, self.q.cycle().job_id)
                else:
                    self.assertEqual(1, self.q.cycle().full_seen,
                        'FULL uses its separate normal data protocol, never a refreshed PARTIAL source')
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_refresh_requires_fresh_stable_prefix_original_parent_and_control_owner(self):
        for fault in ('prefix', 'unstable', 'id', 'pre_release', 'deadline', 'cancel',
                      'foreground', 'locked', 'owner', 'unknown_synth'):
            with self.subTest(fault=fault):
                self.fresh()
                source, opened = self.pending()
                old, counts = self.q.cycle(), self.counts()
                latest = self.changed(source)
                if fault == 'deadline': self.h.now = old.continuation_deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault in ('foreground', 'locked', 'owner'):
                    self.h.tick(front=int(fault != 'foreground'), locked=int(fault == 'locked'),
                                owner=int(fault != 'owner'))
                elif fault == 'unknown_synth':
                    self.p.observe(source)
                    command = self.h.next_move(source)
                    self.h.now = max(self.h.now, command.not_before_ns)
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                    self.h.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id,
                                                                       self.h.now, -1))
                    self.h.prefix = command.id
                    counts = self.counts()
                options = ({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                           {'stable': 0} if fault == 'unstable' else
                           {'number': old.capture_id} if fault == 'id' else
                           {'start': old.release_after_ns - 1} if fault == 'pre_release' else {})
                self.p.observe(latest, **options)
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opened.id, self.h.now, 1, 0, 1))
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_repeated_same_prefix_refresh_keeps_first_parent_and_requires_each_new_result(self):
        source, _ = self.pending(extra={(9, 3): 'floor', (10, 3): 'floor'})
        parent, counts = self.q.cycle().continuation_deadline_ns, self.counts()
        for point in ((8, 3), (9, 3), (10, 3)):
            source, old, fresh = self.refresh(source, point=point)
            self.assertLessEqual(fresh.continuation_deadline_ns, parent)
            self.assertEqual(counts, self.counts())
            self.q.assess(0, 1, self.safe)
            self.assertEqual((3, 0), (self.q.cycle().state, self.q.cycle().completed_shops))
            self.no_move()
        old = self.q.cycle()
        self.h.now = parent + 1
        self.p.observe(self.changed(source, material='floor'))
        self.assertEqual(old.job_id, self.q.cycle().job_id)
        self.assertNotEqual(0, self.q.cycle().state)
        self.no_move()
        self.assertEqual(counts, self.counts())

    def test_far_refresh_does_not_consume_or_restore_old_exposed_item_once_allowance(self):
        source, _ = self.exposed_source()
        counts = self.counts()
        latest, _, _ = self.refresh(source)
        self.q.assess(0, 1, self.safe)
        old = self.q.cycle()
        exposed = self.expose(latest)
        self.assertEqual(1, self.p.observe(exposed))
        self.assert_fresh(old, counts)
        self.q.assess(0, 1, self.safe)
        changed, _, _ = self.refresh(exposed, point=(9, 3))
        self.q.assess(0, 1, self.safe)
        before = self.q.cycle()
        second = self.expose(changed, point=(-8, 2), adjacent=False)
        self.p.observe(second)
        self.assertEqual((before.job_id, 7), (self.q.cycle().job_id, self.q.cycle().state),
            'far data refresh cannot restore the old ITEM exposure allowance')
        self.no_move()

    def actual_move(self, source, command):
        before = self.h.status()
        latest = native.translated(source, command.direction)
        dx, dy = native.DIRS[command.direction]
        self.assertEqual((1, dx, dy), self.motion(source, latest, command.direction))
        a, b, entered = self.h.scene(2, 2, source), self.h.scene(2, 2, latest), observation.Entrance()
        admitted = self.lib.ng2_entered_gate(C.byref(a), C.byref(b), command.direction,
            before.x, before.y, 1, C.byref(entered))
        self.h.ack(command)
        self.assertEqual((before.inputs + 1, before.moves),
                         (self.h.status().inputs, self.h.status().moves))
        old = self.q.cycle()
        self.h.observed_result(command, latest)
        event = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, dx, dy), (event.motion, event.dx, event.dy))
        self.assertEqual((before.inputs + 1, before.moves + 1),
                         (self.h.status().inputs, self.h.status().moves))
        self.assertEqual((old.job_id + 1, 1, self.h.number, command.id),
            (self.q.cycle().job_id, self.q.cycle().pending,
             self.q.cycle().capture_id, self.q.cycle().prefix))
        if admitted:
            self.assertEqual(1, entered.valid)
            self.entrance = entered
        return latest

    def test_left_opening_two_real_left_moves_then_down_uses_current_normal_jobs(self):
        items = {(-5, 3), (-4, 3), (-3, 3)}
        protected = set().union(*(self.cross(point) for point in items))
        cells = {(x, y): 'floor' for x in range(-6, -1) for y in range(-1, 4)}
        cells.update({point: 'item' for point in items})
        source, opened = self.pending(extra=cells, protected=protected)
        self.assertEqual(3, self.h.events()[-1].motion, 'the public LEFT opening is actual DOOR_OPENED')
        self.assertEqual(1, self.p.observe(source))
        first = self.h.next_move(source)
        self.assertEqual((4, 1), (first.kind, first.direction))
        at_gate = self.actual_move(source, first)
        self.assertIsNotNone(self.entrance, 'public entered-gate proof must establish the observed opening')
        self.assertEqual('gold', at_gate.tiles[(0, 1)],
                         'DOWN is not inferred through the gate-side GOLD before moving farther inside')
        self.q.assess(0, 1, self.safe)
        changed, _, fresh = self.refresh(at_gate, point=(9, 3))
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.assertEqual(1, self.p.observe(changed))
        inside = self.h.next_move(changed)
        self.assertEqual((4, 1), (inside.kind, inside.direction))
        self.assertGreater(inside.source_capture_id, fresh.capture_id)
        interior = self.actual_move(changed, inside)
        self.q.assess(0, 1, self.safe)
        # A genuine strict MOVED starts a normal latest-source scope. This
        # further changed observation still needs classification and static.
        latest, _, newest = self.refresh(interior, point=(10, 3), material='gold')
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.assertEqual(1, self.p.observe(latest))
        down = self.h.next_move(latest)
        self.assertEqual((4, 4), (down.kind, down.direction),
                         'the ordinary observed-cell planner must turn DOWN toward the lower merchandise')
        self.assertEqual('floor', latest.tiles[(0, 1)])
        self.assertNotIn((0, 1), latest.protected)
        self.assertGreater(down.source_capture_id, newest.capture_id)
        final = self.actual_move(latest, down)
        self.q.assess(1, 1)
        self.assertEqual((1, 1, 1), (self.q.cycle().outcome,
            self.q.cycle().candidate_latched, self.q.cycle().completed_shops))
        self.assertEqual('partial', final.goods)
        self.assertEqual((5, 4, 1),
            (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opened.id,
                                                        self.h.now, 1, 0, 1))
        self.no_move()

    def test_far_floor_to_dirt_rebinds_observe_more_before_fresh_result_and_new_static(self):
        source, opened = self.pending()
        old = self.q.cycle()
        counts = (self.h.status().inputs, self.h.status().moves,
                  self.h.status().x, self.h.status().y)
        latest = deepcopy(source)
        latest.tiles[(8, 3)] = 'dirt'
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((2, 0, 0), self.motion(source, latest, 1),
                         'actual normal motion must prove static zero before testing refresh authority')
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.assert_fresh(old, counts)
        frozen = bytes(self.q.cycle()), bytes(self.h.status())
        stale = Result(abi=1, size=C.sizeof(Result), selected_row=-1, selected_partial=-1,
                       started_ns=self.h.now, finished_ns=self.h.now + 1)
        self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            old.job_id, old.capture_id, old.prefix, self.h.now))
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
            old.job_id, old.capture_id, old.prefix, self.h.now, C.byref(stale)))
        self.assertEqual(frozen, (bytes(self.q.cycle()), bytes(self.h.status())))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opened.id,
                                                        self.h.now, 1, 0, 1))
        self.q.assess(0, 1, self.safe)
        self.assertEqual((fresh.job_id, 3, 0, 0),
            (self.q.cycle().job_id, self.q.cycle().state,
             self.q.cycle().completed_shops, self.q.cycle().candidate_latched))
        self.assertEqual(0, self.h.tick()[0], 'fresh result alone is not a later static capture')
        self.assertEqual(1, self.p.observe(latest))
        command = self.h.next_move(latest)
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.source_capture_id, fresh.capture_id)
        self.assertGreater(command.id, opened.id)
        self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
        self.assertEqual(counts,
            (self.h.status().inputs, self.h.status().moves, self.h.status().x, self.h.status().y))


if __name__ == '__main__':
    unittest.main()
