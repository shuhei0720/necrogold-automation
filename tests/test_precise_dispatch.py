"""TEST042: sleepの末尾遅れを避けても、10msの送信上限は緩めない。"""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import beat_sync, shop_walk as walk
from necroprobe.validation import ProbeError
import test_shop_walk as old
import test_shop_navigation as oldnav


class PreciseDispatchTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def prepared(self, noisy_input=1, overshoot_ns=23_000_000):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            d,now,_,_,sent=values
            before,model=d.synchronize(d.observe())
            before['_extra']['scene']=oldnav.ShopNavigationBurstTests.corridor('left',6)
            before['_captured']=now[0];model['last_sample_ns']=now[0]
            target=now[0]+500_000_000
            # clock読み取りも100us進む。busy tailが静止時計で停止しない実行模型。
            def clock():
                now[0]+=100_000
                return now[0]
            sleeps=[]
            def sleeper(seconds):
                extra=overshoot_ns if len(sent)==noisy_input-1 else 0
                sleeps.append((now[0],seconds,extra))
                now[0]+=round(seconds*1e9)+extra
            d.clock=clock;d.sleeper=sleeper;d.spin_wait=None
            with patch.object(beat_sync,'next_target',return_value=target):
                yield d,now,sent,before,model,target,sleeps,folder

    def test_public_driver_avoids_sleep_overshoot_on_first_and_each_followup(self):
        for ordinal in (1,2,3,4):
            for overshoot in (13_000_000,23_000_000):
                with self.subTest(ordinal=ordinal,overshoot=overshoot), \
                     self.prepared(ordinal,overshoot) as (d,now,sent,before,model,target,sleeps,folder):
                    actual=0
                    try:actual=d.perform('left',before,model,count=4)
                    except ProbeError:pass
                    self.assertEqual(4,actual)
                    self.assertEqual([walk.move_batch('left')]*4,sent)
                    actions=d.state['actions']
                    self.assertEqual([target+i*model['period_ns'] for i in range(4)],
                                     [a['target_ns'] for a in actions])
                    self.assertTrue(all(0<=a['issued_ns']-(a['target_ns']-walk.LEAD_NS)<=walk.DISPATCH_LATE_NS
                                        for a in actions))
                    self.assertTrue(any(extra for _,_,extra in sleeps))
                    walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])

    def test_late_authorization_check_still_refuses_first_or_any_followup(self):
        for ordinal in (1,2,3,4):
            with self.subTest(ordinal=ordinal),self.prepared(ordinal) as (d,now,sent,before,model,target,_,_):
                goods=d.goods;delayed=[False]
                until=target+(ordinal-1)*model['period_ns']-walk.LEAD_NS
                def slow_validation(frame):
                    if len(sent)==ordinal-1 and now[0]>=until and not delayed[0]:
                        delayed[0]=True;now[0]+=11_000_000
                    return goods(frame)
                actual=0
                with patch.object(d,'goods',side_effect=slow_validation):
                    try:actual=d.perform('left',before,model,count=4)
                    except ProbeError:pass
                self.assertTrue(delayed[0]);self.assertEqual(ordinal-1,actual)
                self.assertEqual(ordinal-1,len(sent))
                self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                self.assertTrue(any(q['status']=='late' for q in d.state['actions'][-1]['target_checks']))

    def test_clock_delay_between_validation_and_tail_never_uses_stale_authorization(self):
        import inspect
        for ordinal in (2,3,4):
            for fault in ('late','cancel','session'):
                with self.subTest(ordinal=ordinal,fault=fault),self.prepared(0,0) as values:
                    d,now,sent,before,model,target,_,_=values
                    until=target+(ordinal-1)*model['period_ns']-walk.LEAD_NS
                    original=d.clock;injected=[]
                    def clock():
                        value=original()
                        caller=inspect.currentframe().f_back.f_code.co_name
                        if (len(sent)==ordinal-1 and not injected and caller in ('wait_until','spin_until')
                                and value>=until-25_000_000):
                            now[0]=until+11_000_000;injected.append(True)
                            if fault=='cancel':walk.base.supervisor._cancel_requested=True
                            if fault=='session':d.stop_ns=now[0]
                            return now[0]
                        return value
                    d.clock=clock
                    try:
                        try:d.perform('left',before,model,count=ordinal)
                        except ProbeError:pass
                        self.assertTrue(injected)
                        self.assertEqual(ordinal-1,len(sent))
                        self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                    finally:walk.base.supervisor._cancel_requested=False

    def test_late_ack_never_retargets_a_followup_to_another_beat(self):
        with self.prepared(2) as (d,now,sent,before,model,target,_,_):
            call=d.client.call
            def late_ack(method,params,timeout):
                result=call(method,params,timeout)
                if method=='run_steps':now[0]+=model['period_ns']+walk.DISPATCH_LATE_NS+1
                return result
            with patch.object(d.client,'call',side_effect=late_ack):
                self.assertEqual(1,d.perform('left',before,model,count=4))
            self.assertEqual(1,len(sent));last=d.state['actions'][-1]
            self.assertEqual(target+model['period_ns'],last['target_ns'])
            self.assertEqual('not_requested',last['outcome']);self.assertFalse(d.pending)

    def test_cancel_session_and_walk_expiry_during_tail_never_send(self):
        for fault in ('cancel','session','walk'):
            with self.subTest(fault=fault),self.prepared() as (d,now,sent,before,model,target,_,_):
                clock=d.clock;injected=[False];until=target-walk.LEAD_NS
                def changing_clock():
                    value=clock()
                    if value>=until-10_000_000 and not injected[0]:
                        injected[0]=True
                        if fault=='cancel':walk.base.supervisor._cancel_requested=True
                        elif fault=='session':d.stop_ns=value
                        else:d.state['started_ns']=value-walk.WALK_SECONDS*1_000_000_000
                    return value
                try:
                    d.clock=changing_clock
                    with self.assertRaises(ProbeError):d.perform('left',before,model,count=1)
                    self.assertTrue(injected[0]);self.assertEqual([],sent)
                    self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                finally:walk.base.supervisor._cancel_requested=False


