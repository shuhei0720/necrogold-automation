"""Independent policy6 validation and real Ring-to-restart public C joining.

Synthetic RGBA and UI responses establish boundaries, never physical speed,
arrival or unknown target accuracy. Integration changes only result clocks.
"""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_structural_cycle096 as structural
from tests import test_native_shop_coverage102 as pixels102
from tests import test_native_ring_bank094 as bank


class NativeShopController102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    @staticmethod
    def scene(**kwargs):
        return native.Scene.from_buffer_copy(bytes(pixels102.shop_scene(**kwargs)))

    @staticmethod
    def certificate(value, scene, left=301, sy=117, truncated_side=1):
        structural.NativeStructuralCycle096Tests.certificate(value, scene, left, sy)
        value.certificate.policy_version = value.certificate.board_mode = 6
        for side in range(2):
            top, height = (-4, 19) if side == truncated_side else (-14, 29)
            value.certificate.board_boxes[side][:] = (left + 72 * side - 14, sy + top, 29, height)
            value.certificate.board_counts[side] = 200

    def assess(self, scene=None, mutate=None, truncated_side=1, sy=117):
        scene = self.scene() if scene is None else scene
        self.assertEqual(1, self.h.observe(scene))
        def build(value):
            self.certificate(value, scene, sy=sy, truncated_side=truncated_side)
            if mutate: mutate(value)
        return self.q.assess(3, 2, build)

    def assert_held(self):
        self.assertEqual((0, 3, 0), (self.q.cycle().outcome, self.q.cycle().status, self.h.status().restarts))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_positive_observed_door_enclosure_and_single_top_loss_face_have_independent_authority(self):
        for mirror in (False, True):
            for door in (False, True):
                for opening in (1, 5):
                    for truncated in (None, 0, 1):
                        with self.subTest(mirror=mirror, door=door, opening=opening, truncated=truncated):
                            self.setUp()
                            self.assess(self.scene(mirror=mirror, bottom_door=door, opening=opening),
                                        truncated_side=truncated)
                            self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status),
                                'a separate fixed enclosure/top-loss proof must be recomputed from immutable source')

    def test_every_positive_wall_and_door_position_is_checked_despite_equal_total_count(self):
        for mirror in (False, True):
            sample = self.scene(mirror=mirror)
            for i, kind in enumerate(sample.tiles):
                if kind != 2: continue
                with self.subTest(mirror=mirror, removed=i):
                    self.setUp()
                    latest = self.scene(mirror=mirror)
                    latest.tiles[i] = 0
                    latest.tiles[(4+5)*23+10+11] = 2
                    self.assess(latest)
                    self.assert_held()
        for fault in ('second_door', 'end_door', 'unbracketed', 'extra_support', 'cap', 'item', 'opening'):
            with self.subTest(fault=fault):
                self.setUp(); latest = self.scene()
                point = {'second_door':(-3,2), 'end_door':(-6,2), 'unbracketed':(-3,2),
                    'extra_support':(-6,-3), 'cap':(-1,-1), 'item':(-3,-1), 'opening':(0,0)}[fault]
                latest.tiles[(point[1]+5)*23+point[0]+11] = 5 if fault in ('second_door','end_door') else 0
                self.assess(latest);self.assert_held()

    def test_full_anchor_bottoms_widths_and_complete_numeric_target_proof_remain_strict(self):
        faults = {
            'both_truncated': lambda v: v.certificate.board_boxes[0].__setitem__(slice(None), (287,113,29,19)),
            'bottom_loss': lambda v: v.certificate.board_boxes[1].__setitem__(slice(None), (359,113,29,16)),
            'width_loss': lambda v: v.certificate.board_boxes[1].__setitem__(2,28),
            'top_extension': lambda v: v.certificate.board_boxes[1].__setitem__(slice(None), (359,97,29,35)),
            'x_shift': lambda v: v.certificate.board_boxes[1].__setitem__(0,364),
            'wrong_mode': lambda v: setattr(v.certificate,'board_mode',5),
            'extra_board': lambda v: setattr(v.certificate,'unmatched_boards',1),
            'extra_price': lambda v: setattr(v.certificate,'unmatched_prices',1),
            'cap_black': lambda v: setattr(v.certificate.endcaps[1],'black_count',467),
            'upper_target': lambda v: setattr(v.partial[1],'icon_upper_bound',.8),
            'strong_word': lambda v: (setattr(v.rows[0].slots[0],'word_present',1),
                setattr(v.rows[0].slots[0],'word_iou',.82),setattr(v.rows[0].slots[0],'word_coverage',.90)),
            'wrong_row': lambda v: setattr(v.certificate,'row_index',1),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp();self.assess(mutate=mutate);self.assert_held()
        self.setUp()
        def wrong_row(value):
            value.rows[0].sy = value.certificate.row[1] = 122
            for slot in value.rows[0].slots: slot.sy = 122
        self.assess(mutate=wrong_row);self.assert_held()

    def normal_result(self, *, target=False, unknown=False):
        if not hasattr(self, 'ring'):
            tmp = tempfile.TemporaryDirectory(prefix='controller-ring102-')
            self.addCleanup(tmp.cleanup)
            self.ring = bank.NativeRingBank094Tests.build_library(
                native.CORE/'NG2Ring.c', Path(tmp.name)/'ring.so')
        scene = pixels102.shop_scene()
        pixels = pixels102.shop_pixels(target=target, missing_price=1 if unknown else None)
        status, result = pixels102.normal_assess(self.ring, pixels, scene)
        self.assertEqual((0,0),(status,result.status))
        return self.scene(), result

    def adopt_normal(self, scene, result):
        self.assertEqual(1, self.h.observe(scene)); job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now))
        evidence = cycle.Result.from_buffer_copy(bytes(result))
        evidence.started_ns = evidence.finished_ns = 0
        result.started_ns, result.finished_ns = self.h.now, self.h.now+1
        unchanged = cycle.Result.from_buffer_copy(bytes(result))
        unchanged.started_ns = unchanged.finished_ns = 0
        self.assertEqual(bytes(evidence), bytes(unchanged), 'normalize clock fields only, never certificate/outcome')
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(result)))
        return job

    def test_normal_classifier_negative_runs_through_durable_intent_real_restart_ack_and_next_floor(self):
        scene, result = self.normal_result()
        self.assertEqual((3,2,6),(result.outcome,result.coverage,result.certificate.policy_version))
        job = self.adopt_normal(scene,result)
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0], 'normal negative cannot bypass durable publication')
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick();self.assertEqual((1,3),(ready,restart.kind))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,restart.id,self.h.now,1,0,1))
        self.assertEqual(1,self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1,0),(self.h.status().restarts,self.h.status().terminal))
        proof = self.q.cycle()
        self.assertEqual(job.level_id,proof.level_id)
        self.assertEqual(0,self.h.tick()[0], 'ACK/new floor still waits for linked durable outcome')
        self.assertEqual(1,self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            proof.job_id,proof.next_floor_capture_id,self.h.prefix,self.h.now))
        self.assertEqual((job.level_id+1,0,0),(self.q.cycle().level_id,self.q.cycle().state,self.h.status().terminal))

    def test_normal_classifier_target_and_incomplete_result_hold_without_restart(self):
        for target,unknown in ((True,False),(False,True)):
            with self.subTest(target=target,unknown=unknown):
                self.setUp()
                scene,result=self.normal_result(target=target,unknown=unknown)
                self.assertNotEqual(3,result.outcome)
                self.adopt_normal(scene,result)
                self.q.pause_observed();self.assertEqual(1,self.q.durable())
                self.assertEqual(0,self.h.tick()[0]);self.assertEqual(0,self.h.status().restarts)
