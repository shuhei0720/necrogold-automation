"""TEST111 policy15 producer and independent Controller adoption boundary.

Procedural pixels establish proof handoff, not unrecorded phone continuation.
"""
import ctypes as C
import unittest

from tests import test_native_controller as native
from tests import test_native_goods111 as goods
from tests import test_native_offer_coverage104 as offer
from tests import test_native_single_offer108 as single
from tests.test_native_ring094 import Result


class NativeUpperAdoption111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        single.NativeSingleOfferController108Tests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        single.NativeSingleOfferController108Tests.tearDownClass.__func__(cls)

    setUp = single.NativeSingleOfferController108Tests.setUp

    def normal(self, *, mirror=False, scene_change=None, result_change=None, **pixel_kwargs):
        scene = goods.upper_scene(mirror=mirror)
        pixels = goods.prices(offer.shop_pixels(left=301,sy=225,**pixel_kwargs),301,225)
        status, value = offer.normal_assess(self.ring,pixels,scene)
        self.assertEqual((0,0),(status,value.status))
        if scene_change:
            scene_change(scene)
        self.assertEqual(1,self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job=self.q.cycle()
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine,job.job_id,job.capture_id,job.prefix,self.h.now))
        if result_change:
            result_change(value)
        value.started_ns,value.finished_ns=self.h.now,self.h.now+1
        self.h.now+=2
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,job.job_id,
            job.capture_id,job.prefix,self.h.now,C.byref(value)))
        return job,value

    def test_normal_upper_producer_requires_durable_pause_intent_and_real_restart_outcome(self):
        for mirror in (False,True):
            with self.subTest(mirror=mirror):
                self.setUp()
                job,result=self.normal(mirror=mirror)
                self.assertEqual((3,2,15),(result.outcome,result.coverage,result.certificate.policy_version))
                self.assertEqual((3,0,4),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state),
                    'the independent Controller must adopt the positive upper-side offer proof')
                self.q.pause_observed()
                self.assertEqual(0,self.h.tick()[0])
                self.assertEqual(1,self.q.durable())
                ready,restart=self.h.tick()
                self.assertEqual((1,3),(ready,restart.kind))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,restart.id,self.h.now,1,0,1))
                self.assertEqual(1,self.q.intent(restart))
                self.q.next_floor(restart)
                waiting=self.q.cycle()
                self.assertEqual((1,job.level_id),(self.h.status().restarts,waiting.level_id))
                self.assertEqual(0,self.h.tick()[0])
                self.assertEqual(1,self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
                    waiting.job_id,waiting.next_floor_capture_id,self.h.prefix,self.h.now))
                self.assertEqual((job.level_id+1,0),(self.q.cycle().level_id,self.q.cycle().state))

    def test_controller_rechecks_every_upper_wall_and_exact_offer_projection(self):
        support={(-6,y) for y in range(-3,5)}|{(x,-3) for x in range(-6,-1)}|{(0,-1),(0,1)}
        def missing(scene,point):
            offer.set_tile(scene,*point,0)
            offer.set_tile(scene,10,4,2)
        changes=[lambda s,p=p:missing(s,p) for p in sorted(support)]
        changes += [lambda s:offer.set_tile(s,0,0,4),lambda s:offer.set_tile(s,-3,3,0),
            lambda s:offer.set_tile(s,-5,2,0),lambda s:offer.set_tile(s,8,3,6),
            lambda s:s.protected_cells.__setitem__(7*23+7,0),
            lambda s:s.protected_cells.__setitem__(0,1)]
        for index,change in enumerate(changes):
            with self.subTest(scene_mutation=index):
                self.setUp();_,result=self.normal(scene_change=change)
                self.assertEqual(3,result.outcome,'the unchanged worker certificate remains positive')
                self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind in (3,4))

    def test_controller_rejects_forged_upper_numeric_faces_prices_and_binary_absence(self):
        changes=[lambda r:setattr(r.certificate,'layout_version',2),
            lambda r:setattr(r.certificate,'policy_version',16),
            lambda r:setattr(r.certificate,'board_mode',9),
            lambda r:setattr(r.certificate,'actual_gold_cells',13),
            lambda r:setattr(r.certificate.endcaps[0],'floor_upper',0),
            lambda r:r.certificate.board_boxes[1].__setitem__(1,225+5),
            lambda r:r.certificate.price_boxes[1].__setitem__(1,225+89),
            lambda r:setattr(r.rows[0].slots[0],'icon_upper_bound',.8),
            lambda r:setattr(r.certificate,'observed_prices',2)]
        for index,change in enumerate(changes):
            with self.subTest(certificate_mutation=index):
                self.setUp();self.normal(result_change=change)
                self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind in (3,4))


if __name__=='__main__':
    unittest.main()
