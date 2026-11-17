"""TEST112 published restart-yield proofs; synthetic records, no game/native run."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from necroprobe import native_cycle as cycle
from necroprobe import trial_evidence099 as trial
from necroprobe import campaign099 as campaign, native_walk
from unittest.mock import patch
from necroprobe.validation import ProbeError
from test_native_cycle_client094 import companion, png
from test_native_irregular_client110 import replace_fixture_record, store_model, IrregularServer, status_value

RUN = 'a' * 32
SPEC = cycle.IRREGULAR_PROTOCOL


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def restart_yield_model(run_id=RUN, *, data=True, data_outcome='unknown'):
    """Independent protocol record factory, retaining the old and new jobs."""
    negative = companion()
    negative.update(state='negative_persist', level_id=1, job_id=1, capture_id=10,
        capture_start_ns=100, prefix=4, worker_started_ns=105, assessment_ns=110,
        deadline_ns=250, durable_ns=0, completed_shops=1,
        pause_source_capture_id=11, pause_capture_id=12,
        outcome='negative', assessment_status='ok', coverage='complete', full_seen=True)
    checkpoint = dict(run_id=run_id, clock_id='e'*32, generation=7,
        capture_ids=[10,11,12], cycle=copy.deepcopy(negative),
        assessment=dict(status='ok', outcome='negative', coverage='complete'),
        assessment_adopted=True, raw_sha256='c'*64)
    intent_state = copy.deepcopy(negative)
    intent_state.update(state='negative_restart', durable_ns=165,
        pause_source_capture_id=11, pause_capture_id=12, restart_command_id=6)
    command = dict(id=6, ordinal=1, target_ns=180, not_before_ns=175, deadline_ns=195,
        source_capture_id=13, source_start_ns=170, phase_sample_ns=170,
        kind=3, direction=0, x=144, y=448)
    intent = dict(cycle=copy.deepcopy(intent_state), command=command, generation=7,
        source_prefix=5, source_raw_sha256='c'*64)
    outcome_state = copy.deepcopy(intent_state)
    outcome_state.update(intent_ns=180, next_floor_capture_id=20)
    events = [dict(id=5, kind=2, outcome=2, reason=0, source_capture_id=11,
        source_start_ns=140, begin_ns=150, end_ns=151, observed_capture_id=12),
        dict(id=6, kind=3, outcome=2, reason=0, source_capture_id=13,
        source_start_ns=170, begin_ns=182, end_ns=183, observed_capture_id=20)]
    outcome = dict(cycle=copy.deepcopy(outcome_state), generation=7,
        floor_capture_id=20, floor_prefix=6, floor_raw_sha256='c'*64,
        controller=dict(events=copy.deepcopy(events), inputs=3, moves=3, restarts=1,
                        last_completed_id=6, x=0, y=0))
    current = companion()
    current.update(level_id=2, completed_shops=1, state='done', prefix=6,
        full_seen=data, job_id=2 if data else 0, capture_id=20 if data else 0,
        capture_start_ns=200 if data else 0, worker_started_ns=205 if data else 0,
        assessment_ns=210 if data else 0, deadline_ns=350 if data else 0,
        outcome=data_outcome if data else 'unknown',
        assessment_status='ok', coverage='incomplete')
    events.append(dict(id=7, kind=2, outcome=2, reason=0, source_capture_id=21,
        source_start_ns=220, begin_ns=230, end_ns=231, observed_capture_id=22))
    handoff = dict(schema='ngg2-trial-handoff-v1', kind='restarted_budget', allowed=True,
        reason=14, qualified_ns=225, source_capture_id=21, source_prefix=6,
        pause_capture_id=22, completed_prefix=7)
    controller = dict(terminal=1, phase=7, paused=1, input_state=0, current_command_id=0,
        last_completed_id=7, last_capture_id=22, started_ns=2, ended_ns=250,
        walk_started_ns=80, reason=14, restarts=1, inputs=3, moves=3,
        x=0, y=0, events=events, handoff=handoff)
    terminal = dict(cycle=current, controller=controller,
        assessment=dict(status='ok', outcome=data_outcome, coverage='incomplete') if data else None,
        assessment_adopted=False)
    chain = [('checkpoint', checkpoint), ('restart_intent', intent),
             ('restart_outcome', outcome), ('terminal', terminal)]
    raw_png = png()
    records = {0:cycle.canonical(dict(schema='ngg2-cycle-spool-v1', run_id=run_id,
        owner_sha256='d'*64, provenance=dict(native_profile=SPEC.profile,
            yield_after_restart=True, accepted_started_ns=1, generation=7,
            clock_id='e'*32, runtime_instance_id='f'*32, system_uptime_ns=1)))}
    kinds = [(0, 'session', 0)]; previous = None
    for sequence, (name, payload) in enumerate(chain, 1):
        body = dict(schema='ngg2-cycle-record-v1', run_id=run_id, sequence=sequence,
            kind=name, cycle=1, previous=previous, payload=payload)
        records[sequence] = cycle.canonical(body); previous = sha(records[sequence])
        kinds.append((sequence, name, 1))
    for sequence, (capture, start, prefix) in enumerate(((10,100,4), (11,140,4),
            (12,160,5), (13,170,5), (20,200,6), (21,220,6), (22,240,7)), 513):
        metadata = dict(capture_id=capture, capture_start_ns=start, capture_end_ns=start+1,
            completed_prefix_start=prefix, completed_prefix_end=prefix, stable_prefix=True,
            inflight_start=False, inflight_end=False, generation=7, pixel_width=896, pixel_height=414)
        records[sequence] = cycle.canonical(dict(schema='ngg2-cycle-frame-v1', run_id=run_id,
            capture_id=capture, raw_sha256='c'*64, raw_bytes=896*414*4, metadata=metadata))
        kinds.append((sequence, 'frame', 0))
    images = [dict(name='capture-'+str(c).zfill(6)+'.png', capture_id=c,
        bytes=len(raw_png), sha256=sha(raw_png), raw_sha256='c'*64, width=896, height=414)
        for c in (10,11,12,13,20,21,22)]
    manifest = dict(schema='ngg2-cycle-manifest-v1', run_id=run_id, profile=SPEC.profile,
        export_id=sha(run_id.encode())[:32], complete=True, interrupted=False, terminal=True,
        workers_drained=True, input_state=0, native_inflight=False, ui_frozen=False,
        images=images, records=[dict(sequence=s, kind=k, cycle=n,
            bytes=len(records[s]), sha256=sha(records[s])) for s,k,n in kinds], diagnostics=[],
        total_bytes=len(images)*len(raw_png)+sum(map(len,records.values())), chunk_bytes=cycle.CHUNK_BYTES)
    return dict(image=raw_png, records=records, manifest=manifest, irregular=status_value(),
                terminal=terminal, cycle=current, published=False)


def revise(model, sequence, change):
    body = json.loads(model['records'][sequence]); change(body)
    replace_fixture_record(model, sequence, body)


def inspect_opted_in(base, record):
    # The unchanged parser is a runnable before-implementation oracle. Missing
    # the new behavior produces an assertion failure, not a keyword error.
    if 'allow_restarted_budget' in inspect.signature(trial.inspect_run).parameters:
        return trial.inspect_run(base, record, protocol_spec=SPEC, allow_restarted_budget=True)
    return trial.inspect_run(base, record, protocol_spec=SPEC)


class RestartYieldParser112Tests(unittest.TestCase):
    def inspect(self, model=None, *, opted_in=True, cancelled=False, published=True):
        model = restart_yield_model() if model is None else model
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);record=store_model(base,model,protocol=SPEC)
            record.update(published=published,cancel_intent=cancelled);cycle._journal(base,record)
            return (inspect_opted_in(base,record) if opted_in else
                    trial.inspect_run(base,record,protocol_spec=SPEC))

    def test_new_unknown_data_job_uses_old_restart_chain_but_reports_new_floor_unassessed(self):
        row=self.inspect()
        self.assertEqual(('handoff','unassessed',False),
            (row['stop_reason'],row['outcome'],row['assessment_adopted']))
        self.assertEqual('restarted_budget',row['handoff']['kind'])

    def test_precommit_outcome_keeps_old_shop_coordinates_until_durable_reset(self):
        model=restart_yield_model()
        # Runtime saves this snapshot before outcome fsync/commit resets C's
        # world origin. Three old moves can end at (-1,2); the final floor is 0,0.
        revise(model,3,lambda body:body['payload']['controller'].update(x=-1,y=2))
        row=self.inspect(model)
        self.assertEqual(('handoff','unassessed',False),
            (row['stop_reason'],row['outcome'],row['assessment_adopted']))
        revise(model,4,lambda body:body['payload']['controller'].update(x=-1))
        self.assertEqual('handoff_invalid',self.inspect(model)['stop_reason'],
            'Only the precommit diagnostic may keep old coordinates; terminal must be the new origin')

    def test_retained_previous_job_is_diagnostic_after_restart_and_never_new_floor_negative(self):
        model=restart_yield_model(data=False)
        def retained(body):
            state=body['payload']['cycle'];old=json.loads(model['records'][3])['payload']['cycle']
            state.update(job_id=old['job_id'],capture_id=old['capture_id'],capture_start_ns=old['capture_start_ns'],
                prefix=old['prefix'],worker_started_ns=old['worker_started_ns'],assessment_ns=old['assessment_ns'],
                outcome='negative',coverage='complete')
        revise(model,4,retained)
        row=self.inspect(model)
        self.assertEqual(('handoff','unassessed',False),(row['stop_reason'],row['outcome'],row['assessment_adopted']))

    def test_restart_can_use_a_fresh_pause_frame_acquired_before_checkpoint_commit(self):
        model=restart_yield_model()
        def intent(body):
            body['payload']['command'].update(source_capture_id=12,source_start_ns=160,phase_sample_ns=160)
        revise(model,2,intent)
        def actual_event(body):
            events=body['payload']['controller']['events']
            next(event for event in events if event['id']==6).update(source_capture_id=12,source_start_ns=160)
        revise(model,3,actual_event);revise(model,4,actual_event)
        self.assertEqual('handoff',self.inspect(model)['stop_reason'])

    def test_boolean_job_identity_cannot_alias_the_completed_negative_job(self):
        model=restart_yield_model()
        revise(model,3,lambda body:body['payload']['cycle'].update(job_id=True))
        self.assertNotEqual('handoff',self.inspect(model)['stop_reason'])

    def refused(self,model):
        try: row=self.inspect(model)
        except ProbeError: return
        self.assertNotEqual('handoff',row['stop_reason'])

    def test_explicit_parser_opt_in_and_immutable_session_flag_are_both_required(self):
        self.assertNotEqual('handoff',self.inspect(opted_in=False)['stop_reason'])
        for value in (None,False,1,'true'):
            model=restart_yield_model()
            def change(body):
                if value is None:body['provenance'].pop('yield_after_restart')
                else:body['provenance']['yield_after_restart']=value
            revise(model,0,change)
            with self.subTest(flag=value):self.refused(model)
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);record=store_model(base,restart_yield_model(),protocol=SPEC)
            record['published']=True
            for flag,protocol in ((1,SPEC),(True,cycle.STANDARD_PROTOCOL)):
                with self.subTest(flag=flag,profile=protocol.profile),self.assertRaises(ProbeError):
                    trial.inspect_run(base,record,protocol_spec=protocol,allow_restarted_budget=flag)

    def test_new_data_negative_and_adopted_ok_are_not_new_floor_absence(self):
        model=restart_yield_model(data_outcome='negative')
        def normal_commit(body):
            body['payload']['assessment_adopted']=True
            body['payload']['assessment']['coverage']='complete'
            body['payload']['cycle']['coverage']='complete'
        revise(model,4,normal_commit)
        row=self.inspect(model)
        self.assertEqual(('handoff','unassessed',False),(row['stop_reason'],row['outcome'],row['assessment_adopted']))
        self.assertEqual('handoff',self.inspect(restart_yield_model(data=False))['stop_reason'])

    def test_first_new_floor_can_itself_supply_the_fresh_pause_source(self):
        model=restart_yield_model()
        def source(body):
            value=body['payload']['controller'];value['handoff']['source_capture_id']=20
            value['events'][-1].update(source_capture_id=20,source_start_ns=200)
        revise(model,4,source)
        self.assertEqual('handoff',self.inspect(model)['stop_reason'])

    def test_all_positive_assessments_latches_and_late_hints_precede_yield(self):
        for role in ('target','candidate','old_checkpoint','sticky','late_hint'):
            model=restart_yield_model()
            def positive(body):
                value=body['payload']
                if role=='sticky':
                    value['cycle']['candidate_latched']=True;value['assessment']=None
                elif role=='late_hint':
                    value['assessment_hint']=dict(job_id=9,capture_id=20,prefix=6,status='deadline',outcome='target')
                else:
                    value['assessment']=dict(status='deadline',outcome='candidate' if role=='old_checkpoint' else role,coverage='incomplete')
                    value['assessment_adopted']=False
            revise(model,1 if role=='old_checkpoint' else 4,positive)
            with self.subTest(role=role):
                row=self.inspect(model);self.assertIn(row['outcome'],('candidate','target'))
                self.assertEqual(row['outcome'],row['stop_reason']);self.assertIsNone(row['handoff'])

    def test_nested_row_slot_and_partial_outcomes_cannot_hide_a_positive_or_invalid_row(self):
        observed=[]
        cases=(dict(rows=[dict(outcome='target',slots=[])]),
               dict(rows=[dict(outcome='candidate',slots=[])]),
               dict(rows=[dict(outcome='unknown',slots=[dict(outcome='target')])]),
               dict(rows=[dict(outcome='unknown',slots=[dict(outcome='candidate')])]),
               dict(partial=[dict(outcome='target')]),
               dict(rows=[dict(outcome='invalid',slots=[])]))
        for fields in cases:
            model=restart_yield_model()
            revise(model,4,lambda body:body['payload']['assessment'].update(fields))
            observed.append(self.inspect(model)['stop_reason'])
        self.assertEqual(['candidate']*5+['handoff_invalid'],observed)

    def test_old_complete_negative_checkpoint_and_its_raw_identity_are_required(self):
        changes=[lambda p:p.update(assessment_adopted=False),
            lambda p:p['assessment'].update(outcome='unknown'),
            lambda p:p['assessment'].update(coverage='incomplete'),
            lambda p:p['assessment'].update(status='deadline'),
            lambda p:p.update(raw_sha256='a'*64),
            lambda p:p.update(clock_id='0'*32),
            lambda p:p.update(generation=8)]
        for index,change in enumerate(changes):
            model=restart_yield_model();revise(model,1,lambda body:change(body['payload']))
            with self.subTest(index=index):self.refused(model)

    def test_checkpoint_intent_outcome_records_cannot_be_omitted_or_reordered(self):
        for sequence in (1,2,3):
            model=restart_yield_model()
            revise(model,sequence,lambda body:body.update(kind='assessment'))
            next(item for item in model['manifest']['records'] if item['sequence']==sequence)['kind']='assessment'
            with self.subTest(missing=sequence):self.refused(model)
        model=restart_yield_model()
        def wrong_time(body):body['payload']['cycle']['intent_ns']=190
        revise(model,3,wrong_time);self.refused(model)

    def test_restart_command_outcome_generation_and_floor_roles_are_exact(self):
        faults=[(2,lambda p:p['command'].update(id=5)),
            (2,lambda p:p['command'].update(kind=2)),
            (2,lambda p:p.update(generation=True)),
            (2,lambda p:p.update(source_raw_sha256='a'*64)),
            (2,lambda p:p.update(source_prefix=6)),
            (3,lambda p:p.update(floor_prefix=5)),
            (3,lambda p:p.update(floor_raw_sha256='a'*64)),
            (3,lambda p:p['cycle'].update(next_floor_capture_id=21)),
            (3,lambda p:p['cycle'].update(outcome_ns=202)),
            (3,lambda p:p['controller'].update(inputs=4)),
            (4,lambda p:p['controller']['events'][1].update(observed_capture_id=21))]
        for index,(sequence,change) in enumerate(faults):
            model=restart_yield_model();revise(model,sequence,lambda body:change(body['payload']))
            with self.subTest(index=index):self.refused(model)

    def test_no_move_resume_restart_or_unknown_input_can_follow_the_restart(self):
        for kind,outcome in ((4,2),(4,3),(1,2),(3,2),(2,3)):
            model=restart_yield_model()
            def event(body):
                body['payload']['controller']['events'].append(dict(id=8,kind=kind,outcome=outcome,
                    source_capture_id=21,source_start_ns=220,begin_ns=232,end_ns=233,observed_capture_id=22))
            revise(model,4,event)
            with self.subTest(kind=kind,outcome=outcome):self.refused(model)
        model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller']['events'][1].update(outcome=4))
        self.refused(model)

    def test_current_pause_source_epoch_metadata_and_chronology_are_required(self):
        faults=[(517,lambda p:p['metadata'].update(generation=8)),
            (518,lambda p:p['metadata'].update(completed_prefix_end=5)),
            (518,lambda p:p['metadata'].update(inflight_start=True)),
            (519,lambda p:p['metadata'].update(stable_prefix=False)),
            (519,lambda p:p['metadata'].update(completed_prefix_start=6,completed_prefix_end=6))]
        for index,(sequence,change) in enumerate(faults):
            model=restart_yield_model();revise(model,sequence,change)
            with self.subTest(index=index):self.refused(model)
        for qualified in (220,231):
            model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller']['handoff'].update(qualified_ns=qualified))
            self.refused(model)
        model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller']['events'][-1].update(end_ns=241))
        self.refused(model)

    def test_required_first_floor_and_current_data_images_remain_registered(self):
        for capture in (10,13,20,21,22):
            model=restart_yield_model();removed=next(image for image in model['manifest']['images'] if image['capture_id']==capture)
            model['manifest']['images'].remove(removed);model['manifest']['total_bytes']-=removed['bytes']
            with self.subTest(capture=capture):self.refused(model)
        model=restart_yield_model();next(image for image in model['manifest']['images'] if image['capture_id']==20)['raw_sha256']='a'*64
        self.refused(model)

    def test_cancel_incomplete_unknown_input_and_worker_faults_precede_handoff(self):
        self.assertEqual('cancelled',self.inspect(cancelled=True)['stop_reason'])
        with self.assertRaisesRegex(ProbeError,'campaign_unpublished_run'):self.inspect(published=False)
        for flags in (dict(complete=False,interrupted=True),dict(input_state=4,ui_frozen=True),
                      dict(workers_drained=False),dict(native_inflight=True),dict(diagnostics=[dict(code='missing',authority=False)])):
            model=restart_yield_model();model['manifest'].update(flags)
            with self.subTest(flags=flags):self.refused(model)
        for status in ('deadline','cancelled','invalid','allocation','kernel'):
            model=restart_yield_model();revise(model,4,lambda body:body['payload']['cycle'].update(assessment_status=status))
            with self.subTest(status=status):self.refused(model)

    def test_closed_handoff_and_original_terminal_budget_are_not_extended(self):
        for field,value in (('allowed',1),('kind','negative_limit'),('reason',13),('source_prefix',True),('completed_prefix',8)):
            model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller']['handoff'].update({field:value}))
            with self.subTest(field=field):self.refused(model)
        model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller']['handoff'].update(extra=1));self.refused(model)
        for field,value in (('inputs',0),('inputs',17),('inputs',True),('moves',4),('restarts',13),('x',1),('walk_started_ns',0),('ended_ns',45_000_000_080)):
            model=restart_yield_model();revise(model,4,lambda body:body['payload']['controller'].update({field:value}))
            with self.subTest(field=field,value=value):self.refused(model)

    def test_positive_in_any_registered_record_blocks_continuation(self):
        model=restart_yield_model();terminal=json.loads(model['records'][4])
        extra=copy.deepcopy(terminal);extra.update(kind='diagnostic',payload=dict(
            assessment=dict(status='deadline',outcome='candidate',coverage='incomplete'),assessment_adopted=False))
        model['records'][4]=cycle.canonical(extra)
        terminal.update(sequence=5,previous=sha(model['records'][4]));model['records'][5]=cycle.canonical(terminal)
        normal=[]
        for sequence in (1,2,3,4,5):
            body=json.loads(model['records'][sequence]);normal.append(dict(sequence=sequence,kind=body['kind'],cycle=body['cycle'],
                bytes=len(model['records'][sequence]),sha256=sha(model['records'][sequence])))
        model['manifest']['records']=[model['manifest']['records'][0]]+normal+[r for r in model['manifest']['records'] if r['kind']=='frame']
        model['manifest']['total_bytes']=len(model['manifest']['images'])*len(model['image'])+sum(map(len,model['records'].values()))
        row=self.inspect(model)
        self.assertEqual(('candidate','candidate',None),(row['outcome'],row['stop_reason'],row['handoff']))

    def test_non_object_assessment_in_a_registered_carrier_is_not_absence(self):
        model=restart_yield_model();terminal=json.loads(model['records'][4])
        carrier=copy.deepcopy(terminal);carrier.update(kind='diagnostic',payload=dict(
            assessment=[dict(rows=[dict(outcome='candidate',slots=[])])]))
        model['records'][4]=cycle.canonical(carrier)
        terminal.update(sequence=5,previous=sha(model['records'][4]));model['records'][5]=cycle.canonical(terminal)
        normal=[]
        for sequence in (1,2,3,4,5):
            body=json.loads(model['records'][sequence]);normal.append(dict(sequence=sequence,kind=body['kind'],cycle=body['cycle'],
                bytes=len(model['records'][sequence]),sha256=sha(model['records'][sequence])))
        model['manifest']['records']=[model['manifest']['records'][0]]+normal+[r for r in model['manifest']['records'] if r['kind']=='frame']
        model['manifest']['total_bytes']=len(model['manifest']['images'])*len(model['image'])+sum(map(len,model['records'].values()))
        row=self.inspect(model)
        self.assertEqual(('handoff_invalid',None),(row['stop_reason'],row['handoff']))


class RestartYieldServer112(IrregularServer):
    """Authenticated transport is covered separately; this exercises real files."""
    yield_after_restart = True
    allow_restarted_budget = True

    def __init__(self,base):
        super().__init__(base);self.cases=['yield','target'];self.fail_publish_once=False

    def call(self,method,params):
        if method=='necro_native_start':
            self.calls.append((method,copy.deepcopy(params)))
            assert set(params)=={'run_id','profile','yield_after_restart'}
            assert params['yield_after_restart'] is True and params['profile']==SPEC.profile
            run_id=params['run_id'];saved=cycle.load_journal(self.base,protocol_spec=SPEC)
            assert saved['start_intent'] and saved['run_id']==run_id
            selected=self.cases.pop(0);model=restart_yield_model(run_id)
            if selected=='target':
                def target(body):
                    value=body['payload'];value['cycle'].update(outcome='target',candidate_latched=True)
                    value['assessment']=dict(status='ok',outcome='target',coverage='complete')
                    value['assessment_adopted']=True
                    value['controller']['reason']=1
                    value['controller']['handoff'].update(kind='none',allowed=False,reason=1,
                        qualified_ns=0,source_capture_id=0,source_prefix=0,pause_capture_id=0,completed_prefix=0)
                revise(model,4,target)
                model['terminal']=json.loads(model['records'][4])['payload'];model['cycle']=model['terminal']['cycle']
            self.models[run_id]=model
            return dict(run_id=run_id,profile=SPEC.profile,state='accepted',api_version=cycle.API_VERSION,
                        report={},yield_after_restart=True)
        if params.get('mode')=='published' and self.fail_publish_once:
            self.fail_publish_once=False;self.calls.append((method,copy.deepcopy(params)))
            raise ProbeError('connection_error')
        result=super().call(method,params)
        if method=='necro_native_cancel':result['yield_after_restart']=True
        return result


class RestartYieldCampaign112Tests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='yield112-campaign-');self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.base=self.root/'local'/'test-112';self.base.mkdir(parents=True)
        self.destination=self.root/'mounted';self.destination.mkdir();self.server=RestartYieldServer112(self.base)

    def invoke(self,**kwargs):
        original=native_walk.device_lock
        with patch('necroprobe.native_cycle.device_lock',lambda path=None:original(path or self.root/'device.lock')):
            return campaign.run(self.server,self.destination,spool=self.base,notice=lambda _:None,
                                protocol_spec=SPEC,**kwargs)

    def starts(self):
        return [p['run_id'] for method,p in self.server.calls if method=='necro_native_start']

    def test_restarted_budget_handoff_publishes_before_a_distinct_new_uuid(self):
        result=self.invoke(until_target=True)
        self.assertEqual(2,len(self.starts()))
        first,second=self.starts();self.assertNotEqual(first,second)
        row=result['ledger']['runs'][0]
        self.assertEqual(('unassessed',False,'handoff'),(row['outcome'],row['assessment_adopted'],row['stop_reason']))
        self.assertEqual('target',result['stop_reason'])
        calls=self.server.calls
        published=next(i for i,(method,p) in enumerate(calls) if p.get('mode')=='published' and p['run_id']==first)
        next_start=next(i for i,(method,p) in enumerate(calls) if method=='necro_native_start' and p['run_id']==second)
        images=[i for i,(method,p) in enumerate(calls) if p.get('mode')=='batch' and p['run_id']==first]
        self.assertTrue(images);self.assertLess(max(images),published);self.assertLess(published,next_start)
        self.assertTrue(all(p['yield_after_restart'] is True for method,p in calls if method=='necro_native_start'))

    def test_export_interruption_keeps_one_uuid_and_recovery_never_starts_next(self):
        self.server.fail_chunk=True
        first=self.invoke(until_target=True)
        self.assertEqual(1,len(self.starts()));self.assertFalse(first['record']['published'])
        run_id=first['record']['run_id']
        recovered=self.invoke(recovery_only=True)
        self.assertEqual([run_id],self.starts());self.assertEqual(run_id,recovered['record']['run_id'])
        self.assertTrue(recovered['record']['published']);self.assertEqual(1,len(recovered['ledger']['runs']))
        # A collection failure durably requests cancellation; recovery may
        # publish the same run but cannot restore its continuation authority.
        row=recovered['ledger']['runs'][0]
        self.assertEqual('cancelled',row['stop_reason']);self.assertIsNone(row['handoff'])

    def test_publication_ack_failure_keeps_original_zip_and_zero_next_start(self):
        self.server.fail_publish_once=True
        first=self.invoke(until_target=True)
        self.assertEqual(1,len(self.starts()));self.assertFalse(first['record']['published'])
        run_id=first['record']['run_id'];archive=self.root/'mounted'/'runtime'/('test-112-'+run_id+'.zip')
        before=archive.read_bytes()
        recovered=self.invoke(recovery_only=True)
        self.assertEqual([run_id],self.starts());self.assertEqual(before,archive.read_bytes())
        self.assertTrue(recovered['record']['published'])

    def test_cancel_after_published_yield_sends_no_next_start(self):
        cancelled=lambda:any(p.get('mode')=='published' for _,p in self.server.calls)
        result=self.invoke(until_target=True,cancelled=cancelled)
        self.assertEqual(1,len(self.starts()));self.assertTrue(result['record']['published'])
        self.assertEqual('cancelled',result['stop_reason'])


if __name__ == '__main__':
    unittest.main()
