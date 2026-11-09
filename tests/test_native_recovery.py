"""TEST061 recovery contracts with the real C core and explicit host clocks.

Procedural textures and timestamps establish controller semantics; they do not
stand in for missing TEST060 device images or iPhone acceptance.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests.test_native_beat import NativeModel, NativeSample

CORE=fixture.CORE
SECOND=fixture.SECOND
PERIOD=fixture.PERIOD
Scene=fixture.Scene
Command=fixture.Command
Status=fixture.Status
Event=fixture.Event
MotionWait=fixture.MotionWait
textured=fixture.textured
translated=fixture.translated


class RecoveryTrace(C.Structure):
    _fields_=[*[(name,C.c_uint64) for name in (
        'sequence','episode_id','at_ns','capture_id','command_id',
        'abandoned_target_ns','sync_deadline_ns')],
        ('model',NativeModel),*[(name,C.c_int32) for name in ('reason','clock','sample_count')]]


class RecoveryStatus(C.Structure):
    _fields_=[*[(name,C.c_uint64) for name in (
        'initial_reacquisitions','post_move_reacquisitions','episode_id',
        'schedule_deadline_ns','visual_deadline_ns','ack_ns','record_count','dropped_records')],
        ('mode',C.c_int32),('records',RecoveryTrace*2)]


class NativeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        directory=Path(cls.temp.name)
        common=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',
                '-fPIC','-fno-fast-math','-ffp-contract=off']
        objects=[]
        for name in ('NG2Controller','NG2Beat','NG2Navigation','NG2Perception'):
            obj=directory/(name+'.o')
            profile='-O0' if name in ('NG2Controller','NG2Beat') else '-O2'
            subprocess.run([*common,profile,'-c',str(CORE/(name+'.c')),'-o',str(obj)],check=True)
            objects.append(str(obj))
        library=directory/'recovery.so'
        subprocess.run(['cc','-shared',*objects,'-lm','-o',str(library)],check=True)
        cls.lib=C.CDLL(str(library));l=cls.lib
        l.ng2_controller_create.argtypes=[C.c_uint64];l.ng2_controller_create.restype=C.c_void_p
        l.ng2_controller_destroy.argtypes=[C.c_void_p]
        l.ng2_controller_observe.argtypes=[C.c_void_p,C.POINTER(Scene),C.c_uint64,C.c_uint64,C.c_uint64,C.c_uint64,C.c_int32]
        l.ng2_controller_tick.argtypes=[C.c_void_p,C.c_uint64,C.c_int32,C.c_int32,C.c_int32,C.POINTER(Command)]
        l.ng2_controller_begin.argtypes=[C.c_void_p,C.c_uint64,C.c_uint64,C.c_int32,C.c_int32,C.c_int32]
        l.ng2_controller_complete.argtypes=[C.c_void_p,C.c_uint64,C.c_uint64,C.c_int32]
        l.ng2_controller_cancel.argtypes=[C.c_void_p,C.c_uint64,C.c_int32]
        l.ng2_controller_status.argtypes=[C.c_void_p,C.POINTER(Status)]
        l.ng2_controller_events.argtypes=[C.c_void_p,C.POINTER(Event),C.c_size_t]
        l.ng2_controller_events.restype=C.c_size_t
        l.ng2_controller_motion_wait.argtypes=[C.c_void_p,C.POINTER(MotionWait)]
        # The semantic Red tests above intentionally use only the old API.
        # New API tests bind when the implementation provides its symbols.
        if hasattr(l,'ng2_controller_recovery_status'):
            l.ng2_controller_recovery_status.argtypes=[C.c_void_p,C.POINTER(RecoveryStatus)]
            l.ng2_controller_recovery_samples.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(NativeSample),C.c_size_t]
            l.ng2_controller_recovery_samples.restype=C.c_size_t
            l.ng2_controller_observe_at.argtypes=[*l.ng2_controller_observe.argtypes,C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    # Reuse fixture mechanics, without inheriting its unrelated test methods.
    setUp=fixture.NativeControllerTests.setUp
    scene=fixture.NativeControllerTests.scene
    observe=fixture.NativeControllerTests.observe
    tick=fixture.NativeControllerTests.tick
    status=fixture.NativeControllerTests.status
    events=fixture.NativeControllerTests.events
    motion_wait=fixture.NativeControllerTests.motion_wait
    ack=fixture.NativeControllerTests.ack
    fit=fixture.NativeControllerTests.fit
    next_move=fixture.NativeControllerTests.next_move
    publish_procedural_candidate=fixture.NativeControllerTests.publish_procedural_candidate
    armed_initial=fixture.NativeControllerTests.armed_initial
    fresh_engine=fixture.NativeControllerTests.fresh_engine
    observed_result=fixture.NativeControllerTests.observed_result
    initial_scene_change=fixture.NativeControllerTests.initial_scene_change
    scene_changes=fixture.NativeControllerTests.scene_changes
    scene_details=fixture.NativeControllerTests.scene_details

    def recovery(self):
        out=RecoveryStatus();self.lib.ng2_controller_recovery_status(self.engine,C.byref(out));return out

    def recovery_samples(self,index):
        out=(NativeSample*13)()
        count=self.lib.ng2_controller_recovery_samples(self.engine,index,out,13)
        return list(out)[:count]

    def observe_actual(self,scene,commit=None,start=None,end=None,prefix=None,stable=1):
        self.number+=1
        return self.lib.ng2_controller_observe_at(self.engine,C.byref(scene),self.number,
            self.now-2 if start is None else start,self.now if end is None else end,
            self.prefix if prefix is None else prefix,stable,self.now if commit is None else commit)

    def all_public_bytes(self):
        return (bytes(self.status()),b''.join(bytes(e) for e in self.events()),
                bytes(self.recovery()),tuple(tuple(bytes(s) for s in self.recovery_samples(i)) for i in range(2)))

    def reject_old_callbacks_without_mutation(self,old):
        before=self.all_public_bytes()
        # Even a future old callback may not advance C's known clock/budget.
        future=self.now+30*SECOND
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,future,1,0,1))
        for outcome in (-1,0,1):
            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,future,outcome))
        self.assertEqual(before,self.all_public_bytes())

    def first_operation(self,kind):
        if kind in ('moved','blocked'):
            before=self.fit();command=self.next_move()
            after=translated(before,command.direction) if kind=='moved' else before
        else:
            obstacle='door' if kind=='door' else 'dirt'
            before=textured({(0,0):'floor',(0,-1):obstacle,(-1,-1):'gold',
                             (1,-1):'gold',(0,-2):'floor'})
            self.fit(before);command=self.next_move();after=deepcopy(before)
            after.tiles[(0,-1)]='floor'
        self.ack(command)
        return before,after,command

    def schedule_deadline(self,command):
        return command.target_ns+PERIOD-self.status().lead_ns+10_000_000

    def test_known_ack_survives_schedule_deadline_without_resend(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
        self.observed_result(command,unknown)
        self.assertEqual((3,1,0),(self.status().input_state,self.motion_wait().attempts,self.status().moves))
        self.now=self.schedule_deadline(command)+1
        ready,next_command=self.tick()
        self.assertEqual((0,0,3,0),(ready,next_command.kind,self.status().input_state,self.status().reason),
                         'known ACK visual wait must survive an unissued next beat')
        self.assertEqual(command.id,self.status().current_command_id)
        self.assertEqual(1,len(self.events()))

    def test_unissued_initial_preparation_miss_retires_without_fatal_stop(self):
        _,not_before=self.armed_initial()
        self.now=not_before-49_999_999
        self.assertEqual(0,self.tick()[0])
        s=self.status()
        self.assertEqual((0,0,0,4,0),(s.reason,s.terminal,s.input_state,s.phase,s.next_target_ns),
                         'definitely unsent initial candidate must reacquire inside its original sync budget')
        self.assertEqual([],self.events())

    def test_late_real_move_enters_reacquisition_without_old_next_beat(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        self.now=self.schedule_deadline(command)+1
        self.observe(self.scene(2,2,translated(terrain,command.direction),beat=True))
        s=self.status()
        self.assertEqual((1,1,0,0),(s.inputs,s.moves,s.input_state,s.reason),
                         'real proof after schedule D remains eligible inside frozen visual D')
        ready,next_command=self.tick()
        self.assertNotEqual(4,next_command.kind)
        self.assertEqual(0,self.status().reason)
        self.assertEqual(1,len(self.events()))

    def test_additive_queries_preserve_layout_and_initial_zeroes(self):
        self.assertEqual((192,456,120,56),(C.sizeof(RecoveryTrace),C.sizeof(RecoveryStatus),
                                        C.sizeof(NativeModel),C.sizeof(NativeSample)))
        self.assertEqual((192,128,23864,48),tuple(C.sizeof(t) for t in (Status,Event,Scene,MotionWait)))
        self.assertEqual(bytes(RecoveryStatus()),bytes(self.recovery()))
        self.assertEqual([],self.recovery_samples(0));self.assertEqual([],self.recovery_samples(1))
        out=RecoveryStatus();C.memset(C.byref(out),0xa5,C.sizeof(out))
        self.lib.ng2_controller_recovery_status(None,C.byref(out))
        self.assertEqual(bytes(RecoveryStatus()),bytes(out))

    def test_visual_and_schedule_deadlines_freeze_across_initial_reissue(self):
        _,_,old,new=self.initial_scene_change()
        r=self.recovery()
        expected=min(old.source_start_ns+3*SECOND,old.phase_sample_ns+3*SECOND,
                     self.status().walk_started_ns+45*SECOND,self.status().started_ns+180*SECOND)
        self.assertEqual(self.schedule_deadline(old),r.schedule_deadline_ns)
        self.assertEqual(expected,r.visual_deadline_ns)
        self.assertEqual(expected,self.motion_wait().deadline_ns)
        self.assertGreater(r.visual_deadline_ns,r.schedule_deadline_ns)
        self.ack(new)
        self.assertEqual(self.now,self.recovery().ack_ns)
        self.assertEqual((expected,r.schedule_deadline_ns),
                         (self.recovery().visual_deadline_ns,self.recovery().schedule_deadline_ns))

    def test_expired_unsent_complete_zero_retires_and_all_old_callbacks_are_inert(self):
        terrain=self.fit();old=self.next_move();old_bytes=bytes(old)
        self.now=old.deadline_ns+1
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,old.id,self.now,0))
        r=self.recovery();s=self.status()
        self.assertEqual((0,0,0,4,0),(s.reason,s.terminal,s.input_state,s.phase,s.current_command_id))
        self.assertEqual((1,1,1),(r.mode,r.initial_reacquisitions,r.record_count))
        trace=r.records[0]
        self.assertEqual((5,2,old.id,old.target_ns),(trace.reason,trace.clock,trace.command_id,trace.abandoned_target_ns))
        self.assertEqual((3,0,old_bytes),(self.events()[-1].outcome,self.events()[-1].begin_ns,
                                        bytes(self.events()[-1].command)))
        self.reject_old_callbacks_without_mutation(old)
        for n in range(27):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
            if n==2:self.reject_old_callbacks_without_mutation(old)
        new=self.next_move();self.assertGreater(new.id,old.id);self.assertGreater(new.target_ns,old.target_ns)
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new);self.reject_old_callbacks_without_mutation(old)
        self.assertEqual(1,self.status().inputs)

    def test_unsent_complete_zero_inside_window_remains_failure(self):
        self.fit();command=self.next_move()
        self.now=command.deadline_ns
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,0))
        self.assertEqual((6,0),(self.status().reason,self.recovery().initial_reacquisitions))
        self.assertEqual(3,self.events()[-1].outcome)

    def test_initial_sync_budget_equality_and_late_callbacks_do_not_restart_it(self):
        for entry in ('tick','begin','complete'):
            for late in (0,1):
                with self.subTest(entry=entry,late=late):
                    self.fresh_engine();self.fit();command=self.next_move()
                    deadline=self.status().walk_started_ns+12*SECOND
                    self.now=deadline+late
                    if entry=='tick':self.tick()
                    elif entry=='begin':self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1)
                    else:self.lib.ng2_controller_complete(self.engine,command.id,self.now,0)
                    self.assertEqual(8,self.status().reason)
                    self.assertEqual((0,0),(self.status().inputs,self.recovery().initial_reacquisitions))
                    self.assertNotEqual(4,self.tick()[1].kind)

    def test_unknown_synth_never_enters_visual_or_recovery(self):
        self.fit();command=self.next_move();self.now=command.not_before_ns
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.now+=300_000_000
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,-1))
        self.assertEqual((1,11,4,0),(self.status().terminal,self.status().reason,
                                    self.status().input_state,self.motion_wait().active))
        self.assertEqual((0,0,0),(self.recovery().mode,self.recovery().initial_reacquisitions,
                                  self.recovery().post_move_reacquisitions))
        self.now+=SECOND;self.observe_actual(self.scene(2,2,textured(),beat=True))
        self.assertEqual(0,self.tick()[0]);self.assertEqual(1,len(self.events()))

    def test_three_unknown_results_keep_one_command_and_fixed_visual_budget(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        deadline=self.motion_wait().deadline_ns
        unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
        for attempt in range(3):
            self.now=self.schedule_deadline(command)+10_000_000*(attempt+1)
            self.observe_actual(self.scene(2,2,unknown,beat=False))
            self.assertEqual((attempt+1,deadline),(self.motion_wait().attempts,self.motion_wait().deadline_ns))
        self.assertEqual((10,0,0),(self.status().reason,self.status().moves,self.motion_wait().active))
        self.assertEqual((0,1),(self.recovery().post_move_reacquisitions,len(self.events())))
        self.now+=10_000_000;self.observe_actual(self.scene(2,2,translated(terrain,command.direction),beat=True))
        self.assertEqual((0,3),(self.status().moves,self.motion_wait().attempts))

    def test_ack_phase_failure_does_not_end_visual_confirmation(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
        self.now=command.target_ns+100_000_000
        frame=self.scene(2,2,unknown,beat=True);frame.beat_remaining=(frame.beat_remaining+.20)%1
        self.observe_actual(frame)
        self.assertEqual((0,3,0),(self.status().reason,self.status().input_state,self.status().moves))
        self.assertGreater(self.recovery().record_count,0)
        self.now+=100_000_000
        self.observe_actual(self.scene(2,2,translated(terrain,command.direction),beat=False))
        self.assertEqual((1,0,0),(self.status().moves,self.status().input_state,self.status().reason))
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(2,self.recovery().mode)
        self.assertEqual(0,self.status().next_target_ns)

    def test_valid_old_model_without_proof_hud_waits_for_later_adopted_hud(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction)
        self.now=self.schedule_deadline(command)+1
        frame=self.scene(2,2,after,beat=True)
        frame.beat_remaining=1.0  # beat_valid alone does not prove sample adoption.
        self.observe_actual(frame)
        self.assertEqual(1,self.status().moves)
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(0,self.status().next_target_ns)
        self.now+=20_000_000;self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
        self.assertGreater(self.status().next_target_ns,command.target_ns+PERIOD)
        self.assertEqual(0,self.status().reason)

    def test_adopted_proof_hud_selects_new_slot_without_two_second_fit_delay(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        self.now=self.schedule_deadline(command)+1
        self.observe_actual(self.scene(2,2,translated(terrain,command.direction),beat=True))
        proof_commit=self.now;self.tick();s=self.status()
        self.assertGreater(s.next_target_ns,command.target_ns+PERIOD)
        self.assertGreaterEqual(s.next_target_ns-s.lead_ns-proof_commit,50_000_000)
        self.assertEqual((0,1),(s.reason,self.recovery().post_move_reacquisitions))

    def test_same_observation_phase_failure_and_move_requires_new_hud_fit(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction)
        self.now=command.target_ns+100_000_000
        frame=self.scene(2,2,after,beat=True);frame.beat_remaining=(frame.beat_remaining+.20)%1
        self.observe_actual(frame)
        self.assertEqual((1,1,0),(self.status().inputs,self.status().moves,self.status().reason))
        r=self.recovery();first_record=bytes(r.records[0]);first_samples=tuple(bytes(s) for s in self.recovery_samples(0))
        self.assertEqual((7,1,self.number),(r.records[0].reason,r.records[0].clock,r.records[0].capture_id))
        self.tick()
        self.assertEqual((0,0,2),(self.status().beat_period_ns,self.status().next_target_ns,self.recovery().mode))
        for _ in range(20):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,after,beat=True))
            self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(0,self.status().beat_period_ns)
        for _ in range(7):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,after,beat=True))
        self.assertEqual(PERIOD,self.status().beat_period_ns)
        self.assertEqual(first_record,bytes(self.recovery().records[0]))
        self.assertEqual(first_samples,tuple(bytes(s) for s in self.recovery_samples(0)))
        self.assertEqual((1,1),(self.status().inputs,self.status().moves))

    def test_initial_replan_budget_survives_unsent_retirement_and_refit(self):
        terrain=self.fit();command=self.next_move()
        for count,cell in enumerate(((-10,4),(-9,4)),1):
            terrain=deepcopy(terrain);terrain.tiles[cell]='stone';self.now+=2
            self.observe_actual(self.scene(2,2,terrain,beat=True));command=self.next_move()
            self.assertEqual((count,1),(self.scene_changes()[-1].replan_count,self.scene_changes()[-1].replan_allowed))
        self.now=command.deadline_ns+1
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,0))
        for _ in range(27):
            self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
        new=self.next_move();terrain=deepcopy(terrain);terrain.tiles[(-8,4)]='stone';self.now+=2
        self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual((2,0),(self.scene_changes()[-1].replan_count,self.scene_changes()[-1].replan_allowed))
        self.assertEqual((17,0,0),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual((new.id,3),(self.events()[-1].command.id,self.events()[-1].outcome))

    def test_actual_commit_after_visual_deadline_rejects_all_proof_branches(self):
        for kind in ('moved','door','dirt','blocked'):
            with self.subTest(kind=kind):
                self.fresh_engine();_,after,_=self.first_operation(kind)
                deadline=self.motion_wait().deadline_ns
                self.now=deadline-1_000_000
                frame=self.scene(2,2,after,beat=False)
                self.observe_actual(frame,commit=deadline+1_000_000)
                s=self.status()
                self.assertEqual((0,0,0,150_000_000),(s.moves,s.door_changes,s.terrain_changes,s.lead_ns))
                self.assertEqual((9,0),(s.reason,self.motion_wait().active))
                self.now=deadline+1_000_000
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))

    def test_actual_tick_after_visual_deadline_cannot_issue_from_any_proof(self):
        for kind in ('moved','door','dirt','blocked'):
            with self.subTest(kind=kind):
                self.fresh_engine();_,after,_=self.first_operation(kind)
                deadline=self.motion_wait().deadline_ns
                self.now=deadline-1_000_000
                self.observe_actual(self.scene(2,2,after,beat=False))
                s=self.status()
                self.assertEqual((int(kind=='moved'),int(kind=='door'),int(kind=='dirt')),
                                 (s.moves,s.door_changes,s.terrain_changes))
                self.now=deadline+1
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(9,self.status().reason)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))

    def test_visual_deadline_commit_equality_and_one_ns_late_for_all_proofs(self):
        for kind in ('moved','door','dirt','blocked'):
            for late in (0,1):
                with self.subTest(kind=kind,late=late):
                    self.fresh_engine();_,after,_=self.first_operation(kind)
                    deadline=self.motion_wait().deadline_ns
                    self.now=deadline-1_000_000
                    self.observe_actual(self.scene(2,2,after,beat=False),commit=deadline+late)
                    s=self.status();allowed=not late
                    self.assertEqual((int(kind=='moved' and allowed),int(kind=='door' and allowed),
                                      int(kind=='dirt' and allowed)),(s.moves,s.door_changes,s.terrain_changes))
                    self.assertEqual(75_000_000 if kind=='blocked' and allowed else 150_000_000,s.lead_ns)
                    self.assertEqual(9 if late else 0,s.reason)

    def test_new_recovery_slot_preparation_fifty_ms_equality_and_one_ns_short(self):
        for remaining,allowed in ((50_000_000,True),(49_999_999,False)):
            with self.subTest(remaining=remaining):
                self.fresh_engine();terrain=self.fit();command=self.next_move();self.ack(command)
                after=translated(terrain,command.direction)
                self.now=self.schedule_deadline(command)+1
                self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
                target=self.status().next_target_ns
                self.assertGreater(target,command.target_ns+PERIOD)
                self.now=target-self.status().lead_ns-remaining
                self.observe_actual(self.scene(2,2,after,beat=True));ready,new=self.tick()
                if allowed:
                    self.assertEqual((1,4,target,command.ordinal+1),
                                     (ready,new.kind,new.target_ns,new.ordinal))
                    self.assertEqual(remaining,new.not_before_ns-self.now)
                else:
                    self.assertEqual((0,0,0,0),(ready,new.kind,self.status().next_target_ns,self.status().reason))
                    r=self.recovery();latest=r.records[min(r.record_count-1,1)]
                    self.assertEqual((4,target),(latest.reason,latest.abandoned_target_ns))
                    self.assertEqual(1,len(self.events()))

    def test_recovery_episode_twelve_second_budget_survives_candidate_retirements(self):
        for late in (0,1):
            with self.subTest(late=late):
                self.fresh_engine();terrain=self.fit();command=self.next_move();self.ack(command)
                after=translated(terrain,command.direction)
                self.now=self.schedule_deadline(command)+1
                self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
                r=self.recovery();episode=r.episode_id
                deadline=r.records[min(r.record_count-1,1)].sync_deadline_ns
                for _ in range(2):
                    target=self.status().next_target_ns
                    self.assertGreater(target,0)
                    self.now=target-self.status().lead_ns-49_999_999
                    self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
                    self.assertEqual(0,self.status().next_target_ns)
                    self.now+=10_000_000
                    self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
                    r=self.recovery()
                    self.assertEqual((episode,1),(r.episode_id,r.post_move_reacquisitions))
                    self.assertEqual(deadline,r.records[min(r.record_count-1,1)].sync_deadline_ns)
                self.now=deadline-1_000_000
                self.observe_actual(self.scene(2,2,after,beat=False));self.tick()
                self.assertEqual(0,self.status().reason)
                self.now=deadline+late;self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(8,self.status().reason)
                r=self.recovery();latest=r.records[min(r.record_count-1,1)]
                self.assertEqual((8,deadline,episode),(latest.reason,latest.sync_deadline_ns,r.episode_id))

    def test_post_move_recovery_reserved_before_budget_cannot_begin_after_budget(self,reissue=None):
        terrain=self.fit();old=self.next_move();self.ack(old)
        after=translated(terrain,old.direction)
        self.now=self.schedule_deadline(old)+400_000_000
        self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
        deadline=self.recovery().records[0].sync_deadline_ns;start=self.now
        # Keep a real tracked HUD current through this bounded episode. The
        # first selected candidate remains unsent and is explicitly retired.
        for n in range(1,30):
            self.now=start+n*400_000_000
            self.observe_actual(self.scene(2,2,after,beat=True))
        self.now=deadline-100_000_000
        self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
        self.now+=1_000_000
        self.observe_actual(self.scene(2,2,after,beat=True));self.tick()
        not_before=self.status().next_target_ns-self.status().lead_ns
        self.assertGreater(not_before,deadline)
        self.now=not_before-100_000_000
        self.observe_actual(self.scene(2,2,after,beat=True));ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind));self.assertLess(self.now,deadline)
        if reissue is not None:
            changed=deepcopy(after)
            changed.tiles[(-10,4)]='stone'
            if reissue=='fresh':changed.tiles[(0,-1)]='dirt'
            self.now+=2;self.observe_actual(self.scene(2,2,changed,beat=True))
            ready,replacement=self.tick();self.assertEqual((1,4),(ready,replacement.kind))
            self.assertGreater(replacement.id,new.id)
            self.assertEqual((new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal),
                             (replacement.target_ns,replacement.not_before_ns,replacement.deadline_ns,replacement.ordinal))
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
            new=replacement
        self.now=new.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1),
                         'a queued fresh ticket cannot escape its original recovery episode budget')
        self.assertEqual((8,1),(self.status().reason,self.status().inputs))

    def test_post_recovery_same_and_fresh_reissues_keep_original_episode_budget(self):
        for policy in ('same','fresh'):
            with self.subTest(policy=policy):
                self.fresh_engine()
                self.test_post_move_recovery_reserved_before_budget_cannot_begin_after_budget(reissue=policy)

    def test_retune_recovery_ticket_keeps_same_beat_alignment_after_publication(self):
        terrain=textured();period=515_000_000
        def observed(bias=0):
            scene=self.scene(2,2,terrain,beat=True)
            scene.beat_remaining=(((5*SECOND-(self.now-1))%period)/period+bias)%1
            self.observe_actual(scene)
        for _ in range(4):
            self.now+=700_000_000;observed()
        first=self.next_move();self.ack(first)
        self.now=first.target_ns+80_000_002;observed();self.tick()
        self.assertEqual((75_000_000,0),(self.status().lead_ns,self.status().lead_confirmed))
        self.now=self.status().next_target_ns-self.status().lead_ns-100_000_000
        observed();ready,retune=self.tick();self.assertEqual((1,4),(ready,retune.kind))
        # These small live HUD changes keep tracking valid while cumulatively
        # moving this issued physical beat beyond .08 of its original period.
        for bias in (.04,.07,.09,.11,.13,.15,.17):
            self.now+=2;observed(bias)
        self.assertGreater(self.status().beat_period_ns,period)
        self.now=retune.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,retune.id,self.now,1,0,1),
                         'retune is a new frozen ticket and must keep its original physical beat')
        self.assertEqual((8,1),(self.status().reason,self.status().inputs))

    def test_diagnostic_sync_deadline_is_clamped_at_signed_session_boundary(self):
        limit=1<<63;started=limit-180*SECOND-1
        self.engine=self.lib.ng2_controller_create(started)
        self.assertTrue(self.engine);self.addCleanup(self.lib.ng2_controller_destroy,self.engine)
        self.prefix=0;self.number=0;self.now=limit-8*SECOND
        terrain=textured()
        for _ in range(4):
            self.now+=700_000_000
            self.observe_actual(self.scene(2,2,terrain,beat=True))
        self.assertEqual(PERIOD,self.status().beat_period_ns)
        self.now+=2;bad=self.scene(2,2,terrain,beat=True)
        bad.beat_remaining=(bad.beat_remaining+.09)%1
        self.observe_actual(bad)
        record=self.recovery().records[0]
        self.assertEqual((1,1),(record.reason,record.clock))
        self.assertEqual(started+180*SECOND,record.sync_deadline_ns,
                         'diagnostic ns must remain within the actual session and signed native clock')
        self.assertLess(record.sync_deadline_ns,limit)

    def test_hud_failure_before_sync_deadline_committed_after_it_cannot_reacquire(self):
        terrain=self.fit();deadline=self.status().walk_started_ns+12*SECOND
        self.now=deadline-1_000_000
        bad=self.scene(2,2,terrain,beat=True);bad.beat_remaining=(bad.beat_remaining+.3)%1
        self.observe_actual(bad,commit=deadline+1_000_000)
        self.assertEqual((0,8),(self.recovery().initial_reacquisitions,self.status().reason),
                         'capture-end diagnostics cannot backdate the actual sync-budget entry gate')
        record=self.recovery().records[0]
        self.assertEqual((8,3,deadline+1_000_000),(record.reason,record.clock,record.at_ns))

    def test_goods_after_visual_deadline_are_held_without_move_credit(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        deadline=self.motion_wait().deadline_ns
        after=translated(terrain,command.direction);after.goods='visible'
        self.now=deadline-1_000_000
        self.observe_actual(self.scene(2,2,after,beat=False),commit=deadline+1_000_000)
        self.assertEqual((1,1,0,0),(self.status().goods,self.status().reason,
                                   self.status().moves,self.motion_wait().active))
        self.now=deadline+1_000_000
        ready,pause=self.tick();self.assertEqual((1,2),(ready,pause.kind))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))

    def test_invalid_actual_commit_interval_is_inert(self):
        self.fit();before=self.all_public_bytes()
        self.now+=10_000_000
        result=self.observe_actual(self.scene(2,2,textured(),beat=True),commit=self.now-1)
        self.assertIn(result,(-1,0));self.assertEqual(before,self.all_public_bytes())

    def test_started_or_cancelled_input_cannot_use_unsent_recovery(self):
        for state in ('started','unknown','cancelled'):
            with self.subTest(state=state):
                self.fresh_engine();self.fit();command=self.next_move();self.now=command.not_before_ns
                if state=='cancelled':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                else:
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
                    if state=='unknown':
                        self.now+=50_000_000
                        self.lib.ng2_controller_complete(self.engine,command.id,self.now,-1)
                self.now=command.deadline_ns+1
                self.lib.ng2_controller_complete(self.engine,command.id,self.now,0)
                self.assertEqual(0,self.recovery().initial_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)

    def test_recovery_samples_are_capacity_bounded_and_snapshots_survive_refit_and_pause(self):
        terrain,not_before=self.armed_initial()
        self.now=not_before-49_999_999;self.tick()
        initial=self.recovery()
        self.assertEqual((1,1),(initial.record_count,initial.records[0].sequence))
        self.assertEqual(bytes(RecoveryTrace()),bytes(initial.records[1]))
        first_record=bytes(initial.records[0]);first_samples=tuple(bytes(s) for s in self.recovery_samples(0))
        self.assertEqual(initial.records[0].sample_count,len(first_samples))
        self.assertGreater(len(first_samples),0);self.assertLessEqual(len(first_samples),13)
        self.assertEqual(PERIOD,initial.records[0].model.period_ns)
        for _ in range(2):
            for _ in range(27):
                self.now+=100_000_000;self.observe_actual(self.scene(2,2,terrain,beat=True))
            ready,command=self.tick()
            if ready:
                self.assertEqual(4,command.kind)
                self.now=command.deadline_ns+1
                self.lib.ng2_controller_complete(self.engine,command.id,self.now,0)
            else:
                self.assertGreater(self.status().next_target_ns,0)
                self.now=self.status().next_target_ns-self.status().lead_ns-49_999_999
                self.tick()
        record=self.recovery()
        self.assertGreaterEqual(record.record_count,3)
        self.assertEqual(record.record_count-2,record.dropped_records)
        self.assertEqual((1,record.record_count),(record.records[0].sequence,record.records[1].sequence))
        self.assertEqual(first_record,bytes(record.records[0]))
        self.assertEqual(first_samples,tuple(bytes(s) for s in self.recovery_samples(0)))
        query=self.lib.ng2_controller_recovery_samples
        for index in (0,1):
            snapshots=self.recovery_samples(index)
            for capacity in (0,1,13,14,C.c_size_t(-1).value):
                guarded=(NativeSample*15)();C.memset(C.byref(guarded),0xa5,C.sizeof(guarded))
                expected=min(capacity,len(snapshots))
                self.assertEqual(expected,query(self.engine,index,guarded,capacity))
                self.assertEqual(tuple(bytes(s) for s in snapshots[:expected]),
                                 tuple(bytes(s) for s in list(guarded)[:expected]))
                self.assertEqual(bytes([0xa5])*C.sizeof(NativeSample)*(15-expected),
                                 bytes(guarded)[expected*C.sizeof(NativeSample):])
        invalid=(NativeSample*1)();C.memset(C.byref(invalid),0xa5,C.sizeof(invalid))
        self.assertEqual(0,query(self.engine,2,invalid,13))
        self.assertEqual(bytes([0xa5])*C.sizeof(invalid),bytes(invalid))
        self.assertEqual(0,query(None,0,None,13))
        self.assertEqual(0,query(self.engine,0,None,13))
        goods=deepcopy(terrain);goods.goods='visible';self.now+=10_000_000
        self.observe_actual(self.scene(2,2,goods,beat=True));ready,pause=self.tick()
        self.assertEqual((1,2),(ready,pause.kind));self.ack(pause)
        self.now+=100_000_000;self.observe_actual(self.scene())
        self.assertEqual(1,self.status().terminal)
        self.assertEqual(first_record,bytes(self.recovery().records[0]))
        self.assertEqual(first_samples,tuple(bytes(s) for s in self.recovery_samples(0)))


if __name__=='__main__':
    unittest.main()
