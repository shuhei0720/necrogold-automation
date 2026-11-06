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

if __name__=='__main__':unittest.main()
