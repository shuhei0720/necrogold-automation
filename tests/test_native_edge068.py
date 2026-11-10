"""TEST068: one observed-floor vantage for explicit below-grid gold evidence.

Procedural world coordinates outside the finite Scene grid are clipped before
the C call. A later synthetic unit translation may reveal them; this is not a
reconstruction of TEST067's unrecorded next game frame. Public APIs preserve
the original input windows, ACK/motion proof, prefix and whole-run budgets.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE
SECOND = fixture.SECOND
PERIOD = fixture.PERIOD


class Entrance(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('valid', 'x', 'y', 'direction')]


class Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


class NativeEdge068Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = Path(os.environ.get('NECRO_TEST068_EDGE_BASELINE', CORE))
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)

    setUp = mechanics.NativeRecoveryTests.setUp
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
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate

    def scene(self, state=1, gold=0, terrain=None, beat=False):
        out = fixture.NativeControllerTests.scene(self, state, gold, terrain, beat)
        if gold == 2 and getattr(terrain, 'edge_down', False):
            out.gold_state = 3  # Explicit EDGE_DOWN, never a hidden GOLD tile.
        return out

    def edge_terrain(self):
        terrain = fixture.textured({(0,y): 'floor' for y in range(5)})
        terrain.tiles.update({(-1,5): 'gold', (1,5): 'gold', (0,5): 'door',
                              (0,6): 'floor', (5,-2): 'stone'})
        terrain.gold = {(-1,5), (1,5)}
        terrain.edge_down = True
        return terrain

    def choice(self, frame, x=0, y=0, entrance=None):
        visits = (C.c_uint16*1089)();visits[16*33+16] = 1
        choice = Decision()
        ok = self.lib.ng2_choose(C.byref(frame), x, y, visits, len(visits),
                                C.byref(entrance or Entrance()), C.byref(choice))
        return ok, tuple(getattr(choice, key) for key,_ in choice._fields_)

    def armed_edge(self):
        terrain = self.edge_terrain()
        self.fit(terrain)
        command = self.next_move(terrain)
        self.assertEqual((4,4,1), (command.kind, command.direction, command.ordinal))
        self.assertEqual((0,0,0), (self.status().inputs,self.status().moves,self.status().lead_confirmed))
        self.assertGreaterEqual(command.not_before_ns-self.now, 50_000_000)
        self.assertLessEqual(command.deadline_ns-command.not_before_ns,10_000_000)
        return terrain, command

    def test_only_explicit_down_hint_can_choose_one_observed_floor_step(self):
        terrain = self.edge_terrain();frame = self.scene(2,2,terrain)
        self.assertEqual(0,sum(tile==2 for tile in frame.tiles))
        self.assertEqual((1,(4,9,0,1,1)),self.choice(frame),
            'below-grid evidence may select observed DOWN floor without inventing a gold tile')
        for gold in (0,1,2,4):
            with self.subTest(gold=gold):
                wrong = fixture.Scene.from_buffer_copy(bytes(frame));wrong.gold_state=gold
                self.assertNotEqual((1,(4,9,0,1,1)),self.choice(wrong))

    def test_down_hint_does_not_authorize_blockers_items_protection_or_other_origins(self):
        terrain=self.edge_terrain();frame=self.scene(2,2,terrain)
        for kind in (0,2,3,4,5,6):
            with self.subTest(next_tile=kind):
                changed=fixture.Scene.from_buffer_copy(bytes(frame))
                changed.tiles[(1+5)*23+11]=kind
                self.assertNotEqual((1,(4,9,0,1,1)),self.choice(changed))
        for fault in ('origin','partial','visible','protected_near','protected_far',
                      'x','y','entered','other_gold','unknown','pause'):
            with self.subTest(fault=fault):
                changed=fixture.Scene.from_buffer_copy(bytes(frame));x=y=0;entered=Entrance()
                if fault=='origin':changed.tiles[5*23+11]=3
                elif fault in ('partial','visible'):changed.goods=1 if fault=='partial' else 2
                elif fault.startswith('protected'):changed.protected_cells[5*23+11 if fault=='protected_near' else 0]=1
                elif fault=='x':x=1
                elif fault=='y':y=1
                elif fault=='entered':entered=Entrance(1,0,0,4)
                elif fault=='other_gold':changed.tiles[0]=2
                elif fault=='unknown':changed.state=0
                elif fault=='pause':changed.state=1
                ok,choice=self.choice(changed,x,y,entered)
                self.assertFalse(ok and choice[1]==9)

    def test_one_verified_edge_step_returns_to_normal_gold_route_but_never_repeats_hint(self):
        for reveal_gold in (True,False):
            with self.subTest(reveal_gold=reveal_gold):
                self.fresh_engine();terrain,command=self.armed_edge()
                frozen=bytes(self.events()[-1].command)
                self.ack(command)
                self.assertEqual((1,0),(self.status().inputs,self.status().moves))
                after=fixture.translated(terrain,4)
                if not reveal_gold:
                    for point in list(after.tiles):
                        if after.tiles[point]=='gold':after.tiles[point]='stone'
                    after.gold=set();after.edge_down=True
                self.observed_result(command,after)
                self.assertEqual((1,1,0,1,0,1),(self.status().inputs,self.status().moves,
                    self.status().door_changes,self.status().lead_confirmed,self.status().x,self.status().y))
                self.assertEqual((2,1,0,1),(self.events()[-1].outcome,self.events()[-1].motion,
                    self.events()[-1].dx,self.events()[-1].dy))
                self.assertEqual(frozen,bytes(self.events()[-1].command))
                self.reject_old_callbacks_without_mutation(command)
                if reveal_gold:
                    following=self.next_move(after)
                    self.assertEqual(4,following.direction)
                    self.assertGreater(following.id,command.id)
                    self.assertEqual(2,following.ordinal)
                    self.assertEqual(1,self.status().inputs)
                else:
                    for _ in range(3):
                        self.now+=100_000_000;self.observe(self.scene(2,2,after,True))
                        self.assertNotEqual(4,self.tick()[1].kind)
                    self.assertEqual(1,self.status().inputs)

    def test_unstarted_edge_deadline_can_refit_without_reusing_id_or_sync_budget(self):
        for first,clock in (('tick',2),('observe',3)):
            with self.subTest(first=first):
                self.fresh_engine();terrain,old=self.armed_edge();original=bytes(old)
                changed=deepcopy(terrain);changed.tiles[(-8,2)]='dirt';self.now+=2
                self.observe(self.scene(2,2,changed,True))
                self.assertEqual((0,old.id,1),(self.status().reason,self.status().current_command_id,
                    self.status().input_state),
                    'unchanged edge action survives only irrelevant, stationary remote palette drift')
                self.assertEqual(original,bytes(self.events()[-1].command))
                self.assertEqual(old.source_capture_id,self.events()[-1].command.source_capture_id)
                terrain=changed;self.now=old.deadline_ns+1
                if first=='observe':
                    self.assertEqual(1,self.observe_actual(self.scene(2,2,terrain,True)))
                else:
                    self.assertNotEqual(4,self.tick()[1].kind)
                status=self.status();recovery=self.recovery();retired=bytes(self.events()[-1])
                self.assertEqual((0,0,0,0),(status.reason,status.inputs,status.moves,status.current_command_id))
                self.assertEqual((3,9),(self.events()[-1].outcome,self.events()[-1].reason))
                self.assertEqual(original,bytes(self.events()[-1].command))
                self.assertEqual((1,1),(recovery.mode,recovery.initial_reacquisitions))
                self.assertEqual((5,clock,self.now),(recovery.records[0].reason,
                    recovery.records[0].clock,recovery.records[0].at_ns))
                original_deadline=recovery.records[0].sync_deadline_ns
                self.assertEqual(status.walk_started_ns+12*SECOND,original_deadline)
                self.reject_old_callbacks_without_mutation(old)
                for _ in range(27):
                    self.now+=100_000_000;self.observe(self.scene(2,2,terrain,True))
                new=self.next_move(terrain)
                self.assertGreater(new.id,old.id);self.assertGreater(new.target_ns,old.target_ns)
                self.assertEqual((1,4),(new.ordinal,new.direction))
                self.assertEqual(retired,bytes(self.events()[-2]))
                self.assertEqual(original_deadline,self.recovery().records[0].sync_deadline_ns)
                self.reject_old_callbacks_without_mutation(old)

    def test_edge_blocked_unknown_motion_or_unknown_synth_never_gets_another_input(self):
        for outcome in ('blocked','unknown_motion','unknown_synth'):
            with self.subTest(outcome=outcome):
                self.fresh_engine();terrain,command=self.armed_edge()
                if outcome=='unknown_synth':
                    self.now=command.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
                    self.now+=50_000_000
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,-1))
                else:
                    self.ack(command)
                    after=deepcopy(terrain)
                    if outcome=='unknown_motion':after.signature=bytes([40])*23296
                    offsets=([80_000_002+index*(PERIOD//10) for index in range(7)]+[80_000_002+PERIOD]
                        if outcome=='unknown_motion' else (80_000_002,150_000_004,730_000_006))
                    for index,offset in enumerate(offsets):
                        self.observed_result(command,after,offset=offset)
                        if outcome=='unknown_motion' and index<7:
                            self.assertEqual((index+1,3,0),(self.motion_wait().attempts,
                                self.status().input_state,self.status().reason))
                self.assertEqual((1,0,0,150_000_000),(self.status().inputs,self.status().moves,
                    self.status().lead_confirmed,self.status().lead_ns))
                self.assertIn(self.status().reason,(10,11))
                for _ in range(3):
                    self.now+=100_000_000;self.observe(self.scene(2,2,terrain,True))
                    self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4 and e.outcome in (1,2,4)]))

    def test_edge_authority_prefix_goods_control_and_visual_deadline_stay_frozen(self):
        for fault in ('unstable','prefix','edge_lost','next_dirt','protected','goods','owner','locked','foreground'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,command=self.armed_edge()
                saved=bytes(command);before=self.status().last_capture_id
                if fault in ('owner','locked','foreground'):
                    flags={'front':1,'locked':0,'owner':1};flags[fault if fault!='foreground' else 'front']=1 if fault=='locked' else 0
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,
                        flags['front'],flags['locked'],flags['owner']))
                    self.assertEqual({'owner':5,'locked':4,'foreground':3}[fault],self.status().reason)
                else:
                    self.now+=2;frame=self.scene(2,2,terrain,True)
                    if fault=='edge_lost':frame.gold_state=1
                    elif fault=='next_dirt':frame.tiles[(1+5)*23+11]=4
                    elif fault=='protected':frame.protected_cells[0]=1
                    elif fault=='goods':frame.goods=2
                    result=self.observe_actual(frame,stable=int(fault!='unstable'),
                        prefix=self.prefix+1 if fault=='prefix' else self.prefix)
                    if fault in ('unstable','prefix'):
                        self.assertEqual(0,result);self.assertEqual(before,self.status().last_capture_id)
                        self.assertEqual(saved,bytes(self.events()[-1].command))
                    else:
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
                        self.assertEqual(0,self.status().inputs)
                self.assertEqual(0,self.status().moves)
        for late in (0,1):
            with self.subTest(visual_commit_late=late):
                self.fresh_engine();terrain,command=self.armed_edge();self.ack(command)
                after=fixture.translated(terrain,4);deadline=self.motion_wait().deadline_ns
                self.now=deadline-1_000_000
                self.observe_actual(self.scene(2,2,after,False),commit=deadline+late)
                self.assertEqual((1-late,1),(self.status().moves,self.status().inputs))
                self.assertEqual(9 if late else 0,self.status().reason)
                self.assertEqual(bytes(command),bytes(self.events()[-1].command))
