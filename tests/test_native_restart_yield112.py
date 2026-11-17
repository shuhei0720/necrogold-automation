"""Opt-in restart budget boundary with procedural public C lifecycle.

The explicit before-feature adapter only ignores the opt-in. Semantic Red is
old C continuing another level, not a missing symbol or compile failure.
No phone speed/acceptance or Runtime queue-drain claim is made here.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_irregular110 as irregular
from tests.test_native_handoff099 import handoff
from tests.test_native_ring094 import Result


class Yield(C.Structure):
    _fields_ = [('abi_version',C.c_uint32),('struct_size',C.c_uint32)] + [
        (name,C.c_int32) for name in ('enabled','pending','invalid','ready',
            'goods_processed','needs_goods','permitted','initial_pause_seen')] + [
        (name,C.c_uint64) for name in ('old_job_id','restart_command_id','new_floor_capture_id',
            'new_floor_start_ns','prefix','level_id','parent_deadline_ns','goods_capture_id',
            'goods_start_ns','source_capture_id','source_start_ns','source_prefix')]


class NativeRestartYield112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous=native.CORE
        try:
            native.CORE=Path(os.environ.get('NECRO112_YIELD_CORE',str(previous)))
            irregular.NativeIrregular110Tests.setUpClass()
        finally:native.CORE=previous
        cls.lib=irregular.NativeIrregular110Tests.lib
        cls.has_yield=hasattr(cls.lib,'ng2_controller_enable_restart_yield')
        if not cls.has_yield and os.environ.get('NECRO112_YIELD_BEFORE')!='1':
            raise RuntimeError('Missing yield API is not a semantic Red; use explicit before-feature adapter')
        if cls.has_yield:
            cls.lib.ng2_controller_enable_restart_yield.argtypes=[C.c_void_p]
            cls.lib.ng2_controller_restart_yield_status.argtypes=[C.c_void_p,C.c_uint64,C.POINTER(Yield)]
            cls.lib.ng2_controller_restart_yield_ready.argtypes=[C.c_void_p,C.c_uint64]
            cls.lib.ng2_controller_restart_yield_permit.argtypes=[C.c_void_p]+[C.c_uint64]*4
            cls.lib.ng2_controller_restart_yield_goods.argtypes=[C.c_void_p,C.POINTER(native.Scene)]+[C.c_uint64]*5

    @classmethod
    def tearDownClass(cls):irregular.NativeIrregular110Tests.tearDownClass()

    def setUp(self):self.engine()

    def engine(self,enabled=True):
        self.f=irregular.NativeIrregular110Tests(methodName='runTest');self.f.lib=self.lib
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h,self.q=self.f.h,self.f.q
        if enabled:
            self.assertEqual(1,self.enable())
        return self.h

    def enable(self):
        return self.lib.ng2_controller_enable_restart_yield(self.h.engine) if self.has_yield else 1

    def state(self):
        value=Yield()
        if self.has_yield:self.lib.ng2_controller_restart_yield_status(self.h.engine,self.h.now,C.byref(value))
        return value

    def permit(self,capture=None,start=None,prefix=None):
        status=self.h.status()
        if not self.has_yield:return 0
        return self.lib.ng2_controller_restart_yield_permit(self.h.engine,
            status.last_capture_id if capture is None else capture,
            status.last_capture_start_ns if start is None else start,
            self.h.prefix if prefix is None else prefix,self.h.now)

    def first_pause(self):
        self.assertEqual(1,self.h.observe(self.h.scene(state=1)))
        ready,resume=self.h.tick();self.assertEqual((1,1),(ready,resume.kind))
        self.h.ack(resume);self.h.now+=210_000_000
        floor=self.h.scene(2,2,native.textured(),beat=True)
        self.assertEqual(1,self.h.observe(floor));return floor

    def walked_negative(self):
        self.first_pause()
        # Real public ACK/MOVED establishes spent directional budget. The
        # later unstarted ticket is revoked by ordinary goods priority.
        terrain,_command=self.h.continuous_walk(moves=1,direction=1)
        self.h.now+=2;self.q.goods();self.q.assess(3,2);self.q.pause_observed()
        self.assertEqual(1,self.q.durable())
        old=self.q.cycle();ready,restart=self.h.tick()
        self.assertEqual((1,3),(ready,restart.kind));self.assertEqual(1,self.q.intent(restart))
        return old,restart

    def new_floor(self,goods=0,commit=True):
        old,restart=self.walked_negative();self.h.ack(restart);self.h.now+=210_000_000
        floor=self.h.scene(2,2,native.textured(),beat=True);floor.fingerprint[:]=bytes([80])*48
        floor.goods=goods
        self.assertEqual(1,self.h.observe(floor))
        source=self.q.cycle();source_id=self.h.number;start=self.h.status().last_capture_start_ns
        if commit:
            self.assertEqual(1,self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
                source.job_id,source.next_floor_capture_id,self.h.prefix,self.h.now))
        return old,restart,floor,source_id,start

    def goods(self,scene,ident=None,start=None,end=None,prefix=None):
        ident=self.h.number if ident is None else ident
        start=self.h.now-2 if start is None else start;end=start+1 if end is None else end
        if not self.has_yield:return 0
        return self.lib.ng2_controller_restart_yield_goods(self.h.engine,C.byref(scene),
            ident,start,end,self.h.prefix if prefix is None else prefix,self.h.now)

    def probe(self,outcome=0,mutate=None,status=0):
        state=self.q.cycle()
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now))
        result=Result(abi=1,size=C.sizeof(Result),status=status,outcome=outcome,
            selected_row=-1,selected_partial=-1,started_ns=self.h.now,finished_ns=self.h.now+1)
        if mutate:mutate(result)
        self.h.now+=1
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(result)))
        return result

    def finish_pause(self):
        ready,pause=self.h.tick();self.assertEqual((1,2),(ready,pause.kind))
        self.assertEqual(0,handoff(self.lib,self.h.engine).allowed)
        self.h.ack(pause);self.h.now+=210_000_000
        self.assertEqual(1,self.h.observe(self.h.scene(state=1)))
        self.h.tick();return pause,handoff(self.lib,self.h.engine)

    def test_optin_after_durable_restart_never_enters_another_level_with_spent_budget(self):
        old,restart,floor,capture,start=self.new_floor()
        spent=self.h.status().inputs
        self.assertEqual(1,spent)
        self.assertEqual((0,0),(self.h.status().x,self.h.status().y))
        for _ in range(27):
            self.h.now+=100_000_000
            fresh=self.h.scene(2,2,native.textured(),beat=True);fresh.fingerprint[:]=floor.fingerprint[:]
            self.assertEqual(1,self.h.observe(fresh))
        ready,command=self.h.tick()
        if not ready and self.h.status().next_target_ns:
            self.h.now=max(self.h.now,self.h.status().next_target_ns-self.h.status().lead_ns-100_000_000)
            fresh=self.h.scene(2,2,native.textured(),beat=True);fresh.fingerprint[:]=floor.fingerprint[:]
            self.h.observe(fresh);ready,command=self.h.tick()
        self.assertNotEqual(4,command.kind,
            'after walking/negative/real RESTART, old global16 budget cannot fund another level before a qualified newrun boundary')
        self.assertEqual((0,0),(ready,self.h.status().input_state),'Runtime quiescence permit is still required')
        self.assertEqual(spent,self.h.status().inputs,'same-run counters are not reset')
        state=self.state()
        self.assertEqual((1,1,0),(state.enabled,state.pending,state.invalid))
        self.assertEqual((old.job_id,restart.id,capture,start),
            (state.old_job_id,state.restart_command_id,state.new_floor_capture_id,state.new_floor_start_ns))

    def test_optin_initial_floor_or_other_ui_is_input_free_but_old_start_is_unchanged(self):
        for state in (0,2,3):
            with self.subTest(state=state):
                self.engine();self.h.observe(self.h.scene(state=state,gold=1))
                for _ in range(6):
                    self.h.now+=50_000_000;self.h.observe(self.h.scene(state=state,gold=1))
                    self.assertEqual((0,0),(self.h.tick()[0],len(self.h.events())),
                        'new opt-in requires a fresh initial PAUSE before any gameplay UI')
        self.engine(enabled=False);self.h.observe(self.h.scene(state=1))
        self.assertEqual((1,1),(self.h.tick()[0],self.h.events()[-1].command.kind))

    def test_old_negative_or_uncommitted_restart_is_not_a_yield_basis(self):
        self.first_pause();self.h.now+=2;self.q.goods();self.q.assess(3,2);self.q.pause_observed();self.q.durable()
        self.assertEqual((0,0),(self.state().pending,self.permit()))
        self.engine();self.new_floor(commit=False)
        self.assertEqual((0,0),(self.state().pending,self.permit()))
        self.assertEqual(0,handoff(self.lib,self.h.engine).allowed)

    def test_source_bound_permit_requires_live_current_floor_and_real_pause_confirmation(self):
        _old,restart,_floor,_capture,_start=self.new_floor()
        for args in ((self.h.number+1,None,None),(None,self.h.now+1,None),(None,None,restart.id+1)):
            with self.subTest(args=args):self.assertEqual(0,self.permit(*args))
        self.assertEqual(1,self.permit())
        pause,proof=self.finish_pause()
        self.assertEqual((3,1,14),(proof.kind,proof.allowed,proof.reason))
        self.assertEqual((pause.source_capture_id,restart.id,pause.id,pause.id),
            (proof.source_capture_id,proof.source_prefix,proof.completed_prefix,self.h.status().last_completed_id))
        self.assertEqual(pause.observed_capture_id if hasattr(pause,'observed_capture_id') else self.h.events()[-1].observed_capture_id,
            proof.pause_capture_id)
        self.assertEqual((1,7,1,14),(self.h.status().terminal,self.h.status().phase,self.h.status().paused,self.h.status().reason))

    def test_later_floor_observation_revokes_permit_without_renewing_parent(self):
        _old,_restart,floor,_capture,_start=self.new_floor();state=self.state();self.assertEqual(1,self.permit())
        self.h.now+=10_000_000;self.h.observe(deepcopy(floor))
        self.assertEqual((0,0),(self.state().permitted,self.h.tick()[0]))
        self.assertEqual(state.parent_deadline_ns,self.state().parent_deadline_ns)
        self.assertEqual(1,self.permit())

    def test_first_goods_is_data_only_and_partial_then_full_each_requires_positive_veto(self):
        _old,_restart,floor,capture,start=self.new_floor(goods=1)
        current=self.h.status();before=(current.last_capture_id,current.last_capture_start_ns,current.inputs,current.moves)
        self.assertEqual(0,self.permit(),'visible products cannot be bypassed as unassessed metadata')
        self.assertEqual(1,self.goods(floor,capture,start,start+1));self.probe()
        self.assertEqual(1,self.state().goods_processed)
        self.assertEqual(1,self.permit())
        self.h.now+=20_000_000;full=deepcopy(floor);full.goods=2
        self.h.observe(full);full_id=self.h.number;full_start=self.h.status().last_capture_start_ns
        self.assertEqual(0,self.permit(),'new FULL must not be hidden by earlier clean PARTIAL')
        self.assertEqual(1,self.goods(full,full_id,full_start,full_start+1));self.probe()
        self.assertEqual(1,self.permit())
        self.assertEqual(before[2:],(self.h.status().inputs,self.h.status().moves))
        self.assertEqual((full_id,full_start),(self.h.status().last_capture_id,self.h.status().last_capture_start_ns))

    def test_target_candidate_late_hint_and_malformed_results_never_allow_next_start(self):
        for label,outcome,status in (('target',2,0),('candidate',1,0),('hint',0,0),('row_hint',0,0),
                                    ('row_invalid',0,0),('deadline',0,2),('malformed',0,0)):
            with self.subTest(label=label):
                self.engine();_old,_rs,floor,ident,start=self.new_floor(goods=2)
                self.assertEqual(1,self.goods(floor,ident,start,start+1))
                def mutate(r):
                    if label=='hint':r.row_count=1;r.rows[0].slots[0].icon_upper_bound=.81
                    if label=='row_hint':r.row_count=1;r.rows[0].outcome=1
                    if label=='row_invalid':r.row_count=1;r.rows[0].outcome=99
                    if label=='malformed':r.abi=99
                self.probe(outcome,mutate,status)
                self.assertEqual(0,self.permit());self.assertEqual(0,handoff(self.lib,self.h.engine).allowed)
                self.assertNotEqual(3,self.h.tick()[1].kind)

    def test_retained_goods_cannot_replace_current_ui_scene_or_expired_prefix_source(self):
        _old,_rs,floor,ident,start=self.new_floor(goods=1)
        self.h.now+=20_000_000;later=deepcopy(floor);later.goods=0;self.h.observe(later)
        live=(self.h.status().last_capture_id,self.h.status().last_capture_start_ns)
        self.assertEqual(0,self.goods(floor,ident,start,start+1,self.h.prefix+1))
        self.assertEqual(1,self.goods(floor,ident,start,start+1))
        self.assertEqual(live,(self.h.status().last_capture_id,self.h.status().last_capture_start_ns))
        self.probe();self.assertEqual(1,self.permit())
        self.engine();_old,_rs,floor,ident,start=self.new_floor(goods=1)
        self.h.now=start+150_000_001
        self.assertEqual(0,self.goods(floor,ident,start,start+1))
        self.assertEqual(0,self.permit(),'an expired protected source cannot count as inspected')

    def test_original_budgets_cancellation_and_started_or_unknown_pause_cannot_mint_handoff(self):
        for fault in ('parent','walk','session','cancel','foreground','locked','owner','unknown'):
            with self.subTest(fault=fault):
                self.engine();self.new_floor();state=self.state()
                if fault=='parent':self.h.now=state.parent_deadline_ns+1
                elif fault=='walk':self.h.now=self.h.status().walk_started_ns+45*native.SECOND
                elif fault=='session':self.h.now=self.h.status().started_ns+180*native.SECOND
                elif fault=='cancel':self.lib.ng2_controller_cancel(self.h.engine,self.h.now,2)
                elif fault in ('foreground','locked','owner'):
                    self.h.tick(front=int(fault!='foreground'),locked=int(fault=='locked'),owner=int(fault!='owner'))
                else:
                    self.assertEqual(1,self.permit());ready,pause=self.h.tick();self.assertEqual(1,ready)
                    self.h.now=max(self.h.now,pause.not_before_ns)
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.h.engine,pause.id,self.h.now,1,0,1))
                    self.h.now+=1;self.lib.ng2_controller_complete(self.h.engine,pause.id,self.h.now,-1)
                self.assertEqual(0,self.permit());self.assertEqual(0,handoff(self.lib,self.h.engine).allowed)

    def test_enable_is_immutable_and_old_walking_restart_still_continues(self):
        self.assertEqual(0,self.enable(),'the run flag cannot be enabled twice')
        plain=self.lib.ng2_controller_create_cycle(native.SECOND)
        try:self.assertEqual(0,self.lib.ng2_controller_enable_restart_yield(plain),'irregular opt-in is required')
        finally:self.lib.ng2_controller_destroy(plain)
        self.engine(enabled=False);self.new_floor()
        self.assertEqual(0,self.enable(),'a flag cannot be installed after captures or inputs')
        self.assertEqual((0,0),(self.state().enabled,self.state().pending))
        for _ in range(27):
            self.h.now+=100_000_000
            floor=self.h.scene(2,2,native.textured(),beat=True);floor.fingerprint[:]=bytes([80])*48
            self.h.observe(floor)
        ready,command=self.h.tick()
        if not ready and self.h.status().next_target_ns:
            self.h.now=max(self.h.now,self.h.status().next_target_ns-self.h.status().lead_ns-100_000_000)
            floor=self.h.scene(2,2,native.textured(),beat=True);floor.fingerprint[:]=bytes([80])*48
            self.h.observe(floor);ready,command=self.h.tick()
        self.assertEqual((1,4),(ready,command.kind),'old callers retain their existing next-level behavior')

    def test_full_then_partial_sources_are_serial_once_and_pause_has_no_restart(self):
        _old,restart,floor,ident,start=self.new_floor(goods=2)
        self.assertEqual(0,self.q.cycle().pending,'latest must not preempt the retained goods entrance')
        self.assertEqual(1,self.goods(floor,ident,start,start+1))
        self.h.now+=10_000_000;partial=deepcopy(floor);partial.goods=1
        self.h.observe(partial);partial_id=self.h.number;partial_start=self.h.status().last_capture_start_ns
        self.assertEqual(0,self.goods(partial,partial_id,partial_start,partial_start+1),'one actual worker at a time')
        self.assertEqual(0,self.permit());self.probe()
        self.assertEqual(0,self.goods(floor,ident,start,start+1),'one immutable source per goods kind')
        self.assertEqual(1,self.goods(partial,partial_id,partial_start,partial_start+1));self.probe()
        self.assertEqual(1,self.permit());pause,proof=self.finish_pause()
        self.assertEqual(1,proof.allowed)
        later=[event.command.kind for event in self.h.events() if event.command.id>restart.id]
        self.assertEqual([2],later,'new floor is held; no MOVE, RESUME or second RESTART')
        self.assertEqual(pause.id,self.h.status().last_completed_id)

    def test_late_worker_hint_survives_frozen_data_timeout_without_handoff(self):
        _old,_restart,floor,ident,start=self.new_floor(goods=2)
        self.assertEqual(1,self.goods(floor,ident,start,start+1));state=self.q.cycle()
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now))
        state=self.q.cycle();worker_start=self.h.now;self.h.now=state.deadline_ns+1
        self.h.tick();self.assertEqual(0,self.permit())
        result=Result(abi=1,size=C.sizeof(Result),status=0,outcome=0,row_count=1,
            selected_row=-1,selected_partial=-1,started_ns=worker_start,finished_ns=self.h.now)
        result.rows[0].slots[0].icon_upper_bound=.81
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(result)))
        self.assertEqual(1,self.q.cycle().candidate_latched)
        self.assertEqual((0,0),(self.permit(),handoff(self.lib,self.h.engine).allowed))

    def test_irregular_ui_companion_vetoes_floor_permit_and_pause_confirmation(self):
        for label in ('death','death_present','menu','invalid','pause_death'):
            with self.subTest(label=label):
                self.engine();_old,_restart,floor,_ident,_start=self.new_floor()
                if label=='pause_death':
                    self.assertEqual(1,self.permit());ready,pause=self.h.tick();self.assertEqual(1,ready)
                    self.h.ack(pause);self.h.now+=210_000_000;floor=self.h.scene(state=1)
                else:self.h.now+=10_000_000
                observation=irregular.death()
                if label=='death_present':observation.kind=0;observation.empty_hearts=2
                if label=='menu':observation=irregular.menu()
                if label=='invalid':observation.abi_version=99
                self.f.observe(floor,observation)
                self.assertEqual(0,self.permit(),'strong or malformed UI evidence cannot mint a normal boundary')
                self.assertEqual(0,handoff(self.lib,self.h.engine).allowed)
                self.assertEqual(0,self.h.tick()[0],'a contradicted floor never licenses a holding PAUSE')

    def test_stale_first_pause_or_invalid_pause_companion_never_opens_floor_start(self):
        for label in ('stale','invalid','menu','death_present'):
            with self.subTest(label=label):
                self.engine();observation=irregular.none();kwargs={}
                if label=='stale':kwargs['start']=self.h.now-2;kwargs['end']=self.h.now;kwargs['commit']=self.h.now+3*native.SECOND+1
                if label=='invalid':observation.abi_version=99
                if label=='menu':observation=irregular.menu()
                if label=='death_present':observation=irregular.death();observation.kind=0;observation.empty_hearts=2
                self.f.observe(self.h.scene(state=1),observation,**kwargs)
                self.assertEqual(0,self.state().initial_pause_seen,'only a fresh, compatible PAUSE opens the new opt-in gate')
                if label=='stale':self.h.now=kwargs['commit']+10_000_000
                else:self.h.now+=10_000_000
                self.f.observe(self.h.scene(2,2,native.textured(),beat=True),irregular.none())
                self.assertEqual((0,0),(self.h.tick()[0],len(self.h.events())))

    def test_durable_first_newfloor_survives_unknown_tail_without_rewinding_ui(self):
        for enabled in (True,False):
            with self.subTest(enabled=enabled):
                self.engine(enabled=enabled)
                _old,restart,partial,first_id,first_start=self.new_floor(goods=1,commit=False)
                old=self.q.cycle()
                self.h.now+=5_000_000;full=deepcopy(partial);full.goods=2;self.h.observe(full)
                full_id=self.h.number;full_start=self.h.status().last_capture_start_ns
                self.h.now+=5_000_000;self.h.observe(self.h.scene(state=0));latest=self.h.status()
                accepted=self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
                    old.job_id,old.next_floor_capture_id,restart.id,self.h.now)
                self.assertEqual(int(enabled),accepted,
                    'only the new opt-in may bind durable DATA from the actual first newfloor proof while current UI stays UNKNOWN')
                if not enabled:continue
                self.assertEqual((latest.last_capture_id,latest.last_capture_start_ns),
                    (self.h.status().last_capture_id,self.h.status().last_capture_start_ns))
                self.assertEqual(0,self.permit(),'the earlier newfloor raster is not current UI authority')
                self.assertEqual(1,self.goods(partial,first_id,first_start,first_start+1));self.probe()
                self.assertEqual(1,self.goods(full,full_id,full_start,full_start+1));self.probe()
                self.assertEqual(0,self.permit(),'clean retained DATA cannot replace current UNKNOWN')
                self.h.now+=5_000_000;self.h.observe(full)
                self.assertEqual(1,self.permit());_pause,proof=self.finish_pause();self.assertEqual(1,proof.allowed)

    def test_death_retires_budget_into_existing_irregular_owner_after_worker_settles(self):
        for candidate in (False,True):
            with self.subTest(candidate=candidate):
                self.engine();_old,_restart,floor,ident,start=self.new_floor(goods=2)
                self.assertEqual(1,self.goods(floor,ident,start,start+1));job=self.q.cycle()
                self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    job.job_id,job.capture_id,job.prefix,self.h.now));worker_start=self.h.now
                self.h.now+=10_000_000;self.f.observe(floor,irregular.death());episode=self.f.irregular()
                self.assertEqual((0,1),(self.state().pending,self.state().invalid))
                self.assertEqual(1,episode.stage,'the original irregular owner waits for the same actual DATA job')
                self.assertEqual(0,self.h.tick()[0])
                result=Result(abi=1,size=C.sizeof(Result),status=0,outcome=1 if candidate else 0,
                    selected_row=-1,selected_partial=-1,started_ns=worker_start,finished_ns=self.h.now)
                self.assertEqual(1,self.lib.ng2_controller_irregular_ring_settled(self.h.engine,
                    episode.episode_id,job.job_id,job.capture_id,job.prefix,C.byref(result),self.h.now))
                settled=self.f.irregular()
                if candidate:
                    self.assertEqual((9,4,1),(settled.stage,settled.held_reason,self.q.cycle().candidate_latched))
                    self.assertEqual(0,self.h.tick()[0])
                else:
                    self.assertEqual(2,settled.stage)
                    self.assertEqual(1,self.lib.ng2_controller_irregular_durable(self.h.engine,
                        settled.episode_id,settled.trigger_capture_id,settled.prefix,self.h.now))
                    ready,command=self.h.tick();self.assertEqual((1,5),(ready,command.kind),
                        'qualified DEATH keeps the existing checkpoint/continue path after DATA settles')
                self.assertEqual((0,0),(self.permit(),handoff(self.lib,self.h.engine).allowed))

    def test_positive_invalid_yield_cleanup_pause_ack_is_observed_without_handoff_or_resend(self):
        # Actual Mac223 commit/capture cases reached a real cleanup PAUSE ACK,
        # then accepted hundreds of PAUSE frames while input3 stayed open.
        for label,outcome in (('candidate',1),('target',2),('hint',0)):
            with self.subTest(label=label):
                self.engine();_old,restart,floor,ident,start=self.new_floor(goods=2)
                self.assertEqual(1,self.goods(floor,ident,start,start+1))
                def hint(result):
                    if label=='hint':result.row_count=1;result.rows[0].slots[0].icon_upper_bound=.81
                self.probe(outcome,hint)
                self.assertEqual((1,1,0),(self.state().pending,self.state().invalid,self.permit()))
                spent=(self.h.status().inputs,self.h.status().moves,self.h.status().restarts)
                ready,pause=self.h.tick();self.assertEqual((1,2),(ready,pause.kind))
                self.assertGreater(pause.id,restart.id)
                self.assertEqual((0,0),(handoff(self.lib,self.h.engine).kind,handoff(self.lib,self.h.engine).allowed))
                self.h.ack(pause);self.assertEqual(3,self.h.status().input_state)
                ack=self.h.now
                self.f.observe(self.h.scene(state=1),start=ack-2,end=ack-1,commit=ack)
                self.assertEqual((3,0),(self.h.status().input_state,self.h.events()[-1].observed_capture_id),
                    'an observation starting before ACK cannot settle the cleanup command')
                self.h.now+=10_000_000;self.f.observe(self.h.scene(state=1),prefix=restart.id)
                self.assertEqual((3,0),(self.h.status().input_state,self.h.events()[-1].observed_capture_id),
                    'an earlier completed prefix cannot settle the cleanup command')
                self.h.now+=210_000_000;self.h.observe(self.h.scene(state=1));observed=self.h.number
                self.assertEqual(0,self.h.status().input_state,
                    'matching independent PAUSE must close the ordinary candidate cleanup ACK, even after budget yield was invalidated')
                self.h.tick();status=self.h.status();event=self.h.events()[-1]
                self.assertEqual((1,1,1),(status.terminal,status.paused,status.reason))
                self.assertEqual((pause.id,2,observed),(event.command.id,event.outcome,event.observed_capture_id))
                self.assertEqual(1,self.q.cycle().candidate_latched)
                self.assertEqual(2 if label=='target' else 1,self.q.cycle().outcome)
                self.assertEqual(spent,(status.inputs,status.moves,status.restarts))
                self.assertEqual((0,0),(self.permit(),handoff(self.lib,self.h.engine).allowed))
                count=len(self.h.events());self.h.now+=10_000_000;self.h.observe(self.h.scene(state=1))
                self.assertEqual((0,count),(self.h.tick()[0],len(self.h.events())),'no second PAUSE or restart is issued')
