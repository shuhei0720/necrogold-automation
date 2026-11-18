"""TEST114 private host diagnostics; procedural transport, never phone acceptance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import native_cycle as cycle
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
from tests.test_native_cycle_client094 import Server, RUN


class RecordingObserver:
    def __init__(self):
        self.rpc_calls = []
        self.terminal_calls = []

    def rpc(self, *args, **kwargs):
        self.rpc_calls.append((args, kwargs))

    def terminal(self, *args, **kwargs):
        self.terminal_calls.append((args, kwargs))


class CampaignDiagnostics114Tests(unittest.TestCase):
    def test_existing_rpc_timings_are_observed_without_changing_the_result_or_requests(self):
        observer = RecordingObserver()
        class TimedClient:
            diagnostics114 = True
            _diagnostics114 = observer
            calls = []
            def call(self, method, params):
                self.calls.append((method, params))
                return RpcReply({'answer': 7}, {'request_start_ns': 10, 'http_start_ns': 20,
                    'http_end_ns': 30, 'decrypt_start_ns': 40, 'decrypt_end_ns': 50,
                    'response_end_ns': 60, 'request_bytes': 12, 'encrypted_response_bytes': 21})
        client = TimedClient()
        result = cycle._call(client, cycle.IRREGULAR_PROTOCOL.query, {'run_id': RUN, 'mode': 'status'})
        self.assertEqual({'answer': 7}, result)
        self.assertEqual(1, len(client.calls))
        self.assertEqual(1, len(observer.rpc_calls), 'existing timing must survive the dedicated client wrapper')

    def test_readonly_observation_runs_once_only_after_real_drain_before_collection(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)/'test-114';base.mkdir()
            server = Server(base)
            server.diagnostics114 = True
            observer = RecordingObserver();server._diagnostics114 = observer
            server.status_queue = [server.status(state='draining', terminal=True, workers_drained=False),
                server.status(state='draining', terminal=True, workers_drained=False), server.status()]
            record = cycle.run_session(server, base, sleep=lambda _:None, notice=lambda _:None)
            self.assertTrue(record['resolved'])
            self.assertFalse(record['cancel_intent'])
            self.assertEqual(1, len(observer.terminal_calls), 'diagnostics must wait for actual drain, then run once')

    def test_fixed_rpc_aggregates_bound_runs_and_store_no_request_bodies(self):
        from necroprobe import campaign_diagnostics114 as diag
        d=diag.DiagnosticCollector114('.')
        times=dict(zip(diag.TIMES,(10,20,30,40,50,60)),request_bytes=12,encrypted_response_bytes=21)
        for index in range(40):
            rid=format(index,'032x')
            for _ in range(300):
                d.rpc(cycle.IRREGULAR_PROTOCOL.query,{'run_id':rid,'mode':'batch','secret':'TOKEN'},
                    RpcReply({'secret':'TOKEN'},times),start=10,end=60)
        ledger={'campaign_id':'c'*32,'revision':1}
        raw=d.seal(ledger);value=json.loads(raw)
        self.assertTrue(diag.valid_sealed(raw,ledger));self.assertLessEqual(len(raw),diag.MAX_BYTES)
        self.assertEqual(32,len(value['runs']));self.assertEqual(8,value['runs_dropped'])
        self.assertNotIn(b'TOKEN',raw)
        bin=value['runs'][-1]['rpc']['images']
        self.assertEqual(300,bin['count']);self.assertEqual(15000,bin['total_ns'])
        self.assertEqual(3000,bin['parts']['decrypt']);self.assertEqual(3600,bin['request_bytes'])

    def test_marker_grammar_drops_private_urls_tokens_and_arbitrary_messages(self):
        from necroprobe import campaign_diagnostics114 as diag
        self.assertEqual({'wall_ms':3723004,'kind':'app_didBecomeActive'},diag.marker('[01:02:03.004] 🔄 app didBecomeActive'))
        self.assertEqual('lan_foreground',diag.marker('[01:02:03.004] 🔼 runner brought forward (foreground for LN prompt)')['kind'])
        for line in ('[01:02:03.004] 🔗 handling loopctrl://start?token=SECRET',
            '[01:02:03.004] 🔄 app didBecomeActive SECRET','[24:00:00.000] 🔄 app didBecomeActive',
            '[01:02:03.004] → activate_app bundle_id=PRIVATE','[01:02:03.004] unknown secret'):
            self.assertIsNone(diag.marker(line))

    def test_readonly_deadline_once_and_primary_failure_diagnostics_are_preserved(self):
        from necroprobe import campaign_diagnostics114 as diag
        now=[0];d=diag.DiagnosticCollector114('.',clock=lambda:now[0])
        failure={'stage':'http','host_timings':{'request_start_ns':1}}
        class Client:
            last_failure=failure
            _rpc_stage='http'
            _rpc_timings={'old':1}
            def __init__(self):
                self.calls=[]
                self.transport=type('T',(),{'last_diagnostic':{'original':True}})()
            def call(self,method,params,timeout=None):
                self.calls.append((method,params,timeout));self.last_failure={'SECRET':'changed'}
                self._rpc_stage='changed';self._rpc_timings={'changed':True};self.transport.last_diagnostic={'changed':True}
                now[0]+=2_000_000_001
                raise ProbeError('rpc_error')
        client=Client();status=dict(terminal=True,workers_drained=True,input_state=0,native_inflight=False)
        d.terminal(client,RUN,dict(status,workers_drained=False));self.assertEqual([],client.calls)
        d.terminal(client,RUN,status);d.terminal(client,RUN,status)
        self.assertEqual(1,len(client.calls));self.assertLessEqual(client.calls[0][2],2)
        self.assertIs(client.last_failure,failure);self.assertEqual('http',client._rpc_stage)
        self.assertEqual({'old':1},client._rpc_timings);self.assertEqual({'original':True},client.transport.last_diagnostic)
        self.assertEqual(['rpc','budget'],d.runs[RUN]['readonly_errors'])

    def test_readonly_projection_retains_only_typed_native_numbers_and_static_markers(self):
        from necroprobe import campaign_diagnostics114 as diag
        d=diag.DiagnosticCollector114('.')
        class Client:
            calls=[]
            def call(self,method,params,timeout=None):
                self.calls.append((method,params))
                if method=='recent_logs':return {'lines':['[01:02:03.004] 🔄 app didEnterBackground',
                    '[01:02:03.004] 🔗 handling PRIVATE?token=SECRET'],'count':2,'total':500,'hint':'SECRET'}
                return {'run_id':RUN,'report':dict(clock_id='d'*32,device_now_ns=70,last_capture_id=92,
                    live_completed_prefix=3,walk_started_ns=10,phase=7,beat_period_ns=0,captures=[],private='SECRET')}
        client=Client();d.terminal(client,RUN,dict(terminal=True,workers_drained=True,input_state=4,native_inflight=False))
        raw=d.seal({'campaign_id':'c'*32,'revision':1});self.assertNotIn(b'SECRET',raw)
        self.assertEqual(2,len(client.calls));self.assertEqual(92,d.runs[RUN]['native']['last_capture_id'])
        self.assertEqual('app_didEnterBackground',d.markers[0]['kind'])
        self.assertTrue(diag.admit_readonly114('recent_logs',{'max_elements':500}))
        for method,params in [('recent_logs',{'max_elements':True}),('recent_logs',{'max_elements':500,'text':'SECRET'}),
            ('necro_native_status',{'run_id':RUN,'keepalive':True}),('tap',{'x':1,'y':2})]:
            self.assertFalse(diag.admit_readonly114(method,params))

    def test_observer_exceptions_do_not_replace_primary_rpc_error_or_cancel_run(self):
        class BrokenObserver:
            def rpc(self,*args,**kwargs):raise RuntimeError('observer')
            def terminal(self,*args,**kwargs):raise RuntimeError('observer')
        class FailingClient:
            diagnostics114=True
            _diagnostics114=BrokenObserver()
            last_failure={'stage':'http'}
            def call(self,*args,**kwargs):raise ProbeError('connection_error')
        client=FailingClient()
        with self.assertRaisesRegex(ProbeError,'connection_error'):
            cycle._call(client,cycle.IRREGULAR_PROTOCOL.query,{'run_id':RUN,'mode':'status'})
        self.assertEqual({'stage':'http'},client.last_failure)
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)/'test-114';base.mkdir();server=Server(base)
            server.diagnostics114=True;server._diagnostics114=BrokenObserver()
            record=cycle.run_session(server,base,notice=lambda _:None)
            self.assertTrue(record['resolved']);self.assertFalse(record['cancel_intent'])
            self.assertIsNone(record['last_error'])

    def test_private_sidecar_is_optional_sealed_and_does_not_change_index_or_nested_run(self):
        from necroprobe import campaign_diagnostics114 as diag
        from necroprobe.trial_evidence099 import bundle
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);last=root/'last.zip'
            with zipfile.ZipFile(last,'w') as archive:archive.writestr('original','bytes')
            raw=last.read_bytes();row=dict(run_id=RUN,archive_name='test-114-'+RUN+'.zip',
                archive_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest())
            ledger=dict(campaign_id='c'*32,revision=1,runs=[row],pending_archive=None)
            old=bundle(root/'old',ledger,last,label='test-114')
            observer=diag.DiagnosticCollector114(root);observer.phase('publish_ack',RUN,1,9)
            extra=observer.seal(ledger);new=bundle(root/'new',ledger,last,label='test-114',diagnostics=extra)
            with zipfile.ZipFile(old) as before,zipfile.ZipFile(new) as after:
                self.assertEqual(before.namelist()+[diag.MEMBER],after.namelist())
                for name in before.namelist():self.assertEqual(before.read(name),after.read(name))
                self.assertEqual(extra,after.read(diag.MEMBER))
            original=new.read_bytes();observer.phase('copy',RUN,10,100)
            self.assertEqual(new,bundle(root/'new',ledger,last,label='test-114',diagnostics=observer.seal(ledger)))
            self.assertEqual(original,new.read_bytes())
            bad=bundle(root/'bad',ledger,last,label='test-114',diagnostics=b'{"token":"SECRET"}')
            with zipfile.ZipFile(bad) as saved:
                value=saved.read(diag.MEMBER)
                self.assertNotIn(b'SECRET',value);self.assertEqual('unavailable',json.loads(value)['status'])

    def test_failed_diagnostic_reads_preserve_real_campaign_publication_and_handoff_qualification(self):
        from necroprobe import campaign099 as campaign, native_walk
        from necroprobe import campaign_diagnostics114 as diag
        from tests.test_campaign099 import CampaignServer
        class DiagnosticFailureServer(CampaignServer):
            diagnostics114=True
            def call(self,method,params,timeout=None):
                if method in ('recent_logs','necro_native_status'):
                    self.calls.append((method,params));self.last_failure={'stage':'http','PRIVATE':'TOKEN'}
                    raise ProbeError('connection_error')
                return super().call(method,params)
        for cases,expected_starts in ((['negative_limit','target'],2),(['unknown','target'],1)):
            with self.subTest(cases=cases),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);base=root/'local/test-114';base.mkdir(parents=True)
                server=DiagnosticFailureServer(base);server.cases=cases
                original=native_walk.device_lock
                with patch('necroprobe.native_cycle.device_lock',lambda path=None:original(path or root/'device.lock')):
                    result=campaign.run(server,root/'output',spool=base,until_target=True,notice=lambda _:None)
                starts=[p['run_id'] for m,p in server.calls if m=='necro_native_start']
                self.assertEqual(expected_starts,len(starts))
                self.assertFalse(any(m=='necro_native_cancel' for m,_ in server.calls))
                self.assertTrue(result['record']['published']);self.assertFalse(result['record']['cancel_intent'])
                self.assertIsNone(result['record']['last_error'])
                self.assertFalse(hasattr(server,'last_failure'))
                with zipfile.ZipFile(result['campaign_archive']) as saved:
                    raw=saved.read(diag.MEMBER);self.assertNotIn(b'TOKEN',raw)
                    self.assertTrue(diag.valid_sealed(raw,result['ledger']))
                    value=json.loads(raw)
                    self.assertEqual(2*expected_starts,sum(r['readonly_attempts'] for r in value['runs']))
                    phases=set().union(*(set(r['phases']) for r in value['runs']))
                    self.assertTrue({'records_collect','images_collect','evidence_verify','inventory',
                        'zip_build','zip_verify','copy','copy_hash','publish_ack'}<=phases)
                    if expected_starts==2:self.assertIn('predecessor',phases)

    def test_sealed_reuse_rejects_duplicate_keys_and_noncanonical_hidden_bytes(self):
        from necroprobe import campaign_diagnostics114 as diag
        ledger={'campaign_id':'c'*32,'revision':1};raw=diag.unavailable(ledger)
        self.assertTrue(diag.valid_sealed(raw,ledger))
        for changed in (b'{"schema":"SECRET",'+raw[1:],raw+b' '):
            self.assertFalse(diag.valid_sealed(changed,ledger),'discarded duplicate/whitespace bytes must not be archived as validated private data')

    def test_existing_campaign_symlink_is_rejected_before_any_zip_read(self):
        from necroprobe import campaign_diagnostics114 as diag
        from necroprobe.trial_evidence099 import bundle
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'output/runtime';output.mkdir(parents=True)
            ledger=dict(campaign_id='c'*32,revision=1,runs=[],pending_archive=None)
            outside=root/'outside.zip';raw=diag.unavailable(ledger)
            with zipfile.ZipFile(outside,'w') as archive:
                archive.writestr('campaign-index.json',cycle.canonical(ledger));archive.writestr(diag.MEMBER,raw)
            before=outside.read_bytes();link=output/('test-114-campaign-'+ledger['campaign_id']+'-r1.zip')
            link.symlink_to(outside)
            real=zipfile.ZipFile
            with patch('necroprobe.trial_evidence099.zipfile.ZipFile',wraps=real) as opened:
                with self.assertRaisesRegex(ProbeError,'cycle_local_symlink'):
                    bundle(root/'output',ledger,None,label='test-114',diagnostics=raw)
                self.assertEqual(0,opened.call_count,'an optional sidecar must not dereference a forbidden artifact')
            self.assertEqual(before,outside.read_bytes());self.assertTrue(link.is_symlink())

    def test_optional_clock_failure_preserves_primary_error_and_reports_missing_timing(self):
        from necroprobe import campaign_diagnostics114 as diag
        d=diag.DiagnosticCollector114('.')
        client=type('Client',(),{'diagnostics114':True,'_diagnostics114':d})()
        caught=None
        with patch.object(diag.time,'monotonic_ns',side_effect=RuntimeError('clock')):
            try:
                with diag.span(client,'copy',RUN):raise ProbeError('connection_error')
            except Exception as failure:caught=failure
        self.assertIsInstance(caught,ProbeError,'optional clock must not mask primary error')
        self.assertEqual('connection_error',caught.code)
        value=json.loads(d.seal({'campaign_id':'c'*32,'revision':1}))
        self.assertIn('clock',value['errors'])
        self.assertNotIn('copy',d.runs.get(RUN,{}).get('phases',{}),'invalid time must not be recorded as a successful zero duration')
