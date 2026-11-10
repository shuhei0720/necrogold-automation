"""TEST067: one bounded fresh-beat attempt after a proven stationary gate input.

TEST066's first run reported BLOCKED for an observed FLOOR gold bracket. Its
post-input PNG125 is absent, so these public-C procedural sequences test the
limited recovery contract, not whether that device input missed or opened a
previously misclassified dark door. UNKNOWN input is never replayed.
"""
import ctypes as C
from copy import deepcopy
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


class NativeBlocked067Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)

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
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate

    def armed_floor_gate(self, direction=1, distance=2, goods='unknown'):
        tiles = {(0,-n):'floor' for n in range(distance+2)}
        tiles.update({(-1,-distance):'gold',(1,-distance):'gold',(6,3):'stone'})
        rotate = {1:lambda x,y:(y,-x),2:lambda x,y:(-y,x),
                  3:lambda x,y:(x,y),4:lambda x,y:(-x,-y)}[direction]
        terrain = fixture.textured({rotate(x,y):k for (x,y),k in tiles.items()})
        self.fit(terrain); first = self.next_move()
        self.assertEqual(direction,first.direction)
        self.ack(first); terrain = fixture.translated(terrain,direction)
        terrain.goods=goods
        self.observed_result(first,terrain)
        self.verified_ns=self.now
        self.assertEqual((1,1,1,0),(self.status().inputs,self.status().moves,
            self.status().lead_confirmed,self.status().reason))
        command=self.next_move(terrain)
        self.assertEqual(direction,command.direction)
        if distance==2:
            frame=self.scene(2,2,terrain,beat=True);s=self.status()
            visits=(C.c_uint16*1089)();visits[16*33+16]=1
            dx,dy=fixture.DIRS[direction];visits[(dy+16)*33+dx+16]=1
            choice=Decision()
            self.assertEqual(1,self.lib.ng2_choose(C.byref(frame),s.x,s.y,visits,
                len(visits),C.byref(Entrance()),C.byref(choice)))
            self.assertEqual((direction,5,dx,dy,1),tuple(getattr(choice,k) for k,_ in choice._fields_))
        return terrain,command

    def credit(self):
        s=self.status()
        return (s.moves,s.door_changes,s.terrain_changes,s.x,s.y,s.lead_ns,
            s.lead_confirmed,s.first_move_ns,s.last_ordinal)

    def known_blocked(self,terrain,command):
        original_period=self.status().beat_period_ns
        self.ack(command); credit=self.credit()
        self.observed_result(command,terrain)
        self.assertEqual((0,0,0,credit),(self.status().reason,self.status().terminal,
            self.status().input_state,self.credit()),
            'a single proven stationary FLOOR gate may reacquire without claiming progress')
        e=self.events()[-1]
        self.assertEqual((2,2,0,0),(e.outcome,e.motion,e.dx,e.dy))
        self.assertEqual(bytes(command),bytes(e.command))
        self.assertEqual((command.id,0),(self.status().last_completed_id,self.status().current_command_id))
        self.assertEqual((0,0),(self.status().next_target_ns,self.status().beat_period_ns))
        self.assertEqual(0,self.motion_wait().active)
        r=self.recovery();index=min(r.record_count-1,1);latest=r.records[index]
        self.assertEqual((2,1,6,3),(r.mode,r.post_move_reacquisitions,latest.reason,latest.clock),
            'snapshot the stationary recovery at actual commit before retiring its HUD model')
        self.assertEqual((self.now,self.number,command.id),
            (latest.at_ns,latest.capture_id,latest.command_id))
        self.assertEqual(original_period,latest.model.period_ns,
            'the trace must retain the model retired for fresh fitting')
        self.assertGreaterEqual(latest.model.sample_count,4)
        samples=self.recovery_samples(index)
        self.assertEqual(latest.sample_count,len(samples))
        self.assertGreaterEqual(len(samples),4)
        self.assertLess(samples[0].start_ns,command.source_start_ns,
            'retain the original HUD sample span, not just the stationary proof image')
        self.assertEqual(self.now-1,samples[-1].midpoint_ns)
        self.assertEqual(self.verified_ns+12*SECOND,latest.sync_deadline_ns,
            'BLOCKED must not reset the previous verified-progress epoch')
        snapshot=bytes(r);raw=tuple(bytes(sample) for sample in samples)
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(snapshot,bytes(self.recovery()),
            'the first actual tick must preserve the pre-clear snapshot without a duplicate record')
        self.assertEqual(raw,tuple(bytes(sample) for sample in self.recovery_samples(index)))
        return bytes(e),latest.sync_deadline_ns

    def new_attempt(self,terrain,old):
        # Under two seconds of fresh HUD cannot revive the retired model.
        for _ in range(18):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
            self.assertNotEqual(4,self.tick()[1].kind)
            self.assertEqual(0,self.status().beat_period_ns)
        for _ in range(9):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual(PERIOD,self.status().beat_period_ns)
        new=self.next_move(terrain)
        self.assertGreater(new.id,old.id)
        self.assertGreater(new.target_ns,old.target_ns)
        self.assertEqual((old.ordinal,old.direction),(new.ordinal,new.direction))
        self.assertGreater(new.source_capture_id,old.source_capture_id)
        self.assertGreaterEqual(new.not_before_ns-self.now,50_000_000)
        return new

    def test_floor_gate_blocked_reacquires_once_in_four_directions_without_progress_credit(self):
        for direction in (1,2,3,4):
            with self.subTest(direction=direction):
                self.fresh_engine();terrain,old=self.armed_floor_gate(direction)
                retired,_=self.known_blocked(terrain,old)
                self.reject_old_callbacks_without_mutation(old)
                new=self.new_attempt(terrain,old)
                self.assertEqual(retired,bytes(self.events()[-2]))
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new);self.observed_result(new,fixture.translated(terrain,direction))
                self.assertEqual((3,2,0,0),(self.status().inputs,self.status().moves,
                    self.status().door_changes,self.status().reason))
                self.assertEqual(retired,bytes(self.events()[-2]))

    def test_second_stationary_attempt_stops_and_cannot_receive_another_retry(self):
        terrain,old=self.armed_floor_gate()
        retired,_=self.known_blocked(terrain,old);new=self.new_attempt(terrain,old)
        credit=self.credit();self.ack(new);self.observed_result(new,terrain)
        self.assertEqual((10,3,credit),(self.status().reason,self.status().inputs,self.credit()))
        self.assertEqual((2,2),(self.events()[-1].outcome,self.events()[-1].motion))
        self.assertEqual(retired,bytes(self.events()[-2]))
        for _ in range(3):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
            self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(3,len([e for e in self.events() if e.command.kind==4 and e.outcome==2]))

    def test_changed_gate_goods_or_local_proof_cannot_gain_stationary_retry(self):
        for fault in ('non_gate','partial_before','partial_after','origin','next_dirt','next_door',
                      'bracket','remote_gold','protected','local','signature'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,old=self.armed_floor_gate(distance=3 if fault=='non_gate' else 2,
                    goods='partial' if fault=='partial_before' else 'unknown')
                self.ack(old);changed=deepcopy(terrain)
                if fault=='partial_after':changed.goods='partial'
                elif fault=='partial_before':changed.goods='unknown'
                elif fault=='origin':changed.tiles[(0,0)]='stone'
                elif fault=='next_dirt':changed.tiles[(-1,0)]='dirt'
                elif fault=='next_door':changed.tiles[(-1,0)]='door'
                elif fault=='bracket':changed.tiles[(-1,-1)]='stone'
                elif fault=='remote_gold':changed.tiles[(8,3)]='gold'
                elif fault=='protected':changed.protected.add((8,3))
                elif fault=='local':changed.tiles[(0,1)]='stone'
                elif fault=='signature':changed.signature=bytes([40])*23296
                self.observed_result(old,changed)
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual((2,1,0),(self.status().inputs,self.status().moves,self.status().door_changes))
                self.assertNotEqual(2,self.recovery().mode)
        # The known stationary result permits only the same observed entrance.
        # A later fresh HUD fit is not permission to issue a different action
        # or to ignore terrain/signature changes before its new ticket.
        for stage in ('fitting','publication'):
            for fault in ('remote_gold','remote_tile','next_dirt','protected','partial','candidate','signature'):
                with self.subTest(recovery_stage=stage,fault=fault):
                    self.fresh_engine();terrain,old=self.armed_floor_gate()
                    retired,_=self.known_blocked(terrain,old)
                    changed=deepcopy(terrain)
                    if fault=='remote_gold':changed.tiles[(8,3)]='gold'
                    elif fault=='remote_tile':changed.tiles[(8,3)]='stone'
                    elif fault=='next_dirt':changed.tiles[(-1,0)]='dirt'
                    elif fault=='protected':changed.protected.add((8,3))
                    elif fault=='partial':changed.goods='partial'
                    elif fault=='signature':changed.signature=bytes([40])*23296
                    for step in range(27):
                        self.now+=100_000_000
                        current=changed if stage=='fitting' else terrain
                        frame=self.scene(2,2,current,beat=True)
                        if fault=='candidate' and stage=='fitting':frame.gold_state=1
                        self.observe_actual(frame)
                        if stage=='fitting' or step<18:
                            self.assertNotEqual(4,self.tick()[1].kind,
                                'reacquiring HUD must not broaden the stationary entrance permission')
                    # Model acquisition has completed in the positive fixture.
                    # Present the changed Scene before selecting/publishing the
                    # new MOVE, including the 100ms publication boundary.
                    for _ in range(2):
                        self.now+=2
                        frame=self.scene(2,2,changed,beat=True)
                        if fault=='candidate':frame.gold_state=1
                        self.observe_actual(frame)
                        self.assertNotEqual(4,self.tick()[1].kind,
                            'the fresh ticket must reprove the original stationary entrance')
                        s=self.status()
                        if s.next_target_ns:
                            self.now=max(self.now,s.next_target_ns-s.lead_ns-100_000_000)
                    self.assertEqual((2,1,0),(self.status().inputs,self.status().moves,
                        self.status().door_changes))
                    self.assertEqual(retired,bytes(self.events()[1]))
        # A new ID still has not sent an input. Generic FRESH revalidation
        # must not turn this FLOOR-entrance permission into a DIRT action.
        for fault in ('next_dirt','signature'):
            with self.subTest(recovery_stage='issued',fault=fault):
                self.fresh_engine();terrain,old=self.armed_floor_gate()
                retired,_=self.known_blocked(terrain,old);new=self.new_attempt(terrain,old)
                changed=deepcopy(terrain);self.now+=2
                if fault=='next_dirt':changed.tiles[(-1,0)]='dirt'
                else:changed.signature=bytes([40])*23296
                self.observe_actual(self.scene(2,2,changed,beat=True))
                if fault=='signature':
                    # Signature-only drift has scene_change mask zero. The
                    # final input callback may run before another tick.
                    self.now=max(self.now,new.not_before_ns)
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1),
                        'a signature-only invalidation must precede a pending final input callback')
                ready,cleanup=self.tick()
                self.assertEqual((1,2),(ready,cleanup.kind),
                    'retire the changed retry and preserve the normal holding PAUSE')
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                self.assertEqual((2,1,0),(self.status().inputs,self.status().moves,self.status().door_changes))
                self.assertEqual(retired,bytes(self.events()[1]))
                self.ack(cleanup);self.now+=2
                self.observe_actual(self.scene(1,2,changed))
                self.assertEqual((1,1,0,17,2,1),(self.status().terminal,self.status().paused,
                    self.status().input_state,self.status().reason,self.status().inputs,self.status().moves),
                    'withdrawn retry authority must not leak into PAUSE begin or its ACK confirmation')
        # Existing initial safe-floor tuning is still finite and separate:
        # no previous real move means this new gate recovery is ineligible.
        self.fresh_engine();terrain=self.fit();old=self.next_move();self.ack(old)
        self.observed_result(old,terrain)
        self.assertEqual((0,75_000_000,0,0),(self.status().reason,self.status().lead_ns,
            self.status().moves,self.recovery().post_move_reacquisitions))
        self.fresh_engine()
        terrain=fixture.textured({(0,0):'floor',(0,-1):'floor',(0,-2):'floor',
            (-1,-1):'gold',(1,-1):'gold'})
        self.fit(terrain);old=self.next_move();self.ack(old);self.observed_result(old,terrain)
        self.assertEqual((10,0,0),(self.status().reason,self.status().moves,
            self.recovery().post_move_reacquisitions))

    def test_matching_stable_ack_prefix_is_required_and_unknown_input_never_retries(self):
        for fault in ('unstable','wrong_prefix','inflight','unknown_synth','unknown_motion'):
            with self.subTest(fault=fault):
                self.fresh_engine();terrain,old=self.armed_floor_gate()
                if fault=='inflight':
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    self.now=old.target_ns+80_000_002
                    self.observe_actual(self.scene(2,2,terrain,beat=True))
                    self.assertEqual(2,self.status().input_state)
                elif fault=='unknown_synth':
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    self.now+=50_000_000
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,-1))
                    self.now=old.target_ns+80_000_002
                    self.observe_actual(self.scene(2,2,terrain,beat=True))
                    self.assertEqual((4,11),(self.status().input_state,self.status().reason))
                elif fault=='unknown_motion':
                    self.ack(old);unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
                    for offset in (80_000_002,210_000_004,730_000_006):
                        self.now=old.target_ns+offset
                        self.observe_actual(self.scene(2,2,unknown,beat=True))
                    self.assertEqual((10,0),(self.status().reason,self.status().input_state))
                else:
                    self.ack(old);self.now=old.target_ns+80_000_002
                    self.observe_actual(self.scene(2,2,terrain,beat=True),stable=int(fault!='unstable'),
                        prefix=old.id-1 if fault=='wrong_prefix' else old.id)
                    self.assertEqual(3,self.status().input_state)
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual((1 if fault=='inflight' else 2,1),(self.status().inputs,self.status().moves))

    def test_actual_visual_deadline_and_previous_verified_sync_budget_are_not_extended(self):
        for late in (0,1):
            with self.subTest(bound='visual',late=late):
                self.fresh_engine();terrain,old=self.armed_floor_gate();self.ack(old)
                deadline=self.motion_wait().deadline_ns;self.now=deadline-1_000_000
                self.observe_actual(self.scene(2,2,terrain,beat=False),commit=deadline+late)
                if late:
                    self.assertEqual((9,0),(self.status().reason,self.recovery().post_move_reacquisitions))
                else:
                    self.assertEqual(0,self.status().reason)
                    self.now=deadline;self.assertNotEqual(4,self.tick()[1].kind)
                    self.assertEqual(self.verified_ns+12*SECOND,self.recovery().records[0].sync_deadline_ns)
        for late in (0,1):
            with self.subTest(bound='sync',late=late):
                self.fresh_engine();terrain,old=self.armed_floor_gate()
                _,deadline=self.known_blocked(terrain,old)
                self.now=deadline-1_000_000
                self.observe_actual(self.scene(2,2,terrain,beat=False));self.tick()
                self.assertEqual(0,self.status().reason)
                self.now=deadline+late
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual((8,2,1),(self.status().reason,self.status().inputs,self.status().moves))

    def test_goods_cancel_and_control_guards_preempt_recovery_or_its_new_ticket(self):
        for stage in ('recovery','new_ticket'):
            for fault in ('goods','cancel','foreground','locked','owner'):
                with self.subTest(stage=stage,fault=fault):
                    self.fresh_engine();terrain,old=self.armed_floor_gate()
                    self.known_blocked(terrain,old)
                    if stage=='new_ticket':new=self.new_attempt(terrain,old)
                    if fault=='goods':
                        changed=deepcopy(terrain);changed.goods='visible';self.now+=2
                        self.observe_actual(self.scene(2,2,changed,beat=True))
                    elif fault=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    else:
                        flags={'front':1,'locked':0,'owner':1}
                        flags[{'foreground':'front','locked':'locked','owner':'owner'}[fault]]=0 if fault!='locked' else 1
                        self.assertNotEqual(4,self.tick(**flags)[1].kind)
                    if stage=='new_ticket':
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
                    self.assertNotEqual(4,self.tick()[1].kind)
                    self.assertEqual((2,1,0),(self.status().inputs,self.status().moves,self.status().door_changes))
                    self.assertEqual({'goods':1,'cancel':2,'foreground':3,'locked':4,'owner':5}[fault],self.status().reason)
