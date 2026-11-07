"""NG-G2 public controller with real C beat/navigation/motion, native fake clock.

Known synthetic textures establish host transitions, not iPhone acceptance.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import os
import random
import subprocess
import tempfile
import unittest
from PIL import Image
from necroprobe import shop_navigation as nav

ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'patches/loopctrl/ngg2'
SECOND=1_000_000_000
PERIOD=520_000_000
class Scene(C.Structure):
    _fields_=[('abi_version',C.c_uint32),('struct_size',C.c_uint32),
        *[(k,C.c_int32) for k in ('state','restart_label','gold_state','gold_peak','goods')],
        ('tiles',C.c_uint8*230),('protected_cells',C.c_uint8*230),
        ('signature',C.c_uint8*23296),('fingerprint',C.c_uint8*48),('beat_valid',C.c_int32),
        ('beat_remaining',C.c_double),('beat_spacing',C.c_double),('beat_center',C.c_double)]
class Command(C.Structure):
    _fields_=[*[(k,C.c_uint64) for k in ('id','ordinal','target_ns','not_before_ns','deadline_ns',
                'source_capture_id','source_start_ns','phase_sample_ns')],
              *[(k,C.c_int32) for k in ('kind','direction','x','y')]]
class Status(C.Structure):
    _fields_=[('abi_version',C.c_uint32),('struct_size',C.c_uint32),
        *[(k,C.c_int32) for k in ('phase','reason','terminal','goods','paused','input_state',
                                 'inputs','moves','door_changes','terrain_changes','restarts','x','y','lead_confirmed')],
        *[(k,C.c_uint64) for k in ('started_ns','walk_started_ns','ended_ns','first_move_ns',
                                 'last_capture_id','last_capture_start_ns','last_capture_end_ns','last_completed_id',
                                 'current_command_id','last_ordinal','next_target_ns','lead_ns','capture_count',
                                 'accepted_frames','discarded_frames','beat_period_ns')]]
class Event(C.Structure):
    _fields_=[('command',Command),*[(k,C.c_uint64) for k in ('begin_ns','end_ns','observed_capture_id')],
              *[(k,C.c_int32) for k in ('outcome','reason','motion','dx','dy')]]
class SceneChange(C.Structure):
    _fields_=[*[(k,C.c_uint64) for k in ('command_id','source_capture_id','observed_capture_id','target_ns','deadline_ns')],
              *[(k,C.c_int32) for k in ('change_mask','changed_tiles','changed_protected','state_before','state_after',
                                      'goods_before','goods_after','replan_count','replan_allowed')]]
KINDS={'floor':1,'gold':2,'stone':3,'dirt':4,'door':5,'item':6}
DIRS={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}

def textured(tiles=None):
    if tiles is None:
        tiles={(0,0):'floor',(0,-1):'floor',(0,-2):'floor',(0,-3):'door',(-1,-3):'gold',(1,-3):'gold',
               (-4,-2):'stone',(5,1):'stone'}
    rng=random.Random(43043)
    return nav.Scene(dict(tiles),{p for p,k in tiles.items() if k=='gold'},'unknown',set(),
                     bytes(rng.randrange(20,100) for _ in range(23296)))

def translated(scene,direction,amount=9):
    dx,dy=DIRS[direction]
    image=Image.frombytes('L',(224,104),scene.signature)
    out=Image.new('L',image.size);out.paste(image,(-dx*amount,-dy*amount))
    tiles={(x-dx,y-dy):kind for (x,y),kind in scene.tiles.items()}
    return nav.Scene(tiles,{p for p,k in tiles.items() if k=='gold'},scene.goods,
                     {(x-dx,y-dy) for x,y in scene.protected},out.tobytes())

class NativeControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        library=Path(cls.temp.name)/'controller.so'
        cls.sources=[CORE/name for name in ('NG2Controller.c','NG2Perception.c','NG2Navigation.c','NG2Beat.c')]
        subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fPIC','-shared',
                        *map(str,cls.sources),'-lm','-o',str(library)],check=True)
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
        l.ng2_reason_name.argtypes=[C.c_int32];l.ng2_reason_name.restype=C.c_char_p
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.now=SECOND+100_000_000;self.number=0;self.prefix=0;self.engine=self.lib.ng2_controller_create(SECOND)
        self.assertTrue(self.engine);self.addCleanup(self.lib.ng2_controller_destroy,self.engine)
    def scene(self,state=1,gold=0,terrain=None,beat=False):
        s=Scene(abi_version=1,struct_size=C.sizeof(Scene),state=state,gold_state=gold,restart_label=1)
        s.tiles[5*23+11]=1
        if terrain:
            s.goods={'unknown':0,'partial':1,'visible':2}[terrain.goods]
            for (x,y),kind in terrain.tiles.items():
                if -11<=x<=11 and -5<=y<=4:s.tiles[(y+5)*23+x+11]=KINDS[kind]
            for x,y in terrain.protected:
                if -11<=x<=11 and -5<=y<=4:s.protected_cells[(y+5)*23+x+11]=1
            s.signature[:]=terrain.signature
        if beat:
            mid=self.now-1
            s.beat_valid=1;s.beat_remaining=((5*SECOND-mid)%PERIOD)/PERIOD
            s.beat_spacing=104.;s.beat_center=446.
        return s
    def observe(self,s,number=None,prefix=None,stable=1,start=None,end=None):
        self.number+=1
        return self.lib.ng2_controller_observe(self.engine,C.byref(s),self.number if number is None else number,
            self.now-2 if start is None else start,self.now if end is None else end,self.prefix if prefix is None else prefix,stable)
    def tick(self,front=1,locked=0,owner=1):
        c=Command();result=self.lib.ng2_controller_tick(self.engine,self.now,front,locked,owner,C.byref(c));return result,c
    def status(self):
        out=Status();self.lib.ng2_controller_status(self.engine,C.byref(out));return out
    def events(self):
        out=(Event*64)();n=self.lib.ng2_controller_events(self.engine,out,64);return list(out)[:n]
    def ack(self,command):
        self.now=max(self.now,command.not_before_ns)
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.now+=50_000_000
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,1));self.prefix=command.id
    def fit(self,terrain=None):
        terrain=terrain or textured()
        for _ in range(27):
            self.now+=100_000_000
            self.observe(self.scene(2,2,terrain,beat=True))
        self.assertEqual(PERIOD,self.status().beat_period_ns)
        return terrain
    def next_move(self):
        ready,c=self.tick();self.assertEqual((ready,c.kind),(1,4));return c
    def observed_result(self,command,terrain,offset=80_000_002):
        self.now=max(self.now+2,command.target_ns+offset)
        self.observe(self.scene(2,2,terrain,beat=True))
    def hold_goods(self,terrain):
        goods=deepcopy(terrain);goods.goods='visible'
        self.now+=100_000_000;self.observe(self.scene(2,2,goods,beat=True))
        ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2));self.ack(pause)
        self.now+=100_000_000;self.observe(self.scene())
        s=self.status();self.assertEqual((s.terminal,s.goods,s.paused,s.reason),(1,1,1,1))
    def fresh_engine(self):
        self.now=SECOND+100_000_000;self.number=0;self.prefix=0
        self.engine=self.lib.ng2_controller_create(SECOND)
        self.assertTrue(self.engine);self.addCleanup(self.lib.ng2_controller_destroy,self.engine)
    def scene_changes(self):
        query=self.lib.ng2_controller_scene_changes
        query.argtypes=[C.c_void_p,C.POINTER(SceneChange),C.c_size_t];query.restype=C.c_size_t
        out=(SceneChange*3)();count=query(self.engine,out,3)
        return list(out)[:count]
    def initial_scene_change(self,terrain=None):
        terrain=self.fit(terrain);old=self.next_move()
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        ready,new=self.tick();self.assertEqual((1,4),(ready,new.kind))
        return terrain,changed,old,new
    def reconstructed_public_beat_model(self,rows):
        from tests.test_native_beat import NativeSample,NativeModel
        make=self.lib.ng2_make_sample
        make.argtypes=[C.c_double,C.c_double,C.c_double,C.c_uint64,C.c_uint64,C.POINTER(NativeSample)]
        fit=self.lib.ng2_beat_fit;fit.argtypes=[C.POINTER(NativeSample),C.c_size_t,C.POINTER(NativeModel)]
        track=self.lib.ng2_beat_track
        track.argtypes=[C.POINTER(NativeModel),C.POINTER(NativeSample),C.c_size_t,C.POINTER(NativeModel)]
        samples=[];model=NativeModel()
        for end,q in rows:
            sample=NativeSample();self.assertEqual(1,make(q,104.,446.,end-2,end,C.byref(sample)));samples.append(sample)
            if len(samples)>=4:
                observed=(NativeSample*len(samples))(*samples);updated=NativeModel()
                if not track(C.byref(model),observed,len(samples),C.byref(updated)):
                    self.assertEqual(1,fit(observed,len(samples),C.byref(updated)))
                model=updated
        return model
    def test_public_native_controller_resumes_directly_from_confirmed_pause(self):
        self.observe(self.scene());ready,c=self.tick()
        self.assertEqual(1,ready);self.assertEqual((1,297,448),(c.kind,c.x,c.y))
        self.ack(c);self.now+=100_000_000;self.observe(self.scene(2,1))
        self.assertEqual((self.status().phase,self.status().input_state),(1,0))
        self.assertEqual(self.number,self.events()[-1].observed_capture_id)
    def test_observed_scene_is_copied_before_caller_mutation(self):
        scene=self.scene();self.observe(scene)
        self.assertEqual(1,self.status().paused)
        scene.state=0;scene.restart_label=0;scene.goods=2
        ready,command=self.tick()
        self.assertEqual((ready,command.kind),(1,1))
        self.assertEqual(0,self.status().goods)
    def test_full_public_resume_clear_restart_changed_gold_walk_goods_hold(self):
        self.observe(self.scene());_,resume=self.tick();self.ack(resume)
        self.now+=100_000_000;clear=self.scene(2,1);self.observe(clear)
        _,pause=self.tick();self.assertEqual((2,390,448),(pause.kind,pause.x,pause.y));self.ack(pause)
        self.now+=100_000_000;self.observe(self.scene());self.assertEqual(0,self.tick()[0])
        self.now+=100_000_000;_,restart=self.tick();self.assertEqual((3,144,448),(restart.kind,restart.x,restart.y));self.ack(restart)
        self.now+=100_000_000;floor=self.scene(2,2,textured(),beat=True)
        self.observe(floor);self.assertEqual(0,self.status().restarts)
        self.now+=100_000_000;floor=self.scene(2,2,textured(),beat=True)
        for k in (0,1,2,8,9,10):floor.fingerprint[k]=12
        self.observe(floor);self.assertEqual(1,self.status().restarts)
        terrain=self.fit();command=self.next_move();self.assertEqual((command.direction,command.x,command.y),(3,290,838))
        self.ack(command);after=translated(terrain,3);self.observed_result(command,after)
        self.assertEqual((self.status().moves,self.status().x,self.status().y,self.status().last_ordinal),(1,0,-1,1))
        self.hold_goods(after)
    def test_dense_capture_history_retains_two_second_span(self):
        self.fit();s=self.status();self.assertEqual((s.beat_period_ns,s.terminal),(PERIOD,0))
        self.assertEqual(27,s.accepted_frames)
        self.assertEqual(4,self.next_move().kind)
    def test_initial_unsent_scene_change_replans_same_beat_and_retires_old_id(self):
        terrain=self.fit();old=self.next_move()
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind))
        self.assertNotEqual(old.id,new.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.ordinal,old.direction),
                         (new.target_ns,new.not_before_ns,new.ordinal,new.direction))
        self.assertLessEqual(new.deadline_ns,old.deadline_ns)
        self.assertEqual(self.number,new.source_capture_id)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,new.not_before_ns,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,new.not_before_ns,1))
        self.assertEqual((new.id,1),(self.status().current_command_id,self.status().input_state))
        self.ack(new);self.observed_result(new,translated(changed,new.direction))
        self.assertEqual((1,1,1),(self.status().inputs,self.status().moves,self.status().last_ordinal))
    def test_initial_replan_two_changes_then_third_stops_without_next_beat(self):
        terrain=self.fit();original=self.next_move();retired=[];current=original
        for attempt in range(1,4):
            changed=deepcopy(terrain);changed.tiles[(-10+attempt,4)]='stone';terrain=changed
            self.now+=2;self.observe(self.scene(2,2,changed,beat=True));retired.append(current.id)
            ready,replacement=self.tick()
            if attempt<=2:
                self.assertEqual((1,4),(ready,replacement.kind))
                self.assertEqual((original.target_ns,original.not_before_ns,original.ordinal,original.direction),
                                 (replacement.target_ns,replacement.not_before_ns,replacement.ordinal,replacement.direction))
                self.assertLessEqual(replacement.deadline_ns,original.deadline_ns)
                current=replacement
            else:
                self.assertNotEqual(4,replacement.kind)
                self.assertEqual((17,0,0),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual(3,len([e for e in self.events() if e.command.kind==4]))
        self.now=original.deadline_ns+PERIOD
        for old in retired:
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old,self.now,1,0,1))
            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old,self.now,1))
        self.assertNotEqual(4,self.tick()[1].kind)
        changes=self.scene_changes();self.assertEqual(3,len(changes))
        self.assertEqual([1,2,2],[c.replan_count for c in changes])
        self.assertEqual([1,1,0],[c.replan_allowed for c in changes])
    def test_initial_replan_rejects_unsafe_or_changed_evidence(self):
        cases=('unknown','pause','partial','visible','gold','origin_protected','near_protected',
               'destination_neighbor_protected','obstacle','motion_moved','motion_tween','motion_unknown')
        for case in cases:
            with self.subTest(case=case):
                self.fresh_engine();terrain=self.fit();old=self.next_move();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone'
                state=2
                if case=='unknown':state=0
                elif case=='pause':state=1
                elif case in ('partial','visible'):changed.goods=case
                elif case=='gold':changed.tiles[(-9,4)]='gold';changed.gold.add((-9,4))
                elif case=='origin_protected':changed.protected.add((0,0))
                elif case=='near_protected':changed.protected.add((1,0))
                elif case=='destination_neighbor_protected':changed.protected.add((1,-1))
                elif case=='obstacle':changed.tiles[(0,-1)]='stone'
                elif case=='motion_moved':changed.signature=translated(terrain,3).signature
                elif case=='motion_tween':changed.signature=translated(terrain,3,amount=8).signature
                elif case=='motion_unknown':changed.signature=bytes([40])*23296
                self.now+=2;self.observe(self.scene(state,2,changed,beat=True));ready,next_command=self.tick()
                self.assertNotEqual(4,next_command.kind)
                self.assertEqual((0,0),(self.status().inputs,self.status().moves))
                self.assertEqual(3,[e for e in self.events() if e.command.id==old.id][0].outcome)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
                if case=='visible':self.assertEqual((1,1),(self.status().goods,self.status().reason))
    def test_initial_replan_requires_latest_choose_same_direction(self):
        terrain=textured({(0,0):'floor',(0,-1):'floor',(0,-2):'floor',(0,-3):'floor',
                          (1,-3):'floor',(2,-3):'floor',(1,0):'floor',(2,-1):'floor',
                          (2,-2):'door',(1,-2):'gold',(3,-2):'gold'})
        self.fit(terrain);old=self.next_move();self.assertEqual(3,old.direction)
        changed=deepcopy(terrain);changed.tiles[(2,0)]='floor'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual((17,0),(self.status().reason,self.status().inputs))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_initial_replan_requires_original_target_to_be_safe_floor(self):
        terrain=textured({(0,0):'floor',(0,-1):'door',(-1,-1):'gold',(1,-1):'gold'})
        self.fit(terrain);old=self.next_move();self.assertEqual(0,old.ordinal)
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual((17,0),(self.status().reason,self.status().inputs))
    def test_initial_replan_discards_unstable_wrong_prefix_and_old_capture(self):
        for case in ('unstable','wrong_prefix','old_id'):
            with self.subTest(case=case):
                self.fresh_engine();terrain=self.fit();old=self.next_move();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';self.now+=2
                args=({'stable':0} if case=='unstable' else {'prefix':1} if case=='wrong_prefix' else {'number':self.number})
                self.assertEqual(0,self.observe(self.scene(2,2,changed,beat=True),**args))
                self.assertEqual((1,old.id),(self.status().input_state,self.status().current_command_id))
                self.assertEqual(0,self.tick()[0]);self.assertEqual([],self.scene_changes())
    def test_initial_replan_keeps_original_deadline_equal_and_rejects_one_ns_late(self):
        for late in (0,1):
            with self.subTest(late=late):
                self.fresh_engine();terrain,changed,old,new=self.initial_scene_change()
                self.now=old.deadline_ns+late
                result=self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1)
                self.assertEqual(1-late,result)
                if late:
                    self.assertEqual((9,0),(self.status().reason,self.status().inputs))
                    self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,new.id,self.now,1))
    def test_initial_replan_preserves_shorter_original_source_horizon_deadline(self):
        terrain=self.fit();self.now=4_130_000_002
        self.observe(self.scene(2,2,terrain,beat=True));self.now=6_929_999_999
        old=self.next_move()
        self.assertEqual((7_080_000_000,6_930_000_000,6_930_000_000),
                         (old.target_ns,old.not_before_ns,old.deadline_ns))
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=1
        self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind))
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns))
        self.assertGreater(new.source_start_ns,old.source_start_ns)
        self.now=old.deadline_ns+1
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.assertEqual((9,0),(self.status().reason,self.status().inputs))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
    def test_initial_replan_guard_and_cancel_still_reject_latest_id(self):
        for case,front,locked,owner,reason in (('foreground',0,0,1,3),('locked',1,1,1,4),
                                             ('owner',1,0,0,5),('cancel',1,0,1,2)):
            with self.subTest(case=case):
                self.fresh_engine();terrain,changed,old,new=self.initial_scene_change();self.now=new.not_before_ns
                if case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,front,locked,owner))
                self.assertEqual((reason,0),(self.status().reason,self.status().inputs))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,self.now,1))
    def test_initial_replan_never_reopens_sent_or_unknown_input(self):
        for outcome in (None,-1):
            with self.subTest(outcome=outcome):
                self.fresh_engine();terrain=self.fit();command=self.next_move();self.now=command.not_before_ns
                self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
                if outcome is not None:self.lib.ng2_controller_complete(self.engine,command.id,self.now+1,outcome)
                changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
                self.observe(self.scene(2,2,changed,beat=True));self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]));self.assertEqual([],self.scene_changes())
    def test_initial_replan_is_disabled_after_blocked_sent_trial_or_confirmed_move(self):
        for moved in (False,True):
            with self.subTest(moved=moved):
                self.fresh_engine();terrain=self.fit();first=self.next_move();self.ack(first)
                after=translated(terrain,3) if moved else terrain;self.observed_result(first,after)
                self.assertEqual(1,self.status().inputs);self.assertEqual(int(moved),self.status().lead_confirmed)
                current=self.next_move();changed=deepcopy(after);changed.tiles[(-10,4)]='stone'
                self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
                self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual((17,1),(self.status().reason,self.status().inputs))
                self.assertEqual(2,len([e for e in self.events() if e.command.kind==4]))
    def test_initial_replan_scene_change_diagnostic_is_exact_and_bounded(self):
        terrain,changed,old,new=self.initial_scene_change();rows=self.scene_changes()
        self.assertEqual(1,len(rows));row=rows[0]
        self.assertEqual((old.id,old.source_capture_id,new.source_capture_id,old.target_ns,old.deadline_ns),
                         (row.command_id,row.source_capture_id,row.observed_capture_id,row.target_ns,row.deadline_ns))
        self.assertEqual((4,1,0,2,2,0,0,1,1),(row.change_mask,row.changed_tiles,row.changed_protected,
                         row.state_before,row.state_after,row.goods_before,row.goods_after,row.replan_count,row.replan_allowed))
    def test_initial_replan_accepts_remote_protected_change_and_reports_cell_counts(self):
        terrain=self.fit();old=self.next_move();changed=deepcopy(terrain);changed.protected.add((-10,4))
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind));self.assertEqual(old.target_ns,new.target_ns)
        row=self.scene_changes()[0]
        self.assertEqual((8,0,1,1),(row.change_mask,row.changed_tiles,row.changed_protected,row.replan_allowed))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_initial_replan_same_beat_and_new_source_motion_in_all_four_directions(self):
        transforms={1:lambda x,y:(y,-x),2:lambda x,y:(-y,x),3:lambda x,y:(x,y),4:lambda x,y:(-x,-y)}
        for direction,transform in transforms.items():
            with self.subTest(direction=direction):
                self.fresh_engine();base=textured()
                terrain=textured({transform(x,y):kind for (x,y),kind in base.tiles.items()})
                self.fit(terrain);old=self.next_move();self.assertEqual(direction,old.direction)
                changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
                self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick();self.assertEqual((1,4),(ready,new.kind))
                self.assertEqual((direction,old.target_ns,old.not_before_ns,old.ordinal),
                                 (new.direction,new.target_ns,new.not_before_ns,new.ordinal))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                self.ack(new);self.observed_result(new,translated(changed,direction))
                self.assertEqual((1,1,*DIRS[direction]),(self.status().inputs,self.status().moves,self.status().x,self.status().y))
    def test_initial_replan_pending_scene_cannot_accumulate_unbounded_updates_before_tick(self):
        terrain=self.fit();old=self.next_move();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        changed.tiles[(-9,4)]='stone';self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual((17,0),(self.status().reason,self.status().inputs))
        rows=self.scene_changes();self.assertEqual([1,0],[r.replan_allowed for r in rows])
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_initial_replan_keeps_original_beat_when_latest_fit_period_changes(self):
        terrain=textured()
        for _ in range(4):
            self.now+=700_000_000;self.observe(self.scene(2,2,terrain,beat=True))
        self.assertEqual(PERIOD,self.status().beat_period_ns);old=self.next_move()
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        scene=self.scene(2,2,changed,beat=True);scene.beat_remaining=(scene.beat_remaining+.04)%1
        self.observe(scene);ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind));self.assertNotEqual(PERIOD,self.status().beat_period_ns)
        self.assertEqual((old.target_ns,old.not_before_ns,old.ordinal,old.direction),
                         (new.target_ns,new.not_before_ns,new.ordinal,new.direction))
        self.assertLessEqual(new.deadline_ns,old.deadline_ns)
        self.ack(new);self.observed_result(new,translated(changed,new.direction))
        self.assertEqual((1,1),(self.status().inputs,self.status().moves))
        self.assertEqual(2,len([e for e in self.events() if e.command.kind==4]))
        ready,following=self.tick();self.assertEqual((1,4),(ready,following.kind))
        self.assertEqual(new.target_ns+PERIOD-150_000_000+10_000_000,following.deadline_ns)
    def test_initial_replan_invalidated_model_stops_instead_of_waiting_for_new_beat(self):
        terrain=textured()
        for _ in range(4):
            self.now+=700_000_000;self.observe(self.scene(2,2,terrain,beat=True))
        old=self.next_move();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        scene=self.scene(2,2,changed,beat=True);scene.beat_remaining=(scene.beat_remaining+.16)%1
        self.observe(scene);self.assertNotEqual(4,self.tick()[1].kind)
        self.assertNotEqual(0,self.status().reason)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
        self.now=old.deadline_ns+PERIOD;self.observe(self.scene(2,2,changed,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_initial_replan_rechecks_original_phase_alignment_after_later_hud_updates(self):
        terrain=textured()
        for _ in range(4):
            self.now+=700_000_000;self.observe(self.scene(2,2,terrain,beat=True))
        old=self.next_move();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick();self.assertEqual((1,4),(ready,new.kind))
        for _ in range(2):
            self.now+=2;scene=self.scene(2,2,changed,beat=True)
            scene.beat_remaining=(scene.beat_remaining+.13)%1;self.observe(scene)
        self.assertGreater(self.status().beat_period_ns,PERIOD)
        self.assertEqual((old.target_ns,old.not_before_ns,old.ordinal),(new.target_ns,new.not_before_ns,new.ordinal))
        self.now=new.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.assertEqual(0,self.status().inputs)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
    def test_initial_replan_phase_alignment_boundary_is_inclusive_for_original_period(self):
        # Reconstruct the public fit/track output to establish that the fake
        # HUD sequence actually reaches before/equal/after the original bound.
        cases=((0.12831125,529_773_493,41_599_995,1),
               (0.12831126475488247,529_773_494,41_600_000,1),
               (0.1283112647548825,529_773_495,41_600_005,0))
        for bias,expected_period,expected_delta,allowed in cases:
            with self.subTest(bias=bias):
                self.fresh_engine();terrain=textured();rows=[]
                for _ in range(4):
                    self.now+=700_000_000;scene=self.scene(2,2,terrain,beat=True)
                    rows.append((self.now,scene.beat_remaining));self.observe(scene)
                old=self.next_move();self.assertEqual(4_480_000_000,old.target_ns)
                changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
                scene=self.scene(2,2,changed,beat=True);rows.append((self.now,scene.beat_remaining));self.observe(scene)
                ready,new=self.tick()
                self.assertEqual((1,4),(ready,new.kind))
                for _ in range(2):
                    self.now+=2;scene=self.scene(2,2,changed,beat=True)
                    scene.beat_remaining=(scene.beat_remaining+bias)%1
                    rows.append((self.now,scene.beat_remaining));self.observe(scene)
                self.assertEqual(expected_period,self.status().beat_period_ns)
                model=self.reconstructed_public_beat_model(rows)
                self.assertEqual(expected_period,model.period_ns)
                forward=(model.epoch_ns-old.target_ns)%model.period_ns
                aligned=old.target_ns+forward if forward<=model.period_ns//2 else old.target_ns-(model.period_ns-forward)
                self.assertEqual(expected_delta,abs(aligned-old.target_ns))
                self.assertEqual((old.target_ns,old.not_before_ns,old.ordinal),(new.target_ns,new.not_before_ns,new.ordinal))
                self.now=new.not_before_ns
                self.assertEqual(allowed,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
    def test_initial_replan_expired_before_reissue_never_moves_to_a_later_beat(self):
        terrain=self.fit();old=self.next_move();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));self.now=old.deadline_ns+1
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertNotEqual(0,self.status().reason)
        self.now+=PERIOD;self.observe(self.scene(2,2,changed,beat=True));self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_fixed_ordinals_allow_observed_turn_and_never_skip_late_beat(self):
        terrain=textured({(0,0):'floor',(0,-1):'floor',(1,-1):'floor',(2,-1):'door',
                          (2,-2):'gold',(2,0):'gold',(-4,-2):'stone',(5,1):'stone'})
        self.fit(terrain);first=self.next_move();self.assertEqual(3,first.direction);self.ack(first)
        after=translated(terrain,3);self.observed_result(first,after)
        second=self.next_move();self.assertEqual((second.direction,second.ordinal),(2,2))
        self.assertLessEqual(abs(second.target_ns-first.target_ns-PERIOD),1)
        self.assertLessEqual(second.deadline_ns,first.target_ns+PERIOD-150_000_000+10_000_000)
        self.ack(second);after=translated(after,2);self.observed_result(second,after)
        s=self.status();self.assertEqual((s.moves,s.x,s.y,s.last_ordinal),(2,1,-1,2))
        self.now=second.target_ns+PERIOD-150_000_000+10_000_001
        self.assertEqual(0,self.tick()[0]);self.assertEqual(9,self.status().reason)
        self.assertEqual(2,len([e for e in self.events() if e.command.kind==4]))
    def test_door_and_dirt_opening_count_operation_without_step(self):
        for obstacle,field in (('door','door_changes'),('dirt','terrain_changes')):
            with self.subTest(obstacle=obstacle):
                if obstacle=='dirt':
                    self.engine=self.lib.ng2_controller_create(self.now)
                    self.addCleanup(self.lib.ng2_controller_destroy,self.engine);self.prefix=0;self.number=0
                terrain=textured({(0,0):'floor',(0,-1):obstacle,(-1,-1):'gold',(1,-1):'gold',(0,-2):'floor'})
                self.fit(terrain);first=self.next_move();self.assertEqual(0,first.ordinal);self.ack(first)
                opened=deepcopy(terrain);opened.tiles[(0,-1)]='floor';self.observed_result(first,opened)
                s=self.status();self.assertEqual((s.moves,getattr(s,field),s.lead_confirmed,s.last_ordinal),(0,1,0,0))
                second=self.next_move();self.assertEqual(1,second.ordinal);self.ack(second)
                inside=translated(opened,3);self.observed_result(second,inside)
                self.assertEqual((self.status().moves,self.status().y,self.status().lead_confirmed,self.status().last_ordinal),(1,-1,1,1));self.hold_goods(inside)
    def test_queued_main_late_guard_and_single_consumption(self):
        self.fit();command=self.next_move()
        self.assertEqual(0,self.tick()[0])
        self.now=command.deadline_ns+1
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.assertEqual((self.status().input_state,self.status().reason),(0,9))
        self.assertEqual(3,self.events()[-1].outcome)
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,command.id,self.now,1))
    def test_source_horizon_includes_lead_and_fifty_ms_end(self):
        terrain=self.fit();self.now+=190_000_000
        self.observe(self.scene(2,2,terrain,beat=True));source=self.status().last_capture_start_ns
        self.now=source+2_800_000_000
        self.assertEqual(0,self.tick()[0])
        self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_phase_horizon_independently_includes_input_end(self):
        terrain=self.fit();self.now+=190_000_000
        self.observe(self.scene(2,2,terrain,beat=True));phase=self.now-1
        self.now=phase+2_800_000_000
        self.observe(self.scene(2,2,terrain,beat=False))
        self.assertEqual(0,self.tick()[0])
        self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_actual_one_ns_late_end_cannot_cross_source_horizon(self):
        terrain=self.fit();self.now=4_130_000_002
        self.observe(self.scene(2,2,terrain,beat=True))
        self.now=6_929_999_999
        command=self.next_move();self.assertEqual(7_080_000_000,command.target_ns)
        self.now=command.not_before_ns+1
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
    def test_input_end_exactly_on_source_horizon_is_allowed(self):
        terrain=self.fit();self.now=4_130_000_002
        self.observe(self.scene(2,2,terrain,beat=True));self.now=6_929_999_999
        command=self.next_move();self.now=command.not_before_ns
        self.assertEqual(self.status().last_capture_start_ns+3*SECOND,self.now+150_000_000+50_000_000)
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
    def test_unknown_synth_and_started_cancel_freeze_even_pause(self):
        self.observe(self.scene());_,c=self.tick()
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,c.id,self.now,1,0,1))
        self.now+=10
        self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,c.id,self.now,-1))
        self.observe(self.scene(2,2));self.assertEqual(0,self.tick()[0])
        self.assertEqual((self.status().terminal,self.status().input_state,self.status().reason),(1,4,11))
        self.assertEqual(1,len(self.events()))
    def test_cancel_reserved_is_definitely_not_sent(self):
        self.observe(self.scene());_,c=self.tick();self.lib.ng2_controller_cancel(self.engine,self.now,2)
        self.assertEqual((self.status().terminal,self.status().input_state,self.events()[-1].outcome),(1,0,3))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,c.id,self.now,1,0,1))
    def test_cancel_after_begin_is_unknown_and_never_cleanup_pause(self):
        self.observe(self.scene());_,command=self.tick()
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
        self.now+=1;self.lib.ng2_controller_cancel(self.engine,self.now,2)
        self.assertEqual((self.status().terminal,self.status().input_state,self.events()[-1].outcome),(1,4,4))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,command.id,self.now+2,1))
        self.assertEqual(0,self.tick()[0])
    def test_capture_crossing_and_old_prefix_cannot_confirm_movement(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction);self.now=command.target_ns+80_000_002
        self.assertEqual(0,self.observe(self.scene(2,2,after,beat=True),prefix=0))
        self.assertEqual(0,self.observe(self.scene(2,2,after,beat=True),stable=0,start=self.now,end=self.now+1))
        self.assertEqual((self.status().moves,self.status().input_state),(0,3))
        self.now+=100_000_000;self.observe(self.scene(2,2,after,beat=True))
        self.assertEqual((self.status().moves,self.status().input_state),(1,0))
    def test_before_target_plus_eighty_ms_and_tween_wait_for_real_motion(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction)
        self.now=command.target_ns+79_000_000;self.observe(self.scene(2,2,after,beat=True))
        self.assertEqual((self.status().moves,self.status().input_state),(0,3))
        tween=translated(terrain,command.direction,amount=8)
        self.now+=10_000_000;self.observe(self.scene(2,2,tween,beat=True))
        self.assertEqual((self.status().moves,self.status().input_state),(0,3))
        self.now+=10_000_000;self.observe(self.scene(2,2,after,beat=True))
        self.assertEqual((self.status().moves,self.status().input_state),(1,0))
    def test_unknown_motion_stops_without_lead_retry(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=deepcopy(terrain);after.signature=bytes([40])*23296
        self.observed_result(command,after)
        self.assertEqual((self.status().reason,self.status().lead_ns,self.status().lead_confirmed),(10,150_000_000,0))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_late_unobserved_prefix_stops_at_original_next_beat(self):
        terrain=self.fit();first=self.next_move();self.ack(first)
        after=translated(terrain,3);self.observed_result(first,after)
        second=self.next_move();self.ack(second)
        self.now=second.target_ns+PERIOD-150_000_000+10_000_001
        self.assertEqual(0,self.tick()[0])
        self.assertEqual((self.status().terminal,self.status().reason,self.status().moves),(1,9,1))
    def test_phase_discontinuity_never_reacquires_after_confirmation(self):
        terrain=self.fit();first=self.next_move();self.ack(first)
        after=translated(terrain,3);self.observed_result(first,after)
        self.now+=10_000_000;bad=self.scene(2,2,after,beat=True)
        bad.beat_remaining=(bad.beat_remaining+.2)%1
        self.observe(bad)
        self.assertEqual(8,self.status().reason)
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_current_stale_goods_frame_is_discarded_without_latch(self):
        self.now=SECOND+3_900_000_000;self.tick()
        stale=self.scene(2,2);stale.goods=2
        self.observe(stale,start=SECOND+100_000_000,end=SECOND+100_000_002)
        self.assertEqual(0,self.status().goods)
    def test_goods_crossing_latches_before_motion_but_needs_stable_pause_source(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        goods=translated(terrain,3);goods.goods='visible';self.now=command.target_ns+80_000_002
        self.observe(self.scene(2,2,goods,beat=True),stable=0)
        self.assertEqual((self.status().goods,self.status().moves),(1,0));self.assertEqual(0,self.tick()[0])
        self.now+=100_000_000;self.observe(self.scene(2,2,goods,beat=True))
        self.assertEqual(2,self.tick()[1].kind)
    def test_invalid_out_of_order_stale_and_unknown_geometry_never_move(self):
        self.observe(self.scene(2,0));self.now+=10
        bad=self.scene(2,2);bad.struct_size-=1
        self.observe(bad);self.assertEqual((self.status().terminal,self.status().reason),(1,20))
    def test_guard_change_before_main_rejects_input(self):
        for front,locked,owner,reason in ((0,0,1,3),(1,1,1,4),(1,0,0,5)):
            engine=self.lib.ng2_controller_create(SECOND)
            try:
                scene=self.scene();self.lib.ng2_controller_observe(engine,C.byref(scene),1,SECOND+100_000_000-2,SECOND+100_000_000,0,1)
                command=Command();self.lib.ng2_controller_tick(engine,SECOND+100_000_000,1,0,1,C.byref(command))
                self.assertEqual(0,self.lib.ng2_controller_begin(engine,command.id,SECOND+100_000_000,front,locked,owner))
                out=Status();self.lib.ng2_controller_status(engine,C.byref(out));self.assertEqual((out.terminal,out.reason),(1,reason))
            finally:self.lib.ng2_controller_destroy(engine)
    def test_session_180_and_sync_12_second_boundaries(self):
        self.now+=180*SECOND;self.assertEqual(0,self.tick()[0]);self.assertEqual((self.status().terminal,self.status().reason),(1,15))
    def test_initial_sync_twelve_second_limit_and_walk_forty_five(self):
        terrain=textured();self.observe(self.scene(2,2,terrain));walk=self.status().walk_started_ns
        self.now=walk+12*SECOND;self.observe(self.scene(2,2,terrain))
        self.assertEqual(0,self.tick()[0]);self.assertEqual(8,self.status().reason)
        other=self.lib.ng2_controller_create(SECOND);self.addCleanup(self.lib.ng2_controller_destroy,other)
        self.engine=other;self.now=SECOND+100_000_000;self.number=0;self.prefix=0
        self.observe(self.scene(2,2,terrain));walk=self.status().walk_started_ns
        self.now=walk+45*SECOND;self.assertEqual(0,self.tick()[0]);self.assertEqual(14,self.status().reason)
    def test_twelve_changed_restarts_bound_and_no_thirteenth(self):
        fingerprint=0
        self.observe(self.scene(2,1))
        for count in range(12):
            ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2));self.ack(pause)
            self.now+=200_000_000;self.observe(self.scene());ready,restart=self.tick()
            self.assertEqual((ready,restart.kind),(1,3));self.ack(restart)
            self.now+=100_000_000;clear=self.scene(2,1);fingerprint=12-fingerprint
            for k in (0,1,2,8,9,10):clear.fingerprint[k]=fingerprint
            self.observe(clear);self.assertEqual(count+1,self.status().restarts)
        self.assertEqual(0,self.tick()[0]);self.assertEqual(14,self.status().reason)
        self.assertEqual(12,len([e for e in self.events() if e.command.kind==3]))
    def test_sixteen_actual_operations_bound_even_with_valid_next_beat(self):
        terrain=self.fit();first=self.next_move();self.ack(first)
        after=translated(terrain,3);self.observed_result(first,after)
        closed=textured({(0,0):'floor',(0,-1):'door',(-1,-1):'gold',(1,-1):'gold'})
        for count in range(15):
            self.now+=10_000_000;self.observe(self.scene(2,2,closed,beat=True))
            command=self.next_move();self.assertEqual(count+2,command.ordinal);self.ack(command)
            opened=deepcopy(closed);opened.tiles[(0,-1)]='floor'
            self.observed_result(command,opened)
            self.assertEqual((self.status().inputs,self.status().door_changes),(count+2,count+1))
        self.assertEqual(0,self.tick()[0]);self.assertEqual((self.status().reason,self.status().moves),(14,1))
        self.assertEqual(16,len([e for e in self.events() if e.command.kind==4]))
    def test_blocked_initial_lead_retunes_only_same_safe_floor_then_confirms(self):
        terrain=self.fit();first=self.next_move();self.ack(first);self.observed_result(first,terrain)
        self.assertEqual((self.status().lead_ns,self.status().lead_confirmed,self.status().moves),(75_000_000,0,0))
        second=self.next_move();self.assertEqual(1,second.ordinal);self.ack(second)
        after=translated(terrain,second.direction);self.observed_result(second,after)
        self.assertEqual((self.status().lead_confirmed,self.status().moves,self.status().last_ordinal),(1,1,1))
        third=self.next_move();self.assertEqual(2,third.ordinal)
    def test_seven_blocked_initial_trials_exhaust_without_unknown_retry(self):
        terrain=self.fit()
        for lead in (150,75,225,300,375,450,25):
            self.assertEqual(lead*1_000_000,self.status().lead_ns)
            command=self.next_move();self.ack(command);self.observed_result(command,terrain)
        self.assertEqual((self.status().reason,self.status().lead_confirmed,self.status().inputs),(10,0,7))
        self.assertEqual(0,self.status().moves)
    def test_stale_old_id_and_observation_before_creation_are_rejected(self):
        self.assertEqual(0,self.observe(self.scene(),start=SECOND-2,end=SECOND))
        self.now+=100_000_000;self.assertEqual(1,self.observe(self.scene()))
        accepted=self.status().last_capture_id
        self.now+=100_000_000;self.assertEqual(0,self.observe(self.scene(2,2),number=accepted))
        self.assertEqual(accepted,self.status().last_capture_id)
        self.now+=3*SECOND;self.assertEqual(0,self.tick()[0]);self.assertEqual(7,self.status().reason)
    def test_restart_unchanged_timeout_never_resends(self):
        self.observe(self.scene(2,1));_,pause=self.tick();self.ack(pause)
        self.now+=200_000_000;self.observe(self.scene());_,restart=self.tick();self.ack(restart)
        self.now+=100_000_000;self.observe(self.scene(2,2))
        self.now+=4*SECOND;self.assertEqual(0,self.tick()[0])
        self.assertEqual((self.status().terminal,self.status().reason,self.status().restarts),(1,16,0))
        self.assertEqual(2,len(self.events()))
    def test_clock_extremes_and_invalid_calls(self):
        self.assertFalse(self.lib.ng2_controller_create(2**63-1))
        self.assertFalse(self.lib.ng2_controller_create(2**64-1))
        self.assertEqual(-1,self.lib.ng2_controller_tick(None,self.now,1,0,1,None))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,1,2**63,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,1,self.now,1))
        self.assertEqual(b'unknown',self.lib.ng2_reason_name(999))
    def test_next_fixed_target_cannot_escape_signed_native_time_range(self):
        end=2**63-1;started=end-180*SECOND
        self.engine=self.lib.ng2_controller_create(started);self.addCleanup(self.lib.ng2_controller_destroy,self.engine)
        self.assertTrue(self.engine);self.number=0;self.prefix=0;terrain=textured();epoch=end-100_000_000
        for i in range(24):
            self.now=started+177_200_000_000+i*100_000_000
            scene=self.scene(2,2,terrain,beat=True)
            scene.beat_remaining=((epoch-(self.now-1))%PERIOD)/PERIOD
            self.observe(scene)
        command=self.next_move();self.ack(command)
        self.now=command.target_ns+80_000_002;after=translated(terrain,3)
        scene=self.scene(2,2,after,beat=True);scene.beat_remaining=((epoch-(self.now-1))%PERIOD)/PERIOD
        self.observe(scene)
        self.assertLess(self.status().next_target_ns,2**63)
    def test_sanitized_full_real_core_walk_and_goods_hold(self):
        harness=r'''
#include "NG2Controller.h"
#include <stdio.h>
#include <math.h>
#define SEC UINT64_C(1000000000)
static void beat(NG2Scene *s,uint64_t now){
    double q=fmod((5000000000.0-(double)(now-1))/520000000.0,1.0);
    s->beat_valid=1;s->beat_remaining=q<0?q+1:q;s->beat_spacing=104;s->beat_center=446;
}
int main(void){
    NG2Scene before,after,pause={0};NG2Command command,hold;NG2ControllerStatus status;
    NG2Controller *p;NG2ControllerEvent events[64];uint64_t now=SEC,id=0;int i;
    if(fread(&before,1,sizeof(before),stdin)!=sizeof(before)||fread(&after,1,sizeof(after),stdin)!=sizeof(after))return 20;
    p=ng2_controller_create(now);if(!p)return 21;
    for(i=0;i<27;++i){now+=100000000;beat(&before,now);
        if(ng2_controller_observe(p,&before,++id,now-2,now,0,1)!=1)return 22;}
    if(ng2_controller_tick(p,now,1,0,1,&command)!=1||command.kind!=4)return 23;
    now=command.not_before_ns;if(ng2_controller_begin(p,command.id,now,1,0,1)!=1)return 24;
    now+=50000000;if(ng2_controller_complete(p,command.id,now,1)!=1)return 25;
    now=command.target_ns+80000002;beat(&after,now);
    if(ng2_controller_observe(p,&after,++id,now-2,now,command.id,1)!=1)return 26;
    ng2_controller_status(p,&status);if(status.moves!=1||status.last_ordinal!=1)return 27;
    now+=100000000;after.goods=2;beat(&after,now);
    if(ng2_controller_observe(p,&after,++id,now-2,now,command.id,1)!=1)return 28;
    if(ng2_controller_tick(p,now,1,0,1,&hold)!=1||hold.kind!=2)return 29;
    if(ng2_controller_begin(p,hold.id,now,1,0,1)!=1)return 30;
    now+=50000000;if(ng2_controller_complete(p,hold.id,now,1)!=1)return 31;
    now+=100000000;pause.abi_version=1;pause.struct_size=sizeof(pause);pause.state=1;
    ng2_controller_observe(p,&pause,++id,now-2,now,hold.id,1);
    ng2_controller_status(p,&status);
    if(!status.terminal||!status.paused||status.goods!=1)return 32;
    if(ng2_controller_events(p,events,64)!=2||ng2_controller_events(p,NULL,64)!=0)return 33;
    ng2_controller_destroy(p);
    for(i=0;i<100;++i){p=ng2_controller_create(SEC);if(!p)return 34;
        ng2_controller_cancel(p,SEC+1,2);ng2_controller_status(p,&status);ng2_controller_destroy(p);}
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='ngg2-controller-sanitize-') as directory:
            directory=Path(directory);source=directory/'harness.c';source.write_text(harness)
            executable=directory/'harness'
            subprocess.run(['cc','-std=c99','-O1','-g','-Wall','-Wextra','-Werror','-ffp-contract=off',
                            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I',str(CORE),
                            str(source),*map(str,self.sources),'-lm','-o',str(executable)],check=True)
            before=textured();after=translated(before,3)
            raw=bytes(self.scene(2,2,before))+bytes(self.scene(2,2,after))
            result=subprocess.run([str(executable)],input=raw,capture_output=True,
                                  env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1',
                                       'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
            self.assertEqual(0,result.returncode,result.stderr.decode())

if __name__=='__main__':unittest.main()
