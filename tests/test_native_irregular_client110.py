"""Explicit irregular protocol: pure client/storage contracts, not phone UI."""
import copy
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import native_cycle as cycle
from necroprobe import native_walk, irregular
from necroprobe import cycle_publication as publication
from necroprobe import campaign099 as campaign
from necroprobe import trial_evidence099 as trial
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_native_cycle_client094 import companion, png
from test_protocol import KEY, TOK, sealed_reply

RUN = 'a' * 32
PROFILE = 'normal-1-1-irregular-v1'
QUERY = 'necro_native_irregular'
SCHEMA = 'ngg2-irregular-cycle-v1'
SPEC = cycle.IRREGULAR_PROTOCOL


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def status_value(**changes):
    value = dict.fromkeys(irregular.STATUS_NUMBERS, 0)
    value.update(abi_version=1, enabled=True, kind='none', stage='idle', held_reason='none')
    value.update(changes)
    return value


def observation(kind=0):
    value = dict.fromkeys(irregular.OBS_NUMBERS, 0)
    value.update(abi_version=1, struct_size=288, kind=kind)
    value.update({key: [0]*3 for key in irregular.HEART_ARRAYS})
    value.update({key: [0]*4 for key in irregular.ENEMY_ARRAYS})
    if kind == 1:
        value.update(glyph_intersection=476, glyph_union=727, hud_mask=15,
            empty_hearts=3, matches=1, left=312, top=312, width=270, height=24,
            heart_inter=[374]*3, heart_union=[397]*3, heart_red=[250]*3,
            heart_dark=[225]*3, heart_bright=[25]*3)
    elif kind == 2:
        value.update(glyph_intersection=223, glyph_union=223, matches=1,
            left=357, top=256, width=181, height=28)
    elif kind == 3:
        value.update(enemy_mask=2,hud_mask=15)
        for key, number in dict(enemy_matches=1, enemy_inter=137, enemy_union=137,
            enemy_left=477, enemy_top=181, enemy_body_luma=80,
            enemy_body_saturation=160, enemy_heart_count=1,
            enemy_width=15, enemy_height=13).items():
            value[key][1] = number
    return value


def frame(role, capture, start, prefix):
    return dict(role=role, capture_id=capture, start_ns=start, end_ns=start+1,
        prefix=prefix, generation=1, rgba_sha256='c'*64)


def command(kind, source, ident):
    return dict(id=ident, ordinal=ident, target_ns=source['end_ns']+5,
        not_before_ns=source['end_ns']+5, deadline_ns=source['end_ns']+10,
        source_capture_id=source['capture_id'], source_start_ns=source['start_ns'],
        phase_sample_ns=source['start_ns'], kind=kind, direction=2 if kind==4 else 0,
        x=90 if kind==5 else 144, y=447 if kind==5 else 448)


def payload(state, frames, *, action=None, ack=None, observations=(), proofs=()):
    return dict(irregular=copy.deepcopy(state), generation=1,
        resources=dict(raw_slots=8, raw_bytes=8*896*414*4, pin_slots=8,
            episode_metadata_bytes=4096, final_metadata_bytes=2048),
        frames=copy.deepcopy(frames), observations=copy.deepcopy(list(observations)),
        command=copy.deepcopy(action), ack=copy.deepcopy(ack),
        proofs=copy.deepcopy(list(proofs)), assessment_hint=None)


def death_episode(case='complete'):
    baseline=frame('last_live_baseline', 1, 90, 0)
    trigger=frame('trigger', 2, 100, 0)
    after=frame('continue_outcome', 3, 120, 1)
    menu1=frame('menu1', 4, 130, 1)
    menu2=frame('menu2', 5, 140, 1)
    fresh=frame('new_floor', 6, 160, 2)
    state=status_value(kind='death', stage='checkpoint', episode_id=1, episodes=1,
        trigger_capture_id=2, live_baseline_capture_id=1, trigger_ns=102,
        parent_deadline_ns=1000, durable_ns=104)
    observed=lambda f,k: dict(capture_id=f['capture_id'],value=observation(k))
    result=[('irregular_checkpoint', payload(state,[baseline,trigger],
        observations=[observed(trigger,1)]))]
    if case=='checkpoint':return result
    death=copy.deepcopy(trigger);death['role']='fresh_death'
    cont=command(5,death,1)
    state.update(stage='death_continue',continue_command_id=1,continue_intent_ns=105)
    result.append(('irregular_continue_intent', payload(state,[death],action=cont,
        observations=[observed(death,1)])))
    if case=='pending':return result
    unknown=case=='unknown'
    state.update(stage='held' if unknown else 'wait_menu',
        held_reason='unknown_input' if unknown else 'none',
        prefix=0 if unknown else 1,continue_capture_id=3,continue_outcome_ns=122)
    ack=dict(command_id=1,kind=5,started_ns=108,completed_ns=109,
             outcome='unknown' if unknown else 'acked')
    if unknown:after['prefix']=0
    result.append(('irregular_continue_outcome', payload(state,[death,after],action=cont,ack=ack)))
    if unknown or case=='continued':return result
    restart_source=copy.deepcopy(menu2);restart_source['role']='restart_source'
    restart=command(3,restart_source,2)
    state.update(stage='restart_ready', restart_command_id=2,restart_intent_ns=143)
    result.append(('irregular_restart_intent',payload(state,[menu1,menu2,restart_source],
        action=restart,observations=[observed(menu1,2),observed(menu2,2)])))
    state.update(stage='outcome',prefix=2,next_floor_capture_id=6,outcome_ns=162)
    ack=dict(command_id=2,kind=3,started_ns=150,completed_ns=151,outcome='acked')
    result.append(('irregular_restart_outcome',payload(state,[restart_source,fresh],action=restart,ack=ack)))
    return result


