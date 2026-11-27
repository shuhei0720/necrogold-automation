"""Low-score icon probe coordinates may grant observation, never NEGATIVE.

Public fit, opening, real Motion H1 and projection earn the upper owner.
Sparse Scenes and typed UNKNOWN worker packets are declared control inputs;
the original PNG131 normal producer/consumer cut is a separate private check.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_projection124 as projection
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests import test_native_ring_bank094 as ring_bank
from tests.test_target_assessment087 import shop


def low_probe_pixels():
    """Procedural cyan shapes stress a canonical probe near the HUD boundary.

    This is an RGBA/normal Ring interface fixture with a declared Scene,
    not a Perception/game replay or an image of an identified product.
    """
    pixels = bytearray(shop(left=231, sign_y=297, icon=False, name=False))
    for cx in (231, 267, 303):
        for start, colour in ((328, (12, 8, 7, 255)), (361, (10, 170, 165, 255))):
            for y in range(start, start+24):
                for x in range(cx-9, cx+9):
                    at = 4*(y*896+x)
                    pixels[at:at+4] = bytes(colour)
    return bytes(pixels)


class NativeUpperObservation125Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = os.environ.get('NECRO124_UPPER_PROJECTION_CORE')
        selected = os.environ.get('NECRO125_UPPER_OBSERVATION_CORE')
        if selected:
            os.environ['NECRO124_UPPER_PROJECTION_CORE'] = selected
        try:
            projection.NativeUpperProjection124Tests.setUpClass()
        finally:
            if previous is None:
                os.environ.pop('NECRO124_UPPER_PROJECTION_CORE', None)
            else:
                os.environ['NECRO124_UPPER_PROJECTION_CORE'] = previous
        cls.lib = projection.NativeUpperProjection124Tests.lib
        cls.ring_temp = tempfile.TemporaryDirectory(prefix='upper-observation125-ring-')
        cls.addClassCleanup(cls.ring_temp.cleanup)
        core = Path(selected) if selected else native.CORE
        cls.ring = ring_bank.NativeRingBank094Tests.build_library(
            core/'NG2Ring.c', Path(cls.ring_temp.name)/'ring.so')

    @classmethod
    def tearDownClass(cls):
        projection.NativeUpperProjection124Tests.tearDownClass()

    def setUp(self):
        self.p = projection.NativeUpperProjection124Tests(methodName='runTest')
        self.p.lib = self.lib
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.t, self.h = self.p.t, self.p.h

    def rebound_after_actual_H1(self):
        source, world, command = self.p.actual_H1_new_projection()
        self.p.safe_current(source)
        self.assertEqual((1, 0, 1, 0), self.p.token()[:4])
        self.assertEqual(3, self.t.q.cycle().state)
        before = self.p.earned()
        prior = self.t.q.cycle()
        changed = deepcopy(source)
        # A distant palette change preserves every ITEM/GOLD/protection and
        # the next FLOOR. Public observe must earn the new worker job.
        changed.tiles[(6, -3)] = 'stone'
        self.t.frame(changed)
        state = self.t.q.cycle()
        self.assertEqual((1, 1, 5, 2), self.p.earned()[:4])
        self.assertEqual((1, 1, 0, 5), self.p.earned()[4:8])
        self.assertEqual((prior.job_id + 1, 1, 1, command.id),
            (state.job_id, state.pending, state.partial, state.prefix))
        self.assertGreater(state.capture_id, prior.capture_id)
        self.assertEqual(before[8:12], self.p.earned()[8:12])
        self.assertEqual(world, self.p.world())
        self.assertEqual((3, 2, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().input_state))
        self.assertEqual((1, 0, 1, 0), self.p.token()[:4])
        return changed, world, state

    def packet(self, source):
        value = Result(abi=1, size=C.sizeof(Result), status=0, outcome=0,
            coverage=1, reason=1, selected_row=-1, selected_partial=1,
            partial_count=4, partial_safe_no_positive=1)
        left = min(x for (x, y), kind in source.tiles.items() if kind == 'item')
        # The normal classifier may locate the SHOP alias a few pixels away
        # from the tile projection. These declared offsets remain inside the
        # structural-cell contract and original candidate_probe search domain.
        for index, x in enumerate((left+2, left+3, left, left+1)):
            slot = value.partial[index]
            slot.cx, slot.sy = 448+36*x-1, 207+36*4-48-6
            slot.icon_score = slot.icon_upper_bound = .669815225
            slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
            slot.word_present = 1
            slot.word_box[:] = (slot.cx-25, slot.sy+23, 84, 11)
            slot.word_iou, slot.word_coverage = .067857143, .079497908
        weak = value.partial[2]
        weak.icon_box[:] = (weak.cx-24, weak.sy+57, 33, 28)
        self.assertEqual((231, 297, [207, 354, 33, 28]),
            (weak.cx, weak.sy, list(weak.icon_box)))
        return value

    def assess(self, state, value):
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now))
        value.started_ns = self.h.now+1
        self.h.now += self.t.WORKER
        value.finished_ns = self.h.now
        self.h.now += self.t.CALLBACK
        self.assertLess(self.h.now, state.continuation_deadline_ns)
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)))

    def assert_no_move(self):
        before = self.h.status().inputs, self.h.status().moves
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))

    def test_earned_H1_rebound_weak_probe_can_keep_observation_without_NEG_or_MOVE(self):
        source, world, state = self.rebound_after_actual_H1()
        value = self.packet(source)
        before = self.p.earned()
        self.assess(state, value)
        after = self.t.q.cycle()
        self.assertEqual((3, 0, 0),
            (after.state, after.pending, after.candidate_latched),
            'UNKNOWN low-score normal probe pose needs observation; it is not a positive sprite box')
        self.assertEqual((0, 1, 1),
            (value.outcome, value.coverage, value.partial_safe_no_positive))
        self.assertEqual(before[8:12], self.p.earned()[8:12])
        self.assertEqual(world, self.p.world())
        self.assertEqual((3, 2, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().input_state))

    def test_new_current_and_normal_unit_are_still_required_for_H2_then_DOWN(self):
        source, world, state = self.rebound_after_actual_H1()
        value = self.packet(source)
        self.assess(state, value)
        self.assertEqual(3, self.t.q.cycle().state)
        self.assertEqual(0, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)),
            'one job cannot reacquire result rights')
        self.assert_no_move()
        parent = state.continuation_deadline_ns
        for direction in (1, 4):
            command = self.t.ticket(source)
            self.assertEqual(direction, command.direction)
            prior = self.h.status().moves
            self.t.ack(command, source)
            self.assertEqual(prior, self.h.status().moves, 'ACK is not a unit')
            source = native.translated(source, direction)
            source.tiles[native.DIRS[4]] = 'floor'
            source.protected = self.t.cross({p for p, kind in source.tiles.items() if kind == 'item'})
            self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
            event = self.h.events()[-1]
            self.assertEqual((1, *native.DIRS[direction]), (event.motion, event.dx, event.dy))
            self.p.safe_current(source)
            self.assertEqual(parent, self.t.q.cycle().continuation_deadline_ns)
            self.assertEqual(world, self.p.world())
        self.assertEqual((3, 2, 1, 5), self.p.earned()[4:8])

    def test_malformed_or_positive_probe_never_grants_observation(self):
        faults = ('score_boundary', 'nan', 'inexact_mismatch', 'exact', 'shape',
            'outside_image', 'outside_probe_x', 'outside_probe_y', 'bad_center',
            'word_domain', 'word_hud', 'absent_word_data', 'strong_word',
            'strong_word_absent', 'candidate', 'target', 'non_target_kind',
            'leftover_id', 'leftover_box', 'leftover_score', 'complete',
            'not_safe', 'negative', 'bad_reason')
        for fault in faults:
            with self.subTest(fault=fault):
                self.setUp()
                source, world, state = self.rebound_after_actual_H1()
                value = self.packet(source)
                slot = value.partial[2]
                if fault == 'score_boundary': slot.icon_score = slot.icon_upper_bound = .80
                elif fault == 'nan': slot.icon_score = slot.icon_upper_bound = float('nan')
                elif fault == 'inexact_mismatch': slot.icon_score -= .01
                elif fault == 'exact': slot.icon_score_exact = 1
                elif fault == 'shape': slot.icon_box[2] = 35
                elif fault == 'outside_image': slot.icon_box[1] = 413
                elif fault == 'outside_probe_x': slot.icon_box[0] -= 1
                elif fault == 'outside_probe_y': slot.icon_box[1] += 1
                elif fault == 'bad_center': slot.cx = 2**31-1
                elif fault == 'word_domain': slot.word_box[0] -= 60
                elif fault == 'word_hud': slot.word_box[1] = 380
                elif fault == 'absent_word_data': slot.word_present = 0
                elif fault in ('strong_word', 'strong_word_absent'):
                    slot.word_iou = slot.word_coverage = 1.
                    if fault == 'strong_word_absent': slot.word_present = 0
                elif fault == 'candidate': slot.outcome = value.outcome = 1
                elif fault == 'target': slot.outcome = value.outcome = 2
                elif fault == 'non_target_kind': slot.kind = 3
                elif fault == 'leftover_id': slot.non_target_id = 1
                elif fault == 'leftover_box': slot.ignored_icon_box[2] = 1
                elif fault == 'leftover_score': slot.non_target_icon_score = .01
                elif fault == 'complete': value.coverage = 2
                elif fault == 'not_safe': value.partial_safe_no_positive = 0
                elif fault == 'negative': value.outcome = 3
                elif fault == 'bad_reason': value.reason = 2**32-1
                self.assess(state, value)
                self.assertNotEqual(3, self.t.q.cycle().state)
                self.assert_no_move()
                self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)
                self.assertEqual(world, self.p.world())

    def test_old_strict_exact_packet_is_preserved(self):
        source, _world, state = self.rebound_after_actual_H1()
        value = self.packet(source)
        slot = value.partial[2]
        slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
        slot.icon_score_exact = 1
        slot.icon_score, slot.icon_upper_bound = .65, .70
        self.assess(state, value)
        self.assertEqual(3, self.t.q.cycle().state)

    def test_normal_producer_packet_reaches_the_earned_same_consumer_without_edits(self):
        source, world, state = self.rebound_after_actual_H1()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now))
        scene = self.h.scene(2, 2, source, beat=True)
        pixels = C.create_string_buffer(low_probe_pixels())
        now, cancel = Clock(lambda _: self.h.now+1), Cancelled(lambda _: 0)
        options = Options(abi=1, size=C.sizeof(Options), mode=2,
            deadline_ns=state.deadline_ns, now_ns=now, cancelled=cancel,
            scene=C.addressof(scene), fast=1)
        value = Result()
        self.assertEqual(0, self.ring.ng2_ring_assess_rgba(pixels, len(pixels)-1,
            896*4, C.byref(options), C.byref(value)))
        original = bytes(value)
        self.assertEqual((0, 0, 1, 0, 3, 1), (value.status, value.outcome,
            value.coverage, value.row_count, value.partial_count, value.partial_safe_no_positive))
        for slot in value.partial[:value.partial_count]:
            self.assertEqual((0, .799732172, .799732172, 353, 28),
                (slot.icon_score_exact, slot.icon_score, slot.icon_upper_bound,
                 slot.icon_box[1], slot.icon_box[3]))
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)))
        self.assertEqual(original, bytes(value), 'normal producer fields stay byte-for-byte immutable')
        self.assertEqual(3, self.t.q.cycle().state)
        self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)
        self.assertEqual(world, self.p.world())
        self.assertEqual((3, 2, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().input_state))

    def test_wrong_job_capture_prefix_cancel_and_late_result_do_not_reuse_probe(self):
        for fault in ('job', 'capture', 'prefix', 'cancel', 'late', 'status'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _world, state = self.rebound_after_actual_H1()
                value = self.packet(source)
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                    self.assertEqual(0, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        state.job_id, state.capture_id, state.prefix, self.h.now))
                else:
                    self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        state.job_id, state.capture_id, state.prefix, self.h.now))
                    value.started_ns = value.finished_ns = self.h.now+1
                    self.h.now += 2
                    if fault == 'late': self.h.now = state.continuation_deadline_ns+1
                    if fault == 'status': value.status = 1
                    result = self.lib.ng2_controller_cycle_assess(self.h.engine,
                        state.job_id+int(fault == 'job'), state.capture_id+int(fault == 'capture'),
                        state.prefix+int(fault == 'prefix'), self.h.now, C.byref(value))
                    self.assertEqual(int(fault in ('late', 'status')), result)
                self.assertNotEqual(3, self.t.q.cycle().state)
                self.assert_no_move()
                self.assertEqual(state.continuation_deadline_ns, self.t.q.cycle().continuation_deadline_ns)


if __name__ == '__main__':
    unittest.main()
