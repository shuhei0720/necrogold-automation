"""FULL data refresh with an immutable movement source and bounded FIFO.

TEST109 retained a directly stationary FULL view while remote ordinary cells
resolved. A normal negative was available before the original parent bound,
but the old material equality guard never classified that source. All clocks,
Scenes and pixels here are procedural contracts, not future phone results.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_full_framing101 as full
from tests import test_native_ring_bank094 as bank
from tests import test_native_offer_coverage104 as offer
from tests import test_native_single_offer108 as single
from tests.test_native_ring094 import Result
from tests.test_native_stop099 import stop_detail

ROOT = Path(__file__).resolve().parents[1]


class NativeFullData110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO_TEST110_FULL_DATA_CORE', str(previous)))
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.tmp = tempfile.TemporaryDirectory(prefix='full-data110-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            ROOT / 'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name) / 'ring.so')

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.f = full.NativeFullFraming101Tests(methodName='runTest')
        self.f.lib = self.lib
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def admitted(self, normal=False):
        if normal:
            build = self.f.full_source
            def complete_source():
                value = build()
                value.tiles[(-1, -2)] = 'floor'
                return value
            self.f.full_source = complete_source
            def normal_unknown(value):
                status, produced = offer.normal_assess(self.ring,
                    single.shop_pixels(missing_wall=True),
                    self.f.h.scene(2, 2, complete_source(), beat=True))
                self.assertEqual((0, 0, 1, 1),
                    (status, produced.outcome, produced.coverage, produced.row_count))
                started, finished = value.started_ns, value.finished_ns
                C.memmove(C.byref(value), C.byref(produced), C.sizeof(value))
                value.started_ns, value.finished_ns = started, finished
            self.f.result = normal_unknown
        source, opening, state, moves = self.f.admitted()
        self.h, self.q = self.f.h, self.f.q
        return source, opening, state, moves

    def observe(self, source, advance=10_000_000, **kwargs):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, source, beat=True), **kwargs)

    @staticmethod
    def changed(source, kind='dirt'):
        latest = deepcopy(source)
        latest.tiles[(-5, -3)] = kind  # Remote, unprotected, outside both 3x3 footprints.
        return latest

    def normal(self, source, **kwargs):
        status, value = offer.normal_assess(self.ring, single.shop_pixels(**kwargs),
            self.h.scene(2, 2, source, beat=True))
        self.assertEqual((0, 0), (status, value.status))
        return value

    def begin(self):
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        return job, self.h.now

    def finish(self, job, started, value, latency=44_000_000, expected=1):
        finished = started + latency
        self.assertGreaterEqual(finished, self.h.now)
        value.started_ns, value.finished_ns = started, finished
        self.h.now = finished
        self.assertEqual(expected, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))

    def unknown(self):
        value = Result(abi=1, size=C.sizeof(Result), selected_row=-1, selected_partial=-1)
        full.NativeFullFraming101Tests.result(value)
        return value

    def assert_no_input(self, moves):
        self.assertEqual((0, moves), (self.h.status().input_state, self.h.status().moves))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_remote_material_stationary_full_starts_only_a_data_job(self):
        source, opening, original, moves = self.admitted()
        latest = self.changed(source)
        self.assertEqual((2, 0, 0), self.h.motion(source, latest, 1))
        self.assertEqual(1, self.observe(latest))
        job = self.q.cycle()
        self.assertEqual((original.job_id + 1, self.h.number, 1, 0),
            (job.job_id, job.capture_id, job.pending, job.completed_shops),
            'fresh direct-zero FULL data must be classified before the unchanged parent deadline')
        self.assertEqual(original.prefix, job.prefix)
        self.assertLessEqual(job.continuation_deadline_ns, original.continuation_deadline_ns)
        self.assertEqual((0, moves), (self.h.status().input_state, self.h.status().moves))
        self.assertEqual((0, 0), (self.h.tick()[0], stop_detail(self.lib, self.h.engine).valid),
            'a data job owns no MOVE or premature PAUSE permission')

    def test_normal_producer_data_negative_uses_new_source_then_durable_restart_chain(self):
        source, _, original, moves = self.admitted(normal=True)
        latest = self.changed(source)
        self.observe(latest)
        job, started = self.begin()
        value = self.normal(latest)
        self.assertEqual((3, 2, 11), (value.outcome, value.coverage, value.certificate.policy_version))
        # A newer ordinary palette view cannot cancel the running negative.
        later = self.changed(source, 'stone')
        self.observe(later, 40_000_000)
        self.assertEqual(job.capture_id, self.q.cycle().capture_id)
        self.finish(job, started, value)
        self.assertEqual((3, 0, 4, 1, job.capture_id),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state,
             self.q.cycle().completed_shops, self.q.cycle().capture_id))
        self.assertEqual(moves, self.h.status().moves)
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, original.continuation_deadline_ns)
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
        self.assertEqual((1, original.level_id), (self.h.status().restarts, waiting.level_id))
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual(original.level_id + 1, self.q.cycle().level_id)

    def test_first_eligible_queued_source_survives_faster_captures_and_worker_latency(self):
        for latency in (44_000_000, 80_000_000, 100_000_000):
            with self.subTest(worker_ns=latency):
                self.setUp()
                source, _, original, moves = self.admitted(normal=True)
                first = self.changed(source)
                self.observe(first)
                old_job, started = self.begin()
                good = self.changed(source, 'stone')
                self.observe(good, 40_000_000)
                queued = self.h.number
                flicker = self.changed(source)
                flicker.tiles[(-8, -3)] = 'floor'
                if latency >= 80_000_000:
                    self.observe(flicker, 40_000_000)
                self.assertEqual(queued, self.q.cycle().queued_capture_id,
                    'the one queued source is FIFO, even when later pixels arrive before adoption')
                self.finish(old_job, started, self.normal(first, missing_price=1), latency)
                next_job = self.q.cycle()
                self.assertEqual((old_job.job_id + 1, queued, 1, 0),
                    (next_job.job_id, next_job.capture_id, next_job.pending, next_job.completed_shops))
                self.assertEqual(original.continuation_deadline_ns, next_job.continuation_deadline_ns)
                self.assertEqual(0, self.h.tick()[0], 'queued classification grants no input')
                job, next_started = self.begin()
                if latency == 44_000_000:
                    self.observe(flicker, 36_000_000)
                self.assertEqual(queued, self.q.cycle().capture_id)
                self.finish(job, next_started, self.normal(good), 80_000_000)
                self.assertEqual((3, 0, queued),
                    (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().capture_id))
                self.assertEqual(moves, self.h.status().moves)

    def test_normal_target_candidate_win_over_queued_negative_or_later_unsafe_scene(self):
        # TEST111 mode2 uses observed price glyph support, without numeric OCR.
        for target_name, price, outcome in ((True, None, 2), (False, None, 2), (False, 1, 1)):
            with self.subTest(target_name=target_name, missing_price=price):
                self.setUp()
                source, _, _, moves = self.admitted(normal=True)
                latest = self.changed(source)
                self.observe(latest)
                job, started = self.begin()
                unsafe = deepcopy(latest)
                unsafe.tiles[(8, 3)] = 'item'
                unsafe.protected.add((8, 3))
                self.observe(unsafe, 40_000_000)
                self.finish(job, started, self.normal(latest, target=True, target_name=target_name, missing_price=price))
                self.assertEqual((outcome, 1, 7, 1),
                    (self.q.cycle().outcome, self.q.cycle().candidate_latched,
                     self.q.cycle().state, self.q.cycle().completed_shops))
                self.assert_no_input(moves)

    def test_data_unknown_keeps_original_unissued_step_and_never_restores_consumed_step(self):
        source, opening, original, moves = self.admitted()
        latest = self.changed(source)
        self.observe(latest)
        job, started = self.begin()
        self.finish(job, started, self.unknown())
        self.assertEqual((3, 0, 0), (self.q.cycle().state, self.q.cycle().pending, self.q.cycle().completed_shops))
        self.assertEqual(0, self.h.status().beat_period_ns)
        self.assertEqual(original.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
        self.assert_no_input(moves)
        self.observe(source)
        proof = self.h.number
        command = self.h.next_move(source)
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.id, opening.id)
        self.assertGreaterEqual(command.source_capture_id, proof)
        self.assertLessEqual(self.h.motion_wait().deadline_ns, original.continuation_deadline_ns)
        self.h.ack(command)
        moved = native.translated(source, 1)
        self.h.observed_result(command, moved)
        self.assertEqual(moves + 1, self.h.status().moves)
        self.q.assess(0, 1, full.NativeFullFraming101Tests.result)
        self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_current_classifier_scene_does_not_replace_original_motion_anchor(self):
        source, _, original, moves = self.admitted()
        latest = self.changed(source)
        self.observe(latest)
        job, started = self.begin()
        self.finish(job, started, self.unknown())
        a = deepcopy(latest)
        rng = random.Random(110110)
        a.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
        b = deepcopy(a)
        self.assertEqual((0, 0, 0), self.h.motion(source, a, 1))
        self.assertEqual((2, 0, 0), self.h.motion(a, b, 1))
        for frame in (a, b):
            self.observe(frame)
            self.assertEqual((job.job_id, job.capture_id, 0),
                (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
            self.assert_no_input(moves)
        self.h.now = original.continuation_deadline_ns + 1
        self.h.tick()
        stop = stop_detail(self.lib, self.h.engine)
        self.assertEqual((1, original.capture_id, job.capture_id, original.continuation_deadline_ns),
            (stop.valid, stop.anchor_capture_id, stop.source_capture_id, stop.deadline_ns))

    def test_near_material_new_item_gold_protection_state_or_motion_cannot_start_data_refresh(self):
        for fault in ('near', 'item', 'gold', 'protection', 'partial', 'state', 'unknown', 'moved'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _, original, moves = self.admitted()
                latest = self.changed(source)
                if fault == 'near': latest.tiles[(-1, 0)] = 'dirt'
                elif fault == 'item': latest.tiles[(8, 3)] = 'item'
                elif fault == 'gold': latest.tiles[(8, 3)] = 'gold'
                elif fault == 'protection': latest.protected.add((8, 3))
                elif fault == 'partial': latest.goods = 'partial'
                elif fault == 'unknown': latest.signature = bytes([80]) * 23296
                elif fault == 'moved': latest = native.translated(source, 1)
                self.h.now += 10_000_000
                scene = self.h.scene(0 if fault == 'state' else 2, 2, latest, beat=True)
                self.assertEqual(1, self.h.observe_actual(scene))
                self.assertEqual((original.job_id, original.capture_id, 0),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
                self.assert_no_input(moves)

    def test_pending_unsafe_frame_blocks_negative_without_changing_bound_worker_identity(self):
        for fault in ('item', 'gold', 'protection', 'unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _, _, moves = self.admitted(normal=True)
                latest = self.changed(source)
                self.observe(latest)
                job, started = self.begin()
                unsafe = deepcopy(latest)
                if fault == 'item': unsafe.tiles[(8, 3)] = 'item'
                elif fault == 'gold': unsafe.tiles[(8, 3)] = 'gold'
                elif fault == 'protection': unsafe.protected.add((8, 3))
                else: unsafe.signature = bytes([80]) * 23296
                self.observe(unsafe, 40_000_000)
                self.assertEqual((job.job_id, job.capture_id, 1),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
                self.finish(job, started, self.normal(latest))
                self.assertEqual((7, 0, 0), (self.q.cycle().state, self.q.cycle().outcome,
                    self.q.cycle().candidate_latched))
                self.assert_no_input(moves)

    def test_queued_source_capture_budget_worker_budget_cancel_and_stale_result(self):
        for fault in ('capture_budget', 'worker_budget', 'cancel', 'stale_job'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _, original, moves = self.admitted()
                latest = self.changed(source)
                self.observe(latest)
                job, started = self.begin()
                self.observe(self.changed(source, 'stone'), 40_000_000)
                self.finish(job, started, self.unknown(), 100_000_000)
                current, current_started = self.begin()
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                    self.finish(current, current_started, self.unknown(), expected=0)
                elif fault == 'stale_job':
                    before = bytes(self.q.cycle()), bytes(self.h.status())
                    self.finish(job, started, self.unknown(), 100_000_000, expected=0)
                    self.assertEqual(before, (bytes(self.q.cycle()), bytes(self.h.status())))
                else:
                    # At the queued capture's old 150ms limit, its worker
                    # cannot gain a fresh 100ms on top of its 60ms age.
                    delay = 90_000_001 if fault == 'capture_budget' else 100_000_001
                    self.finish(current, current_started, self.unknown(), delay)
                    self.assertEqual((7, 2), (self.q.cycle().state, self.q.cycle().status))
                self.assertLessEqual(self.q.cycle().continuation_deadline_ns, original.continuation_deadline_ns)
                self.assertEqual(moves, self.h.status().moves)

    def test_unstable_prefix_frames_reserved_or_unknown_input_never_gain_data_rights(self):
        for fault in ('unstable', 'prefix', 'reserved', 'input_unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                if fault in ('reserved', 'input_unknown'):
                    source, _, original, moves, command = self.f.ticket()
                    self.h, self.q = self.f.h, self.f.q
                    if fault == 'input_unknown':
                        self.h.now = command.not_before_ns
                        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                            command.id, self.h.now, 1, 0, 1))
                        self.h.now += 1
                        self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, -1)
                    self.observe(self.changed(source))
                    self.assertEqual((original.job_id, 0), (self.q.cycle().job_id, self.q.cycle().pending))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                else:
                    source, _, original, moves = self.admitted()
                    kwargs = {'stable': 0} if fault == 'unstable' else {'prefix': original.prefix + 100}
                    self.assertEqual(0, self.observe(self.changed(source), **kwargs))
                    self.assertEqual((original.job_id, original.capture_id, 0),
                        (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().pending))
                self.assertEqual(moves, self.h.status().moves)
