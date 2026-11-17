"""TEST112 upper side door: each observed step to the lower offer row.

Scenes, clocks and later floor refinements are procedural public-C responses.
The received empty lower source motivates admission, not future phone arrival.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_fade100 as opened
from tests import test_native_structural_cycle096 as structural


class NativeUpperEntry112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        opened.NativeOpenedFade100Tests.setUpClass()
        cls.lib = opened.NativeOpenedFade100Tests.lib

    @classmethod
    def tearDownClass(cls):
        opened.NativeOpenedFade100Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib = self.lib
        self.addCleanup(self.q.doCleanups)
        self.p = opened.NativeOpenedFade100Tests(methodName='runTest')
        self.p.lib = self.lib
        self.addCleanup(self.p.doCleanups)

    @staticmethod
    def cross(items):
        return {(x+a, y+b) for x, y in items for a, b in ((0, 0), *native.DIRS.values())
                if -11 <= x+a <= 11 and -5 <= y+b <= 4}

    @staticmethod
    def mirror(point, direction):
        x, y = point
        return (x, y) if direction == 1 else (-x, y)

    def pending(self, direction=1, fault=None, result_mutate=None):
        h = self.p.harness()
        self.h = self.q.h = h
        cells = {(x, y): 'floor' for x in range(-6, 1) for y in range(-1, 5)}
        cells.update({(-1, 0): 'door', (-1, -1): 'gold', (-1, 1): 'gold',
                      (-7, -2): 'gold', (-7, -1): 'gold', (-7, 0): 'gold', (-7, 1): 'gold',
                      (-6, -2): 'gold', (-5, -2): 'gold', (-4, -2): 'gold',
                      (-2, 0): 'dirt', (0, 1): 'dirt',
                      (-8, -3): 'stone', (5, 2): 'stone', (8, 3): 'stone'})
        dx, dy = native.DIRS[direction]
        initial = {(self.mirror(p, direction)[0]+dx, self.mirror(p, direction)[1]+dy): kind
                   for p, kind in cells.items()}
        initial[(0, 0)] = 'floor'
        terrain = native.textured(initial)
        h.fit(terrain)
        first = h.next_move(terrain)
        self.assertEqual(direction, first.direction)
        h.ack(first)
        terrain = native.translated(terrain, direction)
        h.observed_result(first, terrain)
        opening = h.next_move(terrain)
        self.assertEqual(direction, opening.direction)
        h.ack(opening)
        source = deepcopy(terrain)
        source.tiles[(dx, dy)] = 'floor'
        source.goods = 'partial'
        items = {self.mirror((x, 3), direction) for x in range(-7, 0)}
        for point in items:
            source.tiles[point] = 'item'
        source.protected = self.cross(items)
        if fault == 'missing_bracket':
            source.tiles.pop(self.mirror((-1, -1), direction), None)
        elif fault == 'missing_roof':
            source.tiles.pop(self.mirror((-5, -2), direction), None)
        elif fault == 'extra_item':
            source.tiles[(5, -3)] = 'item'
            source.protected = self.cross(items | {(5, -3)})
        elif fault == 'missing_mask':
            source.protected.remove(self.mirror((-4, 2), direction))
        elif fault == 'dirty_next':
            source.tiles[(dx, dy)] = 'dirt'
        elif fault == 'protected_next':
            source.protected.add((dx, dy))
        elif fault == 'no_opening':
            source.tiles[(dx, dy)] = 'door'
        h.observed_result(opening, source)
        if not fault:
            self.assertEqual((2, 3, 0, 0),
                (h.events()[-1].outcome, h.events()[-1].motion, h.events()[-1].dx, h.events()[-1].dy))
        pending = self.q.cycle()
        self.assertEqual(1, pending.pending)
        # Deforming the opening response can correctly revoke authority
        # before a worker is admissible. Those rejection cases must still
        # forbid new movement; they are not fabricated classified sources.
        if pending.capture_id and not h.status().input_state:
            self.q.assess(0, 1, result_mutate)
        else:
            self.assertIsNotNone(fault)
        return source, opening, pending

    def independent(self, source, delay=10_000_000):
        self.h.now += delay
        return self.h.observe_actual(self.h.scene(2, 2, source, beat=True))

    def ticket(self, source):
        self.assertEqual(1, self.independent(source))
        command = self.h.next_move(source)
        self.assertEqual(4, command.kind)
        return command

    def unknown(self, source, slots=False):
        def fill(value):
            if not slots:
                return
            items = sorted(point for point, kind in source.tiles.items() if kind == 'item')
            # Only actual non-HUD returned probes are present. The third
            # lower icon can still be hidden; its potential is not absence.
            visible = [(x, y) for x, y in items if x < 0][:2]
            value.partial_safe_no_positive = int(source.goods == 'partial')
            value.partial_count = len(visible)
            value.selected_partial = 0 if visible else -1
            for i, (x, y) in enumerate(visible):
                slot = value.partial[i]
                slot.cx, slot.sy = 448 + 36*x, 207 + 36*y - 48
                slot.icon_score = slot.icon_upper_bound = .1
                slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
        return self.q.assess(0, 1, fill)

    def step(self, source, command, *, reveal_floor=False, refine=False, refine_row=3, full=False, observed_at=None):
        before, parent = self.h.status(), self.q.cycle()
        self.h.ack(command)
        self.assertEqual(before.moves, self.h.status().moves, 'synth ACK gives no displacement')
        latest = native.translated(source, command.direction)
        if reveal_floor:
            latest.tiles[native.DIRS[command.direction]] = 'floor'
        if refine:
            # A new procedural response resolves the seven sign-origin
            # aliases to three real offers in the same original world row.
            keep = {(-3, refine_row), (-2, refine_row), (-1, refine_row)}
            for point, kind in list(latest.tiles.items()):
                if kind == 'item' and point not in keep:
                    latest.tiles[point] = 'floor'
            for point in keep:
                latest.tiles[point] = 'item'
            latest.protected = self.cross(keep)
        if full:
            latest.goods = 'visible'
        self.assertEqual((1, *native.DIRS[command.direction]), self.h.motion(source, latest, command.direction))
        if observed_at is not None:
            self.h.now = max(self.h.now, observed_at)
        self.h.observed_result(command, latest)
        event = next(row for row in self.h.events() if row.command.id == command.id)
        self.assertEqual((1, *native.DIRS[command.direction]), (event.motion, event.dx, event.dy))
        self.assertEqual((before.inputs+1, before.moves+1), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual((parent.job_id+1, 1, self.h.number, command.id),
            (self.q.cycle().job_id, self.q.cycle().pending, self.q.cycle().capture_id, self.q.cycle().prefix))
        self.assertEqual(parent.hold_started_ns, self.q.cycle().hold_started_ns)
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, parent.continuation_deadline_ns)
        return latest

    def four_steps(self, final_full=True, late_final=False):
        source, _, parent = self.pending()
        targets = []
        for index, direction in enumerate((1, 1, 4, 4)):
            command = self.ticket(source)
            self.assertEqual(direction, command.direction)
            self.assertGreater(self.h.status().beat_period_ns, 0)
            targets.append(command.target_ns)
            source = self.step(source, command, reveal_floor=index == 0,
                               refine=index == 1, full=final_full and index == 3,
                               observed_at=parent.continuation_deadline_ns-60_000_000
                               if late_final and index == 3 else None)
            if index != 3:
                self.unknown(source, slots=index >= 1)
        self.assertTrue(all(b-a == native.PERIOD for a, b in zip(targets, targets[1:])),
                        'fresh public HUD tracking must permit every beat without a new two-second fit')
        self.assertLess(self.h.now, parent.continuation_deadline_ns)
        return source, parent

    def complete(self, source):
        from tests import test_native_offer_coverage104 as pixels
        from tests import test_native_ring_bank094 as bank
        from pathlib import Path
        import tempfile
        temporary = tempfile.TemporaryDirectory(prefix='upper-entry112-ring-')
        self.addCleanup(temporary.cleanup)
        ring = bank.NativeRingBank094Tests.build_library(native.CORE/'NG2Ring.c', Path(temporary.name)/'ring.so')
        scene = self.h.scene(2, 2, source, beat=True)
        status, result = pixels.normal_assess(ring, pixels.shop_pixels(left=339, sy=195), scene, mode=2)
        self.assertEqual((0, 0, 3, 2, 9),
            (status, result.status, result.outcome, result.coverage, result.certificate.policy_version))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        original = cycle.Result.from_buffer_copy(bytes(result)); original.started_ns = original.finished_ns = 0
        result.started_ns, result.finished_ns = self.h.now, self.h.now+1
        normalized = cycle.Result.from_buffer_copy(bytes(result)); normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(original), bytes(normalized), 'normal producer evidence changes only procedural clocks')
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        return job

    def test_empty_lower_opening_observes_only_the_fresh_safe_entry_step(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                source, opening, parent = self.pending(direction)
                self.assertEqual((3, 1, 0, 0),
                    (self.q.cycle().state, self.q.cycle().partial,
                     self.q.cycle().full_seen, self.q.cycle().completed_shops),
                    'empty lower-side merchandise needs a distinct observation wait, not immediate HELD')
                self.assertEqual(0, self.h.tick()[0], 'a worker result never supplies the independent static frame')
                command = self.ticket(source)
                self.assertEqual(direction, command.direction)
                self.assertGreater(command.id, opening.id)
                self.assertGreater(command.source_capture_id, parent.capture_id)
                self.assertEqual((2, 1, 1), (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
                self.assertLessEqual(self.h.motion_wait().deadline_ns, parent.continuation_deadline_ns)
                self.assertEqual(parent.hold_started_ns, self.q.cycle().hold_started_ns)
                self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
                self.assertEqual(0, self.q.cycle().pending)


    def test_each_safe_step_tracks_live_model_until_all_goods_then_durable_restart(self):
        source, parent = self.four_steps()
        self.assertEqual((6, 5, 1), (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        job = self.complete(source)
        self.assertEqual((3, 0, 1), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().completed_shops))
        self.assertEqual(0, self.q.durable())
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        waiting = self.q.cycle()
        self.assertEqual(1, self.h.status().restarts)
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id+1, 0), (self.q.cycle().level_id, self.q.cycle().state))

    def test_seven_partial_aliases_remain_until_first_down_reveals_the_real_full_row(self):
        # The normal procedural RGBA Perception factory keeps all seven
        # sign-origin aliases through H2. Only D1 reveals three FULL items.
        source, _, parent = self.pending()
        for index, direction in enumerate((1, 1, 4, 4)):
            command = self.ticket(source)
            self.assertEqual(direction, command.direction)
            source = self.step(source, command, reveal_floor=index == 0,
                refine=index == 2, refine_row=2, full=index >= 2)
            count = sum(kind == 'item' for kind in source.tiles.values())
            self.assertEqual(7 if index < 2 else 3, count)
            self.assertEqual(parent.hold_started_ns, self.q.cycle().hold_started_ns)
            self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
            if index != 3:
                self.unknown(source, slots=index >= 1)
        self.complete(source)
        self.assertEqual((3, 0, 1),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().completed_shops))
        self.assertEqual((6, 5, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_normal_nonempty_partial_potential_may_still_extend_into_hud_before_down(self):
        source, _, _ = self.pending()
        source = self.step(source, self.ticket(source), reveal_floor=True)
        self.unknown(source)
        source = self.step(source, self.ticket(source), refine=True)
        self.unknown(source, slots=True)
        self.assertEqual(1, self.q.cycle().partial)
        self.assertGreater(267+115, 315)
        down = self.ticket(source)
        self.assertEqual((4, 4), (down.kind, down.direction),
                         'unknown future potential is not an observed HUD collision or complete coverage')

    def test_geometry_projection_and_first_safe_floor_are_independent_requirements(self):
        for fault in ('missing_bracket', 'missing_roof', 'extra_item', 'missing_mask',
                      'dirty_next', 'protected_next', 'no_opening'):
            with self.subTest(fault=fault):
                source, _, _ = self.pending(fault=fault)
                counts = self.h.status().inputs, self.h.status().moves
                self.independent(source)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_unobserved_second_floor_waits_without_guessing_or_restoring_root(self):
        source, _, parent = self.pending()
        source = self.step(source, self.ticket(source))
        self.unknown(source)
        self.assertEqual('dirt', source.tiles[(-1, 0)])
        for _ in range(3):
            self.independent(source)
            ready, command = self.h.tick()
            self.assertFalse(ready and command.kind == 4)
        self.assertEqual((3, 2), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
        self.h.now = parent.continuation_deadline_ns+1
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(0, self.h.status().restarts)

    def test_target_candidate_and_late_hint_preempt_later_negative(self):
        for outcome, late in ((1, False), (2, False), (0, True)):
            with self.subTest(outcome=outcome, late=late):
                source, _, parent = self.pending()
                source = self.step(source, self.ticket(source), reveal_floor=True)
                job = self.q.cycle()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now))
                value = cycle.Result(abi=1, size=C.sizeof(cycle.Result), outcome=outcome, coverage=1,
                    selected_row=-1, selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now+1)
                self.h.now += 2
                if late:
                    value.status = 2
                    value.partial_count = 1
                    value.partial[0].icon_upper_bound = .8
                    self.h.now = max(self.h.now, job.deadline_ns+1)
                    value.finished_ns = self.h.now
                self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
                self.assertEqual(1, self.q.cycle().candidate_latched)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(0, self.h.status().restarts)

    def test_extra_world_item_or_lost_gold_invalidates_movement_stickily(self):
        for fault in ('item', 'gold'):
            with self.subTest(fault=fault):
                source, _, parent = self.pending()
                changed = deepcopy(source)
                if fault == 'item':
                    changed.tiles[(5, -3)] = 'item'
                    changed.protected = self.cross({p for p, kind in changed.tiles.items() if kind == 'item'})
                else:
                    changed.tiles[(-5, -2)] = 'floor'
                self.independent(changed)
                if self.q.cycle().pending:
                    self.unknown(changed)
                self.independent(source)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_four_started_inputs_exhaust_observation_without_general_navigation(self):
        source, parent = self.four_steps(final_full=False)
        self.unknown(source, slots=True)
        self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.independent(source)
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual((6, 5, 0), (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_prefix_cancel_root_and_live_phase_revoke_new_permission(self):
        for fault in ('prefix', 'cancel', 'root', 'phase'):
            with self.subTest(fault=fault):
                source, _, parent = self.pending()
                if fault == 'prefix':
                    self.h.now += 10_000_000
                    self.h.observe_actual(self.h.scene(2, 2, source, beat=True), prefix=self.h.prefix+1)
                elif fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now+1, 2)
                elif fault == 'root':
                    self.h.now = parent.continuation_deadline_ns+1
                else:
                    self.h.now += 10_000_000
                    frame = self.h.scene(2, 2, source, beat=True)
                    frame.beat_remaining = (frame.beat_remaining+.2)%1
                    self.h.observe_actual(frame)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual((2, 1), (self.h.status().inputs, self.h.status().moves))



    def test_fresh_queued_full_after_fourth_input_or_move_parent_expiry_still_keeps_candidate(self):
        for expired in (False, True):
            with self.subTest(expired=expired):
                source, parent = self.four_steps(final_full=False, late_final=expired)
                old = self.q.cycle()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    old.job_id, old.capture_id, old.prefix, self.h.now))
                started = self.h.now
                full = deepcopy(source); full.goods = 'visible'
                self.independent(full, delay=20_000_000)
                queued = self.h.number
                self.assertEqual(old.capture_id, self.q.cycle().capture_id)
                self.assertEqual(queued, self.q.cycle().queued_capture_id)
                self.h.now = parent.continuation_deadline_ns+10_000_000 if expired else self.h.now+2
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(old.job_id, self.q.cycle().job_id, 'old worker drains before source/job switch')
                result = cycle.Result(abi=1, size=C.sizeof(cycle.Result), coverage=1,
                    selected_row=-1, selected_partial=-1, started_ns=started, finished_ns=self.h.now)
                self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                    old.job_id, old.capture_id, old.prefix, self.h.now, C.byref(result)))
                self.assertEqual((old.job_id+1, queued, 1),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
                self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
                self.assertEqual(parent.hold_started_ns, self.q.cycle().hold_started_ns)
                self.q.assess(2, 1)
                self.assertEqual(1, self.q.cycle().candidate_latched)
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual((6, 5, 0), (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_remaining_live_schedule_budget_never_renews_the_fixed_parent(self):
        source, _, parent = self.pending()
        self.h.now = parent.continuation_deadline_ns-1_000_000_000
        self.independent(source)
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(parent.hold_started_ns, self.q.cycle().hold_started_ns)
        self.assertEqual(parent.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
        self.assertEqual((2, 1, 0), (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))

    def test_started_unknown_move_never_resends_or_credits_a_new_step(self):
        source, _, parent = self.pending()
        command = self.ticket(source)
        before = self.h.status()
        self.h.ack(command)
        unknown = deepcopy(source)
        unknown.signature = bytes(len(source.signature))
        self.assertEqual((0, 0, 0), self.h.motion(source, unknown, command.direction))
        first = command.target_ns+80_000_002
        for attempt in range(8):
            self.h.now = max(self.h.now+native.PERIOD//10+2, first)
            if attempt == 7:
                self.h.now = max(self.h.now, first+native.PERIOD+2)
            self.h.observe_actual(self.h.scene(2, 2, unknown, beat=True))
        self.assertEqual(before.moves, self.h.status().moves)
        self.assertEqual(before.inputs+1, self.h.status().inputs)
        self.assertEqual(0, self.h.status().restarts)
        self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(command.id, [e for e in self.h.events() if e.command.kind == 4][-1].command.id)

    def test_other_normally_certified_shop_row_is_not_the_original_merchandise(self):
        from tests import test_native_offer_coverage104 as pixels
        from tests import test_native_ring_bank094 as bank
        from pathlib import Path
        import tempfile
        source, _, parent = self.pending()
        foreign = deepcopy(source)
        for point, kind in list(foreign.tiles.items()):
            if kind == 'item': foreign.tiles[point] = 'floor'
        items = {(-3, -3), (-2, -3), (-1, -3)}
        for point in items:
            foreign.tiles[point] = 'item'
            foreign.tiles[(point[0], point[1]+1)] = 'floor'
        foreign.tiles[(-4, -3)] = foreign.tiles[(0, -3)] = 'floor'
        foreign.protected = self.cross(items); foreign.goods = 'visible'
        self.independent(foreign)
        self.assertEqual(1, self.q.cycle().pending, 'the current raw view remains eligible for DATA-only positive detection')
        temporary = tempfile.TemporaryDirectory(prefix='upper-entry112-foreign-')
        self.addCleanup(temporary.cleanup)
        ring = bank.NativeRingBank094Tests.build_library(native.CORE/'NG2Ring.c', Path(temporary.name)/'ring.so')
        scene = self.h.scene(2, 2, foreign, beat=True)
        status, produced = pixels.normal_assess(ring, pixels.shop_pixels(left=339, sy=43), scene, mode=2)
        self.assertEqual((0, 0, 3, 2, 9),
            (status, produced.status, produced.outcome, produced.coverage, produced.certificate.policy_version))
        # Prove this normal certificate is valid to the ordinary public C,
        # so the episode's original physical-row binding is a separate gate.
        ordinary = cycle.NativeCycle094Tests(methodName='runTest')
        ordinary.setUp(); self.addCleanup(ordinary.doCleanups)
        self.assertEqual(1, ordinary.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        normal = ordinary.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(ordinary.h.engine,
            normal.job_id, normal.capture_id, normal.prefix, ordinary.h.now))
        proof = cycle.Result.from_buffer_copy(bytes(produced))
        proof.started_ns, proof.finished_ns = ordinary.h.now, ordinary.h.now+1
        ordinary.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(ordinary.h.engine,
            normal.job_id, normal.capture_id, normal.prefix, ordinary.h.now, C.byref(proof)))
        self.assertEqual((3, 0), (ordinary.cycle().outcome, ordinary.cycle().status))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        produced.started_ns, produced.finished_ns = self.h.now, self.h.now+1
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(produced)))
        self.assertEqual((0, 3, 7), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
        self.assertEqual(0, self.h.status().restarts)
        self.assertNotEqual(4, self.h.tick()[1].kind)



if __name__ == '__main__':
    unittest.main()
