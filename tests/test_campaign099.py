"""TEST099 finite native runs join only at verified, published trial boundaries.

The baseline fallback invokes the old single publication path so missing
campaign behavior is an assertion failure, not an import or compile failure.
Fixtures exercise real journal/collection/ZIP publication, not game pixels.
"""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import cycle_publication as publication
from necroprobe import native_cycle as cycle
from necroprobe import native_walk
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_native_cycle_client094 import companion, png
from test_protocol import KEY, TOK, sealed_reply


class LegacyCampaign:
    MAX_RUNS = 128

    @staticmethod
    def run(client, destination, *, spool, until_target=False, recovery_only=False,
            cancelled=lambda:False, notice=print):
        record, archive = publication.run(client, destination, spool=spool,
            recovery_only=recovery_only, cancelled=cancelled, notice=notice)
        return dict(record=record, archive=archive, campaign_archive=None,
                    ledger={'runs':[]}, stop_reason='single')


if importlib.util.find_spec('necroprobe.campaign099') is not None:
    from necroprobe import campaign099 as campaign
else:
    campaign = LegacyCampaign
if importlib.util.find_spec('necroprobe.trial_evidence099') is not None:
    from necroprobe.trial_evidence099 import TrialClient099
else:
    TrialClient099 = cycle.CycleClient


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def proof(kind='none'):
    return dict(schema='ngg2-trial-handoff-v1', kind=kind, allowed=kind!='none',
        reason=14 if kind!='none' else 1, qualified_ns=130 if kind!='none' else 0,
        source_capture_id=8 if kind=='clear_search_limit' else 7 if kind!='none' else 0,
        source_prefix=4 if kind!='none' else 0, pause_capture_id=9 if kind!='none' else 0,
        completed_prefix=5 if kind!='none' else 0)


def native_model(run_id, kind='negative_limit', fault=None):
    raw_png = png()
    prior_negative = kind == 'clear_search_limit_after_negative'
    clear = kind.startswith('clear_search_limit')
    result = 'negative' if kind=='negative_limit' or prior_negative else 'unknown' if clear else kind
    state = companion()
    assessed = not clear or prior_negative
    state.update(level_id=1, job_id=1 if assessed else 0, capture_id=7 if assessed else 0,
        capture_start_ns=80 if assessed else 0, prefix=4 if assessed else 0,
        worker_started_ns=85 if assessed else 0, assessment_ns=95 if assessed else 0,
        deadline_ns=110 if assessed else 0, durable_ns=125 if assessed else 0,
        pause_source_capture_id=8 if assessed else 0, pause_capture_id=9 if assessed else 0,
        completed_shops=4 if kind=='negative_limit' else 1 if assessed else 0,
        outcome=result, coverage='complete' if result=='negative' else 'incomplete',
        full_seen=assessed, candidate_latched=result in ('target','candidate'))
    handoff = proof('clear_search_limit' if clear else kind if kind=='negative_limit' else 'none')
    if prior_negative:state.update(level_id=2, prefix=1, durable_ns=96, outcome_ns=98)
    controller = dict(terminal=1, phase=7, paused=1, input_state=0, current_command_id=0,
        last_completed_id=5, last_capture_id=9, started_ns=1, ended_ns=140,
        reason=14 if handoff['allowed'] else 17 if result=='unknown' else 1,
        restarts=12 if clear else 3, moves=0 if not assessed else 8,
        inputs=0 if not assessed else 12, x=0, y=0, handoff=handoff,
        events=[dict(id=5, kind=2, outcome=2, reason=0, source_capture_id=8,
            source_start_ns=100, begin_ns=110, end_ns=115, observed_capture_id=9)])
    assessment = dict(status='ok', outcome=result, coverage=state['coverage']) if assessed else None
    checkpoint = dict(cycle=copy.deepcopy(state), controller=copy.deepcopy(controller),
        assessment=assessment, assessment_adopted=assessed, raw_sha256='c'*64)
    terminal = dict(cycle=copy.deepcopy(state), controller=controller,
        assessment=assessment, assessment_adopted=assessed)
    if prior_negative:
        checkpoint['cycle']['level_id']=1
        terminal.update(assessment=None,assessment_adopted=False)
    if fault:
        fault(terminal, checkpoint)
    records = {0:cycle.canonical(dict(schema='ngg2-cycle-spool-v1', run_id=run_id,
                                    owner_sha256='d'*64))}
    chain = []
    if assessed: chain.append(('checkpoint', checkpoint))
    chain.append(('terminal',terminal))
    previous = None
    kinds = [(0,'session',0)]
    for sequence,(name,payload) in enumerate(chain,1):
        body = dict(schema='ngg2-cycle-record-v1', run_id=run_id, sequence=sequence,
                    kind=name, cycle=state['completed_shops'], previous=previous, payload=payload)
        records[sequence] = cycle.canonical(body)
        previous = sha(records[sequence]);kinds.append((sequence,name,state['completed_shops']))
    for sequence,capture,start,prefix in ((513,7,80,4),(514,8,100,4),(515,9,120,5)):
        if prior_negative and capture==7:prefix=1
        metadata = dict(capture_id=capture, capture_start_ns=start, capture_end_ns=start+1,
            completed_prefix_start=prefix, completed_prefix_end=prefix, stable_prefix=True,
            inflight_start=False, inflight_end=False, generation=1, pixel_width=896, pixel_height=414)
        if fault and getattr(fault,'metadata',None):fault.metadata(capture,metadata)
        records[sequence] = cycle.canonical(dict(schema='ngg2-cycle-frame-v1', run_id=run_id,
            capture_id=capture, raw_sha256='c'*64, raw_bytes=896*414*4, metadata=metadata))
        kinds.append((sequence,'frame',0))
    export_id = hashlib.sha256(run_id.encode()).hexdigest()[:32]
    images=[dict(name='capture-'+str(c).zfill(6)+'.png',capture_id=c,bytes=len(raw_png),
        sha256=sha(raw_png),raw_sha256='c'*64,width=896,height=414) for c in (7,8,9)]
    manifest = dict(schema='ngg2-cycle-manifest-v1',run_id=run_id,profile=cycle.PROFILE,
        export_id=export_id,complete=True,interrupted=False,terminal=True,workers_drained=True,
        input_state=0,native_inflight=False,ui_frozen=False,images=images,
        records=[dict(sequence=s,kind=k,cycle=n,bytes=len(records[s]),sha256=sha(records[s]))
                 for s,k,n in kinds],diagnostics=[],total_bytes=3*len(raw_png)+sum(map(len,records.values())),
        chunk_bytes=cycle.CHUNK_BYTES)
    return dict(image=raw_png,records=records,manifest=manifest,terminal=terminal,cycle=state,published=False)


