import tempfile
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from necroprobe import shop_walk as p
from necroprobe.validation import ProbeError
from test_resume_once import GOOD

def obs(goods='unknown'):
    return {'state':'floor','_extra':{'scene':goods},'_sha':'a'*64,'_seen_ns':1,'_raw':b'x'}

class Fake:
    def __init__(self,frames,motions=(),unknown=False):
        self.state=p.new_walk();self.frames=iter(frames);self.motions=iter(motions)
        self.pending=False;self.sent=[];self.unknown=unknown;self.last=None
        self.clock=lambda:1;self.stop_ns=100_000_000_000
    def observe(self):self.last=next(self.frames);return self.last
    def goods(self,o):return o['_extra']['scene']
    def synchronize(self,o):return o,{'period_ns':520_000_000}
    def choose(self,o):return {'direction':'left','target':[-1,0],'reason':'approach'}
    def movement(self,a,b,d):return next(self.motions)
    def perform(self,a,o,model=None):
        self.sent.append(a);self.state['paused']=False
        if self.unknown and a=='left':self.pending=True;raise ProbeError('batch_unknown')
    def checkpoint(self):pass
    def save(self,n,o):pass
    def finish(self,reason,o):
        self.state['reason']=reason
        if not self.pending:self.sent.append('pause');self.state['paused']=True
    def note_step(self,*args):pass

