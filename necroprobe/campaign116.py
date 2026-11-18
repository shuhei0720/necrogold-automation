"""Native-owned continuous campaigns; host collection starts only after drain.

This client never selects a movement, restarts a game, or transfers input
authority. Its start UUID is durable before the sole start POST. An interrupted
invocation recovers that UUID and cannot automatically start a replacement.
"""
import copy
import hashlib
from pathlib import Path
import re
import time
import uuid
import zipfile

from . import native_cycle as cycle
from . import cycle_publication as publication
from . import campaign_forensic116 as forensic
from .test069 import _digest, _sync_directory
from .trial_evidence099 import inspect_run, _frame, _negative, _raw_assessment_hints
from .validation import ProbeError

SPEC = cycle.IRREGULAR_PROTOCOL
CAPABILITY = 'necrogold_native_continuous_campaign_v1'
ROOT_DURATION_NS = 2_880_000_000_000
CHILD_LIMIT = 16
ROOT_KEYS = frozenset(('schema','root_id','state','active_run_id','terminal','workers_drained',
    'input_state','native_inflight','ui_frozen','stop_reason','child_limit','deadline_ns','children'))
CHILD_KEYS = frozenset(('index','run_id','predecessor_id','state','escrow_sealed',
    'escrow_sha256','terminal_reason'))
STOP_REASONS = frozenset(('none','target','candidate','unknown','cancelled','owner','locked',
    'storage','escrow_quota','run_limit','native_limit','session'))
UNUSED_QUALIFIED_STOPS = frozenset(('cancelled','owner','locked','session','native_limit'))
PROVENANCE_KEYS = frozenset(('schema','root_id','index','predecessor_id','root_started_ns','root_deadline_ns'))
SEAL_KEYS = frozenset(('schema','root_id','run_id','index','predecessor_id','next_run_id',
    'terminal_sha256','frames_sha256','controller','clock_id','session_sha256'))
CONTROLLER_NUMBERS = frozenset(('root_deadline_ns','qualified_ns','parent_deadline_ns',
    'old_job_id','restart_command_id','new_floor_capture_id','source_capture_id','source_start_ns','source_prefix'))
LEDGER_KEYS = frozenset(('schema','campaign_id','revision','mode','state','start_intent',
    'cancel_intent','complete','collection_complete','stop_reason','native_status','runs','last_error','recovery_ids','index_source'))
ROW_KEYS = frozenset(('run_id','index','predecessor_id','escrow_sha256','archive_name',
    'archive_sha256','archive_bytes','outcome','assessment_adopted','stop_reason',
    'controller_reason','restarts','moves','verified','diagnostic_only','verification_error','diagnostic_collection'))


def start_reply(value, root):
    cycle.closed(value,('run_id','profile','state','api_version','report','continuous_campaign'))
    cycle.require(value['run_id']==root and value['profile']==SPEC.profile
        and type(value['state']) is str and value['state'] in cycle.STATES and value['api_version']==cycle.API_VERSION
        and type(value['report']) is dict and value['continuous_campaign'] is True)
    return value['state']


def status_payload(value, root):
    p=cycle.closed(value,ROOT_KEYS)
    cycle.require(p['schema']=='ngg2-continuous-campaign-v1' and p['root_id']==root
        and cycle.identifier(root) and type(p['state']) is str and p['state'] in ('accepted','running','draining','stopped')
        and all(type(p[k]) is bool for k in ('terminal','workers_drained','native_inflight','ui_frozen'))
        and type(p['input_state']) is int and p['input_state'] in (0,1,2,3,4)
        and type(p['stop_reason']) is str and p['stop_reason'] in STOP_REASONS and type(p['child_limit']) is int
        and p['child_limit']==CHILD_LIMIT and cycle.ns(p['deadline_ns']) and p['deadline_ns']>ROOT_DURATION_NS
        and type(p['children']) is list and 1<=len(p['children'])<=min(128,p['child_limit']))
    previous=None
    seen=set()
    for index,row in enumerate(p['children']):
        cycle.closed(row,CHILD_KEYS)
        cycle.require(type(row['index']) is int and row['index']==index
            and cycle.identifier(row['run_id']) and row['run_id'] not in seen
            and row['predecessor_id']==previous and (index!=0 or row['run_id']==root)
            and type(row['state']) is str and row['state'] in cycle.STATES and type(row['escrow_sealed']) is bool
            and (cycle.digest(row['escrow_sha256']) if row['escrow_sealed'] else row['escrow_sha256'] is None)
            and type(row['terminal_reason']) is int and 0<=row['terminal_reason']<=20)
        if index<len(p['children'])-1:
            cycle.require(row['state'] in cycle.TERMINAL and row['escrow_sealed'])
        if row['escrow_sealed']:
            cycle.require(row['state'] in cycle.TERMINAL)
        seen.add(row['run_id']);previous=row['run_id']
    cycle.require(p['active_run_id']==previous)
    if p['terminal'] and p['workers_drained']:
        cycle.require(p['state']=='stopped')
    if p['state']=='stopped':
        cycle.require(p['terminal'] and p['workers_drained'] and not p['native_inflight']
            and p['input_state'] in (0,3,4) and all(r['state'] in cycle.TERMINAL for r in p['children']))
    if not p['terminal']:
        cycle.require(p['state'] in ('accepted','running','draining') and p['stop_reason']=='none')
    return p


