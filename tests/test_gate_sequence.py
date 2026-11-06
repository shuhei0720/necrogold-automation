"""TEST033: 商店の開扉→次拍進入。2入力と実歩行1マスを区別する。"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from necroprobe import shop_navigation as nav, shop_walk as walk, gold_scan as gold, beat_sync
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_shop_walk as old
from test_walk_doorway import corridor
from test_shop_navigation import terrain,tile,shifted


def evidence(name,digest):
    folder=os.environ.get('NECRO_TEST032_FRAMES')
    if not folder:raise unittest.SkipTest('external TEST032 frames not supplied')
    p=Path(folder)/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise AssertionError('TEST032 evidence hash mismatch')
    with Image.open(p) as image:return image.convert('RGB')


def gate_frame(driver):
    before,model=driver.synchronize(driver.observe())
    before['_extra']['scene']=corridor('left',0,opened=False)
    return before,model


class GateSequenceTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime

    def test_actual_three_goods_pause_and_closed_gate_plan(self):
        before=evidence('run-105.jpg','79c82275cca850b7a874d10bf0c4ea817445038a84aa4fd54ac40519969e5111')
        found=evidence('found.jpg','1bec740b12ef98d588990e47edbeb471e2efbd2f473fc5c5a9cad08f4b117367')
        paused=evidence('stopped.jpg','5e33fc28c0a100014ed96f18e076212ad870f509e71d980b986ae931ac16ec33')
        self.assertEqual('visible',nav.scan(found).goods);self.assertEqual('pause',gold.analyze_image(paused)['state'])
        with tempfile.TemporaryDirectory() as folder:
            d,clock=old.SyncDeadlineTests.build(self,folder)
            obs=gold.analyze_image(before);obs['_extra']=d.analyze_frame(before,obs)
            decision=d.choose(obs);self.assertEqual('left',decision['direction'])
            self.assertEqual(2,d.burst_count(obs,decision,16));self.assertEqual(0,d.burst_count(obs,decision,1))

    def test_only_observed_adjacent_closed_unprotected_gate_allows_pair(self):
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            base=corridor(direction,0,opened=False)
            self.assertTrue(nav.closed_gate_entry(base,direction))
            for fault in ('open','unknown','gold','origin','protected','next_neighbor','visible','direction'):
                s=deepcopy(base);which=direction
                if fault=='open':s.tiles[(dx,dy)]='floor'
                elif fault=='unknown':s.tiles.pop((dx,dy))
                elif fault=='gold':s.tiles.pop((dx-dy,dy+dx))
                elif fault=='origin':s.tiles[(0,0)]='item'
                elif fault=='protected':s.protected.add((dx,dy))
                elif fault=='next_neighbor':s.protected.add((2*dx,2*dy))
                elif fault=='visible':s.goods='visible'
                else:which=next(k for k,v in nav.DIRECTIONS.items() if v==(-dx,-dy))
                self.assertFalse(nav.closed_gate_entry(s,which),fault)

    def test_gate_two_single_rpcs_follow_live_beats_without_intermediate_work(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,_,sent):
            before,model=gate_frame(d);call=d.client.call;events=[];checkpoint=d.checkpoint;cap_count=len(captures)
            def rpc(method,params,timeout):
                result=call(method,params,timeout)
                events.append(('input' if method=='run_steps' else 'guard',now[0]))
                if method=='run_steps':now[0]+=400_000_000
                return result
            def save():events.append(('checkpoint',now[0]));checkpoint()
            with patch.object(d.client,'call',side_effect=rpc),patch.object(d,'checkpoint',side_effect=save):
                self.assertEqual(2,d.perform('left',before,model,count=2))
            inputs=[v for k,v in events if k=='input'];self.assertEqual(model['period_ns'],inputs[1]-inputs[0])
            self.assertEqual([],events[events.index(('input',inputs[0]))+1:events.index(('input',inputs[1]))])
            self.assertEqual(cap_count,len(captures));self.assertEqual([walk.move_batch('left')]*2,sent)

    def test_gate_horizon_and_last_input_budget_never_send_only_opener(self):
        for fault in ('frame','phase','foreground','remaining','single_request'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=gate_frame(d);target=now[0]+300_000_000;guard=d.guard
                if fault=='frame':before['_captured']=target-walk.LEAD_NS-2_600_000_000
                if fault=='phase':model['last_sample_ns']=target-walk.LEAD_NS-2_600_000_000
                if fault=='remaining':d.state['actions']=[{'scheduled_inputs':1}]*15
                def front():return guard()-500_000_000 if fault=='foreground' else guard()
                with patch.object(d,'guard',side_effect=front),patch.object(beat_sync,'next_target',return_value=target):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model,count=1 if fault=='single_request' else 2)
                self.assertEqual([],sent);self.assertFalse(d.pending)
                if fault in ('frame','phase','foreground'):
                    self.assertEqual('dispatch_window_expired',caught.exception.code)
                    self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                    self.assertIsNone(d.state['actions'][-1]['issued_ns'])
                elif fault=='remaining':self.assertEqual('walk_limit',caught.exception.code)
                else:self.assertEqual('method_not_allowed',caught.exception.code)

    def test_protected_goods_beyond_gate_never_downgrade_to_single_opener(self):
        for count in (1,2):
            with self.subTest(count=count),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=gate_frame(d);scene=d.scene(before)
                scene.protected.add((-2,0))
                decision=d.choose(before)
                self.assertEqual('gate_single_probe',decision['reason'])
                self.assertFalse(nav.closed_gate_entry(scene,'left'))
                self.assertEqual(0,d.burst_count(before,decision,16))
                with self.assertRaises(ProbeError) as caught:d.perform('left',before,model,count=count)
                self.assertEqual('method_not_allowed',caught.exception.code)
                self.assertEqual([],sent);self.assertFalse(d.pending)

    def test_gate_second_foreground_boundary_includes_allowed_host_lateness(self):
        for slack in (0,-1):
            with self.subTest(slack=slack),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=gate_frame(d);target=now[0]+300_000_000
                front=target+model['period_ns']-walk.LEAD_NS+walk.DISPATCH_LATE_NS-1_000_000_000+slack
                with patch.object(d,'guard',return_value=front),patch.object(beat_sync,'next_target',return_value=target):
                    if slack==0:self.assertEqual(2,d.perform('left',before,model,count=2))
                    else:
                        with self.assertRaises(ProbeError) as caught:d.perform('left',before,model,count=2)
                        self.assertEqual('dispatch_window_expired',caught.exception.code)
                self.assertEqual(2 if slack==0 else 0,len(sent))

    def test_gate_late_ack_unknown_and_cancel_do_not_repeat(self):
        for fault in ('late','unknown','cancel'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=gate_frame(d);call=d.client.call
                def rpc(method,params,timeout):
                    reply=call(method,params,timeout)
                    if method=='run_steps':
                        if fault=='late':now[0]+=model['period_ns']+walk.DISPATCH_LATE_NS+1
                        elif fault=='unknown':return RpcReply({}, {})
                        else:walk.base.supervisor._cancel_requested=True
                    return reply
                try:
                    with patch.object(d.client,'call',side_effect=rpc):
                        if fault=='late':self.assertEqual(1,d.perform('left',before,model,count=2))
                        else:
                            with self.assertRaises(ProbeError):d.perform('left',before,model,count=2)
                finally:walk.base.supervisor._cancel_requested=False
                self.assertEqual(1,len(sent));self.assertIsNone(d._followup_token)
                self.assertEqual(fault=='unknown',d.pending)

    def test_visual_closed_to_entry_counts_one_move_and_sets_context(self):
        # Synthetic images test world displacement and gate context; not device entry evidence.
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            ground=terrain()
            for sign in (-1,1):tile(ground,(dx-sign*dy,dy+sign*dx),(160,130,45))
            closed=ground.copy();tile(closed,(dx,dy),(65,44,22))
            before=nav.scan(closed)
            with tempfile.TemporaryDirectory() as folder:
                d,clock=old.SyncDeadlineTests.build(self,folder)
                for amount,expected in ((1,'gate_entered'),(2,'unexpected'),(-1,'unexpected')):
                    after=nav.scan(shifted(ground,-36*amount*dx,-36*amount*dy));d.entrance=None
                    def obs(scene):o=old.obs();o['_extra']['scene']=scene;return o
                    self.assertEqual(expected,d.movement(obs(before),obs(after),direction,expected_steps=2))
                    self.assertEqual({'gate':(dx,dy),'direction':direction} if amount==1 else None,d.entrance)
                invalid=nav.scan(shifted(ground,-36*dx,-36*dy))
                invalid.tiles.pop((-dy,dx));d.entrance={'gate':(-dx,-dy),'direction':direction}
                self.assertEqual('unknown',d.movement(obs(before),obs(invalid),direction,expected_steps=2))
                self.assertEqual({'gate':(-dx,-dy),'direction':direction},d.entrance)
                opened=nav.scan(ground);d.entrance=None
                self.assertEqual('door_opened',d.movement(obs(before),obs(opened),direction,expected_steps=2))
                self.assertIsNone(d.entrance)

    def test_walk_gate_entry_credits_one_and_consumes_two_input_slots(self):
        class Driver(old.Fake):
            def burst_count(self,frame,decision,remaining):return 2
            def note_step(self,index,direction,before,after,outcome,decision,count=1):self.indices.append((index,count))
        d=Driver([old.obs(),old.obs(),old.obs('visible')],['gate_entered']);d.indices=[]
        walk.walk(d)
        self.assertEqual([(1,2),(3,2)],d.indices)
        self.assertEqual(1,d.state['moves_confirmed']);self.assertEqual([-1,0],d.state['position'])
        self.assertEqual(1,d.state['door_changes']);self.assertTrue(d.state['goods_visible'])
        self.assertEqual(['resume','left','left','pause'],d.sent)
        for limit,reason in ((16,'no_safe_path'),(1,'walk_limit')):
            d=Driver([old.obs()]);d.burst_count=lambda *args:0;d.indices=[]
            with patch.object(walk,'MAX_STEPS',limit):walk.walk(d)
            self.assertEqual(['resume','pause'],d.sent);self.assertEqual(reason,d.state['reason'])

if __name__=='__main__':unittest.main()