class DispatchWaitTests(unittest.TestCase):
    def test_long_wait_sleeps_and_only_last_25ms_uses_spin_with_checks_around_it(self):
        from necroprobe.dispatch_wait import SPIN_NS,wait_until
        now=[1_000_000_000];until=now[0]+500_000_000;events=[]
        def clock():return now[0]
        def check():events.append(('check',now[0]));return 8
        def sleeper(seconds):
            events.append(('sleep',seconds));now[0]+=round(seconds*1e9)
        def spin(target):
            events.append(('spin',target-now[0]));now[0]=target
        wait_until(until,clock,sleeper,check,spin)
        self.assertEqual(until,now[0])
        self.assertTrue(all(0<value<=.05 for kind,value in events if kind=='sleep'))
        spins=[value for kind,value in events if kind=='spin']
        self.assertEqual([SPIN_NS],spins)
        index=next(i for i,event in enumerate(events) if event[0]=='spin')
        self.assertEqual('check',events[index-1][0]);self.assertEqual('check',events[index+1][0])

    def test_past_target_checks_once_without_sleep_or_spin(self):
        from necroprobe.dispatch_wait import wait_until
        events=[]
        wait_until(1,lambda:2,lambda _:self.fail('sleep'),lambda:events.append('check'),
                   lambda _:self.fail('spin'))
        self.assertEqual(['check'],events)

    def test_checks_abort_long_wait_before_spin_and_after_tail_spin(self):
        from necroprobe.dispatch_wait import wait_until
        for fault in ('before','after'):
            with self.subTest(fault=fault):
                now=[0];spins=[]
                def check():
                    if fault=='before' or now[0]>=20_000_000:raise ProbeError('cancelled')
                    return 8
                def spin(target):spins.append(target);now[0]=target
                with self.assertRaises(ProbeError):
                    wait_until(20_000_000,lambda:now[0],lambda _:self.fail('sleep'),check,spin)
                self.assertEqual([] if fault=='before' else [20_000_000],spins)


if __name__=='__main__':
    unittest.main()