def status_reply(value, root):
    return status_payload(cycle.envelope(value,root,'campaign_status',protocol_spec=SPEC),root)


def transition(previous, current):
    """An authenticated later reply cannot replace an already observed child."""
    if previous is None:
        return current
    cycle.require(current['root_id']==previous['root_id']
        and current['deadline_ns']==previous['deadline_ns']
        and len(current['children'])>=len(previous['children']),'campaign_index_changed')
    for before,after in zip(previous['children'],current['children']):
        cycle.require(all(before[k]==after[k] for k in ('index','run_id','predecessor_id')),
                      'campaign_index_changed')
        if before['escrow_sealed']:
            cycle.require(before==after,'campaign_index_changed')
    if previous['state']=='stopped':
        cycle.require(previous==current,'campaign_index_changed')
    return current


def _validate(ledger):
    cycle.closed(ledger,LEDGER_KEYS,'campaign_ledger_invalid')
    cycle.require(ledger['schema']=='necroprobe-continuous-campaign116-v1'
        and cycle.identifier(ledger['campaign_id']) and ledger['mode']=='continuous_until_target'
        and type(ledger['revision']) is int and 0<=ledger['revision']<2**63
        and ledger['state'] in ('prepared','running','pending','stopped')
        and ledger['index_source'] in ('live','recovered_readonly','unavailable')
        and all(type(ledger[k]) is bool for k in ('start_intent','cancel_intent','complete','collection_complete'))
        and (ledger['stop_reason'] is None or type(ledger['stop_reason']) is str and len(ledger['stop_reason'])<=64)
        and (ledger['last_error'] is None or type(ledger['last_error']) is str and len(ledger['last_error'])<=64)
        and type(ledger['runs']) is list and len(ledger['runs'])<=128
        and type(ledger['recovery_ids']) is list and len(ledger['recovery_ids'])<=128
        and all(cycle.identifier(v) for v in ledger['recovery_ids'])
        and len(set(ledger['recovery_ids']))==len(ledger['recovery_ids']),'campaign_ledger_invalid')
    native=ledger['native_status']
    if native is not None:
        status_payload(native,ledger['campaign_id'])
    seen=set()
    for row in ledger['runs']:
        cycle.closed(row,ROW_KEYS,'campaign_ledger_invalid')
        cycle.require(cycle.identifier(row['run_id']) and row['run_id'] not in seen
            and type(row['index']) is int and 0<=row['index']<128
            and (row['predecessor_id'] is None or cycle.identifier(row['predecessor_id']))
            and (row['escrow_sha256'] is None or cycle.digest(row['escrow_sha256']))
            and row['archive_name']=='test-116-'+row['run_id']+'.zip'
            and cycle.digest(row['archive_sha256']) and type(row['archive_bytes']) is int
            and 0<row['archive_bytes']<=100*1024*1024
            and row['outcome'] in ('target','candidate','negative','unknown','unassessed')
            and type(row['assessment_adopted']) is bool and type(row['verified']) is bool
            and type(row['diagnostic_only']) is bool
            and (row['verification_error'] is None or type(row['verification_error']) is str and len(row['verification_error'])<=64)
            and type(row['stop_reason']) is str and len(row['stop_reason'])<=64
            and all(cycle.ns(row[k]) for k in ('controller_reason','restarts','moves')),'campaign_ledger_invalid')
        seen.add(row['run_id'])
        if row['diagnostic_only']:
            cycle.require(not row['verified'] and row['outcome']=='unknown' and not row['assessment_adopted']
                and row['verification_error']=='campaign_terminal_missing'
                and row['stop_reason']=='prepared_child_diagnostic'
                and row['diagnostic_collection']==forensic.COLLECTION_SCOPE,'campaign_ledger_invalid')
        else:
            cycle.require(row['diagnostic_collection'] is None,'campaign_ledger_invalid')
    if ledger['collection_complete']:
        cycle.require(native is not None and native['state']=='stopped'
            and len(ledger['runs'])==len(native['children'])
            and [r['run_id'] for r in ledger['runs']]==[r['run_id'] for r in native['children']]
            and all(r['verified'] or r['diagnostic_only'] for r in ledger['runs'])
            and all(not r['diagnostic_only'] for r in ledger['runs'][:-1]),'campaign_ledger_invalid')
    if ledger['complete']:
        cycle.require(ledger['collection_complete'] and native is not None and native['state']=='stopped'
            and len(ledger['runs'])==len(native['children']) and all(r['verified'] for r in ledger['runs'])
            and [r['run_id'] for r in ledger['runs']]==[r['run_id'] for r in native['children']],
            'campaign_ledger_invalid')
    return ledger


def _fresh(root=None):
    return dict(schema='necroprobe-continuous-campaign116-v1',campaign_id=root or uuid.uuid4().hex,
        revision=0,mode='continuous_until_target',state='prepared',start_intent=False,
        cancel_intent=False,complete=False,collection_complete=False,stop_reason=None,native_status=None,runs=[],last_error=None,
        recovery_ids=[],index_source='unavailable')


