"""TEST107 clipped top roles composed with the existing quiet residual.

Procedural public C/worker callbacks exercise the recorded failure conditions.
No original pixels or unrecorded future phone scenes are embedded here.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_refresh104 as refresh
from tests import test_native_cycle094 as cycle
from tests import test_native_offer_controller105 as offers_controller
from tests import test_native_offer_coverage104 as offers
from tests import test_native_ring_bank094 as bank


class NativePartialRoles107Tests(unittest.TestCase):
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

    def source(self, *, doubled=False, halo=False, shift=0, extra_item=False, **options):
        left = -1+shift
        items = {(x, -4) for x in range(left, left+5)}
        if doubled:
            items |= {(x, -5) for x in range(left, left+5)}
        if extra_item:
            items.add((8, 3))
        mask = set().union(*(self.cross(point) for point in items))
        mask = {(x, y) for x, y in mask if -5 <= y <= 4}
        cells = {point: 'item' for point in items}
        if not doubled:
            cells.update({(left, -5): 'gold', (left+2, -5): 'dirt', (left+3, -5): 'floor'})
        if halo:
            cells.pop((left+1, -5), None)
        cells[(5, 3)] = 'dirt'
        source, opened = self.p.pending(direction=3, extra=cells, protected=mask, **options)
        self.assertEqual((3, 5, 0, -1, 1), self.choice(source))
        self.assertEqual((3, 0, 0),
            (self.q.cycle().state, self.q.cycle().pending, self.q.cycle().status))
        return source, opened

    def grow(self, source):
        latest = deepcopy(source)
        for x in sorted(x for (x, y), kind in source.tiles.items() if y == -4 and kind == 'item'):
            latest.tiles[(x, -5)] = 'item'
            latest.protected.update((xx, yy) for xx, yy in self.cross((x, -5)) if -5 <= yy <= 4)
        latest.tiles.pop((5, 3), None)
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    @staticmethod
    def shrink(source):
        latest = deepcopy(source)
        xs = sorted(x for (x, y), kind in source.tiles.items() if y == -4 and kind == 'item')
        for x, kind in zip(xs, (None, 'floor', 'dirt', 'floor', None)):
            if kind is None:
                latest.tiles.pop((x, -5), None)
            else:
                latest.tiles[(x, -5)] = kind
        latest.protected.difference_update({(xs[0]-1, -5), (xs[-1]+1, -5)})
        latest.tiles[(1, -2)] = 'floor'
        latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def qualified(self, source, latest):
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((2, 0, 0), self.motion(source, latest, 3))
        return self.q.cycle(), self.counts()

    def test_growth_over_supported_top_gold_composes_with_far_palette_before_new_job_and_move(self):
        source, _ = self.source()
        self.p.observe(source)
        retired = self.h.next_move(source)
        latest = self.grow(source)
        old, counts = self.qualified(source, latest)
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.assert_fresh(old, counts)
        previous = next(e for e in self.h.events() if e.command.id == retired.id)
        self.assertEqual((3, 0, bytes(retired)),
            (previous.outcome, previous.begin_ns, bytes(previous.command)))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, retired.id, self.h.now, 1, 0, 1))
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.p.observe(latest)
        command = self.h.next_move(latest)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.source_capture_id, fresh.capture_id)
        self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
        self.actual_move(latest, command)
        self.assertEqual((counts[0]+1, counts[1]+1), self.counts()[:2])
        self.q.assess(0, 1, self.safe)
        self.assertEqual((fresh.job_id+1, command.id, 0),
            (self.q.cycle().job_id, self.q.cycle().prefix, self.q.cycle().pending))

    def test_top_alias_reduction_and_old_shielded_palette_share_one_static_proof(self):
        source, _ = self.source(doubled=True)
        self.p.observe(source)
        old, counts = self.q.cycle(), self.counts()
        latest = self.shrink(source)
        self.qualified(source, latest)
        self.assertEqual(1, self.p.observe(latest))
        current = self.q.cycle()
        self.assertEqual((0, 0, 0),
            (current.state, self.h.status().reason, self.h.status().terminal))
        self.assertEqual((old.job_id, old.capture_id, old.continuation_deadline_ns),
            (current.job_id, current.capture_id, current.continuation_deadline_ns))
        self.assertEqual(counts, self.counts())
        command = self.h.next_move(latest)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)

    def test_remote_protected_non_item_top_exposure_reclassifies_once_without_old_credit(self):
        source, _ = self.source(halo=True)
        self.p.observe(source)
        ticket = self.h.next_move(source)
        latest = deepcopy(source)
        latest.tiles[(0, -5)] = 'floor'
        old, counts = self.qualified(source, latest)
        self.assertEqual(source.protected, latest.protected)
        self.assertEqual(1, self.p.observe(latest))
        fresh = self.assert_fresh(old, counts)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now, 1, 0, 1))
        self.q.assess(0, 1, self.safe)
        self.no_move()
        second = deepcopy(latest)
        second.tiles[(0, -5)] = 'unknown'
        self.p.observe(second)
        self.assertEqual(fresh.job_id, self.q.cycle().job_id,
            'the original one-use exposed-item allowance is not restored by data binding')
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, old.continuation_deadline_ns)
        self.no_move()
        self.assertEqual(counts, self.counts())

    def test_new_job_target_candidate_and_missing_independent_zero_hold(self):
        for outcome in (1, 2, 0):
            with self.subTest(outcome=outcome):
                self.fresh()
                source, _ = self.source()
                latest = self.grow(source)
                old, counts = self.qualified(source, latest)
                self.p.observe(latest)
                fresh = self.assert_fresh(old, counts)
                self.q.assess(outcome, 1, self.safe if outcome == 0 else None)
                if outcome:
                    self.assertEqual((fresh.job_id, 7, 1),
                        (self.q.cycle().job_id, self.q.cycle().state, self.q.cycle().candidate_latched))
                else:
                    unknown = deepcopy(latest)
                    unknown.signature = bytes([80])*23296
                    self.p.observe(unknown)
                    self.assertEqual((fresh.job_id, 3), (self.q.cycle().job_id, self.q.cycle().state))
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_role_support_geometry_authority_and_original_deadline_are_required(self):
        for fault in ('lower_item', 'mask_extra', 'mask_loss', 'other_item', 'both_other_item', 'other_gold',
                      'strong_word', 'near', 'stone', 'door', 'motion', 'unknown_motion', 'prefix', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.fresh()
                options = {'extra_item': True} if fault == 'both_other_item' else {}
                if fault == 'strong_word':
                    def strong(value):
                        value.partial[0].word_present = 1
                        value.partial[0].word_iou, value.partial[0].word_coverage = .83, .95
                    options['mutate_assessment'] = strong
                source, _ = self.source(**options)
                old, counts = self.q.cycle(), self.counts()
                latest = self.grow(source)
                if fault == 'lower_item': latest.tiles[(0, -4)] = 'floor'
                elif fault == 'mask_extra': latest.protected.add((10, 3))
                elif fault == 'mask_loss': latest.protected.discard((0, -4))
                elif fault == 'other_item':
                    latest.tiles[(8, 3)] = 'item'
                    latest.protected.update(self.cross((8, 3)))
                elif fault == 'other_gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault == 'near': latest.tiles[(0, -1)] = 'dirt'
                elif fault in ('stone', 'door'): latest.tiles[(0, -5)] = fault
                elif fault == 'motion': latest.signature = native.translated(source, 3).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80])*23296
                elif fault == 'deadline': self.h.now = old.continuation_deadline_ns+1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                latest.gold = {p for p, kind in latest.tiles.items() if kind == 'gold'}
                self.p.observe(latest, **({'prefix': self.h.prefix+1} if fault == 'prefix' else {}))
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.no_move()
                self.assertEqual(counts, self.counts())

    def test_supported_roles_translate_to_the_other_observed_top_columns(self):
        source, _ = self.source(shift=-3)
        latest = self.grow(source)
        old, counts = self.qualified(source, latest)
        self.p.observe(latest)
        fresh = self.assert_fresh(old, counts)
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.p.observe(latest)
        command = self.h.next_move(latest)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.source_capture_id, fresh.capture_id)
        self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
        self.assertEqual(counts, self.counts())

    def test_mixed_refresh_real_up_and_current_normal_producer_reach_durable_restart(self):
        source, _ = self.source()
        latest = self.grow(source)
        old, counts = self.qualified(source, latest)
        self.p.observe(latest)
        fresh = self.assert_fresh(old, counts)
        self.q.assess(0, 1, self.safe)
        self.no_move()
        self.p.observe(latest)
        command = self.h.next_move(latest)
        self.assertEqual((4, 3), (command.kind, command.direction))
        # A procedural later Perception response resolves duplicate projections
        # to the three now observed offers and their actual supporting floors.
        # It still must pass the unmodified public strict MOVED assessment.
        full = native.translated(latest, 3)
        items = {(-1, -3), (0, -3), (1, -3)}
        for point, kind in list(full.tiles.items()):
            if kind == 'item' and point not in items:
                full.tiles[point] = 'floor'
        for x, y in items:
            full.tiles[(x, y)] = 'item'
            full.tiles[(x, y+1)] = 'floor'
        for point in ((-2, -3), (2, -3)):
            full.tiles[point] = 'floor'
        full.protected = set().union(*(self.cross(point) for point in items))
        full.goods = 'visible'
        self.assertEqual((1, 0, -1), self.motion(latest, full, 3))
        self.h.ack(command)
        self.assertEqual((counts[0]+1, counts[1]), self.counts()[:2],
            'synth ACK is not a physical entry')
        self.h.observed_result(command, full)
        event = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
        self.assertEqual((counts[0]+1, counts[1]+1), self.counts()[:2])
        job = self.q.cycle()
        self.assertEqual((fresh.job_id+1, 1, command.id, 0),
            (job.job_id, job.pending, job.prefix, job.partial))
        scene = native.Scene.from_buffer_copy(bytes(self.h._last_fixture_scene))
        temporary = tempfile.TemporaryDirectory(prefix='partial-roles-ring107-')
        self.addCleanup(temporary.cleanup)
        ring = bank.NativeRingBank094Tests.build_library(native.CORE/'NG2Ring.c',
                                                       Path(temporary.name)/'ring.so')
        code, result = offers.normal_assess(ring, offers.shop_pixels(left=411, sy=51), scene, mode=2)
        self.assertEqual((0, 0, 3, 2, 9),
            (code, result.status, result.outcome, result.coverage, result.certificate.policy_version))
        self.assertEqual((3, 3, 0),
            (result.certificate.observed_items, result.certificate.observed_prices,
             result.certificate.failure_flags))
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        original = cycle.Result.from_buffer_copy(bytes(result))
        original.started_ns = original.finished_ns = 0
        result.started_ns, result.finished_ns = self.h.now, self.h.now+1
        normalized = cycle.Result.from_buffer_copy(bytes(result))
        normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(original), bytes(normalized),
            'the normal producer is preserved apart from its procedural worker clock')
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        offers_controller.NativeOfferController105Tests.restart_after_durable_intent(self, job)


if __name__ == '__main__':
    unittest.main()
