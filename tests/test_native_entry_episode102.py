"""TEST102 A2: at most two newly proved entry observations, public C.

All Scenes, clocks, classification results and subsequent responses are
procedural. They verify finite input/source ownership, not future iPhone
arrival, image accuracy or complete merchandise visibility.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_entry_corridor102 as corridor
from tests import test_native_partial_framing097 as top
from tests import test_native_full_framing101 as horizontal
from tests import test_native_shop_coverage102 as pixels102
from tests import test_native_ring_bank094 as bank


class NativeEntryEpisode102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        corridor.NativeEntryCorridor102Tests.setUpClass()
        cls.lib = corridor.NativeEntryCorridor102Tests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        corridor.NativeEntryCorridor102Tests.tearDownClass()

    def setUp(self):
        self.fresh()

    def fresh(self):
        self.a = corridor.NativeEntryCorridor102Tests(methodName='runTest')
        self.a.lib = self.lib
        self.a.fresh()
        self.addCleanup(self.a.doCleanups)
        self.h, self.q, self.p = self.a.h, self.a.q, self.a.p
        self.issued = []

    def origin(self):
        terrain, opening = self.a.pending()
        parent = self.a.admitted()
        self.original_inputs, self.original_moves = self.h.status().inputs, self.h.status().moves
        self.opening, self.parent = opening, parent
        return terrain

    @staticmethod
    def nonpositive(value, terrain, *, nonempty=False, full=False, safe=False):
        """A normal typed UNKNOWN result; never a negative certificate."""
        items = sorted(point for point, kind in terrain.tiles.items() if kind == 'item')
        x, y = items[len(items) // 2]
        left, sy = 448 + 36 * (x - 1), 207 + 36 * y - 48
        if full:
            value.row_count = 1
            value.selected_row = 0
            row = value.rows[0]
            row.left, row.sy, row.word_slot = left, sy, -1
            for index, slot in enumerate(row.slots):
                slot.cx, slot.sy, slot.slot = left + 36 * index, sy, index
                slot.icon_score = slot.icon_upper_bound = .1
                slot.icon_score_exact = 1
                slot.icon_box[:] = (slot.cx - 16, sy + 35, 32, 28)
        if nonempty or safe:
            value.partial_count = 1
            slot = value.partial[0]
            slot.cx, slot.sy, slot.slot = left, sy, 0
            slot.icon_score = slot.icon_upper_bound = .1
            slot.icon_score_exact = 1
            slot.icon_box[:] = (left - 16, sy + 35, 32, 28)
        value.partial_safe_no_positive = int(safe)

    def assess_unknown(self, terrain, *, nonempty=False, full=False, safe=False, mutate=None):
        def result(value):
            self.nonpositive(value, terrain, nonempty=nonempty, full=full, safe=safe)
            if mutate:
                mutate(value)
        self.q.assess(0, 1, result)

    def bounded(self):
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns,
                             self.parent.continuation_deadline_ns,
                             'new job/source must not renew the original entry parent')
        begins = [event for event in self.h.events()
                  if event.command.kind == 4 and event.command.id > self.opening.id and event.begin_ns]
        self.assertLessEqual(len(begins), 2, 'the episode starts at most two new direction inputs')
        self.assertLessEqual(self.h.status().inputs, 16)

    def waiting(self):
        state = self.q.cycle()
        self.assertEqual((0, 0, 0), (state.pending, state.outcome, state.completed_shops),
            'intermediate UNKNOWN belongs to the same uncompleted entry episode')
        self.assertEqual(0, self.h.tick()[0], 'a classification result alone cannot issue a direction input')
        self.bounded()

    def ticket(self, terrain):
        self.waiting()
        self.assertEqual(1, self.p.observe(terrain))
        self.assertEqual(0, self.q.cycle().state,
                         'the fresh independent static observation releases the existing scheduler')
        command = self.h.next_move(terrain)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.id, self.opening.id)
        self.assertGreaterEqual(command.not_before_ns - self.h.now, 50_000_000)
        self.assertLessEqual(command.deadline_ns, self.parent.continuation_deadline_ns)
        self.assertLessEqual(self.h.motion_wait().deadline_ns, self.parent.continuation_deadline_ns)
        if self.issued:
            self.assertGreater(command.ordinal, self.issued[-1].ordinal)
            self.assertGreater(command.source_capture_id, self.issued[-1].source_capture_id)
        self.issued.append(command)
        return command

    def moved(self, terrain, command, *, goods=None, check_parent=True):
        before = self.h.status()
        self.h.ack(command)
        self.assertEqual((before.inputs + 1, before.moves),
            (self.h.status().inputs, self.h.status().moves), 'known ACK gives zero displacement credit')
        old_job = self.q.cycle()
        self.assertEqual(0, old_job.pending)
        latest = native.translated(terrain, 3)
        if goods is not None:
            latest.goods = goods
        self.assertNotEqual((terrain.tiles, terrain.signature), (latest.tiles, latest.signature))
        self.h.observed_result(command, latest)
        event = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy),
            'procedural moved fixture must produce actual strict unit UP, not a desired motion label')
        self.assertEqual(before.moves + 1, self.h.status().moves)
        if latest.goods != 'unknown':
            job = self.q.cycle()
            self.assertEqual((old_job.job_id + 1, 1, self.h.number, command.id),
                (job.job_id, job.pending, job.capture_id, job.prefix))
            self.assertEqual(int(latest.goods == 'partial'), job.partial)
            self.assertEqual(int(latest.goods == 'visible'), job.full_seen)
        if check_parent:
            self.bounded()
        return latest

    def held(self):
        state, status = self.q.cycle(), self.h.status()
        self.assertTrue(state.state == 7 or state.status != 0 or status.terminal,
                        'rejected authority must enter explicit HELD/failure, not merely miss publication timing')
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.bounded()

    def first_move(self, *, goods='partial', check_parent=True):
        terrain = self.origin()
        command = self.ticket(terrain)
        latest = self.moved(terrain, command, goods=goods, check_parent=check_parent)
        return latest, command

    def test_partial_unknown_after_first_move_needs_new_assessment_static_and_second_move(self):
        for nonempty in (False, True):
            with self.subTest(nonempty=nonempty):
                self.fresh()
                # Check the renewed-parent defect separately, then reach
                # the missing second-assessment authority on the baseline.
                # ticket().waiting() still checks this same parent after
                # normal UNKNOWN adoption and before any second input.
                latest, first = self.first_move(check_parent=False)
                self.assertEqual(self.original_inputs + 1, self.h.status().inputs)
                self.assess_unknown(latest, nonempty=nonempty)
                second = self.ticket(latest)
                after = self.moved(latest, second)
                self.assertEqual((self.original_inputs + 2, self.original_moves + 2),
                    (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, first.id, self.h.now, 1, 0, 1))
                self.q.assess(1, 1)
                self.assertEqual((1, 1, 1), (self.q.cycle().outcome,
                    self.q.cycle().candidate_latched, self.q.cycle().completed_shops))
                self.held()
                self.assertEqual('partial', after.goods)

    def test_full_unknown_after_first_move_requalifies_up_from_its_exact_latest_job(self):
        latest, first = self.first_move(goods='visible')
        normal = self.q.cycle()
        self.assess_unknown(latest, nonempty=True, full=True)
        second = self.ticket(latest)
        stale = cycle.Result(abi=1, size=C.sizeof(cycle.Result), selected_row=-1,
            selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now)
        before = bytes(self.q.cycle())
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
            self.parent.job_id, self.parent.capture_id, self.parent.prefix, self.h.now, C.byref(stale)))
        self.assertEqual(before, bytes(self.q.cycle()))
        self.assertGreater(second.source_capture_id, normal.capture_id)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, first.id, self.h.now, 1, 0, 1))
        self.moved(latest, second, goods='visible')
        self.q.assess(1, 1)
        self.held()

    def test_full_rebind_before_first_input_withdraws_unsent_ticket_without_resetting_parent(self):
        for reserved in (False, True):
            for bridge in ('zero', 'unknown'):
                with self.subTest(reserved=reserved, bridge=bridge):
                    self.fresh()
                    terrain = self.origin()
                    old = self.ticket(terrain) if reserved else None
                    full = deepcopy(terrain)
                    full.goods = 'visible'
                    if bridge == 'unknown':
                        full.signature = bytes([80]) * 23296
                    old_job = self.q.cycle()
                    self.assertEqual(1, self.p.observe(full))
                    rebound = self.q.cycle()
                    self.assertEqual((old_job.job_id + 1, 1, 0, 1, 0),
                        (rebound.job_id, rebound.pending, rebound.partial,
                         rebound.full_seen, rebound.completed_shops))
                    self.assertGreater(rebound.capture_id, old_job.capture_id)
                    self.assertEqual(self.parent.prefix, rebound.prefix)
                    self.assertEqual(self.original_inputs, self.h.status().inputs)
                    self.bounded()
                    if old:
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                            old.id, max(self.h.now, old.not_before_ns), 1, 0, 1))
                        retired = next(e for e in self.h.events() if e.command.id == old.id)
                        self.assertEqual((3, 0), (retired.outcome, retired.begin_ns))
                    self.assess_unknown(full, nonempty=True, full=True)
                    if bridge == 'unknown':
                        self.held()
                    else:
                        fresh = self.ticket(full)
                        self.assertEqual(self.original_inputs, self.h.status().inputs)
                        if old:
                            self.assertGreater(fresh.id, old.id)

    def test_second_unknown_and_goods_unknown_hold_without_generic_credit_or_third_input(self):
        for full, nonempty, safe in ((False, False, False), (False, True, False),
                                     (False, True, True), (True, True, False)):
            with self.subTest(full=full, nonempty=nonempty, safe=safe):
                self.fresh()
                latest, _ = self.first_move()
                self.assess_unknown(latest, nonempty=True)
                second = self.ticket(latest)
                after = self.moved(latest, second, goods='visible' if full else 'partial')
                self.assess_unknown(after, nonempty=nonempty, full=full, safe=safe)
                self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
                for _ in range(3):
                    self.p.observe(after)
                    self.held()
                self.assertEqual(self.original_inputs + 2, self.h.status().inputs)
        self.fresh()
        terrain = self.origin()
        first = self.ticket(terrain)
        self.moved(terrain, first, goods='unknown')
        self.assertEqual(0, self.q.cycle().pending)
        self.held()
        self.assertEqual(self.original_inputs + 1, self.h.status().inputs)

    def test_ack_unknown_visual_wait_and_unknown_synth_do_not_create_second_step(self):
        for fault in ('ack_only', 'visual_unknown', 'unknown_synth'):
            with self.subTest(fault=fault):
                self.fresh()
                terrain = self.origin()
                first = self.ticket(terrain)
                job = self.q.cycle()
                if fault == 'unknown_synth':
                    self.h.now = first.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, first.id, self.h.now, 1, 0, 1))
                    self.h.prefix = first.id
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, first.id, self.h.now + 1, -1))
                    self.h.now += 2
                    self.assertEqual(4, self.h.status().input_state)
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, first.id, self.h.now, 1, 0, 1))
                    self.assertNotEqual(4, self.h.tick()[1].kind)
                    self.assertEqual(self.original_moves, self.h.status().moves)
                    continue
                self.h.ack(first)
                self.assertEqual((self.original_moves, job.job_id, 0),
                    (self.h.status().moves, self.q.cycle().job_id, self.q.cycle().pending))
                if fault == 'visual_unknown':
                    uncertain = native.translated(terrain, 3)
                    uncertain.signature = bytes([80]) * 23296
                    self.h.observed_result(first, uncertain)
                    event = next(e for e in self.h.events() if e.command.id == first.id)
                    self.assertIn(event.motion, (0, 7), 'uncertain procedural response must actually be UNKNOWN/TWEEN')
                    self.assertEqual((self.original_moves, job.job_id, 0),
                        (self.h.status().moves, self.q.cycle().job_id, self.q.cycle().pending))
                self.assertEqual(0, self.h.tick()[0])
                self.h.now = self.h.motion_wait().deadline_ns + 1
                self.h.tick()
                self.held()
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, first.id, self.h.now, 1, 0, 1))

    def test_parent_horizon_input_budget_cancel_level_and_prefix_cannot_be_refreshed(self):
        for fault in ('parent_zero', 'parent_one', 'worker_delay', 'walk', 'session',
                      'cancel', 'prefix', 'job', 'source'):
            with self.subTest(fault=fault):
                self.fresh()
                terrain = self.origin()
                if fault in ('parent_one', 'worker_delay', 'walk', 'session', 'job', 'source'):
                    first = self.ticket(terrain)
                    terrain = self.moved(terrain, first)
                    pending = self.q.cycle()
                    if fault in ('job', 'source'):
                        frozen = bytes(pending)
                        self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                            pending.job_id + int(fault == 'job'),
                            pending.capture_id + int(fault == 'source'), pending.prefix, self.h.now))
                        self.assertEqual(frozen, bytes(self.q.cycle()))
                    if fault == 'worker_delay':
                        self.h.now = self.parent.continuation_deadline_ns + 1
                        self.h.tick()
                        self.held()
                        continue
                    self.assess_unknown(terrain, nonempty=True)
                if fault == 'prefix':
                    state = bytes(self.q.cycle())
                    self.h.now += 10_000_000
                    self.h.observe(self.h.scene(2, 2, terrain, beat=True), prefix=self.h.prefix + 1)
                    self.assertEqual(state, bytes(self.q.cycle()))
                    self.assertEqual(0, self.h.tick()[0])
                    continue
                if fault in ('job', 'source'):
                    self.ticket(terrain)
                    continue
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault == 'walk': self.h.now = self.h.status().walk_started_ns + 45 * native.SECOND
                elif fault == 'session': self.h.now = self.h.status().started_ns + 180 * native.SECOND
                else: self.h.now = self.parent.continuation_deadline_ns + 1
                self.p.observe(terrain)
                self.held()
        # A new native run gets its own ordinary constructor. Old run IDs and
        # jobs do not inject a pre-existing episode into that fresh context.
        self.fresh()
        terrain = self.origin()
        old = self.ticket(terrain)
        previous = self.h.engine
        fresh = self.lib.ng2_controller_create_cycle(self.h.now)
        self.assertTrue(fresh)
        self.addCleanup(self.lib.ng2_controller_destroy, fresh)
        self.assertNotEqual(previous, fresh)
        self.assertEqual(0, self.lib.ng2_controller_begin(fresh, old.id, self.h.now, 1, 0, 1))
        self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(fresh,
            self.parent.job_id, self.parent.capture_id, self.parent.prefix, self.h.now))

    def test_parent_and_current_roi_masks_floor_or_static_changes_reject_authority(self):
        for fault in ('item_loss', 'missing_mask', 'extra_mask', 'destination_item',
                      'destination_unknown', 'parent_support', 'motion', 'unknown', 'slot_roi'):
            with self.subTest(fault=fault):
                self.fresh()
                latest, _ = self.first_move()
                if fault == 'slot_roi':
                    def outside(value):
                        value.partial[0].cx = 20
                        value.partial[0].icon_box[:] = (4, value.partial[0].sy + 35, 32, 28)
                    self.assess_unknown(latest, nonempty=True, mutate=outside)
                    self.held()
                    continue
                self.assess_unknown(latest, nonempty=True)
                changed = deepcopy(latest)
                item = min(point for point, kind in latest.tiles.items() if kind == 'item')
                if fault == 'item_loss': changed.tiles[item] = 'floor'
                elif fault == 'missing_mask': changed.protected.remove(item)
                elif fault == 'extra_mask': changed.protected.add((7, 0))
                elif fault == 'destination_item':
                    changed.tiles[(0, -1)] = 'item'; changed.protected.add((0, -1))
                elif fault == 'destination_unknown': changed.tiles.pop((0, -1), None)
                elif fault == 'parent_support': changed.tiles[(1, 0)] = 'stone'
                elif fault == 'motion': changed.signature = native.translated(latest, 3).signature
                else: changed.signature = bytes([80]) * 23296
                self.assertNotEqual((latest.tiles, latest.protected, latest.signature),
                    (changed.tiles, changed.protected, changed.signature),
                    'each post-MOVED negative changes the actual current ITEM/mask/material/texture')
                self.p.observe(changed)
                self.held()
        self.fresh()
        latest, _ = self.first_move()
        self.assess_unknown(latest, nonempty=True)
        self.assertEqual((4, 3), (self.ticket(latest).kind, self.issued[-1].direction),
                         'unchanged independent current evidence reaches the second future ticket')

    def test_old_top_and_horizontal_one_shots_cannot_acquire_entry_episode(self):
        old = top.NativePartialFraming097Tests(methodName='runTest')
        old.lib = self.lib
        old.setUp()
        self.addCleanup(old.doCleanups)
        terrain, _ = old.pending()
        old.admitted()
        old.p.observe(terrain)
        command = old.h.next_move(terrain)
        old.h.ack(command)
        latest = native.translated(terrain, 3)
        old.h.observed_result(command, latest)
        old.q.assess(0, 1)
        self.assertEqual(7, old.q.cycle().state)
        self.assertNotEqual(4, old.h.tick()[1].kind)
        self.fresh()
        self.a.pending(corridor=False)
        self.assertEqual(7, self.q.cycle().state, 'old DIRT-rail no_top shape never starts an episode')
        frame = horizontal.NativeFullFraming101Tests(methodName='runTest')
        frame.lib = self.lib
        frame.setUp()
        self.addCleanup(frame.doCleanups)
        _, latest, _, _, moves, _ = frame.moved(partial=True)
        def safe(value):
            value.partial_count = value.partial_safe_no_positive = 1
            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
        frame.q.assess(0, 1, safe)
        self.assertEqual(7, frame.q.cycle().state)
        self.assertEqual(moves + 1, frame.h.status().moves)
        self.assertNotEqual(4, frame.h.tick()[1].kind)

    def adopt_bound_old_job(self, job, outcome, *, already_started=False, mutate=None):
        if not already_started:
            self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                job.job_id, job.capture_id, job.prefix, self.h.now),
                'queued FULL must not retire the older HOLD worker source')
        value = cycle.Result(abi=1, size=C.sizeof(cycle.Result), outcome=outcome,
            coverage=1, selected_row=-1, selected_partial=-1,
            started_ns=self.h.now, finished_ns=self.h.now + 1)
        if mutate: mutate(value)
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)),
            'the older current worker result must be adopted before queued FULL data')

    def test_pending_full_preserves_hold_assess_and_old_candidate_target_before_fifo_rebind(self):
        for started in (False, True):
            for view in ('stable', 'unstable', 'prefix'):
                for outcome in (1, 2):
                    with self.subTest(started=started, view=view, outcome=outcome):
                        self.fresh()
                        latest, _ = self.first_move()
                        old = self.q.cycle()
                        if started:
                            self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                                old.job_id, old.capture_id, old.prefix, self.h.now))
                        before = self.q.cycle()
                        full = deepcopy(latest); full.goods = 'visible'
                        options = {'stable': 0} if view == 'unstable' else {'prefix': self.h.prefix+1} if view == 'prefix' else {}
                        self.p.observe(full, **options)
                        after = self.q.cycle()
                        if view != 'stable':
                            self.assertEqual(bytes(before), bytes(after),
                                'unqualified FULL may not mutate cycle state or poison the pending worker')
                        self.assertEqual((before.job_id, before.capture_id, before.prefix, before.state,
                            before.pending, before.worker_started_ns), (after.job_id, after.capture_id,
                            after.prefix, after.state, after.pending, after.worker_started_ns),
                            'stable FULL queues data while old HOLD/ASSESS ownership remains intact')
                        self.adopt_bound_old_job(old, outcome, already_started=started)
                        current = self.q.cycle()
                        self.assertEqual((old.job_id, old.capture_id, 1, outcome, 7),
                            (current.job_id, current.capture_id, current.candidate_latched,
                             current.outcome, current.state))
                        self.assertFalse(current.pending)
                        self.held()

    def test_pending_full_requires_safe_old_unknown_before_latest_full_second_step(self):
        for started in (False, True):
            for fault in ('safe', 'upper', 'strong_word'):
                with self.subTest(started=started, fault=fault):
                    self.fresh()
                    latest, _ = self.first_move()
                    old = self.q.cycle()
                    if started:
                        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                            old.job_id, old.capture_id, old.prefix, self.h.now))
                    full = deepcopy(latest); full.goods = 'visible'
                    self.p.observe(full)
                    queued_id = self.h.number
                    self.assertEqual(old.job_id, self.q.cycle().job_id)
                    def result(value):
                        self.nonpositive(value, latest, nonempty=True)
                        if fault == 'upper': value.partial[0].icon_upper_bound = .8
                        elif fault == 'strong_word':
                            value.partial[0].word_present = 1
                            value.partial[0].word_iou = .82; value.partial[0].word_coverage = .90
                    self.adopt_bound_old_job(old, 0, already_started=started, mutate=result)
                    if fault != 'safe':
                        self.assertEqual((old.job_id, 7), (self.q.cycle().job_id, self.q.cycle().state))
                        self.held()
                    else:
                        current = self.q.cycle()
                        self.assertEqual((old.job_id+1, queued_id, old.prefix, 1, 0, 1),
                            (current.job_id, current.capture_id, current.prefix,
                             current.pending, current.partial, current.full_seen))
                        self.bounded()
                        self.assess_unknown(full, nonempty=True, full=True)
                        second = self.ticket(full)
                        self.assertEqual((4, 3), (second.kind, second.direction))
                        self.assertEqual(self.original_inputs+1, self.h.status().inputs,
                            'late FULL after first MOVED may requalify but never auto-send the second input')

    def test_pending_worker_keeps_its_original_budget_after_observation_parent_expires(self):
        for outcome in (0, 1, 2, 'expired_worker'):
            with self.subTest(outcome=outcome):
                self.fresh()
                terrain = self.origin()
                first = self.ticket(terrain)
                self.h.ack(first)
                self.h.now = self.parent.continuation_deadline_ns - 20_000_000
                latest = native.translated(terrain, 3)
                self.h.observed_result(first, latest)
                self.assertEqual(self.original_moves+1, self.h.status().moves)
                job = self.q.cycle()
                self.assertTrue(job.pending)
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now))
                running = self.q.cycle()
                self.assertGreater(running.deadline_ns, self.parent.continuation_deadline_ns,
                    'the late proven frame has an existing classification budget beyond its MOVE parent')
                if outcome == 0:
                    full = deepcopy(latest); full.goods = 'visible'
                    self.p.observe(full)
                    self.assertEqual(job.job_id,self.q.cycle().job_id)
                if outcome == 'expired_worker':
                    self.h.now = running.deadline_ns+1
                    self.h.tick(); self.held()
                    before = bytes(self.q.cycle())
                    value = cycle.Result(abi=1,size=C.sizeof(cycle.Result),outcome=2,
                        coverage=1,selected_row=-1,selected_partial=-1,
                        started_ns=self.h.now,finished_ns=self.h.now)
                    self.assertEqual(0,self.lib.ng2_controller_cycle_assess(self.h.engine,
                        job.job_id,job.capture_id,job.prefix,self.h.now,C.byref(value)))
                    self.assertEqual(before,bytes(self.q.cycle()))
                    continue
                self.h.now = self.parent.continuation_deadline_ns+1
                self.assertEqual(0,self.h.tick()[0])
                current = self.q.cycle()
                self.assertEqual((job.job_id,job.capture_id,2,1,running.deadline_ns),
                    (current.job_id,current.capture_id,current.state,current.pending,current.deadline_ns),
                    'input-parent expiry cannot discard the current worker before its original data deadline')
                self.adopt_bound_old_job(job,outcome,already_started=True)
                if outcome:
                    self.assertEqual((outcome,1,7),(self.q.cycle().outcome,
                        self.q.cycle().candidate_latched,self.q.cycle().state))
                else:
                    self.assertEqual((0,7),(self.q.cycle().outcome,self.q.cycle().state))
                self.held()
                self.assertEqual(self.original_inputs+1,self.h.status().inputs)

    def test_second_observation_normal_complete_negative_preserves_durable_restart_protocol(self):
        latest, _ = self.first_move()
        self.assess_unknown(latest, nonempty=True)
        second = self.ticket(latest)
        self.moved(latest, second, goods='visible')
        job = self.q.cycle()
        self.assertEqual((1, 0, 1, 0), (job.pending, job.partial,
            job.full_seen, job.completed_shops))
        # Copy the actual immutable Scene accepted for this latest C job.
        # Its wider ITEM projection and the three raw offers are procedural;
        # no Perception output or normal Ring proof is hand-written here.
        scene = native.Scene.from_buffer_copy(bytes(self.h._last_fixture_scene))
        self.assertEqual(2, scene.goods)
        original = bank.complete_shop(bank.bank_data()['entries'][:3], auth=bank.auth_data())
        width, height = 896, 414
        pixels = bytearray(bytes((0, 0, 0, 255)) * (width * height))
        dx, dy = 376 - 360, 87 - 120
        x0, x1 = max(0, -dx), min(width, width - dx)
        for y in range(max(0, -dy), min(height, height - dy)):
            pixels[4 * ((y + dy) * width + x0 + dx):4 * ((y + dy) * width + x1 + dx)] = \
                original[4 * (y * width + x0):4 * (y * width + x1)]
        temporary = tempfile.TemporaryDirectory(prefix='entry-episode-ring102-')
        self.addCleanup(temporary.cleanup)
        ring = bank.NativeRingBank094Tests.build_library(
            native.CORE / 'NG2Ring.c', Path(temporary.name) / 'ring.so')
        raw_status, produced = pixels102.normal_assess(ring, bytes(pixels), scene, mode=2)
        self.assertEqual((0, 0, 3, 2),
            (raw_status, produced.status, produced.outcome, produced.coverage),
            'ordinary Ring must actually produce COMPLETE negative; an incomplete fixture is not forced negative')
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        result = cycle.Result.from_buffer_copy(bytes(produced))
        proof = cycle.Result.from_buffer_copy(bytes(produced))
        proof.started_ns = proof.finished_ns = 0
        result.started_ns, result.finished_ns = self.h.now, self.h.now + 1
        normalized = cycle.Result.from_buffer_copy(bytes(result))
        normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(proof), bytes(normalized),
                         'only result clocks are normalized, not its ordinary producer evidence')
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        self.assertEqual((3, 0, 1), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().completed_shops),
            'episode exhaustion must not override a freshly certified negative')
        self.assertEqual(4, self.q.cycle().state,
                         'a complete negative joins the existing NEGATIVE_PAUSE protocol')
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0], 'ordinary negative still waits for durable publication')
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
            restart.id, self.h.now, 1, 0, 1), 'actual RESTART cannot begin before its exact durable intent')
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))
        awaiting = self.q.cycle()
        self.assertEqual(job.level_id, awaiting.level_id)
        self.assertEqual(0, self.h.tick()[0], 'ACK/new floor still waits for linked outcome durability')
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            awaiting.job_id, awaiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id + 1, 0, 0, 1), (self.q.cycle().level_id,
            self.q.cycle().state, self.h.status().terminal, self.q.cycle().completed_shops))


if __name__ == '__main__':
    unittest.main()