def _save(base, ledger):
    _validate(ledger);history=base/'continuous-campaigns';history.mkdir(mode=0o700,exist_ok=True)
    cycle.require(not history.is_symlink(),'cycle_local_symlink')
    ledger['revision']+=1;raw=cycle.canonical(ledger)
    cycle._atomic(history/(ledger['campaign_id']+'.json'),raw)
    cycle._atomic(base/'continuous-campaign.json',raw)


def _load(base):
    selector=base/'continuous-campaign.json'
    if not selector.exists():
        # A lost selector does not discard the durable per-root start intent.
        history=base/'continuous-campaigns'
        if not history.exists():
            return None
        cycle.require(not history.is_symlink(),'cycle_local_symlink')
        pending=[];closed=[]
        for path in history.glob('*.json'):
            value=_validate(cycle.json_object(cycle._read(path,512*1024),512*1024))
            if value['start_intent'] and not value['collection_complete']:
                pending.append(value)
            elif value['collection_complete']:
                closed.append(value)
        cycle.require(len(pending)<=1,'campaign_recovery_ambiguous')
        if pending:return pending[0]
        if closed:
            active=cycle.load_journal(base,protocol_spec=SPEC)
            matches=([value for value in closed if any(row['run_id']==active['run_id']
                for row in value['runs'])] if active is not None else [])
            if len(matches)==1:return matches[0]
            if len(closed)==1:return closed[0]
            raise ProbeError('campaign_recovery_ambiguous')
        return None
    selected=_validate(cycle.json_object(cycle._read(selector,512*1024),512*1024))
    path=base/'continuous-campaigns'/(selected['campaign_id']+'.json')
    value=_validate(cycle.json_object(cycle._read(path,512*1024),512*1024))
    cycle.require(value['campaign_id']==selected['campaign_id'] and value['revision']>=selected['revision'],
                  'campaign_ledger_invalid')
    return value


def _root_status(client, base, ledger, *, keepalive):
    root=ledger['campaign_id']
    reply=status_reply(cycle._call(client,SPEC.query,dict(run_id=root,
        mode='campaign_status',keepalive=keepalive)),root)
    ledger['native_status']=copy.deepcopy(transition(ledger['native_status'],reply))
    ledger['index_source']='live'
    ledger['state']='running' if not reply['terminal'] else 'pending'
    _save(base,ledger)
    return reply


def _cancel(client, base, ledger):
    save_failure=None
    if not ledger['cancel_intent']:
        ledger['cancel_intent']=True
        try:
            _save(base,ledger)
        except OSError as error:
            save_failure=error
    start_reply(cycle._call(client,'necro_native_cancel',dict(run_id=ledger['campaign_id'])),ledger['campaign_id'])
    if save_failure is not None:
        raise save_failure


def _header(base, record):
    headers=[r for r in record['records'] if r['kind']=='session']
    cycle.require(len(headers)==1,'campaign_child_provenance')
    path=base/('cycle-'+record['run_id'])/'records'/cycle.record_name(headers[0])
    body=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
    value=body.get('provenance',{}).get('continuous_campaign')
    cycle.closed(value,PROVENANCE_KEYS,'campaign_child_provenance')
    cycle.require(value['schema']=='ngg2-continuous-child-v1' and cycle.identifier(value['root_id'])
        and type(value['index']) is int and 0<=value['index']<128
        and (value['predecessor_id'] is None or cycle.identifier(value['predecessor_id']))
        and cycle.ns(value['root_started_ns']) and value['root_started_ns']>0
        and cycle.ns(value['root_deadline_ns'])
        and value['root_deadline_ns']-value['root_started_ns']==ROOT_DURATION_NS,
        'campaign_child_provenance')
    return value


