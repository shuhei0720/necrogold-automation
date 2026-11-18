"""TEST116 closed wire, durable client, and post-stop publication contracts.

All server bytes and clocks are procedural transport fixtures; no phone UI
or unrecorded shop outcome is claimed. Before implementation the wire tests
exercise TEST115's actual client and status parser as a runnable semantic Red.
"""
import copy
import hashlib
import importlib.util
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_cycle as cycle
from necroprobe.crypto import Crypto
from necroprobe.test115 import DeviceClient115
from necroprobe.validation import ProbeError
from tests.test_protocol import KEY, TOK
from test_native_irregular_client110 import IrregularServer, normal_model, replace_fixture_record
from test_restart_yield112 import restart_yield_model
from necroprobe.rpc_diagnostics import RemoteRpcError


ROOT = 'a' * 32
SECOND = 'b' * 32
CAPABILITY = 'necrogold_native_continuous_campaign_v1'
SPEC = cycle.IRREGULAR_PROTOCOL


def subject_client():
    if importlib.util.find_spec('necroprobe.test116') is None:
        return DeviceClient115
    from necroprobe.test116 import DeviceClient116
    return DeviceClient116


def parse_root(value, root=ROOT):
    if importlib.util.find_spec('necroprobe.campaign116') is None:
        return cycle.status(value, root, protocol_spec=SPEC)
    from necroprobe.campaign116 import status_reply
    return status_reply(value, root)


def status_wire(*, terminal=False, second=False):
    first = dict(index=0, run_id=ROOT, predecessor_id=None,
        state='completed' if second else ('stopped' if terminal else 'running'),
        escrow_sealed=second or terminal, escrow_sha256='c'*64 if second or terminal else None,
        terminal_reason=14 if second else (17 if terminal else 0))
    children = [first]
    if second:
        children.append(dict(index=1, run_id=SECOND, predecessor_id=ROOT,
            state='stopped' if terminal else 'running', escrow_sealed=terminal,
            escrow_sha256='d'*64 if terminal else None, terminal_reason=17 if terminal else 0))
    payload = dict(schema='ngg2-continuous-campaign-v1',root_id=ROOT,
        state='stopped' if terminal else 'running',active_run_id=SECOND if second else ROOT,
        terminal=terminal,workers_drained=terminal,input_state=0,native_inflight=False,
        ui_frozen=False,stop_reason='unknown' if terminal else 'none',child_limit=16,
        deadline_ns=2_880_000_000_001,children=children)
    return dict(schema=SPEC.schema,run_id=ROOT,profile=SPEC.profile,
        mode='campaign_status',payload=payload)


