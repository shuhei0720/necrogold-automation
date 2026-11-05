"""TEST-015の必要な変更境界。端末速度は別途実機計測。"""
import base64
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image
from necroprobe import restart_loop as p, gold_scan
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
from test_restart_loop import A,P,Driver,LiveStub
from test_source_geometry import geometry_payload
from test_gold_scan import floor

class SpeedTests(unittest.TestCase):
    def driver(self,folder,client=None):
        now=[1_000_000_000]
        report=p.new_report(now[0],'c'*32)
        d=p.RuntimeDriver(client or LiveStub(),report,folder,now[0]+20_000_000_000,clock=lambda:now[0])
        return d,now
    def test_01_evidence_is_deferred_and_candidate_kept_within_ram_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.driver(folder)
            obs=dict(A,_raw=b'a'*50000)
            d.save('run-001.jpg',obs)
            self.assertFalse((Path(folder)/'run-001.jpg').exists())
            # New candidate is retained even with normal evidence filling the budget.
            for i in range(1,32):d.save('run-%03d.jpg'%i,dict(obs,_raw=b'x'*150000))
            d.save('found.jpg',dict(obs,_raw=b'G'*150000))
            self.assertLessEqual(sum(map(len,d.images.values())),4*1024*1024)
            self.assertEqual(b'G'*150000,d.images['found.jpg'])
            d.export_images()
            self.assertEqual(b'G'*150000,(Path(folder)/'found.jpg').read_bytes())
            self.assertIn('found.jpg',d.report['exported_images'])
    def test_02_capture_is_decoded_once_for_inspection_and_analysis(self):
        buf=io.BytesIO();floor().save(buf,'JPEG',quality=60);raw=buf.getvalue()
        _,payload=geometry_payload(p.resume.CAPTURE_PARAMS,size=(896,414),source_scale=2)
        payload.update(data=base64.b64encode(raw).decode(),source_orientation=2)
        class Capture(LiveStub):
            def call(self,method,params,timeout):
                if method=='screenshot':return RpcReply(payload,{})
                return super().call(method,params,timeout)
        with tempfile.TemporaryDirectory() as folder:
            d,_=self.driver(folder,Capture())
            with patch.object(Image,'open',wraps=Image.open) as opened:
                obs=d.observe()
            self.assertEqual('floor',obs['state'])
            # One verified image open + one integrity-only open; no second decode in analysis.
            self.assertEqual(2,opened.call_count)
            self.assertEqual(1,len(d.report['decode_ms']))
            # first-confirmedは同じpauseでは維持し、次のpause遷移で更新する。
            with patch.object(gold_scan,'analyze_image',side_effect=[deepcopy(P),deepcopy(P),deepcopy(A),deepcopy(P)]):
                d.observe(); first=d.menu_since_ns
                d.clock=lambda:first+10_000_000
                d.observe();self.assertEqual(first,d.menu_since_ns)
                d.observe();self.assertIsNone(d.menu_since_ns)
                d.observe();self.assertEqual(first+10_000_000,d.menu_since_ns)
    def test_03_restart_menu_wait_resets_and_rechecks_after_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.driver(folder)
            d.sleeper=lambda seconds:now.__setitem__(0,now[0]+round(seconds*1e9))
            for elapsed in (0,200_000_000,300_000_000):
                d.menu_since_ns=now[0]-elapsed
                obs=dict(P,_captured=now[0]);d.last=obs
                begin=now[0]
                guards=d.client.calls.count('device_info')
                d.tap('restart',obs)
                self.assertGreaterEqual(now[0]-d.menu_since_ns,200_000_000)
                self.assertEqual(max(0,200_000_000-elapsed),now[0]-begin)
                self.assertEqual(2 if elapsed==0 else 1,d.client.calls.count('device_info')-guards)
                if elapsed>=200_000_000:self.assertEqual(0,d.report['actions'][-1]['menu_wait_ms'])
            d.menu_since_ns=now[0];obs=dict(P,_captured=now[0]);d.last=obs
            def changed_app(seconds):
                now[0]+=round(seconds*1e9)
                d.client.system={'foreground_app':'other','screen_locked':False}
            d.sleeper=changed_app
            prior=d.client.calls.count('run_steps')
            with self.assertRaises(ProbeError):d.tap('restart',obs)
            self.assertEqual(prior,d.client.calls.count('run_steps'))
            d.client.system={'foreground_app':p.GAME,'screen_locked':False}
            d.menu_since_ns=now[0];d.stop_ns=now[0]+100_000_000
            d.last=obs=dict(P,_captured=now[0])
            d.sleeper=lambda seconds:now.__setitem__(0,now[0]+round(seconds*1e9))
            with self.assertRaises(ProbeError):d.tap('restart',obs)
            self.assertEqual(prior,d.client.calls.count('run_steps'))
    def test_04_export_failure_preserves_confirmed_game_result(self):
        with tempfile.TemporaryDirectory() as folder:
            d,_=self.driver(folder)
            d.report.update(candidate=True,paused=True,status='completed',reason='gold_candidate')
            d.save('found.jpg',dict(A,_raw=b'G'))
            original=p.atomic_write
            def failed_image(path,raw):
                if str(path).endswith('.jpg'):raise OSError('private path')
                return original(path,raw)
            with patch.object(p,'atomic_write',side_effect=failed_image):d.export_images()
            self.assertTrue(d.report['candidate']);self.assertTrue(d.report['paused'])
            self.assertEqual('output_write_failed',d.report['export_error'])
            self.assertEqual([],d.report['exported_images'])
            self.assertNotIn('private path',str(d.report))


    def test_05_parent_keeps_confirmed_control_when_export_is_interrupted(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            args=p.parser().parse_args(['--output',folder])
            def interrupted_export(command,timeout,diagnostics):
                cp=Path(command[command.index('--checkpoint-dir')+1])
                r=json.loads((cp/'report.json').read_bytes())
                r.update(status='completed',reason='gold_candidate',candidate=True,paused=True,
                         control_reason='gold_candidate',control_end_ns=r['start_ns']+1,end_ns=r['start_ns']+1)
                p.write(cp,r)
                diagnostics.update(exit_confirmed=True,returncode=-15)
                return 'session_deadline'
            with patch.object(p.supervisor,'supervise',side_effect=interrupted_export):
                self.assertEqual(2,p.run(args))
            path=next(Path(folder).glob('*/parent-result.json'))
            r=json.loads(path.read_bytes())
            self.assertTrue(r['candidate']);self.assertTrue(r['paused'])
            self.assertFalse(r['export_complete'])
            self.assertEqual('gold_candidate',r['control_reason'])
            self.assertEqual('session_deadline',r['reason'])

    def test_07_worker_records_control_error_before_export(self):
        from contextlib import nullcontext
        class LaunchStub(LiveStub):
            def call(self,method,params,timeout):
                if method=='launch_app':return RpcReply({}, {})
                return super().call(method,params,timeout)
        with tempfile.TemporaryDirectory() as folder:
            start=time.monotonic_ns();run_id='d'*32
            args=p.parser().parse_args(['--worker','--output',folder,'--run-id',run_id,
                '--start-ns',str(start),'--stop-ns',str(start+20_000_000_000)])
            p.write(folder,p.new_report(start,run_id))
            def export(driver):
                r=p.read_report(Path(folder)/'report.json',run_id,start)
                self.assertEqual('host_observation_expired',r['control_reason'])
                self.assertIsNotNone(r['control_end_ns'])
                self.assertEqual('stopped',r['status'])
            with patch.object(p,'device_lock',return_value=nullcontext()), \
                 patch.object(p,'load_pairing',return_value=(b'key','token')), \
                 patch.object(p,'RestartClient',return_value=LaunchStub()), \
                 patch.object(p,'collect',side_effect=ProbeError('host_observation_expired')), \
                 patch.object(p.RuntimeDriver,'export_images',export):
                self.assertEqual(0,p.worker(args))

    def test_06_initial_gold_pause_precedes_slow_image_export(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.driver(folder)
            frames=iter([dict(A,gold='candidate',gold_peak=167,_raw=b'gold',_captured=now[0],_seen_ns=now[0],_sha='0'*64),
                         dict(P,_raw=b'pause',_captured=now[0],_seen_ns=now[0],_sha='1'*64)])
            def observe():
                d.last=next(frames);return d.last
            d.observe=observe
            original=p.atomic_write
            def slow_export(path,raw):
                if str(path).endswith('.jpg'):
                    self.assertTrue(d.report['paused'])
                    self.assertEqual(1,d.client.calls.count('run_steps'))
                    now[0]+=5_000_000_000
                return original(path,raw)
            with patch.object(p,'atomic_write',side_effect=slow_export):
                p.collect(d)
                self.assertTrue(d.report['paused'])
                self.assertEqual([],list(Path(folder).glob('*.jpg')))
                d.export_images()
            self.assertEqual(1,d.client.calls.count('run_steps'))
            self.assertTrue(d.report['candidate'])
            self.assertFalse(d.report['candidate_pause_already_issued'])
            self.assertEqual(d.report['start_ns'],d.report['candidate_detected_ns'])

if __name__=='__main__':unittest.main()