def verify_child(base, record, native, descriptor):
    """Bind native escrow, exported hash chain, root provenance, and ordering."""
    header=_header(base,record);index=descriptor['index'];root=native['root_id']
    cycle.require(header['root_id']==root and header['index']==index
        and header['predecessor_id']==descriptor['predecessor_id']
        and header['root_deadline_ns']==native['deadline_ns'],'campaign_child_provenance')
    seals=[r for r in record['records'] if r['kind']=='continuation_seal']
    terminals=[r for r in record['records'] if r['kind']=='terminal']
    cycle.require(descriptor['escrow_sealed'] and len(seals)==len(terminals)==1
        and seals[0]['sha256']==descriptor['escrow_sha256'],'campaign_child_seal')
    path=base/('cycle-'+record['run_id'])/'records'/cycle.record_name(seals[0])
    body=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
    p=cycle.closed(body.get('payload'),SEAL_KEYS,'campaign_child_seal')
    successor=native['children'][index+1]['run_id'] if index+1<len(native['children']) else None
    session_item,session=_record_body(base,record,'session')
    _terminal_item,terminal_body=_record_body(base,record,'terminal')
    terminal_controller=terminal_body.get('payload',{}).get('controller',{})
    manifest=_stored_manifest(base,record)
    cycle.require(terminal_controller.get('input_state')==manifest['input_state'],'campaign_child_seal')
    clock_id=session.get('provenance',{}).get('clock_id')
    refs=[];images={r['capture_id']:r for r in record['images']}
    for item in record['records']:
        if item['kind']=='frame':
            path=base/('cycle-'+record['run_id'])/'records'/cycle.record_name(item)
            frame=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
            image=images.get(frame.get('capture_id'))
            cycle.require(image is not None and frame.get('raw_sha256')==image['raw_sha256']
                and frame.get('raw_bytes')==896*414*4,'campaign_child_seal')
            refs.append(dict(capture_id=frame['capture_id'],raw_sha256=frame['raw_sha256'],
                metadata_sha256=item['sha256'],bytes=896*414*4))
    refs.sort(key=lambda r:r['capture_id'])
    cycle.require(len(refs)==len(images) and len({r['capture_id'] for r in refs})==len(images),
                  'campaign_child_seal')
    cycle.require(p['schema']=='ngg2-continuation-seal-v1' and p['root_id']==root
        and p['run_id']==record['run_id']==descriptor['run_id'] and type(p['index']) is int and p['index']==index
        and p['predecessor_id']==descriptor['predecessor_id'] and p['next_run_id']==successor
        and p['terminal_sha256']==terminals[0]['sha256']
        and p['frames_sha256']==hashlib.sha256(cycle.canonical(refs)).hexdigest()
        and cycle.identifier(clock_id) and p['clock_id']==clock_id
        and p['session_sha256']==session_item['sha256'],
        'campaign_child_seal')
    cycle.require(type(terminal_controller.get('reason')) is int
        and terminal_controller['reason']==descriptor['terminal_reason'],'campaign_child_seal')
    c=cycle.closed(p['controller'],CONTROLLER_NUMBERS|{'abi_version','enabled','successor_floor','qualified'},
                   'campaign_child_seal')
    cycle.require(type(c['abi_version']) is int and c['abi_version']==1
        and all(type(c[k]) is bool for k in ('enabled','successor_floor','qualified'))
        and c['enabled'] and c['successor_floor']==(index>0)
        and all(cycle.ns(c[k]) for k in CONTROLLER_NUMBERS)
        and c['root_deadline_ns']==native['deadline_ns']
        and (successor is None or c['qualified']), 'campaign_child_seal')
    cycle.require(terminal_controller.get('continuous_campaign')==c,'campaign_child_seal')
    if c['qualified']:
        if successor is None:
            # Cancellation may win after C qualified but before the next
            # admission. Preserve that true snapshot for archival verification;
            # this never grants a successor, heartbeat, or another start.
            cycle.require(native['state']=='stopped' and native['terminal']
                and native['workers_drained'] and native['input_state']==0
                and not native['native_inflight'] and not native['ui_frozen']
                and native['stop_reason'] in UNUSED_QUALIFIED_STOPS,'campaign_child_seal')
        _continuation_chain(base,record,c,terminal_controller)
    return header