class CampaignServer:
    def __init__(self, base, cases=('negative_limit','target'), fault=None):
        self.base=base;self.cases=list(cases);self.fault=fault;self.models={};self.calls=[]
        self.on_publish=None;self.supported=True;self.fail_export=False;self.fail_start=False;self.fail_ack=False

    def check_schema(self):
        self.calls.append(('schema',{}))
        if not self.supported:raise ProbeError('trial_support_missing')
        return {}

    @staticmethod
    def wrap(run_id,mode,payload):
        return dict(schema=cycle.SCHEMA,run_id=run_id,profile=cycle.PROFILE,mode=mode,payload=payload)

    def call(self,method,params):
        self.calls.append((method,copy.deepcopy(params)))
        run_id=params['run_id']
        if method=='necro_native_start':
            self.assert_start_intent(run_id)
            selected=self.cases.pop(0) if self.cases else 'target'
            self.models[run_id]=native_model(run_id,selected,self.fault)
            if self.fail_start:
                self.fail_start=False;raise ProbeError('connection_error')
            return dict(run_id=run_id,profile=cycle.PROFILE,state='accepted',api_version=cycle.API_VERSION,report={})
        if method=='necro_native_cancel':
            return dict(run_id=run_id,profile=cycle.PROFILE,state='stopped',api_version=cycle.API_VERSION,report={})
        mode=params['mode']
        if mode=='prepare':return self.wrap(run_id,mode,dict(ready=True,notification_authorization='authorized',
            recovery_scan='ready',unpublished_run_ids=[],reason='none'))
        model=self.models[run_id];manifest=model['manifest']
        if mode=='status':return self.wrap(run_id,mode,dict(state='completed',terminal=True,
            workers_drained=True,input_state=manifest['input_state'],ui_frozen=manifest['ui_frozen'],
            native_inflight=False,cycle=model['cycle'],notification=dict(authorization='authorized',state='requested')))
        if mode=='manifest':
            raw=cycle.canonical(manifest)
            return self.wrap(run_id,mode,dict(export_id=manifest['export_id'],manifest_sha256=sha(raw),manifest_json=raw.decode()))
        if mode in ('record','chunk','batch'):
            if mode=='batch' and self.fail_export:
                self.fail_export=False;raise ProbeError('connection_error')
            key='sequence' if mode=='record' else 'capture_id'
            data=model['records'][params[key]] if mode=='record' else model['image']
            offset=params['offset'];parts=[]
            for _ in range(params.get('count',1)):
                raw=data[offset:offset+cycle.CHUNK_BYTES]
                import base64
                parts.append(dict(export_id=manifest['export_id'],**{key:params[key]},offset=offset,
                    total_bytes=len(data),sha256=sha(data),data_base64=base64.b64encode(raw).decode(),
                    next_offset=offset+len(raw),eof=offset+len(raw)==len(data)))
                offset+=len(raw)
                if offset==len(data):break
            return self.wrap(run_id,mode,dict(export_id=manifest['export_id'],chunks=parts) if mode=='batch' else parts[0])
        if mode=='published':
            if self.fail_ack:
                self.fail_ack=False;raise ProbeError('connection_error')
            active=cycle.load_journal(self.base)
            assert active['resolved'] and active['run_id']==run_id
            model['published']=True
            if self.on_publish:self.on_publish(run_id)
            return self.wrap(run_id,mode,dict(accepted=True,export_id=manifest['export_id'],
                manifest_sha256=params['manifest_sha256'],archive_sha256=params['archive_sha256'],receipt_sha256='f'*64))
        raise AssertionError(mode)

    def assert_start_intent(self,run_id):
        active=cycle.load_journal(self.base)
        assert active['run_id']==run_id and active['start_intent']


