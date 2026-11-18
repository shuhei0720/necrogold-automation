"""TEST117: an owned stationary wait withdraws stale permission before W.

Preparation uses the existing public-API two-real-MOVE procedural fixture.
The cut reuses recorded3b capture/commit latency offsets, not its private state,
PNG or unrecorded future replies. Texture and physical HUD remain procedural.
"""
import ctypes as C
from copy import deepcopy
from unittest.mock import patch
import unittest
import os
from pathlib import Path

from tests import test_native_controller as native
from tests import test_native_plural_wait103 as plural
from tests import test_native_stationary_wait076 as stationary
from tests import test_native_passage072 as passage
from tests import test_native_clear_stationary095 as clear095

CORE=Path(os.environ.get("NECRO117_STATIONARY_CORE",native.CORE))


class NativeClearProof117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous=clear095.CORE
        try:
            clear095.CORE=CORE
            plural.NativePluralWait103Tests.setUpClass.__func__(cls)
        finally:clear095.CORE=previous
    tearDownClass = classmethod(plural.NativePluralWait103Tests.tearDownClass.__func__)

    def start_clear_cut(self):
        room = passage.passage_room(mouth=(-2, -3))
        room.tiles[(-5, -2)] = room.tiles[(2, 2)] = 'stone'
        with patch.object(passage, 'passage_room', return_value=room):
            terrain, second = self.armed('passage')
        self.ack(second)
        terrain = native.translated(terrain, second.direction)
        self.now = max(self.now, second.target_ns + 80_000_002)
        self.assertEqual(1, self.observe(terrain))
        self.assertEqual((2, 2, 1), (self.status().inputs, self.status().moves,
                                    self.status().lead_confirmed))
        self.verified_ns = self.now
        before, after = deepcopy(terrain), deepcopy(terrain)
        before.signature, after.signature = plural.room_phase_pair(self.frame(terrain))
        self.now += 10_000_000
        self.assertEqual(1, self.observe(before))
        old = passage.NativePassage072Tests.next_move(self, before)
        self.assertEqual((0, 0, 0), self.motion(before, after, old.direction))
        self.assertEqual(1, self.frame(before).gold_state, 'this is CLEAR, not the115 candidate fixture')
        self.saved_credit = self.credit()
        self.parent_deadline = min(old.source_start_ns + 3*native.SECOND,
            old.phase_sample_ns + 3*native.SECOND, self.verified_ns+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,
            self.status().started_ns+180*native.SECOND)
        self.original_period = self.status().beat_period_ns
        # Original3b trigger actualcommit was9.277249ms before notBefore.
        self.now = old.not_before_ns-9_277_249
        self.trigger_commit = self.now
        self.wait_deadline = min(self.parent_deadline, self.now+2*self.original_period)
        # Original218 source interval versus its actualcommit.
        self.cut_observe(after, start=-34_251_750, end=-23_506_833, commit=0)
        self.trigger_id = self.number
        self.assertEqual((0, 0, 0, 0), (self.status().reason, self.status().input_state,
            self.status().current_command_id, self.status().next_target_ns))
        event = self.events()[-1]
        self.assertEqual((old.id, 3, 0), (event.command.id, event.outcome, event.begin_ns))
        return before, after, old

    def cut_observe(self, terrain, *, start, end, commit, beat=True):
        self.now = self.trigger_commit+commit
        frame = self.frame(terrain)
        # Independent fixed physical520ms world: use the capture midpoint,
        # never the future selected ticket/fit or model to move this phase.
        midpoint = self.trigger_commit+(start+end)//2
        frame.beat_remaining = ((5*native.SECOND-midpoint) % native.PERIOD)/native.PERIOD
        frame.beat_valid = int(beat)
        self.number += 1
        return self.lib.ng2_controller_observe_at(self.engine, C.byref(frame), self.number,
            self.trigger_commit+start, self.trigger_commit+end,
            self.prefix, 1, self.now)

    def test_clear_ready_loses_current_proof_within_original_W_without_SCREEN(self):
        before, after, old = self.start_clear_cut()
        a, b = self.frame(before), self.frame(after)
        self.assertEqual(1, self.lib.ng2_clear_plural_stationary_zero(
            C.byref(a), C.byref(b), old.direction))
        # Original219 interval; metadataanalysis_end is the explicit testcommit.
        self.assertEqual(1, self.cut_observe(after, start=10_700_083,
            end=22_107_292, commit=45_736_417))
        self.assertEqual(0, self.status().reason)
        # Original220/221 independent strict-zero slots. No tick/publication is
        # requested between these captures; neither earns displacement credit.
        self.assertEqual((2, 0, 0), self.motion(before, before, old.direction))
        self.cut_observe(before, start=55_814_292, end=66_476_083, commit=90_950_250)
        self.cut_observe(before, start=97_351_000, end=108_534_125, commit=132_202_125)
        uncertain = stationary.NativeStationaryWait076Tests.uncertain(self, after)
        self.assertEqual((0, 0, 0), self.motion(before, uncertain, old.direction))
        c = self.frame(uncertain)
        self.assertEqual(0, self.lib.ng2_clear_plural_stationary_zero(
            C.byref(a), C.byref(c), old.direction))
        self.assertEqual(1, self.cut_observe(uncertain, start=138_665_250,
            end=149_785_167, commit=175_623_458))
        self.assertLess(self.now, self.wait_deadline)
        self.assertEqual((0, 0, 0, 0), (self.status().reason,
            self.status().input_state, self.status().current_command_id,
            self.status().next_target_ns),
            'CLEAR READY must withdraw stale proof and observe inside originalW, not terminateSCREEN')
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual(self.parent_deadline, self.recovery().records[0].sync_deadline_ns)
        self.assertEqual(0, next(e for e in self.events() if e.command.id == old.id).begin_ns)
        self.reject_old_callbacks_without_mutation(old)
        self.assertEqual(0, self.tick()[0], 'no input can use the lost proof')

    def start_gold_cut(self):
        # Sparse physical room: a top/left wall guides LEFT twice, then DOWN
        # toward the single lower-left GOLD. No phone Scene dump or STONE.
        tiles={(x,y):'floor' for x in range(-2,5) for y in range(-2,3)}
        for x in range(-3,6):tiles[(x,-3)]='dirt'
        for y in range(-2,1):tiles[(-3,y)]='dirt'
        for x in range(1,5):tiles[(x,3)]='dirt'
        tiles.update({(-5,2):'gold',(-5,1):'dirt',(-4,2):'dirt',(-3,2):'dirt'})
        terrain=native.textured(tiles)
        self.fit(terrain)
        for _ in range(2):
            command=self.next_move(terrain)
            self.assertEqual(1,command.direction)
            self.ack(command)
            terrain=native.translated(terrain,command.direction)
            self.now=max(self.now,command.target_ns+80_000_002)
            self.assertEqual(1,self.observe(terrain))
        self.assertEqual((2,2,1),(self.status().inputs,self.status().moves,self.status().lead_confirmed))
        self.verified_ns=self.now
        self.assertEqual({(-3,2)},terrain.gold)
        before,after=deepcopy(terrain),deepcopy(terrain)
        before.signature,after.signature=plural.room_phase_pair(self.frame(terrain))
        after.tiles[(5,-3)]='stone'  # Remote oldDIRT palette change triggers this actualGOLD wait.
        self.now+=10_000_000
        self.observe(before)
        old=self.next_move(before)
        self.assertEqual(4,old.direction)
        self.assertEqual((0,0,0),self.motion(before,after,old.direction))
        self.assertEqual(0,list(self.frame(before).tiles).count(3))
        self.saved_credit=self.credit()
        self.parent_deadline=min(old.source_start_ns+3*native.SECOND,
            old.phase_sample_ns+3*native.SECOND,self.verified_ns+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,self.status().started_ns+180*native.SECOND)
        self.original_period=self.status().beat_period_ns
        # Original098 trigger actualcommit was4.535846ms after notBefore,
        # still inside the original10ms begin window. No timing bound changes.
        self.now=old.not_before_ns+4_535_846
        self.trigger_commit=self.now
        self.wait_deadline=min(self.parent_deadline,self.now+2*self.original_period)
        self.cut_observe(after,start=-36_713_667,end=-24_824_250,commit=0)
        self.trigger_id=self.number
        self.assertEqual((0,0,0),(self.status().reason,self.status().input_state,self.status().current_command_id))
        self.assertEqual((old.id,3,0),(self.events()[-1].command.id,self.events()[-1].outcome,self.events()[-1].begin_ns))
        return before,after,old

    def test_single_actual_GOLD_without_old_STONE_uses_zero_only_inside_owned_wait(self):
        # This later world is independent of the missing098 future captures.
        # The real-image numeric88/90 versus70/91/92 cases are private calibration.
        _,after,old,_=self.lose_ready(gold=True)
        new=self.reacquire_fixed_cadence(after)
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(0,next(e for e in self.events() if e.command.id==old.id).begin_ns)
        self.assertGreater(new.id,old.id)
        self.assertEqual(old.direction,new.direction)
        self.assertEqual((2,2),(self.status().inputs,self.status().moves))
        self.assertLess(new.deadline_ns,self.parent_deadline)
        self.reject_old_callbacks_without_mutation(old)

    def lose_ready(self, gold=False):
        before, after, old = self.start_gold_cut() if gold else self.start_clear_cut()
        self.cut_observe(after, start=10_700_083, end=22_107_292, commit=45_736_417)
        self.cut_observe(before, start=55_814_292, end=66_476_083, commit=90_950_250)
        self.cut_observe(before, start=97_351_000, end=108_534_125, commit=132_202_125)
        uncertain = stationary.NativeStationaryWait076Tests.uncertain(self, after)
        self.cut_observe(uncertain, start=138_665_250, end=149_785_167, commit=175_623_458)
        self.assertEqual((0, 0, 0), (self.status().reason, self.status().input_state,
                                    self.status().current_command_id))
        return before, after, old, uncertain

    def reacquire_fixed_cadence(self, after):
        # Fixed50ms acquisitions and fixed physical520ms HUD. No selected
        # target/model determines capture phase or moves the fixture clock.
        for offset in range(225_623_458, 1_975_623_459, 50_000_000):
            self.cut_observe(after, start=offset-18_000_000,
                end=offset-6_000_000, commit=offset)
            self.assertEqual(0, self.status().reason)
            ready, command = self.tick()
            if ready:
                self.assertEqual(4, command.kind)
                self.assertGreater(command.id, self.events()[1].command.id)
                self.assertLessEqual(command.deadline_ns+self.status().lead_ns+50_000_000,
                                     self.parent_deadline)
                return command
        self.fail('fixed current proof/HUD cadence must qualify a bounded replacement')

    def test_withdrawn_CLEAR_permission_keeps_original_W_equalities(self):
        for extra in (0, 1):
            with self.subTest(extra=extra):
                self.fresh_engine()
                _, after, old, uncertain = self.lose_ready()
                offset=self.wait_deadline-self.trigger_commit
                self.cut_observe(uncertain, start=offset-18_000_000,
                    end=offset-6_000_000, commit=offset+extra)
                self.assertEqual((8, 2, 2), (self.status().reason,
                    self.status().inputs, self.status().moves))
                self.assertEqual(self.saved_credit,self.credit())
                self.assertEqual(self.parent_deadline,self.recovery().records[0].sync_deadline_ns)
                self.assertEqual(0,next(e for e in self.events() if e.command.id==old.id).begin_ns)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))

    def test_independent_reproof_current_HUD_then_recorded_ACK_duration_and_real_Motion(self):
        _, after, old, _ = self.lose_ready()
        new = self.reacquire_fixed_cadence(after)
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,new.not_before_ns,1,0,1))
        # Scheduling begin at its declared timer is the product operation, not
        # resampling the world at a fitted phase. Original15 ACK lasted271.86ms.
        begin=new.not_before_ns
        self.now=begin
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.now+=271_861_834
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,new.id,self.now,1))
        self.prefix=new.id
        self.assertEqual((3,2),(self.status().inputs,self.status().moves),'ACK is not movement')
        moved=native.translated(after,new.direction)
        self.assertEqual((1,*native.DIRS[new.direction]),self.motion(after,moved,new.direction))
        self.cut_observe(moved,start=begin+340_724_584-self.trigger_commit,
            end=begin+353_951_000-self.trigger_commit,
            commit=begin+376_731_959-self.trigger_commit)
        self.assertEqual((0,3,3),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual(1,len([e for e in self.events() if e.command.id==new.id and e.begin_ns]))
        self.reject_old_callbacks_without_mutation(old)

    def test_issued_replacement_original_P_and_unknown_synth_remain_hard_stops(self):
        for fault in ('parent0','parent1','unknown'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _,after,old,_=self.lose_ready()
                new=self.reacquire_fixed_cadence(after)
                if fault=='unknown':
                    self.now=new.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                    self.now+=271_861_834
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,new.id,self.now,-1))
                    self.prefix=new.id
                    self.assertEqual(4,self.status().input_state)
                    self.now+=50_000_000
                    self.observe(after)
                    ready,command=self.tick()
                    self.assertFalse(ready and command.kind==4)
                    self.assertEqual((3,2),(self.status().inputs,self.status().moves))
                else:
                    self.now=self.parent_deadline+int(fault[-1])
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                    self.assertEqual((8,2,2),(self.status().reason,self.status().inputs,self.status().moves))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))

    def test_real_nonzero_Motion_cannot_become_permission_withdrawal(self):
        before,after,old=self.start_clear_cut()
        self.cut_observe(after,start=10_700_083,end=22_107_292,commit=45_736_417)
        moved=native.translated(before,old.direction)
        self.assertEqual((1,*native.DIRS[old.direction]),self.motion(before,moved,old.direction))
        self.cut_observe(moved,start=138_665_250,end=149_785_167,commit=175_623_458)
        self.assertEqual((17,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual(0,next(e for e in self.events() if e.command.id==old.id).begin_ns)

    def test_issued_but_unbegun_proof_loss_retires_new_id_once_with_original_W(self):
        for late in (False, True):
            with self.subTest(late=late):
                self.fresh_engine()
                _,after,old,uncertain=self.lose_ready()
                new=self.reacquire_fixed_cadence(after)
                self.assertEqual((1,new.id),(self.status().input_state,self.status().current_command_id))
                instant=self.wait_deadline+1 if late else new.not_before_ns-1_000_000
                if not late:self.assertLess(instant,self.wait_deadline)
                offset=instant-self.trigger_commit
                self.cut_observe(uncertain,start=offset-18_000_000,end=offset-6_000_000,commit=offset)
                self.assertEqual((8 if late else 0,0,0),(self.status().reason,
                    self.status().input_state,self.status().current_command_id))
                event=next(e for e in self.events() if e.command.id==new.id)
                self.assertEqual((3,0),(event.outcome,event.begin_ns))
                self.assertEqual(0,self.preparation_epoch(new))
                self.assertEqual(self.saved_credit,self.credit())
                self.assertEqual(self.parent_deadline,self.recovery().records[0].sync_deadline_ns)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,instant,1,0,1))
                self.reject_old_callbacks_without_mutation(old)
                self.reject_old_callbacks_without_mutation(new)

    def test_reproof_without_current_HUD_cannot_reuse_the_retained_model_authority(self):
        _,after,old,_=self.lose_ready()
        period=self.status().beat_period_ns
        self.assertGreater(period,0)
        events=len(self.events())
        offset=225_623_458
        self.cut_observe(after,start=offset-18_000_000,end=offset-6_000_000,commit=offset,beat=False)
        self.assertEqual(period,self.status().beat_period_ns,'withdrawal retains the model, not input authority')
        self.assertEqual(0,self.status().reason)
        self.assertEqual(0,self.tick()[0],'model capture predating new proof cannot publish')
        self.assertEqual(events,len(self.events()))
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))


for _name in ('setUp','scene','frame','observe','observe_actual','tick','status','events',
    'ack','fit','next_move','publish_procedural_candidate','fresh_engine','recovery',
    'recovery_samples','all_public_bytes','reject_old_callbacks_without_mutation',
    'motion_wait','credit','choice','observed_vantage','observed_result','preparation_epoch',
    'armed','motion','assert_waiting','next_operation'):
    setattr(NativeClearProof117Tests,_name,getattr(plural.NativePluralWait103Tests,_name))

if __name__ == '__main__':unittest.main()