def _continuation_chain(base, record, c, terminal):
    """Verify the old negative and actual restart, never a fresh-floor absence."""
    invalid='campaign_child_continuation'
    required=CONTROLLER_NUMBERS-{'root_deadline_ns'}
    cycle.require(all(c[k]>0 for k in required)
        and c['source_prefix']==c['restart_command_id']
        and c['new_floor_capture_id']<=c['source_capture_id']
        and c['qualified_ns']<=c['parent_deadline_ns']<=c['root_deadline_ns']
        and c['qualified_ns']<c['root_deadline_ns'],invalid)
    cycle.require(all(type(terminal.get(k)) is int for k in ('terminal','phase','paused','input_state',
        'current_command_id','last_completed_id','ended_ns','inputs','moves','restarts'))
        and terminal['terminal']==1 and terminal['phase']==7 and terminal['paused']==0
        and terminal['input_state']==terminal['current_command_id']==0
        and terminal['last_completed_id']==c['source_prefix']
        and c['qualified_ns']<=terminal['ended_ns']<=c['parent_deadline_ns']
        and terminal['ended_ns']<c['root_deadline_ns']
        and 0<=terminal['moves']<=terminal['inputs']<=16 and 1<=terminal['restarts']<=12,invalid)
    frames={};checkpoints=[];intents=[];outcomes=[]
    for item in record['records']:
        if item['kind']=='session':
            continue
        path=base/('cycle-'+record['run_id'])/'records'/cycle.record_name(item)
        body=cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)
        if item['kind']=='frame':
            frames[body['capture_id']]=body;continue
        p=body.get('payload',{})
        cycle.require(type(p) is dict,invalid)
        assessment=p.get('assessment');hint=p.get('assessment_hint');state=p.get('cycle',{})
        hinted,malformed=_raw_assessment_hints(assessment)
        cycle.require(not hinted and not malformed
            and not(type(assessment) is dict and assessment.get('outcome') in ('target','candidate'))
            and not(type(hint) is dict and hint.get('outcome') in ('target','candidate'))
            and not(type(state) is dict and (state.get('candidate_latched') is True
                or state.get('outcome') in ('target','candidate'))),invalid)
        if type(state) is dict and 'candidate_latched' in state:
            cycle.require(type(state['candidate_latched']) is bool and not state['candidate_latched'],invalid)
        if item['kind']=='checkpoint':checkpoints.append(body)
        if item['kind']=='restart_intent':
            cycle.require(type(p.get('command')) is dict,invalid)
            if p['command'].get('id')==c['restart_command_id']:
                intents.append(body)
        if item['kind']=='restart_outcome' and p.get('floor_prefix')==c['restart_command_id']:
            outcomes.append(body)
    cycle.require(len(intents)==len(outcomes)==1,invalid)
    intent,outcome=intents[0]['payload'],outcomes[0]['payload']
    before=intent.get('cycle',{});after=outcome.get('cycle',{});command=intent.get('command',{})
    cycle.require(type(before) is dict and type(after) is dict and type(command) is dict
        and before.get('job_id')==after.get('job_id')==c['old_job_id']
        and before.get('state')=='negative_restart'
        and before.get('outcome')==after.get('outcome')=='negative'
        and before.get('coverage')==after.get('coverage')=='complete'
        and command.get('kind')==3 and command.get('id')==c['restart_command_id']
        and outcome.get('floor_capture_id')==after.get('next_floor_capture_id')==c['new_floor_capture_id']
        and intents[0]['sequence']<outcomes[0]['sequence'],invalid)
    cycle.require(all(cycle.ns(command.get(k)) for k in ('id','source_capture_id','source_start_ns'))
        and cycle.ns(intent.get('source_prefix')) and cycle.ns(intent.get('generation'))
        and cycle.ns(outcome.get('generation')) and cycle.ns(outcome.get('floor_prefix'))
        and cycle.ns(outcome.get('floor_capture_id')),invalid)
    try:
        checkpoint,_goods=_negative(checkpoints,before,frames)
        cycle.require(checkpoint is not None,invalid)
        fresh=_frame(frames,c['new_floor_capture_id'],c['source_prefix'])
        source=_frame(frames,c['source_capture_id'],c['source_prefix'])
        restart_source=_frame(frames,command.get('source_capture_id'),intent.get('source_prefix'))
    except ProbeError:
        raise ProbeError(invalid) from None
    for state in (before,after,checkpoint.get('cycle',{})):
        cycle.require(type(state) is dict and all(cycle.ns(state.get(k)) for k in
            ('job_id','capture_id','capture_start_ns','prefix','worker_started_ns','assessment_ns','durable_ns'))
            and state['job_id']==c['old_job_id'] and state['capture_id']>0,invalid)
    checkpoint_sequence=next(body['sequence'] for body in checkpoints if body['payload'] is checkpoint)
    terminal_item,_terminal_body=_record_body(base,record,'terminal')
    cycle.require(checkpoint_sequence<intents[0]['sequence']<outcomes[0]['sequence']<terminal_item['sequence'],invalid)
    _session_row,session=_record_body(base,record,'session')
    provenance=session.get('provenance',{})
    cycle.require(type(provenance) is dict and cycle.identifier(provenance.get('clock_id'))
        and cycle.ns(provenance.get('generation')) and provenance['generation']>0
        and checkpoint.get('clock_id')==provenance['clock_id']
        and type(checkpoint.get('generation')) is int
        and checkpoint['generation']==provenance['generation'],invalid)
    outcome_controller=outcome.get('controller')
    cycle.require(type(outcome_controller) is dict and type(outcome_controller.get('events')) is list,invalid)
    events=outcome_controller['events']
    ack=[e for e in events if type(e) is dict and e.get('id')==c['restart_command_id']]
    final_ack=[e for e in terminal.get('events',[]) if type(e) is dict and e.get('id')==c['restart_command_id']]
    cycle.require(len(ack)==len(final_ack)==1 and ack[0]==final_ack[0],invalid)
    event=ack[0]
    cycle.require(event.get('kind')==3 and event.get('outcome')==2
        and all(cycle.ns(event.get(k)) for k in ('begin_ns','end_ns','source_start_ns','source_capture_id','observed_capture_id'))
        and event['source_capture_id']==command.get('source_capture_id')
        and event['source_start_ns']==command.get('source_start_ns')==restart_source['capture_start_ns']
        and event['observed_capture_id']==c['new_floor_capture_id']
        and intent.get('source_raw_sha256')==frames[command['source_capture_id']]['raw_sha256']
        and outcome.get('floor_raw_sha256')==frames[c['new_floor_capture_id']]['raw_sha256']
        and fresh['generation']==source['generation']==restart_source['generation']==intent.get('generation')==outcome.get('generation')==provenance['generation']
        and restart_source['capture_end_ns']<=event['begin_ns']<=event['end_ns']<=fresh['capture_start_ns']
        and ((c['new_floor_capture_id']==c['source_capture_id'] and fresh==source)
            or (c['new_floor_capture_id']!=c['source_capture_id'] and fresh['capture_end_ns']<=source['capture_start_ns']))
        and source['capture_start_ns']==c['source_start_ns']
        and source['capture_end_ns']<=c['qualified_ns'],invalid)


