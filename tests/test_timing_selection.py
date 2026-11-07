"""TEST034: 実変位を観測して入力先行量を選ぶ。入力受付時刻の校正ではない。"""
from copy import deepcopy
from pathlib import Path
import hashlib,os,tempfile,unittest
from unittest.mock import patch
from PIL import Image
from necroprobe import shop_walk as w,shop_navigation as nav,beat_sync
from necroprobe.validation import ProbeError
import test_shop_walk as old
import test_shop_navigation as oldnav

class TimingSelectionTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    measured_runtime=old.SyncDeadlineTests.measured_runtime

    def fresh(self,d,now):
        before,model=d.synchronize(d.observe())
        before['_extra']['scene']=oldnav.ShopNavigationBurstTests.corridor('left',6)
        before['_captured']=now[0];before['_http_start_ns']=now[0];model['last_sample_ns']=now[0]
        d.state['lead_confirmed']=False;d.state['lead_trials']=[]
        return before,model

    def test_actual_static_scene_initial_single(self):
        root=os.environ.get('NECRO_TEST033_FRAMES')
        if not root:self.skipTest('external TEST033 frames not supplied')
        frames=[]
        for name,digest in [('run-099.jpg','1cf9d17900edd14e1cc157ac34e5e760240615004b95e898f0dccdec8ef0233a'),('run-101.jpg','099d261da354e398ae10543f4e91a98ce333f89c50cdb096c581e828a1bbced5')]:
            path=Path(root)/name;self.assertEqual(digest,hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:frames.append(nav.scan(image.convert('RGB')))
        from necroprobe.input_timing import eligible
        self.assertEqual('blocked',nav.motion(*frames,'up'))
        self.assertTrue(all(eligible(s,'up') for s in frames))
        with tempfile.TemporaryDirectory() as folder:
            r=w.new_report(1,'a'*32);d=w.Driver(None,r,folder,100_000_000_000,folder,clock=lambda:1)
            self.assertFalse(d.state['lead_confirmed'])
            before=old.obs();before['_extra']['scene']=frames[0]
            self.assertEqual(1,d.burst_count(before,d.choose(before),16))

    def execute_walk(self,outcomes,modify=None):
        # 本物のDriver/perform/walk。画像系列と正味変位だけを構成する。
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        context=self.measured_runtime(folder.name);d,now,_,_,sent=context.__enter__();self.addCleanup(context.__exit__,None,None,None)
        before,model=self.fresh(d,now);images=[];motions=iter(outcomes);sent_leads=[]
        def observe():
            o=deepcopy(before);o['_captured']=now[0];o['_http_start_ns']=now[0];o['_sha']=str(len(images))
            if len(images)>0 and not outcomes:o['_extra']['scene'].goods='visible'
            d.last=o;images.append(o)
            if modify:modify(d,o,images,sent)
            return o
        def synchronize(o):model['last_sample_ns']=now[0];return o,model
        def movement(a,b,direction,expected_steps=1):return next(motions)
        real=d.perform
        def perform(action,o,m=None,count=1):
            if action in w.MOVE_POINTS:sent_leads.append((d.state['dispatch_lead_ns'],count))
            else:return 0
            return real(action,o,m,count=count)
        def finish(reason,o):d.state['reason']=reason
        d.last=deepcopy(before);d.last['state']='pause'
        with patch.object(d,'observe',side_effect=observe),patch.object(d,'synchronize',side_effect=synchronize),patch.object(d,'movement',side_effect=movement),patch.object(d,'perform',side_effect=perform),patch.object(d,'finish',side_effect=finish):
            w.walk(d)
        return d,sent,sent_leads,images

    def test_real_walk_default_single_blocked_then_moved_then_four(self):
        def visible(d,o,images,sent):
            if len(sent)>=3:o['_extra']['scene'].goods='visible'
        d,sent,leads,images=self.execute_walk(['blocked','moved'],visible)
        self.assertEqual([(150_000_000,1),(75_000_000,1),(75_000_000,4)],leads)
        self.assertEqual(1,d.state['moves_confirmed']);self.assertTrue(d.state['lead_confirmed'])
        self.assertEqual(['blocked','moved'],[a['motion'] for a in d.state['lead_trials']])
        self.assertEqual([1,2,3],[e['index'] for e in d.state['events']]);self.assertEqual('goods_visible',d.state['reason'])
        self.assertEqual(6,len(sent))

    def test_all_seven_trials_consume_inputs_and_stop(self):
        from necroprobe.input_timing import LEADS_NS
        d,sent,leads,_=self.execute_walk(['blocked']*7)
        self.assertEqual([(x,1) for x in LEADS_NS],leads);self.assertEqual(7,len(sent))
        self.assertEqual('timing_not_found',d.state['reason']);self.assertEqual(0,d.state['moves_confirmed'])
        self.assertEqual(7,sum(a['scheduled_inputs'] for a in d.state['actions']))
        with patch.object(w,'MAX_STEPS',2):
            d,sent,leads,_=self.execute_walk(['blocked']*2)
        self.assertEqual(2,len(sent));self.assertEqual('walk_limit',d.state['reason'])

    def test_unknown_changed_route_protection_and_goods_do_not_retune(self):
        for fault in ('unknown','partial','direction','gold','protected','goods'):
            def mutate(d,o,images,sent):
                if not sent:return
                s=o['_extra']['scene']
                if fault=='gold':s.gold.add((4,4))
                if fault=='protected':s.protected.add((-1,0))
                if fault=='goods':s.goods='visible'
                if fault=='direction':s.tiles=oldnav.ShopNavigationBurstTests.corridor('up',6).tiles;s.gold={(1,-6),(-1,-6)}
            d,sent,leads,_=self.execute_walk([fault if fault in ('unknown','partial') else 'blocked'],mutate)
            self.assertEqual(1,len(sent),fault);self.assertEqual([],d.state['lead_trials'],fault)
            self.assertFalse(d.state['lead_confirmed'])

    def test_selected_lead_applies_to_single_followup_and_report(self):
        for lead in (75_000_000,450_000_000,25_000_000):
            with self.subTest(lead=lead),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=self.fresh(d,now);d.state['lead_confirmed']=True;d.state['dispatch_lead_ns']=lead
                from necroprobe.input_timing import LEADS_NS
                d.state['lead_trials']=[{'lead_ns':value,'direction':'left','motion':'moved' if value==lead else 'blocked'}
                                        for value in LEADS_NS[:LEADS_NS.index(lead)+1]]
                # 同期短縮でepochが変わっても、先行量の伝播を同じ前面期限内で検証する。
                # 前面1秒/10ms境界はtest_foreground_windowで独立して検証する。
                target=now[0]+lead+300_000_000
                with patch.object(beat_sync,'next_target',return_value=target):
                    self.assertEqual(2,d.perform('left',before,model,count=2))
                for a in d.state['actions']:
                    self.assertEqual(lead,a['dispatch_lead_ns']);self.assertEqual(lead,a['target_ns']-a['issued_ns'])
                self.assertEqual(model['period_ns'],d.state['actions'][1]['target_ns']-d.state['actions'][0]['target_ns'])
                w.write(folder,d.outer);w.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
                self.assertFalse(d.state['dispatch_timing_calibrated'])

    def test_early_image_or_unknown_ack_cannot_advance_and_observation_waits(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=self.fresh(d,now);d.state['dispatch_lead_ns']=450_000_000
            from necroprobe.input_timing import LEADS_NS
            d.state['lead_trials']=[{'lead_ns':value,'direction':'left','motion':'blocked'} for value in LEADS_NS[:5]]
            d.perform('left',before,model,count=1);a=d.state['actions'][-1]
            self.assertGreaterEqual(now[0],a['target_ns']+200_000_000)
            after=deepcopy(before);after['_captured']=now[0];after['_http_start_ns']=a['target_ns']-1;d.last=after
            self.assertIsNone(d.timing_result(before,after,'left','blocked',1));self.assertEqual(5,len(d.state['lead_trials']))

            after['_http_start_ns']=now[0];a['outcome']='unknown'
            self.assertIsNone(d.timing_result(before,after,'left','blocked',1));self.assertEqual(5,len(d.state['lead_trials']))
            a['outcome']='acknowledged'
            self.assertEqual('retry',d.timing_result(before,after,'left','blocked',1))
            self.assertEqual(6,len(d.state['lead_trials']));self.assertEqual(25_000_000,d.state['dispatch_lead_ns'])

    def test_single_long_lead_must_fit_all_deadlines_and_empty_trials_are_unconfirmed(self):
        for boundary in ('frame','phase','walk','session'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
                before,model=self.fresh(d,now);d.state['dispatch_lead_ns']=450_000_000
                from necroprobe.input_timing import LEADS_NS
                d.state['lead_trials']=[{'lead_ns':value,'direction':'left','motion':'blocked'} for value in LEADS_NS[:5]]
                target=now[0]+600_000_000;until=target-450_000_000
                if boundary=='frame':before['_captured']=until-2_900_000_000
                if boundary=='phase':model['last_sample_ns']=until-2_900_000_000
                if boundary=='walk':d.state['started_ns']=until-44_900_000_000
                if boundary=='session':d.stop_ns=until+100_000_000
                with patch.object(beat_sync,'next_target',return_value=target):
                    with self.assertRaises(ProbeError) as caught:d.perform('left',before,model,count=1)
                self.assertEqual('dispatch_window_expired',caught.exception.code)
                self.assertEqual([],sent);self.assertFalse(d.pending)
        with tempfile.TemporaryDirectory() as folder:
            for confirmed,lead in ((True,150_000_000),(False,450_000_000),(True,450_000_000)):
                r=w.new_report(1,'a'*32);r['walk'].update(lead_confirmed=confirmed,dispatch_lead_ns=lead)
                w.write(folder,r)
                with self.assertRaises(ValueError):w.read_report(Path(folder)/'report.json','a'*32,1)

    def test_lead_mutation_during_sequence_stops_and_report_rejects_bad_trials(self):
        with tempfile.TemporaryDirectory() as folder,self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=self.fresh(d,now);d.state['lead_confirmed']=True;call=d.client.call
            def rpc(method,params,timeout):
                reply=call(method,params,timeout)
                if method=='run_steps':d.state['dispatch_lead_ns']=75_000_000
                return reply
            with patch.object(d.client,'call',side_effect=rpc):
                with self.assertRaises(ProbeError):d.perform('left',before,model,count=2)
            self.assertEqual(1,len(sent));self.assertFalse(d.pending);self.assertIsNone(d._followup_token)
            for trials in ([{'lead_ns':True,'direction':'left','motion':'blocked'}],
                           [{'lead_ns':150_000_000,'direction':'left','motion':'unknown'}],
                           [{'lead_ns':150_000_000,'direction':'left','motion':'blocked'}]*2):
                r=w.new_report(1,'a'*32);r['walk']['lead_trials']=trials;w.write(folder,r)
                with self.assertRaises(ValueError):w.read_report(Path(folder)/'report.json','a'*32,1)

if __name__=='__main__':unittest.main()