class ContinuousClientWire116Tests(unittest.TestCase):
    def client(self):
        return subject_client()(lambda *_: b'',KEY,TOK,crypto=Crypto(native=False))

    def admitted(self, method, params, *, client=None):
        try:
            (client or self.client())._validate(method,params)
            return True
        except ProbeError:
            return False

    def parsed(self, value):
        try:
            return parse_root(value)
        except ProbeError:
            return None

    def test_continuous_start_is_explicit_without_the_old_yield_flag(self):
        client=self.client()
        self.assertIs(False,client.yield_after_restart,
            'continuous mode cannot inherit the old collection-PAUSE flag')
        self.assertIn(CAPABILITY,client.required_capabilities)
        self.assertTrue(self.admitted('necro_native_start',dict(run_id=ROOT,
            profile=SPEC.profile,continuous_campaign=True),client=client),
            'the dedicated continuous client must admit its closed start shape')

    def test_root_status_has_only_the_root_identity_and_typed_keepalive(self):
        self.assertTrue(self.admitted(SPEC.query,dict(run_id=ROOT,
            mode='campaign_status',keepalive=True)),
            'the dedicated root query must work while child ownership changes')
        self.assertTrue(self.admitted(SPEC.query,dict(run_id=ROOT,
            mode='campaign_status',keepalive=False)))
        for keepalive in (0,1,None,'true'):
            self.assertFalse(self.admitted(SPEC.query,dict(run_id=ROOT,
                mode='campaign_status',keepalive=keepalive)))
        self.assertFalse(self.admitted(SPEC.query,dict(run_id=ROOT,
            mode='campaign_status',keepalive=True,child_id=SECOND)))

    def test_start_refuses_false_untyped_flags_extra_fields_and_other_profiles(self):
        for flag in (False,0,1,None,'true'):
            self.assertFalse(self.admitted('necro_native_start',dict(run_id=ROOT,
                profile=SPEC.profile,continuous_campaign=flag)))
        for extra in ({'yield_after_restart':True},{'root_id':ROOT},{'child_id':SECOND}):
            self.assertFalse(self.admitted('necro_native_start',dict(run_id=ROOT,
                profile=SPEC.profile,continuous_campaign=True,**extra)))
        self.assertFalse(self.admitted('necro_native_start',dict(run_id=ROOT,
            profile=cycle.STANDARD_PROTOCOL.profile,continuous_campaign=True)))

    def test_old_client_keeps_rejecting_new_flags_and_new_query(self):
        old=DeviceClient115(lambda *_: b'',KEY,TOK,crypto=Crypto(native=False))
        self.assertFalse(self.admitted('necro_native_start',dict(run_id=ROOT,
            profile=SPEC.profile,continuous_campaign=True),client=old))
        self.assertFalse(self.admitted(SPEC.query,dict(run_id=ROOT,
            mode='campaign_status',keepalive=True),client=old))

    def test_running_and_stopped_root_statuses_keep_all_ordered_children(self):
        for terminal in (False,True):
            for second in (False,True):
                value=status_wire(terminal=terminal,second=second)
                parsed=self.parsed(value)
                self.assertIsNotNone(parsed,
                    'the new mode must parse its own schema rather than old cycle status')
                self.assertEqual(value['payload'],parsed)

    def test_root_status_rejects_duplicate_out_of_order_missing_and_mistyped_children(self):
        modifications = (
            lambda p:p.update(stop_reason=[]),
            lambda p:p['children'][0].update(state=[]),
            lambda p:p.update(state='running'),
            lambda p:p.update(root_id=SECOND),
            lambda p:p.update(active_run_id=ROOT),
            lambda p:p.update(deadline_ns=True),
            lambda p:p.update(child_limit=True),
            lambda p:p.update(children=[]),
            lambda p:p['children'].append(copy.deepcopy(p['children'][0])),
            lambda p:p['children'][1].update(index=0),
            lambda p:p['children'][1].update(index=True),
            lambda p:p['children'][1].update(predecessor_id=SECOND),
            lambda p:p['children'][1].update(run_id=ROOT),
            lambda p:p['children'][0].update(escrow_sha256=None),
            lambda p:p['children'][0].update(escrow_sealed=1),
            lambda p:p['children'][0].update(untrusted='extra'),
        )
        for change in modifications:
            value=status_wire(terminal=True,second=True);change(value['payload'])
            self.assertIsNone(self.parsed(value))


def campaign_model(run_id, root, index, predecessor, successor):
    from necroprobe import campaign116 as campaign
    model=(restart_yield_model(run_id,data=False) if successor is not None else normal_model(run_id,'unknown'))
    header=json.loads(model['records'][0])
    header['provenance'].pop('yield_after_restart',None)
    header['provenance'].setdefault('clock_id','f'*32)
    header['provenance']['continuous_campaign']=dict(schema='ngg2-continuous-child-v1',
        root_id=root,index=index,predecessor_id=predecessor,root_started_ns=1,
        root_deadline_ns=1+campaign.ROOT_DURATION_NS)
    replace_fixture_record(model,0,header)
    rows=model['manifest']['records'];terminal=next(r for r in rows if r['kind']=='terminal')
    if successor is not None:
        body=json.loads(model['records'][terminal['sequence']])
        body['payload']['controller'].update(reason=14,paused=0,last_completed_id=6,last_capture_id=21)
        body['payload']['controller']['events']=[e for e in body['payload']['controller']['events'] if e['id']<=6]
        body['payload']['controller']['handoff'].update(kind='none',allowed=False)
        replace_fixture_record(model,terminal['sequence'],body)
    sequence=terminal['sequence']+1
    controller=dict.fromkeys(campaign.CONTROLLER_NUMBERS,0)
    controller.update(abi_version=1,enabled=True,successor_floor=index>0,
        qualified=successor is not None,root_deadline_ns=1+campaign.ROOT_DURATION_NS)
    if successor is not None:
        controller.update(qualified_ns=225,parent_deadline_ns=350,old_job_id=1,restart_command_id=6,
            new_floor_capture_id=20,source_capture_id=21,source_start_ns=220,source_prefix=6)
    terminal_body=json.loads(model['records'][terminal['sequence']])
    terminal_body['payload']['controller']['continuous_campaign']=copy.deepcopy(controller)
    replace_fixture_record(model,terminal['sequence'],terminal_body)
    seal=dict(schema='ngg2-cycle-record-v1',run_id=run_id,sequence=sequence,kind='continuation_seal',
        cycle=0,previous=terminal['sha256'],payload=dict(schema='ngg2-continuation-seal-v1',
            root_id=root,run_id=run_id,index=index,predecessor_id=predecessor,next_run_id=successor,
            terminal_sha256=terminal['sha256'],frames_sha256=frame_digest(model),controller=controller,
            clock_id=header['provenance']['clock_id'],session_sha256=next(r['sha256'] for r in rows if r['kind']=='session')))
    model['records'][sequence]=cycle.canonical(seal)
    position=next(i for i,r in enumerate(rows) if r['kind']=='frame')
    rows.insert(position,dict(sequence=sequence,kind='continuation_seal',cycle=0,
        bytes=len(model['records'][sequence]),sha256=hashlib.sha256(model['records'][sequence]).hexdigest()))
    model['manifest']['total_bytes']=len(model['manifest']['images'])*len(model['image'])+sum(map(len,model['records'].values()))
    return model