def stalled_upgrade():
    before=frame('before',2,100,0);zero1=frame('zero1',3,120,1);zero2=frame('zero2',4,140,1)
    baseline=frame('last_live_baseline',1,90,0);trigger=copy.deepcopy(zero2);trigger['role']='trigger'
    state=status_value(kind='stalled',stage='checkpoint',episode_id=1,episodes=1,
        trigger_capture_id=4,before_capture_id=2,live_baseline_capture_id=1,
        proof_capture_id=3,prefix=1,trigger_ns=142,parent_deadline_ns=1000)
    action=command(4,before,1);ack=dict(command_id=1,kind=4,started_ns=108,completed_ns=109,outcome='acked')
    proofs=[dict(capture_id=f['capture_id'],start_ns=f['start_ns'],end_ns=f['end_ns'],
        normal_motion='blocked',dx=0,dy=0,enemy=observation(3)) for f in (zero1,zero2)]
    observed=[dict(capture_id=f['capture_id'],value=observation(3)) for f in (zero1,zero2)]
    checkpoint=payload(state,[baseline,before,zero1,zero2,trigger],action=action,ack=ack,
        observations=observed,proofs=proofs)
    fresh=frame('fresh_death',5,150,1)
    state.update(kind='death',stage='death_continue',durable_ns=145,continue_command_id=2)
    intent=payload(state,[fresh],action=command(5,fresh,2),
        observations=[dict(capture_id=5,value=observation(1))])
    return [('irregular_checkpoint',checkpoint),('irregular_continue_intent',intent)]


def raw_frames(sequence):
    frames={}
    for _,value in sequence:
        for row in value['frames']:
            frames[row['capture_id']]=dict(raw_sha256=row['rgba_sha256'],metadata=dict(
                capture_start_ns=row['start_ns'],capture_end_ns=row['end_ns'],
                completed_prefix_start=row['prefix'],completed_prefix_end=row['prefix'],
                generation=row['generation'],stable_prefix=True,inflight_start=False,inflight_end=False))
    return frames


def native_model(run_id, case='complete', *, protocol=SPEC):
    """Native bytes are constructed once, never profile-translated by the client."""
    raw_png=png()
    hint_case=case.startswith('hint_')
    chain=death_episode('pending' if hint_case else case)
    if hint_case:
        value=chain[0][1];source=copy.deepcopy(value['frames'][0]);source['role']='ring_source'
        value['frames'].append(source)
        value['assessment_hint']=dict(job_id=9,capture_id=source['capture_id'],prefix=source['prefix'],
            status='deadline',outcome=case.split('_',1)[1])
    known_ack=max((item['ack']['command_id'] for _,item in chain
        if item['ack'] is not None and item['ack']['outcome']=='acked'),default=0)
    state=companion()
    state.update(job_id=0,outcome='unknown',completed_shops=0,full_seen=False,
                 coverage='incomplete',prefix=known_ack,level_id=2 if case=='complete' else 1)
    events=[]
    for _, item in chain:
        if item['ack'] is not None:
            ack=item['ack'];cmd=item['command']
            events.append(dict(id=cmd['id'],kind=cmd['kind'],direction=0,
                outcome=2 if ack['outcome']=='acked' else 4,reason=0,
                source_capture_id=cmd['source_capture_id'],source_start_ns=cmd['source_start_ns'],
                begin_ns=ack['started_ns'],end_ns=ack['completed_ns'],
                observed_capture_id=0,motion=0,dx=0,dy=0))
    controller=dict(events=events,motion_references=[],moves=0,restarts=1 if case=='complete' else 0,reason=17,
        inputs=0,last_completed_id=known_ack)
    terminal=dict(cycle=copy.deepcopy(state),controller=controller,
        assessment=None,assessment_adopted=False,irregular=copy.deepcopy(chain[-1][1]['irregular']))
    chain.append(('terminal',terminal))
    records={0:cycle.canonical(dict(schema='ngg2-cycle-spool-v1',run_id=run_id,
        owner_sha256='d'*64,provenance=dict(native_profile=protocol.profile)))}
    kinds=[(0,'session',0)];previous=None;frames={}
    for sequence,(name,item) in enumerate(chain,1):
        body=dict(schema='ngg2-cycle-record-v1',run_id=run_id,sequence=sequence,
            kind=name,cycle=0,previous=previous,payload=item)
        records[sequence]=cycle.canonical(body)
        previous=sha(records[sequence]);kinds.append((sequence,name,0))
        for row in item.get('frames',[]):frames[row['capture_id']]=row
    for sequence,(ident,row) in enumerate(sorted(frames.items()),513):
        metadata=dict(capture_id=ident,capture_start_ns=row['start_ns'],capture_end_ns=row['end_ns'],
            completed_prefix_start=row['prefix'],completed_prefix_end=row['prefix'],
            generation=1,stable_prefix=True,inflight_start=False,inflight_end=False,
            pixel_width=896,pixel_height=414)
        records[sequence]=cycle.canonical(dict(schema='ngg2-cycle-frame-v1',run_id=run_id,
            capture_id=ident,raw_sha256=row['rgba_sha256'],raw_bytes=896*414*4,metadata=metadata))
        kinds.append((sequence,'frame',0))
    images=[dict(name='capture-'+str(c).zfill(6)+'.png',capture_id=c,bytes=len(raw_png),
        sha256=sha(raw_png),raw_sha256='c'*64,width=896,height=414) for c in sorted(frames)]
    export_id=sha(run_id.encode())[:32]
    manifest=dict(schema='ngg2-cycle-manifest-v1',run_id=run_id,profile=protocol.profile,
        export_id=export_id,complete=True,interrupted=False,terminal=True,workers_drained=True,
        input_state=4 if case=='unknown' else 0,ui_frozen=case=='unknown',native_inflight=False,
        images=images,records=[dict(sequence=s,kind=k,cycle=n,bytes=len(records[s]),sha256=sha(records[s]))
            for s,k,n in kinds],diagnostics=[],total_bytes=len(images)*len(raw_png)+sum(map(len,records.values())),
        chunk_bytes=cycle.CHUNK_BYTES)
    return dict(image=raw_png,records=records,manifest=manifest,terminal=terminal,cycle=state,
        irregular=terminal['irregular'],published=False)


def store_model(base, model, *, protocol=SPEC):
    """Materialize authoritative fixture bytes, including their own hashes."""
    manifest=model['manifest'];record=cycle.fresh_record(manifest['run_id'],protocol_spec=protocol)
    folder=base/('cycle-'+record['run_id']);folder.mkdir(parents=True,exist_ok=True)
    raw=cycle.canonical(manifest);(folder/'native-manifest.json').write_bytes(raw)
    record.update(start_intent=True,state='completed',resolved=True,
        manifest_sha256=sha(raw),export_id=manifest['export_id'])
    for name in ('records','images'):
        (folder/name).mkdir()
        for item in manifest[name]:
            data=model['records'][item['sequence']] if name=='records' else model['image']
            filename=cycle.record_name(item) if name=='records' else item['name']
            (folder/name/filename).write_bytes(data)
        record[name]=[dict(item,offset=item['bytes'],prefix_sha256=item['sha256']) for item in manifest[name]]
    cycle._journal(base,record)
    return record


