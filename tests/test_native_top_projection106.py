"""TEST106 latest normal job when a protected top duplicate becomes visible.

The unchanged lower row supports the projected top row. No old result or
definitely-unsent ticket can authorize moving through the changed evidence.
"""
from copy import deepcopy
import unittest

from tests import test_native_partial_refresh104 as refresh


class NativeTopProjection106Tests(unittest.TestCase):
    setUpClass = classmethod(refresh.NativePartialRefresh104Tests.setUpClass.__func__)
    tearDownClass = classmethod(refresh.NativePartialRefresh104Tests.tearDownClass.__func__)
    setUp = refresh.NativePartialRefresh104Tests.setUp
    fresh = refresh.NativePartialRefresh104Tests.fresh
    choice = refresh.NativePartialRefresh104Tests.choice
    motion = refresh.NativePartialRefresh104Tests.motion
    counts = refresh.NativePartialRefresh104Tests.counts
    no_move = refresh.NativePartialRefresh104Tests.no_move
    safe = staticmethod(refresh.NativePartialRefresh104Tests.safe)
    cross = staticmethod(refresh.NativePartialRefresh104Tests.cross)
    assert_fresh = refresh.NativePartialRefresh104Tests.assert_fresh
    actual_move = refresh.NativePartialRefresh104Tests.actual_move

    def projected_source(self):
        items = {(x, -4) for x in range(-3, 4)}
        protected = set().union(*(self.cross(point) for point in items))
        cells = {point: 'item' for point in items}
        cells.update({(-2, -5): 'floor', (-1, -5): 'dirt', (1, -5): 'dirt', (2, -5): 'floor'})
        return self.p.pending(direction=3, extra=cells, protected=protected)

    def projected(self, source):
        latest = deepcopy(source)
        for x in range(-3, 4):
            latest.tiles[(x, -5)] = 'item'
            latest.protected.update((xx, yy) for xx, yy in self.cross((x, -5)) if -5 <= yy <= 4)
        return latest

    def test_new_top_projection_retires_reserved_credit_and_classifies_latest_before_up(self):
        source, opened = self.projected_source()
        self.assertEqual(1, self.p.observe(source))
        ticket = self.h.next_move(source)
        old, counts = self.q.cycle(), self.counts()
        latest = self.projected(source)
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((2, 0, 0), self.motion(source, latest, 3))
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.assert_fresh(old, counts)
        retired = next(e for e in self.h.events() if e.command.id == ticket.id)
        self.assertEqual((3, 0, bytes(ticket)), (retired.outcome, retired.begin_ns, bytes(retired.command)))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now, 1, 0, 1))
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.assertEqual(1, self.p.observe(latest))
        new = self.h.next_move(latest)
        self.assertEqual((4, 3), (new.kind, new.direction))
        self.assertGreater(new.source_capture_id, fresh.capture_id)
        self.assertLessEqual(new.deadline_ns, old.continuation_deadline_ns)
        self.actual_move(latest, new)
        self.assertEqual((counts[0]+1, counts[1]+1), self.counts()[:2])
        self.assertEqual((new.id, fresh.job_id+1, 1),
            (self.q.cycle().prefix, self.q.cycle().job_id, self.q.cycle().pending))

    def test_projection_requires_the_unchanged_supported_lower_row_and_explained_halo(self):
        for fault in ('lower', 'gold', 'stone', 'door', 'old_item', 'mask_loss',
                      'mask_extra', 'near', 'moved', 'unknown_motion', 'prefix', 'expired', 'cancel'):
            with self.subTest(fault=fault):
                self.fresh();source, _ = self.projected_source()
                self.p.observe(source);ticket = self.h.next_move(source)
                old, counts = self.q.cycle(), self.counts()
                latest = self.projected(source)
                if fault == 'lower': latest.tiles[(-2, -4)] = 'floor'
                elif fault == 'gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault in ('stone', 'door'): latest.tiles[(0, -5)] = fault
                elif fault == 'old_item': latest.tiles[(3, -4)] = 'dirt'
                elif fault == 'mask_loss': latest.protected.discard((-3, -4))
                elif fault == 'mask_extra': latest.protected.add((10, 4))
                elif fault == 'near': latest.tiles[(1, -2)] = 'stone'
                elif fault == 'moved':
                    from tests import test_native_controller as native
                    latest.signature = native.translated(source, 3).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80]) * 23296
                elif fault == 'expired': self.h.now = old.continuation_deadline_ns+1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
                self.p.observe(latest, **({'prefix': self.h.prefix+1} if fault == 'prefix' else {}))
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.no_move();self.assertEqual(counts, self.counts())

    def test_new_target_candidate_and_missing_independent_zero_hold_after_the_new_job(self):
        for outcome in (1, 2, 0):
            with self.subTest(outcome=outcome):
                self.fresh();source, _ = self.projected_source();old, counts = self.q.cycle(), self.counts()
                latest = self.projected(source);self.p.observe(latest)
                fresh = self.assert_fresh(old, counts)
                self.q.assess(outcome, 1, self.safe if outcome == 0 else None)
                if outcome:
                    self.assertEqual((fresh.job_id, 7, 1),
                        (self.q.cycle().job_id, self.q.cycle().state, self.q.cycle().candidate_latched))
                else:
                    changed = deepcopy(latest);changed.signature = bytes([80]) * 23296
                    self.p.observe(changed)
                    self.assertEqual((fresh.job_id, 3), (self.q.cycle().job_id, self.q.cycle().state))
                self.no_move();self.assertEqual(counts, self.counts())

    def test_projection_does_not_restore_the_one_use_exposed_item_allowance(self):
        source, _ = self.projected_source()
        # The pre-existing one-use path first observes a separate remote item.
        latest = deepcopy(source);latest.tiles[(8, 3)] = 'item'
        latest.protected.update(self.cross((8, 3)))
        # Source was STONE here, so use an ordinary same-prefix data refresh
        # first to bind a positively observed FLOOR, preserving the first D.
        floor = deepcopy(source);floor.tiles[(8, 3)] = 'floor'
        original, counts = self.q.cycle(), self.counts()
        self.p.observe(floor);first = self.assert_fresh(original, counts)
        self.q.assess(0, 1, self.safe)
        self.p.observe(latest);second = self.assert_fresh(first, counts)
        self.q.assess(0, 1, self.safe)
        projected = self.projected(latest)
        self.p.observe(projected)
        self.assertEqual(second.job_id, self.q.cycle().job_id)
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, original.continuation_deadline_ns)
        self.no_move();self.assertEqual(counts, self.counts())


if __name__ == '__main__':
    unittest.main()
