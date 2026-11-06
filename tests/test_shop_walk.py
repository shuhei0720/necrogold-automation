import tempfile
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import unittest
from unittest.mock import patch
from necroprobe import shop_walk as p
from necroprobe.validation import ProbeError
from test_resume_once import GOOD

def obs(goods='unknown'):
    return {'state':'floor','_extra':{'scene':goods},'_sha':'a'*64,'_seen_ns':1,'_raw':b'x'}


def test019_samples():
    """TEST019 parent-result.json / shop-walk-20261106T025025Z-efa5d9cc の実測11標本。"""
    from necroprobe import beat_sync
    rows = [
        (125945800458000, 125945959202000, 0.8168588335276556, 104.19999999999999, 445.3),
        (125948201905000, 125948343852000, 0.23269396502147233, 104.25, 445.25),
        (125949073627000, 125949228441000, 0.5452368766135953, 105.0, 445.25),
        (125950068532000, 125950230713000, 0.6378205669853869, 104.0, 445.25),
        (125950841082000, 125950994140000, 0.16546744438772792, 104.25, 445.25),
        (125951718836000, 125951875846000, 0.4863295735044895, 104.5, 445.25),
        (125952693580000, 125952838095000, 0.6522436439084638, 104.0, 445.25),
        (125953478953000, 125953642323000, 0.08931424796841578, 104.5, 445.25),
        (125954330822000, 125954478991000, 0.453261881866172, 104.75, 445.16666666666663),
        (125957241759000, 125957392901000, 0.903278050431733, 104.25, 445.5),
        (125963760450000, 125963905148000, 0.4289133055619059, 104.5, 445.25),
    ]
    return [beat_sync.make_sample({'remaining':q,'spacing_px':spacing,'center_px':center},start,end)
            for start,end,q,spacing,center in rows]


def test020_samples():
    """TEST020 0歩run/左2歩runの最終取得window（生画像を含まない実測値）。"""
    from necroprobe import beat_sync
    rows = [
        [
            (127960807041000, 127960962068000, 0.6618703220855697, 104.25, 445.25),
            (127963603003000, 127963796462000, 0.28442226441658486, 103.5, 445.25),
            (127964620766000, 127964794358000, 0.2978087396549835, 104.58333333333331, 445.25),
            (127965738685000, 127965899635000, 0.17764460800896673, 104.375, 445.25),
            (127966605026000, 127966782264000, 0.5560386727719953, 103.5, 445.25),
            (127967584176000, 127967753322000, 0.6187048544596705, 104.25, 445.25),
            (127968677607000, 127968846163000, 0.5801282592930792, 104.0, 445.25),
            (127969515010000, 127969702358000, 0.9456435692608577, 104.25, 445.25),
            (127970499006000, 127970673609000, 0.060911270997635616, 104.25, 445.25),
        ],
        [
            (128230524883000, 128230712516000, 0.6570745220391305, 104.25, 445.25),
            (128231539286000, 128231704746000, 0.7338127681287352, 104.25, 445.25),
            (128232662502000, 128232812537000, 0.5657051823700023, 104.0, 445.25),
            (128233541635000, 128233728536000, 0.8936848771868298, 104.25, 445.0),
            (128234545043000, 128234716601000, 0.9601276450976024, 104.5, 445.25),
            (128235663604000, 128235808552000, 0.8450839328681392, 104.25, 445.25),
            (128236549538000, 128236732586000, 0.1201595780688471, 104.375, 445.25),
            (128237560865000, 128237736336000, 0.20383711196718818, 104.25, 445.25),
            (128238771035000, 128238936377000, 0.8737011232176922, 104.25, 445.25),
            (128239690382000, 128239856005000, 0.11790586370197646, 104.25, 445.25),
        ],
    ]
    return [[beat_sync.make_sample({'remaining':q,'spacing_px':spacing,'center_px':center},start,end)
             for start,end,q,spacing,center in run] for run in rows]

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


class ExpiringFake(Fake):
    def __init__(self,frames,outcomes):
        super().__init__(frames,['moved']*p.MAX_STEPS)
        self.outcomes=iter(outcomes);self.synced=[];self.chosen=[];self.captures=0
    def budget(self):
        if p.base.supervisor._cancel_requested:raise ProbeError('cancelled')
        return 8
    def observe(self):
        self.captures+=1;return super().observe()
    def synchronize(self,frame):
        self.synced.append(frame);return super().synchronize(frame)
    def choose(self,frame):
        self.chosen.append(frame)
        return {'direction':frame.get('direction','left'),'target':[-1,0],'reason':'approach'}
    def perform(self,action,frame,model=None):
        entry={'action':action,'outcome':'not_requested','reason':None,'requested_ns':self.clock(),
               'issued_ns':None,'completed_ns':None,'target_ns':None,'rpc_timings':{}}
        self.state['actions'].append(entry)
        if action in p.MOVE_POINTS:
            result=next(self.outcomes)
            if result=='expired':
                entry['reason']='dispatch_window_expired';raise ProbeError('dispatch_window_expired')
            if result in ('unknown','issued','cancelled'):
                if result=='unknown':self.pending=True;self.state['input_pending']=True;entry['outcome']='unknown'
                if result=='issued':entry['issued_ns']=self.clock()
                raise ProbeError('cancelled' if result=='cancelled' else 'dispatch_window_expired')
        entry.update(outcome='acknowledged',issued_ns=self.clock(),completed_ns=self.clock())
        self.sent.append(action)
    def finish(self,reason,frame):
        self.state['reason']=reason
        if not self.pending:self.perform('pause',frame);self.state['paused']=True