def replace_fixture_record(model, sequence, body):
    """Only a fixture factory: regenerate hash-linked native test bytes."""
    model['records'][sequence]=cycle.canonical(body)
    previous=None
    for item in model['manifest']['records']:
        seq=item['sequence']
        if 0 < seq < 513:
            value=json.loads(model['records'][seq]);value['previous']=previous
            model['records'][seq]=cycle.canonical(value);previous=sha(model['records'][seq])
        item.update(bytes=len(model['records'][seq]),sha256=sha(model['records'][seq]))
    model['manifest']['total_bytes']=len(model['manifest']['images'])*len(model['image'])+sum(map(len,model['records'].values()))


def normal_model(run_id, case):
    from test_campaign099 import native_model as normal_fixture
    # The selected native fixture owns its profile before any RPC or durable
    # client bytes exist; the production client never translates these fields.
    model=normal_fixture(run_id,case)
    model['manifest']['profile']=PROFILE
    header=json.loads(model['records'][0]);header['provenance']=dict(native_profile=PROFILE)
    model['records'][0]=cycle.canonical(header)
    terminal=next(item for item in model['manifest']['records'] if item['kind']=='terminal')
    body=json.loads(model['records'][terminal['sequence']])
    body['payload']['irregular']=status_value()
    replace_fixture_record(model,terminal['sequence'],body)
    model['irregular']=status_value()
    return model


class IrregularServer:
    protocol_spec=SPEC

    def __init__(self,base,case='complete'):
        self.base=base;self.case=case;self.calls=[];self.models={};self.fail_start=False
        self.fail_chunk=False;self.schema_error=None;self.cases=[];self.omit_capture_id=None

    def check_schema(self):
        self.calls.append(('schema',{}))
        if self.schema_error:raise ProbeError(self.schema_error)
        return {}

    def wrap(self,run_id,mode,value):
        return dict(schema=SCHEMA,run_id=run_id,profile=PROFILE,mode=mode,payload=value)

    def call(self,method,params):
        self.calls.append((method,copy.deepcopy(params)));run_id=params['run_id']
        if method=='necro_native_start':
            assert params['profile']==PROFILE
            saved=cycle.load_journal(self.base,protocol_spec=SPEC)
            assert saved['start_intent'] and saved['run_id']==run_id
            selected=self.cases.pop(0) if self.cases else self.case
            self.models[run_id]=(normal_model(run_id,selected.split(':',1)[1])
                if selected.startswith('normal:') else native_model(run_id,selected))
            if self.omit_capture_id is not None:
                manifest=self.models[run_id]['manifest']
                removed=[item for item in manifest['images'] if item['capture_id']==self.omit_capture_id]
                manifest['images']=[item for item in manifest['images'] if item['capture_id']!=self.omit_capture_id]
                manifest['total_bytes']-=sum(item['bytes'] for item in removed)
            if self.fail_start:
                self.fail_start=False;raise ProbeError('connection_error')
            return dict(run_id=run_id,profile=PROFILE,state='accepted',api_version=cycle.API_VERSION,report={})
        if method=='necro_native_cancel':
            return dict(run_id=run_id,profile=PROFILE,state='stopped',api_version=cycle.API_VERSION,report={})
        assert method==QUERY
        mode=params['mode']
        if mode=='prepare':return self.wrap(run_id,mode,dict(ready=True,
            notification_authorization='authorized',recovery_scan='ready',unpublished_run_ids=[],reason='none'))
        model=self.models[run_id];manifest=model['manifest'];export_id=manifest['export_id']
        if mode=='status':return self.wrap(run_id,mode,dict(state='completed',terminal=True,
            workers_drained=True,input_state=manifest['input_state'],ui_frozen=manifest['ui_frozen'],
            native_inflight=False,cycle=model['cycle'],irregular=model['irregular'],
            notification=dict(authorization='authorized',state='requested')))
        if mode=='manifest':
            raw=cycle.canonical(manifest)
            return self.wrap(run_id,mode,dict(export_id=export_id,manifest_sha256=sha(raw),manifest_json=raw.decode()))
        if mode in ('record','batch'):
            if self.fail_chunk:
                self.fail_chunk=False;raise ProbeError('connection_error')
            key='sequence' if mode=='record' else 'capture_id'
            data=model['records'][params[key]] if mode=='record' else model['image']
            offset=params['offset'];parts=[]
            for _ in range(params.get('count',1)):
                raw=data[offset:offset+cycle.CHUNK_BYTES]
                parts.append(dict(export_id=export_id,**{key:params[key]},offset=offset,
                    total_bytes=len(data),sha256=sha(data),data_base64=base64.b64encode(raw).decode(),
                    next_offset=offset+len(raw),eof=offset+len(raw)==len(data)))
                offset+=len(raw)
                if offset==len(data):break
            return self.wrap(run_id,mode,dict(export_id=export_id,chunks=parts) if mode=='batch' else parts[0])
        if mode=='published':
            saved=cycle.load_journal(self.base,protocol_spec=SPEC)
            assert saved['resolved'] and saved['archive_sha256']==params['archive_sha256']
            model['published']=True
            return self.wrap(run_id,mode,dict(accepted=True,export_id=export_id,
                manifest_sha256=params['manifest_sha256'],archive_sha256=params['archive_sha256'],receipt_sha256='f'*64))
        raise AssertionError(mode)


