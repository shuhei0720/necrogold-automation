"""A pending FULL classification retains DATA authority across distant material.

These public Controller/normal Ring fixtures are declared procedural contexts,
not reconstructed private state or unrecorded phone images.
"""
import ctypes as C
from copy import deepcopy

from tests import test_native_controller as native
from tests import test_native_goods113 as goods
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular


class NativeCurrentData118Tests(goods.Goods113Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_observe_irregular_at.restype = None

    def pending_current(self):
        p = current.NativeCurrentView114Tests(methodName='runTest')
        p.lib, p.ring = self.lib, self.ring
        p.setUp()
        self.addCleanup(p.doCleanups)
        p.queue_current()
        self.p = p
        self.h, self.q = p.h, p.q
        return p

    def start_worker(self):
        value = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            value.job_id, value.capture_id, value.prefix, self.h.now))
        return value

    @staticmethod
    def distant_material(p):
        value = deepcopy(p.current)
        value.tiles[(5, 4)] = 'dirt'
        return value

    def test_pending_full_keeps_normal_negative_without_reviving_observation_move(self):
        p = self.pending_current()
        before = self.q.cycle()
        counts = self.h.status().inputs, self.h.status().moves
        self.start_worker()
        value = p.producer(p.current, left=375, sy=44)
        self.assertEqual((3, 2), (value.outcome, value.coverage))
        changed = deepcopy(p.current)
        changed.tiles[(5, 4)] = 'dirt'
        p.frame(changed)
        self.assertEqual((before.job_id, before.capture_id, before.prefix, 1),
            (self.q.cycle().job_id, self.q.cycle().capture_id,
             self.q.cycle().prefix, self.q.cycle().pending))
        p.commit(value)
        self.assertEqual((3, 0, 4), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state),
            'distant material cannot turn an on-time immutable FULL negative into SCREEN')
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
        p.immutable_parent(before)
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_data_downgrade_unknown_stays_held_without_observation_move(self):
        p = self.pending_current()
        before = self.start_worker()
        counts = self.h.status().inputs, self.h.status().moves
        value = p.producer(p.current, left=375, sy=44, unknown=True)
        self.assertEqual(0, value.outcome)
        p.frame(self.distant_material(p))
        p.commit(value)
        self.assertEqual((0, 0, 7), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        p.no_move_or_restart()
        p.immutable_parent(before)
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_bound_positive_remains_prior_to_distant_material(self):
        p = self.pending_current()
        self.start_worker()
        counts = self.h.status().inputs, self.h.status().moves
        value = p.producer(p.current, left=375, sy=44, target=True)
        self.assertEqual(2, value.outcome)
        p.frame(self.distant_material(p))
        p.commit(value)
        self.assertEqual((2, 1, 7), (self.q.cycle().outcome,
            self.q.cycle().candidate_latched, self.q.cycle().state))
        p.no_move_or_restart()
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_changed_goods_protection_local_floor_door_and_gold_loss_still_veto(self):
        for fault in ('item', 'protection', 'origin', 'neighbor', 'door', 'gold_loss'):
            with self.subTest(fault=fault):
                p = self.pending_current()
                self.start_worker()
                counts = self.h.status().inputs, self.h.status().moves
                value = p.producer(p.current, left=375, sy=44)
                self.assertEqual(3, value.outcome)
                changed = self.distant_material(p)
                if fault == 'item': changed.tiles[(5, 4)] = 'item'
                elif fault == 'protection': changed.protected.add((5, 4))
                elif fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'neighbor': changed.tiles[(1, 0)] = 'dirt'
                elif fault == 'door': changed.tiles[(5, 4)] = 'door'
                else: changed.tiles[(-4, -1)] = 'dirt'
                p.frame(changed)
                p.commit(value)
                self.assertNotEqual((3, 0, 4), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state))
                p.no_move_or_restart()
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_a_later_safe_image_does_not_erase_a_prior_sticky_rejection(self):
        p = self.pending_current()
        self.start_worker()
        value = p.producer(p.current, left=375, sy=44)
        unsafe = self.distant_material(p)
        unsafe.protected.add((5, 4))
        p.frame(unsafe)
        p.frame(self.distant_material(p))
        p.commit(value)
        self.assertEqual((0, 5, 7), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        p.no_move_or_restart()

    def test_unchanged_source_keeps_existing_two_proof_observation_path(self):
        p = self.pending_current()
        self.start_worker()
        value = p.producer(p.current, left=375, sy=44, unknown=True)
        p.frame(p.current)
        p.commit(value)
        self.assertEqual((0, 0, 3), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        p.frame(p.current)
        p.frame(p.current)
        command = self.h.next_move(p.current)
        self.assertEqual((4, 3), (command.kind, command.direction))

    def test_downgrade_cannot_reopen_an_observation_epoch_after_result(self):
        p = self.pending_current()
        self.start_worker()
        value = p.producer(p.current, left=375, sy=44, unknown=True)
        p.commit(value)
        self.assertEqual(3, self.q.cycle().state)
        p.frame(self.distant_material(p))
        self.assertEqual((0, 5, 7), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        p.no_move_or_restart()

    def test_a_fresh_material_image_does_not_extend_the_original_parent(self):
        p = self.pending_current()
        before = self.start_worker()
        counts = self.h.status().inputs, self.h.status().moves
        value = p.producer(p.current, left=375, sy=44)
        self.h.now = before.continuation_deadline_ns+1
        p.frame(self.distant_material(p))
        p.commit(value)
        self.assertNotEqual((3, 0, 4), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns,
            before.continuation_deadline_ns)
        p.no_move_or_restart()
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