def _collect_one(client, base, destination, run_id, *, notice, clock, sleep):
    record=cycle.load_journal(base,protocol_spec=SPEC)
    if record is None or record['run_id']!=run_id:
        path=base/('cycle-'+run_id)/'journal.json'
        if path.exists():
            cycle._atomic(base/'active-cycle.json',cycle._read(path,512*1024))
            record=cycle.load_journal(base,protocol_spec=SPEC)
        else:
            record=cycle.fresh_record(run_id,protocol_spec=SPEC)
            record.update(start_intent=True,state='unknown');cycle._journal(base,record)
    if not record['resolved']:
        cycle.collect(client,base,record,notice=notice,clock=clock,protocol_spec=SPEC)
    cycle.verify_evidence(base,record,protocol_spec=SPEC)
    if record['published']:
        receipt_path=base.parent/('.'+base.name+'-publication')/(run_id+'.receipt.json')
        receipt=cycle.json_object(cycle._read(receipt_path,4096),4096)
        cycle.closed(receipt,('schema','run_id','export_id','manifest_sha256','archive_sha256','archive_bytes','receipt_sha256'),
                     'cycle_publication_receipt')
        cycle.require(receipt['schema']=='ngg2-cycle-publication-v1' and receipt['run_id']==run_id
            and receipt['export_id']==record['export_id'] and receipt['manifest_sha256']==record['manifest_sha256']
            and receipt['archive_sha256']==record['archive_sha256'] and cycle.digest(receipt['receipt_sha256']),
            'cycle_publication_receipt')
        old_archive=receipt_path.with_name(run_id+'.zip')
        cycle.require(_digest(old_archive,lambda:False)==(receipt['archive_bytes'],receipt['archive_sha256']),
                      'cycle_archive_changed')
    archive=publication.publish(client,base,destination,record,notice=notice,clock=clock,sleep=sleep,protocol_spec=SPEC)
    return record,archive


def _bundle(base, destination, ledger):
    if not ledger['runs']:
        return None
    output=Path(destination)/'runtime';output.mkdir(mode=0o700,exist_ok=True)
    cycle.require(not output.is_symlink(),'cycle_local_symlink')
    name='test-116-campaign-'+ledger['campaign_id']+'-r'+str(ledger['revision'])+'.zip'
    target=output/name;part=output/(name+'.part')
    cycle.require(not target.is_symlink() and not part.is_symlink(),'cycle_local_symlink')
    last=ledger['runs'][-1]
    archive=output/last['archive_name']
    cycle.require(_digest(archive,lambda:False)==(last['archive_bytes'],last['archive_sha256']),
                  'campaign_archive_changed')
    with part.open('wb') as handle:
        with zipfile.ZipFile(handle,'w',compression=zipfile.ZIP_DEFLATED) as result:
            result.writestr('campaign-index.json',cycle.canonical(ledger))
            result.write(archive,'last-run/'+last['archive_name'])
        handle.flush();cycle.os.fsync(handle.fileno())
    with zipfile.ZipFile(part) as check:
        cycle.require(check.testzip() is None,'campaign_archive_changed')
    cycle.os.replace(part,target);_sync_directory(output)
    return target


def _record_body(base, record, kind):
    found=[r for r in record['records'] if r['kind']==kind]
    cycle.require(len(found)==1,'campaign_child_seal')
    path=base/('cycle-'+record['run_id'])/'records'/cycle.record_name(found[0])
    return found[0],cycle.json_object(cycle._read(path,cycle.MAX_RECORD),cycle.MAX_RECORD)


def _stored_manifest(base, record):
    path=base/('cycle-'+record['run_id'])/'native-manifest.json'
    raw=cycle._read(path,cycle.MAX_MANIFEST)
    cycle.require(hashlib.sha256(raw).hexdigest()==record['manifest_sha256'],'cycle_manifest_changed')
    return cycle.json_object(raw,cycle.MAX_MANIFEST)


def _recovered_native(base, ledger, collected):
    """Reconstruct evidence only. A recovered index never grants a keepalive."""
    indexed=[];root=None;deadline=None
    for run_id,(record,_archive) in collected.items():
        header=_header(base,record)
        root=header['root_id'] if root is None else root
        deadline=header['root_deadline_ns'] if deadline is None else deadline
        cycle.require(header['root_id']==root and header['root_deadline_ns']==deadline,
                      'campaign_recovery_ambiguous')
        seal,_body=_record_body(base,record,'continuation_seal')
        _terminal_row,terminal=_record_body(base,record,'terminal')
        reason=terminal.get('payload',{}).get('controller',{}).get('reason')
        cycle.require(type(reason) is int and 0<=reason<=20,'campaign_child_seal')
        indexed.append(dict(index=header['index'],run_id=run_id,predecessor_id=header['predecessor_id'],
            state='stopped',escrow_sealed=True,escrow_sha256=seal['sha256'],terminal_reason=reason))
    indexed.sort(key=lambda r:r['index'])
    cycle.require(indexed and indexed[0]['run_id']==root,'campaign_recovery_ambiguous')
    if ledger['campaign_id']!=root:
        cycle.require(ledger['native_status'] is None and not ledger['runs'],'campaign_recovery_ambiguous')
        # Retain the orphan selector as a non-authoritative recovery alias.
        alias=copy.deepcopy(ledger);alias.update(start_intent=False,state='pending',last_error='campaign_rebound_readonly')
        _save(base,alias);ledger['campaign_id']=root
    native=dict(schema='ngg2-continuous-campaign-v1',root_id=root,state='stopped',
        active_run_id=indexed[-1]['run_id'],terminal=True,workers_drained=True,input_state=0,
        native_inflight=False,ui_frozen=False,stop_reason='unknown',child_limit=CHILD_LIMIT,
        deadline_ns=deadline,children=indexed)
    manifests=[_stored_manifest(base,record) for record,_archive in collected.values()]
    native.update(input_state=max(m['input_state'] for m in manifests),
        ui_frozen=any(m['ui_frozen'] for m in manifests),
        native_inflight=any(m['native_inflight'] for m in manifests),
        terminal=all(m['terminal'] for m in manifests),
        workers_drained=all(m['workers_drained'] for m in manifests))
    status_payload(native,root)
    # This is a forensic index. Each child is independently verified below;
    # an invalid continuation must retain its actual UNKNOWN diagnostics.
    return native