class IrregularClient110Tests(unittest.TestCase):
    def test_explicit_irregular_client_admits_only_its_profile_and_query(self):
        client_type = getattr(cycle, 'IrregularCycleClient', cycle.CycleClient)
        client = client_type(lambda *_: None)
        try:
            client._validate('necro_native_start', {'run_id': RUN, 'profile': PROFILE})
            client._validate(QUERY, {'run_id': RUN, 'mode': 'status', 'keepalive': False})
        except ProbeError:
            self.fail('the explicit irregular client must admit the authorized sibling protocol')

    def test_old_and_new_admission_do_not_follow_reply_selected_profiles(self):
        for client_type,wrong in ((cycle.CycleClient,SPEC),
                                  (cycle.IrregularCycleClient,cycle.STANDARD_PROTOCOL)):
            client=client_type(lambda *_:None)
            for method,params in (('necro_native_start',dict(run_id=RUN,profile=wrong.profile)),
                (wrong.query,dict(run_id=RUN,mode='status',keepalive=False))):
                with self.subTest(client=client_type.__name__,method=method),self.assertRaises(ProbeError):
                    client._validate(method,params)
        old=cycle.CycleClient(lambda *_:None)
        self.assertIs(cycle.STANDARD_PROTOCOL,old.protocol_spec)
        with self.assertRaises(AttributeError):SPEC.profile=cycle.PROFILE
        with self.assertRaises(ProbeError):cycle.fresh_record(protocol_spec=SPEC._replace(profile=cycle.PROFILE))

    def test_api16_schema_requires_both_caps_and_keeps_unrelated_tags(self):
        class Transport(HttpTransport):
            def schema(self,_timeout):return cycle.canonical(self.metadata)
        transport=Transport()
        with OwnedRpcTimer() as timer:
            client=cycle.IrregularCycleClient(transport,KEY,TOK,deadline_owner=timer)
            for caps in ([cycle.CAPABILITY],[SPEC.capability],[]):
                transport.metadata=dict(server_version=cycle.API_VERSION,protocol_version=1,capability_tags=caps)
                with self.subTest(caps=caps),self.assertRaisesRegex(ProbeError,'native_capability_missing'):
                    client.check_schema()
            transport.metadata=dict(server_version=cycle.API_VERSION,protocol_version=1,
                capability_tags=['unrelated',SPEC.capability,cycle.CAPABILITY])
            self.assertEqual(dict(api_version=cycle.API_VERSION,capability=SPEC.capability),client.check_schema())
            old=cycle.CycleClient(transport,KEY,TOK,deadline_owner=timer)
            self.assertEqual(cycle.CAPABILITY,old.check_schema()['capability'])

    def test_trial_preflight_uses_only_selected_sibling_query(self):
        class Transport(HttpTransport):
            def schema(self,_timeout):return cycle.canonical(dict(server_version=cycle.API_VERSION,
                protocol_version=1,capability_tags=[cycle.CAPABILITY,SPEC.capability]))
            def _exchange(self,method,path,body,timeout,maximum):
                return sealed_reply(body,result=dict(schema=SCHEMA,run_id=client.trial_probe_id,
                    profile=PROFILE,mode='trial_support',payload=trial.SUPPORT))
        with OwnedRpcTimer() as timer:
            client=trial.IrregularTrialClient110(Transport(),KEY,TOK,
                crypto=Crypto(native=False),deadline_owner=timer)
            self.assertEqual(SPEC.capability,client.check_schema()['capability'])
            with self.assertRaises(ProbeError):
                client._validate(cycle.STANDARD_PROTOCOL.query,dict(run_id=RUN,mode='trial_support'))

    def test_old_eight_and_new_nine_payloads_are_closed(self):
        common=dict(state='completed',terminal=True,workers_drained=True,input_state=0,
            ui_frozen=False,native_inflight=False,cycle=companion(),
            notification=dict(authorization='authorized',state='requested'))
        def wire(spec,value):return dict(schema=spec.schema,profile=spec.profile,
            mode='status',run_id=RUN,payload=value)
        self.assertEqual(8,len(cycle.status(wire(cycle.STANDARD_PROTOCOL,common),RUN)))
        fresh=dict(common,irregular=status_value(proof_capture_id=7,before_capture_id=6,
            live_baseline_capture_id=5))
        self.assertEqual(9,len(cycle.status(wire(SPEC,fresh),RUN,protocol_spec=SPEC)))
        for spec,value in ((cycle.STANDARD_PROTOCOL,fresh),(SPEC,common)):
            with self.subTest(profile=spec.profile),self.assertRaises(ProbeError):
                cycle.status(wire(spec,value),RUN,protocol_spec=spec)
        for key,bad in (('episode_id',True),('prefix',-1),('durable_ns',1.5),
                        ('kind','trapped'),('stage','resume'),('held_reason','timeout'),('extra',0)):
            with self.subTest(key=key),self.assertRaises(ProbeError):
                cycle.status(wire(SPEC,dict(fresh,irregular=dict(fresh['irregular'],**{key:bad}))),RUN,protocol_spec=SPEC)

    def test_kind5_is_not_move_credit_and_is_refused_by_old_snapshot_parser(self):
        controller=dict(events=[dict(id=1,kind=5,direction=0,outcome=2,motion=0,dx=0,dy=0)],
            motion_references=[],moves=0,restarts=0,completed_shops=0,last_completed_id=1)
        original=copy.deepcopy(controller)
        irregular.validate_controller(controller,allow_irregular=True)
        self.assertEqual(original,controller)
        with self.assertRaises(ProbeError):irregular.validate_controller(controller,allow_irregular=False)
        for changes in (dict(direction=1),dict(motion=1),dict(dx=1),dict(dy=True)):
            bad=copy.deepcopy(controller);bad['events'][0].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ProbeError):
                irregular.validate_controller(bad,allow_irregular=True)
        bad=copy.deepcopy(controller);bad['motion_references']=[dict(command_id=1)]
        with self.assertRaises(ProbeError):irregular.validate_controller(bad,allow_irregular=True)

    def test_observation_fields_and_positive_geometry_are_closed(self):
        for kind in (0,1,2,3):self.assertEqual(kind,irregular.validate_observation(observation(kind))['kind'])
        for change in (dict(struct_size=240),dict(kind=4),dict(matches=True),
                       dict(heart_inter=[374]*2),dict(enemy_mask=16),dict(extra=0)):
            value=observation(1);value.update(change)
            with self.subTest(change=change),self.assertRaises(ProbeError):irregular.validate_observation(value)
        for kind,change in ((1,dict(heart_dark=[191]*3)),(1,dict(left=311)),
                            (2,dict(matches=2)),(3,dict(enemy_heart_count=[0,4,0,0]))):
            value=observation(kind);value.update(change)
            with self.subTest(kind=kind,change=change),self.assertRaises(ProbeError):irregular.validate_observation(value)

    def test_records_preserve_same_capture_roles_but_refuse_mismatched_hash(self):
        sequence=death_episode()
        for kind,value in sequence:irregular.validate_record(kind,value)
        kind,value=copy.deepcopy(sequence[3])
        self.assertEqual(value['frames'][1]['capture_id'],value['frames'][2]['capture_id'])
        value['frames'][2]['rgba_sha256']='e'*64
        with self.assertRaises(ProbeError):irregular.validate_record(kind,value)
        for field,maximum in (('raw_slots',44),('raw_bytes',64*1024*1024),('pin_slots',24),
            ('episode_metadata_bytes',224*1024),('final_metadata_bytes',1080*1024)):
            kind,value=copy.deepcopy(sequence[0]);value['resources'][field]=maximum+1
            with self.subTest(field=field),self.assertRaises(ProbeError):irregular.validate_record(kind,value)

    def test_checkpoint_without_completed_restart_stays_pending(self):
        for case in ('checkpoint','pending','continued','unknown','complete'):
            sequence=death_episode(case);frames={}
            for _,value in sequence:
                for row in value['frames']:
                    frames[row['capture_id']]=dict(raw_sha256=row['rgba_sha256'],metadata=dict(
                        capture_start_ns=row['start_ns'],capture_end_ns=row['end_ns'],
                        completed_prefix_start=row['prefix'],completed_prefix_end=row['prefix'],
                        generation=row['generation'],stable_prefix=True,inflight_start=False,inflight_end=False))
            result=irregular.sequence_summary(sequence,frames)
            with self.subTest(case=case):
                self.assertEqual(case!='complete',result['pending'],
                    'an irregular episode cannot authorize another run before its restart outcome is durable')
                self.assertEqual(case=='unknown',result['unknown_ack'])

    def test_sequence_refuses_wrong_epoch_prefix_ack_order_and_raw_binding(self):
        for fault in ('missing_checkpoint','repeat_intent','changed_epoch','wrong_prefix',
                      'early_outcome','wrong_raw','inflight','continue_after_unknown'):
            sequence=death_episode();frames={}
            for _,value in sequence:
                for row in value['frames']:
                    frames[row['capture_id']]=dict(raw_sha256=row['rgba_sha256'],metadata=dict(
                        capture_start_ns=row['start_ns'],capture_end_ns=row['end_ns'],
                        completed_prefix_start=row['prefix'],completed_prefix_end=row['prefix'],
                        generation=row['generation'],stable_prefix=True,inflight_start=False,inflight_end=False))
            if fault=='missing_checkpoint':sequence.pop(0)
            elif fault=='repeat_intent':sequence.insert(2,copy.deepcopy(sequence[1]))
            elif fault=='changed_epoch':sequence[1][1]['irregular']['episode_id']=2
            elif fault=='wrong_prefix':sequence[2][1]['irregular']['prefix']=2
            elif fault=='early_outcome':sequence[2][1]['ack']['completed_ns']=121
            elif fault=='wrong_raw':frames[2]['raw_sha256']='e'*64
            elif fault=='inflight':frames[2]['metadata']['inflight_end']=True
            elif fault=='continue_after_unknown':sequence[2][1]['ack']['outcome']='unknown'
            with self.subTest(fault=fault),self.assertRaises(ProbeError):irregular.sequence_summary(sequence,frames)

    def test_stalled_checkpoint_preserves_both_observations_and_source_identity(self):
        kind,value=stalled_upgrade()[0]
        irregular.validate_record(kind,value)
        for fault in ('zero1','zero2','before','missing_observation','changed_observation','non_move_ack'):
            bad=copy.deepcopy(value)
            if fault=='zero1':bad['irregular']['proof_capture_id']=4
            elif fault=='zero2':bad['irregular']['trigger_capture_id']=3
            elif fault=='before':bad['irregular']['before_capture_id']=1
            elif fault=='missing_observation':bad['observations'].pop()
            elif fault=='changed_observation':bad['observations'][0]['value']['enemy_body_luma'][1]+=1
            elif fault=='non_move_ack':bad['ack']['kind']=5
            with self.subTest(fault=fault),self.assertRaises(ProbeError):irregular.validate_record(kind,bad)

    def test_only_durable_unreserved_stalled_episode_can_upgrade_to_fresh_death(self):
        sequence=stalled_upgrade()
        accepted=False
        try:accepted=irregular.sequence_summary(sequence,raw_frames(sequence))['pending']
        except ProbeError:pass
        self.assertTrue(accepted,'the durable original stalled evidence must admit its fresh death upgrade')
        for fault in ('wrong_epoch','changed_deadline','not_durable','pause_already_acked',
                      'wrong_stage','no_fresh_death','death_to_stalled'):
            bad=copy.deepcopy(sequence);state=bad[1][1]['irregular']
            if fault=='wrong_epoch':state['episode_id']=2
            elif fault=='changed_deadline':state['parent_deadline_ns']+=1
            elif fault=='not_durable':state['durable_ns']=0
            elif fault=='pause_already_acked':state['pause_capture_id']=6
            elif fault=='wrong_stage':state['stage']='wait_restart'
            elif fault=='no_fresh_death':bad[1][1]['observations']=[]
            elif fault=='death_to_stalled':bad[0][1]['irregular']['kind']='death'
            with self.subTest(fault=fault),self.assertRaises(ProbeError):irregular.sequence_summary(bad,raw_frames(bad))

    def test_physical_count_bounds_reject_impossible_positive_and_none_observations(self):
        invalid=[]
        for kind,changes in ((1,dict(glyph_intersection=100000,glyph_union=0)),
            (1,dict(glyph_intersection=523)),(1,dict(glyph_union=500)),
            (0,dict(glyph_union=6481)),(0,dict(left=897)),(0,dict(width=897)),
            (0,dict(heart_inter=[383,0,0],heart_union=[400,0,0])),
            (0,dict(heart_union=[626,0,0])),(0,dict(heart_red=[307,0,0])),
            (0,dict(heart_dark=[307,0,0])),(0,dict(heart_bright=[307,0,0])),
            (0,dict(enemy_inter=[1,0,0,0])),(0,dict(enemy_union=[5305,0,0,0])),
            (0,dict(enemy_heart_count=[4,0,0,0])),(0,dict(enemy_width=[897,0,0,0])),
            (0,dict(enemy_body_luma=[697,0,0,0])),
            (0,dict(enemy_body_saturation=[697,0,0,0])),
            (3,dict(hud_mask=0)),(2,dict(glyph_intersection=224,glyph_union=224))):
            value=observation(kind);value.update(changes);invalid.append(value)
        for index,value in enumerate(invalid):
            with self.subTest(index=index),self.assertRaises(ProbeError):irregular.validate_observation(value)
        partial=observation(1);partial.update(kind=0,empty_hearts=0,heart_red=[0]*3,
            heart_dark=[0]*3,heart_bright=[0]*3)
        self.assertEqual(partial,irregular.validate_observation(partial),
            'a bounded death-present diagnostic without empty hearts remains non-authoritative NONE')

    def test_limit_episode_thirteen_is_exportable_diagnostic_without_extra_retry_authority(self):
        state=status_value(kind='death',stage='held',held_reason='limit',episodes=13,
            episode_id=13,trigger_capture_id=2,trigger_ns=100,parent_deadline_ns=1000)
        accepted=False
        try:accepted=irregular.validate_status(state)==state
        except ProbeError:pass
        self.assertTrue(accepted,'the C limit hold for the thirteenth trigger must remain collectible')
        with self.assertRaises(ProbeError):irregular.validate_status(dict(state,episodes=2**31))

    def test_proof_ids_and_clocks_are_typed_and_none_enemy_is_not_positive(self):
        kind,value=stalled_upgrade()[0]
        for field in ('capture_id','start_ns','end_ns'):
            bad=copy.deepcopy(value);bad['proofs'][0][field]=True
            with self.subTest(field=field),self.assertRaises(ProbeError):irregular.validate_record(kind,bad)
        bad=copy.deepcopy(value)
        bad['proofs'][0]['enemy']['kind']=0;bad['observations'][0]['value']['kind']=0
        with self.assertRaises(ProbeError):irregular.validate_record(kind,bad)

    def test_outcome_state_command_and_capture_ids_bind_exact_action_and_role(self):
        sequence=death_episode()
        for index,field in ((2,'continue_command_id'),(2,'continue_capture_id'),
                            (4,'restart_command_id'),(4,'next_floor_capture_id')):
            kind,value=copy.deepcopy(sequence[index]);value['irregular'][field]=999
            with self.subTest(field=field),self.assertRaises(ProbeError):irregular.validate_record(kind,value)

    def test_intent_state_command_ids_bind_exact_action(self):
        for index,field in ((1,'continue_command_id'),(3,'restart_command_id')):
            sequence=death_episode();kind,value=sequence[index]
            value['irregular'][field]=999
            with self.subTest(field=field,boundary='record'),self.assertRaises(ProbeError):
                irregular.validate_record(kind,value)
            with self.subTest(field=field,boundary='sequence'),self.assertRaises(ProbeError):
                irregular.sequence_summary(sequence,raw_frames(sequence))

    def test_fixture_uses_c_restart_level_move_only_inputs_and_unknown_event_identity(self):
        complete=native_model(RUN,'complete');controller=complete['terminal']['controller']
        self.assertEqual((1,0,2),(controller['restarts'],controller['inputs'],controller['last_completed_id']))
        self.assertEqual((2,2),(complete['cycle']['level_id'],complete['cycle']['prefix']))
        continued=native_model(RUN,'continued');controller=continued['terminal']['controller']
        self.assertEqual((0,0,1),(controller['restarts'],controller['inputs'],controller['last_completed_id']),
            'DEATH_CONTINUE alone is not a restart or a direction input')
        self.assertEqual((1,1),(continued['cycle']['level_id'],continued['cycle']['prefix']))
        self.assertEqual(5,controller['events'][0]['kind']);self.assertEqual(2,controller['events'][0]['outcome'])
        unknown=native_model(RUN,'unknown');controller=unknown['terminal']['controller']
        self.assertEqual((0,0,0),(controller['restarts'],controller['inputs'],controller['last_completed_id']))
        self.assertEqual(4,controller['events'][0]['outcome'],'UNKNOWN input is outcome 4; NOTSENT is 3')