class WalkTests(unittest.TestCase):
    def test_46_expired_unsent_action_refreshes_full_sync_and_direction_then_goods_wins(self):
        for visible in (False,True):
            with self.subTest(visible=visible):
                initial=obs();fresh=dict(obs('visible' if visible else 'unknown'),direction='right')
                d=ExpiringFake([initial,fresh,obs('visible')],['expired','ok'])
                p.walk(d)
                self.assertEqual(['resume','pause'] if visible else ['resume','right','pause'],d.sent)
                self.assertEqual([initial] if visible else [initial,fresh],d.synced)
                self.assertEqual([initial] if visible else [initial,fresh],d.chosen)
                self.assertTrue(d.state['goods_visible']);self.assertEqual('goods_visible',d.state['reason'])

    def test_47_only_two_expiry_refreshes_across_entire_walk(self):
        frames=[obs() for _ in range(6)]
        d=ExpiringFake(frames,['expired','ok','expired','ok','expired'])
        with self.assertRaises(ProbeError) as caught:p.walk(d)
        self.assertEqual('dispatch_window_expired',caught.exception.code)
        self.assertEqual(5,d.captures);self.assertEqual(2,d.state['moves_confirmed'])
        self.assertEqual(['resume','left','left'],d.sent)
        self.assertEqual(1,d.state['started_ns'])

    def test_48_expiry_reason_does_not_allow_refresh_after_pending_issued_or_cancel(self):
        for outcome in ('unknown','issued','cancelled'):
            with self.subTest(outcome=outcome):
                d=ExpiringFake([obs(),obs('visible')],[outcome])
                with self.assertRaises(ProbeError):p.walk(d)
                self.assertEqual(1,d.captures);self.assertEqual(['resume'],d.sent)

    def test_49_refresh_does_not_reset_step_time_or_report_action_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            d=ExpiringFake([obs() for _ in range(19)],['expired','expired']+['ok']*16)
            p.walk(d)
            self.assertEqual(16,d.state['moves_confirmed']);self.assertEqual([-16,0],d.state['position'])
            self.assertEqual(16,sum(action in p.MOVE_POINTS for action in d.sent))
            self.assertEqual(20,len(d.state['actions']));self.assertEqual(1,d.state['started_ns'])
            r=p.new_report(1,'5'*32);r['walk']=d.state
            p.write(folder,r);p.read_report(Path(folder)/'report.json','5'*32,1)
            r['walk']['actions'].append(deepcopy(r['walk']['actions'][-1]));p.write(folder,r)
            with self.assertRaises((ValueError,ProbeError)):p.read_report(Path(folder)/'report.json','5'*32,1)
            d=ExpiringFake([obs(),obs()],['expired']);now=[1];d.clock=lambda:now[0]
            observe=d.observe
            def expire_during_refresh():
                frame=observe()
                if d.captures==2:now[0]=1+p.WALK_SECONDS*1_000_000_000
                return frame
            d.observe=expire_during_refresh;p.walk(d)
            self.assertEqual(1,d.state['started_ns']);self.assertEqual('walk_limit',d.state['reason'])
            self.assertEqual(['resume','pause'],d.sent)

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
        for boundary in ('other_app','pending','deadline','checkpoint_deadline'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as folder:
                now=5_000_000_000;r=p.new_report(1,'b'*32);r['phase']='walk'
                d=p.Driver(LiveStub(),r,folder,now+20_000_000_000,folder,clock=lambda:now)
                d.last=dict(obs(),_captured=now)
                if boundary=='other_app':d.client.system={'foreground_app':'other','screen_locked':False}
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
                self.assertTrue(r['walk']['paused'])
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
                with self.assertRaises(ProbeError):d.perform('left',d.last,{'period_ns':520_000_000,'last_sample_ns':now[0]})
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

    def test_15_fit_and_track_cannot_return_model_at_deadline(self):
        from test_beat_sync import observations
        from necroprobe import beat_sync
        from types import SimpleNamespace
        samples=observations(9)
        for boundary in ('fit','compatible_track'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder);now[0]=samples[-1 if boundary=='compatible_track' else 0]['http_end_ns'];start=now[0]
                d.stop_ns=start+100_000_000_000;d.state['started_ns']=start
                def frame(sample):
                    return dict(obs(),_captured=sample['http_start_ns'],
                        _http_start_ns=sample['http_start_ns'],_http_end_ns=sample['http_end_ns'],
                        _extra={'scene':SimpleNamespace(goods='unknown'),'beat':{
                            'remaining':sample['remaining'],'spacing_px':104.,'center_px':446.}})
                frames=[frame(sample) for sample in samples]
                original_fit=d.fit_beat;original_track=d.track_beat
                def delayed_track(model):
                    result=original_track(model);self.assertIsNotNone(result)
                    now[0]=start+12_000_000_000;return result
                def delayed_fit():
                    result=original_fit();self.assertIsNotNone(result)
                    now[0]=start+12_000_000_000;return result
                if boundary=='compatible_track':
                    d.samples=samples[:-1];d.model=beat_sync.fit(samples[:-1])
                    first=frames[-1]
                else:first=frames[0]
                d.last=first
                if boundary=='compatible_track':d.track_beat=delayed_track
                else:d.fit_beat=delayed_fit
                def observe():
                    d.last=next(pending_frames);now[0]=d.last['_http_end_ns'];return d.last
                pending_frames=iter(frames[1:])
                with patch.object(d,'observe',side_effect=observe):
                    with self.assertRaises(ProbeError) as caught:d.synchronize(first)
                self.assertEqual('beat_sync_timeout',caught.exception.code);self.assertIsNone(d.model)

    def test_16_timeout_cleanup_refresh_failure_invalidates_last_and_never_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder);old=d.last;old['_captured']=now[0]-3_000_000_001
            def fail():
                self.assertIsNone(d.last);self.assertTrue(d.finishing)
                raise ProbeError('connection_error')
            with patch.object(d,'observe',side_effect=fail) as capture:
                with self.assertRaises(ProbeError):d.finish('beat_sync_timeout',old)
                d.finish('host_observation_expired',old)
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
        for boundary in ('floor','pause','unknown','pending','state_pending','other_app','deadline','previous_pause','cancel'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 patch.object(p.base.supervisor,'_cancel_requested',boundary=='cancel'):
                d,now=self.build(folder);d.client=Capture();old=d.last;old['_captured']=now[0]-3_000_000_001
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
                    d.finish('host_observation_expired',d.last)
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

    def test_19_test022_report_engine_enum(self):
        from types import SimpleNamespace
        from necroprobe import navigation_stats,motion_stats,shop_navigation,beat_sync
        with tempfile.TemporaryDirectory() as folder:
            r=p.new_report(1,'7'*32)
            self.assertEqual('TEST-022',r['test_id']);self.assertEqual('shop-walk-v7',r['revision'])
            self.assertEqual('runtime/test-022',p.parser().parse_args([]).output)
            self.assertEqual(navigation_stats.ENGINE,r['walk']['navigation_engine'])
            self.assertEqual(motion_stats.ENGINE,r['walk']['motion_engine'])
            for key in ('navigation_engine','motion_engine'):
                for engine in ('native_i386','pillow'):
                    r['walk'][key]=engine;p.write(folder,r)
                    p.read_report(Path(folder)/'report.json','7'*32,1)
                for engine in ('unknown',None,[],False):
                    r['walk'][key]=engine;p.write(folder,r)
                    with self.assertRaises((ValueError,ProbeError)):
                        p.read_report(Path(folder)/'report.json','7'*32,1)
                r['walk'][key]='pillow'
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
                with self.subTest(motion_failure=fail),patch.object(motion_stats,'ENGINE','native_i386'):
                    d,_=self.build(folder)
                    def motion_fallback(*args):
                        motion_stats.ENGINE='pillow'
                        if fail:raise RuntimeError('motion failed after fallback')
                        return 'moved'
                    with patch.object(shop_navigation,'motion',side_effect=motion_fallback):
                        if fail:
                            with self.assertRaises(RuntimeError):d.movement(d.last,d.last,'left')
                        else:self.assertEqual('moved',d.movement(d.last,d.last,'left'))
                    self.assertEqual('pillow',d.state['motion_engine'])
                    self.assertEqual(1,len(d.state['motion_ms']))

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

    @contextmanager
    def measured_runtime(self,folder,test021=False):
        """TEST-018実測相当の各工程費用。HUD抽出/標本化/fit/拍計算は実物。"""
        import base64,io
        from necroprobe import gold_scan,shop_navigation,beat_sync
        from necroprobe.protocol import RpcReply
        from test_source_geometry import geometry_payload
        from test_restart_loop import LiveStub,A
        from test_beat_sync import hud
        d,now=self.build(folder);origin=now[0];captures=[];scenes=[];sent=[]
        scene=shop_navigation.Scene({(0,0):'floor',(-1,0):'floor',(-2,0):'gold'},
                                    {(-2,0)},'unknown',set(),b'')
        validator=p.WalkClient(lambda *a:None);validator.walking=True
        class Transport(LiveStub):
            def call(self,method,params,timeout):
                if method=='device_info':now[0]+=130_000_000 if test021 else 120_000_000
                if method=='screenshot':
                    self.calls.append(method);start=now[0];now[0]+=622_794_000 if test021 else 450_000_000
                    captures.append((start,getattr(d,'beat_only',False)))
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
        def basic(image):now[0]+=125_000_000;return deepcopy(A)
        def navigation(image):
            now[0]+=1_538_909_000 if test021 else 1_012_000_000
            fresh=deepcopy(scene);scenes.append(fresh);return fresh
        extract=beat_sync.extract
        def beat(image):now[0]+=62_000_000;return extract(image)
        d.client=Transport()
        if test021:
            checkpoint=d.checkpoint
            def save_checkpoint():
                checkpoint();now[0]+=155_000_000
                d.report['checkpoint_ms'][-1]=155
            d.checkpoint=save_checkpoint
        with patch.object(gold_scan,'analyze_image',side_effect=basic), \
             patch.object(shop_navigation,'scan',side_effect=navigation), \
             patch.object(beat_sync,'extract',side_effect=beat):
            yield d,now,captures,scenes,sent

    def test_21_test018_cost_sync_hands_off_latest_full_scene_and_moves(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            first=d.observe();start=now[0]
            before,model=d.synchronize(first)
            self.assertIsNotNone(model);self.assertGreaterEqual(model['sample_count'],9)
            self.assertAlmostEqual(520_000_000,model['period_ns'],delta=2_000_000)
            self.assertLess(now[0]-start,12_000_000_000)
            self.assertEqual(2,len(scenes));self.assertEqual(7,sum(light for _,light in captures))
            self.assertIs(before,d.last);self.assertIsNot(before,first)
            self.assertIs(before['_extra']['scene'],scenes[-1])
            self.assertIsNot(before['_extra']['scene'],first['_extra']['scene'])
            self.assertEqual(before['_http_end_ns']-225_000_000,model['last_sample_ns'])
            self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)
            direction=d.choose(before)['direction'];self.assertEqual('left',direction)
            d.perform(direction,before,model)
            self.assertEqual([p.move_batch('left')],sent)
            self.assertFalse(d.state['device_timing_verified'])

    def test_22_light_observation_cannot_supply_goods_route_or_movement(self):
        from necroprobe import shop_navigation
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            full=d.observe();d.beat_only=True;light=d.observe();d.beat_only=False
            self.assertIsNone(light['_extra']['scene']);self.assertIsNotNone(light['_extra']['beat'])
            self.assertEqual('unknown',d.goods(light));self.assertIsNone(d.choose(light)['direction'])
            with patch.object(shop_navigation,'motion',side_effect=AssertionError('light scene used')):
                self.assertEqual('unknown',d.movement(light,full,'left'))
                self.assertEqual('unknown',d.movement(full,light,'left'))
            with self.assertRaises(ProbeError) as caught:d.perform('left',light,{'period_ns':520_000_000})
            self.assertEqual('navigation_unknown',caught.exception.code)
            self.assertEqual([],sent);self.assertEqual([],d.state['actions'])

    def test_23_cached_full_reuses_capture_but_light_requires_fresh_full(self):
        for light in (False,True):
            with self.subTest(light=light),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                _,model=d.synchronize(d.observe())
                d.beat_only=light;current=d.observe();d.beat_only=False
                count=len(captures);nav_count=len(scenes)
                result,updated=d.synchronize(current)
                self.assertIs(result,d.last);self.assertIs(result['_extra']['scene'],scenes[-1])
                self.assertEqual(count+int(light),len(captures))
                self.assertEqual(nav_count+int(light),len(scenes))
                self.assertEqual(not light,result is current)
                self.assertGreater(updated['last_sample_ns'],model['last_sample_ns'])
                self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_24_full_handoff_failure_never_returns_model_or_leaves_modes(self):
        boundaries={'phase':'beat_unconfirmed','scene':'navigation_unknown','unknown':'navigation_unknown',
                    'stale':'navigation_unknown','light_capture':'connection_error',
                    'sync':'beat_sync_timeout','session':'session_deadline','walk':'walk_limit',
                    'capture':'connection_error','foreground':'foreground_not_verified',
                    'tracking':'beat_unconfirmed'}
        for boundary,expected in boundaries.items():
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                first=d.observe();observe=d.observe;track=d.track_beat
                def handoff():
                    if d.beat_only and boundary=='light_capture':raise ProbeError('connection_error')
                    if not d.beat_only and boundary=='capture':raise ProbeError('connection_error')
                    if not d.beat_only and boundary=='foreground':
                        d.client.system={'foreground_app':'other','screen_locked':False}
                    fresh=observe()
                    if not d.beat_only:
                        if boundary=='phase':fresh['_extra']['beat']['remaining']=(fresh['_extra']['beat']['remaining']+.3)%1
                        elif boundary=='scene':fresh['_extra']['scene']=None
                        elif boundary=='unknown':fresh['state']='unknown'
                        elif boundary=='stale':now[0]+=3_000_000_001
                        elif boundary=='sync':now[0]=d.sync_deadline
                        elif boundary=='session':d.stop_ns=now[0]
                        elif boundary=='walk':d.state['started_ns']=now[0]-p.WALK_SECONDS*1_000_000_000
                    return fresh
                def tracking(model):return None if boundary=='tracking' else track(model)
                with patch.object(d,'observe',side_effect=handoff),patch.object(d,'track_beat',side_effect=tracking):
                    with self.assertRaises(ProbeError) as caught:
                        d.synchronize(first)
                self.assertEqual(expected,caught.exception.code)
                self.assertEqual([],sent);self.assertIsNone(d.model)
                self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_25_latest_full_goods_latches_even_when_beat_extraction_fails(self):
        from necroprobe import shop_navigation,beat_sync
        for fail in (False,True):
            with self.subTest(beat_failure=fail),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                first=d.observe();navigation=shop_navigation.scan.side_effect;extract=beat_sync.extract.side_effect
                def visible(image):
                    scene=navigation(image);scene.goods='visible';return scene
                def beat(image):
                    if not d.beat_only and fail:raise ValueError('beat failed')
                    return extract(image)
                with patch.object(shop_navigation,'scan',side_effect=visible),patch.object(beat_sync,'extract',side_effect=beat):
                    if fail:
                        with self.assertRaises(ProbeError) as caught:d.synchronize(first)
                        self.assertEqual('walk_analysis_failed',caught.exception.code)
                    else:
                        result,model=d.synchronize(first)
                        self.assertIs(result,d.last);self.assertIsNone(model)
                self.assertTrue(d.state['goods_visible']);self.assertEqual('visible',d.goods(d.last))
                self.assertEqual([],sent);self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_26_cached_model_tracks_without_repeating_full_band_acquisition(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            d.synchronize(d.observe());current=d.observe();count=len(captures)
            with patch.object(d,'fit_beat',side_effect=AssertionError('cached model reacquired')):
                result,updated=d.synchronize(current)
            self.assertIs(result,current);self.assertEqual(count,len(captures))
            self.assertEqual('tracking',updated['mode']);self.assertIs(updated,d.model)
            self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_27_input_rechecks_model_age_after_guard_and_checkpoint(self):
        from necroprobe import beat_sync
        for boundary in ('guard','checkpoint'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());model=deepcopy(model)
                # 準備後も画面/予定拍は有効だが、モデルの3秒上限だけを越える。
                target=beat_sync.next_target(model,now[0],p.LEAD_NS+120_000_000)
                prepared=target-p.LEAD_NS
                model['last_sample_ns']=prepared-beat_sync.FRESH_NS+1
                if boundary=='guard':
                    guard=d.guard
                    def late_guard():
                        value=guard();model['last_sample_ns']=prepared-beat_sync.FRESH_NS-1;return value
                    d.guard=late_guard
                else:
                    checkpoint=d.checkpoint
                    def late_checkpoint():checkpoint();model['last_sample_ns']=prepared-beat_sync.FRESH_NS-1
                    d.checkpoint=late_checkpoint
                self.assertIsNotNone(beat_sync.next_target(model,now[0]))
                with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                self.assertEqual('dispatch_window_expired',caught.exception.code)
                self.assertLess(now[0],target);self.assertLess(now[0]-before['_captured'],3_000_000_000)
                self.assertEqual([],sent);self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])

    def test_28_test019_stale_after_motion_reacquires_if_new_full_disagrees(self):
        from necroprobe import beat_sync
        samples=test019_samples();model=beat_sync.fit(samples[:9])
        self.assertIsNotNone(model);self.assertEqual(521_599_608,model['period_ns'])
        self.assertTrue(beat_sync.compatible(model,samples[9]))
        updated=beat_sync.fit(samples[:10]);self.assertIsNotNone(updated)
        self.assertEqual(6_515_469_000,samples[10]['midpoint_ns']-samples[9]['midpoint_ns'])
        self.assertFalse(beat_sync.compatible(updated,samples[10]))
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            old=d.observe();sample=samples[9]
            old.update(_captured=sample['http_start_ns'],_http_start_ns=sample['http_start_ns'],
                       _http_end_ns=sample['http_end_ns'])
            old['_extra']['beat']={k:sample[k] for k in ('remaining','spacing_px','center_px')}
            d.samples=deepcopy(samples[:9]);d.state['samples']=d.samples;d.model=model
            # 実測の次のHTTP開始直前。移動判定4471.72ms後は3秒を越えている。
            now[0]=samples[10]['http_start_ns']-120_000_000
            self.assertGreater(now[0]-old['_captured'],beat_sync.FRESH_NS)
            d.state['started_ns']=125944424328000;d.stop_ns=now[0]+100_000_000_000
            count=len(captures);start=now[0]
            before,fresh_model=d.synchronize(old)
            self.assertIsNot(before,old);self.assertIs(before,d.last)
            self.assertFalse(captures[count][1]);self.assertFalse(captures[-1][1])
            self.assertTrue(all(light for _,light in captures[count+1:-1]))
            self.assertEqual(7,len(captures[count+1:-1]))
            self.assertTrue(all(item['http_start_ns']>sample['http_end_ns'] for item in d.samples))
            self.assertLess(now[0]-start,12_000_000_000)
            self.assertEqual(['acquired','tracking'],[item['mode'] for item in d.state['models']])
            self.assertEqual(fresh_model,d.state['models'][-1])
            d.perform('left',before,fresh_model)
            self.assertEqual([p.move_batch('left')],sent)
            self.assertEqual(before['_raw'],d.images['run-099.jpg'])
            self.assertNotEqual(old['_raw'],d.images['run-099.jpg'])

    def test_29_sync_observation_age_boundary_keeps_model_and_refreshes_full(self):
        from necroprobe import beat_sync
        for age in (beat_sync.FRESH_NS-1,beat_sync.FRESH_NS,beat_sync.FRESH_NS+1,-1):
            with self.subTest(age=age),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                d.synchronize(d.observe());current=d.observe();count=len(captures)
                current['_captured']=now[0]-age;old_samples=deepcopy(d.samples)
                original=d.observe;first=[True]
                def fresh():
                    if first[0]:
                        self.assertIsNotNone(d.model);self.assertEqual(old_samples,d.samples)
                        self.assertEqual(old_samples,d.state['samples']);self.assertFalse(d.beat_only)
                        first[0]=False
                    return original()
                with patch.object(d,'observe',side_effect=fresh):
                    result,model=d.synchronize(current)
                stale=not 0<=age<=beat_sync.FRESH_NS
                self.assertEqual(not stale,result is current)
                self.assertEqual(count+int(stale),len(captures))
                self.assertEqual(3,len(d.state['models']))
                self.assertEqual(model,d.state['models'][-1])
                self.assertTrue(any(sample in old_samples for sample in d.samples))
                self.assertEqual([],sent);self.assertFalse(d.pending)
                self.assertFalse(d.state['input_pending'])

    def test_30_before_frame_save_cost_cannot_bypass_final_limits(self):
        from necroprobe import beat_sync
        for boundary in ('frame','model','session','walk','pending','goods'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());save=d.save;saved=[]
                def slow_save(name,frame):
                    saved.append((name,frame));save(name,frame)
                    if boundary=='frame':before['_captured']=now[0]-beat_sync.FRESH_NS-1
                    if boundary=='model':now[0]+=beat_sync.FRESH_NS+1
                    if boundary=='session':d.stop_ns=now[0]
                    if boundary=='walk':d.state['started_ns']=now[0]-p.WALK_SECONDS*1_000_000_000
                if boundary=='pending':d.pending=True;d.state['input_pending']=True
                if boundary=='goods':d.state['goods_visible']=True
                with patch.object(d,'save',side_effect=slow_save):
                    with self.assertRaises(ProbeError):d.perform('left',before,model)
                self.assertEqual([],sent)
                self.assertEqual([] if boundary in ('pending','goods') else [('run-099.jpg',before)],saved)
                self.assertEqual(boundary=='pending',d.pending)
                self.assertEqual(boundary=='pending',d.state['input_pending'])

    def test_31_pending_checkpoint_persists_bounded_model_history_then_rechecks_limits(self):
        from necroprobe import beat_sync
        for boundary in ('valid','frame','model','walk','session'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                d.synchronize(d.observe());current=d.observe()
                previous=d.model;d.state['models']=[deepcopy(previous) for _ in range(p.MAX_STEPS+1)]
                with patch.object(d,'checkpoint') as accept_checkpoint:
                    result,model=d.synchronize(current)
                accept_checkpoint.assert_not_called()
                self.assertIs(current,result);self.assertEqual(model,d.state['models'][-1])
                checkpoint=d.checkpoint
                saved=[]
                def check():
                    checkpoint()
                    if not d.pending:return
                    saved.append(p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns']))
                    if boundary=='frame':current['_captured']=now[0]-beat_sync.FRESH_NS-1
                    if boundary=='model':d.state['models'][-1]['last_sample_ns']=now[0]-beat_sync.FRESH_NS-1
                    if boundary=='walk':d.state['started_ns']=now[0]-p.WALK_SECONDS*1_000_000_000
                    if boundary=='session':d.stop_ns=now[0]
                with patch.object(d,'checkpoint',side_effect=check):
                    if boundary=='valid':d.perform('left',current,model)
                    else:
                        with self.assertRaises(ProbeError) as caught:d.perform('left',current,model)
                        self.assertEqual({'frame':'dispatch_window_expired','model':'dispatch_window_expired',
                                          'walk':'walk_limit','session':'session_deadline'}[boundary],caught.exception.code)
                self.assertEqual(1,len(saved));self.assertTrue(saved[0]['walk']['input_pending'])
                self.assertEqual('unknown',saved[0]['walk']['actions'][-1]['outcome'])
                self.assertIsNone(saved[0]['walk']['actions'][-1]['target_ns'])
                self.assertEqual(previous['mode'],saved[0]['walk']['models'][-1]['mode'])
                self.assertEqual(p.MAX_STEPS+1,len(d.state['models']))
                self.assertEqual(1 if boundary=='valid' else 0,len(sent))

    def test_32_input_model_age_three_second_boundary(self):
        from necroprobe import beat_sync
        for age in (beat_sync.FRESH_NS-1,beat_sync.FRESH_NS,beat_sync.FRESH_NS+1):
            with self.subTest(age=age),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());model=deepcopy(model)
                target=beat_sync.next_target(model,now[0],p.LEAD_NS+120_000_000)
                prepared=target-p.LEAD_NS;model['last_sample_ns']=prepared-age
                if age<=beat_sync.FRESH_NS:
                    d.perform('left',before,model)
                    self.assertEqual([p.move_batch('left')],sent)
                else:
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                    self.assertEqual('dispatch_window_expired',caught.exception.code);self.assertEqual([],sent)
                self.assertEqual(age,target-p.LEAD_NS-model['last_sample_ns'])
                self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])

    def test_33_before_frame_export_roundtrip_keeps_report_valid(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            before,model=d.synchronize(d.observe())
            d.perform('left',before,model)
            d.export_images();p.write(folder,d.outer)
            report=p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
            self.assertTrue(report['search']['export_complete'])
            self.assertEqual(['run-099.jpg'],report['search']['exported_images'])
            self.assertEqual(before['_raw'],(Path(folder)/'run-099.jpg').read_bytes())
            self.assertEqual([p.move_batch('left')],sent)


    def test_34_test020_initial_lock_survives_consistent_full_handoff(self):
        from types import SimpleNamespace
        from necroprobe import beat_sync
        for samples in test020_samples():
            with self.subTest(start=samples[0]['http_start_ns']),tempfile.TemporaryDirectory() as folder:
                d,now=self.build(folder)
                initial=beat_sync.fit(samples[:-1])
                self.assertIsNotNone(initial)
                self.assertTrue(beat_sync.compatible(initial,samples[-1]))
                # 旧full帯域再取得はaliasgap .04をわずかに割り、整合したfresh画像を捨てる。
                self.assertIsNone(beat_sync.fit(samples))
                def frame(sample):
                    return dict(obs(),_captured=sample['http_start_ns'],
                        _http_start_ns=sample['http_start_ns'],_http_end_ns=sample['http_end_ns'],
                        _extra={'scene':SimpleNamespace(goods='unknown'),'beat':{
                            key:sample[key] for key in ('remaining','spacing_px','center_px')}})
                frames=[frame(sample) for sample in samples];d.last=frames[0]
                now[0]=frames[0]['_http_end_ns']+1_200_000_000
                d.state['started_ns']=now[0];d.stop_ns=now[0]+100_000_000_000
                captures=[];pending=iter(frames[1:])
                def observe():
                    d.last=next(pending);captures.append(d.beat_only)
                    now[0]=d.last['_http_end_ns']+(250_000_000 if d.beat_only else 1_200_000_000)
                    return d.last
                with patch.object(d,'observe',side_effect=observe):
                    before,model=d.synchronize(frames[0])
                self.assertIs(before,frames[-1]);self.assertIs(model,d.model)
                self.assertEqual('tracking',model['mode'])
                self.assertEqual([True]*(len(samples)-2)+[False],captures)
                self.assertEqual(samples,d.samples);self.assertEqual([],d.state['actions'])

    def test_35_preparation_finishes_before_waiting_to_actual_lead(self):
        from necroprobe import beat_sync
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            before,model=d.synchronize(d.observe())
            # 次の前面120ms/保存60msは直前の20ms/10msより遅い。
            d.report['foreground_ms'][-1]=20;d.report['checkpoint_ms']=[10]
            target=now[0]+600_000_000;events=[];checkpoint=d.checkpoint;sleeper=d.sleeper
            def save_checkpoint():
                events.append(('checkpoint',now[0]));checkpoint();now[0]+=60_000_000
            def wait(seconds):events.append(('wait',now[0]));sleeper(seconds)
            with patch.object(d,'checkpoint',side_effect=save_checkpoint),patch.object(d,'sleeper',side_effect=wait), \
                 patch.object(beat_sync,'next_target',return_value=target):
                d.perform('left',before,model)
            entry=d.state['actions'][-1]
            self.assertEqual(p.LEAD_NS,entry['target_ns']-entry['issued_ns'])
            self.assertEqual('checkpoint',events[0][0]);self.assertEqual([p.move_batch('left')],sent)

    def test_36_late_checkpoint_stops_without_dispatch(self):
        from necroprobe import beat_sync
        for lateness in (1,p.LEAD_NS+1):
            with self.subTest(lateness=lateness),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());target=now[0]+600_000_000
                checkpoint=d.checkpoint
                def late_checkpoint():checkpoint();now[0]=target-p.LEAD_NS+lateness
                with patch.object(d,'checkpoint',side_effect=late_checkpoint), \
                     patch.object(beat_sync,'next_target',return_value=target):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                self.assertEqual('beat_unconfirmed',caught.exception.code)
                self.assertEqual([],sent);self.assertIsNone(d.state['actions'][-1]['issued_ns'])
                self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])

    def test_37_dispatch_rpc_timings_allowlist_roundtrip(self):
        from necroprobe.protocol import RpcReply
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            before,model=d.synchronize(d.observe());call=d.client.call;expected={}
            def timed_call(method,params,timeout):
                reply=call(method,params,timeout)
                if method!='run_steps':return reply
                expected.update({key:now[0]+index for index,key in enumerate((
                    'request_start_ns','http_start_ns','http_end_ns','response_end_ns'))})
                now[0]+=3
                return RpcReply(reply.result,dict(expected,crypto_engine='PRIVATE',request='PRIVATE'))
            with patch.object(d.client,'call',side_effect=timed_call):d.perform('left',before,model)
            entry=d.state['actions'][-1]
            self.assertEqual(expected,entry['rpc_timings']);self.assertNotIn('PRIVATE',str(d.outer))
            p.write(folder,d.outer)
            report=p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
            self.assertEqual(expected,report['walk']['actions'][-1]['rpc_timings'])
            for timings in ({'secret':1},{'http_start_ns':'PRIVATE'},{'http_start_ns':True},
                            {'http_start_ns':-1},{'http_start_ns':2**63},{'http_start_ns':1.5}):
                with self.subTest(timings=timings):
                    entry['rpc_timings']=timings;p.write(folder,d.outer)
                    with self.assertRaises((ValueError,ProbeError)):
                        p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])


    def test_38_stale_after_uses_one_new_full_and_tracks_for_next_step(self):
        from necroprobe import beat_sync
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            before,model=d.synchronize(d.observe());d.perform('left',before,model)
            after=d.observe();now[0]+=1_500_000_000
            self.assertGreater(now[0]-after['_captured'],beat_sync.FRESH_NS)
            old_samples=deepcopy(d.samples);count=len(captures);start=now[0]
            with patch.object(d,'fit_beat',side_effect=AssertionError('tracking should not reacquire')):
                before,updated=d.synchronize(after)
            self.assertEqual(count+1,len(captures));self.assertFalse(captures[-1][1])
            self.assertIs(before,d.last);self.assertIsNot(before,after)
            self.assertEqual(old_samples,d.samples[:-1]);self.assertEqual('tracking',updated['mode'])
            self.assertLess(now[0]-start,3_000_000_000)
            d.perform('left',before,updated)
            self.assertEqual([p.move_batch('left')]*2,sent)
            self.assertEqual(before['_raw'],d.images['run-099.jpg'])
            self.assertEqual(['acquired','tracking','tracking'],[m['mode'] for m in d.state['models']])

    def test_39_final_wait_rechecks_every_stop_boundary_before_rpc(self):
        from necroprobe import beat_sync
        expected={'cancel':'cancelled','session':'session_deadline','walk':'walk_limit',
                  'frame':'host_observation_expired','model':'beat_unconfirmed',
                  'foreground':'host_observation_expired','oversleep':'beat_unconfirmed'}
        for boundary,reason in expected.items():
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent), \
                 patch.object(p.base.supervisor,'_cancel_requested',False):
                before,model=d.synchronize(d.observe());model=deepcopy(model)
                target=beat_sync.next_target(model,now[0],p.LEAD_NS+120_000_000)
                until=target-p.LEAD_NS;sleeper=d.sleeper;waits=[]
                def wait(seconds):
                    sleeper(seconds);waits.append(now[0])
                    if now[0]<until:return
                    if boundary=='cancel':p.base.supervisor._cancel_requested=True
                    elif boundary=='session':d.stop_ns=now[0]
                    elif boundary=='walk':d.state['started_ns']=now[0]-p.WALK_SECONDS*1_000_000_000
                    elif boundary=='frame':before['_captured']=now[0]-beat_sync.FRESH_NS-1
                    elif boundary=='model':model['last_sample_ns']=now[0]-beat_sync.FRESH_NS-1
                    elif boundary=='foreground':now[0]+=1_000_000_001
                    elif boundary=='oversleep':now[0]=target+1
                with patch.object(d,'sleeper',side_effect=wait):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                self.assertTrue(waits);self.assertEqual(reason,caught.exception.code)
                self.assertEqual([],sent);self.assertIsNone(d.state['actions'][-1]['issued_ns'])
                self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
                self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])

    def test_40_failed_tracking_reacquires_within_same_deadline_and_honors_goods(self):
        from necroprobe import beat_sync,shop_navigation
        for visible in (False,True):
            with self.subTest(goods=visible),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                d.synchronize(d.observe());current=d.observe();old_samples=deepcopy(d.samples)
                current['_extra']['beat']['remaining']=(current['_extra']['beat']['remaining']+.3)%1
                extract=beat_sync.extract.side_effect;navigation=shop_navigation.scan.side_effect
                def shifted(image):
                    result=extract(image);result['remaining']=(result['remaining']+.3)%1;return result
                def goods(image):
                    scene=navigation(image)
                    if visible:scene.goods='visible'
                    return scene
                count=len(captures);start=now[0];observe=d.observe;first=[True]
                def collect():
                    if first[0]:
                        self.assertIsNone(d.model);self.assertTrue(d.beat_only)
                        self.assertEqual(1,len(d.samples));self.assertNotIn(d.samples[0],old_samples)
                        first[0]=False
                    self.assertEqual(start+12_000_000_000,d.sync_deadline)
                    return observe()
                with patch.object(beat_sync,'extract',side_effect=shifted), \
                     patch.object(shop_navigation,'scan',side_effect=goods), \
                     patch.object(d,'observe',side_effect=collect):
                    before,updated=d.synchronize(current)
                self.assertEqual(count+8,len(captures));self.assertTrue(all(light for _,light in captures[count:-1]))
                self.assertFalse(captures[-1][1]);self.assertLess(now[0]-start,12_000_000_000)
                self.assertFalse(any(sample in old_samples for sample in d.samples))
                self.assertEqual(visible,d.state['goods_visible']);self.assertIs(before,d.last)
                if visible:self.assertIsNone(updated);self.assertEqual('visible',d.goods(before))
                else:self.assertEqual('tracking',updated['mode']);self.assertIs(updated,d.model)
                self.assertEqual([],sent);self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_42_final_wait_lateness_budget_is_not_the_game_acceptance_window(self):
        from necroprobe import beat_sync
        for lateness,accepted in ((10_000_000,True),(10_000_001,False),(100_000_000,False)):
            with self.subTest(lateness=lateness),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe())
                target=beat_sync.next_target(model,now[0],p.LEAD_NS+120_000_000)
                def wait(seconds):now[0]=target-p.LEAD_NS+lateness
                with patch.object(d,'sleeper',side_effect=wait):
                    if accepted:d.perform('left',before,model)
                    else:
                        with self.assertRaises(ProbeError):d.perform('left',before,model)
                self.assertEqual(int(accepted),len(sent))
                if accepted:
                    self.assertEqual(p.LEAD_NS-lateness,target-d.state['actions'][-1]['issued_ns'])
                else:
                    self.assertFalse(d.pending);self.assertIsNone(d.state['actions'][-1]['issued_ns'])

    def test_41_failed_rpc_keeps_unknown_pending_without_inventing_rpc_timings(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,captures,scenes,sent):
            before,model=d.synchronize(d.observe());call=d.client.call;attempts=[]
            def failing(method,params,timeout):
                if method=='run_steps':attempts.append(method);raise ProbeError('connection_error')
                return call(method,params,timeout)
            with patch.object(d.client,'call',side_effect=failing):
                with self.assertRaises(ProbeError):d.perform('left',before,model)
                d.finish('connection_error',d.last)
            entry=d.state['actions'][-1]
            self.assertEqual(['run_steps'],attempts);self.assertEqual({},entry['rpc_timings'])
            self.assertIsNotNone(entry['issued_ns']);self.assertIsNone(entry['completed_ns'])
            self.assertEqual('unknown',entry['outcome']);self.assertTrue(d.pending)
            self.assertTrue(d.state['input_pending']);self.assertIsNone(d.last)
            p.write(folder,d.outer)
            p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])

    def test_43_test021_cost_selects_nearest_beat_after_single_pending_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder,test021=True) as (d,now,captures,scenes,sent):
            first=d.observe();checkpoints=len(d.report['checkpoint_ms'])
            before,model=d.synchronize(first)
            self.assertEqual(checkpoints,len(d.report['checkpoint_ms']))
            self.assertEqual(2_348_703_000,now[0]-before['_captured'])
            stored=[];checkpoint=d.checkpoint
            def save_pending():
                checkpoint()
                if d.pending:stored.append(deepcopy(d.outer))
            with patch.object(d,'checkpoint',side_effect=save_pending):d.perform('left',before,model)
            self.assertEqual([p.move_batch('left')],sent)
            self.assertEqual(1,len(stored));self.assertEqual(model,stored[0]['walk']['models'][-1])
            entry=d.state['actions'][-1]
            self.assertLessEqual(entry['issued_ns']-before['_captured'],3_000_000_000)
            self.assertEqual(p.LEAD_NS,entry['target_ns']-entry['issued_ns'])

    def test_44_infeasible_dispatch_window_stops_before_wait_and_rpc(self):
        from necroprobe import beat_sync
        for boundary in ('frame','model','foreground','session','walk'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());model=deepcopy(model)
                target=now[0]+600_000_000;until=target-p.LEAD_NS
                if boundary=='frame':before['_captured']=until-beat_sync.FRESH_NS-1
                elif boundary=='model':model['last_sample_ns']=until-beat_sync.FRESH_NS-1
                elif boundary=='foreground':target=now[0]+1_400_000_000
                elif boundary=='session':d.stop_ns=until
                else:d.state['started_ns']=until-p.WALK_SECONDS*1_000_000_000
                with patch.object(beat_sync,'next_target',return_value=target), \
                     patch.object(d,'sleeper',side_effect=AssertionError('infeasible wait started')):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                self.assertEqual('dispatch_window_expired',caught.exception.code)
                self.assertEqual([],sent);self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])
                entry=d.state['actions'][-1]
                self.assertEqual('not_requested',entry['outcome']);self.assertIsNone(entry['issued_ns'])
                self.assertEqual({},entry['rpc_timings'])

    def test_45_cleanup_refreshes_stale_or_missing_frame_once_for_any_reason(self):
        for reason in ('host_observation_expired','dispatch_window_expired','internal_error','beat_sync_timeout'):
            for missing in (False,True):
                with self.subTest(reason=reason,missing=missing),tempfile.TemporaryDirectory() as folder:
                    d,now=self.build(folder);old=d.last
                    if missing:d.last=None;old=None
                    else:old['_captured']=now[0]-3_000_000_001
                    def failed_capture():
                        self.assertIsNone(d.last);self.assertTrue(d.finishing)
                        raise ProbeError('connection_error')
                    with patch.object(d,'observe',side_effect=failed_capture) as capture:
                        with self.assertRaises(ProbeError):d.finish(reason,old)
                        d.finish('navigation_unknown',old)
                    self.assertEqual(1,capture.call_count);self.assertIsNone(d.last)
                    self.assertNotIn('run_steps',d.client.calls)

    def test_50_pending_checkpoint_or_target_exception_cannot_send_or_cleanup(self):
        from necroprobe import beat_sync
        for boundary in ('checkpoint','target'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());checkpoint=d.checkpoint;next_target=beat_sync.next_target
                def persist():
                    checkpoint()
                    if boundary=='checkpoint':raise OSError('simulated output failure')
                def target(*args,**kwargs):
                    if d.pending:raise RuntimeError('simulated target failure')
                    return next_target(*args,**kwargs)
                with patch.object(d,'checkpoint',side_effect=persist),patch.object(beat_sync,'next_target',side_effect=target):
                    with self.assertRaises(OSError if boundary=='checkpoint' else RuntimeError):d.perform('left',before,model)
                persisted=p.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
                self.assertEqual(model,persisted['walk']['models'][-1])
                self.assertTrue(persisted['walk']['input_pending']);self.assertTrue(d.pending)
                self.assertEqual('unknown',persisted['walk']['actions'][-1]['outcome'])
                calls=len(d.client.calls);d.finish('internal_error',d.last)
                self.assertEqual(calls,len(d.client.calls));self.assertEqual([],sent)

    def test_51_preparation_model_expiry_is_distinct_from_invalid_model(self):
        from necroprobe import beat_sync
        for invalid in (False,True):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as folder, \
                 self.measured_runtime(folder) as (d,now,captures,scenes,sent):
                before,model=d.synchronize(d.observe());checkpoint=d.checkpoint
                def change():
                    checkpoint()
                    if invalid:model['residual_cycles']=float('inf')
                    else:now[0]=model['last_sample_ns']+beat_sync.FRESH_NS+1
                with patch.object(d,'checkpoint',side_effect=change), \
                     patch.object(d,'sleeper',side_effect=AssertionError('expired wait started')):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model)
                self.assertEqual('beat_unconfirmed' if invalid else 'dispatch_window_expired',caught.exception.code)
                self.assertEqual([],sent);self.assertFalse(d.pending);self.assertFalse(d.state['input_pending'])

if __name__=='__main__':unittest.main()
