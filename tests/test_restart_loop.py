"""TEST-014のループ契約。実機合格を代用しない。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from necroprobe import restart_loop as p
from necroprobe.validation import ProbeError


def frame(state='floor', gold='clear', room=1):
    return {'state':state,'gold':gold if state=='floor' else 'unknown',
            'fingerprint':[room*30]*48 if state=='floor' else [], 'gold_peak':160 if gold=='candidate' else 40,
            'restart_label':state=='pause'}

P=frame('pause'); A=frame(); B=frame(room=2); G=frame(gold='candidate',room=2); U=frame('unknown')


class Driver:
    def __init__(self, frames, fail=None, timeout_at=None):
        self.frames=iter(deepcopy(frames));self.actions=[];self.reads=0;self.saved=[]
        self.fail=fail;self.timeout_at=timeout_at;self.report={'candidate':False,'paused':False,'restarts_confirmed':0,'runs':[],'reason':None}
        self.current=None
    def observe(self):
        self.current=next(self.frames); self.reads+=1; return self.current
    def tap(self, action, observed):
        self.actions.append(action)
        if self.fail==len(self.actions): raise ProbeError('batch_unknown')
    def save(self, name, observed): self.saved.append(name)
    def record_run(self, observed): self.report['runs'].append(observed['gold'])
    def checkpoint(self): pass
    def bounded(self): return self.timeout_at is not None and self.reads>=self.timeout_at
    def changed(self,a,b): return a['fingerprint']!=b['fingerprint']


class RestartLoopTests(unittest.TestCase):
    def test_01_resume_restart_until_gold_then_pause(self):
        d=Driver([P,A,A,P,B,G,P])
        p.collect(d)
        self.assertEqual(['resume','pause','restart','pause'],d.actions)
        self.assertEqual(1,d.report['restarts_confirmed'])
        self.assertEqual('gold_candidate',d.report['reason'])
        self.assertTrue(d.report['candidate']);self.assertTrue(d.report['paused'])
        self.assertIn('found.jpg',d.saved)

    def test_02_candidate_is_latched_and_never_restarted(self):
        for end in [P,A,U]:
            with self.subTest(end=end['state']):
                d=Driver([G,end,end,end,end,end,end])
                p.collect(d)
                self.assertEqual(['pause'],d.actions)
                self.assertTrue(d.report['candidate'])
                self.assertEqual(0,d.report['restarts_confirmed'])
        d=Driver([G],fail=1)
        with self.assertRaises(ProbeError):p.collect(d)
        self.assertEqual(['pause'],d.actions);self.assertTrue(d.report['candidate'])

    def test_10_candidate_during_pause_transition_is_kept_without_toggle(self):
        d=Driver([A,A,G,P])
        p.collect(d)
        self.assertEqual(['pause'],d.actions)
        self.assertTrue(d.report['candidate']);self.assertTrue(d.report['paused'])
        self.assertEqual('gold_candidate',d.report['reason'])
        self.assertIn('found.jpg',d.saved)
        d=Driver([A,G,P],timeout_at=1)
        p.collect(d)
        self.assertEqual(['pause'],d.actions)
        self.assertTrue(d.report['candidate'])
        self.assertEqual('gold_candidate',d.report['reason'])

    def test_03_clear_streak_and_new_run_confirmation(self):
        d=Driver([A,U,A,A,P,U,A,B,G,P])
        p.collect(d)
        self.assertEqual(['pause','restart','pause'],d.actions)
        self.assertEqual(1,d.report['restarts_confirmed'])
        d=Driver([A,A,P]+[A]*7)
        with self.assertRaises(ProbeError):p.collect(d)
        self.assertEqual(['pause','restart'],d.actions)
        self.assertEqual(0,d.report['restarts_confirmed'])
        d=Driver([A,A,P,G,P])
        p.collect(d)
        self.assertTrue(d.report['candidate'])
        self.assertEqual(['pause','restart','pause'],d.actions)

    def test_04_unknown_and_ambiguous_input_do_not_retry(self):
        d=Driver([U]*7)
        with self.assertRaises(ProbeError):p.collect(d)
        self.assertEqual([],d.actions)
        d=Driver([A,A,P],fail=2)
        with self.assertRaises(ProbeError):p.collect(d)
        self.assertEqual(['pause','restart'],d.actions)
        uncertain=frame(gold='unknown')
        d=Driver([uncertain]*7)
        with self.assertRaises(ProbeError):p.collect(d)
        self.assertNotIn('restart',d.actions)

    def test_05_limits_pause_without_another_restart(self):
        d=Driver([A,A,P,B,B,P])
        p.collect(d,max_restarts=1)
        self.assertEqual(1,d.report['restarts_confirmed'])
        self.assertEqual(['pause','restart','pause'],d.actions)
        self.assertEqual('restart_limit',d.report['reason'])
        d=Driver([A,P],timeout_at=1)
        p.collect(d)
        self.assertEqual(['pause'],d.actions)
        self.assertEqual('time_limit',d.report['reason'])

if __name__=='__main__': unittest.main()

# 固定RPC・保存遅延・二重起動の境界だけを追加検証する。
from unittest.mock import patch
from necroprobe.protocol import GAME, RpcReply
from test_resume_once import GOOD

class LiveStub:
    def __init__(self,result=None,system=None):
        self.calls=[]; self.result=deepcopy(GOOD if result is None else result)
        self.system=system or {'foreground_app':GAME,'screen_locked':False}
    def call(self,method,params,timeout):
        self.calls.append(method)
        if method=='device_info':return RpcReply({'system':self.system,'capabilities':list(p.resume.CAPABILITIES)}, {})
        if method=='run_steps':return RpcReply(self.result,{})
        raise AssertionError(method)

class InputBoundaryTests(unittest.TestCase):
    def build(self,folder,client=None):
        now=[1_000_000_000]
        report=p.new_report(now[0],'a'*32)
        d=p.RuntimeDriver(client or LiveStub(),report,folder,now[0]+10_000_000_000,clock=lambda:now[0])
        obs=dict(A,_captured=now[0],_raw=b'original',_sha='0'*64);d.last=obs
        return d,obs,now
    def test_06_checkpoint_delay_expiry_and_foreground_block_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            for delay in (1_000_000_001,3_000_000_001,11_000_000_000):
                d,obs,now=self.build(folder)
                d.checkpoint=lambda:now.__setitem__(0,now[0]+delay)
                with self.assertRaises(ProbeError):d.tap('pause',obs)
                self.assertNotIn('run_steps',d.client.calls)
                self.assertEqual('not_requested',d.report['actions'][-1]['outcome'])
            for system in ({'foreground_app':'other','screen_locked':False},{'foreground_app':GAME,'screen_locked':True}):
                d,obs,_=self.build(folder,LiveStub(system=system))
                with self.assertRaises(ProbeError):d.tap('pause',obs)
                self.assertNotIn('run_steps',d.client.calls)
    def test_07_unknown_batch_is_not_retried_and_fixed_params(self):
        with tempfile.TemporaryDirectory() as folder:
            d,obs,_=self.build(folder,LiveStub(result={'message':'PRIVATE'}))
            with self.assertRaises(ProbeError):d.tap('pause',obs)
            with self.assertRaises(ProbeError):d.tap('pause',obs)
            self.assertEqual(1,d.client.calls.count('run_steps'))
            self.assertNotIn('PRIVATE',str(d.report))
            self.assertEqual('unknown',d.report['actions'][0]['outcome'])
        client=p.RestartClient.__new__(p.RestartClient)
        for action in p.POINTS:
            good=p.batch(action);client._validate('run_steps',good)
            for value in (True,float('nan'),-1,448.0):
                bad=deepcopy(good);bad['steps'][1]['params']['x']=value
                with self.assertRaises(ProbeError):client._validate('run_steps',bad)
        with self.assertRaises(ProbeError):client._validate('tap',{'x':297,'y':448})
    def test_08_lock_and_report_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            lock=Path(folder)/'lock'
            with p.device_lock(lock):
                with self.assertRaises(ProbeError):
                    with p.device_lock(lock): self.fail('duplicate owner')
            with p.device_lock(lock): pass
            report=p.new_report(1,'a'*32);p.write(folder,report)
            self.assertEqual(report,p.read_report(Path(folder)/'report.json','a'*32,1))
            report['reason']='PRIVATE';p.write(folder,report)
            with self.assertRaises(ValueError):p.read_report(Path(folder)/'report.json','a'*32,1)

class WorkerIntegrationTests(unittest.TestCase):
    def test_09_worker_capture_geometry_classification_and_files(self):
        import base64,io,time
        from PIL import Image,ImageDraw
        from test_gold_scan import floor,fixture
        from test_source_geometry import geometry_payload
        menu=Image.new('RGB',(896,414));fixture(menu,'continue');fixture(menu,'restart')
        first=floor();gold=floor()
        ImageDraw.Draw(gold).rectangle((224,70,391,165),fill=(210,170,30))
        def jpeg(im):
            out=io.BytesIO();im.save(out,'JPEG',quality=60);return out.getvalue()
        sequence=[jpeg(im) for im in (menu,first,first,menu,gold,menu)]
        class IntegrationClient(LiveStub):
            def __init__(self,*args,**kwargs):super().__init__();self.frames=iter(sequence)
            def call(self,method,params,timeout):
                if method=='launch_app':return RpcReply({}, {})
                if method=='screenshot':
                    _,payload=geometry_payload(p.resume.CAPTURE_PARAMS,size=(896,414),source_scale=2)
                    payload.update(data=base64.b64encode(next(self.frames)).decode(),source_orientation=2)
                    return RpcReply(payload,{})
                return super().call(method,params,timeout)
        with tempfile.TemporaryDirectory() as folder:
            start=time.monotonic_ns();run_id='b'*32
            args=p.parser().parse_args(['--worker','--output',folder,'--start-ns',str(start),
                                       '--stop-ns',str(start+30_000_000_000),'--run-id',run_id,'--python-crypto'])
            p.write(folder,p.new_report(start,run_id))
            original_lock=p.device_lock
            with patch.object(p,'RestartClient',IntegrationClient),patch.object(p,'load_pairing',return_value=(None,None)), \
                 patch.object(p,'device_lock',side_effect=lambda:original_lock(Path(folder)/'lock')):
                self.assertEqual(0,p.worker(args))
            r=p.read_report(Path(folder)/'report.json',run_id,start)
            self.assertEqual(('completed','gold_candidate',True,1),(r['status'],r['reason'],r['paused'],r['restarts_confirmed']))
            self.assertEqual(['resume','pause','restart','pause'],[a['action'] for a in r['actions']])
            self.assertEqual(sequence[4],(Path(folder)/'found.jpg').read_bytes())
            self.assertEqual(sequence[-1],(Path(folder)/'stopped.jpg').read_bytes())
            self.assertEqual(6,len(r['capture_ms']))
            self.assertNotIn('PRIVATE',str(r))