class PowerLoss(BaseException):
    pass


class Campaign099Tests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='campaign099-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.base=self.root/'local'/'test-099';self.base.mkdir(parents=True)
        self.destination=self.root/'mounted';self.destination.mkdir();self.notices=[]
        self.server=CampaignServer(self.base)

    def invoke(self,**kwargs):
        original=native_walk.device_lock
        def locks(path=None):return original(path or self.root/'device.lock')
        with patch('necroprobe.native_cycle.device_lock',locks):
            return campaign.run(self.server,self.destination,spool=self.base,notice=self.notices.append,**kwargs)

    def starts(self):
        return [p['run_id'] for m,p in self.server.calls if m=='necro_native_start']

    def test_negative_handoff_publishes_before_new_uuid_and_stops_at_target(self):
        result=self.invoke(until_target=True)
        self.assertEqual(2,len(result.get('ledger',{}).get('runs',[])), 'one explicit start must join proved negative to target')
        self.assertEqual('target',result.get('stop_reason'))
        self.assertEqual(2,len(set(self.starts())))
        first=self.starts()[0];calls=self.server.calls
        first_ack=next(i for i,(m,p) in enumerate(calls) if p.get('mode')=='published' and p['run_id']==first)
        second_start=next(i for i,(m,p) in enumerate(calls) if m=='necro_native_start' and p['run_id']!=first)
        self.assertLess(first_ack,second_start)

    def test_clean_search_limit_default_unknown_is_distinct_from_unknown_assessment(self):
        self.server.cases=['clear_search_limit','target']
        result=self.invoke(until_target=True)
        self.assertEqual('target',result.get('stop_reason'))
        self.assertEqual(2,len(self.starts()))
        self.assertEqual('unassessed',result.get('ledger',{}).get('runs',[{}])[0].get('outcome'))

    def test_clean_search_after_earlier_resolved_negative_uses_current_handoff(self):
        self.server.cases=['clear_search_limit_after_negative','target']
        result=self.invoke(until_target=True)
        self.assertEqual('target',result.get('stop_reason'))
        self.assertEqual(2,len(self.starts()))

    def test_collection_interruption_recovers_same_uuid_without_new_start(self):
        self.server.cases=['target'];self.server.fail_export=True
        first=self.invoke(until_target=True)
        original=cycle.load_journal(self.base)['run_id']
        self.assertEqual(1,len(self.starts()))
        self.assertIsNone(first.get('archive'))
        second=self.invoke(recovery_only=True)
        self.assertEqual([original],self.starts())
        self.assertIsNotNone(second.get('campaign_archive'))
        self.assertTrue(cycle.load_journal(self.base)['published'])

    def test_uncertain_start_response_is_only_recovered_under_original_uuid(self):
        self.server.cases=['target'];self.server.fail_start=True
        first=self.invoke(until_target=True)
        original=cycle.load_journal(self.base)['run_id']
        self.assertIsNone(first.get('archive'))
        second=self.invoke(until_target=True)
        self.assertEqual([original],self.starts())
        self.assertEqual('target',second.get('stop_reason'))

    def test_target_candidate_and_real_unknown_never_start_another_run(self):
        for kind in ('target','candidate','unknown'):
            with self.subTest(kind=kind):
                self.server.cases=[kind]
                result=self.invoke(until_target=True)
                self.assertEqual(kind,result.get('stop_reason'))
                self.assertEqual(1,len(result.get('ledger',{}).get('runs',[])))
                self.server.calls.clear()

    def test_missing_malformed_or_denied_handoff_does_not_repeat_limit(self):
        faults=(lambda t,c:t['controller'].pop('handoff'),
                lambda t,c:t['controller']['handoff'].update(allowed=False),
                lambda t,c:t['controller']['handoff'].update(extra=True),
                lambda t,c:t['controller']['handoff'].update(source_prefix=True))
        for fault in faults:
            with self.subTest(fault=fault):
                self.server.fault=fault;self.server.cases=['negative_limit']
                result=self.invoke(until_target=True)
                self.assertEqual(1,len(self.starts()))
                self.assertIn(result.get('stop_reason'),('handoff_unavailable','handoff_invalid'))
                self.server.calls.clear()

    def test_controller_fault_or_unadopted_negative_does_not_restart_campaign(self):
        for fault in (lambda t,c:t['controller'].update(reason=17),
                      lambda t,c:t.update(assessment_adopted=False),
                      lambda t,c:t['cycle'].update(durable_ns=0)):
            with self.subTest(fault=fault):
                self.server.fault=fault;self.server.cases=['negative_limit']
                result=self.invoke(until_target=True)
                self.assertEqual(1,len(self.starts()))
                self.assertNotEqual('handoff',result.get('stop_reason'))
                self.server.calls.clear()

    def test_handoff_requires_matching_registered_stable_source_and_pause_prefix(self):
        def bad(t,c):pass
        bad.metadata=lambda capture,m:m.update(completed_prefix_end=6) if capture==7 else None
        self.server.fault=bad
        result=self.invoke(until_target=True)
        self.assertEqual(1,len(self.starts()))
        self.assertEqual('handoff_invalid',result.get('stop_reason'))

    def test_handoff_denies_referenced_frame_without_manifest_image(self):
        original=native_model
        for capture in (7,8,9):
            with self.subTest(capture=capture):
                self.server.calls.clear()
                def omit(*args,**kwargs):
                    model=original(*args,**kwargs);manifest=model['manifest']
                    removed=next(item for item in manifest['images'] if item['capture_id']==capture)
                    manifest['images']=[item for item in manifest['images'] if item is not removed]
                    manifest['total_bytes']-=removed['bytes']
                    return model
                self.server.cases=['negative_limit','target']
                with patch(__name__+'.native_model',omit):result=self.invoke(until_target=True)
                self.assertEqual(1,len(self.starts()),'registered metadata alone cannot authorize the next run')
                self.assertEqual('handoff_invalid',result.get('stop_reason'))
                self.server.calls.clear()

    def test_handoff_denies_pause_command_source_from_other_generation(self):
        def bad(t,c):pass
        bad.metadata=lambda capture,m:m.update(generation=2) if capture==8 else None
        self.server.fault=bad
        result=self.invoke(until_target=True)
        self.assertEqual(1,len(self.starts()),'the acknowledged PAUSE source must share the handoff generation')
        self.assertEqual('handoff_invalid',result.get('stop_reason'))

    def test_completed_run_before_index_crash_is_reconciled_before_next_start(self):
        original=publication.run;raised=[False]
        def crash(*args,**kwargs):
            value=original(*args,**kwargs)
            if not raised[0] and value[1] is not None:
                raised[0]=True;raise PowerLoss()
            return value
        with patch.object(publication,'run',crash),self.assertRaises(PowerLoss):self.invoke(until_target=True)
        original_id=cycle.load_journal(self.base)['run_id']
        self.assertTrue(cycle.load_journal(self.base)['published'])
        result=self.invoke(until_target=True)
        self.assertEqual(2,len(result.get('ledger',{}).get('runs',[])))
        self.assertEqual(original_id,result['ledger']['runs'][0]['run_id'])
        self.assertEqual(2,len(self.starts()))

    def test_next_intent_crash_never_skips_or_restarts_the_previous_uuid(self):
        save=getattr(campaign,'_save',lambda *_:None);raised=[False]
        def crash(base,ledger):
            save(base,ledger)
            if not raised[0] and (ledger.get('intent') or {}).get('kind')=='handoff':
                raised[0]=True;raise PowerLoss()
        with patch.object(campaign,'_save',crash,create=True),self.assertRaises(PowerLoss):self.invoke(until_target=True)
        self.assertEqual(1,len(self.starts()))
        result=self.invoke(until_target=True)
        self.assertEqual('target',result.get('stop_reason'))
        self.assertEqual(2,len(set(self.starts())))

    def test_trial_run_limit_stops_before_an_additional_native_start(self):
        self.server.cases=['negative_limit','negative_limit','target']
        with patch.object(campaign,'MAX_RUNS',2):
            result=self.invoke(until_target=True)
        self.assertEqual('campaign_run_limit',result.get('stop_reason'))
        self.assertEqual(2,len(self.starts()))

    def test_prepared_next_journal_cannot_skip_revalidation_of_prior_proof(self):
        original=publication.run;raised=[False]
        def crash(*args,**kwargs):
            active=cycle.load_journal(self.base)
            if active is not None and active['published'] and not kwargs.get('recovery_only') and not raised[0]:
                raised[0]=True
                cycle._journal(self.base,cycle.fresh_record('e'*32))
                raise PowerLoss()
            return original(*args,**kwargs)
        with patch.object(publication,'run',crash),self.assertRaises(PowerLoss):self.invoke(until_target=True)
        old=self.starts()[0]
        manifest=cycle.json_object((self.base/('cycle-'+old)/'native-manifest.json').read_bytes(),cycle.MAX_MANIFEST)
        terminal=next(item for item in manifest['records'] if item['kind']=='terminal')
        path=self.base/('cycle-'+old)/'records'/cycle.record_name(terminal)
        path.write_bytes(path.read_bytes()+b' ')
        rejected=None
        try:self.invoke(until_target=True)
        except ProbeError as error:rejected=error.code
        self.assertIsNotNone(rejected,'a prepared next UUID is not evidence that its predecessor was safe')
        self.assertEqual([old],self.starts())

    def test_publication_ack_failure_returns_incomplete_fault_bundle_and_same_id_recovery(self):
        self.server.fail_ack=True
        escaped=None;result=None
        try:result=self.invoke(until_target=True)
        except ProbeError as error:escaped=error.code
        self.assertIsNone(escaped,'an ACK fault must preserve an attachable verified current-run ZIP')
        self.assertEqual(1,len(self.starts()))
        self.assertEqual('pending',result['ledger']['state'])
        self.assertFalse(result['ledger']['complete'])
        self.assertTrue(result['ledger']['pending_publication'])
        descriptor=result['ledger']['pending_archive']
        with zipfile.ZipFile(result['campaign_archive']) as returned:
            index=json.loads(returned.read('campaign-index.json'))
            self.assertEqual(descriptor,index['pending_archive'])
            self.assertEqual(descriptor['archive_sha256'],sha(returned.read('last-run/'+descriptor['archive_name'])))
        old=self.starts()[0]
        recovered=self.invoke(recovery_only=True)
        self.assertEqual([old],self.starts())
        self.assertTrue(recovered['ledger']['complete'])
        self.assertFalse(recovered['ledger']['pending_publication'])
        self.assertEqual('recovery',recovered['stop_reason'])

    def test_cancel_after_publication_keeps_last_zip_and_issues_no_next_start(self):
        cancelled=[False];self.server.on_publish=lambda _:cancelled.__setitem__(0,True)
        result=self.invoke(until_target=True,cancelled=lambda:cancelled[0])
        self.assertEqual('cancelled',result.get('stop_reason'))
        self.assertEqual(1,len(self.starts()))
        self.assertIsNotNone(result.get('campaign_archive'))

    def test_recovery_only_restores_last_bundle_without_start_or_new_campaign(self):
        self.server.cases=['target'];first=self.invoke(until_target=True);self.server.calls.clear()
        second=self.invoke(recovery_only=True)
        self.assertEqual([],self.starts())
        self.assertEqual(first.get('ledger',{}).get('campaign_id'),second.get('ledger',{}).get('campaign_id'))
        self.assertIsNotNone(second.get('campaign_archive'))

    def test_indexed_published_run_clears_pending_markers_after_recovery(self):
        self.server.cases=['negative_limit'];first=self.invoke()
        run_id=self.starts()[0]
        receipt=self.base.parent/('.'+self.base.name+'-publication')/(run_id+'.receipt.json')
        original=receipt.read_bytes();damaged=json.loads(original)
        damaged['receipt_sha256']='invalid';receipt.write_bytes(cycle.canonical(damaged))
        pending=self.invoke(recovery_only=True)
        self.assertEqual('pending',pending['ledger']['state'])
        self.assertEqual(run_id,pending['ledger']['pending_run_id'])
        self.assertTrue(pending['ledger']['pending_publication'])
        self.assertIsNotNone(pending['ledger']['pending_archive'])
        receipt.write_bytes(original)
        recovered=self.invoke(recovery_only=True)
        self.assertEqual([run_id],self.starts(),'recovery must never start or continue the campaign')
        self.assertEqual(first['ledger']['campaign_id'],recovered['ledger']['campaign_id'])
        self.assertEqual('stopped',recovered['ledger']['state'])
        self.assertTrue(recovered['ledger']['complete'])
        self.assertIsNone(recovered['ledger']['pending_run_id'])
        self.assertIsNone(recovered['ledger']['pending_archive'])
        self.assertFalse(recovered['ledger']['pending_publication'])
        self.assertEqual('recovery',recovered['stop_reason'])

    def test_single_mode_returns_a_checked_index_and_last_full_run_zip(self):
        self.server.cases=['negative_limit'];result=self.invoke()
        bundle=result.get('campaign_archive');self.assertIsNotNone(bundle,'single test must return the same diagnostic package format')
        with zipfile.ZipFile(bundle) as saved:
            self.assertIsNone(saved.testzip());names=saved.namelist()
            self.assertEqual(2,len(names));self.assertIn('campaign-index.json',names)
            index=json.loads(saved.read('campaign-index.json'));last=index['runs'][-1]
            data=saved.read('last-run/'+last['archive_name'])
            self.assertEqual(last['archive_sha256'],sha(data))
            with zipfile.ZipFile(io.BytesIO(data)) as nested:self.assertIsNone(nested.testzip())

    def test_unsupported_trial_feature_stops_before_any_native_start(self):
        self.server.supported=False
        result=self.invoke(until_target=True)
        self.assertEqual([],self.starts())
        self.assertIn(result.get('stop_reason'),('trial_support_missing','pending'))

    def test_trial_client_reads_feature_every_preflight_and_rejects_old_or_malformed(self):
        class Transport(HttpTransport):
            def __init__(self):super().__init__();self.calls=[];self.payload=None
            def schema(self,_):return cycle.canonical(dict(server_version=cycle.API_VERSION,
                protocol_version=1,capability_tags=[cycle.CAPABILITY]))
            def _exchange(self,method,path,body,timeout,limit):
                self.calls.append(body)
                if self.payload is None:return sealed_reply(body,result=dict(code=-32602,message='unsupported'),rpc_error=True)
                result=dict(schema=cycle.SCHEMA,run_id=self.run_id,profile=cycle.PROFILE,
                    mode='trial_support',payload=self.payload)
                return sealed_reply(body,result=result)
        transport=Transport()
        with OwnedRpcTimer() as timer:
            client=TrialClient099(transport,KEY,TOK,crypto=Crypto(native=True),deadline_owner=timer)
            error=None
            try:client.check_schema()
            except ProbeError as exc:error=exc.code
            self.assertEqual('trial_support_missing',error,'old API version alone must not admit the new trial')
            transport.run_id=getattr(client,'trial_probe_id','a'*32)
            transport.payload=dict(stop_detail_schema='ngg2-stop-detail-v1',handoff_schema='ngg2-trial-handoff-v1',maximum_run_ids=128,pin_limit=24)
            client.check_schema();client.check_schema()
            self.assertEqual(3,len(transport.calls))
            transport.payload['maximum_run_ids']=True
            with self.assertRaises(ProbeError):client.check_schema()


if __name__=='__main__':unittest.main()
