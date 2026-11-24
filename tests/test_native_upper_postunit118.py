"""V2 post-unit next-beat preparation, using public calls and fixed phase.

CI260 D2->93/94 relative clocks are applied to three declared procedural
post-unit shapes. This is not the missing original CI261 rolling-model replay.
The old last-D3 fixture and its original relative clock are privately retained.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_snapshot118 as snapshot


class NativeUpperPostunit118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot.NativeUpperSnapshot118Tests.setUpClass()
        cls.lib=snapshot.NativeUpperSnapshot118Tests.lib

    @classmethod
    def tearDownClass(cls):
        snapshot.NativeUpperSnapshot118Tests.tearDownClass()

    def context(self,direction=1,moved=2,fault=None,clock='ci260'):
        fixture=snapshot.NativeUpperSnapshot118Tests(methodName='runTest')
        fixture.lib=self.lib
        fixture.setup_case(enabled=fault!='feature_off')
        self.addCleanup(fixture.doCleanups)
        self.t,self.h=fixture.t,fixture.h
        source,_=self.t.pending(direction)
        self.parent=self.t.q.cycle().continuation_deadline_ns
        self.next_direction=direction if moved<2 else 4
        for index in range(moved):
            wanted=direction if index<2 else 4
            command=self.t.ticket(source)
            self.assertEqual(wanted,command.direction)
            if index+1<moved:
                self.t.ack(command,source)
            else:
                while self.h.now<command.not_before_ns:
                    self.t.frame(source,min(20_000_000,command.not_before_ns-self.h.now))
                self.h.now=command.not_before_ns+(8_819_093 if clock=='ci261' else 1_481_500)
                self.assertEqual(1,self.lib.ng2_controller_begin(self.h.engine,command.id,self.h.now,1,0,1))
                self.h.now+=323_059_542 if clock=='ci261' else 351_364_917
                self.assertEqual(1,self.lib.ng2_controller_complete(self.h.engine,command.id,self.h.now,1))
                self.h.prefix=command.id
            source=native.translated(source,wanted)
            upcoming=direction if index==0 else 4
            source.tiles[native.DIRS[upcoming]]='floor'
            source.protected=self.t.cross({p for p,k in source.tiles.items() if k=='item'})
            if index+1<moved:
                self.h.observe_actual(self.h.scene(2,2,source,beat=True))
                self.t.assess(source)
            else:
                ack=self.h.events()[-1].end_ns
                if fault=='default_viable':
                    # A separate fast-response model: the observed unit cost
                    # itself fits the original parent even on the default.
                    self.observe(source,ack+1_000_000,ack+2_000_000,ack+3_000_000)
                    worker,release=ack+4_000_000,ack+8_000_000
                    self.unit_end=ack+2_000_000
                elif clock=='ci261':
                    self.observe(source,ack+28_620_292,ack+64_452_208,ack+86_150_917)
                    # The original release itself is not saved. Its first
                    # real return-fenced tick bounds it above; use that bound
                    # as this independent model's explicit worker release.
                    worker,release=ack+89_495_250,ack+102_391_250
                    self.unit_end=ack+64_452_208
                else:
                    self.observe(source,ack+14_255_417,ack+47_304_750,ack+63_880_292)
                    worker,release=ack+66_703_667,ack+79_506_208
                    self.unit_end=ack+47_304_750
                self.assertEqual((1,*native.DIRS[wanted]),
                    (self.h.events()[-1].motion,self.h.events()[-1].dx,self.h.events()[-1].dy))
                self.assertEqual(self.unit_end,self.h.status().last_capture_end_ns)
                self.assertEqual(self.h.events()[-1].observed_capture_id,self.t.q.cycle().capture_id)
                self.assess(source,worker,release,candidate=fault=='candidate')
                current=deepcopy(source)
                if fault=='floor':current.tiles.pop(native.DIRS[self.next_direction],None)
                elif fault=='protected':current.protected.add(native.DIRS[self.next_direction])
                start,end,commit,tick=(111_435_875,138_772_000,159_050_750,162_558_958) if clock=='ci261' else (
                    83_432_292,100_480_708,117_839_333,121_304_292)
                self.observe(current,ack+start,ack+end,ack+commit,
                    bad_prefix=fault=='prefix',bad_phase=fault=='phase')
                self.h.now=ack+tick
                self.source,self.last=current,command
        if fault=='past_NB':self.h.now=self.last.target_ns+native.PERIOD+20_000_000
        self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)

    def observe(self,source,start,end,commit,bad_prefix=False,bad_phase=False):
        self.h.now=commit
        scene=self.h.scene(2,2,source,beat=True)
        scene.beat_remaining=((5*native.SECOND-(start+end)//2)%native.PERIOD)/native.PERIOD
        if bad_phase:scene.beat_remaining=(scene.beat_remaining+.49)%1
        return self.h.observe_actual(scene,start=start,end=end,
            prefix=self.h.prefix+1 if bad_prefix else self.h.prefix)

    def assess(self,source,worker,release,candidate=False):
        # Reuse the established normal safe procedural result shape. These
        # bounded worker clocks are source inputs, not an actual Ring replay.
        from tests.test_native_ring094 import Result
        state=self.t.q.cycle()
        self.h.now=worker
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine,state.job_id,state.capture_id,state.prefix,worker))
        value=Result(abi=1,size=C.sizeof(Result),status=0,outcome=2 if candidate else 0,
            coverage=1,reason=1,selected_row=-1,selected_partial=0,partial_count=1,
            partial_safe_no_positive=0 if candidate else 1,
            started_ns=worker+1_104_333,finished_ns=release-179_041)
        x,y=max((p for p,k in source.tiles.items() if k=='item'),key=lambda p:abs(p[0]))
        slot=value.partial[0]
        slot.cx,slot.sy=448+36*x,207+36*y-48
        slot.icon_score=slot.icon_upper_bound=.771821673
        slot.icon_box[:]=(slot.cx-16,slot.sy+24,32,28)
        slot.outcome=value.outcome
        self.h.now=release
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,release,C.byref(value)))

    def test_each_postunit_shape_preserves_the_unissued_next_beat_with_observed_need(self):
        cases=[(d,m,'ci260') for d in (1,2) for m in (1,2,3)]
        for direction,moved,clock in cases:
            with self.subTest(direction=direction,prior_moves=moved,clock=clock):
                self.context(direction,moved,clock=clock)
                before=(self.h.status().inputs,self.h.status().moves)
                nominal_NB=self.last.target_ns+native.PERIOD-self.h.status().lead_ns
                self.assertGreater(nominal_NB,self.h.now)
                self.assertLess(nominal_NB-self.h.now,50_000_000)
                ready,command=self.h.tick()
                period=self.h.status().beat_period_ns
                default_target=command.target_ns+period if ready else self.h.status().next_target_ns
                default_last=default_target+(4-moved)*period
                self.assertLessEqual(default_last+80_000_000,self.parent)
                self.assertGreater(default_last+self.unit_end-self.last.target_ns,self.parent,
                    'the original observed unit cost must put the default final step outsideP')
                self.assertEqual(1,ready,'a proved post-unit next physical beat is still unissued and future')
                self.assertEqual((4,self.next_direction),(command.kind,command.direction))
                self.assertGreater(command.not_before_ns,self.h.now)
                self.assertLess(command.not_before_ns-self.h.now,50_000_000)
                self.assertEqual(10_000_000,command.deadline_ns-command.not_before_ns)
                self.assertLessEqual(abs(command.target_ns-(self.last.target_ns+native.PERIOD)),native.PERIOD*.08)
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)

    def test_viable_default_and_invalid_current_proofs_do_not_spend_a_short_window(self):
        for fault in ('default_viable','ci261_filter_viable','feature_off','candidate','floor','protected','prefix','phase','past_NB'):
            with self.subTest(fault=fault):
                self.context(fault=fault,clock='ci261' if fault=='ci261_filter_viable' else 'ci260')
                before=(self.h.status().inputs,self.h.status().moves)
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind==4)
                if fault in ('default_viable','ci261_filter_viable'):
                    last=self.h.status().next_target_ns+2*self.h.status().beat_period_ns
                    self.assertLessEqual(last+self.unit_end-self.last.target_ns,self.parent)
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)

    def test_a_new_postunit_ticket_never_reissues_after_publication_not_sent_or_unknown(self):
        for moved,outcome in ((m,o) for m in (1,2,3) for o in ('published','not_sent','unknown')):
            with self.subTest(prior_moves=moved,outcome=outcome):
                self.context(moved=moved)
                ready,command=self.h.tick()
                self.assertEqual(1,ready)
                if outcome!='published':
                    self.h.now=command.not_before_ns
                    if outcome=='unknown':
                        self.assertEqual(1,self.lib.ng2_controller_begin(
                            self.h.engine,command.id,self.h.now,1,0,1))
                        self.h.now+=self.t.SYNTH
                    self.assertEqual(1,self.lib.ng2_controller_complete(
                        self.h.engine,command.id,self.h.now,-1 if outcome=='unknown' else 0))
                again,next_command=self.h.tick()
                self.assertFalse(again and next_command.kind==4)
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)


if __name__=='__main__':unittest.main()
