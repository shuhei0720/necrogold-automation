"""Preserve image/price positives through the public C cycle.

TEST113's real ring was retained as a candidate. Its original PNG and exact
score are private calibration, not embedded here or relabeled as unseen data.
These pixels, Scenes, clock and PAUSE responses are procedural. The normal
producer result is passed to the controller without modifying its fields.
"""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_restart_yield112 as yielding
from tests import test_native_ring_bank094 as bank
from tests.test_native_handoff099 import handoff
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_target_assessment087 import FEATURES, WIDTH

CORE = native.CORE


class NativePositive114Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = CORE
            yielding.NativeRestartYield112Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = yielding.NativeRestartYield112Tests.lib
        cls.tmp = tempfile.TemporaryDirectory(prefix='positive114-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            Path(CORE)/'NG2Ring.c', Path(cls.tmp.name)/'ring.so', include=(CORE,))

    @classmethod
    def tearDownClass(cls):
        yielding.NativeRestartYield112Tests.tearDownClass()

    def setUp(self):
        self.f = yielding.NativeRestartYield112Tests(methodName='runTest')
        self.f.lib = self.lib
        self.f.has_yield = True
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.h, self.q = self.f.h, self.f.q
        self.f.first_pause()

    @staticmethod
    def pixels(ambiguous=False):
        pixels = bytearray(bank.complete_shop(bank.bank_data()['entries'][:3],
            auth=bank.auth_data(), target=True, target_name=False))
        if ambiguous:
            # Reuse the existing image-price111 ambiguity fixture. Only the
            # image changes; the complete same-slot price stays untouched.
            for dx, dy, *_ in FEATURES['icons'][1]['bright'][:70]:
                at = 4*((155+dy)*WIDTH+378+dx)
                pixels[at:at+4] = bytes((27, 17, 12, 255))
        return bytes(pixels)

    @staticmethod
    def price_band(pixels):
        return b''.join(pixels[4*(y*WIDTH+384):4*(y*WIDTH+409)]
                        for y in range(188, 210))

    def credit(self):
        state = self.h.status()
        return tuple(getattr(state, key) for key in ('inputs', 'moves',
            'door_changes', 'terrain_changes', 'restarts', 'x', 'y'))

    def produced(self, pixels):
        # Independent acquisition after the first-floor observation; equal
        # intervals are correctly rejected by the unchanged capture gate.
        self.h.now += 3
        scene = self.q.goods()
        job = self.q.cycle()
        self.assertEqual(1, job.pending)
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
        job = self.q.cycle()
        self.assertEqual(self.h.now, job.worker_started_ns)
        scene_bytes = bytes(scene)

        def clock(_):
            self.h.now += 1
            return self.h.now

        now = Clock(clock)
        cancelled = Cancelled(lambda _: 0)
        options = Options(abi=1, size=C.sizeof(Options), mode=2,
            deadline_ns=job.deadline_ns, now_ns=now, cancelled=cancelled,
            scene=C.addressof(scene), fast=1)
        result = Result()
        buf = C.create_string_buffer(pixels)
        self.assertEqual(0, self.ring.ng2_ring_assess_rgba(buf, len(pixels),
            WIDTH*4, C.byref(options), C.byref(result)))
        self.assertEqual(0, result.status)
        self.assertEqual(scene_bytes, bytes(scene))
        self.assertLess(result.finished_ns, job.deadline_ns)
        self.assertLessEqual(result.finished_ns-job.worker_started_ns, 100_000_000)
        raw = bytes(result)
        self.h.now += 1
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        self.assertEqual(raw, bytes(result), 'the normal result is never repaired for adoption')
        return result, job

    def assert_pause_and_no_continuation(self, outcome, source, credit):
        held = self.q.cycle()
        self.assertEqual((outcome, 1, 7),
            (held.outcome, held.candidate_latched, held.state))
        self.assertEqual((source.capture_id, source.prefix),
            (held.capture_id, held.prefix))
        self.assertEqual(0, held.restart_command_id)
        self.assertEqual(0, self.q.durable(), 'a result cannot replace a fresh PAUSE image')
        pause = self.q.pause_observed()
        self.assertEqual(2, pause.kind)
        self.assertEqual(credit, self.credit())
        self.assertEqual(1, self.q.durable())
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual((1, 1, 0), (self.h.status().terminal,
            self.h.status().paused, self.h.status().input_state))
        self.assertEqual((outcome, 1),
            (self.q.cycle().outcome, self.q.cycle().candidate_latched))
        self.assertEqual(credit, self.credit())
        self.assertEqual((0, 0), (handoff(self.lib, self.h.engine).kind,
            handoff(self.lib, self.h.engine).allowed))
        self.assertFalse(any(event.command.kind in (3, 4) for event in self.h.events()))
        self.assertEqual(0, self.h.tick()[0])
        events = tuple(bytes(event) for event in self.h.events())
        self.h.now = max(self.h.now, held.continuation_deadline_ns)+1
        self.assertEqual(0, self.h.observe(self.h.scene(2, 2)))
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(events, tuple(bytes(event) for event in self.h.events()))
        self.assertEqual(credit, self.credit())
        self.assertEqual((outcome, 1),
            (self.q.cycle().outcome, self.q.cycle().candidate_latched))
        self.assertEqual(0, handoff(self.lib, self.h.engine).allowed)

    def test_valid_price_ambiguous_image_is_retained_through_durable_pause(self):
        pixels = self.pixels(ambiguous=True)
        self.assertEqual(self.price_band(self.pixels()), self.price_band(pixels))
        self.assertGreaterEqual(sum(min(pixels[at:at+3]) > 140
            for y in range(188, 210) for at in
            range(4*(y*WIDTH+384), 4*(y*WIDTH+409), 4)), 18)
        credit = self.credit()
        result, source = self.produced(pixels)
        self.assertEqual(1, result.outcome)
        slot = result.rows[result.selected_row].slots[1]
        self.assertEqual(1, slot.icon_score_exact)
        self.assertGreaterEqual(slot.icon_score, .80)
        self.assertLess(slot.icon_score, .94)
        self.assert_pause_and_no_continuation(1, source, credit)

    def test_pristine_image_with_price_and_no_name_keeps_target_and_no_handoff(self):
        credit = self.credit()
        result, source = self.produced(self.pixels())
        self.assertEqual((2, 16), (result.outcome, result.certificate.policy_version))
        slot = result.rows[result.selected_row].slots[1]
        self.assertGreaterEqual(slot.icon_score, .94)
        self.assertEqual((0, 0., 0.), (slot.word_present, slot.word_iou, slot.word_coverage))
        self.assertEqual((1, 1), (result.certificate.observed_items,
            result.certificate.observed_prices))
        self.assert_pause_and_no_continuation(2, source, credit)


if __name__ == '__main__':
    unittest.main()
