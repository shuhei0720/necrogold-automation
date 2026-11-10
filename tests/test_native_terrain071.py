"""TEST071: reobserve a never-sent DIRT action newly observed as FLOOR.

The received 3c1 pair motivates the DIRT/reason6 -> FLOOR/reason7 case.
Every image, later observation and successful continuation here is procedural
public-C evidence, not a reconstruction of absent device captures.
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
PERIOD = fixture.PERIOD


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


class NativeTerrain071Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST071_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test071-terrain-baseline-')
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
    scene_details = mechanics.NativeRecoveryTests.scene_details

    def observed_result(self, command, terrain, offset=80_000_002):
        moves = self.status().moves
        mechanics.NativeRecoveryTests.observed_result(self, command, terrain, offset)
        if self.status().moves > moves:
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

    def armed_dirt(self, direction=1, second_gate=False, distance=3, goods='unknown', late_parent=False):
        tiles = {(0,0): 'floor', (0,-1): 'floor', (0,-2): 'dirt', (0,-3): 'floor',
            (-1,-3): 'gold', (1,-3): 'gold', (0,-4): 'floor'}
        if distance != 3:
            tiles = {(0,0): 'floor', (0,-1): 'floor'}
            tiles.update({(0,-step): 'dirt' for step in range(2, distance)})
            tiles.update({(0,-distance): 'dirt' if distance == 2 else 'floor',
                (-1,-distance): 'gold', (1,-distance): 'gold', (0,-distance-1): 'floor'})
        if second_gate:
            tiles.update({(0,-4): 'dirt', (0,-5): 'floor', (-1,-5): 'gold',
                (1,-5): 'gold', (0,-6): 'floor'})
        rotate = {1: lambda x,y: (y,-x), 2: lambda x,y: (-y,x),
            3: lambda x,y: (x,y), 4: lambda x,y: (-x,-y)}[direction]
        terrain = fixture.textured({rotate(x,y): kind for (x,y),kind in tiles.items()})
        self.fit(terrain)
        first = self.next_move(); self.assertEqual(direction, first.direction)
        self.ack(first)
        terrain = fixture.translated(terrain, direction)
        terrain.tiles[(8,3)] = 'floor'
        terrain.goods = goods
        self.observed_result(first, terrain,
            PERIOD-150_000_000+10_000_001 if late_parent else 80_000_002)
        old = self.next_move(terrain)
        dx,dy = fixture.DIRS[direction]
        target = max(1, distance-2)
        self.assertEqual((direction,5 if distance == 2 else 6,target*dx,target*dy,4), self.choice(terrain))
        self.assertEqual((1,1,1,0), (self.status().inputs, self.status().moves,
            self.status().lead_confirmed, self.status().reason))
        return terrain, old

    def opened(self, terrain, direction=1):
        changed = deepcopy(terrain)
        changed.tiles[fixture.DIRS[direction]] = 'floor'
        changed.tiles[(8,3)] = 'dirt'
        return changed

    def withdraw(self, direction=1, second_gate=False, late_parent=False):
        terrain, old = self.armed_dirt(direction, second_gate, late_parent=late_parent)
        changed = self.opened(terrain, direction)
        dx,dy = fixture.DIRS[direction]
        self.assertEqual((direction,7,dx,dy,1), self.choice(changed))
        self.assertEqual((4,0,0), self.motion(terrain, changed, direction))
        credit = self.credit(); period = self.status().beat_period_ns
        previous_recoveries = self.recovery().post_move_reacquisitions
        self.now = old.deadline_ns-36_326_275
        self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual((0,0,0,credit), (self.status().reason, self.status().terminal,
            self.status().input_state, self.credit()),
            'a never-sent DIRT action must withdraw for an independent FLOOR proof, not end the run')
        event = self.events()[-1]
        self.assertEqual((3,17,0,0,0), (event.outcome, event.reason, event.begin_ns,
            event.motion, event.observed_capture_id))
        self.assertEqual(bytes(old), bytes(event.command))
        self.assertEqual((old.id-1,0), (self.status().last_completed_id, self.status().current_command_id))
        self.assertEqual((period,0), (self.status().beat_period_ns, self.motion_wait().active),
            'an unchanged valid HUD model must not be retired for another two-second fit')
        recovery = self.recovery(); row = recovery.records[min(1, recovery.record_count-1)]
        deadline = min(self.verified_ns+12*SECOND, self.status().walk_started_ns+45*SECOND,
            self.status().started_ns+180*SECOND)
        self.assertEqual((2,previous_recoveries+1,6,3,old.id,self.number,deadline),
            (recovery.mode,recovery.post_move_reacquisitions,row.reason,row.clock,
             row.command_id,row.capture_id,row.sync_deadline_ns))
        self.assertEqual(self.now, row.at_ns)
        self.assertEqual(period, row.model.period_ns)
        self.assertNotEqual(4, self.tick()[1].kind)
        self.reject_old_callbacks_without_mutation(old)
        return changed, old, bytes(event), deadline, credit

    def new_ticket(self, changed, old, beat=True):
        started = self.now
        self.now += 4
        self.observe_actual(self.scene(2, 2, changed, beat=beat))
        proof_midpoint = self.now-1
        if not beat:
            self.assertNotEqual(4, self.tick()[1].kind)
            self.now += 60_000_000
            self.observe_actual(self.scene(2, 2, changed, beat=True))
            proof_midpoint = self.now-1
        new = self.next_move(changed)
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertEqual((old.ordinal,old.direction), (new.ordinal,new.direction))
        self.assertGreater(new.source_capture_id, old.source_capture_id)
        self.assertGreaterEqual(new.not_before_ns-self.now, 50_000_000)
        self.assertGreaterEqual(new.phase_sample_ns, proof_midpoint)
        self.assertLess(self.now-started, PERIOD+100_000_000)
        return new

    def test_independent_floor_proof_resumes_on_a_future_beat_without_opening_credit(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine()
                changed, old, retired, _, credit = self.withdraw(direction)
                new = self.new_ticket(changed, old)
                self.assertEqual(credit, self.credit())
                self.assertEqual(retired, bytes(self.events()[-2]))
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new)
                self.observed_result(new, fixture.translated(changed, direction))
                self.assertEqual((2,2,0,0,0), (self.status().inputs, self.status().moves,
                    self.status().door_changes, self.status().terrain_changes, self.status().reason))
                self.assertEqual((2,1), (self.events()[-1].outcome, self.events()[-1].motion))
                self.assertEqual(retired, bytes(self.events()[-2]))

    def test_trigger_requires_a_never_started_unit_action_and_original_commit_deadline(self):
        faults = ('deadline_equal','deadline_plus','begun','sent_unknown','ack_opened',
            'wrong_prefix','unstable','unknown','moved','tween','blocked','nonunit_target',
            'gate_reason','old_partial','partial','visible','gold','protected','origin','next_door')
        for fault in faults:
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, old = self.armed_dirt(distance=4 if fault == 'nonunit_target' else
                    2 if fault == 'gate_reason' else 3,
                    goods='partial' if fault == 'old_partial' else 'unknown')
                changed = self.opened(terrain)
                if fault == 'unknown': changed.signature = bytes([40])*23296
                elif fault in ('moved','tween'):
                    moved = fixture.translated(terrain, 1, 9 if fault == 'moved' else 8)
                    changed.signature = moved.signature
                elif fault == 'blocked': changed.tiles[(-1,0)] = 'dirt'
                elif fault == 'partial': changed.goods = 'partial'
                elif fault == 'visible': changed.goods = 'visible'
                elif fault == 'gold': changed.tiles[(8,-3)] = 'gold'
                elif fault == 'protected': changed.protected.add((8,-3))
                elif fault == 'origin': changed.tiles[(0,0)] = 'stone'
                elif fault == 'next_door': changed.tiles[(-1,0)] = 'door'
                if fault in ('begun','sent_unknown'):
                    self.now = old.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
                    if fault == 'sent_unknown':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, old.id, self.now, -1))
                elif fault == 'ack_opened':
                    self.ack(old)
                    self.observed_result(old, changed)
                    self.assertEqual((2,4), (self.events()[-1].outcome,self.events()[-1].motion))
                    self.assertGreater(self.events()[-1].observed_capture_id, 0)
                    self.assertEqual((2,1,1), (self.status().inputs,self.status().moves,self.status().terrain_changes))
                    self.assertEqual(0, self.recovery().post_move_reacquisitions)
                    continue
                else:
                    self.now = old.deadline_ns-1 if fault.startswith('deadline_') else old.deadline_ns-36_326_275
                credit = self.credit()
                options = {}
                if fault.startswith('deadline_'): options['commit'] = old.deadline_ns+int(fault == 'deadline_plus')
                elif fault == 'wrong_prefix': options['prefix'] = self.prefix-1
                elif fault == 'unstable': options['stable'] = 0
                self.observe_actual(self.scene(2,2,changed,beat=True), **options)
                self.assertEqual(credit, self.credit())
                if fault == 'deadline_equal':
                    self.assertEqual((0,0,1), (self.status().reason,self.status().input_state,
                        self.recovery().post_move_reacquisitions))
                    self.reject_old_callbacks_without_mutation(old)
                else:
                    self.assertEqual(0, self.recovery().post_move_reacquisitions,
                        'no rejected pair or previously started input may enter the new recovery')
                    if fault == 'visible': self.assertEqual((1,1), (self.status().reason,self.status().goods))
                    elif fault in ('wrong_prefix','unstable','begun','sent_unknown'):
                        self.assertEqual(old.id, self.status().current_command_id)
                self.assertEqual(bytes(old), bytes(next(e for e in self.events() if e.command.id == old.id).command))

    def test_independent_proof_and_issued_ticket_reject_motion_geometry_and_invalid_prefix(self):
        for stage in ('observing','issued'):
            for fault in ('unknown','moved','tween','gold','protected','origin','next','local','partial',
                          'wrong_prefix','unstable','overlap'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine()
                    changed, old, retired, _, credit = self.withdraw()
                    if stage == 'issued': new = self.new_ticket(changed, old)
                    drift = deepcopy(changed)
                    if fault == 'unknown':
                        rng = random.Random(71071); drift.signature = bytes(rng.randrange(20,100) for _ in range(23296))
                    elif fault in ('moved','tween'):
                        drift.signature = fixture.translated(changed, 1, 9 if fault == 'moved' else 8).signature
                    elif fault == 'gold': drift.tiles[(8,-3)] = 'gold'
                    elif fault == 'protected': drift.protected.add((8,-3))
                    elif fault == 'origin': drift.tiles[(0,0)] = 'stone'
                    elif fault == 'next': drift.tiles[(-1,0)] = 'dirt'
                    elif fault == 'local': drift.tiles[(0,1)] = 'stone'
                    elif fault == 'partial': drift.goods = 'partial'
                    previous_end = self.now
                    self.now += 4
                    options = {'prefix': self.prefix-1} if fault == 'wrong_prefix' else \
                        {'stable':0} if fault == 'unstable' else \
                        {'start':previous_end-1} if fault == 'overlap' else {}
                    self.observe_actual(self.scene(2,2,drift,beat=True), **options)
                    self.assertEqual(credit, self.credit())
                    if fault in ('wrong_prefix','unstable'):
                        if stage == 'observing':
                            self.assertNotEqual(4, self.tick()[1].kind)
                            self.new_ticket(changed, old)
                        else:
                            self.assertEqual(new.id, self.status().current_command_id)
                    elif fault == 'unknown' and stage == 'observing':
                        self.assertEqual(0, self.status().reason)
                        self.assertNotEqual(4, self.tick()[1].kind)
                        self.new_ticket(drift, old)
                    else:
                        self.assertEqual(17, self.status().reason)
                        self.assertNotEqual(4, self.tick()[1].kind)
                        if stage == 'issued':
                            self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                                new.not_before_ns, 1,0,1))
                    self.assertEqual(retired, bytes(next(e for e in self.events() if e.command.id == old.id)))

    def test_hud_proof_original_budgets_and_fifty_ms_preparation_are_not_reset(self):
        for late_parent in (False, True):
            with self.subTest(late_parent=late_parent):
                self.fresh_engine()
                changed, old, retired, deadline, credit = self.withdraw(late_parent=late_parent)
                new = self.new_ticket(changed, old, beat=False)
                self.assertEqual(deadline,
                    self.recovery().records[min(1,self.recovery().record_count-1)].sync_deadline_ns)
                self.assertEqual(credit, self.credit())
                self.assertEqual(retired, bytes(self.events()[-2]))
                self.now = deadline
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(8, self.status().reason)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                    new.not_before_ns, 1,0,1))
        for limit in ('walk','session'):
            with self.subTest(limit=limit):
                self.fresh_engine()
                changed, old, _, _, credit = self.withdraw()
                new = self.new_ticket(changed, old)
                self.now = self.status().walk_started_ns+45*SECOND if limit == 'walk' else self.status().started_ns+180*SECOND
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(14 if limit == 'walk' else 15, self.status().reason)
                self.assertEqual(credit, self.credit())
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id, self.now,1,0,1))
        for late in (0,1):
            with self.subTest(preparation_plus_one=late):
                self.fresh_engine()
                changed, old, _, _, credit = self.withdraw()
                self.now += 4; self.observe_actual(self.scene(2,2,changed,beat=True))
                self.assertEqual(0, self.tick()[0])
                target = self.status().next_target_ns; self.assertGreater(target,old.target_ns)
                self.now = target-self.status().lead_ns-50_000_000+late
                self.observe_actual(self.scene(2,2,changed,beat=True))
                ready, new = self.tick()
                if late:
                    self.assertEqual(0, ready)
                    self.assertNotEqual(target, self.next_move(changed).target_ns)
                else:
                    self.assertEqual((1,4,target), (ready,new.kind,new.target_ns))
                    self.assertEqual(50_000_000, new.not_before_ns-self.now)
                self.assertEqual(credit, self.credit())

    def test_goods_cancel_and_control_authority_preempt_observing_and_issued_states(self):
        for stage in ('observing','issued'):
            for fault in ('goods','cancel','foreground','locked','owner','phase'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine()
                    changed, old, retired, _, credit = self.withdraw()
                    if stage == 'issued': new = self.new_ticket(changed, old)
                    if fault == 'goods':
                        goods = deepcopy(changed); goods.goods = 'visible'
                        self.now += 4; self.observe_actual(self.scene(2,2,goods,beat=True))
                    elif fault == 'cancel': self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    elif fault == 'phase':
                        self.now += 4; frame = self.scene(2,2,changed,beat=True)
                        frame.beat_remaining = (frame.beat_remaining+.20)%1
                        self.observe_actual(frame); self.tick()
                    else:
                        flags = {'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]] = int(fault == 'locked')
                        self.tick(**flags)
                    if stage == 'issued':
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertNotEqual(4, self.tick()[1].kind)
                    self.assertEqual(credit, self.credit())
                    if fault != 'phase':
                        self.assertEqual({'goods':1,'cancel':2,'foreground':3,'locked':4,'owner':5}[fault],
                            self.status().reason)
                    elif stage == 'observing': self.assertEqual(0,self.status().beat_period_ns)
                    else: self.assertEqual(8,self.status().reason)
                    self.assertEqual(retired, bytes(next(e for e in self.events() if e.command.id == old.id)))

    def test_a_second_observed_open_cannot_start_another_recovery(self):
        changed, old, retired, _, _ = self.withdraw(second_gate=True)
        new = self.new_ticket(changed, old)
        self.ack(new); terrain = fixture.translated(changed,1); self.observed_result(new,terrain)
        entry = self.next_move(terrain)
        self.assertEqual((1,5,-1,0,1), self.choice(terrain))
        self.ack(entry); terrain = fixture.translated(terrain,1); self.observed_result(entry,terrain)
        following = self.next_move(terrain)
        passed = Entrance(1,self.status().x,self.status().y,1)
        self.assertEqual((1,6,-1,0,4), self.choice(terrain, passed))
        credit = self.credit(); previous = self.recovery().post_move_reacquisitions
        opened = self.opened(terrain)
        self.assertEqual((4,0,0), self.motion(terrain,opened,1))
        self.now += 4; self.observe_actual(self.scene(2,2,opened,beat=True))
        self.assertEqual((17,previous,credit), (self.status().reason,
            self.recovery().post_move_reacquisitions,self.credit()))
        self.assertEqual((3,0), (self.events()[-1].outcome,self.events()[-1].begin_ns))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,following.id,following.not_before_ns,1,0,1))
        self.assertEqual(retired, bytes(next(e for e in self.events() if e.command.id == old.id)))


if __name__ == '__main__':
    unittest.main()