class WalkTests(unittest.TestCase):
    def test_09_analysis_failure_keeps_new_frame_and_pauses_once(self):
        import base64, io
        from types import SimpleNamespace
        from PIL import Image
        from necroprobe import gold_scan, shop_navigation, beat_sync
        from necroprobe.protocol import RpcReply
        from test_source_geometry import geometry_payload
        from test_gold_scan import floor
        from test_restart_loop import LiveStub, A, P
        buf=io.BytesIO();floor().save(buf,'JPEG');raw=buf.getvalue()
        _,payload=geometry_payload(p.base.resume.CAPTURE_PARAMS,size=(896,414),source_scale=2)
        payload.update(data=base64.b64encode(raw).decode(),source_orientation=2)
        class Capture(LiveStub):
            def call(self,method,params,timeout):
                if method=='screenshot':return RpcReply(payload,{})
                return super().call(method,params,timeout)
        for stage,goods in (('navigation','unknown'),('beat_extract','unknown'),('beat_extract','visible')):
            with self.subTest(stage=stage,goods=goods), tempfile.TemporaryDirectory() as folder:
                now=1_000_000_000;r=p.new_report(now,'d'*32);r['phase']='walk'
                d=p.Driver(Capture(),r,folder,now+20_000_000_000,folder,clock=lambda:now)
                d.last={'state':'pause','_captured':now,'_raw':b'old'}
                fail=TypeError('PRIVATE_TOKEN must not be saved')
                with patch.object(gold_scan,'analyze_image',side_effect=[deepcopy(A),deepcopy(P)]), \
                     patch.object(shop_navigation,'scan',side_effect=fail if stage=='navigation' else None,
                                  return_value=SimpleNamespace(goods=goods)), \
                     patch.object(beat_sync,'extract',side_effect=fail if stage=='beat_extract' else None):
                    with self.assertRaises(ProbeError) as caught:d.observe()
                    self.assertEqual('walk_analysis_failed',caught.exception.code)
                    self.assertEqual('floor',d.last['state']);self.assertEqual(raw,d.last['_raw'])
                    d.finish(caught.exception.code,d.last)
                    d.finish(caught.exception.code,d.last)
                self.assertTrue(d.state['paused']);self.assertEqual(1,d.client.calls.count('run_steps'))
                self.assertEqual({'stage':stage,'kind':'TypeError'},d.state['failure'])
                self.assertEqual(goods=='visible',d.state['goods_visible'])
                self.assertNotIn('PRIVATE_TOKEN',str(r));self.assertEqual(1,len(d.state['navigation_ms']))
                if stage=='beat_extract':self.assertEqual(1,len(d.state['beat_extract_ms']))
                p.write(folder,r);p.read_report(Path(folder)/'report.json','d'*32,now)

    def test_10_cleanup_rechecks_foreground_age_and_pending(self):
        from test_restart_loop import LiveStub
        for boundary in ('stale','other_app','pending','deadline','checkpoint_deadline'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                now=5_000_000_000;r=p.new_report(1,'b'*32);r['phase']='walk'
                d=p.Driver(LiveStub(),r,folder,now+20_000_000_000,folder,clock=lambda:now)
                d.last=dict(obs(),_captured=now)
                if boundary=='stale':d.last['_captured']=1
                elif boundary=='other_app':d.client.system={'foreground_app':'other','screen_locked':False}
                elif boundary=='pending':d.pending=True;d.state['input_pending']=True
                elif boundary=='deadline':d.stop_ns=now
                else:
                    original=d.checkpoint;calls=[0]
                    def expire():
                        calls[0]+=1;original()
                        if calls[0]==2:d.stop_ns=now
                    d.checkpoint=expire
                try:d.finish('walk_analysis_failed',d.last)
                except ProbeError:pass
                self.assertNotIn('run_steps',d.client.calls)

    def test_11_worker_handles_internal_failure_before_timer_exit(self):
        from contextlib import contextmanager, nullcontext
        import time
        from necroprobe.protocol import RpcReply
        from test_restart_loop import LiveStub, P
        active=[False]
        @contextmanager
        def timer():
            active[0]=True
            try:yield object()
            finally:active[0]=False
        class Client(LiveStub):
            def call(client,method,params,timeout):
                if method=='launch_app':return RpcReply({}, {})
                if method=='run_steps':self.assertTrue(active[0])
                return super().call(method,params,timeout)
        for stale in (False, True):
            with self.subTest(stale=stale), tempfile.TemporaryDirectory() as folder:
                start=time.monotonic_ns();run_id='9'*32;client=Client()
                args=p.parser().parse_args(['--worker','--output',folder,'--checkpoint-dir',folder,
                    '--run-id',run_id,'--start-ns',str(start),'--stop-ns',str(start+20_000_000_000)])
                p.write(folder,p.new_report(start,run_id))
                def collect(d,**kwargs):
                    d.report.update(candidate=True,paused=True,reason='gold_candidate')
                    d.last=dict(P,_captured=d.clock(),_raw=b'pause',_sha='1'*64)
                def fail(d):
                    d.state['started_ns']=d.clock()
                    d.perform('resume',d.last)
                    if not stale:d.last=dict(obs(),_captured=d.clock())
                    raise ValueError('SECRET failure')
                def paused(d):
                    d.last=dict(P,_captured=d.clock(),_raw=b'pause',_sha='1'*64)
                    return d.last
                with patch.object(p.base,'device_lock',return_value=nullcontext()), \
                     patch.object(p.base,'load_pairing',return_value=(b'key','token')), \
                     patch.object(p.base,'Crypto',return_value=type('Crypto',(),{'engine':'python'})()), \
                     patch.object(p.base,'OwnedRpcTimer',timer), \
                     patch.object(p,'WalkClient',return_value=client), \
                     patch.object(p.base,'collect',collect),patch.object(p,'walk',fail), \
                     patch.object(p.Driver,'observe',paused):
                    self.assertEqual(0,p.worker(args))
                r=p.read_report(Path(folder)/'report.json',run_id,start)
                self.assertEqual('internal_error',r['reason']);self.assertNotIn('SECRET',str(r))
                self.assertEqual(not stale,r['walk']['paused'])
                self.assertEqual(['resume'] if stale else ['resume','pause'],
                                 [a['action'] for a in r['walk']['actions']])
                self.assertEqual({'stage':'control','kind':'ValueError'},r['walk']['failure'])

    def test_12_diagnostic_schema_rejects_unbounded_values(self):
        with tempfile.TemporaryDirectory() as folder:
            for bad in ({'failure':{'stage':'arbitrary','kind':'TypeError'}},
                        {'failure':{'stage':'navigation','kind':'private message'}},
                        {'failure':{'stage':'navigation','kind':[]}},
                        {'failure':{'stage':{},'kind':'TypeError'}},
                        {'pillow_version':'x'*33}, {'navigation_ms':[float('inf')]}):
                r=p.new_report(1,'8'*32);r['walk'].update(bad)
                # allow_nan=False itself rejects Infinity before persistence.
                with self.assertRaises((ValueError,ProbeError)):
                    p.write(folder,r);p.read_report(Path(folder)/'report.json','8'*32,1)

    def test_01_goods_latches_before_motion_and_no_more_input(self):
        d=Fake([obs(),obs('visible')],['unexpected'])
        p.walk(d)
        self.assertEqual(['resume','left','pause'],d.sent)
        self.assertTrue(d.state['goods_visible']);self.assertTrue(d.state['paused'])
    def test_02_unknown_input_never_sends_cleanup_pause(self):
        d=Fake([obs()],unknown=True)
        with self.assertRaises(ProbeError):p.walk(d)
        d.finish('batch_unknown',d.last)
        self.assertEqual(['resume','left'],d.sent)
        self.assertFalse(d.state['paused'])
    def test_03_only_expected_one_step_or_door_change_allows_continuation(self):
        for motion in ('blocked','unexpected','unknown'):
            d=Fake([obs(),obs()], [motion])
            p.walk(d)
            self.assertEqual(['resume','left','pause'],d.sent)
            self.assertEqual(0,d.state['moves_confirmed'])
        d=Fake([obs(),obs(),obs('visible')],['tween'])
        p.walk(d);self.assertTrue(d.state['goods_visible'])
        self.assertEqual(['resume','left','pause'],d.sent)
    def test_04_fixed_gestures_and_reply_shape(self):
        c=p.WalkClient(lambda *a:None)
        for direction in p.MOVE_POINTS:
            with self.assertRaises(ProbeError):c._validate('run_steps',p.move_batch(direction))
            c.walking=True;c._validate('run_steps',p.move_batch(direction));c.walking=False
        c.walking=True
        with self.assertRaises(ProbeError):c._validate('run_steps',p.base.batch('restart'))
        for direction,point in p.MOVE_POINTS.items():
            gesture=p.move_batch(direction)['steps'][1]['params']['fingers'][0]
            self.assertEqual(point,(gesture[0]['x'],gesture[0]['y']))
            self.assertEqual([0,.05],[s['t'] for s in gesture])
        r=deepcopy(GOOD);r['steps'][1]['method']='gesture'
        self.assertEqual('acknowledged',p.gesture_evidence(r))
        self.assertEqual('unknown',p.gesture_evidence(GOOD))
    def test_05_report_does_not_inherit_search_pause(self):
        with tempfile.TemporaryDirectory() as folder:
            r=p.new_report(1,'c'*32);r['search']['paused']=True
            p.write(Path(folder),r)
            got=p.read_report(Path(folder)/'report.json','c'*32,1)
            self.assertFalse(got['walk']['paused']);self.assertFalse(got['walk']['device_timing_verified'])
            r['walk']['paused']='yes';p.write(Path(folder),r)
            with self.assertRaises((ValueError,ProbeError)):p.read_report(Path(folder)/'report.json','c'*32,1)

    def test_06_runtime_unknown_gesture_keeps_pending_and_blocks_cleanup(self):
        from test_restart_loop import LiveStub
        from necroprobe import beat_sync
        with tempfile.TemporaryDirectory() as folder:
            now=[1_000_000_000];r=p.new_report(now[0],'e'*32);r['phase']='walk'
            d=p.Driver(LiveStub(),r,folder,now[0]+20_000_000_000,folder,clock=lambda:now[0])
            d.state['started_ns']=now[0]
            d.sleeper=lambda seconds:now.__setitem__(0,now[0]+round(seconds*1e9))
            d.last=dict(obs(),_captured=now[0]);target=now[0]+600_000_000
            # tapと名付けられた応答はgesture成功と扱わない。
            with patch.object(beat_sync,'next_target',return_value=target):
                with self.assertRaises(ProbeError):d.perform('left',d.last,{'period_ns':520_000_000})
            self.assertTrue(d.pending);self.assertTrue(d.state['input_pending'])
            calls=len(d.client.calls);d.finish('batch_unknown',d.last)
            self.assertEqual(calls,len(d.client.calls))
            p.read_report(Path(folder)/'report.json','e'*32,1_000_000_000)

    def test_07_pause_ack_then_capture_failure_does_not_toggle_again(self):
        from test_restart_loop import LiveStub
        with tempfile.TemporaryDirectory() as folder:
            now=1_000_000_000;r=p.new_report(now,'f'*32);r['phase']='walk'
            d=p.Driver(LiveStub(),r,folder,now+20_000_000_000,folder,clock=lambda:now)
            d.last=dict(obs('visible'),_captured=now);d.state['goods_visible']=True
            with patch.object(d,'observe',side_effect=ProbeError('connection_error')):
                with self.assertRaises(ProbeError):d.finish('goods_visible',d.last)
                d.finish('goods_visible',d.last)
            self.assertEqual(1,d.client.calls.count('run_steps'))
            self.assertFalse(d.state['paused']);self.assertTrue(d.state['goods_visible'])

    def test_08_last_sync_observation_keeps_goods_even_if_checkpoint_fails(self):
        from types import SimpleNamespace
        from test_restart_loop import LiveStub
        from necroprobe import beat_sync
        with tempfile.TemporaryDirectory() as folder:
            now=1_000_000_000;r=p.new_report(now,'a'*32);r['phase']='walk'
            d=p.Driver(LiveStub(),r,folder,now+100_000_000_000,folder,clock=lambda:now)
            d.state['started_ns']=now;d.sleeper=lambda seconds:None
            regular=dict(obs(),_extra={'scene':SimpleNamespace(goods='unknown'),'beat':None})
            visible=dict(regular,_extra={'scene':SimpleNamespace(goods='visible'),'beat':None})
            with patch.object(p.base.RuntimeDriver,'observe',side_effect=[regular]*11+[visible]):
                result,model=d.synchronize(regular)
            self.assertIs(result,visible);self.assertIsNone(model);self.assertTrue(d.state['goods_visible'])
            d.state['goods_visible']=False
            with patch.object(p.base.RuntimeDriver,'observe',return_value=visible), \
                 patch.object(d,'checkpoint',side_effect=OSError('write failed')):
                with self.assertRaises(OSError):d.observe()
            self.assertTrue(d.state['goods_visible'])

class SyncDeadlineTests(unittest.TestCase):
    def build(self,folder):
        from types import SimpleNamespace
        from test_restart_loop import LiveStub
        now=[1_000_000_000];r=p.new_report(now[0],'6'*32);r['phase']='walk'
        d=p.Driver(LiveStub(),r,folder,now[0]+100_000_000_000,folder,clock=lambda:now[0])
        d.state['started_ns']=now[0]
        d.sleeper=lambda seconds:now.__setitem__(0,now[0]+round(seconds*1e9))
        d.last=dict(obs(),_captured=now[0],_extra={'scene':SimpleNamespace(goods='unknown'),'beat':None})
        return d,now

    def test_13_sync_never_starts_capture_after_deadline_or_sleep_jitter(self):
        for delay in (11_999_999_999,12_000_000_000,12_000_000_001):
            with self.subTest(delay=delay),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);start=now[0];captures=[]
                d.sleeper=lambda seconds:now.__setitem__(0,now[0]+delay)
                def capture():
                    captures.append(now[0]);now[0]+=1;return d.last
                with patch.object(d,'observe',side_effect=capture):
                    with self.assertRaises(ProbeError) as caught:d.synchronize(d.last)
                self.assertEqual('beat_sync_timeout',caught.exception.code)
                self.assertEqual([start+delay] if delay<12_000_000_000 else [],captures)
                self.assertIsNone(d.model)

    def test_14_slow_observation_cannot_start_next_capture_or_supply_model(self):
        for delay,expected in ((4_000_000_000,3),(12_000_000_000,1),(12_000_000_001,1)):
            with self.subTest(delay=delay),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);start=now[0];captures=[]
                def capture():
                    captures.append(now[0]);now[0]+=delay;return d.last
                with patch.object(d,'observe',side_effect=capture):
                    with self.assertRaises(ProbeError) as caught:d.synchronize(d.last)
                self.assertEqual('beat_sync_timeout',caught.exception.code)
                self.assertEqual(expected,len(captures))
                self.assertTrue(all(t<start+12_000_000_000 for t in captures))
                self.assertIsNone(d.model);self.assertEqual([],d.state['models'])

    def test_15_fit_and_checkpoint_cannot_return_model_at_deadline(self):
        from test_beat_sync import observations
        from necroprobe import beat_sync
        from types import SimpleNamespace
        samples=observations(8)
        for boundary in ('fit','checkpoint','compatible_fit'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);now[0]=samples[-1]['http_end_ns'];start=now[0]
                d.stop_ns=start+100_000_000_000;d.state['started_ns']=start
                def frame(sample):
                    return dict(obs(),_captured=sample['http_start_ns'],
                        _http_start_ns=sample['http_start_ns'],_http_end_ns=sample['http_end_ns'],
                        _extra={'scene':SimpleNamespace(goods='unknown'),'beat':{
                            'remaining':sample['remaining'],'spacing_px':104.,'center_px':446.}})
                frames=[frame(sample) for sample in samples]
                original_fit=d.fit_beat
                def delayed_fit():
                    result=original_fit();self.assertIsNotNone(result)
                    now[0]=start+12_000_000_000;return result
                if boundary=='compatible_fit':
                    d.samples=samples[:-1];d.model=beat_sync.fit(samples)
                    first=frames[-1]
                else:first=frames[0]
                if boundary=='checkpoint':d.checkpoint=lambda:now.__setitem__(0,start+12_000_000_000)
                else:d.fit_beat=delayed_fit
                with patch.object(d,'observe',side_effect=frames[1:]):
                    with self.assertRaises(ProbeError) as caught:d.synchronize(first)
                self.assertEqual('beat_sync_timeout',caught.exception.code);self.assertIsNone(d.model)

    def test_16_timeout_cleanup_refresh_failure_invalidates_last_and_never_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder);old=d.last
            def fail():
                self.assertIsNone(d.last);self.assertTrue(d.finishing)
                raise ProbeError('connection_error')
            with patch.object(d,'observe',side_effect=fail) as capture:
                with self.assertRaises(ProbeError):d.finish('beat_sync_timeout',old)
                d.finish('beat_sync_timeout',old)
            self.assertEqual(1,capture.call_count);self.assertIsNone(d.last)
            self.assertNotIn('run_steps',d.client.calls);self.assertFalse(d.state['paused'])

    def test_17_timeout_cleanup_basic_capture_and_safety_boundaries(self):
        import base64,io
        from necroprobe import gold_scan,shop_navigation,beat_sync
        from necroprobe.protocol import RpcReply
        from test_source_geometry import geometry_payload
        from test_gold_scan import floor
        from test_restart_loop import LiveStub,A,P
        buf=io.BytesIO();floor().save(buf,'JPEG')
        _,payload=geometry_payload(p.base.resume.CAPTURE_PARAMS,size=(896,414),source_scale=2)
        payload.update(data=base64.b64encode(buf.getvalue()).decode(),source_orientation=2)
        class Capture(LiveStub):
            def call(self,method,params,timeout):
                if method=='screenshot':self.calls.append(method);return RpcReply(payload,{})
                return super().call(method,params,timeout)
        for boundary in ('floor','pause','unknown','pending','state_pending','other_app','deadline','previous_pause'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);d.client=Capture();old=d.last
                if boundary=='pending':d.pending=True
                if boundary=='state_pending':d.state['input_pending']=True
                if boundary=='other_app':d.client.system={'foreground_app':'other','screen_locked':False}
                if boundary=='deadline':d.stop_ns=now[0]
                if boundary=='previous_pause':d.state['actions']=[{'action':'pause'}]
                fresh=deepcopy(P if boundary=='pause' else A)
                if boundary=='unknown':fresh['state']='unknown'
                with patch.object(gold_scan,'analyze_image',side_effect=[fresh,deepcopy(P)]), \
                     patch.object(shop_navigation,'scan',side_effect=AssertionError('heavy navigation')), \
                     patch.object(beat_sync,'extract',side_effect=AssertionError('heavy beat extraction')):
                    try:d.finish('beat_sync_timeout',old)
                    except ProbeError:pass
                    d.finish('beat_sync_timeout',d.last)
                self.assertEqual(1 if boundary=='floor' else 0,d.client.calls.count('run_steps'))
                self.assertEqual(boundary in ('floor','pause'),d.state['paused'])
                self.assertEqual(2 if boundary=='floor' else 1 if boundary in ('pause','unknown') else 0,
                                 d.client.calls.count('screenshot'))

    def test_18_real_fit_to_fixed_gesture_and_fresh_observation(self):
        import base64,io
        from types import SimpleNamespace
        from necroprobe import gold_scan,shop_navigation
        from necroprobe.protocol import RpcReply
        from test_source_geometry import geometry_payload
        from test_restart_loop import LiveStub,A
        from test_beat_sync import hud
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder);origin=now[0];sent=[]
            validator=p.WalkClient(lambda *a:None);validator.walking=True
            class Transport(LiveStub):
                def call(self,method,params,timeout):
                    if method=='screenshot':
                        self.calls.append(method);start=now[0];now[0]+=600_000_000
                        midpoint=(start+now[0])//2
                        with hud((.23-(midpoint-origin)/520_000_000)%1) as image:
                            buf=io.BytesIO();image.save(buf,'JPEG')
                        _,payload=geometry_payload(p.base.resume.CAPTURE_PARAMS,size=(896,414),source_scale=2)
                        payload.update(data=base64.b64encode(buf.getvalue()).decode(),source_orientation=2)
                        return RpcReply(payload,{'http_start_ns':start,'http_end_ns':now[0]})
                    if method=='run_steps':
                        validator._validate(method,params);sent.append(deepcopy(params))
                        self.calls.append(method);reply=deepcopy(GOOD);reply['steps'][1]['method']='gesture'
                        return RpcReply(reply,{})
                    return super().call(method,params,timeout)
            d.client=Transport()
            with patch.object(gold_scan,'analyze_image',side_effect=lambda image:deepcopy(A)), \
                 patch.object(shop_navigation,'scan',return_value=SimpleNamespace(goods='unknown')):
                first=d.observe();before,model=d.synchronize(first)
                self.assertIsNotNone(model);self.assertGreaterEqual(model['sample_count'],8)
                self.assertLess(now[0]-origin,12_000_000_000)
                self.assertAlmostEqual(520_000_000,model['period_ns'],delta=2_000_000)
                d.perform('left',before,model);self.assertIsNone(d.last)
                after=d.observe()
            self.assertEqual([p.move_batch('left')],sent)
            self.assertEqual('acknowledged',d.state['actions'][-1]['outcome'])
            self.assertGreater(d.state['actions'][-1]['target_ns'],d.state['actions'][-1]['issued_ns'])
            self.assertIs(after,d.last);self.assertIsNot(before,after)
            self.assertGreater(after['_http_start_ns'],before['_http_end_ns'])
            self.assertFalse(d.state['device_timing_verified'])

    def test_19_test018_report_engine_enum(self):
        from types import SimpleNamespace
        from necroprobe import navigation_stats,shop_navigation,beat_sync
        with tempfile.TemporaryDirectory() as folder:
            r=p.new_report(1,'7'*32)
            self.assertEqual('TEST-018',r['test_id']);self.assertEqual('shop-walk-v3',r['revision'])
            self.assertEqual(navigation_stats.ENGINE,r['walk']['navigation_engine'])
            for engine in ('native_i386','pillow'):
                r['walk']['navigation_engine']=engine;p.write(folder,r)
                p.read_report(Path(folder)/'report.json','7'*32,1)
            for engine in ('unknown',None,[],False):
                r['walk']['navigation_engine']=engine;p.write(folder,r)
                with self.assertRaises((ValueError,ProbeError)):
                    p.read_report(Path(folder)/'report.json','7'*32,1)
            for fail in (False,True):
                with self.subTest(scan_failure=fail),patch.object(navigation_stats,'ENGINE','native_i386'):
                    d,_=self.build(folder)
                    def fallback(image):
                        navigation_stats.ENGINE='pillow'
                        if fail:raise RuntimeError('scan failed after fallback')
                        return SimpleNamespace(goods='unknown')
                    with patch.object(shop_navigation,'scan',side_effect=fallback), \
                         patch.object(beat_sync,'extract',return_value=None):
                        d.analyze_frame(None,{'state':'floor'})
                    self.assertEqual('pillow',d.state['navigation_engine'])

    def test_20_foreground_delay_cannot_start_capture_at_sync_deadline(self):
        from test_restart_loop import LiveStub
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder)
            class SlowGuard(LiveStub):
                def call(self,method,params,timeout):
                    if method=='device_info':
                        now[0]+=12_000_000_000
                        return super().call(method,params,timeout)
                    self.calls.append(method);raise ProbeError('connection_error')
            d.client=SlowGuard()
            with self.assertRaises(ProbeError) as caught:d.synchronize(d.last)
            self.assertEqual('beat_sync_timeout',caught.exception.code)
            self.assertNotIn('screenshot',d.client.calls)
            self.assertGreater(d.budget(),0)

if __name__=='__main__':unittest.main()