def frame_digest(model):
    values=[]
    for row in model['manifest']['records']:
        if row['kind']=='frame':
            body=json.loads(model['records'][row['sequence']])
            values.append(dict(capture_id=body['capture_id'],raw_sha256=body['raw_sha256'],
                metadata_sha256=row['sha256'],bytes=896*414*4))
    values.sort(key=lambda r:r['capture_id'])
    return hashlib.sha256(cycle.canonical(values)).hexdigest()


def change_snapshot(model, changes):
    seal=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
    terminal=next(r for r in model['manifest']['records'] if r['kind']=='terminal')
    body=json.loads(model['records'][seal['sequence']]);body['payload']['controller'].update(changes)
    c=body['payload']['controller'];tb=json.loads(model['records'][terminal['sequence']])
    tb['payload']['controller'].update(continuous_campaign=copy.deepcopy(c),
        ended_ns=c['qualified_ns'],last_capture_id=c['source_capture_id'])
    replace_fixture_record(model,terminal['sequence'],tb)
    body['payload']['terminal_sha256']=terminal['sha256']
    replace_fixture_record(model,seal['sequence'],body)


class ContinuousServer116(IrregularServer):
    yield_after_restart=False

    def __init__(self,base):
        super().__init__(base)
        self.root=None;self.polls=0;self.live=False;self.cancelled=False
        self.start_failure=False;self.root_unavailable=False;self.before_post=None
        self.exports_while_live=[];self.validator=subject_client()(lambda *_:b'',KEY,TOK,crypto=Crypto(native=False))
        self.after_models=None
        self.reverse_prepare=False
        self.refuse_start=False;self.refusal_shape_valid=True

    def wire(self,terminal=False,second=True):
        value=status_wire(terminal=terminal,second=second)
        p=value['payload'];p['root_id']=self.root;value['run_id']=self.root
        p['children'][0].update(run_id=self.root)
        if second:
            p['children'][1].update(predecessor_id=self.root)
        p['active_run_id']=SECOND if second else self.root
        for row in p['children']:
            if row['escrow_sealed']:
                seal=next(r for r in self.models[row['run_id']]['manifest']['records'] if r['kind']=='continuation_seal')
                row['escrow_sha256']=seal['sha256']
        if terminal and self.cancelled:p['stop_reason']='cancelled'
        return value

    def call(self,method,params):
        self.validator._validate(method,params)
        mode=params.get('mode')
        if method=='necro_native_start':
            if self.before_post is not None:self.before_post()
            guard=getattr(self,'_before_start_post',None)
            if guard is not None:guard()
            saved=json.loads((self.base/'continuous-campaign.json').read_bytes())
            assert saved['start_intent'] and saved['campaign_id']==params['run_id']
            if self.refuse_start:
                self.refuse_start=False;self.calls.append((method,copy.deepcopy(params)))
                raise RemoteRpcError(-32095,'unclassified',self.refusal_shape_valid)
            self.calls.append((method,copy.deepcopy(params)));self.root=params['run_id'];self.live=True
            self.models={self.root:campaign_model(self.root,self.root,0,None,SECOND),
                SECOND:campaign_model(SECOND,self.root,1,self.root,None)}
            if self.after_models is not None:self.after_models(self)
            if self.start_failure:
                self.start_failure=False;raise ProbeError('connection_error')
            return dict(run_id=self.root,profile=SPEC.profile,state='accepted',api_version=cycle.API_VERSION,
                report={},continuous_campaign=True)
        if method=='necro_native_cancel':
            self.calls.append((method,copy.deepcopy(params)))
            if self.root_unavailable:raise RemoteRpcError(-32097,'unclassified',True)
            self.live=False;self.cancelled=True
            return dict(run_id=params['run_id'],profile=SPEC.profile,state='stopped',
                api_version=cycle.API_VERSION,report={},continuous_campaign=True)
        if mode=='prepare':
            self.calls.append((method,copy.deepcopy(params)))
            ids=[rid for rid,model in self.models.items() if not model['published']]
            if self.reverse_prepare:ids.reverse()
            return self.wrap(params['run_id'],mode,dict(ready=not ids,notification_authorization='authorized',
                recovery_scan='ready',unpublished_run_ids=ids,reason='none'))
        if mode=='campaign_status':
            self.calls.append((method,copy.deepcopy(params)))
            if self.root_unavailable:raise RemoteRpcError(-32097,'unclassified',True)
            self.polls+=1;terminal=self.cancelled or self.polls>=3
            if terminal:self.live=False
            return self.wire(terminal,second=self.polls>=2 or terminal)
        if mode in ('manifest','record','batch','published') and self.live:
            self.exports_while_live.append(copy.deepcopy(params))
        return super().call(method,params)


