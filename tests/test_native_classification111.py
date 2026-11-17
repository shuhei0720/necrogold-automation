"""Bounded data evidence across an independently confirmed observation MOVE.

Procedural clocks/pixels exercise public C. Received PNG motion non-transitivity
is calibrated separately; these fixtures never credit the retained early frame.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_fade100 as opened
from tests import test_native_full_framing101 as full
from tests import test_native_ring_bank094 as bank
from tests import test_native_offer_coverage104 as offer
from tests import test_native_single_offer108 as single
from tests.test_native_ring094 import Result

ROOT=Path(__file__).resolve().parents[1]


class NativeClassification111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous=native.CORE
        try:
            native.CORE=Path(os.environ.get('NECRO111_CLASSIFICATION_CORE',str(previous)))
            full.NativeFullFraming101Tests.setUpClass()
        finally:native.CORE=previous
        cls.lib=full.NativeFullFraming101Tests.lib
        cls.tmp=tempfile.TemporaryDirectory(prefix='classification111-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring=bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c',Path(cls.tmp.name)/'ring.so')

    @classmethod
    def tearDownClass(cls):full.NativeFullFraming101Tests.tearDownClass()

    def setUp(self):
        self.f=full.NativeFullFraming101Tests(methodName='runTest');self.f.lib=self.lib
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        build=self.f.full_source
        def source():
            value=build();value.tiles[(-1,-2)]='floor';return value
        self.f.full_source=source

    def pending(self):
        source,_,original,moves,command=self.f.ticket()
        self.h,self.q=self.f.h,self.f.q
        self.h.ack(command)
        latest=native.translated(source,1)
        latest.tiles[(7,3)]='door'
        first=deepcopy(latest);first.tiles[(8,3)]='stone'
        return source,latest,first,original,moves,command

    def frame(self,value,start,age=35_000_000,**kwargs):
        self.h.now=start+age
        self.assertEqual(1,self.h.observe_actual(self.h.scene(2,2,value,beat=True),
            start=start,end=start+12_000_000,**kwargs))
        return self.h.number

    def arrived(self,fault=None):
        source,latest,first,original,moves,command=self.pending()
        # Two accepted FULLs precede the existing visual comparison's earliest
        # eligible time. Neither one can establish this MOVE's displacement.
        self.frame(first,command.target_ns+20_000_000)
        retained=deepcopy(first)
        if fault=='near':retained.tiles[(-1,0)]='dirt'
        elif fault=='item':retained.tiles[(8,3)]='item';retained.protected.add((8,3))
        elif fault=='protection':retained.protected.add((8,3))
        elif fault=='motion':retained.signature=bytes([80])*23296
        retained_id=self.frame(retained,command.target_ns+60_000_000)
        before=self.q.cycle()
        self.assertEqual((3,moves),(self.h.status().input_state,self.h.status().moves))
        self.assertEqual(original.job_id,before.job_id)
        latest.tiles[(7,3)]='gold'  # Positive, remote DOOR -> GOLD exposure.
        latest.tiles[(8,3)]='dirt'
        if fault=='old_gold':latest.tiles[(-5,0)]='floor'
        final_start=command.target_ns+(220_000_000 if fault=='expired' else 114_000_000)
        observed_id=self.frame(latest,final_start,36_000_000)
        event=self.h.events()[-1]
        self.assertEqual((1,-1,0,observed_id),(event.motion,event.dx,event.dy,event.observed_capture_id))
        self.assertEqual(moves+1,self.h.status().moves)
        return retained,latest,original,retained_id,observed_id

    def test_latest_full_is_data_only_after_independent_move_and_keeps_original_clocks(self):
        retained,_,original,ident,observed=self.arrived()
        job=self.q.cycle()
        self.assertEqual((original.job_id+1,ident,1),(job.job_id,job.capture_id,job.pending),
            'the latest fresh FULL retained during this ACK must survive independent movement confirmation')
        self.assertEqual(original.hold_started_ns,job.hold_started_ns)
        self.assertLessEqual(job.continuation_deadline_ns,original.continuation_deadline_ns)
        self.assertEqual(job.capture_start_ns+150_000_000,job.deadline_ns)
        self.assertEqual(observed,self.h.status().last_capture_id)
        self.q.assess(0,1,full.NativeFullFraming101Tests.result)
        self.assertEqual((7,0),(self.q.cycle().state,self.q.cycle().pending))
        self.assertNotEqual(4,self.h.tick()[1].kind,'data UNKNOWN cannot restore a spent observation MOVE')

    def test_normal_complete_negative_is_bound_to_retained_pixels_and_current_pause(self):
        retained,_,_,ident,observed=self.arrived()
        job=self.q.cycle()
        scene=self.h.scene(2,2,retained,beat=True)
        status,result=offer.normal_assess(self.ring,offer.shop_pixels(left=340,sy=87),scene)
        self.assertEqual((0,3,2),(status,result.outcome,result.coverage))
        self.assertEqual(ident,job.capture_id)
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now))
        result.started_ns=self.h.now;self.h.now+=40_000_000;result.finished_ns=self.h.now
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now,C.byref(result)))
        self.assertEqual((3,0,4),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
        self.assertEqual(job.capture_start_ns+150_000_000,job.deadline_ns)
        self.q.pause_observed()
        self.assertGreaterEqual(self.q.cycle().pause_source_capture_id,observed)
        self.assertEqual(0,self.h.tick()[0])
        self.assertEqual(1,self.q.durable())
        ready,restart=self.h.tick();self.assertEqual((1,3),(ready,restart.kind))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,restart.id,self.h.now,1,0,1))

    def test_each_bridge_guard_or_original_source_deadline_falls_back_to_new_full(self):
        for fault in ('near','item','protection','old_gold','motion','expired'):
            with self.subTest(fault=fault):
                self.setUp()
                _,_,_,_,observed=self.arrived(fault)
                self.assertEqual(observed,self.q.cycle().capture_id)

    def test_target_candidate_remain_latched_and_never_restore_move(self):
        for missing,outcome in ((1,1),(None,2)):
            with self.subTest(outcome=outcome):
                self.setUp();retained,*_=self.arrived()
                kwargs={} if missing is None else {'missing_price':missing}
                status,result=offer.normal_assess(self.ring,
                    offer.shop_pixels(left=340,sy=87,target=True,target_name=False,**kwargs),
                    self.h.scene(2,2,retained,beat=True))
                self.assertEqual((0,outcome),(status,result.outcome))
                def produced(value):
                    start,end=value.started_ns,value.finished_ns
                    C.memmove(C.byref(value),C.byref(result),C.sizeof(value))
                    value.started_ns,value.finished_ns=start,end
                self.q.assess(outcome,1,produced)
                state=self.q.cycle()
                self.assertEqual((outcome,1,7),(state.outcome,state.candidate_latched,state.state))
                self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_unstable_or_other_prefix_never_replaces_the_data_pixel_lease(self):
        for fault in ('unstable','prefix'):
            with self.subTest(fault=fault):
                self.setUp();_,latest,_,original,moves,command=self.pending()
                start=command.target_ns+60_000_000;self.h.now=start+35_000_000
                kwargs={'stable':0} if fault=='unstable' else {'prefix':command.id+1}
                self.assertEqual(0,self.h.observe_actual(self.h.scene(2,2,latest,beat=True),
                    start=start,end=start+12_000_000,**kwargs))
                self.assertEqual((0,original.job_id),(self.q.cycle().queued_capture_id,self.q.cycle().job_id))
                self.frame(latest,command.target_ns+114_000_000,36_000_000)
                self.assertEqual(self.h.number,self.q.cycle().capture_id)
                self.assertEqual(moves+1,self.h.status().moves)

    def test_original_worker_limit_and_cancel_cannot_reuse_retained_source(self):
        for fault in ('source_deadline','cancel'):
            with self.subTest(fault=fault):
                self.setUp();self.arrived();state=self.q.cycle()
                if fault=='source_deadline':
                    self.h.now=state.deadline_ns+1
                    self.assertEqual(0,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        state.job_id,state.capture_id,state.prefix,self.h.now))
                    self.assertEqual((7,2),(self.q.cycle().state,self.q.cycle().status))
                else:
                    self.lib.ng2_controller_cancel(self.h.engine,self.h.now,2)
                    self.assertEqual(0,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        state.job_id,state.capture_id,state.prefix,self.h.now))
                self.assertNotEqual(4,self.h.tick()[1].kind)


class NativeClassificationRetry111Tests(unittest.TestCase):
    setUpClass=classmethod(NativeClassification111Tests.setUpClass.__func__)
    tearDownClass=classmethod(NativeClassification111Tests.tearDownClass.__func__)
    frame=NativeClassification111Tests.frame

    def setUp(self):
        self.q=cycle.NativeCycle094Tests(methodName='runTest');self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.p=opened.NativeOpenedFade100Tests(methodName='runTest');self.p.lib=self.lib
        self.addCleanup(self.p.doCleanups);self.h=self.q.h=self.p.harness()
        self.source=full.NativeFullFraming101Tests.full_source()
        self.source.tiles[(-1,-2)]='floor'

    def initial(self,age=110_000_000):
        start=self.h.now+20_000_000;self.frame(self.source,start,age)
        state=self.q.cycle();self.root=state
        self.h.now=start+max(age,111_000_000)
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now))
        return self.q.cycle()

    def timeout(self,state,change=None):
        self.h.now=state.deadline_ns+3
        result=Result(abi=1,size=C.sizeof(Result),status=2,outcome=0,
            selected_row=0,selected_partial=-1,row_count=1,
            started_ns=state.worker_started_ns+1,finished_ns=self.h.now-1)
        if change:change(result)
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(result)))
        return result

    def test_deadline_waits_for_actual_worker_then_fresh_full_owns_normal_negative(self):
        state=self.initial()
        self.h.now=state.deadline_ns+1
        self.assertEqual((0,0),(self.h.tick()[0],self.h.status().input_state),
            'an expired running worker must drain before any PAUSE or replacement job')
        self.assertEqual((state.job_id,1),(self.q.cycle().job_id,self.q.cycle().pending))
        self.timeout(state)
        self.assertEqual((3,0,2),(self.q.cycle().state,self.q.cycle().pending,self.q.cycle().status))
        fresh=self.frame(self.source,state.capture_start_ns+117_360_833,68_418_750)
        job=self.q.cycle()
        self.assertEqual((state.job_id+1,fresh,1),(job.job_id,job.capture_id,job.pending))
        self.assertEqual((self.root.hold_started_ns,self.root.continuation_deadline_ns),
            (job.hold_started_ns,job.continuation_deadline_ns))
        status,result=offer.normal_assess(self.ring,single.shop_pixels(),
            self.h.scene(2,2,self.source,beat=True))
        self.assertEqual((0,3),(status,result.outcome))
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now))
        result.started_ns=self.h.now;self.h.now+=40_000_000;result.finished_ns=self.h.now
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now,C.byref(result)))
        self.assertEqual((3,0,4,0),(self.q.cycle().outcome,self.q.cycle().status,
            self.q.cycle().state,self.h.status().moves))

    def test_late_slot_or_global_positive_hints_veto_fresh_negative(self):
        mutations={
            'candidate':lambda r:setattr(r,'outcome',1),
            'target':lambda r:setattr(r,'outcome',2),
            'slot_candidate':lambda r:setattr(r.rows[0].slots[1],'outcome',1),
            'slot_target':lambda r:setattr(r.rows[0].slots[1],'outcome',2),
            'score':lambda r:setattr(r.rows[0].slots[1],'icon_score',.80),
            'bound':lambda r:setattr(r.rows[0].slots[1],'icon_upper_bound',.80),
            'word':lambda r:(setattr(r.rows[0].slots[1],'word_iou',.82),
                setattr(r.rows[0].slots[1],'word_coverage',.90)),
            'partial':lambda r:(setattr(r,'partial_count',1),
                setattr(r.partial[0],'icon_upper_bound',.80)),
        }
        for name,change in mutations.items():
            with self.subTest(hint=name):
                self.setUp();state=self.initial();self.timeout(state,change)
                self.assertEqual((7,1,2),(self.q.cycle().state,self.q.cycle().candidate_latched,
                    self.q.cycle().status))
                self.frame(self.source,state.capture_start_ns+117_360_833,68_418_750)
                self.assertEqual((state.job_id,0),(self.q.cycle().job_id,self.q.cycle().pending))

    def fresh_retry(self):
        state=self.initial();self.timeout(state)
        self.frame(self.source,state.capture_start_ns+117_360_833,68_418_750)
        return self.q.cycle()

    def test_retry_unknown_has_no_movement_credit_and_at_most_two_new_jobs(self):
        job=self.fresh_retry();self.q.assess(0,1,full.NativeFullFraming101Tests.result)
        self.assertEqual((7,0,0),(self.q.cycle().state,self.h.status().moves,self.h.status().inputs))
        self.assertNotEqual(4,self.h.tick()[1].kind)
        self.setUp();job=self.fresh_retry()
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            job.job_id,job.capture_id,job.prefix,self.h.now))
        job=self.q.cycle()
        queued=self.frame(self.source,job.capture_start_ns+80_000_000,60_000_000)
        self.assertEqual((job.job_id,queued,1),(self.q.cycle().job_id,
            self.q.cycle().queued_capture_id,self.q.cycle().pending))
        self.timeout(job);last=self.q.cycle()
        self.assertEqual((job.job_id+1,queued,1),(last.job_id,last.capture_id,last.pending))
        self.assertEqual((self.root.hold_started_ns,self.root.continuation_deadline_ns),
            (last.hold_started_ns,last.continuation_deadline_ns))
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            last.job_id,last.capture_id,last.prefix,self.h.now))
        last=self.q.cycle();self.timeout(last)
        self.assertEqual((7,0,last.job_id),(self.q.cycle().state,self.q.cycle().pending,self.q.cycle().job_id))
        self.frame(self.source,last.capture_start_ns+160_000_000,60_000_000)
        self.assertEqual((last.job_id,0),(self.q.cycle().job_id,self.q.cycle().pending))

    def test_latest_unsafe_frame_blocks_retry_without_rewinding_to_earlier_safe_pixels(self):
        for fault in ('item','protection','gold','near','motion'):
            with self.subTest(fault=fault):
                self.setUp();state=self.initial()
                self.frame(self.source,state.capture_start_ns+20_000_000,100_000_000)
                unsafe=deepcopy(self.source)
                if fault=='item':unsafe.tiles[(8,3)]='item'
                elif fault=='protection':unsafe.protected.add((8,3))
                elif fault=='gold':unsafe.tiles[(8,3)]='gold'
                elif fault=='near':unsafe.tiles[(-1,0)]='dirt'
                else:unsafe.signature=bytes([80])*23296
                self.frame(unsafe,state.capture_start_ns+60_000_000,70_000_000)
                self.h.now=state.deadline_ns+1
                self.assertEqual((0,1),(self.h.tick()[0],self.q.cycle().pending))
                self.timeout(state)
                self.assertEqual((7,0),(self.q.cycle().state,self.q.cycle().pending))
                self.frame(self.source,state.capture_start_ns+160_000_000,60_000_000)
                self.assertEqual(state.job_id,self.q.cycle().job_id)

    def test_malformed_or_missing_deadline_report_never_starts_retry(self):
        changes={
            'abi':lambda r:setattr(r,'abi',0),
            'size':lambda r:setattr(r,'size',0),
            'count':lambda r:setattr(r,'row_count',5),
            'status':lambda r:setattr(r,'status',99),
            'clock':lambda r:setattr(r,'finished_ns',r.started_ns-1),
            'nan':lambda r:setattr(r.rows[0].slots[0],'icon_upper_bound',float('nan')),
        }
        for name,change in changes.items():
            with self.subTest(fault=name):
                self.setUp();state=self.initial();self.timeout(state,change)
                self.assertEqual((7,0,3),(self.q.cycle().state,self.q.cycle().pending,self.q.cycle().status))
        self.setUp();state=self.initial();self.h.now=state.deadline_ns+1
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,None))
        self.assertEqual((7,0,3),(self.q.cycle().state,self.q.cycle().pending,self.q.cycle().status))

    def test_source_149_150_ms_worker_begin_and_expired_before_start_keep_root_bound(self):
        for age in (149_000_000,150_000_000,150_000_001):
            with self.subTest(age=age):
                self.setUp();start=self.h.now+20_000_000;self.frame(self.source,start,age)
                state=self.q.cycle()
                self.assertEqual(int(age<=150_000_000),self.lib.ng2_controller_cycle_worker_begin(
                    self.h.engine,state.job_id,state.capture_id,state.prefix,self.h.now))
                if age<=150_000_000:self.timeout(self.q.cycle())
                self.assertEqual((3,0),(self.q.cycle().state,self.q.cycle().pending))
                self.frame(self.source,start+117_360_833,68_418_750)
                self.assertEqual((state.job_id+1,state.continuation_deadline_ns,state.hold_started_ns),
                    (self.q.cycle().job_id,self.q.cycle().continuation_deadline_ns,self.q.cycle().hold_started_ns))

    def test_prefix_cancel_parent_expiration_and_late_root_positive_preserve_freeze(self):
        for fault in ('prefix','unstable','cancel','parent'):
            with self.subTest(fault=fault):
                self.setUp();state=self.initial()
                if fault=='parent':
                    self.h.now=state.continuation_deadline_ns+1;self.h.tick()
                    self.assertEqual((7,0),(self.q.cycle().state,self.q.cycle().pending))
                    result=Result(abi=1,size=C.sizeof(Result),status=2,outcome=1,
                        selected_row=-1,selected_partial=-1,started_ns=state.worker_started_ns,
                        finished_ns=self.h.now)
                    self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
                        state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(result)))
                    self.assertEqual((7,1),(self.q.cycle().state,self.q.cycle().candidate_latched))
                    continue
                self.timeout(state)
                if fault=='cancel':self.lib.ng2_controller_cancel(self.h.engine,self.h.now,2)
                else:
                    self.h.now=state.capture_start_ns+190_000_000
                    kwargs={'prefix':state.prefix+1} if fault=='prefix' else {'stable':0}
                    self.assertEqual(0,self.h.observe_actual(self.h.scene(2,2,self.source,beat=True),
                        start=state.capture_start_ns+130_000_000,end=state.capture_start_ns+142_000_000,**kwargs))
                self.assertEqual((state.job_id,0),(self.q.cycle().job_id,self.q.cycle().pending))

    def test_terminal_drain_can_retain_a_late_candidate_without_reopening(self):
        state=self.initial();self.h.now=state.continuation_deadline_ns+1;self.h.tick()
        self.frame(self.source,self.h.now+1,60_000_000)
        self.q.pause_observed();self.assertEqual(1,self.q.durable());self.h.tick()
        self.assertEqual(1,self.h.status().terminal)
        frozen=(self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id,
            self.q.cycle().continuation_deadline_ns)
        result=Result(abi=1,size=C.sizeof(Result),status=2,outcome=1,
            selected_row=-1,selected_partial=-1,started_ns=state.worker_started_ns,
            finished_ns=self.h.now)
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(result)))
        self.assertEqual((8,1,1),(self.q.cycle().state,self.q.cycle().candidate_latched,self.h.status().terminal))
        self.assertEqual(frozen,(self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id,
            self.q.cycle().continuation_deadline_ns))
        self.assertEqual(0,self.h.tick()[0])


if __name__=='__main__':unittest.main()
