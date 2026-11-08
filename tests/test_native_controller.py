"""NG-G2 public controller with real C beat/navigation/motion, native fake clock.

Known synthetic textures establish host transitions, not iPhone acceptance.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
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
class CellChange(C.Structure):
    _fields_=[(k,C.c_int32) for k in ('x','y','tile_before','tile_after','protected_before','protected_after')]
class SceneDetail(C.Structure):
    _fields_=[*[(k,C.c_uint64) for k in ('command_id','source_capture_id','observed_capture_id')],
              *[(k,C.c_int32) for k in ('validation','continuous_count','chain_count','cell_count','omitted_cells')],
              ('cells',CellChange*4)]
class MotionWait(C.Structure):
    _fields_=[*[(k,C.c_uint64) for k in ('command_id','source_capture_id','last_capture_id','deadline_ns')],
              *[(k,C.c_int32) for k in ('attempts','last_motion','active')]]
class MotionReference(C.Structure):
    _fields_=[*[(k,C.c_uint64) for k in ('command_id','authority_capture_id','reference_capture_id',
                                      'reference_start_ns','reference_prefix','observed_capture_id')],
              *[(k,C.c_int32) for k in ('reference_eligible','primary_motion','fallback_attempted','fallback_motion')],
              ('selected_capture_id',C.c_uint64),('selected_motion',C.c_int32)]
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
        l.ng2_controller_motion_wait.argtypes=[C.c_void_p,C.POINTER(MotionWait)]
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
    def motion_wait(self):
        out=MotionWait();self.lib.ng2_controller_motion_wait(self.engine,C.byref(out));return out
    def motion_references(self):
        query=self.lib.ng2_controller_motion_references
        query.argtypes=[C.c_void_p,C.POINTER(MotionReference),C.c_size_t];query.restype=C.c_size_t
        out=(MotionReference*16)();count=query(self.engine,out,16);return list(out)[:count]
    def motion_selection_wrapper(self):
        """Unit-only result selection, distinct from real-pixel replay above.

        Every unarmed call uses the unchanged actual C motion matcher. Only
        explicitly armed assessment calls or one numbered guard call differ.
        """
        cls=type(self)
        if not hasattr(cls,'motion_selection_lib'):
            directory=Path(cls.temp.name);source=directory/'selection-wrapper.c'
            source.write_text(r'''
#include "NG2Core.h"
static int mode,calls,at,values[8];
static int choice_calls,choice_at,choice_field;
void test_motion_reset(void){mode=0;calls=0;choice_calls=0;choice_at=0;}
void test_reference_choice_fault(int call,int field){choice_calls=0;choice_at=call;choice_field=field;}
void test_motion_force(int r1,int k1,int x1,int y1,int r2,int k2,int x2,int y2){
    mode=2;calls=0;values[0]=r1;values[1]=k1;values[2]=x1;values[3]=y1;
    values[4]=r2;values[5]=k2;values[6]=x2;values[7]=y2;
}
void test_motion_once(int call,int result,int kind,int x,int y){
    mode=1;calls=0;at=call;values[0]=result;values[1]=kind;values[2]=x;values[3]=y;
}
int test_motion_calls(void){return calls;}
int ng2_real_motion(const NG2Scene *,const NG2Scene *,int32_t,NG2Motion *);
int ng2_motion(const NG2Scene *a,const NG2Scene *b,int32_t direction,NG2Motion *out){
    int offset=0;++calls;
    if((mode==1&&calls==at)||(mode==2&&calls<=2)){
        if(mode==2&&calls==2)offset=4;
        out->kind=values[offset+1];out->dx=values[offset+2];out->dy=values[offset+3];return values[offset];
    }
    return ng2_real_motion(a,b,direction,out);
}
int ng2_real_choose(const NG2Scene *,int32_t,int32_t,const uint16_t *,size_t,const NG2Entrance *,NG2Decision *);
int ng2_choose(const NG2Scene *s,int32_t x,int32_t y,const uint16_t *v,size_t n,const NG2Entrance *e,NG2Decision *out){
    int result=ng2_real_choose(s,x,y,v,n,e,out);++choice_calls;
    if(result&&choice_calls==choice_at){
        if(choice_field==1)out->direction=out->direction==NG2_UP?NG2_RIGHT:NG2_UP;
        else if(choice_field==2)out->reason=out->reason==7?8:7;
        else if(choice_field==3)++out->target_x;
        else if(choice_field==4)++out->target_y;
        else if(choice_field==5)out->obstacle=NG2_TILE_DIRT;
    }
    return result;
}
''')
            navigation=directory/'selection-navigation.c'
            navigation.write_text('#define ng2_motion ng2_real_motion\n#define ng2_choose ng2_real_choose\n#include "'+str(CORE/'NG2Navigation.c')+'"\n')
            library=directory/'selection-controller.so'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fPIC','-shared',
                            '-I',str(CORE),str(source),str(navigation),str(CORE/'NG2Controller.c'),
                            str(CORE/'NG2Perception.c'),str(CORE/'NG2Beat.c'),'-lm','-o',str(library)],check=True)
            cls.motion_selection_lib=C.CDLL(str(library))
        original=self.lib;self.lib=cls.motion_selection_lib;self.addCleanup(setattr,self,'lib',original)
        for name in ('create','destroy','observe','tick','begin','complete','cancel','status','events','motion_wait'):
            name='ng2_controller_'+name;old=getattr(original,name);new=getattr(self.lib,name)
            new.argtypes=old.argtypes;new.restype=old.restype
        self.lib.test_motion_reset.argtypes=[];self.lib.test_motion_force.argtypes=[C.c_int]*8
        self.lib.test_motion_once.argtypes=[C.c_int]*5;self.lib.test_motion_calls.argtypes=[]
        self.lib.test_reference_choice_fault.argtypes=[C.c_int]*2
        self.lib.test_motion_reset()
    def qualified_reference_reissue(self,direction=3):
        terrain,old=self.continuous_walk(moves=1,direction=direction)
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
        self.assertNotEqual(old.id,new.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal))
        return terrain,changed,old,new
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
        ready,c=self.tick()
        s=self.status()
        if not ready and not s.inputs and not s.moves and not s.lead_confirmed and not s.reason and s.next_target_ns:
            # Positive first-MOVE fixtures explicitly reach the publication
            # window. Direct negative tick/begin tests never use this helper.
            self.now=max(self.now,s.next_target_ns-s.lead_ns-100_000_000)
            ready,c=self.tick()
        self.assertEqual((ready,c.kind),(1,4));return c
    def test_initial_slot_waits_before_publishing_a_far_first_beat(self):
        self.fit();self.now=3_840_000_000
        ready,command=self.tick()
        self.assertEqual(0,ready)
        self.assertEqual((0,0,0),(command.kind,self.status().input_state,len(self.events())))
        self.assertEqual(4_480_000_000,self.status().next_target_ns)
    def test_initial_slot_selects_preparation_margin_before_first_ticket(self):
        self.fit();self.now=3_807_430_000
        self.tick();status=self.status()
        self.assertGreaterEqual(status.next_target_ns-status.lead_ns-self.now,50_000_000)
        self.assertEqual((4_480_000_000,0,0),(status.next_target_ns,status.input_state,len(self.events())))
    def armed_initial(self,terrain=None):
        terrain=self.fit(terrain);self.now=3_840_000_000
        self.assertEqual(0,self.tick()[0]);status=self.status()
        self.assertEqual((4_480_000_000,0,0),(status.next_target_ns,status.input_state,len(self.events())))
        return terrain,status.next_target_ns-status.lead_ns
    def test_initial_slot_publication_boundaries_and_no_reselection(self):
        for remaining,expected in ((100_000_001,0),(100_000_000,1),(50_000_000,1),(49_999_999,0)):
            with self.subTest(remaining=remaining):
                self.fresh_engine();terrain,not_before=self.armed_initial()
                self.now=not_before-remaining;ready,command=self.tick()
                self.assertEqual(expected,ready)
                if expected:
                    self.assertEqual((4,4_480_000_000,not_before,not_before+10_000_000,1),
                                     (command.kind,command.target_ns,command.not_before_ns,command.deadline_ns,command.id))
                    self.assertEqual(not_before+PERIOD+10_000_000,self.motion_wait().deadline_ns)
                else:
                    self.assertEqual((0,0,[]),(self.status().input_state,self.status().current_command_id,self.events()))
                    if remaining>100_000_000:
                        self.assertEqual(0,self.status().reason)
                        for _ in range(3):self.assertEqual(0,self.tick()[0])
                        self.now=not_before-100_000_000
                        self.assertEqual((1,4),(lambda v:(v[0],v[1].kind))(self.tick()))
                    else:
                        self.assertEqual(9,self.status().reason)
                        self.now+=PERIOD;self.observe(self.scene(2,2,terrain,beat=True))
                        self.assertNotEqual(4,self.tick()[1].kind)
                        self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_initial_slot_uses_latest_normal_planner_before_any_authority(self):
        _,not_before=self.armed_initial()
        latest=textured({**{(x,0):'floor' for x in range(-7,1)},(-8,0):'door',
                         (-8,-1):'gold',(-8,1):'gold',(-4,-2):'stone',(5,1):'stone'})
        self.assertEqual('left',nav.choose(latest,(0,0))['direction'])
        self.now=not_before-100_000_000;self.observe(self.scene(2,2,latest,beat=True))
        ready,command=self.tick()
        self.assertEqual((1,4,1,self.number,4_480_000_000),(ready,command.kind,command.direction,
                         command.source_capture_id,command.target_ns))
        self.assertEqual([],self.scene_changes())
        self.ack(command);self.observed_result(command,translated(latest,1))
        self.assertEqual((1,1,-1,0),(self.status().inputs,self.status().moves,self.status().x,self.status().y))
    def test_initial_slot_expiry_precedes_unknown_wait_and_never_recovers(self):
        terrain,not_before=self.armed_initial();self.now=not_before-49_999_999
        unknown=self.scene(0);self.observe(unknown)
        self.assertEqual(0,self.tick()[0]);self.assertEqual((9,0),(self.status().reason,self.status().inputs))
        self.now+=PERIOD;self.observe(self.scene(2,2,terrain,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_initial_slot_goods_and_control_guards_prevent_publication(self):
        for case in ('goods','foreground','locked','owner','cancel'):
            with self.subTest(case=case):
                self.fresh_engine();terrain,not_before=self.armed_initial();self.now=not_before-100_000_000
                if case=='goods':
                    terrain.goods='visible';self.observe(self.scene(2,2,terrain,beat=True),stable=0,prefix=99)
                if case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                self.assertNotEqual(4,self.tick(front=int(case!='foreground'),locked=int(case=='locked'),owner=int(case!='owner'))[1].kind)
                self.assertEqual({'goods':1,'foreground':3,'locked':4,'owner':5,'cancel':2}[case],self.status().reason)
                self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_initial_slot_discarded_prefix_and_unstable_frames_do_not_replace_source(self):
        for case in ('prefix','unstable','old_id'):
            with self.subTest(case=case):
                self.fresh_engine();terrain,not_before=self.armed_initial();source=self.status().last_capture_id
                self.now=not_before-100_000_000
                args={'prefix':1} if case=='prefix' else {'stable':0} if case=='unstable' else {'number':source}
                self.assertEqual(0,self.observe(self.scene(2,2,terrain,beat=True),**args))
                ready,command=self.tick();self.assertEqual((1,4,source),(ready,command.kind,command.source_capture_id))
                self.assertEqual([],self.scene_changes())
    def test_initial_slot_invalid_track_cannot_recover_via_immediate_successful_fit(self):
        from tests.test_native_beat import NativeSample,NativeModel
        terrain=textured();rows=[]
        for _ in range(4):
            self.now+=700_000_000;scene=self.scene(2,2,terrain,beat=True)
            rows.append((self.now,scene.beat_remaining));self.observe(scene)
        model=self.reconstructed_public_beat_model(rows)
        self.assertEqual(0,self.tick()[0]);target=self.status().next_target_ns
        self.now+=2;scene=self.scene(2,2,terrain,beat=True);scene.beat_remaining=(scene.beat_remaining+.09)%1
        rows.append((self.now,scene.beat_remaining));samples=[]
        for end,q in rows:
            sample=NativeSample();self.assertEqual(1,self.lib.ng2_make_sample(q,104.,446.,end-2,end,C.byref(sample)));samples.append(sample)
        samples=(NativeSample*len(samples))(*samples);updated=NativeModel()
        self.assertEqual(0,self.lib.ng2_beat_track(C.byref(model),samples,len(samples),C.byref(updated)))
        self.assertEqual(1,self.lib.ng2_beat_fit(samples,len(samples),C.byref(updated)))
        self.assertTrue(updated.period_ns)
        self.observe(scene)
        self.assertEqual((8,0,0,[]),(self.status().reason,self.status().inputs,self.status().moves,self.events()))
        self.now=target+PERIOD;self.observe(self.scene(2,2,terrain,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertFalse(any(e.command.kind==4 for e in self.events()))
    def test_initial_slot_freezes_period_before_first_ticket_and_motion_horizon(self):
        terrain=textured();original_period=515_000_000
        def observed(bias=0):
            scene=self.scene(2,2,terrain,beat=True)
            scene.beat_remaining=(((5*SECOND-(self.now-1))%original_period)/original_period+bias)%1
            self.observe(scene)
        for _ in range(4):self.now+=700_000_000;observed()
        self.assertEqual(0,self.tick()[0]);target=self.status().next_target_ns;not_before=target-self.status().lead_ns
        self.now+=50_000_000;observed(.04)
        self.assertNotEqual(original_period,self.status().beat_period_ns)
        self.assertEqual(0,self.tick()[0]);self.assertEqual(target,self.status().next_target_ns)
        self.now=not_before-100_000_000;ready,old=self.tick();wait=self.motion_wait()
        self.assertEqual((1,4,target,not_before),(ready,old.kind,old.target_ns,old.not_before_ns))
        self.assertEqual(target+original_period-150_000_000+10_000_000,wait.deadline_ns)
        terrain.tiles[(-10,4)]='stone';self.now+=2;observed(.04);ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind))
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,self.motion_wait().deadline_ns))
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
    def test_initial_slot_fresh_publication_cannot_extend_original_source_or_phase_caps(self):
        for horizon in ('source','phase'):
            for late in (0,1):
                with self.subTest(horizon=horizon,late=late):
                    self.fresh_engine();terrain=self.fit();self.now=4_130_000_002
                    self.observe(self.scene(2,2,terrain,beat=True))
                    original_bound=(self.status().last_capture_start_ns if horizon=='source' else self.now-1)+3*SECOND
                    self.now=6_700_000_000
                    if horizon=='phase':self.observe(self.scene(2,2,terrain,beat=False))
                    self.assertEqual(0,self.tick()[0]);target=self.status().next_target_ns
                    self.assertEqual(7_080_000_000,target)
                    self.now=target-150_000_000-100_000_000
                    self.observe(self.scene(2,2,terrain,beat=True));ready,command=self.tick()
                    self.assertEqual((1,4),(ready,command.kind))
                    self.assertEqual(original_bound-200_000_000,command.deadline_ns)
                    self.assertEqual(original_bound,self.motion_wait().deadline_ns)
                    self.assertGreater(command.source_start_ns+3*SECOND,original_bound)
                    self.now=command.deadline_ns+late
                    self.assertEqual(1-late,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
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
    def continuous_walk(self,moves=2,direction=1,terrain=None):
        transforms={1:lambda x,y:(x,y),2:lambda x,y:(-x,-y),3:lambda x,y:(-y,x),4:lambda x,y:(y,-x)}
        length=3 if direction in (3,4) else 8
        tiles={**{(x,0):'floor' for x in range(1-length,1)},
                          (-length,0):'door',(-length,-1):'gold',(-length,1):'gold',
                          (-4,-2):'stone',(5,1):'stone'}
        if terrain is None:terrain=textured({transforms[direction](x,y):kind for (x,y),kind in tiles.items()})
        self.fit(terrain)
        for _ in range(moves):
            command=self.next_move();self.assertEqual(direction,command.direction);self.ack(command)
            terrain=translated(terrain,direction);self.observed_result(command,terrain)
        self.assertEqual((moves,moves,1),(self.status().inputs,self.status().moves,self.status().lead_confirmed))
        return terrain,self.next_move()
    def scene_details(self):
        query=self.lib.ng2_controller_scene_details
        query.argtypes=[C.c_void_p,C.POINTER(SceneDetail),C.c_size_t];query.restype=C.c_size_t
        out=(SceneDetail*3)();count=query(self.engine,out,3)
        return list(out)[:count]
    def continuous_vantage_drift(self):
        initial=textured({**{(x,0):'floor' for x in range(-7,1)},(-7,0):'stone',
                          (-8,0):'door',(-8,-1):'gold',(-8,1):'gold',
                          (-4,-2):'stone',(5,1):'stone'})
        terrain,old=self.continuous_walk(terrain=initial);changed=deepcopy(terrain)
        changed.tiles[(-4,0)]='stone'
        return terrain,changed,old
    def received_test055_frames(self):
        """Real known pixels; synthetic HUD/clock below is not full trace replay."""
        manifest=json.loads((ROOT/'tests/test055-fixtures.json').read_text())
        self.assertEqual(('ngg2-test055-fixtures-v1',11),(manifest['schema'],manifest['count']))
        fixture_root=Path(os.environ.get('NECRO_TEST055_FIXTURE_ROOT','/workspace/analysis-evidence'))
        analyze=self.lib.ng2_analyze_rgba
        analyze.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Scene)]
        frames={};terrain={}
        for entry in manifest['images']:
            capture=entry['capture_id']
            if capture not in (60,69,70):continue
            path=fixture_root/entry['path'];self.assertTrue(path.is_file(),str(path));raw=path.read_bytes()
            self.assertEqual((entry['bytes'],entry['sha256']),(len(raw),hashlib.sha256(raw).hexdigest()))
            with Image.open(path) as image:
                rgba=image.convert('RGBA');pixels=rgba.tobytes();frame=Scene()
                self.assertEqual((896,414),rgba.size)
                self.assertEqual(0,analyze(pixels,len(pixels),rgba.width*4,C.byref(frame)))
                terrain[capture]=nav.scan(image.convert('RGB'))
            frames[capture]=frame
        self.assertEqual({60,69,70},set(frames))
        return frames,terrain
    def received_test055_replan(self):
        frames,terrain=self.received_test055_frames()
        # A public synthetic fit/ACK lead-in establishes the real recorded
        # position(0,1), visits and no entered gate using actual60->69 pixels.
        # Command numbers, HUD and timing here are synthetic, not the missing
        # device beat model or a claimed full original Controller replay.
        self.fit(terrain[60])
        def observed(capture):
            frame=Scene.from_buffer_copy(bytes(frames[capture]));clock=self.scene(2,2,beat=True)
            for field in ('beat_valid','beat_remaining','beat_spacing','beat_center'):setattr(frame,field,getattr(clock,field))
            self.number=capture-1;self.assertEqual(1,self.observe(frame))
        self.now+=2;observed(60);first=self.next_move()
        self.assertEqual((4,60),(first.direction,first.source_capture_id));self.ack(first)
        self.now=max(self.now+2,first.target_ns+80_000_002);observed(69)
        self.assertEqual((1,1,0,1,1),(self.status().inputs,self.status().moves,self.status().x,
                                    self.status().y,self.status().lead_confirmed))
        old=self.next_move();wait=self.motion_wait()
        self.assertEqual((3,69),(old.direction,old.source_capture_id))
        self.now+=2;observed(70)
        retired=[row for row in self.events() if row.command.id==old.id][0]
        self.assertEqual((3,0),(retired.outcome,retired.begin_ns))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
        return old,wait,self.tick()
    def test_required_test055_actual69_70_latest_dirt_plan(self):
        old,wait,(ready,new)=self.received_test055_replan()
        self.assertEqual((1,4,1,207,49,70),(ready,new.kind,new.direction,new.x,new.y,new.source_capture_id))
        self.assertNotEqual(old.id,new.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
    def test_required_test055_actual69_70_latest_authority_and_frozen_beat(self):
        old,wait,(ready,new)=self.received_test055_replan()
        self.assertEqual((12,1,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                   self.scene_details()[-1].chain_count))
        self.assertEqual((1,4,70),(ready,new.kind,new.source_capture_id))
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
    def assert_fresh_ticket(self,old,ready,new,changed):
        visits={(0,0):1};x=y=0
        for row in self.events():
            if row.outcome==2 and row.motion==1:
                x+=row.dx;y+=row.dy;visits[(x,y)]=visits.get((x,y),0)+1
        latest=nav.choose(changed,(self.status().x,self.status().y),visits)
        direction={name:number for number,name in ((1,'left'),(2,'right'),(3,'up'),(4,'down'))}[latest['direction']]
        self.assertEqual((1,4,direction),(ready,new.kind,new.direction))
        self.assertEqual((207 if direction in (1,2) else 290 if direction==3 else 124,
                          49 if direction==1 else 838),(new.x,new.y))
        self.assertNotEqual(old.id,new.id);self.assertEqual(self.number,new.source_capture_id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal))
        self.assertEqual((12,1,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                   self.scene_details()[-1].chain_count))
        retired=[row for row in self.events() if row.command.id==old.id][0]
        self.assertEqual((3,0),(retired.outcome,retired.begin_ns))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,new.not_before_ns,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,new.not_before_ns,1))
    def fresh_private_wrapper(self):
        """Test-only private context, never an app hook or recorded beat model.

        Seed the recorded position/visits/entrance/prefix/frozen bounds exactly.
        The valid model is explicitly constructed because its device samples
        were not retained. All planner/motion/Controller operations stay real C.
        """
        cls=type(self)
        if not hasattr(cls,'fresh_private_lib'):
            directory=Path(cls.temp.name);source=directory/'fresh-private.c'
            source.write_text('static int test055_choose_at,test055_choose_field,test055_choose_calls;\n'
                              '#define ng2_choose test055_choose\n#include "'+str(CORE/'NG2Controller.c')+'"\n'+r'''
#undef ng2_choose
int ng2_choose(const NG2Scene *,int32_t,int32_t,const uint16_t *,size_t,const NG2Entrance *,NG2Decision *);
int test055_choose(const NG2Scene *s,int32_t x,int32_t y,const uint16_t *v,size_t n,const NG2Entrance *e,NG2Decision *out){
    int result=ng2_choose(s,x,y,v,n,e,out);++test055_choose_calls;
    if(result&&test055_choose_calls==test055_choose_at){
        if(test055_choose_field==1)out->direction=out->direction==NG2_UP?NG2_RIGHT:NG2_UP;
        else if(test055_choose_field==2)out->reason=out->reason==7?8:7;
        else if(test055_choose_field==3)++out->target_x;
        else if(test055_choose_field==4)++out->target_y;
        else if(test055_choose_field==5)out->obstacle=NG2_TILE_DIRT;
    }
    return result;
}
void test055_choose_fault(int call,int field){test055_choose_calls=0;test055_choose_at=call;test055_choose_field=field;}
void test055_context(NG2Controller *p,const NG2Scene *scene){
    test055_choose_at=test055_choose_calls=0;
    memset(p,0,sizeof(*p));p->s.abi_version=NG2_ABI_VERSION;p->s.struct_size=sizeof(p->s);
    p->s.started_ns=UINT64_C(30612606910666);p->s.walk_started_ns=UINT64_C(30614393055375);
    p->last_now=UINT64_C(30617195192458);p->s.phase=NG2_PHASE_WALK;
    p->s.inputs=p->s.moves=p->s.lead_confirmed=p->s.y=1;p->s.lead_ns=150000000;
    p->s.last_completed_id=p->last_observed_prefix=3;p->s.last_ordinal=1;
    p->s.last_capture_id=p->seen_id=69;
    p->s.last_capture_start_ns=p->seen_start=UINT64_C(30617158482583);
    p->s.last_capture_end_ns=p->seen_end=UINT64_C(30617170710625);
    p->scene=p->before=*scene;p->have_scene=1;p->event_count=3;p->initial_ticket_valid=1;
    p->visits[16*33+16]=p->visits[17*33+16]=1;
    p->model.mode=2;p->model.sample_count=8;p->model.period_ns=521723193;
    p->model.last_ns=UINT64_C(30617164596604);p->model.first_ns=p->model.last_ns-2100000000;
    p->model.epoch_ns=UINT64_C(30617475642792);p->s.beat_period_ns=p->model.period_ns;
    p->s.next_target_ns=p->next_nominal=UINT64_C(30617475642792);
    p->next_deadline=UINT64_C(30617335642792);p->next_period=p->model.period_ns;
}
int test055_relation(const NG2Scene *a,const NG2Scene *b){return monotone_terrain(a,b);}
void test055_choice(const NG2Controller *p,int which,int32_t *out){
    memcpy(out,which?&p->continuous_pending_choice:&p->command_choice,sizeof(NG2Decision));
}
uint64_t test055_value(const NG2Controller *p,int which){
    switch(which){
        case 0:return p->command_period;case 1:return (uint64_t)p->motion_reference_valid;
        case 2:return (uint64_t)p->motion_reference_present;case 3:return (uint64_t)p->continuous_count;
        case 4:return (uint64_t)p->continuous_chain_count;case 5:return (uint64_t)p->continuous_pending;
        case 6:return p->visits[16*33+16];case 7:return p->visits[17*33+16];
        case 8:return (uint64_t)p->entrance.valid;case 10:return (uint64_t)test055_choose_calls;
        default:return continuous_horizon(p);
    }
}
void test055_mutate(NG2Controller *p,int which,uint64_t value){
    switch(which){
        case 0:p->continuous_ticket.source_start_ns=value;break;
        case 1:p->continuous_ticket.phase_sample_ns=value;break;
        case 2:p->s.walk_started_ns=value;break;case 3:p->s.started_ns=value;break;
        case 4:p->continuous_motion_deadline=value;break;case 5:p->model.last_ns=value;break;
        case 6:p->s.inputs=(int)value;break;case 7:p->model.epoch_ns=value;break;
        case 8:p->continuous_count=(int)value;break;case 9:p->continuous_chain_count=(int)value;break;
        default:((int32_t *)&p->continuous_pending_choice)[which-10]+=(int32_t)value;break;
    }
}
''')
            library=directory/'fresh-private.so'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fPIC','-shared',
                            '-I',str(CORE),str(source),str(CORE/'NG2Perception.c'),str(CORE/'NG2Navigation.c'),
                            str(CORE/'NG2Beat.c'),'-lm','-o',str(library)],check=True)
            cls.fresh_private_lib=C.CDLL(str(library))
        original=self.lib;self.lib=cls.fresh_private_lib;self.addCleanup(setattr,self,'lib',original)
        for name in ('create','destroy','observe','tick','begin','complete','cancel','status','events','motion_wait'):
            name='ng2_controller_'+name;old=getattr(original,name);new=getattr(self.lib,name)
            new.argtypes=old.argtypes;new.restype=old.restype
        self.lib.test055_context.argtypes=[C.c_void_p,C.POINTER(Scene)]
        self.lib.test055_relation.argtypes=[C.POINTER(Scene),C.POINTER(Scene)]
        self.lib.test055_choice.argtypes=[C.c_void_p,C.c_int,C.POINTER(C.c_int32)]
        self.lib.test055_value.argtypes=[C.c_void_p,C.c_int];self.lib.test055_value.restype=C.c_uint64
        self.lib.test055_mutate.argtypes=[C.c_void_p,C.c_int,C.c_uint64]
        self.lib.test055_choose_fault.argtypes=[C.c_int,C.c_int]
    def fresh_private_case(self,before=None,after=None,admit=True):
        self.fresh_private_wrapper();self.fresh_engine()
        if before is None:
            before,after,_=self.fresh_synthetic_scenes('dirt')
        before=Scene.from_buffer_copy(bytes(before));after=Scene.from_buffer_copy(bytes(after))
        before.beat_valid=after.beat_valid=0
        self.lib.test055_context(self.engine,C.byref(before))
        self.now=30617195192458;self.number=69;self.prefix=3;old=self.next_move();wait=self.motion_wait()
        self.now=30617240808083
        if admit:self.assertEqual(1,self.observe(after,number=70,start=30617198203458,end=30617216601291))
        return before,after,old,wait
    def private_choice(self,pending=False):
        values=(C.c_int32*5)();self.lib.test055_choice(self.engine,int(pending),values);return tuple(values)
    def test_required_test055_actual_private_context_exact_clock_and_pending_full_decision(self):
        frames,_=self.received_test055_frames()
        _,_,old,wait=self.fresh_private_case(frames[69],frames[70])
        self.assertEqual((4,2,3,69,30617475642792,30617325642792,30617335642792),
                         (old.id,old.ordinal,old.direction,old.source_capture_id,old.target_ns,old.not_before_ns,old.deadline_ns))
        self.assertEqual((3,8,-4,0,1),self.private_choice())
        self.assertEqual((1,6,-4,0,4),self.private_choice(True))
        self.assertEqual((2,1,1,0),tuple(self.lib.test055_value(self.engine,k) for k in (5,6,7,8)))
        new=self.next_move()
        self.assertEqual((5,2,1,70,207,49),(new.id,new.ordinal,new.direction,new.source_capture_id,new.x,new.y))
        self.assertEqual((1,6,-4,0,4),self.private_choice())
        self.assertEqual((521723193,30617857365985),(self.lib.test055_value(self.engine,0),wait.deadline_ns))
        self.assertEqual(wait.deadline_ns,self.motion_wait().deadline_ns)
        self.assertEqual((1,1,0,1,3),(self.status().inputs,self.status().moves,self.status().x,self.status().y,self.status().last_completed_id))
    def test_fresh_monotone_relation_all_tile_pairs_and_door_brackets(self):
        self.fresh_private_wrapper();k=5*23+8
        allowed={0:{1,2,3,4,5},1:{2,3,4,5},4:{2,3,5}}
        for a in range(7):
            for b in range(7):
                with self.subTest(before=a,after=b):
                    before=self.scene(2,2);after=self.scene(2,2)
                    for frame in (before,after):frame.tiles[k-23]=frame.tiles[k+23]=2
                    before.tiles[k]=a;after.tiles[k]=b
                    self.assertEqual(int(b in allowed.get(a,set())),self.lib.test055_relation(C.byref(before),C.byref(after)))
        before=self.scene(2,2);after=self.scene(2,2);after.tiles[k]=5
        self.assertEqual(0,self.lib.test055_relation(C.byref(before),C.byref(after)))
        after.tiles[k]=2;after.protected_cells[k]=1
        self.assertEqual(0,self.lib.test055_relation(C.byref(before),C.byref(after)))
    def test_fresh_pending_full_five_fields_cannot_drift(self):
        for field in range(5):
            with self.subTest(field=field):
                _,_,old,_=self.fresh_private_case()
                self.lib.test055_mutate(self.engine,10+field,1)
                self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual(17,self.status().reason)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_fresh_cached_source_five_fields_are_proved_once_without_rescue(self):
        for field in range(1,6):
            with self.subTest(field=field):
                _,after,old,_=self.fresh_private_case(admit=False)
                self.lib.test055_choose_fault(1,field)
                self.observe(after,number=70,start=30617198203458,end=30617216601291)
                self.assertEqual(1,self.lib.test055_value(self.engine,10))
                self.assertEqual((10,0,0),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                          self.scene_details()[-1].chain_count))
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def fresh_synthetic_scenes(self,obstacle='dirt',turns=0):
        """Explicit synthetic observation/route variants, not future054 frames."""
        distance=1 if obstacle=='door' else 3
        tiles={(0,y):'floor' for y in range(-3,2)}
        tiles.update({(-distance,-1):'gold',(-distance,0):'dirt',(-distance,1):'dirt'})
        if obstacle=='dirt':tiles.update({(-1,0):'dirt',(-2,0):'dirt'})
        after=dict(tiles);after[(-distance,1)]='gold';after[(-distance,0)]='door'
        if obstacle=='floor':after.update({(-1,0):'floor',(-2,0):'floor'})
        def rotate(x,y):
            for _ in range(turns):x,y=-y,x
            return x,y
        before=self.scene(2,2,textured({rotate(*point):kind for point,kind in tiles.items()}))
        after=self.scene(2,2,textured({rotate(*point):kind for point,kind in after.items()}))
        return before,after,rotate(-1,0)
    def test_fresh_normal_planner_floor_dirt_door_in_all_four_directions(self):
        for obstacle,kind,reason in (('floor',1,7),('dirt',4,6),('door',5,5)):
            for turns in range(4):
                with self.subTest(obstacle=obstacle,turns=turns):
                    before,after,unit=self.fresh_synthetic_scenes(obstacle,turns)
                    _,_,old,wait=self.fresh_private_case(before,after);new=self.next_move()
                    direction=next(d for d,v in DIRS.items() if v==unit)
                    self.assertEqual((direction,reason,kind),tuple(self.private_choice()[i] for i in (0,1,4)))
                    self.assertEqual((direction,207 if direction in (1,2) else 290 if direction==3 else 124,
                                      49 if direction==1 else 838),(new.direction,new.x,new.y))
                    self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                                     (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
                    self.assertEqual((12,1,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                               self.scene_details()[-1].chain_count))
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,new.not_before_ns,1,0,1))
    def test_fresh_then_same_keeps_new_direction_and_sticky_reference_until_budget(self):
        before,after,_=self.fresh_synthetic_scenes('floor')
        _,_,old,wait=self.fresh_private_case(before,after);new=self.next_move()
        self.assertEqual((3,1),(old.direction,new.direction))
        self.assertEqual((1,0),(self.lib.test055_value(self.engine,2),self.lib.test055_value(self.engine,1)))
        for attempt in range(2):
            after=Scene.from_buffer_copy(bytes(after));after.tiles[9+attempt]=3
            self.now+=2;self.observe(after);ready,current=self.tick()
            if not attempt:
                self.assertEqual((1,4,1,207,49),(ready,current.kind,current.direction,current.x,current.y))
                self.assertEqual((2,2,2),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                        self.scene_details()[-1].chain_count))
                self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                                 (current.target_ns,current.not_before_ns,current.deadline_ns,current.ordinal,self.motion_wait().deadline_ns))
                new=current
            else:
                self.assertNotEqual(4,current.kind);self.assertEqual(5,self.scene_details()[-1].validation)
            self.assertEqual(0,self.lib.test055_value(self.engine,1))
        self.assertEqual((1,1),(self.status().inputs,self.status().moves))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,new.not_before_ns,1,0,1))
    def test_fresh_and_same_share_run_eight_and_chain_two_budgets(self):
        for first_same in (False,True):
            with self.subTest(first_same=first_same):
                before,latest,_=self.fresh_synthetic_scenes('floor')
                first=Scene.from_buffer_copy(bytes(before if first_same else latest));first.tiles[8]=3
                _,_,old,wait=self.fresh_private_case(before,first);current=self.next_move()
                self.assertEqual(2 if first_same else 12,self.scene_details()[-1].validation)
                self.lib.test055_mutate(self.engine,8,7)
                second=Scene.from_buffer_copy(bytes(latest))
                second.tiles[8]=3
                if not first_same:second.tiles[5*23+10]=4
                self.now+=2;self.observe(second);replacement=self.next_move()
                self.assertEqual((12,8,2),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count,
                                          self.scene_details()[-1].chain_count))
                self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                                 (replacement.target_ns,replacement.not_before_ns,replacement.deadline_ns,
                                  replacement.ordinal,self.motion_wait().deadline_ns))
                second.tiles[9]=3;self.now+=2;self.observe(second)
                self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual(5,self.scene_details()[-1].validation)
                self.assertEqual((8,2),(self.lib.test055_value(self.engine,3),self.lib.test055_value(self.engine,4)))
                for retired in (old,current,replacement):
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,retired.id,retired.not_before_ns,1,0,1))
    def test_fresh_deadline_and_all_original_horizons_cannot_be_refreshed(self):
        for where in ('tick','begin'):
            for late in (0,1):
                with self.subTest(where=where,late=late):
                    _,_,old,_=self.fresh_private_case()
                    if where=='tick':self.now=old.deadline_ns+late;ready,new=self.tick()
                    else:ready,new=self.tick();self.now=old.deadline_ns+late
                    if where=='tick' and late:self.assertNotEqual(4,new.kind)
                    else:self.assertEqual(1-late,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
        for bound,span in ((0,3*SECOND),(1,3*SECOND),(2,45*SECOND),(3,180*SECOND)):
            for where in ('reserve','begin'):
                with self.subTest(bound=bound,where=where):
                    _,_,old,_=self.fresh_private_case()
                    if where=='begin':new=self.next_move()
                    # A new authority/model may be fresh while the original
                    # horizon no longer covers the entire lead+50ms tail.
                    value=old.deadline_ns+150_000_000+50_000_000-1-span
                    self.lib.test055_mutate(self.engine,bound,value)
                    if where=='reserve':self.assertNotEqual(4,self.tick()[1].kind)
                    else:self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,old.deadline_ns,1,0,1))
                    self.assertEqual((1,1),(self.status().inputs,self.status().moves))
    def test_fresh_pending_change_goods_and_guard_failures_never_send(self):
        for case in ('change','goods','partial','cancel','owner','foreground','locked','phase','model','inputs'):
            with self.subTest(case=case):
                _,after,old,_=self.fresh_private_case()
                if case=='change':
                    after.tiles[8]=3;self.now+=2;self.observe(after)
                elif case in ('goods','partial'):
                    after.goods=2 if case=='goods' else 1;self.now+=2;self.observe(after)
                elif case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                elif case=='phase':self.lib.test055_mutate(self.engine,7,old.target_ns+100_000_000)
                elif case=='model':self.lib.test055_mutate(self.engine,5,self.now-3*SECOND-1)
                elif case=='inputs':self.lib.test055_mutate(self.engine,6,16)
                ready,new=self.tick(front=int(case!='foreground'),locked=int(case=='locked'),owner=int(case!='owner'))
                self.assertNotEqual(4,new.kind)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                if case=='change':self.assertEqual(4,self.scene_details()[-1].validation)
                if case=='goods':self.assertEqual((1,1),(self.status().goods,self.status().reason))
    def test_fresh_ack_earliest_attempts_and_opening_are_not_displacement(self):
        for obstacle in ('dirt','door'):
            with self.subTest(obstacle=obstacle):
                before,after,_=self.fresh_synthetic_scenes(obstacle)
                _,_,_,wait=self.fresh_private_case(before,after);new=self.next_move();self.ack(new)
                earliest=max(self.now,new.target_ns+80_000_000)
                opened=Scene.from_buffer_copy(bytes(after));opened.tiles[5*23+10]=1
                self.now=earliest+1;self.observe(opened,start=earliest-1,end=earliest+1)
                self.assertEqual((0,1),(self.motion_wait().attempts,self.status().moves))
                self.now=earliest+3;self.observe(opened,start=earliest,end=earliest+3)
                self.assertEqual((1,1,0,1),(self.motion_wait().attempts,self.status().moves,self.status().x,self.status().y))
                self.assertEqual((int(obstacle=='door'),int(obstacle=='dirt')),
                                 (self.status().door_changes,self.status().terrain_changes))
                row=self.motion_references()[-1]
                self.assertEqual((new.source_capture_id,0,0),(row.authority_capture_id,row.reference_eligible,row.fallback_attempted))
                self.assertEqual(wait.deadline_ns,self.motion_wait().deadline_ns)
    def test_fresh_unknown_ack_never_retries_or_cleans_up(self):
        _,after,_,_=self.fresh_private_case();new=self.next_move();self.now=new.not_before_ns
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.now+=1;self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,new.id,self.now,-1))
        self.now+=2;self.observe(after);self.assertEqual(0,self.tick()[0])
        self.assertEqual((11,1,4,2),(self.status().reason,self.status().terminal,self.status().input_state,self.status().inputs))
        self.assertEqual([],self.motion_references())
    def test_fresh_unknown_primary_has_three_original_horizon_attempts_without_fallback(self):
        _,after,_,wait=self.fresh_private_case();new=self.next_move();self.ack(new)
        after.signature[:]=bytes([40])*23296
        earliest=max(self.now,new.target_ns+80_000_000)
        for attempt in range(1,4):
            self.now=earliest+2*attempt;self.observe(after)
            row=self.motion_references()[-1]
            self.assertEqual((attempt,wait.deadline_ns),(self.motion_wait().attempts,self.motion_wait().deadline_ns))
            self.assertEqual((0,0,0,new.source_capture_id,0),(row.reference_eligible,row.primary_motion,
                             row.fallback_attempted,row.selected_capture_id,row.selected_motion))
        self.assertEqual((10,1,2),(self.status().reason,self.status().moves,self.status().inputs))
        self.assertNotEqual(4,self.tick()[1].kind)
    def test_fresh_motion_must_be_strict_blocked_before_cancelling_for_new_action(self):
        for kind in ('moved','tween','unknown'):
            with self.subTest(kind=kind):
                _,after,old,_=self.fresh_private_case(admit=False)
                signature=bytes([40])*23296 if kind=='unknown' else translated(textured(),old.direction,8 if kind=='tween' else 9).signature
                after.signature[:]=signature
                self.observe(after,number=70,start=30617198203458,end=30617216601291)
                self.assertEqual((11,0),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count))
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual((1,1),(self.status().inputs,self.status().moves))
    def test_fresh_all_four_directions_and_ordinary_floor_dirt_door(self):
        for obstacle,reason in (('floor',7),('dirt',6),('door',5)):
            for turns in range(4):
                with self.subTest(obstacle=obstacle,turns=turns):
                    before,after,delta=self.fresh_synthetic_scenes(obstacle,turns)
                    _,_,old,wait=self.fresh_private_case(before,after);new=self.next_move()
                    direction={v:k for k,v in DIRS.items()}[delta]
                    self.assertEqual((direction,reason,KINDS[obstacle]),
                                     (new.direction,self.private_choice()[1],self.private_choice()[4]))
                    self.assertEqual((12,1,1),(self.scene_details()[-1].validation,
                                              self.scene_details()[-1].continuous_count,self.scene_details()[-1].chain_count))
                    self.assertNotEqual(old.direction,new.direction)
                    self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                                     (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
    def test_fresh_then_same_keeps_latest_direction_and_sticky_reference(self):
        before,after,_=self.fresh_synthetic_scenes('floor')
        _,_,original,wait=self.fresh_private_case(before,after);fresh=self.next_move()
        self.assertEqual((3,1),(original.direction,fresh.direction))
        self.assertEqual((1,0),tuple(self.lib.test055_value(self.engine,k) for k in (2,1)))
        after.tiles[9*23+1]=3;self.now+=2;self.observe(after)
        same=self.next_move()
        self.assertEqual((1,207,49),(same.direction,same.x,same.y))
        self.assertEqual([12,2],[row.validation for row in self.scene_details()])
        self.assertEqual((2,2,0),tuple(self.lib.test055_value(self.engine,k) for k in (3,4,1)))
        self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal,wait.deadline_ns),
                         (same.target_ns,same.not_before_ns,same.deadline_ns,same.ordinal,self.motion_wait().deadline_ns))
        after.tiles[9*23+2]=3;self.now+=2;self.observe(after)
        self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual([12,2,5],[row.validation for row in self.scene_details()])
        for command in (original,fresh,same):
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
    def test_same_then_fresh_and_fresh_then_fresh_share_two_and_eight(self):
        for first_same in (False,True):
            with self.subTest(first_same=first_same):
                before,after,_=self.fresh_synthetic_scenes('floor')
                if first_same:
                    first=Scene.from_buffer_copy(bytes(before));first.tiles[9*23+1]=3
                    _,_,original,wait=self.fresh_private_case(before,first)
                else:_,_,original,wait=self.fresh_private_case(before,after)
                current=self.next_move();self.lib.test055_mutate(self.engine,8,7)
                if first_same:after.tiles[9*23+1]=3
                else:after.tiles[5*23+10]=4
                self.now+=2;self.observe(after);replacement=self.next_move()
                self.assertEqual([2 if first_same else 12,12],[row.validation for row in self.scene_details()])
                self.assertEqual((8,2),tuple(self.lib.test055_value(self.engine,k) for k in (3,4)))
                self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal,wait.deadline_ns),
                                 (replacement.target_ns,replacement.not_before_ns,replacement.deadline_ns,replacement.ordinal,self.motion_wait().deadline_ns))
                after.tiles[9*23+2]=3;self.now+=2;self.observe(after)
                self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual(5,self.scene_details()[-1].validation)
                for command in (original,current,replacement):
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,command.not_before_ns,1,0,1))
    def test_fresh_original_deadline_equality_and_one_ns_late(self):
        for late in (0,1):
            with self.subTest(late=late):
                _,_,old,_=self.fresh_private_case();self.now=old.deadline_ns+late
                ready,new=self.tick()
                if late:
                    self.assertNotEqual(4,new.kind);self.assertEqual(9,self.status().reason)
                    self.now+=521723193;self.assertNotEqual(4,self.tick()[1].kind)
                else:
                    self.assertEqual((1,4,old.deadline_ns),(ready,new.kind,new.deadline_ns))
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
    def test_fresh_latest_source_cannot_restore_frozen_source_phase_walk_session(self):
        for stage in ('reserve','begin'):
            for which,budget in ((0,3*SECOND),(1,3*SECOND),(2,45*SECOND),(3,180*SECOND)):
                with self.subTest(stage=stage,horizon=which):
                    _,_,old,_=self.fresh_private_case()
                    new=self.next_move() if stage=='begin' else old
                    self.lib.test055_mutate(self.engine,which,new.not_before_ns+200_000_000-1-budget)
                    if stage=='reserve':self.assertNotEqual(4,self.tick()[1].kind)
                    else:
                        self.now=new.not_before_ns
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                    self.assertEqual(7,self.status().reason)
                    self.assertEqual((1,1),(self.status().inputs,self.status().moves))
    def test_fresh_post_ack_earliest_start_three_unknown_attempts_no_old_fallback(self):
        _,after,_,wait=self.fresh_private_case();new=self.next_move();self.ack(new)
        unknown=Scene.from_buffer_copy(bytes(after));unknown.signature[:]=bytes([40])*23296
        earliest=max(self.now,new.target_ns+80_000_000)
        self.now=earliest+1;self.observe(unknown,start=earliest-1,end=self.now)
        self.assertEqual((0,wait.deadline_ns),(self.motion_wait().attempts,self.motion_wait().deadline_ns))
        for attempt in range(1,4):
            self.now+=2;self.observe(unknown,start=self.now-1,end=self.now)
            row=self.motion_references()[-1]
            self.assertEqual((attempt,wait.deadline_ns),(self.motion_wait().attempts,self.motion_wait().deadline_ns))
            self.assertEqual((70,69,0,0,70),(row.authority_capture_id,row.reference_capture_id,row.reference_eligible,
                                           row.fallback_attempted,row.selected_capture_id))
        self.assertEqual((2,1,10),(self.status().inputs,self.status().moves,self.status().reason))
    def test_fresh_ordinary_opening_is_not_displacement(self):
        for obstacle in ('dirt','door'):
            with self.subTest(obstacle=obstacle):
                before,after,_=self.fresh_synthetic_scenes(obstacle)
                _,_,_,_=self.fresh_private_case(before,after);new=self.next_move();self.ack(new)
                opened=Scene.from_buffer_copy(bytes(after));opened.tiles[5*23+10]=1
                self.now=max(self.now+2,new.target_ns+80_000_002);self.observe(opened)
                self.assertEqual((2,1,0,1,2),(self.status().inputs,self.status().moves,self.status().x,
                                            self.status().y,self.status().last_ordinal))
                self.assertEqual((int(obstacle=='door'),int(obstacle=='dirt')),
                                 (self.status().door_changes,self.status().terrain_changes))
                self.assertEqual((0,0),(self.motion_references()[-1].reference_eligible,
                                        self.motion_references()[-1].fallback_attempted))
    def test_fresh_goods_and_live_guards_revoke_both_ids_unknown_never_resends(self):
        for case in ('goods','cancel','foreground','locked','owner','unknown'):
            with self.subTest(case=case):
                _,after,old,_=self.fresh_private_case();new=self.next_move();self.now=new.not_before_ns
                if case=='goods':
                    after.goods=2;self.now+=2;self.observe(after)
                    self.assertEqual((1,1),(self.status().goods,self.status().reason))
                elif case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                elif case=='unknown':
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                    self.now+=1;self.lib.ng2_controller_complete(self.engine,new.id,self.now,-1)
                    self.assertEqual((11,4),(self.status().reason,self.status().input_state))
                    self.assertEqual(0,self.tick()[0])
                for command in (old,new):
                    self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,self.now,
                        int(case!='foreground'),int(case=='locked'),int(case!='owner')))
                self.assertEqual(1+int(case=='unknown'),self.status().inputs)
    def test_continuous_unsent_scene_change_after_two_moves_keeps_original_beat(self):
        terrain,old=self.continuous_walk();wait=self.motion_wait()
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
        ready,new=self.tick()
        self.assertEqual((1,4),(ready,new.kind))
        self.assertNotEqual(old.id,new.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,old.direction),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,new.direction))
        self.assertEqual(wait.deadline_ns,self.motion_wait().deadline_ns)
        self.assertEqual(self.number,new.source_capture_id)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,new.not_before_ns,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,new.not_before_ns,1))
        self.assertEqual((new.id,1),(self.status().current_command_id,self.status().input_state))
        self.ack(new);self.observed_result(new,translated(changed,1))
        self.assertEqual((3,3,-3,0,3),(self.status().inputs,self.status().moves,self.status().x,
                                    self.status().y,self.status().last_ordinal))
        row=self.scene_changes()[-1];detail=self.scene_details()[-1]
        self.assertEqual((old.id,old.source_capture_id,new.source_capture_id,old.deadline_ns),
                         (row.command_id,row.source_capture_id,row.observed_capture_id,row.deadline_ns))
        self.assertNotEqual(self.events()[0].command.deadline_ns,row.deadline_ns)
        self.assertEqual((old.id,old.source_capture_id,new.source_capture_id,2,1,1,1,0),
                         (detail.command_id,detail.source_capture_id,detail.observed_capture_id,detail.validation,
                          detail.continuous_count,detail.chain_count,detail.cell_count,detail.omitted_cells))
        cell=detail.cells[0]
        self.assertEqual((-10,4,0,3,0,0),(cell.x,cell.y,cell.tile_before,cell.tile_after,
                                        cell.protected_before,cell.protected_after))
    def test_continuous_revalidation_all_four_directions(self):
        for direction in DIRS:
            with self.subTest(direction=direction):
                self.fresh_engine();terrain,old=self.continuous_walk(moves=1,direction=direction)
                changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
                self.now+=2;self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
                self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,direction),
                                 (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,new.direction))
                self.ack(new);self.observed_result(new,translated(changed,direction))
                self.assertEqual((2,2,2*DIRS[direction][0],2*DIRS[direction][1]),
                                 (self.status().inputs,self.status().moves,self.status().x,self.status().y))
    def test_continuous_chain_limit_two_then_stops_without_next_beat(self):
        terrain,original=self.continuous_walk();current=original;retired=[]
        for attempt in range(1,4):
            terrain=deepcopy(terrain);terrain.tiles[(-10+attempt,4)]='stone'
            self.now+=2;self.observe(self.scene(2,2,terrain,beat=True));retired.append(current.id)
            ready,new=self.tick()
            if attempt<=2:
                self.assertEqual((1,4),(ready,new.kind));current=new
                self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal),
                                 (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal))
            else:self.assertNotEqual(4,new.kind)
        self.assertEqual((17,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual([2,2,5],[d.validation for d in self.scene_details()])
        self.assertEqual([1,2,2],[d.chain_count for d in self.scene_details()])
        for old in retired:
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old,original.not_before_ns,1,0,1))
            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old,original.not_before_ns,1))
    def test_continuous_run_limit_eight_and_first_latest_diagnostics(self):
        terrain,current=self.continuous_walk();rows=[];changed=False
        for chain in range(4):
            for refresh in range(2):
                terrain=deepcopy(terrain);changed=not changed
                if changed:terrain.tiles[(-10,4)]='stone'
                else:terrain.tiles.pop((-10,4),None)
                self.now+=2;self.observe(self.scene(2,2,terrain,beat=True));current=self.next_move()
                rows.append(self.number)
                detail=self.scene_details()[-1]
                self.assertEqual((2,chain*2+refresh+1,refresh+1),
                                 (detail.validation,detail.continuous_count,detail.chain_count))
            self.ack(current);terrain=translated(terrain,1);self.observed_result(current,terrain)
            current=self.next_move()
        terrain=deepcopy(terrain);terrain.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,terrain,beat=True));rows.append(self.number)
        self.assertNotEqual(4,self.tick()[1].kind)
        details=self.scene_details();changes=self.scene_changes()
        self.assertEqual([rows[0],rows[-2],rows[-1]],[d.observed_capture_id for d in details])
        self.assertEqual([d.observed_capture_id for d in details],[c.observed_capture_id for c in changes])
        self.assertEqual((5,8,0),(details[-1].validation,details[-1].continuous_count,details[-1].chain_count))
        self.assertEqual((17,6,6),(self.status().reason,self.status().inputs,self.status().moves))
    def test_continuous_guards_reject_changed_world_and_strict_motion(self):
        cases=('unknown','pause','partial','visible','gold_set','gold_state','remote_protected',
               'origin_protected','near_protected','obstacle','motion_moved','motion_tween','motion_unknown')
        for case in cases:
            with self.subTest(case=case):
                self.fresh_engine();terrain,old=self.continuous_walk();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';state=2;gold=2
                if case=='unknown':state=0
                elif case=='pause':state=1
                elif case in ('partial','visible'):changed.goods=case
                elif case=='gold_set':changed.tiles[(-9,4)]='gold';changed.gold.add((-9,4))
                elif case=='gold_state':gold=1
                elif case=='remote_protected':changed.protected.add((-10,4))
                elif case=='origin_protected':changed.protected.add((0,0))
                elif case=='near_protected':changed.protected.add((-2,0))
                elif case=='obstacle':changed.tiles[(-1,0)]='stone'
                elif case=='motion_moved':changed.signature=translated(terrain,1).signature
                elif case=='motion_tween':changed.signature=translated(terrain,1,amount=8).signature
                elif case=='motion_unknown':changed.signature=bytes([40])*23296
                self.now+=2;self.observe(self.scene(state,gold,changed,beat=True));ready,new=self.tick()
                # TEST055: new observations/restrictions may replace the old
                # lease with a fresh ordinary choice; the old lease stays unsent.
                if case in ('gold_set','obstacle'):
                    self.assert_fresh_ticket(old,ready,new,changed)
                else:self.assertNotEqual(4,new.kind)
                self.assertEqual((2,2),(self.status().inputs,self.status().moves))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
                self.assertNotEqual(2,self.scene_details()[-1].validation)
                self.assertEqual(int(case in ('gold_set','obstacle')),self.scene_details()[-1].continuous_count)
                if case=='visible':self.assertEqual((1,1),(self.status().goods,self.status().reason))
                elif case in ('gold_set','obstacle'):self.assertEqual(0,self.status().reason)
                else:self.assertEqual(17,self.status().reason)
    def test_continuous_requires_full_route_decision_even_when_direction_matches(self):
        terrain,old=self.continuous_walk();changed=deepcopy(terrain);changed.tiles[(-5,0)]='stone'
        before=nav.choose(terrain,(-2,0));after=nav.choose(changed,(-2,0))
        self.assertEqual('left',before['direction']);self.assertEqual(before['direction'],after['direction'])
        self.assertNotEqual(before,after)
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick()
        self.assert_fresh_ticket(old,ready,new,changed)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_continuous_reason8_target_x_drift_keeps_original_action_and_beat(self):
        terrain,changed,old=self.continuous_vantage_drift()
        before=nav.choose(terrain,(-2,0));after=nav.choose(changed,(-2,0))
        self.assertEqual({'direction':'left','reason':'observed_floor_vantage','target':(-4,0)},before)
        self.assertEqual({**before,'target':(-3,0)},after)
        wait=self.motion_wait();self.now+=2;self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,old.direction,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,new.direction,self.motion_wait().deadline_ns))
        self.assertNotEqual(old.id,new.id);self.assertEqual(self.number,new.source_capture_id)
        self.assertEqual((2,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,old.not_before_ns,1))
        self.ack(new);self.observed_result(new,translated(changed,1))
        self.assertEqual((3,3,-3,0,3),(self.status().inputs,self.status().moves,self.status().x,
                                    self.status().y,self.status().last_ordinal))
    def test_continuous_reason8_target_y_drift_keeps_original_action_and_beat(self):
        initial=textured({**{(0,y):'floor' for y in range(-3,1)},(0,-4):'stone',
                          (0,-5):'door',(-1,-5):'gold',(1,-5):'gold',
                          (-4,-2):'stone',(5,1):'stone'})
        terrain,old=self.continuous_walk(moves=1,direction=3,terrain=initial);changed=deepcopy(terrain)
        changed.tiles[(0,-2)]='stone'
        before=nav.choose(terrain,(0,-1));after=nav.choose(changed,(0,-1))
        self.assertEqual({'direction':'up','reason':'observed_floor_vantage','target':(0,-2)},before)
        self.assertEqual({**before,'target':(0,-1)},after)
        wait=self.motion_wait();self.now+=2;self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,old.direction,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,new.direction,self.motion_wait().deadline_ns))
        self.assertNotEqual(old.id,new.id);self.assertEqual(self.number,new.source_capture_id)
        self.assertEqual((2,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
        self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,old.not_before_ns,1))
        self.ack(new);self.observed_result(new,translated(changed,3))
        self.assertEqual((2,2,0,-2,2),(self.status().inputs,self.status().moves,self.status().x,
                                    self.status().y,self.status().last_ordinal))
    def test_continuous_other_reason_target_x_and_y_drift_still_reject(self):
        for direction,transform,position in ((1,lambda x,y:(x,y),(-2,0)),
                                              (3,lambda x,y:(-y,x),(0,-2))):
            with self.subTest(direction=direction):
                self.fresh_engine()
                tiles={(x,0):'floor' for x in range(-5,1)}
                tiles.update({(x,y):'floor' for x in range(-5,-2) for y in range(-2,3)})
                for point in ((-5,-2),(-5,0),(-5,2)):tiles[point]='gold'
                initial=textured({transform(x,y):kind for (x,y),kind in tiles.items()})
                terrain,old=self.continuous_walk(direction=direction,terrain=initial)
                before=nav.choose(terrain,position);changed=deepcopy(terrain)
                changed.tiles[before['target']]='stone';after=nav.choose(changed,position)
                self.assertEqual('approach_gate',before['reason']);self.assertEqual(before['reason'],after['reason'])
                self.assertEqual(before['direction'],after['direction']);self.assertNotEqual(before['target'],after['target'])
                self.assertEqual(((-2,-1),(-2,1)) if direction==1 else ((-1,-2),(1,-2)),
                                 (before['target'],after['target']))
                self.now+=2;self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick()
                self.assert_fresh_ticket(old,ready,new,changed)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_continuous_two_reason8_drifts_save_each_new_source_decision(self):
        terrain,changed,original=self.continuous_vantage_drift();current=original;retired=[]
        wait=self.motion_wait()
        for attempt,x in enumerate((-4,-3,-2),1):
            changed=deepcopy(terrain);changed.tiles[(x,0)]='stone'
            before=nav.choose(terrain,(-2,0));after=nav.choose(changed,(-2,0))
            self.assertEqual(('left','observed_floor_vantage'),(before['direction'],before['reason']))
            self.assertEqual({**before,'target':(x+1,0)},after);self.assertNotEqual(before['target'],after['target'])
            self.now+=2;self.observe(self.scene(2,2,changed,beat=True));retired.append(current.id)
            ready,new=self.tick()
            if attempt<3:
                self.assertEqual((1,4),(ready,new.kind));current=new
                self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal,wait.deadline_ns),
                                 (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
                self.assertEqual(self.number,new.source_capture_id)
            else:self.assertNotEqual(4,new.kind)
            terrain=changed
        self.assertEqual([2,2,5],[d.validation for d in self.scene_details()])
        self.assertEqual([1,2,2],[d.chain_count for d in self.scene_details()])
        self.assertEqual((17,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        for old_id in retired:
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old_id,original.not_before_ns,1,0,1))
            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old_id,original.not_before_ns,1))
    def test_continuous_reason8_drift_keeps_deadline_motion_and_ownership_guards(self):
        for case in ('deadline_equal','deadline_expired','pending_expired','moved','tween','unknown',
                     'protected','gold','local_floor','gate','foreground','locked','owner','cancel'):
            with self.subTest(case=case):
                self.fresh_engine();terrain,changed,old=self.continuous_vantage_drift()
                if case=='moved':changed.signature=translated(terrain,1).signature
                elif case=='tween':changed.signature=translated(terrain,1,amount=8).signature
                elif case=='unknown':changed.signature=bytes([40])*23296
                elif case=='protected':changed.protected.add((-10,4))
                elif case=='gold':changed.tiles[(-9,4)]='gold';changed.gold.add((-9,4))
                elif case=='local_floor':changed.tiles[(-1,0)]='dirt'
                elif case=='gate':
                    for point in ((-1,-1),(-1,1)):changed.tiles[point]='gold';changed.gold.add(point)
                self.now=old.deadline_ns+(case=='deadline_expired') if case.startswith('deadline_') else self.now+2
                self.observe(self.scene(2,2,changed,beat=True))
                if case=='pending_expired':self.now=old.deadline_ns+1
                ready,new=self.tick()
                if case in ('deadline_equal','foreground','locked','owner','cancel'):
                    self.assertEqual((1,4),(ready,new.kind));self.assertEqual(old.deadline_ns,new.deadline_ns)
                    self.now=max(self.now,new.not_before_ns)
                    front,locked,owner=int(case!='foreground'),int(case=='locked'),int(case!='owner')
                    if case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    self.assertEqual(int(case=='deadline_equal'),
                                     self.lib.ng2_controller_begin(self.engine,new.id,self.now,front,locked,owner))
                elif case in ('gold','local_floor','gate'):
                    self.assert_fresh_ticket(old,ready,new,changed)
                else:self.assertNotEqual(4,new.kind)
                self.assertEqual((2,2),(self.status().inputs,self.status().moves))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,max(self.now,old.not_before_ns),1,0,1))
                self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,max(self.now,old.not_before_ns),1))
    def test_continuous_source_decision_and_each_after_pending_action_field_are_independent(self):
        # Fault only one public planner result after its real computation. The
        # controller, motion, beat and every other planner call stay production.
        wrapper=r'''
#include "NG2Core.h"
static int countdown,field;
void test_choice_fault(int call,int member){countdown=call;field=member;}
int ng2_real_choose(const NG2Scene *,int32_t,int32_t,const uint16_t *,size_t,const NG2Entrance *,NG2Decision *);
int ng2_choose(const NG2Scene *s,int32_t x,int32_t y,const uint16_t *visits,size_t n,
               const NG2Entrance *entrance,NG2Decision *out){
    int result=ng2_real_choose(s,x,y,visits,n,entrance,out);
    if(countdown>0&&--countdown==0&&result){
        if(field==1)out->direction=NG2_RIGHT;
        else if(field==2)out->reason=7;
        else if(field==3)++out->target_x;
        else if(field==4)++out->target_y;
        else if(field==5)out->obstacle=NG2_TILE_DIRT;
    }
    return result;
}
'''
        with tempfile.TemporaryDirectory(prefix='ngg2-controller-choice-fault-') as directory:
            directory=Path(directory);source=directory/'choice-fault.c';source.write_text(wrapper)
            navigation=directory/'navigation.c'
            navigation.write_text('#define ng2_choose ng2_real_choose\n#include "'+str(CORE/'NG2Navigation.c')+'"\n')
            library=directory/'controller.so'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fPIC','-shared',
                            '-I',str(CORE),str(source),str(navigation),str(CORE/'NG2Controller.c'),
                            str(CORE/'NG2Perception.c'),str(CORE/'NG2Beat.c'),'-lm','-o',str(library)],check=True)
            original=self.lib;self.lib=C.CDLL(str(library));self.addCleanup(setattr,self,'lib',original)
            for name in ('create','destroy','observe','tick','begin','complete','cancel','status','events','motion_wait'):
                name='ng2_controller_'+name;old=getattr(original,name);new=getattr(self.lib,name)
                new.argtypes=old.argtypes;new.restype=old.restype
            self.lib.test_choice_fault.argtypes=[C.c_int,C.c_int]
            for phase,fields in (('source',(1,2,3,4,5)),('after',(1,2,5)),('pending',(1,2,5))):
                for field in fields:
                    with self.subTest(phase=phase,field=field):
                        self.lib.test_choice_fault(0,0);self.fresh_engine()
                        terrain,changed,old=self.continuous_vantage_drift()
                        if phase=='pending':
                            # Keep targets equal so removing one action-field
                            # comparison cannot hide behind target inequality.
                            changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
                        if phase!='pending':
                            # Two optional-reference planner calls precede
                            # the unchanged authority before/after pair.
                            self.lib.test_choice_fault(3 if phase=='source' else 4,field)
                        self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
                        if phase=='pending':
                            self.assertEqual((2,1),(self.scene_details()[-1].validation,
                                                   self.scene_details()[-1].continuous_count))
                            self.lib.test_choice_fault(1,field)
                        elif phase=='after':
                            # A changed latest action may enter FRESH, but the
                            # one-call fault cannot survive pending all5 proof.
                            self.assertEqual((12,1),(self.scene_details()[-1].validation,
                                                    self.scene_details()[-1].continuous_count))
                        else:self.assertEqual((10,0),(self.scene_details()[-1].validation,
                                                     self.scene_details()[-1].continuous_count))
                        self.assertNotEqual(4,self.tick()[1].kind)
                        self.assertEqual((17,2,2),(self.status().reason,self.status().inputs,self.status().moves))
                        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_required_test051_actual77_79_reissue_same_up_after_synthetic_lead_in(self):
        manifest=json.loads((ROOT/'tests/test052-fixtures.json').read_text())
        self.assertEqual(('ngg2-test052-fixtures-v1',9),(manifest['schema'],manifest['count']))
        self.assertEqual([77,78,79],manifest['target_drift_capture_ids'])
        fixture_root=Path(os.environ.get('NECRO_TEST052_FIXTURE_ROOT','/workspace/analysis-evidence'))
        analyze=self.lib.ng2_analyze_rgba
        analyze.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Scene)]
        frames={};terrain={}
        for entry in manifest['images']:
            capture=entry['capture_id']
            if capture not in (67,77,78,79):continue
            path=fixture_root/entry['path'];self.assertTrue(path.is_file(),str(path))
            raw=path.read_bytes();self.assertEqual(entry['bytes'],len(raw))
            self.assertEqual(entry['sha256'],hashlib.sha256(raw).hexdigest())
            with Image.open(path) as image:
                rgba=image.convert('RGBA');pixels=rgba.tobytes();frame=Scene()
                self.assertEqual(0,analyze(pixels,len(pixels),rgba.width*4,C.byref(frame)))
                terrain[capture]=nav.scan(image.convert('RGB'))
            self.assertEqual((2,2,0),(frame.state,frame.gold_state,frame.goods));frames[capture]=frame
        self.assertEqual({67,77,78,79},set(frames))
        # Source55 was not recovered. This reverse-translated texture and
        # corrected synthetic origin establish lead only; captures67/77/78/79
        # below are unmodified real C perception results with a synthetic HUD clock.
        seed=translated(terrain[67],2);seed.tiles[(0,0)]='floor';self.fit(seed)
        def observe_actual(capture):
            frame=frames[capture];clock=self.scene(2,2,beat=True)
            for field in ('beat_valid','beat_remaining','beat_spacing','beat_center'):
                setattr(frame,field,getattr(clock,field))
            self.number=capture-1;self.assertEqual(1,self.observe(frame))
        for capture in (67,77):
            command=self.next_move();self.assertEqual(1,command.direction);self.ack(command)
            self.now=max(self.now+2,command.target_ns+80_000_002);observe_actual(capture)
        self.assertEqual((2,2,-2,0,1),(self.status().inputs,self.status().moves,self.status().x,
                                      self.status().y,self.status().lead_confirmed))
        original=self.next_move();wait=self.motion_wait();self.assertEqual((3,77),(original.direction,original.source_capture_id))
        current=original;retired=[]
        for capture in (78,79):
            self.now+=2;observe_actual(capture);retired.append(current.id);current=self.next_move()
            self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal,3,wait.deadline_ns),
                             (current.target_ns,current.not_before_ns,current.deadline_ns,current.ordinal,
                              current.direction,self.motion_wait().deadline_ns))
            self.assertEqual(capture,current.source_capture_id)
        self.assertEqual([2,2],[detail.validation for detail in self.scene_details()])
        self.assertEqual([1,2],[detail.chain_count for detail in self.scene_details()])
        self.assertEqual((0,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        for old_id in retired:
            self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old_id,current.not_before_ns,1,0,1))
            self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old_id,current.not_before_ns,1))
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,current.id,current.not_before_ns,1,0,1))
    def test_required_test052_three_flickers_before_initial_publication(self):
        manifest=json.loads((ROOT/'tests/test053-fixtures.json').read_text())
        self.assertEqual(('ngg2-test053-fixtures-v1',17),(manifest['schema'],manifest['count']))
        fixture_root=Path(os.environ.get('NECRO_TEST053_FIXTURE_ROOT','/workspace/analysis-evidence'))
        analyze=self.lib.ng2_analyze_rgba
        analyze.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Scene)]
        class Decision(C.Structure):
            _fields_=[(field,C.c_int32) for field in ('direction','reason','target_x','target_y','obstacle')]
        class Motion(C.Structure):
            _fields_=[(field,C.c_int32) for field in ('kind','dx','dy')]
        class Entrance(C.Structure):
            _fields_=[(field,C.c_int32) for field in ('valid','x','y','direction')]
        choose=self.lib.ng2_choose
        choose.argtypes=[C.POINTER(Scene),C.c_int32,C.c_int32,C.POINTER(C.c_uint16),C.c_size_t,C.POINTER(Entrance),C.POINTER(Decision)]
        motion=self.lib.ng2_motion;motion.argtypes=[C.POINTER(Scene),C.POINTER(Scene),C.c_int32,C.POINTER(Motion)]
        visits=(C.c_uint16*1089)();visits[16*33+16]=1
        frames={};terrain={}
        for entry in manifest['images']:
            capture=entry['capture_id']
            if 'native-c934567d1600449e8ede6529b3c78150/' not in entry['path'] or capture not in (34,35,36,37):continue
            path=fixture_root/entry['path'];self.assertTrue(path.is_file(),str(path));raw=path.read_bytes()
            self.assertEqual((entry['bytes'],entry['sha256']),(len(raw),hashlib.sha256(raw).hexdigest()))
            with Image.open(path) as image:
                rgba=image.convert('RGBA');pixels=rgba.tobytes();frame=Scene()
                self.assertEqual((896,414),rgba.size)
                self.assertEqual(0,analyze(pixels,len(pixels),rgba.width*4,C.byref(frame)))
                terrain[capture]=nav.scan(image.convert('RGB'))
            decision=Decision();entrance=Entrance()
            self.assertEqual(1,choose(C.byref(frame),0,0,visits,1089,C.byref(entrance),C.byref(decision)))
            self.assertEqual((1,8,-4,-1,1),tuple(getattr(decision,f) for f,_ in decision._fields_))
            frames[capture]=frame
        self.assertEqual({34,35,36,37},set(frames))
        for before,after,changed_count in ((34,35,4),(35,36,1),(36,37,1)):
            a,b=frames[before],frames[after];result=Motion()
            self.assertEqual(changed_count,sum(x!=y for x,y in zip(a.tiles,b.tiles)))
            self.assertEqual(bytes(a.protected_cells),bytes(b.protected_cells))
            self.assertEqual([x==2 for x in a.tiles],[x==2 for x in b.tiles])
            self.assertEqual(1,motion(C.byref(a),C.byref(b),1,C.byref(result)))
            self.assertEqual((2,0,0),(result.kind,result.dx,result.dy))
        # Only the real tile/texture scenes are replayed. Their HUD and clock
        # below are explicit synthetic lead-in, not missing future device data.
        self.fit(terrain[34]);self.now=3_840_000_000;self.assertEqual(0,self.tick()[0])
        target=self.status().next_target_ns;not_before=target-self.status().lead_ns
        for capture,now in zip((34,35,36,37),(3_850_000_000,3_930_000_000,4_010_000_000,4_090_000_000)):
            self.now=now;frame=frames[capture];clock=self.scene(2,2,beat=True)
            for field in ('beat_valid','beat_remaining','beat_spacing','beat_center'):setattr(frame,field,getattr(clock,field))
            self.number=capture-1;self.assertEqual(1,self.observe(frame));self.assertEqual(0,self.tick()[0])
            self.assertEqual((target,0,0),(self.status().next_target_ns,self.status().input_state,len(self.events())))
            self.assertEqual([],self.scene_changes())
        self.now=not_before-100_000_000;ready,original=self.tick()
        self.assertEqual((1,4,1,37,target),(ready,original.kind,original.direction,original.source_capture_id,original.target_ns))
        wait=self.motion_wait();current=original;frame=frames[37]
        for attempt in range(1,4):
            frame=Scene.from_buffer_copy(bytes(frame));frame.tiles[(4+5)*23+(-10+attempt)+11]=3
            self.now+=2;clock=self.scene(2,2,beat=True)
            for field in ('beat_valid','beat_remaining','beat_spacing','beat_center'):setattr(frame,field,getattr(clock,field))
            self.assertEqual(1,self.observe(frame));ready,new=self.tick()
            if attempt<3:
                self.assertEqual((1,4),(ready,new.kind));current=new
                self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,wait.deadline_ns),
                                 (new.target_ns,new.not_before_ns,new.deadline_ns,self.motion_wait().deadline_ns))
            else:self.assertNotEqual(4,new.kind)
        self.assertEqual([1,1,0],[row.replan_allowed for row in self.scene_changes()])
        self.assertEqual([1,2,2],[row.replan_count for row in self.scene_changes()])
        self.assertEqual((17,0,0),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,current.id,current.not_before_ns,1,0,1))
    def received_test053_reference_walk(self,after_capture):
        manifest=json.loads((ROOT/'tests/test054-fixtures.json').read_text())
        self.assertEqual(('ngg2-test054-fixtures-v1',17),(manifest['schema'],manifest['count']))
        fixture_root=Path(os.environ.get('NECRO_TEST054_FIXTURE_ROOT','/workspace/analysis-evidence'))
        analyze=self.lib.ng2_analyze_rgba
        analyze.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Scene)]
        frames={};terrain={}
        for entry in manifest['images']:
            capture=entry['capture_id']
            if capture not in (63,77,89,99,101,after_capture):continue
            path=fixture_root/entry['path'];self.assertTrue(path.is_file(),str(path));raw=path.read_bytes()
            self.assertEqual((entry['bytes'],entry['sha256']),(len(raw),hashlib.sha256(raw).hexdigest()))
            with Image.open(path) as image:
                rgba=image.convert('RGBA');pixels=rgba.tobytes();frame=Scene()
                self.assertEqual((896,414),rgba.size)
                self.assertEqual(0,analyze(pixels,len(pixels),rgba.width*4,C.byref(frame)))
                terrain[capture]=nav.scan(image.convert('RGB'))
            frames[capture]=frame
        self.assertEqual({63,77,89,99,101,after_capture},set(frames))
        # Missing initial source62 and real intermediate clocks are not
        # invented: fit uses an explicit synthetic63 scene/HUD lead-in.
        self.fit(terrain[63]);self.assertEqual(0,self.tick()[0])
        self.now=self.status().next_target_ns-self.status().lead_ns-100_000_000
        def observed(capture):
            frame=Scene.from_buffer_copy(bytes(frames[capture]));clock=self.scene(2,2,beat=True)
            for field in ('beat_valid','beat_remaining','beat_spacing','beat_center'):setattr(frame,field,getattr(clock,field))
            self.number=capture-1;self.assertEqual(1,self.observe(frame))
        observed(63)
        for direction,capture in ((1,77),(3,89),(3,99)):
            command=self.next_move();self.assertEqual(direction,command.direction);self.ack(command)
            self.now=max(self.now+2,command.target_ns+80_000_002);observed(capture)
        self.assertEqual((3,3,-1,-2,1),(self.status().inputs,self.status().moves,self.status().x,
                                      self.status().y,self.status().lead_confirmed))
        old=self.next_move();wait=self.motion_wait();self.assertEqual((3,99),(old.direction,old.source_capture_id))
        self.now+=2;observed(101);new=self.next_move()
        self.assertNotEqual(old.id,new.id)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
        self.assertEqual(101,new.source_capture_id)
        self.ack(new);self.now=max(self.now+2,new.target_ns+80_000_002);observed(after_capture)
        return old,new,wait
    def test_required_test053_original_reference_after_reissue(self):
        for capture in (110,111):
            with self.subTest(after_capture=capture):
                self.fresh_engine();self.received_test053_reference_walk(capture)
                self.assertEqual((4,4,-1,-3),(self.status().inputs,self.status().moves,self.status().x,self.status().y))
                row=self.motion_references()[-1]
                previous_ack=[e.command.id for e in self.events()[:-1] if e.outcome==2][-1]
                self.assertEqual((101,99,previous_ack),
                                 (row.authority_capture_id,row.reference_capture_id,row.reference_prefix))
                self.assertEqual((capture,1,0,1,1,99,1),(row.observed_capture_id,row.reference_eligible,
                                 row.primary_motion,row.fallback_attempted,row.fallback_motion,row.selected_capture_id,row.selected_motion))
    def test_motion_reference_unit_unknown_uses_only_matching_unit_fallback_all_directions(self):
        self.motion_selection_wrapper()
        for direction,(dx,dy) in DIRS.items():
            with self.subTest(direction=direction):
                self.lib.test_motion_reset();self.fresh_engine();_,changed,old,new=self.qualified_reference_reissue(direction)
                previous_ack=[e.command.id for e in self.events() if e.outcome==2][-1]
                self.ack(new);row=self.motion_references()[-1]
                self.assertEqual((new.id,new.source_capture_id,old.source_capture_id,old.source_start_ns,previous_ack,0,1,0,0,0,new.source_capture_id,0),
                                 tuple(getattr(row,name) for name,_ in row._fields_))
                self.lib.test_motion_force(1,0,0,0,1,1,dx,dy)
                self.observed_result(new,translated(changed,direction));row=self.motion_references()[-1]
                self.assertEqual((2,2,2*dx,2*dy),(self.status().inputs,self.status().moves,self.status().x,self.status().y))
                self.assertEqual((2,1,0,1,1,old.source_capture_id,1),(self.lib.test_motion_calls(),row.reference_eligible,
                                 row.primary_motion,row.fallback_attempted,row.fallback_motion,row.selected_capture_id,row.selected_motion))
                self.assertEqual((1,1,dx,dy),(self.motion_wait().attempts,self.events()[-1].motion,
                                             self.events()[-1].dx,self.events()[-1].dy))
    def test_motion_reference_unit_known_primary_results_never_call_fallback(self):
        self.motion_selection_wrapper()
        for primary in (1,2,3,4,5,6,7):
            with self.subTest(primary=primary):
                self.lib.test_motion_reset();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue()
                self.ack(new);self.lib.test_motion_force(1,primary,0,-1 if primary==1 else 0,1,1,0,-1)
                self.observed_result(new,translated(changed,3));row=self.motion_references()[-1]
                self.assertEqual((1,primary,0,0,new.source_capture_id,primary),(self.lib.test_motion_calls(),
                                 row.primary_motion,row.fallback_attempted,row.fallback_motion,row.selected_capture_id,row.selected_motion))
                self.assertEqual(1+(primary==1),self.status().moves)
    def test_motion_reference_unit_nonmatching_fallback_never_credits_or_spends_an_extra_attempt(self):
        self.motion_selection_wrapper()
        for returned,kind,dx,dy in ((1,0,0,0),(1,2,0,0),(1,3,0,0),(1,4,0,0),
                                    (1,5,0,0),(1,6,0,0),(1,7,0,0),(1,1,1,0),
                                    (1,1,0,-2),(0,1,0,-1)):
            with self.subTest(returned=returned,kind=kind,dx=dx,dy=dy):
                self.lib.test_motion_reset();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue()
                self.ack(new);self.lib.test_motion_force(1,0,0,0,returned,kind,dx,dy)
                self.observed_result(new,translated(changed,3));row=self.motion_references()[-1]
                self.assertEqual((2,1,1,0),(self.status().inputs,self.status().moves,self.motion_wait().attempts,self.motion_wait().last_motion))
                self.assertEqual((2,0,1,kind if returned else 0,new.source_capture_id,0),
                                 (self.lib.test_motion_calls(),row.primary_motion,row.fallback_attempted,
                                  row.fallback_motion,row.selected_capture_id,row.selected_motion))
    def test_motion_reference_unit_mask_zero_disqualification_is_sticky(self):
        self.motion_selection_wrapper();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue()
        source=new.source_capture_id;signature=changed.signature
        shifted=bytearray(signature);shifted[5000]=(shifted[5000]+1)%256;changed.signature=bytes(shifted)
        self.lib.test_motion_once(1,1,0,0,0);self.now+=2
        self.observe(self.scene(2,2,changed,beat=True))
        self.assertEqual((1,new.id),(self.status().input_state,self.status().current_command_id))
        self.assertEqual(1,len(self.scene_changes()))
        self.lib.test_motion_reset();changed.signature=signature;self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));self.assertEqual(1,len(self.scene_changes()))
        self.ack(new);row=self.motion_references()[-1]
        self.assertEqual((source,0),(row.authority_capture_id,row.reference_eligible))
        self.lib.test_motion_force(1,0,0,0,1,1,0,-1);self.observed_result(new,translated(changed,3))
        row=self.motion_references()[-1]
        self.assertEqual((1,0,0,1),(self.lib.test_motion_calls(),row.reference_eligible,row.fallback_attempted,self.status().moves))
    def test_motion_reference_unit_pending_signature_change_is_checked_before_reserve(self):
        self.motion_selection_wrapper();self.fresh_engine();terrain,old=self.continuous_walk(moves=1,direction=3)
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        self.observe(self.scene(2,2,changed,beat=True))
        self.assertEqual((0,0),(self.status().input_state,self.status().current_command_id))
        self.assertEqual([2],[row.validation for row in self.scene_details()])
        signature=changed.signature;modified=bytearray(signature);modified[5000]=(modified[5000]+1)%256
        changed.signature=bytes(modified);self.lib.test_motion_once(1,1,0,0,0);self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));self.assertEqual(1,self.lib.test_motion_calls())
        self.lib.test_motion_reset();changed.signature=signature;self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns),(new.target_ns,new.not_before_ns,new.deadline_ns))
        self.ack(new);self.lib.test_motion_force(1,0,0,0,1,1,0,-1);self.observed_result(new,translated(changed,3))
        row=self.motion_references()[-1]
        self.assertEqual((1,0,0,1),(self.lib.test_motion_calls(),row.reference_eligible,row.fallback_attempted,self.status().moves))
    def test_motion_reference_unit_second_reissue_checks_original_directly_and_preserves_legacy(self):
        self.motion_selection_wrapper();self.fresh_engine();_,changed,original,current=self.qualified_reference_reissue()
        # Force only original->latest proof UNKNOWN. Neighbouring current->
        # latest uses unchanged actual C and remains BLOCKED/legacy-allowed.
        changed.tiles[(-9,4)]='stone';self.lib.test_motion_once(1,1,0,0,0);self.now+=2
        self.observe(self.scene(2,2,changed,beat=True));replacement=self.next_move()
        self.assertEqual([2,2],[row.validation for row in self.scene_details()])
        self.assertEqual((original.target_ns,original.not_before_ns,original.deadline_ns,original.ordinal),
                         (replacement.target_ns,replacement.not_before_ns,replacement.deadline_ns,replacement.ordinal))
        self.assertNotEqual(current.id,replacement.id)
        self.lib.test_motion_reset();self.ack(replacement)
        self.lib.test_motion_force(1,0,0,0,1,1,0,-1);self.observed_result(replacement,translated(changed,3))
        row=self.motion_references()[-1]
        self.assertEqual((original.source_capture_id,0,0,1),(row.reference_capture_id,row.reference_eligible,
                         row.fallback_attempted,self.status().moves))
    def test_motion_reference_unit_same_goods_frame_keeps_reference_until_move_credit(self):
        self.motion_selection_wrapper();self.fresh_engine();_,changed,old,new=self.qualified_reference_reissue()
        self.ack(new);goods=translated(changed,3);goods.goods='visible'
        self.lib.test_motion_force(1,0,0,0,1,1,0,-1);self.observed_result(new,goods)
        row=self.motion_references()[-1]
        self.assertEqual((2,2,1,1,old.source_capture_id),(self.status().inputs,self.status().moves,self.status().goods,
                         row.fallback_attempted,row.selected_capture_id))
        ready,pause=self.tick();self.assertEqual((1,2),(ready,pause.kind))
    def test_motion_reference_unit_three_attempts_keep_one_ack_row_and_original_deadline(self):
        self.motion_selection_wrapper();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue()
        self.ack(new);deadline=self.motion_wait().deadline_ns
        for attempt in range(1,4):
            self.lib.test_motion_force(1,0,0,0,1,0,0,0)
            if attempt==1:self.observed_result(new,translated(changed,3))
            else:
                self.now+=2;self.observe(self.scene(2,2,translated(changed,3),beat=True))
            self.assertEqual((2,attempt,deadline),(len(self.motion_references()),self.motion_wait().attempts,self.motion_wait().deadline_ns))
            row=self.motion_references()[-1]
            self.assertEqual((self.number,1,0),(row.observed_capture_id,row.fallback_attempted,row.selected_motion))
        self.assertEqual((10,1,2),(self.status().reason,self.status().moves,self.status().inputs))
    def test_motion_reference_diagnostics_ignore_unacked_unknown_and_nonmove_events(self):
        self.observe(self.scene());ready,resume=self.tick();self.assertEqual((1,1),(ready,resume.kind))
        self.assertEqual([],self.motion_references());self.ack(resume);self.assertEqual([],self.motion_references())
        self.now+=100_000_000;self.observe(self.scene(2,2,textured(),beat=True));self.fit()
        first=self.next_move();self.assertEqual([],self.motion_references())
        self.now=first.not_before_ns;self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,first.id,self.now,1,0,1))
        self.now+=1;self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,first.id,self.now,-1))
        self.assertEqual((11,[]),(self.status().reason,self.motion_references()))
    def test_motion_reference_diagnostics_initial_and_retune_never_acquire_reference(self):
        terrain=self.fit();first=self.next_move();self.ack(first)
        self.assertEqual((0,0,0),(self.motion_references()[-1].reference_capture_id,
                         self.motion_references()[-1].reference_start_ns,self.motion_references()[-1].reference_prefix))
        self.observed_result(first,terrain)
        self.assertEqual((75_000_000,0,2,0),(self.status().lead_ns,self.status().lead_confirmed,
                         self.motion_references()[-1].primary_motion,self.motion_references()[-1].fallback_attempted))
        retune=self.next_move();self.ack(retune);self.observed_result(retune,translated(terrain,retune.direction))
        row=self.motion_references()[-1]
        self.assertEqual((2,1,0,0,0),(len(self.motion_references()),self.status().moves,
                         row.reference_capture_id,row.reference_eligible,row.fallback_attempted))
    def test_motion_reference_diagnostics_preserve_unassessed_and_previous_assessment_on_goods(self):
        self.motion_selection_wrapper()
        for prior in (False,True):
            with self.subTest(prior=prior):
                self.lib.test_motion_reset();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue();self.ack(new)
                if prior:
                    self.lib.test_motion_force(1,0,0,0,1,0,0,0);self.observed_result(new,translated(changed,3))
                    previous=self.motion_references()[-1];self.now=self.motion_wait().deadline_ns+1
                else:
                    previous=self.motion_references()[-1];self.now+=2
                    self.assertLess(self.now,new.target_ns+80_000_000)
                goods=translated(changed,3);goods.goods='visible';self.lib.test_motion_reset()
                self.observe(self.scene(2,2,goods,beat=True));row=self.motion_references()[-1]
                self.assertEqual(bytes(previous),bytes(row))
                self.assertEqual((1,1,0),(self.status().goods,self.status().moves,self.lib.test_motion_calls()))
                self.assertEqual((self.number,0),(self.events()[-1].observed_capture_id,self.events()[-1].motion))
                self.assertLess(row.observed_capture_id,self.events()[-1].observed_capture_id)
                self.assertEqual(0 if not prior else previous.observed_capture_id,row.observed_capture_id)
    def test_motion_reference_unit_prefix_time_and_control_guards_do_not_assess_or_retry(self):
        self.motion_selection_wrapper()
        for case in ('unstable','prefix','old_capture','early','late','cancel','foreground','locked','owner'):
            with self.subTest(case=case):
                self.lib.test_motion_reset();self.fresh_engine();_,changed,_,new=self.qualified_reference_reissue();self.ack(new)
                self.lib.test_motion_force(1,0,0,0,1,1,0,-1);self.now=max(self.now+2,new.target_ns+80_000_002)
                kwargs={}
                if case=='unstable':kwargs['stable']=0
                elif case=='prefix':kwargs['prefix']=0
                elif case=='old_capture':kwargs['number']=self.number
                elif case=='early':self.now=new.target_ns+80_000_001
                elif case=='late':self.now=self.motion_wait().deadline_ns+1
                elif case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                else:self.tick(front=int(case!='foreground'),locked=int(case=='locked'),owner=int(case!='owner'))
                self.observe(self.scene(2,2,translated(changed,3),beat=True),**kwargs)
                row=self.motion_references()[-1]
                self.assertEqual((1,0,0,0),(self.status().moves,self.lib.test_motion_calls(),row.observed_capture_id,row.fallback_attempted))
                self.assertEqual(2,len([e for e in self.events() if e.outcome==2 and e.command.kind==4]))
    def test_motion_reference_unit_no_fallback_without_reissue_or_across_next_ordinal(self):
        self.motion_selection_wrapper();self.fresh_engine();terrain,old=self.continuous_walk(moves=1,direction=1)
        self.ack(old);row=self.motion_references()[-1]
        self.assertEqual((old.source_capture_id,0),(row.reference_capture_id,row.reference_eligible))
        self.lib.test_motion_force(1,0,0,0,1,1,-1,0);self.observed_result(old,translated(terrain,1))
        self.assertEqual((1,1,0),(self.status().moves,self.lib.test_motion_calls(),self.motion_references()[-1].fallback_attempted))
        # Establish the first definite result, then create the next logical
        # ordinal. Its candidate must come from that new authority image.
        self.lib.test_motion_force(1,1,-1,0,1,1,-1,0);self.now+=2
        terrain=translated(terrain,1);self.observe(self.scene(2,2,terrain,beat=True));self.lib.test_motion_reset()
        self.assertEqual(2,self.status().moves);next_command=self.next_move()
        self.ack(next_command);row=self.motion_references()[-1]
        self.assertEqual((next_command.source_capture_id,next_command.source_capture_id,0),
                         (row.authority_capture_id,row.reference_capture_id,row.reference_eligible))
        self.assertNotEqual(old.source_capture_id,row.reference_capture_id)
    def test_motion_reference_unit_reason8_drift_keeps_authority_without_optional_reference(self):
        self.motion_selection_wrapper();self.fresh_engine();terrain,changed,old=self.continuous_vantage_drift()
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));new=self.next_move();self.ack(new)
        self.assertEqual((2,1),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count))
        self.lib.test_motion_force(1,0,0,0,1,1,-1,0);self.observed_result(new,translated(changed,1))
        row=self.motion_references()[-1]
        self.assertEqual((old.source_capture_id,0,0,2),(row.reference_capture_id,row.reference_eligible,row.fallback_attempted,self.status().moves))
    def assert_reference_choice_guard(self,field,call):
        self.lib.test_motion_reset();self.fresh_engine();terrain,old=self.continuous_walk(moves=1,direction=3)
        changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone';self.now+=2
        self.lib.test_reference_choice_fault(call,field);self.observe(self.scene(2,2,changed,beat=True))
        new=self.next_move();self.assertNotEqual(old.id,new.id)
        self.assertEqual(2,self.scene_details()[-1].validation)
        self.ack(new);self.lib.test_motion_force(1,0,0,0,1,1,0,-1)
        self.observed_result(new,translated(changed,3));row=self.motion_references()[-1]
        self.assertEqual(0,row.reference_eligible,'reference_choice_field_'+str(field))
        self.assertEqual((0,1),(row.fallback_attempted,self.status().moves))
    def test_motion_reference_unit_each_full_decision_field_is_required_without_revoking_authority(self):
        self.motion_selection_wrapper()
        for field in range(1,6):
            for call in (1,2):
                with self.subTest(field=field,original_or_latest=call):self.assert_reference_choice_guard(field,call)
    def test_motion_reference_real_controller_full_decision_guard_mutations_are_detected(self):
        self.motion_selection_wrapper();production=self.lib;directory=Path(type(self).temp.name)
        controller=(CORE/'NG2Controller.c').read_text()
        start=controller.index('static int same_choice(');end=controller.index('static int same_continuous_action(',start)
        predicates=('a->direction==b->direction','a->reason==b->reason','a->target_x==b->target_x',
                    'a->target_y==b->target_y','a->obstacle==b->obstacle')
        for field,predicate in enumerate(predicates,1):
            with self.subTest(field=field):
                block=controller[start:end];self.assertEqual(1,block.count(predicate))
                mutated=controller[:start]+block.replace(predicate,'1')+controller[end:]
                source=directory/('reference-field-'+str(field)+'.c');source.write_text(mutated)
                library=directory/('reference-field-'+str(field)+'.so')
                subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fPIC','-shared',
                                '-I',str(CORE),str(directory/'selection-wrapper.c'),str(directory/'selection-navigation.c'),str(source),
                                str(CORE/'NG2Perception.c'),str(CORE/'NG2Beat.c'),'-lm','-o',str(library)],check=True)
                self.lib=C.CDLL(str(library))
                for name in ('create','destroy','observe','tick','begin','complete','cancel','status','events','motion_wait'):
                    name='ng2_controller_'+name;old=getattr(production,name);new=getattr(self.lib,name)
                    new.argtypes=old.argtypes;new.restype=old.restype
                with self.assertRaisesRegex(AssertionError,'reference_choice_field_'+str(field)) as caught:
                    self.assert_reference_choice_guard(field,1)
                print('TEST054 actual Controller guard mutant detected: '+json.dumps({'field':field,
                      'controller_sha256':hashlib.sha256(mutated.encode()).hexdigest(),'assertion':str(caught.exception)}),flush=True)
        self.lib=production
    def test_continuous_rejects_reason_only_change_under_same_gold_and_target(self):
        terrain,old=self.continuous_walk();changed=deepcopy(terrain);changed.tiles.pop((-6,0))
        before=nav.choose(terrain,(-2,0));after=nav.choose(changed,(-2,0))
        self.assertEqual({'direction':'left','reason':'approach_gate','target':(-5,0)},before)
        self.assertEqual({**before,'reason':'observed_floor_vantage'},after)
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual((10,0),(self.scene_details()[-1].validation,self.scene_details()[-1].continuous_count))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_continuous_prefix_stability_and_started_ack_unknown_never_reissue(self):
        for case in ('unstable','prefix','old_id','started','ack','unknown'):
            with self.subTest(case=case):
                self.fresh_engine();terrain,old=self.continuous_walk();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';args={}
                if case=='unstable':args['stable']=0
                elif case=='prefix':args['prefix']=0
                elif case=='old_id':args['number']=self.number
                else:
                    self.now=old.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                    if case!='started':
                        self.now+=1;self.lib.ng2_controller_complete(self.engine,old.id,self.now,1 if case=='ack' else -1)
                        if case=='ack':self.prefix=old.id
                self.now+=2;self.observe(self.scene(2,2,changed,beat=True),**args)
                self.assertEqual([],self.scene_details());self.assertEqual(0,self.tick()[0])
                self.assertEqual(3,len([e for e in self.events() if e.command.kind==4]))
    def test_continuous_original_deadline_equality_and_expiry(self):
        for late in (0,1):
            with self.subTest(late=late):
                self.fresh_engine();terrain,old=self.continuous_walk();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';self.now=old.deadline_ns+late
                self.observe(self.scene(2,2,changed,beat=True));ready,new=self.tick()
                if late:
                    self.assertNotEqual(4,new.kind);self.assertEqual(6,self.scene_details()[-1].validation)
                else:
                    self.assertEqual((1,4),(ready,new.kind));self.assertEqual(old.deadline_ns,new.deadline_ns)
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
    def test_continuous_expiry_after_revalidation_never_searches_later_beat(self):
        terrain,old=self.continuous_walk();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));self.now=old.deadline_ns+1
        self.assertEqual(0,self.tick()[0]);self.assertEqual(9,self.status().reason)
        self.now+=PERIOD;self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(3,len([e for e in self.events() if e.command.kind==4]))
    def test_continuous_refresh_preserves_original_period_and_visual_horizon_after_hud_update(self):
        terrain,old=self.continuous_walk();wait=self.motion_wait();changed=deepcopy(terrain)
        changed.tiles[(-10,4)]='stone';self.now+=2
        scene=self.scene(2,2,changed,beat=True);scene.beat_remaining=(scene.beat_remaining+.001)%1
        self.observe(scene);new=self.next_move()
        self.assertNotEqual(PERIOD,self.status().beat_period_ns)
        self.assertGreater(new.source_start_ns,old.source_start_ns)
        self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                         (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
        self.ack(new);self.observed_result(new,translated(changed,1))
        next_command=self.next_move()
        self.assertEqual(new.target_ns+PERIOD-150_000_000+10_000_000,next_command.deadline_ns)
    def test_continuous_phase_revocation_and_stale_horizons_never_resend(self):
        for case in ('phase_changed','source_expired','model_expired'):
            with self.subTest(case=case):
                self.fresh_engine();terrain,old=self.continuous_walk();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';self.now+=2
                self.observe(self.scene(2,2,changed,beat=True));new=self.next_move()
                if case=='phase_changed':
                    self.now+=2;scene=self.scene(2,2,changed,beat=True)
                    scene.beat_remaining=(scene.beat_remaining+.2)%1;self.observe(scene)
                    self.now=new.not_before_ns
                elif case=='source_expired':self.now=old.source_start_ns+3*SECOND+1
                else:self.now=old.phase_sample_ns+3*SECOND+1
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                self.assertEqual((2,2),(self.status().inputs,self.status().moves))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                self.assertNotEqual(4,self.tick()[1].kind)
    def test_continuous_guard_or_cancel_after_revalidation_rejects_new_and_old_ids(self):
        for case,front,locked,owner,reason in (('foreground',0,0,1,3),('locked',1,1,1,4),
                                             ('owner',1,0,0,5),('cancel',1,0,1,2)):
            with self.subTest(case=case):
                self.fresh_engine();terrain,old=self.continuous_walk();changed=deepcopy(terrain)
                changed.tiles[(-10,4)]='stone';self.now+=2;self.observe(self.scene(2,2,changed,beat=True))
                new=self.next_move();self.now=new.not_before_ns
                if case=='cancel':self.lib.ng2_controller_cancel(self.engine,self.now,2)
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,front,locked,owner))
                self.assertEqual((reason,2),(self.status().reason,self.status().inputs))
                self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
                self.assertEqual(0,self.lib.ng2_controller_complete(self.engine,old.id,self.now,1))
    def test_continuous_pending_change_stops_instead_of_accumulating_refreshes(self):
        terrain,old=self.continuous_walk();terrain=deepcopy(terrain);terrain.tiles[(-10,4)]='stone'
        self.now+=2;self.observe(self.scene(2,2,terrain,beat=True))
        terrain.tiles[(-9,4)]='stone';self.now+=2;self.observe(self.scene(2,2,terrain,beat=True))
        self.assertNotEqual(4,self.tick()[1].kind);self.assertEqual(17,self.status().reason)
        self.assertEqual([2,4],[d.validation for d in self.scene_details()])
        self.assertEqual([1,1],[d.continuous_count for d in self.scene_details()])
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,old.not_before_ns,1,0,1))
    def test_scene_detail_query_is_bounded_and_leaves_existing_abi_unchanged(self):
        self.assertEqual((23864,192,128,80,144),tuple(C.sizeof(x) for x in (Scene,Status,Event,SceneChange,SceneDetail)))
        self.assertEqual([],self.scene_details());terrain,old=self.continuous_walk();changed=deepcopy(terrain)
        for x in range(-11,-5):changed.tiles[(x,4)]='stone'
        changed.protected.add((-11,4))
        self.now+=2;self.observe(self.scene(2,2,changed,beat=True));detail=self.scene_details()[0]
        self.assertEqual((9,4,2),(detail.validation,detail.cell_count,detail.omitted_cells))
        self.assertEqual([(-11,4),(-10,4),(-9,4),(-8,4)],[(c.x,c.y) for c in detail.cells])
        self.assertEqual((0,3,0,1),(detail.cells[0].tile_before,detail.cells[0].tile_after,
                                  detail.cells[0].protected_before,detail.cells[0].protected_after))
        query=self.lib.ng2_controller_scene_details
        guarded=(SceneDetail*2)();C.memset(C.byref(guarded),0xa5,C.sizeof(guarded));sentinel=bytes(guarded[1])
        self.assertEqual(0,query(self.engine,guarded,0));self.assertEqual(bytes([0xa5])*C.sizeof(guarded),bytes(guarded))
        self.assertEqual(1,query(self.engine,guarded,1));self.assertEqual(sentinel,bytes(guarded[1]))
        self.assertEqual(0,query(self.engine,None,3));self.assertEqual(0,query(None,guarded,3))
        self.fresh_engine();terrain=self.fit();self.next_move()
        for attempt in range(3):
            terrain=deepcopy(terrain);terrain.tiles[(-10+attempt,4)]='stone'
            self.now+=2;self.observe(self.scene(2,2,terrain,beat=True));self.tick()
        self.assertEqual(3,len(self.scene_details()))
        for capacity in (0,1,2,3,C.c_size_t(-1).value):
            guarded=(SceneDetail*4)();C.memset(C.byref(guarded),0xa5,C.sizeof(guarded))
            expected=min(capacity,3)
            self.assertEqual(expected,query(self.engine,guarded,capacity))
            self.assertEqual(bytes([0xa5])*C.sizeof(SceneDetail)*(4-expected),
                             bytes(guarded)[expected*C.sizeof(SceneDetail):])
            self.assertEqual([d.command_id for d in self.scene_details()][:expected],
                             [guarded[i].command_id for i in range(expected)])
    def reconstructed_public_beat_model(self,rows,allow_refit=True):
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
                    self.assertTrue(allow_refit or len(samples)==4,"valid-track fixture unexpectedly requires a new fit")
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
        self.observe(self.scene(2,2,terrain,beat=True));self.now=6_830_000_000
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
    def test_initial_replan_is_disabled_after_blocked_sent_trial(self):
        terrain=self.fit();first=self.next_move();self.ack(first);self.observed_result(first,terrain)
        self.assertEqual((1,0),(self.status().inputs,self.status().lead_confirmed))
        current=self.next_move();changed=deepcopy(terrain);changed.tiles[(-10,4)]='stone'
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
        # This >.08 HUD jump now poisons the first slot instead of silently
        # replacing the invalid tracked model by another successful fit.
        self.assertEqual((8,0),(self.status().reason,self.status().inputs))
        self.assertEqual((old.target_ns,old.not_before_ns,old.ordinal),(new.target_ns,new.not_before_ns,new.ordinal))
        self.now=new.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.assertEqual(0,self.status().inputs)
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,old.id,self.now,1,0,1))
    def test_initial_replan_phase_alignment_boundary_is_inclusive_for_original_period(self):
        # The old >.08 single HUD jump needed a new fit. An armed slot now
        # poisons on that failure. Use genuine valid tracking with gradual
        # <=.08 changes and an original515ms period to reach the same inclusive
        # .08-original-period boundary without leaving the fixed profile.
        cases=((.1018182,525_214_523,41_199_997,1),
               (.1018182781279141,525_214_524,41_200_000,1),
               (.10181827812791411,525_214_525,41_200_005,0))
        for replan in (False,True):
            for bias,expected_period,expected_delta,allowed in cases:
                with self.subTest(replan=replan,bias=bias):
                    self.fresh_engine();terrain=textured();rows=[];original_period=515_000_000
                    def observed(bias=0):
                        scene=self.scene(2,2,terrain,beat=True)
                        scene.beat_remaining=(((5*SECOND-(self.now-1))%original_period)/original_period+bias)%1
                        rows.append((self.now,scene.beat_remaining));self.observe(scene)
                    for _ in range(4):
                        self.now+=700_000_000;observed()
                    self.assertEqual(original_period,self.status().beat_period_ns)
                    old=self.next_move();self.assertEqual(4_485_000_000,old.target_ns);wait=self.motion_wait()
                    if replan:terrain.tiles[(-10,4)]='stone'
                    self.now+=2;observed(.04);ready,new=self.tick()
                    if replan:self.assertEqual((1,4),(ready,new.kind))
                    else:
                        self.assertEqual(0,ready);new=old
                        self.assertEqual([],self.scene_changes())
                    for step in (.07,.09,.11,bias):
                        self.now+=2;observed(step)
                    self.assertEqual(expected_period,self.status().beat_period_ns)
                    model=self.reconstructed_public_beat_model(rows,allow_refit=False)
                    self.assertEqual(expected_period,model.period_ns)
                    forward=(model.epoch_ns-old.target_ns)%model.period_ns
                    aligned=old.target_ns+forward if forward<=model.period_ns//2 else old.target_ns-(model.period_ns-forward)
                    self.assertEqual(expected_delta,abs(aligned-old.target_ns))
                    self.assertEqual((old.target_ns,old.not_before_ns,old.deadline_ns,old.ordinal,wait.deadline_ns),
                                     (new.target_ns,new.not_before_ns,new.deadline_ns,new.ordinal,self.motion_wait().deadline_ns))
                    self.assertEqual(0 if allowed else 8,self.status().reason)
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
        self.now=6_830_000_000
        command=self.next_move();self.assertEqual(7_080_000_000,command.target_ns)
        self.now=command.not_before_ns+1
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
    def test_input_end_exactly_on_source_horizon_is_allowed(self):
        terrain=self.fit();self.now=4_130_000_002
        self.observe(self.scene(2,2,terrain,beat=True));self.now=6_830_000_000
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
    def test_three_unknown_motion_observations_stop_without_lead_retry(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=deepcopy(terrain);after.signature=bytes([40])*23296
        for n in range(3):self.observed_result(command,after,offset=80_000_002+n*10_000_000)
        self.assertEqual((self.status().reason,self.status().lead_ns,self.status().lead_confirmed),(10,150_000_000,0))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
        self.assertEqual((3,0),(self.motion_wait().attempts,self.motion_wait().active))
        self.now+=10_000_000;self.observe(self.scene(2,2,translated(terrain,3),beat=True))
        self.assertEqual(0,self.status().moves)
        self.assertEqual(3,self.motion_wait().attempts)
    def test_acknowledged_unknown_waits_for_same_command_moved_observation(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        unknown=translated(terrain,command.direction);unknown.signature=bytes([40])*23296
        self.observed_result(command,unknown)
        self.assertEqual((self.status().inputs,self.status().moves,self.status().input_state,self.status().reason),(1,0,3,0))
        self.assertEqual(command.id,self.status().current_command_id)
        self.assertEqual(0,self.tick()[0])
        self.now+=10_000_000
        self.observe(self.scene(2,2,translated(terrain,command.direction),beat=True))
        self.assertEqual((self.status().inputs,self.status().moves,self.status().input_state,self.status().reason),(1,1,0,0))
        self.assertEqual(command.id,self.events()[-1].command.id)
    def test_motion_wait_diagnostic_retains_each_eligible_capture_and_fixed_deadline(self):
        self.assertEqual(bytes(MotionWait()),bytes(self.motion_wait()))
        terrain=self.fit();command=self.next_move();reserved=self.motion_wait()
        self.assertEqual((command.id,command.source_capture_id,0,0,0),
                         (reserved.command_id,reserved.source_capture_id,reserved.last_capture_id,reserved.attempts,reserved.active))
        self.assertEqual(command.target_ns+PERIOD-150_000_000+10_000_000,reserved.deadline_ns)
        self.ack(command);self.assertEqual(1,self.motion_wait().active)
        unknown=translated(terrain,command.direction);unknown.signature=bytes([40])*23296
        for n in range(2):
            self.observed_result(command,unknown,offset=80_000_002+n*10_000_000)
            record=self.motion_wait()
            self.assertEqual((command.id,command.source_capture_id,self.number,reserved.deadline_ns,n+1,0,1),
                             (record.command_id,record.source_capture_id,record.last_capture_id,record.deadline_ns,
                              record.attempts,record.last_motion,record.active))
            self.assertEqual(self.number,self.events()[-1].observed_capture_id)
        self.observed_result(command,translated(terrain,command.direction),offset=100_000_002)
        record=self.motion_wait()
        self.assertEqual((3,1,0,self.number),(record.attempts,record.last_motion,record.active,record.last_capture_id))
        self.assertEqual((1,1),(self.status().inputs,self.status().moves))
    def test_full_resolution_thirty_five_then_thirty_six_pixels_all_four_directions(self):
        # Raster at full resolution before taking the real 4px sparse signature.
        # 35px changes the sampling phase; it is neither the existing 32px tween
        # nor proof of a completed tile. No threshold is modified for this test.
        rng=random.Random(46046)
        raster=Image.frombytes('L',(896,414),bytes(rng.randrange(20,100) for _ in range(896*414)))
        def signature(image):
            raw=image.tobytes()
            return b''.join(raw[y*896:(y+1)*896:4] for y in range(0,414,4))
        for direction,(dx,dy) in DIRS.items():
            with self.subTest(direction=direction):
                self.fresh_engine()
                source=textured()
                tiles={(-dy*x-dx*y,dx*x-dy*y):kind for (x,y),kind in source.tiles.items()}
                terrain=nav.Scene(tiles,{p for p,k in tiles.items() if k=='gold'},'unknown',set(),signature(raster))
                self.fit(terrain);command=self.next_move();self.assertEqual(direction,command.direction);self.ack(command)
                for attempt,pixels in enumerate((35,36),1):
                    changed=translated(terrain,direction)
                    image=Image.new('L',raster.size);image.paste(raster,(-pixels*dx,-pixels*dy));changed.signature=signature(image)
                    self.observed_result(command,changed,offset=100_000_002+attempt*10_000_000)
                    if pixels==35:
                        self.assertEqual((0,3,0),(self.status().moves,self.status().input_state,self.motion_wait().last_motion))
                        self.assertEqual(0,self.tick()[0])
                    else:
                        self.assertEqual((1,dx,dy,0),(self.status().moves,self.status().x,self.status().y,self.motion_wait().active))
                self.assertEqual((1,2),(self.status().inputs,self.motion_wait().attempts))
    def test_old_crossed_and_early_frames_do_not_spend_visual_attempts(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction)
        self.observed_result(command,after,offset=79_000_000)
        self.assertEqual(0,self.motion_wait().attempts)
        self.now=command.target_ns+90_000_000
        for prefix,stable in ((0,1),(command.id,0),(command.id+1,1)):
            self.now+=10_000_000
            self.observe(self.scene(2,2,after,beat=True),prefix=prefix,stable=stable)
            self.assertEqual((0,3,0),(self.motion_wait().attempts,self.status().input_state,self.status().moves))
        self.now+=10_000_000;self.observe(self.scene(2,2,after,beat=True))
        self.assertEqual((1,1),(self.motion_wait().attempts,self.status().moves))
    def test_unknown_and_tween_share_three_attempt_budget(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        unknown=translated(terrain,3);unknown.signature=bytes([40])*23296
        for n,after in enumerate((unknown,translated(terrain,3,amount=8),unknown)):
            self.observed_result(command,after,offset=90_000_002+n*10_000_000)
            self.assertEqual(n+1,self.motion_wait().attempts)
            if n<2:self.assertEqual((3,0),(self.status().input_state,self.status().reason))
        self.assertEqual((10,0,0),(self.status().reason,self.status().moves,self.motion_wait().active))
        self.now+=2;self.observe(self.scene(2,2,translated(terrain,3),beat=True))
        self.assertEqual((3,0),(self.motion_wait().attempts,self.status().moves))
    def test_first_and_continuous_visual_deadline_equality_and_one_ns_late(self):
        for confirmed in (False,True):
            for late in (0,1):
                with self.subTest(confirmed=confirmed,late=late):
                    self.fresh_engine();terrain=self.fit();command=self.next_move();self.ack(command)
                    if confirmed:
                        terrain=translated(terrain,3);self.observed_result(command,terrain)
                        command=self.next_move();self.ack(command)
                    deadline=self.motion_wait().deadline_ns
                    self.now=deadline+late
                    self.observe(self.scene(2,2,translated(terrain,3),beat=True))
                    self.assertEqual(int(confirmed)+(not late),self.status().moves)
                    self.assertEqual(9 if late else 0,self.status().reason)
                    self.assertEqual(int(confirmed)+1,self.status().inputs)
                    if late:
                        ready,cleanup=self.tick();self.assertEqual((ready,cleanup.kind),(1,2))
                        self.assertEqual(0,self.motion_wait().active)
    def test_analysis_completion_after_fixed_deadline_cannot_send_another_move(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        deadline=self.motion_wait().deadline_ns
        self.now=command.target_ns+100_000_002
        self.observe(self.scene(2,2,translated(terrain,3),beat=True))
        self.assertEqual(1,self.status().moves)
        # The capture timestamp precedes the bound. Analysis may finish later.
        self.now=deadline+1;ready,cleanup=self.tick()
        self.assertEqual(0,ready)  # tick first records lateness, then next tick cleans up.
        self.assertEqual(9,self.status().reason)
        ready,cleanup=self.tick();self.assertEqual((ready,cleanup.kind),(1,2))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_visual_wait_keeps_original_source_phase_walk_and_session_horizons(self):
        for horizon in ('source','phase','walk','session'):
            with self.subTest(horizon=horizon):
                self.fresh_engine();terrain=textured()
                if horizon in ('source','phase'):
                    self.fit(terrain);old_source=self.status().last_capture_start_ns;old_phase=self.now-1
                    self.now+=2_400_000_000
                    if horizon=='phase':self.observe(self.scene(2,2,terrain,beat=False))
                    bound=(old_source if horizon=='source' else old_phase)+3*SECOND
                else:
                    if horizon=='walk':
                        self.fit(terrain);base=self.status().walk_started_ns
                        first=base+42_200_000_000;epoch=base+44_800_000_000;bound=base+45*SECOND
                    else:
                        base=self.status().started_ns
                        first=base+177_200_000_000;epoch=base+179_800_000_000;bound=base+180*SECOND
                    # End the valid positive fit before the strict first-slot
                    # selection threshold; the original absolute bound stays.
                    for n in range(24):
                        self.now=first+n*100_000_000;scene=self.scene(2,2,terrain,beat=True)
                        scene.beat_remaining=((epoch-(self.now-1))%PERIOD)/PERIOD;self.observe(scene)
                command=self.next_move();record=self.motion_wait()
                self.assertEqual(bound,record.deadline_ns)
                self.assertLess(bound,command.target_ns+PERIOD-150_000_000+10_000_000)
                self.ack(command);unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
                self.observed_result(command,unknown)
                self.assertEqual(bound,self.motion_wait().deadline_ns)
                self.now=bound+1
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(0,self.motion_wait().active)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_wrong_direction_and_two_tiles_stop_without_visual_retry(self):
        for amount in (-9,18):
            with self.subTest(amount=amount):
                self.fresh_engine();terrain=self.fit();command=self.next_move();self.ack(command)
                self.observed_result(command,translated(terrain,3,amount=amount))
                self.assertEqual((10,0,0),(self.status().reason,self.status().moves,self.motion_wait().active))
                self.assertEqual((1,6),(self.motion_wait().attempts,self.motion_wait().last_motion))
                self.now+=10_000_000;self.observe(self.scene(2,2,translated(terrain,3),beat=True))
                self.assertEqual(0,self.status().moves)
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_visual_timeout_needs_new_matching_ack_prefix_before_cleanup(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        self.now=self.motion_wait().deadline_ns+1
        self.assertEqual(0,self.tick()[0]);self.assertEqual((0,0,9),(self.status().terminal,self.status().input_state,self.status().reason))
        self.assertEqual(0,self.motion_wait().active)
        for prefix,stable in ((0,1),(command.id,0)):
            self.now+=2;self.observe(self.scene(2,2,terrain,beat=True),prefix=prefix,stable=stable)
            self.assertEqual(0,self.tick()[0])
        self.now+=2;self.observe(self.scene(2,2,terrain,beat=True))
        ready,cleanup=self.tick();self.assertEqual((ready,cleanup.kind),(1,2))
        self.assertEqual(self.number,cleanup.source_capture_id)
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_goods_during_unknown_visual_wait_hold_without_direction_retry(self):
        for crossed in (False,True):
            with self.subTest(crossed=crossed):
                self.fresh_engine();terrain=self.fit();command=self.next_move();self.ack(command)
                unknown=translated(terrain,3);unknown.signature=bytes([40])*23296
                self.observed_result(command,unknown)
                goods=deepcopy(unknown);goods.goods='visible';self.now+=10_000_000
                self.observe(self.scene(2,2,goods,beat=True),stable=int(not crossed))
                self.assertEqual((1,1,0),(self.status().goods,self.status().reason,self.motion_wait().active))
                ready,cleanup=self.tick()
                if crossed:
                    self.assertEqual(0,ready)
                    self.now+=10_000_000;self.observe(self.scene(2,2,goods,beat=True));ready,cleanup=self.tick()
                self.assertEqual((ready,cleanup.kind),(1,2))
                self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_goods_frame_preserves_evidenced_move_before_holding_pause(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction);after.goods='visible'
        self.observed_result(command,after)
        s=self.status();record=self.motion_wait();event=self.events()[-1]
        self.assertEqual((1,1,1,1,1,6,0),(s.inputs,s.moves,s.lead_confirmed,s.goods,s.reason,s.phase,s.input_state))
        self.assertEqual((1,self.number),(event.motion,event.observed_capture_id))
        self.assertEqual((1,1,0),(record.attempts,record.last_motion,record.active))
        ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2))
        self.assertEqual(self.number,pause.source_capture_id)
        self.ack(pause);self.now+=100_000_000;self.observe(self.scene())
        self.assertEqual((1,1,1),(self.status().terminal,self.status().paused,self.status().moves))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_goods_frame_unknown_motion_is_recorded_once_without_waiting(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        after=translated(terrain,command.direction);after.goods='visible';after.signature=bytes([40])*23296
        self.observed_result(command,after)
        s=self.status();record=self.motion_wait()
        self.assertEqual((1,0,0,1,1,0),(s.inputs,s.moves,s.lead_confirmed,s.goods,s.reason,s.input_state))
        self.assertEqual((1,0,0,self.number),(record.attempts,record.last_motion,record.active,record.last_capture_id))
        ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2))
        self.assertEqual(self.number,pause.source_capture_id)
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_goods_frame_after_original_motion_deadline_holds_without_move_credit(self):
        terrain=self.fit();command=self.next_move();self.ack(command)
        deadline=self.motion_wait().deadline_ns
        after=translated(terrain,command.direction);after.goods='visible'
        self.now=deadline+1;self.observe(self.scene(2,2,after,beat=True))
        s=self.status();record=self.motion_wait()
        self.assertEqual((1,0,0,1,1,6,0),(s.inputs,s.moves,s.lead_confirmed,s.goods,s.reason,s.phase,s.input_state))
        self.assertEqual((0,0,deadline),(record.attempts,record.active,record.deadline_ns))
        ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2))
        self.assertEqual(self.number,pause.source_capture_id)
        self.ack(pause);self.now+=100_000_000;self.observe(self.scene())
        self.assertEqual((1,1,0),(self.status().terminal,self.status().paused,self.status().moves))
        self.assertEqual(1,len([e for e in self.events() if e.command.kind==4]))
    def test_cancel_foreground_owner_and_unknown_synth_never_retry_waited_direction(self):
        for reason in (2,3,4,5,11):
            with self.subTest(reason=reason):
                self.fresh_engine();terrain=self.fit();command=self.next_move()
                if reason==11:
                    self.now=command.not_before_ns
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,command.id,self.now,1,0,1))
                    self.now+=50_000_000
                    self.assertEqual(1,self.lib.ng2_controller_complete(self.engine,command.id,self.now,-1))
                else:
                    self.ack(command);unknown=deepcopy(terrain);unknown.signature=bytes([40])*23296
                    self.observed_result(command,unknown)
                    if reason==2:self.lib.ng2_controller_cancel(self.engine,self.now,2)
                    elif reason==3:self.tick(front=0)
                    elif reason==4:self.tick(locked=1)
                    else:self.tick(owner=0)
                self.assertEqual((1,0),(self.status().terminal,self.motion_wait().active))
                self.now+=10_000_000;self.observe(self.scene(2,2,translated(terrain,3),beat=True))
                self.assertEqual(0,self.tick()[0])
                self.assertEqual(1,len(self.events()))
    def test_late_unobserved_prefix_stops_at_original_next_beat(self):
        terrain=self.fit();first=self.next_move();self.ack(first)
        after=translated(terrain,3);self.observed_result(first,after)
        second=self.next_move();self.ack(second)
        self.now=second.target_ns+PERIOD-150_000_000+10_000_001
        self.assertEqual(0,self.tick()[0])
        self.assertEqual((self.status().terminal,self.status().reason,self.status().moves),(0,9,1))
        self.assertEqual(0,self.tick()[0])  # Last floor predates the second ACK.
        self.now+=2;self.observe(self.scene(2,2,translated(after,3),beat=True))
        ready,pause=self.tick();self.assertEqual((ready,pause.kind),(1,2))
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
        self.assertEqual(16,len(self.motion_references()))
        self.assertEqual([e.command.id for e in self.events() if e.command.kind==4 and e.outcome==2],
                         [row.command_id for row in self.motion_references()])
        self.assertEqual((192,128,23864,48,80),(C.sizeof(Status),C.sizeof(Event),C.sizeof(Scene),C.sizeof(MotionWait),C.sizeof(MotionReference)))
        query=self.lib.ng2_controller_motion_references
        self.assertEqual(0,query(None,None,16));self.assertEqual(0,query(self.engine,None,16))
        for capacity in (0,1,15,16,17):
            guarded=(MotionReference*18)();C.memset(C.byref(guarded),0xa5,C.sizeof(guarded));count=min(capacity,16)
            self.assertEqual(count,query(self.engine,guarded,capacity))
            self.assertEqual(bytes([0xa5])*C.sizeof(MotionReference)*(18-count),bytes(guarded)[count*C.sizeof(MotionReference):])
    def test_blocked_initial_lead_retunes_only_same_safe_floor_then_confirms(self):
        terrain=self.fit();first=self.next_move();self.ack(first);self.observed_result(first,terrain)
        self.assertEqual((self.status().lead_ns,self.status().lead_confirmed,self.status().moves),(75_000_000,0,0))
        second=self.next_move();self.assertEqual(1,second.ordinal);self.ack(second)
        after=translated(terrain,second.direction);self.observed_result(second,after)
        self.assertEqual((self.status().lead_confirmed,self.status().moves,self.status().last_ordinal),(1,1,1))
        third=self.next_move();self.assertEqual(2,third.ordinal)
    def test_blocked_initial_trials_stop_when_original_next_beat_cannot_fit_observation(self):
        terrain=self.fit()
        for lead in (150,75,225,300,375,450):
            self.assertEqual(lead*1_000_000,self.status().lead_ns)
            command=self.next_move();self.ack(command);self.observed_result(command,terrain)
        self.assertEqual((self.status().reason,self.status().lead_confirmed,self.status().inputs),(9,0,6))
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
        self.assertEqual(0,self.tick()[0])
        self.assertEqual((self.status().reason,self.status().inputs),(15,0))
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
    if(ng2_controller_tick(p,now,1,0,1,&command)!=0)return 23;
    ng2_controller_status(p,&status);now=status.next_target_ns-status.lead_ns-100000000;
    if(ng2_controller_tick(p,now,1,0,1,&command)!=1||command.kind!=4)return 35;
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