class IrregularPublication110Tests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='irregular110-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.base=self.root/'local'/'test-110';self.base.mkdir(parents=True)
        self.destination=self.root/'mounted';self.destination.mkdir();self.server=IrregularServer(self.base)

    def invoke(self,**kwargs):
        original=native_walk.device_lock
        with patch('necroprobe.native_cycle.device_lock',lambda path=None:original(path or self.root/'device.lock')):
            return campaign.run(self.server,self.destination,spool=self.base,notice=lambda _:None,
                protocol_spec=SPEC,**kwargs)

    def starts(self):return [p['run_id'] for m,p in self.server.calls if m=='necro_native_start']

    def test_whole_native_kind5_evidence_survives_journal_and_archive_unchanged(self):
        result=self.invoke(until_target=True);record=result['record'];run_id=record['run_id']
        model=self.server.models[run_id]
        self.assertTrue(record['published']);self.assertEqual(1,len(self.starts()))
        self.assertEqual(record,cycle.load_journal(self.base,protocol_spec=SPEC))
        self.assertEqual((SPEC.revision,PROFILE),(record['revision'],record['profile']))
        row=result['ledger']['runs'][0]
        self.assertEqual(('unassessed',1,0),(row['outcome'],row['restarts'],row['moves']))
        self.assertEqual('unassessed',row['stop_reason'])
        self.assertEqual(model['manifest'],cycle.verify_evidence(self.base,record,protocol_spec=SPEC))
        with zipfile.ZipFile(result['archive']) as saved:
            manifest=next(n for n in saved.namelist() if n.endswith('native-manifest.json'))
            self.assertEqual(cycle.canonical(model['manifest']),saved.read(manifest))
            records={Path(n).name:saved.read(n) for n in saved.namelist() if '/records/' in n}
            for item in model['manifest']['records']:
                self.assertEqual(model['records'][item['sequence']],records[cycle.record_name(item)])
        self.assertTrue(all(m in ('schema','necro_native_start',QUERY) for m,_ in self.server.calls))
        self.assertTrue(result['campaign_archive'].is_file())

    def test_cross_profile_journal_read_and_client_spec_are_refused_before_network(self):
        cycle._journal(self.base,cycle.fresh_record(RUN,protocol_spec=SPEC))
        with self.assertRaisesRegex(ProbeError,'cycle_journal_invalid'):cycle.load_journal(self.base)
        with self.assertRaisesRegex(ProbeError,'cycle_protocol_invalid'):
            publication.run(self.server,self.destination,spool=self.base,notice=lambda _:None)
        self.assertEqual([],self.server.calls)
        cycle._journal(self.base,cycle.fresh_record(RUN))
        with self.assertRaisesRegex(ProbeError,'cycle_journal_invalid'):
            cycle.load_journal(self.base,protocol_spec=SPEC)

    def test_missing_capability_starts_zero_and_no_game_identity_is_replaced(self):
        self.server.schema_error='native_capability_missing'
        result=self.invoke()
        self.assertEqual([],self.starts());self.assertFalse(result['record']['start_intent'])
        original=result['record']['run_id'];self.server.schema_error=None
        next_result=self.invoke()
        self.assertEqual([original],self.starts());self.assertTrue(next_result['record']['published'])

    def test_unknown_start_and_export_failure_recover_same_uuid_without_resend(self):
        self.server.fail_start=True
        first=self.invoke();self.assertEqual(1,len(self.starts()))
        run_id=first['record']['run_id'];self.assertTrue(first['record']['start_intent'])
        self.server.fail_chunk=True
        second=self.invoke(recovery_only=True)
        self.assertEqual(run_id,second['record']['run_id']);self.assertFalse(second['record']['published'])
        third=self.invoke(recovery_only=True)
        self.assertEqual([run_id],self.starts());self.assertTrue(third['record']['published'])
        self.assertEqual(run_id,third['record']['run_id'])
        recovery_status=[p for m,p in self.server.calls if m==QUERY and p.get('mode')=='status']
        self.assertTrue(recovery_status and all(p['keepalive'] is False for p in recovery_status))

    def test_unknown_ack_and_dangling_intent_do_not_authorize_campaign_next_start(self):
        for case,reason in (('checkpoint','irregular_pending'),('pending','irregular_pending'),
                            ('continued','irregular_pending'),('unknown','unknown_input')):
            with self.subTest(case=case):
                self.server.case=case
                result=self.invoke(until_target=True)
                self.assertTrue(result['record']['published'])
                self.assertEqual(reason,result['stop_reason'])
                self.assertEqual('unknown',result['ledger']['runs'][-1]['outcome'])
                self.assertEqual(1,len(self.starts()))
                # Use another install namespace; the preserved run is never rewritten.
                self.base=self.root/('local-'+case)/'test-110';self.base.mkdir(parents=True)
                self.server=IrregularServer(self.base)

    def test_irregular_positive_hint_is_unadopted_candidate_and_never_shop_credit(self):
        for outcome,expected in (('target','candidate'),('candidate','candidate'),
                                 ('unknown','unknown'),('negative','unknown')):
            self.server.case='hint_'+outcome
            result=self.invoke(until_target=True);row=result['ledger']['runs'][0]
            with self.subTest(outcome=outcome):
                self.assertEqual(expected,row['outcome'])
                self.assertFalse(row['assessment_adopted']);self.assertEqual(0,row['restarts'])
                self.assertEqual(1,len(self.starts()))
                if expected=='candidate':
                    self.assertEqual('candidate',result['stop_reason'])
                    self.assertIn('未採用の解析結果',trial.irregular_result_notice(self.base,result['record'],row))
            self.base=self.root/('hint-'+outcome)/'test-110';self.base.mkdir(parents=True)
            self.server=IrregularServer(self.base)

    def test_hint_cannot_bind_other_capture_prefix_or_untyped_job(self):
        kind,value=death_episode()[0]
        value['assessment_hint']=dict(job_id=9,capture_id=1,prefix=0,status='ok',outcome='target')
        irregular.validate_record(kind,value)
        for field,bad in (('job_id',True),('job_id',0),('capture_id',99),('prefix',2),('outcome','absent')):
            changed=copy.deepcopy(value);changed['assessment_hint'][field]=bad
            with self.subTest(field=field,value=bad),self.assertRaises(ProbeError):irregular.validate_record(kind,changed)

    def test_new_profile_keeps_proved_normal_negative_campaign_handoff_until_target(self):
        self.server.cases=['normal:negative_limit','normal:target']
        result=self.invoke(until_target=True)
        self.assertEqual('target',result['stop_reason'])
        self.assertEqual(2,len(set(self.starts())))
        self.assertEqual(['negative','target'],[row['outcome'] for row in result['ledger']['runs']])
        first=self.starts()[0]
        published=next(i for i,(method,p) in enumerate(self.server.calls) if method==QUERY
            and p.get('mode')=='published' and p['run_id']==first)
        next_start=next(i for i,(method,p) in enumerate(self.server.calls)
            if method=='necro_native_start' and p['run_id']!=first)
        self.assertLess(published,next_start)
        self.assertEqual('完全対象なし',trial.irregular_result_notice(self.base,
            cycle.json_object((self.base/('cycle-'+first)/'journal.json').read_bytes()),
            result['ledger']['runs'][0]).split('商品判定: ')[1].split('。')[0])

    def test_manifest_session_provenance_and_raw_hash_mismatch_refuse_authority(self):
        result=self.invoke();record=result['record'];model=self.server.models[record['run_id']]
        wrong=copy.deepcopy(model['manifest']);wrong['profile']=cycle.PROFILE
        raw=cycle.canonical(wrong)
        wire=self.server.wrap(record['run_id'],'manifest',dict(export_id=wrong['export_id'],
            manifest_sha256=sha(raw),manifest_json=raw.decode()))
        with self.assertRaises(ProbeError):cycle.read_manifest(wire,record['run_id'],protocol_spec=SPEC)
        header=next(i for i in record['records'] if i['kind']=='session')
        path=self.base/('cycle-'+record['run_id'])/'records'/cycle.record_name(header)
        raw=path.read_bytes();body=json.loads(raw);body['provenance']['native_profile']=cycle.PROFILE
        replaced=cycle.canonical(body);path.write_bytes(replaced)
        with self.assertRaisesRegex(ProbeError,'cycle_file_changed'):
            cycle.verify_evidence(self.base,record,protocol_spec=SPEC)
        path.write_bytes(raw)
        self.assertEqual(model['manifest'],cycle.verify_evidence(self.base,record,protocol_spec=SPEC))

    def test_every_irregular_referenced_png_is_required_before_publication(self):
        for capture in range(1,7):
            model=native_model(RUN);manifest=model['manifest']
            removed=next(item for item in manifest['images'] if item['capture_id']==capture)
            manifest['images'].remove(removed);manifest['total_bytes']-=removed['bytes']
            base=self.root/('missing-'+str(capture))/'test-110';base.mkdir(parents=True)
            record=store_model(base,model)
            with self.subTest(capture=capture),self.assertRaises(ProbeError):
                cycle.verify_evidence(base,record,protocol_spec=SPEC)

    def test_missing_irregular_png_preserves_original_run_without_publication_or_restart(self):
        self.server.omit_capture_id=2
        try:self.invoke(until_target=True)
        except ProbeError:pass
        self.assertEqual(0,sum(p.get('mode')=='published' for _,p in self.server.calls),
            'a missing referenced PNG must be detected before publishing the incomplete archive')
        first=cycle.load_journal(self.base,protocol_spec=SPEC);run_id=first['run_id']
        self.assertTrue(first['start_intent']);self.assertFalse(first['published'])
        self.assertEqual([run_id],self.starts())
        folder=self.base/('cycle-'+run_id)
        original={path.relative_to(folder).as_posix():sha(path.read_bytes()) for path in folder.rglob('*')
            if path.is_file() and path.name not in ('journal.json','archive-journal.json')}
        again=self.invoke(recovery_only=True)
        self.assertEqual(run_id,again['record']['run_id']);self.assertFalse(again['record']['published'])
        self.assertEqual([run_id],self.starts())
        self.assertEqual(0,sum(p.get('mode')=='published' for _,p in self.server.calls))
        for name,digest in original.items():self.assertEqual(digest,sha((folder/name).read_bytes()))

    def test_old_diagnostic_manifest_may_omit_png_without_new_irregular_requirement(self):
        from test_campaign099 import native_model as old_fixture
        model=old_fixture(RUN,'unknown');manifest=model['manifest']
        omitted=manifest['images'].pop(0);manifest['total_bytes']-=omitted['bytes']
        manifest.update(complete=False,interrupted=True,diagnostics=[dict(code='png_omitted',authority=False)])
        record=store_model(self.base,model,protocol=cycle.STANDARD_PROTOCOL)
        self.assertEqual(manifest,cycle.verify_evidence(self.base,record))

    def test_hash_valid_cross_profile_session_and_old_kind5_records_are_rejected(self):
        for fault in ('missing_profile','unknown_profile','old_profile','old_kind5','old_companion'):
            model=native_model(RUN)
            protocol=cycle.STANDARD_PROTOCOL if fault.startswith('old_') and fault!='old_profile' else SPEC
            if fault=='missing_profile':
                body=json.loads(model['records'][0]);body.pop('provenance')
                replace_fixture_record(model,0,body)
            elif fault in ('unknown_profile','old_profile'):
                body=json.loads(model['records'][0]);body['provenance']['native_profile']='alien' if fault=='unknown_profile' else cycle.PROFILE
                replace_fixture_record(model,0,body)
            else:
                model['manifest']['profile']=protocol.profile
                body=json.loads(model['records'][0]);body['provenance']['native_profile']=protocol.profile
                replace_fixture_record(model,0,body)
                # A sole ordinary terminal keeps profile/kind checks independent.
                body=json.loads(model['records'][6]);body.update(sequence=1,previous=None)
                body['payload'] = dict(controller=body['payload']['controller']) if fault=='old_kind5' else dict(irregular=status_value())
                model['records']={0:model['records'][0],1:cycle.canonical(body)}
                model['manifest'].update(images=[],records=[dict(sequence=s,kind=k,cycle=0,
                    bytes=len(model['records'][s]),sha256=sha(model['records'][s])) for s,k in ((0,'session'),(1,'terminal'))],
                    total_bytes=sum(map(len,model['records'].values())))
            base=self.root/fault/'test-110';base.mkdir(parents=True)
            record=store_model(base,model,protocol=protocol)
            with self.subTest(fault=fault),self.assertRaises(ProbeError):
                cycle.verify_evidence(base,record,protocol_spec=protocol)

    def test_archive_snapshot_cannot_disguise_its_selected_profile_or_revision(self):
        record=store_model(self.base,native_model(RUN))
        snapshot=self.base/('cycle-'+RUN)/'archive-journal.json'
        storage=self.root/'archive';storage.mkdir()
        for key,value in (('profile',cycle.PROFILE),('revision',cycle.REVISION)):
            snapshot.write_bytes(cycle.canonical(dict(record,**{key:value})))
            with self.subTest(key=key),self.assertRaises(ProbeError):
                publication.build_archive(self.base,record,storage,protocol_spec=SPEC)
            archive=storage/(RUN+'.zip')
            if archive.exists():archive.unlink()

    def test_test110_entry_selects_new_protocol_and_old_entry_stays_default(self):
        from necroprobe import test099,test110
        with patch('sys.stdout',new_callable=io.StringIO) as printed:
            self.assertEqual(0,test110.main(['--check']))
        self.assertEqual('native-irregular-trial-v1 / '+cycle.API_VERSION,printed.getvalue().strip())
        with patch('sys.stdout',new_callable=io.StringIO) as printed:
            self.assertEqual(0,test099.main(['--check']))
        self.assertEqual('native-trial-v1 / '+cycle.API_VERSION,printed.getvalue().strip())

    def test_new_notice_distinguishes_unknown_negative_target_and_retry_hold(self):
        self.server.case='unknown';result=self.invoke();row=result['ledger']['runs'][0]
        notice=trial.irregular_result_notice(self.base,result['record'],row)
        self.assertIn('商品判定: UNKNOWN',notice)
        self.assertIn('death / held / unknown_input',notice)
        for outcome,adopted,label in (('negative',True,'完全対象なし'),
            ('negative',False,'UNKNOWN'),('target',True,'のろいのゆびわ確認'),
            ('target',False,'のろいのゆびわ候補を保持（未採用の解析結果）'),
            ('candidate',False,'のろいのゆびわ候補を保持（未採用の解析結果）'),('unassessed',False,'未判定')):
            with self.subTest(outcome=outcome,adopted=adopted):
                notice=trial.irregular_result_notice(self.base,result['record'],
                    dict(row,outcome=outcome,assessment_adopted=adopted))
                self.assertIn('商品判定: '+label+'。',notice)


if __name__ == '__main__':
    unittest.main()