def _finish_collect(client, base, destination, ledger, *, notice, clock, sleep, recover_index=False):
    native=ledger['native_status']
    ids=([r['run_id'] for r in native['children']] if native is not None else [])
    if recover_index:
        ids=list(dict.fromkeys(ids+ledger['recovery_ids']+[r['run_id'] for r in ledger['runs']]))
    collected={};recovery_error=None
    for run_id in ids:
        record,archive=_collect_one(client,base,destination,run_id,notice=notice,clock=clock,sleep=sleep)
        collected[run_id]=(record,archive)
        if recover_index:
            try:
                header=_header(base,record)
                _seal_row,body=_record_body(base,record,'continuation_seal')
                link=body.get('payload',{}).get('next_run_id')
                for needed in (header['root_id'],header['predecessor_id'],link):
                    if needed is not None:
                        cycle.require(cycle.identifier(needed),'campaign_child_seal')
                        if needed not in ids:
                            cycle.require(len(ids)<128,'campaign_run_limit');ids.append(needed)
            except ProbeError as error:
                recovery_error=error.code
    if recover_index and recovery_error is None:
        try:
            native=_recovered_native(base,ledger,collected)
            ledger.update(native_status=copy.deepcopy(native),index_source='recovered_readonly')
        except ProbeError as error:
            recovery_error=error.code
    for run_id in ids:
        record,archive=collected[run_id]
        descriptor=None
        if native is not None:
            descriptor=next((r for r in native['children'] if r['run_id']==run_id),None)
        verified=False;failure=None
        try:
            if descriptor is None:
                _header(base,record)
                failure='campaign_index_unavailable'
            else:
                verify_child(base,record,native,descriptor);verified=recovery_error is None
        except ProbeError as error:
            failure=error.code
        diagnostic=False;verification_error=failure
        try:
            evidence=inspect_run(base,record,protocol_spec=SPEC)
        except ProbeError as error:
            if error.code!='campaign_terminal_missing':raise
            evidence=forensic.admit(base,record,native,descriptor,collected,index_source=ledger['index_source'])
            diagnostic=True;verified=False;verification_error=error.code;failure=error.code
        size,digest=_digest(archive,lambda:False)
        row=dict(run_id=run_id,index=descriptor['index'] if descriptor else len(ledger['runs']),
            predecessor_id=descriptor['predecessor_id'] if descriptor else None,
            escrow_sha256=descriptor['escrow_sha256'] if descriptor else None,
            archive_name='test-116-'+run_id+'.zip',archive_bytes=size,archive_sha256=digest,
            verified=verified,diagnostic_only=diagnostic,verification_error=verification_error,
            diagnostic_collection=copy.deepcopy(forensic.COLLECTION_SCOPE) if diagnostic else None,**evidence)
        row.pop('handoff',None)
        known=[i for i,r in enumerate(ledger['runs']) if r['run_id']==run_id]
        if known:
            old=ledger['runs'][known[0]]
            cycle.require(all(old[k]==row[k] for k in ROW_KEYS-{'verified'})
                and (not old['verified'] or row['verified']),'campaign_run_changed')
            ledger['runs'][known[0]]=row
        else:
            ledger['runs'].append(row)
        if failure is not None:
            ledger['last_error']=failure
        _save(base,ledger)
    if recovery_error is not None:
        ledger['last_error']=recovery_error
    if native is not None:
        positions={r['run_id']:r['index'] for r in native['children']}
        ledger['runs'].sort(key=lambda r:positions.get(r['run_id'],128))
    ledger['complete']=bool(native is not None and native['state']=='stopped'
        and len(ledger['runs'])==len(native['children']) and all(r['verified'] for r in ledger['runs']))
    ledger['collection_complete']=bool(native is not None and native['state']=='stopped'
        and len(ledger['runs'])==len(native['children'])
        and all(r['verified'] or r['diagnostic_only'] for r in ledger['runs']))
    ledger['state']='stopped' if ledger['collection_complete'] else 'pending'
    ledger['stop_reason']=native['stop_reason'] if native is not None else 'campaign_index_unavailable'
    _save(base,ledger)
    return dict(ledger=ledger,campaign_archive=_bundle(base,destination,ledger),
        stop_reason=ledger['stop_reason'],record=cycle.load_journal(base,protocol_spec=SPEC))


