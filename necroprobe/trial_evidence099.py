"""Read-only TEST099 feature/handoff evidence and small return archives."""
import hashlib
from pathlib import Path
import re
import uuid
import zipfile

from . import native_cycle as cycle
from .protocol import HttpTransport
from .validation import ProbeError

HANDOFF_KEYS = frozenset(('schema','kind','allowed','reason','qualified_ns','source_capture_id',
                          'source_prefix','pause_capture_id','completed_prefix'))
SUPPORT = dict(stop_detail_schema='ngg2-stop-detail-v1', handoff_schema='ngg2-trial-handoff-v1',
               maximum_run_ids=128, pin_limit=24)


class TrialClient099(cycle.CycleClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trial_probe_id = uuid.uuid4().hex

    def _validate(self, method, params):
        if method == 'necro_native_cycle' and type(params) is dict and params.get('mode') == 'trial_support':
            cycle.closed(params, ('run_id','mode'), 'method_not_allowed')
            cycle.require(cycle.identifier(params.get('run_id')), 'method_not_allowed')
            return
        return super()._validate(method, params)

    def check_schema(self):
        result = super().check_schema()
        try:
            reply = cycle._call(self, 'necro_native_cycle',
                dict(run_id=self.trial_probe_id,mode='trial_support'))
        except ProbeError as error:
            if getattr(error,'rpc_code',None) in (-32601,-32602) and getattr(error,'error_shape_valid',False):
                raise ProbeError('trial_support_missing') from None
            raise
        payload = cycle.envelope(reply,self.trial_probe_id,'trial_support')
        cycle.closed(payload,SUPPORT,'trial_support_invalid')
        cycle.require(payload == SUPPORT and type(payload['maximum_run_ids']) is int
                      and type(payload['pin_limit']) is int, 'trial_support_invalid')
        return result


def _frame(frames, capture, prefix):
    cycle.require(capture in frames, 'campaign_handoff_invalid')
    value = frames[capture]['metadata']
    cycle.require(type(value) is dict and value.get('capture_id') == capture
        and all(cycle.ns(value.get(key)) for key in ('capture_start_ns','capture_end_ns',
            'completed_prefix_start','completed_prefix_end','generation'))
        and value['capture_end_ns'] > value['capture_start_ns']
        and value['completed_prefix_start'] == value['completed_prefix_end'] == prefix
        and value.get('stable_prefix') is True and value.get('inflight_start') is False
        and value.get('inflight_end') is False and value.get('pixel_width') == 896
        and value.get('pixel_height') == 414, 'campaign_handoff_invalid')
    return value


def _negative(checkpoints, state, frames):
    matches=[]
    for body in checkpoints:
        payload=body['payload'];old=payload.get('cycle',{});value=payload.get('assessment')
        if tuple(old.get(k) for k in ('job_id','capture_id','prefix')) != tuple(state.get(k) for k in ('job_id','capture_id','prefix')):
            continue
        if (payload.get('assessment_adopted') is True and type(value) is dict
            and value.get('status') == 'ok' and value.get('outcome') == 'negative'
            and value.get('coverage') == 'complete' and old.get('assessment_status') == 'ok'
            and old.get('outcome') == 'negative' and old.get('coverage') == 'complete'):
            matches.append(payload)
    cycle.require(len(matches)==1, 'campaign_handoff_invalid')
    found=matches[0]
    source=_frame(frames,state['capture_id'],state['prefix'])
    cycle.require(found.get('raw_sha256') == frames[state['capture_id']]['raw_sha256']
                  and state.get('assessment_status') == 'ok' and state.get('outcome') == 'negative'
                  and state.get('coverage') == 'complete'
                  and cycle.ns(state.get('assessment_ns')) and cycle.ns(state.get('durable_ns'))
                  and 0 < state['assessment_ns'] <= state['durable_ns'], 'campaign_handoff_invalid')
    return found,source


def _handoff(payload, frames, checkpoints):
    controller=payload['controller'];state=payload['cycle'];value=controller.get('handoff')
    if value is None:return None,'handoff_unavailable'
    cycle.closed(value,HANDOFF_KEYS,'campaign_handoff_invalid')
    cycle.require(value['schema']=='ngg2-trial-handoff-v1'
        and value['kind'] in ('none','negative_limit','clear_search_limit')
        and type(value['allowed']) is bool
        and all(cycle.ns(value[k]) for k in HANDOFF_KEYS-{'schema','kind','allowed'}), 'campaign_handoff_invalid')
    if not value['allowed']:return value,'handoff_unavailable'
    cycle.require(value['kind']!='none' and value['reason']==14
        and all(type(controller.get(k)) is int for k in ('terminal','phase','paused','input_state',
            'current_command_id','last_completed_id','reason','ended_ns','restarts','inputs','moves'))
        and controller['terminal']==1 and controller['phase']==7 and controller['paused']==1
        and controller['input_state']==0 and controller['current_command_id']==0 and controller['reason']==14
        and 0 <= controller['restarts'] <= 12 and 0 <= controller['inputs'] <= 16
        and 0 <= controller['moves'] <= 16 and state.get('state')=='done'
        and state.get('pending') is False and state.get('candidate_latched') is False,
        'campaign_handoff_invalid')
    source=_frame(frames,value['source_capture_id'],value['source_prefix'])
    pause=_frame(frames,value['pause_capture_id'],value['completed_prefix'])
    cycle.require(source['generation']==pause['generation']
        and source['capture_end_ns'] <= value['qualified_ns'] <= controller['ended_ns']
        and pause['capture_end_ns'] <= controller['ended_ns']
        and value['completed_prefix']==controller['last_completed_id'], 'campaign_handoff_invalid')
    events=controller.get('events')
    cycle.require(type(events) is list and len(events)<=64, 'campaign_handoff_invalid')
    matched=[event for event in events if type(event) is dict and event.get('id')==value['completed_prefix']]
    cycle.require(len(matched)==1, 'campaign_handoff_invalid')
    event=matched[0]
    cycle.require(all(cycle.ns(event.get(k)) for k in ('id','kind','outcome','begin_ns','end_ns',
        'source_capture_id','source_start_ns','observed_capture_id'))
        and event['kind']==2 and event['outcome']==2 and 0 < event['begin_ns'] <= event['end_ns']
        and event['observed_capture_id']==value['pause_capture_id']
        and event['end_ns'] <= pause['capture_start_ns'], 'campaign_handoff_invalid')
    pause_source=_frame(frames,event['source_capture_id'],value['source_prefix'])
    cycle.require(event['source_start_ns']==pause_source['capture_start_ns']
        and pause_source['generation']==source['generation']
        and pause_source['capture_end_ns'] <= event['begin_ns'], 'campaign_handoff_invalid')
    if value['kind']=='negative_limit':
        _negative(checkpoints,state,frames)
        assessment=payload.get('assessment')
        cycle.require(value['source_capture_id']==state.get('capture_id')
            and value['source_prefix']==state.get('prefix')
            and payload.get('assessment_adopted') is True and type(assessment) is dict
            and assessment.get('status')=='ok' and assessment.get('outcome')=='negative'
            and assessment.get('coverage')=='complete'
            and (state.get('completed_shops')==4 or controller['restarts']==12), 'campaign_handoff_invalid')
    else:
        cycle.require(controller['restarts']==12 and controller.get('x')==controller.get('y')==0
            and value['source_capture_id']==event['source_capture_id'], 'campaign_handoff_invalid')
        if state.get('job_id')==0:
            cycle.require(all(state.get(k)==0 for k in ('capture_id','worker_started_ns','assessment_ns','durable_ns'))
                and payload.get('assessment') is None and not checkpoints, 'campaign_handoff_invalid')
        else:
            old,_=_negative(checkpoints,state,frames)
            cycle.require(cycle.ns(state.get('level_id')) and state['level_id'] > old['cycle'].get('level_id',-1)
                and value['source_capture_id'] > state['capture_id'] and value['source_prefix'] > state['prefix']
                and cycle.ns(state.get('outcome_ns')) and state['outcome_ns'] >= state['durable_ns']
                and source['capture_start_ns'] > state['outcome_ns']
                and payload.get('assessment') is None and payload.get('assessment_adopted') is False,
                'campaign_handoff_invalid')
    return value,'handoff'


def inspect_run(base, record):
    """Interpret only records already published and then byte-verified again."""
    cycle.require(record['resolved'] and record['published'], 'campaign_unpublished_run')
    manifest=cycle.verify_evidence(base,record)
    folder=Path(base)/('cycle-'+record['run_id'])/'records'
    images={item['capture_id']:item for item in manifest['images']}
    frames={};checkpoints=[];terminals=[];positives=[]
    for item in manifest['records']:
        raw=cycle._read(folder/cycle.record_name(item),cycle.MAX_RECORD)
        cycle.require(hashlib.sha256(raw).hexdigest()==item['sha256'],'cycle_file_changed')
        body=cycle.json_object(raw,cycle.MAX_RECORD)
        if item['kind']=='frame':
            image=images.get(body['capture_id'])
            if image is not None and image['raw_sha256']==body['raw_sha256']:
                frames[body['capture_id']]=body
        elif item['kind'] in ('checkpoint','terminal','assessment'):
            payload=body.get('payload',{});assessment=payload.get('assessment')
            if type(assessment) is dict and assessment.get('outcome') in ('target','candidate'):
                positives.append((assessment['outcome'],payload.get('assessment_adopted') is True))
            if item['kind']=='checkpoint':checkpoints.append(body)
            if item['kind']=='terminal':terminals.append(payload)
    cycle.require(len(terminals)==1,'campaign_terminal_missing')
    payload=terminals[0];controller=payload.get('controller');state=payload.get('cycle')
    cycle.require(type(controller) is dict and type(state) is dict,'campaign_terminal_invalid')
    outcome=state.get('outcome') if state.get('job_id',0)>0 else 'unassessed'
    reason='handoff_unavailable';handoff=None
    adopted=payload.get('assessment_adopted') is True
    if positives:
        outcome='target' if any(p[0]=='target' for p in positives) else 'candidate'
        adopted=any(p[0]==outcome and p[1] for p in positives);reason=outcome
    elif record['cancel_intent']:reason='cancelled'
    elif not manifest['complete'] or manifest['interrupted'] or manifest['diagnostics']:reason='incomplete'
    elif manifest['input_state']!=0 or manifest['native_inflight'] or manifest['ui_frozen']:reason='unknown_input'
    elif outcome=='unknown':reason='unknown'
    elif state.get('assessment_status')!='ok':reason='assessment_failed'
    if reason=='handoff_unavailable':
        try:handoff,reason=_handoff(payload,frames,checkpoints)
        except ProbeError as error:
            if error.code!='campaign_handoff_invalid':raise
            reason='handoff_invalid'
    # No assessment is not a Ring UNKNOWN, but still needs the explicit B proof.
    if outcome=='unassessed' and reason=='handoff_unavailable':reason='unassessed'
    return dict(outcome=outcome,assessment_adopted=adopted,stop_reason=reason,
        handoff=handoff,controller_reason=controller.get('reason',0),
        restarts=controller.get('restarts',0),moves=controller.get('moves',0))


def bundle(destination, ledger, last_archive, *, label='test-099'):
    """Stream an index and the last run ZIP; never load all run images in RAM."""
    from .test069 import _sync_directory
    cycle.require(type(label) is str and re.fullmatch(r'test-[0-9]{3}',label),'campaign_ledger_invalid')
    output=Path(destination)/'runtime';output.mkdir(parents=True,exist_ok=True)
    cycle.require(not output.is_symlink(),'cycle_local_symlink')
    index=cycle.canonical(ledger)
    name=label+'-campaign-'+ledger['campaign_id']+'-r'+str(ledger['revision'])+'.zip'
    target=output/name;temporary=output/(name+'.part')
    last=ledger['pending_archive'] or (ledger['runs'][-1] if ledger['runs'] else None)
    member='last-run/'+last['archive_name'] if last else None
    if last is not None:
        cycle.require(last_archive is not None and not Path(last_archive).is_symlink()
            and Path(last_archive).stat().st_size==last['archive_bytes'],'campaign_archive_missing')
    def verify(path):
        cycle.require(not path.is_symlink(),'cycle_local_symlink')
        with zipfile.ZipFile(path) as saved:
            cycle.require(saved.namelist()==(['campaign-index.json',member] if last else ['campaign-index.json']),
                          'campaign_bundle_changed')
            cycle.require(saved.read('campaign-index.json')==index,'campaign_bundle_changed')
            if last:
                item=saved.getinfo(member)
                cycle.require(item.file_size==last['archive_bytes'] and item.compress_type==zipfile.ZIP_STORED,
                              'campaign_bundle_changed')
                digest=hashlib.sha256();count=0
                with saved.open(item) as source:
                    while True:
                        data=source.read(256*1024)
                        if not data:break
                        digest.update(data);count+=len(data)
                        cycle.require(count<=last['archive_bytes'],'campaign_bundle_changed')
                cycle.require((count,digest.hexdigest())==(last['archive_bytes'],last['archive_sha256']),
                              'campaign_bundle_changed')
    if not target.exists():
        cycle.require(not temporary.is_symlink(),'cycle_local_symlink')
        with temporary.open('wb') as stream:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as saved:
                info=zipfile.ZipInfo('campaign-index.json',date_time=(1980,1,1,0,0,0));info.external_attr=0o600<<16
                saved.writestr(info,index)
                if last:
                    info=zipfile.ZipInfo(member,date_time=(1980,1,1,0,0,0));info.external_attr=0o600<<16
                    digest=hashlib.sha256();count=0
                    with Path(last_archive).open('rb') as source,saved.open(info,'w') as entry:
                        while True:
                            data=source.read(256*1024)
                            if not data:break
                            count+=len(data);digest.update(data)
                            cycle.require(count<=last['archive_bytes'],'campaign_archive_changed')
                            entry.write(data)
                    cycle.require((count,digest.hexdigest())==(last['archive_bytes'],last['archive_sha256']),
                                  'campaign_archive_changed')
            stream.flush();cycle.os.fsync(stream.fileno())
        verify(temporary);cycle.os.replace(temporary,target);_sync_directory(output)
    verify(target)
    return target
