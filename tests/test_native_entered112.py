"""Delayed original-ACK movement proof before one bounded FULL observation.

Scenes and clocks are procedural. TEST111 supplied an early FULL whose direct
comparison stayed UNKNOWN, followed by a later FULL that independently proved
MOVED from the original ACK source. Unseen endcaps remain UNKNOWN.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_full_framing101 as full
from tests import test_native_observation072 as observation


class NativeEntered112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous=native.CORE
        try:
            native.CORE=Path(os.environ.get('NECRO_TEST112_ENTERED_CORE',str(previous)))
            full.NativeFullFraming101Tests.setUpClass()
        finally:
            native.CORE=previous
        cls.lib=full.NativeFullFraming101Tests.lib
        cls.lib.ng2_motion.argtypes=[C.POINTER(native.Scene),C.POINTER(native.Scene),C.c_int32,
                                    C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        full.NativeFullFraming101Tests.tearDownClass()

    def setUp(self):
        self.f=full.NativeFullFraming101Tests('runTest');self.f.lib=self.lib;self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def pending(self, mutate_result=None, input_unknown=False):
        h,_,_,_=self.f.p.armed(reserve=False)
        self.h=self.f.h=self.f.q.h=h;self.q=self.f.q
        late=full.NativeFullFraming101Tests.full_source()
        late.tiles[(-1,-2)]='floor'
        late.tiles[(1,0)]='floor'  # The old ACK origin projected after LEFT.
        before=native.translated(late,2)
        for point in list(before.tiles):
            if before.tiles[point]=='item':del before.tiles[point]
        before.tiles[(0,0)]='floor'
        before=native.textured(before.tiles);before.goods='unknown'
        h.now+=10_000_000
        self.assertEqual(1,h.observe_actual(h.scene(2,2,before,beat=True)))
        old=h.next_move(before)
        self.assertEqual(1,old.direction)
        late.signature=native.translated(before,1).signature
        early=deepcopy(late);early.tiles.pop((-1,-2));early.signature=bytes([80])*23296
        self.assertEqual((0,0,0),h.motion(before,early,1))
        self.assertEqual((1,-1,0),h.motion(before,late,1))
        self.assertEqual((0,0,0),h.motion(early,late,1),
                         'the old FULL source must remain UNKNOWN, not a transitive zero')
        if input_unknown:
            h.now=max(h.now,old.not_before_ns)
            self.assertEqual(1,self.lib.ng2_controller_begin(h.engine,old.id,h.now,1,0,1))
            h.now+=50_000_000
            self.assertEqual(1,self.lib.ng2_controller_complete(h.engine,old.id,h.now,-1))
            self.before,self.early,self.late,self.old=before,early,late,old
            self.moves,self.inputs=h.status().moves,h.status().inputs
            self.original=self.q.cycle()
            return self.original
        h.ack(old);h.now=max(h.now+2,old.target_ns+100_000_000)
        self.assertEqual(1,h.observe_actual(h.scene(2,2,early,beat=True)))
        self.assertEqual((0,0),(h.status().input_state,h.events()[-1].motion),
                         'the existing initial FULL/UNKNOWN closure is preserved')
        self.before,self.early,self.late,self.old=before,early,late,old
        self.moves,self.inputs=h.status().moves,h.status().inputs
        self.original_visual=h.motion_wait().deadline_ns
        if mutate_result is not False:
            def unknown(value):
                full.NativeFullFraming101Tests.result(value)
                if mutate_result:mutate_result(value)
            self.q.assess(0,1,unknown)
        self.original=self.q.cycle()
        return self.original

    def observe(self, scene=None, advance=70_000_000, **kwargs):
        self.h.now+=advance
        return self.h.observe_actual(self.h.scene(2,2,self.late if scene is None else scene,beat=True),**kwargs)

    def refresh(self):
        old=self.pending();self.assertEqual(3,old.state)
        self.assertEqual(1,self.observe())
        new=self.q.cycle()
        self.assertEqual((old.job_id+1,self.h.number,1,1),(new.job_id,new.capture_id,new.pending,new.state),
                         'a later original-ACK MOVED proof must admit fresh FULL data, not stop on the revealed halo floor')
        self.assertEqual((self.moves+1,self.inputs,0),(self.h.status().moves,self.h.status().inputs,self.h.status().input_state))
        event=next(e for e in self.h.events() if e.command.id==self.old.id)
        self.assertEqual((2,1,-1,0,self.h.number),(event.outcome,event.motion,event.dx,event.dy,event.observed_capture_id))
        ref=next(r for r in native.NativeControllerTests.motion_references(self.h) if r.command_id==self.old.id)
        self.assertEqual((self.old.source_capture_id,self.h.number,1,1),
                         (ref.authority_capture_id,ref.observed_capture_id,ref.primary_motion,ref.selected_motion))
        self.assertEqual(old.hold_started_ns,new.hold_started_ns)
        self.assertLessEqual(new.continuation_deadline_ns,old.continuation_deadline_ns)
        self.assertLessEqual(new.deadline_ns,new.capture_start_ns+150_000_000)
        self.assertEqual(0,self.h.tick()[0],'the trigger supplies data only, never an input ticket')
        self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,self.old.id,self.h.now,1,0,1))
        return old,new

    def test_late_original_moved_updates_once_and_binds_only_fresh_full_data(self):
        old,new=self.refresh()
        counts=(self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id)
        self.observe(advance=10_000_000)
        self.assertEqual(counts,(self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id))
        self.assertEqual(new.capture_id,self.q.cycle().capture_id)

    def test_refreshed_unknown_requires_independent_zero_then_only_one_future_observation(self):
        old,new=self.refresh()
        self.q.assess(0,1,full.NativeFullFraming101Tests.result)
        self.assertEqual((3,0,0),(self.q.cycle().state,self.q.cycle().pending,self.q.cycle().completed_shops))
        self.assertEqual(0,self.h.tick()[0])
        self.observe(advance=10_000_000)
        command=self.h.next_move(self.late)
        self.assertEqual((4,1),(command.kind,command.direction))
        self.assertGreater(command.id,self.old.id);self.assertGreater(command.ordinal,self.old.ordinal)
        self.assertGreater(command.source_capture_id,new.capture_id)
        self.assertLessEqual(self.h.motion_wait().deadline_ns,old.continuation_deadline_ns)
        self.h.ack(command)
        self.assertEqual(self.moves+1,self.h.status().moves,'ACK of the new input adds no movement credit')
        self.h.observed_result(command,native.translated(self.late,1))
        self.assertEqual(self.moves+2,self.h.status().moves)
        self.q.assess(0,1,full.NativeFullFraming101Tests.result)
        self.assertEqual((7,1),(self.q.cycle().state,self.q.cycle().completed_shops),
                         'a second UNKNOWN must not replenish the consumed one-use framing allowance')
        self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_original_unknown_blocked_tween_and_expired_visual_proof_cannot_refresh(self):
        for fault in ('unknown','blocked','tween','visual_expired','parent_expired'):
            with self.subTest(fault=fault):
                self.setUp();old=self.pending();latest=deepcopy(self.late)
                if fault=='unknown':latest.signature=bytes([80])*23296
                elif fault=='blocked':latest.signature=self.before.signature
                elif fault=='tween':
                    latest.signature=native.translated(self.before,1,amount=4).signature
                    self.assertEqual((7,0,0),self.h.motion(self.before,latest,1))
                elif fault=='visual_expired':self.h.now=self.original_visual+1
                else:self.h.now=old.continuation_deadline_ns+1
                self.observe(latest,advance=0 if 'expired' in fault else 70_000_000)
                self.assertEqual((self.moves,self.inputs,old.job_id),
                                 (self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id))
                self.assertFalse(self.q.cycle().pending)
                self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_changed_items_projection_gold_or_local_floor_never_gain_refresh(self):
        faults={
            'item':lambda s:s.tiles.__setitem__((-3,-2),'floor'),
            'new_item':lambda s:s.tiles.__setitem__((4,3),'item'),
            'missing_protection':lambda s:s.protected.discard((-1,-2)),
            'extra_protection':lambda s:s.protected.add((8,3)),
            'gold':lambda s:s.tiles.__setitem__((-6,-3),'floor'),
            'origin':lambda s:s.tiles.__setitem__((0,0),'dirt'),
            'next':lambda s:s.tiles.__setitem__((-1,0),'dirt'),
            'protected_nonfloor':lambda s:s.tiles.__setitem__((-1,-2),'dirt'),
            'near_change':lambda s:s.tiles.__setitem__((-2,0),'dirt'),
            'old_origin_near':lambda s:s.tiles.__setitem__((2,0),'dirt'),
        }
        for fault,mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp();old=self.pending();latest=deepcopy(self.late);mutate(latest)
                self.observe(latest)
                self.assertEqual((self.moves,self.inputs,old.job_id),
                                 (self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id))
                self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_candidate_target_and_strong_word_keep_priority_over_late_moved(self):
        changes={
            'candidate':lambda v:setattr(v,'outcome',1),
            'target':lambda v:setattr(v,'outcome',2),
            'upper':lambda v:setattr(v.rows[0].slots[1],'icon_upper_bound',.8),
            'word':lambda v:(setattr(v.partial[0],'word_present',1),setattr(v.partial[0],'word_iou',1),setattr(v.partial[0],'word_coverage',1)),
        }
        for fault,mutate in changes.items():
            with self.subTest(fault=fault):
                self.setUp();old=self.pending(mutate);self.observe()
                self.assertEqual((self.moves,self.inputs,old.job_id),
                                 (self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id))
                self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_worker_prefix_unstable_and_cancel_cannot_reanchor(self):
        for fault in ('worker','prefix','unstable','cancel'):
            with self.subTest(fault=fault):
                self.setUp();old=self.pending(False if fault=='worker' else None)
                kwargs={}
                if fault=='worker':
                    self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,old.job_id,old.capture_id,old.prefix,self.h.now))
                elif fault=='prefix':kwargs['prefix']=self.h.prefix+1
                elif fault=='unstable':kwargs['stable']=0
                elif fault=='cancel':self.lib.ng2_controller_cancel(self.h.engine,self.h.now,1)
                self.observe(**kwargs)
                self.assertEqual((self.moves,self.inputs,old.job_id),
                                 (self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id))
                self.assertNotEqual(4,self.h.tick()[1].kind)

    def test_unknown_input_cannot_use_late_moved_as_a_known_ack(self):
        old=self.pending(input_unknown=True)
        self.assertEqual(4,self.h.status().input_state)
        self.observe()
        self.assertEqual((self.moves,self.inputs,old.job_id,4),
                         (self.h.status().moves,self.h.status().inputs,self.q.cycle().job_id,self.h.status().input_state))
        self.assertNotEqual(4,self.h.tick()[1].kind)


if __name__=='__main__':unittest.main()