def run(client, destination, *, spool, until_target=True, recovery_only=False,
        cancelled=lambda:False, notice=print, clock=time.monotonic_ns, sleep=time.sleep):
    cycle.require(cycle.client_protocol(client) is SPEC and not client.yield_after_restart,
                  'cycle_protocol_invalid')
    cycle.require(not(until_target and recovery_only),'campaign_mode_conflict')
    cycle.require(until_target or recovery_only,'campaign_mode_required')
    base=Path(spool);base.mkdir(mode=0o700,parents=True,exist_ok=True)
    cycle.require(not base.is_symlink(),'cycle_local_symlink')
    with cycle.device_lock():
        ledger=_load(base)
        recovering=bool(ledger is not None and ledger['start_intent'] and not ledger['collection_complete'])
        if ledger is not None and ledger['collection_complete'] and recovery_only:
            return _finish_collect(client,base,destination,ledger,notice=notice,clock=clock,sleep=sleep)
        if ledger is None or ledger['collection_complete'] or not ledger['start_intent']:
            if ledger is not None and ledger['collection_complete']:
                forensic.verify_closed_collection(base,ledger)
            client.check_schema()
            probe=uuid.uuid4().hex
            prepared=cycle.prepare(cycle._call(client,SPEC.query,dict(run_id=probe,mode='prepare',
                request_authorization=False)),probe,protocol_spec=SPEC)
            if prepared['unpublished_run_ids']:
                ledger=_fresh(prepared['unpublished_run_ids'][0]);ledger.update(start_intent=True,
                    state='pending',recovery_ids=prepared['unpublished_run_ids'])
                _save(base,ledger);recovering=True
                notice('端末の未回収記録を確認しました。新しいゲームは開始しません。')
            else:
                cycle.require(not recovery_only,'campaign_recovery_record_missing')
                cycle.require(prepared['ready'],'cycle_notification_permission')
                if ledger is None or ledger['collection_complete']:
                    ledger=_fresh()
                _save(base,ledger)
        root=ledger['campaign_id']
        try:
            if not ledger['start_intent']:
                cycle.require(not recovery_only and not cancelled(),'cancel_requested')
                ledger.update(start_intent=True,state='running',last_error=None);_save(base,ledger)
                # There is exactly one POST. All uncertain results retain root.
                ready_deadline=clock()+8_000_000_000
                def start_guard():
                    try:
                        cycle._checked(cancelled,clock,ready_deadline)
                    except ProbeError as error:
                        raise cycle._StartNotSent(error.code) from None
                previous_guard=getattr(client,'_before_start_post',None)
                client._before_start_post=start_guard
                try:
                    start_guard()
                    state=start_reply(cycle._call(client,'necro_native_start',dict(run_id=root,
                        profile=SPEC.profile,continuous_campaign=True)),root)
                except cycle._StartNotSent:
                    ledger.update(start_intent=False,state='prepared');_save(base,ledger)
                    raise
                except ProbeError as failure:
                    # The dedicated authenticated code is emitted strictly
                    # before native admission. Other errors remain uncertain.
                    if (isinstance(failure,cycle.RemoteRpcError) and failure.error_shape_valid is True
                            and failure.rpc_code==-32095):
                        ledger.update(start_intent=False,state='prepared',last_error='cycle_start_not_admitted')
                        _save(base,ledger)
                        raise cycle._StartNotSent('cycle_start_not_admitted') from None
                    raise
                finally:
                    client._before_start_post=previous_guard
                cycle.require(state in cycle.STATES)
            if recovering and ledger['native_status'] is not None and ledger['native_status']['state']=='stopped':
                return _finish_collect(client,base,destination,ledger,notice=notice,clock=clock,sleep=sleep)
            deadline=clock()+ROOT_DURATION_NS+30_000_000_000
            cancelled_sent=False
            while True:
                if (recovering or recovery_only or cancelled() or clock()>=deadline) and not cancelled_sent:
                    _cancel(client,base,ledger);cancelled_sent=True
                native=_root_status(client,base,ledger,
                    keepalive=not(recovering or recovery_only or ledger['cancel_intent'] or cancelled()))
                if native['terminal'] and native['workers_drained'] and not native['native_inflight'] \
                        and native['input_state'] in (0,3,4):
                    break
                cycle.require(clock()<deadline,'host_deadline')
                sleep(.25)
            notice('自動周回が停止しました。ここから全周の画像・記録を回収します。')
            return _finish_collect(client,base,destination,ledger,notice=notice,clock=clock,sleep=sleep)
        except (ProbeError,OSError) as error:
            if getattr(error,'rpc_code',None)==-32097 and getattr(error,'error_shape_valid',False):
                prepared=cycle.prepare(cycle._call(client,SPEC.query,dict(run_id=root,mode='prepare',
                    request_authorization=False)),root,protocol_spec=SPEC)
                ids=prepared['unpublished_run_ids']
                cycle.require(ids or ledger['runs'],'campaign_recovery_record_missing')
                ledger['recovery_ids']=list(dict.fromkeys(ledger['recovery_ids']+ids))
                _save(base,ledger)
                return _finish_collect(client,base,destination,ledger,notice=notice,clock=clock,sleep=sleep,recover_index=True)
            code=error.code if isinstance(error,ProbeError) else 'local_storage_failed'
            ledger.update(state='pending',complete=False,last_error=(code
                if re.fullmatch('[a-z_0-9]{1,64}',code) else 'campaign_rpc_failed'))
            try:
                _save(base,ledger)
            except OSError:
                pass  # The original durable start UUID still owns recovery.
            if ledger['start_intent'] and not ledger['cancel_intent'] and not (
                    ledger['native_status'] is not None and ledger['native_status']['state']=='stopped'):
                try:
                    _cancel(client,base,ledger)
                except (ProbeError,OSError):
                    pass
            return dict(ledger=ledger,campaign_archive=_bundle(base,destination,ledger),
                stop_reason=ledger['last_error'],record=cycle.load_journal(base,protocol_spec=SPEC))
