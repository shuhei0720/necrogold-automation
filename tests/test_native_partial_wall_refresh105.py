"""TEST105 data refresh for observed GOLD under an unchanged goods halo.

TEST104 run3 retained all goods cells/protection and the local UP footprint,
while remote protected UNKNOWN/DOOR became GOLD. Procedural public callbacks
below exercise job ownership, not later phone/game arrival or Ring accuracy.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_refresh104 as refresh104


class NativePartialWallRefresh105Tests(unittest.TestCase):
    # Reuse public-C helpers without rediscovering the old module's tests.
    setUpClass = classmethod(refresh104.NativePartialRefresh104Tests.setUpClass.__func__)
    tearDownClass = classmethod(refresh104.NativePartialRefresh104Tests.tearDownClass.__func__)
    setUp = refresh104.NativePartialRefresh104Tests.setUp
    fresh = refresh104.NativePartialRefresh104Tests.fresh
    choice = refresh104.NativePartialRefresh104Tests.choice
    motion = refresh104.NativePartialRefresh104Tests.motion
    counts = refresh104.NativePartialRefresh104Tests.counts
    no_move = refresh104.NativePartialRefresh104Tests.no_move
    safe = staticmethod(refresh104.NativePartialRefresh104Tests.safe)
    cross = staticmethod(refresh104.NativePartialRefresh104Tests.cross)
    assert_fresh = refresh104.NativePartialRefresh104Tests.assert_fresh
    actual_move = refresh104.NativePartialRefresh104Tests.actual_move
    def wall_source(self, old_wall='unknown', **options):
        items = {(x, -4) for x in range(-3, 2)}
        protected = set().union(*(self.cross(point) for point in items))
        cells = {point: 'item' for point in items}
        cells.update({(1, -3): 'door', (3, 4): 'stone'})
        if old_wall != 'unknown': cells[(1, -5)] = old_wall
        source, opened = self.p.pending(direction=3, extra=cells, protected=protected, **options)
        acknowledged = options.get('opened', True)
        self.assertEqual((3, 0, 0, 1 + acknowledged, 1, int(acknowledged)),
            (self.q.cycle().state, self.q.cycle().pending, self.q.cycle().status,
             self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        self.assertEqual(3 if acknowledged else 1, self.h.events()[-1].motion)
        return source, opened

    @staticmethod
    def observed_wall(source):
        latest = deepcopy(source)
        latest.tiles.update({(1, -5): 'gold', (1, -3): 'gold', (3, 4): 'dirt'})
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def test_remote_observed_gold_retires_job_and_waits_for_latest_result_and_independent_zero(self):
        source, opened = self.wall_source()
        old, counts = self.q.cycle(), self.counts()
        latest = self.observed_wall(source)
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((3, 5, 0, -1, 1), self.choice(source))
        self.assertEqual((2, 0, 0), self.motion(source, latest, 3))
        self.assertEqual(source.protected, latest.protected)
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.assert_fresh(old, counts)
        self.q.assess(0, 1, self.safe)
        self.assertEqual((fresh.job_id, 3, 0), (self.q.cycle().job_id,
            self.q.cycle().state, self.q.cycle().completed_shops))
        self.no_move()
        self.assertEqual(1, self.p.observe(latest))
        new = self.h.next_move(latest)
        self.assertEqual((4, 3), (new.kind, new.direction))
        self.assertGreater(new.id, opened.id)
        self.assertGreater(new.source_capture_id, fresh.capture_id)
        self.assertLessEqual(new.deadline_ns, old.continuation_deadline_ns)
        self.assertEqual(counts, self.counts())
        at_gate = self.actual_move(latest, new)
        self.assertEqual((new.id, fresh.job_id + 1, 1, self.h.number),
            (self.q.cycle().prefix, self.q.cycle().job_id,
             self.q.cycle().pending, self.q.cycle().capture_id))
        self.assertEqual((counts[0] + 1, counts[1] + 1, counts[2], counts[3] - 1), self.counts())
        self.q.assess(0, 1, self.safe)
        self.assertEqual((fresh.job_id + 1, new.id, 0),
            (self.q.cycle().job_id, self.q.cycle().prefix, self.q.cycle().pending))
        self.assertEqual('partial', at_gate.goods)

    def test_new_protected_wall_withdraws_credit_and_any_definitely_unsent_ticket(self):
        for stage in ('credit', 'reserved'):
            with self.subTest(stage=stage):
                self.fresh()
                source, _ = self.wall_source()
                self.assertEqual(1, self.p.observe(source))
                ticket = self.h.next_move(source) if stage == 'reserved' else None
                old, counts = self.q.cycle(), self.counts()
                self.assertEqual(1, self.p.observe(self.observed_wall(source)))
                self.assert_fresh(old, counts)
                self.assertEqual((0, 0),
                    (self.h.status().input_state, self.h.status().current_command_id))
                if ticket:
                    retired = next(e for e in self.h.events() if e.command.id == ticket.id)
                    self.assertEqual((0, 3, bytes(ticket)),
                        (retired.begin_ns, retired.outcome, bytes(retired.command)))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        ticket.id, max(self.h.now, ticket.not_before_ns), 1, 0, 1))

    def test_wall_refresh_rejects_other_protected_changes_and_missing_original_authority(self):
        faults = ('protected_floor', 'protected_dirt', 'protected_stone', 'protected_door',
                  'item', 'mask', 'lost_gold', 'near', 'motion', 'unknown_motion',
                  'old_dirt', 'old_stone', 'no_open_ack', 'other_open_ack', 'prefix', 'expired')
        for fault in faults:
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.wall_source(**(
                    {'opened': False} if fault == 'no_open_ack' else
                    {'opening_direction': 2} if fault == 'other_open_ack' else
                    {'old_wall': fault.removeprefix('old_')} if fault.startswith('old_') else {}))
                old, counts = self.q.cycle(), self.counts()
                latest = self.observed_wall(source)
                if fault.startswith('protected_'):
                    latest.tiles[(1, -5)] = fault.removeprefix('protected_')
                elif fault == 'item': latest.tiles[(1, -5)] = 'item'
                elif fault == 'mask': latest.protected.discard((1, -5))
                elif fault == 'lost_gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault == 'near': latest.tiles[(1, -2)] = 'gold'
                elif fault == 'motion': latest.signature = native.translated(source, 3).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80]) * 23296
                elif fault == 'expired': self.h.now = old.continuation_deadline_ns + 1
                latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
                self.p.observe(latest, **({'prefix': self.h.prefix + 1} if fault == 'prefix' else {}))
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_latest_positive_candidate_and_unproved_zero_never_resume_old_move(self):
        for outcome in (1, 2, 0):
            with self.subTest(outcome=outcome):
                self.fresh()
                source, _ = self.wall_source()
                old, counts = self.q.cycle(), self.counts()
                latest = self.observed_wall(source)
                self.p.observe(latest)
                fresh = self.assert_fresh(old, counts)
                self.q.assess(outcome, 1, self.safe if outcome == 0 else None)
                if outcome:
                    self.assertEqual((fresh.job_id, 7, 1), (self.q.cycle().job_id,
                        self.q.cycle().state, self.q.cycle().candidate_latched))
                else:
                    not_zero = deepcopy(latest)
                    not_zero.signature = bytes([80]) * 23296
                    self.p.observe(not_zero)
                    self.assertEqual((fresh.job_id, 3),
                        (self.q.cycle().job_id, self.q.cycle().state))
                self.no_move()
                self.assertEqual(counts, self.counts())


if __name__ == '__main__':
    unittest.main()
