"""TEST026: 単一タッチ2回の絶対時刻、未送信/不明、停止画像の余裕。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from necroprobe import shop_walk as p
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_walk_burst as burst
import test_shop_walk as old


class SequenceTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime
    corridor=burst.BurstTests.corridor

    def test_device_measured_first_ack_fits_next_absolute_beat_without_extra_work(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,caps,_,sent):
            before,model=d.synchronize(d.observe());self.corridor(before)
            call=d.client.call;checkpoint=d.checkpoint;events=[];captures=len(caps)
            def rpc(method,params,timeout):
                result=call(method,params,timeout)
                if method=='run_steps':events.append(('input',now[0]));now[0]+=487_135_000
                elif method=='device_info':events.append(('guard',now[0]))
                return result
            def persist():events.append(('checkpoint',now[0]));checkpoint()
            with patch.object(d.client,'call',side_effect=rpc),patch.object(d,'checkpoint',side_effect=persist):
                self.assertEqual(2,d.perform('left',before,model,count=2))
            inputs=[v for k,v in events if k=='input']
            self.assertEqual(2,len(inputs));self.assertEqual(model['period_ns'],inputs[1]-inputs[0])
            middle=events[events.index(('input',inputs[0]))+1:events.index(('input',inputs[1]))]
            self.assertEqual([],middle);self.assertEqual(captures,len(caps))
            self.assertEqual([p.move_batch('left')]*2,sent)
            self.assertEqual([1,1],[a['scheduled_inputs'] for a in d.state['actions']])

    def test_planned_count_survives_downgrade_unknown_and_report_roundtrip(self):
        for mode in ('single','pair','downgrade','unknown'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=d.synchronize(d.observe());self.corridor(before)
                planned=1 if mode=='single' else 2
                target=now[0]+300_000_000
                if mode=='downgrade':before['_captured']=target-p.LEAD_NS-2_600_000_000
                call=d.client.call
                def rpc(method,params,timeout):
                    if mode=='unknown' and method=='run_steps':return RpcReply({}, {})
                    return call(method,params,timeout)
                with patch('necroprobe.beat_sync.next_target',return_value=target),patch.object(d.client,'call',side_effect=rpc):
                    if mode=='unknown':
                        with self.assertRaises(ProbeError):d.perform('left',before,model,count=planned)
                    else:actual=d.perform('left',before,model,count=planned)
                first=d.state['actions'][0];self.assertEqual(planned,first['planned_inputs'])
                if mode!='unknown':self.assertEqual(2 if mode=='pair' else 1,actual)
                self.assertEqual('sequence_window_short' if mode=='downgrade' else None,first['reason'])
                p.write(folder,d.outer);saved=p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
                self.assertEqual(planned,saved['walk']['actions'][0]['planned_inputs'])
                if mode=='unknown':self.assertTrue(d.pending)

    def test_late_first_ack_skips_second_without_shifting_to_a_later_beat(self):
        for extra in (p.DISPATCH_LATE_NS,p.DISPATCH_LATE_NS+1):
            with self.subTest(extra=extra),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=d.synchronize(d.observe());self.corridor(before);call=d.client.call
                def rpc(method,params,timeout):
                    reply=call(method,params,timeout)
                    if method=='run_steps' and len(sent)==1:now[0]+=model['period_ns']+extra
                    return reply
                with patch.object(d.client,'call',side_effect=rpc):actual=d.perform('left',before,model,count=2)
                self.assertEqual(2 if extra==p.DISPATCH_LATE_NS else 1,actual)
                self.assertEqual(actual,len(sent));self.assertFalse(d.pending)
                last=d.state['actions'][-1]
                self.assertEqual(d.state['actions'][0]['target_ns']+model['period_ns'],last['target_ns'])
                if actual==1:
                    self.assertEqual('not_requested',last['outcome']);self.assertIsNone(last['issued_ns'])
                    self.assertIn('run-099.jpg',d.images)

    def test_second_unknown_exception_not_sent_and_cancel_never_repeat_first(self):
        for fault in ('unknown','exception','not_sent','cancel'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=d.synchronize(d.observe());self.corridor(before);call=d.client.call;attempts=[]
                def rpc(method,params,timeout):
                    if method=='run_steps':
                        attempts.append(now[0])
                        if len(attempts)==2:
                            if fault=='exception':raise RuntimeError('transport failed')
                            if fault=='unknown':return RpcReply({}, {})
                            if fault=='not_sent':return RpcReply({'marker':'not_sent'}, {})
                        result=call(method,params,timeout)
                        if fault=='cancel':p.base.supervisor._cancel_requested=True
                        return result
                    return call(method,params,timeout)
                evidence=p.gesture_evidence
                def parse(result):return 'not_sent' if result=={'marker':'not_sent'} else evidence(result)
                try:
                    with patch.object(d.client,'call',side_effect=rpc),patch.object(p,'gesture_evidence',side_effect=parse):
                        with self.assertRaises((ProbeError,RuntimeError)):d.perform('left',before,model,count=2)
                        if fault in ('unknown','exception'):
                            with patch.object(d,'observe',side_effect=AssertionError('pending capture')):d.finish('movement_unconfirmed',None)
                            self.assertTrue(d.pending);self.assertTrue(d.state['input_pending'])
                        else:self.assertFalse(d.pending)
                finally:p.base.supervisor._cancel_requested=False
                self.assertEqual(1 if fault=='cancel' else 2,len(attempts))
                self.assertIn('run-099.jpg',d.images)
                self.assertIsNone(d._followup_token)
                with self.assertRaises(ProbeError):d.followup(object(), 'left',before,model,0,0)
                self.assertEqual(1 if fault=='cancel' else 2,len(attempts))

    def test_near_expiry_stop_frame_is_refreshed_before_pause_with_no_heavy_analysis(self):
        for age,refreshes in ((2_000_000_000,0),(2_000_000_001,1),(2_900_000_000,1)):
            with self.subTest(age=age),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);now[0]+=4_000_000_000;before=d.last;before['_captured']=now[0]-age
                observations=[];actions=[]
                def observe():
                    self.assertTrue(d.finishing);observations.append(True)
                    state='floor' if not actions else 'pause'
                    d.last=dict(before,state=state,_captured=now[0],_extra=None)
                    return d.last
                def perform(action,frame,model=None,count=1):
                    actions.append(action)
                    self.assertLessEqual(now[0]-frame['_captured'],2_000_000_000)
                    now[0]+=200_000_000
                    d.state['actions'].append({'action':'pause'})
                with patch.object(d,'observe',side_effect=observe),patch.object(d,'perform',side_effect=perform):
                    d.finish('movement_unconfirmed',before);d.finish('internal_error',d.last)
                self.assertEqual(['pause'],actions);self.assertEqual(refreshes+1,len(observations));self.assertTrue(d.state['paused'])

    def test_second_target_follows_actual_first_target_after_skipped_candidate(self):
        from necroprobe import beat_sync
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=d.synchronize(d.observe());self.corridor(before)
            before['_captured']=now[0];model['last_sample_ns']=now[0]
            first=now[0]+300_000_000;period=model['period_ns'];original=d.goods;delayed=[False]
            def goods(frame):
                if not delayed[0] and now[0]>=first-p.LEAD_NS:delayed[0]=True;now[0]+=20_000_000
                return original(frame)
            def target(m,current,lead=p.LEAD_NS):return first if current<=first-p.LEAD_NS else first+period
            with patch.object(d,'goods',side_effect=goods),patch.object(beat_sync,'next_target',side_effect=target):
                d.perform('left',before,model,count=2)
            a,b=d.state['actions']
            self.assertEqual(['late','ready'],[q['status'] for q in a['target_checks']])
            self.assertEqual(first+period,a['target_ns']);self.assertEqual(a['target_ns']+period,b['target_ns'])
            self.assertNotEqual(a['target_ns'],b['target_ns'])

    def test_followup_checks_new_clock_after_validation_and_each_authorization_boundary(self):
        for fault in ('validation_late','goods','scene','same_frame_scene','profile','frame','foreground','walk','session'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=d.synchronize(d.observe());self.corridor(before);call=d.client.call;goods=d.goods;changed=[False]
                def rpc(method,params,timeout):
                    reply=call(method,params,timeout)
                    if method=='run_steps' and len(sent)==1:
                        if fault=='goods':d.state['goods_visible']=True
                        if fault=='scene':d.last=deepcopy(before)
                        if fault=='same_frame_scene':before['_extra']['scene']=deepcopy(before['_extra']['scene'])
                        if fault=='profile':model['cadence_profile']['id']='invalid'
                        if fault=='frame':before['_captured']-=3_000_000_000
                        if fault=='foreground':now[0]+=1_000_000_001
                        if fault=='walk':d.state['started_ns']=now[0]-45_000_000_001
                        if fault=='session':d.stop_ns=now[0]
                    return reply
                def checked(frame):
                    if fault=='validation_late' and len(d.state['actions'])==2 and not changed[0]:
                        changed[0]=True;now[0]=d.state['actions'][-1]['target_ns']-p.LEAD_NS+p.DISPATCH_LATE_NS+1
                    return goods(frame)
                with patch.object(d.client,'call',side_effect=rpc),patch.object(d,'goods',side_effect=checked):
                    try:self.assertEqual(1,d.perform('left',before,model,count=2))
                    except ProbeError:pass
                self.assertEqual(1,len(sent));self.assertFalse(d.pending)
                self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])

    def test_report_rejects_legacy_pair_count_and_hard_limits(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=d.synchronize(d.observe());self.corridor(before);d.perform('left',before,model,count=2)
            for actions in ([deepcopy(d.state['actions'][0])]*17,
                            [dict(deepcopy(d.state['actions'][0]),scheduled_inputs=0)]*37,
                            [dict(deepcopy(d.state['actions'][0]),scheduled_inputs=2)],
                            [dict(deepcopy(d.state['actions'][0]),period_ns=522_000_000)]):
                r=deepcopy(d.outer);r['walk']['actions']=actions;p.write(folder,r)
                with self.assertRaises(ValueError):p.read_report(Path(folder)/'report.json',r['run_id'],r['start_ns'])
            r=deepcopy(d.outer);r['walk']['actions']=[deepcopy(r['walk']['actions'][0]) for _ in range(36)]
            for a in r['walk']['actions'][16:]:a['scheduled_inputs']=0
            p.write(folder,r);p.read_report(Path(folder)/'report.json',r['run_id'],r['start_ns'])

    def test_new_stop_image_expiring_during_preparation_never_pauses_or_refreshes_twice(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before=d.observe();before['_captured']=now[0]-2_900_000_000
            capture=d.observe;guard=d.guard;seen=[]
            def observe():seen.append(True);return capture()
            def delayed_guard():
                result=guard()
                if len(seen):now[0]+=3_000_000_001
                return result
            with patch.object(d,'observe',side_effect=observe),patch.object(d,'guard',side_effect=delayed_guard):
                with self.assertRaises(ProbeError):d.finish('movement_unconfirmed',before)
                d.finish('movement_unconfirmed',d.last)
            self.assertEqual(1,len(seen));self.assertEqual([],sent)


if __name__=='__main__':unittest.main()
