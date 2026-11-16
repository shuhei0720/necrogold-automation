"""TEST107 unsent route change: revoke first, then observe a new floor route.

The C-state fixture records prior visits explicitly after the existing public
lead/move setup. Its sparse terrain and clocks are semantic tests, not replay
of the missing eleven-move phone history or Runtime acceptance.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_side_opening098 as side


SHIM = r'''
int test108_vantage_context(NG2Controller*p,const NG2Scene*s,NG2Command*out){
    NG2Decision choice;NG2ControllerEvent*e=event(p);int y;
    if(!p||!s||!out||!e||p->s.input_state!=1||p->s.phase!=NG2_PHASE_WALK
        ||!p->s.lead_confirmed||p->s.moves!=1||p->s.inputs!=1||e->begin_ns||e->outcome)return 0;
    /* A private history fixture, not a new production entry point. */
    p->scene=p->before=*s;memset(p->visits,0,sizeof(p->visits));
    for(y=-3;y<0;++y)p->visits[(p->s.y+y+16)*33+p->s.x+16]=2;
    p->visits[(p->s.y+16)*33+p->s.x+16]=1;
    if(!choose_step(p,s,&choice)||choice.direction!=NG2_RIGHT||choice.reason!=8
        ||choice.target_x!=1||choice.target_y||choice.obstacle!=NG2_TILE_FLOOR)return 0;
    p->command_choice=choice;p->command.direction=choice.direction;
    p->continuous_ticket.direction=choice.direction;e->command=p->command;*out=p->command;return 1;
}
void test108_vantage_fault(NG2Controller*p,int fault){
    if(fault==1)++p->command_choice.target_x;
    if(fault==2)p->observation_refresh_count=8;
    if(fault==3)p->observation_refresh_verified=p->latest_verified_ns;
}
uint64_t test108_vantage_history(const NG2Controller*p){
    uint64_t value=UINT64_C(1469598103934665603);size_t i;
    const unsigned char*raw=(const unsigned char*)p->visits;
    for(i=0;i<sizeof(p->visits);++i)value=(value^raw[i])*UINT64_C(1099511628211);
    raw=(const unsigned char*)&p->entrance;
    for(i=0;i<sizeof(p->entrance);++i)value=(value^raw[i])*UINT64_C(1099511628211);
    return value;
}
'''


class NativeVantageReplan108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='vantage-replan108-')
        directory = Path(cls.source_directory.name)
        for path in fixture.CORE.glob('NG2*'):
            if path.suffix in ('.c','.h'):
                shutil.copyfile(path,directory/path.name)
        controller = directory/'NG2Controller.c'
        baseline = os.environ.get('NECRO_TEST108_VANTAGE_BASELINE_CONTROLLER')
        if baseline:
            shutil.copyfile(baseline,controller)
        with controller.open('a') as output:
            output.write('\n'+SHIM)
        old = mechanics.CORE
        try:
            mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = old
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene),C.c_int32,C.c_int32,
            C.POINTER(C.c_uint16),C.c_size_t,C.POINTER(side.observation.Entrance),
            C.POINTER(side.observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene),C.POINTER(fixture.Scene),
            C.c_int32,C.POINTER(side.observation.Motion)]
        cls.lib.test108_vantage_context.argtypes = [C.c_void_p,C.POINTER(fixture.Scene),C.POINTER(fixture.Command)]
        cls.lib.test108_vantage_fault.argtypes = [C.c_void_p,C.c_int]
        cls.lib.test108_vantage_history.argtypes = [C.c_void_p]
        cls.lib.test108_vantage_history.restype = C.c_uint64
        evidence = os.environ.get('NECRO_TEST108_VANTAGE_BUILD')
        if evidence:
            target = Path(evidence);target.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(Path(cls.lib._name),target/'controller.so')
            (target/'source.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c','.h')},indent=2)+'\n')

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

    for _name in ('setUp','scene','observe','observe_actual','tick','status','events','motion_wait',
        'ack','fit','next_move','publish_procedural_candidate','fresh_engine','recovery','recovery_samples',
        'all_public_bytes','reject_old_callbacks_without_mutation','observed_result','credit','choice',
        'motion','preparation_epoch','trigger','prove_and_issue'):
        locals()[_name] = getattr(side.NativeSideOpening098Tests,_name)

    def armed(self,turns=0,side_sign=-1):
        self.assertEqual((0,-1),(turns,side_sign))
        side.NativeSideOpening098Tests.armed(self)
        source = fixture.textured({(0,0):'floor',(1,0):'floor',(2,0):'stone',
            (0,-1):'floor',(0,-2):'floor',(0,-3):'floor',
            (1,-3):'dirt',(1,-4):'floor',(2,-5):'gold',(-2,0):'dirt'})
        old = fixture.Command()
        self.assertEqual(1,self.lib.test108_vantage_context(self.engine,C.byref(self.scene(2,2,source)),C.byref(old)))
        latest = deepcopy(source)
        latest.tiles.update({(1,-5):'dirt',(1,-3):'floor',(-2,0):'floor'})
        latest.tiles.pop((2,0))
        self.new_direction = 3
        # The ordinary chooser uses the fixture's explicit earlier visits.
        frame=self.scene(2,2,latest);choice=side.observation.Decision()
        visits=(C.c_uint16*1089)()
        for y in range(-3,0):visits[(self.status().y+y+16)*33+self.status().x+16]=2
        visits[(self.status().y+16)*33+self.status().x+16]=1
        self.assertEqual(1,self.lib.ng2_choose(C.byref(frame),self.status().x,self.status().y,visits,
            len(visits),C.byref(side.observation.Entrance()),C.byref(choice)))
        self.assertEqual((3,8,1,-4,1),tuple(getattr(choice,k)for k,_ in choice._fields_))
        self.assertEqual((2,0,0),self.motion(source,latest,old.direction))
        self.armed_history=self.lib.test108_vantage_history(self.engine)
        self.armed_prefix=self.status().last_completed_id
        return source,latest,old

    def test_unsent_route_is_retired_then_independent_zero_issues_only_a_new_future_ticket(self):
        _,latest,old,retired=self.trigger()
        history=self.lib.test108_vantage_history(self.engine)
        self.assertEqual((self.armed_history,self.armed_prefix),
            (history,self.status().last_completed_id),'revoking the old route preserves world history and prefix')
        new=self.prove_and_issue(latest)
        self.assertEqual(history,self.lib.test108_vantage_history(self.engine))
        self.assertGreater(new.id,old.id);self.assertGreater(new.target_ns,old.target_ns)
        self.assertEqual(old.ordinal,new.ordinal)
        self.assertEqual(retired,bytes(self.events()[-2]))
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new)
        self.assertEqual((2,1),(self.status().inputs,self.status().moves),'ACK is not displacement')
        self.assertEqual(history,self.lib.test108_vantage_history(self.engine))
        moved=fixture.translated(latest,new.direction)
        self.observed_result(new,moved)
        self.assertEqual((2,2),(self.status().inputs,self.status().moves),'only the independent real motion result credits one step')
        self.now+=4;self.observe_actual(self.scene(2,2,moved,beat=True))
        self.assertEqual((2,2),(self.status().inputs,self.status().moves),'the same completed action has no second movement credit')

    def test_only_one_remote_stone_loss_and_positive_route_opening_are_eligible(self):
        for fault in ('no_stone_loss','stone_to_floor','new_stone','second_stone_loss','no_positive_opening',
            'door','item','gold','protected','origin','new_next','new_target','near_material'):
            with self.subTest(fault=fault):
                self.fresh_engine();source,latest,old=self.armed()
                if fault=='no_stone_loss':latest.tiles[(2,0)]='stone'
                elif fault=='stone_to_floor':latest.tiles[(2,0)]='floor'
                elif fault=='new_stone':latest.tiles[(8,3)]='stone'
                elif fault=='second_stone_loss':
                    source.tiles[(-5,3)]='stone';latest.tiles.pop((-5,3),None)
                    self.assertEqual(1,self.lib.test108_vantage_context(self.engine,C.byref(self.scene(2,2,source)),C.byref(old)))
                elif fault=='no_positive_opening':
                    source.tiles.pop((1,-3))
                    self.assertEqual(1,self.lib.test108_vantage_context(self.engine,C.byref(self.scene(2,2,source)),C.byref(old)))
                elif fault in ('door','item','gold'):latest.tiles[(8,3)]=fault
                elif fault=='protected':latest.protected.add((8,3))
                elif fault=='origin':latest.tiles[(0,0)]='dirt'
                elif fault=='new_next':latest.tiles[(0,-1)]='dirt'
                elif fault=='new_target':latest.tiles[(1,-4)]='dirt'
                elif fault=='near_material':latest.tiles[(-1,-1)]='floor'
                credit=self.credit();history=self.lib.test108_vantage_history(self.engine)
                self.now=old.deadline_ns-30_000_000;self.observe_actual(self.scene(2,2,latest,beat=True))
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertEqual((credit,history),(self.credit(),self.lib.test108_vantage_history(self.engine)))

    def test_old_full_decision_progress_once_and_session_count_cannot_be_bypassed(self):
        for fault in (1,2,3):
            with self.subTest(fault=fault):
                self.fresh_engine();_,latest,old=self.armed()
                self.lib.test108_vantage_fault(self.engine,fault)
                credit=self.credit();self.now=old.deadline_ns-30_000_000
                self.observe_actual(self.scene(2,2,latest,beat=True))
                self.assertEqual(0,self.recovery().post_move_reacquisitions)
                self.assertNotEqual(4,self.tick()[1].kind)
                self.assertEqual(credit,self.credit())

    def test_later_mode3_anchor_cannot_accept_even_a_remote_material_update(self):
        _,latest,_,_=self.trigger()
        changed=deepcopy(latest);changed.tiles[(8,3)]='dirt'
        self.now+=20_000_000;self.observe_actual(self.scene(2,2,changed,beat=True))
        self.assertEqual(17,self.status().reason)
        self.assertNotEqual(4,self.tick()[1].kind)
        self.assertEqual(self.saved_credit,self.credit())

    test_strict_zero_and_started_or_unknown_input_rejections = side.NativeSideOpening098Tests.test_trigger_requires_strict_zero_and_cannot_reuse_started_or_unknown_input
    test_independent_prefix_and_nonoverlap_are_required = side.NativeSideOpening098Tests.test_later_proof_requires_independent_current_prefix_capture
    test_nontransitive_zero_keeps_the_frozen_anchor = side.NativeSideOpening098Tests.test_fixed_new_anchor_cannot_be_replaced_by_transitive_zero_frames
    test_frozen_original_deadlines_are_not_extended = side.NativeSideOpening098Tests.test_original_ticket_and_recovery_horizons_cannot_be_extended
    test_cancellation_owner_foreground_phase_and_hud_revoke_permission = side.NativeSideOpening098Tests.test_goods_cancel_owner_phase_and_current_hud_revoke_new_permission
    test_new_ack_unknown_has_no_resend_or_movement_credit = side.NativeSideOpening098Tests.test_new_ack_unknown_remains_unresolved_without_resend


if __name__=='__main__':
    unittest.main()