class ContinuousClientRun116Tests(unittest.TestCase):
    def run_client(self,server,base,destination,**options):
        from necroprobe import campaign116 as campaign
        original=cycle.device_lock
        with patch('necroprobe.native_cycle.device_lock',lambda path=None:original(path or Path(destination)/'device.lock')):
            return campaign.run(server,destination,spool=base,notice=lambda _:None,
                clock=lambda:100,sleep=lambda _:None,**options)

    def unused_qualified_server(self, base, reason='cancelled', *, zero=False):
        server=ContinuousServer116(base);original_wire=server.wire
        def finish_before_next(server):
            model=server.models[server.root]
            if zero:
                from necroprobe import campaign116 as campaign
                changes=dict.fromkeys(campaign.CONTROLLER_NUMBERS,0)
                changes['root_deadline_ns']=1+campaign.ROOT_DURATION_NS
                change_snapshot(model,changes)
            seal=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
            body=json.loads(model['records'][seal['sequence']]);body['payload']['next_run_id']=None
            replace_fixture_record(model,seal['sequence'],body)
            server.models={server.root:model}
        def wire(terminal=False,second=True):
            value=original_wire(terminal,second=False)
            if terminal:
                value['payload']['stop_reason']=reason
                value['payload']['children'][0]['terminal_reason']=14
            return value
        server.after_models=finish_before_next;server.wire=wire
        return server

    def test_live_handoffs_export_nothing_then_collect_and_publish_every_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);result=self.run_client(server,base,dest)
            self.assertTrue(result['ledger']['complete'])
            self.assertEqual([server.root,SECOND],[r['run_id'] for r in result['ledger']['runs']])
            self.assertEqual([],server.exports_while_live)
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))
            self.assertTrue(all(m['published'] for m in server.models.values()))
            self.assertTrue(result['campaign_archive'].exists())
            self.assertTrue(all((dest/'runtime'/r['archive_name']).is_file() for r in result['ledger']['runs']))

    def test_uncertain_start_is_never_posted_again_and_recovery_has_no_keepalive(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.start_failure=True
            first=self.run_client(server,base,dest)
            self.assertFalse(first['ledger']['complete'])
            server.calls.clear()
            second=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(second['ledger']['complete'])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))
            self.assertFalse(any(p.get('keepalive') for m,p in server.calls if p.get('mode')=='campaign_status'))

    def test_collection_failure_resumes_original_children_without_new_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.fail_chunk=True
            first=self.run_client(server,base,dest)
            self.assertFalse(first['ledger']['complete'])
            root=server.root;server.calls.clear()
            second=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(second['ledger']['complete'])
            self.assertEqual(root,second['ledger']['campaign_id'])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_lost_selector_uses_durable_root_intent_instead_of_new_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.start_failure=True
            self.run_client(server,base,dest);root=server.root
            (base/'continuous-campaign.json').unlink();server.calls.clear()
            result=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(result['ledger']['complete']);self.assertEqual(root,result['ledger']['campaign_id'])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_native_restart_reconstructs_all_child_links_and_only_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.start_failure=True
            self.run_client(server,base,dest);server.root_unavailable=True;server.calls.clear()
            result=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(result['ledger']['complete'],
                'durable child sessions and seals must replace a lost in-memory root index')
            self.assertEqual([server.root,SECOND],[r['run_id'] for r in result['ledger']['runs']])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_cancel_between_durable_intent_and_transport_sends_no_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);cancelled=[False]
            server.before_post=lambda:cancelled.__setitem__(0,True)
            result=self.run_client(server,base,dest,cancelled=lambda:cancelled[0])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls),
                'the final transport guard must recheck cancellation after saving start intent')
            self.assertFalse(result['ledger']['start_intent'])

    def test_wrong_frames_digest_cannot_complete_or_drop_any_child_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base)
            def tamper(server):
                model=server.models[SECOND]
                seal=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
                body=json.loads(model['records'][seal['sequence']]);body['payload']['frames_sha256']='f'*64
                replace_fixture_record(model,seal['sequence'],body)
            server.after_models=tamper
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['complete'],
                'a well-formed hash must match the exact exported frame registry')
            self.assertEqual(2,len(result['ledger']['runs']))
            self.assertTrue(all((dest/'runtime'/r['archive_name']).is_file() for r in result['ledger']['runs']))

    def test_local_status_save_failure_still_cancels_the_live_root(self):
        from necroprobe import campaign116 as campaign
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);original=campaign._save;failed=[False]
            def save(base,ledger):
                if ledger['native_status'] is not None and not failed[0]:
                    failed[0]=True;raise OSError('procedural durable status write fault')
                return original(base,ledger)
            with patch.object(campaign,'_save',save):
                try:self.run_client(server,base,dest)
                except OSError:pass
            self.assertTrue(server.cancelled,
                'a failed host journal write must not leave the live root running')

    def test_orphan_native_namespaces_are_all_recovered_without_a_new_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.root=ROOT;server.root_unavailable=True
            server.models={ROOT:campaign_model(ROOT,ROOT,0,None,SECOND),
                SECOND:campaign_model(SECOND,ROOT,1,ROOT,None)}
            result=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertTrue(result['ledger']['complete'])
            self.assertEqual('recovered_readonly',result['ledger']['index_source'])
            self.assertEqual([ROOT,SECOND],[r['run_id'] for r in result['ledger']['runs']])
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_seal_clock_session_terminal_and_qualified_binding_cannot_be_forged(self):
        for field,value in (('clock_id','a'*32),('session_sha256','a'*64),
                            ('terminal_sha256','a'*64),('next_run_id','a'*32),
                            ('controller',None)):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=ContinuousServer116(base)
                def tamper(server):
                    model=server.models[SECOND]
                    item=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
                    body=json.loads(model['records'][item['sequence']])
                    if field=='controller':body['payload']['controller']['qualified']=True
                    else:body['payload'][field]=value
                    replace_fixture_record(model,item['sequence'],body)
                server.after_models=tamper
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['complete'])
                self.assertEqual(2,len(result['ledger']['runs']))

    def test_unsealed_storage_failure_keeps_all_archives_and_incomplete_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);wire=server.wire
            def unsealed(terminal=False,second=True):
                value=wire(terminal,second)
                if terminal:
                    value['payload'].update(stop_reason='storage')
                    value['payload']['children'][-1].update(escrow_sealed=False,escrow_sha256=None)
                return value
            server.wire=unsealed
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['complete']);self.assertEqual('storage',result['stop_reason'])
            self.assertEqual(2,len(result['ledger']['runs']));self.assertTrue(result['campaign_archive'].exists())

    def test_root_deadline_cannot_be_extended_by_a_later_status_reply(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);wire=server.wire
            def extended(terminal=False,second=True):
                value=wire(terminal,second)
                if terminal:value['payload']['deadline_ns']+=1
                return value
            server.wire=extended
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['complete'])
            self.assertEqual('campaign_index_changed',result['ledger']['last_error'])
            self.assertEqual([],server.exports_while_live);self.assertTrue(server.cancelled)

    def test_missing_new_capability_never_posts_a_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.schema_error='native_capability_missing'
            with self.assertRaisesRegex(ProbeError,'native_capability_missing'):
                self.run_client(server,base,dest)
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls))

    def test_no_continuous_opt_in_cannot_create_a_new_native_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base)
            try:self.run_client(server,base,dest,until_target=False,recovery_only=False)
            except ProbeError:pass
            self.assertFalse(any(m=='necro_native_start' for m,_ in server.calls),
                'continuous campaigns require explicit opt-in or read-only recovery')

    def test_qualified_zero_snapshot_cannot_verify_a_continued_child(self):
        from necroprobe import campaign116 as campaign
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base)
            def zero(server):
                model=server.models[server.root]
                seal=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
                terminal=next(r for r in model['manifest']['records'] if r['kind']=='terminal')
                body=json.loads(model['records'][seal['sequence']])
                for key in campaign.CONTROLLER_NUMBERS:body['payload']['controller'][key]=0
                body['payload']['controller']['root_deadline_ns']=1+campaign.ROOT_DURATION_NS
                tb=json.loads(model['records'][terminal['sequence']])
                tb['payload']['controller']['continuous_campaign']=copy.deepcopy(body['payload']['controller'])
                replace_fixture_record(model,terminal['sequence'],tb)
                body['payload']['terminal_sha256']=terminal['sha256']
                replace_fixture_record(model,seal['sequence'],body)
            server.after_models=zero
            result=self.run_client(server,base,dest)
            self.assertFalse(result['ledger']['complete'],
                'qualified=true and a matching zero companion are not a completed negative/restart chain')

    def test_unordered_orphan_namespaces_reconstruct_in_child_index_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.root=ROOT;server.root_unavailable=True;server.reverse_prepare=True
            server.models={ROOT:campaign_model(ROOT,ROOT,0,None,SECOND),
                SECOND:campaign_model(SECOND,ROOT,1,ROOT,None)}
            result=None
            try:result=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            except ProbeError:pass
            self.assertIsNotNone(result,'namespace enumeration order cannot prevent a valid recovery')
            self.assertTrue(result['ledger']['complete'])
            self.assertEqual([ROOT,SECOND],[r['run_id'] for r in result['ledger']['runs']])

    def test_first_floor_itself_and_parent_deadline_equality_remain_legal(self):
        for changes in (dict(source_capture_id=20,source_start_ns=200),dict(parent_deadline_ns=225)):
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=ContinuousServer116(base)
                server.after_models=lambda server:change_snapshot(server.models[server.root],changes)
                result=self.run_client(server,base,dest)
                self.assertTrue(result['ledger']['complete'],
                    'the independent verifier must preserve native same-frame and parent-equality semantics')

    def test_continuation_requires_the_real_negative_restart_and_epoch_chain(self):
        cases=(
            ('checkpoint',lambda p:p['assessment'].update(outcome='unknown')),
            ('checkpoint',lambda p:p.update(clock_id='a'*32)),
            ('checkpoint',lambda p:p.update(generation=8)),
            ('restart_intent',lambda p:p.update(command=None)),
            ('restart_intent',lambda p:p['cycle'].update(job_id=True)),
            ('restart_outcome',lambda p:p.update(controller=None)),
            ('restart_outcome',lambda p:p.update(floor_raw_sha256='a'*64)),
            ('restart_outcome',lambda p:p.update(generation=True)),
        )
        for kind,change in cases:
            with self.subTest(kind=kind,change=change),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=ContinuousServer116(base)
                def tamper(server):
                    model=server.models[server.root]
                    item=next(r for r in model['manifest']['records'] if r['kind']==kind)
                    body=json.loads(model['records'][item['sequence']]);change(body['payload'])
                    replace_fixture_record(model,item['sequence'],body)
                    seal=next(r for r in model['manifest']['records'] if r['kind']=='continuation_seal')
                    terminal=next(r for r in model['manifest']['records'] if r['kind']=='terminal')
                    body=json.loads(model['records'][seal['sequence']])
                    body['payload']['terminal_sha256']=terminal['sha256']
                    replace_fixture_record(model,seal['sequence'],body)
                server.after_models=tamper
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['complete'])
                self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_recovered_root_keeps_unknown_diagnostics_from_every_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.start_failure=True
            self.run_client(server,base,dest)
            server.models[server.root]['manifest'].update(input_state=4,ui_frozen=True)
            server.root_unavailable=True
            result=self.run_client(server,base,dest,until_target=False,recovery_only=True)
            self.assertEqual(4,result['ledger']['native_status']['input_state'],
                'a later clean child cannot erase an earlier UNKNOWN input diagnostic')
            self.assertTrue(result['ledger']['native_status']['ui_frozen'])
            self.assertFalse(result['ledger']['complete'],
                'manifest UNKNOWN contradicts the claimed input-free continuation snapshot')

    def test_authenticated_not_admitted_resets_intent_without_reposting_and_rechecks_prepare(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.refuse_start=True
            first=self.run_client(server,base,dest);root=first['ledger']['campaign_id']
            self.assertFalse(first['ledger']['start_intent'],
                'only authenticated pre-admission refusal proves that no root was started')
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))
            self.assertFalse(any(m=='necro_native_cancel' for m,_ in server.calls))
            server.calls.clear()
            second=self.run_client(server,base,dest)
            self.assertTrue(second['ledger']['complete'])
            self.assertEqual(root,second['ledger']['campaign_id'])
            self.assertEqual('schema',server.calls[0][0])
            self.assertEqual('prepare',server.calls[1][1]['mode'])
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_untrusted_not_admitted_code_keeps_the_uncertain_original_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
            server=ContinuousServer116(base);server.refuse_start=True;server.refusal_shape_valid=False
            result=self.run_client(server,base,dest)
            self.assertTrue(result['ledger']['start_intent'])
            self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))

    def test_cancelled_last_child_may_retain_a_real_unused_qualified_snapshot(self):
        for reason in ('cancelled','owner','locked','session','native_limit'):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=self.unused_qualified_server(base,reason)
                result=self.run_client(server,base,dest)
                self.assertTrue(result['ledger']['complete'],
                    'a cancelled successor admission cannot falsify an already durable C proof')
                self.assertEqual(1,len(result['ledger']['runs']))
                self.assertEqual(reason,result['stop_reason'])
                self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))
                self.assertEqual([],server.exports_while_live)

    def test_unused_last_qualification_is_not_a_zero_or_unexplained_positive_stop(self):
        for reason,zero in (('cancelled',True),('none',False),('unknown',False),
                            ('target',False),('candidate',False),('storage',False)):
            with self.subTest(reason=reason,zero=zero),tempfile.TemporaryDirectory() as temporary:
                dest=Path(temporary);base=dest/'spool'/'test-116';base.mkdir(parents=True)
                server=self.unused_qualified_server(base,reason,zero=zero)
                result=self.run_client(server,base,dest)
                self.assertFalse(result['ledger']['complete'])
                self.assertEqual(1,sum(m=='necro_native_start' for m,_ in server.calls))


class ContinuousClientEntry116Tests(unittest.TestCase):
    def test_known_not_started_notice_requests_normal_retry_instead_of_recovery(self):
        from necroprobe import test116 as entry
        from necroprobe import campaign116 as campaign
        ledger=campaign._fresh();ledger.update(last_error='cycle_start_not_admitted')
        result=dict(ledger=ledger,campaign_archive=None,stop_reason='cycle_start_not_admitted',record=None)
        output=io.StringIO()
        with tempfile.TemporaryDirectory() as temporary,patch.object(Path,'home',return_value=Path(temporary)),\
                patch.object(entry,'load_pairing',return_value=(KEY,TOK)),\
                patch.object(campaign,'run',return_value=result),redirect_stdout(output):
            self.assertEqual(2,entry.main(['--until-target','--python-crypto']))
        self.assertIn('ゲームは開始していません',output.getvalue())
        self.assertNotIn('--recovery',output.getvalue())


if __name__ == '__main__':
    unittest.main()
