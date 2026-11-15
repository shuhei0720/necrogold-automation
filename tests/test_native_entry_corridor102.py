"""TEST102 observed UP entry corridor, public C and procedural responses.

Received TEST101 source152 has a row-4 ITEM projection and a positive GOLD
rail beside an observed FLOOR corridor. It is not the old097 top-row proof:
that fixture's DIRT rail remains a rejection. These modeled callbacks do not
invent later iPhone images, classifier accuracy, or merchandise acceptance.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle094
from tests import test_native_partial_entry097 as entry


class NativeEntryCorridor102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry.NativePartialEntry097Tests.setUpClass()
        cls.lib = entry.NativePartialEntry097Tests.lib

    @classmethod
    def tearDownClass(cls):
        entry.NativePartialEntry097Tests.tearDownClass()

    def setUp(self):
        self.fresh()

    def fresh(self):
        # Delegate only the existing public-C mechanics; no old test methods
        # are inherited or selected by discovery in this new class.
        self.p = entry.NativePartialEntry097Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q

    @staticmethod
    def projection(items):
        items = set(items)
        protected = set(items)
        for x, y in items:
            protected.update((x + dx, y + dy) for dx, dy in native.DIRS.values())
        protected = {point for point in protected
                     if -11 <= point[0] <= 11 and -5 <= point[1] <= 4}
        return {point: 'item' for point in items}, protected

    def pending(self, *, side=1, items=None, corridor=True, extra=None,
                protected_extra=(), remove_protected=(), opened=True,
                opening_direction=None, outcome=0, mutate=None):
        if items is None:
            items = {(side * x, -4) for x in range(-3, 2)}
        cells, protected = self.projection(items)
        if corridor:
            # Actual152-like side=+1 includes the upper GOLD at(1,-5).
            # The new independent witness is the positive lower rail, not
            # the presence of an ITEM in row-5.
            cells.update({(side, -5): 'gold', (side, -3): 'gold',
                          (side, -2): 'gold', (side, -1): 'gold',
                          (-side, -1): 'gold', (0, -1): 'floor',
                          (0, -2): 'floor'})
        cells.update(extra or {})
        protected.update(protected_extra)
        protected.difference_update(remove_protected)
        return self.p.pending(direction=3, side=side,
            initial='gold' if corridor else 'dirt', opened=opened,
            opening_direction=opening_direction, extra=cells, protected=protected,
            outcome=outcome, safe_slots=False, mutate_assessment=mutate)

    def admitted(self):
        current = self.q.cycle()
        self.assertEqual((3, 0, 0, 1, 0),
            (current.state, current.outcome, current.status,
             current.coverage, current.completed_shops),
            'positive observed entry corridor must grant only bounded empty-UNKNOWN framing')
        self.assertEqual((0, 0, 0, 0), (current.pending, current.full_seen,
            current.candidate_latched, self.h.status().goods))
        self.assertEqual(0, self.h.tick()[0], 'admission itself is not input authority')
        return current

    def held(self, counts=None):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertNotEqual(0, self.q.cycle().state)
        self.assertEqual(0, self.h.status().restarts)
        if counts is not None:
            self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_observed_row4_corridor_gets_one_future_input_then_new_candidate_job(self):
        for side in (-1, 1):
            with self.subTest(side=side):
                self.fresh()
                terrain, opening = self.pending(side=side)
                original = self.admitted()
                self.assertFalse(any(kind == 'item' and y == -5
                    for (x, y), kind in terrain.tiles.items()))
                self.assertEqual(1, self.p.observe(terrain))
                current = self.q.cycle()
                self.assertEqual((0, 0, 0, 1, 0),
                    (current.state, current.outcome, current.status,
                     current.coverage, current.completed_shops))
                self.assertEqual((original.job_id, original.capture_id,
                                  original.continuation_deadline_ns),
                    (current.job_id, current.capture_id, current.continuation_deadline_ns))
                command = self.h.next_move(terrain)
                self.assertEqual((4, 3), (command.kind, command.direction))
                self.assertGreater(command.id, opening.id)
                self.assertGreaterEqual(command.not_before_ns - self.h.now, 50_000_000)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opening.id, command.not_before_ns, 1, 0, 1))
                before = self.h.status()
                self.h.ack(command)
                self.assertEqual((before.inputs + 1, before.moves),
                    (self.h.status().inputs, self.h.status().moves),
                    'ACK is one input and zero displacement credit')
                self.h.observed_result(command, native.translated(terrain, 3))
                latest = self.q.cycle()
                self.assertEqual((before.inputs + 1, before.moves + 1),
                    (self.h.status().inputs, self.h.status().moves))
                self.assertEqual((original.job_id + 1, 1, 0),
                    (latest.job_id, latest.pending, latest.completed_shops))
                self.assertGreater(latest.capture_id, original.capture_id)
                self.assertEqual(command.id, latest.prefix)
                self.assertEqual(0, self.h.tick()[0], 'new image must be assessed before another MOVE')
                stale = cycle094.Result(abi=1, size=C.sizeof(cycle094.Result),
                    outcome=1, coverage=1, selected_row=-1, selected_partial=-1,
                    started_ns=self.h.now, finished_ns=self.h.now)
                frozen = bytes(latest)
                self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    original.job_id, original.capture_id, original.prefix, self.h.now, C.byref(stale)))
                self.assertEqual(frozen, bytes(self.q.cycle()))
                self.q.assess(1, 1)
                self.assertEqual((1, 1, 1), (self.q.cycle().outcome,
                    self.q.cycle().candidate_latched, self.q.cycle().completed_shops))
                self.held((before.inputs + 1, before.moves + 1))

    def test_old097_row4_without_positive_gold_rail_still_holds(self):
        terrain, _ = self.pending(corridor=False)
        self.assertEqual('dirt', terrain.tiles[(1, -2)],
            'the old no_top_item fixture must retain its original DIRT rail')
        self.held((2, 1))

    def test_missing_dirt_or_stone_rail_never_grants_a_framing_step(self):
        for point in ((1, -3), (1, -2), (1, -1), (-1, -1)):
            for material in ('unknown', 'dirt', 'stone'):
                with self.subTest(point=point, material=material):
                    self.fresh()
                    terrain, _ = self.pending()
                    self.admitted()
                    changed = deepcopy(terrain)
                    if material == 'unknown': changed.tiles.pop(point, None)
                    else: changed.tiles[point] = material
                    self.p.observe(changed)
                    self.held((2, 1))

    def test_origin_destination_and_axis_floor_are_not_inferred(self):
        for point in ((0, 0), (0, -1), (0, -2)):
            for fault in ('unknown', 'item', 'protected'):
                with self.subTest(point=point, fault=fault):
                    self.fresh()
                    terrain, _ = self.pending()
                    self.admitted()
                    changed = deepcopy(terrain)
                    if fault == 'unknown': changed.tiles.pop(point, None)
                    elif fault == 'item':
                        changed.tiles[point] = 'item'; changed.protected.add(point)
                    else: changed.protected.add(point)
                    if point == (0, 0) and fault == 'unknown':
                        # The old generic scene fixture defaults origin to
                        # FLOOR; clear the actual ABI cell for this rejection.
                        self.h.now += 10_000_000
                        frame = self.h.scene(2, 2, changed, beat=True)
                        frame.tiles[5 * 23 + 11] = 0
                        self.h.observe(frame)
                    else:
                        self.p.observe(changed)
                    self.held((2, 1))

    def test_item_projection_must_explain_all_protection_without_loss(self):
        for fault in ('extra', 'missing', 'unprotected_item', 'new_item', 'old_item_loss'):
            with self.subTest(fault=fault):
                self.fresh()
                terrain, _ = self.pending()
                self.admitted()
                changed = deepcopy(terrain)
                if fault == 'extra': changed.protected.add((7, 0))
                elif fault == 'missing': changed.protected.remove((-3, -5))
                elif fault == 'unprotected_item': changed.protected.remove((-3, -4))
                elif fault == 'new_item':
                    changed.tiles[(2, -4)] = 'item'; changed.protected.add((2, -4))
                else: changed.tiles[(-3, -4)] = 'floor'
                self.p.observe(changed)
                self.held((2, 1))

    def test_source_roi_cannot_lose_potential_goods_to_viewport_or_hud(self):
        for xs in (range(-7, -2), range(1, 6)):
            with self.subTest(xs=tuple(xs)):
                self.fresh()
                self.pending(items={(x, -4) for x in xs})
                self.held((2, 1))

    def test_actual_up_opening_and_completed_unknown_domain_remain_required(self):
        for fault in ('no_open', 'wrong_direction', 'candidate', 'target',
                      'kernel', 'deadline', 'coverage', 'row', 'partial', 'safe'):
            with self.subTest(fault=fault):
                self.fresh()
                def mutate(value):
                    if fault == 'kernel': value.status = 5
                    elif fault == 'deadline': value.status = 2
                    elif fault == 'coverage': value.coverage = 0
                    elif fault == 'row': value.row_count = 1
                    elif fault == 'partial': value.partial_count = 1
                    elif fault == 'safe': value.partial_safe_no_positive = 1
                self.pending(opened=fault != 'no_open',
                    opening_direction=2 if fault == 'wrong_direction' else None,
                    outcome={'candidate': 1, 'target': 2}.get(fault, 0), mutate=mutate)
                self.held((1 if fault == 'no_open' else 2, 1))

    def test_original_horizon_prefix_static_zero_and_cancel_are_never_refreshed(self):
        for fault in ('prefix', 'unstable', 'pre_release', 'deadline', 'cancel', 'motion'):
            with self.subTest(fault=fault):
                self.fresh()
                terrain, _ = self.pending()
                original = self.admitted()
                if fault in ('prefix', 'unstable', 'pre_release'):
                    self.h.now += 10_000_000
                    options = ({'prefix': self.h.prefix + 1} if fault == 'prefix' else
                        {'stable': 0} if fault == 'unstable' else {'start': original.release_after_ns - 1})
                    self.h.observe(self.h.scene(2, 2, terrain, beat=True), **options)
                    self.assertEqual((3, original.job_id, original.continuation_deadline_ns),
                        (self.q.cycle().state, self.q.cycle().job_id,
                         self.q.cycle().continuation_deadline_ns))
                    self.assertEqual(0, self.h.tick()[0])
                    continue
                if fault == 'deadline': self.h.now = original.continuation_deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                else:
                    terrain = deepcopy(terrain)
                    terrain.signature = native.translated(terrain, 3).signature
                self.p.observe(terrain)
                self.held((2, 1))
                self.assertLessEqual(self.q.cycle().continuation_deadline_ns,
                                     original.continuation_deadline_ns)


if __name__ == '__main__':
    unittest.main()
