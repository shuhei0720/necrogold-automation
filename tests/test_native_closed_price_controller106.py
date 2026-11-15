"""Normal closed-price pixel producer joined to public C cycle authority."""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_offer_controller105 as previous
from tests import test_native_ring_bank094 as bank
from tests import test_native_closed_price106 as prices


class NativeClosedPriceController106Tests(unittest.TestCase):
    setUpClass=classmethod(previous.NativeOfferController105Tests.setUpClass.__func__)
    tearDownClass=classmethod(previous.NativeOfferController105Tests.tearDownClass.__func__)
    setUp=previous.NativeOfferController105Tests.setUp
    restart_after_durable_intent=previous.NativeOfferController105Tests.restart_after_durable_intent
    held=previous.NativeOfferController105Tests.held

    def normal(self,slot=2,variation=True,target=False,target_name=True,mutate=None,
               container_id=11,pixels=None,scene=None,price_height=7):
        if not hasattr(self,'ring'):
            tmp=tempfile.TemporaryDirectory(prefix='closed-price-controller106-');self.addCleanup(tmp.cleanup)
            self.ring=bank.NativeRingBank094Tests.build_library(native.CORE/'NG2Ring.c',Path(tmp.name)/'ring.so')
        scene=prices.single.shop_scene() if scene is None else scene
        pixels=prices.shop_pixels(slot=slot,variation=variation,target=target,
            target_name=target_name,container_id=container_id,
            price_height=price_height) if pixels is None else pixels
        status,value=prices.single.normal_assess(self.ring,pixels,scene)
        self.assertEqual((0,0),(status,value.status))
        self.assertEqual(1,self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job=self.q.cycle();self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now))
        original=bytes(value);value.started_ns,value.finished_ns=self.h.now,self.h.now+1
        check=cycle.Result.from_buffer_copy(bytes(value));old=cycle.Result.from_buffer_copy(original)
        check.started_ns=check.finished_ns=old.started_ns=old.finished_ns=0
        self.assertEqual(bytes(old),bytes(check),'only the procedural clock is normalized')
        if mutate:mutate(value)
        self.h.now+=2
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,job.job_id,
            job.capture_id,job.prefix,self.h.now,C.byref(value)))
        return job,value

    def test_normal_closed_price_reaches_durable_intent_restart_ack_and_next_floor(self):
        for slot in range(3):
            for height in (7,8,9):
                with self.subTest(slot=slot,height=height):
                    self.setUp();job,value=self.normal(slot=slot,price_height=height)
                    self.assertEqual((3,2,7,2),(value.outcome,value.coverage,
                        value.certificate.policy_version,value.certificate.layout_version))
                    self.assertEqual((235,height),tuple(value.certificate.price_boxes[slot])[1::2])
                    self.restart_after_durable_intent(job)

    def test_target_candidate_and_forged_closed_price_never_restart(self):
        for named,expected in ((True,2),(False,1)):
            self.setUp();_,value=self.normal(target=True,target_name=named)
            self.assertEqual(expected,value.outcome);self.held()
        changes={
            'old version':lambda r:setattr(r.certificate,'layout_version',1),
            'wrong id':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_container_id',12),
            'score':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_icon_score',.994999999),
            'coverage':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_gold_coverage',.949999999),
            'price before body end':lambda r:r.certificate.price_boxes[2].__setitem__(1,225),
            'ordinary price shifted':lambda r:r.certificate.price_boxes[0].__setitem__(1,235),
            'second closed':lambda r:setattr(r.rows[r.selected_row].slots[0],'ignored_container_id',11),
            'extra price':lambda r:setattr(r.certificate,'unmatched_prices',1),
        }
        for label,mutate in changes.items():
            with self.subTest(label=label):
                self.setUp();self.normal(mutate=mutate);self.held()
        # Isolate each price bound using a complete ordinary baseline. ID9's
        # body ends at232, so a 10px price234..243 is inside B but still too tall.
        def closed_beyond(value):
            box=value.certificate.price_boxes[2];box[1]=236;box[3]=9
        def ordinary_beyond(value):
            for index in (0,1):
                box=value.certificate.price_boxes[index];box[1]=235;box[3]=8
        def too_tall(value):
            box=value.certificate.price_boxes[2];box[1]=234;box[3]=10
        for label,identity,mutate in (
                ('closed beyond B',11,closed_beyond),
                ('ordinary beyond original band',11,ordinary_beyond),
                ('height above nine within B',9,too_tall),
                ('expanded price with old layout',11,
                    lambda r:setattr(r.certificate,'layout_version',1))):
            with self.subTest(label=label):
                self.setUp();self.normal(container_id=identity,price_height=9,
                    mutate=mutate);self.held()

    def test_canonical_closed_identities_reach_durable_restart_in_each_offer_slot(self):
        for identity in (9,10):
            for slot in range(3):
                for height in (7,8,9):
                    with self.subTest(identity=identity,slot=slot,height=height):
                        self.setUp();job,value=self.normal(slot=slot,container_id=identity,
                            price_height=height)
                        self.assertEqual((3,2,7,2),(value.outcome,value.coverage,
                            value.certificate.policy_version,value.certificate.layout_version))
                        self.assertEqual(identity,value.rows[value.selected_row].slots[slot].ignored_container_id)
                        self.assertEqual((235,height),tuple(value.certificate.price_boxes[slot])[1::2])
                        self.restart_after_durable_intent(job)

    def test_c_independently_checks_integer_coverage_boundaries_and_lattice_for_every_identity(self):
        def strong_only(value):
            slot=value.rows[value.selected_row].slots[2]
            slot.ignored_gold_iou=slot.ignored_dark_iou=.8
            return slot
        for identity in (9,10,11):
            for component in ('gold','dark'):
                ink=prices.closed_entry(identity)['container_shape'][component+'_ink']
                minimum=95*ink//100
                for count,accepted in ((minimum,True),(minimum-1,False)):
                    with self.subTest(identity=identity,component=component,count=count):
                        self.setUp()
                        def coverage(value):
                            slot=strong_only(value)
                            setattr(slot,'ignored_'+component+'_coverage',round(count/ink,9))
                        self.normal(container_id=identity,mutate=coverage)
                        if accepted:
                            self.assertEqual((3,0,4),(self.q.cycle().outcome,
                                self.q.cycle().status,self.q.cycle().state))
                        else:self.held()
            for fault in ('non_lattice','low_color','nan','infinite','impossible_iou','old_layout'):
                with self.subTest(identity=identity,fault=fault):
                    self.setUp()
                    def forged(value):
                        slot=strong_only(value)
                        if fault=='non_lattice':
                            ink=prices.closed_entry(identity)['container_shape']['gold_ink']
                            slot.ignored_gold_coverage=round((95*ink//100+.25)/ink,9)
                        elif fault=='low_color':slot.ignored_icon_score=.994999999
                        elif fault=='nan':slot.ignored_dark_coverage=float('nan')
                        elif fault=='infinite':slot.ignored_gold_iou=float('inf')
                        elif fault=='impossible_iou':slot.ignored_dark_iou=.001
                        else:value.certificate.layout_version=1
                    self.normal(container_id=identity,mutate=forged);self.held()

    def test_complete_prices_and_unknown_closed_lower_cell_keep_version_two_identity(self):
        for identity in (9,10,11):
            for slot in range(3):
                for height in (7,8,9):
                    with self.subTest(identity=identity,slot=slot,height=height):
                        pixels=bytearray(prices.shop_pixels(slot=slot,variation=True,
                            container_id=identity,price_height=height))
                        scene=prices.closed.shop_scene(ax=-5,ay=0,container_slot=slot)
                        before=bytes(scene)
                        prices.single.draw_faces(pixels,267,153,((-15,-14,30,29),(-15,-14,30,29)))
                        # Complete ordinary prices retain their old lower band;
                        # only the positively identified closed slot reaches B.
                        for ordinary in (s for s in range(3) if s!=slot):
                            cx=267+36*ordinary
                            for y in range(222,244):
                                for x in range(cx-11,cx+12):prices.single._put(pixels,x,y,(27,17,15))
                            for i in range(3):
                                for y,row in enumerate(('111','101','101','101','101','101','111')):
                                    for x,bit in enumerate(row):
                                        if bit=='1':prices.single._put(pixels,cx-6+4*i+x,235+y,(245,245,245))
                        self.setUp();job,value=self.normal(container_id=identity,slot=slot,
                            pixels=bytes(pixels),scene=scene)
                        self.assertEqual((3,2,10,2),(value.outcome,value.coverage,
                            value.certificate.policy_version,value.certificate.layout_version))
                        self.assertEqual((3,0),(value.certificate.observed_prices,
                            value.certificate.unmatched_prices))
                        self.assertEqual(identity,value.rows[value.selected_row].slots[slot].ignored_container_id)
                        self.assertEqual((235,height),tuple(value.certificate.price_boxes[slot])[1::2])
                        self.assertEqual(before,bytes(scene),'no UNKNOWN is filled to manufacture FLOOR')
                        self.restart_after_durable_intent(job)


if __name__=='__main__':unittest.main()
