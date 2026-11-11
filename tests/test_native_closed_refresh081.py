"""TEST081: bounded observation refresh for an observed closed shop approach.

Public C calls and procedural images exercise source, proof and clock authority.
They do not reconstruct the omitted TEST080 device captures.
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

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativeClosedRefresh081Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            baseline = os.environ.get('NECRO_TEST081_BASELINE_CONTROLLER')
            cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test081-closed-source-')
            directory = Path(cls.baseline_directory.name)
            for path in CORE.glob('NG2*'):
                if path.suffix in ('.c', '.h'):
                    shutil.copyfile(path, directory/path.name)
            if baseline:
                shutil.copyfile(baseline, directory/'NG2Controller.c')
            mechanics.CORE = directory
            hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(mechanics.CORE.glob('NG2*')) if path.suffix in ('.c','.h')}
            evidence = os.environ.get('NECRO_TEST081_CLOSED_SOURCE_IDENTITY')
            if evidence:
                Path(evidence).write_text(json.dumps({'controller_override':baseline,
                    'source_sha256':hashes,'python_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in (Path(__file__),Path(fixture.__file__),Path(mechanics.__file__),
                                     Path(observation.__file__))}},sort_keys=True,indent=2)+'\n')
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    observe = mechanics.NativeRecoveryTests.observe
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    scene_details = mechanics.NativeRecoveryTests.scene_details
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    publish_procedural_candidate = mechanics.NativeRecoveryTests.publish_procedural_candidate
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    choice = observation.NativeObservation072Tests.choice
    motion = observation.NativeObservation072Tests.motion
    credit = observation.NativeObservation072Tests.credit
    observed_result = observation.NativeObservation072Tests.observed_result
    observed_vantage = observation.NativeObservation072Tests.observed_vantage

    def armed(self, direction=3, distance=3, opened=False, partial=False, protected=False):
        self.rotate = {1:lambda x,y:(y,-x),2:lambda x,y:(-y,x),
            3:lambda x,y:(x,y),4:lambda x,y:(-x,-y)}[direction]
        cells = {(0,-n):'floor' for n in range(distance+1)}
        cells.update({(0,-distance-1):'floor' if opened else 'door',
            (-1,-distance-1):'gold',(1,-distance-1):'gold',(-3,1):'stone'})
        terrain = fixture.textured({self.rotate(*cell):kind for cell,kind in cells.items()})
        if protected: terrain.protected.add(self.rotate(-3,1))
        self.fit(terrain); first = self.next_move(terrain)
        self.assertEqual(direction,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,direction)
        if partial: terrain.goods='partial'
        self.observed_result(first,terrain); command = self.next_move(terrain)
        self.assertEqual((1,1,1,1),(self.status().inputs,self.status().moves,
            self.status().lead_confirmed,self.status().input_state))
        if not opened:
            self.assertEqual((direction,7,(distance-1)*fixture.DIRS[direction][0],
                (distance-1)*fixture.DIRS[direction][1],1),self.choice(terrain))
        self.stone_cell = self.rotate(-3,2)
        return terrain,command

    def capped(self, direction=3, distance=3, opened=False, partial=False, protected=False):
        terrain,command = self.armed(direction,distance,opened,partial,protected)
        for cell in ((2,2),(3,2)):
            terrain = deepcopy(terrain); terrain.tiles[self.rotate(*cell)]='dirt'
            self.now += 2; self.observe_actual(self.scene(2,2,terrain,beat=True))
            command = self.next_move(terrain)
            self.assertEqual(2,self.scene_details()[-1].validation)
        self.assertEqual(2,self.scene_details()[-1].chain_count)
        return terrain,command

    def retiring(self, direction=3, distance=3, opened=False, partial=False, protected=False):
        terrain,old = self.capped(direction,distance,opened,partial,protected)
        anchor = deepcopy(terrain); anchor.tiles[self.rotate(-2,2)]='floor'
        self.assertEqual(self.choice(terrain),self.choice(anchor))
        self.assertEqual((2,0,0),self.motion(terrain,anchor,direction))
        self.now = old.deadline_ns-8_306_930; credit = self.credit()
        self.observe_actual(self.scene(2,2,anchor,beat=True))
        self.assertEqual((0,0,0,credit),(self.status().reason,self.status().terminal,
            self.status().input_state,self.credit()))
        retired = bytes(self.events()[-1])
        self.assertEqual((3,17,0,0,0),(self.events()[-1].outcome,
            self.events()[-1].reason,self.events()[-1].begin_ns,
            self.events()[-1].motion,self.events()[-1].observed_capture_id))
        self.assertEqual(bytes(old),bytes(self.events()[-1].command))
        self.reject_old_callbacks_without_mutation(old)
        return anchor,old,retired,credit

    def drift(self, anchor):
        changed = deepcopy(anchor); changed.tiles[self.stone_cell]='dirt'
        self.assertEqual(self.choice(anchor),self.choice(changed))
        self.assertEqual((2,0,0),self.motion(anchor,changed,3 if self.rotate(0,-1)==(0,-1)
            else {(-1,0):1,(1,0):2,(0,1):4}[self.rotate(0,-1)]))
        return changed

    def test_four_direction_closed_gate_refresh_accepts_remote_stone_without_credit(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine(); anchor,old,retired,credit = self.retiring(direction)
                changed = self.drift(anchor); self.now += 4
                self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual((0,0,credit),(self.status().reason,self.status().terminal,self.credit()),
                    'formal closed-gate refresh must accept independently stationary remote STONE drift')
                new = self.next_move(changed)
                self.assertGreater(new.id,old.id); self.assertGreater(new.target_ns,old.target_ns)
                self.assertGreaterEqual(new.not_before_ns-self.now,50_000_000)
                self.assertEqual((old.ordinal,direction),(new.ordinal,new.direction))
                self.assertEqual(credit,self.credit()); self.assertEqual(retired,bytes(self.events()[-2]))
                self.assertEqual(1,self.recovery().post_move_reacquisitions)
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new); self.observed_result(new,fixture.translated(changed,direction))
                self.assertEqual((0,2,2),(self.status().reason,self.status().inputs,self.status().moves))

    def test_geometry_near_cells_and_all_protection_materials_bound_stone_scope(self):
        for fault in ('distance2','distance4','opened','partial','protected_material',
                      'near_origin_diagonal','near_next_diagonal','origin','next','extra_gold',
                      'lost_gold','new_protection','door','item','route'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                if fault=='partial':
                    # PARTIAL already takes formal refresh at its first scene
                    # change; it cannot accumulate the UNKNOWN-goods SAME chain.
                    anchor,old=self.armed(partial=True); credit=self.credit()
                    changed=self.drift(anchor); self.now=old.deadline_ns-8_306_930
                    self.observe_actual(self.scene(2,2,changed,beat=True))
                    self.assertEqual((17,0,credit),(self.status().reason,
                        self.recovery().post_move_reacquisitions,self.credit()))
                    self.assertNotEqual(4,self.tick()[1].kind)
                    self.assertEqual(bytes(old),bytes(next(row for row in self.events() if row.command.id==old.id).command))
                    continue
                anchor,old,retired,credit = self.retiring(
                    distance=2 if fault=='distance2' else 4 if fault=='distance4' else 3,
                    protected=fault=='protected_material')
                changed = self.drift(anchor)
                if fault=='opened': changed.tiles[(0,-3)]='floor'
                elif fault=='near_origin_diagonal': changed.tiles[(1,1)]='dirt'
                elif fault=='near_next_diagonal': changed.tiles[(1,-2)]='dirt'
                elif fault=='origin': changed.tiles[(0,0)]='dirt'
                elif fault=='next': changed.tiles[(0,-1)]='dirt'
                elif fault=='extra_gold': changed.tiles[(-8,3)]='gold'
                elif fault=='lost_gold': changed.tiles[(-1,-3)]='dirt'
                elif fault=='new_protection': changed.protected.add((-8,3))
                elif fault in ('door','item'): changed.tiles[(-8,3)]=fault
                elif fault=='route': changed.tiles[(0,-2)]='dirt'
                self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual((17,credit),(self.status().reason,self.credit()))
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_direct_anchor_strict_proof_and_independent_current_prefix_are_required(self):
        for fault in ('unknown','moved','tween','wrong_prefix','unstable','overlap','transitive'):
            with self.subTest(fault=fault):
                self.fresh_engine(); anchor,old,retired,credit = self.retiring()
                changed = self.drift(anchor)
                if fault=='unknown':
                    rng=random.Random(81081)
                    changed.signature=bytes(rng.randrange(20,100) for _ in anchor.signature)
                elif fault in ('moved','tween'):
                    changed.signature=fixture.translated(anchor,3,9 if fault=='moved' else 8).signature
                elif fault=='transitive':
                    rng=random.Random(81081); noise=bytes(rng.randrange(20,100) for _ in anchor.signature)
                    middle=deepcopy(anchor)
                    middle.signature=bytes((80*a+20*b+50)//100 for a,b in zip(anchor.signature,noise))
                    changed.signature=bytes((60*a+40*b+50)//100 for a,b in zip(anchor.signature,noise))
                    self.assertEqual((2,0,0),self.motion(anchor,middle,3))
                    self.assertEqual((2,0,0),self.motion(middle,changed,3))
                    self.assertEqual((0,0,0),self.motion(anchor,changed,3),
                        'adjacent BLOCKED proofs do not establish original-anchor BLOCKED')
                    self.now+=4; self.observe_actual(self.scene(2,2,middle,beat=True))
                    self.assertEqual(0,self.status().reason)
                previous=self.now; self.now+=4
                options={'prefix':self.prefix-1} if fault=='wrong_prefix' else \
                    {'stable':0} if fault=='unstable' else {'start':previous-1} if fault=='overlap' else {}
                last=self.status().last_capture_id
                self.observe_actual(self.scene(2,2,changed,beat=True),**options)
                if fault in ('wrong_prefix','unstable'):
                    self.assertEqual((0,last),(self.status().reason,self.status().last_capture_id))
                    self.assertNotEqual(4,self.tick()[1].kind)
                else:
                    self.assertEqual(17,self.status().reason)
                    self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(credit,self.credit())
                self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_original_horizons_current_hud_and_fifty_ms_preparation_remain_frozen(self):
        for late in (0,1):
            with self.subTest(original_ticket_deadline_plus_one=late):
                self.fresh_engine(); terrain,old=self.capped(); changed=self.drift(terrain)
                self.now=old.deadline_ns-1; credit=self.credit()
                self.observe_actual(self.scene(2,2,changed,beat=True),commit=old.deadline_ns+late)
                self.now=old.deadline_ns+late
                if late:
                    self.assertEqual((17,0),(self.status().reason,self.recovery().post_move_reacquisitions))
                else:
                    self.assertEqual((0,1),(self.status().reason,self.recovery().post_move_reacquisitions))
                self.assertEqual(credit,self.credit())
                self.assertEqual(bytes(old),bytes(next(row for row in self.events() if row.command.id==old.id).command))
        for limit in ('proof','walk','session'):
            with self.subTest(limit=limit):
                self.fresh_engine(); anchor,old,retired,credit = self.retiring()
                deadline=min(self.verified_ns+12*SECOND,self.status().walk_started_ns+45*SECOND,
                    self.status().started_ns+180*SECOND)
                row=self.recovery().records[min(1,self.recovery().record_count-1)]
                self.assertEqual((6,3,deadline),(row.reason,row.clock,row.sync_deadline_ns))
                changed=self.drift(anchor); self.now+=4
                self.observe_actual(self.scene(2,2,changed,beat=True)); new=self.next_move(changed)
                self.now={'proof':deadline,'walk':self.status().walk_started_ns+45*SECOND,
                    'session':self.status().started_ns+180*SECOND}[limit]
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual({'proof':8,'walk':14,'session':15}[limit],self.status().reason)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                self.assertEqual(credit,self.credit())
                self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))
        for late in (0,1):
            with self.subTest(preparation_plus_one=late):
                self.fresh_engine(); anchor,old,_,credit=self.retiring()
                changed=self.drift(anchor); self.now+=4
                self.observe_actual(self.scene(2,2,changed,beat=True)); self.assertEqual(0,self.tick()[0])
                target=self.status().next_target_ns; self.assertGreater(target,old.target_ns)
                self.now=target-self.status().lead_ns-50_000_000+late
                self.observe_actual(self.scene(2,2,changed,beat=True)); ready,new=self.tick()
                if late:
                    self.assertEqual(0,ready); self.assertNotEqual(target,self.next_move(changed).target_ns)
                else:
                    self.assertEqual((1,4,target,50_000_000),
                        (ready,new.kind,new.target_ns,new.not_before_ns-self.now))
                self.assertEqual(credit,self.credit())
        self.fresh_engine(); anchor,old,_,credit=self.retiring()
        changed=self.drift(anchor); self.now+=4
        self.observe_actual(self.scene(2,2,changed,beat=True)); new=self.next_move(changed)
        self.now+=4; self.observe_actual(self.scene(2,2,changed,beat=False))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
        self.assertEqual((8,credit),(self.status().reason,self.credit()))

    def test_published_identity_source_and_old_refresh_scope_do_not_broaden(self):
        anchor,old,retired,credit=self.retiring(); changed=self.drift(anchor); self.now+=4
        self.observe_actual(self.scene(2,2,changed,beat=True)); new=self.next_move(changed)
        immutable=bytes(new); epoch=self.preparation_epoch(new)
        self.assertNotEqual(0,epoch); self.assertEqual(0,self.preparation_epoch(old))
        for kind in ('floor','dirt','stone'):
            latest=deepcopy(changed); latest.tiles[self.stone_cell]=kind; self.now+=4
            self.observe_actual(self.scene(2,2,latest,beat=True))
            self.assertEqual((0,1,new.id,epoch,credit),(self.status().reason,self.status().input_state,
                self.status().current_command_id,self.preparation_epoch(new),self.credit()))
            self.assertEqual(immutable,bytes(self.events()[-1].command))
            self.assertEqual(retired,bytes(self.events()[-2])); changed=latest
        self.reject_old_callbacks_without_mutation(old)
        # Existing singleton reason8 refresh stays within its old U/F/D scope.
        self.fresh_engine(); terrain,command=self.observed_vantage()
        for cell in ((1,0),(-1,0)):
            terrain=deepcopy(terrain); terrain.tiles[cell]='dirt'; self.now+=2
            self.observe_actual(self.scene(2,2,terrain,beat=True)); command=self.next_move(terrain)
            self.assertEqual(2,self.scene_details()[-1].validation)
        self.assertEqual(2,self.scene_details()[-1].chain_count)
        terrain=deepcopy(terrain); terrain.tiles[(1,1)]='dirt'
        self.now=command.deadline_ns-8_306_930
        self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual((0,0),(self.status().reason,self.status().input_state))
        drift=deepcopy(terrain); drift.tiles[(-8,3)]='stone'; self.now+=4
        self.assertEqual((2,0,0),self.motion(terrain,drift,3))
        self.observe_actual(self.scene(2,2,drift,beat=True))
        self.assertEqual(17,self.status().reason)

    def test_goods_cancel_phase_owner_and_unknown_sent_input_preempt_refresh(self):
        for stage in ('observing','issued'):
            for fault in ('goods','cancel','foreground','locked','owner','phase'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine(); anchor,old,retired,credit=self.retiring()
                    changed=self.drift(anchor)
                    if stage=='issued':
                        self.now+=4; self.observe_actual(self.scene(2,2,changed,beat=True)); new=self.next_move(changed)
                    if fault=='goods':
                        changed.goods='visible'; self.now+=4
                        self.observe_actual(self.scene(2,2,changed,beat=True))
                    elif fault=='cancel': self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    elif fault=='phase':
                        self.now+=4; frame=self.scene(2,2,changed,beat=True)
                        frame.beat_remaining=(frame.beat_remaining+.20)%1
                        self.observe_actual(frame); self.tick()
                    else:
                        flags={'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]]=int(fault=='locked')
                        self.tick(**flags)
                    if stage=='issued':
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertNotEqual(4,self.tick()[1].kind); self.assertEqual(credit,self.credit())
                    if fault!='phase':
                        self.assertEqual({'goods':1,'cancel':2,'foreground':3,'locked':4,'owner':5}[fault],self.status().reason)
                    elif stage=='observing': self.assertEqual(0,self.status().beat_period_ns)
                    else: self.assertEqual(8,self.status().reason)
                    self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))
        for state in ('started','sent_unknown'):
            with self.subTest(input_state=state):
                self.fresh_engine(); terrain,old=self.capped()
                self.now=old.not_before_ns
                self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                if state=='sent_unknown':
                    self.now+=1; self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,-1))
                credit=self.credit()
                changed=self.drift(terrain); self.now+=4
                self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual((old.id,0,credit),(self.status().current_command_id,
                    self.recovery().post_move_reacquisitions,self.credit()))
                self.assertNotEqual(4,self.tick()[1].kind)


if __name__ == '__main__':
    unittest.main()
