"""TEST104 lower merchandise needs its full observation band, public C.

Every Scene, clock, typed worker result and later response is procedural. This
test does not replay missing phone frames or certify actual Ring accuracy.
Existing first-DOWN candidate coverage remains in its original test unchanged.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_observation072 as observation
from tests import test_native_partial_refresh104 as refresh
from tests import test_native_offer_coverage104 as pixels
from tests import test_native_ring_bank094 as bank
from tests.test_native_stop099 import stop_detail


class NativeLowerObservation104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        refresh.NativePartialRefresh104Tests.setUpClass()
        cls.lib = refresh.NativePartialRefresh104Tests.lib

    @classmethod
    def tearDownClass(cls):
        refresh.NativePartialRefresh104Tests.tearDownClass()

    def setUp(self):
        self.f = refresh.NativePartialRefresh104Tests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.h, self.q = self.f.h, self.f.q

    def exact_mask(self, items):
        protected = set().union(*(self.f.cross(point) for point in items))
        return {p for p in protected if -11 <= p[0] <= 11 and -5 <= p[1] <= 4}

    def lower_source(self, broad=False):
        items = {(x, 4) for x in range(-8, -1)} if broad else {(-5, 3), (-4, 3), (-3, 3)}
        cells = {(x, y): 'floor' for x in range(-6, -1) for y in range(-1, 5)}
        cells.update({point: 'item' for point in items})
        return self.f.pending(extra=cells, protected=self.exact_mask(items))

    def assess_partial(self, terrain, *, full=False, mutate=None):
        items = sorted(point for point, kind in terrain.tiles.items() if kind == 'item')
        self.assertIn(len(items), (3, 7))
        def normal(value):
            value.partial_safe_no_positive = int(not full)
            value.partial_count = len(items)
            value.selected_partial = 0
            for index, (x, y) in enumerate(items):
                slot = value.partial[index]
                slot.cx, slot.sy, slot.slot = 448 + 36 * x, 207 + 36 * y - 48, 0
                slot.icon_score = slot.icon_upper_bound = .1
                slot.icon_score_exact = 1
                slot.icon_box[:] = (slot.cx - 16, slot.sy + 35, 32, 28)
                slot.word_present = 0
                slot.word_iou = slot.word_coverage = 0
            if full:
                self.assertEqual(3, len(items))
                value.row_count, value.selected_row, value.selected_partial = 1, 0, -1
                row = value.rows[0]
                row.left, row.sy, row.word_slot = 448 + 36 * items[0][0], 207 + 36 * items[0][1] - 48, -1
                for i, slot in enumerate(row.slots):
                    slot.cx, slot.sy, slot.slot = row.left + 36 * i, row.sy, i
                    slot.icon_score = slot.icon_upper_bound = .1
                    slot.icon_score_exact = 1
                    slot.icon_box[:] = (slot.cx - 16, slot.sy + 35, 32, 28)
            if mutate:
                mutate(value)
        return self.q.assess(0, 1, normal)

    def move(self, source, command, *, full=False, refine=None):
        before, old = self.h.status(), self.q.cycle()
        latest = native.translated(source, command.direction)
        if refine is not None:
            # A new procedural Perception response resolves broad aliases,
            # and positively observes price floors newly inside the viewport.
            for point, kind in list(latest.tiles.items()):
                if kind == 'item' and point not in refine:
                    latest.tiles[point] = 'floor'
            for x, y in refine:
                latest.tiles[(x, y)] = 'item'
                latest.tiles[(x, y + 1)] = 'floor'
        latest.protected = self.exact_mask({p for p, k in latest.tiles.items() if k == 'item'})
        latest.goods = 'visible' if full else 'partial'
        dx, dy = native.DIRS[command.direction]
        self.assertEqual((1, dx, dy), self.f.motion(source, latest, command.direction),
                         'new projection/protection is recomputed, but actual strict MOVED is still mandatory')
        self.h.ack(command)
        self.assertEqual((before.inputs + 1, before.moves),
                         (self.h.status().inputs, self.h.status().moves))
        self.h.observed_result(command, latest)
        event = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, dx, dy), (event.motion, event.dx, event.dy))
        self.assertEqual((before.inputs + 1, before.moves + 1),
                         (self.h.status().inputs, self.h.status().moves))
        self.assertEqual((old.job_id + 1, 1, self.h.number, command.id),
            (self.q.cycle().job_id, self.q.cycle().pending,
             self.q.cycle().capture_id, self.q.cycle().prefix))
        return latest

    def reach_lower(self, broad=False):
        source, opening = self.lower_source(broad)
        for direction in (1, 1, 4):
            self.assertEqual(1, self.f.p.observe(source))
            command = self.h.next_move(source)
            self.assertEqual((4, direction), (command.kind, command.direction))
            source = (self.move(source, command) if direction == 4 else
                      self.f.actual_move(source, command))
            if direction != 4:
                self.assess_partial(source)
        self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))
        return source, opening, command, self.q.cycle()

    def down_ticket(self, terrain, parent):
        actual = self.diagnostic_choice(terrain)
        self.assertEqual(1, self.f.p.observe(terrain))
        self.assertIn(self.q.cycle().state, (0, 3))
        command = self.h.next_move(terrain)
        self.assertEqual((4, 4), (command.kind, command.direction), f'ordinary Nav={actual}')
        self.assertGreater(command.source_capture_id, self.q.cycle().capture_id)
        self.assertLessEqual(command.deadline_ns, parent)
        return command

    def complete_and_restart(self):
        scene = native.Scene.from_buffer_copy(bytes(self.h._last_fixture_scene))
        self.assertEqual(2, scene.goods)
        temporary = tempfile.TemporaryDirectory(prefix='lower-observation-ring104-')
        self.addCleanup(temporary.cleanup)
        ring = bank.NativeRingBank094Tests.build_library(native.CORE / 'NG2Ring.c', Path(temporary.name) / 'ring.so')
        status, produced = pixels.normal_assess(ring, pixels.shop_pixels(left=339, sy=195), scene, mode=2)
        self.assertEqual((0, 0, 3, 2, 9),
            (status, produced.status, produced.outcome, produced.coverage, produced.certificate.policy_version),
            'the ordinary producer must actually certify the consistent row1 Scene and pixels')
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        result, proof = cycle.Result.from_buffer_copy(bytes(produced)), cycle.Result.from_buffer_copy(bytes(produced))
        proof.started_ns = proof.finished_ns = 0
        result.started_ns, result.finished_ns = self.h.now, self.h.now + 1
        normalized = cycle.Result.from_buffer_copy(bytes(result))
        normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(proof), bytes(normalized), 'only producer clocks are normalized')
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        self.assertEqual((3, 0, 1),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().completed_shops))
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        waiting = self.q.cycle()
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id + 1, 0), (self.q.cycle().level_id, self.q.cycle().state))

    def diagnostic_choice(self, terrain):
        # Read the real public planner with the entered-gate output already
        # established from public source/strict MOVED callbacks. No selector,
        # private Controller field or fabricated DOWN decision is used.
        visits = (C.c_uint16 * 1089)()
        visits[16 * 33 + 16] = 1
        x = y = 0
        for event in self.h.events():
            if event.motion == 1:
                x += event.dx
                y += event.dy
                visits[(y + 16) * 33 + x + 16] += 1
        frame, choice = self.h.scene(2, 2, terrain, beat=True), observation.Decision()
        entrance = self.f.entrance or observation.Entrance()
        accepted = self.lib.ng2_choose(C.byref(frame), x, y, visits, len(visits),
                                       C.byref(entrance), C.byref(choice))
        return accepted, tuple(getattr(choice, key) for key, _ in choice._fields_)

    def band(self, terrain):
        items = sorted(point for point, kind in terrain.tiles.items() if kind == 'item')
        self.assertEqual(3, len(items))
        self.assertEqual(1, len({y for _, y in items}))
        self.assertEqual([items[0][0] + i for i in range(3)], [x for x, _ in items])
        # Canonical item center is sy+48. The existing full B strip is the
        # fixed 180x67 domain [left-54, sy+24], not a one-icon observation.
        left, sy = 448 + 36 * items[0][0], 207 + 36 * items[0][1] - 48
        return left - 54, sy + 24, left - 54 + 180, sy + 24 + 67

    def test_safe_partial_after_first_down_requires_second_down_before_whole_lower_band(self):
        source, opening = self.lower_source()
        self.assertEqual((1, 3), (opening.direction, self.h.events()[-1].motion))
        self.assertEqual(1, self.f.p.observe(source))
        first = self.h.next_move(source)
        self.assertEqual((4, 1), (first.kind, first.direction))
        at_gate = self.f.actual_move(source, first)
        self.assertIsNotNone(self.f.entrance)
        self.assess_partial(at_gate)
        self.assertEqual(1, self.f.p.observe(at_gate))
        second = self.h.next_move(at_gate)
        self.assertEqual((4, 1), (second.kind, second.direction))
        interior = self.f.actual_move(at_gate, second)
        self.assess_partial(interior)
        self.assertEqual(1, self.f.p.observe(interior))
        first_down = self.h.next_move(interior)
        self.assertEqual((4, 4), (first_down.kind, first_down.direction))
        lower = self.move(interior, first_down)
        self.assertEqual((5, 4, 1),
            (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        self.assertTrue(all(y == 2 for (x, y), kind in lower.tiles.items() if kind == 'item'))
        self.assertGreater(self.band(lower)[3], 315,
            'the first DOWN still leaves the lower edge of the whole product band beyond the central viewport')
        self.assertEqual(('floor', 'floor'), (lower.tiles[(0, 0)], lower.tiles[(0, 1)]))
        self.assertFalse({(0, 0), (0, 1)} & lower.protected)
        items = {point for point, kind in lower.tiles.items() if kind == 'item'}
        exact = set().union(*(self.f.cross(point) for point in items))
        exact = {point for point in exact if -11 <= point[0] <= 11 and -5 <= point[1] <= 4}
        self.assertEqual(exact, lower.protected)
        self.assertEqual((2, 0, 0), self.f.motion(lower, lower, 4))
        normal_job = self.q.cycle()
        self.assertEqual((1, 1, self.h.number, first_down.id),
            (normal_job.pending, normal_job.partial, normal_job.capture_id, normal_job.prefix))
        self.assess_partial(lower)
        self.assertEqual((3, 0, 0), (self.q.cycle().state,
            self.q.cycle().completed_shops, self.q.cycle().candidate_latched))
        self.assertEqual(0, self.h.tick()[0], 'a fresh SAFE UNKNOWN result is not input authority')
        choice = self.diagnostic_choice(lower)
        self.assertEqual(1, self.f.p.observe(lower))
        self.assertIn(self.q.cycle().state, (0, 3),
            'the isolated lower observation mode may remain OBSERVE_MORE after its static proof')
        self.assertEqual((0, 0),
            (self.q.cycle().status, self.h.status().reason),
            f'eligible lower goods remain incomplete after the first DOWN; actual public Nav={choice}')
        further = self.h.next_move(lower)
        self.assertEqual((4, 4), (further.kind, further.direction),
                         f'a fresh observed FLOOR step must continue the lower observation; actual Nav={choice}')
        self.assertGreater(further.id, first_down.id)
        self.assertGreater(further.source_capture_id, normal_job.capture_id)
        self.assertLessEqual(further.deadline_ns, normal_job.continuation_deadline_ns)
        self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, first_down.id,
                                                        self.h.now, 1, 0, 1))
        latest = self.move(lower, further, full=True)
        self.assertTrue(all(y == 1 for (x, y), kind in latest.tiles.items() if kind == 'item'))
        left, top, right, bottom = self.band(latest)
        self.assertTrue(143 <= left < right <= 663 and 45 <= top < bottom <= 315)
        self.assertEqual((6, 5, 1),
            (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        self.assertEqual((1, 0, self.h.number, further.id),
            (self.q.cycle().pending, self.q.cycle().partial,
             self.q.cycle().capture_id, self.q.cycle().prefix))
        self.complete_and_restart()

    def test_seven_item_projection_requires_geometric_two_downs_and_fresh_refinement(self):
        for refined in (False, True):
            with self.subTest(refined=refined):
                self.setUp()
                lower, _, _, job = self.reach_lower(broad=True)
                items = {p for p, k in lower.tiles.items() if k == 'item'}
                self.assertEqual({(x, 3) for x in range(-6, 1)}, items)
                self.assertEqual(self.exact_mask(items), lower.protected)
                result = self.assess_partial(lower)
                bottom = max([207 + 36 * y + 61 for _, y in items] +
                             [result.partial[i].sy + 115 for i in range(result.partial_count)])
                self.assertEqual(2, (bottom - 315 + 35) // 36)
                first = self.down_ticket(lower, job.continuation_deadline_ns)
                projected = self.move(lower, first, full=refined,
                    refine={(-3, 2), (-2, 2), (-1, 2)} if refined else None)
                self.assess_partial(projected, full=refined)
                if not refined:
                    self.assertIn((0, 1), projected.protected)
                    self.f.p.observe(projected)
                    ready, command = self.h.tick()
                    self.assertFalse(ready and command.kind == 4,
                                     'a broad projection still protects the real next destination')
                    self.assertEqual((6, 5), (self.h.status().inputs, self.h.status().moves))
                    continue
                self.assertEqual('floor', projected.tiles[(0, 1)])
                self.assertNotIn((0, 1), projected.protected)
                second = self.down_ticket(projected, job.continuation_deadline_ns)
                self.assertGreater(second.id, first.id)
                latest = self.move(projected, second, full=True)
                self.assertEqual({(-3, 1), (-2, 1), (-1, 1)},
                                 {p for p, k in latest.tiles.items() if k == 'item'})
                self.assertEqual((7, 6), (self.h.status().inputs, self.h.status().moves))
                self.complete_and_restart()

    def test_unproved_direct_or_queued_full_bridge_never_mints_down_from_later_self_zero(self):
        for queued in (False, True):
            with self.subTest(queued=queued):
                self.setUp()
                source, _, _, original = self.reach_lower()
                self.assess_partial(source)
                if queued:
                    changed = self.f.changed(source, point=(10, 2))
                    self.assertEqual((2, 0, 0), self.f.motion(source, changed, 4))
                    self.assertEqual(1, self.f.p.observe(changed))
                    self.assertEqual((original.job_id + 1, 1),
                        (self.q.cycle().job_id, self.q.cycle().pending))
                    source = changed
                before = self.q.cycle()
                full = deepcopy(source)
                full.goods = 'visible'
                full.signature = bytes(255 - value for value in source.signature)
                self.assertEqual((0, 0, 0), self.f.motion(source, full, 4),
                    'the previous source-to-FULL bridge must actually remain UNKNOWN')
                self.assertEqual((2, 0, 0), self.f.motion(full, full, 4),
                    'the new rich FULL texture has its own strict self-zero, which cannot replace the missing bridge')
                self.assertEqual(1, self.f.p.observe(full))
                full_id = self.h.number
                if queued:
                    self.assertEqual((before.job_id, before.capture_id, 1),
                        (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending),
                        'queued FULL cannot retire the current normal PARTIAL worker')
                    self.assess_partial(source)
                fresh = self.q.cycle()
                self.assertEqual((before.job_id + 1, full_id, 1, 0, 1),
                    (fresh.job_id, fresh.capture_id, fresh.pending, fresh.partial, fresh.full_seen),
                    'unproved movement bridge still permits a new data job for positive/negative classification')
                self.assertLessEqual(fresh.continuation_deadline_ns, original.continuation_deadline_ns)
                self.assess_partial(full, full=True)
                self.assertEqual(1, self.f.p.observe(full))
                self.assertEqual(7, self.q.cycle().state,
                    'UNKNOWN after an unproved source-to-FULL bridge must stay HELD even after new-source self-zero')
                detail = stop_detail(self.lib, self.h.engine)
                self.assertEqual((1, 3, 1, 11, before.capture_id, before.capture_id, full_id, full_id),
                    (detail.valid, detail.stage, detail.reason, detail.validation,
                     detail.source_capture_id, detail.anchor_capture_id,
                     detail.observed_capture_id, detail.last_comparison_capture_id))
                self.assertLessEqual(detail.deadline_ns, original.continuation_deadline_ns)
                frozen = bytes(detail)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual((5, 4, 0),
                    (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))
                self.assertEqual(frozen, bytes(stop_detail(self.lib, self.h.engine)))
        # An unproved world bridge forbids a continuation MOVE. It does not
        # discard independently classified visible data or demote positives.
        for outcome in (1, 2, 3):
            with self.subTest(independent_current_data=outcome):
                self.setUp()
                source, _, _, _ = self.reach_lower()
                self.assess_partial(source)
                full = deepcopy(source)
                full.goods = 'visible'
                full.signature = bytes(255 - value for value in source.signature)
                if outcome == 3:
                    for point, kind in list(full.tiles.items()):
                        if kind == 'item': full.tiles[point] = 'floor'
                    for point in {(-3, 1), (-2, 1), (-1, 1)}:
                        full.tiles[point] = 'item'
                        full.tiles[(point[0], 2)] = 'floor'
                    full.protected = self.exact_mask({p for p, kind in full.tiles.items() if kind == 'item'})
                self.assertEqual((0, 0, 0), self.f.motion(source, full, 4))
                self.f.p.observe(full)
                self.assertEqual(1, self.q.cycle().pending)
                if outcome == 3:
                    self.complete_and_restart()
                else:
                    self.assess_partial(full, full=True, mutate=lambda value: setattr(value, 'outcome', outcome))
                    self.assertEqual((outcome, 1, 7),
                        (self.q.cycle().outcome, self.q.cycle().candidate_latched, self.q.cycle().state))
                self.assertEqual(0, stop_detail(self.lib, self.h.engine).valid,
                    'candidate/independent valid negative is not reported as a frozen UNKNOWN bridge fault')

    def assert_no_local_down(self, terrain):
        # Permit unchanged general navigation when the separate local proof
        # is ineligible, but never begin it or accept a local DOWN by accident.
        for _ in range(40):
            ready, command = self.h.tick()
            self.assertFalse(ready and command.kind == 4 and command.direction == 4)
            if ready or self.q.cycle().state == 7 or self.h.status().terminal or self.h.status().reason not in (0, 1):
                return
            self.h.now += 20_000_000
            self.f.p.observe(terrain)

    def test_full_unknown_and_authenticated_hud_coverage_need_the_local_down(self):
        for authenticated in (False, True):
            with self.subTest(authenticated=authenticated):
                self.setUp()
                lower, _, _, original = self.reach_lower()
                self.assess_partial(lower)
                full = deepcopy(lower)
                full.goods = 'visible'
                self.f.p.observe(full)
                job = self.q.cycle()
                self.assertEqual((original.job_id + 1, 1, 0, 1),
                    (job.job_id, job.pending, job.partial, job.full_seen))
                self.assertLessEqual(job.continuation_deadline_ns, original.continuation_deadline_ns)
                if authenticated:
                    temporary = tempfile.TemporaryDirectory(prefix='lower-authenticated104-')
                    self.addCleanup(temporary.cleanup)
                    ring = bank.NativeRingBank094Tests.build_library(native.CORE / 'NG2Ring.c', Path(temporary.name) / 'ring.so')
                    source = bank.complete_shop(bank.bank_data()['entries'][:3], auth=bank.auth_data())
                    rgba = bytearray(bytes((0, 0, 0, 255)) * (896 * 414))
                    dx, dy = 339 - 360, 231 - 120
                    for y in range(414 - dy):
                        rgba[4 * ((y + dy) * 896):4 * ((y + dy) * 896 + 896 + dx)] = \
                            source[4 * (y * 896 - dx):4 * (y * 896 + 896)]
                    scene = native.Scene.from_buffer_copy(bytes(self.h._last_fixture_scene))
                    status, produced = pixels.normal_assess(ring, bytes(rgba), scene, mode=2)
                    self.assertEqual((0, 0, 0, 1), (status, produced.status, produced.outcome, produced.coverage))
                    self.assertTrue(produced.certificate.failure_flags & 512,
                                    'existing BOUNDS guard must keep authenticated row2 coverage UNKNOWN')
                    self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        job.job_id, job.capture_id, job.prefix, self.h.now))
                    value = cycle.Result.from_buffer_copy(bytes(produced))
                    proof = cycle.Result.from_buffer_copy(bytes(produced)); proof.started_ns = proof.finished_ns = 0
                    value.started_ns, value.finished_ns = self.h.now, self.h.now + 1
                    normalized = cycle.Result.from_buffer_copy(bytes(value)); normalized.started_ns = normalized.finished_ns = 0
                    self.assertEqual(bytes(proof), bytes(normalized))
                    self.h.now += 2
                    self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                        job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
                else:
                    self.assess_partial(full, full=True)
                down = self.down_ticket(full, original.continuation_deadline_ns)
                framed = self.move(full, down, full=True)
                if authenticated:
                    self.complete_and_restart()
                else:
                    self.assess_partial(framed, full=True)
                    self.assertEqual(7, self.q.cycle().state)
                    self.f.p.observe(framed)
                    self.assert_no_local_down(framed)
                    self.assertEqual((6, 5), (self.h.status().inputs, self.h.status().moves))

    def test_candidate_target_upper_word_and_unfit_union_do_not_gain_local_down(self):
        for fault in ('candidate', 'target', 'upper', 'word', 'pose', 'bottom', 'left'):
            with self.subTest(fault=fault):
                self.setUp()
                lower, _, _, _ = self.reach_lower()
                def mutate(value):
                    if fault in ('candidate', 'target'): value.outcome = {'candidate': 1, 'target': 2}[fault]
                    elif fault == 'upper':
                        value.partial[0].icon_score_exact = 0
                        value.partial[0].icon_upper_bound = .8
                    elif fault == 'word':
                        value.partial[0].word_present = 1
                        value.partial[0].word_iou, value.partial[0].word_coverage = .82, .90
                    elif fault == 'pose': value.partial[0].cx = value.partial[0].sy = 0
                    elif fault == 'bottom': value.partial[0].sy = 400
                    else: value.partial[0].cx = 160
                self.assess_partial(lower, mutate=mutate)
                self.f.p.observe(lower)
                self.assert_no_local_down(lower)
                if fault in ('candidate', 'target'):
                    self.assertEqual(1, self.q.cycle().candidate_latched)
                    self.assertEqual(7, self.q.cycle().state)
                self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))

    def test_static_floor_exact_projection_and_motion_rejections_have_frozen_diagnostics(self):
        for fault in ('origin', 'destination', 'unknown_destination', 'origin_mask', 'destination_mask',
                      'missing_mask', 'extra_mask', 'item_loss', 'motion'):
            with self.subTest(fault=fault):
                self.setUp()
                lower, _, _, job = self.reach_lower()
                self.assess_partial(lower)
                changed = deepcopy(lower)
                if fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'destination': changed.tiles[(0, 1)] = 'dirt'
                elif fault == 'unknown_destination': changed.tiles.pop((0, 1))
                elif fault == 'origin_mask': changed.protected.add((0, 0))
                elif fault == 'destination_mask': changed.protected.add((0, 1))
                elif fault == 'missing_mask': changed.protected.discard((-3, 2))
                elif fault == 'extra_mask': changed.protected.add((-8, 3))
                elif fault == 'item_loss': changed.tiles[(-1, 2)] = 'floor'
                else: changed.signature = bytes(255 - v for v in lower.signature)
                self.assertNotEqual((lower.tiles, lower.protected, lower.signature),
                                    (changed.tiles, changed.protected, changed.signature))
                self.f.p.observe(changed)
                out = stop_detail(self.lib, self.h.engine)
                self.assertEqual((1, 3, 17, 11 if fault == 'motion' else 9,
                                  job.capture_id, job.capture_id, self.h.number, self.h.number),
                    (out.valid, out.stage, out.reason, out.validation, out.source_capture_id,
                     out.anchor_capture_id, out.observed_capture_id, out.last_comparison_capture_id))
                self.assertEqual(job.continuation_deadline_ns, out.deadline_ns)
                frozen = bytes(out)
                self.assert_no_local_down(changed)
                self.assertEqual(frozen, bytes(stop_detail(self.lib, self.h.engine)))
                self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))

    def test_current_prefix_independent_capture_and_control_guards_do_not_reuse_tickets(self):
        for fault in ('id', 'prefix', 'unstable', 'pre_release', 'cancel', 'foreground', 'locked', 'owner', 'unknown_synth'):
            with self.subTest(fault=fault):
                self.setUp()
                lower, _, old, job = self.reach_lower()
                self.assess_partial(lower)
                current = self.q.cycle()
                if fault in ('foreground', 'locked', 'owner', 'unknown_synth'):
                    ticket = self.down_ticket(lower, job.continuation_deadline_ns)
                    self.h.now = max(self.h.now, ticket.not_before_ns)
                    if fault == 'unknown_synth':
                        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now, 1, 0, 1))
                        self.h.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, ticket.id, self.h.now, -1))
                        self.h.prefix = ticket.id
                        self.f.p.observe(lower)
                        self.assertEqual(4, self.h.status().input_state)
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now, 1, 0, 1))
                    else:
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now,
                            int(fault != 'foreground'), int(fault == 'locked'), int(fault != 'owner')))
                else:
                    if fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                    options = ({'number': current.capture_id} if fault == 'id' else
                               {'prefix': self.h.prefix + 1} if fault == 'prefix' else
                               {'stable': 0} if fault == 'unstable' else
                               {'start': current.release_after_ns - 1} if fault == 'pre_release' else {})
                    self.f.p.observe(lower, **options)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, old.id, self.h.now, 1, 0, 1))
                self.assertEqual((6 if fault == 'unknown_synth' else 5, 4),
                                 (self.h.status().inputs, self.h.status().moves))

    def test_far_refresh_and_expiry_preserve_first_parent_and_never_reset_spent_count(self):
        for reserved in (False, True):
            with self.subTest(reserved=reserved):
                self.setUp()
                lower, _, _, job = self.reach_lower()
                self.assess_partial(lower)
                ticket = self.down_ticket(lower, job.continuation_deadline_ns) if reserved else None
                changed = self.f.changed(lower, point=(10, 2))
                self.assertEqual((2, 0, 0), self.f.motion(lower, changed, 4))
                self.f.p.observe(changed)
                fresh = self.q.cycle()
                self.assertEqual((job.job_id + 1, self.h.number, 1),
                    (fresh.job_id, fresh.capture_id, fresh.pending))
                self.assertLessEqual(fresh.continuation_deadline_ns, job.continuation_deadline_ns)
                if ticket:
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, ticket.id, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.h.tick()[0])
                self.assess_partial(changed)
                issued = self.down_ticket(changed, job.continuation_deadline_ns)
                self.h.now = job.continuation_deadline_ns + 1
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, issued.id, self.h.now, 1, 0, 1))
                self.f.p.observe(changed)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))
        self.setUp()
        lower, _, _, job = self.reach_lower()
        self.assess_partial(lower)
        down = self.down_ticket(lower, job.continuation_deadline_ns)
        framed = self.move(lower, down)
        self.assess_partial(framed)
        self.assertEqual(7, self.q.cycle().state)
        self.f.p.observe(self.f.changed(framed, point=(10, 1)))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertEqual((6, 5), (self.h.status().inputs, self.h.status().moves))
        for outcome in (0, 1, 2):
            with self.subTest(pending_worker_after_parent=outcome):
                self.setUp()
                lower, _, _, original = self.reach_lower()
                self.assess_partial(lower)
                self.h.now = original.continuation_deadline_ns - 20_000_000
                changed = self.f.changed(lower, point=(10, 2))
                self.f.p.observe(changed)
                job = self.q.cycle()
                self.assertEqual((original.job_id + 1, 1), (job.job_id, job.pending))
                self.assertLessEqual(job.continuation_deadline_ns, original.continuation_deadline_ns)
                self.assertGreater(job.deadline_ns, original.continuation_deadline_ns + 2)
                self.h.now = original.continuation_deadline_ns + 1
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual((job.job_id, job.capture_id, 1),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending),
                    'the observation parent cannot discard a current worker before its independent data deadline')
                self.assess_partial(changed, mutate=lambda value: setattr(value, 'outcome', outcome))
                self.assertEqual((outcome, int(outcome != 0), 7),
                    (self.q.cycle().outcome, self.q.cycle().candidate_latched, self.q.cycle().state))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
                self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))
        self.setUp()
        lower, _, _, original = self.reach_lower()
        self.assess_partial(lower)
        self.h.now = original.continuation_deadline_ns - 20_000_000
        changed = self.f.changed(lower, point=(10, 2))
        self.f.p.observe(changed)
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        own_deadline = self.q.cycle().deadline_ns
        self.h.now = own_deadline + 1
        self.h.tick()
        self.assertEqual((2, 0, 0),
            (self.q.cycle().status, self.q.cycle().pending, self.q.cycle().candidate_latched))

    def test_pending_full_fifo_preserves_old_candidate_before_latest_source(self):
        for started in (False, True):
            for outcome in (1, 2):
                with self.subTest(started=started, outcome=outcome):
                    self.setUp()
                    lower, _, _, _ = self.reach_lower()
                    self.assess_partial(lower)
                    changed = self.f.changed(lower, point=(10, 2))
                    self.f.p.observe(changed)
                    job = self.q.cycle()
                    if started:
                        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                            job.job_id, job.capture_id, job.prefix, self.h.now))
                    full = deepcopy(changed); full.goods = 'visible'
                    self.f.p.observe(full)
                    self.assertEqual((job.job_id, job.capture_id, 1),
                        (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
                    if started:
                        value = cycle.Result(abi=1, size=C.sizeof(cycle.Result), outcome=outcome, coverage=1,
                            selected_row=-1, selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now + 1)
                        self.h.now += 2
                        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
                    else:
                        self.assess_partial(changed, mutate=lambda value: setattr(value, 'outcome', outcome))
                    self.assertEqual((job.job_id, job.capture_id, 1, 0),
                        (self.q.cycle().job_id, self.q.cycle().capture_id,
                         self.q.cycle().candidate_latched, self.q.cycle().pending))
                    ready, command = self.h.tick()
                    self.assertFalse(ready and command.kind in (3, 4))
                    self.assertEqual((5, 4), (self.h.status().inputs, self.h.status().moves))


if __name__ == '__main__':
    unittest.main()
