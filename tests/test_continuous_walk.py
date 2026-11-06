"""TEST033: 観測済み直線の3/4拍入力。実機の全経路毎拍歩行とは区別。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from necroprobe import shop_walk as walk, shop_navigation as nav, beat_sync
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_shop_walk as old
import test_shop_navigation as old_nav
from test_shop_navigation import terrain,shifted


def corridor(driver,now):
    before,model=driver.synchronize(driver.observe())
    before['_extra']['scene']=old_nav.ShopNavigationBurstTests.corridor('left',6)
    # 機構試験用の新鮮な取得時刻。端末の処理速度を模擬した結果ではない。
    before['_captured']=now[0];model['last_sample_ns']=now[0]
    return before,model


class ContinuousWalkTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime

    def test_longest_observed_straight_prefix_stops_before_gate_and_goods(self):
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            s=old_nav.ShopNavigationBurstTests.corridor(direction,6);decision=nav.choose(s)
            self.assertEqual(2,nav.burst_count(s,decision))
            self.assertEqual(4,nav.burst_count(s,decision,limit=4))
            for distance,count in ((2,1),(3,2),(4,3),(5,4)):
                s=old_nav.ShopNavigationBurstTests.corridor(direction,distance)
                self.assertEqual(count,nav.burst_count(s,nav.choose(s),limit=4))
            s=old_nav.ShopNavigationBurstTests.corridor(direction,6);s.protected.add((4*dx,4*dy))
            self.assertEqual(1,nav.burst_count(s,decision,limit=4))  # 選択先への経路自体が遮断。
            nearby=dict(decision,target=(3*dx,3*dy))
            self.assertEqual(2,nav.burst_count(s,nearby,limit=4))
            s.goods='partial';self.assertEqual(1,nav.burst_count(s,decision,limit=4))

    def test_four_absolute_beats_with_foreground_renewal_and_no_images(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,_,sent):
            before,model=corridor(d,now);call=d.client.call;guards=[];images=len(captures)
            self.assertEqual(4,d.burst_count(before,d.choose(before),16))
            def rpc(method,params,timeout):
                result=call(method,params,timeout)
                if method=='run_steps':now[0]+=390_000_000
                if method=='device_info':guards.append(now[0])
                return result
            with patch.object(d.client,'call',side_effect=rpc):self.assertEqual(4,d.perform('left',before,model,count=4))
            self.assertEqual(4,len(sent));self.assertEqual(images,len(captures));self.assertGreaterEqual(len(guards),2)
            actions=d.state['actions'];first=actions[0]['target_ns']
            self.assertEqual([first+i*model['period_ns'] for i in range(4)],[a['target_ns'] for a in actions])
            self.assertEqual([model['period_ns']]*3,[b['issued_ns']-a['issued_ns'] for a,b in zip(actions,actions[1:])])
            self.assertEqual([4,0,0,0],[a['planned_inputs'] for a in actions])
            walk.write(folder,d.outer);walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])

    def test_full_sequence_trims_to_frame_horizon_before_first_input(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=corridor(d,now);target=now[0]+300_000_000
            before['_captured']=target+2*model['period_ns']+50_000_000-3_000_000_000
            with patch.object(beat_sync,'next_target',return_value=target):actual=d.perform('left',before,model,count=4)
            self.assertEqual(3,actual);self.assertEqual(3,len(sent))
            self.assertEqual('sequence_window_short',d.state['actions'][0]['reason'])

    def test_renewal_delay_or_foreground_change_never_sends_late_third(self):
        for fault in ('late','foreground'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=corridor(d,now);guard=d.guard;calls=[]
                def checked():
                    calls.append(True)
                    if len(calls)>1:
                        if fault=='foreground':raise ProbeError('foreground_not_verified')
                        now[0]+=2_000_000_000
                    return guard()
                with patch.object(d,'guard',side_effect=checked):
                    if fault=='foreground':
                        with self.assertRaises(ProbeError):d.perform('left',before,model,count=4)
                    else:self.assertEqual(2,d.perform('left',before,model,count=4))
                self.assertEqual(2,len(sent));self.assertIsNone(d._followup_token);self.assertFalse(d.pending)

    def test_third_unknown_cancel_and_late_stop_without_fourth_or_retry(self):
        for fault in ('unknown','cancel','late'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=corridor(d,now);call=d.client.call
                def rpc(method,params,timeout):
                    result=call(method,params,timeout)
                    if method=='run_steps' and len(sent)==3:
                        if fault=='unknown':return RpcReply({}, {})
                        if fault=='cancel':walk.base.supervisor._cancel_requested=True
                        else:now[0]+=model['period_ns']+walk.DISPATCH_LATE_NS+1
                    return result
                try:
                    with patch.object(d.client,'call',side_effect=rpc):
                        if fault=='late':self.assertEqual(3,d.perform('left',before,model,count=4))
                        else:
                            with self.assertRaises(ProbeError):d.perform('left',before,model,count=4)
                finally:walk.base.supervisor._cancel_requested=False
                self.assertEqual(3,len(sent));self.assertIsNone(d._followup_token);self.assertEqual(fault=='unknown',d.pending)

    def test_four_input_plan_never_exceeds_route_or_remaining_total(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=corridor(d,now)
            for count in (0,5,True):
                with self.assertRaises(ProbeError):d.perform('left',before,model,count=count)
            d.state['actions']=[{'scheduled_inputs':1}]*13
            self.assertEqual(3,d.perform('left',before,model,count=4))
            self.assertEqual(16,sum(a['scheduled_inputs'] for a in d.state['actions']))
            self.assertEqual(3,len(sent))

    def test_later_unknown_or_exception_keeps_pending_and_blocks_cleanup(self):
        for number in (3,4):
            for fault in ('unknown','exception'):
                with self.subTest(number=number,fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                    before,model=corridor(d,now);call=d.client.call
                    def rpc(method,params,timeout):
                        reply=call(method,params,timeout)
                        if method=='run_steps' and len(sent)==number:
                            if fault=='exception':raise RuntimeError('transport failure')
                            return RpcReply({}, {})
                        return reply
                    with patch.object(d.client,'call',side_effect=rpc):
                        with self.assertRaises((RuntimeError,ProbeError)):d.perform('left',before,model,count=4)
                        with patch.object(d,'observe',side_effect=AssertionError('pending capture')):
                            d.finish('movement_unconfirmed',None)
                    self.assertEqual(number,len(sent));self.assertTrue(d.pending)
                    self.assertTrue(d.state['input_pending']);self.assertIsNone(d._followup_token)

    def test_actual_sent_count_is_used_for_motion_and_next_index(self):
        class Long(old.Fake):
            def burst_count(self,*args):return 4
            def perform(self,action,frame,model=None,count=1):
                super().perform(action,frame,model);return 3 if action in walk.MOVE_POINTS else 0
            def movement(self,before,after,direction,expected_steps=1):
                self.expected.append(expected_steps);return 'moved'
            def note_step(self,index,direction,before,after,outcome,decision,count=1):self.indices.append((index,count))
        d=Long([old.obs(),old.obs(),old.obs('visible')]);d.expected=[];d.indices=[]
        walk.walk(d)
        self.assertEqual([3],d.expected);self.assertEqual([(1,3),(4,3)],d.indices)
        self.assertEqual(3,d.state['moves_confirmed']);self.assertEqual([-3,0],d.state['position'])

    def test_native_scores_include_extra_competitors_only_for_long_sequences(self):
        from necroprobe import motion_stats
        before_image=terrain();before=nav.scan(before_image);original=nav._pillow_motion_scores
        for steps in (2,4):
            after=nav.scan(shifted(before_image,36*steps,0));calls=[]
            def extra(a,b,extra=False):calls.append(extra);return original(a,b,extra=extra)
            with patch.object(motion_stats,'scores',side_effect=lambda a,b:original(a,b)),patch.object(nav,'_pillow_motion_scores',side_effect=extra):
                self.assertEqual('moved',nav.motion(before,after,'left',expected_steps=steps))
            self.assertEqual([] if steps==2 else [True],calls)
        after=nav.scan(shifted(before_image,144,0))
        def ambiguous(a,b,extra=False):
            candidates=original(a,b,extra=extra);score=min(candidates)[0]
            return [(score if (x,y)==(-36,0) else value,x,y) for value,x,y in candidates]
        with patch.object(motion_stats,'scores',side_effect=lambda a,b:original(a,b)),patch.object(nav,'_pillow_motion_scores',side_effect=ambiguous):
            self.assertEqual('unknown',nav.motion(before,after,'left',expected_steps=4))

    def test_three_four_tile_displacement_signed_and_partial_not_credited(self):
        before_image=terrain();before=nav.scan(before_image)
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            for steps in (3,4):
                after=nav.scan(shifted(before_image,-36*steps*dx,-36*steps*dy))
                self.assertEqual('moved',nav.motion(before,after,direction,expected_steps=steps))
                reverse=next(k for k,v in nav.DIRECTIONS.items() if v==(-dx,-dy))
                self.assertEqual('unexpected',nav.motion(before,after,reverse,expected_steps=steps))
            after=nav.scan(shifted(before_image,-72*dx,-72*dy))
            self.assertEqual('partial',nav.motion(before,after,direction,expected_steps=4))
        class Long(old.Fake):
            def burst_count(self,*args):return 4
            def perform(self,action,frame,model=None,count=1):super().perform(action,frame,model);return count
        d=Long([old.obs(),old.obs()],['partial']);walk.walk(d)
        self.assertEqual(0,d.state['moves_confirmed']);self.assertEqual('movement_unconfirmed',d.state['reason'])
        d=Long([old.obs(),old.obs('visible')]);walk.walk(d)
        self.assertTrue(d.state['goods_visible']);self.assertEqual(['resume','left','pause'],d.sent)

if __name__=='__main__':unittest.main()
