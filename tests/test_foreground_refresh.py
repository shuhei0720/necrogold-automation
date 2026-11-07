"""TEST042: 未送信で前面だけが古い時、同じ候補を一度だけ確認する。"""
import tempfile
import unittest
from unittest.mock import patch
from necroprobe import shop_walk as walk, beat_sync
from necroprobe.validation import ProbeError
import test_shop_walk as old


class ForegroundRefreshTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime

    def test_public_perform_refreshes_only_foreground_without_recapture_or_retarget(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,_,sent):
            before,model=d.synchronize(d.observe())
            before['_captured']=now[0];model['last_sample_ns']=now[0]
            origin=now[0];target=origin+1_420_000_000;captured=len(captures)
            guard=d.guard;fronts=[];checkpoint=d.checkpoint;persisted=[False]
            def foreground():
                value=guard();fronts.append(value);return value
            def persist():
                checkpoint()
                if not persisted[0]:persisted[0]=True;now[0]+=1_000_000_000
            original=beat_sync.next_target;targets=[]
            def next_target(*args):
                if len(args)==3:targets.append(target);return target
                return original(*args)
            with patch.object(d,'guard',side_effect=foreground),patch.object(d,'checkpoint',side_effect=persist), \
                 patch.object(beat_sync,'next_target',side_effect=next_target):
                try:count=d.perform('left',before,model)
                except ProbeError:count=None
            self.assertEqual(1,count)
            self.assertEqual([walk.move_batch('left')],sent)
            self.assertEqual(captured,len(captures));self.assertEqual([target],targets)
            self.assertEqual(2,len(fronts))
            check=d.state['actions'][-1]['target_checks'][-1]
            self.assertEqual(fronts[-1],check['window']['foreground_ns'])
            self.assertLessEqual(target-walk.LEAD_NS+walk.DISPATCH_LATE_NS,fronts[-1]+1_000_000_000)

    def test_failed_or_slow_guard_and_expired_sources_never_retarget_or_send(self):
        for fault in ('guard_failure','guard_slow','frame','phase','session','walk','cancel'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,_,sent):
                before,model=d.synchronize(d.observe())
                before['_captured']=now[0];model['last_sample_ns']=now[0]
                origin=now[0];target=origin+1_420_000_000;guards=[];targets=[]
                if fault=='frame':before['_captured']-=2_000_000_000
                if fault=='phase':model['last_sample_ns']-=2_000_000_000
                if fault=='session':d.stop_ns=origin+1_300_000_000
                if fault=='walk':d.state['started_ns']=origin+1_300_000_000-45_000_000_000
                guard=d.guard;checkpoint=d.checkpoint;persisted=[False]
                def foreground():
                    guards.append(True)
                    if len(guards)==2:
                        if fault=='guard_failure':raise ProbeError('foreground_not_verified')
                        if fault=='guard_slow':now[0]+=50_000_001
                        if fault=='cancel':walk.base.supervisor._cancel_requested=True
                    return guard()
                def persist():
                    checkpoint()
                    if not persisted[0]:persisted[0]=True;now[0]+=1_000_000_000
                original=beat_sync.next_target
                def next_target(*args):
                    if len(args)==3:targets.append(target);return target
                    return original(*args)
                try:
                    with patch.object(d,'guard',side_effect=foreground),patch.object(d,'checkpoint',side_effect=persist), \
                         patch.object(beat_sync,'next_target',side_effect=next_target):
                        with self.assertRaises(ProbeError):d.perform('left',before,model)
                    self.assertEqual([],sent);self.assertEqual([target],targets)
                    self.assertEqual(2 if fault in ('guard_failure','guard_slow','cancel') else 1,len(guards))
                    self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])
                    self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                finally:walk.base.supervisor._cancel_requested=False

    def test_one_foreground_refresh_never_weakens_the_new_one_second_boundary(self):
        for offset,accepted in ((10_000_000,True),(9_999_999,False)):
            with self.subTest(offset=offset),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=d.synchronize(d.observe())
                before['_captured']=now[0];model['last_sample_ns']=now[0]
                target=now[0]+1_420_000_000;until=target-walk.LEAD_NS
                guard=d.guard;fronts=[];checkpoint=d.checkpoint;persisted=[False]
                def foreground():
                    value=guard()
                    # 不完全なfresh値でも、更新後の1秒境界を厳密に検査する。
                    if fronts:value=until-1_000_000_000+offset
                    fronts.append(value);return value
                def persist():
                    checkpoint()
                    if not persisted[0]:persisted[0]=True;now[0]+=1_000_000_000
                original=beat_sync.next_target;targets=[]
                def next_target(*args):
                    if len(args)==3:targets.append(target);return target
                    return original(*args)
                with patch.object(d,'guard',side_effect=foreground),patch.object(d,'checkpoint',side_effect=persist), \
                     patch.object(beat_sync,'next_target',side_effect=next_target):
                    if accepted:self.assertEqual(1,d.perform('left',before,model))
                    else:
                        with self.assertRaises(ProbeError):d.perform('left',before,model)
                self.assertEqual(2,len(fronts));self.assertEqual([target],targets)
                self.assertEqual(int(accepted),len(sent))

    def test_unknown_ack_after_refresh_is_never_resent_or_paused(self):
        from necroprobe.protocol import RpcReply
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=d.synchronize(d.observe())
            before['_captured']=now[0];model['last_sample_ns']=now[0]
            target=now[0]+1_420_000_000;checkpoint=d.checkpoint;persisted=[False]
            def persist():
                checkpoint()
                if not persisted[0]:persisted[0]=True;now[0]+=1_000_000_000
            original=beat_sync.next_target;call=d.client.call
            def next_target(*args):return target if len(args)==3 else original(*args)
            def rpc(method,params,timeout):
                reply=call(method,params,timeout)
                return RpcReply({}, {}) if method=='run_steps' else reply
            with patch.object(d,'checkpoint',side_effect=persist),patch.object(d.client,'call',side_effect=rpc), \
                 patch.object(beat_sync,'next_target',side_effect=next_target):
                with self.assertRaises(ProbeError):d.perform('left',before,model)
                calls=len(d.client.calls);d.finish('batch_unknown',None)
            self.assertEqual(1,len(sent));self.assertEqual(calls,len(d.client.calls))
            self.assertTrue(d.pending);self.assertTrue(d.state['input_pending'])


if __name__=='__main__':unittest.main()
