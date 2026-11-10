"""TEST072: observed terrain updates may not end an unstarted safe walk.

TEST071's 883 run has a protected mask overlapping an impassable GOLD
bracket, while 2e exhausts the old logical ticket's two SAME reissues.
Procedural public-C images below prove those control boundaries; their
later continuation does not reconstruct missing device captures.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests.test_native_blocked067 import Decision, Entrance

CORE = mechanics.CORE
SECOND = fixture.SECOND


class Motion(C.Structure):
    _fields_ = [(key, C.c_int32) for key in ('kind', 'dx', 'dy')]


class NativeObservation072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST072_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test072-observation-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory/path.name)
                shutil.copyfile(baseline, directory/'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(Motion)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
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

    def observed_result(self, command, terrain, offset=80_000_002):
        before = (self.status().moves, self.status().door_changes, self.status().terrain_changes)
        mechanics.NativeRecoveryTests.observed_result(self, command, terrain, offset)
        if before != (self.status().moves, self.status().door_changes, self.status().terrain_changes):
            self.verified_ns = self.now

    def credit(self):
        status = self.status()
        return (status.inputs, status.moves, status.door_changes, status.terrain_changes,
            status.x, status.y, status.last_ordinal, status.first_move_ns, status.lead_ns)

    def choice(self, terrain, entrance=None):
        visits = (C.c_uint16*1089)(); visits[16*33+16] = 1
        x = y = 0
        for event in self.events():
            if event.motion == 1:
                x += event.dx; y += event.dy
                visits[(y+16)*33+x+16] += 1
        frame = self.scene(2, 2, terrain, beat=True)
        choice = Decision()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(frame), x, y, visits,
            len(visits), C.byref(entrance or Entrance()), C.byref(choice)))
        return tuple(getattr(choice, key) for key, _ in choice._fields_)

    def motion(self, before, after, direction):
        first = self.scene(2, 2, before); second = self.scene(2, 2, after)
        motion = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(first), C.byref(second), direction, C.byref(motion)))
        return motion.kind, motion.dx, motion.dy

    def protected_gold_entry(self, direction=1, side=1):
        rotate = {1: lambda x,y: (y,-x), 2: lambda x,y: (-y,x),
            3: lambda x,y: (x,y), 4: lambda x,y: (-x,-y)}[direction]
        terrain = fixture.textured({rotate(x,y):kind for (x,y),kind in {
            (0,0):'floor',(0,-1):'floor',(0,-2):'door',(-1,-2):'gold',
            (1,-2):'gold',(0,-3):'floor',(0,-4):'floor'}.items()})
        self.fit(terrain); first = self.next_move(terrain); self.assertEqual(direction,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,direction); self.observed_result(first,terrain)
        opening = self.next_move(terrain); self.ack(opening)
        terrain = deepcopy(terrain); terrain.tiles[fixture.DIRS[direction]] = 'floor'; terrain.goods = 'partial'
        self.bracket = rotate(side,-1); terrain.protected.add(self.bracket)
        self.observed_result(opening,terrain)
        command = self.next_move(terrain)
        self.assertEqual((direction,5,*fixture.DIRS[direction],1),self.choice(terrain))
        self.assertEqual((2,1,1,0), (self.status().inputs,self.status().moves,
            self.status().door_changes,self.status().reason))
        return terrain,command

    def armed_floor(self):
        terrain = fixture.textured({(0,0):'floor',(0,-1):'floor',(0,-2):'floor',
            (0,-3):'floor',(0,-4):'door',(-1,-4):'gold',(1,-4):'gold',
            (2,0):'dirt',(3,0):'floor',(-4,-2):'stone',(5,1):'stone'})
        self.fit(terrain)
        for _ in range(2):
            command = self.next_move(terrain); self.assertEqual(3,command.direction)
            self.ack(command); terrain = fixture.translated(terrain,3); self.observed_result(command,terrain)
        command = self.next_move(terrain)
        self.assertEqual((2,2,1,1),(self.status().inputs,self.status().moves,
            self.status().lead_confirmed,self.status().input_state))
        self.assertEqual(7,self.choice(terrain)[1],
            'the independent-refresh fixture remains a bracket approach, distinct from reason8 quiet walking')
        return terrain,command

    def observed_vantage(self, direction=3):
        rotate = {1: lambda x,y: (y,-x), 2: lambda x,y: (-y,x),
            3: lambda x,y: (x,y), 4: lambda x,y: (-x,-y)}[direction]
        terrain = fixture.textured({rotate(x,y):kind for (x,y),kind in {
            (0,0):'floor',(0,-1):'floor',(0,-2):'floor',(0,-3):'floor',(0,-4):'gold'}.items()})
        dx,dy = fixture.DIRS[direction]
        terrain.tiles[(2+dx,2+dy)]='dirt'; terrain.tiles[(3+dx,2+dy)]='floor'
        self.fit(terrain); first = self.next_move(terrain); self.assertEqual(direction,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,direction); self.observed_result(first,terrain)
        command = self.next_move(terrain)
        self.assertEqual((direction,8,1),(self.choice(terrain)[0],self.choice(terrain)[1],self.choice(terrain)[4]))
        return terrain,command

    def test_unknown_goods_observed_vantage_keeps_original_beat_for_irrelevant_drift(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine(); terrain,command = self.observed_vantage(direction)
                credit = self.credit(); epoch = self.preparation_epoch(command)
                saved = (tuple(bytes(row) for row in self.events()),bytes(self.motion_wait()),
                    bytes(self.recovery()),tuple(bytes(row) for row in self.scene_details()))
                for _ in range(3):
                    changed = deepcopy(terrain)
                    changed.tiles[(2,2)]='floor' if terrain.tiles[(2,2)]=='dirt' else 'dirt'
                    changed.tiles[(3,2)]='floor' if terrain.tiles[(3,2)]=='dirt' else 'dirt'
                    self.assertEqual(self.choice(terrain),self.choice(changed))
                    self.assertEqual((2,0,0),self.motion(terrain,changed,direction))
                    self.now += 2; self.observe_actual(self.scene(2,2,changed,beat=True))
                    self.assertEqual((0,1,command.id,credit),(self.status().reason,self.status().input_state,
                        self.status().current_command_id,self.credit()),
                        'unchanged known-floor vantage must retain its physical beat instead of spending another observation beat')
                    self.assertEqual(bytes(command),bytes(self.events()[-1].command))
                    self.assertEqual(epoch,self.preparation_epoch(command))
                    self.assertEqual(saved,(tuple(bytes(row) for row in self.events()),bytes(self.motion_wait()),
                        bytes(self.recovery()),tuple(bytes(row) for row in self.scene_details())))
                    terrain = changed
                self.ack(command); self.observed_result(command,fixture.translated(terrain,direction))
                self.assertEqual((0,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        for fault in ('deadline_equal','deadline_plus','near','next','route','gold','protected','partial',
                      'unknown','moved','tween','wrong_prefix','unstable','phase','foreground','locked','owner'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,command = self.observed_vantage()
                changed = deepcopy(terrain); changed.tiles[(2,2)]='floor'; changed.tiles[(3,2)]='dirt'
                if fault=='near': changed.tiles[(1,0)]='dirt'
                elif fault=='next': changed.tiles[(0,-1)]='dirt'
                elif fault=='route': changed.tiles[(0,-2)]='dirt'
                elif fault=='gold': changed.tiles[(8,-3)]='gold'
                elif fault=='protected': changed.protected.add((8,-3))
                elif fault=='partial': changed.goods='partial'
                elif fault=='unknown': changed.signature=bytes([40])*23296
                elif fault in ('moved','tween'):
                    changed.signature=fixture.translated(terrain,3,9 if fault=='moved' else 8).signature
                options = {}
                self.now = command.deadline_ns-1 if fault.startswith('deadline') else self.now+2
                # Rebuild the HUD after choosing the actual capture clock.
                frame = self.scene(2,2,changed,beat=True)
                if fault=='phase': frame.beat_remaining=(frame.beat_remaining+.20)%1
                if fault.startswith('deadline'): options['commit']=command.deadline_ns+int(fault=='deadline_plus')
                elif fault=='wrong_prefix': options['prefix']=self.prefix-1
                elif fault=='unstable': options['stable']=0
                credit = self.credit(); last_capture = self.status().last_capture_id
                events = tuple(bytes(row) for row in self.events())
                self.observe_actual(frame,**options)
                self.now = max(self.now,options.get('commit',self.now))
                if fault in ('wrong_prefix','unstable'):
                    self.assertEqual((command.id,last_capture,events),(self.status().current_command_id,
                        self.status().last_capture_id,tuple(bytes(row) for row in self.events())))
                elif fault=='deadline_equal':
                    self.assertEqual(command.id,self.status().current_command_id)
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,command.deadline_ns,1,0,1))
                    continue
                else:
                    if fault in ('foreground','locked','owner'):
                        flags={'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]]=int(fault=='locked')
                        self.tick(**flags)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                    ready,replacement = self.tick()
                    if ready and replacement.kind==4:
                        # Ordinary SAME/FRESH may issue a different ID under
                        # their existing guards. This is not quiet retention.
                        self.assertNotEqual(command.id,replacement.id)
                self.assertEqual(credit,self.credit())

    def capped_floor(self):
        terrain, original = self.armed_floor(); current = original
        for cell in ((8,3),(9,3)):
            terrain = deepcopy(terrain); terrain.tiles[cell] = 'dirt'; self.now += 2
            self.observe_actual(self.scene(2,2,terrain,beat=True)); current = self.next_move(terrain)
            self.assertEqual(2,self.scene_details()[-1].validation)
        self.assertEqual(2,self.scene_details()[-1].chain_count)
        return terrain,current

    def retire_after_same_chain(self):
        terrain,current = self.capped_floor()
        changed = deepcopy(terrain); changed.tiles[(2,2)] = 'floor'; changed.tiles[(3,2)] = 'dirt'
        self.assertEqual(self.choice(terrain),self.choice(changed))
        self.assertEqual((2,0,0),self.motion(terrain,changed,current.direction))
        self.now = current.deadline_ns-8_306_930
        credit = self.credit(); self.observe_actual(self.scene(2,2,changed,beat=True))
        self.assertEqual((0,0,0,credit),(self.status().reason,self.status().terminal,
            self.status().input_state,self.credit()),
            'after two old SAME reissues, a new independent floor observation must replace the unsent ticket without ending the run')
        row = self.events()[-1]
        self.assertEqual((3,17,0,0,0),(row.outcome,row.reason,row.begin_ns,row.motion,row.observed_capture_id))
        self.assertEqual(bytes(current),bytes(row.command)); self.reject_old_callbacks_without_mutation(current)
        return changed,current,bytes(row),credit

    def test_protected_gold_wall_does_not_block_the_same_observed_entry(self):
        for direction in (1,2,3,4):
            for side in (-1,1):
                with self.subTest(direction=direction,side=side):
                    self.fresh_engine(); terrain,command = self.protected_gold_entry(direction,side)
                    changed = deepcopy(terrain); changed.tiles[(-3,-1)] = 'dirt'
                    self.assertEqual(self.choice(terrain),self.choice(changed))
                    self.assertEqual((2,0,0),self.motion(terrain,changed,direction))
                    events = tuple(bytes(row) for row in self.events()); credit = self.credit()
                    self.now += 2; self.observe_actual(self.scene(2,2,changed,beat=True))
                    self.assertEqual((0,1,command.id,credit),(self.status().reason,self.status().input_state,
                        self.status().current_command_id,self.credit()),
                        'a static protected mask over an impassable GOLD bracket must not cancel the FLOOR entry')
                    self.assertEqual(events,tuple(bytes(row) for row in self.events()))
                    self.ack(command); self.observed_result(command,fixture.translated(changed,direction))
                    self.assertEqual((0,3,2,1,0),(self.status().reason,self.status().inputs,
                        self.status().moves,self.status().door_changes,self.status().goods))
                    # The same GOLD wall now neighbors the player. It remains
                    # impassable, while the next interior FLOOR is unprotected.
                    interior = fixture.translated(changed,direction)
                    further = self.next_move(interior)
                    self.assertEqual(direction,further.direction)
                    self.ack(further); self.observed_result(further,fixture.translated(interior,direction))
                    self.assertEqual((0,4,3,1,0),(self.status().reason,self.status().inputs,
                        self.status().moves,self.status().door_changes,self.status().goods))

    def test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket(self):
        changed, old, retired, credit = self.retire_after_same_chain()
        self.assertNotEqual(4,self.tick()[1].kind)
        self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True))
        new = self.next_move(changed)
        self.assertGreater(new.id,old.id); self.assertGreater(new.target_ns,old.target_ns)
        self.assertGreaterEqual(new.not_before_ns-self.now,50_000_000)
        self.assertEqual((old.ordinal,old.direction),(new.ordinal,new.direction))
        self.assertEqual(credit,self.credit()); self.assertEqual(retired,bytes(self.events()[-2]))
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new); self.observed_result(new,fixture.translated(changed,new.direction))
        self.assertEqual((0,3,3),(self.status().reason,self.status().inputs,self.status().moves))

    def test_current_floor_refresh_rejects_changed_action_protection_and_old_input_authority(self):
        for fault in ('deadline_equal','deadline_plus','begun','sent_unknown','wrong_prefix','unstable',
                      'unknown','moved','tween','gold','protected','origin','next','door','item','stone',
                      'partial','visible'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain,old = self.capped_floor()
                changed = deepcopy(terrain); changed.tiles[(2,2)] = 'floor'; changed.tiles[(3,2)] = 'dirt'
                if fault == 'unknown': changed.signature = bytes([40])*23296
                elif fault in ('moved','tween'):
                    changed.signature = fixture.translated(terrain,3,9 if fault=='moved' else 8).signature
                elif fault == 'gold': changed.tiles[(8,-3)] = 'gold'
                elif fault == 'protected': changed.protected.add((8,-3))
                elif fault == 'origin': changed.tiles[(0,0)] = 'dirt'
                elif fault == 'next': changed.tiles[(0,-1)] = 'dirt'
                elif fault == 'door': changed.tiles[(8,-3)] = 'door'
                elif fault == 'item': changed.tiles[(8,-3)] = 'item'
                elif fault == 'stone': changed.tiles[(8,-3)] = 'stone'
                elif fault in ('partial','visible'): changed.goods = fault
                options = {}
                if fault in ('begun','sent_unknown'):
                    self.now = old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    if fault == 'sent_unknown':
                        self.now += 1; self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,-1))
                else:
                    self.now = old.deadline_ns-1 if fault.startswith('deadline') else old.deadline_ns-8_306_930
                if fault.startswith('deadline'): options['commit'] = old.deadline_ns+int(fault=='deadline_plus')
                elif fault == 'wrong_prefix': options['prefix'] = self.prefix-1
                elif fault == 'unstable': options['stable'] = 0
                credit = self.credit(); self.observe_actual(self.scene(2,2,changed,beat=True),**options)
                self.assertEqual(credit,self.credit())
                if fault == 'deadline_equal':
                    self.assertEqual((0,0,1),(self.status().reason,self.status().input_state,
                        self.recovery().post_move_reacquisitions))
                else:
                    self.assertEqual(0,self.recovery().post_move_reacquisitions)
                    if fault == 'visible': self.assertEqual((1,1),(self.status().reason,self.status().goods))
                    elif fault in ('begun','sent_unknown','wrong_prefix','unstable'):
                        self.assertEqual(old.id,self.status().current_command_id)
                    else: self.assertEqual(17,self.status().reason)
                self.assertEqual(bytes(old),bytes(next(row for row in self.events() if row.command.id==old.id).command))

    def test_independent_floor_proof_and_published_ticket_keep_full_current_permission(self):
        for stage in ('observing','issued'):
            for fault in ('unknown','moved','tween','gold','protected','origin','next','item','partial',
                          'wrong_prefix','unstable','overlap'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine(); changed,old,retired,credit = self.retire_after_same_chain()
                    if stage == 'issued':
                        self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True)); new = self.next_move(changed)
                    drift = deepcopy(changed)
                    if fault == 'unknown':
                        rng = random.Random(72072); drift.signature = bytes(rng.randrange(20,100) for _ in range(23296))
                    elif fault in ('moved','tween'):
                        drift.signature = fixture.translated(changed,3,9 if fault=='moved' else 8).signature
                    elif fault == 'gold': drift.tiles[(8,-3)] = 'gold'
                    elif fault == 'protected': drift.protected.add((8,-3))
                    elif fault == 'origin': drift.tiles[(0,0)] = 'dirt'
                    elif fault == 'next': drift.tiles[(0,-1)] = 'dirt'
                    elif fault == 'item': drift.tiles[(8,-3)] = 'item'
                    elif fault == 'partial': drift.goods = 'partial'
                    previous_end = self.now; self.now += 4
                    options = {'prefix':self.prefix-1} if fault=='wrong_prefix' else \
                        {'stable':0} if fault=='unstable' else \
                        {'start':previous_end-1} if fault=='overlap' else {}
                    self.observe_actual(self.scene(2,2,drift,beat=True),**options)
                    self.assertEqual(credit,self.credit())
                    if fault in ('wrong_prefix','unstable'):
                        if stage == 'observing': self.assertNotEqual(4,self.tick()[1].kind)
                        else: self.assertEqual(new.id,self.status().current_command_id)
                    elif fault=='unknown' and stage=='observing':
                        self.assertEqual(0,self.status().reason); self.assertNotEqual(4,self.tick()[1].kind)
                    else:
                        self.assertEqual(17,self.status().reason); self.assertNotEqual(4,self.tick()[1].kind)
                        if stage=='issued':
                            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required(self):
        for limit in ('proof','walk','session'):
            with self.subTest(limit=limit):
                self.fresh_engine(); changed,old,retired,credit = self.retire_after_same_chain()
                deadline = min(self.verified_ns+12*SECOND,self.status().walk_started_ns+45*SECOND,
                    self.status().started_ns+180*SECOND)
                row = self.recovery().records[min(1,self.recovery().record_count-1)]
                self.assertEqual((6,3,deadline),(row.reason,row.clock,row.sync_deadline_ns))
                self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True)); new = self.next_move(changed)
                self.now = {'proof':deadline,'walk':self.status().walk_started_ns+45*SECOND,
                    'session':self.status().started_ns+180*SECOND}[limit]
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual({'proof':8,'walk':14,'session':15}[limit],self.status().reason)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                self.assertEqual(credit,self.credit())
                self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))
        for late in (0,1):
            with self.subTest(preparation_plus_one=late):
                self.fresh_engine(); changed,old,_,credit = self.retire_after_same_chain()
                self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual(0,self.tick()[0]); target = self.status().next_target_ns
                self.assertGreater(target,old.target_ns)
                self.now = target-self.status().lead_ns-50_000_000+late
                self.observe_actual(self.scene(2,2,changed,beat=True)); ready,new = self.tick()
                if late:
                    self.assertEqual(0,ready); self.assertNotEqual(target,self.next_move(changed).target_ns)
                else: self.assertEqual((1,4,target,50_000_000),(ready,new.kind,new.target_ns,new.not_before_ns-self.now))
                self.assertEqual(credit,self.credit())
        self.fresh_engine(); changed,old,_,credit = self.retire_after_same_chain()
        self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True)); new = self.next_move(changed)
        self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=False))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1),
            'a newly accepted geometric proof cannot use an older HUD sample at final begin')
        self.assertEqual((8,credit),(self.status().reason,self.credit()))

    def test_goods_cancellation_phase_and_owner_guards_preempt_observing_or_issued_refresh(self):
        for stage in ('observing','issued'):
            for fault in ('goods','cancel','foreground','locked','owner','phase'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine(); changed,old,retired,credit = self.retire_after_same_chain()
                    if stage=='issued':
                        self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True)); new = self.next_move(changed)
                    if fault=='goods':
                        goods = deepcopy(changed); goods.goods = 'visible'; self.now += 4
                        self.observe_actual(self.scene(2,2,goods,beat=True))
                    elif fault=='cancel': self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    elif fault=='phase':
                        self.now += 4; frame = self.scene(2,2,changed,beat=True)
                        frame.beat_remaining = (frame.beat_remaining+.20)%1
                        self.observe_actual(frame); self.tick()
                    else:
                        flags = {'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]] = int(fault=='locked')
                        self.tick(**flags)
                    if stage=='issued':
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertNotEqual(4,self.tick()[1].kind); self.assertEqual(credit,self.credit())
                    if fault!='phase':
                        self.assertEqual({'goods':1,'cancel':2,'foreground':3,'locked':4,'owner':5}[fault],self.status().reason)
                    elif stage=='observing': self.assertEqual(0,self.status().beat_period_ns)
                    else: self.assertEqual(8,self.status().reason)
                    self.assertEqual(retired,bytes(next(row for row in self.events() if row.command.id==old.id)))

    def test_refresh_limit_is_once_per_verified_progress_and_eight_per_session(self):
        terrain = fixture.textured({**{(x,0):'floor' for x in range(-9,1)},
            (-9,-1):'floor',(-9,-2):'floor',(-10,-2):'floor',(-11,-2):'door',
            (-11,-3):'gold',(-11,-1):'gold'})
        self.fit(terrain); first = self.next_move(terrain); self.ack(first)
        terrain = fixture.translated(terrain,first.direction); terrain.goods='partial'
        self.observed_result(first,terrain); old = self.next_move(terrain)
        for attempt in range(1,10):
            changed = deepcopy(terrain); changed.tiles[(-10,4)]='dirt'
            self.assertEqual(self.choice(terrain),self.choice(changed))
            self.assertEqual(1,self.choice(changed)[4]); self.assertEqual((2,0,0),self.motion(terrain,changed,old.direction))
            credit = self.credit(); self.now += 2; self.observe_actual(self.scene(2,2,changed,beat=True))
            if attempt==9:
                self.assertEqual((17,8,credit),(self.status().reason,self.recovery().post_move_reacquisitions,self.credit()))
                self.assertEqual((3,0),(self.events()[-1].outcome,self.events()[-1].begin_ns))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                break
            self.assertEqual((0,0,attempt,credit),(self.status().reason,self.status().input_state,
                self.recovery().post_move_reacquisitions,self.credit()))
            retired = bytes(self.events()[-1]); self.now += 4
            self.observe_actual(self.scene(2,2,changed,beat=True)); new = self.next_move(changed)
            # More same-action palette observations before begin retain this
            # new logical ticket and cannot replenish the verified budget.
            latest = deepcopy(changed); latest.tiles[(-11,3)]='dirt'; self.now += 4
            self.observe_actual(self.scene(2,2,latest,beat=True))
            self.assertEqual((new.id,attempt,credit),(self.status().current_command_id,
                self.recovery().post_move_reacquisitions,self.credit()))
            self.assertEqual(retired,bytes(self.events()[-2])); self.reject_old_callbacks_without_mutation(old)
            self.ack(new); terrain = fixture.translated(latest,new.direction); self.observed_result(new,terrain)
            old = self.next_move(terrain)


if __name__ == '__main__':
    unittest.main()
