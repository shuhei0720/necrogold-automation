"""TEST098: a stationary side opening replaces only an unsent floor route.

Public C operations use explicit procedural terrain, texture and clocks. The
later photographs are synthetic proofs, not omitted TEST097 game responses.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_observation072 as observation

CORE = fixture.CORE
SECOND = fixture.SECOND


class NativeSideOpening098Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='test098-side-source-')
        directory = Path(cls.source_directory.name)
        for path in CORE.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory/path.name)
        baseline = os.environ.get('NECRO_TEST098_SIDE_BASELINE_CONTROLLER')
        if baseline:
            shutil.copyfile(baseline, directory/'NG2Controller.c')
        identity = os.environ.get('NECRO_TEST098_SIDE_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({'controller_override': baseline,
                'sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(directory.glob('NG2*')) if path.suffix in ('.c', '.h')},
                'tests': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                sort_keys=True, indent=2)+'\n')
        previous = mechanics.CORE
        try:
            mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]
        cls.lib.ng2_controller_preparation_epoch.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64]
        cls.lib.ng2_controller_preparation_epoch.restype = C.c_uint64

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

    setUp = fixture.NativeControllerTests.setUp
    scene = fixture.NativeControllerTests.scene
    observe = fixture.NativeControllerTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = fixture.NativeControllerTests.tick
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    motion_wait = fixture.NativeControllerTests.motion_wait
    ack = fixture.NativeControllerTests.ack
    fit = fixture.NativeControllerTests.fit
    next_move = fixture.NativeControllerTests.next_move
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    observed_result = observation.NativeObservation072Tests.observed_result
    credit = observation.NativeObservation072Tests.credit
    choice = observation.NativeObservation072Tests.choice
    motion = observation.NativeObservation072Tests.motion
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch

    def armed(self, turns=0, side=-1):
        def rotate(x, y):
            x *= -side
            for _ in range(turns): x, y = -y, x
            return x, y
        self.rotate = rotate
        cells = {(0,0): 'floor', (0,1): 'floor', (0,2): 'floor', (-1,-1): 'floor',
            (-2,-2): 'gold', (-1,0): 'dirt', (-2,-1): 'dirt', (0,-1): 'dirt',
            (1,-1): 'dirt', (1,0): 'dirt', (-2,0): 'dirt', (-2,1): 'dirt',
            (-1,1): 'dirt', (1,1): 'dirt', (-1,2): 'stone'}
        source = fixture.textured({rotate(*p): kind for p, kind in cells.items()})
        direction = {value: key for key, value in fixture.DIRS.items()}[rotate(0,1)]
        initial = fixture.translated(source, direction)
        self.fit(initial); first = self.next_move(initial); self.ack(first)
        source = fixture.translated(initial, first.direction)
        self.observed_result(first, source)
        old = self.next_move(source)
        self.assertEqual((direction, 8, 1), (old.direction, self.choice(source)[1], self.choice(source)[4]))
        latest = deepcopy(source); latest.tiles[rotate(-1,0)] = 'floor'
        self.new_direction = {value: key for key, value in fixture.DIRS.items()}[rotate(-1,0)]
        self.assertEqual((self.new_direction, 8, 1),
            (self.choice(latest)[0], self.choice(latest)[1], self.choice(latest)[4]))
        self.assertEqual((2,0,0), self.motion(source, latest, direction))
        self.assertEqual((1,1,1), (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        return source, latest, old

    def trigger(self, turns=0, side=-1):
        source, latest, old = self.armed(turns, side)
        self.saved_credit = self.credit()
        self.now = old.deadline_ns-30_000_000
        self.observe_actual(self.scene(2,2,latest,beat=True))
        self.trigger_id, self.trigger_end = self.number, self.now
        self.assertEqual((0,0,4,0,0), (self.status().reason, self.status().terminal,
            self.status().phase, self.status().input_state, self.status().current_command_id),
            'an independent stationary side opening must retire the unsent old route and reacquire')
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual((3,17,0,0), (self.events()[-1].outcome, self.events()[-1].reason,
            self.events()[-1].begin_ns, self.events()[-1].motion))
        self.assertEqual(bytes(old), bytes(self.events()[-1].command))
        self.assertEqual(0, self.preparation_epoch(old))
        self.assertEqual(0, self.tick()[0], 'the trigger cannot authorize its own replacement')
        self.reject_old_callbacks_without_mutation(old)
        return source, latest, old, bytes(self.events()[-1])

    def prove_and_issue(self, latest):
        self.now += 20_000_000
        self.observe_actual(self.scene(2,2,latest,beat=True))
        self.assertEqual((0,self.saved_credit), (self.status().reason,self.credit()))
        new = self.next_move(latest)
        self.assertEqual((self.new_direction,4), (new.direction,new.kind))
        self.assertGreaterEqual(new.not_before_ns-self.now,50_000_000)
        return new

    def test_eight_side_turns_retire_old_ticket_and_prepare_new_direction_without_credit(self):
        for turns in range(4):
            for side in (-1,1):
                with self.subTest(turns=turns,side=side):
                    self.fresh_engine(); _, latest, old, retired = self.trigger(turns,side)
                    new = self.prove_and_issue(latest)
                    self.assertGreater(new.id,old.id); self.assertGreater(new.target_ns,old.target_ns)
                    self.assertEqual(old.ordinal,new.ordinal)
                    self.assertEqual((1,1), (self.status().inputs,self.status().moves))
                    self.assertEqual(retired,bytes(self.events()[-2]))
                    self.assertNotEqual(0,self.preparation_epoch(new))
                    self.reject_old_callbacks_without_mutation(old)
                    self.ack(new)
                    self.assertEqual((2,1), (self.status().inputs,self.status().moves), 'ACK is not displacement')

    def test_trigger_rejects_extra_material_changes_gold_protection_goods_and_unsafe_floor(self):
        for fault in ('extra_floor','extra_dirt','stone','door','item','lost_gold','new_gold','parallel_opening',
                      'protected_opening','protected_far','origin','old_next','new_next','partial'):
            with self.subTest(fault=fault):
                self.fresh_engine(); source, latest, old = self.armed()
                if fault == 'extra_floor': latest.tiles[(8,3)]='floor'
                elif fault == 'extra_dirt': latest.tiles[(8,3)]='dirt'
                elif fault in ('stone','door','item'): latest.tiles[(8,3)]=fault
                elif fault == 'lost_gold': latest.tiles[(-2,-2)]='dirt'
                elif fault == 'new_gold': latest.tiles[(8,3)]='gold'
                elif fault == 'parallel_opening':
                    latest=deepcopy(source); latest.tiles[(0,-1)]='floor'
                elif fault == 'protected_opening': latest.protected.add((-1,0))
                elif fault == 'protected_far': latest.protected.add((8,3))
                elif fault == 'origin': latest.tiles[(0,0)]='dirt'
                elif fault == 'old_next': latest.tiles[(0,1)]='dirt'
                elif fault == 'new_next': latest.tiles[(-1,0)]='stone'
                elif fault == 'partial': latest.goods='partial'
                credit = self.credit(); self.now=old.deadline_ns-30_000_000
                self.observe_actual(self.scene(2,2,latest,beat=True))
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                offered = self.tick()[1]
                if fault == 'new_next':
                    self.assertNotEqual(self.new_direction, offered.direction if offered.kind==4 else 0,
                        'an unchanged old floor route may retain its existing SAME authority')
                else: self.assertNotEqual(4,offered.kind)
                self.assertEqual(credit,self.credit())
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))

    def test_trigger_requires_strict_zero_and_cannot_reuse_started_or_unknown_input(self):
        for fault in ('unknown','moved','tween','started','sent_unknown'):
            with self.subTest(fault=fault):
                self.fresh_engine(); source, latest, old = self.armed()
                if fault == 'unknown': latest.signature=bytes([40])*23296
                elif fault in ('moved','tween'):
                    latest.signature=fixture.translated(source,old.direction,9 if fault=='moved' else 8).signature
                if fault in ('started','sent_unknown'):
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    if fault == 'sent_unknown':
                        self.now+=1
                        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,-1))
                    self.now=old.target_ns+80_000_002
                else: self.now=old.deadline_ns-30_000_000
                credit=self.credit()
                self.observe_actual(self.scene(2,2,latest,beat=True))
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(credit,self.credit())

    def test_later_proof_requires_independent_current_prefix_capture(self):
        for fault in ('prefix','unstable','id','overlap'):
            with self.subTest(fault=fault):
                self.fresh_engine(); _, latest, old, retired=self.trigger()
                self.now+=20_000_000
                frame=self.scene(2,2,latest,beat=True)
                if fault == 'id': self.observe(frame,number=self.trigger_id)
                else:
                    options={'prefix':self.prefix-1} if fault=='prefix' else \
                        {'stable':0} if fault=='unstable' else {'start':self.trigger_end-1}
                    self.observe_actual(frame,**options)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(self.saved_credit,self.credit())
                self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))
                self.reject_old_callbacks_without_mutation(old)

    def test_fixed_new_anchor_cannot_be_replaced_by_transitive_zero_frames(self):
        _, latest, old, retired=self.trigger()
        rng=random.Random(98198); noise=bytes(rng.randrange(20,100) for _ in latest.signature)
        middle, changed=deepcopy(latest),deepcopy(latest)
        middle.signature=bytes((80*a+20*b+50)//100 for a,b in zip(latest.signature,noise))
        changed.signature=bytes((60*a+40*b+50)//100 for a,b in zip(latest.signature,noise))
        self.assertEqual((2,0,0),self.motion(latest,middle,self.new_direction))
        self.assertEqual((2,0,0),self.motion(middle,changed,self.new_direction))
        self.assertEqual((0,0,0),self.motion(latest,changed,self.new_direction))
        self.now+=4; self.observe_actual(self.scene(2,2,middle,beat=True))
        self.assertEqual(0,self.status().reason)
        self.now+=4; self.observe_actual(self.scene(2,2,changed,beat=True))
        self.assertEqual(17,self.status().reason)
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_original_ticket_and_recovery_horizons_cannot_be_extended(self):
        for late in (0,1):
            with self.subTest(ticket_deadline_plus=late):
                self.fresh_engine(); _, latest, old=self.armed(); credit=self.credit()
                self.now=old.deadline_ns-1
                self.observe_actual(self.scene(2,2,latest,beat=True),commit=old.deadline_ns+late)
                self.assertEqual((17,0) if late else (0,1),
                    (self.status().reason,self.recovery().post_move_reacquisitions))
                self.assertEqual(credit,self.credit())
        self.fresh_engine(); _, latest, old, retired=self.trigger()
        deadline=min(self.verified_ns+12*SECOND,self.status().walk_started_ns+45*SECOND,
            self.status().started_ns+180*SECOND)
        row=self.recovery().records[min(1,self.recovery().record_count-1)]
        self.assertEqual(deadline,row.sync_deadline_ns)
        new=self.prove_and_issue(latest)
        self.assertLessEqual(self.motion_wait().deadline_ns,deadline)
        self.assertLessEqual(new.deadline_ns+self.status().lead_ns+50_000_000,deadline)
        self.now=deadline
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.assertEqual(self.saved_credit,self.credit())
        self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_goods_cancel_owner_phase_and_current_hud_revoke_new_permission(self):
        for issued in (False,True):
            for fault in ('goods','cancel','foreground','locked','owner','phase','hud'):
                with self.subTest(issued=issued,fault=fault):
                    self.fresh_engine(); _, latest, old, retired=self.trigger()
                    new=self.prove_and_issue(latest) if issued else None
                    if fault == 'goods':
                        latest.goods='visible'; self.now+=4
                        self.observe_actual(self.scene(2,2,latest,beat=True))
                    elif fault == 'cancel': self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    elif fault in ('phase','hud'):
                        self.now+=4; frame=self.scene(2,2,latest,beat=fault=='phase')
                        if fault=='phase': frame.beat_remaining=(frame.beat_remaining+.20)%1
                        self.observe_actual(frame); self.tick()
                    else:
                        flags={'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]]=int(fault=='locked')
                        self.tick(**flags)
                    if new:
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertNotEqual(4,self.tick()[1].kind)
                    self.assertEqual(self.saved_credit,self.credit())
                    self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_new_ack_unknown_remains_unresolved_without_resend(self):
        _, latest, old, retired=self.trigger()
        new=self.prove_and_issue(latest); self.ack(new)
        unknown=deepcopy(latest); unknown.signature=bytes([40])*23296
        period=self.status().beat_period_ns
        for attempt, offset in enumerate([n*(period//10) for n in range(7)]+[period]):
            self.now=new.target_ns+80_000_002+offset
            self.observe_actual(self.scene(2,2,unknown,beat=True))
            self.assertNotEqual(4,self.tick()[1].kind)
            self.assertEqual((2,1),(self.status().inputs,self.status().moves))
            self.assertEqual(attempt+1,self.motion_wait().attempts)
        self.assertEqual(10,self.status().reason)
        self.assertEqual(1,self.recovery().post_move_reacquisitions)
        self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))


if __name__ == '__main__': unittest.main()
