"""V2 last D3: public lifecycle with CI260's relative response clocks.

The physical phase is fixed. This retained last-D3 boundary adds an explicit
post-D1 control callback delay until the next target itself is past. Its
original future-NB fixture is privately preserved; the updated independent
fixture is not a replay of CI260's callback timing. Sparse scenes/results do
not certify actual Swift AX scheduling or iPhone acceptance.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_snapshot118 as snapshot
from tests.test_native_ring094 import Result


class NativeUpperLastSlot118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot.NativeUpperSnapshot118Tests.setUpClass()
        cls.lib = snapshot.NativeUpperSnapshot118Tests.lib

    @classmethod
    def tearDownClass(cls):
        snapshot.NativeUpperSnapshot118Tests.tearDownClass()

    def context(self, direction=1, enabled=True, fault=None):
        fixture = snapshot.NativeUpperSnapshot118Tests(methodName='runTest')
        fixture.lib = self.lib
        fixture.setup_case(enabled=enabled)
        self.addCleanup(fixture.doCleanups)
        self.t, self.h = fixture.t, fixture.h
        source, _ = self.t.pending(direction)
        parent = self.t.q.cycle().continuation_deadline_ns
        for index, wanted in enumerate((direction, direction, 4, 4)):
            command = self.t.ticket(source)
            self.assertEqual(wanted, command.direction)
            if index < 2:
                self.t.ack(command, source)
            else:
                while self.h.now < command.not_before_ns:
                    self.t.frame(source, min(20_000_000, command.not_before_ns-self.h.now))
                # Actual CI260 D1/D2 begin offsets and ACK call intervals.
                self.h.now = command.not_before_ns+(612_848 if index == 2 else 1_481_500)
                self.assertEqual(1, self.lib.ng2_controller_begin(
                    self.h.engine, command.id, self.h.now, 1, 0, 1))
                duration = 291_588_542 if index == 2 else 351_364_917
                if index == 3 and fault == 'ordinary':
                    duration = self.t.SYNTH
                self.h.now += duration
                self.assertEqual(1, self.lib.ng2_controller_complete(
                    self.h.engine, command.id, self.h.now, 1))
                self.h.prefix = command.id
            source = native.translated(source, wanted)
            source.tiles[native.DIRS[direction if index == 0 else 4]] = 'floor'
            if index == 3:
                items = {p for p,k in source.tiles.items() if k == 'item'}
                kept = set(sorted(items, key=lambda p: abs(p[0]))[:3])
                for point in items-kept:
                    source.tiles.pop(point)
                source.goods = 'visible'
            source.protected = self.t.cross({p for p,k in source.tiles.items() if k == 'item'})
            if index < 2:
                self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
                self.t.assess(source)
            else:
                ack = self.h.events()[-1].end_ns
                if index == 2:
                    self.observe(source, ack+16_992_875, ack+44_647_916, ack+64_750_208)
                    self.assess(source, ack+70_218_666, ack+77_036_375)
                    # Keep original frame80's relative capture clock, but
                    # explicitly delay the first control callback beyond the
                    # next physical target. This independent adverse input
                    # cannot be rescued by a future-NB post-unit exception.
                    self.observe(source, ack+85_175_000, ack+163_771_791, ack+184_773_208)
                    self.h.now = command.target_ns+native.PERIOD+20_000_000
                    ready, _ = self.h.tick()
                    self.assertFalse(ready, 'a next physical target already past cannot fund D2')
                    self.d1 = command
                else:
                    self.assertGreater(command.target_ns-self.d1.target_ns,
                        native.PERIOD+native.PERIOD//2, 'the original delayed response loses one beat')
                    self.observe(source, ack+14_255_417, ack+47_304_750, ack+63_880_292)
                    self.assertEqual((1,0), (self.h.events()[-1].motion,self.h.events()[-1].dx))
                    self.assess(source, ack+66_703_667, ack+79_506_208,
                        candidate=fault == 'candidate')
                    current = deepcopy(source)
                    if fault == 'floor':
                        current.tiles.pop((0,1),None)
                    elif fault == 'protected':
                        current.protected.add((0,1))
                    self.observe(current, ack+83_432_292, ack+100_480_708, ack+117_839_333,
                        bad_prefix=fault=='prefix',bad_phase=fault=='phase')
                    self.h.now = ack+121_304_292
                    self.last, self.source, self.parent = command, current, parent
        self.assertEqual(parent, self.t.q.cycle().continuation_deadline_ns)
        return source

    def observe(self, source, start, end, commit, bad_prefix=False, bad_phase=False):
        self.h.now = commit
        scene = self.h.scene(2, 2, source, beat=True)
        scene.beat_remaining = ((5*native.SECOND-(start+end)//2) % native.PERIOD)/native.PERIOD
        if bad_phase:
            scene.beat_remaining=(scene.beat_remaining+.49)%1
        return self.h.observe_actual(scene,start=start,end=end,
            prefix=self.h.prefix+1 if bad_prefix else self.h.prefix)

    def assess(self, source, worker, release, candidate=False):
        state = self.t.q.cycle()
        self.h.now = worker
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine,state.job_id,state.capture_id,state.prefix,worker))
        value = Result(abi=1,size=C.sizeof(Result),status=0,outcome=2 if candidate else 0,
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

    def test_last_full_D3_uses_only_the_unissued_next_beat_before_original_parent(self):
        for direction in (1,2):
            with self.subTest(direction=direction):
                self.context(direction)
                before=(self.h.status().inputs,self.h.status().moves)
                now=self.h.now
                ready,command=self.h.tick()
                self.assertEqual(1,ready,'last observed safe D3 needs the still-future unissued beat')
                self.assertEqual((4,4),(command.kind,command.direction))
                self.assertGreater(command.not_before_ns,now)
                self.assertLess(command.not_before_ns-now,50_000_000)
                self.assertEqual(10_000_000,command.deadline_ns-command.not_before_ns)
                self.assertLessEqual(command.target_ns+80_000_000,self.parent)
                self.assertGreater(command.target_ns+native.PERIOD+80_000_000,self.parent)
                self.assertLessEqual(abs(command.target_ns-(self.last.target_ns+native.PERIOD)),
                    native.PERIOD*.08)
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)

    def test_default_preparation_and_current_last_slot_vetoes_remain_closed(self):
        for fault in ('ordinary','feature_off','candidate','floor','protected','prefix','phase','past_NB','expired'):
            with self.subTest(fault=fault):
                self.context(enabled=fault!='feature_off',fault=fault)
                before=(self.h.status().inputs,self.h.status().moves)
                if fault=='past_NB':
                    self.h.now=self.last.target_ns+native.PERIOD-self.h.status().lead_ns+1
                elif fault=='expired':
                    self.h.now=self.parent+1
                elif fault=='ordinary':
                    self.t.frame(self.source)  # ordinary20ms cadence enters its100ms publication window
                ready,command=self.h.tick()
                if fault=='ordinary':
                    self.assertEqual((1,4),(ready,command.kind))
                    self.assertGreaterEqual(command.not_before_ns-self.h.now,50_000_000)
                else:
                    self.assertFalse(ready and command.kind==4)
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)

    def test_published_not_sent_or_unknown_D3_cannot_create_another_input(self):
        for outcome in ('published','not_sent','unknown','moved'):
            with self.subTest(outcome=outcome):
                self.context()
                ready,command=self.h.tick()
                self.assertEqual(1,ready)
                before=(self.h.status().inputs,self.h.status().moves)
                if outcome=='not_sent':
                    self.h.now=command.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.h.engine,
                        command.id,self.h.now,0))
                elif outcome in ('unknown','moved'):
                    self.h.now=command.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.h.engine,
                        command.id,self.h.now,1,0,1))
                    self.h.now+=self.t.SYNTH
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.h.engine,
                        command.id,self.h.now,-1 if outcome=='unknown' else 1))
                    if outcome=='moved':
                        self.h.prefix=command.id
                        ack=self.h.now
                        latest=native.translated(self.source,4)
                        latest.protected=self.t.cross({p for p,k in latest.tiles.items() if k=='item'})
                        self.observe(latest,ack+14_255_417,ack+47_304_750,ack+63_880_292)
                        event=self.h.events()[-1]
                        self.assertEqual((1,0,1),(event.motion,event.dx,event.dy))
                        self.assertEqual((before[0]+1,before[1]+1),
                            (self.h.status().inputs,self.h.status().moves))
                again,new=self.h.tick()
                self.assertFalse(again and new.kind==4)
                if outcome in ('published','not_sent'):
                    self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(self.parent,self.t.q.cycle().continuation_deadline_ns)


if __name__=='__main__':
    unittest.main()
