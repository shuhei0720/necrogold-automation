"""Independent policy9 full-offer coverage on a procedural observed floor."""
import ctypes as C
import unittest
from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_structural_cycle096 as structural

class NativeObservedShopController104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass();cls.lib=cycle.NativeCycle094Tests.lib
    @classmethod
    def tearDownClass(cls):cycle.NativeCycle094Tests.tearDownClass()
    def setUp(self):
        self.q=cycle.NativeCycle094Tests(methodName='runTest');self.q.setUp();self.addCleanup(self.q.doCleanups);self.h=self.q.h
    index=staticmethod(structural.NativeStructuralCycle096Tests.index)
    def scene(self):
        s=self.h.scene(state=2,gold=2);s.goods=2;s.tiles[self.index(-8,1)]=2
        for x in(-4,0):s.tiles[self.index(x,-3)]=1
        for x in range(-3,0):
            s.tiles[self.index(x,-3)]=6;s.tiles[self.index(x,-2)]=1
            for dx,dy in((0,0),(-1,0),(1,0),(0,-1),(0,1)):s.protected_cells[self.index(x+dx,-3+dy)]=1
        return s
    @staticmethod
    def certificate(value,scene,left=339,sy=43):
        structural.NativeStructuralCycle096Tests.certificate(value,scene,left,sy)
        value.certificate.policy_version=value.certificate.board_mode=9
    def assess(self,scene=None,mutate=None):
        s=self.scene()if scene is None else scene;self.assertEqual(1,self.h.observe(s))
        def result(v):
            self.certificate(v,s)
            if mutate:mutate(v)
        return self.q.assess(3,2,result)
    def test_three_observed_floor_cells_under_offers_and_two_full_faces_have_independent_authority(self):
        self.assess()
        self.assertEqual((3,0,4),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state),
            'full witnessed offers do not require inventing a specific unseen enclosure')
    def held(self):
        self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
        ready,command=self.h.tick();self.assertFalse(ready and command.kind in(3,4))
        self.assertEqual(0,self.h.status().restarts)
    def test_observed_items_floor_caps_gold_and_exact_protection_are_all_independent(self):
        for point in [(-4,-3),(-3,-3),(-2,-3),(-1,-3),(0,-3),(-3,-2),(-2,-2),(-1,-2),(-8,1)]:
            with self.subTest(missing=point):
                self.setUp();scene=self.scene();scene.tiles[self.index(*point)]=0;self.assess(scene);self.held()
        for fault in ('extra_item','extra_protection','missing_protection'):
            with self.subTest(fault=fault):
                self.setUp();scene=self.scene()
                if fault=='extra_item':scene.tiles[self.index(8,3)]=6
                elif fault=='extra_protection':scene.protected_cells[self.index(8,3)]=1
                else:scene.protected_cells[self.index(-3,-4)]=0
                self.assess(scene);self.held()
        self.setUp();scene=self.scene();scene.protected_cells[self.index(-3,-4)]=2
        self.assertEqual(0,self.h.observe(scene),'nonbinary Scene is rejected before any worker authority')
        self.assertEqual(0,self.q.cycle().capture_id)
        ready,command=self.h.tick();self.assertFalse(ready and command.kind in(3,4))
    def test_common_certificate_faces_prices_target_and_source_count_remain_strict(self):
        changes={
            'missing_right':lambda v:(v.certificate.board_boxes[1].__setitem__(slice(None),(0,0,0,0)),v.certificate.board_counts.__setitem__(1,0)),
            'count149':lambda v:v.certificate.board_counts.__setitem__(0,149),
            'partial_right':lambda v:v.certificate.board_boxes[1].__setitem__(3,15),
            'pair':lambda v:v.certificate.board_boxes[1].__setitem__(0,500),
            'extra_board':lambda v:setattr(v.certificate,'unmatched_boards',1),
            'extra_price':lambda v:setattr(v.certificate,'unmatched_prices',1),
            'missing_price':lambda v:v.certificate.price_boxes[0].__setitem__(slice(None),(0,0,0,0)),
            'merchant':lambda v:setattr(v.certificate,'merchant_score',.99),
            'glyph':lambda v:v.certificate.sign_iou.__setitem__(0,.99),
            'edge':lambda v:v.certificate.board_edge_counts[1].__setitem__(0,1),
            'black_cap':lambda v:setattr(v.certificate.endcaps[0],'black_count',63),
            'gold_count':lambda v:setattr(v.certificate,'actual_gold_cells',2),
            'accepted_two':lambda v:setattr(v.certificate,'accepted_rows',2),
            'wrong_mode':lambda v:setattr(v.certificate,'board_mode',8),
            'row_candidate':lambda v:setattr(v.rows[0].slots[0],'outcome',1),
            'partial_upper':lambda v:setattr(v.partial[1],'icon_upper_bound',.8),
            'strong_word':lambda v:(setattr(v.partial[0],'word_present',1),setattr(v.partial[0],'word_iou',.82),setattr(v.partial[0],'word_coverage',.90)),
            'partial_domain':lambda v:v.partial[1].non_target_icon_box.__setitem__(2,35),
        }
        for fault,mutate in changes.items():
            with self.subTest(fault=fault):self.setUp();self.assess(mutate=mutate);self.held()
    def test_central_nonhud_band_and_cell_mapping_are_independent(self):
        for left,sy in ((196,43),(538,43),(339,20),(339,225),(358,43),(339,69)):
            with self.subTest(left=left,sy=sy):
                self.setUp();scene=self.scene();self.assertEqual(1,self.h.observe(scene))
                self.q.assess(3,2,lambda value:self.certificate(value,scene,left,sy));self.held()
    def normal(self,*,target=False,unknown=False):
        from pathlib import Path
        import tempfile
        from tests import test_native_offer_coverage104 as pixels
        from tests import test_native_ring_bank094 as bank
        if not hasattr(self,'ring'):
            tmp=tempfile.TemporaryDirectory(prefix='observed-shop-controller104-');self.addCleanup(tmp.cleanup)
            self.ring=bank.NativeRingBank094Tests.build_library(native.CORE/'NG2Ring.c',Path(tmp.name)/'ring.so')
        s=pixels.shop_scene();rgba=pixels.shop_pixels(target=target,missing_price=1 if unknown else None)
        status,value=pixels.normal_assess(self.ring,rgba,s)
        self.assertEqual((0,0),(status,value.status))
        self.assertEqual(1,self.h.observe(native.Scene.from_buffer_copy(bytes(s))))
        job=self.q.cycle();self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,job.job_id,job.capture_id,job.prefix,self.h.now))
        original=cycle.Result.from_buffer_copy(bytes(value));original.started_ns=original.finished_ns=0
        value.started_ns,value.finished_ns=self.h.now,self.h.now+1
        normalized=cycle.Result.from_buffer_copy(bytes(value));normalized.started_ns=normalized.finished_ns=0
        self.assertEqual(bytes(original),bytes(normalized),'only result clocks are normalized; producer evidence is immutable')
        self.h.now+=2;self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,job.job_id,job.capture_id,job.prefix,self.h.now,C.byref(value)))
        return job,value
    def test_normal_policy9_producer_reaches_durable_intent_restart_ack_and_next_floor(self):
        job,value=self.normal();self.assertEqual((3,2,9),(value.outcome,value.coverage,value.certificate.policy_version))
        self.assertEqual((3,0,4),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
        self.q.pause_observed();self.assertEqual(0,self.h.tick()[0]);self.assertEqual(1,self.q.durable())
        ready,restart=self.h.tick();self.assertEqual((1,3),(ready,restart.kind))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,restart.id,self.h.now,1,0,1))
        self.assertEqual(1,self.q.intent(restart));self.q.next_floor(restart)
        self.assertEqual((1,0),(self.h.status().restarts,self.h.status().terminal));waiting=self.q.cycle()
        self.assertEqual(job.level_id,waiting.level_id);self.assertEqual(0,self.h.tick()[0])
        self.assertEqual(1,self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,waiting.job_id,waiting.next_floor_capture_id,self.h.prefix,self.h.now))
        self.assertEqual((job.level_id+1,0),(self.q.cycle().level_id,self.q.cycle().state))
    def test_normal_target_and_incomplete_results_never_acquire_restart_authority(self):
        for target,unknown in((True,False),(False,True)):
            with self.subTest(target=target,unknown=unknown):
                self.setUp();_,value=self.normal(target=target,unknown=unknown)
                self.assertNotEqual(3,value.outcome);self.assertNotEqual(3,self.q.cycle().outcome)
                ready,command=self.h.tick();self.assertFalse(ready and command.kind in(3,4))
                self.assertEqual(0,self.h.status().restarts)
